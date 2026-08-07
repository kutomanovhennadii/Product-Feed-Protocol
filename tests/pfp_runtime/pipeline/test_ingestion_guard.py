"""Mirror unit tests for pfp_runtime.pipeline.ingestion_guard."""

from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Tuple

import pytest

from pfp_runtime.pipeline.ingestion_guard import (
    IngestionError,
    IngestionExtractCallError,
    IngestionExtractIterationError,
    guard_ingestion_stream,
    ingestion_step,
    resolve_ingestion_reason_code,
)
from pfp_utils.diagnostics.diagnostic_models import Diagnostic


class _ExtractResult(Iterable[int]):
    """Simple iterable result object exposing diagnostics for ingestion_step tests."""

    def __init__(
        self,
        items: Iterable[int],
        diagnostics: Tuple[Diagnostic, ...] = (),
    ) -> None:
        """Store source items and diagnostics for iteration.

        Args:
            items: Iterable returned by the synthetic connector.
            diagnostics: Diagnostics attached to the extract result.

        Returns:
            None.
        """
        self._items = items
        self.diagnostics = diagnostics

    def __iter__(self) -> Iterator[int]:
        """Yield items from the wrapped source iterable.

        Returns:
            Iterator over the wrapped items.
        """
        yield from self._items


class _ConnectorStub:
    """Test double exposing extract for ingestion_step scenarios."""

    def __init__(
        self,
        result: Optional[object] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Configure the connector stub for success or failure.

        Args:
            result: Object returned by extract when no error is configured.
            error: Optional exception raised by extract.

        Returns:
            None.
        """
        self._result = result
        self._error = error

    def extract(self, input_data: object) -> object:
        """Return configured result or raise configured extract error.

        Args:
            input_data: Raw input forwarded by the caller.

        Returns:
            Configured extract result object.

        Raises:
            Exception: Configured extract error for failure-path tests.
        """
        del input_data
        if self._error is not None:
            raise self._error
        return self._result


def test_ingestion_error_base_constructor() -> None:
    """Store message and original exception on the base ingestion error.

    Returns:
        None.
    """
    exc = ValueError("boom")

    error = IngestionError("msg", original_exc=exc)

    assert str(error) == "msg"
    assert error.original_exc is exc


def test_ingestion_extract_call_error_inherits_ingestion_error() -> None:
    """Expose call-time extract errors through the shared ingestion root type.

    Returns:
        None.
    """
    error = IngestionExtractCallError(
        "msg",
        original_exc=RuntimeError("boom"),
    )

    assert isinstance(error, IngestionError)


def test_ingestion_extract_iteration_error_inherits_ingestion_error() -> None:
    """Preserve root cause and chaining when iteration fails mid-stream.

    Returns:
        None.
    """

    def _boom() -> Iterator[int]:
        yield 1
        raise ValueError("broken source")

    iterator = iter(guard_ingestion_stream(_boom()))
    assert next(iterator) == 1

    with pytest.raises(IngestionExtractIterationError) as excinfo:
        next(iterator)

    assert isinstance(excinfo.value, IngestionError)
    assert isinstance(excinfo.value.original_exc, ValueError)
    assert str(excinfo.value.original_exc) == "broken source"
    assert excinfo.value.__cause__ is excinfo.value.original_exc


# ---------------------------------------------------------------------------
# guard_ingestion_stream
# ---------------------------------------------------------------------------


def test_guard_passes_items_through() -> None:
    """Values from the source iterable flow through the guard unchanged."""
    source: List[int] = [1, 2, 3]

    guarded: Iterable[int] = guard_ingestion_stream(iter(source))

    assert list(guarded) == source


def test_guard_completes_on_stop_iteration() -> None:
    """A generator that naturally completes passes through without raising."""

    def _empty() -> Iterator[int]:
        if False:
            yield 0  # pragma: no cover — empty generator
        return

    assert list(guard_ingestion_stream(_empty())) == []


def test_guard_wraps_runtime_exception() -> None:
    """A mid-stream exception is repackaged as IngestionExtractIterationError."""

    def _boom() -> Iterator[int]:
        yield 1
        raise ValueError("broken source")

    iterator = iter(guard_ingestion_stream(_boom()))
    assert next(iterator) == 1
    with pytest.raises(IngestionExtractIterationError) as excinfo:
        next(iterator)
    assert "broken source" in str(excinfo.value)
    assert isinstance(excinfo.value.original_exc, ValueError)
    assert excinfo.value.__cause__ is excinfo.value.original_exc


def test_guard_wraps_timeout_exception() -> None:
    """TimeoutError is also wrapped; guard does not distinguish exception types."""

    def _timeout() -> Iterator[int]:
        raise TimeoutError("read timed out")
        yield 0  # pragma: no cover — unreachable after raise

    iterator = iter(guard_ingestion_stream(_timeout()))
    with pytest.raises(IngestionExtractIterationError) as excinfo:
        next(iterator)
    assert "read timed out" in str(excinfo.value)
    assert isinstance(excinfo.value.original_exc, TimeoutError)


# ---------------------------------------------------------------------------
# ingestion_step
# ---------------------------------------------------------------------------


def test_ingestion_step_happy_path() -> None:
    """Return guarded items and attached diagnostics when extract succeeds.

    Returns:
        None.
    """
    diagnostics = (Diagnostic(severity="INFO", code="INGEST.OK", message="done"),)
    connector = _ConnectorStub(
        result=_ExtractResult([1, 2, 3], diagnostics=diagnostics)
    )

    items, result_diagnostics = ingestion_step(connector, b"raw")

    assert list(items) == [1, 2, 3]
    assert result_diagnostics == diagnostics


def test_ingestion_step_extract_failure_raises_extract_call_error() -> None:
    """Wrap synchronous extract failures in IngestionExtractCallError.

    Returns:
        None.
    """
    connector = _ConnectorStub(error=ValueError("bad input"))

    with pytest.raises(IngestionExtractCallError) as excinfo:
        ingestion_step(connector, b"raw")

    assert isinstance(excinfo.value.original_exc, ValueError)
    assert str(excinfo.value.original_exc) == "bad input"
    assert excinfo.value.__cause__ is excinfo.value.original_exc


def test_ingestion_step_iteration_failure_raises_iteration_error() -> None:
    """Expose lazy iteration failures through IngestionExtractIterationError.

    Returns:
        None.
    """

    def _boom() -> Iterator[int]:
        yield 1
        raise TimeoutError("read timed out")

    connector = _ConnectorStub(result=_ExtractResult(_boom()))

    items, diagnostics = ingestion_step(connector, b"raw")

    assert diagnostics == ()
    iterator = iter(items)
    assert next(iterator) == 1
    with pytest.raises(IngestionExtractIterationError) as excinfo:
        next(iterator)

    assert isinstance(excinfo.value.original_exc, TimeoutError)
    assert str(excinfo.value.original_exc) == "read timed out"
    assert excinfo.value.__cause__ is excinfo.value.original_exc


# ---------------------------------------------------------------------------
# resolve_ingestion_reason_code
# ---------------------------------------------------------------------------


def test_resolve_timeout_returns_extract_timeout() -> None:
    """TimeoutError maps to the timeout-specific reason code."""
    assert resolve_ingestion_reason_code(TimeoutError()) == "INGESTION.EXTRACT_TIMEOUT"


def test_resolve_generic_returns_extract_error() -> None:
    """Any non-timeout exception falls back to the generic extract error code."""
    assert resolve_ingestion_reason_code(RuntimeError()) == "INGESTION.EXTRACT_ERROR"


def test_resolve_timeout_subclass_returns_extract_timeout() -> None:
    """Subclasses of TimeoutError still hit the timeout branch (isinstance check)."""

    class _CustomTimeout(TimeoutError):
        pass

    assert (
        resolve_ingestion_reason_code(_CustomTimeout()) == "INGESTION.EXTRACT_TIMEOUT"
    )
