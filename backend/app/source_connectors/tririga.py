"""TRIRIGA source connector — wraps the existing TririgaClient."""
from typing import Any, Dict, List, Optional, Tuple

from app.source_connectors.base import SourceConnector


class TririgaSourceConnector(SourceConnector):
    def __init__(self, client):  # client: TririgaClient
        self._client = client

    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        return await self._client.test_connection()

    async def get_objects(self) -> List[Dict[str, Any]]:
        return await self._client.get_modules()

    async def get_object_fields(self, object_name: str) -> List[Dict[str, Any]]:
        return await self._client.get_module_fields(object_name)

    async def run_query(
        self,
        object_name: str,
        query_name: str,
        filters: Dict[str, Any],
        max_records: int = 100,
    ) -> List[Dict[str, Any]]:
        return await self._client.run_named_query(
            module_name=object_name,
            query_name=query_name,
            filters=filters,
            max_records=max_records,
        )
