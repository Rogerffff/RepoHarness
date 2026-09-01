# Miles + RH2 正式首训就绪范围

日期：2026-09-01

状态：**讨论稿，待 Owner 确认；不修改任何现有闸门或启动语义**

> **2026-09-01 显著提示**：后续执行以
> `docs/agentic_RL/repo_harness_rh2_workstreams/06-first-training-local-execution-plan.md`
> 为准——06 是**待 Owner 批准的替代提案**（Claude 起草 + codex 三轮复核）。06 的 §6 防御清理
> 提议删除本文 §0.2/§5.1 的授权公式、qualification manifest 与闸门代码化方案（owner 拍板
> 06 决策包 A 后生效）；本文其余缺口分析（四个实现级缺口、campaign 分段、"明确不做"清单）
> 已被 06 收编为 W 包。本文保留作范围论证的历史依据，不再单独执行。

本文回答一个比 `gpu_spike_scope.md` 更强的问题：

> 在不继续建设 Slime 自有异步流水线的前提下，当前 RH2 + Miles 还要完成
> 哪些本地工作和八卡验证，才能让下一次 GPU 租期结束后，训练基础设施已经
> 具备正式首训条件；以后选定首训数据和实验参数时，不再补一次训练后端集成？

本文只确定范围和完成标准。机器供应商、镜像制作、拓扑参数、任务清单、启动
命令、阈值和验收器实现仍在下一轮反向设计。现有 `launch.sh`、
`thresholds.md`、`positive_control.md`、`g1_acceptance.py` 和旧 G1/G2/G3
编号不自动继承。

本文建立在当前 `miles-migration` 分支和
`reference/miles-rh2-integration` 的代码事实上。旧计划和状态文档有未及时
更新之处，例如 S2 数据 ingestion 已经产出 216 题可信包，但
`00-project-status.md` 仍概括为“尚未开工”。以下判断以代码、最新阶段记录和
真实消费点为准。

---

## 0. 总结论

### 0.1 可以只租一次八卡，但现在还不能直接租

建议把下一次 GPU spike 直接升级为：

```text
Miles FA 核心资格
+ fa_formal 正式评分与训练准入资格
+ 最小安全链资格
+ 正常关停资格
+ checkpoint 冷恢复资格
+ before/after eval 运输资格
+ 首训成本与容量资格
= 正式首训基础设施资格作业
```

这些内容可以在**同一次租期、多个全新进程的作业段**内完成，不需要先做一次
Migration-Go，再为 FA-5 或冷恢复另租一次卡。

但 Claude 草案中“剩下的大头不是实现工作，而是验收与闸门定义”这一判断过于
乐观。当前至少还有以下真实生产链缺口：

1. Miles 派发路径没有写 `fa_formal` 强制要求的 RH2 四层身份；
2. RH2 产出了 `training_eligibility_class`，Miles buffer/trainer 却没有把
   `online_policy_loss_eligible` 当作训练准入条件；
3. bring-up 仍只加载 S1 的 8 道探针题，且
   `environment_package_digest=None`；
4. `fa_formal` 仍被启动挡板拒绝，现有 Docker 静止屏障已被审查判为 NO-GO；
5. rollout sandbox 目前只是 Docker bridge + root，S2 的运行期防线尚未接入；
6. 跨 publish 的整批提前 drain 让 staleness 在错误时点判定；
7. Miles 没有生产可用的 fully-async close/dispose 链；
8. checkpoint、证据水位、已发布 weight version 和新 segment 的采样起点没有
   联合提交与冷恢复协议。

这些缺口不要求恢复旧 FA 的庞大自建方案，但都不能只靠 GPU 上“看看能否跑”来
替代本地实现。

### 0.2 本轮不做正式首训，但要证明“以后只差数据与实验定案”

本次租期运行的是**可丢弃的正式链资格作业**：使用通过环境门的资格任务包，
真实进入 `fa_formal`、fresh grader、online eligibility、faithful DIS、R3、
optimizer、checkpoint 和冷恢复；其模型 checkpoint 用后删除，不形成模型效果
结论，也不作为正式首训起点。

本轮通过后，仍然保持：

```text
rh2_formal_training_allowed = false
```

直到 Owner 选定并冻结首训任务集、reward/grader、base checkpoint、采样配置、
训练超参数、评测面和预算。这里剩下的是**具体 run 的授权包**，不是训练 infra
代码缺口。

为避免一个全局布尔值混淆不同事实，本文使用三个判定概念：

```text
qualification_run_authorized
    = Owner 批准的限量正式链资格作业
    ∧ qualification taskset/reward/profile 已冻结
    ∧ step、GPU-hour 和输出目录有硬上限
    ∧ checkpoint 标记 disposable，禁止成为后续训练起点

formal_path_infrastructure_qualified
    = 本文所有本地硬门与八卡硬门通过

formal_run_authorized(run)
    = 首训 taskset/environment/reward/config/budget 全部冻结并通过各自门槛
    ∧ Owner 批准该次正式训练
```

`qualification_run_authorized` 是总正式训练闸门为 false 时唯一允许进入 optimizer
的窄授权，不得实现成普通环境变量旁路；它只能由本次预注册 campaign 使用。
其余两个名字先作为验收结论使用，不要求现在新增一套复杂的通用 gate 系统。

本次通过后的建议状态是：

```text
rh2_fully_async_training_path_verified       = true
formal_path_infrastructure_qualified          = true
rh2_online_reward_integrity_minimum_qualified = true
rh2_s2_signal_trusted                         = false
rh2_formal_training_allowed                   = false
```

这里不直接复用 `rh2_s2_signal_trusted`，因为现行 S2 计划还把 exporter、完整
红队展示和其他非首训在线正链事项包含在该字段中。只有 Owner 以 T0 明确重定义并
同步 inspector/acceptance 后，才能用本文最小安全范围翻旧 S2 字段。

但“旧 S2 字段保持 false”不能意味着首训前还要再改一次 infra 闸门。本文建议
现在就把首个在线 RL run 的正式准入公式定为：

```text
rh2_formal_training_allowed(run) =
    formal_path_infrastructure_qualified
  ∧ rh2_fully_async_training_path_verified
  ∧ rh2_online_reward_integrity_minimum_qualified
  ∧ formal_run_authorized(run)
```

其中 `formal_run_authorized(run)` 是绑定最终 taskset/environment/reward/config/
budget digest 的 Owner 授权 manifest，而不是一个可手填的布尔环境变量。旧
`rh2_s2_signal_trusted` 继续表示范围更宽的 S2 项目里程碑，但不再阻塞本文定义的
首个在线 RL 支持 profile。该公式、inspector 和 preflight 的修改属于租卡前本地
必做；是否采用是本文最重要的 T0 之一。这样 GPU 资格通过后，保持
`rh2_formal_training_allowed=false` 的唯一原因才是尚未冻结并批准具体首训 run，
而不是还有治理代码待开发。

### 0.3 “首训就绪”只对一个明确支持 profile 成立

一次八卡资格不能外推到所有 Miles 能力。租卡前必须由 Owner 冻结一个支持
profile，至少包括：

