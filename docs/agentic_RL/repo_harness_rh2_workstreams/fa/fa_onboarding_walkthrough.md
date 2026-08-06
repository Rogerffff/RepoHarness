# Fully Async 改造全景走读（onboarding，2026-07-20）

> 写给"几天没碰项目、对 slime fully async 和 rh2 链路都不熟"的读者（也就是
> 现在的你）。目标：读完后你能（1）在脑子里过一遍一次 rollout 的完整链路；
> （2）说清 fully async 改造在改什么、为什么改；（3）知道每个 FA 阶段的
> 完成状态和下一步。所有说法都锚在真实文件路径和已发生的数字上。
>
> 先澄清一件事：你在 IDE 里打开的 `src/repo_harness/rl/runtime.py` 属于
> **旧一代代码**（stage0~2 时期的 harness）。当前项目所有活跃代码在
> `rh2/` 目录下，包名是 `repoharness2`。旧目录只作历史参考，不要在那里找
> 现在的链路。

---

## 1. 项目在做什么：一句话与分层

**RepoHarness rh2 = 站在工业级训练框架之上的"环境生产 + 训练数据治理层"，
用一次真实的 coding agent RL 训练来证明它有效。**

分层地图（谁负责什么）：

```text
┌────────────────────────────────────────────────────────┐
│ RepoHarness rh2（本项目的差异化层）                      │
│   环境生产线：SWE 任务包构建、质量门槛、数据 ingestion    │
│   训练治理：EligibilityGate、capture 保真、反作弊、        │
│             版本/staleness 事实、batch 准入、faithful DIS │
├────────────────────────────────────────────────────────┤
│ slime（训练后端，reference/slime/）                      │
│   Megatron 训练 + SGLang 推理 + Ray 编排                 │
│   自带 agent 栈：AnthropicAdapter / TrajectoryManager /   │
│   ClaudeCodeHarness / fully_async_rollout                │
├────────────────────────────────────────────────────────┤
│ SGLang（推理引擎，slime patch 过：weight_version、        │
│   top-p tape、routed experts tape）                      │
├────────────────────────────────────────────────────────┤
│ 被训模型：Qwen3-30B-A3B（MoE）                           │
│ harness：Claude Code CLI 2.1.205（固定版本 + sha256 钉死）│
│ 任务：SWE（django 等真实仓库 bug 修复），docker 沙箱执行   │
└────────────────────────────────────────────────────────┘
```

核心叙事（简历角度）：训练框架会不断吸收 rollout 基础设施（slime 已经内置
了 coding agent 示例），但**环境的生产与质量治理、训练数据的资格治理**是
框架不发货的东西——rh2 钉死在这一层，并用一次真实训练闭环验证。

已完成的大阶段（细节见 `00-project-status.md`）：

- **P0~P3**：预实验。P3 在 8 GPU 上跑通了真实 preflight，产出了 J4/J5
  两组真实 batch 事件数据（后面反复用作测试夹具）。
- **S1**：batch-synchronous 的完整绑定链路（slime ↔ rh2 ↔ CC ↔ 评分），
  在真机验证过。这是 FA 改造的地基。
- **数据预处理 / S2-1**：SWE 任务 ingestion（另一条并行线程在推进，
  最近一次提交是"real 216/216 packages built"）。
- **FA（本文主角）**：把 S1 的 batch-sync 链路升级为 version-aware
  fully async 正式训练链。当前 FA-0/FA-1/FA-3 离线/FA-4 parity 已完成，
  FA-1 又经历了 8 轮 codex 审查修复（轮次 6~13），刚刚全部闭合。

---

## 2. 一次 rollout 的完整链路（先看 batch-sync 版，FA 在它之上改）

### 2.1 大图：三个系统怎么咬合

一次训练 step 的数据流（S1 batch-sync 形态）：

