"""为10个已审题建立显式绑定，并重放20份历史日志及碰撞反例。

生成时的表示变体只用于提出静态绑定；运行时只消费落盘的完整nodeid，不猜测。
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import re
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "rh2/src"))
from reference_bindings import ANSI, bound_states, parse_bound

OLD = REPO / "runs/full216_rh2_diagnostic_20260919"
DEST = REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_recipe_repair_20260919"
TASKS = {
    "iterative__dvc-4185", "pydantic__pydantic-8977", "getmoto__moto-5417", "getmoto__moto-5545",
    "getmoto__moto-5562", "getmoto__moto-5701", "getmoto__moto-6308",
    "pandas-dev__pandas-48106", "pandas-dev__pandas-50319", "conan-io__conan-11594",
}


def full_ids(text):
    result = set()
    for raw in text.splitlines():
        line = ANSI.sub("", raw).strip()
        m = re.match(r"^(?:PASSED|FAILED|ERROR|XFAIL) (.+)", line)
        if m:
            item = m[1].split(" - ", 1)[0]
        else:
            m = re.match(r"^(.+) (?:PASSED|FAILED|ERROR|XFAIL)(?:\s+\[\s*\d+%\])?$", line)
            if not m:
                continue
            item = m[1]
        if "::" in item:
            result.add(item)
    return result


def candidates(reference, observed):
    control = re.sub(r"\\x([\da-fA-F]{2})", lambda m: chr(int(m[1], 16)), reference)
    variants = {reference, reference.replace("\\", "\\\\")}
    for value in (reference, control):
        escaped = value.encode("unicode_escape").decode()
        variants.update((escaped, escaped.replace("\\", "\\\\")))
    matches = set()
    for full in observed:
        for variant in variants:
            if full == variant or (not reference.endswith("]") and full.startswith(variant + " ")):
                matches.add(full)
    return sorted(matches)


def main():
    for source in json.loads((OLD / "source_snapshot.json").read_text()):
        if source["path"].endswith(("/envpack/scoring.py", "/envpack/swegym_parsers.py")):
            assert hashlib.sha256((REPO / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    views = {r["instance_id"]: r["grading"] for r in map(json.loads,
             (OLD / "remote/replay/private/host_grading_views.jsonl").read_text().splitlines())}
    rows = [r for r in map(json.loads, (OLD / "zero_audit/parsed_facts.jsonl").read_text().splitlines())
            if r["campaign"] == "baseline01" and r["instance_id"] in TASKS]
    assert len(rows) == 20
    tasks, verification = {}, []
    for iid in sorted(TASKS):
        pair = {r["kind"]: r for r in rows if r["instance_id"] == iid}
        texts = {kind: (REPO / row["log_path"]).read_text() for kind, row in pair.items()}
        selected = pair["gold"]["reference_missing"]
        if iid == "conan-io__conan-11594":
            selected = views[iid]["fail_to_pass"]
        bindings = {}
        for alias in selected:
            per_kind = {k: candidates(alias, full_ids(t)) for k, t in texts.items()}
            assert per_kind["gold"] and per_kind["gold"] == per_kind["noop"], (iid, alias, per_kind)
            bindings[alias] = per_kind["gold"]
        flat = [n for g in bindings.values() for n in g]
        assert len(flat) == len(set(flat)), "不同参考不能占用同一完整case"
        tasks[iid] = {"bindings": bindings,
                      "meaning": "同一来源参考对应多个完整node时取全部通过；原测试与参考分组保留",
                      "source_logs": {k: {"path": pair[k]["log_path"], "sha256": hashlib.sha256(t.encode()).hexdigest()}
                                      for k, t in texts.items()}}
        for kind, text in texts.items():
            audit = []
            verdict = parse_bound(SimpleNamespace(**views[iid]), text, bindings, audit.append)
            assert not verdict.reference_missing, (iid, kind, verdict.reference_missing)
            assert verdict.resolved == (kind == "gold"), (iid, kind)
            assert all(audit[0]["raw_node_states"].values())
            # 重新走模型校验，避免model_copy省略校验造成假验证。
            type(verdict).model_validate(verdict.model_dump())
            verification.append({"instance_id": iid, "kind": kind, **audit[0]})
    # 真实碰撞形状：不论哪一行在末尾，一个失败就不能被另一个通过覆盖。
    group = tasks["conan-io__conan-11594"]["bindings"]
    alias, nodes = next(iter(group.items()))
    assert len(nodes) == 2
    for order in (nodes, nodes[::-1]):
        text = "\n".join(("FAILED " if n == nodes[0] else "PASSED ") + n for n in order)
        assert bound_states(text, group)[0][alias] == "FAILED"
    assert alias not in bound_states("PASSED " + nodes[0], group)[0]
    output = {"version": "reference-bindings-v1", "decision": "E04/E07, user delegated 2026-09-19",
              "tasks": tasks}
    (DEST / "reference_bindings_v1.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    evidence = REPO / "runs/env_recipe_repair_20260919/reference_bindings"
    evidence.mkdir(exist_ok=True)
    (evidence / "historical_replay.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"tasks": len(tasks), "historical_logs": len(verification),
                      "reference_groups": sum(len(x["bindings"]) for x in tasks.values()),
                      "full_nodes": sum(len(g) for x in tasks.values() for g in x["bindings"].values()),
                      "collision_order_and_missing_checks": 3}, ensure_ascii=False))


if __name__ == "__main__":
    main()
