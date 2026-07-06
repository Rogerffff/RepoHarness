# 第 3 讲：数据与任务合成 I——coding / SWE / repo repair

这一讲开始进入和 coding agent / SWE agent 最直接相关的部分：

> 如何把 GitHub issue、PR、commit、test、repo、Docker 环境，转化成可以用于 **SFT / RL / OPD / agent 评测** 的训练任务？

这一讲只讲 **coding / SWE / repo repair**。Terminal、AppDev、browser、office、slides、workspace 会放到第 4 讲。

---

## 1. 本讲核心结论

先给结论：

**现代 coding-agent 训练的核心数据单位，不是“代码文件”，也不是“问答样本”，而是一个可执行的软件工程任务。**

它通常长这样：

```text
Task = {
  problem_statement,
  repo_snapshot_at_base_commit,
  buggy_state,
  optional_gold_patch,
  hidden_or_public_tests,
  verifier_script,
  executable_environment,
  tool_schema,
  rollout_trajectory,
  reward_result
}
```

也就是说，一条高质量 SWE 训练样本至少要回答六个问题：

1. **任务是什么？**
   issue / problem statement 是否清楚。

2. **模型从哪里开始？**
   base commit / buggy repo state 是什么。

3. **正确答案是什么？**
   gold patch 或 expected behavior 是什么。

4. **如何验证？**
   test patch、hidden tests、F2P/P2P tests、verifier script 如何构造。

5. **在哪里执行？**
   Docker / sandbox / repo environment 是否可复现。

6. **如何产生训练轨迹？**
   agent 如何读文件、运行命令、修改代码、debug、提交 patch。

这一讲最重要的一句话是：

> **GitHub PR 不是直接拿来训练模型的代码语料，而是可以被还原成“问题、初始状态、答案、测试、环境、轨迹”的任务生成原料。**

---

# 2. 为什么 GitHub PR 是 SWE agent 数据的核心来源？

GitHub PR 天然包含几类对 agent 训练非常有价值的信号：

```text
Issue / PR title / PR description  →  problem statement
Base commit / changed files         →  starting repo state
Code diff                           →  gold patch
Test diff                           →  hidden tests / verifier
Review comments                     →  reasoning / critique / code review signal
CI / test output                    →  execution signal
```

这就是为什么 Qwen、MiniMax、GLM、DeepSeek、Microsoft 都把 GitHub issue/PR 作为 SWE 环境构造的主来源。

Qwen3-Coder-Next 报告明确说，它有两种生成可验证任务的方法：第一种从真实软件工程问题出发，挖掘 GitHub PR 并构造 runnable environments；第二种从已有可执行环境的数据集出发，在其中合成新的任务实例。它还会把 PR 分解成 buggy state、fix 和 test patch，并由环境构建 agent 生成 Docker 环境和 verification script。([arXiv][1])

MiniMax-M2 也把 GitHub PR 看成结构化 SWE 训练数据的来源：一个 well-structured PR 通常包含问题描述、代码变更和测试用例，因此能提供 objective correctness signals；但它也强调原始 PR 数据噪声很大，不能直接使用，需要经过过滤、环境构造、任务分类和 verifier 构造。([arXiv][2])

Microsoft 的 MAI-Thinking-1 报告披露了非常具体的规模：它们从 1.02 亿个 public GitHub PR 开始筛选，要求 PR 已合并、修改文件少于 15 个、同时包含代码和测试变更，并且和 GitHub/Jira/Bugzilla/YouTrack/Phabricator/Launchpad/Linear 等 issue 系统有关联；这一阶段后得到约 487 万个带 linked issues 的 PR。([Microsoft AI][3])

所以 GitHub PR 的价值不是“里面有代码”，而是它天然接近一个 supervised / verifiable repair episode：

```text
有人报告问题
→ 开发者修改代码
→ 添加或修改测试
→ PR 被合并
→ CI / test 通过
```

这正好是 SWE agent 要学习的行为。

---

# 3. 通用 pipeline：从 PR 到 SWE training task

我们先抽象出一个通用流程。后面每篇报告都可以映射到这条 pipeline。

```text
Raw GitHub PRs
  → PR / Issue Filtering
  → Base Commit Reconstruction
  → Problem Statement Construction
  → Code Diff / Test Diff Separation
  → F2P / P2P / P2F Extraction
  → Docker / Sandbox Environment Build
  → Verifier Script Construction
  → Environment Validation
  → Task Quality Filtering / Rewriting
  → Agent Rollout / Trajectory Generation
  → SFT / RL / OPD Data
```

逐步解释。

---

## 3.1 PR / Issue Filtering：先过滤原始 PR

