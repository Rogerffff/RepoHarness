"""W1b 第一集成切片（F6）：RolloutManager actor 内的 prepared 任务面。

职责（与 bringup 的 v1 `load_bundle_pairs()` 八题任务面并列，二选一）：

1. 只读 trusted-prep 的两份产物（`envpack.prepared_tasks` 三个读取口，全部复核
   identity/digest/权限），**不调用完整 loader**；
2. 公开面 → `RolloutTaskSpec`（`grading_spec=None`：rollout 侧只携带 digest 锚，
   评分材料不再内嵌在模型侧可见路径的对象上——W2a T1）；
3. 私有面 → 同一 actor 进程持有的 `HostGradingView` 表；评分 spec/parser **在
   本进程内从 v2 safe view 构造**（`build_grading_spec_from_host_view`），闭包捕获的是
   `PrivateGradingBundleV2`（无 golden 字段），取代 v1 `build_swe_grading_spec` 捕获
   含 golden_patch 的 `PrivateGradingBundle` 的构造方式；
4. 评分材料查找只经 F4 的 `AttemptAssignment`（attempt → host 原始分派），并在
   消费时刻 `revalidated()`。

v2 eval 脚本形态说明（S1-c，评分接线 2026-09-15 改造）：`PrivateGradingBundleV2` 不携带官方
eval_script 全文，命令全部按 `spec_vendor` 从 pinned JSON 派生。脚本形态对齐 SWE-Gym fork
`make_eval_script_list`：激活环境 → vendor `eval_commands`（conan 的 PYTHONPATH 导出）→ git 状态记录
→ 恢复 official 测试文件 → heredoc apply test_patch → **安装段**（vendor `install` 逐字执行，带
`RH2_PHASE_START/END=install`、`RH2_INSTALL_RC`、`RH2_TS_*` 时间戳）→ 官方 Start/End 标记 → vendor
派生的测试命令（mypy `-k "case…"`；其余 `test_cmd + 剔除资源文件的测试文件`）→ reset。
与官方的有意差别（用户决定 D2=A）：官方"安装 → 恢复/注入测试 → 测试"，这里可信 setup（root）先
恢复/注入测试，安装在其后的候选段以候选用户执行——尚未证明等价，由代表题对账检查安装产物与
逐测试结果。安装段与官方一样在同一 shell 里、没有 `set -e`：安装串里的 `export` 对后续测试命令
有效；`RH2_INSTALL_RC` 只是安装串最后一个命令的退出码。
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from repoharness2.adapters.slime.generate import RolloutTaskSpec
from repoharness2.adapters.slime.sandbox_profile import grader_trusted_setup_attest_lines
from repoharness2.envpack import scoring
from repoharness2.envpack.bundles import render_user_prompt
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleR2E, PrivateGradingBundleV2
from repoharness2.envpack.environment_overlay import (
    EnvironmentOverlayError,
    EnvironmentOverlayV1,
    env_requirement_mismatch,
    parse_environment_overlays,
)
from repoharness2.envpack.prepared_tasks import (
    PreparedTasksError,
    PreparedTasksManifest,
    load_host_grading_views,
    load_prepared_manifest,
    load_prepared_rollout_views,
    verify_prompt_data_binding,
)
from repoharness2.envpack.spec_vendor import (
    derive_eval_commands,
    derive_import_probe_module,
    derive_install_cmd,
    derive_test_command_for_bundle,
    verify_grading_eval_cmd,
)
from repoharness2.envpack.swegym_parsers import SWEGYM_PARSERS_VERSION_TAG
from repoharness2.envpack.training_view import HostGradingView, RolloutTaskView
from repoharness2.grading.manager import (
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    EnvQualification,
    GradingEnvSpec,
    HygieneRules,
    patch_touched_paths,
    render_compile_probe_script,
)

# swebench.harness.constants 的两个日志标记（官方 parser 按它们切出测试输出段）。
# 不在模块级 import swebench（envpack 纪律：swebench 只在解析日志时惰性 import）；
# 单测与 swebench 常量逐字对拍。
V2_EVAL_START_MARKER = ">>>>> Start Test Output"
V2_EVAL_END_MARKER = ">>>>> End Test Output"
V2_EVAL_HEREDOC_DELIMITER = "EOF_RH2_V2_TEST_PATCH"
V2_EVAL_CONDA_ENV = "testbed"
V2_EVAL_TESTBED = "/testbed"


class GradingMaterialsError(RuntimeError):
    """actor 内评分材料查找/构造 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


