# W5b 实现报告 · 最小冷恢复合同（决策包 D2+B v2 B-3）

日期：2026-09-04。执行依据：`miles_spike/decision_package_D2_B.md` v2 B-3（owner 2026-09-04 细化："不建设联合 checkpoint、事务恢复或复合版本体系"）、06 计划 §1.5（W5b 行原文作废，以 B-3 为准）。工作树：rh2 HEAD `025c4b9a`（未 commit / 未 stash）；miles integration tree `reference/miles-rh2-integration` HEAD `c97d8c201`（patch 0015 已存档），工作树改动**未 commit**（待集成者存档为 patch 0016，清单见 §6）。本文同时充当本工作包的 implementation-notes。

一句话：**三个正确性点全部落在 miles 侧、rh2 侧零源码改动。已核实 miles 从未保存"已发布版本"——现在 `RolloutManager.save(rollout_id)` 在写 data_source 游标的同一次调用里把当时已发布给 engine 的版本 p 写成一个小 JSON（同目录、同 rollout_id），重启时 trainer 每个 rank 把 updater 计数器恢复为 p-1（bootstrap publish 标 p、首次真实更新 p+1），RolloutManager 要求本 run 首次 `set_weight_version` 恰为 p；恢复语境下 data_source 状态缺失改为 typed 报错；恢复成功发一条 `run_restarted` 事件。33 例本地测试全绿（含真实 `RolloutManager.save/load/set_weight_version` 方法体与真实 `RolloutDataSource`）。**

---

## 0. 交付物一览

| 文件 | 性质 | 内容 |
|---|---|---|
| miles `miles/utils/rh2_recovery.py` | **新增**（integration tree 工作树，309 行） | 合同的全部实现：`RecoveryStateMissing` / `RecoveryVersionMismatch` 两个 typed 异常；`is_recovery_context`；状态文件路径、原子写 `save_published_weight_version`、校验读 `load_published_weight_version`；`initial_updater_weight_version`（p→p-1）；`resolve_restore_rollout_id` + `restore_updater_weight_version`（trainer 侧）；`check_first_publish_after_restore`、`save_rollout_state`、`restore_rollout_state`（RolloutManager 侧，含 `run_restarted` 事件） |
| miles `miles/utils/rh2_event_log.py` | 修改（+16） | 事件常量 `RUN_RESTARTED_EVENT = "run_restarted"` 与字段说明块 |
| miles `miles/rollout/data_source.py` | 修改（+12） | `RolloutDataSource.load`：恢复语境下状态文件缺失 → `RecoveryStateMissing`；全新 run 原静默路径不变 |
| miles `miles/ray/rollout/rollout_manager.py` | 修改（+21/−4） | `__init__` 新字段 `_rh2_restored_published_weight_version`；`save` → `rh2_recovery.save_rollout_state`；`load` → `rh2_recovery.restore_rollout_state`；`set_weight_version` 首次 publish 恢复核对（在 W10 单调断言与逐 engine 收敛核对之前） |
| miles `miles/backends/megatron_utils/actor.py` | 修改（+8/−1） | updater 唯一构造点之后：`self.weight_updater.weight_version = rh2_recovery.restore_updater_weight_version(self.args, loaded_rollout_id)` |
| miles `miles/backends/fsdp_utils/actor.py` | 修改（+5/−1） | 同上，放在 `checkpoint.finalize_load` 之后（FSDP 的 `start_rollout_id` 到那时才定） |
| `rh2/tests/adapters_miles/test_w5b_cold_recovery.py` | **新增** | 13 个测试函数 / 33 例（全部 `integration_base` 标记，只在 lane B 跑），见 §5 |
| 本文 | **新增** | 报告 + implementation-notes |

