"""Tests for publisher contract errors."""

from pfp_runtime.publishing.contracts.publisher_errors import PublisherBuildError


def test_publisher_build_error_is_value_error() -> None:
    """Publisher assembly errors stay compatible with value-error handling."""

    error = PublisherBuildError("broken publisher config")

    assert isinstance(error, ValueError)
    assert str(error) == "broken publisher config"
