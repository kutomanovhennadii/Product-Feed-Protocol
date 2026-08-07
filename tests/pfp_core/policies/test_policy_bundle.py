"""Tests for policy bundle container."""

from dataclasses import fields

from pfp_core.policies.domain.strictness import StrictnessPolicy
from pfp_core.policies.policy_bundle import OptionalPolicy, PolicyBundle


def test_policy_bundle_holds_required_strictness_policy() -> None:
    """PolicyBundle stores strictness policy and optional slots default to None."""
    bundle = PolicyBundle(strictness=StrictnessPolicy("fail_on_error"))
    assert bundle.strictness.strategy == "fail_on_error"
    assert bundle.eligibility is None


def test_optional_policy_alias_accepts_none() -> None:
    """OptionalPolicy alias supports None values for optional bundle entries."""
    value: OptionalPolicy = None
    assert value is None


def test_policy_bundle_fields_match_current_contract() -> None:
    """PolicyBundle dataclass exposes only active policy slots."""
    names = [item.name for item in fields(PolicyBundle)]

    assert names == [
        "strictness",
        "eligibility",
        "logging",
        "telemetry",
        "fault_isolation",
    ]
