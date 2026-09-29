"""L7 判别用例 · pydantic__pydantic-8500

F2P 用的模型是 `a: str = 'a'` / `b: str`，声明序恰好等于字母序，
所以"按字段名 sorted"的假修复与 gold 的"保持 model_fields 声明序"无法区分。
把字段声明成非字母序就能分开。

三态预期：base 失败（默认值被放到最后：{"a","b"}）、gold 通过（{"b","a"}）、fake 失败（字母序 {"a","b"}）。
"""
from pydantic import BaseModel


def test_l7_declaration_order_is_kept_when_not_alphabetical():
    class M(BaseModel):
        b: str = "b"
        a: str

    m = M.model_construct(a="a")
    assert m.model_dump_json() == '{"b":"b","a":"a"}'


def test_l7_fields_set_only_contains_supplied_fields():
    class M(BaseModel):
        b: str = "b"
        a: str

    assert M.model_construct(a="a").model_fields_set == {"a"}
