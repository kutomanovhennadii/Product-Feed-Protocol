from __future__ import annotations

import copy
from pathlib import Path
from typing import Mapping

from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_registry import SchemaRegistry


def load_schema_doc(schema_path: Path) -> Mapping[str, object]:
    return parse_schema_text(schema_path.read_text(encoding="utf-8"), format="yaml")


def register_protocol_alias(
    *,
    registry: SchemaRegistry,
    base_doc: Mapping[str, object],
    protocol_id: str,
    source: str,
) -> None:
    alias_doc = copy.deepcopy(base_doc)
    header = alias_doc.get("header")
    assert isinstance(header, dict)

    schema_version = str(header.get("schema_version"))
    header["protocol_id"] = protocol_id
    filename = "{0}-{1}.yaml".format(protocol_id, schema_version)

    registry.register(
        alias_doc,
        source=source,
        filename=filename,
    )
