"""汇总正式评分账本：每个候选一行。用法：python summarize_ledgers.py <formal 目录>"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
print("| 候选 | reward | F2P | P2P 失败/总数 | 参考缺席 | 安装 rc | 测试 rc | 清理 | 补丁 sha256 前缀 | grader_version |")
print("|---|---|---|---|---|---|---|---|---|---|")
for f in sorted(d.glob("ledger_*.jsonl")):
    for line in f.read_text().splitlines():
        r = json.loads(line)
        rep, c = r["report"], r["candidate"]
        sha = (c.get("patch_sha256") or "-").replace("sha256:", "")[:8]
        print(f"| {f.stem[len('ledger_'):]} | {rep['reward']} | {rep['f2p_pass']}/{rep['f2p_total']} | "
              f"{rep['p2p_fail']}/{rep['p2p_total']} | {r['reference_missing_count']} | "
              f"{r['install']['install_rc_last_command']} | {r['install']['test_rc']} | "
              f"{r['cleanup']['removed']} | {sha} | {rep['grader_version']} |")
