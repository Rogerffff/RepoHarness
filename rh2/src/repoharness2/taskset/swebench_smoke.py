"""SweSmokeTaskset：rh2 S0-7 的 SWE-bench Verified smoke 任务集（8 题，冻结题单）。

结构模板参照 `reference/verifiers/verifiers/v1/tasksets/harbor/taskset.py`（harbor 任务集），
但数据源不是 Harbor Hub，而是本包 `data/swe_smoke_tasks.json`（由
`rh2/experiments/s0_swe_smoke_prep.py` 从 SWE-bench Verified 冻结生成，含每题的官方
预构建镜像引用、manifest digest、官方 eval 脚本与 F2P/P2P 清单）。

职责划分（对应执行计划 S0-7 第 2 步）：

- 每题一个官方 x86_64 镜像（`Task.image`），Environment 会把它注入 verifiers
  DockerRuntime；`Task.workdir="/testbed"`，bash/edit 工具与评分命令都在 /testbed 下执行。
- prompt 用 instance 的 problem_statement 原文（仅加一行仓库定位头）；解题指引放
  system_prompt（default harness 会把它拼在自己的 bash/edit 说明之后作为 system 消息）。
- `setup`：确认镜像内 /testbed 已物化——fail-closed 校验两件事：base_commit 对象存在、
  HEAD 血缘正确（HEAD == base_commit，或 HEAD 是官方构建叠加的 "SWE-bench" 提交且
  HEAD^ == base_commit）。注意两个实测事实：官方镜像 HEAD 都不是 base_commit 本身
  （django-11099：HEAD=2a2861e0…，父=d26b2424…=base）；且 "SWE-bench" 提交**不保证
  内容为空**——astropy-14995 里它带 pyproject.toml 1 行官方环境修补，所以既不能用
  HEAD 等值、也不能用树内容等值判断，只能校验血缘；diff --stat base..HEAD 记进
  trace.info 作环境修补证据。git 状态记进 trace.info；另写入 /root/.rh2_bash_env（conda testbed 环境
  激活脚本），配合 runner 侧 harness.env 的 BASH_ENV 让 agent 的每次 bash 调用都在
  testbed 环境里（否则 `python`/`pip` 落在 miniconda base 环境，测试根本跑不起来）。
- `finalize`：harness 结束后、评分前，抓取 agent 对 /testbed 的 git diff 存证。
- `@reward resolved`：**同一个容器**里跑官方 eval 脚本（内容 = 官方 make_test_spec
  生成：git checkout 还原测试文件 → git apply golden test_patch → 官方测试命令，
  输出夹在 '>>>>> Start/End Test Output' 标记之间），然后用 swebench 官方
  grading 函数（get_logs_eval / get_eval_tests_report / get_resolution_status）解析
  F2P/P2P。reward = 1.0 当且仅当 resolution 状态为 RESOLVED_FULL（全部 F2P 通过且
  P2P 无一失败），其余为 0.0；F2P/P2P 通过率作为 metric 记录。

评分隔离声明（如实记录，S0 允许）：eval 在 agent 用过的同一容器/同一工作树上跑，
agent 理论上可以篡改测试基建（例如改 runtests.py 本体、恶意改 git 二进制）而本任务集
不设防。S0 只验证物化与评分解析链路；评分隔离是 S2 的验收项。

对 swebench 包的依赖是**惰性**的：模块 import 不需要 swebench（EnvConfig 校验会
import 本模块），只有 `@reward` 解析日志时才 import。运行机的 venv 需要
`uv pip install swebench==4.1.0`（S0 实验期临时依赖，未写入 pyproject）。
"""

import json
import logging
import time
from pathlib import Path

from pydantic import Field

import verifiers.v1 as vf

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "swe_smoke_tasks.json"

# 评分脚本与 agent 环境激活文件在容器内的落点（都用绝对路径，避开 workdir 依赖）。
EVAL_SCRIPT_PATH = "/tmp/rh2_swe_eval.sh"
BASH_ENV_PATH = "/root/.rh2_bash_env"
BASH_ENV_CONTENT = (
    "# rh2 S0-7: 让 agent 的每个非交互 bash 命令都运行在 conda testbed 环境里。\n"
    "source /opt/miniconda3/bin/activate testbed 2>/dev/null || true\n"
)

