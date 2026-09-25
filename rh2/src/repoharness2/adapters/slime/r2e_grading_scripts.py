"""R2E-Gym-Subset 的评分脚本渲染与 spec 构造（R2E 接线 R-c，2026-09-20）。

与 `prepared_task_face` 里 SWE v2 那组渲染器并列；两个入口（replay driver、`PreparedTaskFace.grading_spec()`）
都经 `build_grading_spec_from_host_view` 按评分面的 `schema_id` 分派到这里，没有第二份 R2E 逻辑。

grader 内的顺序（manager 既有流程不变）：基线重建比对 → 应用候选 delta → **可信 setup（root）** →
属主 / 权限布置 → 候选前观测 → **候选测试段（uid 54322）** → 候选后观测 →（需要时）编译复证。

可信 setup 做四件事，全部成功后才置自证尾段要的成功状态（B 线 B3：该 helper 的 `RH2_APPLY_RC` 缺省为 1）：

1. `rm -rf /testbed/r2e_tests`，再从派生镜像的 root 私有位置原样复制隐藏测试——候选 delta 里任何落在
   `r2e_tests/` 下的文件（包括它自己新建的 `conftest.py`）都在这一步被清掉；
2. 按 bundle 逐字节重写 `/testbed/run_tests.sh`（base64 传输，原文没有行尾换行）——agent 对入口的改动被覆盖；
3. 复算隐藏测试树摘要与入口摘要，与 bundle 不符 → `exit 3`，候选测试不启动（manager 归 infra）；
4. 复用 `grader_trusted_setup_attest_lines`：official 清单 = `r2e_tests/<每个隐藏测试文件>` + `run_tests.sh`，
   随后 manager 的权限布置把它们收回 root、祖先目录加 sticky。

候选段没有安装段（R2E 镜像自带装好的 `.venv`；打 `RH2_INSTALL_SKIPPED=1`），入口就是来源的
`bash run_tests.sh`——不加 `-q`、不加插件、不改命令：入口一变，`short test summary info` 段的内容就变，
期望映射是用这个入口生成的。

不处理的边界（用户决定 DR4，本片不宣称防作弊完备）：候选代码本来就运行在测试进程里（仓库根 `conftest.py`、
被测包的 import 期代码），它能在 sticky 目录里新建 official 清单之外的文件、能向 stdout 打印同形的摘要段。
"""

from __future__ import annotations

import base64
import shlex
from collections.abc import Sequence

from repoharness2.adapters.slime.sandbox_profile import grader_trusted_setup_attest_lines
from repoharness2.envpack import scoring
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleR2E
from repoharness2.envpack.r2e_parsers import R2E_GRADER_VERSION_TAG
from repoharness2.grading.manager import (
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    EnvQualification,
    GradingEnvSpec,
    HygieneRules,
    render_compile_probe_script,
)

R2E_TESTBED = "/testbed"
R2E_TESTS_DIRNAME = "r2e_tests"
R2E_ENTRY_FILENAME = "run_tests.sh"
# 与派生镜像配方的约定（用户决定 DR3=A）：隐藏测试搬到只有 root 可读的私有位置；`/r2e_tests` 与
# `/testbed/r2e_tests` 在派生镜像里都不存在。环境覆盖表的 `facts.hidden_tests_location` 必须等于它。
R2E_PRIVATE_HIDDEN_TESTS_DIR = "/rh2_private/r2e_tests"
# 测试入口写死的解释器（相对 /testbed）：观测与编译复证点名同一个，不依赖 PATH。
R2E_VENV_PYTHON = "/testbed/.venv/bin/python"

# R2E 八个仓库的包导入名（只给候选后观测的"导入路径探针"用，纯诊断）。
_R2E_IMPORT_PROBE_MODULES: dict[str, str] = {
    "aiohttp": "aiohttp",
    "coveragepy": "coverage",
    "datalad": "datalad",
    "numpy": "numpy",
    "orange3": "Orange",
    "pandas": "pandas",
    "pillow": "PIL",
    "scrapy": "scrapy",
}

_R2E_ROOT_ENV_LINES = (
    "#!/bin/bash",
    "set -o pipefail",
    f"cd {R2E_TESTBED}",
    f"git config --global --add safe.directory {R2E_TESTBED}",
)

_R2E_CANDIDATE_ENV_LINES = (
    "#!/bin/bash",
    "set -o pipefail",
    f"cd {R2E_TESTBED}",
)


