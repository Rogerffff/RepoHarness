from stats_utils import average


def test_average_non_empty():
    assert average([2.0, 4.0, 6.0]) == 4.0

def test_average_empty():
    assert average([]) == 0.0
