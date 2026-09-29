# I01 B 实施的 Codex 聚焦审查

日期：2026-09-09。对象：主仓库 `2a533b1f9b8e7cc8a9aca1a90b8ea1b32afb31f8` 上未提交的三个源文件、一个既有测试和一个新增测试。具体文件与内容摘要见 [review_snapshot.json](review_snapshot.json)。本次只审 I01 B 接线及其观测，不重新决定 B/C、I18/I19 或预算策略。

**当前状态：2026-09-09 修复后的针对性复核通过，R1/R2 均已关闭，运输测试已补齐；本批无未解决的阻塞 finding。** 修后证据见 §7 与 [followup_snapshot.json](followup_snapshot.json)。§1–6 保留首审时的发现与结果，不表示当前仍待修；代码尚未提交，目标 GPU 验证仍按原定 spike。

## 1. 结论

**B 的生产接线与本机消费接缝通过；本批观测部分有两项 P2，建议窄修后再提交。未发现本补丁引入 P0/P1 训练语义问题。** 两项问题都已用当前真实 adapter/manager/finish 包装的 CPU 反例复现：同一 token 漂移被多个后继叶重复计数；末行差额被过宽地解释成 B 相对旧阈值的成本增量。它们不改变训练 token、mask、reward 或 member 权重，但会误导这次特意新增的诊断。

建议只修下述 R1/R2 并补对应反例；修复后聚焦复核，不再扩大成全仓审计。Claude 可以同时准备预算终止闭环的 Brief，但共享文件继续串行修改。当前没有提交或推送，也没有替用户决定提交。

## 2. 已核实的接线与验证

- `bringup.py:905–908` 在真实 `BringupService` 的 `AnthropicAdapter` 构造处传入常量 0；`finish_session` 包装在 `:711` 读取同一 manager 的实际阈值。vendor 的 REALIGN 条件在 0 下不成立，消息 rewrite merge 也显式关闭。不是仅修改测试构造器或身份导出的默认值。
- 生产包装在 `bringup.py:740–755` 生成统计并暂挂叶样本；`generate.py:2815–2817` 在后续资格检查前取走统计、剥除临时属性并写入 audit；`bringup.py:590` 写出 JSON。`canonicalize` 的未知属性规则没有被放宽。
- 额外的[生产运输探针](production_transport_probe.py)复用现有测试替身，贯穿真实 AnthropicAdapter 会话面、manager、finish 包装、`fa_formal` 编排、audit、canonicalize、组准入、buffer 和训练数据转换。两个 member 各产 `[22,35]` 两行，转换后 `rollout_ids=[0,0,1,1]`、`rollout_mask_sums=[18,18,18,18]`、`raw_reward=[1,1,0,0]`；每 member audit 的两轮都保留，miles 样本无诊断/身份临时属性。主审独立重跑，结果见 [review_transport.json](review_transport.json)。生成响应、capture 绑定、Docker、评分与排空屏障使用替身，不能视作真实 CLI/HTTP/GPU 作业。
- [独立反例探针](falsifier_probe.py)还验证了多次 token FORK、token drift 后消息 rewrite 的共享前缀：各 capture 只回填一次。主审重跑输出见 [review_counterexamples.json](review_counterexamples.json)。

| 主审实际运行 | 结果 | 证据 |
|---|---|---|
| 默认 miles 基座，I01/bringup/F1/编排/组准入/交付的七份定向测试 | 141 passed、1 skipped；6.85 秒；exit 0 | [pin 输出](review_tests_pin.txt) |
| 相同测试切到 `reference/miles-rh2-integration` | 142 passed；7.06 秒；exit 0 | [integration 输出](review_tests_integration.txt) |
| 五份被审文件的 ruff | exit 0 | [ruff 输出](review_ruff.txt) |
| 生产运输探针与独立反例探针 | 均 exit 0；前者通过运输断言，后者确认两个现存问题 | 上述两个 JSON |
| 源码差异/内容检查 | tracked diff 无空白错误；被审五文件在上述验证期间内容未变；vendored slime 与 miles 集成工作树无改动 | [内容摘要](review_snapshot.json)，本轮工具输出 |

