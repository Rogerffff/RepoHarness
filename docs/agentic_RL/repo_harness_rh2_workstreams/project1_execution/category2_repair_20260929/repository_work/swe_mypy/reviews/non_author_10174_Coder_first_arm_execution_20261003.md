# 10174 Coder 首轮：非作者执行链窄核

审查日期：2026-10-03。角色：review-standards.md §10.4 Production Tracer。目标仅为 `gpu1003-mypy10174-coder-a1` 的新增本机闭包；不 SSH，不运行 CPU/GPU、模型、容器、项目代码或测试，不修改旧报告、raw、请求或共享文件。本审查者此前已读本题私有评分材料、gold/旧候选与已完成的安装审查，属于 **非 fresh 审查**。

本轮原件支持：固定 code_v8 入口完成 Coder 求解，完整原 FrozenPatch 经同源基线重建和正式 manager 评分；三条安装命令正常完成，正式 1 个 F2P、3 个 P2P 均执行、解析并通过，actor 与 grader 清理均收口。未发现本次候选身份、评分或清理的具体矛盾。这里的执行结论不等于修复语义验收、两模型公平比较或训练准入；raw reward=1 只对应下述材料及四个参考。Coder 来源可以证明到当前服务配置、运行容器、只读模型挂载与题级 gateway/adapter/SSE 对应，不能证明 GPU 驻留权重 SHA。

## 1. 闭包与核验范围