def r2e_official_files(grading: PrivateGradingBundleR2E) -> tuple[str, ...]:
    """official 文件清单（相对 /testbed）：每个隐藏测试文件 + 入口脚本。同时是 `HygieneRules.test_files`——
    候选对这些路径的改动按 D2-3 不重放。"""

    # 按路径排序：清单进脚本渲染与资格键的脚本摘要，不随 bundle 内的条目顺序变
    return tuple(sorted(f"{R2E_TESTS_DIRNAME}/{f.path}" for f in grading.hidden_test_files)) + (R2E_ENTRY_FILENAME,)


def _restore_lines(grading: PrivateGradingBundleR2E, hidden_tests_dir: str) -> list[str]:
    """隐藏测试恢复 + 入口重写 + 摘要复算（不含自证尾段）。任何一步失败 `exit 3`。"""

    src = shlex.quote(hidden_tests_dir)
    tests = f"{R2E_TESTBED}/{R2E_TESTS_DIRNAME}"
    entry = f"{R2E_TESTBED}/{R2E_ENTRY_FILENAME}"
    entry_b64 = base64.b64encode(grading.run_tests_sh.encode("utf-8")).decode("ascii")
    want_tree = grading.hidden_tests_tree_sha256.removeprefix("sha256:")
    want_entry = grading.run_tests_sh_sha256.removeprefix("sha256:")
    return [
        "git status --short | head -n 200",  # 审计：候选 delta 应用后的工作区状态（R2E 初态本来就不是干净树，不做 reset）
        f'[ -d {src} ] && [ ! -L {src} ] || {{ echo "RH2_SETUP_ERROR=hidden_tests_source_missing:{hidden_tests_dir}"; exit 3; }}',
        f"rm -rf {tests}",
        f'cp -r {src} {tests} || {{ echo "RH2_SETUP_ERROR=hidden_tests_copy_failed"; exit 3; }}',
        # 私有位置若带着字节码缓存，不带进工作区（树摘要的定义也不含它）
        f"find {tests} -type d -name __pycache__ -prune -exec rm -rf {{}} +",
        f"rm -rf {entry}",
        f"printf '%s' {shlex.quote(entry_b64)} | base64 -d > {entry}"
        ' || { echo "RH2_SETUP_ERROR=entry_rewrite_failed"; exit 3; }',
        # 树摘要定义见 envpack.bundles_v2.r2e_hidden_tests_tree_digest（两侧同一条流水线）
        f"RH2_TREE=$(cd {tests} && find . -type f -not -path '*/__pycache__/*' -print0"
        " | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)",
        f"RH2_ENTRY=$(sha256sum {entry} | cut -d' ' -f1)",
        'echo "RH2_SETUP_HIDDEN_TESTS_TREE=$RH2_TREE"',
        'echo "RH2_SETUP_ENTRY_SHA256=$RH2_ENTRY"',
        f'[ "$RH2_TREE" = "{want_tree}" ] || {{ echo "RH2_SETUP_ERROR=hidden_tests_tree_mismatch:$RH2_TREE"; exit 3; }}',
        f'[ "$RH2_ENTRY" = "{want_entry}" ] || {{ echo "RH2_SETUP_ERROR=run_tests_sh_mismatch:$RH2_ENTRY"; exit 3; }}',
    ]


def _candidate_test_lines() -> list[str]:
    return [
        "echo RH2_INSTALL_SKIPPED=1",
        'echo "RH2_TS_TEST_START=$(date +%s.%N)"',
        f"echo {shlex.quote(scoring.R2E_EVAL_START_MARKER)}",
        f"bash {R2E_ENTRY_FILENAME}",
        "RH2_TEST_RC=$?",  # 入口脚本的退出码：期望里有 FAILED / ERROR 键的题，gold 也会是非 0（只进诊断与 P-A）
        f"echo {shlex.quote(scoring.R2E_EVAL_END_MARKER)}",
        'echo "RH2_TEST_RC=$RH2_TEST_RC"',
        'echo "RH2_TS_TEST_END=$(date +%s.%N)"',
    ]


def render_r2e_trusted_setup_script(
    grading: PrivateGradingBundleR2E, *, hidden_tests_dir: str = R2E_PRIVATE_HIDDEN_TESTS_DIR,
) -> str:
    """root 可信 setup：恢复隐藏测试 → 重写入口 → 摘要核验 → **全部成功后**置成功状态 → 自证尾段。"""

    return "\n".join([
        *_R2E_ROOT_ENV_LINES,
        *_restore_lines(grading, hidden_tests_dir),
        "RH2_APPLY_RC=0",  # 复制、重写、两项摘要核验都过了才走到这里（B 线 B3）
        f"RH2_RESTORED={len(grading.hidden_test_files)}",
        *grader_trusted_setup_attest_lines(r2e_official_files(grading)),
    ]) + "\n"


