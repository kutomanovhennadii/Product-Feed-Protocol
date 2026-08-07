"""Prepared artifact producer contract for runtime/core integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    Literal,
    Optional,
    cast,
)

from pfp_core.artifact_production.artifact_production_naming import make_filename_hint
from pfp_core.artifact_production.artifact_production_schema_resolution import (
    normalize_target_id,
)
from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.artifact_production_result import ArtifactProductionResult
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.engine.mapping_executor import MappedOutput, MappingExecutor
from pfp_core.engine.plan_types import CompiledSchema
from pfp_core.engine.validation_executor import ValidationExecutor
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import Emission, ProducerContext
from pfp_core.policies import PolicyBundle
from pfp_core.policies.policy_bundle_builder import default_policy_registry
from pfp_core.policies.policy_config_loader import load_policy_bundle_from_yaml_text
from pfp_core.schema import SchemaRef
from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_refs import extract_ref_from_doc
from pfp_core.schema.schema_registry import SchemaRegistry
from pfp_core.schema.schema_types import SchemaErrorItem, SchemaFormatError
from pfp_core.writers.writer_base import Writer
from pfp_core.writers.writer_builtins import build_default_writer_registry
from pfp_core.writers.writer_registry import WriterRegistry
from pfp_core.writers.writer_types import MISSING
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.logging import LogPipeline


@dataclass(frozen=True)
class _PreparedSchema:
    """Prepared executable schema bundle bound to producer identity."""

    schema_ref: SchemaRef
    target_id: str
    compiled: CompiledSchema
    encoding: str
    validation_executor: Optional[ValidationExecutor] = None
    mapping_executor: Optional[MappingExecutor] = None
    writer: Optional[Writer] = None


class ArtifactProducer:
    """Prepared producer for schema/policy-bound artifact execution.

    Args:
        prepared_schema: Prepared schema execution state.
        policies: Optional prepared policy bundle.
    """

    def __init__(
        self,
        *,
        prepared_schema: _PreparedSchema,
        policies: Optional[PolicyBundle] = None,
    ) -> None:
        """Build a prepared producer identity."""
        self._policies = policies
        self._catalog: ExtCatalog = build_builtin_catalog()
        self._writer_registry: WriterRegistry = build_default_writer_registry()
        self._prepared_schema = self._prepare_execution_components(prepared_schema)

    def _prepare_execution_components(
        self, prepared: _PreparedSchema
    ) -> _PreparedSchema:
        if not prepared.compiled.is_valid:
            return prepared

        validation_executor = prepared.validation_executor or ValidationExecutor(
            catalog=self._catalog,
            policy_bundle=self._policies,
            target=prepared.target_id,
        )
        mapping_executor = prepared.mapping_executor or MappingExecutor(
            catalog=self._catalog
        )
        writer = prepared.writer or self._writer_registry.create(
            prepared.compiled.writer_spec.writer_id,
            prepared.compiled.writer_spec.writer_config,
            {
                "encoding": prepared.encoding,
                "content_type": prepared.compiled.writer_spec.artifact_content_type,
                "file_extension": prepared.compiled.writer_spec.artifact_file_extension,
            },
        )

        return replace(
            prepared,
            validation_executor=validation_executor,
            mapping_executor=mapping_executor,
            writer=writer,
        )

    def produce_artifacts(
        self,
        um: Iterable[Any],
        *,
        generated_at: Optional[datetime] = None,
    ) -> ArtifactProductionResult:
        """Build artifacts against prepared schema/policy identity.

        Args:
            um: Input items iterable.
            generated_at: Optional explicit UTC timestamp.

        Returns:
            Artifact production result.
        """
        generated_at_utc = _ensure_generated_at_utc(generated_at)

        prepared = self._prepared_schema
        aggregated_report = ValidationReport(
            target=prepared.target_id,
            artifact_profile=prepared.compiled.artifact_profile,
        )

        if not prepared.compiled.is_valid:
            for compile_diag in prepared.compiled.diagnostics:
                diag = Diagnostic(
                    severity=_normalize_compile_severity(compile_diag.severity),
                    code=compile_diag.code,
                    message=compile_diag.message,
                    path=compile_diag.path,
                    item_ref="schema",
                    metadata={"action": "FAIL"},
                )
                aggregated_report.add(diag)
            return ArtifactProductionResult(
                artifacts=tuple(),
                validation_report=aggregated_report,
            )

        writer = prepared.writer
        if writer is None:
            raise RuntimeError("prepared writer is required")

        payload = self._build_payload_iter(
            um_items=um,
            prepared=prepared,
            aggregated_report=aggregated_report,
        )

        metadata = ArtifactMetadata(
            target=prepared.target_id,
            schema_version=prepared.schema_ref.schema_version,
            generated_at=generated_at_utc,
            content_type=prepared.compiled.writer_spec.artifact_content_type,
            encoding=prepared.encoding,
            artifact_profile=prepared.compiled.artifact_profile,
            filename_hint=make_filename_hint(
                target=prepared.target_id,
                artifact_profile=prepared.compiled.artifact_profile,
                schema_version=prepared.schema_ref.schema_version,
                file_extension=prepared.compiled.writer_spec.artifact_file_extension,
            ),
        )
        artifacts = (
            ProducedArtifact(
                payload=writer.write(payload),
                metadata=metadata,
            ),
        )

        return ArtifactProductionResult(
            artifacts=artifacts,
            validation_report=aggregated_report,
        )

    def _build_payload_iter(
        self,
        *,
        um_items: Iterable[Any],
        prepared: _PreparedSchema,
        aggregated_report: ValidationReport,
    ) -> Iterable[object]:
        validation_executor = prepared.validation_executor
        if validation_executor is None:
            raise RuntimeError("prepared validation executor is required")
        mapping_executor = prepared.mapping_executor
        if mapping_executor is None:
            raise RuntimeError("prepared mapping executor is required")

        artifact_profile = prepared.compiled.artifact_profile

        def _records() -> Iterator[object]:
            for item in um_items:
                try:
                    if not isinstance(item, Mapping):
                        diagnostic = Diagnostic(
                            severity=DiagnosticSeverity.ERROR,
                            code="VALIDATION.INVALID_ITEM_TYPE",
                            message="Invalid item type: expected mapping.",
                            path="build:producer",
                            item_ref="unknown",
                            metadata={"action": "DROP"},
                        )
                        aggregated_report.add(diagnostic)
                        continue

                    item_ref = _extract_item_ref(item)
                    validation = validation_executor.run_one(
                        plan=prepared.compiled.validation_plan,
                        input_record=item,
                        artifact_profile=artifact_profile,
                    )
                    for issue in validation.items:
                        diag = Diagnostic(
                            severity=_normalize_validation_severity(issue.severity),
                            code=issue.code,
                            message=issue.message,
                            path=issue.path,
                            item_ref=item_ref,
                            metadata={"action": validation.decision},
                        )
                        aggregated_report.add(diag)

                    if validation.decision == "DROP":
                        continue
                    if validation.decision == "FAIL":
                        stop_diag = Diagnostic(
                            severity=DiagnosticSeverity.ERROR,
                            code="BUILD.FAIL_STOP",
                            message="Build stopped due to FAIL validation decision.",
                            path="build:validation",
                            item_ref=item_ref,
                            metadata={"action": "FAIL"},
                        )
                        aggregated_report.add(stop_diag)
                        break

                    mapped = mapping_executor.run_one(
                        plan=prepared.compiled.mapping_plan,
                        input_record=item,
                        artifact_profile=artifact_profile,
                    )
                    for mapping_issue in mapped.issues:
                        map_diag = Diagnostic(
                            severity=DiagnosticSeverity.ERROR,
                            code=mapping_issue.code,
                            message=mapping_issue.message,
                            path=mapping_issue.path,
                            item_ref=item_ref,
                            metadata={"action": "DROP"},
                        )
                        aggregated_report.add(map_diag)

                    yield _mapped_output_to_writer_record(mapped.output)

                except Exception as exc:
                    fault_isolation = (
                        self._policies.fault_isolation if self._policies else None
                    )
                    if fault_isolation is not None:
                        fault_isolation.handle_error(
                            exc, context_msg="Item processing error"
                        )
                        # SKIP_ITEM: handle_error logs, does not re-raise — loop continues
                        # FAIL_FAST: handle_error re-raises — propagates outward
                    else:
                        raise

        return _records()

    @property
    def target_label(self) -> str:
        """Return stable target label for observability fields."""
        return self._prepared_schema.schema_ref.protocol_id


def prepare_artifact_producer_from_files(
    *,
    schema_file: str,
    policy_file: str,
    tax_mapping: Optional[Mapping[str, Any]] = None,
    log_pipeline: LogPipeline,
) -> ArtifactProducer:
    """Prepare artifact producer from file-based schema and policy inputs.

    Args:
        schema_file: Path to schema YAML/JSON document.
        policy_file: Path to policy YAML document.
        tax_mapping: Optional infra-supplied tax mapping reserved for compile-time use.
        log_pipeline: Manifest-owned log pipeline used by policy infrastructure.

    Returns:
        Prepared ``ArtifactProducer`` instance.
    """
    schema_path = Path(schema_file).expanduser().resolve()
    schema_text = schema_path.read_text(encoding="utf-8")
    schema_format = cast(
        Literal["yaml", "json"],
        _resolve_schema_format_from_suffix(schema_path),
    )
    schema_doc = parse_schema_text(schema_text, format=schema_format)

    schema_registry = SchemaRegistry()
    schema_registry.register(
        schema_doc,
        filename=schema_path.name,
        source="file",
    )

    schema_ref = extract_ref_from_doc(schema_doc)

    policy_path = Path(policy_file).expanduser().resolve()
    policy_text = policy_path.read_text(encoding="utf-8")
    policy_registry = default_policy_registry(log_pipeline=log_pipeline)
    policies = load_policy_bundle_from_yaml_text(
        policy_text,
        registry=policy_registry,
        log_pipeline=log_pipeline,
    )

    compiler = SchemaCompiler(catalog=build_builtin_catalog())
    context = None
    if tax_mapping is not None:
        context = ProducerContext(tax_mapping=tax_mapping)

    if context is None:
        compiled = compiler.compile(schema_doc)
    else:
        compiled = compiler.compile(schema_doc, context=context)
    prepared = _PreparedSchema(
        schema_ref=schema_ref,
        target_id=normalize_target_id(schema_ref.protocol_id),
        compiled=compiled,
        encoding=_resolve_artifact_encoding(schema_doc),
    )

    return ArtifactProducer(
        prepared_schema=prepared,
        policies=policies,
    )


def _resolve_schema_format_from_suffix(path: Path) -> str:
    """Resolve schema document format from a filesystem suffix.

    Args:
        path: Filesystem path to the schema document.

    Returns:
        Schema format token supported by the parser.

    Raises:
        SchemaFormatError: If the path suffix is unsupported.
    """
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    raise SchemaFormatError(
        [
            SchemaErrorItem(
                code="SCHEMA_PARSE_ERROR",
                path="$",
                message=(
                    "Unsupported schema file extension: "
                    + suffix
                    + ". Supported extensions are: .yaml, .yml, .json."
                ),
            )
        ],
        source=str(path),
    )


def default_generated_at_utc() -> datetime:
    """Return deterministic default timestamp source for producer execution."""
    return datetime.now(timezone.utc)


def _ensure_generated_at_utc(value: Optional[datetime]) -> datetime:
    """Validate and normalize explicit generation timestamps to UTC.

    Args:
        value: Optional timestamp supplied by the caller.

    Returns:
        UTC-aware timestamp suitable for artifact metadata.

    Raises:
        ValueError: If the timestamp is naive or not expressed in UTC.
    """
    timestamp = value or default_generated_at_utc()
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware UTC datetime")
    offset = timestamp.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("generated_at must be UTC datetime")
    return timestamp.astimezone(timezone.utc)


def _normalize_compile_severity(value: str) -> DiagnosticSeverity:
    """Map compile-time severity tokens to canonical diagnostic severity.

    Args:
        value: Raw compile-time severity token.

    Returns:
        Canonical diagnostic severity enum.
    """
    normalized = value.upper()
    if normalized in {"ERROR", "ERR", "E"}:
        return DiagnosticSeverity.ERROR
    if normalized in {"WARN", "WARNING", "W"}:
        return DiagnosticSeverity.WARN
    return DiagnosticSeverity.INFO


def _normalize_validation_severity(value: str) -> DiagnosticSeverity:
    """Map validation severity tokens to canonical diagnostic severity.

    Args:
        value: Raw validation severity token.

    Returns:
        Canonical diagnostic severity enum.
    """
    normalized = value.upper()
    if normalized in {"ERROR", "ERR", "E"}:
        return DiagnosticSeverity.ERROR
    if normalized in {"WARN", "WARNING", "W"}:
        return DiagnosticSeverity.WARN
    return DiagnosticSeverity.INFO


def _extract_item_ref(item: Mapping[str, Any]) -> str:
    """Extract a stable item reference from a mapped input record.

    Args:
        item: Runtime input mapping being processed.

    Returns:
        Best-effort item identifier, or ``unknown`` when none is present.
    """
    for key in ("id", "sku", "pk", "uuid", "_id"):
        candidate = item.get(key)
        if candidate is not None:
            text = str(candidate).strip()
            if text:
                return text
    return "unknown"


def _mapped_output_to_writer_record(output: MappedOutput) -> object:
    """Convert mapped output payload into writer-compatible data.

    Args:
        output: Mapping executor output payload.

    Returns:
        Tuple or mapping with OMIT emissions removed.
    """
    if isinstance(output, tuple):
        return tuple(_emission_to_writer_value(value) for value in output)

    mapped: Dict[str, object] = {}
    for key, emission in output.items():
        writer_value = _emission_to_writer_value(emission)
        if writer_value is MISSING:
            continue
        mapped[key] = writer_value
    return mapped


def _emission_to_writer_value(emission: Emission) -> object:
    """Convert emission objects into writer-facing primitive values.

    Args:
        emission: Emission produced by the mapping executor.

    Returns:
        Writer-facing value, ``None`` for NULL, or ``MISSING`` for OMIT.
    """
    if emission.kind == "OMIT":
        return MISSING
    if emission.kind == "NULL":
        return None
    return emission.value


def _resolve_artifact_encoding(schema_doc: Mapping[str, Any]) -> str:
    """Resolve artifact encoding from schema output section.

    Args:
        schema_doc: Raw schema document mapping.

    Returns:
        Encoding string, defaulting to utf-8.
    """
    output_section = schema_doc.get("output")
    if not isinstance(output_section, Mapping):
        return "utf-8"
    artifact_section = output_section.get("artifact")
    if not isinstance(artifact_section, Mapping):
        return "utf-8"
    encoding = artifact_section.get("encoding")
    if isinstance(encoding, str) and encoding.strip():
        return encoding.strip()
    return "utf-8"


__all__ = [
    "ArtifactProducer",
    "prepare_artifact_producer_from_files",
    "default_generated_at_utc",
]
