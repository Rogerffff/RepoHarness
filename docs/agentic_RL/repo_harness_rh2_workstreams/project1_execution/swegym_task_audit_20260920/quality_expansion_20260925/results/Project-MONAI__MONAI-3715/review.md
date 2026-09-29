# Project-MONAI__MONAI-3715 独立交叉复核

结论：与主审在核心判断一致——train诉求未被评分覆盖（25 issue），eval新增参数有公开依据（23不是隐藏规格冲突），gold单行修复静态合理，未证新增回归（26 unknown）。支持先形成行为导向train验收提案；需要补checks.by并收窄check40，保留needs_review/static_review。

## 决定性主张与八方面复核

|方面|交叉核验结果|
|---|---|
|①版本/输入|base d36b835b…与grading/原运行一致；实际actor消息不由题面完整性证明。|
|②题意|文档承诺str/ForwardMode的train和eval；Saliency是动机，不追加修复全部CAM算法要求。|
|③全部断言|test.patch只加mode='eval'；F2P run后仅验image/label，P2P默认mode且空数据。没有train/模型状态/梯度/预测断言。|
|④gold与替代|规范化局部mode后选上下文，与两个Evaluator子类的with self.mode相容；临时变量/等效上下文方案不应被函数身份检查误拒。|
|⑤原评分|w05-1 ledger15/16对应no-op 1fail1pass、gold2pass；失败为eval ValueError，并无train运行结果。|
|⑥开发条件|需torch/numpy/Ignite及工作区MONAI，CPU合成数据/小网络足够，不必预置权重或GPU。actor运行未知。|
|⑦暴露/提交|私有阅读本身不等于29泄漏，后稿已改正；历史源码投影/测试恢复有限支持正确。|
|⑧用途|train漏测足以支持先改进验收设计，不用CPU再证明字符串选择器没有train；仍非正式批准。|

关键代码与初判独立一致：evaluator.py:117–123把look_up_option返回值放错变量，普通Enum的str不等于枚举；gold赋回局部后，Supervised:260与Ensemble:397实际调用上下文。networks/utils.py:294–357控制training/梯度并恢复原状态。主审增加Workflow空epoch直接return的定位合理，本题P2P本身的空数据设计已足以说明它不验证forward训练模式。

## 新增复核与建议

主审对public_read脚本的函数身份误拒风险处理正确：`engine.mode is expected`只是本实现诊断，不能升级验收。建议协调者在后续可交付提案中完全删去此身份约束，使用公开SupervisedEvaluator.run中的forward观测training、is_grad_enabled与退出后恢复；保持eval及枚举合理边界。不能只构造成功或直接with内部helper就声称用户训练推理路径已验。

静态错误实现“只规范化eval”或“全部改为eval_mode”可满足已读F2P/P2P但违背题面train；不需要虚构mutant得分。关于旧“只删elif train也满分”，主审限定准确：若从原base只删该分支，eval字符串比较仍失败；必须先修eval才能构成漏检。旧记录原始措辞确实没有给此前提，不能当历史执行事实。

我的初判把正式actor mode矩阵执行列为下一步；主审先提出行为验收的排序更贴合眼前最有区分力缺口，采纳该顺序。因为未知actor环境的具体事实尚未取得，不以静态确认的train漏测为理由强制立即跑CPU。以后做actor资格仍需正式入口、真实公开API功能执行，私有gold结果不替代。

## 历史delta复核

已全文读refs唯一L1_monai_1本题记录并核SHA，未读3690、dupidx或旧stage1链接。主审把旧23/26的覆盖问题归25、旧3 pass改actual input unknown、旧29 traceback“降低难度”与泄漏分开，均有明确依据。原traceback是合法定位线索，不是答案代码。旧“环境完全干净/4.75秒”的运行未独立取原件，不把它迁移为当前actor条件；现有w05-1原日志足以证明引用grader执行。3690先后包含关系仅作未核实线索，不能因两份报告提到同一线索就自动证明。

## 最有价值下一步

形成基于公开SupervisedEvaluator API的train行为验收提案：forward时training与梯度开启、退出恢复、eval/枚举保留；不用对象身份约束、不改题面、不扩大到全仓或所有Saliency模型。是否修订生产验收及后续运行由协调者/任务二处理。本review未新增或派发运行。

## 结构与共同证据边界复核