入口是 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-mypy10174-coder-a1_closed_manifest_v1.json`，实际 SHA-256 为 `f7aa33ddcbc3500506477c6bac4fc1739f413dfd89e65564d53dc950432bdaa8`。以下缩写均为仓库相对路径：

- `S`：`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-mypy10174-coder-a1/`。
- `G`：`S/queue_v30/results/gpu1003-mypy10174-coder-a1/`。
- `W`：`S/services_v28/coder/gateway/gpu1003-mypy10174-coder-a1/`。
- `D`：`S/diagnostics/QUEUE_V30_gpu1003-mypy10174-coder-a1_before/`。

独立逐文件读核 **152 件、39,742,093 bytes** 的存在、SHA 和大小，全部匹配：目标结果 29 件、目标 gateway 日志/SSE、目标 adapter JSONL、D 的 14 件、config_queue_v30、config_v30 当前文件、code_v8 闭包成员、本题 prepared 六件、同镜像 wheel 读回以及相关三条固定工具源码。没有把 manifest 声明的 552 件全部记作本题独立核验；其中别题、历史公共窗口和 prior_Q29 文件未分析。另从本机 `frozen_code_v8` 只读补查真实父入口、冻结运输及契约源码，先核与本闭包 `code_v8/source_manifest.json` 的成员 SHA 一致；不执行这些源码。

`config_queue_v30_inputs_v1/inputs_manifest.json` 与 `config_v30/fixed_inputs_manifest.json` 字节相同，SHA 为 `563fbf306464131207cbcf70172be308b0d1d08c7c6b8fb4636c01500288fd94`。其中早期 `ready=false`、`actual_GPU_images_verified=false` 是准备快照状态，不能覆盖后续实际入口、镜像和运行原件；同样也没有静默把它们改为 true。当前闭包仍保留 `paired_request_closed=false`。

## 2. 实际入口与公开交付

`S/gpu1003-mypy10174-coder-a1_terminal_snapshot_v1.json` 的目标命令是 code_v8 的 venv Python 调用 `rh2/experiments/ordinary_gpu_probe_20261002/entry.py --execute`，实际任务、solver、attempt-id 均指向本题 Coder；使用 config_v30/tasks.json、gateway_coder.json、services_v14/coder adapter，日志落 services_v28，gateway 端口 18081。题主请求副本 SHA 为 `117617f74e54c379022cb43e9679d0af07d3465c9f0c05eb03a33679db3c5f7c`；dispatcher 记录的派发请求 SHA 为 `660b06ae781383933baafa93f253ead50145cb3e818fffa8b990f6a25f9cfd3d`。二者分别是题主请求与加上 readiness 等字段后的队列请求，不能混称同一文件摘要。

入口实际 SHA `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`，父 `solve_attempt.py` SHA `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9`，manager SHA `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`。manager 与 code_v5/v7/v8 已核版本相同，**不与本题旧 code_v4/R6 的 b6b10f98… manager 字节相同**；不据此推断整套 runtime 等价。本轮源码消费链是：`entry.load_inputs → CurrentPromptAttempt.run/solve → ClaudeCodeDriver → frozen_transport.export_candidate → source_from_original → grade_original/SWEGradingManager`。入口在求解 finally 中清理，核完停止原因与 gateway 交付后才评分；评分 finally 中 close，基线或清理未确认会抛错。

`prepared/rollout_task_views.jsonl` 中公开 bundle 以 JSON canonical 重算得 `e1cc57aeabbf0261482d0d06da3c08509d54f12c32fc06b4cc6e8eedf8b9e41c`；assignment、baseline、FP 和 grading revision 同值。环境包为 `a79297ff3b78edb32dde4c39a1bb698e4bd4f4fae43590bf17359176f151651d`。公开的实际交付采用 brief 模式：prepared 原 prompt 加 entry 中固定分隔语和本题 development_brief.md，独立重组与 `G/solver_prompt.txt`、`G/attempt/prompt.txt` 逐字节相同。

实际首条 gateway 请求的第一个 user message 有两个文本块：CC system-reminder 为 306 bytes，题目/公开说明块为 **1389 bytes**，SHA `f54cfa4687dd0936a8f0f7d56fc1eb2a93d02dfde61782e3c011f57aa724f7b6`，与上述两份交付 prompt 完全相同。不能把整个 user message 当成这个 prompt。题面仍保留原 CRLF；当前 brief 明示 Python 环境、公开窄测试及镜像初态 test-requirements.txt 的环境准备改动。未以执行回执中的“交付完成”替代首请求原件。

## 3. 完整生成与工具生命周期

`W/requests.jsonl`、`responses.jsonl` 各 69 行，包含 **68 次 `/v1/messages` 生成及 1 次 count_tokens**；计数请求没有 SSE，也不算生成。68 个生成 seq 连续为 1–68，各 response HTTP 200、attempt=1、stream_error=null；68 个 resp_N.sse 均有且仅有一个 message_stop。68 条目标 adapter JSONL 的 SID 全部为本题，逐回合输入/输出 token 数与 gateway response 一致，合计输入 2,869,312、输出 12,327。

首到末实际请求时间为 12:50:15.123876–12:52:36.864446 UTC；adapter 首到末完成记录为 12:50:16.045857–12:52:41.711325 UTC。gateway 强制发送 `Qwen3-Coder-30B-A3B-Instruct`，CC/响应仍报告别名 `slime-actor`；别名本身不证明模型。68 次实际 max_tokens 均 65536。CC 末条 modelUsage 的 maxOutputTokens=32000 是客户端元数据，与实际 request 的 65536 分开保留。

`G/attempt/trajectory.jsonl` 与 harness 原轨迹闭包字节一致，809 行中有 117 条 assistant 事件，但独立按 ID 得到 **67 个 tool_use 与 67 个对应 tool_result**，无遗漏结果或孤立结果：Bash 41、Read 14、Write 10、Edit 2，其中 12 个结果标 is_error。工具错误不等于本次环境失败；最终独立 result 为 success、is_error=false、num_turns=68、stop_reason=end_turn、terminal_reason=completed，permission_denials=[]。没有将模型最终文字中的“所有测试通过”当作正式评分依据。

追加的窄交叉读核：adapter 第 49 条与轨迹 tool `toolu_9038b7202eae828c` 的 old_string、new_string 逐值相等；old 为 3355 bytes、SHA `afb75a8963f6ac1473dba6d7d13bc6e68b965595e0dc6c43651b4304708e9e4d`，new 为 3871 bytes、SHA `ae5d801c9c315ae6560573cc1916d26bfa80381ae58afcb333e53490d207428d`，各含两次 `OVERLAPPING_TYPES_WHITELIST`。resp_49.sse 重组的参数与 adapter 完全相等，raw/SSE 各含四次该标识。轨迹 input 仅多出 `replace_all:false`，未发现新串丢失 whitelist 或少九行的事实。

## 4. 实际镜像、基线、FP 与投影

actor 和 grader 均使用 `sha256:80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f`，不仅是 tasks.json 声明：attempt image_id/container_image_id、grading diagnostics 和目标资源样本均同值。`q30_actual_image_readback_v1.json` 指向同 ID 的原 UID/wheel 读回。reader_54321、reader_54322 的三份 wheel 字节摘要和大小一致，复用之前已核的可读权限证据；本次没有重新运行权限测试。三 wheel 为 packaging-24.1、setuptools-75.1.0、wheel-0.44.0。actor 实际 facts 为 UID/GID 54321，Python 3.9.19 来自 testbed prefix；formal candidate 安装由 grader profile 的 UID 54322 消费，日志 prefix owner pre 为 54322。actor 前缀不可写和 grader 安装前缀可写是不同角色事实。

基线不是 Git clean checkout 猜测或只取跟踪文件。父入口在启动 solver 前采集完整 manifest 和 baseline.tar；本轮 tar 的 **1472 个唯一 regular 成员**，路径集合、每个内容 SHA、契约执行位全部独立对上 manifest。实际 tar 权限只按契约映射为 100644/100755（例如 clean-mypyc.sh 的 0777 映射 100755），没有把完整 POSIX 权限冒称契约 mode。baseline census 中 1472 行对象记录逐项匹配，另有 24 行 EXCL 和两行遗漏缓存计数；actor census 与 grader rebuild census 字节完全相同。遗漏的是政策允许的缓存目录 1、文件 3，**没有净化候选的 .mypy_cache**。

本轮 baseline canonical digest 为 `4dd938f76acfcaaaefa50bbfde72605930b6fc43c84c27f821d0f652455cd38f`。与本题旧 GPU 基线对照，1472 个 entries 及其他字段相同，唯一变化是 runtime_image_digest 从旧镜像改为实际 80418df；因此不能把新旧 baseline canonical 摘要混用。base/materialized HEAD 为 `c8bae06919674b9846e3ff864b0a44592db888eb`，镜像初态 ` M test-requirements.txt` 仍属于基线。

原 FP canonical digest 为 `172bffdc4938b68ee3bd6c80006a2cd8d02c2e16ff5cda6f6fa80f95b5b17c80`，绑定本题 rollout、`#p1`、上述新基线及实际 80418df 镜像；66 项 content_b64 全部重解码并核 content_digest。分类为 projectable，excluded_pathset_changed=false。其组成是 **55 个 .mypy_cache 文件 + 10 个候选复现/调试脚本 + mypy/checkexpr.py**，后者 SHA `b6ccea9c19a1c71988968943cbd6118707d857bd8034bc96e1ec3d7ee2970c52`。评分 projection 的 included_entry_paths 与原 66 项路径及顺序完全一致，没有用清理过的候选、渲染 diff 或旧 Qwen 的 50 路径 projection 替代。实际入口 source_from_original 直接读取 FP、baseline 并建立 FrozenDeltaSource；diff 只供审阅。

