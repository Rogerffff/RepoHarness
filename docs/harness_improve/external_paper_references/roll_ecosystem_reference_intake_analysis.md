# ROLL / ROCK / ROME 生态参考资料接入分析

本文记录本轮对阿里 ROLL 生态的资料拉取、代码阅读和架构判断。它的目标不是重新写一份 ROLL 论文综述，而是回答一个更直接的问题：

```text
ROLL / ROCK / iFlow CLI / Terminal-Bench-Pro 这一组完整 agentic RL 系统，
对 RepoHarness 当前的长期定位、环境服务设计、黑盒 harness 训练和训练后端适配，
到底补充了什么？哪些内容应该进入参考池？哪些内容已有参考已经足够？
```

## 1. 总结结论

ROLL 生态应该加入 RepoHarness 的外部参考池，而且值得作为 P0 级系统参考继续跟踪，但它不需要推翻当前 `repo_harness_repositioning_after_polar.md` 的主方向。

当前主方向仍然成立：

```text
Prime-style composable environment
  + Polar-style rollout-as-a-service / model proxy
  + renderers-style token fidelity
  + verl / slime adapter
```

ROLL 生态补充的是另外三块以前相对薄的工程证据：

1. `ROCK` 证明环境执行不只是“启动一个 Docker sandbox”。大规模 agentic RL 需要独立的 sandbox lifecycle service、环境仓库、agent 安装、运行时代理、网络策略、模型服务代理和轨迹 record/replay。

2. `Agent Native Mode` 证明黑盒或半黑盒 CLI harness 可以保留自己的上下文管理、工具协议和部署行为，训练系统只在模型调用边界做代理和捕获。这一点和 Polar 的 model API capture 思路一致，但 ROCK 把 proxy 放进 sandbox / environment service 侧，进一步强调“训练与部署 harness 一致性”。

3. `RollArt` 证明 agentic RL 的异步问题不只是“rollout 写 artifact，trainer 读取 batch”。真实系统还需要轨迹级异步、EnvManager、LLMProxy、SampleBuffer、serverless reward、权重版本握手、staleness 上界、长尾环境处理和后端消费确认。

因此，ROLL 生态最适合补强以下设计面：

```text
P0: ROCK-style sandbox / environment service reference
P0: sandbox-side ModelProxyService / Agent Native Mode
P0: trajectory-level async runtime coordination reference
P1: reward service / serverless evaluator offload reference
P1: Terminal-Bench-Pro style environment and benchmark production reference
P2: IPA semantic interaction chunk credit assignment, 留给后续训练算法和数据设计
```

不建议现在照搬的内容：

```text
1. 不要马上复刻完整 ROLL 训练框架。
2. 不要马上复刻完整 ROCK 分布式环境管理系统。
3. 不要把 iFlow CLI 作为 RepoHarness 的长期运行时依赖。
4. 不要现在就做 RollArt 级硬件亲和调度、serverless reward 和跨集群权重同步。
5. 不要因为 ROLL 有完整生态，就削弱 RepoHarness 自己对白盒 native harness、用户模拟、权限和 artifact safety 的控制。
```

## 2. 本轮已加入的资料

### 2.1 PDF 报告

本轮将以下报告加入 `external_paper_references/pdfs/`，并更新了 `manifest.json`：

| 编号 | 文件 | 来源 | 主要价值 |
| --- | --- | --- | --- |
| R10 | `pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf` | `https://arxiv.org/pdf/2512.24873` | ALE 总报告，说明 ROLL、ROCK、iFlow CLI、ROME、IPA 和 Terminal-Bench-Pro 如何组成完整 agentic learning ecosystem。 |
| R11 | `pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf` | `https://arxiv.org/pdf/2512.22560` | RollArt 系统报告，说明轨迹级异步、硬件亲和、serverless reward 和 bounded-staleness 权重同步。 |
| R12 | `pdfs/R12_roll_framework_2506.06122.pdf` | `https://arxiv.org/pdf/2506.06122` | ROLL 框架技术报告，说明 Ray 多角色架构、Parallel Worker、Rollout Scheduler、Environment Worker、Reward Worker 和 AutoDeviceMapping。 |

另外，`README.md` 已经索引但 `manifest.json` 之前缺失的 R9 Composer 2 也已补进 manifest。

### 2.2 参考代码库

本轮将以下仓库浅克隆到 `reference/`：