- 模型、tokenizer、目标八卡硬件和单节点训推拓扑；
- SGLang engine 数、Miles router 形态与权重传输模式；
- `fa_formal`、R3-on、sampling-support replay、`retract` pause mode；
- faithful-DIS policy objective only、默认 actor-group trainer、`CP=1`；
- reward-only/masked member 是否计入 GBS、group denominator 和 optimizer-step
  计数口径；
- speculative decoding、MTP、OPD、KL、entropy、MoE auxiliary 的启停；
- Claude Code harness 工具面，是否允许 subagent、compaction 和 fan-out；
- staleness 阈值、buffer 容量和最大并发；
- checkpoint 分段频率和恢复承诺。

没有进入这个 profile 的能力不算失败，也不能被本次结果宣称为支持。

---

## 1. 对旧 FA 剩余工作的最终处置

本节不用“先后移”描述。每一项只有三种结果：**首训前本地做完**、**同一次八卡
验证**、或**明确不做**。明确不做的项目没有排期；只有以后出现新的训练需求或
失败证据时，才重新提出范围与成本。

| 旧 FA / 相邻事项 | 当前事实 | 首训就绪处置 |
| --- | --- | --- |
| RH2 自建持续 worker、top-up、ready queue、反压 | Miles `FullyAsyncRolloutFn` + `DefaultDataBuffer` 已提供 | **不做自建实现**；本地测 worker 自主推进/反压，八卡测真实重叠与长尾 |
| `PromptGroupAssembler`、`QualifiedPromptGroupQueue` | Miles 原生按完整 prompt group 生产和 drain | **不做这些组件**；补 eligibility group filter、reward dynamic filter 与补采守恒 |
| `SlimeBatchAssembler`、lease/ACK、`HANDED_OFF→TRAINED` 全状态机 | 仅服务被冻结的 Slime FA 自建面 | **不做**；正式支持面只认 Miles 训练转换和本文最小恢复合同 |
| D-FA-3 proxy abort 归因、trainer coordinator 与内部重生成 | 支持 profile 采用 SGLang `retract`：同一 HTTP 请求回等待队列、更新后重算 KV，并由 version spans 记录跨版本 token | **不接旧 coordinator**；本地验证异常 fail-closed，八卡 H4 验证同请求 multi-span；`abort` mode 不属于支持面 |
| D-FA-4 before/after eval | 正式首训需要知道指定 checkpoint 能否被评测路径加载，但本轮不做能力结论 | **本地接标准非 FA eval；八卡做运输 smoke**，eval 时 producer 必须停止，不另建训中异步 eval |
| FA 四层身份 | RH2 契约和旧 worker 已有；Miles submit/generate 未盖章 | **本地接通**，否则 `fa_formal` 会全量 fail-closed |
| capture、turn identity、sampling mask、R3、weight spans | 本地 spike 已大体闭合 | 保留；补 formal 身份后做聚焦本地回归，八卡做真实生产/消费证明 |
| B1～B4：baseline、不可变 patch、hygiene、fresh grader | 组件已实现，但只在被禁止的 `fa_formal` 分支消费 | 保留并接通；替换 NO-GO 静止屏障，完成缩小后的真实 Docker 组合测试 |
| B5 finalization receipt | 已有 per-attempt 原子 receipt 与 formal 构造要求 | 保留既有最小 receipt；**不扩展**成 trainer delivery/recovery ledger |
| 旧 B6 正式评分组合测试 | 尚未完成；不能与 Miles spike 中“零信号 B6”混为一项 | **本地必做**：正常完成、后台/root writer、Git 注入、评分器不回读 live workspace |
| F2-4 完整 active/buffer 恢复 | Miles 不保存 frontier；旧方案包含较大状态机 | **不实现同一 run 的 pending replay**；只做本文 §2.7 的已发布权重 checkpoint、全新 segment 冷启动和显式采样偏离记录 |
| F2-5 collector 不变量 | group shape/转换的一部分由 Miles 吸收 | 不建独立 collector；保留 group 守恒、eligibility、唯一消费和训练消费证据 |
| F2-6 durable physical-attempt→Outcome manifest、43 事件全接线 | 当前没有生产消费者 | **不做完整实现**；只保留本文验收、checkpoint 和证据水位真正读取的最小事件与 manifest |
| C3/C7 governed buffer、attempt ledger、lifecycle 原型 | 未接生产链，且原型把整组 ID 当 member physical attempt，粒度冲突 | **不接入**；关闭和恢复直接扩 Miles producer 的小接口，不以原型为前置 |
| `retry_local_operation` 通用重试框架 | 仅旧 Slime worker helper，有单测、无正式 Miles 消费点 | **不接通用重试**；可重试的数据不足由 producer 补采，系统边界故障按 typed run-fatal，不重跑整段 harness |
| 运行期内存与同步 evidence 写盘 | 旧审计发现部分 list 无界、部分 `fsync` 位于 asyncio 路径 | **本地必做容量闭包**：对支持步数给出硬上限或流式落盘后淘汰；热路径同步写超预算则移到有界 writer/线程，不建 WAL |
| episode deadline 起点 | 现实现从首次模型调用起计，未覆盖 materialize/启动等待 | **本地冻结语义**：分别限制 setup、attempt/episode 和 run；不能让任务在首次调用前无限占用资源 |
| FA-3 batch admission | 离线差分测试已有，生产 Miles 路径仍需正式准入闭环 | 本地 preflight + group filter/refill 集成测试；八卡验证过滤后仍组成合法训练 batch |
| FA-4 faithful DIS、零信号 skip | 本地实现和对拍已有 | 八卡验证真实分布式 loss、梯度、optimizer/scheduler/version 守恒 |
| FA-5 | 旧含义是短租集成验收 | 被本文八卡资格作业完整吸收，不再另租一次 |
| S2 数据 ingestion | 216 题 v2 三分包和 trusted loader 已有；环境门 runner 未完成 | 补环境门机制和正式 bring-up 消费接线；最终首训子集的选择不在本轮 |
| S2 runtime/anti-cheat | schema 多、真实消费者少；当前 `findings=()` | 完成 §2.4 的最小 reward-integrity 安全链 |
| S2 exporter / SemanticSFT / warm-start | 不在在线 RL 正链上 | **不做** |

---

## 2. 租卡前必须在本地完成的工作

### 2.1 冻结支持 profile 和闸门口径

先完成 §0.3 的 Owner 决策，并把每个关键配置分成：

```text
训练语义值
资源/性能值
诊断值
明确不支持值
```

formal preflight 必须至少拒绝：

- `s1_compat` / `fa_audit_only` 冒充正式链；
- 总正式训练闸门为 false 且缺少不可变 `qualification_run_authorized` manifest
  的 optimizer 作业；
- S1 的 8 道 Verified 探针题冒充训练数据；
- 未绑定 `EnvironmentPackageV1.digest()` 的任务；
- S2 最小安全验收未通过；
- offline/audit eligibility 进入 policy loss；
- integration tree、SGLang、Megatron、镜像、模型或 tokenizer 身份不符；
- 超出本次支持 profile 的 engine、pause、objective、并行或 harness 配置。

