"""Last-mile record builder: converts mapped UM-key records into nested dict records."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pfp_utils.logging import LogPipeline


class ProductProducer:
    """Convert mapped UM-key records into nested dict record stream.

    Stateless: no constructor arguments, safe to reuse across calls.
    """

    def __init__(self, *, log_pipeline: LogPipeline) -> None:
        self._log_pipeline = log_pipeline

    def produce_stream(
        self,
        mapped_records: Iterable[Mapping[str, Any]],
    ) -> Iterable[Mapping[str, Any]]:
        """Yield a nested dict record for each valid mapped record.

        The only required UM field at this stage is ``product.item_id``.
        Other required constraints must be enforced by schema-driven validation.

        Args:
            mapped_records: Iterable of dicts with dot-path UM keys
                (e.g. ``"product.item_id"``, ``"offer.price.amount"``).

        Yields:
            Nested dict records.
        """
        for record in mapped_records:
            nested = _unflatten(record)
            built = _build_record(nested)
            if built is None:
                self._log_pipeline.log_process(
                    logging.WARNING,
                    __name__,
                    "required UM field missing (product.item_id) — record skipped",
                    extra={"top_level_keys": list(nested.keys())},
                )
                continue
            yield built


def _unflatten(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a flat dot-path record into a nested dict.

    Example::

        {"product.item_id": "X1", "offer.price.amount": "10"}
        → {"product": {"item_id": "X1"}, "offer": {"price": {"amount": "10"}}}
    """
    result: Dict[str, Any] = {}
    for dot_path, value in record.items():
        segments = dot_path.split(".")
        current = result
        for segment in segments[:-1]:
            if segment not in current or not isinstance(current[segment], dict):
                current[segment] = {}
            current = current[segment]
        current[segments[-1]] = value
    return result


def _build_record(nested: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a nested dict record from an unflattened UM-key dict.

    Returns None if the record cannot be identified (missing ``product.item_id``).
    """
    product_data = nested.get("product")
    if not isinstance(product_data, dict):
        return None

    item_id = _str_or_none(product_data.get("item_id"))
    if not item_id:
        return None

    product_data["item_id"] = item_id
    return nested


def _str_or_none(value: Any) -> Optional[str]:
    """Return stripped string if non-empty, else None."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


__all__: List[str] = ["ProductProducer"]
