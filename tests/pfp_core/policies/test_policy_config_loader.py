"""Tests for YAML-based policy config loading."""

from unittest.mock import Mock

import pytest

from pfp_core.policies.domain.strictness import StrictnessMode
from pfp_core.policies.policy_config_loader import (
    load_policy_bundle_from_yaml_text,
    load_policy_config_from_yaml_text,
)


def _policy_yaml(strategy: str = "fail_on_error", extra: str = "") -> str:
    return (
        'version: "1.0"\n'
        "core:\n"
        "  strictness:\n"
        '    strategy: "' + strategy + '"\n' + extra
    )


def _policy_yaml_with_fault_isolation(
    strategy: str = "fail_on_error",
) -> str:
    return (
        'version: "1.0"\n'
        "core:\n"
        "  strictness:\n"
        '    strategy: "' + strategy + '"\n'
        "  fault_isolation:\n"
        '    strategy: "SKIP_ITEM"\n'
    )


def test_load_policy_bundle_valid() -> None:
    """load_policy_bundle_from_yaml_text builds bundle from valid minimal YAML."""
    bundle = load_policy_bundle_from_yaml_text(
        _policy_yaml_with_fault_isolation("fail_on_error"),
        log_pipeline=Mock(),
    )
    assert bundle.strictness.strategy == StrictnessMode.FAIL_ON_ERROR.value


def test_load_policy_bundle_rejects_unknown_key() -> None:
    """Loader rejects unknown strictness keys from YAML."""
    with pytest.raises(ValueError, match="Unknown keys"):
        load_policy_bundle_from_yaml_text(
            _policy_yaml("fail_on_error", '    extra: "nope"\n'),
            log_pipeline=Mock(),
        )


def test_load_policy_bundle_rejects_non_mapping_root() -> None:
    """Loader rejects non-mapping YAML root values."""
    with pytest.raises(ValueError, match="Policy config root must be a mapping"):
        load_policy_bundle_from_yaml_text("- 1\n- 2\n", log_pipeline=Mock())


def test_load_policy_config_rejects_empty_yaml() -> None:
    """Loader rejects empty YAML payloads before schema validation."""

    with pytest.raises(ValueError, match="Policy config is empty"):
        load_policy_config_from_yaml_text("")


def test_load_policy_config_from_yaml_text_happy_path() -> None:
    """Loader accepts strictness profile in YAML text."""
    yaml_text = _policy_yaml_with_fault_isolation("drop_invalid")
    config = load_policy_config_from_yaml_text(yaml_text)
    assert config.version == "1.0"
    assert config.core.strictness.strategy == "drop_invalid"


def test_load_policy_bundle_includes_fault_isolation() -> None:
    """Bundle builds from policy YAML and exposes fault_isolation."""
    bundle = load_policy_bundle_from_yaml_text(
        _policy_yaml_with_fault_isolation("fail_on_error"),
        log_pipeline=Mock(),
    )
    assert bundle.strictness.strategy == StrictnessMode.FAIL_ON_ERROR.value
    assert bundle.fault_isolation is not None


def test_load_policy_bundle_rejects_logging_in_core() -> None:
    """Loader rejects logging inside core — it belongs in infra YAML."""
    yaml_text = (
        'version: "1.0"\n'
        "core:\n"
        "  strictness:\n"
        '    strategy: "fail_on_error"\n'
        "  logging:\n"
        '    level: "INFO"\n'
    )
    with pytest.raises(ValueError, match="Unknown keys at 'core': logging"):
        load_policy_config_from_yaml_text(yaml_text)


def test_load_policy_bundle_rejects_telemetry_in_core() -> None:
    """Loader rejects telemetry inside core — it belongs in infra YAML."""
    yaml_text = (
        'version: "1.0"\n'
        "core:\n"
        "  strictness:\n"
        '    strategy: "fail_on_error"\n'
        "  telemetry:\n"
        '    provider: "none"\n'
    )
    with pytest.raises(ValueError, match="Unknown keys at 'core': telemetry"):
        load_policy_config_from_yaml_text(yaml_text)
