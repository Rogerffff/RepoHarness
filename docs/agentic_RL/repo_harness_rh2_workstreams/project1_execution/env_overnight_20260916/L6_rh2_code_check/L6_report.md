# L6 · 各包对 RH2 代码断言的源码核实

日期：2026-09-16 夜（03:54–04:20）。范围：把今晚 L0–L4、L1_* 各包报告里对 **RH2 源码行为**的断言逐条对照当前工作树核实。
本包**只读** `rh2/`，未改任何 rh2 文件，未起 Docker、未连远程机器、未调模型 API。结构化结果在同目录 `claims.json`。

## 1. 被核实树的状态（照实记录，不修）

| 项 | 值 |
| --- | --- |
| `git rev-parse HEAD` | `bac7659ea70cc07a3a8c872a29e7659a894afc5a` |
| 分支 | `miles-migration` |
| `git status --short rh2/ \| wc -l` | **45**（26 个 ` M` + 19 个 `??`） |
| 核实时刻 | 2026-09-16 03:54–04:20（本机时间） |

树里含另一会话未提交的 P-A/P-B/P-C/P-D 改动。关键的评分路径文件全部处于未提交状态：
`envpack/swegym_parsers.py`（`??` 未跟踪）、`envpack/scoring.py`、`envpack/spec_vendor.py`、`grading/manager.py`、
`grading/trusted_projection.py`、`contracts/grading.py`、`adapters/slime/prepared_task_face.py`、
`adapters/slime/replay_grade.py`（`??`）、`scripts/replay_grade.py`（`??`）、`scripts/screening_facts.py`（`??`，L0 今晚新增）。

> **引用注意**：所有行号都是在这棵会动的树上取的。M2 给的 `sandbox_profile.py:517` 现在已经是 520（C13）；
> L2 在 02:3x 报的 `contracts/grading.py:317` 语法错误现在已经不存在（C14）。早上引用请按内容 grep，不按行号。

## 2. 断言核实表

