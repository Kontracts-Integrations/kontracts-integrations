from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.connection import ConnectionType


class TririgaCredentials(BaseModel):
    username: str = Field(..., description="TRIRIGA username")
    password: str = Field(..., description="TRIRIGA password")
    wsdl_path: str = Field(
        default="/ws/TririgaWS?wsdl", description="WSDL path"
    )


class KontractsCredentials(BaseModel):
    auth0_domain: str = Field(..., description="Auth0 domain")
    client_id: str = Field(..., description="Auth0 client ID")
    client_secret: str = Field(..., description="Auth0 client secret")
    audience: str = Field(..., description="Auth0 audience / API identifier")


class ConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    connection_type: ConnectionType
    base_url: str = Field(..., description="Base URL of the service")
    credentials: Dict[str, Any] = Field(
        ..., description="Credentials dict (will be encrypted)"
    )


class ConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ConnectionResponse(BaseModel):
    id: int
    name: str
    connection_type: ConnectionType
    base_url: Optional[str]
    is_active: bool
    last_tested_at: Optional[datetime]
    last_test_success: Optional[bool]
    last_test_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
