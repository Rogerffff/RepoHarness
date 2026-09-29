"""给公开读者的命令清单前面加协调者的标准 env 命令（与第二批相同：解释器、包来源、pip / pytest 版本、
/rh2/bash_env 对 agent 是否可写、工作区初态），写到 <out>/<iid>.json。用法：add_env_cmd.py <commands.json> <iid> <out_dir>"""
import json
import sys
from pathlib import Path

MOD = {"aiohttp": "aiohttp", "coveragepy": "coverage", "datalad": "datalad", "numpy": "numpy", "orange3": "Orange",
       "pandas": "pandas", "pillow": "PIL", "scrapy": "scrapy"}
src, iid, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
mod = MOD[iid.split("__")[0]]
env = {"id": "env", "timeout_s": 240, "expect": "zero", "purpose": "协调者标准命令：解释器、包来源、pip / pytest 版本、激活文件、工作区初态",
       "cmd": ("id; echo VIRTUAL_ENV=$VIRTUAL_ENV; echo RH2_BASHENV_WRITE=$( ( : >> /rh2/bash_env ) 2>/dev/null && echo WRITABLE || echo DENIED ); "
               "python -c 'import sys; print(\"RH2_SYS_EXECUTABLE=\"+sys.executable)'; "
               f"python -c 'import {mod}; print(\"{mod}\", getattr({mod}, \"__version__\", \"?\"), {mod}.__file__)'; "
               "python -m pip --version 2>&1 | head -1; python -m pytest --version 2>&1 | head -1; git status --porcelain=v1; echo PORCELAIN_RC=$?")}
cmds = json.loads(Path(src).read_text())
assert not any(c["id"] == "env" for c in cmds), "清单里已有 env"
out.mkdir(parents=True, exist_ok=True)
(out / f"{iid}.json").write_text(json.dumps([env] + cmds, ensure_ascii=False, indent=1))
print(len(cmds) + 1)
