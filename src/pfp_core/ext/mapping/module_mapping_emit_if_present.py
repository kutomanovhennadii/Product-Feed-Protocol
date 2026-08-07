"""Mapping op: convert presence into a typed `Emission`."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, Emission, MappingOpSpec, ParamSpec, TypeSpec


def _emit_if_present(value: Any, args: Mapping[str, Any]) -> Emission:
    """Emit VALUE/NULL/OMIT depending on the input presence.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `Emission(kind="OMIT")` for `MISSING`, `Emission(kind="NULL")` for `None`,
        otherwise `Emission(kind="VALUE", value=str(value))`.
    """
    _ = args
    if value is MISSING:
        return Emission(kind="OMIT")
    if value is None:
        return Emission(kind="NULL")
    return Emission(kind="VALUE", value=str(value))


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `emit_if_present` operation."""
    return MappingOpSpec(
        op_id="emit_if_present",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("object", nullable=False, optional=False),
        args_spec=ParamSpec(),
        call=_emit_if_present,
    )
