# Conan15422 Coder a1：非作者语义与误拒窄核

2026-10-03。仅核 `gpu1003-conan15422-coder-a1`，physical attempt `#p1`；公开 base `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`；当前材料 `conan15422_private_test_v2`。遵循 `coordination_workflow_20261003.md`，不启动 CPU/GPU，不重审旧 CPU 矩阵，不改既有材料、候选或回执。GPU 独立执行审仍待回，本报告不代替它。

## 结论与处置

**raw0 对应本候选实际遗漏，未发现当前 v2 评分误拒或材料缺陷。** 候选仅在 `conf._values` 含显式 `tools.build:jobs` 时写 jobs；不配置 jobs 的普通 install 仍生成缺少 jobs 的 build preset，保留公开问题所述的主要默认场景。可信唯一失败是读取默认 `jobs` 的 KeyError，不是 CMake 安装失败、测试被修改而自动判零或固定数字 oracle。

发现一项 **P1 候选功能缺陷**（默认 jobs 遗漏）和一项 **P2 验证范围表述问题**；没有 P0、共享 blocker 或待 Qwen 停发理由。P1 是这份候选不能判成功的原因，不是当前任务材料应停止探针的理由。raw0 保留；不建议删除默认参考、改 reward 或补新假想 guard。模型的默认假设错误及自测驱动回退值得作为能力诊断事实记录。

## 七个方面的核查要点

| 方面 | 判断与边界 |
| --- | --- |
| 1. 材料与身份 | v2 测试文件 SHA 与固定 revision_plan 相符；本次 diagnostics 的材料 identity 与已接受 R12 CPU 材料相同。只核这一绑定与本次原日志，没有重跑 CPU 或重做 GPU 身份审。 |
| 2. 公开题意 | issue 要求生成 buildPresets.jobs，使 install 后直接调用 preset 的 CMake 能并行构建；没有逐字指定默认算法。默认接续既有 public helper 是公开源码支持且本批已接受的行为范围。 |
| 3. 生产修法 | 显式正整数配置可写入 jobs，但 guard 跳过 helper 的正常默认值，是部分修复；可信默认失败与此同因。 |
| 4. 兼容与边界 | 插入位置被 single/multi-config 共用，显式值和多配置追加/替换通过；schema/minimum CMake 未改。不能据这些通过抵消默认功能缺失，也不扩大成所有平台实际消费已验。 |
| 5. 完整候选与可信评分 | 三份完整文件与 diff 内存回放一致，三路径全部投影保留；公开单元测试修改没有被排除。仅目标 integration 文件从 base 恢复后施加可信 v2。45 参考真实 44P/1F，3 个非参考 OS skip 单列。 |
| 6. 求解方法 | 模型先使用 build_jobs 的默认值，再为通过自己定义的“无显式配置应无 jobs”测试加 guard；不能把这个测试假设当成公开要求。没有发现评分绕过。 |
| 7. 验证与最终陈述 | 修改后的公开单元模块 4 passed、CMake 单元目录 58 passed；原公开 integration 模块 40 passed/3 skipped。demo 实际调用生成函数并检查 JSON，未运行 CMake configure/build 或并行编译。最终“全面解决”与默认遗漏不符，“所有既有测试通过”须限定到实际命令范围与 skip。 |

## P1：显式配置 guard 保留默认问题

**当前行为**：生产 `_build_preset_fields` 仅在 `"tools.build:jobs" in conanfile.conf._values` 时调用 `build_jobs`，否则没有 jobs 字段。原 issue 没有要求用户先补 jobs 配置；其抱怨就是普通生成文件缺少 jobs，手动填较大数字后才并行。

**公开依据与不变量**：公开 `conan/tools/build/cpu.py` 第 8–28 行明确写明 `build_jobs()` 显式配置优先，否则使用 `_cpu_count()` 的 CPU/cgroup 默认值，探测不可用时安全返回 1。公开 `conan/tools/cmake/cmake.py` 第 11–19 行的 Makefiles/Ninja 构建参数已经按该有效值加 `-j`。因此默认 preset 接续 Conan 既有有效 jobs 行为，是公开目标与源码的合理推导；不是把 issue 中示例 16 当常量，更不是要求候选采用某个固定内部函数位置。

**精确触发**：无显式 `tools.build:jobs` 的 Ninja install。缺少 jobs 字段使普通 preset 构建无法获得 Conan 的默认并行设置；模型自身的生成测试还实际观察到 helper 默认 2（trajectory 第 294/299 行）。此 2 仅是 actor 自测原输出，不当作 grader 默认核数。可信默认测试在生成同一进程输出 helper 值，然后检查生成 JSON，不锁宿主核数或容器配额。

**影响**：显式设置 jobs2/7/42 等路径可工作，但默认使用者仍遇到本题原缺口。从当前公开 `Conf.get()` 也可静态看到默认值是有效配置语义的一部分，内部存储是否有 key 不能替代有效值判断。本候选没有改 helper，因此默认 oracle 被候选协同改坏的假设在此不成立。

