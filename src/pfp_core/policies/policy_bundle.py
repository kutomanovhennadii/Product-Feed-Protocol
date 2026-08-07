"""Policy bundle container types."""

from dataclasses import dataclass
from typing import Any, Optional

from pfp_core.policies.domain.strictness import StrictnessPolicy

OptionalPolicy = Optional[Any]


@dataclass(frozen=True)
class PolicyBundle:
    """Built policies ready for use by the core API."""

    strictness: StrictnessPolicy
    eligibility: OptionalPolicy = None
    logging: OptionalPolicy = None
    telemetry: OptionalPolicy = None
    fault_isolation: OptionalPolicy = None
