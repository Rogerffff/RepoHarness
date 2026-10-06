# 普通探针接入：Production Tracer 独立复核

日期：2026-09-29。范围：公共 root Git 窄修的真实接线，以及当前 SWE/R2E 探针的导出、清理、评分接缝。此报告由分工复核代理产出，主审查者仍需去重裁决；不冒充跨模型独立审查。

**当前结论：公共 `fa_formal` 链与新增宿主运输核心在本轮范围内通过复核；完整探针入口尚待集成验收。** 初轮旧入口的 root Git、政策回退和失败传播发现保留在 §2；新增 `frozen_transport.py` 的独立核心验收见 §6，不能据此直接核销旧入口发现。本轮未改生产或探针源码，未访问远端、启动 Docker 或调用 API。

适用基点：`a31cdcd0adb0fab3e681201edfb928653fdf5b3c` 加共享工作树；逐文件摘要见 `runs/ordinary_probe_20260929/reviews/tracer/source_hashes_initial.json`。下列行号针对该摘要，不把其后的并行修改算作已复核。后续新探针接入应在本报告追加独立验收结果。

## 1. 当前真实调用链与所有权

| 路径 | 实际顺序与身份 | 本轮判断 |
|---|---|---|
| 正式 `fa_formal` | `bringup.py:1706` 注入 `DockerQuiescenceBarrier` → `generate.py:4895` 物化 workspace 时按 task_id 选择政策 → `:3917` baseline 消费 `workspace.census_policy` → 会话 revoke/drain 与 capture 收口 → `:3423` 屏障 → `:3480` exporter → 冻结工件持久化、释放 rollout → `FrozenDeltaSource` → grader | 同一 workspace/policy 跨完整 attempt 运输，无第二个政策 owner。 |
| 公共屏障 | `quiescence_barrier.py:118` 校验会话已 drain → `:125` 有界终止 agent UID 进程 → `:145` 取 workspace policy → 两次可信 census → `FrozenWorkspace` 保存同一 policy | 脚本不含 Git；未引入新失败码。读取非零仍 `snapshot_freeze_failed`，双读不同仍 `active_writer_detected`。 |
| 正式冻结导出 | `patch_exporter.py:183` 以 `baseline.policy` 做 census → host 结构比较 → 内容抓取与摘要核对 → typed artifact | 不把 `UNSUPPORTED` 提前在屏障解析为 run-fatal；仍交 exporter 分类。缓存观测计数不参与屏障指纹。 |
| SWE 旧探针 | `solve_attempt.py:369` CC 求解 → `:372` 自有 `export_candidate` → root kill/status/add/diff → 宿主 diff → `run_matrix.py:165` replay grader | **不经过公共屏障**；公共修复不会替换其 root Git。 |
| R2E 旧探针 | `R2EAttempt.run` 建基线 → 复用 SWE `solve` → `:502` 新建 workspace → 公共屏障 → exporter → 分类 →宿主 bare Git 渲染 → 可选 legacy Git 对照 | 正常冻结路线已消费公共修复，但导出 workspace 未传政策；legacy 开关仍在冻结后运行候选 Git。 |
| replay 候选阶段 | `replay_grade.py:351` fresh 基线 → `:375/:380` **agent UID** `git apply` → `:388` 可信 census 导出 → fresh grader | 不把该 agent Git 误报为模型容器中的 root Git；需要验证求解冻结物与回放冻结物一致。 |
| grader | `manager.py:1975` 收到 frozen_delta 时直接验证绑定、准备 delta；`workspace` 旧文本导出只在相反分支 | 正式冻结路径不会回退到 `EXPORT_PATCH_SCRIPT`。`s1_compat` 仍有旧文本能力，但不是本轮 API 探针应走的路径。 |

