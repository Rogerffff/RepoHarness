# W4 实现报告：consume-time staleness 唯一权威接线 / 负 lag 拒绝 / drop 事件 / no-progress / JIT drain

日期：2026-09-04。执行依据：决策包 `miles_spike/decision_package_D2_B.md` v2（owner 已批）B-1 / B-2 / B-4 / B-6；06 计划 §1.5 与 §3 W4 行；前置清理批报告 `wave3_precleanup_report.md`（当前 rh2 形态：finalize-time 阈值门已删，第七维 = 版本事实可用且合法，handshake 阈值只是记录镜像）。本文同时充当本批的 implementation-notes。

工作树状态：**两个仓库都未 commit / 未 stash**。rh2 HEAD = `b007c0d9`；miles 集成分支 `reference/miles-rh2-integration` HEAD = `d66576aea`（patch 0013），本批 miles 侧改动留在工作树供集成者存档为 **patch 0014**。

> 同一集成工作树里 `miles/ray/rollout/rollout_manager.py` 也有未提交改动——那是并行的 W10 agent 的，**不属于本批**；format-patch 0014 时只取 §1 列出的 5 个文件。

## 0. 一句话

miles `DefaultDataBuffer.get()` 现在是 consume-time staleness 的唯一判定点：恰等阈值放行、超阈交 handler（drop）；**负 lag 与 formal 组的版本事实缺失不是 stale，而是 typed run-fatal**；三个丢弃分支 + 被消费 + drain 完成各发一条结构化事件；新增 `--rh2-max-time-without-accepted-group` no-progress 停止规则；`train_async.py` 在 `--fully-async` 下改为 **publish 之后才 drain**（JIT），用真实 rollout fn 的行为测试证明 booked staleness 不再低报一代。

## 1. miles 侧改动清单（供 format-patch 0014；不改训练语义）

| 文件 | 改动的函数 / 符号 | 内容 |
|---|---|---|
| `miles/rollout/fully_async_data_buffer.py` | 新增常量 `RH2_ADMISSION_METADATA_KEY` / `RH2_PROMPT_GROUP_ID_KEY` / `RH2_MEMBER_SLOT_KEY` / `RH2_PHYSICAL_ATTEMPT_ID_KEY`；新增 `_sample_meta()`、`group_claims_formal()`、`group_identity_facts()`；新增异常 `WeightVersionAccountingError(reason_code, …, oldest_weight_version, current_weight_version, group_facts)` | rh2 formal 链 metadata 键的字面量镜像（rh2 侧测试钉死一致）；组身份事实提取；typed fatal |
| 同上 | `DefaultDataBuffer.__init__`：新增 run 级累计计数 `drop_totals`（三分支）与 `consumed_total`；新增只读属性 `staleness_limit` | 不随 `get_metrics()` 窗口复位；供 no-progress fatal 与 `drain_complete` 事件引用 |
| 同上 | `DefaultDataBuffer.put()`：ABORTED 分支与 dynamic filter keep=False 分支改调 `_record_drop(...)` | 分支逻辑、handler 调用、指标计数逐字不变，只是事件字段补齐 |
| 同上 | `DefaultDataBuffer.get()`：staleness 判定改调 `_judge_consume_time_staleness()`；放行分支调 `_record_consumed()`；超阈分支调 `_record_drop(drop_stage=consume_stale, …)` | 放行/超阈/`None` 不过滤三种语义逐字不变；新增负 lag / 版本缺失 fatal |
| 同上 | `_emit_group_filtered()` → 改名 `_record_drop(group, *, drop_stage, reason_code, **facts)`；新增 `_record_consumed()`；新增静态方法 `_judge_consume_time_staleness()`；`_staleness()` 保留为纯算术（`get_metrics` 的 buffer 观测用） | 事件 kind 仍是 `group_filtered`，旧字段 `reason/group_index/instance_id/sample_indices/rewards` 原样保留（G1 collect 兼容） |
| `miles/rollout/fully_async_rollout.py` | 新增 `no_progress_limit_seconds(args)`、异常 `NoProgressTimeout`；`FullyAsyncRolloutFn.__init__` 新增 `_no_progress_limit` / `_progress_anchor`；新增 `_seconds_without_accepted_group()`、`_no_progress_timeout()`；`_next_group()` 的等待超时改为 `min(30s 告警周期, 距期限剩余)` 并在到期抛 `NoProgressTimeout`；`_drain()` 入口与每次接受一组重置计时锚点，末尾发 `drain_complete` 事件 | 生产者/worker/aclose/关停链逐字不变；`return RolloutFnTrainOutput(samples=data, metrics=self._output.get_metrics())` 与 `self._output.get(current_version=current_version)` 两行文本保留（既有源码事实测试锚点） |
| `train_async.py` | `train()` 循环：新增 `jit_drain = bool(args.fully_async)`；JIT 分支在循环顶部 `rollout_data_curr_ref = await rollout_manager.generate.remote(rollout_id)`；stock 预取（循环前 `generate(start)`、循环内 `generate(rollout_id+1)`、publish 前 sync）整体移入 `else` / `if not jit_drain:` 分支 | 只改取批时点；train / save / publish 门控 / eval / finally-dispose 逐字不变 |
| `miles/utils/arguments.py` | **仅新增** `--rh2-max-time-without-accepted-group`（float，默认 None），紧跟 `--custom-async-data-buffer-path` | 不改其它参数（W10 所有） |
| `miles/utils/rh2_event_log.py` | 新增事件 schema 常量与说明：`GROUP_DROP_EVENT="group_filtered"`、`GROUP_CONSUMED_EVENT="group_consumed"`、`DRAIN_COMPLETE_EVENT="drain_complete"`、`DROP_STAGE_PUT_ABORTED/DYNAMIC_FILTER/CONSUME_STALE`、`DROP_STAGES` | `emit()` 本体不变 |

