# Conan 14177 R11 正式 CPU：非作者 Production Tracer 窄核

审查日期：2026-10-03。审查角色：非作者，GPT-6.1 Sol / high；依据根 AGENTS 与 review-standards §10.4、§10.5。本报告仅审本批正式运行的材料身份、实际消费、完整候选运输、评分原件和生命周期，不重新审查既有测试语义。

**结论：本范围未发现阻断。** 15 个完整候选经固定 R11 的 fresh prepare、候选容器、FrozenPatch、受信投影和真实 SWEGradingManager 完成正式评分；15 个奖励均符合 `plan.json`。13 个完整参考 × 15 次运行 = 195 个状态，均有原日志且与诊断一致，无缺失、跳过或段外解析。安装和 driver 均正常退出，候选容器、grader manager 与随后按精确 run label 的外层清理均闭合。此结论支持本题正式 CPU 运行链路验收；不扩展为实际 solver 完整题面交付、GPU/functionality、训练资格或完整资源配额实测结论。

## 1. 范围与证据锚点

以下使用仓库相对路径，前缀为：

- `C = runs/category2_repair_20260929/conan_cpu_20261003/`
- `S = C/formal_matrix_14177_r11_v1_evidence/formal_matrix_14177_r11_v1/`
- `R = runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe17_dask_conan_v1/`
- `T = docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_conan/tasks/conan-io__conan-14177/`

独立核对 `S` 全部 211 个正式原件的文件集合、SHA256、大小，与远端回收清单完全相符，无多件或缺件。独立核对 `R/manifest.json` 所列 980 个成员均为普通非软链文件，SHA256 与大小全部相符。仅以标准库读取、计算散列和解析日志/补丁；未调用远端、Docker、模型或项目测试，未执行 release 代码，也未改材料、共享文件或历史证据。

| 原件 | SHA256 |
| --- | --- |
| `C/formal_matrix_14177_r11_v1_remote_audit.json` | `81511492e83df8f7bb5aa79881d880b64b16e2befd28afa0958c36ec967bb10a` |
| `C/formal_matrix_14177_r11_v1_audit.json` | `88d3d5717c5e42ef03b6a51d56caacc94ea56c401be268a5003e62cb1e06f922` |
| `R/manifest.json` | `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9` |
| `S/run_matrix.py` | `80a8765bc9384f7a9495f7c7dfbf5637800bd8aede79ae75af27ee8205621313` |
| `S/plan.json` | `229d18c2a78b0b9357dbd60cdfc80ec6f90cb5b2995467d434e84fa8b84a39ed` |
| `S/matrix_results.json` | `b2b2eb5b8ac50c7861a002fbf359fd7cb3daee9da2f4b544756973dda82e2577` |
| `S/publication_input.json` | `44e1ab30fa5e9da1aa0f6f2e7d9747155ec42fde5636cfdcb3a2f7ba6f86ef73` |
| `S/publication_receipt.json` | `f924f7311cf082973e4afd57bccab472a38c1b7397eb4c95b4fb5045787fcceb` |
| `S/prepared/prepared_manifest.json` | `89c310ba0bbf6c53394fc8c9abaf98efd706141a851fa55b4e115b54d8f7317a` |
| `S/prepared/replay_summary.json` | `3bd1c6a08e30134dadb79238a0b558bd7c0a25e3e5afe13e641ed6d1bf41096e` |
| `S/prepared_identity.json` | `12fda0f90465acc60cc7f247375acd7e192616ebf4b88385204eacaa252744ad` |

读取了本题 `revision_plan`、`historical_integrity`、publication input/receipt 及允许的公开 base，仅用于当前材料的来源/分组边界。旧 actor 的 13 测试未重跑、未重新验收；旧记录中不同运行的测试计数不代替本批日志。13230、11594 已落账结果不在本次重审范围。

## 2. 固定材料和 fresh prepare 的实际消费

实际 release 为 `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`。`run_matrix.py` 在 prepare 前逐件验证 release 和 14 个非空候选，核 publication 原件 SHA；`release_verify.rc.json`、`prepare.rc.json` 均为 0。prepared manifest 时间为 `2026-10-02T21:58:04.389735Z`，位于本批作业开始之后、首候选开始之前。prepared 内部引用散列、host grading view、consumer checks 和 plan 身份逐项一致，未用旧 prepare 结果替代。

| 身份 | 实际值 |
| --- | --- |
| task / base commit | `swe_gym_lite::conan-io__conan-14177` / `b43eb83956f053a47cc3897cfdd57b9da13a16e6` |
| revision | `conan14177-cloud-test-v2-regroup-v1` |
| grading materials identity | `sha256:926d6baa95fad4532d8a85387c6fc9dbf0b05fc6b53d7ff4e7a8565428fe94a4` |
| grading bundle digest | `sha256:5c2724e58c3273ea2fa1ce509b6e2082e5338d45d58642997370e8943f426413` |
| environment package digest | `sha256:5a047601494efe2b4c4532ce0f48b74f9a2d72731c815c6fe66ed2a914eef6da` |
| public bundle digest | `sha256:05af9bfee3a1a190b43e1bdeb7b473800206bde44c583f5c1144743f3381776a` |
| effective test patch SHA256 | `ee614041a0b3579f99b561daf33a763a3fe567cd90bc64cb3df0bca6131d2d8c` |
| registry SHA256 | `cd218a8784db849d63bac185b529348795e23477e65b18893cdecfdcf0346ec3` |