```text
slime 训练循环（Megatron）
  │ ①"给我 32 个 prompt 组的样本"
  ▼
slime RolloutManager ──(--rollout-function-path)──► rh2 的 rollout 函数
  │                                                    │
  │                                    ② 对每个组的每个成员：
  │                                    RolloutOrchestrator.generate(...)
  │                                                    │
  │                     ③ 起 docker 沙箱（django 仓库）+ 挂任务包
  │                     ④ 启动 Claude Code CLI（子进程，在沙箱里改代码）
  │                     ⑤ CC 的每次模型调用 → HTTP → adapter → SGLang
  │                     ⑥ CC 退出 → 收轨迹树 → 双沙箱干净评分 → Gate
  │                                                    │
  ▼                                                    ▼
  ⑦ 收 32 组样本（token/logprob/reward/tape）→ 转训练张量 → 更新权重
  ⑧ 权重同步到 SGLang → 下一个 step
```

**batch-sync 的含义**：第 ⑦ 步必须等**所有** 32 组全部跑完才开始训练。
一个组里 CC 跑 3 分钟，另一个跑 40 分钟（真实会发生：coding agent 时长
方差极大），GPU 就干等 37 分钟。这是 fully async 要解决的核心浪费。

### 2.2 三个执行域（理解后面所有并发 bug 的钥匙）

同一个 Ray rollout actor 进程里有**三个执行域**，codex 轮次 10~13 的
几乎所有 P0 都发生在它们的边界上：

```text
执行域 A：Ray actor 主线程
  slime 同步调用 rollout 函数入口（generate_rollout）

执行域 B：slime AsyncLoopThread（持久后台 event loop）
  FaRolloutService / ContinuousExecutionWorker /
  RolloutOrchestrator.generate / 沙箱操作 / 评分队列

执行域 C：aiohttp adapter 线程（独立线程 + 自己的 event loop）
  AnthropicAdapter 的 HTTP handler / ModelCallProxy /
  SGLang 请求 / capture 的 stage 和 commit
```

反例（真实修过的 bug，轮次 10 P0-1）：poison（判定某会话作废）发生在
域 C，要取消的 harness task 活在域 B。直接调 `task.cancel()` 是**跨线程
调用 asyncio API**——静默无效。正确写法是域 B 先记下自己的 loop，回调走
`owner_loop.call_soon_threadsafe(task.cancel)`。我们所有单元测试都在一个
事件循环里跑，所以这类 bug 全靠 codex 的双线程探针抓出来。

### 2.3 一次 Claude Code 模型调用的 HTTP 之旅（微观链路）

CC 在沙箱里决定"我要调一次模型"，之后发生的事（当前代码形态）：

```text
CC 子进程（沙箱内）
  │ POST /v1/messages（流式），Authorization: Bearer <sid>
  ▼
adapter 线程的 aiohttp app（glue.py 起在宿主）
  │ ①会话守卫 middleware：bearer 不在 registry / 已中毒 → 403
  │   + x-should-retry:false（绝不 404——CC 对 404 会绕过重试开关）
  │ ②404→503 middleware：任何路由 404 一律转 503
  ▼
BaseAdapter._run_turn（slime 代码）
  │ 组 prompt token ids，按名字解析模块级 call_sglang_generate
  ▼
rh2 替换版 call_sglang_generate（capture_wire.py，整函数替换 stock）
  │ ③未注册 sid → UnknownSessionError（fail-closed，不许直连引擎）
  │ ④poison.check(sid)：会话已作废 → 立即拒绝
  ▼
ModelCallProxy.call(execution_scope, turn_id, send_fn)   ← async_worker.py
  │ ⑤episode deadline 检查（预算耗尽不再发）
  │ ⑥等待训练窗口 ACTIVE（权重正在更新时不发）
  │ ⑦真正 POST SGLang /generate（return_logprob + top-p tape +
  │   routing tape 三个 flag 都在这里注入）
  │ ⑧响应必须带 meta_info.weight_version，否则 fail-closed
  │ ⑨若被权重更新 abort → 窗口内部重生成（详见 §4.3）
  ▼
CaptureRegistry.stage(sid, PendingTurn)     ← 只是"暂存"，还没算数
  │
adapter 把响应转成 Anthropic SSE 流，flush 给 CC
  │ ⑩CC 完整收到响应后，slime 调 record_turn 把这轮记入轨迹树
  ▼
CaptureRegistry.commit(sid)                 ← 这时才"提交"
    hook 收到 (prompt_ids, params, raw_response)，
    proxy 侧 finalize_delivered（两阶段定案：这轮真的交付了）
```

