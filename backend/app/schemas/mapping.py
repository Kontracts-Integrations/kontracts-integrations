from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    id: str = Field(..., description="Unique ID for this mapping row")
    source_field: str = Field(..., description="Source system field name / path")
    target_field: str = Field(..., description="Kontracts field name / path")
    transform_type: str = Field(
        default="direct",
        description=(
            "Transform type: direct, constant, date_format, number_convert, "
            "boolean_convert, string_template, lookup_table, json_path"
        ),
    )
    transform_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Transform-specific configuration",
    )
    is_required: bool = Field(default=False)
    description: Optional[str] = None


class MappingTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_connection_id: Optional[int] = None
    target_connection_id: Optional[int] = None
    source_module: Optional[str] = None
    source_object: Optional[str] = None
    source_query: Optional[str] = None
    kontracts_endpoint: Optional[str] = None
    kontracts_method: Optional[str] = Field(default="POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    field_mappings: List[FieldMapping] = Field(default_factory=list)


class MappingTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    source_connection_id: Optional[int] = None
    target_connection_id: Optional[int] = None
    source_module: Optional[str] = None
    source_object: Optional[str] = None
    source_query: Optional[str] = None
    kontracts_endpoint: Optional[str] = None
    kontracts_method: Optional[str] = None
    field_mappings: Optional[List[FieldMapping]] = None
    is_active: Optional[bool] = None


class MappingVersionResponse(BaseModel):
    id: int
    template_id: int
    version_number: int
    field_mappings: Dict[str, Any]
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MappingTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_connection_id: Optional[int]
    target_connection_id: Optional[int]
    source_module: Optional[str]
    source_object: Optional[str]
    source_query: Optional[str]
    kontracts_endpoint: Optional[str]
    kontracts_method: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    current_version: Optional[MappingVersionResponse] = None

    model_config = {"from_attributes": True}
