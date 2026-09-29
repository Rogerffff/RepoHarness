# R2E 探针链路检查与适配（2026-09-29 夜）

Claude（B 线 R2E 生命周期批，探针链路子任务）。回答"R2E 题明天能不能走统一探针链路、缺什么"，并在 CPU 上用真实 Claude Code 2.1.205 + 桩端点把 R2E 求解链路跑通。没有启动模型、没有用 GPU、没有调用付费 API；只新增 `rh2/experiments/r2e_lifecycle_20260929/` 下的文件，没改共用探针脚本与 `rh2/src`，没提交。远端只在 `/work/r2e/probe_proto/` 下工作，容器与网络带 `rh2.r2e_lifecycle=probe_proto` 标签，收尾零残留。代码快照 `0ed0af10ab4c`：本任务依赖的 23 个文件与本机逐字节一致（`sha256sum -c` 通过）。

状态用词：**已实施** = 代码写好；**已验证** = 本机 / 远端实跑过；**建议** = 未定，需要决定。

## 0. 结论

**R2E 题明天可以走统一探针链路，但要换求解入口、改一处派发、评分沿用 `replay_grade run`。**

1. **入口**：R2E 题用原型 `r2e_solve_attempt.py`（已实施、已验证）。它继承共用入口 `solve_attempt.Attempt`（CC 启动、`--max-turns`、窗口 / 输出注入、轨迹与会话目录收集、清理都是共用那份），只换 R2E 必需的层：正式 R2E 任务面与覆盖表、census 基线与 R2E 预检、root 命令走可信前缀、正式静止屏障 + census 冻结导出。模型端点不变：容器 → relay → 宿主 `model_gateway.py` → 上游（今晚是桩，明天换自部署 adapter 或供应商，入口不用动）。评分：`scripts/replay_grade.py run --candidate patch-dir:<attempt>/candidate --image-overlays <覆盖表>`。
2. **今晚已验的题**（真实 CC + 网关 + 桩 + 正式 relay / 专用网络 / profile）：aiohttp `61833518`（普通题，初态带 4 个已跟踪改动）全链通过，候选分数与 noop 相同（0，45/47）；orange3 `4014f248`（编译题）agent 改 `.pyx` 并以解题身份重编成功，冻结补丁带着新 `.so`，全新 grader 评分 **1（27/27）**；同一改动不重编的候选 **0（26/27）**，差别只在构建产物，失败键是 `TestEqualFreq.test_below_precision`；同批 gold 1（27/27）、noop 0（26/27，同一失败键）——grader 加载的是新产物。orange3 的评分是在只放宽 grader 一段时限后得到的（见第 4 点第 3 项）。R2E 预检三项以 agent 身份全部通过（入口自己跑一次、经 CC 的 Bash 工具再跑一次，三个 attempt 都是）。链路本身不挑题：覆盖表与 prepared 里有、预检能过的题都能走；逐题能否进探针仍以 `board.json` 为准。
3. **旧路径不能直接用**：`solve_attempt.py` 构造 R2E 任务面时就被拒（`prepared_task_face.py:485-490`，防止回退到隐藏测试与修复提交可见的来源镜像）。硬绕（`--image-override`）的话，git diff 导出会漏掉 `.gitignore` 忽略的构建产物——orange3 实测旧口径只导出 `.pyx`，漏掉 `_discretize.c`、两个 `_discretize*.so` 和 `.o`，编译题的正确修复会被判 0；而且旧入口的 root 命令按镜像 `PATH` 找程序，首项是 agent 可写的 `/testbed/.venv/bin`（按镜像配置与命令形态推断，未做利用实验）。
4. **明早必须补的**（都不大，但不补 R2E 题跑不起来或分数无效）：
   - `run_matrix.py`（共用派发器）按题选求解入口、评分带 `--image-overlays`、R2E 与 SWE-Gym 各自的 prepared summary：约 15–25 行（§4 D1）。不改的话 R2E 题要么求解被拒，要么回放落到来源镜像、候选阶段预检失败不评分。
   - 派生镜像要到 GPU 机：44 张（覆盖表 devcheck 版）按 `Size` 合计 75.4 GB（含共享层），rollout 不拉镜像。本机是经典 overlay2 存储，image ID = 配置摘要，`docker save` 再 `docker load` 按 Docker 内容寻址的一般行为会保留 ID（今晚未实测；GPU 机若用 containerd 存储要先核），覆盖表可沿用；重建会换 ID，覆盖表与 noop / gold 资格都要重出。
   - 预算要算上 R2E 的固定开销（§1 第 7 行）：`.venv` 在 `/testbed` 里，rollout 可信初始化、回放候选阶段、grader 控制面保护各做一次 `chown -R`，overlay 会整树复制。本机负载下 orange3 的 rollout 初始化 428–456 s，回放候选阶段 436–635 s（又一次可信初始化），grader 控制面保护 487–517 s；而 grader 那一步有 300 s 硬时限，今晚我的两次 orange3 首轮评分与协调者账本里（截至 19:15 UTC）datalad 10 行、orange3 6 行评分都因此记 `infra_failure`（不是模型或候选问题）。orange3 一次尝试在本机约 9 分钟求解 + 18–20 分钟评分（放宽时限后）；aiohttp 70 s + 75 s。
