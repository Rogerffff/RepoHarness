# 1c1 公开 cancelled-main 输入：实际执行归因复核

日期：2026-10-03。角色：非作者 Production Tracer。按 [review-standards §10.4/10.5](../../../../../review-standards.md) 完成一次有界实际链路复核；这是已知原候选及作者结果后的离线审查，不是 fresh 公开盲审。

**结论：本次原件链足以支持 Coder 完整原候选在公开自身取消输入上的清理回归。** 同一原基线、镜像、身份和输入下，基线及 Qwen 在 `run_app` 返回控制权前完成 worker、async generator、event loop 的清理；Coder 留下 1 个 pending task、开放的 generator 和 loop，之后由观察者补清理。本次观察不计算 reward，不改旧 raw1/58，也不作为新的正式评分或训练资格裁定。

## 固定范围与执行前问题

唯一输入调用公开 `web.run_app(cancelled_app_factory(), loop=loop, handle_signals=False, print=None)`。coroutine 先让 worker 实际开始、让 generator 产出一次并保留强引用，再取消当前 main task。未替换 aiohttp 库函数；取消发生在真正 `_run_app` 的 await 路径。`after_run_app_before_observer_cleanup` 在任何观察者补清理之前保存，避免把补救误记为库内清理。来源：[公开输入](../followup_1c1_cancelled_main_20261003/public_cancelled_main_probe.py)、[固定驱动](../followup_1c1_cancelled_main_20261003/run_fixed_public_probe.py)。

执行前发现的具体问题是：驱动最初虽核输入文件 SHA，却没有把实际转交的 commands、overlays、prepared summary 参数硬绑定到本批文件；公开输入仅检查 Python 3.9 大小版本。它们会削弱“实际执行的就是固定输入/环境”的解释力。最终固定驱动已绑定 case 对应 commands、原 overlays、prepared summary 的本次实际 SHA，并核实际捕获的 Python 3.9.21。此次实际参数与这些绑定相符，未留下这一解释缺口。

独立重核 [input_manifest.json](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/input_manifest.json) SHA 为 `921aebdb79dadef42c487e064b749de94a02242012c3cf05410e6f77f75a6517`；其 11 个文件 SHA 与 bytes 均相符。公开 probe 为 4345 bytes，SHA `50c09f6ee8e303a1521dbfc958be4cbcc67055e82f493cd70cde3d8ca23b598e`；最终驱动 SHA `91b2712747ac46b7f3ba2167c0e0cc6bb39eff74a8405a29397b29f43da98d48`。三份 commands 的 here-doc 正文均逐字等于该 probe。

## 原基线、完整候选与实际树

