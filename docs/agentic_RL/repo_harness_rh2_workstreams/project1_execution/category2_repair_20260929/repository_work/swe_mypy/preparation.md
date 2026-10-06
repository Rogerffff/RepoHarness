# SWE mypy：两题当前入口

2026-10-03 21:33（Asia/Singapore）。持续负责人：`SWE | mypy 题目修订`（`01a0fd63-1eba-7133-951d-7dd3475840a4`）。**两题正式CPU验收和两模型各一次首轮观察均已收口。** 15184 R10四候选0/1/0/0，两模型原raw1、各五参考通过，核心源码相同，见[配对验收](python__mypy-15184/two_model_first_round_acceptance_20261003.md)；总账已returned/ack并清空活动请求。10174原Qwen候选已在新GPU80418df/code8完成实际安装及四参考重评分，题主与两非作者[有界验收](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)完成；新增Coder首轮及两模型[题级配对验收](python__mypy-10174/two_model_first_round_acceptance_20261003.md)现已完成，两臂各四参考通过、源码修法不同。两题总账均returned/ack，活动请求清空；本包无已知CPU/GPU待办或在途，训练、留出资格均未增加。

| 题目 | 已验证的问题与材料 | 当前剩余工作 |
| --- | --- | --- |
| [10174](python__mypy-10174/card.md) | R6正式矩阵0/1/0保持；原Qwen候选CPU r16及新GPU80418df/code8窄安装/四参考重评分均验收，原1472基线/50投影含49cache保持。 | [两模型首轮验收](python__mypy-10174/two_model_first_round_acceptance_20261003.md)已完成，Coder 66项完整候选/四PASS、两非作者核查与行为分析已核。returned/ack、活动请求清空；Qwen恢复不增样本，旧安装RC1/raw1保留，无CPU/GPU待办。 |
| [15184](python__mypy-15184/card.md) | R10正式3F/2P五参考、四候选0/1/0/0；两模型各一次首轮语义/执行观察已由题主及非作者核实。 | [配对验收](python__mypy-15184/two_model_first_round_acceptance_20261003.md)已完成；returned/ack、活动请求清空，无新增CPU/GPU作业。P3自验陈述与有限模型身份记录保留，稳定性未知；普通追加采样暂缓。 |

## 结果分析与资源依赖

结果回读按[完整性与资源依赖](result_completion_20261003.md)执行。逐轨迹核方法、定位、工具、并行机会/实际执行、验证及效率，环境、队列和模型时间分别报告。15184的[Qwen轨迹](python__mypy-15184/qwen36_first_arm_trace_20261003.md)和[Coder轨迹](python__mypy-15184/coder_first_arm_trace_20261003.md)已核；Coder更少回合但累计输入更多，单次不作性能排序或稳定性结论。Q13新增40请求/adapter/后端对应见[独立来源补证](python__mypy-15184/q13_operational_identity_supplement_20261003.json)，不借用旧Q12审查范围；两模型身份均仅作有限运营归因，旧false标记不改。10174已有[Q12与权限补证](python__mypy-10174/gpu_identity_and_wheel_supplement_20261003.md)，87请求对应、完整清单不变和双UID读取已核；随后[新GPU原FP重评分](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)已验收，无新Qwen样本；新增[Coder轨迹与比较](python__mypy-10174/coder_first_arm_trace_20261003.md)已核，两模型首轮完成。Coder更少回合但累计输入更多，内联flags对照及自验声明过宽等行为问题保留，不作单次稳定性/性能排名。按[当前覆盖优先规则](../../overnight_watch_20261003.md)暂停尚未开始的普通追加采样，不机械要求每模型三次；后续真实缺陷才按影响登记。停止沿用旧退租检查/自动销毁安排，本线程只记录题级依赖。

## 当前协作与交接

按[三方流程](../../coordination_workflow_20261003.md)和[总账工具用法](../../task_board_usage_20261003.md)执行。共享[总账](../../repository_work_packages_20261002.json)只由工具按目标revision更新。本包材料、阶段、检查点和阻塞由题主维护；普通进度不广播，不抄送原管理线程。