原始 GitHub PR 不能直接用，因为里面有大量不适合训练的样本：

* 没有关联 issue；
* issue 描述太短，比如 “fix bug”；
* 只改文档，没有代码行为；
* 没有测试；
* patch 太大，涉及太多文件；
* 依赖过旧，环境无法构建；
* CI 不可复现；
* 测试和代码变更无法分离；
* 可能和 benchmark 重叠；
* PR 信息泄漏了答案。

因此第一步是筛选。

Microsoft 的 pipeline 要求 PR 已合并、修改文件数少于 15、同时含代码和测试变化，并且关联外部 issue；Qwen 也会去除与 downstream benchmarks 重叠的实例；MiniMax-M2 则强调从 public GitHub repositories with permissive licenses 中抓取 PR 和 linked issues，并使用 rule-based quality filter。([Microsoft AI][3])

这里的工程要点是：

> **过滤条件不是越严格越好，而是要在规模、可验证性和任务多样性之间平衡。**

太严格，剩下的任务太少、分布窄。
太宽松，环境构建失败率高、reward 噪声大。

---

## 3.2 Base Commit Reconstruction：还原模型要面对的初始状态

SWE agent 不能看到最终代码。
训练任务必须把 repo 还原到问题发生时的状态。

通常做法是：

```text
base repo = repo at commit before PR fix
gold patch = PR code diff
test patch = PR test diff
```

Qwen 会把 PR 分解成 buggy state、fix 和 test patch；Microsoft 会将 repository checkout 到 specific commit，并把 problem statement 和 grading unit tests 一起封装进 self-contained container image。([arXiv][1])

这里有一个容易忽略但非常关键的问题：**git history 泄漏**。

如果 repo 里保留了未来 commit，agent 可以通过 `git log`、`git show`、remote fetch 等方式找到答案。这不是模型会修 bug，而是环境泄漏。Microsoft 和 NVIDIA 都明确处理这个问题：Microsoft 会 scrub base commit 之后的 commits、references 和 branches，构造“time-traveled” repo；NVIDIA 的 SWE teacher 训练也会把容器内 repo 改写成 base commit 时刻的 fresh clone，并删除未来 commits，同时阻止通过网络把历史拉回来。([Microsoft AI][3])

所以一个 SWE environment 不只是 checkout 一个 commit，还要做：

```text
remove future git history
hide gold patch
hide test patch
block remote recovery
sanitize local references
```

这在后面的 reward hacking 讲会继续展开。

---

## 3.3 Problem Statement Construction：问题描述要“足够清楚但不过度泄漏”

一个 PR 的 linked issue 可能很糟糕：

```text
fix bug
handle edge case
improve parser
test failed
```

这种描述对真实开发者可能足够，因为他们有上下文，但对训练 agent 来说太模糊。
如果 hidden tests 期待一个很具体的行为，而 issue 没说清楚，模型只能猜测试。

Microsoft 报告非常明确地指出：即使环境能执行、测试也严密，仍然可能有低质量或 underspecified problem statements，例如 “fix things”；如果 problem statement 和 grader tests 之间有很大 gap，模型就只能猜测测试要求。Microsoft 的做法是部署一个 agent 在同一环境中检查 problem statement、repo 和 tests，并按照 specification clarity、test quality、leakage risk、feasibility 打分；对低质量任务，agent 会重写问题描述，使其更贴近测试要求，同时避免泄漏和过度规定。([Microsoft AI][3])

这个细节很重要。它说明 SWE task 不是简单地取 issue title，而要构造一个训练友好的 problem statement：

```text
clear enough to solve
not so specific that it leaks tests
not so vague that model must guess
aligned with expected behavior
```

这也是 coding-agent 数据工程和普通代码预训练数据工程的巨大区别。

---

## 3.4 Code Diff / Test Diff Separation：把 PR 拆成“答案”和“验证器”

PR 里通常有两类变化：

```text
code changes  → gold solution
test changes  → hidden tests / verifier
```

训练时，模型不能看到 gold patch 和 hidden tests。
但环境构造器可以用它们来定义验证逻辑。

Microsoft 对 test 和 code changes 做分离，让 grader 使用 test changes 作为 hidden tests 评估模型是否修复问题；Qwen 也会把每个 PR 分解成 fix 和 test patch；DeepSeek-V3.2 则要求每个样本含 reasonable issue description、correlated gold patch 和 test patch。([Microsoft AI][3])

这一步的核心思想是：

```text
gold patch is for building/verifying the task
not for the model to imitate directly during RL
```

对于 SFT，可以用 gold patch 构造 supervised edit data。
对于 RL，gold patch 更多用于验证 task 是否有效，而不是直接暴露给 agent。

---

