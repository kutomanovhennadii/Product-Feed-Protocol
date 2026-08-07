"""Tests for ConnectorFieldMapping, ConnectorMappingConfig, and error types."""

import dataclasses

import pytest

from pfp_runtime.connectors.connector_mapping.connector_mapping_config import (
    ConnectorFieldMapping,
    ConnectorMappingConfig,
    ConnectorMappingLoadError,
    ConnectorMappingValidationError,
)


def test_connector_field_mapping_all_fields():
    """Verify that all fields are stored correctly when set explicitly.

    Given: source, target, required=True passed to ConnectorFieldMapping.
    When: Instance is created.
    Then: All attributes reflect the provided values.
    """
    mapping = ConnectorFieldMapping(
        source="sku", target="product.item_id", required=True
    )
    assert mapping.source == "sku"
    assert mapping.target == "product.item_id"
    assert mapping.required is True


def test_connector_field_mapping_default_required():
    """Verify that required defaults to False when not provided.

    Given: Only source and target passed to ConnectorFieldMapping.
    When: Instance is created.
    Then: required is False.
    """
    mapping = ConnectorFieldMapping(source="name", target="product.title")
    assert mapping.required is False


def test_connector_field_mapping_frozen():
    """Verify that ConnectorFieldMapping is immutable after creation.

    Given: A ConnectorFieldMapping instance.
    When: An attribute assignment is attempted.
    Then: FrozenInstanceError is raised.
    """
    mapping = ConnectorFieldMapping(source="sku", target="product.item_id")
    with pytest.raises(dataclasses.FrozenInstanceError):
        mapping.source = "new_sku"  # type: ignore[misc]


def test_connector_mapping_config_all_fields():
    """Verify that all fields are stored correctly when set explicitly.

    Given: mappings tuple and continue_on_error=False.
    When: ConnectorMappingConfig is created.
    Then: All attributes reflect the provided values.
    """
    field = ConnectorFieldMapping(source="sku", target="product.item_id", required=True)
    config = ConnectorMappingConfig(mappings=(field,), continue_on_error=False)
    assert config.mappings == (field,)
    assert config.continue_on_error is False


def test_connector_mapping_config_default_continue_on_error():
    """Verify that continue_on_error defaults to True when not provided.

    Given: Only mappings passed to ConnectorMappingConfig.
    When: Instance is created.
    Then: continue_on_error is True.
    """
    field = ConnectorFieldMapping(source="sku", target="product.item_id")
    config = ConnectorMappingConfig(mappings=(field,))
    assert config.continue_on_error is True


def test_connector_mapping_config_frozen():
    """Verify that ConnectorMappingConfig is immutable after creation.

    Given: A ConnectorMappingConfig instance.
    When: An attribute assignment is attempted.
    Then: FrozenInstanceError is raised.
    """
    field = ConnectorFieldMapping(source="sku", target="product.item_id")
    config = ConnectorMappingConfig(mappings=(field,))
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.continue_on_error = False  # type: ignore[misc]


def test_connector_mapping_config_empty_mappings():
    """Verify that empty mappings tuple is accepted at the dataclass level.

    Given: An empty tuple passed as mappings.
    When: ConnectorMappingConfig is created.
    Then: Instance is created without error (validation is the validator's job).
    """
    config = ConnectorMappingConfig(mappings=())
    assert config.mappings == ()


def test_connector_mapping_load_error_is_exception():
    """Verify that ConnectorMappingLoadError inherits from Exception.

    Given: ConnectorMappingLoadError class.
    When: Checked with issubclass and raised/caught.
    Then: It is a subclass of Exception and can be caught as Exception.
    """
    assert issubclass(ConnectorMappingLoadError, Exception)
    with pytest.raises(Exception):
        raise ConnectorMappingLoadError("file not found")


def test_connector_mapping_validation_error_is_exception():
    """Verify that ConnectorMappingValidationError inherits from Exception.

    Given: ConnectorMappingValidationError class.
    When: Checked with issubclass and raised/caught.
    Then: It is a subclass of Exception and can be caught as Exception.
    """
    assert issubclass(ConnectorMappingValidationError, Exception)
    with pytest.raises(Exception):
        raise ConnectorMappingValidationError("mappings list is empty")


def test_error_types_are_independent():
    """Verify that the two error types are distinct and not interchangeable.

    Given: ConnectorMappingLoadError and ConnectorMappingValidationError.
    When: Cross-checked with issubclass.
    Then: Neither is a subclass of the other.
    """
    assert not issubclass(ConnectorMappingLoadError, ConnectorMappingValidationError)
    assert not issubclass(ConnectorMappingValidationError, ConnectorMappingLoadError)
