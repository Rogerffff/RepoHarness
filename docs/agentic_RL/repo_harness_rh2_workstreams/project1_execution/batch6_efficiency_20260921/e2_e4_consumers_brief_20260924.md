# Brief：E2 批量 census（I26）与 E4 完成历史释放（I29）——消费者梳理与切片设计

2026-09-24 / Claude（A 线）。**状态：设计稿；只读梳理（sub-agent，本地 `runs/decision_package_20260924/e2_e4_survey/README.md` 与三个本机探针，git-ignore），我核过 census 调用点以 root 无 `-u` 执行、R2E 探针 `WRITE_VENV_BIN=ok` 证据、fork 无关。没有改代码、没跑 Docker / 远端。** 依据：[README §2 E2 / E4](README.md)、[README §8.1 第 5 条](README.md)（先做只读消费者梳理和 Brief，实施按文件 / 函数归属顺序落地；保留扫描语义、活动资源 owner、未消费结果与累计计数）。

## 1. E2：批量 census

### 1.1 现状（源码 + 本机探针）

- 三个调用点共用 `baseline_census.build_census_script`：rollout 基线（`generate.py` materialize）、运行后（`patch_exporter` ← `generate.py`）、grader 重建（`grading/manager.py`）；B 的重放 driver（`replay_grade.py`）另有两处同样调用。都用 `docker exec <c> bash -c …`，**不带 `-u`、不带 `-e`**：root 身份、按镜像自带 PATH 找命令。
- 进程数：普通文件每个 1 个 `$(…)` 子 shell + `sha256sum` + `cut`；软链每个 1 子 shell + `readlink` + `tr` + `sha256sum` + `cut`；执行位用内建 `[ -x ]`。PATH 垫片计数与公式 `2R + 4S + 2 + 2·N_excl(+5)` 一致。
- 规模（1413 份已落盘基线清单）：SWE-Gym 216 题中位 1,276 条 / 最大 2,793；R2E 48 题中位 1,447 / 最大 2,569 → 每次 census 约 2.6k–5.6k 次 exec，每个 attempt 三次。grader 重建阶段 p50 4.57 s（431 次评分、4 路并发），其中起进程占比未测。
- `BASE_UNTRACKED_SNAPSHOT_SCRIPT` 不是逐文件的（常数个进程 + 一次 `git ls-files`）；fa_formal 模式下没有读者。

### 1.2 必须原样保留的语义

不跟随软链、目录不进清单、`LC_ALL=C` 排序、按换行分隔；分类先 `-L` 再 `-f`，其余 UNSUPPORTED；软链摘要 = readlink 输出删全部换行后再算；执行位按 root `[ -x ]`（= 任一 x 位）；EXCL 只列普通文件、不剪排除区里的缓存目录（B 的 R2E prewarm 测试依赖）；缓存计数目录只数顶层、文件只数普通文件；无 EXCL 行时排除区摘要 None；宿主解码 `errors="replace"`；脚本无 pipefail。

边界输入现状（本机实测；E2a 原样保留）：文件名含 TAB → `post_census_parse_failed`（单题失败）；含换行 → `unsupported_object_in_patch`（unsafe 通道）；目录不可遍历 → 脚本仍退出 0、子树静默漏掉；**文件名含 0x01 → 解析时 pydantic `ValidationError`，exporter 不捕获，按源码推断正式链升级为 `rh2_contract_validation_failed` 并停批——模型能让整场训练停下来**。这条不属于 E2，需要另立窄修（失败等级从停批降为单题的路由变化，**待用户 / Codex 决定**）。

### 1.3 可信执行入口与一个新风险

- coreutils 在两类镜像都有使用先例（R2E `find -print0 | sort -z | xargs -0 sha256sum`；SWE-Gym 保护脚本 `stat -c`）；Python 位置因来源而异（SWE-Gym `/usr/bin/python3` + miniconda，R2E `/opt/py/<版本>` 而 `.venv/bin/python` 在 agent 可写目录）→ 两份方向复核选 coreutils 正确。
- **新风险（推断，未用 Docker 复现）**：R2E 派生镜像的 PATH 以 `/testbed/.venv/bin` 开头，而该目录 agent 可写（`runs/r2e_env_repair_20260924/smoke/none2/*/agent_probe.log` 记 `WRITE_VENV_BIN=ok`）。root 执行的 `docker exec bash` 本身及脚本里的 `find` / `sha256sum` / `base64` / `cat` 都可能执行 agent 或候选放进去的同名程序；受影响的是运行后 census、内容抓取、grader 在候选代码跑完之后的 root 读取。这打破 exporter "不信任模型写过的树"的前提；SWE-Gym 的 PATH 目录不归 agent 所有，不受影响。**处置方向（T0，待用户）**：root exec 统一用绝对路径 / 可信 PATH（`env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin /bin/bash`）——影响安全边界与 B 的 E09 激活设计，先与 B 对齐。
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
3. **E2b**：census 与 root exec 改绝对路径 / 可信 PATH、`/bin/bash`——与 B 的 E09 及 E1 协调，等 §1.3 的 T0 决定。
4. 抓取阶段批量化可选；0x01 窄修另立。

