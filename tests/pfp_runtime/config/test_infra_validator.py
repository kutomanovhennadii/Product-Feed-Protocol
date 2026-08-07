"""Unit tests for canonical infra validator helpers."""

from pathlib import Path
from typing import Any, Dict

import pytest

from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_validator import (
    InfraConfigValidationError,
    validate_infra_config,
)


def _config() -> Dict[str, Any]:
    """Build valid canonical infra config (publisher v2 schema)."""
    return {
        "input": {"format": "json", "config": {}},
        "output": {
            "archive_type": "local",
            "archive_config": "./archive/local.yaml",
            "client_type": "noop",
            "client_config": "./clients/noop.yaml",
        },
        "producer": {
            "schema_file": "./schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml",
            "policy_file": "./config/policies.yaml",
        },
    }


def test_validate_infra_config_accepts_valid_model() -> None:
    """Accepts valid InfraConfig as semantic validation output."""
    infra = InfraConfig.model_validate(_config())

    validated = validate_infra_config(infra)

    assert validated is infra


def test_validate_infra_config_rejects_unknown_input_token_in_validator() -> None:
    """Rejects unsupported input.format at semantic validator stage."""
    config = _config()
    config["input"]["format"] = "custom-source"

    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="input.format token 'custom-source' is missing in connectors registry",
    ):
        validate_infra_config(infra)


def test_validate_infra_config_accepts_tokens_declared_in_registry_keys() -> None:
    """Accepts input tokens that exist as keys in connectors registry file."""
    config = _config()
    config["input"]["format"] = "csv"
    config["input"]["config"] = {}

    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra)

    assert validated is infra


def test_validate_infra_config_rejects_unsupported_logging_level() -> None:
    """Rejects unsupported observability.logging.level using fixed validator set."""
    config = _config()
    config["observability"] = {
        "labels": {"env": "test"},
        "logging": {"level": "TRACE"},
    }
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="observability.logging.level is not supported",
    ):
        validate_infra_config(infra)


def test_validate_infra_config_accepts_valid_flood_control_subtree() -> None:
    """Accepts flood-control subtree when downstream contract validation passes."""
    config = _config()
    config["observability"] = {
        "labels": {"env": "test"},
        "logging": {
            "level": "INFO",
            "flood_control_config": {
                "enabled": True,
                "mode": "deduplicate",
                "context_keys": ["item_ref", "run_id"],
                "suppressed_levels": ["INFO", "WARNING"],
                "force_log_attr": "force_log",
                "key_fields": ["name", "levelno", "msg"],
                "window_seconds": 12.5,
                "max_events_per_window": 2,
                "emit_summary": True,
                "summary_level": "WARNING",
                "summary_interval_seconds": 60.0,
                "max_cache_size": 2048,
            },
        },
    }

    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra)

    assert validated is infra


def test_validate_infra_config_wraps_flood_control_validation_error() -> None:
    """Prefixes downstream flood-control validation errors with canonical config path."""
    config = _config()
    config["observability"] = {
        "labels": {"env": "test"},
        "logging": {
            "flood_control_config": {
                "mode": "invalid-mode",
            },
        },
    }

    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match=(
            "observability\\.logging\\.flood_control_config: "
            "Invalid flood control mode: invalid-mode"
        ),
    ):
        validate_infra_config(infra)