ruff（miles 自身规则 `--config reference/miles-rh2-integration/pyproject.toml`）：5 个文件 All checks passed。W0 旋钮消费者锁（`test_knob_consumer_file_sets_locked`）：`max_weight_staleness` / `dynamic_sampling_filter_path` 字面量仍只在原文件集合里（事件字段因此命名为 `staleness_limit`，见 T1-8）。

## 2. consume-time 判定语义（B-1）

`DefaultDataBuffer.get(current_version)` 弹出一组后调 `_judge_consume_time_staleness(group, current_version)`：

| 事实 | 组声称 formal（任一成员 metadata 带 `rh2_admission`） | 非 formal（s1_compat / mock 链） |
|---|---|---|
| `oldest = min(全组每成员每轮可解析 int 版本)` 为 None（无版本 / 非数值如 `step_0`） | **fatal** `weight_version_facts_missing` | stock：不判定，原样交出 |
| `current_version is None` | **fatal** `current_version_missing` | stock：不判定，原样交出 |
| `current − oldest < 0` | **fatal** `negative_consume_time_staleness` | **fatal**（同左） |
| `0 ≤ staleness ≤ N`（含恰等） | 放行 → `group_consumed` 事件 | 同左 |
| `staleness > N` | `_metric_stale_groups += 1` → `consume_stale` 事件 → `unused_handler_fn(prompt_group)`（`drop` = 本次不回队、不立即重试） | 同左 |
| `N is None` | 不过滤（staleness 仍记录进事件与指标） | 同左 |