**为什么要 stage/commit 两阶段**（反例）：如果在第 ⑦ 步返回时就提交，
而 CC 在第 ⑩ 步前断连（响应没送到），轨迹树里**没有**这轮、capture 里
**有**这轮——后面按轨迹回填 token 时对不上账，训练数据就是错的。所以
提交点必须钉在 record_turn（上游依据：slime `_respond()` 先 await 响应
写出、再调 record_turn）。

### 2.4 orchestrator.generate 的九步（宏观编排）

`rh2/src/repoharness2/adapters/slime/generate.py` 的 `RolloutOrchestrator`
是单次 execution 的编排权威，大致九步：

1. 解析任务（instance_id → RolloutTaskSpec：镜像、prompt、评分脚本）；
2. 起 rollout 沙箱（租约先行、镜像 digest 校验、只挂 public 任务包——
   private 评分包挂进来会被 schema 直接拒绝）；
3. 开 adapter 会话（open_session：注册 capture hook；失败会回滚注册）；
4. 启动 harness（CC CLI 子进程；包成 asyncio task，poison 时可被
   call_soon_threadsafe 取消）；
5. harness 退出后：**先 finish_session（drain 所有在飞 HTTP turn）**，
   再做 poison 复检 / 非零 exit 拒绝 / 交付账边界断言 / 冻结 capture
   records 快照（这个顺序是轮次 13 P0-2 刚修正的）；
6. 装配轨迹：每条叶链回链 capture 轮次、检测上下文收缩（compaction
   兜底）、回填真实 weight_version；
7. 评分：**第二个干净沙箱**跑评分脚本（rollout 沙箱不可信——模型可能
   篡改测试）；
8. 投影 + EligibilityGate：产出资格结论（fully_eligible / audit_only_
   or_rejected），降级时发 GroupRepairSignal；
9. 返回 slime 形状的样本（保留 rollout_top_p tape 等字段），或 abort
   形状（remove_sample=True）；finally 里清理容器 → 清理确认后才归档
   poison → 写 execution 终态审计（fa_execution_audit.jsonl）。

---

## 3. slime 的异步模型：train_async vs fully_async

slime 有两档"异步"：

**train_async（S1 用的）**：rollout 和训练在 batch 粒度重叠——训练第 N
个 batch 时，第 N+1 个 batch 的 rollout 已经在跑。但 batch 内部仍是
"等最慢的那个"。

**fully_async（`reference/slime/slime/rollout/fully_async_rollout.py`）**：
rollout 侧持续不断地跑，攒够一个训练 batch 就交付，训练与 rollout 完全
解耦。数值直觉：

```text
假设 32 个组，时长分布 5~40 分钟（P3 真实观察量级）
batch-sync：每 step 耗时 = max(组时长) ≈ 40 分钟
fully async：GPU 每攒够 32 个"已完成组"就训练，
             吞吐由平均时长（≈15 分钟）决定，不由尾部决定
```

但 stock fully_async 有三个已确认缺陷（rh2 不用它裸跑的原因，都有
源码 pin 测试守着 `tests/contract_slime_async/test_fully_async_surface.py`）：

- **N1**：rollout task 抛异常时 done_callback 只打日志就返回——样本
  静默消失，账不平；
- **N2**：结果队列用阻塞 `put`——队列满时整个 reap 协程悬挂；
- **ABORTED 整组回队**：权重更新打断请求时，slime 把整组塞回队列重跑，
  且 assert 组大小 == n_samples_per_prompt（和我们的 fan-out 分叉轨迹
  不兼容）。

rh2 的做法：**不改 slime 源码**，用自己的 worker/proxy 层替代这三个
行为（见 §5 FA-1），slime 只负责训练引擎和推理引擎。

---

## 4. 为什么要 version-aware fully async（正式链的三个核心概念）

用户 2026-07-12 的定案：**正式训练链 = version-aware fully async +
faithful DIS**。三个必须吃透的概念：

### 4.1 三层身份（P3 的真实反例）

```text
PromptGroup（同题组）        ← GRPO 的 advantage 归一化单位
  └─ RolloutExecution ×n    ← 一次"起沙箱跑 CC"的执行，调度/计数单位
       └─ Branch ×k         ← 一次执行内的分叉轨迹（compaction/FORK 产生）
```

