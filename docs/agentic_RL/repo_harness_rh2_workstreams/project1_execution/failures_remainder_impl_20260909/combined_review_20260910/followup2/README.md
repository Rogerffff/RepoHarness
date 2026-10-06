# R2 / R6 余项最终窄复核

日期：2026-09-10。审查者：Codex。基线 `0313991c` → `f7521d94`；代码修复 `01b7f351`，manifest 计数 `6d8f7f69`；miles 集成树仍为 `4c04f997b`。

**结论：R2 原 P1 余项关闭，R6 原 P2 余项关闭；没有发现此次修复的直接回归。结合上一轮已通过的 R1/R3/R4/R5/R7，N1–N4 本批实施审查可以收口，进入下一切片。没有新增 T0。**

本轮严格沿[上轮停止条件](../followup1/README.md)：只核对两处 prelaunch 清理及直接回归，顺带核对已修的离线成本汇总。未重开必要记录改判、旧取消 backlog、其它组决策或 GPU 资格范围。主审检查实际 diff，并按既有协议让 Production Tracer / Falsifier 交叉复跑 R2；R6 为纯函数，由主审直接核对。

## 1. R2：两处分支由外层统一清理，原反例已消除

`rh2/src/repoharness2/grading/manager.py:1667` 与 `1682` 删除了内部 `_remove_container()` 等待，直接抛原 `SandboxProfileViolation`。唯一生产调用方 `_start_container()` 在 `1632–1634` 持有 record、捕获异常并调用现有 `_close_container_scope()`。没有新计时器、owner 或状态机。

因此两种结果符合既定合同：

| prelaunch 失败后的清理 | 应得到的事实 | 本次复跑 |
|---|---|---|
| `rm` 及时返回 | 容器已删除，原 profile 违规到达提交者，不追加评分 | 初始化失败与检查不合格两案均成立 |
| `rm` 卡满独立清理预算，提交者仍等待 | 停止状态无法确认，`GradingScopeTerminationError` 到达提交者；槽位释放，记录保留 | 两案均成立；清理约 1.001 秒被取消，评分在约 1.001–1.002 秒收口 |
| 同上，但提交者已取消 | 致命错误仍须通过独立通知通道送出，不能随 future 一起丢失 | 两案均恰好通知一次，槽位释放，记录保留 |

工作预算为 0.1 秒，清理预算为 1 秒。阻塞 `rm` 没有由探针主动释放，也没有先强制关闭队列帮助它退出；它由生产清理期限取消。随后 `manager.close()` 的第二次删除才清净模拟对象，最终 `containers_open=[]`。所有失败例都没有追加评分。

**通知口径澄清：** `queue.py:267–272` 分工明确：等待中的提交者从 future 收到异常；future 已取消/结束才由队列调用 out-of-band fatal sink。不能要求前一种情况下队列也直接通知一次。探针分别验证两条通道；这沿用现行传播方式，没有改异常语义。

**清理错误覆盖 profile 违规不是新决策。** 第一次 `rm` 用完总清理预算后，没有证据确认容器已停，按原 D-2 合同报告 `GradingScopeTerminationError`；原 profile 违规仍保留在异常上下文。及时清理的对照仍保留原码。这里关闭的是无期限等待，不将未知状态伪报为清理成功。

主审独立重跑 [R2 九案探针](r2_probe.py)，[结果](r2_probe_result.json)包含上述六案及三个对照：正常评分仍 `resolved`；创建期到期仍归 `grading_deadline_exhausted:container_start` 并回收；连续两次回包丢失仍处理两个名字、仅追加一次。Production Tracer 与 Falsifier 独立复跑并交叉检查一致。两个分支的失败来源均通过正式 profile 的外部 I/O 替身触发，测试没有直接给内部 helper 强塞最终异常。

## 2. R6：整组成本能按原因归属，消费/丢弃成本分开

`drop_events.py` 的新增逻辑只作用于离线汇总，未进入训练准入或执行控制流。`by_root_cause` 保留失败成员自身成本；`by_root_cause_set` 将整组成本归到排序后的原因集合，多原因只进入组合键一次。`by_task` 则分别输出 `consumed_member_fields` 与 `dropped_member_fields`，原 `member_fields` 保留合计。

[主审成本探针](cost_closure_probe.py)复用上轮原始输入，动态检查的[结果](cost_closure_result.json)如下：

| 条件 | 结果 |
|---|---|
| harness 失败组 4205 秒、拉镜像失败组 75 秒；交换正常成员成本 | 两个原因集合桶随之交换，完整汇总不再相同 |
| 同组两种原因 | 只出现一个组合键，成本 4205 秒只累计一次；调换原因顺序不改变结果 |
| 八成员只有七份快照 | 原因集合的完整成本为空，已知下界为 3605 秒 |
| 所有 elapsed 均未知 | 成本为 null、unknown=1，不填零 |
| 失败成员快照缺失，七个正常成员快照存在 | 归 `<no_snapshot>` 集合，成本仅为已知下界 4200 秒 |
| 同 task 有消费组与丢弃组 | 消费成本 70 秒、丢弃成本 4205 秒、合计 4275 秒，分别可读 |

这满足原 R6 余项的诊断目标。没有将快照当成权威终态，也没有把不完整成本算作完整成本。本轮一处既有测试由整个 task 字典相等改为核对原四项字段，原因是新增输出键；原成本数值断言仍在，新增终态分布也有独立断言，不构成放松旧数值 oracle。

## 3. 验证、改动范围与停止条件

- 主审相关测试：**204 passed / 0 failed / 0 skipped，26.52 秒**。范围为非 Docker grading、formal 冻结、预算与成本汇总；显式忽略两个原本不执行的 Docker 文件，避开上轮已知的混合收集问题。
- `ruff check src tests` 通过；`miles_integration_lanes.sh --checks-only` 通过。后者只验证集成树、pin 与补丁等前置事实，不等于完整双 lane。
- R2 九案和 R6 原反例及对照均由主审执行，命令与版本见 [verification.json](verification.json)。未把作者的全量 2252 项或完整双 lane 结果记成主审实跑结果。
- 没有真实 Docker daemon、SWE 镜像、Claude Code、模型 API 或 GPU。因此仅确认 Python 生产控制流与离线汇总，不据此推断真实故障频率、Docker 清理耗时或训练吞吐。
- 未修改生产源码、维护测试、配置、依赖或 Git 提交。新增复核工件，追加 `infra.md`，同步 Brief 和交接的审查状态；现有共享改动保留。

复跑 R2 时在 `rh2/` 下执行 `uv run --no-sync python` 并传本目录 `r2_probe.py` 的相对路径；它将结果写到同目录 `r2_probe_result.json`，保留本次证据时请另存输出。成本探针仅打印 JSON，复用上轮脚本构造输入，不覆盖上轮结果。

**停止条件已经满足：原 R1–R7 全部关闭，本批无剩余阻塞。** 不再为本次两行删除安排新的广泛审查或补审批。其它切片的既有未决事项、已登记残余和真实环境/GPU 验证保持各自范围；本结论不代表整个训练项目验收完成。
