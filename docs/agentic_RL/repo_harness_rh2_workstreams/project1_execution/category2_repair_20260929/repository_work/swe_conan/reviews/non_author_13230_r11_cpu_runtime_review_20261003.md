# Conan 13230 R11 正式 CPU：非作者 Production Tracer 窄核

整理日期：2026-10-03。角色：非作者 Production Tracer；范围按 review-standards §10.4/§10.5。只读取本机固定代码与回收原件，执行静态 JSON、SHA、补丁及日志对账；没有访问远端、运行 Docker、模型或旧测试，没有修改材料和共享实现。本文只核 **13230**，没有核 14177。

## 结论与停止条件

**13230 的 R11 v2 三候选正式 CPU 重放证据成立，本范围未发现阻断项。** 已证明 fresh prepare → 原完整候选 → FrozenPatch → 可信投影 → fresh 真实 grader → 完整参考判定 → manager 关闭的链路。noop/gold/android_only 的 reward 为 0/1/0，均没有 infra、缺参考、skip 或日志截断。

足以将本题记为“R11 新材料正式 CPU 三候选验证完成”，并停止本批运行链路窄核。此结论不授予正式训练资格，不证明模型能求解，也不证明 14177。资源完整实测、当前远端 daemon 状态及新 actor 全题面交付均不在本证据覆盖范围；不能把它们描述为已验证。只有原件身份变化、参考不完整、退出/清理出现矛盾，才需要重新打开本批链路核查；能够继续设想未触发异常不是继续阻断的理由。

## 原件与身份

以下前缀仅为阅读缩写，都是仓库相对路径：

- `C` = `runs/category2_repair_20260929/conan_cpu_20261003/`。
- `S` = `C/formal_matrix_13230_r11_v2_evidence/formal_matrix_13230_r11_v2/`。
- `R` = `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe17_dask_conan_v1/`。

独立逐文件重算：S 全部 **55/55** 文件的 SHA256 和字节数与 `C/formal_matrix_13230_r11_v2_remote_audit.json` 一致，没有未列文件；R/repo 全部 **980/980** manifest 成员的 SHA256/大小一致，均为文件且非 symlink。R/manifest.json SHA256 为 `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9`；release 为 `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`。

| 原件 | SHA256（文件内容） |
| --- | --- |
| C/formal_matrix_13230_r11_v2_remote_audit.json | `45c765ef5760760f550ab46c8d3adbaecfbdc353418ce22e241679d35d8f8c9d` |
| C/source_alias_r11_and_initial_failure_remote_receipt.json | `d709626ac6603f9cbb4beb1f7dba35fb8739716d741b5d4793f9f88e5b4c3c40` |
| S/run_matrix.py | `80a8765bc9384f7a9495f7c7dfbf5637800bd8aede79ae75af27ee8205621313` |
| S/prepared/prepared_manifest.json | `59372c86fda5c3b0f4ee7f11ba20e8a29eb74b0d4e06a6f67b6a25c08e32008a` |
| S/private/host_grading_views.jsonl | `7a314a5c982419d32a8661685e4af420c4093042d4821316a5996520b02f2f4a` |
| R/checks/consumer_combined_264.json | `68b62c8ef6c9c21374769d2e91981193be689b901277cc294d5665611aa6ad9f` |
| R/checks/consumer_parent_264.json | `c9f0b9c28a4e1257ed80d21d8d4e06473b29912e60ffa0a5cd868e805cc535ee` |

S/plan.json 的 consumer_identity 与 R/checks/consumer_combined_264.json 本题条目逐字段相等。fresh host view 的有效 test_patch SHA256 为 `15834b7e16c8fac6c5386c5ebf1f6ad1df9ad56c67af1c87df6a178f6e374db1`；test_patch 触碰且只触碰该 autotools 测试文件。材料身份为 `sha256:c19c5f0f18836b70f99718f1a7afb4ceb11b3cca974b5e4413489045b21b80e2`；grading digest 为 `sha256:0ef6056f3b8e7ae42d5e06dd169afd46a46e5f41594e50188a3845eaaf49822f`。三账本和 diagnostics 一致，revision 为 `conan13230-private-test-v1`。

