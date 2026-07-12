# slime fully_async 升级设计（四缺口实现分析 + 机制知识沉淀）

日期：2026-07-08。定位：P3 预注册升级档（分离 + fully_async + 自建三件）的**实现设计文档**——只分析不写代码；同时把三轮 slime 源码调研的机制知识持久化（此前散在对话与 task 输出中，易失）。触发条件不变：J4b 或首训实测 rollout 尾部空闲 > 每步墙钟 25%。

> **2026-07-12 修订说明**：P3 已实测 `wait_time_ratio=0.82`、J4/J5 rollout 尾部空闲 26%～28%，升级条件已经满足。fully async 不再只是“首训后按需开启”的可选档，而应成为正式长预算训练前的主链改造。本文原先把 batch schedule preflight 描述为“必须先做、fully async 不应等它”，需要区分逻辑和接线顺序：预检算法可并行离线开发，但正式接线应先有 continuous worker → RH2 finalize → PromptGroupAssembler → QualifiedPromptGroupQueue，再由 SlimeBatchAssembler 调用 `build_dp_schedule` 预检和换组。详见 `../fully_async_rollout_pipeline_design_discussion.md` 的 2026-07-12 修订；`04-s2-execution-plan.md` 尚未据此重排。
>
> **本轮决策对旧建议的取代关系**：正式链直接采用 version-aware fully async + faithful DIS，不再把 session-pinned policy、bounded async/update barrier 或 TIS/IcePop-style 近似当作候选主方案。首版也不实现同 prompt 成员补采。本文下方关于 starts-over 后自动补采、依赖补采的 dynamic filter，以及“turn 级 mask + TIS”推荐组合，保留用于解释当时如何发现 slime 缺口，但已经被新的独立 FA 工作流取代，不能直接转写为实施任务。

所有 `file:line` 相对 `reference/slime/`，基于 pin `e848052a`；上游影响见 §2。

## 0. 结论先行

```text
1. 升级可行，总工作量 ~7-9 人日（不含真续跑；含真续跑 12-16 人日），
   四缺口中三个可落我方 adapter 层或极轻 core 改动。
2. 反转性发现：README "starts over" 对标准 generate 路径不准确——
   token 级续跑静态可证会生效（reuse_existing_input_ids 链）；但我们的
   custom_generate 完全绕过该机制，续跑与否由我方代码决定。
   缺口① = 在我方 custom_generate 写 resume 分支，不是等上游。
3. 缺口①升级为正确性问题：starts-over 有系统性长度偏置
   （短轨迹更易在权重更新间隔内完成——DeepSeek-V4 不变量的 slime 版）。
   当前定案是终止该 execution、把所属 PromptGroup 记为缺员并继续创建新组；
   不从头重跑该成员，也不做同 prompt 成员补采。
4. 新发现一个隐性 bug 风险：fully_async worker 的 task 崩溃时样本
   静默泄漏（不进 queue 也不回 buffer），长训练累积后某些 prompt
   永不被训——升级时必须兜底。
```

## 1. slime 异步机制知识汇总（三轮调研沉淀，file:line 为证）