## 5. 可信恢复、安装与四个正式参考

本轮 private/host_grading_views.jsonl 固定正式材料；diagnostics 的 materials_identity=`dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065`、scripts_digest=`f111e77dbc1a70b7d469cdb656034aa59c701e9ead3b2ef31e7fa0bd3a45d4ed` 与本题已核材料相同，revision 为 mypy10174-strict-equality-v1。可信 setup 原件有恢复文件 1/预期 1、apply RC0、RH2_SETUP_OK=1；保护文件 1/1、目录 3、missing=0、RH2_PROTECT_OK=1。runner 安装/测试前后 SHA 均 `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4`；候选没有修改 conftest/fixture 或正式测试文件。baseline 与投影之外的这一步恢复/保护没有删除那十份候选脚本。

正式 eval.log 在 install 段先设置 `set -E` 和 `ERR` trap，失败会输出 `RH2_INSTALL_CMD_FAILED=$? ${BASH_COMMAND}`。逐条核原件：

| 正式命令 | 原件中的完成依据 | RC 口径 |
| --- | --- | --- |
| `python -m pip install -r test-requirements.txt` | 正常列出已满足依赖，随后进入第二条；没有实际失败 marker | 完整 ERR 监测与输出支持成功；未单独持久化成功数字 RC |
| `python -m pip install -e .` | Obtaining file:///testbed；build/editable 各阶段 done；Successfully built/installed mypy | 同上，且有完整成功输出 |
| `pip install pytest pytest-xdist` | 已满足依赖并正常结束 | 最后命令 RC0；不是前两条 RC 的替代证据 |
| 正式 `pytest -n0 -rA -k …` | 四条 PASSED 与 `4 passed, 9419 deselected` | RH2_TEST_RC=0、candidate exec RC0 |

