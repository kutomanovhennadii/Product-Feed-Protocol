"""Tests for internal writers.impl package contract."""

import importlib

import pfp_core.writers.impl as impl_package


def test_impl_package_is_importable() -> None:
    """Import internal impl package marker without widening public facade."""

    assert impl_package.__name__ == "pfp_core.writers.impl"


def test_impl_package_does_not_reexport_concrete_classes() -> None:
    """Avoid wide re-export surface from internal impl package."""

    assert not hasattr(impl_package, "CSVWriter")
    assert not hasattr(impl_package, "JSONLWriter")


def test_impl_modules_are_importable_by_canonical_paths() -> None:
    """Resolve concrete writer modules via new canonical import paths."""

    csv_module = importlib.import_module("pfp_core.writers.impl.csv_writer")
    jsonl_module = importlib.import_module("pfp_core.writers.impl.jsonl_writer")

    assert hasattr(csv_module, "CSVWriter")
    assert hasattr(jsonl_module, "JSONLWriter")
