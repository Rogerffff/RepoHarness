# coveragepy__f5eb5f21：读历史前的私有分析（主审）

- 角色：R2E 私有主审，单题闭环试行（2026-09-29），按统一标准 v1 给暂定结论。本文在读任何历史调查之前写成并封存。
- 读过的材料：
  - 角色卡及其列出的方法文档：八方面协议、R2E 环境卡、记录模板、40 项清单、统一标准 v1。
  - `public_read.md` 与 `commands.json`。
  - 本题公开包和私有包的全部文件。
  - `run_refs.json` 指向的 4 条 RH2 账本行、2 条 M3 账本行和 6 份日志。6 份日志的 sha256 都与 `run_refs.json` 一致。
  - 两份跨题比对。
  - 同仓其它 4 题的公开包：只读了 prompt、`coverage/jsonreport.py`、`tests/test_json.py` 和少量 grep。
- 没读的材料：任何 history、旧审查目录、本批 README / board / assignments、其它题的私有包，以及 devcheck 结果（协调者第二步给出）。没有运行项目代码、测试或容器。
- 路径约定：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`
  - `WT/` = `PUB/worktree/`
  - `EA/` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/worktree/`
  - 日志和账本路径相对仓库根。

## 0. 暂定结论

| 项 | 暂定结论 | 证据级别 |
| --- | --- | --- |
| 题目 | 分支覆盖模式下，JSON 报告的 `totals` 缺 `covered_branches`、`missing_branches`，要求补上 | 题面 `PUB/user_prompt.txt:4-24` |
| 严重度 | **S1。** v1 §4 第 2 步命中（T2c）：唯一的分支模式断言只用了题面错误信息里给出的示例值 1/1。第 3 步的退化候选 D0（硬编码 1/1）预计得 1（T2b），第 4 步的构造候选 C2、C3 也预计得 1 | 第 2 步是静态事实；第 3、4 步是静态推断，待实跑 |
| 疑似误拒 | 把两键也对称加进每个文件的 `summary`（上游后来正是这样做的）会判 0。归 P3，可能转 T1，待 C1 实跑与复核 | 静态推断：测试用整字典相等 |
| 其它登记 | P6：公开 `test_branch_coverage` 与任何正确修复冲突。P4：题面说的 AssertionError 在 base 的公开测试上不出现，示例代码也不完整。X1：三处同仓关系。E5：时间戳断言，风险可忽略 | 静态分析 + 日志 |
| 用途（v1 §2） | 问题定位 yes；能力比较 conditional；训练候选 no（当前材料）；留出 no | 见 §9 |
| 修订 | R-c 两项：非示例计数；按数据门控。另外二选一：R-b（每文件 `summary` 允许出现两键，但值必须正确）或 R-f（题面补一句） | 见 §8 |
| 最关键未知 | D0、C1 的正式评分；devcheck（解题侧公开路径）；新机器重建镜像上的 noop / gold | — |
| 唯一优先下一步 | 在当前材料上一批跑 D0 与 C1，各 1 次正式评分；C2、C3 顺带 | — |

## 1. 公开读者没有捕获的条件（第 1 步）

- **实际消息。** `user_prompt.txt` 只含题面。按环境卡 §2，`public_hints`（不改测试、用 `.venv`、用 `python -m pytest` 等）写进容器的 `/rh2/public_task_bundle.json`，不注入系统提示；模型实际收到的完整消息未验证。`public_read.md` §1.1 把这些提示当作解题者已知。这会影响 P6 的解读：模型可能修改 `tests/test_json.py`，但对评分无影响，因为评分只跑 `r2e_tests`。
- **容器条件。** 评分侧有账本实测：
  - 导入的是 `/testbed/coverage/__init__.py`，版本 5.0.5a0（账本字段 `observations`）；
  - xdist 生效（日志 "bringing up nodes"）；
  - pytest 是 4.x 的输出格式（"in 0.85 seconds"）；
  - 资源为 2 CPU / 4 GiB，网络 `deny_all`，评分用户 uid 54322。
  解题侧（uid 54321）待 devcheck。
- **对 `public_read.md` 的三处小修正（都不改变结论）：**
  1. 题面错误信息不是 unittest 风格，而是 pytest 做字典比较时输出的 "Differing items" 行，逐字来自隐藏测试在 noop 上的失败输出（R-f noop 日志第 90–93 行）。所以这条错误信息同时泄露了隐藏测试的期望值，见 §4(b)。
  2. `n_partial_branches`（`WT/coverage/results.py:35`）数的是"已执行的分支行上缺失的弧数"，不是"部分覆盖的分支行数"。
  3. 原来标为未知的 R5、R7 现在有答案：
     - R5（按数据门控还是按配置门控）没有测：所有隐藏测试里配置 `branch` 与数据 `has_arcs()` 始终一致。
     - R7：隐藏测试要求每个文件的 `summary` 不加这两个键。

