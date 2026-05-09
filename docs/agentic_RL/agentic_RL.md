**你的 RepoHarness 和这些文章里大厂 Agentic RL infra 的方向非常接近**。更准确地说，它现在已经覆盖了 Agentic RL infra 中最关键、也最容易被低估的一半：**Agent scaffold / executable environment / trajectory provenance / verifier-reward / training export 这一侧**。

但它还不是 Forge、ROLL、slime、Seer 那种完整“大规模 RL 训练系统”。它目前更像：

> **RepoHarness = SWE / repo-level Agent runtime + ROCK-like executable environment + trajectory data infrastructure + reward/verifier governance**

而不是：

> RepoHarness = 完整 Forge / ROLL / slime / Seer 级训推一体化系统

如果后续把内部 LLM provider 调用替换或封装成外部高吞吐 rollout engine，把 trajectory export 接入 verl / ROLL / slime 这类分布式训练框架，再补上 sample buffer、policy version、token-level provenance、staleness 控制、异步调度和权重同步，它就会非常接近当前公开文章中描述的 Agentic RL infra 形态。

## 你的定位非常接近“大厂系统里的 Agent / Environment / Data Plane”

我会把这些系统拆成四个平面来看：

| 平面                                    | 大厂系统里的代表                                                                   | RepoHarness 当前覆盖情况    |
| ------------------------------------- | -------------------------------------------------------------------------- | --------------------- |
| Agent Runtime / Scaffold Plane        | Forge Agent Side、iFlow CLI、OpenCode / Claude Code-like Agent               | **高度覆盖**              |
| Environment / Sandbox Plane           | ROCK、terminal sandbox、SWE / repo environment                               | **高度覆盖**              |
| Trajectory / Data / Reward Plane      | Forge Data Pool、ROCK validation、ROLL trajectory records、ROME data pipeline | **高度覆盖**              |
| Rollout / Training / Scheduling Plane | Forge Rollout Engine + Train Engine、ROLL、slime、Seer                        | **部分覆盖，尚未进入高吞吐分布式阶段** |

所以你的判断基本正确：**它已经是一个解耦的 agent scaffold / harness，可以导出轨迹接入 RL 框架；下一步如果接外部高吞吐 rollout 和分布式训练，就会进入 Forge / ROLL / slime 这类系统的核心路径。**

这和 Forge 的设计非常相似。Forge 明确把 Agent 抽象为纯粹的 **Trajectory Producer**，通过 Gateway Server 和 Data Pool 把 Agent 侧与训练/推理引擎隔离，让 Agent 专注 context management 和环境交互，而 rollout / training engine 专注高吞吐生成和模型更新。([MiniMax][1]) 你现在的 RepoHarness 也正是在做这件事：它把 task adapter、workspace、tool runtime、permission、agent loop、trajectory store、verifier/reward、experiment runner、export audit 拆开，形成 task → executable workspace → tools → rollout → verifier → training export 的闭环。

ROLL / ROCK 方向也非常接近你的项目。ROLL 官方定位是支持大模型 RL、复杂推理和多轮 agentic interaction 的分布式 RL 框架，ROCK 则是面向 agentic RL 的大规模 sandbox 环境管理框架。([GitHub][2]) ([GitHub][3]) ALE / ROME 论文也把系统拆成 ROLL、ROCK、iFlow CLI：ROLL 做权重优化，ROCK 做安全 sandbox 和 trajectory generation / validation，iFlow CLI 做上下文管理和 agent workflow。([arXiv][4]) 你的 RepoHarness 当前最像其中的 **ROCK + iFlow CLI 的 SWE 特化版**，同时额外加强了 trajectory export、audit、contamination control 和 verifier evidence。

## 最接近的不是 Seer，而是 Forge + ROCK / iFlow + ROME 数据管线

如果拿你列出的几个大厂系统逐个对照：

