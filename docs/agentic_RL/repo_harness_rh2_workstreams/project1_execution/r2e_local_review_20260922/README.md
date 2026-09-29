# R2E 本机接线完整复核与 R-f 交接

> **后续状态（2026-09-23）：** 旧 CR2、R-e 组级维护测试与资格缺席口径已收口；三题六次真实本机运行独立逐键核对通过。新的对账工具及 runbook 窄收尾、x86 R-f / 正式 actor 剩余边界见 [本机收尾复核](closeout_20260923.md)。以下保留当时完整审查，不把旧未完成项当作当前状态。

审查始于 2026-09-22，2026-09-23 收口。审查者：Codex A；对象为 [R2E 实施计划 §11.3](../r2e_grading_wiring_20260920.md) 的 R-a…R-e 与 R-0 余项。R2E 改动仍未提交；审查期间其它 A 线提交了 E3 / E3b，收口 HEAD 为 `d4a11940`。本轮没有审查 E3 的实现，也没有把它混入 R2E 的通过结论。受审文件摘要见 [review_snapshot.json](review_snapshot.json)。

## 1. 结论与工作边界

**本机 R2E 评分主链通过本轮限定验收，可以进入既定 R-f 代表题真机对账。未发现需要阻止该步骤的新 P0/P1。** 材料、parser、来源语义、真实容器往返以及 miles 组级运输均有独立证据；不再仅凭 Claude 的测试数量或 grep 作判断。

收口前还需处理三件事，均不需要新的用户语义决策：

1. **旧 CR2 仍有一个 P2 遗漏**：正常评分报告被 scope 清理异常替换时，停批账本仍丢日志 / sidecar 引用。补这个窄修与真实 producer 回归，见 §2。它不改判分，不阻塞派生镜像准备；建议在 R-f 整批异常对账前补齐。
2. **R-e 组级行为本轮已用独立探针验证，但尚未成为维护测试。** Claude 将 §4 中两个组级关键案移植到既有 miles 测试面，与 A 文件 owner 串行更新 lane manifest 即可。此前 manifest 未提交的阻碍已随 A 的提交消失；不必把“谁加这一个测试”再升级成项目决策。
3. **改正 §11.3 的资格缺席表述**：参考键全部缺席、但测试正常结束的样本仍可按来源规则得 0；不是一律 infra / None。见 §3。

**这不是 48 题真实环境验收，也不是正式 actor 接入完成。** 本机 Docker 用形状夹具；真实派生镜像、真实 pytest / xvfb / 自定义入口、两侧初始化成本、48 题逐键对账仍由 R-f 完成。正式 actor 目前尚不消费本地派生镜像覆盖表；该段入口及 harness 求解另行按 D4=B 接好，不能从本轮报告运输成功外推。

## 2. 唯一代码 finding：CR2 正常报告分支仍丢失停批诊断引用

**P2；已独立复现；原问题的部分遗漏，不是新的 reward 污染。**

| 项 | 证据与结论 |
| --- | --- |
| 真实路径 | `scripts/replay_grade._run → ReplayGrader.replay_one → SWEGradingManager.grade → finally _close_container_scope → GradingScopeTerminationError → driver 停批账本`。探针只替换 Docker I/O，manager 和 driver 控制流保持真实 |
| 具体反例 | 测试已正常完成、manager 已形成 resolved 报告并将日志和 sidecar 写盘；随后无法确认评分容器停止。driver 正确停批，返回 2，但账本 `log` 与 `diagnostics_ref` 都为 None。最终 close 又清理成功时仍有相同遗漏 |
| 根因 | [manager.py](../../../../../rh2/src/repoharness2/grading/manager.py) 的正常报告分支（本轮 L1957–1966，落盘点 L1961）直接调用 `_persist_eval_log`；只有 infra 分支（L1997）调用 `_remember_infra_log`。而 [replay_grade.py](../../../../../rh2/src/repoharness2/adapters/slime/replay_grade.py) 的 `_fill_halted_grading_refs`（L683–702）仅查 `infra_eval_log_ref / cancelled_eval_log_ref` |
| 已修好的部分 | `install/test/resource_facts` 的运输已补；取消后的 `test` 也在。CR1 未捕获异常 / 取消不再生成成功摘要。正常、晚清成功、最终残留、停批的 0/0/3/2 主分支均正确 |
| 测试为何没抓到 | `test_r2e_replay_overlay.py:253` 用假 manager 直接填好 `infra_eval_log_ref` 再抛异常；`:289` 只覆盖真实 manager 的 infra 分支。两例不能覆盖正常报告落盘后被 finally 异常替换 |
| 最小修法 | 让正常、infra、取消三种落盘结果都能由 container record 找到；无需新的恢复流程或扫描目录。停批分支继续不构造报告 / reward，退出码仍为 2 |
| 回归要求 | 真实 manager 正常产报告并落盘，然后注入 scope 停止确认失败。断言账本有两个引用、引用文件存在、候选段事实在、没有 report/reward、没有继续下一次尝试。保留一个晚清成功对照即可 |

