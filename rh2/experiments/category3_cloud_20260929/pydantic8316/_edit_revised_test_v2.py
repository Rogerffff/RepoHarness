"""生成 pydantic-8316 修订版测试补丁 v2（R-c 草案，09-30 主审）。
做法同 v1：base tests/test_utils.py → 应用原 test_patch（新增 CAMELToSnake 参数）→ 在 test_camel2snake 函数体内，
仅对 F2P 参数 CAMELToSnake 追加断言，测试 ID 不变，17 个 P2P 参数的语义不变。
v2 = v1 的 4 条 + 3 条：
  - '__HTTPResponse__' -> '__http_response__'：缩写前后带下划线（同 P2P 的 __CamelToSnake__ 形态）；v1 放过 skip_if_underscore、lower_or_start_la；
  - 'base64URLEncode' -> 'base_64_url_encode'：数字夹在小写字母与大写字母之间，两处都断开是 P2P（camel2Snake、Camel2Snake）
    已定的约定，base 与 gold 的数字读法在此一致；v1 放过 skip_if_digit；
  - 'parseURL' -> 'parse_url'：末尾缩写仍是一个词（base、gold 都如此）；v1 放过 no_trailing_upper。
仍不断言“大写字母→数字”（base 为 a_1，gold 与上游 2.8.1 起为 a1，两种读法都有依据），也不断言单字母缩写（XAxis、OAuth）。
用法：python _edit_revised_test_v2.py <base_test_utils.py> <original_test.patch> <out.patch>
"""
import difflib
import subprocess
import sys
import tempfile
from pathlib import Path

OLD_BODY = """def test_camel2snake(value: str, result: str) -> None:
    assert to_snake(value) == result
"""
NEW_BODY = """def test_camel2snake(value: str, result: str) -> None:
    assert to_snake(value) == result
    if value == 'CAMELToSnake':
        # an acronym followed by a capitalized word is split wherever it appears, not only at the start
        assert to_snake('HTTPResponse') == 'http_response'
        assert to_snake('getHTTPResponseCode') == 'get_http_response_code'
        assert to_snake('userIDToken') == 'user_id_token'
        assert to_snake('XMLToJSONConverter') == 'xml_to_json_converter'
        # ... also next to underscores and digits, which are handled as for the other inputs
        assert to_snake('__HTTPResponse__') == '__http_response__'
        assert to_snake('base64URLEncode') == 'base_64_url_encode'
        # a trailing acronym stays one word
        assert to_snake('parseURL') == 'parse_url'
"""


def main() -> None:
    base_file, orig_patch, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    base = base_file.read_text()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "tests").mkdir()
        (tdp / "tests" / "test_utils.py").write_text(base)
        subprocess.run(["git", "init", "-q"], cwd=td, check=True)
        subprocess.run(["git", "apply", str(orig_patch.resolve())], cwd=td, check=True)
        patched = (tdp / "tests" / "test_utils.py").read_text()
    assert patched.count(OLD_BODY) == 1
    new = patched.replace(OLD_BODY, NEW_BODY)
    diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile="a/tests/test_utils.py", tofile="b/tests/test_utils.py")
    out.write_text("diff --git a/tests/test_utils.py b/tests/test_utils.py\n" + "".join(diff))
    print(out.read_text())


if __name__ == "__main__":
    main()
