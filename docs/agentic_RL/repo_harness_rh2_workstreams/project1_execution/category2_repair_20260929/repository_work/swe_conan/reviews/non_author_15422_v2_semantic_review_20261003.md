# Conan15422 v2 非作者语义窄核

2026-10-03。角色：Falsifier / Simplifier；未参与 v2 编写。**当前 v2 可提交共同登记后的受影响窄核；没有发现需要先修改测试的当前语义阻断项。** Qwen3.6 a2 的实际消费缺陷已在私有 v2 中被拒绝，三种已有有效实现仍通过。共同 consumer、完整 FrozenPatch 的正式评分及正式用途结论尚未发生，本报告不把私有源码投影结果写成正式 reward。

保存时收到最新暂停要求，已停止新增检查、实验和外部搜索；以下可提交结论仅说明材料条件，不表示当前获准继续执行或发送下游通知。后续事项保留，未启动。

## 上下文与核查方式

收到题主限定任务：核公开 jobs 目标、默认值、显式 2/7、多配置追加/替换、CMake3.23.5 兼容要求和源码投影边界；已告知 v2 因 v1 实际消费缺口而增加 configure/build。本轮不是 fresh 公开读者。先读公开 `user_prompt.txt` 与指定 base，再读 v2、候选源码与原件、诊断原日志和作者 audit，最后接续已有非作者 v1 材料意见；没有将修订单的 expected_reward 作为事实。遵循根 AGENTS.md、review-standards.md §10.4/§10.5 和 remaining_workflow_20261002.md 的窄核与停止条件。未再委派子 agent。

仅用本地只读的 Python stdlib 重算哈希、内存应用统一 diff、AST 对比和解析原日志；未运行 Conan/pytest/候选代码、远端、容器、安装、模型或正式评分。另查官方 CMake3.23 文档。唯一写入是本报告。

本次绑定材料：base `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`；有效测试补丁 SHA256 `9ad7529457054bb004534951feb4d08b40973a06fd30b4a1564054de074a0bb6`；有效测试文件 SHA256 `5de644e248dc131c250f343885d95ec5b9d9f2f35798852d79e263fe4252c16a`。根有效补丁与 materials/v2 原件字节相等，内存应用结果等于有效 `.py`；v1→v2 只有 `test_presets_jobs_explicit_values` 的函数 AST 改变，无删除函数。

## 公开依据与接受范围

[公开 issue 文本](../../../../../../../../runs/swegym_quality_batch01_20260921/public/conan-io__conan-15422/user_prompt.txt)要求 Conan 在 buildPresets 中设置 jobs，使 install 后直接调用 CMake 能并行构建。报告者使用 Ubuntu、CMake3.27.4；这个报告版本本身不构成项目最低版本决定。

公开 base 的 [build_jobs](../../../../../../../../runs/swegym_quality_batch01_20260921/public/conan-io__conan-15422/base/conan/tools/build/cpu.py)说明显式 `tools.build:jobs` 优先，否则读取 CPU/cgroup 默认值；[CMake helper](../../../../../../../../runs/swegym_quality_batch01_20260921/public/conan-io__conan-15422/base/conan/tools/cmake/cmake.py)的 Makefiles/Ninja 构建参数已经使用这一逻辑。默认 jobs 与 helper 一致是结合既有公开行为的合理推导，不能表述为 issue 逐字指定了默认算法。新默认断言只比较同一生成进程的输出值，没有要求修复必须导入该 helper，也没有绑定宿主固定核数。

