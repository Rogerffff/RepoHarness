# 私有模拟 R2E 评分：解析 run_tests.sh 输出（pytest -rA 的 PASSED/FAILED 行），逐键对照 expected_output.json
import json, re, sys
out = open(sys.argv[1], errors="replace").read()
expected = json.load(open(sys.argv[2]))
status = {}
for m in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) r2e_tests/test_1\.py::(\w+)::(\w+)", out, re.M):
    status[f"{m.group(2)}.{m.group(3)}"] = m.group(1)
mismatch = {k: (v, status.get(k)) for k, v in expected.items() if status.get(k) != v}
extra = sorted(set(status) - set(expected))
print(json.dumps({"match": not mismatch and not extra, "n_expected": len(expected), "n_parsed": len(status),
                  "mismatch": mismatch, "unexpected": extra}))
