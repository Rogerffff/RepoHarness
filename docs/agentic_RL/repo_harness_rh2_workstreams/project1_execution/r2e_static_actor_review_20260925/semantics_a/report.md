# R2E 首批独立语义复核 A：四题（2026-09-25）

本报告只审 pandas 32dd55cb、coveragepy 5dbbe143、orange3 9b5494e2 与 22e98f8f。**原审查的四个主要问题均成立；发现一项需要在诊断统计前修正的判读规则（F1）。** 没有发现负责范围内的评分数字、候选身份或日志摘要算错。

本次只读公开题面与 base、当前隐藏测试与 expected、gold、候选补丁、既有评分和开发命令证据；在本目录执行了标准库探针。没有启动 Docker、访问远端或网络，没有改实现、题目材料、维护测试或历史证据。Orange 探针使用记录参数的替身底座，**没有重跑真实 sklearn 拟合**。本上下文已见答案，不能再作为这些题的公开 solver。

配套产物：[audit.py](audit.py)、[audit_results.json](audit_results.json)。脚本可从仓库根执行：

    python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/semantics_a/audit.py

## 1. 引用、范围与当前快照

下文路径均相对仓库根，简称如下：

| 简称 | 完整前缀 |
| --- | --- |
| S/ | docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/ |
| P/ | runs/r2e_static_prep_20260924/v2/public/ |
| H/ | runs/r2e_static_prep_20260924/v2/private/ |
| G/ | runs/r2e_actor_20260925/grader/ |
| C/ | runs/r2e_actor_20260925/grader_cands/ |
| D/ | runs/r2e_actor_20260925/devcheck/ |

题目录使用完整 instance_id：

- pandas：pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0。
- coveragepy：coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9。
- orange9：orange3__9b5494e26f407b75e79699c9d40be6df1d80a040。
- orange22：orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237。

读取了 AGENTS.md、review-standards.md、协作协议及本批入口。A/E/F/G/H/M 为主要维度：需求与测试对应、实际运行身份、原始证据是否支持结论；B/I 涉及误拒分类对能力统计的影响与修复分期；N 核对当前补丁、日志和镜像版本。没有修改 owner、配置、守卫或运行入口，因此 C/D/K 不做实施验收；L 不新增性能实验；J 只看会改变结论的表述。不是训练准入总审计。

审查期间 S/grader_candidates.md:85 与 S/README.md:72 已被其它工作更新为“7 个、V1/V3 原例实测、V4/V5 原例静态推断、V7 不计入”。本报告按更新后文本评估，不把已更正的旧表述重复列为 finding。

## 2. 14 条评分记录独立复算

本范围占本批 26 条中的 14 条：pandas 1、coveragepy 4（含 gold）、orange9 9；orange22 没有本批候选评分行。逐条核对候选 SHA256、grader/cands 与 grader_cands 副本、日志 SHA256、expected 与日志解析出的全部键、reward、投影路径、镜像覆盖 ID、测试材料改动标记和清理记录。均匹配；具体哈希、路径与状态计数保存于 audit_results.json。

| 候选 | reward | 期望键匹配 | 不匹配键 |
| --- | ---: | ---: | --- |
| pandas C1 | 0 | 91/92 | Period 均值错误文字 T2 |
| coverage gold | 1 | 75/75 | 无 |
| coverage CE1 | 0 | 74/75 | ApiTest.test_warn_once |
| coverage CE3 | 1 | 75/75 | 无 |
| coverage CE4 | 1 | 75/75 | 无 |
| orange P1 | 1 | 13/13 | 无 |
| orange P2 | 1 | 13/13 | 无 |
| orange V1 / OR1 | 0 | 12/13 | test_auto_solver |
| orange V3 / OR2 | 0 | 12/13 | test_auto_solver |
| orange V4 | 0 | 12/13 | test_auto_solver |
| orange V5 | 0 | 12/13 | test_auto_solver |
| orange V7 | 0 | 10/13 | test_auto_solver、两个 scorer 键 |
| orange W1 | 0 | 12/13 | test_auto_solver |
| orange G1 | 1 | 13/13 | 无 |

这里的 13/13 是**状态与期望一致**，不是 13 个测试 PASSED：orange P1/P2/G1 是 11 PASSED、2 FAILED；V1/V3/V4/V5/W1 是 10 PASSED、3 FAILED；V7 是 12 PASSED、1 FAILED。两个 scorer 的 FAILED 是当前 expected 的要求。

## 3. F1 · P2：失败键只能定位待复核样本，不能直接免除能力失败

