# 1c1：取消分支回归与一项P2P补缺建议

2026-10-03。题主对一次公开输入的实际归因及两份非作者有界核查均已完成并核收。原首轮Coder／Qwen各58/58、raw reward 1和旧结果文件不改。这里记录的是候选新增公开行为回归与测试覆盖遗漏，不是重算正式成绩。

在原00ad演员镜像、Python3.9.21、UID54321、2CPU／4GiB／512pids下，真实`run_app(coroutine)`接收到主任务自身取消。原基线全部307文件先核一致，再完整应用Coder7／Qwen2条FrozenPatch，得到313／308文件的对应可评分树；候选helper与coverage保留，排除的运行时文件不冒充原solver运行目录的复制。实际固定R6入口、CC2.1.205桩的两次Bash调用依次为R2E预检和同一公开脚本，没有模型生成或正式评分。96个原件已完整按SHA和大小回收，作业正常结束，三个actor/网络/relay/桩均已清理，标签容器/网络残留为空。

| 观察者补清理之前 | 原基线 | 完整原Coder | 完整原Qwen |
| --- | --- | --- | --- |
| caller异常 | CancelledError | CancelledError | CancelledError |
| 主任务done／cancelled | true／true | true／true | true／true |
| 后台任务done／cancelled | true／true | false／false | true／true |
| asyncgen关闭 | true | false | true |
| loop关闭 | true | false | true |
| pending任务 | 0 | 1 | 0 |
| worker／generator finally事件 | 均发生 | 均未发生 | 均发生 |
| observer补清理 | 不需要 | 需要，随后关闭loop | 不需要 |

caller的CancelledError是三侧共同结果，不能用它单独宣布回归；脚本rc0也仅表示观察成功。资源差异发生在observer之前，之后的补清理不能算作库的成功。Coder冻结`aiohttp/web.py:525`在`main_task.done()`为true时直接取`main_task.exception()`，缺少cancelled guard；读取已取消任务的exception会抛CancelledError，使其后530–532行的全任务取消、asyncgen关闭与loop关闭不能执行。动态取证没有采样异常堆栈，这一控制流归因由精确生产源码、实际done/cancelled状态和资源差异联合得出。原基线和Qwen同输入正确清理，因此不是基线同错或输入无法触发。

一般DevRunner的`interpreter_in_tool_result`和`bashenv_denied_for_agent`为false，因为本次命令没有发出它们所需的标准marker／权限写入探测。此次核对使用公开脚本实际identity、R2E preflight、正式容器参数和完整census；不宣称复验了整条harness所有权限／资格能力。旧模型checkpoint／sampling／code_snapshot等原有证据边界保持。

建议只补一项取消P2P：同一公开coroutine先使worker进入try、打开强引用asyncgen，再取消当前主任务；观察`run_app`结束后，worker收尾、asyncgen关闭、loop关闭且pending为0。保留正常取消传播，不锁异常message／traceback、不要求捕获新的stderr文字或指定内部修法。测试失败后的observer清理只放在finally，断言必须先执行，不允许清理动作使失败变为通过。

可追加的检查逻辑（尚未加入正式材料）：

```python
try:
    with pytest.raises(asyncio.CancelledError):
        web.run_app(cancelled_app_factory(), loop=loop,
                    handle_signals=False, print=None)
    assert state['main_task'].done() and state['main_task'].cancelled()
    assert state['worker'].done()
    assert 'worker_cleanup' in state['events']
    assert state['generator'].ag_frame is None
    assert 'generator_cleanup' in state['events']
    assert loop.is_closed()
    assert not asyncio.all_tasks(loop)
finally:
    # 如失败留下资源，观察者在此回收；不能先回收再断言。
    recover_observer_resources_if_needed(loop)
```

factory／worker／asyncgen及后清理实现直接来自固定4345字节公开脚本，不引入私有API或替换库函数。该项原基线和有效替代实现应通过，属于保留已正常的公开行为（P2P），不人为加入新功能。旧58键和题面保留，预期只追加一个收集后核实的PASSED键，58→59；不先虚构pytest精确key或占材料revision编号。

建议本批裁定接受这一窄修订后，再由题主准备材料、发布线程登记／冻结／部署，沿固定入口验证实际59键消费。至少核原基线、gold／C1两种合理实现以及原完整Coder／Qwen；旧矩阵的未改断言证据按适用范围复用，不先重跑整个矩阵。新的结果作为材料验证记录，不能回写原模型首轮reward，也不能裁剪或重解原候选来让它通过。此建议不直接发布、不修改共享reward契约，不启动追加模型采样。当前1c1旧binding的题级阻断保持，其他三题不受此具体缺陷影响。

依据：[实际结果](results_public_cancelled_main_20261003.json)、[非作者核收](review_acceptance_public_cancelled_main_20261003.json)、[执行报告](../reviews/non_author_1c1_cancelled_main_execution_20261003.md)、[反证报告](../reviews/non_author_1c1_cancelled_main_falsifier_20261003.md)。
