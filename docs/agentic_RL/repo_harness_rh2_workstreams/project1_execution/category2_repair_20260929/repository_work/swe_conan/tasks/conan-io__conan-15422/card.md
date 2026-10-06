# Conan 15422 当前题卡

2026-10-03。**R12材料v2正式CPU与两份独立复核保持；[两模型首次分析](probe_pair_analysis_20261003.md)已核收并ACK／清活动指针。Qwen3.6 raw1／5F40P共45参考全过；Coder raw0／4F40P通过，默认jobs缺键是有效P1候选遗漏。两臂七维与语义／执行独审完成，没有当前材料误拒。**

v1私有诊断发现Qwen3.6 a2字段正确但实际CMake3.23.5拒读。当前[材料v2](materials/v2/revision_plan.json)在原jobs2／7节点中加入真实configure＋build，保留5F／40P和合理的gold／Coder a2／DeepSeek a4接受范围。私有v2矩阵与两位非作者材料／语义核查可以复用，不能代替当前正式全补丁回放。

正式作业`conan15422-formal-matrix-r12-20261003-v2`保留各原完整候选中的README、非官方测试、脚本及官方测试改动，核实际可信投影。旧“改测试自动0”不用于本次判定。v1误用宿主Python，在候选评分前缺依赖退出，失败原件保留；v2使用固定runtime和新目录。

R12实际Claude Code actor使用固定CMake3.23.5派生镜像，UID54321、source导入、CMake／CTest3.23.5及Conan CLI可执行；入口SHA与登记配方相同。34原件及清理已核，这是工具与权限证据。本次Coder另已核完整原issue＋brief首gateway交付与实际actor／grader同一固定config ID，不把旧actor检查替代模型求解证据。

120原件SHA／大小、八份原完整候选与Frozen内容／控制面投影、360参考状态、安装／退出／双层清理已根核及独立复核。45参考每轮均有完整raw状态且无skip；三个非参考平台skip通过原日志源行／原因和可信测试函数映射确认，没有冒称日志直接打印完整skip节点。DS a4官方测试改动被控制面投影排除但reward仍为1；非官方测试、README和脚本完整保留。

[首次七维分析](probe_coder_a1_analysis_20261003.md)已核157原件和本次完整三路径FP／实际投影。Coder起初调用默认`build_jobs()`，后来为通过自己错误的“无显式配置便省略”测试加了guard，最终只有显式配置时才写jobs。默认可信节点因缺键失败，尚未比较CPU数值，不是核数不一致或CMake版本误拒。显式2／7的真实configure＋build、Multi-Config及40原P均通过；三个平台skip是非参考。记P1候选默认遗漏及P2验证陈述过宽，原raw0保持，没有材料／下一模型阻断。

[固定探针请求](probe_request_20261003_r12_v1.json) `swe-conan15422-r12-briefv1-20261003-v1`两模型各首次一次齐，总回执及题主完整核收完成；总账returned已ACK，phase closeout、活动指针已清。Qwen无条件调用公开build_jobs，默认、显式和Multi-Config行为正确；正式投影只保留生产、排除其新增官方测试。实际默认继承preset的C++构建／运行已验；另一jobs8脚本只读JSON，广测八error的根因及最终披露不足记非阻断P2，详见[Qwen七维](probe_qwen36_a1_analysis_20261003.md)。显式2／7可信参考用project NONE，只证明CMake接受configure／build presets，不证明源码编译吞吐。旧Qwen configure拒绝与Coder原raw0保留，不按schema数字判负。无CPU／GPU作业在途；未来具体修订再评估，普通追加采样按覆盖优先暂缓，训练资格未建立，见[结果清单](result_manifest.json)。

固定actor／grader镜像的只读archive已与13403镜像一起导出并交GPU线程，SHA／大小／原config ID均已留证。本次实际模型臂已使用15422原config ID；这不代表含13403的两镜像供应整体已核销。供应未重建镜像、重跑CPU测试或修改已提交请求。
