# N1–N4 修后针对性复核

日期：2026-09-10。审查者：Codex，含 Production Tracer / Falsifier 独立交叉复跑。

**结论：R1、R3、R4、R5、R7 通过；R2 仍有一项原 P1 余项；R6 部分完成，保留原 P2，不扩大阻塞范围。没有新增 T0。** Claude 的修复方向成立，但“七项全部修复”目前还不能确认。唯一阻塞应能通过删除两处重复清理调用解决，无需再设计清理层。

审查范围为根仓库 `06dd7c06` → `0313991c`：代码/测试修复 `dc7a613b`、manifest 计数 `647127c6`、文档 `0313991c`。miles 集成树仍为 `4c04f997b`，本轮未修改。沿用[上一轮审查](../README.md)的范围、A–N 适用性和分期，只核对原问题与修复的直接回归。本次没有修改生产源码、维护测试、配置或 Git 提交。

## 1. 七项处置状态

| 原编号 | 本次结论 | 核对依据 |
|---|---|---|
| R1 / P1 | 通过 | 创建请求发出前登记名字；连续两次回包丢失、首次/第二次创建到期、外层取消，均进入现有清理所有权。无法确认停止的反例仍走 fatal |
| R2 / P1 | **部分修复，保留一项阻塞** | init、prelaunch 检查、两次 digest inspect 已接共同期限；到期不再读可选内存。但 prelaunch 两个失败分支仍先等无超时的 `rm`，挡住新的有界收口 |
| R3 / P1 | 通过 | 真双 loop 的必要审计缺失反例不再成功退出；安全晚收口和正常完成仍成功，可选成本事件失败不被升级为必要证据 |
| R4 / P2 | 通过 | 实际 bringup 停止谓词接入 manager；真实 run-fatal 后、manager 尚未关闭时不再第二次 pull。普通暂态失败仍至多追加一次 |
| R5 / P2 | 通过 | 组与 attempt 连接键含 run 身份；同名组的两个 run 分别记 10 秒、100 秒，互不混合 |
| R6 / P2 | **部分完成，非阻塞** | 缺失/全未知口径已修，增加了失败成员自身的按原因成本；整组连带成本按原因的关联、同 task 内消费/丢弃成本对照仍未完成 |
| R7 / P2 | 通过 | 11 个指标数值不变，计数辅助函数的 `.item()` 调用由 11 次降到 0 次；CPU/CP 对拍通过，未测 GPU 性能收益 |

## 2. R2 余项：旧的无超时清理挡住新的有界清理

**位置：** `rh2/src/repoharness2/grading/manager.py:1663` 与 `1679`。无超时分支在 `1689–1690`；集中收口入口在 `1633–1634`，独立清理预算从 `_close_container_scope()` 的 `1752–1756` 起算。

**当前行为与原因：** `_start_container()` 已正确持有 record，并在异常时调用 `_close_container_scope()`。但 `_grader_prelaunch()` 在可信初始化失败或检查不合格时，先执行旧的 `await self._remove_container(record)`，之后才抛 `SandboxProfileViolation`。这两次调用没有传 timeout，实际直接等待 Docker。若这里卡住，异常就到不了外层，新的独立清理预算也尚未启动。

```text
可信初始化失败 / prelaunch 检查不合格
  → 内层 rm -f（无 timeout，可能卡住）
  → 抛 SandboxProfileViolation
  → 外层 _start_container 捕获
  → _close_container_scope（此时才开始有界清理）
```

**不变量与原验收：** 评分的完整工作路径要按共同期限停止，资源清理使用独立有界预算；不能在进入这个清理范围之前另有一段无期限清理等待。这属于原 R1/R2 聚合修复的未闭合验收，不另立新问题。

**反例与生产可达性：** [N2 探针](n2_followup_probe.py) 的 `prelaunch_violation_rm_hang` 使用真实 queue → manager、冻结 delta、正式 grader profile，只替换 Docker I/O。可信初始化失败后，第一次 `rm` 阻塞；工作预算为 0.1 秒，清理预算为 1 秒，从评分开始 **1.251 秒后 worker 仍活动、record 未移除、提交尚未返回**（已在该阻塞点等待约 1.25 秒）。显式强制关队列后，外层才接管第二次有界清理。主审和两个独立角色分别复跑一致，见 [N2 结果](n2_followup_result.json)。初始化失败分支有动态证据；检查不合格分支具有同样的直接调用，静态确认。判定 `production_reachable`，发生频率未知。

**准确影响与分期：** 延迟评分结束、故障通知和资源释放，违反本批共同期限与独立清理预算。容器现在已经登记，外层提交仍有“工作期限 + 清理预算 + 60 秒”的最终兜底，故不再描述为无人记账、永久无人监管或退出假绿。维持原 P1，不能用作者全量测试通过代替此反例。

**最小修法：** 删除 `1663`、`1679` 两处重复 `_remove_container()` 等待，直接抛原 `SandboxProfileViolation`；由已经持有 record 的 `_start_container()` 统一调用现成的 `_close_container_scope()`。同步说明清理所有权的注释即可，不必给内外两层分别加计时器或新状态。

**验收条件：** 两个失败分支分别覆盖：及时 `rm` 时清理完成、保留原 `SandboxProfileViolation` 且不追加评分；`rm` 阻塞且无法确认停止时，在现有独立清理预算后 worker 结束，并经 fatal sink 报告 `GradingScopeTerminationError`，资源记录仍可供后续清理。正常评分、创建到期及连续两次回包丢失对照继续成立。