- 10174原请求：`swe-mypy10174-strict-equality-v1-20261003`，总账材料版本`binding-sha256:deeca18d4afab72556bf2edc4a62c755ac718acacd4625627efd2c19e191641b`是固定source binding摘要，生产身份仍按R6及原请求内容。初次GPU intake为 `runs/ordinary_gpu_probe_20261002/intake/mypy10174_v1/review.md`；GPU code_v4已实际运行Qwen3.6，原FP`5772af…`、baseline`337be5…`及raw1保持。兼容/旧安装缺陷证据分别记；现在Coder完整原件及题级配对验收已完成，整项returned/ack、活动请求清空。请求里的迁移code_v3 blocker/legacy_gpu_status是已失效历史字段，当前progress与固定验收为现状。
- 15184发布请求：`swe-mypy15184-nested-v2-publish-20261003`已returned并回读/ack，旧活动指针已清空。固定输入SHA `e6e0380752b6a0d7076278a237f6586f2f8dbfab8f2b540aeba031cc4c4db214`不变。正式材料为`mypy15184-nested-nominal-types-v2`、grading`3a3c4e…`，R10 manifest`00ac5c…`；cpu-a950成员及可信48/216部署证据已核，实际测试命令不含-k、只选五node。正式CPU增量现已验收，不再以旧草案阻断此正式版本。
- 15184探针请求：`swe-mypy15184-nested-nominal-v2-20261003`，固定输入SHA `623bc39612a9812e92b3c5ec218480e916e3c4dae219c4e4f17d7e85056e993e`；两模型各1次、`probe-wide-v1`已完整返回。题主核回执及原件后，request revision5已ack，task progress revision13清空活动请求、phase=closeout。见[固定配对验收](python__mypy-15184/two_model_first_round_acceptance_20261003.json)。旧GPU回执not_sent/request_returned是冻结时状态，未改写；当前事实以总账为准。
- 行政暂停已被用户恢复通知接替；[旧暂停点](pause_checkpoint_20261003.md)及[恢复检查点](resume_checkpoint_20261003.md)保留当时事实。CPU作业沿[资源入口](../../cpu_resources_20261003.md)在cpu-a完成，端口18198/18199；主机开放、版本发布和题级CPU验收是分别核实的事实。

## 证据与身份

每题 `revision_proposal.json` 是准备记录，**不是生产schema或冻结登记**。当前15184提案包含一个已有正式P2P、一个新增嵌套F2P，另四项只作开发回归。公开题面和bundle字节保持fresh审的固定输入；不把私有候选或新增测试交给solver。

- 原正式评分：[10174作者回读](python__mypy-10174/original_cpu_readback_20261003.json)、[15184作者回读](python__mypy-15184/original_cpu_readback_20261003.json)。三条原参考逐项执行/解析、缺席0；安装成功、源码来自/testbed、runner摘要未变、候选与grader清理正常。两非作者已核原件；这些仍是原材料成绩。
- 10174修订后正式评分：[新CPU作者回读](python__mypy-10174/revised_cpu_readback_20261003.json)。第六版重新prepare并绑定新grading摘要；四参考、安装、可信测试恢复/保护、源码投影、runner完整性、候选和grader清理、slot/driver退出均已逐项核对。繁忙75的前两请求未执行，正式成绩来自第3个新job。
- 私有行为：各题 `private_behavior_readback_20261003.json`；15184另见 [嵌套F2P校准](python__mypy-15184/nested_guard_cpu_readback_20261003.json)。真实节点已收集执行，私有root容器清理确认；不是actor权限证据或新正式reward。
- 15184首嵌套草案误期望小写list，现有suite强制List导致gold也失败。首attempt原件保留；v2依据公开base配置修正，gold真实通过，原三case正文逐项不变。
- [非作者材料窄核](reviews/non_author_material_review_20261003.md)接受原准备范围；[fresh公开静态审](reviews/fresh_public_reader_20261003.md)只见固定公开输入和base，未运行、未见私有。新增嵌套F2P及R10正式增量已由下述两份新报告另核，旧审SHA保持不变。新中性brief只引用已有公开环境事实，Falsifier作非fresh边界核；不冒称原fresh审覆盖该新增文件。
- [运行链核查](reviews/non_author_cpu_execution_trace_20261003.md)和[反证/最小方案核查](reviews/non_author_cpu_falsifier_20261003.md)均已完成旧证据及10174新正式增量；已见gold/private上下文，非fresh。题主核对关键原件后的[10174普通探针CPU条件收口](python__mypy-10174/cpu_probe_acceptance_20261003.json)不授予GPU运行、全面隔离、训练或留出资格。
- 10174原GPU候选窄重评分：[作者原件回读](python__mypy-10174/gpu_install_revalidation_readback_20261003.json)、[运行链审查](reviews/non_author_10174_gpu_install_trace_20261003.md)、[反证审查](reviews/non_author_10174_gpu_install_falsifier_20261003.md)及[新收口](python__mypy-10174/gpu_install_revalidation_acceptance_20261003.json)。原FP/完整基线与投影不变，r16在CPU可读wheel镜像上得1、四参考通过，三安装实RC0，1建1移无遗留。前置安装造成预热，来源为独立Python探针；editable元数据安装前已存在，resource_facts为null。GPU新权限层已核实际ID、1663条完整/testbed清单不变及双UID三wheel完整读取，见[补证](python__mypy-10174/gpu_identity_and_wheel_supplement_20261003.md)；[新GPU实际安装/四参考重评分](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)已独立验收，旧raw不改。本题旧code4 manager与code8不同，实际脚本/材料/参考相符；新GPU无前置CPU三安装预热，不混用r16身份，逐成功pip数字RC缺席等限制保留。
- 15184 R10正式评分：[作者原件回读](python__mypy-15184/revised_cpu_readback_20261003.json)、[新运行链核查](reviews/non_author_15184_r10_execution_trace_20261003.md)、[新反证核查](reviews/non_author_15184_r10_falsifier_20261003.md)及[普通探针CPU条件收口](python__mypy-15184/cpu_probe_acceptance_20261003.json)。四候选每项均收集/执行/解析五键；安装、/testbed源码、可信测试恢复/保护、投影、runner前后摘要、UID/资源、退出和八个候选/grader容器清理已核。原件归档SHA`c7f4f348…`；两非作者独立回读原件，没有重复运行，已见gold/private，非fresh。R10 manager增加DVC条件，本题为None且四诊断均null，不能声称其字节未变。每条成功安装命令未单列数值rc、BASHENV检查未测及ledger包版本`?`等边界保留在收口记录。