def _v2_eval_preconditions(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> str:
    verify_grading_eval_cmd(grading)  # eval_cmd 消费前互检（bundles_v2 第三道防线）
    if not test_files:
        raise GradingMaterialsError(
            "v2_test_files_empty", f"{grading.instance_id}: test_patch 未触碰任何路径——无法确定测试文件，拒绝构造 eval 脚本。"
        )
    if V2_EVAL_HEREDOC_DELIMITER in grading.test_patch:
        raise GradingMaterialsError(
            "v2_heredoc_delimiter_collision", f"{grading.instance_id}: test_patch 含 heredoc 定界符，拒绝构造 eval 脚本。"
        )
    return " ".join(shlex.quote(p) for p in test_files)


# e1 真机发现（2026-09-15）：pandas 镜像的 conda 激活钩子（activate-binutils_linux-64.sh）引用未定义变量，
# `set -u` 会让可信 setup 在 `conda activate testbed` 处退出。SWE-Gym fork 的 eval 脚本头是 `set -xo pipefail`
# （无 -u；swebench 4.1.0 才是 -uxo），按 vendor 来源对齐，不加 -u。
_V2_ENV_LINES = (
    "#!/bin/bash",
    "set -xo pipefail",
    "source /opt/miniconda3/bin/activate",
    f"conda activate {V2_EVAL_CONDA_ENV}",
    f"cd {V2_EVAL_TESTBED}",
    f"git config --global --add safe.directory {V2_EVAL_TESTBED}",
)


def _v2_trusted_setup_lines(grading: PrivateGradingBundleV2, files: str) -> list[str]:
    reset = f"git checkout {grading.base_commit} {files}"
    return [
        "git status",
        "git show",
        f"git -c core.fileMode=false diff {grading.base_commit}",
        reset,
        f"git apply -v - <<'{V2_EVAL_HEREDOC_DELIMITER}'",
        grading.test_patch,
        V2_EVAL_HEREDOC_DELIMITER,
    ]


def _v2_vendor_env_lines(grading: PrivateGradingBundleV2) -> list[str]:
    """vendor `eval_commands`（官方在激活环境后、任何 git 操作前逐条执行；两段脚本都要有）。"""
    return list(derive_eval_commands(grading.spec_vendor_id, grading.repo_key_lower, grading.version))


def _v2_install_lines(grading: PrivateGradingBundleV2) -> list[str]:
    """安装段（候选用户执行）：vendor `install` 串逐字执行，前后打阶段标记与时间戳，段末退出码单独记录。

    `RH2_INSTALL_RC` = 安装串最后一个命令的退出码（多命令 `a; b` 只反映 b）；它不单独证明安装成功或失败，
    安装是否作用于候选由 root 观测（S1-m）与对账判断。没有 `install` 的 spec 只打 `RH2_INSTALL_SKIPPED=1`。"""
    install = derive_install_cmd(grading.spec_vendor_id, grading.repo_key_lower, grading.version)
    if install is None:
        return ["echo RH2_INSTALL_SKIPPED=1"]
    return [
        "echo RH2_PHASE_START=install",
        'echo "RH2_TS_INSTALL_START=$(date +%s.%N)"',
        # 2026-09-19（B 线 216 题诊断 / A 线 F4）：段末 rc 只反映最后一条命令，116 次安装段末非零、138 行零分有真实
        # 安装失败却 rc=0。ERR trap 把每条失败的简单命令连同退出码打成一行 `RH2_INSTALL_CMD_FAILED=<rc> <cmd>`
        # （bash 在 trap 结束后恢复 $?，段末 `RH2_INSTALL_RC=$?` 不受影响；`set -E` 让子 shell/函数继承）。只进诊断。
        # 边界：`a && b` 里 a 失败不触发 ERR（bash 规则：&&/|| 列表的非末项不算），此类失败只能从 pip/make 的文本判断。
        "set -E; trap 'echo \"RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}\"' ERR",
        install,
        "RH2_INSTALL_RC=$?",
        "trap - ERR; set +E",
        'echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"',
        'echo "RH2_TS_INSTALL_END=$(date +%s.%N)"',
        "echo RH2_PHASE_END=install",
    ]


def _v2_candidate_test_lines(grading: PrivateGradingBundleV2) -> list[str]:
    """测试段：官方 Start/End 标记之间是 vendor 派生的测试命令（不再是 `eval_cmd + 全部触碰文件`）。"""
    return [
        'echo "RH2_TS_TEST_START=$(date +%s.%N)"',
        f": '{V2_EVAL_START_MARKER}'",
        derive_test_command_for_bundle(grading),
        "RH2_TEST_RC=$?",  # I7：测试命令自身的退出码（在 End 标记之外打印，只进诊断）
        f": '{V2_EVAL_END_MARKER}'",
        'echo "RH2_TEST_RC=$RH2_TEST_RC"',
        'echo "RH2_TS_TEST_END=$(date +%s.%N)"',
    ]


def render_v2_eval_script(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> str:
    """从 v2 评分面渲染**完整** eval 脚本（形态对齐 SWE-Gym fork make_eval_script_list，安装段位置见模块头）。

    legacy（无 grader profile）路径以 root 整段执行；grader profile 路径不执行它，而是执行下面两个
    拆分脚本（F2）——三者由同一组行构成，不会分家。"""

    files = _v2_eval_preconditions(grading, test_files)
    reset = f"git checkout {grading.base_commit} {files}"
    lines = [
        *_V2_ENV_LINES,
        *_v2_vendor_env_lines(grading),
        *_v2_trusted_setup_lines(grading, files),
        *_v2_install_lines(grading),
        *_v2_candidate_test_lines(grading),
        reset,
    ]
    return "\n".join(lines) + "\n"


def _v2_attested_trusted_setup_lines(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> list[str]:
    """F2 + codex Wave3 §9.2：可信 setup 的**带成功判据**版本（只用于 grader profile 路径）。

    与官方单脚本形态（`render_v2_eval_script` 里那份，逐字不变）有两处刻意的差别，都是为了让
    "必需步骤是否成功"可判定，而不是给整段加 `set -e`：

    1. **恢复到基线**拆成逐文件：`base_commit` 里存在的 official test 文件必须 `git checkout` 成功
       （失败即整段 `exit 3`）；base 里不存在的路径（official test_patch 新增的测试文件、或改名的
       目标侧）跳过并记数。官方那条一次性 `git checkout <base> <全部路径>` 只要清单里有一个新增
       路径就会整条 pathspec 失败，把它当判据会把正常任务判成失败——这正是不能机械加 `set -e` 的原因。
    2. **应用 official test_patch** 的 `git apply` 返回码单独捕获进 `RH2_APPLY_RC`，交给自证尾段
       （`grader_trusted_setup_attest_lines`）判定并写进 root 属主自证文件，manager 读回后才允许
       启动候选测试。
    """

    files = _v2_eval_preconditions(grading, test_files)
    base = grading.base_commit
    return [
        "git status",
        "git show",
        f"git -c core.fileMode=false diff {base}",
        "RH2_RESTORED=0",
        f"for f in {files}; do",
        f'  if git cat-file -e {base}:"$f" 2>/dev/null; then',
        f'    git checkout {base} -- "$f" || {{ echo "RH2_SETUP_ERROR=official_test_restore_failed:$f"; exit 3; }}',
        "    RH2_RESTORED=$((RH2_RESTORED+1))",
        "  fi",
        "done",
        f"git apply -v - <<'{V2_EVAL_HEREDOC_DELIMITER}'",
        grading.test_patch,
        V2_EVAL_HEREDOC_DELIMITER,
        "RH2_APPLY_RC=$?",
        *grader_trusted_setup_attest_lines(test_files),
    ]


def render_v2_trusted_setup_script(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> str:
    """F2：root 可信 setup 半段——git status/show/diff、恢复 official test files、应用 official test_patch，
    并把结果写进 root 属主的自证文件（manager 读回判定后才启动候选测试）。
    候选代码在这一步之前不运行、之后再也改不了这些文件（manager 随后做属主/权限布置）。"""

    return "\n".join([*_V2_ENV_LINES, *_v2_vendor_env_lines(grading), *_v2_attested_trusted_setup_lines(grading, test_files)]) + "\n"


def render_v2_candidate_test_script(grading: PrivateGradingBundleV2, test_files: Sequence[str]) -> str:
    """F2：候选执行用户半段——vendor env → 安装段 → 官方 Start/End 标记内的测试命令。不含最后的 reset
    （official files 对候选用户只读，reset 只是官方脚本的收尾整理，对 reward 无因果作用）。"""

    _v2_eval_preconditions(grading, test_files)  # eval_cmd 互检 + 测试文件非空（文件清单本段不再直接使用）
    return "\n".join([*_V2_ENV_LINES, *_v2_vendor_env_lines(grading), *_v2_install_lines(grading), *_v2_candidate_test_lines(grading)]) + "\n"


_V2_OBS_ENV_LINES = (
    "#!/bin/bash",
    "set -o pipefail",  # 同上：conda 激活钩子不兼容 -u
    "source /opt/miniconda3/bin/activate",
    f"conda activate {V2_EVAL_CONDA_ENV}",
    f"cd {V2_EVAL_TESTBED}",
)

# 测试运行器完整性摘要：pytest/_pytest/pluggy 包目录内全部文件（路径 + 内容）的 sha256。
# 只作观察（D3=A 的真实代价：候选可在安装段改写运行器），不作闸门。
_V2_RUNNER_DIGEST_PY = r"""python - <<'RH2_OBS_EOF'
import hashlib, importlib.util, os
h = hashlib.sha256()
for pkg in ("pytest", "_pytest", "pluggy"):
    spec = importlib.util.find_spec(pkg)
    locs = list(spec.submodule_search_locations or []) if spec is not None else []
    if not locs:
        h.update((pkg + ":absent").encode()); continue
    for root in sorted(locs):
        for dp, dn, fn in os.walk(root):
            dn[:] = sorted(d for d in dn if d != "__pycache__")
            for f in sorted(fn):
                if f.endswith(".pyc"):
                    continue
                path = os.path.join(dp, f); h.update(path.encode())
                try:
                    with open(path, "rb") as fh:
                        h.update(fh.read())
                except OSError:
                    h.update(b"?")
print("RH2_OBS_RUNNER_DIGEST=" + h.hexdigest())
RH2_OBS_EOF"""


def render_v2_pre_candidate_observation_script(grading: PrivateGradingBundleV2) -> str:
    """S1-m：候选段之前的观测——运行器摘要基线 + 候选可写前缀属主。输出 `RH2_OBS_*=`。
    I1：脚本激活候选可写的 conda 环境并启动 Python（cwd=/testbed 在 sys.path 上），manager 以**候选身份**执行它；
    输出只作诊断线索，不是可信安装证明。"""
    return "\n".join([
        *_V2_OBS_ENV_LINES,
        _V2_RUNNER_DIGEST_PY,
        "echo \"RH2_OBS_PREFIX_OWNER=$(stat -c '%u' /opt/miniconda3/envs/testbed 2>/dev/null || echo absent)\"",
    ]) + "\n"


def render_v2_post_candidate_observation_script(grading: PrivateGradingBundleV2) -> str:
    """S1-m：候选段之后的观测——运行器摘要（与基线比对得 runner_integrity_changed）、包导入路径与版本串
    （可编辑安装应指向 /testbed；`.dirty` 版本串只是线索，安装是否生效以实际产物对照为准）。
    I1：直接 import 候选包，manager 以候选身份执行；只进诊断 sidecar。"""
    lines = [*_V2_OBS_ENV_LINES, _V2_RUNNER_DIGEST_PY]
    module = derive_import_probe_module(grading.repo_key_lower)
    if module is not None:
        probe = (
            f"python -c \"import {module}, sys; print('RH2_OBS_IMPORT_PATH=' + str(getattr({module}, '__file__', '?')));"
            f" print('RH2_OBS_PKG_VERSION=' + str(getattr({module}, '__version__', '?')))\" 2>/dev/null"
            " || echo RH2_OBS_IMPORT_PATH=import_failed"
        )
        lines.append(probe)
    return "\n".join(lines) + "\n"


def render_v2_compile_probe_script(paths: Sequence[str]) -> str:
    """第四组 P-A / F3：候选改动 .py 路径的内存内 compile() 复证——与测试同一 conda 环境、同一解释器，
    manager 以候选身份执行（不 import、不写字节码）。框架无关的脚本体在 grading.manager.render_compile_probe_script。"""
    return render_compile_probe_script(paths, env_lines=_V2_OBS_ENV_LINES)


def build_grading_spec_from_host_view(
    view: HostGradingView, *, image: str, image_manifest_digest: str, env_qualification: "EnvQualification | None" = None,
) -> GradingEnvSpec:
    """actor 内从 safe view 构造评分 spec：parser 闭包只捕获评分面 bundle（无 golden）。
    `env_qualification`（P-A）：调用方（driver / 正式链）从资格账本取得的环境资格记录；manager 自行核对镜像身份
    与脚本摘要，不符视同缺席。

    两个入口（replay driver、`PreparedTaskFace.grading_spec()`）共用这一处，按评分面的 `schema_id` 分派
    （R2E 接线 §3.6）：R2E 走 `r2e_grading_scripts.build_r2e_grading_spec`，来源语义也在那里确定。"""

    grading = view.grading
    if isinstance(grading, PrivateGradingBundleR2E):
        from repoharness2.adapters.slime.r2e_grading_scripts import build_r2e_grading_spec

        return build_r2e_grading_spec(
            task_id=view.task_id, grading=grading, image=image,
            image_manifest_digest=image_manifest_digest, env_qualification=env_qualification,
        )
    if not isinstance(grading, PrivateGradingBundleV2):
        raise GradingMaterialsError(
            "grading_bundle_type_unknown", f"{view.task_id}: 未知评分面类型 {type(grading).__name__}，拒绝构造评分 spec。"
        )
    test_files = tuple(sorted(patch_touched_paths(grading.test_patch)))

    def _parse(log_text: str) -> scoring.EvalVerdict:
        # S1-b：v2 入口——vendored SWE-Gym parser + 只解析标记段（不回退整份日志）
        return scoring.parse_eval_log_v2(grading, log_text)

    return GradingEnvSpec(
        task_id=view.task_id,
        image=image,
        base_commit=grading.base_commit,
        image_manifest_digest=image_manifest_digest,
        eval_script=render_v2_eval_script(grading, test_files),
        # F2：grader profile 路径按 root setup / 候选测试两步执行（与完整脚本同一组行）
        trusted_setup_script=render_v2_trusted_setup_script(grading, test_files),
        candidate_test_script=render_v2_candidate_test_script(grading, test_files),
        pre_candidate_observation_script=render_v2_pre_candidate_observation_script(grading),
        post_candidate_observation_script=render_v2_post_candidate_observation_script(grading),
        render_compile_probe=render_v2_compile_probe_script,
        env_qualification=env_qualification,
        parse_log=_parse,
        grader_version=f"swebench-{scoring.swebench_version()}+{SWEGYM_PARSERS_VERSION_TAG}",
        hygiene=HygieneRules(
            test_files=test_files,
            test_globs=(),  # 第四组 P-B：不再按测试名通配剔除候选改动；观测进 sidecar
            forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
        ),
        checkout_mode="image_embedded",
    )


# ---------------------------------------------------------------------------
# R2E 正式 actor 任务面（E09 + D4=B，2026-09-25）
# ---------------------------------------------------------------------------
# R2E 的来源镜像不能直接给解题者：`/r2e_tests`（隐藏测试）对所有用户可读，git 的分支上有修复提交。环境侧为每题构建
# 派生镜像（隐藏测试移到 root 私有目录、清掉修复提交、解释器搬出 /root），用覆盖表（EnvironmentOverlayV1）登记。
# 回放评分早已按覆盖表用派生镜像；这里让正式 actor 的两侧（rollout 容器与评分容器）也只用派生镜像，并按 R2E 的
# 实际环境给激活脚本与解释器前缀（/testbed/.venv，不是 SWE-Gym 的 conda testbed）。缺覆盖条目 = 构造即拒，不回退。
R2E_TASK_SOURCE = "r2e_gym_subset"
R2E_INTERPRETER_PREFIX = "/testbed/.venv"
# 与派生镜像的 ENV（PATH 首项 /testbed/.venv/bin、VIRTUAL_ENV=/testbed/.venv）一致；经 BASH_ENV 显式给出，
# 不依赖 exec 时是否继承镜像 ENV。不额外设 PYTHONPATH：部分仓库要 cwd=/testbed 或 `python -m pytest` 才能导入，
# 这是来源环境本来的条件，写在中性环境说明里，不在这里悄悄改变。
R2E_VENV_ACTIVATION = (
    "# rh2 envpack (R2E): run every non-interactive bash command with the /testbed/.venv interpreter.\n"
    "export VIRTUAL_ENV=/testbed/.venv\n"
    'export PATH="/testbed/.venv/bin:$PATH"\n'
)
# 正式 actor 的覆盖表输入（与 prepared 产物同纪律：路径与摘要成对给出，缺一即拒）。bringup 目前不显式传参，
# `PreparedTaskFace.load` 在调用方未传时从这两个环境变量读取。
IMAGE_OVERLAYS_PATH_ENV = "RH2_IMAGE_OVERLAYS_PATH"
IMAGE_OVERLAYS_SHA256_ENV = "RH2_IMAGE_OVERLAYS_SHA256"


def overlay_binding_mismatch(overlay: EnvironmentOverlayV1, *, public: Any, grading: Any) -> str | None:
    """覆盖条目与环境包 / 评分面的静态互检（回放与正式 actor 共用）；返回原因文本或 None。

    - 派生镜像必须是从这道题记录的来源镜像构建的；
    - R2E：隐藏测试的私有位置与树摘要要等于评分面，配方要自报已搬迁解释器、清理 git；本题修订若只在特定环境
      下成立（`environment_overlay.REVISION_ENV_REQUIREMENTS`，例 orange3 的 r2e-mr-020 需要 SciPy 1.5.4），配方身份必须
      带上那一步，配方内容摘要也必须是批准并复验过的那一份（Codex 批次三复核 F1、09-25 复核 R1）。"""

    if (overlay.base_image_ref, overlay.base_image_manifest_digest) != (public.image, public.image_manifest_digest):
        return "overlay:base_image_mismatch"  # 派生镜像不是从这道题的来源镜像构建的（或环境包记录的来源镜像已换）
    if isinstance(grading, PrivateGradingBundleR2E):
        from repoharness2.adapters.slime.r2e_grading_scripts import R2E_PRIVATE_HIDDEN_TESTS_DIR

        if overlay.facts.hidden_tests_location != R2E_PRIVATE_HIDDEN_TESTS_DIR:
            return f"overlay:hidden_tests_location_mismatch:{overlay.facts.hidden_tests_location}"
        if overlay.facts.hidden_tests_tree_sha256 != grading.hidden_tests_tree_sha256:
            return "overlay:hidden_tests_tree_mismatch"
        if not (overlay.facts.interpreter_relocated and overlay.facts.git_scrubbed):
            return "overlay:recipe_facts_incomplete"
        env_error = env_requirement_mismatch(overlay.recipe_id, grading.material_revisions, recipe_sha256=overlay.recipe_sha256)
        if env_error is not None:
            return "overlay:" + env_error
    return None


def rollout_spec_from_view(
    view: RolloutTaskView, *, time_budget_seconds: int, overlay: EnvironmentOverlayV1 | None = None,
) -> RolloutTaskSpec:
    """RolloutTaskView → 模型侧任务面（grading_spec=None：只带 digest 锚）。

    R2E（E09 + D4=B）：必须给覆盖条目；镜像用派生镜像的 image ID（不可重指），走 `image_local_build` 豁免
    registry digest 比对；激活脚本与解释器前缀用 R2E 的 `.venv`。其它来源不接受覆盖条目（未定义，不猜）。"""

    public = view.public
    common = dict(
        task_id=view.task_id,
        base_commit=public.base_commit,
        prompt=render_user_prompt(public),
        public_bundle_payload=public.model_dump_json(indent=2).encode("utf-8"),
        public_bundle_digest=view.public_bundle_digest,
        grading_spec=None,
        workdir=public.workdir,
        time_budget_seconds=time_budget_seconds,
    )
    if view.source == R2E_TASK_SOURCE:
        if overlay is None:
            raise PreparedTasksError(
                f"{view.task_id}: R2E 任务在正式 actor 里必须用派生镜像，但覆盖表里没有这道题——来源镜像里隐藏测试"
                "与修复提交对解题者可见，拒绝回退到来源镜像"
            )
        if overlay.task_id != view.task_id:
            raise PreparedTasksError(f"{view.task_id}: 覆盖条目属于 {overlay.task_id}")
        if (overlay.base_image_ref, overlay.base_image_manifest_digest) != (public.image, public.image_manifest_digest):
            raise PreparedTasksError(f"{view.task_id}: 覆盖条目的来源镜像与任务面记录不符（overlay:base_image_mismatch）")
        return RolloutTaskSpec(
            **common,
            image=overlay.derived_image_id,
            image_manifest_digest=None,
            image_local_build=True,
            env_activation_script=R2E_VENV_ACTIVATION,
            expected_interpreter_prefix=R2E_INTERPRETER_PREFIX,
        )
    if overlay is not None:
        raise PreparedTasksError(f"{view.task_id}: 来源 {view.source} 没有定义派生镜像覆盖，拒绝使用覆盖条目")
    return RolloutTaskSpec(**common, image=public.image, image_manifest_digest=public.image_manifest_digest)


def load_overlays_input(path: Path | str | None, sha256: str | None) -> dict[str, EnvironmentOverlayV1]:
    """覆盖表输入：路径与文件摘要（裸 hex 或 `sha256:` 前缀）成对给出；都没给时读环境变量；都缺 = 空表。"""

    if path is None and sha256 is None:
        path, sha256 = os.environ.get(IMAGE_OVERLAYS_PATH_ENV) or None, os.environ.get(IMAGE_OVERLAYS_SHA256_ENV) or None
    if path is None and sha256 is None:
        return {}
    if not path or not sha256:
        raise PreparedTasksError(
            f"覆盖表输入要求路径与摘要成对给出（{IMAGE_OVERLAYS_PATH_ENV} / {IMAGE_OVERLAYS_SHA256_ENV}），缺一即拒"
        )
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256.removeprefix("sha256:"):
        raise PreparedTasksError(f"覆盖表文件摘要不符：actual={actual[:16]}… expected={sha256.removeprefix('sha256:')[:16]}…")
    try:
        return parse_environment_overlays(data.decode("utf-8"), name=Path(path).name)
    except EnvironmentOverlayError as exc:
        raise PreparedTasksError(f"覆盖表内容非法：{exc}") from exc


class PreparedTaskFace:
    """actor 内任务面：公开 RolloutTaskSpec 表 + host 侧 HostGradingView 表 + manifest 记录。"""

    def __init__(
        self,
        *,
        manifest: PreparedTasksManifest,
        rollout_views: dict[str, RolloutTaskView],
        host_grading_views: dict[str, HostGradingView],
        time_budget_seconds: int,
    
        qualifications: Mapping[str, EnvQualification] | None = None,
        image_overlays: Mapping[str, EnvironmentOverlayV1] | None = None,
    ) -> None:
        if set(rollout_views) != set(manifest.task_ids()) or set(host_grading_views) != set(manifest.task_ids()):
            raise PreparedTasksError("任务面两侧视图集合与 manifest 不一致，拒绝构造")
        self._manifest = manifest
        self._rollout_views = rollout_views
        self._host_grading_views = host_grading_views
        # 第四组 P-A（A 线复核 R5）：正式 actor 的环境资格入口——按 task_id 的资格记录由流水线阶段随题包冻结后传入；
        # 缺席（当前默认）= 全局执行失败一律未确定（infra、无 reward），不会误判候选。
        self._qualifications: dict[str, EnvQualification] = dict(qualifications or {})
        # E09 + D4=B：只取本题包里的题的覆盖条目（覆盖表可以覆盖整个来源池）；构造时静态互检，不符即拒
        overlays = dict(image_overlays or {})
        self._overlays: dict[str, EnvironmentOverlayV1] = {}
        for tid in manifest.task_ids():
            overlay = overlays.get(tid)
            if overlay is None:
                continue
            error = overlay_binding_mismatch(overlay, public=rollout_views[tid].public, grading=host_grading_views[tid].grading)
            if error is not None:
                raise PreparedTasksError(f"{tid}: 覆盖条目与题包不配套（{error}），拒绝构造任务面")
            self._overlays[tid] = overlay
        self._specs = {
            tid: rollout_spec_from_view(view, time_budget_seconds=time_budget_seconds, overlay=self._overlays.get(tid))
            for tid, view in rollout_views.items()
        }

    @classmethod
    def load(
        cls,
        *,
        prepared_dir: Path | str,
        manifest_sha256: str | None,
        host_grading_path: Path | str | None,
        host_grading_sha256: str | None,
        time_budget_seconds: int,
        prompt_data_path: Any = None,
        image_overlays_path: Path | str | None = None,
        image_overlays_sha256: str | None = None,
    ) -> "PreparedTaskFace":
        """从两份产物加载（全部复核）。``manifest_sha256`` = trusted-prep 输出的外部 manifest
        digest（`RH2_PREPARED_TASKS_MANIFEST_SHA256`，输入身份而非授权闸门），缺失/不符即拒；
        ``prompt_data_path`` 非 None 时把 miles 数据源读的文件与 prep 的 prompts.jsonl 按内容
        digest 绑定。

        ``image_overlays_path`` / ``image_overlays_sha256``（E09 + D4=B）：派生镜像覆盖表与其文件摘要，成对给出；
        都没传时从 `RH2_IMAGE_OVERLAYS_PATH` / `RH2_IMAGE_OVERLAYS_SHA256` 读取；只给一个或摘要不符即拒。
        题包里有 R2E 题而没有覆盖表时，构造任务面即拒（不回退来源镜像）。"""

        if not host_grading_path or not host_grading_sha256:
            raise PreparedTasksError(
                "prepared 链要求同时给出 runtime-private 产物的 opaque 路径与期望 sha256"
                "（RH2_HOST_GRADING_ARTIFACT_PATH / RH2_HOST_GRADING_ARTIFACT_SHA256）"
            )
        manifest = load_prepared_manifest(prepared_dir, expected_sha256=manifest_sha256)
        rollout_views = load_prepared_rollout_views(prepared_dir, manifest)
        host_views = load_host_grading_views(host_grading_path, expected_sha256=host_grading_sha256, manifest=manifest)
        if prompt_data_path is not None:
            verify_prompt_data_binding(prompt_data_path, manifest)
        return cls(
            manifest=manifest,
            rollout_views=rollout_views,
            host_grading_views=host_views,
            time_budget_seconds=time_budget_seconds,
            image_overlays=load_overlays_input(image_overlays_path, image_overlays_sha256),
        )

    @property
    def manifest(self) -> PreparedTasksManifest:
        return self._manifest

    def task_ids(self) -> tuple[str, ...]:
        return self._manifest.task_ids()

    def verify_dispatch(self, assignment: Any) -> None:
        """F4 绑定时的 manifest 核对：分派三元组必须是 manifest 同一行记录的值。"""

        rec = self._manifest.record(assignment.task_id)
        if (
            rec.environment_package_digest != assignment.environment_package_digest
            or rec.public_bundle_digest != assignment.public_bundle_digest
        ):
            raise PreparedTasksError(
                f"{assignment.task_id}: 分派 digest 与 prepared manifest 记录不符——不是 host 原始分派的三元组"
            )

    def rollout_spec(self, task_id: str) -> RolloutTaskSpec:
        spec = self._specs.get(task_id)
        if spec is None:
            raise PreparedTasksError(f"unknown task_id（prepared 任务面不存在）: {task_id!r}")
        return spec

    def grading_spec(self, assignment: Any) -> GradingEnvSpec:
        """按 attempt 绑定的分派取评分材料：manifest 核对 → digest 贯穿核对 → revalidated() → 构造 spec。"""

        try:
            self.verify_dispatch(assignment)
        except PreparedTasksError as exc:
            raise GradingMaterialsError("grading_dispatch_not_authoritative", str(exc)) from exc
        view = self._host_grading_views.get(assignment.task_id)
        if view is None:
            raise GradingMaterialsError(
                "grading_view_missing", f"{assignment.task_id}: actor 内没有对应的 host grading 视图。"
            )
        if view.environment_package_digest != assignment.environment_package_digest:
            raise GradingMaterialsError(
                "grading_environment_digest_mismatch",
                f"{assignment.task_id}: attempt 绑定的 environment_package_digest 与 host grading 视图不符——拒绝评分 join。",
            )
        try:
            view = view.revalidated()
        except Exception as exc:  # noqa: BLE001 - 消费时刻重验失败即拒绝
            raise GradingMaterialsError(
                "grading_view_revalidation_failed", f"{assignment.task_id}: host grading 视图消费时刻重验失败：{exc}"
            ) from exc
        rollout_view = self._rollout_views[assignment.task_id]
        spec = build_grading_spec_from_host_view(
            view,
            image=rollout_view.public.image,
            image_manifest_digest=rollout_view.public.image_manifest_digest,
            env_qualification=self._qualifications.get(assignment.task_id),  # P-A 资格入口（R5）
        )
        overlay = self._overlays.get(assignment.task_id)
        if overlay is not None:
            # E09 + D4=B：评分容器与 rollout 容器用同一张派生镜像，按 image ID 启动（不可重指），资格键随 ID
            spec = dataclasses.replace(
                spec, image=overlay.derived_image_id, image_manifest_digest=None, image_local_build=True,
                image_local_build_id=overlay.derived_image_id,
            )
        return spec


__all__ = [
    "R2E_INTERPRETER_PREFIX",
    "R2E_TASK_SOURCE",
    "R2E_VENV_ACTIVATION",
    "V2_EVAL_END_MARKER",
    "V2_EVAL_START_MARKER",
    "GradingMaterialsError",
    "PreparedTaskFace",
    "build_grading_spec_from_host_view",
    "load_overlays_input",
    "overlay_binding_mismatch",
    "render_v2_candidate_test_script",
    "render_v2_eval_script",
    "render_v2_trusted_setup_script",
    "rollout_spec_from_view",
]
