# 复核者私有模拟评分：把 run_cand.sh 的日志按测试版本切开，
# 用 RH2 移植的上游解析器（parse_log_pytest + normalize_status_map）解析，
# 同时给出上游口径（prime_calculate_reward）与 RH2 生产口径（expected_map_matches，键集并集）。
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))  # rh2/src
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest, prime_calculate_reward
from repoharness2.envpack.scoring import expected_map_matches

def grade(log_path, expmap):  # expmap: {testver: expected_json_path}
    text = open(log_path, errors="replace").read()
    out = {}
    for m in re.finditer(r"=====BEGIN (\S+) (\S+)\n(.*?)=====END \1 rc=(\d+)", text, re.S):
        tv, tsha, body, rc = m.group(1), m.group(2), m.group(3), m.group(4)
        exp_raw = open(expmap[tv]).read()
        got = normalize_status_map(parse_log_pytest(body))
        exp = normalize_status_map(json.loads(exp_raw))
        mm = expected_map_matches(exp, got)
        rh2 = 1 if (mm.keys_equal and mm.match_count == mm.total_count) else 0
        out[tv] = {"test_sha12": tsha, "prime_reward": prime_calculate_reward(body, exp_raw), "rh2_reward": rh2,
                   "n_expected": len(exp), "n_parsed": len(got),
                   "mismatch": {k: [v, got.get(k)] for k, v in exp.items() if got.get(k) != v},
                   "unexpected": sorted(set(got) - set(exp)), "pytest_rc": int(rc)}
    return out

if __name__ == "__main__":
    log = sys.argv[1]
    expmap = dict(a.split("=", 1) for a in sys.argv[2:])
    print(json.dumps(grade(log, expmap), ensure_ascii=False))
