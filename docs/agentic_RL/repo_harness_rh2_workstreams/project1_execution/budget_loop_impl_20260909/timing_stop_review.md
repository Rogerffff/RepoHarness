# 批 B/C/D 的计时与停止窄反证

日期：2026-09-09。角色：Falsifier / Simplifier。对象：本目录 `README.md` 的批 B/C/D；不评价 §6 四码的完整分类。审查期间工作树 HEAD 为 `297f1f59`，已不同于 Brief 顶部的 `2a533b1f + 未提交 I01`。没有修改业务源码、测试 oracle 或执行提交，没有启动 Docker/GPU。

## 主结论

批 B/C/D 的方向可以沿用，但不能原样称为“全部只是已批内容的实施”。**cap 先发生便覆盖后续 hard wall、最后 KEEP_FULL** 是一个遗漏的 T0：它改变了已经确认的“墙钟触发整组不训练”。最小处理是删掉这条例外，沿用 hard wall 的既有处置，不需要新增用户决策。

其余主要是执行计划还没有闭合的具体接线：准备/引导必须真正受同一期限限制；补期限取消时必须同时补现有资源 owner 的清理；proxy 不能把 deadline 的 typed 原因改写成更新窗口错误；cap 事实不能覆盖真实失败；cap producer 与 disposition 注入必须形成同一个可运行版本。它们不分别升级成新状态机或新的决策包。

审查维度：A/B/D/E/F/G/H/I/L/N 适用（并发、训练分布、资源所有权、测试、既有定案、生产入口、事实来源、分批、活性、CLI/HTTP 行为）。C 没有新增挡板建议；J/K 仅核最小改动与避免新 owner；M 复用计划已有 audit，不要求新监控平台。

## 1. cap 压过 hard wall 改变了已批训练语义

- **计划行为**：`README.md:66` 规定 cap 命中后挂到墙钟仍取 `max_turns_exhausted`，并在 `:129` 归 T1。配合 `:73` 的 KEEP_FULL 注入，完整可信记录将留在组内训练。
- **不变量与证据**：第一组已确认文本 `../batch1_budget_20260908/README.md:5,79-94` 明确墙钟是强制保护，触发整组不训练；停止宽限只用于收口，不给另一段自主行动时间。
- **最小反例**：episode deadline=600s；cap 在 595s 命中；CC 未退出；到 600s 仍有执行，按 30s grace 方案到 625s 才强制停止。计划随后可按 cap KEEP；已批方案要求这次 hard wall 不训练。
- **影响与分期**：`conditional_future`，依赖批 C 待实施规则；是本次计划的设计阻塞项，不声称当前代码 P0。它会保留原定应丢弃的慢执行，改变组成员分布。频率未知，但在预算诊断任务里是直接可触发条件。
- **最小修订**：记录 cap 和 wall 两个事实；凡 episode 强制期限在执行停止前到达，训练处置沿用 hard wall DROP。只有在 deadline 前已经完成 episode 停止、进入独立 cleanup/grading 时，不把后续清理耗时算成 episode 超时。grace 的有效等待须服从 episode deadline，不能冻结该 deadline。若仍要 cap 优先，必须作为推翻旧决定的 T0 明说后请 owner 决定。
- **验收**：可控时钟覆盖 cap→wall、wall→cap、cap→正常退出，第一种不能因 cap 先发生而 KEEP；无须为此构造新终态平台。

## 2. 入口记 deadline 尚未覆盖准备、CLI 引导与取消清理

