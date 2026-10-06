# Pydantic：首轮候选审查与当前补验

当前接续（2026-10-04）：六题原固定交接及8511新版补评分均已完成执行、题主分析与独立核收，ACK并清活动指针。8511 R27四候选177CPU奖励0/0/1/0；[原完整Qwen FP新版核收](8511_original_fp_v2_regrade_acceptance.md)确认同版实际177参考为旧173通过、新4失败、奖励0，109原件及独立25项通过。原173/raw1、原完整FP、R26 false/hold保持，模型新采样0；不授训练、留出或稳定成功率。当前续作以[接续点](../continuation_checkpoint_20261004.md)为准，以下历史模型报告保持原范围。

- [8316 Qwen与两模型首次核收](8316_qwen_first_arm_and_pair_acceptance.md)：150新成员/173证据绑定、同451 baseline/f939镜像、144正式参考全过；目标修复有效，Qwen无失败文件。Coder交付缺陷保持。
- [8511原完整FP的v2补评分核收](8511_original_fp_v2_regrade_acceptance.md)：原FP/base/tar字节保持，452项实际fresh census/HEAD及canonical相符，177正式参考中仅新4失败、奖励0非infra。109原件/143绑定、原日志逐参考及独立25项已核，returned ACK/revision5、active清；原[173/raw1首次报告](8511_qwen_first_arm_and_pair_acceptance.md)、[四项直接诊断](../cpu_acceptance_20261003/8511_fieldinfo_retention_diagnostic_v1/actual_v3_readback.md)及[四候选CPU](../cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/actual_matrix_semantics_20261004.md)分别保持各自版本和范围。
- [8567 Qwen与两模型回归核收](8567_qwen_first_arm_and_pair_acceptance.md)：204成员/222绑定，2F/2P失败与无条件handler吻合、raw0保持；Qwen仅源码，Coder失败临时文件保持，无新材料/CPU需求证据。
- [9066 Qwen与两模型成功核收](9066_qwen_first_arm_and_pair_acceptance.md)：214成员/230绑定、370参考全过/raw1，最终六类标量IP限定有效；早期fallback回归已纠正，依赖切换线索撤回，旧容器T3不升本轮评分要求。

- [8511首Coder拒绝核收](8511_coder_first_arm_acceptance.md)：356封存成员、452项baseline、173参考及23生成／22工具核收；公开repr修好但隐藏继承构造TypeError。完整FP仅源码，原0分合理，暂不需材料或CPU改版。
- [8567首Coder拒绝及交付缺陷](8567_coder_first_arm_acceptance.md)：377成员、458项baseline、162参考及44生成／43工具核收；bool改善，但强制生成inner schema使两F＋两P失败。两个实际失败调试脚本未修正／删除，原0分与交付缺陷分别记录。
- [9066首Coder成功核收](9066_coder_first_arm_acceptance.md)：368成员、482项baseline、370参考及35生成／34工具核收；标量IP默认值修复有效并保留dataclass行为，原1分保持。`pytest | head`不能支持模型全测试通过表述；容器IP仍是已有题外T3，不升本轮评分条件。