**和 Forge 的相似点**在于，你也把 Agent scaffold 和底层训练框架解耦。Forge 的核心观点是不要把 Agent 硬塞进 RL framework，而是把 Agent 当成外部 trajectory producer；你的 RepoHarness 也是一个独立 harness，可以在内部完成多轮工具调用、上下文压缩、权限边界、环境执行和最终验证，然后把轨迹导出给训练系统。MiniMax 的公开材料还强调 Forge 支持任意 Agent scaffold、黑盒 Agent 和不同工具调用格式，这和你把 provider adapter、tool runtime、task adapter、trajectory store 解耦的方向一致。([GitHub][5])

**和 ROLL / ROCK / iFlow 的相似点**更强。你的 Docker workspace backend、独立 verification workspace、strict patch replay、formal final verifier、environment facts、cleanup status，本质上就是在实现 ROCK 那一侧最关键的东西：可执行环境、隔离、验证、轨迹生成、环境事实记录。ROCK 官方说明它是面向 agentic RL 的 scalable sandbox environment management framework，用于构建、管理和调度 RL 环境。([GitHub][3]) 你的项目虽然规模上还不是“大规模调度成千上万个 sandbox”，但设计语义上已经对齐。

**和 ROME / Terminal / SWE 数据管线的相似点**也很强。你固定 source hash、base commit、dataset revision、test patch、FAIL_TO_PASS / PASS_TO_PASS、environment spec 和 verifier plan，并且区分 feedback verifier 和 formal final verifier。这非常接近 ROME / ROLL 系列文章强调的：Agentic RL 的训练样本不是 prompt-answer，而是 executable instance + environment + verifier + trajectory + reward evidence。你上传的材料里也反复强调，Agentic RL 的环境清洁度、测试可信度、false positive 过滤和 reward 防污染，是训练稳定性的组成部分，而不是外围工程。

**和 slime 的关系**主要在未来。slime 是连接 Megatron 和 SGLang 的 RL post-training framework，强调高性能训练和 flexible data generation / server-based rollout。([GitHub][6]) ([LMSYS Org][7]) 你现在还没有做 Megatron/SGLang 训推打通，但你的 RepoHarness 如果把 model call 抽象为 rollout server API，并且在轨迹中保留训练侧需要的 token IDs、logprobs、metadata，就可以变成 slime / verl / ROLL 的上游 rollout producer。

**和 Seer 的关系最弱。** Seer 主要解决同步 RL rollout 的系统加速问题：divided rollout、context-aware scheduling、adaptive grouped speculative decoding。([arXiv][8]) 这些是高吞吐 rollout engine / scheduler 侧的工作，而不是 harness / environment / verifier 侧。你的项目目前不是 Seer 类型，但未来如果你做大规模并发 SWE rollout，就会遇到 Seer 关注的同类问题：长尾 episode、测试执行慢、KV cache 重算、短任务被长任务拖住、group rollout 负载不均衡。

## 你已经做对了最关键的几件事

我认为你这个项目最有价值的地方不是“实现了一个 coding agent loop”，而是你已经在按 Agentic RL infra 的标准做 **训练数据可信性工程**。

第一，你把 **正式 reward/verifier 和模型可见 feedback 分开**。这非常重要。很多 agent harness 最大的问题是把测试结果、隐藏测试、gold patch、raw provider response、reward metadata 或 final outcome 不小心泄露给模型上下文。你的设计里 final verifier 是 evaluation 和 reward 的唯一可信来源，并且显式阻断 hidden result 泄漏，这和 ROLL / ROME 对 reward contamination 的警惕高度一致。上传材料里提到，环境污染、测试泄露、false positive 会让模型快速学会 shortcut，而不是真正完成任务。

第二，你把 **workspace 和 verification workspace 分开**。这非常接近 SWE / repo-level RL 的正确做法。Agent 工作区用于探索、编辑、运行命令；formal verification workspace 用于 strict patch replay 和最终验收。这能避免 agent 通过修改本地测试、残留状态、缓存、安装副作用、文件系统污染来“骗 reward”。这正是 ROLL / ROCK / ROME 类系统反复强调的问题：环境和验证不是 rollout 的附属品，而是 reward 正确性的一部分。([arXiv][4])