## 2. 隐藏测试展开（第 2 步）

隐藏测试只有 `PRIV/hidden_tests/test_1.py`（外加空的 `__init__.py`），内容就是修复提交之后的 `tests/test_json.py`。它和公开的 `WT/tests/test_json.py` 只差一处：`test_branch_coverage` 的 `totals` 多了两个键（`test_1.py:68-70`，用 diff 核过）。4 个期望键全是 PASSED（`PRIV/expected_output.json:2-5`）。

**目标键**（noop 与 gold 结果不同的键）只有 `JsonReportTest.test_branch_coverage`。noop 跑过 2 次，都是 3/4 且只错这一个键；gold 跑过 2 次，都是 4/4。

- **调用链**：
  1. `test_1.py:37-73` 调用 `_assert_expected_json_report`（`:16-35`）；
  2. `make_file("a.py")` 写入三行夹具（`:21-25`）；
  3. `start_import_stop`（`WT/tests/coveragetest.py:113-130`）：start → `import_local_file`（`WT/coverage/backward.py:226-253`）→ stop；
  4. `cov.json_report(a, outfile)`（`WT/coverage/control.py:953-975`）→ `JsonReporter.report`（`WT/coverage/jsonreport.py:24-71`；每文件部分在 `:73-99`）；
  5. `json.load` 读回报告；
  6. `assert_recent_datetime` 检查时间戳（`coveragetest.py:330-334`，要求不超过 10 秒）；
  7. 删掉 timestamp 后做**整字典相等**比较（`test_1.py:35`）。
- **最终断言**：
  - `meta` 的 3 个键；
  - `files['a.py']` 的行号列表，以及**只有 7 个键的 `summary`**（`:50-58`，不含新键）；
  - `totals` 的 9 个键，其中含 `covered_branches: 1`、`missing_branches: 1`（`:61-71`）。
- **夹具的性质**：2 个分支弧走了 1 个，于是 `n_missing_branches = n_partial_branches = n_executed_branches = 1`（`results.py:35-36`、`:201-204`）。这组数无法区分三种算法："未执行的弧数"、"已执行分支行上的缺失弧数"，以及常数 1。
- **公开依据**：两个新键和它们的数值来自题面 `:21` 与 `:28`（错误信息逐字给出 1/1）；其余断言全部来自公开旧测试 `WT/tests/test_json.py:37-71`。

**回归键**（noop 与 gold 都 PASSED）：

- `test_simple_line_coverage`（`:75-105`）；
- `test_context_non_relative` / `test_context_relative`（`:107-159`，通过 config 文件打开 `[json] show_contexts` 和 `relative_files`）。

它们用整字典相等锁定两件事：行覆盖模式下，`totals` 和每个文件的 `summary` 都不出现分支键（R4）；以及 contexts 的输出格式。

**阅读范围**：

- 读了全文：隐藏测试、`jsonreport.py`、`results.py`。
- 读了相关段落：`coveragetest.py`、`conftest.py`、`control.py`、`cmdline.py`、`xmlreport.py`、`summary.py`、`config.py`、`parser.py`（`If` / `Return` / 函数体的弧与 `exit_counts`）、`report.py`、`doc/branch.rst`、`doc/cmd.rst`。
- 没读：`sqldata.py`、插件、HTML 模板、`unittest_mixins` 源码（不在公开包里）。

## 3. 双向映射（第 3 步）

需求编号沿用 `public_read.md`。

### 3.1 公开要求 / 旧行为 → 断言

