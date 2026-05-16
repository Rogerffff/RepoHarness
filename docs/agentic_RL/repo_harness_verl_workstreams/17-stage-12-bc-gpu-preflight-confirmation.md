# Stage 12-B / Stage 12-C 远端 GPU 执行前确认清单

```text
status: pre_implementation_confirmation
created_at: 2026-05-17
depends_on:
  - 01-sequential-implementation-plan.md
  - 16-stage-12-a-execution-plan.md
  - Stage 12-A commit 1ce1c0c2
scope:
  - Stage 12-B 真实模型端到端 smoke 前置确认
  - Stage 12-C 小 batch trainer smoke 前置确认
not_scope:
  - 本文不是 Stage 12-B 或 Stage 12-C 的正式执行计划
  - 本文不直接规定最终训练配置
```

## 1. 当前结论

Stage 12-A 已经证明本地 Mac 可以完成真实 `real_episode` runtime bridge 和真实 `reference/verl` 结构 smoke。下一步 Stage 12-B / Stage 12-C 需要远端 GPU，因为它们要验证真实模型、真实推理服务、真实 `LLMServerClient.generate(...)`、真实 log probability、以及小 batch trainer 路径。

我的默认推荐是：

```text
Stage 12-B 第一轮：
  模型：Qwen/Qwen2.5-Coder-7B-Instruct
  GPU：单卡 RTX PRO 6000 96GB
  镜像：优先沿用 verlai/verl:vllm011.latest
  推理后端：先以 vLLM 作为主 smoke
  任务：当前 worktree 内 tests/fixtures/repos 的极小 Python 任务

Stage 12-C 第一轮：
  如果只做 DataProto / loss 形状和 invalid filtering smoke：
    可以先尝试单卡 RTX PRO 6000 96GB
  如果要跑真实 actor 更新、真实 rollout 服务和更少调参风险：
    推荐双卡 RTX PRO 6000 96GB
```

这个推荐的核心理由是：Stage 12-B 的目标是先排除 infra、adapter、token provenance、workspace、verifier、reward、visibility 和 artifact 链路问题，不应该第一步就用大模型或复杂 trainer 配置放大变量。Stage 12-C 再单独处理 trainer loss、log probability、invalid sample filtering 和资源调度。

## 2. 已查证的外部事实

这些信息来自公开官方页面，主要用于帮助选择模型和镜像。