进程/并发：每个 solve 子进程持有自己的容器、attempt 网络和 relay，在 `finally` 清理；模型进程以 agent UID 运行。旧 Matrix 在同一 asyncio loop 中持有全局与 solver 信号量、停止标记和连续失败计数，`asyncio.gather` 创建全部任务，但任务进入信号量后才检查 STOP。默认并发 3；本轮反例固定并发 1，证明不是已经在途任务造成“下一题继续”的假象。宿主 bare Git 渲染通过 `asyncio.to_thread` 运行，只消费冻结字节和核过摘要的旧字节，不读候选 `.git/config`。

## 2. 必修发现

### TR-1 · P1 · 旧 SWE 与 R2E legacy 在冻结边界后仍可运行 root Git

- **可达性：`production_reachable`。** SWE 的真实入口 `run_matrix.py:123` 固定启动 `solve_attempt.py`；后者 `:462–475` 在 CC 返回后以 root 调用 `git status`、`git add -N` 和 `git diff`。R2E `export_candidate:583` 受 `--legacy-gitdiff-compare` 开关控制，进入 `:656–663` 的 root Git；该 CLI 开关对 solve 模式仍接受。
- **不变量/影响：** 候选可以修改 `.git/config`。可信 PATH 或 `--no-ext-diff/--no-textconv` 不能整体消除 clean filter 等执行面，已批准的“root 不执行候选程序”边界仍未恢复；影响范围是容器内权限与私有材料边界，本轮没有宿主逃逸证据。SWE 旧导出还忽略文件模式和部分 ignored/untracked 变化，不能等价于正式冻结物。
- **证据：** `trace_reachable_seams.py` 直接调用当前 SWE exporter，把底层 Docker 调用替换成桩，记录到两个 root Git 通道；见 `reachable_seams.json:swe_post_model_commands`。该实测证明控制流可达，不另声称本轮实测了 Git payload。公共修复已有真实 Docker uid=0 证据，本轮未重复执行它。
- **来源：** 两个旁路均为既有旧探针行为，不是 A 的 census 修复新引入。
- **最小修复：** SWE 直接改用实际物化基线 → 公共屏障 → exporter → 现有宿主受控 renderer；真实求解入口拒绝/移除 R2E legacy 对照。不要保留状态诊断中的 root Git。只换 Git 开关或在旧导出前调用一次屏障仍不充分。
- **验收/停止条件：** 用真实探针入口、候选 Git 执行标记验证停止、导出及诊断全程不触发；normal/noop、ignored `.so`、untracked、mode、普通 symlink 均能冻结并回放。本次不要求证明任意恶意程序都不可运行。

### TR-2 · P1 · R2E 导出 workspace 未运输已选基线政策

- **可达性：`production_reachable`。** `r2e_solve_attempt.py:416–419` 基线用 `baseline_policy_r2e_v1`，但 `:502` 创建导出 workspace 时没有 `census_policy`。新公共屏障 `:145` 因而消费 dataclass 默认 `baseline_policy_v1`，包括原应排除的 `.venv/` 和缓存内容。
- **不变量/影响：** 屏障与 exporter 不再对同一评分树判定稳定性；新屏障可能扫描整个虚拟环境，增加非评分内容影响冻结判定与读取成本的机会。不能从旧 R2E CPU 证据推断新政策接缝已通过。
- **证据：** 对真实 `R2EAttempt.export_candidate` 仅替换 barrier 的末端执行，捕获 `baseline=baseline_policy_r2e_v1`、`barrier=baseline_policy_v1`、`same_object=false`；见 `reachable_seams.json:r2e_export_policy`。这不是仅构造独立 helper 的假想调用。
- **来源：** A 新增 workspace 字段后的现有 consumer 接入遗漏；A 正式 `fa_formal` 物化/基线/屏障接线本身正确。应由探针 owner 补接，而不改公共默认政策或改评分规则。
- **最小修复：** 导出 workspace 明确传 `census_policy=self.baseline.policy`；基线处也可以先选择政策再用 workspace 运输，避免两份选择逻辑。
- **验收/停止条件：** 从 R2E 真实 attempt 入口断言 baseline、屏障及 frozen wrapper 的政策同一；`.venv` 不进入评分内容，缓存计数变化不新增拒绝。无需增加政策注册表或新的长期 owner。

