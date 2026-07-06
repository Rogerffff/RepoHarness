我读完这两份报告后，最重要的结论是：

**你的 RepoHarness 项目现在往 “Prime-style composable environment + Polar-style rollout service + token-faithful trajectory + verl adapter” 方向改，是对的；但从 Microsoft 和 NVIDIA 的报告看，还需要更强调三件事：环境构建流水线、rollout group / problem worker 抽象、反作弊与 clean grading。**

也就是说，你的项目不应该只证明：

```text
我能让 agent 在 repo 里跑一圈，然后把 reward 接给 verl。
```

而应该证明：

```text
我能构造 SWE RL 环境包；
我能用同一套 harness 跑多种任务和多种 agent；
我能安全地产生 token-faithful rollout artifact；
我能用 verifier / anti-cheat / clean replay 决定哪些轨迹有资格进入 RL。
```

---

# 1. 两份报告里的 SWE agentic RL 共同模式

Microsoft MAI-Thinking-1 的 agentic climb 明确把 agentic RL 定义成：模型必须和外部环境交互，而不是单次文本回答；模型要分解用户请求、选择工具或代码动作、观察结果，并在多步中调整计划。奖励信号包括软件环境里的测试通过、数据库达到目标状态等 verifiable reward，也包括任务理解、helpfulness、trajectory quality 这类 AI-feedback reward。([Microsoft AI][1])

NVIDIA Nemotron 3 Ultra 也采用了 agent-focused post-training pipeline：先 SFT，再统一 RLVR，之后通过多教师 on-policy distillation 把不同 specialist teacher 的能力合并回来。它们的统一 RLVR 覆盖 terminal usage、software engineering、search、general tool-calling、math、code、safety、chat、long-context 等环境，并且明确说 harness-based environments 使用多种 harness implementation 和 interaction format，以提升鲁棒性、降低对某个 harness design 的过拟合。

所以这两篇报告都支持你现在的判断：

```text
单一 SWE harness 不够；
真正要做的是 environment / harness / verifier / rollout / trainer interface 的基础设施。
```

但它们也都显示：**强模型公司做 SWE agentic RL 时，真正重的部分不是 agent loop，而是环境构建、rollout 调度、验证、反作弊、异步训练和推理服务。**

---

# 2. Microsoft MAI-Thinking-1：你最该借鉴的基础设施点

## 2.1 Agent loop 很简单，但环境很重

Microsoft 的 SWE RL 环境并没有用一个特别复杂的 agent loop。它们的 SWE 动作主要是读写文件、运行 shell 命令、查看 repo 状态；报告中还明确说 SWE agentic training data 只使用 bash 和 string-replace 两个工具，没有专门训练 Terminal-Bench-like terminal interaction。([Microsoft AI][1])

这对你的项目很重要：**不要把亮点放在继续堆更多工具。** 你当前 16G 之前一直在增强 tool surface，但从这篇报告看，SWE RL 的核心工具面可以很简单：

```text
bash(command: string)
str_replace_editor / apply_patch / string replace editing
```

真正值得做的是：

```text
环境是否可执行；
测试是否可信；
轨迹是否可训练；
reward 是否防作弊；
rollout 是否可异步扩展。
```

---

## 2.2 每个 SWE 问题被打包成 self-contained container image

Microsoft 的 SWE RL problem 是一个自包含 container image，包含指定 commit 的 repo、预安装依赖、problem statement 和 grading unit tests。因为依赖已经在 image 中捕获，rollout 开始时无需 setup，环境可复现、可立即执行。模型在容器内通过工具读写文件、运行 shell、导航 repo，完成后 grader 在同一容器内执行测试并对比 expected outcomes，产出 verifiable reward。([Microsoft AI][1])

这对 RepoHarness 的启发是：你的 `TaskSet` 不应该只是一条 JSON task，它应该逐步升级成：

```text
SWEEnvPackage:
  repo_snapshot
  base_commit
  problem_statement
  public_tool_schema
  hidden_verifier_bundle
  dependency_image_or_setup_cache
  expected_pre_fix_outcome
  expected_post_fix_outcome
  sandbox_spec
  visibility_policy
```