**拒绝方式**：`WeightVersionAccountingError` 是 `RuntimeError` 子类，带 `reason_code`（`rh2_shutdown._describe` 会渲染成 `WeightVersionAccountingError(negative_consume_time_staleness): …`）、`oldest_weight_version`、`current_weight_version`、`group_facts`（组身份，不含内容）。它在 owner loop 的 `get()` 里抛出 → `FullyAsyncRolloutFn._drain` → `call_rollout_function`（`run()` 把异常传回调用线程）→ `RolloutManager.generate` 失败 → driver `train_async` 循环异常 → `finally: dispose(driver_cause=serialize_driver_cause(exc))` → rh2 关停链首因 = 本异常（磁盘 `shutdown_report.json.first_cause` 同值）。与 group filter 在 `put()` 内抛 `GroupAdmissionFatal` 走的是同一条关停链，只是入口在消费侧（worker 本身不死，被 `aclose()` 取消，报告 `worker_state=cancelled`）。测试：`test_negative_lag_fatal_surfaces_to_driver_and_becomes_shutdown_first_cause`。

`_staleness()`（纯算术）保留给 `get_metrics()` 的 buffer 观测与既有测试 `test_negative_consume_time_staleness_reproduction_is_closed_at_filter`（那条 filter 侧反例原样通过）。

## 3. drop / consumed / drain 事件 schema（B-2）

emit 统一盖 `event / ts_unix / host / pid / run_id`。全部只取标识，不记 prompt / response / private / patch 内容（测试断言无 `prompt/response/tokens/patch/metadata` 字段）。

**`group_filtered`（三个丢弃分支同一事件名，字段只增不改）**

| 字段 | 来源 | put_aborted | dynamic_filter | consume_stale |
|---|---|---|---|---|
| `drop_stage` | 判定分支 | `put_aborted` | `dynamic_filter` | `consume_stale` |
| `reason_code` / `reason`（旧名，同值） | | `aborted_member` | filter 的 reason（复合 filter：`admission_<code>` / `zero_std_<r>`） | `staleness_exceeded` |
| `group_index` / `sample_indices` / `member_count` / `rewards` | 组事实（`rewards` 不可得为 null） | ✓ | ✓ | ✓ |
| `task_id` / `instance_id` / `prompt_id` / `rh2_prompt_group_id` / `formal` | 首个成员 metadata（分派三键之 task_id、W1a 组身份）；`formal` = 任一成员带 `rh2_admission` | ✓ | ✓ | ✓ |
| `aborted_members` | `[{index, member_slot, physical_attempt_id}]`（`rh2_member_slot` / `rh2_physical_attempt_id`，W1a 铸造） | ✓ | — | — |
| `oldest_weight_version` / `current_weight_version` / `staleness` / `staleness_limit` | 全组最老版本 / 消费时刻已发布版本 / 差 / 生效阈值（`--max-weight-staleness` 的值，None=不过滤） | — | — | ✓ |

**`group_consumed`**（get() 交出一组 = no-progress 的 progress 定义点）：组身份七字段 + `oldest_weight_version` / `current_weight_version` / `staleness`（非 formal 无版本事实时 null）/ `staleness_limit`。

**`drain_complete`**（H5 最小计时事件）：`rollout_id` / `current_weight_version` / `target_groups` / `elapsed_seconds` / `consumed_total` / `drop_totals`（run 级累计快照）。

真实 fa_formal 链（prepared registry → `Rh2MilesGenerateFn` → 真实复合 filter）产出的事件里 `rh2_prompt_group_id="miles_g0"`、`task_id=TID1`、`aborted_members[].physical_attempt_id="miles_g0_m1#p1-…"` 均来自真实铸造：`test_real_formal_chain_events_carry_minted_identity`。

**run 结束汇总**：rh2 侧新模块 `rh2/src/repoharness2/adapters/miles/drop_events.py`（纯 stdlib）：`summarize_group_events(rows, run_id=…)` → `{totals: {attempts, accepted, dropped, dropped_by_stage, dropped_by_reason}, consumed_staleness: {count,min,max,mean,histogram,unknown}, stale_drops: {…, limits_seen}, aborted_members_total, by_task: {task: {attempts, accepted, dropped, dropped_by_stage, drop_ratio}}, rows_skipped: {foreign_run, malformed, unknown_drop_stage}}`；命令行 `python -m repoharness2.adapters.miles.drop_events $MILES_RH2_EVENT_DIR [--run-id R] [--json out]`。分母定义：每个 prompt group 在 buffer 恰有一个终局，`attempts = accepted + dropped`；task 键 = `task_id`，缺则 `instance_id`，再缺 `<unknown>`；W4 之前的旧 emitter 行（无 `drop_stage`）计入 dropped 但记 `unknown_drop_stage`，不静默。

