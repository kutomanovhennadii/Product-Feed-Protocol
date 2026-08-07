"""Adapter implementations used by connector build dispatch."""

from .adapter_contract import AdapterFormatError, FormatAdapter
from .csv_adapter import CsvAdapter
from .json_adapter import JsonAdapter
from .jsonl_adapter import JsonlAdapter
from .rows_adapter import RowsAdapter
from .streaming_csv_adapter import StreamingCsvAdapter
from .streaming_json_adapter import StreamingJsonAdapter
from .streaming_jsonl_adapter import StreamingJsonlAdapter

__all__ = [
    "AdapterFormatError",
    "CsvAdapter",
    "FormatAdapter",
    "JsonAdapter",
    "JsonlAdapter",
    "RowsAdapter",
    "StreamingCsvAdapter",
    "StreamingJsonAdapter",
    "StreamingJsonlAdapter",
]
