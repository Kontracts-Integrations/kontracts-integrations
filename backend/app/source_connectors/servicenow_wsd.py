"""ServiceNow Workplace Service Delivery source connector stub."""
from typing import Any, Dict, List, Optional, Tuple

from app.source_connectors.base import SourceConnector

DEMO_OBJECTS = [
    {"name": "ast_contract", "label": "Contract", "category": "Contracts"},
    {"name": "ast_ci", "label": "Location / Space", "category": "Asset Management"},
    {"name": "cmn_location", "label": "Location", "category": "Master Data"},
]

DEMO_FIELDS = {
    "ast_contract": [
        {"name": "number", "label": "Contract Number", "type": "string", "required": True},
        {"name": "short_description", "label": "Description", "type": "string", "required": False},
        {"name": "starts", "label": "Start Date", "type": "date", "required": True},
        {"name": "ends", "label": "End Date", "type": "date", "required": False},
        {"name": "value", "label": "Contract Value", "type": "decimal", "required": False},
        {"name": "vendor", "label": "Vendor", "type": "reference", "required": False},
    ],
}


class ServiceNowWsdSourceConnector(SourceConnector):
    def __init__(self, base_url: str, credentials: Dict[str, Any]):
        self.base_url = base_url
        self.credentials = credentials

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        return True, "ServiceNow WSD connector (stub) — not yet implemented", {"mode": "stub"}

    async def get_objects(self) -> List[Dict[str, Any]]:
        return DEMO_OBJECTS

    async def get_object_fields(self, object_name: str) -> List[Dict[str, Any]]:
        return DEMO_FIELDS.get(object_name, [
            {"name": "sys_id", "label": "Sys ID", "type": "string", "required": True},
            {"name": "name", "label": "Name", "type": "string", "required": False},
        ])

    async def run_query(
        self, object_name: str, query_name: str, filters: Dict[str, Any], max_records: int = 100
    ) -> List[Dict[str, Any]]:
        return [
            {"number": "CNTR0001", "short_description": "Office Lease - HQ", "starts": "2021-01-01", "value": 500000},
        ][:max_records]