定向命令在 `rh2/` 执行：

```bash
uv run --frozen pytest tests/adapters_miles/test_i01_fork_wiring.py tests/adapters_miles/test_bringup_vendor_only.py tests/adapters_miles/test_f1_turn_identity.py tests/adapters_miles/test_f1_e2e_identity_chain.py tests/adapters/test_slime_generate.py tests/adapters_miles/test_w1b_group_admission.py tests/adapters/test_w1b_delivery_face.py -q
```

integration 使用同一命令，设置 `RH2_MILES_PATH` 指向当前集成 checkout。默认基座跳过的是依赖 integration 字段的既有 F1 纵链；新增 I01 的 run8 重放在两次运行中均实际执行。Claude 报告的全量 `1774 passed / 310 skipped` 未在本轮重新全量运行；不能把以上定向数字描述成全量验收。目标 GPU 的 packing、显存和 step 耗时仍按原定 spike 验证。

## 3. R1 / P2：共享历史上的同一次 token FORK 被重复记事件

**当前行为与位置：** `turn_identity.py:153` 对每个 routing leaf 重放祖先链，`:182–194` 对遇到的 FORK 都追加事件。训练归属有 `claimed` 去重，事件没有。同一个生成节点在两条叶的共享前缀中出现，就留下两条相同 `turn_index` 的事件。

**应满足的口径：** 当前 Brief 将这些数据用于真实请求的漂移率与分歧位置分布；一个已发生的生成轮漂移，不应因未来多出一个后继叶而变成两次。若统计的其实是逐叶重放操作，需要另作明确命名；本批更适合按真实生成轮计数。

**证据与生产可达性：** `production_reachable`，不是生产频率实测。四轮会话：t2 在 t1 响应内 token 漂移，t3 正常继续，t4 的历史消息改写 t3。阈值 0 保留两条消息叶，它们共享 t2。探针得到行长 `[6,12,15]`、四轮各自 capture 使用一次，但 `fork_events` 含两条完全相同的 t2 记录。全部 prompt 长度递增、各轮在 cap=100 以内；不依赖 subagent、compaction、未决 I19 或异常引擎返回。

**影响与分期：** P2，本批观测收口前修正。会夸大漂移次数；若以唯一生成轮数为分母，还会使漂移率前后口径不同。它没有造成重复训练。这里修的是新观测自身的正确性，不新增训练闸门。

**复现：** 仓库根运行 `rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_b_impl_20260909/falsifier_probe.py`；结果键 `shared_prefix_token_fork_then_message_rewrite`。

**最小修正与验收：** 利用现有首次认领信息，或在本次导出内按 node/turn 身份只记一次漂移。不改变 builder 或 mask。四轮反例只保留一条 t2 事件，训练行/掩码/四个 capture 的一次归属保持；连续两次独立漂移仍分别保留 t2、t3。无需新增跨 execution 状态、哈希或拒绝路径。

## 4. R2 / P2：末行差额不等于 B 相对旧阈值的额外成本

**当前行为与位置：** `turn_identity.py:268–270` 计算 `sum(row_tokens)-row_tokens[-1]`；同文件 `:99–100`、Brief §3 和 Claude 实施记录将它解释为 B 相对“REALIGN 单行”的额外输入量。公式本身算对了，但这个解释并不普遍成立。

**应满足的口径：** 训练输入的实际规模与更改阈值带来的增量是两个不同事实。旧阈值 1024 也会 FORK，消息树也不保证只有一条叶；不能假设所有旧执行都等价于当前最后一行。

**证据与生产可达性：** `production_reachable`。两轮会话，首轮完整序列长 6，次轮 prompt 长 7，在上一响应内漂移，次轮输出恰为 1024。阈值 0 和 1024 均产 `[6,1031]`，总量都是 1037，实际 B 增量为 **0**；字段却报告 **6**。两轮在 cap=2000 内，1024 响应也属于现有请求允许的输出范围。无需未来功能。run8 的 19132 差额在那条具体轨迹上成立，不能据此推广到所有轨迹。