固定入口是 R6 `cat2-cpu-r2e080087-swe8-git-20261003-v1` 的 `rh2/experiments/r2e_actor_20260925/r2e_devcheck.py`；release manifest SHA 为 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`。驱动校验后使用此入口，转入已审 DevRunner；不另造替代库运行路径。共用机制沿用同 SHA 的既有 [R6 执行复核](non_author_1c1_240d_r6_execution_trace_20261003.md)，本轮不重新全核 release code manifest。

原 baseline tar SHA `a6441ad8cd27ab02b38834e847ad17c8099da6d80e99347cf9e3745ff625bff8`，native manifest 文件 SHA `c0a8b09805d2c59415506c0df5e2560bcfbaeba8aed612cc638a5dd32e1e2b61`；307 项 canonical digest 为 `40b0956474180605d1f46cc2b59f3e4ae3dcef0fffd18f9f2ff24b539d007608`。三侧实际 initial manifest 的 entries、canonical 身份均与它一致，HEAD 都为 `87342c791dfd4c916877ba3dffafb9345bb0491f`。

| 实际侧 | 完整原 Frozen 身份 | 应用后 canonical 树项数 | 实际 `aiohttp/web.py` SHA |
| --- | --- | ---: | --- |
| baseline | 无候选 | 307 | `da7193c490d70bcaa96ee788ff434fdb60ea6a344ca2e32a08118b20405ec746` |
| Coder | 7 项；`dc7a8f17e1b22988f2091bc882fb75fb28227a61bb97b26d713b03d69e70798d` | 313 | `279d0a2d2b733dcb0bce0530043de938ec3fc8148f98bcc2e9a1f76ce6ae8887` |
| Qwen | 2 项；`77d02d948b6a6e003aba9a497d905189c15b174ddb02f5f10b3fa62362b036be` | 308 | `f7c5c1d1b2fd638d4527ca8e2c17a105512848d6da24d2b6220f5124dfd92933` |

Coder 实际应用 `.coverage`、`FIX_SUMMARY.md`、`aiohttp/web.py`、`comprehensive_test.py`、`reproduce_issue.py`、`test_exception_handling.py`、`verify_fix.py` 全部 7 项；Qwen 实际应用 `.coverage` 与 `aiohttp/web.py` 两项。独立以原 Frozen 的完整 entries 构造 baseline 加候选的预期树，三侧 actual candidate manifest 均精确相等；再逐项比对原始 census 的路径、object type、Git mode、内容 SHA，六份初态/候选 census 与对应 manifest 均精确相等。没有把单个 web.py 拼成候选；排除的运行时文件未作为候选回放。来源：[固定输入目录](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1)、[baseline 原件](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/baseline)、[Coder 原件](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/coder_full_frozen)、[Qwen 原件](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/qwen_full_frozen)。

## 实际环境与 CC 工具链

三侧 prelaunch 均为 `ok=true, violations=[]`：实际 image 是 `sha256:00ad3e96b2ec0cf385aba6e9b69b6335c5e1623c5c3235cd57c34d6300b87683`、Linux/amd64；Docker inspect 为 2 CPU、4294967296 bytes memory，PIDs 512，swap 与 memory 同额，非 privileged、无 bind/mount、init 开启。实际 agent UID/GID 54321，effective capabilities 0、NNP 1；cgroup CPU `200000 100000`、memory 4 GiB、swap 0、PIDs 512；tmp 1 GiB、home 256 MiB、writable quota 8 GiB。原 prelaunch 的隐藏路径和受限网络检查符合本批 profile。

工具内 identity 三侧均记录 `/testbed/.venv/bin/python`、Python **3.9.21**、UID **54321**、`/testbed/aiohttp/web.py` 及上表 SHA。实际 CC 版本为 **2.1.205**。preflight 经 CC Bash 输出 interpreter、hidden tests、git history 三项 `ok`。这些是本次实际身份与预检证据；并不靠退出码推断环境。

每侧完整 trajectory 为 28 个事件：桩提供 preflight Bash、公开 probe Bash、结束文本，实际出现两次工具调用、两次对应 tool_result、三次请求及正常 success result。独立核工具 ID 配对、完整 capture 与 tool_result 正文，以及下一请求携带的结果，全部一致。公开命令在 CC 记录中去掉了内部冗余 `cd /testbed &&`，外层仍先 `cd /testbed`；解析实际 `bash -c` 后，除此之外命令和 4345-byte probe 正文精确不变。这不构成输入运输失真。证据均在上述各侧 `stub_script.json`、`harness/trajectory.jsonl`、`stub/stub_log.json` 与 `captures/`。

三侧 preflight 完整输出均 88 bytes；公开 probe 完整输出分别 927、900、935 bytes。它们与 `commands_result.output_bytes` 一致，远小于 200000-byte 捕获上限；工具结果含完整输出而非被截断的片段。三个公开命令 RC 均为 0、`expect:any`：只说明捕获程序正常完成观察，不能称为行为通过。

DevRunner 旧通用字段 `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false` 保留原值。本输入未提供旧通用 PY_CHECK/denial marker，因此不能把它们改成 true；本批环境结论由实际 identity、prelaunch、R2E preflight 支撑，不主张所有通用 checks 已通过。

## 原始观测与异常传播

| `run_app` 交还控制权、观察者补清理前 | baseline | Coder 完整原候选 | Qwen 完整原候选 |
| --- | --- | --- | --- |
| caller exception | `CancelledError` | `CancelledError` | `CancelledError` |
| main done / cancelled | true / true | true / true | true / true |
| worker done / cancelled | true / true | false / false | true / true |
| pending task count | 0 | **1** | 0 |
| generator closed / loop closed | true / true | **false / false** | true / true |
| worker / generator cleanup 事件 | 两者均有 | **两者均无** | 两者均有 |
| observer cleanup needed | false | **true** | false |

三侧均先出现 `worker_started, generator_started, main_self_cancel`，排除了 worker 未进入运行状态或 generator 未开始的伪差异；三侧 loop handler 均为空。Coder 的观察者补清理随后没有报错并关闭 loop，单列为事后回收，不能覆盖表内原始状态。完整原 JSON：[baseline capture](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/baseline/captures/cancelled_main.out)、[Coder capture](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/coder_full_frozen/captures/cancelled_main.out)、[Qwen capture](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/qwen_full_frozen/captures/cancelled_main.out)。

因果归因由原代码与该观测共同支持：baseline 的 `finally` 顺序取消 main、取消其余 tasks、`shutdown_asyncgens()`、`loop.close()`；Qwen 保留这一顺序。Coder 在这些收尾动作前新增 `if main_task.done() and main_task.exception() is not None:`。本次 main 已 done 且 cancelled，调用 `main_task.exception()` 自身抛出 `CancelledError`，跳过后面的 worker/generator/loop 清理。公开输入没有修改这段代码，完整实际候选树又绑定到原 Frozen，因此足以归因为原 Coder 候选的该分支，而不是捕获或运输错误。由于 probe 只记录异常类型与资源状态，没有异常栈或第二次注入，具体抛出位置是基于固定原代码的因果判断；不声称已经逐帧运行追踪。

## 完整性、生命周期与停止边界

独立重算归档 SHA `61b87b3b100c433a051c013cc49fdb05599f24ade84e6de3a8340a3d20f46a63`；[archive_manifest.json](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/archive_manifest.json) SHA `5e3c2344e4ae3b42684b56bd958620ece17abc7b6e4f197d4bb99884eab29ae9`，所列 96 文件实际 SHA/bytes 全部相符。此核查以原件为准，没有继承 owner readback 的裁决。

三侧实际 process argv 均指向固定驱动、对应输入 commands、同 overlays 与 prepared summary；[prepared replay_summary](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/outputs/prepared/replay_summary.json) 实际 SHA `4dfc6de582b7f913af734c6e265c0e4cacd62ac3c793bf10368db9c6a30040cf`，与参数硬绑定一致。每侧 wall limit 600 秒，公开 Bash 使用 `timeout -k 10 120`；三侧正常结束，未发生命令 timeout。

实际 [slot status](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/slot_job/status.json) 为 finished/0；[controller receipt](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/actual_artifacts_v1/bounded/outputs_v1_bounded_controller_receipt.json) 记录 05:56:26–06:01:17 UTC、return 0、whole-run budget 1800 秒、cleanup grace 120 秒、`timeout_occurred=false`。独立重核 [controller 源码](../followup_1c1_cancelled_main_20261003/bounded_controller.py) SHA `f2e1e411b4a703462a1eac0ce5248c3bdc94cb552e2228d1eb6d91c668fa5a09` 与实际 launch 一致。它配置了超时后进程组 TERM、宽限后 KILL；本次没有触发，强制超时分支的实际效果为 unknown，不能据此宣称已实测。

三份 attempt 的 container remove RC 0，network/relay failures 为空，stub RC 0，labeled containers/networks left 与 residual-after-force 均为空。Coder 在库内清理时留下资源，与随后观察者回收及 harness/container 清理完成是两个不同事实；本次未把后者当成候选语义成功。

本次不存在阻断该单输入归因的材料缺口。**实质行为阻断是 Coder 的取消态清理回归**：原有 58/58 不能证明该公开行为正确。Qwen 仅在同一输入上与 baseline 一致，不据此扩大接受范围。仅核一次三侧执行，不估计发生频率，不覆盖其它取消时序、真实服务器长时运行或所有 Qwen/Coder 行为；没有新模型采样、正式评分、CPU 矩阵、pytest、远端操作、release 写入或训练契约审查。旧 raw 值保持。基线和完整 Coder 的实际差异链已足够解释，停止本轮审查。
