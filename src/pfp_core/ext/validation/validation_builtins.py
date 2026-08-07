"""Built-in validation modules allowlist for Story 6b.3.

This module exposes a deterministic tuple of lazy builder callables that return
``ValidationModuleSpec`` instances. The canonical contract lives in
``validation_contract.VALIDATION_MODULE_REGISTRY``.
"""

from typing import Callable, Tuple

from pfp_core.ext.ext_types import ValidationModuleSpec
from pfp_core.ext.validation.validation_contract import VALIDATION_MODULE_REGISTRY

VALIDATION_BUILTINS: Tuple[Callable[[], ValidationModuleSpec], ...] = tuple(
    VALIDATION_MODULE_REGISTRY.values()
)