| ID | 来源包 | 断言（摘要） | 结论 | 关键证据 |
| --- | --- | --- | --- | --- |
| C01 | L1_moto_3 / L1_moto_2 R8 / L1_moto_1 / L2 | `swegym_parsers.py:52-55` 用 `line.split()` 取第 2 段并后写覆盖 → 含空格参数化 ID 截断塌缩 | **成立** | 源码 + 实跑：两行不同用例塌成键 `tests/test_s3.py::test_head[my`，值取后写的 `FAILED` |
| C02 | L1_dvc_1 / L1_monai_1 / L1_monai_2 | `SKIPPED [N] path:line:` 取成 `[N]` 伪键；`scoring.py:24` 的「SKIPPED 不进桶」不可达；v2 同样受影响 | **成立** | `scoring.py:231` 用同一 `lookup_parser`；实跑 `SKIPPED [1] …` → 键 `[1]`；唯一例外是 pydantic 尾状态分支 |
| C03 | L1_monai_1 / L2 | 任意以 FAILED/PASSED/ERROR 开头的行都记状态、不校验键 | **成立**（且比断言更宽） | `:48` 是 `startswith` 前缀匹配；`ERROR: Could not find…` → `{'Could': 'ERROR:'}`；**状态值同样不校验** |
| C04 | L1_monai_1 | `manager.py:672` `test_globs=()` 使候选 `tests/conftest.py` 不被剔除；`prepared_task_face.py:199-210` 只恢复 test_patch；`trusted_projection.py:18-20` 登记不修 | **成立** | 三处源码逐条命中；补：sidecar **会**记录（`CONFTEST_OR_FIXTURE_GLOBS`→`observe_candidate_paths`→账本键） |
| C05 | L1_mypy_2 | `hygiene.test_files` 只等于 test_patch 路径；mypy 测试驱动与 fixtures 不受保护；`additional_exclusions` 是否生效 | **成立** | `manager.py:656/672/581`、`prepared_task_face.py:306/329/330`；`additional_exclusions` 在 `rh2/src` **零命中 → 当前不生效** |
| C06 | L1_mypy_2 / L1_mypy_1 | `spec_vendor.py:183-191`：mypy 的 `-k` = test_patch 里 `[case X]` 的子串闭包 | **成立** | 正则 `:137`；实跑 16966 得 `…CustomEquals-skip`，`-skip` 后缀确被拼进 `-k` |
| C07 | L1_moto_3 | 阶段一 eval.sh 恢复 checkout 不含新建路径、3 题无 pathspec；当前代码是否沿用 | **部分成立** | 阶段一实测是 **4** 题无 pathspec；当前代码**不沿用**：空清单直接拒绝构造；profile 路径逐文件 `git cat-file -e` 守卫已修；legacy 路径整条 checkout 失败（静默不恢复） |
| C08 | L1_dvc_1 / L0 / M2 | 安装失败被 `\|\| true` 吞、`RH2_INSTALL_RC` 仍 0 | **成立** | 采集点 `prepared_task_face.py:137-141`（只在段末采一次 `$?`）；dvc 串三处字面 `\|\| true`、mypy 串以 `hash -r` 收尾 |
| C09 | L0 | driver 账本 schema 漂移而 `schema_id` 未升 | **成立** | `replay_grade.py:78/458` 仍 `…ledger.v1`；逐键核对 **10** 项（L0 的 9 个行级键 + `projection.unsupported_shape_reasons`）在 e1 的 10 行里全缺 |
| C10a | L1_dvc_1 / L1_monai_2 / L2 / L1_pydantic | 代码里有无任何 ID 归一化 | **成立（确认「无」）** | `rh2/src` 全树无 `unicode_escape`/`ascii_escaped`/`latin-1`；匹配是纯字符串相等 |
| C10b | L1_moto_2 / L1_moto_3 / L1_dask | `fragile_reference_id` 由哪段代码计算、为何全 false | **成立（并给出机理）** | **不由 rh2 代码产生**；数据反推判据 = stage1 gold `RESOLVED_NO ∧ f2p_missing=0 ∧ p2p_missing≥1`，是**结果派生**信号 |
| C11 | L1_moto_2 问题 3 | P-A 候选失败归因是否把安装 rc / 测试 rc 当输入 | **不成立** | `manager.py:2939-2948` test_rc≥128 直接判 resource；`:2968-2972` install_rc 与**资格基线**比较、不等即阻断候选归因 |
| C12 | L1_moto_2 / L1_moto_3 | `duplicate_clusters_v0.json` 只按 base_commit 归组 | **成立** | `ingest_swegym_lite.py:198-217` 分组键 `(repo.lower(), base_commit)`；6121/6157、7331/7335 题面 sha 相同但 base 不同，四题全不在该文件 |
| C13 | M2 | `sandbox_profile.py:517` 的 `candidate_writable_prefixes` | **部分成立** | 字段与语义成立，行号已漂到 **520** |
| C14 | L2 | `contracts/grading.py:317` 有未提交语法错误、`import repoharness2.envpack` 直接 SyntaxError | **不成立（已被修复）** | 当前树 import 成功；`tests/contracts/` 425 条全绿 |
| C15 | L1_pydantic R4 / L1_monai_1 | 恢复面只有 test_patch 触碰文件，`conftest.py` / `pyproject.toml` 不恢复 | **成立** | 两个恢复渲染器的对象都只有 test_patch 路径；只有观测、无恢复、无篡改判定 |
| C16 | L1_mypy_1 / L1_mypy_2 | 6 题 version≥1.8 的 mypy `eval_cmd` 无 `-n0` | **成立** | 16555/16869/16905/16963/16966/17071；全池另有 92 题无 `-n0`（MONAI 26、dvc 35、pydantic 20、pandas 5） |
| C17 | L6 自查 | 整树 `uv run pytest -q` 能否当绿/红判据 | **不成立** | 6 条失败是 `sys.path` 顺序造成的 import 遮蔽，见 §3 |
| C18 | L1_dvc_2 / L6 自查 | 阶段一日志无 Start/End 标记、status_map 由整份日志解析、混进 pip `ERROR:` 伪键；v2 只取标记段不回退 | **成立** | 181/181 份 gold 日志含标记数 **0**；伪键 54 种 / 148 条 / 54 题；`scoring.py:233-238` 缺标记即空映射 + `apply_ok=False` |
| C19 | M2 / L1_dask / L0 / L1_monai_1 | 各包给出的 rh2 源码行号 | **部分成立** | 结构性断言全部成立，行号偏 0–4 行（M2 `:517`→520、`:496`→497、`:502`→501、`:323`→324；L1_dask `:22-24`→18-20；L0 `:2731-2737`→2734-2741） |