## 3.5 F2P / P2P / P2F：可验证 reward 的核心

SWE agent reward 通常来自测试状态变化。

常见术语：

```text
F2P = Fail-to-Pass
P2P = Pass-to-Pass
P2F = Pass-to-Fail
```

含义是：

* **F2P**：在 bug 状态失败，应用正确 patch 后通过。
  这是 issue 被修复的主要信号。

* **P2P**：原来通过，patch 后仍然通过。
  这是不引入回归的信号。

* **P2F**：原来通过，patch 后失败。
  这是回归或破坏已有功能的负信号。

MiniMax-M2 对不同 PR 类型区分不同 verifier：bug fix 用 F2P 和 P2P；feature addition 不一定适用传统 F2P/P2P，因此重点抽取新增测试点并确保 golden patch 通过；performance optimization 则关注 P2P tests 能否验证优化前后稳定且显著的性能差异。([arXiv][2])

Microsoft 的做法也很典型：先在 base commit 上只应用 test diff 得到 pre-fix 结果，再应用 test diff + code diff 得到 post-fix 结果；F2P tests 是 issue-resolution signal，P2P tests 是 regression signal；没有 surviving F2P tests 的问题会被丢弃。([Microsoft AI][3])

DeepSeek-V3.2 的 code agent pipeline 也要求：应用 gold patch 后有非零 F2P test cases，并且 P2F test cases 为零，才认为环境构建成功。([arXiv][4])

这一步决定 reward 质量。
如果 F2P 太少，模型学不到修复信号。
如果 P2P 太弱，模型可以通过粗暴改动让 hidden tests 过但破坏已有功能。
如果 tests 非确定，RL reward 会变成噪声。

---

# 4. 报告细节对比

下面按报告讲具体做法。

---

## 4.1 Qwen3-Coder-Next：从 PR 和合成 bug 两条路线扩展 SWE tasks

Qwen3-Coder-Next 在本讲中最值得读的是 **task synthesis + executable environment + multi-turn trajectory**。

它有两条 task synthesis 路线：

```text
Route A: Real GitHub PRs
  → issue-related PRs
  → buggy state / fix / test patch
  → Docker env + verification script
  → QA filtering

Route B: Existing executable datasets
  → curated containerized repositories
  → controlled bug injection
  → issue description synthesis
  → test-fail / patch-reversion validation
```

第一条路线从真实 issue-related PR 出发，构造 runnable Docker environment 和 verification script；第二条路线是在已有可执行 repo 中注入 controlled bugs，并保留那些会 fail existing tests、且 patch reversion 能修复的任务。报告称这个过程产生约 80 万个 verifiable SWE task instances，覆盖 9 种以上编程语言。([arXiv][1])

Qwen 的另一个关键点是 mid-training 数据。它不只是训练单文件代码，而是扩大 repo-level code 和 PR 数据：报告说 GitHub 语言覆盖从 92 种扩展到 370 种，强调 repository-level code 以学习跨文件依赖，并把训练上下文扩展到 262,144 tokens；repo-level 数据约 600B tokens。([arXiv][1])

Qwen 还把 PR 转成结构化 SWE task，每个实例包含自然语言问题描述、repo-level code context 和 code edits；问题描述来自 linked issues，若没有则来自 PR title/description；它会 revert PR patch 并检索额外相关文件，引入真实的 signal/noise 混合；编辑格式同时使用 Search-and-Replace 和 git diff，以支持不同 editing paradigms。([arXiv][1])

最值得注意的是多轮 agentic coding 轨迹。Qwen 用多个 agent framework 生成 trajectories，包括 SWE-agent、Mini-SWE-agent、OpenHands、Claude-Code、Qwen-Code 和 Terminus；生成后进行严格 rule-based filtering，去掉缺失终止信号、任务失败、malformed tool calls 等样本。报告还观察到：同一 scaffold 内随着 mid-training tokens 增加性能提升明显，但跨 scaffold transfer 有限。([arXiv][1])

这对我们后面讲 scaffold 很重要：

> **coding agent 数据不是只要“多”，还要覆盖多种 scaffold / tool protocol，否则模型可能只学会某个 agent harness 的习惯。**

---

## 4.2 MiniMax-M2：把 SWE 数据构造成“任务类型 → reward 类型”的体系

MiniMax-M2 的 SWE 数据管线更像一个完整的工程 taxonomy。

它把 agentic coding 数据分成三个域：

```text
SWE
AppDev
Terminal interaction
```

本讲只看 SWE。MiniMax-M2 说 SWE 数据构造有三个耦合挑战：task diversity、objective verifiability、scale。它的 SWE-scaling pipeline 从 public GitHub repositories with permissive licenses 中抓取 PR 和 linked issues，保留 code diff、test files、problem statements，并用规则过滤 merged PR 和包含相关测试的 PR。([arXiv][2])

