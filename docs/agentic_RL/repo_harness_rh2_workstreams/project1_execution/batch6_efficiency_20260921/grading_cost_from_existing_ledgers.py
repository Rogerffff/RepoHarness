"""只读汇总 09-19 的 216 题基线账本；不运行题目或 Docker。

这是旧实验阶段计时，不是原容器评分的收益测量。
"""
import hashlib
import json
import statistics
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
base = ROOT / "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers"
paths = sorted(base.glob("*/ledger.jsonl"))
rows = [json.loads(line) for path in paths for line in path.read_text().splitlines() if line.strip()]
assert len(rows) == 432
result = {
    "scope": "2026-09-19 baseline01, 216 tasks x noop/gold; read-only reaggregation",
    "rows": len(rows),
    "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    "notes": [
        "One application failure has phases=null; unavailable phases are not filled with zero.",
        "Some timed-out tests have no completed test phase; n differs by phase.",
        "Phase medians cannot be added into the median of total time or claimed as savings.",
        "grader_trusted_setup and test are not wholly removable by container reuse.",
    ],
    "phases": {},
}
for field in ("grader_start_and_verify", "grader_baseline_rebuild", "delta_apply", "grader_trusted_setup", "test", "grader_cleanup"):
    values = sorted(row["phases"][field] for row in rows if isinstance((row.get("phases") or {}).get(field), (float, int)))
    result["phases"][field] = {
        "n": len(values), "p50_seconds": round(statistics.median(values), 3),
        "p90_nearest_lower_seconds": round(values[int(.9 * (len(values) - 1))], 3),
        "max_seconds": round(max(values), 3), "sum_seconds": round(sum(values), 3),
    }
print(json.dumps(result, ensure_ascii=False, indent=2))
