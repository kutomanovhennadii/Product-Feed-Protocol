"""Engine package exports for schema-driven compiler contracts."""

from typing import TYPE_CHECKING, List

from pfp_core.engine.mapping_executor import (
    MappingExecutionIssue,
    MappingExecutionResult,
    MappingExecutor,
)
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    CompiledSchema,
    FieldMappingPlan,
    FieldPresencePlan,
    MappingOpCall,
    MappingPlan,
    ValidationPlan,
    ValidationRulePlan,
    WriterSpec,
)
from pfp_core.engine.validation_executor import (
    ValidationExecutionResult,
    ValidationExecutor,
    ValidationReportItem,
)

if TYPE_CHECKING:
    from pfp_core.engine.compiler import SchemaCompiler

__all__: List[str] = [
    "CompiledSchema",
    "CompileDiagItem",
    "FieldMappingPlan",
    "FieldPresencePlan",
    "MappingExecutionIssue",
    "MappingExecutionResult",
    "MappingExecutor",
    "MappingOpCall",
    "MappingPlan",
    "SchemaCompiler",
    "ValidationExecutionResult",
    "ValidationExecutor",
    "ValidationPlan",
    "ValidationReportItem",
    "ValidationRulePlan",
    "WriterSpec",
]


def __getattr__(name: str):
    """Provide lazy access to heavy engine exports."""
    if name == "SchemaCompiler":
        from pfp_core.engine.compiler import SchemaCompiler

        return SchemaCompiler
    raise AttributeError(name)
