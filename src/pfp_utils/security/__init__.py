"""PFP security primitives: secret references and resolution."""

from pfp_utils.security.secret_resolver import resolve_secret
from pfp_utils.security.secret_types import (
    ResolvedSecret,
    SecretRef,
    SecretResolutionError,
)

__all__ = [
    "ResolvedSecret",
    "SecretRef",
    "SecretResolutionError",
    "resolve_secret",
]
