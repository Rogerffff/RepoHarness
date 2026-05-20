from range_spec import RangeSpec


def test_closed_range_includes_both_edges():
    spec = RangeSpec.parse("[1,3]")

    assert spec.contains(1)
    assert spec.contains(2)
    assert spec.contains(3)


def test_open_upper_range_excludes_upper_edge():
    spec = RangeSpec.parse("[1,3)")

    assert spec.contains(1)
    assert spec.contains(2)
    assert not spec.contains(3)


def test_open_lower_range_excludes_lower_edge():
    spec = RangeSpec.parse("(1,3]")

    assert not spec.contains(1)
    assert spec.contains(2)
    assert spec.contains(3)


def test_open_range_excludes_both_edges():
    spec = RangeSpec.parse("(1,3)")

    assert not spec.contains(1)
    assert spec.contains(2)
    assert not spec.contains(3)
