"""Feed usage accounting models for pipeline runtime diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Mapping, Sequence


@dataclass(frozen=True)
class FeedUsage:
    """Usage accounting snapshot for a single pipeline run.

    Immutable snapshot created by FeedUsageCollector.build().
    Stored in ExecutionReport and persisted as business usage data.

    Args:
        input_items_count: Number of input items seen by the pipeline.
        artifacts_count: Number of artifacts produced during the run.
        processed: Number of items processed successfully.
        dropped: Number of items dropped during processing.
        errors: Number of item or stage errors recorded for the run.
        diagnostics_count_by_severity: Diagnostic counters grouped by severity.
    """

    input_items_count: int = 0
    artifacts_count: int = 0
    processed: int = 0
    dropped: int = 0
    errors: int = 0
    diagnostics_count_by_severity: Mapping[str, int] = field(
        default_factory=lambda: {"ERROR": 0, "WARN": 0, "INFO": 0}
    )


class FeedUsageCollector:
    """Mutable collector that accumulates feed usage counters for one run.

    Created during init-phase and reset at the start of each runtime cycle.

    Returns:
        FeedUsage snapshots through build().
    """

    def __init__(self) -> None:
        """Initialize usage counters with zero values.

        Returns:
            None.
        """
        self._input: int = 0
        self._processed: int = 0
        self._dropped: int = 0
        self._errors: int = 0
        self._artifacts: int = 0
        self._diagnostics: Dict[str, int] = {"ERROR": 0, "WARN": 0, "INFO": 0}

    def reset(self) -> None:
        """Reset all counters to zero for the next pipeline run.

        Returns:
            None.
        """
        self._input = 0
        self._processed = 0
        self._dropped = 0
        self._errors = 0
        self._artifacts = 0
        self._diagnostics = {"ERROR": 0, "WARN": 0, "INFO": 0}

    def inc_input(self, count: int = 1) -> None:
        """Increment the input items counter.

        Args:
            count: Number of input items to add.

        Returns:
            None.
        """
        self._input += count

    def attach_input_counter(self, items: Iterable[Any]) -> Iterable[Any]:
        """Return a pass-through iterable that accounts for input items.

        Args:
            items: Input items to expose downstream.

        Returns:
            Original sequence for eager counting, or a lazy wrapper iterable
            that increments the counter as items are consumed.
        """
        if isinstance(items, Sequence):
            self.inc_input(len(items))
            return items
        return self._lazy_input_counter(items)

    def _lazy_input_counter(self, items: Iterable[Any]) -> Iterator[Any]:
        """Yield items lazily while incrementing the input counter.

        Args:
            items: Source iterable to proxy.

        Returns:
            Iterator over the original items with per-item counter updates.
        """
        for item in items:
            self.inc_input()
            yield item

    def inc_processed(self, count: int = 1) -> None:
        """Increment the processed items counter.

        Args:
            count: Number of processed items to add.

        Returns:
            None.
        """
        self._processed += count

    def inc_dropped(self, count: int = 1) -> None:
        """Increment the dropped items counter.

        Args:
            count: Number of dropped items to add.

        Returns:
            None.
        """
        self._dropped += count

    def inc_error(self, count: int = 1) -> None:
        """Increment the error counter.

        Args:
            count: Number of errors to add.

        Returns:
            None.
        """
        self._errors += count

    def inc_artifacts(self, count: int = 1) -> None:
        """Increment the artifacts counter.

        Args:
            count: Number of artifacts to add.

        Returns:
            None.
        """
        self._artifacts += count

    def inc_diagnostic(self, severity: str) -> None:
        """Increment a diagnostic counter for the given severity.

        Args:
            severity: Diagnostic severity token.

        Returns:
            None.
        """
        key = severity.upper()
        self._diagnostics[key] = self._diagnostics.get(key, 0) + 1

    def build(self) -> FeedUsage:
        """Build an immutable usage snapshot from current counters.

        Returns:
            Frozen FeedUsage snapshot with current collector values.
        """
        return FeedUsage(
            input_items_count=self._input,
            artifacts_count=self._artifacts,
            processed=self._processed,
            dropped=self._dropped,
            errors=self._errors,
            diagnostics_count_by_severity=dict(self._diagnostics),
        )


__all__ = ["FeedUsage", "FeedUsageCollector"]
