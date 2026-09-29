#!/usr/bin/env python3
"""R2E 派生镜像的构建、复核与环境覆盖表生成（R2E 接线 R-d，DR3=A，2026-09-23）。

每题一张派生镜像：`FROM <来源镜像@manifest digest>` + `RUN bash recipe_v1.sh <修复提交>`（配方见
`scripts/r2e_derive/recipe_v1.sh`：解释器搬迁 / 隐藏测试进 root 私有目录 / git 清理；不 chown、不改入口、不装包）。
构建后在宿主侧**逐项复核**——不信配方自报，每个 facts 字段都由容器里的实测算出：

  1. 导层完整性（防 metacopy / docker commit 曾出现过的全 0 文件）：/testbed 非 .git / 非 .venv 全部文件、
     .venv 除 bin/ 与 pyvenv.cfg 外全部文件的 sha256 与来源镜像逐条相同；.venv/bin 每个文件去掉 shebang 行后
     相同、shebang 只允许 /root/.local/share/uv/python → /opt/py 的改写；符号链接只允许 python* 重指；
     git 的 HEAD / status / index / diff 摘要相同（初态脏树保留）。
  2. 隐藏测试：root 私有目录的树摘要 == 评分面 `hidden_tests_tree_sha256`（同一条 sha256sum 流水线）；
     /r2e_tests 与 /testbed/r2e_tests 不存在；沙箱身份读不到私有目录。
  3. 解释器：uid 54321 / 54322 都能执行 `.venv/bin/python`（-I -S 与普通模式），sys.path 无 /root。
  4. git：HEAD 无子提交、修复提交对象已不可得、无 ref / remote / reflog；run_tests.sh 摘要 == 评分面。
  5. 直接执行 driver 的 R2E rollout 预检脚本（agent 身份）并用同一评估函数判定。

**材料修订（2026-09-24 起）**：评分面带"隐藏测试修订"的题（用户批准的修订单）在 recipe_v1 之后多跑一步材料步骤，
把 `s2_r2e/revisions/files/…` 里修订后的全文写进私有目录：替换类写前核原文件摘要，新增类要求目标原本不存在，写后都核新摘要。
当前步骤是 `scripts/r2e_derive/material_v2.sh`（v2 起支持新增文件，例 scrapy `cfed9b66` 的夹具 egg、pandas `4ec87eb9`
的私有 conftest），配方身份 `r2e_derive_v1+material_v2`（tag 后缀 `r2e_derive_v1m2`），`recipe_sha256` 是
`{"recipe_v1.sh", "material_v2.sh", "manifest.tsv"}` 三者摘要的规范 JSON 再取 sha256（见 `material_recipe_digest`）。
`material_v1.sh` 保留不改：datalad `58ba5165` 的现有派生镜像按 `r2e_derive_v1+material_v1` 构建，身份里记着它的摘要。
只改期望原文的修订（例 `r2e-mr-001`）不动镜像，仍用 recipe_v1。

**环境配方（2026-09-24 起，`--env-pins <env_pins_v1.json>`）**：配方里登记了依赖固定的题（例：numpy `43e333e2` 把
hypothesis 固定回仓库 test_requirements 的 6.24.1）在 recipe_v1（与材料步骤）之后多跑一步 `scripts/r2e_derive/env_v1.sh`：
wheel 由宿主侧按配方的 url 下载并核 sha256，放进构建上下文，镜像里用自带的 uv 离线安装再核版本。配方身份追加
`+env_v1`（tag 后缀加 `e`），`recipe_sha256` 把 `env_v1.sh` 与 env 清单的摘要一并纳入。导层完整性比对对 `.venv` 只放行
配方里 `venv_changed_globs` 列出的路径，另加一项 `env_pins_applied` 复核安装后的版本。
环境步骤按配方条目的 `env_step` 选（缺省 `env_v1.sh`）：`env_v2.sh`（09-24 夜）只改读包版本的方式——`env_v1` 用的
`importlib.metadata` 要 Python 3.8 起才有，orange3 `9b5494e2` 是 3.7.9；`env_v2` 按 sys.path 读 dist-info 元数据，
只用标准库（`DIST_VERSIONS_PY`）。配方身份相应为 `+env_v2`（tag 后缀加 `e2`），`recipe_sha256` 里记 `env_v2.sh` 的摘要；
`env_v1.sh` 与 `+env_v1` 的身份计算逐字不变（numpy `43e333e2` 现有镜像按它构建）。

全部通过的题才写进 `overlays.jsonl`（`EnvironmentOverlayV1`，driver `run --image-overlays` 直接消费）；
`derived_image_id` 是**构建机**上的 image ID（不同 daemon 的 ID 不同，manifest digest 才是跨机身份）。

**修订依赖的环境（09-25，Codex 批次三复核 F1）**：`environment_overlay.REVISION_ENV_REQUIREMENTS` 登记了只在特定环境
配方下成立的修订（orange3 `9b5494e2` 的 `r2e-mr-020` 需要 `+env_v2`）；这类题缺对应环境步骤（没给 `--env-pins` 或步骤不对）
时构建直接失败，不产出覆盖条目。

**构建配置步骤（2026-09-29，`--sysconfig-fix`）**：recipe_v1 搬迁解释器后，解释器自带的构建配置（`_sysconfigdata_*.py`、
`pkgconfig/*.pc`）仍写着 /root 下的原前缀，解题身份编译扩展时链接不到 libpython（orange3 `4014f248`）。带这个开关时，
本次构建的每道题在 recipe_v1 之后多跑 `scripts/r2e_derive/sysconfig_v1.sh`，把 /opt/py 内文本文件里的旧前缀改到新位置；
配方身份追加 `+sysconfig_v1`、tag 后缀加 `s`，`recipe_sha256` 是 `{"base_recipe_sha256": 原配方摘要, "sysconfig_v1.sh": 脚本摘要}`
的规范 JSON 再取 sha256；复核多一项 `sysconfig_paths_relocated`（以 agent 身份读构建配置，不得再含 /root 下的 uv 前缀）。
不带开关时 Dockerfile、配方身份与复核项都与之前逐字节相同。

**同一输出目录同一时刻只允许一个构建进程**（Codex closeout F2）：覆盖表与 results.json 都是"读目录 → 整文件写回"，
两个进程交错会互相丢条目。工具用 `<out>/.build.lock` 锁住输出目录，锁在场就拒绝启动；要并行就各用独立输出目录，
结束后由单一进程 `--regenerate-overlays` 逐目录汇总（或把 facts.json 收到一个目录再汇总）。串行多次调用同一目录是安全的。

用法（从 rh2/）：
  .venv/bin/python scripts/build_r2e_derived.py --repo-root .. --out-dir /work/r2e_derived \\
      --task-ids coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae[,…]   [--platform linux/amd64]
  .venv/bin/python scripts/build_r2e_derived.py --repo-root .. --out-dir /work/r2e_derived --all
产物：<out>/<instance_id>/{context/,build.log,facts.json,integrity_base.txt,integrity_derived.txt}、
<out>/overlays.jsonl、<out>/results.json（含宿主存储驱动 / metacopy 事实与逐题耗时）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repoharness2.adapters.slime.r2e_grading_scripts import (  # noqa: E402
    R2E_PRIVATE_HIDDEN_TESTS_DIR,
    evaluate_r2e_rollout_preflight,
    render_r2e_rollout_preflight_script,
)
from repoharness2.envpack.environment_overlay import (  # noqa: E402
    EnvironmentOverlayFacts,
    EnvironmentOverlayV1,
    env_requirement_mismatch,
)
from repoharness2.envpack.ingest_r2e_subset import (  # noqa: E402
    HIDDEN_REVISION_KINDS,
    REVISION_KIND_HIDDEN_ADD,
    R2EMaterialRevision,
    load_trusted_r2e_ingest_outputs,
)

RECIPE_ID = "r2e_derive_v1"
RECIPE_PATH = Path(__file__).resolve().parent / "r2e_derive" / "recipe_v1.sh"
MATERIAL_STEP = "material_v2.sh"
MATERIAL_RECIPE_ID = "r2e_derive_v1+material_v2"
MATERIAL_TAG_SUFFIX = "r2e_derive_v1m2"
MATERIAL_PATH = Path(__file__).resolve().parent / "r2e_derive" / MATERIAL_STEP
ENV_STEP_DIR = Path(__file__).resolve().parent / "r2e_derive"
ENV_STEPS = {"env_v1.sh": ("+env_v1", "e"), "env_v2.sh": ("+env_v2", "e2")}   # 步骤脚本 → (配方身份后缀, tag 后缀)
DEFAULT_ENV_STEP = "env_v1.sh"
ENV_PINS_SCHEMA_ID = "rh2.r2e_env_pins.v1"
UVROOT = "/root/.local/share/uv/python"
# 构建配置步骤（2026-09-29）：见文档串"构建配置步骤"一段
SYSCONFIG_STEP = "sysconfig_v1.sh"
SYSCONFIG_ID_SUFFIX = "+sysconfig_v1"
SYSCONFIG_TAG_SUFFIX = "s"
SYSCONFIG_CHECK_PY = (
    "import json, sysconfig as s; v = s.get_config_vars(); "
    "bad = sorted(k for k, x in v.items() if isinstance(x, str) and '/root/.local/share/uv' in x); "
    "print(json.dumps({'bad': bad, 'LIBDIR': v.get('LIBDIR'), 'INCLUDEPY': v.get('INCLUDEPY')}))"
)

# 读包版本（只用标准库，Python 3.x 通用；importlib.metadata 要 3.8 起才有）：按 sys.path 逐项找 *.dist-info/METADATA
# 与 *.egg-info 的 Name/Version，每个参数打印一行 "<分发名>=<版本,…|absent>"；同名多份时按 sys.path 顺序逗号分隔，
# 调用方把它当作与配方不符。env_v2.sh 的 CODE 与本段逐字相同（测试核对）。
DIST_VERSIONS_PY = """\
import os, re, sys
def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()
seen, found = set(), {}
for entry in sys.path:
    base = entry or os.getcwd()
    try:
        names = sorted(os.listdir(base))
    except OSError:
        continue
    for name in names:
        path = os.path.join(base, name)
        if name.endswith(".dist-info"):
            meta = os.path.join(path, "METADATA")
        elif name.endswith(".egg-info"):
            meta = os.path.join(path, "PKG-INFO") if os.path.isdir(path) else path
        else:
            continue
        real = os.path.realpath(meta)
        if real in seen or not os.path.isfile(meta):
            continue
        seen.add(real)
        fields = {}
        with open(meta, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    break
                key, sep, value = line.partition(":")
                if sep and key in ("Name", "Version") and key not in fields:
                    fields[key] = value.strip()
        found.setdefault(norm(fields.get("Name", "")), []).append(fields.get("Version", "?"))
for dist in sys.argv[1:]:
    print(dist + "=" + (",".join(found.get(norm(dist), [])) or "absent"))
"""
AGENT_UID, GRADER_UID = 54321, 54322

DOCKERFILE = """\
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG FIX_COMMIT
COPY recipe_v1.sh /rh2_build/recipe_v1.sh
RUN bash /rh2_build/recipe_v1.sh "$FIX_COMMIT" && rm -rf /rh2_build
"""

DOCKERFILE_MATERIAL = """\
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG FIX_COMMIT
COPY recipe_v1.sh /rh2_build/recipe_v1.sh
COPY material_v2.sh /rh2_build/material_v2.sh
COPY material /rh2_build/material
RUN bash /rh2_build/recipe_v1.sh "$FIX_COMMIT" && bash /rh2_build/material_v2.sh /rh2_build/material && rm -rf /rh2_build
"""


def render_dockerfile(*, material: bool, env: bool, env_step: str = DEFAULT_ENV_STEP, sysconfig: bool = False) -> str:
    """按步骤拼 Dockerfile。只有 recipe_v1 / 只加材料步骤时与既有 DOCKERFILE / DOCKERFILE_MATERIAL 逐字节相同；
    环境步骤取 `env_v1.sh` 时与引入 `env_step` 之前逐字节相同；不带构建配置步骤时与引入它之前逐字节相同。
    构建配置步骤紧跟 recipe_v1（它只改搬迁后的解释器目录，与材料、环境步骤互不依赖）。"""

    if not env and not sysconfig:
        return DOCKERFILE_MATERIAL if material else DOCKERFILE
    copies = ["COPY recipe_v1.sh /rh2_build/recipe_v1.sh"]
    runs = ['bash /rh2_build/recipe_v1.sh "$FIX_COMMIT"']
    if sysconfig:
        copies.append(f"COPY {SYSCONFIG_STEP} /rh2_build/{SYSCONFIG_STEP}")
        runs.append(f"bash /rh2_build/{SYSCONFIG_STEP}")
    if material:
        copies += [f"COPY {MATERIAL_STEP} /rh2_build/{MATERIAL_STEP}", "COPY material /rh2_build/material"]
        runs.append(f"bash /rh2_build/{MATERIAL_STEP} /rh2_build/material")
    if env:
        if env_step not in ENV_STEPS:
            raise ValueError(f"未知环境步骤: {env_step!r}")
        copies += [f"COPY {env_step} /rh2_build/{env_step}", "COPY env /rh2_build/env"]
        runs.append(f"bash /rh2_build/{env_step} /rh2_build/env")
    return ("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nARG FIX_COMMIT\n" + "\n".join(copies)
            + "\nRUN " + " && ".join(runs) + " && rm -rf /rh2_build\n")


def load_env_pins(path: Path | None) -> dict[str, dict]:
    """环境配方 → {instance_id: 条目}。结构不符即拒（fail-closed）。"""

    if path is None:
        return {}
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema_id") != ENV_PINS_SCHEMA_ID:
        raise ValueError(f"环境配方 schema_id 非法: {doc.get('schema_id')!r}")
    out = {}
    for iid, ent in (doc.get("tasks") or {}).items():
        pins = ent.get("pins") or []
        if not pins or not ent.get("venv_changed_globs"):
            raise ValueError(f"{iid}: 环境配方缺 pins 或 venv_changed_globs")
        if ent.get("env_step", DEFAULT_ENV_STEP) not in ENV_STEPS:
            raise ValueError(f"{iid}: 未知环境步骤 {ent.get('env_step')!r}")
        for pin in pins:
            if set(pin) != {"dist", "version", "wheel", "sha256", "url"} or len(pin["sha256"]) != 64:
                raise ValueError(f"{iid}: pin 字段不符: {pin}")
            if "/" in pin["wheel"] or not pin["wheel"].endswith(".whl"):
                raise ValueError(f"{iid}: wheel 文件名非法: {pin['wheel']!r}")
        out[iid] = ent
    return out


def env_manifest(entry: dict) -> bytes:
    return "".join(f"{p['dist']}\t{p['version']}\t{p['wheel']}\t{p['sha256']}\n"
                   for p in sorted(entry["pins"], key=lambda p: p["dist"])).encode("utf-8")


def composite_recipe_digest(*, material_manifest_bytes: bytes | None, env_manifest_bytes: bytes | None,
                            env_step: str = DEFAULT_ENV_STEP) -> str:
    """带额外步骤的配方身份：各脚本与清单摘要的规范 JSON 的 sha256（只有材料步骤时与 material_recipe_digest 相同；
    环境步骤以脚本文件名为键，`env_v1.sh` 时与引入 `env_step` 之前相同）。"""

    doc = {"recipe_v1.sh": _sha256_file(RECIPE_PATH)}
    if material_manifest_bytes is not None:
        doc[MATERIAL_STEP] = _sha256_file(MATERIAL_PATH)
        doc["manifest.tsv"] = hashlib.sha256(material_manifest_bytes).hexdigest()
    if env_manifest_bytes is not None:
        if env_step not in ENV_STEPS:
            raise ValueError(f"未知环境步骤: {env_step!r}")
        doc[env_step] = _sha256_file(ENV_STEP_DIR / env_step)
        doc["env_manifest.tsv"] = hashlib.sha256(env_manifest_bytes).hexdigest()
    return "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def with_sysconfig_step(recipe_id: str, recipe_sha256: str, tag_suffix: str) -> tuple[str, str, str]:
    """在已有配方身份上叠加构建配置步骤：身份追加 `+sysconfig_v1`、tag 后缀加 `s`，摘要把原配方摘要与脚本摘要一并纳入。"""

    doc = {"base_recipe_sha256": recipe_sha256, SYSCONFIG_STEP: _sha256_file(ENV_STEP_DIR / SYSCONFIG_STEP)}
    digest = "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return recipe_id + SYSCONFIG_ID_SUFFIX, digest, tag_suffix + SYSCONFIG_TAG_SUFFIX


def _fetch_wheel(pin: dict, dst: Path, cache: Path) -> None:
    """宿主侧取 wheel：先看缓存，没有就按配方 url 下载；两处都核 sha256。"""

    import urllib.request

    cached = cache / pin["wheel"]
    if not (cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == pin["sha256"]):
        cache.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(pin["url"], timeout=300) as resp:  # noqa: S310 配方里固定的 PyPI 文件地址
            body = resp.read()
        if hashlib.sha256(body).hexdigest() != pin["sha256"]:
            raise ValueError(f"wheel 摘要不符: {pin['wheel']}")
        cached.write_bytes(body)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(cached.read_bytes())


def material_manifest(revisions: list[R2EMaterialRevision]) -> bytes:
    """材料步骤读的清单：每条隐藏测试修订一行 "<路径>\t<修订前 hex，新增为 ->\t<修订后 hex>"（按路径排序）。"""

    lines = sorted(
        f"{r.target}\t{'-' if r.kind == REVISION_KIND_HIDDEN_ADD else r.sha256_before.removeprefix('sha256:')}"
        f"\t{r.sha256_after.removeprefix('sha256:')}\n"
        for r in revisions
    )
    return "".join(lines).encode("utf-8")


def material_recipe_digest(manifest: bytes) -> str:
    """带材料步骤的配方身份：recipe_v1.sh、材料步骤脚本、manifest.tsv 三者摘要的规范 JSON 的 sha256。"""

    doc = {
        "recipe_v1.sh": _sha256_file(RECIPE_PATH),
        MATERIAL_STEP: _sha256_file(MATERIAL_PATH),
        "manifest.tsv": hashlib.sha256(manifest).hexdigest(),
    }
    return "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

# 导层完整性：来源与派生镜像里跑同一段脚本，宿主侧逐段比对
INTEGRITY_SCRIPT = r"""
set -o pipefail
cd /testbed
echo "## A"
find . \( -path ./.git -o -path ./.venv \) -prune -o -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
echo "## B"
cd /testbed/.venv
find . \( -path ./bin -o -name __pycache__ -o -path ./pyvenv.cfg \) -prune -o -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
echo "## C"
cd /testbed/.venv/bin
for f in $(find . -type f | LC_ALL=C sort); do
  first=$(LC_ALL=C head -n1 "$f" | LC_ALL=C head -c 300 | tr -d '\r')
  case "$first" in
    '#!'*) printf '%s\t%s\t%s\n' "$f" "$(tail -n +2 "$f" | sha256sum | cut -d' ' -f1)" "$first" ;;
    *) printf '%s\t%s\t-\n' "$f" "$(sha256sum "$f" | cut -d' ' -f1)" ;;
  esac