诊断 `install_failed_commands=[]`、install_skipped=false、log_partial=false、candidate_segment_completed=true；本次三条没有旧 GPU 的 editable EACCES。不能把“日志存在 trap 声明”当失败 marker，也不能只据 install_rc_last_command=0 宣称全部安装成功。当前闭包没有三个独立成功数字 RC 数组，结论依据是上述正式完整命令输出和 ERR 监测；没有追加 owner preflight 安装或独立探针来改变正式候选状态。

实际测试命令为 `pytest -n0 -rA -k "testOverlappingAnyTypeWithoutStrictOptional or testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional or testUnimportedHintAny"`。原 pytest 段收集 9423 项，选择四项；以下 nodeid 均在同一正式段 PASSED：

- 原 F2P：`mypy/test/testcheck.py::TypeCheckSuite::testOverlappingAnyTypeWithoutStrictOptional`。
- 原 P2P：`mypy/test/testcheck.py::TypeCheckSuite::testUnimportedHintAnyLower`、`mypy/test/testcheck.py::TypeCheckSuite::testUnimportedHintAny`。
- 新增 P2P：`mypy/test/testcheck.py::TypeCheckSuite::testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`。

parser 原件 num_parsed_tests=4、outside segment=0、reference_missing/reference_skipped 均空，各分区 success 与 private refs 逐项相同。status/report 的 resolved/reward=1、F2P 1/1、P2P failure 0/3 因而有正式原日志支持；不从四项结果外推全测试集或所有严格可选类型语义。正式导入观测是 `/testbed/mypy/__init__.py`，不是候选前后每个模块独立 SHA/loader 探针；本次没有这些额外模块导入观测。

## 6. 终止、双层清理与计量

原 harness 最终 RC0、termination=completed、日志完整；末条 result=end_turn。冻结前先停止 actor UID 残留，residual=0；gateway 的独立 session_close 原件 revoked=true、active_requests=0、drained=true。12:52:47.740304 UTC 的 quiescence 原件为进程零残留和两次工作区摘要稳定，随后冻结并退出 actor。actor cleanup container_rm=0、container_left 空，带本题标签的 containers/networks 为空，relay/network failures 均空。grader status 中 close 建 1、移除 1、leases_total=1，containers_open/supply_open/cleanup_failures 都为空，cleanup_ok=true。

terminal snapshot 记录外层任务 12:49:37.012153–12:54:24.559656 UTC、exit_code=0、evidence_ready；它引用的 `queue_v30/dispatcher/gpu1003-mypy10174-coder-a1.log` 未进入当前本机闭包，本闭包也没有本题 success.json/done/systemd journal 原件。故本报告不宣称独立核实 systemd 单元成功，尤其不把 not-found/default RC0 当成功；执行结束依据为实际 harness result/RC、drain、原 FP 导出、正式 eval.log 和两层清理。缺外层单元原件不改写这些内层已证事实。

