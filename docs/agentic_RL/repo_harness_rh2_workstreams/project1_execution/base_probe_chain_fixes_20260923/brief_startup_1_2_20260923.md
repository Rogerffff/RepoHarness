# #1 / #2 启动修复短 Brief：项目解释器注入、harness 日志与控制文件

2026-09-23 / Claude（A 线）。**状态：Brief，待 Codex 聚焦检查后实施。** 依据：[基座探针交接包](../base_model_probe_20260922_aline_handoff.md) §1–§2、§13（A 线接收）、§14（Codex 开工复核，其修订全部并入本文）；[R2E 计划 §11.5](../r2e_grading_wiring_20260920.md) 的接缝。两个提交可独立审查：提交 A = #1，提交 B = #2。

## 0. 已在验证机上复现的基线（2026-09-23）

x86_64 CPU Docker 机（Ubuntu 24.04、Docker 28、cgroup v2；沙箱 profile `verify` 通过，digest `sha256:0f62e1f8…`）。三题（conan-15422、dvc-5839、moto-5134）用 B 线的 `solve_attempt.py --mode dev-check` 各跑 `original` / `bash_env_v1`，与 B 线 p1 证据一致：

| 变体 | `BASH_ENV` | `python` | `pytest` | 项目 import |
| --- | --- | --- | --- | --- |
| `original`（正式链现状） | 空 | `/opt/miniconda3/bin/python` 3.11.5 | 无 | 三题全部失败（RC 1） |
| `bash_env_v1`（诊断变体） | `/rh2/bash_env`，可读 | `/opt/miniconda3/envs/testbed/bin/python` | 有 | 三题全部通过 |

六次运行容器均已回收。证据：本地 `runs/base_probe_fixes_20260923/remote/a1_devcheck/`（`attempt.json`、`facts/agent_env_facts.txt`、`dev_check_output.txt`）。

## 1. #1：actor 拿不到项目解释器

### 1.1 两处缺口（已核源码）

| 缺口 | 位置 | 现状 |
| --- | --- | --- |
| ① 激活文件对 agent 不可读 | `envpack/materialize.py:47` `BASH_ENV_PATH="/root/.rh2_bash_env"`；`sandbox_profile.py:339` `hidden_paths=("/root",)`；探针 `HIDDEN_*` 须 DENIED | 文件写在 agent 不能读的目录，且探针**要求**它不可读 |
| ② 环境没有注入 CC 子进程 | `generate.py:2934` 只把 `{"BASH_ENV": …}` 写进 `HarnessLaunchSpec.env_injections`；`:2960` 调 driver 时没有传下去；`bringup.ClaudeCodeDriver.run` → vendored `ClaudeCodeHarness.launch_and_wait`，子进程环境 = `ANTHROPIC_*` + `static_env` + 进程级 `SLIME_AGENT_CC_EXTRA_ENVS` | 契约字段存在、没有运输 |

### 1.2 修法

**① 激活文件**：root 可信初始化建 `/rh2`（root:root 0755），激活文件写到 `/rh2/bash_env`（root:root 0644：agent 可读、不可写；目录不可写 → 不能删除 / 替换）。`hidden_paths` 不变（`/root` 继续隐藏）。`materialize.BASH_ENV_PATH` 改为该路径；写入点仍是 `generate.py:4856–4873` 那一段（root `docker exec` 写入，随后 `chmod 0644`）。

**激活内容按来源，不写死 conda**（R2E §11.5）：`RolloutTaskSpec` 增加 `env_activation_script: str`（公开、模型可见面，过 forbidden marker 扫描），默认值 = 现在的 `materialize.BASH_ENV_CONTENT`（`swe_gym_lite` 的 conda `testbed` 激活）；`rollout_spec_from_view` 本片不改（B 线在制品文件），R2E 接入时由其 overlay 给 `.venv` 的激活行。写入 `/rh2/bash_env` 的内容取自 spec，不取常量。

**② 按 execution 运输**：`RolloutOrchestrator` 调 driver 时传 `env_injections=launch.env_injections`；`ClaudeCodeDriver.run(..., env_injections: Mapping[str, str] | None = None)`；driver 用 RS 层子类 `Rh2ClaudeCodeHarness(ClaudeCodeHarness)` 覆盖 `launch_and_wait`，把 `env_injections` 并入子进程 env（在 `ANTHROPIC_*` / `static_env` / 进程级 extra envs 之后、优先级最高）。**不经过** `SLIME_AGENT_CC_EXTRA_ENVS`；训练守卫三个键仍走它（它们本来就是进程级常量）。vendored `claude_code.py` 不改（子类只重写 `launch_and_wait` 一个方法，约 15 行，见 #2 同一子类）。

**③ 启动前探针新增两项**（`rollout_prelaunch_probe_script`，agent 身份）：

- `ACTIVATION_READ=1|0`、`ACTIVATION_WRITE=DENIED|WRITABLE`（`[ -r ]` 与 `: >> 文件` 的失败）——可读且不可写才通过；
- `ACTIVATION_PYTHON=<sys.executable>`：以 **CC 同形**方式取得——`env BASH_ENV=/rh2/bash_env PYTHONDONTWRITEBYTECODE=1 bash -c 'cd /tmp && python -c "import sys; print(sys.executable)"'`，与 spec 声明的 `expected_interpreter_prefix`（新增，默认 `/opt/miniconda3/envs/testbed`，R2E 给 `/testbed/.venv`）比对。cwd 用 `/tmp`、只 import `sys`、不写字节码：不碰工作区，放在首次 census 之后（探针本来就在 census 之后运行），满足 R2E "首次 census 前不新增写缓存的 Python 探针"。

### 1.3 验收

1. 三题 `original` 条件（即修复后的正式路径，不再需要诊断变体）下 `agent_env_facts` 与 `bash_env_v1` 一致：`BASH_ENV=/rh2/bash_env`、`CONDA_DEFAULT_ENV=testbed`、`python`/`pytest` 指向 testbed；dev-check 各步 RC 与 `bash_env_v1` 逐项相同。
2. 探针三项新事实为 `1 / DENIED / 前缀匹配`；把文件改成 agent 可写、或内容指向 base 解释器的反例各一个 → 探针拒绝启动。
3. 基线与运行后 census 不变（`/rh2` 在工作区外；探针不写工作区）。
4. 单测：`HarnessLaunchSpec.env_injections` 经 driver 到子进程 env 的运输（替身 harness 记录收到的 env）；两个并发 execution 各自的注入互不串扰；vendored `launch_and_wait` 未被调用路径的测试不变。
5. B 线 `public_hints` "pre-activated conda env" 措辞由 B 核对（该字段不进 prompt）。

