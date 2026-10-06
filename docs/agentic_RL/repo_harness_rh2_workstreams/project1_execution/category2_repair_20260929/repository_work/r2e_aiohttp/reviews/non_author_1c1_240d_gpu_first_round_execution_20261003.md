# 1c1 / 240d 首轮 GPU：非作者执行链复核

日期：2026-10-03。角色为 Production Tracer，依据 [review-standards §10.4 / §10.5](../../../../../review-standards.md)。这是一次已见私有材料、候选和作者结果后的有界离线复核，不是 fresh 公开盲审。范围只含 queue_v11 的 `gpu1003-aio1c1-qwen36-a1`、`gpu1003-aio240d-qwen36-a1` 与 queue_v16r1 的 `gpu1003-aio1c1-coder-a1`、`gpu1003-aio240d-coder-a1`。只读已有本地原件、用 `PYTHONDONTWRITEBYTECODE=1 python -B` 标准库解析；没有 SSH、Docker、pytest、模型、CPU 矩阵、安装或共享编辑。

## 本轮结论

四个 job 的关键实际工具、原 baseline / Frozen / projection、完整评分与清理链可对应。**1c1 两模型的原 58/58、240d Qwen 的原 33/33 与独立重解析一致；240d Coder 保留原 null / failed_to_grade。** 未发现关键候选字节的捕获或运输失真，也未发现这四份结果因截断日志、替代 baseline 或未清理而不能核收的实质阻断。这里只核收执行证据，不宣布题级语义接受或训练资格。

| job / 原 result | 实际终止 | Frozen 条目 | 正式 test RC / 独立解析 | 原 reward / outcome |
| --- | --- | --- | --- | --- |
| [1c1 Qwen](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/result.json) | completed，harness RC 0 | 2 | 0；58 个 expected 与 observed 精确相等 | 1.0 / resolved，58/58 |
| [1c1 Coder](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/result.json) | completed，harness RC 0 | 7 | 0；58 个 expected 与 observed 精确相等 | 1.0 / resolved，58/58 |
| [240d Qwen](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/result.json) | completed，harness RC 0 | 1 | 0；33 个 expected 与 observed 精确相等 | 1.0 / resolved，33/33 |
| [240d Coder](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/result.json) | completed，harness RC 0 | 6 | 2；仅 `ERROR r2e_tests/test_1.py`，33 expected 全部未收集 | null / failed_to_grade，原 expected 计数均 null |

## 实际工具与异常传播

**1c1 Qwen。** [完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/attempt/harness/trajectory.jsonl) 268 行，SHA256 `ffc283408a425dd2c12998baba5f8d10ed457431ff365937e77ac440527976fa`。158 行 `toolu_6a669b0667b2a087` Edit、162 行成功结果修改 `aiohttp/web.py::_cancel_tasks`：取消前记录已 done 的任务；取消、gather 后跳过这些任务的 `call_exception_handler`。gateway [resp_10.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v9/qwen36/gateway/gpu1003-aio1c1-qwen36-a1/resp_10.sse) 的相同 tool ID、路径、old/new string 均与实际记录相等，记录另填默认 `replace_all=false`。在原 baseline 内存执行这次替换，字节精确等于 Frozen `web.py`，内容 SHA256 `f7c5c1d1b2fd638d4527ca8e2c17a105512848d6da24d2b6220f5124dfd92933`。另一条 Frozen 是公开自测产生的 `.coverage`；projection 两条全保留。

**1c1 Coder。** [完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/attempt/harness/trajectory.jsonl) 253 行，SHA256 `86d46c9562c2ac52224586ce836e304a3e52221e06c8c5880145cb60e69dccbd`。88 行 `toolu_da9e72cf505ed641` Edit、92 行成功结果修改 `run_app` 的 finally：`main_task.done()` 且 `main_task.exception() is not None` 时跳过仅针对 main task 的 `_cancel_tasks`；其它任务取消仍随后执行。gateway [resp_7.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v14/coder/gateway/gpu1003-aio1c1-coder-a1/resp_7.sse) 对应同一 tool ID；可见差异仅是记录填默认 `replace_all=false`、new string 一行注释尾空格被去除。原 baseline 按实际记录 Edit 重放后等于 Frozen `web.py`，SHA256 `279d0a2d2b733dcb0bce0530043de938ec3fc8148f98bcc2e9a1f76ce6ae8887`。7 条 projection 包含该文件、`.coverage` 和 5 个公开 helper / 说明文件。实际公开工具记录 `test_run_app.py` 55 passed，三个后续单测各 1 passed；正式 hidden 的完整 58 键另核，不用模型最终正文代替它。

两种 1c1 候选修改的位置与异常传播策略不同。正式 58 键通过可证明本材料下的执行结果，不能由此推出所有 done / cancelled task 状态、全部调用者异常或日志行为均正确；特别是 Coder 新分支中的 `main_task.exception()` 对 cancelled task 的行为，本轮未新增构造或实验，覆盖保持 unknown，交题级语义审查处理。

