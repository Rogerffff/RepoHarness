"""契约测试 2：Rollout 生命周期调用序与 runtime 归属（rh2 S0-2）。

用自写的 SpyTaskset + FakeHarness（最小 Harness 子类，绝不调用模型）驱动真实的
`vf.Rollout.run()`（subprocess runtime），断言 rh2 依赖的生命周期行为：

1. 调用序固定：taskset.setup(task, trace, runtime) -> harness.setup ->
   harness.launch -> taskset.finalize -> taskset.score（@reward）；
   且 `Taskset.setup` 的签名含 trace 参数（执行计划 F6），框架按参数名注入。
2. harness 抛错时：finalize/score 被跳过、错误以 HarnessError 记录到 trace，
   但 runtime 仍然在 finally 里被 teardown（subprocess 的 /tmp workdir 被删除）。
3. score 在 runtime 存活期执行：@reward 里可以直接 runtime.run() 执行命令
   （rh2 的评分设计 5.2 依赖这一点——评分时还能读 agent 留下的现场）。

不依赖网络模型 API、不依赖 docker：runtime 全部走 SubprocessConfig；
FakeHarness.launch 直接返回 exit_code=0，模型 client 是一个"被调用即失败"的哨兵。
"""

import inspect

import verifiers.v1 as vf
from verifiers.v1.clients.client import Client, RolloutContext
from verifiers.v1.runtimes import ProgramResult, SubprocessConfig


class SentinelClient(Client):
    """哨兵 client：本测试里任何一次模型调用都是 bug。"""

    async def get_response(self, *args, **kwargs):  # pragma: no cover - 防御
        raise AssertionError("contract test must not call the model")


class SpyTaskset(vf.Taskset):
    """记录生命周期调用的最小 Taskset。

    calls 里每个元素是 (阶段名, 附加观测...)，用于断言调用顺序和调用时的
    runtime 状态（workdir 是否存在 == runtime 是否活着）。"""

    def __init__(self, config: vf.TasksetConfig, calls: list) -> None:
        super().__init__(config)
        self.calls = calls
        self.seen_trace: vf.Trace | None = None

    def load_tasks(self) -> list[vf.Task]:
        return [vf.Task(idx=0, prompt="noop task")]

    async def setup(self, task, trace, runtime) -> None:
        # 记录：框架把 task/trace/runtime 按参数名注入；此时 runtime 已 start。
        self.seen_trace = trace
        self.calls.append(
            (
                "taskset_setup",
                isinstance(task, vf.Task),
                isinstance(trace, vf.Trace),
                runtime.workdir is not None and runtime.workdir.exists(),
            )
        )

    async def finalize(self, task, trace, runtime) -> None:
        self.calls.append(("finalize", runtime.workdir.exists()))

    @vf.reward
    async def runtime_alive_at_scoring(self, trace, runtime) -> float:
        # 评分期在 runtime 里真实执行一条命令，证明 runtime 尚未 teardown。
        result = await runtime.run(["/bin/echo", "score-alive"], {})
        ok = result.exit_code == 0 and "score-alive" in result.stdout
        self.calls.append(("score", ok, runtime.workdir.exists()))
        return 1.0 if ok else 0.0


class FakeHarness(vf.Harness):
    """最小 Harness：不装任何东西、不跑任何 agent、不调模型。"""

    def __init__(self, config: vf.HarnessConfig, calls: list, fail: bool = False):
        super().__init__(config)
        self.calls = calls
        self.fail = fail

    async def setup(self, runtime) -> None:
        self.calls.append(("harness_setup", runtime.workdir.exists()))

    async def launch(
        self, ctx, trace, runtime, endpoint, secret, mcp_urls
    ) -> ProgramResult:
        # 记录 Rollout 注入的拦截 endpoint/secret（黑盒 harness 可训练的边界）。
        self.calls.append(
            (
                "launch",
                endpoint.startswith("http://") and endpoint.endswith("/v1"),
                bool(secret),
                mcp_urls == {},
            )
        )
        if self.fail:
            raise RuntimeError("fake harness exploded")
        return ProgramResult(exit_code=0, stdout="", stderr="")


