# 批 B Production Tracer 聚焦审查

结论：**当前取消回收尚未接通生产资源链，应在批 B 修复后收口。** 对应主审 R2 的两个 P1 子点：物化使用的真实 Docker runner 没有取消回收；建网与 relay 接入不在物化取消清理保护内。后者包括**已登记网络**，比 Brief 所列“创建途中”的残余风险更宽。主审 R1 的 baseline 期限遗漏也经本角色独立静态核对，探针入口与断言有效。

基线 `6bb5ffe4`，审查对象是其上未提交批 B；日期 2026-09-09。仅追踪 `generate → materialize → 私网/容器 → Driver` 的 deadline 与取消所有权，读取 Brief 批 B 第 1–7 条、相关 diff、网络 helper 和生产 bringup 接线。未审全链、未运行 Docker/CC/API/GPU，未修改业务源码、维护测试或共享文档。维护测试由主审执行。

## R2a · P1：物化的真实 runner 取消时未回收宿主 CLI

- **行为与不变量**：批 B 第 3 条要求取消阶段先回收所持子进程，再结束。新增保护实际只在 `docker_sandbox._run`；物化仍走 `grading.manager.run_docker`，后者只 `await proc.communicate()`，收到取消直接退出，没有 `kill/wait`。
- **生产可达条件与主链**：`BringupService` 创建 `RolloutOrchestrator` 时未传 `docker`（`bringup.py:1328`）；构造器采用 `docker or run_docker`（`generate.py:2425`），其导入来自 `grading.manager`。期限在 `_await_within_episode_deadline` 到点后取消物化（`generate.py:3647`），可命中镜像 inspect（4084）、network create/connect、docker run（4169）及后续物化 exec。只需某个真实 Docker CLI 尚未完成，不要求自定义 driver 或异常注入。
- **证据与最小反例**：[production_resource_probe.py](production_resource_probe.py) 仅替换 `asyncio.create_subprocess_exec` 为一个停在 `communicate` 的进程替身，分别调用两条真实 runner。结果：`manager.run_docker` 的 `kill=0/wait=0`；`docker_sandbox._run` 为 `kill=1/wait=1`。同时断言 `generate.run_docker is manager.run_docker`、`bringup._sandbox_docker() is manager.run_docker`。相关真实代码：`grading/manager.py:95–110` 对比 `docker_sandbox.py:42–62`。
- **影响**：阶段 task 被取消不证明宿主 CLI 已退出。`generate.py:4172` 的“宿主 CLI 已被 _run 杀掉”在生产物化链不成立；后续按名字 `rm -f` 不会回收先前 CLI 本身。网络变更/起容器仍存在结果未确认窗口，不能仅凭 task 已结束认定资源收口。
- **分期**：runner 的缺陷早已存在，但批 B 新增期限取消把它接入正常终止路径；因此是本批资源闭环的缺口。虽然 Brief 批 D 另列 `manager.run_docker` 的取消改造，这个 helper 同时服务 rollout 物化，不能等 D 才满足批 B 第 3 条。本项不要求提前实现评分停止协议。
- **窄修与验收**：让实际物化 runner 在 `CancelledError` 时 kill 并 await wait，然后传播取消；继续保留物化按名字回收容器/网络的所有权。验收应从生产绑定走到真实 runner，仅替换底层子进程，验证取消传播前已经 kill/wait，且后续资源清理仍执行；不能只验证 `docker_sandbox._run`。

## R2b · P1：私网创建及 relay 接入取消后，无 attempt 级回收