验收：冻结现行脚本作对照，在覆盖各种权限位、各类软链、同名缓存文件与软链、排除区边界、空目录、特殊文件名、强制回退的语料树上比较新旧 stdout 逐字节相同；既有 census 测试（含 Docker 组与 B 的 R2E 测试）不改动即通过；目标机 root 跑最大真实镜像（pandas-56849、R2E numpy）与已落盘基线清单摘要对账，记 exec 次数与耗时（空闲 / 4 路并发各一组）。

## 2. E4：完成历史释放

### 2.1 读者清单

- `manager._records`：每个评分容器一条，永不删除。读者：`gc` / `close` / bringup 的 container_residue（只需未确认删除的活记录）；**B 的重放 driver**（grade 返回、取消或停批后立刻按 trajectory 找最近一条，读 diagnostics、candidate_facts、两种日志引用、resource_facts，`replay_grade.py`）；约 45 处测试；资源闭包读列表长度。**生产编排器从不读记录**，只用 `GradingReport` 与 `take_grader_phase_timing`。
- `leases`：无上界、无生产读者。`cleanup_failures`：只在失败时增长；B 的 `final_exit_status` 用其长度当累计总数。
- queue 的 `events`：无上界；每次 finalize 把整个列表复制两次（`generate.py`、`bringup`），gate 只取本轨迹事件；`backpressure_count` = 列表长度。
- 编排器的 `audits` 带 `finalized.projection`，可能才是最大的常驻对象（`_execution_closure_facts` 遍历全部）——不在 E4 字面范围。

### 2.2 可释放对象与条件

- 全文日志已在 `58a14b00` 于 grade 的 finally 释放。仍留在记录上的：`parsed_verdict`（中位约 3 KB、最大约 0.4 MB）、`diagnostics`（与 sidecar 同内容，中位 2.6 KB、最大 238 KB）、`prelaunch`。
- 三个释放条件：容器已清理（`record.removed`，可判）；已落盘（有日志引用，可判）；消费者已取走（**无信号**）→ 活记录永不裁剪；已删除的完成记录只保留最近 N 条（建议 256），更早整条丢掉。

### 2.3 不变量

`containers_open` 恰好 = 删除未获确认的记录；不恢复按年龄清扫；`cleanup_failures` / `regrade_total` / `backpressure_count` 等累计数不随裁剪变小；本轨迹的反压事件在其 finalize 时必须可见（`trajectory_id` 跨物理尝试不变）；driver 与测试必须能读到刚完成那一条的完整事实；资源闭包同时报告保留长度与累计数。顺带既有小缺陷：`close()["regrade_declined"]` 取截到 256 条的列表长度，超过后少计。

### 2.4 切片与验收

- **E4a（manager 历史有界）**，等 B 提交 `manager.py` / `replay_grade.py`：`_remove_container` 成功时把记录"退役"并按容量裁剪（`_records` 仍是 list）；新增累计数（已创建、已删除、leases、regrade_declined）；`cleanup_failures` 本片不截断；更新资源闭包报告；同文件的 CR1 诊断余项（owner A，八卡作业前）一并做（exec 结果先写进 record，再 inspect / 读 tee，两份输出取较长）。验收：FakeDocker 连评 N+50 次条数有界、累计数准确、每次 `[-1]` 事实都在；清理失败记录超容量仍保留、close 时晚清成功计数不变；取消与停批时 driver 账本行逐字段不变；CR1 探针两个取消窗口与短 tee 的断言翻转；CPU 上 tracemalloc 看内存平台期。
- **E4b（queue 事件）**：先加按轨迹索引与 `backpressure_total`，不删事件；删除需要"该执行已终局"信号，单独决定。
- **E4c（audits）**：先测量再决定立项。

## 3. 未核实与风险

镜像版本类事实缺记录；R2E PATH 劫持未用 Docker 复现；0x01 → 停批的最后一步只来自源码推断；E2 时间收益与 E4 内存数字都是估计。共享工作区同时有 B 在制品：E2a / E4a 等 B 提交后实施（或经用户同意在独立 worktree）。顺带疑点（未验证）：`bringup.record_event` 用执行 id 比对 `s-{paid}` 形式的会话 id，正式链里可能永远匹配不上 audit。