- **计划行为**：`README.md:49-55` 给入口设 deadline、harness 启动前传 `floor(remaining)`，但列出的接线没有让整个 materialize/baseline/driver bootstrap 受该绝对期限约束。
- **生产证据**：`generate.py:2668` 直接等待物化；`:2690-2703` 执行 baseline census。`bringup.py:350-382` 在收到 `time_budget_sec` 后，先安装 CLI，再执行最多 900s 的 useradd/chown，才调用 vendored harness。`slime/agent/harness/common.py:97-104` 还有 ensure-user/write-config；`slime/agent/sandbox.py:111-124` 还有 launcher 写入/启动，之后 `:71-77` 才从相对 budget 开始轮询。
- **不变量/影响**：资源从占用起必须有实际强制保护。若 materialize 永久挂住，当前方案没有机会到“启动前剩余≤0”分支；如果启动前剩 20s，但 driver bootstrap 再花 60s，CC 仍可能在 deadline 后才启动。只修 model-call 队列不能解决没有模型请求时的占用。
- **取消所有权必须同批补**：`generate.py:3914` 启动容器；`:3926-4053` 的物化清理只捕获 `Exception`，没有接住 `CancelledError`；物化未返回时外层 `sandbox` 仍为 None，`:3689-3691` 不会清该容器。`docker_sandbox.py:27-40` 是 CLI 引导和轮询的实际通道，只回收自身 `TimeoutError`，外层取消会跳过 kill/wait。批 D 只改 `grading.manager.run_docker` 覆盖不到它。
- **可达性与分期**：准备/引导等待为 `production_reachable`；由新统一 deadline 主动取消物化产生的清理回归为 `conditional_future`，会在本批启用。均在批 B 启用前补齐；不是要求重做整个 shutdown 系统。
- **最小修订**：用同一绝对 deadline 有界覆盖当前执行阶段，保留 grading/stop/cleanup 的独立有界预算；在现有 materialize owner 上接住取消并清理它已获得的容器/网络；给实际 `DockerSandbox._run` 补取消后的 kill/wait。绝对期限应作为强制权威，vendored 相对整数秒只作兼容参数；明确 `0 < remaining < 1` 时如何处理，不能依赖 `floor` 与 5s 轮询实现精确期限。
- **验收**：物化前/容器已启动后/baseline/CLI 安装与 chown/工具执行中分别挂起；到点不再启动后续工作，能清已获得资源。CLI 取消探针见下方，当前输出 `kill_called=false, wait_called=false`。

## 3. `_send` 新抛 deadline 码仍会被现有 proxy 改写

- **计划行为**：`README.md:53-54` 要求 semaphore 等待到点抛 `UnattributableModelCallError("episode_deadline_exhausted")`，随后按 poison reason 将其识别为 hard wall。
- **生产证据**：`async_worker.py:868-878` 的 `except Exception` 会吸收 `_send` 抛出的该 typed 错误；在 ACTIVE 稳态下 `:919-923` 将其改为 `no_overlapping_update_window`，`:827-829` 最后以改写后的码 poison。普通 `_send` 的 `wait_for` 超时亦进入这条归因分支。
- **不变量/影响**：真实期限耗尽必须保留其发生事实，不伪装成 API/更新窗口故障；否则批 B4 只识别 `episode_deadline_exhausted` 会漏掉本批新加的超时路径。主要影响真实归因与停止分支，不能仅用 pre-send 已有码的单测证明 semaphore/send 路径正确。
- **可达性/分期**：当前通用吸收分支 `production_reachable`；计划的新 semaphore typed 输入为 `conditional_future`。批 B 内闭合。
- **最小修订与验收**：在现有 `_call_inner` 归因入口识别并保留 deadline 事实，不能无条件把所有 TimeoutError 都叫 hard wall。分别测试 semaphore 到点、取得 semaphore 后剩余重算、send 到点、普通 attempt timeout，以及真实更新窗口异常；需调用 `proxy.call`，只测 `_send` 不够。以下探针已证明仅按 README 所写从 `_send` 抛码会得到旧错误。

## 4. cap 宽限与在飞请求：预算事实只是停止触发，不是完整性的豁免

`README.md:62` 的 cap 拒绝自身不 poison、不 revoke，可以避免把 **第 N+1 个未进入采样的拒绝** 错当 capture 故障。但它不能保证已经接纳的 N 个请求全部交付完毕。

