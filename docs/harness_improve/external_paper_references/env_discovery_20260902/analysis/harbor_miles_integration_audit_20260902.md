# Harbor⇄miles 集成两种接入形态审计（T-a / T-b）

> 来源：Claude 主线程派出的代码审计 subagent，2026-09-02。
> 性质：只读调查报告，非定案文档；所有 T0 判断只是提案，须走决策包。
> 输入：本地 `reference/miles/`（pin `f2b7c7929`，2026-08-24）、
> `reference/miles-rh2-integration/`（`rh2-integration-v3`，HEAD `63c7a94e7`）、
> Harbor 官方仓库 `harbor-framework/harbor` 分支 `harbor-miles-v0.20.0`
> （HEAD `53a6e92`，clone 于 scratchpad，下文以 `harbor:<路径>` 引用）、
> rh2 工作树与 `docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/` 文档。
> 背景：terminal 作为第二训练域的规划见同目录 `prompts/pro_env2_terminal_domain.md`。

---

## 0. 结论速览

1. **T-a 的数据面比"黑盒"直觉更好，但比 fa_formal 要求差得多**。Harbor agent
   server 确实只回传 `reward/exit_status/eval_report/agent_metrics` 四个字段
   （`harbor:agent_server/models.py:22-27`）——token/logprob **不经过 Harbor**；
   token 事实由 miles 自己的 session server（TITO 代理）在服务端捕获，训练侧
   Sample 能拿到 tokens / loss_mask / rollout_log_probs / R3 routed_experts
   /（integration base 上还有）sampling mask 和逐轮单数 weight_version。
   真正的缺口在三处：**装配粒度**（无 per-token weight_version spans、无逐轮
   CaptureSamplingParams 出口）、**纪律**（TITO mismatch 只记 metadata 不阻断、
   session 无认证——正是形态乙被降级的三条理由）、**rh2 治理链整体旁路**
   （capture record / 六字段身份 / eligibility / faithful DIS 分母全部不在数据
   路径上）。结论：T-a 不满足 fa_formal，且"补到满足"等价于重建已被裁定拒绝的
   形态乙（spike-log 2026-08-25 决策表）。
2. **T-a 下身份/eligibility 不能工作**：六字段身份的铸造点在
   `Rh2MilesGenerateFn.__call__`（`rh2/src/repoharness2/adapters/miles/identity.py`），
   T-a 用的是 miles 的 `agentic_tool_call.generate`，铸造点不在链上；会话层
   capability token 被 Harbor 的 `api_key="dummy"` 取代（miles 侧根本不传
   api_key），session 身份是明文 URL 路径；eligibility gate 的 token_provenance
   维因无 capture record 恒 fail（`governance/gate.py:270-302`）→ T-a 样本在
   fa_formal 语义下**永远全拒**。
3. **T-b 改动面集中且有限**：harness、编排、治理层、训练侧全部复用；新增面 =
   envpack 的 Harbor-terminal ingestion（含镜像构建/digest 冻结）+ terminal
   血缘探针 + grading 的 in-place verifier 新路径 + terminal prompt 模板。粗估
   **5~8 个新文件、约 1500~2600 行实现 + 同量级测试**，带 4 个 T0 决策点（schema
   扩源、reward 语义、"在被 agent 碰过的容器里评分"的安全边界、镜像 digest
   冻结策略）。
4. **T-a 作为对照面要拆开看**：任务质量/verifier triage 的高性价比部分其实是
   **Harbor standalone + API 模型**（完全不接 miles）；真正需要 T-a（policy 在环）
   的只有黑盒对照训练/基线，而 CC 路径还要求 pin 之后的新版 miles（Anthropic
   协议面，pin 上 grep 为零），对 vendor 冻结纪律是实质冲击。
5. **建议**："T-b 主线"成立；"T-a 对照"修正为三级——(i) Harbor standalone 任务
   triage 先行（零 miles 耦合）；(ii) T-b verifier 与 Harbor verifier 的同任务
   双跑 parity 测试（把对照价值压缩成 CI 资产）；(iii) policy-in-loop 的 T-a
   黑盒训练对照降为可选项，若做则用 mini-swe-agent 而非 CC，且明确其样本
   永不入账。

---

## 1. T-a 形态解剖：miles 官方 Harbor agent server 链路

### 1.1 端到端控制流（逐步，均已源码核实）