5. **顺带发现的两个生产链问题（A 线，今晚只记录、未改）**：
   - **正式链直接评分 R2E 冻结补丁会停批**：rollout 基线在 git sanitize 之后取，sanitize 删了 `.git/logs/HEAD`；grader 的全新容器不做 sanitize，重建基线的排除区路径集不同 → `baseline_digest_mismatch`（`BaselineIntegrityError`，run-halt）。已验证：aiohttp 那次的冻结补丁按正式语义直接评分被拒，排除区摘要分别等于 sanitize 后 / 前的值（§3.4）；orange3 四次候选回放的基线摘要也与求解侧不等、条目相等。generate.py 把它升成 `FatalExecutionInfrastructureError`（`generate.py:5515-5530`），即正式链照现状跑 R2E 会在第一次评分时停批。`replay_grade run` 不受影响（它在未 sanitize 的候选容器里重算基线），所以不挡明天的探针。SWE-Gym 镜像未测（本机没有），sanitize 会删远端 refs 与 logs、repack，推测同样不等。
   - **静止屏障用 root 在 agent 属主的仓库里跑 `git status` / `git diff`**：可信前缀只清环境变量，不清仓库配置。一次性容器最小复现：agent 写进 `.git/config` 的 `core.fsmonitor` 与 `diff.external` 都以 uid=0 被执行；加 `-c core.fsmonitor=false`、`--no-ext-diff` 的对照都没执行（§3.4）。未在正式 profile 容器里复现；属 E2b 同类边界（root 不执行候选可控程序）。

## 1. 链路差异清单

"旧"= `base_probe_20260922/solve_attempt.py` + `run_matrix.py`（09-25 已接 A 线修复的版本）；"正式"= `adapters/slime/generate.py` 的 fa_formal rollout + `grading/manager.py`；"原型"= `r2e_lifecycle_20260929/r2e_solve_attempt.py`。**影响**列标"无效"= 会让 R2E 结果无效；"不可比"= 与正式链或其它批次不可比；"阻断"= 跑不起来。

