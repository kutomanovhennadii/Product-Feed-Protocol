"""Tests for required_if_profile validation module."""

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.validation.module_validation_required_if_profile import (
    _normalize_profiles,
    _required_if_profile,
    get_spec,
)


def test_normalize_profiles_accepts_single_and_multiple_filters() -> None:
    """Module normalizes both singular and plural artifact-profile filters."""

    assert _normalize_profiles({}) is None
    assert _normalize_profiles({"artifact_profile": "   "}) is None
    assert _normalize_profiles({"artifact_profile": " Catalog_Snapshot "}) == {
        "catalog_snapshot"
    }
    assert _normalize_profiles(
        {
            "artifact_profiles": [
                " Catalog_Snapshot ",
                "inventory_price_delta",
                "",
                1,
            ]
        }
    ) == {"catalog_snapshot", "inventory_price_delta"}
    assert _normalize_profiles({"artifact_profiles": "catalog_snapshot"}) is None


def test_required_if_profile_ignores_inactive_profiles() -> None:
    """Validation is skipped when current artifact profile is outside configured set."""

    result = _required_if_profile(
        MISSING,
        {"artifact_profile": "catalog_snapshot"},
        artifact_profile="catalog_delta",
    )

    assert result.ok is True
    assert result.details is None


def test_required_if_profile_rejects_missing_and_null_when_rule_is_active() -> None:
    """Active profile filters reject both missing and null values."""

    missing_result = _required_if_profile(
        MISSING,
        {"artifact_profiles": ["catalog_snapshot"]},
        artifact_profile="catalog_snapshot",
    )
    null_result = _required_if_profile(None, {}, artifact_profile=None)
    ok_result = _required_if_profile(
        "value",
        {"artifact_profiles": ["catalog_snapshot"]},
        artifact_profile="catalog_snapshot",
    )

    assert missing_result.ok is False
    assert missing_result.details == "required_if_profile: value is missing"
    assert null_result.ok is False
    assert null_result.details == "required_if_profile: value is null"
    assert ok_result.ok is True


def test_required_if_profile_spec_exposes_expected_contract() -> None:
    """Spec builder declares the expected config fields and module id."""

    spec = get_spec()

    assert spec.module_id == "required_if_profile"
    assert spec.value_type.type_id == "any"
    assert tuple(field.name for field in spec.config_spec.fields) == (
        "artifact_profile",
        "artifact_profiles",
    )
    assert spec.call is _required_if_profile
