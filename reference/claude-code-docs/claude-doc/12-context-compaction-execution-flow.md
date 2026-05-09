# 第 12 篇：上下文压缩管线的执行模型

本篇专门回答一个容易混淆的问题：**Claude Code 的多层压缩到底是怎么调度的？**

读完应该能回答：
- 每一轮模型调用前，是只跑成本低的层？还是把所有层都跑一遍？
- AutoCompact 是 microcompact 失败的兜底吗？
- 上下文 token 预算是「全局共享」的，还是每层各自有触发条件？

---

## 1. 一句话总结

> **每一轮模型调用前，整条压缩管线从头到尾跑一遍。每一层独立判断「我现在要不要真做事」，没人在等谁失败。**

不是"成本低的先试，不够再升级"——这是常见的误解。实际上：

- **轻量层（applyToolResultBudget / Snip / Microcompact / Context Collapse）**
  每轮都跑。它们检查的是**结构性条件**："有没有旧工具结果可以清"、"距上次 assistant 消息有多久了"、"工具结果的累计数量超阈值了吗"。**与当前 token 总数无关**，能清就清，机会主义运行。
- **重量层（AutoCompact）**
  每轮也跑。但它检查的是**总 token 数**：低于 167K（200K 模型）什么都不做，达到阈值才掏 LLM 写 9 段摘要。
- **兜底层（Reactive Compact）**
  只有 API 真的抛出 `prompt_too_long` 才触发。

**轻量层和重量层的关系是「上游/下游」**，不是「便宜的失败了就升级到贵的」。轻量层每轮都在勤奋清理，目的就是**让 token 增长得慢一点，让 AutoCompact 触发得晚一点**。

下面用一个具体例子让这个区分更清楚。

---

## 2. 一个具体例子：300 轮对话里压缩在做什么

假设 200K 上下文窗口的 Sonnet，AutoCompact 阈值 167K（= 180K 有效窗口 - 13K 缓冲）。

| 轮次 | tokens | 这一轮压缩管线做了什么 |
|---|---|---|
| 1 | 5K | applyToolResultBudget 检查 → 没大输出，跳过<br>Snip 检查 → 历史不长，跳过<br>Microcompact 检查 → 工具结果不多，跳过<br>AutoCompact 检查 → 5K 远低于 167K，跳过 |
| 50 | 60K | applyToolResultBudget → 一个 Bash 输出超 30K → **落盘换占位符**<br>Microcompact (cached 路径) → 已有 12 个旧 Read，超阈值 → **API 层删 7 个，本地不动**<br>AutoCompact → 60K 仍低于 167K，跳过 |
| 100 | 120K | Microcompact → 又积累了一些工具结果，**清掉一批**<br>AutoCompact → 还差 47K 才到阈值，跳过 |
| 180 | 165K | Microcompact → **持续清旧结果**<br>AutoCompact → 接近阈值，但还差 2K，跳过 |
| 181 | 168K | AutoCompact → **超阈值！触发 LLM 摘要 → 上下文压缩到 ~30K** |
| 182 | 35K | 重新开始积累，轻量层再次进入"勤奋清理"模式 |

注意第 50 轮——**applyToolResultBudget 和 Microcompact 同时各做各的事**，没有顺序依赖。Microcompact 也没有"等到上下文超 100K 才开始清"，它一开始就在跑，只是前几轮没有可清的旧工具结果。

---

## 3. 完整执行链（query.ts 主循环里的实际顺序）

打开 [query.ts:370-468](../../claude-code-typescript-src/query.ts) 看主循环每轮跑的代码。我把它简化成下面这张图：