```text
miles 训练侧（每个 rollout member 一次）：
  agentic_tool_call.generate                    reference/miles/miles/rollout/generate_hub/agentic_tool_call.py:44
    ├─ OpenAIEndpointTracer.create              …/generate_utils/openai_endpoint_utils.py:47
    │    POST {session_server}/sessions → session_id
    │    base_url = {session_server}/sessions/{session_id}
    ├─ custom_agent_function = swe_agent_function.run
    │    POST {AGENT_SERVER_URL}/run            reference/miles/examples/swe-agent-harbor-docker/swe_agent_function.py:113-127
    │    请求体 = {**metadata(含 instance_id/agent_name), base_url+"/v1",
    │              model="openai/<name>", sampling_params, max_seq_len,
    │              session_server_id, session_server_instance_id}
    │    （注意：不传 api_key → Harbor 侧默认 "dummy"）
    ↓
Harbor agent server（独立机器/进程）：
  /run → run_trial_in_subprocess（每 trial 一个子进程）
                                                harbor:miles_agent_server.py:115-253
                                                harbor:agent_server/trial_runner.py:420-467
    ├─ TrialConfig(task=HARBOR_TASKS_DIR/<instance_id>, agent, environment, verifier)
    │                                           harbor:agent_server/trial_runner.py:290-410
    ├─ Trial.create → docker compose 起任务沙箱（environment/ 目录定义）
    ├─ agent 在沙箱内执行，模型调用打回 miles session URL
    ├─ verifier：上传任务 tests/ → 沙箱内 /tests，执行 test.sh，
    │    读 /logs/verifier/reward.txt|reward.json
    │                                           harbor:src/harbor/verifier/verifier.py:138-238
    │                                           harbor:src/harbor/models/trial/paths.py:36-43
    └─ 返回 {reward, exit_status, agent_metrics, eval_report}
    ↓
miles session server（TITO 代理，token 事实的真正产地）：
  每次 /v1/chat/completions：
    prepare_chat_request：服务端预分词 input_ids、强制 logprobs=True、
      return_meta_info=True，可选 return_routed_experts / return_indexer_topk
      （--use-rollout-routing-replay / --use-rollout-indexer-replay）
                                                reference/miles/miles/rollout/session/core.py:158-206,355-444
    extract_completion：校验 meta_info.output_token_logprobs 逐 token 在场
                                                reference/miles/miles/rollout/session/core.py:209-241
    SessionRecord(request 全文, response 全文) 追加进会话；
    回给 agent 的响应剥掉 routed_experts/indexer_topk（copy-on-write）
                                                reference/miles/miles/rollout/session/core.py:74-85
    ↓
  agent 结束后 generate 收尾：
    tracer.collect_samples → POST {base_url}/samples → 服务端把逐轮记录
    装配成 Sample（compute → truncate → merge 成单条线性样本）并以
    safetensors wire 回传，随后 DELETE session
                                                reference/miles/miles/rollout/session/core.py:311-340
                                                reference/miles/miles/rollout/generate_utils/openai_endpoint_utils.py:71-94
    agent_metadata（reward 等）merge 进 sample.metadata；
    reward_func 直接读 metadata["reward"]        reference/miles/examples/swe-agent-harbor-docker/generate.py:32-40
```

超时/中止面：`--agent-timeout`（Harbor 权威）< `AGENT_TRIAL_TIMEOUT`（客户端
天花板，默认 7200s，`swe_agent_function.py:27-34`）；miles oversampling abort 时
经 `abort()` 钩子 POST `/flush` 让 Harbor 取消在飞 trial 并释放容器
（`swe_agent_function.py:137-165`，`harbor:miles_agent_server.py:268-296`）。

### 1.2 T-a 训练侧 Sample 实际拿到什么（wire 白名单）

样本 wire 是静态白名单 `SAMPLES_VALUE_SPEC`
（`reference/miles/miles/rollout/session/samples/codec.py:32-54`）：

| 字段 | pin f2b7c7929 | integration v3（含 #2596/#2595） |
|---|---|---|
| tokens / response / response_length | ✅ | ✅ |
| loss_mask（观察位=0 由多轮 merge 填充） | ✅ | ✅ |
| rollout_log_probs | ✅（全词表） | ✅（mask 会话为 support-normalized，`merge.py` 经 `append_sampling_metadata`） |
| rollout_sampling_mask（CSR 支持集） | ❌ | ✅（`--rollout-top-p<1` 时服务端自动请求，`reference/miles-rh2-integration/miles/rollout/session/core.py:190-209`） |
| rollout_routed_experts（R3） | ✅（R3-on 时） | ✅ |
| rollout_indexer_topk | ✅ | ✅ |
| weight_versions | ✅ **逐轮单数** | ✅ **仍逐轮单数**（`…/session/samples/merge.py:145-146`；spike-log V2 条目登记的残余："session merge.py 仍单数"） |
| status / prefix_cache_info / metadata | ✅ | ✅ |
| per-token weight_version_spans | ❌ | ❌ |
| 逐轮实际采样参数（temperature/top_p 等） | ❌（存在 SessionRecord.request 里，collect 后随 session 删除，不上 wire） | ❌ |
| GenerationCaptureRecord / A4 sidecar | ❌（rh2 概念，不存在于该链） | ❌ |