- [8316首Coder目标修复与交付缺陷](8316_coder_first_arm_acceptance.md)：140件证据绑定、451项baseline及21HTTP／20工具已核；完整源码通用正则修复有效。新增临时脚本真实失败却未清理，正式命令没有收集该文件；原评分与FP保持，P4不升级，两模型尚未成对完成。
- [5662新Coder与版本明确首轮核收](5662_coder_versioned_two_model_acceptance.md)：137件绑定、288项baseline、完整16生成HTTP／15工具已核，唯一生产变更一般NotImplemented委托有效，129参考全过。三份附带脚本实际通过、缓存随FP运输；题面已给修法，独立定位难度有限。旧Qwen原候选评分复用，本次已ACK清指针，跨求解环境不比较能力或效率。
- [5662原初审](5662_qwen36_a1_preliminary.md)：普通比较委托修复真实，当前范围未见具体语义回归。公开题面已给出NotImplemented修法，不能称无提示独立发现；完整FP中的Hypothesis Unicode缓存保留。
- [5662原FP补评分核收](5662_original_fp_regrade_acceptance.md)：同一原候选，含Hypothesis缓存，权限修复新grader安装2.0a3成功；2F2P＋127P2P全通过，grader与标签容器查询清理完成。资源采样未捕获grader，关闭后的网络原件未查询，保持未知。该报告保留当时尚缺Coder的范围；新Coder及本次交接核收见上条。
- [6283原FP的v2补评分与语义核收](6283_original_fp_v2_regrade_acceptance.md)：原完整候选及391项baseline字节保持，code_v8/540e镜像下正式2F＋39P中仅新增PrivateAttr失败；29原件、23输入及相关报告共63绑定核收，零新模型样本。新Coder已另行核收，见下一条。
- [6283新Coder与v2续作核收](6283_coder_v2_continuation_acceptance.md)：新Coder install0/test0、41参考全过，专门可信构造保留合法PrivateAttr；159绑定、完整39工具已审。八个附带文件未清理，包含一个已知相对导入失败调试文件；固定请求两项操作及语义已核收、returned已ACK清指针。原Qwen与新Coder求解环境不同，不作模型胜负判断；重复阶段仍待总协调覆盖门槛。
- [6283原初审](6283_qwen36_a1_preliminary.md)保留当时未验证范围；随后[新CPU实际读回](../coordination_20261003/6283_v2_formal_owner_readback_v1.json)确认Python3.8.19/core0.42.0下无条件删除合法私有状态导致可信构造`TypeError`。[真实语义确认报告](6283_privateattr_v2_cpu_semantic_readback.md)记录新41参考准确拒绝该源码负对照，gold全通过，noop新P2P通过；这份CPU报告只覆盖源码等价负对照；原完整FP的GPU实际补评分另见上条。

模型来源的[有限回溯补证](../coordination_20261003/q12_limited_checkpoint_lineage_owner_readback_v1.json)已核收：29件原件SHA/大小相符，共用独立报告13项核查通过。5662／6283分别17／38次gateway请求、adapter generation及后端HTTP200相符，实际转发名称、固定端点与服务启动谱系支持Qwen/Qwen3.6-35B-A3B的运营来源。

原turn没有内嵌engine ID，服务关联依靠时间、配置和历史／当前同容器身份推断；精确revision来自完成下载manifest与固定只读挂载，HTTP revision/checksum仍为null。这不是每job当时保存的checkpoint快照，也没有重读权重或证明GPU内存哈希。旧config_only/runtimefalse/checkpointfalse原flags不改。补证足以继续带限度的普通题目诊断，无需为此机械重跑模型，不扩大为其它仓库、Q13或训练验收。

两题GPU公开wheel读取修复的[实际局部核收](../coordination_20261003/q12_pydantic_wheel_readability_v3_owner_readback_v1.json)包含52件绑定：完整/testbed分别356／463项保持，Config及旧RootFS层相同，仅八个固定wheel的0600改为0644，目录仍0755；UID54321／54322实际完整读取的字节数和SHA均与原八个公开wheel相符。真实读取容器的Image/User/资源/断网/无挂载已核，八个自有容器删除及末尾标签查空通过。此轮没有安装、测试或模型调用，也不替代8511／9066各自GPU镜像验收。

6283的[旧请求安全partial核收](../coordination_20261003/6283_old_probe_safe_partial_owner_readback_v1.json)通过206件链接绑定，原actor／manager清理及GPU维护者实际无旧资源记录已读；未作题主GPU SSH或新的Docker查询。总账ACK并清指针后，新v2已在R19发布和CPU-a部署，见[题主发布核收](../coordination_20261003/6283_v2_r19_publication_owner_readback_v1.json)。旧原FP安装／重评分及PrivateAttr实际观察明确未执行，不等待旧版本续跑；新材料CPU已完成真实依赖、base新增P2P、gold及原Qwen负对照，非作者实际验收已通过，[新v2普通GPU请求](../cpu_acceptance_20261003/6283_privateattr_v2/probe_request_v2.json)已提交：Qwen新采样0，原FP单独补v2评分；Coder补未执行首臂1。原完整FP重评当轮没有新actor或HTTP投送；随后新Coder首臂的实际环境／公开首请求／41参考及完整语义另行核收通过，固定续作已returned并ACK。旧score不覆盖，旧6283不再开Coder／重复臂。首轮每模型一次不能作稳定能力或成功率结论。
