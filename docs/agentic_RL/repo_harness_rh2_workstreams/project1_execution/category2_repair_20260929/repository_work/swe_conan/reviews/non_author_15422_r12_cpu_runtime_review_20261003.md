# Conan 15422 R12 正式 CPU 与 actor 工具：非作者 Production Tracer 窄核

日期：2026-10-03。审查角色：非作者，GPT-6.1 Sol / high；依据根 AGENTS、review-standards §10.4/§10.5。本轮只核新增正式回执与 R12 actor 工具原件，复用既有 v2 语义结论，不重审旧矩阵或全面测试语义。只用本地标准库读取、计算 SHA、解析补丁/日志；未访问远端，未运行 Docker、模型或项目测试。唯一新增本报告，不改 task/board/shared 或历史材料。

**结论：本范围无阻断，停止于此。** 八个完整原候选经固定 R12 fresh prepare、FrozenPatch、受信投影和实际 grader，奖励依次为 0/1/0/0/0/1/1/0，均符合 plan。45 个参考 × 8 次 = 360 个完整原日志状态，无参考 skip/missing。整份 coder a3 与 DS a1 的非官方文件保留；DS a4 官方测试改动保存在 FrozenPatch，但在评分投影中排除，源码实际获得 1 分。八次前置/安装/driver 退出与内外清理闭合。实际 actor 工具作业也核实了固定镜像、UID 54321、Claude Code 2.1.205 与公开工具可执行；此不等于完整 solver brief 交付、编译链接功能或训练资格。

## 1. 原件与固定身份

以下为仓库相对路径前缀：

- `C = runs/category2_repair_20260929/conan_cpu_20261003/`
- `S = C/formal_matrix_15422_r12_v2_evidence/formal_matrix_15422_r12_v2/`
- `A = C/actor_tools_15422_r12_v1_evidence/actor_tools_15422_r12_v1/`
- `R = runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe21_conan_v1/`
- `M = R/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/conan15422_test_patch_f2p_v1/`

独立逐件对账 `S` 120 个原件、`A` 34 个原件的文件集合、SHA256 和大小，均与各自 remote audit 一致，无多件/缺件。独立核 R12 manifest 的 1020 成员，均为普通非软链文件且 SHA/大小一致。仅相关本题 registry/consumer/生产链深读，未审其他题结果。

| 锚点 | SHA256 |
| --- | --- |
| `R/manifest.json` | `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987` |
| `C/formal_matrix_15422_r12_v2_remote_audit.json` | `a7a33508b01e9de96aca536ca8040153d29eacdd84bd91bacfcd2a7ebd644763` |
| `C/formal_matrix_15422_r12_v2_audit.json` | `0acc97b0a3fe6a73fc01003a6f29a97783aa511efa5aea58e1c2b4816320651e` |
| `C/actor_tools_15422_r12_v1_remote_audit.json` | `bee82b0264fd265ce213615c479e66544c626f02532277c5a0556f01439e10f7` |
| `C/actor_tools_15422_r12_v1_audit.json` | `7d3d696d1c8fea32e35e07324ad59d635b20343126338448609b15ea665afcb9` |
| `S/plan.json` | `15c47b0e916ce146d0fb3b2fde06010f73aac6b9f4e82d2225881314455c9cd8` |
| `S/run_matrix.py` | `e952ee6106d4bb20a4292f74f4ccdb6e0418f66a9f9dc565a7da0dac670e3cee` |
| `S/matrix_results.json` | `bfb54c7b42d260581fb772c0140b37540488dadf3a77252a84dea47315f23b8a` |
| `S/publication_input.json` | `3835f8449e7f65bc4a6c569d6fd2e415809b1a3c6032a031a77669c57cd655c9` |
| `S/publication_receipt.json` | `add2f534febb96493a2077a9ff64df667e81f4066d89544bf2fa8c9448a4a2fb` |
| `S/prepared/prepared_manifest.json` | `f054e0923e3c9b56b8191ddfec9d4ad9b8a219b9462044e788256ec511d33059` |
| `S/prepared/replay_summary.json` | `d350567546295cb56837488f511b931539a02f31fc142ae1b424ea701d2dcf88` |
| `S/prepared_identity.json` | `46bb3a26b03c73e6190ceabb27c39a5004f874fd358aa41df73bbf31c66faf97` |
| `M/material_revisions.json` | `0122d844e68b8f7f9f0c80140048c1cfedf2d809b5c1d4b595c6dfa73a115672` |
| `M/effective_test.py` | `5de644e248dc131c250f343885d95ec5b9d9f2f35798852d79e263fe4252c16a` |
| `M/environment_recipe.json` | `822a4fa5074199283858d39174d21bd91aa4d58fc0fcf8b82ff902252abd7e86` |