### 1.3 哪些 miles 参数控制 T-a

来自 `reference/miles/examples/swe-agent-harbor-docker/run.py:168-241`：

- 接线四件套：`--custom-generate-function-path miles.rollout.generate_hub.agentic_tool_call.generate`、
  `--custom-agent-function-path swe_agent_function.run`、`--custom-rm-path generate.reward_func`、
  `--rollout-function-path generate.RolloutFn`；
- session server：`--use-session-server`、`--session-server-port`、`--tito-model glm47`
  （TITO 分词/模板身份）；`--sglang-tool-call-parser`/`--sglang-reasoning-parser`；
- 采样与预算：`--rollout-temperature`、`--rollout-max-response-len`、`--max-seq-len`
  （转发给 Harbor 作提前中止 + session 装配期截断，`agentic_tool_call.py:147-157`）；
- 过滤：`--dynamic-sampling-filter-path …check_no_aborted`（aborted 拖垮整组）；
- 环境变量：`AGENT_SERVER_URL`、`AGENT_MODEL_NAME`、`MILES_ROUTER_EXTERNAL_HOST`
  （把 session URL 重写成 Harbor 可达地址）、`AGENT_TRIAL_TIMEOUT`、`HARBOR_TASKS_DIR`。

Harbor 侧控制面（`harbor:miles_agent_server.py:346-447` + `trial_runner.py`）：
`--max-concurrent`、`--agent-timeout`、`--agent-setup-timeout`、`--trials-dir`、
`HARBOR_ENV_TYPE(docker|daytona)`、`HARBOR_DELETE_CONTAINERS`（**默认 false =
trial 容器默认留存**）、`HARBOR_AGENT_MAX_ITERATIONS`、`HARBOR_MAX_SEQ_LEN`、
`AGENT_MAX_OUTPUT_TOKENS`、`HARBOR_VERIFIER_TIMEOUT_SEC`、`HARBOR_TIMEOUT_MULTIPLIER`、
`HARBOR_ENV_ALLOWED_HOSTS`/`HARBOR_AGENT_ALLOWED_HOSTS`、`HARBOR_ADMIN_SECRET`。

### 1.4 Harbor 侧能起什么 agent；沙箱与 verifier 生命周期

- **agent 选择**：`metadata.agent_name` 逐 trial 决定。专门接线的有
  `mini-swe-agent`（默认）、`terminus-2/1`（宿主进程 agent）、`claude-code`、
  `opencode`（`harbor:agent_server/trial_runner.py:34-140`）；Harbor 本体的
  installed-agent 目录还有 codex/aider/goose/gemini-cli 等 30+ 种
  （`harbor:src/harbor/agents/installed/`），但未在 miles 服务器里配连接参数。
- **采样参数只对 terminus 生效**：`request.sampling_params` 仅在 terminus 分支
  作为 `llm_call_kwargs` 下发（`trial_runner.py:64-86`）；**claude-code、
  mini-swe-agent、opencode 分支全部丢弃 sampling_params**——生成时的
  temperature/top_p 由 agent 自身客户端决定。miles 侧 `prepare_chat_request`
  也不强制采样参数（只强制 logprobs/meta_info）。
- **claude-code 分支细节**（`trial_runner.py:88-106` +
  `harbor:src/harbor/agents/installed/claude_code.py:1367-1539`）：CC 装在任务
  容器内，`claude --print --output-format=stream-json --permission-mode=bypassPermissions`；
  `ANTHROPIC_BASE_URL` = miles session URL、`ANTHROPIC_API_KEY` = request.api_key
  （默认 "dummy"）；强制 `--disallowedTools WebSearch,WebFetch`、
  `ENABLE_TOOL_SEARCH=false`、`FORCE_AUTO_BACKGROUND_TASKS=1`、
  `ENABLE_BACKGROUND_TASKS=1`。**注意**：代码注释明言 "Miles implements the
  client-side Anthropic protocol only"——该能力在我们的 pin（`f2b7c7929`）与
  integration v3 上 **grep 为零**（`grep -rn anthropic reference/miles/miles/`
  空），是 Harbor 分支 2026 年 #2654/#2670/#2671/#2673 系列配套的**pin 之后**
  上游 miles 能力。在我们现有 miles 版本上，T-a 的 claude-code 路径**跑不通**。
