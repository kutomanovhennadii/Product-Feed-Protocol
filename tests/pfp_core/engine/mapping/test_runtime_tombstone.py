from pfp_core.engine.mapping.runtime_tombstone import (
    _should_project_delete_tombstone,
    detect_delete_unsupported,
)
from pfp_core.engine.plan_types import MappingPlan


def test_should_project_delete_tombstone_on_delete_flag_for_allowed_profile() -> None:
    """delete=true projects tombstone when feature is enabled in mapping plan."""
    plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=True,
        delete_tombstone_flag_path="delete",
    )

    assert (
        _should_project_delete_tombstone(
            plan=plan,
            input_record={"delete": True},
            artifact_profile="catalog_delta",
        )
        is True
    )


def test_should_project_delete_tombstone_handles_disabled_missing_and_string() -> None:
    """Projection handles disabled mode, missing flag, and string forms of delete."""
    disabled_plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=False,
        delete_tombstone_flag_path="delete",
    )
    assert (
        _should_project_delete_tombstone(
            plan=disabled_plan,
            input_record={"delete": True},
            artifact_profile="catalog_delta",
        )
        is False
    )


def test_detect_delete_unsupported_returns_issue_when_disabled() -> None:
    """Delete intent reports CONTRACT.DELETE_UNSUPPORTED when tombstone is disabled."""
    plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=False,
        delete_tombstone_flag_path="delete",
    )

    issue = detect_delete_unsupported(
        plan=plan,
        input_record={"delete": True},
        artifact_profile="custom_profile",
    )

    assert issue is not None
    code, path, message = issue
    assert code == "CONTRACT.DELETE_UNSUPPORTED"
    assert path == "build:contract"
    assert "custom_profile" in message


def test_detect_delete_unsupported_returns_none_when_supported_or_absent() -> None:
    """No issue is emitted when tombstone is enabled or delete intent is absent."""
    enabled_plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=True,
        delete_tombstone_flag_path="delete",
    )
    assert (
        detect_delete_unsupported(
            plan=enabled_plan,
            input_record={"delete": True},
            artifact_profile="catalog_delta",
        )
        is None
    )

    disabled_plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=False,
        delete_tombstone_flag_path="delete",
    )
    assert (
        detect_delete_unsupported(
            plan=disabled_plan,
            input_record={},
            artifact_profile="catalog_snapshot",
        )
        is None
    )
    assert (
        detect_delete_unsupported(
            plan=disabled_plan,
            input_record={"delete": "no"},
            artifact_profile="catalog_snapshot",
        )
        is None
    )
    assert (
        detect_delete_unsupported(
            plan=disabled_plan,
            input_record={"delete": 1},
            artifact_profile="catalog_snapshot",
        )
        is None
    )

    enabled_plan = MappingPlan(
        output_kind="json_object",
        delete_tombstone_enabled=True,
        delete_tombstone_flag_path="delete",
    )
    assert (
        _should_project_delete_tombstone(
            plan=enabled_plan,
            input_record={},
            artifact_profile="catalog_delta",
        )
        is False
    )
    assert (
        _should_project_delete_tombstone(
            plan=enabled_plan,
            input_record={"delete": "yes"},
            artifact_profile="catalog_delta",
        )
        is True
    )
    assert (
        _should_project_delete_tombstone(
            plan=enabled_plan,
            input_record={"delete": "no"},
            artifact_profile="catalog_delta",
        )
        is False
    )
    assert (
        _should_project_delete_tombstone(
            plan=enabled_plan,
            input_record={"delete": 1},
            artifact_profile="catalog_delta",
        )
        is False
    )
