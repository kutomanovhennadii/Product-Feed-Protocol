"""Tests for pfp_core.unified_model.pricing."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import pytest

pytest.importorskip(
    "pfp_core.unified_model", reason="unified_model removed: legacy tests disabled"
)

from decimal import Decimal

from pfp_core.unified_model.pricing import Money


def test_money_requires_currency() -> None:
    """Create valid Money with required currency and decimal amount."""
    money = Money(amount=Decimal("10.50"), currency="USD")
    assert money.amount == Decimal("10.50")
    assert money.currency == "USD"


def test_money_converts_amount_to_decimal() -> None:
    """Convert string amount input into Decimal during Money initialization."""
    money = Money(amount="10.50", currency="USD")  # type: ignore[arg-type]
    assert isinstance(money.amount, Decimal)
    assert money.amount == Decimal("10.50")