直接证据：[R-0 探针](probes/probe_r0_current.py)、[八案与 CLI 结果](probe_r0_results.json)。`halt_running`、`halt_late_removed` 两案均 `run_return=2`、两种引用为 false；正常与取消对照有引用。主审独立复跑了 09-20 原反例，未改原探针来迎合新实现。

定位影响：这是失败现场的**可追溯性缺口**。已有停批动作有效，没有继续评分或生成错误奖励的证据，不上调成 P1。owner 为本次 driver / manager 实现者；R-f 异常对账是收口时点，不新增一轮架构审批。

## 3. R-a / R-b：来源、解析和评分语义

### 3.1 已核实

- 四份封板输入（raw、revision、M3 镜像事实、固定规则源）与既有归档逐字节相同；重新 ingest 的四面文件与 manifest 均相同。48 题 gold 与固定上游 `extract_gold_patch` 字节相同；维护测试另验证 48/48 应用后的内容与来源新文件一致。
- 固定 `prime-envs@c4d04dfe` 的实际函数由 AST 直接取出，对拍 336 份真实日志：原始解析映射、去色后映射、缺失 / 多出 / 状态失配集合及 reward 均无差异，164 个 1、172 个 0。读取时直接 decode 字节，避免文本读取自动转换 CR 掩盖差异。
- 48 题未命中新增输入拒绝：重复键、空键、归一化碰撞、非法状态、CR、多参数 SGR 均为 0；331 个带 ANSI 的期望键正常进入匹配。这里不将只能改可信输入及其 pin 后才能注入的异常描述成当前生产阻塞。
- R2E 的 `grading_semantics` 在 spec 中先确定；早期 infra、P-A 候选归因和正常结果都保留 `r2e_expected_map`，四个 SWE F2P/P2P 计数为 None。
- `expected_present_count` 按期望键是否出现在观测中判断。状态全错、部分缺键、额外键不会再因为 R2E 的空 F2P/P2P 桶被误送“参考全部缺席”通道。
- SWE 旧 `trusted_prep` 命令在 `cee933b4` 导出源码和当前源码中都生成 216 题，三个 prepared 文件摘要全同；manifest 仅生成时间不同。默认来源没有混入 R2E；显式来源的 48 / 264 题由维护测试覆盖。

证据：[来源 / 336 日志独立结果](materials_results.json)、[旧新 SWE CLI 对拍](swe_cli_invariance_results.json)、[离线探针](probes/falsifier_materials.py)。

### 3.2 必须纠正的文档表述

Claude §11.3 未决项 4 写“零解析 / 参考全缺席在资格缺席时一律走未确定”。**这把两个边界混在一起了。**

本轮真实 manager → 正式编排 → miles 的反例是：期望键有 3 个，实际正常完成的测试只有另一键，`RH2_TEST_RC=0`，没有资格记录。结果为 `tests_failed / 0`、match/total=`0/4`，`execution_failure_decision.kind=source_rule`，不会发起编译复证，而且可与同题成功成员组成有效训练组。

这是已批准的行为，代码不应为了迎合错误文案改成 None。应写成：**零解析，或参考全缺席且有全局执行失败形状时，才进入 P-A 归因；资格 / 资源 / 语法位置证据不充分就无 reward。参考全缺席但测试正常完成，沿来源匹配规则得 0。** 详细边界以已有 manager 判定为准，不另造 R2E 特例。

还需保留两个已有语义边界：

- R2E 匹配的是期望状态映射。若来源期望本来带 FAILED / ERROR，测试退出非零仍可能得 1。本轮包含此正例；不能改成“有 error 就 infra”或“rc 非零就 0”。
- RH2 并集计数与固定上游函数不是所有畸形输入上的形式等价。空观测键有已登记反例，但当前 336 份语料未命中；不为了追求形式等价撤销已批并集口径，也不把 336/336 夸成全输入证明。