- **行为与不变量**：`generate.py:4158` 的 `await _create_attempt_network(...)` 在 4168 和 4187 两个取消清理保护之前。底层 `create_attempt_network` 在 `sandbox_profile.py:745` 先占子网，再 await 创建；取消路径不释放/记录这个槽位。创建成功后 `generate.py:4379` 已登记网络，4382 的 relay connect 若被取消也没有清理。外层尚未取得 sandbox，最终清理在 `generate.py:3940` 的条件不满足。
- **生产可达条件与主链**：正式 profile 每个 attempt 必经该建网路径。episode 在网络创建或 relay 接入等待响应时到点即可触发；daemon 可以已完成操作，而 CLI 仍在等待返回。本反例不依赖 CC 启动，容器 `run` 调用为 0。
- **证据与最小反例**：同一独立探针从真实 `_formal_chain().orchestrator.generate` 执行完整入口，保留真实网络 helper、deadline 包装和 finally，仅让 Docker IO 替身在创建/接入已生效后等待。两案均返回 `ABORTED`、`hard_wall_timeout`、`episode_deadline_in_materialize`，并记 `cleanup_completed`；但网络仍为 1、占用槽位仍为 1、网络移除次数为 0、`cleanup_failures=0`、隔离队列为空。创建案的登记数为 0；**relay 接入案的登记数已为 1，仍未回收**。
- **label 兜底的真实边界**：探针随后直接执行生产 `BringupService._build_shutdown_steps()` 的 `egress_runtime` 一步，确认它确实可按 run label 删除残留 daemon 网络。该路径只在关停链执行（`bringup.py:1915–1948,1989`），调用 teardown 时没有 pool/subnet（1937）；探针结束时 live pool 仍占 1，接入案 mapping 仍有 1。**这不是要求退出时修复已无用的内存池，而是证明关停兜底不能替代运行中 attempt 的释放。** 运行中重复到期会占用有限子网资源；`EgressSubnetPool.allocate` 耗尽后拒绝后续 attempt（`sandbox_profile.py:720–727`）。
- **影响与分期**：本批新的正常 deadline 终止能持续留下网络及地址池槽位，又没有在该 attempt 的 cleanup 账里显示残留。Brief `README.md:68` 已承认创建中风险，但当前代码还漏掉已登记的 relay 接入阶段；登记残余风险不等于实现了第 3 条的回收要求。本项属于 B，不是 C 的先停止再 drain。
- **窄修与验收**：在资源刚被预留时明确其取消 owner。创建 helper 应持有预选网络名与 subnet，对结果未确认的创建执行有界回收，并在确认网络不存在后释放槽位；relay connect 取消应拆已登记网络。清理失败保留可追踪记录，不能在未知情况下盲目释放。验收至少覆盖创建等待、接入等待、docker run 等待三点，检查网络、登记与槽位都被释放，或失败明确入账；不以全 run 关停作为成功条件。

## 已核对的其它边界

| 阶段 | 当前 owner 与期限 | 本角色判断 |
|---|---|---|
| 入口起表 | `_generate_attempt` 写绝对 deadline；materialize 包装消费 remaining | 方向符合批 B；不扩大到 RH2 入口前 miles 队列 |
| 容器 run 及后续物化 | `_materialize_rollout_sandbox` 捕取消，用预选名字 `_reclaim_after_cancel`，完成后才返回 | 局部保护已存在；真实 CLI 路由仍受 R2a 限制，建网之前受 R2b 限制 |
| baseline HEAD/census | materialize 返回之后、启动前 remaining 检查之前 | 主审 R1 成立；`generate.py:2727,2736` 均在包装外。实际 `baseline_census.py:165` await `workspace.run_bash`，其默认 runner 没有另设超时 |
| CLI 引导与 harness | Driver 使用 `DockerSandbox`；外层 `_await_harness_within_deadline` 取消其 task | 本角色确认此处新增 `_run` kill/wait 确实接在真实 driver 通道；launch facts 与分秒取整问题由主审单列 |
| 容器内 CC 停止 / drain 顺序 | CLI kill 不代表容器内 CC 停止，后续屏障/清理持有容器 | Brief `README.md:68,70–80` 明确递延到 C；不将其当作本批新增 finding |
| 取消时次生 fatal | `_settle_cancelled_stage` 会吸收一般 Exception | 本角色未在已追踪取消 handler 中建立天然 Fatal producer，不将人工抛 Fatal 的反例升级为本轮阻塞项 |

对主审 [orchestrator_probe.py](orchestrator_probe.py) 的 `baseline_wait` 独立审读：它保留真实 generate 入口与完整物化，只在真正 census await 位置替换阻塞 IO；按该 audit 的真实 monotonic deadline 等到过墙，核对同一 task 仍 pending 且 census 未被取消，再外部取消验证 cleanup。这个反例足以证明 R1 的生产入口覆盖缺口；不需要再造一个只调用私有 deadline helper 的测试。本角色未重复运行主审探针。

## 验证与证据绑定

命令在 `rh2/` 执行，exit 0：

```bash
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_b_review/production_resource_probe.py
```

完整输出：[production_resource_probe_result.json](production_resource_probe_result.json)。这是 CPU 替身证据与静态生产调用链核对，不宣称发生过真实 Docker 残留。

本角色核对时的源码 SHA-256：

| 文件（相对 `rh2/src/repoharness2/`） | SHA-256 |
|---|---|
| `adapters/slime/generate.py` | `b74f8882933c1fd08ac4bda39d6f97a1053ea6d4dbd814237cddc13996ab00f3` |
| `adapters/slime/bringup.py` | `15c029bb02186f5d49d3345decbe45dc5469089950877172af6ce227d41a03ec` |
| `adapters/slime/docker_sandbox.py` | `f48632408425e1bbd712cb3f98eaa4f6561f86cd9ed6d25ca10ae3ce1c319bdd` |
| `adapters/slime/sandbox_profile.py` | `93bdded5819a4846ebdfa2b32d0471d0a32f7182591257ecfc2bcbec9e3364a5` |
| `grading/manager.py` | `325747dd58ccd36778ae7b935b8275ba08e8c99894f02a003c27151b51fc1de4` |