**T 级**：T1。`RolloutTaskSpec` 是 RS 内部 dataclass，不是公共 schema；`HarnessLaunchSpec` 不改。`envpack/materialize.py` 目前无 B 线在制品，A 写；开工前留言确认。

## 2. #2：harness 轨迹文件对 agent 可读

### 2.1 现状（已核源码）

vendored `run_agent`（`slime/agent/harness/common.py:107–122`）在 `{workdir}/.harness` 建目录并 `chown agent`，经 `exec_and_wait` 以 agent 身份 `setsid` 启动 launcher `/tmp/.run.sh`，stdout 重定向到 `{workdir}/.harness/trajectory.jsonl`，退出码由 launcher 写进 `/tmp/.run.done`，宿主每 5 s 轮询该标记。三个文件都归 agent：轨迹可读（探针里 DVC5839 把自己的编辑当"参考解"反复 grep）、`git status` 显示 `?? .harness/`、退出码标记可伪造。rh2 源码没有读取轨迹内容的消费者（census 只审计排除区的路径集合）；B 线探针的分析消费它。

`exec_and_wait` 的"分离 + 标记轮询"是为 E2B 网关会切断长流设计的（其 docstring）；本地 Docker CLI 没有这个限制，`DockerSandbox.exec` 就是宿主 `docker exec` + PIPE。

### 2.2 修法：宿主收集，不再有容器内日志与控制文件

按 Codex §14.1：不用 0733 目录、不预选 FIFO。比较后选**宿主收集**：

- `Rh2ClaudeCodeHarness.launch_and_wait`（#1 同一子类）不调 `run_agent`，改调 RS 层 `run_agent_host_collected(sb, workdir, cmd, env, deadline, out_path)`：宿主起 `docker exec -u agent -e … <容器> bash -c 'cd <workdir> && export HOME=/home/agent && exec <cmd>'`，stdout/stderr 用 asyncio 子进程管道**增量写**到宿主文件 `<artifact_dir>/<execution>/harness/trajectory.jsonl`（宿主 root 目录，容器内没有副本）；退出码来自 `docker exec` 的返回（daemon 报告，不可伪造）。容器内不再创建 `.harness/`、`/tmp/.run.sh`、`/tmp/.run.done`。
- 长输出：逐块写文件，不在内存里攒完整输出（`_run` 的 `communicate()` 不适用，新增一个流式变体）；写文件是小块同步写，不阻塞 owner 循环。
- 期限与取消：到期 / 取消时杀宿主 `docker exec` 客户端（现有 `_run` 的 kill 路径），容器内 CC 进程由既有 `execution_scope` 屏障（`pkill -u agent`）与容器清理终止；退出码映射沿用 `EXIT_TIME_BUDGET_EXCEEDED`。
- 收集失败（宿主 `docker exec` 客户端异常退出而容器仍在跑）：typed `harness_output_collection_failed`，进 launch facts；不影响 capture / 终止判定（它们从不依赖这个文件）。
- `.harness/` 排除区政策**不改**（公共契约）；目录不再存在只是排除区为空。`audit.artifact_paths` 追加宿主轨迹文件路径，B 线分析改读宿主副本。
- 与 R2E：`rollout_trusted_init_script` 只加 `/rh2` 目录（#1），不动其它；`.git/`、`.harness/`、`.venv/` 政策与 `/rh2_private` 私有性不变。

不选 FIFO 的理由：要多一个 root 读端进程及其就绪 / EOF / EPIPE / 取消 / 清理，而 `execution_scope` 只终止 agent UID；同 UID 仍可向 FIFO 注入内容。宿主收集没有这些生命周期，且顺带消除了可伪造的退出码标记。

### 2.3 验收

1. 真实 CC 2.1.205 + 桩端点（同 #3 夹具）跑一题：agent 身份 `ls /testbed/.harness`、`cat` 任何候选路径失败、`/tmp/.run.*` 不存在、`git status --porcelain` 干净；宿主轨迹文件完整（`result` 事件在场，行数与桩端点请求数一致）；退出码与 CC 真实退出一致（正常 0、`--max-turns` 到顶、被 `pkill` 时各一例）。
2. 期限到点：宿主客户端被杀、屏障终止 CC、launch facts 记录 `time_budget_exceeded`，文件保留已收集部分。
3. census：基线与运行后 digest 不变；排除区独立 census 为空集。
4. 单测：流式收集器的分块写、取消、非零退出；driver 不再调用 vendored `run_agent`（源码断言）。

**T 级**：T1（强化边界，不改公共契约、不改 reward）。改动文件：`bringup.py`（子类 + 收集器）、`docker_sandbox.py`（流式 exec 变体）、`generate.py`（传 env_injections、artifact 路径）、`sandbox_profile.py`（`/rh2` 目录、探针两项）、`envpack/materialize.py`（路径 / 内容来源）。vendored 文件零改动。

## 3. 顺序、机器与不做的事

- 顺序：提交 A（#1）→ 提交 B（#2）；两者共用 `Rh2ClaudeCodeHarness`，A 先引入子类只做 env 合并。
- 验证机：已就绪的 CPU 机（profile verify 通过，三题镜像与 CC 2.1.205 平台包在位）。#2 的真实 CC 验收与 #3 复现共用桩端点夹具，夹具随 #3 一起写。
- 不做：不改 `.harness/` 排除政策；不给容器加 SETUID；不动 vendored 文件；不把"末轮 tool_use 无后续请求"当准入规则；不定 `#8` 窗口等训练条件。

## 4. Codex 计划复核入口（2026-09-23）

[聚焦复核与证据](codex_plan_review_20260923.md)：接受方向，SR1–SR4 并入后实施，无新 T0。重点为继承单例下逐 execution 数据运输、宿主收集器的取消与执行失败分流、首次 census 的真实先后顺序、dev-check/真实 CC/持久 audit 的验收入口。原方案正文保留供作者逐项回应，不把本节指针当作已完成修订或实现通过。

## 4. 并入 Codex 设计复核 SR1–SR4（2026-09-23，实施前）

[Codex 复核](codex_plan_review_20260923.md)接受方向；以下修订全部 accepted，与上文冲突处以本节为准：

