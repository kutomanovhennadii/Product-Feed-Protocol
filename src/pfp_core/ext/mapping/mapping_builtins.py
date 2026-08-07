"""Built-in mapping operations allowlist for Story 6b.3.

This module exposes a deterministic tuple of lazy builder callables that return
``MappingOpSpec`` instances. The canonical contract lives in
``mapping_contract.MAPPING_OP_REGISTRY``.
"""

from typing import Callable, Tuple

from pfp_core.ext.ext_types import MappingOpSpec
from pfp_core.ext.mapping.mapping_contract import MAPPING_OP_REGISTRY

MAPPING_BUILTINS: Tuple[Callable[[], MappingOpSpec], ...] = tuple(
    MAPPING_OP_REGISTRY.values()
)
