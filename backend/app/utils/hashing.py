"""Stable hashing of mapped payloads for change detection across sync runs."""
import hashlib
import json
from typing import Any


def payload_hash(payload: Any) -> str:
    """Return a stable SHA-256 hex digest of a mapped payload.

    Keys are sorted and the JSON is rendered deterministically so that the same
    logical payload always hashes to the same value regardless of key order.
    """
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
