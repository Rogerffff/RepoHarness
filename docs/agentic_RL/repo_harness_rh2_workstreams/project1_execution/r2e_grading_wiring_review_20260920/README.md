# R2E 接线计划复核

日期：2026-09-20。审查者：Codex（A 线）。对象：[Claude 计划](../r2e_grading_wiring_20260920.md)，不是实施验收。

结论：**采用来源适配器、共用真实 grader、保留 R2E expected-map 语义的方向合理；计划修正后可以按切片推进，不建议把当前 DR1–DR4 原样全选 A。** 最重要的修正是撤回 DR2 的错误事实前提，其次把 manager 的语义迁移与真实产出测试补进清单。没有发现需要重开已经批准的 R2E 方案 A、第四组 reward/infra 规则或额外反作弊决策的理由。

本轮只新增审查文档与 CPU 探针、追加导航；没有修改生产代码、维护测试、数据、配置或 fork，没有运行 Docker/GPU/远端任务，没有提交或向其它任务发送消息。工作区包含其它任务改动；尤其 manager 的启动清扫修复归 A 分叉任务，本报告不替它验收。

## 1. 发现与修正要求

### R1 · P1：DR2 基于已经撤回的上游去色误读，应撤销这个二选一

**计划位置**：§2.2 第四条、§3.2 归一化与 pillow 表格、§5.1 R-b、§8 DR2（原稿第 53、81、90、141、177–183 行）。

计划称 Prime 的 `_decolor` 只删 `[数字m`，留下 ESC，导致 pillow 六题 gold 恒为 0。实际固定源码的正则是 `\x1b\[\d+m`，**包含 ESC 字节**。它只是原文件里的不可见字符，不是缺失的字符。这在 [09-09 独立核查 §3.1](../env_probe_20260909/codex_remote_check_20260909.md) 已确认，Claude 也在 [当日记录 §8](../env_probe_20260909/README.md) 明确 accepted、撤回；L4 后来又引用了旧结论。

**本次独立验证**：从当时固定为 Prime `c4d04dfe…` 的原始源码归档，用 AST 提取三个实际纯函数，保留原始字符串字节；重放旧 24 题的 144 份日志和 M3 的 192 份日志，共 **336 份，来源函数与本地 runner 的 reward 全部相同**。其中带 ANSI 的 pillow 六题共 24 次 gold，固定来源函数全部给 1。最小例子也把带 ESC 的 `test_sanity` 正确规范化为不带颜色的键。源码归档摘要与逐项结果见 [probe_results.json](probe_results.json)。

**影响**：按原稿会新增一套实际并非上游原版的 `prime_v1`，再增加双实现、双结果记录与用户决策；验收还会错误要求它与正确版本在六题上分歧。

**修正 / 分期**：R-b 开工前改正。固定实际 parser/reward 的**代码仓库、commit 和文件**，数据 revision `e8b9fcbc…` 不能替代代码版本。首版用一条实际来源适配路径；不为这项已证伪差异维护第二套实现。计划与 L4 加勘误链接，历史原始日志不重写。

**验收**：真实固定函数与新 adapter 在现有语料上对拍；不能把手抄一个缺 ESC 的正则称作上游 oracle。保留已批准的 RH2 非空/键并集口径与 Prime 空键宽松行为之间的真实差别，不把本次语料一致外推为所有输入完全同义；更广 ANSI 文法如要扩展，按真实差异说明，不能再用“pillow 六题上游恒零”论证。

### R2 · P1：manager 的来源语义迁移不能只靠判分 helper

**计划位置**：§3.2（原稿第 82–83 行）、§3.3 P-A（第 100 行）、R-b/R-c/R-e 文件与验收清单。

计划写的“参考全缺席 = 期望键无一在观测里”是对的，但实施清单没有覆盖它在现有 manager 的真正判定点。当前 [execution_failure_trigger](../../../../../rh2/src/repoharness2/grading/manager.py) 用四个 F2P/P2P 桶的总长度减缺席数判断。按计划，R2E 的四个桶全部为空，因此**只要缺一个键，就被当成全缺席**。