| 仓库 | 本地路径 | 当前本地 commit | 状态 |
| --- | --- | --- | --- |
| `https://github.com/alibaba/ROLL` | `reference/ROLL/` | `c7e3793 2026-06-26 fix: add deepspeed dependency in ci` | 新增参考，工作树干净。 |
| `https://github.com/alibaba/ROCK` | `reference/ROCK/` | `8c5e3c3 2026-06-24 feat: support configurable runtime env (#1149)` | 新增参考，工作树干净。 |
| `https://github.com/iflow-ai/iflow-cli` | `reference/iflow-cli/` | `4642808 2026-03-20 Add shutdown notice: iFlow CLI shutting down on April 17, 2026 (UTC+8)` | 新增参考。注意该项目已经声明停止服务。 |
| `https://github.com/alibaba/terminal-bench-pro` | `reference/terminal-bench-pro/` | `874af40 2026-04-02 Update leaderboard (#9)` | 新增 benchmark / task package 参考。 |

### 2.3 网页和模型卡

本轮还检查了以下外部入口：

| 资料 | 位置 | 结论 |
| --- | --- | --- |
| ROLL 团队页 | `https://wwxfromtju.github.io/roll_team.html` | 能直接读到 ROLL 团队对 ROLL、ROLL Flash、RollArt、ALE、ROME 和博客的总结，是后续跟踪入口。 |
| Notion 博客 | `https://www.notion.so/The-Bitter-Lesson-Behind-Building-Agentic-RL-in-Terminal-Environments-2eaddd45837f80c9ad2ed6a15ef3c1a1?pvs=21` | 该 URL 运行时会跳转到 `faithful-almanac-add.notion.site`。本轮没有把 Notion 正文镜像成本地稳定 markdown，因此文档分析主要以 R10/R11/R12、团队页和模型卡为准。 |
| iFlow-ROME 模型卡 | `https://huggingface.co/FutureLivingLab/iFlow-ROME` | 模型卡明确把 ALE 归纳为 ROLL、ROCK、iFlow CLI，并记录 ROME-30B-A3B 的 Terminal-Bench 2.0 和 SWE-bench Verified 表现。 |

## 3. 对既有参考仓库 freshness 的非破坏性检查

> **勘误（2026-07）**：本节表格中 `reference/verifiers/` 一行的原结论不成立。后续核实发现该工作树的 `git log -1` 实际就是远端最新 `97be43bf`（工作树干净，仅 AGENTS.md / CLAUDE.md 为本地导览修改），并非"落后 236 个 commit / 停在 a01ce52f"。verifiers v1 当前源码已包含 Trace 消息图、interception、EnvServer 等新版结构（旧版 `runtime.py` / `sandbox.py` / `user.py` 等文件已删除），其根部 AGENTS.md 描述的是旧版结构、已过时，阅读应以 `reference/verifiers/CLAUDE.md` 和 `verifiers/v1/ARCHITECTURE.md` 为准。`reference/slime/` 一行已在本轮刷新到 `origin/main` 并更新导览。其余各行的 freshness 结论未逐一复核，实现级设计前仍建议单独 audit。详见 `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`。

用户提到 Prime 系列可能后续需要检查是否更新。本轮对既有参考仓库只做了 `git fetch --all --prune`，没有 `pull`、没有切分支、没有覆盖本地导览文件。

检查结果：

