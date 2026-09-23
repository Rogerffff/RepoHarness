"""只读对照 53 + 6 条既有真机日志：本次正常完成短路是否改变形状判定。"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "matrix"))
import probe_pytest_shapes as probe
import repoharness2.grading.manager as m

rows = []
missing = []
for relative in (
    "runs/swe_grading_wiring_20260915/e2/ledger_e2_A.jsonl",
    "runs/swe_grading_wiring_20260915/e2/ledger_e2_B.jsonl",
    "runs/chainfix_20260919/replay/ledger_dvc2141.jsonl",
    "runs/chainfix_20260919/replay/ledger_pa2_broken_q.jsonl",
):
    ledger = probe.ROOT / relative
    for n, text in enumerate(ledger.read_text().splitlines(), 1):
        r = json.loads(text)
        log_ref = r.get("log") or {}
        if not log_ref.get("path"):
            continue
        path = ledger.parent / "eval_logs" / Path(log_ref["path"]).name
        if not path.is_file():
            missing.append({"ledger": relative, "row": n, "log": path.name})
            continue
        data = path.read_bytes()
        log = data.decode()
        rc = (r.get("install") or {}).get("test_rc")
        normal = m.outer_session_completed_normally(m._candidate_test_segment(log) or "")
        shape = m.classify_execution_failure_shape(log, rc, zero_parsed=False)
        original = m.outer_session_completed_normally
        try:
            m.outer_session_completed_normally = lambda _: False
            old_shape = m.classify_execution_failure_shape(log, rc, zero_parsed=False)
        finally:
            m.outer_session_completed_normally = original
        checksum = "sha256:" + hashlib.sha256(data).hexdigest()
        rows.append({"ledger": relative, "row": n, "instance_id":r.get("instance_id"), "log": str(path.relative_to(probe.ROOT)),
            "sha256":checksum, "ledger_checksum_matches":log_ref.get("sha256") == checksum,
            "test_rc":rc, "reported_category":(r.get("report") or {}).get("failure_category"),
            "normal":normal, "new_shape":shape, "previous_shape":old_shape, "shape_changed":shape!=old_shape})
out = {"scope":"reference_all_missing 分支形状的离线对照；不代替重新评分或环境复跑", "rows":rows, "missing_logs":missing}
(HERE / "saved_corpus_result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"logs":len(rows),"missing":len(missing),"checksum_mismatches":sum(not r["ledger_checksum_matches"] for r in rows),"shape_changes":sum(r["shape_changed"] for r in rows)},ensure_ascii=False))
