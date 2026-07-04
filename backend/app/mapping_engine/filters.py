"""Source-record filtering.

Keeps only the source records that match a set of configured conditions before
they are mapped and pushed. Field resolution mirrors the mapping engine (section
prefixes like "Record Information||triNameTX" are stripped, dotted paths and
Associated BO fields are supported), so a filter field can be selected the same
way a mapping source field is.
"""
import logging
import re
from typing import Any, Dict, List

from app.mapping_engine.engine import _get_nested_value

logger = logging.getLogger(__name__)

# Supported operators (kept in sync with the frontend filter editor).
OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "is_empty",
    "is_not_empty",
    "greater_than",
    "less_than",
    "gte",
    "lte",
    "regex",
}


def _resolve(record: Dict[str, Any], field: str) -> Any:
    if not field:
        return None
    if "||" in field:
        field = field.split("||", 1)[1]
    if field.startswith("Associated."):
        assoc = record.get("Associated", {}) or {}
        return _get_nested_value(assoc, field.split(".", 1)[1])
    return _get_nested_value(record, field)


def _match_one(record: Dict[str, Any], flt: Dict[str, Any]) -> bool:
    op = (flt.get("operator") or "equals").lower()
    value = _resolve(record, flt.get("field", ""))

    if op == "is_empty":
        return value is None or str(value).strip() == ""
    if op == "is_not_empty":
        return value is not None and str(value).strip() != ""

    raw_target = flt.get("value")
    sval = "" if value is None else str(value)
    tval = "" if raw_target is None else str(raw_target)
    s, t = sval.lower(), tval.lower()  # string comparisons are case-insensitive

    if op == "equals":
        return s == t
    if op == "not_equals":
        return s != t
    if op == "contains":
        return t in s
    if op == "not_contains":
        return t not in s
    if op == "starts_with":
        return s.startswith(t)
    if op == "ends_with":
        return s.endswith(t)
    if op == "regex":
        try:
            return re.search(tval, sval) is not None
        except re.error:
            logger.warning("Invalid regex in source filter: %r", tval)
            return False
    if op in ("greater_than", "less_than", "gte", "lte"):
        try:
            a: Any = float(sval)
            b: Any = float(tval)
        except (ValueError, TypeError):
            a, b = sval, tval  # fall back to lexical comparison
        if op == "greater_than":
            return a > b
        if op == "less_than":
            return a < b
        if op == "gte":
            return a >= b
        return a <= b

    logger.warning("Unknown source filter operator '%s' — record passes", op)
    return True


def record_matches(
    record: Dict[str, Any], filters: List[Dict[str, Any]], match: str = "all"
) -> bool:
    """Return True if the record satisfies the filters.

    match="all" (default) requires every filter to match; match="any" requires
    at least one. Filters with no field are ignored.
    """
    active = [f for f in (filters or []) if f.get("field")]
    if not active:
        return True
    results = [_match_one(record, f) for f in active]
    return any(results) if match == "any" else all(results)


def filter_records(
    records: List[Dict[str, Any]], filters: List[Dict[str, Any]], match: str = "all"
) -> List[Dict[str, Any]]:
    """Return only the records that match the filters (all records if none set)."""
    active = [f for f in (filters or []) if f.get("field")]
    if not active:
        return records
    return [r for r in records if record_matches(r, active, match)]