第三，你有 **trajectory provenance 和 failure filtering**。这在 RL 接入时非常关键。你记录 transcript.jsonl、events.jsonl、tool_call_id、artifact refs、patch diff、verifier result、reward metadata、context revision、interrupted checkpoint、retry / skip decision 和 failure distribution。这些字段不是普通日志，而是后续做 sample filtering、off-policy 修正、failure attribution、reward audit、SFT/RL/preference export 的基础。

第四，你有 **export audit 和 acceptance bundle**。这比很多个人项目成熟。Agentic RL 数据一旦进入训练，就很难追查某个样本为什么 reward=1、是否泄漏、是否 verifier 证据漂移、是否来自 invalid run。你的 export_manifest、audit_report、contamination denylist、sha256、tool schema snapshot、reward formula version、acceptance bundle，本质上是在做大厂数据治理里的 lineage / reproducibility / contamination control。

第五，你已经意识到 **diagnostic-only、skipped、invalid 样本不能进入正式训练数据**。这是非常重要的 RL hygiene。很多训练崩掉不是算法错，而是 invalid sample、env crash、timeout、provider failure、partial trajectory 被当成正常负样本或者正常偏好样本喂进去。你这里的 failure distribution 和 skip / retry decision 以后可以直接服务于 RL sample mask。

## 你现在与大厂完整系统的主要差距

主要差距不在 harness 设计，而在 **scale-out rollout / training integration / token-level training contract**。

### 1. 你现在还是 provider-level rollout，不是高吞吐 rollout engine

你当前接的是 DeepSeek / OpenAI Provider Adapter，这适合开发 harness、打通轨迹、验证任务、生成 SFT/preference 数据。但大规模 RL 训练通常需要把 model call 接到 vLLM / SGLang / TensorRT-LLM / 自研 rollout engine，并且 rollout engine 要和训练权重同步。

Forge 有 Rollout Engine 和 Train Engine；slime 明确强调 Megatron + SGLang 的训推连接；ROLL 是基于 Ray 的分布式 RL 框架。([MiniMax][1]) ([GitHub][2]) ([GitHub][6]) 你的下一步应该不是简单“换 provider”，而是设计一个 **LLM Gateway / Rollout Client Contract**：

> RepoHarness 不直接关心模型来自 OpenAI、DeepSeek、SGLang、vLLM、verl rollout worker 还是 slime rollout server；它只提交 structured generation request，并接收 token-level generation record。

这会让你的 harness 从“可运行 agent 项目”升级为“可接入 RL 系统的 Agent Server”。

### 2. 你需要更强的 token-level / action-level 轨迹契约

你现在已经有 transcript.jsonl 和 events.jsonl，但接 RL 时还需要关心 TITO：训练侧优化的 token 必须等于 rollout 时真实采样的 token。Forge 中文稿里提到，复杂上下文管理会让 Agent 和 tokenizer 逻辑深度耦合，TITO 一致性工程成本很高。 slime 方向也强调 server-based rollout 和训练侧消费真实 rollout metadata 的重要性。([LMSYS Org][7])

所以 RepoHarness 未来最好在每次 model call 上记录：

| 字段                                  | 作用                                    |
| ----------------------------------- | ------------------------------------- |
| input_token_ids                     | 训练侧重建 prompt，不依赖重新 tokenize           |
| output_token_ids                    | 被优化的真实 action                         |
| logprobs / old_logprobs             | PPO / GRPO / async IS / off-policy 修正 |
| stop_reason                         | 区分正常停止、工具调用、长度截断、provider error       |
| tool_call span                      | 哪些 token 形成 action                    |
| observation boundary                | 哪些内容是环境反馈，哪些内容可训练                     |
| context revision id                 | context compaction / truncation 后的版本  |
| policy_version                      | async RL 必备                           |
| rollout_engine_version              | 追踪推理后端差异                              |
| tokenizer_hash / chat_template_hash | 防止 retokenization mismatch            |