**未触碰**：rh2 的 `bringup.py` / `generate.py` / `grading/*` / `governance/*` / `envpack/*` / `contracts/` / `rh2/src/slime`（W3b 并行所有权与禁改清单）；miles 的 `fully_async_data_buffer.py` / `fully_async_rollout.py`（W4 刚落地，恢复不需要触碰——buffer 在新进程里天然是空的，没有任何持久化面）、`train_async.py`（bootstrap publish 与 save→rollout_manager.save→update_weights 的既有顺序正是本合同依赖的事实，不需要改）、`miles/utils/arguments.py`（**没有新增任何参数**：恢复语境完全由既有 `--load` / `start_rollout_id` 推出）、`placement_group.py`、两个 updater 文件 `update_weight_from_tensor.py` / `update_weight_from_rdt.py`（`weight_version = 0` 行原样保留，见 T1-1）。

---

## 1. 三个正确性点的落点

### ① updater 版本计数从恢复点继续

| 落点 | 内容 |
|---|---|
| `miles/backends/megatron_utils/actor.py::MegatronTrainRayActor.init`（`self.weight_updater = update_weight_cls(...)` 之后，行 285-291） | `self.weight_updater.weight_version = rh2_recovery.restore_updater_weight_version(self.args, loaded_rollout_id)`。`loaded_rollout_id` 就是同函数里 `initialize_model_and_optimizer` 返回、用来算 `start_rollout_id = loaded_rollout_id + 1` 的 Megatron 迭代号（miles 里 iteration == rollout_id） |
| `miles/backends/fsdp_utils/actor.py::FSDPTrainRayActor.init`（`checkpoint.finalize_load(...)` 之后，行 210-213） | 同一调用，`loaded_rollout_id=None`——FSDP 的 `args.start_rollout_id` 由 `finalize_load` 从 `meta.json` 的 `next_rollout_id` 设定，`resolve_restore_rollout_id` 取 `start_rollout_id - 1` |
| `miles/utils/rh2_recovery.py::restore_updater_weight_version` | 非恢复语境返回 0（stock）；恢复语境读 `<load>/rollout/rh2_published_weight_version_<rollout_id>.json` → `initial_updater_weight_version(p) = p - 1`；文件缺失/损坏 → `RecoveryStateMissing`（每个 rank 在 `init()` 里抛 → `create_training_models` 的 `asyncio.gather` 传到 driver → 走 W5a 关停链，run 在任何 publish 之前停止） |
| `miles/utils/rh2_recovery.py::resolve_restore_rollout_id` | 镜像 `placement_group.create_training_models` 的公式：`start_rollout_id` = 用户显式值，否则 `loaded_rollout_id + 1`；随后 `RolloutManager.load(start_rollout_id - 1)`。trainer 与 RolloutManager 由此对同一个 rollout_id 取状态文件 |
| `miles/ray/rollout/rollout_manager.py::RolloutManager.set_weight_version`（行 565-570） | 本 run 首次 publish（`self.weight_version is None`）时 `rh2_recovery.check_first_publish_after_restore(self._rh2_restored_published_weight_version, weight_version)`：恢复点记录了 p 就必须恰等于 p，否则 `RecoveryVersionMismatch`（经 trainer 的 `ray.get` 传播，run 停止）。位置在 W10 的"版本回退"断言与 `_verify_engine_weight_versions` 之前，所以不一致时不会先去问 engine |

为什么是 p-1（06 计划 codex 终核修正的 off-by-one）：六个 updater（`update_weight_from_tensor.py:103`、`update_weight_from_rdt.py:111`、`update_weight_from_distributed/{p2p.py:61, broadcast.py:44, delta.py:56}`、`fsdp_utils/update_weight_utils.py:58`）构造时都是 `weight_version = 0`，`update_weights()` 都先 `+= 1` 再把 `str(weight_version)` 发给 engine（`mixin.py:358→326`、`update_weight_from_tensor.py:241→374`、`delta.py:114→158`、`fsdp:71→119`）；`train_async.py:82` 启动即 `await actor_model.update_weights()`。计数器恢复为 p-1 ⇒ bootstrap publish 标 p、首次真实更新 p+1；`set_weight_version` 的单调断言（None→p→p+1）与 W10 逐 engine 收敛核对（engine 报 "p"）都不被破坏。测试 `test_updater_and_wiring_source_facts` 把六个构造点与增量顺序钉死在真实源码上。