MiniMax-M2 非常强调多语言 Docker 环境构建。报告指出非 Python 环境更难，因为有不同依赖、版本冲突、编译工具链、测试接口和 repo 结构差异；因此它引入 agent-driven execution loop，根据 execution feedback 迭代生成和修复 build scripts。([arXiv][2])

它的关键设计是 **PR tagging and task diversification**。PR 被分成 bug fix、feature addition、performance optimization、refactoring、test construction 等类型；不同任务类型对应不同 reward formulation。比如 bug fix 用 F2P/P2P；feature addition 聚焦新增测试点；performance optimization 需要验证性能变化；test construction 可以被反转成 SWE-Test，让 agent 写一个在 pre-patch 失败、post-patch 通过的测试。([arXiv][2])

MiniMax-M2 还加入多种 task augmentation：

```text
bug injection
commit merging
SWE-Test conversion
code review tasks
```

其中 commit merging 用相邻 commits/PRs 构造更复杂的多步 repair tasks；SWE-Test 把“修 bug”反转成“写测试”；code review task 不一定需要 runnable env，而是让模型静态分析代码变更并识别潜在缺陷，结果由 secondary LLM 验证。最终每个 SWE 实例包含 problem statement、test-based verifiable reward 和 runnable Docker environment，覆盖 10 种以上编程语言和多种 coding task 类别。([arXiv][2])

MiniMax-M2 的启发是：

> **不要把所有 PR 都当成 bug fix。不同 PR 类型应该进入不同任务模板、不同 reward、不同 verifier。**

这对做数据管线很重要。一个混杂的 “PR → patch” 数据集，质量通常不如一个带 task taxonomy 的 SWE 数据集。

---

## 4.3 GLM-5：从 repo-level mid-training 到 10K+ 可执行 SWE 环境

GLM-5 在本讲中有两层数据。

第一层是 mid-training 的 software engineering data。它保留把 repo-level code files、commit diffs、GitHub issues、pull requests、relevant source files 拼接成统一训练序列的范式。GLM-5 放宽 repo-level filtering 以扩大候选库，同时强化 issue-level quality filtering；报告称得到约 1000 万 issue–PR pairs，过滤后 issue–PR 部分约 160B unique tokens。([arXiv][5])

第二层是 post-training / agentic RL 的 executable environments。GLM-5 在 Environment Scaling for Agents 中说，为支持 diverse agentic tasks 的 RL，它构造 verifiable executable environments；对 SWE，它先收集真实 Issue-PR pairs，并用 rule-based 与 LLM-based filtering 保证 issue statement 质量，然后按 bug fixing、feature implementation、refactoring 等类别分类。([arXiv][5])

GLM-5 使用基于 RepoLaunch 的环境构建 pipeline，自动分析 repo installation/dependency setup，构建可执行环境，生成 test commands，并用 LLM 生成 language-aware log-parsing functions，从测试输出中提取 F2P 和 P2P tests。最终构造了超过 10K 个 verifiable environments，跨数千个 repo 和 9 种语言，包括 Python、Java、Go、C、C++、JavaScript、TypeScript、PHP 和 Ruby。([arXiv][5])

GLM-5 的特点是：

> **它把 SWE task environment 作为异步 agent RL 基础设施的一部分，而不是单独的数据集。**

这会在第 10、12、13 讲继续出现：当 rollout 很长、环境很多、任务异构时，数据管线和 RL infrastructure 是一体的。

---

## 4.4 DeepSeek-V3.2：real code agent environments + synthetic general agent tasks

DeepSeek-V3.2 在本讲中有两个值得对比的地方。

第一，它把 agentic tasks 明确分成 code agent、search agent、general agent、code interpreter 等类型。表中 code agent 有 24,667 个任务，environment 是 real，prompt 是 extracted；search agent 有 50,275 个任务，environment 是 real，prompt 是 synthesized；general agent 则是 synthetic environment + synthetic prompt。([arXiv][4])

第二，DeepSeek-V3.2 的 code agent pipeline 和 Qwen/MiniMax/Microsoft 很相似：从 GitHub 挖掘数百万 issue-PR pairs，用 heuristic rules 和 LLM judgments 过滤；每个样本要有 reasonable issue description、correlated gold patch 和 test patch；再由 DeepSeek-V3.2 驱动的 environment-setup agent 构建可执行环境，处理 package installation、dependency resolution 和 test execution；测试结果统一输出为 JUnit 格式，便于跨语言和测试框架解析。([arXiv][4])

