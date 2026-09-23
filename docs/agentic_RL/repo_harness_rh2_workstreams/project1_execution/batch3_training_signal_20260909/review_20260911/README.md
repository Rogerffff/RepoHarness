# I19 / I20 实施聚焦复核（2026-09-11）

**结论：I19 窄清理通过本轮复核；I20 已实现，但四项 P2 统计问题修正前，不宜把输出当可靠的 run 诊断报告。** 四项均属于消费者接线与统计口径，未发现它们改变训练 reward、loss 或准入。无需新增 owner 决策，也不需要为本次修复安排 GPU 作业。

审查范围：`f7521d94` → `76ede7f4800c5a8f485418bc7cdb19a8ed13c0c9`，覆盖 `2a18fe50`、`f9e151cb`、`9d13b1f3`、`a467d885`、`a8e49e0d`、`76ede7f4`。miles 集成树为 `4c04f997b60fd08c36941d8715db06bfc0ed0543`，工作树无改动。前批 N1–N4 不重开，I18 继续未定。本轮没有修改生产源码、维护测试或训练配置，没有提交、推送、stash、checkout 或 git apply。

## 1. I19：已足以收口的部分

- `generate.py:1076` 守卫表只剩三个已批的重试 / fallback 键；`bringup.py:476、1272` 两处生产入口仍调用同一合并函数，保留冲突检测。取消强制注入 `DISABLE_COMPACT` 不等于主动擦除用户自行传入的同名环境值，也不保证每次执行都会压缩。
- 已删除 `reject_context_shrink` 配置、正式链强制耦合、叶链拒绝、bringup 的旧环境解析与 launcher 的 export / runtime env；会话级长度下降仍只写线索，不影响准入。
- 两个新用例经过真实 `TrajectoryManager`、capture、身份导出、正式编排、投影、准入和训练数据转换，检查了每个生成动作恰训练一次、原请求上下文、摘要重注入后的 mask=0、execution 分母。harness / Docker / grader 等为替身，测试文件也明确了这个边界。
- 不要求原封不动复制已引用删除字段的旧五案脚本。新两案、I01 既有覆盖及本轮 171 项相关回归足以验收这次窄清理；它们不等于目标 CC 的真实压缩协议已验真，更不等于 MoE 路由问题已解决。

非阻塞文字余项：`generate.py:1968–1971` 仍写“收缩 fail-closed、正式基线必须 True”，`:2108` 仍提 reject 开关；`:1121` 的历史别名注释仍称压缩闭环。请顺手改成当前纯观测语义。[I19 Brief](../i19_impl_brief_20260910.md) §1.2 的“Microcompact 等今天就在发生”也应收窄为参考版本存在这些机制，目标 CC 仍待真实请求核对，不能从 B 表示或本机合成测试推出它们已实际启用。

## 2. I20：本轮建议修正的四项 P2

共同不变量来自 [I20 Brief §3](../i20_run_report_brief_20260910.md)：单位分开、消费真实 producer、未知不当事实、run 身份不混连。四项均为 **production_reachable**；对应输入由当前生产函数生成，主审独立执行了下述 CPU 探针。建议现在修的原因是它们直接影响本工具已承诺的诊断用途，修复局限于消费者及维护测试，不需要扩建平台或新增训练拒绝路径。

### R1：生命周期读取了错误字段，计数被当作秒数