### ② data_source 状态缺失显式报错

`miles/rollout/data_source.py::RolloutDataSource.load`（行 148-161）：`if not os.path.exists(path)` 分支内，`rh2_recovery.is_recovery_context(self.args, rollout_id)` 为真（有 `--load` 且 `rollout_id >= 0`）→ `raise RecoveryStateMissing(kind="data_source_state", path, rollout_id, load_dir)`；否则保留原 `logger.info(...)` + `return`。`RolloutDataSourceWithBuffer` 继承同一方法。异常消息给出文件路径、rollout_id、`--load` 目录，并说明"想从这些权重全新开训请走 `--ref-load`"。

### ③ 重启记录

`miles/utils/rh2_recovery.py::restore_rollout_state`（由 `RolloutManager.load` 调用）：`data_source.load(rollout_id)` → 恢复语境下读版本文件（缺失同样 typed 报错）→ `rh2_event_log.emit("run_restarted", ...)`。字段：`rollout_id`（恢复自哪个 checkpoint 迭代）、`start_rollout_id`（= rollout_id + 1）、`load_dir`、`published_weight_version`（p）、`bootstrap_weight_version`（= p）、`previous_run_id`（写状态文件的旧 run 的 `MILES_RH2_RUN_ID`）、`published_version_state_path`、`data_source_state_path`、`data_source_state_present`、`data_source_state`（恢复后的游标四元组）；新 run_id 由 `emit()` 从 `MILES_RH2_RUN_ID` 盖章（`run_id` 字段），`ts_unix/host/pid` 同其它事件。全新 run 不发。rh2 侧不建新模块（judge 暂不消费，见开放问题 3）。

## 2. "已发布版本"的保存 / 恢复来源（核实结论）

**核实：miles 里没有任何地方保存已发布版本。** `RolloutManager.save(rollout_id)` 只做 `data_source.save(rollout_id)`（`sample_offset/epoch_id/sample_group_index/sample_index/metadata` → `<save>/rollout/global_dataset_state_dict_<rollout_id>.pt`）与 `event_logger_checkpoint.snapshot`（审计事件目录快照）；Megatron checkpoint 保存 model/optimizer/scheduler/RNG/iteration/args，不含 updater 计数器；`RolloutManager.weight_version` 是纯内存字段。"从恢复的 rollout_id 推导"不可靠：F2 的 `weights_dirty` 门控会跳过零信号 step 的 publish（`weight_publish_skipped`），版本号与 rollout_id 之间没有固定算术关系。

**因此新增最小状态**：`<save>/rollout/rh2_published_weight_version_<rollout_id>.json`（schema `rh2.published_weight_version_state.v1`：`rollout_id`、`published_weight_version`（int 或 null）、`run_id`、`saved_at_unix`、`host`、`pid`），由 `rh2_recovery.save_rollout_state` 在 `RolloutManager.save` 里紧随 `data_source.save` 之后写（tmp + fsync + `os.replace` 原子写；只要有 `--save` 就写，不受 `rollout_global_dataset` 限制）。这是"保存一个整数"，不是联合 checkpoint：与 Megatron checkpoint、data_source 状态之间没有事务（见 §4）。

**p 的精确定义**：`RolloutManager.weight_version`，即 trainer 上一次 publish 后经 `set_weight_version` 告知 rollout 侧的版本。`train_async.py` 循环顺序是 `save_model(rollout_id)`（行 161）→ `rollout_manager.save(rollout_id)`（行 164）→ `update_weights(rollout_id)`（行 182），所以 p 是 rollout_id **之前**那次 publish 的版本；checkpoint 里的权重（rollout_id 训练后）保存时尚未发布。重启后 bootstrap 把这份权重按 p 重发——这正是 B-3 原文"bootstrap 重发 checkpoint 权重"的含义。`published_weight_version = null` 只在恢复点之前从未 publish 时出现（`debug_train_only` / `debug_skip_weight_update`），此时 updater 保持 0、首次 publish 不做恢复核对（测试 `test_recovery_with_no_publish_before_checkpoint_keeps_stock_start`）。

