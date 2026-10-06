# 1c1 取消清理 P2P：发布后五行实际执行窄核

2026-10-03。非作者 Production Tracer，按 [review-standards §10.4/10.5](../../../../../../review-standards.md) 在同一批内完成静态反馈及实际结果复核。本轮已知原候选、私有材料与题主结果，不是 fresh 读者或盲审；没有重跑测试、矩阵、模型或远端实验。

**本批新 P2P 已被实际完整消费，并检出完整原 Coder 候选的取消清理回归。** 五行均实际收集且解析精确 59 键：baseline 57/59、gold/C1/Qwen 59/59、Coder 58/59。Coder 唯一不匹配的是新增取消清理键；它的旧 58 键仍全部 PASSED。正常库行为与两种合理修法未被新项误拒。材料与候选运输、评分结束及本批清理原件没有出现阻断这项判别的执行缺口。

建议接受这一次新材料的 CPU 判别证据；它不授予整条 harness、模型或训练资格，不解除或改写旧 binding。旧 raw1/58、原尝试与原 Frozen 保留；新材料重评分单列为诊断。

## 固定输入、入口与静态 finding 的处置

独立重算 [input_manifest.json](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/inputs_v1/input_manifest.json) SHA `e6ab6daa53dd0a56cf82be4e79984bfccb37b5965f5d65be89b3613ba14c33a5`；所列 12 文件 SHA/bytes 均相符。实际 driver SHA `5b47a7081e52b4a5037d11ef048da181cfa8298c1748acd03ae57b27ff01cee4`，controller SHA `8182d9208e0664abdee04b52d4e13a1a42e434ae0fc2ed9ef038788e89991670`。

固定发布为 R22 `cat2-cpu-r2e094095-swe40-aio1c1-cancelled-20261003-v1`；[release manifest](../../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_094095_swe40_aio1c1_cancelled_v1/manifest.json) 实际 SHA `aaa957435ca509a7733a1965a74915b26d86a3c7d09624786755ed50c9aea6c9`，与输入、publication receipt、prepare/matrix 的 verifier 调用一致。此处不扩为复核其余题材料或全 release manifest 成员。

[最终 driver](../run_p2p_cpu_validation.py) 把 baseline/gold/C1/完整 Coder/完整 Qwen 的精确顺序、对应 patch/Frozen 文件名、清单成员、输出五行数都绑定；controller 自身路径与 SHA 也绑定。它不因 `anticipated_reward` 不符修改分数，该字段只用于诊断对照。矩阵 summary/overlay 的 SHA 必须与实际参数相等。静态反馈中“五行标志固定为 true、文件清单成员未强制”的问题已按 [execution_static_response_v1.json](../execution_static_response_v1.json) 处置，并由这次实际固定输入落实。

外层 controller 仍只对进程组 TERM、120 秒宽限后 KILL；不保证 Docker daemon 清理。最终 receipt 明确 `docker_cleanup_confirmed_by_this_controller=false`，超时须停止并另核残留。本次 prepare/matrix 都未触发 timeout，因此这项限制没有被虚记成实测通过，也没有导致本次原件中断。

实际 `prepare_process.json`、五份 `*_process.json` 均调用 R22 的 `rh2/scripts/replay_grade.py`，候选分别为 `noop` 或四份固定 `patch:`；没有替代评分入口。路径为 `ReplayGrader` 以 agent/54321 应用候选、重新导出完整 Frozen，随后向 `SWEGradingManager.grade` 交 `FrozenDeltaSource`。manager 在重建 baseline 与保护控制面后应用 Frozen 内容，执行固定 R2E runner；不是把文本 patch 直接交给一个临时测试脚本。

共用来源边界也保留：entry、sandbox profile、trusted projection、Frozen 契约与 R6 同 SHA；parser 也同 SHA。R22 replay 模块 SHA 为 `ef8c54e1336c9446cdf65692666aeadfc50485ad62e86db044d649075f753690`，不能冒称已完整复用 R6 审查。独立窄读 R6→R22 增量，新增 SWE 固定环境/镜像及任务预算分支未在本批 R2E 数据与实际账本中启用；本次沿原 overlay/default 分支。manager SHA `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e` 可复用 [R15 有限身份核查](../../../swe_dask/reviews/non_author_source_image_matrix_adapter_r15_review_20261003.md) 的适用部分；相对 R6 新增的可选 `candidate_prerequisite` 本批五份 diagnostics 都是 null。以上均不是新的全 grader 安全审计。

