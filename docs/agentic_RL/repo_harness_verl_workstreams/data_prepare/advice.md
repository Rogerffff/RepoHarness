下面是我从两篇报告中整理出的**与训练/评测数据集构建相关的内容**。我会优先聚焦你关心的 **SWE coding agentic RL 后训练**：数据从哪里来、是否来自 GitHub issue/PR、公开数据集有哪些、如何清洗、如何选择 SFT/RL/评测数据、如何防止泄漏和 reward hacking。

## 1. 总体结论

两篇报告都有数据获取与数据处理章节，但侧重点不同。

**NVIDIA Nemotron 3 Ultra** 更像是“公开数据 + 多教师合成轨迹 + RL/MOPD recipe”的路线。它明确列出了一批可公开复用的数据与环境，包括 `Nemotron-Pretraining-Code-v3`、`Nemotron-Posttraining-v3`、SWE-Gym、R2E-Gym、SWE-rebench、SWE-smith、OpenCodeReasoning、OpenMathReasoning、SWE-bench、SWE-Fixer-Train-110K 等，并且详细描述了 terminal-use、software issue resolution、competitive coding、CUDA、RTL 等后训练数据的构建和过滤方式。NVIDIA 还强调它会发布 post-training recipes、datasets、RL environments，数据覆盖 reasoning、agentic、code、safety、usability、chat 等领域。

**Microsoft MAI-Thinking-1** 更像是“从原始 public GitHub PR/issue 批量生成可验证 SWE RL 环境”的工业化 pipeline。它没有说自己用某个开源 SWE 训练集直接训练；相反，它明确说预训练不使用 open-source training datasets，而是从 public/licensed 原始数据处理，包括 public GitHub code，并给出了从 **102M public GitHub PRs → 4.87M linked-issue PRs → 2.08M buildable → 745,452 extractable grading → 265,617 verified SWE RL problems** 的详细过滤流程。([Microsoft AI][1])

对你当前任务最有价值的部分是：**用 Microsoft 的 GitHub PR/issue → executable SWE environment 流程作为 RL 环境构建主干，用 NVIDIA 的多教师轨迹生成、多 harness、多数据源过滤策略补充 SFT 和 RL 数据多样性。**

---

## 2. 两篇报告中与数据获取相关的章节

### NVIDIA Nemotron 3 Ultra

NVIDIA 报告里最相关的是：

**§2.3 Pretraining Data**：描述预训练数据来源，包括 refreshed GitHub source code，并提到新增 173B tokens、cutoff 到 2025-09-30 的 GitHub code 数据；也提到 synthetic Q&A 来自公开数据集的训练 split，避免使用 held-out test split。

**§3.1.1 Data**：这是后训练数据核心章节。它包含 long-context、OpenResearcher、terminal-use、software issue resolution、competitive coding、CUDA、RTL、chat/instruction-following 等数据来源与处理细节。

**§3.1.2 Data Packing**：描述 SFT 数据 packing 策略，例如 length-aware best-fit packing、round-robin interleave、样本不截断不拆分、同 pack 内避免 duplicate prompt、最终 shuffle。这个对你做 SFT 数据组织很实用。

**§3.2 RL 与 §3.3 MOPD / Teachers**：描述统一 RLVR、SWE teacher、MOPD 多轮迭代、dense teacher signal、SWE end-to-end RL、hidden test reward、malformed tool call 惩罚、gold patch 防泄漏等。

**§3.7 / Appendix A evaluation**：描述 agentic eval 的 benchmark 和 harness robustification，例如 SWE-Bench Verified、SWE-Bench Multilingual、Terminal-Bench、GDPVal、ProfBench、PinchBench、TauBench、BrowseComp 等；并强调同类任务要用多个 harness 训练，避免模型过拟合某个交互框架。

### Microsoft MAI-Thinking-1

Microsoft 报告里最相关的是：