## 4. no-progress（B-2）

参数：`--rh2-max-time-without-accepted-group SEC`（`args.rh2_max_time_without_accepted_group`，float，默认 None = 不启用；≤ 0 在 `FullyAsyncRolloutFn.__init__` 构造时 `ValueError`）。数值归 C。

语义（`NoProgressTimeout`，`reason_code = no_accepted_group_within_limit`）：

- **progress** = `DefaultDataBuffer.get()` 交出一个通过 consume-time 判定的组（`_drain` 里 `_next_group` 返回）。put 拒绝（ABORTED）、filter 拒绝、get 判 stale 的组**都不是** progress——持续完成又持续丢弃不重置计时（测试：v1 组每 20ms 完成一组、消费时刻 v5、N=0 → 全部 consume_stale，0.5s 到期 fatal，`facts.drop_totals.consume_stale ≥ 3`、`consumed_total = 0`）。
- **计时只在 trainer 等待下一组期间累积**：锚点在 `_drain` 入口设置、每接受一组重置、`_drain` 返回时清空；训练 / eval 期间没有人在等组，不计。理由：若从"上一次接受"起跨训练步累计，限值会被训练步时长绑架（训练 10 分钟 > SEC 就误停），而"trainer 在一次 drain 里等了 SEC 仍没拿到可训练组"正是 owner 要抓的"连续无法成 batch"。一次 drain 不接受满 `rollout_batch_size` 组就不会返回，所以这个定义没有绕开的口子。测试：`test_no_progress_clock_resets_on_an_accepted_group`（第一组 0.3s 到达并被接受，之后全 stale，limit 0.6 → 总耗时 ≥ 0.85s、`waited_seconds ≈ 0.6`、`consumed_total = 1`）。
- 到期即抛：异常消息带 `current_weight_version / queue_size / consumed_total / drop_totals / staleness_limit / worker_alive`，一眼区分"producer 死了"（worker 死亡本来就由 `_next_group` 先报）与"producer 在产但全被 drop"。传播路径与 §2 相同（driver 异常 → dispose(driver_cause) → 关停链首因）。
- 未配置时 `_next_group` 行为 = stock（30s 一次告警，永远等）：`test_no_progress_disabled_by_default_keeps_waiting`。

## 5. JIT drain 顺序（B-6"提前 drain 关闭"）

核实：stock `train_async.py` 在循环第 N 轮 `await generate(N)` 后**立即**发起 `generate(N+1)`（batch N+1 在 train(N) 之前开始 drain），publish 前 `rollout_data_curr_ref = (await x) …` 把它 sync 完，再 `update_weights`——于是 batch N+1 的每个组在 `get(current_version=V)` 下判定，却在 V+1 下训练：booked staleness 比 trainer 消费时刻的真实 lag 恰好低一代。

改动：`--fully-async` 下 `jit_drain=True`，循环顶部 `rollout_data_curr_ref = await rollout_manager.generate.remote(rollout_id)`（上一轮 `update_weights` 之后），不再预取、publish 前无 sync；持续 producer（`FullyAsyncRolloutFn` worker）不受影响，只是 trainer 侧取批时点后移。非 fully-async 的 stock 异步 driver 保留一步预取（那条路径的预取就是 rollout/train 重叠本身，见 T1-2）。

证明测试（真实 `FullyAsyncRolloutFn` + 真实 `DefaultDataBuffer` + W5a 的双 loop 生产拓扑替身；`published["v"]` 模拟已发布给 engine 的版本，generate 替身在生成时刻读它作为行为版本）：

