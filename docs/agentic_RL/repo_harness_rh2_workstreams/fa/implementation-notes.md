# FA 工作流 implementation-notes（三节制）

范围：`05-fully-async-execution-plan.md` 的 FA-0~FA-5 实现期记录。每任务一节，
只记重要事项。

## FA-0 身份、版本与执行结果契约（2026-07-12 完成）

**交付**：`contracts/fa_runtime.py`（ExecutionIdentity / RolloutAttemptOutcome /
TrainingRuntimeWindow / ModelCallAttempt 四契约 + 三层身份与 mask 分离的模块级
定义）；真实 weight_version 管道（TurnTape/capture 记录逐轮透传 →
backfill 逐入训轮回填 → 握手 staleness 真实计算）；正式链启动断言；
`routed_experts_start_len` 扩展位（非 0 fail-closed）；D-FA-6 环境注入 helper +
上下文收缩检测；fully_async 表面契约测试 7 条。测试 647 → 684 全绿。

### 设计决策

1. **FA 契约注册走 CLI 聚合表**（`registry.EXTRA_SCHEMA_REGISTRY`），S1 核心
   registry 保持验收口径的 15 个冻结。`inspect_s1` 的收编对照相应改为
   "S1-9 五个是下界 + `rh2.fa.*` 前缀放行、未知前缀仍 FAIL"——S1 账本对
   S1 面的保护强度不变，FA 面归未来 `inspect-rh2-fa`。
2. **上下文收缩不加 gate 第八维**：七维是封闭枚举（`failed_dimensions`
   校验器拒绝未知名），加维度牵动 `GATE_VERSION`——而升版机制是 S2-0/S2-7
   的 TIER_CAP 解封职责，FA 不越权。改为**装配期 fail-closed**：
   `detect_context_shrink` 检出 → `SlimeBindingError("context_shrink_detected")`
   → 既有 abort 收口（`remove_sample=True`），语义同样是"轨迹退出基线"。
   检测默认只记录（`reject_context_shrink=False`，S1 行为逐字不变），
   正式 GRPO 基线配置必须置 True。
3. **fully_async 表面契约测试是源码级结构断言**：本地 venv 无 torch，
   slime 模块不可 import；文本 pin 足以在升级 pin 时抓住承重事实漂移
   （N1 吞异常形态、组长断言、阻塞 put、`_key`、pause/continue 端点、
   weight_version 记账）。行为级验证归 FA-5。
4. **weight_versions 回填语义**：逐入训轮真实值优先 → 缺失回退
   policy_version → 部分轮两者皆无则**整字段不写**（宁可无事实让 gate
   降级，不拼"真实+猜测"混合序列）。正式链（require_real_weight_versions）
   下任何入训轮缺真实值直接 fail-closed。
5. **staleness 真实计算只在正式链启用**（current − min(seen)，数值版本），
   S1 兼容路径恒 0/True 逐字不变——避免翻动 S1 已验收的握手 evidence 语义。
6. **consume-time 字段冻结禁令**：Outcome 的 `current_version_at_consume` /
   `worst_token_lag` 在 finalize 校验器强制 None；FA-3 assembler 消费时另行
   落账，不回写冻结记录。

### 偏离说明

- 计划原文写"上下文收缩 → gate 维度"，实现为装配期 fail-closed（理由见
  决策 2）；语义等价、机制不同，05 计划不改文（该节本就写的是目标语义）。
- "DISABLE_COMPACT inspector 探针在本地 harness 冒烟中验真"以 **stub 子进程**
  实现（`test_compaction_disabled_env_reaches_child_process`：env 准备 →
  子进程读回 `SLIME_AGENT_CC_EXTRA_ENVS`）；真实 CC 子进程的验真按计划
  挂 FA-5 短租。glue 的实际接线（在 GPU 机器的启动路径调用
  `ensure_claude_code_compaction_disabled`）留 FA-1——本地无法冒烟真实
  glue 路径，helper 与探针已就绪。
- `RolloutAttemptOutcome` 本任务只交付契约与测试，编排循环的发射接线归
  FA-2（PromptGroupAssembler 是它的消费者，先有消费者再接生产者）。