对简历项目来说，不一定要真的构建海量 Docker image，但你至少应该有：

```text
env_id
image_or_fixture_ref
source_digest
setup_digest
verifier_digest
tool_schema_digest
visibility_policy_digest
```

这样面试官会看到你理解“环境包”才是训练单位。

---

## 2.3 环境构建流水线比 rollout 本身更关键

Microsoft 从 public GitHub PR/issue 构建 SWE RL 环境：先从 102 million public PR 过滤，要求 PR merged、修改少于 15 个文件、有 code 和 test changes、有关联 issue；然后用 LLM agent 读 repo state、生成 Docker files、构建可执行 container；再提取 reference grading signal：base commit + test diff 应失败，test+code diff 应通过，从中得到 F2P 和 P2P 信号。最后在和 RL 训练相同的 SEE infrastructure 中反复验证：empty patch 必须失败，golden patch 必须成功，并过滤非确定性测试。([Microsoft AI][1])

这说明你的项目后续要补一个层：

```text
EnvironmentBuilder / TaskIngestionPipeline
```

不要只写：

```text
load_task(path) -> run_episode
```

而要有：

```text
PR / fixture / synthetic task
  -> environment build
  -> pre-fix / post-fix signal extraction
  -> deterministic verifier validation
  -> task quality scoring
  -> EnvPackage freeze
```

第一版可以很小，例如 20 个 fixture repos，但结构上要对齐。

---

## 2.4 需要 task quality filtering 和 problem statement rewriting

Microsoft 发现，环境能跑、测试能判定还不够；很多 problem statement 太短、太模糊，或者“fix things” 这类描述只把真实需求藏在 hidden tests 里。它们用 agent 在同一环境中检查 problem statement、repo 和 tests，对 specification clarity、test quality、leakage risk、feasibility 打分，并对低质量环境重写 problem statement，使它更对齐测试要求，同时避免泄漏或过度指定。([Microsoft AI][1])

这对你的 RepoHarness 非常重要。你之前关注 user simulator / permission system，但在 SWE RL 中还有一个更基础的问题：

```text
任务是否公平？
模型是否可以从用户请求和 repo 状态中合理推出该做什么？
hidden tests 是否在考未说明的需求？
```

建议加一个 `TaskQualityEvaluator`：

```text
clarity_score
test_alignment_score
leakage_risk_score
feasibility_score
underspecification_flags
overspecification_flags
rewrite_suggestion
```

这可以先不用 LLM 自动重写，但至少要产出 audit report。

---

## 2.5 反 reward hacking 是 SWE RL 的硬需求

Microsoft 明确列了 SWE reward hacking 的三类：搜索互联网找到 public PR/gold solution；搜索本地 git history 找 hidden solution commit；篡改 tests、monkey-patch testing framework 或修改 equivalence behavior。对应防线包括 sandbox 网络访问控制、清理 base commit 之后的 commits/references/branches、reset agent 修改的 test files、隐藏 test changes 只在 grading 时应用，以及用 LLM monitor 和人工 review 持续强化 anti-tampering heuristics。([Microsoft AI][1])

这应该直接进入你的架构硬门槛：

```text
AntiCheatPlane:
  network_policy
  git_history_sanitizer
  remote_git_blocker
  hidden_test_visibility_guard
  test_file_reset
  monkeypatch_detector
  forbidden_diff_checker
  clean_grading_replay
  rollout_monitor
```

尤其是 **clean grading replay**：不要直接信任 rollout workspace 的当前状态，而应该导出 cleaned patch，在 clean checkout 中重放并评分。

---

## 2.6 General tool-use synthetic env 支持你做 UserSim / PermissionSpec