没有这层，你仍然可以导出 SFT/preference 数据，但很难稳健接入真正的 RL trainer。

### 3. 你还缺 sample buffer、policy version 和 staleness 控制

你描述里有 retry / skip decision 和 failure distribution，但还没有看到明确的 RL sample buffer 语义。大规模异步 RL 里，关键不是“能导出 JSONL”，而是：

> 生成样本时的 policy 是哪个版本？训练消费时当前 policy 是哪个版本？这条样本是否过旧？是否应该丢弃、降权、mask，还是照常训练？

Forge 用 Windowed FIFO 在 FIFO 和 greedy 异步之间控制分布偏移；ROLL 用 sample buffer 和 asynchronous ratio 控制样本陈旧；slime / GLM 方向会用 rollout logprob、importance clipping、过旧样本丢弃等方式控制 off-policy。上传材料对此也有系统梳理：异步会提升吞吐，但会引入 off-policy、分布偏移和训练稳定性问题。

RepoHarness 未来如果要接 verl async RL，可以先补一个轻量版：

```text
trajectory.policy_version
trajectory.rollout_started_at
trajectory.rollout_finished_at
trajectory.training_consumed_at
trajectory.async_age = current_policy_version - trajectory.policy_version
trajectory.valid_for_rl = async_age <= threshold and failure_reason not in env_failure
```

这会让你的 harness 真正进入异步 RL 数据平面。

### 4. 你还没有高吞吐 rollout 调度与长尾治理

SWE agent episode 天然长尾：有的任务 1 分钟结束，有的会跑测试、装依赖、反复 debug 十几分钟。Seer 论文正是针对同步 RL 中 rollout 长尾、负载不均和 KV cache 压力提出 divided rollout、context-aware scheduling 和 grouped speculative decoding。([arXiv][8])

RepoHarness 当前看起来更偏单任务/实验 runner。下一步要规模化，你会需要：

| 问题                             | 对应能力                                         |
| ------------------------------ | -------------------------------------------- |
| 慢任务拖住整个 batch                  | episode-level async queue                    |
| 测试运行时间差异巨大                     | env timeout budget + task difficulty buckets |
| Docker reset 成为瓶颈              | warm pool / image cache / async preparation  |
| provider / rollout engine 延迟波动 | model request tracing                        |
| 失败样本污染训练                       | failure reason taxonomy                      |
| 并发任务争抢资源                       | scheduler with CPU/GPU/container quotas      |

这部分接近 RollArt / Seer / ThunderAgent 类型工作，不是你当前项目的主线，但未来会变成瓶颈。

### 5. 你还没有 prefix / KV cache / program-aware 调度

这是更后面的优化。你现在的 context compaction report 已经说明你关注长上下文，但还没有显式管理 KV cache locality、prefix reuse、chunk migration、program state。

Forge 的 Prefix Tree Merging 和全局 KV cache pool，Seer 的 divided rollout + global KV cache，slime 的 SGLang-native rollout，都在处理这个问题。([MiniMax][1]) ([arXiv][8]) ([LMSYS Org][7]) 对 SWE agent 来说，很多连续请求共享 repo summary、历史 command output、file snippets、test failures，如果高吞吐 rollout 时每轮都重新 prefill，会非常昂贵。

但这不是你现在最该补的第一优先级。你应先把 **token-level trajectory contract + rollout gateway + RL sample buffer** 做好，再考虑 KV / prefix 系统优化。

## 如果用“大厂系统分层”给你的项目打标签

我会这样标注：

