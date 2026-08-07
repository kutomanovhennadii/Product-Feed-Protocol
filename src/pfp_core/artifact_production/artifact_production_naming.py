"""Deterministic filename hint rules for artifacts."""

import re
from typing import Dict, Optional

EXT_BY_TARGET: Dict[str, str] = {
    "stripe": ".csv",
    "openai": ".jsonl",
}

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]")


def make_filename_hint(
    target: str,
    artifact_profile: str,
    schema_version: str,
    file_extension: Optional[str] = None,
) -> str:
    """Build a deterministic filename hint for an artifact.

    Args:
        target: Target identifier (e.g., STRIPE, OPENAI).
        artifact_profile: Artifact profile (e.g., catalog_snapshot).
        schema_version: Target schema version.
        file_extension: Optional explicit extension from writer spec.

    Returns:
        Deterministic filename hint with a target-specific extension.

    Raises:
        ValueError: If target is empty or unsupported.
    """
    if not target:
        raise ValueError("Target must not be empty")

    if file_extension is not None:
        safe_target = target.replace("/", "_")
        safe_artifact_profile = artifact_profile.replace("/", "_")
        safe_schema_version = schema_version.replace("/", "_")
        return (
            safe_target
            + "__"
            + safe_artifact_profile
            + "__v"
            + safe_schema_version
            + file_extension
        )

    normalized_target = _normalize_target_for_extension(target)
    ext = EXT_BY_TARGET.get(normalized_target)
    if ext is None:
        raise ValueError("Unsupported target for filename hint: {0}".format(target))

    return "{0}__{1}__v{2}{3}".format(
        _sanitize_part(target),
        _sanitize_part(artifact_profile),
        _sanitize_part(schema_version),
        ext,
    )


def _sanitize_part(value: str) -> str:
    """Sanitize filename components to the allowed character set."""
    return _SANITIZE_RE.sub("_", value or "")


def _normalize_target_for_extension(target: str) -> str:
    """Normalize target to base key for extension mapping."""
    if not target:
        return ""
    base = re.split(r"[._-]", target, maxsplit=1)[0]
    return re.sub(r"[^A-Za-z0-9]", "", base).lower()
