# DVC 9395 双模型回执：非作者执行证据核查

核查日期：2026-10-04。范围：本机只读原件及标准库机械核读；此轮已获授权读取评分私有视图，身份不是 fresh 公开读者。没有模型求解、测试重跑、Docker、SSH、源码修改、current/board 修改或用户线程消息。旧 Coder 运行与同原 FP CPU 评分按固定版本复用。

## 结论与必须纠正的口径

新 Qwen 执行证据链可核实：原 raw reward 为 0，outcome 为 unresolved；安装 RC=0、pytest RC=1，harness 完整结束，solver 与 grader 两层 cleanup 均为 true。实际 41 节点是 37 passed / 4 failed；绑定实际 40 条正式 references 后为 **F2P 1/3、P2P 36/37**，另有未评分的原 import 节点 FAILED。任务转述的“P37/37”错误，原双模型总回执与 Qwen 机械回执本身均写 P2P fail=1/37。不要把实际 37 个 passed 当成 37 个 P2P passed。

Coder 原 GPU raw=null、entry RC=1、cleanup=false 保持。已核收的同原 FP CPU 补评 raw=0、F2P 0/3、P2P 37/37，属于独立评分补充，不替换旧 GPU null、不构成新模型样本。本轮不复读完整旧轨迹，不重新语义验收。

本报告仅完成非作者执行核查，不 ACK、不关闭配对请求、不作轨迹/候选语义验收或训练资格认定。`each_model_first_once_complete` 只可解释为两次首次求解及其证据已返回；不能解释为原 Coder GPU 入口与评分清理成功。

## 封存身份、FP 与基线

- Qwen closed_manifest SHA256 `4d93b2f811c5dd94923ef4a0a5b6182407c6cdcb31193614dde1b0b4fe12506f`；独立逐一读取 **429 成员、45,840,124 字节**，大小与 SHA 全匹配，无缺件或错误。清单及同步回执是封存元数据，不把它们额外算成成员。全部成员核读记录见本报告配套 local readback JSON 的 `manifest.verified_members`。
- 原 FP JSON 文件身份与内容规范身份分别列于证据表；以 UTF-8、sort_keys、紧凑 separators 重算规范 SHA256 为 `bca0a3a7a04f2259a21b1f0aa7904b12ceff777f234dc2bde16f28345f45d476`，全部 3 条 b64 内容摘要匹配。原 FP 包含 `dvc/commands/repro.py`、`dvc/stage/__init__.py`、`tests/func/test_run_cache.py`。
- 评分 projection 绑定该同一 FP / rollout / physical attempt，只应用两个 DVC 源码路径；测试文件改动留在完整 FP 中而被评分投影排除。因此原 FP 的“有测试修改”与评分 report 的 `test_files_modified=false` 是不同范围，不能将后者泛化成模型没有改测试。投影有效路径与原件见证据表；本轮不评价改动意图。
- 基线规范 SHA256 `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`。baseline.tar 的 **615 条**逐项核验内容、对象类型和 mode 均匹配 baseline_manifest，无额外或缺失成员，archive SHA256 `a91aea77992a789ede590526ffd72200106afb99ff10ccc1cc655e139d1eb3ce`。原 census 与 grader rebuild census 字节相同；641 行中 615 行为实质文件、24 行为 EXCL、2 行为零缓存省略计数，实质文件行全部匹配。不能将641行误报为641个基线文件。
- baseline 的 environment_package_digest=null 保留；实际任务 assignment 和评分材料中的环境摘要另外绑定为 `62df73d0a7bf30057b6b4e585cc799a09c853c320310e32f93f9f7b6aaaf437e`，不回填 baseline 的 null。

## 实际输入及两侧差异

