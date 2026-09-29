# Conan11594：Ninja修复后开发与私有行为结果

2026-09-29，`ninja-v1`。**只补Ninja后，真实actor已到达原目标RUN_TESTS错误；私有gold真实执行Release测试并验marker，丢失配置的退化实际运行Debug并失败。** 本记录只接受actor/private已核证据；虽然同步status已记录正式分数，正式完整日志、实际导出、绑定/逐参考尚未在本卡核验，不提前确认最终评分。此前`mixed-v1`缺Ninja造成的configure失败保留为环境失败，不算目标复现。

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

后续只需接续正式完整证据与独立复核，不重复本次已完成actor/private。全pip_check和完整资源观测未在本卡证明，模型/GPU/预算/训练仍另行管理。[机器记录与原件SHA](result_partial.json) 固定本次已核范围；本轮没有执行项目、操作远端或修改旧输入。
