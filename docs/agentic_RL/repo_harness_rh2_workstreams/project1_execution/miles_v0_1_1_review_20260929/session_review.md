# miles v0.1.1：Session / Agentic 的替代与简化边界

日期：2026-09-29。角色：review-standards §10.4 Falsifier / Simplifier。结论性质：只读源码审查、有限 CPU 反例与已有真实请求交叉；不是实施、端到端验收或新训练决策。

## 结论

**不能直接用 v0.1.1 SessionCore 替换当前 CC + RH2 捕获链。建议升级训练底座与替换捕获层分开：本批保留现有捕获层；新 session 能力作为有条件的组件来源。** 不应因为上游已有新服务而重造服务，也不应因功能名称相似就删除已有边界。

最直接的反证来自现有请求：22 条 Qwen3.6 基座尝试的 **617/617 个生成请求**含 `thinking={type:adaptive}` 与 `output_config={effort:high}`；修后正式启动参数的 CC 2.1.205 + 剧本引擎验收留存的 **3/3 个请求**也含两字段。上游新 Anthropic route 明确拒绝它们。上游默认 picker 还会删除相同 prompt 的早次真实采样输出，而 I01 B 保留它。

上游的真实收益也应保留：v2 已有分支森林、压缩多段样本、共享动作唯一 loss 归属、sampling-support 运输、逐调用版本 span、分离的请求参数管线，以及评测关闭 replay、abort 拒绝、客户端解码移出事件循环。它们可以减少未来实现量，**但不自动解决 CC 请求兼容、I01 B、I18、执行身份、预算、清理和可信评分边界**。

## 范围与证据

- 上游 tag：`v0.1.1`，`2806267d060d51b1d3b62f85a1f9b145047aeef9`；本批只读快照中的 24 个重点文件逐字节核对 tag 一致。
- 当前 RH2：`a31cdcd0adb0fab3e681201edfb928653fdf5b3c`；miles fork：`275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`。文件哈希见 [session_sources.json](../../../../../runs/miles_v0_1_1_review_20260929/session_sources.json)。
- 已读当前 [A 线状态](../a_line_status.md)、[I01 决定](../decision_batches_20260908.md)、[I01 TITO 讨论](../i01_options_20260908/miles_tito_followup.md)、[I18 / I19 决定](../batch3_training_signal_20260909/README.md)、[I19 Brief](../batch3_training_signal_20260909/i19_impl_brief_20260910.md)、[基座链路修复 Brief](../base_probe_chain_fixes_20260923/brief_conditions_6_8_9_10_20260924.md)。I01 B 已批；C 暂缓、不专排 B/C 对比实验；I18 仍未定；I19 恢复正常压缩已实施。
- 本轮证据：[探针脚本](../../../../../runs/miles_v0_1_1_review_20260929/session_probe.py)、[结果](../../../../../runs/miles_v0_1_1_review_20260929/session_probe_result.json)。从仓库根运行：`rh2/.venv/bin/python runs/miles_v0_1_1_review_20260929/session_probe.py`。
- 未安装依赖；本机缺 fastapi / SGLang，所以未跑上游 HTTP 测试。Anthropic validator 是 AST 提取未修改的生产函数；picker、postprocessor、sampling validator、vendored TrajectoryManager 是直接 import。没有模型、GPU、远端或新 CC 作业。

## 真实生产路径

上游生产入口确实接入下列调用链，不只是未接线的 helper；本轮未作真实服务端到端验收：

```text
--use-session-server [v2]
  → ray/specs/inference.py:83–114 创建独立 session worker 进程
  → session/server.py:33–48 → setup_session_routes
  → POST /sessions/{id}/v1/messages
  → Anthropic schema / feature validation → SGLang Anthropic→OpenAI 转换
  → SessionCore[v2].chat_completions
  → prepare request args + TITO input_ids → backend /v1/chat/completions
  → 从 choice.meta_info 提取真实 output ids / logprobs → commit
  → POST /sessions/{id}/samples
  → per-leaf assemble / truncate / picker / postprocessor / safetensors
  → OpenAIEndpointTracer.collect_samples → agentic_tool_call.generate
```

调用者必须选 `miles.rollout.generate_hub.agentic_tool_call.generate` 或自行使用 tracer；只有升级依赖不会让 RH2 自动走这条路。当前正式 launcher 仍选 `repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn`（`rh2/experiments/miles_gpu_spike/launch.sh:445`），其共享 adapter 在 [bringup.py](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py) 1300–1350 行按顺序装 capture / turn-budget / count / parse wire，构造 `Rh2AnthropicAdapter`，再绑定 capability guard。

