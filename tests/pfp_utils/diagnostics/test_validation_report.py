from typing import Any, Dict, List, cast

from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.validation_report import ValidationReport


def test_validation_report_serialization_is_deterministic() -> None:
    """Serialize diagnostics in deterministic order by severity and keys."""
    report = ValidationReport(
        target="stripe.product", artifact_profile="catalog_snapshot"
    )

    report.add(
        Diagnostic(
            severity="INFO",
            code="INFO_CODE",
            message="informational",
            item_ref="SKU-INFO",
        )
    )
    report.add(
        Diagnostic(
            severity="WARN",
            code="WARN_CODE",
            message="warning",
            item_ref="SKU0",
        )
    )
    report.add(
        Diagnostic(
            severity="ERROR",
            code="ERR_CODE",
            message="error",
            item_ref="SKU-ERROR",
            path="price.amount",
        )
    )

    serialized = cast(List[Dict[str, Any]], report.to_dict()["diagnostics"])
    assert report.to_dict()["artifact_profile"] == "catalog_snapshot"
    assert serialized[0]["severity"] == "ERROR"
    assert serialized[1]["severity"] == "WARN"
    assert serialized[2]["code"] == "INFO_CODE"