- `test_jit_drain_books_true_trainer_consumption_staleness`：JIT 顺序下每批 `booked == published_at_train − oldest`（[0, 1]）；stock 预取顺序下 publish 之后训练的那批 `booked = 0`、真实 lag = 1——低报恰好一代（负对照）。booked 从 `group_consumed` 事件按 `group_index` 取（`get_metrics` 的 `max_staleness` 窗口把被丢弃的 stale 组也计入，不能当被消费组的记账）。
- `test_jit_drain_with_zero_limit_drops_pre_publish_groups_instead_of_training_them`：N=0 下 publish 前生成的组在 publish 后被 `get()` 判 stale（`consume_stale` 事件 oldest=1/current=2），训练的是 v2 的组。
- `test_train_async_jit_drain_source_facts`：钉死 `train_async.py` 文本顺序（`jit_drain = bool(args.fully_async)` → JIT 取批紧跟 `if jit_drain:` → train → publish 前 sync 只在 `if not jit_drain:` → `update_weights`；`generate.remote(` 恰出现 3 次）。

## 6. bringup 接缝（不改 bringup.py，归 W10）

`rh2/src/repoharness2/adapters/slime/bringup.py:920` `_async_start_body(self, args)` 构造 `SlimeBindingConfig(...)` 处加一行：

```python
staleness_threshold=getattr(args, "max_weight_staleness", None),  # W4：consume-time 阈值的记录用镜像（B-1）
```

- 参数名：`SlimeBindingConfig.staleness_threshold: int | None`（前置清理批已改为记录用镜像，gate/admission/filter 都不读）。
- 来源：`args` 就是 miles Namespace（`Rh2MilesGenerateFn` 以 `ensure_fa_started(input.args)` 传入，`input.args = state.args`），`args.max_weight_staleness` = `--max-weight-staleness N`（miles 默认 None）。
- 缺省行为：None → `_build_handshake` 在非 s1 模式写哨兵 `STALENESS_THRESHOLD_MIRROR_UNBOUNDED = 2^31−1` 并在 audit 时间线记 `staleness_threshold_mirror_unconfigured`（前置清理批 T1-2，与 miles "None = 不过滤"一致）；填入 N 后 `BackendHandshake.staleness_threshold = N`、`staleness_within_threshold = finalize_lag ≤ N` 只是 finalize 时刻的观测镜像，真正裁决仍只在 `get()`。
- 不需要新增校验：非法值会在握手构造时被 contracts validator 拒绝（前置清理批 T1-9）。

## 7. CPU materialization benchmark（一次性取数）

`tests/adapters_miles/test_w4_materialization_benchmark.py`（integration_base；环境变量 `RH2_W4_BENCH_RESPONSE_TOKENS / _TURNS / _TOPK / _REPEATS`；`-s` 打印）。真实实现：`parse_turn_sampling_support`（逐轮 sampled∈support 校验）→ `assemble_leaf_sampling_mask`（run↔turn 锚定 + 观察位单例补齐，CSR）→ `canonicalize_sample`（slime→miles：mask 转 `RolloutSamplingMask` 一等字段 + spans 写 metadata + 两本版本账互检）。形状：12 轮，每轮 70% 采样 / 30% 观察 token，top-k=20，轮交替 v5/v6，5 次取中位数（本机 Apple Silicon，CPU 单线程）：

| response tokens | support ids | parse | assemble | canonicalize（含 list→tensor 0.46/0.94/3.69 ms） | 合计 / 叶 |
|---|---|---|---|---|---|
| 4 092 | 58 356 | 2.20 ms | 1.56 ms | 0.68 ms | **4.4 ms** |
| 8 184 | 116 940 | 4.87 ms | 3.22 ms | 1.30 ms | **9.4 ms** |
| 32 760 | 468 240 | 16.97 ms | 13.75 ms | 5.02 ms | **35.7 ms** |

