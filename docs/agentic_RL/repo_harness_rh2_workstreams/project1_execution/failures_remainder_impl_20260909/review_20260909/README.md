# 下一批计划审查：N1–N3 与第三组草案

日期：2026-09-09。主审：Codex。受审源码 HEAD：`92d165aa1dae5a660557f5f07cc702c3dee62ea3`。这是**写码前的计划审查**，不把尚未实现的方案缺口写成已经发生的训练事故。

受审材料：[Claude 开工说明](../../tmp/claude下一批开工.md)、[第 2 组剩余实施 Brief](../README.md)、[第三组决策草案](../../batch3_training_signal_20260909/README.md)。决定依据：[决策分组 §4.1 / §7](../../decision_batches_20260908.md)、[已批重评分范围 §8](../../batch2_failures_20260908/i15_i16_sampling_and_retry_20260909.md)。

## 1. 结论与开工顺序

**三项方向都符合已批决定，但不宜照原稿直接实现 N2/N3。** 有两项 P1 计划缺口：N2 依赖了当前不存在的评分总期限；N3 的最终关闭证据不完整。N1 有两处观测口径需要先修正。它们都是落实已有决定所需的实施修正，不要求 owner 再批准相同语义。

| 切片 | 结论 | 开工条件 |
|---|---|---|
| N1 丢组成本 | 方向通过；按 §4 修正计数、连接和事件含义后可做 | 不等待第三组；可以先做纯汇总器及对应数据例子 |
| N2 窄重评分 | 允许范围已批；先补 §2 的真实期限与取消接线 | 可以先写期限及生命周期部分，再启用最多两次的循环；不必等 N3 |
| N3 退出改判 | 行为和 fork 修改位置都已批；§3 的改判证据需补全 | 在最终关闭条件可验证前保持旧非零结果；不以新增 supervisor 或全关停重构作为默认修法 |
| 第三组 | 可保留为讨论草案；不能整包当作已批准的实施规格 | 已批纯观测可先做；I18 来源要求仍单独讨论，见 §5 |

**删掉 Brief §6 的两次重复确认。** I13 的 fork 文件已明确列在决策分组 §4.1 的批准实施位置，并写明沿现有 miles patch 维护方式落地。N1 同时观察消费组和丢弃组，正是已批比较所需的两边数据，属于 T1；不需要为每组几条小事件再请求批准。每个 fork 实施提交仍应同步现有补丁交付方式。

Brief 顶部和开工说明中“合同 A 与 F1 待复核”已过时：[预算第四次窄复核](../../budget_loop_impl_20260909/combined_review_20260909/followup4/README.md)已关闭两项，预算批次可以收口。此次不重开它们。

## 2. R1（P1，N2）：评分总期限目前没有生产接线

**计划位置：** Brief 第 51 行“同一评分预算（外层 `scoring_timeout` 不重置）”；第 56 行验收只列重试次数与队列并发，没有总期限反例。

**当前事实与不变量：** 已批条件要求等待、准备、重试共享一个有界评分预算。实际调用是：

```text
generate.py::_finalize._grade（5118）
  → bringup.py::_grading_submit（1801）
  → GradingQueue.submit（queue.py:223–224）
  → 独立 worker 的 manager.grade（queue.py:251）
```

上述链没有总评分 deadline。`scoring_timeout` 在 `rh2/src/repoharness2` 与 vendored `slime` 的检索结果只有 `manager.py:595` 一条旧注释。`_ensure_image` 的锁、inspect、pull（1291 起）与 `_start_container` 的 `docker run`（1380）也不受共同期限限制；已有 reset/apply/test 分段 timeout 不能补上这个缺口。

