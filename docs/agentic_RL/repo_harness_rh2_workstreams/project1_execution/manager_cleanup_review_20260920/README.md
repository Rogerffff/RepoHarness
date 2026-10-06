# 跨 manager 清扫与中断日志运输：聚焦复核

日期：2026-09-20。审查方：Codex A。对象：Claude A 的未提交改动；基线提交 `e3d120b55a62cca5985f688de8cdd481b12ea6be`，受审文件和摘要见 [snapshot_before.json](snapshot_before.json)，差异见 [implementation.diff](implementation.diff)。

## 1. 结论与分期

**删除跨 manager 年龄清扫的修复接受；本轮未发现新的阻塞问题。** 中断 exec 的正常返回及容器已死两条路径已改善，正常评分、模型失败和自身清理的对照通过。不能将它扩大成“所有取消窗口都能保留已交付证据”：还剩一项既有 P2 诊断问题，见 §3。

- **本轮接受**：`startup()` 无副作用、删除年龄配置、保留本实例清理及原有标签；未收尾且 exec 以信号退出的日志按 partial/infra 记录，已死容器的已交付输出可传到 sidecar。
- **可后补**：§3 / CR1，owner 建议为 A，放入评分诊断后续维护；验收以两处取消窗口及短 tee 反例为准，不阻塞本轮清扫修复或下一组决策。正式处置由作者回填，本报告不冒充其已承诺修复。
- **文案应修正**：收口行来自候选 stdout，不能声称“伪造换不到 reward”；`candidate_exec_exit_code=None` 只能说明“未记录到退出码”，不能保证“exec 没有返回”。无新增 T0 或安全机制设计。
- **B 的启动兼容项仍待处理**：使用 `--grading-label-prefix` 的实验脚本还读取已删除配置，必须在再次运行该命令前同步；CLI 最终退出码亦仍由 B 负责。本审查不宣称整个 B 重放链已通过。

按审查标准 §10.4 仅安排一对限定角色，分别追踪生命周期和推翻严重度；主审重放关键反例后合并结论。没有改生产源码、维护测试、配置、fork，未提交、push 或发送跨任务消息。

## 2. 已核销的行为

### 2.1 容器所有权

`grading/manager.py:1552` 的 `startup()` 直接返回 `[]`，不枚举或删除外来容器。`orphan_min_age_seconds` 已从配置删除；评分 `finally`、`close()/gc()` 仍沿本实例 `_records` 回收。`shutdown/run_residue.py` 的按 run 标签清理未改，空 run_id 的保护仍在。

单测覆盖旧时间戳、非法时间戳的外来容器不被清扫，以及本实例容器回收；真实 Docker 用例确认同一命名空间的外来活跃旧容器在另一个 manager startup/close 后仍存活。其它真实评分对照覆盖自身容器的成功、失败、超时收口。

代价保持已知：进程崩溃遗留不再由新 manager 自动捡走。确认**整个所属 run 已结束**后，才按准确 run 标签或容器名清理；单个 manager 结束不能代表同 run 其它 worker 结束。

### 2.2 MONAI 日志运输与正常评分对照

[probe.py](probe.py) 使用原始 MONAI-763 日志，核对其账本 SHA256 为 `25407384b0ff0f20e05ff5baab592e81034230bf3b2fadc92f2a16bfaf72abc7`。受控注入 exec=137 与容器状态，调用真实 `grade()`：

| 场景 | 修复后的结果 |
| --- | --- |
| exec=137，inspect 仍为 running，日志未收尾 | `infra_failure`、reward=None、phase=test、partial=true、exec=137，保留候选输出 |
| exec=137，inspect 已为 stopped，tee 读不到 | 同样保留输出/退出码，原因是 `grading_container_killed_during_test` |
| 正常成功 / 普通测试失败 | 分别 reward=1 / reward=0，partial=false |
| 测试子命令返回 137，但外围脚本正常收尾 | 继续按既有测试结果解析，不因子命令的 137 自动判 infra |

旧 `_run_eval` 方法差分在同一 MONAI 日志下复现 `official_bad_codes_after_successful_replay` 和 partial=false；新代码修正该运输。注意这是**既有日志 + 显式 rc/state 注入**，不是再次运行 MONAI，也不是原事故全部时序的录制证明。

真实 Docker 的外部 `rm -f` 用例另证实：候选执行中容器被删除，输出与退出码保留、评分是 infra/None、自身资源最终回收。新增 sidecar 与内存事实在主探针逐案一致，未触发追加评分。

## 3. CR1 / P2：取消或短 tee 仍可能丢掉已交付的 exec 输出

**分期：既有诊断残余，非本轮阻塞。标签：production_reachable。**

