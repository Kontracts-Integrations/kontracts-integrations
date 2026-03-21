"""
Normalize SOAP responses (zeep objects) to plain Python dicts/lists.
"""
from typing import Any, Dict, List


def normalize_soap_response(obj: Any) -> Any:
    """
    Recursively convert zeep objects, CompoundValue, and similar types
    to plain Python dicts/lists suitable for JSON serialization.
    """
    if obj is None:
        return None

    # Handle zeep CompoundValue (looks like a dict)
    type_name = type(obj).__name__
    if type_name in ("CompoundValue", "AnyObject"):
        result = {}
        for key in obj:
            result[key] = normalize_soap_response(obj[key])
        return result

    # Handle zeep ArrayOfXxx
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, dict)):
        try:
            return [normalize_soap_response(item) for item in obj]
        except TypeError:
            pass

    # Handle regular dicts
    if isinstance(obj, dict):
        return {k: normalize_soap_response(v) for k, v in obj.items()}

    # Handle lists
    if isinstance(obj, list):
        return [normalize_soap_response(item) for item in obj]

    # Scalars
    return obj


def normalize_query_response(obj: Any) -> List[Dict[str, Any]]:
    """
    Normalize the result of a TRIRIGA runNamedQuery call into a list of records.
    TRIRIGA returns a QueryResult with rowData, columnHeaders, etc.
    """
    normalized = normalize_soap_response(obj)

    if normalized is None:
        return []

    if isinstance(normalized, list):
        return normalized

    if isinstance(normalized, dict):
        # Look for common TRIRIGA result wrappers
        for key in ("queryResultList", "rowData", "records", "item", "result"):
            if key in normalized:
                val = normalized[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    return [val]

        # If it has columnHeaders + rowData structure
        if "columnHeaders" in normalized and "rowData" in normalized:
            headers = normalized["columnHeaders"]
            rows = normalized["rowData"]
            if isinstance(headers, list) and isinstance(rows, list):
                result = []
                for row in rows:
                    record = {}
                    values = row.get("values", row) if isinstance(row, dict) else []
                    for i, header in enumerate(headers):
                        field_name = (
                            header.get("fieldLabel", header.get("name", f"field_{i}"))
                            if isinstance(header, dict)
                            else str(header)
                        )
                        record[field_name] = values[i] if i < len(values) else None
                    result.append(record)
                return result

        return [normalized]

    return []


def extract_fields(normalized: Any) -> List[Dict[str, Any]]:
    """
    Extract field definitions from a normalized getObjectTypeByName response.
    Returns a list of {name, label, type, required} dicts.
    """
    fields = []

    if isinstance(normalized, dict):
        field_sections = normalized.get(
            "fieldSections",
            normalized.get("sections", normalized.get("fields", []))
        )
        if isinstance(field_sections, list):
            for section in field_sections:
                if isinstance(section, dict):
                    section_fields = section.get("fields", section.get("field", []))
                    if isinstance(section_fields, list):
                        for f in section_fields:
                            fields.append(_normalize_field(f))
                    elif isinstance(section_fields, dict):
                        fields.append(_normalize_field(section_fields))
        elif isinstance(field_sections, dict):
            fields.append(_normalize_field(field_sections))

    if not fields:
        # Return a set of common TRIRIGA fields as fallback
        fields = _get_default_fields()

    return fields


def _normalize_field(field: Any) -> Dict[str, Any]:
    if not isinstance(field, dict):
        return {"name": str(field), "label": str(field), "type": "string"}
    return {
        "name": field.get("fieldName", field.get("name", "unknown")),
        "label": field.get("fieldLabel", field.get("label", field.get("name", "unknown"))),
        "type": field.get("dataType", field.get("type", "string")),
        "required": field.get("required", False),
        "read_only": field.get("readOnly", False),
    }


def _get_default_fields() -> List[Dict[str, Any]]:
    return [
        {"name": "tririgaRecordId", "label": "Record ID", "type": "number", "required": True},
        {"name": "tririgaSpecId", "label": "Spec ID", "type": "number", "required": True},
        {"name": "name", "label": "Name", "type": "string", "required": True},
        {"name": "status", "label": "Status", "type": "string", "required": False},
        {"name": "createdDate", "label": "Created Date", "type": "datetime", "required": False},
        {"name": "modifiedDate", "label": "Modified Date", "type": "datetime", "required": False},
    ]