| 项 | 修订 |
| --- | --- |
| SR1 单例 | `BaseHarness` 经 `SingletonABCMeta` 是单例，RS 子类同样只有一个实例——**不再子类化、不放任何逐 execution 数据到实例字段**。改为 RS 层无状态函数 `launch_claude_code(sb, *, workdir, session_id, adapter_url, prompt, time_budget_sec, env_injections, harness_log_dir)`：按 vendored `run()` 的三步调用 `ensure_agent_user` → `ClaudeCodeHarness().write_config(sb, ctx)`（无状态方法）→ 自己拼 cmd/env 后启动。`HarnessDriver` 协议、`ClaudeCodeDriver.run`、`SimpleLoopDriver` 与测试替身同步加 `env_injections` / `harness_log_dir` 两个关键字参数。日志目录由编排层从非秘密的 trajectory / execution 身份生成并传入，不用 `session_id`（它是 capability token）。验收：两个 env / 路径 / 期限不同的 execution 在真实 RS 启动函数与收集器处交错，各归各的；一个中途取消不影响另一个 |
| SR2 收集器 | 客户端进程、两路读取任务、文件句柄归同一次调用，`try/finally` 收口：正常结束排空尾部；异常或取消回收进程与任务、关文件后传播。只有确认期限到点才返回 `EXIT_TIME_BUDGET_EXCEEDED`；其它取消原样传播 `CancelledError`。失败分两类：① 只是诊断文件写失败（磁盘）——继续排空管道、取得可信退出码，记 `harness_log_partial=True` + 错误，执行处置不变；② 执行连接异常（docker CLI 自身错误 125/126/127 或 daemon 连接错误形态）——失去可信结束事实，抛 typed `harness_exec_connection_lost`，登记进 `FAILURE_CODE_TERMINATION_MAP` 按既定"执行基础设施失败"收口（不评分交付、继续停止与清理、不受 turn-cap 豁免）。未知程序错误按批 A fail-fast，不大包 `except Exception`。退出事实分列：`harness_exit_code`（容器内进程）、`client_exit_kind`（container_process_exit / docker_cli_error / killed_by_owner / time_budget）。stdout（JSONL）与 stderr 分开保存 |
| SR3 探针位置与 HOME | 现有安全探针在物化函数内、首次 census **之前**（`_materialize_rollout_sandbox` → `run_rollout_prelaunch_check`），不动它。新增的解释器 / 激活检查单独成一步，放在 `generate_baseline_manifest` 之后、harness 启动之前；`PYTHONDONTWRITEBYTECODE=1`、cwd=/tmp、只 import `sys`，但不宣称"不写工作区"——任何副作用都会落在运行后 census 的 delta 里被看见。HOME 随 exec env 显式传入（`docker exec -e HOME=/home/agent`），探针与最终 launcher 共用一个 `agent_exec_env(...)` 构造函数，不写两份常量 |
| SR4 真实验收入口 | 六份基线保留。修复后的验收不用 dev-check（它自建 env、走旧 `exec_and_wait`），而是**真实 CC 2.1.205 + 桩端点**经正式 `ClaudeCodeDriver.run`：桩脚本让 CC 用 Bash 工具执行 `python -c 'import sys,os; print(sys.executable, os.environ.get("CONDA_DEFAULT_ENV"))'`，从宿主收集的轨迹与工具结果回读解释器。日志 oracle 改为：正常结束有 `result` 事件、`message_start` 数 = 桩端点请求数、强制终止允许缺终局事件且标 partial；不把 `result` 在场变成训练样本闸门。`write_execution_audit_record` 补落盘 `harness_log`（path / stderr_path / bytes / complete / partial / error），从落盘 JSON 回读验收 |

其余接受项：`/rh2` 权限与逐 execution 注入成立；R2E `.venv` 的生产来源映射仍待 B 接线；宿主收集"小块同步写不阻塞"的绝对保证撤回，首版实测占用；A 提交先完成环境运输（launcher 仍是 vendored `run_agent`、旧日志路径 = 明确的未修 #2 状态），B 提交切换宿主收集。

## 5. 提交 A（#1）实施记录（2026-09-23，Claude，已实施、本机与真机验证）

### 5.1 改动

| 文件 | 改动 |
| --- | --- |
| `envpack/materialize.py` | `BASH_ENV_PATH = "/rh2/bash_env"`；新增 `SWE_GYM_INTERPRETER_PREFIX`；注释说明 root 0644 / 按来源 |
| `adapters/slime/sandbox_profile.py` | 可信初始化加 `install -d -m 0755 -o 0 -g 0 /rh2`；`rollout_prelaunch_probe_script(profile, activation_file=)` 追加 `ACTIVATION_READ / ACTIVATION_WRITE / ACTIVATION_STAT`（`[ -r ]`、追加零字节失败，无副作用）；`check_rollout_probe(..., activation_file=)` 要求 `1 / DENIED`；`run_rollout_prelaunch_check(..., activation_file=)` 透传；新增 `agent_shell_env(profile, activation_file)`（HOME + BASH_ENV，探针与 launcher 共用）、`rollout_activation_probe_script(env, expected_interpreter_prefix)`（`env HOME= BASH_ENV= PYTHONDONTWRITEBYTECODE=1 bash -c 'cd /tmp; …import sys…'`）、`check_rollout_activation`、`run_rollout_activation_check` |
| `adapters/slime/generate.py` | `RolloutTaskSpec.env_activation_script`（默认 = 现常量）与 `expected_interpreter_prefix`（默认 conda testbed 前缀）；激活文件内容取自 spec，写入后 `chmod 0644`；启动前探针带 `activation_file`；launch spec 的 `env_injections` = `agent_shell_env(...)`（无 profile 的 legacy 路径只带 `BASH_ENV`）；`HarnessDriver` 协议加 `env_injections` / `harness_log_dir`；driver 调用传 `env_injections=dict(launch.env_injections)` 与 `harness_log_dir=<artifact_dir>/<trajectory>/harness`；新增 `_check_activation_after_census`（在 `generate_baseline_manifest` 之后、harness 之前，失败抛 typed `rollout_activation_check_failed`，事实进 `audit.activation_check`） |
| `adapters/slime/bringup.py` | `claude_code_launch_env(...)`（ANTHROPIC_* + static_env + 进程级 extra envs + 逐 execution 注入，注入优先级最高）；无状态 `launch_claude_code(sb, *, workdir, session_id, adapter_url, prompt, time_budget_sec, env_injections)`（`ensure_agent_user` → 单例 `ClaudeCodeHarness().write_config` → 自拼 cmd/env → vendored `run_agent`）；`ClaudeCodeDriver.run` / `SimpleLoopDriver.run` 接 `env_injections` / `harness_log_dir`（后者 #2 启用）；audit 落盘加 `activation_check` |
| `adapters/slime/outcome_producer.py` | `rollout_activation_check_failed → ("sandbox_failure", "sandbox_crash")`（task-local，可补采） |
| `scripts/sandbox_probes/rollout-trusted-init.sh` | 重新 dump（+1 行 `/rh2` 目录） |
| 测试 | 新增 `tests/adapters/test_startup_fix_1_activation.py`（20 例）；`sandbox_test_support.py` 探针罐头加 ACTIVATION 三行、`activation_overrides` 旋钮与 `rollout-activation-probe` 应答；13 处 driver 替身签名同步（含 `experiments/s1_parity.py`）；4 处 fake docker 的 `cat > <path>` 解析改为只取路径；旧路径 oracle 与两处"补丁打在 vendored `launch_and_wait`"的用例改到新接缝 `bringup.launch_claude_code` |
| vendored `rh2/src/slime/` | 零改动（`VENDOR_README` 修补记录不需要新增） |