**§2.4 Pre-training Data / Appendix B.4 Public GitHub**：描述 public GitHub code corpus，包含 files、commits、PRs 三类数据，并给出过滤、去重、去污染、质量评分、语义去重、PR 数据结构等。([Microsoft AI][1])

**§2.5 Selecting a Data Mixture**：描述 data mixture 优化，包括 dedup、quality buckets、held-out NLL eval、small-scale ablation、target domain upweight、multi-epoch effect 等。([Microsoft AI][1])

**§3.2 Competitive Coding Data**：描述 competitive coding RL 数据，强调需要 test cases，所以使用 targeted 与 vendor-acquired sources；reference solutions 要验证；最终有 160K problems、17 种语言，并做 benchmark decontamination。([Microsoft AI][1])

**§3.3 Agentic Climb，尤其 §3.3.1 Software Engineering**：这是最重要的 SWE agentic RL 数据构建章节。它完整描述了从 GitHub PR/issue 构建 self-contained containerized SWE problem、提取 fail-to-pass tests、验证 golden patch、过滤 nondeterminism、重写 problem statement、防 reward hacking 等流程。([Microsoft AI][1])

**§4 / Appendix I evaluation**：描述 SWE-bench Verified、SWE-Bench Pro、Terminal-Bench 2.0 的评测设置，包括 ReAct loop、tools、context/output length、max steps、grader 在 isolated environment 中运行等。([Microsoft AI][1])

---

## 3. 报告中明确出现的公开数据集 / 公开来源

### NVIDIA 明确使用或提到的公开数据源

NVIDIA 在后训练中明确提到这些与 coding / SWE / agentic 相关的数据源：

| 类别                            | 数据源 / 来源                                                                                 | 用途                                                |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------- |
| 代码预训练                         | `Nemotron-Pretraining-Code-v3`，fresh GitHub code，173B tokens，cutoff 2025-09-30           | 代码预训练                                             |
| 后训练公开数据                       | `Nemotron-Posttraining-v3`                                                               | agentic、reasoning、general SFT/RL                  |
| Terminal-use / SWE-like tasks | OpenCodeReasoning、OpenMathReasoning、SWE-bench、SWE-Fixer-Train-110K、SWE-rebench、SWE-smith | 生成 terminal agent 轨迹                              |
| GitHub issue resolution       | SWE-Gym、R2E-Gym、SWE-rebench、SWE-rebench-V2                                               | 从真实 GitHub issue statement 生成 issue resolution 轨迹 |
| Competitive coding            | Codeforces、AtCoder、AIZU、CodeChef                                                         | 生成 Python/C++/tool-calling reasoning traces       |
| CUDA                          | open-source libraries、NVIDIA APIs、BackendBench                                           | kernel generation / repair / optimization         |
| RTL                           | ACE-RTL / ScaleRTL 风格数据，license-checked open-source RTL repos                            | Verilog/RTL 生成、编辑、debug                           |
| Web research agent            | OpenResearcher commercial-cleared subset                                                 | search/open/find browser-tool 轨迹                  |

NVIDIA 的 software issue resolution 数据特别值得借鉴：它使用 MiniMax-M2.5 和 Qwen3-Coder-480B-A35B 作为 teacher，从 SWE-Gym、R2E-Gym、SWE-rebench、SWE-rebench-V2 中取 issue statements，并用 OpenHands、SWE-agent、Mini-SWE-agent、Opencode 等多个 agent framework 捕获解决轨迹。

NVIDIA 还对每条 SWE 轨迹做 heuristic analysis，例如检查是否有 valid submission、是否出现不允许的 git 操作、是否陷入 edit-test loop、是否 lost in exploration、是否有 malformed tool call、patch 里是否有 debug artifact、是否 edit without tests verification 等。这个非常适合直接转成你的数据过滤规则。

### Microsoft 明确使用或提到的公开来源

