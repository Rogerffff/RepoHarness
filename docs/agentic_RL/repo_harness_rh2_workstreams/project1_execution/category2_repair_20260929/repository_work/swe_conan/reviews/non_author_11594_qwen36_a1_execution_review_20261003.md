# Conan11594 Qwen 首臂：非作者执行窄核

审查日期：2026-10-03。审查者：`conan11594_qwen_execution_recover`，独立于候选、封包及执行回执作者。对象：`gpu1003-conan11594-qwen36-a1`，请求 `swe-conan11594-r12-briefv2-20261003-v1`。

**结论：`execution_evidence_verified_with_scope_limits`。本次 Qwen 首臂的执行、材料交付、原 FrozenPatch 评分运输与作业闭合可核销；未发现本 scope 内新增 blocker。** 原评分 `reward=1 / resolved` 有完整原日志支撑。19 个资源切片及权重未重新全量散列的限制仍保留。候选语义、题级准入与训练资格由对应审查承担，本报告不作结论。

范围与授权来自[现行分类二协作流程](../../../coordination_workflow_20261003.md)。只在本地使用 Python 标准库读取原件；没有导入项目模块、执行项目代码、模型调用、远端、Docker、CPU/GPU 作业或项目测试。未读取 root 私有 audit 作为结论依据；被中断 reviewer 的初步消息未用作完成证据。仅新增本报告及[结构化核对结果](non_author_11594_qwen36_a1_execution_review_20261003.json)，原件与共享账本保持原状。

## 证据入口与完整性

权威输入为[冻结快照](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1)及其[closed_manifest.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan11594-qwen36-a1/closed_manifest.json)。本地逐件重算 SHA-256 和字节数，**183/183 件、20,795,215 字节全部匹配**；不以 sync 回执的 `true` 代替本次重算。

| 固定入口 | 本次重算 SHA-256 |
| --- | --- |
| closed manifest | `380a6c4594a029a8248c98f67222e85b01079eb2c447924834cc3f30d51d0caf` |
| 新 Qwen 执行回执 | `e82526fda4bae85e621aaceecd4f4d2b79789ae978af59f777d5ed16594e1770` |
| 配对执行回执 | `2ba6709ce574cd4a19879c5b9378cb26e96abd141d21f1a04486ae1fd1a8d7c6` |
| 原题主 request | `274c7e394eda8da6b3dd1f2161754338a721bc4fa71f300ed9a5db237a65b581` |

两份新回执分别见[Qwen 执行回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan11594-qwen36-a1_execution_receipt_v1.json)、[配对回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan11594-r12-briefv2-20261003-v1_pair_execution_receipt_v1.json)。其中 owner 语义待分析状态是回执产生时的记录；本审查不改写它。

## baseline → 原 FrozenPatch → scoring projection

从[baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/attempt/frozen/baseline_manifest.json) canonical JSON 重算得到 `sha256:df11bdaf691c19123e35a09df765e698363900f926515553b629a3b7903c03f4`。[baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/attempt/frozen/baseline.tar) 10,311,680 字节，1,243 项均为 regular；逐项比较路径、对象类型、Git 执行位 mode 和内容 SHA，无缺项、重复项或差异。没有将 tar 元数据直接等同于 Git mode。

原[baseline census](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/attempt/frozen/baseline_census.txt)中 1,243 条 regular 完全重建 manifest entries；`baseline_policy_v2` digest 重算为 `sha256:77527b33576220ebe06770f4372eeb400fa5b07d0e1f0aa65804373c37866c27`。[grader rebuild census](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/grading/baseline_rebuild_census.txt)与原 census **逐字节相同**，共同 SHA `177322a7402b9edbead98100ae8440f589b1379f643cf8980291ccebed2502b3`，与 `baseline_rebuild_passed=true` 相互支撑；本轮没有实际启动新 grader 重建。

[原 FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/attempt/frozen/frozen_patch.json) canonical digest 重算为 `sha256:7397e59387d0333d0152a081dc26c16854b5099293c019dcacbb6d3296b845d8`。task、job、physical attempt `#p1`、baseline、public bundle、运行镜像及 base HEAD 均与本作业原记录相接。逐项 base64 解码后内容 digest 正确：

