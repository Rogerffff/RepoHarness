import pytest

from calculator import add, divide


def test_add():
    assert add(2, 3) == 5


def test_divide_regular_numbers():
    assert divide(8, 2) == 4


def test_divide_zero():
    with pytest.raises(ValueError, match="division by zero"):
        divide(8, 0)
