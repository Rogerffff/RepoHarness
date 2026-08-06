"""F2-0 纯迁移验收（05 计划切片规格）：src 唯一权威 + experiments 薄壳。

三条硬断言：
1. 壳 parity——壳导出与 src 是**同一对象**（identity，不是 equal）；
   container_train.sh 按模块路径引用的 `s1_7a_bringup.glue.generate`
   必须继续可解析（GPU 启动链硬需求）。
2. src 不反向依赖 experiments（按 import 语句扫描，文档字符串不算）。
3. 禁止双实现——壳文件不得含 class/def 定义（只许 re-export）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RH2_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RH2_ROOT / "experiments"))

SRC_SLIME = RH2_ROOT / "src" / "repoharness2" / "adapters" / "slime"
SHELL_DIR = RH2_ROOT / "experiments" / "s1_7a_bringup"
MIGRATED = {
    "capture_wire.py": "repoharness2.adapters.slime.capture_wire",
    "glue.py": "repoharness2.adapters.slime.bringup",
    "docker_sandbox.py": "repoharness2.adapters.slime.docker_sandbox",
}


def test_shell_parity_identity():
    import importlib

    from s1_7a_bringup import capture_wire as shell_cw
    from s1_7a_bringup import docker_sandbox as shell_ds
    from s1_7a_bringup import glue as shell_glue

    src_cw = importlib.import_module("repoharness2.adapters.slime.capture_wire")
    src_b = importlib.import_module("repoharness2.adapters.slime.bringup")
    src_ds = importlib.import_module("repoharness2.adapters.slime.docker_sandbox")

    # GPU 启动链的模块路径硬需求
    assert shell_glue.generate is src_b.generate
    assert shell_glue.BringupService is src_b.BringupService
    # capture 面关键名同一对象（isinstance/monkeypatch 语义不分叉）
    for name in (
        "CaptureRegistry", "PendingTurn", "install_capture_wire",
        "rh2_no_404_middleware", "build_session_guard_middleware",
    ):
        assert getattr(shell_cw, name) is getattr(src_cw, name), name
    assert shell_ds.DockerSandbox is src_ds.DockerSandbox


def test_src_never_imports_experiments():
    pattern = re.compile(r"^\s*(from|import)\s+(s1_7a_bringup|fa_bringup)\b", re.M)
    offenders = []
    for path in (RH2_ROOT / "src").rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(RH2_ROOT)))
    assert offenders == [], f"src 反向依赖 experiments：{offenders}"


def test_shells_contain_no_implementation():
    impl = re.compile(r"^\s*(class|def|async def)\s+", re.M)
    for name in MIGRATED:
        text = (SHELL_DIR / name).read_text(encoding="utf-8")
        assert not impl.search(text), f"兼容壳 {name} 含实现定义（禁止双实现）"


def test_p3_probe_lib_still_resolves():
    """P3 探针 lib 走壳导入 glue.generate——历史脚本兼容面。"""

    from p3_preflight.lib import j4c_probe  # noqa: F401 —— import 即验证
