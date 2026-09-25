# Brief：E2 批量 census（I26）与 E4 完成历史释放（I29）——消费者梳理与切片设计

2026-09-24 / Claude（A 线）。**状态：设计稿（2026-09-25 按 [Codex 复核 R6 与 §5/§6](review_next_slices_20260924/README.md) 修订）；只读梳理（sub-agent，本地 `runs/decision_package_20260924/e2_e4_survey/README.md` 与三个本机探针，git-ignore），我核过 census 调用点以 root 无 `-u` 执行、R2E 探针 `WRITE_VENV_BIN=ok` 证据、fork 无关。没有改代码、没跑 Docker / 远端。** 依据：[README §2 E2 / E4](README.md)、[README §8.1 第 5 条](README.md)（先做只读消费者梳理和 Brief，实施按文件 / 函数归属顺序落地；保留扫描语义、活动资源 owner、未消费结果与累计计数）。

## 1. E2：批量 census

### 1.1 现状（源码 + 本机探针）

- 三个调用点共用 `baseline_census.build_census_script`：rollout 基线（`generate.py` materialize）、运行后（`patch_exporter` ← `generate.py`）、grader 重建（`grading/manager.py`）；B 的重放 driver（`replay_grade.py`）另有两处同样调用。都用 `docker exec <c> bash -c …`，**不带 `-u`、不带 `-e`**：root 身份、按镜像自带 PATH 找命令。
- 进程数：普通文件每个 1 个 `$(…)` 子 shell + `sha256sum` + `cut`；软链每个 1 子 shell + `readlink` + `tr` + `sha256sum` + `cut`；执行位用内建 `[ -x ]`。PATH 垫片计数与公式 `2R + 4S + 2 + 2·N_excl(+5)` 一致。
- 规模（1413 份已落盘基线清单）：SWE-Gym 216 题中位 1,276 条 / 最大 2,793；R2E 48 题中位 1,447 / 最大 2,569 → 每次 census 约 2.6k–5.6k 次 exec，每个 attempt 三次。grader 重建阶段 p50 4.57 s（431 次评分、4 路并发），其中起进程占比未测。
- `BASE_UNTRACKED_SNAPSHOT_SCRIPT` 不是逐文件的（常数个进程 + 一次 `git ls-files`）；fa_formal 模式下没有读者。

### 1.2 必须原样保留的语义

不跟随软链、目录不进清单、`LC_ALL=C` 排序、按换行分隔；分类先 `-L` 再 `-f`，其余 UNSUPPORTED；软链摘要 = readlink 输出删全部换行后再算；执行位按 root `[ -x ]`（= 任一 x 位）；EXCL 只列普通文件、不剪排除区里的缓存目录（B 的 R2E prewarm 测试依赖）；缓存计数目录只数顶层、文件只数普通文件；无 EXCL 行时排除区摘要 None；宿主解码 `errors="replace"`；脚本无 pipefail。

边界输入现状（本机实测；E2a 原样保留）：文件名含 TAB → `post_census_parse_failed`（单题失败）；含换行 → `unsupported_object_in_patch`（unsafe 通道）；目录不可遍历 → 脚本仍退出 0、子树静默漏掉；**文件名含 0x01 → 解析时 pydantic `ValidationError`，exporter 不捕获，按源码推断正式链升级为 `rh2_contract_validation_failed` 并停批——模型能让整场训练停下来**。这条不属于 E2。Codex §6 的处置：按**既有不支持候选工件的处置补漏**——在具体的候选路径解析边界给 typed 不支持原因，复用已批的 unsafe 通道（保留事实、无 reward、按完整组规则处理），不把整个 `ValidationError` 兜底降成单题损耗，我方身份 / 摘要 / 契约矛盾继续 fatal；实施验收补正常文件、该控制字符、我方契约矛盾三个对照。只有改成 reward 0、支持新文件名协议或新增处置通道才是新 T0。

### 1.3 可信执行入口与一个新风险

