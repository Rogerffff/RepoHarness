# miles v0.1.1：RH2 运行时生产路径审查

整理：2026-09-29。角色：review-standards §10.4 Production Tracer。范围是实际集成路径、状态 owner、异常传播与补丁承接；不实施迁移，不把上游全部功能当作本项目必须采用的功能。

**结论：v0.1.1 不是当前 fork 的可直接替换版本。** 发布后 drain 的关键修复在 fork 已有等价实现；bridge 恢复修复甚至已在 base 中。新版确实提供更统一的 controller、worker 管理、权重传输和指标，但没有承接 RH2 的零信号语义、关停合同、全引擎版本收敛、冷恢复版本状态、评测身份与验收证据。迁移主要成本是重新建立这些边界，不能靠重命名 import 或删除冲突补丁完成。

本轮没有发现足以要求立刻升级整个 runtime 的证据。可考虑的窄项是取消组隔离、选中数据的版本指标，以及未来确实需要快照评测时的相关修复；它们的收益和前提见下表。这是审查建议，不是迁移批准。

## 1. 版本、事实来源与验证边界

- **F（当前 fork）**：`reference/miles-rh2-integration`，HEAD `275e31eb2`。构造事实以 [integration_base_manifest.json](../../miles_spike/integration_base_manifest.json) 为准：base `f2b7c79298a53c53861514d099f7def73bd29f4a`、四个上游选材、0001–0020。patch README 开头的“至 0016”是旧说明；下方表与 manifest 已列至 0020，不能用标题计数。
- **U（上游）**：`runs/miles_v0_1_1_review_20260929/upstream`，tag `v0.1.1`，`2806267d060d51b1d3b62f85a1f9b145047aeef9`。提交历史从现有 `reference/miles` 读取；没有 checkout/fetch 其它库。
- 最新状态按 [A 线状态](../a_line_status.md) 与 [第五组入口 §8](../batch5_launch_eval_20260919/README.md) 理解：公共评测、独立评测、冷恢复的本机部分已复核；GPU 验证没有完成。八卡实际启动命令后置，旧 `rh2/experiments/miles_gpu_spike/launch.sh` 是 `s1_compat` 历史入口，不能冒充已经冻结的 formal 作业命令。
- 下文源位置用 `F/路径:行`、`U/路径:行` 标明。二者根目录如上。上游 PR 链接指向 radixark/miles；源代码事实来自固定快照和 git，而非仅据 PR 标题推断。
- 本轮运行 [CPU AST 探针](../../../../../runs/miles_v0_1_1_review_20260929/runtime_contract_probe.py)，结果为 [runtime_contract_probe.json](../../../../../runs/miles_v0_1_1_review_20260929/runtime_contract_probe.json)。抽取真实驱动与辅助函数体，用已完成 Future 模拟 Ray 的“调用即提交”，其余外部 actor/服务为替身。证明控制流和局部合同，不证明 GPU/NCCL、真实 Ray 调度或 Docker 清理。未运行 GPU、远端或全套测试。

## 2. 当前真实调用链与 owner 迁移

### 2.1 当前 fork

```text
driver 主 asyncio loop：train_async.train
  create_rollout_manager → Ray RolloutManager actor
  create_training_models → RayTrainGroup（缺省旧 actor_group；实验 FT 另选）
  actor_model.update_weights（bootstrap）
  每轮：RolloutManager.generate → actor_model.train
       → save_model + RolloutManager.save（若到保存点）
       → 有实际权重变化才 publish → eval（若到评测点）
  finally：RolloutManager.dispose(driver_cause) → run 退出 verdict

RolloutManager actor loop
  owns data_source、published weight_version、engine fleet、eval lock
  generate/_get_rollout_data → asyncio.to_thread(call_rollout_function)
    → compatibility.call_rollout_function → async_utils.run
      → 共享后台 AsyncLoopThread
        FullyAsyncRolloutFn worker + active group tasks + DataBuffer
          → GenerateState.generate_function
          → Rh2MilesGenerateFn → ensure_fa_started → RH2 BringupService
          → rh2_custom_generate → 现有 harness/代理/评分/交付
        DefaultDataBuffer.get：消费时版本判定 → 整批 Sample → trainer

trainer rank：MegatronTrainRayActor
  权重 updater → engine Ray actor → SGLang HTTP
  rank 0 → RolloutManager.set_weight_version
    → 每个已分配 engine actor 查询版本 → 不一致/不可达使 run 失败
```