Microsoft 的报告没有给出一串开源 SWE 训练集名称；它反而强调：预训练不直接使用 open-source training datasets，而是从 web、public GitHub code、books、academic papers、news、multilingual/domain-specific data 等原始 public/licensed 数据处理，并且不使用 LM-generated synthetic data 做预训练。([Microsoft AI][1])

但在 coding/SWE 上，它给出了非常详细的 public GitHub 数据构建方式：

| 类别                      | 来源                                                                                  | 用途                              |
| ----------------------- | ----------------------------------------------------------------------------------- | ------------------------------- |
| Public GitHub files     | public GitHub repositories 的最新文件                                                    | 代码预训练                           |
| Public GitHub commits   | 每个 repo 最新最多 10K commits                                                            | patch/diff 形式的代码预训练             |
| Public GitHub PRs       | PR title/body、linked issues、comments、reviews、review threads、commits、precommit files | PR-level code/change/review 预训练 |
| Public GitHub PR/issues | 102M public GitHub PRs 起步，筛选 merged PR、linked issues、code+test changes              | 构建 executable SWE RL problems   |
| Public evals            | SWE-bench Verified、SWE-Bench Pro、Terminal-Bench 2.0、LiveCodeBench v6 等              | coding / agentic coding 评测      |

Microsoft 的 public GitHub code corpus 规模是 7.4T tokens，分为 files、commits、PRs 三类，经过 shared filtering、deduplication、decontamination、quality scoring，最终得到 1.26T file tokens、4.5T commit tokens、1.19T PR tokens。([Microsoft AI][1])

---

## 4. 从 GitHub issue / PR 构建 SWE RL 数据的关键流程

这一部分 Microsoft 报告给得最完整，可直接作为你的 pipeline 模板。

### 4.1 原始 PR 过滤

Microsoft 从 102M public GitHub PRs 开始，过滤条件包括：PR 已 merge 到 main；修改文件数小于 15；同时包含 code changes 和 test changes；能通过 patch file contents 区分 code/test；并且 PR linked 到 GitHub、Jira、Bugzilla、YouTrack、Phabricator、Launchpad、Linear 等 issue tracker。经过这一步剩下约 4.87M PRs with linked issues。([Microsoft AI][1])

这对你的数据构建意味着：不要直接抓 issue；更好的单位是 **linked issue + merged PR + test diff + code diff + base commit**。issue 提供 problem statement，PR code diff 提供 golden patch，test diff 提供 hidden grading signal。

### 4.2 构建 executable container

Microsoft 使用 LLM agent 为 repo 创建 Docker/build files，安装依赖并构建可执行容器；如果是 dependency 或 environment error，就丢弃。最终每个 SWE RL problem 是一个 self-contained container：repo checkout 到某个 commit，dependencies installed，包含 problem statement 和 grading tests。rollout 时 agent 可以 read/edit files、run shell、navigate repo；grader 在最后运行 tests。([Microsoft AI][1])

这说明你的训练样本最好不是普通 `(issue, patch)` pair，而是：

```text
repo + base_commit + issue_statement + editable_workspace + hidden_tests + grader + allowed_tools
```

也就是一个可交互的 RL environment。

### 4.3 提取 F2P / P2P tests

Microsoft 的 reference grading 是：在 base commit 上只应用 test diff，运行 tests，找到 fail-to-pass tests；再应用 test diff + code diff，确认 golden patch 后这些 tests 通过。同时 pass-to-pass tests 用于检测 regression。如果没有 fail-to-pass tests，就丢弃。([Microsoft AI][1])

这给你一个很强的过滤标准：

```text
base + test_diff: F2P tests 必须 fail
base + test_diff + golden_code_diff: F2P tests 必须 pass
P2P tests: 应该继续 pass
```

也就是 RL reward 不应该只看“所有测试通过”，而应该区分：

```text
issue resolution signal: F2P
regression signal: P2P
```

