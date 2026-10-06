# Conan 六题：当前执行入口

2026-10-03。题主：**SWE | Conan 题目修订**，线程 `01a0fd61-bd33-7553-8a0e-cba65444cfb6`。

**六题均已正式发布，正式CPU与非作者验收保持；12／12首轮模型臂的题主七维和语义／执行独审已完成，6／6双模型总回执已核收、ACK并清活动指针。** 11臂raw1；15422 Coder raw0是有效的默认jobs候选遗漏，非材料误拒，该题Qwen raw1不能核销Coder失败。当前未发现须再改题目的阻断，验证方法及陈述问题逐题保留；本包无CPU／GPU作业在途，普通追加采样按覆盖优先暂缓，训练／留出资格未建立。

11594、13403、15422固定actor／grader镜像的只读archive已导出并交付。11594已在GPU全量核验并load同一ID，本项不再依赖CPU源archive；13403及15422已核各自两模型实际actor／grader使用同一原ID，不据此核销两镜像archive的全量供应／清理。当前本包无CPU作业在途；未来具体修订再核CPU／GPU需求；题级无在途不等于跨包镜像供应或整机退租可自动核销，整批资源操作服从现行授权。题级进度和活动请求由 `category2_task_board.py` 写总账，发布与GPU直接返回题主。

| 题目 | 当前有效材料与范围 | 当前证据与下一步 |
| --- | --- | --- |
| [11594](tasks/conan-io__conan-11594/card.md) | 保留 generator cases、新增真实 CTest Release；原 Ninja 参考固定 ALL 绑定两个完整节点；Ninja1.10.2.4／CMake3.22.1 | R12正式CPU及两非作者完成；[两模型首轮](tasks/conan-io__conan-11594/probe_pair_analysis_20261003.md)均raw1／2F4P六逻辑七节点，语义／执行独审已核收，ACK／清指针；Qwen null preset条件P2与自测失败分母保留 |
| [12397](tasks/conan-io__conan-12397/card.md) | Apple 完整 cpp 键与 Linux 节点，2F／2P；保持来源镜像及 vendor 安装 | R12正式CPU与两非作者保持；[两模型首轮](tasks/conan-io__conan-12397/probe_pair_analysis_20261003.md)均raw1四参考全过，生产内容相同、配置生成成立，独审已核收／ACK／清指针；实际链接未验，自测失败和选测范围P2保留 |
| [13230](tasks/conan-io__conan-13230/card.md) | Android 及34旧参考保留，新增 Linux 无SDK／SDK哨兵两节点，3F／34P | R11正式CPU保持；[两模型首轮](tasks/conan-io__conan-13230/probe_pair_analysis_20261003.md)均raw1／37参考全过，七维及语义／执行审无阻断；host判断修复成立，两P2限定Coder自测；总回执已核收、活动指针已清，训练资格未建立 |
| [13403](tasks/conan-io__conan-13403/card.md) | 云端 v4 原字节，1F／0P；固定 GNU 环境层 | [两模型首轮](tasks/conan-io__conan-13403/probe_pair_analysis_20261003.md)均raw1，所选目录／args／异常／cwd正确，七维及两独审已核收／ACK／清指针；参考为受控调用，Qwen79单测含1新mock例，Coder自测无调用／GNU功能失败／错误示例及Qwen管道P2保留 |
| [14177](tasks/conan-io__conan-14177/card.md) | 云端 v2；单补丁描述移入P2P，2F／11P，原13节点保留；brief v2 | R11正式CPU保持；旧误拒安全取消。[两模型首轮](tasks/conan-io__conan-14177/probe_pair_analysis_20261003.md)均raw1／13参考全过，两臂完整brief交付、七维及独审已核收／ACK／清指针；Qwen无新finding，mock范围与Coder demo观察误述P2保持 |
| [15422](tasks/conan-io__conan-15422/card.md) | 最新 v2，5F／40P；同进程默认／2／7与Multi-Config；固定CMake3.23.5 | R12正式八完整候选保持；[两模型首轮](tasks/conan-io__conan-15422/probe_pair_analysis_20261003.md)已核收／ACK／清指针，Coder raw0默认缺键P1、Qwen raw1／45参考全过；Qwen实际继承preset C++构建通过，另JSON-only脚本和广测八error边界／P2保留 |

