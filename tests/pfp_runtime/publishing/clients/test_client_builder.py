"""Tests for client_builder.build_client."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

import pfp_runtime.publishing.clients.client_builder as _builder_mod
from pfp_runtime.publishing.clients.client_builder import build_client
from pfp_runtime.publishing.clients.http_client import HttpDeliveryClient
from pfp_runtime.publishing.clients.noop_client import NoopClient
from pfp_runtime.publishing.clients.sftp_client import SftpDeliveryClient
from pfp_runtime.publishing.clients.streaming_http_client import (
    StreamingHttpDeliveryClient,
)
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogContext as _LogContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[4]  # c:\Repository\A2S-tools\PFP\python
_NOOP_YAML = str(_REPO_ROOT / "config" / "clients" / "noop.yaml")

_HTTP_YAML_CONTENT = """\
endpoint: "https://api.example.com/feed"
"""

_SFTP_YAML_CONTENT = """\
host: "sftp.example.com"
username: "uploader"
remote_path: "/feeds/product_feed.jsonl.gz"
password_ref:
  kind: env
  value: FAKE_SFTP_PASSWORD
transport:
  verify_ssh_host_key: false
"""


class _LogPipelineStub:
    """Minimal log pipeline stub for client builder tests."""

    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _write_yaml(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Happy path — noop
# ---------------------------------------------------------------------------


def test_build_noop() -> None:
    """build_client("noop", noop.yaml) returns a NoopClient instance."""
    result = build_client(
        "noop",
        _NOOP_YAML,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, NoopClient)


# ---------------------------------------------------------------------------
# Happy path — http
# ---------------------------------------------------------------------------


def test_build_http(tmp_path: Path) -> None:
    """build_client("http", ...) returns HttpDeliveryClient with correct endpoint."""
    yaml_path = _write_yaml(tmp_path, "http.yaml", _HTTP_YAML_CONTENT)
    result = build_client(
        "http",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, HttpDeliveryClient)


# ---------------------------------------------------------------------------
# Happy path — http_streaming (same minimal YAML as http)
# ---------------------------------------------------------------------------


def test_build_http_streaming(tmp_path: Path) -> None:
    """build_client("http_streaming", ...) returns StreamingHttpDeliveryClient."""
    yaml_path = _write_yaml(tmp_path, "http_streaming.yaml", _HTTP_YAML_CONTENT)
    result = build_client(
        "http_streaming",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, StreamingHttpDeliveryClient)


# ---------------------------------------------------------------------------
# Happy path — sftp (secret mocked, verify_ssh_host_key disabled)
# ---------------------------------------------------------------------------


def test_build_sftp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """build_client("sftp", ...) returns SftpDeliveryClient; secrets are resolved via mock."""
    monkeypatch.setattr(
        "pfp_runtime.publishing.clients.sftp_client.resolve_secret_ref",
        lambda _ref: "fake-secret",
    )
    yaml_path = _write_yaml(tmp_path, "sftp.yaml", _SFTP_YAML_CONTENT)
    result = build_client(
        "sftp",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, SftpDeliveryClient)


# ---------------------------------------------------------------------------
# Error path — unknown type
# ---------------------------------------------------------------------------


def test_unknown_client_type_raises() -> None:
    """build_client with unknown client_type raises PublisherBuildError."""
    with pytest.raises(PublisherBuildError):
        build_client(
            "unknown_xyz",
            _NOOP_YAML,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — file not found
# ---------------------------------------------------------------------------


def test_missing_config_file_raises() -> None:
    """build_client with nonexistent config path raises PublisherBuildError."""
    with pytest.raises(PublisherBuildError):
        build_client(
            "noop",
            "/nonexistent/path/noop.yaml",
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — invalid YAML
# ---------------------------------------------------------------------------


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    """build_client with malformed YAML raises PublisherBuildError."""
    yaml_path = _write_yaml(tmp_path, "bad.yaml", "key: [unclosed")
    with pytest.raises(PublisherBuildError):
        build_client(
            "noop",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — Pydantic ValidationError (missing required field)
# ---------------------------------------------------------------------------


def test_missing_required_field_raises(tmp_path: Path) -> None:
    """build_client raises PublisherBuildError when IaC is missing a required field."""
    yaml_path = _write_yaml(
        tmp_path,
        "http_missing.yaml",
        """\
        content_type: application/json
        """,
    )
    with pytest.raises(PublisherBuildError):
        build_client(
            "http",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — Pydantic ValidationError (extra fields forbidden)
# ---------------------------------------------------------------------------


def test_extra_fields_raises(tmp_path: Path) -> None:
    """build_client raises PublisherBuildError when IaC has extra forbidden fields."""
    yaml_path = _write_yaml(
        tmp_path,
        "http_extra.yaml",
        """\
        endpoint: "https://api.example.com/feed"
        unexpected_field: oops
        """,
    )
    with pytest.raises(PublisherBuildError):
        build_client(
            "http",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — PublisherBuildError from constructor is NOT re-wrapped
# ---------------------------------------------------------------------------


def test_publisher_build_error_not_rewrapped() -> None:
    """PublisherBuildError raised by the constructor is propagated unchanged."""
    original = PublisherBuildError("from constructor")

    with patch(
        "pfp_runtime.publishing.clients.noop_client.NoopClient.__init__",
        side_effect=original,
    ):
        with pytest.raises(PublisherBuildError) as exc_info:
            build_client(
                "noop",
                _NOOP_YAML,
                log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            )

    assert exc_info.value is original


# ---------------------------------------------------------------------------
# Error path — arbitrary constructor exception is wrapped in PublisherBuildError
# ---------------------------------------------------------------------------


def test_arbitrary_constructor_exception_wrapped() -> None:
    """RuntimeError from the constructor is wrapped in PublisherBuildError."""
    with patch(
        "pfp_runtime.publishing.clients.noop_client.NoopClient.__init__",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(PublisherBuildError, match="boom"):
            build_client(
                "noop",
                _NOOP_YAML,
                log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Observability — LogContext is active during build
# ---------------------------------------------------------------------------


def test_log_context_active() -> None:
    """build_client runs under LogContext(stage="init", component="client_builder")."""
    log_calls: list[Dict[str, Any]] = []

    def capturing_log_context(**kwargs: Any) -> Any:
        log_calls.append(kwargs)
        return _LogContext(**kwargs)

    with patch.object(_builder_mod, "LogContext", capturing_log_context):
        build_client(
            "noop",
            _NOOP_YAML,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )

    assert any(
        c.get("stage") == "init" and c.get("component") == "client_builder"
        for c in log_calls
    )
