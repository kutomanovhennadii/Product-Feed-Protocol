from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence


@dataclass(frozen=True)
class SchemaRef:
    """Reference to a schema document identity.

    Args:
        protocol_id: Canonical protocol identifier.
        schema_version: Schema version in string form.
    """

    protocol_id: str
    schema_version: str


SchemaDoc = Mapping[str, Any]


@dataclass(frozen=True)
class SchemaErrorItem:
    """Structured schema validation error item.

    Args:
        code: Stable machine-readable error code.
        path: Dot-path of a failing field or "$" for root-level issues.
        message: Deterministic human-readable message.
    """

    code: str
    path: str
    message: str


def sort_schema_error_items(items: Iterable[SchemaErrorItem]) -> list[SchemaErrorItem]:
    """Sort schema error items deterministically.

    Args:
        items: Error items to sort.

    Returns:
        A list sorted by ``(code, path, message)``.
    """

    return sorted(items, key=lambda item: (item.code, item.path, item.message))


class SchemaFormatError(Exception):
    """Exception for schema format and schema contract violations."""

    def __init__(
        self,
        items: Sequence[SchemaErrorItem],
        *,
        schema_ref: Optional[SchemaRef] = None,
        source: Optional[str] = None,
    ) -> None:
        """Initialize the exception with deterministic error ordering.

        Args:
            items: Raw collection of schema error items.
            schema_ref: Optional schema reference context.
            source: Optional source hint (for example filename or embedded id).
        """

        self.items = sort_schema_error_items(items)
        self.schema_ref = schema_ref
        self.source = source
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Build a compact deterministic exception message.

        Returns:
            A formatted message built from sorted error items.
        """

        if not self.items:
            return "Schema format error"
        details = "; ".join(
            f"{item.code} at {item.path}: {item.message}" for item in self.items
        )
        return f"Schema format error: {details}"


class SchemaNotFoundError(LookupError):
    """Exception raised when schema document is not registered in the registry."""

    def __init__(self, schema_ref: SchemaRef) -> None:
        self.schema_ref = schema_ref
        super().__init__(
            "Schema is not registered for "
            f"protocol_id='{schema_ref.protocol_id}', schema_version='{schema_ref.schema_version}'."
        )


SchemaError = SchemaErrorItem
SchemaRegistryError = SchemaFormatError
SchemaValidationError = SchemaFormatError
SchemaVersionError = SchemaFormatError