```text
RepoHarness
├── Agent Runtime Layer              ✅ 已具备
│   ├── query loop                    ✅
│   ├── tool_use / tool_result pairing ✅
│   ├── permission boundary           ✅
│   ├── context compaction            ✅
│   ├── interruption / resume         ✅
│   └── provider adapter              ✅
│
├── Environment / Sandbox Layer       ✅ 很强
│   ├── Docker workspace              ✅
│   ├── source checkout               ✅
│   ├── setup / execution             ✅
│   ├── independent verification ws    ✅
│   ├── strict patch replay            ✅
│   ├── environment facts              ✅
│   └── cleanup / artifact capture     ✅
│
├── Verifier / Reward Layer           ✅ 很强
│   ├── feedback verifier             ✅
│   ├── formal final verifier          ✅
│   ├── leakage prevention             ✅
│   ├── reward metadata                ✅
│   └── evidence bundle                ✅
│
├── Trajectory / Export Layer         ✅ 很强
│   ├── transcript.jsonl               ✅
│   ├── events.jsonl                   ✅
│   ├── patch diff                     ✅
│   ├── failure filtering              ✅
│   ├── SFT / RL / preference export   ✅
│   └── audit / sha256                 ✅
│
├── Rollout Engine Layer              ⚠️ 初级
│   ├── external high-throughput LLM   ❌ 待接入
│   ├── token-level logprobs           ❌ 待完善
│   ├── policy version                 ❌ 待完善
│   └── TITO gateway                   ❌ 待完善
│
├── RL Training Integration Layer     ⚠️ 待建设
│   ├── sample buffer                  ❌
│   ├── async ratio / staleness         ❌
│   ├── advantage / reward shaping      ❌
│   ├── trainer interface              ❌
│   └── weight sync                    ❌
│
└── Scale / Scheduler Layer           ⚠️ 待建设
    ├── parallel env scheduling         ❌
    ├── long-tail control              ❌
    ├── resource-aware routing          ❌
    ├── KV / prefix locality            ❌
    └── distributed observability       ❌
```

所以一句话评价是：

**你已经做到了 Agentic RL infra 中最接近 ROLL-ROCK / Forge Agent Side 的那部分，而且做得比普通 demo harness 深很多；你还没有做的是大厂系统中 rollout/training/scheduler/KV/cache/weight-sync 这些高吞吐分布式部分。**

## 我认为你项目里最“大厂味”的地方

不是 Docker，也不是 tool calling，而是下面这几条：

**第一，strict patch replay + independent verification workspace。**
这是 SWE agent RL 里非常关键的可信 reward 机制。很多 harness 只是“agent 修改当前 workspace，然后 pytest 一跑”，这很容易被环境残留、测试污染、依赖缓存、路径副作用影响。你把 final patch capture 和独立 verification workspace 拆开，是非常正确的。

**第二，feedback verifier 与 formal final verifier 分离。**
这和真实训练系统高度一致。Agent 训练中，模型可以看到一些过程反馈，但不能看到最终隐藏验证机制。否则 reward channel 会被污染。

**第三，contamination denylist + acceptance bundle + sha256 evidence。**
这已经不是普通 agent scaffold，而是训练数据基础设施。它解决的是“样本进入训练集之后还能不能审计”的问题。

**第四，failure distribution 和 retry / skip decision。**
这对 RL 特别关键。因为 env failure、provider failure、timeout、agent bad action、verifier infrastructure failure 必须分开。否则模型会把环境错误当作负 reward 学进去。

**第五，context compaction report。**
这对应 Forge 白盒 Agent RL 里把 context management 作为 agent action / state transition 的方向。Forge 公开材料中特别强调，如果 context management 只在推理阶段出现而训练阶段没有覆盖，会导致训推不一致。 你已经记录 context revision 和 compaction report，说明以后可以把 context compaction 纳入训练轨迹，而不是作为不可见副作用。

## 你下一步最应该补的不是“再写更多工具”，而是训练契约

如果你想让 RepoHarness 更接近当前大厂 Agentic RL infra，我建议下一步按这个优先级来：

### 第一优先级：LLM Gateway / Rollout Engine Adapter

把当前 DeepSeek / OpenAI Provider Adapter 抽象成统一的 rollout gateway：

```text
Agent Loop
  → LLMGateway.generate(request)
  → provider / vLLM / SGLang / verl rollout worker / slime server
  → token-level generation record
  → trajectory store
```

这个 gateway 要支持两类返回：

