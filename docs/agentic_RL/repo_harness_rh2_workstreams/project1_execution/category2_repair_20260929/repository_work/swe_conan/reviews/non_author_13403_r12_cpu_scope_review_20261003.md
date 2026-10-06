# Conan13403 R12 正式 CPU 语义与范围窄核

2026-10-03。非作者 Falsifier / Simplifier；本批指定 GPT-6.1 Sol / high。按根 AGENTS.md、review-standards.md §10.4/10.5 执行。本次已获准读取私有 CPU 材料，**不是干净公开盲读**；不改写已有公开或 GNU 开发审查。

**结论：新增 R12 正式 CPU 切片未发现真实新增 P0/P1/P2 或具体阻断，满足本次停止条件。** 21 个完整候选的 Frozen 内容、可信投影、raw 单参考状态与正式报告相符；五个正对照通过，十六个负例为 0。固定 v4 原字节与 GNU 派生身份被实际消费。后到的 289 文件运输与 21 组 owned label 清理原件也已核对。该结论不证明模型首请求已交付完整 issue/brief，不建立完整 solver 成功、GPU probe 或训练资格。

## 范围与复用

仅本地只读新矩阵、必要可信材料及已有适用报告；另用标准库进行 JSON、SHA/大小、AST/补丁内容及日志检查。未访问远端、运行 Docker/项目测试/实验或模型，未重开历史 41 矩阵，未修改材料、共享文件或旧 evidence；仅新增本报告。

本次读取入口（均相对仓库根）：

- `runs/category2_repair_20260929/conan_cpu_20261003/formal_matrix_13403_r12_v2_evidence/formal_matrix_13403_r12_v2/`：plan、publication input/receipt、prepare/readback 原件、prepared identity、host grading view、20 原补丁、21 份账本与 raw log、Frozen/projection/classification/stage/diagnostics、run_matrix.py。
- 同 runroot 后到的 `formal_matrix_13403_r12_v2_remote_audit.json`、`formal_matrix_13403_r12_v2_audit.json`。汇总是索引，关键结果另核完整原件。
- 固定 R12 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/`：manifest、consumer_combined_264.json 仅 13403 行、repo 内本题 material/environment registry 和相关正式 prepare/replay/manager/projection/parser 代码。
- 本包 `tasks/conan-io__conan-13403/` 的 card、revision_plan、publication_request_20261003_v1、effective_test.patch/py、solver_brief_20261003_v1。
- 公开 `runs/swegym_quality_expansion_20260925/public/conan-io__conan-13403/` 的 issue 及用于补丁字节核对的 base。
- 既有 `reviews/non_author_material_review_20261003.md` 的 13403 适用段；`reviews/non_author_13403_gnu_actor_scope_review_20261003.md`、`reviews/non_author_13403_gnu_actor_runtime_review_20261003.md` 的窄 GNU/actor 结论。
- 既有云端 `category3_diagnosis_20260929/tasks/conan-io__conan-13403/review.md`、`review_v3.md` 的相关边界/停止条件及 result.md 的 v4 说明。只用于复用固定 v4 行为语义，不将历史私有复跑或正式诊断重新计成本轮运行。

## 固定材料与 consumer

R12 release ID 是 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`，manifest SHA `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`、成员数 1020。独立核 manifest SHA、相关消费源码与本题材料/env 成员的 SHA/大小；读取保存的 release_verify rc0、1020 成员 readback 输出，未在本机扩审其它题成员。

publication_input 与本题固定 request **字节相等**。release 的本题 consumer 与 plan、prepared_identity 完全相等；实际 runtime 是 plan 固定的 runtime_cpu_v2 Python。v1 宿主 Python 缺 pydantic 的前评分失败保留为历史，不把本次 v2 成功覆盖到它，也不补计候选分数。

实际 registry 是 `repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan13403_test_patch_environment_v1/material_revisions.json`，SHA `4b03ad86199522f4905c282c66c716971140e208c1963b8211850cc3ca711698`，与账本一致，revision 为 `conan13403-cloud-test-v4-gnu-v2`。它保留原 patch SHA `e6811f47541fa7dd41f6434ff4009fe19af3f0a524856d7e1ae3679f7fa7d433`、父 grading 与公开身份，操作为 `replace_test_patch_preserve_refs`。