consumer 对账入口为 `R/checks/consumer_combined_264.json` 的 14177 项；registry 位于 `R/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan14177_test_patch_v1/material_revisions.json`。正式 host view 消费完整有效测试补丁，最终 2 F2P / 11 P2P。`test_single_patch_description` 从原 F2P 移到 P2P，并在 `moved_p2p` 分区保留原来源，不计作新增参考；其余为原 2 F2P 与原 10 P2P。prepare 的 14177 专用 revision context 和实际 grader 诊断都保留此分区。

图像 tag 为 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-14177:latest`，固定 manifest digest 为 `sha256:e83f64f4a2761078dbd377548ff8be3f9402e65c3b3ef5a6117e4fcb6d841db8`。`prepared_identity.json` 保存本批实际 inspect 的 config ID `sha256:4ca5aeae4e588c89008e6ca335500ffa71aea77bd6eab0b7491d514534696bb0`，与 plan 相符；不是本地衍生构建。逐候选 ledger 的 `image_id_actual` 为 null，不能声称 15 个独立 config ID 均有 inspect 原件。固定 manager 的实际启动链会检查正在运行容器的 Image / RepoDigest，15 次均未产生 image identity 异常；这一代码与执行证据支持固定 manifest 消费，但不填补未保存的逐容器原始 inspect。

## 3. 完整候选到 FrozenPatch 和真实 grader

对 14 个非空候选分别核对 plan 所指原完整 `.patch`、`S/candidates/<id>.patch` 与运行 artifact `candidate.patch`，字节散列均一致。没有缩成片段、替换控制或只以合成断言评分。noop 无 patch，FrozenPatch 为空。

14 个非空 FrozenPatch 均只有 `conan/tools/files/patches.py` 的完整文件修改。解码每个 `content_b64` 并核内容散列；按原补丁的上下文和新增内容逐 hunk 逆还原，全部恢复同一基线文件 SHA256 `81639a4ac4e27b284342a881d7ec0caba83959cbf8e0ecad8d8e2a919240547e`。因此完整原候选与实际冻结源码相对应。pubcand 的第三 hunk 以唯一上下文匹配其实际位置，不能把 diff 行号当作不可偏移的内容位置。

逐次重新计算 FrozenPatch 的 canonical JSON digest，与 artifact projection 和 ledger 全部一致。受信投影精确包含上述单一源码文件，noop 不含路径；15 次 `ignored_paths` 和 `unsupported_shape_reasons` 均为空，无测试/fixture/conftest 候选改动进入此批。baseline manifest、classification、projection、FrozenPatch 和 stage 原件均保存于 `S/output/<id>/artifacts/`。

实际代码链为 `replay_grade.py run` → `adapters/slime/replay_grade.py` 候选 stage → sanitize / 原 patch check+apply（agent UID 54321）→ census / export / trusted projection → `FrozenDeltaSource` → `SWEGradingManager.grade`。manager 从独立干净 grader 容器重建基线、应用冻结内容和受信测试补丁后运行实际 pytest；不是在候选容器中把结果直接当 grader 成绩。以下固定代码均通过 release manifest 身份核对：

| `R/repo/` 内代码 | SHA256 |
| --- | --- |
| `rh2/scripts/replay_grade.py` | `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3` |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py` | `df9b26dc81938239dc4c45c5466c0b08c5505f4c724ba331e482862a3834c178` |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | `a2e9a955032989eed642e6057ebd2f47cc627c6afe3e1f1fc235bef95f0ec7ca` |
| `rh2/src/repoharness2/grading/manager.py` | `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e` |
| `rh2/src/repoharness2/grading/material_revision.py` | `88abc81970eb8896b00d03040163685a16cd6c02283319441b648ff25fd253f5` |

本次仅深读这些代码中与 14177 材料/正式 replay/manager 生命周期相关的路径，不扩为 common 实现重审。

## 4. 逐候选、逐参考原日志

正式命令为 `pytest -n0 -rA conans/test/unittests/tools/files/test_patches.py`。15 个原日志各含 13 个完整唯一 node；逐项与 audit `full_reference_states`、ledger 分区诊断对账。全部节点仅 PASSED 或 FAILED，没有 ERROR、SKIP、missing、unaccounted；`num_parsed_outside_segment=0`。195 是 13 个参考在 15 次运行中的状态数，不是 195 个不同测试。

