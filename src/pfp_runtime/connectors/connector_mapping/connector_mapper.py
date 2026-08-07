"""Runtime key-routing mapper for connector mapping.

Compiles ConnectorMappingConfig into fast lookup structures once on init,
then applies them lazily to each record in apply_stream.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorMappingConfig,
    ConnectorMappingValidationError,
)
from pfp_utils.logging import LogPipeline
from pfp_utils.sanitization import sanitize_text


class ConnectorMapper:
    """Stream mapper that routes source keys to UM-space target keys.

    Compiles ConnectorMappingConfig into fast lookup structures on init,
    then applies them lazily to each record in apply_stream. Values are
    passed through unchanged — type coercion is the responsibility of the
    core pipeline.

    Attributes:
        config: Original validated mapping config (stored for reference).
    """

    def __init__(
        self,
        config: ConnectorMappingConfig,
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Compile mapping config into fast lookup structures.

        Builds ``_source_to_target`` and ``_required_sources`` once so that
        apply_stream performs only O(1) lookups per field per record.

        Args:
            config: Validated ConnectorMappingConfig from connector_mapping_validator.
        """
        self.config = config
        self._source_to_target: Dict[str, str] = {
            m.source: m.target for m in config.mappings
        }
        self._required_sources: FrozenSet[str] = frozenset(
            m.source for m in config.mappings if m.required
        )
        self._continue_on_error: bool = config.continue_on_error
        self._log_pipeline = log_pipeline

    def apply_stream(
        self,
        records: Iterable[Mapping[str, Any]],
    ) -> Iterable[Mapping[str, Any]]:
        """Apply mapping rules to a stream of raw source records.

        Iterates over the compiled mapping (O(n_mappings) per record) with
        O(1) lookups into each record. Unmapped source keys are silently
        dropped. Values are passed through unchanged.

        Args:
            records: Iterable of raw dicts from a FormatAdapter, where keys
                are source field names (e.g. CSV column names).

        Yields:
            Dicts with UM-space keys (e.g. ``"product.item_id"``).

        Raises:
            ConnectorMappingValidationError: If a required field is absent and
                continue_on_error is False.
        """
        for record in records:
            output: Dict[str, Any] = {}
            skip = False

            for source_key, target_key in self._source_to_target.items():
                if source_key in record:
                    output[target_key] = record[source_key]
                elif source_key in self._required_sources:
                    if self._continue_on_error:
                        self._log_pipeline.log_process(
                            logging.WARNING,
                            __name__,
                            "required source field missing — record skipped",
                            extra={
                                "source_key": sanitize_text(source_key),
                                "target_key": target_key,
                            },
                        )
                        skip = True
                        break
                    else:
                        raise ConnectorMappingValidationError(
                            "required field missing: '" + source_key + "'"
                        )
                # absent optional field — not added to output, no warning

            if not skip:
                yield output


__all__: List[str] = ["ConnectorMapper"]