- **当前行为与位置**：`rh2/src/repoharness2/adapters/miles/run_report.py:531–536、550–559` 查找 `lifecycle_timing.segments`，找不到就把整个 lifecycle 字典当计时段。
- **生产证据**：`rh2/src/repoharness2/adapters/slime/attempt_timing.py:121–130` 写出的字段是 `segments_seconds`；`generate.py:2258–2300`、`bringup.py:699–712` 原样持久化。真实 writer 输出 `test=40 秒`、`sandbox_container_start=3.5 秒`、排队深度 `7` 后，报告没有两个耗时段，反而在 `lifecycle_segments_seconds` 中报告 `grading_queue_depth_at_enqueue.sum=7 秒`。
- **违反与影响**：不是单纯少展示两个指标，而是读取失败后混淆单位；会把瓶颈藏掉，同时制造不存在的耗时。新测试 `_audit()` 手造了 `segments`，因此没有覆盖真实 schema。
- **最小修复与验收**：消费 `segments_seconds`，队列深度 / backpressure 等独立处理或标未采集；不要把整个容器字典作为“兼容秒数”兜底。使用真实 `AttemptLifecycleTiming.to_dict()` / audit writer 的输入，40 与 3.5 正确出现，队列深度不进入秒数桶；缺失计时仍为未知。探针键：`R1_lifecycle`。

### R2：评分取自不存在的 audit 字段，已评分被算成未评分

- **当前行为与位置**：`run_report.py:252、291–325、567–575` 读取 `audit.grading`，并把缺这个键直接计入 `attempts_without_grading`。
- **生产证据**：`bringup.py:652–763` 的 `write_execution_audit_record()` 不写 `grading`。评分实际由 `BringupService.record_event():1814–1888` 写到 `bringup_events.jsonl`，而报告 loader `run_report.py:110–139` 不加载这个文件。探针用真实两处 writer 写一条 `resolved / reward=1` 的已评分执行，报告仍为 `attempts_without_grading=1`、`audit_grading=null`。
- **违反与影响**：字段未采集被误当成业务上的“未评分”，且可信评分总体、按 task 的 reward 分布与评分细分耗时拿不到。测试夹具自己添加了生产 audit 没有的 `grading`，掩盖了断口。
- **最小修复与验收**：优先复用既有 `bringup_events.jsonl` 的评分事实，明确其与 audit 的 session / run 关联，不为报告复制一份新生产账本。缺评分记录时区分“无法知道”与“已知没有评分”；如果首版暂不消费，必须把相关面标未采集并撤回完成声明，不能继续报未评分计数。验收至少包含实际 writer 的成功评分、失败 / 缺失、audit 与评分记录顺序不同三类输入；缺记录不变成 reward=0。探针键：`R2_grading`。

### R3：把 FORK 训练行当成 GRPO 成员统计 reward 与优势符号

- **当前行为与位置**：`run_report.py:334–359` 对 `rollout_group.rewards` 每一项计一次成员，并用这些值的均值推算优势符号。
- **生产证据**：miles `miles/ray/rollout/rollout_manager.py:235–329` 的真实 `_emit_rollout_evidence()` 逐叶写 reward 和重复的 `sample_indices`，同时提供 `leaf_ordinals`。两个 execution 的 reward 为 0 与 1，第一个分三行，真实事件为 `sample_indices=[10,10,10,11]`、`rewards=[0,0,0,1]`。报告 `consumed_member_rewards.count=4`、sum=1（据此均值为 0.25），优势符号为正 1 / 负 3；应为 2 个成员、均值 0.5、正 1 / 负 1。
- **违反与影响**：长轨迹 / 经常分行的成员在诊断分布中权重更大，可能让人错误归因于训练收益或样本难度变化；此处只影响报告，不能说训练本身也按行错误计权。
- **最小修复与验收**：按 run、组、execution 身份先归并成员，再计算成员 reward 和组均值；训练行分布另列。相同成员各叶 reward 不一致时显式记数据矛盾，不静默选第一条。验收上述两成员不等分行数的真实 emitter 输入，正控为各一行，组 / 成员统计应相同。
- **总体边界一起说清**：`rollout_manager.py:216–220` 是 `_get_rollout_data()` 从 buffer 取完后才发 `rollout_group`。它能说明已交付给 learner 的组，不能代表被过滤前的全组总体，也不证明已进入 applied optimizer step。Brief 承诺的三种分布应分别说明有无来源；暂缺的总体标未采集，不从现有事件推造。当前 exact tuple 的 consumed join 是成立的，探针未匹配数为 0；不需要为此重写组连接。探针键：`R3_fanout_reward`。

