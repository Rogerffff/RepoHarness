#!/usr/bin/env python3
"""比较两个条件下的 SWE-Gym 评分结果：逐参考 case（F2P/P2P）状态差异 + 资源/阶段事实。

用法：
  diff_runs.py --data /work/data --ledger-a /work/ledger/swegym_ledger.jsonl --tag-a default --variant-a default \
               --ledger-b /work/ledger/stage1_offline.jsonl --tag-b stage1_offline --variant-b offline --gates empty,gold

两侧均取每个 (iid, gate) 的最低 attempt；同一 attempt 重复时取账本最后一条，包括 infra 或缺失判定。
迁移产物时，用 --root-a/--root-b 指定各侧原 /work/ledger 对应的新目录。输出 Markdown：判定变化、逐 case 状态变化（参考集内）、参考集外测试数变化、
测试阶段/退出/超时/资源事件。"网络敏感"只作为"条件相关差异候选"列出，不下因果结论。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def load_rows(path: str, tag: str, variant: str, gates: set[str]) -> dict:
    out = {}
    for line_no, ln in enumerate(Path(path).read_text().splitlines(), 1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError as exc:
            raise ValueError(f"账本第 {line_no} 行不是完整 JSON：{path}") from exc
        if not isinstance(r, dict):
            raise ValueError(f"账本第 {line_no} 行不是记录对象：{path}")
        if r.get("gate") not in gates or r.get("variant") != variant:
            continue
        if (r.get("run_tag") or "default") != tag:
            continue
        k = (r["instance_id"], r["gate"])
        if k not in out or r.get("attempt", 1) <= out[k].get("attempt", 1):
            out[k] = r
    return out


def log_path_of(rec: dict, root: str | None = None) -> Path | None:
    p = rec.get("log_path")
    if not p:
        return None
    path = Path(p)
    if root is not None:
        # 显式重定位不回退到旧绝对路径，避免误读另一台机器留下的文件。
        relative = path.relative_to("/work/ledger") if path.is_absolute() else path
        if ".." in relative.parts:
            raise ValueError("log_path 含上级目录，不能按产物根重定位")
        path = Path(root) / relative
    return path


def status_map_of(rec: dict, root: str | None = None) -> dict | None:
    try:
        p = log_path_of(rec, root)
        if p is None:
            return None
        result = json.loads(p.with_name("status_map.json").read_text())
        if not isinstance(result, dict) or any(not isinstance(v, str) for v in result.values()):
            return None
        return result
    except (OSError, ValueError):
        return None


def artifact_facts(rec: dict, root: str | None) -> tuple[dict | None, str | None, list[str]]:
    """只核对保存产物，不重新评分；脚本与 status_map 仍按日志所在目录关联。"""
    issues = []
    try:
        p = log_path_of(rec, root)
    except ValueError:
        return None, None, ["log_path 无法按指定产物根重定位"]
    if p is None:
        return None, None, ["缺失 log_path，脚本/日志/status_map 对应无法验证"]
    sm = status_map_of(rec, root)
    if sm is None:
        issues.append("status_map.json 缺失、不可读或格式无效")
    try:
        digest = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
        if not rec.get("log_sha256"):
            issues.append("缺失 log_sha256，日志与账本对应无法验证")
        elif digest != rec["log_sha256"]:
            issues.append("日志 log_sha256 不匹配，日志与账本对应无法验证")
    except OSError:
        issues.append("日志缺失或不可读，日志与账本对应无法验证")
    try:
        script_digest = "sha256:" + hashlib.sha256(p.with_name("eval.sh").read_bytes()).hexdigest()
    except OSError:
        script_digest = None
        issues.append("eval.sh 缺失或不可读，脚本/日志对应无法验证")
    return sm, script_digest, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/work/data")
    ap.add_argument("--ledger-a", required=True)
    ap.add_argument("--root-a", help="A 侧原 /work/ledger 对应的产物根目录")
    ap.add_argument("--tag-a", default="default")
    ap.add_argument("--variant-a", default="default")
    ap.add_argument("--ledger-b", required=True)
    ap.add_argument("--root-b", help="B 侧原 /work/ledger 对应的产物根目录")
    ap.add_argument("--tag-b", required=True)
    ap.add_argument("--variant-b", default="offline")
    ap.add_argument("--gates", default="empty,gold")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    gates = set(args.gates.split(","))
    refs = {}
    for ln in open(Path(args.data) / "grading_bundles_v2_v0.jsonl"):
        b = json.loads(ln)
        f2p = b["fail_to_pass"] if isinstance(b["fail_to_pass"], list) else json.loads(b["fail_to_pass"])
        p2p = b["pass_to_pass"] if isinstance(b["pass_to_pass"], list) else json.loads(b["pass_to_pass"])
        refs[b["instance_id"]] = (f2p, p2p)
    A = load_rows(args.ledger_a, args.tag_a, args.variant_a, gates)
    B = load_rows(args.ledger_b, args.tag_b, args.variant_b, gates)
    expected = {(iid, gate) for iid in refs for gate in gates}
    keys = sorted(set(A) | set(B) | expected)
    lines = [
        f"# 条件对照：A=({args.tag_a},{args.variant_a}) vs B=({args.tag_b},{args.variant_b})\n",
        f"A 账本：`{args.ledger_a}`；产物根：`{args.root_a or '使用账本原路径'}`。",
        f"B 账本：`{args.ledger_b}`；产物根：`{args.root_b or '使用账本原路径'}`。\n",
        "选择规则：两侧均取每个 (task, gate) 的最低 attempt；同一 attempt 重复时取账本最后一条，保留 infra 和缺失判定。",
        "范围：数据文件中的任务 × 指定 gate，并保留账本额外任务；两侧均缺记录也列为未验证。",
        "差异仅为条件相关候选。网络、主机、镜像和运行条件可能同时变化；本报告不证明主机相同，也不据此认定网络因果。",
        "证据边界：日志按 log_sha256 核对；eval.sh 与 status_map 按同目录关联。历史账本未记录执行脚本摘要或 status_map 摘要，无法独立证明二者与执行一一对应；official_script_sha256 是未加观测标记的官方脚本摘要，不能代替 eval.sh 摘要。未重新运行官方解析器。\n",
        f"共同 (task, gate)：{len(set(A) & set(B))}；仅 A：{len(set(A)-set(B))}；仅 B：{len(set(B)-set(A))}；两侧均缺记录：{len(expected-set(A)-set(B))}\n",
    ]
    verdict_changes, case_changes, extra_changes, resource_notes, unverified = [], [], [], [], []
    tally = Counter()
    for iid, gate in keys:
        a, b = A.get((iid, gate), {}), B.get((iid, gate), {})
        ma, script_a, issues_a = artifact_facts(a, args.root_a) if a else (None, None, ["缺失账本记录"])
        mb, script_b, issues_b = artifact_facts(b, args.root_b) if b else (None, None, ["缺失账本记录"])
        for rec, issues in ((a, issues_a), (b, issues_b)):
            if rec:
                if not rec.get("result"):
                    issues.append("缺失 result")
                elif str(rec["result"]).startswith("infra"):
                    issues.append(f"基础设施失败：{rec['result']}")
                if rec.get("official_verdict") is None or (rec.get("strict") or {}).get("strict_full") is None:
                    issues.append("缺失 official/strict 判定")
        if iid not in refs:
            issues_a.append("数据文件中缺失参考 case 集合")
        comparable = not issues_a and not issues_b
        va, vb = a.get("official_verdict"), b.get("official_verdict")
        sa, sb = (a.get("strict") or {}).get("strict_full"), (b.get("strict") or {}).get("strict_full")
        if not comparable:
            tally["unverified"] += 1
            unverified.append((iid, gate, a.get("result", "MISSING"), b.get("result", "MISSING"), issues_a, issues_b))
        elif va != vb or sa != sb:
            verdict_changes.append((iid, gate, va, sa, vb, sb))
            tally["verdict_changed"] += 1
        else:
            tally["verdict_same"] += 1
        if comparable:
            tally["cases_compared"] += 1
            f2p, p2p = refs.get(iid, ([], []))
            for kind, cases in (("F2P", f2p), ("P2P", p2p)):
                for cse in cases:
                    xa, xb = ma.get(cse, "MISSING"), mb.get(cse, "MISSING")
                    if xa != xb:
                        case_changes.append((iid, gate, kind, cse, xa, xb))
            refset = set(f2p) | set(p2p)
            ea = {k for k in ma if k not in refset}
            eb = {k for k in mb if k not in refset}
            fa = Counter(ma[k] for k in ea)
            fb = Counter(mb[k] for k in eb)
            if fa != fb:
                extra_changes.append((iid, gate, dict(fa), dict(fb)))
        # 阶段 / 资源事实
        note = {}
        for f in ("result", "attempt", "rc_setup", "rc_install", "rc_test", "t_setup", "t_install", "t_test", "t_eval_total", "eval_rc", "timed_out", "test_patch_applied", "official_parse", "conditions", "source_revision", "fork_commit", "image_digest_actual", "official_script_sha256"):
            if a.get(f) != b.get(f):
                note[f] = (a.get(f), b.get(f))
        if script_a != script_b:
            note["保存的 eval.sh 摘要"] = (script_a, script_b)
        for side, rec in (("A", a), ("B", b)):
            resources = {f: rec[f] for f in ("mem_peak_bytes", "mem_peak_source", "oom_kill_events", "oom_killed_flag", "shm_size_bytes", "log_signatures") if f in rec}
            if resources:
                note[f"{side} 资源事实"] = resources
        if note:
            resource_notes.append((iid, gate, note))
    lines.append(f"产物可核对且判定值相同 {tally['verdict_same']}，判定变化 {tally['verdict_changed']}；未验证 {tally['unverified']}（不计为无差异）。\n")
    lines.append(f"参考 case 已比较 {tally['cases_compared']} 对 (task, gate)，观察到 {len(case_changes)} 个状态变化；结论受上述脚本与 status_map 关联边界限制。\n")
    lines.append("## 缺失 / 基础设施失败 / 无法验证\n")
    lines.append("| task | gate | A result | B result | A 问题 | B 问题 |")
    lines.append("|---|---|---|---|---|---|")
    for iid, gate, ra, rb, ia, ib in unverified:
        lines.append(f"| {iid} | {gate} | {ra} | {rb} | {'；'.join(ia) or '无'} | {'；'.join(ib) or '无'} |")
    lines.append("\n## 判定变化（条件相关差异候选）\n")
    lines.append("| task | gate | A official/strict | B official/strict |")
    lines.append("|---|---|---|---|")
    for x in verdict_changes:
        lines.append(f"| {x[0]} | {x[1]} | {x[2]}/{x[3]} | {x[4]}/{x[5]} |")
    lines.append("\n## 参考 case 逐 ID 状态变化\n")
    lines.append("| task | gate | 集合 | case | A | B |")
    lines.append("|---|---|---|---|---|---|")
    for x in case_changes:
        case_display = x[3].replace("|", "&#124;").replace("\n", "\\n")
        lines.append(f"| {x[0]} | {x[1]} | {x[2]} | `{case_display}` | {x[4]} | {x[5]} |")
    lines.append("\n## 参考集外测试状态计数变化（旁路记录）\n")
    lines.append("| task | gate | A 计数 | B 计数 |")
    lines.append("|---|---|---|---|")
    for x in extra_changes:
        lines.append(f"| {x[0]} | {x[1]} | {x[2]} | {x[3]} |")
    lines.append("\n## 阶段 / 退出 / 资源事实（含未验证记录）\n")
    for x in resource_notes:
        lines.append(f"- {x[0]} {x[1]}: {json.dumps(x[2], ensure_ascii=False)}")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