Microsoft 的 general tool-use RL 环境是 stateful mocked backend，模拟 API 或 MCP 行为。每个问题由 query、available tools with schema、initial environment state 和 grader 组成；单个环境经常超过 50 个工具。它们还生成 self-contained closed-world environments，包括 seeded databases、tool definitions、verifiable tasks；生成过程分为 environment bootstrapping、task creation、verification/refinement，并生成 environment-specific personas。奖励由 environment-specific graders 和 cross-environment graders 组成，后者检查工具效率、并行调用、避免重复调用、参数类型与参数值正确性。([Microsoft AI][1])

这和你要做的 UserSim / PermissionSpec 非常相关，但我建议先用于 SWE 里的“小型用户交互任务”，不要一开始扩成全行业。

可以把 SWE task 写成：

```text
query:
  “帮我重构 payments 模块，但不要影响退款逻辑。”

tools:
  bash, str_replace_editor, run_tests, request_permission, message_user

initial_state:
  repo snapshot
  user hidden constraints
  permission state

grader:
  hidden tests
  forbidden diff
  permission violation
  user burden
  final patch quality
```

这正好把 Microsoft general tool-use env 的形式迁移回 SWE。

---

## 2.7 Rocket 的 RL infra 给你 Rollout Service 设计参考

Microsoft 的 Rocket 架构分成 controller、problem workers、rollout workers、router/inference servers、learner pool、persistent rollout store、metric store、checkpointing、curriculum 和 weight transfer。Controller 加载 RL tasks，把任务发送给 problem workers；收到 completed rollouts 后，根据 pass/fail、reward、normalized advantages 等 metadata 过滤并组 batch 发给 learner。它们主要用 off-policy RL 做大规模运行，把 on-policy RL 留给小实验和 debug。([Microsoft AI][1])

这对你的 `RepoRolloutService` 很直接。你可以实现一个小型版本：

```text
Controller:
  选择任务、harness、num_samples、policy_version

ProblemWorker:
  管理一个 task 的 rollout group
  负责 early-exit、retry、pass-rate filtering、advantage normalization

RolloutWorker:
  跑单条 agent rollout
  调用 model gateway / model proxy
  执行工具
  产生 trajectory artifact

RubricRunner:
  可在 rollout worker 或 problem worker 侧评分

VerlAdapter:
  只消费 artifact，不 import runtime 内部对象
```

尤其要借鉴 Microsoft 的 `ProblemWorker` 抽象，而不是只做 `run_one_episode`。

---

## 2.8 Early-exit rollouts 和 pass-rate filtering 值得做成你的小型版本

Microsoft 的 problem worker 会先发 16 个 early-exit rollouts，估计 task pass rate；如果 pass rate 在预设区间内，才继续发 128 个 full rollouts，否则丢弃任务。full group 也会做 pass-rate filtering，低方差任务如果几乎全对或全错，就不用于训练；之后再做 GRPO reward normalization、length penalty 等 postprocessing。([Microsoft AI][1])

你可以在 RepoHarness 里做一个简化版：

```yaml
rollout_group_policy:
  early_samples: 4
  full_samples: 16
  early_pass_rate_range: [0.05, 0.80]
  full_pass_rate_range: [0.10, 0.80]
  retry_failed_rollout: true
  length_penalty: optional
  group_advantage: grpo_normalized
```

这比单条 rollout 更像真实 RL infra，也能帮你避免训练无信号任务。

---

## 2.9 Router / inference / staleness 是训练系统第一等问题

Microsoft 明确说 inference 是 RL 系统最重要的组件之一；最大 RL job 里 inference GPU 与 learner GPU 比例可到 4096:768，推理性能和稳定性是 first-order concern。多轮 workload 是 prefill-heavy，所以它们重用 prefix caching，生产 RL 里的 prefix cache hit rate 达到 97–98%。它们也强调 inference 和 learner 的 numerics gap 很关键，小的 per-token logprob 差异会在长 rollout 中累积，并 destabilize off-policy correction；因此用 bf16、MoE routing replay 和 top-p mask replay。([Microsoft AI][1])

你个人项目不需要复制这些集群优化，但需要在 schema 里为它们留位置：

```text
policy_version
behavior_policy_version
learner_policy_version
inference_backend
prompt_ids
response_ids
response_logprobs
sampling_params
top_p
top_p_mask_ref 或 mask_replay_status
staleness_steps
logprob_source
numerics_policy
```

