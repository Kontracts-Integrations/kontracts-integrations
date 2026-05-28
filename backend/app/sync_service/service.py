"""
Sync service: orchestrates fetching TRIRIGA data, mapping, validating,
pushing to Kontracts, and logging results.
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lease_mapping import LeaseMapping
from app.models.log_entry import LogEntry, LogLevel
from app.models.mapping import MappingTemplate, MappingVersion
from app.models.sync_run import RecordStatus, RunStatus, SyncRecord, SyncRun

logger = logging.getLogger(__name__)


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

        # Fetch TRIRIGA data via runDynamicQuery
        await self._log(
            run_id,
            LogLevel.info,
            f"Fetching TRIRIGA data: module={template.source_module}, "
            f"object={template.source_object}, fields={len(source_field_names)}",
            "tririga_client",
        )

        records = await tririga_client.run_dynamic_query(
            module_name=template.source_module or "",
            object_type_name=template.source_object or "",
            field_names=source_field_names,
            filter_condition="",
            max_records=1000,
            fetch_all=True,
        )

        run.total_records = len(records)
        await self._log(
            run_id,
            LogLevel.info,
            f"Fetched {len(records)} records from TRIRIGA",
            "tririga_client",
        )
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

        # Pre-load lease_mappings for deduplication check and lease_lookup transform
        existing_result = await self.db.execute(
            select(
                LeaseMapping.tririga_record_id,
                LeaseMapping.tririga_lease_id,
                LeaseMapping.kontracts_id,
            )
        )
        lease_rows = existing_result.fetchall()
        
        is_lease_sync = template.kontracts_endpoint and "leases" in template.kontracts_endpoint.lower()
        already_synced = {row[0] for row in lease_rows} if is_lease_sync else set()
        
        lease_map = {}
        for row in lease_rows:
            lease_map[str(row[0])] = row[2]
            if row[1]:
                lease_map[str(row[1])] = row[2]
        engine_context = {"lease_mappings": lease_map}

        await self._log(
            run_id, LogLevel.info,
            f"{len(already_synced)} records already synced — will skip duplicates" if is_lease_sync
            else "Payment sync run — skipping lease deduplication check",
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
                
                # If fetch_associated is enabled, fetch associated records concurrently for this batch
                if template.fetch_associated and template.assoc_string:
                    async def _enrich_record(rec):
                        rid = str(
                            rec.get("triRecordId",
                            rec.get("triRecordIdSY",
                            rec.get("id",
                            rec.get("recordId", ""))))
                        )
                        if rid:
                            assocs = await tririga_client.get_associated_records(
                                record_id=int(rid),
                                association_name=template.assoc_string,
                            )
                            if assocs:
                                first_assoc = assocs[0]
                                rec["Associated"] = {
                                    "triRecordId": str(first_assoc.get("associatedRecordId", "")),
                                    "triRecordIdSY": str(first_assoc.get("associatedRecordId", "")),
                                    "triIdTX": first_assoc.get("associatedRecordName", ""),
                                    "triNameTX": first_assoc.get("associatedRecordName", ""),
                                    "id": str(first_assoc.get("associatedRecordId", "")),
                                }
                            else:
                                rec["Associated"] = {}
                        else:
                            rec["Associated"] = {}

                    enrich_tasks = [_enrich_record(r) for r in batch]
                    await asyncio.gather(*enrich_tasks)
                
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

            # 2. Push all valid payloads to Kontracts in chunked bulk requests!
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

                                if is_lease_sync:
                                    self.db.add(LeaseMapping(
                                        tririga_lease_id=tririga_lease_id,
                                        tririga_record_id=tririga_record_id,
                                        kontracts_id=kontracts_id,
                                    ))
                                
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
                
                # If fetch_associated is enabled, fetch associated records concurrently for this batch
                if template.fetch_associated and template.assoc_string:
                    async def _enrich_record(rec):
                        rid = str(
                            rec.get("triRecordId",
                            rec.get("triRecordIdSY",
                            rec.get("id",
                            rec.get("recordId", ""))))
                        )
                        if rid:
                            assocs = await tririga_client.get_associated_records(
                                record_id=int(rid),
                                association_name=template.assoc_string,
                            )
                            if assocs:
                                first_assoc = assocs[0]
                                rec["Associated"] = {
                                    "triRecordId": str(first_assoc.get("associatedRecordId", "")),
                                    "triRecordIdSY": str(first_assoc.get("associatedRecordId", "")),
                                    "triIdTX": first_assoc.get("associatedRecordName", ""),
                                    "triNameTX": first_assoc.get("associatedRecordName", ""),
                                    "id": str(first_assoc.get("associatedRecordId", "")),
                                }
                            else:
                                rec["Associated"] = {}
                        else:
                            rec["Associated"] = {}

                    enrich_tasks = [_enrich_record(r) for r in batch]
                    await asyncio.gather(*enrich_tasks)
                
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

                # 2. Push to Kontracts concurrently (this is the slow network part!)
                async def push_single_record(record_id, source_record, mapped_payload):
                    try:
                        res = await kontracts_client.push_record(
                            endpoint=template.kontracts_endpoint or "/api/v1/leases/",
                            method=template.kontracts_method or "POST",
                            payload=mapped_payload,
                        )
                        return {"status": "success", "record_id": record_id, "source_record": source_record, "mapped_payload": mapped_payload, "result": res}
                    except Exception as e:
                        return {"status": "failed", "record_id": record_id, "source_record": source_record, "mapped_payload": mapped_payload, "error": str(e)}

                push_tasks = [
                    push_single_record(rid, src, pl)
                    for rid, src, pl in tasks_to_run
                ]
                
                results = await asyncio.gather(*push_tasks)

                # 3. Process and write results serially (safe for SQLAlchemy)
                for res in results:
                    record_id = res["record_id"]
                    source_record = res["source_record"]
                    mapped_payload = res["mapped_payload"]
                    
                    if res["status"] == "success":
                        result_data = res["result"]
                        kontracts_id = str(result_data.get("id", "unknown"))
                        tririga_lease_id = str(result_data.get("lease_id", ""))
                        tririga_record_id = record_id

                        if is_lease_sync:
                            self.db.add(LeaseMapping(
                                tririga_lease_id=tririga_lease_id,
                                tririga_record_id=tririga_record_id,
                                kontracts_id=kontracts_id,
                            ))
                        
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
                            f"Record {record_id} -> Kontracts {kontracts_id} (success)",
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
        await self.db.flush()

        # Also emit to Python logging
        python_level = {
            LogLevel.debug: logging.DEBUG,
            LogLevel.info: logging.INFO,
            LogLevel.warning: logging.WARNING,
            LogLevel.error: logging.ERROR,
        }.get(level, logging.INFO)
        logger.log(python_level, f"[run={run_id}] [{component}] {message}")