**最小修正与分期**：候选若要完成本题，应移除“必须显式配置”的门槛，按有效 jobs 值生成 build preset，并纠正自测中“未配置应无 jobs”的断言。可以保留合理生成器范围与正整数处理，不要求照抄某一修法。本报告不写回候选，也不要求追加试验；作为本候选成功判定前必修。可达性为普通公开生成路径，处置为 `accepted`。

## 主动排查误拒与既有范围

误拒假设一：“只支持显式 jobs 也是完整合理实现”。原 issue 确实没有逐字给出默认算法，不能以隐藏题面补写要求；但缺字段导致默认单线程的公开问题、Conan helper 的默认并行行为及普通 CMake helper 已有消费共同支持默认场景。本候选完全省略默认 jobs，并把省略宣传为 backward compatibility，没有给出需要保留该缺口的公开约束。本批既有 v2 独审已接受同进程 helper 比较；不同合理实现、合理生成器边界在已有 CPU 验收中保留通过。这里复用接受范围，不把旧候选 expected0、gold 或其相似失败当作本次正确性依据。

误拒假设二：“默认测试锁实现、固定 CPU 数或只是 JSON 严格字段”。v2 `test_presets_jobs_default_matches_public_helper`（第 1227–1247 行）在同一 recipe generate 中获取有效 helper 值，执行真实 `CMakeToolchain.generate()`、读取输出并比较 jobs。它不要求 import 写在候选哪里，也不锁字段顺序/具体核数。缺少字段正是公开未被修复的对象。本轮不能以此独立证明 helper 的 CPU 探测本身正确，但 helper 未改，未发现本候选相关 oracle 失真。

误拒假设三：“改过测试自动判0”。与原件不符：完整投影包括生产、公开单元模块和 demo，classification projectable；可信评分只保护自己的 integration 路径。raw0 有具体正常测试失败且其它 44 参考通过，不是卫生规则或自动拒绝。

已有 v2 边界：显式 Unix Makefiles jobs2/7 会实际 CMake configure/build `project(... NONE)`，默认 Ninja 与多配置 jobs 映射主要检查 JSON；不要求真实并行编译吞吐，也不扩到所有 generator。当前候选保留既有 schema=3/minimum 3.15，不触发前轮最低版本消费问题。v2 此次不需改测试或升级 actor；待 Qwen 不因本候选失败停发。该判断不替代尚待回的 GPU 执行独审。

## 完整 FrozenPatch、投影与实际失败

完整候选有且仅有三份内容：

1. `conan/tools/cmake/presets.py`：上述显式 guard，函数内导入 helper。没有私有节点名、题号或环境分支；其它 preset 合并和 schema 逻辑不变。
2. `conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py`：模块级共享 fixture 改为每次创建新 recipe，既有两个功能断言保留；新增显式 jobs8 和“未配置无 jobs”的两个断言。后者是方法错误，但不是评分保护面绕过。
3. `demo_jobs_feature.py`：新增脚本调用 `_CMakePresets.generate`，输出两组 JSON；catch Exception 后打印、错误分支只打印，不可靠地以退出码证明断言成功。本次最后的原输出确有显式16/默认无 jobs 两种结果，错误默认假设也在 demo 中被标为成功。

本轮用 stdlib 对三个文件内存应用完整 diff，包括新增脚本无末尾换行，再与 Frozen 逐字节比较；三者相等、content SHA 相等、AST 可解析。Frozen canonical digest `aedc9be118a8ac7bd198e6089a59d81ba378517411912f6cb0584585c26bfca9` 与 projection 相符；`included_entry_paths` 与全部三 entry 集合精确相等。公开单元模块在投影中保留，不能写成“官方测试修改已全部排除”。report 的 `test_files_modified=false` 在此不表示候选没有修改任何测试文件；受保护的可信 integration 路径未被候选触碰。

