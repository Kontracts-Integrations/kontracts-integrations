"""Abstract interface that every source-system connector must implement."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class SourceConnector(ABC):
    """Common interface for all IWMS source connectors."""

    @abstractmethod
    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Return (success, message, details)."""
        ...

    @abstractmethod
    async def get_objects(self) -> List[Dict[str, Any]]:
        """Return available objects / modules / business objects.
        Each item: {"name": str, "label": str, "category": str (optional)}
        """
        ...

    @abstractmethod
    async def get_object_fields(self, object_name: str) -> List[Dict[str, Any]]:
        """Return fields for a given object.
        Each item: {"name": str, "label": str, "type": str, "required": bool}
        """
        ...

    @abstractmethod
    async def run_query(
        self,
        object_name: str,
        query_name: str,
        filters: Dict[str, Any],
        max_records: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch records from the source system."""
        ...

    async def preview_records(
        self,
        object_name: str,
        module_name: Optional[str] = None,
        field_names: Optional[List[str]] = None,
        query_name: str = "",
        max_records: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch a small sample of records for the mapping preview.

        Default implementation defers to run_query. Connectors that fetch via a
        dynamic field query (rather than a named query) should override this so
        the preview matches how the sync actually pulls data.
        """
        return await self.run_query(object_name, query_name, {}, max_records)