| 仓库 | 当前状态 | 当前本地 commit | 远端最新 commit | 处理建议 |
| --- | --- | --- | --- | --- |
| `reference/verifiers/` | `main` 落后 `origin/main` 236 个 commit；`AGENTS.md`、`CLAUDE.md` 有本地修改。 | `a01ce52f 2026-06-07 feat(v1/sandbox): canonical /vf/model bridge...` | `97be43bf 2026-06-28 fix: make uv-script prep hermetic...` | 需要单独 freshness audit。不能直接 pull，否则会和本地导览文件冲突。 |
| `reference/research-environments/` | `main` 落后 67 个 commit；`AGENTS.md`、`CLAUDE.md` 有本地修改。 | `4c08260f0 2026-06-04 Restrict opencode verifiers version` | `bae0ffe5a 2026-06-28 fix: parse scaleswe score...` | 需要单独 freshness audit。 |
| `reference/renderers/` | `main` 落后 12 个 commit；`AGENTS.md`、`CLAUDE.md` 是未跟踪文件。 | `596c15f 2026-06-04 feat(nemotron3)...` | `a5efbb9 2026-06-26 feat(thinking)...` | 需要单独 freshness audit，尤其是 thinking retention / bridge 行为可能已变。 |
| `reference/ProRL-Agent-Server/` | `stable` 落后 2 个 commit；`AGENTS.md`、`CLAUDE.md` 是未跟踪文件。 | `8bc67cc3 2026-05-31 vLLM support...` | `f0e8343a 2026-06-25 Harbor evaluator and TMAX example` | 需要后续检查 stable 最新代码对 Harbor / evaluator 的影响。 |
| `reference/slime/` | **已于 2026-07 刷新到 `origin/main`**；`AGENT.md`、`AGENTS.md`、`CLAUDE.md` 是本地未跟踪导览文件。 | `e848052a 2026-07-05 [docker] Update dependencies (#2178)` | `e848052a 2026-07-05 [docker] Update dependencies (#2178)` | 本轮已完成更新。后续比较 verl / slime / ROLL 时，应以 `reference/slime/AGENTS.md` 的新版导览为入口。 |
| `reference/verl/` | `main` 本地 ahead 2、behind 245。 | `ba8cfb6d 2026-05-16 docs: consolidate local verl agent guide` | `3d66a3d7 2026-06-29 [trainer, rollout] feat: log rollout moe load-balance metrics` | verl 本地参考明显落后。后续实现前应单独刷新，不应基于当前参考直接下结论。 |

这个检查意味着：ROLL 生态本轮是比较新的参考；既有 Prime、Polar、slime、verl 参考仍然有价值，但后续做实现级设计之前需要单独更新或重拉一个干净副本。

## 4. ROLL 生态的职责拆分

### 4.1 ROLL：训练框架和 agentic pipeline

ROLL 是大规模强化学习训练框架，不是 SWE 环境 ownership 框架。它的职责更接近 `verl`、`slime` 或 OpenRLHF 这类训练后端：

```text
ActorTrain / ActorInfer / Critic / Reference / Reward
  -> Ray Cluster
  -> RolloutScheduler
  -> Environment Worker
  -> Reward Worker
  -> vLLM / SGLang / Megatron / DeepSpeed / FSDP2
```

关键代码位置：

```text
reference/ROLL/roll/pipeline/agentic/agentic_pipeline.py
reference/ROLL/roll/pipeline/agentic/agentic_rollout_pipeline.py
reference/ROLL/roll/distributed/scheduler/rollout_scheduler.py
reference/ROLL/roll/distributed/scheduler/reward_scheduler.py
reference/ROLL/roll/distributed/scheduler/rollout_mock_mixin.py
reference/ROLL/roll/configs/worker_config.py
reference/ROLL/roll/pipeline/agentic/env_manager/agent_native_env_manager.py
reference/ROLL/roll/pipeline/agentic/llm_proxy/policy_proxy.py
```

最值得 RepoHarness 学习的点：

1. `AgenticPipeline` 把训练集群、推理集群、可选 reference、可选 critic、可选 reward cluster 和 rollout scheduler 组合在同一个训练 pipeline 中。它说明训练框架需要拥有权重同步、推理服务生命周期、reward cluster 生命周期和设备映射。

2. `RolloutScheduler` 里有 `GroupQueue`、`GroupQueueManager`、`EnvActivityMonitor`、`group_size_redundancy`、`async_generation_ratio` 和过期 group 丢弃逻辑。它说明长程 agentic rollout 不能只按 batch 同步等待，必须把慢环境、坏环境、过期样本和 group 级过滤当成运行时问题处理。

3. `AgentNativeStepEnvManager` 会在每一步保存 `prompt_ids`、`response_ids`、`infer_logprobs`、`response_mask`、`prompt_mask`、`scores`、`traj_group_id`、`traj_id`、`state_hash`、`step_scores`、`episode_scores` 和 `trajectory_data`。这和 RepoHarness 当前强调的 token provenance、loss mask 和 reward attribution 是同一方向。

4. `RolloutMockMixin` 提供 dump/mock 机制，用于把昂贵、随机的 rollout 保存成可重放的 `DataProto`，从而验证 dynamic batching、sequence packing、并行策略等数值优化。这对 RepoHarness 后续做 adapter / training view 回归测试很有启发：应该能把某次轨迹投影固定下来，反复验证后端转换是否数值一致。

不能照搬的点：

