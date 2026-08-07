"""Tests for file-oriented artifact producer preparation contract."""

from __future__ import annotations

import importlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest

import pfp_core.artifact_production.artifact_producer as producer_mod
from pfp_core.artifact_production.artifact_producer import (
    ArtifactProducer,
    _PreparedSchema,
    prepare_artifact_producer_from_files,
)
from pfp_core.schema import SchemaRef
from pfp_core.engine.plan_types import CompiledSchema
from pfp_core.ext.ext_types import Emission, ProducerContext
from pfp_core.policies import PolicyBundle
from pfp_core.policies.domain.strictness import StrictnessPolicy
from pfp_core.policies.infra.fault_isolation_policy import (
    FaultIsolationConfig,
    FaultIsolationPolicy,
)
from pfp_core.schema.schema_types import SchemaFormatError
from pfp_utils.diagnostics.validation_report import ValidationReport


def _repo_python_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _schema_file() -> Path:
    return (
        _repo_python_root()
        / "schemas"
        / "stripe.product_feed"
        / "stripe.product_feed-1.0.0.yaml"
    )


def _policy_file() -> Path:
    return _repo_python_root() / "config" / "policies.yaml"


def _write_policy_file(tmp_path: Path) -> Path:
    policy_path = tmp_path / "policies.yaml"
    policy_path.write_text(
        'version: "1.0"\ncore:\n  strictness:\n    strategy: "fail_on_error"\n',
        encoding="utf-8",
    )
    return policy_path


def test_prepare_from_files_rejects_unsupported_schema_extension(
    tmp_path: Path,
) -> None:
    """Raise SchemaFormatError when schema extension is not yaml/json."""
    schema_path = tmp_path / "schema.txt"
    schema_path.write_text("header: {}", encoding="utf-8")

    with pytest.raises(SchemaFormatError):
        prepare_artifact_producer_from_files(
            schema_file=str(schema_path),
            policy_file=str(_policy_file()),
            log_pipeline=Mock(),
        )


def test_prepare_from_files_rejects_invalid_schema_payload(tmp_path: Path) -> None:
    """Raise SchemaFormatError when schema yaml/json cannot be parsed."""
    schema_path = tmp_path / "broken.yaml"
    schema_path.write_text("header: [", encoding="utf-8")

    with pytest.raises(SchemaFormatError):
        prepare_artifact_producer_from_files(
            schema_file=str(schema_path),
            policy_file=str(_policy_file()),
            log_pipeline=Mock(),
        )


def test_prepare_from_files_happy_path_produce(tmp_path: Path) -> None:
    """prepare_artifact_producer_from_files returns producer that can produce_artifacts."""
    producer = prepare_artifact_producer_from_files(
        schema_file=str(_schema_file()),
        policy_file=str(_write_policy_file(tmp_path)),
        log_pipeline=Mock(),
    )
    result = producer.produce_artifacts([{"item_id": "SKU-1"}])
    assert result.validation_report is not None
    assert producer.target_label != ""


def test_prepare_from_files_passes_context_when_tax_mapping_is_supplied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build ProducerContext and pass it into compiler when tax_mapping is supplied."""
    observed: dict[str, Any] = {}

    class _CompilerStub:
        def __init__(self, *, catalog: Any) -> None:
            observed["catalog"] = catalog

        def compile(
            self,
            schema_doc: Any,
            *,
            context: ProducerContext | None = None,
        ) -> Any:
            observed["schema_doc"] = schema_doc
            observed["context"] = context
            return _compiled_stub(valid=True)

    monkeypatch.setattr(producer_mod, "SchemaCompiler", _CompilerStub)

    tax_mapping = {"mappings": {"Pet Supplies": "txcd_99999999"}}
    producer = prepare_artifact_producer_from_files(
        schema_file=str(_schema_file()),
        policy_file=str(_write_policy_file(tmp_path)),
        tax_mapping=tax_mapping,
        log_pipeline=Mock(),
    )

    assert isinstance(producer, ArtifactProducer)
    assert isinstance(observed["context"], ProducerContext)
    assert observed["context"].tax_mapping == tax_mapping


def test_prepare_from_files_omits_context_when_tax_mapping_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Call compiler without context when tax_mapping is not supplied."""
    observed: dict[str, Any] = {}

    class _CompilerStub:
        def __init__(self, *, catalog: Any) -> None:
            observed["catalog"] = catalog

        def compile(
            self,
            schema_doc: Any,
            *,
            context: ProducerContext | None = None,
        ) -> Any:
            observed["schema_doc"] = schema_doc
            observed["context"] = context
            return _compiled_stub(valid=True)

    monkeypatch.setattr(producer_mod, "SchemaCompiler", _CompilerStub)

    producer = prepare_artifact_producer_from_files(
        schema_file=str(_schema_file()),
        policy_file=str(_write_policy_file(tmp_path)),
        log_pipeline=Mock(),
    )

    assert isinstance(producer, ArtifactProducer)
    assert observed["context"] is None


