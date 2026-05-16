# Stage 12-B / Stage 12-C 执行计划

```text
status: execution_plan
created_at: 2026-05-17
depends_on:
  - 01-sequential-implementation-plan.md
  - 16-stage-12-a-execution-plan.md
  - 17-stage-12-bc-gpu-preflight-confirmation.md
  - Stage 12-A commit 1ce1c0c2
  - Stage 12-B/C preflight commit a36089df
target_environment:
  - Vast.ai 或同类远端 Linux GPU 实例
  - image: verlai/verl:sgl056.latest
  - disk: 300GB
  - first_model: Qwen/Qwen2.5-Coder-7B-Instruct
scope:
  - Stage 12-B: 真实模型端到端 smoke
  - Stage 12-C: 小 batch trainer smoke
not_scope:
  - 不追求训练收敛
  - 不直接上 SWE-Bench
  - 不把模型失败误判为基础设施失败
```

## 1. 当前决策

本阶段采用下面固定决策。

```text
模型：
  Qwen/Qwen2.5-Coder-7B-Instruct

Stage 12-B 远端实例：
  先使用单卡 RTX PRO 6000 96GB
  硬盘空间 300GB

Stage 12-B 主后端：
  SGLang

Stage 12-B 镜像：
  verlai/verl:sgl056.latest

Stage 12-B parity 后端：
  vLLM
  后续使用 verlai/verl:vllm011.latest 或同等 vLLM 镜像补测

Stage 12-C：
  Stage 12-B 通过后再执行
  优先尝试同一张 96GB 卡
  如果 trainer OOM 或 Ray 资源调度复杂，再切换双卡

任务：
  只使用当前 worktree 已有极小 fixture
  不依赖 /Users/roger/Desktop/claude-code 中的可变路径

工具协议：
  严格 Hermes-style <tool_call>...</tool_call> JSON 文本协议
  第一版每轮最多一个工具调用
  工具白名单：read_file、grep、edit_file、git_diff
  暂不开放 run_tests
```

Stage 12-B 先验证真实模型、真实 tokenizer、真实 SGLang 推理服务、真实 log probability、RepoHarness real episode、workspace、工具、final verifier、reward、artifact 和 verl postprocess。Stage 12-C 再验证 tiny batch 能进入 trainer loss 关键路径。

## 2. 总体执行顺序

整体顺序固定为：

```text
12-B-0：远端环境 preflight
12-B-1：fixture freeze 和 sha256 manifest
12-B-2：严格工具调用 parser / gateway 接入
12-B-3：真实模型 tool_format_probe
12-B-4：单条真实 episode smoke
12-B-5：小任务池真实 episode smoke
12-B-6：边界任务 smoke
12-B-7：Stage 12-B evidence bundle 和可见性审计
12-C-0：trainer smoke 配置 preflight
12-C-1：tiny batch DataProto / formal validator smoke
12-C-2：PPO 或 GRPO trainer loss path smoke
12-C-3：Stage 12-C evidence bundle
```

Stage 12-C 必须等 Stage 12-B 至少完成下面条件后再开始：

```text
真实 SGLang 后端可生成 TokenOutput.token_ids 和 log_probs
至少一条 real_episode 跑到结构化 RepoHarnessEpisodeResult
TrainingView -> AgentLoopOutput -> DataProto 路径通过 visibility 和 shape 检查
invalid / failed 样本不会进入 formal online RL valid batch
run directory、artifact、timing、resource、reward evidence 可回查
```

## 3. Stage 12-B-0：远端环境 preflight

拿到 SSH 后先做只读环境记录，不跑 episode。

建议远端工作目录：

```text
/workspace/repo-harness
/workspace/hf_cache
/workspace/runs
```

建议初始化命令：

```bash
set -euxo pipefail

mkdir -p /workspace /workspace/hf_cache /workspace/runs
cd /workspace

git clone -b codex/repo-harness-verl-stage0h git@github.com:Rogerffff/RepoHarness.git repo-harness
cd /workspace/repo-harness

git rev-parse HEAD
git status --short
```

