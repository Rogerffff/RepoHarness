"""SweSmokeTaskset：SWE-bench Verified smoke 8 题的 **verifiers 薄壳**（S1-2 拆分后形态）。

S0-7 版本把数据加载、/testbed 血缘校验、官方 parser 评分全写在本文件里；
S1-2 起这些全部下沉到框架无关的 `repoharness2.envpack` 库层，本文件只剩
"verifiers 协议适配"这一层皮：

    load_tasks   <- envpack.bundles.load_bundle_pairs（含 frozen_v1 防漂移校验）
                    Task 只携带 public bundle 字段（A6：私有评分材料不上 Task——
                    Task 会随 trace dump 序列化，S0-7 版挂在 Task 上的
                    fail_to_pass/pass_to_pass/test_cmd 已全部移除，评分时按
                    instance_id 从 private bundle 取）。
    setup        <- envpack.materialize（探针脚本生成 + 血缘判定：base_commit 对象
                    存在 且 HEAD==base 或 HEAD^==base，官方构建叠加的 "SWE-bench"
                    提交内容可非空——astropy-14995 带 1 行 pyproject.toml 环境修补；
                    本层只负责 runtime.write/runtime.run 与把证据写进 trace.info）。
    finalize        仍在本层：抓 agent 对 /testbed 的 git diff/status 存证
                    （纯 harness 证据动作，不涉库层判定）。
    @reward      <- envpack.scoring.parse_eval_log（官方 parser 三类：django
                    unittest verbose / sympy bin/test / pytest -rA 含 ANSI）；
                    eval 脚本来自 private bundle，reward = 1.0 当且仅当
                    RESOLVED_FULL（全部 F2P 通过且 P2P 无一失败）。

评分隔离声明（沿 S0 如实记录）：eval 仍在 agent 用过的同一容器/同一工作树上跑，
agent 理论上可篡改测试基建而本薄壳不设防；clean-checkout 重放与 patch hygiene
是 S1-4 SWEGradingManager 的验收项（A7），薄壳保持 S0-7 行为以维持 8 题回归可对照。

对 swebench 包的依赖仍是惰性的（库层评分时才 import；运行机 venv 需要
`uv pip install swebench==4.1.0`）；对 verifiers 的依赖只存在于本文件——
envpack 库层不 import verifiers（tests/envpack/test_no_verifiers_import.py 钉死）。
"""

import logging
import time
from pathlib import Path

import verifiers.v1 as vf

from repoharness2.envpack import bundles, materialize, scoring

logger = logging.getLogger(__name__)

# trace.info 里各类文本存证的截断上限（字符）。eval 完整日志由 runner 侧另存文件。
DIFF_CAP = 60_000
LOG_TAIL_CAP = 20_000


class SweSmokeConfig(vf.TasksetConfig):
    tasks_file: Path = bundles.TASKS_FILE
    """冻结题单数据文件（默认用 envpack 包内 data/swe_smoke_tasks.json）。"""
    frozen_file: Path | None = bundles.FROZEN_V1_FILE
    """frozen_v1 防漂移账本（默认逐题重算 digest 比对；None = 跳过，仅限自举/实验场景）。"""
    subset: list[str] | None = None
    """只加载这些 instance_id（None = 全部 8 题）。runner 用它做单题一进程的隔离运行。"""
    eval_log_dir: Path | None = None
    """非空时，把每题官方 eval 的完整原始日志写到该目录（宿主侧）
    `<instance_id>.eval.log`，作为"日志解析要点"的证据文件。"""


class SweSmokeTask(vf.Task):
    """verifiers Task + public bundle 的标识字段（全部是 A6 public 名单内的公开事实）。"""

    instance_id: str
    repo: str
    base_commit: str
    image_manifest_digest: str


