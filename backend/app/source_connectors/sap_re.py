"""SAP RE-FX source connector stub."""
from typing import Any, Dict, List, Optional, Tuple

from app.source_connectors.base import SourceConnector

DEMO_OBJECTS = [
    {"name": "RealEstateContract", "label": "Real Estate Contract", "category": "Contracts"},
    {"name": "RentalObject", "label": "Rental Object", "category": "Objects"},
    {"name": "BusinessEntity", "label": "Business Entity", "category": "Master Data"},
]

DEMO_FIELDS = {
    "RealEstateContract": [
        {"name": "ContractNumber", "label": "Contract Number", "type": "string", "required": True},
        {"name": "ContractType", "label": "Contract Type", "type": "string", "required": True},
        {"name": "StartDate", "label": "Start Date", "type": "date", "required": True},
        {"name": "EndDate", "label": "End Date", "type": "date", "required": False},
        {"name": "AnnualRent", "label": "Annual Rent", "type": "decimal", "required": False},
        {"name": "Currency", "label": "Currency", "type": "string", "required": False},
    ],
    "RentalObject": [
        {"name": "RentalObjectId", "label": "Rental Object ID", "type": "string", "required": True},
        {"name": "Description", "label": "Description", "type": "string", "required": False},
        {"name": "Area", "label": "Area", "type": "decimal", "required": False},
        {"name": "AreaUnit", "label": "Area Unit", "type": "string", "required": False},
    ],
}


class SapReSourceConnector(SourceConnector):
    def __init__(self, base_url: str, credentials: Dict[str, Any]):
        self.base_url = base_url
        self.credentials = credentials

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        return True, "SAP RE-FX connector (stub) — not yet implemented", {"mode": "stub"}

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
            {"ContractNumber": "RE-001", "ContractType": "Lease", "StartDate": "2024-01-01", "AnnualRent": 120000},
            {"ContractNumber": "RE-002", "ContractType": "Lease", "StartDate": "2024-03-01", "AnnualRent": 85000},
        ][:max_records]