这也再次支持你之前的 `token-faithful TrajectoryArtifact` 设计。

---

# 3. NVIDIA Nemotron 3 Ultra：你最该借鉴的基础设施点

## 3.1 多 harness 轨迹是 SFT / warm-start 的重要来源

NVIDIA 的 terminal-use SFT 数据不是静态代码问答，而是约 370K multi-turn conversations，模型在 live terminal environment 中发命令、观察 execution feedback、迭代完成任务，覆盖 software engineering、data processing、file operations、scientific computing。

更重要的是 software issue resolution：NVIDIA 用 reasoning teacher 和 non-thinking coder teacher 生成 GitHub issue resolution trajectories，issue 来源包括 SWE-Gym、R2E-Gym、SWE-rebench 等；轨迹通过 OpenHands、SWE-agent、Mini-SWE-agent 和 Opencode harness 捕获。它们强调 raw agent rollouts 不能直接用于 SFT，因为会包含不良行为，于是用 per-trajectory heuristic analyzer 过滤提交完整性、disallowed git operations、edit-test loop、lost-in-exploration、tool-call hygiene、debug artifacts、修改后不跑测试等信号。

这对你的项目非常关键：你不应该只做 RL online rollout，还要做：

```text
TrajectoryFilter / SFTCandidateFilter
```

过滤指标可以直接借鉴 NVIDIA：

```text
valid_submission_action
disallowed_git_ops
edit_test_loop_pattern
lost_in_exploration
malformed_tool_call_rate
debug_artifact_in_patch
edited_but_never_tested
test_run_after_edit
```

这会成为你的 warm-start / SFT 数据生产能力。

---

## 3.2 NVIDIA 的 SWE teacher 训练路径支持“三阶段”路线

Nemotron 的 SWE teacher 不是直接端到端 SWE RL。它们先对 Ultra base 做 agentic SFT，再用 PivotRL 在 single-step agentic environments 上训练，最后做 end-to-end SWE-RL：模型多轮和 code repository 交互，发 tool 和 bash commands，产出 patch，hidden tests 给 binary reward，用 GRPO 训练。

这对你的项目有很强启发。你不要一开始就追求 formal online RL，路线应该是：

```text
Stage A: trajectory collection / SFT warm-start
  用 RepoHarness / mini-swe / external harness 生成轨迹，过滤后做 SFT 候选。

Stage B: single-step or short-horizon agentic RL
  例如：读任务 -> 生成 patch / 或少量工具调用 -> verifier reward。

Stage C: end-to-end multi-turn SWE RL
  完整 repo interaction，hidden tests reward，permission/user reward。
```

这样比“直接接 verl 跑大任务”稳很多。

---

## 3.3 Final reward 不足以塑造 trajectory，需要 token/process-level 惩罚

NVIDIA 说 SWE-RL 的 hidden-test binary reward 不总是能帮助 trajectory-level behavior，有时会错误奖励或惩罚轨迹。因此它们 mask 掉 unfinished trajectories 的 loss，并对 malformed reasoning 和 tool calls 的 offending tokens 赋 negative advantage。

这对你的 `Rubric` 和 `TrainingEligibilityPolicy` 很重要。你应该区分：

```text
outcome_reward:
  hidden tests pass/fail

process_penalty:
  malformed tool call
  invalid reasoning format
  repeated denied action
  timeout / max turns
  edited tests
  edit-test thrashing
  no test after edit
  lost in exploration

eligibility:
  unfinished trajectory -> no policy loss or masked loss
  invalid token provenance -> no online RL
  malformed tool call span -> negative advantage or rejected
```

不要把 reward 简化成：

```text
hidden_tests_passed ? 1 : 0
```

---

## 3.4 NVIDIA 对泄漏通道的处理非常具体