| 要求或旧行为 | 公开依据 | 断言 | 覆盖情况 | 执行证据或下一步 |
| --- | --- | --- | --- | --- |
| R1：分支模式下 `totals` 有两键 | 题面 `:7`、`:21`、`:24` | `test_1.py:61-71` + `:35` | 覆盖 | noop 缺键失败（R-f noop 日志 `:93`）；gold 通过 |
| R2：示例值 1/1 | 题面 `:28` | `test_1.py:69-70` | 覆盖，但只有这一个实例 | 同上 |
| R3：两值分别是已执行 / 未执行的分支弧数，两者之和等于 `num_branches` | `results.py:36`、`:201-204`；XML 用同一口径，本地变量名就叫 `missing_branches`（`WT/coverage/xmlreport.py:203-205`、`:122-123`）；与 `covered_lines` / `missing_lines` 命名平行（`jsonreport.py:51-57`） | 只有 a.py 一例 | **部分**：分不清正确口径、部分弧计数和常数 | D0、C2 待实跑；R-c 第 1 项 |
| R4：非分支模式不出现分支键 | `jsonreport.py:59`、`:94`；公开旧测试 | `test_1.py:75-159` | 覆盖（行模式和 contexts 两种配置） | 3 个回归键在 noop 和 gold 上都 PASSED |
| R5：按数据 `has_arcs()` 门控；文档里的 CLI 流程是 `coverage run --branch` 后单独执行 `coverage json` | `jsonreport.py:38`、`:59`、`:94`；`summary.py:20`；`xmlreport.py:60`；`doc/branch.rst:38-40`、`:52-54`；`cmdline.py:374-388`（json 子命令没有 `--branch`）、`:532-544`；`config.py:182` | 无。隐藏测试里配置 `branch` 恒等于 `has_arcs`（`test_1.py:38`、`:76`、`:116`） | **缺失** | C3 待实跑；R-c 第 2 项 |
| R6：其它输出不变 | 公开旧测试 | 各测试的整字典相等 | 覆盖（示例夹具） | — |
| R6′：`report()` 返回值（供 `--fail-under` 使用） | `jsonreport.py:71`；`cmdline.py:611-622` | 无 | 缺失（gold 没改这里，风险低） | 登记 |
| R7：每个文件的 `summary` 是否也加两键 | 题面只点名 `totals`。但 base 代码里两处分支块对称（`jsonreport.py:59-63` 与 `:94-98`），其它报告在每文件和总计两级都给分支数（`summary.py:86`、`:120`；XML 按类和总计）。上游后来也加了（`EA/coverage/jsonreport.py:97-103`） | `test_1.py:50-58` 要求每文件 `summary` 恰好 7 个键 | **争议**：对称加键的合理解会被判 0 | C1 待实跑；R-b 或 R-f |
| 多文件时 `totals` 的汇总 | `Numbers.__add__`（`results.py:249-262`） | 无（只有单文件） | 缺失（风险低） | 登记为 T3 |

### 3.2 关键断言 → 公开依据

| 断言 | 公开依据 |
| --- | --- |
| `totals.covered_branches == 1`、`missing_branches == 1`（`:69-70`） | 题面 Expected（`:21`）和错误信息（`:28`，逐字给出） |
| `files['a.py']['summary']` 恰好 7 个键（`:50-58`） | 只有公开旧测试 `WT/tests/test_json.py:50-58`，而这条旧测试同样锁定了必须改变的 `totals`（P6）；再加上题面只点名 `totals`。所以"不得额外加键"的依据弱，见 C1 |
| `meta`、三个行号列表、时间戳格式与时效 | 公开旧测试（与 base 相同） |
| 行模式下不出现分支键 | 公开旧测试 + base 的 `has_arcs()` 门控 |

**合理替代实现**：C1，把两键同时对称加进每个文件的 `summary`。**可能蒙混的实现**：D0（硬编码）、C2（用部分弧计数冒充）、C3（按配置门控）。详见 §7。

## 4. R2E 专项（第 4 步）

- **(a) 非 PASSED 的期望键：没有。** 但存在同类风险：更完整的修复 C1 会把期望 PASSED 的目标键翻成 FAILED，原因是整字典相等。
- **(b) 题面报错确实出现在 noop 目标键的失败里。** R-f noop 日志第 90–93 行：

  ```
  Differing items:
  {'totals': {'covered_lines': 2, 'excluded_lines': 0, 'missing_lines': 1, 'num_branches': 2, ...}} != {'totals': {'covered_branches': 1, 'covered_lines': 2, 'excluded_lines': 0, 'missing_branches': 1, ...}}
  ```

  同一日志还显示 "Omitting 2 identical items"，即 `meta` 与 `files` 在 noop 上已经相同。题面 `:28` 是这一行的删节版，所以题面错误信息就是隐藏测试的期望值。第 2 步的示例拟合因此是按构造必然命中。
- **(c) 题面没有直接给出修法**，不属于 P1。但它点名了键名、所在段落和示例值，而 base 的 `Numbers` 已经有 `n_executed_branches` / `n_missing_branches`，修复几乎是机械的两行。
- **(d) 依赖 base 测试辅助与搬迁伪影。**
  - 隐藏测试通过 `from tests.coveragetest import ...`（`test_1.py:11`）依赖 base 的 `tests/coveragetest.py`、`tests/helpers.py`，以及 venv 里的 `unittest_mixins`（`WT/requirements/pytest.pip:17`）。候选可以改这些文件，评分时不会重置。提示禁止这样做；这属于共享机制的观测范围，不在逐题复审。
  - `tests/conftest.py` 的三个 autouse fixture（`WT/tests/conftest.py:22-78`）对 `r2e_tests/` 不生效，根目录也没有 conftest。
  - `setup.cfg` 的 addopts（`-n3 --failed-first` 等，`WT/setup.cfg:2`）对评分同样生效。
  - 实跑证据：gold 共 4 次 4/4（RH2 2 次、M3 2 次），说明搬迁不影响这 4 个测试。只有一个隐藏测试文件，不会跨文件撞键。
