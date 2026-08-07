from __future__ import annotations

from typing import List, SupportsIndex, Tuple

import pytest

import pfp_core.schema.schema_refs as refs_module
from pfp_core.schema.schema_refs import extract_ref_from_doc, extract_ref_from_filename
from pfp_core.schema.schema_types import SchemaErrorItem, SchemaFormatError


def _error_triplets(error: SchemaFormatError) -> List[Tuple[str, str, str]]:
    """Convert schema error items to comparable tuples."""

    return [(item.code, item.path, item.message) for item in error.items]


def test_extract_ref_from_doc_reports_missing_header() -> None:
    """Ensure missing header in schema doc yields SCHEMA_MISSING_FIELD."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_doc({})

    assert any(item.path == "header" for item in exc.value.items)


def test_extract_ref_from_doc_reports_invalid_field_types() -> None:
    """Ensure invalid header field types are reported deterministically."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_doc({"header": {"protocol_id": 1, "schema_version": 2}})

    assert _error_triplets(exc.value) == [
        (
            "SCHEMA_INVALID_TYPE",
            "header.protocol_id",
            "header.protocol_id must be a string.",
        ),
        (
            "SCHEMA_INVALID_TYPE",
            "header.schema_version",
            "header.schema_version must be a string.",
        ),
    ]


def test_extract_ref_from_filename_collects_multiple_errors() -> None:
    """Ensure filename parser accumulates multiple errors before raising."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_filename("bad name.txt")

    assert _error_triplets(exc.value) == [
        (
            "SCHEMA_FILENAME_INVALID",
            "$",
            "Filename extension must be one of: json, yaml, yml.",
        ),
        (
            "SCHEMA_FILENAME_INVALID",
            "$",
            "Filename must be non-empty and must not contain spaces.",
        ),
        (
            "SCHEMA_FILENAME_INVALID",
            "$",
            "Filename must match <protocol_id>-<schema_version>.<ext>.",
        ),
    ]


def test_extract_ref_from_filename_requires_extension() -> None:
    """Ensure filename without extension is rejected."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_filename("stripeproductfeed-100")

    assert (
        "SCHEMA_FILENAME_INVALID",
        "$",
        "Filename must include an extension.",
    ) in _error_triplets(exc.value)


def test_extract_ref_from_filename_requires_dash_pattern() -> None:
    """Ensure filename stem without dash protocol/version separator is rejected."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_filename("stripe.product_feed_1.0.0.yaml")

    assert (
        "SCHEMA_FILENAME_INVALID",
        "$",
        "Filename must match <protocol_id>-<schema_version>.<ext>.",
    ) in _error_triplets(exc.value)


def test_protocol_id_rejects_dash_in_filename() -> None:
    """Ensure protocol_id with dash in filename is rejected."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_filename("protocol-id-with-dash-1.0.0.yaml")

    assert exc.value.items[0].code == "SCHEMA_PROTOCOL_ID_INVALID"


def test_schema_version_requires_semver_in_filename() -> None:
    """Ensure non-SemVer schema_version in filename is rejected."""

    with pytest.raises(SchemaFormatError) as exc:
        extract_ref_from_filename("stripe.product_feed-1.0.yaml")

    assert exc.value.items[0].code == "SCHEMA_VERSION_INVALID"


def test_extract_ref_from_doc_raises_when_helper_returns_none_without_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _no_items_none(*args, **kwargs):
        return None

    monkeypatch.setattr(refs_module, "_try_get_mapping", _no_items_none)
    monkeypatch.setattr(refs_module, "_try_get_str", _no_items_none)

    with pytest.raises(SchemaFormatError):
        extract_ref_from_doc({"header": {}})


def test_extract_ref_from_filename_raises_when_identifiers_not_extracted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Stem(str):
        def rsplit(self, sep: str | None = None, maxsplit: SupportsIndex = -1):
            if sep == "-" and maxsplit == 1:
                return ["stripe.product_feed", None]
            return super().rsplit(sep, maxsplit)

    class _Name(str):
        def rsplit(self, sep: str | None = None, maxsplit: SupportsIndex = -1):
            if sep == "." and maxsplit == 1:
                return [_Stem("stripe.product_feed-opaque"), "yaml"]
            return super().rsplit(sep, maxsplit)

    monkeypatch.setattr(
        refs_module,
        "PurePath",
        lambda _value: type(
            "_P", (), {"name": _Name("stripe.product_feed-opaque.yaml")}
        )(),
    )

    with pytest.raises(SchemaFormatError):
        extract_ref_from_filename("ignored")


def test_private_helper_try_get_mapping_non_mapping_value() -> None:
    items: List[SchemaErrorItem] = []
    result = refs_module._try_get_mapping({"header": "x"}, "header", "header", items)
    assert result is None
    assert any(item.code == "SCHEMA_INVALID_TYPE" for item in items)


def test_private_helper_try_get_str_missing_key() -> None:
    items: List[SchemaErrorItem] = []
    result = refs_module._try_get_str({}, "protocol_id", "header.protocol_id", items)
    assert result is None
    assert any(item.code == "SCHEMA_MISSING_FIELD" for item in items)


def test_private_helper_try_extract_ref_none_and_valid() -> None:
    assert refs_module._try_extract_ref("not-a-mapping") is None
    assert (
        refs_module._try_extract_ref(
            {"header": {"protocol_id": 1, "schema_version": "1.0.0"}}
        )
        is None
    )
    assert (
        refs_module._try_extract_ref(
            {
                "header": {
                    "protocol_id": "stripe.product_feed",
                    "schema_version": "1.0.0",
                }
            }
        )
        is not None
    )
