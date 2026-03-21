"""Planon source connector stub."""
from typing import Any, Dict, List, Optional, Tuple

from app.source_connectors.base import SourceConnector

DEMO_OBJECTS = [
    {"name": "Lease", "label": "Lease", "category": "Contracts"},
    {"name": "Property", "label": "Property", "category": "Real Estate"},
    {"name": "Space", "label": "Space", "category": "Space Management"},
]

DEMO_FIELDS = {
    "Lease": [
        {"name": "Code", "label": "Lease Code", "type": "string", "required": True},
        {"name": "Description", "label": "Description", "type": "string", "required": False},
        {"name": "StartDate", "label": "Start Date", "type": "date", "required": True},
        {"name": "ExpirationDate", "label": "Expiration Date", "type": "date", "required": False},
        {"name": "AnnualRentAmount", "label": "Annual Rent", "type": "decimal", "required": False},
    ],
}


class PlanonSourceConnector(SourceConnector):
    def __init__(self, base_url: str, credentials: Dict[str, Any]):
        self.base_url = base_url
        self.credentials = credentials

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        return True, "Planon connector (stub) — not yet implemented", {"mode": "stub"}

    async def get_objects(self) -> List[Dict[str, Any]]:
        return DEMO_OBJECTS

    async def get_object_fields(self, object_name: str) -> List[Dict[str, Any]]:
        return DEMO_FIELDS.get(object_name, [
            {"name": "id", "label": "ID", "type": "string", "required": True},
            {"name": "name", "label": "Name", "type": "string", "required": False},
        ])

    async def run_query(
        self, object_name: str, query_name: str, filters: Dict[str, Any], max_records: int = 100
    ) -> List[Dict[str, Any]]:
        return [
            {"Code": "PL-LEASE-001", "Description": "Office Space - Floor 3", "StartDate": "2023-01-01", "AnnualRentAmount": 200000},
        ][:max_records]
