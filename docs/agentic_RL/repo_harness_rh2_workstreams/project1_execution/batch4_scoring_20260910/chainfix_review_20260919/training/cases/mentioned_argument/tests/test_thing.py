def load_metadata(source):
    from qualified_external_fixture import VALUE
    return VALUE
VALUE = load_metadata("src/unused.py")
def test_feature():
    assert VALUE == 1
def test_stable():
    assert VALUE > 0