## 2. Fresh prepare、材料与镜像/前置

release ID 为 `cat2-cpu-r2e089092-swe21-conan-20261003-v1`。正式脚本先逐件验证 release、publication 与候选 SHA；release_verify / prepare 实际 returncode 都为 0。prepared 时间 `2026-10-02T22:50:09.839448Z` 在本次 job 开始之后、首候选之前，内部 prompts/rollout/host 文件散列全部一致。plan、prepared identity 与 `R/checks/consumer_combined_264.json` 本题项完全一致。

实际消费 revision `conan15422_private_test_v2`，base `f08b9924712cf0c2f27b93cbb5206d56d0d824d8`，完整有效 test patch SHA256 `9ad7529457054bb004534951feb4d08b40973a06fd30b4a1564054de074a0bb6`。host 的 patch 字节重新核 hash；另从固定公开 base 文件（SHA256 `55b95908ac4dc968a732f88c994c62e0c4dd9591708dc9cf1d141f5346e62569`）按完整有效 patch 重建，结果逐字节等于 `M/effective_test.py`。因此后文 source-line skip 映射使用的是实际受信有效文件，不是任意另存的同名文件。

| 消费身份 | 值 |
| --- | --- |
| materials identity | `sha256:90aad16e26a29c327e6735755eee37125a885b4051dc5f27a6a9ba1d456f0927` |
| grading bundle | `sha256:875041c5f0c9196d3623165d071f16da85be021e9da998186458f3f2b00343e9` |
| environment package | `sha256:249bf87ebdaa5be09fd6327d0e1342b5a226f00fb39ce2dff3114769ad9b193a` |
| public bundle | `sha256:a0a21d92e5a054648c1618987305c24d5a8e0b7ea06601ac50374e023be1a554` |
| source image manifest | `sha256:afd7d4928ba361196d446926204dbd8e0c37ea2018dda392096972a8767c353a` |
| source config | `sha256:bb264f88ffc338f8b33c58e15a5f0373761abfe75145e7ae201e360031a8b9c8` |
| derived image ID | `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead` |
| Conan console entry SHA256 | `df26d3928be05d409787e3ecfffb06b278da9e738fdd1f5810a579ec854cf9d8` |

