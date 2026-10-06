# Project-MONAI__MONAI-5686 独立交叉复核

结论：与主审及公开阅读形成独立一致的证据链：输出flag不证明真实SSIM输入导数（25），gold未解决公开C5递归detach（27），这不是新引入回归（26 unknown）。支持需要复核的development_diagnostic用途；优先私有gold定向诊断可确认参考修复范围，不能单独证明actor开发资格。

## 决定性主张与八方面复核

|方面|交叉核验结果|
|---|---|
|①版本/输入|base25130db1…、grading与历史原件一致；Expected句结合上下文没有实际互斥规格。|
|②公开目标|loss保留输入图，C5 pseudo-3D有loss docstring:69–74直接依据，不是由未来题或gold发明的新要求。|
|③全体断言|2F2P仅None/cpu同一B1C1问题的flag；8P2P逐个为2D/3D相同/零图像数值。无backward、正确导数、多通道梯度。|
|④gold/替代/回归|绕过最外层detach可修单通道；C>1递归回公开metric入口导致再次detach。改用私有helper本身不是错误，不改通用metric契约也是合理方案。|
|⑤历史评分|w06-1 ledger3/4是2fail8pass→10pass、无missing/skip；只证明现有CPU验收，不证明C5/backward/GPU。|
|⑥开发条件|核心是CPU合成tensor、torch/MONAI；actor身份/源码/依赖未知，既有batch拼接限制不等于环境失败。|
|⑦暴露/提交|授权私有审查仅限审查用途，actor泄漏未知；benign gold投影恢复证据没有越界为完整抗攻击认证。|
|⑧用途/后续|needs_review合适；参考不完整与actor未知是两个不同事实，私有gold对照旨在前者。|

完整决定性链与我封存初判一致：gold改loss两个batch分支为_compute_tensor；regression.py:78–82检查shape/type后调用_compute_metric；C>1在:338再次SSIMMetric(...)(channel...)，经metric.py:330与69–71 detach；当data_range不需梯度时，后续stack/mean/view不可能恢复到y。无需引用5908未来修复推断。B>=3的loss.view(1)拼接问题是原有未改逻辑，应单独记既有边界，不作gold新增回归。

## 复核后补充与风险边界

“加0*y.sum()”可保前向值、让requires_grad及y.grad存在，却不代表正确SSIM导数；我初判已考虑同机制。主审delta补充这一点正确。用于确认C5残留时，仅flag/backward失败已经能区分本gold，但未来评价替代修复不可只要求grad非None。若提案声称验证梯度正确性，应采用非恒等小输入、可推导的导数或数值差分，并保留误差容忍；不能要求相同图像每个像素非零。public_read命令A在不同0.5/0.25常量图上检查梯度总量非零，是所选输入的预期，不应泛化为所有图像的规格。

主审card的私有CPU建议适合回答“gold是否完整覆盖C5”。它必须使用与目标版本对应的私有环境并固定无梯度data_range，保存B1C1对照及C5结果；含gold的环境不可交solver。即便诊断成功/失败符合预期，也只给题目质量和参考范围证据。**对我封存初判最后一节“同时检验actor可用性和质量疑点”的表述作补充限定：只有实际正式actor入口独立执行公开命令并保存完整actor条件时，才有actor资格意义；私有gold诊断本身没有。** 初判不改，本后稿明确收窄。

## 历史delta复核

全文读取refs唯一L1_monai_2记录并核SHA，未沿5908、summary、scan、stage1链接扩读。赞同主审：旧27“调用私有API所以错误/未来重写所以不正确”的理由不成立，实际问题须来自当前C5调用链；旧26用8项P2P推无回归应降unknown；旧ready_for_probe标签不可迁移。

CUDA条件只在已有None/cpu之后追加test2d_4/5、test3d_4/5、test_grad_2，旧expected ID与语义保持；主审纠正旧“条目含义都变”准确。CPU两个F2P的语义重复，不等于parser错误或必须跑collect-only。这里未实际运行CUDA或检查对象id，仍按静态顺序说明。5908版本包含/同侧划分只保留为未经独立核实的线索。

## 最有价值下一步

认可主审唯一优先事项：定向私有gold B1C1/B1C5公开API对照，固定无梯度data_range、保存flag/backward/y.grad与前向值，用于确认静态残留并决定参考/验收修订；不强制全仓、模型或GPU。actor开发资格另外核正式入口/初始工作树/依赖与公开功能，不能让gold参考可执行替代其证据。本review没有执行或派发任何新运行。

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

- `public_read.md`：`1c6342a4eb078f71d896a3cb5cda5d315a3d8e4cbff515389bccbfc6bba7715d`。
- `analysis_before_history.md`：`fe1224ecb0ad89c6695635d2520ad5ef5aebfd3d42fe34421dfe98570b6644b3`。
- `old_findings_delta.md`：`6567ac36b507349a9de627116be8118676bce328252a91f0da33e754a064db48`。
- `card.md`：`59ea56a676ff48b40b3c7bc12431a638d1f0918398a68d5aeecd5663b6177636`。
- `screening_record.json`：`cf8094f266efda2e78ec6f79016a9478c68f19139d12a888597abe8dffc65cf4`。
- `reviewer_initial.md`：`e021faa393369b57ef140653b7d5403d170e7a80551d4eefa37b4e64524a64b6`。
- 唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_2/records/Project-MONAI__MONAI-5686.json`：`6bc79ad28feaf47b8132b9c5817d0b4b995ede80869b8395da33d5fbd8524e0d`（已核）。

仅新增本review.md；reviewer_initial的SHA与release前封存一致。所提card/record修正由协调者完成，本文不将它们记作已应用。全程静态文本、stdlib JSON/hash；无项目执行/导入/测试、安装/网络、容器/SSH/GPU/模型、子agent、commit/push。
