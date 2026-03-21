"""
Sync service: orchestrates fetching TRIRIGA data, mapping, validating,
pushing to Kontracts, and logging results.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
            raise

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

        # Fetch TRIRIGA data
        await self._log(
            run_id,
            LogLevel.info,
            f"Fetching TRIRIGA data: module={template.tririga_module}, "
            f"query={template.tririga_query_name}",
            "tririga_client",
        )

        records = await tririga_client.run_named_query(
            module_name=template.tririga_module or "",
            query_name=template.tririga_query_name or "",
            filters={},
            max_records=500,
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
        field_mappings_data = version.field_mappings.get("mappings", [])
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

        # Process each record
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for i, source_record in enumerate(records):
            record_id = str(
                source_record.get("triRecordIdSY",
                source_record.get("id",
                source_record.get("recordId", f"record_{i}")))
            )

            try:
                # Apply mapping
                mapped_payload, warnings = engine.apply(source_record)

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
                if schema_fields:
                    is_valid, val_errors = engine.validate(mapped_payload, schema_fields)
                    if not is_valid:
                        error_msgs = [e.to_dict() for e in val_errors]
                        await self._log(
                            run_id,
                            LogLevel.warning,
                            f"Record {record_id} validation warnings: {error_msgs}",
                            "validators",
                        )

                # Push to Kontracts
                result = await kontracts_client.push_record(
                    endpoint=template.kontracts_endpoint or "/api/v1/leases/",
                    method=template.kontracts_method or "POST",
                    payload=mapped_payload,
                )

                kontracts_id = str(
                    result.get("id", result.get("lease_id", "unknown"))
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
                    f"Record {record_id} -> Kontracts {kontracts_id} (success)",
                    "sync_service",
                    extra={"tririga_id": record_id, "kontracts_id": kontracts_id},
                )

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                logger.error(
                    f"Record {record_id} failed: {error_msg}", exc_info=True
                )
                await self._save_record(
                    run_id=run_id,
                    tririga_id=record_id,
                    status=RecordStatus.failed,
                    source_data=source_record,
                    error=error_msg,
                )
                await self._log(
                    run_id,
                    LogLevel.error,
                    f"Record {record_id} failed: {error_msg}",
                    "sync_service",
                    extra={"record_id": record_id},
                )

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
            select(MappingTemplate)
            .where(MappingTemplate.id == template_id)
            .options(selectinload(MappingTemplate.versions))
        )
        template = result.scalar_one_or_none()
        if not template:
            return None, None

        raw = template.versions
        versions: list = raw if isinstance(raw, list) else ([raw] if raw is not None else [])

        current_version = None
        for v in versions:
            if v.is_current:
                current_version = v
                break
        if not current_version and versions:
            current_version = versions[0]

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
