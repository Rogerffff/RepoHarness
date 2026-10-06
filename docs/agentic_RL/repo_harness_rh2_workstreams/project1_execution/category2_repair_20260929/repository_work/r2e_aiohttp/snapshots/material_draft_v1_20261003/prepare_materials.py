"""准备 aiohttp 四题的本地草案；不发布 ingest、pins，不运行容器或模型。

从当前正式修订单续接。990 起的编号仅用于本地解析检查，发布者必须另行
分配正式编号并替换旧目标条目；本脚本只写本工作包目录。
"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
DOCS = "docs/agentic_RL/repo_harness_rh2_workstreams"
S2 = ROOT / DOCS / "s2_r2e"
EXECUTION = f"{DOCS}/project1_execution"
OUT = HERE / "materials"
SHORTS = ("4075c653", "1c1c0ea3", "240da100", "61833518")


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def replace_one(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"替换锚点必须恰好一处：{old[:80]!r}")
    return text.replace(old, new, 1)


CLEANUP_TEST = '''

def test_run_app_cleanup_error_is_observable_after_interrupt(patched_loop) -> None:
    # 清理异常可以抛给调用者，也可以交给异常处理器；两条路线均有效。
    message = "cleanup failed after interrupt"
    cleanup_reached = []
    reports = []

    async def context(app):
        yield
        cleanup_reached.append(True)
        raise RuntimeError(message)

    app = web.Application()
    app.cleanup_ctx.append(context)
    patched_loop.set_exception_handler(lambda loop, context: reports.append(context))
    raised = ""
    try:
        web.run_app(
            app, print=stopper(patched_loop), loop=patched_loop, handle_signals=False
        )
    except Exception as exc:
        raised = str(exc)

    assert cleanup_reached, "cleanup context was not reached"
    reported = any(
        message in str(context.get("exception", ""))
        or message in str(context.get("message", ""))
        for context in reports
    )
    assert message in raised or reported, "cleanup exception was silently lost"
'''

PROXY_REPRO = '''import asyncio
from unittest import mock
from aiohttp import ProxyConnector
from aiohttp.client import ClientRequest

loop = asyncio.new_event_loop()
transport, protocol = mock.Mock(), mock.Mock()
connected = loop.create_future()
connected.set_result((transport, protocol))
transport_loop = mock.Mock()
transport_loop.create_connection.return_value = connected
connector = ProxyConnector('http://proxy.example.com', loop=transport_loop)
try:
    req = ClientRequest('GET', 'http://localhost:1234/path', loop=loop)
    loop.run_until_complete(connector.connect(req))
    print(req.path)
    assert req.path == 'http://localhost:1234/path'
finally:
    connector.close()
    loop.close()
'''

DEFLATE_REPRO = '''import zlib
from unittest import mock
from aiohttp import protocol

payload = b'data'
compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
compressed_data = compressor.compress(payload) + compressor.flush()

# 检查传给 write() 的实际字节，而不是 mock.call 对象本身的真值。
transport = mock.Mock()
msg = protocol.Response(transport, 200)
msg.add_headers(('content-length', str(len(compressed_data))))
msg.add_chunking_filter(2)
msg.add_compression_filter('deflate')
msg.send_headers()
msg.write(payload)
msg.write_eof()
chunks = [call.args[0] for call in transport.write.call_args_list]
assert all(chunks), chunks

# HTTP/1.1 chunked 路径：终止块应在末尾，解压后仍有完整载荷。
transport = mock.Mock()
msg = protocol.Response(transport, 200)
msg.add_compression_filter('deflate')
msg.send_headers()
msg.write(payload)
msg.write_eof()
wire = b''.join(call.args[0] for call in transport.write.call_args_list)
headers, rest = wire.split(b'\\r\\n\\r\\n', 1)
assert b'transfer-encoding: chunked' in headers.lower()
data = []
while True:
    line, separator, rest = rest.partition(b'\\r\\n')
    assert separator, 'missing chunk size'
    size = int(line, 16)
    if size == 0:
        assert rest == b'\\r\\n', 'data after the terminating chunk'
        break
    assert len(rest) >= size + 2 and rest[size:size + 2] == b'\\r\\n'
    data.append(rest[:size])
    rest = rest[size + 2:]
assert zlib.decompress(b''.join(data), -zlib.MAX_WBITS) == payload
'''


def main() -> None:
    public_file = S2 / "ingest/public_bundles_v0.jsonl"
    grading_file = S2 / "ingest/grading_bundles_r2e_v0.jsonl"
    revision_file = S2 / "revisions/material_revisions_v11.json"
    public = {x["instance_id"]: x for x in map(json.loads, public_file.read_text().splitlines())}
    grading = {x["instance_id"]: x for x in map(json.loads, grading_file.read_text().splitlines())}
    formal = json.loads(revision_file.read_text())
    raw_file = S2 / "raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
    raw = {x["commit_hash"]: x for x in map(json.loads, raw_file.read_text().splitlines())}
    drafts, tasks = [], []
    rid = 990

    def entry(iid: str, kind: str, target: str, before: str, after: str,
              edits: list[dict] | None, revised_file: str | None = None,
              expected_change: dict | None = None) -> dict:
        nonlocal rid
        value = {
            "revision_id": f"r2e-mr-{rid}", "instance_id": iid, "kind": kind,
            "target": target, "edits": edits, "sha256_before": sha(before),
            "sha256_after": sha(after), "revised_file": revised_file,
            "expected_change": expected_change,
            "decision_ref": "统一标准 v1 R-a/R-c/R-f 与当前仓库持续负责人授权；草案未发布",
            "reason": "2026-10-03 aiohttp 续接草案；正式编号和发布由共用维护者负责",
            "evidence": [
                f"{EXECUTION}/category2_repair_20260929/r2e/r2e_inventory.md",
                str((HERE / "preparation.md").relative_to(ROOT)),
            ],
        }
        rid += 1
        drafts.append(value)
        return value

    for short in SHORTS:
        iid = next(k for k in public if k.startswith("aiohttp__" + short))
        directory = OUT / short
        directory.mkdir(parents=True, exist_ok=True)
        statement = public[iid]["problem_statement"]
        if sha(statement) != public[iid]["problem_statement_sha256"]:
            raise ValueError(f"公开题面摘要不符：{iid}")
        new_statement = statement
        task = {"instance_id": iid, "status": "draft_cpu_and_review_pending",
                "parent_public_sha256": sha(statement),
                "parent_grading": grading[iid], "draft_revision_ids": [],
                "publish_replaces": [], "local_files": {}}
        start = len(drafts)

        if short == "4075c653":
            old = '    invalid_header = "\\xffoo: bar".encode()'
            new = '    invalid_header = "\\xffoo: bar"'
            new_statement = replace_one(statement, old, new)
            entry(iid, "statement_text_replace", "problem_statement", statement,
                  new_statement, [{"old": old, "new": new}])
        elif short in ("240da100", "61833518"):
            first, fenced = statement.split("```python\n", 1)
            old_code, tail = fenced.split("```", 1)
            code = PROXY_REPRO if short == "240da100" else DEFLATE_REPRO
            ast.parse(code)
            new_statement = first + "```python\n" + code + "```" + tail
            edits = [{"old": old_code, "new": code}]
            if short == "240da100":
                notice = "The example replaces the transport connection with a completed Future, so it runs without contacting the proxy. It still exercises ProxyConnector.connect().\n\n"
                old = "**Example Code**\n\n"
                new = "**Example Code**\n\n" + notice
            else:
                notice = "The example checks actual write arguments and the HTTP/1.1 wire body without a network server. A zero-size terminating chunk is valid only at the end of the response.\n\n"
                old = "**Example Code:**\n"
                new = "**Example Code:**\n" + notice
            new_statement = replace_one(new_statement, old, new)
            edits.append({"old": old, "new": new})
            entry(iid, "statement_text_replace", "problem_statement", statement,
                  new_statement, edits)
            (directory / "public_repro.py").write_text(code)

        if short in ("1c1c0ea3", "240da100"):
            current = [x for x in formal["revisions"] if x["instance_id"] == iid]
            hidden = next(x for x in current if x["target"] == "test_1.py")
            expected = next(x for x in current if x["target"] == "expected_output_json")
            execution = json.loads(raw[iid.split("__", 1)[1]]["execution_result_content"])
            hidden_sources = list(zip(execution["test_file_names"], execution["test_file_codes"], strict=True))
            matching = [code for name, code in hidden_sources if Path(name).name == "test_1.py"]
            if len(matching) != 1:
                raise ValueError("来源必须恰好有一份 test_1.py")
            before_hidden = matching[0]
            original_hidden = before_hidden
            if sha(before_hidden) != hidden["sha256_before"]:
                raise ValueError("来源隐藏测试与正式修订父摘要不符")
            for edit in hidden["edits"]:
                before_hidden = replace_one(before_hidden, edit["old"], edit["new"])
            if sha(before_hidden) != hidden["sha256_after"]:
                raise ValueError("现有隐藏测试修订重放摘要不符")
            after_hidden = before_hidden
            edits = copy.deepcopy(hidden["edits"])
            mapping = json.loads((ROOT / expected["revised_file"]).read_text())
            after_mapping = dict(mapping)
            if short == "1c1c0ea3":
                old = "\n\nclass TestShutdown:\n"
                new = CLEANUP_TEST + old
                after_hidden = replace_one(after_hidden, old, new)
                edits.append({"old": old, "new": new})
                after_mapping["test_run_app_cleanup_error_is_observable_after_interrupt[pyloop]"] = "PASSED"
            else:
                tree = ast.parse(after_hidden)
                owner = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "HttpClientConnectorTests")
                lines = after_hidden.splitlines(keepends=True)
                for method in owner.body:
                    if not isinstance(method, ast.FunctionDef) or method.name not in ("test_tcp_connector", "test_unix_connector"):
                        continue
                    lo = min([method.lineno] + [d.lineno for d in method.decorator_list])
                    old = "".join(lines[lo - 1:method.end_lineno])
                    after_hidden = replace_one(after_hidden, old, "")
                    edits.append({"old": old, "new": ""})
                    del after_mapping["HttpClientConnectorTests." + method.name]
                if len(mapping) - len(after_mapping) != 2:
                    raise ValueError("必须只移除两项已失效的真实网络测试")
            ast.parse(after_hidden)
            original_expected = raw[iid.split("__", 1)[1]]["expected_output_json"]
            after_expected = json.dumps(after_mapping, ensure_ascii=False, indent=2) + "\n"
            parent_mapping = json.loads(original_expected)
            change = {"changed": {k: [v, after_mapping[k]] for k, v in parent_mapping.items()
                                  if k in after_mapping and v != after_mapping[k]},
                      "added": {k: v for k, v in after_mapping.items() if k not in parent_mapping},
                      "removed": [k for k in parent_mapping if k not in after_mapping]}
            future = f"{DOCS}/s2_r2e/revisions/files/{iid}/category2_20261003"
            entry(iid, "hidden_test_text_replace", "test_1.py", original_hidden,
                  after_hidden, edits, future + "/test_1.py")
            entry(iid, "expected_file_replace", "expected_output_json", original_expected,
                  after_expected, None, future + "/expected_output.json", change)
            (directory / "test_1.py").write_text(after_hidden)
            (directory / "expected_output.json").write_text(after_expected)
            (directory / "hidden_test.patch").write_text("".join(difflib.unified_diff(
                before_hidden.splitlines(True), after_hidden.splitlines(True),
                fromfile="current/test_1.py", tofile="draft/test_1.py")))
            task["publish_replaces"] = [hidden["revision_id"], expected["revision_id"]]
            task["expected_count_before"] = len(mapping)
            task["expected_count_after"] = len(after_mapping)
            task["expected_delta_from_current"] = {
                "added": {k: v for k, v in after_mapping.items() if k not in mapping},
                "removed": [k for k in mapping if k not in after_mapping],
                "changed": {k: [v, after_mapping[k]] for k, v in mapping.items()
                            if k in after_mapping and v != after_mapping[k]},
            }

        if new_statement != statement:
            (directory / "problem_statement.txt").write_text(new_statement)
            (directory / "statement.patch").write_text("".join(difflib.unified_diff(
                statement.splitlines(True), new_statement.splitlines(True),
                fromfile="current/problem_statement", tofile="draft/problem_statement")))
        task["draft_revision_ids"] = [x["revision_id"] for x in drafts[start:]]
        task["local_files"] = {p.name: sha(p.read_bytes()) for p in directory.iterdir() if p.is_file()}
        # 只存材料身份，不在准备清单重复完整私有 bundle。
        task["parent_grading"] = {k: grading[iid][k] for k in (
            "material_revisions", "hidden_tests_tree_sha256", "expected_output_json_sha256")}
        tasks.append(task)

    dump(HERE / "revision_draft.json", {
        "schema_id": formal["schema_id"],
        "purpose": "本地未发布草案；990起编号未预留。两项私有修订替换原目标条目，不直接追加；未来 revised_file 路径尚不存在。",
        "revisions": drafts,
    })
    dump(HERE / "material_manifest.json", {
        "as_of": "2026-10-03", "package_id": "r2e_aiohttp",
        "owner_thread_id": "01a0fd63-99aa-7af0-94bb-591d3c151b17",
        "published": False, "cpu_acceptance": "not_run", "independent_review": "pending",
        "sources": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (
            public_file, grading_file, revision_file, raw_file)},
        "tasks": tasks,
    })
    print(json.dumps({"tasks": len(tasks), "draft_revisions": len(drafts), "published": False}))


if __name__ == "__main__":
    main()