### 5.2 验证

- 本机：`tests/adapters/test_startup_fix_1_activation.py` 20 passed；五目录非 Docker **1589 passed / 1 skipped**；双 lane 脚本全绿（A 463p/343s、B 806p/0s，计数与当前 manifest 一致）；ruff 通过。
- 真机（验证机，真实 `conan-15422` 镜像，`runs/base_probe_fixes_20260923/local_probe_checks/activation_probe_real_image_conan15422.txt`）：`/rh2` 0:755、`/rh2/bash_env` 0:644；agent 身份探针 `ACTIVATION_READ=1 / ACTIVATION_WRITE=DENIED`；**生成的激活探针脚本原样**运行得到 `ACT_SYS_EXECUTABLE=/opt/miniconda3/envs/testbed/bin/python`、`ACT_CONDA_DEFAULT_ENV=testbed`；反例——文件 0666 → `WRITABLE`、激活内容置空 → base 解释器、agent `rm` / 在 `/rh2` 下建文件均 Permission denied；探针后 `/testbed` 的 `git status --porcelain` 为 0 行。
- 一个排查记录：真机第一轮探针曾报 base 解释器，原因是我的测试脚本用 `printf '%s' $CONTENT` 写激活文件、内容以 `#` 开头被外层 shell 当注释吞掉，文件为空；改为 base64 经 stdin 写入后通过。生产写入走 `docker exec -i … cat > …`（stdin），不受此影响。
- **未做**：真实 CC 2.1.205 经正式 driver 的端到端验收（Brief §4 SR4）留到 #2 提交后与 #3 夹具一起做——A 提交只改环境运输，launcher 仍是 vendored `run_agent`。

### 5.3 与 Brief 的差异

- SR3 的"cwd=/tmp、只 import sys、不写字节码"照做，但不宣称零副作用；真机对照显示 `/testbed` 未被写。
- 激活核对失败按 task-local（`sandbox_failure / sandbox_crash`）处理而不是 run-halt：同一镜像的系统性失败会表现为该任务反复 ABORTED，可从 `activation_check.facts` 直接看出；R2E 的逐题 `.venv` 也可能只有个别题失败，run-halt 不合适。

## 6. 提交 B（#2）实施记录（2026-09-23，Claude，已实施、本机验证；真机验收见 §6.4）

### 6.1 改动

| 文件 | 改动 |
| --- | --- |
| `adapters/slime/docker_sandbox.py` | 新增宿主收集器：`host_exec_argv(container_name, user, workdir, env, cmd)` 拼 `docker exec -u agent -w <workdir> -e K=V … <容器> bash -c 'exec <cmd>'`（HOME / BASH_ENV 在 bash 启动前就位，SR3）；`run_host_collected(argv, stdout_path, stderr_path, deadline_seconds, time_budget_exit_code)`：asyncio 子进程 + 两路泵任务逐块（64 KiB）追加写宿主文件、stderr 留 4 KiB 尾部；`wait_for` 期限到点杀客户端记 `time_budget`；`CancelledError` 杀客户端、取消泵、原样传播；返回 `HostCollectedRun`（`exit_code / client_exit_code / client_exit_kind / stdout_path / stderr_path / stdout_bytes / stderr_bytes / log_complete / log_partial_reason / stderr_tail / seconds`）。`classify_client_exit(rc, stderr_tail)`：125/126/127 或 stderr 末行是 docker 客户端错误形态 → `docker_cli_error`，否则 `container_process_exit`。`_open_log` 单独成函数作测试接缝 |
| `adapters/slime/bringup.py` | `launch_claude_code(..., harness_log_dir=None)` 不再调 vendored `run_agent`：宿主收集到 `<harness_log_dir>/{trajectory.jsonl,stderr.log}`（目录 0700；编排未给目录时用宿主临时目录 `rh2-harness-*` 并留痕）；事实进 `HARNESS_LAUNCH_FACTS["harness_log"]`；`client_exit_kind == docker_cli_error` → 抛 typed `harness_exec_connection_lost`（事实先落再抛）；期限到点返回 `EXIT_TIME_BUDGET_EXCEEDED`（-1）。`ClaudeCodeDriver.run` 把 `harness_log_dir` 传下去；`write_execution_audit_record` 落盘 `harness_log` |
| `adapters/slime/generate.py` | `RolloutAudit.harness_log`；harness 返回后从 launch facts 复制，宿主两份文件进 `audit.artifact_paths`（§2.2） |
| `adapters/slime/outcome_producer.py` | `harness_exec_connection_lost → ("harness_crash", "harness_crash")`（执行基础设施失败：不评分交付、继续停止与清理、不受 turn-cap 豁免） |
| 测试 | 新增 `tests/adapters/test_startup_fix_2_host_collected.py`（21 例：真实子进程的双通道流式收集、非零退出码、期限杀客户端且 `pgrep` 无残留、外层取消传播且无残留、写失败只标 partial 而退出码可信、`classify_client_exit` 矩阵、argv 形状、启动函数接线 / 无容器内 launcher / 事实与 typed 码、经真实 `ClaudeCodeDriver.run` 的 typed 码不被引导层改写、无目录时临时目录、audit 落盘回读、编排复制事实与 artifact 清单、源码断言不再调 `run_agent`）；`test_startup_fix_1_activation.py` 的并发用例改到收集器接缝 |
| `tests/adapters/test_w3b_sandbox_docker.py` | 夹具任务声明自己的 `env_activation_script` / `expected_interpreter_prefix="/usr/local"`（夹具镜像 `python:3.12-slim` 无 conda）；正常 rollout 用例加断言：真容器上激活核查通过、注入的 BASH_ENV 在 agent 的非交互 bash 里生效（`ACTIVATED=1`）；`AgentViewDriver` 把 `env_injections` 随 exec 传入 |
| vendored `rh2/src/slime/` | 零改动 |