**具体后果：** 即使最多两次，第一次镜像查询或 pull 卡住也可能持续占着评分槽位。仅给提交方加 `wait_for` 仍不够：提交方等待的是 `item.future`，评分在另一个 worker task 中执行。主审复跑真实 queue 探针，提交方超时取消后，worker 未收到取消、`active_grading_count=1`；真实 manager 配 Docker 通道替身的对照中，放开查询后还会继续执行 pull。没有使用真实 Docker，也没有测量生产发生率。

**最小修改要求：**

1. 写清评分工作期限在哪个入口建立，怎样沿同一个 queue item 传到 manager；覆盖入队反压、排队、镜像锁、两次准备与两次之间的收口，不在第二次重置。
2. 到期约束实际评分工作，不能只取消提交方 future。到期或 shutdown 后不再启动追加尝试；取消/收口期间出现的 typed fatal 仍走已有传播通道。
3. 评分工作预算耗尽后，仍允许沿既有独立清理预算回收持有资源；不能用“总预算为零”跳过清理，也不能在清理结束后获得新的评分额度。明确当前阶段的错误归类，不顺带决定第四组的 reward 规则。
4. 明确第二次尝试前读取哪个现有停止状态。`grade()` 入口检查一次 `_closed`，不能自动证明稍后的第二次仍被允许；保持正常排空既有工作的合同。

**同一切片的生命周期验收约束：** 临时 `_ContainerRecord` 不能只作为 `_close_container_scope` 的局部参数。该函数允许“已停止但尚未删除”返回；此时对象仍需进入 manager 的现有清理记录，追加尝试使用新 nonce/容器名，最终 gc/close 能看到两次对象。主审复跑条件探针：未登记的临时 record 在 rm 失败、inspect 明确 false 时正常返回，随后 `manager.close()` 报 `containers_open=[]`。这是待实施分支的反例，不是对现有正常创建路径另报新 P1。

**必要验收：** 排队耗尽；镜像锁耗尽；首次失败和旧容器收口吃光预算；第二次期间到期；提交方已取消；shutdown/run-fatal 后不重开；stopped-but-not-removed 对象仍可清理；两次合计上限与最终只交付一次评分。测试走真实 queue→manager 关系，外部 Docker 操作可以替身。纯错误映射测试不能代替这些用例。

**分期、代价与停止条件：** 这是启用 N2 前的要求。现象在当前调用链可达，频率未知；有界预算已批，继续遗漏会使重试无法兑现自己的运行合同。优先沿既有 queue/manager 修正，不建重试服务。写清上述接线并纳入对应验收即可实施，不因本项扩大检查无关评分阶段。

## 3. R2（P1，N3）：RH2 在飞表清空不足以批准成功退出

**计划位置：** Brief 第 67–68 行，以 RH2 的 `unfinished_after_cancel_wait == []`、空 residue、evidence 成功与无 fatal 解消 miles 等待快照。

**当前事实：**

- `LifecycleState` 登记/注销的是 member 执行 task（`shutdown/chain.py:204–236`；`bringup.py:1769–1777`）。miles 另持有 `_worker` 和 `_active_groups`（`fully_async_rollout.py:209–241`）。清空前者不是后两者的最终状态证明。
- `FullyAsyncRolloutFn.aclose()` 缓存第一次关闭报告（259–260、330）；第二次调用它仍会拿到旧快照。`rh2_shutdown.py:220` 当前也只读第一次返回的 worker exception。
- “没有 fatal”不等于必要执行记录成功。取消期间 receipt 写失败可以只进 audit 的 secondary failure，保持原 `CancelledError`；`_run_finally_section` 的这一行为见 `generate.py:4215–4242,4399`。主审用真实 formal orchestrator 与真实 inflight 关闭步骤复跑，成功/失败对照都显示任务结束、容器被移除、`unfinished_after_cancel_wait=[]`、fatal 数为 0；区别是失败案 receipt 数为 0，audit 里有 `finalization_receipt_write_failed`。这不能由 shutdown 报告自身的写入成功代替。
- 当前 `container_residue`（`bringup.py:2014`）取隔离列表、grader 记录等，不能把这些集合为空直接描述成所有 rollout 容器均已确认删除。上一批已登记的二次取消清理残余继续留在原 backlog；本次改判不能绕过必要资源的证据缺失。

