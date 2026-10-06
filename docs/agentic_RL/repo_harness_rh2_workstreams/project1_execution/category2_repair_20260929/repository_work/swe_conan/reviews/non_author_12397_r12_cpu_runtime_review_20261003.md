# Conan 12397 R12 正式 CPU：非作者 Production Tracer 窄核

日期：2026-10-03。角色：非作者，GPT-6.1 Sol / high，按根 AGENTS、review-standards §10.4/§10.5 审查本批正式生产消费和结果。仅本地读取新正式原件与相关固定代码；不重审既有材料语义、旧矩阵或旧 actor 测试，不访问远端、不运行 Docker、模型或项目测试。唯一新增文件为本报告。

**结论：本范围无阻断。** 固定 R12 fresh prepare 后，noop / gold / objcpp_only / apple_only 四个完整候选经过真实 FrozenPatch、受信投影与独立 grader；奖励 0/1/0/0 与计划一致。2 F2P + 2 P2P × 4 次 = 16 个完整参考状态，全部原日志与诊断对账。完整补丁与冻结内容一致，安装和 driver 退出正常，候选/manager 清理与精确 run label 外层回执均闭合。停止于正式 CPU 结果验收，不据此宣称完整编译/链接路径、首请求完整 solver brief 交付或训练准入。

## 1. 原件范围和身份

仓库相对路径前缀：

- `C = runs/category2_repair_20260929/conan_cpu_20261003/`
- `S = C/formal_matrix_12397_r12_v1_evidence/formal_matrix_12397_r12_v1/`
- `R = runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/`

独立检查 `S` 的 68 件正式原件：文件集合、SHA256 和大小全部符合 remote audit，无多件或缺件。独立检查固定 release manifest 的 1020 成员：均为普通非软链文件，SHA256 和大小全部一致。未用根核结论代替这些核对。

| 原件 | SHA256 |
| --- | --- |
| `C/formal_matrix_12397_r12_v1_remote_audit.json` | `a8d095268d0e49d829c618e07482bf04b12207e76445bf1ffc36ecbd3924a0b9` |
| `C/formal_matrix_12397_r12_v1_audit.json` | `28aafb6c3dbc356207a326421263be95d0222b285c6d42fe8b877a468bcba941` |
| `R/manifest.json` | `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987` |
| `S/plan.json` | `fc636b5eac85c535939496a3c199249bc4dac5e97e67254683a3b45106a3ac78` |
| `S/run_matrix.py` | `e952ee6106d4bb20a4292f74f4ccdb6e0418f66a9f9dc565a7da0dac670e3cee` |
| `S/matrix_results.json` | `4100a1c5db827f02cff8efb705476d6ca0367faaa780c795b3df97571b4e2077` |
| `S/publication_input.json` | `a6484900f98ca242066a4529fc6c69ff959616ed26e3d491c6b29a19fa29b251` |
| `S/publication_receipt.json` | `b4d8731dc572d10d1c38558826aa64d69407a4648b697cf0a862db4447c48a96` |
| `S/prepared/prepared_manifest.json` | `0a5777c69b379649d09601f7fafa19768232f9e489d6a574367a20e8d04c7521` |
| `S/prepared/replay_summary.json` | `84792dd028257f89a445a7dea9afaa147f3ff831c53c016ca9729402767e3cd4` |
| `S/prepared_identity.json` | `4b6b785d367045aa968fb5891d1ab8522c2866b405454f1c83c41254251ec58d` |

只深读 12397 registry/producer、正式 replay 和实际 manager 消费链；release 其他题的成员仅做身份完整性核对，不审其他题结果。

## 2. Fresh prepare、source 镜像与材料消费

release ID 为 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`。`run_matrix.py` 先逐件核 release、publication 和候选散列，实际 `release_verify` / `prepare` returncode 均为 0。fresh prepare 时间为 `2026-10-02T22:30:24.934732Z`，在本批 job 开始后、首候选 `22:30:27.769845Z` 前；prepared manifest 所引公开/host 原件散列全部核实。

plan、prepared identity 与 `R/checks/consumer_combined_264.json` 的本题项完全一致。正式材料为 `conan12397-private-test-v1`：完整替换受信 test patch、保留原 Apple F2P / 两个原 P2P，增加 Linux F2P；诊断分别保存 `original_f2p`、`original_p2p`、`added_f2p`，无来源混计。

| 消费身份 | 值 |
| --- | --- |
| task / base | `swe_gym_lite::conan-io__conan-12397` / `883eff8961d6e0d96652f78e3d7d3884479e769e` |
| effective test patch SHA256 | `7352a2fd18bcaccaa5e35ae5746b2b8a87725fa40c48972adb3b8647c8335e0b` |
| registry SHA256 | `dac2ff528a751e94b73e942d4a8f8f504b7cf931191a163a4bd8bce8ed409013` |
| materials identity | `sha256:7b653025a36ffb5e389cc0b1d98c5683d2f5974a4985468fc3a56d26475ffbe4` |
| grading bundle | `sha256:ac629d6d493f6bbbd82a429694397a66e83517da617d1487b9a0fca008d89c43` |
| environment package | `sha256:da099ad56c0f5fc10f7b4618ddd28cabaa6d995cbfe11214b7c072b2fde9e719` |
| public bundle | `sha256:d527da308594c085e47b77960326a0c1efca1d30180cb2ff0d38fe12a2fab593` |

registry 为 `R/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan12397_test_patch_f2p_v1/material_revisions.json`。固定 producer 对本题 base/public/parent grading/原与有效 patch hash 做字面量约束，读取 registry 的固定 SHA 与普通文件属性；host grading 实際 test patch 字节 hash 与上述值相同。prepared_task_face 生成 F2P context、安装/测试脚本和材料身份，实际 run 在该 fresh prepared summary 上消费。

本题仍使用 source 镜像 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-12397:latest`，manifest 为 `sha256:b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55`，非衍生本地镜像。prepared identity 保留本批 image inspect 实际 config ID `sha256:d0b6f915791c8c4597dffc2642093dfdc864a90f122544b23561e09ad6ba90a1`，与 plan 相同。四个 ledger 的 `image_id_actual` 均为 null；固定 manager 会检查运行容器 Image 与 RepoDigest，四次均无身份异常，但未保存四份逐容器 inspect 原件。

