"""Public writer-layer facade without concrete implementation re-exports."""

from typing import List

from pfp_core.engine.plan_types import WriterSpec
from pfp_core.writers.writer_base import Writer
from pfp_core.writers.writer_builtins import build_default_writer_registry
from pfp_core.writers.writer_registry import WriterRegistry
from pfp_core.writers.writer_types import MISSING

__all__: List[str] = [
    "MISSING",
    "Writer",
    "WriterRegistry",
    "WriterSpec",
    "build_default_writer_registry",
]
