# I20 首版实施 Brief：离线 run 报告工具（七面基础摘要，只消费已有记录）

日期：2026-09-10。作者：Claude（A 线）。依据：[第三组决策包 §0 / §0.1 第 4 条](README.md)、[讨论补充 §4](i19_i20_discussion_20260910.md)。状态：**Brief 发出即实施；T1（纯消费者，不改任何 producer 的语义，不改 loss / 准入 / 处置）。** I18 路由度量不实施；第四组评分语义独立讨论，本工具只消费已有评分事实并保留未知与分类来源。

## 1. 交付物

`rh2/src/repoharness2/adapters/miles/run_report.py`（CLI：`python -m repoharness2.adapters.miles.run_report <run_dir_or_files>... [--run-id ID] [--json out]`）：读取一个 run 的既有文件，输出一份 JSON 报告（七面各一段 + 顶层 `coverage`：每面标 `collected` / `partial` / `not_collected` 及原因）。可对**进行中**的 run 快照运行（不要求正常退出、不常驻、不轮询）。复用既有汇总器（`drop_events.summarize_group_events` / `summarize_attempt_costs`），不新建成本账本。

## 2. 七面 → 现有 producer 映射（首版只读这些；缺口如实标注）

| 面 | 输入文件 / 事件 | 启用条件与关联键 | 首版输出 | 缺口（标 not_collected，本版不补 producer） |
|---|---|---|---|---|
| ① 执行、丢组与损耗 | `rh2_events_*.jsonl` 的 `group_filtered` / `group_consumed` / `drain_complete` / `attempt_cost_snapshot` / `grading_regrade`；`fa_execution_audit.jsonl`（disposition、failure_records、termination） | 事件需 `MILES_RH2_EVENT_DIR`（未设 = 无事件，报 not_collected，**不能显示为"没有损耗"**）；组键 (run_id, rh2_prompt_group_id)，成员键 (run_id, physical_attempt_id) | 组终局计数（按原因 / task）、成员成本分布、整组连带成本（按根因集合）、重评分次数 / 结果；audit 侧 disposition 与终止原因分布 | "发起 / 在飞"分母：audit 只覆盖已结束 attempt；进行中的长任务单列为 `audit_missing`（不推造） |
| ② 动作覆盖与表示成本 | audit `turn_coverage`（captured / unique trainable / rows / input tokens）、`context_shrink_reasons`（会话级线索） | 每 attempt 一条 | 覆盖率、行数、`input_tokens_total` 与 `input_tokens_excluding_last_row`（分别列，不相减冒充阈值成本）、FORK 行数、上下文长度下降线索计数（**不称压缩次数**） | 摘要来源 / 主子分支细分：无明确证据不细分 |
| ③ reward、优势与分布 | audit `grading`（outcome / failure_category / reward）；`rollout_group` 事件（rewards、behavior_versions）；`group_filtered` 的 zero_std / admission 原因 | audit + 事件；按 task / 长度（turn_coverage 行长）切片 | 有可信评分成员的 reward 分布；全 0 / 全 1 / 零方差组占比；评分后 vs 过滤后 vs 实际消费（`group_consumed`）三个分布分开 | 优势值本身在 trainer 内部（不导出）：报"优势符号分布"仅当 rewards 与组均值可算时按组内 reward−mean 近似并**标注为近似** |
| ④ DIS 与支持集（I17） | `train_step` 事件的 `loss_reduced`（含 `dis_*` 十五项，**已 ÷ num_rollouts**）+ 同事件 `num_rollouts`；`sample_dis_accounting`（accepted / provenance，按 sample+leaf） | 事件 dir；按 (rollout_id, step_id) | 每 step 原始总量 = 均值 × num_rollouts（跨 step 比例用总量之和）；accepted 三分（单例 / 零优势 / 候选信号）、两侧拒绝、支持集桶；跨 rank 只取 `is_pp_last_stage` 且 dp_rank=0 的一份 | 有界 log-ratio 分布：当前无 producer，not_collected；`sample_dis_accounting` 不补造候选信号 |
| ⑤ 陈旧度与训推对齐 | `group_consumed` / `consume_stale`（oldest / current / staleness / limit）；`rollout_group`（behavior_versions、weight_version_spans）；`logprob_compare`（同版本标记、动作数、平均绝对差、长度错配） | 事件 dir；按 rollout_id | 消费时版本差分布、等待比例、多版本动作比例；同版本 logprob 差异单列（可比动作数、无可比样本时显示"无"）；跨版本差异单列 | 按陈旧度关联拒绝 / 候选信号：需要 step↔组的映射（`train_step_consumed.sample_indices` ↔ `rollout_group.sample_indices`），首版只在两者都在场时做，否则 partial |
| ⑥ 优化器与权重发布 | `train_step`（outcome、optimizer_step_applied、adam / scheduler 前后、grad_norm、duration）、`train_step_consumed`（sample_indices / leaf）、`weight_update`（version_before/after、duration）、`engine_versions_after_publish`、`run_restarted` | 事件 dir；按 rollout_id / step_id | 尝试 / 应用 / 跳过 step 计数与连续零信号；发布版本序列与耗时；引擎版本收敛；每 step 实际消费的行与 execution 数 | 学习率：只在事件里有时报；无则 not_collected |
| ⑦ 吞吐、排队与资源 | audit `timing_summary` / `lifecycle_timing`（19 段：sandbox 五段、census、capture、persist、grading 排队 / 启动 / 重建 / 测试 / 清理、hold）、`episode_deadline`、`model_call_attempts`；`drain_complete`（elapsed、target_groups）；`grading_regrade`；`train_step.duration_seconds`、`weight_update.duration_seconds` | audit + 事件 | 各段 p50 / p95（重叠段分开列，不拼饼图）；组装批耗时；生成 token / attempt 与训练消费动作 / step 的粗吞吐；成员 elapsed 之和**不称** run 墙钟 | GPU / 显存 / 缓存与 Docker 资源指标：现有 logger 不在本工具输入内，not_collected |

## 3. 统计口径（验收 oracle）

1. 单位分开：组、成员执行、训练行、token、optimizer step 各自计数；FORK 三行不算三题；跨 run 键含 run_id。
2. 保留原始和、数量与未知数量；`train_step` 指标均值 × `num_rollouts` 还原总量，跨 step 比例 = 总量之和 / 分母之和；多 rank 副本只取一份。
3. "发起""已终结""已被 buffer 取走""参与 applied step"分开；缺失记录 / 未匹配 / 未知版本不记 0；进行中 attempt 单列。
4. token 成本与计算成本分开；重叠阶段单独展示。
5. 观测与解释分开：会话级长度下降 ≠ 压缩次数；同版本差异不直接归因 MoE；不把跨版本 log-ratio 叫 KL。
6. 只诊断不处置：工具不重采样、不改预算、不改准入。

## 4. 测试与验收

`tests/adapters_miles/test_run_report.py`（双 lane，合成行 + 真实汇总器）：无事件目录 → 面①④⑤⑥ not_collected 且不显示零损耗；两 run 同名组不混连；FORK 三行一题；`train_step` 均值 × num_rollouts 还原、两 step 比例按总量；多 rank 副本去重；进行中 attempt（audit 缺）单列；无可比同版本样本显示"无"。`ruff check src tests`、全量 `pytest tests -q`、lanes 计数同步。不运行 GPU；开销与真实缺失比例随原定 GPU 作业测。

## 5. 不做

不新增 producer、设备侧统计、告警阈值、常驻服务；不接路由一致率；不改 reward / loss / 准入 / 处置；不重写 `drop_events.py` 已有汇总，只调用。
