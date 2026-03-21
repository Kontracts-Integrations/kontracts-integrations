"""
Parse WSDL structure from zeep client to extract operations and type definitions.
"""
from typing import Any, Dict, List


def extract_wsdl_structure(zeep_client) -> Dict[str, Any]:
    """
    Extract the full WSDL structure from an initialized zeep client.
    Returns operations, types, and service info.
    """
    structure: Dict[str, Any] = {
        "services": [],
        "operations": [],
        "types": {},
    }

    try:
        wsdl = zeep_client.wsdl
        for service_name, service in wsdl.services.items():
            service_info: Dict[str, Any] = {
                "name": service_name,
                "ports": [],
            }
            for port_name, port in service.ports.items():
                port_info: Dict[str, Any] = {
                    "name": port_name,
                    "operations": [],
                }
                binding = port.binding
                for op_name, operation in binding.all().items():
                    op_info = _extract_operation_info(op_name, operation)
                    port_info["operations"].append(op_info)
                    structure["operations"].append(op_info)
                service_info["ports"].append(port_info)
            structure["services"].append(service_info)
    except Exception as e:
        structure["parse_error"] = str(e)

    return structure


def _extract_operation_info(name: str, operation) -> Dict[str, Any]:
    op_info: Dict[str, Any] = {
        "name": name,
        "input": {},
        "output": {},
    }
    try:
        if hasattr(operation, "input") and operation.input is not None:
            op_info["input"] = _extract_message_info(operation.input)
    except Exception:
        pass
    try:
        if hasattr(operation, "output") and operation.output is not None:
            op_info["output"] = _extract_message_info(operation.output)
    except Exception:
        pass
    return op_info


def _extract_message_info(message) -> Dict[str, Any]:
    info: Dict[str, Any] = {"parts": []}
    try:
        if hasattr(message, "body") and message.body is not None:
            element = message.body
            if hasattr(element, "type") and element.type is not None:
                info["parts"] = _extract_type_parts(element.type)
    except Exception:
        pass
    return info


def _extract_type_parts(xsd_type, depth: int = 0) -> List[Dict[str, Any]]:
    if depth > 5:
        return []

    parts = []
    try:
        if hasattr(xsd_type, "elements"):
            for name, element in xsd_type.elements:
                part: Dict[str, Any] = {
                    "name": name,
                    "type": str(getattr(element, "type", "unknown")),
                    "min_occurs": getattr(element, "min_occurs", 0),
                    "max_occurs": getattr(element, "max_occurs", 1),
                }
                # Recurse into complex types
                if hasattr(element, "type") and hasattr(element.type, "elements"):
                    part["children"] = _extract_type_parts(element.type, depth + 1)
                parts.append(part)
    except Exception:
        pass
    return parts


async def parse_wsdl_operations(tririga_client) -> List[Dict[str, Any]]:
    """Return known TRIRIGA SOAP operations (static list augmented with WSDL introspection)."""
    known_ops = [
        {"name": "runNamedQuery", "category": "query", "description": "Run a saved named query"},
        {"name": "runDynamicQuery", "category": "query", "description": "Run an ad-hoc query"},
        {"name": "runNamedMetricQuery", "category": "query", "description": "Run a metrics query"},
        {"name": "keywordSearch", "category": "query", "description": "Full-text search"},
        {"name": "saveRecord", "category": "record", "description": "Create or update a record"},
        {"name": "getRecordState", "category": "record", "description": "Get record workflow state"},
        {"name": "getRecordDataHeaders", "category": "record", "description": "Get record field headers"},
        {"name": "copy", "category": "record", "description": "Copy a record"},
        {"name": "getGUI", "category": "ui", "description": "Get GUI definition"},
        {"name": "getDefaultGUIStructure", "category": "ui", "description": "Get default GUI structure"},
        {"name": "getGUIStateTransitions", "category": "ui", "description": "Get GUI state transitions"},
        {"name": "getGUIsByName", "category": "ui", "description": "Find GUIs by name"},
        {"name": "associateRecords", "category": "association", "description": "Associate two records"},
        {"name": "deassociateRecords", "category": "association", "description": "Remove record association"},
        {"name": "getAssociatedRecords", "category": "association", "description": "Get associated records"},
        {"name": "getAssociationDefinitions", "category": "association", "description": "Get association types"},
        {"name": "upload", "category": "document", "description": "Upload a document"},
        {"name": "uploadFrom", "category": "document", "description": "Upload from URL"},
        {"name": "download", "category": "document", "description": "Download a document"},
        {"name": "downloadTo", "category": "document", "description": "Download to URL"},
        {"name": "delete", "category": "document", "description": "Delete a document"},
        {"name": "getModules", "category": "meta", "description": "List all modules"},
        {"name": "getObjectType", "category": "meta", "description": "Get object type by ID"},
        {"name": "getObjectTypeByName", "category": "meta", "description": "Get object type by name"},
        {"name": "getHierarchyMetadata", "category": "meta", "description": "Get hierarchy metadata"},
        {"name": "getProjects", "category": "project", "description": "List projects"},
        {"name": "getProjectId", "category": "project", "description": "Get project ID"},
        {"name": "getAvailableActions", "category": "workflow", "description": "Get available workflow actions"},
        {"name": "triggerActions", "category": "workflow", "description": "Trigger workflow actions"},
        {"name": "getCurrencies", "category": "currency", "description": "List currencies"},
        {"name": "getCurrencyConversionRates", "category": "currency", "description": "Get conversion rates"},
        {"name": "getApplicationInfo", "category": "session", "description": "Get application info"},
        {"name": "getUserLicenses", "category": "session", "description": "Get user licenses"},
    ]
    return known_ops
