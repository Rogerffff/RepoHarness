# 汇总一个正式评分目录下的全部账本：reward、F2P、参考缺席、应用、安装/测试 RC、清理、候选 sha256，
# 以及评分日志中第一条失败位置与原因。用法：python summarize_formal.py <formal 目录> [输出文件]
import json
import os
import re
import sys
from pathlib import Path

d = Path(sys.argv[1])
rows = []
for p in sorted(d.glob("ledger_*.jsonl")):
    row = json.loads(p.read_text().strip().splitlines()[-1])
    cand = p.name[len("ledger_"):-len(".jsonl")]
    rep, diag, ins = row["report"], row["verdict_diagnostics"], row["install"]
    logs = re.findall(r'evallog_[^"]+?\.eval\.log', json.dumps(row))
    where, reason = "", ""
    if logs:
        log = d / "eval_logs" / os.path.basename(logs[0])
        if log.exists():
            for line in log.read_text(errors="replace").splitlines():
                m = re.match(r"^(/testbed/\S+\.py):(\d+): (\w+)", line)
                if m and not where:
                    where = "{}:{}".format(os.path.basename(m.group(1)), m.group(2))
                if re.match(r"^E\s+\S", line) and not reason:
                    reason = line.strip()[:110]
    sha = (row["candidate"].get("patch_sha256") or "-").replace("sha256:", "")[:8]
    rows.append("{:20s} reward={} f2p={}/{} missing={} apply={} install_rc={} test_rc={} cleanup={} sha={} {} {}".format(
        cand, rep["reward"], rep["f2p_pass"], rep["f2p_total"], len(diag["reference_missing"]), diag["apply_ok"],
        ins["install_rc_last_command"], ins["test_rc"], row["cleanup"]["removed"], sha, where, reason))
text = "\n".join(rows) + "\n"
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(text)
print(text)