## 实际链路、所有权与异常传播

固定代码路径均位于 R/repo：

1. S/run_matrix.py 顺序执行 release verify、Docker source 身份读取、`rh2/scripts/replay_grade.py prepare`，然后顺序起三个独立 `run --repeat 1` 子进程。没有模型参与，也没有多候选并发。
2. `adapters/slime/replay_grade.py:222` 使用正式 TrustedTaskController 生成 prepared/private。`envpack/prepared_tasks.py:225-250` 拒绝覆盖旧 manifest/prompts/rollout/host 文件。实际 prepare rc=0，prepared_at 为 `2026-10-02T21:48:49.869445Z`，在 v2 job 启动之后、首候选之前；prepared manifest 内全部文件摘要及 host 摘要重算一致。
3. `adapters/slime/replay_grade.py:318-444` 创建 candidate 容器，核 base HEAD，sanitize、trusted init、基线 census 后，以 agent UID 54321 对原补丁 `git apply --check` 再 `git apply`，没有 fuzz 或裁剪补丁；导出 FrozenPatch，再分类和可信投影。
4. 同文件 `:610-685` 无论候选阶段成功/失败都先持久化再有界清理；清理未确认则 stop。实际三组 stage_error=null、last_stage=projection、removed=true、rm:ok；候选容器在评分前被释放。
5. `:688-690` 调 `SWEGradingManager.grade(workspace=None, frozen_delta=source, deadline_monotonic=...)`。`prepared_task_face.py:443-525` 重验 host view，生成受信 setup/候选测试脚本和 revision parser。manager `:1987-2048` 核 FrozenDelta 绑定、独立重算可信路径集、创建 fresh grader、核运行中镜像 digest、clean checkout、重建基线再应用被冻结的文件内容，随后运行真实测试和 parser。
6. manager `:2190-2201` 的 finally 收口 grader scope；driver `rh2/scripts/replay_grade.py:108-114` 的 finally 关闭 manager 并把 final_status 变成实际退出码。manager `:1669-1717` 只回收本实例记账容器，不扫他人对象。

拓扑：外层 run_matrix supervisor/子进程 → 三个串行 replay driver；每个 driver 一个 asyncio event loop 和一个 manager。候选容器由 ReplayGrader 持有，grader 容器由 manager 的 record 持有；单候选的 candidate 与 grader 生命周期先后相接。日志显示每组 manager 只创建一个 grader、移除一个，无 regrade。

固定代码 SHA256：`rh2/scripts/replay_grade.py`=`d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`；adapter replay=`df9b26dc81938239dc4c45c5466c0b08c5505f4c724ba331e482862a3834c178`；prepared_task_face=`a2e9a955032989eed642e6057ebd2f47cc627c6afe3e1f1fc235bef95f0ec7ca`；manager=`1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`。上述源码位置前缀为 `rh2/src/repoharness2/`，driver 除外。

## 完整候选与逐参考判定

本地原件（plan 记录的原路径）、S/candidates 副本、输出 candidate.patch 三者 SHA 相等：gold=`c77c7fa0aca6eecc6acaff2f21a23eeef23443c13467057b1367527ddfece7f7`，1110 字节；android_only=`8d99fdcef2c400cf07c11e26de93af78f62030a2594c2ae6d86aac45dd4583fe`，591 字节。二者只改 `conan/tools/gnu/autotoolstoolchain.py`。

