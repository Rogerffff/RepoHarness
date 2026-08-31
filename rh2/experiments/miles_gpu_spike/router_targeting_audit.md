# miles router 定向审计（V3 vendor refresh 第三批）

> 目的：`--use-miles-router` 启用后（#2596 fail-closed 强制，top_p<1 前提），逐端点
> 判定 rh2 请求平面在**单 engine** 下的行为正确性，以及 **≥2 engine** 时的错发面；
> 给出多 engine 解锁前置清单，供实验设计轮决策。
> 方法：只读代码审计。rh2 侧 = `rh2/src/repoharness2/adapters/slime/capture_wire.py`
> 与 `bringup.py`；miles 侧 = integration tree `reference/miles-rh2-integration`
> （分支 rh2-integration-v3，树 digest 以 miles_spike/integration_base_manifest.json
> 钉死）。所有行号取自该树当前 HEAD，树 digest 变更时本文件行号须复核。
> 结论一句话：**单 engine 首枪全部端点安全（一处 FT 路径缺口不在 G1 执行面）；
> 多 engine 在 abort/版本探测两处有真实错发面，解锁前置清单见 §5。**

## 1. 请求平面拓扑（谁经过 router，谁不经过）

rh2 侧经 router 的 HTTP 调用点恰有 3 个（`adapter.sglang_url =
http://{args.sglang_router_ip}:{args.sglang_router_port}`，bringup.py:662——
`use_miles_router` 下该地址就是 MilesRouter）：