def _make_rollout(calls: list, fail: bool = False) -> tuple[vf.Rollout, SpyTaskset]:
    taskset = SpyTaskset(vf.TasksetConfig(), calls)
    harness = FakeHarness(vf.HarnessConfig(id="fake"), calls, fail=fail)
    ctx = RolloutContext(
        model="never-called", client=SentinelClient(), sampling=vf.SamplingConfig()
    )
    rollout = vf.Rollout(
        task=taskset.load_tasks()[0],
        taskset=taskset,
        harness=harness,
        ctx=ctx,
        runtime_config=SubprocessConfig(),
    )
    return rollout, taskset


# ---------------------------------------------------------------------------
# 断言 1：调用序 + setup 签名含 trace（F6）
# ---------------------------------------------------------------------------


def test_taskset_setup_signature_declares_trace_parameter():
    # 基类签名就是注入契约：setup 声明 (task, trace, runtime)，
    # 框架用 invoke() 按参数名注入（rollout.py 里的 {"task","trace","runtime"}）。
    params = list(inspect.signature(vf.Taskset.setup).parameters)
    assert params == ["self", "task", "trace", "runtime"]


async def test_lifecycle_order_setup_harness_finalize_score():
    calls: list = []
    rollout, taskset = _make_rollout(calls)
    trace = await rollout.run()

    # 完整调用序（本测试的核心断言）。
    assert [c[0] for c in calls] == [
        "taskset_setup",
        "harness_setup",
        "launch",
        "finalize",
        "score",
    ]
    # setup 收到的 trace 就是 run() 最终返回的那一个（trace 先于 setup 存在，
    # taskset 可以在 setup 里往 trace/state 写 per-rollout 状态）。
    assert taskset.seen_trace is trace
    # setup 时注入的三个参数类型正确，且 runtime 已经 start（workdir 存在）。
    assert calls[0] == ("taskset_setup", True, True, True)
    # launch 拿到了 http endpoint + 非空 secret（interception 边界已建立）。
    assert calls[2] == ("launch", True, True, True)

    assert trace.error is None
    assert trace.is_completed is True
    assert trace.stop_condition == "agent_completed"
    # 正常路径下 runtime 也在 run() 返回前 teardown（workdir 已删除）。
    assert rollout.runtime is not None
    assert not rollout.runtime.workdir.exists()


# ---------------------------------------------------------------------------
# 断言 2：harness 抛错 -> 错误记录到 trace，runtime 仍在 finally teardown
# ---------------------------------------------------------------------------


async def test_harness_error_recorded_and_runtime_still_torn_down():
    calls: list = []
    rollout, _ = _make_rollout(calls, fail=True)
    trace = await rollout.run()  # 不应向外抛异常：坏 rollout 是数据，不是 crash

    # harness 失败后不再进入 finalize/score。
    assert [c[0] for c in calls] == ["taskset_setup", "harness_setup", "launch"]
    # 错误被 boundary 归因为 HarnessError 并记录在 trace 上。
    assert trace.error is not None
    assert trace.error.type == "HarnessError"
    assert "fake harness exploded" in trace.error.message
    assert trace.is_completed is True
    assert trace.stop_condition == "error"
    assert trace.reward == 0.0  # score 没跑，reward 不应有值
    # 关键：即便 harness 抛错，runtime 仍在 finally 中被 teardown。
    assert rollout.runtime is not None
    assert not rollout.runtime.workdir.exists()


# ---------------------------------------------------------------------------
# 断言 3：score 在 runtime 存活期执行
# ---------------------------------------------------------------------------


async def test_score_runs_inside_live_runtime():
    calls: list = []
    rollout, _ = _make_rollout(calls)
    trace = await rollout.run()

    score_calls = [c for c in calls if c[0] == "score"]
    assert len(score_calls) == 1
    # @reward 里 runtime.run(["/bin/echo", ...]) 成功执行、workdir 仍存在
    # —— 评分发生在 runtime teardown 之前。
    assert score_calls[0] == ("score", True, True)
    # reward 以函数名记入 trace.rewards 并计入总 reward。
    assert trace.rewards == {"runtime_alive_at_scoring": 1.0}
    assert trace.reward == 1.0