```
每一轮模型调用前
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 1. applyToolResultBudget  (query.ts:379)               │
│    检查：单个工具结果是否超 maxResultSizeChars          │
│    动作：落盘到 /tmp，消息里只留路径占位符              │
│    成本：0（无 LLM 调用）                                │
├─────────────────────────────────────────────────────────┤
│ 2. snipCompactIfNeeded  (query.ts:403)                 │
│    检查：feature('HISTORY_SNIP') 启用 + 历史够长        │
│    动作：消息级裁剪，释放的 token 数会传给 AutoCompact   │
│    成本：0                                                │
├─────────────────────────────────────────────────────────┤
│ 3. microcompactMessages  (query.ts:414)                │
│    检查（两条独立路径，二选一）：                         │
│      a. time-based：距上次 assistant ≥ 60 分钟           │
│         → 替换旧 tool_result 内容为占位字符串           │
│      b. cached：工具结果累计数 > triggerThreshold        │
│         → 发 cache_edits 给 API，本地消息不动            │
│    成本：0                                                │
├─────────────────────────────────────────────────────────┤
│ 4. applyCollapsesIfNeeded  (query.ts:441)              │
│    检查：feature('CONTEXT_COLLAPSE') 启用                │
│    动作：把一段对话折叠成归档摘要（read-time projection） │
│    成本：低（fork 子代理，但有 prompt cache 共享）        │
├─────────────────────────────────────────────────────────┤
│ 5. autocompact  (query.ts:454)                         │
│    检查：tokens ≥ 167K（= 180K 有效窗口 - 13K 缓冲）     │
│    内部还做一次分支判断：                                 │
│      a. 优先尝试 Session Memory Compact（已有笔记？）    │
│      b. 不行再走 LLM AutoCompact（9 段摘要）             │
│    成本：高（一次完整 LLM 调用，~17K tokens 输出）       │
├─────────────────────────────────────────────────────────┤
│ 6. Blocking 检查  (query.ts:637)                       │
│    检查：tokens ≥ 177K（= 180K - 3K）                    │
│    动作：拒绝继续，要求用户手动 /compact                  │
│    （正常情况下 AutoCompact 已经处理过了）                │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   调用模型 API  (query.ts:659)
        │
        ▼
   如果 API 抛 prompt_too_long
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 7. tryReactiveCompact  (query.ts:1120)                 │
│    检查：API 错误响应 = prompt_too_long                  │
│    动作：按 API round 分组，丢弃最旧的若干组重试        │
│    最多重试 3 次                                          │
└─────────────────────────────────────────────────────────┘
```

每一层的"检查"都是一个独立的判断，不存在"上一层失败才进入下一层"的依赖。**正常情况下，1-4 每轮都跑且大概率会做点小事，5 通常只在长会话里偶尔触发，7 几乎永远不会触发**。

---

## 4. 各层简介：检查什么 + 做什么

> 每一层的实现细节、阈值、触发条件、具体例子见后续展开篇。这里只说"它在管线里扮演什么角色"。

### 4.1 applyToolResultBudget — 大输出落盘

[query.ts:379](../../claude-code-typescript-src/query.ts) → [utils/toolResultStorage.ts](../../claude-code-typescript-src/utils/toolResultStorage.ts)

每个工具有自己的 `maxResultSizeChars` 限制。比如 Bash 输出了 200K 行日志，超过限制，工具结果会被写到磁盘临时文件，消息里替换为：

```
[Tool result stored at /tmp/cc-results/abc.txt - read with FileRead]
```

模型需要时再用 Read 工具去取。这步严格说不是"压缩"，是"防膨胀"——单个工具调用就把上下文撑爆是常见事故源，落盘换路径让超大输出也只占百来 token。

### 4.2 Snip Compact — 消息级削减

[services/compact/snipCompact.ts](../../claude-code-typescript-src/services/compact/snipCompact.ts)

feature 开关 `HISTORY_SNIP` 控制。逻辑相对激进，在消息层面做裁剪。重点：**它释放的 token 数（`snipTokensFreed`）会向下传给 AutoCompact**（[query.ts:466](../../claude-code-typescript-src/query.ts)），这样 AutoCompact 才能正确判断"snip 已经省了 30K，我其实不用触发"——因为 token 计数读的是 protected-tail assistant 的 usage 字段，反映的是 snip 之前的状态。

