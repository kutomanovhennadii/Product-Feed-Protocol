import pytest

from pfp_core.artifact_production.artifact_production_schema_resolution import (
    normalize_target_id,
)


def test_normalize_target_id_normalizes_only_without_semantic_remapping() -> None:
    """Normalize target id format without changing explicit identity semantics."""
    assert normalize_target_id("stripe.product") == "stripe.product"
    assert normalize_target_id("openai.product_feed") == "openai.product_feed"
    assert normalize_target_id("custom.catalog") == "custom.catalog"


def test_schema_resolution_error_branches() -> None:
    """Cover remaining schema-resolution validation and normalization error paths."""
    assert normalize_target_id("unknown.feed") == "unknown.feed"
    with pytest.raises(ValueError, match="target_id must be a string"):
        normalize_target_id(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        normalize_target_id("   ")
