"""DVC5839 行为裁决：`dvc metrics show --precision n` 的默认 / 4 / 8 × 普通 / Markdown / JSON 真实 CLI 输出（题卡待验项），
可用来比较 base / gold / 候选 / "命令层硬编码 8" 校准候选。每行 RESULT= 一个 JSON。需要 actor 侧 pathspec 兼容
（公开镜像 pathspec 0.12.1 会让 CLI 报错；用 actor_dvc5839_v1 派生镜像运行本脚本）。"""
import json
import os
import subprocess
import tempfile

YAML = "mae: 1.4832495253358502e-05\nmse: 5.0172572763074186e-09\n"


def run(args):
    env = dict(os.environ, DVC_TEST="true", PYTHONPATH="/testbed")
    p = subprocess.run(["python", "-m", "dvc", "metrics", "show", "metrics.yaml", *args], capture_output=True, text=True, env=env, timeout=300)
    return p.returncode, (p.stdout + p.stderr).strip()[-400:]


d = tempfile.mkdtemp()
open(os.path.join(d, "metrics.yaml"), "w").write(YAML)
os.chdir(d)
cases = {
    "default": [], "precision4": ["--precision", "4"], "precision8": ["--precision", "8"],
    "precision8_md": ["--precision", "8", "--show-md"], "precision8_json": ["--precision", "8", "--show-json"],
    "precision2": ["--precision", "2"],
}
for name, args in cases.items():
    rc, out = run(args)
    print("RESULT=" + json.dumps({"case": name, "value": out, "rc": rc,
                                  "basis": "公开需求：默认 5 位小数、--precision n 生效（小数点后 n 位）、JSON 保留原值；题面原例 precision 8 → 1.483e-05 / 1e-08"}, ensure_ascii=False))