**按原稿实现的风险：** 首次等待留下的状态已经过期，最终只看 RH2 表，就可能把未收集的外围任务状态或必要记录失败一起当作“等得稍久但最终成功”。当前代码仍维持非零；这里是**即将新增成功分支的设计缺口**，不是宣称当前作业已假绿，更不是 P0。默认 worker 没发现吞取消造成永久挂起的处理，stubborn-task 测试不能冒充这种生产事实。

**最小充分方案：**

1. 由原 miles owner loop 在最终合成 verdict 前复查实际 worker/group task 的完成、取消和 exception；保存第一次等待快照作诊断，收集晚到异常。不新增任务 owner，不用第二次 `aclose()` 代替复查。
2. RH2 提供它负责的执行、资源及**必要**记录完成事实。已收到的 receipt/audit/cleanup 失败不能被“task 已 done”覆盖；缺证据就维持旧失败结果，不要求自动恢复。N1 这种可选观测事件写失败仍遵守自己的非 fatal 合同，不能扩大成新的必需证据。
3. 只解消已经验证消失的等待问题。`rh2_shutdown.py:243–281` 已会把该等待失败填进 `primary_cause` 并传给 RH2，`ShutdownReport.ok` 又要求 `first_cause is None`（`chain.py:455–463`）。计划需明确怎样把**这一条可解消的等待事实**从当前失败原因转为保留的历史诊断；只忽略 residue 会仍然失败，笼统清空 first_cause 又会吞掉真实错误。
4. “最终期限”写明所指的是当前 owner-loop 关闭范围，不把现有 900 秒限制描述成整个 driver dispose 的统一期限。不另定预算值。

**必要验收：** 首次等待 10ms、最终 60ms 安全结束可成功；相同形态但 task 未结束、晚到异常、必要 receipt 写失败、资源未确认删除均仍失败；原 driver/fatal/evidence 错误保持非零。成功例要能通过真实 fork verdict 与 RH2 报告合成，不能只测试一个手造 `resolved=true` 字段。

**分期、代价与停止条件：** 这些证据只约束 N3 新增的成功改判。不能证明的分支继续旧失败结果即可；不要求先修完全部关停 backlog。补齐证据来源、首因处理和上述正反例即可实施，不再为已批准的 fork 文件索取许可。

## 4. N1 两处 P2 观测修正

### R3：区分生成量、训练行大小和整组连带成本

**计划位置：** Brief 第 31–32 行。

`response_length` 是首轮 prompt 之后的整个 response 区域长度，包含后续工具/模板等 `loss_mask=0` 的上下文，不等于模型生成 token。真实 `_SampleBuilder.to_sample` 在 `rh2/src/slime/agent/trajectory.py:239–257` 直接这样构造。

本轮真实 builder 的小例子：两轮各生成 2 个 token，中间工具输出 100 个 token，得到 `response_length=104`、唯一生成量 4、`sum(loss_mask)=4`、总训练输入长度 106。把 104 命名为生成量会直接误导长轨迹成本分析。

**建议：** 复用可取得的 capture/tape 计数表示唯一已捕获输出；以既有 `turn_coverage.trainable_tokens_total`、`input_tokens_total` 分别表示表示层可训动作量与训练行输入规模，不将它们声称为实际梯度或 GPU 耗时。已知的 aborted 部分事实可保留，确实未取得才记 null。首版不要求为缺失轨迹重建 token。多个 FORK 训练行仍属于同一个 physical attempt，不能重复记成员。