同时实现并测试 §0.2 的 run-scoped 正式准入公式。具体首训 manifest 缺失、任一
digest 漂移、授权过期或预算越界时，`rh2_formal_training_allowed(run)` 必须为
false；qualification campaign 只能走更窄且一次性的
`qualification_run_authorized`，二者不能共用旁路。

GPU 敏感参数不能全部留到资格作业后再选。租卡前必须二选一：冻结首训拟采用的
精确值；或冻结一个保守的 qualified envelope，并在 envelope 的资源最坏点和语义
边界取点验证。至少包括 sampling 参数、global/micro batch、并行 shape、staleness
阈值、buffer/并发、`update_weights_interval` 和 checkpoint segment 间隔。资格后
可以再选的是通过相同环境门的 task 内容、run seed、预算和不会改变已资格化 shape/
资源边界的参数；超出 envelope 就诚实要求局部重资格，不能宣称本次覆盖所有配置。

完成标准：用正例配置能通过 checks-only；每个拒绝面都有一个会使 preflight
失败的负例，不接受仅靠文档提醒。

### 2.2 Miles FA 身份和 eligibility 真准入

#### 当前缺口

`generate.py` 在非 `s1_compat` 模式下要求：

```text
rh2_prompt_group_id
rh2_rollout_execution_id
rh2_group_index
rh2_member_slot
rh2_physical_attempt_id
rh2_physical_attempt_seq
```

旧 RH2 worker 会在 dispatch 时铸造这些事实，但
`Rh2MilesGenerateFn` 当前只是启动 bring-up 并调用旧 generate；Miles prompt
没有完整盖章。因此仅解除 `fa_formal` 启动挡板仍会在 materialize 前全拒。

同时，RH2 在 leaf metadata 写入 `training_eligibility_class`，当前 Miles
canonicalizer 只透传；默认 buffer 只处理 status、dynamic filter 和
staleness，没有训练资格消费者。S1 cap 会把事实合格的轨迹封顶为
`offline_or_sft_candidate`，但该结果并不会自动令 `remove_sample=True`，所以
现在真实可达的坏路径是“报告说 offline，trainer 仍然训练”。

#### 必做实现

1. 在 Miles 的 group submit / generate 边界铸造稳定的 prompt-group、execution、
   member 身份；每次 retry/replay 产生新的 physical attempt 和 seq；
2. retry 保持逻辑 execution 不变，但不能复用 session capability 或 physical
   attempt；
3. 在唯一 group 准入点强制：

   ```text
   group_eligible =
       每个 member.training_eligibility_class == online_policy_loss_eligible
       ∧ reward/dynamic-filter 条件通过
       ∧ group shape、slot、身份和训练 schedule 合法
   ```

4. 任一 member 不合格时整组拒绝，Miles producer 自动补采；拒绝原因和数量进入
   最小事件流；
5. 本地先实现“安全 acceptance artifact → 资格解封”的 fail-closed 机制；GPU
   campaign 先以**不进入 policy loss**的安全资格段完成真实在线拦截与 fresh
   grading，再在全新进程中用该 artifact 和
   `qualification_run_authorized` 允许 qualification task 获得 online
   eligibility；不允许普通环境变量绕过；
6. 这只关闭 `rh2_online_reward_integrity_minimum_qualified`。旧
   `rh2_s2_signal_trusted` 是否按本文范围重定义，必须另有 Owner T0 和 inspector
   同步，不能在实现时顺手翻转。

完成标准：成功、retry、单 member 不合格、整组不合格、cap 未解除、metadata
丢失和身份复用的生产路径测试全部通过；被拒组零样本到达 conversion/loss，后续
合法组能补足 batch。

### 2.3 正式任务入口、环境 lineage 和环境门

#### 已有资产

- `load_trusted_ingest_outputs(repo_root)` 已能加载并核对 S2-1 的 216 题 v2
  三分 bundle；
- `docs/.../s2/ingest/` 已有 216 条 environment/public/grading/validation
  产物；
- S1 的 clean grader 和评分 parser 可以复用。

#### 仍缺的生产接线

1. `BringupService` 不能再固定调用 `bundles.load_bundle_pairs()` 的 8 题表；
   应消费可信 ingest/taskset manifest，并按 task id 同时解析 public、grading 和
   environment package；
2. Miles data source 与 RH2 task resolver 必须绑定同一个 taskset revision 和
   package digest；未知 task、同 id 不同 digest、漏包都 fail-closed；
3. 把真实 `EnvironmentPackageV1.digest()` 接入 `RolloutTaskSpec`、
   `BaselineWorkspaceManifestV1`、frozen patch、finalization receipt 和 run
   manifest；不能用 public bundle digest 冒充；
4. 完成 `grade_controlled_patch`、环境门 runner 和 `EnvValidationReport` 的
   最小闭环，证明 empty patch、golden patch、已知错误 patch和确定性门能真实
   执行；
5. 为本次资格作业冻结一小组**来自训练候选面、通过环境门、不会污染评测面**的
   qualification taskset。它不是最终首训题单，也不能使用 S1 的 8 道 Verified
   探针冒充。

还要把时间边界拆清：environment/materialization 与 harness 启动有独立 setup
deadline；physical attempt/episode 从实际资源占用开始受绝对 deadline 约束；run
有总墙钟上限。任务自身的 deadline 到期是 attempt/group-local 拒绝并补采，无法
终止 execution scope 或释放资源才升级为 run-fatal。具体数值属于支持 profile，
但“首次模型调用前无限等待”不属于支持语义。

最终首训题单选定后，需要对该题单运行相同环境门并生成 run-specific manifest；
这属于数据包生成和授权，不应再改训练后端代码。

### 2.4 最小 `fa_formal` 评分冻结与 reward-integrity 安全链

#### 评分冻结

保留现有 B1～B5 的窄语义，不继续扩建账本：

```text
materialize 后、模型写入前记录 baseline
→ 撤销模型会话能力并排空 request/capture
→ 终止 owned execution scope 的所有写者
→ 宿主可信 exporter 从静止 workspace 生成不可变 patch
→ hygiene / protected-path 检查
→ fresh grader 在干净 checkout 应用 patch并评分
→ 原子写最小 finalization receipt
→ cleanup
```

当前 `DockerQuiescenceBarrier` 不能直接解禁。它依赖容器内
`pkill -u agent`、`ps` 和模型可控的 Git 命令；会漏 root writer、受 zombie
影响，并引入 `diff.external` 执行面。最小替换方案应由 runtime owner 直接停止
和等待容器/cgroup execution scope，再让宿主侧 git-free census/exporter 读取
静止文件树。评分器不能拿到 rollout live workspace。

本地 B6 缩为真正影响首训正确性的组合测试：

- 正常 agent 写完后，grader 输入与 frozen patch 完全一致；
- agent/后台/root writer 试图迟写时，要么先被终止，要么 formal attempt
  fail-closed，不能悄悄改变 grader 输入；
- Git hook/filter/`diff.external` 注入不能执行；
- binary、symlink、mode、add/modify/delete 按既有契约工作；
- grader 明确不回读 live workspace；
- task-local 迟写、patch/hygiene 不合格或 protected-path 篡改使该 attempt/group
  ineligible 并 refill，不以 reward 0 洗绿，也不能让单个恶意任务成为整作业拒绝
  服务入口；
