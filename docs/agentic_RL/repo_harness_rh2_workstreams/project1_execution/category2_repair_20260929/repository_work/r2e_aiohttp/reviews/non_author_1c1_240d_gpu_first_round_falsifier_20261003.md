# 1c1／240d 首轮 GPU 非作者 Falsifier / Simplifier 复核

日期：2026-10-03。按 AGENTS.md 与 review-standards §10.4／10.5，对四个固定 job 做一次离线窄核。已见 actual trajectory、候选与私有评分，不是 fresh 公开盲审。仅标准库解析、`python -B`、`PYTHONDONTWRITEBYTECODE=1`；没有 SSH、Docker、pytest、安装、模型调用、CPU 矩阵或共享文件编辑。

**结论：三条通过记录可以保留为当前固定评分范围的探索性求解证据；Coder 240d 的 null 保留，实际原因是候选撤回兼容预置后引入 SyntaxError。** 不能把 1c1 的 58／58 说成完整清理保证：Coder 候选新增条件缺少 cancelled guard，存在可由公共 coroutine app 进入的清理跳过分支。本轮实际轨迹没有触发它，不据此改原评分或自动追加 CPU 依赖。Qwen 240d 与 Coder 240d 都实际遇到范围外旧 HTTPS API 兼容缺口，不能外推完整客户端／服务端兼容。

| 固定 job | 原始正式结果 | 本轮独立证据与用途限制 |
| --- | --- | --- |
| `gpu1003-aio1c1-qwen36-a1` | resolved，raw 1.0，58／58 | 按完成状态去重；取消期间新 cleanup 错误仍报告。当前调用链未找到已观测新错漏报；不声称所有私有 helper 用法均正确 |
| `gpu1003-aio1c1-coder-a1` | resolved，raw 1.0，58／58 | 启动／原错误去重、当前中断后 cleanup 新错可观察；done+cancelled 主任务边界会跳过后续清理，限制完整性结论 |
| `gpu1003-aio240d-qwen36-a1` | resolved，raw 1.0，33／33 | 真正 connect 复现保留 1234；其他 HTTP 端口和 CONNECT 单次端口由原 33 键验证。stash 后已恢复兼容预置 |
| `gpu1003-aio240d-coder-a1` | failed_to_grade，raw null，test_log_parse_failed | 早期端口修法有效，最终撤回三兼容文件；actor 内已出现 client.py:140 SyntaxError，评分 33 键全部缺失 |

四条 solve 均 completed、harness exit 0、日志完整、清理成功。这只证明尝试完整结束；其中 null 不改为 0，不注入 qualification，不虚构恢复兼容层后的成绩，也不为通过重采。

## 固定材料与精确评分读回

复用 [既有 CPU R6 独立语义报告](non_author_1c1_240d_r6_falsifier_20261003.md)（SHA256 `a6af2757be6d5bce3a3708dc1f469bbb65fb0c5ebe3d3a64829ac53ba67b0fae`）的同 SHA 正负对照结论，不重新展开 oracle 设计或共同 Git／运输协议。当前 request 绑定 1c1 为 080／081，240d 为 082／083／084；固定 release 为 `cat2-cpu-r2e080087-swe8-git-20261003-v1`。

两模型各自 `solver_prompt.txt` 都包含其 request 指定的完整题面与当前 brief，`attempt/prompt.txt` 与之逐字节相同；prompt 摘要符合 attempt 记录，public bundle digest 与 request 一致。1c1 的题面/brief SHA 为 `b66629f137ff1c11b95f9c4cadc257ae2963b40abdbd54a735077dbb16039d85`／`8fa9daeae7d032d109ea073f53e8a2131567352318ba015c32ccae655da22909`；240d 为 `d3ff12a9a27890831dcedc62d53e8c124647d6fe036c28712505ed247d7a272c`／`d99fa9ea660d6321729f26cf87542da4fda02674ec06426af9a676f2b0631908`。

