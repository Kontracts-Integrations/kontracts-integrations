from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.sync_run import RecordStatus, RunStatus


class SyncRunCreate(BaseModel):
    mapping_template_id: int
    triggered_by: Optional[str] = Field(default="api")


class SyncRunResponse(BaseModel):
    id: int
    mapping_template_id: Optional[int]
    status: RunStatus
    triggered_by: Optional[str]
    total_records: Optional[int]
    success_count: int
    failed_count: int
    skipped_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncRecordResponse(BaseModel):
    id: int
    run_id: int
    tririga_record_id: Optional[str]
    kontracts_record_id: Optional[str]
    status: RecordStatus
    source_data: Optional[Dict[str, Any]]
    mapped_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LogEntryResponse(BaseModel):
    id: int
    run_id: Optional[int]
    level: str
    message: str
    component: Optional[str]
    extra: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncRunDetailResponse(SyncRunResponse):
    records: List[SyncRecordResponse] = []
    logs: List[LogEntryResponse] = []