SYSTEM_PROMPT = (
    "You are a software engineer fixing a real GitHub issue in the repository "
    "checked out at /testbed (your bash tool already runs there).\n"
    "- The project's Python environment is a pre-activated conda env named "
    "`testbed`: `python`, `pip` and the repo's test tools already point at it.\n"
    "- Explore the code, find the root cause, and edit NON-TEST source files to fix "
    "the issue.\n"
    "- Do NOT modify test files: grading resets the test files to their original "
    "state before running the official test suite, so test edits never count.\n"
    "- You may run tests to verify your fix, but keep runs narrow (a single test "
    "file or module) to save time.\n"
    "- When you are confident the fix is complete, reply with a short summary and "
    "stop calling tools."
)

# trace.info 里各类文本存证的截断上限（字符）。eval 完整日志由 runner 侧另存文件。
DIFF_CAP = 60_000
LOG_TAIL_CAP = 20_000


class SweSmokeConfig(vf.TasksetConfig):
    tasks_file: Path = DATA_FILE
    """冻结题单数据文件（默认用包内 data/swe_smoke_tasks.json）。"""
    subset: list[str] | None = None
    """只加载这些 instance_id（None = 全部 8 题）。runner 用它做单题一进程的隔离运行。"""
    eval_log_dir: Path | None = None
    """非空时，把每题官方 eval 的完整原始日志写到该目录（宿主侧）
    `<instance_id>.eval.log`，作为"日志解析要点"的证据文件。"""


class SweSmokeTask(vf.Task):
    """在基础 Task 上带出 SWE instance 的标识字段（供评分与报告用）。

    golden patch / golden test_patch / eval 脚本**不**放在 Task 上：Task 会随
    trace dump 序列化，把答案带出去既污染证据又有泄漏到 prompt 的风险。评分需要的
    材料由 taskset 按 instance_id 从冻结数据行里取。
    """

    instance_id: str
    repo: str
    version: str
    base_commit: str
    fail_to_pass: list[str] = Field(default_factory=list)
    pass_to_pass: list[str] = Field(default_factory=list)
    test_cmd: str = ""