NVIDIA 为了防止 agent 从 task container 读 gold patch，做了两件事：第一，在 agent 开始前重写 container 内 repo，使其像 base commit 的 fresh clone，不只是隐藏 future commits，而是物理删除，无法通过低层 git recovery 命令恢复；第二，加 runtime command filter，阻止通过 remote git operations 或 HTTP 工具从 GitHub web/raw-content/Pages 域下载历史。

这和 Microsoft 的反作弊策略高度一致，说明你项目里必须有：

```text
GitSanitizer:
  remove future commits
  remove reflog
  remove remote refs
  scrub branches/tags after base

CommandFilter:
  block git fetch/pull/clone/remote/reflog/fsck
  block curl/wget to github raw/web/pages unless explicitly allowed
  block network by default

LeakageAudit:
  scan model-visible prompt/tool output/final patch for hidden markers
```

这不是安全附加项，而是 SWE RL 的核心基础设施。

---

## 3.5 NVIDIA 的 unified RLVR 强调多环境、多 harness、多格式

NVIDIA 的 RLVR 覆盖 terminal、office/productivity、SWE、search、general tool-calling、math、code、safety、chat、long-context QA 等环境；对 harness-based environments，它们有意使用多种 harness implementation 和 interaction format，来降低对单个 harness design 的过拟合。

这支持你现在的设计：

```text
TaskSet 与 Harness 解耦；
同一个 TaskSet 可跑 RepoHarnessNativeHarness / mini-swe-agent / OpenCode-like harness；
同一个 Harness 可跑 SWEBenchTaskSet / InteractiveRefactorTaskSet / RepoPermissionTaskSet。
```

你的项目如果只支持一个内置 harness，长期价值会下降。最好把 external harness adapter 和 model proxy 作为中期目标保留。

---

## 3.6 MOPD / async distillation 对你的 artifact schema 很有启发

NVIDIA 的 MOPD 是异步的：student rollout generation、teacher scoring、student optimization 组成 pipeline；一条 trajectory 可能由 stale behavior policy 生成，而 learner 优化的是更新的 student snapshot。它们显式计算 behavior policy、proximal policy 和 teacher policy 的 token logprob，并用 token-level masking。

你现在可能不做 MOPD，但 schema 应该支持未来扩展：

```text
behavior_logprobs
proximal_logprobs
teacher_logprobs
teacher_id
teacher_score_ref
token_loss_mask
policy_version_at_generation
policy_version_at_training
staleness
```

这也证明你之前强调 `CompletionRecord / TrainTrace / TrajectoryArtifact` 是正确方向。

---

## 3.7 NVIDIA 的 infra 经验：失败主要来自 generation 和 sandbox/tool calling

Nemotron 报告里，RL 软件失败中 generation engine failures / timeouts 占 56%，sandbox / tool calling 占 36%，两者合计约 92%。它们由此投入大量 instrumentation 和优化。

这对你的项目非常现实。你当前不是大集群，但也应该在 artifact 中记录：

```text
failure_category:
  generation_timeout
  model_backend_error
  sandbox_setup_error
  tool_execution_error
  verifier_timeout
  permission_denied
  invalid_task
  infra_error

retryable:
  true / false

where_failed:
  init / rollout / tool / verifier / artifact_export / trainer_adapter
```

不要只记录 `status=failed`。

---

## 3.8 NVIDIA 的未来工作支持你做 disaggregated sandbox/tool infra 和 checkpoint

NVIDIA 未来工作明确瞄准两大失败类：fail-fast fault isolation、component-level recovery、generation worker 或 sandbox instance 独立重启、sandbox/tool-calling infrastructure disaggregated 独立扩缩、in-flight rollouts/KV cache/conversation state 的 fine-grained checkpointing。

这和你之前 synthetic environment 文章中的观点完全一致：长程 agent RL 的原子对象不是 sample row，而是可恢复的 environment artifact 和 rollout lineage。你项目中应该至少支持：

```text
checkpoint:
  event_log cursor
  workspace diff
  permission state
  user state
  conversation state
  generation records
  verifier partial state
```

第一版可以只 checkpoint filesystem diff + event log + generation records，不必做 KV cache。

---