如果远端没有 GitHub SSH key，可改用 HTTPS 或由本地同步 worktree；但正式 report 必须记录代码来源、分支和 commit。

环境记录命令：

```bash
set -euxo pipefail

cd /workspace/repo-harness

{
  echo "### date"
  date -u
  echo "### hostname"
  hostname
  echo "### git"
  git rev-parse HEAD
  git status --short
  echo "### nvidia-smi"
  nvidia-smi
  echo "### python"
  python --version
  which python
  echo "### disk"
  df -h
  echo "### memory"
  free -h || true
  echo "### shm"
  df -h /dev/shm || true
  echo "### packages"
  python - <<'PY'
import importlib.metadata as md
for name in ["torch", "transformers", "ray", "verl", "vllm", "sglang", "flashinfer_python"]:
    try:
        print(name, md.version(name))
    except Exception as exc:
        print(name, "missing", type(exc).__name__)
PY
  echo "### torch cuda"
  python - <<'PY'
import torch
print("cuda_available", torch.cuda.is_available())
print("device_count", torch.cuda.device_count())
for idx in range(torch.cuda.device_count()):
    print(idx, torch.cuda.get_device_name(idx), torch.cuda.get_device_properties(idx).total_memory)
PY
} | tee /workspace/runs/stage12b_env_preflight.log
```

模型 tokenizer 预检：

```bash
set -euxo pipefail

export HF_HOME=/workspace/hf_cache
export TRANSFORMERS_CACHE=/workspace/hf_cache

if python - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("hf_transfer") else 1)
PY
then
  export HF_HUB_ENABLE_HF_TRANSFER=1
  echo "hf_transfer_available=true"
else
  unset HF_HUB_ENABLE_HF_TRANSFER
  echo "hf_transfer_available=false"
fi

python - <<'PY' | tee /workspace/runs/stage12b_tokenizer_preflight.log
from transformers import AutoTokenizer

model_id = "Qwen/Qwen2.5-Coder-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
messages = [
    {"role": "system", "content": "You are RepoHarness software engineering agent."},
    {"role": "user", "content": "Read calculator.py and fix divide."},
]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
print("model_id", model_id)
print("chat_template_present", bool(getattr(tokenizer, "chat_template", None)))
print("prompt_chars", len(text))
print("prompt_tokens", len(ids))
print(text[:1000])
PY
```

验收：

- `nvidia-smi` 正常。
- `torch.cuda.is_available()` 为 `True`。
- `sglang`、`verl`、`ray` 可以导入。
- `AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")` 可以加载。
- 磁盘至少有 150GB 可用；300GB 实例应满足。

## 4. Stage 12-B-1：fixture freeze 和 sha256 manifest

本阶段不依赖另一个 worktree。任务池固定为当前仓库内 fixture。

正例任务：

```text
tests/fixtures/tasks/task_001.yaml
tests/fixtures/tasks/task_002.yaml
tests/fixtures/tasks/task_003_create_file.yaml
```

边界任务：

```text
tests/fixtures/tasks/task_security_probe.yaml
tests/fixtures/tasks/task_invalid_baseline.yaml
tests/fixtures/tasks/task_flaky.yaml
```

需要新增或生成：

```text
runs/stage12b-<timestamp>/
  fixture_manifest.json
  fixture_sha256_report.json
```

建议命令：