- execution scope 无法终止、grader 隔离失效、artifact/receipt 存储不可用、身份
  或安全边界破坏属于系统性故障，必须 run-fatal。

#### 最小安全链

当前 rollout 容器声明 `allowlist`，真实 Docker 参数却只是 `--network bridge`，
并以 root 启动；`AntiHackEvent` 仍是 schema，formal finalize 传入的是
`findings=()`。首训前至少要完成：

1. 依赖预装；agent 进程以非 root 身份运行，capabilities、pids、CPU、内存和
   writable mount 有明确边界；
2. 使用隔离网络，只放行模型 proxy 和必要内部服务，公网默认拒绝；
   `--network none` 不能用于需要访问模型 proxy 的 Claude Code rollout；
3. hidden tests、golden patch、validation-only bundle 和 grader-only 文件永不
   挂入模型可见 workspace；
4. 按真实镜像扫描结果清理 future Git history/reflog/remote refs；
5. 对 remote git/下载、私有路径探测、受保护测试/评分器篡改等动作真实阻断并
   记录 attempted/executed；
6. 安全事件和 patch hygiene 真正进入 EligibilityGate，而不是固定空 findings；
7. 用少量针对性正反例证明：作弊动作不能改变 reward 或进入 loss，正常轨迹不
   被误拒。

不要求本轮实现 microVM、透明通用出网代理、LLM claim-check 或完整五类展示型
红队报告。它们不改变本次在线 RL reward 的最低可信边界。

### 2.5 关闭跨 publish 的整批提前 drain，并补齐计时

#### 代码事实

当前 `train_async.py` 会在训练 A 前提交下一批 B 的 `generate.remote()`，并在
publish A 之前等待 B future。这个 future 返回时，不只是 B 的 generation
完成，还已经做完：

```text
buffer drain/filter
→ rollout postprocess
→ RH2 evidence/debug/logging
→ reward 提取/归一化与 train-data conversion
→ DP schedule/split
→ Ray object-store put
```

trainer 收到后才继续 object-store get、CPU→GPU、advantage 计算、replay fill 和
pre-forward。因此旧 prefetch 没有隐藏 trainer 侧 advantage 计算。

Miles 的 `FullyAsyncRolloutFn` 第一次调用后会保留无限后台 worker；即使 driver
不提前 materialize B，A 训练期间仍会持续 generation、grading、dynamic
filter 和 buffer put，直到 buffer 满而反压。因此关闭整批提前 drain 后仍然是：

```text
持续 producer + bounded buffer + just-in-time batch materialization
```

不是同步 rollout。

#### 为什么首版要关

当前 B 在 publish 前按 version `k` 从 buffer 取出，A 随后把 trainer/engine
推进到 `k+1`，B 才进入 trainer。于是 buffer get 看到的 current version 不是
真正 trainer-consumption version，正式 staleness gate 会低报一代。首版应在
publish 后再 drain B，让判定时点与 trainer 消费一致。

为了不同时引入“哪些 step 可以 prefetch”的第二套控制流，首个支持 profile
推荐固定 `update_weights_interval=1`，所有下一批都 JIT materialize。若 Owner
选择更大的 interval，则名义 publish boundary 仍保守 JIT；即使该 boundary
最后因 zero-signal 没有实际 publish，也接受这一次性能损失。非 publish step
是否 prefetch 必须在 profile 中写死并进入本地顺序矩阵。

#### 性能代价不能假定为零

如果 B 在 A 训练期间尚未凑齐，两种方案都要等待 generation；JIT 改变 publish
和 `retract` 的时点，可能改变哪些请求被撤回及其重算量，不能先验声称只重算
“少量 token”。如果 B 已经在 buffer 中凑齐，旧提前 drain 可以隐藏一部分：

```text
warm queue pop/filter
+ postprocess/evidence/conversion
+ DP schedule/split
+ object-store put
```

关闭后这部分成为 trainer bubble。它不包含 trainer 侧 object-get 和 GPU
preprocess，因为这两项旧实现本来也没有隐藏。

租卡前必须补以下最小单调时钟事件，并带 batch/group/version 身份：

- group/execution dispatch、generation start/end、任务长短类别或 active-count 变更；
- driver batch-materialize submit、await begin/end、train call begin/end、publish
  begin/end；
- drain begin 时的 target/queue/trainable depth、每次 get attempt/decision、
  decision current version、oldest behavior version、stale/drop/refill reason；
- drain end、postprocess end、conversion end、DP split end、pack ready；
- trainer object-get begin/end、GPU preprocess end、pre-forward、step end；
- pause/retract/resume 和 retracted request 数。只有 pinned SGLang 提供一手计数
  时才把 recomputed tokens 当精确指标；否则只能把 prefill counter 增量标为估计。

本地测试至少覆盖：worker 在没有第二次 drain 时仍自主生产到反压、B-ready、
B-not-ready、zero-signal 不 publish、真实 publish、末批、generate/publish 失败。
还要增加：publish `k→k+1` 后混合 fresh/stale 与全 stale 的 refill 纵切，以及用
fake monotonic clock 验证事件配对、非负、区间和、B-ready 分类和身份联结不会洗绿。
再用真实 RH2 shape 做 CPU materialization benchmark。

八卡上记录：

```text
JIT 暴露的绝对 bubble
rollout wait
manager materialization
trainer preprocess
publish pause/update/resume
generation ∩ train 重叠区间
buffer-full backpressure
```

一条 JIT 时间线只能给出 JIT 的绝对关键路径、idle 和 GPU-hour，不能严格重建旧
prefetch 的反事实时间线：两者会竞争 CPU/Ray/object store，B-not-ready 时又会
改变 retract 时点。为了回答 Owner 指定的“关闭后实际增加多少时间”，同一次租期
在主资格全绿后追加一个短的 Miles-only、同源码、同 profile、同任务构成的
prefetch on/off 成本对照；prefetch-on 只作数据级诊断，不取得正式 staleness
资格，也不是 Slime 性能 A/B。若无法形成可信 matched 对照，只报告 JIT 绝对成本
和可隐藏时间上界，不声称因果增量。

“可信 matched”至少要求任务构成、有效 token/批量、applied-update/publish 数可比，
并单独报告 stale/drop/refill 是否已经分岔；任一条件不满足就输出
`NOT_COMPARABLE`，不能仍给一个漂亮的相对百分比。

重叠率按“至少一个 generation active 的时间与 trainer compute 区间的交集”计算，
并发请求不能重复累加；快组穿越慢组至少要有
`slow.start < fast.end < fast.train < slow.end` 的身份化证据。GPU workload 没有
自然出现 B-ready 或 B-not-ready 某一分支时，本地确定性测试足以覆盖；不为填表
强行改变主作业分布。

不为这些计时增加第二次租卡。若以后要重新开启跨 publish batch prefetch，必须先
有 trainer pre-forward 二次 staleness gate，并由本次成本对照证明收益值得增加
语义复杂度。

### 2.6 首训支持 profile 的正常关停

当前 `RolloutManager.dispose()` 只关闭 data source、指标和 monitor，不会关闭
`FullyAsyncRolloutFn` 的无限 worker；`Rh2MilesGenerateFn` 也明确把 adapter
HTTP 线程和评分队列留给进程退出回收。现有 `Rh2RolloutLifecycle` 原型没有生产
调用点，且绑定了不采用的 governed ledger。