原 eval log 第 787–803 行仍显示公开单元模块新增断言；第 805–816 行才对 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py` 从固定 base checkout 并施加可信补丁。第 837–849 行 restored=1、apply_rc=0、expected/present=1、缺失/不规则文件=0、setup_ok=1。

实际唯一失败：第 1055–1080 行 `test_presets_jobs_default_matches_public_helper` 到达 `presets["buildPresets"][0]["jobs"]`，`KeyError: 'jobs'`。install 已完成，expected helper 输出的正则条数检查已经通过；失败发生在字段缺席，未进入数值相等比较。不能把它描述成 jobs 数字不符、默认 CMake build 命令失败或 CMake schema 拒绝。

本轮从 raw `PASSED/FAILED` 精确节点逐项对照 diagnostics 中 45 正式参考：44 passed、1 failed、没有缺席或额外 pass/fail 节点；对应原 F2P1/1、added F2P3/4、P2P40/40。第 1123–1126 行明确为原 jobs42、显式 jobs2、显式 jobs7、多配置追加/替换通过。第 1127–1129 行另 3 非参考 OS skip 只打印 source line 355/382/816 + reason；不冒称 raw 打印完整 SKIP ID。第 1131 行是 collected48 的 1 failed/44 passed/3 skipped，与正式45加非参考3一致。parser `num_parsed_tests=46` 不是 raw/参考计数，未用它替代逐项核对。

## 方法回退与真实自测

完整 trajectory 454 行，与另一份 `attempt/trajectory.jsonl` 字节相同。已核全部 assistant 文本、工具输入、关键工具原输出和最终结果，生产回退顺序是决定性证据：

- 第 186 行读公开 helper；第 195 行正确定位 `_build_preset_fields`，第 199 行首次生产实现直接调用 build_jobs 并写有效值。
- 第 225 行新增自测先写 string8，使用共享 module fixture，还加入“未配置应无 jobs”。第 242 行 2 failed/2 passed；第 251 行修 string8 为 int8 后，第 268 行仍 1 failed/3 passed，fixture 上残留 jobs8。
- 第 277 行改成 fresh recipe，隔离修正合理；第 294 行仍失败，输出默认 jobs2。第 303/307 行重新读公开 helper，知道无配置会返回 CPU 默认值。
- 第 312 行把这个真实默认行为当“问题”，第 316 行添加 `_values` 显式 guard。第 333 行其自定单元模块 4 passed。不是环境逼迫回退，也不是既有公开测试要求省略默认字段；主要依据是模型新写的错误默认断言。
- 第 348 行原公开 integration 模块 40 passed/3 skipped，命令用了 `-k "not test_locally_build_linux"`；第 361 行 CMake 单元目录 58 passed。这些没有当前可信默认测试，且通过自定测试不能证明默认目标已满足。
- demo 第 383/423 行分别 import/NameError 失败；第 432 行改写后第 445 行成功生成 JSON，默认无 jobs、显式16有 jobs。最后版本真实调用生成函数，比复制表达式更直接；但没有 `cmake --preset`、`cmake --build --preset` 或真实并行编译调用。

**P2（非阻断方法/验证表述）**：最终第 450/454 行“fully addresses original issue”与 P1 遗漏冲突；“all existing unit/integration tests continue to pass”须写成实际模块/目录数量并保留 3 skip，不扩大成全仓。demo 的 hardcoded 示例名称带 conan 前缀，但实际两组名称是 `relwithdebinfo`；打印的示例 CLI 从未执行，不能说它实际 build 已通过。最小处置是保留轨迹、在分析中写清验证范围与错误默认假设；不需要新的 CPU/GPU 实验。可达性为候选最终说明/分析汇总，处置为 `accepted_with_scope_limit`。

## 原件、已读范围与停止条件

已读：现行 coordination workflow；review-standards 与统一处理标准的相关审查范围；指定 `_20260921_v2` 公开 bundle 及 base 的完整 presets.py/build cpu.py、CMake helper 并行入口、Conf get/define/unset 相关语义；完整本臂 diff/Frozen/classification、两份相同 trajectory、solver prompt、projection/report/diagnostics/raw eval log；当前 materials/v2 revision_plan/change_from_v1/effective_test 的相关默认/显式/多配置函数；已有 v2 独立语义与 runtime 范围；R12 CPU acceptance 的身份与既有接受范围、当前 probe_request 固定绑定。未重读旧八候选源码或矩阵原日志，没有以它们的 expected_reward 作结论。

公开源码根：`runs/swegym_quality_batch01_20260921_v2/public/conan-io__conan-15422/base/`，目录确实存在，不需替代来源。原件根：`runs/ordinary_gpu_probe_20261002/remote/queue_v18/results/gpu1003-conan15422-coder-a1/`。本次材料 identity 为 `sha256:90aad16e26a29c327e6735755eee37125a885b4051dc5f27a6a9ba1d456f0927`，与 R12 已接受材料相同；effective_test.py SHA `5de644e248dc131c250f343885d95ec5b9d9f2f35798852d79e263fe4252c16a`。

| 本次主要原件 | SHA-256 |
| --- | --- |
| 完整 diff | `f429ece39a75f44ffe6feb47251ac842962c2c0dc6ca3ea0a136523dc921b1df` |
| FrozenPatch 文件 | `afec7b91ee51d4cb97233221e9088aa5cd00242242aa7e0e02d5cd5293f42958` |
| 完整 trajectory | `b936d704d424534d2d2181a23787b803dd5a2f9395a3b8017996685a0d4a6103` |
| projection | `6ba15d309f292b4ea2992b7026f6a1697a5affdbe7fb45b7304c0bae69a07f63` |
| raw eval log | `eac651d5b75268f5fdc07034a5e0f91168328d6e004d098e47ada37ea86224f1` |
| diagnostics | `2f5a732154784c696a90aebe8c5a172207981fbe98f96c7679449b62739499c6` |

本轮只运行 stdlib 静态 SHA/AST/diff/日志解析，未执行项目代码或模型。未声称 GPU 完整运输/实际镜像现场独审完成，未授予训练或留出资格。公开默认功能、完整候选、实际失败及误拒假设已有足够证据；没有新的材料或共享阻断，**此处停止**。