当前 CC `/v1/messages` 在 [vendored common.py](../../../../../rh2/src/slime/agent/adapters/common.py) 318–390 行：预处理 → 翻译 → **本次请求完整渲染** → `/generate` → 原始 output ids 解码/解析 → flush → `record_turn`。RH2 在 record 接缝提交 capture 身份及原始 tape，最后由 I01 B 装配 / 投影 / miles 适配消费。新 session 则在返回 HTTP Response 前 commit；Anthropic 事后转换失败也保留 record（`sessions.py:219–223`），不是现有 flush 后提交语义的直接替代。这里没有证明任一方案能证明客户端实际消费，只确认提交时点不同。

源码入口：[session server](../../../../../runs/miles_v0_1_1_review_20260929/upstream/miles/rollout/session/server.py)、[routes](../../../../../runs/miles_v0_1_1_review_20260929/upstream/miles/rollout/session/sessions.py)、[v2 core](../../../../../runs/miles_v0_1_1_review_20260929/upstream/miles/rollout/session/v2/core.py)、[agentic generate](../../../../../runs/miles_v0_1_1_review_20260929/upstream/miles/rollout/generate_hub/agentic_tool_call.py)。

## 能承接什么，不能据此推出什么

| 需求 | 上游真实能力与限制 | 对 RH2 的裁定 |
| --- | --- | --- |
| 实际采样 token、logprob | `core.extract_completion:166–200` 从 `output_token_logprobs` 取 token id，校验条数；`samples/merge.py:108–132` 用记录的 `input_ids` 与真实输出组样本。不是从 CC 文本重编码采样动作。 | 能力成立。但依赖匹配的 SGLang meta_info，且经过 picker/truncate 后未必保留每个已采样动作；不等于现 capture 身份 / sink / flush 接缝等价。 |
| thinking | 历史 assistant thinking 可转换回 `reasoning_content`；Qwen3.5/3.6 固定模板强制 `preserve_thinking=True`。新请求的 `thinking`、`output_config` 仍被拒。 | **历史保留与请求配置兼容是两件事。** 固定模板还会改变未来模型输入；不是已经授权的 #6(a)“仅将特定提醒并入 tool_result”替换件。 |
| 压缩 / I19 | v2 不匹配历史时可开新 root/branch；每条 kept leaf 组样本，postprocessor 为共享动作指定唯一 loss owner。v1 最多回退 1 个 assistant checkpoint，且回退裁掉 records。 | v2 有正确方向的现成结构；v1 不适合直接承接任意 CC 压缩。v2 也不负责触发 CC 压缩、窗口 env 或真实 count；长输出 `finish_reason=length` 的路径在 v2 禁止继续扩展，返回 409。 |
| subagent | v2 并发请求以先选好的 parent 提交 sibling，不像 v1 的并发响应可能因 `num_assistant` 改变而跳过记录。不同 prompt 的 root 默认保留。 | 可承接通用分支；没有 CC 子代理身份 / budget / reward 独立语义。当前正式工具面为五工具，Task/Subagent 不在面内，故这不是本批必须迁移的能力缺口。 |
| I01 B 精确前缀分行 | v2 以 message matcher 找 parent，后续请求复用 parent 原 token 快照；Qwen 固定模板保留 thinking；默认 picker 删除相同 prompt 的较早叶。 | **不等价。** B 只在真实 token 精确前缀时合行，漂移保留旧行且不改变推理输入；TITO 是在线构造未来输入的 C 类选择。identity picker 可解决“删旧叶”，不能解决输入语义差异。 |
| I18 逐动作路由与版本 | 非 retract 用增量 R3（路由记录）patch；retract 仍取每轮全量 R3，合并时最终 `b.rollout_routed_experts` 覆盖。另有逐调用 `WeightVersionsPerCall`。 | 非 retract 改进跨轮传输 / 来源保留；**没有统一解决每次行为 forward 的路由来源**。版本 span 是版本账，不是对应历史动作的路由证明；I18 不能因此标完成。 |
| bounded sampling | `request_args` 填会话采样默认值、锁训练温度；`sampling_mask.py` 校验有限 top-k、非空支持集及 sampled token 在支持集内；组装/codec/训练字段均存在。 | 可继续使用上游底座，但 RH2 已有 #2595/#2596 对应捕获与装配；不是本次首次获得。v0.1.1 支持 top-p=1、top-k>0，现 RH2 validator 仍只接受 0<top-p<1 且请求 k 不超过会话 k，不能直接互换 validator。 |
| 身份、预算和 400 / count_tokens | session UUID 和 routing key 存在；本包未实现 RH2 execution/physical-attempt/capability、总 deadline、turn budget。上游非 200 直接不记录并透传；count_tokens 落入通用 proxy。 | 不可删 RH2 owner。上游代理可能接到 backend 的 count 实现，但本批没有证明它与 TITO 生效参数、RH2 特定预处理同路；也未证明其溢出错误触发 CC 的既有恢复逻辑。 |