结论：线性，约 1.0–1.1 µs/token；一个 32k token 叶 ≈ 36 ms，一批 32 组 × 2 成员 ≈ 2.3 s 最坏（全 32k），且发生在 producer 侧的 generate 边界（与训练重叠），不在 JIT drain 暴露的 trainer bubble 里。JIT 暴露的是 `get()` 弹出 + `postprocess/convert/DP split/object-store put`（后者本批未量，归 GPU spike H5 计时事件）。只取数，无阈值、无监测。

## 8. T1 决策及理由

1. **T1-1 负 lag fatal 对所有组，版本缺失 fatal 只对 formal 组。** 决策包原文"负 lag/缺失/非法版本 = 版本账目错误（FATAL）"没有 formal 限定；任务书把"缺失"明确限定为"组声称 formal"。负 lag 对任何来源的组都是"行为版本晚于已发布版本"的矛盾，不存在合法解释，故不做豁免；缺失/非数值对 s1_compat（`step_0` 哨兵版本）是既有合法形态，只对声称 formal 的组判矛盾。"声称 formal" = 任一成员 metadata 带 `rh2_admission`（完整 finalize 的 formal 成员必带，admission.py `ADMISSION_METADATA_KEY`），字面量在 miles 侧镜像并由 `test_metadata_key_literals_and_drop_stages_match_rh2_sources` 钉死。
2. **T1-2 JIT 只在 `--fully-async` 下生效。** 非 fully-async 的 `train_async.py` 是 stock 一步异步 driver，它的预取就是 rollout/train 重叠本身——无条件删掉会把上游异步训练改成同步，这不是"只改顺序"。rh2 正式 profile 用 `--fully-async`（FA-1），JIT 覆盖全部正式路径。
3. **T1-3 `current_version=None` 对 formal 组也 fatal（`current_version_missing`）。** 任务书只写"oldest is None 且 formal → 拒绝"；但 trainer 侧没有已发布版本事实时同样无法判定，放行等于把"不过滤"当默认。生产里 `update_weights()` bootstrap 先于第一次 generate，`RolloutManager.weight_version` 不会是 None；本条只堵住"版本事实没接上"的接线错误。
4. **T1-4 no-progress 计时锚定在"等待期"而不是"上一次接受的绝对时刻"。** 理由见 §4。
5. **T1-5 新增 `group_consumed` 与 `drain_complete` 两种事件、`group_filtered` 只增字段。** 没有"被接受"事件就算不出总尝试/接受分母；`drain_complete` 是 H5 要的最小计时面（一次 drain 的 target/耗时/累计计数）。旧字段名 `reason` 保留同值，G1 collect 零改动。
6. **T1-6 buffer 暴露 run 级累计计数 `drop_totals` / `consumed_total` / `staleness_limit`（公开属性）。** `get_metrics()` 的窗口计数每步复位，no-progress fatal 需要"自上次接受以来到底丢了什么"的累计事实；不改 `get_metrics()` 返回面（训练侧日志零改变）。
7. **T1-7 oracle 改动：`tests/adapters_miles/conftest.py::mk_gov_finished_group` 默认行为版本 (7, 7) → (1, 1)。** 治理原型 / W5a 测试用 `current_version=1..6` 消费默认版本 7 的组——旧 stock 把 −6 当"新鲜"放行，W4 起负 lag 是 fatal，fixture 必须自洽；所有测 staleness 过滤的用例都显式传 `versions`，无用例依赖旧默认（全仓搜过）。另：`test_governance_receipts_lifecycle.py::test_train_async_prefetch_true_order_source_facts` 与 `test_two_batch_drain_follows_prefetch_order` 只改 docstring（标注它们钉的是非 fully-async 的 stock 分支 / 账本鲁棒性不变量），断言未动。
8. **T1-8 事件里阈值字段命名 `staleness_limit` 而非 `max_weight_staleness`。** W0 的消费者文件集合锁（`test_knob_consumer_file_sets_locked`）把 `max_weight_staleness` 字面量锁在 `fully_async_data_buffer.py` + `multi_lora/async_rollout.py`；`rh2_event_log.py` / `fully_async_rollout.py` 的 schema 说明与 fatal 消息若写这个字面量就会红它。
9. **T1-9 `--rh2-max-time-without-accepted-group` 用 `getattr` 读取，`≤ 0` 拒绝。** 既有 Namespace 测试面没有该属性 = 未启用；0 会让第一次等待立刻停机，没有合理用途。