```text
放置与档位：
  --colocate 强制同步（train_async.py:11 断言禁 colocate）；
  分离放置一等公民（--rollout-num-gpus 独立指定，arguments.py:1858-1894；
  引擎数 = rollout_num_gpus ÷ per-engine TP，须整除，http_utils.py:201-210）。
train_async 双缓冲时序（train_async.py）：
  :31 预启下一轮 generate → :34 等上一轮 → :38 先启下一轮 → :49 训当前 →
  :65-69 按 interval 先 drain 再 update_weights（"防止更新发生在生成中途"）。
  结构性 staleness ≈ 1 × update_weights_interval。
fully_async worker（rollout/fully_async_rollout.py）：
  进程级单例（:49/:56-62），后台线程 + 独立 asyncio loop（:115-167）；
  max_concurrent = sglang_server_concurrency × 引擎数（:59）；
  loop = reap（:126-133）+ top-up get_samples(1)（:136-152）+ 1s poll（:154）；
  ABORTED 组整组回 data_buffer（done_cb :183-188），正常组进 output_queue
  （maxsize=1000，阻塞式 put，:85/:189）；消费侧收满 batch 即返（:194-248）；
  worker 不参与 abort/pause——权重更新对它透明，靠引擎侧兜底；
  eval 模式直接 raise（:254-255）。
权重更新（update_weight/*.py）：
  统一时序 pause_generation → flush_cache → 发权重（带 weight_version）→
  continue_generation（tensor 路径 :156-190；distributed 路径 :110-133）；
  colocate=CUDA IPC，分离=NCCL 跨 PG broadcast；
  --update-weight-buffer-size 默认 512MB（arguments.py:515，MoE 关键旋钮）。
版本记账：
  Sample.weight_versions: list（types.py:120），每次 append_response_tokens
  收到 finish_reason 记一条（:381-382）——粒度 = 一次 /generate 一段，
  非 per-token；全仓无任何下游消费（mask/准入都要新写）；
  _convert_samples_to_train_data 不透传（ray/rollout.py:735）→
  采集必须在 projection 层（S1 交接 H-1 已定）。
  current version 在 rollout 侧唯一来源 = engine.get_weight_version
  （sglang_engine.py:363-369）；训练侧 weight_updater.weight_version
  不跨进程可见。
partial rollout（标准路径专属，sglang_rollout.py）：
  abort 收集 + start_rollout_id 标记（:357-368）→ 回灌 buffer（:637-639）；
  重入时 reuse_existing_input_ids（:46-60）token 级续跑；
  mask-offpolicy 在 generate_and_rm 入口把旧 response loss_mask 清零（:231-232）；
  组完整性由 add_samples 断言保证（data_source.py:206-209）。
动态采样（标准路径专属）：
  dynamic_filter + over_sampling 全在 generate_rollout_async（:394-440）；
  fully_async 路径零调用（静默失效）。
buffer_filter 插入点：
  data_source.py:172-175 注册、:195 调用——注意调用时 rollout_id 传 None，
  默认 pop_first（:225-229）。
```

## 2. 上游动态（pin e848052a → origin/main 领先 8 commit，2026-07-08 fetch）

| commit | 影响 | 处置 |
| --- | --- | --- |
| **680824dd** `routed_experts_start_len` | **高**：routing tape 支持中段偏移拼接（`expected_rows = len(tokens)-1-start_len` + `torch.cat` 中段拼接，types.py:352-369）——**续跑场景的 tape 基建**，也改变 tape 归一化契约 | ① S1-3 的 tape 归一化留 start_len 扩展位（现在留位一行事）；② 若做真续跑必须 cherry-pick |
| **c7487788** `--release-train` | **中**：新增每步 update_weights 分支（train_async.py:39-69）——若启用，缺口②的跨版本盲区急剧恶化 | 只有真实 weight version、逐 token faithful DIS 和 staleness 验收通过后才能启用；TIS 不能作为正确性兜底 |
| **2d909df5** cleanup | 排雷项：删 ppo_utils.py 63 行等 | 升级 rebase 前精读 diff 确认未删依赖 API |
| 474861aa /pull_weights、f27ef35c source_names、3× docker patch | 低/无 | 记录即可 |

F6 纪律的第一个真实案例：pin 之后上游确实在动我们的契约面，升级必须走契约测试先行。

## 3. 四缺口实现设计

### 缺口① partial 续接（正确性问题，非纯吞吐）

**新确证**：ABORTED 组回收全程不重置状态（done_cb `:183-186` → add_samples → pop_first 原样弹回，tokens/status/loss_mask 保留）；标准 generate 路径重入**确定真续跑**（`generate_and_rm:235` 不短路 ABORTED + `generate:162` 允许入场 + `reuse_existing_input_ids:46-60`）；**custom_generate 路径完全绕过**（`:251-259` 直接 dispatch）——我们的 SWE agent 是否续跑由我方代码决定，最坏组合是"带旧 token 但 agent 重开沙箱从头跑"（旧 token 悬挂）。

**长度偏置评估**（starts-over 系统性偏短：短轨迹更易在更新间隔内完成，长尾饥饿 + stale 污染）：