### 4.3 Microcompact — 旧工具结果清理（最具代表性）

[services/compact/microCompact.ts](../../claude-code-typescript-src/services/compact/microCompact.ts)

只对 8 类工具的旧结果生效（Read / Bash / Grep / Glob / WebSearch / WebFetch / Edit / Write）。两条路径：

- **time-based**：距上次 assistant 消息 ≥ 60 分钟时触发。服务端 prompt cache 的 1 小时 TTL 已过期，反正全部 prefix 要重写，干脆先把旧工具结果的内容清掉，替换成 `[Old tool result content cleared]`，保留最近 5 个。
- **cached**：用 API 的 `cache_edits` 能力，告诉服务端"这些 tool_use_id 的结果删掉"，本地消息不动。**核心收益是 prompt cache 不失效**，下一轮请求大部分还是 cache hit，便宜 10 倍。

两条路径**互斥**：cache 是冷的（time-based 触发）就走 time-based；cache 是热的就走 cached。

### 4.4 Context Collapse — 折叠归档

[services/contextCollapse/](../../claude-code-typescript-src/services/contextCollapse/)

feature 开关 `CONTEXT_COLLAPSE` 控制。把一段已经"做完了的工作"（比如调试一个 bug 的 30 轮对话）折叠成一条归档摘要。它的特殊之处是**read-time projection**——折叠条目存在独立的 collapse store，每次进入主循环时通过 `projectView()` 重放折叠日志生成视图，主消息数组不动。这样跨轮次的折叠状态能持久。

放在 AutoCompact 之前是有意的：如果折叠后已经低于 AutoCompact 阈值，就不用做 LLM 摘要，**保留细粒度上下文比一坨摘要更有用**。

### 4.5 AutoCompact — LLM 真摘要（重量级）

[services/compact/autoCompact.ts](../../claude-code-typescript-src/services/compact/autoCompact.ts) + [services/compact/prompt.ts](../../claude-code-typescript-src/services/compact/prompt.ts)

阈值（200K Sonnet）：

```
有效窗口  = 200,000 - 20,000 = 180,000   留给摘要输出
触发阈值  = 180,000 - 13,000 = 167,000   达到就触发
阻塞硬限  = 180,000 - 3,000  = 177,000   拒绝继续
```

触发后：
1. **优先尝试 Session Memory Compact**（如果会话内已经在写笔记）→ 不调 LLM，直接拿现成笔记当摘要
2. **不行再走传统 AutoCompact** → fork 一个子代理，让它读完整对话，输出 9 段结构化摘要（主要请求、技术概念、文件代码、错误修复、问题解决、用户消息、待办、当前工作、下一步）

熔断：连续 3 次失败就停。注释里写了真实事故——某会话失败 3272 次，全球每天浪费 25 万次 API 调用（[autoCompact.ts:67-70](../../claude-code-typescript-src/services/compact/autoCompact.ts)）。

### 4.6 Reactive Compact — PTL 兜底

[services/compact/compact.ts:227-291](../../claude-code-typescript-src/services/compact/compact.ts)

只在 API 抛 `prompt_too_long` 时触发。按 **API round**（每次模型响应算一个 round）分组，从最旧的开始丢弃，直到累计释放量覆盖 API 报错里的 token gap。最多重试 3 次。

为什么按 round 而不是 turn？因为 tool_use 和 tool_result 的配对约束——一个 turn 里可能有多个 round，按 round 切才能保证不破坏配对。

---

## 5. 一个常见误解：「成本由低到高依次升级」

很多人会以为执行模型是这样的：

```
❌ 错误模型：
  上下文超阈值
    → 试试 microcompact（便宜）
    → 不够？再试 autocompact（贵）
    → 不够？最后 reactive compact（兜底）
```

但实际是：

