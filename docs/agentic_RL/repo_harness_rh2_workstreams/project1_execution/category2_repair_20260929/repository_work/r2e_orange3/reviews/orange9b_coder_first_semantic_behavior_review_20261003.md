# Orange9b Coder 首轮：独立语义与行为窄核

2026-10-03，题主安排的非作者 subagent。**作者新增分析受支持，无作者材料、题面、评分或共享 consumer 必修项。Coder 最终修法满足当前公开 L1 自动选 solver 需求，原 reward1、13/13 来源预期状态匹配成立。实际是 11 PASS/2 FAIL/1 SKIP，testRC1、安装 SKIPPED，不能改写成全部测试通过。** 当前只有一次 Coder 样本；Qwen 未齐，原 paired 请求仍 claimed，本报告不 ACK、清 active 或封两模型整体结论。

本轮只读权威 closed snapshot，独立核原 baseline、原 FP、完整 301 事件、必要实际评分链与七维行为，并核[新作者分析](../tasks/9b5494e2/probe_coder_first_analysis_20261003.md)。此前 R9 CPU 十方和公开 CC 按固定版本复用，不重新求解或运行 CPU/GPU/模型/候选/SSH/新增测试。四题 partial execution receipt 只是原执行范围的索引；不存在可冒称复用的“43 项单题完整 GPU 独立审查”。只新增本报告及[JSON](orange9b_coder_first_semantic_behavior_review_20261003.json)，旧报告、作者原件、题目、公共 consumer、原分、请求和总账未改。

## 最终修法与概率语义

原 baseline 的构造函数签名保持 `solver="lbfgs"`、`penalty="l2"`、`multi_class="auto"`。最终在 `self.params=vars()` 之前，仅对 `penalty=="l1" and solver=="lbfgs"` 改选 `liblinear`；实际仍使用 L1、调用原 sklearn fit，没有强改成 L2、吞掉调用者错误或伪造预测。默认 L2、none 和既有可用的显式 solver 分支不变，默认 repr 的签名与参数路径保留。唯一 Edit192→196 已形成正确最终源码，没有撤回或候选重试。原源码内容 SHA `789dc5576987c1c57ee3e86a9ef495a2ce2883166a22115c3e7838a37d474658`。

**默认概率关系是 L2/auto/lbfgs 对显式 multinomial，不是新 L1/liblinear 必须等于 multinomial。** 新 L1 默认由 liblinear 使用 OvR（分别拟合各类再组合），该选择被当前公开需求和固定控制允许。它没有把原已工作默认 L2 多分类模型改成 OvR，区别于已封 CPU 的 G1 负例。固定 `test_auto_solver` 实际 PASS，含 iris/heart 的真实 L1 fit、真实 penalty 与可用 solver、默认 L2/lbfgs、重复默认 repr、none fit，以及默认与显式 multinomial 概率 allclose。此项正式检查与源码机制相互支持；不只按 raw1 倒推，也不认证全部显式 solver/multi_class/dual 组合或整个 Orange。

原 FP 两项是源码 modify 与新增 `test_l1_fix.py`。helper 未清理，也进入原生评分投影；`git diff` 只展示 tracked 源码，不能说工作区只改了源码。原模型工具没有改既有测试、依赖、评分控制或读取隐藏/gold/未来答案/网络的证据。此判断只覆盖可观察通道，不排除先验记忆，也不将错误推理认定为恶意绕过。

## 必要实际链与两项预期 FAILED

