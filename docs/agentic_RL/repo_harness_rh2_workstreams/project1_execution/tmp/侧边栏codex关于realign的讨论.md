# 侧边栏 Codex 关于 REALIGN 的讨论

> 整理日期：2026-09-08。用途：将侧边栏会话移交给其他分支继续讨论。
>
> 本文是保留讨论过程的整理稿，不是新的实现定案或完整审计报告。保留八轮实质性回答及全部例子、数值和限制；补回复制时遗漏的六条注释追问，移除时间戳、耗时和工具状态等界面元素，恢复表格、代码块和来源链接。用户问题仅整理空格、标点和术语写法。
>
> “截至今天”“当前”“本次核对”等表述均指原讨论时点 2026-09-08，不代表之后的上游状态。原回答中的“没有改文件”等描述属于当时的只读调查；此次整理只修改本讨论文档。完整工具调用日志未收录，不能把本文当作平台原始会话导出。

## 阅读导航

- [第 1 轮：上游现状、机制来源与相关文档](#discussion-1)
- [第 2 轮：两轮例子：原始采样记录如何在 REALIGN 后失去直接训练信号](#discussion-2)
- [第 3 轮：保留公共前缀是否合理，以及 P3 是否记录过覆盖损失](#discussion-3)
- [第 4 轮：1024 阈值究竟比较什么](#discussion-4)
- [第 5 轮：“最近一次响应区域”的位置条件](#discussion-5)
- [第 6 轮：纠正时间线：实时捕获与事后组装](#discussion-6)
- [第 7 轮：四轮完整例子：从请求、消息树到两个 Sample](#discussion-7)
- [第 8 轮：Issue、追加式 token 历史、PR 实现与 verl 对照](#discussion-8)
- [完整性核对与待继续讨论的问题](#handoff)

## 接手时先明确的结论与修正

- 每轮实时重新渲染输入、采样并调用 record_turn；token CLEAN / REALIGN / FORK 在 session 收尾的样本组装循环中判定。消息层 rewrite merge 则已经发生在 record_turn 阶段。
- token REALIGN 的 1024 比较对象是当前遍历轮的 output_ids 长度；消息 rewrite merge 使用同一配置，但判断的是被改写旧响应的长度。这两个分支不要混用。
- “保留 token 的采样来源正确”与“所有生成动作都保留直接训练信号”不是同一个保证。mask=0 指没有该位置的直接策略损失，不等于上下文对后续计算完全没有作用。
- P3 归档显示捕获记录与训练投影存在覆盖差异；32/50 不能称为 REALIGN 发生率，也不能当作最终成功训练批次的比例。
- 没有找到默认 1024 的官方训练调优证据，不能推断它针对 GLM 调优。
- PR #2287 保持原始 token 前缀，但当前实现仍通过完整历史渲染和截至 assistant 的渲染来定位后缀，不等于已经实现纯增量分词。
- 追加式历史会改变后续模型实际看到的上下文。保留历史 reasoning、合法压缩、分支、训练与测评一致性仍须讨论；尚未批准迁移 PR、修改阈值或改变训练语义。

## 问题入口：最初选中文本的背景（整理时补回）

以下是进入侧边栏时引用的问题摘要，属于当时主线程的描述；本次文档整理没有重新运行这些 tokenizer 探针，也不把它们升级为新的独立验证结论。

消息重渲染可能使前序轮整轮失去直接训练信号。Claude Code 每轮回传历史，adapter 翻译后重新 apply chat template；reminder 的消息组织、历史 thinking 处理或工具参数序列化都可能使历史 token 与原始采样不同。REALIGN 会把最近旧响应区域改为上下文，另一条 rewrite merge 路径还会清除旧节点的生成记录。

最初引用的两轮 CPU 探针结果为：

| 情况 | 两轮生成 token 数 | 最终直接训练 token 数 |
| --- | --- | --- |
| 普通工具往返 | 27 + 2 | 29 |
| 加入特定 reminder | 27 + 2 | 2 |
| 首轮较长，再加入 reminder | 1125 + 2 | 2 |
| 同类漂移，但新输出达到 1024 token | 27 + 1024 | 1051，拆成两条训练输出；原摘要称为“两条叶” |

这里沿用原摘要的数值，但不把“两条叶”解释为消息树必然增加叶节点。第 7 轮会具体区分消息树的叶、builder 和最终 Sample。

该摘要同时指出：“所有多轮必丢首轮”不成立，普通工具往返有正常对照；“只改 clear_thinking=False 就好”也不能直接成立，所检查模板不读取该开关。精确消息与 tokenizer 的触发条件需要对应真实请求核实。以下八轮讨论是在这个问题入口上展开的。


<a id="discussion-1"></a>

## 第 1 轮：上游现状、机制来源与相关文档

**用户问题**

> 现在这个问题是 miles 本身的机制设计，应该是 fork 延续了 slime。我们先看一下当前 slime 这里的逻辑：是否有 slime 官方远程仓库的更新，以及相关文档？是否有对这个部分的说明？

**Codex 回答**

有明确说明，也有直接相关的新 PR；但截至今天，slime 主分支仍保留这套丢弃旧轮信号的机制，尚未合入相关替代方案。

这次只做了远程查询和内存中的文件比较，没有 fetch/pull、改文件或运行测试。

先纠正一下来源：在我们项目里，这段不是“通过 miles 间接继承”，而是直接复制了 slime 的 agent 层。本地 [VENDOR_README.md](../../../../../rh2/src/slime/VENDOR_README.md) 记录来源为 THUDM/slime@e848052a，2026 年 7 月 5 日版本；换成 miles 后，仍使用这份 TrajectoryManager。

### 1．官方主分支有更新，但这份轨迹实现没有更新。

我查询到的 slime main 为：

- 提交：4c193f1f
- 日期：2026-09-03
- 最近改动：超时 SGLang 请求通过 router workers 进行 abort，属于另一处生命周期修复。[最新提交](https://github.com/THUDM/slime/commit/4c193f1f37509cca70f0e88807a9305b70f63f4e)

关键结果是：当前远程 slime/agent/trajectory.py 与我们 vendored 文件逐字节相同。 该文件最近一次修改为 7 月 2 日，早于我们的 pin。因此，单纯升级到当前 slime main，不会改变这里的 REALIGN/rewrite merge 行为。[当前固定版本源码](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/trajectory.py)

### 2．官方确实说明了：这是主动选择的取舍，不是无意写错 mask。

最直接的文档是官方示例 README 中的 “String-in, Token-out Trajectories”。它解释：

- 每轮将消息历史重新渲染成 token；
- 保存 SGLang 实际生成的 token 和 logprob；
- 后续历史发生 token 漂移时，不能继续把重渲染内容当作原始采样动作训练；
- 因而保留继续执行所需的上下文，同时屏蔽相应旧响应的 loss。[官方 README 对应章节](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/examples/coding_agent_rl/README.md#string-in-token-out-trajectories)

这套结构来自已合并的 [PR #2005](https://github.com/THUDM/slime/pull/2005)，2026 年 6 月 17 日合入，将旧的分段实现改为每个 session 的消息树，并明确引入通过 fork/replace 处理重新 tokenize 的漂移。

源码和测试还把具体策略写得很清楚：

| 情况 | 官方当前行为 |
| --- | --- |
| 新 prompt 精确延续旧 token | CLEAN，继续拼接 |
| 漂移发生在最近响应区域，且新响应短于阈值 | REALIGN，把最近旧响应整段改为 mask=0 的上下文 |
| 漂移更早，或新响应达到阈值 | FORK，保留原训练行，再开启新行 |
| 客户端改写了一个满足条件的短 assistant 叶节点 | rewrite merge，删除该节点的生成记录，只保留路由作用 |

特别是 _try_merge_assistant_rewrite 的说明，明确承认：合并会不可逆地销毁生成记录；保留较长旧响应单独训练，被认为更值得，而短响应被吸收以减少分支。[rewrite merge 说明](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/trajectory.py#L370)

1024 阈值看新输出，也不是我们误读。 官方测试明确验证：新输出长度等于阈值就 fork，小于阈值就替换并屏蔽整段旧响应；漂移尾部长度本身不参与这个阈值判断。但我没有在这些说明中找到“为什么用新输出长度、为什么默认 1024”的实验依据。[阈值测试](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/tests/test_agent/test_trajectory_manager_branching.py#L1218)

### 3．上游已有几乎正对我们问题的 Qwen/Claude Code PR，但尚未合并。

[Issue #2288](https://github.com/THUDM/slime/issues/2288) 和 [PR #2287](https://github.com/THUDM/slime/pull/2287) 讨论的正是：

- Qwen 历史 thinking 被模板移除；
- Claude Code 回传时规范化文本、空白和工具参数；
- 重新渲染导致普通连续交互被误拆成多个训练 Sample。

[PR #2287](https://github.com/THUDM/slime/pull/2287) 当前为 open、未合并。它提出的方案包含：

1. 使用保留历史 reasoning 的 Qwen 模板变体；
2. 服务端保存精确的历史 prompt_ids + output_ids；
3. 使用服务端保存的 assistant 内容恢复客户端回传历史；
4. 将新观察和下一轮生成前缀接到原始 token 历史之后；
5. 对不符合 append-only 条件的情况显式报错。

作者报告了一次真实 Qwen3.5＋Claude Code 实验：

| 指标 | 修改前 | 修改后 |
| --- | --- | --- |
| 环境 rollout | 8 | 8 |
| 训练 Sample | 64 | 8 |
| 总轨迹 token | 1,825,684 | 265,001 |

这些是 PR 作者报告的结果，我未独立复现。它主要处理意外分叉和历史重渲染，不足以证明已经覆盖我们的子 agent、合法压缩、并发请求及 R3 语义。

### 4．还有一个性能 PR，但它不会修复旧轮 loss 丢失。

[Issue #2285](https://github.com/THUDM/slime/issues/2285) 讨论每轮同步处理完整历史带来的 CPU 和事件循环成本，对应 [PR #2328](https://github.com/THUDM/slime/pull/2328)，目前同样未合并。

它把完整历史渲染移入有界工作线程，并增加延迟、排队、取消等指标。它刻意保持相同 prompt token 和现有轨迹语义，因此解决的是事件循环阻塞，不是 REALIGN 屏蔽旧动作，也不消除累计完整历史 tokenize 的成本。

对于我们原先的判断，我会这样进一步说准确：

slime 有意保证“保留下来训练的 token 不冒用错误的采样来源”，但并不保证“所有真实生成的动作都保留下来训练”。

前一个目标合理；后一个覆盖缺口仍然存在。

例如旧响应实际采样为 A，客户端回传后变成 B：不能把 A 的 logprob 直接贴给 B。但这不意味着必须删除 A 的训练机会——可以保留原始条件下的 A 为独立训练行，再让后续响应以 B 为上下文。这正是 fork 路线能够表达的事情，代价是更多训练行和重复前缀计算。

所以，我们接下来要审的是这项取舍是否适合自己的真实 CC 轨迹，而不是先把它当成上游无意写错的实现。 最值得继续对照的两项是：当前实现已有的 fork_threshold_tokens=0 行为，以及未合并的 #2287 如何保持历史。前者影响样本表示，后者改变后续模型实际看到的上下文，不能视为同一种修法。

<a id="discussion-2"></a>

## 第 2 轮：两轮例子：原始采样记录如何在 REALIGN 后失去直接训练信号

**用户追问（原注释，整理时补回）**

> 这里首先帮我回顾一下当前的 slime 的机制，这里是 REALIGN 在什么情况下发生，用一个例子为我展示一下。类似首先第一轮输入 prompt，apply template 然后变成 token 进 SGLang，然后返回输出 token，然后在哪里记录，并传回 Claude Code，然后下一轮重新 apply template 的这个过程。然后触发了 REALIGN 出现了什么问题，用例子说明你认为现在官方这样实现为什么你觉得有问题。

**Codex 回答**

可以。这里先抓住一个关键区别：slime 每轮确实记录了原始采样 token，但这些 token 在最终组装训练样本时，仍可能被移出 loss。

而且，REALIGN 发生在结束时组装训练样本的阶段，不是在第二轮调用 SGLang 前修正输入。 下面按官方当前代码走一个完整例子。

### 第一步：Claude Code 发起第一轮请求。

假设任务是“修复仓库中的一个函数”。Claude Code 发给 adapter 的是结构化消息：

```text
system：工具说明、行为要求
user：修复这个函数……
```

adapter 执行：

```text
Anthropic 消息
    → 翻译为模型 chat template 接受的消息格式
    → apply_chat_template(tokenize=True)
    → prompt_ids
    → SGLang /generate
```

下面使用手写的简化 token ID 展示机制，不是实际 Qwen tokenizer 的编码结果：

```text
第一轮输入 P1 = [10, 11, 12]
```

SGLang 在这个输入上生成第一轮响应，比如“先搜索函数，并调用搜索工具”：

```text
第一轮输出 R1 = [201, 202, 203, 204]

对应采样 logprob：
                 [l201, l202, l203, l204]
```

此时第一轮实际发生过的生成关系是：

```text
P1 → R1
```

每个输出 token 都有明确的原始上下文和采样 logprob。

### 第二步：adapter 同时准备“给训练保存的记录”和“给 Claude Code 的回复”。

SGLang 返回后，adapter 从返回信息中提取精确的输出 token 和 logprob，构造：

```text
TurnRecord 第1轮：
    prompt_ids       = P1
    output_ids       = R1
    output_log_probs = 第一轮采样 logprob
    finish_reason    = 本轮结束原因
```

另一方面，它把输出 token decode 成文本，再解析成 Claude Code 能理解的：

```text
thinking 块
text 块
tool_use 块
```

例如工具调用会变成结构化的工具名称和参数，而不是把原始 token ID 交给 Claude Code。

当前 _run_turn 的顺序是：构造 TurnRecord → 解析回复 → 调用 _respond 回送回复 → 调用 manager.record_turn(...) 登记。record_turn 将 TurnRecord 挂在该 session 消息树的 assistant 节点上，首先是内存记录，不是这里直接保存成最终训练文件。[实际调用顺序](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/adapters/common.py#L318)

所以，此时 R1 原始 token 并没有丢。

### 第三步：Claude Code 执行工具，再发送第二轮完整历史。

Claude Code 收到工具调用，执行搜索，取得结果，然后发送：

```text
system：原系统说明
user：原任务
assistant：第一轮的 thinking / text / tool_use
user/tool：搜索结果
```

这里发送的是消息与字符串，并不是：

```text
请继续使用原始 token [10,11,12,201,202,203,204]
```

adapter 又对这整份历史执行一次 chat template 和 tokenize。

如果一切完全保持 token 一致，结果可能是：

```text
P2_clean =
[10,11,12 | 201,202,203,204 | 31,32]
  原输入       原响应          新工具结果与模板
```

这就是理想的精确前缀延续。

但如果工具 JSON 被重新格式化、消息经过规范化，或者模板对历史 thinking 的处理发生变化，可能得到：

```text
P2_drift =
[10,11,12 | 201,202,999,204 | 31,32]
                     ↑
              原来这里是203
```

对人看起来可能还是同一次工具调用，但 token 序列已经不同。

这个例子假定结构化 assistant 消息仍能匹配消息树中的原节点，只在 token 重渲染时产生差异。例如字典内容相等，不意味着重新序列化后的 token 一样。这样可以单独观察 REALIGN；若消息树节点本身匹配失败，还可能进入另一条 rewrite merge 或分支路径。

### 第四步：第二轮直接用重新渲染后的 P2 调用 SGLang。

注意：此时并没有先用 REALIGN 把 P2 修回原始 token。

SGLang 实际收到的是：

```text
P2_drift =
[10,11,12,201,202,999,204,31,32]
```

然后生成第二轮响应：

```text
R2 = [301,302]
```

adapter 同样保存第二轮：

```text
TurnRecord 第2轮：
    prompt_ids       = P2_drift
    output_ids       = R2
    output_log_probs = 第二轮采样 logprob
```

因此现在保存着两条真实记录：

```text
第1轮：P1       → R1
第2轮：P2_drift → R2
```

两轮各自的原始采样记录都可以是准确的；问题出现在把它们拼成训练行时。

### 第五步：执行结束，TrajectoryManager 开始组装训练样本。

finish_session → get_trajectory → _split_chain_into_builders 会按叶链依次处理各轮。

先放入第一轮，builder 的内部状态是：

```text
tokens：
[10,11,12 | 201,202,203,204]

mask：
[ 0, 0, 0 |  1,  1,  1,  1]
```

这里用 builder 的完整 mask 展示；最终 Sample.loss_mask 会省略最初 prompt 对应的部分。

接着准备加入第二轮，比较：

```text
已经持有：
[10,11,12,201,202,203,204]

第二轮输入：
[10,11,12,201,202,999,204,31,32]
                └─共同前缀─┘
```

共同前缀到 202 为止。分歧发生在第一轮响应内部，而第二轮响应只有 2 个 token，小于默认阈值 1024，因此满足当前 REALIGN 条件：

```text
分歧位置在最近一次响应区域内
并且
len(第二轮输出) < 1024
```

### 第六步：REALIGN 清掉的不是只有不同的那个 token，而是最近旧响应整段的训练权重。

实现从第一轮响应的起点开始，用第二轮 prompt 的对应部分覆盖，并将这些位置的 mask、logprob 置零，再接上第二轮输出。

结果变为：

```text
tokens：
[10,11,12 | 201,202,999,204 | 31,32 | 301,302]

mask：
[ 0, 0, 0 |  0,  0,  0,  0 |  0, 0 |  1,  1]
```

也就是说：

- 999 是重新渲染出来的内容，不拿它冒充原始采样动作训练；
- 原来没有改变的 201、202 也不再训练；
- 第一轮原始 R1=[201,202,203,204] 在这个例子中不再作为独立训练行输出；
- 最终只有第二轮 R2 获得直接的策略梯度信号。

这就是“记录过原始 token，但最终没有训练它们”的具体过程。[REALIGN 实现](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/trajectory.py#L216)

### 为什么官方这样实现有合理性？

因为下面这种拼法确实不对：

```text
使用重渲染后的 token 999
却给它贴上原始 token 203 的采样 logprob
并把它当作模型实际采样的动作
```

即使后面的 token 还是 204，它前面的条件上下文已经改变，也不能仅凭 token ID 相同就直接复用原来整段的行为概率。

所以，不对重渲染的历史直接施加原始动作 loss，是合理的。 官方选择把它作为上下文保留，让一个较连续的训练行继续容纳后面的响应。

我认为有问题的是：为了形成这个训练行，它进一步放弃了原始第一轮本来仍然可以成立的训练记录。

```text
原始记录：
P1 → R1
```

并没有因为下一轮历史改写就变成假的。它仍然证明：模型在 P1 下真实做出了 R1。

从表示能力上，可以分别保留：

```text
训练行A：P1 → R1
         训练第一轮原始动作

训练行B：P2_drift → R2
         P2_drift 全作上下文，只训练第二轮原始动作
```

这不需要把错误 logprob 贴到新 token 上。当前 FORK 路径就能表达这种分离，但会增加训练行和重复前缀计算；最终还需要正确处理执行级 reward、分母和更新边界。

因此，我的质疑具体有三点：

1. 短响应未必缺乏学习价值。 一个很短的搜索、编辑或工具选择，可能决定整道 SWE 任务能否解决。删除它的直接训练信号，需要收益证据。
2. 删除整轮比“屏蔽发生变化的内容”更强。 本例甚至只改了一个位置，却把整个旧响应从 loss 中移除。
3. 保留旧动作与否，取决于下一轮输出长度，理由并不充分。 同样的历史漂移，新输出短于 1024 就屏蔽旧轮，达到 1024 则 fork 保留。官方测试明确锁定了这个行为，但它本身不是训练效果上的论证。[官方阈值测试](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/tests/test_agent/test_trajectory_manager_branching.py#L1218)

所以这里不是“slime 把剩余 token 的 loss 算错了”，而是：它为了减少轨迹拆分，接受了一部分真实动作没有直接训练信号的代价。我们需要判断这个代价在自己的 Claude Code/SWE 链路中有多大、是否值得。

<a id="discussion-3"></a>

## 第 3 轮：保留公共前缀是否合理，以及 P3 是否记录过覆盖损失

**用户追问（原注释，整理时补回）**

> 这里说的是 rollout 过程中只是用消息匹配，而不是 token 级别的检查，token 级别的检查在最后完成后，然后这里应该对应于压缩或者 subagent 的情况吗？

**用户在同一轮进一步提出**

> 我理解你的意思了，你是想说符合realign条件就把这轮的mask全变0可能丢掉某此关键搜索，realign本身如果出现的话整条realign后的[201,202,999,204]被mask = 0应该是合理的，因为999,204变了token和变了前缀条件因此logprob条件不适用这两个mask，但是如果单独留201,202继续反向传播这可能是合理的吗？
>
> 这个地方其实我个人的直觉是我们还需要看这个realign，fork(无论是消息fork还是token fork)在不同的训练任务下会有多大概率会被触发，然后在我们之前做过的p3实验中是否有记录下这一点，虽然只是很少的几个任务的试运行。
>
> 比较微妙的点在于这里的是否fork的权衡，1024是触发他的阈值，你说slime官方说自己做了调优说明他们可能测试过这个旋钮。但是有可能是对glm模型做的而不是qwen模型。

**Codex 回答**

是的：在你给出的例子里，保留 201、202 的直接训练信号，在数学上是有依据的。 另外，我在 P3 归档中找到了“已经捕获的前序轮没有进入训练投影”的具体证据，但没有找到足以计算 REALIGN、消息 fork、token fork 各自发生率的记录。下面分别解释。

### 先澄清消息匹配和 token 检查的时机。

你的理解大体正确，但要限定为 TrajectoryManager 的跨轮拼接流程：

| 阶段 | 当前主要做什么 |
| --- | --- |
| rollout 每轮完成后，record_turn() | 根据结构化消息寻找消息树上的挂载位置，保存这一轮实际的 prompt token、输出 token、logprob；也可能触发 assistant rewrite merge |
| session 结束，get_trajectory() | 遍历消息树路径，用实际 token 的公共前缀判断 CLEAN、REALIGN 或 token FORK，构造最终训练样本 |

所以，“消息树上能接起来”和“token 能忠实地拼成一条训练序列”，确实是两层判断。但不能扩大成“rollout 期间完全不检查 token”；每轮已经捕获 token，rewrite merge 也会读取输出长度。

这也不只对应压缩或 subagent：

- 压缩历史、subagent 使用不同消息历史，可能产生消息分支，具体取决于 session 的组织方式。
- 普通工具往返也可能因为 assistant 消息被重新组织而影响消息匹配。
- 结构化消息仍然相等，但 JSON 重新序列化或 chat template 改写了历史，也可能只在后面的 token 拼接阶段暴露差异。

因此，消息 fork、token fork、压缩、subagent 不能一一对应。[官方实现](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/agent/trajectory.py)

### 关于保留 201、202：需要看的是每个 token 的完整因果前缀。

假设第一轮真实采样是：

```text
输入：P
输出：[201, 202, 203, 204]
```

下一轮重渲染后，历史变成：

```text
P + [201, 202, 999, 204] + 工具结果 + …
```

这里假设 P 完全一致，位置、attention 等模型输入条件也一致。

| 重渲染中的 token | 原始采样记录能否继续用于该位置的策略损失 | 原因 |
| --- | --- | --- |
| 201 | 可以 | 原始条件与现在都是 P |
| 202 | 可以 | 原始条件与现在都是 P + [201] |
| 999 | 不可以 | 原始采样的是 203，没有这个位置采样 999 的原始 logprob |
| 最后的 204 | 不可以直接沿用 | 原始前缀含 203，现在含 999，条件概率已经不同 |

因此，对这段旧响应而言：

```text
当前 REALIGN： [0, 0, 0, 0]
保留忠实前缀：[1, 1, 0, 0]
```

第二种在 token 与原始采样记录的对应关系上是成立的。后面出现改写，不会反过来使前面两个 token 的因果条件失效。

所以，更准确的评价是：当前整轮清零是一种保守处置，但不是 token 正确性所必需的最小屏蔽范围。

不过，“保留前缀合理”还不能直接推出“这就是完整修法”：

- 它仍然丢掉原始 203、204 的训练信号；保留原始完整响应作为另一条训练序列，才有机会保住这些动作。
- 如果保住的是搜索指令的开头，丢掉的是具体搜索内容，关键决策仍可能缺少直接监督。
- 保留多少 token 会影响 loss 分母和执行之间的权重；还需要保持原始 logprob、采样 support、来源轮次等一致，避免公共前缀重复计入损失。

这里要区分两个问题：这些 token 能不能忠实地训练，以及最终训练目标是否保留了我们想要的动作与权重。

### P3 确实留下了相关线索，而且可以举出具体实例。

P3 报告注明，当时同步回的是文本证据，未包含二进制。现存归档中没有找到三类事件的独立计数，也缺少重放 token 公共前缀所需的原始数组。[P3 报告 （第 5 行）](../../preflight/preflight_report.md#L5)

但在两次早期失败尝试的归档里，保留了 50 组 capture_records.json 与 trajectory_projection.json。我逐组比对后发现：

| 归档尝试 | 保留投影数 | 第一轮 capture 未被任何最终 branch 引用 |
| --- | --- | --- |
| converter signature 失败尝试 | 35 | 23 |
| postprocess binding 失败尝试 | 15 | 9 |

这 50 组里的 215 条 capture 都标记为 complete，模型都是 Qwen/Qwen3-30B-A3B。

例如任务 django__django-11099 的一条执行：

| 生成轮次 | 捕获的输出 token 数 | 训练投影是否保留该轮引用 |
| --- | --- | --- |
| 第 1 轮 | 458 | 否 |
| 第 2 轮 | 307 | 否 |
| 第 3 轮 | 199 | 是 |
| 第 4 轮 | 401 | 是 |
| 第 5 轮 | 349 | 是 |
| 第 6 轮 | 553 | 是 |

原始捕获合计 2,267 token；投影中的 mask=1 合计 1,502 token，恰好等于后四轮之和。前两轮合计 765 token 没有作为对应轮次的直接训练信号保留下来。

证据：[原始捕获记录](../../preflight/remote_evidence_20260708/preflight_evidence/preflight_j4_fail_converter_signature_/artifacts/rollouts/00be4692-dfa2-41fe-a270-/capture_records.json)、[训练投影](../../preflight/remote_evidence_20260708/preflight_evidence/preflight_j4_fail_converter_signature_/artifacts/rollouts/00be4692-dfa2-41fe-a270-/trajectory_projection.json)。

这些证据说明覆盖差异实际出现过，但不能把 32/50 称为 REALIGN 发生率。 原因包括：

- 归档来自失败尝试，不代表最终成功训练批次或完整任务分布。
- 缺少事件与原始 token，不能区分 REALIGN、rewrite merge 或其他处理的贡献。
- 投影已经生成，不等于这些样本最终完成了 optimizer 更新。

同样，capture 中的 alignment_status=aligned 不能证明前序轮最终都进入了 loss；这是不同层面的指标。

### 关于 1024，我需要纠正此前可能造成的印象：目前没有找到官方调优实验的证据。

找到的是官方代码和单元测试明确规定了这个行为：token 漂移满足位置条件时，比较的是新一轮输出的总长度；小于阈值走 REALIGN，达到阈值走 FORK。单元测试证明实现符合预期，不能证明 1024 经过训练效果或吞吐调优。[官方阈值测试](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/tests/test_agent/test_trajectory_manager_branching.py#L1218)

因此，当前不能认定“官方对 GLM 调好了，只是不适合 Qwen”。代码里的默认值也不是按模型选择的。我们可以提出模型适配性的疑问，但不能替官方补出实验依据。

这个阈值确实存在值得测量的权衡：拆成更多训练序列通常会增加重复前缀的计算；REALIGN 则可能用信号损失换取更少的序列。它还让前一轮能否保留训练信号，受到后一轮输出长度的影响，所以模型、模板和任务行为都会影响结果。

### 我同意先测实际分布，再决定如何处理；但不能只看 fork 的比例。

下一次小规模探针，最有价值的是同时记录：

- 事件频率：消息分支、rewrite merge、CLEAN、REALIGN、token FORK 分开计数。
- 信号覆盖：每轮生成多少 token、最终保留多少，哪些完整轮次失去直接策略损失。
- 触发背景：普通工具往返、reminder、压缩、subagent，以及具体的模型和模板版本。
- 计算代价：最终训练序列数、重复前缀 token 数、训练耗时。

保留完整原始请求和每轮采样记录后，可以先在 CPU 上重放不同拼接策略，比较“保留多少信号、多出多少计算”。只保存最终 Sample 不够，因为 rollout 期间的 rewrite merge 可能已经删除了旧生成记录。

这能帮助我们回答：它究竟是少见且可接受的折中，还是会系统性地削弱某类模型、某些轮次或某种搜索行为的训练信号。 P3 的现存证据已经足以支持把这个问题列为优先测量项，但还不足以替我们选定阈值或修法。

<a id="discussion-4"></a>

## 第 4 轮：1024 阈值究竟比较什么

**用户追问（原注释，整理时补回）**

> 这里的 1024 我好像理解有点问题，这里的 1024 是怎么判断要 REALIGN 还是 FORK。举个例子为我解释一下，让我直观看到、理解清楚。

**Codex 回答**

1024 比较的是下一轮实际生成的输出 token 数，不是上一轮长度、历史长度，也不是发生漂移的 token 数。这个比较是在拿到下一轮输出后、组装训练样本时做的。

用同一个两轮例子来看。

### 第一轮：实际采样并保存了 4 个输出 token。

```text
第一轮输入：P
第一轮输出：[201, 202, 203, 204]

保存的序列：P + [201, 202, 203, 204]
loss mask：0…0    1    1    1    1
```

### 第二轮：Claude Code 发回历史，重新渲染后有一个 token 变了。

```text
第二轮输入：P + [201, 202, 999, 204] + 工具结果
                            ↑
                      原来这里是 203
```

共同前缀截止到 202。漂移发生在最近一次响应内部，所以满足了“可以考虑 REALIGN”的位置条件。

然后 SGLang 根据这个第二轮输入生成新输出。接下来才比较这个新输出的长度。

### 情况 A：第二轮输出了 20 个 token，小于 1024。

于是走 REALIGN，把第一轮响应所在区域按新 prompt 覆盖，并全部视为上下文：

```text
最终合成一条训练序列：

P + [201, 202, 999, 204] + 工具结果 + 第二轮输出（20 token）
       0    0    0    0       0…0          1…1
```

结果：

- 第一轮原来的 4 个生成 token，不再贡献直接策略损失。
- 第二轮的 20 个生成 token 参与训练。
- 最终只有一条训练序列。

### 情况 B：第二轮输出了 1024 个 token，达到阈值。

于是走 FORK，结束旧训练序列，再以第二轮的真实输入建立新序列：

```text
训练序列 1：

P + [201, 202, 203, 204]
       1    1    1    1
               ↑
       保留第一轮的原始采样


训练序列 2：

P + [201, 202, 999, 204] + 工具结果 + 第二轮输出（1024 token）
       0    0    0    0       0…0             1…1
               ↑
       在第二轮中只是上下文
```

结果：

- 第一轮原始 4 个 token 仍然参与训练。
- 第二轮 1024 个 token 也参与训练。
- 最终形成两条训练序列。这里的 FORK 是训练样本拆分，不会重新执行第一轮，也不会让 agent 重新选择动作。

把其他条件固定，边界就是：

| 第二轮实际输出长度 | 处理方式 | 第一轮原始响应是否保留直接训练信号 |
| --- | --- | --- |
| 20 | REALIGN | 否 |
| 1023 | REALIGN | 否 |
| 1024 | FORK | 是 |
| 2000 | FORK | 是 |

但不是所有第二轮输出都拿 1024 来决定是否拆分。 完整判断顺序是：

```text
新 prompt 是否精确延续已有 token？
├─ 是 → CLEAN，继续拼接，不看 1024
└─ 否 → 漂移位置是否落在最近一次响应区域？
         ├─ 否，漂移更早 → FORK，不看 1024
         └─ 是 → 新一轮输出长度 < 1024？
                  ├─ 是 → REALIGN
                  └─ 否 → FORK
```

所以我之前指出的微妙之处是：在相同的历史漂移下，第二轮生成 1023 个还是 1024 个 token，会决定第一轮响应是否保留训练信号。 它不是根据“第一轮有多少 token 不可信”来确定屏蔽范围。

<a id="discussion-5"></a>

## 第 5 轮：“最近一次响应区域”的位置条件

**用户追问（原注释，整理时补回）**

> “漂移位置是否落在最近一次响应区域”这个条件是什么意思？再举个例子，避免我的理解有偏差。

**Codex 回答**

最近一次响应区域 指的是：当前已经拼好的序列中，最后一轮模型输出所在的位置。 准备接入第三轮时，这里说的是第二轮输出。

用三轮对话举例，更容易区分。

前两轮已经记录完，当前序列是：

```text
原始输入 P
  + 第一轮输出 [201, 202, 203, 204]
  + 工具结果 A
  + 第二轮输出 [401, 402, 403, 404]
                ↑
         最近一次响应从这里开始
```

> **时机表述修正：**原回答在这里把实时请求与事后组装混写了。准确时序是：第三轮请求到达时重新渲染并保存输入；session 结束后，组装循环才遍历第三轮记录并比较 token。下面保留原句以便理解后续追问，第 6 轮给出明确更正。
>
> 原句：接下来第三轮请求到达，重新渲染整个历史。代码比较“已有序列”和“第三轮输入”，找到两者从哪里开始不一致。

### 例子一：变化发生在第二轮输出中。

```text
已有：P + [201,202,203,204] + A + [401,402,403,404]
新入：P + [201,202,203,204] + A + [401,402,999,404] + 工具结果 B
                                           ↑
                                      从这里不一致
```

此前的输入、第一轮、工具结果 A，以及第二轮前两个 token 都相同。

不一致的位置在“最近一次响应起点”之后，满足位置条件。接下来才检查第三轮输出长度：

- 第三轮输出 < 1024：REALIGN。
- 第三轮输出 ≥ 1024：FORK。

如果走 REALIGN，当前实现会把第二轮整个响应区域改成 mask=0，包括没有变化的 401、402；第一轮的 mask 不受这次操作影响。

### 例子二：变化发生在第一轮输出中。

```text
已有：P + [201,202,203,204] + A + [401,402,403,404]
新入：P + [201,202,999,204] + A + [401,402,403,404] + 工具结果 B
                   ↑
              从这里不一致
```

虽然第二轮输出的四个 token 看起来完全一样，但两条序列早在第一轮就分叉了。不一致位置早于“最近一次响应起点”，因此直接 FORK，第三轮输出多短都不会走 REALIGN。

这里的设计含义是：只覆盖最近一轮，无法修复更早的历史差异。 而且第二轮的 token 即使没变，它们依赖的前缀已经变了，也不能直接沿用原来的条件概率。

### 再补一个边界：第二轮第一个 token 就变了，也满足位置条件。

```text
已有：… + A + [401,402,403,404]
新入：… + A + [999,402,403,404] + B
               ↑
        恰好在最近响应起点分叉
```

因为实际判断是：

```text
公共前缀长度 >= 最近一次响应的起始位置
```

所以它要求的是差异不能早于最近一次响应，并不要求最近一次响应必须保留一部分相同 token。只要符合这个位置条件，再由新一轮输出长度决定 REALIGN 还是 FORK。

<a id="discussion-6"></a>

## 第 6 轮：纠正时间线：实时捕获与事后组装

**用户追问（原注释，整理时补回）**

> 这里实际上的 token 对齐应该都是在 rollout 完成后做的吧？这里你只是在模拟这个遍历每一轮的处理循环吗？然后看成是每一轮到达吗？带我看看这部分的代码逻辑。

**Codex 回答**

对，你说得准确。我前面的例子是在模拟 rollout 结束后，遍历各轮记录的组装循环，但用了“第三轮请求到达”的表达，把两条时间线混在了一起。

实际需要明确区分：

- 重新渲染历史：发生在 rollout 期间，每轮请求真正到达时，用于生成该轮的推理输入。
- 跨轮 token 对齐与 REALIGN/FORK：在这条 adapter 路径中，发生在 session 收尾、构造训练样本时。使用各轮已经保存的 token，这里不会重新调用 chat template。

下面按本地 vendored slime 的实际调用链来看。

### 1．rollout 期间：每轮生成、保存记录，挂到消息树。

入口是 [`_run_turn()` （第 318 行）](../../../../../rh2/src/slime/agent/adapters/common.py#L318)。核心顺序如下，省略了异常处理等代码：

```python
translated, tools_schema = self._translate(body)
prompt_ids = _render_token_ids(
    translated, tok, tools=tools_schema, add_generation_prompt=True
)

turn = await call_sglang_generate(
    prompt_ids, s, body, adapter=self, session_id=sid
)

# 中间解析输出、构造协议回复，并调用 _respond()

self.manager.record_turn(
    sid,
    turn=turn,
    prompt_messages=translated,
    response_message=reply.manager_message,
    metadata={"sid": sid},
)
```

这里有两份不同用途的信息：

```text
prompt_messages / response_message
    → 用来组织消息树

turn.prompt_ids / turn.output_ids / turn.output_log_probs
    → 保存本轮真实推理的 token 和概率记录，供后续构造训练样本
```

[`record_turn()` （第 283 行）](../../../../../rh2/src/slime/agent/trajectory.py#L283) 的主要操作是：

```python
node, depth = self._find_mount_point(root, prompt_messages)
node, depth = self._try_merge_assistant_rewrite(
    sid, node, prompt_messages, depth
)
node = self._mount_prompt_messages(node, prompt_messages[depth:])
self._attach_assistant_leaf(
    sid, node,
    turn=turn,
    response_message=response_message,
    metadata=metadata,
)
```

这一段没有调用 classify_token_drift()。它是在消息树中找到位置，再挂上本轮记录。

但有一个重要区别：消息层的 _try_merge_assistant_rewrite() 已经会在这里运行，必要时把旧节点的 turn 清掉。它和我们正在讨论的 token REALIGN 是两套机制，不能都归为“结束后才处理”。

### 2．session 收尾：开始把消息树变成训练样本。

[`finish_session()` （第 245 行）](../../../../../rh2/src/slime/agent/adapters/common.py#L245) 先关闭 session、处理在途请求，再调用：

```python
samples = self.manager.get_trajectory(
    sid,
    base_sample=base_sample,
    reward=reward,
    extra_metadata=extra_metadata,
    max_sample_tokens=max_sample_tokens,
)
```

此后的调用链是：

```text
get_trajectory()
  └─ 遍历消息树的各个叶节点
      └─ 获取从根到该叶节点的路径 chain
          └─ _chain_to_samples(chain)
              └─ _split_chain_into_builders(chain)
                  └─ 逐轮检查 token，执行 CLEAN / REALIGN / FORK
              └─ builder.to_sample()
```

这一步中的“一轮接一轮”，是遍历已有记录，并没有向 SGLang 发起新的生成请求。

### 3．你说的“模拟每一轮到达”，真正对应下面这个循环。

源码在 [`_split_chain_into_builders()` （第 456 行）](../../../../../rh2/src/slime/agent/trajectory.py#L456)：

```python
asst_nodes = [
    n for n in chain
    if n.role == "assistant" and n.turn is not None
]

builders: list[_SampleBuilder] = []
for asst_node in asst_nodes:
    trained = not asst_node.response_trained
    asst_node.response_trained = True

    if not builders or (
        kind := builders[-1].classify_token_drift(asst_node.turn)
    ) is DriftKind.FORK:
        builders.append(_SampleBuilder(self._fork_threshold))
        builders[-1].append_turn(
            asst_node.turn, DriftKind.CLEAN, trained=trained
        )
    else:
        builders[-1].append_turn(
            asst_node.turn, kind, trained=trained
        )
```

builder 可以理解为“正在构造的一条训练序列”。假设这条消息路径保留了三轮生成记录，循环就是：

| 循环位置 | 此时做什么 |
| --- | --- |
| 取出第 1 轮记录 | 当前没有 builder，创建一个，放入第一轮 prompt 和输出 |
| 取出第 2 轮记录 | 比较 builder 已有 token 与保存的第二轮 prompt_ids |
| 取出第 3 轮记录 | 比较经过前一步处理的 builder 与保存的第三轮 prompt_ids |

这里第三轮的输出也早已生成并保存在记录里，所以此时可以直接读取它的长度，与 1024 比较。

另外，response_trained 是跨消息树分支的去重标记：同一个生成节点被多条路径经过时，避免重复计入直接策略损失。

### 4．具体比较、覆盖与拆分，发生在这些位置。

[`classify_token_drift()` （第 169 行）](../../../../../rh2/src/slime/agent/trajectory.py#L169) 的实际判断是：

```python
realign_at = _common_prefix_len(self.tokens, turn.prompt_ids)
drift = len(self.tokens) - realign_at

if drift == 0:
    return DriftKind.CLEAN

start = self.last_response_start_idx
if (
    start is not None
    and realign_at >= start
    and len(turn.output_ids) < self._fork_threshold
):
    return DriftKind.REALIGN

return DriftKind.FORK
```

这里：

- self.tokens：当前 builder 已经拼好的序列，可能经过前几次 REALIGN。
- turn.prompt_ids：当前遍历到的这一轮，当时送给 SGLang 的真实输入。
- turn.output_ids：这一轮当时生成的真实输出。
- last_response_start_idx：builder 中最近一次追加的响应起点。

如果返回 REALIGN，append_turn() 会调用 _align_to_prompt()，核心就是：

```python
response_start = self.last_response_start_idx
tail = prompt_ids[response_start:]

self.tokens[response_start:] = tail
self.loss_mask[response_start:] = [0] * len(tail)
self.logprobs[response_start:] = [0.0] * len(tail)
```

然后再追加当前遍历轮的输出及对应 mask、logprob。

如果返回 FORK，则前面的循环保留旧 builder，创建一个新 builder，以当前轮保存的完整 prompt 和输出开始另一条训练序列；不是重新运行 agent。

因此，我前面那句话准确的写法应当是：

> rollout 结束后，组装循环遍历到第三轮记录，将当前 builder 的 token 与第三轮当时保存的 prompt_ids 比较，判断是否需要 REALIGN 或拆成另一条训练序列。

<a id="discussion-7"></a>

## 第 7 轮：四轮完整例子：从请求、消息树到两个 Sample

**用户问题**

> 直接看代码相对比较慢，用直观的例子再走一遍这个过程：在 rollout 过程中怎么逐轮走的，保存了哪些对象、消息树、每轮的 record_turn，然后走完了之后拼接 Sample 的过程，如何判断，有哪些对象。这里设计一个完整的过程例子展示完整的过程来代替直接看代码，但是要保证和代码逻辑包括和每个对象完整对应。

**Codex 回答**

可以。我们用一次四轮 coding rollout，完整走过“收请求 → 生成 → 保存消息树 → 结束后组装 → 输出 Sample”。

这个例子同时包含一次 CLEAN、一次 REALIGN、一次 token FORK。我已经用当前 TrajectoryManager 和 _SampleBuilder 的实际逻辑在内存中核对过结果。下面的 token、logprob 是便于手算的合成值，不是 Qwen tokenizer 的真实输出。

### 先把对象和名字固定下来。

任务是“修复一个函数的 bug”，四轮分别做：

| 轮次 | 模型行为 | 返回的工具结果 |
| --- | --- | --- |
| 第一轮 | 搜索相关文件 | 找到目标文件 |
| 第二轮 | 查看函数实现 | 返回函数内容 |
| 第三轮 | 修改代码并运行测试 | 测试通过 |
| 第四轮 | 输出最终说明 | 结束 |

以下符号分别表示：

| 名字 | 对应的实际对象或字段 |
| --- | --- |
| sid="demo" | 这次 session 的标识 |
| S、U | 翻译后的 system、user 消息字典 |
| A1～A4 | 四轮生成的结构化 assistant 消息，即 Reply.manager_message |
| E1～E3 | 翻译后的工具结果消息 |
| T1～T4 | 四个 TurnRecord，保存每轮真实输入、输出 token 和 logprob |
| G1～G4 | 每轮的输出 token，即对应 TurnRecord.output_ids |
| B1、B2 | 结束后才创建的 _SampleBuilder |
| Sample 1、Sample 2 | 最后交给下游的训练样本 |

A2 和 T2 不是同一个对象。 A2 是“第二轮说了什么、调用了什么工具”的消息字典；T2 是“第二轮推理实际用了哪些 token”的记录。

这里说的“保存”首先指保存在内存中。slime 的 TurnRecord 也不是 rh2 另行落盘的 GenerationCaptureRecord。

### rollout 开始前，adapter 和 manager 各自持有不同的状态。

开启 session 后，大致是：

```text
adapter
├─ store["demo"] → Session
│                  ├─ sampling_defaults：本次采样配置
│                  └─ max_context_tokens：4096
│
└─ manager → TrajectoryManager
             ├─ _fork_threshold：1024
             ├─ _trees：当前还没有 demo 的消息树
             └─ _turn_count：当前还没有 demo 的生成计数
```

Session 保存采样配置和上下文预算；轨迹放在 TrajectoryManager，不在 Session 里面。

现在还没有 TurnRecord、builder 或最终 Sample。

### 第一轮：收到初始任务，生成第一条回复。

Claude Code 发来初始请求。adapter 翻译后得到：

```text
prompt_messages = [S, U]
```

然后 apply chat template、tokenize。把完整初始输入简记为：

```text
P = [10, 11, 12]
```

SGLang 收到 P，生成：

```text
G1 = [201, 202, 203, 204]
```

adapter 从 SGLang 返回值构造：

```text
T1：TurnRecord
├─ prompt_ids       = P
├─ output_ids       = G1
├─ output_log_probs = [-0.1, -0.1, -0.1, -0.1]
├─ finish_reason    = "stop"
└─ ill_formed       = false
```

随后解析生成内容，构造另一个对象：

```text
Reply
├─ manager_message = A1
│                    结构化 assistant 消息，包含搜索工具调用
├─ finish_reason   = 面向回复的结束原因
└─ wire            = 发给 Claude Code 的协议内容
                     例如 Anthropic 的 tool_use 内容块
```

注意，这里发给 Claude Code 的是协议回复，不是把 T1 原封不动发过去。原始 token、logprob 留在 adapter/manager 这侧。

调用 _respond() 后，执行：

```text
record_turn(
    sid = "demo",
    prompt_messages = [S, U],
    response_message = A1,
    turn = T1
)
```

这次 record_turn() 做四件事：

1. 创建 demo 的虚拟根节点。
2. 消息树为空，没有可复用的历史节点。
3. 挂上 S、U 两个消息节点。
4. 挂上生成的 assistant 节点 A1，让它引用 T1。

消息树变成：

```text
虚拟根
└─ S                       turn=None
   └─ U                    turn=None
      └─ A1                turn=T1，turn_index=1
```

其中 A1 节点是一个 MessageNode，字段对应如下：

```text
role             = "assistant"
message          = A1 的消息字典
parent           = U 节点
children         = []
metadata         = {"sid": "demo"}
turn             = T1
turn_index       = 1
response_trained = false
```

S、U 也是 MessageNode，但 turn=None：它们来自输入，不是这次服务实际生成的响应。

此时没有为第一轮建立 loss mask。 只是保存了消息结构和真实生成记录。

### 第二轮：执行工具后，再次发送完整历史。

Claude Code 执行第一轮的搜索工具，拿到结果 E1，然后发来下一轮请求。

翻译后的消息为：

```text
[S, U, A1, E1]
```

重新渲染后的 token 假设正好延续第一轮：

```text
第二轮 prompt：
P + G1 + D1

其中：
D1 = [301, 302]
```

D1 表示追加的工具结果及相关模板分隔内容。这里将它们一起缩写，实际都已经体现在 prompt_ids 中。

SGLang 生成：

```text
G2 = [401, 402, 403, 404]
```

保存的第二轮记录是：

```text
T2
├─ prompt_ids       = P + G1 + D1
├─ output_ids       = G2
├─ output_log_probs = [-0.2, -0.2, -0.2, -0.2]
├─ finish_reason    = "stop"
└─ ill_formed       = false
```

构造回复 A2、调用 _respond() 后，执行第二次 record_turn()。

这次消息匹配沿着：

```text
S → U → A1
```

全部匹配成功。因此：

- 复用已有 A1 节点，它仍然引用 T1。
- 在下面追加工具结果节点 E1。
- 再追加生成节点 A2，引用 T2。

```text
虚拟根
└─ S
   └─ U
      └─ A1                turn=T1
         └─ E1             turn=None
            └─ A2          turn=T2，turn_index=2
```

到这里，仍然没有拿 T2.prompt_ids 与第一轮 token 做 CLEAN/REALIGN/FORK 判断。

### 第三轮：消息仍能匹配，但 token 历史出现漂移。

Claude Code 执行第二轮工具，拿到函数内容 E2，发来：

```text
[S, U, A1, E1, A2, E2]
```

为了单独观察 token 层处理，我们设定：回传的 A2 与树上的 A2 按字典相等比较仍然匹配，但其渲染 token 与原始输出不同。例如，工具参数的键顺序可能不影响字典相等，却影响序列化文本。

本例中，实际重新渲染出来的是：

```text
原始第二轮输出 G2  = [401, 402, 403, 404]
重渲染历史中的 G2′ = [401, 402, 999, 404]
```

因此第三轮真正送给 SGLang 的输入是：

```text
P + G1 + D1 + G2′ + D2

D2 = [501, 502]
```

模型生成：

```text
G3 = [601, 602, 603, 604]
```

第三轮记录：

```text
T3
├─ prompt_ids       = P + G1 + D1 + G2′ + D2
├─ output_ids       = G3
├─ output_log_probs = [-0.3, -0.3, -0.3, -0.3]
├─ finish_reason    = "stop"
└─ ill_formed       = false
```

第三次 record_turn() 按消息字典匹配，仍然能走到原来的 A2，然后追加 E2、A3：

```text
… → A1[T1] → E1 → A2[T2] → E2 → A3[T3]
```

这里最重要的状态是：

```text
T2.output_ids 里仍然保存着 403。
T3.prompt_ids 里已经出现了 999。
两个 TurnRecord 同时保存，各自忠实记录当时的推理。
```

此时还没有修正这种跨轮差异，也没有清零第二轮的 mask。

### 第四轮：再出现一次漂移，生成一个较长的最终回复。

工具执行结束，Claude Code 发来：

```text
[S, U, A1, E1, A2, E2, A3, E3]
```

消息仍然匹配已有路径，但第三轮的输出在历史重渲染中变成：

```text
G3  = [601, 602, 603, 604]
G3′ = [601, 602, 888, 604]
```

第四轮真实输入是：

```text
P + G1 + D1 + G2′ + D2 + G3′ + D3

D3 = [701, 702]
```

这次模型生成 1024 个 token：

```text
G4 = [10000, 10001, …, 11023]
```

因此：

```text
T4
├─ prompt_ids       = P + G1 + D1 + G2′ + D2 + G3′ + D3
├─ output_ids       = G4
├─ output_log_probs = 1024 个对应 logprob，本例均为 -0.4
├─ finish_reason    = "stop"
└─ ill_formed       = false
```

第四次 record_turn() 后，完整消息树为：

```text
虚拟根
└─ S
   └─ U
      └─ A1                turn=T1，turn_index=1
         └─ E1             turn=None
            └─ A2          turn=T2，turn_index=2
               └─ E2       turn=None
                  └─ A3    turn=T3，turn_index=3
                     └─ E3 turn=None
                        └─ A4
                           turn=T4，turn_index=4
```

现在的事实是：

- 消息树只有一条路径、一个叶节点。
- 保存了 4 个 TurnRecord。
- 四个生成节点的 response_trained 都还是 false。
- 还没有任何 _SampleBuilder，没有最终 Sample。

### rollout 结束后，才开始创建训练序列。

外层调用 finish_session()，关闭 session 并处理在途请求，然后调用 get_trajectory()。

get_trajectory() 找到叶节点 A4，取出根到叶的路径：

```text
chain = [S, U, A1, E1, A2, E2, A3, E3, A4]
```

接着筛选出带 TurnRecord 的 assistant 节点：

```text
asst_nodes = [A1, A2, A3, A4]
```

工具节点虽然没有进入这个列表，工具内容并没有丢失，因为它已经保存在下一轮 TurnRecord.prompt_ids 中。

现在开始循环遍历这四个节点。以下每一步都是读取已保存的记录，不再请求模型生成。

### 遍历到 A1/T1：创建第一个 builder。

当前没有 builder，于是创建 B1，加入 T1：

```text
B1.tokens：
P      | G1
3 个   | 4 个

B1.loss_mask：
000    | 1111

B1.logprobs：
0×3    | L1
```

这里 L1 就是 T1.output_log_probs。

其他字段：

```text
B1.leading_prompt_len       = 3
B1.last_response_start_idx  = 3
B1._fork_threshold          = 1024
```

last_response_start_idx=3 表示：按从 0 开始的位置计数，最近一次输出 G1 从位置 3 开始。

A1.response_trained 此时设为 true，表示这个生成节点已被某条路径认领，供跨路径去重使用。

### 遍历到 A2/T2：精确延续，CLEAN。

此时比较：

```text
B1 已有：P + G1
T2 输入：P + G1 + D1
```

已有的 7 个 token 全部是新输入的前缀，所以是 CLEAN。

追加输入里多出来的 D1，mask 为 0；然后追加真实输出 G2，mask 为 1：

```text
B1.tokens：
P   | G1   | D1 | G2

B1.loss_mask：
000 | 1111 | 00 | 1111

B1.logprobs：
0×3 | L1   | 0×2| L2
```

此时：

```text
tokens 长度                 = 13
leading_prompt_len          = 3
last_response_start_idx     = 9
mask=1 的 token 数           = 8
```

最近一次响应现在是 G2，起点位置为 9。

### 遍历到 A3/T3：漂移在最近响应内，且本轮输出短，REALIGN。

比较：

```text
B1 已有：P + G1 + D1 + [401,402,403,404]
T3 输入：P + G1 + D1 + [401,402,999,404] + D2
                                    ↑
                                  开始不同
```

位置可以直接算：

```text
P：3 个
G1：4 个
D1：2 个
G2 中相同的前两个 token：2 个

公共前缀长度 = 3 + 4 + 2 + 2 = 11
最近响应起点 = 9
```

判断条件：

```text
有漂移                         是
公共前缀长度 11 ≥ 响应起点 9    是
T3.output_ids 长度 4 < 1024     是

→ REALIGN
```

于是从位置 9 开始覆盖，不是从首次不同的位置 11 开始：

```text
覆盖前：
P   | G1   | D1 | G2
000 | 1111 | 00 | 1111

按 T3.prompt_ids 覆盖后：
P   | G1   | D1 | G2′  | D2
000 | 1111 | 00 | 0000 | 00
```

然后追加 T3 的真实输出 G3：

```text
B1.tokens：
P   | G1   | D1 | G2′  | D2 | G3

B1.loss_mask：
000 | 1111 | 00 | 0000 | 00 | 1111

B1.logprobs：
0×3 | L1   | 0×2| 0×4  | 0×2| L3
```

此时：

```text
tokens 长度                 = 19
leading_prompt_len          = 3
last_response_start_idx     = 15
mask=1 的 token 数           = 8
```

注意对象之间的区别：T2 本身没有被 REALIGN 修改。 它仍然保存原始 G2 和 L2。被改写的是 B1.tokens/loss_mask/logprobs，所以最终这条训练序列不再使用第二轮的直接训练信号。

### 遍历到 A4/T4：位置允许 REALIGN，但本轮输出达到阈值，FORK。

比较：

```text
B1 已有：
P + G1 + D1 + G2′ + D2 + [601,602,603,604]

T4 输入：
P + G1 + D1 + G2′ + D2 + [601,602,888,604] + D3
                                    ↑
                                  开始不同
```

此时：

```text
公共前缀长度 = 17
最近响应起点 = 15
```

漂移位置满足条件，但：

```text
T4.output_ids 长度 = 1024
1024 < 1024 不成立

→ FORK
```

执行结果是：

```text
保留 B1：

P   | G1   | D1 | G2′  | D2 | G3
000 | 1111 | 00 | 0000 | 00 | 1111


创建 B2：

完整 T4.prompt_ids                         | G4
P + G1 + D1 + G2′ + D2 + G3′ + D3          |
全部 21 个 token 的 mask 都是 0             | 1024 个 1
```

B2 的字段为：

```text
tokens 长度                 = 1045
leading_prompt_len          = 21
last_response_start_idx     = 21
mask=1 的 token 数           = 1024
```

消息树仍然只有一个叶节点。这里增加的是 builder 数量，消息树没有因为 token FORK 长出新枝。

另外，第四轮 FORK 保留的是此时已经存在的 B1。它不会恢复第三步 REALIGN 已经清掉的第二轮信号。

### 最后，将两个 builder 转成两个 Sample。

假设传入的 base_sample 为：

```text
index       = 7
group_index = 2
rollout_id  = 99
prompt      = "修复这个函数的 bug"
label       = None
```

本次执行最终奖励为 1.0，没有触发长度裁剪。

两个 builder 都还有 mask=1 的 token，因此都被输出：

| 字段 | Sample 1 | Sample 2 |
| --- | --- | --- |
| tokens | P + G1 + D1 + G2′ + D2 + G3 | T4.prompt_ids + G4 |
| tokens 长度 | 19 | 1045 |
| 初始 prompt 长度 | 3 | 21 |
| response_length | 16 | 1024 |
| loss_mask | 1111 + 00 + 0000 + 00 + 1111 | 1024 个 1 |
| mask=1 数量 | 8 | 1024 |
| rollout_log_probs | L1 + 0×8 + L3 | L4 |
| index / group_index / rollout_id | 7 / 2 / 99 | 7 / 2 / 99 |
| reward | 1.0 | 1.0 |
| status | COMPLETED | COMPLETED |

这里有三个容易混淆的字段细节：

- tokens 保留完整输入前缀；loss_mask 和 rollout_log_probs 去掉初始 prompt 对应的部分。 所以 Sample 1 的 token 数是 19，mask 长度却是 16。
- response_length 不等于参与 loss 的 token 数。 Sample 1 的 response 区间还包括工具结果、被置零的旧响应，因此长度为 16，只有 8 个 token 的 mask 是 1。
- 两个 Sample 的 prompt 字段都沿用 base_sample.prompt；每条序列实际的 token 输入由它自己的 tokens 表达。

adapter 随后还会填充 Sample.response：解码整个 response 区间。因此 Sample 1 的这个字符串也包含其中 mask 为 0 的内容，不是只解码参与 loss 的 token。

get_trajectory() 完成后，从 manager 中移除该 sid 的消息树和生成计数，返回：

```text
[Sample 1, Sample 2]
```

本例最后的训练信号去向是：

| 原始生成 | 原始 token 数 | 最终保留的直接训练 token 数 | 原因 |
| --- | --- | --- | --- |
| G1 | 4 | 4 | 保留在 Sample 1 |
| G2 | 4 | 0 | 第三轮组装时被 REALIGN 覆盖 |
| G3 | 4 | 4 | 第四轮 FORK 保留了旧 builder |
| G4 | 1024 | 1024 | 放在新 Sample 2 |

4 个 TurnRecord → 1 条消息树路径 → 2 个 builder → 2 个 Sample。 这些数量描述的是不同对象，不能互相替代。

### 再把消息层的另一套处理放回这个例子，避免遗漏。

上述主例中，四次消息匹配都成功，所以没有触发消息 rewrite merge。实际 record_turn() 还存在以下两条路径：

| 消息匹配时的情况 | rollout 期间发生什么 | 对结束后组装的影响 |
| --- | --- | --- |
| 历史消息匹配失败，且不能 rewrite merge | 把未匹配的历史挂成另一条消息路径 | 结束后遍历多个叶节点；每条路径再分别做 token 检查 |
| 满足短 assistant rewrite 的合并条件 | 改写旧节点的消息，将旧节点 turn 和 turn_index 清掉，记录 merged_rewrite 元数据 | 旧 TurnRecord 不再挂在树上，之后不会进入生成节点的组装列表 |

后者和主例中的 REALIGN 有明确区别：

```text
消息 rewrite merge：
在 record_turn 阶段，把旧节点的 TurnRecord 引用清掉。

token REALIGN：
在组装阶段，TurnRecord 仍在树上，改的是 builder 中的 token/mask/logprob。
```

如果多条消息路径共享一个生成节点，组装时会通过 response_trained 避免重复计算该节点的直接策略损失。这个标记表示“已被路径认领”，也不能证明其 token 最后一定保留为 mask=1——主例中的第二轮就会在认领后被 REALIGN 清零。

以上对象和流程对应本地的 [Session、Reply 与请求处理 （第 33 行）](../../../../../rh2/src/slime/agent/adapters/common.py#L33)、[TurnRecord 与 MessageNode （第 28 行）](../../../../../rh2/src/slime/agent/trajectory.py#L28)、[逐轮组装循环 （第 456 行）](../../../../../rh2/src/slime/agent/trajectory.py#L456) 和 [Sample 字段 （第 94 行）](../../../../../rh2/src/slime/utils/types.py#L94)。

<a id="discussion-8"></a>

## 第 8 轮：Issue、追加式 token 历史、PR 实现与 verl 对照

**用户追问（原注释，整理时补回）**

> 还有就是一开始这个 issue 我没太看懂，这里说的是什么问题，似乎包含了几个问题。他提出的方案我大概能理解，就是 token-in/token-out，我们想办法把下一轮工具输出的 token 拼接，尽量保证不漂移。这个地方我曾经用过的 verl 代码库好像就是类似思路。看起来好像比现在 slime 这种每轮重渲染分词后，最后再重新回来对照 token 的方式合理一些。

**Codex 回答**

对于同一条执行路径上的普通多轮交互，我也更倾向于你说的方式：保留原始 token 历史，追加新观察。 本地 verl 参考代码确实有这样的实现。

不过，单次请求使用 token-in/token-out，与跨轮保持原始 token 前缀，是两件事。当前 slime 调 SGLang 已经是输入 token、返回 token；问题出在下一轮重新构造输入时，没有继续以原始 token 历史为准。

### 这个 issue 实际上是在描述“两种漂移来源，加上一种下游后果”。

| 层次 | 发生了什么 | 举例 |
| --- | --- | --- |
| 模板处理历史 | 作者使用的 Qwen 模板会省略部分历史 reasoning | 第一轮生成了 `<think>`定位过程`</think>`工具调用，下一轮历史里只剩工具调用 |
| 消息转换与客户端回传 | 原始生成被解析成结构化消息，再回传时，文本或参数格式可能改变 | 工具参数原来是带空格的 JSON，回传后重新序列化为另一种格式 |
| 训练样本组装 | 普通连续交互失去精确 token 前缀关系，因而被拆成多个 Sample | 一次 agent 执行产生多条包含重复历史的训练序列 |

前两项是漂移来源，第三项是后果。作者报告的主要现象是 8 次环境 rollout 生成了 64 条 Sample，重复前缀增加了 token 总量和显存压力。[Issue #2288](https://github.com/THUDM/slime/issues/2288)

这里的“false fork”容易误解。它并不是说 token 比较器算错了：

从任务行为看，这是正常的“调用工具 → 收到结果 → 继续”；但从 token 看，历史已经真的改变，所以组装器只能把它视为不能直接拼接的序列。

另外，拆成多条 Sample 本身不必然违反 RL 正确性。每轮原始输入、动作和 logprob 仍然可以组成有效训练记录。这个 issue 主要指出：本来可以连续保存的普通交互，被转换过程人为打断，产生了额外计算。我们此前讨论的 REALIGN，则是面对这类漂移时另一种可能的处置，会进一步影响动作覆盖。

### 用一个例子看，你提出的方案改变了哪里。

第一轮真实推理：

```text
输入 P1：
任务描述

输出 G1：
<think>先检查调用位置，再确定修改点。</think>
调用工具：读取 foo.py
```

服务端已经拿到了精确的 P1、G1。

工具执行后，Claude Code 发回历史和工具结果。假设回传或模板处理把历史 thinking 省略了。

当前路径构造第二轮输入：

```text
P2 = 对客户端发回的完整消息重新套模板、分词

结果：
任务描述
调用工具：读取 foo.py
工具结果：文件内容……
下一轮 assistant 起始标记
```

于是，P1 + G1 不再是 P2 的精确前缀。

你说的追加方式构造第二轮输入：

```text
P2 =
    原样保存的 P1
  + 原样保存的 G1
  + 新工具结果对应的 token
  + 下一轮 assistant 起始标记
```

结果是：

```text
任务描述
<think>先检查调用位置，再确定修改点。</think>
调用工具：读取 foo.py
工具结果：文件内容……
下一轮 assistant 起始标记
```

历史部分直接复用原始 token，不再依赖“解码 → 解析 → 客户端回传 → 重新分词”能否无损往返。 结束后组装训练序列时，这条正常延续通常自然满足 CLEAN。

但追加的内容不能只是裸的“文件内容”字符串，还要正确处理工具角色标记、消息结束标记、下一轮 assistant/thinking 前缀等模板边界。

### PR 的思路确实接近这个方案，但它的具体实现比“只分词新增内容”绕了一步。

我重新读了 PR 当前提交 885a09e…，它主要增加了：

- Session.last_turn_ids：保存上一轮实际的 prompt_ids + output_ids。
- Session.assistant_history：保存服务端生成的结构化 assistant 消息，用来恢复客户端回传的历史。
- 保留历史 reasoning 的 Qwen 模板变体。
- 从重新渲染结果中定位最新 assistant 的结束边界，再取出边界之后的新内容，接到原始 token 历史后面。

这里需要修正我此前“只渲染新观察”的概括：实际代码仍然会渲染完整历史，还会渲染“截至最新 assistant 的历史”，通过二者找到后缀。

```text
渲染完整历史：
[重新渲染的旧历史] + [新增观察和生成前缀]

渲染截至最新 assistant：
[重新渲染的旧历史]

提取后缀，再拼接：
[原始 token 历史] + [新增观察和生成前缀]
```

所以它实现了“推理输入的历史 token 保持不变”，但尚不能据此声称“消除了每轮完整历史渲染的 CPU 开销”。[PR 当前实现](https://github.com/THUDM/slime/blob/885a09e852e5272d497936370707cc604830f805/slime/agent/adapters/common.py#L140)

作者报告修改后 8 次 rollout 对应 8 条 Sample，轨迹 token 总量从约 183 万降到约 26.5 万。这是作者的实验结果，我没有独立复现，也不能直接换算成训练吞吐提升。截至本次核对，PR 仍未合并。[PR #2287](https://github.com/THUDM/slime/pull/2287)

### 你对 verl 的记忆有代码依据，但需要限定到具体路径。

本地 reference/verl 的 ToolAgentLoop 就是这样运作的：

```text
初始消息
   ↓ 套模板
prompt_ids

生成结束
   ↓
把返回的原始 output.token_ids 追加到 prompt_ids
对应 response_mask 追加 1

工具执行结束
   ↓
只处理新增工具消息，构造它们的 token
追加到 prompt_ids
对应 response_mask 追加 0

继续用累积的 prompt_ids 生成
```

可以在 [生成阶段 （第 225 行）](../../../../../reference/verl/verl/experimental/agent_loop/tool_agent_loop.py#L225) 和 [工具结果追加阶段 （第 330 行）](../../../../../reference/verl/verl/experimental/agent_loop/tool_agent_loop.py#L330) 看到这两步。

不过，verl 也有其他路径。例如本地 schemas.py 的 use_inference_chat_template 分支会重新渲染完整消息，因此不能概括成“所有 verl 多轮实现都只追加 token”。[对应分支 （第 346 行）](../../../../../reference/verl/verl/workers/rollout/schemas.py#L346)

### 我赞同追加式设计作为普通线性交互的默认，但需要把两个边界设计清楚。

第一个是：谁拥有下一轮模型上下文的决定权。

verl 的这个工具循环自己执行工具、管理历史，知道哪些内容是新增观察。接入外部 Claude Code 时，客户端还可能压缩历史、修改早期消息或产生分支。服务端需要区分：

```text
普通新增工具结果 → 继续原始 token 历史

明确的压缩或历史改写 → 建立新的上下文段，
                     保留之前生成记录的训练来源
```

不能把所有客户端变化都强行解释成普通追加。

这也是当前 PR 还不能直接视为完整方案的原因之一：它按位置恢复 assistant 历史，并在拼接后检查原始 token 前缀。这个检查能验证拼接结果，却不等于已经验证客户端没有合法修改早期 user/tool 历史。 需要另外确认消息对应关系和上下文变更语义。

第二个是：追加方式会改变真实推理行为，训练和测评必须一致。

原路径可能让第二轮看不到第一轮 thinking；新路径保留它。这不仅是让训练文件更整齐，也改变了模型下一轮看到的状态，以及上下文长度。

因此，我对我们这条链路的倾向是：普通工具往返以原始 token 历史为准；压缩、分支作为明确的上下文变化处理；训练和测评使用同一套规则。 这样才能同时保住训练信号、控制重复前缀计算，并保持 Claude Code 实际执行语义清楚。

<a id="handoff"></a>

## 完整性核对与待继续讨论的问题

### 本次核对的范围

对照当前可见侧边栏会话与用户复制稿，八段实质性回答都已存在，未发现回答正文、两轮/三轮/四轮例子或 P3 关键数值的缺段。复制遗漏主要是六条附着在回答上的用户注释问题；本稿已按原讨论位置补回。最初引用的问题入口也补在正文之前，并明确标记其证据归属。

| 内容 | 核对结果 | 位置 |
| --- | --- | --- |
| vendored 来源、上游快照、README、PR #2005、#2287、#2328 | 原稿已包含；恢复来源链接并固定历史时点 | 第 1 轮 |
| 两轮 REALIGN、原始 logprob 与历史重渲染的区别 | 原稿已包含；恢复 token、mask 和记录示例的代码块 | 第 2 轮 |
| 公共前缀 201/202 可训练的条件及目标函数限制 | 原稿已包含 | 第 3 轮 |
| P3 的 50 份投影、215 条 capture、32 份首轮未引用，以及 2267/1502/765 例子 | 原稿已包含；保留失败尝试和归因限制 | 第 3 轮 |
| 1023/1024 边界、漂移位置、1024 无调优证据 | 原稿已包含；补回两条追问 | 第 3～5 轮 |
| 实时重新渲染与事后 token 对齐的时间线更正 | 原稿已包含；在旧表述旁标注修正并补回追问 | 第 5～6 轮 |
| 四轮全部对象、消息树、builder、mask/logprob、两个 Sample 的字段与数字 | 原稿已包含；恢复表格与对象图 | 第 7 轮 |
| Issue 的两种漂移来源、PR 实际仍渲染历史、verl 路径差异及上下文决定权 | 原稿已包含；补回追问并恢复链接 | 第 8 轮 |

核对是会话内容与排版的检查，没有重新执行 GPU 训练、真实 Claude Code rollout 或 P3 全量重放。四轮例子的历史内存验证使用合成 token/logprob 与当前 TrajectoryManager / _SampleBuilder 逻辑，并非真实 tokenizer 输出；接收 Sample 字段的容器为轻量替身，不代表完整训练后端测试。

### 后续讨论入口（建议，尚未定案）

1. 在真实任务中分别统计消息分支、rewrite merge、CLEAN、REALIGN、token FORK，并统计按轮次的生成 token 与最终直接训练 token。
2. 保存可重放的原始请求及每轮采样记录，避免只剩最终 Sample 而无法归因。区分事件频率、信号覆盖率与最终 optimizer 实际消费。
3. 比较保留完整原始轮次、仅保留忠实公共前缀、保持原始 token 历史等方案；把计算代价、执行级分母及重复前缀去重一起评估。
4. 明确普通追加、合法历史压缩、subagent/并发分支的上下文语义。对 PR #2287 的服务端历史恢复、对应关系检查和增量后缀构造继续核实，不能将已有断言等同于所有历史变更均被正确识别。
5. 若采用保留历史 reasoning 的追加式输入，训练与测评同步采用明确的上下文规则，并测量上下文长度、行为及资源开销的变化。

### 文件与来源可用性

- 原本机绝对路径已改为相对于本文的仓库链接，源代码行号使用链接片段保留。
- reference/verl 是本地参考目录；其他机器或远端分支若未携带该快照，需要另行取得对应实现，不能将本文对本地路径的核查扩大为对所有 verl 版本的结论。
- 本文位于 tmp/ 目录，当前命中仓库 .gitignore 的 tmp/ 规则。此次只整理本地文件，没有修改忽略规则、暂存、提交或推送。跨机器或远程分支读取前需要单独安排同步。
