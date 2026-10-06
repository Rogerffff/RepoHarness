# Conan14177 R11 正式 CPU 语义与范围窄核

日期：2026-10-03。角色：非作者 Falsifier / Simplifier；本批指定模型配置 GPT-6.1 Sol / high。依据根 AGENTS.md、review-standards.md §10.4/10.5。本报告是获准接触私有 CPU 原件后的第二阶段核查，**不是干净公开盲审**；此前公开读者报告保持原样。

**结论：本次限定 CPU 范围没有具体阻断。** 15 个完整候选的正式结果与原始日志相符；当前仍是原 13 个参考，分组为 2F／11P。单补丁描述参考迁移到 P2P 后实际参与评分。五个正对照通过、十个候选为 0；没有把私有诊断或静态检查当作本轮正式运行。结论不建立完整 solver 交付、GPU probe 或训练资格。

## 读取与执行边界

本次只读取下列限定材料及其 14177 相关调用段；仅用本地标准库做 JSON、SHA/大小、原始日志、AST 和内存补丁内容核对。未访问远端、Docker、模型，不运行项目或测试，不修改材料或共享文件，仅新增本报告。

- CPU 原件：`runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_14177_r11_v1_evidence/formal_matrix_14177_r11_v1/`，含 plan、publication input/receipt、prepared identity、host grading view、完整候选、15 份账本、raw eval log、Frozen/projection/classification/stage artifact、run_matrix.py。
- 同 runroot 的 `formal_matrix_14177_r11_v1_remote_audit.json`、`formal_matrix_14177_r11_v1_audit.json`。作者/根审的汇总只作索引，关键结论另核原件。
- 固定 R11：`runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe17_dask_conan_v1/` 的 manifest、`checks/consumer_combined_264.json` **仅 14177 行**，及 repo 内本题 registry/material、prepared consumer、formal replay/manager/projection、绑定 parser 路径。
- 本工作包 `tasks/conan-io__conan-14177/` 的 card、revision_plan、publication_request_20261003_v1、effective_test.patch/py。
- 公开 `runs/swegym_quality_batch01_20260921/public/conan-io__conan-14177/` 的 user_prompt、base patches.py、test_patches.py、output.py 及相应公开 mock。
- 既有独立云端报告 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/conan-io__conan-14177/review.md` 的相关依据及末尾 v2 聚焦复核。只复用其适用语义范围，没有复跑其 23 变体或旧正式矩阵。

## 固定身份与真实消费

固定 release ID 为 `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`，manifest SHA 为 `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9`。本轮独立核 manifest SHA，并核 16 个相关 material/consumer/parser 文件的 manifest SHA 与大小；没有扩审其它题的 release 内容。

publication_input 与工作包固定 request **字节相等**。release 的 14177 consumer 行与 plan、prepared_identity 的 consumer 完全相等。host grading view 实际消费有效测试补丁及 2F／11P 数组，补丁 SHA 为 `ee614041a0b3579f99b561daf33a763a3fe567cd90bc64cb3df0bca6131d2d8c`；与工作包及 release material 的有效补丁/文件字节对应。有效补丁在公开 base 上按上下文在内存应用，所得文件与 effective_test.py 字节相等。

实际 registry 是 `repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan14177_test_patch_v1/material_revisions.json`，SHA `cd218a8784db849d63bac185b529348795e23477e65b18893cdecfdcf0346ec3`，与账本绑定一致。其原测试补丁 SHA `23d0fb5bb7d354dabcaec01ae457efa788b7f1484a445a114eb03ca3c7743f62`、父 grading identity 和精确迁移节点保留，操作为 `replace_test_patch_move_f2p_to_p2p`。正式 grading identity 为 `sha256:926d6baa95fad4532d8a85387c6fc9dbf0b05fc6b53d7ff4e7a8565428fe94a4`。

公开 actor test snapshot 是原 base 文件（SHA `a5721c3f31609fca591c2d90e7b944a337cd93f1ec411118d56f6eee472f18c0`），不是有效私有评分文件；这是公开面与评分面的既有分离。本轮没有把两者混用。prepared_image_id 为 plan 固定 config `sha256:4ca5aeae4e588c89008e6ca335500ffa71aea77bd6eab0b7491d514534696bb0`；账本按来源 manifest 记录 image_identity，不把非 local-build 路径的空 image_id_actual 当作已核 config 值。

## 全补丁、全参考与 raw log

211 个远端回收原件的本地 SHA/大小逐一匹配 remote audit。15 个本轮 run label 的容器/网络查询均 rc=0 且输出为空；15 份账本也记录候选清理 `removed=true`、`rm:ok`。这里只确认已回收的查询原件，不声称我重新查询机器或清理其它对象。

14 份非空候选仅改生产 `conan/tools/files/patches.py`。逐份核 stage candidate SHA、持久化 candidate.patch 字节，再将**整份补丁**按唯一上下文在公开 base 文件上内存应用，与 Frozen 的 decoded content 及 content_digest 相等；noop 的 Frozen entries 为空。全部投影无忽略项，excluded_pathset_changed=false。没有按补丁片段、候选名或预期值替代正式内容。run_matrix.py 的 expected_reward 是运行后断言，正式评分由 FrozenDeltaSource 进入 manager.grade。

原 3F+10P 参考集合与当前 2F+11P 集合严格相同，没有增删成 14 项。迁移的 `test_single_patch_description` 与其它 10 个 P2P 函数均与公开 base 的 AST 相等；有效补丁只改两个 multiple 测试并增加辅助代码。迁移节点在正式 partition 中单列 moved_p2p，gold/gold_log_only 的该节点失败计入 p2p_fail=1，证明不是仅登记后遗漏。

逐候选从 raw pytest summary 提取 13 状态，与三 partition、报告计数逐项相等，共 **15×13=195**。全部 num_parsed_tests=13、参考缺席/跳过/未记账为空，没有 stage_error。失败候选归 `tests_failed`，不因 TypeError/断言失败被误归环境失败。

| 完整候选 | reward | F2P 通过／2 | P2P 失败／11 | raw 归因 |
| --- | ---: | ---: | ---: | --- |
| noop | 0 | 0 | 0 | 不接受 verbose 参数 |
| gold | 0 | 0 | 1 | 原描述输出被改；multiple 默认输出/verbose API 不符 |
| pubcand | 1 | 2 | 0 | 13P |
| probe_post | 1 | 2 | 0 | 13P；成功后记录 |
| probe_abspath | 1 | 2 | 0 | 13P；绝对路径可辨认 |
| probe_merged | 1 | 2 | 0 | 13P；文件名与描述合并 |
| probe_header | 1 | 2 | 0 | 13P；额外说明行 |
| always_log | 0 | 0 | 0 | 默认输出新增文件名行 |
| never_log | 0 | 0 | 0 | True 下缺文件名 |
| gold_log_only | 0 | 0 | 1 | 原描述输出/默认输出不符；不能用它单独证明应用断言 |
| print_only | 0 | 0 | 0 | True 下缺既有描述内容；不能用它单独证明应用断言 |
| output_verbose | 0 | 0 | 0 | 默认 STATUS 下文件名不可见 |
| probe_basename | 0 | 0 | 0 | 缺 conandata 中含目录的补丁名 |
| probe_kwonly | 0 | 1 | 0 | 位置参数 True 的 TypeError |
| probe_logonly_v | 0 | 0 | 0 | 仅 `_applied(calls)` 两断言失败，打印正确但没有应用调用 |

## 接受／拒绝范围与限制

本轮 CPU 重现既有云端 v2 的合理接受范围：不固定 Applying 措辞、不固定打印在应用前、不要求 verbose 无匹配时绝对空输出、不锁描述为独立整行。`probe_post/abspath/merged/header` 四种替代与 pubcand 共五个正对照通过。原 gold 的 0 有公开题义依据，不把 gold 文件名本身当答案权威。

公开 issue 明示 `def apply_conandata_patches(conanfile, verbose=False)`，因此位置参数 True 的既有边界有依据，但仍属非核心边界，复用旧审查记录而不新增要求。公开 output.py 默认 LEVEL_STATUS，verbose() 受更低日志等级门控；True 是调用的显式开关，题面要求构建日志可见哪些文件被应用。因此仅使用 output.verbose 导致默认不可见的拒绝归因成立。示例是否带 CLI `-v` 仍是推断，不能冒称明确题面事实。

`probe_logonly_v` 正式日志只在 `_applied(calls)` 处失败，满足旧云端 B2 所要求的独立辨别力；它纠正“打印正确但不应用”的误接受。需精确限定：此 effective test 通过记录型 patch_ng 替身验证既有解析/应用路径、源文件与 base_path 的调用，并非本轮真实修改磁盘文件的 patch engine 功能测试。既有独立云端语义报告的真实文件依据可复用，但不能计成本轮新 CPU 动态证据。

本轮静态调用链是正式 Frozen → trusted scoring projection → manager，显式官方测试控制面改动被排除且其余候选路径保留；`test_globs=()`，测试样路径只作 sidecar 观测。manager 的 Frozen hygiene 只描述实际重放的候选子集；旧 diff hygiene 自动降为 0 的分支不作为本次正式依据。**15 个候选均未改测试文件，所以本轮没有动态实测 test-edit 分支。** 不新增该候选/guard 来重开已经验过的边界，也不把静态确认写成动态验收。

原 base 不具 verbose API、13 个旧测试仍可用于既有公开开发命令的历史结果解释；card 中旧 actorpatch/verbose 缺席与 13 旧测记录只按不变公开 source 复用。本轮没有重验 actor 环境，不能从正式评分矩阵反推完整 solver 开发流程或交付。

## 事实／方案／停止条件

- **事实**：固定 R11 正式消费、完整候选→Frozen、195 个状态、迁移节点及关键拒绝归因均对齐；当前无新增 P0/P1 或具体 CPU 阻断。
- **更小方案与推荐**：保留已固定材料与既有语义边界，按本轮窄范围结束 CPU 复核。无需新增产品要求、状态机、拒绝 guard 或反例数量；没有依据要求重跑历史或全仓。
- **理由与代价**：关键旧 B1/B2/B3 在本次正式消费与 raw log 中已有对应证据。继续扩大测试会增加运行成本、拖延当前切片，且尚无会改变本轮结论的具体事实。
- **仍未知**：本轮未动态核 test-edit 候选，未复跑真实磁盘 patch engine、actor 工具环境或完整 solver，未核 GPU/probe/训练准入，也不声称全资源事实由本轮建立。这些限制不混入 CPU 功能成功结论。
- **停止条件已满足**：固定材料消费正确、原参考完整、全部预设完整候选正式结果与 raw 归因一致，且接受范围未出现当前具体误拒/漏判。仅有未运行的新能力或理论反例不构成本轮继续阻塞的理由；若后续出现与此固定 identity 不同的材料或具体生产回归，由对应切片另核。
