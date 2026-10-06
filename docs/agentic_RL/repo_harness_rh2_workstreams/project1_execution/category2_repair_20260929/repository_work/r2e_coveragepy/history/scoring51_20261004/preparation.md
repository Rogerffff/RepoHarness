# coveragepy 四题当前执行入口

2026-10-03。**5dbb、016a、F5eb双模型首轮已分析；EA69 R17 Coder原49/49保持，原候选CPU真实Git确认3字面extra_css文件名漏忽略，正常/再生成通过。最小评分草稿新增1键、单方法三对照窄验已完成，尚未发布；正式非作者报告已通过，Qwen仍原claimed请求继续调查。普通a2/a3覆盖优先暂缓。**

本线程持续负责四题的修订、CPU验证、探针申请、结果分析和必要修复。普通进度只维护本目录与总账；需要交接的固定请求先落账，再直交发布或GPU线程。共享CPU作业由正式入口领取名额，GPU由统一执行者单卡排队。

## 逐题当前结果

| 题目／材料 | 已完成的实际结果 | 剩余事项与限制 |
| --- | --- | --- |
| [5dbb](../../tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/card.md)，R5/038+039+068，76键 | 双模型各76/76；[七维分析](../../tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/model_analysis_20261003.md)与独立语义核查完成，首轮请求returned/ACK。源码满足已选A；Coder留2个失败新测试 | 每模型追加2次的[第二阶段计划](../../tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/repeat_sampling_plan_20261003.json)已登记，尚未收到执行回执；已绑定分析原SHA保留 |
| [016a](../../tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/card.md)，R6/001+086+087，15键 | 双模型a1各reward1、15/15及1非参考skip；[首对七维分析](../../tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/model_analysis_first_pair_20261003.md)与非作者语义核查完成，当前保存/read目标满足，总回执returned/ACK | Qwen坏名枚举及弱化自测、Coder NULL孤儿行及弱helper分别保留。[追加请求](../../tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/probe_request_stage2_20261003_v1.json)每模型另2次已claimed/实际通知，当前普通重复因覆盖优先暂缓，未回传，不称全面正确或稳定 |
| [EA69](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/card.md)，新R17/073–075+093，49键 | 新题面公开内容保留和再次生成要求，fresh公开读者通过；CPU-A实际新首请求、46公开HTML/encoding、空候选41/49、逐键同旧noop、运输与清理通过；[CPU收口](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/cpu_acceptance_r17_closeout_v1.json)及实际CPU独立核查通过；新版Coder原reward1、49/49、正式test0，完整原件/七维及[独立语义核查](../../reviews/non_author_ea69_r17_coder_semantic_review_20261003.md)完成 | [Coder分析](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/model_analysis_coder_r17_a1_20261003.md)记录内容过滤/重写及特殊CSS模式边界；现行fixture通过不称全面正确。[边界窄验收口](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/candidate_boundary_r17_coder_cpu_closeout_20261003_v2.json)已完成作者CPU/草稿单项，正式非作者报告已通过；原请求claimed，Qwen继续调查，未pairACK，旧Qwen不改绑 |
| [F5eb](../../tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/card.md)，R6/076+077，8键 | 双模型各8/8、reward1；[首对分析](../../tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/model_analysis_first_pair_20261003.md)及独立语义核查通过，两种实现均符合A，公开预期同步合理；总回执returned/ACK | Coder留5个调试产物、9次失败工具；无评分污染或材料阻断。[重复计划](../../tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/repeat_sampling_plan_20261003.json)因覆盖优先暂缓，未提交新请求/未运行，单次不判稳定 |

016a当前配对状态见其首对分析；旧Qwen单臂分析保持原时间点与SHA。F5eb当前以首对分析为配对入口，旧Qwen单臂原SHA同样不回写。Coder016a新增110原件/9,538,823字节已核SHA/bytes，原件、原分、失败自测与生成物全部保留；本轮只读原件，无新增CPU或重评分。

## EA69公开目标缺项已修复

已授权目标包括保留已有用户`.gitignore`内容，并真实忽略首次及再次生成的报告。旧ISSUE及中性开发brief没有交付保留要求；实际Qwen覆盖原内容，唯一保留键失败，原0/48-of49准确记录该行为，但不能无条件归为无歧义模型能力失败。旧材料仅本题阻断，旧请求已安全cancelled/ACK，原评分、FrozenPatch及失败自测保留，未执行旧Coder或重复。