入口证据：`F/train_async.py:44–95,119–199,213–225`；`F/miles/ray/placement_group.py:16–21,157–196`；`F/miles/ray/rollout/rollout_manager.py:56–118,140–202,418–431,569–597`；`F/miles/rollout/inference_rollout/compatibility.py:42–48`；`rh2/src/repoharness2/adapters/miles/generate_fn.py:122–181`。

不能把治理 buffer 当作所有真实路径都已经启用：类入口允许 `custom_async_data_buffer_path`，缺省仍是 `DefaultDataBuffer`（`F/.../fully_async_rollout.py:179–186`）。本表涉及的 consume-time/drop/no-progress 是 fork 的默认 buffer/rollout 实现；`Rh2GovernedBuffer` 的额外 ledger 接线不能凭“代码存在”推定生产使用。

### 2.2 v0.1.1

```text
driver 主 asyncio loop：train_async.train
  launch_worker_manager → RayWorkerManager 启动 trainer/engine/router/session workers
  create_rollout_components
    InferenceController（driver 本地对象，ContextLock）
      owns engine cell/fleet、provider watcher、health checker/ticker、更新窗口
    Ray RolloutExecutor actor
      owns data_source、rollout/eval fn、当前 published version、eval lock
  TrainerController（driver 本地对象）→ TrainerCell → worker handle/RPC → trainer rank
  update_weights helper
    TrainerController.update_weights → InferenceController.start_update_weights
    → trainer WeightUpdater → SGLangApiClient 直接 HTTP
    → InferenceController.end_update_weights
    → 返回 weight_version → RolloutExecutor.set_weight_version
  prepare_rollout → RolloutExecutor.get → 同一 to_thread / AsyncLoopThread 链
  正常结尾依次 dispose executor / inference controller / trainer controller
```

证据：`U/train_async.py:29–78,120–149`；`U/miles/ray/wiring.py:6–15`；`U/miles/ray/placement_group.py:127–194`；`U/miles/ray/rollout/inference_controller.py:41–109,158–209`；`U/miles/ray/rollout/rollout_executor.py:46–110,114–139,213–233,270–277`；`U/miles/ray/train/group.py:39–77,165–213,337–353`。

