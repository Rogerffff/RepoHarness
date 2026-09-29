# Conan11594 完整 CPU 结果独立复核

2026-09-29，ninja-v1。跨包独立核验，复用已完成的 [Ninja 环境窄审](conan_ninja_environment_review.md)，不是新盲审。先读公开命令、私有与正式原件，再对照 root 冻结 parser 重放，最后读题主 result_partial；不执行项目、容器或远端，不改生产、输入、测试或评分。

**正式 noop=0、gold=1、degenerate_drop_config=1；确认 S1 评分覆盖不足。** 退化虽改对 `test` target，却删掉 Ninja Multi-Config 的构建配置，真实运行 Debug 而非请求的 Release；gold 保留 Release、真实执行 CTest 并验证 marker。两者正式均通过全部六个测试，缺口是正式测试只检查 target 字符串。参考绑定、实际候选源码、安装／测试收口与两层清理均核实，不能用 status 汇总替代这些证据。

## 公开需求与实际行为

[题面](../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-11594/user_prompt.txt) 原始日志明确在 `--config Release` 下调用 cmake.test()，要求 Ninja Multi-Config 使用 `test` 而非 RUN_TESTS。公开 base 的 [cmake.py](../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-11594/base/conan/tools/cmake/cmake.py) `_build` 从参数或 settings.build_type 取得配置，在 multi-config 时传 `--config`，`test` 继续传递 build_type。因此“请求 Release 时不能悄然跑 Debug”来自题面示例和原有配置传递契约，不是因为 gold 碰巧通过新增断言才变成需求；也不是要求所有配置都固定 Release。

[public_commands.json](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/conan-io__conan-11594/public_commands.json) 的 real_cmake 建立无编译语言的 CMake 项目，显式安装 `-s build_type=Release` 与 Ninja Multi-Config；唯一 CTest 检查 `$<CONFIG>` 为 Release 才写 marker，Python 随后读回内容再打印 `REAL_CMAKE_TEST_EXECUTED_RELEASE`。私有 behavior_commands 的 cmd 与该公开命令完全相同，只改变外层 expect 为 any；本次依据完整输出归因，没有将 any/rc1 本身当验证通过。

[private_behavior](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1/private_behavior) 三方均在同一派生 image `97eb7ca6700c1ee0e789fdfdffe69587f7d6e35d3b22e7215cb96e2f17e781d0`、同一 base、uid 0 下运行。准备先核 base 文件，候选 apply-check、apply、应用后 SHA 都 rc0；每个行为命令约 2 秒完成，没有超时或导入／安装失败。

| 变体 | 真实 CMake／CTest 行为 | 命令 rc |
| --- | --- | --- |
| base | configure/generate 完成；保留 --config Release，但 RUN_TESTS 未知 | 1 |
| gold | --config Release、target=test；release_behavior 1/1 通过，marker 读回后打印成功标记 | 0 |
| drop_config | target=test，但无 --config；实际 CMakeFiles/Debug/test.util 调用 ctest -C Debug，release_behavior 0/1 通过 | 1 |

退化不是“不执行测试”：它确实执行了错误配置的测试。失败全文包含 Debug test.util 和 ctest -C Debug；未另保存 LastTest.log，不虚构其内部 `Expected Release` 报错已经被读到。Gold 成功标记位于 marker 内容断言之后，因而可以确认实际 Release 测试和 marker 验证完成。Base／退化在 TestClient.build 异常退出，未到 marker 读取；不把未到达断言补记为已执行。

## 实际补丁与正式投影

对本地公开 base 逐行应用输入补丁文本，再解码正式 artifacts/frozen_patch.json 的 content_b64，比较整个文件；只做文本计算，未 import 或执行 Conan。Gold／退化 candidate.patch 与对应输入补丁逐字节相等，全文件冻结字节与重建结果相同：

| 变体 | patch SHA256 | cmake.py SHA256／bytes |
| --- | --- | --- |
| base | 无 | 461786181aa4a64467e6eb2e87e5f41f0b3bc1d6cc9a18ce53efc407c288c1e4 |
| gold | e49265e4fd430f627dd2293f1f79b3b6c30b30d36c8a6a066c992f4d4b48abfa | cdaa63180dac106f736603cd63ef2c4eb307b9ad374ca127df34f6b86f7d20bf／6,854 |
| drop_config | f4445e51d087748cf00cd647bcf2ddf13a592c1be343561ad6956a367ef408e1 | 052f0805959b19c186fcd9536a998ea6e847b7ce1639dbcec24fd5fe5ce96118／6,904 |

私有 prep 输出的应用后文件 SHA 与正式冻结字节一致。Gold 仅为 Ninja 选择 test；退化还在 `_build` 中为 Ninja Multi-Config 清空 build_config。两者正式 included_paths 仅 conan/tools/cmake/cmake.py，noop 无投影改动；stage_error=null、apply_ok=true，没有测试／fixture 投影。Frozen materialized_head 为 `4ed1bee0fb81b2826208e8c1c824c99fb6d69be8`，image 与上述派生镜像一致。

## 安装、完整日志与 Conan 参考绑定

原件入口：[ninja-v1](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1)。三方正式安装均真实执行 `cython<3` 约束及 conans/requirements.txt、requirements_server.txt、requirements_dev.txt 三次 pip 安装；依赖已有满足，install_skipped=false、failed_commands=[]、install rc0。未冒称本题执行了 editable install：实际依靠 `/testbed/conans/__init__.py` 源码导入，版本为 1.51.0-dev。供应 null，runner digest 前后同为 `9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792`。

