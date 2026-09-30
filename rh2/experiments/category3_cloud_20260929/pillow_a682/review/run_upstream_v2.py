"""上游对照（只作佐证）：用 PyPI 发布的 Pillow wheel（PYTHONPATH 加载）跑复核者 v2 修订测试里的三个函数，
确认 v2 新增的检查不拒绝上游后来的实现。做法同主审的 run_upstream.py。

用法：python run_upstream_v2.py <输出目录> <解压后的 wheel 根目录> <版本,...>
wheel 的 sha256 与 PyPI 登记值、主审 evidence/upstream_check/wheels_sha256.txt 一致（见 review.md）。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[3]
SEMCTL = RH2 / "experiments/task2_swegym_dev_20260925/semantic_control.py"
IMAGE = "c3keep/pillow_a682:src"
V2 = HERE / "materials/hidden_test_1_review_v2.py"

out = Path(sys.argv[1]).resolve()
wheel_root = Path(sys.argv[2]).resolve()
versions = sys.argv[3].split(",")
out.mkdir(parents=True, exist_ok=True)

files = {V2.name: str(V2)}
commands = []
for v in versions:
    files[f"x{v}"] = str(wheel_root / f"x{v}")
    pp = f"PYTHONPATH=/in/x{v}"
    commands += [
        {"id": f"up{v}_import", "timeout_s": 120,
         "cmd": f"{pp} python -c 'import PIL; print(PIL.__version__, PIL.__file__)'"},
        {"id": f"up{v}_rv2_fn", "timeout_s": 600,
         "cmd": ("rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests && "
                 f"cp /in/{V2.name} /testbed/r2e_tests/test_1.py && "
                 f"{pp} PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' .venv/bin/python -W ignore -m pytest "
                 "-rA -p no:cacheprovider --color=no r2e_tests/test_1.py -k 'test_removed_transparency or "
                 "test_rgb_transparency or test_transparent_optimize' 2>&1 | tail -n 12; rm -rf /testbed/r2e_tests")},
    ]

while int(subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True).stdout.strip()) >= 3:
    time.sleep(20)
spec = {"image": IMAGE, "python_prefix": "/testbed/.venv", "variants": {"upstream": []},
        "files": files, "commands": commands}
spec_path = out / "spec_upstream.json"
spec_path.write_text(json.dumps(spec, indent=1))
r = subprocess.run([sys.executable, str(SEMCTL), str(spec_path), "--out", str(out)], capture_output=True, text=True)
print(r.stdout[-2000:], r.stderr[-500:])
