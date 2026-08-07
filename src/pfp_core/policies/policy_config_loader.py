"""YAML loaders for policy configuration and bundles."""

from typing import Optional

import yaml  # type: ignore[import-untyped]

from pfp_core.policies.policy_bundle import PolicyBundle
from pfp_core.policies.policy_bundle_builder import build_policy_bundle
from pfp_core.policies.policy_config import PolicyConfig
from pfp_core.policies.policy_registry import PolicyRegistry
from pfp_utils.logging import LogPipeline


def load_policy_config_from_yaml_text(yaml_text: str) -> PolicyConfig:
    """Load and validate a PolicyConfig from YAML text."""
    data = yaml.safe_load(yaml_text)
    if data is None:
        raise ValueError("Policy config is empty")
    if not isinstance(data, dict):
        raise ValueError("Policy config root must be a mapping")
    return PolicyConfig.from_dict(data)


def load_policy_bundle_from_yaml_text(
    yaml_text: str,
    registry: Optional[PolicyRegistry] = None,
    *,
    log_pipeline: LogPipeline,
) -> PolicyBundle:
    """Load a policy bundle directly from YAML text."""
    config = load_policy_config_from_yaml_text(yaml_text)
    return build_policy_bundle(config, registry, log_pipeline=log_pipeline)


load_policy_config = load_policy_config_from_yaml_text
load_policy_bundle = load_policy_bundle_from_yaml_text