- coreutils 在两类镜像都有使用先例（R2E `find -print0 | sort -z | xargs -0 sha256sum`；SWE-Gym 保护脚本 `stat -c`）；Python 位置因来源而异（SWE-Gym `/usr/bin/python3` + miniconda，R2E `/opt/py/<版本>` 而 `.venv/bin/python` 在 agent 可写目录）→ 两份方向复核选 coreutils 正确。
- **新风险（推断，未用 Docker 复现）**：R2E 派生镜像的 PATH 以 `/testbed/.venv/bin` 开头，而该目录 agent 可写（`runs/r2e_env_repair_20260924/smoke/none2/*/agent_probe.log` 记 `WRITE_VENV_BIN=ok`）。root 执行的 `docker exec bash` 本身及脚本里的 `find` / `sha256sum` / `base64` / `cat` 都可能执行 agent 或候选放进去的同名程序；受影响的是运行后 census、内容抓取、grader 在候选代码跑完之后的 root 读取。这打破 exporter "不信任模型写过的树"的前提；SWE-Gym 的 PATH 目录不归 agent 所有，不受影响。**处置（Codex §6：这是恢复"root 不执行候选可写程序"既有边界的 bug 修复，不是新的安全放宽 T0）**：root 的可信操作统一用绝对 shell 路径 + 可信工具 PATH（`/bin/bash`、`env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin`），**只**用于 root 的可信操作，不禁掉 agent 自己的 `.venv` 激活；与 B 的 E09 对齐，R2E 正式运行前修，不必等 E2 吞吐测量。当前证据是 B 的实际 PATH / 可写性加调用链，未做 Docker 攻击复现。
- 镜像的 OS / coreutils / bash 版本、`sha256sum --zero` 可用性都没有记录，开工前做一次只读探针。

### 1.4 在制品相交

| 文件 : 函数 | 谁在改 | E2 |
| --- | --- | --- |
| `baseline_census.py : build_census_script` | 无人 | E2a 唯一必改点 |
| `baseline_census.py : baseline_policy_for_task_id` | B（R2E 分支） | 不改，同文件 |
| `contracts/baseline_manifest.py : BASELINE_MANIFEST_POLICY_R2E_V1` | B | 不改 |
| 解析函数、`patch_exporter`、`manager._verify_baseline_rebuild`、`generate.py` 调用点 | 无人 | 不改 |
| `replay_grade.py` | B | 不改 |
| `sandbox_profile.py` 的 root exec | E1（A，本轮） | 只 E2b 涉及 |

约 19 个测试替身按 `find .`、`-prune`、`readlink`、`sha256sum` 字样分流（两个在 B 在制品里）；新脚本保留这些字样即不用改测试。

### 1.5 切片与验收

1. 等 B 提交 `baseline_census.py` / `baseline_manifest.py` 在制品。
2. **E2a**：只改 `build_census_script`——枚举、排序、逐行内建分类、软链处理照旧；普通文件哈希集中成一次 `xargs -0 -r sha256sum`，按位置取回；退出码 / 行数 / 格式任一不符即回退到现行逐文件路径（错误情形也逐字节等价，Python 侧不动）。
3. **E2b**：census 与 root exec 改绝对路径 / 可信 PATH、`/bin/bash`——是恢复既有边界的 bug 修复（§1.3），与 B 的 E09 顺序落地，不等新决定。
4. 抓取阶段批量化可选；0x01 窄修另立。

实现约束（Codex §5）：整批结果先私下收集并验证，成功才输出；失败回退不能先输出半批再追加旧路径。验收：冻结现行脚本作对照，在真实 Linux 上覆盖空树、含空格 / 反斜线 / TAB / LF 的文件名、各种权限位、各类软链、同名缓存文件与软链、排除区边界、空目录、单个摘要失败、强制回退的语料树上比较新旧 stdout 逐字节相同（保留脚本关键字让旧替身通过只能证明接线，不是等价证明）；既有 census 测试（含 Docker 组与 B 的 R2E 测试）不改动即通过；目标机 root 跑最大真实镜像（pandas-56849、R2E numpy）与已落盘基线清单摘要对账，记 exec 次数与耗时（空闲 / 4 路并发各一组）。

## 2. E4：完成历史释放

### 2.1 读者清单

