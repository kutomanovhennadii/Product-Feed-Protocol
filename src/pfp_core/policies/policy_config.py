"""Configuration schema for policy bundle building."""

from dataclasses import dataclass, field
from typing import Any, List, Mapping

from pfp_core.policies.domain.eligibility import (
    CheckoutRequirementsConfig,
    EligibilityConfig,
)
from pfp_core.policies.domain.strictness import StrictnessConfig
from pfp_core.policies.infra.fault_isolation_policy import FaultIsolationConfig
from pfp_core.policies.utils.policy_utils import (
    _normalize_version,
    _require_key,
    _require_mapping,
    _validate_keys,
)

__all__: List[str] = [
    "CheckoutRequirementsConfig",
    "EligibilityConfig",
    "FaultIsolationConfig",
    "PolicyConfig",
    "StrictnessConfig",
]


@dataclass(frozen=True)
class CorePolicyConfig:
    """Core domain policies configuration."""

    strictness: StrictnessConfig
    eligibility: EligibilityConfig
    fault_isolation: FaultIsolationConfig

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CorePolicyConfig":
        data = _require_mapping(data, "core")
        allowed = {
            "strictness",
            "eligibility",
            "fault_isolation",
        }
        _validate_keys(data, allowed, "core")

        return cls(
            strictness=StrictnessConfig.from_dict(
                _require_mapping(data.get("strictness", {}), "core.strictness")
            ),
            eligibility=EligibilityConfig.from_dict(
                _require_mapping(data.get("eligibility", {}), "core.eligibility")
            ),
            fault_isolation=FaultIsolationConfig.from_dict(
                _require_mapping(
                    data.get("fault_isolation", {}),
                    "core.fault_isolation",
                )
            ),
        )


@dataclass(frozen=True)
class InfrastructureConfig:
    """Infrastructure policies configuration."""

    fault_isolation: FaultIsolationConfig

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InfrastructureConfig":
        data = _require_mapping(data, "infrastructure")
        allowed = {"fault_isolation"}
        _validate_keys(data, allowed, "infrastructure")

        return cls(
            fault_isolation=FaultIsolationConfig.from_dict(
                _require_mapping(data.get("fault_isolation", {}), "fault_isolation")
            ),
        )


@dataclass(frozen=True)
class PolicyConfig:
    """Root configuration object for all policies."""

    version: str
    core: CorePolicyConfig
    infrastructure: InfrastructureConfig = field(
        default_factory=lambda: InfrastructureConfig.from_dict({})
    )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PolicyConfig":
        data = _require_mapping(data, "root")
        _validate_keys(data, {"version", "core"}, "root")

        version = _normalize_version(_require_key(data, "version", "root"))
        if version != "1.0":
            raise ValueError(f"Unsupported policy config version '{version}'")

        core_data = _require_mapping(
            data.get("core") if "core" in data else _require_key(data, "core", "root"),
            "core",
        )

        core = CorePolicyConfig.from_dict(core_data)

        return cls(
            version=version,
            core=core,
            infrastructure=InfrastructureConfig.from_dict(
                {
                    "fault_isolation": {"strategy": core.fault_isolation.strategy},
                }
            ),
        )