**恢复语境的唯一定义**（`is_recovery_context`）：有 `--load` 且 `rollout_id >= 0`。依据是 arguments.py 既有分类：`--load` 下没有 `latest_checkpointed_iteration.txt` ⇒ `start_rollout_id = 0`（并把 `args.load` 改指 `ref_load`/hf 权重），`placement_group` 于是 `RolloutManager.load(-1)`；有 tracker ⇒ `start_rollout_id` 留 None，由 trainer 实际加载的迭代 k 得 `k + 1`，`load(k)`。用户显式 `--start-rollout-id N>0` 也算恢复（两侧同键 N-1）；显式 0 + 有 checkpoint = "权重续用、游标与版本从头"，按全新 run 处理（与 stock `load(-1)` 一致）。

## 3. 完整冷恢复时序（生产路径逐步对应）

```
原 run（run_id A）：... publish → p ；rollout r：JIT drain@p → train → save_model(r)
      → RolloutManager.save(r)：global_dataset_state_dict_r.pt + rh2_published_weight_version_r.json{p, run_id=A}
      → update_weights → p+1 → ... → 崩溃（buffer/在飞组丢失）
重启（run_id B，--load 指向同一 ckpt 目录）：
  arguments.py：tracker 在 → start_rollout_id=None
  actor.init（每 rank）：Megatron 加载 iter r → 构造 updater(0) → restore_updater_weight_version → p-1
  create_training_models：start_rollout_id = r+1 → RolloutManager.load(r)：游标恢复；版本文件 p；emit run_restarted{run_id=B, previous_run_id=A}
  train_async：bootstrap update_weights → engines 标 "p" → set_weight_version(p)：恢复核对 ✓ → 单调 ✓ → 逐 engine 收敛 ✓
  循环从 rollout_id = r+1 开始：drain@p（buffer 全新为空）→ train → publish p+1
```

## 4. 接受的残余（B-3 原文 + 实现细节）

1. **checkpoint 点与"最后发布版本"之间崩溃**：重启后 bootstrap 按 p 重发 checkpoint 权重；pre-crash 的 p+1、p+2… 号在新 run 里被不同权重复用。因为 buffer 与在飞组已全部丢弃（buffer 无持久化面：`fully_async_data_buffer.py` / `fully_async_rollout.py` 无任何 `torch.save/load`，源码事实测试钉死），没有 pre-crash 样本会拿这些号与新样本比较，对训练正确性无影响，只损失 checkpoint 点之后的样本。checkpoint 频率与可接受损失窗口归 C。
2. **两次写之间崩溃**（`data_source.save` 成功、版本 JSON 未写）：重启时 trainer 先于 RolloutManager 报 `RecoveryStateMissing(published_weight_version_state)`，run 不启动；处置 = 回退到更早一个 `save_interval` 点或按 §2 规则全新开训。不做 joint commit。
3. **版本号跨 run 不唯一**：不做 `(segment_id, numeric_version)` 复合身份；跨 run 的证据对账靠事件里的 `run_id` / `previous_run_id`。
4. **FSDP 路径**只做了同款接线 + 源码事实，未在 GPU 上验证（首训 profile 是 Megatron）。

## 5. 测试（`rh2/tests/adapters_miles/test_w5b_cold_recovery.py`，33 例，全部 `integration_base`）

被测对象全部是集成分支真实对象：`rh2_recovery` 全部函数；真实 `RolloutDataSource.save/load`（`__new__` 绕过 `__init__` 的 tokenizer/Dataset 加载，只装配状态字段）；真实 `RolloutManager.save / load / set_weight_version / _verify_engine_weight_versions` **方法体**（RolloutManager 是 Ray actor，sglang/ray import 链在 rh2 venv 不可导——用 ast 从生产源码抽出这四个方法编译后绑定到最小替身执行，与 `test_zero_signal_semantics` 抽 `_any_weights_dirty` 同一手法）；真实 `DefaultDataBuffer`、真实 `verify_engine_weight_versions`（W10）+ W10 同款 fake actor handle。updater 用"构造 0、publish 前 +1、把 str(version) 发给每台 engine"的最小替身，两条事实由源码事实测试钉死。