有效 v4 patch SHA `2f55ba31f5823a411215b939e15a47b0eee346902941db5ca8b457730bb5a1c5` 与工作包、release、host grading test_patch 对应；有效测试文件 SHA `cfb230e0bb59acd19158fc0460b3e718e94122b743ebcd2fafe34fd01011df90`。在公开 base 上按上下文内存应用完整有效 patch，结果与 effective_test.py 字节相等。release 中公开 actor test snapshot 仍是原 base，不把它误当新私有评分文件。

原与现参考数组严格相等：仅 `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works` 一个 F2P、P2P 为空。host 及每份正式 partition 均实际消费 **1F／0P**，没有增加节点、重分组或删参考。材料 identity 为 `sha256:0f73cdf9d521c865ffd7d7cb070f642581e7225b5d3bfd168832c72125b3a065`。

prepared identity 与 21 份账本的实际 image_id 都是固定 GNU config `sha256:b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`。正式 image binding 只接受登记的 source identity 或该 derived identity，构造时切到派生 image；每次 candidate prerequisite 在 UID54322、可信 cwd `/` 下核 Autoconf/Automake/M4 固定包版本与可执行入口，21 次 state=verified、rc0、stderr 空。这证明前置条件已满足；该检查自身不是正确修法的真实 GNU 功能测试。

## 完整候选与正式状态

20 份非空原候选都只改生产 `conan/tools/gnu/autotools.py`。逐份核原 stage patch SHA、artifact candidate.patch 字节；按唯一上下文将**整份补丁**在公开 base 内容上内存应用，所得完整文件与 Frozen decoded content/content_digest 相等。20 个正式投影均仅包含该生产路径，无忽略项或 unsupported shape；noop Frozen/projection 为空。21 个 classification 均 projectable，测试样路径为空，runner_integrity_changed=false。没有用源码摘录、候选名称或预期 reward 代替实际输入。

正式路径是 run_matrix.py → 固定 replay CLI → 完整候选 apply/freeze → trusted projection → FrozenDeltaSource → manager.grade。expected_reward 只作运行后断言，未进入 parser 充当结果。绑定 parser 为 `swegym_parsers@242429c1`，仅解析正式标记段。

21 份 raw pytest summary 都仅有上述单参考，状态与 partition/report 逐项相等；root audit 的每份 log SHA 与本地 raw log、完整 reference_states 也相等。全部参考缺席/跳过/未记账为空，num_parsed_tests=1；所有 candidate installation 末命令 rc0，没有 stage_error。正例 pytest rc0，负例 pytest rc1 且归 `tests_failed`，没有把下列候选异常或断言失败误记为环境失败。

| 完整候选 | reward | raw 拒绝点或接受行为 |
| --- | ---: | --- |
| noop | 0 | 不接受 build_script_folder 的 TypeError |
| gold | 1 | 所选目录、一次调用、保留失败及恢复 cwd |
| runcwd | 1 | `run(cwd=...)` 合理替代 |
| oschdir | 1 | 直接 os.chdir + finally 合理替代 |
| r3_deferred_raise | 1 | 恢复目录后重新报错；不锁异常链 |
| rv_retcode | 1 | ignore_errors 取非零码，再恢复并报错 |
| noenter | 0 | 仅构造 chdir context，命令实际仍在调用者 build 目录 |
| relonly | 0 | 将绝对 build 路径拼到 source 后；错误路径 FileNotFoundError |
| buildlit | 0 | 只特判 build，其他绝对目录仍被错误拼接 |
| norestore | 0 | 成功后 cwd 未恢复 |
| mutate_source | 0 | recipe 的 source_folder 被改动 |
| fallback | 0 | 所选目录不存在却回退 source；缺预期异常 |
| swallow_run | 0 | 命令失败被吞掉；缺预期异常 |
| w_ignore_errors | 0 | 忽略非零码而不报错；缺预期异常 |
| nofinally | 0 | 失败后 cwd 未恢复到原调用者 root |
| w_argsdrop | 0 | 所选目录下丢失原工具链参数 |
| w_twice | 0 | 命令被调用两次 |
| w3_fallback_code | 0 | 失败后另到 source 重跑；失败执行记录多一次 |
| w3_abs_swallow | 0 | 绝对目录失败只返回非零码；缺预期异常 |
| w3_fail_restore_build | 0 | 失败恢复到 build，而非原调用者 root |
| w3_code_norestore | 0 | 非零码分支报错前未恢复 cwd |