### 权衡

- 三层身份暂未强制挂进 TrajectoryProjection（会动 S1 冻结契约的必填面）；
  FA-1/FA-2 接线时以 sidecar/metadata 承载，投影 schema 是否升版随
  FA-2 定。
- `BackendHandshake` 未加 `attempt_outcome_ref` 字段（codex 轮次 3 曾建议
  方向）：等 FA-2 的 Outcome 发射点定了再挂引用，避免先造空字段。

### 开放问题

- `context_shrink_ratio=0.6` 是预注册黄线，FA-5 用真实 CC 轨迹校准
  （thinking 剥离的真实收缩幅度分布未实测）。
- P3 夹具往返测试依赖本地 evidence 目录（浅 checkout 自动 skip）——
  `inspect-rh2-fa` 建账时把该测试列为必跑项（evidence 在库，正常 clone
  不会 skip）。

## FA-0 follow-up（2026-07-12，codex FA-0 审查全 12 项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 4）

- **严重 1（staleness 事实矛盾被 clamp 掩盖）**：`max(current-min(seen), 0)`
  的 clamp 删除——任何 seen 版本比 current 新即
  `weight_version_ahead_of_current` fail-closed（codex 反例 current=3/
  seen=[5] 现在必炸）。新增 `current_policy_version_provider` 注入点
  （FA-1 接 `engine.get_weight_version` 包装）；provider 缺席时回退
  config 值，注释明确该口径是"相对启动版本"、不得称实时 staleness。
- **严重 2（session 级收缩检测误杀子 agent）**：核实 CC 子 agent 与主
  agent 共享 session id（`claude_code.py` ANTHROPIC_AUTH_TOKEN=session_id
  → adapter 按 token 归组）。重构：session 级检测降为纯 audit 信号；
  **硬拒绝只在叶链自己的入链轮序列上执行**（lineage 内比较，子 agent 是
  独立叶链天然免疫）。负测试：主 agent 长上下文 + 子 agent 短上下文不拒；
  真 e2e：叶链内坍缩 → abort 形状 remove_sample=True。已知边界（诚实
  记录）：compaction 延续分支若经 REALIGN 把压缩前轮全部掉落，叶链级
  检测也看不见——正式基线的完整防线 = DISABLE_COMPACT 验真 + session
  级 audit 信号复核 + 叶链级硬拒绝三层，缺一不可。
- **严重 3（评分枚举统治执行期归因）**：新增 `RuntimeFailureCategory`
  13 值（proxy/推理服务/沙箱/harness/worker/评分基建/capture/对齐/
  staleness/安全/身份/契约/清理），`RolloutAttemptOutcome.failure_category`
  改用之；评分故障映射 grading_infra_failure + evidence 回链 GradingReport。
- **一般项**：present 强制 `current_version_at_finalize`；窗口
  old==target 拒绝（无前进的更新窗口是事实矛盾）；delivered attempt 强制
  weight_version；aborted attempt 加 `abort_fencing_token`（窗口归因双
  凭据）；`shrink_ratio` 域校验 (0,1) 开区间；正式链启动断言强制
  `reject_context_shrink=True`（不再只是注释）；混合序列注释改为精确
  两档口径（正式链 100% 真实、非正式链允许显式回退混合）。
- **测试项**：pin 守卫测试（reference/slime HEAD 必须 e848052a，在场即
  校验；缺席仍 skip，`inspect-rh2-fa` 建账后升为 fail）；误名的收缩测试
  重写为真 e2e（orchestrator 全链 + remove_sample 断言）+ audit-only
  对照。测试 684 → 692。

## FA-3 离线部分（2026-07-12 完成；接线部分待 FA-2）

**交付**：`adapters/slime/batch_admission.py`（预检器 + 层次化归一化 +
三视图纯函数）+ P3 事件夹具加载器 + 21 条测试（单元 15 + 差分 6）。
测试 692 → 713。

### 设计决策

