# DVC9395 当前题卡

2026-10-03 19:30 SGT。**Coder已正常完成解题，候选静态错修；relay评分前清理超时使正式reward null／not_graded，不能计能力0。资源随后闭合，原cleanup false／失败状态保持。Qwen首臂与同一个Coder原FP的正式评分待返回。** R20 CPU六控制与非作者验收已完成，不重跑CPU。

候选把恢复放在 `_check_missing_outputs()` 之后，真正缺失时该检查先抛MissingDataSource，恢复不可达；helper用本地checkout，没有新增cloud pull。`out.exists`是property，不误报缺少括号。原FP canonical `1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456` 保持；GPU已安排首覆盖后评分它，不重新解题覆盖轨迹。

## 首轮候选与轨迹

[题主七维审计](coder_a1_semantic_audit_v1.md)、[逐件原件读回](coder_a1_owner_evidence_readback_v1.json)、[非作者语义报告](../../reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)已完整读回。范围是本次 Coder 首臂；[原轮次执行证据独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)已另行交付并核收，没有新增执行矛盾，仍不代表成对请求闭合。完整 FP 有 3 项，其中 2 个根目录脚本，原件不删改。

先check missing再恢复，缺失时不可达；checkout不新增cloud pull；hasattr脚本不核恢复；后台测试stopped／管道BrokenPipe无完整回归；FP保留2个脚本。实际服务有作业前 engine／adapter、只读模型挂载、argv／HTTP 配置绑定；列出的 25 个模型文件大小匹配，其中 16 个权重分片，声明计数 28 与列表 25 不一致。没有重新全权重 SHA 或 GPU 内存证明。baseline 的 `environment_package_digest` 仍为 null，不能用 prepared 环境摘要补填；资源采样缺口与独立脚本未留存的限制保留。

本轮请求保持 claimed／active，Qwen 首臂待返回，不提前 ACK／returned 或清活动指针。覆盖优先，暂缓未开始的普通重复；本次结果不决定稳定性或训练／留出用途。固定 probe 输入 SHA 不变，材料与原题面／中性说明未热改。

原轮次无grader实例、无正式节点／安装结果／projection，不能继承CPU正确对照的41通过。10:27 UTC两次实际清理读回确认容器／网络不存在、MainPID0、ExecMainStatus1；当前资源闭合不覆盖原失败或产生reward。

## 当前材料与CPU证据

[revision](revision.json)固定 `dvc9395-behavior-v2-draft`：去内部checkout／restore次数约束，核真实缺失数据内容、下游产物、import和用户修改保护；追加frozen输出、dry、无remote、no-run-cache、无hash、依赖变化和HTTP恢复共11参考。dry缺源允许原报错但无状态变化；不用HTTP列举runs，目录部分删除歧义未扩断言。

[R20正式矩阵](formal_matrix_r20_v1.json) 六项0／0／1／0／0／0，41实际／40参考、3F／37P；正确c3_frozenfix全41通过。gold／吞错候选仍失败原missing-source F，却通过新增frozen F，不能说新增F判掉它们。[题主读回](formal_cpu_r20_owner_readback_v1.md)、[CPU验收](cpu_acceptance_r20_v1.json)和[非作者六控制／actor适用报告](../../reviews/non_author_formal9395_r20_runtime_review_20261003.md)核实际prepare／spec900、UID预检／安装和两层清理。R5公开actor17项通过按同public输入复用。

旧R14两次protect300 infra/null保留，不计行为负例；R20六项准备149–249秒不证明旧根因或效率根治。resource_facts null，仅正确c3一个时点实际2CPU／4GiB／PID512 HostConfig，不推广全程或全部控制。GPU本轮实际镜像同CPU c093，setup绑定900但因评分未开始没有实际setup耗时。

## 下一步与历史

等待Qwen首臂和Coder同原FP评分及这两部分执行审查；分别核业务候选、正式分数、infra和轨迹习惯，再决定成对核收。当前不扩材料、不把静态错修写成正式0、不自动普通重复。[固定请求](probe_request.json)、[发送回执](../../requests/dvc9395_probe_delivery_20261003_v1.json)不变。[此前题卡](history/card_before_coder_a1_20261003.md)和旧[材料history](history/dvc9395-behavior-v1-draft/revision.json)保留；当前事实见本页及[results](results.json)。
