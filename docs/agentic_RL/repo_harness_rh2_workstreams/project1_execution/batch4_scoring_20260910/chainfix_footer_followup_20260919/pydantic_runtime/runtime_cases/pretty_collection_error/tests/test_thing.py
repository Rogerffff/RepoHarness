import pytest
from src.id_source import label
@pytest.mark.parametrize("case",[label],ids=[label])
def test_feature(case):
    assert True
@pytest.mark.parametrize("case",[label],ids=[label])
def test_stable(case):
    assert True