DeepSeek 的环境成功条件也很明确：gold patch 应用后要有非零 F2P，并且 P2F 为零。最终它构建了数万 reproducible issue-resolution environments，覆盖 Python、Java、JavaScript、TypeScript、C、C++、Go、PHP 等语言。([arXiv][4])

DeepSeek-V3.2 还很值得注意它的 ablation：只在 synthetic general agent tasks 上对 SFT checkpoint 做 RL，可以在 Tau2Bench、MCP-Mark、MCP-Universe 上带来明显提升；相反，只在 code/search 环境做 RL 并不能提升这些 broader agent benchmarks。这说明 code/SWE 任务虽然重要，但如果目标是 general agent，任务合成必须覆盖更广的工具和环境分布。([arXiv][4])

这对我们当前讲的 SWE 数据有一个提醒：

> **SWE 数据是 agentic training 的高质量核心域，但不是 general agent 的全部。**

---

## 4.5 Microsoft MAI-Thinking-1：最完整的 SWE environment quality funnel

Microsoft 的报告在本讲中非常重要，因为它披露了一个非常完整的 SWE environment funnel。

它的 SWE RL problem 被打包成 self-contained container image，包含 specific commit 的 repo、预装依赖、problem statement 和 grading unit tests；rollout 时模型通过 Bash 和 string-replace editor 读写文件、运行命令、浏览 repo；模型完成或达到 turn limit 后，grader 在同一容器里执行测试并产生 verifiable reward。([Microsoft AI][3])

它的环境构造 pipeline 从 1.02 亿 GitHub PR 开始，到 487 万 linked PR，再经过自动环境构建、reference grading signal extraction、环境与 grader 验证、质量过滤和问题重写。最后披露的漏斗结果是：487 万候选问题中，208 万通过自动环境构建，745,452 通过 reference grading signal extraction，265,617 通过 environment and grader verification，覆盖 94,044 个 unique repositories。([Microsoft AI][3])

这个漏斗极其有价值，因为它告诉我们：

```text
raw PR 很多
真正能变成高质量 RL environment 的比例很低
```

Microsoft 还特别强调 reward hacking：即使有可执行测试，SWE environment 仍会被模型钻空子，包括 Internet search 找到 public PR/gold solution、local git history search 找未来 commit、tamper tests 等。它们使用 network access control、清理 future git history、隐藏 test changes、grading 前 reset test files、LLM monitor 和人工审查来缓解这些问题。([Microsoft AI][3])

这对数据构造的启发很直接：

> **SWE environment 的质量不是看 Docker 能不能 build，而是看它是否 clear、deterministic、non-leaky、non-hackable、reward-aligned。**

---

## 4.6 NVIDIA Nemotron 3 Ultra：SWE teacher 视角

NVIDIA 的报告不是主要讲 PR 数据构造，但它很适合从 **teacher training** 角度理解 SWE 任务如何进入 MOPD。

NVIDIA 说 Nemotron 3 Ultra 的 post-training 包括 SFT、跨 reasoning/agentic/code/safety/usability/chat environments 的 unified RLVR，以及超过 10 个 domain-specialized teachers；其中包括 Terminal-use Teacher、SWE Teacher、Search Teacher、Office work Teacher、Agentic Safety Teacher 等，最终通过 MOPD 整合到 Ultra。([NVIDIA][6])

它的 SWE teacher 训练是三阶段：先用 agentic data 对 Ultra base 做 SFT；再在 single-step agentic environments 上做 PivotRL；最后在 end-to-end SWE-RL 阶段，让模型多轮与代码仓库交互，发出 tool 和 bash commands，生成 patch，verifier 运行 hidden tests，并用 binary reward 做 GRPO。NVIDIA 还会对 unfinished trajectories mask loss，对 malformed reasoning/tool calls 给 offending tokens 负 advantage，并处理 gold patch 泄漏。([NVIDIA][6])

NVIDIA 对本讲的启发是：

> **SWE 数据不一定只直接训练最终模型，也可以训练 SWE specialist / SWE teacher，再通过 MOPD 蒸馏到统一模型。**

这点会在第 8 讲和第 11 讲重点展开。

---

## 4.7 Kimi K2：更偏工具合成，但 coding/SWE 仍依赖真实 sandbox

Kimi K2 不是本讲 SWE 数据的主案例，但它提供了一个重要对照：**大规模 agentic data synthesis 不一定都来自 GitHub PR，也可以来自工具库、模拟环境和 real execution sandbox 的混合。**