这不是单纯类名改动：[拆分 #1842](https://github.com/radixark/miles/pull/1842)、[接线 #1843](https://github.com/radixark/miles/pull/1843)、[generate→get #1844](https://github.com/radixark/miles/pull/1844)、[engine 直连 HTTP #1861](https://github.com/radixark/miles/pull/1861)、[worker manager 启动 engine #2063](https://github.com/radixark/miles/pull/2063)、[权重版本由 driver 转交 #2502](https://github.com/radixark/miles/pull/2502) 改变了 owner 和传播位置。现 fork 的 engine identity、publish 事件、版本收敛核对和关停钩子都需要重新安放。

两版的并发骨架仍相近：一个 rollout actor；一个后台 rollout loop；一个 persistent worker；组内用 task 并发。组预算是 `max(1, async_max_concurrent_samples // n_samples_per_prompt)`，未设则取 `rollout_batch_size`；buffer 容量为 `floor(async_data_buffer_capacity_factor * rollout_batch_size)`，满时 `put` 等待 `get` 唤醒。`F/.../fully_async_rollout.py:224–261`、`U/...:109–141`、`F/.../fully_async_data_buffer.py:206–217,268–290`、`U/...:125–161`。这说明上游没有取消基本反压，但 U 的 active group owner 已从 RH2 可访问的 `_active_groups` 变成 worker 局部 dict；其新取消处理不等价于可由关停入口回收全部在飞组。

### 2.3 权重与 HTTP 变化

- 当前 broadcast 等 updater 分别实现，调用 engine Ray actor；新版统一为 backend-neutral `WeightUpdater`，协议承载 broadcast/p2p/cuda-ipc/delta 等差异。[#2752](https://github.com/radixark/miles/pull/2752)、[#2753](https://github.com/radixark/miles/pull/2753)。`U/miles/backends/training_utils/weight_update/updater.py:37–100,105–142` 仍负责增加版本，驱动 rank 执行 pause/begin/transfer/end/set-version/resume。
- 新版 `InferenceController.start/end_update_weights` 在 `ContextLock` 下获取一份 engine clients 与 cell worker hashes 快照，结束时只把同一代 worker 标成 weights-ready（`U/.../inference_controller.py:158–190`）。这解决上游 cell 生命周期问题，但**不等于** RH2 的逐引擎版本回读校验。
- `SGLangApiClient.get_weight_version` 直接访问每个 `server_url` 的 `/model_info`，兼容回退 `/get_weight_version`（`U/.../sglang_api_client.py:246–252`）。可将 W10 的“逐引擎而非 router”语义迁至这里；不是直接保留旧 `.get_weight_version.remote()`。
- 上游常规 publish 后仅在 `ci_test` 且非 LoRA 时随机选择一个 engine 回读版本（`U/miles/backends/megatron_utils/actor.py:831–837`）。可选 checksum event（`U/miles/ray/train/group.py:355–366`）和数值版本 sane 检查也不是 W10 全引擎回读的等价替代。
- 新 `GeneralHttpClientProvider` 按 event loop 缓存 `httpx.AsyncClient`；connect/write/pool 有限时、read 为 `None`，客户端没有统一 aclose（`U/miles/utils/http_utils.py:221–242`）。本轮不将这单列上游泄漏漏洞：当前循环数有界；迁移关停时应明确这个 owner，不能认为有 `InferenceController.dispose` 就已经关闭 RH2 与所有 HTTP 资源。

## 3. 发布修复对现状的实际价值

| 上游项 | 实际改动与当前 fork | 是否值得窄回植 / 限制 |
| --- | --- | --- |
| [#3343](https://github.com/radixark/miles/pull/3343)，`948c1ba46` | U `train_async.py:87–94,120–127`：fully-async 到发布点时延后下一次 drain，先发布再取批。F `train_async.py:109–126,168–184` 的 patch 0014 已让 fully-async **每轮** JIT drain，达到相同版本判定顺序。 | 当前无需再回植。U 在非发布轮保留预取，F 的控制流更简单；不能据此声称 U 必然更快，persistent producer 两边都持续运行。也不能用 #3343 替代 0014 其余 staleness/fatal/drop/no-progress 语义。 |
| [#2682](https://github.com/radixark/miles/pull/2682)，`49cac7b52` | bridge 模式只在没有有效 checkpoint 时置 `start_rollout_id=0`。`git merge-base --is-ancestor 49cac7b52 f2b7c7929` 成功；F `miles/utils/arguments.py:3086–3096` 与 U `:3013–3023` 均为已修逻辑。 | **已在当前 base**，无新增收益；它没有完成 W5b 的版本状态配对，也没有 I22 显式编号一致性检查。 |
| [#3319](https://github.com/radixark/miles/pull/3319)，`e2a5a3e59` | U `fully_async_rollout.py:115–154` 将 task→prompt_group 存在 dict，单个已取消任务转为一组 ABORTED，后续经 buffer aborted filter 决定 drop/retry。F `:252–261` 对完成 task 直接 `.result()`，取消可终止 worker，随后 `_next_group` 传播。 | 这是尚未等价实现的隔离能力，可作窄评估候选。**未在本轮证明当前正常 RH2 运行会独立取消一个组，也未测发生率**；目前明确存在的是整体关停取消，不能让 #3319 把关停误当可回收新任务。回植需保留 `_active_groups`/closed gate/残留身份/三分支 drop 事件，并确认全组 ABORTED 的训练分布与 retry 账目。不是当前 P0。 |
| [#3334](https://github.com/radixark/miles/pull/3334)，`8cb02421d` | U buffer `:163–173,175–237` 只对真正选中的组计 consumed staleness，并新增 newest lag、生成期 version span、token-weighted lag、version coverage。F `:295–316` 在 stale 拒绝之前把 lag 加入 `_metric_consumed_staleness`，所以旧 `avg_staleness` 混含被丢弃组；但 F 的逐组 `group_consumed`/`group_filtered` 已能区分。 | 可窄回植“selected 指标口径”及需要的派生指标。不可整个文件替换，不能丢 0014 守卫/事件。U 依赖 `Sample.all_weight_version_spans` 的结构化版本对象，F 是字符串列表与 RH2 provenance；token 加权不能拿旧列表长度冒充 token 数。新旧指标口径变化必须注明，不能与历史曲线无说明拼接。 |
| [#3172](https://github.com/radixark/miles/pull/3172)，`ab48452ea` | 支持 `debug-train-only` 的 snapshot eval：独立 eval GPU 布局、http 初始化、offloaded trainer 导出前后 onload/offload。U `EvalDispatcher._export:65–76`；`RolloutExecutor.eval:148–152`；`http_utils:334–347`。 | 对本项目当前 I21 **无直接接线收益**：`rh2/.../eval_wiring.py:14–18` 明确首版只支持共享引擎，包括独立 eval-only 作业；snapshot/专用 eval fleet 因代理绑定训练 router 被拒绝。将来要此形态时再引入，不可只开 flag。 |
| [#2823](https://github.com/radixark/miles/pull/2823)，`dc2726907` | U `RolloutExecutor.report_eval_skip:208–211` 在 `ci_test` 下使 skipped eval 失败；普通运行仍降级 skip。 | CI 防假绿有价值；不是 RH2 `None`/不可得评分语义、评测身份与逐题结果的替代。U `metrics.py:23–38` 仍把 `reward=None` 算 0，故 RH2 自定义 eval log/report 必须保留。 |
| [#2814](https://github.com/radixark/miles/pull/2814)，`4a58e4e10` | U buffer 在 aborted filter 后、dynamic filter 前直接拒绝 missing reward（`fully_async_data_buffer.py:135–150`）。 | 不应当作 RH2 可无条件接受的“健壮性修复”。它增加新的拒绝分支，可能先于 RH2 admission/fatal 诊断吞掉坏输入；需要保留原故障分类、身份与拒绝分母。本轮未建议启用。 |

## 4. 三个有对照证据的迁移接缝

三项均标 **conditional_future**：触发条件是尝试用 U 替换 F 或搬移补丁。当前 fork 不因本报告而变成已确认线上故障；这里的 CPU 探针也不标 `production_observed`。

### RT1：零训练轮的独立评测仍会提交训练生成

- **当前行为**：I21 使用真实 `train_async.train`，形态为 `fully_async=True, debug_rollout_only=True, num_rollout=0, rollout_global_dataset=False, start_rollout_id=0`；F 只发生 bootstrap 空调用、一次 eval、dispose。真实已审形态见 `rh2/tests/adapters_miles/test_i21_eval_only_driver.py:1–17,37–40,138–154`。
- **U 行为 / 违反不变量**：U `train_async.py:76–81` 无条件 `eager_create_task(prepare_and_generate(start))`，在进入零轮循环之前调用 `RolloutExecutor.get.remote`；`eager_create_task` 明确会先 yield 让远程提交发生（U `async_utils.py:80–88`）。违反独立评测“零 training generate/零 train”的合同。
- **证据**：AST 同参对照中，F 无 `training_get`；U 有 `prepare_rollout → training_get`，然后才 dispose，结果见 JSON 的 `eval_only_fork/upstream`。用完整 driver 函数体而非仅 helper。
- **影响**：若先移植 I21 宿主身份令 eval 能运行到这里，额外 `get` 会走训练路径。该形态没有训练题包，且关闭 global dataset；可能导致后台 assertion 或非预期派发。探针只证明已提交，不虚报真实资源泄漏或训练成功。
- **分期 / 建议**：迁移前修 driver 零轮提交边界；无需引入新恢复 owner。保留 eval-only 路径和现参数合同，或明确更换入口并同步 I21 预检与验证。
- **复现**：`python3 runs/miles_v0_1_1_review_20260929/runtime_contract_probe.py`。
- **验收**：同一 eval-only 配置穿过真实新版 driver、数据源和 RH2 预检；调用即提交替身记录恰一次 eval，零 get/train；正常训练仍能开始第一批。

### RT2：原 finally 关停及 RH2 closure 没有上游承接

- **当前行为**：F `train_async.py:60–67,213–225` 在 manager 创建后进入 try/finally；模型构造、bootstrap、eval、train 等异常都执行 dispose，并将 driver 首因交给 RH2。F manager `dispose:140–202` 投递到 rollout owner loop，返回清理 verdict；`rh2_shutdown.py:417–455,490` 负责期限与失败出口。
- **U 行为 / 违反不变量**：U `train_async.py:35–149` 无相应 finally，仅正常结尾调用 dispose。U `RolloutExecutor.dispose:103–110` 也不调用 rollout fn aclose / RH2 BringupService；U `FullyAsyncRolloutFn` 无 aclose。违反现“成功与异常退出都闭合资源、残留使 run 失败、首因不被覆盖”的合同。
- **证据**：AST 对照在 trainer.train 注入同一 RuntimeError：F 记录 `dispose_rollout`，U 不记录任一 dispose；异常原样保留。上游 normal-path dispose 实现也逐项核对，并非只搜索函数名。
- **影响**：若直接采用 U，不能依赖 Ray job 自动退出证明外部 sandbox/评分/HTTP 资源已闭合，也没有现 shutdown report 的可靠最终 verdict。实际泄漏规模、本机之外的信号传播均未测。
- **分期 / 建议**：迁移前保留 0010–0013/0017 语义，拆明 `RolloutExecutor` 的 RH2 owner-loop closure 与 driver 中 controller 资源释放；没有理由新建完整恢复平台。当前 F 无需因这项做额外修复。
- **复现**：同一探针的 `trainer_failure_fork/upstream`。
- **验收**：启动后初始化失败、bootstrap/train/eval 异常、正常退出都进入 closure；在正确 loop 关闭 worker/buffer/RH2；真正残留非成功、等待类暂态仅在最终任务已收齐且 RH2 自证关闭后消解；driver 原始异常仍为首因。

### RT3：新版本发布守卫会误拒绝合法的 all-skip 区间

- **当前行为**：F patch 0002/0003 在全部 rank 的全部 step 均精确零梯度时，跳过 optimizer/scheduler，`weights_dirty=False`；driver 不发布、不加版本（F `train_async.py:23–40,153–196`）。这是已定训练语义。
- **U 行为 / 违反不变量**：[#2470](https://github.com/radixark/miles/pull/2470) 使 `RolloutExecutor.get` 每次增加 `_rollouts_since_weight_version_publish`，`set_weight_version` 才清零（U `rollout_executor.py:114–120,270–277`）；`weight_version.py:17–30` 超过 `max(3, update_weights_interval+1)` 就 assert。它把“参数未变所以没有必要发布”也视为版本运输断线。
- **证据**：抽取真实 F `_any_weights_dirty` 和 U `assert_weight_version_is_published`；`update_weights_interval=1`、连续 all-skip 时 F 每轮均不要求 publish，U 第四次 get 触发断言。结果见 `all_skip_publish_guard`。
- **影响**：如果只搬回 0002/0003 而不处理新守卫，合法零信号序列可被误报 run 失败；直接去掉 0002/0003 则回到零梯度仍经 AdamW 动量/weight decay 更新、版本虚增的另一种语义。默认是否连续出现四批本轮未知，不以发生率假设降低合同冲突。
- **分期 / 建议**：迁移设计时让“完成了 publish 决策但权重没变”与“忘记转交发布版本”可区分；不能通过伪造版本前进解决。可修改现有守卫的输入/触发条件，优先不新增长期状态机。
- **复现**：同一 AST 探针。
- **验收**：全跳过期间版本与参数不动且不触发缺发布；有脏权重却漏转版本仍能失败；混合 applied/skipped step 与跨 publish interval 的 OR 聚合仍正确。

## 5. 指定的 16 个补丁逐项承接表

“未承接”指已检查相应生产消费者没有等价语义，不是仅因 `rh2_*` 名字不存在。搬移成本只给相对范围，不估未经实现验证的工期。

| patch | 当前能力与源位置 | U 的实际对应路径 / 承接程度 | 迁移工作量与不能丢的条件 |
| --- | --- | --- | --- |
| 0002 | 精确全局零梯度跳过 optimizer/scheduler；NaN/Inf 不伪装零信号；聚合报告与连续熔断。F `megatron_utils/model.py:895–946`、`ft/types.py:14–99`。 | **未承接**。U `model.py:587–633` 的 finite/valid 处理后正常调用 optimizer；`ft/types.py:15–23` 只有 NORMAL/DISCARDED 与新 TrainStepOutput。 | 中高：训练返回容器也已变，不能只拷贝分支；需跨 rank 一致、step 聚合与 driver dirty 消费一起验证。训练审查另覆数学面。 |
| 0003 | dirty 在 publish interval 上 OR 聚合；all-skip 不发布、不加版本。F `train_async.py:23–40,104–108,153–196`。 | **未承接**。U `train_async.py:96–125` 不消费训练返回的 dirty 信息，固定间隔更新；新 #2470 还与该语义冲突。 | 中：恢复聚合、发布事件，并处理 RT3，不能用频率守卫覆盖合法不发布。 |
| 0004 | G1 JSONL、跨 actor integration tree identity、消费/optimizer/publish/rollout/eval 证据。F `rh2_event_log.py:122–152,183–212`；actor/model/manager 的 emit。 | **部分通用观测、无合同等价**。U `audit_utils/event_logger/models.py:15–89` 有 checksum、witness、group-step/metrics；不包含 RH2 相同事件、tree digest 与验收 schema。 | 高：角色拆分后重新选启动 identity 点；保持 run-report/G1 collector 的真实事件来源，或明确迁移消费者。不能拿默认 W&B run_id 当 RH2 跨进程 identity。 |
| 0005 | run_id 印章、实际 micro-batch 归属、replay fill/forward/drain 绑定、mask 口径 logprob compare、eval 版本与 scan 耗时。F `actor.py:484–540,554–596,647–730`、`model.py:614–677,912–921`；`utils/step_attribution.py`、`logprob_compare.py`。 | **未承接同等验收链**。U 仍有 replay/logprob/training 通用功能，但无上述 per-leaf/tape/step 证据合同；共享 eval 不向 RolloutFnEvalInput 传已发布版本（U executor `:154–158`）。 | 高：随新训练拆分放到真正 forward/optimizer 消费点；不能仅生成同名事件或以相关 loss 测试替代证据。 |
| 0006 | leaf ordinal 进入 wire、per-rank step 事实、engine identity。F `train_data_conversion.py:29–50,85–94`；`model.py:566–611`；`actor.py:575–596`。 | **未承接**。U `train_data_conversion.py:29–50,76–85` 无 leaf_ordinals；engine Ray shell 被 #1861 删除。 | 中高：新 transport/spec、训练消费者和证据都需匹配；engine 身份须绑定真实 worker/端点，不能继续指向已删除 shell。 |
| 0010 | rollout worker/active groups bounded aclose；buffer close 唤醒 put/get；manager dispose 串 RH2；driver finally。F `fully_async_rollout.py:263–349`、`fully_async_data_buffer.py:318–326`、`train_async.py:213–225`。 | **未承接**。U fully_async 只有局部 active dict；executor dispose 不关闭它；driver 正常出口才 dispose。 | 高：整体迁入新 owner 边界；参见 RT2。 |
| 0011 | closure 回投共享 AsyncLoopThread，外层总期限；避免跨 loop await。F `rh2_shutdown.py:417–455`。 | **未承接，必要拓扑仍在**。U executor `:219–227` 仍 `to_thread`，compatibility `:49–55` 仍把协程送后台 loop。 | 中：原跨 loop 原理可复用；入口从 manager 改 executor，不要在 InferenceController loop 上直接 await rollout task。 |
| 0012 | 关停残留结构化升级 run failure；driver primary、worker/residue secondary。F `rh2_shutdown.py:101–159,217–330,490`、driver `:214–225`。 | **未承接**。U 的普通 dispose 返回值不携该 verdict，顶层 finally 只有 finish_tracking。 | 中：保留失败首因与残留身份；不可降为日志后成功退出。 |
| 0013 | driver cause 严格同源判定，避免子串误合并不同失败。F `rh2_shutdown.py:163–177`。 | **未承接**，依附 RH2 closure。 | 低（在 closure 已移植之后）：纯同源判定可复用，不能用异常消息局部匹配替换。 |
| 0014 | 消费时 staleness 唯一资格点；formal 缺版本/负 lag fatal；三分支 drop、累计接受数、no-progress、JIT drain。F buffer `:278–316,328–373,406–449`；rollout `:89–111,416–508`；driver `:109–126`。 | **只承接发布后 drain 和一般 staleness 过滤**。U buffer `:153–173` 缺 formal/负 lag 拒绝；版本缺失可直接返回；U rollout `:158–177` 只每 30 秒告警，没有 accepted-group hard timeout。#3334 指标也不是逐组终局事件。 | 高：不能删整个 patch；可采用 #3343 的顺序，但需保留判定/事件/无进展出口。#2814 新拒绝分支须另纳入账目。 |
| 0015 | publish 后向所有 engine actor 回读，超时/不一致停 run，发完整收敛事件。F manager `:569–597`、`rh2_engine_versions.py:87–121`。 | **未承接**。U 发布写入全 clients，CI 只随机回读一个；numeric sane 与可选 checksum 不是相同合同。 | 中：改为所有 SGLangApiClient 的有界 HTTP 读；明确 cell generation 快照，放在版本对 executor 生效的边界；保留 indep_dp 既有排除。 |
| 0016 | checkpoint 保存已发布 p；updater 恢复 p−1；bootstrap 重发 p；数据/版本状态缺失 fatal；run_restarted。F manager `:450–464`、actor `:285–291`、`rh2_recovery.py:1–47,174–239,261`。 | **未承接**。U updater `:66` 从 0 开始；executor `:247–262` 调 data_source 与 rollout fn save/load；data_source `:146–149` 缺状态只记日志返回。BaseRolloutFn `:79–83` 默认 save/load 是空操作。 | 中高：可以利用新增 save/load 接缝，但不能宣称它已经保存版本/在飞状态。继续接受原 B-3 无 joint commit、丢 buffer/在飞组、不做 exactly-once 的边界。 |
| 0017 | 等待类暂态在有界 settle 后复查；仅当任务均结束且 RH2 独立自证闭合才消解原等待失败。F `rh2_shutdown.py:337–413`、rollout 的 await_settled/final_close_state。 | **未承接**，上游没有相应 closure 状态。 | 中：随 shutdown 整体搬；不能把单一 task.done 或 dispose 已返回当资源清零。 |
| 0018 | eval 每次调用宿主盖 eval_point_id/目标版本/成员坐标，盖章晚于 inject_metadata；shared-engine eval 窗口事件。F eval `:23–61,117–129`、fully_async `:188–220`、manager `:342–351`。 | **未承接**。U eval `:84` 只 inject_metadata；run_eval_datasets 不接派发事实；shared executor eval 不传 version。 | 中：重新传播调用事实；RH2 generate 的 `eval_host_stamp_unsupported` 守卫必须继续生效。仅打开上游 eval 功能会被现 RH2 拒绝，不能删守卫求运行。 |
| 0019 | 数据集结果挂 `rh2_eval_call`，零样本仍保留评测点/加载后分母。F eval `:176–185`。 | **未承接**。U 返回 samples/rewards 等普通结果，无调用级 RH2 identity；默认 metric 对 None 算 0。 | 低中：与 0018、RH2 自定义 eval report 同迁；必须测所有样本被过滤/无结果，不能只测正常成功题。 |
| 0020 | 显式 N>0 必须满足 N−1 等于 trainer 实载 checkpoint k；0/未知沿用既有边界。F `rh2_recovery.py:242–258`。 | **未承接**。U placement `:150–157` 只在未显式 start 时采用返回值，随后 load(start−1)；#2682 只是 fallback 缩进。 | 低（依附 0016）：可复用纯匹配检查，但实际 loaded k 的来源要跟新 trainer init 对齐；不能以两个状态消费者彼此一致替代与权重加载点一致。 |

## 6. 可复用部分、迁移成本与仍未知

**可复用的基础**：类式 `GenerateFnInput/Output` 调用、Sample→train data 大体流水线、persistent async producer、buffer 反压、独立 eval dispatcher、save/load 入口都保留。RH2 `Rh2MilesGenerateFn` 是 generate function，不是 rollout function，因此新增 `BaseRolloutFn` 继承要求（U `compatibility.py:35–46`）不会仅因这个名字就拒绝它；若迁移自定义 rollout class，则需要继承该类。

**必须重新建立的边界**：driver/executor/controller 的关停传播；trainer 返回值到 dirty publish 的合同；executor 收到的版本与所有引擎实际版本；checkpoint 权重/数据游标/已发布版本；eval 调用身份与零样本结果；训练 wire 的 leaf identity 与真实消费证据。主审的 import 扫描还发现模块/导出改动；通过这些扫描只是能导入，不是上述语义已保持。

**上游新增能力不是当前批准语义**：TrainerController 的重试、cell 替换/health reconcile、权重连接恢复都比旧默认拓扑更广。当前 RH2 B-3/B-5b 是 engine 死亡停 run + 冷恢复，不允许仅因上游会 retry 就自动扩大正式运行恢复边界。需要在采用前明确保留哪条故障路径，不能把 FT 默认实现等同本项目已验合同。

仍未知、登记到真正迁移或 GPU 作业时再验证：

1. 新 controller/HTTP/RPC 组合在本项目模型、SGLang pin、TP/CP 和多引擎形态下的吞吐、暂停窗口、超时与资源释放；本轮没有把上游 CI 或 release tag 当作 RH2 GPU 证据。
2. #3319 在当前 RH2 中“非整体关停而单组 task 被取消”的实际发生条件和频率；不能凭单测取消一个 task 就宣称经常影响本项目。
3. #3334 的 token 加权指标能否直接由 RH2 现存完整 provenance 重建，以及版本跨度/训练 mask/叶 fan-out 的统计分母；structured `Sample.weight_versions` 的具体运输兼容由训练审查负责去重。
4. 新 save/load hooks 与 RH2 原 B-3 残余的组合行为；本轮没有声称 checkpoint、cursor、version 三者原子提交，也不建议为升级另起事务恢复平台。
5. 共享 eval 的真实在飞训练组重叠成本、独立 eval 固定 HF 权重实际加载、多 rank 退出和 cold restart；仍属现有八卡核验清单。

**停止条件已满足**：本轮追到训练消费、发布/版本更新、eval、save/load 与异常关停的主要 owner；指定 16 个 patch 均有消费者级承接判定；三个迁移接缝有局部对照探针。未继续审上游全仓故障恢复/LoRA/所有传输协议，不新增与当前作业无关的阻塞项。
