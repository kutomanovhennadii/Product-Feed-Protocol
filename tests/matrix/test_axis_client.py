"""Client-axis matrix coverage for Phase 10.

Returns:
    None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import paramiko
import pytest

from pfp_runtime.publishing.contracts import PublishMetadata
from tests.matrix._axis_helpers import (
    MATRIX_ROOT,
    assert_success_baseline,
    count_fixture_records,
    read_yaml,
)
from tests.matrix.matrix_runner import run_matrix_cell

_CLIENT_CASES = (
    pytest.param("infra_noop.yaml", "noop", id="noop"),
    pytest.param("infra_http.yaml", "http", id="http"),
    pytest.param("infra_sftp.yaml", "sftp", id="sftp"),
    pytest.param("infra_http_streaming.yaml", "http_streaming", id="http-streaming"),
)


def _make_http_response(status_code: int) -> MagicMock:
    """Create a lightweight HTTP response double with a status code.

    Args:
        status_code: HTTP status code to expose on the response object.

    Returns:
        Mock response instance.
    """
    response = MagicMock(name=f"http_response_{status_code}")
    response.status_code = status_code
    return response


@pytest.mark.parametrize(("infra_name", "client_type"), _CLIENT_CASES)
def test_client_axis_delivers_payload_through_expected_transport(
    infra_name: str,
    client_type: str,
    monkeypatch: pytest.MonkeyPatch,
    mock_http_client: MagicMock,
    mock_sftp_client: MagicMock,
) -> None:
    """Each client variant must propagate the published bytes through its transport seam.

    Args:
        infra_name: Client infra filename.
        client_type: Expected runtime client type token.
        monkeypatch: Pytest monkeypatch fixture for patching transport seams.
        mock_http_client: Shared HTTP client mock fixture.
        mock_sftp_client: Shared SFTP transport mock fixture.

    Returns:
        None.
    """
    infra_path = MATRIX_ROOT / "infra" / "client" / infra_name
    fixture_path = MATRIX_ROOT / "fixtures" / "default.jsonl"
    input_format = str(read_yaml(infra_path)["input"]["format"])

    if client_type == "http":
        mock_http_client.post.return_value = _make_http_response(200)
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    elif client_type == "http_streaming":
        streamed_chunks: list[bytes] = []

        def _capture_streaming_post(*args, **kwargs):
            """Drain the streaming iterator passed into httpx.post().

            Args:
                *args: Positional args forwarded by the runtime.
                **kwargs: Keyword args forwarded by the runtime.

            Returns:
                Mock HTTP response for the streaming request.
            """
            streamed_chunks.extend(list(kwargs["content"]))
            return _make_http_response(200)

        mock_http_client.post.side_effect = _capture_streaming_post
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    elif client_type == "sftp":
        remote_file = MagicMock(name="sftp_remote_file")
        mock_sftp = MagicMock(name="sftp_client")
        mock_sftp.open.return_value = remote_file
        monkeypatch.setenv("MATRIX_SFTP_PASSWORD", "matrix-password")
        monkeypatch.setattr(
            paramiko.SFTPClient,
            "from_transport",
            MagicMock(return_value=mock_sftp),
        )
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    else:
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)

    assert_success_baseline(
        result,
        golden_path=MATRIX_ROOT / "golden" / "client" / "expected.csv",
        expected_target="stripe.product_feed",
        expected_content_type="text/csv",
        expected_input_count=count_fixture_records(fixture_path, input_format),
    )

    metadata = result.report.artifacts[0].metadata
    assert isinstance(metadata, PublishMetadata)
    assert metadata.archive_skipped is True

    if client_type == "noop":
        assert metadata.delivery_skipped is True
        assert metadata.delivery_status_code is None
        assert mock_http_client.post.call_count == 0
        return

    assert metadata.delivery_skipped is False

    if client_type == "http":
        assert metadata.delivery_status_code == 200
        assert mock_http_client.post.call_count == 1
        call = mock_http_client.post.call_args
        assert call.args[0] == "https://matrix.example.test/feed"
        assert call.kwargs["content"] == result.csv_payload
        assert call.kwargs["headers"] == {}
        return

    if client_type == "http_streaming":
        assert metadata.delivery_status_code == 200
        assert mock_http_client.post.call_count == 1
        call = mock_http_client.post.call_args
        assert call.args[0] == "https://matrix.example.test/feed"
        assert call.kwargs["headers"] == {}
        assert b"".join(streamed_chunks) == result.csv_payload
        return

    assert metadata.delivery_status_code == 0
    written_chunks = b"".join(call.args[0] for call in remote_file.write.call_args_list)
    assert written_chunks == result.csv_payload
    rename_args = mock_sftp.rename.call_args
    assert rename_args is not None
    assert rename_args.args[0].startswith("/feeds/matrix.csv.")
    assert rename_args.args[0].endswith(".tmp")
    assert rename_args.args[1] == "/feeds/matrix.csv"