### 6.2 验证（本机）

- `tests/adapters/test_startup_fix_2_host_collected.py` 21 passed（macOS）；同两份文件在验证机 Linux 上 41 passed。
- 五目录 **1663 passed / 1 skipped**（本机 Docker 已开：`test_w3b_sandbox_docker.py` 14 例真容器用例全部执行）；双 lane 全绿（A 463p/343s、B 806p/0s）；ruff 通过。
- **提交 A 遗留的夹具缺口**：提交 A 验证时本机 Docker 未开，`test_w3b_sandbox_docker.py` 未执行；本轮开 Docker 后 4 例失败，原因是夹具镜像 `python:3.12-slim` 的 `sys.executable=/usr/local/bin/python` 不在默认前缀 `/opt/miniconda3/envs/testbed` 下，激活核查按设计 task-local 失败（`sandbox_activation_check_failed`）。修法是夹具任务声明自己的激活事实（非 SWE-Gym 镜像的任务规格本来就该这样，R2E 同理），不是放宽核查。

### 6.3 与 Brief 的差异

- §2.2 的 `harness_output_collection_failed` 按 SR2 拆成两类：① 写文件失败（`log_partial_reason=write_error:…`，退出码仍可信、处置不变）；② `harness_exec_connection_lost`（typed、进映射表）。`client_exit_kind` 只有 `container_process_exit / docker_cli_error / time_budget`；取消不返回 `killed_by_owner` 而是原样传播 `CancelledError`（编排的取消路径已有自己的记录）。
- 期限到点只杀宿主 `docker exec` 客户端，容器内 CC 进程不由收集器终止：正式链随后 `_force_stop_execution_scope`（`pkill -u agent` + 停止证据）与容器清理收口（`generate.py` hard_wall 路径）。真机验收记录残留进程数（§6.4）。
- 日志目录 `<artifact_dir>/<trajectory_id>/harness`（从非秘密身份生成，不用 session token）；`artifact_dir` 缺省时收集到宿主临时目录并留痕，不静默丢日志。
- B 线 `experiments/base_probe_20260922/solve_attempt.py` 仍从容器内 `<workdir>/.harness/trajectory.jsonl` 取轨迹：#2 之后该文件不存在，应改读 `launch_facts["harness_log"]["stdout_path"]`（B 线脚本，留言告知，不由 A 改）。

### 6.4 真机验收（SR4，2026-09-23，验证机 x86_64 CPU / Docker 29.8.1（Codex 复核实测；此前误记为 28），真实 `conan-io__conan-15422` 镜像，真实 CC 2.1.205）

夹具：`rh2/experiments/base_probe_fixes_20260923/stub_anthropic_endpoint.py`（Anthropic Messages 形状的桩端点，SSE 与 vendored `_render_stream` 同形，逐请求剧本：`tool_use / text / hang / cut / http_error`，请求体落盘）+ `acceptance_startup_2.py`（正式 profile → relay → attempt 网络 → `docker_run_args` → sanitize → 可信初始化 → 与 `generate.py` 同一条脚本写激活文件 → `run_rollout_prelaunch_check(activation_file=)` → `run_rollout_activation_check` → **正式 `ClaudeCodeDriver.run(env_injections=agent_shell_env(...), harness_log_dir=...)`**；只有模型端点是桩）。CC 版本核对 `2.1.205 (Claude Code)`；平台包 sha256 记在各 `attempt.json`。证据：`runs/base_probe_fixes_20260923/remote/acc2_{normal,time_budget,max_turns,cut_stream}/`（`attempt.json`、`harness/trajectory.jsonl`、`stub/requests/*.json`、`prelaunch.json`、`activation_check.json`、`post_run_facts_root.txt`）。四个场景都以真实 SWE-Gym 镜像跑；桩剧本让 CC 用 Bash 执行 `python -c 'import sys,os; print(sys.executable, os.environ.get("CONDA_DEFAULT_ENV"))'` 与"模型可见面"检查。

| 场景 | 退出码 / `client_exit_kind` | 宿主日志 | 轨迹 `message_start` = 桩 `/v1/messages` 数 | 关键事实 | 期望 |
| --- | --- | --- | --- | --- | --- |
| normal | 0 / `container_process_exit` | complete，11 822 B，stderr 0 B | 3 = 3 | 工具结果 `RH2_SYS_EXECUTABLE=/opt/miniconda3/envs/testbed/bin/python`、`CONDA_DEFAULT_ENV=testbed`、`HOME=/home/agent`、`BASH_ENV=/rh2/bash_env`；agent 视角 `/testbed/.harness`、`/tmp/.run.sh`、`/tmp/.run.done` 均不存在；`git status --porcelain` 0 行；`/rh2/bash_env` 追加写 `DENIED`；运行后 agent 进程 0；`result{subtype:success,num_turns:3}` | 全部通过 |
| time_budget（wall 60 s，桩在第 2 个请求挂住） | -1 / `time_budget`（客户端 -9） | partial=`time_budget`，5 113 B | 2 = 2（第 2 个请求的 `message_start` 已收到） | 首个工具结果保留；容器内残留 1 个 `claude` 进程（58 s），`pkill -KILL -u agent` 后 0——**收集器不终止容器内进程**，正式链由 `_force_stop_execution_scope` 收口 | 全部通过 |
| max_turns（`--max-turns 3`，桩无限 tool_use） | 1 / `container_process_exit` | complete，10 521 B | 3 = 3 | `result{subtype:error_max_turns,is_error:true,num_turns:4}`；非零退出码来自 docker CLI，不再是 agent 可写的标记 | 通过（脚本 oracle 的解释器项对本剧本 N/A） |
| cut_stream（第 2 个请求在 `content_block_start` 后断开） | 1 / `container_process_exit` | complete，7 215 B | 2 = 2（**CC 未重试**） | `result{subtype:success,is_error:true,stop_reason:stop_sequence,num_turns:2}`，进程退出码 1。这是 #3 的第一条事实：流被切断时 CC 2.1.205 不重试、`result.subtype` 仍是 `success` 但 `is_error=true` 且退出非零——正式链凭宿主拿到的退出码即可区分（`nonzero_harness_exit_in_formal_chain`），不依赖 `result` 事件 | 只记事实（#3 另做四形状 × commit 前/后边界） |