首训前不建设通用 lifecycle 框架，但必须给实际 Miles/RH2 对象补最小关闭面：

```text
train driver finally
→ 停止 producer 新 submission
→ cancel/await active group tasks 与 drain waiter
→ 关闭/排空 RH2 grading queue、capture/proxy/session
→ 停止 adapter HTTP 服务
→ 清理或隔离所有 rollout/grader Docker container
→ flush 必需 evidence/receipt
→ Miles RolloutManager.dispose
→ Ray/CUDA 进程正常退出
→ campaign supervisor 对本 run label 做一次有界兜底清理与残留核对
```

要求有界超时、保留首因；任何兜底后仍未清的 container、open session、未终结
请求、后台 task 或 evidence/checkpoint flush 失败都使资格作业失败。允许 campaign
supervisor 在正常进程退出后按 run label 清理 Ray/Docker，但不允许人工 shell 强杀
后把作业记成正常成功。

本地只覆盖正常 close、异常 close 和“关闭开始后不再 submit”三个生产可达分支，
不扩成所有 put/get 竞态矩阵；八卡再测真实 Ray、SGLang、Claude Code、Docker 和
CUDA 组合。

### 2.7 最小 checkpoint 与全新 run segment 冷恢复

#### 为什么不能只说“从 Miles 上一个 checkpoint 重启”

当前保存顺序是 actor checkpoint 后再存 data-source cursor，publish 又发生在保存
之后；异步 save 未必在 cursor 落盘时 durable。恢复时模型 checkpoint 决定
`start_rollout_id`，对应 cursor 文件缺失却只记日志并从初始位置继续。没有 joint
commit marker 能证明 model、optimizer、scheduler、RNG、cursor 属于同一代。

同时，global cursor 在 prompt submit 时就前进，producer active、completed buffer、
drain 和预取训练包都没有联合保存。若声称从该 cursor 继续同一逻辑 run，会出现
静默跳题或混代。

所有 updater 又在新进程把 `weight_version` 设为 0，恢复后的 bootstrap publish 会
把旧 checkpoint 错标成 version 1。它会破坏 staleness、multi-span provenance
和跨 segment 审计。

#### 本文推荐的最小合同

首训支持 profile 不承诺同一 run 的 frontier 无损续跑。一次正式实验可以由多个
带父子关系的 run segment 组成；崩溃时只保留最后一个完整 checkpoint，旧 segment
未提交的 rollout、buffer 和 optimizer 后缀整体作废。这个采样偏离必须显式记录，
不能伪装成精确 cursor resume。

```text
只在正常 publish boundary 建 checkpoint
且 weights_dirty_since_publish == false
且 trainer ↔ SGLang 参数 equality 已通过
→ 停止 producer 新 submission
→ JIT profile 断言 drain/prefetched/untrained Ray pack 均为 0
→ cancel/await producer active，清空 completed buffer，并写 bounded frontier-discard receipt
→ flush 已进入模型的 batch/group、online eligibility、fresh-grading receipt 与
  trainer-consumption evidence watermark
→ force-sync 保存 model + optimizer + scheduler + trainer RNG 到独立 generation
→ 写 checkpoint manifest：source/profile/environment/grader digest、
  last_applied_optimizer_step、evidence watermark、last_published_weight_version、
  frontier-discard receipt、下一 segment 的显式 data sampling plan
→ 最后写 COMMITTED manifest/pointer
```

恢复只认最新完整 RH2 `COMMITTED` generation，不直接相信 Megatron 的 latest
tracker。新 segment 使用新的 `segment_id`、空 buffer、新 physical attempt/session
身份和显式冻结的 sampling seed/epoch/start policy；不自动加载旧 global cursor，
也不声称未训练 frontier 被重放。恢复 bootstrap 应把 checkpoint 权重发布为原来
的 `last_published_weight_version`，下一次真实 optimizer update 才推进版本。

numeric version 只在一个 segment 内单调；它不是跨 segment 的全局身份。所有持久
证据、artifact 和验收 join 必须使用：

```text
weight_identity = (segment_id, numeric_weight_version)
```

staleness 也只在同一 segment 内计算。这样 Segment A 在 checkpoint 后产生但作废
的 `p+1`，与 Segment B 恢复后再次产生的 numeric `p+1` 不会静默串账；这只是复合
身份，不引入 recovery epoch 或跨 segment 全局版本协调器。

如果 `update_weights_interval>1`，checkpoint 必须等到下一次正常 publish boundary，
不能为保存方便偷偷提前 publish。trainer RNG 要恢复；重新采样的 rollout 不要求
复现旧 SGLang sampling RNG。

本地必须完成 checkpoint crash matrix：model save、manifest、evidence watermark
和 COMMITTED pointer 各步骤前后中断；恢复只能选择上一代或完整新一代，不能
混搭。missing/corrupt manifest、单个 DCP shard、environment/config digest 都
fail-closed。还要验证 Adam step/moment、scheduler、trainer RNG、weight version
和证据水位没有归零或错代。

这个范围明确**不实现 F2-4 pending replay**：

- 不恢复或重放 cursor 已越过的 active/buffer prompt；
- 不恢复 active HTTP、KV、Claude Code session、Docker workspace 或完成 tensor；
- 不承诺 optimizer exactly-once；
- 不做 recovery epoch/fencing 状态机、actor 热替换、自动 heal 或跨节点恢复；
- 不做每 step WAL 或全生命周期 ledger。

代价是崩溃会丢弃最后一个未提交 segment，并可能相对原数据顺序跳过或重复一小段
任务。首训 30～50 step 是否接受这个残余风险、segment 间隔和 sampling reset
规则，属于 Owner T0；本文推荐接受，以避免为第一次训练建设完整异步恢复系统。
这会明确 supersede 先前 F2-4 的 pending-before-cursor 方案在**首训支持 profile**
中的适用性，而不是把旧定案静默删掉。

### 2.8 最小证据和验收包

不补齐旧 Observability V0 的 43 个事件。只实现本次判定真正读取的事实：

- source/runtime/model/tokenizer/taskset/environment/grader/config 身份；
- prompt group / execution / member / physical attempt / leaf 身份；
- eligibility 拒收、dynamic filter、refill 和 group 守恒；
- generation、buffer、drain、conversion、trainer-consumption 四时点版本；
- version evidence 必须在 session unregister/cleanup 前冻结，不能从清理后的空
  registry 反推；
- sampling support、R3、faithful DIS、loss/grad、optimizer/scheduler/version；
- publish 前后参数与 SGLang equality；
- checkpoint generation、evidence watermark、frontier-discard、冷恢复与 version
  continuity；
- sandbox/anti-cheat/fresh-grading 结果；
- close/dispose 和残留资源清单；
- GPU、RAM、object store、磁盘和墙钟成本。

首训支持 profile 还必须完成两个资源闭包，但不扩成观测平台：