| 调用点 | 代码位置 | 语义 |
|---|---|---|
| `POST /generate` | capture_wire.py:971-973 | 每 turn 的采样请求（顶层 `return_sampling_mask`、逐 attempt 唯一 rid） |
| `POST /abort_request {"rid": ...}` | capture_wire.py:979-985 | cancel/超时后释放引擎槽位；**异常整体吞掉**（984-985 `except Exception: pass`） |
| `GET /model_info`（fallback `GET /get_weight_version`） | bringup.py:1036-1042 | finalize 时刻的权威 current 版本，双端点探测先新后旧（V3 审计移交收口，见 §3 已收口条目；顺序对齐引擎侧 sglang_engine.py:578）；`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 时双端点都失败即 fail-closed（1044-1049），并与 capture registry 最大观测交叉检查（1050-1058：registry_max > authoritative ⇒ RuntimeError） |

rh2 还随 `/generate` 发送 `X-SMG-Routing-Key: <session_id>` 头
（capture_wire.py:957-959），意图是会话粘滞路由。

**不经 router** 的控制面（多 engine 判定时不受路由影响）：

- 权重更新的 pause/flush/continue 与参数传输走 Ray actor 句柄直达每个 engine
  （update_weight_from_distributed/mixin.py:314-331 等），与 router 无关。
- miles 自己的 rollout abort（非 rh2 路径）在 `use_miles_router` 下是
  "问 router `/list_workers` 拿全部 worker URL，然后**绕过 router 逐 worker 直发**
  `{"abort_all": true}`"（sglang_rollout.py:413-427、
  inference_rollout_train.py:31-32 + get_worker_urls）——上游对定向问题的既有
  回避模式，见 §5 前置 1。
- engine 注册：每个 engine 起动后向 router `POST /add_worker?url=...` 自注册
  （sglang_engine.py:317-323）；engine 关停向 router `POST /remove_worker?url=...`
  （sglang_engine.py:542-545，之后 `response.raise_for_status()`）。

## 2. MilesRouter 转发逻辑（miles/router/router.py，v3 树）

- 显式路由只有两个：`POST /add_worker`（:68）、`GET /list_workers`（:69）；
  其余**一切路径**落 catch-all `/{path:path}`（:71）→ `proxy` → `do_proxy`。
- `do_proxy`（:134-162）：先 `worker_url = self._use_url()`（:142）选 worker，
  再把原始 body 与 headers 原样转发（:153 `content=body`，仅剥
  content-length/transfer-encoding）。**选择发生在读任何业务 header 之前，
  且选择逻辑从不读 header。**
- `_use_url`（:215-230）：`min(self.worker_request_counts, key=...)` 纯最小
  活跃请求数；无任何 policy 机制。
- **X-SMG-Routing-Key 被忽略的证据**：router.py 全文不含该字符串（全文 251 行，
  可 grep 复核）；选择函数 `_use_url`（:215-230）只消费
  `worker_request_counts`/`dead_workers`。对照：该 header 的正牌消费者是
  sgl-router 的 `consistent_hashing`/`manual` policy
  （miles/rollout/generate_utils/generate_endpoint_utils.py:38-50
  `policy_uses_routing_key`），MilesRouter 没有对应实现。因此 rh2
  capture_wire.py:957-959 发出的路由头在 MilesRouter 下是死字节。
- 健康检查（:87-127）：每 `rollout_health_check_interval`（默认 30s，
  arguments.py:949-952）对全部 worker GET `/health`；连续
  `miles_router_health_check_failure_threshold`（默认 3）次失败 → 加入
  `dead_workers`（:111）永久隔离——**没有回池机制**（:112-114 上游 TODO）。
  全部 worker dead → `RuntimeError("No healthy workers available")`（:227）。
- 就绪判据：`wait_for_server_ready` 只测 TCP 连通（http_utils.py:45-64），
  0 worker 的 router 也算 ready。顺序安全性：engine 在 rollout server 构造期
  就 add_worker 自注册，而 rh2 的首个 `/generate` 出现在首个样本的惰性
  bootstrap 之后——先注册后请求，不存在空池窗口（若倒置，`min({})` 会抛
  ValueError → 500，属显性失败而非错发）。
- 转发对 mask 的透明性：catch-all 按原始 body 转发，`/generate` 顶层
  `return_sampling_mask` 旗标与响应体（含 `meta_info.weight_versions` spans）
  均不被改写——#2596 所述"model gateway 丢 mask"的问题面在 MilesRouter 代理
  平面不存在。

## 3. 单 engine 判定（worker 池恒 1 元素——launch.sh 钉死 per-engine := 全部 rollout 卡）

| 端点 | 单 engine 行为 | 判定 |
|---|---|---|
| `/generate` | `_use_url` 的 min 集合只有唯一 worker，恒中；body/响应原样 | **安全**（mask/spans 完整） |
| `/abort_request {"rid"}` | 恒转发到持有该 rid 的唯一 engine | **安全**（语义精确） |
| 版本探测（`/model_info`，fallback `/get_weight_version`） | 两端点均落 catch-all 转发，恒查询唯一 engine = 权威版本源；bringup 交叉检查（registry_max ≤ authoritative）不可能因路由产生假红 | **安全** |
| `/add_worker` | 唯一 engine 注册一次 | **安全** |
| `/remove_worker` | **MilesRouter 无此路由**：落 catch-all 被转发给唯一 worker，SGLang server 无此端点 → 404 → `shutdown()` 内 `raise_for_status()` 抛 HTTPError | **G1 不受影响**（缺口不在执行面，见下） |

`/remove_worker` 缺口为什么不影响 G1 首枪：正常收尾链
`train_async.py:186 → rollout_manager.dispose()`（rollout_manager.py:136-145）
**不调用** engine shutdown；`stop_engines`（ray/rollout/server_group.py:202-213）
只在 FT/`stop_cell`/健康监控恢复路径触发，且异常被 `except Exception` 吞成
warning。副作用要登记：吞掉异常的同时 `ray.kill(engine)` 也被跳过（在同一
try 块内、raise 之后），engine actor 残留——G1 未启用 FT（launch 钉
`MILES_EXPERIMENTAL_FT_TRAINER` 不设），不会走到；多 engine/FT 解锁前必须修
（§5 前置 4）。

单 engine 残余风险（显性、非错发，如实登记）：

- **唯一 worker 永久隔离**：engine 连续 3 次 `/health` 失败（30s 间隔）后进
  `dead_workers` 且永不回池 → 之后所有请求 `RuntimeError` → rh2 侧
  `sglang upstream 5xx` → turn 失败，fail-closed 显性熔断，不产生静默坏数据。
  权重更新的 pause 不关闭 `/health`（server 层端点），常规更新窗口预计不触发；
  真正卡死 90s+ 的 engine 本来也该停。接受为可观测残余风险。
- **`/get_weight_version` 端点更名风险（与 router 无关但同一调用点）——
  已收口（2026-08-31，src 线程移交完成）**：gh api 核实钉死
  SGLANG_COMMIT=4e230c3d 的 http_server.py 真实路由——旧端点
  `/get_weight_version`（含别名 `/weight_version`）**路由仍注册但 handler
  无条件抛 HTTPException(404 deprecated)**，比登记时预估的"可能已移除"更
  确定：单端点探测对钉死引擎必然 404，不是概率风险；current 版本改由
  `/model_info` 返回体的 "weight_version" 键承载
  （= tokenizer_manager.config_value("weight_version")，权重更新成功即推进，
  与旧端点同一事实源）。修复：bringup.py:1036-1042 探测改为引擎侧
  sglang_engine.get_weight_version 同款"先 `/model_info` 后
  `/get_weight_version`"双端点 fallback；
  `RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下双端点都失败仍 fail-closed。单测
  tests/adapters_miles/test_bringup_weight_version_probe.py（真回环 HTTP）
  钉死仅新端点/仅旧端点各通过、双灭拒绝、bring-up 降级语义四形态。

## 4. 多 engine（≥2 worker）错发面