- **(e) 时间、随机、资源敏感。**
  - 每个键都经过 `assert_recent_datetime`（时间差在 0 到 10 秒之间）和 `strptime(..."%S.%f")`。`datetime.now()` 的微秒恰好为 0 时，`isoformat()` 不带小数部分，`strptime` 会报错；概率约百万分之一，可以忽略。
  - 测试阶段约 2 秒，内存峰值约 280 MB。
  - 6 次运行的结果一致，只差 PASSED 行的顺序。没有随机输入。
  - 结论：不触发 E5。
- **(f) 材料修订：无。** `PRIV/revisions.json` 是 `[]`，`grading_bundle` 的 `material_revisions` 为空。

## 5. gold 检查与运行证据（第 5 步）

- **按公开要求检查 gold。** gold（`PRIV/gold.patch:9-10`）在 `has_arcs()` 分支块里给 `totals` 加了 `n_executed_branches` / `n_missing_branches`：
  - 修到了原例：题面示例在分支模式下的 `totals` 会出现两键；
  - 口径与 XML 报告和 `Numbers` 一致；
  - 门控沿用 `has_arcs()`，所以 CLI 流程也有这两个键（静态推断，devcheck 的 `repro_cli_json` 加 gold 可证实）；
  - 不影响行模式、每文件 `summary` 和 `report()` 的返回值；
  - 没有无关改动。
  上游修复提交另外改了 `CONTRIBUTORS.txt` 和测试文件，已被摄入流程排除（M3 账本 `gold_meta.excluded`），没有丢功能。**无 G1。**
- **初态。** base 17204597 就是修复提交的父提交（M3 `facts.head_is_parent_of_fix=yes`）；初始 diff 为 0 字节（`PUB/worktree_manifest.json`）。noop 在 `test_1.py:35` 失败，差异只在 `totals`，说明 base 上确实缺键，且其余输出已与期望一致。
- **运行证据（`material=current`）。** 当前材料的运行都在旧 R-f 机器的派生镜像上，镜像 `rh2-r2e-derived/coveragepy:f5eb5f215918-r2e_derive_v1`，ID `sha256:1a2107883a20…`：
  - noop：2 次，reward 0，3/4，`mismatched=[test_branch_coverage]`（`ledger_r2e_all_noop.jsonl:10`、`_rerun2/ledger_noop.jsonl:10`）；
  - gold：2 次，reward 1，4/4（`ledger_r2e_all_gold.jsonl:10`、`_rerun2/ledger_gold.jsonl:10`）；
  - gold 确已交付：`projection.included_paths=["coverage/jsonreport.py"]`；
  - 解析完整：4 个键全部解析，测试段完整，无 missing / unexpected；
  - 候选代码确实被执行：`RH2_OBS_IMPORT_PATH=/testbed/coverage/__init__.py`（清单 #9）。
  - M3 独立 runner 在来源镜像上跑 gold 2 次，都是 4/4。
  新机器重建的镜像（ID 会变）上的 noop / gold 还没看到。

## 6. 开发需求（第 6 步）

| 项 | 需求 | 证据 |
| --- | --- | --- |
| 导入 | 从 `/testbed` 运行时导入工作树里的 `coverage` | 评分侧实测（账本 `observations`）；解题侧待验（devcheck 的 `env_versions`） |
| 依赖 | pytest 4.6.6、pytest-xdist 1.30.0、flaky 3.6.1、unittest-mixins 1.6（`WT/requirements/pytest.pip:7-17`）；`setup.cfg` 的 addopts 需要前三者 | 评分侧日志显示 xdist 生效、pytest 为 4.x 格式；解题侧待验（`pytest_version`） |
| 资产 | 无 | 静态分析 |
| 权限 | agent 写 `/testbed` 与 `/tmp`；测试临时目录在 `$TMPDIR/coverage_test/`（`coveragetest.py:85-88`） | 环境说明 `PUB/environment_brief.md:12`；解题侧待验 |
| 网络 | 准备、解题、安装、测试四个阶段都不需要 | 静态分析；评分侧 `deny_all` 下 gold 通过 |
| 构建 | 无，纯 Python 修改；C tracer 与本题无关（`WT/coverage/collector.py:19-33`） | 静态分析 |
| 提交边界 | 只需改 `coverage/jsonreport.py`；R2E 按文件字节差异导出 | gold 交付已实测 |
| 公开测试 | 修复后 `tests/test_json.py::test_branch_coverage` 必然失败（P6），其余 3 个应通过 | 静态分析；待 devcheck 加 gold 对照 |
| 原例复现 | 题面示例的 `# ... execute some code ...` 若什么都没测到，会抛 "No data to report."（`WT/coverage/report.py:65-66`）。替代复现：`commands.json` 的 `repro_api_totals`，修复前退出码非 0，修复后为 0 | 待 devcheck |