### TR-3 · P1 · grader/往返失败没有成为派发与进程的失败结果

- **可达性：`production_reachable`。** `run_matrix.py:152` 在评分前就重置 infra 计数；`:192–202` 只把 grader exit/stage_error 摘入结果；`:211` 无条件返回 0。恢复路径 `:169` 找到任意旧账本行后直接跳过驱动执行，未核 grader cleanup/fatal。R2E E2E 的 `main:457–474` 与 `regrade:413–428` 记录往返比较，却只按资源残留决定退出码。
- **不变量/影响：** 清理不明、评分 fatal 或候选往返不一致不应被当作一个可继续派发的普通分数。现代码可在第一题已记录 `candidate_container_cleanup_failed` 后继续下一题并返回 0。
- **证据：** `trace_reachable_seams.py` 通过真实 Matrix 恢复路径消费两个磁盘夹具账本；第一题 `cleanup.removed=false` 且 `stage_error=candidate_container_cleanup_failed:injected`，随后第二题仍被处理，最终 `exit_code=0`、没有 STOP。见 `reachable_seams.json:matrix_resume_unconfirmed_grader_cleanup`。R2E 往返失败未升级由上述返回分支源码确认，本轮不重复 readiness 已有的内存桩反例。
- **同边界补充：** 共用 `solve_attempt.py:414–417` 将 driver 异常记成 `exit_code=-2`，之后 `:450–452` 仍写 `result=ran` 并返回 0；不能仅凭 ran 和候选文件认定有效求解。导出失败已设 `export_ok=false`，清理失败已有 `cleanup_ok=false`，这些既有措施不能抹去，也不应将合法预算结束或 typed unsafe 一概改为 infra。
- **来源：** 既有探针收口缺口；公共屏障修复未改这些分支。
- **最小修复：** 在本批唯一派发入口统一消费现有 attempt、grader 退出、评分账本、manager close、往返核对与残留事实；致命/清理不明置 STOP 并返回非零，恢复执行必须复核同一事实。可以绕开旧 runner，不必为历史脚本增加一套新状态机。
- **验收/停止条件：** 并发 1 下分别注入 grader fatal、manager close 失败、回放不一致和断流，证明下一任务没有启动、结果无有效分且整体非零；normal 0 分与预算结束但有合法候选仍正常保留。提高并发后只要求停止新增派发，不把此前已在途任务误当修复失败。

## 3. 基线与渲染的接入要求

SWE 的 prep 在 `solve_attempt.py:269–282`，旧 dirty 基线在其后。新 census 与旧字节快照必须同样在 prep 之后、模型获写权之前取得。R2E `fetch_baseline_bytes:586–629` 从另一张同镜像容器取旧字节，会核摘要；直接照搬到有 prep 的 SWE 会拒绝改过的基线或无法构造补丁，不能把镜像初态等同于实际物化初态。

宿主 renderer `:127–179` 使用临时 bare 仓库、空模板、受控 HOME/Git 配置、`hash-object --no-filters`，候选字节只进入对象数据库；`:183–197` 检查 `apply --cached` 后的树身份。这足以作为传输层复用基础，但只证明 renderer 自洽，不证明 fresh replay 容器与求解基线/冻结工件相同。SWE prep、R2E sanitize 导致的已知 `.git/logs/HEAD` 排除区差异须显式列明；不能整体删除 manifest 身份核对。

## 4. 本轮验证及边界

