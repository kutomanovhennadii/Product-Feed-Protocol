"""Unit tests for canonical infra provider facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import pfp_runtime.config.infra_provider as provider_module
from pfp_runtime.config.infra_loader import InfraConfigParseError
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_provider import InfraProvider
from pfp_runtime.config.infra_validator import InfraConfigValidationError


def _valid_yaml(
    schema_file: str,
    policy_file: str,
    *,
    input_format: str = "csv",
    observability_block: str = "",
) -> str:
    """Build YAML config for provider tests.

    Args:
        schema_file: Producer schema path written into the YAML payload.
        policy_file: Producer policy path written into the YAML payload.
        input_format: Input format token used in the generated YAML.
        observability_block: Optional observability YAML block appended verbatim.

    Returns:
        YAML payload string accepted by the infra loader.
    """
    return (
        "input:\n"
        f"  format: {input_format}\n"
        "  config:\n"
        "    connector_mapping: ./mapping.yaml\n"
        "output:\n"
        "  archive_type: local\n"
        "  archive_config: ./archive/local.yaml\n"
        "  client_type: noop\n"
        "  client_config: ./clients/noop.yaml\n"
        "producer:\n"
        f"  schema_file: {schema_file}\n"
        f"  policy_file: {policy_file}\n"
        f"{observability_block}"
    )


def test_provider_calls_loader_and_validator_as_single_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider composes load+validate in one thin entrypoint."""
    calls = {"load": 0, "validate": 0, "normalize": 0}
    infra = InfraConfig.model_validate(
        {
            "input": {"format": "csv", "config": {}},
            "output": {
                "archive_type": "local",
                "archive_config": "./archive/local.yaml",
                "client_type": "noop",
                "client_config": "./clients/noop.yaml",
            },
            "producer": {
                "schema_file": "./schema.yaml",
                "policy_file": "./policy.yaml",
            },
        }
    )

    def _fake_load(path: str) -> InfraConfig:
        calls["load"] += 1
        assert path.endswith("infra.yaml")
        return infra

    def _fake_validate(value: InfraConfig, *, infra_path: str):
        calls["validate"] += 1
        assert value is infra
        assert infra_path.endswith("infra.yaml")
        return value

    def _fake_normalize(value: InfraConfig, *, infra_path: str) -> InfraConfig:
        calls["normalize"] += 1
        assert value is infra
        assert infra_path.endswith("infra.yaml")
        return value

    monkeypatch.setattr(provider_module, "load_infra_config", _fake_load)
    monkeypatch.setattr(provider_module, "validate_infra_config", _fake_validate)
    monkeypatch.setattr(provider_module, "normalize_infra_paths", _fake_normalize)

    result = InfraProvider().get_infra("./infra.yaml")

    assert calls == {"load": 1, "validate": 1, "normalize": 1}
    assert result is infra


def test_provider_returns_validated_infra_config(tmp_path: Path) -> None:
    """Provider returns canonical validated InfraConfig object."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        _valid_yaml("./schema.yaml", "./policy.yaml"),
        encoding="utf-8",
    )

    infra = InfraProvider().get_infra(str(infra_path))

    assert isinstance(infra, InfraConfig)
    assert infra.input.format == "csv"


def test_provider_does_not_mask_loader_error() -> None:
    """Provider propagates loader parse/read errors unchanged."""
    with pytest.raises(InfraConfigParseError):
        InfraProvider().get_infra("./does-not-exist.yaml")


def test_provider_fails_on_semantic_invalid_after_loader_materialization(
    tmp_path: Path,
) -> None:
    """Loader materializes config but provider fails on validator semantic stage."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        _valid_yaml("./schema.yaml", "./policy.yaml", input_format="custom-source"),
        encoding="utf-8",
    )

    with pytest.raises(
        InfraConfigValidationError,
        match="input.format token 'custom-source' is missing in connectors registry",
    ):
        InfraProvider().get_infra(str(infra_path))