**当前行为。** S/results/<orange9>/review.md:210 建议：题面原例能跑通、公开 test_probability 通过、且评分仅错 test_auto_solver，就记为“接口不符”，而不是“未修复”；其 :239 又把这条规则作为原样诊断方案的条件。S/results/<pandas>/card.md:60 类似地规定“T1 通过、只有 T2 失败”的解不计为能力失败。

**违反的不变量。** 能力标签必须由公开需求与候选实际语义决定。失败键描述测试观察到什么，不能证明其它未测需求已满足；“不再报例子中的异常”不等于“按指定参数完成了修复”。

**证据。** orange W1 已在本批实跑为 12/13，仅 test_auto_solver 与期望不同：G/ledger_or_W1.jsonl:1；G/eval_logs/evallog_replay-83df4cb76f94-oran_cffd201e.eval.log:90 显示 test_probability PASSED，:94–96 的另外两条 FAILED 与 expected 一致。公开与隐藏的 test_probability AST 相同；该测试只检查概率和，未检查模型仍使用 L1。可是 C/orange3_9b54_W1_gold_silently_drop_l1.patch:20–21 明确把 penalty='l1' 改为 'l2'。本次执行原方法的参数探针得到 {solver: 'lbfgs', penalty: 'l2'}，直接违反题面要求支持指定的 L1 penalty。

W1 的完整 iris 原例**没有既有独立 MCVE 运行记录，本次也未运行数值拟合**。它会用正常 l2/lbfgs 路径跑通这个仅打印模型的例子，是静态推断；不能把这一步写成已实测。已实测的 12/13 与参数路由反例足以说明，当前分类条件漏掉了决定性的“仍然是 L1”。

pandas 的同类反例是把 C1 的分派条件再加 and name == 'mean'：数值 Int64 mean 保持 C1 行为，Period T2 保持 base 行为，但数值 Int64 sum 继续走 base 报错路径。当前隐藏文件只在 H/<pandas>/hidden_tests/test_1.py:902–908 新增 Int64 mean 例子，没有相应 Int64 sum 例子；base sum 的原错已有 D/pandas__32dd55cb8331c36df6b485eb042c7d2d/orig/captures/mcve_sum.out:25。**该组合反例只有静态路径支持，未生成补丁、未运行评分，不能计为新的实测候选。**

**影响。** 将来按这些规则做诊断，会把部分修复甚至修改了要求参数的错误实现排除出能力失败，夸大修复能力。候选表目前正确把 W1 标为错误解；未发现已经据此产生错误能力汇总的证据。问题在建议的后续判读规则。

**建议分期。** 在首次按此规则汇总诊断结果前修；无需修改或重写原始 reward、账本和历史证据。

**文件与行号。** 主定位：S/results/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/review.md:210；同类定位：S/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/card.md:60。传播入口：S/README.md:71 的“只有 T2 失败”仅应作为待复核标签。

**复现命令／最小探针。** 运行本目录 audit.py，核对 ledger_rows 中 W1 的 12/13，以及 orange_parameter_routing_probe.W1_gold_silently_drop_l1.fresh_l1_selected.penalty == 'l2'。在已有运行环境做最终行为判读时，最小增加的是检查 m.skl_model.penalty == 'l1'；pandas 则至少补读补丁的非 mean 数值 EA 路径。这里没有请求新容器实验。

**最小验收条件。** 文档把上述失败键组合改成“疑似规格／接口争议，待按补丁语义复核”，不得自动改变能力标签；W1 必须保持“未满足指定 L1”的错误解标签。pandas C1 只有在确认数值 EA 归约要求成立后，才可判为测试文字冲突导致的误拒。原始 reward 与语义复核结论分列，二者不得互相覆盖。无需先改 grader 或添加维护测试即可修正文档规则。

## 4. 逐题实证、推断与缺口

### pandas 32dd55cb

**核心结论成立。** 公开题面只要求 numeric_only=True 的数值 EA 归约，base 的 frame.py:8317–8335 在数值筛选后分派块。C1 对数值 EA 调自身 _reduce，其它块保留 base 路径；这不是只对题面随机数组特判。其 91/92 得分与原日志相符，失败是 Period numeric_only=False 的错误文字，与本题新增数值 EA 功能无关。

公开 P/<pandas>/worktree/pandas/tests/frame/test_analytics.py:899 要求 reduction operation 'mean' not allowed；隐藏对应 H/<pandas>/hidden_tests/test_1.py:899 要求 mean is not implemented for Period。两者在同一 DataFrame 场景互斥。gold 私有对照的公开 analytics 文件恰好只有此项失败，支持“gold 改变了公开已有错误文字”的因果解释。

