# I21 / I22 实施 Brief 聚焦审查

2026-09-19 / Codex，分叉 A 线。对象：[Claude Brief](../i21_eval_brief_20260919.md)，主树 HEAD `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 加现有 B 未提交代码；miles fork `4c04f997b60fd08c36941d8715db06bfc0ed0543`，本轮读取时 fork 工作树干净。

**结论：复用方向合理，Brief 需修订后实施；不建议将 §7 四点打包交用户重新批准。** 共用评测入口、独立评测/共享引擎复用、双任务 face、缺失评分的显式表达均可继续。R1–R3 应先改计划；R4 在承诺 A 可用前闭合本地入口，不卡 B 的独立实现；R5 若实施 patch 0019 应修正语义与测试，也可按用户既有授权整项暂缓。

本轮执行当前源码的窄函数体探针，未改生产代码、维护测试、fork 或配置。没有 Ray 集群、CLI 全量参数解析、模型加载、Docker、GPU 或远端作业。不是实施验收或全仓审查。

## 1. 必须修正的计划内容

### R1 / P1：None 占位后仍执行默认日志，会在统计中抛 TypeError

- **位置**：Brief §2.3（81 行）与 §8“miles 默认日志对 None 的兼容”；`miles/ray/rollout/metrics.py:21–40,95–101,142–164`。
- **拟议行为**：不可评分返回 `reward=None, status=ABORTED`；自定义日志钩子返回 False，继续默认日志。
- **证据 / 复现**：运行本目录 `probe.py`。`metrics_none_with_samples` 以当前真实 `log_eval_rollout_data`、`_compute_metrics_from_samples`、`_compute_training_sample_metrics` 函数体处理 `[1.0, None]`，得到 `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'`。`metrics_numeric_control` 的 `[1.0,0.0]` 正常返回 0.5。真实 `inference_rollout_eval.py` 输出包含 `samples`，因此这不是一个无消费者的 helper 反例。
- **根因**：顶层只把局部 `rewards` 列表中的 None 替换成 0；随后通用指标重新从原始 Sample 取 reward，进入 `sum([None])`。ABORTED 只避免再次调用 RM，不会避开该指标路径。
- **影响 / 不变量**：按原设计，已归因的单题评分失败会在日志阶段变成异常，并经共享引擎 dispatch 停掉训练驱动。即使去掉 samples 暂时不崩，默认 `eval/<dataset>` 仍把缺失计为 0，不能宣称主要评分曲线已完成缺失分离。
- **修正**：由自定义聚合接管相关日志，或窄改默认聚合使其完整支持缺失；两者选一即可。不要修改 None 样本为伪造 0 来满足统计。若使用返回 True 的钩子，要核对 `log_eval_rollout_data` 会返回 None 的下游契约（metric checker、事件等），不能只停掉第一处崩溃。
- **验收 / 分期**：本批实现前改计划。真实 eval dataset 输出 → 实际聚合函数至少覆盖全数值、混合缺失、全缺失，检查落盘指标和错误传播。保留 graded 分母、计划分母和缺失计数，不能仅删除 None 后报告看似改善的准确率。`resolved/planned` 可作为明确命名的整体完成比例或下界，但不能把原始缺失事实改成模型答错。

### R2 / P1：rollout_id 不是唯一评测调用标识，也不能代替模型身份

- **位置**：Brief §2.1（41–47 行）、§2.3（81 行）与 patch 0018；`train_async.py:94–95,123,198–199`、`miles/utils/misc.py:130`。
- **拟议行为**：以 dataset + eval_rollout_id + prompt_index + sample_slot 生成 execution/group 身份，汇总时按 eval 点统计；只记录观察到的版本集合与是否单一。
- **证据 / 复现**：本目录 `driver_before_after_zero` 执行实际 `train`、`EvalDispatcher` 与周期判定函数体，替换 Ray/模型依赖。一轮更新得到两次 `eval(0)`：一次 bootstrap 后、一次第 0 步更新后；替身发布版本分别为 1、2。版本数字由替身模拟，但两个 rollout_id 均为 0 是真实驱动控制流。Brief 公式会在同一 run 为这两个不同模型点生成相同 `eval-swe_dev-r0-p3_m1`。在同一 checkpoint 主动重测也有相同问题。
- **影响 / 不变量**：两个 eval 调用无法通过该评测点键区分，可能在报告中混并成重复/多版本点；physical_attempt_id 的随机后缀只能区分单次尝试，不能给整批 before/after 提供各自的共同标识。全体请求恰好使用同一个错误版本也会满足 single_version，仍未证明测的是目标模型。
- **修正**：增加由宿主产生的轻量 `eval_point_id`（run 内计数器或 UUID 均可），一次调用下所有样本共享，不能由数据集提供。rollout_id 保留为训练进度标签。另记录目标模型/已发布版本来源，与观察到的 token 版本事实区分；独立作业记录实际引擎加载的固定模型来源。复用已有模型身份，不增加逐请求模型哈希。
- **验收 / 分期**：本批实现前改计划。训练前 r0 与更新后 r0、同 checkpoint 重测、缺失版本事实不得混并；planned/received 用该次调用的唯一成员集合核对，不能仅靠总数相等掩盖重复/遗漏。全部单一但与目标不符时，报告不得宣称绑定正确。
- **沿用既有要求**：科学报告是否呈现部分结果、使用哪个分母由 B 决定；但声称 W8 必需 before/after 闭环已通过，仍要求两个点真正完成且模型绑定正确，不能把这项既有要求整体转交给 B 重新选择。这里不新增“一次不完整评测就必须停训”的策略。