class SweSmokeTaskset(vf.Taskset[SweSmokeTask, SweSmokeConfig]):
    NEEDS_CONTAINER = True  # 只在 per-task 官方镜像里才有意义，拒绝 subprocess runtime

    def _pairs(self) -> dict[str, bundles.BundlePair]:
        """instance_id -> BundlePair（首次访问时经库层加载 + frozen_v1 校验并缓存）。"""
        cached = getattr(self, "_pairs_cache", None)
        if cached is None:
            pair_list = bundles.load_bundle_pairs(
                tasks_file=self.config.tasks_file,
                subset=self.config.subset,
                frozen_file=self.config.frozen_file,
            )
            cached = {pair.instance_id: pair for pair in pair_list}
            self._pairs_cache = cached
        return cached

    def _rows(self) -> dict[str, dict]:
        """原始冻结条目（instance_id -> dict）。兼容入口：s0_swe_smoke runner 用它取
        image_manifest_digest 核对本地镜像；新代码请直接用 `_pairs()` 的 bundle。"""
        return dict(bundles.load_task_entries(self.config.tasks_file))

    def load_tasks(self) -> list[SweSmokeTask]:
        tasks = []
        for idx, pair in enumerate(self._pairs().values()):
            public = pair.public
            tasks.append(
                SweSmokeTask(
                    idx=idx,
                    name=public.instance_id,
                    prompt=bundles.render_user_prompt(public),
                    system_prompt=public.public_hints,
                    image=public.image,
                    workdir=public.workdir,
                    instance_id=public.instance_id,
                    repo=public.repo,
                    base_commit=public.base_commit,
                    image_manifest_digest=public.image_manifest_digest,
                )
            )
        return tasks

    async def setup(self, task: SweSmokeTask, trace: vf.Trace, runtime: vf.Runtime) -> None:
        """物化确认 + agent 环境注入。镜像本身已含 /testbed@base_commit，这里只核对不重建。"""
        await runtime.write(materialize.BASH_ENV_PATH, materialize.BASH_ENV_CONTENT.encode())
        probe = await runtime.run(
            ["bash", "-c", materialize.build_probe_script(task.base_commit)], {}
        )
        check = materialize.evaluate_probe(
            task.base_commit, probe.exit_code, probe.stdout, probe.stderr
        )
        trace.info.update(check.trace_info())
        # fail-closed：/testbed 不在题目基线上，评分没有意义，直接判 setup 失败
        # （MaterializeError 是 RuntimeError 子类，语义与 S0-7 一致）。
        check.ensure_ok()
        if check.dirty_paths:
            logger.warning(
                "%s: setup 时 /testbed 工作树非干净: %s", task.instance_id, check.dirty_paths[:5]
            )

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
        """同容器跑官方 eval 脚本（取自 private bundle），库层官方 parser 解析，返回 0/1。"""
        private = self._pairs()[task.instance_id].private
        await runtime.write(scoring.EVAL_SCRIPT_PATH, private.eval_script.encode())
        started = time.time()
        result = await runtime.run(
            # 2>&1 合并双流：官方脚本 set -x 的标记走 stderr、测试输出因 repo 而异，
            # 合并后才能按标记切出测试段（官方 harness 同样以合并流写 test_output.txt）。
            ["bash", "-c", f"bash {scoring.EVAL_SCRIPT_PATH} 2>&1"],
            {},
        )
        eval_seconds = time.time() - started
        log_text = result.stdout if result.stdout else result.stderr

        if self.config.eval_log_dir is not None:
            log_dir = Path(self.config.eval_log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{task.instance_id}.eval.log").write_text(log_text)

        verdict = scoring.parse_eval_log(private, log_text)

        trace.record_metrics(
            {
                "f2p_rate": verdict.f2p_rate,
                "p2p_rate": verdict.p2p_rate,
                "eval_apply_ok": 1.0 if verdict.apply_ok else 0.0,
                "eval_exit_code": float(result.exit_code),
                "eval_seconds": round(eval_seconds, 1),
            }
        )
        trace.info["swe_eval"] = {
            "resolution": verdict.resolution,
            "apply_ok": verdict.apply_ok,
            "f2p_success": verdict.f2p_success,
            "f2p_failure": verdict.f2p_failure,
            "p2p_failure": verdict.p2p_failure[:20],
            "p2p_total": len(private.pass_to_pass),
            "eval_seconds": round(eval_seconds, 1),
            "eval_exit_code": result.exit_code,
            "log_tail": log_text[-LOG_TAIL_CAP:],
        }
        return verdict.reward


__all__ = ["SweSmokeTaskset"]
