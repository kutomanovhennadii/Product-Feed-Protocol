"""End-to-end A18 regression test.

Ensures the runtime pipeline never materialises the upstream items iterable.
A second iteration of the input proves materialisation occurred somewhere
between connector.extract and publisher.publish; the test fails in that case.
"""

from __future__ import annotations

import collections.abc
import logging as _stdlib_logging
from pathlib import Path
from typing import Any, Generic, Iterable, Iterator, List, Mapping, TypeVar

import pytest

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_runtime.publishing.publisher_builder import build_publisher

T = TypeVar("T")


class _LogPipelineStub:
    """Forwarding log pipeline stub that routes log_process to stdlib logging."""

    def log_process(
        self,
        level: int,
        module_name: str,
        message: str,
        *_args: Any,
        **kwargs: Any,
    ) -> None:
        """Forward a log record to the stdlib logger.

        Args:
            level: Standard logging level.
            module_name: Logger name to forward through.
            message: Log message body.
            *_args: Positional formatting args (ignored by the stub).
            **kwargs: Optional ``extra`` mapping passed through to stdlib.

        Returns:
            None.
        """
        extra = kwargs.get("extra")
        _stdlib_logging.getLogger(module_name).log(level, message, extra=extra)


class _ExtractResult:
    """Iterable extract result that preserves laziness of the wrapped items."""

    def __init__(self, items: Iterable[Mapping[str, Any]]) -> None:
        """Capture the wrapped items without materialising them.

        Args:
            items: Items iterable returned by the test connector.

        Returns:
            None.
        """
        self._items = items

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        """Yield wrapped items without copying or counting them.

        Returns:
            Iterator over the wrapped items.
        """
        return iter(self._items)


class _Connector:
    """Test connector that yields the configured items iterable from extract."""

    def __init__(self, items: Iterable[Mapping[str, Any]]) -> None:
        """Capture the items iterable passed to ``extract`` later.

        Args:
            items: Items iterable that the connector will expose.

        Returns:
            None.
        """
        self._items = items

    def extract(self, raw_input: Any) -> _ExtractResult:
        """Return the captured items wrapped in an iterable extract result.

        Args:
            raw_input: Raw input bytes (unused by the stub).

        Returns:
            Lazy extract result wrapping the captured items.
        """
        del raw_input
        return _ExtractResult(self._items)


class _OneShotIterable(Generic[T]):
    """Iterable that yields its underlying items exactly once.

    A second call to ``__iter__`` raises RuntimeError so any silent
    materialisation (``list(...)``, ``tuple(...)``, repeated ``for`` loops)
    in downstream code surfaces as a failed test.
    """

    def __init__(self, items: Iterable[T]) -> None:
        """Capture the underlying items and reset the consumed flag.

        Args:
            items: Source iterable to expose downstream exactly once.

        Returns:
            None.
        """
        self._items: List[T] = list(items)
        self._consumed: bool = False

    def __iter__(self) -> Iterator[T]:
        """Yield items on the first call; raise on any subsequent call.

        Returns:
            Iterator over the captured items on the first invocation.

        Raises:
            RuntimeError: If ``__iter__`` is called more than once.
        """
        if self._consumed:
            raise RuntimeError(
                "_OneShotIterable was iterated more than once - "
                "downstream code materialised the stream",
            )
        self._consumed = True
        return iter(self._items)


_PYTHON_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_FILE = (
    _PYTHON_ROOT / "schemas" / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
)
_POLICY_FILE = _PYTHON_ROOT / "config" / "policies.yaml"
_NOOP_OUTPUT_CONFIG = {
    "archive_type": "noop",
    "archive_config": str(_PYTHON_ROOT / "config" / "archive" / "noop.yaml"),
    "client_type": "noop",
    "client_config": str(_PYTHON_ROOT / "config" / "clients" / "noop.yaml"),
}


def _build_runner(items: Iterable[Mapping[str, Any]]) -> PipelineRunner:
    """Assemble a PipelineRunner with a real producer and a noop publisher.

    Args:
        items: Items iterable injected through the test connector. Passed
            through ``connector.extract`` straight into the runtime path
            without any local materialisation.

    Returns:
        Pipeline runner ready to execute against the supplied items.
    """
    log_pipeline = _LogPipelineStub()
    producer = prepare_artifact_producer_from_files(
        schema_file=str(_SCHEMA_FILE),
        policy_file=str(_POLICY_FILE),
        log_pipeline=log_pipeline,  # type: ignore[arg-type]
    )
    publisher = build_publisher(
        _NOOP_OUTPUT_CONFIG,
        log_pipeline=log_pipeline,  # type: ignore[arg-type]
    )
    manifest = PipelineManifest(
        ingestion=ConnectorManifest(
            connector=_Connector(items),  # type: ignore[arg-type]
            raw_input=b"fake-data",
        ),
        core=CoreManifest(producer=producer),
        publish=PublishManifest(publisher=publisher),
        observability=ObservabilityManifest(
            log_pipeline=log_pipeline,  # type: ignore[arg-type]
        ),
    )
    return PipelineRunner(manifest)


def test_one_shot_iterable_yields_items_exactly_once() -> None:
    """First iteration yields items; second iteration raises RuntimeError."""
    one_shot = _OneShotIterable([1, 2, 3])

    assert list(one_shot) == [1, 2, 3]

    with pytest.raises(RuntimeError, match="iterated more than once"):
        list(one_shot)


def test_one_shot_iterable_is_not_sequence() -> None:
    """_OneShotIterable must not be a Sequence so attach_input_counter stays lazy.

    attach_input_counter eagerly counts via len() when items are a Sequence;
    that branch would silently bypass the laziness invariant the e2e test
    relies on.
    """
    one_shot = _OneShotIterable([1])

    assert not isinstance(one_shot, collections.abc.Sequence)


def test_streaming_pipeline_does_not_materialise_input_items() -> None:
    """Upstream items iterable must be consumed exactly once across the runtime path.

    Wraps the input in _OneShotIterable; a second __iter__ would surface
    silent materialisation (list/tuple/double for-loop) as RuntimeError. The
    test passes only if no layer between connector and publisher re-iterates
    the source.
    """
    items: _OneShotIterable[Mapping[str, Any]] = _OneShotIterable(
        [
            {"item_id": "SKU-1", "title": "Widget"},
            {"item_id": "SKU-2", "title": "Gadget"},
        ]
    )
    runner = _build_runner(items)

    report = runner.run(b"fake-data")

    assert report.status == "SUCCESS"
    assert report.usage.input_items_count == 2
    assert report.usage.processed == 2
    assert len(report.artifacts) == 1