源码证据：`slime/agent/adapters/common.py:325-344` 没有每会话串行锁，已接纳请求会分别等待生成；`:359-374` 只有响应 flush 成功才可记录该轮。若 cap 命中时其它请求仍在飞，CC 自行退出或强杀导致断连，则 `async_worker.py:870-876` 仍会记录失败并 poison `client_cancelled`；`capture_wire.py:591-598` 的 drain 要求 poison clean。这是当前完整性规则的结果，不能为了兑现 cap KEEP 将其清掉。

最小修订：把 `README.md:64` 的“预算事实在场时取消都不是 crash”收窄为**可归因于本次预算停止、且其余事实闭合**；cap 不覆盖真实 poison、capture/tape 缺失、fatal、外层取消或 hard wall。N 表示已接纳请求数，不保证 N 轮都有可训练生成。存在在飞未交付时沿用已经批准的“不完整不能冒充完整截断”，无需为保留它新增恢复机制。

30s 是停止收口的候选实现常量，本身可按 T1 报告；如果这 30s 允许接受新模型工作或重开自主行动，就已超出“收口”的授权。应测试 N 请求在飞时 N+1 被拒、cap 与真实模型错误同到、自然完成与迟到 cap 回调、cap 与外层取消同到。子 agent 的启用尚未定，本条不因此要求现在支持子 agent；若后续启用，它同样要满足这组并发不变量。

HTTP 断连不需要凭猜测新增另一套 owner：本机回环使用生产 `_RELAY_SCRIPT` 原函数及 `aiohttp(handler_cancellation=True)`，已观察到 handler 被取消，proxy poison=`client_cancelled`。这证明现有通路具备传播能力；它不是“真实 CC 强杀后每个目标 GPU 都已收到 abort”的证据。真实部署的停止/abort 到达验证仍按 Brief §7 已列的作业范围执行。

## 5. 分批的最小一致性要求

批 C 先产生 `present_truncated/max_turns_exhausted`，批 D 后注入 KEEP 的独立可运行窗口会让当前 `governance/admission.py:634-647` 再抛 `DispositionNotInjectedError`。因此可分提交，但 **cap producer 与对应策略注入必须作为同一可运行版本交付/启用**，或者先完成注入再启用 cap producer。不能将“C 已单独可用”作为中间完成口径。

`DispositionPolicy.policy_horizon_truncation` 实际覆盖三种 horizon（`admission.py:138-149,164-173`）；第一组已确认范围只含正常 turn 截断，明确不顺带决定未来 token/context producer。当前 Brief 明说不新增那两个 producer，因此本轮不要求拆公共契约；在计划中注明 KEEP 注入只服务当前 turn 路径，未来 producer 接线时重新确认对应语义，不能从共享槽位反推 owner 已批准。

scope 最终未证实停止仍必须沿用既有 A4 fatal；一次 drain 超时并不自动等于最终无法停止。批 C/D 应明确这一终点，不能用“已记 cleanup_failures”替代原定失败处置。这里不改变已有首因与后续清理事实的分离，也不要求提前设计 I13/I16。

## 验证证据与停止条件

从 `rh2/` 执行：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/timing_stop_probe.py
```

2026-09-09 实测退出码 0，结果：

```json
{
  "deadline_reason": {
    "raised_reason": "no_overlapping_update_window",
    "poison_reason": "no_overlapping_update_window"
  },
  "docker_cli_cancel": {"kill_called": false, "wait_called": false},
  "relay_disconnect": {"handler_cancelled": true, "poison_reason": "client_cancelled"}
}
```

探针是对现有方法的有界反证，第一项仅替换 `_send` 的输入异常，第二项仅替换子进程创建，第三项仅使用本机临时端口。没有执行整个训练链，也没有把这些结果写成真实 Docker/GPU 停止证据。

**停止条件**：主审将上述语义修正与接线验收加入本批计划即可进入实现；修后只复核这些分支及必要回归。未来 horizon 数值、子 agent 能力、真实 GPU abort 到达率继续留在各自已定工作包，不据此扩大全仓审查。