def test_legacy_prepare_function_is_removed() -> None:
    """Ensure legacy prepare_artifact_producer symbol is not exposed anymore."""
    module = importlib.import_module("pfp_core.artifact_production.artifact_producer")
    with pytest.raises(AttributeError):
        getattr(module, "prepare_artifact_producer")


def test_legacy_artifact_building_module_is_removed() -> None:
    """Ensure removed artifact_building module is no longer importable."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("pfp_core.artifact_production.artifact_building")


def _compiled_stub(*, valid: bool = True) -> CompiledSchema:
    return cast(
        CompiledSchema,
        SimpleNamespace(
            artifact_profile="catalog_snapshot",
            validation_plan=object(),
            mapping_plan=object(),
            writer_spec=SimpleNamespace(
                writer_id="csv",
                writer_config={},
                artifact_content_type="text/csv",
                artifact_file_extension=".csv",
            ),
            diagnostics=(
                SimpleNamespace(
                    severity="ERROR",
                    code="COMPILE.FAIL",
                    message="compile fail",
                    path="schema.path",
                ),
            ),
            is_valid=valid,
        ),
    )


def _prepared_stub(*, valid: bool = True, target: str = "stripe.product"):
    return _PreparedSchema(
        schema_ref=SchemaRef(protocol_id=target, schema_version="1.0.0"),
        target_id=target,
        compiled=_compiled_stub(valid=valid),
        encoding="utf-8",
        validation_executor=None,
        mapping_executor=None,
        writer=None,
    )


def test_build_payload_iter_handles_drop_fail_and_mapping_issues(monkeypatch) -> None:
    """Ensure payload building aggregates invalid, drop, fail, and mapping diagnostics."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs
            self._idx = 0

        def run_one(self, **kwargs):
            del kwargs
            decisions = [
                (
                    "DROP",
                    [
                        SimpleNamespace(
                            severity="ERROR", code="VAL.DROP", message="d", path="p"
                        )
                    ],
                ),
                (
                    "FAIL",
                    [
                        SimpleNamespace(
                            severity="INFO", code="VAL.FAIL", message="f", path="q"
                        )
                    ],
                ),
            ]
            decision, items = decisions[self._idx]
            self._idx += 1
            return SimpleNamespace(decision=decision, items=items)

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                issues=[SimpleNamespace(code="MAP.ERR", message="m", path="x")],
                output={"k": Emission(kind="VALUE", value="v")},
            )

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))
    prepared = cast(Any, producer)._prepared_schema
    agg_report = ValidationReport(target="stripe.product", artifact_profile=None)

    out = list(
        producer._build_payload_iter(
            um_items=[1, {"id": "1"}, {"id": "2"}],
            prepared=prepared,
            aggregated_report=agg_report,
        )
    )
    assert out == []
    codes = [d.code for d in agg_report.diagnostics]
    assert "VALIDATION.INVALID_ITEM_TYPE" in codes
    assert "VAL.DROP" in codes
    assert "VAL.FAIL" in codes
    assert "BUILD.FAIL_STOP" in codes