新版只补公开行为，不给append方案；statement SHA `39b6b28abc08b21a76a71d8908a7e37a00040cbfc3f9d92ee12bc37b3b6a194f`。正式修订r2e-mr-093，R17 manifest SHA `76aee53151d3b58758d00a9feb5a901b720b4b430f37d2057ed07c1ef0ce2fa6`。073–075及49键保留，gold仍是覆盖内容的负对照；两种safe_append路线原各49/49正对照保留。评分材料、runner、源镜像、base及配方不变，已按精确身份复用旧七候选矩阵。

CPU-A实际首请求精确交付新版题面和未改brief；公开兼容命令46通过、2条warning，FrozenPatch为空。原正式评分noop41/49、reward0，全部49键与R6相同，测试rc1属于预期错误候选，执行与驱动rc0，无infra或partial。基线360项、排除路径4850项、运输往返、实际actor/grader镜像与清理均已核。作者原快照保留当时“非作者待核”状态，当前[收口文件](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/cpu_acceptance_r17_closeout_v1.json)关联后来通过的核查，不回写历史SHA。CPU桩不计模型样本。

新请求 `r2e-coveragepy-ea69-r093-cpu-r17-20261003-v1`，输入SHA `8334dc5a3ba8cd5e769d8ca1dd99fba0ab6b402538a7a3cccd67adbf6bcc92b0`。按统一 `probe-wide-v1` 执行两个既有模型各一次新首轮，具体有效配置、实际GPU镜像和公开输入交付由统一执行者记录。CPU镜像ID不代替GPU身份，旧Qwen不算新版a1。

## CPU依赖与证据

CPU-B已销毁。EA69后来分配CPU-C，但7次prepare均rc75、未获槽，没有启动本包作业；C新尝试已停。发布者正式迁至既有CPU-A并部署R17后，两次作业均finished rc0，非作者核查已通过。当前本包CPU在途为0，两个端口18210/18211已实际确认可绑定，此前R17公开交付验收已收口；后来原候选边界作业和草稿单项作业均已finished0、残留0，全SHA回收。特殊CSS漏忽略已有实测，格式/规则顺序仅观察；正式非作者报告已通过。全机2槽、prepare最多1且占槽，本包最多1作业。未来仅出现具体新缺陷时新增CPU依赖，不重租或销毁共享主机。

历史673原件/29,808,648字节的[CPU归档](../../cpu_evidence_archive_20261003.json)保留。新增R17另有87原件/6,982,615字节的闭批归档及SHA；仅排除已失效控制密钥，清单见CPU收口。此前[退租依赖快照](../../cpu_retirement_dependency_20261003.json)早于新缺陷，原SHA不改；增量及关闭事实见[当前依赖记录](../../cpu_dependency_addendum_ea69_public_20261003.json)。这不表示GPU可退租。

历史CPU控制继续有效：5dbb noop74/76、CE3 76/76、CE1 75/76；016a六合理路线15/15、base及七错误14/15；EA两合理路线49/49及五错误；F5四合理路线8/8。每项用途以原版本和逐键证据为准，不相加成模型数量。

## 版本与用途

5dbb首轮固定R5，其余旧首臂固定R6；EA新版绑定R17。模型回传后，题主核全部生产和公开测试差异、完整推理/有效工具参数、自测与七维消耗，再判断能力、材料或链路原因。原三Qwen首臂321件闭批证据及各已绑定分析SHA保留。

当前用途是注明修订版本的普通基座诊断。公开交付、候选语义、原评分和代码质量分别判定；EA69新版Qwen首臂、材料后续发布/实际消费补评分以及各题追加重复仍待接续。`grading_materials_identity`仍为null，本轮不授训练资格，也不证明正式训练typed actor租约已接通。当前接续见[resume](../../resume_checkpoint_20261003.md)，详细原件见各题card/results_manifest与reviews。

F5eb本轮另核Coder174原件/11,078,409字节及总回执26引用SHA；当前首对分析与非作者核查只读既有原件，无新CPU/模型/重评分。Qwen code4与Coder actor/grader code7（adapter仍code4）的实值差异保留，不称完整运行树相同。

EA69本轮Coder506原件/48,458,118字节逐SHA/bytes一致，360基线逐内容SHA一致；原FP只有html.py，无临时脚本/数据库或公开tests改动。正常两行内容及两次真实Git检查通过，过滤空行/换行归一/同名规则移动为已证代码缺口，该旧七维时间点的特殊extra_css静态风险已由后续CPU确认3字面CSS产物未忽略；原报告SHA保留。格式/顺序变化本身不作为新增评分门槛。开发preserve自测目录放错且未正确重跑，三次失败保留。原49/49不改；不自动阻断整题或改变现行评分，当前不授全面目标成功或训练资格。详细证据以本题七维JSON及非作者报告为准。
