# Conan15422 R12 正式 CPU：非作者范围窄核

日期：2026-10-03。角色：Falsifier／Simplifier。只核 v2 新增正式全补丁回放、实际拒绝点、Frozen／评分投影与当前 actor 工具证据；复用既有 v2 语义／运行审查，不重开旧全审。

## 结论与当前用途

**八份计划完整候选的正式结果核查通过：noop／gold／coder_a1／coder_a3／DSa1／DSa4boundary／codera2alt／Qwen36a2 = 0／1／0／0／0／1／1／0。** 45 个参考×8轮的360个实际状态与原日志、ledger、matrix_results 和 root audit 逐项相符，参考无 skip／missing。未发现实际新增 P0、P1 或 P2；最小修正：无需修改。无本轮范围阻断，停止。

Qwen 的两个显式节点被实际 CMake3.23.5 **configure** 拒读，不是固定 schema／最低版本数字 oracle；这两个节点没有执行到 build。DSa4 和 coder a2 两条不同合理实现仍通过。完整 Frozen 正式运输关闭了旧私有诊断只取 `presets.py` 的证据缺口；不代表所有新增脚本／非官方测试被执行。

本报告只给当前正式 CPU 切片结果及实际 actor 工具入口证据，不声明完整模型求解、真实首请求新 brief 已交付、全部生成器／平台消费、实际编译并发或训练资格。root audit 的 `ordinary_probe_ready=false`、`training_eligibility=not_established` 不由本轮改写。

## 360 个正式参考状态与实际拒绝点

完整 nodeid 前缀为 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py::`。五个 F2P 分别为：`test_presets_njobs`（原42）、`test_presets_jobs_default_matches_public_helper`、`test_presets_jobs_explicit_values[jobs2]`、同函数 `[jobs7]`、`test_presets_jobs_multiconfig_append_replace`。P／F 为 raw PASSED／FAILED。

| 正式完整候选 ID | 原42 | 默认 | jobs2 | jobs7 | 追加／替换 | P2P | reward／pytest rc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| noop | F | F | F | F | F | 40/40 P | 0／1 |
| gold | P | P | P | P | P | 40/40 P | 1／0 |
| coder_a1 | P | F | P | P | P | 40/40 P | 0／1 |
| coder_a3 | P | F | P | P | P | 40/40 P | 0／1 |
| deepseek_a1 | P | P | P | P | F | 40/40 P | 0／1 |
| deepseek_a4_generator_boundary | P | P | P | P | P | 40/40 P | 1／0 |
| coder_a2_alternative | P | P | P | P | P | 40/40 P | 1／0 |
| qwen36_a2_schema_diagnostic | P | P | F | F | P | 40/40 P | 0／1 |

八轮均实际收集48节点：45参考，加3非参考平台节点。每轮 ledger 只有1次正式结果，驱动及测试段 exec rc均为0，测试段完成；测试 rc按表为0或1，不能把驱动作业 rc0解释成八方测试全通过。360状态是40个 F2P 状态加320个 P2P 状态，不是360个不同测试。

具体拒绝证据来自各轮 `*.eval.log`，不以计划奖励代替：

- coder_a1 和 coder_a3：仅默认 F2P 失败，实际 `KeyError: 'jobs'` 分别在 raw 第984／989行；FAILED summary在第1036／1041行。显式值及多配置通过，不能泛称所有 jobs 行为都失败。
- deepseek_a1：仅多配置追加／替换 F2P 失败，实际 `KeyError: 'jobs'` 在 raw第1019行，FAILED summary第1071行；其单配置与默认通过。
- Qwen：jobs2/jobs7 的字段值断言已过，随后在有效测试第1266行 `client.run_command("cmake --preset " + configure_name)` 抛出实际进程 rc1。raw第1035／1091行明确为 `"cmakeMinimumRequired" version too new`；FAILED完整 nodeid 在第1144／1145行。候选将最低版本3.15抬为3.25，同时改 schema4；**本次失败不能归因于 schema4**。

固定有效测试的显式节点先比较 jobs 值，再取实际生成的 configure／build preset名称，顺序运行第1266行 configure、第1267行 build。它不比较生成 JSON 的 schema 或 `cmakeMinimumRequired` 字面数字。`CMakeLists.txt` 的 NONE工程和最低版本声明是可消费验证脚手架；实际拒绝由 CMake进程产生。Qwen在configure抛出异常，因此两节点都未到build；不能沿用旧额外诊断中“configure失败仍尝试build”的路径来声称正式build也失败。

gold、DSa4、coder a2 两个显式节点均通过；结合顺序调用证明该范围 configure 与build均成功。DSa4的生成器限域路线、coder a2的替代导入／正整数处理路线按已有语义审查复用；本轮未改其接受范围，也未因源码不同或官方测试改动自动判零。

## 完整 Frozen、非官方路径与官方测试控制面

七份非空 `candidates/<ID>.patch` 的完整字节与 plan SHA及各轮 artifact `candidate.patch` 相符。Frozen pathset与完整 patch涉及路径逐项相等，未抽取 `presets.py` 片段替代原始候选；noop Frozen为空。

所有 Frozen entry的完整 `content_b64` 解码后与content digest一致。逐路径在内存逆应用原始 unified diff，修改文件恢复到对应 baseline完整内容SHA，新建文件逆应用为空且baseline缺席；验证覆盖了所有13个非空 Frozen文件entry。Frozen／baseline的canonical摘要分别与projection／ledger及Frozen中的baseline身份一致。所有materialized HEAD为 `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`，`excluded_pathset_changed=false`；classification均为projectable，unsupported shape为空，runner integrity无变化。

| 候选 | Frozen与实际评分投影中的非源码路径 |
| --- | --- |
| coder_a3 | `README_JOBS_FEATURE.md`、`conans/test/unittests/tools/cmake/test_cmake_presets_jobs.py`、`debug_test.py`、`verify_implementation.py` 均完整保留并投影。 |
| deepseek_a1 | `conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py` 修改完整保留并投影。 |
| deepseek_a4_generator_boundary | 官方 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py` 修改完整保留于Frozen，投影仅将其标为 `official_test_file` 排除；源码投影保留。 |
| 其余非空候选 | 完整patch只涉及 `conan/tools/cmake/presets.py`，均保留。 |

