"""Protocol contract for connector format adapters."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Protocol

from pfp_utils.logging import LogPipeline


class AdapterFormatError(ValueError):
    """Raised when adapter cannot parse the input format (e.g. limit overflow, decoding error)."""

    pass


class FormatAdapter(Protocol):
    """Parses an input format stream into raw records in memory.

    This interface is responsible solely for translating bytes/strings/iterables
    into un-typed dictionaries.
    It has no knowledge of mapping logic and no knowledge of RawProduct.
    """

    format_name: str
    constants: Mapping[str, Any]

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        """Initialize adapter with format constants.

        Args:
            constants: Mapping of constants provided by the registry (e.g. limit constraints).
            log_pipeline: Runtime log pipeline propagated from manifest assembly.
        """
        ...

    def parse(self, raw_input: Any) -> Iterable[Mapping[str, Any]]:
        """Parse raw input payload and yield mapping records.

        Input: raw_input (string, byte stream, ready iterator - depends on format).
        Output: Generator of Mapping[str, Any] representing a single record.
        """
        ...