独立检查不是只相信 apply_method：解码 FrozenPatch 的完整文件内容，核 content_digest；逐 hunk 核候选新增/上下文内容，再逆向还原。两者还原结果均命中 baseline 文件摘要 `sha256:c5da24d439695b2814310b73271cdb78b7c8fcd89b88164a409e9e83c10fa7b0`。FrozenPatch 只有该一个 modify entry，可信投影保留全部一个 entry，无 ignored_paths、unsupported_shape；noop 为零 entry。按固定 `compute_frozen_patch_digest` 的 canonical JSON 规则重算三 artifact digest，与 projection 和账本逐一相等。

| 候选 / artifact 目录末级 | 原 F2P（1项） | 新 F2P（2项） | 原 P2P（34项） | pytest rc / exec rc / driver rc | reward |
| --- | --- | --- | --- | --- | --- |
| noop / a1-538d6acf | 0/1 pass | 0/2 pass | 34/34 pass | 1 / 0 / 0 | 0 |
| gold / a1-735ea1c6 | 1/1 pass | 2/2 pass | 34/34 pass | 0 / 0 / 0 | 1 |
| android_only / a1-2a9ca91e | 1/1 pass | 0/2 pass | 34/34 pass | 1 / 0 / 0 | 0 |

F2P 指修复后应通过的参考测试，P2P 指应保持通过的回归参考。逐一对照 plan 的 3+34 参考与原 eval.log 的 PASSED/FAILED 行：每组恰为 **37 个不同节点**，节点集合相等；所有 revision partition 的 success/failure 与原日志相等。原 F2P 是 `test_crossbuild_from_macos_to_non_apple_os`；新增两项是 `test_linux_host_from_macos_has_no_apple_cflags[no_sdk]` 与 `[sdk_sentinel]`。三组 missing/skipped/unaccounted 均空，num_parsed_outside_segment=0。没有用总通过数代替参考核销。

日志均有 trusted setup apply=0/restored=1/expected=1/present=1/OK=1，安装开始/结束及测试开始/结束 marker 完整，install rc=0，无失败安装命令，candidate segment completed=true，log.partial=false。pytest 非零是正常负候选结果；脚本用 marker 保存 pytest rc 后完成 shell，所以 exec rc=0 不等于测试通过。

日志路径均为 S/output/<候选>/eval_logs/：

| 日志 | SHA256 |
| --- | --- |
| evallog_replay-conan13230-formal_b1cfcd86.eval.log | `cce1098280653a1250f2d1f565c8d14330a741d518dd7c99a0893343d85e7d84` |
| evallog_replay-conan13230-formal_91de4e1e.eval.log | `981830fd96eb1e012b37014b938558de4ef4eab4ebf43bd093a9127cbab9ed88` |
| evallog_replay-conan13230-formal_ed674044.eval.log | `63a0b391fd3724b57ff4c70937c6027e28cdd57227e7183270bc6e8a26ab5c38` |

## 退出、镜像与清理证据

外层 supervisor 回执：`2026-10-02T21:48:36Z` 起、`21:57:00Z` 完成，returncode=0，stderr 空。三 run rc 文件均为0；各 run stdout 的最终记录均 halted=null/aborted=null，manager created_total=removed_total=1，containers_open=[]，supply_open=[]，cleanup_failures=[]，final_status.exit_code=0/reason=ok。

远端回收 audit 对 `conan13230-formal-r11-v2-{noop,gold,android_only}` 三个归属 run_id 分别记录 container/network 查询 rc=0、stdout/stderr 空，并声明 exact owned run label absence。固定代码为 candidate 与 grader 传入相同 rh2.run_id。**回执未保存查询 argv，本文没有独立重新查当前 daemon**；因此报告的是已回收的运行后清理证据，而非对当前远端状态的重新测量。

首次 v1 的 source tag 缺失异常原样保留在 C/source_alias_r11_and_initial_failure_remote_receipt.json：失败发生在 `docker image inspect`，在 prepare/候选/评分之前，不记作候选负分。随后离线 source alias 的 before_rc=1；source 和 after 的 config 都为 `sha256:470bafe8634b5ef92f942aef63a818d7dd681ba591548d467a6f25be420806df`，RepoDigest 都为 `sha256:3f7ba164d697c75bf27b917cd2ea794c8ebefbbb3c6954113e1dc1f2d5e62376`，只补 tag。v2 prepared_identity 实际 image ID 命中该 config；三评分走非 local-build source manifest 身份校验。