| # | 项 | 旧探针路径 | 正式链 | 原型 | 影响 |
| --- | --- | --- | --- | --- | --- |
| 1 | 任务面与镜像 | `rollout_spec_from_view(view, …)` 不带覆盖条目（`solve_attempt.py:174`），R2E 题抛 `PreparedTasksError`（`prepared_task_face.py:485-490`）。`--image-override`（`solve_attempt.py:176, 234-235`）只豁免 digest，不绑定覆盖表、不做评分面互检 | `PreparedTaskFace` + 覆盖表（路径与摘要成对，`prepared_task_face.py:508-605`）；R2E spec = 派生镜像 image ID、`image_local_build`、`.venv` 激活与前缀（`:485-502`）；覆盖条目与评分面互检（`:441-463`）；rollout 按 ID 启动，豁免 registry digest（`generate.py:5171-5172`） | 同正式；另核"容器实际 image ID = 任务面 image = 覆盖表 ID"，三次实跑都相等 | 旧：**阻断**；硬绕到来源镜像则隐藏测试可读、修复提交可达 → **无效** |
| 2 | 解释器与激活 | 09-25 已接：写 `spec.env_activation_script`、启动前核对带激活文件、激活核对、逐次注入（`solve_attempt.py:305-311, 315, 327, 333`）；但 spec 来自第 1 行，R2E 到不了 | `R2E_VENV_ACTIVATION`、前缀 `/testbed/.venv`（`prepared_task_face.py:426-434`）；激活核对在首次 census 之后（`generate.py:3936-3938`） | 同正式顺序：census → 预检 → 激活核对。实测 agent 的 `python`、`sys.executable` 都是 `/testbed/.venv/bin/python` | 接上第 1 行即无差异 |
| 3 | 泄漏预检 | 没有 | rollout 不跑（只在回放候选阶段跑，`replay_grade.py:360-367`；[R2E actor 接线 §4](../r2e_actor_wiring_20260925.md) 第 3 点已登记建议加进 generate.py）；启动前探针的隐藏路径只有 `/root`（`sandbox_profile.py:347`），不含 `/rh2_private` | census 之后、CC 启动前以 agent（uid 54321）跑正式预检脚本（`r2e_grading_scripts.py:208-235`），失败不启动；剧本第一步再经 CC Bash 工具跑一遍 | 没有预检就证明不了隐藏测试不可读、修复提交不可达 → 可信性无保证 |
| 4 | root 命令的执行环境 | `sh()` 与导出都是 `docker exec [-u root] <c> bash -c`，继承镜像 ENV（`solve_attempt.py:120-131, 424, 441-442, 459, 475`）。派生镜像 `PATH` 首项是 `/testbed/.venv/bin`（实测 image `Config.Env`），可信初始化把 `/testbed` 整树交给 agent → agent 放同名 `pkill` / `ps` / `git` / `tar` 就会被 root 执行，静止判断与导出都能被操纵 | E2b 已修：工作区通道用 `TRUSTED_ROOT_EXEC_PREFIX`（`generate.py:2441-2444`，`manager.py:1002-1005`） | 所有 root 命令走可信前缀；共用 `solve()` 里唯一一处 root `bash -c`（打包 CC 会话目录）在进程内改写，记入 `trusted_root_exec_rewrites` | 旧：安全边界缺口；R2E 特有（SWE-Gym 镜像 `PATH` 前段是 conda 目录，可信初始化不把它交给 agent；未逐镜像核对） |
| 5 | 候选导出 | `git add -N . && git diff --binary <stash-create 基线> -- . <排除基线未跟踪清单>`（`solve_attempt.py:468-475`）。`.gitignore` 忽略的文件进不了补丁；基线未跟踪清单（`git ls-files --others --exclude-standard`，`manager.py:354-357`）里的文件被改也按路径排除 | 静止屏障（`quiescence_barrier.py`）→ `export_frozen_patch`：census 字节比较，不经 git（`patch_exporter.py:1-13, 162-248`）；R2E 政策只排除 `.git/ .harness/ .venv/` 与缓存目录（`baseline_manifest.py:122-125`） | 同正式（正式屏障 + 正式导出 + `classify_frozen_patch`） | 旧：编译题漏掉构建产物 → 正确修复判 0，**无效**（orange3 实测，§3.2） |
| 6 | 候选评分方式 | 空补丁送 noop，否则 `patch-dir:<attempt>/candidate`（`run_matrix.py:171-187`），**不带 `--image-overlays`**：回放用 `public.image`（来源镜像，`replay_grade.py:324-327, 467-478`），候选阶段预检必失败（来源镜像解释器 agent 跑不动、隐藏测试可读；按代码推断，未实跑），不评分。`--derived-image` 整批镜像与逐题覆盖表冲突时回放拒绝（`:783-784`） | rollout 冻结补丁 + rollout 基线 → `FrozenDeltaSource` → grader 先用 census 重建基线、摘要必须相等（`manager.py:3021-3100`），再按字节写入（`:3123-3214`） | 冻结补丁（权威）→ 渲染成 git 补丁 → `replay_grade run patch-dir` + `--image-overlays`；回放容器重新 `git apply` + census 导出，核对与求解侧逐条一致（三次全部一致） | 回放口径与正式 grader 同一 manager、同一 R2E spec / 投影、同一派生镜像 ID，**可比**；正式"直接评分"口径当前对 R2E 走不通（§0 第 5 点）。另：`candidate_from_spec` 用 `read_text` 读补丁（`replay_grade.py:804-810`），通用换行会改写 `\r`——旧 git diff 口径碰到 CRLF 文件会 apply 失败（机制推断，未实测）；原型把含 `\r` 或非 UTF-8 的文件强制按二进制出补丁 |
| 7 | 预算参数 | 默认 wall 1800 s、`--max-turns 60`、`--max-context-len` 必填、`--max-new-tokens` 可选（`solve_attempt.py:582-586`）；派发并发 3、评分 5400 s（`run_matrix.py:221-225`）；网关每会话 300 请求（`model_gateway.py:59`）。09-22 实跑 60 回合 / 200 请求 / 1800 s / 131072 | adapter 回合预算闸门（第 26 次 403）、600 s、窗口由 `SlimeBindingConfig.max_context_len` 单点给出（缺省 0 = 不注入，`generate.py:2058`）（[交接 §11](../base_model_probe_20260922_aline_handoff.md)） | 继承 `solve()`，参数与旧入口同名同义；实测注入生效：每个请求 `max_tokens=4096`、工具只有 Bash/Edit/NotebookEdit/Read/Write，CC `contextWindow=32768`。R2E 额外开销见右 | 与训练链**不可比**（旧结论不变）。R2E 另要算：①可信初始化 `chown -R /testbed`（含 `.venv`）：aiohttp 20 s，orange3 428–456 s，协调者 devcheck 里 datalad 471–505 s；②回放候选阶段再做一次（候选阶段预算 900 s）；③grader 控制面保护的 `chown -R` 有 300 s 硬时限（`GradingEnvSpec.env_reset_timeout_seconds`，`manager.py:646, 3354-3359`；CLI / 环境变量调不了），本机并发下 orange3 实际要 487–517 s，超时记 `infra_failure`；④编译题构建（orange3 单扩展，整个 CC 会话含构建 15 s）；⑤CC Bash 工具单次上限 10 分钟 |
| 8 | 已登记的 A 线修复（A-B2） | [A 线状态页](../a_line_status.md) 第 65 行仍记 `blocked`，但 09-25 任务二已实施：adapter 按生产顺序装包装与溢出 400、`solve_attempt` 正式激活 / 逐次注入 / 宿主收集、网关断流中止，完成复核 F1–F4 已修（[任务二结果 §探针接线](../task2_swegym_dev_conditions_20260925/results.md)）——状态页过时。之后的生产修复（E2a 批量 census、G1、AR1 等）凡经生产函数调用的自动生效；E2b 没进旧入口的 root 命令（第 4 行） | — | 继承 `solve()`，接线状态与 SWE-Gym 路径相同；E2b 补上；E1 生效（`agent_user_init_launch=reused`，不再整树 chown） | 未验证的仍是 GPU 项：真实模型的工具调用 / 推理解析、真实窗口 |
| 9 | 其它 | 基线 = `git stash create`（F4）；relay 每 attempt 一份；无 census | census 基线；relay 每 run 一份；会话面撤销 + drain 后屏障 | census 基线（aiohttp 初态 4 个 `M` 文件，导出只含 agent 追加的行）；relay 每 attempt 一份；屏障的"会话面已排空"由入口在 CC 退出后置真 | `excluded_pathset_changed=true` 在求解侧常见（`.git` 索引、`.venv` 字节码），不影响候选 |