- **58 passed、4 deselected**：从 `rh2/` 执行 `.venv/bin/python -m pytest -q -m 'not docker' tests/adapters/test_quiescence_census.py tests/adapters/test_f2_2b_barrier.py tests/adapters/test_budget_deadline.py`。包含三种 task policy 的正式编排正控、缓存计数、屏障失败与预算归因；4 项真实 Docker 用例本轮明确未执行。原日志 `runs/ordinary_probe_20260929/reviews/tracer/pytest_public_boundary.txt`。
- **3 个探针接缝事实通过断言**：真实方法 + 末端桩，源码及 JSON 位于同一 tracer evidence 目录。运行命令：`rh2/.venv/bin/python runs/ordinary_probe_20260929/reviews/tracer/trace_reachable_seams.py`。这些是本地控制流证据，不是付费模型或真实容器结果。
- 当前公共路径中，模型结束后没有发现遗漏的 root Git；模型启动前的 HEAD/物化 Git、fresh replay 的 agent Git、宿主 bare Git、未走的 `s1_compat` 旧路径均已按身份和时序区分，没有仅凭 grep 命中报新安全漏洞。
- SWE `sh` 与会话 tar 仍有继承镜像环境的 root 通道；R2E 通过 subclass/monkeypatch 改了可信前缀。本轮未实测本批三张 SWE 镜像 PATH 的可写性，因此仅记接入一致性提醒，不单独升级当前阻塞项。
- 软链 target 的 `readlink | tr -d '\n'` 字节损失是旧 census 缺陷，未由本片修复，也不是新 public Git 修复引入；普通 symlink 验收不得写成“任意软链字节完全支持”。评分 stdout/conftest/测试辅助代码信任问题由主审查者另一分工处理，本报告不核销它们。

维度覆盖：A/D/E/F/G/H/I/L/M/N 由上述调用链、政策身份、失败控制流、测试与成本边界覆盖。B：只要求恢复既有评分树与失败分类，不能新增合法预算轨迹拒绝。C：本轮只使用 API 开跑前窄修停止条件，不建立新训练闸门。J/K：建议复用现有 exporter/renderer 与一个派发器，避免双 owner 和第二套恢复状态。reward/loss/mask/group contract 本轮未改，非训前总审计。未出现需新增审查维度的漏网问题。

## 5. 停止条件

公共 A 修复在本范围可交探针消费，无需继续扩为 Git 配置黑名单或安全平台。普通 API 小批进入下一步需新入口关闭 TR-1/2/3，完成实际基线、冻结、渲染、回放的 CPU 正控与失败传播验收；主审查者另行核销评分信任边界。本 tracer 对新接入代码按同一边界复核即可，不重复扩大整个 RH2 审计。

## 6. 新增运输核心复核（同日后续）

**结论：`frozen_transport.py` 在该核心范围未发现新的阻塞项，23 项独立 CPU 测试通过；可继续接入口。** 验收源码摘要 `sha256:ffffa51b219ae72a2e45bd21b9f2a6c10db2e3401600b8f657a8d08b440f6a54`，完整记录 `runs/ordinary_probe_20260929/reviews/tracer/source_hashes_transport_core_verified.json`。本节核对的是真实归档读取与宿主 Git 渲染；Docker、网关 HTTP、模型均未运行。

