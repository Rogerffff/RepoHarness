# I21 实施聚焦复核（2026-09-20，Codex A 分叉）

**结论：方向和上一轮 R1–R5 的处置基本成立，本轮实现还需两项 P1 修复；另有一项 P2 统计遗漏。无需重新决定 A/B 方案，也不需要新增用户授权。** 本报告使用 IR1–IR3 编号，避免与前轮设计审查 R1–R5 混淆。

对象是主仓库 `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 上的 I21 未提交改动，加 miles fork `e13f00086`。共享工作树另有 B 线评分修复，本轮没有重审其评分语义。未修改生产代码、维护测试、配置或 fork，未提交、push、运行 Docker/GPU/远端作业。新增审查工件、Brief 导航与 infra 留言不等于已向其它任务发送消息。

## 1. 已接受的修复及范围

| 上轮问题 | 本轮判断 |
| --- | --- |
| R1：默认日志对 `None` 求和 | 非空、正常 RH2 交付路径已修：钩子返回 True 接管日志，graded 与 planned 分母、未评分原因分开。空结果仍有遗漏，见 IR2。 |
| R2：rollout 0 重用、模型绑定不足 | 宿主每次调用生成 `eval_point_id`，覆盖数据集自报事实；目标版本来自 RolloutManager，观察版本来自执行事实，聚合区分 verified/mismatch/unverified。该修法接受。仍需真实引擎证据，不能把 CPU 替身当作加载验证。 |
| R3：全局题目互斥越界 | 已删除；两个 prepared face 按派发平面解析，同题允许重合，交集只记录。接受。 |
| R4：A 不是仅加 debug 标志就完成 | 已如实缩窄为 RH2 侧 eval-only 可启动、训练派发拒绝。驱动只评测及固定 HF 导出实际进入引擎仍未完成；不把 A 整体记为已交付，也不以此阻塞 B。 |
| R5：恢复编号零值不能代表新实验 | I22 整项暂缓符合已有决定。保持明确 checkpoint、不手填 `start_rollout_id` 的操作约束，实际恢复入口另行收口。 |

63 个新增测试独立通过；完整双 lane 通过。正常 graded、基础设施缺失、评測身份、相同题包、两平面绑定、audit 结果块、成本分流等已有用例的关键断言成立。以下问题来自补充交叉场景，而不是否定这些通过项。

## 2. IR1 / P1：评测的不可评分结果仍可能撞上训练用 sampling-mask 检查

**现在发生什么。** `apply_eval_result` 取交付列表第一条作为载体。正常评测完成时它是输入的 miles Sample；unsafe artifact 分支却是 vendor slime 叶。虽然后者已被标成 `None + ABORTED`、且不会训练，`Rh2MilesGenerateFn` 仍以 **训练配置** `args.rollout_top_p` 调 `canonicalize_group`。vendor 转换分支无条件要求训练 mask，没有区分评测面。

**可达反例：** 训练 `top_p=0.95`，评测独立配置 `top_p=1.0`；评测模型产出不支持的 FIFO 文件。这一 artifact 已按既有规则归为 unsafe、无需评分，应交付 `reward_unavailable`。但评测本来不采集 top-p 支持集，交付转换遂抛 `CanonicalizationError(sampling_mask_required)`。共享引擎 eval 异常会上抛训练驱动，原本一个可记录的未评分结果变成停训。

证据见 `results.json`：

| 场景 | 观察结果 |
| --- | --- |
| train/eval top-p 都为 1，同一 unsafe 产物 | `aborted / reward=None / reward_unavailable` |
| train top-p=.95、eval top-p=1，同一 unsafe 产物 | `sampling_mask_required`；评分调用 0 次，绑定已释放 |
| train top-p=.95、eval top-p=1，正常产物 | `completed / reward=1` |

源码锚点：`rh2/src/repoharness2/adapters/slime/eval_result.py:150–160`，`adapters/miles/generate_fn.py:242–248`，`adapters/miles/canonicalize.py:376–382`。探针运行真实 `Rh2MilesGenerateFn → RolloutOrchestrator → apply_eval_result → canonicalize`；Docker/harness/capture 为作者既有替身，exporter 在操作边界注入已有 typed unsafe 错误。为避免作者夹具固定 group_index=0 造成伪阳性，叶的 index/group_index 按真实 vendor 接口从输入复制。

**建议修法：** 评测统一使用不进训练的结果载体，或在明确的评测边界解除仅服务训练的 mask 要求；保留身份、终止事实和评测结果绑定。不要给评测补伪造 mask，不要强制 eval top-p 跟训练相同，也不要通过吞掉所有 canonicalization 异常解决。

**本轮验收条件：** 上表三案均有明确结果，unsafe 一条结果、无 RM 调用、无训练 admission 载荷；另外验证训练 top-p<1 的真实缺 mask 仍拒绝。此项可完全在 CPU 收口，不需新增 T0。

## 3. IR2 / P1：计划集合从过滤后的结果反推，既能误报完整，也有空结果崩溃

这是同一个边界的两种表现：**一次评测调用的计划与身份只附着在存活样本上，汇总没有独立的调用级事实。**

### 3.1 少测题仍报 complete=True

miles `Dataset` 在加载时按 `eval_max_prompt_len` 过滤长输入。patch 0018 后续写的 `num_prompts=len(dataset.samples)` 已经是过滤后的数目，`prompt_index` 也从零重新编号。RH2 的题包 digest 检查只确认输入文件一致，不会察觉这一步改了实际评测题目集合。

探针先加载真实的两题 prepared 产物，再把同一个 prompts.jsonl 交给真实 Dataset。假 tokenizer 仅控制长度，派发与过滤函数保持原样：

| 输入与运行 | planned / received | complete / binding | resolved_rate_planned |
| --- | --- | --- | --- |
| 两题，不过滤 | 2 / 2 | true / verified | 1.0 |
| 两题长度为 1、100，max_prompt_len=10 | **1 / 1** | **true / verified** | **1.0** |

第二行没有任何缺失成员或过滤计数；长题从分母消失。对 coding 评测这会系统性改变长题覆盖，不能把它描述成“完成既定两题题单”。如果 B 线明确选择某个子集，应在选择题单时留下依据，不能靠加载器静默缩小分母。

锚点：fork `miles/rollout/inference_rollout/inference_rollout_eval.py:80–93,106–123`；`miles/utils/data.py:251–258`；RH2 `adapters/miles/eval_report.py:84–97,139–151`。

### 3.2 全部过滤时重新落回默认日志

同一两题包，长度为 20、100，`max_prompt_len=10`，预检照常通过、结果样本为零。`eval_report.log_eval_rollout_data:234–236` 把“没有任何 RH2 样本载荷”当成“非 RH2 路径”，返回 False。miles 继续默认日志，对空列表计算比例抛 `ZeroDivisionError`，没有 `eval_point` 事件；共享引擎形态下异常传回训练驱动。

探针执行了真实 RH2 钩子与 miles 默认日志原函数体。默认样本的附加设备统计用空字典替身，仍在真实默认日志的 `truncated` 空分母处复现除零；真实前缀缓存统计也有空分母，替身没有制造这个失败条件。

**建议修法：** 在调用/数据集层保留宿主评测点与既定题目集合，结果汇总可以在没有存活样本时照常记录；过滤/未执行原因单列，不能回退成 s1_compat 或模型 0 分。首版若不需要通用输入长度过滤，也可在 RH2 的评测路径不应用这一步，由已选择的题包决定范围；仍须处理空结果。无需建设新的评测平台或增加整套题包 hash 守卫。

**本轮验收条件：** 不过滤、部分过滤、全部过滤三案；部分过滤不能声称既定题单已完整完成，全部过滤仍有唯一评测点、明确未完成及未知绑定，不崩溃、不产模型零分。保留非空混合 `[1,None]` 和合法 s1_compat 正控。处理方式不应悄悄改变 B 线的题目划分决定。

## 4. IR3 / P2：评测重评分仍计进训练统计

`_single_run_report` 分开了 audit，`summarize_attempt_costs` 分开了成本，然而传给训练 facet 的 `events_by_kind` 仍含所有事件。`_facet_execution` 直接汇总全体 `grading_regrade`，没有按平面分流。

`results.json → eval_regrade_report`：只有一条评测 audit 和一条对应的 `grading_regrade`，训练 audit 数为 0，但训练侧 `grading_regrades.events=1`。这会让训练重试发生率与成本解释受到评测频率影响，与“各训练 facet 只看训练 attempt”的新说明不一致。

锚点：`adapters/miles/run_report.py:832–846,285–288`。真实 producer 在 `grading/manager.py:2089–2097` 已带 `trajectory_id`。

**建议与验收：** 利用 run 身份 + trajectory_id 与现有 audit 的 evaluation 块连接，将重评分事件分为训练、评测、归属未知；不必为此修改 grading 公共契约或另造 producer。加一组训练与评测各一次重评分的报告对照，以及 audit 缺席的未知项。此项为观测修正，不改变评分或训练处置，建议本轮顺手收口。

## 5. 六个 CPU 失败的独立核实

不能仅凭“单文件能过”推断非回归，本次额外做了对照：

1. 当前树，仅运行该文件：**6 passed**。
2. 当前树，收集全部 CPU 测试但仅运行 `dp_schedule_differential`：**6 failed / 2469 deselected**，错误为 vendor slime 缺少 `utils.dp_schedule` 与 `rollout`。
3. 当前树，排除 I21 的八个新增测试文件后仍做上述收集：**6 failed / 2406 deselected**。
4. `git archive HEAD rh2/` 的独立临时副本，完整非 Docker 测试：**1906 passed / 320 skipped / 40 deselected**，无失败。该对照缺少其它先前未提交工作，不能单独证明 I21 导致回归。
5. 另建临时副本，保留此前工作区的源文件、测试、脚本；只恢复 I21 自有文件、删除 I21 新文件，并从 generate/bringup 反向应用已核实的 I21 hunks。相同全收集窄运行：**仍是原六项失败 / 2406 deselected**。

因此，Claude 对**这六项不属于本轮 I21 回归**的判断有了独立证据；它们仍是现有测试环境的问题，不可写成“全套测试通过”，也不是干净 HEAD 原有失败。维持维护清单后置，本轮不扩查哪个先前测试最先污染导入。

重建方式、保留文件与反向 hunks 在 `pre_i21_dp_probe.py` / `pre_i21_dp.json`；失败全文在 `pre_i21_dp.log`，干净 HEAD 完整测试结果在 `baseline_cpu.json` / `baseline_cpu.log`。所有重建均在临时目录，没有 checkout、stash 或覆盖共享文件。第一次重建漏带一个先前新增的 screening 脚本，补齐后得到上述第 5 项；这不是被审代码的失败。

## 6. 验证范围与下一步

| 检查 | 独立结果 |
| --- | --- |
| 新增 I21 八文件测试，integration miles | 63 passed，12.53 s |
| `bash rh2/scripts/miles_integration_lanes.sh` | A：454 passed / 326 skipped；B：780 passed / 0 skipped；A 非 integration 子集与 fork/pin/patch 前置也通过 |
| IR1–IR3 补充探针 | 7 个确定性场景，结果在 `results.json`，含所读生产文件 SHA256 |
| ruff（I21 源码、测试、审查探针） | 通过 |
| 被审已有 diff 的空白检查 | 通过；fork 工作树仍干净 |
| 六项失败的基线检查 | 如 §5；不以全套绿色代替边界正确性 |
| 未做 | Docker、真实 CLI/Ray/模型加载、GPU、远端作业；未重新跑当前树全部 CPU 测试，作者的 2093/6 快照保持作者证据身份 |

重跑补充探针（从 rh2 目录）：

```sh
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch5_launch_eval_20260919/i21_implementation_review_20260920/probe.py
```

**停止条件：** Claude 修 IR1、IR2，补齐 IR3 的分流；下一轮只复核三个反例和上述正控，加受影响的 lane。A 的只评测驱动/固定模型加载、I22、共享引擎实际竞争成本仍按 Brief §11.5 后置。I18 路由重放未决，不因本次评测接线通过而获得正式首训授权。

## 7. 审查维度覆盖与简化意见

| 维度 | 本轮对应内容 |
| --- | --- |
| A / E / G | 真实入口交付、canonicalize、日志失败传播与反例；定位 IR1/IR2。设备依赖用替身，未冒充端到端复现。 |
| B / F | 缺失不落零分、题目交集不强制拒绝、长题不得无痕退出分母；未改既定训练语义。 |
| C / D | 预检多数对应明确接口不兼容或首版后置路径，不要求任意删掉；两个 prepared face 与宿主身份 owner 明确。 |
| H / M | audit 与交付块同纯函数、模型目标与观察值分开；调用级计划事实缺口及重评分事件漏分流见 IR2/IR3。 |
| I / L | 暂停新组、不排空在飞组的既定策略保留；真实资源竞争和吞吐需 GPU 观测。本轮不新增排空屏障。 |
| J / K | 结果三态集中派生合理。`_eval_host_stamp_supported` 为 CPU 测试新增的源码正则读取分支可以移回测试适配：生产标准入口的宿主模块已加载。属于非阻塞简化建议，不要求先做重构。 |
| N | fork pin/patch/两 lane 已核；日志消费者的 None/空列表兼容性见 IR2。未升级依赖。 |

无新增 T0、无新增临时挡板、无要求用户重复批准的事项。修复应落在现有 I21 边界；不建议把这轮再扩成评分、恢复或数据筛查总审计。