## Prepare/build、材料与新镜像

[prepare 原件](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/prepare_artifacts_v1/outputs) 中 summary、prepared manifest、public views/private grading view 的 SHA 链独立重核相符。矩阵实际参数硬绑定 summary SHA `4644daf00582dfb597fd0f5f66d9566f61bad3f3f1c79021265a44f6fc50b68e`、overlay SHA `038ba72e0f0c017c0d58739138dadda9adea2e0a72cf8ad1332621081ef3da75`；没有消费旧 prepared 或旧 hidden overlay。

材料修订为 hidden094/expected095。expected 正文 SHA `4872a730f3a8ffce94869108668c0a7dd20a68c368ee2141bb5ae47981060adf`，实际 test_1.py SHA `3f57f362fd8d43cfd384386c1ecdc2f8c85b04aec88364a0859bbc2e2e6d3f52`；context 字节与固定输入相同。hidden tree 为 `e62303235b768326fa4d659007778f82f5b5a2699e89ea21131491cb5916496c`，runner 正文 SHA `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`。独立核 expected/runner 正文摘要；五份原日志都记录相应 `RH2_SETUP_HIDDEN_TESTS_TREE`、`RH2_SETUP_ENTRY_SHA256`、setup apply RC 0、expected/test files 4/4、absent 0、irregular 空、setup OK 1，证明新材料实际安装和消费。

build 的正式产物是新评分镜像 `sha256:ea62d2733e1dded64b4e11c174f02de8bb7c1a7f69c19ae7c9d2bb7d8f3e01a8`，recipe `r2e_derive_v1+material_v2+sysconfig_v1`、SHA `929f305e1011cadee6dffcbae812f0f0a05240c0386f596c0d9047347c8f2e0b`。build facts、overlay、五行 actual image ID 与结束后的原 Docker image inspect 相符，平台 Linux/amd64；不能将旧 00ad actor 镜像称为含新 hidden 的评分镜像。build facts 的 agent/grader UID 解释器可执行、private hidden 不可读、git 可读及 rollout preflight 均有对应读回；它们属于 build 阶段证据，不替代五行各自新增 prelaunch/cgroup 证明。

## 完整原候选与身份变化

本批静态阶段已独立从原 307 文件 tar 解析统一 diff、解码 Git binary literal，Coder7/Qwen2 每项原始 bytes 与原 Frozen 精确一致，Git mode 也一致；Coder `.coverage` 为 278528 bytes、Qwen 为 401408 bytes，helpers 未裁。四份 patch SHA 与原来源、当前固定输入和实际保存的 candidate.patch 一致；没有改 gold/C1 或编辑候选来配新测试。见 [完整候选运输原件](../complete_candidate_transport_readback_v1.json)。

这次五份实际 baseline 的 307 个完整 entries 都等于原 baseline。整体 canonical 对象与旧 baseline **不相等**：独立逐字段比较，唯一变化为 `runtime_image_digest` 从原 00ad 改为本次 ea62 新评分镜像。本次 baseline canonical digest 为 `c40290096b9ba3ccaf0bd0357e455ed1fc6294aefafa8079e24069125651ab12`；各实际 Frozen 的 baseline anchor 都与它相符。不能用“307 项相同”偷换整体 baseline 身份。

实际 Coder7/Qwen2 `entries` 与原完整 Frozen 逐字段相等，包括 operation、object type、mode、base64 原内容及 content digest；独立解码并重算每条内容 SHA 全部相符。新的 rollout/physical attempt 与 baseline image 使完整 Frozen canonical 身份自然变化，不把新 replay 文件的整体 digest冒称为原采样 digest。五行实际 Frozen canonical digest 均独立重算并等于 projection/ledger anchor；projection 精确包含全部 Frozen entries，ignored/unsupported 均空。

