# Conan 11594 R12：正式 CPU 与实际 actor 工具权限窄核

日期：2026-10-03。非作者 Production Tracer，按 review-standards §10.4/§10.5 执行。只读本地冻结 release 与回收原件；用 Python 标准库重算 SHA、解析 JSON/日志和逆向补丁。没有访问远端、运行 Docker、模型、项目测试或旧测试，没有修改材料和共享实现。13230 已结案，不重审；本报告不覆盖其它 Conan 题。

## 结论、范围与停止条件

**11594 R12 正式 CPU 三候选运行窄核通过，无本范围阻断项。** fresh prepare、固定镜像/材料、完整原候选到 FrozenPatch/可信投影/真实 grader、6 来源参考到 7 完整节点、UID54322 工具前置、真实安装/测试退出和双层清理均有一致原件。noop/gold/drop_config 的 reward 为 **0/1/0**。

同批追加的实际 actor 原件也通过 **工具权限与运行收口** 窄核：真实 Claude Code 2.1.205，UID54321、testbed 解释器和源码导入、固定派生镜像、Ninja/CMake/CTest 可执行。它使用脚本 stub 和明确 image override；不是模型功能修复验收，也没有证明完整 solver 题面交付或自动训练资格。

上述证据足以分别记为“正式 CPU 三候选验证完成”和“实际 actor 固定镜像工具权限已验证”，停止本批窄核。只有材料/代码身份变动、绑定成员缺失、实际退出/清理矛盾会重新打开本范围；资源完整实测和真正模型求解属于对应后续 gate，不在本轮新增挡板或要求重跑旧测试。

## 固定原件与身份

仓库相对前缀：`C`=`runs/category2_repair_20260929/conan_cpu_20261003/`；`S`=`C/formal_matrix_11594_r12_v1_evidence/formal_matrix_11594_r12_v1/`；`A`=`C/actor_tools_11594_r12_v1_evidence/actor_tools_11594_r12_v1/`；`R`=`runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/`。

- 正式 S **55/55** 文件的 SHA256/字节数均命中 remote audit，集合相等，没有未列文件。
- actor A **34/34** 文件同样全部匹配 remote audit，集合相等。
- R/repo **1020/1020** manifest 成员全部匹配 SHA/大小，均为非 symlink 文件；此处仅做发布身份检查，代码深读限于11594调用与材料消费。
- release=`cat2-cpu-r2e089092-swe21-conan-20261003-v1`；R/manifest.json SHA256=`3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`。

| 原件 | SHA256 |
| --- | --- |
| C/formal_matrix_11594_r12_v1_remote_audit.json | `6de6fb437519b7bd3c4b9da2b9028829773c7beb92854b548be24315c341cefd` |
| C/formal_matrix_11594_r12_v1_audit.json | `cdd7bb05a8b181cdfc5f87c34513a239647fa91cc368041cbeeab7c4cd3f4dbc` |
| S/run_matrix.py | `e952ee6106d4bb20a4292f74f4ccdb6e0418f66a9f9dc565a7da0dac670e3cee` |
| S/publication_input.json | `faa3e5a88a30f1b4cf5d8ba296e17fa0ce6071e1a7df402308360eb89262f514` |
| S/publication_receipt.json | `4b26a28fe6ad8c594fe5e90103c129e3252383204fceb3f1e383680b5ab54130` |
| S/prepared/prepared_manifest.json | `c986845ec686abd17538c6a9ef52e82c2efc37b8a686b123e3fb339a3b4dec6e` |
| S/private/host_grading_views.jsonl | `16b27d2a16852fc23f1a3f2e64956e86a781f98315088db7c34aaee8ef507f6b` |
| R/checks/consumer_combined_264.json | `cc5289134334d012497df98e1127ab8d8d7bf468ce5fed7c7f181aaf5ae912fe` |

S/plan.consumer_identity 与 R/checks/consumer_combined_264.json 的11594条目逐字段相等。R12 本题 registry 位于 `R/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan11594_test_patch_environment_v1/material_revisions.json`，SHA=`105cf9f779eac8c933ff38984b829da23608659abe926ec7269088a524ce4fde`；其 effective_test_patch 与 fresh host grading view 字节相等，SHA=`4a781bc87b05f63cac3af0686bbd6b29817dacd39f0ef7ba053fd0f2f9a47eb2`。三评分材料身份都为 `sha256:fe68e56946f2eeab35c4c335f317ef2a17fb27da4af54024b3d837f2548788a4`，grading digest=`sha256:9a06e834021494ea7b52c05db8837d0df833835b402d581d7bb3703e32ace976`。