本轮另查实际grader在受信恢复前的raw `git status`：coder_a3四个新增文件均出现为untracked，源码为modified；DSa1源码与非官方单测均为modified；DSa4仅源码为modified，官方测试改动没有进入评分工作树。`git diff`本身不会展示untracked文件，故以完整Frozen字节、投影清单和实际status共同核运输，不用仅有tracked diff冒称完整候选证据。

DSa4官方测试Frozen完整内容为48758字节，SHA256 `3bfda25e0e4f9c9643ded3b01ad303caf5f6c3db2e7a8f58bc1976da8eb49074`。它没有被删除出冻结审计，也没有触发legacy“改测试自动0”：classification为projectable，正式5F/40P全通过、reward1。固定consumer控制面按official精确路径分类；非官方测试的保留由本轮实物projection和status证明。上述非官方文件进入评分工作树，不意味着本轮窄模块运行覆盖了其内容。

## 固定材料、CMake3.23.5与当前 actor

正式plan与prepared私有评分row、固定release SWE21 combined中的本题row完全对应；grading canonical digest为 `sha256:875041c5f0c9196d3623165d071f16da85be021e9da998186458f3f2b00343e9`。当前5F/40P、有效补丁和每轮ledger的revision均为 `conan15422_private_test_v2`。

固定release目录内本题revision目录仍命名 `conan15422_test_patch_f2p_v1`，但消费的有效字节为已核v2；不能只据目录名误判消费了旧测试：

- 有效patch SHA256：`9ad7529457054bb004534951feb4d08b40973a06fd30b4a1564054de074a0bb6`。
- 有效测试SHA256：`5de644e248dc131c250f343885d95ec5b9d9f2f35798852d79e263fe4252c16a`。
- registry SHA256：`0122d844e68b8f7f9f0c80140048c1cfedf2d809b5c1d4b595c6dfa73a115672`。
- grading materials identity：`sha256:90aad16e26a29c327e6735755eee37125a885b4051dc5f27a6a9ba1d456f0927`。

本轮独立核上述release成员与environment_recipe的manifest摘要和字节数。共享固定release manifest SHA256为 `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`；其旧完整release验证留存复用，不重新执行发布器或项目模块。

正式评分固定派生镜像身份 `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead` 的依据是 prepared inspect、已登记的 immutable consumer 与实际 prerequisite；八份 ledger 的 `image_id_actual` 虽均记录该 ID，本报告不将字段值解释为逐 grader 独立 image inspect 证据。其每轮prerequisite实际以UID54322执行且verified／rc0，脚本SHA为 `ed0834ad7fd732a65083443feb1fbf05e182d9ef9b772d74226913efd683e686`。固定consumer该脚本实际核CMake／CTest指向3.23.5、版本输出、Conan console入口的regular/executable/SHA；它不是“记录一个预期版本”的空标记。所有安装段结束rc0，测试段完整到上述实际assertion／CMake进程与summary。

