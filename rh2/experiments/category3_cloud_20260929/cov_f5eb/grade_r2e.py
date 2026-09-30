# 私有模拟 R2E 评分：用 RH2 移植的上游解析器（parse_log_pytest + normalize_status_map）逐键对照期望映射
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))  # rh2/src
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest, prime_calculate_reward
log = open(sys.argv[1], errors="replace").read()
exp_raw = open(sys.argv[2]).read()
got = normalize_status_map(parse_log_pytest(log))
exp = normalize_status_map(json.loads(exp_raw))
print(json.dumps({"reward": prime_calculate_reward(log, exp_raw), "n_expected": len(exp), "n_parsed": len(got),
                  "mismatch": {k: [v, got.get(k)] for k, v in exp.items() if got.get(k) != v},
                  "unexpected": sorted(set(got) - set(exp))}, ensure_ascii=False))