def test_build_payload_iter_maps_and_yields_writer_records(monkeypatch) -> None:
    """Ensure mapped value emissions are yielded and mapping issues are reported."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(decision="PASS", items=[])

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                issues=[SimpleNamespace(code="MAP.ERR", message="m", path="x")],
                output={
                    "keep": Emission(kind="VALUE", value="v"),
                    "omit": Emission(kind="OMIT"),
                },
            )

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))
    prepared = cast(Any, producer)._prepared_schema
    agg_report = ValidationReport(target="stripe.product", artifact_profile=None)

    out = list(
        producer._build_payload_iter(
            um_items=[{"id": "1"}],
            prepared=prepared,
            aggregated_report=agg_report,
        )
    )
    assert out == [{"keep": "v"}]
    assert any(d.code == "MAP.ERR" for d in agg_report.diagnostics)


def test_produce_artifacts_no_diagnostics_on_produced_artifact(monkeypatch) -> None:
    """ProducedArtifact from produce_artifacts has no diagnostics field."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(decision="PASS", items=[])

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                issues=[], output={"id": Emission(kind="VALUE", value="X")}
            )

    class _FakeWriter:
        def write(self, payload):
            list(payload)
            return iter([b"ok\n"])

    class _FakeWriterRegistry:
        def create(self, *args, **kwargs):
            del args, kwargs
            return _FakeWriter()

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)
    monkeypatch.setattr(
        producer_mod, "build_default_writer_registry", lambda: _FakeWriterRegistry()
    )

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))
    result = producer.produce_artifacts([{"id": "A"}])
    assert len(result.artifacts) == 1
    assert not hasattr(result.artifacts[0], "diagnostics")


def test_produce_artifacts_single_validation_report_no_duplicates(monkeypatch) -> None:
    """produce_artifacts returns one validation_report — diagnostics not duplicated per-target."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                decision="PASS",
                items=[
                    SimpleNamespace(
                        severity="WARN", code="RULE.WARN", message="w", path="p"
                    )
                ],
            )

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                issues=[], output={"id": Emission(kind="VALUE", value="X")}
            )

    class _FakeWriter:
        def write(self, payload):
            list(payload)
            return iter([b"ok\n"])

    class _FakeWriterRegistry:
        def create(self, *args, **kwargs):
            del args, kwargs
            return _FakeWriter()

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)
    monkeypatch.setattr(
        producer_mod, "build_default_writer_registry", lambda: _FakeWriterRegistry()
    )

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))
    result = producer.produce_artifacts([{"id": "A"}])
    # exactly one diagnostic in the aggregated report (not duplicated)
    assert len(result.validation_report.diagnostics) == 1
    assert result.validation_report.diagnostics[0].code == "RULE.WARN"


def test_schema_format_suffix_resolution_and_timestamp_guards(tmp_path: Path) -> None:
    """Validate schema suffix detection and UTC timestamp guards for generated manifests."""

    assert producer_mod._resolve_schema_format_from_suffix(Path("a.yaml")) == "yaml"
    assert producer_mod._resolve_schema_format_from_suffix(Path("a.yml")) == "yaml"
    assert producer_mod._resolve_schema_format_from_suffix(Path("a.json")) == "json"
    with pytest.raises(SchemaFormatError):
        producer_mod._resolve_schema_format_from_suffix(Path("a.toml"))

    with pytest.raises(ValueError):
        producer_mod._ensure_generated_at_utc(datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        producer_mod._ensure_generated_at_utc(
            datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=3)))
        )
    assert (
        producer_mod._ensure_generated_at_utc(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
        ).tzinfo
        == timezone.utc
    )
    assert producer_mod.default_generated_at_utc().tzinfo is not None


def test_produce_artifacts_returns_compile_diagnostics_for_invalid_schema() -> None:
    """Invalid compiled schemas return no artifacts and surface compile diagnostics."""

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=False))

    result = producer.produce_artifacts([])

    assert result.artifacts == ()
    assert result.validation_report is not None
    assert result.validation_report.diagnostics[0].code == "COMPILE.FAIL"


def test_produce_artifacts_requires_writer_for_valid_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid prepared schemas must carry a writer before producing artifacts."""

    class _WriterRegistryWithoutWriter:
        def create(self, *args, **kwargs):
            del args, kwargs
            return None

    monkeypatch.setattr(
        producer_mod,
        "build_default_writer_registry",
        lambda: _WriterRegistryWithoutWriter(),
    )

    prepared = replace(_prepared_stub(valid=True), writer=None)
    producer = ArtifactProducer(prepared_schema=prepared)

    with pytest.raises(RuntimeError, match="prepared writer is required"):
        producer.produce_artifacts([])


