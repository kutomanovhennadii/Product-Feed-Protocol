"""Shared helpers for pfp_runtime integration tests."""

from __future__ import annotations

from pathlib import Path

_RUNTIME_CSV_INPUT = (
    b"sku,name,description,url,availability\n"
    b"SKU-1,Runner,Lightweight shoe,https://example.test/products/sku-1,IN_STOCK\n"
)


def python_root() -> Path:
    """Return the project repository root for runtime integration tests.

    Returns:
        Repository root path for the Python workspace.
    """

    return Path(__file__).resolve().parents[2]


def runtime_csv_input() -> bytes:
    """Return the canonical CSV payload reused across runtime integration tests.

    Returns:
        CSV bytes containing one product row.
    """

    return _RUNTIME_CSV_INPUT


def write_runtime_infra(
    tmp_path: Path,
    *,
    connector_mapping: str | Path | None = None,
    schema_file: str | Path | None = None,
    policy_file: str | Path | None = None,
    archive_type: str = "noop",
    archive_config: str | Path | None = None,
    client_type: str = "noop",
    client_config: str | Path | None = None,
) -> Path:
    """Create a runtime infra file pointing at real project assets.

    Args:
        tmp_path: Temporary directory that will contain the generated infra YAML.
        connector_mapping: Optional override for the connector mapping file.
        schema_file: Optional override for the producer schema file.
        policy_file: Optional override for the producer policy file.
        archive_type: Archive provider key stored in the generated infra file.
        archive_config: Optional override for the archive IaC path.
        client_type: Delivery client key stored in the generated infra file.
        client_config: Optional override for the client IaC path.

    Returns:
        Path to the generated runtime infra YAML file.
    """

    root = python_root()
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        "\n".join(
            [
                "input:",
                "  format: csv",
                "  config:",
                f"    connector_mapping: {connector_mapping or (root / 'config' / 'mapping.yaml')}",
                "producer:",
                f"  schema_file: {schema_file or (root / 'schemas' / 'stripe.product_feed' / 'stripe.product_feed-1.0.0.yaml')}",
                f"  policy_file: {policy_file or (root / 'config' / 'policies.yaml')}",
                "output:",
                f"  archive_type: {archive_type}",
                f"  archive_config: {archive_config or (root / 'config' / 'archive' / 'noop.yaml')}",
                f"  client_type: {client_type}",
                f"  client_config: {client_config or (root / 'config' / 'clients' / 'noop.yaml')}",
            ]
        ),
        encoding="utf-8",
    )
    return infra_path
