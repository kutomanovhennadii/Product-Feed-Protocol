"""Mapping executor for per-item execution of compiled `MappingPlan`."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, List, Mapping, Tuple, Union

from pfp_core.engine.mapping.runtime_presence import _apply_presence
from pfp_core.engine.mapping.runtime_tombstone import (
    _should_project_delete_tombstone,
    detect_delete_unsupported,
)
from pfp_core.engine.mapping.runtime_values import (
    _apply_transform,
    _extract_by_source_path,
)
from pfp_core.engine.plan_types import FieldMappingPlan, MappingPlan
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import Emission

MappedRow = Tuple[Emission, ...]
MappedObject = Mapping[str, Emission]
MappedOutput = Union[MappedRow, MappedObject]


@dataclass(frozen=True)
class MappingExecutionIssue:
    """Structured runtime issue produced by mapping executor.

    Args:
        code: Stable issue code.
        path: Field path associated with issue.
        message: Deterministic issue message.

    Returns:
        None.
    """

    code: str
    path: str
    message: str


@dataclass(frozen=True)
class MappingExecutionResult:
    """Per-item mapping execution result.

    Args:
        output: Mapped output structure with `Emission` values.
        issues: Deterministic runtime issue list.

    Returns:
        None.
    """

    output: MappedOutput
    issues: Tuple[MappingExecutionIssue, ...]


class MappingExecutor:
    """Execute compiled mapping plan for a single record.

    Args:
        catalog: Ext modules catalog for resolving mapping operations.

    Returns:
        None.
    """

    def __init__(self, *, catalog: ExtCatalog) -> None:
        """Initialize executor with mapping operations catalog.

        Args:
            catalog: Ext catalog used to resolve mapping operations.

        Returns:
            None.
        """
        self._catalog = catalog

    def run_one(
        self,
        *,
        plan: MappingPlan,
        input_record: Mapping[str, object],
        artifact_profile: str,
    ) -> MappingExecutionResult:
        """Execute mapping plan for one input record.

        Args:
            plan: Compiled mapping plan.
            input_record: One source record.
            artifact_profile: Current artifact profile.

        Returns:
            Mapping execution result with emissions and deterministic issues.
        """

        issues: List[MappingExecutionIssue] = []

        if plan.output_kind == "csv_row":
            ordered_fields = self._ordered_csv_fields(plan, issues)
            emissions: List[Emission] = []
            unsupported_delete = detect_delete_unsupported(
                plan=plan,
                input_record=input_record,
                artifact_profile=artifact_profile,
            )
            if unsupported_delete is not None:
                code, path, message = unsupported_delete
                issues.append(
                    MappingExecutionIssue(
                        code=code,
                        path=path,
                        message=message,
                    )
                )
            should_project_tombstone = _should_project_delete_tombstone(
                plan=plan,
                input_record=input_record,
                artifact_profile=artifact_profile,
            )
            for field_id in ordered_fields:
                field_plan = plan.fields.get(field_id)
                if field_plan is None:
                    issues.append(
                        MappingExecutionIssue(
                            code="EXEC_MAPPING_FIELD_NOT_FOUND",
                            path="mapping.fields." + field_id,
                            message=(
                                "Field '"
                                + field_id
                                + "' is missing in mapping plan fields."
                            ),
                        )
                    )
                    emissions.append(Emission(kind="OMIT"))
                    continue
                if (
                    should_project_tombstone
                    and field_id != plan.delete_tombstone_id_field
                ):
                    emissions.append(Emission(kind="OMIT"))
                    continue
                emissions.append(
                    self._execute_field(
                        field_plan,
                        input_record,
                        issues,
                    )
                )
            return MappingExecutionResult(
                output=tuple(emissions),
                issues=self._ordered_issues(issues),
            )

        object_output: Dict[str, Emission] = {}
        for field_id in sorted(plan.fields.keys()):
            emission = self._execute_field(
                plan.fields[field_id],
                input_record,
                issues,
            )
            if emission.kind != "OMIT":
                object_output[field_id] = emission

        return MappingExecutionResult(
            output=MappingProxyType(dict(object_output)),
            issues=self._ordered_issues(issues),
        )

    @staticmethod
    def _ordered_csv_fields(
        plan: MappingPlan,
        issues: List[MappingExecutionIssue],
    ) -> Tuple[str, ...]:
        """Resolve deterministic CSV field order from mapping plan.

        Args:
            plan: Compiled mapping plan.
            issues: Mutable list where runtime issues are appended.

        Returns:
            Ordered tuple of field identifiers.
        """
        if plan.output_order is not None:
            return plan.output_order
        issues.append(
            MappingExecutionIssue(
                code="EXEC_MAPPING_OUTPUT_ORDER_MISSING",
                path="mapping.output_order",
                message="mapping.output_order is required for csv_row output.",
            )
        )
        return tuple(sorted(plan.fields.keys()))

    def _execute_field(
        self,
        field_plan: FieldMappingPlan,
        input_record: Mapping[str, object],
        issues: List[MappingExecutionIssue],
    ) -> Emission:
        """Execute source extraction, transforms, and presence for one field."""

        current: object = _extract_by_source_path(input_record, field_plan.source_path)

        for index, op_call in enumerate(field_plan.transforms):
            current, should_break = _apply_transform(
                catalog=self._catalog,
                current=current,
                op_call=op_call,
                field_plan=field_plan,
                transform_index=index,
                issues=issues,
                issue_factory=lambda code, path, message: MappingExecutionIssue(
                    code=code,
                    path=path,
                    message=message,
                ),
            )
            if should_break:
                break

        return _apply_presence(
            current=current,
            field_plan=field_plan,
            issues=issues,
            issue_factory=lambda code, path, message: MappingExecutionIssue(
                code=code,
                path=path,
                message=message,
            ),
        )

    @staticmethod
    def _ordered_issues(
        items: List[MappingExecutionIssue],
    ) -> Tuple[MappingExecutionIssue, ...]:
        """Sort runtime mapping issues into deterministic order."""
        return tuple(
            sorted(
                items,
                key=lambda item: (item.code, item.path, item.message),
            )
        )