- `manager._records`：每个评分容器一条，永不删除。读者：`gc` / `close` / bringup 的 container_residue（只需未确认删除的活记录）；**B 的重放 driver**（grade 返回、取消或停批后立刻按 trajectory 找最近一条，读 diagnostics、candidate_facts、两种日志引用、resource_facts，`replay_grade.py`）；约 45 处测试；资源闭包读列表长度。**生产编排器从不读记录**，只用 `GradingReport` 与 `take_grader_phase_timing`。
- `leases`：无上界、无生产读者。`cleanup_failures`：只在失败时增长；B 的 `final_exit_status` 用其长度当累计总数。
- queue 的 `events`：无上界；每次 finalize 把整个列表复制两次（`generate.py`、`bringup`），gate 只取本轨迹事件；`backpressure_count` = 列表长度。
- 编排器的 `audits` 带 `finalized.projection`，可能才是最大的常驻对象（`_execution_closure_facts` 遍历全部）——不在 E4 字面范围。

### 2.2 可释放对象与条件

- 全文日志已在 `58a14b00` 于 grade 的 finally 释放。仍留在记录上的：`parsed_verdict`（中位约 3 KB、最大约 0.4 MB）、`diagnostics`（与 sidecar 同内容，中位 2.6 KB、最大 238 KB）、`prelaunch`。
- 三个释放条件：容器已清理（`record.removed`，可判）；已落盘（有日志引用，可判）；消费者已取走（**无信号**）→ 活记录永不裁剪；已删除的完成记录只保留最近 N 条（建议 256），更早整条丢掉。
- **R6 补清（Codex 生命周期探针的两个反例）**：(1) 退役顺序按**完成顺序**（确认删除的时刻），不是创建顺序——早启动、最后完成的任务按创建序会刚完成就被丢掉；(2) GC / close 正在遍历 `_records` 并 `await _remove_container` 时不能原地 `_records[:] = kept` 裁剪——探针里 256 条历史 + 3 条活动记录、原地裁剪后 close 只删了 `active_0` / `active_2`，漏掉 `active_1`；遍历用快照（`list(self._records)`）或遍历结束后再裁剪，活动 / 未确认删除的记录永远保留。(3) `leases` 现在只有初始化与 append：随记录确认删除一起退役，或限量留摘要；无日志的启动失败记录不能因永远等不到"有日志引用"而永久保留。(4) `cleanup_failures`、queue events、audits 本片不释放 → "内存平台期"只限于本片裁剪的容器历史，不宣称整个 manager / run 内存已稳定。

### 2.3 不变量

`containers_open` 恰好 = 删除未获确认的记录；不恢复按年龄清扫；`cleanup_failures` / `regrade_total` / `backpressure_count` 等累计数不随裁剪变小；本轨迹的反压事件在其 finalize 时必须可见（`trajectory_id` 跨物理尝试不变）；driver 与测试必须能读到刚完成那一条的完整事实；资源闭包同时报告保留长度与累计数。顺带既有小缺陷：`close()["regrade_declined"]` 取截到 256 条的列表长度，超过后少计。

### 2.4 切片与验收

- **E4a（manager 历史有界）**，等 B 提交 `manager.py` / `replay_grade.py`：`_remove_container` 成功时把记录"退役"（按确认删除的完成顺序进入有界历史；活动记录以 `removed` 标记区分；GC 遍历快照、遍历后裁剪）并释放对应 lease；新增累计数（已创建、已删除、leases、regrade_declined）；`cleanup_failures` 本片不截断；更新资源闭包报告；同文件的 CR1 诊断余项（owner A，八卡作业前）一并做（exec 结果先写进 record，再 inspect / 读 tee，两份输出取较长）。验收：FakeDocker 连评 N+50 次条数有界、累计数准确、每次 `[-1]` 事实都在（序列执行不足以覆盖遍历问题，另加"历史满 + 多条活动记录时 close 全部清完"与"早启动晚完成不被丢"两案，以及启动失败记录、取消 / 晚清成功）；清理失败记录超容量仍保留、close 时晚清成功计数不变；取消与停批时 driver 账本行逐字段不变；CR1 探针两个取消窗口与短 tee 的断言翻转；CPU 上 tracemalloc 看内存平台期。
- **E4b（queue 事件）**：先加按轨迹索引与 `backpressure_total`，不删事件；删除需要"该执行已终局"信号，单独决定。
- **E4c（audits）**：先测量再决定立项。