独立对照两侧原 attempt.json、input_check.json 与冻结材料字节：任务、镜像、base commit、public bundle、原/交付 prompt、baseline、模型预算、评分材料与预算一致。两侧 owner request、prepared prompts、rollout view、host grading view 原件字节均相同。实际交付 prompt SHA256 `6aeed5c0b63922deb81519b033392a11ab4f2af0be1f24f954e66536bc41f3a4`；Qwen 第一条真实网关请求的用户文本 UTF-8 字节与 attempt/prompt.txt 完全相同，包含公开开发说明。原题面中的 CRLF 保持；本机 read_text 换行归一化不能用作不一致证据。

两侧实际 profile 唯一差异是 `network.model_proxy_upstream`：Coder `172.17.0.1:18081`、Qwen `172.17.0.1:18082`。对应 profile digest 为 Coder `4a6435bc16d26c517b34eb1a4e40e83cdeef3ef08e813a136e9ae06ed67e22b6`、Qwen `c731fff97bcd8ed6be3f31ac2108980dc549f0e5a75403f9738b2b3b2537e500`。模型端点、模型/parser服务差异是配对的预期模型差异，不将它们混成同权重运行。

| 预算 | 两侧实际绑定 |
| --- | --- |
| 上下文 / 单请求输出 / CC回合 | 196608 / 65536 / 240 |
| solver / gateway请求 / first byte / adapter idle | 10800s / 1024 / 1800s / 14400s |
| grading whole / setup / apply / test | 3600s / 900s / 120s / 1800s |

setup900 已在两侧 input_check 的实际 preparation policy 与 grading_budgets 中绑定，并出现在 Qwen 注册请求；策略记录 original300 → effective900。本輪没有改变预算。评分诊断中 grader_trusted_setup 228.024776s、总评分268.066s，未见该预算超时。配置检查的 `config_only=true`/`runtime_request_and_sglang_readback_verified=false` 原值保留；Qwen 实际服务回读与请求另由下面的 live capture/gateway 原件支持。

## 实际节点与40条正式引用

原日志 `grading/eval_logs/evallog_gpu1003-dvc9395-qwen36-a_89f3ee6d.eval.log` 的命令在675行，684行 collected41；6309–6349行给出全部41节点，6350行总计4 failed/37 passed。以冻结 `host_grading_views.jsonl` 的实际 fail_to_pass / pass_to_pass 列表绑定，3F/37P均唯一、无缺失、无跳过；原 import 是唯一未评分节点。official parser 的42条含额外捕获日志项 `dvc.commands.freeze:freeze.py:19=ERROR`，该项不是pytest节点或正式reference。