| 需保留的不变量 | 源码与独立证据 | 状态 |
|---|---|---|
| 渲染旧字节来自实际模型前基线 | `capture_baseline_archive` 使用当前容器与 baseline.entries；`render_candidate` 从该 tar 读 modify/delete 的旧字节。独立测试调用真实 `render_candidate`，以模拟 prep 后的脏字节作基线，回放成功；换成镜像原始字节则在归档摘要核对处失败且未写出 diff。 | 核心通过；prep 后的实际调用顺序待入口验收。 |
| 字节、类型和执行位一致 | `archive_blobs` 不向宿主解包，拒绝重复、未知、缺少成员及 type/mode/digest 不符。实测普通/可执行/二进制/软链、7 类不一致均符合预期。 | 通过。 |
| LF 软链目标不能被静默归一化 | tar `linkname` 用原始字节重算；真实 target `tar\nget\n` 对旧 census 的 `target` 摘要被明确拒绝。 | 基线归档通过；不是对模型新建 LF target 的旧 exporter 缺陷作修复声明。 |
| 普通硬链接按评分模型视作普通文件 | 新命令已加入 `--hard-dereference`，避免 GNU tar 将第二条硬链接存为 LNKTYPE；读取器仍拒绝这种与 baseline regular 不符的归档。 | 源码正确；容器内 GNU tar 实跑留待真实入口 CPU 验收。 |
| 宿主 Git 不消费候选配置 | 真实本机 Git 2.50.1：当前目录为已初始化候选仓库，设置 candidate filter/textconv、`GIT_DIR`、`GIT_CONFIG_GLOBAL`、`GIT_CONFIG_COUNT`/diff.external，调用真实 renderer；补丁自检成功且执行标记没有生成。环境隔离、临时 bare GIT_DIR、空模板及 `hash-object --no-filters` 路径正确。 | 通过；仅说明该宿主渲染面，不扩为任意 Git 使用均安全。 |
| ignored/untracked、binary、mode、symlink 不丢失 | 综合往返包含 ignored `.so`、已有/新增 untracked、空文件增删、CRLF、NUL/非 UTF-8、纯 mode 变化、symlink target 修改、regular↔symlink；以 replay 同形的 UTF-8 `read_text` 再 encode 后实际 `git apply`，逐路径类型/字节/mode 全等。另有 5 组空格、引号、wildcard、反斜线、中文路径。 | 通过。 |
| 失败不得变成 noop | 真实 `export_candidate` 的末端注入 drain 失败、未 drain、export infra、typed unsafe、render 失败；均 `export_ok=false` 且未输出候选 diff。只有合法零 entries 为 `empty=true/export_ok=true`；typed unsafe 保留候选拒绝分类。workspace 与 baseline 使用同一 policy 对象。 | 核心通过；外层派发如何消费仍待 TR-3 集成复核。 |

测试文件：`runs/ordinary_probe_20260929/reviews/tracer/test_frozen_transport_core.py`。命令：`rh2/.venv/bin/python -m pytest -q runs/ordinary_probe_20260929/reviews/tracer/test_frozen_transport_core.py`。最终日志 `pytest_transport_core_verified.txt`：**23 passed**。测试数量是同一套覆盖的最后一次结果，不与前面 22 项或中间重跑相加。

首次测试期间实现方增加了 `drain_gateway`，旧测试桩因此在进入 exporter 前失败，形成 19 passed/2 failed；随后在本轮核心测试中显式替换该末端网关调用，并新增 drain-failure 分支。这是测试夹具对并行新增接缝的适配，不是放松失败判据；初次日志保留为 `pytest_transport_core_initial_fixture_drift.txt`。网关真实撤销/排空未由末端桩证明。

本段停止条件：归档、受控渲染和 export 分支已有充分核心证据，暂不扩测相同 helper。下一段只核入口在 prep 后/模型前完成 census+归档、所有结束后 root 通道经过可信执行、网关实际收口与 policy 运输、容器内 tar 正控、冻结—回放硬对账及致命/清理失败的停止派发。基线 tar 会增加容器盘、宿主盘与读文件量，实际大树成本留在运行时间/字节事实里，不能从本机小树测试外推。

## 7. Dask 6626 真实 CPU 冒烟的定向复核

详见 [dask_cpu_review.md](tracer/dask_cpu_review.md)。只读核对 `dask6626_v1` 的本地回传原件：真实 CC 激活、Bash、撤销/排空、冻结导出、fresh replay 与 0 分评分有完整证据，414 个基线条目与候选 entries 相等。原运行因九个 `.git` 内部路径差异退出 4，原失败保持不变。九条均可归因于模型前 sanitizer 与同源两派生镜像的不同初态；支持在这次固定 task/有序镜像对/源码版本上精确登记，独立 reconciliation 的 22 个证据条件通过。没有 pack 对象清单，因此不声称 pack 内容等价；也不把一次 add-only、scripted stub 的 CPU 冒烟外推为 DeepSeek 能力结果或全量集成验收。本段未连接远端、重跑测试、CC 或评分。

上述例外只适用于诊断探针的“宿主 diff → fresh replay → 重新冻结”双侧对账，不代表正式 `manager` 直接接收 actor FrozenPatch 时的 `excluded_census_digest` 身份拒绝已经修复。
