"""Tests for EligibilityPolicy."""

from typing import Any, Dict, Optional

import pytest

from pfp_core.policies.domain.eligibility import (
    CheckoutRequirementsConfig,
    EligibilityConfig,
    EligibilityPolicy,
)
from pfp_utils.diagnostics.diagnostic_models import DiagnosticSeverity


def create_product(
    is_eligible_checkout: bool = False,
    is_eligible_search: bool = True,
    merchant: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper to create a product dict for testing."""
    return {
        "item_id": "test_item",
        "title": "Test Item",
        "description": "Description",
        "url": "http://example.com",
        "is_eligible_checkout": is_eligible_checkout,
        "is_eligible_search": is_eligible_search,
        "merchant": merchant,
    }


def test_checkout_product_missing_required_field() -> None:
    """Checkout-eligible product without required merchant field emits error diagnostic."""
    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(
                merchant_fields=("seller_tos",)
            )
        )
    )

    merchant = {"seller_name": "Seller", "seller_url": "http://s.com"}
    diagnostics = policy.validate(
        create_product(is_eligible_checkout=True, merchant=merchant)
    )
    assert len(diagnostics) == 1
    assert (
        DiagnosticSeverity.normalize(diagnostics[0].severity)
        == DiagnosticSeverity.ERROR
    )
    assert diagnostics[0].code == "ELIGIBILITY_CHECKOUT_MISSING_REQ"


def test_search_only_product_valid() -> None:
    """Search-only products pass eligibility checks without checkout requirements."""
    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(
                merchant_fields=("seller_tos",)
            )
        )
    )
    assert not policy.validate(
        create_product(is_eligible_checkout=False, merchant=None)
    )


def test_checkout_requirements_from_dict_invalid_fields_type_raises() -> None:
    """CheckoutRequirementsConfig.from_dict rejects non-list merchant_fields."""
    with pytest.raises(
        ValueError,
        match="merchant_fields must be a list",
    ):
        CheckoutRequirementsConfig.from_dict({"merchant_fields": "seller_tos"})


def test_eligibility_config_from_dict_invalid_checkout_requirements_type_raises() -> (
    None
):
    """EligibilityConfig.from_dict rejects non-mapping checkout_requirements."""
    with pytest.raises(
        ValueError,
        match="checkout_requirements must be a mapping",
    ):
        EligibilityConfig.from_dict({"checkout_requirements": "not-a-mapping"})


def test_missing_merchant_emits_diagnostics() -> None:
    """Checkout-eligible product with merchant=None emits error for each required field."""
    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(
                merchant_fields=("seller_tos", "seller_privacy_policy")
            )
        )
    )

    diagnostics = policy.validate(
        create_product(is_eligible_checkout=True, merchant=None)
    )

    assert len(diagnostics) == 2
    codes = {d.code for d in diagnostics}
    assert codes == {"ELIGIBILITY_CHECKOUT_MISSING_REQ"}


def test_no_config_returns_empty() -> None:
    """Policy without config returns empty diagnostics list."""
    policy = EligibilityPolicy()

    diagnostics = policy.validate(
        create_product(is_eligible_checkout=True, merchant={"seller_name": "S"})
    )

    assert diagnostics == []


def test_empty_required_fields_returns_empty() -> None:
    """Configured policy with empty merchant_fields returns no diagnostics."""
    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(merchant_fields=tuple())
        )
    )

    diagnostics = policy.validate(
        create_product(is_eligible_checkout=True, merchant={"seller_name": "S"})
    )

    assert diagnostics == []


def test_validate_emits_telemetry_metric() -> None:
    """validate() emits eligibility_checked metric when telemetry handler is provided."""

    class _TelemetryStub:
        """Minimal TelemetryHandler stub for unit tests."""

        def __init__(self) -> None:
            self.calls: list[tuple[str, float, dict[str, str]]] = []

        def observe_duration(
            self, stage: str, duration: float, labels: Dict[str, str]
        ) -> None:
            del stage, duration, labels

        def inc(
            self,
            name: str,
            value: float = 1.0,
            labels: Dict[str, str] | None = None,
        ) -> None:
            self.calls.append((name, value, dict(labels or {})))

    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(
                merchant_fields=("seller_tos",)
            )
        )
    )
    telemetry = _TelemetryStub()

    diagnostics = policy.validate(
        create_product(
            is_eligible_checkout=True,
            merchant={"seller_name": "Seller", "seller_url": "http://s.com"},
        ),
        telemetry=telemetry,
    )

    assert len(diagnostics) == 1
    assert telemetry.calls == [
        ("eligibility_checked", 1.0, {"type": "checkout", "eligible": "False"})
    ]


def test_all_merchant_fields_present_returns_empty() -> None:
    """Checkout-eligible product with all required merchant fields emits no diagnostics."""
    policy = EligibilityPolicy(
        EligibilityConfig(
            checkout_requirements=CheckoutRequirementsConfig(
                merchant_fields=("seller_tos",)
            )
        )
    )

    merchant = {
        "seller_name": "Seller",
        "seller_url": "http://s.com",
        "seller_tos": "http://tos",
    }
    diagnostics = policy.validate(
        create_product(is_eligible_checkout=True, merchant=merchant)
    )

    assert diagnostics == []