## 7. 候选（请协调者用正式评分实跑；描述可直接改成补丁，行号按 base）

**D0：v1 第 3 步的退化候选（与输入无关的固定结果）。**

- 改法：`coverage/jsonreport.py` 的 `JsonReporter.report`，在 `if coverage_data.has_arcs():` 的 `totals.update({...})` 里（`:60-63`，与 gold 同一个 hunk）加两行：

  ```python
                  'covered_branches': 1,
                  'missing_branches': 1,
  ```

- 预期：reward 1（4/4）。
- 违反的公开要求：R1/R3，即两值要反映被测代码的分支覆盖（题面 `:21` 说 "providing detailed branch coverage information"）。
- 能看出错误的输入：附录 B 的 `BRANCHY` 夹具，正确值是 4/2，D0 仍报 1/1。
- 实跑时核对：`projection.included_paths` 为 `["coverage/jsonreport.py"]`，`num_parsed_tests` 为 4，测试段完整。

**C1：合理替代解（规格争议）。**

- 改法：gold 那两行，再在 `report_one_file` 的 `has_arcs()` 块（`:95-98`）加：

  ```python
                  'covered_branches': nums.n_executed_branches,
                  'missing_branches': nums.n_missing_branches,
  ```

  这与上游后来的形态一致（`EA/coverage/jsonreport.py:97-103`，其测试见 `EA/tests/test_json.py:50-60`）。
- 预期：reward 0。`test_branch_coverage` 会 FAILED，因为 `files['a.py']['summary']` 多两个键；其余 3 个 PASSED。
- 判断：它满足全部公开要求（题面的 `totals` 要求），也不破坏任何有依据的旧行为（每文件 `summary` 只是多了键；锁定旧形状的公开测试本来就会被必需的 `totals` 改动打破）。按角色卡补充规则 1，这是"疑似规格争议的待复核样本"，原始 reward 保留。

**C2：错误口径（可能蒙混）。**

- 改法：在 `totals` 块里加：

  ```python
                  'covered_branches': self.total.n_branches - self.total.n_partial_branches,
                  'missing_branches': self.total.n_partial_branches,
  ```

- 预期：reward 1，因为夹具里 `n_partial == n_missing`。
- 违反 R3：对从未执行过的分支行，它的弧不计入 missing，反而算作 covered。例如 `BRANCHY`：它会报 covered 6、missing 0，而函数 `h` 里的 `if` 根本没跑。正确值是 4/2，XML 报告会给 `branches-covered="4"`。
- 用途：第 4 步的证据，也作为 R-c 验收时的负对照。

**C3：按配置门控（可能蒙混）。**

- 改法：`totals` 原有的 `has_arcs()` 块不动，在它之后、`json.dump` 之前（`:64-65` 之间）加：

  ```python
          if self.config.branch:
              self.report_data["totals"].update({
                  'covered_branches': self.total.n_executed_branches,
                  'missing_branches': self.total.n_missing_branches,
              })
  ```

- 预期：reward 1，因为所有隐藏测试里配置 `branch` 与 `has_arcs()` 一致。
- 违反 R5，即文档里的常用 CLI 流程：先 `coverage run --branch`，再单独执行 `coverage json`。后一个进程的 `config.branch` 为 False（`cmdline.py:532-544`，`config.py:182`，工作树里也没有任何 rc 设置 `branch`），于是 `meta.branch_coverage` 为 true、`num_branches` 也在，但 `totals` 缺这两键。
- 能看出错误的输入：公开命令 `repro_cli_json`。
- 用途：第 4 步的证据；R-c 第 2 项的负对照。

**可选私有核对（便宜；不进解题者材料）：**