fresh prepare rc=0、prepared_at=`2026-10-02T22:16:32.988703Z`，在本次 job 启动之后、首候选之前。manifest 内 prompts/rollout 文件与 host artifact 摘要重算一致。固定 prepare 实现拒绝覆盖已有四份产物，未复用草案 prepared。

## 真实链路、并发基数与所有权

S/run_matrix.py 先核 release，再核固定 image ID、fresh prepare 与六份 spec 脚本摘要，然后串行起三个 `replay_grade.py run --repeat 1` 子进程。每个 driver 独立 asyncio loop 和 manager，每组一个候选暂存容器、一个 fresh grader；候选先删除，grader后启动，没有模型或多候选并发。

固定代码（以下 adapter/manager 路径在 `R/repo/rh2/src/repoharness2/`）：

1. `adapters/slime/replay_grade.py:504-590` 从 source public/host view 构造 spec，核 Conan 固定派生 image ID；`prepared_task_face.py:585-605` 只接受已登记 source/manifest 或固定 derived-ID，绑定 grader image=`sha256:f3b8d6671607e167fa549c05faa860345e5256c8f834a6a711447df9dce6839f`。replay 的候选暂存也用该 ID，实际账本与 prepared_identity 命中同 ID；这不自动改变正式 actor 的 source rollout。
2. replay `_candidate_stage` 在 base HEAD=`4ed1bee0fb81b2826208e8c1c824c99fb6d69be8` 上 sanitize/init/census，再以 agent UID54321 整份 git apply 原候选、导出 FrozenPatch 和可信投影；three stage.last_stage=projection、stage_error=null。
3. replay 的 finally 持久化并有界删除候选容器。然后 `:691-692` 调真实 `SWEGradingManager.grade(workspace=None,frozen_delta=...)`，而非只调用 parser/helper。
4. manager `:1987-2048` 核绑定、独立重算投影、创建 fresh grader、重建基线并直接应用冻结文件内容。受信 setup 后保护控制面，再执行 UID54322 的前置工具检查、vendor安装、完整测试段及正式 bound parser。
5. manager `:2190-2201` 收口 grader scope；driver finally 调 manager.close 并据最终状态给实际进程退出码。candidate owner 是 ReplayGrader，grader owner 是 manager 的记账 record；清理失败不能假称正常收口。

代码 SHA：adapter replay=`7cb03bfd1a6ddcb4238f54d2a19d30d4e3e93a56ad630b81e8fb05ac031160fb`；prepared_task_face=`a96c46bb2ada9c84e92de6b48b41dc3b0292bb1029946081b10e235433e1a619`；manager=`1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`；`envpack/conan11594_reference_bindings.py`=`07172db6cedd9b443910941808aa04037c4faa10411ae664e69e5ba21b2d1b00`。

## 原候选到 FrozenPatch：没有裁剪修法

原 gold 文件、S/candidates/gold.patch、输出 candidate.patch 的 SHA 都为 `e49265e4fd430f627dd2293f1f79b3b6c30b30d36c8a6a066c992f4d4b48abfa`（662字节）；drop_config 三份都为 `f4445e51d087748cf00cd647bcf2ddf13a592c1be343561ad6956a367ef408e1`（807字节）。原路径由 plan 指向既有 gold 和 degenerate_drop_config，原件摘要独立核过。

两 FrozenPatch 各只有 `conan/tools/cmake/cmake.py` 一个 modify entry；解码完整文件并核 content_digest，然后逐 hunk 匹配候选新增/上下文行并逆向还原，均得到 baseline 文件摘要 `sha256:461786181aa4a64467e6eb2e87e5f41f0b3bc1d6cc9a18ce53efc407c288c1e4`。可信投影完整保留该 entry，无 ignored/unsupported 路径。noop 零 entry。三个 FrozenPatch canonical JSON 摘要独立重算，与各 projection/ledger 相等。

## 6 来源参考、7 完整节点与 ALL 判定