| 原 FP entry | 运输内容 |
| --- | --- |
| `conan/tools/cmake/cmake.py` | modify、regular、100644；6,950 字节；内容 SHA `08e110a8adfee3e5dfde9fa350e6f64239a29bf37aa08e3bf67f5d67cef0421d` |
| `conans/test/unittests/tools/cmake/test_cmake_test_target.py` | add、regular、100644；5,429 字节；内容 SHA `7a17ae8e64aa11e13e72fac574d084dc80969680674adf30815d9e6af65f60d8` |

[完整审阅 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/attempt/candidate/conan-io__conan-11594.diff)为 6,803 字节、2 个文件段，SHA `2450b9f97dcdb0b970d149bca8a35a8cd99c5096702e40a6331e0ee9c4f9fe16`。本地从 baseline 原字节按每个 hunk 的旧行、上下文和行数重建两个新文件，与 FP 两项的完整内容及新增文件 mode 一致。[projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/grading/projection.json)保留同两项，job/physical attempt/FP identity 正确；实际 entry-set digest 重算为 `sha256:bbd1999637c6ea27fd9322e418d8b259c4dd3a73bf48f24ffd75df12396fc93f`，与 report hygiene 相同。这是运输身份核对，不解释候选语义。

## 同一请求和固定材料的实际消费

[Qwen 派发 request](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/requests/gpu1003-conan11594-qwen36-a1.json)列出 53 个输入 SHA，本地均匹配。[first10 fixed inputs](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/config_qwen_first10_v1/fixed_inputs_manifest.json)本题 target 中 43 个 material map 项与实际 request 相同（包括共用封包材料）；task config 与 fixed target 完全一致。actual input_check 的 prepared manifest、host grading artifact、grading materials identity、assignment、grading revision、public delivery、baseline policy、spec overrides 和 grading budgets 与冻结 expected record 相同。前置 `ready=false`、`runtime_identity_capture_pending` 等字段保留原历史，不用于否认后来实际运行，也不作为完成证明。

与旧 Coder 原件做 identity 对照：prepared manifest `c986845ec686abd17538c6a9ef52e82c2efc37b8a686b123e3fb339a3b4dec6e`、host grading `16b27d2a16852fc23f1a3f2e64956e86a781f98315088db7c34aaee8ef507f6b`、grading materials `sha256:fe68e56946f2eeab35c4c335f317ef2a17fb27da4af54024b3d837f2548788a4`、公开 prompt/brief、baseline 与实际评分预算均相同。actual actor 的 `container_image_id` 与 grader diagnostics `local_build` 身份同为 `sha256:f3b8d6671607e167fa549c05faa860345e5256c8f834a6a711447df9dce6839f`；资源切片分别实际看见 actor 9 次、grader 6 次，镜像身份也相同，超过 purecheck 的配置声明。

Coder 使用 code7、Qwen executor 使用 code8。比对 source manifests 和本地冻结源码：code7 的 985 项、code8 的 1,045 项各自全部 size/SHA 匹配；**5 个修改、60 个新增、0 个删除**。5 个修改是 `entry.py`、`prepared_task_face.py`、`bundles_v2.py`、`swe_material_revisions.py`、`material_revision.py`。快照中的 entry/dispatcher 与 code8 manifest 一致。三项关键运输源码声明及本地字节 SHA 未变：`solve_attempt.py`、`grading/manager.py`、`grading/trusted_projection.py`。entry 新增的 preparation policy 在本题实际 `null`，准备仍为 300 秒；这不构成 code8 所有分支的实现审查，也不意味着全代码相同或远端整个源码树重新散列过。

profile digest 不同：仅 `model_proxy_upstream` 从 Coder 的 `172.17.0.1:18081` 改为 Qwen 的 `172.17.0.1:18082`。所以可以确认本题固定材料复用，不能宣称两个模型的整个 runtime/profile 相同。

旧 Coder 执行结论仅复用[已完成非作者执行审查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan11594_coder_a1_execution_review_v1.json)，本次校验其 SHA 为 `4be7e58d6ace46c3969cb3b001792592b232669985044c672e8324b578ad7275`。配对回执中“一模型一次已覆盖”的执行层判断因此有旧 Coder 及本次 Qwen 两臂支撑；本报告不重跑 Coder，也不替题主做整项 ACK。

