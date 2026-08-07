from typing import Any, Mapping

from pfp_core.ext.ext_types import MappingOpSpec


def call_spec(spec: MappingOpSpec, value: Any, args: Mapping[str, Any]) -> Any:
    """Call a mapping operation spec directly without catalog integration."""
    return spec.call(value, args)
