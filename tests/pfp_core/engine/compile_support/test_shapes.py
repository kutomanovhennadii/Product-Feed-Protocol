from pfp_core.engine.compile_support.shapes import as_mapping


def test_as_mapping_returns_mapping_or_none() -> None:
    assert as_mapping({"a": 1}) == {"a": 1}
    assert as_mapping([1, 2]) is None