**反例**：期望有 `test_a`、`test_b`，观测已包含 `test_a`，另有收集失败导致 `test_b` 缺失。按计划的精确映射规则，这是有部分参考结果的 `tests_failed / 0`；把当前空桶 verdict 送入实际 manager 判定函数，会触发 `reference_all_missing`。在无资格记录时，探针进一步得到 `unattributed`，后续将给 None、丢失整个训练组。这个误判不会由正常 noop/gold 对账自动覆盖。

还有一个同源接缝：`grading_semantics` 目前只由成功走到判分 helper 的字段字典提供。manager 的公共报告字段没有来源语义；P-A 候选归因会整体替换该字典，提前 infra / patch-apply 分支也绕过 helper，最后回落到 `GradingReport` 的默认 SWE 语义。本次真实 `grade()` 控制流探针得到：

| 路径 | reward | 当前报告语义 |
| --- | ---: | --- |
| 新 helper 返回 resolved / tests_failed | 1 / 0 | `r2e_expected_map` |
| P-A `candidate_execution_failed` | 0 | **`swe_f2p_p2p`** |
| parser 前发生 infra | None | **`swe_f2p_p2p`** |
| patch apply 失败 | 0 | **`swe_f2p_p2p`** |

**修正 / 分期**：R-b/R-c 必须显式包含 `grading/manager.py` 与 spec 的来源信息运输，和正在修改该文件的 A 任务串行合入。全缺席判据从 R2E expected/observed 的在场关系得出，不借用空 SWE 桶，也不能用“状态匹配数为 0”代替“参考键在场数为 0”。来源语义在 parser 运行前就应确定，所有报告分支保留，未知计数仍是 None。

**验收**：通过新材料/spec → 实际 `manager.grade()` 产出报告，再送运输链；覆盖全匹配（含 expected ERROR/FAILED）、状态全错但键全在、部分缺键、全部缺键、零解析、候选归因、提前 infra。不要只手工构造四种正确报告验证下游。上表探针为计划接缝模拟：仅替换尚未实现的 R2E 判分字段，候选案另注入归因结果；它不声称 R2E 实际 parser、正式 profile 或候选归因已实现。

**一处文字校正**：§3.3 的“自定义 unittest 无 pytest 收尾 → 退回未确定”也不准确。当前三路逻辑在“参考全缺席且无全局形状”时直接走来源规则；没有收尾行并不自动产生 None。应沿已批规则描述，并为真实自定义入口验证完整输出及启动失败，不顺带增加新的日志格式拒绝政策。

### R3 · P2：混合来源的运输验收必须是同批不同组

**计划位置**：§5.1 R-e（原稿第 144 行）“组内混有 SWE 与 R2E 成员不串语义”。

当前 [group_admission.py](../../../../../rh2/src/repoharness2/adapters/miles/group_admission.py) 第 457–466 行要求同组成员的 `task_id / environment_package_digest / public_bundle_digest` 相同；否则为 `mixed_group_members`。这正是 GRPO 按同一题多个尝试计算相对优势的边界，不应为来源扩展放宽。

**修正 / 验收**：改成“同一批次包含 SWE 组与 R2E 组，两组各自完成准入、优势与转换；组内仍为同一道题的多个 execution”。另保留不同题硬塞同组被拒的反例。多训练行仍归各自 execution，不把行数当成员数。纯改验收口径，不需要新用户决策。

### R4 · P2：R-a 指定的输入只有扩展 24 题，不是 48 题

**计划位置**：§3.1 原稿第 75 行。

计划指定 `M3/inputs/r2e_expansion_preparation/r2e_candidates_full.jsonl`，实读为 **24 行**；另一个“同源”路径也是相同的扩展 24。旧 24 在 `runs/env_probe_20260909_codex_backup/data/`，不会通过读取这两个同源文件补齐。