P3 真实数据点：`group_index=5` 的组，其中一个执行 `exec_22` 产出了
**8 条 branch**。三层都有各自的 id；混用会出什么事的反例：slime stock
按"组大小恒等于 n_samples_per_prompt"断言，遇到 8-branch 的执行直接
assert 崩——这就是"fan-out 形状必须在交付边界统一展平"的由来（FA-3 的
问题 C）。

### 4.2 权重版本与 staleness

fully async 下，rollout 进行中权重会更新好几次。每轮模型调用的响应都带
`meta_info.weight_version`（slime patch 的 SGLang 提供）。一条轨迹可能
跨版本：turn 1~3 用 v7 生成，turn 4~6 用 v8。训练时必须知道每个 token
是哪个版本的 policy 生成的——这就是逐 turn 记录版本、握手时算
`staleness = current - min(seen)` 的原因。反例（轮次 6 修过）：如果只
clamp 成 0，current=3 但看到 turn 版本是 5（不可能的未来版本）会被伪装
成健康——现在这种矛盾直接 fail-closed。

### 4.3 更新窗口 abort 与 D-FA-3"proxy 内部重生成"

权重更新的瞬间，SGLang 会 abort 在飞请求。stock slime 的做法是整组
重跑（见 §3 缺陷三）。rh2 的定案（D-FA-3）是把重生成收进 proxy 一层，
对 CC 完全透明：

```text
时间线：
  t0  CC 发起第 4 轮模型调用（attempt_1）
  t1  trainer 开始把权重 v7 → v8，SGLang abort 了 attempt_1
  t2  proxy 发现：中断与更新窗口重叠 + 响应未交付 → 不报错，
      留痕 attempt_1（non_delivered_aborted，记录 update_epoch/fence）
  t3  proxy 等待：窗口回到 ACTIVE 且版本**到达 abort 窗口的目标版本 v8**
      （同 epoch 要求 active==target；晚到的 epoch 要求 >=）
  t4  proxy 用同一个请求体重发（attempt_2，新的 SGLang RID）
  t5  attempt_2 成功 → 只有它的响应交给 CC；CC 全程只看到"一次调用"
```

为什么可行：slime adapter 是先拿到完整 /generate JSON、再伪装成 SSE 流
发给 CC（`common.py`），所以 abort 发生时 CC 还什么都没收到，重生成不会
产生"半截流"。守卫三元组：**重叠 ∧ 未交付 ∧ 版本已到达**，三者缺一就
走缺员（execution 作废），绝不透明重试。

### 4.4 faithful DIS（训练侧的正确性组件）

首训算法仍是 GRPO，但重要性采样修正按 SAO 论文（2607.07508）的忠实
实现：`r = exp(logπ_current − logπ_rollout)`，f(r) 在**开区间**
(1−ε_ℓ, 1+ε_h) = (0.2, 4.0) 内取 r、区间外取 0（token 被拒绝但**留在
分母里**）。具体数字例子：某 token 的 ratio=0.19 → 权重 0（贡献零梯度
但占分母）；ratio=0.21 → 权重 0.21。实现在
`rh2/src/repoharness2/training/faithful_dis.py`，用 torch autograd 建了
解析梯度 parity 权威（FA-4 的 Megatron 接线要对着它对拍）。

---

## 5. FA-0 ~ FA-5：每一步是什么、现在到哪了

计划权威：`05-fully-async-execution-plan.md`。状态速览：

| 阶段 | 内容 | 状态 |
|------|------|------|
| FA-0 | 运行时契约：ExecutionIdentity、RolloutAttemptOutcome、TrainingRuntimeWindow、ModelCallAttempt（`contracts/fa_runtime.py`） | ✅ 完成（P3 真实事件做夹具） |
| FA-1 | 持续 worker + proxy 边界 + slime 生产入口 | ✅ 完成 + **8 轮 codex 审查全部闭合**（详见 §6） |
| FA-2 | 第一批：**身份基座 F2-1~6**；第二批：PromptGroupAssembler 状态机 + 合格组队列 | ⬜ **下一步就是它** |
| FA-3 | SlimeBatchAssembler：batch 准入（问题 A~E）、reward 归一化、fan-out 展平 | ◐ 离线部分完成（`batch_admission.py`，对着 slime 真 `build_dp_schedule` 做差分测试）；接线等 FA-2 |
| FA-4 | faithful DIS 接 Megatron + 真 TrainingRuntimeCoordinator（consensus version） | ◐ parity 权威完成；真协调器未做（当前 StaticActiveCoordinator 只会保守缺员，**不会**真的透明重生成） |
| FA-5 | 故障注入 + 短租 GPU 真机验收（与 S2 G10 合并租一次） | ⬜ 验收清单已扩到 10 项增项 |

