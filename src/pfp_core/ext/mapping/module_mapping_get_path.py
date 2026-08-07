"""Mapping op: extract a value from an object by dot-path.

This module implements the minimal Story 6b.3 `get_path` operation.
"""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _get_path(value: Any, args: Mapping[str, Any]) -> Any:
    """Extract a nested value from `value` using the provided dot-path.

    Args:
        value: Input object (typically a nested Mapping/list structure).
        args: Operation args. Requires a non-empty string key `path`.

    Returns:
        Extracted value, `None` if explicitly present, or `MISSING` if the path
        cannot be resolved.

    Raises:
        ValueError: If `args["path"]` is missing or invalid.
    """
    path = args.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("get_path requires non-empty string arg 'path'.")

    current = value
    for segment in path.split("."):
        if isinstance(current, Mapping) and segment in current:
            current = current[segment]
            continue
        if isinstance(current, list):
            try:
                index = int(segment)
            except ValueError:
                return MISSING
            if index < 0 or index >= len(current):
                return MISSING
            current = current[index]
            continue
        return MISSING
    return current


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `get_path` operation.

    Returns:
        A mapping op specification suitable for registration in `ExtCatalog`.
    """
    return MappingOpSpec(
        op_id="get_path",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("any", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="path",
                    type_spec=TypeSpec("string", nullable=False, optional=False),
                    required=True,
                ),
            ),
            allow_extra=False,
        ),
        call=_get_path,
    )
