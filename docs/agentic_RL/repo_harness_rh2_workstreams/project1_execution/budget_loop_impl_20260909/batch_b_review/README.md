# 预算闭环批 B：Codex 聚焦审查

日期：2026-09-09。基线：批 A 提交 `6bb5ffe4`；对象为其上的未提交批 B（6 个源文件、9 个维护测试文件、1 个兼容实验夹具）。范围按 [Owner Brief v2.2 的批 B](../README.md#批-bi03-统一期限排队重算到期取消的资源收口与原因传递) 第 1–7 条。没有审查或修改 B 线的环境探针，也不将预算批 C/D 当作已经实施。

**结论：暂不建议提交或标记批 B 审查通过。两项 P1 需要在本批补齐：准备阶段的期限覆盖、物化取消时的真实资源回收。** 绝对期限下传、模型额度排队重算、驱动 Docker 通道的取消回收方向成立；现有测试全过，但遗漏了下表中的真实调用接缝。

| 编号 | 级别与分期 | 结论 |
|---|---|---|
| R1 | P1，本批修 | HEAD 读取和 baseline census 在期限包装之外，过墙后仍可一直占用容器和执行槽 |
| R2a/R2b | 合并为一项 P1，本批修 | 物化实际 Docker runner 未 kill/wait；建网和已登记的 relay 接入被取消后均漏回收网络/地址池槽位 |
| R3 | P2，建议同批窄修，不另加阻塞轮 | 引导阶段的启动事实和向下取整的局部期限会误导失败归因；最终仍丢弃样本 |

## 1. R1：准备阶段只在结束后查时间，没有全程受期限约束

**行为与位置。** `generate.py:2712` 的 `_await_within_episode_deadline` 只包住 `_materialize_rollout_sandbox`。返回以后，`:2727` 的 `git rev-parse HEAD` 与 `:2736` 的 `generate_baseline_manifest` 都在包装外；到 `:2756` 才重新检查剩余时间。`baseline_census.py:165` 实际 await 容器内的扫描命令；`RolloutContainerWorkspace.run_bash`（`generate.py:2270`）使用默认 Docker runner，没有另一个能覆盖这段的 episode timeout。

**违反的决定。** 准备时间计入宽墙钟，且到点强制取消。结束后算出剩余时间为负，不能替代扫描尚未返回时的停止动作。

**独立证据。** 主审 [orchestrator_probe.py](orchestrator_probe.py) 的第一案进入真实 formal `generate`，完成物化，只把真实 census await 替换成阻塞 IO。预算设为 1 秒；等到 audit 的实际单调钟期限之后，观察到：执行仍 pending、census 未取消、容器删除次数 0、`hit_by=none`。由探针主动取消整个执行后，才删除容器。见 [实际输出](orchestrator_result.jsonl)。这不是仅调用私有计时 helper 的反例。

**影响与可达性。** `production_reachable`：正式链每个 attempt 都经过这段；慢磁盘、Docker 无响应或大目录扫描即可触发，不要求未来功能或特殊模型动作。准备阶段最坏可无限等待，违背墙钟防止无限占资源的用途。发生频率未实测；短 CPU 探针不冒充真实 Docker 挂起记录。扫描最终返回时仍会被丢弃，但这不能解决返回前的资源占用。

**最小修法与验收。** 将 HEAD/census 的异步工作一并纳入同一期限，保留已取得 sandbox 的清理所有权；不新建第二套 watchdog。新回归应从 formal 入口让扫描实际进入等待，过墙后自动取消、不启动 CC、记录 hard wall，并自行清理，无需 owner 再取消。不得只把测试时钟跳到扫描结束之后。完成即可关闭 R1，不要求本批重构 census 算法或做吞吐优化。

## 2. R2：取消了阶段 task，不等于已经回收它的资源

### R2a：改动的子进程函数不是物化使用的那条

`generate.py:155,2425` 导入并默认采用 **`grading.manager.run_docker`**；生产 Bringup 构造器没有替换它。该函数（`grading/manager.py:95–110`）只等待 `proc.communicate()`，取消时没有 kill/wait。批 B 修改的 `docker_sandbox._run` 用于 **Claude Code 驱动**，这部分接线正确，但不覆盖物化的 inspect、建网、docker run 与 exec。

主审回读并重跑 [production_resource_probe.py](production_resource_probe.py)，分别调用两条真实 runner，只替换底层 subprocess：

| 被取消的真实函数 | `kill` 次数 | `wait` 次数 |
|---|---:|---:|
| 物化默认 `manager.run_docker` | **0** | **0** |
| 驱动 `docker_sandbox._run` | 1 | 1 |

因此 `generate.py:4172` 注释“宿主 CLI 已被 `_run` 杀掉”在物化链不成立。之后按名字删除容器也不等于回收先前的宿主 CLI。**应把批 D 中共享 `run_docker` 的取消回收小改动提前到 B**；它已经是 B 新增取消路径的依赖，无须把整个 grader 停止协议一起提前。

### R2b：网络创建与 relay 接入都绕过取消清理

`generate.py:4158` 调用 `_create_attempt_network`，位置在新增的两个取消保护块之前。底层 `sandbox_profile.py:745` 先从地址池占槽，然后 await `network create`；创建成功后，`generate.py:4379` 已登记网络，再 await relay connect。任一点取消，都没有走 attempt 的网络 teardown。外层还没拿到 sandbox，最终清理也找不到完整句柄。

从真实 formal 入口，仅让 Docker IO 在操作已生效、响应未返回时阻塞，主审复现了两案：

| 到点位置 | 最终样本 | 网络残留 | 槽位占用 | 已登记网络 | cleanup 失败记录 |
|---|---|---:|---:|---:|---:|
| `network create` | ABORTED / hard wall | **1** | **1** | 0 | **0** |
| relay `network connect` | ABORTED / hard wall | **1** | **1** | **1** | **0** |

两案都还记录 `cleanup_completed`，容器尚未开始创建。完整结果见 [production_resource_result.json](production_resource_result.json)。**这比作者所说的“私网创建途中可能残留”更宽：已经登记的网络也会漏清。**

探针随后执行真实 shutdown 的 `egress_runtime` 步骤，确认 run label 扫描确实能删除 daemon 里的网络。但它只在关停时执行，且不处理活进程中的 pool/subnet；运行中重复超时仍会耗用有限槽位。这里不是要求进程退出时维护一个已经无用的内存池，而是不能把“整个 run 结束时会扫”当作“单次失败已经释放资源”。

**不变量、影响与可达性。** R2a/R2b 都是 `production_reachable`，当前正式 profile 的必经路径。B 将期限主动取消接入日常失败收口，却只补了部分 owner；真实频率未知，但不依赖假想功能。结果是进程/网络资源残留、后续 attempt 受共享资源耗尽影响，且网络残留没有体现在该 attempt 的 cleanup 错误里。登记残余风险不能替代本批已经承诺的到期回收。

**最小修法与验收。** 在真实 `manager.run_docker` 回收宿主 CLI；在知道网络名和已预留 subnet 的现有获取函数内处理取消；已登记的 connect 路径复用现有 teardown。创建结果未确认也要按预选标识有界收口，确认删除/不存在后才能归还槽位；清理失败应明确留痕，遵守既有失败处置，不盲目归还仍可能被占用的地址。无须新建资源登记平台或改写关停链。

回归覆盖至少三个位置：创建网络中、接入 relay 中、docker run 中。通过真实入口与真实 runner/helper，只替换外部 IO；检查取消传播、kill/wait、网络/登记/槽位释放及失败留痕。不能再仅验证 `docker_sandbox._run`，也不能调用全 run shutdown 后才宣布 attempt 清理成功。

## 3. R3：引导事实与局部整数期限的诊断缺口（P2）

这部分最终仍丢弃样本，未发现因此让 hard wall 样本入训，不按训练语义 P1 处理；但它会干扰本轮新增观测用途，建议与窄修一起整理。

1. **真正的引导取消没有 `launched=False`。** `bringup.py:375–390` 仅在主动执行 `budget_exhausted()` 时回填，安装 await 被外层期限直接取消时 dict 仍空。真实 driver 探针得到 `harness_launched=None`、`hit_by=harness_outer`，随后 drain/finish 各执行一次，以 `no_capture_records` 结束；CC 实际尚未启动。现有 `_BootstrapStarvedDriver` 测试自己写入 False，绕开了这个接缝。
2. **`launched=True` 又写得过早。** `bringup.py:420` 在调用 vendored `ClaudeCodeHarness.run` 之前就写 True；但该方法还要 ensure user、write config，之后才进入 spawn。因此“调用了 harness.run”不能称为“CC 已启动”。保持“尚未尝试启动 / 已确认启动 / 结果未知”的事实含义即可，不必为这个字段建立新状态机；没有确认证据时可留 unknown，不能据 False 推导绝无活进程。
3. **取整制造提前结束并改判引导失败。** 驱动根据收到的整数秒重建局部 deadline，然后 `bounded()` 再向下取整。主审可控时钟案中：预算 600 秒、安装花 0.3 秒，chown 被设为 599 秒；到点时仍剩 0.7 秒，`except SandboxExecError` 因 `remaining()>0` 抛 `harness_bootstrap_failed`，没有识别为预算限制。见 `orchestrator_result.jsonl` 末案。应让可取消引导服从实际绝对期限，保持自有操作 timeout 与 episode 到点的区别；不要仅根据异常发生时“刚好过墙”猜来源。

窄修验收只需真实 driver 在安装/写配置尚未启动 CC 时被外层取消的路径，以及带小数余量的操作超时。不要仅重复人工写 launch facts 的替身测试。

若精确定位 spawn 必须复制上游启动流程，首版可以保留 unknown，并把“进入上游 run”与“已确认启动”分开表述；只在已知尚未尝试启动时跳过装配。不为这个观测字段再造一套 CLI 生命周期。

## 4. 已验证的正确部分与不扩大的范围

- **期限下传与排队重算有效。** registry 接收显式 deadline，proxy 在额度等待和发送期间使用剩余时间；新测试验证真实 `proxy.call` 的原因保留、发送超时和普通 attempt timeout 的区别。跨线程新 event loop 的独立探针读取同一个绝对期限，没有重新起表。
- **额度取消未发现泄漏。** 独立探针覆盖取消先到/获取先完成各 25 案，额度均归还；客户端取消保留 `CancelledError` 与 `client_cancelled` poison。详见 [queue_deadline_result.jsonl](queue_deadline_result.jsonl)。这不表示任意多次取消或真实多进程已经穷举。
- **结束后的评分、清理不被补造为 hard wall。** 现有定向测试覆盖 harness 已返回后时间越界仍按正常结果处理；本轮不推翻这一已定语义。
- **非阻塞观测问题**：排队被外层取消时 `_note_queue_wait` 尚未运行，已等约 0.017 秒却记 0；新 `queue_wait_seconds` 表在 audit ACK 后也未移除。可在已有取消/ACK 边界补齐记录和释放，不必新增指标平台。不会阻塞 R1/R2 收口。
- **只记录证据边界，不新增生产 P1**：人工让安装取消 handler 抛 Fatal，确实会被 `_settle_cancelled_stage` 吸收为次生记录；但本轮未找到已追踪生产 handler 的天然触发来源，不将这个注入案写成真实生产故障。旧 ACTIVE/版本恢复等待耗尽期限的原因码仍有盲点，B 没有修改这两条；同样留作后续原因整理，不借此扩审。
- **C 的停止顺序可继续按计划实施。** “先终止容器内 CC 再 drain”是明确留给 C 的已知工作；本轮只确认宿主 CLI 取消不能代表 CC 已死，不要求把整批 C 搬进 B。D 的处置注入仍须先于/同批于 cap 启用。

## 5. 实际验证、交接与停止条件

主审在 integration miles 基座实际运行本批 9 个维护测试文件：**181 passed in 5.16s**；16 个变更 Python 文件 ruff 通过；`git diff --check` 通过。作者所报全量 **1812 passed / 310 skipped** 本轮未再次运行。

```bash
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters/test_budget_deadline.py tests/adapters/test_async_worker.py \
  tests/adapters/test_capture_registry_fa.py tests/adapters/test_f2_2_capability.py \
  tests/adapters/test_slime_generate.py tests/adapters_miles/test_b2_mask_chain.py \
  tests/adapters_miles/test_batch_a_failure_routing.py \
  tests/adapters_miles/test_f1_e2e_identity_chain.py tests/adapters_miles/test_w1a_formal_chain.py
```

主审审读并独立运行三份 CPU 探针（在 `rh2/` 使用 `uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_b_review/<脚本名>`）：[orchestrator_probe.py](orchestrator_probe.py)、[production_resource_probe.py](production_resource_probe.py)、[queue_deadline_probe.py](queue_deadline_probe.py)。均退出 0；它们有的断言当前错误确实复现，退出 0 **不表示批 B 无问题**。没有调用真实 Docker、CC、模型 API 或 GPU。

独立角色分别核对了 [生产路径与所有权](production_tracer.md)、[反证、额度取消与分期](falsifier.md)，并交叉核对 R1/R2。主审自行检查源码和探针、重跑关键证据、去重并裁定，没有按角色投票。摘要与命令范围见 [review_snapshot.json](review_snapshot.json)，测试结果见 [review_tests.txt](review_tests.txt)、[review_ruff.txt](review_ruff.txt)。

适用维度：A/B/D/E/F/G/H/I/L/M（取消、资源归属、拒绝分布、真实接线、测试接缝、既有决定、原因与活性）；J/K 限于两个闭环的最小改动与减少虚假观测；C 没有新生产挡板，N 无依赖变更。未扩展到算法、SWE 数据清洗或全链总审计。

**停止条件：** Claude 修 R1/R2 并补真实接缝回归后，只复核这两项及必要回归即可结束本批；R3 和 §4 非阻塞项明确回应即可，不因还能构造理论反例继续加轮。共享 `manager.run_docker` 的取消回收需提前到 B，其余 D 的处置注入可以继续准备。§6 六项仍无新增 owner 批准，本轮不把它们算作遗漏。审查只新增工件、更新 Brief 与 `infra.md` 状态，没有修改业务代码、维护测试、提交或推送。