## 2. 原型（已实施）

文件都在 `rh2/experiments/r2e_lifecycle_20260929/`：

| 文件 | 作用 |
| --- | --- |
| `r2e_solve_attempt.py` | R2E 求解入口。`R2EAttempt(solve_attempt.Attempt)`：覆盖 `run()`（按 generate.py 顺序调同一组正式函数，逐段注释对应关系）、`sh()`（root 走可信前缀）、`export_candidate()`（正式屏障 → `export_frozen_patch` → 分类 → 渲染 git 补丁）；沿用父类 `solve()` / `cleanup()`。参数与 `solve_attempt.py` 同名（多 `--overlays`、`--extra-label`、`--legacy-gitdiff-compare`）。候选记录保留 `export_ok` / `empty` 两键，run_matrix 的评分分支可直接沿用。落盘：`attempt.json`、`frozen/{baseline_manifest,frozen_patch,classification}.json`、`candidate/<iid>.diff`、轨迹、`cc_home.tgz` |
| 冻结补丁 → git 补丁 | `render_git_patch()`：修改 / 删除路径的基线字节取自同一派生镜像的一次性容器（root、不联网、可信前缀），逐个按基线清单摘要核对；宿主临时**裸**仓库里用 `hash-object --no-filters` / `update-index --index-info` / `write-tree` 建两棵只含变更路径的树，`diff-tree -p --binary --full-index --no-renames` 出补丁（不读任何工作区、仓库配置、属性或钩子）；自检 `apply --cached` 后的树必须等于冻结后侧。本机与远端 git 2.34 单测：文本改、初态脏文件改、被忽略的未跟踪 `.so` 改、增删、mode、软链、非 UTF-8、CRLF、带空格路径，`git apply` 后逐字节 / 逐 mode 相等（含 `read_text` 往返） |
| `r2e_probe_e2e.py` | CPU 端到端夹具：剧本 → 桩 → 网关 → 求解 → `replay_grade run` → 往返核对 → 对照（gold / noop）→ 残留核对。回放子进程的 docker 调用经一个只加 `--label rh2.r2e_lifecycle=probe_proto` 的 shim |
| `scenarios/*.json` | 三个剧本：aiohttp 普通改动；orange3 `edit_pyx`+`build`；orange3 只 `edit_pyx`（命令原文取自 `r2e_actor_20260925/commands/agentpath_orange3_4014.json`，记录文件与命令摘要） |
| `grade_frozen_direct.py` | 对照：按正式链语义直接评分求解侧冻结补丁（`FrozenDeltaSource` + 与 `PreparedTaskFace.grading_spec` 同构造的 spec） |
| `replay_grade_budget.py` | 评分预算包装：只放宽 `env_reset_timeout_seconds`，其余逐字执行 `scripts/replay_grade.py`（§3.2 用于 orange3 重评） |

