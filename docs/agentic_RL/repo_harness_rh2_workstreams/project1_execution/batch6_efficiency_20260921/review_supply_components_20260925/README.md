# 网络供应组件与三项链路修复复核

2026-09-25，Codex。复核 `2f5e63d9`、`69ea494f`、`9c59a1f6`、`b169c10e`、`9d741bd4`；HEAD 为 `9d741bd47faf54a343e65d4377d342d9a6e0ccc4`。

**结论：统计尾项、rollout 可信命令通道、共用溢出 400 可以收口；控制字符路径的目标问题已修复，另登记一项非阻塞收紧。网络组件的正常访问与隔离正控通过，但还有两个生命周期尾项，应在接入正式 attempt / grader 前补齐。没有新 T0，也不需要重开 1A+2A。**

网关、供应 relay、撤网核对函数目前在 `rh2/src` 没有正式调用方。下述网络问题是组件反例，不能说成当前训练已联网或已发生泄漏。grader 两段 exec、失败归因、正式作业启用和目标机成本仍未验收。

本轮复核期间 `sandbox_profile.py` 出现另一项 G1 tmpfs 未提交改动，不纳入本报告。已逐函数比对：本轮涉及的 relay 构造、启动、撤网及 DockerRunner 与 `69ea494f` 逐字相同，证据为 [reviewed_source_scope.json](reviewed_source_scope.json)。维护测试使用共享工作区，含既有 B 在制品，不冒称干净树全库复验。

## 1. NG1 / P2：释放 token 尚未收齐在途请求与最终统计

**位置：** `rh2/src/repoharness2/adapters/slime/pkg_index_gateway.py:314–340, 566–637`，尤其 `release()` 与 `_file()` 的状态持有。

**当前行为与反例：** `release()` 从 `_tokens` 删除记录，复制统计后立即返回；已经进入 `_file()` 的请求仍持有原 `_TokenState`，其状态保持 active。真实 aiohttp 网关配 localhost 上游，先发 5 字节、暂停，再 release：新请求正确返回 404，`active_tokens=0`，但旧请求随后完整收到剩余 5 字节。release 返回的摘要为 `bytes=0`，之后落盘的该文件请求为 `served_file / bytes=10`。

`withdraw()` 的正控也核过：后续请求 403，在下一个上游 chunk 到达时断流，客户端报 `ClientPayloadError`；上游暂停时，撤销 200 ms 后连接仍未结束。这里的 200 ms 只用于证明没有立即主动关闭，不是正式时限要求。

**违反的边界与影响：** Brief §4.4 / §10 要在 attempt 结束释放 token 和签发表，并将统计摘要写入 attempt 事实。目前“拒绝新请求”与“请求已经结束、最终统计已收齐”是不同事实；不能将 `release()` 返回或 token 数为零当作后两者。否则在途请求继续占用网关连接，终态统计可能缺文件字节或错误。release 的现有 docstring 只明确承诺后续 404，因此本 finding 针对接线所需的终态所有权，不把它扩大成已证的授权绕过。2A 的离线边界仍是宿主 disconnect + inspect，不能由 token 状态替代。

**可达性与分期：** `conditional_future`；当前新组件直接可复现，正式接线尚未发生。A 在接入前解决，不阻塞其它已通过的切片。

**最小修正：** 给每个 token 的在途请求明确同一个 owner：结束 attempt 时停止新请求、终止或有界收齐已接纳请求，再给终态摘要、释放登记。可以扩充现有控制面，也可以由接线 owner 保证顺序；不必新增供应调度平台。若先返回的是快照，应明确它不完整，不能作为最终统计写出。仅让调用方顺序执行 `withdraw(); release()` 还不足以证明已经收齐，因为 withdraw 现在也不等待结束。

**验收：** 至少覆盖下载中途 release、上游停顿时撤销、尚在等待上游响应的请求，以及正常完整下载。终态完成后不得再按原 active 权限传输，统计收齐或显式标未收齐；后续 403/404 与正常供包正控保持。探针见 [tracer_lifecycle_probe.py](tracer_lifecycle_probe.py) / [结果](tracer_lifecycle_probe.json)；主审独立重跑见 [main_replay_lifecycle_probe.json](main_replay_lifecycle_probe.json)。

