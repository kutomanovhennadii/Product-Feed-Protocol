"""Render helpers for fixture records consumed by tests.

This module provides fixture record detachment and deterministic JSON serialization for test inputs.
It is not a feed writer.
"""

import copy
import json
from typing import Any, Dict, Iterable, List


def ensure_dict(value: Any) -> Dict[str, Any]:
    """Return value as dict, raising deterministic type error otherwise.

    Args:
        value: Candidate mapping value.

    Returns:
        Dictionary value.
    """
    if not isinstance(value, dict):
        raise TypeError("Expected dict value for fixture operation.")
    return value


def to_um_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return deep-copied UM record.

    Args:
        record: Source fixture record.

    Returns:
        Deep copy of input record.
    """
    return copy.deepcopy(record)


def to_um_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert iterable of records into detached list.

    Args:
        records: Fixture record iterable.

    Returns:
        Deep-copied list of records.
    """
    records_list = list(records)
    return [to_um_record(r) for r in records_list]


def to_json_bytes(record: Dict[str, Any]) -> bytes:
    """Serialize fixture record to deterministic JSON bytes.

    Args:
        record: Fixture record.

    Returns:
        UTF-8 encoded JSON bytes.
    """
    payload: str = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (payload + "\n").encode("utf-8")
