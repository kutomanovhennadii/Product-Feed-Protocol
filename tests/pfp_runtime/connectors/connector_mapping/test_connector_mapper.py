"""Tests for ConnectorMapper.apply_stream."""

import logging
import types
from typing import Any, List, Mapping

import pytest

from pfp_runtime.connectors.connector_mapping.connector_mapper import ConnectorMapper
from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorFieldMapping,
    ConnectorMappingConfig,
    ConnectorMappingValidationError,
)


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


def _make_config(
    mappings: List[ConnectorFieldMapping],
    continue_on_error: bool = True,
) -> ConnectorMappingConfig:
    """Build a ConnectorMappingConfig from a list of field mappings."""
    return ConnectorMappingConfig(
        mappings=tuple(mappings),
        continue_on_error=continue_on_error,
    )


def _make_mapper(
    mappings: List[ConnectorFieldMapping],
    continue_on_error: bool = True,
) -> ConnectorMapper:
    """Build a ConnectorMapper directly from field mapping specs."""
    return ConnectorMapper(
        _make_config(mappings, continue_on_error),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_apply_stream_renames_keys_and_drops_unmapped() -> None:
    """Output keys are UM-space targets; unmapped source keys are silently dropped."""
    mapper = _make_mapper(
        [
            ConnectorFieldMapping(source="sku", target="product.item_id"),
            ConnectorFieldMapping(source="name", target="product.title"),
        ]
    )
    records: List[Mapping[str, Any]] = [
        {"sku": "ABC", "name": "Widget", "extra_col": "ignored"},
    ]

    result = list(mapper.apply_stream(records))

    assert len(result) == 1
    assert result[0] == {"product.item_id": "ABC", "product.title": "Widget"}
    assert "extra_col" not in result[0]


def test_apply_stream_values_passed_unchanged() -> None:
    """Values are copied into the output without any modification."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="price", target="offer.price.amount")]
    )
    raw_value = " 9.99 "  # leading/trailing whitespace must be preserved

    result = list(mapper.apply_stream([{"price": raw_value}]))

    assert result[0]["offer.price.amount"] == raw_value


def test_apply_stream_is_lazy_generator() -> None:
    """apply_stream returns a generator, not a materialised list."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id")]
    )

    result = mapper.apply_stream([{"sku": "X"}])

    assert isinstance(result, types.GeneratorType)


def test_apply_stream_empty_input() -> None:
    """Empty input stream yields no records and raises no exceptions."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id")]
    )

    result = list(mapper.apply_stream([]))

    assert result == []


def test_apply_stream_multiple_records() -> None:
    """All records in the stream are mapped correctly."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id")]
    )
    records: List[Mapping[str, Any]] = [{"sku": "A"}, {"sku": "B"}, {"sku": "C"}]

    result = list(mapper.apply_stream(records))

    assert [r["product.item_id"] for r in result] == ["A", "B", "C"]


def test_apply_stream_source_equals_target() -> None:
    """Trivial case where source key and target key are the same string."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="product.item_id", target="product.item_id")]
    )

    result = list(mapper.apply_stream([{"product.item_id": "X"}]))

    assert result == [{"product.item_id": "X"}]


# ---------------------------------------------------------------------------
# Optional field absent
# ---------------------------------------------------------------------------


def test_apply_stream_optional_field_absent_record_not_skipped() -> None:
    """Record with a missing optional field is still yielded, just without that key."""
    mapper = _make_mapper(
        [
            ConnectorFieldMapping(source="sku", target="product.item_id"),
            ConnectorFieldMapping(source="brand", target="product.brand"),  # optional
        ]
    )

    result = list(mapper.apply_stream([{"sku": "ABC"}]))

    assert len(result) == 1
    assert "product.item_id" in result[0]
    assert "product.brand" not in result[0]


def test_apply_stream_extra_keys_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Unmapped source keys are dropped silently — no WARNING is emitted."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id")]
    )
    with caplog.at_level(logging.WARNING):
        list(mapper.apply_stream([{"sku": "X", "noise1": "a", "noise2": "b"}]))

    assert caplog.records == []


# ---------------------------------------------------------------------------
# Required field absent — continue_on_error=True
# ---------------------------------------------------------------------------


def test_apply_stream_required_missing_record_skipped() -> None:
    """Record missing a required field is not yielded when continue_on_error=True."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)]
    )

    result = list(mapper.apply_stream([{"other_key": "value"}]))

    assert result == []


