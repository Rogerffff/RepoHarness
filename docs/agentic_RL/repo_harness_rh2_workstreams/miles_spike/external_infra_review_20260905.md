# miles + harness + rh2：独立 infra 审查

日期：2026-09-05。对象：当前 miles 候选生产链。性质：代码、架构、数值与故障模型审查；**不是训前总验收，也不翻转任何训练闸门**。本次未修改实现、测试或依赖，未启动 GPU 或真实 Docker 作业。

> **2026-09-06 补充**：与 Claude 报告交叉复核后，确认本轮遗漏了 generated→trained 覆盖：REALIGN 可使前序响应整轮失去训练信号。原文关于剩余 token 对齐与给定 mask 的数值验证不能证明覆盖完整。新增预算/诊断/性能发现及对两份报告的纠正，见 [交叉复核](external_infra_review_crosscheck_20260906.md)。保留本篇原始审查记录，不将其视为完整训练语义已签收。

## 1. 结论与证据边界

用户对过度防御和 agent 自行决策的担忧部分成立。最有证据的情况不是“所有检查都过多”，而是：**一些局部防御仍维护旧策略，某些内部错误被包装成普通样本损耗，而大张量捕获在正常热路径承担了不必要的 Python 容器成本。** 应优先修这些具体边界，不应启动全仓库去 guard 或重写训练后端。

本轮确认三项问题行为，另有一项 R3 语义需要 owner 与 GPU 证据裁决。没有确认新增 P0，也没有确认 faithful DIS 的分母或 CP 切片公式错误。

| 编号 | 裁定 | 建议处理时点 | 证据强度 |
|---|---|---|---|
| F1 | P1：R3 捕获同步阻塞 adapter loop，且逐轮保留两种 routing 表示 | 长多轮 R3 / GPU 容量定档前 | 正常生产路径；真实 capture 的 CPU 实测；未测 GPU 吞吐/RSS |
| F2 | P1：未分类协议或内部装配错误可被转成 ABORTED，整组丢弃后继续 | 正式训练前，和当前三终态边界一起收口 | 当前入口故障注入 + 下游静态追踪；真实发生频率未知 |
| F3 | P1：receipt 写失败时仍跳过未冻结容器清理，与现行计划矛盾 | 租 GPU 前；与 W7 清理接线合并验收 | 当前入口故障注入；旧报告已有此策略，不能冒充新事故 |
| R1 | 训练语义决策项：最终 R3 tape 可替换早轮行为路由来源 | C 包 + R3 真机资格 | 真实装配复现 + pin SGLang 源码可达性；算法后果未定量 |
| C1 | 非阻塞清理：654 行未接线原型及 824 行专用测试 | 独立清理批 | 当前仓库配置无生产消费者；不宣称性能收益 |

主审与三个独立上下文角色分工核查：Production Tracer 追真实调用和状态 owner；Falsifier/Simplifier 尝试推翻问题与寻找更小方案；Training Semantics Reviewer 检查 reward、mask、组语义与 loss。主审重跑关键探针后裁决，未按多数票直接采纳子报告。

**基线**：主仓库 `ce2009f879cf38071d7898a1387e01d4e27741d6`；miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`、tree `c8687c9b33968c31e13becc4e3d249d97aec717a`；上游 miles pin `f2b7c79298a53c53861514d099f7def73bd29f4a`。集成 tree、patch 与 pin 前置校验通过。SGLang pin 为 `4e230c3d85cefdab5b65eeb6f6f87793a707a6fb`，Megatron pin 为 `235952df607b3820716e5e67728a5ab470ca33ae`。

**排除范围**：SWE 题单、暂定数据格式、环境四门、镜像质量、最终 evaluator 控制面、实际 reward 的任务正确性；历史 FA/legacy 不作当前运行链审查。未逐行遍历所有历史文件，也未逐篇精读整个外部资料库。外部建议依据本文直接引用的官方资料与实现，README 的二次摘要只作导航。

## 2. 当前真实调用链与状态归属

```text
miles train_async（driver）
  → Ray RolloutManager.generate
    → AsyncLoopThread（持续 rollout 的 owner loop）
      → FullyAsyncRolloutFn / SubmissionScheduler
        → generate_and_rm_group（n 个 member 并发）
          → Rh2MilesGenerateFn：identity / assignment / canonicalize
            → BringupService → RolloutOrchestrator
              materialize → ClaudeCodeDriver
              → drain/quiescence → 冻结产物持久化 → 提前释放 rollout 容器
              → 有界 GradingQueue → fresh grader → projection / gate / finalize
              → receipt / cleanup → miles Sample
        → DefaultDataBuffer.put：先处理 ABORTED，再执行完整组 admission
      → DefaultDataBuffer.get：以消费时版本判断 staleness
  → conversion：member reward → fan-out 广播 / execution 分母 / DP schedule
  → trainer：faithful DIS → optimizer（有真实更新才 dirty）
  → update_weights：逐 engine 发布并核对版本 → 下一次消费
