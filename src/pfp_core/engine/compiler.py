"""Schema compiler orchestration: SchemaDoc -> typed execution plans (Story 6b.4)."""

from __future__ import annotations

from typing import List, Mapping, Optional, cast

from pfp_core.engine.compiler_checks import check_presence_required_contradictions
from pfp_core.engine.mapping_compiler import compile_mapping
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    CompiledSchema,
    sort_compile_diagnostics,
)
from pfp_core.engine.validation_compiler import compile_validation
from pfp_core.engine.writer_compiler import compile_writer_spec
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import ProducerContext
from pfp_core.schema.schema_types import SchemaDoc


class SchemaCompiler:
    """Compile schema documents into deterministic plans and diagnostics.

    Args:
        catalog: Ext-modules catalog used for op and module resolution.

    Returns:
        None.
    """

    def __init__(self, *, catalog: ExtCatalog) -> None:
        """Initialize compiler with ext catalog dependency.

        Args:
            catalog: Ext-modules catalog used for op and module resolution.

        Returns:
            None.
        """

        self._catalog = catalog

    def compile(
        self,
        schema_doc: SchemaDoc,
        *,
        context: Optional[ProducerContext] = None,
    ) -> CompiledSchema:
        """Compile schema-doc into `CompiledSchema` without schema exceptions.

        Args:
            schema_doc: Schema document to compile.
            context: Optional compile-time context reserved for infra-supplied data.

        Returns:
            Compiled schema with plans, diagnostics, and validity flag.
        """

        diagnostics: List[CompileDiagItem] = []
        writer_spec = compile_writer_spec(schema_doc, diagnostics)
        (
            mapping_plan,
            field_final_types,
            field_presence,
        ) = compile_mapping(
            schema_doc=schema_doc,
            catalog=self._catalog,
            diagnostics=diagnostics,
            context=context,
        )
        (
            validation_plan,
            required_by_profile_sources,
        ) = compile_validation(
            schema_doc=schema_doc,
            known_fields=set(mapping_plan.fields.keys()),
            field_final_types=field_final_types,
            diagnostics=diagnostics,
            catalog=self._catalog,
        )
        check_presence_required_contradictions(
            field_presence=field_presence,
            required_by_profile_sources=required_by_profile_sources,
            diagnostics=diagnostics,
        )

        ordered_diagnostics = sort_compile_diagnostics(diagnostics)
        is_valid = not any(item.severity == "ERROR" for item in ordered_diagnostics)
        header = cast(Mapping[str, object], schema_doc["header"])
        artifact_profile = str(header["artifact_profile"])
        return CompiledSchema(
            artifact_profile=artifact_profile,
            validation_plan=validation_plan,
            mapping_plan=mapping_plan,
            writer_spec=writer_spec,
            diagnostics=ordered_diagnostics,
            is_valid=is_valid,
        )
