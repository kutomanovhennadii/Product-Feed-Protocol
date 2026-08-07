"""Integration tests for the pfp_runtime.config block."""

from __future__ import annotations

from pathlib import Path

from pfp_runtime.config.infra_provider import InfraProvider


def _python_root() -> Path:
    """Return the project project root.

    Returns:
        Repository root path for the Python workspace.
    """

    return Path(__file__).resolve().parents[3]


def test_infra_provider_loads_validated_and_normalized_fixture_config() -> None:
    """Config provider loads, validates, and normalizes the manifest fixture infra."""

    root = _python_root()
    infra = InfraProvider().get_infra(
        str(
            root
            / "tests"
            / "pfp_runtime"
            / "manifest"
            / "fixtures"
            / "pipeline_manifest_provider"
            / "infra.yaml"
        )
    )

    assert infra.input.format == "csv"
    assert infra.input.config.connector_mapping is not None
    assert infra.input.config.connector_mapping.endswith("mapping.yaml")
    assert Path(infra.input.config.connector_mapping).is_absolute()
    assert Path(infra.output.archive_config).is_absolute()
    assert Path(infra.output.client_config).is_absolute()
    assert Path(infra.producer.schema_file).is_absolute()
    assert Path(infra.producer.policy_file).is_absolute()


def test_infra_provider_normalizes_optional_tax_mapping_path(tmp_path: Path) -> None:
    """Config provider resolves optional tax_mapping_file relative to infra.yaml.

    Args:
        tmp_path: Temporary directory that hosts the generated infra and tax files.
    """

    root = _python_root()
    tax_mapping = tmp_path / "tax_mapping.json"
    tax_mapping.write_text('{"mappings": {}}\n', encoding="utf-8")
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        "\n".join(
            [
                "input:",
                "  format: csv",
                "  config:",
                f"    connector_mapping: {root / 'config' / 'mapping.yaml'}",
                "producer:",
                f"  schema_file: {root / 'schemas' / 'stripe.product_feed' / 'stripe.product_feed-1.0.0.yaml'}",
                f"  policy_file: {root / 'config' / 'policies.yaml'}",
                "  tax_mapping_file: ./tax_mapping.json",
                "output:",
                "  archive_type: noop",
                f"  archive_config: {root / 'config' / 'archive' / 'noop.yaml'}",
                "  client_type: noop",
                f"  client_config: {root / 'config' / 'clients' / 'noop.yaml'}",
            ]
        ),
        encoding="utf-8",
    )

    infra = InfraProvider().get_infra(str(infra_path))

    assert infra.producer.tax_mapping_file == str(tax_mapping.resolve())