正式 `prepared_task_face.py:563-565` 在11594 revision走 `parse_conan11594_bound`。固定 binding asset SHA=`ca0987bd0bdde5926b33eabf31bf51b1e704165036e1441e66ff97e6f9630bcc`，与 host revision、diagnostics 的 binding_version 一致。bound parser 对两完整 Ninja node 精确匹配：缺任一成员就没有来源参考状态；任一 ERROR/FAILED/SKIPPED/XFAIL 都不能得到 PASSED；先删除旧 parser 的碰撞末值，再写纠正状态。这是当前真实消费路径，不是题主诊断聚合器。

下表 node 前缀均为 `conans/test/unittests/tools/cmake/test_cmake_test.py::`；保留参数内空格，未以空白切断节点。

| 完整节点 | noop | gold | drop_config |
| --- | --- | --- | --- |
| test_run_tests[Ninja Makefiles-test] | PASSED | PASSED | PASSED |
| test_run_tests[Ninja Multi-Config-test] | FAILED | PASSED | PASSED |
| test_ninja_multiconfig_executes_requested_release | FAILED | PASSED | FAILED |
| test_run_tests[NMake Makefiles-test] | PASSED | PASSED | PASSED |
| test_run_tests[Unix Makefiles-test] | PASSED | PASSED | PASSED |
| test_run_tests[Xcode-RUN_TESTS] | PASSED | PASSED | PASSED |
| test_run_tests[Visual Studio 14 2015-RUN_TESTS] | PASSED | PASSED | PASSED |

来源原 F2P `test_run_tests[Ninja`对应前两完整节点，必须ALL通过；新增F2P是实际Release执行测试，其余4来源P2P各对应1完整节点。独立从每份原日志提取7完整状态，再按固定映射重建6来源状态，全部与正式账本/partition/作者audit相等。三组共 **18个来源参考状态，对应21个完整node状态**，不是18个完整测试节点。无missing/skip/unaccounted，num_parsed_outside_segment=0，正式 num_parsed_tests=6 是来源聚合数。

| 候选 | F2P pass/total | P2P pass/total | pytest rc | exec rc | driver rc | reward |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 0/2 | 4/4 | 1 | 0 | 0 | 0 |
| gold | 2/2 | 4/4 | 0 | 0 | 0 | 1 |
| drop_config | 1/2 | 4/4 | 1 | 0 | 0 | 0 |

原日志分别为 `S/output/<候选>/eval_logs/evallog_replay-conan11594-formal_<nonce>.eval.log`：noop nonce=badd40f0、SHA=`eb270f0b1c5df999907bf3fb0284105f368f4d386c9a91a83947a33b287d4d2c`；gold nonce=317d8fbf、SHA=`f9f83661a815932e135827d3c7d5956e62cd7f7863698aacfd680be0c0896cef`；drop_config nonce=1cd2f220、SHA=`4af1c86bdae8bdf4fd1dd9c92c468b258c01b4a14d8e7fe6a5eaf529b6ce614d`。

## 测试缺席、前置工具、安装与退出

原测试文件在base缺席是 registry/host revision 的明确 `base_state=absent`，不是从异常猜出的缺席。固定 `prepared_task_face.py:193-197` 核 git base 和工作树都缺席，再受信 apply new-file有效测试补丁。三组实际 setup APPLY_RC=0、RESTORED=0、EXPECTED=1、PRESENT=1、ABSENT=0、OK=1；RESTORED=0符合新增文件，不应被误判为恢复失败。

三 diagnostics 的 candidate_prerequisite 全为 user=`54322`、home=`/home/rh2grader`、state=verified、exit_code=0、stderr空、SHA=`bdb8f8d6694951ba761da7b9505db153ac4215c48495cb77d883aa0570373e1c`。manager `:3453-3493` 用 grader候选执行身份运行，而非root。固定脚本在可信cwd `/`、隔离解释器 `python -I` 下断言实际euid54322、Ninja distribution1.10.2.4、固定binary可执行并成功执行 `--version`、CMake3.22.1。保留stdout含 Ninja `1.10.2.git.kitware.jobserver-1` 与成功marker；CMake版本由固定断言通过证明，formal prereq stdout未单独打印该版本文本。

三安装段完整执行且未skip，RH2_INSTALL_RC=0，无失败安装命令；三测试段均完整，RH2_TEST_RC=1/0/1，有开始/结束marker，log.partial=false、runner_integrity_changed=false。pytest非零是负候选正常结果；shell保存pytest rc后完成执行，因此exec rc=0不能被写成测试通过。