bounded sampling 还有明确使用边界：`arguments.py:2871–2893` 要求 top-p 截断配正 top-k，不与 prefill 重算、reference KL 或 OPD 同开。这里是已有上游契约事实，不替用户定新配方。

## 三个迁移反例与最小修法

这些是**替换提案的阻塞条件**，不是当前生产链已出现的新 P0/P1；新 session 尚未接入 RH2。

### S1：正式 CC 请求仍不被新 Anthropic 入口接受

- **当前行为 / 不变量：** 新入口先校验 feature，再调用 core；未改变 CC 作业条件的替换必须接受现有请求面。`anthropic_adapter.py:82–86` 拒绝任何非 None 的 `thinking` 与 `output_config`；65–79 行拒绝 `is_error=true` 工具结果。
- **证据：** 617/617 历史生成请求带上述两项；374/617 带至少一个历史 `tool_result.is_error=true`；595/617 带历史 thinking。计数按请求，历史块会重复，**374 不是独立工具失败次数**。另有修后 CC 2.1.205 三请求正交叉。精确路径、首个行号和哈希在 [结果](../../../../../runs/miles_v0_1_1_review_20260929/session_probe_result.json) 的 `corpus`。原函数探针对 thinking/output_config/is_error 均抛 `ValueError`；`sessions.py:157–180` 将此转为 Anthropic 400。
- **影响 / 分布：** 原样切换会在真实已观察请求上失败；只删 thinking 字段仍会撞 output_config，二者都删后还可能拒绝普通工具失败历史。若把这些失败当任务负例，会污染 reward；若丢弃，会系统性剔除遇到工具错误的轨迹。历史样本的发生率不能外推新正式作业。
- **分期 / 最小方案：** 当前保留 RH2 Anthropic adapter；若以后采用新 session，只做一层窄的兼容转换并证明语义，不改 CC 任务工具面来掩盖不兼容。不将本轮没出现的 image/tool_reference/betas 等条件性差异升级为当前故障。
- **验收：** 原样回放这批请求及修后请求面，证明参数处理、thinking / tool_result 语义、实际送入引擎的 input_ids、400/压缩恢复与预算归属。本文 CPU validator 不代替该 HTTP / CC 验收。

### S2：默认 picker 删除已采样动作，TITO 同时改变后续输入

- **当前行为 / 不变量：** `arguments.py:2498–2509` 默认 `drop_same_prompt_retries`；[picker](../../../../../runs/miles_v0_1_1_review_20260929/upstream/miles/rollout/session/v2/picker_hub/drop_same_prompt_retries.py) 7–13 行调用按 sibling + prompt 判定的删除。I01 B 则要求漂移/重写不清除旧真实动作，每个保留动作唯一归属。
- **证据 / 复现：** 本轮直接调用上游 picker/postprocessor 与 RH2 vendored `TrajectoryManager(fork_threshold_tokens=0)`：同 prompt 两次真实输出 `[3]`、`[4]`；默认上游仅训练 `[4]`，RH2 B 训练两者。identity picker 后上游也能保留两者。结果见 `picker`。TITO 的另一差异在 `v2/session_state.py:119–150`：parent 非空就复用其 token；`tito_tokenizer.py:429–452` 为 Qwen3.5/3.6 强制保留 thinking；现 RH2 `common.py:341–342` 完整重渲染当前请求。
- **影响 / 分布：** 默认丢叶减少重试、长度受限、反复修正等动作信号，不是纯去重。TITO 可能减少重复训练前缀、改善 KV 复用，也会改变后续上下文长度与行为；没有 GPU 吞吐或成绩证据，不能保证净收益。
- **分期 / 最小方案：** 本批沿用 B。未来若重开 C，复用已有进程内 tokenizer/matcher，保留 B 作为不匹配时的行保留策略；若直接用 v2，先用 identity picker，不另造森林或新的 picker 状态机。**不因本轮 review 启动已经暂缓的专门 B/C 实验。**
- **验收：** 对输入变更明确批准的合同，逐动作核对实际 prompt/output/logprob、mask 唯一 owner、重试叶保留；压缩前后、同 prompt 重试、JSON 表示变化分别有反例。不能用“返回多条 Sample”或“没有 mismatch 报错”代替动作守恒。

