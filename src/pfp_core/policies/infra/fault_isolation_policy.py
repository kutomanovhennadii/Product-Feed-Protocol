"""Fault isolation policy implementation."""

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from pfp_core.policies.utils.policy_utils import _require_mapping, _validate_keys
from pfp_utils.logging import LogContext
from pfp_utils.logging.log_context import get_context
from pfp_utils.logging.log_pipeline import LogPipeline


@dataclass(frozen=True)
class FaultIsolationConfig:
    strategy: str = "SKIP_ITEM"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FaultIsolationConfig":
        data = _require_mapping(data, "infrastructure.fault_isolation")
        _validate_keys(data, {"strategy"}, "infrastructure.fault_isolation")

        strategy = data.get("strategy")
        if strategy is None:
            strategy = "SKIP_ITEM"
        elif not isinstance(strategy, str):
            raise ValueError("infrastructure.fault_isolation.strategy must be a string")

        valid_strategies = {"SKIP_ITEM", "FAIL_FAST", "IGNORE"}
        normalized = strategy.upper()
        if normalized not in valid_strategies:
            raise ValueError(
                f"Invalid fault isolation strategy '{strategy}'. "
                f"Must be one of: {', '.join(sorted(valid_strategies))}"
            )

        return cls(strategy=normalized)


class FaultIsolationPolicy:
    def __init__(
        self,
        config: FaultIsolationConfig,
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        self._strategy = config.strategy
        self._log_pipeline = log_pipeline

    def handle_error(
        self,
        error: Exception,
        context_msg: str = "Processing error",
    ) -> None:
        ctx = get_context()
        item_ref = ctx.get("item_ref", "unknown")

        with LogContext(item_ref=item_ref, strategy=self._strategy):
            self._log_pipeline.log_process(
                logging.ERROR,
                __name__,
                "%s: %s",
                context_msg,
                str(error),
                exc_info=error,
            )

        if self._strategy == "FAIL_FAST":
            raise error
