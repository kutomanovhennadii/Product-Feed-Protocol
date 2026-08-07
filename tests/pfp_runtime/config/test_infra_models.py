"""Unit tests for canonical infra models."""

from typing import Any, Dict

import pytest

from pfp_runtime.config import infra_models
from pfp_runtime.config.infra_models import InfraConfig


def _minimal_config() -> Dict[str, Any]:
    """Build minimal canonical config for InfraConfig (publisher v2 schema)."""
    return {
        "input": {"format": "csv", "config": {"connector_mapping": "./mapping.yaml"}},
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


def test_infra_config_accepts_canonical_sections() -> None:
    """Validates canonical input/output/producer sections for InfraConfig."""
    config = InfraConfig.model_validate(_minimal_config())

    assert config.input.format == "csv"
    assert config.output.archive_type == "local"
    assert config.output.client_type == "noop"
    assert config.producer.schema_file is not None


def test_infra_config_rejects_legacy_trigger_field() -> None:
    """Rejects legacy trigger field in canonical InfraConfig root contract."""
    config = _minimal_config()
    config["trigger"] = {"mode": "cli"}

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_infra_config_accepts_open_input_format_token() -> None:
    """Accepts non-empty open discriminator token for input.format."""
    config = _minimal_config()
    config["input"]["format"] = "custom-source"

    validated = InfraConfig.model_validate(config)

    assert validated.input.format == "custom-source"


def test_logging_config_accepts_open_level_token() -> None:
    """Accepts non-empty open discriminator token for logging.level."""
    config = _minimal_config()
    config["observability"] = {
        "labels": {"env": "test"},
        "logging": {"level": "verbose"},
    }

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.logging is not None
    assert validated.observability.logging.level == "VERBOSE"


def test_producer_policy_file_has_no_hidden_default() -> None:
    """Requires explicit producer.policy_file and has no hidden default path."""
    config = _minimal_config()
    config["producer"].pop("policy_file")

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_producer_schema_file_is_required() -> None:
    """Requires explicit producer.schema_file in canonical producer section."""
    config = _minimal_config()
    config["producer"].pop("schema_file")

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_producer_tax_mapping_file_defaults_to_none() -> None:
    """Defaults producer.tax_mapping_file to None when the field is omitted."""
    validated = InfraConfig.model_validate(_minimal_config())

    assert validated.producer.tax_mapping_file is None


def test_producer_tax_mapping_file_accepts_trimmed_path() -> None:
    """Accepts producer.tax_mapping_file and normalizes surrounding spaces."""
    config = _minimal_config()
    config["producer"][
        "tax_mapping_file"
    ] = "  ./config/tax_mappings/shopify_to_stripe_ptc.json  "

    validated = InfraConfig.model_validate(config)

    assert (
        validated.producer.tax_mapping_file
        == "./config/tax_mappings/shopify_to_stripe_ptc.json"
    )


def test_producer_tax_mapping_file_rejects_blank_value() -> None:
    """Rejects blank producer.tax_mapping_file when the field is explicitly set."""
    config = _minimal_config()
    config["producer"]["tax_mapping_file"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_root_producer_section_is_required() -> None:
    """Rejects configs without required root producer section."""
    config = _minimal_config()
    config.pop("producer")

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_open_discriminator_tokens_reject_blank_values() -> None:
    """Rejects blank discriminator values for input.format and logging.level."""
    config = _minimal_config()
    config["input"]["format"] = "   "
    with pytest.raises(ValueError, match="format must be non-empty"):
        InfraConfig.model_validate(config)

    config = _minimal_config()
    config["observability"] = {
        "labels": {},
        "logging": {"level": "   "},
    }
    with pytest.raises(ValueError, match="level must be non-empty"):
        InfraConfig.model_validate(config)


def test_logging_level_normalizes_to_uppercase_after_trim() -> None:
    """Normalizes logging level to uppercase after trim in canonical model."""
    config = _minimal_config()
    config["observability"] = {
        "labels": {},
        "logging": {"level": "  INFO  "},
    }

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.logging is not None
    assert validated.observability.logging.level == "INFO"


def test_observability_logging_defaults_when_section_present() -> None:
    """Materializes default observability.logging when observability exists."""
    config = _minimal_config()
    config["observability"] = {"labels": {"pipeline": "test"}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.logging is not None
    assert validated.observability.logging.level == "INFO"
    assert validated.observability.logging.flood_control_config.mode == (
        "context_info_suppression"
    )
    assert (
        validated.observability.logging.flood_control_config.model_dump()[
            "max_cache_size"
        ]
        == 10000
    )


def test_observability_logging_accepts_explicit_flood_control_config() -> None:
    """Materializes explicit flood-control subtree in canonical logging config."""
    config = _minimal_config()
    config["observability"] = {
        "labels": {"pipeline": "test"},
        "logging": {
            "level": "info",
            "flood_control_config": {
                "enabled": True,
                "mode": "deduplicate",
                "context_keys": ["item_ref", "run_id"],
                "suppressed_levels": ["INFO", "WARNING"],
                "force_log_attr": "force_log",
                "key_fields": ["name", "levelno", "msg"],
                "window_seconds": 12.5,
                "max_events_per_window": 3,
                "emit_summary": True,
                "summary_level": "WARNING",
                "summary_interval_seconds": 45.0,
                "max_cache_size": 512,
            },
        },
    }

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    flood_control = validated.observability.logging.flood_control_config
    assert flood_control.mode == "deduplicate"
    assert flood_control.context_keys == ["item_ref", "run_id"]
    assert flood_control.suppressed_levels == ["INFO", "WARNING"]
    assert flood_control.summary_level == "WARNING"
    assert flood_control.model_dump()["max_cache_size"] == 512


def test_observability_logging_rejects_extra_flood_control_key() -> None:
    """Rejects unknown keys inside flood-control canonical subtree."""
    config = _minimal_config()
    config["observability"] = {
        "labels": {"pipeline": "test"},
        "logging": {
            "flood_control_config": {
                "unknown_key": True,
            },
        },
    }

    with pytest.raises(ValueError, match="unknown_key"):
        InfraConfig.model_validate(config)


def test_observability_log_format_defaults_to_text() -> None:
    """Defaults observability.log_format to TEXT when field is omitted."""
    config = _minimal_config()
    config["observability"] = {"labels": {}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.log_format == "TEXT"


def test_observability_log_format_normalizes_to_uppercase() -> None:
    """Normalizes observability.log_format token to uppercase."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "log_format": "  json  "}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.log_format == "JSON"


def test_observability_log_format_rejects_invalid_token() -> None:
    """Rejects unsupported observability.log_format values."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "log_format": "xml"}

    with pytest.raises(
        ValueError,
        match="observability.log_format must be 'TEXT' or 'JSON'",
    ):
        InfraConfig.model_validate(config)


def test_observability_defaults_materialize_directly_in_model() -> None:
    """Store observability defaults directly in canonical model representation."""
    config = _minimal_config()
    config["observability"] = {"labels": {"pipeline": "test"}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry.provider == "none"


def test_observability_explicit_sections_are_stored_directly_in_model() -> None:
    """Store explicit telemetry values directly in canonical model fields."""
    config = _minimal_config()
    config["observability"] = {
        "labels": {"pipeline": "test"},
        "telemetry": {"provider": "prometheus"},
    }

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry.provider == "prometheus"


def test_secret_ref_is_not_exported_in_models_public_surface() -> None:
    """Ensures SecretRef is not leaked through infra_models __all__."""
    assert "SecretRef" not in infra_models.__all__


def test_output_destination_config_is_not_exported() -> None:
    """Ensures OutputDestinationConfig is removed from infra_models public surface."""
    assert "OutputDestinationConfig" not in infra_models.__all__


def test_input_config_connector_mapping_rejects_blank_string() -> None:
    """Rejects blank input.config.connector_mapping when field is present."""
    config = _minimal_config()
    config["input"]["config"]["connector_mapping"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_output_archive_type_normalizes_to_lowercase() -> None:
    """Normalizes archive_type to lowercase after strip."""
    config = _minimal_config()
    config["output"]["archive_type"] = "  LOCAL  "

    validated = InfraConfig.model_validate(config)

    assert validated.output.archive_type == "local"


def test_output_client_type_normalizes_to_lowercase() -> None:
    """Normalizes client_type to lowercase after strip."""
    config = _minimal_config()
    config["output"]["client_type"] = "  NOOP  "

    validated = InfraConfig.model_validate(config)

    assert validated.output.client_type == "noop"


def test_output_archive_type_rejects_blank() -> None:
    """Rejects blank archive_type token in canonical output model."""
    config = _minimal_config()
    config["output"]["archive_type"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_output_client_type_rejects_blank() -> None:
    """Rejects blank client_type token in canonical output model."""
    config = _minimal_config()
    config["output"]["client_type"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_output_archive_config_rejects_blank() -> None:
    """Rejects blank archive_config path in canonical output model."""
    config = _minimal_config()
    config["output"]["archive_config"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_output_client_config_rejects_blank() -> None:
    """Rejects blank client_config path in canonical output model."""
    config = _minimal_config()
    config["output"]["client_config"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_output_all_four_fields_required() -> None:
    """Rejects output section missing any of the four required fields."""
    for field in ("archive_type", "archive_config", "client_type", "client_config"):
        config = _minimal_config()
        config["output"].pop(field)

        with pytest.raises(ValueError):
            InfraConfig.model_validate(config)


def test_output_rejects_extra_fields() -> None:
    """Rejects output section containing extra unknown fields."""
    config = _minimal_config()
    config["output"]["unknown_field"] = "value"

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_producer_file_paths_reject_blank_strings() -> None:
    """Rejects blank producer.schema_file and producer.policy_file paths."""
    config = _minimal_config()
    config["producer"]["schema_file"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)


def test_telemetry_config_accepts_prometheus_provider() -> None:
    """Accepts 'prometheus' as telemetry provider."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "telemetry": {"provider": "prometheus"}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry is not None
    assert validated.observability.telemetry.provider == "prometheus"


def test_telemetry_config_accepts_none_provider() -> None:
    """Accepts 'none' as telemetry provider (default NoOp)."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "telemetry": {"provider": "none"}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry is not None
    assert validated.observability.telemetry.provider == "none"


def test_telemetry_config_normalizes_provider_to_lowercase() -> None:
    """Normalizes telemetry provider to lowercase."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "telemetry": {"provider": "PROMETHEUS"}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry is not None
    assert validated.observability.telemetry.provider == "prometheus"


def test_telemetry_config_rejects_invalid_provider() -> None:
    """Rejects unknown telemetry provider token."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "telemetry": {"provider": "datadog"}}

    with pytest.raises(
        ValueError, match="telemetry.provider must be 'none' or 'prometheus'"
    ):
        InfraConfig.model_validate(config)


def test_telemetry_config_defaults_to_none_when_section_absent() -> None:
    """observability.telemetry defaults to provider='none' when omitted."""
    config = _minimal_config()
    config["observability"] = {"labels": {}}

    validated = InfraConfig.model_validate(config)

    assert validated.observability is not None
    assert validated.observability.telemetry is not None
    assert validated.observability.telemetry.provider == "none"


def test_observability_rejects_extra_field() -> None:
    """Rejects unknown fields in observability section."""
    config = _minimal_config()
    config["observability"] = {"labels": {}, "unknown_key": "value"}

    with pytest.raises(ValueError):
        InfraConfig.model_validate(config)


def test_optional_string_fields_accept_none_values() -> None:
    """Accepts explicit null values for optional string fields in input.config."""
    config = _minimal_config()
    config["input"]["config"] = {"connector_mapping": None}

    validated = InfraConfig.model_validate(config)

    assert validated.input.config.connector_mapping is None

    config = _minimal_config()
    config["producer"]["policy_file"] = "   "

    with pytest.raises(ValueError, match="value must be non-empty"):
        InfraConfig.model_validate(config)
