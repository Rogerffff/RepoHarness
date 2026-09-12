# An Early Preview of SWE-1.6 and Research Update | Cognition

原始来源：https://cognition.com/blog/swe-1-6-preview

采集时间：2026-09-11T09:42:40.145Z。以下为网页正文提取，不是精读报告；交互示例的完整数据另见 states/、embedded/ 与公共 JSON。数学公式优先保留网页自身的 TeX；图片公式请查看图表 PDF。

---

An Early Preview of SWE-1.6 and Research Update | Cognition
Menu
Close
We are sharing an early preview of our ongoing SWE-1.6 training run. Since training SWE 1.5, we have refined our RL recipe and scaled our infrastructure to unlock two orders of magnitude more compute. Our next model SWE-1.6 is post-trained on the same pre-trained model as SWE-1.5 and runs equally as fast at 950 tok/s. The current checkpoint achieves an 11% higher score than SWE-1.5 on SWE-Bench Pro.
Training this model has taught us a lot about how RL can affect the “user experience” of a model. For example, our current checkpoint exhibits behaviors like overthinking and excessive self-verification. This is an active area of research for us - we believe
Model UX
is an important axis that isn’t captured by benchmarks like SWE-Bench Pro.
We are rolling out early access to this model to a small subset of users to collect feedback for tuning model behavior. Our goal for the preview period is to fix rough edges and further push intelligence as we continue training the model!
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/c9417d507221b1aa1541fa7e40e7bbcc60e76a77-1600x975.png?w=1600&fit=max]
Evaluation Details
We chose to evaluate SWE-1.6 on SWE-Bench Pro following
OpenAI’s recommendation
as the spiritual successor of SWE-Bench Verified. Running bug-free and reproducible evaluations for agents requires care. We manually read hundreds of trajectories and cross-checked against Scale-reported
SWE-Bench Pro trajectories
when applicable. Some examples of subtle issues we resolved include: dependency issues in agent and grading environment setup, inconsistent handling of timeouts across harnesses, edge cases in patch collection and application, and out-of-memory during grading. We also double checked there is no overlap in repositories between training tasks & SWE-Bench Pro tasks.
For Claude Opus 4.6 and Sonnet 4.6 we used high reasoning effort and reported the best result from runs across three harnesses: Claude Code, Cascade (Windsurf), and Devin. Anthropic did not report SWE-Bench Pro results for Opus 4.6 and Sonnet 4.6. For Claude Opus 4.5 we used Anthropic’s officially reported results for the 64k thinking setting. For GPT-5.3-Codex and GPT-5.3-Codex-Spark we used OpenAI’s reported results (
Codex
,
Codex Spark
). We attempted to replicate GPT-5.3-Codex results on three harnesses (Codex CLI, Cascade, and Devin) but obtained a slightly worse measurement (54.0% best). For GLM-5 and Kimi K2.5 we report the best result of two harnesses (Cascade and Devin). We ran Composer-1.5 under the Cursor CLI and did multiple iterations of spot checking and re-runs towards ensuring that we report a fair measurement. For SWE-1.6-Preview and SWE-1.5 we evaluated on the Cascade harness with the same system prompt and settings as in the Windsurf product.
Scaling RL
Since our early attempts at agentic RL, including Kevin-32B and SWE-grep, we have continued to refine our algorithm for stable training. We have significantly scaled the number of RL environments while further improving data quality. As a consequence, we observe continued improvements as we train for more steps.
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/897206eb8b18422b08f07dcbbcfc08e32b82390d-1600x846.png?w=1600&fit=max]
It has been fun to observe the model learning to think harder and iterate for more turns on hard SWE-Bench Pro problems. On the flip side, we observe overthinking and excessive self-verification in our own dogfooding. Figuring out the right balance between interactivity and long-horizon thinking is an active area of research.
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/7f030c4b78f02a27645ffca09d06b9330e3a1bb4-1600x846.png?w=1600&fit=max]
How we made our training 6x faster
Our philosophy is: first get it working, then make it fast. Since SWE-1.5, through a variety of improvements, our training stack is more stable, and training steps for SWE-1.6 now run 6x faster than they did 3 months ago (normalizing for batch size).
Rollouts on long-horizon software engineering tasks often require tens or hundreds of turns interacting with the environment. With this profile in mind, we’ve made several choices that improved our rollout throughput.
First, we’ve optimized our inference configurations, in particular using lower precision. However, this introduces issues like high mismatch between training and inference logprobs. We’ve made algorithmic improvements that enabled us to use rollouts in precisions as low as NVFP4, which is a numeric format optimized for
Blackwell chips
, and achieved 2-3x higher throughput than with BF16 or FP8.
As multi-turn rollouts are made up of serial requests that share prefixes, we tag each rollout with a corresponding DP rank ID and route that rollout’s requests to the specified rank, maximizing KV cache hit rate and maintaining balanced workloads across DP ranks.
Finally, we’ve significantly improved the stability and performance of our training infrastructure. SWE-1.6 was trained on thousands of GB200 NVL72 chips, requiring attention to stable networking. Moreover, we were able to accelerate our training by 1.5x using NVIDIA’s Multi-Node NVLink.
GPUs Allocation and Staleness
In async RL we can think of the system as a two-stage pipeline:
An inference/rollout stage that generates samples (trajectories).
A training stage that consumes those samples and runs one optimizer step whenever
B
samples are ready.
In steady state, rollouts and training overlap, and the wall-clock time per optimizer step is set by whichever stage is slower. If inference produces samples faster than training can consume them, the sample queue grows without bound. If training is faster, then the trainer sits idle waiting for samples. A good first guess for the optimal GPU split is therefore the one that balances the two stages.
Thanks to our algorithmic improvements, we can neglect staleness (the number of optimizer steps between when a rollout starts and when its samples are consumed by training) when choosing the GPU split. We also ignore the time to refresh and broadcast the updated weights to inference engines, assuming it’s negligible compared to rollout generation and the training step (or amortized asynchronously).
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/3e18f64ecf9696b066b3bb3b3ec74c0744bc9567-1600x602.png?w=1600&fit=max]
Given these assumptions, we can use the following simple model to produce a first guess for the inference/training allocation. Suppose that:
We have
N
total GPUs, split into
nᵢ
inference GPUs and
nₜ
training GPUs,
Each optimizer step consumes
B
samples,
The inference engines sustain
s_roll
output tokens/sec/GPU at saturation (measured end-to-end, including prefill),
r
denotes the output-to-input token ratio,
L_out
is the average number of output tokens per trajectory,
The trainer runs at
s_train
tokens/sec/GPU for the update workload.
One practical detail is that we parameterize inference cost using (1) the measured
output tokens/sec
on the inference engines, and (2) the average
output/input token ratio
. This works well in our setup because we do not re-prefill the entire history at each turn, so the “input tokens” we pay are primarily the newly appended prompt tokens. We enable this by “sticking” each trajectory to an inference engine, which can then keep the trajectory’s
KV cache
resident across turns. As a result, the end-to-end measured output throughput (
s_roll
) already reflects the real prefill+decode cost, and
r = in/out
can be interpreted as the ratio of newly-prefilled tokens to generated tokens along the rollout.
From r, the number of total tokens per trajectory is
L_tot = L_out + L_in = L_out⋅(1+r)
. Rollouts for a turn generate
B⋅L_out
output tokens in total. With nᵢ inference GPUs producing output at total rate
nᵢ⋅s_roll
:
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/5e430c03a2194aeb8c2f8a512e72052d7edeb57a-2956x408.png?w=1600&fit=max]
Training does work proportional to
B⋅L_tot
tokens. With
nₜ
GPUs at
s_train
effective tokens/sec/GPU:
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/67c8c9edfb11896898e5491bdfb4a763dc0285f1-2934x444.png?w=1600&fit=max]
Because rollout generation and training overlap, the steady-state step time is approximately
t_step ≈ max(t_roll, t_train)
. To minimize step time, we want
t_roll ≈ t_train
. Setting them equal cancels
B
and
L_out
, and we can solve for the training allocation:
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/d29e12b3338b09f6155645b5a7b8cdb184b6dd19-2950x416.png?w=1600&fit=max]
In our system each inference rank runs an optimal fixed concurrency
c
(the number of in-flight rollouts per engine). Each optimizer step consumes
B
samples, so a natural equilibrium estimate for step-based staleness is
≈ c⋅n_i/B
. Plugging in the equilibrium allocation for
nᵢ
yields an explicit expression in terms of the same measured throughputs.
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/e607c6caa174199c77a75bb269f06daaf0f2ffaa-3022x436.png?w=1600&fit=max]
The missing axis: Model UX
The industry has
moved
to benchmarks like SWE-Bench Pro, which is more difficult, less contaminated, and more representative of ability to solve longer horizon tasks compared to previous SWE benchmarks. Through large-scale RL, SWE-1.6 has improved significantly on that benchmark over SWE-1.5. Qualitatively, we’ve noticed that SWE-1.6 thinks for longer and takes more turns, especially for harder queries.
However, one axis these benchmarks don’t measure is “Model UX”. We’ve previously discussed some of these ideas in the “Semi-Async Valley of Death” in our SWE-grep and SWE-1.5
blog post
. Back then, we optimized for the interactive side of the software engineering experience, focusing on speed.
Windsurf Arena mode was a first step towards this, by measuring blind subjective preference on real coding tasks. SWE-1.5 performed better than we expected here, which we largely attribute to its speed.
[原网页图片：An Early Preview of SWE-1.6 and Research Update；地址：https://cdn.sanity.io/images/2mc9cv2v/production/4ffeee4beff9cf794ee91b9bdf24ebad7fbd374d-1600x757.png?w=1600&fit=max]
However, this ranking misses some critical details. Now that background agents are attaining wider adoption, we believe the following aspects of model UX will matter even more:
Ability to infer intent from incomplete context
Visibility of chain of thought, commands being run, or todo list
Tool call efficiency and non-invasiveness
Adaptive thinking
Instruction following over multiple turns
We notice that large-scale reinforcement learning can improve the model’s intelligence and incentivize it to think for longer, but can come at a tradeoff by introducing undesirable behaviors.
For example, we noticed that SWE-1.6 Preview learns to use bash commands for search instead of pre-defined tools because terminal commands are more expressive and allow it to solve the task faster. But complex commands give less visibility into the model’s problem solving trajectory. Excessive use of commands is also annoying for the user, who has to manually approve each command every 10-20 seconds or so over a very long horizon, when they might otherwise have switched to a different task already.
We were able to address many undesirable behaviors from SWE-1.5. Now our model:
Avoids writing unnecessary unit tests and documentation
Uses todo lists to track progress for long-running tasks
Adopts a professional tone and keeps answers concise and clear
Explores the codebase, gathers context, and reasons before jumping into coding
However, we think that large-scale RL has introduced undesirable behaviors:
Overthinking / reasoning in loops / excessive self-verification
High number of turns
Executing long-running commands synchronously instead of in the background
Using sequential tool calls when they could’ve been run in parallel
We aim to improve these behaviors in our next training runs, and we’re excited to do more research around ways to improve UX in general through model training.
Extra credit: We want to highlight some members of our contractor team who have made outsized contributions to data & tooling: Claudio Costa, Martin McKeaveney, Lance Fuchia, Tomer Nosrati, Merlijn Vos.
04. Articles
Articles
[原网页图片：Estimating the Productivity of an Autonomous AI Software Engineer；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F8527b7c1b2b03f309d7ba9189296ac76a1c7b650-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
Estimating the Productivity of an Autonomous AI Software Engineer
06.04.26
[原网页图片：AI should earn its keep: Introducing the AI Productivity Guarantee；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2Fd378ef146ec6070438bfaeab4d9e47e8b886e55d-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
AI should earn its keep: Introducing the AI Productivity Guarantee
06.04.26
[原网页图片：Introducing Devin Desktop；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F5841a7932386c05dc112f92fda8ff519b38d4f9a-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
Introducing Devin Desktop
06.02.26
[原网页图片：More Devins in More Places；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F58309361c06f31fa49f8c36e307963f21bd3f22b-1382x777.jpg%3Frect%3D1%2C0%2C1381%2C777%26w%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
More Devins in More Places
05.27.26
[原网页图片：Devin in Windsurf；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F89fcacf48d33b51277268808596d123237018950-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
Devin in Windsurf
04.15.26
[原网页图片：How Cognition Uses Devin to Build Devin；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2Fc1e05d959a8c25c8df5e86198a4213e4fd634b61-1500x844.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
How Cognition Uses Devin to Build Devin
02.27.26
[原网页图片：Introducing Cognition for Government；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F164f27869605d7c326a68e511efcf1a4077fc2b7-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
Introducing Cognition for Government
02.25.26
[原网页图片：Introducing Devin 2.2；地址：/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F2mc9cv2v%2Fproduction%2F5638cfd0a8a65ad3074019b69c3aa05e112577b7-1920x1080.jpg%3Fw%3D640%26h%3D360%26fit%3Dcrop&w=1920&q=75]
Introducing Devin 2.2
02.24.26
[原网页图片：；地址：https://www.facebook.com/tr?id=1228809948990597&ev=PageView&noscript=1]