### S3：新 session 的身份和通用 proxy 不承接 RH2 执行边界

- **当前行为 / 不变量：** `sessions.py:237–247` 把任意剩余 path 交给 `core.proxy`；`core.py:428–435` 仅附 `X-SMG-Routing-Key` 后转发，**不查询 session registry，也不做 RH2 capability / execution / deadline / budget 校验**。Session create/delete/sample 路由也无此层认证。当前 RH2 [session_capability.py](../../../../../rh2/src/repoharness2/adapters/slime/session_capability.py) 1–19 行区分稳定执行身份、attempt sid 与秘密 capability；`bringup.py:1346–1350` 真接 guard。
- **证据 / 复现界限：** 源码沿 route→proxy 与当前 bringup 追踪；本轮没有对外暴露服务或执行越权请求。这是把上游监听面直接交给现有 sandbox 时的条件性契约差异，不是宣称上游在所有部署都不安全。
- **影响：** 不能把 session URL / UUID 当现 RH2 凭证；简单更换 endpoint 会绕过预登记身份、预算与 capture 归属要求。delete 只移除 session 数据，不等于现有 rid abort、inflight 交付、容器/模型调用收尾和持久 finalization 都完成。
- **分期 / 最小方案：** 保留现可信入口和 owner；如未来迁移，只对已认证 attempt 暴露所需模型 API，create/collect/delete 仍由可信编排器调用，封住通用 proxy 的未授权入口。复用现有 guard，不再造一套 execution ledger。
- **验收：** 用未知/关闭/旧 attempt capability、并发预算命中、取消与 drain、count_tokens 不计轮、超限 400 不留 pending 等现有反例检验新真实入口；同时验证分组、投影与终止事实不变。

## 指定变更逐项裁定

| 变更 | 源码事实 | 复用方式 / 不可推出的结论 |
| --- | --- | --- |
| Anthropic #2358，`11563829a` | `sessions.py:134–223` 转协议后调用同一 core；后台非流式，完成后生成 fake SSE。 | 新接口成立；不等于当前 CC 的完整参数/错误/压缩兼容，见 S1。 |
| request pipeline #3258/#3301/#3264/#3302/#3311/#3249 | v2 去 active cursor，由树派生 latest；resolve→render→commit 的职责清晰；v1 先验证再 rollback；turn_args 随 checkpoint 保存；server 禁 input_ids/logprob_start_len 等 client override，LoRA 来源受约束。 | 可借鉴“生效参数先解析并随动作记录”的结构与反例。不是删除 RH2 的 execution/capture 字段、预处理或 guard 的依据。 |
| Qwen3.5/3.6 TITO #2759，`e2390c53b` | `Qwen35TITOTokenizer` / `Qwen36TITOTokenizer` 复用 Qwen `<im_end>` 后补换行逻辑，固定 preserve_thinking，只允许追加 tool/user/assistant。 | 将来进程内 C 有现成组件；按 I01 现决定本批不启用。不能以“模型受支持”推导请求面/原生模板逐 token 等价。 |
| incremental R3 #2834，`73e0f87b8` | `server.py:45–47` 按 **pause_generation_mode != retract** 启用增量；`core.py:223–240` 检查 causal token prefix；`samples/merge.py:153–200` 拼有连续 offset 的 patch。retract 的普通 `sample_utils.py:168` 仍选最后 R3。 | 可供 I18 以后设计参考；不解决 current retract 每个历史动作的路由来源，不把切片拼接当训练前缀行为等价证明。 |
| abort #3337，`24ec7d866` | `extract_completion:174–175` 收到 HTTP 200、finish_reason=abort 也抛 503 类错误，commit 前终止。 | 合理的 session 完成性修复；不是 /abort_request 投递或多引擎停止确认，不能替换 RH2 abort/drain。 |
| eval replay off #3323，`8c3a85c8e` | `request_args.py:74–77,127–129` 在 model rules 后再次关闭 sampling/routing/indexer replay，去掉增量 offset；create_session 不给 eval 开 sampling support。 | 适合复用其不变量与测试。RH2 自有生成路径不会仅因升级自动走它；正式 eval owner / 身份仍要保留。 |
| decode offloop #3339，`fbc511100` | `OpenAIEndpointTracer.collect_samples:105–110` 用 `asyncio.to_thread` 解码收到的不可变 safetensors payload。 | 是 **driver 端解码**，不是 session 树渲染/装配全部移出事件循环；`v2/core.py:82–84` 装配仍同步。线程化思路可局部借鉴，不必迁移 native endpoint；RH2 E3 已用紧凑路由字节表示减少部分成本，应先看实际剩余瓶颈，不据此承诺 GPU 利用率提升。 |
| default picker #3657，`63b04d8f1` | 默认从“后来的 sibling 一律替代”缩窄成“相同 prompt 才替代”；首轮相同 prompt 重试也裁剪。 | 比旧默认少删合法分支，但仍与 I01 B 不同；现有 hook 已可 identity selection，无需重造。 |
| Harbor #2806，`4dff6f262` | `examples/experimental/harbor/harbor_agent_function.py:445–483` 在 rollout worker 内 `Trial.create/run`；依赖 Harbor miles 分支。CC binding 注入 endpoint，禁 WebSearch/WebFetch、Tool Search；没有复制 RH2 五工具/auto-memory/window 条件。 | 可借鉴缩短外部 agent-server 链路；不是 SWE 准备/可信评分/隔离/清理的等价替代。其 generic exception/timeout 回 reward=0（395–439、472–478），不能直接套本项目 infra failure 语义。 |
| Terminus2 compaction #2741，`bfe13117c` | `examples/experimental/terminus-compaction/run.py:165–185` 真选择 v2 agentic 路径；Harbor summarization/linear_history 产生多叶；postprocessor 唯一化共享 loss，generate 让多叶共享 rollout_id。 | 是其它 harness 的可用参考路线；不证明 CC 2.1.205 的 400/count_tokens/主动或被动压缩已通，也不替代 RH2 execution/group 计权契约。 |