```bash
set -euxo pipefail

cd /workspace/repo-harness
RUN_ROOT="/workspace/runs/stage12b-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_ROOT"

python - <<'PY' "$RUN_ROOT"
import hashlib
import json
import sys
from pathlib import Path

run_root = Path(sys.argv[1])
paths = [
    Path("tests/fixtures/tasks/task_001.yaml"),
    Path("tests/fixtures/tasks/task_002.yaml"),
    Path("tests/fixtures/tasks/task_003_create_file.yaml"),
    Path("tests/fixtures/tasks/task_security_probe.yaml"),
    Path("tests/fixtures/tasks/task_invalid_baseline.yaml"),
    Path("tests/fixtures/tasks/task_flaky.yaml"),
]
repo_roots = [
    Path("tests/fixtures/repos/buggy_calculator"),
    Path("tests/fixtures/repos/import_config_bug"),
    Path("tests/fixtures/repos/missing_helper_file"),
    Path("tests/fixtures/repos/security_probe"),
    Path("tests/fixtures/repos/baseline_invalid"),
    Path("tests/fixtures/repos/flaky_counter"),
]
files = []
for path in paths:
    files.append(path)
for root in repo_roots:
    for file in sorted(root.rglob("*")):
        if file.is_file() and "__pycache__" not in file.parts and not file.name.endswith(".pyc"):
            files.append(file)
records = []
for file in sorted(set(files)):
    data = file.read_bytes()
    records.append({
        "path": file.as_posix(),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
payload = {
    "schema_version": "repo_harness_stage12b_fixture_manifest_v0",
    "records": records,
}
(run_root / "fixture_manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_root / "fixture_sha256_report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(run_root)
print(len(records))
PY
```

验收：

- manifest 中没有 `__pycache__` 和 `.pyc`。
- manifest 只引用当前 repo 内路径。
- 后续 Stage 12-B result report 记录这个 manifest 路径。

## 5. Stage 12-B-2：严格工具调用 parser / gateway 接入

### 5.1 当前必须补的实现边界

真实 `LLMServerClient.generate(...)` 返回 `TokenOutput.token_ids` 和 `TokenOutput.log_probs`。它不会像 Stage 12-A fake server 那样返回：

```text
TokenOutput.extra_fields["repo_harness_tool_calls"]
```

因此 Stage 12-B 必须在 `repo_harness_verl` adapter 层补一条真实模型文本工具解析路径。

推荐新增：

```text
src/repo_harness_verl/tool_parser.py
tests/unit/test_repo_harness_verl_stage12b_tool_parser.py
```

推荐修改：

```text
src/repo_harness_verl/gateway.py
src/repo_harness_verl/agent_loop.py
```

### 5.2 模型可见工具协议提示词

真实 episode 和 `tool_format_probe` 必须使用同一份模型可见工具协议说明。该说明应作为 Stage 12-B 的一个显式 artifact 保存，并记录：

```text
tool_protocol_prompt_version
tool_protocol_prompt_sha256
tool_protocol_prompt_path
```

提示词内容只能包含：

```text
允许工具列表
每个工具的参数格式
Hermes-style <tool_call>...</tool_call> 输出格式
合法示例
final answer 的输出要求
```

提示词内容不得包含：

```text
hidden verifier
gold patch
accepted label
完整 reward metadata
evaluator-only 日志
provider secret
本地绝对路径
```

如果 Stage 12-B 因真实模型格式不稳定而调整工具协议提示词，必须生成新的版本号和 sha256，不能覆盖旧版本。执行报告中需要说明每个 smoke 使用的是哪一个 prompt version。

### 5.3 Parser 规则

第一版采用 Hermes-style 严格文本协议：

```text
<tool_call>
{"name": "read_file", "arguments": {"path": "calculator.py"}}
</tool_call>
```

parser 输入：

```text
assistant_text: str
turn: int
allowed_tool_names: set[str]
```

parser 输出：

```text
content: str
tool_calls: list[dict]
diagnostics: list[dict]
```

落地到 RepoHarness 时，每个 tool call 必须是：

```json
{
  "tool_call_id": "repo_harness_verl_tool_call_<turn>_<index>",
  "tool_name": "read_file",
  "arguments": {"path": "calculator.py"}
}
```

第一版硬边界：

- 每轮最多执行一个工具调用。
- 如果模型输出多个 `<tool_call>`，只执行第一个，其余记录 `ignored_extra_tool_calls` diagnostics。
- 只允许 `read_file`、`grep`、`edit_file`、`git_diff`。
- 不允许 `run_tests`。
- `arguments` 必须是 JSON object。
- parser 需要拒绝数组参数、字符串参数、非法 JSON、未知工具名、绝对路径、`hidden_verifier`、`ground_truth`、`reward_extra_info`、`provider_secret`。
- Stage 12-B 第一版不做自动 repair；parser failure 统一归类为 `model_format_failure`，不归类为 `infrastructure_error`。
- 如果后续阶段启用可恢复 repair，repair 模型调用也必须计入 `max_model_calls`、`used_model_calls`、`TimingSummary.model_call_count`、`TimingSummary.model_call_seconds` 和 `BudgetConsumption`，并且必须记录 `repair_attempt_count` 与 `repair_stop_reason`。

