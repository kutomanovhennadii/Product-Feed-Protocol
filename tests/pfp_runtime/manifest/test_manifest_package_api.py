"""Mirror unit tests for manifest package public API."""

from __future__ import annotations

import pfp_runtime.manifest as manifest_package
import pfp_runtime.manifest.pipeline_manifest_provider as provider_module


def test_package_reexports_build_pipeline_manifest() -> None:
    """Package API re-exports provider function under stable public name."""
    assert (
        manifest_package.build_pipeline_manifest
        is provider_module.build_pipeline_manifest
    )


def test_package_all_contains_build_pipeline_manifest() -> None:
    """Package __all__ explicitly exposes only public build entry point."""
    assert manifest_package.__all__ == ["build_pipeline_manifest"]
