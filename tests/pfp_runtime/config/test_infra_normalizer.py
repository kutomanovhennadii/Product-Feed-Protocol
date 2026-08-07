"""Unit tests for infra path normalization in config layer."""

from __future__ import annotations

from pathlib import Path

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_normalizer import normalize_infra_paths


def _make_infra(
    *,
    schema_file: str,
    policy_file: str,
    connector_mapping: str,
    tax_mapping_file: str | None = None,
    archive_config: str = "./archive/local.yaml",
    client_config: str = "./clients/noop.yaml",
) -> InfraConfig:
    """Build minimal infra model for normalizer tests."""
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {
                    "connector_mapping": connector_mapping,
                },
            },
            "output": {
                "archive_type": "local",
                "archive_config": archive_config,
                "client_type": "noop",
                "client_config": client_config,
            },
            "producer": {
                "schema_file": schema_file,
                "policy_file": policy_file,
                "tax_mapping_file": tax_mapping_file,
            },
        }
    )


def test_normalizer_resolves_relative_paths_against_infra_dir(tmp_path: Path) -> None:
    """Resolve relative producer and mapping paths against infra.yaml directory."""
    infra_dir = tmp_path / "run"
    infra_dir.mkdir()

    schema_file = infra_dir / "schema.yaml"
    policy_file = infra_dir / "policy.yaml"
    mapping_file = infra_dir / "mapping.json"
    archive_file = infra_dir / "archive" / "local.yaml"
    client_file = infra_dir / "clients" / "noop.yaml"

    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")
    mapping_file.write_text("{}\n", encoding="utf-8")
    archive_file.parent.mkdir()
    archive_file.write_text("mode: local\n", encoding="utf-8")
    client_file.parent.mkdir()
    client_file.write_text("mode: noop\n", encoding="utf-8")

    infra = _make_infra(
        schema_file="./schema.yaml",
        policy_file="./policy.yaml",
        connector_mapping="./mapping.json",
    )

    normalized = normalize_infra_paths(infra, infra_path=str(infra_dir / "infra.yaml"))

    assert normalized.output.archive_config == str(archive_file.resolve())
    assert normalized.output.client_config == str(client_file.resolve())
    assert normalized.producer.schema_file == str(schema_file.resolve())
    assert normalized.producer.policy_file == str(policy_file.resolve())
    assert normalized.input.config.connector_mapping == str(mapping_file.resolve())


def test_normalizer_keeps_absolute_paths_absolute(tmp_path: Path) -> None:
    """Keep absolute producer and mapping paths as absolute resolved values."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    mapping_file = tmp_path / "mapping.json"

    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")
    mapping_file.write_text("{}\n", encoding="utf-8")

    infra = _make_infra(
        schema_file=str(schema_file.resolve()),
        policy_file=str(policy_file.resolve()),
        connector_mapping=str(mapping_file.resolve()),
        archive_config=str((tmp_path / "archive" / "local.yaml").resolve()),
        client_config=str((tmp_path / "clients" / "noop.yaml").resolve()),
    )

    normalized = normalize_infra_paths(infra, infra_path=str(tmp_path / "infra.yaml"))

    assert normalized.output.archive_config == str(
        (tmp_path / "archive" / "local.yaml").resolve()
    )
    assert normalized.output.client_config == str(
        (tmp_path / "clients" / "noop.yaml").resolve()
    )
    assert normalized.producer.schema_file == str(schema_file.resolve())
    assert normalized.producer.policy_file == str(policy_file.resolve())
    assert normalized.input.config.connector_mapping == str(mapping_file.resolve())


def test_normalizer_falls_back_to_project_root_for_missing_local_files() -> None:
    """Fallback producer and output paths to project root when local files are absent."""
    python_root = Path(__file__).resolve().parents[3]
    schema_file = (
        python_root
        / "schemas"
        / "stripe.product_feed"
        / "stripe.product_feed-1.0.0.yaml"
    )
    policy_file = python_root / "config" / "policies.yaml"
    archive_config = python_root / "config" / "archive" / "local.yaml"
    client_config = python_root / "config" / "clients" / "noop.yaml"

    infra = _make_infra(
        schema_file="schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml",
        policy_file="config/policies.yaml",
        connector_mapping="./mapping.json",
        archive_config="config/archive/local.yaml",
        client_config="config/clients/noop.yaml",
    )

    fake_infra_path = python_root / "tests" / "fixtures" / "another" / "infra.yaml"
    normalized = normalize_infra_paths(infra, infra_path=str(fake_infra_path))

    assert normalized.output.archive_config == str(archive_config.resolve())
    assert normalized.output.client_config == str(client_config.resolve())
    assert normalized.producer.schema_file == str(schema_file.resolve())
    assert normalized.producer.policy_file == str(policy_file.resolve())


def test_normalizer_resolves_optional_tax_mapping_path(tmp_path: Path) -> None:
    """Resolve optional producer.tax_mapping_file against infra.yaml directory."""
    infra_dir = tmp_path / "run"
    infra_dir.mkdir()

    tax_mapping_file = infra_dir / "tax_mapping.json"
    tax_mapping_file.write_text('{"mappings": {}}\n', encoding="utf-8")

    infra = _make_infra(
        schema_file=str((tmp_path / "schema.yaml").resolve()),
        policy_file=str((tmp_path / "policy.yaml").resolve()),
        connector_mapping=str((tmp_path / "mapping.json").resolve()),
        archive_config=str((tmp_path / "archive" / "local.yaml").resolve()),
        client_config=str((tmp_path / "clients" / "noop.yaml").resolve()),
        tax_mapping_file="./tax_mapping.json",
    )

    normalized = normalize_infra_paths(infra, infra_path=str(infra_dir / "infra.yaml"))

    assert normalized.producer.tax_mapping_file == str(tax_mapping_file.resolve())


def test_provider_returns_normalized_absolute_paths(tmp_path: Path) -> None:
    """Provider integration surface returns absolute normalized producer paths."""
    from pfp_runtime.config.infra_provider import InfraProvider

    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"

    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        "input:\n"
        "  format: csv\n"
        "  config:\n"
        "    connector_mapping: ./mapping.yaml\n"
        "output:\n"
        "  archive_type: local\n"
        "  archive_config: ./archive/local.yaml\n"
        "  client_type: noop\n"
        "  client_config: ./clients/noop.yaml\n"
        "producer:\n"
        "  schema_file: ./schema.yaml\n"
        "  policy_file: ./policy.yaml\n",
        encoding="utf-8",
    )

    normalized = InfraProvider().get_infra(str(infra_path))

    assert Path(normalized.output.archive_config).is_absolute()
    assert Path(normalized.output.client_config).is_absolute()
    assert Path(normalized.producer.schema_file).is_absolute()
    assert Path(normalized.producer.policy_file).is_absolute()