- **当前行为 / 位置**：exec 已返回 stdout 与 137，`manager.py:2394` 先 await 容器 inspect，尚未保存结果；另一窗口在 `manager.py:2980`，先 await tee 读取，再读取异常携带的 `exec_result`。取消命中任一窗口且 tee 无法读回时，已交付输出会丢失，退出码记录为 None 或整份候选事实缺失。
- **生产链**：Bringup 关停排空评分超时，`bringup.py:2086 → grading_queue.close(drain=False) → queue.py:170–172 worker.cancel()` 可取消正在执行的 `grade()`。无需新配置或新功能。实际命中频率未测。
- **违反的诊断要求**：已收到的候选输出/退出码不应被后续异步诊断步骤丢弃；否则无法从 sidecar 判断已知的终止原因。
- **证据**：[interruption_probe.py](interruption_probe.py) 对完整旧 manager 模块与当前模块分别注入两个取消窗口，[结果](interruption_results.json) 中四案均丢尾部，容器均正常删除、CancelledError 均向外传播。无取消的当前正控保留尾部和 137。它是既有遗漏，不是本轮引入。
- **同根相邻例**：inspect=unknown，tee 非空但仅有安装开头，exec stdout 已有测试段。当前只在 tee 为空时用 stdout，因而丢掉 stdout 尾部并记成 phase=install；探针有独立复现。仍是 infra/None。
- **影响**：丢失诊断证据或阶段误归因；上述反例没有制造错误 reward、吞掉取消或留下未清容器。因此不扩大为清理/训练正确性阻塞。
- **最小方向**：在下一次可取消 await 前同步保留已交付结果；随后读取 tee 只作补充，不让更短日志覆盖已经收到的输出。不要新增 owner、重试、恢复状态机或兜底评分。
- **修复验收**：两个取消窗口均保留 137 与唯一输出尾标记，CancelledError 和自身清理行为不变；短 tee 不使已知 test 阶段退回 install；正常评分及超时读取继续通过。现探针断言的是审查时的残余行为，修复时应翻转这些断言。

## 4. 两个需要澄清的说明

1. `manager.py:973` 及 Claude 账本中的“伪造收口行换不到 reward”过强。仅补收口行而没有可解析测试结果并不能给分，但同时提供可被 parser 接受的官方 End/PASSED 内容时，旧 `_run_eval` 和新实现都可得到 reward=1（[probe_results.json](probe_results.json) 的最后两案）。收口标记只是诊断线索，未建立新的可信结果通道。已知 stdout 信任边界继续由 B 原任务处理，本轮不重开完整防 hacking 设计。
2. `candidate_exec_exit_code=None` 的注释应表述为“未记录到 exec 退出码”。CR1 已证明取消可能发生在 exec 返回之后。None 的语义纠正无需新代码闸门。

## 5. B 线交接核对

未修改以下 B 所有路径，也未向身份不明的会话发消息：

| 项目 | 核对与建议 |
| --- | --- |
| `rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py:129` | `--grading-label-prefix` 分支仍访问 `after.orphan_min_age_seconds`，当前会 AttributeError；同时移除过时的“production orphan detection remains unfixed”说明 |
| 同目录 `probe_grading_namespace.py:39–42` | 旧 oracle 断言活跃旧容器被删，并读已删除字段。作为事故历史证据保留并标明旧源码版本；维护中的正确性用例使用新的 foreign-live-container 测试 |
| 重放 CLI 退出码 | 应按 `close()["containers_open"]` 等最终收口结果处理；`cleanup_failures` 是历史累计，后续清理成功不应因历史报错一概返回失败。仍由 B 实施和验收 |
| sidecar 消费者 | 新增 `candidate_exec_exit_code`、`candidate_segment_completed`，`log_partial` 覆盖未收尾及中断。None/unknown 不填成 0 或“完整” |

## 6. 独立验证、范围与停止条件

本审查亲自执行，未将作者的大套件数字算作独立验证：

| 验证 | 结果 / 工件 |
| --- | --- |
| manager unit、profile unit、replay adapter（非 Docker） | **152 passed**，[focused_tests.log](focused_tests.log) |
| 5 个真实 Docker 对照 | **5 passed**，[docker_tests.log](docker_tests.log)：外来活跃容器、执行中被外部删除、正常成功、测试失败 reward=0、超时 tee 输出 |
| 主探针 | 8 案断言通过，[probe.py](probe.py)、[probe_results.json](probe_results.json) |
| 取消旧新差分 / 短 tee / 正控 | 6 案断言通过，[interruption_probe.py](interruption_probe.py)、[interruption_results.json](interruption_results.json) |
| 真实 Bash + 生产测试段渲染器 | 子命令退出 0 / 1 / 137 / 255 四案；外层脚本均 rc=0，收口=true，子命令退出码正确保留（同上工件） |
| 相关 ruff | 通过，[ruff.log](ruff.log) |
| 审查对象一致性 | 8 个受审文件至验证结束摘要未变，HEAD 未变，[snapshot_after.json](snapshot_after.json)；所检 Docker 标签容器前后均为空 |

在 `rh2/` 运行维护测试；探针从仓库根用 `rh2/.venv/bin/python <本目录>/probe.py` 和 `.../interruption_probe.py`。主探针依赖本地已有 MONAI 证据；第二个探针不依赖远端事故文件。

A–N 覆盖：A/G 检查真实 grade、异常、取消和真实容器；B 验证正常正负 reward 及被中断的 infra/None，不改变 P-A；C 无新增临时挡板；D 核对 manager 与 run 的清理所有权；E 翻转年龄清扫旧 oracle 并有对照；F 沿既定分工与清理决定；H exec 与日志事实分开，未知不作已知；I CR1 非阻塞、B 脚本另属；J 已指出不实注释；K 删除年龄配置、保留兼容入口；L 未加常驻清扫或额外正常路径 Docker 调用，未做吞吐基准；M 核对 sidecar 与诊断余项；N 核对配置删除的脚本消费者，未改外部 pin/fork/GradingReport 契约。

**停止条件已满足**：核心缺陷及两条相邻运输路径均有反例和正控，残余问题已限定影响和 owner 建议。无需重跑 216 题、完整大套件或 GPU 来批准本轮窄修。未跑远端/GPU；本次接受不代表 B 的驱动修复或完整流水线已验收。
