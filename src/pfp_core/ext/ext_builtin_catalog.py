from __future__ import annotations

from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.mapping.mapping_builtins import MAPPING_BUILTINS
from pfp_core.ext.validation.validation_builtins import VALIDATION_BUILTINS


def build_builtin_catalog() -> ExtCatalog:
    """Build Story 6b.3 minimal builtin catalog.

    The minimum includes mapping conversion and formatting operations,
    presence-semantics helpers, and validation modules for
    required/type/enum/range checks.
    """

    catalog = ExtCatalog()
    for build_mapping_spec in MAPPING_BUILTINS:
        catalog.register_mapping_op(build_mapping_spec())
    for build_validation_spec in VALIDATION_BUILTINS:
        catalog.register_validation_module(build_validation_spec())
    return catalog
