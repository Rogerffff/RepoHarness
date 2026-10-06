# Conan 12397 当前题卡

2026-10-03。R12正式CPU及两非作者保持；[两模型首轮](probe_pair_analysis_20261003.md)各一次均raw1，2F／2P四完整参考全过，生产内容相同、配置生成根因修复成立。两份七维与语义／执行独审已核收，总回执已ACK、活动指针已清；实际编译链接及训练资格未建立。

修订测试按完整键读取 Apple cross 和 Linux native 的 cpp 编译／链接参数，保留原参考并新增 Linux 参考，当前为2F／2P。[有效补丁](effective_test.patch)已在R12正式登记，不再只是草案。

正式 noop／gold／objcpp_only／apple_only = 0／1／0／0。68件原始文件的SHA与大小、16个参考状态、完整补丁到FrozenPatch、安装与实际退出、候选及评分容器清理已核。Linux参考独立拒绝只修Apple的候选，完整键解析拒绝objcpp后缀误命中。[CPU记录](cpu_acceptance_r12_20261003_v1.json)及两份非作者报告无当前阻断。

旧实际actor以UID54321生成Linux clang14／libc++配置，三项公开测试通过，见[actor记录](actor_resume_20261003.md)。本次Coder原issue与[公开brief v1](solver_brief_20261003_v1.md)完整首gateway交付和实际来源镜像身份已核；旧actor证据的有限范围保持。

Coder补足`cpp_link_args`的libc++选择，完整原候选的生产文件和公开新增测试均与Frozen内容相符；实际可信投影只保留生产文件，四参考无缺席／跳过。133原件SHA／大小、执行收尾与候选语义已核，详见[首次七维分析](probe_coder_a1_analysis_20261003.md)。验证仅建立配置生成及有限公开回归，未实际编译／链接；功能目录出现工具fixture错误，模型最终却称所有既有测试通过，记非阻断P2。没有发现当前材料缺陷。

固定请求为`swe-conan12397-r12-briefv1-20261003-v1`，按probe-wide-v1两模型各1次，见[探针输入](probe_request_20261003_r12_v1.json)。[Qwen七维](probe_qwen36_a1_analysis_20261003.md)已核158原件；改前／改后配置支持修复，功能setup、VS、GCC mock失败及compiler选测分母保留。两模型总回执已核收，不重复首波；覆盖优先暂缓普通追加采样。当前本题无CPU／GPU作业，未来具体修订再核需求，整批资源操作服从现行授权。本题尚未建立训练资格，见[结果清单](result_manifest.json)。
