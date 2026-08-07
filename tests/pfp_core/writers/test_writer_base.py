"""Tests for base writer protocol contract."""

from typing import Iterable

from pfp_core.writers.writer_base import Writer


class _DummyWriter:
    writer_id = "dummy"
    content_type = "text/plain"
    file_extension = ".txt"
    encoding = "utf-8"

    def write(self, records: Iterable[object]) -> Iterable[bytes]:
        for record in records:
            yield f"{record}\n".encode(self.encoding)


def _accept_writer_contract(writer: Writer) -> bytes:
    return b"".join(writer.write(["ok"]))


def test_writer_protocol_contract_is_satisfied() -> None:
    """Validate that a writer-like object satisfies base protocol shape."""

    payload = _accept_writer_contract(_DummyWriter())

    assert payload == b"ok\n"
