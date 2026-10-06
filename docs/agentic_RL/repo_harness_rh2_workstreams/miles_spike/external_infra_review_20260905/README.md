# 独立 infra 审查的复现材料

这些材料属于 [2026-09-05 外部审查](../external_infra_review_20260905.md)，用于复现观察，不是新的 CI、训练授权门或阶段验收系统。未修改生产代码。探针使用仓库私有接口，适用版本以主报告基线为准。

## 运行

在仓库的 `rh2/` 目录执行，使用已经安装依赖的 `uv` 环境：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905/failure_probes.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905/r3_capture_cost_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905/semantics_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905/grpo_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_20260905/r3_origin_probe.py
```

- `failure_probes.py`：真实 formal 编排与 capture，HTTP/tree/Docker 使用既有测试夹具。四项断言证明**当前问题行为**；退出 0 不表示问题已修复。
- `r3_capture_cost_probe.py`：真实同步 capture commit，48 层 × 8 路由项，8K/16K/32K 行。记录同一事件循环的等待与 routing 容器大小；不测 GPU 或整进程 RSS。两次输出用于显示本机波动，不设性能通过线。
- `semantics_probe.py`：独立 logits/梯度 oracle，96 例，真实 custom loss/归约器。`probe_bootstrap.py` 替换 Ray、并行 state 与 CP 计数 collective；不证明真实分布式训练。
- `grpo_probe.py`：真实 conversion/schedule，16 个 execution、30 个 leaf；独立计算 reward 和 execution 分母。
- `r3_origin_probe.py`：真实 `TrajectoryManager` 与回填，人工不同路由值验证最终取哪一轮；不把人工差异当真机路由差异。

已有测试与 pin 检查命令：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run pytest tests/adapters_miles tests/governance tests/adapters/test_w5a_shutdown_chain.py -q -m 'not docker' --durations=12
bash scripts/miles_integration_lanes.sh --checks-only
```

`focused-tests.log` 为 801 passed、0 skipped、0 xfailed、17 warnings；`base-checks.log` 明确只有前置检查，未运行正式双 lane。日志中的本机根路径已换成 `<repo>`；数值和错误内容未改写。`*-initial.*` 为主审第一次成功运行，`*-repeat.*` 为复制到本目录后重跑。另一个运行时审查者独立运行的 151 项相关测试有重叠，不能加成 952 项。
