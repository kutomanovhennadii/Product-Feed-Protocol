"""Tests for policy bundle builder wiring."""

from unittest.mock import Mock

import pytest

from pfp_core.policies.domain.strictness import StrictnessMode, StrictnessPolicy
from pfp_core.policies.policy_bundle_builder import (
    _build_optional_policy,
    build_policy_bundle,
    default_policy_registry,
)
from pfp_core.policies.policy_config import PolicyConfig
from pfp_core.policies.policy_registry import PolicyRegistry


def _policy_config(strategy: str = "fail_on_error") -> PolicyConfig:
    return PolicyConfig.from_dict(
        {
            "version": "1.0",
            "core": {"strictness": {"strategy": strategy}},
        }
    )


def test_default_registry_builds_strictness_policy() -> None:
    """default_policy_registry builds strictness policy from config."""
    registry = default_policy_registry(log_pipeline=Mock())
    config = _policy_config("fail_on_error")

    bundle = build_policy_bundle(config, registry, log_pipeline=Mock())

    assert isinstance(bundle.strictness, StrictnessPolicy)
    assert bundle.strictness.strategy == StrictnessMode.FAIL_ON_ERROR.value


def test_build_policy_bundle_requires_strictness_factory() -> None:
    """Builder fails if registry does not provide strictness factory."""
    config = _policy_config("fail_on_error")
    registry = PolicyRegistry(log_pipeline=Mock())
    with pytest.raises(ValueError, match="Unknown policy"):
        build_policy_bundle(config, registry, log_pipeline=Mock())


@pytest.mark.parametrize(
    "policy_name,bad_config,error_text",
    [
        ("strictness", object(), "Strictness policy config must be StrictnessConfig"),
        (
            "eligibility",
            object(),
            "Eligibility policy config must be EligibilityConfig",
        ),
        (
            "fault_isolation",
            object(),
            "Fault isolation policy config must be FaultIsolationConfig",
        ),
    ],
)
def test_default_registry_builders_validate_config_type(
    policy_name: str,
    bad_config: object,
    error_text: str,
) -> None:
    """Built-in factories reject incompatible config objects with TypeError."""
    registry = default_policy_registry(log_pipeline=Mock())

    with pytest.raises(TypeError, match=error_text):
        registry.build(policy_name, bad_config)


def test_build_optional_policy_returns_none_for_none_config() -> None:
    """_build_optional_policy returns None when config is absent."""
    registry = default_policy_registry(log_pipeline=Mock())

    assert _build_optional_policy(registry, "eligibility", None) is None


def test_build_optional_policy_returns_none_for_unknown_policy() -> None:
    """_build_optional_policy swallows unknown policy errors as optional absent."""
    registry = PolicyRegistry(log_pipeline=Mock())

    assert _build_optional_policy(registry, "missing_policy", object()) is None


def test_build_optional_policy_reraises_non_unknown_errors() -> None:
    """_build_optional_policy re-raises registry errors unrelated to unknown policies."""
    registry = PolicyRegistry(log_pipeline=Mock())

    def _boom(_: object) -> object:
        raise ValueError("registry failure")

    registry.register("failing_policy", _boom)

    with pytest.raises(ValueError, match="registry failure"):
        _build_optional_policy(registry, "failing_policy", object())