- P-1：以 agent 身份执行 `cd / && /testbed/.venv/bin/python -c "import coverage; print(coverage.__file__, coverage.__version__)"`，看 `/testbed` 以外有没有另装一份 coverage。如果装的是更新版本，里面就含有答案（清单 #29）。
- P-2：应用 C3 后跑公开命令 `repro_cli_json`。预期 `totals` 没有两键，作为 C3 违规的行为证据。
- P-3：应用 gold 后用 API 测 `BRANCHY`，同时出 `coverage xml`。预期 JSON 为 6/0/4/2，XML 为 `branches-valid="6"`、`branches-covered="4"`。这一步用来独立核对附录 B 的推导；**R-c 的期望值不能直接抄 gold 的输出。**

**devcheck 结果需要核对的点**（`commands.json` 6 条；初态和私有 gold 对照各一遍）：

- `env_versions`：python 为 `/testbed/.venv/bin/python` 3.7.9，coverage 来自 `/testbed/coverage`。
- `pytest_version`：退出码 0，能看到 xdist 和 flaky。
- `repro_api_totals`：初态退出码 1（`BUG PRESENT`，`totals` 7 个键）；gold 下退出码 0。
- `repro_cli_json`：gold 下 `totals` 有 1/1。
- `public_test_json`：初态 4 passed；gold 下只有 `test_branch_coverage` 失败。这是 P6 的预期结果，不能判为环境故障。
- 墙钟时间。
- R2E 隔离预检：HEAD 没有子提交、隐藏测试不可读。来源镜像里修复提交是可达的（M3 `facts.fix_reachable=commit`，`commits_after_head=2325`），派生镜像按配方已清除，需要在本题镜像上确认。
- 新镜像上 noop 为 0、gold 为 1。

## 8. 修订建议（v1 §5）

### R-c：补有公开依据的非示例断言

放在 `PRIV/hidden_tests/test_1.py` 的 `JsonReportTest` 里，**只断言 `totals`**，对 C1 的争议保持中立。

**第 1 项（必需）：非示例计数。**

- 公开依据：R3（`results.py:36`、`:201-204`；`xmlreport.py:203-205`；命名与 `covered_lines` / `missing_lines` 平行）。
- 解决的问题：第 2 步 T2c；第 3 步 D0；第 4 步 C2。

**第 2 项（建议纳入）：从保存的分支数据出报告，报告对象本身不设 `branch`。**

- 公开依据：R5（`doc/branch.rst:38-40`、`:52-54`；`cmdline.py:374-388`、`:532-544`；各报告器都按 `has_arcs()` 门控）。
- 解决的问题：C3。
- 复核如果认定 CLI 流程不属于同一核心要求，可以把 C3 降为 T3 登记，不补这一项。

代码（期望值来自附录 B 的静态推导，由 P-3 交叉核对）：

```python
    BRANCHY = """\
        def f(x):
            if x:
                return 1
            return 2

        def g(x):
            if x:
                return 1
            return 2

        def h(x):
            if x:
                return 1
            return 2

        f(0)
        f(1)
        g(0)
        g(1)
        """

    def _branchy_report(self, modname, report_from_saved_data=False):
        """Measure BRANCHY with branch=True and return the parsed JSON report."""
        self.make_file(modname + ".py", self.BRANCHY)
        cov = coverage.Coverage(branch=True)
        mod = self.start_import_stop(cov, modname)
        if report_from_saved_data:
            # Like `coverage run --branch` followed by a separate `coverage json`:
            # the reporting object's own config does not set branch.
            cov.save()
            cov = coverage.Coverage()
            cov.load()
        output_path = os.path.join(self.temp_dir, modname + ".json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            return json.load(result_file)

    def test_branch_totals_count_branch_arcs(self):
        # f and g take both branches of their `if`; h never runs:
        # 6 branch destinations, 4 taken, 2 never taken, no partial branch line.
        totals = self._branchy_report("branchy")['totals']
        assert totals['num_branches'] == 6
        assert totals['num_partial_branches'] == 0
        assert totals['covered_branches'] == 4
        assert totals['missing_branches'] == 2

    def test_branch_totals_from_saved_branch_data(self):
        report = self._branchy_report("branchy_saved", report_from_saved_data=True)
        assert report['meta']['branch_coverage'] is True
        assert report['totals']['covered_branches'] == 4
        assert report['totals']['missing_branches'] == 2
```

`expected_output.json` 增加两个键：`"JsonReportTest.test_branch_totals_count_branch_arcs": "PASSED"`、`"JsonReportTest.test_branch_totals_from_saved_branch_data": "PASSED"`。

`num_branches` 与 `num_partial_branches` 是 base 已有的行为。把它们也断言上，是为了锚定夹具：如果 gold 在这两处失败，说明推导错了，应当改夹具，而不是改期望值。

### C1 的争议：二选一，不同时做