### 5.4 Gateway 接入

`VerlLLMGateway` 处理真实 `TokenOutput` 时应按下面顺序：

```text
TokenOutput.token_ids / log_probs
-> 保存 output_token_ids / output_logprobs
-> tokenizer.decode(token_ids)
-> assistant_text
-> parser 提取 tool_calls
-> tool_calls visibility gate
-> LLMGatewayResponse(
     assistant_message.content = 去掉 tool_call block 后的 content
     tool_calls = parsed tool_calls
     output_token_ids = 原始 token_ids
     output_logprobs = 原始 log_probs
   )
```

重要要求：

- 不得因为去掉 `<tool_call>` 文本而修改 `output_token_ids`。
- `TrainingView.response_ids` 仍必须来自真实 `TokenOutput.token_ids`。
- parser 只影响 tool execution，不影响 token provenance。
- Stage 12-A fake `repo_harness_tool_calls` 通道仍可保留，但真实 Stage 12-B 不使用它。

### 5.5 单元测试

新增测试必须覆盖：

```text
合法 read_file
合法 grep
合法 edit_file
合法 final answer 无 tool_call
多个 tool_call 只执行第一个并记录 diagnostics
非法 JSON
arguments 是数组
未知工具名
绝对路径 /Users/... 或 /root/...
hidden_verifier / ground_truth / reward_extra_info 驼峰或蛇形写法
解析后的 tool_calls 不进入 extra_fields
output_token_ids / output_logprobs 不因 parser 改变
```

验收命令：

```bash
PYTHONPATH=src:reference/verl uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage12b_tool_parser.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage12a_local_preflight.py
```

## 6. Stage 12-B-3：真实模型 tool_format_probe

这一步在远端 GPU 上执行。它只验证真实模型输出格式，不跑完整 RepoHarness episode。

### 6.1 启动真实 SGLang / verl rollout 服务

具体启动命令以 `verlai/verl:sgl056.latest` 中可用入口为准。执行计划中的约束是：

```text
模型：Qwen/Qwen2.5-Coder-7B-Instruct
tensor_parallel_size：单卡时为 1
dtype：bfloat16 或镜像默认安全值
max_model_len：先用 8192 或更低，避免无意义占用
logprobs：必须开启
host：127.0.0.1 或容器内本地地址
```

如果走 verl 内部 `LLMServerClient` 和 Ray actor 启动路径，必须记录：

```text
Ray address
server actor ids
SGLang server pid / log path
model path
tokenizer path
```

如果第一轮为了快速确认模型工具格式而直接调用 SGLang HTTP API，也可以作为 `tool_format_probe` 的前置诊断，但不能替代 Stage 12-B-4 的 `RepoHarnessVerlAgentLoop -> LLMServerClient.generate(...)` 证据。

### 6.2 10 条 prompt 探针

准备 10 条 prompt：

```text
read_file 类：3 条
grep 类：2 条
edit_file 类：3 条
final answer 类：2 条
```

最低通过线：

```text
至少 6 / 10 条可解析
通过样本必须覆盖 read_file、edit_file、final answer 三类
非法字段不能通过 parser / visibility gate
```

这个阈值不是模型能力评价，也不是任务成功率。它只用于判断 prompt 和 parser 是否足以进入完整 episode。

输出 evidence：

```text
runs/stage12b-<timestamp>/
  tool_format_probe/
    prompts.jsonl
    raw_generations.jsonl
    parsed_tool_calls.jsonl
    parser_diagnostics.jsonl
    tool_format_probe_summary.json
```

`tool_format_probe_summary.json` 至少包含：