**计数：20 条 —— 成立 14 / 部分成立 3 / 不成立 3 / 无法静态判定 0。**

## 3. 测试套件结果（`rh2/` 目录，`uv run pytest -q`）

```
6 failed, 2062 passed, 322 skipped, 3 warnings in 167.84s (0:02:47)   # EXIT=1，2026-09-16 03:57:33
```
完整日志：`runs/env_overnight_20260916/L6_rh2_code_check/pytest_full.log`。未做任何修复。

失败用例（6 条，全部在同一文件，错误统一是 `ModuleNotFoundError: No module named 'slime.rollout'`）：

- `tests/contract_slime_async/test_dp_schedule_differential.py::test_differential_on_j4_formal_a_class`
- `…::test_differential_on_j5_gbs16_b_class`
- `…::test_differential_on_j5_gbs20_admits_with_equal_mbs`
- `…::test_differential_randomized_sweep`
- `…::test_dynamic_filter_crashes_on_nested_fanout_shape_p3_pin`
- `…::test_dynamic_filter_accepts_flat_delivery_shape`

**这 6 条不是产品代码回归**，证据链：

1. 该文件单独跑 `uv run pytest tests/contract_slime_async/ -q` → **14 passed**。
2. 整树 `-k differential_on_j4` 复现后插桩（`runs/…/L6_rh2_code_check/l6plug2.py`）：执行时 `sys.path` 里
   `rh2/src` 在索引 **3**、`reference/slime` 在索引 **20**，`import slime` 因此解析到 vendored `rh2/src/slime`（无 `rollout` 子包）。
3. 收集结束时 `sys.modules` 里还没有 `slime`（`l6plug.py` 实测 `slime=None`）——所以是**运行期**路径顺序，不是收集期遮蔽。
4. 机制出处：`rh2/tests/adapters_miles/conftest.py:165-195` 的 module 级 autouse fixture `_vendor_slime_world`
   把 `RH2_SRC` 提到 `sys.path[0]` 再 evict `slime`，teardown 用 `sys.path[:] = saved_path` 还原。注释明写这是为了
   「后续目录（contract_slime_async 等）重新 import slime 时拿 reference/slime」，但还原的那份快照里
   `rh2/src` 本来就排在 `reference/slime` 前面，意图没达成。
5. 涉事文件（`tests/contract_slime_async/*`、`rh2/src/slime/*`、`tests/adapters_miles/conftest.py`）都**不在**本夜未提交改动清单里。

仓库的既定验收方式本来也不是整树一把梭：`rh2/scripts/miles_integration_lanes.sh` 只跑 `tests/adapters_miles/`，
按 `integration_base_manifest.json` 的 `expected_counts` 断言精确计数（双 lane）。整树 `pytest -q` 从未是门禁。

## 4. 早上最该先看的 5 条（C17 的测试套件说明见 §3，不重复）

1. **C18 — 阶段一（2026-09-10）那批 gold/empty 判定不是 v2 口径的预期，别直接拿来当基线。**
   181 份阶段一日志**一份都没有** `>>>>> Start/End Test Output` 标记，status_map 是整份日志解析出来的，
   里面混着 pip 的 `ERROR: Could not find a version…`（伪键 `Could`×35、`No`×21，共 54 种 / 148 条 / 涉及 54 题）。
   当前 v2 入口（`scoring.py:233-238`）缺标记就直接空映射 + `apply_ok=False`，**同一份日志会判成 patch_apply_failed 而不是 FULL/NO**。
   所有以阶段一为依据的结论（各包的 gold 全 FULL / empty 全 NO、p2p_missing、以及 `fragile_reference_id` 这个信号本身）都带这个前提。
2. **C11 — L1_moto_2 的前提反了，别照它的建议改。** 安装 rc 与测试 rc **已经**接在 P-A 候选失败归因上：
   `test_rc>=128` 直接判 resource→infra；`install_rc != 资格基线` 直接阻断候选归因。它担心的 moto `make init` 恒 rc=2
   已被「与基线比较」吸收。真正该修的是反向的放行过宽：C08 证明 rc=0 不代表安装成功（dvc/mypy 的段末命令掩盖失败），
   所以 `install_rc == baseline` 这一关会放过安装其实失败的运行。
