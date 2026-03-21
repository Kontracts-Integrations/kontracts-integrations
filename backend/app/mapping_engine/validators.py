"""
Validate a mapped payload against a target schema.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationError:
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value

    def __repr__(self):
        return f"ValidationError(field={self.field!r}, message={self.message!r})"

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "message": self.message, "value": self.value}


def validate_payload(
    payload: Dict[str, Any],
    schema_fields: List[Dict[str, Any]],
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate a payload dict against a list of field schema definitions.

    Args:
        payload: The dict to validate.
        schema_fields: List of field defs from kontracts schema_parser.

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[ValidationError] = []

    field_map: Dict[str, Dict[str, Any]] = {}
    for f in schema_fields:
        field_map[f["name"]] = f

    # Check required fields are present
    for field_name, field_def in field_map.items():
        if field_def.get("required", False):
            value = _get_nested(payload, field_name)
            if value is None:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Required field '{field_name}' is missing or null",
                    )
                )

    # Validate present fields against their schema
    for field_name, value in _flatten_dict(payload).items():
        if value is None:
            continue

        field_def = field_map.get(field_name)
        if not field_def:
            continue  # Extra fields are allowed

        field_type = field_def.get("type", "string")
        field_format = field_def.get("format")
        enum_values = field_def.get("enum")
        max_length = field_def.get("max_length")

        # Type checks
        type_error = _check_type(field_name, value, field_type, field_format)
        if type_error:
            errors.append(type_error)

        # Enum check
        if enum_values and str(value) not in [str(e) for e in enum_values]:
            errors.append(
                ValidationError(
                    field=field_name,
                    message=f"Value must be one of {enum_values}",
                    value=value,
                )
            )

        # Max length check
        if max_length and isinstance(value, str) and len(value) > max_length:
            errors.append(
                ValidationError(
                    field=field_name,
                    message=f"Value exceeds max length of {max_length}",
                    value=value,
                )
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def _check_type(
    field_name: str, value: Any, field_type: str, field_format: Optional[str]
) -> Optional[ValidationError]:
    if field_type == "string":
        if not isinstance(value, str):
            return ValidationError(
                field=field_name,
                message=f"Expected string, got {type(value).__name__}",
                value=value,
            )
        # Date format validation
        if field_format == "date":
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)):
                return ValidationError(
                    field=field_name,
                    message="Date must be in YYYY-MM-DD format",
                    value=value,
                )

    elif field_type in ("number", "integer"):
        if not isinstance(value, (int, float)):
            try:
                float(value)
            except (ValueError, TypeError):
                return ValidationError(
                    field=field_name,
                    message=f"Expected number, got '{value}'",
                    value=value,
                )

    elif field_type == "boolean":
        if not isinstance(value, bool):
            return ValidationError(
                field=field_name,
                message=f"Expected boolean, got {type(value).__name__}",
                value=value,
            )

    elif field_type == "array":
        if not isinstance(value, list):
            return ValidationError(
                field=field_name,
                message=f"Expected array, got {type(value).__name__}",
                value=value,
            )

    return None


def _get_nested(data: Dict[str, Any], dotted_key: str) -> Any:
    """Get a value from a dict using a dotted key path."""
    parts = dotted_key.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _flatten_dict(
    data: Dict[str, Any], prefix: str = ""
) -> Dict[str, Any]:
    """Flatten a nested dict to dotted keys."""
    result = {}
    for key, value in data.items():
        full_key = f"{prefix}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_dict(value, f"{full_key}."))
        else:
            result[full_key] = value
    return result
