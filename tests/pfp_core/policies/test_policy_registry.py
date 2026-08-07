"""Tests for policy registry behavior."""

from unittest.mock import Mock

import pytest

from pfp_core.policies.domain.strictness import StrictnessPolicy
from pfp_core.policies.policy_registry import PolicyRegistry


def test_register_rejects_duplicates() -> None:
    """PolicyRegistry.register raises when a policy name is registered twice."""
    registry = PolicyRegistry(log_pipeline=Mock())
    registry.register("strictness", lambda _config: StrictnessPolicy("fail_on_error"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            "strictness", lambda _config: StrictnessPolicy("fail_on_error")
        )


def test_build_raises_on_unknown_policy() -> None:
    """PolicyRegistry.build raises for unknown policy names."""
    registry = PolicyRegistry(log_pipeline=Mock())

    with pytest.raises(ValueError, match="Unknown policy"):
        registry.build("missing", object())
