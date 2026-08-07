"""Mirror tests for redaction helpers: sanitize_text, sanitize_mapping."""

from __future__ import annotations

from pfp_utils.sanitization import sanitize_mapping, sanitize_text

# ---------------------------------------------------------------------------
# sanitize_text
# ---------------------------------------------------------------------------


def test_sanitize_text_masks_bearer_token() -> None:
    """sanitize_text masks a Bearer token while preserving the prefix."""
    result = sanitize_text("Authorization: Bearer abc123xyz")
    assert "abc123xyz" not in result
    assert "Bearer" in result
    assert "***" in result


def test_sanitize_text_masks_url_query_params() -> None:
    """sanitize_text masks sensitive URL query parameter values."""
    result = sanitize_text("https://x.test?a=1&api_key=abC123&token=def456")
    assert "abC123" not in result
    assert "def456" not in result
    assert "api_key=***" in result
    assert "token=***" in result
    assert "a=1" in result  # non-sensitive preserved


def test_sanitize_text_masks_inline_key_value_pairs() -> None:
    """sanitize_text masks inline key=value secret fragments."""
    result = sanitize_text("password=my-pass; secret=top; api_key=xyz")
    assert "my-pass" not in result
    assert "top" not in result
    assert "xyz" not in result
    assert "password=***" in result


def test_sanitize_text_replaces_known_secret_values() -> None:
    """sanitize_text verbatim-replaces explicit secret_values."""
    result = sanitize_text(
        "raw-token-12345 appears here", secret_values=["raw-token-12345"]
    )
    assert "raw-token-12345" not in result
    assert "***" in result


def test_sanitize_text_non_string_returns_mask() -> None:
    """sanitize_text returns mask for non-string input."""
    assert sanitize_text(None) == "***"  # type: ignore[arg-type]
    assert sanitize_text(123) == "***"  # type: ignore[arg-type]


def test_sanitize_text_custom_mask() -> None:
    """sanitize_text honours custom mask value."""
    result = sanitize_text("Bearer token", mask="[REDACTED]")
    assert "[REDACTED]" in result


def test_sanitize_text_combined_patterns() -> None:
    """sanitize_text handles known + Bearer + URL + inline together."""
    text = (
        "Authorization: Bearer top-secret-token; "
        "url=https://x.test?a=1&api_key=abC123; "
        "password=my-pass"
    )
    sanitized = sanitize_text(text, secret_values=["top-secret-token", "my-pass"])

    assert "top-secret-token" not in sanitized
    assert "my-pass" not in sanitized
    assert "***" in sanitized


# ---------------------------------------------------------------------------
# sanitize_mapping
# ---------------------------------------------------------------------------


def test_sanitize_mapping_masks_sensitive_keys() -> None:
    """sanitize_mapping masks entries whose keys contain secret/token/password/api_key."""
    payload = {
        "username": "merchant",
        "password": "my-pass",
        "nested": {"api_key": "abC123", "safe": "x"},
    }
    masked = sanitize_mapping(payload)
    assert masked["username"] == "merchant"
    assert masked["password"] == "***"
    assert masked["nested"]["api_key"] == "***"
    assert masked["nested"]["safe"] == "x"


def test_sanitize_mapping_masks_secret_token_access_token_keys() -> None:
    """sanitize_mapping masks additional sensitive key variants."""
    payload = {
        "auth_secret": "a",
        "refresh_token": "b",
        "x_api_key": "c",
        "plain": "ok",
    }
    masked = sanitize_mapping(payload)
    assert masked["auth_secret"] == "***"
    assert masked["refresh_token"] == "***"
    assert masked["x_api_key"] == "***"
    assert masked["plain"] == "ok"


def test_sanitize_mapping_redacts_sensitive_text_inside_lists() -> None:
    """sanitize_mapping sanitizes string fragments nested in list values recursively."""
    payload = {
        "safe": [
            "Authorization: Bearer top-secret-token",
            {"note": "api_key=inline-secret"},
        ]
    }

    masked = sanitize_mapping(payload)

    assert "top-secret-token" not in str(masked)
    assert "inline-secret" not in str(masked)
    assert "***" in str(masked)


def test_sanitize_mapping_recursive_nested_dict() -> None:
    """sanitize_mapping recurses into nested dicts."""
    payload = {"outer": {"middle": {"password": "secret", "plain": "ok"}}}
    masked = sanitize_mapping(payload)
    assert masked["outer"]["middle"]["password"] == "***"
    assert masked["outer"]["middle"]["plain"] == "ok"


def test_sanitize_mapping_preserves_non_string_values() -> None:
    """sanitize_mapping preserves int/bool/None values as-is."""
    payload = {"count": 42, "enabled": True, "optional": None}
    masked = sanitize_mapping(payload)
    assert masked["count"] == 42
    assert masked["enabled"] is True
    assert masked["optional"] is None


def test_sanitize_mapping_does_not_mutate_input() -> None:
    """sanitize_mapping returns a new mapping, input stays unchanged."""
    payload = {"password": "secret"}
    sanitize_mapping(payload)
    assert payload["password"] == "secret"