| 分区 | 节点 | 实际状态 | 原日志行 |
| --- | --- | --- | --- |
| P2P | `tests/func/test_repro_multistage.py::test_non_existing_stage_name` | PASSED | 6309 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_frozen` | PASSED | 6310 |
| P2P | `tests/func/test_repro_multistage.py::test_downstream` | PASSED | 6311 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_cmd_changes` | PASSED | 6312 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_added_in_dvcfile` | PASSED | 6313 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_is_added_in_dvcfile` | PASSED | 6314 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_moved` | PASSED | 6315 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_out_overlaps_others_stage_outs` | PASSED | 6316 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_added_does_not_exist` | PASSED | 6317 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_added_does_not_exist` | PASSED | 6318 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_lockfile_gets_deleted` | PASSED | 6319 |
| P2P | `tests/func/test_repro_multistage.py::test_cyclic_graph_error` | PASSED | 6320 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_multiple_params` | PASSED | 6321 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[True]` | PASSED | 6322 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[False]` | PASSED | 6323 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[True]` | PASSED | 6324 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[False]` | PASSED | 6325 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_pulls_intermediate_out` | PASSED | 6326 |
| F2P | `tests/func/test_repro_multistage.py::test_pull_recovers_frozen_stage_for_downstream` | PASSED | 6327 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_dry_preserves_workspace_and_cache[source]` | PASSED | 6328 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_dry_preserves_workspace_and_cache[output]` | PASSED | 6329 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_when_nothing_missing[normal]` | PASSED | 6330 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_when_nothing_missing[dry]` | PASSED | 6331 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_still_errors_for_missing_source` | PASSED | 6332 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_no_run_cache_does_not_download_runs` | PASSED | 6333 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_existing_output_without_hash_can_run` | PASSED | 6334 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_changed_dependency_can_recompute` | PASSED | 6335 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_restores_from_http_with_local_run_cache` | PASSED | 6336 |
| P2P | `tests/func/test_run_cache.py::test_push_pull` | PASSED | 6337 |
| P2P | `tests/func/test_run_cache.py::test_restore` | PASSED | 6338 |
| P2P | `tests/func/test_run_cache.py::test_save` | PASSED | 6339 |
| P2P | `tests/func/test_run_cache.py::test_do_not_save_on_no_exec_and_dry` | PASSED | 6340 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[metrics_no_cache-True]` | PASSED | 6341 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[plots_no_cache-True]` | PASSED | 6342 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[outs_no_cache-False]` | PASSED | 6343 |
| P2P | `tests/func/test_run_cache.py::test_memory_for_multiple_runs_of_same_stage` | PASSED | 6344 |
| P2P | `tests/func/test_run_cache.py::test_memory_runs_of_multiple_stages` | PASSED | 6345 |
| F2P | `tests/func/test_repro_multistage.py::test_repro_pulls_mising_data_source` | FAILED | 6346 |
| unscored | `tests/func/test_repro_multistage.py::test_repro_pulls_mising_import` | FAILED | 6347 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_preserves_modified_source` | FAILED | 6348 |
| F2P | `tests/func/test_run_cache.py::test_restore_pull` | FAILED | 6349 |

安装标记：431行 INSTALL_START，665行 INSTALL_RC=0，668行 INSTALL_END；673行 TEST_START、6354行 TEST_RC=1、6357行 TEST_END。原stdout与诊断一致，install3.933s、test16.848s；runner阶段test21.321s是另一个计时范围。这里核既有记录一致性，没有用原stdout解决候选可伪造stdout的信任边界，也没有重新执行验证。

## checkpoint、live capture 与 SSE

Qwen固定下载身份：repo `Qwen/Qwen3.6-35B-A3B`、revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；下载清单 SHA256 `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab` 与 engine binding/live capture 一致。**下载清单头部 files_count=40，但实际 files 列表只有37条**，总字节71,926,788,362与37条求和一致；实际大小回读同为37条、全部名称/大小匹配，其中26条为完整00001–00026 safetensors shards。该元数据计数不一致必须显式保留，不能说本轮核了40个实际模型文件，也不能凭差值认定缺了3片权重。

live capture 时间16:51:21.908800–16:51:22.089278 UTC，早于本Qwen注册启动16:51:22.212029；它不是为旧Coder补造运行时capture。engine实际Id `5a023c27c62bb2f37cf060429a59f96b726d1b404cf756bc8052564037bf3349`、adapter Id `aff52a71c621b2520b42350259a2992a18c0ed40ea209906357d3c2a552fc36d`，before/after inspect完全一致，restart均0；模型挂载只读。SGLang实际回读/model path/tokenizer path为 `/model`、context196608、bfloat16、tp1；adapter采样defaults为temperature1.0、top_p0.95、top_k20、max_new_tokens65536，idle启动命令14400。模板/配置字节均已通过全成员SHA核验。

限制：没有重新对71.9GB模型权重逐片计算SHA，没有GPU内存权重证明；gateway中的 `slime-actor` 别名本身不证明checkpoint身份，gateway_audit的 `checkpoint_identity_verified=false` 保留。身份证据是固定下载清单、只读挂载、实际容器及HTTP回读的组合，不能升级为硬件级权重证明。

