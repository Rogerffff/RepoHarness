"""复核者修法草案 v3（只供作者与第2类参考，不是正式材料）：在作者 v2（f0b7b090…e917）的 7 条断言后追加 4 条。
做法同作者 _edit_revised_test_v2.py：base tests/test_utils.py → 应用原 test_patch → 只在 F2P 参数 CAMELToSnake 下追加断言，
测试 ID、F2P/P2P 名单与测试命令都不变。追加的 4 条各针对一个复核中找到的漏判（v2 下得 1 的错误候选）：
  - 'loadCONFIGURATIONFile'：13 个字母的缩写（全大写单词，与原 F2P 的 CAMEL 同类）→ 挡 acr_max5（作者）、w_acr_max8
  - 'convertXMLToJSONViaHTTPRequest'：一串里 3 个缩写、最后一个（HTTP）从下标 19 开始、全长 30 个字符 → 挡 w_count2、w_window8、w_len_cap
  - 'get_HTTPResponse'：缩写紧跟在串中的下划线之后 → 挡 w_mid_underscore
  - '\\u00dcberHTTPClient'（Über…）：串里有非 ASCII 字母，但缩写边界是纯 ASCII → 挡 w_skip_nonascii
四条都避开了“大写字母紧邻数字”“单字母缩写”“两个缩写直接相连”“非 ASCII 字母处在断开边界上”四类未规定的输入；
非 ASCII 用 \\u 转义写，测试文件保持纯 ASCII。
用法：python make_v3_draft.py <base_test_utils.py> <original_test.patch> <out.patch>
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
        # ... whatever its length, however many there are and wherever they appear
        assert to_snake('loadCONFIGURATIONFile') == 'load_configuration_file'
        assert to_snake('convertXMLToJSONViaHTTPRequest') == 'convert_xml_to_json_via_http_request'
        assert to_snake('get_HTTPResponse') == 'get_http_response'
        # other (non-ASCII) letters are kept as they are and do not change how the acronym is split
        assert to_snake('\\u00dcberHTTPClient') == '\\u00fcber_http_client'
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
    assert new.isascii()
    diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile="a/tests/test_utils.py", tofile="b/tests/test_utils.py")
    out.write_text("diff --git a/tests/test_utils.py b/tests/test_utils.py\n" + "".join(diff))
    print(out.read_text())


if __name__ == "__main__":
    main()