## 原 issue 和 brief v2 的首 API 交付

从 rollout public view 重算完整 issue SHA `27b3892e1c2dc35a694def6074c82739d312f7a87436a9e31cbe9e0944dd5246`，正文 1,239 个字符，包含复现、完整原日志及末段。base prompt SHA `53659643a6a2c7be7baefbe1675a437a0262670b54a8722af06520b773cb1357`，brief v2 原文件 SHA `c0ab743d03d433b9fd9f23b5d152430592f3ccb38cf703acec45a45dcddaa5f7`。

[solver prompt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/solver_prompt.txt)、attempt prompt 和[首 API request 原件](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan11594-qwen36-a1/requests.jsonl)的实际任务 text **按原字节一致**，SHA `5de84366859c5a995d424db0543d2fcde183d102d52f13197f9d98cae2c3e699`；包含完整 issue、base prompt 与完整 brief 正文，附有 brief 替代旧开发提示的交付标记。核对保留 issue 内 CRLF，brief 仅剥去首尾空白，避免文本读取自动换行造成假差异。此处只证明交付，未做新公开读者语义审查。

## 原始评分日志与参考 ALL binding

[原 eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan11594-qwen36-a1/grading/eval_logs/evallog_gpu1003-conan11594-qwen3_a990b54f.eval.log)为 29,991 字节，SHA `d11b0cfe43b7d5fd9e1cb31f24e31e5cdb25712cba750f86ffa4c56b8c0363ae`。安装、测试的实际 `RH2_*_START/END` 时间标记完整且顺序正确；独立匹配裸标记得 `RH2_INSTALL_RC=0`、`RH2_TEST_RC=0` 各一次。diagnostics 外层 candidate exec RC=0、install 非 skipped、log 非 partial，与原日志相符。

测试真实命令为 `pytest -n0 -rA conans/test/unittests/tools/cmake/test_cmake_test.py`。日志有 7 条完整 `PASSED` 节点及 `7 passed, 3 warnings in 0.62s`，无缺失、skip、fail；新增候选测试文件不是这次正式测试命令的计分文件。按[固定 reference bindings](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/prepared_conan11594_dask7656_code7_v1/conan11594/private/assets/reference_bindings.json)，逻辑 `test_run_tests[Ninja` 必须以下两项 **ALL 通过**，原日志两项均为 PASSED：

- `test_run_tests[Ninja Makefiles-test]`
- `test_run_tests[Ninja Multi-Config-test]`

另外新增真实执行节点 `test_ninja_multiconfig_executes_requested_release` 和 NMake、Unix、Visual、Xcode 四项均通过。合计 **6 个逻辑参考／7 个完整 raw 节点**，F2P 2/2、P2P 4/4；parser `num_parsed_tests=6` 是逻辑参考口径，不能误写成只执行 6 项。diagnostics 无 missing/skipped/unaccounted 或段外解析；trusted setup apply RC=0、1 个受保护测试文件存在、runner digest 前后相同。UID54322 的 Ninja prerequisite 为 verified/RC0，有实际版本与成功标记。原评分运输与参考覆盖可核销，独立的功能语义结论不在此范围。

## 实际模型调用、预算与终止

HTTP requests、responses、SSE 文件、adapter turns 各 **60**。request/response 的 seq 各恰为 1–60；每响应 HTTP200、attempt1、stream error 为 null。逐 SSE 核字节数、完整 message_start/message_delta/message_stop、model、stop reason 和 usage：59 次 tool_use、最后 1 次 end_turn，均与 response 相符。adapter 的每次 prompt/output tokens 与响应一致；累计输入 1,493,206、输出 11,831，也与 CC result/usage 相同。两个 trajectory 文件字节一致，892 行、591,025 字节，harness stderr 空；CC2.1.205 成功终止，实际 solve 110.811 秒。**CC 自报 `num_turns=61` 不是 60 次 HTTP 计数。**

