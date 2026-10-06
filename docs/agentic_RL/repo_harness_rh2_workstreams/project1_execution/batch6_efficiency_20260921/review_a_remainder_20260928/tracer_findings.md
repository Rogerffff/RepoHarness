# A-N1 Production Tracer：一次有界复核

日期：2026-09-28。依据 HEAD `23f5586d`，限定 `5b00a091` 与 `8f31caee`；按 review-standards §10.4 追实际调用与资源所有权。

## 接线与边界

- 正式 bringup 在 `bringup.py:1472–1477` 只传 `eval_log_dir` 与 `sandbox_profile`，未传 `supply`。`prepared_task_face.py:400–402` 生成两份脚本，但没有供应政策。这次供应路径是已可调用的 manager 组件入口，尚非正式作业已启用能力。
- 实际开启要求 `manager.py:2138–2144` 的 supply、profile、两份脚本同时在场；缺 policy 在 `1919/2147–2153` 起容器前 run-halt。无安装段仍单 shell、全断网。
- manager 在创建网络前登记 record（`2395–2407`），run 成功后才登记 lease（`2414–2415`）；container 名是 token grant 的 attempt_id（`3415–3420`）。网关/relay 属 run owner，attempt 网络/token 属本次 record。
- profile 先建 internal 网络、接入 relay、启动并核对，再跑 root setup、保护官方文件、候选 UID 安装。`3434–3445` 由宿主 disconnect + inspect 空网络确认；撤网失败不测试、不奖励。确认成功后撤销 token、收摘要，`3453–3464` 仅 handoff 才以共用 timeout 剩余额度跑测试。
- 早退/carry 写失败仍交旧 parser/P-A；安装超时为 infra；取消原样上抛。队列 worker 直接 await manager（`queue.py:254`），强制 close 会取消 worker（`160–172`），所以本探针的一次外部取消是该组件接入队列后的真实可达事件。

## P2：释放 await 前丢弃 owner，取消会留下未申报的供应资源

触发范围仅为显式开启 supply 的 manager。

1. 正常安装与撤网后，`manager.py:3448–3449` 在 await gateway.release 之前清掉 `record.supply_token`。该 await 被取消后，grade 的 finally 仍删除容器、拆网，但不再尝试 token 释放；结合当前 gateway 在取消后保持 `releasing=True` 的事实，token 记录及终态摘要丢失在管理链之外。
2. 普通安装超时后，容器删除已经成功，finally 开始 `_release_supply_resources`。`2164` 先置 `supply_released=True`，`2167` 先清 token，`2170` 才 await release；一次取消在这里传播，网络 teardown `2178–2196` 完全不执行。`gc/close` 在 `2208–2209` 又跳过已删除容器。之后的 record 还具备 E4a 退役资格（`2523–2525/2540–2554`），不能视为未完成资源的可靠保留记录。

实证：`tracer_supply_cancel_probe.py` 调用真实 manager 与真实 `PackageIndexGateway.release`，Docker 使用作者既有 `SupplyDocker`。唯一人工边界是在真实 token.inflight 集合内放一条撤销后延迟完成的 task，以确定性命中真实 release 的 `asyncio.wait`；无 HTTP 服务、无 Docker 调用、无网络。结果见同名 JSON：

| 案例 | 返回 | 容器已删 | token / 网络 / 子网槽位 | 随后 close |
| --- | --- | --- | --- | --- |
| normal_control | resolved / reward 1 | 是 | 0 / 0 / 0 | 清理完整 |
| timeout_control | failed_to_grade / reward None | 是 | 0 / 0 / 0 | 清理完整 |
| cancel_normal_release | CancelledError | 是 | 1 / 0 / 0 | 不重试，cleanup_failures=[] |
| cancel_timeout_cleanup_release | CancelledError | 是 | 1 / 1 / 1 | 不重试，containers_open=[]，cleanup_failures=[] |

两取消案都是一次 cancel，均未启动测试，也未产生奖励污染。token 状态是 withdrawn；不能称为授权继续有效或网络隔离突破。网络残留可能由最终 run-label 清理兜底，但本次 manager 已失去正确收尾/报错语义。

最小修法方向：token/完成标志只在对应释放确认后更新；网关释放中断不得跳过 attempt 网络收尾。未收齐的资源继续有 owner 并可重试，或必须明确留下 cleanup failure。结合主审 gateway.release 取消修复一起验收即可，不需要新增 owner 状态机。最小验收就是上述两个取消点与两个正控；取消继续上抛，close 后资源确已释放，或保留明确可回收记录及失败事实。

## 事实持久化边界（供主审归并，不另扩大测试）

普通安装超时正控中 gateway.release 成功，record.supply 有 gateway 摘要，但 `tracer_supply_cancel_timeout_control_logs/*.diagnostics.json` 没有。正常正控的 sidecar 也没有最后的 network_teardown_failures。原因是 sidecar 在 `2076–2077/2114–2115` 写，finally 的 `2130→2170/2194` 才补收尾事实；`_diagnostics` 仅在 `1848` 取当时的 record.supply。网络 Brief §12.1 的“每种结束都把摘要写进评分事实”及 §13.3 的 sidecar 表述需限定或在收尾后补写。此差异不改评分结果，取消清理问题的严重度也不依赖它。

## 本轮未发现问题与验证范围

- E2b root 默认 `env -i` + 绝对 bash（`1000–1003/2663–2667`）；可信 setup 与 legacy eval 保留 image env，候选 UID 路径不改。候选执行后的 tee/cgroup/峰值读取均经默认安全前缀。只读核对命令链；本角色未复跑 Docker 劫持正控。
- E4a 按确认删除序号退役、遍历快照、不移除未确认删除的记录，累计与保留长度分离；CR1 已交付输出/退出码在 inspect await 前同步保存，短 tee 不覆盖长输出。
- 实跑聚焦 CPU：`tests/grading/test_e4a_history_and_cr1.py` 与 `tests/grading/test_supply_two_stage_manager.py`，**23 passed in 1.80s**。覆盖承诺的晚完成、满历史 gc、两取消窗口、短/长 tee 与两段三个终点。
- 新增独立 CPU owner 探针四案均完成。未修改源码、维护测试或共享文档；未用 Docker、远端或公网。停止于本边界。