### R4：默认多 run 输入发生 step 碰撞，指定 run 仍混入其它 audit

- **当前行为与位置**：`run_report.py:205–220、500–510` 的 step 去重和消费并集键只有 `(rollout_id, step_id)`，不含 run；`:601` 让所有缺 `run_id` 的 audit 无条件通过指定 run 的筛选。loader 又没有保留可判定归属的逐行来源。
- **生产证据**：CLI 明确接受多路径 / 递归目录，help 还承诺不跨 run 混连。真实 `_emit_train_step_event()` 生成 r1 与 r2 各一个 `(0,0)`，execution 数均为 8，accepted 均值分别 2 与 5。合报只得 1 step / 16 token，应为 2 steps / 56 token。`--run-id r2` 的事件正控为 40 token，但两个真实 audit 都被保留，attempt 数仍为 2，应为 1 或归属未知。
- **违反与影响**：比较两次实验、读包含重启结果的父目录时会少算训练进展，并把他次运行的覆盖率、失败与耗时混进选定 run。
- **最小修复与验收**：统一带 run 身份的连接 / 去重键；连续未更新步数也不能跨 run 接起来。audit 归属使用真实文件边界 / 已有标识，不靠“缺失即属于当前 run”。更小的首版选择是明确只支持单 run 输入并拒绝歧义，保留报告层的未知项，不需要新 registry 或训练门。验收两 run 同名 step、同名样本、各有 audit、指定 run 的对照。探针键：`R4_runs`。

## 3. 可单独登记的 P2：R5，TP 副本重复累计

**条件可达，当前默认 TP=1 不触发，不阻塞 I19 或当前 TP=1 下的报告修复收口。** `run_report.py:407–417、445–455` 直接累计所有逐叶 DIS / logprob entries；`faithful_dis_loss.py:774–775` 只限定 CP rank 0，未去掉 TP 副本。actor 的 `_emit_logprob_compare():483–522` 同样没有 TP 去重。当前 `launch.sh:148–149` 默认 TP=1、CP=1，但 TP 有覆盖位。

真实 emitter 的 CPU 基数模拟（TP2 × DP2）：两个不同 DP 叶 accepted=3 / 7、provenance=5 / 11，各发两份 TP 副本；报告为 20 / 32，应为 10 / 16，同版本可比动作数也从 16 变 32。逐叶事实被当成独立贡献，违反“副本不重算、真实 DP 分片保留”的口径。探针键 `R5_conditional_tp_copies`；这是源码追踪与 CPU 发射模拟，没有运行 GPU collective。

建议 Claude 随消费者修复一并评估：能在真实消费身份内去副本就做；证据不足则明确当前仅验证 TP=1，TP>1 的此两项为未支持 / 未知。不能只取 DP0 丢掉真实分片，也不能按叶身份跨所有 step 盲目合并。验收为 TP1 正控、TP2 副本与不同 DP 叶同时在场。无需改 loss 或路由链。

## 4. 为什么绿灯没有覆盖这些问题

I19 测试跨了所改的生产接缝，验证有效。I20 的七例主要检验手造记录的算术；`tests/adapters_miles/test_run_report.py:19–36` 中的 `grading`、`lifecycle_timing.segments` 不属于真实 audit schema。“FORK 三行一题”那例只检查动作覆盖，没有喂入重复 reward 的真实 `rollout_group`；跨 run 测试只按参数筛掉异 run 事件，没有覆盖默认合报与 audit 来源。

建议把本轮反例移入既有 `test_run_report.py`，通过真实序列化 helper 或最小真实输出建立 fixture。无需为七面各造大型集成测试，也无需为了报告引入 Docker / GPU 依赖。

## 5. 验证与证据

