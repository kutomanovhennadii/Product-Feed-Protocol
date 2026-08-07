"""Integration tests for the pfp_utils.logging block."""

from __future__ import annotations

import json
import logging

from pfp_utils.logging import LogContext, build_log_pipeline


def test_log_pipeline_emits_contextualized_text_logs(capsys) -> None:
    """Logging block installs a pipeline and emits formatted records with context.

    Args:
        capsys: Pytest capture fixture used to inspect emitted log output.
    """

    pipeline = build_log_pipeline("INFO", "TEXT", {})

    with LogContext(stage="integration", target="stripe.product_feed"):
        pipeline.log_process(
            logging.INFO,
            __name__,
            "integration log message",
            extra={"force_log": True},
        )

    captured = capsys.readouterr()

    assert "integration log message" in captured.out
    assert "stage=integration" in captured.out
    assert "target=stripe.product_feed" in captured.out


def test_log_pipeline_suppresses_repeated_item_logs_under_rate_limit(capsys) -> None:
    """Logging block rate-limits repeated INFO records for the same item context.

    Args:
        capsys: Pytest capture fixture used to inspect emitted log output.
    """

    pipeline = build_log_pipeline(
        "INFO",
        "TEXT",
        {
            "mode": "rate_limit",
            "context_keys": ["item_ref"],
            "suppressed_levels": ["INFO"],
            "window_seconds": 30.0,
            "max_events_per_window": 1,
        },
    )

    with LogContext(item_ref="SKU-1", stage="integration"):
        pipeline.log_process(logging.INFO, __name__, "duplicate item log")
        pipeline.log_process(logging.INFO, __name__, "duplicate item log")

    lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if "duplicate item log" in line
    ]

    assert len(lines) == 1


def test_log_pipeline_emits_json_records_with_context(capsys) -> None:
    """Logging block supports JSON output while preserving context fields.

    Args:
        capsys: Pytest capture fixture used to inspect emitted log output.
    """

    pipeline = build_log_pipeline("INFO", "JSON", {})

    with LogContext(stage="integration", target="stripe.product_feed"):
        pipeline.log_process(logging.INFO, __name__, "json integration log")

    payload = json.loads(capsys.readouterr().out.strip())

    assert payload["message"] == "json integration log"
    assert payload["context"]["stage"] == "integration"
    assert payload["context"]["target"] == "stripe.product_feed"