**影响与分期：** P2，本批观测收口前校正。将旧方案本来就存在的分叉成本归给 B，会误导后续性能和 C 方案判断；多叶时最后一行还受树遍历顺序影响。没有改变实际样本或 GPU 计算。

**复现：** 同 R1 命令，输出键 `long_output_b`、`long_output_old_threshold`、`actual_b_delta_against_1024`。当前新增测试中直接复写求和式的断言不能检验这个比较含义。

**最小修正与验收：** 推荐保留 `row_tokens`、总行 token 数等直接可观测量，删除该差额字段，或将其改名并明确仅为“除末行之外的 token 总数”，不得再称为相对旧阈值的实际增量。同步更新注释、Brief、实施记录和相应 oracle。不要为修指标而在线增加一遍旧阈值重放，也不新增专门 B/C 实验。上述两种阈值输入量相同的反例必须能阻止再次将该量解读为真实增量。

## 5. 不扩大本批范围的事项

- **裁剪后的 `turns_trained` 口径：非阻塞。** 集合在最终裁剪前累加，人工超预算 TurnRecord 能使它高报；但当前实际安装的 `capture_wire.py:1046–1058` 在同一 session 上限下限制输出，prompt 已达上限时返回空响应，`generate.py:2723–2728` 与 finish 读取同一上限。B 的有效非空响应遵守该预算时不会被相同上限从最终行中裁掉。当前反例标 `test_only`；引擎超额返回或未来单独增加训练裁剪上限才成为 `conditional_future`。记录即可，不为它加新挡板；以后引入独立裁剪时再由最终存活 spans 定义覆盖计数。详细反证见 [Falsifier 报告](falsifier.md)。
- **“进入训练行”不等于实际已优化。** 本统计发生在组准入与 learner 前，后续丢组或零梯度仍可能存在；它只证明该 execution 的候选训练表示，不替代 I15/I17 观测。`fork_events` 目前只记录 token builder 漂移，也不是所有消息分枝、全部 horizon 事件的总表。
- **测试与 Brief 的偏离应如实收口。** 将共享身份测试放在新文件、将汇总并入既有导出循环都合理。既有 fan-out 测试可复用；本次运输探针又补证了真实 FORK 行贯穿消费。Brief §5(c) 承诺的非空 coverage 经 orchestrator/audit 落盘断言在新增 13 例中并不存在，原测试只直接验证 `take_turn_coverage` 剥除；本次独立探针提供了该证据。修复时可将这个窄接缝断言纳入维护的测试，或准确链接探针，不能仍声称原 13 例已覆盖全部运输。
- **无需新增 T0 或升级 audit schema 版本。** 阈值常量落实已批 B；当前可选 audit 字段没有改变既有字段语义，仓库内未发现要求该记录严格枚举键的消费者。I01 不要求重写公共训练 schema、canonicalize 或 vendor。常量接线、字段口径与测试 oracle 的变化按 T1 说明即可。

## 6. A–N 适用性与审查收口

| 维度 | 本批证据与判断 |
|---|---|
| A 正确性/并发/安全，D 所有权，G 生产路径 | 生产构造与同 manager 阈值已核；复用既有 drain 后快照、无新异步 owner；运输探针核属性剥除。没有重验 Docker 安全或分布式关停，这些接口本批未改。 |
| B 分布，C 挡板，F 决策一致性 | 按已批 B 保留动作；探针确认唯一 capture 归属与 member 分母；无新拒绝/过滤/阈值闸门，C/I18/I19 未扩展。 |
| E 测试，H 唯一事实，M 观测 | 两基座定向测试、真实包装反例与运输；R1/R2 是本批须修的观测口径，原公式断言不构成独立 oracle。 |
| I 分期，J 可读性，K 演进成本 | 两项局部 T1 修正即可；不将裁剪反例或后续链路缺口拉进本批，复用原导出而未新增第三份线性化算法。 |
| L 性能/容量 | 增加导出期局部计数、一次树扫描、FORK 时再次找公共前缀；没有额外 actor forward、网络请求或跨 execution 累积。未测 GPU 性能，不用 token 差额代替耗时；R2 限制成本解释。 |
| N 兼容性 | vendor/miles 未改；旧导出 API 仍返回原 exports，生产 attach 返回值仅由本次包装消费；audit 可选字段与临时属性隔离已核。 |