独立核88条真实requests、88条responses与resp_1–88.sse：seq完整唯一、全部attempt1/status200/stream=true、无stream_error；每份SSE大小匹配并有1个message_start、闭合content blocks、1个终止message_stop，无error事件，stop_reason与回执一致（87 tool_use、1 end_turn）。88请求均送出max_tokens65536，模型路由为Qwen3.6-35B-A3B；第一请求实际交付prompt已核。没有请求恢复/重试样本。SSE逐件SHA、size、stop记录见local readback。

CC result显示num_turns89、harness completed；summary中的modelUsage.maxOutputTokens=32000是元数据，与88条实际请求65536分开报告。最大观察输出只有1110 tokens，不能以这次短输出证明65536上限实际可达；此差异未造成本次截断/超时证据，也不据此重标基础设施失败。

## 终止、清理与观测边界

Qwen原attempt：harness_exit_code0、termination completed、solve260.0s；solver停止屏障residual0、quiescence双读稳定、gateway session revoked且active_requests0/drained=true。solver cleanup记录容器rm0、容器/relay/network无剩余；独立评分status manager_close为created1/removed1、containers_open/supply_open/cleanup_failures均空、regrade0，cleanup=true。

退出证明使用当前result完整RC0加精确unit的PID1 journal成功事件：`rh2-gpu1003-dvc9395-qwen36-a1-qwen-tail2-v1.service`，17:00:54.827670 UTC的Deactivated successfully（journal.jsonl第2行）。退休unit的not-found/default ExecMainStatus0不作为退出证明；已核的success.json也明确禁止这样使用。这里只审查已封存清理/日志事实，不声称本机再次查询远端当前资源。

资源范围：封存39个monitor样本、monitor_gaps_unknown=true、resource_facts=null，报告container_peak_memory_mb960.875；不能认定资源全程完整可观测。对照模型一次性差异、安装/test计时、轨迹结构与资源限制不改变测试失败性质。

## 精确证据身份及复用范围