本轮核当前评分文件摘要仍匹配 request：1c1 test／expected 为 `5b38ccd1dd8083acbcb8db229a471517512434a5caccdddf0461f418c181910d`／`1bc0a6c74ee6fceb75b695d4d269c90f752deccf60b842db647a3602e1499370`；240d 为 `77b15aea1c9557adb5c686c4ff12055609578eecacfd754a2001cbe32dc8b18a`／`8dab59950c1837a195f854e669fc3778200025beaf29431864e58a2ebe3a3c70`。四日志的 hidden tree、run entry 都匹配 request；没有误用旧 57／35 键材料。

直接从完整日志的 pytest 状态行解析原始键，保留参数化名称，再与固定 expected map 比较：Qwen/Coder 1c1 各 58 个精确键、状态全匹配；Qwen 240d 33 个精确键、状态全匹配，均无缺失/额外键。这个核对独立于 report 的总通过数。Coder 240d 则没有任何 33 个测试的 PASSED／FAILED 状态，只有额外 `ERROR r2e_tests/test_1.py`；不能称“33 个断言都失败”。

四次评分 `baseline_rebuild_passed=true`、setup apply RC 0、预期/实际私有文件数量相等、缺失 0、runner 未改、segment 完整、install skipped。Coder 240d 收集错误没有 OOM、pids max 或 signal exit 证据。自动诊断仍是 `kind=unattributed`、`qualification:absent`、`compile_probe=null`，报告 `execution_failure_stage=null`；人工因果分析不覆盖这些原字段，不新增运行资格。

## 1c1：去重与新 cleanup 错误是不同路径

证据：Qwen [actual trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/attempt/trajectory.jsonl) · [FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/attempt/frozen/frozen_patch.json) · [完整评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio1c1-qwen36-a1/grading/eval_logs/evallog_gpu1003-aio1c1-qwen36-a1_7b2bcbaa.eval.log)；Coder [actual trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/attempt/trajectory.jsonl) · [FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/attempt/frozen/frozen_patch.json) · [完整评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio1c1-coder-a1/grading/eval_logs/evallog_gpu1003-aio1c1-coder-a1_47a61611.eval.log)。以下行号均为相应 `attempt/trajectory.jsonl` 的一基行号；代码行号指 FrozenPatch 解码后的 `aiohttp/web.py`。

Qwen 在第 98／144 行原始复现中观察到 RuntimeError 被抛出且另调用 loop handler；第 158 行只修改 `_cancel_tasks`。最终代码 web.py:447–450 记录取消前已 done 的任务，458–464 先跳过 cancelled，再对已有异常的 already_done 任务跳过重复报告。`run_app` 的 main cancel → other tasks cancel → shutdown_asyncgens → loop.close 顺序不变；`_run_app` 的 `finally: await runner.cleanup()` 不变。第 180 行 duplicate handler 为 0，第 200 行公开 55 passed，第 218 行原 RuntimeError 仍抛出。

“所有 already_done task 的错误都正在向 caller 传播”这句候选注释过宽，不能在任意直接调用 `_cancel_tasks` 时成立；但当前 `run_app` 只传 `{main_task}` 与 `asyncio.all_tasks(loop)`，后者不含 done 任务。正常运行中 main 已失败时 `run_until_complete` 已拿到原错误；主任务 pending 且取消后 cleanup 新抛错时，它不在 already_done 集合，仍交给 loop handler。没有在这条当前调用链看到新 cleanup 错误被广泛吞掉的证据。

Qwen 自写“pending tasks 验证”第 232→236 行确实报告新 `FAIL`，但它把 `stopper` 错写成 async 函数，实际触发的是 `TypeError: 'coroutine' object is not callable`；不能拿这次打印当作精确 Ctrl-C 复现。正式 R6 新键的真实通过更有决定力：test_1.py:952–974 是已启动 cleanup context 在 `stopper` 的 KeyboardInterrupt 后到达 cleanup、抛新 RuntimeError，要求 caller 抛出或 loop 报告二者至少一种；Qwen 和 Coder 的完整正式日志均明确该键 PASSED。

