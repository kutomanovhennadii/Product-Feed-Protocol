"""Integration tests for the pfp_runtime.shell block."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_runtime.config.infra_loader import InfraConfigParseError
from pfp_runtime.manifest.pipeline_manifest import ManifestBuildError
from pfp_runtime.shell.factory import PFPFactory
from tests.pfp_runtime._integration_helpers import (
    python_root,
    runtime_csv_input,
    write_runtime_infra,
)


def test_factory_build_worker_runs_fixture_pipeline_successfully(
    tmp_path: Path,
) -> None:
    """Shell factory builds a worker and preserves the current validation-stop contract.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
    """

    worker = PFPFactory().build_worker(infra_path=write_runtime_infra(tmp_path))

    report = worker.run(runtime_csv_input())

    assert report.status == "SUCCESS"
    assert len(report.artifacts) == 1
    assert report.artifacts[0].payload == (b"id,title,description,link,availability\n",)
    assert {diagnostic.code for diagnostic in report.validation_report.diagnostics} >= {
        "BUILD.FAIL_STOP",
        "STRIPE_TITLE_REQUIRED",
    }
    assert worker.producer is not None


def test_factory_build_worker_propagates_missing_infra_errors() -> None:
    """Shell factory propagates the infra loader error for a missing YAML file."""

    with pytest.raises(InfraConfigParseError, match="cannot read infra config file"):
        PFPFactory().build_worker(infra_path="./does-not-exist-infra.yaml")


def test_factory_build_worker_requires_tax_mapping_for_shopify_realtime(
    tmp_path: Path,
) -> None:
    """Shell factory surfaces the init-time failure for realtime schemas without tax mapping.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
    """

    root = python_root()

    with pytest.raises(
        ManifestBuildError,
        match="map_tax_code requires tax_mapping in producer context",
    ):
        PFPFactory().build_worker(
            infra_path=write_runtime_infra(
                tmp_path,
                schema_file=root
                / "schemas"
                / "stripe.shopify_realtime"
                / "stripe.shopify_realtime-1.0.0.yaml",
                policy_file=root
                / "config"
                / "shopify_realtime"
                / "policies_shopify_realtime.yaml",
            )
        )