对本题screening_record用stdlib JSON逐项检查：14个模板顶层字段齐全；39个checks的编号均在1–40内，未列22可按not_checked，不要求凑满40；status均属于允许的五种值，evidence_refs均存在。**39个已列checks全部缺少by字段**，不满足协调者本阶段明确要求的status/evidence_refs/by，应由协调者补填实际判断者，不把历史作者或independent reviewer冒填成主审。issues.status的open/unverified等不属于checks.status，不误报为检查状态违规。

`facts_ref`两条记录已与run_refs精确选择的原ledger行做JSON字段对照：install、report、parser、projection、cleanup、condition中同名字段、F2P/P2P列表及选中行SHA都一致。历史测试完成/分差与静态语义分开，actor_equivalence=false正确；安装末RC=0没有被当成全链逐步成功。源镜像tag/expected digest与actual ID没有互代，缺失ID保留null。diagnostics中的trusted_setup和control_surface字段支持正常gold路径恢复成功，仍不足以认证任意候选抗攻击。没有新项目运行。

共同需修正的编号：**check40从pass改unknown（或not_checked）**。该问题是筛查流程有没有漏检、误杀、偏差；目前note只证明本包按封存后release读取，不能推出无筛查偏差。可把“读取阶段合规”保留在usage/过程说明，不能重定义40为“已按流程封存”。本次发现元数据缺by，也说明流程完成不能替代质量穷尽证明。1/4/9/16–21的pass需继续保留现有“仅选中历史benign路径”限定；24的pass仅为已读断言未强制实现形式，不扩成所有合理解无误拒。26 unknown正确。

check29已经在后稿改unknown，usage披露授权私有审查者见过gold/test/旧记录且明确不等于actor泄漏，这一修正正确。封存初判中相反编号不要覆写，后稿解释即可。实际actor消息、来源规定初态/准备后status输出与RC/阶段、忽略资产、UID/HOME/cwd/PATH、依赖、写权和资源仍unknown；历史grader成功及私有gold诊断都不能独立赋予actor公开开发资格。

逐项evidence_level目前统一写static_review_and_selected_historical_rh2，正文已说明未运行，不构成已验结果；建议25/27静态主张标为static_inference/static_call_chain，3/8/10等缺证据标explicit_missing_evidence，避免机器消费时误解为相关需求已由历史运行验证。

本review完成后，协调者可更新card的“独立review待完成”及disposition.independent_review/reviewer_findings，附review路径/SHA，并保留未完成的修正和needs_review/static_review。不能因此升为ready_for_probe、训练或正式评测批准。本人没有修改主审card/record、封存初判或任何题目/测试/评分文件。

## 阅读和封存证据

协调者明确cross_review release后才读取本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，及history/refs.json唯一sources本题旧记录。三题的这组获准材料已各自完整审阅（长JSON首次输出截断后以字段/差分分段补读），未读其它包、根汇总、assignments、manifest或旧链接内容。复用了本人initial中逐个F2P/P2P及helper静态原件阅读，本阶段补读本题两份原diagnostics；不声称通读整个项目、全部运行日志或当前runner源码。

本题被审版本SHA256：

- `public_read.md`：`53a312dd9c4acb949ca2511f953b59de5c656d8858694b442a9c0590dbb9cd69`。
- `analysis_before_history.md`：`984e1fff5ba2da925eb85762eade8880bbda15d5de26e3a59b6748cd8ee255d2`。
- `old_findings_delta.md`：`b9a314649feeeb4ed4593924426374d2a62b65f8a0f26d94e212a415c975c8b5`。
- `card.md`：`eea1203329c0bd87ca1bce75e6552dd022a506f5a5aec05276cdd70cc8d11abb`。
- `screening_record.json`：`5719fa46e72af52e62fe54185e710f99653dd6d416ac88b869da2fe7cfc5d2d9`。
- `reviewer_initial.md`：`cc89ab886e401927f867ec7d07cde1c92c01e96ddb8b306c19cdc040e7030f1e`。
- 唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-3715.json`：`e5ccf77b0870e4a046a3da0ec195ecd7b2b764490794248098ed8e3c488c38b0`（已核）。

仅新增本review.md；reviewer_initial的SHA与release前封存一致。所提card/record修正由协调者完成，本文不将它们记作已应用。全程静态文本、stdlib JSON/hash；无项目执行/导入/测试、安装/网络、容器/SSH/GPU/模型、子agent、commit/push。