Kimi K2 的 agentic data synthesis 有三阶段：tool spec generation、agent and task generation、trajectory generation。它先构建真实 MCP tools 和 LLM-synthetic tools 的工具库，然后为 tool-set 生成 agents 和 tasks，再生成多轮 tool-calling trajectories。报告称其抓取 3000+ real MCP tools，并合成 20,000+ synthetic tools。([arXiv][7])

但在 coding/SWE 上，Kimi 仍然回到真实执行。报告说，对于 software engineering tasks，它收集大量 GitHub PRs 和 issues，构建包含 user prompts/issues 和 executable unit tests 的 software development environment；环境建立在 Kubernetes-powered sandbox infrastructure 上，可支持超过 10,000 个并发 sandbox instances。([arXiv][7])

Kimi 的启发是：

> **通用工具使用可以大量合成，但 coding/SWE 这类高真实性任务仍然需要真实代码执行、真实测试和 sandbox。**

---

# 5. 横向对比表

| 报告                       | SWE 数据来源                                                  | 环境构造                                        | Verifier / Reward                                    | 最值得学的点                                                                |
| ------------------------ | --------------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------- |
| Qwen3-Coder-Next         | GitHub PR + 合成 bug + executable seed datasets             | Docker env + verification script + QA agent | fail/pass tests、patch reversion、execution validation | 80 万级 verifiable SWE task、multi-scaffold trajectories、跨 scaffold 泛化问题 |
| MiniMax-M2               | permissive GitHub PR + linked issues                      | agent-synthesized multi-language Docker env | 按 bug/feature/perf/test 类型分别设计 reward                | PR taxonomy、SWE-Test、commit merging、task diversification              |
| GLM-5                    | issue–PR pairs + repo-level files + relevant source files | RepoLaunch-based env setup                  | F2P/P2P extraction、log parsing                       | 10M issue–PR mid-training + 10K+ verifiable SWE env                   |
| DeepSeek-V3.2            | millions of GitHub issue-PR pairs                         | DeepSeek-driven env setup agent             | JUnit output、nonzero F2P、zero P2F                    | code/search/general agent task 分域，真实与合成任务对比                           |
| Microsoft MAI-Thinking-1 | 102M GitHub PR 起步，linked issue 过滤                         | SEE self-contained container                | hidden tests、F2P/P2P、multi-trial validation          | 最完整的 quality funnel、problem rewriting、anti-hacking                    |
| NVIDIA Nemotron 3 Ultra  | agentic SFT + SWE-RL environments                         | repo multi-turn interaction                 | hidden tests + binary GRPO reward                    | SWE teacher → MOPD，SWE 作为 specialist 能力来源                             |
| Kimi K2                  | agentic tool synthesis + GitHub PR/issues for SWE         | Kubernetes sandbox + real execution         | executable unit tests、test pass rates                | simulated tools + real SWE sandbox 的 hybrid data strategy             |

---

# 6. SWE task 的三种数据层次

读这些报告时，要区分三种不同的数据层次。

---

## 6.1 Code pretraining data：学代码语言和知识

例子：

```text
source files
repos
commits
PR diffs
code review text
documentation
```

目标是让模型懂代码、懂 API、懂 repo 结构。

这类数据可以用于 pretraining / mid-training，但它不一定可执行，也不一定有 reward。

Qwen 的 600B repo-level 数据、GLM 的 160B issue–PR tokens、Microsoft 的 public GitHub code pretraining 都属于这一层。([arXiv][1])

---

## 6.2 Supervised SWE edit data：学“问题 → patch”

例子：

```text
problem statement
+ repo context
+ gold diff
```

目标是让模型学会定位和编辑。

这类数据可以用于 SFT，但如果没有环境和 verifier，模型只能模仿 patch，不能从执行反馈中学习。

Qwen 的 PR-based structured software engineering tasks 就处在这一层和下一层之间，因为它包含 problem description、repo context、code edits，并且也会构造 executable tasks。([arXiv][1])

---

## 6.3 Executable SWE RL data：学“环境交互 → 修复成功”

例子：

```text
problem statement
+ repo snapshot
+ hidden tests
+ Docker env
+ tool calls
+ test feedback
+ reward
```

目标是让模型学会像 coding agent 一样行动。

这才是 Qwen、MiniMax、GLM、DeepSeek、Microsoft、NVIDIA 报告里最值得我们关注的核心。

---

# 7. 一个高质量 SWE task 应该满足什么条件？

综合这些报告，我建议把高质量 SWE task 的标准写成 checklist。

## 7.1 任务来源

```text
[ ] 来自真实 issue/PR，或高质量合成 bug
[ ] 有明确 problem statement
[ ] problem statement 不泄漏答案
[ ] problem statement 不过度模糊
[ ] 与 downstream benchmarks 去重
```

## 7.2 Repo 状态

