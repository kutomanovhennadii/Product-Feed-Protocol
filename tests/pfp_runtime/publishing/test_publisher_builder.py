"""Tests for publisher_builder.build_publisher."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

import pfp_runtime.publishing.publisher_builder as _builder_mod
from pfp_runtime.publishing.archivers.noop_archiver import NoopArchiver
from pfp_runtime.publishing.clients.noop_client import NoopClient
from pfp_runtime.publishing.contracts.publisher_contract import Publisher
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_runtime.publishing.publisher_builder import build_publisher
from pfp_utils.logging import LogContext as _LogContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]  # c:\Repository\A2S-tools\PFP\python
_NOOP_ARCHIVE_YAML = str(_REPO_ROOT / "config" / "archive" / "noop.yaml")
_NOOP_CLIENT_YAML = str(_REPO_ROOT / "config" / "clients" / "noop.yaml")

_NOOP_CONFIG: Dict[str, Any] = {
    "archive_type": "noop",
    "archive_config": _NOOP_ARCHIVE_YAML,
    "client_type": "noop",
    "client_config": _NOOP_CLIENT_YAML,
}


class _LogPipelineStub:
    """Minimal log pipeline stub for builder tests."""

    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_build_publisher_noop() -> None:
    """build_publisher with noop types returns a Publisher with NoopArchiver and NoopClient."""
    result = build_publisher(
        _NOOP_CONFIG,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, Publisher)
    assert isinstance(result.archiver, NoopArchiver)
    assert isinstance(result.client, NoopClient)


# ---------------------------------------------------------------------------
# Error path — missing required keys
# ---------------------------------------------------------------------------


def test_missing_archive_type_raises() -> None:
    """build_publisher raises PublisherBuildError when archive_type is missing."""
    config = {k: v for k, v in _NOOP_CONFIG.items() if k != "archive_type"}
    with pytest.raises(PublisherBuildError, match="archive_type"):
        build_publisher(config, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


def test_missing_archive_config_raises() -> None:
    """build_publisher raises PublisherBuildError when archive_config is missing."""
    config = {k: v for k, v in _NOOP_CONFIG.items() if k != "archive_config"}
    with pytest.raises(PublisherBuildError, match="archive_config"):
        build_publisher(config, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


def test_missing_client_type_raises() -> None:
    """build_publisher raises PublisherBuildError when client_type is missing."""
    config = {k: v for k, v in _NOOP_CONFIG.items() if k != "client_type"}
    with pytest.raises(PublisherBuildError, match="client_type"):
        build_publisher(config, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


def test_missing_client_config_raises() -> None:
    """build_publisher raises PublisherBuildError when client_config is missing."""
    config = {k: v for k, v in _NOOP_CONFIG.items() if k != "client_config"}
    with pytest.raises(PublisherBuildError, match="client_config"):
        build_publisher(config, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Error path — PublisherBuildError from sub-builders propagated unchanged
# ---------------------------------------------------------------------------


def test_archiver_build_error_propagated() -> None:
    """PublisherBuildError from build_archiver is propagated without re-wrapping."""
    original = PublisherBuildError("archiver failed")
    with patch.object(_builder_mod, "build_archiver", side_effect=original):
        with pytest.raises(PublisherBuildError) as exc_info:
            build_publisher(_NOOP_CONFIG, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]
    assert exc_info.value is original


def test_client_build_error_propagated() -> None:
    """PublisherBuildError from build_client is propagated without re-wrapping."""
    original = PublisherBuildError("client failed")
    with patch.object(_builder_mod, "build_archiver", return_value=MagicMock()):
        with patch.object(_builder_mod, "build_client", side_effect=original):
            with pytest.raises(PublisherBuildError) as exc_info:
                build_publisher(_NOOP_CONFIG, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]
    assert exc_info.value is original


# ---------------------------------------------------------------------------
# Error path — arbitrary exception wrapped in PublisherBuildError
# ---------------------------------------------------------------------------


def test_arbitrary_exception_wrapped() -> None:
    """RuntimeError from build_archiver is wrapped in PublisherBuildError."""
    with patch.object(_builder_mod, "build_archiver", side_effect=RuntimeError("boom")):
        with pytest.raises(PublisherBuildError, match="boom"):
            build_publisher(_NOOP_CONFIG, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Observability — LogContext active during build
# ---------------------------------------------------------------------------


def test_log_context_active() -> None:
    """build_publisher runs under LogContext(stage="init", component="publisher_builder")."""
    log_calls: list[Dict[str, Any]] = []

    def capturing_log_context(**kwargs: Any) -> Any:
        log_calls.append(kwargs)
        return _LogContext(**kwargs)

    with patch.object(_builder_mod, "LogContext", capturing_log_context):
        build_publisher(_NOOP_CONFIG, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]

    assert any(
        c.get("stage") == "init" and c.get("component") == "publisher_builder"
        for c in log_calls
    )
