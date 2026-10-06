"""只读CPU语义探针：读取捕获正文；隔离执行Scrapy纯Python节点，不导入项目。

这不是Docker/RH2评分重跑。Scrapy的四个响应类只作为相异的类型标记，
six只提供text_type/iteritems；其它执行节点来自本题原件，候选替换仅在内存。
"""

import ast
import io
import json
import mimetypes
import platform
import types
import unittest
import unittest.mock
import zlib
from pathlib import Path


ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
PREP = ROOT / "runs/r2e_static_prep_20260924/v2"
GR = ROOT / "runs/r2e_actor_20260925/grader"
IID = "scrapy__9a15fcf89a151811de8ac783419df0512c863d5e"
WORK = PREP / "public" / IID / "worktree"


def check_body(body):
    """本例的chunked正文解析；不要求固定压缩字节或固定分帧。"""
    offset = 0
    pieces = []
    sizes = []
    try:
        while True:
            end = body.index(b"\r\n", offset)
            size = int(body[offset:end].split(b";", 1)[0], 16)
            assert size >= 0, "negative chunk"
            offset = end + 2
            sizes.append(size)
            if size == 0:
                # 本例没有主动设置trailer；允许合法的trailer行。
                while True:
                    end = body.index(b"\r\n", offset)
                    trailer = body[offset:end]
                    offset = end + 2
                    if not trailer:
                        break
                    assert b":" in trailer, "invalid trailer"
                assert offset == len(body), "bytes remain after terminating chunk"
                break
            assert len(body) >= offset + size + 2, "truncated chunk"
            pieces.append(body[offset:offset + size])
            offset += size
            assert body[offset:offset + 2] == b"\r\n", "missing chunk CRLF"
            offset += 2
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
        decoded = decoder.decompress(b"".join(pieces)) + decoder.flush()
        assert decoder.eof, "incomplete deflate stream"
        assert not decoder.unused_data and not decoder.unconsumed_tail, "extra compressed data"
        assert decoded == b"data", "decoded payload differs"
        return {"ok": True, "chunk_sizes": sizes, "decoded": repr(decoded)}
    except (ValueError, AssertionError, zlib.error) as exc:
        return {"ok": False, "chunk_sizes": sizes, "error": str(exc)}


bodies = {}
for label in ["gold", "AP1", "AP2"]:
    record = json.loads((GR / "aiohttp_c2c3" / (label + ".json")).read_text())
    bodies[label] = ast.literal_eval(record["results"]["mcve_c3_chunked"]["tail"].splitlines()[0])
bodies["synthetic_empty"] = b""
bodies["synthetic_wrong_data"] = b"1\r\nx\r\n0\r\n\r\n"
bodies["synthetic_missing_terminator"] = bodies["gold"][:-5]
# 同一压缩流改用不同的合法分帧，语义检查应接受。
payload = b"KI,I\x04\x00"
bodies["synthetic_valid_reframing"] = b"2\r\n" + payload[:2] + b"\r\n4\r\n" + payload[2:] + b"\r\n0\r\n\r\n"
aiohttp = {
    name: {
        "body": repr(body),
        "existing_C3_prefix_check_passes": not body.startswith(b"0\r\n\r\n"),
        "semantic_check": check_body(body),
    }
    for name, body in bodies.items()
}
assert aiohttp["gold"]["semantic_check"]["ok"]
assert aiohttp["AP2"]["semantic_check"]["ok"]
assert not aiohttp["AP1"]["semantic_check"]["ok"]
assert aiohttp["synthetic_valid_reframing"]["semantic_check"]["ok"]
for name in ["synthetic_empty", "synthetic_wrong_data", "synthetic_missing_terminator"]:
    assert aiohttp[name]["existing_C3_prefix_check_passes"]
    assert not aiohttp[name]["semantic_check"]["ok"]
mock = unittest.mock.Mock()
mock(b"")
literal_example = {
    "all_mock_calls": all(mock.mock_calls),
    "all_write_arguments": all(call[1][0] for call in mock.mock_calls),
}