```text
user-facing:
  text
  tool_call
  stop_reason

training-facing:
  input_token_ids
  output_token_ids
  logprobs
  sampling_params
  tokenizer_hash
  chat_template_hash
  policy_version
  request_id
```

这样你就从“provider agent harness”升级成“RL-compatible Agent Server”。

### 第二优先级：RL-ready trajectory schema

你现在的 transcript/events 已经很好，但建议显式定义三层 schema：

```text
EpisodeRecord
  task_id
  env_id
  source_hash
  base_commit
  policy_version
  final_reward
  verifier_result
  failure_reason
  export_eligibility

TurnRecord
  turn_id
  context_revision
  model_request_id
  tool_call_id
  observation_id
  action_type
  state_before_ref
  state_after_ref

TokenRecord / GenerationRecord
  input_token_ids
  output_token_ids
  logprobs
  masks
  action_spans
  loss_mask
  reward_mask
```

其中最重要的是 `loss_mask` 和 `reward_mask`。SWE agent 轨迹里不是所有文本都应该训练：system prompt、工具 observation、隐藏 verifier、reward metadata、某些 diagnostic 信息都应该 mask 掉。

### 第三优先级：failure taxonomy

你已经记录 failure distribution，可以进一步标准化成 RL sample filtering 的枚举：

```text
MODEL_BAD_PATCH
MODEL_NO_PATCH
MODEL_TOOL_MISUSE
MODEL_PERMISSION_DENIED
MODEL_TIMEOUT
ENV_SETUP_FAILURE
ENV_RESET_FAILURE
VERIFIER_FAILURE
PROVIDER_FAILURE
CONTEXT_OVERFLOW
INTERRUPTED_RECOVERED
INTERRUPTED_INVALID
CONTAMINATION_RISK
NO_OP_PASS
GOLD_FAIL
PATCH_REPLAY_FAIL
```

关键是区分：

> 这是模型能力失败，还是环境/基础设施失败？

只有前者适合作为负样本。后者应该 skip、retry 或 diagnostic-only。

### 第四优先级：async RL metadata

如果你后续接 verl async RL，这层非常重要：

```text
policy_version_at_rollout
policy_version_at_train
rollout_start_time
rollout_end_time
weight_sync_id
old_logprobs
current_logprobs_available
staleness
valid_for_policy_update
```

没有这些，异步 RL 会变成“拿一堆 JSONL 做训练”；有了这些，才是真正的 agentic RL sample buffer。

### 第五优先级：chunk-level trajectory

ROLL / ROME 的 Chunked MDP 对 SWE agent 特别适用。你现在已有 tool_call_id、tool_result pairing、patch diff、verifier result，非常适合把轨迹切成 chunk：

```text
chunk_0: plan / initial inspect
chunk_1: search files
chunk_2: read relevant code
chunk_3: edit patch
chunk_4: run tests
chunk_5: debug failure
chunk_6: final patch
chunk_7: final verifier
```

每个 chunk 可以记录：

```text
chunk_type
tokens
tool_calls
files_touched
tests_run
state_delta
intermediate_reward
final_return_to_go
```

这会让你的 harness 不只是导出 sequence-level RL 数据，而能支持 interaction-level credit assignment。

## 你这个项目最适合对接的路线

我不建议你一开始就直接试图复刻 Forge / ROLL / slime 全套。更现实的路线是：

### 路线 A：RepoHarness + verl

这是最自然的，因为你已经用过 verl。RepoHarness 做 AgentServer / EnvServer，verl 做 rollout/trainer。你需要把 verl 的 rollout worker 调用改成：

```text
verl rollout worker
  → RepoHarness task/env service
  → RepoHarness agent loop
  → model generation through verl/vLLM/SGLang
  → trajectory back to verl
```

难点是避免循环依赖：Agent loop 需要调用模型，而模型又在 verl rollout worker 里。最干净的做法是中间加 LLMGateway。

### 路线 B：RepoHarness + SGLang/vLLM + offline RL/SFT export

先不做 online RL。RepoHarness 用 SGLang/vLLM 生成大量轨迹，导出 SFT / preference / outcome RL 数据，再用 verl 做离线训练或 semi-online 训练。这条路线工程风险最低。