1. 盘点该生产路径上会随 attempt/group/turn 增长的内存集合；要么按支持 profile
   的最大 step、并发和 retry 数证明保守上界可接受，要么流式写出并保留有界窗口。
   重点包括 audit/failure/drop/cleanup/grading event 缓存；不接受仅因 2-step
   spike 没 OOM 就判定 30～50 step 可用。
2. 测量 artifact、receipt 和 checkpoint manifest 的写入次数、字节数、`fsync`
   p50/p95/p99 与 event-loop stall。同步持久化若超过预注册预算，移到有界专用
   writer 或 `to_thread`，shutdown/checkpoint 时 flush；不建设热路径 WAL 或每事件
   exactly-once。COMMITTED pointer 与父目录仍必须原子写并 durable。

本文范围确认后，再从这些事实反向生成启动脚本、collector、judge、阈值和负例
self-test。现有验收器不因文件存在而默认可信。

### 2.9 before/after eval 最小运输链

首训前不实现训中异步 eval，但要把标准非 FA eval 的最小链路接到同一 source、
model/tokenizer 和环境解析器上。preflight 必须保证 eval taskset 与训练 taskset
身份分离、eval 不进入 policy loss，且 eval 开始前 fully-async producer、grading
和 update 已停止。eval 结果绑定明确 checkpoint/weight digest，不接受“latest”。

本地用小模型/fixture 验证 base 与 post-update 两个显式 checkpoint 的加载、环境
运行、评分、结果 manifest 和失败传播；真实 30B checkpoint 的可加载性留给 H10。

---

## 3. 同一次八卡租期必须验证的内容

### 3.1 资格证据必须来自一个连续 campaign

不能把不同源码、模型、拓扑、execution mode、pause mode 或 objective 的成功
片段拼成绿色结论。允许同一次租期分成多个全新进程，但它们必须共享一个冻结支持
profile 和 run/campaign identity：

```text
Safety-Q：fa_formal 安全/评分资格段，不进入 policy loss，产出冻结安全 evidence
Eval-Q0：以显式 base checkpoint 跑标准非 FA eval 运输 smoke
Segment A：qualification-only 授权的正式正链 + 连续非零更新 + committed checkpoint
           → checkpoint 后产生少量未提交进度 → 预期整作业死亡
Segment B：从 A 的 committed checkpoint 开全新 run segment + 连续更新 + 正常退出
Eval-Q1：完全停止 FA worker 后，以 Segment B 显式 checkpoint 跑同一 eval 运输 smoke
Companion probes：零信号、受控不合格组和短 prefetch on/off 成本诊断
```

资格权重和 checkpoint 全部是一次性证据，不进入正式首训。

### 3.2 H1：目标 30B 训推栈与资源闭包

在 Owner 批准的八卡拓扑上同时启动 RH2、Miles fully async、SGLang、Megatron、
Ray、Claude Code、Docker 和 grader，真实执行 30B MoE forward/backward、
optimizer 和权重传输；记录显存、host RAM、Ray object store、磁盘和容器水位。
同时记录 evidence writer 的队列水位、写盘吞吐、`fsync` 延迟和 event-loop stall，
核对本地给出的 30～50 step 内存/磁盘保守上界没有被真实数据推翻。

必须在 GPU 上做：本地不能证明 sm_120 kernel、TP/DP/EP/PP collective、MoE
dispatcher、混合精度 optimizer 与训推同时常驻的显存闭包。

### 3.3 H2：`fa_formal` 正式纵链

Safety-Q 的 GPU 安全 evidence 必须先封存；随后使用全新进程、不可变
`qualification_run_authorized` 和该 evidence，至少让一组真实 qualification SWE
task 完整经过：

```text
trusted EnvironmentPackage
→ 受限 rollout sandbox + Claude Code
→ RH2 capture / identity / immutable patch
→ fresh grader
→ EligibilityGate = online_policy_loss_eligible
→ Miles group admission / buffer / conversion
→ trainer loss
```

另有一个受控 offline/tamper/blocked group，证明它整组不能进入 conversion/loss，
且 producer 会补到合法 batch。没有 Safety-Q evidence、授权过期、taskset/profile
digest 不符的作业都必须在资源启动或 optimizer 前拒绝。

必须在 GPU 上做：Docker/评分单独能在本地测，但只有与真实 SGLang、Ray transport
和分布式 trainer 串起来，才能证明资格 metadata 没在 adapter/buffer 边界失效。

### 3.4 H3：faithful DIS、GRPO、sampling support 和 R3 真消费

同一正链必须证明：

- sampling support mask 与 support-normalized behavior logprob 来自真实 SGLang；
- group reward/advantage、loss mask 和 rollout/execution 分母符合支持 profile；
- faithful DIS 使用真实 current/behavior logprob，loss 与 grad norm 有限；
- R3 routed-experts tape 在 Megatron forward/backward/recompute 被消费并耗尽；
- 在单个正链段内至少完成两个有非零训练信号的 optimizer step；整个 campaign
  还须满足 H5 的连续更新下限。

必须在 GPU 上做：CPU shape/公式测试不能证明 30B 分布式 logits、MoE replay 队列和
多 rank 归约真正使用了这些数据。

### 3.5 H4：真实更新、publish、multi-span 和版本连续性

正链必须证明：

1. optimizer/scheduler/参数只在真实非零更新时前进；
2. trainer 参数与 SGLang 发布后内容相等；
3. 一个真实单 HTTP generation request 跨过权重 publish，SGLang 产生多段
   `weight_versions`；
4. RH2 spans、sampling mask、R3 tape 和 token 行逐位对齐；
5. 该 multi-span 样本进入后续 trainer loss，而不是只落日志；
6. checkpoint 冷恢复后，旧版本不重置为 1，下一次真实更新严格推进。

该结果同时验证本支持 profile 不需要旧 `TrainingRuntimeCoordinator`/proxy abort
重生成链：`retract` 必须让同一个 HTTP 请求最终正常完成；若出现真正 abort 或
不可归因失败，只能令该 attempt/group fail-closed 并由 producer 补采，不能猜测
更新窗口后透明重试。

必须在 GPU 上做：只有真实参数改变、pause/retract/resume、KV 重算和跨进程冷启动
能验证这一组状态边界。

### 3.6 H5：fully async 重叠、长尾穿越、staleness 与 JIT 成本

使用预注册的长短任务混合，证明持续 producer 在 trainer 训练期间仍推进、快组不
等待同批最慢执行、buffer 有界且反压生效。按 §2.5 的分段计时量化：

- generation 与 train 的真实重叠比例；
- warm-buffer 时 JIT 暴露的 materialization 时间；
- B-not-ready 时的等待、pause/retract 时间和 retracted request 数；
- trainer-consumption staleness 分布、drop/refill 数；
- buffer 满反压时长与有效 group 产量；
- 每个有效 optimizer update 的 GPU-hour。

两步只足以证明公式和状态迁移，不能证明首训长度下资源不持续泄漏。本文推荐主
campaign 至少完成 **6 个有非零信号的 applied updates（Segment A ≥3，Segment B
≥3）**，并据此拟合 host RAM、object store、evidence、容器和磁盘水位斜率；Owner
可在实验设计阶段提高，但不应降回“2 步即首训就绪”。这仍是可丢弃资格作业，
不是正式首训或能力实验。