```json
{
  "schema_version": "repo_harness_stage12b_tool_format_probe_summary_v0",
  "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
  "backend": "sglang",
  "image": "verlai/verl:sgl056.latest",
  "prompt_count": 10,
  "parse_success_count": 0,
  "required_categories_covered": false,
  "can_continue_to_real_episode_smoke": false,
  "failure_examples": []
}
```

如果低于阈值：

- 先调整 system prompt / tool instructions。
- 再调整 parser 容错，但不能放松 visibility。
- 不直接进入完整 episode。

## 7. Stage 12-B-4：单条真实 episode smoke

首条任务：

```text
tests/fixtures/tasks/task_001.yaml
tests/fixtures/repos/buggy_calculator
```

目标链路：

```text
RepoHarnessVerlAgentLoop.run(...)
-> RepoHarnessRuntime.run_episode(...)
-> runtime_execution_mode=real_episode
-> RepoHarness agent loop
-> VerlLLMGateway
-> real LLMServerClient.generate(...)
-> SGLang AsyncLLMServer
-> real TokenOutput.token_ids / log_probs
-> parser 提取 tool_calls
-> RepoHarness tool execution
-> final verifier pytest
-> reward boundary
-> TrainingView
-> AgentLoopOutput
-> AgentLoopOutput.as_dict()
-> AgentLoopWorker._agent_loop_postprocess(...)
-> DataProto visibility / shape checks
```

验收点：

- 至少发生一次真实模型调用。
- `generation_records[*].gateway_route == "verl"`。
- `generation_records[*].output_token_ids` 非空。
- `generation_records[*].output_logprobs` 非空，并与 token 长度一致。
- `TrainingView.response_ids` 与 assistant generation spans 可对齐。
- 工具 observation span 的 `response_mask=0` 且 `response_logprobs=0.0`。
- 如果模型输出工具调用，工具调用必须经过 parser 和 visibility gate。
- final verifier 真实运行。
- reward boundary 真实运行。
- episode 可以 `succeeded` 或 `failed`；如果 failed 是模型没修好，不能标成 infrastructure failure。
- `AgentLoopOutput.as_dict()` 和 DataProto 后处理通过 shape / visibility 检查。
- `training_fast` artifact 不保存完整 raw secret 或 evaluator-only 内容。

输出 evidence：

```text
runs/stage12b-<timestamp>/
  single_episode/
    episode_result.json
    training_view.json
    agent_loop_output_summary.json
    dataproto_shape_report.json
    visibility_report.json
    artifact_manifest_ref.txt
    timing_resource_report.json
```

## 8. Stage 12-B-5：小任务池真实 episode smoke

任务：

```text
task_001.yaml
task_002.yaml
task_003_create_file.yaml
```

推荐配置：

```text
parallel_episodes: 1 或 2
max_turns: 6
max_model_calls: 6
max_tool_calls: 6
max_output_tokens: 512
max_prompt_tokens: 8192
generation_timeout_seconds: 120
episode_timeout_seconds: 600
```

验收：

- 三条 episode 都返回结构化 `RepoHarnessEpisodeResult`。
- 至少一条 episode 走到 accepted，或者明确记录模型能力 / 格式遵循不足但基础设施链路成功。
- 所有 rejected / failed episode 的 `status`、`status_reason`、`reward`、`invalid_for_online_rl` 清晰。
- formal batch validator 只接受 valid `route=verl` 样本。
- failed 但 token/logprob 完整的样本是否进入训练，由 Stage 12-C 的 loss 策略决定；Stage 12-B 只记录可训练资格，不实际训练。

## 9. Stage 12-B-6：边界任务 smoke

任务：

```text
task_security_probe.yaml
task_invalid_baseline.yaml
task_flaky.yaml
```

目标：

- `security_probe`：模型工具不能访问 run directory、reward metadata、hidden verifier、gold patch、绝对宿主路径。
- `task_invalid_baseline`：应产生 `invalid_task` 或结构化 invalid，不进入 formal online RL valid batch。
- `task_flaky`：应有 verifier / reward diagnostics，不把 flaky 或 verifier 问题伪装成成功训练样本。

