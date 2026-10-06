# Conan 13403：GNU 环境与公开 actor 接续

2026-10-03，题主自查。**v3已完成真实baseline actor的GNU开发诊断。** 直接GNU调用成功，明确host/build profile的Conan install成功；原版Conan build实际进入Autotools.autoreconf，报configure.ac缺席。两条包装命令均RC0，原功能缺陷保留，未演示修后候选。两份非作者开发窄核已完成，当前范围无阻断；正式v4评分尚未发生。

原镜像actor v1发现autoreconf缺席；独立GNU层固定Autoconf2.71-2、Automake1:1.16.5-1.3、m4 1.4.18-5ubuntu2及两个必要依赖，核五个deb后离线安装。17件构建输入／输出SHA、下载容器实际退出0与清理已核。镜像实际config为`sha256:b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`。v2两个限额断网root容器核原／派生镜像960个Git跟踪文件、HEAD、干净工作树和完整pip freeze一致；freeze SHA为`db12cb8fcc4a16153a0c100d97788a2633ffd0e9a575d556572385d82aa2ed1d`。GNU层未正式登记。

v2实际GNU和原单测通过，但公开`conan build`漏传profile，在目标调用之前失败；52件SHA、39行轨迹、四请求与清理保留。v3只修这条公开命令的profile参数，沿同一image config／第五版／runtime_cpu_v2，新freshprepare及attempt，不重跑已过的旧单测。原v1/v2失败原件未回写。

v3 job为`conan13403-baseline-actor-r5-gnu-20261003-v3`，CC2.1.205／harness／外层退出0，实际UID54321、Python3.10.14、Conan2.1.0-dev从/testbed导入，固定HEAD `55163679ad1fa933f671ddf186e53b92bf39bbdb`。Autoconf2.71和Automake1.16.5可用；带configure.ac的build目录直接autoreconf RC0，Conan install RC0，原build CLI RC1且日志实际记录`RUN: autoreconf --force --install`与`autoreconf: error: 'configure.ac' is required`。从公开base的source-folder chdir逻辑与此recipe布局可归因原目录缺陷；日志没有单独打印cwd，不宣称独立cwd探针。包装RC0表示已完整观察预期原行为，不等于题目修好了。

release固定`cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`；837成员及可信48／216读回通过。v3的34件输入、prepared与回传原件SHA一致；30行JSON轨迹和三次messages请求完整，activation ok。捕获的3118字节GNU输出完整，但CC tool_result按既有devcheck只回显1500字节尾部，不声称actor看过完整stdout。容器删除／stub退出均0，网络／relay失败与最终残留均空。两个泛用marker为false，不宣称全部权限项通过。

本次使用受控devcheck提示，不是完整issue/hints交付、模型求解、正式评分或训练资格。GNU工具与原缺陷路径已有解释；正式v4替换、受信配方、完整候选矩阵及非作者题级CPU核查仍待发布。

忽略原件入口`runs/category2_repair_20260929/conan_cpu_20261003/`：`image_prepare_13403_gnu_v2_audit.json`、`baseline_actor_13403_r5_gnu_v2_audit.json`、`baseline_actor_13403_r5_gnu_v3_evidence/baseline_actor_13403_r5_gnu_v3/`、`baseline_actor_13403_r5_gnu_v3_remote_audit.json`与`baseline_actor_13403_r5_gnu_v3_audit.json`。旧失败及云端v4原字节全部保留。

## 独立开发核查

[运行证据核查](../../reviews/non_author_13403_gnu_actor_runtime_review_20261003.md)与[范围反证核查](../../reviews/non_author_13403_gnu_actor_scope_review_20261003.md)均已完成，配置为GPT-6.1 Sol／high。题主另核103件回传文件SHA与大小，以及公开源码目录切换链、完整GNU输出和fixture解析。范围审查初版把JSON转义误读为字面反斜杠n，已由审查者更正：configure.ac为3个实际换行，marker为1个实际换行，均无字面反斜杠n；无需改材料或重跑。

两份报告仅收口固定环境下的baseline开发诊断。现有配方及v3可复用，不扩大环境、不重复旧单测或41项历史诊断。Git跟踪源码内容与Python版本清单一致；未逐文件核全部Python包或OS。完整solver输入、正确修法、正式环境登记与cloud-v4题级评分仍待后续。报告当前SHA与主审查处置见[result_manifest.json](result_manifest.json)。