3. **C05 — `additional_exclusions` 目前是废字段。** 各包（L1_mypy_2 的 15876、L1_monai_2 的 5 题、M2 的 2 条）
   都在逐题记录里写了 `file_rules.additional_exclusions`，但 `rh2/src` 全树不读这个字段。不实现消费方，这些逐题结论一条都不会生效。
   附带更坏的一点：`mypy/test/testcheck.py` 连观测 glob 都不命中，候选改测试驱动在 sidecar 里也看不见。
4. **C07 — 「恢复 checkout 漏新建路径」在正式链上已经修了，别当遗留缺陷排期。** driver/e1/e2 走的 grader profile 路径
   用 `git cat-file -e <base>:"$f"` 逐文件守卫（`prepared_task_face.py:200-206`，注释在 :185-190 明确点名这个坑）；
   只有 legacy 单脚本路径（仅 s1_compat 与单测）还会整条 `git checkout` 失败并静默不恢复。
   另外阶段一日志里「无 pathspec」是 **4 题**不是 3 题，当前代码已不可能产生该形态。
5. **C10b — `fragile_reference_id` 是结果派生信号，不是形状判据，别再拿它做筛选门槛。** 它不由任何 rh2 代码计算，
   判据等价于「stage1 gold 跑出 P2P 缺席」。截断塌缩不会让 gold 失败，所以对该类天然全 false；
   34 题根本不在 stage1 样本里，更不可能被标。L1_moto_2 提的形状判据（参考 ID 含 `[` 但不以 `]` 结尾）
   本包实测一次圈出 **35/216** 题，可直接采用。

## 5. 复核用产物

全部在 `runs/env_overnight_20260916/L6_rh2_code_check/`（不入提交）：

| 文件 | 用途 |
| --- | --- |
| `pytest_full.log` | 整树测试套件原始输出 |
| `probe_parser.py` / `probe_parser_out.json` | C01/C02/C03 的 parser 行为实跑（7 组输入 → 状态映射） |
| `idshape.py` | C10b：参考 ID 形状三类（截断 / 反斜杠 / 空格）与 `fragile_reference_id` 的交集统计 |
| `sigcheck.py` | C10b：`task_signals_swegym.json` 的 stage1 结构与 fragile 判据反推 |
| `checkout_probe.py` | C07：216 题 test_patch 触碰路径为空的题数、含 `new file mode` 的 8 题 |
| `render_probe.py` | C07：对 moto-5885 实跑两个 v2 渲染器，对比 checkout 形态 |
| `mypy_k_probe.py` | C06：mypy `-k` 表达式与子串闭包 |
| `evalcmd_scan.py` | C16：全池 `eval_cmd` 缺 `-n0` 统计 |
| `l6plug.py` / `l6plug2.py` | C17：pytest 插件，追踪 `slime` 首次 import 与失败时刻的 `sys.path` 顺序 |
| （§3/§C18 的统计用一次性 python -c，命令与输出见本报告正文，未单独落盘） | C18：阶段一 181 份日志的标记计数与 status_map 伪键统计 |

## 6. 未做

- 未核实各包的**数据面**统计总数（如 L1_moto_2 的 35 题、L2 的 72 题截断碰撞 / 53 题 `ERROR:` 行、L1_dvc_1 的 19 题 41 条 SKIPPED）：
  本包只抽验了机理与可复算的少数计数（35 题截断、8 题新建文件、4 题无 pathspec、6 题无 `-n0`、10 题 fragile）。
- 未核实 M3/L4 的 R2E 断言（那条链路在 `rh2/src` 里还没有实现代码，无源码可对）。
- 未核实 L3 的轨迹类断言（不涉及 rh2 源码行为）。
- C18 只核到「阶段一日志与 v2 口径不同源」；**没有**用 v2 口径重解析这 181 份日志（缺标记时 v2 恒空映射，重解析无意义），也没有评估把阶段一结论迁到 v2 需要多少重跑。
- 未跑 `scripts/miles_integration_lanes.sh` 双 lane（会读 `reference/miles-rh2-integration` 并要求工作树干净，本夜树不干净）。
