"""Unit tests for canonical infra loader."""

from pathlib import Path

import pytest

from pfp_runtime.config.infra_loader import (
    InfraConfigParseError,
    InfraConfigValidationError,
    load_infra_config,
)


def test_parse_infra_payload_rejects_invalid_yaml_syntax() -> None:
    """Rejects invalid YAML config with a safe parse error."""
    from pfp_runtime.config import infra_loader

    with pytest.raises(InfraConfigParseError, match="invalid YAML config"):
        infra_loader._parse_infra_config("a: [1, 2")


def test_parse_infra_payload_rejects_non_mapping_root() -> None:
    """Rejects YAML roots that are not a mapping."""
    from pfp_runtime.config import infra_loader

    with pytest.raises(
        InfraConfigValidationError,
        match="infra config root must be a mapping",
    ):
        infra_loader._parse_infra_config("- a\n- b\n")


def test_parse_infra_payload_reports_missing_yaml_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reports missing PyYAML dependency as InfraConfigParseError."""
    import builtins
    from typing import Any

    from pfp_runtime.config import infra_loader

    original_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "yaml":
            raise ImportError("No module named 'yaml'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(InfraConfigParseError, match="YAML support is unavailable"):
        infra_loader._parse_infra_config("a: 1")


def test_format_validation_error_handles_non_tuple_loc() -> None:
    """Formats validation errors when loc is not a tuple."""
    from typing import Any, Dict, List, cast

    from pfp_runtime.config import infra_loader

    class _StubValidationError:
        def errors(self) -> List[Dict[str, object]]:
            return [
                {"loc": ["input", "format"], "msg": "bad"},
            ]

    message = infra_loader._format_validation_error(cast(Any, _StubValidationError()))

    assert "input" in message
    assert "bad" in message


def test_format_validation_error_handles_empty_loc_and_empty_errors() -> None:
    """Formats validation errors when loc is empty or when errors are empty."""
    from typing import Any, Dict, List, cast

    from pfp_runtime.config import infra_loader

    class _EmptyLocValidationError:
        def errors(self) -> List[Dict[str, object]]:
            return [
                {"loc": (), "msg": "bad"},
                {"loc": ()},
            ]

    message = infra_loader._format_validation_error(
        cast(Any, _EmptyLocValidationError())
    )
    assert message.count("bad") == 1
    assert "validation error" in message

    class _NoErrorsValidationError:
        def errors(self) -> List[Dict[str, object]]:
            return []

    assert (
        infra_loader._format_validation_error(cast(Any, _NoErrorsValidationError()))
        == "infra config validation failed"
    )


def test_loader_reads_valid_canonical_yaml(tmp_path: Path) -> None:
    """Loads valid canonical infra yaml into InfraConfig object."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
    format: csv
    config:
        connector_mapping: ./mapping.yaml
output:
  archive_type: local
  archive_config: ./archive/local.yaml
  client_type: noop
  client_config: ./clients/noop.yaml
producer:
  schema_file: ./schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml
  policy_file: ./config/policies.yaml
""",
        encoding="utf-8",
    )

    config = load_infra_config(str(path))

    assert config.input.config.connector_mapping == "./mapping.yaml"
    assert config.output.archive_type == "local"
    assert config.output.client_type == "noop"


def test_loader_rejects_legacy_trigger_section(tmp_path: Path) -> None:
    """Rejects legacy trigger section before model materialization."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
    format: csv
    config:
        connector_mapping: ./mapping.yaml
output:
  archive_type: local
  archive_config: ./archive/local.yaml
  client_type: noop
  client_config: ./clients/noop.yaml
trigger:
  mode: cli
producer:
  schema_file: ./schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml
  policy_file: ./config/policies.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(
        InfraConfigValidationError,
        match="trigger",
    ):
        load_infra_config(str(path))


