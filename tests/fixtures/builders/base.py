"""Base helpers for deterministic UM fixture builders."""

import copy
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

UMRecord = Dict[str, Any]
PatchFunc = Callable[[UMRecord], UMRecord]

VALID_MODES = {"FULL", "DIFF", "DELETE"}


def normalize_mode(mode: Any) -> str:
    """Normalize builder mode argument to upper-case mode token.

    Args:
        mode: Mode-like enum value or mode string.

    Returns:
        Normalized mode token (``FULL``/``DIFF``/``DELETE``).
    """
    if mode is None:
        token = "FULL"
    else:
        token = str(getattr(mode, "value", mode)).strip().upper()
    if token not in VALID_MODES:
        raise ValueError(f"Unsupported mode: {mode!r}")
    return token


def clone_record(record: UMRecord) -> UMRecord:
    """Deep-clone fixture record for immutable patch behavior.

    Args:
        record: Source record.

    Returns:
        Deep-copied record.
    """
    return copy.deepcopy(record)


def apply_patch_chain(
    record: UMRecord,
    patches: Optional[Sequence[PatchFunc]] = None,
) -> UMRecord:
    """Apply patch functions sequentially without mutating source record.

    Args:
        record: Source fixture record.
        patches: Optional ordered patch callables.

    Returns:
        Final patched record.
    """
    current = clone_record(record)
    for patch in patches or ():
        current = patch(current)
        if not isinstance(current, dict):
            raise TypeError("Patch must return UMRecord dict")
    return current


def _split_path(path: str) -> List[str]:
    """Split dotted path into deterministic tokens.

    Args:
        path: Dotted path.

    Returns:
        Non-empty path tokens.
    """
    tokens = [token for token in path.split(".") if token]
    if not tokens:
        raise ValueError("Empty path")
    return tokens


def set_path(record: UMRecord, path: str, value: Any) -> UMRecord:
    """Return copy of record with dotted-path value assigned.

    Args:
        record: Source record.
        path: Dotted field path.
        value: New value.

    Returns:
        Updated record copy.
    """
    result = clone_record(record)
    tokens = _split_path(path)
    if result.get("delete") is True and path not in {"item_id", "delete"}:
        raise ValueError("Cannot set non-tombstone fields for DELETE record")
    current = result
    for token in tokens[:-1]:
        next_value = current.get(token)
        if not isinstance(next_value, dict):
            next_value = {}
            current[token] = next_value
        current = next_value
    current[tokens[-1]] = value
    return result


def delete_path(record: UMRecord, path: str) -> UMRecord:
    """Return copy of record with dotted-path key removed if present.

    Args:
        record: Source record.
        path: Dotted field path.

    Returns:
        Updated record copy.
    """
    result = clone_record(record)
    tokens = _split_path(path)
    current = result
    for token in tokens[:-1]:
        next_value = current.get(token)
        if not isinstance(next_value, dict):
            return result
        current = next_value
    current.pop(tokens[-1], None)
    return result


def merge_fields(record: UMRecord, fields: Optional[Dict[str, Any]]) -> UMRecord:
    """Return copy with top-level fields merged.

    Args:
        record: Source record.
        fields: Optional top-level fields.

    Returns:
        Updated record copy.
    """
    result = clone_record(record)
    for key, value in (fields or {}).items():
        result[key] = value
    return result


def as_patch_list(*patches: PatchFunc) -> Sequence[PatchFunc]:
    """Convert variadic patch args into stable sequence.

    Args:
        *patches: Patch callables.

    Returns:
        Patch sequence.
    """
    return tuple(patches)


def iter_records(records: Iterable[UMRecord]) -> Iterable[UMRecord]:
    """Yield cloned records from iterable.

    Args:
        records: Source record iterable.

    Yields:
        Cloned records.
    """
    for record in records:
        yield clone_record(record)