- 15184两模型首轮：[Qwen七维回读](python__mypy-15184/qwen36_first_arm_trace_20261003.md)、[Coder回读与比较](python__mypy-15184/coder_first_arm_trace_20261003.md)及[题主配对收口](python__mypy-15184/two_model_first_round_acceptance_20261003.md)。旧Qwen95件和新Coder142件闭包已核，1422完整基线、实际任务block、原FP/可信投影、安装、五参考、退出与双层清理均成立。核心源码相同，但原FP和整个runtime不同；Qwen测试修改被排除，Coder102条含97cache/4脚本全部投影。Coder自验范围过宽登记P3，无新增修题/评分缺陷。Q13新增40请求来源已独立核，Coder列出25文件/16权重分片，manifest声明28的3项未知；不推精确驻GPU权重证明或单次稳定性。

历史09-19评分和09-25actor/开发回归可解释来源与复用条件，不能替代本轮新版本验收。已接收的mypy10424/17071不属本包，不重分配或重验。

## 远端与共享分工

两题固定base digest、3/9个wheel及只复制wheel的派生配方已在cpu-a核实；11份去重资产共3,919,155字节，见 [资产记录](install_assets_20261003.json)。实际派生镜像ID、新作业及证据路径见 [CPU状态](cpu_a_preparation_state_20261003.json)。pins不是完整依赖锁，安装/源码身份仍按每次实际运行核算。

`input_v1`上传43个成员的SHA/大小已复核并保留为历史；其中15184旧五P2P提案不用于正式评分。新增私有校准以独立不可变目录保存。既有矩阵/私有证据绑定首份release；后续新作业使用发布回执确认的本题正式版本（含已验证Git修复）及 `runtime_cpu_v2`，在远端重建prepared，不热切在途材料、不因部署机械重跑已完成证据。每个作业使用全机cpu_slot；繁忙退出75不计作题目失败。

本包端口gateway=18198、stub=18199，串行复用。`actor_checks.py`只编排冻结的真实CC公开命令入口，逐项核真实返回码、解释器、UID、profile、镜像与清理；两题各五条命令实际退出0/1/0/0/0，UID54321、2CPU4GiB、精确镜像/解释器、activation/prelaunch及清理均已核；公开回归分别1/6项通过。各题见 `actor_cpu_readback_20261003.json`。10174原镜像自带test-requirements.txt修改，运行后未新增；15184干净。继承的normal场景bashenv写入检查本清单未执行，按未测披露。控制命令桩不是模型能力探针，也不能替代15184新题面实际solver交付证明。

共用维护者负责新消费者、有效测试补丁/参考/选择/保护、受信PublicTaskBundle、基线恢复与不可变登记和CPU公共支持。本线程维护题级材料、候选、作业编排、证据及自己的总账progress；不手改共用总账，不改共享代码、pins或release，旧审查报告保留原件。初版 `prepare_materials.py` 现在拒绝覆盖已有CPU证据或收敛后的提案。

两题按`probe-wide-v1`各模型先1次提交，GPU实际镜像ID保持null供执行者准备/核实，不拿CPU控制桩填作能力成绩。15184已按 [CPU验收计划与结果](cpu_acceptance_plan.md)完成发布、五参考四候选矩阵及增量核查，独立单题请求不改写在用10174请求；新题面实际solver交付是GPU派发前的检查。成功与失败回传后均由本线程分析并必要修复。当前两题均未增加训练或留出资格。
