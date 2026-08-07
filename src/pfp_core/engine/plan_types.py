"""Typed plan contracts and diagnostics for schema compiler (Story 6b.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping, Optional, Sequence, Tuple

TypeId = Literal[
    "string",
    "int",
    "decimal",
    "bool",
    "date",
    "datetime",
    "array[string]",
    "object",
]
CompileSeverity = Literal["ERROR", "WARN"]


@dataclass(frozen=True, init=False)
class CompileDiagItem:
    """Deterministic compiler diagnostic item.

    Args:
        code: Stable diagnostic code.
        path: Schema path where issue was detected.
        message: Deterministic diagnostic message.
        severity: Diagnostic severity level.

    Returns:
        None.
    """

    code: str
    path: str
    message: str
    severity: CompileSeverity = "ERROR"

    def __init__(
        self,
        code: str,
        path: str,
        message: str,
        severity: Optional[CompileSeverity] = None,
        DiagnosticSeverity: Optional[CompileSeverity] = None,
    ) -> None:
        resolved = severity if severity is not None else DiagnosticSeverity
        if resolved is None:
            resolved = "ERROR"
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "severity", resolved)

    @property
    def DiagnosticSeverity(self) -> CompileSeverity:
        """Compatibility alias for legacy field name."""
        return self.severity


OutputKind = Literal["csv_row", "json_object"]
EmissionSemantics = Literal[
    "omit_missing",
    "emit_null_if_missing",
    "error_if_missing",
]
OnMissingBehavior = Literal["pass", "default", "omit", "error"]


@dataclass(frozen=True)
class MappingOpCall:
    """Compiled mapping operation call.

    Args:
        op_id: Mapping operation identifier.
        args: Operation arguments.
        on_missing: On-missing behavior.
        input_type: Expected input type id.
        output_type: Produced output type id.

    Returns:
        None.
    """

    op_id: str
    args: Optional[Mapping[str, object]] = None
    on_missing: Optional[OnMissingBehavior] = None
    input_type: Optional[TypeId] = None
    output_type: Optional[TypeId] = None


@dataclass(frozen=True)
class FieldPresencePlan:
    """Compiled field-level presence semantics.

    Args:
        behavior: Missing-value emission behavior.

    Returns:
        None.
    """

    behavior: EmissionSemantics


@dataclass(frozen=True)
class FieldMappingPlan:
    """Compiled mapping plan for a single output field.

    Args:
        field_id: Output field identifier.
        source_path: Source path expression.
        transforms: Ordered mapping transforms.
        presence: Field-level presence plan.
        final_type: Final inferred output type.
        is_required_source: Whether source is required.

    Returns:
        None.
    """

    field_id: str
    source_path: str
    transforms: Tuple[MappingOpCall, ...] = field(default_factory=tuple)
    presence: FieldPresencePlan = field(
        default_factory=lambda: FieldPresencePlan(behavior="omit_missing")
    )
    final_type: Optional[TypeId] = None
    is_required_source: bool = False


@dataclass(frozen=True)
class MappingPlan:
    """Compiled mapping plan.

    Args:
        output_kind: Mapping output kind.
        output_order: Output order for CSV output.
        fields: Compiled field mapping dictionary.
        delete_tombstone_enabled: Whether tombstone projection is enabled.
        delete_tombstone_flag_path: Input path to tombstone flag.
        delete_tombstone_id_field: Field id preserved in tombstone rows.

    Returns:
        None.
    """

    output_kind: OutputKind
    output_order: Optional[Tuple[str, ...]] = None
    fields: Mapping[str, FieldMappingPlan] = field(
        default_factory=lambda: MappingProxyType({})
    )
    delete_tombstone_enabled: bool = False
    delete_tombstone_flag_path: str = "delete"
    delete_tombstone_id_field: str = "id"


@dataclass(frozen=True)
class ValidationRulePlan:
    """Compiled validation rule plan item.

    Args:
        module_id: Validation module identifier.
        rule_id: Optional schema rule identifier.
        applies_to_field: Optional field scope for the rule.
        config: Module configuration payload.
        on_fail_code: Optional on-fail code.
        on_fail_message: Optional on-fail message.
        severity_hint: Optional DiagnosticSeverity hint.
        expected_value_type: Optional expected value type.

    Returns:
        None.
    """

    module_id: str
    rule_id: Optional[str] = None
    applies_to_field: Optional[str] = None
    config: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
    on_fail_code: Optional[str] = None
    on_fail_message: Optional[str] = None
    severity_hint: Optional[str] = None
    expected_value_type: Optional[TypeId] = None


@dataclass(frozen=True)
class ValidationPlan:
    """Compiled validation plan.

    Args:
        rules: Ordered compiled validation rules.

    Returns:
        None.
    """

    rules: Tuple[ValidationRulePlan, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WriterSpec:
    """Compiled writer and artifact specification.

    Args:
        writer_id: Writer identifier.
        artifact_content_type: Artifact content type.
        artifact_file_extension: Artifact file extension.
        writer_config: Writer configuration payload.

    Returns:
        None.
    """

    writer_id: str
    artifact_content_type: str
    artifact_file_extension: str
    writer_config: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True)
class CompiledSchema:
    """Schema compiler output.

    Args:
        artifact_profile: Product semantics profile from schema header.
        validation_plan: Compiled validation plan.
        mapping_plan: Compiled mapping plan.
        writer_spec: Compiled writer specification.
        diagnostics: Compilation diagnostics.
        is_valid: Compilation validity flag.

    Returns:
        None.
    """

    artifact_profile: str
    validation_plan: ValidationPlan
    mapping_plan: MappingPlan
    writer_spec: WriterSpec
    diagnostics: Tuple[CompileDiagItem, ...] = field(default_factory=tuple)
    is_valid: bool = False


def sort_compile_diagnostics(
    items: Sequence[CompileDiagItem],
) -> Tuple[CompileDiagItem, ...]:
    """Sort diagnostics deterministically with ERROR before WARN.

    Args:
        items: Diagnostic items to sort.

    Returns:
        Tuple with deterministic diagnostic ordering.
    """

    severity_order = {"ERROR": 0, "WARN": 1}
    return tuple(
        sorted(
            items,
            key=lambda item: (
                severity_order.get(item.severity, 99),
                item.code,
                item.path,
                item.message,
            ),
        )
    )
