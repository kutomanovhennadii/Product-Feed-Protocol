"""Mapping op: resolve Stripe Product Tax Code from product namespace."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    ProducerContext,
    TypeSpec,
)

_FALSY_STRINGS = frozenset({"false", "no", "0"})


def _prepare_tax_code(
    args: Mapping[str, Any],
    context: ProducerContext | None,
) -> Mapping[str, Any]:
    """Enrich args at compile time with loaded lookup data.

    Called once by ``field_compiler`` during schema compilation.
    Reads infra-supplied lookup data from ``ProducerContext`` and pre-sorts keys
    for longest-prefix match.

    Args:
        args: Raw args from schema YAML.
        context: Optional compile-time producer context with loaded tax mapping.

    Returns:
        Enriched args dict with ``_lookup_data`` and ``_sorted_keys`` added.

    Raises:
        ValueError: If producer context or tax mapping payload is missing.
    """
    if context is None or context.tax_mapping is None:
        raise ValueError("map_tax_code requires tax_mapping in producer context")

    lookup_data = context.tax_mapping
    sorted_keys = tuple(sorted(lookup_data.get("mappings", {}), key=len, reverse=True))
    return {**args, "_lookup_data": lookup_data, "_sorted_keys": sorted_keys}


def _map_tax_code(value: Any, args: Mapping[str, Any]) -> Any:
    """Resolve Stripe PTC from product namespace dict.

    Priority chain:
    1. ``tax_code_override`` — merchant-supplied PTC passthrough.
    2. ``tax_category``      — Shopify category → longest-prefix lookup.
    3. ``taxable``           — boolean fallback (exempt vs default).

    Args:
        value: Product namespace dict, ``MISSING``, or ``None``.
        args: Must contain ``_lookup_data`` and ``_sorted_keys``
            (injected by ``_prepare_tax_code`` at compile time).

    Returns:
        Stripe PTC code string, ``MISSING``, or ``None``.

    Raises:
        TypeError: If *value* is not ``dict``, ``MISSING``, or ``None``.
    """
    if value is MISSING or value is None:
        return value

    if not isinstance(value, dict):
        raise TypeError(f"map_tax_code requires dict; got {type(value).__name__!r}")

    override_key = args.get("override_key", "tax_code_override")
    category_key = args.get("category_key", "tax_category")
    taxable_key = args.get("taxable_key", "taxable")

    lookup_data: dict[str, Any] = args["_lookup_data"]
    sorted_keys: tuple[str, ...] = args["_sorted_keys"]
    mappings: dict[str, str] = lookup_data.get("mappings", {})
    default_taxable: str = lookup_data.get("default_taxable", "txcd_99999999")
    default_exempt: str = lookup_data.get("default_exempt", "txcd_00000000")

    # Priority 1: merchant override
    override = value.get(override_key)
    if override and isinstance(override, str) and override.strip():
        return override.strip()

    # Priority 2: category lookup (longest-prefix match)
    category = value.get(category_key)
    if category and isinstance(category, str) and category.strip():
        cat = category.strip()
        for prefix in sorted_keys:
            if cat.startswith(prefix):
                return mappings[prefix]

    # Priority 3: taxable fallback
    taxable = value.get(taxable_key)
    if (
        taxable is False
        or (isinstance(taxable, str) and taxable.lower() in _FALSY_STRINGS)
        or taxable == 0
    ):
        return default_exempt

    return default_taxable


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``map_tax_code`` operation."""
    return MappingOpSpec(
        op_id="map_tax_code",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="override_key",
                    type_spec=TypeSpec("string", nullable=True, optional=True),
                    required=False,
                ),
                ParamFieldSpec(
                    name="category_key",
                    type_spec=TypeSpec("string", nullable=True, optional=True),
                    required=False,
                ),
                ParamFieldSpec(
                    name="taxable_key",
                    type_spec=TypeSpec("string", nullable=True, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_map_tax_code,
        prepare=_prepare_tax_code,
    )
