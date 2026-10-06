# AR1 / AR2 / O1 修后聚焦复核

日期：2026-09-28。Codex；基准提交 `a31cdcd0`，父提交 `23f5586d`。范围仅为[上一轮报告](../review_a_remainder_20260928/README.md)的停止条件与本次新增清理任务的生命周期。

## 1. 裁定

**AR1、AR2、O1 均可收口，没有新增阻塞项。** 本轮是组件与本机路径的复核，不代表包供应已经正式接线或启用。

| 项 | 独立检查结果 | 裁定 |
| --- | --- | --- |
| AR1 同名中转误删 | egress 与 supply 的第二次同名启动失败，第一次仍 `Running=true`；本次新建后的 readiness 取消和 Created 失败残留仍会回收 | 通过 |
| AR2 网关释放取消 | 真实 HTTP 下载被截断；release 调用者取消后 token 移除，后续请求 404；计 `tokens_release_interrupted`，不伪造完整摘要 | 通过 |
| AR2 manager 收尾 | 三个取消位置都保持取消传播；可完成的清理最终 token / 网络 / 子网槽位 / 活动清理任务为 0；持续失败明确报 open，恢复后可重试 | 通过 |
| O1 最终事实落盘 | 正常、infra、取消、未签发 token 及收尾失败的诊断状态可区分；最终 sidecar 能回读，与 record 相符 | 通过 |

无需用户新增决策。可按已授权顺序继续 A-B1 供应接线；A-C1 目标机 census 对账、A-C2 代表题与 GPU 验收仍按原计划，不要求为本次复核租机。A-N2 的 B 线交接尚未送达，本轮没有代发消息。

## 2. AR1：归属修复与真实 Docker 对照

`sandbox_profile.py` 的启动入口为每次创建加一次性 `rh2.relay.start_id`。失败/取消清理先读归属，只回收带本次标记的对象；旧的无标记对象、同一 run_id 的另一次启动对象均保留。归属读取失败时不冒险删除，而保留残留证据。

主审复跑上一轮探针的修后副本，只调整预期和输出目录，未回写旧证据：

- [supply + HTTP 对照](main_gateway_relay_probe.py) / [结果](main_gateway_relay_probe.json)：第二次启动 `supply_relay_start_failed`，第一次 inspect 成功且仍为 `true`。
- [默认 egress 对照](main_egress_collision.py) / [结果](main_egress_collision.json)：第二次启动 `egress_relay_start_failed`，第一次仍为 `true`。
- 维护测试同时覆盖两入口 × 有/无旧启动标记、启动 ID 不重复、没有创建对象时不删、确有 Created 对象时回收、readiness 取消回收，含本机真实 Docker 正控。

这满足原 AR1 的关闭条件。新增 label 只提供创建归属，不改变 relay 转发表或正常采样、训练语义；不需要再设计一套中转管理平台。

## 3. AR2 / O1：取消、重试、历史裁剪与落盘

### 实际所有权

- gateway 的 release 在异常/取消退出时移除签发表，并累计“释放被打断”；没有返回终态摘要时，调用方明确记 `release_interrupted`。
- 正常评分阶段在 release 返回或抛出后，查询网关确认 token 是否仍被持有，再放下句柄。
- 供应收尾使用每条 record 的同一个 task；record 和 manager 集合持有引用，调用方经 shield 等待。评分任务取消仍上抛，清理任务继续执行，不会因调用方离开而无人持有。
- token / 网络确认释放后才清句柄；未完成的保留在 record，gc/close 可重试，E4a 不裁剪这些记录。清理任务结束后退出活动集合，没有常驻重试循环。
- 完成收尾后原子更新同一份 diagnostics sidecar。写盘失败进入清理失败记录，不另建日志协议。

### 主审独立结果

[四案主审探针](main_manager_cancel_probe.py)沿用上一轮实际 manager + 实际 gateway 的暂停点，Docker 为既有替身；采用维护测试的 0.3 秒清理配置缩短等待。

| 场景 | 调用方结果 | close 后 token / 网络 / 槽位 | 落盘 token_release / cleanup |
| --- | --- | --- | --- |
| 正常评分 | resolved | 0 / 0 / 0 | released / done |
| 正常 release 时取消 | CancelledError | 0 / 0 / 0 | release_interrupted / done |
| 普通安装超时 | failed_to_grade | 0 / 0 / 0 | released / done |
| 安装超时后的 cleanup release 时取消 | CancelledError | 0 / 0 / 0 | released_incomplete / done |

