import a, b
from typing_extensions import assert_type
def g(x: a.C) -> None:
    assert_type(x, b.C)