资格结论必须使用租卡前预注册的 staleness 和成本阈值。当前指标混合了多段时间，
不能用一个粗 `train_wait_time` 替代。JIT profile 的绝对成本属于硬门；短
prefetch on/off 只回答相对成本，不参与训练正确性资格。

### 3.7 H6：全局零信号语义

受控构造一个 dynamic filter 后仍到达 trainer、但全局无有效梯度的边界 case，证明
所有 rank 一致 skip，且以下状态都不前进：

```text
parameters
optimizer state
scheduler
weight_version
weight publish
```

同时记录原因并允许后续有信号 batch 继续训练。不能用单 microbatch 抛异常或整组
外部 kill 冒充成功。

必须在 GPU 上做：只有真实 DP/PP collective、Megatron optimizer 和多 rank 控制
流能证明不会 rank 分歧或死锁。

### 3.8 H7：安全与真实在线拦截

Safety-Q 在真实 Claude Code 多轮中、**不进入 policy loss**地验证：

- 受限网络仍可访问模型 proxy，但公网/remote git 请求被拒；
- hidden/grader-only 内容不可见；
- 受控作弊或 protected-path 篡改不能改变 reward，且产生可供下一阶段 gate 消费
  的 ineligible 事实；
- dummy/拒绝观测不会令 harness 和 capture 链崩溃；
- 正常任务在同一安全 profile 下能完成。

必须在 GPU 上做：本地规则测试不能证明真实 CC 子进程、模型调用、Ray 和长会话在
拦截后仍保持协议与资源正确。

### 3.9 H8：真实 checkpoint、预期 job death 与全新 segment 冷恢复

Segment A 在满足 §2.7 的正常 published boundary 写一次 committed checkpoint，
随后重新允许 producer 产生少量 checkpoint 后的 active/buffer 或未提交训练进度，
再注入整个 job/state-owner 的预期死亡。彻底清空旧 Ray/CUDA/SGLang/RH2 进程
后，Segment B 从该 generation 作为**全新 run segment**冷启动。必须证明：

- model、Adam step/moment、scheduler 和 trainer RNG 来自 committed generation；
- checkpoint 后的内存模型进度和 frontier 没有泄漏进 Segment B；旧 segment 的
  evidence 被标为未提交后缀，不冒充已恢复；
- Segment B 使用空 buffer、新 segment/physical-attempt 身份和预注册 sampling
  reset policy，不宣称旧 pending 被重放；
- `last_published_weight_version` 保持连续；
- collector/judge 用 `(segment_id, numeric_weight_version)` 联结证据；受控让两个
  segment 都出现 numeric `p+1` 且模型 digest 不同，仍不得串账；
- trainer→SGLang 参数 equality；
- 恢复后再完成一个非零 faithful-DIS + R3 optimizer step 和 publish；
- 恢复后的第一步把版本从 `p` 真正推进到 `p+1`。

缺/坏 manifest、单 shard 和 digest 的负例已由本地 crash matrix 负责，不为每个
坏例再写一次 400GB GPU checkpoint。

必须在 GPU 上做：Megatron 约 380～399GB 的真实分布式 checkpoint、optimizer/RNG
加载、job death 后的 NCCL/Ray/SGLang 全新进程恢复没有可信的 CPU 替代。远端磁盘
规划至少要容纳
“上一代 committed + 新一代写入中”，不能沿用每 step 保存的配置污染主实验。

### 3.10 H9：正常关停和无残留

Safety-Q、正常正链 companion 和 Segment B 最终完成后都要走 §2.6 的正常
shutdown。Segment A 的预期 job death 是 H8 故障注入，不拿 H9 的正常关停判据
制造假失败。正常结束必须证明：

- worker、drain/get/put waiter、adapter HTTP、grading queue、capture session、
  model request 全部终结；
- rollout/grader Docker container 无本 run 遗留；
- Ray actor、SGLang server、CUDA context 和子进程退出；
- evidence/receipt 已 flush，账目守恒；
- campaign supervisor 兜底清理后仍无本 run 残留。

必须在 GPU 上做：本地 fake task 无法覆盖真实 Ray actor、CUDA context、HTTP
generation、CC 子进程和 Docker 组合清理。

### 3.11 H10：before/after eval 运输 smoke

Eval-Q0 与 Eval-Q1 使用同一个小型冻结资格 eval taskset，分别显式绑定 base 和
Segment B checkpoint。必须证明：

- 30B 权重能由标准非 FA eval 路径加载，model/tokenizer/checkpoint digest 对得上；
- FA producer、trainer update 和训练 grading queue 已停止，eval 不与训练 worker
  偷偷重叠；
- environment/fresh grader 与结果 manifest 正常，eval 样本零进入 policy loss；
- 两次结果都可归因到各自 checkpoint，失败不会静默回退到 `latest` 或另一权重。

这里不要求分数提升，也不据 2～3 个 qualification update 形成模型效果结论；只
验证正式首训结束后无需再补一次大模型 eval 运输接线。必须在 GPU 上做，因为本地
fixture 无法证明 30B 分布式 checkpoint 的真实加载、SGLang serving 和资源切换。

---

## 4. 首训前明确不做的内容

以下项目不进入本轮或正式首训支持面，也没有默认后续排期：

1. Slime 侧 RH2 自建 worker、PromptGroupAssembler、SlimeBatchAssembler、
   lease/ACK 状态机；
2. C3/C7 governed buffer、attempt ledger 和当前 lifecycle 原型的生产接线；
3. 旧 `TrainingRuntimeCoordinator`、proxy abort 归因/内部重生成和通用
   `retry_local_operation` 生产接线；正式支持面固定 SGLang `retract`；
4. 同一逻辑 run 的 global cursor 精确续跑、pending prompt descriptor replay、
   recovery epoch/fencing 和 active/completed buffer frontier 恢复；
5. active HTTP/KV/Claude Code session/Docker workspace/tensor buffer 的原位恢复；
6. optimizer exactly-once、actor 热替换、自动 heal、跨节点容灾；
7. 完整 physical-attempt→Outcome durable ledger、43 事件全接线、热路径 WAL、
   每事件 fsync、cleanup reconciler；
8. 多节点、多 engine、多拓扑、multi-LoRA、CP/VPP/DeepEP/FP8/量化组合矩阵；
9. `in_place` 与 `retract` 双 pause mode 资格；
10. speculative decoding、MTP、OPD、KL、entropy、MoE auxiliary 的联合资格；
11. subagent、FORK、compaction、multi-leaf fan-out 的远程强制触发——如果 Owner
   批准的首训 harness profile 关闭它们；
12. microVM、AgentEnv、通用透明出网代理、完整展示型红队套件、LLM claim-check；
13. token-faithful exporter、SemanticSFT、teacher-SFT、warm-start 数据生产；
14. before/after 模型能力结论、正式首训题单选择和本轮资格权重留存；
15. Slime matched 性能 A/B 和 No-Go 后在同一租期现场补 Slime FA。

若未来需要其中任何能力，应根据真实训练需求或失败证据单独开范围，而不是把它们
作为“迟早都要做”的默认债务。

---

## 5. 一次租卡的成立条件与停止规则

### 5.1 租卡前硬门

以下全部完成后才租：

