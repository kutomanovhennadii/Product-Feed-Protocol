"""Shared fixtures for Phase 10 matrix tests.

Returns:
    None.
"""

from __future__ import annotations

import logging
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture(autouse=True)
def restore_matrix_log_pipeline_state() -> Generator[None, None, None]:
    """Restore root logging handlers after each matrix test.

    Matrix cells build a process-global ``LogPipeline`` handler and reject a
    second installation in the same process. Parameterized matrix tests execute
    multiple runtime cells sequentially, so the handler state must be cleaned up
    after every case.

    Yields:
        None while the test executes.

    Returns:
        Generator used by pytest to restore the original root logger state.
    """
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    yield

    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # nosec B110
                pass

    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


@pytest.fixture
def prometheus_registry() -> CollectorRegistry:
    """Provide an isolated Prometheus registry per test.

    Returns:
        CollectorRegistry configured with auto-describe enabled.
    """
    return CollectorRegistry(auto_describe=True)


@pytest.fixture
def moto_s3_bucket() -> Generator[str, None, None]:
    """Provide a hermetic S3 bucket inside moto.

    Yields:
        Name of the temporary S3 bucket created for the test.

    Returns:
        Generator that tears down the moto-backed AWS context.
    """
    import boto3
    from moto import mock_aws

    bucket_name = "phase10-matrix-tests"
    with mock_aws():
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket=bucket_name)
        yield bucket_name


@pytest.fixture
def mock_http_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch httpx client constructors with a shared MagicMock.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to replace constructors.

    Returns:
        Shared mock instance returned by both sync and async HTTP clients.
    """
    import httpx

    client = MagicMock(name="httpx_client")
    monkeypatch.setattr(httpx, "Client", MagicMock(return_value=client))
    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=client))
    return client


@pytest.fixture
def mock_sftp_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch paramiko transport constructor with a shared MagicMock.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to replace transport creation.

    Returns:
        Shared mock transport returned by the patched constructor.
    """
    import paramiko

    transport = MagicMock(name="paramiko_transport")
    monkeypatch.setattr(paramiko, "Transport", MagicMock(return_value=transport))
    return transport


@pytest.fixture
def tmp_archive_dir(tmp_path: Path) -> Path:
    """Provide a temporary local archive directory.

    Args:
        tmp_path: Pytest temporary directory root for the current test.

    Returns:
        Path to the created archive directory.
    """
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


@contextmanager
def noop_capture() -> Iterator[None]:
    """Yield a no-op capture context for tests without side effects.

    Yields:
        None while the caller executes inside the context manager.

    Returns:
        Iterator used by contextmanager to provide a no-op context.
    """
    yield