验收：

- visibility negative case 稳定拒绝。
- invalid 样本不会被 `validate_formal_online_rl_batch(...)` 接受。
- DataProto non-tensor batch 和 meta_info 无 evaluator-only 字段。

## 10. Stage 12-B-7：结果报告和通过标准

Stage 12-B 通过标准：

```text
环境 preflight 完成并保存。
fixture manifest 和 sha256 report 完成。
tool_format_probe 达到最低通过线。
单条真实 episode 通过基础设施链路。
小任务池至少返回结构化结果。
DataProto shape / visibility 通过。
formal batch validator 正确区分 valid 和 invalid 样本。
artifact、timing、resource、reward evidence 可回查。
所有失败都归类为 infra failure、model format failure、model task failure、invalid task、timeout 或 no-progress。
```

Stage 12-B 不要求：

```text
不要求 7B 模型每条任务都修好。
不要求训练 loss 执行。
不要求模型收敛。
不要求 vLLM parity 同时完成；如果未完成，记录为 follow-up。
```

建议汇总文件：

```text
runs/stage12b-<timestamp>/
  stage12b_acceptance_summary.json
  stage12b_command_log.jsonl
  stage12b_failure_taxonomy_report.json
  stage12b_visibility_matrix_report.json
  stage12b_timing_resource_report.json
```

## 11. Stage 12-C-0：trainer smoke 配置 preflight

Stage 12-C 在 Stage 12-B 通过后执行。第一版目标是 tiny batch trainer loss path smoke，不追求收敛。

优先方向：

```text
先尝试 GRPO-style tiny batch smoke。
如果当前 verl 配置接入 PPO sync path 更直接，可以先执行 PPO sync path smoke，并记录原因。
```

Stage 12-C 开始前需要确认：

```text
actor_rollout_ref.rollout.calculate_log_probs=True 或当前 verl 等价配置
batch_size 极小，例如 1 到 2
mini_batch_size 极小，例如 1
max_prompt_length / max_response_length 与 Stage 12-B smoke 对齐
invalid 样本处理策略：丢弃、重采样或置零 loss weight
```

## 12. Stage 12-C-1：tiny batch DataProto / formal validator smoke

输入：

```text
Stage 12-B 产生的 1 到 3 条 RepoHarnessEpisodeResult
```

操作：

```text
RepoHarnessEpisodeResult
-> TrainingView
-> validate_training_view_for_online_rl(...)
-> validate_formal_online_rl_batch(...)
-> AgentLoopOutput
-> AgentLoopOutput.as_dict()
-> DataProto
```

验收：

- valid 样本必须 `route=verl`。
- `generation_records` 必须非空。
- `generation_records[*].gateway_route` 必须全部为 `verl`。
- `TrainingView.online_rl_eligible` 必须为 `True`。
- `TrainingView.extra_fields["repo_harness_invalid_for_online_rl"]` 必须不是 `True`。
- valid 样本必须有 `response_logprobs`。
- `response_ids`、`response_mask`、`response_logprobs` 长度一致。
- `rollout_log_probs` tensor shape 为 `[batch_size, rollout.response_length]`。
- `rm_scores` tensor shape 为 `[batch_size, rollout.response_length]`。
- mixed route、missing logprobs、overflow、empty response 必须在进入 trainer 前被过滤或拒绝，并写入审计报告。
- invalid / failed / timeout / no-progress 样本处理策略写入 metrics。

## 13. Stage 12-C-2：trainer loss path smoke

第一版只要求 tiny trainer path 能执行一个很小步骤。

建议执行策略：

```text
优先只跑 1 个 global step。
关闭长时间保存 checkpoint。
关闭不必要 eval。
保存最小 metrics 和 command log。
```

如果使用 GRPO：

```text
验证 scalar reward / group reward 路径可接收 RepoHarness reward。
验证 invalid 样本不会进入有效 loss。
```

如果使用 PPO sync path：

```text
验证 prompts / responses / response_mask / rollout_log_probs / rm_scores 可进入 trainer。
记录是否需要 critic / value model，以及第一版如何最小化该配置。
```