### R3 / P1（范围）：身份分离不推出所有 train/eval 题目必须互斥

- **位置**：Brief §1.2、§2.2（54 行）、§7 第三项、§8 平面分离测试。
- **拟议行为**：启动时只要训练与评测 task_id 有交集就拒绝整次作业。
- **证据 / 反例**：用户已经决定在环境流水线中用基座结果指导题目/环境处理；通用 eval 还应能在训练题子集上检查“模型更新后能否解决这些题”。这类开发诊断可以合法包含训练任务，同时不能冒充最终独立测试集。第五组 §6 的“eval 身份/任务绑定分离”要求的是分派用途和数据运输清楚，没有批准所有模式统一施加任务集合互斥。
- **影响 / 不变量**：新增硬拒绝把具体实验划分政策写成通用运行规则，阻止诊断用途，也与用户要求控制不必要闸门的方向不符。
- **修正**：保留两个逻辑任务 face 和按 evaluation 选择绑定。第二组 prepared 配置可以复用现有产物格式，是否另外生成目录由任务集合决定；两种用途使用同一份题包并不需要重写 manifest。交集可以报告，最终 held-out 划分由 B 的协议检查，不在本批默认禁止。正式独立评测确实必须避免泄漏，但这与通用 runtime 是否允许训练集诊断是不同范围。
- **验收 / 分期**：先删这项通用硬拒绝及对应“交集必失败”oracle；加同题不同用途的绑定/统计分离正例，并保留绑定到错误 face 的反例。若仍要全局禁止交集，那才是需要用户新定的 T0，而非已批决定的落实。

## 2. 需补齐或收窄的两处边界

### R4 / P2：A 的“只评测指定 checkpoint”需要本地入口证据，不能全部留给 GPU 命令

- **位置**：Brief §0、§2.2 `RH2_EVAL_ONLY` 与 §8 最后一段；`train_async.py:94–123`、`actor.py:178,882`、`sglang_engine.py:794`。
- **拟议行为**：用 `--debug-rollout-only` 作为不训练的独立作业，同一条 eval 路径；是否只跑一次 eval 留到 GPU。
- **证据 / 复现**：`debug_rollout_only_one_iteration` 的真实驱动函数体仍在 initial eval 后调用 `generate(0)`；debug 标志不让训练驱动跳过 rollout 循环。若此时设置 `RH2_EVAL_ONLY`，会撞拟新增的训练派发拒绝。`zero_iteration_candidate` 表明显式零轮、fully_async 下驱动层可只调用一次 initial eval，是可进一步验证的低成本候选，并非要求另造 runner。
- **模型来源**：debug actor 在加载模型/optimizer 前返回，`update_weights` 也直接返回；引擎默认 `model_path=args.hf_checkpoint`。因此只给 `--load` 一个训练 checkpoint，不会自动保证独立 eval 测到它。共享分支传入的 hf_dir 也不会自动加载到当前引擎。
- **修正 / 验收**：实施 A 时先用 CPU 替身验证参数解析后只发生 eval、无训练派发，明确固定 HF 导出或其它已有加载路径怎样真正进入引擎、怎样提供版本/模型绑定。完整机器命令和真实加载仍可留 GPU 验证。训练产物可缺省也要覆盖当前 `select_task_face_mode` / source 构造路径。
- **分期**：不阻塞 B 的独立实现；若暂不能闭合，就把 A 的这一小段明确留作待接线，不能写成仅剩真机命令。这不是要求现在设计完整 launcher。

### R5 / P2：显式 start=0 不是“只加载旧权重开始新实验”的充分条件

- **位置**：Brief §5（113 行），`rh2_recovery.py:220–246`、`arguments.py:3085–3109`、`actor.py:205–220`、`model.py:1394`。
- **拟议行为**：patch 0019 只检查 explicit>0，0 一律放行并解释为新实验；测试固定“0 放行”。
- **证据 / 复现**：探针 `recovery_explicit_zero_loaded_ten=-1`。若实际正常加载 checkpoint 10 的模型、optimizer、scheduler，而仅手填 start=0，恢复 helper 会跳过版本状态。start 编号本身没有清空 optimizer/RNG；当前加载代码另有 finetune/no_load_optim/no_load_rng 等实际控制。
- **影响 / 不变量**：按数字 0 推断 weights-only 新实验，会给真实续训错配留一个豁免，并把这种混合状态写成正确 oracle。
- **修正 / 验收**：区分真实冷恢复与明确的新实验加载方式。若本次继续做窄修，至少不要把 `loaded=10 + explicit=0 + 正常恢复训练状态` 当作已证明合法的新实验；新实验的测试应体现实际加载语义。若处理这些边界超出窄修，用户已允许整个 I22 暂缓，继续文档规定不手填编号即可，不必扩大恢复系统。
- **分期**：做 patch 0019 前修订；不影响 I21 独立推进。既有 B-3 编号、buffer 丢弃与重新发布语义不重开。