class SweSmokeTaskset(vf.Taskset[SweSmokeTask, SweSmokeConfig]):
    NEEDS_CONTAINER = True  # 只在 per-task 官方镜像里才有意义，拒绝 subprocess runtime

    def _rows(self) -> dict[str, dict]:
        """冻结数据行（instance_id -> 冻结条目），首次访问时加载并缓存。"""
        cached = getattr(self, "_rows_cache", None)
        if cached is None:
            payload = json.loads(Path(self.config.tasks_file).read_text())
            cached = {t["instance"]["instance_id"]: t for t in payload["tasks"]}
            self._rows_cache = cached
        return cached

    def load_tasks(self) -> list[SweSmokeTask]:
        rows = self._rows()
        wanted = self.config.subset or list(rows)
        unknown = [iid for iid in wanted if iid not in rows]
        if unknown:
            raise ValueError(f"subset 中的 instance 不在冻结题单里: {unknown}")
        tasks = []
        for idx, iid in enumerate(wanted):
            entry = rows[iid]
            inst = entry["instance"]
            prompt = (
                f"Fix the following issue from the `{inst['repo']}` repository "
                f"(checked out at /testbed, commit {inst['base_commit'][:12]}):\n\n"
                f"{inst['problem_statement']}"
            )
            tasks.append(
                SweSmokeTask(
                    idx=idx,
                    name=iid,
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    image=entry["image"],
                    workdir="/testbed",
                    instance_id=iid,
                    repo=inst["repo"],
                    version=inst["version"],
                    base_commit=inst["base_commit"],
                    fail_to_pass=entry["fail_to_pass"],
                    pass_to_pass=entry["pass_to_pass"],
                    test_cmd=entry["test_cmd"],
                )
            )
        return tasks

    async def setup(self, task: SweSmokeTask, trace: vf.Trace, runtime: vf.Runtime) -> None:
        """物化确认 + agent 环境注入。镜像本身已含 /testbed@base_commit，这里只核对不重建。"""
        await runtime.write(BASH_ENV_PATH, BASH_ENV_CONTENT.encode())
        probe = await runtime.run(
            [
                "bash",
                "-c",
                # safe.directory：容器内统一 root，通常非必需，但官方 eval 脚本也会设，
                # 提前设好让 agent rollout 期间的 git 命令行为与评分期一致。
                # 官方镜像 HEAD 是构建时叠加的 "SWE-bench" 提交（可能含环境修补，如
                # astropy 的 pyproject.toml pin），物化判据是 base_commit 对象存在 +
                # HEAD 血缘（HEAD==base 或 HEAD^==base），环境修补 diff 只记证据。
                "git config --global --add safe.directory /testbed; "
                "cd /testbed "
                '&& echo "HEAD=$(git rev-parse HEAD)" '
                f"&& (git cat-file -e {task.base_commit}^{{commit}} && echo BASE_OBJECT_OK) "
                '&& echo "PARENT=$(git rev-parse HEAD^ 2>/dev/null || echo none)" '
                f'&& echo "DIFFSTAT=$(git diff --stat {task.base_commit} HEAD | tail -1)" '
                "&& git status --porcelain | head -50",
            ],
            {},
        )
        lines = probe.stdout.strip().splitlines() if probe.exit_code == 0 else []
        tagged = {}
        dirty = []
        for line in lines:
            text = line.strip()
            if not text:
                continue
            if text == "BASE_OBJECT_OK":
                tagged["base_object_ok"] = True
            elif text.startswith(("HEAD=", "PARENT=", "DIFFSTAT=")):
                key, _, value = text.partition("=")
                tagged[key.lower()] = value.strip()
            else:
                dirty.append(text)
        head = tagged.get("head", "")
        lineage_ok = head == task.base_commit or tagged.get("parent") == task.base_commit
        trace.info["setup_git_head"] = head
        trace.info["setup_git_head_parent"] = tagged.get("parent", "")
        trace.info["setup_base_object_ok"] = tagged.get("base_object_ok", False)
        trace.info["setup_env_diffstat_vs_base"] = tagged.get("diffstat", "")
        trace.info["setup_git_dirty"] = dirty[:20]
        if probe.exit_code != 0 or not tagged.get("base_object_ok") or not lineage_ok:
            # fail-closed：/testbed 不在题目基线上，评分没有意义，直接判 setup 失败。
            raise RuntimeError(
                f"/testbed 物化校验失败: exit={probe.exit_code}, HEAD={head!r}, "
                f"HEAD^={tagged.get('parent')!r}, base_commit={task.base_commit!r}, "
                f"base_object_ok={tagged.get('base_object_ok', False)}; "
                f"stderr tail: {probe.stderr.strip()[-500:]}"
            )
        if dirty:
            logger.warning("%s: setup 时 /testbed 工作树非干净: %s", task.instance_id, dirty[:5])

    async def finalize(self, task: SweSmokeTask, trace: vf.Trace, runtime: vf.Runtime) -> None:
        """评分前抓取 agent 改动存证（git diff 不含未跟踪文件，另记 status）。"""
        diff = await runtime.run(
            ["bash", "-c", "cd /testbed && git -c core.fileMode=false diff"], {}
        )
        status = await runtime.run(
            ["bash", "-c", "cd /testbed && git status --porcelain"], {}
        )
        text = diff.stdout
        trace.info["agent_diff"] = text[:DIFF_CAP] + (
            f"\n...[truncated {len(text) - DIFF_CAP} chars]" if len(text) > DIFF_CAP else ""
        )
        trace.info["agent_git_status"] = status.stdout.strip().splitlines()[:50]

    @vf.reward
    async def resolved(self, task: SweSmokeTask, trace: vf.Trace, runtime: vf.Runtime) -> float:
        """同容器跑官方 eval 脚本 + swebench 官方 grading 解析，返回 0/1。

        解析方式（如实记录）：eval 脚本 stdout+stderr 合并成单流保序日志 →
        swebench.harness.grading.get_logs_eval（官方 MAP_REPO_TO_PARSER 按 repo 解析
        '>>>>> Start/End Test Output' 标记之间的测试输出，并检查 patch apply 失败等
        坏码）→ get_eval_tests_report 对照 F2P/P2P 清单 → get_resolution_status。
        注意官方语义：不在日志里出现的 F2P/P2P 测试按 "silent success" 计（见
        grading.get_eval_tests_report 的 check_pass_and_fail），我们原样沿用不加严。
        """
        entry = self._rows()[task.instance_id]
        await runtime.write(EVAL_SCRIPT_PATH, entry["eval_script"].encode())
        started = time.time()
        result = await runtime.run(
            # 2>&1 合并双流：官方脚本 set -x 的标记走 stderr、测试输出因 repo 而异，
            # 合并后才能按标记切出测试段（官方 harness 同样以合并流写 test_output.txt）。
            ["bash", "-c", f"bash {EVAL_SCRIPT_PATH} 2>&1"],
            {},
        )
        eval_seconds = time.time() - started
        log_text = result.stdout if result.stdout else result.stderr

        if self.config.eval_log_dir is not None:
            log_dir = Path(self.config.eval_log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{task.instance_id}.eval.log").write_text(log_text)

        verdict = parse_official_eval(entry["instance"], log_text)

        trace.record_metrics(
            {
                "f2p_rate": verdict["f2p_rate"],
                "p2p_rate": verdict["p2p_rate"],
                "eval_apply_ok": 1.0 if verdict["apply_ok"] else 0.0,
                "eval_exit_code": float(result.exit_code),
                "eval_seconds": round(eval_seconds, 1),
            }
        )
        trace.info["swe_eval"] = {
            "resolution": verdict["resolution"],
            "apply_ok": verdict["apply_ok"],
            "f2p_success": verdict["f2p_success"],
            "f2p_failure": verdict["f2p_failure"],
            "p2p_failure": verdict["p2p_failure"][:20],
            "p2p_total": len(task.pass_to_pass),
            "eval_seconds": round(eval_seconds, 1),
            "eval_exit_code": result.exit_code,
            "log_tail": log_text[-LOG_TAIL_CAP:],
        }
        return 1.0 if verdict["resolved"] else 0.0


def parse_official_eval(instance: dict, log_text: str) -> dict:
    """用 swebench 官方 grading 函数解析一份合并流 eval 日志。

    独立成模块级函数以便单测/复核单独调用。swebench 在此惰性 import。
    """
    import tempfile

    from swebench.harness.constants import FAIL_TO_PASS, PASS_TO_PASS, ResolvedStatus
    from swebench.harness.grading import (
        compute_fail_to_pass,
        compute_pass_to_pass,
        get_eval_tests_report,
        get_logs_eval,
        get_resolution_status,
    )
    from swebench.harness.test_spec.test_spec import make_test_spec

    spec = make_test_spec(instance, namespace="swebench", arch="x86_64")
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(log_text)
        log_path = f.name
    try:
        status_map, apply_ok = get_logs_eval(spec, log_path)
    finally:
        Path(log_path).unlink(missing_ok=True)

    gold = {
        FAIL_TO_PASS: json.loads(instance["FAIL_TO_PASS"]),
        PASS_TO_PASS: json.loads(instance["PASS_TO_PASS"]),
    }
    report = get_eval_tests_report(status_map, gold)
    resolution = get_resolution_status(report)
    return {
        "apply_ok": apply_ok,
        "resolution": resolution,
        "resolved": resolution == ResolvedStatus.FULL.value,
        "f2p_rate": compute_fail_to_pass(report),
        "p2p_rate": compute_pass_to_pass(report),
        "f2p_success": report[FAIL_TO_PASS]["success"],
        "f2p_failure": report[FAIL_TO_PASS]["failure"],
        "p2p_failure": report[PASS_TO_PASS]["failure"],
        "num_parsed_tests": len(status_map),
    }


__all__ = ["SweSmokeTaskset"]
