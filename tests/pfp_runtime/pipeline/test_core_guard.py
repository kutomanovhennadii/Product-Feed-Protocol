"""Mirror unit tests for pfp_runtime.pipeline.core_guard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pytest

from pfp_core.contracts.artifact_production_result import ArtifactProductionResult
from pfp_runtime.pipeline.core_guard import (
    CoreContractError,
    CoreError,
    core_step,
    guard_core,
    resolve_core_reason_code,
)
from pfp_runtime.pipeline.ingestion_guard import IngestionExtractIterationError
from pfp_utils.diagnostics.validation_report import ValidationReport


class _ProducerStub:
    """Test double exposing produce_artifacts for core_step scenarios."""

    def __init__(
        self,
        result: Optional[ArtifactProductionResult] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Configure producer success or failure behavior.

        Args:
            result: Result returned by produce_artifacts on success.
            error: Optional exception raised by produce_artifacts.

        Returns:
            None.
        """
        self._result = result
        self._error = error
        self.received_items: Optional[Iterable[Any]] = None
        self.received_generated_at: Optional[datetime] = None

    def produce_artifacts(
        self,
        um_items: Iterable[Any],
        *,
        generated_at: Optional[datetime] = None,
    ) -> ArtifactProductionResult:
        """Return configured result or raise configured producer error.

        Args:
            um_items: Input iterable forwarded by core_step.
            generated_at: Optional timestamp forwarded by core_step.

        Returns:
            Configured artifact production result.

        Raises:
            Exception: Configured producer error for failure-path tests.
        """
        self.received_items = um_items
        self.received_generated_at = generated_at
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def test_core_error_base_constructor() -> None:
    """Store message and original exception on the base core error.

    Returns:
        None.
    """
    exc = RuntimeError("boom")

    error = CoreError("msg", original_exc=exc)

    assert str(error) == "msg"
    assert error.original_exc is exc


def test_core_contract_error_inherits_core_error() -> None:
    """Expose contract failures through the shared core root type.

    Returns:
        None.
    """
    error = CoreContractError("msg", original_exc=ValueError("boom"))

    assert isinstance(error, CoreError)


def test_guard_core_wraps_value_error_in_contract_error() -> None:
    """Wrap ValueError failures in CoreContractError and preserve cause.

    Returns:
        None.
    """
    with pytest.raises(CoreContractError) as exc_info:
        guard_core(lambda: (_ for _ in ()).throw(ValueError("bad contract")))

    assert isinstance(exc_info.value.original_exc, ValueError)
    assert str(exc_info.value.original_exc) == "bad contract"
    assert exc_info.value.__cause__ is exc_info.value.original_exc


def test_guard_core_wraps_generic_exception_in_core_error() -> None:
    """Wrap non-contract failures in CoreError and preserve cause.

    Returns:
        None.
    """
    with pytest.raises(CoreError) as exc_info:
        guard_core(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert type(exc_info.value) is CoreError
    assert isinstance(exc_info.value.original_exc, RuntimeError)
    assert str(exc_info.value.original_exc) == "boom"
    assert exc_info.value.__cause__ is exc_info.value.original_exc


def test_guard_core_re_raises_existing_core_error() -> None:
    """Leave already-wrapped CoreError instances untouched.

    Returns:
        None.
    """
    original_error = CoreError("boom", original_exc=RuntimeError("boom"))

    with pytest.raises(CoreError) as exc_info:
        guard_core(lambda: (_ for _ in ()).throw(original_error))

    assert exc_info.value is original_error


def test_guard_core_re_raises_existing_ingestion_error() -> None:
    """Propagate ingestion-origin failures unchanged through the core guard.

    Returns:
        None.
    """
    original_error = IngestionExtractIterationError(
        "ingestion failed",
        original_exc=TimeoutError("slow source"),
    )

    with pytest.raises(IngestionExtractIterationError) as exc_info:
        guard_core(lambda: (_ for _ in ()).throw(original_error))

    assert exc_info.value is original_error


def test_core_step_returns_producer_result() -> None:
    """Forward items and generated_at to producer and return its result.

    Returns:
        None.
    """
    items = [1, 2, 3]
    generated_at = datetime(2026, 4, 29, tzinfo=timezone.utc)
    result = ArtifactProductionResult(
        artifacts=tuple(),
        validation_report=ValidationReport(target=None, artifact_profile=None),
    )
    producer = _ProducerStub(result=result)

    actual = core_step(producer, items, generated_at)

    assert actual is result
    assert producer.received_items is items
    assert producer.received_generated_at is generated_at


def test_resolve_core_reason_code_returns_contract_error_for_value_error() -> None:
    """Map ValueError to the core contract-error reason code.

    Returns:
        None.
    """
    assert resolve_core_reason_code(ValueError("bad contract")) == (
        "CORE.CONTRACT_ERROR"
    )


def test_resolve_core_reason_code_returns_contract_error_for_value_subclass() -> None:
    """Map ValueError subclasses to the same contract-error reason code.

    Returns:
        None.
    """

    class _CoreValueError(ValueError):
        """Local ValueError subclass for reason-code coverage."""

    assert resolve_core_reason_code(_CoreValueError("bad contract")) == (
        "CORE.CONTRACT_ERROR"
    )


def test_resolve_core_reason_code_returns_internal_error_for_runtime_error() -> None:
    """Map non-ValueError exceptions to the generic internal core code.

    Returns:
        None.
    """
    assert resolve_core_reason_code(RuntimeError("boom")) == "INTERNAL.ERROR"
