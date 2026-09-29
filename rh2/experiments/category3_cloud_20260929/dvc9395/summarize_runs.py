# 汇总 semantic_control 输出：按各候选目录重建 summary.json（避免多次运行互相覆盖），
# 并从每个命令输出中抽取 grade_refs.py 打印的 JSON 判分行，写 grades.json。
# rc.json 里是容器内管道末端命令的退出码，不代表测试结果；得分以 grades.json 为准。
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
summary, grades = {}, {}
for vd in sorted(p for p in out.iterdir() if p.is_dir()):
    rc = vd / "rc.json"
    if not rc.exists():
        continue
    summary[vd.name] = json.loads(rc.read_text())
    for f in sorted(vd.glob("*.out")):
        for line in f.read_text(errors="replace").splitlines():
            if line.startswith('{"reward"'):
                g = json.loads(line)
                grades.setdefault(vd.name, {})[f.stem] = {
                    "reward": g["reward"], "f2p": g["f2p"],
                    "p2p_not_passed": g["p2p_not_passed"], "p2p_total": g["p2p_total"]}
(out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
(out / "grades.json").write_text(json.dumps(grades, ensure_ascii=False, indent=1))
for v, g in grades.items():
    print(f"{v:16}", "  ".join(f"{k}={x['reward']}" for k, x in g.items()))