| 合同条目 | 测试 | 断言要点 |
|---|---|---|
| 完整冷恢复 | `test_full_cold_recovery_continues_version_from_saved_point` | 原 run publish 到 p=7、`save(3)` 只写两个文件（同目录同 rollout_id，无 .tmp、无 buffer 内容）、JSON 字段含 `run_id="w5b-run-1"`；原 run 再 publish 到 9 后"崩溃"；重启：`restore_updater_weight_version` → 6、`RolloutManager.load(3)` 游标恢复 == 保存值、`_rh2_restored_published_weight_version == 7`、`weight_version is None`、新 `DefaultDataBuffer` 队列为空；bootstrap publish 标 "7" 到两台 engine，`set_weight_version(7)` 过恢复核对 + 逐 engine 核对（各问一次）；首次真实更新 → 8；`run_restarted` 恰一条：`run_id="w5b-run-2"`、`previous_run_id="w5b-run-1"`、rollout_id/start_rollout_id/load_dir/p/bootstrap/两个路径/游标齐全；新 run 的 `engine_versions_after_publish` = [("7",True),("8",True)] |
| 恢复点之前从未 publish | `test_recovery_with_no_publish_before_checkpoint_keeps_stock_start` | 文件记 null → updater 0 → 首次 publish 1 不做恢复核对；事件里 p/bootstrap 为 null |
| 状态缺失（恢复语境）→ typed | `test_missing_state_file_in_recovery_context_is_a_typed_error` | `ds.load(3)` → `RecoveryStateMissing`（`RuntimeError` 子类，kind/rollout_id/load_dir/path 齐、消息含 `--ref-load` 指引，游标未动）；data_source 状态在而版本文件缺 → `restore_rollout_state` 与 `restore_updater_weight_version` 都报 kind=`published_weight_version_state`；失败路径不发 `run_restarted`；真实 `RolloutManager.load` 方法体同路 |
| 全新 run 无状态文件 → 正常 | `test_fresh_run_without_state_files_is_normal` | `load(-1)` / `load(None)` 静默、游标为零；`restore_updater_weight_version(start_rollout_id=0, loaded=0)` == 0（Megatron finetune 返回 iteration 0 也不算恢复）；`restore_rollout_state(-1)` 返回 None 且无事件；无 `--load` / 非 global dataset 的 stock 静默路径原样 |
| 恢复语境判定 | `test_recovery_context_predicate[5]`、`test_restore_rollout_id_mirrors_placement_group_formula[6]` | 无 load / -1 / None → False；0、5 → True；`start_rollout_id` None→loaded、0→-1、显式 5→4 |
| 首次 publish 核对 vs W10 | `test_first_publish_after_restore_must_carry_restored_version` | 恢复点 7、未恢复的 updater bootstrap 标 1 → `RecoveryVersionMismatch(restored=7, published=1)`，`weight_version` 仍 None、engine 零次被问（恢复核对先于一切）；恢复后一台 engine 漏 publish → W10 `EngineWeightVersionMismatch` 照常；通过后第二次 publish 只受单调断言约束（回退 → AssertionError） |
| | `test_check_first_publish_after_restore_table[6]` | None 不核对；7/7 过；7 对 8、6、1 都拒 |
| 恢复值 | `test_initial_updater_weight_version[4]`、`..._rejects_impossible_values[4]` | None→0、1→0、7→6；0 / 负数 / bool / 字符串 → ValueError |
| 状态文件 | `test_published_version_state_file_roundtrip_and_validation`、`test_save_rollout_state_without_save_dir_writes_nothing` | 路径、原子写无 .tmp、字段、`required=False` 缺失 → None、版本 0 不可写、损坏 JSON / rollout_id 不匹配 / schema 漂移 → typed（detail 非空）；无 `--save` 不写返回 None |
| 源码事实 | `test_updater_and_wiring_source_facts` | 六个 updater `weight_version = 0`；tensor/mixin/delta/fsdp 的 `+= 1` 先于把版本发给 engine；两个 actor 在唯一构造点之后恢复；`placement_group`：`actor_model.init()` → `start_rollout_id` → `load(start_rollout_id - 1)`；`train_async`：bootstrap publish 在循环前、`save_model → rollout_manager.save → update_weights`；RolloutManager 接线与 `set_weight_version` 内顺序（`if self.weight_version is None` → 恢复核对 → 回退断言 → 记录 → 收敛核对）；data_source 分支顺序与路径字面量镜像；buffer 两文件无 torch.save/load；arguments.py 全新 run 分类 |