**240d Qwen。** [完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/attempt/harness/trajectory.jsonl) 328 行，SHA256 `902b12f367724212322044f0ea79c41ea4189c052dd6af29064406161b159aa8`。120 / 124 与 152 / 156 行两次成功 Edit 改 `connector.py`：引入 `HTTP_PORT`，默认端口省略、其它端口进入代理请求路径。对应 gateway [resp_7.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v9/qwen36/gateway/gpu1003-aio240d-qwen36-a1/resp_7.sse) 与 [resp_9.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v9/qwen36/gateway/gpu1003-aio240d-qwen36-a1/resp_9.sse)，有效 old/new 字节一致。两次 Edit 在 baseline 重放精确等于唯一 Frozen 条目，内容 SHA256 `107d0e3cc7be6348f86bd8dd5959a3ff7af60c0fb974c9f438e0b28f7687939c`。

该轨迹的公开完整 connector 自测曾显示 2 failed / 30 passed。260 / 264 行 `git stash && ... | tail -20` 暂时还原兼容修改后报 `client.py:140` 的 `asyncio.async` SyntaxError；管道工具 `is_error=false` 不代表 pytest 成功，也没有证明前述两项失败是 baseline 原有。274 / 278 行 `git stash pop` 成功恢复包括 client / server / worker 的工作树修改，最终 Frozen 只含 connector，正式评分 33/33。临时 stash 的收集错误未被误写成最终候选的评分失败；公开两个失败的题级关系仍不在本次执行复核内。

**240d Coder。** [完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/attempt/harness/trajectory.jsonl) 315 行，SHA256 `9e8eb33b61c306a745ae15a95f240be5234d41fd5517aa6d10317940b284a675`。145 / 149 行成功 Edit 修改 connector 的 scheme / port 拼接，按实际记录重放精确等于 Frozen connector；gateway [resp_12.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v14/coder/gateway/gpu1003-aio240d-coder-a1/resp_12.sse) 的有效 old/new 字节相等，另填默认 `replace_all=false`。267 / 271 行 `toolu_347c493613b97553` 成功执行 `git checkout -- aiohttp/client.py aiohttp/server.py aiohttp/worker.py`；gateway [resp_22.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v14/coder/gateway/gpu1003-aio240d-coder-a1/resp_22.sse) 的 tool ID、命令精确相同。

实际 baseline 中三文件已使用 `asyncio.create_task`；Frozen 相对 baseline 精确回退为 `asyncio.async`，client 两处、server / worker 各一处。三个文件除此字符串回退之外原字节一致。293 行 reproduction 工具报 exit 1，306 行公开 pytest 工具报 exit 4，均在 `client.py:140` 报同一 SyntaxError；正式 grade 同位置收集失败。6 条 projection 保留三兼容文件、connector 与两个公开脚本。**本单 job 的关键故障字节来自实际 checkout，证据不支持将它归因于 Frozen 捕获或评分运输失真。** 自动 report 的 `execution_failure_stage=null`、`infra_failure_detail=reference_all_missing:unattributed:qualification:absent` 与 reward null 仍原样保留；离线归因不补自动分类或 reward。

## baseline、正式评分与清理

四份 baseline 与 Frozen canonical digest 独立重算均匹配 actor 和 result 绑定；全部 Frozen payload 的内容 SHA、projection 精确路径集、三份 report 内容也一致。关键生产文件的 baseline tar 内容 SHA 匹配 manifest，关键 Edit 的内存重放结果匹配 Frozen。每 job 的 actor baseline census 与 grader rebuild census **完整字节相等**；不是仅比较 HEAD。两模型同题 baseline digest 相同：1c1 为 `40b0956474180605d1f46cc2b59f3e4ae3dcef0fffd18f9f2ff24b539d007608`，240d 为 `15b10740995047ebfb9d564cedb427883b065f456dfae1acfbe3f2ce05ab388f`。

| job | 原 Frozen canonical digest | 完整正式 eval.log SHA256 / 字节 |
| --- | --- | --- |
| 1c1 Qwen | `77d02d948b6a6e003aba9a497d905189c15b174ddb02f5f10b3fa62362b036be` | [日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/grading/eval_logs/evallog_gpu1003-aio1c1-qwen36-a1_7b2bcbaa.eval.log)：`a1879ddddaec28f7b829a07b3db938b9decacbcb4cbfab691451efd1adcbcefe` / 24771 |
| 1c1 Coder | `dc7a8f17e1b22988f2091bc882fb75fb28227a61bb97b26d713b03d69e70798d` | [日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/grading/eval_logs/evallog_gpu1003-aio1c1-coder-a1_47a61611.eval.log)：`6c9f79400606d2f66e5c09815768aad8b46ca9adc74ecb6fd89ce292cb874983` / 24883 |
| 240d Qwen | `053b27f93dff8dce15f8450d3b77d1c6717dbbdf359a22b03e4d95b8bc995602` | [日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/grading/eval_logs/evallog_gpu1003-aio240d-qwen36-a_d32e3fac.eval.log)：`5da3e68092448563b34060b9077b026d291110c266e6ce7cc1cf4e4c1a8d1df2` / 4125 |
| 240d Coder | `23b2a9f3be2c0b7491af5b27c78e8112a0bffab3e89d2d9c4783be86a3780223` | [日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/grading/eval_logs/evallog_gpu1003-aio240d-coder-a1_be7dbfdf.eval.log)：`555e8e0db04ee2a6cae24d798bd6947a1bae8b4d7e31a60dad1571a4dceeb2cf` / 3113 |