## 2. NG2 / P2：relay 启动取消绕过自清理

**位置：** `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` 的 `_start_relay_container`（`69ea494f` 第 1041 行起；本轮 G1 工作树中第 1050 行起）。

**当前行为与反例：** `_fail()` 只由明确的“不就绪 / inspect 失败 / digest 不符”分支调用。Docker run 成功、等待 readiness 时取消，直接抛 `CancelledError`，既未返回 handle，也没有 rm 或残留事实。假 DockerRunner 正反控分别得到 `run → exec`（取消、容器存活）和 `run → exec → rm`（不就绪、已清理）。

主审又在本机真实 Docker 中复现：仅延迟 readiness 那次调用，容器与启动参数均为真实；取消后 `inspect .State.Running=true`，helper 没有执行 rm。探针 finally 已删除自己的随机命名容器并确认无残留，见 [main_relay_cancel_docker.py](main_relay_cancel_docker.py) / [结果](main_relay_cancel_docker.json)。

**违反的边界与影响：** 启动者在 handle 交出前仍拥有容器，取消不能让资源失去直接 owner。将“任一步失败自清理”落实到取消和异常路径即可。普通显式失败分支的清理已通过，不需要另造关停协议。

**可达性与分期：** 新供应 relay 为 `conditional_future`；共用 helper 从旧 egress 实现继承此缺口，不是本次抽取导致的正式路径新回归。旧 bringup 在 await 返回前尚未获得 handle，不能仅依靠成功后设置的字段清理；run label 的最终兜底也不等于启动函数已经收口。A 在供应接线前修，沿用原有取消传播和残留归属。

**验收：** run 已创建但 handle 未交出时，在 readiness / inspect 等待中取消，仍传播原取消并尝试按已知名字回收；回收失败留明确容器名和 run 归属，不吞首因。正常启动、原失败码与原失败清理正控不变。无需增加自动重试、关闭网络检查或要求用户重新决定。

## 3. PC1 / P3：控制字符降级仍可能遮住另一项契约错误

**位置：** `rh2/src/repoharness2/adapters/slime/patch_exporter.py:206–222`。

目标反例已经修复：真实本地文件系统的普通文件照常导出，含 `0x01` 的普通文件与含 DEL 的软链均抛 `unsupported_object_in_patch / unsupported_path_name`；维护测试另走真实 fa_formal 编排，确认 unsafe 交付、不评分。

剩余问题是 catch 任意 `ValidationError` 后重新扫描整段 census，只要任何一行路径不合法便降级。合成输入“第一行 content_digest 不合法、后续另一行含控制字符”时，原异常的 loc 是 `content_digest`，仍被转换成 unsafe；坏 mode 与坏路径并存同样如此。单独坏摘要保持 `ValidationError`。

**可达性为 `test_only`：** 尚未证明当前可信 census 会产生这些错误组合；不称生产停训或安全问题，不阻塞已修目标或网络实施。但“我方契约矛盾始终 fatal”的承诺比代码强，违背了只降级已归因候选路径错误的窄边界。

建议 A 随下次修改该处收紧：从捕获异常的实际条目 input / loc 确认路径规则错误，而非看全文是否碰巧另有坏路径。不要解析错误文案，不必改 B 正在编辑的 parser。验收只需补“坏摘要 + 另一条坏路径仍抛原错误”的反控，已有真实坏路径正控保持；不新增状态、重试或准入规则。证据见 [falsifier_path_boundaries.py](falsifier_path_boundaries.py)、[主审复跑结果](main_replay_path_boundaries.json)。

## 4. 可以收口的部分

