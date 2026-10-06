# DVC 四题当前准备入口

2026-10-03 21:15 SGT。负责人：`SWE | DVC 题目修订`，线程 `01a0fd62-ca8f-7173-a3fd-0e3795c646bd`。本线程负责四题修订、CPU验收、探针交接和候选／轨迹分析；共享发布由“负责处理分类二的明确问题”维护，GPU作业由“负责处理第一类的模型探针”维护。共享总账通过CLI更新。

**四题CPU与非作者验收均已完成并提交两模型首轮；5839已收齐两次raw1并成对核收。4166和6954的Coder首臂分别0和1；9395原GPU轮次null保留，同原Coder FP已在CPU补评得有效0并完成题主与非作者评分／清理核收。三份Coder七维轨迹和原轮次执行独立报告均已核收；三道题的Qwen首臂待返回。** 5839当前无必跑GPU缺项；其余三题不提前核销成对请求。CPU通过、发布／领取或一个模型得分不替代题级分析。

最新[覆盖与研究巡检规则](../../overnight_watch_20261003.md)优先未测题和另一模型首轮，暂缓未开始的普通追加采样；不机械三次／模型，不沿用旧退租流程，不操作云资源。后续校准必须有明确问题。cpu-b已退租，禁止再派发；旧暂停／恢复及作者报告保留当时快照，当前状态以本页、题卡、results和总账为准。

## 逐题当前事实

| 题目 | 当前有效验证 | 下一步 |
| --- | --- | --- |
| [5839](tasks/iterative__dvc-5839/card.md) | R10正式noop0／gold1／固定8错解0，23执行／23参考、2F／21P。公开actor四命令／2基线通过。两模型首轮各1次raw1、23/23通过；相同正确业务修复，执行与非作者语义核收完成 | 首轮请求已ack／活动指针释放，进入题组分析；自测不足、Coder三个生成文件、Qwen实时身份捕获缺口及code5/code7差异保留。无当前必跑GPU缺项，不宣称稳定性／训练用途 |
| [6954](tasks/iterative__dvc-6954/card.md) | R14正式0／1／0，26执行／15参考、3F／12P；11未计分原有实例通过。新增单测完整字节、UID预检／安装／清理和非作者读回已核。R5公开actor11测试通过 | Coder首臂1，26实际全过；冻结负数修法正确，非数字一元边界及弱自测限制保留。Qwen待返回，成对请求不核销 |
| [4166](tasks/iterative__dvc-4166/card.md) | R14正式0／1／0，66执行／63参考、3F／60P；3未计分原有实例通过。R5公开actor v2四命令／29测试及非作者核收完成 | Coder首臂0，3F失败／60P全过、66实际完整；分组改写未修目录语义，是有效错修。Qwen待返回，不为通过放宽材料 |
| [9395](tasks/iterative__dvc-9395/card.md) | R20六控制0／0／1／0／0／0，41实际／40参考；正确c3全过，CPU／actor与非作者核收完整。同原Coder FP的CPU补评有效0，40参考3F失败／37P通过，41实际4失败／37通过，评分和非作者核收完成 | 仅待Qwen首臂及其轨迹／执行读回。旧GPU RC1／cleanup=false／reward=null保持；本次CPU补分另存，成对请求继续claimed |

F2P是基线失败、正确修复应通过的参考；P2P是应保持通过的参考。实际节点可以包含未计分原有测试，执行与参考分母分开。全部CPU原件已回收本机并核SHA；旧infra/null与候选行为失败分别记录。

## 探针交接与当前分析

| 单题请求 | 固定输入与实际发送 | 当前范围 |
| --- | --- | --- |
| swe-dvc5839-precision-values-r10-v1-20261003 | [input](tasks/iterative__dvc-5839/probe_request.json)／[delivery](requests/dvc5839_probe_delivery_20261003_v1.json) | 两模型首轮已returned、题主ack；[双模型分析](tasks/iterative__dvc-5839/two_model_first_round_semantic_audit_v1.md)及[验收](tasks/iterative__dvc-5839/two_model_first_round_acceptance_v1.json) |
| swe-dvc6954-behavior-r14-v1-20261003 | [input](tasks/iterative__dvc-6954/probe_request.json)／[delivery](requests/dvc6954_probe_delivery_20261003_v1.json) | claimed；Coder首臂1已语义复核，Qwen待返回 |
| swe-dvc4166-behavior-r14-v1-20261003 | [input](tasks/iterative__dvc-4166/probe_request.json)／[delivery](requests/dvc4166_probe_delivery_20261003_v1.json) | claimed；Coder首臂0已语义复核，Qwen待返回 |
| swe-dvc9395-behavior-r20-v1-20261003 | [input](tasks/iterative__dvc-9395/probe_request.json)／[delivery](requests/dvc9395_probe_delivery_20261003_v1.json) | claimed；Coder原轮次not_graded保留；题主CPU同原FP补评0及新run非作者核收完成；Qwen待返回 |

各输入保持原SHA，不热改；CPU镜像ID不替代GPU实际ID。GPU原回执须完整读回，原FP／baseline、完整节点、公开prompt、预算、模型服务与清理保持各自证据范围。题主判断根因／修法、定位／纠偏、工具、可观察并行、验证与最终陈述、效率／资源、结束原因；非作者核查闭合后再更新总账，不发普通ACK／接单中转。