def test_loader_rejects_non_yaml_extension(tmp_path: Path) -> None:
    """Rejects unsupported config file extension at loader boundary."""
    path = tmp_path / "infra.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(InfraConfigParseError):
        load_infra_config(str(path))


def test_loader_rejects_missing_root_producer_section(tmp_path: Path) -> None:
    """Rejects config without required root producer section at load time."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
  format: csv
  config:
    connector_mapping: ./mapping.yaml
output:
  archive_type: local
  archive_config: ./archive/local.yaml
  client_type: noop
  client_config: ./clients/noop.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(InfraConfigValidationError, match="producer"):
        load_infra_config(str(path))


def test_loader_rejects_missing_producer_policy_file(tmp_path: Path) -> None:
    """Rejects config with missing producer.policy_file at load time."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
    format: csv
    config:
        connector_mapping: ./mapping.yaml
output:
    archive_type: local
    archive_config: ./archive/local.yaml
    client_type: noop
    client_config: ./clients/noop.yaml
producer:
    schema_file: ./schemas/stripe.product_feed/stripe.product_feed-1.0.0.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(InfraConfigValidationError, match="policy_file"):
        load_infra_config(str(path))


def test_loader_does_not_run_semantic_validation_for_registry_tokens(
    tmp_path: Path,
) -> None:
    """Loads model-valid config even when semantic token checks would fail."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
  format: custom-source
  config:
    connector_mapping: ./mapping.yaml
output:
  archive_type: custom-archive
  archive_config: ./archive/custom.yaml
  client_type: custom-client
  client_config: ./clients/custom.yaml
producer:
  schema_file: ./schemas/custom-feed.yaml
  policy_file: ./config/custom-policy.yaml
""",
        encoding="utf-8",
    )

    config = load_infra_config(str(path))

    assert config.input.format == "custom-source"
    assert config.output.archive_type == "custom-archive"
    assert config.output.client_type == "custom-client"


def test_loader_materializes_observability_log_format_from_yaml(
    tmp_path: Path,
) -> None:
    """Materializes observability.log_format through parse+model validation."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
  format: csv
  config:
    connector_mapping: ./mapping.yaml
output:
  archive_type: local
  archive_config: ./archive/local.yaml
  client_type: noop
  client_config: ./clients/noop.yaml
producer:
  schema_file: ./schemas/product.yaml
  policy_file: ./config/policies.yaml
observability:
  labels:
    env: test
  log_format: json
""",
        encoding="utf-8",
    )

    config = load_infra_config(str(path))

    assert config.observability is not None
    assert config.observability.log_format == "JSON"


def test_loader_materializes_flood_control_config_from_yaml(tmp_path: Path) -> None:
    """Materializes nested flood-control logging config through loader route."""
    path = tmp_path / "infra.yaml"
    path.write_text(
        """
input:
    format: csv
    config:
        connector_mapping: ./mapping.yaml
output:
    archive_type: local
    archive_config: ./archive/local.yaml
    client_type: noop
    client_config: ./clients/noop.yaml
producer:
    schema_file: ./schemas/product.yaml
    policy_file: ./config/policies.yaml
observability:
    labels:
        env: test
    logging:
        level: INFO
        flood_control_config:
            enabled: true
            mode: deduplicate
            context_keys:
                - item_ref
                - run_id
            suppressed_levels:
                - INFO
                - WARNING
            force_log_attr: force_log
            key_fields:
                - name
                - levelno
                - msg
            window_seconds: 12.5
            max_events_per_window: 2
            emit_summary: true
            summary_level: WARNING
            summary_interval_seconds: 60.0
            max_cache_size: 2048
""",
        encoding="utf-8",
    )

    config = load_infra_config(str(path))

    assert config.observability is not None
    flood_control = config.observability.logging.flood_control_config
    assert flood_control.mode == "deduplicate"
    assert flood_control.context_keys == ["item_ref", "run_id"]
    assert flood_control.summary_level == "WARNING"
    assert flood_control.model_dump()["max_cache_size"] == 2048
