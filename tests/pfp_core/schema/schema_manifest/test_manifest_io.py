"""Tests for schema manifest file I/O helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pfp_core.schema.schema_manifest.manifest_io import load_manifest_file


def test_load_manifest_file_rejects_non_object_root(tmp_path: Path) -> None:
    """Raise when manifest JSON root value is not an object mapping."""

    manifest_path = tmp_path / "schema_manifest.json"
    manifest_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with pytest.raises(ValueError, match="root JSON"):
        load_manifest_file(manifest_path)