FA-1 的三个核心件（都在本地全绿的测试覆盖下）：

- `rh2/src/repoharness2/adapters/slime/async_worker.py`：
  `ContinuousExecutionWorker`（账目守恒：dispatched == delivered +
  failed + abandoned，sink 坏了会 run-halt 而不是漏账）、
  `BoundedDeliveryQueue`（非阻塞投递 + 反压计数，替代 N2）、
  `ModelCallProxy`（§4.3 的全部逻辑）、`SessionPoisonRegistry`
  （线程安全、active/archived 生命周期、订阅即取消）、局部重试白名单。
- `rh2/experiments/fa_bringup/rollout_entry.py`：slime
  `--rollout-function-path` 指向的生产入口薄壳（零 slime import，
  同步契约，eval 请求 fail-fast——eval 只走 before/after 标准路径）。
- `rh2/experiments/s1_7a_bringup/capture_wire.py` + `glue.py`：S1 链路
  的 FA 化改造（proxy 接入、两阶段 capture 事务、会话守卫、审计落盘）。

---

## 6. codex 八轮审查（轮次 6~13）到底在修什么：六类教训

FA-1 验收期 codex 提了大量问题、全部被采纳。不用逐条记，记住六类模式
（原文全部存档在 `s2/codex_reviews.md`，处置记录在本目录
`implementation-notes.md`）：

1. **修复没生效 + 测试假阳性**（轮次 9 P0-1，最深刻的一次）：轮次 8 用
   无 assert 的文本替换修 deadline 传参——替换静默没匹配上；配套测试又
   在进入目标分支**之前**就因预算不足退出，照样全绿。教训已固化成规矩：
   文本替换必须带 assert；修复测试必须证明"真走到了目标分支"（断言
   send 恰好一次、reason 精确匹配、时钟 ≤ deadline）。
2. **单事件循环测试 vs 三线程生产拓扑**（轮次 10 全部 4 个 P0）：跨线程
   `task.cancel()` 无效、registry 无锁竞态丢通知、middleware 只 patch
   了"未来的 adapter"而生产那个早就构造好了。现在有真 `threading.Thread`
   的压力测试（50 轮交错、200 轮 barrier 竞态）。
3. **fail-open 的默认值**（轮次 11/12）：sink 磁盘错误被吞掉退回内存
   引用（磁盘满时训练继续、证据悬空）；abandon 路径绕过统一 poison。
   修法都是同一个方向：正式链 fail-closed（sink_required、三层防线、
   启动 write/read/delete 探针）。
4. **生命周期时序错位**（轮次 11 身份 4 / 轮次 13 P0-2）：poison 归档挂
   在了 drop_session（容器还没清完）；边界检查放在了 drain 屏障之前
   （读到不完整快照）。修法：把每个动作钉到它语义上正确的时刻——
   release 在 cleanup_completed 之后，检查在 finish_session 之后。
5. **配置摆设 vs 真接线**（轮次 12/13）：`assert_adapter_status_not_404`
   只有测试在调、`rh2_fa_limit_model_call` 没有生产消费者、FA 路径根本
   不写审计文件。修法：每个配置/守卫必须指认它的生产消费者，接不上就
   删掉。
6. **身份复用与安全旁路**（轮次 11~13，通向 FA-2）：稳定 SID 跨 epoch
   复用与毒归档冲突；健康 SID 并发注册静默覆盖；未注册 SID 可以绕过
   全部治理直连 SGLang（未登记推理代理）。临时挡板已全部加上
   （fail-closed + 403 守卫），**根治 = FA-2 第一批的唯一身份**。