1. ROLL 是训练框架。RepoHarness 不应该把 ROLL 的 Actor / Critic / Reward / Megatron / FSDP2 角色搬进核心环境服务。

2. ROLL 的 `DataProto`、Ray cluster 和 worker config 是它自己的训练数据面。RepoHarness 应该输出中立的 `TrajectoryArtifact` 或 `TrainingView`，再由 adapter 投影到 ROLL / verl / slime 各自的数据结构。

3. ROLL 的 reward normalization、group filtering、动态采样和 staleness 处理默认属于训练后端或训练驱动层，不应该被 RepoHarness core 抢占。

### 4.2 ROCK：环境服务、沙箱生命周期和 sandbox-side model proxy

ROCK 是本轮对 RepoHarness 最有增量价值的参考仓库。它把 agentic RL 环境执行从“一个本地 Docker backend”提升为服务化系统：

```text
ROCK SDK
ROCK CLI
ROCK Admin
ROCK Worker
ROCK Rocklet
ROCK EnvHub
Sandbox SDK
GEM API
ModelService
agent install/run
```

关键代码位置：

```text
reference/ROCK/README.md
reference/ROCK/rock/sdk/sandbox/client.py
reference/ROCK/rock/sdk/sandbox/agent/rock_agent.py
reference/ROCK/rock/sdk/sandbox/model_service/base.py
reference/ROCK/rock/sdk/model/server/main.py
reference/ROCK/rock/sdk/model/server/api/proxy.py
reference/ROCK/rock/sdk/model/server/traj.py
reference/ROCK/examples/install-agents/README.md
reference/ROCK/examples/install-agents/claude_code/rock_agent_config.yaml
reference/ROCK/examples/install-agents/iflow_cli/rock_agent_config.yaml
```

最值得 RepoHarness 学习的点：

1. `Sandbox` SDK 统一了 `start`、`attach`、`get_status`、`execute`、`stop`、`delete`、`create_session`、`arun`、文件系统、网络、部署和 runtime env。这比当前“工具执行器 + Docker backend”的视角更接近长期 rollout service 所需的环境生命周期。

2. `RockAgent` 用 `rock_agent_config.yaml` 安装和运行不同 CLI agent。示例中包括 Claude Code、Cursor CLI、iFlow CLI、OpenClaw、qwen-code 和 SWE-agent。这证明黑盒 harness 支持不应该硬编码某一个 agent，而应该有可配置的安装命令、运行命令、工作目录、环境变量、timeout 和模型服务配置。

3. `ModelService` 可以在 sandbox 内安装和启动模型服务，并监控 agent 进程。`rock/sdk/model/server/api/proxy.py` 提供 OpenAI-compatible `chat/completions` proxy，支持 forward、record 和 replay。`traj.py` 将每次请求写成 JSONL，记录 request、response、status、response_time、model、stream 和 error。

4. ROCK 的 proxy forward path 明确保留上游响应的 provider-specific 字段，不强迫转成某个 OpenAI SDK 内部对象。这对 RepoHarness 很重要：黑盒 harness capture 既要尽量保留真实响应，也要在训练资格层明确哪些轨迹缺 token ids 或 logprobs，不能伪装成 policy-loss-ready。

5. ROCK 的 read/write separation demo 把 Admin 写操作和 Proxy runtime 操作拆开。这对未来 RepoHarness 的 Rollout Service / Runtime Worker / Sandbox Proxy 也有启发：生命周期控制、运行时命令和模型请求不一定要走同一个服务边界。

不能照搬的点：

1. ROCK 是完整 sandbox service。RepoHarness 近期不需要实现 Admin / Worker / Rocklet / EnvHub 全套分布式系统。

2. ROCK 的 proxy record/replay 目前记录的是 request / response JSONL，不等价于 formal online RL 所需的 prompt token ids、sampled response token ids、逐 token logprobs、loss mask 和 reward attribution。RepoHarness 仍然需要自己的 `CompletionRecord` / `TrainingEligibilityGate`。

3. ROCK 的 agent 安装示例大量依赖外部 CLI、API key 和网络。用于训练时必须再加 RepoHarness 自己的 artifact visibility、secret redaction、network allowlist、hidden verifier isolation 和 anti-cheat 规则。

### 4.3 iFlow CLI：真实 agent runtime 的上下文工程参考

