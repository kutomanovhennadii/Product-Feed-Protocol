"""No-op delivery client for client_type: noop.

Implements the DeliveryClient protocol without performing any I/O.
Used when delivery is intentionally disabled in the pipeline configuration.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict

from pfp_runtime.publishing.clients.client_contract import DeliveryResult


class NoopClientIaC(BaseModel):
    """IaC model for the no-op client. Contains no fields.

    Accepts an empty mapping. Supports future extension without builder changes.
    """

    model_config = ConfigDict(extra="forbid")


class NoopClient:
    """Delivery client that performs no I/O.

    Satisfies the DeliveryClient protocol structurally. Instantiated by client_builder
    when client_type is 'noop', using the standard 5-step build path.

    Args:
        iac: Validated NoopClientIaC instance (always empty).
    """

    def __init__(self, iac: NoopClientIaC) -> None:
        """Store IaC (unused, accepted for interface uniformity).

        Args:
            iac: Validated NoopClientIaC instance.
        """
        self._iac = iac

    def open(self) -> None:
        """No-op: no connection to prepare."""

    def send_chunk(self, chunk: bytes) -> None:
        """No-op: discard the chunk.

        Args:
            chunk: Payload bytes — ignored.
        """

    def finalize(self) -> DeliveryResult:
        """Return a skipped result with no status code.

        Returns:
            DeliveryResult with skipped=True and status_code=None.
        """
        return DeliveryResult(skipped=True, status_code=None)


__all__: List[str] = ["NoopClientIaC", "NoopClient"]
