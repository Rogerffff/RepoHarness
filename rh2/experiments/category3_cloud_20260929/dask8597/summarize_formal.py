"""汇总正式评分账本（原材料或修订版诊断评分）。

用法：python summarize_formal.py <formal 目录>
每个 ledger_<候选>.jsonl 第 1 行：reward、F2P、P2P 失败数、参考缺席、安装 rc、测试 rc、清理、grader 版本；
再从对应评分日志取两项非参考公开旧测试的状态，以及 F2P 失败时的第一条 `E ` 行。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

NONREF = ("test_getitem_avoids_large_chunks", "test_slicing_integer_no_warnings")
F2P = "test_slice_array_null_dimension"


def main():
    d = Path(sys.argv[1])
    rows = []
    for led in sorted(d.glob("ledger_*.jsonl")):
        name = led.stem[len("ledger_"):]
        r = json.loads(led.read_text().splitlines()[0])
        rep = r.get("report") or {}
        cand = r.get("candidate") or {}
        origin = cand.get("origin") or cand.get("kind")
        sha = (cand.get("patch_sha256") or "").replace("sha256:", "")[:8] or None
        if not sha and origin and origin != "noop" and Path(str(origin)).is_file():
            sha = hashlib.sha256(Path(origin).read_bytes()).hexdigest()[:8]
        log_path = (r.get("log") or {}).get("path")
        log_text = Path(log_path).read_text(errors="replace") if log_path and Path(log_path).is_file() else ""
        st = {}
        for m in re.finditer(r"^(PASSED|FAILED|ERROR) dask/array/tests/test_slicing.py::(\S+)", log_text, re.M):
            st.setdefault(m.group(2), m.group(1))
        first_e = None
        sec = re.search(r"_{3,} " + F2P + r" _{3,}(.*?)(?=^_{3,} |^=+ )", log_text, re.S | re.M)
        if sec:
            e = re.search(r"^E +(.*)$", sec.group(1), re.M)
            first_e = e.group(1)[:160] if e else None
        tail = re.findall(r"^=+ (\d+ (?:passed|failed).*?) in [\d.]+s", log_text, re.M)
        inst = r.get("install") or {}
        rows.append({
            "cand": name, "sha256_8": sha, "reward": rep.get("reward"),
            "f2p": f"{rep.get('f2p_pass')}/{rep.get('f2p_total')}", "p2p_fail": rep.get("p2p_fail"),
            "p2p_total": rep.get("p2p_total"), "ref_missing": r.get("reference_missing_count"),
            "install_rc": inst.get("install_rc_last_command"), "test_rc": inst.get("test_rc"),
            "cleanup": (r.get("cleanup") or {}).get("removed"), "stage_error": r.get("stage_error"),
            "grader": rep.get("grader_version"),
            "nonref": {k: st.get(k) for k in NONREF}, "f2p_first_E": first_e,
            "pytest_tail": tail[-1] if tail else None,
        })
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