### 4.4 反复验证，过滤 nondeterminism

Microsoft 还在最终 Standardized Execution Environment 中重新验证：empty patch 必须失败，golden patch 必须成功，并且要做 multiple trials，以过滤 nondeterministic tests 和 reward noise。([Microsoft AI][1])

这一步对 RL 很关键，因为 noisy reward 会直接污染 advantage estimation。你的数据入库前最好至少保存：

```text
empty_patch_result
golden_patch_result
num_validation_trials
flaky_test_detected
f2p_test_names
p2p_test_names
grader_command
```

### 4.5 Problem statement 质量过滤与重写

Microsoft 会过滤 vague/underspecified problem statements，并让 agent 评分 clarity、test quality、leakage risk、feasibility；对于低质量 statement，会重写成“足够明确但不泄漏、不 over-specify”的版本。最终从 4.87M linked PRs 到 265,617 verified SWE problems，只保留约 5.5%，覆盖 94,044 repos。([Microsoft AI][1])

这说明你应该把 problem statement 单独建模为数据质量对象，而不是默认信任 GitHub issue 原文。建议至少打这些分：

```text
clarity_score
reproducibility_score
leakage_risk_score
overspecification_score
test_quality_score
feasibility_score
requires_external_service
requires_large_runtime
```

### 4.6 防止 reward hacking / 泄漏

Microsoft 和 NVIDIA 都非常强调 SWE RL 的泄漏与 hacking 问题。

Microsoft 的做法包括：默认 network isolation；必要时只通过 proxy/allowlist 开放网络；scrub local git history after base commit；隐藏 test changes 直到 grading；grading 前 reset agent-modified test files；用 LLM monitor 和 human review 检查 monkey patch、test tampering 等。([Microsoft AI][1])

NVIDIA 的做法包括：把 repo 重写成 base commit 的 fresh clone，删除 future commits，防止 gold patch 泄漏；运行时 command filter 阻止 remote git、GitHub web/raw/Pages 等路径；对 malformed reasoning/tool call 给 negative advantage；未完成 trajectories mask 掉。

你的 SWE RL 环境建议默认加入这些规则：

```text
禁用/限制网络
删除 .git 中 base commit 之后历史
隐藏 tests / test_diff / golden patch
禁止 git fetch/pull/clone/push
禁止访问 GitHub raw/web/pages
grading 前恢复 test files
检测 monkey patch、硬编码测试、修改 grader、跳过测试
记录所有 shell/tool calls
```

---

## 5. 数据清洗、去重、去污染细节

### NVIDIA 的数据清洗

NVIDIA 在 software issue trajectories 上使用 heuristic analyzer，检查 valid submission、不允许的 git 操作、edit-test loop、lost-in-exploration、malformed tool calls、debug artifacts、没有测试验证的编辑等。

在 competitive coding 上，NVIDIA 对 Codeforces、AtCoder、AIZU、CodeChef 题目做 strict dedup 和 aggressive filtering，并通过 teacher rejection sampling 生成 Python、C++、tool-calling reasoning traces。

在 CUDA 数据上，NVIDIA 先从 open-source libraries、NVIDIA APIs、BackendBench 获取种子，再生成 kernel generation/repair/optimization 样本；候选会经过 compilation、numerical correctness、runtime benchmark 验证，丢弃 invalid、noncompiling、incorrect 的样本，并保留最快 valid candidate。

在 RTL 数据上，NVIDIA 使用 license-checked open-source RTL repos，经过 dedup、filter、syntax validation、benchmark decontamination、semantic alignment human rubrics，最终约 1.2M samples。

### Microsoft 的数据清洗