`aborted_members` 用于找到导致丢组的成员及其根因；**整组成本要另连接同组所有已知成员**。例如七个成员各耗时 600 秒，第八个 5 秒失败，则已知成员占用时间合计为 4205 秒，不能只显示失败者的 5 秒，也不能机械写成八条完整轨迹。它是成员耗时之和，不是作业墙钟/GPU 时间。组含多个失败原因时保留原因集合或明确非互斥计数，不把同组成本在多桶累加后称为无重叠总成本。

连接至少按同 run 的组/attempt 身份进行；保留旧格式、缺失、未匹配、无 buffer 终局事件的观测。组终局数仍是现有分母；独立写明成员观测数，不把物理 attempt 和组都叫同一种 attempts。汇总继续保留 task 维度、消费侧对照和已有分段耗时；“长”不能直接当作“难”。

验收采用真实 token 例子，加上一组“七个长成功成员＋一个短失败成员”、多行同成员、多根因同组、外 run 与缺失记录。纯合成全 present 行不足以检验目标。

### R4：finally 中间的记录不能叫整个 attempt 的权威终态

**计划位置：** Brief 第 31、37 行，事件放在 audit sink 之前却承诺每个 attempt 的最终 present/aborted/fatal。

该位置之后仍可能发生：audit sink 失败而 fatal（`generate.py:4372–4396`）、交付 termination 盖章失败（`generate.py:2522–2540`）、miles canonicalize/身份接线失败（`generate_fn.py:187–215`）。finally 本身也可能因后续取消未到达发射点。因此“这一刻有 prepared/present 事实”不等于最终交付成功；fatal/取消且未进入 buffer 的对象也不在原组终局分母中。

**推荐较小方案：** 将它定义为编排阶段的成本快照，明确采集位置与 `disposition_hint` 只是当时事实，最终消费/丢弃仍由 buffer 事件判定；保留未关联项，不承诺所有已发起 attempt 恰好一条终局。复用现有后续 fatal/audit 事实，避免为观测再建终态管理器。若坚持命名 `attempt_terminal` 并提供最终 fatal 分类，就必须把发射放到真实返回/异常汇合后并覆盖这些后置失败，不能只换名字。

补一个“快照已发、随后 audit sink 或交付盖章失败”的对照，确保汇总不会把它算作实际消费成功。可选事件构造/发射失败不改变 receipt、交付与错误传播。

## 5. 第三组草案需要改准，但不阻塞 N1/N2

1. **I17 的 `dis_effective_tokens` 命名和定义不成立。** 草案第 11 行只取 accepted 且 support>1；优势为零的 token 也满足条件，却没有这一项的 policy 梯度。即使再加 advantage 非零，也只是“候选信号”，不能证明最终参数梯度非零。决策分组 §4.1 已写明这一点。建议保留原 accepted 口径，另记非单例数与候选信号数，候选定义为 `loss_mask=1 ∧ DIS accepted ∧ support>1 ∧ advantage≠0`。梯度抵消仍可能发生，不能拿该计数替代全局零梯度判定。现有 8 步配置是已存在的 spike 值，保留原值无需重批；改变 skip/熔断依据另谈。
2. **I17/I20 已批的纯观测不必再问一次。** 复用 detached log-ratio 与 support，以明确分母和有界分桶输出，验证 CP/DP 不重计即可。不给每个指标增加 actor forward、全 token CPU 导出或逐 token 同步。“必备”可作为诊断实施清单，不能偷偷新增缺指标就拒绝训练的机器闸门。
3. **I18 的 A 仍是待讨论建议。** 可以准备观测，但“接受重算路由进行首训”不能混在纯观测的 T1 中批准。先写清同一叶/动作如何对齐、B 路线 FORK 后哪些位置仍可比较、专家顺序还是集合一致、分母与未知量，以及现有 tape 能看到什么。已捕获的早/晚 tape 一致率不证明单次请求内 retract 的每个行为 forward 都已捕获；B 逐轮拼 tape 也不能先写成已证明正确的修法。保留独立深入讨论。
4. **route agreement 的低成本尚无证据。** 当前保存有 tape 不等于逐 token×layer×expert 比较免费；I18 route 位与 trainer DIS 位的关联也不是“多写六个标量”即可完成。先给复用/抽样/有界汇总路径与开销范围，再决定常开程度，不增加全量 tape 副本或新 forward。它可以成为诊断候选，不因为草案称“必备”就提前承诺接线和首训门槛。
5. **I19 区分收缩线索与实际拒绝。** 当前 session 级收缩仅审计、branch 级才可触发拒绝（`generate.py:3063–3110`）；两者不能混算丢组率。关闭 CC 自动压缩的可行性可以只读核查，但不能预先承诺“关闭后不再收缩”，更不能据此关闭现有 guard。保持现状与观测无需重新批准；新增压缩支持或改变真实 harness 行为按原组讨论。