## 3. CPU 端到端验证（已验证）

共同条件：R2E CPU 机，`prepared_dc`（44 题）+ `overlays_devcheck.jsonl`（`sha256:69959557…`），CC 平台包 2.1.205，正式 rollout / grader profile 缺省值（2 CPU / 4 GiB / `/tmp` 1 GiB），桩与网关端口 18190–18197，长任务 `systemd-run --unit=r2e-probeproto-* --collect`。窗口 32768、输出 4096、`--max-turns` = 剧本步数 + 3。

### 3.1 普通题：aiohttp `618335186f22834c0d8daabcf53ccf44d42488a2`

剧本：预检 → Read → Edit（`aiohttp/__init__.py` 一行注释）→ Bash 给初态已被改动的 `aiohttp/worker.py` 追加一行 → Write 新文件 → `git status`。

- 求解：`result=ran`、CC 退出 0、`subtype=success`、7 个请求全部经网关；各阶段通过（镜像 ID、血缘、sanitize、初始化、启动前核对、census 124 条 0.3 s、预检、激活）；整次 70 s（可信初始化 20 s）。
- 冻结补丁 3 条，正是剧本的三处改动：`aiohttp/__init__.py`、`aiohttp/worker.py`（modify）、`rh2_probe_proto_note.txt`（add）。`worker.py` 的 diff 只有 agent 追加的两行，没带镜像初态的已跟踪改动。旧 git diff 口径（stash-create 基线）导出同样 3 个文件——无构建产物的题两种口径一致。
- 回放评分：`git_apply` 成功，投影包含 3 个路径，**reward 0（45/47）= noop 对照（0，45/47）**；账本补丁摘要 = 渲染摘要；回放容器重新导出的冻结补丁与求解侧逐条相等（3 = 3）；基线条目相等（124 = 124）。
- 清理：`cleanup_ok=true`，三个 run_id 下容器 / 网络为零。

