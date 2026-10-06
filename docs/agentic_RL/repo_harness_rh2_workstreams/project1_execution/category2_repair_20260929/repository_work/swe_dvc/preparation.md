# DVC 四题当前入口

2026-10-04。负责人：`SWE | DVC 题目修订`，线程 `01a0fd62-ca8f-7173-a3fd-0e3795c646bd`。修订、CPU验收、两模型首次探针与题主候选／轨迹分析由本线程负责；共享发布和GPU执行分别由原两位负责人维护，共享总账仅通过CLI更新。

**四题CPU／公开actor／非作者验收完成，两模型首轮结果全部返回。5839、6954两模型均通过；4166两模型均失败；9395的Coder同原FP CPU补评分0、Qwen原GPU评分0。四题配对语义和执行核收均已完成，结果已ACK，活动指针全部释放。** 9395原GPU null／入口1／cleanupfalse保留，CPU0是独立补分，不是新模型样本。当前无必跑CPU／GPU缺项；未判定稳定性、训练资格或最终用途。

执行遵循[覆盖与研究政策](../../overnight_watch_20261003.md)：优先其他未测题／缺首臂，暂缓普通追加采样，不机械凑三次。cpu-b已退租，不再派发；本线程不操作云资源、改共享并发或启动额外实验。历史作者报告与证据保留当时状态，本页、题卡、results与总账维护当前事实。

## 四题结果与候选差异

| 题目／材料 | Coder首次候选评分 | Qwen首次候选评分 | 当前解释与入口 |
| --- | --- | --- | --- |
| [5839](tasks/iterative__dvc-5839/card.md)／R10 | 1；2F／21P全过 | 1；2F／21P全过 | 两者正确传precision，23实际／23参考。Qwen真实CLI默认／3／8，Coder弱mock和3生成文件限制保留；[配对分析](tasks/iterative__dvc-5839/two_model_first_round_semantic_audit_v1.md)／[验收](tasks/iterative__dvc-5839/two_model_first_round_acceptance_v1.json) |
| [6954](tasks/iterative__dvc-6954/card.md)／R14 | 1；3F／12P全过 | 1；3F／12P全过 | 合法负整数／浮点／容器行为正确，26实际／15参考，11额外均通过。非数字一元边界不扩评分；公开自测与正式lock／改值覆盖分开；[配对分析](dvc4166_6954_two_model_first_round_audit_20261004_v1.md)／[验收](tasks/iterative__dvc-6954/two_model_first_round_acceptance_v1.json) |
| [4166](tasks/iterative__dvc-4166/card.md)／R14 | 0；F0/3、P60/60 | 0；F1/3、P60/60 | 66实际／63参考。Coder只拆分组；Qwen修否定尾斜杠，正向目录／父目录遍历仍错误；[配对分析](dvc4166_6954_two_model_first_round_audit_20261004_v1.md)／[验收](tasks/iterative__dvc-4166/two_model_first_round_acceptance_v1.json) |
| [9395](tasks/iterative__dvc-9395/card.md)／R20 | 原GPU null；同原FP CPU0、F0/3、P37/37 | GPU0；F1/3、P36/37 | 两侧各41实际／40参考，均37通过／4失败，失败节点不同。Coder先检查致恢复不可达、helper只本地checkout；Qwen普通source／frozen局部恢复成立，但漏repo import／远端run-cache，多余pull破坏modified无远端；[配对分析](dvc9395_two_model_first_round_audit_20261004_v1.md)／[验收](tasks/iterative__dvc-9395/two_model_first_round_acceptance_v1.json) |

F2P是基线失败、修复应通过的参考；P2P是应保持通过的参考。实际节点可以含未评分原测试，两个分母分开。9395原import是额外失败，parser42条中的captured ERROR不是实际测试节点；旧GPUinfra/null也不计行为0。GPU线程曾把Qwen P写成37/37，原回执一直是P fail1/37，已用官方correct-summary保留旧摘要并更正。

## 探针闭环和证据

| 固定请求 | 当前交接 |
| --- | --- |
| [5839 input](tasks/iterative__dvc-5839/probe_request.json)／[发送](requests/dvc5839_probe_delivery_20261003_v1.json) | returned、题主ACK、活动指针释放 |
| [6954 input](tasks/iterative__dvc-6954/probe_request.json)／[发送](requests/dvc6954_probe_delivery_20261003_v1.json) | returned、题主ACK、活动指针释放 |
| [4166 input](tasks/iterative__dvc-4166/probe_request.json)／[发送](requests/dvc4166_probe_delivery_20261003_v1.json) | returned、题主ACK、活动指针释放 |
| [9395 input](tasks/iterative__dvc-9395/probe_request.json)／[发送](requests/dvc9395_probe_delivery_20261003_v1.json) | returned、题主ACK、活动指针释放 |

各输入原SHA、原题面与中性开发说明不热改。题主分析覆盖根因／修法、定位／纠偏、工具、可观察并行、自测／最终陈述、效率／资源与结束原因；非作者复核和原件身份可在每题审计／验收找到。ACK只表示已核收结果，不表示候选正确或获得训练资格；不发普通ACK／接单中转消息。

[4166／6954新非作者执行报告](reviews/non_author_dvc4166_6954_pair_execution_review_20261004_v1.md)、[新非作者语义报告](reviews/non_author_dvc4166_6954_qwen_pair_semantic_review_20261004_v1.md)已核收。9395的[新执行报告](reviews/non_author_dvc9395_pair_execution_review_20261004_v1.md)与[新语义报告](reviews/non_author_dvc9395_qwen_pair_semantic_review_20261004_v1.md)均已核收，[Qwen七维审计](tasks/iterative__dvc-9395/qwen36_a1_semantic_audit_v1.md)已完成；Coder原[七维语义](reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)与[执行报告](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)按已核版本复用。[同原FP CPU读回](tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md)及[验收](tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)保持独立身份，不改原GPU正式评分缺失事实。

## 可用于后续分析的信号与限制

4166两个候选都缺真实目录遍历验证，Qwen正确mock／局部纠偏仍不足以覆盖正向父目录；9395 Qwen真实push／删文件和缓存／恢复内容优于Coder的hasattr自测，但没有覆盖imports、远端run-cache和modified无远端。失败是候选范围不完整，没有新材料无效证据。5839和6954两模型单次通过也不说明任务饱和；候选正确性与自测质量分别记录，不据一次结果直接分训练／留出。

6954 Qwen最终只报两模块31通过，却遗漏已观察的5个扩展实验失败；仅1个在原基线仍失败，另外4个原因未知。9395 Qwen最终五组公开193项（含追加2）有结束摘要，修测试target和identity断言保留恢复内容；正式失败不是它曾看到又隐瞒的结果。原FP、评分投影和hygiene clean分别解释，不能由clean推断模型没改测试或没留脚本。

三份新Qwen封存分别435／417／429成员，完整基线分别430／552／615项；实际模型请求65536输出预算与CC元数据32000分开。9395全部88工具身份匹配，86参数对象逐字一致、两处规范化差异单列，不声称88参数字节全同。资源样本有缺口、baseline environment_package_digest仍null，8GiB writable-layer配置未证明强制；不推断全程峰值、全程无OOM或最低配置。Coder模型清单声明28／列出25文件（16权重），Qwen声明40／列出37（26权重），未重新全权重SHA或GPU内存证明。5839另保留code5／code7差异及Qwen每作业实时捕获缺口；[旧计数更正](tasks/iterative__dvc-5839/coder_a1_model_file_count_correction_v1.md)不回写旧审计SHA。

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
