"""Registers built-in writer factories (csv/jsonl).

This module is the only place allowed to import concrete writer implementations.
"""

from pfp_core.writers.impl.csv_writer import CSVWriter
from pfp_core.writers.impl.jsonl_writer import JSONLWriter
from pfp_core.writers.writer_registry import WriterRegistry


def build_default_writer_registry() -> WriterRegistry:
    """Build registry with default CSV and JSONL writer factories.

    Returns:
        Writer registry pre-populated with built-in writer factories.
    """

    registry = WriterRegistry()
    registry.register("csv", lambda config, meta: CSVWriter(config, meta))
    registry.register("jsonl", lambda config, meta: JSONLWriter(config, meta))
    return registry