finally → dispose_on_owner_loop → RH2 shutdown → miles dispose
```

这里的 `adapters/slime` 仍是 miles 每个 execution 真正使用的共享执行层。它包含模型调用捕获、黑盒 harness 桥接和编排；目录名字不能证明它已死。当前实际 harness 是 Claude Code，mock SimpleLoopDriver 是探针。`verifiers` 仍有 schema、任务绑定、评测/离线接口的作用，但不能把设计文档里的基座定位等同于“当前训练运行时已经由 verifiers 统一承载”。

| 所有者 | 实际持有的状态 / 并发边界 | 审查结论 |
|---|---|---|
| driver / trainer ranks | optimizer、checkpoint、发布顺序 | 最小冷恢复合同已定，不承诺联合提交或在飞样本恢复 |
| rollout owner loop | producer、member tasks、buffer、grading futures | 关闭从此 loop 执行；不是从 HTTP 线程直接操作所有 future |
| adapter aiohttp 线程及其 event loop | session registry、模型代理、capture commit | F1 的同步处理发生在这里，会延迟该 loop 的其它请求/清理 |
| execution / hook | sandbox lease、turn tapes、artifact bytes、Outcome/receipt | tapes 与 bytes 持有到 finalize，未找到逐轮释放 |
| grading queue | 默认 4 个 worker、8 个等待槽 | 满时 submitter 等待；rollout 容器已在评分前释放 |
| miles data buffer | 完整组队列，容量按 group 计算 | 满时 put 等待；已在飞的 member 仍能完成，buffer 容量不是全进程内存上界 |

并发预算也有粒度差异：`async_max_concurrent_samples` 折算为整组，n=8 时至少一组，配置小于 8 不能解释为严格的样本上限。当前没有据此确认新 bug，但做容量估计时必须计入在飞 member、等待评分对象与 buffer，不能只乘队列长度。

主要入口：`adapters/miles/generate_fn.py:113–237`，`adapters/slime/bringup.py:968–980,1243,2192–2248`，`adapters/slime/generate.py`；miles 的 `fully_async_rollout.py`、`fully_async_data_buffer.py:235–322`、`ray/rollout/train_data_conversion.py`。本文路径均相对 `rh2/src/repoharness2/` 或明确标出的 miles 集成根目录。

## 3. F1：R3 正常捕获的同步成本与多轮内存累积

**当前行为与位置。** `capture_wire.py:680,737–742` 的 `CaptureRegistry.commit` 同步调用 `GenerationCaptureHook.on_generate_response`，其 vendor 包装在 `:1284` 附近。`projection.py:140–171` 将 base64 int32 tape 解码为 Python 整数 list；`generate.py:764–773,967` 再打包存入 `artifact_store`，`:978–990` 同时把 tuple 留在 `TurnTape`。直到 `:4732–4735` 才逐 artifact 写盘。当前请求使用完整前缀 routing，没有请求增量片段；未找到逐轮 pop/clear。

**违反的实现目标。** 路由是每 token × MoE 层数 × top-k 的张量，当前把它当普通 Python 标量集合反复转换并长期双份持有，不符合长上下文并发的容量目标。这不是授权 guard 的问题，也不能把解码、打包与 digest 的合计耗时全归因于 hash。

**实测证据。** [capture 探针](external_infra_review_20260905/r3_capture_cost_probe.py) 调用真实 registry/hook，每行 48 层 × 8 个路由项，小整数 ID 0–7。主审首测如下；独立审查者另测约 74/150/294 ms，显示时间随本机状态波动，量级一致。

| routing 行数 | 同步 commit | 同 loop callback 延迟 | 累计 routing tuple + packed bytes 下限 |
|---:|---:|---:|---:|
| 8,192 | 86 ms | 86 ms | 36 MiB |
| 16,384 | 172 ms | 172 ms | 108 MiB |
| 32,768 | 346 ms | 346 ms | 252 MiB |

32K 这一轮本身有 48 MiB int32 wire、64 MiB base64，仅 tuple 指针与 packed bytes 就新增至少 **144 MiB**。专家小整数共享，因此下限按每元素 8B 指针 + 4B packed 计，没有虚增整数对象大小；原始 JSON、响应、临时 list 与其它对象尚未计入。

**影响与频率。** `production_reachable`，R3 开启后是正常每轮路径。它阻塞的是共享 adapter loop，不是所有 miles 线程。长多轮并发会累积内存，例如 **50 轮 × 平均 16K 行 × 48 × 8 × 12B × 32 个同时存活 execution = 112.5 GiB**；这是条件估算，绝非真实作业 RSS 或已发生 OOM。具体轮数与并发尚未在 C/W7 定档。

现有 `shutdown/resource_closure.py:96–107,161–166` 没有 MoE 层数、router top-k 或 R3 项，无法表达这笔已知成本。该估计器自己已标为 `unbounded_or_unknown`，不能指责它虚假承诺硬上界；问题是它遗漏了容量决策所需的重要项。其它逐 attempt 增长的 audit/outcome 集合也已登记为无界，不另造一项新事故。

**推荐与代价。** P1，在长多轮 R3 容量定档前处理。优先紧凑 int32 表示和 native bulk 操作，减少“解码为 Python tuple → 再打包”的双份常驻。不要直接只保留整个 session 的最后一轮，fan-out 的不同 leaf 可能各需不同末轮。把 commit 简单移到线程会改变提交/引用可见顺序，且未必消除 GIL 成本，不是无需论证的修复。

**验收条件。** 相同 token、shape、route ID、digest 和分支产物保持一致；本探针的 retained bytes 与同步占用显著下降；资源说明显式计入 R3 或明确排除。再用计划中的真机负载测 peak RSS 与事件循环延迟。不要在此新增 quota 平台、长期 owner 或新的样本拒绝路径。表示变更只改成本；若转成增量路由，必须先处理 R1 语义。

## 4. F2：内部协议错误可被转换成普通丢组

**当前行为与位置。** `generate.py:3445–3449` 的通用 `except Exception` 调用 `_abort_after_task_local_exception`；`:3511–3516` 对未映射原因按 stage 兜底，最后产 `missing/ABORTED`。finalize/交付内的特定契约错误已 fatal，但同类矛盾若在此前的 assemble 阶段发生，仍可能软收口。

**具体触发链。** 上游响应有正常 token、logprob、版本，仅缺 `meta_info.id`：

```text
GenerationCaptureHook 产生 failed record，但不产生 TurnTape
  → CaptureRegistry.commit 返回非空 record_id
  → vendor wrapper 仍可把引用绑定到 tree
  → backfill 查不到对应 tape，抛 capture_record_unknown_in_backfill
  → 通用异常收口：missing / ABORTED
  → miles put 在 dynamic filter 前整组 drop，继续补组
