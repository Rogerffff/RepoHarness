# 批 A R1 修后针对性复核

日期：2026-09-09。基线：`297f1f59` 上当前未提交修复。范围仅为 R1：容器操作失败的 typed 来源、驱动转换范围、未知异常传播，以及当前 `test_batch_a_failure_routing.py` 的验证方式；不重审预算 B/C/D、六项保留现状分支或清理总链。

**结论：R1 已闭合，本次范围内未发现新增问题。** 驱动已不再捕获所有 RuntimeError；局部操作失败在真实源头产生 `SandboxExecError`，未知内部异常保持原异常并由 formal 编排转 FATAL。

## 来源与传播核对

- `rh2/src/repoharness2/adapters/slime/docker_sandbox.py:27–39` 新增 `SandboxExecError(RuntimeError)`，保留 `op`、`exit_code` 和诊断。它在 `exec(check=True)` 收到非零结果时抛出（`:86–88`），在 `write_file` 收到非零结果时抛出（`:102–106`），没有包住 `_run` 或本地内容转换的任意异常。
- `bringup.py:394–404` 只捕获该类型并转换为 `harness_bootstrap_failed`，保留 `__cause__`。其它 RuntimeError、已有 typed 配置错误不被改名。`exec(check=False)` 继续返回原三元组，没有借此改变轮询等调用语义。
- 未改旧 [error_routing_probe.py](error_routing_probe.py)。其中名为 `known_docker_failure` 的案子直接给 `DockerSandbox.exec` 注入裸 RuntimeError；它绕过了现在产生 typed 错误的真实源头，修后 FATAL 是新契约的正确结果，不能当作局部命令失败的回归。

## 独立 CPU 验证

新建 [error_routing_source_followup_probe.py](error_routing_source_followup_probe.py)，使用真实 `DockerSandbox.exec` / `write_file`、真实 `ClaudeCodeDriver.run` 和真实 formal 编排，只替换底层 `_run` 的结果或异常。既有容器/评分夹具仍是 CPU 替身，没有执行 Docker、CLI、GPU 或网络模型。

```bash
cd rh2
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/error_routing_source_followup_probe.py
```

命令实际退出 0，八案断言均满足：

| 案例 | 源头事实 | 最终结果 |
|---|---|---|
| `exec` 返回 17 / 124（两案） | `SandboxExecError(op="docker exec", exit_code=17/124)` | ABORTED，`harness_bootstrap_failed`，fatal 通知 0，cleanup 完成 |
| `write_file` 返回 17 / 124（两案） | `SandboxExecError(op="sandbox write_file", exit_code=17/124)` | ABORTED，`harness_bootstrap_failed`，fatal 通知 0，cleanup 完成 |
| `exec` / `write_file` 的 `_run` 内部 RuntimeError（两案） | 原始 RuntimeError，没有伪造 op/exit_code | `pre_finalize_failure_unclassified` FATAL，通知 1，无 Outcome，cleanup 完成 |
| 完成引导后的内部 RuntimeError | 原始 RuntimeError | 同上：FATAL、通知 1、无 Outcome、cleanup 完成 |
| `exec(check=False)` 返回非零 | `(17, "stdout", "stderr")` | 原样返回，无 typed 转换 |

124 案验证的是 `_run` 已报告超时结果之后的分类，不冒充真实进程超时或 Docker 回收验证；后者属于其它边界。

## 维护测试与范围界限

已回读当前 `rh2/tests/adapters_miles/test_batch_a_failure_routing.py`：驱动单元覆盖 typed 包装、未知 RuntimeError 透传、CLI 配置错误透传；formal 组合用例对已知失败使用真实 `DockerSandbox.exec` 加 `_run` 返回 124，符合新的来源契约，并覆盖安装/运行内部异常与 CLI 配置错误的 fatal 结果。上述维护测试的执行由主审负责，本报告不重复运行或冒称测试结果；独立探针补核了实际 `write_file` 抛出点及普通非零结果。

复核时所读的 `docker_sandbox.py` / `bringup.py` 与 `generate.py` 差异中未见新接入的 episode deadline 行。本结论只覆盖 R1 的当前错误来源与传播，不对 Claude 后续开始的批 B 做任何验收承诺。

本轮只新增本记录与新独立探针，未修改旧探针、业务源码、维护测试或主文档，未提交。R1 按上述证据可关闭，无须继续扩大审查。
