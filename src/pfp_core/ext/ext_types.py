from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping, Optional, Tuple

TypeId = Literal[
    "string",
    "int",
    "decimal",
    "bool",
    "date",
    "datetime",
    "array[string]",
    "object",
    "any",
]


@dataclass(frozen=True)
class TypeSpec:
    """Type contract for ext operation inputs and outputs.

    Args:
        type_id: Declared logical type identifier.
        nullable: Whether `None` is allowed.
        optional: Whether missing value is allowed.

    Returns:
        None.
    """

    type_id: TypeId
    nullable: bool = True
    optional: bool = True


class Missing:
    """Sentinel type for missing values distinct from None.

    Args:
        None.

    Returns:
        None.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        """Return stable printable sentinel representation.

        Args:
            None.

        Returns:
            Constant sentinel representation.
        """
        return "MISSING"


MISSING = Missing()

EmissionKind = Literal["VALUE", "OMIT", "NULL"]


@dataclass(frozen=True)
class Emission:
    """Typed emission value for target record assembly.

    Args:
        kind: Emission variant: VALUE, OMIT, or NULL.
        value: String payload for VALUE emissions.

    Returns:
        None.
    """

    kind: EmissionKind
    value: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate emission invariants after dataclass initialization.

        Args:
            None.

        Returns:
            None.

        Raises:
            ValueError: When VALUE has no payload or non-VALUE has payload.
        """
        if self.kind == "VALUE" and self.value is None:
            raise ValueError("Emission VALUE requires string value.")
        if self.kind != "VALUE" and self.value is not None:
            raise ValueError("Emission OMIT/NULL must not contain value.")


@dataclass(frozen=True)
class ParamFieldSpec:
    """Single parameter field specification for op args/config.

    Args:
        name: Parameter field name.
        type_spec: Parameter field type contract.
        required: Whether parameter is mandatory.
        constraints: Optional parameter constraints.

    Returns:
        None.
    """

    name: str
    type_spec: TypeSpec
    required: bool
    constraints: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParamSpec:
    """Parameter schema for op args/config payloads.

    Args:
        fields: Declared parameter fields.
        allow_extra: Whether unknown parameters are allowed.

    Returns:
        None.
    """

    fields: Tuple[ParamFieldSpec, ...] = ()
    allow_extra: bool = False


@dataclass(frozen=True)
class ValidationResult:
    """Minimal typed validation outcome.

    Args:
        ok: Validation success flag.
        details: Optional deterministic failure details.

    Returns:
        None.
    """

    ok: bool
    details: Optional[str] = None


@dataclass(frozen=True)
class ProducerContext:
    """Compile-time context with infrastructure-supplied lookups.

    Args:
        tax_mapping: Optional tax mapping lookup loaded from infra configuration.

    Returns:
        None.
    """

    tax_mapping: Optional[Mapping[str, Any]] = None


MappingOpCall = Callable[[Any, Mapping[str, Any]], Any]
MappingOpPrepare = Callable[
    [Mapping[str, Any], Optional[ProducerContext]],
    Mapping[str, Any],
]
ValidationModuleCall = Callable[
    [
        Any,
        Mapping[str, Any],
        Optional[Mapping[str, Any]],
        Optional[str],
    ],
    ValidationResult,
]


@dataclass(frozen=True)
class MappingOpSpec:
    """Mapping operation specification registered in ExtCatalog.

    Args:
        op_id: Stable mapping operation identifier.
        input_type: Input type contract.
        output_type: Output type contract.
        args_spec: Arguments schema for operation call.
        call: Callable implementing operation behavior.
        prepare: Optional compile-time callback to enrich args.

    Returns:
        None.
    """

    op_id: str
    input_type: TypeSpec
    output_type: TypeSpec
    args_spec: ParamSpec
    call: MappingOpCall
    prepare: Optional[MappingOpPrepare] = None


@dataclass(frozen=True)
class ValidationModuleSpec:
    """Validation module specification registered in ExtCatalog.

    Args:
        module_id: Stable validation module identifier.
        value_type: Input value type contract.
        config_spec: Configuration schema for module call.
        call: Callable implementing validation behavior.

    Returns:
        None.
    """

    module_id: str
    value_type: TypeSpec
    config_spec: ParamSpec
    call: ValidationModuleCall
