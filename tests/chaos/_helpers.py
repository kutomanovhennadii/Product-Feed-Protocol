"""Shared helpers for chaos tests. Hermetic and scoped to test-owned temp files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Final

from pfp_runtime.connectors.adapters.jsonl_adapter import JsonlAdapter
from pfp_runtime.manifest.pipeline_manifest import PipelineManifest
from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.shell.factory import PFPFactory, PFPWorker
from pfp_utils.logging.log_pipeline import LogPipeline
from pfp_utils.logging.log_registry import InMemoryLoggingRegistry

_PYTHON_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DEFAULT_MAPPING_RELATIVE: Final[str] = "config/shopify_bulk/mapping_shopify_bulk.yaml"
_CSV_HEADER: Final[str] = "id,title,description,link,availability\n"
_VALID_JSONL_RECORD: Final[dict[str, Any]] = {
    "id": "gid://shopify/ProductVariant/1",
    "title": "Chaos Item",
    "descriptionHtml": "<p>Desc</p>",
    "onlineStoreUrl": "https://example.test/products/chaos-1",
    "vendor": "BrandCo",
    "barcode": "0123456789012",
    "sku": "CHAOS-1",
    "image": "https://example.test/images/1.jpg",
    "media": "",
    "category": "Apparel & Accessories > Clothing > Shirts & Tops",
    "productType": "Chaos Shirts",
    "weight": "0.3 kg",
    "__parentProductId": "gid://shopify/Product/1",
    "__parentTitle": "Chaos Family",
    "color": "Black",
    "size": "M",
    "availableForSale": True,
    "inventoryQuantity": 5,
    "price": "29.99",
    "compareAtPrice": "39.99",
    "shipping": [{"country": "US", "service": "Ground", "price": "5.99 USD"}],
    "stripe_tax_code_override": "",
    "taxable": True,
}


_ADAPTER_LOG_PIPELINE: Final[LogPipeline] = LogPipeline(
    level="ERROR",
    format_type="TEXT",
    filters=(),
    formatter=logging.Formatter("%(message)s"),
    handler=logging.NullHandler(),
    registry=InMemoryLoggingRegistry(),
)


def write_minimal_infra(
    tmp_path: Path,
    *,
    input_format: str = "jsonl",
    schema_relpath: str = "schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml",
    archive_config_relpath: str = "config/archive/noop.yaml",
    client_config_relpath: str = "config/clients/noop.yaml",
) -> Path:
    """Build a minimal infra.yaml in tmp_path that points at production assets."""
    return _write_infra(
        tmp_path,
        input_format=input_format,
        connector_mapping_path=_PYTHON_ROOT / _DEFAULT_MAPPING_RELATIVE,
        schema_path=_PYTHON_ROOT / schema_relpath,
        archive_config_path=_PYTHON_ROOT / archive_config_relpath,
        client_config_path=_PYTHON_ROOT / client_config_relpath,
    )


def write_producer_validation_infra(tmp_path: Path) -> Path:
    """Build a temp infra that routes JSONL records straight into core validation.

    This helper is intentionally separate from ``write_minimal_infra`` because
    the default shopify mapping drops malformed records earlier in connector and
    producer layers. For producer-chaos probes we need a tiny mapping that keeps
    records flowing into schema/policy validation so the tests can exercise the
    current fail-stop contract there.
    """
    mapping_path = tmp_path / "producer_mapping.yaml"
    mapping_path.write_text(
        "\n".join(
            [
                "mappings:",
                '  - source: "item_id"',
                '    target: "product.item_id"',
                '  - source: "title"',
                '    target: "product.title"',
                "continue_on_error: true",
            ]
        ),
        encoding="utf-8",
    )
    return _write_infra(
        tmp_path,
        input_format="jsonl",
        connector_mapping_path=mapping_path,
        schema_path=_PYTHON_ROOT
        / "schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml",
        archive_config_path=_PYTHON_ROOT / "config/archive/noop.yaml",
        client_config_path=_PYTHON_ROOT / "config/clients/noop.yaml",
    )


def build_worker(infra_path: Path) -> PFPWorker:
    """Build a PFPWorker via PFPFactory."""
    return PFPFactory().build_worker(infra_path=infra_path)


def build_manifest(infra_path: Path) -> PipelineManifest:
    """Build a PipelineManifest for tests that patch publisher behavior."""
    return build_pipeline_manifest(str(infra_path))


def valid_jsonl_input() -> bytes:
    """Return one JSONL record that reaches the publish step on current runtime."""
    return (json.dumps(_VALID_JSONL_RECORD) + "\n").encode("utf-8")


def csv_payload_text(report: ExecutionReport) -> str:
    """Decode the first artifact payload as text."""
    artifact = report.artifacts[0]
    return b"".join(artifact.payload).decode(artifact.metadata.encoding)


def expected_header() -> str:
    """Return the header-only CSV payload emitted by empty or fail-stop runs."""
    return _CSV_HEADER


def jsonl_max_line_bytes() -> int:
    """Return the current JSONL adapter line-size limit."""
    return JsonlAdapter({}, log_pipeline=_ADAPTER_LOG_PIPELINE).max_line_bytes


def _write_infra(
    tmp_path: Path,
    *,
    input_format: str,
    connector_mapping_path: Path,
    schema_path: Path,
    archive_config_path: Path,
    client_config_path: Path,
) -> Path:
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        "\n".join(
            [
                "input:",
                f"  format: {input_format}",
                "  config:",
                f"    connector_mapping: {connector_mapping_path}",
                "producer:",
                f"  schema_file: {schema_path}",
                f"  policy_file: {_PYTHON_ROOT / 'config/policies.yaml'}",
                "output:",
                "  archive_type: noop",
                f"  archive_config: {archive_config_path}",
                "  client_type: noop",
                f"  client_config: {client_config_path}",
            ]
        ),
        encoding="utf-8",
    )
    return infra_path


__all__ = [
    "build_manifest",
    "build_worker",
    "csv_payload_text",
    "diagnostics_by_severity",
    "expected_header",
    "jsonl_max_line_bytes",
    "valid_jsonl_input",
    "write_minimal_infra",
    "write_producer_validation_infra",
]


def diagnostics_by_severity(report: ExecutionReport, severity: str) -> list[str]:
    """Return diagnostic codes for a single normalized severity."""
    normalized = severity.upper()
    return [
        diagnostic.code
        for diagnostic in report.validation_report.diagnostics
        if str(diagnostic.severity).upper() == normalized
    ]