iFlow CLI 在 R10 中承担 agent framework 角色：它负责真实 CLI agent 的上下文工程、工具使用和工作流。对 RepoHarness 的价值是“真实产品态 agent runtime 参考”，不是长期依赖。

关键代码和文档位置：

```text
reference/iflow-cli/README.md
reference/iflow-cli/README_CN.md
reference/iflow-cli/docs_cn/glossary.md
reference/iflow-cli/docs_cn/examples/hooks.md
reference/iflow-cli/docs_cn/examples/subagent.md
reference/iflow-cli/docs_cn/features/checkpointing.md
reference/iflow-cli/docs_cn/examples/workflow.md
```

可借鉴点：

1. 四种运行模式：`yolo`、`accepting edits`、`plan mode`、`default mode`。这和 RepoHarness 的权限系统、用户审批和不同训练 profile 可以形成对照。

2. Sub Agent、Task 工具、上下文压缩、hooks、workflow、checkpoint、conversation resume 和 OpenAI-compatible API 配置，都是真实 CLI harness 里会影响训练轨迹的上下文行为。

3. hooks 能在 `PreToolUse`、`PostToolUse`、`SessionStart`、`SessionEnd`、`SubagentStop` 和 `UserPromptSubmit` 等生命周期点插入逻辑。这说明白盒 RepoHarness 的 hook/event log 应该是训练可审计对象，而不是只作为调试日志。

关键限制：

```text
iFlow CLI README 明确声明该项目会在 2026-04-17 停止服务。
```

因此它只能作为 agent runtime 模式参考，不应该成为 RepoHarness 的长期依赖。

### 4.4 Terminal-Bench-Pro：终端环境任务包和评测质量参考

Terminal-Bench-Pro 对 RepoHarness 的价值不在训练框架，而在环境生产、任务 metadata 和 benchmark 组织。

关键路径：

```text
reference/terminal-bench-pro/README.md
reference/terminal-bench-pro/*/instruction.md
reference/terminal-bench-pro/*/task.toml
reference/terminal-bench-pro/*/tests/
reference/terminal-bench-pro/*/environment/
reference/terminal-bench-pro/*/solution/
```

可借鉴点：

1. 400 个任务，200 public + 200 private，覆盖 data processing、games、debugging、system admin、scientific computing、software engineering、machine learning 和 security 八类终端任务。这对 RepoHarness 未来从 SWE-only 扩展到 terminal agentic tasks 有参考价值。

2. 每个任务有 `instruction.md`、`task.toml`、`environment/`、`tests/` 和 `solution/`。`task.toml` 里记录 author、difficulty、category、tags、estimated duration、verifier timeout、agent timeout、环境 CPU / memory / storage / GPU。RepoHarness 的 `EnvironmentPackage` / `TaskPack` 应该保留类似 metadata。

3. README 明确强调专家设计、真实场景或 GitHub issue 来源、高测试覆盖、难度和领域均衡、Harbor / Terminal-Bench 2.0 格式兼容。这些都适合进入 RepoHarness 的环境生产与质量流水线文档，而不是高层主架构正文。

不能照搬的点：

1. Terminal-Bench-Pro 主要是 benchmark 数据格式，不负责 RepoHarness 的用户模拟、权限策略、token provenance 或训练后端适配。

2. 它的私有集评测服务不等于 RepoHarness 自己的数据冻结和训练数据安全机制。RepoHarness 仍然要建立自己的 hidden verifier、clean grading checkout、artifact public projection 和 anti-cheat 规则。

## 5. ROLL 生态与现有参考的关系

### 5.1 与 Prime / research-environments 的关系

Prime 解决的是 ownership 和组合抽象：

```text
TaskSet / Task / Harness / Env / State / User / Sandbox / Artifact / Rubric
```

ROCK 解决的是环境服务运行时：

```text
Admin / Worker / Rocklet / EnvHub / Sandbox SDK / ModelService / agent install-run
```

两者互补，不互相替代。RepoHarness 仍然应该用 Prime-style ownership 定义“环境由什么组成、谁拥有任务事实、谁拥有评分规则、谁拥有 harness 执行协议”。ROCK-style 参考则告诉我们这些对象最终如何变成一个可服务化、可调度、可安装 agent、可代理模型调用的运行环境。

### 5.2 与 Polar / ProRL-Agent-Server 的关系

Polar 的关键思想是从模型 API 边界捕获黑盒 harness 的训练轨迹。ROCK 的 Agent Native Mode 和 ModelService 则提供了另一个落点：