12397 没有进入其他 Conan 题的 derived-image/prerequisite 分支，`candidate_prerequisite_script_sha256=null`，不能把 plan.scope 中泛化的 prerequisite 描述当成本题执行了额外工具验证。实际使用原 vendor 安装和 UID 54322 测试路径，没有增加虚构的 Ninja/CMake/编译工具配方。

## 3. 完整原补丁与 FrozenPatch 对应

按 plan 原路径读取 gold、objcpp_only、apple_only 的完整补丁；与 `S/candidates/<id>.patch` 和 `S/output/<id>/artifacts/.../candidate.patch` 字节一致。原路径和散列为：

| 候选 | 原完整补丁路径 | SHA256 |
| --- | --- | --- |
| gold | `runs/swegym_quality_expansion_20260925/private/conan-io__conan-12397/gold.patch` | `a2601a41c874af2aff7fb7a867d381af14ee7f0e63844e172ad6d3dd4a52c457` |
| objcpp_only | `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_conan/tasks/conan-io__conan-12397/objcpp_only.patch` | `5dae45b86c3e9d4848c2ba0cfea13a9f96f6c12366e2ae70761cf0226c52ad5e` |
| apple_only | 同上任务目录的 `apple_only.patch` | `b53ab66a1c8a279d8e75aa0324dad1f45eab231c6986fafebb8528514c6b6820` |

三个非空 FrozenPatch 都只修改 `conan/tools/meson/toolchain.py`，含完整文件内容。逐一解码并核 content digest；用原完整补丁逐 hunk 的新增/上下文逆还原，三个文件均恢复相同基线 SHA256 `0ef440c35a0aced3c9846a5ef35eeaa380599c891e467a3ee274d4e88c8e999e`，与各 baseline manifest 相符。noop 的冻结 entries 与投影路径都为空。

四个 FrozenPatch 的 canonical JSON digest 均重新计算并与 artifact projection / ledger 对账。三个非空投影精确包含上述源码文件，四次 ignored/unsupported 均为空；没有候选测试、fixture 或 conftest 修改进入评分。所有相关 baseline/classification/projection/Frozen/stage 原件都保留。

真实执行链是候选 stage sanitize → UID 54321 原补丁 check/apply → export/FrozenPatch/trusted projection → 候选容器关闭 → `FrozenDeltaSource` → `SWEGradingManager.grade(workspace=None)`。manager 校验 frozen binding，在独立 fresh grader 上核镜像、clean checkout、基线重建，再应用冻结源码和受信测试补丁，运行完整 pytest。不是把候选容器上的输出直接当最终分数。

本次读取的固定链路代码散列（均在 `R/repo/` 下）：

