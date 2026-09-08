# I01 实施计划（Owner Brief）：B 路线接线 + 动作覆盖与新增行计数

日期：2026-09-09。作者：Claude（A 线）。状态：**已实施、未提交；2026-09-09 Codex 修后针对性复核通过：R1/R2 已关闭，运输测试已补齐，本批无未解决的阻塞 finding，见 [审查正文 §7](codex_review.md#7-修复后的针对性复核2026-09-09)。** 目标 GPU 的 packing/显存/耗时仍待原定 spike。原状态：**按协议"小批开工前一页 Brief，发出不等回复"发出；本批只含已批内容，发现新 T0 即暂停依赖它的部分。** 基线：主仓库 `2a533b1f`，开工前 `rh2` 源码与原审查基线无差异；miles 集成 `98a0272e4`，本批不改 fork。

## 1. 实现哪些决定

- [I01 定案：B 路线](../decision_batches_20260908.md#1-已定i01-首版采用-b)（用户 2026-09-08 原话："I01可以确定B 作为首版路线，C 暂缓，不排专门的 B/C 对比实验"）。
- [可开工清单 §4.1 第一行](../decision_batches_20260908.md#41-直接准备实施的明确部分)：真实 manager 显式接入 `fork_threshold_tokens=0`；记录动作保留量及新增行成本；推理输入与 execution/member 计权不变；不做 C、不改 tokenizer、不决定 I18/I19。
- 依据的证据：[run8 六轮重放](../i01_options_20260908/run8_cost_probe.py)（阈值 0 下 1 行变 2 行，总输入 26,283 → 45,415，可训动作 2,148 → 2,772）、[Codex 八案探针](../i01_options_20260908/threshold_probe.py)（真实 manager + 身份导出 + backfill，阈值 0 关闭 REALIGN 与 rewrite merge 两个销毁点）。

## 2. 改哪些文件、哪些函数（本批唯一修改者：Claude A 线）

| 文件 | 改动 | 行数估计 |
|---|---|---|
| `rh2/src/repoharness2/adapters/slime/bringup.py` | ① 模块常量 `FORK_THRESHOLD_TOKENS = 0`（与 `MAX_TURNS_PER_SID` 同区，附一句"I01 B 路线；0 = 精确 token 前缀才合并，漂移保留旧行"）；② `AnthropicAdapter(...)` 构造传 `fork_threshold_tokens=FORK_THRESHOLD_TOKENS`；③ `PerRolloutAdapter.finish_session` 从 `attach_turn_identity_spans` 取回覆盖统计，以附加属性挂到叶链样本（与 `RH2_TURN_IDENTITY_SPANS_ATTR` 同一运输方式）；④ run 级记录 `runtime_profile.json` 增加 `fork_threshold_tokens` 一项，供事件 join | +25 |
| `rh2/src/repoharness2/adapters/slime/turn_identity.py` | `export_leaf_identity_spans` 在既有重放循环里顺带记录：每个 builder 的 `total_tokens / leading_prompt_tokens / trainable_tokens`，每次 FORK 的 `(turn_index, 首次分歧相对上一响应起点的偏移, 上一响应长度, 本轮输出长度)`；新增纯函数 `summarize_turn_coverage(root, exports)` 汇总为 `TurnCoverageSummary`。不新写第三份线性化算法，只在现有重放上加计数 | +60 |
| `rh2/src/repoharness2/adapters/slime/generate.py` | `RolloutAudit` 增字段 `turn_coverage: dict | None`；`finish_session` 返回后读出附加属性存入 audit 并从样本上剥除（与身份 span 同一处、同一方式）。`_generate_attempt` 控制流不变 | +12 |
| `rh2/src/repoharness2/adapters/slime/bringup.py::write_execution_audit_record` | 记录增 `turn_coverage` 键（可选字段，`schema_id` 不变，消费者忽略未知键；见 §6 T1） | +2 |
| 测试（§5） | 新增 1 个测试文件 + 扩 1 个既有测试 | +250 |

不改：`rh2/src/slime/*`（vendored 字节不变，走已有构造参数）、`reference/miles-rh2-integration/*`、canonicalize、group_admission、gate、loss、sampling 参数、capture wire。

## 3. 行为变化，逐条

1. **生产 manager 阈值 1024 → 0。** 效果：token 漂移落在上一响应区间内时不再 REALIGN 覆盖旧响应，而是 FORK 新开训练行；消息树上的 assistant rewrite merge 关闭，被改写的旧 assistant 节点保留为独立叶。每个真实生成轮在该 execution 的训练行并集中恰有一次 `loss_mask=1` 归属（`response_trained` 首领语义不变）。
2. **每 execution 训练行数可能 >1。** 新增行与原行共享 `index / group_index / rollout_id`（`to_sample` 现有语义），因此 miles 侧 `rollout_mask_sums` 按 rollout_id 跨行求和、优势按 group_index 按 member 计算，均不变；组准入的 fan-out 叶校验（同身份、同载荷、同 reward）已覆盖多行。
3. **推理输入不变。** 每轮仍全量重渲染送引擎；本批不改变模型看到的任何 prompt。
4. **新增观测（只记录，不判定）：** 每 execution 的 `turns_generated`、`turns_trained`、`turns_dropped_realign`、`turns_dropped_merge`、`training_rows`、`row_tokens[]`、`trainable_tokens_total`、`input_tokens_total`（全部行 token 之和）、`input_tokens_excluding_last_row`（全部行 token 之和 − 最后一行；**只是表示层观测量，不是 B 相对阈值 1024 的实际增量**——审查 R2 反例：次轮输出 1024 时两种阈值行长同为 [6,1031]，增量 0，字段仍为 6；要比较阈值只能各自重放后相减）、`fork_events[]`（分歧位置分类：`in_response` / `before_response`；按真实生成轮只记一次，共享前缀被多条叶重放时不重复计数，审查 R1）。落到 `fa_execution_audit.jsonl` 与 `RolloutAudit`；不进 Sample metadata，不进 miles wire。

## 4. 明确不变、不顺带做的

- 不引入 env 旋钮。0 是决定值，写成常量并落 run 记录；以后若做 1024 对照，改一行常量并在实验记录里登记。理由：默认值不应成为隐藏路径。
- 不改 `detect_context_shrink`、`max_sample_tokens` 截断、`bringup_leaf_facts` 多叶放行；不合并 `turn_identity` 与 vendor 的两份线性化。
- 不做 I18 路由来源、I19 压缩、thinking 保留策略、C 的检查点续接。
- 不改任何既有测试的 oracle 来"让它变绿"；只加新断言与新用例。

## 5. 测试：旧 → 新 oracle 与新增反例

| 测试 | 变化 |
|---|---|
| `tests/adapters_miles/test_bringup_vendor_only.py::test_bringup_service_constructs_with_vendor_only` | **扩**：断言 `service.adapter.manager._fork_threshold == 0`，且 `PerRolloutAdapter.finish_session` 导出身份 span 时用的是同一个值（单一来源）。**T1（新 oracle）** |
| 新 `tests/adapters_miles/test_i01_fork_wiring.py` | (a) 移植 Codex 八案为参数化用例，经真实 `AnthropicAdapter(fork_threshold_tokens=0)` → `TrajectoryManager` → `attach_turn_identity_spans` → `backfill_leaf_sample`：token 漂移与消息改写下均得 2 行、两轮全部入训、capture 回链 `c1,c2`；阈值 1024 的同输入作为对照保留旧行为，证明差异只来自阈值。(b) run8 真实 token 重放（`docs/.../s1/7a_artifacts/artifacts_run8` 缺失时 skip）：行长 `[19132, 26283]`、可训 2,772、`turns_generated=turns_trained=6`、`turns_dropped_*=0`、`input_tokens_excluding_last_row=19132`、`fork_events=[{turn_index:2, divergence_offset_in_prev_response:556, prev_response_len:624, next_output_len:606, position:"in_response"}]`。(c) 覆盖统计随 execution audit 落盘且随后已从样本上剥除（canonicalize 未知属性 fail-closed 边界不被触碰）——**审查后补**：首版 13 例只直接验证了 `take_turn_coverage` 的剥除，orchestrator→audit 落盘→canonicalize→组准入→训练数据转换的整段运输由 Codex 的 `production_transport_probe.py` 证明；修复批已把该接缝断言并入本文件（`test_coverage_reaches_audit_and_conversion_through_orchestrator`）。(d) 审查 R1/R2 回归：共享前缀 FORK 事件只记一次；`input_tokens_excluding_last_row` 在两种阈值下相等。 |
| `tests/adapters_miles/test_w1b_group_admission.py` | **不改 oracle**；补一例：同一 member 两行（模拟 FORK）经 canonicalize 后 `rollout_id` 相同、组准入 `keep=True`。 |
| `tests/adapters_miles/test_f1_turn_identity.py`、`test_f1_e2e_identity_chain.py`、`tests/adapters/test_slime_generate.py` | 不改。它们直接构造 `TrajectoryManager()`（库默认 1024），库层行为本批不动。 |

## 6. 验证方式与预期

```bash
cd rh2
uv run pytest tests/adapters_miles/test_i01_fork_wiring.py tests/adapters_miles/test_bringup_vendor_only.py \
  tests/adapters_miles/test_f1_turn_identity.py tests/adapters_miles/test_f1_e2e_identity_chain.py \
  tests/adapters/test_slime_generate.py tests/adapters_miles/test_w1b_group_admission.py -q
uv run pytest tests/ -q          # 期望：1761 + 新增用例数 passed，310 skipped 不变
uv run ruff check src tests
```

观测位置：`fa_execution_audit.jsonl` 每条记录的 `turn_coverage`；run 目录 `runtime_profile.json` 的 `fork_threshold_tokens`。

**T1 报告项：** 新 oracle "bringup 接线阈值 0"；`rh2.fa.execution_audit.v1` 记录新增可选键 `turn_coverage`（append-only，`schema_id` 不变；若 owner 要求升 v2 则一行改动）。**T2：** 常量与注释。

**不宣称：** 本批不证明目标 GPU 上多行样本的 packing/显存/step 耗时；这些按原定 spike 观测 `training_rows` 与 `input_tokens_total` 的分布再看。

## 7. 对 B 线的影响与接口

- B 的基座诊断不消费训练行；本批对 B 的入口零改动。诊断跑出的 `fa_execution_audit.jsonl` 会多出 `turn_coverage`，正好给出真实 Claude Code 请求下的漂移率与分歧位置分布，是后续判断 C 值不值得做的唯一实测来源。
- 本批期间 A 线独占修改：`adapters/slime/bringup.py`、`turn_identity.py`、`generate.py` 三个文件的上述函数；B 线可继续改其它文件。

## 8. 审查与收口

**2026-09-09 审查结果**（[codex_review.md](codex_review.md)）：B 接线与本机消费接缝通过，无 P0/P1；两项 P2 观测口径问题 R1（共享前缀 FORK 事件重复计数）、R2（末行差额被解释为相对旧阈值的增量）均复现并修复；非阻塞项"orchestrator→audit 运输断言不在维护测试里"一并补入。


一次聚焦独立审查（Codex），范围限本批三个源文件与两个测试文件；修复后只复核对应问题与必要回归。本批完成的判据：§6 命令全过、T1 项已在 `infra.md` 登记、run8 重放数字与 Codex 探针一致。