solve_seconds=150.336；CC duration_ms=146652、duration_api_ms=125271，二者有包含关系。grader report total=93.986s，candidate install marker=2.802s、test marker=1.695s，manager test phase=5.015764s，计时层不同，不能嵌套相加。CC total_cost_usd=14.654735 是客户端模型别名元数据，不是自部署 GPU 的实际费用。

目标闭合 resource JSONL 有 22 个完整样本，实际首末为 12:49:22.197375–12:54:38.740182 UTC，约 15 秒一采。样本匹配本题 actor 12 次、relay 12 次、grader 7 次（最后一次 PID0/cgroup 空），没有将共享模型容器或别题计入本题。可读样本的 actor memory.peak 最大 1,025,585,152 bytes、grader 最大 275,460,096 bytes；它们是不同容器不同阶段的采样事实，不合称同时峰值。可读样本 OOM kill 均零；不证明采样间所有事件为零。manager peak_memory_mb=393.059 与资源采样口径不同；resource_facts=null、env_qualification=absent 原样保留。GPU 字段是共享设备读数，不据此估本题独占利用率或 token 吞吐。

## 7. Coder 来源边界与停止条件

D capture 在 12:49:36.721124–12:49:36.919107 UTC 采集，结束早于 attempt 开始 0.591011 秒（外层 dispatcher 开始前 0.093046 秒）。engine/adapter 的 actual 和 after inspect 均发生在这次 **开跑前 capture 内**，不是题后逐 job inspect。engine CID=`0752efbc6887af4d7cf59e583213447dd7f6488887c060d67df49baff3933af2`、start=03:40:20.177710856Z、restart=0；adapter CID=`d761d7ad2a8b744f2fc14dcd02b2e3742934f378ca4a30c855bc4e651d459bb1`、start=03:47:59.985612608Z、restart=0；运行状态、PID 与历史绑定一致。engine `/model` 和 adapter `/model` 都是同一 Coder 目录的只读挂载；adapter 实际命令使用 code_v4 的 qwen_adapter_server.py 和 qwen3_coder parser，不能将求解 code_v8 说成服务 adapter 也换到 code_v8。

实际 engine 命令及 HTTP server_info/model_info 支持 `/model`、Qwen3MoeForCausalLM、bfloat16、TP1、context 196608、max-running=1、mem-fraction=0.90；HTTP revision=null、weight_version=default。fixed config_v30 与 live services_v28 gateway 配置去掉控制密钥文件路径后逐值相同，实际 upstream=18083、force_model=Coder、allowed_sessions 仅本题。结合这次 68 条题级 adapter 与 SSE 可证明运营来源，不能只用 service config 或 alias 推 checkpoint 身份。