- **R-b（我的倾向）。** 在 `_assert_expected_json_report` 增加可选参数 `optional_summary`：每文件 `summary` 里如果出现两键，其值必须等于该文件的已执行 / 未执行弧数，并在比较前 `pop` 掉；其余键仍做整字典相等，`totals` 和行模式测试不变。
  - `test_branch_coverage` 调用时传 `optional_summary={'a.py': {'covered_branches': 1, 'missing_branches': 1}}`。
  - R-c 第 1 项同时加上"如果 `files['branchy.py']['summary']` 里有这两个键，必须是 4/2"。
  - 理由：C1 满足全部公开要求，禁止每文件额外加键没有公开依据；v1 §0 要求环境不让正确解失败。
  - 这不属于 P5 那种"两种相反输出取'或'"：`totals` 的目标仍然严格；每文件的两键只是可选的附加信息，出现时仍要验值。
- **R-f（备选）。** 如果复核认为题面"只说 `totals`"已经足以支撑测试的读法，就在题面 Expected Behavior 后补一句："Only the `totals` section is in scope; the per-file `summary` entries under `files` stay as they are."
  - 公开依据：题面 `:7`、`:21`、`:24`，以及 `WT/tests/test_json.py:50-58`。
  - 前提：R2E 题面文本替换类已实现（v1 §9 D6），并由新的公开读者验收。
- 选哪一种属于模板内的判断，由复核裁定；两者都不改变 `totals` 的要求。

### 验收计划（一轮，按 v1 §5）

新材料上逐一实跑：

| 候选 | 预期 reward | 预期失败的键 |
| --- | --- | --- |
| gold | 1 | 无 |
| noop | 0 | `test_branch_coverage` 与两个新键 |
| D0 | 0 | 两个新键 |
| C2 | 0 | 两个新键 |
| C3 | 0 | 只有第 2 项 |
| C1（采用 R-b 时） | 1 | 无，本次误判被纠正 |
| C1-swap（每文件两值对调、`totals` 正确，仅采用 R-b 时） | 0 | R-c 第 1 项的每文件检查 |

修订后仍受保护的公开要求：R1、R3（非示例实例）、R4（行模式形状）、R5、R6（示例夹具的其余输出）。保存新版本、父版本、理由和触发反例后，交 Codex 复核。预计约 7–9 次正式评分。

## 9. v1 严重度与用途（暂定）

- **严重度步骤：**
  - 第 1 步：核心要求有直接断言（`test_1.py:61-71`），不命中。
  - 第 2 步：命中，T2c，理由见 §4(b)。
  - 第 3 步：D0 预计得 1，待实跑。
  - 第 4 步：C2、C3 预计得 1，待实跑。
  - 结论：**S1**。
  - 另有 P3 / 疑似 T1（C1）、P6、P4、X1、T3（多文件汇总、`report()` 返回值），以及 E5（可忽略）。没有 X2：题面、base、测试、gold、日志相互一致。没有 D1、T5、G1、E1–E4。
- **X1（同仓关系）：**
  - `coveragepy__ea6906b0` 的初态含本题答案：gold 的 2 行逐字出现在 `EA/coverage/jsonreport.py:65-66`。
  - `coveragepy__97997d2c` 与本题 base 相同，两边公开工作树逐字节一致（`diff -rq` 无差异），题意无关，互不包含对方的修复。
  - 本题初态已含 `016af5f6` 和 `5dbbe143` 的修复：`WT/coverage/control.py:337` 的 `once` 参数，`WT/tests/test_oddball.py:566`、`WT/tests/test_api.py:557` 的测试。
  - 测试名扫描对本题没有输出，因为隐藏测试里没有新的测试名。
  - 按 D3 以仓库划分时，这几题落在同侧；训练时控制同一初态的重复采样。
- **用途（`usage.v1`）：**
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。还差三项：devcheck 对公开开发路径的实测；新镜像上 noop 为 0、gold 为 1；C1 争议单列，原始 reward 与语义结论分开记。
  - `training_candidate`：no。当前材料有未处理的 S1；R-c 加上 R-b 或 R-f 验收后重新评估。
  - `heldout_candidate`：no。原因同上；修订之后也只能作"标明版本的自建题"。
- **暂定处置：** `scope=static_review`，`state=needs_review`。原因有三条：
  1. S1 需要测试层修订 R-c；
  2. 题意 / 测试争议（C1）；
  3. 静态候选待 actor 验证。

## 10. 八方面覆盖与 `checks` 草稿