5839两份业务源码均只补传precision，公开decimal/default5契约成立。Qwen真实CLI核默认／3／8，Coder mock未断言输出、helper脚本不能证明命令修复，最终陈述过强；Coder完整FP含三项生成文件，hygiene clean不等于最小候选。两模型各一次正确，不推断稳定成功率或训练饱和。原始评分、候选语义与轨迹质量分别保存。

三题Coder首臂的[4166审计](tasks/iterative__dvc-4166/coder_a1_semantic_audit_v1.md)、[6954更正后审计](tasks/iterative__dvc-6954/coder_a1_semantic_audit_v2.md)、[9395审计](tasks/iterative__dvc-9395/coder_a1_semantic_audit_v1.md)与[非作者报告](reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)已完整核收本次语义范围；这不是成对请求ACK；[原轮次执行独立报告](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)随后交付，三个DVC部分及86个原件指针、78条参考已核收，未发现新矛盾。9395原GPU未评分保留；新[CPU原FP补评分读回](tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md)及[核收](tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)已闭合有效0和正常清理，仅Qwen首臂待返回。4166的错误mock／目录遍历误判、6954真实CLI成功及弱表达式自测、9395先检查后恢复／本地checkout和无效mock分别记录。三个原FP各23／6／3项，脚本残留和hygiene分别解释。

5839旧作者报告的模型文件数量另有[计数更正](tasks/iterative__dvc-5839/coder_a1_model_file_count_correction_v1.md)：实际25个文件，其中16个权重分片；清单declared count28与数组25不同，不再称25权重。原作者审计和首轮验收保持原SHA、业务与评分结论不变。三题baseline的environment_package_digest仍为null，不以prepared摘要补填，不将有限资源样本推断为全程零事件。

## CPU与材料证据入口

- 5839：[R10矩阵](tasks/iterative__dvc-5839/formal_matrix_r10_v1.json)、[CPU验收](tasks/iterative__dvc-5839/cpu_acceptance_r10_v1.json)、[公开actor](tasks/iterative__dvc-5839/public_actor_r10_v1.json)。原R7 setup UID/cap失败保留，旧R7–R9不复用；旧原版固定8错解正式分数未知。
- 6954：[R14矩阵](tasks/iterative__dvc-6954/formal_matrix_r14_v1.json)、[CPU验收](tasks/iterative__dvc-6954/cpu_acceptance_r14_v1.json)、[公开actor](tasks/iterative__dvc-6954/public_actor_r5_v1.json)。新增1624B／56行功能文件在正式运行已严格核字节，先前私测git diff漏导出的限制不冒充当前缺失。
- 4166：[R14矩阵](tasks/iterative__dvc-4166/formal_matrix_r14_v1.json)、[CPU验收](tasks/iterative__dvc-4166/cpu_acceptance_r14_v1.json)、[公开actor v2](tasks/iterative__dvc-4166/public_actor_r5_v2.json)。v1 metadata guard误拒的原失败保留；v2只接受精确原metadata差异，未放宽其它dirty树。
- 9395：[R20矩阵](tasks/iterative__dvc-9395/formal_matrix_r20_v1.json)、[CPU验收](tasks/iterative__dvc-9395/cpu_acceptance_r20_v1.json)、[最终运行窄核](reviews/non_author_formal9395_r20_runtime_review_20261003.md)。gold和吞异常错解仍失败原missing-source F；两者均通过新增frozen恢复F，不能描述成新增F判掉它们。正确c3修复通过全部41项。

9395两次旧R14 protect300 infra/null不计作行为负例；隔离诊断成功不覆盖正式失败。R20仅题级reset300→900，实际prepare/spec/账本已核，正式setup149–249秒不证明旧根因或效率问题根治。resource_facts null保留，HostConfig只有正确c3的一个运行时点，不推广到六项。旧failure、支持输入及回执见该题卡历史；已核收支持请求，不再原样重试。

公开actor使用真实CC配合固定桩，只验工具交付；pytest -q计数parser的null与原capture通过数分开。8GiB writable-layer quota仅配置，未证明强制生效；公开actor没独立collect-only／完整基线文件归档，正式与模型原baseline证据各按对应原件记录。

## 公开规格、历史与协作

[干净上下文公开规格核查](public_contract_review_20261003.json)区分独立公开读者与作者私有覆盖比较。5839公开源码明确小数点后n位；4166固定pathspec0.8.1明确尾斜杠、目录后代、否定、根锚定及通配符，新增测试显式恢复父目录，不扩遍历政策；9395读者只核原公开missing-source恢复目标，不冒称issue定义全部dry／no-remote／本地变动。四题原题面／中性开发说明字节未改。

[GPU公开资产准备](gpu_assets_preparation_20261003.json)固定Dockerfile／公开wheel，资产准备不等于GPU已运行。每题revision／发布请求、CPU矩阵、作者报告均保留形成时状态；当前题卡和results吸收后续核收事实，不回写历史证据。[暂停](pause_checkpoint_20261003.md)及[恢复](resume_checkpoint_20261003.md)只用于历史追溯。

当前工作服从[三方协作](../../coordination_workflow_20261003.md)、[CPU资源规则](../../cpu_resources_20261003.md)和[覆盖优先政策](../../overnight_watch_20261003.md)。不覆盖共享未提交改动，不手改总账，不租机、不改共享并发、不自动停机／销毁资源。
