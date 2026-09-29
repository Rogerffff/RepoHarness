# #1/#2 启动修复 Brief 复核

2026-09-23，Codex A。对象：[Brief](brief_startup_1_2_20260923.md)；这是写码前设计审查，不是新实现的验收。

**结论：接受 `/rh2/bash_env`、逐 execution 环境注入、宿主增量收集，以及 A/B 两次提交的方向。下列 SR1–SR4 并入 Brief 后可实施，无新用户 T0。** 不需要回到 FIFO，也不需要修改训练算法、评分或增加通用进程管理平台。

## 1. 已确认的基线与边界

- 已逐项读取本地回传的三题 × original/bash_env_v1 六份事实与开发检查日志。original 的解释器是 miniconda base，pytest 不存在、项目 import 失败；诊断变体激活 testbed 后 import/解释器恢复。六次容器清理均记成功。
- 六份 `dev_check_exit_code` **全部为 0**，因为开发脚本逐步打印 RC，末尾是成功的 git status。不能用顶层 RC 判断环境恢复；例如 conan 的诊断变体仍有预期的业务断言失败。Brief 的“逐项 RC 对照”应保留。
- 当前正式编排确实只把 BASH_ENV 写入 `HarnessLaunchSpec`，没有传给 driver；旧路径又在隐藏的 `/root`。本轮未发现需要推翻 #1 的证据。
- 宿主收集能够删除 RH2 额外创建的 `.harness/trajectory.jsonl` 和 `/tmp/.run.*`，不改其排除政策。它不等于禁止 CC 自身全部缓存、会话历史或工具输出；本片不扩大到这些 harness 功能。
- 本轮通过用户给定的 CPU 机核实 Docker 可用；只做一个小型 Docker 环境对照，不运行 CC、模型 API、训练或完整 profile 验收。作者已有的 profile verify 与六题证据是复用证据，未冒充本轮重跑。

## 2. 实施前修订

### SR1 / P1：逐 execution 数据不能存入继承来的单例实例

**当前方案**：Brief §1.2（第 31 行）只覆盖 `Rh2ClaudeCodeHarness.launch_and_wait`，但没有说明 env、宿主输出路径和期限如何从 driver 穿过继承的 `run()` 到该方法。`BaseHarness.run` 与 `HarnessContext` 的现有参数没有这些字段。

**关键事实**：`BaseHarness` 使用 `SingletonABCMeta`，继承 `SingletonMeta`，新 RS 子类也只有一个实例。源码：`rh2/src/slime/agent/harness/common.py:32–57`、`rh2/src/slime/utils/misc.py:55–66`。主审真实导入基类的 CPU 反例：

- `Subclass("A")` 与 `Subclass("B")` 是同一对象，第二次构造不再运行初始化，仍取 A。
- 两个协程交错改同一个 `self.value`，最后得到 `["B", "B"]`。

**影响 / 可达性**：`conditional_future`，本片即将启用的方案缺口；不是声称尚未写出的 RS 实现已经串扰。若用构造参数或可变实例字段装逐题 env/path/deadline，并发 execution 将拿到别题的配置或写入同一日志。当前三题 env 相同可能掩盖问题，日志路径本来就不同。正式并发是既有能力，不能留到八卡才发现。

**最小修订**：明确一个逐调用运输办法：无状态 helper 的显式参数优先；若保留继承接口，可用明确 set/reset 的任务局部 context，或窄改调用层。不要为保留“仅 15 行 override”把数据塞进单例。同步 `HarnessDriver` 协议、SimpleLoopDriver 和相关替身的签名。路径在编排层从非秘密 execution/trajectory 身份生成并传入；driver 的 `session_id` 实际是 capability token（`generate.py:2965`），不能用它作为日志目录名。

**验收**：两个不同 env/path/deadline 的 execution 在真实 RS 子类→launch→收集器处交错，各自保持正确归属；一个中途取消也不影响另一个。只让替身 harness 收到 env 不够。探针：[review_cpu_probe.py](review_cpu_probe.py)，结果：[review_cpu_probe.json](review_cpu_probe.json)。这是局部运输修订，无需新状态机或串行化全部 rollout。

### SR2 / P1：收集器要区分“日志写失败”和“执行退出事实丢失”，并补齐取消收口

**当前方案**：Brief §2.2（第 60–67 行）把客户端异常退出、容器仍运行记为 `harness_output_collection_failed`，写 launch facts 后称“不影响终止判定”；取消和到期合写为沿用 `EXIT_TIME_BUDGET_EXCEEDED`。