| 行 | 实际 Frozen 项数 | 实际 projection |
| --- | ---: | --- |
| baseline | 0 | 空 |
| gold / C1 | 各 1 | `aiohttp/web.py` |
| Coder | 7 | `.coverage`、`FIX_SUMMARY.md`、`aiohttp/web.py`、`comprehensive_test.py`、`reproduce_issue.py`、`test_exception_handling.py`、`verify_fix.py` |
| Qwen | 2 | `.coverage`、`aiohttp/web.py` |

完整原件在各行目录的 `artifacts/`、ledger projection 和 eval diagnostics；不是仅回放一个 web.py。

## 固定 parser、59 精确键与补清理前语义

独立使用 R22 固定 parser 的纯解析函数读取全部五份完整原日志。parser SHA `339b7c80cca516dc7d1bcf9c11e3ff9a42f1bc993b5027a0d06c41c85d024b58` 与 R6 精确相同；每份有且仅有一个 Start/End 测试段和一个 short summary，段外没有 summary，整日志/段内解析结果相等。五行都是精确 59 键，无缺键、额外键、零解析或收集异常；独立状态比较与账本 match/total 相符。

与已审 R6 原 expected081 逐键对照，旧 58 键及状态全部相同，只新增 `test_run_app_cancelled_coroutine_cleans_resources[pyloop]=PASSED`。baseline/gold/C1 的旧 58 个实际状态也与 R6 原日志逐键相等；原完整 Coder/Qwen 首轮已审精确 58/58 与同一原 Frozen 的结论按 [前次 GPU 执行复核](../../reviews/non_author_1c1_240d_gpu_first_round_execution_20261003.md) 的范围复用，本次两行旧 58 键仍全 PASSED。

| 实际行与原件 | 旧 58 键符合期望 | 新取消清理键 | 全部 match/total | 原 reward / outcome | 实际 test RC |
| --- | ---: | --- | ---: | --- | ---: |
| [baseline](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/matrix_artifacts_v1/outputs/matrices/baseline) | 56/58 | PASSED | 57/59 | 0 / unresolved | 1 |
| [gold](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/matrix_artifacts_v1/outputs/matrices/gold) | 58/58 | PASSED | 59/59 | 1 / resolved | 0 |
| [C1](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/matrix_artifacts_v1/outputs/matrices/C1) | 58/58 | PASSED | 59/59 | 1 / resolved | 0 |
| [完整原 Coder](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/matrix_artifacts_v1/outputs/matrices/coder_full_frozen) | 58/58 | **FAILED** | 58/59 | 0 / unresolved | 1 |
| [完整原 Qwen](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/matrix_artifacts_v1/outputs/matrices/qwen_full_frozen) | 58/58 | PASSED | 59/59 | 1 / resolved | 0 |

baseline 仍只在 `test_run_app_raises_exception[pyloop]` 与 `test_run_app_raises_exception_on_server_start_failure[pyloop]` 两个旧键失败；新增 P2P 保留正常基线行为，并不要求原基线修好旧 F2P。

实际固定 test_1.py 第 977–1046 行中，取消传播的 `pytest.raises`、快照、worker/generator 清理事件、closed/pending 等所有语义断言都在观察者 `finally` 补清理之前。实际日志中 baseline/gold/C1/Qwen 快照为 worker done/cancelled、generator closed、loop closed、pending 0，两项 cleanup event 都有；Coder 快照为 worker done/cancelled false、generator/loop closed false、pending 1，两项 cleanup event 都无，首个 `assert worker.done()` 真实失败。

Coder traceback 的后续 locals 显示 loop 已 closed、worker 已取消、cleanup events 已追加，是测试失败后 `finally` 的补清理结果，不能反向覆盖此前打印的原始快照。新增测试捕获的是候选回归，不是缺库、语法/收集失败或 observer 未回收资源制造的分数。旧 [实际公开输入归因](../../reviews/non_author_1c1_cancelled_main_execution_20261003.md) 的边界继续成立，本次不重开其审查。

