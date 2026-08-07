"""Tests for policy configuration models."""

import pytest

from pfp_core.policies.domain.eligibility import EligibilityConfig
from pfp_core.policies.domain.strictness import StrictnessConfig
from pfp_core.policies.infra.fault_isolation_policy import FaultIsolationConfig
from pfp_core.policies.policy_config import (
    CorePolicyConfig,
    InfrastructureConfig,
    PolicyConfig,
)


def test_policy_config_accepts_numeric_version_equivalent() -> None:
    """PolicyConfig accepts numeric version values equivalent to supported string."""
    config = PolicyConfig.from_dict(
        {
            "version": 1.0,
            "core": {"strictness": {"strategy": "fail_on_error"}},
        }
    )

    assert isinstance(config, PolicyConfig)
    assert isinstance(config.core.strictness, StrictnessConfig)


def test_policy_config_rejects_non_mapping_root() -> None:
    """PolicyConfig rejects configs where the root is not a mapping."""
    with pytest.raises(ValueError, match="Expected mapping at 'root'"):
        PolicyConfig.from_dict([1, 2, 3])  # type: ignore[arg-type]


def test_policy_config_rejects_unsupported_version() -> None:
    """PolicyConfig rejects unsupported version strings."""
    with pytest.raises(ValueError, match="Unsupported policy config version '2.0'"):
        PolicyConfig.from_dict(
            {
                "version": "2.0",
                "core": {"strictness": {"strategy": "fail_on_error"}},
            }
        )


def test_core_policy_config_parses_all_sections() -> None:
    """CorePolicyConfig parses all domain policy sections when provided."""
    core = CorePolicyConfig.from_dict(
        {
            "strictness": {"strategy": "fail_on_error"},
            "eligibility": {},
            "fault_isolation": {"strategy": "SKIP_ITEM"},
        }
    )

    assert isinstance(core.strictness, StrictnessConfig)
    assert isinstance(core.eligibility, EligibilityConfig)
    assert isinstance(core.fault_isolation, FaultIsolationConfig)


def test_core_policy_config_rejects_logging_section() -> None:
    """CorePolicyConfig rejects logging — it belongs in infra YAML, not policy_file."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'core': logging"):
        CorePolicyConfig.from_dict(
            {
                "strictness": {"strategy": "fail_on_error"},
                "logging": {"level": "INFO"},
            }
        )


def test_core_policy_config_rejects_telemetry_section() -> None:
    """CorePolicyConfig rejects telemetry — it belongs in infra YAML, not policy_file."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'core': telemetry"):
        CorePolicyConfig.from_dict(
            {
                "strictness": {"strategy": "fail_on_error"},
                "telemetry": {"provider": "none"},
            }
        )


def test_core_policy_config_rejects_unknown_section_key() -> None:
    """CorePolicyConfig rejects unknown keys in core section."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'core': unknown_section"):
        CorePolicyConfig.from_dict(
            {
                "strictness": {"strategy": "fail_on_error"},
                "unknown_section": {},
            }
        )


def test_policy_config_rejects_logging_inside_core() -> None:
    """PolicyConfig rejects logging inside core — infra config does not belong in policy_file."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'core': logging"):
        PolicyConfig.from_dict(
            {
                "version": "1.0",
                "core": {
                    "strictness": {"strategy": "fail_on_error"},
                    "logging": {"level": "INFO", "format": "json"},
                },
            }
        )


def test_policy_config_rejects_telemetry_inside_core() -> None:
    """PolicyConfig rejects telemetry inside core — infra config does not belong in policy_file."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'core': telemetry"):
        PolicyConfig.from_dict(
            {
                "version": "1.0",
                "core": {
                    "strictness": {"strategy": "fail_on_error"},
                    "telemetry": {"provider": "none"},
                },
            }
        )


def test_policy_config_rejects_root_level_infrastructure_as_unknown_key() -> None:
    """Root-level infrastructure is not a valid external contract key."""
    with pytest.raises(ValueError, match="Unknown keys at 'root': infrastructure"):
        PolicyConfig.from_dict(
            {
                "version": "1.0",
                "core": {
                    "strictness": {"strategy": "fail_on_error"},
                    "fault_isolation": {"strategy": "SKIP_ITEM"},
                },
                "infrastructure": {
                    "fault_isolation": {"strategy": "SKIP_ITEM"},
                },
            }
        )


def test_infrastructure_policy_config_parses_fault_isolation() -> None:
    """InfrastructureConfig parses fault_isolation section."""
    infrastructure = InfrastructureConfig.from_dict(
        {
            "fault_isolation": {"strategy": "SKIP_ITEM"},
        }
    )
    assert isinstance(infrastructure.fault_isolation, FaultIsolationConfig)


def test_infrastructure_policy_config_rejects_logging() -> None:
    """InfrastructureConfig rejects logging — logging moved to infra YAML."""
    with pytest.raises(ValueError, match=r"Unknown keys at 'infrastructure': logging"):
        InfrastructureConfig.from_dict(
            {
                "logging": {"level": "INFO"},
                "fault_isolation": {"strategy": "SKIP_ITEM"},
            }
        )


def test_infrastructure_policy_config_rejects_telemetry() -> None:
    """InfrastructureConfig rejects telemetry — telemetry moved to infra YAML."""
    with pytest.raises(
        ValueError, match=r"Unknown keys at 'infrastructure': telemetry"
    ):
        InfrastructureConfig.from_dict(
            {
                "telemetry": {"provider": "none"},
                "fault_isolation": {"strategy": "SKIP_ITEM"},
            }
        )
