# Project-MONAI__MONAI-2446 独立交叉复核

结论：支持主审“受限development_diagnostic静态候选、needs_review”。列表所有权根因、gold对list的有效性和compat-v1分差无实质分歧。需补checks.by、收窄check40；另建议把我初判的具体有限输入漏测机制保留到后稿，不能把“没有运行mutant”写成“没有静态可定位的漏测”。

## 决定性主张与八方面复核

|方面|交叉核验结果|
|---|---|
|①身份/输入|公开、grading及历史本题身份一致；actual actor unknown，主审区分正确。|
|②公开需求|外部列表不改、内部保留shuffle和seed；不要求深拷贝任意元素，不把全部Sequence新增语义塞进题意。|
|③全部新增/旧断言|F2P test_datalist的唯一allclose与2个P2P逐项与初判一致；5个test_shape实际执行而非expected成员，主审没有混淆。|
|④gold/替代/回归|copy在randomize和首次缓存前，保留随机序列/窗口；SmartCacheHandler不依赖外部列表重排。无证gold新增回归。|
|⑤评分/历史|compat-v1 no-op 7pass+1目标fail、gold8pass；1F2P/2P2P，setup和投影与原件一致。|
|⑥开发条件|原例只需CPU小数组；完整旧模块额外需nibabel/parameterized和临时文件写权，actor仍未知。|
|⑦暴露/提交|私有gold暴露记usage、29 unknown正确；正常gold提交成功不是所有控制面形状的安全证明。|
|⑧用途/下一步|静态候选可保留；不为断言选择器已知事实强制追加CPU，亦不把metadata/import核对单独当完整actor资格。|

决定性源码仍为P/base/monai/data/dataset.py:681–685、712–716、548–586和718–866；公开test_shuffle:120–125精确检查dataset[15]三次为18/13/5。因此旧记录“dataset[0]与期望不同”确错，“只删除randomize就漏过”的理由不成立：保持原顺序时第一轮新尾项为17，不能满足18。旧test_update_cache:74–101确实没有shutdown，主审纠正准确。以上为静态路径，未执行反例。

## 分歧与补充

主审screening_record.json:490的check25=unknown，理由是未有本轮错修通过实测；我的初判指出更具体的静态路径：仅对元素是ndarray的list禁用shuffle、dict列表仍走原shuffle，新增array列表F2P只查外部不变，而test_shuffle与test_shape都使用dict列表，test_update_cache关闭shuffle。因此现有断言没有同时保证新增fixture上的“外部不变＋内部确实按seed打乱”。这不是对任意有限样本的空泛批评，也不是已运行拿满分报告。

建议check25记录为issue、evidence_level=static_inference、低范围/非阻断，并在issues或card保留这一具体机制；若协调者保留unknown，应将note明确成“静态存在该路径，未作运行确认”，而不是用无运行证据否定静态覆盖缺口。此意见不要求更改生产测试、不要求所有Sequence全覆盖，也不改变静态候选建议。公开读者的同一构造检查原列表、dataset.data和前两缓存值提案能针对该缺口，且不规定copy函数或元素身份。

## 已核历史delta

已全文读取refs唯一授权旧L1_monai_1记录并核SHA。主审对旧nibabel失败、旧耗时、旧ready_for_probe标签的处理恰当：只能说明旧记录曾如此报告；本轮引用的09-19 compat-v1原日志确实装4.0.2且5个shape通过，不能沿用旧“五个环境失败”或要求必须3.x。无需沿旧stage1链接重跑或扩读。旧6975关联未核实，保留线索而不认证同族/划分正确。旧P2P少→26 issue的推理已纠正为unknown，赞同。

## 优先下一步与必要收口

认可先获取正式actor交付后的HEAD、准备后porcelain status/RC/阶段及来源差异、解释器/本地MONAI来源、compat底座到达情况这一顺序，不为静态shuffle判别力重做CPU。若目标进一步是认定actor“可开发”，仍须在该actor身份实际执行公开原例/相关窄验证，而非只核metadata或import；这是后续资格证据要求，不是本review下发新运行。我的初判把这一后续功能步骤列得更靠前，现接受主审先取实际交付事实的优先顺序。

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

- `public_read.md`：`07ddcff0f51e11f3a40f2f87841d8dbdc7a6f17d5ec798ac2b69f73b54ef5b97`。
- `analysis_before_history.md`：`d14a76295e09a753f1a53bed7f54b9e8127289586ceefc73efd4e17bb7df3905`。
- `old_findings_delta.md`：`28954003a9a45163f4ebd0582d2691976b074aa5874d41381d86934f7d18b28e`。
- `card.md`：`30d94db60ca45cf0df90c907f530f6fb31d7a01d9444be85d259853019f6b529`。
- `screening_record.json`：`fdecf08a1dd9a41331cb374ceff706b4b2c6088832f89ddf30a7ba4549c58b67`。
- `reviewer_initial.md`：`75833f84344275970ec1de640d30b93ce7803c968ba865d6371ffd0380c1740a`。
- 唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-2446.json`：`604d8709101b5d43bac3026d1d0d8a782ae585f0f43799b2551be32e0321234c`（已核）。

仅新增本review.md；reviewer_initial的SHA与release前封存一致。所提card/record修正由协调者完成，本文不将它们记作已应用。全程静态文本、stdlib JSON/hash；无项目执行/导入/测试、安装/网络、容器/SSH/GPU/模型、子agent、commit/push。