题主的 [results_five_rows_20261003_v2.json](../results_five_rows_20261003_v2.json) SHA `71c67c24bc812a777b413ddac3016395f5ffde775ed2456e4d5b9c8a88790fb7` 已核；采用其仓库相对证据索引。上述结论先由原日志、固定 parser 与实际 artifact 独立恢复，不以题主预期或总表代替。

## 身份、资源与生命周期的实际边界

五行原日志都记录 Linux、Python **3.9.21**、`/testbed/.venv/bin/python`；导入观察为 `/testbed/aiohttp/__init__.py`。runner 观察摘要前后均为 `8425ef891c5c94503df28bec8b916b5fe3cba7a6b46266e10903742dd43baa9a`，`runner_integrity_changed=false`。该观察摘要与上文材料 runner 正文 SHA 是不同摘要域，二者不混称。prefix owner 观察均为 54322。

身份与资源证据分层：ledger 的候选应用身份是 agent/54321；grader policy 配置为 rh2grader/54322、2 CPU、4 GiB、512 PIDs、deny_all、1 GiB tmpfs、64 MiB shm，profile digest `3ec1bfa87ff800d5d2c5e53e874603f6850b64e1392baa167968b9ec31a50a94`。固定 manager 使用 profile 候选 user 执行测试；build UID 可执行/不可读证据和 prefix owner 观察支持这条接线。但本包**没有五行独立 grader_prelaunch/cgroup 原件或逐行 getuid 读回**，因此不把 policy 当新实测 cgroup 资格，不声称五行逐容器全部资源隔离条件已独立证明。`resource_facts`、`grading_materials_identity`、`grading_revision`、`derived_image_recipe` 等仍为原 null；`env_qualification=absent` 保持。

prepare/build 通过独立 prepare job 占槽，06:58:17–07:00:01 UTC，finished/0；matrix 通过独立 run job 占槽，07:01:24–07:15:04 UTC，finished/0，二者无重叠。五行 process 时间顺序无重叠；不据此断言宿主其它批次全局无并发。总预算 prepare 10800 秒、matrix 24000 秒，宽限各 120 秒；每行 candidate 900、grade 3600、cleanup 120、pull 1800 秒。实际均未 timeout。

五行原测试段都正常结束、无 partial；process/exec RC 0 只说明评分流程交付，baseline/Coder 的真实 test RC 1、tests_failed/reward 0 原样保留。每行候选 cleanup `removed=true/rm:ok`；manager 最终 created1/removed1、open/supply/cleanup_failures 空、final exit0。结束后的 [本批 residue 原读回](../../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/own_five_row_residue_readback_v1.json) 中 builder 及五行标签共 12 次 container/network 查询均 RC 0、stdout/stderr 空，本批残留为空；不是宿主全局清理声明。

两包原件独立核 SHA：prepare `882da996b5fb8c48251cde2823ed014156aac9457244713929c0ca4c7ce7fe07`、matrix `6ee63d8d35dd94998d42825d33e6eef188e9528186ebd0ae83c3dbb2dbde2604`；各自 archive manifest 所列 **38/75 文件 SHA 与 bytes 全部相符**。完整 launch、slot、bounded、process、stdout/stderr、Frozen/projection、ledger、原 eval logs 均保留。

## 结论、未知与停止条件

本次五行实际证据满足批准的单 P2P 材料诊断范围：新项检出 Coder 的原回归，保留正常基线行为，gold/C1 与 Qwen 在该项和原键上通过；没有新执行回归需要继续穷举。静态绑定 finding 已处置；timeout 清理限制仍明确保留，未在本次触发。原 actor 的两个 false 通用 DevRunner marker 不因新 grader 验收改成 true。

未覆盖 timeout/信号中断下的 daemon 清理、其它取消时序/长期服务、整条 grader 安全资格、完整 R22 replay 通用审计、typed 新训练 binding、模型重采样及训练。null 材料/资源字段与缺少独立 cgroup 原件不自动触发本批之外的新实验，也不能被本报告补成资格。旧 raw 与 binding 保持原状态。实际五行的完整候选、精确键、观测前后与清理链足以完成本次判断，停止本轮。
