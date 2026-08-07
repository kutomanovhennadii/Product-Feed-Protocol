"""Compilation of schema output section into `WriterSpec`."""

from __future__ import annotations

from types import MappingProxyType
from typing import List, Mapping, cast

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.plan_types import CompileDiagItem, WriterSpec
from pfp_core.schema.schema_types import SchemaDoc


def compile_writer_spec(
    schema_doc: SchemaDoc,
    diagnostics: List[CompileDiagItem],
) -> WriterSpec:
    """Compile `output` section into `WriterSpec`.

    Args:
        schema_doc: Source schema document.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Writer specification object.
    """

    output = as_mapping(schema_doc.get("output"))
    if output is None:
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output",
            message="output must be an object.",
        )
        return WriterSpec(
            writer_id="",
            artifact_content_type="",
            artifact_file_extension="",
            writer_config=MappingProxyType({}),
        )

    writer_id = output.get("writer_id")
    if not isinstance(writer_id, str):
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output.writer_id",
            message="output.writer_id must be a string.",
        )
        writer_id = ""

    writer_config_obj = output.get("writer_config", {})
    writer_config = as_mapping(writer_config_obj)
    if writer_config is None:
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output.writer_config",
            message="output.writer_config must be an object.",
        )
        writer_config = {}

    artifact = as_mapping(output.get("artifact"))
    if artifact is None:
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output.artifact",
            message="output.artifact must be an object.",
        )
        artifact = {}

    content_type = artifact.get("content_type")
    if not isinstance(content_type, str):
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output.artifact.content_type",
            message="output.artifact.content_type must be a string.",
        )
        content_type = ""

    file_extension = artifact.get("file_extension")
    if not isinstance(file_extension, str):
        add_error(
            diagnostics,
            code="COMPILER_OUTPUT_INVALID",
            path="output.artifact.file_extension",
            message="output.artifact.file_extension must be a string.",
        )
        file_extension = ""

    return WriterSpec(
        writer_id=writer_id,
        artifact_content_type=content_type,
        artifact_file_extension=file_extension,
        writer_config=cast(
            Mapping[str, object],
            MappingProxyType(dict(cast(Mapping[str, object], writer_config))),
        ),
    )