### 3.2 编译题：orange3 `4014f2483e3bab0621c9ae0f994947c008183253`（R-d 验收第 2 点的证据）

同一派生镜像 `sha256:3cab63e6…`（配方 `r2e_derive_v1+sysconfig_v1`）。两个 attempt：**build** = 预检 → 记录构建前产物 → `edit_pyx` → `build` → 记录构建后产物 → 公开复现；**pyx_only** = 预检 → 记录 → `edit_pyx` → 记录（不重编，等同 09-25 的 C2）。

- **agent 身份重编成功**：`BUILD_RC=0`，只 Cythonize `_discretize.pyx`，链接参数 `-L/opt/py/cpython-3.7.9-linux-x86_64-gnu/lib -lpython3.7m`（构建配置修复生效；09-25 同命令在旧镜像上 `cannot find -lpython3.7m`）。in-place `.so` 由 229096 字节 `sha256:9ee458d0…` 变成 229416 字节 `sha256:f1d05c0f…`；agent 进程 `import` 到的是 `/testbed/Orange/preprocess/_discretize.cpython-37m-x86_64-linux-gnu.so`；公开复现 m=4 / m=5 都 `unique=True increasing=True`。
- **冻结补丁带着新产物**：build 的冻结补丁 5 条——`_discretize.pyx`、`_discretize.c`（Cython 输出）、`Orange/preprocess/_discretize.cpython-37m-x86_64-linux-gnu.so`（digest `f1d05c0f…`，= agent 构建后打印的摘要；基线 `9ee458d0…`，= 构建前摘要）、`build/lib…/_discretize…so`、`build/temp…/_discretize.o`。渲染补丁 909 KB，3 个二进制 hunk，自检通过。pyx_only 的冻结补丁只有 `.pyx` 一条（与 build 的 `.pyx` 摘要相同 `2da11037…`）。
- **旧口径对照**：同一容器按旧 git diff 口径导出只有 `.pyx`，漏掉 `.c`、两个 `.so`、`.o`（`.gitignore` 忽略 `*.so`、`_discretize.c`、`build/`）。
- **往返**：build 回放容器重新导出的冻结补丁 5 = 5 逐条相等，基线 1594 条相等，账本补丁摘要 = 渲染摘要。
- **首轮评分**（缺省预算）：两个候选都在 grader 控制面保护（`chown -R` 整棵 `/testbed`）超过 300 s，`failed_to_grade / infra_failure: grading_control_surface_protect_timeout_after_300s`，测试没跑；同时段协调者账本里 datalad 10 行、orange3 6 行是同一结果。
- **重评**（`replay_grade_budget.py` 只把该时限放宽到 1200 s、候选阶段 1800 s，评分语义不变）：

  | 候选 | 冻结补丁 | 评分 | 期望映射 | 测试段 |
  | --- | --- | --- | --- | --- |
  | build（改 `.pyx` + 重编） | 5 条，含新 `.so` | resolved，**1.0** | 27/27 | 9.8 s |
  | pyx_only（只改 `.pyx`） | 1 条 | unresolved，**0.0**（tests_failed） | 26/27 | 9.0 s |
  | gold（对照，只看结果） | — | resolved，**1.0** | 27/27 | — |
  | noop（对照） | — | unresolved，**0.0**（tests_failed） | 26/27 | — |

  控制面保护 487–517 s；回放候选阶段（含又一次可信初始化）554–635 s（首轮 436–459 s），缺省预算 900 s。四次都 `git_apply` / noop 正常、`stage_error` 为空，往返核对两条都逐条相等（5 = 5、1 = 1），收尾零残留。