1. **差分测试是预检器的正确性权威**：slime `utils/dp_schedule.py` 模块
   自述纯 Python、CPU-only 可测——差分测试直接 import **真函数**，同一
   输入比对成功/失败类别 + step 数 + 每 rank microbatch 数三项（J4/J5
   夹具 + 200 例随机扫，seed 固定）。预检器镜像 first-fit 装箱与对齐
   判定；`balance_by_flops`/`balance_data` 未镜像（P3/首训均关闭），
   开启即 fail-closed 拒绝——防止镜像面静默失真。
2. **B 类失败的机制确认**：J5 gbs16 的 "could only produce 23 mbs;
   need 24" = step0 恰 23 个样本（前 16 个有效 rollout 的真实 fan-out
   分布，事件元数据核实）+ align_to=dp2×1=2 + K0=23（全单箱）→
   round_up(23,2)=24 > 可拆分上限 23。夹具结构 100% 真实；样本 token
   总长不在事件元数据里（.pt 未同步），用校准值 20000 保持全单箱——
   报错里的 23/24 两个数字由结构决定，与校准值无关（测试 docstring
   已声明口径）。
3. **归一化实现放 adapter 纯函数层**（不进契约、不碰队列）：五条 E
   不变量以构造保证 + 属性测试钉死；广播不一致/身份矛盾 fail-closed。
   group5×8branch 定向回归直接吃 J4 真实事件（8 branch = 1 execution，
   分母 = 8 branch token 和）。
4. **torch 加入 dev 依赖组**（torch 2.13 CPU）：dynamic_filter 真调用
   测试（P3 崩溃形状复现 + 平铺形状通过）与 FA-4 torch 对拍都需要；
   运行时依赖面不变（只进 dependency-groups.dev）。

### 偏离说明

- 05 计划离线验收 5 要求 dynamic_filter 与 `_key` 都做真函数直接单测：
  **`_key` 的真调用做不到**——import 链穿 `sglang_rollout`（需要 sglang/
  ray，本机不装）。dynamic_filter 真调用已做；`_key` 保持源码级 pin
  （test_fully_async_surface），真调用留 FA-1 的 GPU 环境。如实降级，
  不冒充。

### 开放问题

- J5 gbs20 对照在预检器下 num_steps=1（41 样本中后 9 个 rollout 不足
  第二个 step 被真函数同款丢弃）——"尾部 rollout 静默丢弃"是 stock
  语义，FA-3 接线的 assembler 必须把它变成显式记账（丢弃即 log）。

## FA-4 对拍部分（2026-07-12 完成；custom loss 接线待 GPU 环境）

**交付**：`training/faithful_dis.py`（参考 loss + 解析梯度 + 指标）+
11 条对拍测试。测试 713 → 724。

### 设计决策

1. **三方对拍**：手算逐位 / 冻结权重有限差分（专测 detach 语义——若实现
   忘了 detach，接受 token 上必失配）/ torch autograd 同构实现
   （`ratio.detach()`，loss 与逐 token 梯度 1e-9 容差逐位）。torch 同构
   函数就是未来 Megatron custom loss 的形状雏形与对拍权威。
2. **denominator 语义预注册 v1 = provenance_tokens**（被拒 token 留分母、
   梯度为零）：与 slime stock TIS 的 `rollout_mask_sums` 口径一致，使
   IcePop 近似对照可同分母比较；`accepted_tokens` 第二实现保留用于消融。
   **FA-4 接线时须对照论文原文最终定死并回写**（codex 轮次 3 #7 的
   预注册要求——两档差异测试证明它直接改变有效学习率，不能含糊）。
3. ε 区间 0.8/3.0 按 codex 引注写入常数并标注"接线时对照原文复核"；
   区间语义 = 闭区间（边界测试用实际 ratio 值构造，避开 exp/log 浮点
   回环的 1ulp 假失败——这是实现细节里唯一踩过的坑）。
4. 全零有效 token → `zero_grad_step=True` + loss 0 + 无除零：FA-4 接线
   的"跳过 optimizer step"信号在参考层就位。

### 开放问题

- 论文忠实性只到"公式语义"层：ε 数值、denominator 档位、以及 top-p
  replay 是否参与 current logprob 计算（对拍清单第 5 项）都要在接线时
  对照原文/实测定死——参考实现把每个自由度做成显式参数，就是为了那时
  不需要改结构。
