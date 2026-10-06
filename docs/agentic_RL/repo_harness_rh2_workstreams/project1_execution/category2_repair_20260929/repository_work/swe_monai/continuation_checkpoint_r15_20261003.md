# MONAI：R15与双模型首次诊断检查点

2026-10-04。持续题主为`SWE | MONAI 题目修订`，thread `01a0fd62-fb0a-7d02-877a-f9ef7ef32399`。**本轮工作包完成：三题CPU及非作者验收、双模型首次诊断共6次候选全部收齐；原评分各1，实际候选与完整轨迹的独立复核完成。** 三题均closed/active=null；2446任务revision16、3715 revision5、6975 revision21，6975原request revision5/ACK。当前本仓CPU在途0、无确定新CPU/GPU作业；旧缺图vendor组合仍阻断，不重跑已验矩阵或成功首臂、不追加普通采样、不授稳定率/训练资格。当前统一入口为[三题汇总](probe_summary_three_tasks_20261004.md)；旧段落中的在途/待字样按写入时历史解释，不操作云资源。

## 2446／6975：两题CPU独立验收完成，探针已提交

6975接收时的版本歧义已按[阻断范围依据](checks/monai6975_blocker_scope_clarification_20261003.json)SHA `32bdd77b2b1e0b98f8b1c952569100f85f1a4a7ec3c4ccc9d60fb227a0f280f2`澄清并直接通知GPU：progress revision17起只阻断`monai6975-dataset-dict-pixels-cpu-v1+vendor-nifti-absent@sha256:0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`旧缺图镜像组合；不按裸测试修订ID阻断R15固定COPY环境。旧actor原件与报告、db75fe72请求均未改，CPU不重跑；本GPU首Coder已核实际COPY镜像、baseline官方原图及首请求原字节，独立执行复核亦完成，见下文新增回读。下文及历史验收中的旧裸标签只作历史来源。

两原发布请求均returned、safe_closed、题主ack完成，发布阶段active_request_id已清空：2446原v1含正式image supplement，6975测试＋COPY合并v3。固定输入和旧失败原件保持，6975旧缺图版本阻断不清空；当前活动项是后续探针请求。

- R15：`cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`；manifest SHA `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`。本包独立核远端1305成员大小/SHA，亦核固定请求、测试、参考次序和环境资产。[回读](checks/monai_r15_publication_readback_cpu_c_20261003.json)SHA `37f930b61f21bb0062059e60548f0275b0f97787f908c88fc7306bfc23562dca`。
- 私有连接及辅助在ignored `runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/`，这里只用`client_r15.submit/snapshot/fetch/remote_python`；不要使用其中继承的历史专题快捷函数。R15 release在cpu-c `/work/rh2-category2-20261003/releases/`，runtime为共用`runtime_cpu_v2`；不SSH cpu-b、不改共享control/setup。
- 新准备申请`monai-r15-prepared-20261003-516a5244` **RC75、status=null，未入槽、未产生prepared**。该旧75原件保留；当前指针已转到真正RC0的新prepare `monai-r15-prepared-20261003-df08dee4`，[新prepared回读](checks/monai_r15_prepared_cpu_c_20261003.json)已核公开输入/有效1F3P及4F60P/固定资产绑定。后续正式矩阵按此新输入执行；不能复用release5 prepared或旧FrozenPatch。
- 新脚本[cpu_formal_r15.py](cpu_formal_r15.py)SHA `7dbc9b7b108b816c6da65ed5c8bd01ebb913fc91cf26b995c81d422a3539f63c`，已冻结到本包`campaign_scripts/cpu-tools-r15-20261003-e23612ef/`，工具记录`tools_r15_v1.json`。启动时client核1305/174成员及工具SHA；所有Docker在`cpu_slot`内，同包只取一个槽，按题串行。
- [非作者静态核查](reviews/non_author_r15_runner_static_review_20261003.md)SHA `1812fd7b3dda189e13cd9e91b99c238c66b7f882a13ae3d6b9cd9199407480b4`未发现确定静态阻断；不是正式CPU资格。后续已有subagent `monai_cpu_review`可接续实际原件核查。
- 正式矩阵：2446已实测 **noop／gold／array_no_shuffle／alternative_list_copy=0／1／0／1**，每行完整4参考；6975已实测 **noop／gold／degenerate_discard_dict_output=0／1／0**、每行完整64参考，无缺席或执行错误。2446 setup900；6975 setup1800；test1800/whole3600、candidate900/cleanup120保持。私有旧controls字节可复用，baseline/FP/projection必须本次新导出。
- 2446固定cpu-c镜像`sha256:28959a332c8a17ebfb2db681d3afaf79f8fd6e845ba51406fc7772f32453bcdd`，NiBabel4.0.2＋固定wheel；6975固定镜像`sha256:fbfdddc4edda1f0ea4c1b76a572bd95045be4bbd202b197a94e8d8ee14a73fd6`，只COPY官方原图。既有同镜像公开actor证据按范围复用，R15正式candidate/grader固定ID不意味着正式训练actor已接入。