- **grader 加载的是新产物**：两个候选的 `.pyx` 字节相同（`2da11037…`），同一派生镜像、同一 grader profile、都 `git_apply` 成功；差别只有构建产物（`.c`、两个 `.so`、`.o`，回放投影 `included_paths` 里都在）。评分日志里 `r2e_tests/test_1.py::TestEqualFreq::test_below_precision` 在 build 候选与 gold 下 `PASSED`，在 pyx_only 与 noop 下 `FAILED`（与 09-25 C2 的失败键相同；其余 26 个键四者一致通过）。grader 不做构建（R2E 候选段 `RH2_INSTALL_SKIPPED=1`，`r2e_grading_scripts.py:118-127`），所以这个翻转只能来自重放进评分树的新 `.so`。候选后观测只给包导入路径（`/testbed/Orange/__init__.py`），不直接显示扩展路径。

### 3.3 R2E rollout 预检以 agent 身份通过

三个 attempt 都是两层：入口在 census 之后以 `docker exec -u 54321` 跑正式预检脚本，`RH2_PREFLIGHT_INTERPRETER=ok`、`HIDDEN_TESTS=ok`、`GIT_HISTORY=ok`；剧本第一步经 CC 的 Bash 工具（agent 子 shell、带 `BASH_ENV` 激活）再跑同一脚本，按 `evaluate_r2e_rollout_preflight` 判读 `failures=[]`。

### 3.4 旁证：两个生产链问题

- **sanitize 与 grader 基线重建**：`grade_frozen_direct.py` 把 aiohttp 那次的冻结补丁按正式语义交 grader → `BaselineIntegrityError: baseline_digest_mismatch`（重建 `sha256:d6769c70…` ≠ 基线 `sha256:afbd2da2…`，条目都是 124）。定位：同镜像一次性容器里，sanitize 前后 `.git` 文件 24 → 23（少 `.git/logs/HEAD`）；census 排除区摘要 sanitize 后 = 求解侧基线里的值、sanitize 前 = 回放 / grader 侧的值（`excluded_census_check.json`）。orange3 四次候选回放的基线摘要同样与求解侧不等（`9d3b0899…` 对 `de46bde1…`）、条目相等（1594）。
- **root 执行仓库配置里的程序**：`root_git_config_check.sh`，一次性容器、不联网：agent 设 `core.fsmonitor=/tmp/h.sh`、`diff.external=/tmp/e.sh`，root 以可信前缀逐字执行屏障的指纹脚本（`quiescence_barrier.py:60-65`）→ 两个脚本都记下 `uid=0(root)`；同一容器加 `-c core.fsmonitor=false` 与 `--no-ext-diff` 后都不执行。容器没加正式 profile 的 cap-drop 等限制，只证明"以 root 身份执行"。

### 3.5 证据

本机 `runs/r2e_lifecycle_20260929/probe_proto/`（远端 `/work/r2e/probe_proto/` 同构）：`runs/<场景>/summary.json`（汇总）、`attempt/attempt.json`、`attempt/frozen/`、`attempt/candidate/`、`attempt/legacy_gitdiff/`、`attempt/trajectory.jsonl`、`gateway/<attempt_id>/`（每个请求体与 SSE）、`stub/`、`grade_*/`（账本、评分日志、回放工件；orange3 的 `grade_cc` 是首轮超时，`grade_cc2` / `grade_gold2` / `grade_noop2` 是放宽时限后的重评；aiohttp 的 `grade_direct/` 是正式语义直接评分）；`runs/root_git_config_check/`、`runs/git_path_set_check/`；`tests/`（渲染单测与两个旁证脚本）；`logs/`；`deployed_code_sha256.txt`（远端所用原型文件摘要，与本机一致）。

