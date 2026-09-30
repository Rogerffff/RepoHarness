"""上游对照（只作佐证，不当公开依据）：在同一镜像里用 PYTHONPATH 加载 PyPI 发布的 Pillow wheel，
跑行为矩阵 probe_matrix.py，以及修订测试 v1 里的 test_removed_transparency 这一个函数。

用法：python run_upstream.py <输出目录> <解压后的 wheel 根目录> <版本,...>
wheel 从 PyPI 下载，sha256 与 PyPI 登记值核对后按 x<版本>/ 解压（见结论页）。每个版本先打印 PIL.__file__ 确认加载的是解压目录。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[2]
SEMCTL = RH2 / "experiments/task2_swegym_dev_20260925/semantic_control.py"
IMAGE = "c3keep/pillow_a682:src"

out = Path(sys.argv[1]).resolve()
wheel_root = Path(sys.argv[2]).resolve()
versions = sys.argv[3].split(",")
out.mkdir(parents=True, exist_ok=True)

files = {"probe_matrix.py": str(HERE / "probe_matrix.py"),
         "hidden_test_1_revised_v1.py": str(HERE / "hidden_test_1_revised_v1.py")}
commands = []
for v in versions:
    files[f"x{v}"] = str(wheel_root / f"x{v}")
    pp = f"PYTHONPATH=/in/x{v}"
    commands += [
        {"id": f"up{v}_import", "timeout_s": 120,
         "cmd": f"{pp} python -c 'import PIL; from PIL import Image; print(PIL.__version__, PIL.__file__, Image.core.__file__)'"},
        {"id": f"up{v}_probe", "timeout_s": 600, "cmd": f"rm -rf /tmp/probe && {pp} python /in/probe_matrix.py /tmp/probe 2>&1"},
        {"id": f"up{v}_rev1_fn", "timeout_s": 600,
         "cmd": ("rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests && "
                 "cp /in/hidden_test_1_revised_v1.py /testbed/r2e_tests/test_1.py && "
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