def render_r2e_candidate_test_script(grading: PrivateGradingBundleR2E) -> str:
    """候选执行用户半段：无安装段；Start / End 标记之间只有来源入口 `bash run_tests.sh`。"""

    del grading  # 入口原文已由可信 setup 按 bundle 重写进 /testbed/run_tests.sh，本段不再内嵌
    return "\n".join([*_R2E_CANDIDATE_ENV_LINES, *_candidate_test_lines()]) + "\n"


def render_r2e_eval_script(
    grading: PrivateGradingBundleR2E, *, hidden_tests_dir: str = R2E_PRIVATE_HIDDEN_TESTS_DIR,
) -> str:
    """legacy（无 grader profile）路径的完整脚本：root 一口气执行恢复 + 测试。与两段拆分脚本由同一组行构成。"""

    return "\n".join([*_R2E_ROOT_ENV_LINES, *_restore_lines(grading, hidden_tests_dir), *_candidate_test_lines()]) + "\n"


def _runner_digest_py(interpreter: str) -> str:
    """测试运行器完整性摘要（与 SWE v2 观测同一口径，只换解释器；`-B` 不写字节码）。"""

    from repoharness2.adapters.slime.prepared_task_face import _V2_RUNNER_DIGEST_PY

    head, sep, rest = _V2_RUNNER_DIGEST_PY.partition("\n")
    assert head == "python - <<'RH2_OBS_EOF'" and sep  # SWE 常量形态变了就在这里炸，不静默拼出错脚本
    return f"{interpreter} -B - <<'RH2_OBS_EOF'\n{rest}"


def render_r2e_pre_candidate_observation_script(grading: PrivateGradingBundleR2E) -> str:
    """候选段之前的观测：运行器摘要基线 + `.venv` 属主。以候选身份执行，只进诊断。"""

    del grading
    return "\n".join([
        *_R2E_CANDIDATE_ENV_LINES,
        _runner_digest_py(R2E_VENV_PYTHON),
        f"echo \"RH2_OBS_PREFIX_OWNER=$(stat -c '%u' {R2E_TESTBED}/.venv 2>/dev/null || echo absent)\"",
    ]) + "\n"


def render_r2e_post_candidate_observation_script(grading: PrivateGradingBundleR2E) -> str:
    """候选段之后的观测：运行器摘要（与基线比得 runner_integrity_changed）+ 包导入路径与版本串。"""

    lines = [*_R2E_CANDIDATE_ENV_LINES, _runner_digest_py(R2E_VENV_PYTHON)]
    module = _R2E_IMPORT_PROBE_MODULES.get(grading.repo_key_lower)
    if module is not None:
        lines.append(
            f"{R2E_VENV_PYTHON} -B -c \"import {module}, sys;"
            f" print('RH2_OBS_IMPORT_PATH=' + str(getattr({module}, '__file__', '?')));"
            f" print('RH2_OBS_PKG_VERSION=' + str(getattr({module}, '__version__', '?')))\" 2>/dev/null"
            " || echo RH2_OBS_IMPORT_PATH=import_failed"
        )
    return "\n".join(lines) + "\n"


def render_r2e_compile_probe_script(paths: Sequence[str]) -> str:
    """P-A 编译复证：与测试同一个解释器（`.venv/bin/python -I -S`）、内存内 `compile()`、不 import、不写字节码。"""

    return render_compile_probe_script(paths, env_lines=_R2E_CANDIDATE_ENV_LINES, interpreter=R2E_VENV_PYTHON)


# ---------------------------------------------------------------------------
# rollout 侧预检（R-d）：派生环境对沙箱身份是否真的可用、答案是否真的不可达
# ---------------------------------------------------------------------------

R2E_PREFLIGHT_CHECKS: tuple[str, ...] = ("interpreter", "hidden_tests", "git_history")


