"""Tests for the RedactionStrategy runtime-checkable protocol."""

from __future__ import annotations

import logging

from pfp_utils.logging.filters.redaction_strategies.redaction_strategy import (
    RedactionStrategy,
)


class _StubWithApply:
    """Provide the ``apply`` method required by the ``RedactionStrategy`` Protocol.

    Returns:
        A test double that structurally satisfies the runtime-checkable Protocol.
    """

    def apply(self, record: logging.LogRecord) -> None:
        """Accept a log record to satisfy the Protocol contract.

        Args:
            record: LogRecord instance supplied by the caller.

        Returns:
            None.
        """
        del record


class _StubWithoutApply:
    """Represent a test double that intentionally omits the Protocol method.

    Returns:
        A test double that must fail the runtime-checkable Protocol check.
    """


def test_redaction_strategy_runtime_check_accepts_stub_with_apply() -> None:
    """Runtime-checkable Protocol must accept objects that expose apply()."""
    assert isinstance(_StubWithApply(), RedactionStrategy)


def test_redaction_strategy_runtime_check_rejects_object_without_apply() -> None:
    """Runtime-checkable Protocol must reject objects missing apply()."""
    assert not isinstance(_StubWithoutApply(), RedactionStrategy)
