"""Integral smoke tests for infra `input.config` contract."""

from pathlib import Path
from typing import Tuple

import pytest

from pfp_runtime.config.infra_provider import InfraProvider


def _write_minimal_producer_files(tmp_path: Path) -> None:
    """Writes minimal schema/policy YAML files required by infra validator."""
    (tmp_path / "schema.yaml").write_text(
        'protocol_id: "x"\nschema_version: "1.0.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "policy.yaml").write_text('version: "1.0"\n', encoding="utf-8")


def _write_infra_yaml(
    tmp_path: Path,
    *,
    input_format: str,
    config_lines: Tuple[str, ...],
) -> Path:
    """Writes an infra.yaml file with `input.config` for a given format.

    Args:
        tmp_path: Temporary directory for infra.yaml.
        input_format: Value for `input.format`.
        config_lines: Pre-indented YAML lines for `input.config` section.

    Returns:
        Path to the created infra.yaml.
    """
    config_block = "\n".join(config_lines)
    text = (
        "input:\n"
        f"  format: {input_format}\n"
        "  config:\n"
        f"{config_block}\n"
        "output:\n"
        "  archive_type: local\n"
        "  archive_config: ./archive/local.yaml\n"
        "  client_type: noop\n"
        "  client_config: ./clients/noop.yaml\n"
        "producer:\n"
        "  schema_file: ./schema.yaml\n"
        "  policy_file: ./policy.yaml\n"
    )
    infra_path = tmp_path / "infra.yaml"
    infra_path.write_text(text, encoding="utf-8")
    return infra_path


@pytest.mark.parametrize(
    ("input_format", "config_lines"),
    [
        ("csv", ("    connector_mapping: ./mapping.yaml",)),
        ("jsonl", ("    connector_mapping: ./mapping.yaml",)),
    ],
)
def test_provider_loads_infra_input_format(
    tmp_path: Path,
    input_format: str,
    config_lines: Tuple[str, ...],
) -> None:
    """InfraProvider loads infra.yaml and parses input.format correctly."""
    _write_minimal_producer_files(tmp_path)
    infra_path = _write_infra_yaml(
        tmp_path,
        input_format=input_format,
        config_lines=config_lines,
    )

    infra = InfraProvider().get_infra(str(infra_path))

    assert infra.input.format == input_format