## 4. 明早需要决定的

| # | 事项 | 建议 | 谁 |
| --- | --- | --- | --- |
| D1 | 统一入口怎么接 R2E | 明天先用 `r2e_solve_attempt.py` + 改 `run_matrix.py`：`tasks_config` 每题加 `entry: r2e` 与覆盖表路径 → `one()` 选脚本、R2E 题不传 `--image-override/--prep-*`、传 `--overlays`；`grade()` 对 R2E 题加 `--image-overlays`；prepared summary 按来源分开或合并准备（`prepare --sources swe_gym_lite,r2e_gym_subset`）；结果行加 `expected_match/expected_total`。约 15–25 行。之后再把 R2E 层的钩子（任务面、census 位置、导出）并回 `solve_attempt.py`，免得两份编排分叉 | 共用入口的单一写入者（任务二线程）改；用户定是否明天就用 |
| D2 | 候选评分口径 | 探针用 `replay_grade run`（git 补丁往返 + 往返核对不一致即停）。正式"直接评分冻结补丁"待 A 线修 sanitize / 基线摘要问题后再切 | 用户知悉；A 线排期 |
| D3 | 预算口径 | 求解侧沿用两款模型共同的回合 / 窗口 / 输出参数；R2E 另外按题记准备开销；numpy `2f4a9650` 评分要 `/tmp` 6 GiB + 内存 12 GiB（按题 `RH2_GRADER_*`，run_matrix 的 `grader.env` 已支持）。评分侧：R2E 大环境题（orange3、datalad）限制并发评分数，或由 A 线开放 `env_reset_timeout_seconds` 配置；今晚的 1200 s 只是 CPU 机上的诊断放宽 | 用户定数值；A 线定是否开放配置 |
| D4 | 暂停开关 | 沿用 `STOP` 文件、清理未确认即停、同 solver 连续 3 次 infra 停；R2E 加两条：往返核对不一致即全局停；同一题评分 `infra_failure` 连续出现就降并发而不是重试 | 用户认可后由派发器实现 |
| D5 | 派生镜像搬到 GPU 机 | 优先 `docker save` 后在 GPU 机 `docker load`（预期保 ID，覆盖表与资格可沿用；落地后逐张 `image inspect` 核 ID）；约 75 GB 量级（按 Size 合计，实际去重后更小） | 用户 / 协调者 |
| D6 | 生产链两项（A 线） | ①grader 重建基线前按 rollout 同一脚本做 sanitize，或把 `.git/` 路径集移出摘要比较（后者动契约，属 T0）；②屏障指纹里的 git 加 `-c core.fsmonitor=false`、`--no-ext-diff` 等，或改成不经 git 的指纹。另：A 线状态页 A-B2 状态过时；generate.py 仍不跑 R2E 预检 | A 线 |

## 5. 限制

- 桩只证明链路与交付：工具调用解析、推理、真实窗口与 count_tokens 仍要在 GPU 冒烟里验。
- 只测了 aiohttp 与 orange3 两题；numpy / pandas 等大仓库的 census 与导出耗时没测（A-C1 的范围）。
- `--legacy-gitdiff-compare` 只作对照：它在 census 之后写 `.git` 对象，并在导出后以 root 跑 git（已关 fsmonitor / 外部 diff，但不防 clean filter），明天真实模型运行不要打开。
- 静止屏障仍是生产实现，§0 第 5 点的 root 执行问题原样存在于原型中（与正式链相同）。
- 首轮 orange3 评分超时后，我停掉了还没开始评分的 gold 对照（单元收到 SIGTERM 时回放候选容器刚建好），按标签精确删除，复查零残留。