```text
真实 CLI harness 在 sandbox 中运行
  -> CLI 自己管理上下文和工具协议
  -> sandbox 内 ModelProxyService 拦截模型请求
  -> 请求转发到训练推理服务或部署 API
  -> 轨迹 record/replay
```

因此，ROCK 不替代 Polar，而是让 Polar-style model proxy 更接近“部署同款 harness”的执行环境。RepoHarness 可以把二者合并成长期捕获模式：

```text
ProxyCaptureMode:
  host-side OpenAI-compatible proxy
  sandbox-side ModelProxyService
  provider-native token/logprob capture
  capture-only audit mode
  replay/debug mode
```

硬边界仍然不变：只有拿到真实 prompt token ids、sampled response token ids、逐 token logprobs，并通过 loss mask、reward scope、security 和 staleness 校验的轨迹，才能进入 formal online policy loss。

### 5.3 与 verl / slime 的关系

verl 和 slime 是 RepoHarness 近期最现实的训练后端。ROLL 是第三个重要参考，但不需要立刻接入。

对当前项目更合理的顺序是：

```text
近期：
  继续优先完善 verl trainer-native 接入和 slime 对照适配。

中期：
  把 TrainingBackendAdapter 做成训练后端中立边界。

长期：
  如果要支持 ROLL，再新增 ROLLAdapter，把 TrajectoryArtifact / TrainingView 投影到 ROLL DataProto 或 ROLL agentic rollout 输入。
```

ROLL 的重点启发不是“换掉 verl 或 slime”，而是提醒我们：

```text
训练框架拥有权重同步、推理服务、reward cluster、设备映射、数据 buffer、动态采样和 group 级训练消费。
RepoHarness 拥有环境、工具、用户模拟、权限、轨迹、artifact safety 和训练资格。
```

这一点和当前主架构文档的 `Training Runtime Coordination Plane` 是一致的。

### 5.4 与 renderers 的关系

ROLL 的 `AgentNativeStepEnvManager` 会显式保存 `prompt_ids`、`response_ids`、`infer_logprobs`、`response_mask` 和 `prompt_mask`。这支持了 RepoHarness 当前的判断：

```text
训练样本必须以采样时真实 token 事实为中心，
不能只保存 transcript 再训练前重新 tokenize。
```

不过 ROLL 代码里 TODO 也提示了 prefix merging 和更细粒度消息处理仍然复杂。RepoHarness 不应该因此放松 renderers-style token fidelity；相反，ROLL 提供了另一个现实证据：成熟训练框架也必须在 env manager / rollout layer 保存 token-level 事实。

## 6. 最需要补充到 RepoHarness 设计视野的内容

### P0. ROCK-style Runtime / Execution Service

当前高层文档已经有 `Runtime / Execution Plane`、`SandboxInstance`、`RuntimePool`、`HarnessRunner`、`ScoringRuntimePrewarmer` 等对象。ROLL 生态建议进一步把这部分理解成未来可能服务化的环境执行系统：

```text
SandboxAdmin / RuntimeAdmin
SandboxWorker
SandboxProxy / RuntimeProxy
EnvironmentRegistry / EnvHub-like registry
Sandbox SDK
AgentInstallSpec
ModelServiceSpec
NetworkPolicy / EgressPolicy
RuntimeHealthReport
```

不需要现在实现全套，但高层设计后续应该承认：如果 RepoHarness 要支持黑盒 harness、大规模并发 rollout 和 service-driven topology，单机 Docker adapter 会成为瓶颈。

### P0. Sandbox-side ModelProxyService

当前文档已经有 `OpenAICompatibleModelProxy` 和 Polar-style capture。ROLL / ROCK 说明还应该考虑 sandbox-side proxy：

```text
agent process inside sandbox
  -> local model endpoint inside sandbox
  -> ModelProxyService record/replay/forward
  -> training inference backend or deployment provider
```

这个模式能减少训练 harness 和部署 harness 的上下文差异，因为真实 CLI agent 仍然自己组织上下文、工具和中间 prompt。RepoHarness 后续可以把它作为 `ProxyCaptureExtension` 的一个 capture placement，而不是新建第二套 trajectory 系统。

### P0. Trajectory-level async coordination

RollArt 对 `Training Runtime Coordination Plane` 的最大补充是：异步粒度应该至少能表达轨迹级，而不是只有 batch 级。