## 4. R-e：组级运输已经独立核验

本轮补的 [CPU 探针](probes/training_transport_probe.py) 从真实多来源 prepared 输入开始，经 miles Dataset / 派发、`Rh2MilesGenerateFn`、prepared registry、正式编排、真实 `manager.grade()`、投影 / RewardFacts / gate / Outcome、真实 `DefaultDataBuffer`，最后进入真实训练数据转换。模型响应、harness 和 Docker I/O 使用维护测试的接口替身；未调用 GPU loss，也未声称验证 MoE 路由或异步数值正确性。

| 情形 | 观测结果 |
| --- | --- |
| 同批一个 SWE 组、一个 R2E 组，各两成员 | 两组都进 buffer；原始 reward `[1,0,1,0]`，按组中心化后 `[0.5,-0.5,0.5,-0.5]`；四条 sample index / rollout id 为 0–3；loss mask 和 execution 分母均为 18，无跨题合并 |
| R2E 全错 / 部分缺键 / 多出键 / 正常完成但全部参考缺席 | 都是可信 reward 0；与成功成员共同训练，不因 None 的 SWE 计数被丢弃 |
| 资格齐备且位置与行号相符的语法失败 | collection 与 startup 两条路径均 `candidate_execution_failed / 0`；各复证一次，正常进入组 |
| 零解析缺资格、资源事实未知、可信 setup 失败、缺 marker | infra / None；整个 R2E 组不进 buffer，SWE 组仍在，`drop_admission_reward_scope_none=1`，没有用 0 替代 None |
| 将一个 SWE 成员与一个 R2E 成员硬塞到同组 | 真实 buffer 在动态 filter 处抛 `mixed_group_members`；buffer 为 0，无训练转换 |

共 11 案通过，结果在 [training_transport_results.json](probes/training_transport_results.json)。正式 metadata 不承诺单独的 `source` 键；探针的来源展示由可信 `task_id` 命名空间导出，未为测试新增生产字段。

**维护建议**：无需把本探针全部复制成一套新测试。补“两个来源分组后同批转换”与“不同题混组拒绝”两个关键案；其余 P-A / infra 已有维护测试，按确实缺的接缝增补。按当前真实 lane 跑出的数量更新 manifest，不能照抄 Claude 09-22 的旧计数：审查期间 E3 已使 lane 基线发生变化。

## 5. R-c / R-d：实际容器和环境覆盖表

已逐段追踪：来源评分面分派 → overlay 核对 → 两类容器按确认后的 image ID 启动 → rollout 初始化与首次 census → uid 54321 三条预检 → 严格应用候选 → 冻结 / 投影 → 清理候选容器 → fresh grader → root 恢复测试与入口并核摘要 → uid 54322 测试 → 解析、报告、收口。

三条 R2E 预检确在首次 census 之后，解释器使用 `-B -I -S`。这保留了旧 B1 的修正：不能在首次 census 前用 Python 预热排除区，再让 fresh grader 从冷初态重建。`.venv` 排除政策独立于 SWE v1/v2。

使用已有本机 R2E 形状夹具镜像，**直接运行完整 `ReplayGrader.replay_one` 与正式 rollout/grader profile**，不只拼接 shell 或手工建 report：

| 案例 | 实际结果 |
| --- | --- |
| noop | `tests_failed / 0`，match/total=`1/2`，入口 rc=1 |
| 修复补丁 | `resolved / 1`，match/total=`2/2`，入口 rc=1（来源期望含一个 FAILED） |
| 隐藏测试摘要不符 | `infra / None`，测试段未启动，日志保留实际 setup 失败 |
| 8 秒评分期限，人为 sleep | `infra / None`，部分日志保留，`segment_completed=false`，没有报告成普通负样本 |

四案的两类容器 image ID 相同，预检实际使用 agent 身份，收尾无未清理容器。证据：[完整结果](production_driver_results.json)、[可复跑探针](probes/production_driver.py)。原始调用记录、工件与日志保存在本地 `/tmp/r2e-production-review-20260922/`；复跑脚本使用新临时目录，不回写该次证据。

没有据此证明真实 48 张镜像上工具齐全、入口可运行、解释器搬迁无副作用或初始化预算足够。隐藏测试被恢复 / 保护也不代表已经解决候选 stdout 伪造；该族按既定分期保留，不能把有限夹具的通过写成通用反作弊完成。