## 6. miles 侧改动清单（供 `git format-patch` 存档为 patch 0016）

integration tree `reference/miles-rh2-integration`（HEAD `c97d8c201`）工作树，**未 commit**，`git status --short`：

| 文件 | 改动 |
|---|---|
| `miles/utils/rh2_recovery.py` | **新增** 309 行（模块说明含合同全文与 p 的定义；14 个符号见 §0） |
| `miles/utils/rh2_event_log.py` | +16：`RUN_RESTARTED_EVENT` 常量与字段说明块（行 82-96） |
| `miles/rollout/data_source.py` | +12：`from miles.utils import rh2_recovery`；`load` 的缺文件分支加恢复语境 typed 报错（行 149-159） |
| `miles/ray/rollout/rollout_manager.py` | +21/−4：import；`__init__` 新字段（行 71-73）；`save`/`load` 改为委托 `rh2_recovery.save_rollout_state` / `restore_rollout_state`（行 446-459）；`set_weight_version` 首次 publish 恢复核对（行 565-570） |
| `miles/backends/megatron_utils/actor.py` | +8/−1：import；构造点之后恢复计数器（行 285-291） |
| `miles/backends/fsdp_utils/actor.py` | +5/−1：import；`finalize_load` 之后恢复计数器（行 210-213） |

本批的工作树里没有其它未提交改动（W4/W10 已分别存档为 0014/0015），可整树 `git add -A miles/`。建议 commit message：`[rh2-integration] W5b: minimal cold-recovery contract -- restore updater weight version from the checkpoint's published version, typed error on missing rollout state, run_restarted event (patch 0016)`。ruff（miles pyproject 配置）六文件全过。全部源码改动经"old 片段恰好出现一次"的替换脚本落地（review-standards §7）。

manifest 更新建议（由集成者随 0016 存档）：`expected_tree` / `miles_source_tree_digest` / 新表 `rh2_patches_w5b` / `expected_counts`：lane A `339 passed / 277 → 310 skipped`，lane B `616 → 649 passed / 0 skipped`（+33 全部 `integration_base`，lane A 记 skip）。

## 7. T1 决策及理由