1. `Qwen/Qwen2.5-Coder-7B-Instruct` 的 Hugging Face 页面显示模型大小约为 `8B params`，权重类型为 `BF16`，并建议使用较新的 `transformers`，旧版本可能遇到 `qwen2` 识别错误。参考：[https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
2. Qwen 官方介绍中说明 Qwen2.5-Coder 支持长上下文，代码能力覆盖多语言，并且列出了 `Qwen2.5-Coder-7B-instruct`。参考：[https://qwen2.org/qwen2-5-coder/](https://qwen2.org/qwen2-5-coder/)
3. verl 官方安装文档说明从 Docker 镜像安装时可以使用预构建镜像，示例包括 `verlai/verl:sgl055.latest` 和 `verlai/verl:vllm011.latest`。参考：[https://verl.readthedocs.io/en/latest/start/install.html](https://verl.readthedocs.io/en/latest/start/install.html)

这些事实不等于 Vast.ai 当前实时库存或价格。Vast.ai 的具体可租实例、价格、端口、磁盘和镜像标签仍需要你在下单时确认。

## 3. 需要你确认的默认决策

### 3.1 模型选择

推荐选择：

```text
Qwen/Qwen2.5-Coder-7B-Instruct
```

原因：

- 它是代码 instruct 模型，适合软件工程极小任务 smoke。
- 7B 级别足够小，适合先排查基础设施链路。
- 96GB 显存对 7B BF16 推理和小规模 smoke 很宽裕。
- 即使模型没有成功修复任务，也可以用 rejected episode 验证 reward、artifact、visibility 和 invalid filtering，不会把模型能力问题误判为基础设施问题。

请确认：

```text
[ 1] 同意 Stage 12-B 第一轮使用 Qwen/Qwen2.5-Coder-7B-Instruct。
[ 1] 如果 7B 工具格式遵循太差，优先先调 prompt / parser，而不是立刻换大模型。
[ 1] 如果连续工具格式探针失败，再考虑 Qwen2.5-Coder-14B-Instruct 或 32B 级别模型。
```

我的建议是先不要直接上 32B。32B 可能让推理更稳，但会把模型下载、显存、启动时间、trainer 资源规划都变复杂。Stage 12-B 第一轮更应该证明链路，而不是证明模型能力上限。

### 3.2 GPU 数量和实例规格

Stage 12-B 推荐：

```text
单卡 RTX PRO 6000 96GB
```

原因：

- Stage 12-B 只要求真实模型端到端 smoke，不要求 trainer 反向传播。
- 单卡更容易排查问题，Ray / vLLM / RepoHarness workspace / verifier 都在同一台机器上，日志和资源关系更清楚。
- 96GB 对 7B 推理留有足够空间。

Stage 12-C 推荐：

```text
优先双卡 RTX PRO 6000 96GB；如果价格或库存不方便，可以先单卡尝试。
```

原因：

- Stage 12-C 会碰到 trainer、actor、rollout、log probability 和显存分配。
- 7B 的真实 trainer loss smoke 可能不仅有模型权重，还会有梯度、优化器状态、rollout 服务占用、Ray actor 开销和 batch tensor。
- 双卡可以降低第一次跑 trainer smoke 时的显存调参成本。

请确认：

```text
[ 1] Stage 12-B 先租单卡 RTX PRO 6000 96GB。
[ 1] Stage 12-C 如果单卡 OOM 或资源调度复杂，再切双卡。
[ ] 或者你希望一开始就租双卡，把 Stage 12-B 和 Stage 12-C 放在同一台实例上连续执行。
```

我的推荐是：先单卡完成 Stage 12-B。如果 Stage 12-B 很顺，再按 Stage 12-C 的实际配置决定是否继续单卡或换双卡。这样更省钱，也更容易定位问题。

### 3.3 Vast.ai 镜像和推理后端

你常用的镜像是：

```text
verlai/verl:vllm011.latest
```

根据你补充的回复，`verlai/verl:vllm011.latest` 和 `verlai/verl:sgl056.latest` 都可以接受，后端选择由 RepoHarness / verl 接入目标决定。

更新后的推荐是：

```text
Stage 12-B 主 smoke：
  镜像：verlai/verl:sgl056.latest
  后端：SGLang

Stage 12-B parity smoke：
  镜像：verlai/verl:vllm011.latest
  后端：vLLM
```

原因：

- Stage 12 高层计划原本就倾向先做 SGLang 真实 smoke，因为 verl 的 agentic / multi-turn 示例更偏 SGLang 路线。
- 你已经确认 `verlai/verl:sgl056.latest` 也可以使用，所以没有必要因为镜像熟悉度而强行优先 vLLM。
- vLLM 仍然很重要，但更适合作为第二条 parity smoke，用来证明 `LLMGateway` route 和 tokenizer / log probability contract 不绑定单一后端。
- 如果 Vast.ai 上 `sgl056` 镜像临时不可用、启动失败或与当前 GPU / driver 不兼容，可以回退到 `vllm011`，但必须在 preflight 报告里记录原因。

请确认：

```text
[x] 你已经确认 SGLang 和 vLLM 都可以，由执行计划决定。
[ ] Stage 12-B 主 smoke 改为 verlai/verl:sgl056.latest + SGLang。
[ ] Stage 12-B parity smoke 使用 verlai/verl:vllm011.latest + vLLM。
[ ] 如果 SGLang 镜像或后端在 Vast.ai 上不可用，允许回退为 vLLM 主 smoke，并记录原因。
```

如果你希望重新优先 vLLM，也可以明确改回：

```text
verlai/verl:vllm011.latest
```

但在当前已知条件下，我建议 Stage 12-B 正式计划先按 SGLang 主线编写。

### 3.4 任务选择和 fixture 冻结

Stage 12-B 不建议直接上 SWE-Bench，也不建议依赖另一个 worktree 的可变路径。第一轮建议使用当前 worktree 已经存在的极小任务。

推荐正例任务顺序：

```text
1. tests/fixtures/tasks/task_001.yaml
   repo: tests/fixtures/repos/buggy_calculator
   目标：修改 divide，使除以 0 时抛出 ValueError。

2. tests/fixtures/tasks/task_002.yaml
   repo: tests/fixtures/repos/import_config_bug
   目标：未知 feature flag 返回 False。

3. tests/fixtures/tasks/task_003_create_file.yaml
   repo: tests/fixtures/repos/missing_helper_file
   目标：新增 app/helpers.py。
```

推荐负例或边界任务：

```text
tests/fixtures/tasks/task_security_probe.yaml
tests/fixtures/tasks/task_invalid_baseline.yaml
tests/fixtures/tasks/task_flaky.yaml
```

请确认：

```text
[ 1] Stage 12-B 第一轮只使用当前 worktree 的 tests/fixtures/tasks 和 tests/fixtures/repos。
[ ] 不再依赖 /Users/roger/Desktop/claude-code/tests/fixtures/repos 这个外部 worktree 路径。
[ 1] Stage 12-B 正式执行前生成 fixture manifest 和 sha256 report。
```

如果你还有更适合真实模型 smoke 的极小仓库任务，可以同步进当前 worktree 后再纳入任务池。不要在正式验收里直接引用另一个 worktree 的路径。

## 4. 最重要的实现前确认：真实模型工具调用协议

### 4.1 当前代码事实

我复查了当前 RepoHarness 和 `reference/verl` 代码后，得到下面结论。

第一，真实 `LLMServerClient.generate(...)` 返回的不是完整 assistant 文本对象，也不是 OpenAI / DeepSeek 风格的结构化 `message.tool_calls`。它返回的是 `TokenOutput`：

```text
TokenOutput.token_ids: 模型生成的 response token ids
TokenOutput.log_probs: 每个 response token 的 log probability，可为空
TokenOutput.routed_experts: 可选 MoE routing 信息
TokenOutput.stop_reason: 生成停止原因
TokenOutput.num_preempted: 可选 preempt 计数
TokenOutput.extra_fields: 额外字段
```

vLLM 和 SGLang 的 async server 都会把底层引擎结果转换成这个 `TokenOutput`。因此，Stage 12-B 不能期待真实 `LLMServerClient` 自动返回 `tool_calls` 字段。

第二，`tokenizer` 会传递到 `RepoHarnessVerlAgentLoop`，再传给 `VerlLLMGateway`。当前链路里 `VerlLLMGateway` 已经使用 tokenizer 做两件事：

```text
prompt side:
  raw messages / tools
  -> verl.utils.chat_template.apply_chat_template(...)
  -> prompt_ids

response side:
  TokenOutput.token_ids
  -> tokenizer.decode(...)
  -> assistant_message.content
```

所以真实模型工具调用解析的自然位置是 `VerlLLMGateway` 或其附近的 adapter 层：先保留 `TokenOutput.token_ids` 和 `log_probs` 作为训练事实，再用 tokenizer 解码出的 assistant text 解析工具调用。

第三，RepoHarness 之前 OpenAI / DeepSeek 链路里的工具调用不是从普通文本里解析出来的。它们走的是 OpenAI-compatible provider response 的结构化字段：

```text
choice.message.tool_calls
-> _parse_tool_calls(...)
-> ToolCall(tool_call_id, tool_name, arguments, turn)
-> ModelResponse.tool_calls
-> AgentLoop 执行工具
```

这段实现可以复用其中的“OpenAI-compatible tool call dict 到 RepoHarness `ToolCall`”转换语义，但不能直接解决 Stage 12-B 的真实问题，因为 vLLM / SGLang 这条 verl rollout 路径给我们的是 token，而不是 provider 已经解析好的 `message.tool_calls`。

第四，`reference/verl` 里确实有可复用的文本工具解析实现：

```text
verl.experimental.agent_loop.tool_parser.HermesToolParser
  解析 <tool_call>...</tool_call> 中的 JSON:
  {"name": "...", "arguments": {...}}

verl.experimental.agent_loop.tool_parser.GptOssToolParser
  解析 gpt-oss / harmony 风格工具调用。

verl.experimental.agent_loop.tool_parser.Qwen3XMLToolParser
  解析 Qwen3 Coder / Qwen3.5 风格 XML 工具调用。
```

其中第一版最适合 Stage 12-B 的是 `HermesToolParser` 风格，因为它简单、可控、和我们计划里的严格 JSON 文本协议一致：

```text
<tool_call>
{"name": "read_file", "arguments": {"path": "calculator.py"}}
</tool_call>
```

### 4.2 推荐实现方向

推荐 Stage 12-B 第一版这样做：

```text
TokenOutput.token_ids / log_probs
-> 保存 token facts 到 GenerationRecordCollector
-> tokenizer.decode(token_ids)
-> Hermes-style parser 提取 <tool_call> JSON
-> FunctionCall(name, arguments)
-> RepoHarness LLMGatewayResponse.tool_calls
-> Stage 12-A 已补强的 tool_calls visibility gate
-> LLMGatewayModelClientAdapter.to_model_response(...)
-> RepoHarness AgentLoop 执行工具
```

这个方向有几个好处：

- 不会破坏 token provenance：训练 token 仍然来自真实 `TokenOutput.token_ids` 和 `log_probs`。
- 不会依赖 fake `repo_harness_tool_calls`，后者只保留给 Stage 12-A 本地 fake server。
- 可以复用 verl 已有 `HermesToolParser` 的 `<tool_call>` 解析思路。
- 可以把 OpenAI / DeepSeek 旧链路的 `ToolCall` 形状和错误分类作为 RepoHarness 侧落地格式。
- 解析失败可以进入已有的 `tool_call_parse_failure` / repair message 语义，而不是把 episode 误报成 infrastructure error。

第一版不要直接引入完整 `ToolAgentLoop`。原因是 `ToolAgentLoop` 自己有工具 registry、tool response 拼接和 reward 处理；RepoHarness 已经有自己的 workspace、工具、verifier、reward、artifact 和 audit 边界。我们应该复用 parser 思路，而不是把 verl 的工具执行系统嵌进 RepoHarness。

Stage 12-A 使用 fake `LLMServerClient` 时，可以把工具调用放在：

```text
TokenOutput.extra_fields["repo_harness_tool_calls"]
```

但这只是本地 fake server 的测试通道。真实 Stage 12-B 中，vLLM / SGLang 返回的是模型生成 token 和文本，真实模型不会自动替 RepoHarness 生成 `repo_harness_tool_calls` 这个字段。

因此，Stage 12-B 正式执行计划必须先确定一件事：

```text
真实模型输出的 assistant text 如何变成 RepoHarness 的 tool_calls？
```

推荐方案：

```text
使用严格文本工具调用协议。
第一版只允许每轮一个工具调用。
格式建议使用 verl 已有 tool parser 类似的 <tool_call>...</tool_call> JSON 结构。
```

示例：

```text
<tool_call>
{"name": "read_file", "arguments": {"path": "calculator.py"}}
</tool_call>
```

Stage 12-B 需要新增或确认：

- `VerlLLMGateway` 或 real episode bridge 可以把 assistant text 解析成 `LLMGatewayResponse.tool_calls`。
- 解析结果必须经过 Stage 12-A 已补强的工具调用 visibility gate。
- 解析失败必须形成结构化 `tool_call_parse_failure` 或可恢复 repair message，不能直接崩溃。
- 解析器不能从模型输出中接受 evaluator-only 字段、绝对本地路径、reward metadata、hidden verifier 或 gold patch。
- 真实模型如果只输出普通 final answer 而没有工具调用，可以形成 rejected episode，但不能被误判为 infra failure。

请确认：

```text
[ ] 同意 Stage 12-B 第一版增加严格文本工具调用解析边界。
[ ] 同意第一版优先复用 / 适配 verl 的 Hermes-style `<tool_call>...</tool_call>` parser。
[ ] 同意第一版先限制为每轮最多一个工具调用，降低并发工具调用和配对复杂度。
[ ] 同意工具格式失败时先记为模型格式失败或可恢复 repair，而不是基础设施失败。
[ ] 同意真实 Stage 12-B 不使用 `TokenOutput.extra_fields["repo_harness_tool_calls"]` 作为工具调用来源；这个字段只保留给本地 fake server 测试。
```

这是 Stage 12-B 成败的关键。模型大小不是最大风险，最大风险是“真实模型输出的文本如何安全、稳定、可审计地变成工具调用”。

### 4.3 新增需要你确认的小问题

下面这些问题会影响正式 Stage 12-B 执行计划里的 parser、prompt 和测试用例。

```text
[ 1 ] 是否同意 Stage 12-B 第一版工具白名单只开放 read_file、grep、edit_file、git_diff，暂不开放 run_tests？
[ 1 ] 是否同意第一版每轮最多一个工具调用；如果模型输出多个 <tool_call>，只执行第一个并把其余记录为 interrupted / ignored diagnostics？
[ ] 是否同意格式探针的最低通过线设为：10 条 prompt 中至少 6 条可解析，其中至少包含 read_file、edit_file、final answer 三类？
[ 1 ] 是否同意 parser 对未知工具名、非法 JSON、数组参数、绝对路径、hidden_verifier、ground_truth、reward_extra_info 都返回模型格式失败或 repair，而不是 infrastructure_error？
[ 2 ] 是否希望我在 Stage 12-B 正式计划里先写一个纯 parser / tokenizer 本地测试，再写远端 GPU tool_format_probe？
```

## 5. 是否需要先在 Mac 本地测试 7B 指令遵循

我的建议是：

```text
需要做一个低成本本地探针，但不要把它作为 Stage 12-B 的正式验收。
```

原因：

- 如果 Mac 本地已经有 Ollama、llama.cpp、MLX 或其他量化版 `Qwen2.5-Coder-7B-Instruct`，可以先用 10 到 20 条极小提示测试 `<tool_call>...</tool_call>` 格式遵循率。
- 这个探针可以提前暴露 prompt 太弱、格式说明不清、parser 太脆的问题。
- 但是 Mac 本地量化模型和 Vast.ai 上 vLLM / SGLang 的 BF16 模型不完全等价，不能代替真实 GPU smoke。
- Mac 本地通常也不能验证真实 `TokenOutput.log_probs`、verl server manager、Ray actor、vLLM / SGLang batching 或 trainer batch。

推荐本地探针范围：

```text
1. tokenizer / chat template dry-run：
   使用 Qwen tokenizer 验证 raw_prompt、tools、system prompt 组合后的 token 长度和特殊 token。

2. parser unit test：
   人工构造合法和非法 <tool_call> 输出，验证 parser、visibility gate 和 repair message。

3. 可选量化模型输出探针：
   如果本地已有模型，测试 read_file、edit_file、final answer 三类输出格式。
```

不推荐在 Mac 本地做：

```text
不推荐为了这一步临时下载和运行完整 BF16 7B。
不推荐把本地 GGUF / MLX 通过率作为 Stage 12-B 是否租卡的硬门槛。
不推荐用本地量化模型产生的结果判断真实 vLLM / SGLang logprob 路径。
```

请确认：

```text
[ ] 在写 Stage 12-B 执行计划前，先做 tokenizer / parser 本地探针。
[ ] 如果你本地已有量化 Qwen2.5-Coder-7B-Instruct，再额外做 10 到 20 条格式遵循探针。
[ ] 如果本地没有量化模型，不为这一步阻塞租卡；GPU 实例启动后先跑 tool_format_probe。
```

我的推荐是：先在 Mac 本地做 tokenizer / parser 探针；量化模型探针可选。真正的指令遵循结论以 Stage 12-B GPU 上的 BF16 模型为准。

## 6. 远端实例需要你准备或确认的信息

请在租好实例并给 SSH 前，尽量确认下面信息。信息越完整，Stage 12-B/C 计划越少返工。

### 6.1 机器和镜像

```text
[ ] Vast.ai 实例 ID。
[ ] GPU 型号和数量，例如 1x RTX PRO 6000 96GB 或 2x RTX PRO 6000 96GB。
[ ] 镜像标签，例如 verlai/verl:vllm011.latest。
[ ] CUDA / driver 是否由镜像和宿主机正常提供。
[ ] 是否可以执行 nvidia-smi。
[ ] 是否有 root 权限或 sudo 权限。
[ ] 是否在容器内直接工作，还是需要手动 docker exec。
[ ] 可用磁盘空间，建议至少 150GB，最好 250GB 以上。
[ ] /dev/shm 大小，建议至少 10GB；如果能配置更大更好。
```

### 6.2 网络和模型下载

```text
[ ] 实例可以访问 Hugging Face。
[ ] 是否需要 HF_TOKEN。
[ ] 模型缓存目录，例如 /workspace/hf_cache。
[ ] 是否允许提前下载 Qwen/Qwen2.5-Coder-7B-Instruct。
[ ] 是否需要使用 ModelScope 镜像源作为备用。
```

Qwen2.5-Coder-7B-Instruct 不是 gated model，但 Hugging Face 下载仍可能受网络、速率或磁盘影响。建议把模型缓存目录固定下来，方便 Stage 12-B 和 Stage 12-C 复用。

### 6.3 RepoHarness 代码部署

```text
[ ] 远端工作目录，例如 /workspace/repo-harness。
[ ] 是否从当前 Git 分支 clone，还是由我通过 rsync/scp 同步当前 worktree。
[ ] 目标 commit，当前 Stage 12-A commit 是 1ce1c0c2。
[ ] 是否需要同步未提交 HTML 汇报文件。默认不需要。
[ ] runs 输出目录，例如 /workspace/repo-harness/runs/stage12b-...
[ ] 是否允许在远端安装额外 Python 包。
```

### 6.4 端口和服务

```text
[ ] 是否允许开放 vLLM / SGLang 服务端口。
[ ] 如果只在本机容器内访问，是否可以使用 localhost。
[ ] Ray dashboard 是否需要开放端口。默认 Stage 12-B 不依赖 dashboard。
[ ] 是否需要 tmux / screen 保持长任务。
```

Stage 12-B 第一轮建议所有服务都只绑定本机或容器内部地址，避免暴露未鉴权接口。

### 6.5 安全和日志

```text
[ ] 不把 HF_TOKEN、SSH 私钥、Vast.ai 凭据写入 RepoHarness artifact。
[ ] 不把 /root、/home、/workspace 外的敏感路径暴露给模型工具。
[ ] 模型工具 workspace 与 run directory 分离。
[ ] artifact 中可以保存模型输出、工具调用、verifier summary 和 reward summary。
[ ] raw provider / raw model response 是否采用 training_fast retention policy。
```

## 7. Stage 12-B 建议分层

正式执行计划可以按下面层级写。

### 12-B-0：远端环境 preflight

只验证环境，不跑 episode。

必须记录：

```text
nvidia-smi
python --version
pip show torch transformers ray vllm sglang verl
git rev-parse HEAD
df -h
free -h
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('Qwen/Qwen2.5-Coder-7B-Instruct')"
```

### 12-B-1：真实模型 tool format probe

只启动模型，不跑完整 RepoHarness。

目标：

- 让真实模型输出 `read_file`、`edit_file`、final answer 三类响应。
- 验证 `<tool_call>...</tool_call>` 或选定工具协议可解析。
- 验证非法字段会被拒绝。
- 记录格式遵循率。

建议判定：

```text
至少 5 条提示中有 3 条输出可解析工具格式，即可进入完整 episode smoke。
如果失败，先调整 prompt / parser，再跑完整 episode。
```

### 12-B-2：单条真实 episode smoke

推荐任务：

```text
tests/fixtures/tasks/task_001.yaml
tests/fixtures/repos/buggy_calculator
```

目标：

- 真实模型至少完成一轮工具调用。
- `response_ids`、`response_mask`、`response_logprobs` 对齐。
- final verifier 真实运行。
- reward boundary 真实运行。
- 如果模型没修好任务，episode 可以是 `failed`，但 infra 不能崩。
- 如果模型修好任务，记录 accepted 正例。

### 12-B-3：小任务池 smoke

建议任务：

```text
task_001.yaml
task_002.yaml
task_003_create_file.yaml
```

目标：

- 至少 3 条真实模型 episode。
- 至少 1 条走到 accepted，或者明确说明 7B 格式遵循 / 修复能力不足但 infra 链路成功。
- 所有 failed / invalid / no-progress / timeout 都有结构化状态。
- visibility gate 和 formal batch validator 通过。

### 12-B-4：边界任务 smoke

建议任务：

```text
task_security_probe.yaml
task_invalid_baseline.yaml
task_flaky.yaml
```

目标：

- 验证 evaluator-only 内容不泄漏。
- 验证 invalid task 不进入 formal online RL batch。
- 验证 flaky / verifier 边界有结构化 diagnostics。

## 8. Stage 12-C 建议分层

Stage 12-C 的目标不是训练收敛，而是验证 tiny batch 能进入 trainer 关键路径。

推荐第一版目标：

```text
优先选择 GRPO-style tiny batch smoke。
如果当前 verl 配置接入 PPO 更顺，则先跑 PPO sync path smoke，但必须记录原因。
```

为什么我倾向先看 GRPO：

- RepoHarness 已经提供 scalar reward，GRPO-style smoke 不需要先解决完整 critic / value model 语义。
- Stage 12-C 重点是 batch 形状、logprob、invalid filtering 和 loss 输入，不是训练质量。

但如果 `reference/verl` 当前配置、脚本和 `main_ppo_sync.py` 对 PPO 路径更容易插入自定义 `RepoHarnessVerlAgentLoop`，则第一版可以先以 PPO sync path 为实际落点。

需要你确认：

```text
[ ] Stage 12-C 第一版优先尝试 GRPO。
[ ] 如果 GRPO 配置成本明显更高，允许先跑 PPO sync path。
[ ] Stage 12-C 不要求收敛，只要求 trainer batch / loss path 可执行并可审计。
```

Stage 12-C 必须固定：

- `calculate_log_probs=True` 或当前 verl 版本等价配置。
- valid 样本必须 `route=verl`。
- valid 样本必须有 `response_logprobs`。
- invalid 样本必须被丢弃、重采样或置零 loss weight，且策略写入 metrics 和 artifact。
- DataProto tensor batch、non-tensor batch、meta_info 都通过 visibility 检查。

## 9. 推荐你现在直接确认的选项

如果你希望我下一步直接写 Stage 12-B / Stage 12-C 执行计划，我建议采用下面默认项：

```text
模型：
  Qwen/Qwen2.5-Coder-7B-Instruct

Stage 12-B GPU：
  1x RTX PRO 6000 96GB

Stage 12-C GPU：
  先尝试同一张 96GB 卡；如 trainer OOM 或资源调度复杂，再租 2x RTX PRO 6000 96GB

镜像：
  verlai/verl:vllm011.latest

推理后端：
  vLLM 作为 Stage 12-B 主 smoke
  SGLang 作为后续 parity smoke

任务：
  优先使用当前 worktree 的 tests/fixtures/tasks/task_001.yaml、task_002.yaml、task_003_create_file.yaml
  边界任务使用 task_security_probe.yaml、task_invalid_baseline.yaml、task_flaky.yaml

工具协议：
  第一版使用严格 <tool_call>...</tool_call> JSON 文本协议
  每轮最多一个工具调用
  parser 失败进入结构化 diagnostics 或 repair，不算 infra crash

Mac 本地提前测试：
  必做 tokenizer / parser dry-run
  如果本地已有量化 Qwen2.5-Coder-7B-Instruct，再做可选格式遵循探针
  不为本地量化模型下载阻塞 GPU smoke
```

## 10. 等你确认后的下一步

你确认上面的默认项后，我会再编写正式的 Stage 12-B 执行计划。正式计划会包含：

- 远端 GPU preflight 命令。
- 模型下载和缓存策略。
- vLLM / verl server manager 启动方式。
- `RepoHarnessVerlAgentLoop` 与真实 `LLMServerClient.generate(...)` 的接入点。
- 工具调用文本协议和 parser 实现边界。
- 极小任务 fixture freeze 和 sha256 manifest。
- 单条 episode smoke 验收。
- 小任务池 smoke 验收。
- visibility、DataProto、formal batch validator 验收。
- 失败分类：infra failure、model format failure、model task failure、invalid task、timeout。

Stage 12-B 通过后，再单独写 Stage 12-C 执行计划，避免把真实模型 episode smoke 和 trainer loss smoke 混在同一个阶段里。