**修正 / 验收**：直接用已有 `runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl` 及旁边的 revision。探针已确认其 48 个 commit 与 `r2e_tasks_48.json` 完全相等；无需重新下载或再租机。保持 raw expected 原文，准备产物明确关联这份题单。R-a 开工前改路径即可。

### R5 · P2：一张镜像提前 chown，不能证明两个角色都不再付运行时成本

**计划位置**：§2.2 的成本说明、§3.5 单一派生镜像、§6 时间估算、DR3。

搬迁解释器、保留 `/root` 权限、清理答案历史与隐藏测试私有存放都合理。但 M3 的执行身份对照用 uid **54322**；正式 rollout 是 **54321**，grader 默认 **54322**。当前 rollout 初始化仍递归 `chown -R 54321 /testbed`，grader 控制面布置仍递归 chown 给 54322。一张树不能同时预置为两个不同属主，因此不能从“build 时 chown”推出“每次 episode 不再改整树属主”。`.venv` 的 census 排除也不影响这里的递归 chown。

**影响 / 边界**：至少一侧仍有真实属主更改和遍历成本；metacopy=Y 可以降低 copy-up 成本，不能据此宣称该操作已消失。本次没有重新测 Docker 耗时，不能把 M3 的旧秒数直接套到当前正式 profile，也不能仅按 9 秒测试中位数承诺整个 R-f 不到一小时。

**修正 / 分期**：不用为本片立即扩成复杂权限重构。可继续用现有身份和初始化，先在真实 profile 的小样本记录两侧初始化耗时、可写层增长，再给批量预算。若要兑现“构建一次、运行不递归改属主”，需同时设计角色镜像/属主与 runtime 的实际消费路径，不能只改 Dockerfile，更不应为省时临时放开 `/root`。DR3 的 A 路线可保留，成本理由需要收窄。

## 2. 分期、默认启用与共享文件

1. **同意 driver 实评分与正式 actor 实执行分两步**。R-f 完成只能表述为“真实 RH2 grader 路径 + 训练报告运输已验证”；正式 actor 取正确派生环境、harness 执行与冻结工件仍未验。正式基座诊断开始前补这段实际入口，CPU Docker + harness 替身就能先查环境与工件接缝，不必等八卡。原镜像不能因来源枚举扩展就直接成为可运行题包。
2. **多来源 loader 的默认集合必须写清**。目前 `trusted_prep --task-ids` 省略时会准备 controller 的全部任务（`prepared_tasks.py:251`）。计划既要 controller 合并来源，又要保留现有 SWE 产物不变，因此默认来源/选题集合应保持旧行为，R2E 用显式来源或题单选入。无需增加一套资格平台；避免安装新 adapter 便自动把尚未接好派生环境的 48 题混进正式输入。旧文件能读取与旧命令产生同样题单是两个验收点。
3. **正式镜像接入有两种表示途径**：本地 image ID 的租约支持，或把派生镜像发布到 registry 后写入其真实 manifest digest。后者可能复用现有租约。D4=B 阶段再结合部署选择即可，本片不用为此泛化镜像服务；无论选哪种，都不能把基础镜像 digest 冒充实际派生镜像身份。
4. **R-0 不宜继续标成无人负责的可选项**。A 账本最新记录已明确 manager 归 A、driver 归 B。B 的收口状态外显纳入 driver 切片，在 R-f 批跑前完成；不挡 parser/ingest。累计出现过清理失败、最终已清成功时保留诊断；未清理或不能确认结束才使 CLI 非零。`stage_error`、模型 reward=0 与运行失败分别对账。每题结果仍看账本，不能只看进程退出码。
5. **先覆盖接缝，再扩大重复次数**。本机先完成固定语料 parser 对拍和真实 manager 分支；真机先挑纯 pytest / xvfb / 自定义 runner，以及 dirty-tree、expected ERROR、P-A 各种必要形态，随后 48 题 noop/gold。旧 24 已有多轮重复证据，不必无条件再把旧 24 全部加两轮；环境改变、波动或分歧的题再针对性重复。已有套件按变更范围跑，最终集成再完整运行一次，不要求每片机械重跑全仓。
6. **共享文件**：R2 已明确需要 manager 改动，不能遗漏在只标 envpack 为共享文件的表里；等 A 的启动清扫改动完成后由 B 基于该版本改。`adapters/miles/run_report.py` 也正由其它 A 任务修改，优先测试现有消费者，仅实际缺字段时再协调窄改。不改 loss、DIS、组语义与其它 A 决策。

