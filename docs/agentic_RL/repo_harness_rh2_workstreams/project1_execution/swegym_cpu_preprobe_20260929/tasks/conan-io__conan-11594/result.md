# Conan11594：Ninja修复后的最终 CPU 结果

2026-09-29，`ninja-v1`。**只补Ninja后公开actor能复现目标缺陷；正式 noop=0、gold=1、丢失配置的退化=1。退化将请求的Release测试变成Debug执行而实际失败，来源mock测试却全部通过，确认S1评分覆盖缺口。** 题主已读回完整原件；[跨包独立复核](../../reviews/conan11594_result_review.md)及最终题卡对齐已完成，root冻结parser（显式bindings）和传输对账已完成。当前用于环境和评分覆盖诊断，不授予无条件正确性比较或训练资格。历史partial保留。

版本顺序为：原`mixed-v1`在configure因缺Ninja而停，不能算目标复现；随后`ninja_inventory_v1`只读确认标准路径/PATH/pip均无Ninja，apt installed为空，CMake3.22.1可用；最后`ninja-v1`新增依赖层并复验。旧输入、日志和来源参考不回写，原actor未重跑。

## 实际恢复与公开actor

[恢复原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1/dependency_build) 记录PyPI ninja1.10.2.4兼容wheel：`ninja-1.10.2.4-py2.py3-none-manylinux_2_5_x86_64.manylinux1_x86_64.whl`，120,718 bytes，SHA256 `327c319176c5a4af21908b727b776e9f5caf275680403da632821ba071fd6296`。已在本地核metadata原件SHA及该条目的文件名/直下URL/大小/hash与receipt一致；wheel字节未同步，本地未重算wheel文件。远端脚本先对下载字节校验后才构建，构建日志确认offline `--no-index --no-deps`仅安装Ninja。

派生image `97eb7ca6700c1ee0e789fdfdffe69587f7d6e35d3b22e7215cb96e2f17e781d0` 的15层前13层与immutable原image相同；新增COPY和安装两层。CMake前后均`/usr/bin/cmake` 3.22.1，文件SHA `fd22547781b64bb2db04370970b93db1f3fada1e41e60873b015ee0747009fc0`、模式、实际路径及版本输出完全一致。Ninja实际版本为`1.10.2.git.kitware.jobserver-1`，保留原suffix。没有采用Conan15422或apt1.10.1配方。三个读取/下载容器的query rc0且无remaining；rm回报No such container因`--rm`已移除，清理结论依据随后实际查询为空。

[actor原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1/actor_revised) 仍使用原public_commands清单（本地逐项相等）。CC2.1.205，UID54321，Python3.10.14 testbed解释器、`/testbed/conan`及`/testbed/conans`源码导入；base `4ed1bee0fb81b2826208e8c1c824c99fb6d69be8`。开始/结束git status均0行，agent进程0；prelaunch与activation无violation，4条Bash完成。

| 公开命令 | 结果 | 归因 |
| --- | --- | --- |
| identity | rc0 | 身份、base与源码来源成立 |
| toolchain | rc0 | CMake3.22.1、Ninja实际版本及Multi-Config generator可用 |
| real_cmake | rc1 | configure/generate完成后，`cmake --build ... --config Release --target RUN_TESTS`遇unknown target；已到目标缺陷 |
| public_existing | rc0 | 4 passed、1 imp弃用warning，无skip/import/collection失败 |

容器、网络、relay、stub清理均确认，无残留。真实actor消息仍为Devcheck控制文本；不能据此证明正式题面/public_hints交付或自主模型修题。

## 私有行为与实际补丁

[私有原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1/private_behavior) 使用同一派生image，但为root行为检查，不替代actor权限。三变体准备逐步成功；gold/退化均先check再实际apply并校验完整源码SHA。base `461786181aa4a64467e6eb2e87e5f41f0b3bc1d6cc9a18ce53efc407c288c1e4`，gold `cdaa63180dac106f736603cd63ef2c4eb307b9ad374ca127df34f6b86f7d20bf`，退化 `052f0805959b19c186fcd9536a998ea6e847b7ce1639dbcec24fd5fe5ce96118`。

| 变体 | 实际行为 |
| --- | --- |
| base | configure成功，RUN_TESTS未知target，rc1 |
| gold | 保留`--config Release`且使用`test`目标；CTest的release_behavior通过，marker内容断言通过，打印REAL_CMAKE_TEST_EXECUTED_RELEASE，rc0 |
| drop_config | `test`目标可运行但缺`--config`；日志真实显示`CMakeFiles/Debug/test.util`及`ctest ... -C Debug`，release_behavior失败，rc1 |

退化失败不是缺Ninja、安装或采集故障。原件未另导出CTest的LastTest.log，因此不虚构其内部错误文本；日志中的Debug命令、单项失败及公开命令内Release断言已能归因。三个容器rm/query均0且remaining为空。当前未把私有行为结果直接当正式评分或资格。

## 正式日志、参考绑定与实际源码

[正式三组原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/conan-io__conan-11594/ninja-v1) 均使用上述派生image、原安装和来源测试。实际安装依次执行 `python -m pip install -r conans/requirements.txt`、`conans/requirements_server.txt`、`conans/requirements_dev.txt`；每组安装rc0、failed_commands为空，未跳过。Python2条件包被环境marker排除是正常选择，不是测试skip。测试实际执行 `pytest -n0 -rA conans/test/unittests/tools/cmake/test_cmake_test.py`，完整段及rc标记均在；三组都从`/testbed/conans/__init__.py`导入1.51.0-dev，runner digest前后相同。

