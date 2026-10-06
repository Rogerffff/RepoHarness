# 1c1 首轮：两种去重修法通过，取消边界保留限制

整理：2026-10-03，Asia/Singapore。固定请求 `aiohttp1c1-r080081-probe-wide-v1-20261003`，原题面、中性brief、080/081的58键和 `probe-wide-v1`。两个模型各一次，正常结束、完整评分并清理；原分均1，题主按完整日志逐键重算均58/58。可接受当前重复报告目标的探索性结果，不能称整个取消／清理控制流已完整正确。

| 项目 | qwen36-a1 | coder-a1 |
| --- | --- | --- |
| 原始正式结果 | reward1，58 PASSED／58键 | reward1，58 PASSED／58键 |
| 原候选全部条目 | `.coverage`与`web.py`，2项 | `.coverage`、说明、`web.py`及4个脚本，7项 |
| 生成请求／工具调用／CC回合 | 16／16／17 | 20／19／20 |
| 累计输入／输出 token | 559,669／7,145 | 571,371／4,996 |
| solver 用时 | 82.050秒 | 92.988秒 |
| CC API／CC总用时 | 47.100／78.790秒 | 46.100／89.617秒 |
| 环境 trusted_init，solver外 | 60.605秒 | 62.054秒 |
| 正式评分用时 | 93.092秒 | 95.537秒 |

输入token是逐次送入上下文的累计值，不是峰值context。API包含服务／网络，CC差额不能直接叫工具时间；真实公开pytest本身各约28秒。评分和环境计时单列；没有足够调度时间戳重算模型作业排队时长。report的grading queue_wait=0不代表整个GPU队列等待为零。

## 修法与实际纠错

Qwen检查 `run_app`、runner、cleanup context与公开测试，先复现主异常已抛出但loop又报告一次。第10生成轮在 `_cancel_tasks` 记录取消前已经完成的任务，对这些任务不再重复调用exception handler；取消期间新产生的异常仍走原loop报告，取消、gather和最终关环顺序保留。第11轮实际例子报告数从1变0，第12轮公开55测通过，正式58键也包括新增“中断后进入cleanup且新错可观察”的断言。

Qwen的两次工具错误是 `/tmp` 脚本导入路径和缺 `logging`，随后修正。第14轮所谓pending-task验证同时遇到自制stopper的 `'coroutine' object is not callable`，又确实观察到后台取消产生的 `FAIL` 被loop报告。这个输出不能证明它完整模拟了预期KeyboardInterrupt场景；正式新增键的通过提供了更明确的当前参考证据，不把打印的成功标记当全控制流保证。

Coder先从原复现确认重复报告，在第7轮改变 `run_app` 的finally：主任务已完成且有exception时跳过对它的 `_cancel_tasks`，否则沿用原取消；其它任务、异步生成器与loop关闭保留。第8轮仍向调用者抛原RuntimeError而去掉额外loop报告，第9轮公开55测通过；后续又跑startup／cleanup信号、失败任务取消、正常coroutine app三项公开测试，均通过。

Coder的自制 `comprehensive_test.py` 曾错误地要求修复后仍在stderr报告一次，因实际为0而输出失败。随后它修正验证理解并用更直接脚本核异常传播，未再次修改生产代码。不能把这份辅助脚本的失败当基础设施故障，也不能把模型最后“all tests passing”当所有遗留helper均通过。说明与helper及coverage文件均原样进入正式Frozen和评分，没有替模型清理。

## 取消边界与覆盖范围

Qwen的注释把“已完成”都说成“正在向调用者抛出”过于宽泛；当前真实 `run_app` 调用只传主任务或 `asyncio.all_tasks(loop)`，后者不包含已完成任务。当前观察与正式58键支持普通主异常去重、取消过程中新cleanup错误仍报告，但不能外推任意直接调用 `_cancel_tasks` 的done集合。

Coder的新增条件 `main_task.done() and main_task.exception() is not None` 没有先检查 `cancelled()`。静态当前调用链允许public coroutine app进入 `_run_app`；若主任务已完成且被取消，读取exception会再次抛 `CancelledError`，可能跳过后续其它任务清理、asyncgen关闭和loop.close。四份实际轨迹没有触发这个分支，公开 `test_run_app_coro` 只测正常返回，58个参考也不证明这条边界。保留为实际候选的取消风险；未跑反例，不改原分或自动新增CPU矩阵。正式训练资格未授予，后续扩大清理保证前应处理这一边界。

当前CPU材料对C3吞新cleanup错的已知漏判已关闭；本轮两候选并没有出现仅把错误放在 `__cause__` 的新包装实现，旧的条件性风险不凭空升为当前阻断。

## 工具、并行与原件

Qwen使用Read5／Bash10／Edit1，有1个同轮双工具批次，用于独立读测试和找实现；Coder使用Read3／Bash10／Write5／Edit1，无同轮多工具调用。独立阅读和复現有并行机会，修改与复验有依赖；没有完整工具起止时间，不能证明执行层重叠或下稳定并行能力结论。

两次都是原始完整候选，307个baseline条目逐内容／Git mode核实，Qwen2项、Coder7项原Frozen内容及全部projection一致；完整正式日志按short summary保留参数名空格逐键解析，避免把captured log中的ERROR日志当测试状态。两次原分、公共prompt／brief、预算、同源重建与双层清理均由原件和独立执行报告绑定。code_snapshot_id等原空字段不补，Qwen是原Q11作业，不能误记为Q10。

当前只有每模型一次，不计算稳定成功率。原请求交接核收后，同条件第二阶段重复仍按统一安排；训练／留出资格未授，后续数据划分仍以aiohttp整个仓库为单位。本批仅本地读回，无新增CPU、模型求解或评分。机器记录与核收见 [首轮行为](trajectory_analysis1c1_20261003.json)、[Qwen题主结果](results1c1_qwen36_a1_20261003.json)、[Coder题主结果](results1c1_coder_a1_20261003.json)。