# 4. 根据两篇报告反推出：你的训练基础设施需要具备哪些能力

下面是我建议你把 RepoHarness 目标架构写成的能力清单。

## 4.1 Environment Package / TaskSet 层

必须支持：

```text
TaskDefinition
  task_id
  repo source
  base commit
  problem statement
  hidden constraints
  public context
  expected files
  timeout / budget
  difficulty label

EnvironmentSpec
  execution image
  dependency cache
  setup digest
  network policy
  sandbox resources
  tool schema version

VerifierSpec
  hidden tests
  public tests
  F2P / P2P expectations
  clean grading command
  anti-tamper rules

VisibilityPolicy
  model_visible
  runtime_private
  grader_only
  public_projection
```

Microsoft 的 self-contained container、F2P/P2P extraction 和 environment verification 证明这些都不是过度设计。([Microsoft AI][1])

---

## 4.2 Environment Builder 层

需要从 task source 生成可训练环境：

```text
ingest PR / issue / fixture / synthetic task
filter by size and test availability
split code diff vs test diff
build executable image / fixture
run pre-fix tests
run post-fix tests
extract F2P and P2P
validate empty patch fails
validate golden patch passes
repeat to detect flaky tests
freeze EnvPackage
```

Microsoft 的 4.87M → 745K → 265K 过滤漏斗说明，环境构建本身就是主系统，不是一次性脚本。([Microsoft AI][1])

---

## 4.3 Sandbox / Runtime 层

需要支持：

```text
fresh sandbox per episode
network isolated by default
allowlist / caching proxy for required setup
workspace reset
resource limits
timeout
artifact collection
clean grader workspace
deterministic replay
```

Microsoft 的 SEE 强调 fresh container、任务完成后销毁、默认网络隔离、必要网络通过 cache proxy/domain allowlist。([Microsoft AI][1])

---

## 4.4 Harness 层

至少要有三种 harness：

```text
RepoHarnessNativeHarness:
  你自己的白盒 ReAct-style loop

MiniSWEHarness:
  bash-only baseline

ExternalShellHarness:
  opencode / SWE-agent-like / future Codex-like harness adapter
```

Microsoft 和 NVIDIA 都说明，SWE agentic training 不一定需要复杂 tool surface；Microsoft 只用 bash + string replacement，NVIDIA SFT 数据则刻意来自 OpenHands、SWE-agent、Mini-SWE-agent、Opencode 多个 harness。([Microsoft AI][1])

---

## 4.5 Tool / Permission 层

工具不应该只记录“调用了什么”，而应该抽象出 effect：

```text
Effect:
  read_file
  write_file
  delete_file
  run_command
  network_access
  git_history_access
  modify_tests
  install_package
  submit_patch
```

权限系统需要：

```text
PermissionSpec:
  allow / deny / require_approval

PermissionState:
  active grants
  pending approvals
  explicit boundaries
  audit log

PermissionDecision:
  allow / deny / ask / approve_with_conditions

Approver:
  human approver
  user simulator approver
  static policy approver
```

虽然两份报告没有专门讲“用户审批”，但 Microsoft 的 general tool-use stateful environments 和 environment-specific personas 支持你把 UserSim/PermissionSpec 做成 SWE 长任务的扩展。([Microsoft AI][1])

---

## 4.6 Rollout Group / Problem Worker 层

不要只跑单条 episode。你需要：

```text
RolloutTaskRequest:
  task_id
  env_spec
  harness_spec
  policy_version
  num_samples
  timeout
  builder_strategy
  evaluator_spec

ProblemWorker:
  early rollouts
  full rollouts
  retry failed rollout
  aggregate pass rate
  group filtering
  advantage normalization
  length penalty
  training eligibility
```

Microsoft 的 Rocket problem worker 正是这样：它不直接生成 rollout，而是向 rollout workers 发送请求；先 early-exit，再 full rollouts，再做 postprocessing 和 advantage normalization。([Microsoft AI][1])

---

## 4.7 Rollout Worker 层

每个 rollout worker 要能：