## 3. 未核实与风险

镜像版本类事实缺记录；R2E PATH 劫持未用 Docker 复现；0x01 → 停批的最后一步只来自源码推断；E2 时间收益与 E4 内存数字都是估计。共享工作区同时有 B 在制品：E2a / E4a 等 B 提交后实施（或经用户同意在独立 worktree）。顺带疑点（未验证）：`bringup.record_event` 用执行 id 比对 `s-{paid}` 形式的会话 id，正式链里可能永远匹配不上 audit。

## 4. Codex 设计复核（2026-09-25）

**E2 批量化方向成立；E4 先补清 R6 的退役规则。** 详见[复核报告 §5–§6](review_next_slices_20260924/README.md)。

- 拟议裁剪的反例：真实 gc 遍历时原地缩短 `_records` 会漏过一个活动容器；按创建序保留最近 256 条又可能立即删掉刚完成的长任务。这是未来实现的反例，当前尚未加入裁剪，不报告为现有清理 bug。明确完成顺序、遍历快照或遍历后裁剪；未确认删除的资源始终保留。
- 写清 leases 如何随记录退役；只加累计数不释放 list。启动失败没有日志不能永久阻止释放。事件索引只提速而不删除时，不宣称内存有界。未证明当前 B 串行消费者丢读，不增加消费确认平台。
- E2 保留整批成功才输出、失败无半批污染的规则，真实 Linux 差分覆盖特殊文件名和失败回退；按相关文件交接，不等待 B 所有无关工作结束。
- root 的可信 PATH 修复落实已有边界，不是新的安全放宽 T0。`0x01` 先在候选路径校验边界复用既有不支持工件 / unsafe 处置，不整体降级 `ValidationError`；若要改 reward 或新增文件名协议，再作新决定。

## 5. Codex R6 修订复核（2026-09-25）

**E4 R6 的设计修订通过，可按文件交接进入实现。** [完整报告 §3](review_followup_e5_20260925/README.md)。完成顺序、GC 快照 / 遍历后裁剪、未确认删除的记录保留、leases 同步退役、无日志启动失败、累计计数与保留历史分开均已写清。内存有界结论限于本片容器历史，不增加消费确认协议。本文仍为设计验收，非实现验收。

E2 §1.5 第 3 项残留“等 §1.3 T0 决定”已被 §4 的归类覆盖，应删旧措辞；可信 root PATH 继续与 B E09 顺序落地，不等待新的政策批准。E2 的 Linux 差分与失败回退验收不变。

## 5. 控制字符文件名停批的窄修（§1.2 的发现；2026-09-25，Claude，已实施）