Coder 第 66 行原例同时输出 handler 日志与 RuntimeError；第 88 行改 `run_app` 的 finally，仅在主任务 done 且有异常时跳过 `_cancel_tasks({main_task}, loop)`，其余取消/关闭步骤保持原顺序。第 105 行仍抛原 RuntimeError而无重复 handler，第 120 行公开 55 passed；第 201／216／231 行分别通过 startup cleanup、cancel-failed-task、coroutine app 公开测试。第 142 行自写脚本把“stderr 必须出现一次”当成成功要求，观察为 0 次并失败；题面要求不额外日志、允许 caller 捕获，所以这不是候选失败的反证。第 186 行只验证 RuntimeError 类型/消息，没有独立统计日志，最终“全部边界无回归”声称超出它的证明力。

**Coder 有明确取消边界欠保护。** web.py:525 的 `if main_task.done() and main_task.exception() is not None` 未先检查 `main_task.cancelled()`。公共 `_run_app` 在 321–322 接受 coroutine app 并 `await app`；若该协程取消或 await 的操作被取消，主任务可以 done+cancelled。此时 `Task.exception()` 本身抛 `CancelledError`，finally 后续其他任务取消、asyncgens shutdown 与 loop.close 被跳过。这个链不要求新能力，属于当前公共调用路径的静态可达分支；本轮四条实际轨迹没有触发，现有 `test_run_app_coro` 只测正常返回，`test_run_app_cancels_done_tasks` 测的是成功完成的旁支任务，均不能反证它。

因此原 58／58 保留为当前评分事实，但不能据此声称 Coder 获得完整 cleanup 保证。处置为本轮候选用途限制／residual risk：不改原成绩，不立即加 CPU 依赖或再开矩阵；将来若要以此候选证明全面取消/清理正确性，仍缺该边界证据。新 cleanup 错误在当前 R6 KeyboardInterrupt 路径可观察，与上述已 cancelled 主任务分支需要分开表述。

## 240d：端口修法与最终候选状态

证据：Qwen [actual trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/attempt/trajectory.jsonl) · [FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/attempt/frozen/frozen_patch.json) · [完整评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-aio240d-qwen36-a1/grading/eval_logs/evallog_gpu1003-aio240d-qwen36-a_d32e3fac.eval.log)；Coder [actual trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/attempt/trajectory.jsonl) · [FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/attempt/frozen/frozen_patch.json) · [完整评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16r1/results/gpu1003-aio240d-coder-a1/grading/eval_logs/evallog_gpu1003-aio240d-coder-a1_be7dbfdf.eval.log)。

Qwen 第 106 行用实际 `ProxyConnector.connect` 观察原路径丢失 1234，第 120／152 行改 connector 并导入 `HTTP_PORT`；第 174 行真实路径保留 1234，第 192 行公开 ProxyConnectorTests 13 passed。最终代码 connector.py:342–348 按 `req.port` 拼入非 80 端口，保持 `req.host` 不变；CONNECT 仍在 364–365 使用 `req.host:req.port`，没有先把 port 嵌进 host 再重复拼。正式 `test_request_port`、`test_request_port_other_url`、`test_https_connect_port` 连同 30 旧有效键全通过；这与已有 R6 区分示例/非示例端口、单次 CONNECT port 的语义一致。

Qwen 第 260 行 stash 暂时撤回来源兼容预置，264 行收集出现 client.py:140 SyntaxError；274→278 行实际 stash pop 恢复，最终 314 行真正 connect 的断言成功。最终 FrozenPatch 只含 connector.py，client/server/worker 没有相对 baseline 回退。因此短暂出现同类 Git SyntaxError不能认定最终 Qwen 候选失败。其修法按 HTTP_PORT 而非完整 scheme 分类，不外推所有 URL 形式、端口规范化或任意 scheme 的精确保真；本轮不扩新 URL oracle。

