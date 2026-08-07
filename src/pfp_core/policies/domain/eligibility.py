"""Eligibility policy implementation."""

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple

from pfp_core.policies.utils.policy_utils import _require_mapping, _validate_keys
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.telemetry import TelemetryHandler


@dataclass(frozen=True)
class CheckoutRequirementsConfig:
    """Configuration for checkout eligibility requirements."""

    merchant_fields: Tuple[str, ...] = tuple()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CheckoutRequirementsConfig":
        """Parse checkout requirements config from a mapping.

        Args:
            data: Mapping with optional key ``merchant_fields``.

        Returns:
            Parsed CheckoutRequirementsConfig.

        Raises:
            ValueError: If ``merchant_fields`` is not a list/tuple.
        """
        fields = data.get("merchant_fields", [])
        if not isinstance(fields, (list, tuple)):
            raise ValueError(
                "eligibility.checkout_requirements.merchant_fields must be a list"
            )
        return cls(merchant_fields=tuple(fields))


@dataclass(frozen=True)
class EligibilityConfig:
    """Configuration for EligibilityPolicy."""

    checkout_requirements: CheckoutRequirementsConfig

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EligibilityConfig":
        """Parse eligibility policy config from a mapping.

        Args:
            data: Mapping under ``core.eligibility``.

        Returns:
            Parsed EligibilityConfig.

        Raises:
            ValueError: If config shape is invalid.
        """
        data = _require_mapping(data, "core.eligibility")
        _validate_keys(data, {"checkout_requirements"}, "core.eligibility")

        reqs_data = data.get("checkout_requirements", {})
        if not isinstance(reqs_data, dict):
            raise ValueError("core.eligibility.checkout_requirements must be a mapping")

        return cls(
            checkout_requirements=CheckoutRequirementsConfig.from_dict(reqs_data)
        )


class EligibilityPolicy:
    """Enforces eligibility rules for products."""

    def __init__(self, config: Optional[EligibilityConfig] = None) -> None:
        """Create EligibilityPolicy.

        Args:
            config: Parsed policy config; when None, the policy is effectively disabled.
        """
        self._config = config

    def validate(
        self,
        product: Mapping[str, Any],
        *,
        telemetry: Optional[TelemetryHandler] = None,
    ) -> List[Diagnostic]:
        """Validate eligibility requirements for a single product record.

        Args:
            product: Product record as a mapping.
            telemetry: Optional telemetry handler.

        Returns:
            List of eligibility diagnostics.
        """
        diagnostics: List[Diagnostic] = []

        if product.get("is_eligible_checkout"):
            violations = self._validate_checkout_requirements(product)
            diagnostics.extend(violations)

            if telemetry:
                telemetry.inc(
                    "eligibility_checked",
                    1.0,
                    labels={"type": "checkout", "eligible": str(len(violations) == 0)},
                )

        return diagnostics

    def _validate_checkout_requirements(
        self, product: Mapping[str, Any]
    ) -> List[Diagnostic]:
        """Validate checkout-specific requirements.

        Args:
            product: Product record as a mapping.

        Returns:
            List of diagnostics for missing checkout-required merchant fields.
        """
        diagnostics: List[Diagnostic] = []

        if not self._config or not self._config.checkout_requirements:
            return diagnostics

        required_fields = self._config.checkout_requirements.merchant_fields
        if not required_fields:
            return diagnostics

        merchant = product.get("merchant")
        if not isinstance(merchant, Mapping):
            for field in required_fields:
                diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code="ELIGIBILITY_CHECKOUT_MISSING_REQ",
                        message=(
                            "Checkout eligibility requires merchant field " f"'{field}'"
                        ),
                        item_ref=product.get("item_id", "unknown"),
                        path=f"merchant.{field}",
                    )
                )
            return diagnostics

        for field in required_fields:
            value = merchant.get(field)
            if not value:
                diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code="ELIGIBILITY_CHECKOUT_MISSING_REQ",
                        message=(
                            "Checkout eligibility requires merchant field " f"'{field}'"
                        ),
                        item_ref=product.get("item_id", "unknown"),
                        path=f"merchant.{field}",
                    )
                )

        return diagnostics