- **复现**：候选在 /testbed 建含 `0x01` 的文件名，运行后 census 解析里构造条目时契约拒绝，旧 exporter 不捕获，真实 fa_formal 编排得到 `FatalExecutionInfrastructureError rh2_contract_validation_failed`（stage=assemble）——模型能让整场训练停下。此前是源码推断，现在由反证用例实测（新分支关掉即复现）。会落到这里的只有不被 `splitlines()` 切行的控制字符（`0x01`–`0x08`、`0x0e`–`0x1b`、`0x1f`、`0x7f`）；TAB 已是 `post_census_parse_failed`，换行 / 回车等已按畸形行或 unsafe 处理，本修不动它们。
- **修法（`patch_exporter.export_frozen_patch`，按 Codex §6 的处置）**：解析抛 ValidationError 时，用契约自己的路径规则（`baseline_manifest._check_canonical_path`）逐条复查 post-run 的 regular / symlink 条目路径——**只有**确有候选条目路径过不了规则，才改判为既有 unsafe 通道的 `unsupported_object_in_patch`（新 object_type `unsupported_path_name`，证据路径把控制字符写成 `\xNN`，原 ValidationError 留在异常链）；否则原样上抛，我方身份 / 摘要 / 契约矛盾照旧 run-fatal。编排侧零改动（沿用 `unsupported_object_in_patch` 分支：present + 永久拒绝、不评分、拒绝证据内嵌 receipt）。与同文件里父子前缀冲突改判 `unsupported_delta_shape` 是同一种写法。
- **验收**（`tests/adapters/test_patch_export_path_names.py`，8 例）：正常新文件照常导出；`0x01` / `0x1f` / `0x7f` / ESC 四种路径 → typed 不支持且证据无控制字符；两种我方矛盾（条目落在排除 namespace、同一路径两条）仍抛 ValidationError；真实 fa_formal 编排 → 交付不评分、receipt `delivery_prepared`、拒绝证据 `unsupported_path_name`、`unsafe_artifact_reasons` 带转义路径。反证：把新分支关掉，同一编排场景是 run-fatal。
- **没做**：不改 census 脚本、解析器、契约（B 的在制品文件）；不新增处置通道、不改 reward；非 UTF-8 文件名（census 宿主解码 `errors="replace"`）的口径不在本修范围。

## 6. E2b rollout 侧：root 通道不继承镜像 PATH（2026-09-25，Claude，已实施；grader 侧待 B 落地 manager.py）

- **面**：`generate.RolloutContainerWorkspace.run_bash` 是 rollout 容器里 root 可信操作的唯一通道——两次 census、内容抓取、停止合同的 `pkill -9 -u agent` / `ps -u agent`、静止指纹的 `git status` / `git diff`、`git rev-parse HEAD` 都走它。旧形状 `docker exec <c> bash -c …` 继承镜像 ENV；R2E 派生镜像 PATH 以 agent 可写的 `/testbed/.venv/bin` 开头，候选放同名程序就会被 root 执行（最坏：假 `pkill` + 假 `ps` 让停止合同误判已停，候选进程在 census / 抓取期间继续写）。
- **修法**：通道改为 `docker exec <c> /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /bin/bash --noprofile --norc -c "cd /testbed && …"`（`generate.TRUSTED_ROOT_EXEC_PREFIX`）。清掉继承的全部环境（含 `BASH_ENV`），bash 不读启动文件；agent 的启动与激活（逐 execution 注入的 `BASH_ENV` / `HOME` 等）不经过这条通道，不受影响。
- **兼容核对**：本机 R2E 派生镜像三张（aiohttp / pillow / coveragepy）与验证机 SWE-Gym 镜像三张（dvc / conan / moto）在可信 PATH 下 `find sha256sum readlink tr cut sort xargs base64 cat git pkill ps wc stat` 全部解析到 `/usr/bin`；SWE-Gym 镜像 PATH 以 `/opt/miniconda3/bin` 开头，但 `git` 本就是 `/usr/bin/git`（2.34.1），`git config --system` 写在 `/etc/gitconfig`，可信 PATH 下 root 的 `git rev-parse` / `git status` 在 agent 拥有的仓库上照常。
- **验收**（`tests/adapters/test_trusted_root_exec.py`，2 例）：exec 形状逐项固定；**真容器**以 `-e PATH=/testbed/.venv/bin:…` 模拟 R2E 镜像 ENV、在 `.venv/bin` 放假 `find` / `pkill`：旧形状确实先找到假程序，本通道找到的是 `/usr/bin/find`、真实 census 不含假 `find` 注入的条目（候选放的文件照常作为普通文件记录）、停止合同脚本没有执行假 `pkill`。既有编排 / 导出 / 冻结测试不变。
- **未做 / 交接给 B**：grader 侧同类通道在 `grading/manager.py`（B 的在制品）——候选代码跑完之后 root 的读取与重建同样应走可信环境；SWE-Gym 镜像的 PATH 以 `/opt/miniconda3/bin` 开头，若 grader 的候选可写前缀覆盖该目录，同一问题在 SWE-Gym 上也成立。`docker_sandbox.DockerSandbox` 的 root 调用只在 harness 启动前（镜像原样内容）使用，本轮不改。