[JSON](main_manager_cancel_probe.json)与同名日志保留完整输出。`released_incomplete / done` 不是矛盾：资源已收回，但下载请求统计未收齐；`gateway.complete=False` 与清理失败记录仍在，没有把不完整统计说成完整。

独立 Falsifier 的网络 teardown 取消探针由主审再次复跑，[主审副本](main_replay_cleanup.py) / [结果](main_replay_cleanup.json)：

- 正常与取消后恢复：重复 close 不重复拆网，资源与活动任务均归零。
- Docker 拆网持续不应答：前两次 close 均报 `supply_open=1`，落盘 `cleanup=incomplete`，网络/槽位句柄仍在。
- 恢复应答后再次 close：资源归零，落盘改为 `done`；历史清理失败保留，没有抹去曾经失败的事实。

Tracer 另以三个取消点、正常/超时/签发前失败三个正控核对实际 task 复用及 sidecar；见 [Tracer 记录](tracer_review.md)、[独立探针](tracer_cleanup_owner_probe.py)。主审维护测试也覆盖“没有签发 token”和历史上限为 1 时保留未完成资源。

这些取消实验是实际 manager / gateway 配合确定性暂停点的 CPU 探针，不是假称真实 daemon 故障。正常两段安装→断网→测试交接另有本机 Docker 用例通过。

## 4. 保留的适用边界

1. **时间保证是单条清理的，不是全 manager 的统一关停预算。** close 先 gc，逐条等待资源清理，再等待仍在进行的 task；总体耗时随待清理记录数变化。`_supply_cleanup_bound()` 不应被宣传为整个 close 的总时限。本轮原停止条件只要求有限等待、保留 owner 或明确失败，已满足；正式接线时沿既定关停计划验证总时限即可。
2. **shield 依赖事件循环继续运行。** 它防评分任务的取消，不提供进程崩溃恢复；本片没有承诺后者，也不需要为此增加恢复机制。
3. **`supply_open` 尚未接入正式关停消费。** bringup 当前没有供应配置。A-B1 必须同时接入此字段，不能仅依据容器列表为空就认为所有供应资源均已收回；这是既有接线待办，无需新决策。
4. 无远端、公网依赖、真实模型或 GPU 结论。受控供应仍默认关闭，代表题资格仍需在启用两段执行后按计划取得。

以上为边界说明，不新增本轮阻塞项。

## 5. 验证与改动范围

主审从 `rh2/` 执行：

```bash
PIP_EXTRA_INDEX_URL='' .venv/bin/pytest -q \
  tests/adapters/test_pkg_index_gateway.py \
  tests/adapters/test_supply_relay.py \
  tests/grading/test_supply_cleanup_ownership.py \
  tests/grading/test_e4a_history_and_cr1.py \
  tests/grading/test_supply_two_stage_manager.py \
  tests/grading/test_supply_two_stage_docker.py
```

**85 passed in 15.46s，无跳过**，[原始输出](main_pytest.log)。包含本机 Docker 的两入口冲突、Created/readiness 正控及两段评分交接；HTTP 上游是 localhost 夹具。三个源码文件与三个变更测试文件的 ruff 通过。

主审另完成上述 HTTP、两类 relay、四案 manager 与三案拆网探针。子审的 9 / 32 项 CPU 集合与主审重叠，不累计为额外覆盖。不重跑全库、双 lane、216 题或 GPU，不把 Claude 的 1920 项历史结果计为本轮独立验证。

本轮只写新审查工件、更新当前状态入口与 Brief/账本；没有修改生产代码或维护测试，没有提交、push、联系 B 或登录远端。历史审查证据保持原件。探针自有 Docker 容器已清理。

状态 HTML 已实看桌面 1280 像素与窄屏 390 像素：首屏结论正确，无整页横向溢出；证据区默认折叠，键盘可展开/收起；11 个本地链接目标存在。临时预览与自有探针容器已关闭。

**停止条件达成，审查在此结束。** 后续若无新的真实证据，不继续扩展该边界的故障组合。