```text
initialize prompt
call model
parse tool calls
execute tools
append observations
repeat until final / step limit / context limit / timeout
run or defer grading
write event log
write generation records
write workspace diff
return artifact
```

这和 Microsoft rollout worker 描述一致：生成初始 prompt，发给 inference server，解析 response，执行 tool calls，把结果加入下一轮请求，直到无 tool call、达到 step/time limit，然后 grading。([Microsoft AI][1])

---

## 4.8 Capture / Trace / Token-Faithful 层

每条训练轨迹必须有：

```text
prompt_ids
response_ids / continuation_ids
loss_mask
response_logprobs
generation_records
model_call_id
policy_version
sampling_params
finish_reason
tool schema digest
renderer / tokenizer version
```

NVIDIA MOPD 要用 behavior/proximal/teacher token logprob；Microsoft 也强调 inference learner numerics gap 会影响 long rollout 的 off-policy correction。

你的 hard rule 应该是：

```text
没有 token provenance -> 不进 formal online RL
没有 per-token logprob -> 不进 formal online RL
loss_mask 无法解释 -> 不进 formal online RL
```

---

## 4.9 Rubric / Verifier / Reward 层

需要同时支持：

```text
Outcome reward:
  hidden tests pass
  F2P pass
  P2P preserved
  final state matches target

Process reward / penalty:
  malformed tool calls
  repeated denied actions
  no test after edit
  edit-test loop
  lost in exploration
  too much churn
  timeout / max turns
  permission violation

AI judge reward:
  task interpretation
  user interaction quality
  trajectory quality
  helpfulness
```

Microsoft 混合 verifiable reward 和 AI-feedback reward；NVIDIA 明确对 malformed reasoning/tool tokens 给 negative advantage，并 mask unfinished trajectories。([Microsoft AI][1])

---

## 4.10 Anti-cheat / Eligibility 层

正式进入 online RL 前必须检查：

```text
gold patch not visible
hidden tests not visible
future git history removed
network blocked / allowlisted
test files reset or hidden
test tampering detected
monkeypatch detected
debug artifacts removed
clean patch replay passed
```

Microsoft 和 NVIDIA 都把这些作为 SWE RL 的核心防线，而不是附属工程。([Microsoft AI][1])

---

## 4.11 Artifact Store / Persistent Rollout Store

每次 rollout 应该产出：

```text
TrajectoryArtifact:
  task_id
  env_id
  harness_id
  policy_version
  rollout_step
  group_id
  prompt_ids
  response_ids
  logprobs
  event log
  tool calls
  permission events
  workspace diff
  patch ref
  verifier report
  reward components
  eligibility class
  staleness
  failure category
```

Microsoft Rocket 图中明确有 persistent rollout store、metric store、checkpointing；NVIDIA 也强调 fine-grained checkpointing of in-flight rollouts、KV cache、conversation state 以降低恢复成本。([Microsoft AI][1])

---

## 4.12 Trainer Adapter / verl 层

你不应该让 core runtime 直接依赖 verl。正确边界是：

```text
TrajectoryArtifact
  -> RolloutGroupPackager
  -> StalenessFilter
  -> RewardNormalizer
  -> VerlAdapter
  -> verl batch
```

Microsoft 需要 controller 在 completed rollouts 上过滤、批处理、发给 learner；NVIDIA 的 asynchronous MOPD 也说明 rollout workers、teacher scoring workers、learner workers 应该 pipeline 化。([Microsoft AI][1])

---

# 5. 对你 RepoHarness 的具体架构建议

结合两篇报告，我建议你在原来 Prime/Polar 设计上补强下面几块。

## 5.1 把 `ComposableEnvSpec` 升级成 `SWEEnvPackageSpec`

你的 `ComposableEnvSpec` 可以是通用组合层，但 SWE 需要一个更具体的环境包：