- **沙箱生命周期**：每 trial 一个子进程 → `Trial.create` 用任务 `environment/`
  目录 docker compose 启动 →（阶段网络策略：`no-network|public|allowlist`，
  `harbor:src/harbor/models/task/config.py:36-70`）→ agent setup（联网装 CLI）→
  agent 运行 → verifier → 容器按 `HARBOR_DELETE_CONTAINERS` 决定删留；
  `/flush_all` 兜底回收 compose 项目（`harbor:miles_agent_server.py:314-343`）。
- **verifier 语义**（T-b 要复用的边界）：任务目录四件套
  `instruction.md / task.toml / environment/ / tests/`（+可选 `solution/`，
  `harbor:src/harbor/models/task/paths.py:15-23`）；评分 = 把 `tests/` 上传进
  **同一个 agent 用过的容器** `/tests` → 执行发现的 `test.sh`（stdout 落
  `/logs/verifier/`）→ 读 `/logs/verifier/reward.json`（优先）或 `reward.txt`
  （float，可为分数值）→ 缺文件/空文件/解析失败按异常拒绝
  （`harbor:src/harbor/verifier/verifier.py:66-238`）。`task.toml` 携带
  agent/verifier 超时、cpus/memory_mb/storage_mb、workdir、网络策略
  （`harbor:src/harbor/models/task/config.py:334-460`）。

---

## 2. 对照基线：我们的 capture / 身份 / eligibility 链的硬要求

（只列本审计要用的锚点；细节见各源文件。）

- **逐轮 capture**：`GenerationCaptureHook.on_generate_response` 在 SGLang 客户端
  响应层逐轮构造 `GenerationCaptureRecord`（A4 sidecar）+ `TurnTape`
  （`rh2/src/repoharness2/adapters/slime/generate.py:646-770`）。TurnTape 携带
  output_ids / output_log_probs / top_p tape 或 sampling_supports / routed_experts
  / weight_version / **weight_version_spans**（V2 批新增，per-token 版本区间）。
  capture 缺 tape 即 `partial`/`failed`，投影层拒收（fail-closed，
  `generate.py:689-702` docstring）。
- **CaptureSamplingParams**：每轮必录 temperature/top_p/max_new_tokens/
  return_top_p_token_ids/return_routed_experts（`generate.py:764-769`；契约
  `rh2/src/repoharness2/contracts/capture.py:41`）。
- **eligibility 七维**：token_provenance 维要求每条分支的 capture_record_refs
  解析到 `capture_status=complete` 的记录（`rh2/src/repoharness2/governance/gate.py:270-302`）；
  失败封顶 `offline_or_sft_candidate`（`gate.py:97-108`）。治理唯一入口
  `finalize_rollout`：grade → project → scan → gate
  （`rh2/src/repoharness2/governance/wrapper.py:136-195`）。
- **四层身份（六字段）**：prompt_group / rollout_execution / member_slot /
  physical_attempt(+seq)，铸造点 = miles 派发路径 `Rh2MilesGenerateFn.__call__`
  （`rh2/src/repoharness2/adapters/miles/identity.py:1-60`；消费点
  `adapters/slime/generate.py:2366` 强校验，fa_formal 缺字段全拒——
  `formal_first_training_readiness_scope.md` §2.2）。
- **三层会话身份**：公开稳定身份（trajectory_id/rollout_execution_id）/
  非秘密 internal sid（`s-{physical_attempt_id}`）/ 秘密 capability token
  （`cap-`+128bit = CC 的 ANTHROPIC_AUTH_TOKEN，认证后兑换出局；
  `rh2/src/repoharness2/adapters/slime/session_capability.py:1-52`）。
- **fa_formal GPU 验收对 tape 的要求**（`formal_first_training_readiness_scope.md`
  §3.4/§3.5）：sampling support mask 与 support-normalized behavior logprob 来自
  真实 SGLang；R3 tape 被 Megatron 消费耗尽；单 HTTP 请求跨权重 publish 产生
  multi-span，**RH2 spans、sampling mask、R3 tape 和 token 行逐位对齐**且该样本
  进 trainer loss。
- **形态乙（miles session server TITO）已裁定降级**（spike-log 决策表
  2026-08-25）：三条理由——TITO mismatch 只记 metadata 不阻断；并发关闭时
  "已交付不记账"；session id 明文 URL 无认证。T-a 正建在形态乙的服务面上。

---

## 3. 问题解答

### 3a. T-a 数据能否满足 fa_formal 的 token provenance？

**不能。**但缺口归因要分三层说清（"Harbor 不传"只是其中最浅的一层）：

