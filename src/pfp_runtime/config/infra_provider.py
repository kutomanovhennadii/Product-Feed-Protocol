"""Thin provider that assembles canonical infra load+validate pipeline."""

from __future__ import annotations

from typing import List

from pfp_runtime.config.infra_loader import load_infra_config
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.config.infra_normalizer import normalize_infra_paths
from pfp_runtime.config.infra_validator import validate_infra_config


class InfraProvider:
    """Provide validated InfraConfig through a single config-layer entrypoint."""

    def get_infra(self, path: str) -> InfraConfig:
        """Load infra config and run semantic validation.

        Args:
            path: Path to infra YAML file.

        Returns:
            Validated canonical InfraConfig.

        Raises:
            InfraConfigError: If the loader fails to read or parse the infra YAML.
            InfraConfigValidationError: If semantic validation fails.
        """
        infra = load_infra_config(path)
        validated = validate_infra_config(infra, infra_path=path)
        return normalize_infra_paths(validated, infra_path=path)


__all__: List[str] = ["InfraProvider"]