## 6. 实施组织、验证与边界

- 不需要先排完整第三批到第七批。当前按 **N1 口径修正与汇总 → N2 期限/取消接线及窄重试 → N3 有证据的改判** 分别提交；不重叠的部分可并行。N3 不应拖住前两项。
- “N1/N2 不碰同一文件”需修正：N1 要动 `generate.py`，N2 又承诺写 rollout audit 的 grading 块；实际接线可能也经过该文件（`_grade` 与 `_record_grader_timing`）。若复用现有旁路无需改它，明确说明；否则共享文件串行集成，避免两个任务同时改。此项是协调事实，不是新 T0。
- 错误分类函数保留明确操作阶段与原始 CLI 返回；不要按一个 `EOF`/`timeout` 子串兜底。真实已核对形态可以小范围映射，但“从已知 stderr 形态映射”与“不解析 stderr”不能同时声称。没有可靠来源的项先不开放；确定配置/认证错误不被通用传输字样覆盖。无需建设分类平台。
- `regrade_events` 的新增列表要明确消费者及保留期限。优先复用现有 manager/audit/事件，避免一条重试事实永久保留三份且无清理。首版最终只交付一个评分，不要求为尚未执行测试的失败凭空造可信 0/1 报告。

**本轮独立验证：** 按高风险计划审查使用一对限定范围的 Production Tracer 与 Falsifier，主审回读源码并独立复跑关键探针。证据位于本目录 `production_probe.py`、`falsifier_probe.py` 及对应输出；前者包含真实 queue 的任务边界、真实 formal orchestrator 取消时必要记录的正反例；后者包含真实 queue→manager 的 timeout 对照，以及未登记临时容器的条件反例。另用真实 vendored `_SampleBuilder` 验证 104/4 token 口径。外部 Docker/评分环境由替身提供，没有运行真实 Docker、CC、模型 API、GPU，也没有重跑全量测试。

**A–N 适用性简扫：** A 核取消及错误传播；B 核重试范围、丢组与原样本选择不变；C 不新增指标闸门或临时挡板；D 核期限消费者与任务/容器 owner；E 核真实 queue/编排入口及正反例；F 对照已批决定；G 追踪正式评分与关闭接线；H 区分 buffer 终态、快照、capture 与重复行；I 限定本轮前置和旧 backlog；J 修正命名及失实注释；K 复用既有 queue/manager/补丁机制；L 核总期限、反压与指标开销；M 核根因、成本和未知量；N 核已知 CLI 错误形态、fork 补丁维护及旧事件兼容。未做算法推导或 GPU 数值验收。回退以独立切片为单位，不回退已批准并关闭的预算批次，也不通过删除失败测试“恢复绿灯”。

本轮只新增审查工件并登记共享账本，不改作者计划正文、生产源码、维护测试、训练配置或依赖，不提交/推送。owner 没有新增批准事项；I18 等原未定语义保持未定。**停止条件：Claude 将 R1/R2 的真实接线及验收写回 Brief，N1 采用准确口径，即可按切片实施；无须再等一轮纯文案确认。实施完成后只复核这些行为及直接接缝。**
