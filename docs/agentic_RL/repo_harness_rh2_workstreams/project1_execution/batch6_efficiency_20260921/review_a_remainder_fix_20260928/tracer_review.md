# AR2/O1 Production Tracer 有界复核

2026-09-28；HEAD / 修复提交 `a31cdcd0`。只复核上一轮 AR2/O1 的资源责任方、三个取消点和 sidecar 时序，不审查 AR1 或其它评分语义。

结论：上一轮丢 token、丢网络/子网槽位、close 假称无残留、finally 最终事实没落盘的指定反例已闭合。本轮限定调用链未发现需要阻塞的新增问题。

## 真实调用链与 owner

1. 正常阶段 `manager.py:3560–3567` 在 release 完成或被打断后才通过 `is_issued` 放下 token；被打断记 `release_interrupted`。真实网关 `pkg_index_gateway.py:359–373` 的 finally 无论成功还是取消都从签发表移除 token，并在中断时记累计事实。因此旧的 `releasing=True` 永久残留已消失；取消照常传播，不构造评分结果。
2. grade 的 finally 仍经 `_close_container_scope`（`2705–2709`）先收口容器，再 `_release_supply_resources`。`2194–2211` 只在 record 没有运行中的清理任务时创建独立 task，record.supply_cleanup 与 manager._supply_cleanup_tasks 同时持有；创建、登记、挂 done callback 之间没有 await。调用方经 shield 等待，调用方取消不能取消该 task；重复 gc/close 复用已有任务。
3. `_supply_cleanup`（`2227–2275`）按真实网关查询结果清 token，按 teardown 成功清网络句柄，之后才标 `supply_released`。失败时网络/槽位句柄留存；完成的 task 从 manager 集合摘除。`gc:2309–2322` 现在会处理已删容器的未完成供应资源；`close:1661–1685` 复用/等待清理并把仍存的资源列进 supply_open 与 cleanup_failures。各步骤沿现有 timeout；这里不把 `_supply_cleanup_bound` 说成整个 gc/close 扫描的统一总预算。
4. `_retire:2659–2664` 排除仍持 token 或网络句柄的记录，保证其不会因完成历史裁剪丢失。作者聚焦用例实际验证：history_limit=1 时失败记录仍在，之后 close 可继续清理。删除序号及累计数仍按容器删除确认产生；供应未完成与容器已删除是两个事实。
5. O1 在 `_supply_cleanup:2273–2275` 的最终事实之后同步调用 `_refresh_supply_sidecar:2277–2298`，选择已落盘的正常/infra 或 cancelled 引用，只替换同一 JSON 的 supply 字段，通过临时文件 + os.replace 写回。grade finally 之前的 sidecar 先给 pending 状态，后台清理结束后补最终状态；调用方已取消时允许这一步晚于该调用方返回。

## 实际验证

作者新增聚焦 CPU 测试 `tests/grading/test_supply_cleanup_ownership.py`：**9 passed in 2.63s**。包括拆网不应答时保留句柄并报告 supply_open、恢复后重复 close 清零、历史裁剪保留尚未收齐的记录。

独立探针 `tracer_cleanup_owner_probe.py`：真实 manager + 真实 PackageIndexGateway，沿用上轮作者旧 SupplyDocker 替身；只人工延迟一条在途 task 及 relay disconnect，以确定性进入 await 窗口。不创建 HTTP 服务、不运行 Docker、不使用网络。完整结果在 `tracer_cleanup_owner_probe.json`。

| 案例 | 调用方结果 | 调用方返回时仍在运行的清理 task | close 后 token / 网络 / 槽位 | 最终 token_release |
| --- | --- | --- | --- | --- |
| 正常评分 | resolved / reward 1 | 0 | 0 / 0 / 0 | released |
| 安装超时 | failed_to_grade / reward None | 0 | 0 / 0 / 0 | released |
| 签发 token 前失败 | failed_to_grade / reward None | 0 | 0 / 0 / 0 | not_issued |
| 正常 release 中取消 | CancelledError | 0 | 0 / 0 / 0 | release_interrupted |
| 安装超时后 cleanup release 中取消 | CancelledError | 1 | 0 / 0 / 0 | released_incomplete |
| cleanup 拆网中取消 | CancelledError | 1 | 0 / 0 / 0 | released |

六案都断言：close 后 active cleanup task=0、supply_open=[]、supply_released=true；最终 sidecar.supply 等于 record.supply。每枚 token 的 release 只调用一次、每个 attempt 的 teardown 只调用一次，close 没有重新启动第二个仍在运行的清理任务。release 没收齐在途 task 的案例如实保留 complete=false / inflight_unfinished=1 和 supply_token_release_incomplete，不能把资源句柄清零理解成在途统计完整。

## 正式启用边界与停止条件

`bringup.py:1474` 仍只注入 eval_log_dir / sandbox_profile，未注入 supply。Brief §15.5 明确 supply_open 尚待接入 bringup 关停判定。因此本结论是 manager 组件取消/清理与 sidecar 的验收，不能表述为正式供应作业已验收或启用。无新增 production 已暴露 finding。

仅读源码、Brief 和上一轮证据，运行上述窄 CPU 检查；未改生产/维护测试/共享文档，未使用 Docker、远端或公网，未覆盖上一轮证据。已达到三个取消点与正控的停止条件，不扩展故障矩阵。