| 选项 | 偏置 | 结论 |
| --- | --- | --- |
| 真续跑 | 近无偏 | 最优但最贵：需缺口② mask 配合 + **沙箱中间态恢复**（token 续跑对沙箱 agent 意味着 checkpoint/restore workspace，代价可能高于重跑） |
| starts-over（现状） | 最差 | 尽快废弃 |
| 终止 execution + 缺员组不准入 | 不重复旧轨迹，也不把新采样伪装成重试 | **首版定案**：持续创建新的 PromptGroup，不做成员补采 |

正式接线（若长轨迹占比证明必要）：我方 custom_generate 开头加 resume 分支（判 `status==ABORTED ∧ tokens ∧ metadata.start_rollout_id`，30-80 行 + agent 中间态序列化）+ done_cb 补 start_rollout_id 标记（~5 行碰 core）+ cherry-pick 680824dd。

### 缺口② mask-offpolicy 盲区

**物理根因确证**：weight_version 每段记一条、无 token 级边界（types.py:381-382）——单次 generate 内的 pause/continue 跨版本边界在 meta_info 里不存在，token 级 mask 需 SGLang patch（不现实）。

**但对我们的多轮 SWE agent 有一个关键利好**：每轮 = 一次 /generate = 一次 append = 一条 weight_versions 记录，**段边界我方 custom_generate 完全掌握** → **turn 级版本感知 mask 在 projection 层可行**（~50-100 行，零碰 core），盲区收窄到"单轮内部跨版本"。

**当前定案**：逐次模型调用记录 rollout logprob、weight version 和 token span；训练时基于 current/rollout ratio 执行 faithful DIS，并对缺少 provenance、比率不可计算或过度陈旧的 token/轨迹 fail closed。turn 级版本边界仍是必要输入，但不再以“mask + TIS 兜底”替代 faithful DIS。slime 的 `--use-tis`（arguments.py:1047）只保留为后续小规模近似对照，不是正式训练主链。**前置验证**：实测跨版本 token 比例，并逐 token 对拍 DIS 比率、裁剪、拒绝原因和最终 advantage。

### 缺口③ 动态采样失效

**关键确证：新组持续供给在 fully_async 下天然成立**——worker top-up 的 `get_samples(1)` 在 buffer 空时自动落到全局 prompt 数据集读取新的 prompt group（data_source.py:177-189）。这里是“创建新组”，不是为残缺组补一个同 prompt 成员，二者必须在指标与 lineage 中分开命名。

**当前定案**：RH2 单轨迹 finalize 与 PromptGroupAssembler 在进入 qualified queue 前完成资格判断；残缺组不进入在线 ready queue，worker 继续创建新组。不能把动态过滤写成“丢一条后自动补回同 prompt 成员”，也不能在 slime 消费侧才第一次暴露治理拒绝。

**P3 实测扩充（2026-07-09）：fan-out 假设破裂点 = 两处，不止 dynamic_filter。** J4c 实跑发现 slime **消费侧排序** `_key`（`fully_async_rollout.py:238`）对我们的 fan-out 嵌套形状 `list[list[Sample]]` 同样崩溃——`getattr(list, "index")` 拿到 `list.index` 绑定方法 → `int()` TypeError（诊断补丁：递归展平 + callable 防御，见 `remote_evidence_20260708/preflight_evidence/j4c/slime_fully_async_key_diagnostic_patch.py`）。根因与 dynamic_filter 崩溃相同：**slime 标准路径与 fully_async 路径都假设平铺 `Sample`，我们的 fan-out `list[Sample]` 系统性破坏该假设。** 升级实施必须把"**fan-out aware 的样本展平/排序**"作为独立工作项（覆盖 dynamic_filter、`_key`、以及未来任何按 sample 属性索引/排序的消费点），不能逐点打补丁。

### 缺口④ staleness 准入

**关键障碍确证**：buffer_filter 调用时 `rollout_id=None`（data_source.py:195）且拿不到 engine 句柄——**current policy version 无现成管道**。两个方案：(i) worker top-up 时缓存 `engine.get_weight_version`（~20 行碰 worker）；(ii) 用 buffer 内最大版本近似 current（零管道但偏旧）。推荐 (i)。

准入形态：由 FA 运行时把 current policy version 传到逐 token DIS 与组级 staleness gate。无法校正或超过预注册阈值的轨迹被拒绝进入 qualified queue；不回收重跑，也不触发同 prompt 成员补采。`buffer_filter` 可以作为 slime 侧的第二道防线，但不能成为 policy version 与拒绝事实的唯一权威。