Microsoft 的 public GitHub code 数据清洗非常细：移除 `node_modules`、build artifacts、`__pycache__`、`.vscode`、generated code、non-code types、超过 30K chars 或 excessive long lines 的文件，并做 character composition filtering。去重包括 exact SHA-512 dedup、MinHashLSH fuzzy dedup，以及用 Qwen3-Embedding-0.6B 做 semantic dedup。还会针对 reasoning/eval 中用到的 coding problems 做 decontamination。([Microsoft AI][1])

Microsoft 还提到 public eval leakage 在 GitHub 上很常见，所以会移除 Hugging Face 和 mirrors，并用 universal 20-gram fuzzy dedup，在 80% 阈值下跨训练源做去重；同时承认这种方法并不完美，因此还会依赖 private benchmarks。([Microsoft AI][1])

对于 STEM/coding RL 数据，Microsoft 使用 SHA-256、character n-gram MinHash LSH、embedding cosine similarity 做 self-dedup 和 benchmark dedup，阈值会调到防止 benchmark leakage。([Microsoft AI][1])

---

## 6. SFT / RL 训练数据选择策略

### 6.1 SFT 轨迹数据

NVIDIA 的 terminal-use SFT 数据是 synthetic agent trajectories，覆盖 software engineering、data processing、file operations、scientific computing 等。数据来源包括 OpenCodeReasoning、OpenMathReasoning、SWE-bench、SWE-Fixer-Train-110K、SWE-rebench、SWE-smith，最终 terminal-use 数据约 370K multi-turn conversations。

NVIDIA 的 software issue resolution 数据专门面向真实 GitHub issues，使用多个 teacher model 和多个 agent framework 采集轨迹，这一点很重要：它不是只训练模型学一个固定 harness，而是刻意让模型看到 OpenHands、SWE-agent、Mini-SWE-agent、Opencode 等不同交互格式，提升泛化性。

Microsoft 在 self-distillation 上的经验是：约 O(1M) 条 reasoning traces 已经足够，更多 trace 可能过度约束 policy；它最终主要使用 successful traces，并发现 prompt diversity 比同一个 prompt 上更多 traces 更有价值，同时会混入 mid-training 数据避免长上下文遗忘。([Microsoft AI][1])

对你的 SFT 数据选择建议是：

```text
优先选择：
1. 成功解决 issue 的完整轨迹
2. 有 read/edit/test/debug 循环，但没有明显 reward hacking 的轨迹
3. 多 framework / 多 tool schema / 多 teacher 生成的轨迹
4. 中等难度、多文件、需要定位 bug 的任务
5. 有明确测试验证的 patch

降权或丢弃：
1. 只靠猜测 patch、没有运行测试
2. 大量无效探索、重复 ls/cat/grep
3. 修改 tests、修改 grader、硬编码 hidden tests
4. 使用 git fetch/pull/clone 等外部泄漏通道
5. malformed tool calls 或 final patch 无法应用
```

### 6.2 RL 数据选择

Microsoft 的 RL sampling 策略很值得复用：先对每个 problem 做 early-exit rollout，如果 early pass rate 落在目标区间，才继续生成完整 rollout；这样可以丢掉太容易或太难的 task，保留有学习信号的 problem group。之后计算 normalized advantages，并结合 length penalty / GRPO reward normalization。([Microsoft AI][1])

NVIDIA 的 RLVR 覆盖 terminal use、software engineering、search、tool-calling、math、code、STEM、safety、chat、instruction following、long-context QA 等，并使用 Gaussian-based mixture/curriculum、Async GRPO、16 rollouts per sample、长生成长度等设置。

Microsoft 还明确说，jointly climb on agentic and reasoning-focused STEM，包括 competitive coding，有助于稳定 RL，并迁移到 SWE/tool-calling。([Microsoft AI][1])

对你的 RL 数据池建议分成四类：

