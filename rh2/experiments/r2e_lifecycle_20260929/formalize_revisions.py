#!/usr/bin/env python3
"""把修订执行者的草案（results/<题>/revision_draft.json）转成正式修订单条目，先写到暂存目录，不碰 docs/.../s2_r2e。

每条修订的前后摘要都由本脚本从"当前生效的文件"重算：隐藏测试取私有包 hidden_tests/（已含 v3 修订），期望映射取
私有包 expected_output.json，题面取公开包 public_bundle.json；草案里的摘要只用来核对。同一题同一目标若在 v3 里已有修订，
本脚本停下报冲突（要人工合并为一条新修订），不自动叠加。

用法（仓库根）：
  python3 rh2/experiments/r2e_lifecycle_20260929/formalize_revisions.py --ids <iid>[,<iid>…] --start 21 \
      --decision "统一标准 v1 §9 D4（R-a 至 R-f 一次性授权）" --codex-ref <复核文件相对路径>
产物：runs/r2e_lifecycle_20260929/staging/{new_entries.json, files/<iid>/…, summary.md}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
DOCS = "docs/agentic_RL/repo_harness_rh2_workstreams"
S2R = R / DOCS / "s2_r2e"
B = R / DOCS / "project1_execution/r2e_lifecycle_20260929"
V3 = R / "runs/r2e_static_prep_20260924/v3"
STAGE = R / "runs/r2e_lifecycle_20260929/staging"


def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def apply_edits(text: str, edits: list[dict], who: str) -> str:
    for e in edits:
        n = text.count(e["old"])
        if n != 1:
            raise SystemExit(f"{who}: edit 的 old 出现 {n} 次（必须恰好 1 次）：{e['old'][:80]!r}")
        text = text.replace(e["old"], e["new"])
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--start", type=int, required=True, help="新修订号起点（r2e-mr-NNN）")
    ap.add_argument("--decision", required=True)
    ap.add_argument("--codex-ref", required=True, help="复核文件相对路径；auto = 按仓库取 codex_reviews/review_revision_<仓库>.md；none = 全部由 --codex-ref-override 给出")
    ap.add_argument("--codex-ref-override", default="", help="逗号分隔的 <instance_id>=<复核文件相对路径>，追加在该题证据里（如小改后的复核）")
    ap.add_argument("--defer-statement", default="", help="逗号分隔的 instance_id：草案里的 statement_edits 待用户决定，本轮只落测试与期望修订")
    ns = ap.parse_args()

    sys.path.insert(0, str(R / "rh2/src"))
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs

    trusted = load_trusted_r2e_ingest_outputs(R)
    grad = {g.instance_id: g for g in trusted.result.grading_bundles}
    from repoharness2.envpack.ingest_r2e_subset import R2E_MATERIAL_REVISIONS_RELPATH

    v3 = json.loads((R / R2E_MATERIAL_REVISIONS_RELPATH).read_text())  # 当前生效的修订单（第 1 轮是 v3，之后逐轮递增）
    taken = {(e["instance_id"], e["target"]) for e in v3["revisions"]}
    STAGE.mkdir(parents=True, exist_ok=True)
    out, summary, n = [], [], ns.start
    deferred = set(filter(None, ns.defer_statement.split(",")))
    for iid in ns.ids.split(","):
        d = json.loads((B / "results" / iid / "revision_draft.json").read_text())
        assert d["instance_id"] == iid, iid
        priv, pub = V3 / "private" / iid, V3 / "public" / iid
        codex_ref = ns.codex_ref
        if codex_ref == "auto":
            codex_ref = f"{DOCS}/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_{iid.split('__')[0]}.md"
        extra_refs = [v for k, v in (x.split("=", 1) for x in filter(None, ns.codex_ref_override.split(","))) if k == iid]
        if codex_ref == "none":  # 每题的复核文件全部由 --codex-ref-override 给出
            if not extra_refs:
                raise SystemExit(f"{iid}: --codex-ref none 时必须用 --codex-ref-override 给出本题的复核文件")
            codex_ref, extra_refs = extra_refs[0], extra_refs[1:]
        for ref in [codex_ref, *extra_refs]:
            if not (R / ref).is_file():
                raise SystemExit(f"{iid}: 复核文件 {ref} 不存在")
        evidence = [f"{DOCS}/project1_execution/r2e_lifecycle_20260929/results/{iid}/revision_plan.md",
                    f"{DOCS}/project1_execution/r2e_lifecycle_20260929/results/{iid}/revision_draft.json",
                    f"{DOCS}/project1_execution/r2e_lifecycle_20260929/results/{iid}/trials/", codex_ref, *extra_refs]
        pc = d.get("positive_control", "gold")
        tpl = d.get("template", "?") if iid not in deferred else "R-c（只落与读法无关的测试修订；题面修订待用户决定，未落）"
        reason_head = f"{tpl}（单题闭环试行 09-29）：见 revision_plan.md；" + (
            "正对照 gold" if pc == "gold" else
            f"正对照为经独立核实的替代解 {pc}（v1 §5 / D4）；gold 在修订后测试下不满分，已记录，不因此收窄题意")
        for rev in d.get("revisions", []):
            tgt = rev["target"]
            if (iid, tgt) in taken:
                raise SystemExit(f"{iid}: 目标 {tgt} 在 v3 已有修订，需要人工合并为一条新修订")
            rid = f"r2e-mr-{n:03d}"; n += 1
            rel_file = f"{DOCS}/s2_r2e/revisions/files/{iid}/r2e_tests/{tgt}"
            dst = STAGE / "files" / iid / "r2e_tests" / tgt
            dst.parent.mkdir(parents=True, exist_ok=True)
            if rev["kind"] == "hidden_test_text_replace":
                before = (priv / "hidden_tests" / tgt).read_bytes()
                recorded = {f.path: f.sha256 for f in grad[iid].hidden_test_files}.get(tgt)
                if recorded is None or sha(before) != "sha256:" + recorded.removeprefix("sha256:"):
                    raise SystemExit(f"{iid}/{tgt}: 私有包文件摘要 {sha(before)[:19]} 与正式评分面记录 {str(recorded)[:19]} 不符")
                after = apply_edits(before.decode("utf-8"), rev["edits"], f"{iid}/{tgt}").encode("utf-8")
                ent = {"revision_id": rid, "instance_id": iid, "kind": rev["kind"], "target": tgt, "edits": rev["edits"],
                       "sha256_before": sha(before), "sha256_after": sha(after), "revised_file": rel_file, "expected_change": None}
            elif rev["kind"] == "hidden_test_file_add":
                if (priv / "hidden_tests" / tgt).exists():
                    raise SystemExit(f"{iid}: 新增文件 {tgt} 已存在")
                after = rev["content"].encode("utf-8")
                ent = {"revision_id": rid, "instance_id": iid, "kind": rev["kind"], "target": tgt, "edits": None,
                       "sha256_before": None, "sha256_after": sha(after), "revised_file": rel_file, "expected_change": None}
            else:
                raise SystemExit(f"{iid}: 未知修订类 {rev['kind']}")
            dst.write_bytes(after)
            want = d.get("revised_hidden_test_sha256")
            if want and rev["kind"] == "hidden_test_text_replace" and ent["sha256_after"] != "sha256:" + want.removeprefix("sha256:"):
                summary.append(f"- 注意 {iid}/{tgt}：重算摘要 {ent['sha256_after'][:19]} 与草案 {want[:12]} 不同，核对是否一题多条修订")
            ent.update(decision_ref=ns.decision, reason=reason_head, evidence=evidence)
            out.append(ent)
            summary.append(f"- {rid} {iid[:24]} {rev['kind']} {tgt}：{ent['sha256_before'] and ent['sha256_before'][:19]} → {ent['sha256_after'][:19]}")
        exp_after = d.get("expected_after")
        if exp_after is not None:
            cur_text = grad[iid].expected_output_json
            cur = json.loads(cur_text)
            if exp_after != cur:
                if (iid, "expected_output_json") in taken:
                    raise SystemExit(f"{iid}: 期望映射在 v3 已有修订，需要人工合并")
                rid = f"r2e-mr-{n:03d}"; n += 1
                body = json.dumps(exp_after, ensure_ascii=False, indent=4).encode("utf-8")
                dst = STAGE / "files" / iid / "expected_output.json"
                dst.write_bytes(body)
                change = {"changed": {k: [cur[k], exp_after[k]] for k in cur if k in exp_after and cur[k] != exp_after[k]},
                          "added": {k: v for k, v in exp_after.items() if k not in cur},
                          "removed": sorted(k for k in cur if k not in exp_after)}
                out.append({"revision_id": rid, "instance_id": iid, "kind": "expected_file_replace", "target": "expected_output_json",
                            "edits": None, "sha256_before": sha(cur_text.encode("utf-8")), "sha256_after": sha(body),
                            "revised_file": f"{DOCS}/s2_r2e/revisions/files/{iid}/expected_output.json", "expected_change": change,
                            "decision_ref": ns.decision, "reason": reason_head, "evidence": evidence})
                summary.append(f"- {rid} {iid[:24]} expected_file_replace：改 {len(change['changed'])} 增 {len(change['added'])} 删 {len(change['removed'])}")
        if d.get("statement_edits") and iid in deferred:
            summary.append(f"- 注意 {iid[:24]}：草案里的 {len(d['statement_edits'])} 处题面修订待用户决定，本轮未落")
        elif d.get("statement_edits"):
            raise SystemExit(f"{iid}: 题面修订请单独处理（需新公开读者验收），本脚本不落")
    (STAGE / "new_entries.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    (STAGE / "summary.md").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
