# Brief：E1 同一执行内的重复权限初始化（I25，T1 窄优化）

2026-09-24 / Claude（A 线）。**状态：设计定稿，随后实施；不含 E1+（镜像层预置属主，需 B 配合、随目标存储模式测量）。** 依据：[第六组 README §2 E1](README.md)、[A 方向检查 §2.3](claude_a_direction_review_20260922.md)（三处 chown 属实；重复 chown 是小头、首次整树 copy-up 是大头）、[Codex 方向复核](codex_direction_review_20260922.md)（E1+ 四点）、[README §8.1 第 3 条](README.md)（E1 不依赖 #4；同容器消除重复初始化，仍保持其它直接入口正确）。

## 1. 同一执行里现在发生什么（生产 profile 路径）

| 序 | 位置 | 命令 | 超时 |
| --- | --- | --- | --- |
| ① | `generate.py` materialize → `run_trusted_init(rollout_trusted_init_script(profile))` | root：按固定 uid 建用户 + safe.directory + `chown -R /home/<agent>` + `install -d /rh2` + `chown -R <workdir>` | `init_timeout_seconds`（900） |
| ② | `bringup.ClaudeCodeDriver.run` 装完 CLI 后 | root：`id agent \|\| useradd … && chown -R agent:agent /home/agent <workdir> && git config … && id agent` | 900 与剩余预算取 min |
| ③ | `bringup.launch_claude_code` 开头 → vendored `slime.agent.sandbox.ensure_agent_user` | 同 ② 的命令 | 60（vendored 写死） |
| ④ | vendored `ClaudeCodeHarness.write_config` | `chown -R agent:agent /home/agent/.claude /home/agent/.claude.json`（两个小文件） | 60 |

②③ 的 shell 结合是 `(id \|\| useradd) && chown -R …`：用户已存在也照样整树 `chown -R`。①②③ 各一遍 `/home/agent` + `/testbed` 的递归 chown；legacy（无 profile）路径只有 ②③④。④ 很小，不动。

## 2. 改法：一个完成事实，两处复用

- **完成事实**由 ① 建立：`rollout_trusted_init_script` 在成功 chown 之后写 `/rh2/agent_user_ready`（root:root 0644，内容 `uid=<uid> workdir=<workdir>`；`/rh2` 本就是 root 0755，agent 造不出这个文件）。legacy 路径由 ② 在成功后写同一文件（同样 root 执行；先 `install -d -m 0755 -o 0 -g 0 /rh2`）。
- **复用**：② 与 ③ 改为先做**只读核对**——`/rh2/agent_user_ready` 存在且 uid/workdir 与本执行一致，`id -u agent` = uid，`stat -c %u <workdir>` 与 `stat -c %u /home/agent` = uid（非递归，不触发 copy-up）——通过则跳过 `chown -R`，只保留 `git config --system --add safe.directory '*'`（幂等）与 `id agent`；任一项不符则回退到原整条命令并记 `recheck_failed`。
- ③ 不改 vendored `ensure_agent_user`：`launch_claude_code` 改调 RH2 的 `ensure_agent_user_once(sb, workdir, uid)`（新函数，放 `bringup.py`），它在核对失败时调用 vendored 原函数——vendored `run_agent` 直接入口、其它 harness 仍走原函数，行为不变。
- 不用"用户存在"代替权限已正确：跳过的条件是"可信初始化已成功 chown"这个 root 写下的事实 + 顶层属主复核；两次初始化之间只有 root 的装 CLI（`/usr/local`）与 `write_config`（`/home/agent/.claude*`，随后自 chown），不改 `/testbed` 属主。

## 3. 记录

- ① 已记 `trusted_init_seconds`；②③ 各记 `agent_user_init: {"mode": "reused"|"chown"|"recheck_failed", "seconds": …}` 进 `HARNESS_LAUNCH_FACTS`（随 audit 落盘），满足"记录实际 chown 调用和时间"。

## 4. 验收