独立核上述日志与 report SHA / 字节锚。每份正式 test 段有开始、结束和实际 RC，diagnostics 均记 completed / log_partial=false；setup apply RC 0，expected / actual protected test files 对 1c1 均为 4、对 240d 均为 3，absent 0、irregular 空。hidden tree 对 1c1 为 `bf037fbf…`、240d 为 `e66b0f13…`，实际 entry SHA 均为 `8285765f…`。安装原段全部 `RH2_INSTALL_SKIPPED=1` / install RC null，不能写成重新安装通过。

每题私有 host grading 原件的实际 SHA 与 input / attempt 一致，expected 原始 JSON SHA 独立重算匹配。只抽取固定 parser 纯函数 AST 解析完整正式日志：1c1 两份 58 键、240d Qwen 33 键均无 missing、unexpected 或状态差异；Coder 240d 唯一错误键与 diagnostics 相等，33 键未执行，不能描述成 33 个测试执行失败。未导入项目运行环境。

共同机制按与 [前次执行链复核](non_author_6183_coder_a1_execution_attribution_20261003.md) 相同 SHA 复用：当前 fixed entry `a1efff44…`、shared solve `10a71cca…`、base solve `00ca8499…`、manager `b6b10f98…`、parser `339b7c80…` 均独立重哈相同；不重核 529 文件或新审共同设计。固定 entry 直接消费原 baseline / Frozen，result 均记 `source=original_frozen_patch`、baseline_rebuild_passed=true。该 entry 对 null reward 返回 3，是其结果传播约定；本轮未独立覆盖 queue_v16r1 宿主 unit / 退出状态原件，不将其包装为新实测。

四份 actor prelaunch 实际检查均通过，UID 54321、CPU `200000 100000`、memory 4 GiB、swap 0、PIDs 512 与 profile 一致；profile canonical digest 匹配。1c1 actor / grader image 为 `00ad3e96…`，240d 为 `f74ceef7…`，两模型同题一致；grader diagnostics 记录同 image identity，runner 前后 digest 相同、runner_integrity_changed=false。四份求解均完整终止，quiescence residual 0、稳定双读，无 timeout；actor 清理成功，无 labeled 容器 / 网络残留，gateway revoked / active 0 / drained；每份 grader manager created / removed 各 1，open / supply / cleanup_failures 空，regrade 0。

## 正式回执与边界

独立核 [1c1 aggregate](../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/aiohttp1c1-r080081-probe-wide-v1-20261003_two_model_v1.json) SHA256 `1880bfef27f43e39cc2f0aae2199fecf6daae9001d297af88d83bc32a6ef8618`、[240d aggregate](../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/aiohttp240d-r082084-probe-wide-v1-20261003_two_model_v1.json) SHA256 `8e5a68fcbb3f5c2fa7152ff0dd1b2e33f8c0e76048078a6eb663109963020ee5`。其中四 job 的 result / attempt / baseline / Frozen 文件 SHA 与本地原件均匹配，四份既有 GPU 独立执行审查的引用 SHA 也匹配；没有继承其候选故障裁决代替上述原件追踪。1c1 的回执状态为执行已核、题主语义分析待收口；240d 为 safe partial / one invalid grade。两份均 safe_closed=true、remaining_unexecuted 空，原 null job 明列为 invalid grading，而非漏跑。

四份实际 gateway 首请求均包含完整 delivered prompt，1c1 SHA `15af1be5…`、240d SHA `db3284a4…`，两模型同题相同，首请求 max_tokens 65536。有效关键 Edit / git 操作已对应原 SSE；未逐条核全部非关键参数或采样。公开自测的 head / tail 管道与模型最终自述不代替正式 RC。

`grading_materials_identity`、`grading_revision`、baseline 的 `environment_package_digest`、`code_snapshot_id` 保持 null；`env_qualification=absent`。gateway checkpoint_identity_verified=false，不用 routing alias 声称 loaded weights 身份。本轮没有独立重核权重、SGLang runtime 全窗口、TTL 生存实验、完整 grader inspect、资源采样间隙或每次 backend sampling params；这些保持既有执行审查的有限边界或 unknown。`.coverage` / helper 入 Frozen、excluded_pathset_changed / projectable 事实均不等于私有泄露或题级候选质量接受。

**停止条件满足：四 job 的关键模型工具 → 实际 baseline / 原 Frozen / projection → 完整正式 grade → 清理与异常传播各完成一次追踪。** 可进入原计划的题级语义和结果汇总；本角色没有提出共享捕获/运输修改、模型重跑或新验收闸门。取消异常语义广度、公开自测两失败与原问题的关系及未覆盖 runtime 事实留在上述边界，本轮停止，不扩到其它题、模型或训练契约。