| 完整参数节点 / 结果 | noop | gold | drop_config |
| --- | --- | --- | --- |
| `Ninja Makefiles-test` | PASSED | PASSED | PASSED |
| `Ninja Multi-Config-test` | FAILED | PASSED | PASSED |
| `NMake Makefiles-test` | PASSED | PASSED | PASSED |
| `Unix Makefiles-test` | PASSED | PASSED | PASSED |
| `Visual Studio 14 2015-RUN_TESTS` | PASSED | PASSED | PASSED |
| `Xcode-RUN_TESTS` | PASSED | PASSED | PASSED |
| 正式 F2P / P2P | 0/1；4/4 | 1/1；4/4 | 1/1；4/4 |
| reward / test rc | 0 / 1 | 1 / 0 | 1 / 0 |
| 安装 / 测试段秒数 | 2.067 / 1.130 | 2.186 / 1.009 | 2.619 / 1.142 |

完整nodeid前缀为 `conans/test/unittests/tools/cmake/test_cmake_test.py::test_run_tests[`，表内参数末尾接`]`。三份完整原日志合计18个状态，noop为1 failed/5 passed，gold和退化均6 passed；各有1个ref.py无效转义弃用warning，无import/collection failure或skip。noop失败断言显示正确期望test、实际RUN_TESTS，确为目标错误。

来源grading.json因空格截断只含1 F2P与4 P2P，不应说是5个实际测试。[既有显式binding](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/conan-io__conan-11594/private/reference_bindings.json) 将截断的`test_run_tests[Ninja`绑定两个完整Ninja节点，要求全部通过；任一成员失败则该参考失败。三次实际grade argv显式传`--bindings`，`recipe/reference_bindings.json`与输入task entry一致，原始audit逐成员为noop PASS/FAIL、gold及退化PASS/PASS，revised parser标注`+reference-bindings-v1`。其余4个P2P截断键各自唯一对应表中完整节点。故18个原始状态折合15个来源参考状态，全部可追回，无缺席；退化满分不是碰撞末值造成。

每份candidate.patch和输入字节一致；解码frozen_patch完整源码SHA与上述私有实际apply后值一致。gold只改Ninja目标选择；退化除正确目标选择外，在`_build`中对Ninja Multi-Config清空build_config。两者只投影`conan/tools/cmake/cmake.py`（mode100644），excluded_pathset_changed=false；noop entries为空。三份eval.log完整SHA与ledger匹配，机器记录保存完整值。不能只凭git apply退出0或调度脚本状态确认实际候选。

candidate容器每次removed=true；从原始grade log最终JSON核manager_close，与checked receipt相同：created=removed=1、containers_open/supply_open/cleanup_failures均为空，最终exit0。两层清理确认，安装、日志、投影均未形成无效0/1的证据。

## 公开依据与覆盖缺口

[公开原题](../../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-11594/user_prompt.txt) 要求在Ninja Multi-Config下`cmake.test()`能执行，原失败命令明确使用`--config Release`。[公开base](../../../../../../../runs/swegym_quality_expansion_20260925/public/conan-io__conan-11594/base/conan/tools/cmake/cmake.py) 的CMake类文档说明multi-config构建传`--config Release`，`_build`由请求/设置的build_type形成该参数，`test`沿用此路径。因此换对test目标而丢弃Release是相关核心行为回归，不是强迫使用gold的某个内部写法。

[来源test.patch](../../../../../../../runs/swegym_quality_expansion_20260925/private/conan-io__conan-11594/test.patch) 的六种generator均用ConanFileMock，只断言目标名出现在命令中；虽然settings设为Release，却不断言`--config`，也不执行CTest。drop_config保留正确目标所以六项通过，而私有同一导出源码真实运行时走`ctest -C Debug`，Release行为失败。绑定已正确处理两个Ninja成员，补绑定不能补上这个语义断言缺口。

行为探针是`project(... NONE)`下一个真实CTest，既避免无关编译依赖，也明确检验公开场景中的build_type；gold通过并读取marker，退化实际失败。它不证明编译器矩阵、全部平台/targets或任意CMake版本；本结论以保留CMake3.22.1与Ninja `1.10.2.git.kitware.jobserver-1`的这次CPU运行成立。

## 资源、用途与剩余项

三次正式预算均2 CPU / 4 GiB，setup/reset诊断上限900秒（原300）、test仍1800秒、whole1800秒。trusted_setup依次75.944、76.791、76.161秒；ledger内存峰值分别352.527、352.164、352.047 MiB，resource_facts均null。峰值包含准备，不能当测试独占需求；本卡未从完整cgroup事件证明全程无OOM/PID拒绝。公开命令中自动生成`-j38`来自宿主CPU可见性，实际容器CPU配额仍2，且此探针没有真实编译负载；不据此推定38核成本。

当前允许环境/评分覆盖诊断，原始reward保留。D6未处理前，不把这个1分当完整正确性或训练奖励；若后续采用受限比较，应另行明确相同Release行为后检和预登记。[独立复核](../../reviews/conan11594_result_review.md)、[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/conan11594_final_v1.json)及[传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_conan11594_v1.json)已完成（本题134份已结束证据、1,517,020字节远端／本地SHA一致；环境31条已包含，不重复计数）；全pip_check、wheel本地字节重hash、完整资源事件未在本轮证明。正式题面/public_hints真实交付、自主模型、模型/GPU/预算/训练资格仍独立管理。本轮未修改正式测试、评分或输入，也未执行远端。

[最终机器结果与证据SHA](result.json) 保存恢复、actor/private、实际导出、18个完整测试状态及15个绑定参考状态、安装、日志与清理。历史[result_partial.md](result_partial.md)和JSON保留当时范围。