所有 replay driver/process rc 都是 0，表示本次编排及预设结果断言完成；**不等于所有候选 pytest 成功，更不等于 solver 修复成功**。五个正例与十六个负例的原始 test rc 已分别核对。

## 拒绝范围与旧证据的有效边界

本次接受 cwd、os.chdir、deferred-raise、retcode 四个合理替代及 gold；没有重新引入“必须用 chdir”“必须是固定异常类型/文案/异常链”等旧误拒。v4 只按已定行为核所选目录、命令一次执行、错误如实传出及调用者目录恢复；上述 reject 点与该范围相符。失败场景仍覆盖缺省、相对和绝对目录，不因全部 run_error 都失败而放过换目录重试。当前没有已知合理替代被误拒，也没有本次负例漏判。

v4 使用 run 记录器，故此正式矩阵核目录/参数/次数/错误语义，**不等于 21 个候选都用真实 GNU 生成了 configure**。新正式 GNU prerequisite 与原 GNU actor v3 属于不同层证据，不能相加为功能成功次数。

旧两份 GNU 独立报告按其不变身份复用：source 内容和 Python 包版本清单未变；UID54321 的固定 v3 公开诊断里，直接 GNU 与 Conan install 成功，而显式 profiles 的 Conan build 到达目标 autoreconf 后因 source 没有 configure.ac 返回 1，外层诊断 wrapper 因预期失败已观察到而返回 0。这是原 cwd 缺陷的开发基线证据，不能写成修复成功。v2 缺 profile 与 v1 缺工具不是原缺陷；本轮不重跑或改写它们。

public brief v1 提供 GNU 入口、testbed Python、公开测试命令和 profiles 前置判读；现有 GNU v3 环境身份可复用其适用范围。但本轮正式 prepare/矩阵不能证明该 brief 已在求解模型首请求中交付，也不能把固定工具桩开发诊断扩大为自主 solver。

正式可信投影排除显式官方测试控制面改动，其余候选路径保留；`test_globs=()`、测试样路径只作观测。manager Frozen hygiene 核实际重放子集，旧 diff 文本的“改测试自动降 0”分支不作为本轮结果依据。**本矩阵没有 test-edit 候选，只有静态消费链确认，不能冒称动态验证该分支。** 本次不恢复 legacy 自动 0，也不为此增加新试验。

## 后到运输与清理原件

在远端 inventory/cleanup 原件到位前，只接受本地内容核对与账本 removed 字段，没有先宣布完整运输或外部清理。到位后重新核 `formal_matrix_13403_r12_v2_remote_audit.json`：289 个登记文件的本地 SHA/大小全部相符；job status=finished、returncode=0、stderr 空，stdout 逐项记录 21 完成及最终 stage completed。21 组精确 owned run label 的容器/网络查询均 rc0、stdout/stderr 空，与候选账本清理 removed=true 相符。

这是对本次回收原件的静态核对，不是重新查询机器，不声明无标签对象或其它作业的状态。root audit 的 21 raw SHA/状态/reward 与独立提取一致；其资源口径仍仅声明政策与 retained memory peak，不扩大为完整逐容器资源事实。

## 事实／选项／推荐／停止条件

- **事实**：固定 v4、GNU identity 与正式 consumer 对齐；20 整份原补丁到 Frozen 加 noop、21 raw 单参考、五正十六负、真实 test rc 与拒绝点均核对；289 运输文件及21 owned label 查询已核。本次没有真实新增 finding。
- **更小方案与推荐**：保留已固定材料及接受/拒绝范围，完成本切片 CPU 复核后停止。没有依据新增假想保护层、拒绝 guard、平台、反例数量或重跑 41 历史矩阵。
- **理由与代价**：旧 v4 根因写法已收口，新正式消费与关键合理/错误代表一致。扩大运行会增加环境漂移、资源成本与主线延误；当前没有会改变本结论的具体事实。
- **仍未知**：完整 solver 首请求 issue/brief 交付、自主求解及完整补丁交付、正确候选真实 GNU 端到端表现、test-edit 动态分支、GPU probe 和训练准入均未由本报告建立。它们属于对应后续范围，不把正式 CPU 合格直接提升为这些结论。
- **停止条件已满足**：新增固定 CPU 材料消费、全候选字节、实际异常/rc、原参考完整、合理替代接受及本作业运输/清理证据无具体矛盾。尚能设想额外反例或平台不构成本轮继续阻塞的理由；后续如变更固定身份或出现具体生产回归，再由对应切片核查。