def exec_nodes(source, names, namespace):
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    assert {node.name for node in selected} == set(names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<原件AST节点>", "exec"), namespace)


datatypes_source = (WORK / "scrapy/utils/datatypes.py").read_text()
headers_source = (WORK / "scrapy/http/headers.py").read_text()
response_source = (WORK / "scrapy/responsetypes.py").read_text()
python_source = (WORK / "scrapy/utils/python.py").read_text()
hidden_source = (PREP / "private" / IID / "hidden_tests/test_1.py").read_text()
public_header_test = (WORK / "tests/test_http_headers.py").read_text()


def replace_once(text, old, new):
    assert text.count(old) == 1
    return text.replace(old, new)


def scrapy_variant(name):
    namespace = {
        "six": types.SimpleNamespace(text_type=str, iteritems=lambda d: iter(d.items())),
        "MimeTypes": mimetypes.MimeTypes,
        "StringIO": io.StringIO,
        "unittest": unittest,
        "_BINARYCHARS": set(map(chr, range(32))) - set(["\0", "\t", "\n", "\r"]),
    }
    for cls in ["Response", "TextResponse", "XmlResponse", "HtmlResponse"]:
        namespace[cls] = type(cls, (), {})
    namespace["load_object"] = lambda value: namespace[value.rsplit(".", 1)[-1]]
    def get_data(package, filename):
        assert (package, filename) == ("scrapy", "mime.types")
        return (WORK / "scrapy/mime.types").read_bytes()
    namespace["get_data"] = get_data
    exec_nodes(datatypes_source, ["CaselessDict"], namespace)
    current_headers = headers_source
    current_response = response_source
    if name != "base":
        current_response = replace_once(
            current_response,
            "        'application/json': 'scrapy.http.TextResponse',",
            "        'application/json': 'scrapy.http.TextResponse',\n        'application/x-json': 'scrapy.http.TextResponse',",
        )
    if name == "p4_decode_bytes":
        current_response = replace_once(
            current_response, "        mimetype = content_type.split(';')[0].strip().lower()",
            "        if isinstance(content_type, bytes):\n            content_type = content_type.decode('latin-1')\n        mimetype = content_type.split(';')[0].strip().lower()",
        )
        current_response = replace_once(
            current_response, "            filename = content_disposition.split(';')[1].split('=')[1]",
            "            if isinstance(content_disposition, bytes):\n                content_disposition = content_disposition.decode('latin-1')\n            filename = content_disposition.split(';')[1].split('=')[1]",
        )
    if name == "bad_headers_str":
        current_headers = replace_once(
            current_headers,
            "        return [self._tobytes(x) for x in value]",
            "        return [self._tobytes(x).decode(self.encoding) for x in value]",
        )
    exec_nodes(current_headers, ["Headers"], namespace)
    exec_nodes(python_source, ["isbinarytext"], namespace)
    exec_nodes(current_response, ["ResponseTypes"], namespace)
    namespace["responsetypes"] = namespace["ResponseTypes"]()
    exec_nodes(hidden_source, ["ResponseTypesTest"], namespace)
    statuses = {}
    errors = {}
    for test_name in unittest.defaultTestLoader.getTestCaseNames(namespace["ResponseTypesTest"]):
        case = namespace["ResponseTypesTest"](test_name)
        try:
            getattr(case, test_name)()
            statuses[test_name] = "PASSED"
        except Exception as exc:
            statuses[test_name] = "FAILED"
            errors[test_name] = type(exc).__name__ + ": " + str(exc)
    exec_nodes(public_header_test, ["HeadersTest"], namespace)
    try:
        namespace["HeadersTest"]("test_single_value").test_single_value()
        public_status = "PASSED"
    except AssertionError as exc:
        public_status = "FAILED: " + str(exc)
    header = namespace["Headers"]({"Content-Type": "text/html"})
    return {
        "isolated_hidden_statuses": statuses,
        "errors": errors,
        "public_header_test_single_value": public_status,
        "header_value": repr(header["Content-Type"]),
        "header_value_type": type(header["Content-Type"]).__name__,
    }


scrapy = {name: scrapy_variant(name) for name in ["base", "gold", "p4_decode_bytes", "bad_headers_str"]}
assert list(scrapy["p4_decode_bytes"]["isolated_hidden_statuses"].values()).count("PASSED") == 7
assert list(scrapy["bad_headers_str"]["isolated_hidden_statuses"].values()).count("PASSED") == 7
assert scrapy["p4_decode_bytes"]["public_header_test_single_value"] == "PASSED"
assert scrapy["bad_headers_str"]["public_header_test_single_value"].startswith("FAILED")

result = {
    "scope": "只读本机CPU；aiohttp重读已有正文；Scrapy原件AST节点+响应类型标记/six桩；不构成真实RH2评分",
    "python_version": platform.python_version(),
    "aiohttp_C3": aiohttp,
    "aiohttp_literal_mock_assertion": literal_example,
    "scrapy_A_prime_counterexample": scrapy,
}
path = OUT / "semantic_probe.json"
path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"all_assertions_passed": True, "output": str(path.relative_to(ROOT)),
                  "bad_headers_isolated_hidden_passed": 7,
                  "bad_headers_public_bytes_contract": "FAILED"}, ensure_ascii=False))