| 层 | 事实 | 缺口性质 |
|---|---|---|
| Harbor 层 | `/run` 只回 reward/exit_status/eval_report/agent_metrics（`harbor:agent_server/models.py:22-27`）；token 面在设计上就不走 Harbor | 按设计如此，不是缺陷；token 要从 miles session server 拿 |
| miles session server 层 | 捕获了 token/logprob/R3/（v3）mask，但：① weight_version **逐轮单数**，无 per-token spans（`reference/miles-rh2-integration/miles/rollout/session/samples/merge.py:145-146`；spike-log V2 条目登记残余）——fa_formal H4 的 multi-span 逐位对齐要求直接不满足；② 逐轮实际采样参数存于 SessionRecord.request，collect 后随 session 删除，不在样本 wire 上（`…/session/samples/codec.py:34-51` 白名单无此项）——CaptureSamplingParams 无法如实构造；③ `tito_session_mismatch` 只写 metadata 不阻断（`…/session/core.py:287-301`）、session 无认证——违反 rh2 fail-closed 纪律（形态乙三条理由原样命中） | miles "存了但导出面窄 + 纪律不符"；补齐 = 改 miles session 装配/wire/认证 = 重建形态乙 |
| rh2 层 | T-a 的 generate 函数是 miles 的 `agentic_tool_call.generate`，我们的 capture hook（挂在 `call_sglang_generate` 包装上）、GenerationCaptureRecord、TurnTape、投影、DIS provenance 分母（`faithful_dis_loss.py` 消费 sampling_mask_assembly 的逐轮支持集）整条链**不在数据路径上** | 不是"谁不传"，是形态本身旁路了我们的 adapter 层 |

另有两个独立否定项：

- **采样参数控制权在 agent 侧**：Harbor 只对 terminus 下发 sampling_params
  （`harbor:agent_server/trial_runner.py:64-86`），claude-code/mini-swe/opencode
  丢弃之；miles 侧也不强制（`…/session/core.py:158-206` 只强制 logprobs 等）。
  我们冻结 profile 的 temperature/top_p 在 T-a 下无法保证是生成时的真实值，
  top-p tape/mask 的语义前提（`--rollout-top-p<1` 服务端判定）与 agent 实际
  发送的 top_p 可能脱节。
- **CC 路径依赖 pin 之后的 miles**：Anthropic 协议面在 pin/integration v3 上
  为零（§1.4）。要在 T-a 用 CC，必须 vendor refresh 到上游新 HEAD——对
  integration base 冻结纪律（`miles_spike/integration_base_manifest.json` 树
  哈希钉死 + lanes 校验）是实质冲击。另：CC 的 subagent/sidechain 会破坏 v1
  线性 TITO 的前缀增长假设（`…/session/linear_trajectory.py`），上游给 CC 配的
  应是 session v2 树路径（`…/session/v2/`）——具体接法在 pin 上不可核实，
  属 post-pin 不确定项。

### 3b. T-a 下 eligibility / 身份铸造还能不能工作？

**四层身份（六字段）**：铸造点不在链上（T-a 不经过 `Rh2MilesGenerateFn`）。
技术上可以给 `agentic_tool_call.generate` 包一层在派发时刻盖章（identity.py 只
要求 sample 有 `group_index/index/metadata`，鸭子类型可注入），组/执行/成员/
attempt 四层能勉强外挂成立。

**但会话层与 evidence 层不成立，且不可外挂**：

- capability token 三层拓扑失效：T-a 下 CC/agent 的凭证是 `api_key="dummy"`
  （miles 的 `swe_agent_function.run` 构造请求体时不含 api_key，
  `swe_agent_function.py:91-96`；Harbor `RunRequest.api_key` 默认 "dummy"），
  会话身份是 URL 路径里的明文 session_id，无认证、无按 attempt 撤销面——
  quiescence 撤销（`generate.py:1684-1689` revoke_session）、poison 按 internal
  sid 键控的语义（`session_capability.py:17-19`）全部没有挂点。
- eligibility 恒拒：gate 的 token_provenance 维要求 capture_record_refs 解析到
  complete 记录（`gate.py:270-302`）；T-a 无 capture record → 该维恒 fail →
  全部封顶 `offline_or_sft_candidate`；fa_formal/W1b 语义下 degraded 收口
  abort。**gate 机械上"能跑"，但结论恒为全拒，等价于不能工作。**
- 结论：把这些补齐 = 把 rh2 adapter 链搬进 TITO 会话面 = 形态乙重建，
  与 2026-08-25 已定决策冲突。T-a 只能作为**账本外**形态存在。

