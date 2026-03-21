"""
Core mapping engine: apply field mappings to transform TRIRIGA records into Kontracts payloads.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.mapping_engine.transforms import apply_transform
from app.mapping_engine.validators import ValidationError, validate_payload

logger = logging.getLogger(__name__)


class MappingEngine:
    def __init__(self, field_mappings: List[Dict[str, Any]]):
        """
        Args:
            field_mappings: List of field mapping configs, each having:
                - id: unique row identifier
                - source_field: field name in source record
                - target_field: field name in target payload
                - transform_type: type of transform
                - transform_config: transform-specific config dict
                - is_required: whether this field must succeed
        """
        self.field_mappings = field_mappings

    def apply(
        self,
        source_record: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Apply all field mappings to a single source record.

        Returns:
            (mapped_payload, list_of_warning_messages)
        """
        payload: Dict[str, Any] = {}
        warnings: List[str] = []

        for mapping in self.field_mappings:
            source_field = mapping.get("source_field", "")
            target_field = mapping.get("target_field", "")
            transform_type = mapping.get("transform_type", "direct")
            transform_config = mapping.get("transform_config") or {}
            is_required = mapping.get("is_required", False)

            if not source_field and transform_type != "constant":
                continue
            if not target_field:
                continue

            # Get source value (supports dotted paths)
            source_value = _get_nested_value(source_record, source_field)

            # Apply transform
            try:
                transformed_value = apply_transform(
                    transform_type=transform_type,
                    value=source_value,
                    config=transform_config,
                    source_record=source_record,
                )
            except Exception as e:
                msg = (
                    f"Transform '{transform_type}' on field '{source_field}' failed: {e}"
                )
                logger.error(msg, exc_info=True)
                warnings.append(msg)
                if is_required:
                    raise ValueError(
                        f"Required field mapping failed: {source_field} -> {target_field}: {e}"
                    )
                continue

            # Set value in target payload (supports dotted paths)
            _set_nested_value(payload, target_field, transformed_value)

        return payload, warnings

    def apply_batch(
        self,
        source_records: List[Dict[str, Any]],
    ) -> List[Tuple[Dict[str, Any], List[str], Optional[Exception]]]:
        """
        Apply mappings to a list of records.

        Returns:
            List of (mapped_payload, warnings, error) tuples.
            error is None on success.
        """
        results = []
        for record in source_records:
            try:
                payload, warnings = self.apply(record)
                results.append((payload, warnings, None))
            except Exception as e:
                results.append(({}, [], e))
        return results

    def validate(
        self,
        payload: Dict[str, Any],
        schema_fields: List[Dict[str, Any]],
    ) -> Tuple[bool, List[ValidationError]]:
        return validate_payload(payload, schema_fields)


def _get_nested_value(record: Dict[str, Any], dotted_key: str) -> Any:
    """
    Get a value from a potentially nested dict using a dotted key.
    Also handles direct key lookup for non-dotted keys.
    """
    if not dotted_key:
        return None

    # Direct key first (handles keys that contain dots)
    if dotted_key in record:
        return record[dotted_key]

    # Dotted path traversal
    parts = dotted_key.split(".")
    current: Any = record
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _set_nested_value(target: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """
    Set a value in a potentially nested dict using a dotted key.
    Creates intermediate dicts as needed.
    """
    parts = dotted_key.split(".")
    if len(parts) == 1:
        target[dotted_key] = value
        return

    current = target
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