2446完整53份原件已回收；[题主核查](checks/monai2446_formal_r15_cpu_c_20261003.json) SHA `02a37a0caa6e0dc563e187b222b82d89a1e51c14266a798fee9f611a8859d7d2`核四行0／1／0／1、完整16参考、UID54322预检/安装/测试/实际候选与grader资源/投影/两层清理。私有audit草稿曾误判image_identity应为裸ID，实际local_build前缀合法；只修草稿，没有重跑CPU。[非作者报告](reviews/non_author_monai2446_formal_r15_review_20261003.md) SHA `dcba766535d6f613a7e00e468735230ed24f988dd178087463b16b2e3324fe36`已通过。2446 probe ID `swe-monai2446-r15-shuffle-cache-nib4-20261003-v1`、固定输入SHA `22aea4dfe7a04e2f8f7b5669a8fb1bdf70137537941cc8a251cb3f0113d88cd2`已落账及直接通知GPU，notice成功留档；两个基座各一次已完成，当前核收与范围见下节；不重复提交。6975完整40份原件已回收，[作者核查](checks/monai6975_formal_r15_cpu_c_20261003.json) SHA `0cb7757c35855da2b7eb92105e11a4f4fa7fa33b857f50747d59f367f958bb69`已通过；实际job已finished0/launcher0，无CPU在途，不能重启同矩阵。[非作者报告](reviews/non_author_monai6975_formal_r15_review_20261003.md) SHA `2d6b9c32c4e7e8c644c9fd697c3aa8b3448b504e2f09dca0e245eb3a36231dc2`已通过；6975 probe ID `swe-monai6975-r15-dict-pixels-public-nifti-20261003-v1`、输入SHA `db75fe723a73f2db160439b271023c033fc82316d03cfdab3c81a37f6d1a91e3`已落账及直接通知GPU，notice已成功归档。不得重提或重跑已完成矩阵。私有audit恢复计数/候选源码路径纠正已记在[6975当前验收](cpu_acceptance_6975_20261003.md)，不是CPU失败。GPU按现有code4精确image_override另核本机镜像和实际公开交付。

## 2446：双模型首次诊断完成

当前入口[双模型汇总](probe_summary_2446_two_model_20261004.md)；[核收绑定](checks/monai2446_two_model_first_diagnosis_20261004.json) SHA `41c78a63341862d0682ec334662b77ae1b5e6acf53db4461367ba1b0457324e5`。总回执SHA `46dd39910e0f837fb8bd83a4c3b8ea57648ce4b24d773f1534ca76085c38cf74`已returned/safe_closed、owner ACK，原请求revision5，任务revision16/closed/active=null。

Coder首臂旧[题主分析](probe_analysis_2446_coder_a1_20261003.md)、[非作者语义](reviews/non_author_monai2446_coder_semantics_20261003.md)、[执行回读](checks/monai2446_coder_a1_execution_review_readback_20261003.json)及[首臂验收](checks/monai2446_coder_a1_first_diagnosis_accepted_20261003.json)按原范围复用，不改历史待字样。Qwen新增[七方面题主分析](probe_analysis_2446_qwen36_a1_20261004.md)、[42相关件/逐调用核查](checks/monai2446_qwen36_a1_owner_analysis_20261004.json) SHA `9c9fdab471c813906df8209e18199d7b736630078a32b2dad7b564571ac67864`、[非作者报告](reviews/non_author_monai2446_qwen36_semantics_20261004.md) SHA `8804213d964423aa2638ad045d7c602f90744b1bcfd98045501e63dc6a9cdefc`。

两首轮各raw1，四参考和完整9P全过；最终外层复制方案均合理。Qwen初版self.data被父构造覆盖，133误宣SUCCESS、153真实旧shuffle回归失败、199定位/203修正，最终7P/17P/Handler1P成立。方法返回协议的外部旧调用/override未验，固定版本唯一调用点已接收、无确定漏改；Coder仅打印自测、新节点只list[np.ndarray]、单次/训练边界都保留。两臂solve code8，Coder服务code4/Qwen服务code8、gateway不同，不声称整棵runtime一致。机械运输、模型身份、有限资源样本及stdout范围见各原报告；没有新题级阻断或CPU待办，不追加普通采样。

