"""Ingestion stream guard and reason-code classifier.

Guards the lazy ingestion iterable returned by SourceConnector.extract so
mid-stream failures surfacing during downstream consumption are reported
as ingestion-origin errors. Pairs with a small classifier that maps
caught exceptions to stable reason codes used in ExecutionReport.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

from pfp_utils.diagnostics.diagnostic_models import Diagnostic


class IngestionError(RuntimeError):
    """Base exception for ingestion-step failures."""

    def __init__(
        self,
        message: str,
        *,
        original_exc: Exception,
    ) -> None:
        """Initialize ingestion failure with its root cause.

        Args:
            message: Human-readable failure message.
            original_exc: Original exception raised by the ingestion path.

        Returns:
            None.
        """
        super().__init__(message)
        self.original_exc = original_exc


class IngestionExtractCallError(IngestionError):
    """Raised when connector.extract fails synchronously."""


class IngestionExtractIterationError(IngestionError):
    """Raised when ingestion iterable fails during iteration."""


def ingestion_step(
    connector: Any,
    input_data: Any,
) -> Tuple[Iterable[Any], Tuple[Diagnostic, ...]]:
    """Run connector.extract and wrap call-time ingestion failures.

    Args:
        connector: Runtime connector exposing an extract method.
        input_data: Raw input forwarded to connector.extract.

    Returns:
        Tuple of guarded items iterable and collected diagnostics.

    Raises:
        IngestionExtractCallError: If connector.extract fails synchronously.
    """
    try:
        extract_result = connector.extract(input_data)
    except Exception as exc:
        raise IngestionExtractCallError(str(exc), original_exc=exc) from exc

    items = guard_ingestion_stream(extract_result)
    diagnostics = tuple(getattr(extract_result, "diagnostics", ()))
    return items, diagnostics


def guard_ingestion_stream(items: Iterable[Any]) -> Iterable[Any]:
    """Guard ingestion iteration so mid-stream failures are reported consistently.

    Args:
        items: Ingestion items iterable.

    Returns:
        Iterable yielding items from the source iterable.

    Raises:
        IngestionExtractIterationError: If iteration over the source iterable fails.
    """
    iterator = iter(items)
    while True:
        try:
            yield next(iterator)
        except StopIteration:
            return
        except Exception as exc:
            raise IngestionExtractIterationError(
                "ingestion iteration failed: " + str(exc),
                original_exc=exc,
            ) from exc


def resolve_ingestion_reason_code(exc: Exception) -> str:
    """Map ingestion extract failure type to deterministic reason code.

    Args:
        exc: Exception raised during ingestion extract or its stream consumption.

    Returns:
        Stable reason code string used in ExecutionReport.
    """
    if isinstance(exc, TimeoutError):
        return "INGESTION.EXTRACT_TIMEOUT"
    return "INGESTION.EXTRACT_ERROR"


__all__: List[str] = [
    "IngestionError",
    "IngestionExtractCallError",
    "IngestionExtractIterationError",
    "ingestion_step",
    "guard_ingestion_stream",
    "resolve_ingestion_reason_code",
]