```text
[ ] base commit 可还原
[ ] future commits 被清理
[ ] gold patch 不可见
[ ] hidden tests 不可见
[ ] 依赖可安装
[ ] 环境可重复构建
```

## 7.3 Verifier

```text
[ ] 有 F2P tests
[ ] 有 P2P / regression tests
[ ] P2F 为零或可控
[ ] empty patch fails
[ ] gold patch passes
[ ] 多次运行结果一致
[ ] 测试输出可解析
```

## 7.4 Agent 交互

```text
[ ] 支持 read/edit/run/test
[ ] tool schema 清楚
[ ] timeout 合理
[ ] logging 完整
[ ] 失败原因可区分：model failure / env failure / verifier failure
```

## 7.5 Anti-hacking

```text
[ ] 网络访问受控
[ ] git history 已清理
[ ] test files grading 前 reset
[ ] hidden tests 只在 grading 时应用
[ ] 检测 monkey-patching / test framework tampering
[ ] LLM monitor 或规则检测异常行为
```

Microsoft、NVIDIA 都明确提到网络、git history、hidden tests 和 test tampering 的问题；这说明 reward hacking 不是边缘问题，而是 SWE RL 数据构造的核心问题。([Microsoft AI][3])

---

# 8. 对算法工程师最重要的设计取舍

## 8.1 真实 PR vs 合成 bug

真实 PR 的优点：

```text
真实开发场景
自然问题描述
真实 patch
真实测试
```

缺点：

```text
噪声大
环境难构建
issue 可能模糊
测试覆盖不稳定
答案可能泄漏
```

合成 bug 的优点：

```text
可控
规模大
验证清楚
难度可调
```

缺点：

```text
可能不真实
bug 分布偏 synthetic
模型可能学会合成模式
```

Qwen 两条路线并行，Microsoft 也会复用构建成功但质量不合格的环境来生成 synthetic problems；这说明更合理的策略不是二选一，而是：

```text
真实 PR 提供真实性
合成 bug 提供规模和可控性
```

---

## 8.2 SFT 数据 vs RL 数据

同一个 PR 可以产生两类数据：

```text
SFT:
problem + repo context → gold patch / expert trajectory

RL:
problem + repo env → agent rollout → test reward
```

SFT 更便宜、更稳定，适合冷启动。
RL 更真实、更接近 agent 行为，但成本高、reward 噪声大、容易 hacking。

报告趋势基本一致：先用 SFT / expert / trajectory filtering 建立行为基础，再用 RL/RLVR 提升环境交互能力，最后用 OPD/MOPD 或 consolidation 整合。Microsoft、NVIDIA、DeepSeek 都体现了 specialist → consolidation/distillation 的路线。([Microsoft AI][3])

---

## 8.3 单一 scaffold vs 多 scaffold

Qwen 的结论很值得注意：同 scaffold 内 scaling 效果明显，但跨 scaffold transfer 有限。([arXiv][1])

这意味着如果只用一个 agent framework 采样轨迹，模型可能学到很多 scaffold-specific 行为，比如：

```text
特定 tool call 格式
特定编辑方式
特定终止信号
特定 prompt 风格
特定观察压缩方式
```

所以如果目标是通用 coding agent，数据应覆盖：

```text
SWE-agent style
OpenHands style
Claude-Code style
Terminal-style
search-and-replace editor
git diff editor
bash-heavy workflow
IDE-like workflow
```

这会在第 6 讲详细展开。

---

## 8.4 Hidden tests vs visible tests

如果测试完全可见，模型可能过拟合测试。
如果测试完全 hidden，但 problem statement 太模糊，模型只能猜。

高质量 SWE task 的关键是在两者之间取得平衡：

```text
visible context enough to infer expected behavior
hidden tests enough to verify correctness
regression tests enough to prevent destructive patches
```

Microsoft 的 problem rewriting、F2P/P2P 设计和 hidden test 防篡改就是为了解决这个平衡。([Microsoft AI][3])

---

# 9. 如果自己搭建小规模 SWE 数据管线，应该怎么做？

你不需要一开始复现 10 万级或 100 万级 pipeline。可以先做一个小规模版本。

## Phase 1：选 repo 和 PR

先选：

```text
Python / TypeScript / Go 中一种语言
100–500 个中小型 repo
merged PR
含 issue
含 test change
修改文件数较少
```

优先选择环境容易构建的 repo。不要一开始挑战 Java/C++ 多工具链。

## Phase 2：拆 PR

对每个 PR：

```text
base_commit = PR merge 前状态
gold_patch = code diff
test_patch = test diff
problem_statement = linked issue / PR description
```

## Phase 3：构建 Docker

确保：