| 候选 | 计划 / 实际 reward | F2P 通过 / 2 | P2P 失败 / 11 | pytest rc |
| --- | --- | --- | --- | --- |
| noop | 0 / 0 | 0 | 0 | 1 |
| gold | 0 / 0 | 0 | 1 | 1 |
| pubcand | 1 / 1 | 2 | 0 | 0 |
| probe_post | 1 / 1 | 2 | 0 | 0 |
| probe_abspath | 1 / 1 | 2 | 0 | 0 |
| probe_merged | 1 / 1 | 2 | 0 | 0 |
| probe_header | 1 / 1 | 2 | 0 | 0 |
| always_log | 0 / 0 | 0 | 0 | 1 |
| never_log | 0 / 0 | 0 | 0 | 1 |
| gold_log_only | 0 / 0 | 0 | 1 | 1 |
| print_only | 0 / 0 | 0 | 0 | 1 |
| output_verbose | 0 / 0 | 0 | 0 | 1 |
| probe_basename | 0 / 0 | 0 | 0 | 1 |
| probe_kwonly | 0 / 0 | 1 | 0 | 1 |
| probe_logonly_v | 0 / 0 | 0 | 0 | 1 |

各日志的 13 个完整参考均在 `conans/test/unittests/tools/files/test_patches.py::` 下：F2P 为 `test_multiple_with_version`、`test_multiple_no_version`；P2P 为 `test_single_patch_arguments`、`test_single_apply_fail`、`test_single_patch_type`、`test_single_patch_file_from_forced_build`、`test_base_path`、`test_single_patch_string`、`test_single_patch_extra_fields`、`test_single_patch_file`、`test_apply_in_build_from_patch_in_source`、`test_single_no_patchset`、`test_single_patch_description`。

五个正向候选均 13/13 PASSED。gold 与 gold_log_only 的失败恰为两个 F2P 加 `test_single_patch_description`；其 reward=0 是本批计划预期，不能依据 gold 名称改判。probe_kwonly 只通过 `test_multiple_with_version`，`test_multiple_no_version` 失败；其余七个零分候选两个 F2P 均失败、11 P2P 均通过。上述明细与原完整日志一致，不以总 reward 代替逐参考核对。

## 5. 安装、退出和双层清理

15 次原日志均保存完整安装/测试分段及起止标记，`RH2_INSTALL_RC=0`；ledger 的 `install_rc_last_command=0`、`install_failed_commands=[]`、`install_skipped=false`、segment completed=true、log partial=false。实际导入为 `/testbed/conans/__init__.py`，版本 `2.1.0-dev`，前置 prefix owner 为 UID 54322；runner 前后 digest 一致，`runner_integrity_changed=false`。测试 rc 与上表一致，外层 test exec rc 均为 0，零分来自实际测试失败，未被运输异常伪装。

所有 `run_<id>.rc.json` 都记录实际 driver argv 和 returncode=0；每个 stdout 最终记录为 rows=1、halted/aborted=null、final_status.exit_code=0。candidate stage 的 `cleanup.removed=true` 且步骤为 `rm:ok`。manager 每次 created_total=1 / removed_total=1，containers_open、supply_open、cleanup_failures 均为空，regrade_total=0。固定 driver 在 finally 调用 manager.close；manager grade 在 finally 清理自身 grader，实际累计计数与代码相符。

remote audit 另保存 15 组外层查询：每组使用精确 `rh2.run_id=conan14177-formal-r11-v1-<id>`，分别执行容器和网络查询；各 argv、rc、stdout、stderr 均保留，全部 rc=0 且输出为空。该证据与内部 candidate/manager 关闭分别核对，支持本批精确标签下无遗留容器或网络，不声称主机全局无其他作业资源。

远端原 job 保存 supervisor PID 276101、child PID 276102，`2026-10-02T21:57:51Z` 开始，`2026-10-02T22:38:56Z` 结束，status=finished / returncode=0；stdout 含 15 个 candidate_completed 和 `FORMAL_MATRIX_STAGE_COMPLETED`，stderr 为空。该单作业原件足以判断正式矩阵完成。交接提到的本地 SSH 255 是传输断开；本窄核允许原件没有该本地 SSH 原日志，因此不独立补证断开细节。不能用它覆盖远端正式 rc=0，也没有本次审查重跑。

## 6. 未保存范围、非阻断事项与停止条件

声明 profile 为 2 CPU、4 GiB memory、pids 512、shm 64 MiB、tmpfs 1 GiB、network deny_all、grader UID 54322。15 条 ledger 的 `resource_facts=null`；保留 profile 不是逐容器 CPU quota、memory limit、网络 namespace 或实际并行度测量。现存实际资源观测为每次 cgroup `memory.peak`（固定代码按 1024² 换算，字段名 `mem_peak_mb` 实为 MiB），范围 326.145–327.336 MiB，全部非零且无 unavailable。未保存完整资源 inspect 与 GPU 指标；若后续决策要求这些实测，须另提供相应原件，不能从声明反推。

旧公开 actor 证据的复用主张只能限定在未变 public/source/vendor 条件；本报告没有重审该 actor 或证明其全 solver 题面交付。publication 中 maintenance 测试计数也未在此重跑。GPU/functionality 和训练准入需各自独立证据。

本范围停止条件已满足：固定身份一致，完整候选与冻结内容一致，15 次计划判定一致，195 状态完整，实际安装/driver 退出与双层清理闭合，未保存的资源和 actor 范围已明确。无须扩大运行或重审旧语义；本批无新增阻断项，停止于此报告。
