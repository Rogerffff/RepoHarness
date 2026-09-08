# I01：slime REALIGN / rewrite 的生产链与上游证据

日期：2026-09-08。角色：Production Tracer；只核查这一个边界，不提出预设修法。未修改实现、未运行 GPU / Docker / 全套测试。

本地基线：`ac0e2e64163fbe49411540e901df439aea16b6b0`。下述五个本地源码文件无工作树差异：`trajectory.py`、`adapters/common.py`、RH2 `bringup.py`、`turn_identity.py`、`generate.py`。已读侧边栏讨论第 1、4、8 轮及关联原文。

## 1. 直接结论

- **“为什么看新输出”有作者说明**：2026-06-12 的提交特意把漂移尾长改成新轮完整输出长度，理由是与 rewrite merge 统一成完整响应长度口径。两个入口实际比较的仍分别是新响应、旧响应，不能据此说两者具有相同训练意义。[提交 36fa60e](https://github.com/THUDM/slime/commit/36fa60e82d20e5853feb617319381ea278b2a932)
- **1024 有早期工程取舍和有限实测记录**，但没有找到当前 REALIGN 规则的阈值消融、最终奖励改善、GLM/Qwen 专属调优证据。旧讨论“没有找到官方实验证据”应收窄成这句话，不能遗漏早期 rewrite 的 20 题结果。详见 §3。
- **设为 0 会关闭这两个销毁点**：token REALIGN 条件永不成立，消息 rewrite merge 直接返回。CLEAN 不变；漂移改为保留独立 Sample。消息树和 Sample 是两层不同结构。
- **vendored 库接口可设 0；当前 RH2 正式启动入口没有把这个参数暴露出来**。RH2 身份导出确实从运行中的 manager 读取同一个阈值；不是一套固定 1024、一套固定 0。
- **#2287 尚未合并**；解决范围是普通线性 Qwen/Claude Code 历史续接。不能声称已经支持合法 compaction / subagent，也不能声称所有非追加历史都会被可靠拒绝。

## 2. 当前主分支与真实可达链

2026-09-08 直接查询 GitHub REST API 的 `commits/main`、`pulls/2005`、`pulls/2287`、`issues/2288`，并读取评论、审查与提交列表：

| 对象 | 本次核得状态 | 固定锚点 |
|---|---|---|
| slime main | 最新提交日期 2026-09-03 | [4c193f1f37509cca70f0e88807a9305b70f63f4e](https://github.com/THUDM/slime/commit/4c193f1f37509cca70f0e88807a9305b70f63f4e) |
| PR #2005 | 已合并，2026-06-17 02:08:30 UTC；66 个提交 | [合并提交 243773cf](https://github.com/THUDM/slime/commit/243773cfdfe6413f1d0d7693b217c9e1d88ecdbc) |
| Issue #2288 | open；0 条评论 | [Issue](https://github.com/THUDM/slime/issues/2288) |
| PR #2287 | open、未合并；2 个提交；0 条评论、0 条审查 | [head 885a09e852e5272d497936370707cc604830f805](https://github.com/THUDM/slime/commit/885a09e852e5272d497936370707cc604830f805) |

RH2 vendor 来源是 `THUDM/slime@e848052a65092ec49e4dd2b5d44d0787c3a327a4`，由 RH2 直接复用，不是通过 miles 再导入一份 agent 实现。[本地来源说明](../../../../../rh2/src/slime/VENDOR_README.md)

本次将 main 原始文件与 vendor 比较：`trajectory.py` **逐字节相同**，SHA256 均为 `6dbb7bec446d81fa0542a4c954d458b4a11edab6776b45a63bc33bca08dd0469`。`adapters/common.py` 整体已有别处变化，但 `BaseAdapter._run_turn` 的 AST 完全相同，均仍逐轮完整渲染历史；不是 append-only 实现。[main trajectory](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/trajectory.py)、[main common](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/adapters/common.py)

真实调用顺序：

1. `BringupService` 建共享 `AnthropicAdapter`；未传 `fork_threshold_tokens`，manager 因而取默认 1024。[bringup.py:887](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L887)
2. 每轮 `_run_turn` 完整渲染客户端历史，再调用 RH2 接管的 `call_sglang_generate`；响应 flush 后才 `record_turn`。**消息 rewrite 在此时发生**。[common.py:341](../../../../../rh2/src/slime/agent/adapters/common.py#L341)、[capture_wire.py:1284](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L1284)
3. 会话结束先 drain 在飞请求，再 `get_trajectory` 遍历消息树、生成 Sample。**token REALIGN/FORK 在此时发生**；它不会倒回去改变已完成的模型请求或工具动作。[common.py:245](../../../../../rh2/src/slime/agent/adapters/common.py#L245)、[trajectory.py:307](../../../../../rh2/src/slime/agent/trajectory.py#L307)
4. RH2 留住树根、读取 `manager._fork_threshold` 和相同截断上限，待 vendor finish 后导出身份 span，再据 span 回填。正式路径将各 Sample 交给 miles 的 canonicalize，保留 fan-out 的列表形状与共同 `rollout_id`。[bringup.py:696](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L696)、[canonicalize.py:691](../../../../../rh2/src/repoharness2/adapters/miles/canonicalize.py#L691)

因此，这两个机制是当前候选生产调用链可达的既有行为；是否触发取决于真实 CC 消息与 token 漂移。本文未测量当前题单上的频率。

## 3. 1024 的历史：能证实什么，不能证实什么

| 历史证据 | 作者记录的理由或结果 | 限制 |
|---|---|---|
| [44e7999d](https://github.com/THUDM/slime/commit/44e7999dfa9beea3000ea0bc62ccbf236f9573df) | 把旧 snapshot 默认值集中到 manager；注释以少量快照开销避免静默丢掉超过约千个 loss token。还删除了示例中另一个硬编码 1000。 | 当时比较的是漂移区域中的可训练 token 数；不是今天的新输出长度条件。 |
| [5e59c254](https://github.com/THUDM/slime/commit/5e59c254e1ef6805db68a5bc239c226956d1d123) | 早期可选 rewrite rescue，作者报告 20 个 SWE 任务、阈值 1024：合并 5 次 rewrite，屏蔽 3164 token，assistant-role forks 从 15 降至 6。 | 作者自报工程观测；未独立复现。不是阈值多档消融，也未报告训练奖励/能力。 |
| [4fcbb241](https://github.com/THUDM/slime/commit/4fcbb24133af33682613d4db653e835fff602f8a) | 默认 1024 的短 assistant 合并，早期动机包含避免 stub leaf 稀释按叶均分的轨迹奖励。 | 现行 `get_trajectory` 已给每个 Sample 全额 reward，旧的奖励均分前提已不成立。 |
| [624b9271](https://github.com/THUDM/slime/commit/624b9271fd4ee4abd2d222189bfd652f23de734e) | 漂移宽容线性化：最近响应内的小漂移尾替换，大漂移或更早漂移 fork；参数改名为 `fork_threshold_tokens`。 | 这时比较对象仍是 drift tail。 |
| [18772b06](https://github.com/THUDM/slime/commit/18772b069a2b752adff29733aa187eec3e544b80) | 把最近旧响应的保留前缀也改成 mask=0；作者用“整响应不再忠实回显”解释整段屏蔽。 | 这是作者的整段处理政策，不是“每个公共前缀 token 都已失去原始采样记录”的证据。 |
| [36fa60e8](https://github.com/THUDM/slime/commit/36fa60e82d20e5853feb617319381ea278b2a932) | 2026-06-12 明确改成新轮完整 `output_ids` 长度，并同步改边界测试，理由是两个入口都用完整响应长度。 | 没给出“为何新输出长度适合决定旧动作保留”的训练实验。 |

#2005 的原始讨论还出现过原样拼接历史 token、历史改写保留旧叶的建议，以及两条追问为何不采用增量 tokenization；本次取到的公开讨论没有后续作者答复。[替代思路评论](https://github.com/THUDM/slime/pull/2005#issuecomment-4618447372)、[增量追问](https://github.com/THUDM/slime/pull/2005#issuecomment-4923616912)

已核到的性能数字还包括公共前缀比较的 chunk 优化、消息 dict 匹配优化；这些测量不属于 1024 的调优证据。不能把源码注释中的短/长解释为经过 GLM 或 Qwen 训练效果验证的阈值。

## 4. threshold=0 的确切效果与 RH2 同源传递

| 入口 | 默认条件与动作 | 0 的效果 |
|---|---|---|
| token `classify_token_drift` | 非 CLEAN；分歧位于最近响应起点或以后；**新输出**长度小于阈值。`_align_to_prompt` 从最近响应起点整体覆盖 token、mask、logprob。 | 非负输出长度不可能小于 0，因此任何实际 token drift 都 FORK。 |
| 消息 `_try_merge_assistant_rewrite` | 不匹配消息是 assistant；挂载点只有一个 assistant 子节点；该节点是生成过的叶；**旧输出**长度小于阈值。随后清掉 `turn` 与 `turn_index`。 | 函数入口 `threshold <= 0` 直接返回，旧生成节点保留，改写历史挂新分支。 |

源码：[REALIGN 条件/覆盖](../../../../../rh2/src/slime/agent/trajectory.py#L169)、[rewrite 条件/销毁](../../../../../rh2/src/slime/agent/trajectory.py#L370)。

**两层 fork 必须分开**：token FORK 在一条已有消息链上拆成多个 Sample，未增加消息树节点；rewrite 不合并才会多出消息树分支。共享生成节点仍由首个遍历到它的叶训练一次，后续叶只作 mask=0 上下文。[拆分与去重](../../../../../rh2/src/slime/agent/trajectory.py#L456)

**可配置性分层**：`BaseAdapter` 的构造器可以接收 `fork_threshold_tokens=0` 并原样交给 manager；该库接口已用 CPU 实例核验。对 `rh2/src`、`rh2/experiments`、`rh2/scripts` 的搜索只发现库定义，没有正式启动侧 CLI / 环境变量传参；直接设置上游示例的 `SLIME_FORK_MERGE_MAX_RESPONSE_TOKENS` 不能让当前 RH2 bringup 生效。[库接口](../../../../../rh2/src/slime/agent/adapters/common.py#L149)、[正式构造位置](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L887)

**身份/回填同源**：`bringup.py:703` 读取真实 manager 阈值，`:733` 传给身份导出。`export_leaf_identity_spans` 直接驱动 vendor `_SampleBuilder`，REALIGN 时删被覆盖 span，rewrite 后 `turn=None` 的节点不参与导出；attach 检查样本数、tokens、mask 全等。backfill 只消费存活身份 span，不能恢复被删除的旧动作。[turn_identity.py:69](../../../../../rh2/src/repoharness2/adapters/slime/turn_identity.py#L69)、[对账](../../../../../rh2/src/repoharness2/adapters/slime/turn_identity.py#L160)、[backfill](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L1350)

0 仅关闭上述两点，不取消 `max_sample_tokens` 截断、空训练响应过滤等既有行为。它不改变当前路径的推理上下文；#2287 改变下一轮真正送给模型的历史 token，二者不是同一种操作。

## 5. #2287 实现边界

固定 head `885a09e852e5272d497936370707cc604830f805` 共修改 5 个文件，**没有修改 trajectory.py**。其开关为示例中的 `SLIME_PRESERVE_REASONING_HISTORY=1`，默认关闭。它保存每 sid 的 `last_turn_ids` 和 `assistant_history`，保留历史 reasoning，将新后缀接在上一轮真实 token 后面。[PR](https://github.com/THUDM/slime/pull/2287)、[固定源码](https://github.com/THUDM/slime/blob/885a09e852e5272d497936370707cc604830f805/slime/agent/adapters/common.py#L140)

具体顺序是：从后向前按 assistant 位置恢复服务端消息 → 渲染**完整历史** → 再渲染截至最新 assistant 的历史 → 验证二者渲染前缀 → 把新后缀接到原始 token。不是只 tokenize 新消息，也未消除完整历史渲染成本。[恢复函数](https://github.com/THUDM/slime/blob/885a09e852e5272d497936370707cc604830f805/slime/agent/adapters/common.py#L107)、[生产调用顺序](https://github.com/THUDM/slime/blob/885a09e852e5272d497936370707cc604830f805/slime/agent/adapters/common.py#L450)

作者报告 Qwen3.5-35B-A3B + Claude Code + TMax 的 8 次 rollout：Sample 64→8，轨迹 token 1,825,684→265,001；128 个 assistant 段保留 reasoning，critic 回放不再发生此前的 CUDA OOM。这是作者自报，未独立复现；不是最终 GRPO 奖励改进，也不能直接换算端到端加速。[实测与明确排除范围](https://github.com/THUDM/slime/issues/2288)

**compaction / subagent 判断**：作者明确将合法压缩、subagent、通用 fan-out、GRPO grouping 排除在本 PR 范围之外。实现没有另建分支身份或压缩段，只有每 sid 一份最近 token 历史：

- 没有回传 assistant 的新压缩上下文会直接抛 `RuntimeError`。
- 有 assistant 时，历史先按位置替换，再做最新 assistant 的可见内容比较；这不足以核验原始客户端消息究竟属于哪条分支。
- 最终 token 前缀检查发生在“原始前缀 + 后缀”的构造之后，只证构造结果；并未对早期 user/tool 内容与上一轮历史做等价检查。

本次隔离执行固定提交中四个已读纯函数，以伪 renderer 做控制流探针：无 assistant 压缩被拒；早期 user 改写被接受；不同 assistant 分支被位置恢复后接受。它仅证明这些 helper 的边界，**不是实际 CC 压缩/并发/subagent 的端到端复现**。所以准确口径是“普通线性续接有代码和作者实验，合法分支/压缩未支持到可声称程度；也不能保证全部不兼容历史都被拒绝”。

## 6. 本地 CPU 核验与剩余未知

已将实际运行的 8 案代码原样保存为 [threshold_probe.py](threshold_probe.py)，重跑输出保存为 [threshold_probe.txt](threshold_probe.txt)。从仓库根目录复现：

```bash
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/threshold_probe.py
```

探针导入真实 vendor manager、`attach_turn_identity_spans`、`backfill_leaf_sample`，无网络推理。构造首轮 prompt `[100,101]`、输出 `[201,202,203,204]`；次轮工具 token 为 300，漂移把 203 改为 999；消息改写案另改 assistant 字典。每轮给独立 capture ID / 版本。8 案均 exit 0，真实身份重放与 backfill 全部对账通过：

| 情况 | 阈值 | 新输出 | 消息树叶 | Sample | mask=1 token | backfill 使用 |
|---|---:|---:|---:|---:|---:|---|
| CLEAN | 1024 | 20 | 1 | 1 | 24 | c1、c2 |
| CLEAN | 0 | 20 | 1 | 1 | 24 | c1、c2 |
| token drift | 1024 | 20 | 1 | 1 | 20 | c2 |
| token drift | 1024 | 1024 | 1 | 2 | 1028 | c1、c2 |
| token drift | 0 | 20 | 1 | 2 | 24 | c1、c2 |
| token drift | 0 | 1024 | 1 | 2 | 1028 | c1、c2 |
| message rewrite | 1024 | 20 | 1 | 1 | 20 | c2 |
| message rewrite | 0 | 20 | 2 | 2 | 24 | c1、c2 |

探针传 `reward=1` 后每个 Sample 均获 1；正式 RH2 也把同一个最终 grader reward 赋给该成员的每个 Sample。**最终 reward 不会把 mask=0 或已删 `TurnRecord` 的直接策略损失补回来**。多 Sample 下的最终权重与 GRPO 归一化需沿 miles 消费端判断，本边界只证明动作覆盖、fan-out 与奖励赋值，不声称阈值 0 与原方案目标完全等价。[现行全额奖励](../../../../../rh2/src/slime/agent/trajectory.py#L319)、[RH2 正式交付](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L4651)

仍未知：当前候选题单上的两类漂移频率、0 与 1024 的重复前缀和显存成本、保留动作后最终奖励/样本效率变化、#2287 对真实 CC 合法上下文变更的完整覆盖。没有这些证据前，不把上游旧实验或本地小例子外推为首训收益结论。