### 3c. T-b 需要新建/修改哪些组件（含工作量粗估）

T-b 定义（任务给定）：我们自己的 CC harness 跑 terminal 任务，仅复用 Harbor
的**任务格式**与 **verifier 边界**（rollout 结束后注入 `tests/`、跑 `test.sh`、
读 `/logs/verifier/reward.txt|json`），tape/DIS/eligibility 全链保持。

复用面（零改动或近零改动）：capture/tape/身份/eligibility/DIS/零信号/R3/spans
全链（`adapters/slime/generate.py` 步骤 1/3/4/5/8/9）、vendored CC harness
（`rh2/src/slime/agent/harness/claude_code.py`——本身任务无关：prompt/workdir/
env 注入三件事）、miles 训练侧全部。

新增/修改面（按组件）：

| # | 组件 | 内容 | 参照物 | 量级 |
|---|---|---|---|---|
| 1 | envpack ingestion：Harbor task 目录 → 三分 bundle + EnvironmentPackage | 解析 `task.toml/instruction.md`；`environment/` docker build → 镜像 digest 冻结（Harbor 任务是**构建源**不是预构建镜像引用——与 SWE 的 `image_manifest_digest` 语义要重对齐）；`tests/` 全目录 + test.sh → terminal 私有评分 bundle；`solution/` → validation bundle（oracle 门原料）。映射字段量：public 侧约 8~10 个（instance_id/instruction/image+digest/workdir/资源限额/网络策略/超时），grading 侧约 4~6 个（tests 文件集 digest 表/test 脚本名/verifier 超时/reward 解析约定），validation 侧 1~2 个 | `ingest_swegym_lite.py` 598 行、`bundles_v2.py` 279 行 | 新 2~3 文件，600~1000 行 |
| 2 | schema：source 枚举扩展 + terminal bundle 变体 | `EnvironmentPackageV1.source` 是封闭枚举 `Literal["swe_gym_lite"]`，字段注释明言"扩源升版本"（`bundles_v2.py:167`）；repo/base_commit/test_patch/F2P/P2P 对 terminal 无意义 → 需要 terminal 变体模型（新 schema_id）而非可选化旧字段 | `bundles.py:84-208` | 并入 #1；**T0**（公共 schema/唯一事实来源） |
| 3 | materialize：terminal 血缘探针 | 现探针硬编码 `/testbed`+git（`envpack/materialize.py:60-88`）；terminal 需要"镜像 RepoDigests 比对（已有函数可复用）+ workdir 存在 + 可选启动 marker"最小探针；BASH_ENV conda 注入跳过（SWE 专用） | materialize.py 280 行 | +150~300 行（新函数，不动旧探针） |
| 4 | 任务面：RolloutTaskSpec terminal 变体 | `base_commit` 必填、`workdir="/testbed"` 缺省、`grading_spec: GradingEnvSpec` 类型均 SWE 形（`adapters/slime/generate.py:1748-1798`）；编排层按任务类型分支 | — | +100~200 行改动（generate.py 编排 + spec 构造器） |
| 5 | grading：in-place verifier 新路径 | 新 `TerminalGradingSpec` + manager 新通道：复用 F2-2 quiescence freeze（`generate.py:1550-1560` frozen_grading_workspace）→ 冻结后注入 `tests/` → 容器内以受控 env 跑 `test.sh`（分段超时对齐 `GradingEnvSpec` 的 test_timeout_seconds 纪律）→ 读 reward 文件 fail-closed 解析（对齐 Harbor 的缺文件/空文件/解析失败三类拒绝）→ 映射 GradingReport。**根本差异**：SWE 是"导 patch → fresh 容器重放"（`grading/manager.py:1-32`），terminal 的评分对象是 rollout 容器的最终文件系统状态，patch 导出不适用 → 评分必然发生在 agent 碰过的容器里 | manager.py 1607 行中评分执行段 | 新 1 文件 400~700 行 + manager/contracts 小改；**T0**（评分环境纪律放宽 + 新拒绝路径） |
| 6 | reward 语义 | Harbor reward 可为 [0,1] 分数值或 reward.json 多键（`verifier.py:66-94`）；我们 GradingReport 的 outcome 字段组按 SWE 二值（resolved=1.0/tests_failed=0.0，`grading/manager.py:25-32`）| scoring.py | 小（映射函数）；**T0**（训练样本 reward 语义） |
| 7 | CC harness terminal 模板 | terminal prompt 模板（instruction.md 原文 + 完成约定，无 patch 提交语义；对照 `envpack/bundles.py` 的 `render_user_prompt`）；workdir 从 task.toml（`harbor:…/task/config.py:460`）映射；episode 预算从 `agent.timeout_sec` 映射 | bundles.py 模板段 | +100~200 行 |
| 8 | 数据入口 | 任务目录扫描 → miles JSONL（prompt+metadata.instance_id）+ trusted loader terminal 版入口 | `download_and_process_data.py` 172 行、`load_trusted_ingest_outputs` | +200~400 行 |
| 9 | 环境质量门（部分既有欠账） | 四门 runner 目前零行代码（见同目录 `rh2_env_layer_status_20260902.md` 结论）；terminal 的 oracle 正控可直接用 `solution/solve.sh`（Harbor oracle agent 语义），比 SWE golden_patch 门更简单 | — | 不全算 T-b 增量；terminal 侧适配 +100~300 行 |