| 对象 | 独立核对与裁定 |
| --- | --- |
| `2f5e63d9` / OBS-1、COMPAT-1 | 重跑前轮真实 miles 入口 → prepared 身份 → fa_formal → audit writer → loader → report 的五场景，并补本轮断言。shutdown 不再生成 delivery；一条新审计与另一 attempt 的旧审计显示 1/2、旧记录未知 1；评分数、eval 分流、物理 attempt 去重、旧交付回退保持。accepted / fixed。 |
| `b169c10e` / rollout root 通道 | `/usr/bin/env -i` 与 `/bin/bash --noprofile --norc` 均用绝对路径，真实 workspace 入口已覆盖；本机 Docker 的假 find/pkill 正反控通过，另一本机 UID 探针验证 BASH_ENV 也被清除。仅接受本次 rollout 通道修复，不把 grader 或所有 root 调用一并判为安全。grader root PATH 仍待 A/B 交接。 |
| `9d741bd4` / 溢出 400 | 不装 capture wire 的真实 vendored HTTP app：溢出 400、引擎零调用、短请求正常、无窗口不拒绝、重复安装无叠层。另跑既有 capture wire 窗口测试，未改变真实采样 / pending 语义。accepted / fixed。B 是否采用该入口仍属交接。 |
| `69ea494f` / 正常供应与撤网 | per-token fid、项目封禁与例外、不同 token 不共用文件 ID、页面重建、真实 pip 下载均通过。两个真实 Docker 用例确认只通包源 relay、无模型端口、直连外网不通，以及撤网后新请求失败；inspect 非空或未知均不返回 ok。NG1/NG2 补齐前不称组件生命周期收口。 |

评分运输证据：[main_probe_audit_grading.py](main_probe_audit_grading.py) / [JSON](main_probe_audit_grading.json)。其中一小时事件窗、8 卡配置和评分分段时长均为算术夹具，不能拿作吞吐测量。

## 5. 验证、复杂度与停止条件

在 `rh2/` 运行：

```sh
RH2_MILES_PATH=../reference/miles-rh2-integration PIP_EXTRA_INDEX_URL='' .venv/bin/pytest -q \
  tests/adapters/test_pkg_index_gateway.py tests/adapters/test_supply_relay.py \
  tests/adapters/test_patch_export_path_names.py tests/adapters/test_trusted_root_exec.py \
  tests/adapters/test_prompt_overflow.py tests/adapters_miles/test_e5_run_report.py \
  tests/adapters_miles/test_run_report.py tests/adapters_miles/test_i21_eval_run_report.py \
  tests/adapters_miles/test_run_report_real_emitters.py
PYTHONPATH=src .venv/bin/pytest -q tests/adapters/test_cc_context_window.py
```

**74 + 4 passed，无 skip**。74 项内含三个标记为 Docker 的维护用例；控制字符编排用例的 census 是替身，不将它冒充真实 Docker。另有主审一次真实 Docker relay 取消探针、localhost HTTP 生命周期探针、真实本地文件路径探针及五次 CPU 审计运输。相关文件与探针 ruff 通过。提交 diff whitespace 检查仅提示一处测试文件末尾空行，不作为 finding 或硬门。

未重跑全库 / 双 lane、真实公网 PyPI/devpi、远端、真实 CC/GPU 或 grader 两段 exec；没有修改生产代码、测试 oracle、B 在制品、部署或运行配置，没有提交 / push 或跨任务发消息。

按审查标准 §10.4，本轮新 token owner 与跨进程 relay 边界用一对既有独立代理执行 Production Tracer 与 Falsifier/Simplifier，主审核对源码并重跑关键反例；没有为已收口的纯统计部分再展开全链审计。

A/D/E/G/L/M 的证据集中在 NG1/NG2 与实际入口测试；B/C：控制字符仍是既有 unsafe 整组拒绝，不产生 reward 0，未新增准入闸，网络未启用；F/H：1A+2A 不变，摘要 / 400 复用既有事实；J/K：无需新平台、重复 logger 或重试系统，收紧一处 catch 即可；N：本机 pip 与 Docker 证据不代替目标机 devpi/uv 验收，旧审计回退保持；I：两项网络尾项在接线前处理，PC1 非阻塞，其余收口。

**下一步：** NG1/NG2 可先在网关与 relay owner 内修，不依赖 B 的 `manager.py` 等文件。共享文件按具体文件/函数交接即可，不必等 B 全部工作完成；独立 worktree 能避免互相覆盖，但不能替代合入最新 B 改动后的接缝验收。本报告不新开 worktree，也未向 B 派发任务。

**停止条件：** 修后只复核 NG1/NG2 的反例与正常正控；如顺手修 PC1，再加该组合反控。之后进入既定的 grader 两段 exec / rollout 注入验收，不继续因本轮已通过项扩展闸门或重开网络政策。正式启用仍由作业方案承接。