```python
class SWEEnvPackageSpec:
    env_id: str
    task_id: str
    repo_snapshot_ref: str
    base_commit: str
    problem_statement_ref: str
    sandbox_spec: SandboxSpec
    tool_schema_spec: ToolSchemaSpec
    verifier_spec: VerifierSpec
    visibility_policy: VisibilityPolicy
    anti_cheat_spec: AntiCheatSpec
    expected_pre_fix: ExpectedOutcome
    expected_post_fix: ExpectedOutcome
    quality_report_ref: str | None
```

这对应 Microsoft 的 self-contained SWE container + verifier + F2P/P2P pipeline。

---

## 5.2 新增 `ProblemWorker`，不要只做 `RolloutWorker`

你现在如果只有：

```text
run_episode(task)
```

会不够像真实 RL infra。建议新增：

```python
class ProblemWorker:
    def run_rollout_group(task, policy_version, group_config):
        early = run_n_rollouts(n=group_config.early_n)
        if not pass_rate_in_range(early):
            return rejected_group_artifact

        full = run_n_rollouts(n=group_config.full_n)
        scores = grade(full)
        if not pass_rate_in_range(scores):
            return rejected_group_artifact

        advantages = normalize(scores)
        return RolloutGroupArtifact(...)
```

第一版可以用：

```text
early_n = 4
full_n = 16
```

不需要 Microsoft 的 16 + 128，但抽象要一致。

---

## 5.3 优先实现 `CleanPatchReplayEvaluator`

这是我认为你下一阶段最应该做的 evaluator：

```text
rollout workspace
  -> export cleaned final.patch
  -> create clean grader checkout from base commit
  -> apply patch
  -> apply hidden tests only in grader workspace
  -> run F2P/P2P
  -> produce reward + eligibility
```

如果没有 clean grading，后续做 user simulator / permission system 都会建立在不够可信的 reward 上。

---

## 5.4 新增 `TrajectoryHeuristicAnalyzer`

借鉴 NVIDIA 的 SFT 过滤，用于 warm-start / offline SFT：

```python
class TrajectoryHeuristicAnalyzer:
    signals:
      valid_submission
      disallowed_git_ops
      edit_test_loop
      lost_in_exploration
      malformed_tool_calls
      debug_artifacts
      edited_but_never_ran_tests
      permission_violations
      excessive_churn
```

输出：

```yaml
sft_candidate: true / false
online_rl_candidate: true / false
reject_reasons: [...]
```

这会让你的项目同时支持：

```text
SFT trajectory filtering
offline analysis
RL training eligibility
```

---

## 5.5 将 AntiCheatSpec 纳入环境，而不是写死在工具里

建议新增：

```python
class AntiCheatSpec:
    sanitize_git_history: bool
    scrub_future_refs: bool
    block_remote_git: bool
    block_github_http: bool
    reset_test_files_before_grading: bool
    hide_test_diff_until_grading: bool
    detect_test_monkeypatch: bool
    detect_debug_artifacts: bool
```

这个 spec 应该属于 environment / verifier 层，而不是 `bash` 工具内部的零散规则。

---

## 5.6 为未来 MOPD / teacher scoring 预留字段

你现在不做 MOPD，但 `TrainTrace` 可以预留：

```python
teacher_scores_ref: str | None
teacher_logprobs_ref: str | None
proximal_logprobs_ref: str | None
behavior_policy_version: str
proximal_policy_version: str | None
credit_assignment_strategy: str
```

这来自 NVIDIA 的 asynchronous MOPD 设计。

---

# 6. 哪些内容暂时不需要实现

你不需要在个人项目第一版中复制这些：

```text
1. Microsoft Rocket 全量分布式系统。
2. NVIDIA GB200 / Slurm / Ray GCS / topology-aware NVLink placement。
3. 多千 GPU inference pool。
4. 完整 weight transfer planner。
5. Multi-Token Prediction speculative decoding。
6. 完整 MOPD teacher-scoring pipeline。
7. 10,000+ CPU core environment builder。
```

但你应该借鉴它们背后的抽象：

```text
role separation
artifact lineage
failure attribution
staleness
health checks
rollout group
problem worker
clean grading
cache / reproducibility
```

也就是说，**不要复刻规模，复刻边界。**

---
