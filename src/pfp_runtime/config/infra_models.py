"""Canonical user-facing infra models for runtime config layer."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputSourceConfig(BaseModel):
    """Input config connection details for canonical infra config."""

    model_config = ConfigDict(extra="forbid")

    connector_mapping: Optional[str] = None

    @field_validator("connector_mapping")
    @classmethod
    def _validate_optional_non_empty(cls, value: Optional[str]) -> Optional[str]:
        """Validate optional string fields when present.

        Args:
            value: Optional string value.

        Returns:
            Trimmed value, or None when the field is omitted.

        Raises:
            ValueError: If the value is provided but blank after trimming.
        """
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized


class InputConfig(BaseModel):
    """Canonical input section for infra config."""

    model_config = ConfigDict(extra="forbid")

    format: str
    config: InputSourceConfig

    @field_validator("format")
    @classmethod
    def _normalize_format(cls, value: str) -> str:
        """Normalize the input format token.

        Args:
            value: Input format token.

        Returns:
            Normalized token (trimmed, lowercased).

        Raises:
            ValueError: If the token is blank after trimming.
        """
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("format must be non-empty")
        return normalized


class OutputConfig(BaseModel):
    """Canonical output section for infra config (publisher v2 schema).

    All four fields are required: archive_type and client_type are registry keys,
    archive_config and client_config are paths to IaC YAML files.
    """

    model_config = ConfigDict(extra="forbid")

    archive_type: str
    archive_config: str
    client_type: str
    client_config: str

    @field_validator("archive_type", "client_type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        """Normalize registry key: strip and lowercase.

        Args:
            value: Registry key token.

        Returns:
            Normalized token (trimmed, lowercased).

        Raises:
            ValueError: If the token is blank after trimming.
        """
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized

    @field_validator("archive_config", "client_config")
    @classmethod
    def _validate_config_path(cls, value: str) -> str:
        """Validate IaC config path: strip and require non-empty.

        Args:
            value: Path to IaC YAML file.

        Returns:
            Trimmed path.

        Raises:
            ValueError: If the path is blank after trimming.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized


class FloodControlConfig(BaseModel):
    """Canonical flood-control subtree for observability logging."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: str = "context_info_suppression"
    context_keys: List[str] = Field(default_factory=lambda: ["item_ref"])
    suppressed_levels: List[str] = Field(default_factory=lambda: ["INFO"])
    force_log_attr: str = "force_log"
    key_fields: List[str] = Field(
        default_factory=lambda: ["name", "levelno", "msg", "item_ref"]
    )
    window_seconds: float = 30.0
    max_events_per_window: int = 1
    emit_summary: bool = False
    summary_level: str = "INFO"
    summary_interval_seconds: float = 30.0
    max_cache_size: int = 10000


class LoggingConfig(BaseModel):
    """Minimal runtime logging options for observability."""

    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    flood_control_config: FloodControlConfig = Field(default_factory=FloodControlConfig)

    @field_validator("level")
    @classmethod
    def _normalize_level(cls, value: str) -> str:
        """Normalize the logging level token.

        Args:
            value: Logging level token.

        Returns:
            Uppercased token.

        Raises:
            ValueError: If the token is blank after trimming.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("level must be non-empty")
        return normalized.upper()


class TelemetryConfig(BaseModel):
    """Telemetry provider configuration for runtime observability."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "none"

    @field_validator("provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        """Normalize and validate telemetry provider token.

        Args:
            value: Provider token.

        Returns:
            Lowercased provider token.

        Raises:
            ValueError: If provider is not 'none' or 'prometheus'.
        """
        normalized = value.strip().lower()
        if normalized not in {"none", "prometheus"}:
            raise ValueError("telemetry.provider must be 'none' or 'prometheus'")
        return normalized


class ObservabilityConfig(BaseModel):
    """Canonical observability section for infra config."""

    model_config = ConfigDict(extra="forbid")

    log_format: str = "TEXT"
    labels: Dict[str, str] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    @field_validator("log_format")
    @classmethod
    def _normalize_log_format(cls, value: str) -> str:
        """Normalize and validate observability log format token.

        Args:
            value: Log format token.

        Returns:
            Uppercased token.

        Raises:
            ValueError: If value is not 'TEXT' or 'JSON'.
        """
        normalized = value.strip().upper()
        if normalized not in {"TEXT", "JSON"}:
            raise ValueError("observability.log_format must be 'TEXT' or 'JSON'")
        return normalized


class ProducerConfig(BaseModel):
    """Assembly-time producer configuration using file references."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_file: str
    policy_file: str
    tax_mapping_file: Optional[str] = None

    @field_validator("policy_file")
    @classmethod
    def _validate_non_empty_path(cls, value: str) -> str:
        """Validate producer policy file path.

        Args:
            value: Policy file path.

        Returns:
            Trimmed path.

        Raises:
            ValueError: If the path is blank after trimming.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized

    @field_validator("schema_file")
    @classmethod
    def _validate_optional_schema_file(cls, value: str) -> str:
        """Validate producer schema file path.

        Args:
            value: Schema file path.

        Returns:
            Trimmed path.

        Raises:
            ValueError: If the path is blank after trimming.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized

    @field_validator("tax_mapping_file")
    @classmethod
    def _validate_optional_tax_mapping_file(cls, value: Optional[str]) -> Optional[str]:
        """Validate optional producer tax mapping file path.

        Args:
            value: Optional tax mapping file path.

        Returns:
            Trimmed path, or None when the field is omitted.

        Raises:
            ValueError: If the path is provided but blank after trimming.
        """
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must be non-empty")
        return normalized


class InfraConfig(BaseModel):
    """Canonical root infra configuration for runtime config layer."""

    model_config = ConfigDict(extra="forbid")

    input: InputConfig
    output: OutputConfig
    producer: ProducerConfig
    observability: Optional[ObservabilityConfig] = None


__all__: List[str] = [
    "FloodControlConfig",
    "InfraConfig",
    "InputConfig",
    "InputSourceConfig",
    "LoggingConfig",
    "ObservabilityConfig",
    "OutputConfig",
    "ProducerConfig",
    "TelemetryConfig",
]
