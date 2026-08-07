"""Chaos tests for publish-step failures."""

from __future__ import annotations

import pytest

from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from tests.chaos._helpers import build_manifest, valid_jsonl_input, write_minimal_infra

pytestmark = [pytest.mark.chaos, pytest.mark.timeout(120)]


def test_publisher_raises_runtime_error(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runtime errors from publisher.publish must map to PUBLISH.ERROR."""
    manifest = build_manifest(write_minimal_infra(tmp_path))
    monkeypatch.setattr(
        manifest.publish.publisher,
        "publish",
        _raising_publish(RuntimeError("simulated publish failure")),
    )

    report = PipelineRunner(manifest).run(valid_jsonl_input())

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.error_type == "RuntimeError"
    assert "simulated publish failure" in report.message


def test_publisher_raises_timeout(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout errors from publisher.publish must map to PUBLISH.TIMEOUT."""
    manifest = build_manifest(write_minimal_infra(tmp_path))
    monkeypatch.setattr(
        manifest.publish.publisher,
        "publish",
        _raising_publish(TimeoutError("publish timed out")),
    )

    report = PipelineRunner(manifest).run(valid_jsonl_input())

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.TIMEOUT"
    assert report.error_type == "TimeoutError"
    assert "publish timed out" in report.message


def test_publisher_raises_connection_error(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection errors from publisher.publish must map to PUBLISH.ERROR."""
    manifest = build_manifest(write_minimal_infra(tmp_path))
    monkeypatch.setattr(
        manifest.publish.publisher,
        "publish",
        _raising_publish(ConnectionError("network unreachable")),
    )

    report = PipelineRunner(manifest).run(valid_jsonl_input())

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.error_type == "ConnectionError"
    assert "network unreachable" in report.message


def _raising_publish(exc: Exception):
    """Return a publish replacement that always raises the supplied exception."""

    def _publish(_artifact):
        raise exc

    return _publish
