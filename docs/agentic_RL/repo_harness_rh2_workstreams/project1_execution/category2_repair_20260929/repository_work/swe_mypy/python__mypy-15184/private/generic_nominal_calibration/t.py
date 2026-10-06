import a, b
from typing_extensions import assert_type
def g(x: list[a.C]) -> None:
    assert_type(x, list[b.C])
