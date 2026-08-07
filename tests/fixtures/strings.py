"""Deterministic string helpers for boundary fixtures."""


def repeat_token(token: str, length: int) -> str:
    """Build a string with exact character length from repeated token.

    Length is measured in characters, not bytes.

    Args:
        token: Source token; if empty, ``"x"`` is used.
        length: Required character length.

    Returns:
        String with exact ``length`` characters.
    """
    if length <= 0:
        return ""
    stable_token = token or "x"
    repeats = (length // len(stable_token)) + 1
    return (stable_token * repeats)[:length]


def ascii_text(length: int) -> str:
    """Build deterministic ASCII text with exact character length.

    Args:
        length: Required character length.

    Returns:
        ASCII-only string.
    """
    return repeat_token("abc", length)


def utf8_text(length: int) -> str:
    """Build deterministic Unicode text with exact character length.

    Args:
        length: Required character length.

    Returns:
        Unicode text with exact character length.
    """
    return repeat_token("тест", length)


def ascii_bytes(byte_length: int) -> bytes:
    """Build deterministic ASCII bytes with exact byte length.

    Args:
        byte_length: Required byte length.

    Returns:
        ASCII bytes with exact ``byte_length``.
    """
    return ascii_text(byte_length).encode("ascii")
