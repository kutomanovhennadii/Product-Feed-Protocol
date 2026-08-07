"""Tests for shell factory — verifies manifest-pipeline wiring is in effect."""

from __future__ import annotations

import inspect

import pytest

from pfp_runtime.shell.factory import FactoryConfigError, PFPFactory, get_pfp_factory


def test_factory_init_takes_no_arguments() -> None:
    """PFPFactory.__init__ exposes no user-facing configuration parameters."""
    sig = inspect.signature(PFPFactory.__init__)
    params = set(sig.parameters.keys()) - {"self"}
    assert not params
    assert "infra" not in params, "infra= bypass must not exist"


def test_get_pfp_factory_takes_no_arguments() -> None:
    """get_pfp_factory exposes no user-facing configuration parameters."""
    sig = inspect.signature(get_pfp_factory)
    params = set(sig.parameters.keys())
    assert not params
    assert "infra" not in params, "infra= bypass must not exist"


def test_build_worker_requires_infra_path_keyword_only() -> None:
    """PFPFactory.build_worker requires keyword-only infra_path and no infra parameter."""
    sig = inspect.signature(PFPFactory.build_worker)
    infra_param = sig.parameters["infra_path"]

    assert infra_param.kind is inspect.Parameter.KEYWORD_ONLY
    assert "infra" not in sig.parameters, "infra= bypass must not exist"


def test_build_worker_rejects_empty_infra_path() -> None:
    """build_worker raises FactoryConfigError for empty or blank infra_path."""
    with pytest.raises(FactoryConfigError, match="non-empty"):
        PFPFactory().build_worker(infra_path="")

    with pytest.raises(FactoryConfigError, match="non-empty"):
        PFPFactory().build_worker(infra_path="   ")


def test_build_worker_rejects_non_pathlike_infra_path() -> None:
    """build_worker raises FactoryConfigError for non-string/non-Path infra_path."""
    with pytest.raises(FactoryConfigError, match="string or Path"):
        PFPFactory().build_worker(infra_path=123)  # type: ignore[arg-type]


def test_get_pfp_factory_returns_factory_instance() -> None:
    """Factory helper returns a ready PFPFactory instance."""

    assert isinstance(get_pfp_factory(), PFPFactory)
