# Conan11594 当前题卡

2026-10-03。R12正式CPU及两非作者保持；[两模型首轮](probe_pair_analysis_20261003.md)各一次均raw1、2F／4P六逻辑／七完整节点全部通过。两份七维与语义／执行独审已核收，总回执已ACK、活动指针已清，无当前CPU／GPU在途；训练资格未建立。

目标是 Ninja Multi-Config 下 `cmake.test()` 实际执行请求的配置。原六个 generator case保持，新增真实CTest Release marker；来源 `test_run_tests[Ninja` 固定ALL绑定两个完整Ninja节点，不让其中一个通过遮住另一个失败。

正式完整noop／gold／drop_config的reward为0／1／0。每方6来源参考对应7完整pytest节点，共18来源状态／21完整节点状态；drop_config通过原六例但实际执行Debug，新增Release检查失败，安装与工具前置均成功，拒绝依据是错配置。原测试文件在base缺席已显式登记并受信创建／保护。完整补丁、FrozenPatch、逐参考原日志、安装／测试／实际退出及两层清理已根核，55原件SHA／大小一致，独立报告无阻断。

同R12固定Ninja-only镜像的真实Claude Code2.1.205／UID54321运行两条公开工具命令，原base与源码导入、Ninja/CMake/CTest可执行及清理成立，34原件SHA／大小已核。该显式actor override不会把正式source rollout自动改成派生镜像；GPU须在实际入口明确绑定并核同一固定config ID。工具命令不代表完整solver交付或所有工程功能通过。

[CPU验收及根审处置](cpu_acceptance_r12_20261003_v1.json)保留资源范围限制；声明配额与actor实测不能补写为三个正式grader的完整资源实测。[公开brief v2](solver_brief_20261003_v2.md)区分Ninja分发包版本和binary版本串，干净读者及delta核查完成。两模型实际首请求分别核到完整原issue＋该brief，prompt原字节相同；code7／code8和profile端点差异保留。

[固定探针请求](probe_request_20261003_r12_v1.json)与总账维护交接；[结果清单](result_manifest.json)区分私有草案诊断、正式CPU及模型阶段。[Coder首臂七维分析](probe_coder_a1_analysis_20261003.md)已核145原件SHA／大小及完整候选到FrozenPatch字节。生产补丁正确选择Ninja Multi-Config的默认test目标，保留配置传递；可信CTest真实执行Release。非作者语义报告无生产阻断，另有非阻断P2：模型自测只复制表达式，无关pytest为1失败／78通过／2跳过且非零被掩盖，不能把它当作目标修复验证通过。[Qwen七维](probe_qwen36_a1_analysis_20261003.md)亦已核183原件与完整候选，新增公开八例是run录制自测；旧helper广测4失败／62通过／7skip及最终49分母错误保留。Qwen外部null preset条件回归记非阻断P2，当前标准生成器为字符串，不扩大任意输入兼容结论。两臂无需本轮材料修订／CPU重跑或普通追加采样，首轮交接已收口。

GPU固定版本的consumer要求原派生config ID。只读Docker save／gzip导出已在统一prepare槽安全结束，archive SHA／大小及原ID已直接交付GPU线程；原探针请求和CPU矩阵保持不变。GPU第三次续传后已核全量1,107,750,568字节及原archive SHA，并实际load成功、config ID一致；前两次失败partial保留。这一项不再依赖CPU源机保留archive；现有源原件不在本次删除。见[供应读回](gpu_fixed_image_supply_readback_20261003_v1.json)，其“求解未开始”是供应检查点的历史状态；本轮Coder真实运行与结果另见上方分析。供应完成与单次模型成功均不能判定整机可退租。