**违反的边界**：日志文件本身不是训练事实，但新 `docker exec` 连接也是等待 CC 退出的通道。连接丢失时，不能因为 capture 有记录就认定 CC 正常完成。另一方面，外部取消、poison、宿主客户端被信号终止也不都等于墙钟到期。

**当前消费者证据**：

- `generate.py:3052` 只从 launch facts 取几个启动字段；新键不会自动成为 termination 事实。
- `generate.py:4190`、`outcome_producer.py:56`：未知 typed 码默认 run-fatal，当前映射中没有 `harness_output_collection_failed`。
- `generate.py:3141`：turn-cap 在场时普通非零退出被豁免。因此客户端/收集失败若仅降成整数非零，可能被 cap 正常截断路径掩盖。
- `generate.py:4158`：hard-wall 先取消并等待 harness task 收口，随后第 3077 行才停止容器内 agent。收集器取消时不能等待“容器先停止后才有”的 EOF，否则外层停止动作到不了。容器内停止仍由既有 owner 负责，不另造第二套停止生命周期。

**影响 / 可达性**：`conditional_future`，新增长连接 owner 即将启用；错误分流不清会导致错误保留样本、意外停 run 或关停等待。发生频率未知；修订只是明确局部 try/finally 和既有分流，成本低于实施后重拆生命周期，宜本片完成。

**最小修订**：写明客户端进程、stdout/stderr 读取任务、文件句柄都归同一次收集调用；正常结束排空两路尾部，异常或取消回收宿主进程与读取任务、关文件后传播。仅确认期限到点使用预算超时标记；其它取消保留 `CancelledError`，由编排识别 poison/外层取消。

按来源拆清至少两类失败：① 仅额外诊断文件写失败、仍可排空输出且取得可信退出结果，可记录日志不完整而保留既有执行处置；② 执行连接异常，失去可信结束事实，走既定执行基础设施失败收口，不评分交付、继续停止与清理，不能只记日志或被 turn-cap 豁免。新增 typed 码须明确其实际抛出点与映射消费者，未知程序错误仍按批 A fail-fast，不大包 `except Exception` 洗成局部故障。正常 CLI 非零、客户端异常和 owner 主动终止也应分别留事实，不能只凭一个整数宣称均来自 daemon 中的 CC。

**验收**：持续输出时 hard-wall、外层取消、poison、turn-cap 强停、日志写入异常、客户端异常各覆盖真实收口分支；证明宿主任务/句柄已结束、外层容器清理可继续、部分日志保留、原因没有被 cap 或超时覆盖。无需全训练回归或 GPU。

### SR3 / P2：解释器探针的 census 顺序写反，应明确放置点

**当前方案**：Brief §1.2 第 36 行说“探针本来就在 census 之后”。

**源码事实**：`_prepare_workspace`（`generate.py:3841`）先调用 `_materialize_rollout_sandbox`，后做 `generate_baseline_manifest`；现有 `run_rollout_prelaunch_check` 在物化函数内部第 4897 行。因此，直接扩充旧 probe 会让新增的激活/Python 检查发生在首次 census **之前**。

**影响 / 可达性**：现有调用顺序 `reachable`；新 Python 检查的副作用是 `conditional_future`，本轮未证实三题发生新污染。`PYTHONDONTWRITEBYTECODE` 只限制字节码，并不禁止 Python 启动时的 site/.pth 或激活 hook 执行其它动作，不能把它写成通用的“不写工作区”保证。

**最小修订**：保留原安全 prelaunch 的位置，把新增的解释器检查明确放在 baseline 之后、CC 获得写权之前，或给出实际无副作用的更窄方案；不需要把全部安全探针搬动。按实际调用次序和工作区变化验收，符合已登记的 R2E §11.5。

**同形性补充，非三题新故障**：把 HOME 在启动 Bash **之前**随 exec env 明确传入。远端 conan 实测：Docker 当前会为 `-u agent` 默认给 `/home/agent`，Brief 形态也激活成功；只有显式模拟镜像 HOME=/root 时，BASH_ENV 在主体内 export 前读到 /root，落到 base Python。故这是兼容性/一致性窄修，不应声称当前三题因此失败。探针/结果：[review_docker_home_probe.py](review_docker_home_probe.py)、[review_docker_home_probe.json](review_docker_home_probe.json)。probe 与最终 launcher 应复用必要的有效 env，而不是两份手写常量。

### SR4 / P2：验收入口与日志观测要改成真实消费者

**当前方案与证据**：