| 方面（清单编号） | 已查 | 未查或缺口 |
| --- | --- | --- |
| 公开需求（3、23） | 题面、提示、文档、代码；需求表 R1–R9 | 模型实际收到的消息（#3 unknown）；R7 争议（#23 issue） |
| 材料与初始问题（1、2、27） | 版本与 sha 一致；base 是修复提交的父提交；noop 的失败位置 | 新镜像（#1、#2 在旧镜像上 pass） |
| 测试是否测到要求（18–20、25、32） | 隐藏测试全文；4 个键解析完整；noop/gold 的分差来自目标键 | #25、#32 issue（只有示例值；D0、C2、C3） |
| 是否误拒（24、28） | C1 构造 | #24 issue，待实跑；#28 在修订验收时检查 |
| 回归与 gold（26、27） | gold 正确，回归键保护 R4 | `report()` 返回值、多文件、CLI 流程无测试（T3 / R5） |
| 开发条件（6–15） | 评分侧实测；网络与资源 | 解题侧（#8、#10）待 devcheck；#15 并发未查 |
| 交付与评分边界（4、16–17、21–22、29–31） | gold 已交付；隐藏测试的放置；M3 独立 runner 对照一致 | #29 解题侧泄漏预检待 devcheck；#31 共享机制（根目录 conftest、测试辅助）不逐题复审 |
| 题目关系与用途（5、37–40） | X1 三处关系 | #37–#40 不适用（无修订） |

`checks` 草稿：

| 状态 | 编号 |
| --- | --- |
| pass | 1、2、4、9、11、13、14、16、17、18、19、20、21、22、26、27 |
| issue | 5（X1）、23、24、25、32 |
| unknown | 3、6（解题侧）、8、10、29 |
| not_checked | 15、31、33–36 |
| not_applicable | 37–40 |

## 附录 A：证据摘录

- **隐藏测试与公开测试的差异**：只在 `totals` 增加两键（`test_1.py:68-70`）。其余逐字相同，包括每文件 `summary` 的 7 个键（`:50-58`）。
- **R-f noop**（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-c_d76ba3af.eval.log`）：
  - 第 89–101 行：`assert parsed_result == expected_result` 失败，"Omitting 2 identical items"，差异项只有 `totals`；
  - 第 104–108 行：3 passed、1 failed；
  - `RH2_TEST_RC=1`。
- **R-f gold**（`…all-gold-c_495f77c4.eval.log`）：
  - 第 22–26 行：4 passed；
  - 第 1 行的 git status 为 ` M coverage/jsonreport.py`。
- **环境轮复跑**（`runs/r2e_env_repair_20260924/_rerun2/…_9e168ae0`、`…_e7615d5b`）：与 R-f 相比只差 PASSED 行顺序和耗时。
- **账本共同字段**：
  - `grading_semantics=r2e_expected_map`，`keys_equal=true`；
  - `policy`：2 CPU、4 GiB、`deny_all`、uid 54322；
  - `install_skipped=true`；
  - 测试阶段约 2.4 秒，`grader_trusted_setup` 约 16 秒；
  - 同一镜像 ID `1a2107883a20…`（旧机器）。
- **M3**（`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:45`、`:91`）：
  - 来源镜像 digest `fb0335af…`；
  - gold 两次 4/4；
  - `gold_meta.excluded` 为 `CONTRIBUTORS.txt` 和 `tests/test_json.py`。

## 附录 B：`BRANCHY` 夹具的静态推导（待 P-3 核对）

行号：

| 行号 | 内容 |
| --- | --- |
| 1–4 | 函数 `f` |
| 6–9 | 函数 `g` |
| 11–14 | 函数 `h` |
| 16–19 | 调用 `f(0)`、`f(1)`、`g(0)`、`g(1)` |

推导步骤：

- **每个 `if` 有 2 个出口。** 依据 `WT/coverage/parser.py:930-936`：body 那一侧连到 `return 1`；没有 else 时，另一侧连到下一条语句 `return 2`。两个 `return` 各只有一个出口，指向函数退出（`:953-958`）。模块层每条语句也只有一个出口。所以分支行是 2、7、12，`num_branches = 6`（`results.py:118-120`）。
- **执行情况。** `f(0)` / `f(1)` 走过 2→4 与 2→3；`g` 同理走过 7→9 与 7→8。`h` 从未调用，所以 `missing_branch_arcs = {12: [13, 14]}`，`n_missing_branches = 2`（`results.py:36`）。
- **部分分支。** 第 12 行本身属于未执行的语句，所以不计入 `n_partial_branches`，结果为 0（`:35`）。
- **结果。** `covered_branches = 6 - 2 = 4`。
- **补充（不在断言里）。** 语句 16 条、缺失 3 条（12–14），`percent_covered = (13 + 4) / (16 + 6) × 100 ≈ 77.27`。
- **四个值互不相同（6、0、4、2）。** 所以常数 1/1、部分弧计数口径（6/0）、两值对调（2/4）都会失败。