其它事实：四个场景桩端点**一次都没收到** `/v1/messages/count_tokens`（CC 2.1.205 在此启动形状下不调用它——#8 决策包的输入，B 线"count_tokens 返回 0"的影响面需要按此重估）；请求头 `anthropic-beta` 含 `claude-code-20250219, interleaved-thinking-2025-05-14, mid-conversation-system-2026-04-07, effort-2025-11-24`，请求体已落盘供 #4/#5/#6 分析。

未覆盖 / 偏差：SR2 ② `docker_cli_error`（daemon 断连）与 ① `write_error` 只有单测，真机不制造；census digest 前后对照未做，以 `git status` 0 行 + `find /testbed -newer <激活文件写入时刻>` 0 个文件替代（首轮把 `/testbed/.git` 目录本身算作"新写"——`git status` 刷新 index 的 lock 重命名改了目录 mtime，排除 `.git` 目录后为 0）；桩的 `hang` 场景在 SIGTERM 下不立刻退出（aiohttp 等待处理器），脚本已 kill。验证机用完由用户销毁（Spheron 无暂停）；远端已确认无残留容器 / 网络 / 桩进程。


## 7. Codex 实施复核（2026-09-24）

[复核报告、反例与验收条件](codex_implementation_review_20260924.md)：#1 激活与逐 execution 注入接受；#2 尚有 IR1（P1：客户端退出不能直接证明本次 exec 已完成）、IR2（P2：异常/取消日志事实未进入持久审计）、IR3（P2：短写误报完整）。本机和验证机真实 Docker 均复现 SIGINT/SIGTERM 后 CLI 返回 0、容器内原进程仍活，不能只补负返回码分支。主审 144 项相关维护测试通过（含 14 项真 Docker）；无新 T0，三项在本片修复，#3 夹具/后续决策包可并行准备。作者原验收记录保留，本文指针不把待修项标为已修。

## 7. Codex 实施复核 IR1–IR3 的处置与修订（2026-09-24，Claude）

[复核原文](codex_implementation_review_20260924.md)。三项全部 accepted；无新 T0。

| 项 | 处置 | 修法 |
| --- | --- | --- |
| IR1 / P1：Docker 客户端退出 ≠ 本次 CC 执行结束 | accepted | 宿主收集**不再起 `docker exec` CLI 子进程**，局部直连 Engine API（unix socket，裸 HTTP，无新依赖）：`POST /containers/{c}/exec` 拿 exec ID → `POST /exec/{id}/start`（`Upgrade: tcp` hijack，多路复用帧流增量写宿主文件）→ 流结束后对**同一 exec ID** 轮询 `GET /exec/{id}/json`（上限 10 s，正常几十毫秒）：`Running=false` 且 `ExitCode` 为 0..255 整数才是可信终态。流结束但仍 `Running=true`、inspect 404 / 无退出码 / 负码 → 不给退出码，调用方抛既有 typed `harness_exec_connection_lost`（`harness_crash` 收口，不受 cap 豁免）。没有宿主子进程，也就没有 `-1/-2/-9/-15` 这类与 RH2 内部码碰撞的负返回值。建 exec / 起流失败（daemon 不可达、容器不在）抛 `EngineApiError` → 启动函数转 `SandboxExecError` → driver 既有归因 `harness_bootstrap_failed`（task-local） |
| IR2 / P2：失败与取消时审计引用丢失 | accepted | 启动函数在起流**之前**就把 `progress` dict 挂到 `HARNESS_LAUNCH_FACTS["harness_log"]`，收集器每帧更新字节数、收口（正常 / 期限 / 取消 / 异常）时在 `finally` 里写全事实；编排层把复制动作移到 `_await_harness_within_deadline` 之后的既有 `finally`（`_absorb_harness_log`，幂等）——正常、typed 连接丢失、外层期限取消、poison 取消都能从内存 audit 与落盘 JSON 回读路径、实际字节与 partial 原因。保持原 `CancelledError` / typed 首因，不吞取消、不改预算类别 |
| IR3 / P2：短写误报完整 | accepted | `_LogSink` 按 `write()` 的实际返回累计；返回 0 视为短写（`EFBIG`），写失败 / 短写即关闭该文件、停止写、继续排空管道；`log_complete` 只在 exited 且两路无写失败时为 true。真实 `RLIMIT_FSIZE=4096` 子进程用例：8192 B 落 4096 B、计 4096、标 `write_error:stdout:write:…` |
| §5 验证机 Docker 版本 | accepted | §6.4 改为 29.8.1（此前误记 28） |
| §5 验收脚本没跑正式 orchestrator / cap 路径 | accepted（范围说明） | 新增正式编排（fa_formal）用例：typed 连接丢失在 cap 有 / 无两种情形下都 `aborted`、`remove_sample=True`、`completion_class=missing`、评分 0 次；验收脚本仍只覆盖 driver 层，不冒充正式 orchestrator 验收 |

### 7.1 改动