## 6. 十项 T1 偏离的裁定

| Claude §11.3 项 | 本轮裁定 |
| --- | --- |
| 1. base_commit 用 M3 实测 HEAD、四项输入 | 合理；实际来源只有符号父提交，互检关系与当前 48 题重建通过 |
| 2. 期望原文与隐藏测试清单自证、拒重复 / 碰撞键 | 当前范围可接受；未误伤 48 题，不新增更多推测性拒绝 |
| 3. 数据身份与规则代码身份分开 | 合理；沿现有字段说明保留来源，不把数据 revision 当 parser pin |
| 4. 不额外预剥 ANSI / CR | 同意，以固定上游真实行为为准；336 份对拍成立 |
| 5. R2E 不扫描 SWE 四个坏码字符串 | 同意；没有来源依据，不新增把候选失败洗成 infra 的字面量通道。缺 marker 仍沿现有边界 |
| 6. 渲染器单独模块 | 同意，两个消费者仍从同一个 spec 分派入口进入 |
| 7. legacy hygiene 降级改 infra | 接受本片窄范围：当前 R2E 正式接 frozen delta，不把未支持的旧路径伪装成可用评分；不因此承诺维护另一套 R2E diff 链 |
| 8. trusted_prep stdout 键集合不变 | 同意，旧 CLI 输出 / 文件不变性已独立核实 |
| 9. JSONL 覆盖表与 root 私有路径约定 | 同意，实际 driver 消费已验证；真实 recipe 要按这份合同产出，不只是手填三个 true |
| 10. 保留来源缺陷与重复环境 | 同意，符合 DR4；对账不修题，不以 gold=0 强行改 expected |

## 7. 同步其它任务后，对本批有影响的事项

本轮同步的是**共享工作区当前文件与提交**，不是执行 git pull。没有覆盖其它任务未提交改动，也没有自动给另一任务发消息。

- **环境总入口已换为 [environment_pipeline.md](../environment_pipeline.md)**：SWE 214 题有不同版本的环境对照证据，两个 Modin 题隔离；不等于 214 题已冻结为正式训练池，或全部 actor 开发条件已过。原 09-19 实例已删除，真实派生镜像需要重建。
- **基座探针更新至 09-23**：[运行记录 §8.8](../base_model_probe_run_20260922.md)、[A 线交接包](../base_model_probe_20260922_aline_handoff.md)。解释器注入、同 UID 的轨迹读取、SSE 完结、工具参数 / thinking 回放、`count_tokens` 与窗口认知等均有新线索。探针预算为 60 回合 / 131K，而正式脚本默认是 25 次请求 / 32K；报告中的成功率不可直接外推。交接包的分行成本、压缩触发等部分仍是推断，不在本轮替其升级为正式链已复现事实。
- **这些 actor / 模型接口问题不阻塞固定补丁的 R2E grader 对账**。但在声称正式 R2E 求解或训练闭环可用前，必须回到正式 actor 入口核实；不能拿本轮 synthetic group 测试当替代。
- **A 线 E3 / E3b 已提交，但待其独立复核**。当前目录和 lane 基线与 Claude 最初报数时不同；本轮只核 R2E 与这些共同依赖能否完成限定运输，没有审核路由优化数值。
- **不要机械照抄 R2E 计划 §6 的 metacopy 操作建议。** [A 线最新方向记录](../batch6_efficiency_20260921/claude_a_direction_review_20260922.md)已承认本项目在 metacopy 与 `docker commit` 组合下出现过全 0 文件，并撤回通用开启建议。新机器应明确采用哪套已验证构建方式，留源文件 / 导层完整性证据；评分期是否开启按实际机器条件记录，不把旧机器参数写成通用前置，也不为此改 reward。
- 环境文档发布分支 `codex/environment-pipeline-20260922` 是资料快照，**不包含本地最新生产代码**。今晚不能只 clone 那个分支就当成已同步当前 R2E 实现。固定实际代码、fork、未跟踪 R2E 模块及四份输入后，再向机器分发并核文件摘要。

## 8. 给 Claude 的下一步实施顺序