def render_r2e_rollout_preflight_script(*, hidden_tests_dir: str = R2E_PRIVATE_HIDDEN_TESTS_DIR) -> str:
    """R2E 专属三条预检，**以 agent 身份**执行，失败即该题不进入候选阶段。

    位置约束（B 线 B1）：必须放在首次 census **之后**——`.venv/` 虽在排除区，它的路径清单摘要仍进基线身份；
    解释器预检用 `-B -I -S`（不写字节码、不加载 site），census 之后再跑是第二层保险。

    ① 沙箱身份能执行 `.venv/bin/python`（来源镜像的解释器在 0700 的 /root 下，48/48 跑不动）；
    ② 沙箱身份读不到隐藏测试的私有位置，且 `/r2e_tests`、`/testbed/r2e_tests` 不存在；
    ③ `git rev-list --children --all` 里 HEAD 没有子提交（来源镜像里修复提交是 HEAD 的直接子提交，不用网络就拿得到）。
    每条打印一行 `RH2_PREFLIGHT_<NAME>=ok|fail:<原因>`；判定在 `evaluate_r2e_rollout_preflight`。"""

    private = shlex.quote(hidden_tests_dir)
    return "\n".join([
        "#!/bin/bash",
        f"cd {R2E_TESTBED} || {{ echo RH2_PREFLIGHT_INTERPRETER=fail:no_testbed; exit 0; }}",
        f"if {R2E_VENV_PYTHON} -B -I -S -c pass >/dev/null 2>&1; then echo RH2_PREFLIGHT_INTERPRETER=ok;"
        " else echo RH2_PREFLIGHT_INTERPRETER=fail:not_executable_as_agent; fi",
        f"if [ -e /{R2E_TESTS_DIRNAME} ]; then echo RH2_PREFLIGHT_HIDDEN_TESTS=fail:root_copy_present;"
        f" elif [ -e {R2E_TESTBED}/{R2E_TESTS_DIRNAME} ]; then echo RH2_PREFLIGHT_HIDDEN_TESTS=fail:workdir_copy_present;"
        f" elif ls {private} >/dev/null 2>&1 || [ -r {private} ]; then echo RH2_PREFLIGHT_HIDDEN_TESTS=fail:private_location_readable;"
        " else echo RH2_PREFLIGHT_HIDDEN_TESTS=ok; fi",
        'RH2_HEAD=$(git rev-parse HEAD 2>/dev/null) || RH2_HEAD=""',
        'if [ -z "$RH2_HEAD" ]; then echo RH2_PREFLIGHT_GIT_HISTORY=fail:no_head;',
        'elif ! RH2_CHILDREN=$(git rev-list --children --all 2>/dev/null); then echo RH2_PREFLIGHT_GIT_HISTORY=fail:rev_list_failed;',
        'elif [ "$(printf \'%s\\n\' "$RH2_CHILDREN" | grep "^$RH2_HEAD" | wc -w | tr -d " ")" != "1" ];'
        " then echo RH2_PREFLIGHT_GIT_HISTORY=fail:head_has_children_or_is_unlisted;",
        "else echo RH2_PREFLIGHT_GIT_HISTORY=ok; fi",
    ]) + "\n"


def evaluate_r2e_rollout_preflight(stdout: str) -> list[str]:
    """预检输出 → 失败原因列表（空 = 全过）。缺行按失败计（脚本中途死掉不算通过）。"""

    seen: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("RH2_PREFLIGHT_") and "=" in line:
            key, _, value = line.partition("=")
            seen[key.removeprefix("RH2_PREFLIGHT_").lower()] = value.strip()
    return [f"{name}:{seen.get(name, 'fail:no_output')}" for name in R2E_PREFLIGHT_CHECKS if seen.get(name) != "ok"]


def build_r2e_grading_spec(
    *, task_id: str, grading: PrivateGradingBundleR2E, image: str, image_manifest_digest: str,
    env_qualification: "EnvQualification | None" = None,
    hidden_tests_dir: str = R2E_PRIVATE_HIDDEN_TESTS_DIR,
) -> GradingEnvSpec:
    """R2E 评分 spec。来源语义 `r2e_expected_map` 在这里（parser 运行之前）确定，manager 的所有报告分支都带它。"""

    def _parse(log_text: str) -> scoring.EvalVerdict:
        return scoring.parse_eval_log_r2e(grading, log_text)

    official = r2e_official_files(grading)
    return GradingEnvSpec(
        task_id=task_id,
        image=image,
        base_commit=grading.base_commit,
        image_manifest_digest=image_manifest_digest,
        eval_script=render_r2e_eval_script(grading, hidden_tests_dir=hidden_tests_dir),
        trusted_setup_script=render_r2e_trusted_setup_script(grading, hidden_tests_dir=hidden_tests_dir),
        candidate_test_script=render_r2e_candidate_test_script(grading),
        pre_candidate_observation_script=render_r2e_pre_candidate_observation_script(grading),
        post_candidate_observation_script=render_r2e_post_candidate_observation_script(grading),
        render_compile_probe=render_r2e_compile_probe_script,
        env_qualification=env_qualification,
        parse_log=_parse,
        grader_version=R2E_GRADER_VERSION_TAG,
        grading_semantics="r2e_expected_map",
        hygiene=HygieneRules(
            test_files=official,
            test_globs=(),  # 第四组 P-B：不按测试名通配剔除候选改动
            forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
        ),
        checkout_mode="image_embedded",  # 镜像自带 /testbed；初态不是干净树，不做任何 reset / clean
    )