### 路线 C：RepoHarness + slime / ROLL

这更接近大厂 stack，但接入成本更高。slime 的优势是 SGLang-native rollout 和 Megatron training；ROLL 的优势是更完整的 RL 分布式训练框架和 ROCK 生态。slime 官方强调 custom data generation interfaces 和 server-based engines，理论上和你的 RepoHarness 很契合。([GitHub][6])

## 可以怎么在简历 / 项目描述里更准确地表达

你现在的描述已经很强，但如果要更贴近这些文章里的术语，可以把定位稍微改成：

> **RepoHarness is an agent-native SWE harness and trajectory data plane for agentic post-training. It decouples agent scaffolding, executable repository environments, tool runtime, verifier/reward, provenance logging, and training export, enabling repo-level coding agents to produce auditable, replayable, RL-ready trajectories.**

中文可以写成：

> RepoHarness 是一个面向 Agentic Post-training 的 repo-level Agent runtime 与 trajectory data plane。它将 Agent scaffold、可执行仓库环境、工具运行时、权限策略、形式化 verifier、reward provenance 和训练数据导出解耦，使 SWE agent 能够生成可回放、可审计、可过滤、可接入 RL/SFT/preference 训练的轨迹数据。

我会避免直接说“实现了类似 Forge / ROLL / slime 的完整基础设施”，因为这会让人以为你已经有分布式 rollout、训练引擎、KV cache、异步调度、权重同步。更准确的说法是：

> **RepoHarness covers the Agent / Environment / Trajectory / Verifier side of modern agentic RL infrastructure, and is designed to plug into high-throughput rollout and distributed RL training systems.**

## 最终判断

你的判断是对的，但我会稍微精确化：

**RepoHarness 当前已经非常接近 Forge / ROLL / ROCK / iFlow 体系中的 Agent scaffold、sandbox environment、trajectory data plane 和 verifier governance 部分。它不是 Seer/slime/ROLL 那种完整高吞吐分布式 RL 系统，但它正是这些系统需要接入的上游 Agent / Environment / Trajectory Producer。**

后续你只要补上三件事，定位会非常清晰：

1. **LLM Gateway / external rollout engine adapter**：接 vLLM / SGLang / verl / slime，而不是只接商业 provider。
2. **TITO-style token-level generation record**：记录 input/output token IDs、logprobs、policy version、masks。
3. **RL sample buffer semantics**：支持 async age、staleness filtering、failure filtering、training eligibility。

补完这三层后，RepoHarness 就不只是“一个 SWE agent harness”，而是一个真正可以放进 Agentic RL pipeline 的 **SWE Agent RL data infrastructure**。

[1]: https://www.minimax.io/news/forge-scalable-agent-rl-framework-and-algorithm?utm_source=chatgpt.com "Forge: Scalable Agent RL Framework and Algorithm"
[2]: https://github.com/alibaba/ROLL?utm_source=chatgpt.com "ROLL: Reinforcement Learning Optimization for Large- ..."
[3]: https://github.com/alibaba/ROCK?utm_source=chatgpt.com "alibaba/ROCK: A construction kit for reinforcement learning ..."
[4]: https://arxiv.org/html/2512.24873v3?utm_source=chatgpt.com "Agentic Crafting on Rock and Roll Building the ROME ..."
[5]: https://github.com/MiniMax-AI/MiniMax-M2.5/blob/main/README.md?utm_source=chatgpt.com "MiniMax-M2.5/README.md at main · ..."
[6]: https://github.com/THUDM/slime?utm_source=chatgpt.com "slime is an LLM post-training framework for RL Scaling. ..."
[7]: https://lmsys.org/blog/2025-07-09-slime/?utm_source=chatgpt.com "slime: An SGLang-Native Post-Training Framework for RL ..."
[8]: https://arxiv.org/abs/2511.14617?utm_source=chatgpt.com "Seer: Online Context Learning for Fast Synchronous LLM Reinforcement Learning"