### 边界澄清（2026-07-09 P3 教训）：fully_async 不解决 batch schedule 非法

fully_async 升级解决的是 **rollout/trainer overlap 与长尾空闲**（P3 实测 J5 gbs20 尾段 28%，升级阈值已经触发）。它**不自动解决**“治理过滤后可训练样本数/microbatch 数无法对齐 `dp_size × mb_group`”的问题——那是 slime `build_dp_schedule` 的调度约束，与同步/异步本身正交（P3 formal J4 与 J5 gbs16 都死在这，J5 gbs20 靠改 batch size 碰巧对齐才过）。因此 batch schedule preflight/repair 仍是独立的 adapter 层能力；但实现接线顺序应修正为：先让 fully async 的 per-execution finalize 结果进入完整组 ready queue，再由 BatchAssembler 对 ready groups 进行预检、换组或等待。单独提前实现 predictor 只能更早报错，不能制造缺失 rollout，也不能替代 ready queue 选择。

## 4. 未注意点（四缺口清单外，本轮新扫出）

```text
N1 task 崩溃样本静默泄漏（重要）：done_cb 里 task 异常只 log 后 return
   （fully_async_rollout.py:172-175），样本不进 queue 也不回 buffer——
   长训练累积后部分 prompt 永不被训。升级时 done_cb 必须加异常兜底
   （回收进 buffer 或至少计数告警）。可考虑给 slime 上游提 issue。
N2 output_queue 阻塞死锁点：put 是阻塞式（:189），消费侧长时间不 drain
   → worker 线程卡死在 put → reap/top-up 全停。监控 queue_size。
N3 worker 1s poll（:154）：SWE 分钟级任务可忽略；升级档若混短任务
   需降到 50-100ms 或事件驱动。
N4 eval 干扰：eval 走标准同步路径不受 fully_async raise 影响（主判据
   评测安全），但 eval 与后台 worker 共享引擎与全局 semaphore
   （sglang_rollout.py:95 SingletonMeta）——eval 时延会被后台 rollout
   干扰，正确性无损；评测配置严禁误配 fully_async rollout function。
N5 组完整性不变量：add_samples 断言组长（data_source.py:206-209）——
   未来任何 sample 级（非组级）过滤都会破坏它，过滤一律组级。
N6 worker 崩溃恢复：线程死亡会重建（:56），但 in-flight 与 buffer 内
   回收样本随旧 event loop 丢失——长训练需外层对账（prompt 覆盖率审计）。
```

## 5. 触发升级后的实施顺序

旧的“四缺口顺序”已经被独立 FA 工作流取代。权威顺序以 `../fully_async_rollout_pipeline_design_discussion.md` 为准：

```text
FA-0  冻结异步契约、版本语义和结果分类
FA-1  continuous worker、队列、背压和退出语义
FA-2  RH2 finalize、PromptGroupAssembler 与完整组准入
FA-3  qualified ready queue、BatchAssembler 与 build_dp_schedule 预检
FA-4  weight version、逐 token faithful DIS、staleness 与数值对拍
FA-5  故障注入、监控和短租 GPU 端到端验收
```

必须实验验证（静态不可判）：custom_generate 对 ABORTED 的实际行为、跨版本 token 比例、current policy version 传播延迟、faithful DIS 数值对拍、engine.get_weight_version 调用开销、N1 泄漏实际发生率，以及 ready queue 在残缺组与长尾并存时是否持续供给合法 train batch。

## 6. 对当前阶段的三条即时影响（不等升级触发）

```text
I-1 S1-3 tape 归一化留 routed_experts_start_len 扩展位（上游 680824dd
    已改契约；现在留位一行事，随 §8/H 系列交接给执行线）。
I-2 J4c 判定口径可以更精确了：标准路径续跑已静态确证，J4c 的真正
    未知只剩"我方 custom_generate 对 ABORTED 的行为"——验证点收窄为
    在 custom_generate 入口打点 sample.status / len(tokens) /
    response_length 三元组。
I-3 首训监控加一项：queue_size 与 task 异常计数（N1/N2 是双缓冲档
    也可能间接暴露的问题面，监控成本一行）。
```
