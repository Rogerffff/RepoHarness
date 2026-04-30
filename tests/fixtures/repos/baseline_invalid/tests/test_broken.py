from broken import value


def test_unrelated_failure():
    assert value() == 2
