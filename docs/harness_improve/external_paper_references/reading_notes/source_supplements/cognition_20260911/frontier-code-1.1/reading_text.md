# FrontierCode 1.1 | Cognition

原始来源：https://cognition.com/blog/frontier-code-1.1

采集时间：2026-09-11T09:47:51.919Z。以下为网页正文提取，不是精读报告；交互示例的完整数据另见 states/、embedded/ 与公共 JSON。数学公式优先保留网页自身的 TeX；图片公式请查看图表 PDF。

---

FrontierCode 1.1 | Cognition
Menu
Close
FrontierCode Leaderboard
Benchmarks for how well models meet the standards of high-quality production codebases
View Now
→
One month ago, we introduced FrontierCode
1
, an eval designed to measure not just code correctness, but also code quality. Today, we are releasing a refined version,
FrontierCode 1.1
, with the following improvements:
Fair internet use.
We refined our methodology to capture the nuance between legitimate internet use (e.g., looking up documentation) and unfair use (anything that could reveal a task's solution).
Fairer grading.
We audited all 1000+ grading criteria and relaxed 75 overly strict ones that could unfairly penalize valid solutions.
New model scores.
We are releasing scores for Sonnet 5 and updated scores for Fable 5.
Going forward, we'll be reporting scores on the Main and Extended subsets of FrontierCode, evaluated with the 1.1 methodology. We are no longer reporting the Diamond subset; we elaborate on this below.
Results
#
0
20
40
60
80
100
Score (%)
24.3
Claude
Sonnet 4.6
26.9
Claude Opus
4.6
27.0
GPT-5.4-mini
38.5
Claude Opus
4.7
42.7
Claude
Sonnet 5
43.0
GPT-5.5
46.5
Claude Opus
4.8
53.5
Claude Fable
5
FrontierCode 1.1 Main
Score
vs
Output Tokens
0
20k
40k
60k
80k
100k
120k
140k
avg output tokens per rollout
10
20
30
40
50
Score (%)
Fable 5
Opus 4.8
GPT-5.5
Sonnet 5
Opus 4.7
GPT-5.4-mini
Opus 4.6
Sonnet 4.6
Score
: a weighted aggregate of the rubric items. Solutions that don’t pass blocking criteria receive 0.
Output tokens
: the mean number of tokens a model generated per rollout.
Select dataset
Extended
150
Main
100
Main: the standard 100-task benchmark. Excludes the easy tasks.
We present the results on FrontierCode 1.1 Main above. While the FrontierCode 1.1 methodology leads to some changes in absolute scores, the relative performances of the models we evaluated did not substantially change compared to 1.0.
In the rest of this blog post, we detail our improved methodology for proper internet use.
Getting Internet Use Right
#
FrontierCode tasks are sourced from real PRs in open-source codebases. This produces a realistic task distribution, but it also means that task solutions may exist somewhere on the public internet, such as in a later version of the upstream repository, in its many mirrors, or even in package registries (an agent can sometimes obtain the fix simply by installing the latest release). An agent with internet access can therefore sometimes shortcut a task by looking up the answer instead of solving it.
When designing FrontierCode 1.0, we found a few instances of agents finding the upstream codebase, but occurrences were rare enough that we felt they did not warrant an explicit correction or methodology change. However, the latest models such as Fable 5 are increasingly skilled at retrieving information online, and the rate of unfair internet use is rising accordingly. Without any instructions to the contrary, finding an existing fix is a natural strategy for a capable agent. We expect this trend to continue with future models.
0
20
40
60
80
100
Unfair internet use rate (%)
0.5
Claude Opus
4.6
0.7
Claude
Sonnet 4.6
3.8
GPT-5.5
4.0
Claude Opus
4.7
7.6
GPT-5.4-mini
9.4
Claude Opus
4.8
26.2
Claude
Sonnet 5
37.2
Claude Fable
5
Select dataset
Extended
150
Main
100
Main: the standard 100-task benchmark. Excludes the easy tasks.
Why not just turn the internet off?
Unfair internet use is an increasingly common issue in SWE evals
2
,
3
,
4
,
5
, and the usual fix is to disable internet access entirely. But a blanket ban has two serious problems:
Several FrontierCode tasks require internet access by design, for example, to look up API contracts. This reflects real-world software engineering and was an explicit goal of the benchmark.
Even for tasks that don't require it, frontier models are increasingly trained to use search as a core part of their reasoning and context-gathering workflow. Disabling internet access removes this capability and can cause benchmarks to understate true model performance.
For these reasons, FrontierCode did not (and still does not) disallow internet use. Instead, FrontierCode 1.1 aims to eliminate unfair internet use while preserving the realism that internet access provides.
Our approach: define fair internet use, then verify
We found that the latest models are sufficiently well-aligned that simply telling them which kinds of internet access are allowed (e.g. looking up documentation) versus disallowed (anything that could shortcut the task) almost entirely eliminates unfair internet use, while still permitting fair internet use. Adherence to the prompt is remarkably good: with it in place, unfair internet use rates fall below 1% for every model we evaluated.
FrontierCode 1.1 implements this as two safeguards: a prompt that explains what fair internet use is, and a classical verifier that detects unfair internet use and zeroes out those runs. The prompt alone is currently sufficient to essentially eliminate unfair internet use; the verifier confirms this and will catch any future deviations.
Safeguard 1: a "fair internet use" prompt
that clearly distinguishes allowed from disallowed internet use.
View the fair-internet-use prompt
Hide
You may use the internet to look up general information that helps you reason about the task, such as documentation, API references, language/library behavior, error semantics, standards, examples of intended usage, and background concepts.

You must not search for, open, fetch, view, or copy anything that could reveal the task's reference solution or upstream patch. This includes the upstream repository, mirrors, forks, issues, pull requests, commits, branches, diffs, release notes, changelogs, CI logs, mailing-list discussions, copied patches, pages summarizing the fix, queries likely to find the exact bug/issue/commit/PR/patch, or any other source discussing the specific bug or solution.

Rule of thumb: if a web search has a meaningful chance of trivializing the task by revealing the bug report, fix, patch, implementation strategy, or reference solution, do not perform that search. Prefer searches for general concepts, APIs, error semantics, language/library behavior, intended usage, or documentation that help you reason without revealing the specific solution.
We provide two illustrative examples of models’ internet use below:
Flagged: opened the PR diff
Allowed: read the docs
The model can search the web freely, but the scanner flags the run the moment it opens the upstream PR diff page.
task: Ellipsis on long emails
0/14
Scroll into view to watch the agent work…
Interactive: watch the agent work in real time. Routine steps play fast; the scanner slows down on the moment the run is flagged, when the model opens the upstream PR diff page.
Safeguard 2: programmatic detection.
We flag references to source pull requests, upstream patches or files, and potentially solution-bearing mirrors or vendored copies. To penalize unfair internet use, flagged runs receive a score of zero.
Together, these safeguards eliminate essentially all unfair internet use while still allowing fair use. Agents continue to look up documentation, API references, and background concepts as they would on a real task. We believe this combination of eliminating unfair internet use while preserving realism makes FrontierCode 1.1 a more accurate measurement of real model capabilities.
Alternatives we considered
Before settling on these safeguards, we also considered enforcing fair internet use with a blocklist or allowlist of particular sites. Unfair internet use falls into two main categories: GitHub (and its many mirrors) and package registries (where agents will often just run
npm install
to pull the latest release that already contains the solution).
Blocklisting turned out to be impractical. Over several iterations of blocking domains and inspecting agent trajectories, our blocklist grew to roughly 1,200 domains, and agents kept finding new workarounds, sometimes spending 20+ turns fighting the blocklist before solving the task themselves. Blocking sites also breaks honest workflows, since sites like GitHub are sometimes legitimately required to complete a task.
Allowlisting has the inverse problem: it requires anticipating every site an agent might legitimately need and building a custom allowlist per task, which doesn't scale. It also distorts agent behavior either way: if the allowlist is visible to the agent, it steers the agent toward the listed sites; if it is hidden, the agent either concludes the internet is broken or wastes effort probing which sites are reachable. Neither reflects how agents use the internet in practice.
In the end, clearly defining fair use and verifying compliance proved simpler and more robust than any form of network-level enforcement.
Refined blocker criteria
#
FrontierCode grades each task against a set of reviewer-defined criteria, some of which are designated as
blockers
: requirements so central to the task that failing one caps the score for that run, much like a change requested in a real code review. For FrontierCode 1.1, we audited all 1000+ blocker criteria across FrontierCode and manually reviewed flagged criteria. We found 75 blockers that were overly strict, and we have since demoted them to non-blocker status. We expect this to substantially reduce the occurrence of false negatives in grading.
Deprecating FrontierCode Diamond
#
As described in our original blog post
1
, Diamond consists of the 50 hardest tasks in our full 150-task Extended set, while Main consists of the 100 hardest. With the FrontierCode 1.1 updates, the Diamond set no longer reflects the 50 hardest tasks. Moreover, because the solve rates of the hardest tasks are so low, we have determined that Diamond performance is inherently noisy. As a result, we are deprecating the Diamond set and will rely on Main and Extended going forward.
References
#
[1]
Cognition, "Introducing FrontierCode," 2026.
cognition.com/blog/frontier-code
[2]
METR, "Summary of METR's predeployment evaluation of GPT-5.6 Sol," June 26, 2026.
metr.org/blog/2026-06-26-gpt-5-6-sol
[3]
Naman Jain, "Reward hacking is swamping model intelligence gains," June 25, 2026.
cursor.com/blog/reward-hacking-coding-benchmarks
[4]
Datacurve, "DeepSWE v1.1 — A revision of DeepSWE v1," July 2026.
deepswe.datacurve.ai/blog/deepswe-v1-1
[5]
Posttrain, "Clean Coding Index," 2026.
coding-index.posttrain.dev
Acknowledgments
Research
Eric Lu, Ben Pan, Fermi Ma, Alex Lombardi, Deniz Birlikci, Sam Lee, Ray Wang, Rohan Choudhury, TC Qin, Carlo Baronio, Jacob Teo, Joon Hee Lee, Silas Alberti
Design
Katie Cheng, Joseph Alessio
Contributors
Jeffrey Ling, Walden Yan
37.2
[原网页图片：；地址：https://www.facebook.com/tr?id=1228809948990597&ev=PageView&noscript=1]
