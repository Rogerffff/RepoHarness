# Conan 13403 R12 正式 CPU：非作者 Production Tracer 窄核

日期：2026-10-03。角色：非作者，GPT-6.1 Sol / high；依据根 AGENTS 与 review-standards §10.4/§10.5。本轮仅新正式 CPU 矩阵的生产消费/运行原件和已有 GNU actor 复用边界，不重审旧 41 矩阵、完整语义或修法，不运行远端、Docker、模型、实验或项目测试。唯一新增本报告，不改 task/board/shared 或历史证据。

**结论：本范围无阻断，停止于此。** 21 个完整候选经固定 R12 fresh prepare、FrozenPatch、受信投影和实际 grader，五个正例通过、十六个负例失败，与计划完全一致。1F/0P × 21 的完整原参考状态无 skip/missing；完整候选与冻结内容、GNU 前置、安装、真实退出及内外清理均闭合。289 件原件运输身份与原 job 完成 rc=0 已独立核实。资源未保存及旧 actor 复用范围如下，不扩为完整 solver、修复后的 GNU 端到端功能、GPU/functionality 或训练准入。

## 1. 原件与固定身份

仓库相对路径前缀：

- `C = runs/category2_repair_20260929/conan_cpu_20261003/`
- `S = C/formal_matrix_13403_r12_v2_evidence/formal_matrix_13403_r12_v2/`
- `R = runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/`
- `M = R/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan13403_test_patch_environment_v1/`