**另一个实际actor工具切片** `actor_tools_15422_r12_v1` 在同R12release、同派生image上经受控Claude Code运行两条命令，独立支持：

- actual UID54321，testbed Python3.10.14，`conan`／`conans` 从 `/testbed` 导入，HEAD为上述base。
- `cmake --version`、`ctest --version` 实际输出3.23.5；`conan --version` 输出2.1.0-dev。
- 实际console入口 `/opt/miniconda3/envs/testbed/bin/conan` 的SHA为 `df26d3928be05d409787e3ecfffb06b278da9e738fdd1f5810a579ec854cf9d8`，与固定recipe相符。
- observed Claude Code2.1.205；prelaunch image与UID probe相符，CPU quota为 `200000 100000`，memory max为4294967296。两命令实际rc0，harness退出0，清理无该run label容器／网络残留。

这只证明当前派生环境中actor可调用所核工具与导入入口。受控两命令没有运行旧／新项目测试，没有完成普通issue求解，也不能证明新brief进入真实首请求。此前v2运行审查里的UID0私有诊断仅按其既有范围复用；正式UID54322评分和当前UID54321actor是本轮新增、不同用途的证据。

## 三项非参考 skip与证据边界

正式 `-rA` raw对三项skip**没有打印完整SKIP nodeid**，只有源码位置及reason。每轮均为：

| raw位置与reason | 固定有效测试AST映射的函数 |
| --- | --- |
| 第355行，Only OSX | `test_cmaketoolchain_cmake_system_processor_cross_apple` |
| 第382行，Only OSX | `test_apple_vars_overwrite_user_conf` |
| 第816行，Only Windows | `test_presets_paths_normalization` |

映射来自SHA已核的effective_test.py中对应skipif装饰器与函数范围，和root audit的映射依据相符。这三项不在45参考清单，故不减少360参考状态；不能将映射得到的完整函数名伪写成raw直接打印的SKIP IDs。24次非参考skip与360参考状态分别计数。

旧两份v2非作者审查的结论按当前相同测试字节复用：默认helper比较只核输出与公开helper一致，不能独立证明CPU探测正确；NONE工程只核preset可消费与命令成功，没有实际可并行编译任务；实际消费范围为显式Unix Makefiles2/7，默认／Ninja多配置仍属JSON行为检查。本轮没有新的实际反例要求增加平台、并发速度、compiler或假想helper保护层。正式矩阵资源只保留声明与内存峰值，不冒称全部每容器资源事实；actor切片的prelaunch/probe事实仅适用于该切片。

## 原件范围与停止

正式原件根：`runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_15422_r12_v2_evidence/formal_matrix_15422_r12_v2/`；actor原件根：同runroot的 `actor_tools_15422_r12_v1_evidence/actor_tools_15422_r12_v1/`。两份remote audit分别列120／34文件，独立逐件重算SHA与字节数，均相符；本地文件数也分别120／34，无缺件或多件。

读取正式plan／matrix／ledger／raw日志／Frozen／baseline／projection／候选／prepared私有身份及必要runner、root/remote audits；actor读取其root/remote、身份／工具capture、public_commands、preflight/prelaunch与版本留存。固定R12release仅查本题registry/test/environment recipe与必要consumer。复用 `non_author_15422_v2_semantic_review_20261003.md` 和 `non_author_15422_v2_runtime_review_20261003.md`；未重读旧诊断全树或访问其历史候选指针。

| 当前留存文件 | SHA256 |
| --- | --- |
| `matrix_results.json` | `bfb54c7b42d260581fb772c0140b37540488dadf3a77252a84dea47315f23b8a` |
| 正式root audit | `0acc97b0a3fe6a73fc01003a6f29a97783aa511efa5aea58e1c2b4816320651e` |
| 正式remote audit | `a7a33508b01e9de96aca536ca8040153d29eacdd84bd91bacfcd2a7ebd644763` |
| actor root audit | `7d3d696d1c8fea32e35e07324ad59d635b20343126338448609b15ea665afcb9` |
| actor remote audit | `bee82b0264fd265ce213615c479e66544c626f02532277c5a0556f01439e10f7` |

本轮只用本地stdlib JSON／SHA／AST／base64／文本及内存diff核对，未导入项目模块、远端、Docker、测试、实验或模型，未重跑历史，未向别的线程发消息。唯一新增本报告，不改task／board／shared或已有审查。

停止条件满足：当前正式消费与既有v2范围一致，360实际状态和三项非参考skip的来源明确，完整Frozen运输、控制面排除、合理替代与当前actor工具身份均有对应原件，无实际新缺口。只在这些原件身份或正式执行出现具体反证时再按影响范围复核。