## 9. 开放问题 / 接缝

1. **manifest / 树摘要**：`test_g1_acceptance_events.py::test_producer_tree_digest_matches_audit_manifest` 在集成树上红（manifest `miles_source_tree_digest` 仍是 patch 0013 的树），`miles_integration_lanes.sh` 前置校验也会因工作树不干净红——**预期**，随 patch 0014 存档、manifest 更新（expected_tree / tree digest / rh2_patches 表 / expected_counts）一并解除。
2. **同一集成工作树里 W10 的 `rollout_manager.py` 改动**：format-patch 时按 §1 文件清单拆分，勿混进 0014。
3. **no-progress 数值**归 C；建议 GPU spike 起始值 ≥ 单组最长 attempt 上限 + grading 排队上限（否则长任务集会被本规则误停）。
4. **H5 计时事件**：本批只给 `drain_complete` + 逐组 `group_consumed`/`group_filtered`（各带 `ts_unix`、版本）；readiness scope §2.5 列的 dispatch / generation start-end / publish begin-end / postprocess / DP split / object-store 等更细事件未做——留给 GPU spike 需要时再加，不在本批范围。
5. **retry handler 的事件语义**：`--async-unused-samples-handler retry` 时 put_aborted / consume_stale 仍记 `group_filtered`（"本次 physical group 不训练"），prompt 被回收另起新组——首训固定 `drop`（B-2），若日后启用 retry 需在汇总里区分"回收"与"丢弃"。
6. **非 fully-async 的 `train_async.py` 仍预取**（T1-2）；若将来有非 fully-async 的 rh2 路径需要 consume-time 判定，须另行决定。
7. **rh2 默认 lane 的 2 个红**（`tests/adapters/test_w3a_formal_grading_freeze.py`、`tests/contracts/test_f2_2b_b3_hygiene.py`）来自并行 W3a 的进行中改动（grading/generate.py），与本批无关；本批实跑期间 `grading/manager.py` 曾短暂 import 失败（`field` 未导入），后由该 agent 修复。

## 10. 测试证据（2026-09-04 实跑；rh2 工作树 = `b007c0d9` + 本批 + 并行 W3a/W10 未提交改动）

新增 rh2 测试（全部通过，43 例）：

| 文件 | 例数 | lane | 覆盖 |
|---|---|---|---|
| `tests/adapters_miles/test_w4_consume_time_staleness.py` | 37 | B（integration_base） | 参数化 N=0/1/2/4 恰等放行/超阈交 handler + 事件；负 lag fatal（formal / 非 formal × N）；版本缺失 fatal（`[]`/`step_0`/`v5`）；current 缺失 fatal；非 formal stock 行为；跨版本多轮多 member 取全组最小；None 不过滤；三分支事件字段齐全 + 按 task 分母；事件目录未设时只计数；真实 fa_formal 链事件身份；fatal 经 driver → dispose 首因（含磁盘报告）；no-progress 三例 + 参数校验 + 默认关闭；drain_complete；JIT vs stock 行为模型两例；train_async 源码事实；字面量镜像钉死 |
| `tests/adapters_miles/test_w4_drop_event_summary.py` | 5 | A+B | 聚合 totals / by_task / 回退键 / run_id 过滤与旧行计数 / bool 不算数 / CLI |
| `tests/adapters_miles/test_w4_materialization_benchmark.py` | 1 | B | §7 取数（产物合法性断言，无阈值） |

