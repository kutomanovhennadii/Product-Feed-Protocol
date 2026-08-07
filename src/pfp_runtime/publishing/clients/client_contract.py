"""Delivery client contract and result type for the v2 publisher stack.

Defines the streaming runtime cycle (open / send_chunk / finalize) used by
Publisher.publish(). Concrete implementations are configured via
__init__(self, iac: ConcreteIaC) and instantiated by client_builder.
NoopClient accepts NoopClientIaC — an empty Pydantic model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class DeliveryResult:
    """Result returned by DeliveryClient.finalize().

    Attributes:
        skipped: True when delivery was intentionally skipped (NoopClient).
        status_code: HTTP or SFTP status code, or None when not applicable.
    """

    skipped: bool
    status_code: Optional[int] = None


@runtime_checkable
class DeliveryClient(Protocol):
    """Structural protocol for the runtime delivery client interface.

    Defines the streaming runtime cycle used by Publisher.publish().
    Concrete implementations are configured via __init__(self, iac: ConcreteIaC)
    and instantiated by client_builder. NoopClient accepts NoopClientIaC — an empty Pydantic model.

    Implementations: HttpDeliveryClient, SftpDeliveryClient, NoopClient.
    """

    def open(self) -> None:
        """Prepare connection (open HTTP stream, SFTP channel, etc.)."""
        ...

    def send_chunk(self, chunk: bytes) -> None:
        """Send one chunk of payload bytes to the remote endpoint."""
        ...

    def finalize(self) -> DeliveryResult:
        """Flush, close connection, and return result metadata."""
        ...


__all__ = ["DeliveryClient", "DeliveryResult"]
