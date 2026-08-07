import json
from pathlib import Path


EXPECTED_ENTRYPOINTS = {
    "module": "pfp_runtime",
    "factory": "PFPFactory",
    "factory_method": "build_worker",
    "worker": "PFPWorker",
    "factory_helper": "get_pfp_factory",
}

EXPECTED_STATUSES = ["SUCCESS", "FAILED"]
EXPECTED_FAILED_STEPS = [
    "INGESTION_EXTRACT",
    "CORE_BUILD",
    "PUBLISH",
    "INTERNAL",
]
EXPECTED_REASON_CODES = [
    "INGESTION.EXTRACT_TIMEOUT",
    "INGESTION.EXTRACT_ERROR",
    "CORE.CONTRACT_ERROR",
    "CORE.VALIDATION_FAILED",
    "INTERNAL.ERROR",
    "PUBLISH.TIMEOUT",
    "PUBLISH.ERROR",
]
EXPECTED_REFERENCES = {
    "api_docs": "docs/api.md",
    "yaml_reference": "config/docs/README.md",
    "config_infrastructure": "config/docs/01_infra.md",
    "config_mapping": "config/docs/02_mapping.md",
    "config_policies": "config/docs/03_policies.md",
    "determinism_rules": "docs/determinism.md",
    "troubleshooting": "docs/troubleshooting.md",
    "quickstart_example": "examples/01_minimal_quickstart/README.md",
}


def _root_dir() -> Path:
    return Path(__file__).parent.parent


def _read_text(relative_path: str) -> str:
    return (_root_dir() / relative_path).read_text(encoding="utf-8")


def _load_contract() -> dict:
    contract_path = _root_dir() / "agent_contract.json"
    assert contract_path.exists(), "agent_contract.json is missing"
    try:
        return json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"agent_contract.json is not valid JSON: {exc}") from exc


def test_agent_contract_json_matches_runtime_surface() -> None:
    """Agent contract JSON must match the current runtime entrypoints and outcome model."""
    contract = _load_contract()

    assert contract["entrypoints"]["module"] == EXPECTED_ENTRYPOINTS["module"]
    assert contract["entrypoints"]["factory"] == EXPECTED_ENTRYPOINTS["factory"]
    assert contract["entrypoints"]["factory_method"] == EXPECTED_ENTRYPOINTS["factory_method"]
    assert contract["entrypoints"]["worker"] == EXPECTED_ENTRYPOINTS["worker"]
    assert contract["entrypoints"]["factory_helper"] == EXPECTED_ENTRYPOINTS["factory_helper"]
    assert "worker.run(" in contract["entrypoints"]["usage_example"]
    assert "read_bytes()" in contract["entrypoints"]["usage_example"]

    assert contract["error_model"]["execution_report_statuses"] == EXPECTED_STATUSES
    assert contract["error_model"]["failed_step_tokens"] == EXPECTED_FAILED_STEPS
    assert contract["error_model"]["reason_codes"] == EXPECTED_REASON_CODES
    assert contract["references"] == EXPECTED_REFERENCES


def test_agent_contract_references_and_ci_step_exist() -> None:
    """Story 9 contract must include resolvable references and a dedicated CI validation step."""
    contract = _load_contract()
    root_dir = _root_dir()

    for key, rel_path in contract["references"].items():
        assert (root_dir / rel_path).exists(), (
            f"Reference '{key}' points to non-existent file: {rel_path}"
        )

    diff_ref = contract["diff_semantics"]["reference"]
    assert (root_dir / diff_ref).exists(), (
        f"diff_semantics reference points to non-existent file: {diff_ref}"
    )

    ci_source = _read_text(".github/workflows/ci.yml")
    assert "Validate agent contract" in ci_source
    assert "pytest tests/test_agent_contract.py -q" in ci_source


def test_agent_docs_match_runtime_contract() -> None:
    """AGENT.md and api.md must describe the same runtime contract as the JSON file."""
    agent_doc = _read_text("AGENT.md")
    api_doc = _read_text("docs/api.md")
    factory_source = _read_text("src/pfp_runtime/shell/factory.py")
    report_step_source = _read_text("src/pfp_runtime/pipeline/report_step.py")
    ingestion_guard_source = _read_text("src/pfp_runtime/pipeline/ingestion_guard.py")
    core_guard_source = _read_text("src/pfp_runtime/pipeline/core_guard.py")
    publish_guard_source = _read_text("src/pfp_runtime/pipeline/publish_guard.py")
    pipeline_runner_source = _read_text("src/pfp_runtime/orchestration/pipeline_runner.py")

    assert "def build_worker(" in factory_source
    assert "infra_path: Union[str, Path]" in factory_source
    assert "def run(self, input_data: bytes)" in factory_source
    assert 'status="FAILED" if is_failed else "SUCCESS"' in report_step_source
    assert 'return "INGESTION.EXTRACT_TIMEOUT"' in ingestion_guard_source
    assert 'return "INGESTION.EXTRACT_ERROR"' in ingestion_guard_source
    assert 'return "CORE.CONTRACT_ERROR"' in core_guard_source
    assert 'return "INTERNAL.ERROR"' in core_guard_source
    assert 'return "PUBLISH.TIMEOUT"' in publish_guard_source
    assert 'return "PUBLISH.ERROR"' in publish_guard_source
    assert 'ctx.reason_code = "CORE.VALIDATION_FAILED"' in pipeline_runner_source

    assert "PFPWorker.run(input_data: bytes)" in agent_doc
    assert "SUCCESS" in agent_doc
    assert "FAILED" in agent_doc
    assert "pytest tests/test_agent_contract.py -q" in agent_doc

    assert "`PFPWorker.run(input_bytes)` returns an `ExecutionReport`." in api_doc
    assert "`SUCCESS`" in api_doc
    assert "`FAILED`" in api_doc
    for reason_code in EXPECTED_REASON_CODES:
        assert reason_code in api_doc