## 6975：双模型首次诊断完成

当前入口[双模型汇总](probe_summary_6975_two_model_20261004.md)；[核收绑定](checks/monai6975_two_model_first_diagnosis_20261004.json) SHA `164f3a4942da6f4c5aa76d06b0e69421632780dd8cd82c3a82c6e502bed8baa3`。总回执SHA `18509d0f6ccca7211f300388ec7895ff29b6cf86b791cfad7740f1e402d6a760`已returned/safe_closed、owner ACK，原request revision5，task revision21/closed/active=null；旧vendor缺图组合保留，不误阻断COPY新环境。

首Coder既有[七方面分析](probe_analysis_6975_coder_a1_20261003.md)、[候选非作者语义](reviews/non_author_monai6975_coder_semantics_20261003.md)、[执行回读](checks/monai6975_coder_a1_execution_review_readback_20261003.json)及[首次验收](checks/monai6975_coder_a1_first_diagnosis_accepted_20261003.json)按已验范围复用，原pending标签留作历史快照。新增[Qwen七方面分析](probe_analysis_6975_qwen36_a1_20261004.md)、[42相关件/逐调用核查](checks/monai6975_qwen36_a1_owner_analysis_20261004.json) SHA `0d34d9578c561988a344cd175640f40115f3cdf294d7f2ceaf0af4df5a1560f3`、[非作者报告](reviews/non_author_monai6975_qwen36_semantics_20261004.md) SHA `355a0494e4d268ef407ea1a44903eb4dc163893d187e7018a2d9f5a026001a32`已核收。

Qwen最终单项dataset.py三处lazy=None合理保留Compose策略和dict返回，正式4F60P/64P、安装/测试0、双层清理成立。367事件/23工具/20生成/22HTTP，CC24原值单列；三组多tool消息不误判串行。模型初pending判据输出False后解释Compose末尾flush，路径glob无节点、后台integration最终footer未知/120pipe未完/300明确124及343 All tests pass过宽保留；实际旧模块Dataset1P/Compose55P/DataLoader6P/Cache20P有footer。None及附加Zip/NPZ lazy像素没有专项运行；正式新增CPU硬编码12像素断言通过，原占位无assert也保留。旧CPU0/1/0及独立运行证据不重跑。

实际COPY镜像fbfdddc4、baseline官方NIfTI c01a50ca、原prompt首HTTP字节与相同材料身份均核；两臂solve code8、服务code4/8不同。机械运输400/636件、95/56有限资源样本/gaps、环境谱系null、env_qualification absent、stdout及模型权重证明范围按原报告保持。无新修题或GPU停止项，不重复求解或授予训练资格。

## 3715：双模型首次诊断完成

保持原probe请求`swe-monai3715-string-modes-r5-20261003-v1`、SHA `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67`。两模型总回执SHA `36740efe35e1d98af4c9efcc90e00e3c9582194feb3795d875f59ae94070e832`已returned且safe_closed；题主按总账工具核收并清活动请求，不重提、不重跑。

`gpu1003-monai3715-qwen36-a1`（code_v4）和`gpu1003-monai3715-coder-a1`（code_v7）均原评分1，2F/1P全部通过。当前入口为[双模型首次诊断](probe_summary_3715_two_model_20261003.md)。原[Qwen题主分析](probe_analysis_3715_qwen36_a1_20261003.md)、11件核查和非作者语义审查SHA `5a3ab2715891caf020d4e695bbceebbb4553b9d1f54bb7b5b4b3fc685d53eb4b`保持原件；新增[Coder分析](probe_analysis_3715_coder_a1_20261003.md)、[16件核查](checks/monai3715_coder_a1_owner_analysis_20261003.json)SHA `5207f4049b91ad87cb1e49db983818ff1a2eeabf75f2fe242c6576d9f708f3b9`及[非作者窄核](reviews/non_author_monai3715_coder_semantics_20261003.md)。两种归一化比较修法均合理，无新题级缺陷；Qwen Saliency自测误用与错误宣称、Coder无自测分别保留。两个completed/end_turn无length截断；code4／7共享文件不同，不能称整棵runtime相同。各模型单次不推稳定能力或训练资格。

正常进度不外发、不抄送协调者。接续先读现行三方流程、`overnight_watch_20261003.md`和本包todo；本轮无待回执；只有具体新缺陷才推进对应修订／窄复验，不能因压缩、旧“仍待”标签或历史版本重启矩阵。14:01现行规则优先未覆盖首模型／缺模型，暂缓尚未开始的普通追加，不要求每题每模型三次；旧退租检查及自动销毁规则已停止适用，不能据本包0CPU在途操作机器。旧运行和失败证据不改。