def test_validate_infra_config_checks_producer_files_with_infra_path(
    tmp_path: Path,
) -> None:
    """Validates producer schema/policy file existence when infra path is provided."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    config = _config()
    config["producer"]["schema_file"] = "./schema.yaml"
    config["producer"]["policy_file"] = "./policy.yaml"
    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))

    assert validated is infra


def test_validate_infra_config_rejects_missing_producer_files_with_infra_path(
    tmp_path: Path,
) -> None:
    """Fails semantic validation when producer file refs do not exist on disk."""
    config = _config()
    config["producer"]["schema_file"] = "./missing-schema.yaml"
    config["producer"]["policy_file"] = "./missing-policy.yaml"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.schema_file does not exist",
    ):
        validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))


def test_validate_infra_config_rejects_missing_policy_file_with_infra_path(
    tmp_path: Path,
) -> None:
    """Fails semantic validation when policy file ref does not exist on disk."""
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )

    config = _config()
    config["producer"]["schema_file"] = "./schema.yaml"
    config["producer"]["policy_file"] = "./missing-policy.yaml"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.policy_file does not exist",
    ):
        validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))


def test_validate_infra_config_rejects_schema_path_that_is_not_a_file(
    tmp_path: Path,
) -> None:
    """Rejects schema path that exists but is not a file."""
    schema_dir = tmp_path / "schema.yaml"
    schema_dir.mkdir()
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    config = _config()
    config["producer"]["schema_file"] = "./schema.yaml"
    config["producer"]["policy_file"] = "./policy.yaml"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.schema_file is not a file",
    ):
        validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))


def test_validate_infra_config_rejects_policy_path_that_is_not_a_file(
    tmp_path: Path,
) -> None:
    """Rejects policy path that exists but is not a file."""
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_dir = tmp_path / "policy.yaml"
    policy_dir.mkdir()

    config = _config()
    config["producer"]["schema_file"] = "./schema.yaml"
    config["producer"]["policy_file"] = "./policy.yaml"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.policy_file is not a file",
    ):
        validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))


def test_load_registry_rejects_missing_file(tmp_path: Path) -> None:
    """Reports registry read errors as InfraConfigValidationError."""
    from pfp_runtime.config import infra_validator

    with pytest.raises(InfraConfigValidationError, match="cannot read registry file"):
        infra_validator._load_registry(tmp_path / "missing.json")


def test_load_registry_rejects_invalid_json(tmp_path: Path) -> None:
    """Reports registry JSON decode errors as InfraConfigValidationError."""
    from pfp_runtime.config import infra_validator

    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(InfraConfigValidationError, match="invalid registry JSON"):
        infra_validator._load_registry(path)


def test_load_registry_rejects_non_object_root(tmp_path: Path) -> None:
    """Rejects registry JSON roots that are not objects."""
    from pfp_runtime.config import infra_validator

    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        InfraConfigValidationError, match="registry root must be a JSON object"
    ):
        infra_validator._load_registry(path)


def test_validate_infra_config_rejects_non_yaml_producer_paths() -> None:
    """Rejects producer.schema_file/policy_file that do not point to YAML files."""
    config = _config()
    config["producer"]["schema_file"] = "./schema.txt"
    config["producer"]["policy_file"] = "./policy.yaml"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.schema_file must point to a YAML file",
    ):
        validate_infra_config(infra)

    config = _config()
    config["producer"]["schema_file"] = "./schema.yaml"
    config["producer"]["policy_file"] = "./policy.txt"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="producer.policy_file must point to a YAML file",
    ):
        validate_infra_config(infra)


def test_validate_infra_config_accepts_absolute_producer_paths(
    tmp_path: Path,
) -> None:
    """Accepts absolute producer schema/policy file paths when they exist."""
    schema_file = tmp_path / "schema.yaml"
    policy_file = tmp_path / "policy.yaml"
    schema_file.write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n', encoding="utf-8"
    )
    policy_file.write_text('version: "1.0"\n', encoding="utf-8")

    config = _config()
    config["producer"]["schema_file"] = str(schema_file)
    config["producer"]["policy_file"] = str(policy_file)
    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra, infra_path=str(tmp_path / "infra.yaml"))

    assert validated is infra


def test_validate_infra_config_rejects_non_yaml_archive_config() -> None:
    """Rejects output.archive_config that does not end with .yaml or .yml."""
    config = _config()
    config["output"]["archive_config"] = "./archive/local.json"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="output.archive_config must point to a YAML file",
    ):
        validate_infra_config(infra)


def test_validate_infra_config_rejects_non_yaml_client_config() -> None:
    """Rejects output.client_config that does not end with .yaml or .yml."""
    config = _config()
    config["output"]["client_config"] = "./clients/noop.json"
    infra = InfraConfig.model_validate(config)

    with pytest.raises(
        InfraConfigValidationError,
        match="output.client_config must point to a YAML file",
    ):
        validate_infra_config(infra)


def test_validate_infra_config_accepts_yml_suffix_for_archive_config() -> None:
    """Accepts output.archive_config ending with .yml as a valid YAML path."""
    config = _config()
    config["output"]["archive_config"] = "./archive/local.yml"
    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra)

    assert validated is infra


def test_validate_infra_config_accepts_yml_suffix_for_client_config() -> None:
    """Accepts output.client_config ending with .yml as a valid YAML path."""
    config = _config()
    config["output"]["client_config"] = "./clients/noop.yml"
    infra = InfraConfig.model_validate(config)

    validated = validate_infra_config(infra)

    assert validated is infra