**边界。** C1 的隐藏评分已经实跑；本批没有 C1 的混合题面原例／含 NA／非 mean 公开行为对照。C1 满足题面范围的判断仍包含源码推理，不能把 91 个匹配键解释成全部功能都验证。C2–C4 尚未跑。对非 mean 的漏测判断有公开“reduction operations (e.g., mean)”与 base sum 实测支撑；只补 NA mean 不能排除仅修 mean 的候选，这一点原 reviewer 已指出，应保留。

**T0 建议。** 放宽 T2 的两种错误文字有足够依据；若补测试，含 NA 的混合数值帧和至少一种非 mean 归约各解决不同缺口，应分别说明。不要把 gold 的全 EA 分派路线当作唯一合法实现。是否修改 oracle 仍由用户决定；本审查没有实施。

### coveragepy 5dbbe143

**歧义与漏测均成立。** 题面说“only once each / duplicate warnings”，没有定义去重键；公开 _warn docstring 的确把 slug 称作 warning suppression shorthand（control.py:336–350），因此“按 slug”有公开线索，但不足以使“按消息”明显不合理。隐藏 test_1.py:545–549 要求同 slug、不同消息的第二条也不显示。CE1 按消息去重得 74/75，CE3 按 slug 去重得 75/75，日志支持对应结论。

应称 CE1 为“满足公开歧义的一种合理读法、与隐藏 oracle 冲突”，而不是已证明它在所有可能解释下正确。来源 gold 或生成器见过的 docstring 可以解释原作者意图，不能补足求解者没有收到的规范。

CE4 得 75/75 的漏测证据更直接：本次执行候选原 _warn 函数，连续发 ('first','x',once=True)、('second','y',once=True)、再次发第二条，CE4 只记录 first，CE3 记录 first, second。前两条消息与 slug 都不同，任何“每个警告只显示一次”的合理读法都不应吞掉第二条的首次出现；无需以 gold 为规范就能判定 CE4 错误。

**T0 建议。** 澄清 slug 的题面修订或隔离该题都有充分依据。题面修订本身不会改变 CE1/CE3 的评分；若目标包括消除 CE4 漏测，必须另补不同 slug 的首次显示断言。该断言不应被描述成仅修题面就能得到的效果。关闭旧 R04、暂不改辅助导入的方案可接受，前提仍是本题仅要求 _warn 参数行为；不等于所有扩展调用点改动都已证明安全。

### orange3 9b5494e2

**接口约束与部分误拒证据成立。** 公开要求是为指定 L1 penalty 自动选择支持它的 solver；隐藏 test_1.py:135–153 又要求 "auto" 字面值、_initialize_wrapped() 返回时解析、L1 固定为 liblinear、Python None 原样透传。这些不是题面行为要求自然唯一推出的实现。

- **V1、V3：**原始评分各 12/13，独立私有 MCVE 记录 G/orange3_mcve/OR{1,2}.json 的完整 iris 均 rc=0；V3 有 ConvergenceWarning，不能把它写成收敛质量已验证。L1 分别仍是 liblinear/L1、saga/L1，故“只因隐藏接口约束被拒”的具体判断有较强依据。
- **V4：**12/13 是实证，新建 L1 learner 会选择 liblinear 是源码与本次参数探针支持；完整 iris 没有独立 MCVE 记录。实现会把解析结果永久写入 self.params：先拟合默认 L2，再设 learner.params['penalty']='l1'，第二次路由仍为 lbfgs/L1。P1（13/13）也有此现象。base 的 params 确为可变 dict（Orange/base.py:512–518，公开 test_classification.py:370 有更改 learner 参数先例），但是否把 LR 的“拟合后改参数再复用”列入此次接受域尚未决定。此处是**范围与复用风险观察**，不是本次已证明的任务违规，也不能据此把 V4 的 0 分直接称为应得。
- **V5：**12/13 的唯一差异是映射表不接收 Python None。关键边界可以从原环境日志核实：D/orange3__9b5494e26f407b75e79699c9d40be6d/orig/captures/test_lr.out:68–71 展示 sklearn 0.22.2 的 all_penalties = ['l1', 'l2', 'elasticnet', 'none']，不含 None。隐藏测试只构造估计器并查看属性，没有拟合 None。因此不能把“V5 对 None 抛 KeyError”说成它没有支持一个题面要求的合法 penalty；它与字符串 'none' 的分支也不能混淆。完整 iris 仍仅有静态推断，当前摘要已正确标明。
- **V7：**更换了默认 L2 solver，两个 scorer 键随之 PASSED；这证明了当前 FAILED 期望受默认 solver 影响，不证明 V7 是合理任务修复。不得拿它凑“第八个误拒”。
- **W1：**把 L1 换成 L2，属于实质错误，现有 grader 拒绝它是对的。它也是 F1 的现成负对照。
- **G1：**只改默认 multi_class='ovr' 时，两 scorer 仍在相同首个断言失败。这支持“仅改 multi_class 不足以翻转这两个键”，不等于 multi_class 对所有特征得分或后续断言都没有影响。