外层job `2026-10-02T22:16:20Z`起、`22:24:38Z`结束，rc0。各候选run.rc=0；候选cleanup rm:ok/removed=true；manager created_total=removed_total=1、containers_open=[]、supply_open=[]、cleanup_failures=[]、regrade_total=0，final_status=ok/0。remote audit保存 `docker ps -aq --filter label=rh2.run_id=conan11594-formal-r12-v1-<候选>` 与对应network ls准确argv，三组查询rc0且输出空，只查本run归属。

## 实际 actor 工具证据（同批追加）

A/run_actor.py及actor.rc明确走固定R12 `rh2/experiments/task2_swegym_dev_20260925/devcheck.py --prepared-summary ... --commands ... --image sha256:f3b8...`。本轮实际image override、初始HEAD和运行中容器image都命中固定ID及原base；host/source公开视图仍是source，不能把这次显式override说成正式actor自动切换完成。

独立核 A/public_commands.json 与 attempt内嵌命令相等；trajectory有28有效JSON行、2个Bash tool_use与2个对应tool_result，ID逐一相等，分别执行identity/tools；stub保存3个请求，trajectory对应3次message_start。没有项目测试。两个命令真实rc0、无截断，末尾 result success/end_turn，harness exec实际Exited/ExitCode0、log_complete=true、stderr空；不是仅凭外层job rc0。

- identity.out：实际UID54321，Python `/opt/miniconda3/envs/testbed/bin/python` 3.10.14，conan/conans导入来自 `/testbed`，HEAD=`4ed1bee0fb81b2826208e8c1c824c99fb6d69be8`。
- tools.out：Ninja路径 `/opt/miniconda3/envs/testbed/bin/ninja`，真实binary版本 `1.10.2.git.kitware.jobserver-1`，CMake/CTest真实输出都为3.22.1。Ninja distribution1.10.2.4由已执行命令断言，不将distribution版本与binary字符串混为一谈。
- cc_version_observed.json与trajectory init均确认Claude Code2.1.205。activation probe确认testbed解释器；prelaunch实际inspect image=f3b8…、nano_cpus=2000000000、memory/swap=4294967296，cgroup v2 probe CPU_MAX=`200000 100000`、MEMORY_MAX=4294967296、SWAP_MAX=0、PIDS_MAX=512、UID54321、CapEff=0、NNP=1。以上为actor实际quota事实，不等同正式grader三组完整quota实测。
- actor outer job和actor.rc/harness_exit都为0；attempt cleanup container_rm=0、network/relay failures空、stub_rc=0、labeled containers/networks/residual_after_force都空。remote audit另保存准确run label `cpu-a-conan11594-actor-tools-r12-v1` 的容器/网络查询argv，rc0/输出空。

actor证据SHA：C/actor_tools_11594_r12_v1_remote_audit.json=`1a3e1fba274905e18b2fc1f085793dc0a695992995dd1db4c55ef4a9650d64cd`；C/actor_tools_11594_r12_v1_audit.json=`dc6f0403567b6da492311e7d00c4ddea9f4a32e5fea2eb3783b9e28411b85cdd`；A/run_actor.py=`75ced87a23458186e36ce5146538b796e4542a02612eccb35684d72f65f2f6c4`；A/output/prelaunch.json=`20a2550b480f7c14808a143027e36ebc220d024d72f5cd75e56566fe183b12eb`。

## 非阻断边界与未核内容

正式grader保留policy声明为2CPU/4GiB、512PIDs、64MiB shm、1GiB tmpfs、UID54322、deny_all。代码有prelaunch guard，但S未保存三组完整inspect/probe事实，resource_facts=null；不能把policy或成功退出写成CPU实际消耗、OOM/PID峰值测量。保留的实际cgroup memory.peak分别为354.949/357.957/359.125MiB（非zero/unavailable）；marker测试耗时2.505/2.256/2.591秒。actor新增quota实测只覆盖该actor一次作业，不补写为三组grader实测，也不能外推训练容量。

现有cpu_diagnostic文档明确UID0私有草案诊断；本文没有使用它替代正式CPU或actor证据。公开reader报告只证明静态说明可读，也没有升级成实际完整solver消息交付。未重新审查既有测试语义、所有common实现、异常恢复矩阵、训练reward/mask/group或其它题；本范围没有需要修实现或新增guard的finding。后续完整solver/训练gate由主审按已授权流程处理，历史诊断与证据保留原样。