```text
支持 profile 与阈值冻结
GPU 敏感精确值或 qualified envelope 冻结
run-scoped 正式准入公式 + inspector/preflight 负例
FA 身份 + eligibility 真准入
trusted taskset + environment lineage + qualification taskset
fa_formal 评分冻结 + 最小安全链
跨 publish 提前 drain 关闭 + 分段计时
最小 production close/dispose + 按 run label 的有界兜底清理
已发布边界 checkpoint + 证据水位 + version + 新 segment 冷恢复
运行期内存上界 + evidence writer/fsync 延迟闭包
标准非 FA before/after eval 运输链本地闭合
qualification-run 窄授权 + Safety-Q 资格 artifact 门
launch/preflight/collector/judge 及其洗绿反例
```

否则“一次租卡”只是把第二次租卡的必需工作藏到了第一次失败之后。

### 5.2 远端执行原则

1. 先做 source/build/资源 preflight；硬件栈不能启动时不运行长 SWE；
2. 先运行不进入 policy loss 的 Safety-Q（H7），冻结其 artifact 后退出；
3. 运行 Eval-Q0 后，以全新进程运行 H1～H6 的 qualification-only 正链；
4. 核心正链全绿后，才写大 checkpoint、制造预期 job death 并以新 segment
   全新进程完成 H8；
5. Segment B 正常退出后运行 Eval-Q1/H10；除 H8 中预注册的预期 job death 外，
   每个正常作业都执行 H9；
6. 语义或状态机失败只保全证据，不在昂贵机器上大改业务代码；
7. 只允许现场修普通 wheel/build/path 问题，任何业务改动都要形成新 source
   identity 并重跑受影响的完整范围；
8. 不把剩余租期切到未接完的 Slime FA。

### 5.3 通过条件

只有 H1～H10、必要 companion probes、成本阈值和证据完整性全部通过，才能记录：

```text
formal_path_infrastructure_qualified = true
rh2_fully_async_training_path_verified = true
rh2_online_reward_integrity_minimum_qualified = true
rh2_s2_signal_trusted = false
rh2_formal_training_allowed = false
```

现行 `rh2_s2_signal_trusted` 包含的范围大于本文最小在线 reward-integrity 链，
所以本轮不翻它；本文在租卡前已经按 §0.2 完成首个在线 RL profile 的新准入公式，
不把这项治理接线留到租卡后。`rh2_formal_training_allowed(run)` 继续为 false，
只是因为尚无具体首训的有效 `formal_run_authorized(run)` manifest。若最终首训改变本文支持 profile
中的模型、拓扑、engine 数、pause mode、objective 或 harness 安全语义，相应能力
必须重新资格化；仅更换通过同一环境门的 taskset 内容，不应要求第二次训练 infra
spike。

---

## 6. 对 Claude 方案的逐项判定

| Claude 判断 | 本文判定 | 原因 |
| --- | --- | --- |
| GPU spike = Miles 版 FA-5，一次租卡 | **同意，但扩大到正式首训基础设施资格** | 两次租卡会重复核心链；冷恢复和 formal 安全必须在同一租期完成 |
| Miles 吸收旧 worker/queue/assembler | **同意** | 不应继续造 Slime/RH2 异步机械 |
| 剩余大头不是实现，只是验收 | **不同意** | formal 身份、eligibility 消费、任务入口、barrier、安全、dispose、recovery 都有真实生产缺口 |
| B6 已由当前 C1 覆盖 | **不同意** | 当前 C1 是 `s1_compat`；旧 B6 是 formal 评分冻结组合测试，编号碰撞不等于已完成 |
| F2-4 可裁掉，崩溃后从 Miles checkpoint + cursor reset 重启 | **部分同意，但不能直接采用当前 Miles 行为** | 同意首训 profile 不做 pending replay；仍须补已发布边界、force-sync、COMMITTED manifest、证据水位、version continuity、frontier-discard receipt，并以空 buffer 的新 segment 冷启动；不得把 cursor reset 伪装成精确续跑 |
| F2-5/F2-6 已吸收 | **部分同意** | group 机械由 Miles 吸收；eligibility、守恒和最小恢复 manifest 仍要做，完整 lineage/43 事件明确不做 |
| eligibility/anti-hack 已在 C1 链内 | **不同意** | eligibility 只有 producer metadata、没有下游准入；anti-hack 当前主要是 schema，formal finalize 固定空 findings |
| FA-3 只降为 preflight | **部分同意** | 不做 Slime assembler；但 Miles 正式准入/filter/refill 仍需生产接线和 GPU 证明 |
| 成功后只做一个 pre-formal 首训彩排 | **不够** | 本轮目标应直接验证 `fa_formal` 正链和冷恢复；仍不运行正式首训，也不保留资格权重 |

---

## 7. 需要 Owner 确认的 T0

1. **支持 profile**：§0.3 的模型、拓扑、engine、pause、objective、harness 与
   checkpoint 边界；
2. **闸门语义**：采用 §0.2 的 run-scoped 公式，并在租卡前修改
   inspector/preflight；本次通过后翻
   `rh2_fully_async_training_path_verified` 和
   `rh2_online_reward_integrity_minimum_qualified`；旧
   `rh2_s2_signal_trusted` 保持 false，具体 run 没有有效授权 manifest 时
   `rh2_formal_training_allowed(run)` 保持 false；
3. **S2 最小完成定义**：采用 §2.4 的 reward-integrity 必要集，不把
   claim-check、SFT/exporter、microVM 和完整展示型红队套件作为首训前置；
4. **恢复语义**：采用已发布边界联合 checkpoint、frontier-discard receipt 和
   空 buffer 的新 run segment；接受最后一段未提交 frontier 被丢弃及小范围采样
   跳过/重复，不做 pending replay、精确 cursor resume、recovery fencing 或
   optimizer exactly-once；
5. **资格 taskset**：从训练候选面选一个通过环境门、与评测面隔离的小集合；
6. **GPU 敏感配置**：冻结精确首训拟用值，或批准 qualified envelope 及其最坏点/
   边界点验证；
7. **跨 publish batch prefetch**：首版关闭，保留持续 producer，按 §2.5 计量
   GPU 成本；
8. **正常 shutdown**：作为首训资格硬门，任何外部强杀或残留资源都算失败；
9. **资格作业授权**：总正式训练闸门为 false 时，只允许预注册、限步、限预算、
   checkpoint disposable 的 `qualification_run_authorized` 作业进入 optimizer；
   Safety-Q 本身不得进入 policy loss；
10. **连续运行下限**：采纳 H5 推荐的 Segment A ≥3、Segment B ≥3 个 applied
    updates，或批准一个不低于该证据强度的替代持续性判据。

Owner 确认本文范围后，下一轮才编写正式实验 profile、启动闭包、阈值、故障注入和
验收器；不得从现有未审查脚本反推实验语义。


> **2026-09-01 取代注记**：本稿 §0.2 的 run-scoped 授权公式、三判定概念与解封仪式已被 `06-first-training-local-execution-plan.md` 的防御清理（§1 A3/A7、§6）否决,不再作为方案。本稿其余范围结论（campaign 结构、H1~H10、恢复合同骨架）经 06 收编。