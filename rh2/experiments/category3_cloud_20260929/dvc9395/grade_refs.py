# 私有模拟 SWE F2P/P2P 判分：解析 pytest -rA 行，F2P 与 P2P 全部 PASSED 才算 1
import json, re, sys
out = open(sys.argv[1], errors="replace").read()
refs = json.load(open(sys.argv[2]))
st = {}
for m in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+?::\S+)", out, re.M):
    st[m.group(2)] = m.group(1)
f2p = {k: st.get(k) for k in refs["f2p"]}
p2p_bad = {k: st.get(k) for k in refs["p2p"] if st.get(k) != "PASSED"}
print(json.dumps({"reward": int(all(v == "PASSED" for v in f2p.values()) and not p2p_bad), "f2p": f2p,
                  "p2p_total": len(refs["p2p"]), "p2p_not_passed": p2p_bad}))