1. **本机收尾**：修 §2 的正常报告日志引用；补真实 producer 的窄回归；将两条组级验收落成维护测试并同步 lane；更正资格说明及 metacopy 部署文案。无需再改算法、reward、parser 或拆分架构。图方便手工预填 `infra_eval_log_ref` 的测试不能替代真实 manager producer。
2. **固定可运行代码与输入**：当前 R2E 文件尚未提交，远端分支不足以复现。用明确快照 / 文件清单分发，原始 25 MB JSONL、revision、M3 facts、规则源及 prepared / pins 均需在场。沿既有校验和同步纪律，避免旧的 mtime/大小相同漏传。
3. **DR3 配方与少量构建**：以来源 digest 起步；搬迁解释器且保持 `/testbed/.venv/bin/python` 可用；保留初态工作树字节和 dirty 状态；隐藏测试放 `/rh2_private/r2e_tests`，root 私有且公共位置无副本；清理 refs、reflog 和不可达答案对象。生成真实 image ID / recipe 摘要 / 隐藏树摘要的逐题 overlay，不把源镜像 digest 伪装为派生镜像身份。保留来源 run_tests.sh，不顺便修题。
4. **先跑代表题**：覆盖纯 pytest、xvfb、自定义入口（pillow）、初态 dirty tree、期望 ERROR/FAILED 仍可 resolved、冷镜像首次 census。记录两侧初始化 / census / 测试 / 清理耗时和可写层增长，据此定整批资源与期限；不凭原 runner 的测试中位数推算 RH2 总耗时。
5. **用一题做既定错误对照**：同 image ID 与脚本摘要的成功行供临时资格，人为语法错误在有资格时给 `candidate_execution_failed / 0`、无资格时给 None；人为超时给 infra / None、保留部分日志并清理。临时资格仅用于本次机制验证，不冒充流水线已给 48 题授资格。
6. **代表题无未解释分歧后跑 48×noop/gold**：noop 48 个 0；gold 46 个 1，coveragepy `016af5f6` 与 datalad `58ba5165` 保持 0。逐题比较键集合 / 状态 / 缺失与多出键，不能只看 46/48 总数。已有多轮证据的稳定题无需机械重跑；仅对分歧 / 波动定点重复。
7. **交接**：实际代码身份、机器 / Docker / 存储条件、配方与 overlay、逐题账本及 sidecar / 日志引用、与旧 runner 的 reconciliation、成本与最终清理事实。区分“按来源一致”“环境资格”“题目质量”“actor 可用”，不要合并成一个通过标签。

25 MB 原始行是否进 git **不阻塞真机执行**。我倾向在这版固定 48 题里直接跟踪，避免为了一个文件引入 LFS 流程；提交时由用户决定。Claude 给的 B 不是唯一替代：独立分发归档仍可保留加载期校验，不必改成只信 pins。当前最省事的是继续携带原文件，不动可信加载逻辑。

## 9. 本轮验证记录与停止条件

| 检查 | 独立结果 / 边界 |
| --- | --- |
| R2E 相关 8 个维护测试文件，含 replay 与 registry | 142 passed |
| `tests/envpack tests/contracts tests/grading -m 'not docker'` | 798 passed / 1 skipped / 39 deselected；与上一行有重叠，不相加为独立测试数 |
| 来源与 parser | 48 题重建、336 份真实日志固定上游对拍通过；SWE 旧新 CLI 三个产物全等 |
| 完整本机 Docker driver 探针 | 4 案通过；形状夹具，不是 48 题真实镜像 |
| 训练运输 / 分组 CPU 探针 | 11 案通过；主审完成并执行，使用真实 manager、buffer、转换；模型与 Docker I/O 为替身 |
| R-0 | 8 案 + 真实 CLI 缺补丁子进程；CR1 已修，CR2 复现两条正常报告停批分支的引用遗漏 |
| ruff | R2E 实现 / 维护测试相关范围与本轮探针均通过 |

审查遵循限定分工：来源反证、实际生产路径分别独立核查，主审复核源码并复跑 R-0 反例、完成训练语义接缝。没有重跑全仓、两条完整 GPU/训练 lane、远端 48 题、真实 CC、模型 API 或 GPU；也没有改生产代码、维护测试、manifest、机器配置或提交推送。

停止条件已满足：本轮明确的 P2 窄修、维护测试与文档收尾由实现者处理；后续未知以 R-f 的真实环境证据消除，不继续把本机审查扩成新的全仓防御性审计。已批 DR1 / DR3 / DR4、撤回的 DR2、反作弊与资格分期均不重开。
