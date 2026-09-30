"""构造本题的隐藏测试修订草案（R2E hidden_test_text_replace / expected_file_replace 形式）。

所有 edit 都作用在原隐藏测试 test_1.py（sha256 ee874f37…）上，按顺序替换、每处 old 恰好出现一次，
与 rh2/src/repoharness2/envpack/ingest_r2e_subset.py 的 _apply_edits 规则相同。

产物（写到本目录）：
- hidden_test_1_rc2.py      R-c v2 = 现行 r2e-mr-053 的 edit + 多文件 totals 新测试（选项 B、C 用）
- hidden_test_1_rb2.py      R-b v2 = 历史窄 R-b 草案 5 处 edit + 多文件新测试（含每文件条件核对；选项 A 用）
- expected_output_rc2.json  7 键（两版共用）
- revision_draft_rc2.json / revision_draft_rb2.json  正式条目草案（合并条目，替换 r2e-mr-053/054）
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DOCS = REPO / "docs/agentic_RL/repo_harness_rh2_workstreams"
IID = "coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96"

orig = (HERE / "hidden_test_1_original.py").read_text()
orig_expected = (HERE / "expected_output_orig.json").read_text()
sha = lambda s: "sha256:" + hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
assert sha(orig) == "sha256:ee874f37abb9e6f5307bb02b9b6a3c760218f674d557a51f7f27f5c68298418f"
assert sha(orig_expected) == "sha256:9e555e5145c096ac323d33fdd3d22d7b769a4b3a34c3cc9b92ba70c1949a384c"

mr = json.loads((DOCS / "s2_r2e/revisions/material_revisions_v11.json").read_text())
(mr053,) = [r for r in mr["revisions"] if r["revision_id"] == "r2e-mr-053"]
RC1 = (mr053["edits"][0]["old"], mr053["edits"][0]["new"])
rb_hist = json.loads((DOCS / f"project1_execution/r2e_lifecycle_20260929/results/{IID}/revision_draft_rb.json").read_text())
(rb_rev,) = rb_hist["revisions"]
RB_HIST = [(e["old"], e["new"]) for e in rb_rev["edits"]]
assert RB_HIST[0] == RC1, "历史 R-b 草案第 1 处应与 r2e-mr-053 逐字相同"

K2_END = (
    "        assert report['meta']['branch_coverage'] is True\n"
    "        assert report['totals']['covered_branches'] == 4\n"
    "        assert report['totals']['missing_branches'] == 2\n"
)
K3 = '''
    def test_branch_totals_add_up_across_files(self):
        # R2E revision (2026-09-30, R-c): like the other totals keys, the two
        # counts add up every reported file.  branchy_sum.py is BRANCHY (6
        # branch destinations, 4 taken, 2 never taken); branchy_sum_main.py is
        # the issue's one-branch example after an import (2 destinations, 1
        # taken, 1 not taken, 1 partial branch line).
        self.make_file("branchy_sum.py", self.BRANCHY)
        self.make_file("branchy_sum_main.py", """\\
            import branchy_sum
            a = {'b': 1}
            if a.get('a'):
                b = 1
            """)
        cov = coverage.Coverage(branch=True)
        main = self.start_import_stop(cov, "branchy_sum_main")
        output_path = os.path.join(self.temp_dir, "branchy_sum.json")
        cov.json_report([main, main.branchy_sum], outfile=output_path)
        with open(output_path) as result_file:
            report = json.load(result_file)
        assert sorted(report['files']) == ['branchy_sum.py', 'branchy_sum_main.py']
        totals = report['totals']
        assert totals['num_branches'] == 8
        assert totals['num_partial_branches'] == 1
        assert totals['covered_branches'] == 5
        assert totals['missing_branches'] == 3
'''
K3_RB_TAIL = '''        # R2E revision (2026-09-30, R-b): a per-file summary that also carries
        # the two counts must carry that file's own counts.
        for filename, counts in [('branchy_sum.py', (4, 2)), ('branchy_sum_main.py', (1, 1))]:
            summary = report['files'][filename]['summary']
            if 'covered_branches' in summary or 'missing_branches' in summary:
                assert (summary.get('covered_branches'), summary.get('missing_branches')) == counts
'''
EDIT_K3 = (K2_END, K2_END + K3)
EDIT_K3_RB = (K2_END, K2_END + K3 + K3_RB_TAIL)


def apply(text, edits):
    for i, (old, new) in enumerate(edits, 1):
        assert text.count(old) == 1, f"第 {i} 处 old 出现 {text.count(old)} 次"
        text = text.replace(old, new, 1)
    return text


variants = {
    "rc2": [RC1, EDIT_K3],
    "rb2": RB_HIST + [EDIT_K3_RB],
}
exp = json.loads(orig_expected)
exp.update({
    "JsonReportTest.test_branch_totals_count_branch_arcs": "PASSED",
    "JsonReportTest.test_branch_totals_from_saved_branch_data": "PASSED",
    "JsonReportTest.test_branch_totals_add_up_across_files": "PASSED",
})
exp_text = json.dumps(exp, indent=4) + "\n"
(HERE / "expected_output_rc2.json").write_text(exp_text)
added = {k: v for k, v in exp.items() if k not in json.loads(orig_expected)}

DECISION = "统一标准 v1 §5 / §9 D4（R-a 至 R-f 一次性授权：Claude 执行、Codex 复核）"
FILES = f"docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files/{IID}"
EVID = [f"docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/{IID}/result.md",
        f"docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/{IID}/evidence/"]
REASON = {
    "rc2": "R-c v2：在 r2e-mr-053 的两项之上补多文件 totals（K3）；触发反例 LF（逐文件赋值代替累加）在现行材料得 1；正对照 gold",
    "rb2": "R-c v2 + R-b 窄版 v2（仅在用户就 P5 选 A 时启用）：每文件 summary 可带两键，成对且值对；K3 另核每文件值（挡 FC）；正对照 gold",
}
for name, edits in variants.items():
    text = apply(orig, edits)
    compile(text, f"hidden_test_1_{name}.py", "exec")
    (HERE / f"hidden_test_1_{name}.py").write_text(text)
    draft = {
        "instance_id": IID,
        "status": "草案（第3类第二批，2026-09-30）；未落正式修订单" + ("；只在 P5 选 A 时启用" if name == "rb2" else ""),
        "supersedes": ["r2e-mr-053", "r2e-mr-054"],
        "note": ("同一题同一目标只许一条修订（ingest_r2e_subset.py:415-418）：隐藏测试条目整体取代 r2e-mr-053"
                 "（第 1 处 edit 与之逐字相同），期望条目整体取代 r2e-mr-054。revision_id 与 revised_file 的版本路径由第2类定；"
                 "revised_file 若沿用现有路径，会改变旧修订单引用的文件内容"),
        "revisions": [
            {"revision_id": "待第2类编号", "instance_id": IID, "kind": "hidden_test_text_replace", "target": "test_1.py",
             "edits": [{"old": o, "new": n} for o, n in edits],
             "sha256_before": sha(orig), "sha256_after": sha(text),
             "revised_file": f"{FILES}/<新版本目录>/r2e_tests/test_1.py", "expected_change": None,
             "decision_ref": DECISION, "reason": REASON[name], "evidence": EVID},
            {"revision_id": "待第2类编号", "instance_id": IID, "kind": "expected_file_replace",
             "target": "expected_output_json", "edits": None,
             "sha256_before": sha(orig_expected), "sha256_after": sha(exp_text),
             "revised_file": f"{FILES}/<新版本目录>/expected_output.json",
             "expected_change": {"changed": {}, "added": added, "removed": []},
             "decision_ref": DECISION, "reason": REASON[name], "evidence": EVID},
        ],
    }
    (HERE / f"revision_draft_{name}.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1) + "\n")
    print(name, sha(text), len(text.splitlines()), "lines")
print("expected", sha(exp_text), len(exp), "keys")

# 选项 B（R-f）的题面草稿：句子沿用 R2E 线 revision_plan.md §6.4，未经新公开读者验收
pub = [json.loads(line) for line in (DOCS / "s2_r2e/ingest/public_bundles_v0.jsonl").read_text().splitlines()
       if IID in line][0]
stmt = pub["problem_statement"]
assert sha(stmt) == pub["problem_statement_sha256"]
OLD = ("The `totals` section in `coverage.json` should include `covered_branches` and `missing_branches`, "
       "providing detailed branch coverage information.")
NEW = OLD + " The per-file `summary` entries under `files` are not part of this change and keep their current keys."
new_stmt = apply(stmt, [(OLD, NEW)])
(HERE / "revised_statement_B.txt").write_text(new_stmt)
(HERE / "revision_draft_statement_B.json").write_text(json.dumps({
    "instance_id": IID,
    "status": "草稿，只在用户就 P5 选 B 时启用；未经新公开读者验收，未经 Codex 复核",
    "revisions": [{"revision_id": "待第2类编号", "instance_id": IID, "kind": "statement_text_replace",
                   "target": "problem_statement", "edits": [{"old": OLD, "new": NEW}],
                   "sha256_before": sha(stmt), "sha256_after": sha(new_stmt), "revised_file": None,
                   "expected_change": None, "decision_ref": "待用户就 P5 选 B（v1 §3 P5：模板外，需用户决定）",
                   "reason": "R-f：写明每文件 summary 不在本题改动范围内（公开依据：tests/test_json.py:50-58 的旧形状）",
                   "evidence": EVID}],
}, ensure_ascii=False, indent=1) + "\n")
print("statement_B", sha(new_stmt))