def test_apply_stream_required_missing_warning_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A WARNING is logged when a required field is missing and continue_on_error=True."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)]
    )
    with caplog.at_level(logging.WARNING):
        list(mapper.apply_stream([{"other_key": "value"}]))

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "sku" in caplog.records[0].message or "sku" in str(
        caplog.records[0].__dict__
    )


def test_apply_stream_partial_skip_middle_record() -> None:
    """Three records: middle one missing required field is skipped; first and last pass."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)]
    )
    records: List[Mapping[str, Any]] = [
        {"sku": "A"},
        {"other": "no_sku"},
        {"sku": "C"},
    ]

    result = list(mapper.apply_stream(records))

    assert len(result) == 2
    assert result[0]["product.item_id"] == "A"
    assert result[1]["product.item_id"] == "C"


# ---------------------------------------------------------------------------
# Required field absent — continue_on_error=False
# ---------------------------------------------------------------------------


def test_apply_stream_required_missing_raises_when_strict() -> None:
    """ConnectorMappingValidationError is raised when required field is absent and continue_on_error=False."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)],
        continue_on_error=False,
    )

    with pytest.raises(ConnectorMappingValidationError):
        list(mapper.apply_stream([{"other_key": "value"}]))


def test_apply_stream_strict_raises_immediately() -> None:
    """With continue_on_error=False the exception is raised on the first bad record."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)],
        continue_on_error=False,
    )
    records: List[Mapping[str, Any]] = [
        {"sku": "ok"},
        {"missing": "sku"},  # triggers raise
        {"sku": "unreachable"},
    ]

    with pytest.raises(ConnectorMappingValidationError):
        list(mapper.apply_stream(records))


# ---------------------------------------------------------------------------
# Output order / determinism
# ---------------------------------------------------------------------------


def test_apply_stream_output_key_order_matches_mapping_order() -> None:
    """Output dict key order matches the order of mappings in the config."""
    mapper = _make_mapper(
        [
            ConnectorFieldMapping(source="c", target="z_key"),
            ConnectorFieldMapping(source="a", target="a_key"),
            ConnectorFieldMapping(source="b", target="m_key"),
        ]
    )

    result = list(mapper.apply_stream([{"a": "1", "b": "2", "c": "3"}]))

    assert list(result[0].keys()) == ["z_key", "a_key", "m_key"]


# ---------------------------------------------------------------------------
# Stateless — independent calls
# ---------------------------------------------------------------------------


def test_apply_stream_stateless_independent_calls() -> None:
    """Two consecutive apply_stream calls on the same mapper are fully independent."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id")]
    )

    result_a = list(mapper.apply_stream([{"sku": "A"}]))
    result_b = list(mapper.apply_stream([{"sku": "B"}]))

    assert result_a[0]["product.item_id"] == "A"
    assert result_b[0]["product.item_id"] == "B"


# ---------------------------------------------------------------------------
# Security Rule
# ---------------------------------------------------------------------------


def test_apply_stream_warning_contains_no_raw_cell_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WARNING log must not contain raw cell values — only key names."""
    mapper = _make_mapper(
        [ConnectorFieldMapping(source="sku", target="product.item_id", required=True)]
    )
    sentinel = "SECRET_CELL_VALUE"

    with caplog.at_level(logging.WARNING):
        # Record has other keys with sentinel value, but sku is missing
        list(mapper.apply_stream([{"other_field": sentinel}]))

    full_log = " ".join(r.getMessage() for r in caplog.records)
    assert sentinel not in full_log