Coder 的目标修法本身也有实际依据：第 136 行原例断言失败，第 145 行编辑后 162／245 行真实 connect 复现通过，第 175 行公开代理 13 passed。它按 HTTP 80／HTTPS 443 的默认端口判断拼接路径，CONNECT 分支仍使用独立 `req.host:req.port`，没有把端口回写 host。第 188 行跑全 connector 文件得到两个旧 TCP／Unix 失败、30 passed；这两个测试正是 R6 已删除的已知兼容失效项，不属于当前 33 键回归，也不能当作新端口修法失败。

**最终失败与端口算法分开归因。** Coder 第 258 行 Git diff 已呈现 client/server/worker 的来源兼容预置；267→271 行实际执行 `git checkout -- aiohttp/client.py aiohttp/server.py aiohttp/worker.py`。289→293 行脚本、302→306 行公开 pytest 都在 actor 内先于 freeze 遇到 client.py:140 `asyncio.async` SyntaxError。内存读 baseline.tar 与 FrozenPatch 三文件比较，差异精确等于把 `asyncio.create_task(` 变回 `asyncio.async(`；client.py 140／512、server.py 109、worker.py 29 均回退。评分 Python 3.9.21 与 actor 相同，完整日志再于 r2e_tests/test_1.py:11 → aiohttp/__init__.py:7 → connector.py:13 → client.py:140 收集失败、0 items／1 error、test RC 2。不是运输后才写坏或 grader 解释器漂移的证据。

最终 FrozenPatch 为四个生产文件和两个 helper；并不是最后 Git diff 所显示的“只改 connector”。initial Git dirty 兼容层是真实误判诱因、可改善呈现，但 actor 已在最后看到错误，仍用早期成功声称最终修复。原 `failed_to_grade/null` 不变；候选自行撤回兼容预置的语义失败可以明确记录，不能把 report 的 `infra_failure_detail` 字段名直接当作基础设施实故障。

两条 240d 实际扩展 HTTPS 验证都在第 210 行遇到预存 `asyncio.create_task(..., loop=...)` TypeError。Coder 第 219 行把 comprehensive helper 改成复制端口公式的手算，232 行“全通过”没有再调用真实 HTTPS connect；最终“all edge cases”声称不成立。Qwen 最终成功也只证明当前 HTTP 例及正式 mock CONNECT 范围。固定 brief 已明确公开命令是 mock transport 代理测试、未验证真实 TCP／Unix 客户端/服务端；这里的实际 TypeError 是既有范围外兼容限制，不能抹去，也不将它自动变成当前 CPU 修订依赖。两个原 33 键候选状态没有被恢复兼容层的假想成绩代替。

## 最小交付与停止条件

建议主审合并四条原结果及上述用途限制：保留三条当前材料下的解题证据和一条 null／候选回退失败证据；1c1 Coder 的取消 guard 欠保护禁止被包装成完整 cleanup 证明，240d 的旧 HTTPS 兼容与手算 helper 禁止被包装成全模块验证。四 job 的 baseline rebuild、完整 actor 先后关系和正式日志已经足以区分本轮候选结果，不需要重采、注入资格或重审共同机制。

这份报告不授予训练／留出资格，不扩大到其它题、模型、job 或新评分契约。一次有界四 job 复核结束；理论 URL／exception 包装反例仅保留边界，不继续展开。原件保持只读，仅新增本报告。

为便于定位，四个完整日志的既有 SHA256（已核符合 report）依次为：Qwen 1c1 `a1879ddddaec28f7b829a07b3db938b9decacbcb4cbfab691451efd1adcbcefe`；Coder 1c1 `6c9f79400606d2f66e5c09815768aad8b46ca9adc74ecb6fd89ce292cb874983`；Qwen 240d `5da3e68092448563b34060b9077b026d291110c266e6ce7cc1cf4e4c1a8d1df2`；Coder 240d `555e8e0db04ee2a6cae24d798bd6947a1bae8b4d7e31a60dad1571a4dceeb2cf`。不追加全文件哈希清单。
