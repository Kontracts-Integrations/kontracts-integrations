"""
Normalize SOAP responses (zeep objects) to plain Python dicts/lists.
"""
from typing import Any, Dict, List


def normalize_soap_response(obj: Any) -> Any:
    """
    Recursively convert zeep objects, CompoundValue, and similar types
    to plain Python dicts/lists suitable for JSON serialization.
    """
    # First, use zeep's own serializer to convert all zeep types to plain Python
    try:
        from zeep.helpers import serialize_object
        obj = serialize_object(obj)
    except Exception:
        pass

    if obj is None:
        return None

    if isinstance(obj, dict):
        return {k: normalize_soap_response(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [normalize_soap_response(item) for item in obj]

    # Scalars (str, int, float, bool, Decimal, datetime, etc.)
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


def normalize_dynamic_query_response(obj: Any) -> List[Dict[str, Any]]:
    """
    Normalize the result of a TRIRIGA runDynamicQuery call into a list of records.
    Handles the queryResponseHelpers structure returned by the TRIRIGA SOAP API.
    """
    normalized = normalize_soap_response(obj)

    if normalized is None:
        return []

    if isinstance(normalized, list):
        return normalized

    if isinstance(normalized, dict):
        # Unwrap zeep's <out> envelope if present
        if "out" in normalized and isinstance(normalized["out"], dict):
            normalized = normalized["out"]

        # Primary TRIRIGA runDynamicQuery structure:
        # { queryResponseHelpers: { QueryResponseHelper: [ { queryResponseColumns: { QueryResponseColumn: [...] } } ] } }
        helpers_wrapper = normalized.get("queryResponseHelpers")
        if helpers_wrapper:
            helpers = helpers_wrapper.get("QueryResponseHelper", []) if isinstance(helpers_wrapper, dict) else helpers_wrapper
            if isinstance(helpers, dict):
                helpers = [helpers]
            result = []
            for helper in (helpers or []):
                if not isinstance(helper, dict):
                    continue
                record = {
                    "triRecordId": helper.get("recordId"),
                    "triBoId": helper.get("boId"),
                }
                cols_wrapper = helper.get("queryResponseColumns", {})
                cols = cols_wrapper.get("QueryResponseColumn", []) if isinstance(cols_wrapper, dict) else []
                if isinstance(cols, dict):
                    cols = [cols]
                for col in (cols or []):
                    if isinstance(col, dict):
                        name = col.get("name") or col.get("label")
                        if name:
                            record[name] = col.get("value")
                result.append(record)
            return result

        # columnHeaders + rowData fallback
        if "columnHeaders" in normalized or "rowData" in normalized:
            headers = normalized.get("columnHeaders") or []
            rows = normalized.get("rowData") or []
            if isinstance(headers, list) and isinstance(rows, list):
                result = []
                for row in rows:
                    record = {}
                    values = row.get("values", []) if isinstance(row, dict) else []
                    if isinstance(values, dict):
                        values = list(values.values())
                    for i, header in enumerate(headers):
                        field_name = (
                            header.get("fieldName", header.get("name", f"field_{i}"))
                            if isinstance(header, dict)
                            else str(header)
                        )
                        record[field_name] = values[i] if i < len(values) else None
                    result.append(record)
                return result

        # Flat list nested under a common key
        for key in ("queryResultList", "records", "item", "result", "rowData"):
            if key in normalized:
                val = normalized[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    return [val]

        return [normalized]

    return []


def _unwrap_single_key(obj: Any) -> Any:
    """If a dict has exactly one key whose value is a list, return that list."""
    if isinstance(obj, dict) and len(obj) == 1:
        val = next(iter(obj.values()))
        if isinstance(val, list):
            return val
    return obj


def extract_fields(normalized: Any) -> List[Dict[str, Any]]:
    """
    Extract field definitions from a normalized getObjectTypeByName response.
    Returns a list of {name, label, type, required} dicts.

    TRIRIGA structure:
      sections → {"Section": [...]} → each section → fields → {"Field": [...]}
    """
    fields = []

    if isinstance(normalized, dict):
        # Resolve sections — may be {"Section": [...]} or a plain list
        raw_sections = normalized.get(
            "sections",
            normalized.get("fieldSections", normalized.get("fields", []))
        )
        section_list = _unwrap_single_key(raw_sections) if isinstance(raw_sections, dict) else raw_sections

        if isinstance(section_list, list):
            for section in section_list:
                if not isinstance(section, dict):
                    continue
                section_name = section.get("sectionLabel", section.get("label", section.get("name", "General")))
                # Resolve fields — may be {"Field": [...]} or a plain list
                raw_fields = section.get("fields", section.get("field", []))
                field_list = _unwrap_single_key(raw_fields) if isinstance(raw_fields, dict) else raw_fields

                if isinstance(field_list, list):
                    for f in field_list:
                        field = _normalize_field(f)
                        field["section"] = section_name
                        fields.append(field)
                elif isinstance(field_list, dict):
                    field = _normalize_field(field_list)
                    field["section"] = section_name
                    fields.append(field)

    if not fields:
        fields = _get_default_fields()

    return fields


def _normalize_field(field: Any) -> Dict[str, Any]:
    if not isinstance(field, dict):
        return {"name": str(field), "label": str(field), "type": "string"}
    raw_type = field.get("type") or field.get("dataType") or "string"
    if isinstance(raw_type, dict):
        raw_type = raw_type.get("type") or raw_type.get("typeCode") or "string"
    return {
        "name": field.get("fieldName", field.get("name", "unknown")),
        "label": field.get("fieldLabel", field.get("label", field.get("name", "unknown"))),
        "type": raw_type,
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
