"""Tests for connector_mapping_validator.validate_mapping."""

from pathlib import Path

import pytest

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorMappingValidationError,
)
from pfp_runtime.connectors.connector_mapping.connector_mapping_loader import load_yaml
from pfp_runtime.connectors.connector_mapping.connector_mapping_validator import (
    validate_mapping,
)

_REAL_MAPPING_PATH = Path(__file__).resolve().parents[4] / "config" / "mapping.yaml"


def test_validate_mapping_all_fields() -> None:
    """Happy path: two mappings (one required, one not) and explicit continue_on_error=False."""
    raw = {
        "mappings": [
            {"source": "sku", "target": "product.item_id", "required": True},
            {"source": "name", "target": "product.title"},
        ],
        "continue_on_error": False,
    }

    config = validate_mapping(raw)

    assert len(config.mappings) == 2
    assert config.mappings[0].source == "sku"
    assert config.mappings[0].target == "product.item_id"
    assert config.mappings[0].required is True
    assert config.mappings[1].source == "name"
    assert config.mappings[1].required is False
    assert config.continue_on_error is False


def test_validate_mapping_default_required_false() -> None:
    """Mapping item without 'required' key defaults to required=False."""
    raw = {"mappings": [{"source": "sku", "target": "product.item_id"}]}

    config = validate_mapping(raw)

    assert config.mappings[0].required is False


def test_validate_mapping_default_continue_on_error_true() -> None:
    """Dict without 'continue_on_error' defaults to continue_on_error=True."""
    raw = {"mappings": [{"source": "sku", "target": "product.item_id"}]}

    config = validate_mapping(raw)

    assert config.continue_on_error is True


def test_validate_mapping_missing_mappings_key() -> None:
    """Empty dict raises ConnectorMappingValidationError mentioning 'mappings'."""
    with pytest.raises(ConnectorMappingValidationError, match="mappings"):
        validate_mapping({})


def test_validate_mapping_empty_list() -> None:
    """mappings=[] raises ConnectorMappingValidationError mentioning 'non-empty'."""
    with pytest.raises(ConnectorMappingValidationError, match="non-empty"):
        validate_mapping({"mappings": []})


def test_validate_mapping_mappings_not_a_list() -> None:
    """mappings value that is not a list raises ConnectorMappingValidationError."""
    with pytest.raises(ConnectorMappingValidationError):
        validate_mapping({"mappings": "bad"})


def test_validate_mapping_item_not_a_dict() -> None:
    """A list item that is a string raises ConnectorMappingValidationError mentioning mappings[0]."""
    with pytest.raises(ConnectorMappingValidationError, match=r"mappings\[0\]"):
        validate_mapping({"mappings": ["not_a_dict"]})


def test_validate_mapping_missing_source() -> None:
    """Item with only 'target' raises ConnectorMappingValidationError mentioning mappings[0] and source."""
    with pytest.raises(
        ConnectorMappingValidationError,
        match=r"mappings\[0\].*source|source.*mappings\[0\]",
    ):
        validate_mapping({"mappings": [{"target": "product.item_id"}]})


def test_validate_mapping_empty_source_string() -> None:
    """Item with source='' raises ConnectorMappingValidationError."""
    with pytest.raises(ConnectorMappingValidationError):
        validate_mapping({"mappings": [{"source": "", "target": "product.item_id"}]})


def test_validate_mapping_missing_target() -> None:
    """Item with only 'source' raises ConnectorMappingValidationError mentioning mappings[0] and target."""
    with pytest.raises(
        ConnectorMappingValidationError,
        match=r"mappings\[0\].*target|target.*mappings\[0\]",
    ):
        validate_mapping({"mappings": [{"source": "sku"}]})


def test_validate_mapping_required_not_bool() -> None:
    """required='yes' raises ConnectorMappingValidationError mentioning mappings[0] and required."""
    with pytest.raises(
        ConnectorMappingValidationError,
        match=r"mappings\[0\].*required|required.*mappings\[0\]",
    ):
        validate_mapping(
            {
                "mappings": [
                    {"source": "sku", "target": "product.item_id", "required": "yes"}
                ]
            }
        )


def test_validate_mapping_continue_on_error_not_bool() -> None:
    """continue_on_error='yes' raises ConnectorMappingValidationError mentioning continue_on_error."""
    with pytest.raises(ConnectorMappingValidationError, match="continue_on_error"):
        validate_mapping(
            {
                "mappings": [{"source": "sku", "target": "product.item_id"}],
                "continue_on_error": "yes",
            }
        )


def test_validate_mapping_error_message_contains_no_raw_values() -> None:
    """Security rule: error message must not expose raw values from the mapping dict."""
    sentinel = "SECRET_VALUE"

    with pytest.raises(ConnectorMappingValidationError) as exc_info:
        validate_mapping(
            {
                "mappings": [
                    {"source": "sku", "target": "product.item_id", "required": sentinel}
                ]
            }
        )

    assert sentinel not in str(exc_info.value)


def test_validate_mapping_integration_with_real_file() -> None:
    """Integration: load_yaml + validate_mapping on the real config/mapping.yaml returns a valid config."""
    raw = load_yaml(_REAL_MAPPING_PATH)
    config = validate_mapping(raw)

    assert len(config.mappings) > 0

    targets = {m.target for m in config.mappings}
    assert "product.item_id" in targets
    assert "product.title" in targets
