from __future__ import annotations

from typing import Dict, List

from pfp_core.ext.ext_types import MappingOpSpec, ValidationModuleSpec


class ExtCatalog:
    """Typed in-memory registry for mapping operations and validation modules."""

    def __init__(self) -> None:
        self._mapping_ops: Dict[str, MappingOpSpec] = {}
        self._validation_modules: Dict[str, ValidationModuleSpec] = {}

    def register_mapping_op(self, spec: MappingOpSpec) -> None:
        if spec.op_id in self._mapping_ops:
            raise ValueError(f"Mapping op already registered: {spec.op_id}")
        self._mapping_ops[spec.op_id] = spec

    def register_validation_module(self, spec: ValidationModuleSpec) -> None:
        if spec.module_id in self._validation_modules:
            raise ValueError(f"Validation module already registered: {spec.module_id}")
        self._validation_modules[spec.module_id] = spec

    def get_mapping_op(self, op_id: str) -> MappingOpSpec:
        return self._mapping_ops[op_id]

    def get_validation_module(self, module_id: str) -> ValidationModuleSpec:
        return self._validation_modules[module_id]

    def list_mapping_ops(self) -> List[str]:
        return sorted(self._mapping_ops)

    def list_validation_modules(self) -> List[str]:
        return sorted(self._validation_modules)
