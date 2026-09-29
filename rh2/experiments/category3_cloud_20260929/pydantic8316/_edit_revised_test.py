"""生成 pydantic-8316 修订版测试补丁 v1（R-c 草案）。
做法：base tests/test_utils.py → 应用原 test_patch（新增 CAMELToSnake 参数）→ 在 test_camel2snake 函数体内，仅对 F2P 参数
CAMELToSnake 追加 4 条 to_snake 断言，测试 ID 不变，17 个 P2P 参数的语义不变。
用法：python _edit_revised_test.py <base_test_utils.py> <original_test.patch> <out.patch>
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