正式命令是 `pytest -n0 -rA conans/test/unittests/tools/cmake/test_cmake_test.py`，三方各 collected=6，测试段和 candidate 段均完整结束：

| 变体 | 安装秒 | 测试段秒／rc | pytest 完整结果 | reward |
| --- | --- | --- | --- | --- |
| noop | 2.067 | 1.130／1 | 1 failed, 5 passed, 1 warning | 0 |
| gold | 2.186 | 1.009／0 | 6 passed, 1 warning | 1 |
| drop_config | 2.619 | 1.142／0 | 6 passed, 1 warning | 1 |

唯一 noop 失败是 Ninja Multi-Config 的 target 字符串断言：期望 test、实际 RUN_TESTS，不是基础设施失败。Gold／退化全文没有失败被 parser 忽略，均实为六个测试全过。

本题不能将截短的 Ninja 参考键直接视为一个完整 node。输入 [reference_bindings.json](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/conan-io__conan-11594/private/reference_bindings.json) 把 `…::test_run_tests[Ninja` 绑定为 Ninja Makefiles-test 与 Ninja Multi-Config-test，要求二者全部通过。三个 grade/recipe/reference_bindings.json 都与输入的本题 tasks 子项完整相等；每次 reference.json 记录的 raw_node_states 与原始日志逐项一致：

| 完整 node 参数（共同前缀 conans/test/unittests/tools/cmake/test_cmake_test.py::test_run_tests） | noop | gold | drop_config |
| --- | --- | --- | --- |
| [Ninja Makefiles-test]（同一 F2P 绑定） | PASSED | PASSED | PASSED |
| [Ninja Multi-Config-test]（同一 F2P 绑定） | FAILED | PASSED | PASSED |
| [NMake Makefiles-test]（P2P） | PASSED | PASSED | PASSED |
| [Unix Makefiles-test]（P2P） | PASSED | PASSED | PASSED |
| [Visual Studio 14 2015-RUN_TESTS]（P2P） | PASSED | PASSED | PASSED |
| [Xcode-RUN_TESTS]（P2P） | PASSED | PASSED | PASSED |

因此 F2P 计数为 1 个来源参考，P2P 为 4；parser num_parsed_tests=5 不等于只执行了五测。三方共 18 个完整 node 状态已核；reference_missing/skipped=[]、num_parsed_outside_segment=0。已对照 root [冻结 parser 重放](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan11594_final_v1.json) 的逐参考结果；绑定前后在本次都得到 0/1/1，不能把误奖归咎于 Ninja 名称被截短或绑定规则遗漏失败。

三份完整 eval.log 独立重算 SHA 与 ledger 相符：noop `8ef3ddd3ceaa2edbbe64df740aea9e76ea88a53233acd28916b72d7f42e79d70`；gold `44dbac5fb92c89e06a014076d6c8c71c977e22719f4904f298ab2ae92fc3a5ed`；退化 `b6c14376fc11ac431fb79c3fd65c09bc5562e84f27a6573e25f6093d71f9ec61`。

## 清理、资源与结论范围

私有三容器各自 rm/query rc0、remaining=[]。正式每次 ledger cleanup removed=true，再由 driver_close_checked 确认 manager created=removed=1、containers_open/supply_open/cleanup_failures=[]，无 aborted/halted、final_status exit_code0；这是逐评分容器和 manager 两层清理。工具下载／actor 清理已在环境窄审完成，本轮不重复实证。原始 status 已 finished_at、三次 grade 步骤 rc0，字段仍是 executed_pending_review；本结论来自原件，不把状态字段当自动接受。

三次准备阶段分别 75.944、76.791、76.161 秒，在本批 setup900 内完成；ledger mem_peak_mb 分别 352.527、352.164、352.047，resource_facts=null。本稿不据这些峰值宣称完整零 OOM／PID 事件，也不套用 MONAI 的内存压力数据。

**可确认的误奖范围**：在 Ninja Multi-Config、调用者请求 Release 的真实行为中，丢配置退化切换到 Debug，正式奖励仍为 1。正式 mock 测试设置了 Release，却仅断言 target；没有启动真实 CTest，也没有断言保留 --config。现有公开 real_cmake 命令已可作为最小验收草案：准确复现 base RUN_TESTS 错误、gold 实际 Release marker、退化实际 Debug 失败。后续可复用该公开依据控制接入 D6；本轮未改正式评分或测试，不扩大为任意 generator、配置或全仓兼容性证明。

先前最后读取题主 result_partial，actor/private 事实与本复核一致；最终卡落盘后，已追加窄对照 [result.md](../tasks/conan-io__conan-11594/result.md) 和 [result.json](../tasks/conan-io__conan-11594/result.json)：S1结论、0/1/1、Release／Debug行为、18个完整节点与15个来源参考、安装／清理及限制均一致，正式机器字段亦逐项匹配已验ledger。按root授权仅核销题卡独立复核／冻结parser／传输对账待办并填链接，不改主审事实。root已用显式bindings完成冻结parser重放；[传输manifest](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_conan11594_v1.json)记录本题134份已结束证据、1,517,020字节远端／本地SHA一致，包含环境31条，未重复计数；本复核引用root对账，不重做远端或资源采样。当前用途是环境修复与 S1 覆盖诊断；原评分未修不作为无条件训练合格题。D6 未实施、全环境 pip check／完整测试未做、wheel 二进制未本地重算、正式题面交付和自主模型／训练条件未验证，边界保留。