```

源码：`generate.py:806–829,2883–2889`；`capture_wire.py:737–750,1284–1299`；miles `fully_async_data_buffer.py:239–256`。严格 group admission 无法挽救这条路径，因为 ABORTED 已在它之前消费。

**不变量与证据。** 06 附录 A 已批准“引用、身份、reward、mask、logprob 等账实矛盾走 FATAL；ABORTED 只来自已归因 task-local 故障”。[故障探针](external_infra_review_20260905/failure_probes.py) 的 `wire_commit_missing_meta_info_id` 使用真实 hook、registry 和 formal 编排，仅删响应 id；输出 failed record、0 tape、非空引用，最终为 `capture_record_unknown_in_backfill + ABORTED`。HTTP、tree 与 Docker 是夹具，真实 tree 绑定路径另由源码核对。

**影响与可达性。** `production_reachable` 的协议故障注入；未观察 pin SGLang 真机返回缺 id，频率未知。任意 TypeError 与 leaf-facts 长度错误只是分类对照，标为 `test_only`，不另报生产 bug。风险是受影响组系统性消失而训练继续，可能偏向不触发问题的轨迹类型；不是已证明坏 logprob 进入 loss。audit/drop 事件确实存在，不能称为完全静默；但只要好组持续到来，no-progress 并不保证停止这类部分失败。

**推荐与代价。** P1，正式训练前收敛。明确、已归因的 task-local 错误才能软收口；未知程序异常与结构矛盾默认 fail-stop，协议错误在最早可辨认处 typed raise。不要继续逐条扩充越来越长的 FATAL 特判表，也不要借机改变尚待 C 决定的 timeout/truncation 策略。无需新 ledger、retry 或 fallback。代价是内部 bug 会让作业显式失败，需要修复重启；正常轨迹不应因此新增拒绝。

**验收条件。** 缺 id 的结构矛盾不再返回普通 ABORTED，fatal 传到实际 worker/service halt；已归因 harness crash/单任务局部故障保留既定软失败语义。测试要经过实际 put 前的返回边界，不能只断言 helper 抛错。

## 5. F3：receipt 写失败仍支配容器清理

**当前行为与位置。** `generate.py:3598–3620` receipt 写失败时登记 quarantine；`:3646–3652` 以 `receipt_persist_failed and mode != s1_compat` 跳过 session drop 与容器清理；`:3767–3775` 最终 fatal。若容器尚未在冻结成功后提前释放，便留下它。

**不变量与复现。** 06 A4 要求核心 admission 记录写失败时“样本绝不交付 + run-fatal + 仍撤销 session/终止 scope/清容器，仅 cleanup 自身失败才 quarantine”。[同一故障探针](external_infra_review_20260905/failure_probes.py) 注入冻结前 harness crash + receipt `ENOSPC`，真实 finally 产出 `lease_released=false`、`docker_removed=[]`、`adapter_dropped=[]` 和一个 quarantine，最终 typed fatal。

**影响与可达性。** `production_reachable`，触发需要“冻结前失败 + receipt 存储失败”，频率未知；失败作业可遗留容器进程和可写层。成功冻结路径已经提前删除容器，不能泛化到所有 receipt 失败。service shutdown 的 `capture_sessions` 仍会撤销会话，不能声称永久可调用；`bringup.py:1805–1811` 的 residue 步骤只报告 quarantine，没有删除它。

**已知事实与分歧。** `wave1/w3a_report.md:38,111`、`w5a_report.md:139` 已明确保留旧 B5 策略，`test_b5_finalization.py:103–121` 也把保留容器写成正向 oracle。因此这是**现行要求与旧实现/测试未对齐**，不是第一次发现没有清理机制。`rh2/scripts/rh2_run_trap_cleanup.sh` 已存在；最终 launch trap 未接属于已登记 W7 接缝，`launch.sh` 本身是未审草案。

**推荐与代价。** P1，租卡前处理。删除“receipt 失败所以跳过清理”的旧分支，保留 fatal，仅清理动作自身失败才 quarantine；与 W7 trap 一起验证。只停 Python 进程不够，独立 Docker 容器可能继续存活。无需 WAL、持久 quarantine 管理器或恢复服务。代价是不能靠保留活动容器保存现场；诊断依靠可用的既有日志/冻结产物，不能为现场保留牺牲已批准清理要求。

**验收条件。** 同一 ENOSPC 仍无交付、仍 fatal，但实际执行 session 撤销与容器清理，首因不被清理失败遮掉；成功冻结路径仍仅删除一次。若 owner 想保留旧策略，需要显式改判，而不是让旧测试充当定案。

## 6. R1：R3 路由来源替换，尚不能宣称原行为路由完整保真

R3（记录并在训练时重放 MoE expert 路由）不仅要求行数正确，还需要说明重放的是哪一次 forward 的路由。

**已证事实。** `generate.py:1427–1468` 对多轮 leaf 使用最后一轮的完整 tape；早轮的 logprob、loss mask 和 weight versions 则仍按原轮保留。[真实 TrajectoryManager 探针](external_infra_review_20260905/r3_origin_probe.py) 构造两轮：第一轮路由 1、第二轮路由 7；合并后早轮可训位置变成路由 7，而早轮 logprob 仍是 `[-0.1,-0.2]`、版本仍保留 10/11。人工值只证明来源选择，不证明 GPU 实际差异率。

**生产可达性。** 核对 manifest 所钉 SGLang 官方源码：`reset_for_retract` 清空 prefix cache 索引与原 routing；重新 prefill 旧 prefix 后，state capturer 把当前 forward 的路由写回 host cache，默认返回当前全量前缀。因此跨 publish/retract，或者后轮在另一冷 cache engine 运行时，最终 tape 可包含重算路由。[Req reset 与 prefill](https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/managers/schedule_batch.py#L1674)，[get_topk 与 host cache 写回](https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/state_capturer/base.py#L147)。

当前 proxy 不冻结整个 trajectory 的权重版本，router 按负载选择 engine；miles 权重更新在 retract 后 flush cache。故来源替换是 `production_reachable`，不是需要未来新能力才有的反例。

**没有证明的内容。** 路由来源替换本身不等于 DIS 梯度公式已错。目标究竟要求逐 token 原始行为路由，还是接受最后整段重算路由，是算法定义及近似误差问题。miles stock `sglang_rollout.py:269–285` 也有整段覆盖，S1 实现说明已有这个 T1；不能说这是 RH2 最近独有的拼接回归。S1 dense 模型成功不能证明 MoE 路由值保真；shape 正确、pop 耗尽也不能代替内容来源证明。

**提交 C 包的最小决策面。**

| 选择 | 能解决什么 | 成本与剩余未知 |
|---|---|---|
| 显式接受“合并序列 + 最后整段路由”的近似 | 不改变当前装配与吞吐结构 | 必须测 route agreement、replay logprob/ratio 偏差，并如实限制保真主张 |
| 各 turn 分别构造训练行，只训该轮新 token，保留 execution 共享分母 | 可保留跨 turn 的原始上下文与 tape | 重复 prefill/训练成本增加；**单个 turn 内跨 publish 的 retract 仍可能替换其早段路由** |
| 缩小首个 profile 的 R3/跨版本使用面 | 降低首次实验变量 | 不能据 R3-off 代替原计划 R3-on 资格；若改变既定目标需 owner 改判 |

推荐先完成内容级 GPU 对拍，再选最小充分方案，不立即构建长期 routing 状态机。把各轮旧 decode rows 简单拼进最终 tape，不能自动恢复多层上下文/KV 的因果来源。

**验收条件与 owner。** C 包由用户决定语义，实现者提供两种场景证据：跨 turn publish，以及同一 generate 内 retract。保留原始 token/tape/span，比较早轮生成位置与最终训练 route，并核对真实 replay logprob 与更新。没有该证据前，表述为“routing transport/replay 已接线”，不要表述为“所有原始行为路由已证明精确重放”。

## 7. 已验证正确的部分，以及不应盲删的检查

本轮 [96 例数值探针](external_infra_review_20260905/semantics_probe.py) 经真实 `loss_function → faithful_dis_loss_function → reducer`，用独立小词表 logits 计算 support-normalized logprob、detach IS 权重、execution 分母和梯度。覆盖 CP=1/2/3/4、thd/bshd、变长/空 CP response 分片、DIS 区间内外。最大 loss 误差 `1.11e-16`，logits 梯度误差 `6.94e-17`。

范围严格限于 CPU `true_on_policy_mode=True`；CP 计数 collective 被替换，并行状态和 Megatron 归约因子由探针模拟。不证明 GPU fused cross entropy、TP/PP/NCCL、真实 CP 执行和 optimizer。

[conversion/schedule 探针](external_infra_review_20260905/grpo_probe.py) 用两个 n=8 组、16 个 execution、30 个 fan-out leaf，独立验证成员级均值/标准差、reward 广播、execution 的 mask 总分母以及同一 execution 不跨 optimizer step。结果为两个 step 各 8 个 execution，分母集合 `[1,3,6]`。未发现“叶子多的执行自动取得更大组基线权重”。DIS 拒绝的 token 仍留在 provenance 分母，未出现过滤后重新放大。

正确实现的组政策也有代价：全员 KEEP_FULL 下，假设每个成员独立有 90% 可保留率，n=8 的整组保留率只有 `0.9^8≈43%`。真实失败并不独立，这个数只是说明放大效应；如果失败与长度/难度相关，补采可能改变实际训练分布。这是已批组政策和待定 A5 的取舍，不是可以自行改成拆组或 MASK_MEMBER 的 bug。C/W7 应根据已有 drop 事件判断代价，而不是把所有未解题都归为无效样本。

| 看起来可疑的点 | 本轮裁定与证据 |
|---|---|
| R3 遇到中间上下文变化必然裁错 token | 未证实。真实 builder 的 CLEAN/REALIGN 三步保持 `tokens=当前 prompt+output`，FORK 新 builder 同构；未把伪造 helper 的错位升级为当前 bug |
| 多层 identity / group admission 都是官僚检查 | 不成立。转换后的绑定与真实完整组消费是不同边界；当前 filter 核对 n 个 member、fan-out、reward、版本和 slot，删除会改变入训集合 |
| staleness 重复把关 | 当前 finalize 只检查版本事实，唯一 age 阈值在 miles consume-time；旧第二阈值已删，不能按旧文档重报 |
| hash 必然拖慢每轮训练 | 没有这种性能证据。prepared 文件/manifest 在启动加载，admission 为内存对象核对；F1 应归大张量转换及持有，不能泛化为删全部 digest |
| shutdown 的 broad catch 都该删 | 不成立。清理中保留首因并继续其它步骤是必要行为，与 F2 正常主链把程序错误变 missing 不同 |
| 测试多足以证明可靠 | 不成立。F3 的旧 oracle 固定了过期行为；应检查 oracle 是否仍对应现行定案，不能只数 passed |

## 8. 可减少的维护面与不值得现在做的重构

| 对象 | 处置建议 | 理由 / 限制 |
|---|---|---|
| `adapters/miles/attempt_ledger.py`、`governed_buffer.py` | 独立删除或移出生产包 | 394+260=654 物理行，当前候选配置没有消费者；06 已允许 spike-only 保留或单独清理 |
| `test_governance_buffer.py`、`test_governance_receipts_lifecycle.py` | 随原型删除 | 572+252=824 物理行，另清包导出与专用 fixture；共享 fixture 不连带删 |
| generate_fn 的“治理件未来接线”、miles 包的“slime 不改动”说明 | 更新为当前事实 | 文案仍反映冻结旧计划，影响新读者定位 |
| slime generate/bringup/async_worker | 标出共享职责，后续局部拆分 | 5001/2443/1315 物理行，但均含当前消费者；不要临训按目录批删或大重命名 |
| 历史 inspector、精确 lane 数量与证据文件 | 继续冻结，不扩建 | 属历史/离线维护成本，没有证据显示每条当前 rollout 都经过授权仪式 |

“654+824=1478 行”是明确的原型维护面，不等于 1478 行坏代码，也不预言加速比例。Python 外部动态配置仍可导入原型，所以这里的结论是**当前仓库配置无消费者**，不是永远不可调用。

消费者复核可从仓库根目录运行：

```bash
rg -n 'Rh2GovernedBuffer|Rh2AttemptLedger|Rh2GovernanceConfig|attempt_ledger|governed_buffer' rh2 --glob '!uv.lock'
rg -n 'Rh2GovernedBuffer|Rh2AttemptLedger|custom-async-data-buffer-path|rh2_governance' rh2/experiments rh2/scripts reference/miles-rh2-integration/train_async.py reference/miles-rh2-integration/miles --glob '*.py' --glob '*.sh'
```

不建议围绕异常再建立通用规则引擎，也不建议为了更容易维护旧验收报告再写一个报告框架。本轮三个问题都有局部方案；不满足需要新增平台的条件。

## 9. 外部能力校准：项目的说服力应来自哪里

你的目标可以成立，但“把先进团队用的组件都补上”不是可靠的选择标准。miles 官方已经提供 fully async、TITO、R3、OPD 和多种接入方式；这些能力应准确归属于上游。RH2 的贡献要通过真实 harness 下的语义、故障处理、资源效率和接入代价证明，而不是把上游能力重新列为自己的创新。[miles 官方发布说明](https://www.lmsys.org/blog/2026-08-18-miles-v0-1)。

### 9.1 首先缺的是可比较的证据，不是更多调度组件

当前本地单测不能证明 fully async 比合理基线更快，也不能证明更快的生成最终产生更多有效训练信号。RollArt 的消融显示放宽异步程度存在速度与 time-to-score 的权衡；这一观察支持本项目测完整训练收益，不能直接搬其大型异构集群结构。[RollArt 原文](https://arxiv.org/html/2512.22560v2)。

建议沿用 W7 collector/judge，做一个固定模型、任务负载、harness、预算和 loss 的小型 matched comparison：

- 效率：有效入训 execution/token 每 GPU-hour、trainer 等待、publish/retract 耗时、环境和评分等待、peak RSS。原始生成 token/s 单列，不能代表训练有效吞吐。
- 语义：生成→交付→准入→超龄丢弃→实际消费的守恒；版本跨度、DIS 实际保留比例、零信号 step。重跑时不把 fan-out leaf 当独立 execution 计数。
- 闭环：同等预算的 before/after eval；若能力未涨，区分信号不足、训练数值问题与 infra 效率问题。数据质量部分留待后续。

这些是建议的实验读数，不是要求新增全套监控服务。对比已有可运行路径，离线协议测试不需要放松安全边界；不要为了做 baseline 把真实训练中的评分隔离关掉。

### 9.2 OPD 是合理扩展，但当前还不是 RH2 已打通的能力

OPD 用学生自己的 rollout，让 teacher 为同一序列的 token 提供概率，再形成逐 token 的 reverse-KL 信号；不是让 teacher 另生成答案做 SFT。miles 已有 sampled-token 与 top-k 路径，可与 RL advantage 组合。[Thinking Machines 方法说明](https://thinkingmachines.ai/blog/on-policy-distillation/)，[miles OPD 文档](https://miles.radixark.com/docs/advanced/on-policy-distillation)。

当前 RH2 `canonicalize.py:419` 能运输 `teacher_log_probs`，但当前生产接线没有 teacher scorer；miles 上游的 `on_policy_distillation.py:352,403` 才是 teacher reward/postprocess 消费链。现有 RH2 admission 绑定的是 grader 的标量 task reward。**字段兼容不等于 OPD 闭环，不能仅加 `--use-opd` 就宣布完成。**

首轮 SWE RL 闭环后，最小合理扩展是单一同 tokenizer teacher、sampled-token scoring：明确原始 token/context 与 teacher 的对应、temperature/支持集概率口径、逐 token mask、teacher 失败语义、与 task reward 的组合。先做小型梯度/运输对拍，再讨论 top-k 或多 teacher。teacher 失败不能默认为“RL 任务失败”；这会改变训练分布，属于需要 owner 决策的新增语义。

### 9.3 多 harness 要以第二个真实消费者证明

当前 `bringup.py:1113,1142` 的实际构造是 ClaudeCodeDriver / mock SimpleLoopDriver。类型里允许 `codex`，或 vendored 代码存在另一个 driver，都不等于该路径已被本项目接好。

闭环后建议接一个简单、可读的第二 harness，验证同一 token/provenance 与执行结束接口能否复用，并记录接入改了哪些模块。这比先加五种 harness 的配置更能证明架构。compaction/subagent/fork 仍在 C 包，首训只需明确一个可验证 profile；长程上下文变化的覆盖比“所有工具全开”更有价值。

### 9.4 两项有依据、但需要按收益决定的扩展

MiniMax M2 原文 §6.2.4–6.2.5 分别讨论完成先到造成的训练批次组成变化，以及共享前缀只计算一次的训练加速。这两项与本链路有关，不能直接照搬其参数或加速数字。[MiniMax M2 官方报告 v1](https://arxiv.org/html/2605.26494v1)。

**完成顺序的分布影响。** 当前 miles `fully_async_rollout.py:232–241` 将完成的 group 放入队列，`:394–430` 先取足 batch，再按 index 排序。批内排序并不改变已选中了哪些 group；staleness N 也不限制派发序列的乱序跨度。因此值得用受控长短 group 和现有事件展示 dispatch→consume 顺序，再看真实短跑的完成时长与丢弃关系。本轮没有证明实际训练已因此失稳；窗口调度改变采样/训练时序，应在测出问题后作为 T0 对照选项，不能直接升级为首训必须实现的新组件。

**训练前缀的共享计算。** vendored `trajectory.py:328–336,456–475` 将 leaf 线性化，并把已训练过的共享 response 置 mask=0；这解决重复计 loss，却不会免去每个 leaf 的前缀计算。miles `training_utils/data.py:203–206,222–226` 仍按完整样本长度拼接并执行常规 packed forward。闭环后先测重复前缀比例和训练时间占比，再决定是否值得接入 prefix-tree 训练。该扩展必须与独立样本基线对拍 logprob/梯度，并核验 R3、CP、DIS；论文的等价性或最高加速值不能直接当本项目证据。

### 9.5 暂不建议补的组件

目前没有证据要求本项目新造多租户服务、serverless reward 平台、粘滞路由、dead-engine 自动恢复、joint checkpoint、动态规则引擎或第二套训练调度器。大规模系统的功能不自动适合 8 卡项目。若真机 profile 表明 prefix cache、publish 或评分成为主要瓶颈，再评估上游已有能力及最小集成成本；不要先以“前沿性”为理由扩建。

更有说服力的项目叙事是：说明上游基座，明确自己解决的跨 harness 训练语义/生命周期问题，提供受控对照与可重现故障案例，最后完成实际训练闭环。项目能否支持求职还取决于结果和你对取舍的解释能力，不能由功能清单或代码量保证。

## 10. 覆盖、故障证据与仍未关闭的事项

### 10.1 本轮实际执行

完整命令、探针与输出在 [复现材料](external_infra_review_20260905/README.md)。

| 验证 | 本轮结果 | 能证明 / 不能证明 |
|---|---|---|
| 当前集成基座的 adapters_miles + governance + W5a shutdown 测试 | **801 passed，0 skipped，0 xfailed，17 warnings，51.44 秒** | 选定本地链路回归；不是全仓测试，也没有真实 Docker/GPU |
| 运行时审查者独立跑 W4/W5a/W5b/W10/residue | **151 passed，16.60 秒** | 与上项有重叠，不加成独立 952 项 |
| 独立 DIS 数值/梯度 | 96 例通过 | 小词表 CPU 算法与切片代数；不证明真实并行训练 |
| 独立 GRPO / fan-out / schedule | 16 executions → 30 leaves → 两个各 8 execution 的 step | 转换前后身份与分母守恒；不是整个真实作业的派发账本 |
| 四项故障探针 | 均观察到当前断言行为 | 证明 F2/F3，不代表修复通过 |
| R3 来源 / capture 成本 | 确认来源替换与本机成本 | 不证明 GPU 数值损害或真实作业内存峰值 |
| integration lanes `--checks-only` | tree / patch / pin 通过 | 明确未运行正式双 lane，不宣称 lane 资格 |

17 个 warnings 为 14 个 torch JIT 弃用提示和 3 个单进程 DCP 提示。数值探针运行时另提示未安装 Megatron/deep_ep；这些探针刻意不调用真实分布式引擎。

### 10.2 跨边界不变量与 A~N 适用性

| 维度 | 实际核查与结论 |
|---|---|
| A 正确性/并发/失败 | 真实 owner-loop dispose 与双线程测试；F1/F2/F3；真实 GPU/kill 不在证据内 |
| B 训练分布 | member reward、execution 分母、DIS 拒绝分母、F2 丢组；A5 未定，不擅改 |
| C 挡板 | 对照 D2/B v2 与当前简报，见下表；未建议恢复已删除授权/扫描门 |
| D 所有权/配置 | 上述 owner 图；并发的 sample/group 粒度；唯一 staleness 消费者 |
| E 测试有效性 | 独立 oracle；标出 F3 旧 oracle、人工 TypeError 的证据限制；不按 passed 数签收 |
| F 一致性 | F3 的现行 A4 与旧 B5 冲突；旧 FA 文案不覆盖当前定案 |
| G 生产可达性 | current generate→buffer→trainer 路径；每个运行时 finding 单列 reachable/observed 限制 |
| H 唯一事实源 | prepared 可信输入、identity/admission join、版本阈值；R1 区分 route 来源与版本列表 |
| I 分期 | 三项局部处置、一个 C/GPU 决策，原型删除非阻塞；不给理论反例 P0 |
| J 可读性 | 已定位的未接线原型、过期文案、大共享模块；不要求全仓风格重写 |
| K 演进成本 | 未分类异常的默认行为优于不断追加特判；第二 harness 和 OPD 尚无真实闭环消费者 |
| L 性能/容量/活性 | F1 实测、两级反压、无界集合、no-progress 范围；真机吞吐待测 |
| M 可诊断性 | drop/audit 存在但不能替代 F2 fatal；作业守恒与零信号 step 需最终 collector 消费 |
| N 外部依赖 | integration pin/tree/patch 校验；读取 pin SGLang；升级能力不自动视为当前可用 |

SWE 数据/环境质量不在本轮，因此 A/B 中涉及任务本身与 reward 真值的部分明确排除；不能将本表视为安全或数据阶段验收。

### 10.3 故障注入与账目守恒的边界

| 故障类 | 已有证据 | 未证明部分 |
|---|---|---|
| crash | F3 的 harness crash；已有 worker 首因传播测试 | 真正 process-kill 后 Ray/Docker 状态 |
| cancel | W5a 双 loop dispose、active group 不响应取消时有界放弃 | 黑盒 CLI/GPU 卡死的实机回收 |
| timeout | W4 no-progress、W10 router 查询/发布版本超时、W5a shutdown timeout | 全 run optimizer/publish 的实际 watchdog 上界 |
| retry | W1 身份/attempt 换号与 assignment 测试 | 不主张 pending replay/exactly-once；外部引擎实际重试开销 |
| restart | W5b cursor/version 缺失/损坏/首次 publish 校验 | 真 Megatron 全 checkpoint 加载；W7 RESUME_FROM 接线 |
| artifact sink failure | F3 receipt ENOSPC + 现有 finalization 测试 | 真磁盘/容器故障组合与 trap 兜底 |
| queue full | buffer put/get 等待者关闭唤醒、grading 满队列反压测试 | 长时间 CPU/RSS/GPU 容量稳定性 |

本轮没有运行一个完整实际训练作业，**不能重建全作业的“分派=交付+失败+放弃+在飞”最终总账**。已经重建的是 conversion/schedule 的 16 个 execution 守恒，以及单 attempt 故障终态。最终 W7 仍需消费现有事件重建端到端守恒；这是本次外部代码审查与正式集成验收的界限，不用新增持久 ledger 填补。

### 10.4 当前挡板、开放项与处置归属

| 项目 | 本轮对照结果 | 下一步责任与时点 |
|---|---|---|
| S1_TIER_CAP、逐轨迹能力事实、第二 staleness 阈值、projection 扫描资格 | 已按 D0/D2/B 删除，不恢复 | 无新增工作 |
| runtime profile 创建约束、真实版本与身份/token/reward 检查 | 保留，属于科学有效性和执行约束 | 实现者维护；真实 profile 由 C/W7 验证 |
| A5 horizon / hard-wall disposition、最终 loss、N、harness 工具面 | C 尚未决定 | 用户在 C 决定；本报告不代定 |
| R1 R3 来源语义 | 本轮补入决策面 | 用户 C 决策；实现者与审查者做内容级 GPU 对拍 |
| W8 eval transport | 当前简报已列未完 | 实现者沿原计划闭合，不视为新增缺陷 |
| W7 launch trap / RESUME_FROM / 新 run_id / judge 事件消费 | 已知未接线草案 | 实现者租卡前闭合；F3 同批验收清理 |
| R1 容器可写层预算（既有编号，与本报告 R1 无关） | 已知只记录未强制 | 沿现有 W7 责任关闭，不建通用 quota 平台 |
| CP=2、normalize_advantages=false、单 rank 失败等 watchdog | 已知 C/GPU 开放项 | 用户定故障合同，真机验证；不报为本轮新 bug |
| F1/F2/F3 | 本报告建议，尚无实现方正式回应 | 实现者逐项回应并做局部修复；影响正常训练语义时交 owner |
| 原型/文案清理 | 非阻塞 backlog | 独立清理批，不混入生产语义修复 |

全部本轮 finding 可由现有 A~N 表达，无需新增维度。一次审查没有命中某维度不能证明该维度可退役；本轮最明显的改进空间是让历史 oracle 和当前定案对齐，而不是继续增加审查维度或报告数量。

## 11. 建议收口顺序与停止条件

用局部改动收敛 F2 异常分类与 F3 清理，并处理 F1 的紧凑表示/容量；这些工作可与 W8 并行，按各项表列时点验收。R1 随 C 包与 GPU 对拍裁决，不阻塞 W8。上述实现建议新增长期 owner、retry、fallback 或治理服务均为 **0**。F1 正常路径只应改变表示成本，F2/F3 应恢复既有失败合同，不新增对正常轨迹的静默剔除。

主线继续原定 **W8 → C → W7 → GPU 资格**。当前稿不能替代这个顺序，也不允许用数值单测绿灯宣称首训可运行。对已定的最小冷恢复，不因能构造更复杂 crash 窗口就要求 joint commit；对已登记的长跑资源问题，用即将执行的 profile 测量。

本轮停止条件：当前入口、线程/状态 owner、训练分母与组成员、主要异常传播、发布/恢复/关闭已完成一次聚焦审查；高风险候选已反证并提供可重跑证据。F1–F3 按表列时点处置，R1 随 C/GPU 处理，其余进 backlog；不再增加 W8 前置审查。**“还能想出边界情况”不构成继续阻塞理由。**

按项目报告口径：待拍板 T0 仅为 R1 的训练语义及原有 C 项；本次无生产 T1 决策、无挡板变动、无实现修复。推翻的候选包括“slime 全包可删”“中间 token 裁剪已经证明有错”“重复 hash 已证明是主要瓶颈”。测试与证据如上；不修改 spike-log 的既有阶段结论，以免把外部审查误写成实现收口。