source tag 为 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-15422:latest`；recipe `conan15422-cmake-console-v1` 的 SHA、source/derived 身份和 console entry 一致。固定 prepared_task_face 只接受登记 source 配对或登记 derived ID，正式 spec 使用后者，image_local_build=true / manifest=null。`S/prepared_identity.json` 保存本批实际 image inspect 的相同 config ID。逐份读取八个 `S/output/<id>/ledger.jsonl`（各一行），顶层 `image_id_actual` 均为 `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead`，与登记 derived ID 一致；不能声称另存了八份逐 grader config inspect。local-build 分支也不是 source RepoDigest 实测；应以登记不可变 config ID、ledger 身份、预检和实际前置证据表述。

八份 diagnostics 均保存 UID 54322 前置：state=verified、exit_code=0、stderr 为空、stdout=`RH2_CONAN15422_CMAKE_CONSOLE_PREREQUISITE_OK=1`，script SHA256 `ed0834ad7fd732a65083443feb1fbf05e182d9ef9b772d74226913efd683e686` 与 consumer 一致。固定代码以隔离解释器、cwd `/` 检查 UID；用 NOFOLLOW 打开普通 Conan entry 并核完整 SHA/可执行属性；核 CMake/CTest 固定真实路径与 3.23.5 版本。manager 将这份受信脚本作为 UID 54322 前置执行，失败走 infra，而非调用候选 repo CLI 当作前置验证。

## 3. 完整候选到冻结内容与投影

plan 列出的七个非空原完整 candidate.patch、`S/candidates/<id>.patch` 和运行 artifact `candidate.patch` 字节一致。原路径全部保存在有 SHA 锚点的 plan；没有替换成“只留源码”的缩减候选。

| 候选 | 原完整 patch SHA256 | FrozenPatch 路径数 / 投影路径数 |
| --- | --- | --- |
| noop | 无 patch | 0 / 0 |
| gold | `1bcbaa52ea35d4893b8eb55e921f082ce73d7948e355f5a4d8657f4b1b620e66` | 1 / 1 |
| coder_a1 | `c807e19bed52cf4d8e51c85a954b5108d0b69620b4a4bf1a94b78eedd0f44d58` | 1 / 1 |
| coder_a3 | `90c9d84ea7dd586a0a3062528a33a2f3af401b23490b4536a877eead39b0b754` | 5 / 5 |
| deepseek_a1 | `33ff4f9817a4fd12505557ceb41cc0c1daadea5b59544acd6ed5aa21eb9a3648` | 2 / 2 |
| deepseek_a4_generator_boundary | `35bffd28ab6643dbd3d375e0fa3f4cc5d1f772f97169caa1885527635ec93530` | 2 / 1 |
| coder_a2_alternative | `310cb1811571e14861faa0d1e2d86dadafc74ad786f8aeb6ec83bfcadb92e134` | 1 / 1 |
| qwen36_a2_schema_diagnostic | `5918c22c0a20a2846ead80e90e1aa9bf46705249ec8980c7368cef9cd290127c` | 1 / 1 |

对全部 FrozenPatch entries 解码并核 content digest，路径集合精确等于原补丁集合；modify 文件以原补丁各 hunk 逆还原，全部与本次 baseline manifest 内容散列相符；add 文件与原补丁完整新增内容逐字节一致且基线原本无此路径。四类 artifact 的 canonical Frozen digest、projection 与 ledger 全部重新计算一致。

coder a3 的五条路径均在 Frozen 和投影中：`README_JOBS_FEATURE.md`、`conan/tools/cmake/presets.py`、`conans/test/unittests/tools/cmake/test_cmake_presets_jobs.py`、`debug_test.py`、`verify_implementation.py`。DS a1 的源码与 `conans/test/unittests/tools/cmake/test_cmake_presets_definitions.py` 都被保留，不能因它是非官方测试文件就声称被滤掉。

DS a4 的 `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py` 整份改动实际冻结，但被投影明确分类为 `official_test_file` 控制面排除；只向 grader 投影 `conan/tools/cmake/presets.py`。其 Frozen digest 为 `sha256:24668c097fe66c7ad3d1cb6826eb67600197162f5b956ef6ed6e754e39f98086`。这是保留原证据后排除控制面，不是丢弃整份候选或 legacy 自动给 0；真实 reward=1。八轮 unsupported_shape_reasons 均为空，除上述单个官方测试条目外没有 ignored 路径。

实际链为候选 sanitize / UID 54321 原 patch check+apply → baseline/census/export → FrozenPatch / trusted projection → 候选清理 → `FrozenDeltaSource` → `SWEGradingManager.grade(workspace=None)`。grader 独立 fresh checkout、基线重建与冻结内容应用，再恢复并应用受信官方 test patch。只复核此链路及本题 producer，不重审全部 common 实现。

## 4. 360 个参考状态与非参考 OS skip

实际命令 `pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`。F2P 五个完整 node 为此前缀下的 `test_presets_njobs`（原参考）、`test_presets_jobs_default_matches_public_helper`、`test_presets_jobs_explicit_values[jobs2]`、`test_presets_jobs_explicit_values[jobs7]`、`test_presets_jobs_multiconfig_append_replace`（四个新增参考）；P2P 40 个完整 node 逐项按 plan 与原日志对账，全部 PASSED。本报告分母仅本题 45 × 8。

| 候选 | F2P pass / 5 | P2P fail / 40 | 计划 / 实际 reward | pytest rc | F2P 实际失败 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | 0 | 0 / 0 | 1 | 五项全失败 |
| gold | 5 | 0 | 1 / 1 | 0 | 无 |
| coder_a1 | 4 | 0 | 0 / 0 | 1 | default_matches_public_helper |
| coder_a3 | 4 | 0 | 0 / 0 | 1 | default_matches_public_helper |
| deepseek_a1 | 4 | 0 | 0 / 0 | 1 | multiconfig_append_replace |
| deepseek_a4_generator_boundary | 5 | 0 | 1 / 1 | 0 | 无 |
| coder_a2_alternative | 5 | 0 | 1 / 1 | 0 | 无 |
| qwen36_a2_schema_diagnostic | 3 | 0 | 0 / 0 | 1 | explicit_values[jobs2]、[jobs7] |

每轮 48 collected，raw 恰有 45 条完整 PASSED/FAILED 参考 node 状态；每条与 root audit full_reference_states、ledger 原/新增分区逐项一致，无 ERROR、参考 missing/skipped/unaccounted，段外解析 0。另有三条非参考 OS skip，不能混入 45 参考分母：

| raw `-rA` skip 源位置 | reason | 通过有效文件映射的函数 |
| --- | --- | --- |
| `test_cmaketoolchain.py:355` | Only OSX | `test_cmaketoolchain_cmake_system_processor_cross_apple` |
| `test_cmaketoolchain.py:382` | Only OSX | `test_apple_vars_overwrite_user_conf` |
| `test_cmaketoolchain.py:816` | Only Windows | `test_presets_paths_normalization` |

八个原日志均保存这三条源行和 reason；本地用上述 SHA 已核且由完整 patch 重建一致的 effective_test.py 函数/装饰器行范围独立映射。**raw 没有直接打印这三个完整 SKIP node ID**；audit 的完整名称是源位置映射结果。parser 的汇总计数也不作为“45 参考”的定义，参考状态以逐完整 node 对账为准。

## 5. 正式前置/安装、真实退出和清理

八次前置如第 2 节。安装原日志均有完整起止与 rc 标记，RH2_INSTALL_RC=0；install failed commands 为空，未跳过安装，segment completed=true、partial=false。实际 test exec rc 均为 0，pytest rc 如上表；零分是实际测试失败，非 infra/运输失败。观测源码导入 `/testbed/conans/__init__.py`、版本 `2.1.0-dev`、prefix owner PRE=54322，runner 前后 digest 一致。

八个 run rc 原件都是实际 driver argv / returncode=0，stage_error=null。每个 final driver record 为 rows=1、halted/aborted=null、final_status.exit_code=0；candidate cleanup removed=true / rm:ok，manager created_total=removed_total=1，containers_open、supply_open、cleanup_failures 为空。固定 candidate finally、manager grade finally 与 driver finally/manager.close 和实际关闭计数相符。

remote audit 另外保存八组精确 `rh2.run_id=conan15422-formal-r12-v2-<id>` 的容器和网络查询：各 argv 完整，rc=0、stdout/stderr 为空。内部关闭与外层标签确认分别核实，范围限本批标签。

正式远端 job supervisor PID 361368 / child PID 361369；`2026-10-02T22:49:57Z` 至 `23:14:13Z`，finished / returncode=0，stdout 八个 candidate_completed 后有 FORMAL_MATRIX_STAGE_COMPLETED，stderr 为空。交接所述 v1 宿主 Python 错误、未评分记录只作为历史失败说明，不纳入本次 v2 成绩；本报告没有读取旧矩阵重判或重跑。

## 6. 实际 actor 工具原件

actor 工具作业在相同固定 R12 上另 fresh prepare，`A/run_actor.py` 实际调用 devcheck，并显式 `--image` 登记 derived ID。`preflight`、attempt image_override、实际 inspect 和 prelaunch 的 image 全部同一 `a279365…`；不能把该工具探针概括为所有正式 actor 启动入口都已接好镜像。

实际两条公开命令：identity 与 tools，都 rc=0，没有 pytest。capture 和实际轨迹工具结果一致：UID 54321、Python 3.10.14 / testbed interpreter、`/testbed/conan/__init__.py` 与 `/testbed/conans/__init__.py`、HEAD 为固定 base；CMake/CTest 实际 `--version` 均为 3.23.5，Conan entry 可执行且读出 SHA 等于 recipe / 固定 `environment/conan_entry.py`，`conan --version` 为 2.1.0-dev。

真实 Claude Code init 和版本原件为 2.1.205。trajectory 28 行 JSON 均可解析，含三次 message_start、两个 Bash tool call/result 和成功 result；stub 保留三个请求文件，数量对应。harness/actor 退出为 0、完整日志，stderr 为空。两个 generic marker checks（interpreter_in_tool_result、bashenv_denied_for_agent）仍为 false，不能声称所有通用标记或全局权限检查已通过；具体 interpreter/UID 有 capture 和 prelaunch 实测支持。

actor 内部 cleanup container_rm/stub_rc=0，network/relay failures、labeled leftovers、residual_after_force 为空；外层 remote audit 按精确 `rh2.run_id=cpu-a-conan15422-actor-tools-r12-v1` 查容器/网络也均 rc=0、空输出。job PID 357239 / 357240，`2026-10-02T22:40:00Z` 至 `22:41:23Z`，finished / returncode=0、BASELINE_ACTOR_STAGE_COMPLETED，stderr 为空。

| actor 锚点 | SHA256 |
| --- | --- |
| `A/run_actor.py` | `75ced87a23458186e36ce5146538b796e4542a02612eccb35684d72f65f2f6c4` |
| `A/prepared_identity.json` | `5fbf42d94ae3585eab6efe73b127ddbde171bdc42092196dd215edfd117efe81` |
| `A/output/attempt.json` | `a575914c4e517287ee13d129003411c34afee5dfe9b9b31cc843c44dfe3f2dba` |
| `A/output/prelaunch.json` | `a77724e76c430fb5b72cc4187bd9d7feb703cd806c64cfda94081f383ac8e085` |

## 7. 资源边界和停止条件

正式 grader 声明 profile 为 2 CPU、4 GiB、pids 512、shm 64 MiB、tmpfs 1 GiB、network deny_all、UID 54322；八次 `resource_facts=null`。仅有实际 cgroup memory peak 341.266–343.988 MiB（按 1024² 换算，字段名 mem_peak_mb），均非零且无 unavailable。未保存八次完整资源 inspect，不能从 profile 推断实际 CPU/配额/并行度测量。

actor 工具 prelaunch 则保存实际 inspect 和 cgroup probe：NanoCPUs=2000000000，CG_CPU_MAX=`200000 100000`，memory=4294967296 / CG_MEMORY_MAX 同值，UID=54321，pids 512，NNP=1，外部 DNS 和直接 upstream denied、指定 relay connected。它支持这个具体工具作业的 2 CPU/4 GiB 与权限路径观测，不能补全正式八个 grader 未保存的资源原件，也不等于 GPU 或完整功能验收。

本次正式结果、actor 工具可执行与既有 v2 语义是不同证据范围。没有重跑旧测试，没有模型解题或完整 solver 首请求题面交付记录，没有完整编译/链接功能新验收，不据此授予 ordinary probe 或训练资格。

停止条件已满足：固定身份、新 prepare、七份完整原候选与所有冻结文件逐项对应、投影控制面边界明确、360 参考状态和 OS skip 映射闭合、八次正式及 actor 真实退出/内外清理闭合，资源和交付未验证范围明确。本批未发现新增阻断，不扩大运行或修改共享材料。
