"""Mapping op: always emit a typed OMIT `Emission`."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import Emission, MappingOpSpec, ParamSpec, TypeSpec


def _omit_if_missing(value: Any, args: Mapping[str, Any]) -> Emission:
    """Always emit an OMIT `Emission`.

    Args:
        value: Input value (unused).
        args: Operation args (unused).

    Returns:
        `Emission(kind="OMIT")`.
    """
    _ = value
    _ = args
    return Emission(kind="OMIT")


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `omit_if_missing` operation."""
    return MappingOpSpec(
        op_id="omit_if_missing",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("object", nullable=False, optional=False),
        args_spec=ParamSpec(),
        call=_omit_if_missing,
    )