def test_private_normalizers_and_mapping_output_helpers() -> None:
    """Cover severity normalizers, item reference extraction, and writer record shaping."""

    assert (
        producer_mod._normalize_compile_severity("err")
        == producer_mod.DiagnosticSeverity.ERROR
    )
    assert (
        producer_mod._normalize_compile_severity("warning")
        == producer_mod.DiagnosticSeverity.WARN
    )
    assert (
        producer_mod._normalize_compile_severity("info")
        == producer_mod.DiagnosticSeverity.INFO
    )
    assert (
        producer_mod._normalize_validation_severity("E")
        == producer_mod.DiagnosticSeverity.ERROR
    )
    assert (
        producer_mod._normalize_validation_severity("W")
        == producer_mod.DiagnosticSeverity.WARN
    )
    assert (
        producer_mod._normalize_validation_severity("x")
        == producer_mod.DiagnosticSeverity.INFO
    )

    assert producer_mod._extract_item_ref({"id": "  A  "}) == "A"
    assert producer_mod._extract_item_ref({"sku": "S"}) == "S"
    assert producer_mod._extract_item_ref({"pk": "P"}) == "P"
    assert producer_mod._extract_item_ref({"uuid": "U"}) == "U"
    assert producer_mod._extract_item_ref({"_id": "I"}) == "I"
    assert producer_mod._extract_item_ref({}) == "unknown"

    tuple_out = producer_mod._mapped_output_to_writer_record(
        (
            Emission(kind="VALUE", value="x"),
            Emission(kind="NULL"),
            Emission(kind="OMIT"),
        )
    )
    assert tuple_out == ("x", None, producer_mod.MISSING)

    dict_out = producer_mod._mapped_output_to_writer_record(
        {
            "v": Emission(kind="VALUE", value="x"),
            "n": Emission(kind="NULL"),
            "o": Emission(kind="OMIT"),
        }
    )
    assert dict_out == {"v": "x", "n": None}


def test_repeated_produce_reuses_prepared_execution_components(monkeypatch) -> None:
    """Ensure repeated production reuses prepared executors and writer instances."""

    counters = {
        "validation_ctor": 0,
        "mapping_ctor": 0,
        "writer_create": 0,
        "validation_run": 0,
        "mapping_run": 0,
    }

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs
            counters["validation_ctor"] += 1

        def run_one(self, **kwargs):
            del kwargs
            counters["validation_run"] += 1
            return SimpleNamespace(decision="PASS", items=[])

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs
            counters["mapping_ctor"] += 1

        def run_one(self, **kwargs):
            del kwargs
            counters["mapping_run"] += 1
            return SimpleNamespace(
                issues=[], output={"id": Emission(kind="VALUE", value="X")}
            )

    class _FakeWriter:
        def write(self, payload):
            list(payload)
            return iter([b"ok\n"])

    class _FakeWriterRegistry:
        def create(self, *args, **kwargs):
            del args, kwargs
            counters["writer_create"] += 1
            return _FakeWriter()

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)
    monkeypatch.setattr(
        producer_mod,
        "build_default_writer_registry",
        lambda: _FakeWriterRegistry(),
    )

    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))

    list(producer.produce_artifacts([{"id": "A"}]).artifacts[0].payload)
    list(producer.produce_artifacts([{"id": "B"}]).artifacts[0].payload)

    assert counters["validation_ctor"] == 1
    assert counters["mapping_ctor"] == 1
    assert counters["writer_create"] == 1
    assert counters["validation_run"] == 2
    assert counters["mapping_run"] == 2


def test_target_label_returns_protocol_id() -> None:
    """target_label returns schema_ref.protocol_id for single-schema producer (A17)."""
    producer = ArtifactProducer(
        prepared_schema=_prepared_stub(target="stripe.product_feed")
    )
    assert producer.target_label == "stripe.product_feed"


def test_runtime_guards_raise_for_broken_prepared_components() -> None:
    """Raise deterministic RuntimeError when prepared execution components are missing."""
    producer = ArtifactProducer(prepared_schema=_prepared_stub(valid=True))
    prepared = cast(Any, producer)._prepared_schema

    with pytest.raises(RuntimeError, match="prepared validation executor is required"):
        producer._build_payload_iter(
            um_items=[{"id": "A"}],
            prepared=replace(prepared, validation_executor=None),
            aggregated_report=ValidationReport(
                target="stripe.product",
                artifact_profile=None,
            ),
        )

    with pytest.raises(RuntimeError, match="prepared mapping executor is required"):
        producer._build_payload_iter(
            um_items=[{"id": "A"}],
            prepared=replace(prepared, mapping_executor=None),
            aggregated_report=ValidationReport(
                target="stripe.product",
                artifact_profile=None,
            ),
        )