1. **T1-1 计数器恢复放在两个 actor 的 updater 唯一构造点，而不是逐个改六个 updater 构造函数。** 任务书按决策包行号列了 `update_weight_from_tensor.py:103` / `update_weight_from_rdt.py:111`，但 06 计划明确"覆盖全部 updater 不只 rollout manager（p2p.py:61 / mixin.py:358）"。六个构造函数没有共同基类、签名里也拿不到 `loaded_rollout_id`；在 `actor.py` 的 `self.weight_updater = update_weight_cls(...)` 之后设一次，六个都覆盖、上游新增 updater 也自动覆盖，且 `weight_version` 本就是被 actor 读写的普通属性（`actor.py:912`）。代价：触碰了所有权清单之外的 `megatron_utils/actor.py` 与 `fsdp_utils/actor.py`（各 +1 import +1 语句）；两个 updater 文件零改动。
2. **T1-2 trainer 侧自己读状态文件，而不是经 RolloutManager → `EnginesAndLock` 传递。** 时序上 `actor.init()` 先于 `RolloutManager.load`，trainer 在构造 updater 时 RolloutManager 还没恢复；改 `EnginesAndLock`（跨组件 dataclass）传值要动 `update_weights` 调用链。让 trainer 按与 data_source 完全相同的模式（`args.load` + 同一 rollout_id）读同一文件，两侧再用首次 publish 核对互相校验，比传值更简单也更可审计。
3. **T1-3 新增首次 publish 恢复核对（`RecoveryVersionMismatch`）**——决策包没写，但没有它"bootstrap 标 p"只是一个假设：trainer 与 RolloutManager 读不同 rollout_id（例如用户 `--start-rollout-id` 与实际加载迭代不一致，stock 本就允许）时会静默错标。核对只在本 run 首次 `set_weight_version` 做一次，放在 W10 检查之前；它是 run-fatal 而非 warning，与 W10"engine 不一致即停"同一语义。
4. **T1-4 恢复语境 = 有 `--load` 且 `rollout_id >= 0`，严格按任务书；不做"tracker 是否存在"判断。** 全新 run 下 arguments.py 会把 `args.load` 改指 `ref_load`（通常本身就是带 tracker 的 Megatron 目录），用 tracker 判恢复会把全新 run 误判成恢复。用 `-1`/`>= 0` 与 stock 自己的分类完全同源。
5. **T1-5 版本文件是独立 JSON，不塞进 `global_dataset_state_dict_*.pt`。** 改 `.pt` 内容要改 `DataSource.save/load` 抽象接口（公共 API，custom data source 也实现它）；独立文件不动接口，且 JSON 可人工读、import-light。写入不受 `rollout_global_dataset` 限制（版本与数据源类型无关）；但 `RolloutManager.load` 在 `placement_group.py:195` 仍只在 `rollout_global_dataset` 下被调用——首训 profile 为 True，非 global dataset 的恢复面登记为开放问题 4。
6. **T1-6 已发布版本严格只收 `int`（bool / 数字字符串都拒）。** 版本事实的来源唯一（updater 的 int 计数器），任何别的类型都意味着来源错了，不做静默转换；损坏文件报 `RecoveryStateMissing(detail=...)` 而非泛 `ValueError`。
7. **T1-7 FSDP backend 一并接线（+4 行）**：不接的话 FSDP 恢复会沿用错误的 v1 语义，与 Megatron 路径分叉；只做源码事实测试，GPU 未验证（残余 4）。
8. **T1-8 不新增 CLI 参数、不改 `train_async.py`。** 恢复语境全部由既有参数推出，避免与 W4 在 `arguments.py` 的改动并发；`train_async.py` 的既有顺序正是合同依赖的事实（源码事实测试钉死）。
9. **T1-9 测试手法：ast 抽真实 RolloutManager 方法体绑定到替身。** RolloutManager 不能在 rh2 venv 实例化（W5a/W10 只做了源码事实），本批需要真实 `save/load/set_weight_version` 语义参与冷恢复时序，故沿用 `test_zero_signal_semantics` 的"编译生产源码单个函数"手法，替身只提供 `__init__` 的两个字段与 `_get_updatable_server`。

## 8. 开放问题