权威目录为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-coder-a1`。[sync v3](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-coder-a1/sync_receipt_v3.json)核390个选中成员、73,151,319B，全 SHA 匹配；manifest/sync另两份元数据不计入390。全390运输检查按该已核收据和题主核对复用，本轮独立检查必要原件与其 SHA，不把目录数量或旧 remote 的 partial compatibility mirror 当另一份完整归档。

本轮独立确认：

- 原 host 本题行绑定020/092、13键 expected map `cd034086…`，其中两个来源 FAILED；prepared/host SHA `25b3007b…/4632b750…` 与实际 input/attempt 一致。
- 完整 recipe `050316e44910d53ea3ded25e5a510a01c43e1ed60e1034270385ff9dcbe7fff1`、base recipe `7e1710…` 关联 derived image `08470256e1bdb8e6952a77280695ca7bdb89800d3409eca7cc0a24aa5b96d4d2`。原 CPU 镜像归档读回、overlay、actor identity与grader diagnostics一致；本题 GPU 镜像确与当前 R9 CPU 相同，不能套用 Orange50 的不同镜像结论。
- 两个 FP entry 内容 SHA 通过；纯 JSON canonical digest 重算为 `8455731d9eb836380bcc69148c858c9ef727958f8c761cc83adcff79e329fffe`，projection 同 digest 且完整包含两项。FP 文件 SHA `eb9d63c1…` 是另一口径。
- baseline manifest canonical `df404e5c…` 与 FP/status 一致；1531个 baseline entries，actor census与grader重建 census逐字同 SHA `a0c62815…`。原 status 记录重建成功，diagnostics apply_ok，runner 未改变、candidate prerequisite=null、受保护测试完整。没有在本轮重新重建或应用候选。
- [正式 eval](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-coder-a1/queue_v25/results/gpu1003-orange9b-coder-a1/grading/eval_logs/evallog_gpu1003-orange9b-coder-a_94d0d142.eval.log)隐测 tree `8a2adb79…`、entry `5dee57d9…` 匹配 host；独立解析的13个键与来源 expected map逐状态精确相等，无缺键、unexpected或评分段外解析。安装 SKIPPED/RC=null，正文/footer完整，testRC1。
- actor清理无残留；manager close的open容器、supply、cleanup_failures为空，created/removed各1、无regrade。清理结论依据原终态记录，不新运行容器检查。

两项失败都使用默认 L2 learner，而新条件不进入该路径：

| 来源与实际均 FAILED | 原 traceback | 结论边界 |
| --- | --- | --- |
| test_learner_scorer | 70：major vessels colored ≠ chest pain | 默认特征排序首断言失败，后面71的shape未达到。 |
| test_learner_scorer_multiclass | 92：aquatic ≠ legs | 默认首类首断言失败，93–100未达到，不推其通过或失败。 |

它们与已封 R9 CPU noop 的两个既有 FAILED 键一致；原默认参数、score/Normalize/coefficients代码未改，当前无新增该类退化证据。来源 expected FAILED 不是认证这些排序行为正确，也不是抹去实际失败。模型未执行 baseline 全文，其249的“likely既有”只是推断；既有来源与当前代码/日志的独立核对补足本轮判断。

## 七维事实

以下编号是[原 trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-coder-a1/queue_v25/results/gpu1003-orange9b-coder-a1/attempt/harness/trajectory.jsonl)一基事件行；JSON逐项列出23工具 call/result与ID。

1. **方法。** 179→183读取本环境 `_check_solver`（`toolu_34d730cae20f642d`），188正确识别L1支持liblinear/saga，192→196唯一Edit（`toolu_cdcd767d3f7bedcd`）只修本例不支持组合。205→209（`toolu_8707db331d68618d`）真实L1/L2 fit成功，275→279（`toolu_671dd99b0276cd46`）未捕异常的精确原例成功；最终机制与正式目标支持当前需求。

2. **定位与纠错。** 23→27全源Read、36→40重复尾部、49→53公开测试Read，工具 `toolu_b60179250391e00d`、`toolu_d68b02c8c3070472`、`toolu_5fc845af9970d92f`。62→66（`toolu_1bedbdafe3333da6`）真实fit已复现明确ValueError。88→92、101→105、114→118、153→157却只构造，显示支持/OK；97/110错误理解构造成功，149/175版本或检查过严推断未由原件支持。127→131与166→170的真实fit仍失败，179→183源码才纠正。75→79只打印默认solver，不是available支持列表。题面已给类、报错、fit与版本，不能外推盲定位能力；补充错误栈有价值，不把重复调用全判无用。

3. **工具与结果使用。** 23工具为Bash18/Read3/Edit1/Write1，全部有实际结果。唯一 `is_error` 为240→244（`toolu_9869603caf24146d`）全文RC1；66/131/170是真实需求失败，只因捕异常后打印而工具RC0，不能按error计数遗漏。262→266（`toolu_d536c8d995fba831`）helper实际打印3/3，不能仅据RC0：失败分支无sys.exit。当前明确成功正文和279未捕异常fit是有效正向证据。没有成功构造就等于训练成功、写文件就等于测试成功的推断。

4. **并行。** 24generation为23单工具组及最终无工具组，最大batch1；实际gateway、adapter和message分组一致。无完整工具执行起止，只观察结果时间，不能证明实际重叠或任一模型缺并行能力。Qwen未齐，不做两臂比较。

5. **验证。** 218→222默认公开selector、227→231 L1概率selector均1PASS，工具 `toolu_24ee0aae4ede8905`、`toolu_e9fdf4ed84377d8b`。244公开全文为2FAIL/10PASS/1SKIP/RC1，尚无新增hidden的auto_solver。266是三个布尔/打印成功函数，验证L1/L2 fit及调用predict/probs、learner.params solver，非3个pytest断言，不检验数值概率等价或失败退出传播。模型未自验binary/none/repr/默认multinomial关系。正式多一项auto_solver所以11PASS；不能把正式检验回标为模型自测或将两种分母相加。

6. **效率。** 首次fit已明确报错后多次构造参数矩阵、版本推断和重复尾部Read增加工作，直到fit栈与源码才纠正。再次原例和残留helper也增加调用；无实测可节省秒数。完整公开文件提供真实回归反馈，不能因为两个预期FAIL判无用。累计209848/4589非context峰值，最高单次13609/682；API/gateway与generation到结果含服务与往返。环境、solve、评分和全job分列。

7. **结束与稳定性。** 301真实success/end_turn/completed、harness0；原完整冻结评分与清理成立，无观察到预算截断或infra失败。297只说两个相关selectorPASS，属实，不套用Orange50的“声称全文全过”；但省略244两FAIL，full backward compatibility超出模型自己的验证覆盖。源码与固定目标支持当前修复，非全参数空间认证。仅一次Coder完成1/1、来源匹配成功1/1、完整样本语义支持1/1，Qwen缺样本不计失败，不作稳定能力或训练结论。

## 独立核对的数字与交付

作者关键结论、指标与独立原件一致；31项顶层 evidence_refs 的SHA/size全匹配。

| 实际指标 | Coder |
| --- | ---: |
| 原reward / expected match / testRC | 1 / 13/13 / 1 |
| 累计输入 / 输出 | 209848 / 4589 |
| 单次最高输入 / 输出 | 13609 / 682 |
| CC turns / generation / 全HTTP | 24 / 24 / 24 |
| count_tokens HTTP | 0 |
| 工具 / 源码Edit | 23 / 1 |
| solve / CC总 / API秒 | 52.192 / 48.834 / 33.347 |
| gateway seconds_total求和 | 32.786 |
| trusted_init / actor总墙钟秒 | 114.785 / 201.451818 |
| grader总 / wrapper测试秒 | 124.793 / 3.482 |
| TEST marker区间秒 | 2.463198184967041 |
| 派发后整个job秒 | 327.728305 |

首源Read23→27从该generation请求到结果0.382090秒，从首generation到结果1.506521秒；192→196正确Edit分别3.283236/25.775521秒。都含生成/派发/工具/返回，非纯定位、工具或GPU时长。约5.5分钟全job不能说成5.5分钟解题；派发前候槽未知，graderqueue0仅管理器；CCcost为估算非账单。

首HTTP实际包含2430字符solver prompt全文，SHA `23b45f4dd7ca7ecb0ba967409612a767fcd4c6b298fee57d43346838f9f71963`；closed公开brief与题主文件逐字相同，入prompt只strip末端空白。24条实际generation均请求65536；宽松配置196608 context/240回合/10800 solve秒/1024请求，与实际单次约13.6K不同，未验证满负载。CC metadata32000与HTTP65536分别保留，不认32K截断。Python3.7.9有原runtime事实，sklearn0.22.2.post1在144实际输出；pip before/after相同，NumPy1.17.5与SciPy1.5.4 wheel绑定原同镜像环境，不是本轮新测环境。

## 观测边界与接收状态

本题entry为实际code8命令、entry SHA `bdf806bf…`、source manifest `09ddb8bf…` 的操作关联；原code_snapshot_id、grading_materials_identity/typedqualification等null仍保留。历史engine_launch文件记录03:48:27捕获，不改标为当前；closed另有09:30:46.488–.670的作业前live service capture receipt，关联同历史engine SHA/ID、只读mount与配置。两者均不是重复权重逐文件哈希或物理GPU逐POST attestation。input_check旧config_only/readback=false保持原件，当前HTTP事实另记。

24份有限cgroup telemetry中actor/relay各14次、grader8次，首末无容器；角色/时刻/ID已匹配，有actor CPU throttle。profile声明2CPU/4GiB/512/swap0，与这些telemetry分列；没有当前HostConfig或cpu.max/memory.max/PidsLimit直接快照，不能把旧CPU观测或同镜像当GPU全程限额实测。空容器不当内存0，采样无oom_kill非零不证明全程OOM0或完整峰值。原diagnostics.resource_facts=null。grader只直接观测Orange/__init__.py路径，无logistic模块加载字节SHA直接快照；原FP应用、同镜像fresh正式结果与源代码归因支持当前消费链，保留直接加载hash未实测的边界。原runtime_private_pathset_changed/excluded_pathset_changed未清空，按projectable及受保护控制完整判断，不虚称所有排除路径未变。

新单Coder独立审查完成，`necessary_fixes=[]`。题主可另写当前Coder局部接收，原请求继续claimed/active等待Qwen；本报告没有ACK/clear，没有为成功重跑或普通追加采样。作者原new_non_author_review_complete=false为生成时状态，不回写。当前CPU无需因本轮诊断新增步骤；本题两模型整体和全包GPU仍未完成，不授予训练/留出资格。

## 文件绑定

- 新作者MD SHA：`3655d5a280e987191194ce129c48b36029aefd5030ab7538331251063904a465`；JSON SHA：`901728cf958855fc5d77a9ed28fba68a1703f6555b8eb7ff624862c89422a85e`。
- 作者evidence索引 SHA：`7f137a9c848a57caf10a5ed4c832521cdcf225db9ed50029c9af09d8bdc54ff8`；binding索引 SHA：`c5b334d6ebb902fc0c5578bd8be87cb7cbca18d150a86561dfe4c57280cd09e0`，仅作索引，实际判断来自原件。
- closed manifest SHA：`52e653eb79d318a77204808f0e2cd0dcd47dae16823dd47189cea798c31dd3c4`；sync v3 SHA：`c10116d6c8c4255d30af82a840717c9307a17b7def1765b33336693dcecea5a5`。
- trajectory SHA：`856f090fa755941a06d9c51eca9f5b3dbc3f2f4c92ef2eb5484b57c2b901d0af`；FP文件SHA：`eb9d63c1a20ffd30012f98aac9a3c65f9d2ad2c043128e3e699a35caa434f0b9`；formal eval SHA：`768e9f3c7aa78d2fe5fe8af2597195acca61cb69168242f5fe95ade1aeb3d9ef`。
- 复用已封CPU终审JSON SHA：`9f43232b76507f893c986e510739cc0183b57c9e3a2ce04d6bd7f123896e7466`；旧概率复用窄核JSON SHA：`4d15ebf872c726d3a3e9a21d343985ef0b8a643d43a72403da63164352ff06ba`。没有重做旧校准或把其旧env_v2当新R9。

其余材料、SHA/size、13键逐状态、23工具索引、时间与限制见本报告JSON。

