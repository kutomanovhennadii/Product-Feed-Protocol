"""Configuration utilities for PFP policies."""

from typing import Any, Mapping, Set


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping at '{path}'")
    return value


def _validate_keys(data: Mapping[str, Any], allowed: Set[str], path: str) -> None:
    unknown = set(data.keys()) - allowed
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown keys at '{path}': {unknown_list}")


def _require_key(data: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required key '{key}' at '{path}'")
    return data[key]


def _normalize_version(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    raise ValueError("Policy config version must be a string")