## 3. 实施时直接覆盖的接缝（不另开决策）

1. `generate_fn.py:208` 的 `_verify_admission_binding` 也在身份已铸造时执行。eval 不产训练 admission 载荷，必须一起区分；只跳过入口 `_assert_group_admission_filter_wired` 不够。
2. `_generate_attempt` 的 finally 在 `generate.py:4488` 调 audit sink，发生在外层 `generate()` 返回并盖最终 eval 载荷之前。eval 派发身份应在入口即进入 audit；需要落盘的结果事实须在 sink 前可派生，或使用已有追加事实机制。不能先落盘空块再在内存补齐后称审计完整；也不需要制造一套平行 outcome 数据库。
3. `run_report` 区分用途时同时核对已有 cost/event 消费路径，避免只过滤 audit 行但在训练成本/分母里仍混入 eval；共享资源总成本可以合计，需明确口径。
4. 预检使用一个共同 helper 尽量在资源启动前运行，独立 eval、启用 periodic eval 的训练都能到达。`BringupService` 当前由首次 generate 惰性启动；把检查写在构造中不一定等于整个作业在资源分配前检查。
5. 单 eval 数据集是允许采用的首版支持边界，不是评测数学要求；明确写出即可，不为本批强求多数据集。数据集名限制若只是为了拼字符串身份，可用独立 point id 消除不必要的名称限制。

## 4. Claude 提出的四个确认点如何处理

| 项 | 审查判断 | 当前处置 |
| --- | --- | --- |
| 不可评分/执行缺失不伪装成 0 | **false-positive T0**：前文已明确批准事实分开；None+aborted 是具体运输选择 | 不重复问原则；按 R1 修完整消费路径。最终主指标/部分结果协议归 B 后续，不暗改 |
| fork patch 0018 | **T1**：在现有 miles fork 内为已批 eval 接线补宿主调用事实，没有新引入 fork/服务 | 按 R2 补真正的调用身份和模型来源，走既有 patch 存档/回归；不能只因“要改 fork”要求新许可 |
| 第二个 prepared 目录 + 全局题目互斥 | 前者 **T1**；后者是额外数据用途政策，若坚持才为 **confirmed T0** | 推荐保留第二组配置、删除通用互斥门；不把两者捆绑成一个问题 |
| 与 B 的共享文件顺序 | 工程协调，已有用户分工可落实 | 按文件/函数约定一个写者。可先做独立部分；不要只因 B 正在改无关 manager 逻辑就停止整批，也不覆盖其未提交改动 |

共享引擎首版沿用“不排空在飞组”的现成行为，可作为本次适配范围，用 eval_window 和既有墙钟/成本记录观察；这没有修改已批 hard wall 处置。真实资源竞争程度是 **experiment-required**，留八卡诊断，不在本轮宣称没有代价。I18、GPU 配置、独立测试集协议为 **deferred**，不阻塞这些窄实现。没有要求用户新批准一套调度/恢复平台。

## 5. 证据、验收与停止条件

运行：

```sh
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch5_launch_eval_20260919/i21_eval_review_20260919/probe.py
```

结果：[results.json](results.json)，探针：[probe.py](probe.py)。8 个观测场景：缺失评分带 samples 报错、全数值正控、无 samples 的 None 默认计零、钩子截断默认日志、before/after 两次 r0、debug-only 仍派发训练、零轮驱动候选、显式 0 恢复 helper。源码摘要仅用于记录本轮取证版本，不是新增运行时门槛。

AST 只提取未修改的函数/类节点以避开 GPU 导入依赖；外部 Ray/模型/日志等使用替身。指标异常和驱动调用顺序已复现，权重更新本身、完整 CLI 校验、真实模型加载、并发资源影响没有验证。未复跑全套 pytest，不将窄探针数量当作实现测试数量。

本次按计划审查适用的 A/B/D/F/G/H/M/N 检查身份、错误传播、授权范围与现有上游接口；C/K/L 检查新增拒绝和生命周期扩张，E 检查所列用例能否到达真正消费者，J 只检查重复事实来源与接口清晰度。没有源码实现可供整批质量验收，不作“各维度全部通过”的声明。

**停止条件**：Claude 修订 R1–R3、明确 R4/R5 的分期和本地证据后，可按窄切片实施；不要再等四点打包批准。后续审查限于上述反例、计划列出的真实入口和必要回归，GPU 只承担真设备相关验证，不重复全仓审计。
