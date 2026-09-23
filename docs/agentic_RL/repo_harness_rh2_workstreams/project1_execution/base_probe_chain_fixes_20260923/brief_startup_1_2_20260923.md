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