- 主审相关测试 **171 passed / 0 failed（23.29 秒）**，原始输出 [focused_tests.txt](focused_tests.txt)。覆盖本批两测试文件、I01、slime generate、F2-2、formal chain、准入、prepared chain、正式入口。
- 相关改动文件 ruff 通过；launcher `bash -n` 通过；lanes 只独立跑了 `--checks-only`，输出 [lanes_checks.txt](lanes_checks.txt)。没有重跑作者的 2261 全量或完整双 lane，不能把作者数字称为本轮独立结果。
- 黑盒 CLI 接线边界按标准使用 Production Tracer / Falsifier 一对做有界核查；主审独立重跑所有报告反例，未照转子报告。被推翻的猜想包括 consumed tuple 无法匹配、I19 两案声称验证真实 CC、当前正式链内同一 step attempt 重试碰撞，均未列为 finding。
- 本轮探针 [consumer_probe.py](consumer_probe.py) 与 [consumer_probe_result.json](consumer_probe_result.json)。前四例调用真实 audit / bringup / rollout / train-step 序列化函数；Ray / Megatron 函数原样提取 AST，只替换硬件查询和事件 sink；最终调用真实 loader / report。R5 单列为条件性基数模拟。
- [source_snapshot.json](source_snapshot.json) 记录审查源码摘要；收尾校验见 [review_verification.json](review_verification.json)。未运行真实 CC、Docker、API、GPU；目标 CC 请求面核对仍归基座诊断，I18 未决不变。

从仓库根目录复跑（退出 0 表示当前反例成功复现，不是报告正确性通过；修复后应更换验收断言）：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch3_training_signal_20260909/review_20260911/consumer_probe.py
```

主审相关测试命令（`rh2/` 内）：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" .venv/bin/python -m pytest -q \
  tests/adapters_miles/test_run_report.py \
  tests/adapters_miles/test_i19_compaction_representation.py \
  tests/adapters_miles/test_i01_fork_wiring.py \
  tests/adapters/test_slime_generate.py \
  tests/adapters/test_f2_2_capability.py \
  tests/adapters_miles/test_w1a_formal_chain.py \
  tests/adapters_miles/test_w1b_group_admission.py \
  tests/adapters_miles/test_w1b_prepared_chain.py \
  tests/adapters_miles/test_w3b_formal_entry_vertical.py
```

## 6. 范围扫描与停止条件

| 维度 | 本轮结论与证据 |
|---|---|
| A / D / G | I19 真实双入口仍合并三个守卫；无新状态 owner。I20 对照真实 writer 与 CLI，R1 / R2 / R4 可达。 |
| B / C / F | I19 删除项已有 owner 定案；保留动作、终局 reward、execution 分母。I20 只读，无新的拒绝 / 熔断；报告分布偏差为 R3。 |
| E | 171 项相关回归通过，但 I20 手造 schema 避开真实缺口；用本轮 producer 接缝反例补验收。 |
| H / M | 复用既有事件 / 成本汇总器是正确方向；消费者字段、身份与单位偏差见 R1–R5，不新增第二份事实账本。 |
| I | I19 现在收口；I20 修 R1–R4 后只做针对性复核；R5 条件性登记；真实 CC 核对与 I18 按原阶段推进。 |
| J / K | I19 有非阻塞旧注释；I20 优先修映射与小 helper，不建议增加配置平台或逐指标类层次。 |
| L | I20 离线读取整批文件，不在训练热路径增加采集；大 run 文件的内存 / 时间未实测，不声称已验证容量。 |
| N | 本批未改 vendored slime、miles fork 或依赖 pin；真实 CC 兼容性仍有限定。I20 现有 schema 兼容缺口即 R1 / R2。 |

**停止条件**：Claude 对 R1–R4 给出处置，真实 producer 输入得到上述正确值或诚实的未采集 / 未支持状态，对应维护测试与直接回归通过，即完成 I20 本轮复核。不以补齐所有未来观测项、增加真实 CC / GPU 实验、解决 I18 或扩展第四组评分语义为本批收口条件。R5 和文字余项可随手处理，也可显式登记，不扩大当前阻塞范围。