以下完整SHA为文件字节身份；FP/baseline规范摘要另在上文列出。Q表示 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dvc9395-qwen36-a1`，QA表示Q下 `queue_qwen_tail2_v1/results/gpu1003-dvc9395-qwen36-a1`。所有长路径和40个重点pins均保存于local readback的 `evidence_pins`；429成员pins与88份SSE pins亦完整保存。

| 原件 | SHA256 |
| --- | --- |
| `Q/qwen_tail2_closed_v1/gpu1003-dvc9395-qwen36-a1/closed_manifest.json` | `4d93b2f811c5dd94923ef4a0a5b6182407c6cdcb31193614dde1b0b4fe12506f` |
| `QA/attempt/attempt.json` | `8c47f9ef6aecbe36b728c672d422e9b300729a1263e28fd60475857666b26f99` |
| `QA/attempt/frozen/frozen_patch.json` | `f64380b3567fd0e7967a4ff46f1062910a2682a8912861e97940dc99b8295ab0` |
| `QA/attempt/frozen/baseline_manifest.json` | `b41f4a530df5841ab7bc6f9c9f9344f4e3bc271649dc50f3345d5a444178d6d1` |
| `QA/attempt/frozen/baseline.tar` | `a91aea77992a789ede590526ffd72200106afb99ff10ccc1cc655e139d1eb3ce` |
| `QA/grading/baseline_rebuild_census.txt` | `87dedd5c5e50786ce2c71f166495671c6c2d5f867894a1b620df999e67d4fd50` |
| `QA/grading/projection.json` | `4b790a837397b90f6372386b8cb333d7dcc3dadd8f4615496b63916c382e5622` |
| `QA/grading/eval_logs/evallog_gpu1003-dvc9395-qwen36-a_89f3ee6d.eval.log` | `e69b70cd673b8df8c6c30f812798ef1eed01bcfd9a08178c7e3384ed7ca272fd` |
| `Q/prepared_remaining_eight_code8_v1/dvc9395/private/host_grading_views.jsonl` | `21198a8ee0f8b99e693b93110834b00d4445f5de4755a933c4a7708da51ab34e` |
| `Q/diagnostics/QUEUE_QWEN_TAIL2_V1_gpu1003-dvc9395-qwen36-a1_before/capture_receipt.json` | `2ae12b3cf951dea64af12128efe50cd9106f7b2cb91f3a3e0c8418d3e637d1c4` |
| `Q/diagnostics/QUEUE_QWEN_TAIL2_V1_gpu1003-dvc9395-qwen36-a1_before/download_manifest_actual.json` | `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab` |
| `Q/diagnostics/QUEUE_QWEN_TAIL2_V1_gpu1003-dvc9395-qwen36-a1_before/model_file_sizes_actual.json` | `cb0718f57a6ec078826434d95f110af217b297810191ecacbf283c913a8e24a6` |
| `Q/diagnostics/QUEUE_QWEN_TAIL2_V1_gpu1003-dvc9395-qwen36-a1_before/current_terminal_evidence_v3/success.json` | `b67d22663bc5d1add52fa2d606ae2fa19dce00b974efa10dfffd7764cd115ae7` |
| `Q/diagnostics/QUEUE_QWEN_TAIL2_V1_gpu1003-dvc9395-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl` | `b3633ae7053bc586d3d9591fa696060f6d8d56ba8abe34860b80ae6ad472193d` |
| `Q/services_qwen_code8_v1/qwen36/gateway/tail2-v1/gpu1003-dvc9395-qwen36-a1/requests.jsonl` | `3e4ae33d2b5fb415796fe70baae7f8a3ecb5e7b0dc9a267db6814c5e96adad03` |
| `Q/services_qwen_code8_v1/qwen36/gateway/tail2-v1/gpu1003-dvc9395-qwen36-a1/responses.jsonl` | `df1eaf20a936c99f0283e881550a6e0a29303d76ebd6e6cb18e8a3f422463d9f` |
| `runs/ordinary_gpu_probe_20261002/migration_20261003/swe-dvc9395-behavior-r20-v1-20261003_pair_execution_receipt_v1.json` | `eed35d58c543a7ef411042cbe310b4d5553034658ccbf75166354e6f53bbfe4c` |
| `runs/ordinary_gpu_probe_20261002/migration_20261003/dvc9395_qwen36_execution_receipt_v1/execution_receipt.json` | `55f1bfda379232313c6c187af4926d791ad95ec1514542f3c2b8604118ca29fe` |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_acceptance_v1.json` | `5c48c93d0b7670edcc22cd937daf49361cc5054787d88851437a9287e302e52b` |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/reviews/non_author_dvc9395_same_original_fp_cpu_runtime_20261003_v1.json` | `940a96ba9032d26911f9e38072551f6b070bbb1ee0c19bf409eb6c02bbceac8b` |
| `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dvc9395-coder-a1/queue_v27/results/gpu1003-dvc9395-coder-a1/attempt/attempt.json` | `1561b5b242bc34cc0164295ede46adcbf080a74fa0504aaf2da6ace666771ae0` |

Coder CPU验收JSON固定SHA256 `5c48c93d0b7670edcc22cd937daf49361cc5054787d88851437a9287e302e52b`，非作者runtime核查JSON固定SHA256 `940a96ba9032d26911f9e38072551f6b070bbb1ee0c19bf409eb6c02bbceac8b`；此轮对它们核身份并按版本复用，不重做已核的旧FP/CPU全链。总回执不将CPU补评raw0改写成原GPU raw0；旧接受记录的Qwen pending字段是当时状态，不回写历史原件。

配套机械局部核读JSON：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/reviews/non_author_dvc9395_pair_execution_local_readback_20261004_v1.json`，SHA256 `983903c2ca0573459839b5a84066bdb9911cd2f0a2790efcc9bf58745dbd5c6b`。本报告仅新增此报告、配套review JSON及自有local readback JSON；评分结果与材料原件均保持。