| 端点 | 错发行为 | 后果定级 |
|---|---|---|
| `/generate` | 每 turn 独立最小负载选 worker，会话跨 turn 在 engine 间漂移 | **数据仍正确**：mask/logprob/`weight_versions` spans 由真实服务该请求的 engine 打，逐响应自洽。代价是 radix/KV 前缀局部性全失（纯性能），以及把 abort 与 generate 的 worker 解耦（见下）。若未来权重更新选 `in_place`，#2783 的旧权重 KV 复用问题按 engine 数扩面 |
| `/abort_request {"rid"}` | 与当初服务该 rid 的 worker 解耦：命中概率 ≈ 1/N。错发 = SGLang 对不认识的 rid 静默无操作，router 照样 200，rh2 侧本就吞异常（capture_wire.py:984-985） | **静默失效**：被放弃的生成继续占 engine 槽位与算力直至自然完成。放大面：capture wire 的 cancel/超时 abort 与 proxy 更新窗口 abort 全部失准 → 容量泄漏、延迟堆积、deadline 超时增多 → degraded 样本（reward=0 + remove_sample）比例上升。属资源/证据噪声，非系统性样本偏置（丢弃与内容无关），但吞吐/latency 阈值证据会被污染 |
| 版本探测（`/model_info`，fallback `/get_weight_version`） | 查询到任意 worker。稳态各 engine 版本一致时结果正确；**更新窗口竞态**：capture 已从某个已更新 engine 观测到新版本，而探测命中未更新 engine → `registry_max > authoritative` → bringup.py:1050-1058 把瞬态偏斜判成"版本管道错乱" RuntimeError（fail-closed 假红崩溃）。反向（探测到新、观测旧）则 staleness 分母被抬高，交叉检查不拦 | **假红崩溃面**（方向安全但可用性差）；单 engine 下结构性不存在 |
| `/remove_worker` | 错发 + 无路由双重问题（§3）；被停 engine 残留在池中直到健康检查隔离（最长 interval×threshold ≈ 90s），期间 min-load 仍可能把 `/generate` 发给已死 worker → httpx 连接错误 → 500 → turn 失败 | FT/弹性回收路径不可用 |
| 健康隔离 | dead worker 永不回池 → 容量单调衰减；N-1 台 dead 仍可服务 | 弹性缺失，显性 |

## 5. 多 engine 解锁前置清单（关闭全部条目并留痕后，才可撤 launch.sh 的
engine=1 钉死与 preflight P11(d) 断言；逐条都有代码锚点，供实验设计轮排期）

1. **abort 定向或广播**：最小改动 = 仿上游自身模式（§1：router `/list_workers`
   拿全量 worker，逐 worker 直发 `{"rid": ...}`——SGLang 对未知 rid 静默忽略，
   rid 级广播幂等安全）；或给 MilesRouter 实现 rid→worker 粘滞表 / 按
   `X-SMG-Routing-Key` 定向。改动落点二选一：rh2 capture_wire（广播）或
   miles router（定向），前者不动 vendor。
2. **版本探测去任意化**：版本探测（`/model_info`，fallback
   `/get_weight_version`）改为逐 worker 查询并断言全等（不等 = 更新窗口，
   重试或 fail），或 bringup 改走 engine actor API `get_weight_version()`
   （sglang_engine.py:573-582，绕 router）。归 rh2/src 线程；双端点 fallback
   已落地（§3 已收口条目），逐 worker 全等断言仍未做——本项在多 engine 解锁
   前依旧开放。
3. **会话粘滞路由**：`X-SMG-Routing-Key` 一致性路由要么在 MilesRouter 实现，
   要么换 sgl-router `consistent_hashing` policy——后者当前不可选：#2596 的
   前提正是 model gateway 不转发 `return_sampling_mask`（arguments.py:2942-2948
   TODO 注明 gateway 转发落地后才移除强制）。此项只影响 KV 局部性/性能，
   不是正确性硬前提（spans/mask 逐响应自洽）。
4. **`/remove_worker` 路由 + stop_engines 修正**：MilesRouter 实现 remove；
   `server_group.py:202-213` 的 `ray.kill` 不应因 shutdown HTTP 错误被跳过
   （上游候选修复）。FT/弹性恢复解锁前提。
5. **dead worker 回池**：上游 TODO（router.py:112-114，需版本同步机制）。
   无此项时多 engine 容量单调衰减，长跑不可接受。
6. **阈值重校准**：`throughput_min_tokens_per_sec` 等 calibrate 组绑定
   engine 拓扑（1×TPn vs m×TPk 不可直接对比），解锁时重校准并按 thresholds.md
   纪律留痕。
7. **上卡验证探针**：多 engine abort 探针（故意 cancel 后核对各 worker 运行中
   请求数归零）、更新窗口版本探测（`/model_info`）竞态探针（并发轮询断言无
   registry_max > authoritative 假红）。

## 6. 与 launch/preflight 的对应关系（本轮已落地）

- launch.sh：`--use-miles-router` 显式进 SGLANG_ARGS（一等 CLI 旗标层）；
  per-engine := rollout 卡数 ⇒ engine 数恒 1（topo 注释）；旧
  `RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE` 覆盖位作废（设了即红）。
- preflight P11：(a) top_p<1 ⇒ router 旗标在场 + top-k 正有限 + 无
  `--recompute-logprobs-via-prefill`（miles_validate_args 同判据，
  arguments.py:2931-2948）；(b) qkv_format 非 thd 即红（#2798 未吸收）；
  (c) PD 两入口（`--prefill-num-servers`/`--sglang-config`）即红（#2596 撤销
  PD mask 支持 + router_manager.py:41 assert）；(d) engine 数恒 1。
- thresholds.md：拓扑限制登记节（散文，不加无消费者的 json 键）。