## I18 不能被增量 R3 与版本 span 偷换

这两类账要分别看：

1. **版本账：** `WeightVersionsPerCall.from_meta_info`（`utils/types.py:33–56`）把每次调用输出区间的 version span 转成绝对位置；没有 spans 时可退回单数 version，缺两者时得空表。它提供运输容器，不强制 RH2 正式链的完整性、单调性和 provenance 要求。
2. **路由账：** 当前 RH2 `generate.py:1544–1592` 选最后一轮全量 tape；上游 retract 分支也在普通 merge 中这样做。非 retract 增量模式保留旧 patch，是实质改善，却仍须证明 engine 对旧前缀、跨 publish/cache 状态以及每次行为 forward 的条件，才可决定训练使用哪一版路由。

上游 `arguments.py:2863–2868` 对 session + R3 + retract 仍明确保留 SGLang known-issues 警告。本轮无目标 SGLang/GPU 证据，因此结论是“缩小了部分实现工作”，不是“已完成 I18”。现有版本解析与 gate 不应因容器重名而删除。

## 最小充分迁移方案与停止条件

**现在：** 捕获层维持 `Rh2AnthropicAdapter + capture_wire + I01 B`；miles 训练底座如升级，另按主审的依赖/训练 API 差异做窄接线。不要额外启动 session workers，也不把 Harbor 引入当前可信执行路径。对 #3337/#3323/#3339 只检查当前链是否有同类需要；不要 cherry-pick 未被生产调用的新 helper 来宣称获益。

**未来若因实测成本重开 C：** 优先复用进程内 Qwen tokenizer、matcher 与已存在的参数规则；只扩展现有 adapter 的 rendering 接缝，复用 capture owner、错误处理和 B 的保留能力。若选择整个 v2 服务，则 S1–S3 都是替换前的具体验收对象；identity picker + default postprocessor 足够表达“不丢重试叶且共享动作只训一次”，无需另建平台。该路线会改变上下文/请求匹配语义，应沿既有 T0 决策流程，本文没有批准它。

**成本 / 未知：** 新 fixed template 对模型行为、CC 的真实压缩与窗口、SGLang 依赖升级后的 token/meta_info/retract 行为、GPU 吞吐/内存收益均未测。上游树每节点保留完整 token snapshot，默认 node cap=1024；不能只按“增量 tokenize”估算总内存。当前主线已具有所需捕获能力，没有证据要求为这些未知新建独立服务或现在专排 B/C 作业。

**本子审查达到停止条件：** 已证实新路径的实际入口、三个直接替换差异、关键组件可复用范围和最小充分方案；CPU picker 反例及真实 CC 请求反例均可复核。剩余的是明确选择后的接口/目标机验收，不继续全仓漏洞扫描、不改实现、不改变 I01/I18/I19 决定。