**合计粗估**：新增 5~8 文件、实现约 **1500~2600 行** + rh2 惯例同量级测试；
触碰既有文件 3~5 处（generate.py 编排分支、contracts 小扩、manager 接线）。

**T0 决策点（须走决策包）**：① schema 扩源/升版方案（#2）；② terminal reward
语义与 eligibility 映射（#6）；③ "在被 agent 碰过的容器里评分"的安全边界与
补偿控制（#5——见 §3e 风险登记）；④ 镜像"本地构建 vs 预构建+digest 冻结"
策略（#1，对应 `GradingEnvSpec.__post_init__` 的二选一纪律，
`grading/manager.py:570-576`）。

### 3d. T-a 作为"快速对照/评测面"的价值与成本

**价值成立的部分**：

1. **参考实现对拍**：miles↔Harbor 链是官方跑通过的（README 记录了 8×H200 多日
   TB2 run，`reference/miles/examples/swe-agent-harbor-docker/README.md:85-115`）。
   当 T-b 接线出问题时，同一任务在 T-a/Harbor 栈上的行为是"任务坏 vs 我们接线
   坏"的分诊器。
2. **任务质量 triage**：跑一遍任务集看 reward 分布/超时率/verifier 失败率，
   过滤坏任务后再进 T-b ingestion。
3. **黑盒基线**：policy 模型在环的 terminal 通过率基线（GRPO 有无信号的快速
   探测）。

**关键修正——价值 1、2 其实不需要 T-a**：任务 triage 和 verifier 正确性验证用
**Harbor standalone CLI + 任意 API 模型**即可（Harbor 本体自带 trial/job 执行
面，`harbor:src/harbor/cli/`），零 miles 耦合、不占 GPU、不碰 session server。
T-a（整套 miles serving + session server + agent server）只有在"必须我们的
policy 模型在环"时才必要——即价值 3。

**成本与限制**：

- 重依赖面：harbor-framework 全量安装 + 每 trial 一个 docker compose 项目 +
  dashboard 进程；`HARBOR_DELETE_CONTAINERS` 默认 false（容器留存，磁盘持续
  增长）；超时纪律两层（`--agent-timeout` < `AGENT_TRIAL_TIMEOUT`）配错会拖垮
  GRPO 组（README:52-63 明文警告）。
- CC 路径需要 pin 后新版 miles（§3a），或换 mini-swe-agent/terminus——但换
  harness 后与我们 T-b 的 CC 训练链**不同构**（prompt/工具面/采样参数都不同），
  "对照"的解释力只剩"该任务集在成熟栈上可训"这一条。
- 其样本/评测结果在我们账本外（无身份、无 capture、无 eligibility），不能充当
  readiness scope §2.9/H10 的 eval 运输链（那条要求绑定我们的 source/环境解析
  器、taskset 身份分离、checkpoint digest 绑定，
  `formal_first_training_readiness_scope.md:641-649,839-852`）。

**判断**：T-a 作为常驻评测面**不划算**；作为一次性"任务集可训性"探测（用
mini-swe-agent，不动 CC、不动 pin）**可选、低优先**。任务质量 triage 应直接用
Harbor standalone。

### 3e. 结论：T-b 主线 + T-a 对照是否成立

**成立，带四点修正**：

1. **T-b 主线确认**。它是唯一满足 fa_formal（capture/四层身份/eligibility/
   faithful DIS/spans/R3）的形态；且复用面比直觉大——harness、编排、治理、
   训练侧全复用，净新增集中在 envpack ingestion 与 grading 新路径（§3c 表）。
2. **"T-a 对照"降级并拆分**：(i) 任务 triage → **Harbor standalone + API 模型**
   先行（零 miles 耦合，立即可做）；(ii) verifier 对拍 → 把对照价值固化为
   **同任务双跑 parity 测试**（我们的 in-place grader vs Harbor verifier 同
   reward，可进 CI）——这比常驻 T-a 便宜且可回归；(iii) policy-in-loop 黑盒
   对照训练 → 可选项，若做用 mini-swe-agent（避免 CC 逼出 vendor refresh），
   且预先声明其样本/曲线只回答"任务集可训"，永不入账。