1. **launch.sh 无法表达重启**：`rh2/experiments/miles_gpu_spike/launch.sh` 把 `--load "$CKPT" --save "$CKPT"` 绑定在唯一 run root（`RUN_ROOT/ckpt`）下，且 run 模式断言 run root 不存在——冷重启需要"新 run_id + `--load` 指向旧 run 的 ckpt 目录 + 新 `--save`"的入口（例如 `RH2_SPIKE_RESUME_FROM=<old RUN_ROOT>/ckpt`）。归 W7 / C 包（launch 是 W7 读取口径的一部分），本批不改 launch。
2. **GPU 验证项**（归 spike/C）：真实 run 在 `save_interval` 点后 kill → 同一 ckpt 目录重启 → 核对 `run_restarted` 事件、bootstrap `weight_update.version_after == p`、`engine_versions_after_publish` 收敛、`train_rollout` 的 current version 从 p 起、`weight_publish_conservation` 以 bootstrap 起根仍通过；负例：删掉 `rollout/global_dataset_state_dict_r.pt` 重启必须 typed 失败且退出码非零。
3. **judge 消费**：`run_restarted` 尚无 `g1_acceptance.py` 判定键；judge 现有 `weight_publish_conservation` 以 bootstrap `version_after` 起根，不假设从 1 起，重启 run 应能通过（未实跑）。是否升为判定键（如"重启 run 必须恰有一条 run_restarted 且 bootstrap 版本等于其 p"）待 C 定（增判定 = T1）。
4. **非 global dataset 的恢复面**：`placement_group.py:195` 只在 `rollout_global_dataset` 下调 `RolloutManager.load`，此时版本文件会写不会读（trainer 侧仍恢复计数器，但 RolloutManager 侧不做首次 publish 核对、不发事件）。首训 profile 为 True；若将来用非 global dataset 恢复，需把该调用去掉条件（改 `placement_group.py`，本批未动）。
5. **`--ckpt-step` 回退到更早迭代**：状态文件按 rollout_id 键，回退到迭代 k 时读 k 的文件——只要 `rollout/` 下的文件没被清理就成立；miles 里没有任何代码删除 `rollout/` 状态文件（`save_retain_interval` 只在 arguments.py 出现），登记为事实，未加保护。
6. **manifest / patch 0016**：由集成者存档并更新 manifest；在此之前 `miles_integration_lanes.sh` 前置校验（工作树不干净）与 `test_g1_acceptance_events.py::test_producer_tree_digest_matches_audit_manifest` 保持红——预期。

## 9. 测试证据（2026-09-04 实跑）

- 新文件单跑：`RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/test_w5b_cold_recovery.py -q` → **33 passed**（首跑 1 红：`initial_updater_weight_version("7")` 因 `int("7")` 静默转换未拒，改为严格 int 校验后全绿，见 T1-6）。
- lane B（integration tree）：`uv run pytest tests/adapters_miles/ -q` → **648 passed, 1 failed** = 616（manifest）+ 33 − 1；唯一红 = `test_g1_acceptance_events.py::test_producer_tree_digest_matches_audit_manifest`（manifest 树摘要仍是 patch 0015 的树，预期，随 0016 存档解除）。
- lane A（默认 pin）：`uv run pytest tests/adapters_miles/ -q` → **339 passed, 310 skipped**（= 277 + 33，新测试全部 `integration_base` 豁免；失败 0）。
- `miles_integration_lanes.sh --checks-only` → `FAIL: integration checkout 工作树不干净`（预期，列出的正是 §6 六个文件）。
- ruff：miles 六文件用 miles `pyproject.toml` 规则 `All checks passed!`（仅 ruff 对该 pyproject 顶层 `select/ignore` 位置的既有 deprecation warning）；rh2 新测试文件用 rh2 规则 `All checks passed!`。
- 全仓（默认 pin，`cd rh2 && uv run pytest tests/ -q`）：**1653 passed, 310 skipped, 0 failed**（exit 0；并行 W3b 线程本批实跑期间在 rh2 工作树没有落下源码改动，故无需归因）。
- rh2 侧：除新测试文件与本文外零改动（`git status` 无 rh2 源码 M 项）；两个仓库均未 commit / 未 stash。

## 10. 本轮没有改变哪些已定案语义

B-1 consume-time 唯一权威与 `--max-weight-staleness`（W4）；B-2 drop 语义与三分支事件；B-4 `update_weights_interval = 1`；B-5 retract / W10 多 engine 收敛核对（`set_weight_version` 的 W10 段逐字未动，只在其前插入首次 publish 核对）；W5a 关停链；F2 零信号 publish 门控；train_async 的 JIT drain 顺序；`DataSource` 抽象接口；Megatron checkpoint 内容与 `start_rollout_id` 的 stock 推导；不做 joint commit / COMMITTED marker / 复合身份 / pending replay / 精确 cursor / optimizer exactly-once / crash matrix 扩展。

**待拍板 T0：无。**（新增状态文件与事件均为决策包已批的"保存一个整数 + 重启记录"；首次 publish 核对是 T1-3 的正确性护栏，不改变任何已批语义。）
