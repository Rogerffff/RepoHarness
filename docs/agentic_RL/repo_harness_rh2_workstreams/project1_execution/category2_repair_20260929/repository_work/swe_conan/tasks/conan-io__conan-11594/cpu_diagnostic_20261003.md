# Conan 11594：新机私有草案诊断

2026-10-03，题主自查。新增Release marker已在cpu-a实际执行，原六个参数化case保留。正式consumer、受信缺席文件登记和正式reward仍待共用发布；本记录不授予训练资格。

| 候选 | pytest退出码 | 七个实际节点 | 来源F2P通过／总数 | 来源P2P通过／总数 |
| --- | --- | --- | --- | --- |
| gold | 0 | 7通过 | 2／2 | 4／4 |
| noop | 1 | 2失败、5通过 | 0／2 | 4／4 |
| drop_config | 1 | 1失败、6通过 | 1／2 | 4／4 |

noop原Ninja Multi-Config目标仍错误地为`RUN_TESTS`，真实CLI报unknown target。drop_config虽选择`test`，却遗漏请求的Release配置；日志明确执行`ctest --force-new-ctest-process -C Debug`，新增CTest断言失败。gold的测试通过包含实际CTest和Release marker检查，不只核命令字符串。正常warning为旧源码的invalid escape及imp弃用，无ERROR、跳过或缺席节点。

原来源键`test_run_tests[Ninja`仍按`reference-bindings-v1`绑定两个完整节点并要求ALL通过；参数节点含空格，按整行读取，未用空白切分截断。六个来源参考对应七个实际节点。这里聚合用于题主诊断，仍须在正式consumer核同一规则。

环境恢复严格沿已有Ninja-only Dockerfile：wheel SHA `327c319176c5a4af21908b727b776e9f5caf275680403da632821ba071fd6296`、120718字节；原镜像config ID `sha256:292bf28a71ae6e3b9c52dcb25ed28020bf0c2ff90fc47a6c0761720b89c1f516`。新派生镜像ID `sha256:f3b8d6671607e167fa549c05faa860345e5256c8f834a6a711447df9dce6839f`；运行核CMake3.22.1、Ninja CLI `1.10.2.git.kitware.jobserver-1`与distribution1.10.2.4，解释器位于testbed环境，Conan导入来自`/testbed`。

作业`conan11594-draft-diagnostic-20261003-v3`统一领取CPU槽，外层RC0。此前v1/v2均RC75未启动，属于名额拥挤而非题目失败。三方串行、2CPU／4GiB、network none，原`private_behavior.py`未改；基线HEAD、测试文件缺席、补丁应用及测试／实现文件SHA均逐方核过。删除RC与残留查询RC均0，remaining为空；49件输入及回传文件SHA一致，21条实际节点状态完整。

范围：UID0私有草案诊断；没有重新运行来源安装前缀，没有在本作业运行actor、FrozenPatch或正式grader。历史actor/真实Release与Debug诊断按身份保留；新基线与正式评分使用届时已冻结的共用release及runtime_cpu_v2，不把旧FrozenPatch改摘要重绑。

原件位于忽略目录`runs/category2_repair_20260929/conan_cpu_20261003/`：

- `diagnostic_11594_v1/`：冻结草案、候选、绑定、spec及原runner。
- `diagnostic_evidence_11594_v1/output/`：逐方完整identity、collection、pytest与summary。
- `diagnostic_11594_v1_remote_audit.json`：49件SHA及远端作业收尾。
- `diagnostic_audit_11594_v1.json`：逐完整节点及来源聚合；formal_cpu_acceptance为null。
- `image_evidence_11594_ninja_v1_complete/`：完整历史配方重建输入、wheel、日志与receipt，另核11件SHA。

停止条件：私有新断言已区分既有假阳性，暂不扩大矩阵；正式发布后验0／1／0及受信缺席／绑定消费，再核影响范围内的非作者CPU结果。没有修改公开题面或提示，不因纯私有测试变化重做公开读者。