done
echo "## L"
find . -type l -printf '%p -> %l\n' | LC_ALL=C sort
echo "## D"
cd /testbed
echo "head=$(git rev-parse HEAD)"
echo "status=$(git status --porcelain=v1 -uall | sha256sum | cut -d' ' -f1)"
echo "index=$(git ls-files -s | sha256sum | cut -d' ' -f1)"
echo "diff=$(git -c core.fileMode=false diff --full-index HEAD | sha256sum | cut -d' ' -f1)"  # gc 后缩写哈希变短，用全长
echo "## P"
cat /testbed/.venv/pyvenv.cfg
"""

ROOT_CHECKS = r"""
set -o pipefail
echo "tree=$(cd {private} && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
echo "private_mode=$(stat -c %a {private_parent})"
echo "private_owner=$(stat -c %U:%G {private_parent})"
echo "r2e_tests_root=$([ -e /r2e_tests ] && echo present || echo absent)"
echo "r2e_tests_workdir=$([ -e /testbed/r2e_tests ] && echo present || echo absent)"
echo "run_tests_sh=$(sha256sum /testbed/run_tests.sh | cut -d' ' -f1)"
echo "testbed_owner=$(stat -c %U /testbed)"
cd /testbed
echo "head=$(git rev-parse HEAD)"
echo "children=$(git rev-list --children --all | grep "^$(git rev-parse HEAD)" | wc -w | tr -d ' ')"
echo "fix_present=$(git cat-file -e '{fix}^{{commit}}' 2>/dev/null && echo yes || echo no)"
echo "refs=$(git for-each-ref | wc -l | tr -d ' ')"
echo "remotes=$(git remote | wc -l | tr -d ' ')"
echo "reflog=$(git reflog 2>/dev/null | wc -l | tr -d ' ')"
echo "interp=$(readlink -f /testbed/.venv/bin/python)"
echo "metacopy=$(cat /sys/module/overlay/parameters/metacopy 2>/dev/null || echo unknown)"
"""

UID_CHECKS = r"""
cd /testbed
if /testbed/.venv/bin/python -I -S -c 'import sys; bad=[p for p in sys.path if p.startswith("/root")]; sys.exit(1 if bad else 0)' 2>/dev/null; then echo "interp_isolated=ok"; else echo "interp_isolated=fail"; fi
if /testbed/.venv/bin/python -c 'import sys; bad=[p for p in sys.path if p.startswith("/root")]; sys.exit(1 if bad else 0)' 2>/dev/null; then echo "interp_normal=ok"; else echo "interp_normal=fail"; fi
echo "interp_exe=$(/testbed/.venv/bin/python -I -S -c 'import sys; print(sys.executable)' 2>/dev/null || echo fail)"
echo "private_ls=$(ls {private} >/dev/null 2>&1 && echo readable || echo denied)"
echo "private_cat=$(cat {private}/* >/dev/null 2>&1 && echo readable || echo denied)"
echo "git_head=$(git rev-parse HEAD 2>/dev/null || echo fail)"
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Docker:
    def __init__(self, platform: str | None) -> None:
        self.platform = platform

    def _plat(self) -> list[str]:
        return ["--platform", self.platform] if self.platform else []

    def run(self, args: list[str], *, timeout: int, log=None, check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["docker", *args]
        if log is not None:
            log.write(("$ " + " ".join(cmd) + "\n").encode("utf-8"))
            log.flush()
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if log is not None:
            log.write(proc.stdout)
            log.write(proc.stderr)
            log.write(f"[rc={proc.returncode}]\n".encode("utf-8"))
            log.flush()
        if check and proc.returncode != 0:
            raise RuntimeError(f"{' '.join(cmd[:3])} failed rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[-800:]}")
        return proc

    def bash(self, image: str, script: str, *, user: str | None = None, timeout: int = 900) -> tuple[int, str, str]:
        args = ["run", "--rm", "--network", "none", *self._plat()]
        if user is not None:
            args += ["--user", user, "-e", "HOME=/tmp"]
        args += [image, "bash", "-c", script]
        proc = self.run(args, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")

    def inspect(self, image: str) -> dict:
        proc = self.run(["image", "inspect", image], timeout=120)
        return json.loads(proc.stdout.decode("utf-8"))[0]


def _sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def _kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def compare_integrity(base: str, derived: str, *, pydir: str, env_globs: tuple[str, ...] = ()) -> dict[str, dict]:
    """来源 vs 派生的导层完整性比对。返回 {检查名: {"ok": bool, "detail": …}}。
    `env_globs`（相对 .venv 的路径通配，来自环境配方）：只有这些路径允许因环境配方而变化，其余逐条相同。"""

    import fnmatch

    def _venv_path(line: str) -> str:
        return line.split("  ", 1)[-1].removeprefix("./")

    def _allowed(path: str) -> bool:
        return any(fnmatch.fnmatch(path, g) for g in env_globs)

    b, d = _sections(base), _sections(derived)
    checks: dict[str, dict] = {}
    for key, label in (("A", "testbed_files_outside_git_and_venv"), ("B", "venv_files_outside_bin")):
        lb, ld = b.get(key, []), d.get(key, [])
        env_changed: list[str] = []
        if key == "B" and env_globs:
            env_changed = sorted({_venv_path(x) for x in set(lb) ^ set(ld) if _allowed(_venv_path(x))})
            lb = [x for x in lb if not _allowed(_venv_path(x))]
            ld = [x for x in ld if not _allowed(_venv_path(x))]
        same = lb == ld
        diff = sorted(set(lb) ^ set(ld))
        checks[label] = {"ok": same and bool(b.get(key)), "count": len(b.get(key, [])), "diff_sample": diff[:6]}
        if env_changed:
            checks[label]["env_changed_count"] = len(env_changed)
            checks[label]["env_changed_sample"] = env_changed[:6]

    # C：.venv/bin 逐文件（去 shebang 行后的内容相同；shebang 只允许 /root uv 前缀 → /opt/py）
    def _c(lines: list[str]) -> dict[str, tuple[str, str]]:
        out: dict[str, tuple[str, str]] = {}
        for ln in lines:
            parts = ln.split("\t", 2)
            if len(parts) == 3:
                out[parts[0]] = (parts[1], parts[2])
        return out

    cb, cd = _c(b.get("C", [])), _c(d.get("C", []))
    if env_globs:  # C 段路径相对 .venv/bin（"./hypothesis"）；配方里写成 "bin/hypothesis"
        bin_globs = tuple(g.removeprefix("bin/") for g in env_globs if g.startswith("bin/"))
        cb = {k: v for k, v in cb.items() if not any(fnmatch.fnmatch(k.removeprefix("./"), g) for g in bin_globs)}
        cd = {k: v for k, v in cd.items() if not any(fnmatch.fnmatch(k.removeprefix("./"), g) for g in bin_globs)}
    bad: list[str] = []
    if set(cb) != set(cd):
        bad.append(f"file_set_differs:{sorted(set(cb) ^ set(cd))[:5]}")
    for path, (rest_b, first_b) in cb.items():
        if path not in cd:
            continue
        rest_d, first_d = cd[path]
        if rest_b != rest_d:
            bad.append(f"content:{path}")
        elif first_b != first_d and not (first_b.startswith("#!" + UVROOT) and first_d == first_b.replace(UVROOT, "/opt/py", 1)):
            bad.append(f"shebang:{path}:{first_b!r}->{first_d!r}")
    checks["venv_bin_files"] = {"ok": not bad and bool(cb), "count": len(cb), "bad": bad[:8]}

    # L：符号链接只允许 python* 重指向 /opt/py
    lb, ld = set(b.get("L", [])), set(d.get("L", []))
    changed = sorted(lb ^ ld)
    allowed = all(
        (ln.split(" -> ", 1)[0].rsplit("/", 1)[-1].startswith("python"))
        and (ln in lb and UVROOT in ln or ln in ld and "/opt/py/" in ln or ln in lb and ln.split(" -> ", 1)[1] in ("python", "python3"))
        for ln in changed
    )
    checks["venv_bin_symlinks"] = {"ok": allowed, "changed": changed[:10]}

    # D：git 工作树 / 索引 / HEAD 不变
    db, dd = _kv("\n".join(b.get("D", []))), _kv("\n".join(d.get("D", [])))
    checks["git_worktree_preserved"] = {
        "ok": bool(db) and all(db.get(k) == dd.get(k) for k in ("head", "status", "index", "diff")),
        "base": db, "derived": dd,
    }
    # P：pyvenv.cfg 只改 home
    pb, pd = "\n".join(b.get("P", [])), "\n".join(d.get("P", []))
    checks["pyvenv_cfg_home_only"] = {"ok": pd == pb.replace(f"{UVROOT}/{pydir}", f"/opt/py/{pydir}") and pb != pd}
    return checks


def build_one(docker: Docker, *, out: Path, public, grading, tag_prefix: str, skip_pull: bool, timeouts: dict,
              repo_root: Path | None = None, revisions: tuple[R2EMaterialRevision, ...] = (),
              env_entry: dict | None = None, sysconfig: bool = False) -> dict:
    iid = grading.instance_id
    tdir = out / iid
    ctx = tdir / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    repo_ref = public.image.rsplit(":", 1)[0]
    base_ref = f"{repo_ref}@{public.image_manifest_digest}"
    hidden_revs = [r for r in revisions if r.kind in HIDDEN_REVISION_KINDS]
    manifest = material_manifest(hidden_revs) if hidden_revs else b""
    if hidden_revs and repo_root is None:
        raise ValueError(f"{iid}: 带隐藏测试修订的题需要 repo_root 取修订后文件")
    env_bytes = env_manifest(env_entry) if env_entry else None
    env_step = (env_entry or {}).get("env_step", DEFAULT_ENV_STEP)
    if env_entry:
        env_id_suffix, env_tag_suffix = ENV_STEPS[env_step]
        recipe_id = (MATERIAL_RECIPE_ID if hidden_revs else RECIPE_ID) + env_id_suffix
        recipe_sha = composite_recipe_digest(material_manifest_bytes=manifest if hidden_revs else None, env_manifest_bytes=env_bytes,
                                             env_step=env_step)
        tag_suffix = (MATERIAL_TAG_SUFFIX if hidden_revs else RECIPE_ID) + env_tag_suffix
    elif hidden_revs:
        recipe_id, recipe_sha, tag_suffix = MATERIAL_RECIPE_ID, material_recipe_digest(manifest), MATERIAL_TAG_SUFFIX
    else:
        recipe_id, recipe_sha, tag_suffix = RECIPE_ID, "sha256:" + _sha256_file(RECIPE_PATH), RECIPE_ID
    # 环境要求（REVISION_ENV_REQUIREMENTS）批准的是环境步骤所在的原配方身份与摘要；构建配置步骤只改搬迁后解释器的
    # 构建配置、不动依赖，所以要求按叠加前的原配方核对，原配方身份与摘要都记进 facts
    base_recipe_id, base_recipe_sha = recipe_id, recipe_sha
    if sysconfig:
        recipe_id, recipe_sha, tag_suffix = with_sysconfig_step(recipe_id, recipe_sha, tag_suffix)
    tag = f"{tag_prefix}/{grading.repo_key_lower}:{grading.source_commit_hash[:12]}-{tag_suffix}"
    result: dict = {
        "instance_id": iid, "task_id": f"r2e_gym_subset::{iid}", "base_image_ref": public.image,
        "base_image_manifest_digest": public.image_manifest_digest, "base_ref_by_digest": base_ref, "tag": tag,
        "recipe_id": recipe_id, "recipe_sha256": recipe_sha, "ok": False, "failures": [],
        "base_recipe_id": base_recipe_id, "base_recipe_sha256": base_recipe_sha,
        "material_revisions": [r.revision_id for r in hidden_revs],
        "env_pins": [f"{p['dist']}=={p['version']}" for p in (env_entry or {}).get("pins", [])],
    }
    # Codex 批次三复核 F1：本题修订若只在特定环境配方下成立（例 orange3 的 r2e-mr-020 需要 +env_v2），缺这一步的构建
    # 不能产出可用于该材料版本的覆盖条目——直接判失败，不起构建，也不写 overlays.jsonl
    env_error = env_requirement_mismatch(base_recipe_id, [r.revision_id for r in revisions], recipe_sha256=base_recipe_sha)
    if env_error is not None:
        result["failures"].append(env_error)
        return result
    with open(tdir / "build.log", "ab") as log:
        try:
            if not skip_pull:
                docker.run(["pull", *docker._plat(), base_ref], timeout=timeouts["pull"], log=log)
            base = docker.inspect(base_ref)
            result["base_image_id"] = base["Id"]
            result["base_repo_digests"] = base.get("RepoDigests")
            if not any(rd.endswith("@" + public.image_manifest_digest) for rd in base.get("RepoDigests") or []):
                result["failures"].append("base_repo_digest_mismatch")
                return result
            (ctx / "recipe_v1.sh").write_bytes(RECIPE_PATH.read_bytes())
            (ctx / "Dockerfile").write_text(render_dockerfile(material=bool(hidden_revs), env=bool(env_entry), env_step=env_step,
                                                              sysconfig=sysconfig), encoding="utf-8")
            if sysconfig:
                (ctx / SYSCONFIG_STEP).write_bytes((ENV_STEP_DIR / SYSCONFIG_STEP).read_bytes())
            if env_entry:
                (ctx / env_step).write_bytes((ENV_STEP_DIR / env_step).read_bytes())
                (ctx / "env" / "wheels").mkdir(parents=True, exist_ok=True)
                (ctx / "env" / "manifest.tsv").write_bytes(env_bytes)
                for pin in env_entry["pins"]:
                    _fetch_wheel(pin, ctx / "env" / "wheels" / pin["wheel"], out / "_wheel_cache")
            if hidden_revs:
                (ctx / MATERIAL_STEP).write_bytes(MATERIAL_PATH.read_bytes())
                (ctx / "material" / "files").mkdir(parents=True, exist_ok=True)
                (ctx / "material" / "manifest.tsv").write_bytes(manifest)
                for rev in hidden_revs:
                    body = (repo_root / rev.revised_file).read_bytes()
                    if "sha256:" + hashlib.sha256(body).hexdigest() != rev.sha256_after:
                        raise ValueError(f"{rev.revision_id}: 修订后文件摘要与修订单不符")
                    dst = ctx / "material" / "files" / rev.target
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(body)
            t_build = time.monotonic()
            docker.run(
                ["build", "--pull=false", "--network=none", "--progress=plain", *docker._plat(),
                 "--build-arg", f"BASE_IMAGE={base_ref}", "--build-arg", f"FIX_COMMIT={grading.source_commit_hash}",
                 "-t", tag, str(ctx)],
                timeout=timeouts["build"], log=log,
            )
            result["build_seconds"] = round(time.monotonic() - t_build, 1)
            built = docker.inspect(tag)
            result["derived_image_id"] = built["Id"]
            result["base_size_bytes"], result["derived_size_bytes"] = base.get("Size"), built.get("Size")
            result["base_layers_preserved"] = built["RootFS"]["Layers"][: len(base["RootFS"]["Layers"])] == base["RootFS"]["Layers"]
            derived_id = built["Id"]

            # ---- 复核：导层完整性
            rc_b, ib, eb = docker.bash(base_ref, INTEGRITY_SCRIPT, timeout=timeouts["check"])
            rc_d, idv, ed = docker.bash(derived_id, INTEGRITY_SCRIPT, timeout=timeouts["check"])
            (tdir / "integrity_base.txt").write_text(ib, encoding="utf-8")
            (tdir / "integrity_derived.txt").write_text(idv, encoding="utf-8")
            if rc_b != 0 or rc_d != 0:
                result["failures"].append(f"integrity_script_rc:{rc_b}/{rc_d}:{(eb + ed)[-300:]}")
                return result
            pydir = _kv("\n".join(_sections(ib).get("P", []))).get("home", "").removeprefix(UVROOT + "/").split("/")[0]
            checks = compare_integrity(ib, idv, pydir=pydir, env_globs=tuple((env_entry or {}).get("venv_changed_globs", ())))
            result["integrity"] = checks
            if env_entry:
                # ---- 复核：环境配方里固定的版本确实生效（以沙箱身份读包元数据；同名分发多于一份即不符）
                dists = " ".join(shlex.quote(p["dist"]) for p in env_entry["pins"])
                rc_e, out_e, err_e = docker.bash(derived_id, f"/testbed/.venv/bin/python -c {shlex.quote(DIST_VERSIONS_PY)} {dists}",
                                                 user=f"{AGENT_UID}:{AGENT_UID}", timeout=timeouts["check"])
                got = _kv(out_e)
                want = {p["dist"]: p["version"] for p in env_entry["pins"]}
                checks["env_pins_applied"] = {"ok": rc_e == 0 and got == want, "got": got, "want": want}

            # ---- 复核：root 侧事实
            rc, out_root, err = docker.bash(
                derived_id, ROOT_CHECKS.format(private=R2E_PRIVATE_HIDDEN_TESTS_DIR, private_parent=str(Path(R2E_PRIVATE_HIDDEN_TESTS_DIR).parent),
                                               fix=grading.source_commit_hash), timeout=timeouts["check"],
            )
            root_facts = _kv(out_root)
            result["root_facts"] = root_facts
            if rc != 0:
                result["failures"].append(f"root_checks_rc:{rc}:{err[-300:]}")
            checks["hidden_tests_tree_matches_bundle"] = {"ok": "sha256:" + root_facts.get("tree", "") == grading.hidden_tests_tree_sha256}
            checks["hidden_tests_private_and_absent_elsewhere"] = {"ok": (
                root_facts.get("private_mode") == "700" and root_facts.get("private_owner") == "root:root"
                and root_facts.get("r2e_tests_root") == "absent" and root_facts.get("r2e_tests_workdir") == "absent")}
            checks["run_tests_sh_matches_bundle"] = {"ok": "sha256:" + root_facts.get("run_tests_sh", "") == grading.run_tests_sh_sha256}
            checks["head_matches_bundle_base_commit"] = {"ok": root_facts.get("head") == grading.base_commit}
            checks["git_scrubbed"] = {"ok": (
                root_facts.get("children") == "1" and root_facts.get("fix_present") == "no"
                and root_facts.get("refs") == "0" and root_facts.get("remotes") == "0" and root_facts.get("reflog") == "0")}
            checks["interpreter_relocated_root"] = {"ok": root_facts.get("interp", "").startswith("/opt/py/")}

            # ---- 复核：沙箱身份
            for uid, label in ((GRADER_UID, "grader_uid"), (AGENT_UID, "agent_uid")):
                rc, out_uid, err = docker.bash(derived_id, UID_CHECKS.format(private=R2E_PRIVATE_HIDDEN_TESTS_DIR), user=f"{uid}:{uid}", timeout=timeouts["check"])
                facts = _kv(out_uid)
                result[f"{label}_facts"] = facts
                checks[f"interpreter_executable_as_{label}"] = {"ok": facts.get("interp_isolated") == "ok" and facts.get("interp_normal") == "ok" and facts.get("interp_exe", "").startswith("/testbed/.venv/")}
                checks[f"hidden_tests_unreadable_as_{label}"] = {"ok": facts.get("private_ls") == "denied" and facts.get("private_cat") == "denied"}
                checks[f"git_readable_as_{label}"] = {"ok": facts.get("git_head") == grading.base_commit}
            if sysconfig:
                # ---- 复核：构建配置已指向搬迁后的解释器（agent 身份读 sysconfig，不得再含 /root 下的 uv 前缀）
                rc_s, out_s, err_s = docker.bash(derived_id, f"/testbed/.venv/bin/python -c {shlex.quote(SYSCONFIG_CHECK_PY)}",
                                                 user=f"{AGENT_UID}:{AGENT_UID}", timeout=timeouts["check"])
                try:
                    sc = json.loads(out_s.strip().splitlines()[-1]) if rc_s == 0 and out_s.strip() else {}
                except json.JSONDecodeError:
                    sc = {}
                result["sysconfig_facts"] = sc or {"rc": rc_s, "stderr": err_s[-300:]}
                checks["sysconfig_paths_relocated"] = {"ok": bool(sc) and not sc.get("bad") and str(sc.get("LIBDIR", "")).startswith("/opt/py/")
                                                       and str(sc.get("INCLUDEPY", "")).startswith("/opt/py/")}
            # ---- 复核：driver 的 rollout 预检（agent 身份、同一评估函数）
            rc, out_pf, err = docker.bash(derived_id, render_r2e_rollout_preflight_script(), user=f"{AGENT_UID}:{AGENT_UID}", timeout=timeouts["check"])
            pf_failures = evaluate_r2e_rollout_preflight(out_pf)
            result["preflight_stdout"] = out_pf.strip().splitlines()
            checks["driver_rollout_preflight"] = {"ok": rc == 0 and not pf_failures, "failures": pf_failures}
            checks["base_layers_preserved"] = {"ok": bool(result["base_layers_preserved"])}

            bad = sorted(name for name, c in checks.items() if not c.get("ok"))
            result["failures"].extend(bad)
            result["ok"] = not result["failures"]
            if result["ok"]:
                overlay = EnvironmentOverlayV1(
                    task_id=result["task_id"], base_image_ref=public.image, base_image_manifest_digest=public.image_manifest_digest,
                    derived_image_ref=tag, derived_image_id=derived_id, recipe_id=recipe_id, recipe_sha256=result["recipe_sha256"],
                    built_at_utc=datetime.now(timezone.utc),
                    facts=EnvironmentOverlayFacts(
                        interpreter_relocated=True, testbed_owner=root_facts.get("testbed_owner", "root"), git_scrubbed=True,
                        hidden_tests_location=R2E_PRIVATE_HIDDEN_TESTS_DIR, hidden_tests_tree_sha256="sha256:" + root_facts["tree"],
                    ),
                )
                result["overlay"] = json.loads(overlay.model_dump_json())
        except (RuntimeError, subprocess.TimeoutExpired, KeyError, ValueError) as exc:
            result["failures"].append(f"{type(exc).__name__}:{str(exc)[-400:]}")
        finally:
            result["seconds_total"] = round(time.monotonic() - started, 1)
            (tdir / "facts.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return result


def write_overlays(out: Path) -> int:
    """覆盖表 = 输出目录下**全部**已通过题目的 facts.json 汇总（按 task_id 排序）。按目录汇总而不是按本次运行
    的内存列表重写：**串行**多次调用共享同一个输出目录时，后一次不会把前一次的行覆盖掉（并行由目录锁拒绝）。"""

    rows: dict[str, dict] = {}
    for facts_path in sorted(out.glob("*/facts.json")):
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        if facts.get("ok") and facts.get("overlay"):
            rows[facts["overlay"]["task_id"]] = facts["overlay"]
    (out / "overlays.jsonl").write_text("".join(json.dumps(rows[k], ensure_ascii=False) + "\n" for k in sorted(rows)), encoding="utf-8")
    return len(rows)


def host_facts(docker: Docker) -> dict:
    info = subprocess.run(["docker", "info", "--format", "{{.Driver}}|{{.OSType}}/{{.Architecture}}|{{.ServerVersion}}|{{json .DriverStatus}}"],
                          capture_output=True, text=True, timeout=60)
    return {"docker_info": info.stdout.strip(), "platform_flag": docker.platform, "recorded_at_utc": _now()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--task-ids", default=None, help="逗号分隔的 instance_id 或 task_id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--platform", default=None, help="非 x86 宿主（如 Apple Silicon 仿真）时传 linux/amd64")
    ap.add_argument("--tag-prefix", default="rh2-r2e-derived")
    ap.add_argument("--skip-pull", action="store_true")
    ap.add_argument("--pull-timeout", type=int, default=3600)
    ap.add_argument("--build-timeout", type=int, default=3600)
    ap.add_argument("--check-timeout", type=int, default=1800)
    ap.add_argument("--regenerate-overlays", action="store_true", help="不构建，只按输出目录下的 facts.json 重写 overlays.jsonl")
    ap.add_argument("--sysconfig-fix", action="store_true",
                    help="本次构建的每道题都加构建配置步骤 sysconfig_v1.sh（配方身份 +sysconfig_v1，tag 后缀加 s）")
    ap.add_argument("--env-pins", default=None, help="环境配方 env_pins_v*.json（逐题依赖固定；只对其中登记的题生效；条目的 env_step 选环境步骤脚本）")
    ns = ap.parse_args(argv)
    out = Path(ns.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lock = out / ".build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(json.dumps({"error": "output_dir_locked", "lock": str(lock),
                          "hint": "同一输出目录同一时刻只允许一个构建进程；确认无其它进程后删除锁文件"}), file=sys.stderr)
        return 2
    try:
        with os.fdopen(fd, "w") as fh:  # 锁说明写失败（如 ENOSPC）也走 finally，不留空锁
            fh.write(f"pid={os.getpid()} started_at_utc={_now()}\n")
        return _main_locked(ns, ap, out)
    finally:
        lock.unlink(missing_ok=True)


def _main_locked(ns: argparse.Namespace, ap: argparse.ArgumentParser, out: Path) -> int:
    if ns.regenerate_overlays:
        print(json.dumps({"overlays": str(out / "overlays.jsonl"), "rows": write_overlays(out)}))
        return 0
    if not ns.all and not ns.task_ids:
        ap.error("--task-ids 或 --all 必选其一")
    repo_root = Path(ns.repo_root).resolve()
    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    publics = {p.instance_id: p for p in trusted.result.public_bundles}
    gradings = {g.instance_id: g for g in trusted.result.grading_bundles}
    if ns.all:
        wanted = sorted(gradings)
    else:
        wanted = [x.strip().split("::", 1)[-1] for x in ns.task_ids.split(",") if x.strip()]
        unknown = [w for w in wanted if w not in gradings]
        if unknown:
            ap.error(f"未知任务: {unknown}")
    docker = Docker(ns.platform)
    env_pins = load_env_pins(Path(ns.env_pins) if ns.env_pins else None)
    unknown_env = sorted(set(env_pins) - set(gradings))
    if unknown_env:
        ap.error(f"环境配方里有未知任务: {unknown_env}")
    timeouts = {"pull": ns.pull_timeout, "build": ns.build_timeout, "check": ns.check_timeout}
    results_path = out / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    results.update({"schema_id": "rh2.r2e_derived_build_results.v1", "recipe_id": RECIPE_ID,
                    "recipe_sha256": "sha256:" + _sha256_file(RECIPE_PATH), "host": host_facts(docker)})
    if ns.sysconfig_fix:
        results["sysconfig_step"] = {"script": SYSCONFIG_STEP, "sha256": _sha256_file(ENV_STEP_DIR / SYSCONFIG_STEP)}
    results.setdefault("tasks", {})  # 同一输出目录多次调用：逐题合并，不丢先前的题
    built_ok = 0
    for iid in wanted:
        res = build_one(docker, out=out, public=publics[iid], grading=gradings[iid], tag_prefix=ns.tag_prefix,
                        skip_pull=ns.skip_pull, timeouts=timeouts, repo_root=repo_root,
                        revisions=trusted.revisions.get(iid, ()), env_entry=env_pins.get(iid), sysconfig=ns.sysconfig_fix)
        results["tasks"][iid] = {k: res.get(k) for k in ("ok", "failures", "derived_image_id", "recipe_id", "material_revisions", "env_pins",
                                                           "build_seconds", "seconds_total", "base_size_bytes", "derived_size_bytes")}
        built_ok += bool(res.get("ok"))
        print(json.dumps({iid: results["tasks"][iid]}, ensure_ascii=False), flush=True)
        write_overlays(out)
        results_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [i for i in wanted if not results["tasks"][i]["ok"]]
    print(json.dumps({"built_ok": built_ok, "failed": bad, "overlay_rows_total": write_overlays(out), "overlays": str(out / "overlays.jsonl")}, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