## 3. DR1–DR4 与 T0 扫描

| 项 | 审查意见 | 决策性质 |
| --- | --- | --- |
| DR1 | 推荐 A：来源专有 private bundle + 按 schema 判别，共用 controller/spec；保留旧 SWE 字节与默认题单。不要用无类型 dict 或复制 controller。 | 新来源材料契约范围可一次确认；既有 R2E 报告方案 A 不重开，具体 union/字段实现归 T1。 |
| DR2 | **撤回当前二选一**。固定真实上游代码，按其实际去色行为接入；当前六题不存在宣称的差异。 | 当前为 false-positive T0，不让用户批准错误“原版”与“修正版”的选择。 |
| DR3 | 推荐 A：逐题派生环境、解释器搬迁、答案历史清理、隐藏测试 root 私有位置，评分时恢复来源原文；按 R5 补实际身份与成本边界。 | 环境/材料存放方式可一次确认；构建脚本与分工是 T1，不把文档指定 owner 当成已派发。 |
| DR4 | 同意接线阶段保持 expected-map 来源口径，保留两个 gold=0 的已知反例；资格、参考修订与额外防作弊仍归后续流水线。 | 与既有分期一致，是范围确认，不等于批准 48 题进入训练。 |

**没有新增必须现在拍板的训练算法或奖励 T0。** 期望映射修订、最终题单及 repo helper 保护属于 deferred T0；当进入题目处理/真实模型探针时再拿具体证据决定。实际初始化成本、正式 profile 对账和 actor 实执行属于尚需验证的事项，不用虚构实验结果，也不因未测就停止所有本机切片。

## 4. 验证与审查边界

- 读码：source/private/prepared/controller、spec 渲染、baseline census、replay driver、manager 报告与 P-A、报告契约、组准入；对照用户已批 R2E 方案 A、第四组分期、L4/M3 及 09-09 勘误。
- [probe_plan_seams.py](probe_plan_seams.py)：固定源码纯函数重放 336 份现有日志；48/24 材料核对；部分参考在场的 P-A 反例；五条真实 manager 报告分支（R2E 字段 producer 为替身）；生产 profile 渲染的 UID/chown 核对。命令见文件头，结果在 [probe_results.json](probe_results.json)，进程退出 0。
- 336 份日志来自既有实跑：旧 24 的 noop/gold 各 3 次，共 144；M3 的 48 题 noop/gold 各 2 次，共 192。它们不是本轮新容器实验。聚合为 noop 168 个 0；gold 164 个 1、4 个 0（M3 两道已知反例各两次），不能把 336 当 336 道题。
- 适用性扫描：A/F/G（归因、接线、与已定语义一致）、B/E（0 与 None、同题分组、真实 producer 验收）、D/H/N（材料/镜像/来源版本与兼容）、I/J/K（分期、避免伪双版本与重复入口）、L/M（初始化成本和可观测结果）均已检查；C 未引入临时挡板。多 rank/GPU 并发、真实 actor 与尚未构建的派生镜像不在本次证据中。
- 止损：下一轮核对这五项及分期文字是否落实；实现后按切片验收真实入口。不要重新开已收口的 SWE footer/CR1/CR3 审查，也不要为这份计划重跑 216 题。
