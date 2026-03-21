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