独立分工：[Production Tracer](production_tracer.md)核生产接线、消费与运输；[Falsifier](falsifier.md)核观测反例、共享历史与边界；主审回读 diff、独立重跑两类探针并归并为 R1/R2。无新 T0、无新增挡板；修正的是“计数可直接代表漂移次数/新增成本”的两项结论。后续只复核 R1/R2 及其受影响接缝，不用本报告要求再开一轮完整审计。

## 7. 修复后的针对性复核（2026-09-09）

**裁定：通过，R1/R2 关闭。** 对照首审内容摘要，本次只有 `turn_identity.py` 与 `test_i01_fork_wiring.py` 内容发生变化；`bringup.py`、`generate.py` 和既有 bringup 测试保持首审版本。未重新审查已通过的全链边界，也没有重复派发双角色审查。

| 复核项 | 实际结果 |
|---|---|
| R1 事件去重 | `forked_ids` 只控制统计事件追加，不包住 builder 创建或训练 span 更新。共享前缀反例事件 `[2,2]→[2]`，独立漂移仍为 `[2,3]`。 |
| R1 训练表示不变 | 主审复用首审真实包装/backfill 探针，并与首审 JSON 对比：行长、mask 总和、逐行身份 span、各 capture 使用次数全部不变，四轮 capture 各使用一次。 |
| R2 口径与实现 | 旧字段移除，改为 `input_tokens_total` 和 `input_tokens_excluding_last_row`。docstring 与 Brief 已明确后者仅为除末行外的 token 总量，不是阈值变化造成的增量。两阈值均为 `[6,1031]`，总量均 1037、除末行量均 6；真实差额仍为 0。 |
| 运输测试补齐 | 新维护测试实际经过 orchestrator、audit writer、canonicalize、组准入、buffer 与转换；断言两 member 各两行、audit 每 member 总输入 57、单条 t2 事件、样本无临时属性、rollout 分母均 18。默认及集成基座均执行通过。 |
| 非阻塞裁剪项 | 本次未改截断或 `turns_trained` 的定义，仍按 §5 记录的生产前提处置；没有因此新增门槛。 |

主审在 `rh2/` 新运行的命令：

```bash
uv run --frozen pytest tests/adapters_miles/test_i01_fork_wiring.py tests/adapters_miles/test_f1_turn_identity.py tests/adapters_miles/test_f1_e2e_identity_chain.py -q
uv run --frozen ruff check src/repoharness2/adapters/slime/turn_identity.py tests/adapters_miles/test_i01_fork_wiring.py
```

- 默认基座：**36 passed / 1 skipped**，2.74 秒；[输出](followup_tests_pin.txt)。既有 F1 integration-only 用例跳过，新增 18 例全部执行。
- 同一 pytest 命令切换 `RH2_MILES_PATH` 到集成 checkout：**37 passed**，2.56 秒；[输出](followup_tests_integration.txt)。
- ruff：exit 0；[输出](followup_ruff.txt)。
- 独立修后探针：仓库根运行 `rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_b_impl_20260909/followup_probe.py`，exit 0；[脚本](followup_probe.py)、[结果](followup_probe_result.json)。原 `falsifier_probe.py` 的 main 保留“确认旧缺陷存在”的断言作为历史证据；修后验收使用新脚本，不修改旧反例来伪装历史通过。
- 本轮被审五文件在验证期间内容不变，内容摘要另存 [followup_snapshot.json](followup_snapshot.json)。没有修改被审源码/测试、vendor 或 miles；没有运行真实 Docker/GPU/API 作业，也没有提交或推送。Claude 报告的全量 1779/310 没有在本轮再次全量运行。

本批可以结束聚焦审查，继续预算终止闭环；无需再开一轮 I01 全面审计。提交范围与操作由用户后续指示，GPU packing/显存/耗时不因 CPU 复核通过而记为已验证。
