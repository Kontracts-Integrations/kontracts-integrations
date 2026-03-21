"""
Parse Kontracts OpenAPI schema to extract endpoint definitions and field schemas.
"""
from typing import Any, Dict, List, Optional

DEMO_OPENAPI_SCHEMA: Dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "Kontracts API", "version": "1.0.0"},
    "paths": {
        "/api/v1/leases/": {
            "post": {
                "summary": "Create a lease",
                "tags": ["leases"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LeaseCreate"}
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
            "get": {
                "summary": "List leases",
                "tags": ["leases"],
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v1/leases/{id}": {
            "get": {"summary": "Get lease", "tags": ["leases"]},
            "put": {
                "summary": "Update lease",
                "tags": ["leases"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LeaseCreate"}
                        }
                    }
                },
            },
            "delete": {"summary": "Delete lease", "tags": ["leases"]},
        },
        "/api/v1/payments/": {
            "post": {
                "summary": "Create payment",
                "tags": ["payments"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PaymentCreate"}
                        }
                    }
                },
            },
            "get": {"summary": "List payments", "tags": ["payments"]},
        },
        "/api/v1/schedules/": {
            "post": {
                "summary": "Create amortization schedule",
                "tags": ["schedules"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ScheduleCreate"}
                        }
                    }
                },
            },
            "get": {"summary": "List schedules", "tags": ["schedules"]},
        },
        "/api/v1/journal-entries/": {
            "post": {
                "summary": "Create journal entry",
                "tags": ["journal-entries"],
            },
            "get": {"summary": "List journal entries", "tags": ["journal-entries"]},
        },
    },
    "components": {
        "schemas": {
            "LeaseCreate": {
                "type": "object",
                "required": ["name", "lease_type", "commencement_date", "expiration_date"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Lease name or identifier",
                        "maxLength": 255,
                    },
                    "lease_type": {
                        "type": "string",
                        "enum": ["operating", "finance"],
                        "description": "ASC 842 / IFRS 16 classification",
                    },
                    "commencement_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Lease commencement date (YYYY-MM-DD)",
                    },
                    "expiration_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Lease expiration date (YYYY-MM-DD)",
                    },
                    "monthly_payment": {
                        "type": "number",
                        "format": "float",
                        "description": "Monthly payment amount",
                    },
                    "currency": {
                        "type": "string",
                        "default": "USD",
                        "description": "ISO 4217 currency code",
                    },
                    "discount_rate": {
                        "type": "number",
                        "format": "float",
                        "description": "Incremental borrowing rate as decimal (e.g. 0.035)",
                    },
                    "lessor_name": {
                        "type": "string",
                        "description": "Name of the lessor/landlord",
                    },
                    "lessee_name": {
                        "type": "string",
                        "description": "Name of the lessee/tenant",
                    },
                    "asset_description": {
                        "type": "string",
                        "description": "Description of the underlying asset",
                    },
                    "leased_area_sqft": {
                        "type": "number",
                        "format": "float",
                        "description": "Leased area in square feet",
                    },
                    "address_line1": {
                        "type": "string",
                        "description": "Property street address",
                    },
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "postal_code": {"type": "string"},
                    "country": {"type": "string"},
                    "has_renewal_options": {
                        "type": "boolean",
                        "description": "Whether renewal options exist",
                    },
                    "renewal_term_months": {
                        "type": "integer",
                        "description": "Renewal term in months",
                    },
                    "has_purchase_option": {
                        "type": "boolean",
                        "description": "Whether a purchase option exists",
                    },
                    "external_id": {
                        "type": "string",
                        "description": "External system record ID (e.g. TRIRIGA ID)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Metadata tags",
                    },
                },
            },
            "PaymentCreate": {
                "type": "object",
                "required": ["lease_id", "payment_date", "amount"],
                "properties": {
                    "lease_id": {"type": "string"},
                    "payment_date": {"type": "string", "format": "date"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "payment_type": {
                        "type": "string",
                        "enum": ["rent", "variable", "initial_direct_cost", "incentive"],
                    },
                    "description": {"type": "string"},
                },
            },
            "ScheduleCreate": {
                "type": "object",
                "required": ["lease_id"],
                "properties": {
                    "lease_id": {"type": "string"},
                    "accounting_standard": {
                        "type": "string",
                        "enum": ["ASC842", "IFRS16"],
                    },
                    "calculation_date": {"type": "string", "format": "date"},
                },
            },
        }
    },
}


def parse_openapi_endpoints(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a flat list of endpoints from an OpenAPI schema.
    Returns: [{path, method, summary, tags, has_request_body}]
    """
    endpoints = []
    paths = schema.get("paths", {})

    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation is None:
                continue

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": operation.get("summary", ""),
                "tags": operation.get("tags", []),
                "has_request_body": "requestBody" in operation,
                "operation_id": operation.get("operationId", f"{method}_{path.replace('/', '_')}"),
            })

    return endpoints


def parse_endpoint_schema(
    schema: Dict[str, Any], endpoint: str, method: str
) -> List[Dict[str, Any]]:
    """
    Extract field definitions for a specific endpoint/method from the OpenAPI schema.
    Returns: [{name, type, required, description, enum, format}]
    """
    paths = schema.get("paths", {})
    path_item = paths.get(endpoint, {})
    operation = path_item.get(method.lower(), {})

    if not operation:
        return []

    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema_ref = json_content.get("schema", {})

    # Resolve $ref
    resolved = _resolve_schema(schema_ref, schema)
    if not resolved:
        return []

    return _extract_schema_fields(resolved, schema, required_fields=resolved.get("required", []))


def _resolve_schema(
    schema_obj: Dict[str, Any], root_schema: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    if "$ref" in schema_obj:
        ref = schema_obj["$ref"]
        # Parse JSON reference like "#/components/schemas/LeaseCreate"
        parts = ref.lstrip("#/").split("/")
        current = root_schema
        for part in parts:
            current = current.get(part, {})
        return current
    return schema_obj


def _extract_schema_fields(
    schema_obj: Dict[str, Any],
    root_schema: Dict[str, Any],
    required_fields: Optional[List[str]] = None,
    prefix: str = "",
) -> List[Dict[str, Any]]:
    if required_fields is None:
        required_fields = schema_obj.get("required", [])

    fields = []
    properties = schema_obj.get("properties", {})

    for field_name, field_schema in properties.items():
        resolved = _resolve_schema(field_schema, root_schema)
        full_name = f"{prefix}{field_name}" if prefix else field_name

        field_type = resolved.get("type", "string")

        if field_type == "object" and "properties" in resolved:
            # Recurse into nested objects with dotted prefix
            nested = _extract_schema_fields(
                resolved,
                root_schema,
                required_fields=resolved.get("required", []),
                prefix=f"{full_name}.",
            )
            fields.extend(nested)
        else:
            fields.append({
                "name": full_name,
                "type": field_type,
                "format": resolved.get("format"),
                "required": field_name in required_fields,
                "description": resolved.get("description", ""),
                "enum": resolved.get("enum"),
                "default": resolved.get("default"),
                "max_length": resolved.get("maxLength"),
            })

    return fields
