"""Concrete runtime source connector orchestration."""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Mapping

from pfp_runtime.connectors.adapters.adapter_contract import FormatAdapter
from pfp_runtime.connectors.connector_mapping.connector_mapper import ConnectorMapper
from pfp_runtime.connectors.producers.product_producer import ProductProducer
from pfp_utils.logging import LogContext

UnifiedItem = Mapping[str, Any]


class SourceConnector:
    """Concrete connector orchestration pipeline for runtime phase."""

    adapter: FormatAdapter
    mapper: ConnectorMapper
    producer: ProductProducer

    def __init__(
        self,
        adapter: FormatAdapter,
        mapper: ConnectorMapper,
        producer: ProductProducer,
    ) -> None:
        self.adapter = adapter
        self.mapper = mapper
        self.producer = producer

    def extract(self, raw_input: Any) -> Iterable[UnifiedItem]:
        """Extract streaming dict records from raw input."""
        with LogContext(stage="runtime", component="source_connector"):
            records = self.adapter.parse(raw_input)
            mapped = self.mapper.apply_stream(records)
            return _StreamingResult(self.producer.produce_stream(mapped))


class _StreamingResult(Iterable[UnifiedItem]):
    """Wrapper preserving iterable contract and lazy evaluation."""

    def __init__(self, source: Iterable[UnifiedItem]) -> None:
        self._source = source

    def __iter__(self) -> Iterator[UnifiedItem]:
        yield from self._source
