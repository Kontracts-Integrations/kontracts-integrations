"""Factory: build the right SourceConnector for a given connection type."""
from typing import Any, Dict, Optional

from app.models.connection import ConnectionType
from app.source_connectors.base import SourceConnector


def build_source_connector(
    connection_type: str,
    base_url: str,
    credentials: Dict[str, Any],
    demo_mode: bool = False,
) -> SourceConnector:
    """Instantiate and return the correct SourceConnector subclass."""
    ct = connection_type

    if ct == ConnectionType.tririga:
        from app.tririga_client.client import TririgaClient
        from app.source_connectors.tririga import TririgaSourceConnector
        client = TririgaClient(
            base_url=base_url,
            username=credentials.get("username", ""),
            password=credentials.get("password", ""),
            wsdl_path=credentials.get("wsdl_path", "/ws/TririgaWS?wsdl"),
            demo_mode=demo_mode,
        )
        return TririgaSourceConnector(client)

    if ct == ConnectionType.sap_re:
        from app.source_connectors.sap_re import SapReSourceConnector
        return SapReSourceConnector(base_url=base_url, credentials=credentials)

    if ct == ConnectionType.planon:
        from app.source_connectors.planon import PlanonSourceConnector
        return PlanonSourceConnector(base_url=base_url, credentials=credentials)

    if ct == ConnectionType.costar:
        from app.source_connectors.costar import CoStarSourceConnector
        return CoStarSourceConnector(base_url=base_url, credentials=credentials)

    if ct == ConnectionType.servicenow_wsd:
        from app.source_connectors.servicenow_wsd import ServiceNowWsdSourceConnector
        return ServiceNowWsdSourceConnector(base_url=base_url, credentials=credentials)

    raise ValueError(f"Unknown source connection type: {connection_type!r}")