```text
A. SWE executable repo tasks
   来源：GitHub PR/issue、SWE-Gym、R2E-Gym、SWE-rebench、SWE-smith
   reward：F2P/P2P hidden tests

B. Terminal coding tasks
   来源：Terminal-Bench-like、自建 shell/file/data tasks
   reward：programmatic grader

C. Competitive coding / algorithmic reasoning
   来源：Codeforces/AtCoder/AIZU/CodeChef/LiveCodeBench-style
   reward：unit tests / hidden tests

D. General tool-use tasks
   来源：mock APIs、MCP-style tools、stateful enterprise tasks
   reward：final state / tool usage / answer correctness
```

---

## 7. 数据 packing 与 mixture

NVIDIA 的 SFT packing 细节可以直接照搬：使用 length-aware best-fit packing；按数据源 round-robin interleave；不 truncate、不 split 单个样本；同一个 pack 内避免 duplicate prompt；最后全局 shuffle，保证每个 batch 是多源混合。

Microsoft 的 data mixture 选择更偏系统化：先把数据分成 buckets，用 metadata、source-specific heuristics、learned classifiers、prompted LLMs、manual labeling 做过滤和分类；再用小模型做大量 mixture ablations，通过 held-out NLL eval 预测大模型效果，并考虑 domain balance、quality、unique tokens、repetition、multi-epoch effects。([Microsoft AI][1])

Microsoft 在 consolidation SFT 中披露了大类比例：按 sample 数，STEM & Coding 56%、Agentic 11%、Helpfulness/Safety 33%；按 token 数，STEM & Coding 89%、Agentic 9%、Helpfulness/Safety 2%。后续 consolidation RL 仍保留少量 STEM/coding，以维持 reasoning 能力。([Microsoft AI][1])

对你做 SWE coding agentic RL，初版 mixture 可以考虑：

```text
SFT:
- 40–60% SWE / terminal agent trajectories
- 20–40% competitive coding / code reasoning traces
- 10–20% general instruction / tool-use / safety
- 少量 long-context repo navigation 样本

RL:
- 主体放在 executable SWE tasks
- 混入 competitive coding 稳定 reasoning
- 混入 terminal tasks 提升 shell/debug 能力
- 混入 no-tool-needed / simple tasks 防止过度调用工具
```

这个比例不是报告原样，而是根据两篇报告的共同经验抽象出的起步方案。

---

## 8. 评测数据选择与协议

NVIDIA 的 agentic eval 包括 Terminal-Bench 2.1、GDPVal、SWE-Bench Verified、SWE-Bench Multilingual、ProfBench、PinchBench、TauBench V3、BrowseComp、Financial Agent Benchmark 等，并强调使用统一 evaluation SDK / harness，固定 resources、input data、prompts、repeats、metrics、inference params。

Microsoft 的 agentic coding eval 主要包括 SWE-bench Verified、SWE-Bench Pro、Terminal-Bench 2.0。它使用 ReAct loop，SWE 任务工具是 bash + string replace editor，Terminal-Bench 是 bash；总 context 256K，SWE max output 8K，Terminal-Bench max output 32K，max 1000 steps，grader 在 Standardized Execution Environment 中运行。([Microsoft AI][1])

Microsoft 还说明 SWE-bench Verified 是 SWE-bench 的 500-task human-curated subset，来自 public GitHub issues，hidden tests，并经人工审核 solvable/fair；SWE-Bench Pro 有 731 tasks，更难，覆盖真实 OSS、多文件 edits、长程任务和 Python 以外语言；Terminal-Bench 2.0 有 89 tasks，覆盖 SWE、debug、data science、ML、security、sysadmin 等。([Microsoft AI][1])

你的评测集建议至少分三层：

```text
Public eval:
- SWE-bench Verified
- SWE-Bench Pro
- Terminal-Bench 2.x
- LiveCodeBench v6 / competitive coding
- BFCL / tool-calling eval，如果你的 agent 有 function calling

Private held-out eval:
- 自己从 GitHub PR/issue pipeline 留出的 repos/tasks
- 与训练 repo、issue、PR、patch、test names 做严格去重
- 最好包含不同语言、不同 build systems、不同 repo size

Regression eval:
- shell misuse / test tampering / git history leakage
- 修改 tests、硬编码 expected output、跳过 grader
- long-context repo navigation
- flaky tests / nondeterministic environment stress test
```

