# 来源适配器一致性卡：R2E-Gym-Subset

日期：2026-09-16 夜 · L4（全静态分析，未起容器、未连机器）。对应[清单意见 S9](../../environment_screening_checklist_claude_review_20260915.md#s9--缺来源适配器一致性这一层)与[最小约定 §2](../../environment_screening_definition_20260915.md)。
适用范围：`R2E-Gym/R2E-Gym-Subset` revision `e8b9fcbce43eaca0dc2c0d4798ee6f3e965f590a`，镜像 `namanjain12/<repo>_final:<commit>`，本卡由 48 题（`r2e_tasks_48.json`）的实测证据支撑；同 revision 其余 4,530 题**未验证**。
本卡区分：`[实测]` 有本地运行/快照证据；`[代码]` 读 Prime/我们的 probe 源码得到；`[未查]` 需要机器（编号指向 `machine_checks.md`）。

## 1. 输入字段与初态

| 项 | 事实 | 证据 |
| --- | --- | --- |
| 数据行字段 | `repo_name / docker_image / commit_hash / problem_statement / prompt / parsed_commit_content / execution_result_content / expected_output_json / modified_files / modified_entity_summaries / relevant_files / num_non_test_{files,func_methods,lines}` | `r2e_candidates_full.jsonl` 首行字段枚举 `[实测]` |
| 题面 | `problem_statement`（`[ISSUE]` 开头的合成 issue，48 题 593–1,551 字符，中位 1,123）。`prompt` 是**题面生成指令**，不是 solver 输入 | `r2e_task_facts.json.problem_statement_chars`；Prime loader 只用 `problem_statement` `[代码]` |
| 初态 HEAD | 48/48 `HEAD = 修复提交的父提交`（`head_is_parent_of_fix=yes`） | 账本 `facts` `[实测]` |
| **初态不是干净树** | 镜像把"让旧代码在新 Python/新构建链上跑起来"的补丁留在**未提交**状态。已实测 6 题有已跟踪文件修改：aiohttp 3 题把 `asyncio.async` 改成 `asyncio.create_task`（`aiohttp/{client,server,worker}.py`）；pandas 3 题删掉 `pyproject.toml`、改 `setup.cfg`/`versioneer.py`/`pandas/{__init__,_version}.py`。48/48 `git status --porcelain` 行数在 2–7 之间（含未跟踪） | `.../observations/<key>/pre_test.diff`；账本 `facts.status_lines` `[实测]`；旧 24 的逐文件清单 `[未查 M-06]` |
| 未跟踪文件 | 至少含 `run_tests.sh`（Prime 的 `snapshot_untracked` 注释也把它列为 R2E 镜像自带未跟踪文件）与 `.venv` | 精读 `prime_swe_tasksets_validation.md` §3.3 `[代码]`；完整清单 `[未查 M-06]` |
| venv | `/testbed/.venv`，Python 3.7.9（24 题）/ 3.8.20（4）/ 3.9.21（19）/ 3.10.16（1） | 账本 `facts.venv_python` `[实测]`；属主与可写性 `[未查 M-03]` |
| 镜像大小 | 0.84–3.73 GB（只有 24 题有 inspect 记录，另 24 题 `[未查]`） | `runs/env_probe_stage1_20260910/logs/r2e_all24_image_facts.json` `[实测]` |
| **修复提交在镜像 git 库里可达** | 48/48 `fix_reachable=commit`；HEAD 之后还有 710–31,448 个提交可达，`git for-each-ref` 83–327 条，`git tag` 77–289 个，`remotes=1` | 账本 `facts` `[实测]`；`git branch --contains` / `git remote -v` 细节 `[未查 M-05]` |

**这条对 rh2 的直接后果**：任何"恢复干净初态"的实现（`git checkout .` / `git reset --hard` / `git clean -fd` / `git stash`）都会**破坏环境**（aiohttp 在 Python 3.9 上没有那三处改动会直接 import 失败）。候选 delta 也不能用 `git diff HEAD` 取——rh2 现有的 baseline census + patch exporter 路线（materialize 尾部对容器树做一次 census，模型介入前）天然正确，**不要为 R2E 换成 git-based 提取**。

## 2. agent 可见 / 私有材料

| 材料 | 谁可见 | 事实 |
| --- | --- | --- |
| `problem_statement` | agent | 合成 issue；R2E 的生成 prompt 要求不提测试函数/文件名、不泄露解法，但这是 prompt 约束不是实测泄漏率（`O03_r2e_gym.md` §2.3） |
| `/r2e_tests`（隐藏测试） | **镜像里默认存在、默认可读** | 48/48 `r2e_tests_root` 为 1–5 个条目，`/testbed/r2e_tests` 起始为 0 `[实测]`。Prime 的 `R2EGymTask.setup()` 会把 `/r2e_tests` 打包搬到 host 并从沙箱删除，评分时再放回 `[代码]`。**rh2 必须自己实现这一步，否则隐藏测试直接可读** |
| `run_tests.sh` | agent 可读、**可能可写** | 在 `/testbed` 里，Prime 也没搬走 `[代码]`；权限 `[未查 M-02]` |
| gold patch | 不给 agent | 但 `git show <fix_commit>`、`git log --all` 可直接取到完整上游提交（含测试改动）`[实测 fix_reachable]` |
| `expected_output_json` | 不在镜像里 | 48/48 `facts.expected_file=0`（只查了 `/testbed/expected_test_output.json` 与 `/expected_test_output.json` 两条路径）`[实测]`；全盘扫描 `[未查 M-08]` |
| 仓库自带测试目录 | agent 可读**可写** | 这是本来源最大的一处可见性差异，见 §7.3 |

**题面里的测试样标识**：扫过 48 个 `problem_statement`，5 题出现 `test_*` / `Test*` 标识，其中 aiohttp `240da100` 的复现片段逐字给出了该题唯一判别用例的类名与方法名（`ProxyConnectorTests.test_request_port`）`[实测]`。R2E 的题面是由 commit + 测试 diff + 执行结果反译出来的，复现片段像测试代码属于设计，不自动等于泄漏；但"不提测试函数/文件名"只是生成 prompt 的要求。

**"测试生成时可见 gold" 的含义**：R2E 在**造题阶段**用 ground-truth patch 条件化地生成 `/r2e_tests`（`O03_r2e_gym.md` §2.3，Appendix A p.16）。这不是推理期泄漏，但意味着隐藏测试可能**精确贴合 gold 的实现细节**（清单第 24 项"测试是否错误地强制唯一实现"在本来源上风险偏高）；本轮没有做合法替代解实验，该项记 `not_checked`。

## 3. 真实入口

- 入口固定为 `/testbed/run_tests.sh`，工作目录 `/testbed`，Prime 以 `/bin/bash run_tests.sh 2>&1` 调用，只把合并后的输出交给 parser `[代码]`。
- 48 题实测三种形态 `[实测]`：
  - 40 题：`PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' .venv/bin/python -W ignore -m pytest -rA r2e_tests`
  - 7 题（orange3 全部）：前面加 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`
  - **1 题（pillow `3ac9396e`）：`.venv/bin/python -W ignore r2e_tests/unittest_custom_runner.py`——不是 pytest**。读过该文件（本地快照 153 行）`[实测]`：它是一个 `unittest.TestResult` 子类，`loader.discover("r2e_tests")` 收集，**手工打印一段 `short test summary info`**，行形如 `PASSED <module>::<Class>::<method>`，所以 Prime 的 `split("::")[1:]` 规则恰好适用（该题 expected 11 键与 AST 里的 11 个测试一一对应）。三个要注意的点：① 它也打印 `SKIPPED` 行，同样会被 parser 丢掉；② `_ErrorHolder` 回退分支只产出 `module::Class` 两段，键会退化成类名；③ `discover` 只收 `unittest.TestCase` 子类，pytest 风格的模块级测试函数不会被收集。
- `-rA` 是关键：`short test summary info` 段必须包含全部用例，parser 只读这一段。rh2 若换入口或加 `-p`/`-q`/分片，会改变该段内容。
- **不要把 `run_tests.sh` 重写成 rh2 自己的 pytest 命令**：至少那 1 题不是 pytest，7 题需要 xvfb，且各题的环境变量不同。正确做法是照原样执行并只在外层加超时与输出捕获。

## 4. 测试选择与收集

- 选择器就是目录 `r2e_tests`，没有 `-k`、没有 node id 列表、没有额外 eval_commands `[实测]`。
- 评分前的 setup（Prime 与我们的 probe 一致）`[代码]`：`rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests`，再清 `__pycache__`。所以 agent 在 `/testbed/r2e_tests` 下写的任何东西都会被覆盖，**但仓库自带测试目录不会被恢复**。
- 隐藏测试的组成 `[实测，仅新 24]`：`test_1.py` 必有；4 题有 `test_2.py`；5 题有 `conftest.py`；3 题有 `helper.py`；1 题有 `unittest_custom_runner.py`。旧 24 `[未查 M-01]`。
- **fixture 没有被移植**：测试从仓库原位置抽到 `/testbed/r2e_tests/`，仓库的 `conftest.py` 层级不再生效。实测后果见 §7.1。

## 5. parser 与版本

Prime `parse_log_pytest` + `calculate_reward`（我们的 `rh2/experiments/env_probe_20260909/r2e_probe.py` 是逐字复刻，`runner_version=r2e_probe/0.3`）：

1. 先 `re.sub(r"\x1b\[[0-9;]*m|\r", "", output)` 去掉日志侧 ANSI 与 CR；
2. 只取 `short test summary info` 之后的部分，**没有这一段就返回空映射**；
3. 逐行：含 `PASSED` → 键 = `nodeid.split("::")[1:]` 用 `.` 连接（**文件路径被丢掉**）；含 `FAILED`/`ERROR` → 同样取名再 `split(" - ")[0]`；
4. `calculate_reward`：对**期望侧**做 `_decolor`（Prime 原版只删 `[数字m`，**不删 ESC 字节**），再 `split(" - ")[0]`；然后 `len(parsed) != len(expected) → 0`；再对每个**非空** parsed 键要求存在于 expected 且状态相同。

> **勘误（2026-09-20，B 线 Claude）**：下文关于"Prime `_decolor` 只删 `[数字m`、不删 ESC，pillow 6 题按原版 gold 恒为 0"的说法是误读，已撤回。固定源码 `prime-envs@c4d04dfe…/environments/swe/r2e_gym/r2e_gym/taskset.py` 的正则是 `\x1b\[\d+m`（ESC 是源文件里的不可见字节）；A 线用固定源码的三个纯函数重放 336 份既有日志，与本地 runner 的 reward 全部相同，pillow 六题 24 次 gold 全为 1。见 [R2E 接线计划复核](../../r2e_grading_wiring_review_20260920/README.md) R1 与 [09-09 远端核查 §3.1](../../env_probe_20260909/codex_remote_check_20260909.md)。原文保留不改。

**已知的两处实现分歧，必须先定版本口径**：

| 分歧 | Prime 原版行为 | 我们 `r2e_probe/0.3` 的行为 | 影响面 |
| --- | --- | --- | --- |
| ANSI | 日志侧完整去 ANSI，期望侧只删 `[数字m` → `'\x1b[1mtest_sanity\x1b[0m'` 变成 `'\x1btest_sanity\x1b'`，与日志侧 `'test_sanity'` 永不相等 | 两侧都先删完整 ANSI 序列再套 Prime 规则 | **pillow 6 题**：期望键 100% 带 `\x1b[1m…\x1b[0m`（实测 `2b061b68` 55/55、`4bc64835` 24/24）。按 Prime 原版这 6 题 reward 恒为 0 `[实测+代码]` |
| 空键 | `if k and (...)` 跳过空 parsed 键 → 键集不等也可能给 1 | 不特殊处理（我们的 reward 函数复刻了这一行，但 rh2 工作区里的 `expected_map_matches` 用并集，更严） | 48 题实测 `n_missing/n_extra` 全为 0，未触发 `[实测]` |

**键塌陷风险**：键丢掉文件路径，所以 `test_1.py::TestX::test_a` 与 `test_2.py::TestX::test_a` 会塌成同一个键。48 题里有 4 题是双测试文件（`5dbbe143`、`58ba5165`、`87787609`、`3ac9396e`）。对这 4 题做了 AST 级检查：把两个文件里的模块级 `test*` 函数与 `Class.method` 全列出来，**四题都没有跨文件同名**（3ac9396e 11 键、58ba5165 4 键、5dbbe143 59 个函数名、87787609 24 个函数名）`[实测]`。参数化展开后的塌陷仍要实跑收集确认 `[未查 M-11]`；旧 24 连测试文件个数都不知道。

**SKIPPED / XFAIL 被静默丢弃**：parser 只认 PASSED/FAILED/ERROR。pytest `-rA` 的跳过行形如 `SKIPPED [9] r2e_tests/test_1.py:1059: Missing SciPy requirement`——**连测试 id 都没有**，即使想支持也恢复不出名字。48 题里 **14 题**的 gold 日志摘要里有这类行，单次运行合计丢掉 **38 个用例** `[实测]`：

| 题 | 丢弃 | 原因（摘录） |
| --- | --- | --- |
| pandas `19c5eea5` | 9 SKIPPED + 1 XFAIL | `Missing SciPy requirement` |
| orange3 `f5026689` | 6 SKIPPED | `orangewidget/tests/base.py`（GUI 相关） |
| orange3 `22e98f8f` / `50f6a758` / `f237f968` / `c3fb72ba` | 各 3 SKIPPED | 同上 |
| aiohttp `4075c653` | 2 SKIPPED | `C based HTTP parser not available` |
| pandas `4ec87eb9` | 2 SKIPPED | `Unclear numpy expectation for nearest result` |
| pandas `32dd55cb` | 1 SKIPPED | `Missing SciPy requirement` |
| pandas `294cbc8d` | 1 SKIPPED | `on PyPy deep=True does not change result` |
| coveragepy `016af5f6` | 1 SKIPPED | `This is too expensive for now (30s)` |
| orange3 `9b5494e2` | 1 SKIPPED | `Re-enable when Logistic regression support…` |
| datalad `19f5b450` | 1 SKIPPED | `_pytest/unittest.py:385` |
| datalad `6b6fa389` | 1 XFAIL | `reason: [NOTRUN]` |

上游用同一个 parser 生成 expected，所以这些用例两侧都不在，**正常情况下不影响判分**。危险在于它们的跳过条件是**环境**（装没装 scipy、C 扩展有没有构建、有没有 GUI）：条件一变，键数就变，`len(parsed) != len(expected)` 直接判 0。

## 6. 评分规则与计数（方案 A）

- 来源语义：`reward = 1 ⇔ 观测状态映射 == 期望状态映射`（键集相等且每键状态相等），**不是 "F2P 由败转胜 + P2P 不回归"**。期望值可以是 `PASSED / FAILED / ERROR / SKIPPED` 中任意一个。
- rh2 侧已按用户 2026-09-15 的决定实现了方案 A，但**目前只在工作区、未提交**：`contracts/grading.py` 的 `grading_semantics: Literal["swe_f2p_p2p","r2e_expected_map"]` + `expected_match_count/expected_total_count`，`envpack/scoring.py` 的 `ExpectedMapMatch` / `expected_map_matches` / `grading_outcome_fields_r2e`。`git show HEAD:...grading.py` 里没有 `grading_semantics` `[实测]`。本包没有改动这两个文件。
- `expected_map_matches` 的口径是**期望键 ∪ 观测键**：多出或缺少键都让 `match < total`，`resolved ⇔ keys_equal and match == total > 0`。这比 Prime 的"长度相等 + 非空 parsed 键逐一匹配"**更严格但方向一致**，没有把"多出键"误判成 resolved。
- 仍缺的实现：R2E 的 **parser（第 5 节的四步）**、**expected 映射的运输**（不在镜像里，必须随 bundle 下发并进私有面）、**taskset ingest**、**入口执行与 `/r2e_tests` 搬运**。`rh2/src` 里目前没有任何 R2E parser 或 taskset 代码 `[实测：grep]`。

## 7. 已知限制（本轮新增的都带证据）

### 7.1 期望映射里混着环境缺陷，不是题目语义

48 题 2,650 个期望键里 **93 个不是 PASSED**，分布在 **20 题** `[实测]`。逐题查 gold 日志的错误行后，几乎全部是抽取/环境缺陷的快照：

- **`fixture 'X' not found`：58 个 ERROR 键，覆盖 pandas 全部 7 题 + orange3 `f237f968` 1 题。** 测试被抽到 `/testbed/r2e_tests/` 后，`pandas/conftest.py` 定义的 `frame_or_series`、`float_frame` 等 fixture 不再可见，于是 setup 阶段报错。这些键**必须原样复现 ERROR** 才能拿 reward 1。
- `TypeError: test_dirty() got multiple values for argument 'path'`：datalad `16c1ffc3` / `9ba5de09`，nose 风格装饰器在 pytest 下失效。
- `NameError: HttpRequestParserC is not defined`：aiohttp `4075c653`，C 扩展没构建。
- `ModuleNotFoundError: No module named 'testegg'`：scrapy `cfed9b66`，测试资产缺失。
- `TypeError: cannot 'yield from' a coroutine object` / `'str' object has no attribute 'decode'` / `a bytes-like object is required`：aiohttp `240da100`、orange3 `9b5494e2`、scrapy `9a15fcf8`，Python 版本迁移残留。
- coveragepy `016af5f6`：期望 `MockingProtectionTest.test_os_path_exists = FAILED`（作者环境子进程缺 `mock`），我们的容器里实测 **PASSED** → gold reward 0 `[实测]`。

**后果**：我们只要把环境修好一点（补 conftest、装上 `mock`、构建 C 扩展），这些题的 gold 就从 1 掉到 0。这不是"题目更难"，是 oracle 记录了坏环境。

### 7.2 fixture 缺失（datalad 类）可以静态检出

gold 补丁按 Prime 规则**排除全部测试路径**（48/48 都有被排除的测试文件 `[实测]`），于是"上游提交里对测试 helper 的修改"不会被移植。用隐藏测试的 import 与 gold 排除清单做交集，本轮命中 2 题 `[实测，仅新 24]`：

- datalad `58ba5165`：隐藏测试 `from datalad.interface.tests.test_docs import ...`，gold 排除 `datalad/interface/tests/test_docs.py` → gold reward **0**（已知反例）。
- coveragepy `5dbbe143`：隐藏测试 `from tests.coveragetest import ...`，gold 排除 `tests/coveragetest.py` → gold reward **1**（本次这道题不需要那处改动，属**潜伏**风险，不是现行故障）。

旧 24 没有隐藏测试文本，同类检查 `[未查 M-01 + M-07]`。

### 7.3 仓库自带测试目录是可写的评分控制面

评分 setup 只恢复 `/testbed/r2e_tests`，**不恢复仓库自带的测试/helper 模块**。而 16/24 新题的隐藏测试 import 了这些模块 `[实测]`：`aiohttp.test_utils`、`tests.test_client_functional`、`tests.coveragetest`、`tests.helpers`、`datalad.tests.utils(_pytest)`、`datalad.interface.tests.test_docs`、`numpy.testing`、`numpy.ma.testutils`、`Orange.widgets.tests.{base,utils}`、`pandas.util.testing`、`scrapy.utils.{testproc,testsite}`。
agent 改写其中任何一个（例如把断言 helper 改成 no-op）都能直接影响隐藏测试结果，而现有 setup 不会覆盖回去。这是**本来源特有的奖励漏洞入口**（清单第 31 项），SWE-Gym 那边靠 `test_patch` 全量恢复挡住了，R2E 没有对应机制。

### 7.4 有效信号极窄，噪声面极宽

noop 与 expected 的差异键数分布 `[实测]`：**1 个键 33 题**、2 个 11 题、3 个 1 题、6 个 2 题、15 个 1 题。
也就是说 33/48 题的"是否修好"只由**一个**测试决定，而 reward 是整张映射（最大 323 键）的逐键与。任何一个无关用例抖动都把 1 变成 0。本轮没有做 flakiness 复测（旧 24 有 3 次一致的实测，新 24 只有 1 次，其中 2 题额外重复 2 次），稳定性记 `unknown`。

### 7.5 评分在哪个容器跑

Prime 在 **agent 自己的 runtime 里**评分（先捕获 patch，再把测试放回原 runtime 执行）`[代码]`。rh2 是冻结 delta + fresh grader。两者在"agent 是否动过 venv/`run_tests.sh`/仓库测试模块"上后果完全不同——**沿用 rh2 的 fresh grader**，不要为了对齐官方分数改成原地评分。另：Prime `_restore_tests` 是一次性消费（pop 后 finally 删本地归档），同一 runtime 第二次 `solved()` 会缺归档，重复 gold/noop 必须各自新建 runtime `[代码]`。

### 7.6 环境变好会改变键集，不只是改变状态

§5 的 SKIPPED 表和 §7.1 的 fixture ERROR 是同一个机制的两面：**期望映射是在上游那台机器的环境缺陷下拍的快照**。装上 scipy → pandas `19c5eea5` 多出 9 个键；补上 `conftest.py` → 58 个 ERROR 键变成别的状态；构建 C 扩展 → aiohttp `4075c653` 的 2 个 SKIPPED 变成实际结果、3 个 expected FAILED 也会翻。三种情况都让 reward 从 1 变 0。做环境筛查时**不要**把"修好环境"当成无条件的改进。

### 7.7 期望映射的生成条件未知

`expected_output_json` 是上游在**它们的**机器上跑出来的。我们没有它的 CPU/内存/网络/并发条件，也没有版本。48 题在 `--network none / 8g / 3cpu` 下 gold 46/48 得 1 `[实测]`，但这只说明"在这套条件下能复现"，不说明条件可变。

## 8. 接入 rh2 时每一项需要的实现点与验收样例

| # | 实现点 | 位置建议 | 验收样例（都可离线构造） |
| --- | --- | --- | --- |
| I1 | R2E ingest：把 `commit_hash/docker_image/problem_statement/expected_output_json/parsed_commit_content` 切成公开面与私有面 | `envpack/` 新增 `ingest_r2e_subset.py`，沿 `ingest_swegym_lite.py` 的形状 | 公开 bundle 里**不得**出现 `expected_output_json`、`parsed_commit_content`、`prompt`；用现有泄漏扫描（`split_frozen_entry`）做 fail-closed 断言 |
| I2 | `parse_log_pytest` 的 rh2 版本 | `envpack/r2e_parsers.py`（与 `swegym_parsers.py` 并列，**不复用**） | 三条固定样本：①正常 `-rA` 段；②**无** `short test summary info` 段（应得空映射，最终 reward 0 而不是抛异常）；③pillow 带 `\x1b[1m…\x1b[0m` 的期望键 |
| I3 | 键归一化口径（ANSI / `" - "`）**要先定版本** | 同 I2，写成显式 `normalization_version` 字段进报告 | pillow `4bc6483564ae…`：期望 24 键全部带 ANSI；按"对称去完整 ANSI"得 24 匹配，按 Prime 原版得 0 匹配。两个断言都写进测试，明确我们选哪个 |
| I4 | 入口执行：照原样跑 `/testbed/run_tests.sh`，只加超时与输出捕获 | `adapters/slime/` 的执行段 | 三种入口各一个样例：纯 pytest / xvfb-run / `unittest_custom_runner.py`（pillow `3ac9396e`） |
| I5 | `/r2e_tests` 搬离与恢复 | materialize 段搬离并留 digest；grader 段恢复 | 断言 agent 会话开始时 `/r2e_tests` 与 `/testbed/r2e_tests` 都不存在；恢复后目录 digest 与搬离时相等 |
| I6 | **不做** git 复位；候选 delta 走 baseline census | 已有 `baseline_census.py` + `patch_exporter.py`，确认排除区不含 `.venv`/`r2e_tests` 之外的东西即可 | 用 aiohttp `240da100` 的初态脏树做样例：census 后不改任何文件，导出的 delta 必须为空（现在的 `git diff HEAD` 会给出 3 个文件） |
| I7 | 仓库测试模块的恢复策略（§7.3） | 需要**先决定**，见 `L4_report.md` §4 | 反例：把 `datalad/tests/utils_pytest.py` 里某个断言改成 `pass`，再跑评分；当前实现下会得到 reward 1 |
| I8 | 评分报告字段 | 已有 `grading_outcome_fields_r2e`（工作区未提交） | `expected_match_count=total>0 → resolved`；观测多一个键 → union 变大 → `tests_failed`。两条已可直接单测 |
| I9 | 镜像泄漏清理（派生镜像或 git 清洗） | 需要**先决定**清洗到什么程度，见 `L4_report.md` §4 | 清洗后断言 `git cat-file -t <fix_commit>` 失败且 `git log --all` 里不含 HEAD 之后的提交 |

## 9. 代表对照（已有，可直接复用）

| 对照 | 题 | 结论 | 证据 |
| --- | --- | --- | --- |
| noop 必须真跑测试且得 0 | 48/48 | 全部 reward 0，且每题至少 1 个键与期望不同（不是空解析凑 0） | 账本 `reward_details.n_mismatch ≥ 1` |
| gold 得 1 | 46/48 | 旧 24 三次全 1；新 24 有 2 题 0 | `r2e_ledger_v3.jsonl`、`r2e_expansion_20260911_summary.json` |
| gold 复现失败 | coveragepy `016af5f6` | 期望 FAILED 实测 PASSED（环境更好反而扣分） | 同上 + `local_checks/r2e_coveragepy_016af5_diagnosis_20260911.md` |
| gold 复现失败 | datalad `58ba5165` | 隐藏测试 import 被 gold 排除的测试文件 | 同上 + `r2e_fixture_snapshots_20260911/58ba…/` |
| 无关补丁不得给分 | probe 有 `probe_unrelated` gate | **本轮 48 题没有跑过这个 gate** | `r2e_probe.py` 有实现，账本 gates 只有 noop/gold `[实测]` |
