"""CoStar source connector stub."""
from typing import Any, Dict, List, Optional, Tuple

from app.source_connectors.base import SourceConnector

DEMO_OBJECTS = [
    {"name": "Lease", "label": "Lease", "category": "Contracts"},
    {"name": "Property", "label": "Property", "category": "Properties"},
    {"name": "Tenant", "label": "Tenant", "category": "Parties"},
]

DEMO_FIELDS = {
    "Lease": [
        {"name": "leaseId", "label": "Lease ID", "type": "string", "required": True},
        {"name": "propertyId", "label": "Property ID", "type": "string", "required": True},
        {"name": "tenantName", "label": "Tenant Name", "type": "string", "required": False},
        {"name": "commencementDate", "label": "Commencement Date", "type": "date", "required": True},
        {"name": "expirationDate", "label": "Expiration Date", "type": "date", "required": False},
        {"name": "baseRent", "label": "Base Rent", "type": "decimal", "required": False},
        {"name": "rentableArea", "label": "Rentable Area (SF)", "type": "decimal", "required": False},
    ],
}


class CoStarSourceConnector(SourceConnector):
    def __init__(self, base_url: str, credentials: Dict[str, Any]):
        self.base_url = base_url
        self.credentials = credentials

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        return True, "CoStar connector (stub) — not yet implemented", {"mode": "stub"}

    async def get_objects(self) -> List[Dict[str, Any]]:
        return DEMO_OBJECTS

    async def get_object_fields(self, object_name: str) -> List[Dict[str, Any]]:
        return DEMO_FIELDS.get(object_name, [
            {"name": "id", "label": "ID", "type": "string", "required": True},
        ])

    async def run_query(
        self, object_name: str, query_name: str, filters: Dict[str, Any], max_records: int = 100
    ) -> List[Dict[str, Any]]:
        return [
            {"leaseId": "CS-001", "tenantName": "Acme Corp", "commencementDate": "2022-06-01", "baseRent": 50.0, "rentableArea": 5000},
            {"leaseId": "CS-002", "tenantName": "Beta LLC", "commencementDate": "2023-01-01", "baseRent": 45.0, "rentableArea": 3200},
        ][:max_records]