| 文件 | 改动 |
| --- | --- |
| `adapters/slime/docker_sandbox.py` | 删除 CLI 收集器（`run_host_collected / host_exec_argv / classify_client_exit / HostCollectedRun`）；新增 `docker_socket_path()`（`DOCKER_HOST=unix://…` 优先，否则 `/var/run/docker.sock`，再退 Docker Desktop 用户 socket）、`engine_request()`（普通请求，`Content-Length` / chunked 两种响应体）、`engine_hijack()`（`Upgrade: tcp`；101 = 原始帧流，200 + chunked = 帧在 chunk 体里）、`_FrameSource`（8 字节头解帧，chunk 边界与帧边界无关）、`_LogSink`（实际写入计数、短写收口）、`ExecCollectedRun`（`exec_id / exit_code / exec_state / 路径 / 字节 / log_complete / log_partial_reason / stderr_tail / seconds / inspect`）、`run_exec_collected(container_name, user, workdir, env, cmd, stdout_path, stderr_path, deadline_seconds, time_budget_exit_code, progress, socket_path, settle_seconds)`。`exec_state ∈ {start_failed, streaming, exited, time_budget, exec_running_after_stream_end, inspect_failed, cancelled}` |
| `adapters/slime/bringup.py` | `launch_claude_code` 改调 `run_exec_collected`；`progress` 先挂进 launch facts；`EngineApiError → SandboxExecError`；`time_budget → EXIT_TIME_BUDGET_EXCEEDED`；非 `exited` → typed `harness_exec_connection_lost` |
| `adapters/slime/generate.py` | `_absorb_harness_log(audit, launch_facts)`（幂等：`audit.harness_log` + 两条宿主路径进 `artifact_paths`）在既有 `finally` 里调用；删除只在正常返回后复制的旧写法 |
| 测试 | `test_startup_fix_2_host_collected.py` 重写（27 例）：unix socket 上的假 daemon（exec create / start(101 或 200+chunked) / inspect 剧本）钉住终态判定（settle 轮询、EOF 后仍 Running、404、无码、负码、bool）、期限（关连接不等退出、记一次 inspect 事实）、取消（传播 + 事实交出）、建 exec 失败、socket 不可达、短写 / open 失败、真实 RLIMIT_FSIZE、启动函数接线（create body 的 User / WorkingDir / Env / Cmd）、真实 driver（spawn 失败 → bootstrap_failed；typed 码不被改写）、编排落盘（正常 / typed / 外层期限取消三条路径的 `harness_log`）、正式编排 cap 有 / 无。新增 `test_startup_fix_2_engine_exec_docker.py`（7 例，`@pytest.mark.docker`，无 daemon 或镜像即 skip，`RH2_EXEC_TEST_IMAGE` 可指到在场镜像）：真实 daemon 的 0 / 3 / 130、300 KB、User/WorkingDir/Env 生效、期限后进程仍在且屏障杀掉后 daemon 记下终态、取消保留部分日志、容器被 kill → 137、容器不存在。`test_startup_fix_1_activation.py` 并发用例改到新接缝 |
| vendored `rh2/src/slime/` | 零改动 |

### 7.2 真实 daemon 上核对的事实（原型脚本，本机 29.4.1 与验证机 29.8.1 一致）

- 不带 `Upgrade` 头时 29.x 的 exec start 回 `200 + Transfer-Encoding: chunked`（帧在 chunk 体里）；带 `Upgrade: tcp` 回 `101` + `application/vnd.docker.multiplexed-stream` 原始帧流——正式路径用后者（与官方 CLI 同一接缝），前者作兼容分支只在假 daemon 上测。
- 流只在进程退出或连接丢失时结束：进程把自己的 stdio 重定向到 `/dev/null` 后继续跑，流**不会**结束——所以"流已 EOF 但 `Running=true`"只会来自连接层，作 typed 判据成立。
- 流 EOF 后立即 inspect 就是 `Running=false` + `ExitCode`（3 / 130 / 0，300 KB 输出逐帧完整）；容器被 `docker kill` 时 exec 的终态是 137，走既有非零退出码路径而不是"完成"。
- 关掉本次 hijack 连接**不会**终止容器内进程（`sleep` 继续在 `/proc` 里）：期限 / 取消后容器内 CC 仍归既有 `_force_stop_execution_scope` 屏障与容器清理，收集器不另造停止生命周期（Codex：owner 语义不变）。

### 7.3 验证

- 单测（§7.5 处置后的最终数）：`test_startup_fix_2_host_collected.py` 40 passed（假 daemon；含 daemon 侧连接重置 → 记 `stream_error`、截断帧不落盘、仍以 inspect 为准，以及 §7.5 各缺陷的用例）；`test_startup_fix_2_engine_exec_docker.py` 8 passed（本机 Docker 29.4.1 用 `python:3.12-slim`；验证机 29.8.1 用在场的 conan 镜像 `RH2_EXEC_TEST_IMAGE=…`）；`test_startup_fix_1_activation.py` 20 passed；验证机三文件合计 68 passed。
- 本机五目录 **1691 passed / 1 skipped**（含 `test_w3b_sandbox_docker.py` 14 例真容器；§7.5 处置后的最终一轮）；双 lane 全绿（A 463p/343s、B 806p/0s）；ruff 通过。
- 真机验收（同 §6.4 的四个场景重跑，`runs/base_probe_fixes_20260923/remote/acc3_*/`；§7.5 处置后的最终代码再跑 normal / time_budget = `acc4_*/`，期望项全部通过）：normal 退出 0、`exec_state=exited`、`inspect={Running:false, ExitCode:0}`、11 822 B 完整、`message_start` 3 = 桩请求 3、解释器 / 模型可见面事实全同 §6.4；time_budget -1 / `time_budget` partial / `inspect.Running=true`、容器内残留 1 个 claude 进程由 `pkill -u agent` 收口；max_turns 退出 1（inspect ExitCode=1）、`result.subtype=error_max_turns`；cut_stream 退出 1、CC 不重试（与 §6.4 一致）。全部期望项通过（max_turns 剧本不含解释器项，同前）。

### 7.4 未覆盖 / 残余

- daemon 重启、daemon 暂停、并发字节精确、退出与期限竞态、信号打到收集器进程——交给独立对抗验证（Opus 5.5 子代理，验证机），结果见 §7.5。
- `200 + chunked` 的 exec start 兼容分支只在假 daemon 上测过（29.x 带 `Upgrade` 头时总是 101）。
- settle 上限 10 s 是经验值：流 EOF 后 daemon 正常几十毫秒内记下终态；超过上限仍 `Running=true` 视为连接丢失（typed），不会把慢 daemon 误判成完成，只会把极慢的终态记录误判成丢失（保守方向）。
- 收集器不终止容器内进程（设计如此）：期限 / 取消 / 连接丢失后的 CC 由 `_force_stop_execution_scope` 与容器清理收口，这一段没有改。

### 7.5 独立对抗验证（Opus 5.5 子代理，验证机 Docker 29.8.1 + 本机 29.4.1，2026-09-24）与处置