## 资源与公开 actor 证据的复用边界

正式 policy 声明 2 CPU、4 GiB memory、512 PIDs、64 MiB shm、1 GiB tmpfs、UID 54322、deny_all；候选脚本 UID 54321。固定 manager 会运行 prelaunch profile/身份探针并拒绝违规；正常完成是这条 guard 通过的间接证据。**本轮保留原件没有三组完整 prelaunch inspect/probe 事实，resource_facts=null，账本 image_id_actual=null**，不能把 policy 当成 CPU 消耗、实际 quota、OOM 或 PID 峰值测量。

有直接保留的实测：grader cgroup memory.peak（读不到回退 v1，manager:3979）分别为 noop **321.098 MiB**、gold **318.457 MiB**、android_only **320.492 MiB**，均非 zero/unavailable；测试 marker 段耗时 1.315/1.143/1.483 秒，grader_cleanup 耗时 0.746213/0.818777/0.884854 秒。它们不能外推为高并发容量或训练吞吐。

先前公开 actor 证据 C/baseline_actor_13230_v2_audit.json 的 SHA=`a6af60a804a9285796fac9aca40274313cf96ba2bfd9af5778598b3e0b1477db`。其 remote audit 列20文件，本机 _evidence 中17个输出 SHA 都匹配，另 C/baseline_actor_13230_v2/plan.json 与 public_commands.json 两份输入 SHA 匹配；preflight.json 未在本机找到，预检 stdout 另存，未伪称全20文件核验。attempt 内嵌三个 public_commands，与实际 captures 和 trajectory 结果相接。

公开 actor 使用同 source manifest/config、同 base HEAD、相同 conan/conans `/testbed` 导入路径，Python3.10.14/Conan2.0.0/pytest6.2.5/Jinja2 3.1.4，真实 Claude Code 2.1.205（脚本 stub）。prelaunch 留有实际 quota/身份/网络 probe，activation 指向 testbed 解释器；34项原公开回归通过，issue_exact CLI 在错误 SDK 分支失败，显式哨兵 SDK 诊断走预期 raise 并输出 `-isysroot /public-diagnostic-sdk` 和 `-arch x86_64`。

R 的父/新 consumer 本题比较证实 public_digest、source image/manifest、candidate_install_script、candidate_test_script、candidate_test_after_install_script 摘要不变；变化的是环境包和 grading 身份、host/rollout 行身份、eval/trusted setup（新私有测试）。因此先前公开 actor 可以复用为 **原公开开发命令和 source/vendor 条件的证据**。它不能替代 R11 的新评分材料验证（本轮三正式候选单独补齐），也不能证明 R11 真实模型求解、完整题面交付或 actor 全链在新 release 上重跑。两个 CLI rc=1 均不应自动被称作环境失败，失败位置与 payload 已有原始输出。

## 阻断项与登记项

- **阻断：无。** 本题正式三候选运行、逐参考结果和收口证据没有矛盾；不新增 guard、不改 reward/材料、不要求重跑旧测试。
- **非阻断、保留证据边界：** 本次资源完整 profile 事实、label 查询 argv、baseline preflight.json 未全部留存。它们不推翻已通过的三候选评分；如后续 gate 要求完整资源实测或独立 daemon 清洁确认，由对应运行 owner 在该 gate 补原件。现阶段不得扩大已验证措辞。
- **不适用/未核：** 模型能力、训练 distribution/mask/group、GPU、14177、测试本身是否覆盖所有错误实现、common 管理器全量异常恢复。这些没有本轮新实施授权或证据；本文不重新审查既有语义，也不将理论反例作为当前 P0/P1。