建议后续在数据契约或 adapter 设计中注意以下概念：

```text
env_manager_id
llm_proxy_request_id
sample_buffer_entry_id
trajectory_start_weight_version
trajectory_completion_weight_version
trajectory_staleness
abort_or_evict_reason
reward_submission_time
reward_completion_time
backend_consume_time
```

这些字段不表示 RepoHarness 自己要实现 RollArt。它们表示当 RepoHarness 对接 verl、slime、ROLL 或未来训练后端时，需要能记录训练后端如何处理这条轨迹。

### P1. Reward service and serverless evaluator reference

当前 RepoHarness 文档已经强调 reward 不应盲目广播，也不应把 reward normalization 放在核心服务。RollArt 和 ROLL 的 reward cluster / reward scheduler 进一步说明：

```text
Reward / Evaluator 可能是独立服务，
可能用独立 GPU，
也可能是 serverless / 弹性 CPU / 外部 judge。
```

RepoHarness 后续应该把 `RubricRunner` / `Evaluator` 设计成可本地、可服务化、可异步完成的对象，并在 artifact 中记录 reward 计算状态、提交时间、完成时间、失败类别和 retryable。

### P1. Terminal-Bench-Pro style environment production

Terminal-Bench-Pro 建议 RepoHarness 的环境包 metadata 至少要支持：

```text
category
difficulty
tags
estimated_duration
expert_time_estimate
junior_time_estimate
agent_timeout
verifier_timeout
environment_resources
public_or_private_split
test_count_or_test_coverage_summary
```

这部分更适合放进 `environment_production_and_quality_pipeline_design.md`，不应该把具体生产流程塞进主架构文档。

### P2. IPA semantic interaction chunks

R10 的 IPA 强调 semantic interaction chunk 级 credit assignment。它对 RepoHarness 很有启发，但更偏训练算法和数据设计，不应现在进入核心环境契约。

可以在后续训练设计中考虑：

```text
interaction_chunk_id
chunk_boundary_reason
chunk_level_reward
chunk_level_advantage
chunk_replay_or_resample_policy
```

现在只需要保留扩展空间，不要把 IPA 字段提前冻结进主 artifact schema。

## 7. 哪些已有参考已经足够

### 7.1 环境 ownership

Prime / verifiers / research-environments 仍然是最适合 RepoHarness 学习 ownership 的参考。ROLL / ROCK 不应该改变 `TaskSet owns task facts`、`Harness owns execution protocol`、`Rubric owns scoring`、`State owns runtime outputs` 这些边界。

### 7.2 token fidelity

renderers 仍然是最直接的 token-faithful 参考。ROLL 的 token 保存方式强化了这条结论，但不能替代 renderers 对 `bridge_to_next_turn`、thinking retention、tool call rendering 和 retokenization drift 的专门处理。

### 7.3 近期 trainer-native 接入

对于近期接入，verl 和 slime 仍然比 ROLL 更直接：

```text
verl:
  当前项目已有 fully async / MessageQueue / AgentLoop 接入背景。

slime:
  已经和 ProRL-Agent-Server / GLM 系列参考关系更近，适合做第二训练后端对照。

ROLL:
  更适合作为第三参考后端和系统设计校准源，暂时不需要实现 ROLLAdapter。
```

### 7.4 极简 baseline

mini-swe-agent 仍然适合作为“最小 bash-only baseline”。ROLL 生态不会替代它，因为 ROLL / ROCK 是完整系统，而 mini-swe-agent 的价值恰恰是简单、边界清楚、容易对照。

## 8. 对当前高层设计文档的建议

本轮不建议直接大改 `repo_harness_repositioning_after_polar.md`。原因是主文档已经覆盖以下关键边界：

```text
1. Prime-style ownership。
2. Polar-style model proxy 和 trajectory builder。
3. token provenance、logprob alignment、loss mask 和 reward attribution。
4. trainer_native 与 service_driven 双拓扑。
5. Training Runtime Coordination Plane。
6. hidden verifier、clean grading、artifact visibility 和 anti-cheat。
7. verl / slime ownership 边界。
```

如果下一轮要把 ROLL 生态吸收进主文档，建议只做四处轻量补充：

1. 在外部参考章节新增 `从 ROLL / ROCK / RollArt 借鉴` 小节，说明它是 environment service、agent native mode 和 trajectory-level async 的参考，不是替代 Prime / Polar / verl / slime。