探针脚本 `rh2/experiments/base_probe_fixes_20260923/review_probes/`（未跟踪），结果 `runs/base_probe_fixes_20260923/adversarial_ir1/`。**核心不变量成立**：7 个场景、几百次收集，没有一次在不该给退出码时给出 `exited`；所有 `exited` 的码都来自同一 exec 的 inspect 且与实际一致。

| 场景 | 观测 | 结论 |
| --- | --- | --- |
| 流式收集中 `systemctl restart docker` / `kill -9 dockerd`（live-restore 关 / 开各一遍） | 4 例都是 `inspect_failed`（settle 上限 10 s 内 48 次 inspect 全失败 / 404），无退出码；live-restore 关时容器 143 退出、开时 `sleep` 仍活 | 符合设计（typed 收口） |
| `kill -STOP/-CONT dockerd` | 流中途暂停 5 s：只是停顿，300 行 / 20 MiB 全到、`exited`；期限内暂停：`time_budget` 5.0 s 返回，有界 inspect 2.0 s；settle 期间暂停 15 s：`inspect_failed`（偏安全，实际已完成的执行被 typed 收口）；create 与 start 之间暂停 40 s：**未包装的 `TimeoutError`**（D1）；CONT 后没有"幽灵启动" | D1 缺陷，其余符合设计 |
| 容器 `kill -KILL` / `stop`（有 / 无 `--init`）/ `rm -f` / `restart` / `pause` 跨期限 | 全部 `exited 137`（`rm -f` 后 inspect 404 也不给错码）；`pause` → `time_budget`；`docker stop` 时 exec 进程收不到 SIGTERM（随 PID 命名空间被 KILL） | 符合设计 |
| 6 路并发、各 3 MiB stdout + 3 MiB stderr、随机块交错、0x00–0xff、单段 298 KB 无换行、退出码各不相同 | 24/24 sha256 与容器内一致、无串扰；真实 daemon 单帧最大 32 KiB | 符合设计 |
| 退出与期限竞态（deadline 1.0 s，进程约 1.0 s 退出，120 次） | 只有 `exited 7` 或 `time_budget -1`，无错码无异常；7 次 `time_budget` 时进程其实刚退出 | 设计接受的竞态结局 |
| SIGINT / SIGTERM / SIGHUP / SIGKILL 打到运行收集器的 Python 进程 | SIGINT 走 `CancelledError` 路径（事实 cancelled）；默认处理的 TERM/HUP 直接终止（无 finally）；宿主无僵尸；容器内 exec 仍在跑（归屏障）；dockerd 侧 hijack socket 约 125 s 后由 GC 释放，不累积（旧 CLI 路径同样） | 符合设计 |
| 代码审读疑点复现 | 帧头跨 chunk 边界正确；settle 中 inspect 间歇 500/404 后仍得正确终态；`writer.close()` 无 ResourceWarning / fd 泄漏；收集器停顿 5 s 不丢尾部（假设被推翻）；1 MiB tmpfs 写满 → `write_error`、退出码仍可信 | 符合设计 |

**缺陷与处置（全部已修，均有用例）**：

| 编号 | 问题 | 修法 |
| --- | --- | --- |
| D1 / P2 | `engine_hijack` 起流阶段的超时 / 连接重置原样抛 `TimeoutError` / `ConnectionResetError`，经正式编排实测是 `pre_finalize_failure_unclassified` **整 run 停机**，而同一故障在 create 阶段只作废本条 | 与 `engine_request` 同样包成 `EngineApiError` → `SandboxExecError` → `harness_bootstrap_failed`；`_read_http_head` 改抛可包装的 `ConnectionError` / `ValueError`；用例：/start 永不应答、/start 被重置，各经真实 driver 归因 bootstrap 失败 |
| D7 / P2 | 日志追加写（`"ab"`）+ 目录按跨 retry 恒等的 execution id → 重派发的两次尝试混进同一文件，事实只计本次字节却报 complete | `_open_log` 改 `"wb"`（每次尝试从空文件开始）；`_harness_log_dir` 再按 `physical_attempt_id` 分子目录 `…/harness/<attempt>/`（消费者按 audit 里的路径读，不猜路径）；用例：预置旧内容被替换、目录按 attempt 区分 |
| D3 / P3 | 期限后的那次 inspect 里被外层取消：`cancelled` 却带 `exit_code=-1` | 取消分支置 `exit_code=None`；用例：慢 inspect + 取消 |
| D2 / P3 | 畸形 chunked：create 阶段抛未包装 `ValueError`；流中途时 progress 停在 `streaming` | `engine_request` / `engine_hijack` 包 `ValueError`；`_FrameSource` 把 `ValueError` 当流结束记 `stream_error`；未知异常路径记 `stream_error:<type>` 后原样传播（不包、不吞） |
| D4 / P3 | `_TIME_BUDGET_INSPECT_SECONDS` 按阶段计时，最坏约 8 s | `engine_request` 改为整次请求一个 `wait_for` 上限 |
| D5 / P3 | 退出码没有上限检查 | `0 <= code <= 255` 之外一律 `inspect_failed` |
| D6 / P3 | OCI 启动失败（工作目录不在、bash 不在 PATH）被报成 `exited 127`、daemon 错误文本进 stdout 文件 | `Running=false` 且 `Pid=0` 且码非零 → `exec_never_started`（保留 daemon 合成码与 stdout 尾部）→ 启动函数抛 `SandboxExecError` → `harness_bootstrap_failed`；真 daemon 用例：工作目录不存在 |
| D9 / P3 | `docker_socket_path()` 只看 `DOCKER_HOST`，与用非默认 context 的 CLI 分家 | `DOCKER_HOST` 未设时按 `docker context inspect` 的 endpoint（进程内缓存），再退到默认路径 |
| D12 / P3 | 测试打补丁的 `_EXEC_SETTLE_SECONDS` 无效（默认值定义时绑定） | `settle_seconds=None` 时调用时取模块常量；`_ENGINE_REQUEST_TIMEOUT` 同理；用例断言耗时 |
| D13 / P3 | 截断的 chunked 响应体被当完整 | 终止 chunk 之前 EOF → `IncompleteReadError` → `EngineApiError`；用例 |
| D10 / D11 | 类型非 1/2 的帧被静默丢弃；超大帧约 3 倍内存 | 不改：真实 exec 只有类型 1/2，daemon 单帧 ≤ 32 KiB（记录为已知边界） |

子代理对生产代码零改动；远端资源全部清理（探针容器 0 残留、无自建网络、live-restore 已恢复关闭、tmpfs 已卸载）。