验收：

- trainer 进入 loss path 或明确到达当前 smoke 定义的最后一步。
- 没有因为 DataProto shape、missing logprobs、visibility 字段导致崩溃。
- 如果 OOM，记录显存、batch、sequence length 和建议切双卡，不把 OOM 误判为 contract failure。

## 14. Stage 12-C-3：结果报告和通过标准

Stage 12-C 通过标准：

```text
tiny batch 可以由 RepoHarness episode 结果构造。
formal batch validator 在 trainer 前执行。
valid / invalid 样本处理可审计。
DataProto shape 和 visibility 通过。
trainer loss path 至少执行到预定 smoke 终点。
失败时有明确分类和下一步建议。
```

Stage 12-C 不要求：

```text
不要求 loss 下降。
不要求模型质量提升。
不要求 checkpoint 可用于后续评测。
不要求多机多卡。
```

建议汇总文件：

```text
runs/stage12c-<timestamp>/
  stage12c_acceptance_summary.json
  stage12c_command_log.jsonl
  stage12c_dataproto_report.json
  stage12c_loss_path_report.json
  stage12c_invalid_sample_policy_report.json
```

## 15. 远端执行前用户需要提供的信息

你租好实例后，请提供：

```text
SSH 连接方式
实例 GPU 型号和数量
镜像实际标签
工作目录约定
是否已有 Hugging Face token
是否允许使用 /workspace/hf_cache 下载模型
是否使用 root 用户进入容器
是否需要通过 tmux 保持长任务
```

如果 SSH 到位后发现镜像不是 `verlai/verl:sgl056.latest`，或者 GPU 不是单卡 96GB，本计划仍可执行，但 Stage 12-B-0 必须记录差异，并由执行 agent 决定是否需要调整后端、batch、sequence length 或模型下载策略。

## 16. 本地提交前验收命令

正式实现 Stage 12-B 代码前，本地至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage12a_local_preflight.py

git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/18-stage-12-bc-execution-plan.md \
  src/repo_harness_verl \
  tests/unit \
  tests/integration
```

Stage 12-B 代码实现完成后，还必须重新运行 Stage 12-A 本地 smoke：

```bash
PYTHONPATH=src:reference/verl uv run --extra dev \
  --with numpy \
  --with torch \
  --with ray \
  --with tensordict \
  --with hydra-core \
  --with omegaconf \
  --with pillow \
  --with transformers \
  --with datasets \
  --with torchdata \
  --with codetiming \
  --with cachetools \
  --with uvicorn \
  --with fastapi \
  --with requests \
  --with aiohttp \
  --with prometheus-client \
  python -m pytest -q \
    tests/unit/test_repo_harness_verl_stage12a_local_preflight.py \
    tests/integration/test_repo_harness_verl_stage12a_real_episode_smoke.py \
    tests/integration/test_repo_harness_verl_stage12a_visibility_dataproto.py \
    tests/integration/test_repo_harness_verl_stage12a_concurrency.py
```

## 17. 失败分类

Stage 12-B/C 的失败必须按下面类别记录：

```text
environment_preflight_failed:
  远端环境、镜像、CUDA、包、磁盘、模型下载问题。

backend_start_failed:
  SGLang / Ray / server manager 启动失败。

model_format_failure:
  模型没有按工具协议输出，或 parser / visibility 拒绝模型输出。

model_task_failure:
  模型输出格式可用，但没有修好任务，final verifier rejected。

repo_harness_runtime_failure:
  workspace、tool、verifier、reward、artifact、resource lease 等 RepoHarness 路径异常。

verl_adapter_failure:
  RepoHarnessVerlAgentLoop、VerlLLMGateway、AgentLoopOutput、postprocess、DataProto 转换异常。

formal_batch_rejected_expected:
  invalid 样本被 formal validator 正确拒绝。

trainer_smoke_failure:
  Stage 12-C trainer loss path 报错、OOM 或配置错误。
```

任何失败都必须写入 command log 和 summary，不允许只在终端输出中存在。
