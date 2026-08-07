"""Mirror unit tests for pfp_utils.diagnostics.feed_usage."""

from typing import Iterator

from pfp_utils.diagnostics.feed_usage import FeedUsage, FeedUsageCollector


def test_feed_usage_defaults_are_zeroed() -> None:
    """Expose zero-valued defaults for a fresh immutable usage snapshot."""
    usage = FeedUsage()

    assert usage.input_items_count == 0
    assert usage.artifacts_count == 0
    assert usage.processed == 0
    assert usage.dropped == 0
    assert usage.errors == 0
    assert usage.diagnostics_count_by_severity == {
        "ERROR": 0,
        "WARN": 0,
        "INFO": 0,
    }


def test_feed_usage_collector_reset_clears_all_counters() -> None:
    """Reset the collector back to zero values after counters were updated."""
    collector = FeedUsageCollector()
    collector.inc_input(2)
    collector.inc_processed(1)
    collector.inc_dropped(3)
    collector.inc_error(4)
    collector.inc_artifacts(5)
    collector.inc_diagnostic("error")

    collector.reset()
    usage = collector.build()

    assert usage == FeedUsage()


def test_feed_usage_collector_builds_snapshot_from_all_increment_methods() -> None:
    """Accumulate counters through all public increment methods into a snapshot."""
    collector = FeedUsageCollector()
    collector.inc_input(10)
    collector.inc_processed(7)
    collector.inc_dropped(2)
    collector.inc_error(1)
    collector.inc_artifacts(4)
    collector.inc_diagnostic("error")
    collector.inc_diagnostic("warn")
    collector.inc_diagnostic("info")
    collector.inc_diagnostic("custom")

    usage = collector.build()

    assert usage.input_items_count == 10
    assert usage.processed == 7
    assert usage.dropped == 2
    assert usage.errors == 1
    assert usage.artifacts_count == 4
    assert usage.diagnostics_count_by_severity == {
        "ERROR": 1,
        "WARN": 1,
        "INFO": 1,
        "CUSTOM": 1,
    }


def test_feed_usage_collector_build_returns_immutable_snapshot_copy() -> None:
    """Return a snapshot that is not mutated by later collector updates."""
    collector = FeedUsageCollector()
    collector.inc_processed(2)

    first_snapshot = collector.build()

    collector.inc_processed(3)
    collector.inc_diagnostic("error")
    second_snapshot = collector.build()

    assert first_snapshot.processed == 2
    assert first_snapshot.diagnostics_count_by_severity == {
        "ERROR": 0,
        "WARN": 0,
        "INFO": 0,
    }
    assert second_snapshot.processed == 5
    assert second_snapshot.diagnostics_count_by_severity["ERROR"] == 1


def test_feed_usage_collector_build_after_reset_returns_zero_snapshot() -> None:
    """Build a clean zero snapshot after collector state was reset."""
    collector = FeedUsageCollector()
    collector.inc_input(1)
    collector.inc_diagnostic("warn")

    collector.reset()

    assert collector.build() == FeedUsage()


def test_attach_input_counter_sequence_eager() -> None:
    """Count a sequence eagerly and return the original sequence object."""
    collector = FeedUsageCollector()
    items = [{"item_id": "SKU-1"}, {"item_id": "SKU-2"}]

    attached = collector.attach_input_counter(items)

    assert attached is items
    assert collector.build().input_items_count == 2


def test_attach_input_counter_iterable_lazy() -> None:
    """Count a non-sequence iterable only when items are consumed."""
    collector = FeedUsageCollector()

    def source() -> Iterator[dict[str, str]]:
        yield {"item_id": "SKU-1"}
        yield {"item_id": "SKU-2"}

    attached = iter(collector.attach_input_counter(source()))

    assert collector.build().input_items_count == 0
    assert next(attached) == {"item_id": "SKU-1"}
    assert collector.build().input_items_count == 1
    assert next(attached) == {"item_id": "SKU-2"}
    assert collector.build().input_items_count == 2


def test_attach_input_counter_returns_passthrough_items() -> None:
    """Preserve item values while wrapping a lazy input iterable."""
    collector = FeedUsageCollector()

    def source() -> Iterator[int]:
        yield 1
        yield 2
        yield 3

    attached = collector.attach_input_counter(source())

    assert list(attached) == [1, 2, 3]
    assert collector.build().input_items_count == 3