```text
docker build 成功
依赖固定
测试命令可运行
无外部网络依赖或有缓存
```

## Phase 4：提取 verifier

至少验证：

```text
base + test_patch → F2P should fail
base + test_patch + gold_patch → F2P should pass
existing tests remain passing
empty patch fails
gold patch passes multiple times
```

## Phase 5：质量过滤

过滤掉：

```text
problem statement 太短
测试非确定
gold patch 不能稳定通过
empty patch 也通过
依赖下载不稳定
任务答案泄漏
```

## Phase 6：生成 trajectories

先用强 agent 或现有 coding agent scaffold 采样：

```text
read files
run tests
edit files
rerun tests
submit patch
```

保留成功轨迹进入 SFT。
失败轨迹不要全丢，可以标记失败原因，后续用于 reward model、debug training 或 process reward。

## Phase 7：进入 RL

当你有：

```text
稳定环境
稳定 verifier
可控 reward
完整 trajectory logs
```

再做 RLVR / GRPO。
不要在环境和 verifier 还不稳定时上 RL，否则模型会学习 reward 噪声。

---

# 10. 本讲总结

第 3 讲需要记住八句话：

1. **coding-agent 训练数据的核心单位是 executable SWE task，不是代码文件。**
2. **GitHub PR 的价值在于它能被还原成 issue、base state、gold patch、test patch 和 verifier。**
3. **F2P/P2P/P2F 是 SWE reward 的核心语言。**
4. **高质量 SWE task 必须同时满足 clear problem statement、reproducible environment、non-leaky repo、deterministic verifier。**
5. **真实 PR 提供真实性，合成 bug 提供规模和可控性；最好混合使用。**
6. **SFT 学 patch 和轨迹，RL 学环境交互和纠错。**
7. **单 scaffold 数据容易过拟合 agent harness，多 scaffold 数据更接近通用 coding agent。**
8. **SWE RL 的第一难点不是 GRPO，而是 task/environment/verifier 数据工程。**

---

# 本讲笔记快照 v3

```text
已讲主题：
- 第 0 讲：agentic post-training 总系统图
- 第 1 讲：agentic capability 定义与能力分层
- 第 2 讲：架构与长上下文为什么会影响 post-training
- 第 3 讲：coding / SWE / repo repair 数据与任务合成

本讲新增关键概念：
- GitHub PR as task source
- base commit / buggy state
- gold patch
- test patch
- hidden tests
- F2P / P2P / P2F
- executable SWE environment
- Docker / sandbox
- verifier script
- problem statement rewriting
- scaffold-specific trajectory
- synthetic bug injection
- SWE-Test conversion
- reward hacking in SWE environments

本讲关键报告定位：
- Qwen3-Coder-Next：PR + 合成 bug，80 万级 verifiable SWE tasks，多 scaffold trajectory
- MiniMax-M2：PR taxonomy、multi-language Docker、task-specific reward、SWE-Test
- GLM-5：10M issue–PR mid-training，10K+ executable SWE env，RepoLaunch pipeline
- DeepSeek-V3.2：real code agent environments，JUnit parsing，nonzero F2P / zero P2F
- Microsoft：最完整 SWE environment funnel，SEE container，quality rewriting，anti-hacking
- NVIDIA：SWE teacher 通过 multi-turn repo interaction + hidden tests + GRPO 训练
- Kimi K2：通用工具合成为主，但 SWE 仍依赖 GitHub PR/issues + real sandbox

下一讲：
- 第 4 讲：数据与任务合成 II——terminal、search、browser、office、slides、workspace
```

下一讲会把视角从 repo repair 扩展出去：**terminal、search、browser、office、slides、workspace 这些 general agent 任务如何构造，为什么它们比 SWE 更难验证，以及各报告如何处理真实环境与合成环境的取舍。**

[1]: https://arxiv.org/html/2603.00729v1?utm_source=chatgpt.com "Qwen3-Coder-Next Technical Report"
[2]: https://arxiv.org/html/2605.26494v1?utm_source=chatgpt.com "The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence"
[3]: https://microsoft.ai/wp-content/uploads/2026/06/main_20260602_2.pdf?utm_source=chatgpt.com "MAI-Thinking-1: Building a Hill-Climbing Machine"
[4]: https://arxiv.org/html/2512.02556v1?utm_source=chatgpt.com "DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models"
[5]: https://arxiv.org/html/2602.15763v1?utm_source=chatgpt.com "GLM-5: from Vibe Coding to Agentic Engineering"
[6]: https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf?utm_source=chatgpt.com "https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf"
[7]: https://arxiv.org/html/2507.20534v1?utm_source=chatgpt.com "Kimi K2: Open Agentic Intelligence"