3. **不要为 T-a 提前升级 miles**。CC-over-TITO 所需的 Anthropic 面是 pin 后
   能力，为对照面引入一次 vendor refresh（V1 条目记载的 cherry-pick 重建 +
   manifest/lanes 全链重锚）不成比例；若未来因其他原因 refresh，届时再评估
   T-a-with-CC 是否顺带解锁。
4. **风险登记（T-b 头号新议题）**：in-place 评分 = 相对 SWE fresh-grader 的
   纪律放宽。agent 在 rollout 期间可预置陷阱：篡改 shell 环境/PATH、预写
   `/tests` 或 `/logs/verifier/reward.txt`、替换 test.sh 将要调用的工具。
   Harbor 的威胁模型是 benchmark（agent 不知道也不针对 verifier），RL 训练下
   模型会**学**这些路径。补偿控制至少需要：tests 注入严格在 quiescence freeze
   之后、评分前扫描/清空 `/tests` 与 `/logs/verifier`、test.sh 以 root+受控
   env 执行、reward 文件仅认评分动作自己创建的路径、hygiene 面从"patch 段
   剔除"改为"评分前状态断言"。此项应按
   `formal_first_training_readiness_scope.md` §2.4 最小 reward-integrity 链的
   同款标准出决策包（对应 §3c 的 T0-③）。

---

## 4. 主要证据索引

| 主题 | 路径 |
|---|---|
| T-a miles 侧五件套 | `reference/miles/examples/swe-agent-harbor-docker/{README.md, swe_agent_function.py, generate.py, run.py, download_and_process_data.py}` |
| T-a generate/tracer | `reference/miles/miles/rollout/generate_hub/agentic_tool_call.py`；`reference/miles/miles/rollout/generate_utils/openai_endpoint_utils.py` |
| TITO session server（pin） | `reference/miles/miles/rollout/session/{core.py, sessions.py, server.py, linear_trajectory.py, samples/codec.py, samples/merge.py}` |
| TITO session server（v3，mask/R3/单数 weight_version） | `reference/miles-rh2-integration/miles/rollout/session/{core.py:190-209, samples/codec.py:34-51, samples/merge.py:116-146}`（分支 `rh2-integration-v3`，HEAD `63c7a94e7`） |
| Harbor agent server | `harbor-framework/harbor@harbor-miles-v0.20.0`（HEAD `53a6e92`）：`miles_agent_server.py`、`agent_server/{models,trial_runner,results,state,teardown,background}.py` |
| Harbor verifier/任务结构 | 同上：`src/harbor/verifier/verifier.py`、`src/harbor/models/trial/paths.py`、`src/harbor/models/task/{paths.py, config.py}`、`src/harbor/trial/trial.py` |
| Harbor CC agent | 同上：`src/harbor/agents/installed/claude_code.py`（安装/运行/env 注入/turn 计数） |
| rh2 capture/编排 | `rh2/src/repoharness2/adapters/slime/generate.py`（docstring:1-64、TurnTape:646-686、CaptureHook:689-770、RolloutTaskSpec:1748-1798、SlimeBindingConfig:1804-1853） |
| rh2 会话三层身份 | `rh2/src/repoharness2/adapters/slime/session_capability.py` |
| rh2 六字段身份铸造 | `rh2/src/repoharness2/adapters/miles/identity.py` |
| rh2 治理/资格 | `rh2/src/repoharness2/governance/{wrapper.py:136-195, gate.py:97-108,270-317}`；`rh2/src/repoharness2/contracts/capture.py` |
| rh2 评分/环境包 | `rh2/src/repoharness2/grading/manager.py`（GradingEnvSpec:543-583）；`rh2/src/repoharness2/envpack/{bundles.py:84-208, bundles_v2.py:132-259, materialize.py:1-115}` |
| 我们的 CC harness（vendored） | `rh2/src/slime/agent/harness/claude_code.py` |
| 决策与要求文档 | `docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/spike-log.md`（形态甲/乙决策 2026-08-25、S1b、P0-3、V2 spans 残余、V3 router）；`…/miles_spike/formal_first_training_readiness_scope.md`（§0.3、§1 表、§2.2、§2.9、§3.3-3.5、§3.11、§4） |
| 环境层现状（sibling） | 同目录 `rh2_env_layer_status_20260902.md`、`prompts/pro_env2_terminal_domain.md` |