download manifest SHA=`5783533eae085661e3b3cde2e46ee46c9dbce0c05154d6028f6e46aa7260de39`，声明 repo `Qwen/Qwen3-Coder-30B-A3B-Instruct`、revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`。本次 stat 的 25 个列出文件与 manifest 列表大小一致，含 16 个 safetensors；顶层 files_count=28 与列表 25 的计数差异保留，不能称完整 28 件已核。capture 明确 individual_weight_file_hashes_repeated=false、GPU_memory_weight_hash_attestation=false；本次没有重新核各权重 SHA，更没有 GPU 驻留权重加密证明。gateway_audit checkpoint_identity_verified=false 仍适用。

**有限来源缺项**：D/backend_continuous_log.txt 最后两条是 12:49:36 的身份 HTTP 读回，早于首生成 12:50:15；未包含本题 68 次生成期间的逐请求后端完成记录。不能用旧 Q12/Q13、15184 或其他 job 的记录冒称覆盖本题。外层 dispatcher log/success/done/journal 缺项如上一节所述。若题主需要进一步收口这些运营层声明，最小接续仅为已有本题窗口后端完成原件和外层结束原件的本机读核；本报告不要求或执行新增远端采样、模型重跑、权重审查或通用 gate。已证的正式评分及内层生命周期无当前具体阻断；新增范围至此停止。

## 8. 关键原件 SHA-256

下表是本次独立读过并与闭包匹配的原件；canonical digest 与文件 SHA 是不同口径，前文已分别写明。其余已核文件可由固定 manifest 的对应路径定位，不把 summary/回执列成评分替代品。

| 原件路径 | SHA-256 |
| --- | --- |
| `G/input_check.json` | `198dce3ec4d0cbcfa13897a56de6bd06cdd47d57116170076e06accf2d981a99` |
| `G/attempt/attempt.json` | `b84aff32eb6c5bd0658b4b00d45314012d3d7a4fa56ddc83e012a56352813c55` |
| `G/attempt/trajectory.jsonl` | `b21c5f45f3b81eaecd81eaeb27de9746d23e1064648dfb485324a5a7539acc38` |
| `W/requests.jsonl` | `5e592728bfdada0eaac1382aba6bc3c6ecc9cef6f43e2e923c2ff890dfb460be` |
| `W/responses.jsonl` | `0c943560b6cf940688e1725576a9cee22ad1f6dc3f691950c6c03537dad11a6b` |
| `S/services_v14/coder/adapter/gpu1003-mypy10174-coder-a1.turns.jsonl` | `2b1c4f244757f05ec88eef4d831a301e78bad7b4561d425654fba059ca3c6363` |
| `G/attempt/frozen/frozen_patch.json` | `fdd12eaefbb74535c10f9041c97d3574d4b4aa9ea337b162500b7ba3fa5d0648` |
| `G/attempt/frozen/baseline_manifest.json` | `b58c6e60b28e8145a95dc54869142363164aebe39a4425811655a61eb061c46c` |
| `G/attempt/frozen/baseline.tar` | `f76975a2c93aab3f09c1501ce0b9ae986190b2e28555ebd4b21fde295d55e656` |
| `G/attempt/frozen/baseline_census.txt` 与 `G/grading/baseline_rebuild_census.txt` | `67c508e55dd3aa024a3e1f1c9c2f5e5e09b370ea02757740724344978a19bcf7` |
| `G/grading/projection.json` | `a44d1e62825d4a748576869963815b0de71465241c064c3a44e3f8fc83d00268` |
| `G/grading/eval_logs/evallog_gpu1003-mypy10174-coder-_8acef403.eval.log` | `effaa652c04deec6f2595b4389096afd290705e3886a80ea7d1655d6893da74e` |
| 同名 `.diagnostics.json` | `413d3cc82fd1fd5733d990e35766a4b63244e99cdec524049ccd38cd2503d026` |
| `G/grading/status.json` | `c2f3f1edbb5e9c68065b7e9406be5ebad2fe9b504b645ab0c8f817d451acbd41` |
| `W/session_close.jsonl` | `394cc597b825876629f7244707987e3a734cab3eeaa4ace8c9f0571d1e6a1440` |
| `D/capture_receipt.json` | `3cb7370c51fdf553764c42b1e93979a788c5cb15780bb6373d746a0705fb1d9e` |
| `D/backend_continuous_log.txt` | `bbea4a4b4271a7094f2fa7a1f37b545a41608e957e47431099183af96d16b4d2` |
| `S/gpu1003-mypy10174-coder-a1_terminal_snapshot_v1.json` | `9eb9915b7575f1fa122401fa60bb3c9456cefe661a37180f8c0afe655b13b805` |
| `S/gpu1003-mypy10174-coder-a1_closed_resource_v1.jsonl` | `9c7483b79e19e121c5b5e6f4cb33cb8f1a3642b2cf862249d76ba641b9e74bc7` |
