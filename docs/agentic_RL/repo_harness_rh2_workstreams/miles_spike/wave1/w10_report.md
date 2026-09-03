# W10 实现报告 · 多 engine 最小正确性（决策包 D2+B v2 B-5b）

日期：2026-09-04。执行依据：`miles_spike/decision_package_D2_B.md` v2 B-5a/B-5b（owner 2026-09-04 拍板"租卡前必做"）、06 计划 §3 W10 行。工作树：rh2 HEAD `b007c0d9`（未 commit / 未 stash）；miles integration tree `reference/miles-rh2-integration` HEAD `d66576aea`，工作树改动**未 commit**（待集成者存档为 patch 0015；同一工作树里还有 W4 的未提交改动，存档时须按文件拆分，见 §5）。本文同时充当本工作包的 implementation-notes。

一句话：**MilesRouter 的两处多 engine 正确性缺口（rid abort 错发、经 router 随机探测版本）已关闭——abort 改为 `/list_workers` 全 worker 广播、版本探测整体删除、publish 后版本收敛经 engine actor 逐台核对；`engine_count == 1` 的硬编码与 preflight 限制已删；两假 engine 的本地反例 23 例全绿。GPU 真多 engine e2e 与 matched comparison 归 spike/C（§6 清单）。**

---

## 0. 交付物一览

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/adapters/slime/engine_router_client.py` | **新增** | `MilesRouterWorkerClient`：`list_workers()`（GET `/list_workers`，fallback 新 sgl-router 的 `/workers`；URL 规整镜像 miles `router_worker_base_urls`）与 `broadcast_abort(rid)`（对全部 worker 直发同一 rid，永不抛，返回 `AbortBroadcastResult`） |
| `rh2/src/repoharness2/adapters/slime/capture_wire.py` | 修改（仅 abort 分支 + registry 挂点） | `CaptureRegistry.engine_abort` 挂点、`abort_results` 有界环、4 个 abort 计数；`_send_once` 的 cancel/超时/连接错误分支改经 `_abort_rid(rid)`：挂点在场即广播，未接线退回 stock 经 router 单发并记 `abort_router_single_send` |
| `rh2/src/repoharness2/adapters/slime/bringup.py` | 修改 | ① `__init__` 接线 `registry.engine_abort = MilesRouterWorkerClient(sglang_url).broadcast_abort`；② **删除** `_latest_engine_version`（GET `/model_info` fallback `/get_weight_version` + registry 交叉检查）与 `_registry_max_version`，新 `_observed_current_version`（只读 capture 观测，不发请求）作 finalize 握手与 proxy 窗口的 current 版本；③ W4 接缝 `staleness_threshold_mirror_from_args(args)` → `SlimeBindingConfig.staleness_threshold`；④ startup_evidence 新增 `router_workers`（worker 列表与数量；取不到只记错误） |
| `rh2/experiments/miles_gpu_spike/launch.sh` | 修改（未审文件） | per-engine 恢复为 `RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE`（默认 2）；删"覆盖位已作废设了即红"与 `per-engine := 全部 rollout 卡`；P11(d) 删 `ENGINE_COUNT -eq 1`，改为正整数 / ≤ rollout 卡数 / 整除 / engine 数 ≥ 1；P11(c)、文件头、dry-run 拓扑行去掉"钉死单 engine" |
| `rh2/experiments/miles_gpu_spike/{launch_args.md, thresholds.md, router_targeting_audit.md, implementation-notes.md}` | 修改（未审文件） | 参数条目 / 拓扑登记 / 审计 §0 状态表 / 本包记录 |
| `rh2/tests/adapters_miles/test_w10_multi_engine.py` | **新增** | 23 例（16 例双 lane + 7 例 `integration_base`），见 §4 |
| `rh2/tests/adapters_miles/test_bringup_weight_version_probe.py` | **删除**（4 例） | 被测探测已删除（T1-9） |
| miles `miles/utils/rh2_engine_versions.py` | **新增**（integration tree 工作树） | `verify_engine_weight_versions(handles, expected, timeout)`：并发问全部 engine actor，发 `engine_versions_after_publish` 事件，不一致/不可达抛 `EngineWeightVersionMismatch` |
| miles `miles/ray/rollout/rollout_manager.py` | 修改（integration tree 工作树，+23/−1） | `set_weight_version` 改 `async`，publish 后对可更新 server 的全部 node-0 engine 逐台核对（`indep_dp` 跳过） |

**未触碰**：`adapters/miles/generate_fn.py`（其中没有版本探测或 abort 代码，无需改动）、`generate.py`/`grading/*`（W3a）、`governance/*`、`envpack/*`、`contracts/`、`rh2/src/slime`、bringup 的挡板（任务书所指 `bringup.py:705-713`：HEAD 该区间是 `return PerRolloutAdapter()` / `class BringupService` 头与 `__init__` 的三行 import，内容未动；fa_formal 暂禁挡板在 HEAD 778-787、现因上方插入位移到 819-829，逐字未动）；miles 的 `fully_async_data_buffer.py`/`fully_async_rollout.py`/`train_async.py`/`rh2_event_log.py`/`arguments.py`（W4）、`miles/router/router.py`（无需改：广播不经 router 选路）。

---

## 1. abort 广播机制（B-5b 第 1 项）

**问题**（代码事实）：MilesRouter 只有 `POST /add_worker`、`GET /list_workers` 两条显式路由，其余路径走 catch-all `do_proxy` → `_use_url()` 取"活跃请求数最小"的 worker，不读 `X-SMG-Routing-Key`、不记 rid 归属。rh2 capture wire 在 cancel/超时后发 `POST /abort_request {"rid"}` 若经 router，命中持有者的概率是 1/N；错发时 SGLang 对未知 rid 静默无操作、router 照样 200，被放弃的生成继续占槽位直到自然完成。

**方案**（仿 miles 自身 abort-all 形状 `inference_rollout_train.abort` → `get_worker_urls`）：

1. bringup `__init__`：`self.router_workers = MilesRouterWorkerClient(self.sglang_url)`；`self.registry.engine_abort = self.router_workers.broadcast_abort`（纯配置，在任何资源型副作用之前）。
2. capture wire `_send_once` 的 except 分支（`asyncio.CancelledError` / `aiohttp.ClientError` / `asyncio.TimeoutError`）调 `_abort_rid(rid)`：`registry.engine_abort` 在场 → `broadcast_abort(rid)`：GET `{router}/list_workers` → 对每个 worker `POST {worker}/abort_request {"rid": rid}`（`asyncio.gather(return_exceptions=True)`），持有者终止、其余 worker 忽略；结果经 `registry.note_abort_result` 记进 `stats`（`abort_requested` / `abort_broadcast` / `abort_router_single_send` / `abort_delivery_failed`）与 `abort_results`（最近 256 条）。投递失败只记账不上抛（与 stock 一致：abort 是尽力释放，不改变本次失败的归因）。
3. 退化路径（显式记录，不静默）：`/list_workers` 与 `/workers` 都取不到（非 MilesRouter / router 不可达）→ 退回 stock 形状经 router 单发，`mode="router_single_send"` + `list_error`；`engine_abort` 未接线（S1 mock 链 / 无 bringup 的测试面）→ 同样单发并记 `list_error="engine_abort_not_wired"`。单发只在单 worker 池下语义正确，多 engine 下会错发——这正是 §4 反例测试所证。
4. 不做：rid→worker 粘滞表、`X-SMG-Routing-Key` 定向、dead worker 回池、`/remove_worker`。capture wire 仍发送 `X-SMG-Routing-Key` 头（对 MilesRouter 是死字节，无害，未动）。

worker 可达性：engine 以 `http://{server_host}:{server_port}` 自注册；miles 自己的 abort-all 就是从 rollout fn 进程（与 bringup 同进程）直发 worker，路径同源。

## 2. 版本探测删除点（B-5b 第 2 项）

| 删除 | 位置 | 替代 |
|---|---|---|
| `BringupService._latest_engine_version`：经 router 发 GET `/model_info`（fallback `/get_weight_version`）取"权威版本"，`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下失败 fail-closed；registry 最大观测 > 权威 → `RuntimeError("版本事实矛盾")` | bringup.py（原 :1095-1160 区段） | `BringupService._observed_current_version`：capture wire 逐轮记录的 `meta_info.weight_version`（含 spans 内全部版本）数值最大值，无记录回退启动探针值 `policy_version`；**不发任何请求** |
| `BringupService._registry_max_version` | 同上 | 并入 `_observed_current_version` |
| `build_production_model_call_proxy(self.registry, self._latest_engine_version, …)` | bringup `_async_start_body` | `self._observed_current_version`（`StaticActiveCoordinator` 的 provider） |
| `RolloutOrchestrator(current_policy_version_provider=self._latest_engine_version)` | 同上 | `self._observed_current_version` |
| bringup 的 `import requests`（只在该方法内） | 同上 | 无 |

为什么可以删：B-1 改判后 finalize-time staleness 不是任何资格门（consume-time `--max-weight-staleness` 是唯一权威，`current_published_rollout_weight_version` 由 miles buffer 持有），该探测已无资格用途；而它在多 engine 下的具体危害是更新窗口内探到未更新 engine、capture 已从已更新 engine 观测到新版本时，交叉检查把瞬态偏斜判成"版本管道错乱"假红崩溃（router_targeting_audit.md §4）。新口径 = "截至目前引擎向本进程报告过的最新版本"这一观测上界：一定 ≥ 本轨迹任何 turn 的 behavior 版本（同一 registry），`_build_handshake` 的 `weight_version_ahead_of_current` 矛盾检查不会因取数方式假红；可能滞后于 trainer 刚发布、尚未服务过本进程任何请求的版本——只让 finalize-time lag 的**观测值**偏小，不影响任何准入判定。

**publish 后收敛事实（可选项，已做最小实现，miles 侧）**：trainer rank 0 在 `weight_updater.update_weights()`（对 `EnginesAndLock.rollout_engines` 全量 pause → update → `update_weight_version` → continue）之后调 `rollout_manager.set_weight_version(v)`；该方法改为 `async`，对可更新 server 的全部 node-0 engine（`srv.engines`，`is_allocated`）经 actor handle `get_weight_version.remote()` 并发查询（每台超时 `RH2_MILES_ENGINE_VERSION_TIMEOUT_SEC`，默认 60s），发一条 `engine_versions_after_publish` 事件（expected / versions / errors / num_engines / converged），任一 engine 版本不等于发布值或不可达 → `EngineWeightVersionMismatch` 经 trainer 的 `ray.get` 传播 → run 停止（走既有关停链，B-3 重启）。`indep_dp` 跳过（副本可合法不同版本）；`debug_train_only`（无 server）跳过。不经 router。

## 3. 参数 / preflight 恢复清单

| 项 | 之前 | 现在 |
|---|---|---|
| `ROLLOUT_GPUS_PER_ENGINE` | `:= $ROLLOUT_GPUS`（恒 1 engine）；`RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE` 设了即 `die` | `"${RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE:-2}"`——默认 2 = P3 J4 的 2×TP2 形态；G1 默认 6+2 得 1×TP2（与此前实际拓扑相同），G2 4+4 得 2×TP2，覆盖 4 得 1×TP4 |
| P11(d) | 整除检查 + `[ "$ENGINE_COUNT" -eq 1 ] \|\| die` | 正整数（`case` 非数字即 die）、≥ 1、≤ `ROLLOUT_GPUS`（单节点，engine 不跨出 rollout 卡集）、整除、`ENGINE_COUNT ≥ 1`；不再限制 engine 数 |
| P11(c) `--sglang-config` 拒绝 | 措辞"V3 钉死单模型单 engine" | "首训钉死单模型 regular worker（engine 数只由 `--rollout-num-gpus-per-engine` 决定）"——PD/多模型入口仍拒绝 |
| 文件头钉死组 / dry-run 拓扑行 / run_manifest | "engine 数钉死 1" | 普通配置；`run_manifest.json.topology.rollout_engines` 记实际值（字段未变） |
| `launch_args.md` §1/§2/§4(d)、`thresholds.md` 拓扑登记、`router_targeting_audit.md` §0 | 单 engine 限制陈述 | W10 语义（见各文件） |
| `g1_acceptance.py` / `postrun_probes.py` / `custom_config.yaml` | 无 engine 数约束 | 未改 |

miles 侧 `arguments.py` 未加整除校验（`rollout_server.py:49` 整数除法仍会静默丢余数卡）：preflight 已挡；且 W4 正在同一文件加参数，避免并发改同一文件（T1-5）。

## 4. 两假 engine 本地反例（`rh2/tests/adapters_miles/test_w10_multi_engine.py`）

替身只有 HTTP 两端，全部走生产 wire（`install_capture_wire` 后的 `rh2_call_sglang_generate`，真 aiohttp 客户端）：`FakeMilesRouter`（真 aiohttp server，镜像 `miles/router/router.py` 的 `/add_worker`、`/list_workers`、catch-all 最小负载选路、进入 +1 / 返回 −1、不读任何业务 header）+ `FakeEngine ×2`（真 aiohttp server：`/generate` 挂起到 rid 被 abort 或显式放行；`/abort_request` 只终止自己持有的 rid，不认识的 rid 记 ignored 并 200；`/model_info` 记录探测命中）。有意不用 `aiohttp.test_utils.TestServer`（它强制 `handler_cancellation=True`，客户端断连会取消 handler，与 uvicorn+httpx / SGLang "断连后请求仍占槽位"的真实行为不符）。

| B-5b 条目 | 测试 | 断言要点 |
|---|---|---|
| 分发到不同 engine | `test_router_dispatches_concurrent_generates_to_different_engines` | 两条并发 `/generate` 分别落 A、B；router 记录 `[(generate, A), (generate, B)]` |
| rid abort 到达持有者 | `test_abort_broadcast_reaches_holding_engine_and_other_engine_ignores` | cancel 后 A（持有者）`aborted == [rid]` 且槽位释放；B `abort_seen == [rid]`、`abort_ignored == [rid]`；router **没有**收到 `abort_request`；stats `abort_broadcast +1`、`abort_delivery_failed +0`；`abort_results[-1]` = broadcast 到 `[A, B]` 全部 delivered |
| **反例：旧路径错发** | `test_counterexample_single_send_via_router_misses_the_holder` | `engine_abort=None`（W10 之前形状）：A 仍持有 rid（router 计数 A=1），最小负载把 abort 送到 B，B 忽略，A 永远没收到（`rid in A.inflight`）；stats `abort_router_single_send +1`，`list_error == "engine_abort_not_wired"` |
| 单 engine 仍正常 | `test_single_engine_pool_still_works_with_broadcast` | `list_workers == [only]`；正常生成；cancel 后广播到唯一 engine，`abort_ignored == []` |
| 版本不猜 | `test_current_version_is_observed_from_engine_replies_not_probed_from_any_worker` | 绑定 `BringupService._observed_current_version` 真实方法体：无观测 → `step_0`；两条 generate 分别由 A（v7）/B（v9）服务并 `registry.commit` 后 → `"9"`；A、B 的 `version_probes == []`，router 只代理过 `generate` |
| | `test_bringup_has_no_router_version_probe_left` | `BringupService` 无 `_latest_engine_version` / `_registry_max_version`；`_observed_current_version.__code__` 不含 `requests`、无以 `/` 开头的常量、只读 `snapshot_weight_versions` / `policy_version`；源码无 `import requests`；接线行在场 |
| 发布到全部 engine（`integration_base`） | `test_publish_convergence_check_queries_every_engine_actor` | 两个 fake actor handle 各被问恰好一次；`converged`；事件 `engine_versions_after_publish` 一条，`versions == ["8","8"]`、`num_engines == 2` |
| | `test_publish_convergence_mismatch_or_dead_engine_stops_the_run[mismatch/unreachable/timeout]` | 一台 v7 / 一台抛错 / 一台超时 → `EngineWeightVersionMismatch`，report 逐台 versions/errors；事件在抛错前落盘且 `converged=false` |
| | `test_engine_version_timeout_env_knob` | 默认 60s；env 覆盖；非正数拒绝 |
| | `test_miles_publish_paths_iterate_all_updatable_engines` | 源码锚定：mixin.py / update_weight_from_tensor.py 的 pause / `update_weight_version` / continue 都对 `self.rollout_engines` 全量迭代；`rollout_engines=[e.actor_handle for e in srv.engines]`；`RolloutServer.engines` = 全部 group 的 node-0 engine；`async def set_weight_version` + `_verify_engine_weight_versions` + `indep_dp` 跳过 |
| | `test_worker_base_urls_mirror_miles_semantics` | rh2 镜像与 miles `router_worker_base_urls` 同规则（`rpartition("@")` + 数字 rank 去后缀 + 去重） |
| W4 接缝 | `test_staleness_threshold_mirror_from_args[4 组]`、`test_staleness_threshold_mirror_rejects_illegal_values[-1/True/"2"/1.5]`、`test_bringup_config_carries_staleness_mirror` | 缺失/None → None；0/2 原值；负数/bool/字符串/浮点 → RuntimeError；`SlimeBindingConfig(staleness_threshold=self.staleness_threshold_mirror)` 在场 |
| launch.sh | `test_launch_script_has_no_single_engine_hard_constraint` | `bash -n` 过；无 `[ "$ENGINE_COUNT" -eq 1 ]`、无"覆盖位已移除"；覆盖位默认 2、整除与 ≤ 检查在场、`--rollout-num-gpus-per-engine "$ROLLOUT_GPUS_PER_ENGINE"` 在场 |

## 5. miles 侧改动清单（供 `git format-patch` 存档为 patch 0015）

integration tree `reference/miles-rh2-integration`（HEAD d66576aea）工作树，**未 commit**：

| 文件 | 改动 |
|---|---|
| `miles/utils/rh2_engine_versions.py` | 新增 121 行：`EngineWeightVersionMismatch`、`EngineVersionReport`（`converged` / `to_dict`）、`engine_version_timeout_sec()`（env `RH2_MILES_ENGINE_VERSION_TIMEOUT_SEC`，默认 60）、`collect_engine_weight_versions(handles, timeout)`（并发 `asyncio.wait_for(handle.get_weight_version.remote())`，逐台记错误不抛）、`verify_engine_weight_versions(handles, expected, timeout=None)`（collect → `rh2_event_log.emit("engine_versions_after_publish", …)` → 不收敛即抛） |
| `miles/ray/rollout/rollout_manager.py` | +23/−1：import；`set_weight_version` → `async def`，末尾 `await self._verify_engine_weight_versions(weight_version)`；新 `_verify_engine_weight_versions`（`_get_updatable_server()` 为 None 或 `args.indep_dp` 跳过；`handles = [e.actor_handle for e in srv.engines if e.is_allocated]`；日志一行） |

建议 commit message：`[rh2-integration] W10: verify weight-version convergence across all rollout engines after publish (patch 0015)`。**注意**：同一工作树里还有 W4 的未提交改动（`miles/rollout/fully_async_data_buffer.py`、`fully_async_rollout.py`、`train_async.py`、`miles/utils/arguments.py`、`miles/utils/rh2_event_log.py`），存档 0015 时按上表两个路径 `git add`，不要整树提交。ruff（miles pyproject 配置）对两文件全过。lane B 的 `test_producer_tree_digest_matches_audit_manifest` 在存档 + manifest 更新（expected_tree / miles_source_tree_digest / patch 表 / expected_counts）之前保持红——预期。

调用面核实：`set_weight_version` 只被 `megatron_utils/actor.py:927` 与 `fsdp_utils/actor.py:648` 经 `ray.get(self.rollout_manager.set_weight_version.remote(...))` 调用，async 化对调用方透明（RolloutManager 本就是 asyncio actor，`probe_and_mark_dead` 已用同款 `await asyncio.wait_for(engine.actor_handle.get_weight_version.remote(), timeout=60)`）。miles 自身 `ci_test` 下的"随机抽一台 engine 核对版本"逻辑（`actor.py:942-948`）未动。

## 6. GPU 验证清单（归 spike/C；matched comparison 记录项）

前置：patch 0015 存档 + manifest 更新 + 双 lane 绿；launch preflight 过。

**A. 两种拓扑各跑一次 G1 最小规模（同模型、同预注册 prompt、同 `--max-weight-staleness N`、`--pause-generation-mode retract`、同 num_rollout / GBS）**：
- 拓扑 1：`RH2_SPIKE_ROLLOUT_GPUS=4 RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE=4`（1×TP4）；
- 拓扑 2：`RH2_SPIKE_ROLLOUT_GPUS=4 RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE=2`（2×TP2，P3 J4 形态）。

**B. 每次 run 记录（多 engine 正确性面，均为一手证据）**：
1. `artifacts/startup_evidence.json` `router_workers.count == ROLLOUT_GPUS / PER_ENGINE`，`urls` 与 engine 自注册地址一致；
2. `rollout_workers` 事件 `worker_ids` 集合大小 == engine 数且跨 step 不变（既有 `g1_sglang_engines_stable_across_steps`）；
3. 分发：各 engine 实际服务过请求（engine 日志 / `router_workers` 对照 `capture` 记录的 `weight_version` 来源；可选：临时读 router `worker_request_counts`）；
4. abort 探针：制造至少一次 cancel/超时（例如缩短一次 `SWE_AGENT_TIME_BUDGET_SEC` 或 proxy deadline），核对 `bringup_events.jsonl`/关停报告里的 `capture_stats`：`abort_requested == abort_broadcast`、`abort_router_single_send == 0`、`abort_delivery_failed == 0`，且各 engine 运行中请求数随后归零（sglang `/get_server_info` 或 metrics）；
5. publish：每次权重更新后恰一条 `engine_versions_after_publish`，`num_engines == engine 数`、`converged == true`、`versions` 全等于 `weight_update.version_after`；
6. retract：`weight_update.duration_seconds`、pause/resume 时间、重算 token 量（既有 F2/W4 事件）；跨 publish 的 turn 在 `rollout_group.weight_version_spans` 有多段区间（既有 `weight_version_spans_coverage`）；
7. mask / R3 tape 入 loss、≥ 2 个有效 optimizer step、checkpoint 存读、eval 冒烟——既有 G1 判定不变；
8. consume-time staleness 分布 / stale 丢弃比例（W4 事件）；吞吐 tokens/s、显存峰值（dmon）。

**C. 决策规则**：两拓扑在 B.1–B.7 全部通过的前提下，按 B.8 的吞吐 / 更新窗口损失选首训 engine 数，结论与所选拓扑一并写入 `thresholds.md` 并重校准 calibrate 组阈值（不得沿用单拓扑校准值）。

**D. 不在本清单**：dead-engine 恢复、`/remove_worker`、缩扩容、FT——任一 engine 死亡 = run 停止，按 B-3 重启后按同清单复跑。

## 7. T1 决策及理由

1. **广播落在 rh2 侧（capture_wire + 新客户端），不改 MilesRouter。** 审计 §5 前置 1 的两个落点里，rh2 侧不动 vendor、与 miles 自身 abort-all 同形；MilesRouter 实现 rid→worker 粘滞表是 B-5b 明示不做的通用粘滞路由。
2. **`capture_wire.py` 被触碰（不在任务书的显式所有权清单，也不在禁改清单）**：abort 的 HTTP 调用点只在该文件，改动限于 except 分支 + registry 挂点 + 记账；未改任何 stage/commit/guard 语义。
3. **worker 列表取不到时退回 stock 单发而不是放弃 abort**：abort 是尽力释放槽位，放弃比错发更差；退化路径显式记 `mode="router_single_send"` + `list_error`，不静默。
4. **finalize/proxy 的 current 版本 = capture 观测最大值（原 bring-up 降级路径），不再问任何 engine。** 理由见 §2；`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下原"双端点全灭 fail-closed"分支随探测一起消失——它保护的是"用历史观测冒充 current"，而现在 current 的定义就是观测上界，且资格门已不在 finalize。
5. **miles 版本收敛核对：不一致/不可达即抛（停 run），不是 warning；超时旋钮走 env 而非新 CLI 参数。** 抛错 = B-5b "任一 engine 死亡 = 停 run"的同一语义；W4 正在 `arguments.py` 加参数，避免并发改同一文件，且 env 旋钮与 `rh2_shutdown.py` 的既有旋钮同风格。
6. **`engine_versions_after_publish` 事件在抛错之前落盘**：不收敛的事实必须留证；judge 暂不消费（开放问题 3）。
7. **launch.sh per-engine 默认 2**：= P3 J4 正式链的 2×TP2；G1 默认 6+2 的实际拓扑不变（1×TP2）；G2 4+4 从此前的 1×TP4 变为 2×TP2——这是有意的语义变化，matched comparison 两种都跑。
8. **startup_evidence `router_workers` 取不到只记错误、不阻断启动**：启动探针已证明至少一个 worker 可达；非 MilesRouter 部署（无 `/list_workers`）不应因证据项启动失败。
9. **测试 oracle 改动登记**：删除 `test_bringup_weight_version_probe.py`（4 例：仅新端点 / 仅旧端点 fallback / 双灭 fail-closed / 双灭降级）——被测方法整体删除；其"降级语义"（registry 最大观测 → 启动探针值）由新测试 `test_current_version_is_observed_from_engine_replies_not_probed_from_any_worker` 覆盖。
10. **replace-only 纪律**：全部源码改动经"old 片段恰好出现一次"的替换脚本落地（review-standards §7 文本替换带 assert）。

## 8. 开放问题

1. **engine 数**：由 GPU matched comparison 决定（§6 C），不在本包结论。
2. **`/remove_worker`**：MilesRouter 无该路由，engine `shutdown()` 经 router `POST /remove_worker` 会落 catch-all → SGLang 404 → `raise_for_status` 抛错（审计 §3 登记）；只在 FT / `stop_cell` / 健康恢复路径触发，首训无 FT。首版不做，登记为残余。
3. **judge 消费**：`engine_versions_after_publish` 事件尚无 g1_acceptance.py 判定键；GPU 清单 B.5 手工核对。是否升为 judge 键（`engine_versions_converged_after_publish`）待 spike/C 定（增判定 = T1，改阈值表 = 按 thresholds.md 纪律）。
4. **manifest / patch 0015**：由集成者存档并更新 `integration_base_manifest.json`（新 patch 表、expected_tree、miles_source_tree_digest、expected_counts）；在此之前 lanes 前置校验与 `test_producer_tree_digest_matches_audit_manifest` 保持红（预期）。
5. **并行 agent 的在途改动**（非本包）：默认全套里 `tests/contracts/test_f2_2b_b3_hygiene.py::test_e2e_test_tampering_is_permanent_rejection_no_grader` 红（W3a D2-3 正在改"改测试文件 = 永久拒绝"的旧 oracle；`generate.py`/`grading/*` 有未提交改动）；lane B 里 `test_w4_consume_time_staleness.py::test_jit_drain_with_zero_limit_drops_pre_publish_groups_instead_of_training_them` 红（W4 在途）。两者与 W10 文件无交集。
6. **finalize-time lag 观测偏小**：见 §2 说明；若 spike 需要"相对已发布版本"的 lag 观测，可由 W4 把 buffer 的 `current_published_rollout_weight_version` 挂到 args 供 bringup 读——不是资格语义，属遥测改进。

## 9. 测试 / 证据 / 账本状态（2026-09-04 实跑，工作树 = `b007c0d9` + 本包与并行包的未提交改动）

| 命令 | 结果 |
|---|---|
| `RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/test_w10_multi_engine.py -q` | **23 passed** |
| `uv run pytest tests/adapters_miles/ -q`（lane A，pin base） | 339 passed / 277 skipped；`-m "not integration_base"` → 339 passed / 0 skipped（skip 全部为 integration_base 豁免） |
| `RH2_MILES_PATH=… uv run pytest tests/adapters_miles/ -q`（lane B） | 614 passed / **2 failed**：树 digest 测试（集成树不干净，预期）+ W4 在途测试（开放问题 5） |
| `uv run pytest tests/ -q --deselect tests/adapters_miles`（默认全套其余部分） | 1258 passed / 15 skipped / **1 failed**：W3a 在途 oracle（开放问题 5） |
| ruff：`bringup.py` / `capture_wire.py` / `engine_router_client.py` / `test_w10_multi_engine.py`；miles `rh2_engine_versions.py` / `rollout_manager.py`（miles pyproject 配置） | 全过 |
| `bash -n launch.sh` | 过 |
| `miles_integration_lanes.sh` 前置校验 | 未跑通（集成树不干净——预期，待 patch 0015 存档） |

W10 归属的计数变化（以 manifest 当前 322/232、554/0 为基线，不含 W4 在途新增）：lane A **+12 passed / +7 skipped**（新 16 passed + 7 integration_base skipped − 删 4）→ 334/239；lane B **+19 passed** → 573/0。当前观测总数（含 W4 在途）：lane A 339/277，lane B 616 例（614+2）。

---

## 收尾五段

**① 待拍板 T0**：无。本包未改训练样本准入 / reward / loss / 算法语义，未改公共 schema、协议或唯一事实来源（contracts/ 零改动），未改跨组件状态所有权或崩溃恢复语义，未新增拒绝路径，未降低安全边界，未引入依赖。

**② T1 决策及理由**：§7 十条。

**③ 临时挡板新增 / 命中 / 解除**：新增无；bringup 挡板未动（任务书所指 HEAD 705-713 区间内容未动；fa_formal 暂禁块 HEAD 778-787 → 现 819-829 逐字未动）；lanes 前置校验因集成树不干净红——预期，非挡板。abort 的"未接线退回单发"是显式记账的退化路径，不是挡板。

**④ 推翻或修正了哪些旧结论**：router_targeting_audit.md §5 前置 1/2 由"开放"改"已关闭"，3/4/5 改"首版不做"（B-5b 裁定），6/7 待 GPU；thresholds.md "rollout engine 数钉死 1 … 任何多 engine 配置 = 换实验（T0 级）"整段作废；launch_args.md / launch.sh 的"钉死 1"陈述作废；V3 收尾两小项里"`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下双端点全灭 fail-closed"的探测语义随探测删除而消失（T1-4）。

**⑤ 测试 / 证据 / 账本状态**：§9。

**本轮没有改变哪些已定案语义**：B-1 consume-time 唯一权威与叶版本绑定 / 负 lag FATAL；B-2 drop；B-3 最小冷恢复合同；B-4 `update_weights_interval=1`；B-5a `retract`；gate 第七维"版本事实可用且合法"与 `GATE_VERSION`；contracts/ 全部 schema；`generate.py` / `grading/*` / `governance/*` / `envpack/*` / vendored slime；miles buffer / rollout fn / train_async / event log（W4 所有）；MilesRouter 选路语义本身（仍最小负载、仍忽略 routing key——只是不再承载 abort 与版本探测两类正确性请求）。