| 路径 | SHA256 |
| --- | --- |
| `rh2/scripts/replay_grade.py` | `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3` |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py` | `7cb03bfd1a6ddcb4238f54d2a19d30d4e3e93a56ad630b81e8fb05ac031160fb` |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | `a96c46bb2ada9c84e92de6b48b41dc3b0292bb1029946081b10e235433e1a619` |
| `rh2/src/repoharness2/grading/manager.py` | `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e` |
| `rh2/src/repoharness2/envpack/swe_material_revisions.py` | `7efd19c648b0b479c1b439df6570fe726707a2117fed8ce45d15c95dec1ce3bc` |

## 4. 16 个完整状态和独立拒绝点

命令为 `pytest -n0 -rA conans/test/integration/toolchains/meson/test_mesontoolchain.py`。下表参考均使用此前缀的完整 node ID：A=`test_apple_meson_keep_user_custom_flags`（原 F2P），L=`test_linux_native_clang_libcxx_link_args`（新增 F2P），Q=`test_correct_quotes`、E=`test_extra_flags_via_conf`（原 P2P）。四份原日志各有四个完整唯一 node；PASSED/FAILED、分区诊断和 audit full_reference_states 逐项一致。

| 候选 | A | L | Q | E | 计划 / 实际 reward | pytest rc |
| --- | --- | --- | --- | --- | --- | --- |
| noop | FAILED | FAILED | PASSED | PASSED | 0 / 0 | 1 |
| gold | PASSED | PASSED | PASSED | PASSED | 1 / 1 | 0 |
| objcpp_only | FAILED | FAILED | PASSED | PASSED | 0 / 0 | 1 |
| apple_only | PASSED | FAILED | PASSED | PASSED | 0 / 0 | 1 |

四次都无 missing/skipped/unaccounted/ERROR，段外解析为 0。原日志中 objcpp_only 的 Apple 拒绝点是实际 `cpp_args` / `cpp_link_args` 中缺少 `-stdlib=libc++`，Linux 拒绝点是 `cpp_link_args=[]`；apple_only 通过 Apple 后，仍在 Linux 的 `cpp_link_args` 断言被拒绝。因此新增 Linux 参考确实独立拒绝只覆盖 Apple 的候选，不能用 Apple 已通过替代全部 F2P。这里仅核实际断言落点及状态，没有重审已有测试设计。

## 5. 安装、真实退出、内外清理

四条 ledger 与各自原 `ledger.jsonl` 完全一致。四份完整 eval log 都有安装/测试起止和 rc 标记，`RH2_INSTALL_RC=0`；install failed commands 为空、未跳过安装、segment completed=true、partial=false。测试 exec rc 都为 0，实际 pytest rc 如上表，零分由测试失败产生而非 infra。源码导入 `/testbed/conans/__init__.py`，版本 `1.54.0-dev`；prefix owner PRE=54322，runner 前后 digest 相同，runner_integrity_changed=false。

四个 `run_<id>.rc.json` 保留真实 argv 与 returncode=0；stdout final record 的 rows=1、halted/aborted=null、final_status.exit_code=0、cleanup failures 为空。四个候选容器均 `removed=true`、`rm:ok`。四个 manager 均 created_total=removed_total=1，containers_open/supply_open/cleanup_failures 为空；代码的 candidate cleanup、grade finally 和 driver finally/manager.close 与实际记录闭合。

remote audit 的四组外层查询分别使用 `rh2.run_id=conan12397-formal-r12-v1-<id>`，容器与网络 argv 精确保留；每项 rc=0、stdout/stderr 为空。此证明限于本批各标签资源，不扩为主机全局资源状态。

job 原回执为 supervisor PID 332877 / child PID 332881，`2026-10-02T22:30:12Z` 开始，`2026-10-02T22:41:01Z` 完成，status=finished、returncode=0。stdout 四个 candidate_completed 后有 `FORMAL_MATRIX_STAGE_COMPLETED`，stderr 为空。本审查没有重跑。

## 6. 资源与旧 actor 复用边界；停止条件

声明 profile 为 2 CPU、4 GiB memory、pids 512、shm 64 MiB、tmpfs 1 GiB、network deny_all、UID 54322。四次 `resource_facts=null`，未保存完整容器资源 inspect；不能据 profile 宣称配额/CPU 使用量/实际并行度已测。实际 cgroup peak 为 noop 348.785、gold 348.203、objcpp_only 349.910、apple_only 349.168 MiB（代码按 1024² 换算，字段名为 `mem_peak_mb`），均非零、无 unavailable。未保存 GPU 或完整编译/链接实测。

只按既定范围读旧 `C/baseline_actor_12397_r5_v1_audit.json`（SHA256 `f079b4a23dced9f2ceb740d7a0e9d17d00c466f88ae4af37e459e889b3283ae4`）和 `C/actor_r5_r12_reuse_code_scope_20261003_v1.json`（SHA256 `e870a55bf68916a91a36aacb4975c3f9f3d19895799e89d06d22f081fa3c46ba`）。后者三个 direct devcheck/sandbox/startup 路径的当前 R12 SHA 与回执 old/new SHA 相同，已本地核对；旧 release 的原件未扩读或重新运行。旧 actor 只记录公开 source base 的配置生成和原三项测试，明确没有 compiler/Meson/link 执行，也非完整 issue/hints solver 首请求交付；其两个 generic marker 检查为 false，不能转述为全局权限验收。publication 的维护测试声明也未在本审查重跑。

本次新正式 CPU 成绩与该旧 actor 范围分别成立：前者验证新材料真实评分，后者仅按既有回执复用 source 公开开发探针；都不自动满足完整工具链交付或训练资格。plan 中泛化 prerequisite 文案与本题实际 null 字段的差异已按执行代码澄清，为非阻断记录。

停止条件已满足：固定身份、新 prepare、原完整候选/Frozen 对应、16 个参考状态、计划奖励、实际安装/退出与内外清理全部闭合；资源和旧 actor 未验证部分已如实列出。无新增阻断，不扩大运行、旧语义审查或共享修改。