## 3. R6 余项：失败成员成本不等于整组连带成本

`drop_events.py:414–424` 的 `by_root_cause` 只读取 `aborted_members` 对应快照；`391–392` 则把同 task 的消费与丢弃成员成本放进同一个 `member_fields`，虽然两种终态各有计数，却没有各自的成本分布。

一个具体反例：两个同 task 的八成员组分别因 harness 失败、拉镜像失败而丢弃。两个失败成员都用了 5 秒。第一组其余七人各用 600 秒，整组为 4205 秒；第二组其余七人各用 10 秒，整组为 75 秒。随后交换两组正常成员的成本，实际按故障原因分配的整组损失随之交换，但**当前完整汇总输出完全相同**，两个原因桶仍各只报告失败成员的 5 秒。见[诊断探针](cost_diagnostic_probe.py)和[结果](cost_diagnostic_result.json)。

这里的 5 秒作为“失败成员成本”并没有算错；问题是它不能回答原计划要求的“哪类故障主要连带丢掉长轨迹”。全局整组成本分布也无法恢复已经丢失的原因关联。因此 R6 可以记为部分完成，不能记为全部关闭。它只影响离线诊断，保持原 P2，不阻塞本批主线。

后续沿用当前离线汇总即可：将整组已知成本关联到原因或原因集合；同 task 内保留消费/丢弃成本对照；多原因组不能重复累加后称作无重叠总量。缺失快照与全未知值本轮已正确区分，不重做。

## 4. 通过项的关键证据

**R1/R2 已修部分及 R4：** N2 共执行 16 案，覆盖正常评分、连续创建失败、两次创建期限、init/prelaunch/digest 等待、工作到期后的可选内存、清理消耗剩余工作时间、取消和 unknown 清理、真实停止谓词。16 案中包含上文用于确认剩余 P1 的反例，不能写成“16 项修复全过”。`fatal_while_pull` 替身 manager 已补传 bringup 实际的停止谓词，否则会绕过本次生产接线。

**R3：** `generate.py:4526` 只在 receipt 持久化与必要 audit sink 成功后记录 `necessary_records_complete`；sink 返回至置位之间没有 `await`。正式 bringup 确实注入 sink/store；`bringup.py:2325–2328` 与 `2352` 在缺少完成事实时拒绝解消等待失败。[双 loop 探针](n3_followup_probe.py)的两个 resolver 都绑定真实 owner loop，主审重跑[七案](n3_followup_result.json)：

| 场景 | 必要记录完整 | 最终结果 |
|---|---|---|
| 宽限内完成清理 | 是 | 成功，解消旧等待失败 |
| 第二次取消打断必要 audit 之前的 await | 否 | 失败，不解消 |
| receipt 写失败 | 否 | 失败 |
| audit sink 写失败 | 否 | 失败 |
| 仅可选 N1 快照发射失败 | 是 | 成功 |
| 原 driver fatal 已存在 | 是 | 保留原失败 |
| 正常 formal 评分交付 | 是 | reward=1，正常关停 |

这关闭了原来的“没有写失败记录，所以误以为已写完”的成功改判问题；没有把已有二次取消 backlog 扩成全关停重构。

**R5/R6 已修部分及 R7：** 原[观测探针](../observation_probe.py)原样重跑，结果另存 [observation_result.json](observation_result.json)，未覆盖修前证据。跨 run 得到 10/100 秒；7/8 快照记缺失且只形成已知下界；全未知总成本为 null；DIS 十一项值不变，标量 `.item()` 调用为零。

## 5. 验证范围、产物与停止条件

本轮主审选择评分、预算、formal 冻结、shutdown、成本汇总与 DIS/CP 相关用例：**316 passed，0 failed，14 warnings，38.82 秒**。警告为 torch JIT 弃用提示。另运行 `ruff check src tests` 与 `miles_integration_lanes.sh --checks-only`，均通过；后者仅为 manifest/补丁/集成树前置校验，未重跑完整双 lane。命令与版本见 [verification.json](verification.json)，测试原始输出见 [targeted_tests.txt](targeted_tests.txt)。没有将作者的 2245 项全量结果记为本次主审结果。

第一次组合选择在收集期失败：两个 Docker 文件通过 `from conftest import requires_docker` 导入时解析到 adapters_miles 的同名模块，`-m 'not docker'` 尚未来得及筛选。随后显式忽略这两个原本不执行的 Docker 文件，得到上述 316 项结果；未修改测试源码。此项是本次命令的收集限制，不据此新增实现 finding。

复跑 N2/N3 时在 `rh2/` 下使用 `uv run --no-sync python`，传入本目录脚本的相对路径；N3 脚本定位本仓库集成树。N2 复用上一轮 `n2_production_probe.py` 的替身支持。N2/N3 脚本会写本目录对应结果文件，若需保留本次证据，应先复制脚本/结果或改输出位置。R6 探针仅打印 JSON。

本轮均为真实 Python 控制流加外部 I/O 替身，没有真实 Docker daemon、SWE 镜像、Claude Code、模型 API 或 GPU，不能推断故障发生频率或性能收益。源码/维护测试/脚本的工作区 diff 为空，现有共享文档改动保留。

**停止条件：** Claude 完成两处重复清理的窄修与正反例后，只核对这一项原 P1 及直接回归。R6 保持非阻塞 P2；不重开已通过的 R1/R3，不新增审批或其它切片的验收要求。
