"""只读重核四题原始账本、日志和后检；不运行容器、不导入历史包。

输出仅写本目录 evidence_audit.json。评分解析函数从当前原件 AST 提取。
TIFF 探针从公开原件提取类型推断及字段编解码函数，在内存中应用原候选。
它验证 Python 字段路径，不等同于整张 TIFF 保存/重载或正式评分。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import struct
import sys
from fractions import Fraction
from numbers import Number, Rational
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
RUN = ROOT / "runs/r2e_actor_20260925"
V3 = ROOT / "runs/r2e_static_prep_20260924/v3"
IIDS = (
    "numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb",
    "numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764",
    "pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07",
    "pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605",
)


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def compile_nodes(nodes, namespace, filename):
    nodes = copy.deepcopy(nodes)
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, filename, "exec"), namespace)


def parser_namespace():
    path = ROOT / "rh2/src/repoharness2/envpack/r2e_parsers.py"
    tree = ast.parse(path.read_text())
    names = {"parse_log_pytest", "decolor_keys", "normalize_status_map"}
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    selected += [
        n for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in {"SHORT_SUMMARY_MARKER", "_DECOLOR_RE"} for t in n.targets)
    ]
    namespace = {"re": re}
    compile_nodes(selected, namespace, relative(path))
    return namespace


def ledger_audit():
    namespace = parser_namespace()
    parse = namespace["parse_log_pytest"]
    normalize = namespace["normalize_status_map"]
    rows = []
    for path in sorted((RUN / "grader").glob("ledger_*.jsonl")):
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            row = json.loads(line)
            iid = row.get("instance_id")
            if iid not in IIDS:
                continue
            log = RUN / "grader/eval_logs" / Path(row["log"]["path"]).name
            text = log.read_text()
            segment = text.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
            observed = normalize(parse(segment))
            expected_path = V3 / "private" / iid / "expected_output.json"
            expected = normalize(json.loads(expected_path.read_text()))
            mismatch = sorted(k for k in set(expected) | set(observed) if expected.get(k) != observed.get(k))
            candidate = row["candidate"]
            patch = None
            if candidate["kind"] != "noop":
                if candidate["kind"] == "gold":
                    patch = V3 / "private" / iid / "gold.patch"
                else:
                    patch = RUN / "grader_cands" / Path(candidate["origin"]).name
            patch_matches = patch is None or digest(patch) == candidate["patch_sha256"]
            report = row["report"]
            entry = {
                "ledger": relative(path), "line": line_number, "iid": iid,
                "patch": relative(patch) if patch else None,
                "patch_hash_matches": patch_matches,
                "log": relative(log), "log_hash_matches": digest(log) == row["log"]["sha256"],
                "reward": report["reward"], "reparsed_reward": float(not mismatch),
                "reparsed_matched": sum(observed.get(k) == v for k, v in expected.items()),
                "expected_count": len(expected), "observed_count": len(observed),
                "mismatched": mismatch,
                "ledger_matches_reparse": (
                    float(not mismatch) == report["reward"]
                    and sum(observed.get(k) == v for k, v in expected.items()) == report["expected_match"]
                ),
                "image": row["image_id_actual"], "uid": row["policy"]["uid"],
                "network": row["policy"]["network"],
                "install_skipped": row["install"]["install_skipped"],
                "candidate_test_paths": row["candidate_test_like_paths"],
                "test_execution_complete": row["test"]["segment_completed"],
                "cleanup_removed": row["cleanup"]["removed"],
                "python": next((s for s in text.splitlines() if s.startswith("platform linux")), None),
            }
            assert entry["patch_hash_matches"] and entry["log_hash_matches"] and entry["ledger_matches_reparse"], entry
            rows.append(entry)
    return rows


def private_audit(ledgers):
    paths = list((RUN / "grader/numpy5e83_extra").glob("*.json"))
    for pattern in ("na5ea_sem_*.json", "p3a61_*.json", "p3ac9_*.json"):
        paths.extend((RUN / "grader/private_public_b2").glob(pattern))
    rows = []
    for path in sorted(paths):
        row = json.loads(path.read_text())
        patch_name = Path(row["gold"]).name
        if patch_name in {"none", "noop"}:
            matched = [x for x in ledgers if x["patch"] is None and x["image"] == row["image"]]
        else:
            matched = [
                x for x in ledgers if x["patch"] and x["image"] == row["image"] and
                (Path(x["patch"]).name == patch_name or (patch_name == x["iid"] + ".gold.patch" and Path(x["patch"]).name == "gold.patch"))
            ]
        # np5 的 extra2 base 没有本批 noop 正式评分，这项不可强行配对。
        rows.append({
            "path": relative(path), "sha256": digest(path), "image": row["image"],
            "patch_basename": patch_name, "user_recorded": row.get("user"),
            "network_recorded": row.get("network"),
            "apply": row.get("apply"),
            "matched_ledgers_by_image_and_name": [x["ledger"] for x in matched],
            "patch_digest_recorded": any("sha" in k and "patch" in k for k in row),
            "results": {k: {
                "rc": v["rc"], "cmd": v.get("cmd"), "stdout": v.get("stdout", v.get("tail")),
                "stderr": v.get("stderr"), "truncated": v.get("truncated"),
            } for k, v in row["results"].items()},
        })
    return rows


def patched_text(original, patch_text, filename):
    """严格按旧行号在内存里应用该文件的 unified diff，并核对每行上下文。"""
    chunks = patch_text.split("diff --git ")[1:]
    selected = [c for c in chunks if c.splitlines()[0] == f"a/{filename} b/{filename}"]
    if not selected:
        return original
    assert len(selected) == 1
    lines = original.splitlines(keepends=True)
    patch_lines = selected[0].splitlines(keepends=True)
    output, cursor, index = [], 0, 0
    while index < len(patch_lines):
        header = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", patch_lines[index])
        if not header:
            index += 1
            continue
        old_start = int(header.group(1)) - 1
        output.extend(lines[cursor:old_start])
        cursor = old_start
        index += 1
        while index < len(patch_lines) and not patch_lines[index].startswith("@@"):
            part = patch_lines[index]
            if part.startswith((" ", "-")):
                assert lines[cursor] == part[1:], (filename, cursor, lines[cursor], part)
                cursor += 1
            if part.startswith((" ", "+")):
                output.append(part[1:])
            index += 1
    output.extend(lines[cursor:])
    return "".join(output)


def tiff_probe():
    iid = IIDS[3]
    public = V3 / "public" / iid / "worktree"
    original = {name: (public / name).read_text() for name in ("PIL/TiffTags.py", "PIL/TiffImagePlugin.py")}
    candidates = {"base": None, "gold": V3 / "private" / iid / "gold.patch"}
    for key in ("K1_rational_type_5", "K2_zero_denominator_only", "K4b_tag_len_0", "RC6_gold_with_numbers_rational"):
        candidates[key] = RUN / "grader_cands" / f"pillow_3ac9_{key}.patch"
    results = {}
    for key, patch_path in candidates.items():
        patch = patch_path.read_text() if patch_path else ""
        source = {name: patched_text(text, patch, name) for name, text in original.items()}
        tags = {}
        exec(compile(source["PIL/TiffTags.py"], "public/PIL/TiffTags.py", "exec"), tags)
        namespace = {"Rational": Rational, "Number": Number, "Fraction": Fraction, "sys": sys,
                     "TagInfo": tags["TagInfo"], "TAGS_V2": tags["TAGS_V2"]}
        tree = ast.parse(source["PIL/TiffImagePlugin.py"])
        selected = [n for n in tree.body if getattr(n, "name", None) in {"IFDRational", "_limit_rational"}]
        directory = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ImageFileDirectory_v2")
        selected.extend(n for n in directory.body if getattr(n, "name", None) in {
            "_setitem", "write_rational", "load_rational", "write_signed_rational", "load_signed_rational"})
        compile_nodes(selected, namespace, "public/PIL/TiffImagePlugin.py")
        basic = next(n for n in directory.body if getattr(n, "name", None) == "_register_basic")
        writer = next(n.value for n in basic.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)
                      and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == "_write_dispatch")
        rational = namespace["IFDRational"]
        cases = [(41988, "zero", rational(0, 0)), (41988, "half", rational(1, 2)),
                 (65000, "zero", rational(0, 0)), (65000, "half", rational(1, 2)),
                 (65000, "int5", 5), (65000, "int70000", 70000)]
        rows = []
        for tag, label, value in cases:
            holder = SimpleNamespace(tagtype={}, _tags_v1={}, _tags_v2={},
                                     _pack=lambda fmt, *v: struct.pack("<" + fmt, *v),
                                     _unpack=lambda fmt, v: struct.unpack("<" + fmt, v))
            namespace["_setitem"](holder, tag, value, False)
            kind = holder.tagtype[tag]
            values = holder._tags_v2[tag]
            values = values if isinstance(values, tuple) else (values,)
            record = {"tag": tag, "value": label, "inferred_type": kind}
            try:
                if kind in (3, 4):
                    fmt = {3: "H", 4: "L"}[kind]
                    write = eval(compile(ast.Expression(writer), "public/basic_writer", "eval"), {"fmt": fmt})
                    encoded = write(holder, *values)
                    decoded = struct.unpack("<" + fmt * len(values), encoded)
                else:
                    assert kind in (5, 10)
                    name = "signed_rational" if kind == 10 else "rational"
                    encoded = namespace["write_" + name](holder, *values)
                    decoded = namespace["load_" + name](holder, encoded, False)
                record.update(encoded_hex=encoded.hex(), decoded_repr=repr(decoded),
                              decoded_type=type(decoded[0]).__name__, equals_int5=decoded == (5,),
                              numerator=getattr(decoded[0], "numerator", None),
                              denominator=getattr(decoded[0], "denominator", None))
            except Exception as exc:
                record.update(error_type=type(exc).__name__, error=str(exc))
            rows.append(record)
        results[key] = rows
    return results


if __name__ == "__main__":
    ledgers = ledger_audit()
    output = {"mode": "local_read_only_evidence_and_isolated_original_functions",
              "ledger_rows": ledgers, "private_rows": private_audit(ledgers), "tiff_field_probe": tiff_probe()}
    (HERE / "evidence_audit.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ledger_count": len(ledgers), "private_count": len(output["private_rows"]),
                      "all_ledger_checks_passed": True, "tiff_candidates": list(output["tiff_field_probe"])}, ensure_ascii=False))