命令与计数：

```
cd rh2
uv run pytest tests/ -q                                   # 1606 passed, 292 skipped, 2 failed（两红均为并行 W3a 文件，见 §9-7）
uv run pytest tests/adapters_miles/ -q                    # lane A: 339 passed, 277 skipped（-m "not integration_base" 零 skip）
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q
                                                          # lane B: 615 passed, 1 failed（唯一红 = 树摘要 vs manifest，预期，见 §9-1）
uv run ruff check src/repoharness2 tests                  # All checks passed
uv run ruff check --config ../reference/miles-rh2-integration/pyproject.toml <5 个 miles 改动文件>   # All checks passed
```

本批相对基线（lane A 322/232、lane B 554/0，本批开工前实跑 lane B = 554 passed 确认）的**自身**增量：lane A **+5 passed / +38 skipped**（37 + 1 integration_base 例在 pin 树豁免）；lane B **+43 passed**。lane 现值里其余差额（A +12 passed / +7 skipped，B +19）来自并行 W10 新增的 `test_w10_multi_engine.py` 与删除的 `test_bringup_weight_version_probe.py`，不属本批。`test_w1b_group_admission.py` 38 例（含 filter 侧负 lag 反例）、W5a 关停链 15 例、W0 旋钮锁、治理原型两文件在本批改动后全绿。

## 11. 协作协议五段收尾

**① 待拍板 T0**：无新增。未触碰 contracts/、rh2/src/slime、bringup.py / generate.py / grading/*、`rollout_manager.py` / router / `arguments.py` 其它部分。

**② T1 决策及理由**：§8 T1-1 ~ T1-9。请 owner 特别知悉 T1-1（负 lag 对非 formal 组也 fatal）与 T1-2（JIT 只在 `--fully-async` 生效）。

**③ 临时挡板新增/命中/解除**：无新增；`bringup.py:705-713` fa_formal 挡板未触碰（其解除条件"W1b+W3a+W3b+W4"中 W4 项——consume-time 权威与 publish→drain 顺序——本批闭合，解除动作归集成者）。

**④ 推翻或修正了哪些旧结论**：
- `test_train_async_prefetch_true_order_source_facts` 的"train_async 真顺序 = 预取先于训练、publish 前 sync"——现只对非 fully-async 分支成立；fully-async 为 JIT。
- 06 计划 W1b 行"consume-time 由 buffer.get() 复查（归 W4）"与附录 A"consume-time 超龄由 buffer.get()→handler"——已落地；超龄 = handler（drop），负 lag/缺失 = fatal，不是 DROP。
- stock miles 注释"groups exceeding this threshold are recycled back to the data buffer"（`--max-weight-staleness` help）——在 `drop` handler 下不回收；本批未改 help 文本（W10 所有），建议集成时顺手改。

**⑤ 测试/证据/账本状态**：§10；manifest 与 spike-log 由集成者随 patch 0014 落账（expected_counts 本批自身增量见 §10；需同时计入 W10 增量）。

**本轮没有改变哪些已定案语义**：`contracts/` 全部 schema（`BackendHandshake` 阈值记录字段与 validator 原样）；W1b 复合 group filter 的身份/分派/termination/fan-out/版本绑定对账与零方差过滤（filter 侧负 lag 反例原样通过）；第七维"版本事实可用且合法"；`DispositionPolicy` fail-fast；W5a 关停链（aclose 顺序、首因/次生/同源去重、`ShutdownFailure`）；G1 `group_filtered` 旧字段；faithful DIS loss；B-4 `update_weights_interval=1`；`--async-unused-samples-handler drop` 的"不回队、不立即重试"；s1_compat 交付形状与握手记录；`miles/ray/rollout/rollout_manager.py`、router、`arguments.py` 其它参数、bringup.py、generate.py、grading/*、rh2/src/slime、reference/ 其它文件、lanes manifest 与 patch 表。