```
✅ 实际模型：
  每一轮主循环开始时
    ├─ applyToolResultBudget 自己判断、自己干活      ─┐
    ├─ snip 自己判断、自己干活                       │ 各自独立
    ├─ microcompact 自己判断、自己干活               │ 没有依赖
    ├─ contextCollapse 自己判断、自己干活            │
    └─ autocompact 自己判断、自己干活                ─┘

  调用 API
    └─ 失败时 reactive compact 才介入（独立兜底）
```

**协作关系不是"失败升级"，而是"上游清理 + 下游摘要"**：

```
轻量层（每轮勤奋清）    →    AutoCompact 触发得越晚    →    省 LLM 摘要的钱
轻量层（不工作）        →    AutoCompact 触发得越早    →    更频繁 LLM 摘要
```

也就是说，轻量层做得好，AutoCompact 就少触发；但 AutoCompact 不是它们的"备份方案"。

唯一明显的"层间通信"是 **snip → autocompact 的 `snipTokensFreed`**：因为 token 计数有滞后，必须显式告诉 AutoCompact"我已经省了多少"，否则 AutoCompact 会误判。除此之外，各层都是独立的。

---

## 6. 后台记忆系统：和压缩管线并行的另一条线

压缩管线是「同步、阻塞、在主循环里」的。记忆系统是「异步、后台、在 stop hook 里」的。

```
主循环                          后台
┌──────────────┐               ┌────────────────────┐
│ 压缩管线      │               │ Session Memory     │
│ ↓             │               │  ├─ 每 5K token    │
│ 调用 API      │               │  │  或 3 工具调用 │
│ ↓             │               │  │  写一次笔记    │
│ 工具执行      │               │  └─ 笔记可被        │
│ ↓             │               │     AutoCompact    │
│ stop hook ────┼───触发───────►│     当摘要直接用    │
└──────────────┘               │                    │
                                │ Extract Memories   │
                                │  ├─ 主代理 turn    │
                                │  │  结束时         │
                                │  └─ fork 子代理    │
                                │     共享 prompt    │
                                │     cache 写       │
                                │     ~/.claude/...  │
                                │     /memory/*.md   │
                                └────────────────────┘
                                        │
                                ┌────────────────────┐
                                │ AutoMem (跨会话)    │
                                │  下次会话启动时    │
                                │  Sonnet selector  │
                                │  挑最相关的 ≤ 5    │
                                │  个文件注入        │
                                └────────────────────┘
```

三个机制简介：

- **Session Memory** ([services/SessionMemory/](../../claude-code-typescript-src/services/SessionMemory/))
  会话内 fork 子代理写 markdown 笔记。触发：累积 ≥ 10K token 后初始化，之后每增长 5K 或每 3 次工具调用更新一次。**最大价值是当 AutoCompact 真触发时，可以拿现成的笔记当摘要，省一次 LLM 调用**。
- **Extract Memories** ([services/extractMemories/](../../claude-code-typescript-src/services/extractMemories/))
  主代理 turn 结束时（stop hook 里），后台 fork 一个子代理扫描对话，把"应该跨会话保留"的信息（用户偏好、项目背景、外部系统指针等）写到 `~/.claude/projects/<path>/memory/*.md`。权限沙箱：只能读全局、写 memory 目录。
- **AutoMem 召回** ([memdir/findRelevantMemories.ts](../../claude-code-typescript-src/memdir/findRelevantMemories.ts))
  下次会话启动时，扫描所有 memory 文件的 frontmatter（name + description），让 Sonnet 当 selector 挑出与当前对话最相关的 ≤ 5 个，注入正文到系统提示词。**不是"全部记忆都注入"，是"按需召回"**。

记忆系统和压缩管线的关系：

```
记忆系统给压缩管线"喂数据"     →    Session Memory 笔记可被 AutoCompact 直接用
压缩管线给记忆系统"清场"       →    runPostCompactCleanup 重置 memory 文件缓存
                                    确保压缩后 InstructionsLoaded hook 重新触发
```

