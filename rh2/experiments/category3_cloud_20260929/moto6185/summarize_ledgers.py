"""汇总正式评分账本（moto-6185）：每个候选一行，reward、F2P/P2P、参考缺席、安装、测试退出码、清理、镜像、grader 版本、
候选 sha256，以及评分日志里 F2P 失败的第一条错误。
用法：python summarize_ledgers.py <formal 目录>...
"""
import json
import re
import sys
from pathlib import Path

for d in map(Path, sys.argv[1:]):
    print(f"## {d.name}")
    print("| 候选 | reward | F2P | P2P 失败/总数 | 参考缺席 | 安装rc | 测试rc | 清理 | 派生镜像 | grader_version | 候选 sha256 | F2P 首个错误 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for lf in sorted(d.glob("ledger_*.jsonl")):
        rows = [json.loads(x) for x in lf.read_text().splitlines() if x.strip()]
        if not rows:
            print(f"| {lf.stem[7:]} | (空账本) |")
            continue
        r = rows[-1]
        rep = r["report"]
        err = ""
        logp = Path(r["log"]["path"]) if r.get("log") else None
        if logp and logp.exists():
            t = logp.read_text(errors="replace")
            i = t.find("_ test_put_item__string_as_integer_value _")
            if i >= 0 and rep.get("f2p_pass") != rep.get("f2p_total"):
                blk = t[i:]
                line = re.search(r"tests/test_dynamodb/exceptions/test_dynamodb_exceptions\.py:(\d+):", blk)
                e = re.search(r"^E\s+(.*)$", blk, re.M)
                err = ("L" + line.group(1) + " " if line else "") + (e.group(1)[:90] if e else "")
                err = err.replace("|", "/")
        print(f"| {lf.stem[7:]} | {rep['reward']} | {rep['f2p_pass']}/{rep['f2p_total']} | {rep['p2p_fail']}/{rep['p2p_total']} | "
              f"{r.get('reference_missing_count')} | {r['install'].get('install_rc_last_command')} | {r['test'].get('rc')} | "
              f"{'ok' if r['cleanup'].get('removed') else r['cleanup']} | {r['image_id_actual'][7:19]} | {rep['grader_version']} | "
              f"{(r['candidate'].get('patch_sha256') or 'noop')[7:19]} | {err} |")
