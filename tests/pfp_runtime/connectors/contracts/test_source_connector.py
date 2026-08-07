"""Tests for runtime source connector contract module."""

import collections.abc
from typing import Any, get_origin

import pfp_runtime.connectors.contracts.source_connector as source_connector
from pfp_runtime.connectors.contracts import SourceConnector, UnifiedItem


def test_source_connector_contract_exports_expected_symbols() -> None:
    """Contract module exposes SourceConnector and UnifiedItem symbols."""
    assert (
        SourceConnector.__module__
        == "pfp_runtime.connectors.contracts.source_connector"
    )
    assert hasattr(source_connector, "SourceConnector")
    assert hasattr(source_connector, "UnifiedItem")
    assert source_connector.SourceConnector is SourceConnector
    assert source_connector.UnifiedItem is UnifiedItem


def test_source_connector_is_concrete() -> None:
    """SourceConnector can be instantiated as concrete orchestrator."""
    abstract_type: type[Any] = SourceConnector
    instance = abstract_type(
        adapter=_StubAdapter(), mapper=_StubMapper(), producer=_StubProducer()
    )
    assert isinstance(instance, SourceConnector)


def test_unified_item_alias_is_mapping() -> None:
    """UnifiedItem alias is exposed and bound to Mapping[str, Any]."""
    assert get_origin(UnifiedItem) is collections.abc.Mapping


class _StubAdapter:
    format_name = "rows"

    def parse(self, raw_input: Any) -> Any:
        del raw_input
        return ()


class _StubMapper:
    def apply_stream(self, records: Any) -> Any:
        return records


class _StubProducer:
    def produce_stream(self, mapped_records: Any) -> Any:
        return mapped_records
