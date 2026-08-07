"""Tests for pfp_core.engine package exports."""

import pytest

import pfp_core.engine as engine_pkg
from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.engine.mapping_executor import MappingExecutor
from pfp_core.engine.validation_executor import ValidationExecutor


def test_engine_package_reexports_runtime_symbols() -> None:
    """Package root exposes canonical engine symbols including lazy compiler."""

    assert engine_pkg.MappingExecutor is MappingExecutor
    assert engine_pkg.ValidationExecutor is ValidationExecutor
    assert engine_pkg.SchemaCompiler is SchemaCompiler


def test_engine_package_rejects_unknown_attributes() -> None:
    """Unknown engine package exports raise AttributeError."""

    with pytest.raises(AttributeError, match="MissingEngineSymbol"):
        getattr(engine_pkg, "MissingEngineSymbol")
