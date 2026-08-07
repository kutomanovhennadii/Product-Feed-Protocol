"""Registry for policy factories."""

import logging
from typing import Any, Callable, Dict

from pfp_utils.logging import LogPipeline

PolicyFactory = Callable[[Any], Any]


class PolicyRegistry:
    """Registry of policy factories keyed by policy name."""

    def __init__(self, *, log_pipeline: LogPipeline) -> None:
        self._factories: Dict[str, PolicyFactory] = {}
        self._log_pipeline = log_pipeline

    def register(self, name: str, factory: PolicyFactory) -> None:
        """Register a policy factory under a name."""
        if name in self._factories:
            self._log(logging.ERROR, "Policy factory already registered")
            raise ValueError(f"Policy factory '{name}' is already registered")
        self._factories[name] = factory

    def build(self, name: str, config: Any) -> Any:
        """Build a policy using the factory registered for a name."""
        try:
            factory = self._factories[name]
        except KeyError as exc:
            self._log(logging.ERROR, "Unknown policy requested", exc_info=exc)
            raise ValueError(f"Unknown policy '{name}'") from exc
        return factory(config)

    def _log(self, level: int, message: str, *, exc_info: Any = None) -> None:
        self._log_pipeline.log_process(
            level,
            __name__,
            message,
            exc_info=exc_info,
        )