# ---------------------------------------------------------------------------
# G3 — FaultIsolationPolicy integration with _build_payload_iter
# ---------------------------------------------------------------------------


def _bundle_with_fault_isolation(strategy: str) -> PolicyBundle:
    return PolicyBundle(
        strictness=StrictnessPolicy("fail_on_error"),
        fault_isolation=FaultIsolationPolicy(
            FaultIsolationConfig(strategy=strategy),
            log_pipeline=Mock(),
        ),
    )


def test_build_payload_iter_skip_item_continues_on_mapping_error(monkeypatch) -> None:
    """SKIP_ITEM: mapping RuntimeError is caught, item skipped, other items processed."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(decision="PASS", items=[])

    call_count = {"n": 0}

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("mapping exploded")
            return SimpleNamespace(
                issues=[],
                output={"id": Emission(kind="VALUE", value="ok")},
            )

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)

    producer = ArtifactProducer(
        prepared_schema=_prepared_stub(valid=True),
        policies=_bundle_with_fault_isolation("SKIP_ITEM"),
    )
    prepared = cast(Any, producer)._prepared_schema
    agg_report = ValidationReport(target="stripe.product", artifact_profile=None)

    out = list(
        producer._build_payload_iter(
            um_items=[{"id": "bad"}, {"id": "good"}],
            prepared=prepared,
            aggregated_report=agg_report,
        )
    )

    # First item skipped due to error, second item processed successfully
    assert out == [{"id": "ok"}]
    assert call_count["n"] == 2


def test_build_payload_iter_fail_fast_propagates_on_mapping_error(monkeypatch) -> None:
    """FAIL_FAST: mapping RuntimeError propagates out of produce_artifacts."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(decision="PASS", items=[])

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            raise RuntimeError("mapping exploded")

    class _FakeWriter:
        def write(self, payload):
            return list(payload)

    class _FakeWriterRegistry:
        def create(self, *args, **kwargs):
            del args, kwargs
            return _FakeWriter()

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)
    monkeypatch.setattr(
        producer_mod, "build_default_writer_registry", lambda: _FakeWriterRegistry()
    )

    producer = ArtifactProducer(
        prepared_schema=_prepared_stub(valid=True),
        policies=_bundle_with_fault_isolation("FAIL_FAST"),
    )

    with pytest.raises(RuntimeError, match="mapping exploded"):
        producer.produce_artifacts([{"id": "bad"}])


def test_build_payload_iter_no_policies_propagates_exception(monkeypatch) -> None:
    """policies=None: exception in mapping propagates as before (backward compat)."""

    class _FakeValidationExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            return SimpleNamespace(decision="PASS", items=[])

    class _FakeMappingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def run_one(self, **kwargs):
            del kwargs
            raise RuntimeError("unexpected error")

    class _FakeWriter:
        def write(self, payload):
            return list(payload)

    class _FakeWriterRegistry:
        def create(self, *args, **kwargs):
            del args, kwargs
            return _FakeWriter()

    monkeypatch.setattr(producer_mod, "ValidationExecutor", _FakeValidationExecutor)
    monkeypatch.setattr(producer_mod, "MappingExecutor", _FakeMappingExecutor)
    monkeypatch.setattr(
        producer_mod, "build_default_writer_registry", lambda: _FakeWriterRegistry()
    )

    producer = ArtifactProducer(
        prepared_schema=_prepared_stub(valid=True),
        policies=None,
    )

    with pytest.raises(RuntimeError, match="unexpected error"):
        producer.produce_artifacts([{"id": "x"}])


def test_resolve_artifact_encoding_defaults_and_override() -> None:
    """_resolve_artifact_encoding: default utf-8, explicit override, whitespace-only fallback."""
    assert producer_mod._resolve_artifact_encoding({}) == "utf-8"
    assert producer_mod._resolve_artifact_encoding({"output": {}}) == "utf-8"
    assert (
        producer_mod._resolve_artifact_encoding(
            {"output": {"artifact": {"encoding": " cp1251 "}}}
        )
        == "cp1251"
    )
    assert (
        producer_mod._resolve_artifact_encoding(
            {"output": {"artifact": {"encoding": "   "}}}
        )
        == "utf-8"
    )