2. 在 `Runtime / Execution Plane` 增加一段 ROCK-style sandbox service 说明，承认长期可能需要 `SandboxAdmin`、`SandboxWorker`、`SandboxProxy`、`AgentInstallSpec`、`ModelServiceSpec` 和 `EnvironmentRegistry`。

3. 在 `Model Boundary Capture Plane` 增加 `sandbox-side ModelProxyService` 作为 capture placement，强调它和 host-side OpenAI-compatible proxy 共享同一个 `CompletionRecord` / `TrainingEligibilityGate`，不能另立一套轨迹事实。

4. 在 `Training Runtime Coordination Plane` 增加 RollArt 术语映射：`EnvManager`、`LLMProxy`、`SampleBuffer`、`serverless reward`、`bounded staleness`、`abort / evict stale trajectories`。这些作为 adapter 握手和运行时事实，不表示 RepoHarness 要自己实现训练框架。

## 9. 关键本地阅读路径

后续线程如果继续读 ROLL 生态，建议从以下文件开始：

```text
docs/harness_improve/external_paper_references/pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf
docs/harness_improve/external_paper_references/pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf
docs/harness_improve/external_paper_references/pdfs/R12_roll_framework_2506.06122.pdf

reference/ROLL/README.md
reference/ROLL/CLAUDE.md
reference/ROLL/docs_roll/docs/Overview.mdx
reference/ROLL/docs_roll/docs/Development/Developer Guide/customer_env.md
reference/ROLL/docs_roll/docs/Development/Developer Guide/llm_as_judge_optimization.md
reference/ROLL/docs_roll/docs/Development/Developer Guide/rollout_mock_usage.md
reference/ROLL/roll/pipeline/agentic/agentic_pipeline.py
reference/ROLL/roll/pipeline/agentic/agentic_rollout_pipeline.py
reference/ROLL/roll/pipeline/agentic/env_manager/agent_native_env_manager.py
reference/ROLL/roll/pipeline/agentic/llm_proxy/policy_proxy.py
reference/ROLL/roll/distributed/scheduler/rollout_scheduler.py
reference/ROLL/roll/distributed/scheduler/reward_scheduler.py
reference/ROLL/roll/distributed/scheduler/rollout_mock_mixin.py
reference/ROLL/roll/configs/worker_config.py

reference/ROCK/README.md
reference/ROCK/CLAUDE.md
reference/ROCK/rock/sdk/sandbox/client.py
reference/ROCK/rock/sdk/sandbox/agent/rock_agent.py
reference/ROCK/rock/sdk/sandbox/model_service/base.py
reference/ROCK/rock/sdk/model/server/main.py
reference/ROCK/rock/sdk/model/server/api/proxy.py
reference/ROCK/rock/sdk/model/server/traj.py
reference/ROCK/examples/install-agents/README.md
reference/ROCK/examples/install-agents/claude_code/rock_agent_config.yaml
reference/ROCK/examples/install-agents/iflow_cli/rock_agent_config.yaml

reference/iflow-cli/README.md
reference/iflow-cli/README_CN.md
reference/iflow-cli/docs_cn/glossary.md
reference/iflow-cli/docs_cn/examples/hooks.md
reference/iflow-cli/docs_cn/examples/subagent.md
reference/iflow-cli/docs_cn/features/checkpointing.md

reference/terminal-bench-pro/README.md
reference/terminal-bench-pro/fix-django-command-injection/instruction.md
reference/terminal-bench-pro/fix-django-command-injection/task.toml
reference/terminal-bench-pro/fix-django-command-injection/tests/
```

## 10. 后续建议

建议后续分三步处理：

1. 先把本轮 ROLL 生态 intake 作为资料池状态固定下来，不急着把主架构文档改厚。

2. 单独开一个 reference freshness audit，更新或重拉 Prime、Polar、renderers、verl 等仍未复核的干净副本，避免后续基于明显落后的参考代码做实现设计。`reference/slime/` 已在本轮刷新到 `origin/main`，不再属于这条待刷新清单。

3. 在下一轮主架构冻结时，只把 ROCK-style environment service、sandbox-side ModelProxyService 和 RollArt-style trajectory-level async coordination 三个 P0 点合并进主文档，其余 ROLL 训练框架、serverless reward、IPA 和硬件亲和调度继续留在子文档或训练设计文档中。
