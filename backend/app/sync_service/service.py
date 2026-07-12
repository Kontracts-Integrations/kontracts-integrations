"""
Sync service: orchestrates fetching TRIRIGA data, mapping, validating,
pushing to Kontracts, and logging results.
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.mapping_engine.filters import _resolve as _resolve_source_field
from app.models.id_mapping import DEFAULT_LOOKUP_TABLE, IdMapping
from app.models.lookup_table import LookupTable
from app.models.log_entry import LogEntry, LogLevel
from app.models.mapping import MappingTemplate, MappingVersion
from app.models.record_sync_state import RecordSyncState
from app.models.sync_run import RecordStatus, RunStatus, SyncRecord, SyncRun
from app.utils.hashing import payload_hash

logger = logging.getLogger(__name__)


def _extract_lookup_keys(source_record: Dict[str, Any], fields: List[str]) -> List[str]:
    """Resolve each configured source field to a string key value.

    Blank/None values are dropped. Field resolution mirrors the mapping engine
    (``Section||field`` prefixes stripped, ``Associated.`` paths supported).
    """
    keys: List[str] = []
    for field in fields or []:
        value = _resolve_source_field(source_record, field)
        if value is None:
            continue
        sval = str(value).strip()
        if sval and sval not in keys:
            keys.append(sval)
    return keys


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_run(self, run_id: int) -> None:
        """
        Main entry point. Loads the run from DB, executes the sync,
        and updates the run record.
        """
        run = await self._get_run(run_id)
        if not run:
            logger.error(f"SyncRun {run_id} not found")
            return

        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._log(run_id, LogLevel.info, f"Sync run {run_id} started", "sync_service")

        try:
            await self._run_sync(run)
        except Exception as e:
            run.status = RunStatus.failed
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await self._log(
                run_id, LogLevel.error, f"Sync run failed: {e}", "sync_service"
            )
            await self.db.flush()

    async def _run_sync(self, run: SyncRun) -> None:
        run_id = run.id

        # Load mapping template
        template, version = await self._load_mapping(run.mapping_template_id)
        if not template or not version:
            raise ValueError(
                f"No active mapping template/version for id {run.mapping_template_id}"
            )

        await self._log(
            run_id,
            LogLevel.info,
            f"Using mapping '{template.name}' v{version.version_number}",
            "sync_service",
        )

        # Build clients
        tririga_client = await self._build_tririga_client(template)
        kontracts_client = await self._build_kontracts_client(template)

        # Extract source field names from field mappings
        field_mappings_data = version.field_mappings.get("mappings", [])
        source_field_names = [
            fm["source_field"] for fm in field_mappings_data
            if fm.get("source_field")
        ]
        # Fields referenced only by filters must also be fetched, otherwise the
        # filter has no value to compare against and drops every record. Fields on
        # the associated BO (use_associated) are collected separately below and
        # joined into the query, not fetched from the main object.
        associated_field_names: List[str] = []
        for flt in (template.source_filters or []):
            fld = flt.get("field")
            if not fld:
                continue
            if flt.get("use_associated"):
                if fld not in associated_field_names:
                    associated_field_names.append(fld)
            elif fld not in source_field_names:
                source_field_names.append(fld)

        # Associated fields referenced by mappings (use_associated) are joined too,
        # so a single runDynamicQuery returns their real values inline.
        if template.fetch_associated and template.assoc_object:
            for fm in field_mappings_data:
                if fm.get("use_associated") and fm.get("source_field"):
                    if fm["source_field"] not in associated_field_names:
                        associated_field_names.append(fm["source_field"])

        use_assoc_join = bool(
            template.fetch_associated and template.assoc_object and associated_field_names
        )

        # Fetch TRIRIGA data via runDynamicQuery
        await self._log(
            run_id,
            LogLevel.info,
            f"Fetching TRIRIGA data: module={template.source_module}, "
            f"object={template.source_object}, fields={len(source_field_names)}"
            + (f", associated {template.assoc_object}: {len(associated_field_names)} fields" if use_assoc_join else ""),
            "tririga_client",
        )

        records = await tririga_client.run_dynamic_query(
            module_name=template.source_module or "",
            object_type_name=template.source_object or "",
            field_names=source_field_names,
            filter_condition="",
            max_records=1000,
            fetch_all=True,
            associated_module=(template.assoc_module or "") if use_assoc_join else "",
            associated_object=(template.assoc_object or "") if use_assoc_join else "",
            associated_field_names=associated_field_names if use_assoc_join else None,
        )

        await self._log(
            run_id,
            LogLevel.info,
            f"Fetched {len(records)} records from TRIRIGA",
            "tririga_client",
        )

        # Apply source-record filters (starts_with / contains / equals / etc.).
        source_filters = template.source_filters or []
        # If any filter targets the associated BO and the query join wasn't used to
        # supply that data, fall back to attaching id/name via getAssociatedRecords
        # before filtering (the join already populates record["Associated"]).
        needs_assoc_filter = any(f.get("use_associated") for f in source_filters)
        if needs_assoc_filter and not use_assoc_join and template.fetch_associated and template.assoc_string:
            await self._enrich_associated(records, tririga_client, template.assoc_string)
            await self._log(
                run_id, LogLevel.info,
                f"Attached associated records to {len(records)} records for filtering",
                "sync_service",
            )
        if source_filters:
            from app.mapping_engine.filters import filter_records
            fetched = len(records)
            records = filter_records(records, source_filters, template.filter_match or "all")
            await self._log(
                run_id,
                LogLevel.info,
                f"Source filters kept {len(records)} of {fetched} records "
                f"(match={template.filter_match or 'all'})",
                "sync_service",
            )

        run.total_records = len(records)
        await self.db.flush()

        # Build mapping engine
        from app.mapping_engine.engine import MappingEngine
        engine = MappingEngine(field_mappings_data)

        # Fetch Kontracts schema for validation
        schema_fields = []
        if template.kontracts_endpoint:
            try:
                from app.kontracts_client.schema_parser import parse_endpoint_schema
                openapi_schema = await kontracts_client.get_openapi_schema()
                schema_fields = parse_endpoint_schema(
                    openapi_schema,
                    template.kontracts_endpoint,
                    template.kontracts_method or "post",
                )
            except Exception as e:
                await self._log(
                    run_id,
                    LogLevel.warning,
                    f"Could not load Kontracts schema for validation: {e}",
                    "kontracts_client",
                )

        # Determine which named lookup table this mapping writes produced IDs into.
        # An explicit lookup_table_name wins; otherwise a leases endpoint implicitly
        # writes to the default table (backward compatible with prior behavior).
        write_table = template.lookup_table_name
        if not write_table and template.kontracts_endpoint and "leases" in template.kontracts_endpoint.lower():
            write_table = DEFAULT_LOOKUP_TABLE
        should_write_lookup = bool(write_table)

        # Source fields whose values are also indexed as lookup keys for the
        # produced kontracts_id (so later mappings can resolve it by business key).
        lookup_key_fields = list(template.lookup_key_fields or [])

        # Register the named lookup table this mapping writes to (if any) so it is
        # discoverable by other mappings even before this run populates entries.
        if should_write_lookup:
            await self._ensure_lookup_table(write_table)

        # Pre-load all id mappings for deduplication and lookup transforms,
        # partitioned by their named lookup table.
        existing_result = await self.db.execute(
            select(
                IdMapping.table_name,
                IdMapping.source_record_id,
                IdMapping.source_key,
                IdMapping.kontracts_id,
                IdMapping.lookup_keys,
            )
        )
        lease_rows = existing_result.fetchall()

        # Upsert mode: when enabled, subsequent runs update changed records rather
        # than skipping them, so the plain "already synced" skip is disabled and the
        # per-record hash decision (see _plan_record) drives create/update/skip.
        update_existing = bool(template.update_existing)

        # Skip records already present in the table this mapping writes to.
        already_synced = (
            {row[1] for row in lease_rows if row[0] == write_table}
            if should_write_lookup and not update_existing else set()
        )

        # Pre-load prior sync state (kontracts_id + payload hash per source record)
        # for this mapping, used to decide create vs update vs skip on re-runs.
        sync_state: Dict[str, tuple] = {}
        if update_existing:
            state_result = await self.db.execute(
                select(
                    RecordSyncState.source_record_id,
                    RecordSyncState.kontracts_id,
                    RecordSyncState.payload_hash,
                ).where(RecordSyncState.mapping_template_id == template.id)
            )
            for row in state_result.fetchall():
                sync_state[str(row[0])] = (row[1], row[2])

        # Build per-table lookup maps: {table_name: {source_key: kontracts_id}}.
        # Keys are the record id, the lease id, and any indexed business keys.
        lookup_tables: Dict[str, Dict[str, str]] = {}
        for row in lease_rows:
            table = lookup_tables.setdefault(row[0], {})
            table[str(row[1])] = row[3]
            if row[2]:
                table[str(row[2])] = row[3]
            for key in (row[4] or []):
                if key:
                    table[str(key)] = row[3]
        default_bucket = lookup_tables.get(DEFAULT_LOOKUP_TABLE, {})
        engine_context = {
            "lookup_tables": lookup_tables,
            # Backward-compat aliases for the default bucket: legacy configs
            # referenced it as "lease_mappings"; the current default is "default".
            "default": default_bucket,
            "lease_mappings": lookup_tables.get("lease_mappings", default_bucket),
        }

        # Existing IDs from this mapping's lookup table, used to update previously
        # created records that predate the sync-state table.
        existing_lookup = lookup_tables.get(write_table, {}) if should_write_lookup else {}

        await self._log(
            run_id, LogLevel.info,
            f"{len(already_synced)} records already synced into '{write_table}' — will skip duplicates"
            if should_write_lookup
            else "No lookup table configured — skipping deduplication check",
            "sync_service",
        )

        # Process in batches of 10 concurrently
        batch_size = 10
        success_count = 0
        failed_count = 0
        skipped_count = 0

        is_bulk_endpoint = template.kontracts_endpoint and "bulk" in template.kontracts_endpoint.lower()

        if is_bulk_endpoint:
            # === BULK SYNC PATH ===
            # 1. Map and validate all records (still fetching associated records in batches of 10 for SOAP client efficiency)
            valid_records = []  # List of dicts: {"record_id": str, "source_record": dict, "mapped_payload": dict}
            
            for batch_start in range(0, len(records), batch_size):
                batch = records[batch_start : batch_start + batch_size]
                
                # If fetch_associated is enabled, attach associated records for this
                # batch (records already enriched for filtering are skipped).
                if template.fetch_associated and template.assoc_string and not use_assoc_join:
                    await self._enrich_associated(batch, tririga_client, template.assoc_string)

                for i, source_record in enumerate(batch):
                    record_id = str(
                        source_record.get("triRecordId",
                        source_record.get("triRecordIdSY",
                        source_record.get("id",
                        source_record.get("recordId", f"record_{batch_start + i}"))))
                    )

                    if record_id in already_synced:
                        skipped_count += 1
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            status=RecordStatus.skipped,
                            source_data=source_record,
                            mapped_data=None,
                            error="Already synced",
                        )
                        continue

                    try:
                        mapped_payload, warnings = engine.apply(source_record, context=engine_context)

                        for warning in warnings:
                            await self._log(
                                run_id, LogLevel.warning, warning, "mapping_engine",
                                extra={"record_id": record_id}
                            )

                        if not mapped_payload:
                            await self._log(
                                run_id,
                                LogLevel.warning,
                                f"Record {record_id} produced empty payload — skipping",
                                "mapping_engine",
                            )
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=record_id,
                                status=RecordStatus.skipped,
                                source_data=source_record,
                                mapped_data=mapped_payload,
                                error="Empty payload after mapping",
                            )
                            skipped_count += 1
                            continue

                        # Validate
                        is_valid = True
                        val_errors = []
                        if schema_fields:
                            is_valid, val_errors = engine.validate(mapped_payload, schema_fields)
                            
                        # Extra validation: amount > 0 and due_date not null (for payments endpoints)
                        amount_val = 0
                        try:
                            amount_val = float(mapped_payload.get("amount", 0) or 0)
                        except ValueError:
                            pass
                        
                        due_date_val = mapped_payload.get("due_date")
                        is_payments_endpoint = template.kontracts_endpoint and "payments" in template.kontracts_endpoint.lower()
                        
                        extra_errors = []
                        if is_payments_endpoint:
                            if amount_val <= 0:
                                extra_errors.append({"field": "amount", "message": "Amount must be greater than 0", "value": mapped_payload.get("amount")})
                            if not due_date_val:
                                extra_errors.append({"field": "due_date", "message": "Required field due_date is missing or null", "value": None})
                                
                        if not is_valid or extra_errors:
                            error_msgs = [e.to_dict() for e in val_errors] + extra_errors
                            await self._log(
                                run_id,
                                LogLevel.error,
                                f"Record {record_id} failed local validation: {error_msgs}",
                                "validators",
                            )
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=record_id,
                                status=RecordStatus.failed,
                                source_data=source_record,
                                mapped_data=mapped_payload,
                                error=str(error_msgs),
                            )
                            failed_count += 1
                            continue

                        valid_records.append({
                            "record_id": record_id,
                            "source_record": source_record,
                            "mapped_payload": mapped_payload
                        })

                    except Exception as e:
                        failed_count += 1
                        error_msg = str(e)
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            status=RecordStatus.failed,
                            source_data=source_record,
                            mapped_data=None,
                            error=error_msg,
                        )
                        await self._log(
                            run_id,
                            LogLevel.error,
                            f"Record {record_id} failed: {error_msg}",
                            "sync_service",
                            extra={"record_id": record_id},
                        )

            # 1b. Upsert partitioning: split validated records into skips (unchanged),
            # updates (changed / previously created), and creates. Only creates go
            # through the bulk endpoint; updates are applied as individual PUTs.
            if update_existing and valid_records:
                creates = []
                updates = []
                for rec in valid_records:
                    action, plan_kid, new_hash = self._plan_record(
                        rec["record_id"], rec["mapped_payload"], sync_state, existing_lookup, update_existing
                    )
                    rec["new_hash"] = new_hash
                    if action == "skip":
                        skipped_count += 1
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=rec["record_id"],
                            kontracts_id=plan_kid,
                            status=RecordStatus.skipped,
                            source_data=rec["source_record"],
                            mapped_data=rec["mapped_payload"],
                            error="Unchanged since last sync",
                        )
                    elif action == "update":
                        rec["kontracts_id"] = plan_kid
                        updates.append(rec)
                    else:
                        creates.append(rec)

                if updates:
                    await self._log(
                        run_id, LogLevel.info,
                        f"Updating {len(updates)} changed records via PUT",
                        "sync_service",
                    )

                    async def _update_one(rec):
                        try:
                            res = await kontracts_client.update_record(
                                endpoint=template.kontracts_endpoint or "/api/v1/payments/bulk",
                                kontracts_id=rec["kontracts_id"],
                                payload=rec["mapped_payload"],
                                method="PUT",
                            )
                            return {"status": "success", "rec": rec, "result": res}
                        except Exception as e:
                            return {"status": "failed", "rec": rec, "error": str(e)}

                    for ur in await asyncio.gather(*[_update_one(r) for r in updates]):
                        rec = ur["rec"]
                        if ur["status"] == "success":
                            kontracts_id = str((ur["result"] or {}).get("id", "") or "") or rec["kontracts_id"]
                            await self._record_sync_state(
                                template.id, rec["record_id"], kontracts_id, rec["new_hash"], sync_state
                            )
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=rec["record_id"],
                                kontracts_id=kontracts_id,
                                status=RecordStatus.success,
                                source_data=rec["source_record"],
                                mapped_data=rec["mapped_payload"],
                            )
                            success_count += 1
                        else:
                            failed_count += 1
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=rec["record_id"],
                                status=RecordStatus.failed,
                                source_data=rec["source_record"],
                                mapped_data=rec["mapped_payload"],
                                error=ur["error"],
                            )
                            await self._log(
                                run_id, LogLevel.error,
                                f"Record {rec['record_id']} update failed: {ur['error']}",
                                "sync_service",
                                extra={"record_id": rec["record_id"]},
                            )

                valid_records = creates

            # 2. Push all valid (create) payloads to Kontracts in chunked bulk requests!
            if valid_records:
                bulk_batch_size = 1000
                await self._log(
                    run_id,
                    LogLevel.info,
                    f"Paging through {len(valid_records)} validated records in chunks of {bulk_batch_size} for bulk API push",
                    "sync_service"
                )
                
                for chunk_start in range(0, len(valid_records), bulk_batch_size):
                    chunk_records = valid_records[chunk_start : chunk_start + bulk_batch_size]
                    payloads_array = [rec["mapped_payload"] for rec in chunk_records]
                    
                    await self._log(
                        run_id,
                        LogLevel.info,
                        f"Pushing bulk chunk ({chunk_start + 1} to {chunk_start + len(chunk_records)}) in a single HTTP request",
                        "sync_service"
                    )
                    
                    try:
                        res = await kontracts_client.push_bulk(
                            endpoint=template.kontracts_endpoint or "/api/v1/payments/bulk",
                            method=template.kontracts_method or "POST",
                            payloads=payloads_array
                        )
                        
                        # 3. Process the bulk response and match back by index order in this chunk
                        created_payments = res.get("payments", [])
                        bulk_errors = res.get("errors", [])
                        
                        # Map the results to original records by index correlation
                        for idx, rec in enumerate(chunk_records):
                            record_id = rec["record_id"]
                            source_record = rec["source_record"]
                            mapped_payload = rec["mapped_payload"]
                            
                            # Check if this index was successfully created or has a bulk error
                            if idx < len(created_payments) and created_payments[idx]:
                                result_data = created_payments[idx]
                                kontracts_id = str(result_data.get("id", "unknown"))
                                tririga_lease_id = str(result_data.get("lease_id", ""))
                                tririga_record_id = record_id

                                if should_write_lookup:
                                    self.db.add(IdMapping(
                                        table_name=write_table,
                                        source_key=tririga_lease_id,
                                        source_record_id=tririga_record_id,
                                        kontracts_id=kontracts_id,
                                        lookup_keys=_extract_lookup_keys(source_record, lookup_key_fields) or None,
                                    ))

                                if update_existing:
                                    await self._record_sync_state(
                                        template.id, record_id, kontracts_id,
                                        rec.get("new_hash") or payload_hash(mapped_payload),
                                        sync_state,
                                    )

                                await self._save_record(
                                    run_id=run_id,
                                    tririga_id=record_id,
                                    kontracts_id=kontracts_id,
                                    status=RecordStatus.success,
                                    source_data=source_record,
                                    mapped_data=mapped_payload,
                                )
                                success_count += 1
                            else:
                                # Index had a push failure (extract error details if present)
                                failed_count += 1
                                error_msg = "Bulk push error at index"
                                if idx < len(bulk_errors) and bulk_errors[idx]:
                                    error_msg = str(bulk_errors[idx].get("message", bulk_errors[idx]))
                                elif "detail" in res:
                                    error_msg = str(res["detail"])
                                
                                await self._save_record(
                                    run_id=run_id,
                                    tririga_id=record_id,
                                    status=RecordStatus.failed,
                                    source_data=source_record,
                                    mapped_data=mapped_payload,
                                    error=error_msg,
                                )
                                await self._log(
                                    run_id,
                                    LogLevel.error,
                                    f"Record {record_id} bulk sync failed: {error_msg}",
                                    "sync_service",
                                    extra={"record_id": record_id},
                                )
                                
                    except Exception as e:
                        # The bulk HTTP request failed for this chunk
                        error_msg = str(e)
                        await self._log(
                            run_id,
                            LogLevel.error,
                            f"Bulk request chunk push failed: {error_msg}",
                            "sync_service"
                        )
                        # Mark all chunk records as failed
                        for rec in chunk_records:
                            failed_count += 1
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=rec["record_id"],
                                status=RecordStatus.failed,
                                source_data=rec["source_record"],
                                mapped_data=rec["mapped_payload"],
                                error=error_msg,
                            )
            
            # Commit all database records at once
            run.success_count = success_count
            run.failed_count = failed_count
            run.skipped_count = skipped_count
            await self.db.commit()

        else:
            # === TRADITIONAL CONCURRENT RECORD-BY-RECORD PUSH PATH ===
            for batch_start in range(0, len(records), batch_size):
                batch = records[batch_start : batch_start + batch_size]
                
                # If fetch_associated is enabled, attach associated records for this
                # batch (records already enriched for filtering are skipped).
                if template.fetch_associated and template.assoc_string and not use_assoc_join:
                    await self._enrich_associated(batch, tririga_client, template.assoc_string)

                # 1. Map and validate serially (instantaneous in-memory operations)
                tasks_to_run = [] # List of tuples: (record_id, source_record, mapped_payload)
                
                for i, source_record in enumerate(batch):
                    record_id = str(
                        source_record.get("triRecordId",
                        source_record.get("triRecordIdSY",
                        source_record.get("id",
                        source_record.get("recordId", f"record_{batch_start + i}"))))
                    )

                    if record_id in already_synced:
                        skipped_count += 1
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            status=RecordStatus.skipped,
                            source_data=source_record,
                            mapped_data=None,
                            error="Already synced",
                        )
                        continue

                    try:
                        mapped_payload, warnings = engine.apply(source_record, context=engine_context)

                        for warning in warnings:
                            await self._log(
                                run_id, LogLevel.warning, warning, "mapping_engine",
                                extra={"record_id": record_id}
                            )

                        if not mapped_payload:
                            await self._log(
                                run_id,
                                LogLevel.warning,
                                f"Record {record_id} produced empty payload — skipping",
                                "mapping_engine",
                            )
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=record_id,
                                status=RecordStatus.skipped,
                                source_data=source_record,
                                mapped_data=mapped_payload,
                                error="Empty payload after mapping",
                            )
                            skipped_count += 1
                            continue

                        # Validate
                        is_valid = True
                        val_errors = []
                        if schema_fields:
                            is_valid, val_errors = engine.validate(mapped_payload, schema_fields)
                            
                        # Extra validation: amount > 0 and due_date not null (for payments endpoints)
                        amount_val = 0
                        try:
                            amount_val = float(mapped_payload.get("amount", 0) or 0)
                        except ValueError:
                            pass
                        
                        due_date_val = mapped_payload.get("due_date")
                        is_payments_endpoint = template.kontracts_endpoint and "payments" in template.kontracts_endpoint.lower()
                        
                        extra_errors = []
                        if is_payments_endpoint:
                            if amount_val <= 0:
                                extra_errors.append({"field": "amount", "message": "Amount must be greater than 0", "value": mapped_payload.get("amount")})
                            if not due_date_val:
                                extra_errors.append({"field": "due_date", "message": "Required field due_date is missing or null", "value": None})
                                
                        if not is_valid or extra_errors:
                            error_msgs = [e.to_dict() for e in val_errors] + extra_errors
                            await self._log(
                                run_id,
                                LogLevel.error,
                                f"Record {record_id} failed local validation: {error_msgs}",
                                "validators",
                            )
                            await self._save_record(
                                run_id=run_id,
                                tririga_id=record_id,
                                status=RecordStatus.failed,
                                source_data=source_record,
                                mapped_data=mapped_payload,
                                error=str(error_msgs),
                            )
                            failed_count += 1
                            continue

                        # Add to task queue for parallel push
                        tasks_to_run.append((record_id, source_record, mapped_payload))

                    except Exception as e:
                        failed_count += 1
                        error_msg = str(e)
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            status=RecordStatus.failed,
                            source_data=source_record,
                            mapped_data=None,
                            error=error_msg,
                        )
                        await self._log(
                            run_id,
                            LogLevel.error,
                            f"Record {record_id} failed: {error_msg}",
                            "sync_service",
                            extra={"record_id": record_id},
                        )

                if not tasks_to_run:
                    # Still commit partial totals/progress after each batch chunk
                    run.success_count = success_count
                    run.failed_count = failed_count
                    run.skipped_count = skipped_count
                    await self.db.commit()
                    continue

                # 2. Plan create/update/skip for each record (upsert-aware)
                planned = []  # (record_id, source_record, mapped_payload, action, kontracts_id, new_hash)
                for record_id, source_record, mapped_payload in tasks_to_run:
                    action, plan_kid, new_hash = self._plan_record(
                        record_id, mapped_payload, sync_state, existing_lookup, update_existing
                    )
                    if action == "skip":
                        skipped_count += 1
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            kontracts_id=plan_kid,
                            status=RecordStatus.skipped,
                            source_data=source_record,
                            mapped_data=mapped_payload,
                            error="Unchanged since last sync",
                        )
                        continue
                    planned.append((record_id, source_record, mapped_payload, action, plan_kid, new_hash))

                if not planned:
                    run.success_count = success_count
                    run.failed_count = failed_count
                    run.skipped_count = skipped_count
                    await self.db.commit()
                    continue

                # 3. Push to Kontracts concurrently (this is the slow network part!)
                async def push_single_record(record_id, source_record, mapped_payload, action, plan_kid, new_hash):
                    try:
                        if action == "update":
                            res = await kontracts_client.update_record(
                                endpoint=template.kontracts_endpoint or "/api/v1/leases/",
                                kontracts_id=plan_kid,
                                payload=mapped_payload,
                                method="PUT",
                            )
                        else:
                            res = await kontracts_client.push_record(
                                endpoint=template.kontracts_endpoint or "/api/v1/leases/",
                                method=template.kontracts_method or "POST",
                                payload=mapped_payload,
                            )
                        return {"status": "success", "action": action, "record_id": record_id, "source_record": source_record, "mapped_payload": mapped_payload, "plan_kid": plan_kid, "new_hash": new_hash, "result": res}
                    except Exception as e:
                        return {"status": "failed", "action": action, "record_id": record_id, "source_record": source_record, "mapped_payload": mapped_payload, "error": str(e)}

                push_tasks = [push_single_record(*p) for p in planned]

                results = await asyncio.gather(*push_tasks)

                # 4. Process and write results serially (safe for SQLAlchemy)
                for res in results:
                    record_id = res["record_id"]
                    source_record = res["source_record"]
                    mapped_payload = res["mapped_payload"]

                    if res["status"] == "success":
                        result_data = res["result"]
                        action = res["action"]
                        kontracts_id = str(result_data.get("id", "") or "") or res["plan_kid"] or "unknown"
                        tririga_lease_id = str(result_data.get("lease_id", ""))
                        tririga_record_id = record_id

                        # New lookup rows are only written for creates (updates reuse the id).
                        if should_write_lookup and action == "create":
                            self.db.add(IdMapping(
                                table_name=write_table,
                                source_key=tririga_lease_id,
                                source_record_id=tririga_record_id,
                                kontracts_id=kontracts_id,
                                lookup_keys=_extract_lookup_keys(source_record, lookup_key_fields) or None,
                            ))

                        if update_existing:
                            await self._record_sync_state(
                                template.id, record_id, kontracts_id, res["new_hash"], sync_state
                            )

                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            kontracts_id=kontracts_id,
                            status=RecordStatus.success,
                            source_data=source_record,
                            mapped_data=mapped_payload,
                        )
                        success_count += 1

                        await self._log(
                            run_id,
                            LogLevel.info,
                            f"Record {record_id} -> Kontracts {kontracts_id} ({action}d)",
                            "sync_service",
                            extra={"tririga_id": record_id, "kontracts_id": kontracts_id},
                        )
                    else:
                        failed_count += 1
                        error_msg = res["error"]
                        logger.error(f"Record {record_id} failed: {error_msg}")
                        await self._save_record(
                            run_id=run_id,
                            tririga_id=record_id,
                            status=RecordStatus.failed,
                            source_data=source_record,
                            mapped_data=mapped_payload,
                            error=error_msg,
                        )
                        await self._log(
                            run_id,
                            LogLevel.error,
                            f"Record {record_id} failed: {error_msg}",
                            "sync_service",
                            extra={"record_id": record_id},
                        )
                
                # Commit after each batch chunk to preserve progress
                run.success_count = success_count
                run.failed_count = failed_count
                run.skipped_count = skipped_count
                await self.db.commit()

        # Update run totals
        run.success_count = success_count
        run.failed_count = failed_count
        run.skipped_count = skipped_count
        run.status = RunStatus.completed if failed_count == 0 else RunStatus.failed
        if failed_count > 0 and success_count > 0:
            run.status = RunStatus.completed  # Partial success still marks completed
        run.completed_at = datetime.now(timezone.utc)

        await self._log(
            run_id,
            LogLevel.info,
            f"Run complete: {success_count} success, {failed_count} failed, {skipped_count} skipped",
            "sync_service",
        )
        await self.db.flush()

    async def _get_run(self, run_id: int) -> Optional[SyncRun]:
        result = await self.db.execute(
            select(SyncRun).where(SyncRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def _load_mapping(
        self, template_id: Optional[int]
    ):
        if not template_id:
            return None, None

        result = await self.db.execute(
            select(MappingTemplate).where(MappingTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            return None, None

        # Query current version directly — avoids relationship loading issues
        version_result = await self.db.execute(
            select(MappingVersion)
            .where(MappingVersion.template_id == template_id)
            .where(MappingVersion.is_current.is_(True))
            .order_by(MappingVersion.version_number.desc())
            .limit(1)
        )
        current_version = version_result.scalar_one_or_none()

        return template, current_version

    async def _build_tririga_client(self, template: MappingTemplate):
        from app.config import settings
        from app.models.connection import Connection
        from app.tririga_client.client import TririgaClient

        if settings.demo_mode:
            return TririgaClient(
                base_url=settings.tririga_url,
                username="demo",
                password="demo",
                demo_mode=True,
            )

        if template.source_connection_id:
            result = await self.db.execute(
                select(Connection).where(Connection.id == template.source_connection_id)
            )
            conn = result.scalar_one_or_none()
            if conn:
                from app.utils.crypto import decrypt_credentials
                creds = decrypt_credentials(conn.encrypted_credentials)
                return TririgaClient(
                    base_url=conn.base_url or settings.tririga_url,
                    username=creds.get("username", ""),
                    password=creds.get("password", ""),
                )

        return TririgaClient(
            base_url=settings.tririga_url,
            username=settings.tririga_username or "",
            password=settings.tririga_password or "",
        )

    async def _build_kontracts_client(self, template: MappingTemplate):
        from app.config import settings
        from app.kontracts_client.client import KontractsClient

        if settings.demo_mode:
            return KontractsClient(
                base_url=settings.kontracts_base_url,
                auth0_domain="demo.auth0.com",
                client_id="demo",
                client_secret="demo",
                audience="demo",
                demo_mode=True,
            )

        if template.target_connection_id:
            from app.models.connection import Connection
            result = await self.db.execute(
                select(Connection).where(
                    Connection.id == template.target_connection_id
                )
            )
            conn = result.scalar_one_or_none()
            if conn:
                from app.utils.crypto import decrypt_credentials
                creds = decrypt_credentials(conn.encrypted_credentials)
                return KontractsClient(
                    base_url=conn.base_url or settings.kontracts_base_url,
                    auth0_domain=creds.get("auth0_domain", ""),
                    client_id=creds.get("client_id", ""),
                    client_secret=creds.get("client_secret", ""),
                    audience=creds.get("audience", ""),
                )

        return KontractsClient(
            base_url=settings.kontracts_base_url,
            auth0_domain=settings.kontracts_auth0_domain or "",
            client_id=settings.kontracts_client_id or "",
            client_secret=settings.kontracts_client_secret or "",
            audience=settings.kontracts_audience or "",
        )

    def _plan_record(
        self,
        record_id: str,
        mapped_payload: Dict[str, Any],
        sync_state: Dict[str, tuple],
        existing_lookup: Dict[str, str],
        update_existing: bool,
    ) -> tuple:
        """Decide how to push a record: returns (action, kontracts_id, new_hash).

        action is one of "create", "update", "skip". When update_existing is off
        every record is a create (prior behavior).
        """
        new_hash = payload_hash(mapped_payload)
        if not update_existing:
            return "create", None, new_hash

        prior = sync_state.get(record_id)
        if prior:
            kontracts_id, old_hash = prior
            if old_hash == new_hash:
                return "skip", kontracts_id, new_hash
            return "update", kontracts_id, new_hash

        # No tracked state yet — reuse an existing lookup-table id if present so a
        # previously created record is updated instead of duplicated.
        kontracts_id = existing_lookup.get(record_id)
        if kontracts_id:
            return "update", kontracts_id, new_hash
        return "create", None, new_hash

    async def _enrich_associated(self, records, tririga_client, assoc_string: str) -> None:
        """Attach the associated BO record (id/name) to each record under
        record["Associated"]. Records already enriched are skipped, so this is
        safe to call before filtering and again per batch."""
        async def _one(rec):
            if rec.get("Associated") is not None:
                return
            rid = str(
                rec.get("triRecordId",
                rec.get("triRecordIdSY",
                rec.get("id",
                rec.get("recordId", ""))))
            )
            if not rid.isdigit():
                rec["Associated"] = {}
                return
            assocs = await tririga_client.get_associated_records(
                record_id=int(rid), association_name=assoc_string
            )
            if assocs:
                fa = assocs[0]
                rec["Associated"] = {
                    "triRecordId": str(fa.get("associatedRecordId", "")),
                    "triRecordIdSY": str(fa.get("associatedRecordId", "")),
                    "triIdTX": fa.get("associatedRecordName", ""),
                    "triNameTX": fa.get("associatedRecordName", ""),
                    "id": str(fa.get("associatedRecordId", "")),
                }
            else:
                rec["Associated"] = {}

        await asyncio.gather(*[_one(r) for r in records])

    async def _ensure_lookup_table(self, name: str) -> None:
        """Register a named lookup table (bucket) if it isn't already, so other
        mappings can discover it. Idempotent."""
        if not name:
            return
        existing = await self.db.execute(
            select(LookupTable.id).where(LookupTable.name == name)
        )
        if existing.scalar_one_or_none() is None:
            self.db.add(LookupTable(name=name))
            await self.db.flush()

    async def _record_sync_state(
        self,
        template_id: int,
        source_record_id: str,
        kontracts_id: str,
        new_hash: str,
        sync_state: Dict[str, tuple],
    ) -> None:
        """Persist (or update) the per-record sync state for upsert on future runs."""
        if source_record_id in sync_state:
            await self.db.execute(
                sql_update(RecordSyncState)
                .where(RecordSyncState.mapping_template_id == template_id)
                .where(RecordSyncState.source_record_id == source_record_id)
                .values(kontracts_id=kontracts_id, payload_hash=new_hash)
            )
        else:
            self.db.add(RecordSyncState(
                mapping_template_id=template_id,
                source_record_id=source_record_id,
                kontracts_id=kontracts_id,
                payload_hash=new_hash,
            ))
        sync_state[source_record_id] = (kontracts_id, new_hash)

    async def _save_record(
        self,
        run_id: int,
        tririga_id: Optional[str] = None,
        kontracts_id: Optional[str] = None,
        status: RecordStatus = RecordStatus.success,
        source_data: Optional[Dict] = None,
        mapped_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        record = SyncRecord(
            run_id=run_id,
            tririga_record_id=tririga_id,
            kontracts_record_id=kontracts_id,
            status=status,
            source_data=source_data,
            mapped_data=mapped_data,
            error_message=error,
        )
        self.db.add(record)
        await self.db.flush()

    async def _log(
        self,
        run_id: Optional[int],
        level: LogLevel,
        message: str,
        component: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = LogEntry(
            run_id=run_id,
            level=level,
            message=message,
            component=component,
            extra=extra,
        )
        self.db.add(entry)
        # No per-entry flush: the session (autoflush=False) persists buffered log
        # rows at the next batch commit, avoiding a DB round-trip per log line.

        # Also emit to Python logging
        python_level = {
            LogLevel.debug: logging.DEBUG,
            LogLevel.info: logging.INFO,
            LogLevel.warning: logging.WARNING,
            LogLevel.error: logging.ERROR,
        }.get(level, logging.INFO)
        logger.log(python_level, f"[run={run_id}] [{component}] {message}")