- 单测（假 sandbox 记录 exec 命令）：profile 路径 ①后 ②③ 零次 `chown -R`；legacy 路径（无标记）命令与改前逐字相同；标记在但 `stat` 不符 → 回退整条命令且 `mode=recheck_failed`；`write_config` 不变；uid/workdir 不一致的标记视为无标记。
- 真容器（`RH2_EXEC_TEST_IMAGE`，本机 Docker）：跑 ① 后按 ③ 路径启动一个以 agent 身份写 `/testbed` 与 `$HOME` 的命令成功；`/rh2/agent_user_ready` 对 agent 只读；记录 chown 次数 1 与三段耗时。
- 不验收：overlay2 首次 chown 的 copy-up 成本（E1+，目标机）；grader（不同容器/uid，不在本片）。

## 5. 边界与不做的事

不改 grader 初始化；不改 ④；不预装 CC、不复用 HTTP 连接、不改轮询/网络（README E1 明确另看）；不改 profile 的 uid/能力集；与 B 派生镜像的属主配方无交集（E1+ 时再对齐）。

## 6. 实施记录（2026-09-24，Claude；单测与真容器通过，待全量回归与 Codex 复核）

- **与 §2 的一处偏离**：driver 预建（②）没有拆成"核对 exec + 整条命令 exec"两次，而是**一次 exec** 的脚本 `agent_user_init_script`：脚本内先只读核对，通过 → `RH2_AGENT_USER_INIT=reused` 退出 0；否则逐字执行原整条命令（`DRIVER_AGENT_USER_INIT_CMD`，与 vendored 文本相同）→ 写标记 → `=chown`。原因：保持 driver 引导只有这一次 exec，超时上限（`min(900, 剩余)`）、R3(3) 的分数秒期限判定与失败归因完全不变；现有 `test_budget_deadline` 等用例无需改动。
- **launch 路径（③）**：`bringup.ensure_agent_user_once` 先跑 `agent_user_recheck_script`（只读，退出码恒 0），`ok` → 跳过；否则原样调用 vendored `ensure_agent_user`（文本、60s 上限不变）。vendored 模块零改动；`write_config`（④）不动。
- **完成标记**：`rollout_trusted_init_script` 在 workdir chown 之后、`RH2_INIT_OK` 之前写 `/rh2/agent_user_ready`（`uid=` / `workdir=` 两行，root 0644；失败 → `RH2_INIT_ERROR=ready_marker_failed` 退出 4）。`scripts/sandbox_probes/rollout-trusted-init.sh` 已重新 dump。
- **记录**：launch facts 新增 `agent_user_init_bootstrap`（②）与 `agent_user_init_launch`（③），各含 `mode`（`reused` / `chown`）、`recheck` 状态、`seconds`。
- **验收**（`tests/adapters/test_e1_agent_user_init.py`，10 例）：脚本形状（标记位置、核对脚本无 chown/useradd/find、单次脚本内嵌原命令且只含一处 `chown -R`）；launch 路径 `ok` 跳过、五种不通过状态回退到逐字相同的 vendored 命令；driver 一次 exec、两种模式进 facts；**真容器**（`python:3.12-slim`，本机 Docker）：可信初始化 → 核对 `ok` 且 `AGENT_UID=54321`；agent 写不了 `/rh2`；改顶层属主 → `owner_mismatch`、改回 → `ok`；`/other` → `workdir_mismatch`；删标记 → `no_marker`；driver 脚本无标记时 `chown`（文件 ctime 变）、有标记时 `reused`（ctime 不变 = 没再 chown）。相关既有用例（deadline、host-collected、batch A 归因、w3b profile）115 + 43 passed。`test_startup_fix_2_host_collected` 的"零 exec"断言改为"只允许这一次只读核对"。
- **没有测**：overlay2 上首次 chown 的 copy-up 成本与目标机耗时（E1+）；grader 侧不变。
- **全量回归（2026-09-24）**：五目录（Docker 在线）首轮 1759 passed / 1 failed——`test_startup_fix_1_activation` 的假 sandbox 没有 `exec` 方法（该测试把 vendored 引导替身掉，从未需要 exec），给替身补一个返回空输出的 `exec`（= 核对不通过 → 走已替身的 vendored 路径）后再跑 **1760 passed / 1 skipped**；双 lane A 463p/343s、B 806p/0s（E1 改动后首轮即通过，测试修正只涉及 adapters 目录）；ruff 通过。计数含 B 线同工作区未提交的新增测试。