def test_provider_preserves_valid_flood_control_subtree_through_full_route(
    tmp_path: Path,
) -> None:
    """Provider keeps valid flood-control config through load+validate+normalize route."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    mapping_file = tmp_path / "mapping.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")
    mapping_file.write_text("mappings: []\n", encoding="utf-8")

    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        _valid_yaml(
            "./schema.yaml",
            "./policy.yaml",
            observability_block=(
                "observability:\n"
                "  labels:\n"
                "    env: test\n"
                "  logging:\n"
                "    level: INFO\n"
                "    flood_control_config:\n"
                "      enabled: true\n"
                "      mode: deduplicate\n"
                "      context_keys:\n"
                "        - item_ref\n"
                "        - run_id\n"
                "      suppressed_levels:\n"
                "        - INFO\n"
                "        - WARNING\n"
                "      force_log_attr: force_log\n"
                "      key_fields:\n"
                "        - name\n"
                "        - levelno\n"
                "        - msg\n"
                "      window_seconds: 12.5\n"
                "      max_events_per_window: 2\n"
                "      emit_summary: true\n"
                "      summary_level: WARNING\n"
                "      summary_interval_seconds: 60.0\n"
                "      max_cache_size: 2048\n"
            ),
        ),
        encoding="utf-8",
    )

    infra = InfraProvider().get_infra(str(infra_path))

    assert infra.input.config.connector_mapping == str(mapping_file.resolve())
    assert infra.observability is not None
    assert infra.observability.logging.flood_control_config.mode == "deduplicate"
    assert infra.observability.logging.flood_control_config.context_keys == [
        "item_ref",
        "run_id",
    ]


def test_provider_wraps_invalid_flood_control_config_from_validator(
    tmp_path: Path,
) -> None:
    """Provider surfaces flood-control semantic errors from validator stage."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(
        _valid_yaml(
            "./schema.yaml",
            "./policy.yaml",
            observability_block=(
                "observability:\n"
                "  labels:\n"
                "    env: test\n"
                "  logging:\n"
                "    level: INFO\n"
                "    flood_control_config:\n"
                "      mode: invalid-mode\n"
            ),
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        InfraConfigValidationError,
        match=(
            "observability\\.logging\\.flood_control_config: "
            "Invalid flood control mode: invalid-mode"
        ),
    ):
        InfraProvider().get_infra(str(infra_path))


@pytest.mark.parametrize(
    "relative_infra_path,pipeline_label",
    [
        ("config/infra.yaml", "product-feed"),
        ("config/shopify_bulk/infra_shopify_bulk.yaml", "shopify-catalog-bulk"),
        (
            "config/shopify_delete/infra_shopify_delete.yaml",
            "shopify-catalog-delete",
        ),
        (
            "config/shopify_inventory/infra_shopify_inventory.yaml",
            "shopify-inventory",
        ),
        (
            "config/shopify_realtime/infra_shopify_realtime.yaml",
            "shopify-catalog-realtime",
        ),
    ],
)
def test_provider_materializes_operational_flood_control_baseline_from_real_yaml(
    relative_infra_path: str,
    pipeline_label: str,
) -> None:
    """Materialize default flood-control subtree from operational infra YAML files.

    Args:
        relative_infra_path: Repo-relative path to canonical operational infra.
        pipeline_label: Expected observability label from the selected infra.

    Returns:
        None.
    """
    project_root = Path(__file__).resolve().parents[3]
    infra_path = project_root / relative_infra_path

    infra = InfraProvider().get_infra(str(infra_path))
    assert infra.observability is not None
    flood_control: dict[str, Any] = (
        infra.observability.logging.flood_control_config.model_dump(exclude_none=True)
    )

    assert infra.observability.labels["pipeline"] == pipeline_label
    assert flood_control == {
        "enabled": True,
        "mode": "context_info_suppression",
        "context_keys": ["item_ref"],
        "suppressed_levels": ["INFO"],
        "force_log_attr": "force_log",
        "key_fields": ["name", "levelno", "msg", "item_ref"],
        "window_seconds": 30.0,
        "max_events_per_window": 1,
        "emit_summary": False,
        "summary_level": "INFO",
        "summary_interval_seconds": 30.0,
        "max_cache_size": 10000,
    }