轮次 13 是收尾的**全链路审计**，结论原话："FA-1 不是失败实现……正确
行动不是回退 batch-synchronous，而是先关闭模型边界与 capture 事务 P0
→ 建立 FA-2 唯一身份 → 再实现 assembler"。五个 P0 已在同日全部落地
（commit `178cbdff`，测试 895 全绿）。

---

## 7. 当前未完成的事（按执行顺序）

### 7.1 FA-2 第一批：身份基座（下一个要写的代码）

| # | 内容 | 一句话 |
|---|------|--------|
| F2-1 | ExecutionIdentity 贯穿 | `fa_g3_m1` 这样的身份要从 task source 一路传到 worker→orchestrator→session→proxy→capture→评分→artifact→Outcome，消灭 orchestrator 用 task+index+group 重造稳定 SID（epoch 复用、artifact 覆盖的根源） |
| F2-2 | 身份与凭证分离 | 公开身份（可审计）与 `ANTHROPIC_AUTH_TOKEN` bearer（128-bit 随机、会话关闭即失效）拆开——现在模型能从自己 shell 里读到可推导的 SID |
| F2-3 | request 级 capture 归属 | `(execution_id, request_id)` 做键，替代"同 SID 并发就 fail-closed"的临时策略——CC 并行 subagent 是真实工作负载 |
| F2-4 | 预取恢复语义 | codex 探针：预取 7 组时崩溃 = 7 组永久跳题。三选一定案：checkpoint 含 RH2 状态 / data source lease-ACK / at-least-once + 去重 |
| F2-5 | collector 组不变量 | 组长度 == n、slot 0..n-1 无重复、重复投递拒绝、混合 branch 策略显式 |
| F2-6 | attempt→Outcome 血缘 | `drain_attempts`（已有）接 per-execution manifest，双向引用，退出前无 owner 检查 |

### 7.2 之后

FA-2 第二批（assembler 状态机 + 合格组队列）→ FA-3 接线（lease/ACK 批
组装）→ FA-4（真协调器 + Megatron DIS）→ FA-5 租 GPU 真机验收（清单含
10 条新增项，如"未知 SID 不达 SGLang""limiter=1 实测峰值 1""actor kill
后预取组不丢不重"）。P1×8 + P2×4 的递延项登记在 05 计划 §6.1 表格里，
FA-5 前逐项销案。

闸门：`rh2_fully_async_training_path_verified` 目前保持 **false**——
F2 身份基座完成前不许翻真；`StaticActiveCoordinator` 在位期间不得声称
"生产链已透明重生成"。

---

## 8. 读代码的建议顺序 + 常用命令

按依赖顺序读（每个文件头部的 docstring 都写了它的出处和决策编号）：

1. `rh2/src/repoharness2/contracts/fa_runtime.py` —— 先看契约（数据形状
   即设计）；
2. `rh2/src/repoharness2/adapters/slime/async_worker.py` —— proxy/worker/
   poison（§4.3 的实现）；
3. `rh2/experiments/s1_7a_bringup/capture_wire.py` —— 模型边界的替换点
   （§2.3 的第 ③~⑨ 步）；
4. `rh2/src/repoharness2/adapters/slime/generate.py` —— orchestrator 九步
   （最长的文件，对照 §2.4 读）；
5. `rh2/experiments/fa_bringup/rollout_entry.py` —— slime 入口薄壳；
6. `rh2/src/repoharness2/adapters/slime/batch_admission.py` +
   `rh2/src/repoharness2/training/faithful_dis.py` —— FA-3/FA-4 的离线
   权威；
7. 对照读 slime 侧：`reference/slime/slime/agent/adapters/common.py`
   （_run_turn / call_sglang_generate / finish_session）和
   `reference/slime/slime/rollout/fully_async_rollout.py`（三缺陷现场）。

常用命令（都在 `rh2/` 目录下执行）：

```bash
uv run pytest tests/ -q          # 全量测试（当前 895 passed）
uv run inspect-rh2-s1            # 账本校验（每次 commit 前必须 PASS）
uv run pytest tests/adapters/test_async_worker.py -q   # 只跑 proxy/worker
```

历史追溯：`s2/codex_reviews.md`（八轮审查原文）、本目录
`implementation-notes.md`（每轮的处置与设计决策）、
`05-fully-async-execution-plan.md`（计划权威，D-FA-1~7 定案在 §0）。