---

## 9. 给你当前数据集构建的落地 schema

结合两篇报告，我建议你把每个 SWE RL 样本整理成下面这种结构：

```yaml
task_id:
source:
  repo_url:
  repo_name:
  base_commit:
  pr_id:
  issue_id:
  issue_tracker:
  license:
problem:
  original_issue_text:
  rewritten_statement:
  clarity_score:
  feasibility_score:
  leakage_risk_score:
patches:
  golden_code_diff:
  test_diff:
tests:
  f2p_tests:
  p2p_tests:
  grader_command:
  empty_patch_result:
  golden_patch_result:
  validation_trials:
  flaky_tests:
environment:
  dockerfile:
  image_id:
  setup_script:
  allowed_tools:
  network_policy:
  git_history_scrubbed:
  hidden_tests_visible_to_agent: false
trajectory:
  teacher_model:
  harness:
  tool_schema:
  messages:
  tool_calls:
  final_patch:
  final_reward:
quality_flags:
  valid_submission:
  malformed_tool_call:
  disallowed_git_operation:
  edit_test_loop:
  lost_in_exploration:
  debug_artifacts_in_patch:
  modified_tests:
  reward_hacking_suspected:
split:
  train_or_eval:
  split_reason:
decontamination:
  exact_hashes:
  minhash_signature:
  embedding_signature:
  benchmark_overlap_flags:
```

最重要的是：**训练数据可以来自公开 GitHub，但评测数据必须做 repo/PR/issue/patch/test 多层隔离**。Microsoft 明确指出 public eval leakage 在 GitHub 上很常见，单靠模糊去重仍不完美，所以它使用 private benchmarks 辅助日常开发；这一点对 SWE agentic RL 尤其关键。([Microsoft AI][1])

---

## 10. 最值得你直接复用的设计

我会把两篇报告提炼成一个最小可行 pipeline：

```text
1. 从 public GitHub PRs 抽取候选：
   merged PR + linked issue + code diff + test diff + <15 files

2. 构建容器：
   checkout base commit → install deps → run tests → 失败则丢弃

3. 提取 reward：
   base + test_diff 必须 fail
   base + test_diff + golden_patch 必须 pass
   P2P tests 用于 regression

4. 验证稳定性：
   empty patch fail
   golden patch pass
   多次运行过滤 flaky tests

5. 清洗 statement：
   过滤 vague / leakage / over-specific
   必要时重写 issue statement

6. 防 hacking：
   禁网或 allowlist
   scrub git history
   隐藏 tests 和 future commits
   禁 git remote / GitHub raw
   grading 前 reset tests

7. 生成 SFT trajectories：
   多 teacher、多 harness、多 tool schema
   只保留 successful 或高质量失败轨迹
   过滤 malformed/tool misuse/no-test/debug-artifact

8. RL 采样：
   early-exit pass-rate band
   丢弃太简单/太难任务
   用 GRPO/advantage normalization
   混入 competitive coding 和 terminal tasks 稳定训练

9. 评测：
   public: SWE-bench Verified / SWE-Bench Pro / Terminal-Bench
   private: held-out GitHub PR/issue tasks
   safety/regression: reward hacking 和 tool misuse 专项集
```

简而言之，**NVIDIA 给了你可直接拿来扩充数据池的公开数据源与 agent trajectory filtering 思路；Microsoft 给了你从 GitHub issue/PR 到可执行 SWE RL 环境的完整工业级 recipe。**

[1]: https://microsoft.ai/wp-content/uploads/2026/06/main_20260602_2.pdf "MAI-Thinking-1: Building a Hill-Climbing Machine"
