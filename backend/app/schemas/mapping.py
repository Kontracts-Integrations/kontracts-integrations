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
    use_associated: bool = Field(default=False)
    description: Optional[str] = None


class SourceFilter(BaseModel):
    field: str = Field(..., description="Source field name / path to filter on")
    operator: str = Field(
        default="equals",
        description=(
            "One of: equals, not_equals, contains, not_contains, starts_with, "
            "ends_with, is_empty, is_not_empty, greater_than, less_than, gte, lte, regex"
        ),
    )
    value: Optional[str] = Field(
        default=None, description="Comparison value (ignored for is_empty/is_not_empty)"
    )


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
    lookup_table_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Named table this mapping writes produced IDs into for subsequent lookups",
    )
    update_existing: bool = Field(
        default=False,
        description="Update already-synced records whose payload changed instead of skipping",
    )
    source_filters: List[SourceFilter] = Field(default_factory=list)
    filter_match: str = Field(default="all", pattern="^(all|any)$")
    field_mappings: List[FieldMapping] = Field(default_factory=list)
    fetch_associated: bool = False
    assoc_module: Optional[str] = None
    assoc_object: Optional[str] = None
    assoc_string: Optional[str] = None


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
    lookup_table_name: Optional[str] = Field(default=None, max_length=255)
    update_existing: Optional[bool] = None
    source_filters: Optional[List[SourceFilter]] = None
    filter_match: Optional[str] = Field(default=None, pattern="^(all|any)$")
    field_mappings: Optional[List[FieldMapping]] = None
    is_active: Optional[bool] = None
    fetch_associated: Optional[bool] = None
    assoc_module: Optional[str] = None
    assoc_object: Optional[str] = None
    assoc_string: Optional[str] = None


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
    lookup_table_name: Optional[str] = None
    update_existing: bool = False
    source_filters: List[SourceFilter] = Field(default_factory=list)
    filter_match: str = "all"
    fetch_associated: bool = False
    assoc_module: Optional[str] = None
    assoc_object: Optional[str] = None
    assoc_string: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    current_version: Optional[MappingVersionResponse] = None

    model_config = {"from_attributes": True}
