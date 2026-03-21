"""
Transform functions applied per-field during mapping.

Supported transform types:
  direct           - copy value as-is
  constant         - always return a fixed value
  date_format      - convert date string from one format to another
  number_convert   - parse string to float/int, with optional rounding
  boolean_convert  - convert truthy string/int to bool
  string_template  - Jinja2-style {field} substitution
  lookup_table     - map discrete values to other values
  json_path        - extract value from nested dict via JSONPath
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def apply_transform(
    transform_type: str,
    value: Any,
    config: Optional[Dict[str, Any]],
    source_record: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Dispatch to the appropriate transform function.

    Args:
        transform_type: One of the supported transform names.
        value: The source field value.
        config: Transform-specific configuration dict.
        source_record: The full source record (needed for string_template, json_path).

    Returns:
        Transformed value.
    """
    cfg = config or {}
    source = source_record or {}

    try:
        if transform_type == "direct":
            return _direct(value, cfg)
        elif transform_type == "constant":
            return _constant(value, cfg)
        elif transform_type == "date_format":
            return _date_format(value, cfg)
        elif transform_type == "number_convert":
            return _number_convert(value, cfg)
        elif transform_type == "boolean_convert":
            return _boolean_convert(value, cfg)
        elif transform_type == "string_template":
            return _string_template(value, cfg, source)
        elif transform_type == "lookup_table":
            return _lookup_table(value, cfg)
        elif transform_type == "json_path":
            return _json_path(value, cfg, source)
        else:
            logger.warning(f"Unknown transform type '{transform_type}', using direct")
            return _direct(value, cfg)
    except Exception as e:
        logger.error(f"Transform '{transform_type}' failed: {e}", exc_info=True)
        return None


def _direct(value: Any, cfg: Dict) -> Any:
    """Return the value unchanged, with optional default."""
    if value is None:
        return cfg.get("default")
    return value


def _constant(value: Any, cfg: Dict) -> Any:
    """Always return the configured constant value."""
    return cfg.get("value")


def _date_format(value: Any, cfg: Dict) -> Optional[str]:
    """
    Convert a date string from one format to another.

    Config:
        input_format  - strptime format (default: auto-detect via dateutil)
        output_format - strftime format (default: "%Y-%m-%d")
    """
    if value is None:
        return None

    from dateutil import parser as dateutil_parser

    output_fmt = cfg.get("output_format", "%Y-%m-%d")

    try:
        input_fmt = cfg.get("input_format")
        if input_fmt:
            from datetime import datetime
            dt = datetime.strptime(str(value), input_fmt)
        else:
            dt = dateutil_parser.parse(str(value))

        return dt.strftime(output_fmt)
    except Exception as e:
        logger.warning(f"date_format transform failed for value '{value}': {e}")
        return str(value) if value is not None else None


def _number_convert(value: Any, cfg: Dict) -> Optional[Any]:
    """
    Parse a value to a number.

    Config:
        as_type    - "float" (default) or "int"
        decimals   - number of decimal places to round to
        divisor    - divide result by this (e.g. 100 to convert cents to dollars)
        multiplier - multiply result by this
    """
    if value is None:
        return cfg.get("default")

    try:
        # Remove common currency symbols and commas
        cleaned = re.sub(r"[,$€£¥%\s]", "", str(value))
        num = float(cleaned)

        divisor = cfg.get("divisor")
        if divisor:
            num /= float(divisor)

        multiplier = cfg.get("multiplier")
        if multiplier:
            num *= float(multiplier)

        as_type = cfg.get("as_type", "float")
        if as_type == "int":
            return int(round(num))

        decimals = cfg.get("decimals")
        if decimals is not None:
            return round(num, int(decimals))

        return num
    except (ValueError, TypeError) as e:
        logger.warning(f"number_convert failed for value '{value}': {e}")
        return cfg.get("default")


def _boolean_convert(value: Any, cfg: Dict) -> Optional[bool]:
    """
    Convert a value to boolean.

    Config:
        true_values  - list of strings considered True (default: ["true","1","yes","y","on"])
        false_values - list of strings considered False (default: ["false","0","no","n","off"])
    """
    if value is None:
        return cfg.get("default")

    if isinstance(value, bool):
        return value

    true_vals = cfg.get("true_values", ["true", "1", "yes", "y", "on", "True", "TRUE"])
    false_vals = cfg.get("false_values", ["false", "0", "no", "n", "off", "False", "FALSE"])

    str_val = str(value).strip()
    if str_val in true_vals:
        return True
    if str_val in false_vals:
        return False

    # Try numeric
    try:
        return bool(float(str_val))
    except (ValueError, TypeError):
        return None


def _string_template(value: Any, cfg: Dict, source_record: Dict) -> Optional[str]:
    """
    Build a string from a template with {field_name} placeholders.

    Config:
        template - template string, e.g. "{triNameTX} - {triCityTX}, {triStateProvinceListTX}"
    """
    template = cfg.get("template", "{value}")
    try:
        context = dict(source_record)
        context["value"] = value
        # Replace {field_name} patterns
        def replacer(match):
            key = match.group(1)
            return str(context.get(key, ""))

        result = re.sub(r"\{(\w+)\}", replacer, template)
        return result
    except Exception as e:
        logger.warning(f"string_template failed: {e}")
        return str(value) if value is not None else None


def _lookup_table(value: Any, cfg: Dict) -> Any:
    """
    Map a discrete value to another using a lookup table.

    Config:
        table    - dict mapping input -> output
        default  - value to return if no match (default: original value)
    """
    table: Dict[str, Any] = cfg.get("table", {})
    default_val = cfg.get("default", value)

    if value is None:
        return default_val

    str_val = str(value)
    return table.get(str_val, table.get(value, default_val))


def _json_path(value: Any, cfg: Dict, source_record: Dict) -> Any:
    """
    Extract a value from the source record using a JSONPath expression.

    Config:
        path    - JSONPath expression, e.g. "$.address.city"
        default - default if path not found
    """
    path = cfg.get("path")
    default = cfg.get("default")

    if not path:
        return value

    try:
        from jsonpath_ng import parse as jsonpath_parse

        expr = jsonpath_parse(path)
        matches = expr.find(source_record)
        if matches:
            return matches[0].value
        return default
    except Exception as e:
        logger.warning(f"json_path '{path}' failed: {e}")
        return default
