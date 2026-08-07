"""Built-in bundle wiring from policy config to policy instances."""

from typing import Any, Optional

from pfp_core.policies.domain.eligibility import EligibilityConfig
from pfp_core.policies.domain.strictness import StrictnessConfig, StrictnessPolicy
from pfp_core.policies.infra.fault_isolation_policy import FaultIsolationConfig
from pfp_core.policies.policy_bundle import OptionalPolicy, PolicyBundle
from pfp_core.policies.policy_config import PolicyConfig
from pfp_core.policies.policy_registry import PolicyRegistry
from pfp_utils.logging import LogPipeline


def _build_strictness_policy(config: StrictnessConfig) -> StrictnessPolicy:
    if not isinstance(config, StrictnessConfig):
        raise TypeError("Strictness policy config must be StrictnessConfig")
    return StrictnessPolicy(config.strategy)


def _build_eligibility_policy(config: EligibilityConfig) -> Any:
    if not isinstance(config, EligibilityConfig):
        raise TypeError("Eligibility policy config must be EligibilityConfig")

    from pfp_core.policies.domain.eligibility import EligibilityPolicy

    return EligibilityPolicy(config)


def _build_fault_isolation_policy(
    config: FaultIsolationConfig,
    *,
    log_pipeline: LogPipeline,
) -> Any:
    if not isinstance(config, FaultIsolationConfig):
        raise TypeError("Fault isolation policy config must be FaultIsolationConfig")

    from pfp_core.policies.infra.fault_isolation_policy import FaultIsolationPolicy

    return FaultIsolationPolicy(config, log_pipeline=log_pipeline)


def _build_optional_policy(
    registry: PolicyRegistry,
    name: str,
    config: Optional[Any],
) -> OptionalPolicy:
    if config is None:
        return None

    try:
        return registry.build(name, config)
    except ValueError as exc:
        if "Unknown policy" in str(exc):
            return None
        raise


def default_policy_registry(*, log_pipeline: LogPipeline) -> PolicyRegistry:
    """Return a registry pre-populated with built-in policies."""
    registry = PolicyRegistry(log_pipeline=log_pipeline)
    registry.register("strictness", _build_strictness_policy)
    registry.register("eligibility", _build_eligibility_policy)
    registry.register(
        "fault_isolation",
        lambda config: _build_fault_isolation_policy(
            config,
            log_pipeline=log_pipeline,
        ),
    )
    return registry


def build_policy_bundle(
    config: PolicyConfig,
    registry: Optional[PolicyRegistry] = None,
    *,
    log_pipeline: LogPipeline,
) -> PolicyBundle:
    """Build a PolicyBundle using the provided registry."""
    registry = registry or default_policy_registry(log_pipeline=log_pipeline)
    strictness = registry.build("strictness", config.core.strictness)
    eligibility = _build_optional_policy(
        registry, "eligibility", config.core.eligibility
    )
    fault_isolation = _build_optional_policy(
        registry,
        "fault_isolation",
        config.core.fault_isolation,
    )

    return PolicyBundle(
        strictness=strictness,
        eligibility=eligibility,
        fault_isolation=fault_isolation,
    )