---

## 7. 关键不变量

不管哪一层做了什么，必须保持以下不变量：

1. **tool_use 必须配对 tool_result**
   所有压缩、所有重试、所有 PTL 兜底都不能破坏配对。Reactive Compact 丢弃最旧 round 后，如果新的首条消息是 assistant，会插一条合成 user 消息（[compact.ts:284](../../claude-code-typescript-src/services/compact/compact.ts)）。

2. **服务端 cache 与本地消息一致**
   cached microcompact 不改本地消息但发 cache_edits → 本地和服务端必须同步。time-based microcompact 改了本地消息 → 必须 `resetMicrocompactState()`（[microCompact.ts:517](../../claude-code-typescript-src/services/compact/microCompact.ts)），否则下一轮 cached 路径会试图删服务端不存在的工具。

3. **递归保护**
   `session_memory` / `compact` / `marble_origami` 三类 forked agent 是 querySource，永远不能触发 AutoCompact，否则会死循环或破坏主线程的 module-level state（[autoCompact.ts:171-183](../../claude-code-typescript-src/services/compact/autoCompact.ts)）。

4. **主线程 vs 子代理的状态隔离**
   `runPostCompactCleanup` 用 `isMainThreadCompact` 判断（[postCompactCleanup.ts:36](../../claude-code-typescript-src/services/compact/postCompactCleanup.ts)）。子代理压缩时不能动主线程共享的 module-level state（context-collapse store、getUserContext cache 等）。

---

## 8. 后续展开（待写）

本篇是入口图。每一层的细节、阈值、prompt 设计、踩坑案例放在后续：

- `13-microcompact-detail.md`：双路径具体逻辑、cache_edits 协议、`COMPACTABLE_TOOLS` 选取依据、占位符为什么是"[Old tool result content cleared]"
- `14-autocompact-detail.md`：9 段 prompt 全文、`<analysis>` 剥离、Session Memory Compact 的消息选取算法、熔断器设计
- `15-reactive-compact-detail.md`：API round 分组算法、PTL token gap 解析、20% 兜底回退、合成 user marker 的作用
- `16-session-memory-detail.md`：触发表达式、笔记文件结构、Compact 时的 messagesToKeep 计算、tool_use/tool_result 配对保护
- `17-automem-and-extract-memories.md`：4 类型分类原则、selector prompt、Trailing Run、forked agent 的 prompt cache 共享

---

## 9. 速查

| 层 | 每轮跑？ | 触发条件 | 成本 | 调用位置 |
|---|---|---|---|---|
| applyToolResultBudget | ✓ | 单工具结果超 maxResultSizeChars | 0 | query.ts:379 |
| Snip | ✓（feature） | 历史够长 + feature 开关 | 0 | query.ts:403 |
| Microcompact (time) | ✓ | 距上次 assistant ≥ 60 分钟 | 0 | query.ts:414 |
| Microcompact (cached) | ✓ | 工具数 > triggerThreshold | 0 | query.ts:414 |
| Context Collapse | ✓（feature） | feature 开关启用 | 低 | query.ts:441 |
| AutoCompact | ✓ | tokens ≥ 167K（200K 模型） | 高 | query.ts:454 |
| Blocking | ✓ | tokens ≥ 177K | - | query.ts:637 |
| Reactive Compact | ✗ | API 抛 prompt_too_long | 重试 3 次 | query.ts:1120 |
| Session Memory 写笔记 | 后台 | 增长 ≥ 5K 或 3 次工具调用 | 异步 LLM | stop hook |
| Extract Memories | 后台 | 主代理 turn 结束 | 异步 LLM | stop hook |
| AutoMem 召回 | 启动时 | 新会话启动 | Sonnet selector | setup |

记住核心：**每层都在每轮跑，但 99% 的轮次里只有轻量层真做了事，AutoCompact 一直在等 token 攒够。**