1. `solve_attempt.py:314–350` 手工构造 env；dev-check 直接调旧 `exec_and_wait`，没有经过 `ClaudeCodeDriver`。它的 original 分支明确不注入 BASH_ENV。只改 Brief 列出的生产文件，再跑原命令，不会自然验到新接线。正式 driver 只在另一个 solve 分支进入。
2. Brief §2.3 第 71 行要求 JSONL 行数与请求数一致，实际启用了 partial messages、hook events、verbose。本地 CC 2.1.205 历史正例为 **323 行、26 个 message_start、1 个 result**；不是一请求一行。
3. Brief §2.2 第 64 行仅向 `audit.artifact_paths` append 路径；`bringup.write_execution_audit_record`（第 675–786 行）当前不序列化这个列表。若不补实际落盘引用，B 无法按 execution audit 找到新日志，内存里记过不等于已交付。

**影响 / 可达性**：当前工具/消费者行为 `reachable`，修复验收遗漏和日志运输是本片将启用的接缝。会出现测试没测到新路径、正常流因错误 oracle 被误判或日志无持久索引；不表述为已发生训练污染。

**最小修订与验收**：保留六份基线，后测让验证入口复用最终 env/launcher；并在既定真实 CC + 桩端点用例里，通过一次真实 Bash 工具调用回传解释器/环境。无需新增模型训练作业。以已知桩响应、CC 事件类型和实际退出状态核对日志，正常有 result，强制终止允许缺终局事件并明确 partial；不要把 result 在场另加成所有训练样本的新闸门。补 execution audit 的路径及 complete/partial/error 观测，再从落盘 JSON 回读，包含失败路径。

## 3. 可接受项、分工与停止条件

- `/rh2` root 所有权、0755/0644 及逐 execution 注入成立；内部 dataclass 增加激活字段不需要新公共 schema。R2E `.venv` 生产来源映射仍需后续 B 接线，不能把“留了字段”写成“R2E actor 已完成”。
- 宿主收集比 FIFO 少一个容器 root 读端，方向成立；但它仍持有宿主进程和管道任务。小块同步写也会占用事件循环，撤回“不会阻塞”的绝对保证。首版沿本地小块写可测其占用，不预建异步存储平台；若磁盘慢，队列/线程方案必须有界。
- 默认 stdout JSONL 与 stderr 分开保存便于消费；若保留旧混合形式则需明确并让 B 的读取器覆盖，不能给混合输出强加纯 JSONL 的解析承诺。
- `materialize.py` 当前无未提交 diff，且 R2E 计划 §11.5 已记录 A 为该接口修复 owner。继续按单写者协作即可，不再请用户批准文件归属；B 的 public_hints 措辞属于并行配合，不阻塞 A 这两个修复。
- A 提交完成环境运输，B 提交切换宿主收集；中间 A 保留旧日志路径是明确的未修 #2 状态。避免同一 execution 新旧两个 launcher 同时启动。可各自回退，回退 A 时需同时检查 B 对接口的依赖。

**Stop condition**：SR1/SR2 的逐调用运输、取消/错误分流，以及 SR3/SR4 的探针位置和真实验收入口写清后，Claude 可以在同轮实施，无需再等用户方向批准。实现后按这些接缝做一次聚焦复核。#3 流故障夹具可以同期开发；#6/#8 窗口/#9/#10 的模型输入决策保持独立。暂不扩展全部 CC 原生日志隔离、网络供应、历史脚本清理、E3 或评分重审。

## 4. 审查范围与复现

按计划审查 §3.2：深查 A/D/G/L（启动、共享状态、真实入口、收集反压与取消），B/F/H（保留预算与失败语义、唯一退出事实），E/M/N（有效验收、持久日志与 CC 版本）；I/J/K 用于控制切片和实现规模。C 无新增临时挡板。本片未改 reward/loss/训练行，相关数学不重审。依 §10.4 两路限定检查，主审独立复现关键证据并裁决。

本机命令（从仓库根执行）：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/review_cpu_probe.py
rh2/.venv/bin/ruff check docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/review_cpu_probe.py docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/review_docker_home_probe.py
```

远端使用已有 CPU 机的 `python3 -` 接收 `review_docker_home_probe.py`：只使用已存在的 conan 镜像，网络 none、512 MiB，不改 daemon、镜像或部署代码，finally 按本次随机名称删除容器；删除成功且本轮标签下无残留。连接方式留在本机私有配置，不写凭据或机器地址进本文。

本轮 CPU 探针与 ruff 通过；未跑维护测试全库、真实 CC、GPU 或付费模型 API，未租/销毁机器。只新增审查文档、探针与结果，追加 Brief 指针和 infra 记录；未改生产代码、维护测试、fork 或历史 evidence，未提交/push、未向其它任务发送消息。