R11为 `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`，980成员及可信48R2E／216SWE读回；13230、14177已验收版本保持不变。R12为 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`，1020成员及相同可信数量读回；余四题发布回执SHA已核、已ack并清活动publish指针。发布者的维护／prepare检查不算题目CPU验收。四题R12正式actor默认仍source；GNU／Ninja／CMake派生评分镜像发布也不算actor验收，后续普通探针须明确绑定和验证其固定actor环境。

## 证据与边界

- [13230正式CPU及根审处置](tasks/conan-io__conan-13230/cpu_acceptance_r11_20261003_v1.json)：完整正式消费、逐参考、原完整补丁到FrozenPatch内容、安装／测试／退出／两层清理及两份独立报告。声明配额不冒称逐容器CPU容量实测；旧脚本actor不代表真实solver交付或求解。
- [正式输入准备](formal_cpu_preparation_20261003.md)：六题54个入口，48份完整原补丁SHA、隔离应用及AST检查。它是输入完整性证据；每题是否运行看逐题结果，不据静态预检声称CPU通过。
- [六题静态检查](static_checks.json) 与各题 `revision_plan.json`：准备记录，非生产registry。15422当前材料在 `materials/v2/`，不再用旧snippet生成v1。
- [最初非作者材料核查](reviews/non_author_material_review_20261003.md)：适用原四份草案；15422 v2另有[运行](reviews/non_author_15422_v2_runtime_review_20261003.md)及[语义](reviews/non_author_15422_v2_semantic_review_20261003.md)报告。旧语义有效范围复用，不因发布全套重审。
- 13403／14177的历史日志完整性、既有运行、诊断失败与修订依据保存在各题原记录；不重跑41／15项历史诊断，也不回写历史reward。13403录制器不是GNU执行；v3实际GNU诊断的异常归因与尾部输出限制见[actor记录](tasks/conan-io__conan-13403/actor_resume_20261003.md)。
- 15422旧私有诊断只应用`presets.py`投影。正式矩阵应用原完整候选，保留README、非官方测试、脚本及官方测试改动；按当前FA可信投影核实际接受与剔除，不能沿legacy“改测试自动0”规则判定。Qwen3.6 a2由实际CMake3.23.5 configure拒绝，两个显式节点未到build，不按schema或最低版本数字拒绝。DS a4及Coder a2替代接受范围保留。

## 公开输入与探针

13230当前[brief v2](tasks/conan-io__conan-13230/solver_brief_20261003_v2.md)已由[干净读者](reviews/non_author_r11_public_reader_20261003.md)及[增量核查](reviews/non_author_r11_public_reader_v2_delta_20261003.md)核对。14177原brief v1的公开文件名触发code7误报，已另版brief v2并由[新干净读者](reviews/non_author_14177_brief_v2_fresh_public_reader_20261003.md)核查；真实本地load_inputs通过，旧请求已安全关闭核收。新版两模型均已核实际完整首请求交付与公开目录筛选运行，并完成各自语义／执行独审核收；Qwen重复同13旧例的范围不扩大。11594当前brief v2另有[版本说明delta](reviews/non_author_r12_public_reader_11594_v2_delta_20261003.md)，余三题及11594初版brief v1由[干净公开读者](reviews/non_author_r12_public_reader_20261003.md)核对。所有brief保留原issue、替代旧generic hints中错误的全测试恢复断言，只提供中性开发说明；静态读者与当前首臂运行分别留证，不自动建立另一模型交付或更广工具能力。

[13230固定请求](tasks/conan-io__conan-13230/probe_request_20261003_r11_v1.json)按现行 `probe-wide-v1` 两模型各1次，CPU证据和私有材料只给宿主接收，不能整体挂给solver。GPU执行方自行冻结兼容版本并核实际镜像ID、原issue＋当前brief的完整首请求交付。探针原件回传后，本题主检查执行／评分运输和候选语义，分析修法、根因定位、纠错、工具、验证、真实并行机会与效率；环境和排队耗时单列，不新增未经校准总分。

每题两模型各一次只建立首波诊断，不下稳定成功率或总体模型排名结论。11594／12397／14177／15422两臂code7／8差异明确保留；13403两臂均code8且input／grading source manifest相同，模型transport／profile仍不同；13230既有code5／7消费范围另见原配对页。截断、infra、缺评分或缺模型保持待接续；正式训练／留出资格尚未建立。13230旧Qwen首臂“待Coder／执行审”字段保留为历史，当前配对页和结果清单汇合完整核收；不回写原证据。资源需求由逐题 `result_manifest.json` 维护，旧[暂停点](pause_checkpoint_20261003.md)为历史；已有恢复授权不重复请示。

固定派生镜像的GPU供应采用Docker save／load并核同一config ID，或由registry证明可pull完全相同ID。consumer登记身份是镜像ID，不能仅凭工具版本和recipe相同接受另一重建ID。11594、13403、15422的固定供应已在统一prepare槽结束并直接交付；供应另留只读archive与SHA证据，不改先前已提交请求、不重跑验收矩阵。

13403和15422原作业及owned cleanup／SHA审计均已安全结束，原件根核、两份独立复核及探针交接完成。两个v1宿主Python失败原件已保存，v2输入保持固定。恢复时先查已有请求与模型回执，不因本地会话结束重跑候选；镜像导出也已结束，当前本包无CPU作业在途。

## 执行纪律

本包使用cpu-a与统一两槽；gateway18190／stub18191。远端Docker／评分／actor／准备均经 `control/cpu_slot.py`，75为未启动，重试使用新job ID，不记候选负分。正式运行绑定已交付不可变release、fresh prepared与原完整候选；不改共享consumer、pins、control或在途代码。

`prepare_materials.py`是初始批次工具，运行／审查阶段不得覆盖已有题卡和证据。继续修订创建新材料版本并保留原件。各题卡与结果清单是当前事实入口；总账保存阶段、阻塞及交接；消息只用于发布／探针交接与具体输入或共享缺陷，不抄送常规进度。