独立核 S 全部 289 个正式原件的文件集合、SHA256 和大小，与 remote audit 完全一致，无多件或缺件。release ID 为 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`；独立核 manifest 中 1020 个成员，均为普通非软链文件、SHA256 和大小完全一致。仅本题 registry/consumer/producer 与正式链路深读，不审其他题结果。

| 已核锚点 | SHA256 |
| --- | --- |
| `R/manifest.json` | `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987` |
| `C/formal_matrix_13403_r12_v2_remote_audit.json` | `dc1e451be99a5d67f4e7cbd61f872c6f0e78c99dd76e7fed51795c5ae0677568` |
| `C/formal_matrix_13403_r12_v2_audit.json` | `b931ba48ad058fb5befa4ec88c8c546c4ccf9d8bed72307bddd1678527157695` |
| `S/plan.json` | `cd0f373696dc6da32d0162144b31b9699cfc95fbbe9606a1a46a44b245589cfe` |
| `S/run_matrix.py` | `e952ee6106d4bb20a4292f74f4ccdb6e0418f66a9f9dc565a7da0dac670e3cee` |
| `S/matrix_results.json` | `b080ab2cd1ff9bf15ff99ac5e1cf008a17d75fafb14724d46b9a409a7f3bf3a7` |
| `S/publication_input.json` | `7d71131b5df041f8cbfa10eed727ed924cd5fe52feef124cc6a4b1d2cc3dd1ec` |
| `S/publication_receipt.json` | `3a3be261e1854aed276a591380758d150dff21a2dc3bfc9072dc3cfc528954fe` |
| `S/prepared/prepared_manifest.json` | `7905288b43fab17a3d0f0c2d8ff5e6e31d1177eb5c7b159050bdd14a51b4df25` |
| `S/prepared/replay_summary.json` | `658d6e85c33b7059963136b5cc0ebd1bd683ba8bc7ea640566db6431c3e9e516` |
| `S/prepared_identity.json` | `aa0008fc57bb6541812767bf4e5e7764bfae1b5a13f88a80d9b8ad6e9202c4f1` |
| `M/material_revisions.json` | `4b03ad86199522f4905c282c66c716971140e208c1963b8211850cc3ca711698` |

remote audit 到位后仅补核新增运输身份、job 与外层标签查询，未重开旧语义或旧矩阵。

## 2. Fresh prepare 与实际材料消费

release_verify / prepare 的真实 argv 与 returncode=0 均保存。fresh prepare 时间为 `2026-10-02T22:50:07.155514Z`，首候选开始为 `22:50:09.625868Z`。prepared manifest 的 prompts/rollout 文件 SHA 和 host grading 原件 SHA 全部重新计算相符。plan、prepared identity 与 `R/checks/consumer_combined_264.json` 本题项完全一致；未复用旧 private prepare 替代本批消费。

| 消费身份 | 实际值 |
| --- | --- |
| task / base | `swe_gym_lite::conan-io__conan-13403` / `55163679ad1fa933f671ddf186e53b92bf39bbdb` |
| revision | `conan13403-cloud-test-v4-gnu-v2` |
| effective test patch SHA256 | `2f55ba31f5823a411215b939e15a47b0eee346902941db5ca8b457730bb5a1c5` |
| parent grading digest | `sha256:87c4669a16d72b64d25f4edb4e9022e1647d4a8244e90c7cefb378fe2424bd8e` |
| grading bundle | `sha256:0a8aeebe928ddc6062f3bd6d0e498a0b0a2e89983bf9be4dc6ae5de9e9e16222` |
| materials identity | `sha256:0f73cdf9d521c865ffd7d7cb070f642581e7225b5d3bfd168832c72125b3a065` |
| environment package | `sha256:f95f864606a7117f670a815ab86071d91beb15de91e8001fcedf267cc53ad901` |
| public bundle | `sha256:0ed07332c3b10087f669e9345772ed5eddd316cab87621a95a1e38b38464374a` |

host view 的完整实际 test patch hash 与上表相符。固定 producer 对本题 registry SHA、普通文件、版本/base/public/原与有效 patch 身份做限定；prepared_task_face 构造本题专用 revision context，保留原 F2P 一项及原 P2P 空集，实际 diagnostics partitions 一致。只有 `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works` 一项正式参考，不新增参考、P2P 或其它语义。

## 3. 镜像、GNU 前置与完整候选冻结

登记 recipe `conan13403-gnu-v2`：source tag `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13403:latest`、source manifest `sha256:6c7a9b7d705ffab262c468fcd3dca87b3cbc6ba8c772ecce155699c30a71da84`、source config `sha256:dffa4bbcef5c3bae8ff2328524c4d70bebb0e6d45d6067ac064f12881987c383`；derived ID 为 `sha256:b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`。registry 与已有 reuse binding 的环境身份完全一致。

fresh prepared_identity 的实际 image inspect 命中登记 derived ID。逐份读取 21 个 `S/output/<id>/ledger.jsonl`（各一行），顶层 `image_id_actual` 全部为同一 `b40849…`，不是 null；image_ref/local_build_id 亦绑定该不可变 ID，image_local_build=true / image_manifest_digest=null。local-build 路径不是 source RepoDigest 实测；本批没有另存 21 份逐 grader 完整 inspect。

21 个 diagnostics 的 candidate_prerequisite 均 state=verified、UID/user=54322、exit_code=0、stderr 为空、stdout 含 `RH2_CONAN13403_GNU_PREREQUISITE_OK=1`；脚本 SHA256 `6c7421e5b9ae6226740d918b5eafbe2c7f48aa8810ec8f0294dad87de13360e6` 与 consumer 相同。固定脚本在 cwd `/`、隔离 testbed Python 下检查实际 UID、`/usr/bin/autoreconf` / automake / m4 可执行，调用 dpkg-query 核 Autoconf `2.71-2`、Automake `1:1.16.5-1.3`、m4 `1.4.18-5ubuntu2`。manager 以正式 UID54322 执行并保存结果；这证明本轮前置可用，不自动证明修复后的真实 GNU 端到端功能。

按 plan 指出的 20 份完整原 patch 读取，与 `S/candidates/<id>.patch` 和 `S/output/<id>/artifacts/.../candidate.patch` 逐字节相同、SHA 全部符合 plan。gold 原路径为 `runs/swegym_quality_expansion_20260925/private/conan-io__conan-13403/gold.patch`；其余为 `rh2/experiments/category3_cloud_20260929/conan13403/<id>.patch`。完整路径与所有 SHA 保留在有散列锚点的 plan；noop 无补丁。

20 个非空 FrozenPatch 都只含 `conan/tools/gnu/autotools.py` modify 的完整内容。每条解码后内容 hash 核实；依原完整 patch 每个 hunk 的上下文/新增内容逆还原，全部恢复同一 baseline SHA256 `3c73d9c29605bdef8eff4bec2400397271369efe53cab88b48beb49cf3fdf8c0`，与各 baseline manifest 相符。noop Frozen entries 为空。21 个 canonical Frozen digest 重新计算，与 artifact projection 和实际 ledger 一致；所有投影 included 路径精确等于冻结源码集合，无 ignored/unsupported，未遗漏候选文件或偷偷改用缩减 patch。

实际链为固定 `replay_grade.py run` → candidate sanitize / UID54321 原 patch check+apply → census/FrozenPatch/trusted projection → candidate 清理 → FrozenDeltaSource → `SWEGradingManager.grade(workspace=None)`。grader 独立 fresh checkout、基线重建、冻结内容应用，恢复受信测试并执行完整 pytest。当前 R12 的 driver/adapter/prepared_task_face/manager 和 producer 身份由 manifest 核实；本次仅相关分支窄读，不扩大 common 全实现重审。

## 4. 21 个完整原参考状态

实际命令 `pytest -n0 -rA conans/test/unittests/tools/gnu/autotools_test.py`。21 个 raw log 各有一个完整唯一参考 node：`conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works`。逐项与 ledger 原 F2P 分区对账；无 SKIP、ERROR、missing、unaccounted，段外解析 0。分母 1F/0P × 21，五个通过、十六个失败。

| 候选 | raw 状态 | 计划 / 实际 reward | pytest rc |
| --- | --- | --- | --- |
| noop | FAILED | 0 / 0 | 1 |
| gold | PASSED | 1 / 1 | 0 |
| runcwd | PASSED | 1 / 1 | 0 |
| oschdir | PASSED | 1 / 1 | 0 |
| r3_deferred_raise | PASSED | 1 / 1 | 0 |
| rv_retcode | PASSED | 1 / 1 | 0 |
| noenter | FAILED | 0 / 0 | 1 |
| relonly | FAILED | 0 / 0 | 1 |
| buildlit | FAILED | 0 / 0 | 1 |
| norestore | FAILED | 0 / 0 | 1 |
| mutate_source | FAILED | 0 / 0 | 1 |
| fallback | FAILED | 0 / 0 | 1 |
| swallow_run | FAILED | 0 / 0 | 1 |
| w_ignore_errors | FAILED | 0 / 0 | 1 |
| nofinally | FAILED | 0 / 0 | 1 |
| w_argsdrop | FAILED | 0 / 0 | 1 |
| w_twice | FAILED | 0 / 0 | 1 |
| w3_fallback_code | FAILED | 0 / 0 | 1 |
| w3_abs_swallow | FAILED | 0 / 0 | 1 |
| w3_fail_restore_build | FAILED | 0 / 0 | 1 |
| w3_code_norestore | FAILED | 0 / 0 | 1 |

不是只看奖励汇总：各原 log SHA 重算符合 ledger，完整参考 node 和分区 success/failure 一致；matrix_results 与每份实际 JSONL 逐条相同，并与 root audit 的 21 项 full_reference_states 对账。没有借旧 41 矩阵或材料作者自测来替代当前正式结果。

## 5. 安装、真实退出、清理与资源

21 个安装/测试 log 都保存完整分段和起止/rc 标记，RH2_INSTALL_RC=0；install_failed_commands 为空、install_skipped=false、segment completed=true、partial=false。实际 test exec rc 全为 0，pytest rc 如上表；零分由测试失败而非 infra/运输故障产生。实际导入 `/testbed/conans/__init__.py`、版本 `2.1.0-dev`、prefix owner PRE=54322，runner 前后 digest 一致。

21 份 run rc 都记录真实 argv / returncode=0，stage_error=null；final driver rows=1、halted/aborted=null、final_status.exit_code=0。candidate removed=true / rm:ok；每个 manager created_total=removed_total=1、containers_open/supply_open/cleanup_failures 为空。固定 candidate finally、grade finally、driver finally/manager.close 与实际内部计数闭合。

remote audit 保存 21 组外层精确 `rh2.run_id=conan13403-formal-r12-v2-<id>` 的容器与网络查询。逐组核 argv、标签、rc 和输出：全部 rc=0、stdout/stderr 为空。该查询与内部 candidate/manager 关闭分别核实，支持本批标签下无遗留容器/网络，不扩大为主机全局状态。

远端原 job supervisor PID 361274 / child PID 361275，`2026-10-02T22:49:55Z` 开始、`2026-10-02T23:47:30Z` 结束，status=finished / returncode=0。stdout 含 21 个 candidate_completed 后接 FORMAL_MATRIX_STAGE_COMPLETED，stderr 为空；本次没有重跑。

声明 grader profile 为 2 CPU、4 GiB、pids 512、shm 64 MiB、tmpfs 1 GiB、network deny_all、UID54322；21 条 `resource_facts=null`。实际 cgroup memory peak 为 317.273–320.363 MiB（代码按 1024² 换算，字段名 mem_peak_mb），全部非零、无 unavailable。未保存逐容器完整资源 inspect；不能将声明 profile 当作 CPU quota/使用量/实际并行度实测，也没有 GPU 观测。

## 6. 已有 GNU actor 的范围复用

实际既有 audit 名称为 `C/baseline_actor_13403_r5_gnu_v3_audit.json`（SHA256 `cabe6bbf21a1f7eb2caf313aa7efbfe3b3dd23ff097a37ae8caabe43a1867dd2`），依据 `C/actor_gnu_13403_r12_reuse_binding_20261003_v1.json`（SHA256 `c0b76ed8dc04d6cc70e1c525a5f0fec2bef73acec943539494e4d64bc047f647`）。本地核其 current registry、source actor audit、direct code scope 和两份既有独立报告 SHA 均匹配；current environment 与当前 registry 完全一致。direct code scope 三个当前 R12 devcheck/startup/sandbox 文件 SHA 与所存 old/new SHA 相同。

既有独立报告为同 reviews 目录的 `non_author_13403_gnu_actor_runtime_review_20261003.md`（SHA256 `717f463b8935babb449787d642d998a43155f4c88b0a4cdd391b3ca6cadd293a`）与 `non_author_13403_gnu_actor_scope_review_20261003.md`（SHA256 `b36b1bf29bc4d613726818c7b12b2a7f3a2e84fea3b6213c15e9302ca636fe7d`）。仅按其已验范围复用：固定派生 GNU 环境下 UID54321 的真实 Claude Code 公共 CLI 开发诊断，直接 GNU 成功、原 Conan autoreconf 缺文件错误可达。未重新打开旧 actor 原件全集或旧 41 测试，未补做传递依赖全代码比较。

旧 actor 是 controlled devcheck/桩安排命令，不证明首请求完整 issue/hints solver brief、修复后 GNU 执行、自主解题或全局权限。当前正式评分则证明本次一个受信参考的 21 候选矩阵；二者相互补充，但都不自动成为完整端到端 GNU 修复、functionality/GPU 或训练资格结论。

## 7. 停止条件

停止条件已满足：289 件运输身份、固定 release/consumer、新 prepare、20 份原完整补丁与冻结源码、21 个完整参考状态和计划奖励、GNU 前置/安装/真实退出、内部关闭及 21 组外层精确标签清理均闭合。未保存资源与旧 actor 复用限制已列明，无新增阻断，不扩大运行、旧语义审查或共享修改。