统一实际口径为 context 196,608、输出请求 65,536、CC turns 240、solver 10,800 秒、gateway 1,024 requests、首字节 timeout 1,800 秒、adapter idle 14,400 秒；grading whole/setup/apply/test 为 3,600/300/120/1,800 秒。全部请求 `max_tokens=65536`，actual adapter sampling 为 temperature1.0/top_p0.95/top_k20/max_new_tokens65536。SGLang readback context=196608、max_req_input_len=196602、max_running_requests=1、tp=1、bf16、版本0.5.20，与服务 inspect 相接。CC modelUsage 的 `maxOutputTokens=32000` 是其自报字段，不能替换实际 HTTP/adapter 的 65536；本次最大观测 output 1,371 tokens，没有实际验证 65,536 输出边界。

运行前/后 engine 与 adapter inspect 的 container ID、PID、StartedAt、RestartCount、镜像及只读 model/code mount 完全一致；download manifest 绑定 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`。37 个 runtime 文件的大小与下载清单逐项一致，总 71,926,788,362 字节；chat template 实际 SHA 也匹配。**没有重复所有权重文件散列，更没有 GPU 内存权重散列证明**，保留 capture/gateway 原字段的限制，不以模型显示名独自证明权重身份。

[当前 terminal snapshot](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan11594-qwen36-a1/terminal_snapshot.json)记录 entry RC0。[原 PID1 journal](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-conan11594-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl)的 exact UNIT 在起止窗口内有 `_PID=1 / SYSLOG_IDENTIFIER=systemd` 的 Started 及 `Deactivated successfully`，成功时刻 `2026-10-03T13:37:14.860325Z`，与 registered ended `13:37:14.831267Z` 相接；journal query RC0、原 journal SHA 已重算。`LoadState=not-found / ExecMainStatus=0` 是退役 unit 的默认 show，**未当成退出证明**。

## 两层清理与资源缺口

actor 记录 `container_rm=0`、container_left 空、network/relay failures 空、labeled containers/networks 空、cleanup_ok=true；pre-drain stop 和 quiescence residual0、未超时。独立 `session_close.jsonl` 与 attempt gateway drain 相同：本 session revoked=true、active_requests=0、drained=true。grader manager close 为 created1/removed1、containers_open/supply_open/cleanup_failures 空、regrade0；最后资源切片本 job 容器为空。可确认本作业与 session 闭合；共享模型服务保持运行不等于作业遗留。

[19 个资源切片](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan11594-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan11594-qwen36-a1/resources.jsonl)覆盖 `13:32:49.259819Z`–`13:37:20.548034Z`，最大间隔 15.084519 秒。actor/relay/grader 分别被采到 9/10/6 次；采到的 memory.peak 最大分别为 986,894,336／30,724,096／310,333,440 字节，pids.peak 为 26/7/8；采到的 OOM、OOM kill、pids.max event 均为0。diagnostics 的 grader peak 365.996 MiB 来自另一个采样口径，不与切片最大值合并成新全程峰值。

**资源限制直接保留：切片不是连续观察，未给引擎/adapter 服务 cgroup 和容器终点完整计数；GPU 字段只有采样读数。不能由此推出整作业真实资源峰值、完整 CPU 吞吐、总体 GPU 利用率或跨模型效率比较。** 此缺口约束效率分析，不否定上述已闭合执行与评分运输证据。

## 审查适用性与停止条件

A/D/E/F/G/H/L/M/N 在本次运行证据上适用：分别核终止/清理、配置与身份、原评分参考有效消费、冻结版本一致、实际入口、原件事实链、有限资源/预算、原日志完整性、CC/SGLang/adapter版本。B/C 的训练分布/闸门及 J/K 的全面源码质量/演进审查不在本次只读执行对象内；I 以显式资源/权重限制和复用旧 Coder scope 管分期，不新设准入闸门。没有新实现、T0 决策、挡板变动或训练消费验证。

本轮修正的是“中断 reviewer 初步消息可当完成审查”的潜在引用方式：只以本次落盘完成报告作为 Qwen 执行独审依据。保存报告及 JSON、给出 SHA 后停止；不改冻结原件、共享账、题主文件，不启动重复采样、不发其他 Codex 线程。结构化核对结果 SHA：`446a58caa11851ce31abe8472b22bd874cd7e49498779dd8bbc05e75304e7e6f`。
