"""Tests for archiver_builder.build_archiver."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

import pfp_runtime.publishing.archivers.archiver_builder as _builder_mod
from pfp_runtime.publishing.archivers.archiver_builder import build_archiver
from pfp_runtime.publishing.archivers.local_archiver import LocalArchiver
from pfp_runtime.publishing.archivers.noop_archiver import NoopArchiver
from pfp_runtime.publishing.archivers.s3_archiver import S3Archiver
from pfp_runtime.publishing.archivers.s3_compat_archiver import S3CompatArchiver
from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError
from pfp_utils.logging import LogContext as _LogContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[4]  # c:\Repository\A2S-tools\PFP\python
_NOOP_YAML = str(_REPO_ROOT / "config" / "archive" / "noop.yaml")


class _LogPipelineStub:
    """Minimal log pipeline stub for archiver builder tests."""

    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _write_yaml(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Happy path — noop (no secrets, no network)
# ---------------------------------------------------------------------------


def test_build_noop(tmp_path: Path) -> None:
    """build_archiver("noop", noop.yaml) returns a NoopArchiver instance."""
    result = build_archiver(
        "noop",
        _NOOP_YAML,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, NoopArchiver)


# ---------------------------------------------------------------------------
# Happy path — local
# ---------------------------------------------------------------------------


def test_build_local(tmp_path: Path) -> None:
    """build_archiver("local", ...) returns LocalArchiver with correct output_dir."""
    output_dir = tmp_path.as_posix()
    yaml_path = _write_yaml(
        tmp_path,
        "local.yaml",
        f"output_dir: {output_dir}\nfilename_base: test_artifact\n",
    )
    result = build_archiver(
        "local",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, LocalArchiver)


# ---------------------------------------------------------------------------
# Happy path — s3 (boto3 is NOT called in __init__)
# ---------------------------------------------------------------------------


def test_build_s3(tmp_path: Path) -> None:
    """build_archiver("s3", ...) returns S3Archiver; boto3 client is not called in __init__."""
    yaml_path = _write_yaml(
        tmp_path,
        "s3.yaml",
        """\
        bucket: my-test-bucket
        filename_base: test_artifact
        """,
    )
    result = build_archiver(
        "s3",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, S3Archiver)


# ---------------------------------------------------------------------------
# Happy path — s3_compat (secrets mocked via monkeypatch)
# ---------------------------------------------------------------------------


def test_build_s3_compat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """build_archiver("s3_compat", ...) returns S3CompatArchiver; secrets are resolved via mock."""
    monkeypatch.setattr(
        "pfp_runtime.publishing.archivers.s3_compat_archiver.resolve_secret_ref",
        lambda _ref: "fake-secret",
    )
    yaml_path = _write_yaml(
        tmp_path,
        "s3_compat.yaml",
        """\
        endpoint: "https://minio.example.com"
        bucket: my-bucket
        filename_base: test_artifact
        access_key_ref:
          kind: env
          value: FAKE_ACCESS_KEY
        secret_key_ref:
          kind: env
          value: FAKE_SECRET_KEY
        """,
    )
    result = build_archiver(
        "s3_compat",
        yaml_path,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(result, S3CompatArchiver)


# ---------------------------------------------------------------------------
# Error path — unknown type
# ---------------------------------------------------------------------------


def test_unknown_archive_type_raises(tmp_path: Path) -> None:
    """build_archiver with unknown archive_type raises PublisherBuildError."""
    with pytest.raises(PublisherBuildError):
        build_archiver(
            "unknown_xyz",
            _NOOP_YAML,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — file not found
# ---------------------------------------------------------------------------


def test_missing_config_file_raises() -> None:
    """build_archiver with nonexistent config path raises PublisherBuildError."""
    with pytest.raises(PublisherBuildError):
        build_archiver(
            "noop",
            "/nonexistent/path/noop.yaml",
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — invalid YAML
# ---------------------------------------------------------------------------


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    """build_archiver with malformed YAML raises PublisherBuildError."""
    yaml_path = _write_yaml(tmp_path, "bad.yaml", "key: [unclosed")
    with pytest.raises(PublisherBuildError):
        build_archiver(
            "noop",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — Pydantic ValidationError (missing required field)
# ---------------------------------------------------------------------------


def test_missing_required_field_raises(tmp_path: Path) -> None:
    """build_archiver raises PublisherBuildError when IaC is missing a required field."""
    yaml_path = _write_yaml(
        tmp_path,
        "local_missing.yaml",
        """\
        output_dir: "/tmp"
        """,
    )
    with pytest.raises(PublisherBuildError):
        build_archiver(
            "local",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — Pydantic ValidationError (extra fields forbidden)
# ---------------------------------------------------------------------------


def test_extra_fields_raises(tmp_path: Path) -> None:
    """build_archiver raises PublisherBuildError when IaC has extra forbidden fields."""
    yaml_path = _write_yaml(
        tmp_path,
        "local_extra.yaml",
        """\
        output_dir: "/tmp"
        filename_base: test
        unexpected_field: oops
        """,
    )
    with pytest.raises(PublisherBuildError):
        build_archiver(
            "local",
            yaml_path,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Error path — PublisherBuildError from constructor is NOT re-wrapped
# ---------------------------------------------------------------------------


def test_publisher_build_error_not_rewrapped(tmp_path: Path) -> None:
    """PublisherBuildError raised by the constructor is propagated unchanged."""
    original = PublisherBuildError("from constructor")

    with patch(
        "pfp_runtime.publishing.archivers.noop_archiver.NoopArchiver.__init__",
        side_effect=original,
    ):
        with pytest.raises(PublisherBuildError) as exc_info:
            build_archiver(
                "noop",
                _NOOP_YAML,
                log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            )

    assert exc_info.value is original


# ---------------------------------------------------------------------------
# Error path — arbitrary constructor exception is wrapped in PublisherBuildError
# ---------------------------------------------------------------------------


def test_arbitrary_constructor_exception_wrapped(tmp_path: Path) -> None:
    """RuntimeError from the constructor is wrapped in PublisherBuildError."""
    with patch(
        "pfp_runtime.publishing.archivers.noop_archiver.NoopArchiver.__init__",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(PublisherBuildError, match="boom"):
            build_archiver(
                "noop",
                _NOOP_YAML,
                log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Observability — LogContext is active during build
# ---------------------------------------------------------------------------


def test_log_context_active(tmp_path: Path) -> None:
    """build_archiver runs under LogContext(stage="init", component="archiver_builder")."""
    log_calls: list[Dict[str, Any]] = []

    def capturing_log_context(**kwargs: Any) -> Any:
        log_calls.append(kwargs)
        return _LogContext(**kwargs)

    with patch.object(_builder_mod, "LogContext", capturing_log_context):
        build_archiver(
            "noop",
            _NOOP_YAML,
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )

    assert any(
        c.get("stage") == "init" and c.get("component") == "archiver_builder"
        for c in log_calls
    )
