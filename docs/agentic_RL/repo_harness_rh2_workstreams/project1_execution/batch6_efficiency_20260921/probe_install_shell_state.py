"""只执行当前渲染器的阶段包装与合成命令，验证拆开 Bash 是否保留安装段 export。"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

RELATIVE_SOURCE = Path("rh2/src/repoharness2/adapters/slime/prepared_task_face.py")
REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / RELATIVE_SOURCE).is_file())
source = (REPO / RELATIVE_SOURCE).read_bytes()
functions = [
    node for node in ast.parse(source).body
    if isinstance(node, ast.FunctionDef) and node.name in {"_v2_install_lines", "_v2_candidate_test_lines"}
]
module = ast.Module(
    body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *functions],
    type_ignores=[],
)
namespace = {
    "derive_install_cmd": lambda *_: "export RH2_REVIEW_INSTALL_STATE=present",
    "derive_test_command_for_bundle": lambda *_: 'test "${RH2_REVIEW_INSTALL_STATE-}" = present',
    "V2_EVAL_START_MARKER": "REVIEW_TEST_START",
    "V2_EVAL_END_MARKER": "REVIEW_TEST_END",
}
# 仅载入本地已审查的两个渲染函数；不导入模块或执行真实 vendor 安装命令。
exec(compile(ast.fix_missing_locations(module), str(RELATIVE_SOURCE), "exec"), namespace)  # noqa: S102
grading = SimpleNamespace(spec_vendor_id="review", repo_key_lower="review", version="review")
install = "\n".join(namespace["_v2_install_lines"](grading)) + "\n"
test = "\n".join(namespace["_v2_candidate_test_lines"](grading)) + "\n"


def run(script: str) -> dict:
    completed = subprocess.run(
        ["/bin/bash", "-c", script], capture_output=True, text=True, check=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    return {
        key: int(value)
        for line in completed.stdout.splitlines()
        if line.startswith(("RH2_INSTALL_RC=", "RH2_TEST_RC="))
        for key, value in [line.split("=", 1)]
    }


result = {
    "source": str(RELATIVE_SOURCE),
    "source_sha256": hashlib.sha256(source).hexdigest(),
    "single_shell": run(install + test),
    "separate_shells": {**run(install), **run(test)},
    "scope": "真实阶段包装 + 合成 export/test；不加载依赖、不运行 Docker、不证明完整评分链。",
}
assert result["single_shell"]["RH2_TEST_RC"] == 0
assert result["separate_shells"]["RH2_TEST_RC"] == 1
print(json.dumps(result, ensure_ascii=False, indent=2))