本次重新比对了同仓公开树：另外 5 题的 _initialize_wrapped 与本题 gold AST、test_auto_solver 与隐藏 AST 均一致，跨题暴露事实成立。它说明快照包含答案；没有测量模型是否访问或记住了其它题，不能把暴露事实直接换成实际污染率。

**T0 建议。** 行为级测试方案有充分理由，且原 reviewer 草案已包含 m.skl_model.penalty == 'l1'，能正确排除 W1；只补 solver='auto'/liblinear/_initialize_wrapped 到题面则是明确收窄接口接受域，不能仅因它等于上游修复就宣称没有增加公开要求。该取舍原材料已经说明“接近把测试写进题面”，应由用户明确选定。V4/P1 的复用边界属于 experiment-required／接受域待定，当前不另增运行门槛。

### orange3 22e98f8f

**题面泄漏结论充分。** 公开 user_prompt.txt:14–23 的函数可执行 body 与应用 gold 后 unique_in_order_mapping 完全相同；唯一差别是仓库原有 docstring 未复制。actor 的 mcve_statement_code.out:1–2 已输出正确 [0,1,2]。本次独立抽出题面函数，对 364 个长度 0–5、元素来自 {0,1,2} 的序列检验“首次出现顺序、唯一性、按 mapping 重建原输入”，均成立。它不是只偶然修好 [2,3,1] 的答案片段。

隐藏 test_1.py:77–100 同时覆盖空输入、重复值、多个置换和重复的三元轮换，断言不固定返回 list/ndarray 类型。在此范围未发现误拒合理算法的证据；尚未实际给 numpy 逆置换候选评分，不能把“评分侧没问题”扩大为完备性证明。三道后续公开快照包含相同修复函数，本次再次核实。

**T0 建议。** 删除泄漏实现或替换为真实 base 代码，不改变现有期望行为；保留示例调用的定义／导入即可。只改题面时，验收重点是新公开包、摘要和真实消息消费，不需要用重复评分冒充题面修订验收。仍不能据函数探针证明正式模型收到的完整任务消息；这是 actor 主审的范围。

## 5. 开发命令证据核对

四题 orig/attempt.json 与 captures 均记录真实 CC 命令经 agent 执行；私有 gold 对照为 root 身份。下面计数直接取输出，不把模型桩当真实求解，也不把 expect='any' 下命令成功执行当作测试通过。

| 题 | base → gold 的目标表现 | 公开测试 base → gold | 判定 |
| --- | --- | --- | --- |
| pandas | mean 报 dtype ValueError → B=5.5；sum 同类报错 → A=45/B=55 | analytics 91过1跳 → 90过1败1跳；整数函数25过→25过 | 摘要准确；新增失败就是公开 Period 文字 |
| coveragepy | 不认 once → 只打印第一条 | warn 子集6过→6过 | 摘要准确；公开测试不区分新增 once 功能 |
| orange9 | lbfgs/L1 ValueError → liblinear/L1 模型 | LR 9过3败1跳 →10过2败1跳；Qt 21过3败3跳→相同；repr等5过→5过 | 摘要准确；不能把恒失败键当作有效通过信号 |
| orange22 | 仓库 mapping [2,0,1]→[0,1,2]；题面函数始终正确 | helper1过→1过；widget23过3跳→相同 | 摘要准确；题面确实已经给修法 |

pandas 的 checks.bashenv_denied_for_agent=false 不是“agent 可写”证据；CC 命令未输出该检查标志。orig/prelaunch.json 另有 agent 写入拒绝事实，actor 主审已核对。因此本报告不把共同“不可写”结论列为问题。

## 6. 收口与验收边界

- **已验证：**14 条本批评分的候选与日志身份及逐键判分；coverage CE4 的错误行为；W1 将 L1 改为 L2 的参数语义；orange22 泄漏与有限输入域的一般映射性质；四题 devcheck 输出摘要。
- **静态支持：**pandas C1 的题面修复路径与 T2 冲突；orange V4/V5 新建 L1 learner 的行为；pandas 仅修 mean 的组合反例；V4/P1 拟合后修改参数的复用风险。探针验证的只有参数路由，不含数值训练结果。
- **未验证：**新的真实模型求解、候选完整功能域、V4/V5/W1 完整 iris 独立 MCVE、修改后的 oracle、真实提示渲染、跨题污染率。没有替这些缺项增加授权门槛或改变既定处置。

F1 的最小修正是收窄诊断分类规则，按候选语义复核再决定能力标签。其它主要结论足以支持提交四题对应的 T0 选择，但不构成对任何材料修订或训练使用的批准。