公开 [preset writer](../../../../../../../../runs/swegym_quality_batch01_20260921/public/conan-io__conan-15422/base/conan/tools/cmake/presets.py)告知用户手动 preset 适用 CMake>=3.23；公开 [tool fixture](../../../../../../../../runs/swegym_quality_batch01_20260921/public/conan-io__conan-15422/base/conans/test/conftest.py)已有 Linux CMake3.23.5 路径。因此 v2 用这个版本消费生成 preset，是保持既有可用范围，而非从 gold 增加新目标。官方 [CMake3.23 preset 文档](https://cmake.org/cmake/help/v3.23/manual/cmake-presets.7.html#build-preset)明确 jobs 为整数，等价于命令行并行参数；同页也支持 schema 1–4。jobs 不需要抬高到 CMake3.25。

多配置测试在同一目录执行 Release2→Debug7→Debug3，每步核完整 configuration→jobs 映射与配置数量，既能拒绝丢旧配置/不更新 jobs，也不固定列表顺序。公开 writer 的 `_insert_preset` 与原 `test_cmake_presets_multiconfig` 已有追加和同名替换语义；新要求只是让 jobs 随既有配置正确保留。它没有把 Ninja Multi-Config 误当不支持并行的生成器。

v2 的显式 2/7 改用 Unix Makefiles，并在生成的名称上执行 `cmake --preset` 和 `cmake --build --preset`。名称来自实际输出、经过 shell 引号保护；`project(... NONE)` 避免编译器要求。测试不要求 schema=3、最低版本=3.15 或特定内部函数位置；只要求实际生成配置能在已支持的 CMake 上使用。

## 反证尝试与实际结果

独立从八份 `effective_module.out` 解析全部 45 个正式参考节点，与计划逐项对照，没有参考缺席。下表为**私有 root 源码投影**结果；40 个 P2P 在八行全部通过。日志另收集的三个平台节点不是这些正式参考，不能把它们的 skip 计成 P2P 缺席。

| 候选 | F2P 通过数 / 5 | pytest rc | 有区分力的结论 |
| --- | ---: | ---: | --- |
| noop | 0 | 1 | 旧实现缺 jobs，未被错误放过。 |
| gold | 5 | 0 | 直接在 build preset 写 helper 值仍通过。 |
| coder_a1 | 4 | 1 | 显式值通过，但默认缺 jobs。 |
| coder_a3 | 4 | 1 | 显式值通过，但默认缺 jobs。 |
| deepseek_a1 | 4 | 1 | 单配置有 jobs，多配置缺 jobs。 |
| deepseek_a4_generator_boundary | 5 | 0 | 限定 Makefiles/Ninja 且排除 NMake 的不同合理路线通过。 |
| coder_a2_alternative | 5 | 0 | 函数内导入 helper、正整数条件写入的不同路线通过。 |
| qwen36_a2_schema_diagnostic | 3 | 1 | 字段检查通过，2/7 的实际 configure 均因最低版本过高失败。 |

证据：[各候选原日志目录](../../../../../../../../runs/category2_repair_20260929/conan_cpu_20261003/diagnostic_evidence_15422_v2/output)、[作者 audit](../../../../../../../../runs/category2_repair_20260929/conan_cpu_20261003/diagnostic_audit_15422_v2.json)。本轮重新解析结果与 audit 相符，但没有独立重新执行这些命令。

**历史 finding：v1 放过不可消费 preset，现已在私有 v2 关闭。** 可达性 `test_only`：这次观察入口是私有 root 诊断；正式消费尚未实施。Qwen3.6 a2 把 schema 从 3 改为 4，同时把 `cmakeMinimumRequired` 从 3.15 抬为 3.25。原日志明确为 `"cmakeMinimumRequired" version too new`，不能把失败归因于 schema4。v2 两个显式节点在该处失败，gold 和两个不同有效实现保留通过。处置 `accepted`：保留已有最小局部修订，不再增加恢复状态、fallback 或候选。现在修的理由是已观察的真实输出不能消费，而不是理论输入；删除消费断言会恢复此漏判，延后会把已知错误候选带入下一正式验收切片。

**误拒假设：CMake3.23.5 是不合理约束。** 处置 `rejected_with_evidence`。公开 base 已承诺该范围，jobs 在该版本可用，已有不同合理源码路线实际通过。无需升级到报告者的3.27.4；升级反而会失去这项既有兼容检查。没有发现当前合理修复必须依赖更高 CMake 才能实现本题功能。

## 投影边界与剩余不确定性

独立对七份 `.original.patch` / `.source.patch` 重算原摘要、投影摘要，在内存分别应用其中 `conan/tools/cmake/presets.py` 的 diff；七份目标源码均完全相同，after SHA 均匹配 [source_projection.json](../../../../../../../../runs/category2_repair_20260929/conan_cpu_20261003/diagnostic_15422_v2/private/source_projection.json)。因此可据此判断 presets 实现本身在 v2 下的表现。

coder_a3 省略 README/新增测试/调试脚本，deepseek_a1 省略单测，deepseek_a4 省略集成测试修改；其他四份投影等于原补丁。省略这些路径使本次诊断不能证明完整 FrozenPatch 的应用、受信测试恢复或正式评分行为。正式 consumer 仍须消费已冻结完整候选；不能拿投影替代原件，也不能把本表直接登记为新 reward。可达性 `conditional_future`：仅在共同登记/正式执行后才涉及正式评分，本轮无该结果。

两个非阻断边界采用 `no_fix_accept_residual_risk`：

- 默认断言通过公开 helper 得到答案，能核本题输出与既有行为的一致性，不能独立证明 helper 自身的 CPU 探测正确。七份已核候选只改 presets 实现及所列非目标路径，未改变 helper；目前无实际关联 oracle 失真。未来候选若改 helper，再据具体补丁审计，不为本轮新增公共保护层。可达性 `conditional_future`，条件是候选另改 helper 且造成一致错误。
- NONE 项目实际 configure/build 验证可读性、配置关联和命令成功，没有可并行任务，故不证明运行时确实有2/7个任务并发，也不证明加速。jobs 字段和官方等价定义足够验收本次已知缺陷；新增速度、时间或并发压力测试会引入资源噪声，当前没有需要它的新反例。可达性 `test_only`，属于本次测试可观测范围，不是当前正式评分缺陷。

默认 Ninja、多配置节点仍只核 JSON；实际消费只在显式 Makefiles2/7。这个范围足以关闭本次最低版本抬高的漏判，不据此宣称所有生成器/平台都能消费。没有本题已知证据要求扩展 NMake、Visual Studio、Xcode 或新增全题调研。

## 选项、推荐与停止条件

| 选项 | 理由与代价 |
| --- | --- |
| 保留 v2，提交共同登记后的受影响窄核 | 推荐。保留实际兼容检查及三条已验证合理路线，新增成本只在原两个显式节点。 |
| 删除实际消费 | 少两次命令，但会重新放过已观察的最低版本回归，不推荐。 |
| 固定 schema/最低版本字面值 | 静态更便宜，但会绑定实现数字，且不保证实际可用，不推荐。 |
| 扩展所有生成器或升级 CMake | 无当前必要反例；增加成本或丢失旧兼容检查，不作为本轮要求。 |

**停止条件已满足：材料语义窄核结束。** 题主可继续提交 v2 给共同登记维护者，受影响正式验收至少保留 noop、有效正对照、默认遗漏、多配置遗漏、最低版本回归，以及已存在的不同合理实现；同机制两份默认遗漏是否去重按已有正式矩阵约定处理，不机械新增候选。下一步只核共同消费的材料身份、实际 CMake3.23.5、完整 FrozenPatch 与对应参考断言执行结果。未完成正式评分是当前用途边界，不是要求再次审批材料。若正式证据与本次私有结果矛盾，回到相应差异；不继续扩展无关反例。
