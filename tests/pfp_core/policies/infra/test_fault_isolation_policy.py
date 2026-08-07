"""Tests for fault isolation policy."""

import logging
from unittest.mock import patch

import pytest

from pfp_core.policies.infra.fault_isolation_policy import (
    FaultIsolationConfig,
    FaultIsolationPolicy,
)


class _LogPipelineStub:
    def log_process(self, level, module_name, message, *args, **kwargs) -> None:
        extra = kwargs.get("extra")
        exc_info = kwargs.get("exc_info")
        logging.getLogger(module_name).log(
            level,
            message,
            *args,
            extra=extra,
            exc_info=exc_info,
        )


@patch("pfp_core.policies.infra.fault_isolation_policy.get_context")
def test_fault_isolation_handle_error_skip_item(mock_ctx, caplog) -> None:
    """SKIP_ITEM strategy logs and suppresses raised error."""
    mock_ctx.return_value = {"item_ref": "item_1"}
    policy = FaultIsolationPolicy(
        FaultIsolationConfig(strategy="SKIP_ITEM"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    with caplog.at_level(logging.ERROR):
        policy.handle_error(ValueError("oops"), "context")

    assert "context: oops" in caplog.text


@patch("pfp_core.policies.infra.fault_isolation_policy.get_context")
def test_fault_isolation_handle_error_fail_fast(mock_ctx, caplog) -> None:
    """FAIL_FAST strategy logs and re-raises original error."""
    mock_ctx.return_value = {"item_ref": "item_2"}
    policy = FaultIsolationPolicy(
        FaultIsolationConfig(strategy="FAIL_FAST"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="oops"):
            policy.handle_error(ValueError("oops"))

    assert "Processing error: oops" in caplog.text


def test_fault_isolation_config_defaults_and_validates_strategy() -> None:
    """Config loader defaults to SKIP_ITEM and rejects invalid strategy payloads."""

    assert FaultIsolationConfig.from_dict({}) == FaultIsolationConfig(
        strategy="SKIP_ITEM"
    )

    with pytest.raises(ValueError, match="must be a string"):
        FaultIsolationConfig.from_dict({"strategy": 1})

    with pytest.raises(ValueError, match="Invalid fault isolation strategy"):
        FaultIsolationConfig.from_dict({"strategy": "pause"})
