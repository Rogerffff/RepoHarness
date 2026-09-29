# M3 报告：R2E 48 题镜像事实（机器 3 实测）

日期：2026-09-16 夜 · M3 · 全部在**机器 3**的一次性容器里采集，`envscreen-m3-*` 前缀、`--network none`、并发 3、用完即删、未 `docker commit`、未改 `rh2/src` 与 `rh2/tests`。
检查编号沿用 L4 的 [`machine_checks.md`](../L4_r2e/machine_checks.md)（M-01…M-13）。逐题记录见 `M3_r2e_check_records.json`。

## 0. 覆盖范围与成本

| 项 | 结果 |
| --- | --- |
| 采集镜像 | **48 / 48**（`r2e_images_48.txt` 全量，镜像合计 75.9 GB） |
| 采集轮次 | pass1 只读事实（M-01…M-08、M-10、M-13）→ pass2 候选身份执行探针 + M-07 修正 → pass3 包来源/rootdir → pass4 同容器连跑两次 `run_tests.sh`（M-11/M-12）→ pass5 git 清理实验（48 题）→ gold gate（48 题，用 `r2e_probe.py` 副本）→ pass6 清理后再跑 gold（48 题）→ pass7 泄漏路径核实（48 题） |
| `checks` 状态计数 | `pass` 314、`issue` 262、`not_checked` 48（全部是 M-09）、`unknown` 0 |
| 实跑成本 | noop 两次 629 s、gold 一次 621 s（中位 9.1 s/题）、清理实验与清理后 gold 各一轮；单次最慢 aiohttp `1c1c0ea3` 39 s |
| 未采 | **M-09（默认网络出网）**：本包机器纪律要求所有容器 `--network none`，未做；见 §6 |

产物：本目录 `M3_r2e_check_records.json` / `M3_key_collisions.json` / `M3_git_scrub_probe.json` / `M3_gold_after_scrub.json` / `M3_leak_path_probe.json`；
大文件在 `runs/env_overnight_20260916/M3/`（逐题 `facts/<commit12>/`、聚合 `r2e_image_facts.json`、重复实验 `noop_repeat.json`、gold 账本 `gold_ledger/`、采集脚本 `bin/`、批处理日志 `logs/`）。

## 1. 48 题事实表（按仓库聚合）

| 仓库 | 题 | Python | pytest | 入口 | 仓库 `addopts`（生效行） | 隐藏测试 import 仓库测试支撑模块 | 初态已跟踪改动 | 目标包必须 cwd=/testbed | venv 无 pip | 镜像 GB(中位) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aiohttp | 5 | 3.9.21×5 | 8.3.4×2/8.3.2/8.3.3/7.4.2 | pytest×5 | 空 | 4/5 | 5/5 | 5/5 | 2/5 | 1.4 |
| coveragepy | 5 | 3.7.9×5 | 4.6.6×4/6.2.5 | pytest×5 | `-q -n3 --strict --no-flaky-report -rfe --failed-first`（×4）；`-q -n3 --strict-markers --force-flaky --no-flaky-report -rfeX --failed-first`（×1） | 5/5 | 0/5 | 0/5 | 1/5 | 0.8 |
| datalad | 5 | 3.7.9×3/3.9.21×2 | 7.4.4×3/8.3.4×2 | pytest×5 | 空 | 5/5 | 0/5 | 0/5 | 5/5 | 1.8 |
| numpy | 7 | 3.7.9×6/3.10.16 | 7.4.4×6/8.3.4 | pytest×7 | `-l` | 7/7 | 0/7 | 7/7 | 7/7 | 1.4 |
| orange3 | 7 | 3.7.9×5/3.8.20×2 | 7.4.4×5/8.3.4×2 | pytest+xvfb×7 | 空 | 6/7 | 0/7 | 0/7 | 0/7 | 3.1 |
| pandas | 7 | 3.7.9×5/3.8.20×2 | 7.4.4×5/8.3.4×2 | pytest×7 | 空 | 7/7 | 7/7 | 0/7 | 0/7 | 1.6 |
| pillow | 7 | 3.9.21×7 | 8.3.4×7 | pytest×6/custom | `-ra --color=yes` | 0/7 | 0/7 | 0/7 | 7/7 | 1.2 |
| scrapy | 5 | 3.9.21×5 | 8.3.4×5 | pytest×5 | `--doctest-modules --assert=plain` | 1/5 | 0/5 | 0/5 | 5/5 | 1.0 |

全 48 题一致的事实：镜像 `Config.User=""`（默认 root）、`WorkingDir=/testbed`、无 ENTRYPOINT、`CMD=["/bin/bash"]`；OS 全部 Ubuntu 22.04.5；
`/testbed` 与 `/r2e_tests` 均 `root:root 755`，`run_tests.sh` `root:root 664`；`/testbed` 文件数中位 5,498、最大 40,680（numpy）；
`/testbed/.git` 21 MB–369 MB；`/r2e_tests` 之外**没有**任何 expected/gold 材料（`find / -xdev` 命中仅 `/r2e_tests` 本身）。
逐题证据：`runs/env_overnight_20260916/M3/facts/<commit12>/facts/{stat.txt,run_tests_meta.txt,find_expected.txt,testbed_count.txt}`。

### 入口与 `/r2e_tests` 形态（M-01 / M-02）

- `run_tests.sh` 只有 **3 种原文**：40 题 `PYTHONWARNINGS=… .venv/bin/python -W ignore -m pytest -rA r2e_tests`、7 题 orange3 在前面加 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`、1 题 pillow `3ac9396e` 是 `.venv/bin/python -W ignore r2e_tests/unittest_custom_runner.py`。每题 sha256 在 `M3_r2e_check_records.json` 的 M-02。
- `/r2e_tests` 文件组合：`__init__.py+test_1.py` 23 题、`+conftest.py` 7 题、`+helper.py` 6 题、只有 `test_1.py` 5 题、双测试模块 **7 题**（L4 静态只识别出新 24 里的 4 题，旧 24 另有 scrapy `cfed9b66`、numpy `d89bc4bb`、pandas `f656217a`）。
- `xvfb-run` / `Xvfb` 只装在 orange3 的 7 个镜像里，与 `run_tests.sh` 的用法一一对应（M-13 全 48 题 `pass`）。

## 2. 最重要的发现（七条）

### 2.1（新）候选身份 uid 54322 **完全跑不动**这批镜像 —— 48/48

实测（`asuser_exec.txt` / `interp.txt`）：

- `/testbed/.venv/bin/python` 是符号链接，真实解释器在 **`/root/.local/share/uv/python/cpython-<ver>/bin/python*`**，而 `/root` 是 `drwx------`（mode 700）。以 uid 54322 执行 → `/testbed/.venv/bin/python: Permission denied`。
- `sys.path` 里有 3 条目录在 `/root/...` 下（`python3x.zip`、`lib/python3.x`、`lib-dynload`）——**只 chown `/testbed` 解决不了**，标准库也在 `/root` 里。
- `/testbed`、`/r2e_tests`、`.venv/bin` 对 uid 54322 全部不可写（`touch` 实测 DENIED）；`run_tests.sh` 可读不可写。
- 以 uid 54322 在 `/testbed` 跑 `git` 直接 `fatal: detected dubious ownership`。

也就是说：方案 A 如果打算用非 root 身份跑 agent，这 48 个镜像**一个都不能直接用**。
**→ 第二片 §8 已把修法实测完**：搬迁解释器到 `/opt` + `chown -R /testbed` + `git safe.directory` 这一套（§8 的布置 b）在**全部 48 题 × noop/gold 共 96 次实跑**里让 uid 54322 的结果与 root 基线逐键相同，**但挡不住候选替换评分面**（§8.4）。下面这段里"chown 量级在秒级"的估计**被实测推翻**：因为 overlay2 的 copy-up，`chown -R /testbed` 实测要 11–149 s 并让容器可写层涨 0.35–2 GB，只能在派生镜像 build 时付一次。

### 2.2（量化 + 修正）修复提交是 HEAD 的**直接子提交**，一条不需要哈希、不需要网络的命令就能列出来 —— 48/48

三层实测：

1. **48/48 题的 `git branch -a --contains <fix>` 命中本地分支**（`master` 22 题、`main` 21 题、`maint` 5 题），48/48 也都有含该提交的 tag，`remote.origin.url` 完好。
2. **48/48 题 HEAD 是游离（detached）状态，且修复提交就是 HEAD 的直接子提交。** 用 `git rev-list --children --all | grep ^$(git rev-parse HEAD)` —— **一条命令、不需要预先知道修复提交的哈希、不需要网络** —— 列出 HEAD 的全部子提交：子提交个数 1 个 26 题、2 个 9 题、3 个 6 题、4 个 3 题、5 个 3 题、6 个 1 题；**修复提交在这张列表里排第 1 的 35 题、第 2 的 6 题、第 3 的 5 题、第 4 的 2 题——48/48 都在前 4 个之内**。`git show` 其中之一就是完整答案补丁。
3. `git rev-list --count HEAD..<fix>` 是 1（36 题）/2（7）/3（2）/4（3）——大于 1 只是因为修复提交是合并提交、带进了第二父链上的提交，不影响第 2 点。

**这比 L4 记的 `fix_reachable=commit`（"对象还在，但要知道哈希才取得到"）严重一档**：泄漏不依赖哈希、不依赖分支名、不依赖网络。
**同时修正一个直觉误判**：因为 HEAD 是游离的、`master` 的顶端在修复提交之后还有几千个提交，`git log master -1` 给的是 master 的最新提交而**不是**修复提交（实测 aiohttp `1c1c0ea3`：`git rev-list HEAD..master` 有 3,284 个提交）。真正短的路径是上面第 2 点。证据 `M3_leak_path_probe.json` 与 `runs/.../M3/facts/<commit12>/leak_path/children.txt`。

### 2.3（新，可执行）git 清理方案实测可行：修复提交被彻底删除，噪声评分逐键不变 —— **48/48**

pass5 在一次性容器里对**全部 48 题**做同一套清理：分离 HEAD → 删全部 ref/tag → 删 remote → `reflog expire --expire=now --all` → 删 `packed-refs` → `git gc --prune=now`；清理前后各跑一次 `run_tests.sh`（noop），用 `r2e_probe` 同规则解析后逐键比对。

| 仓库 | 题 | refs 合计 | tags 合计 | 清理后修复提交**取不到** | `.git` 合计 | 清理后 noop 键集与状态不变 |
| --- | --- | --- | --- | --- | --- | --- |
| aiohttp | 5 | 1635→0 | 1445→0 | 5/5 | 0.16→0.07 GB | **5/5** |
| coveragepy | 5 | 855→0 | 750→0 | 5/5 | 0.10→0.07 GB | **5/5** |
| datalad | 5 | 1320→0 | 1230→0 | 5/5 | 0.22→0.09 GB | **5/5** |
| numpy | 7 | 1995→0 | 1764→0 | 7/7 | 1.09→0.39 GB | **7/7** |
| orange3 | 7 | 581→0 | 539→0 | 7/7 | 0.71→0.62 GB | **7/7** |
| pandas | 7 | 1386→0 | 1239→0 | 7/7 | 2.52→1.41 GB | **7/7** |
| pillow | 7 | 1001→0 | 644→0 | 7/7 | 1.40→0.48 GB | **7/7** |
| scrapy | 5 | 800→0 | 595→0 | 5/5 | 0.14→0.09 GB | **5/5** |
| **合计** | **48** | **9,004→0** | **7,893→0** | **48/48** | **6.3→3.2 GB（省 49%）** | **48/48** |

结果：**48/48 题清理后 `git cat-file -t <fix>` 报 `could not get object info`（对象已被 gc 掉）、`git branch --contains` 命中 0、reflog 0 行**；同时 **48/48 题的 noop 解析键集与每个键的状态与清理前逐键相同**，没有一题出现状态翻转或键集差异，scrub 步骤本身也没有任何 `fatal`/`error`。
HEAD 之前的历史完整保留（`git log --all` 仍有数千行），依赖历史的构建不受影响。48/48 清理后 `git describe --tags` 变成 `fatal: No names found`，**但 pandas 7 题（versioneer）的 noop 评分照样逐键不变**——L4 Q3 里"删 tag 会打坏 versioneer 类构建"的担心在这批镜像上没有出现（原因：包在造镜像时已装好，`pandas/_version.py` 在初态就是改过的固定值，测试不断言版本号）。
**gold gate 也验了**（pass6，48/48）：在清理后的容器里用 `r2e_probe` 同一条 `git apply --whitespace=fix` 打 gold 补丁 —— **48/48 `apply_rc=0`**，随后按来源入口评分得到的 reward 与**未清理**镜像上的 gold reward **48/48 完全一致**（46 个 1、2 个 0，那 2 个就是 §2.7 里来源自身的缺陷题）。也就是说清理不影响打补丁、不影响判分。
**范围限制**：`probe_unrelated` gate 仍未跑，记 `not_checked`。证据 `M3_git_scrub_probe.json`、`M3_gold_after_scrub.json` 与 `runs/.../M3/facts/<commit12>/{git_scrub,gold_after_scrub}/`。

### 2.4（新）入口不能归一化：1 题非 pytest + 12 题必须 `cwd=/testbed`

- pillow `3ac9396e`：`/r2e_tests/test_1.py` 与 `test_2.py` 用**绝对** import `from helper import …`。用统一的 `pytest r2e_tests` 入口跑，实测 `collect_rc=2`、2 个模块全部 `ModuleNotFoundError: No module named 'helper'`、**收集 0 个用例**（`facts/3ac9396e8c99/collect.txt`）。另外 6 题 pillow 用的是相对 import `from .helper import …`，在 pytest 下正常。所以这 1 题只能沿用它自己的 `unittest_custom_runner.py`。
- **12 题（aiohttp 5 + numpy 7）的目标包根本没装进 venv**：`cd /testbed` 时 `import numpy` → `/testbed/numpy/__init__.py`；`cd /tmp` 时直接 `ModuleNotFoundError`。site-packages 里没有任何同名副本（48/48 都没有）。这些题只靠 "pytest 把 rootdir/cwd 放进 `sys.path[0]`" 才导入到候选代码。**评分执行必须 `cwd=/testbed` 且用相对路径 `r2e_tests`**；换 cwd 或改用绝对路径 → 全部用例 ERROR → reward 恒 0，而且是静默失败。证据 `facts/<c>/pkgsrc.txt`。

### 2.5（补齐旧 24）隐藏测试 import 仓库自带测试支撑模块：35/48

L4 只能在新 24 上查这一项（16/24）。48 题实测（`import_origins2.json`，在容器里用 venv 解释器 `find_spec` 解析到真实路径）：**35/48** 命中，按仓库 numpy 7/7、pandas 7/7、orange3 6/7、coveragepy 5/5、datalad 5/5、aiohttp 4/5、scrapy 1/5、pillow 0/7。
典型模块：`numpy.testing` / `numpy.ma.testutils`、`pandas._testing`、`tests.coveragetest` / `tests.helpers` / `tests.goldtest`、`datalad.tests.utils(_pytest)`、`Orange.widgets.tests.base` / `Orange.widgets.tests.utils`。
其中 3 题直接 import 了仓库里的**测试用例模块**本身：aiohttp `240da100` → `tests.test_client_functional`、datalad `58ba5165` → `datalad.interface.tests.test_docs`、pandas `f656217a` → `pandas.tests.reshape.merge.test_merge`。
这些文件现在是 `root:root 644`，在当前权限下候选写不了（见 2.1）；**一旦按 2.1 的方案 (b) 把 `/testbed` 交给候选用户，它们立刻变成可写的评分控制面**，而评分 setup 只恢复 `/testbed/r2e_tests`。

### 2.6（新）27/48 的 venv 里**没有 pip**

`/testbed/.venv/bin/python -m pip freeze` 在 27 题返回 `No module named pip`：numpy 7/7、pillow 7/7、datalad 5/5、scrapy 5/5、aiohttp 2/5、coveragepy 1/5。两个后果：

- **候选装不了包**——这是一条实打实的环境约束，应该写进任务卡，而不是等 agent 在轨迹里撞上。
- **依赖快照取不到**：这 27 题的 `pip freeze` / `pip list` 证据为空，`venv.plugins` 字段不可信。本报告里凡是涉及插件的判定都改用**运行输出 + `addopts` 原文**作直接证据（例如 coveragepy `ea6906b0` 的 `pip list` 是空的，但 noop 输出里有两行 `bringing up nodes...`，`setup.cfg` 里有 `-n3 … --force-flaky`，所以 xdist 与 flaky 都确实装着且生效）。逐题 `pip_available` 字段见 `M3_r2e_check_records.json` 的 M-04。

### 2.7（复核 L4 的 T1）gold gate 在机器 3 上 46/48 拿到 reward=1，失败的 2 题与 L4 静态结论逐题吻合

用 `r2e_probe.py` 的副本（只改容器名前缀以满足本包纪律，解析与判分逻辑逐字不动，`runner_version` 仍是 `r2e_probe/0.3`；diff 见 `runs/.../M3/bin/r2e_probe_m3.py`）对 48 题各跑一次 gold gate，`--network none`：

- **46/48 reward=1**（`result=passed`），`n_missing = n_extra = 0`，48/48 `patch_apply=git_apply` 成功。
- **2 题 reward=0，正是 L4 的 T1 前两题**，且判别键逐字相同：coveragepy `016af5f6` 的 `MockingProtectionTest.test_os_path_exists`（期望 `FAILED`，机器 3 实测 `PASSED`）；datalad `58ba5165` 的 `test_alter_interface_docs_for_cmdline`（期望 `PASSED`，实测 `FAILED`，即隐藏测试 import 了被 gold 排除的文件）。两题都在**不同机器上复现**，说明是来源数据本身的缺陷，不是本机环境偶发。
- **L4 的 T1 第三题 pillow `3ac9396e`（非 pytest 入口）在这里 reward=1**。原因是 `r2e_probe` 逐字执行 `run_tests.sh`，自定义 runner 正常工作。所以它不是"来源给不出正确信号"，而是"**入口不能被归一化**"——归到本报告的 R2，判定口径要改。
- **pillow 6 个期望键带 ANSI 的题全部 reward=1**，说明 `r2e_probe/0.3` 的对称去色修法在机器 3 上同样成立（对应 L4 的 Q2；这仍是与 Prime 原版的口径分歧，需要显式定版本，不是本包能决定的）。

账本 `runs/.../M3/gold_ledger/r2e_gold_m3.jsonl`（48 行），逐题日志 `gold_ledger/logs_r2e/<repo>/<commit12>/gold/a1/{gold.diff,test_output.txt,status_map.json}`。

## 3. 按风险分层

分层只用**机器 3 的实测事实**，与 L4 的 T1–T4（静态 + 历史账本）是两套坐标，不要混读。

### R1 全局（48/48，不分层）

1. 候选身份 uid 54322 不可执行解释器 / 不可写 `/testbed` / git 不可用（§2.1）。
2. 修复提交在本地分支与 tag 上一步可得（§2.2）。
3. 镜像初态**不是干净树**：48/48 至少有 `install.sh` + `run_tests.sh` 两个未跟踪文件；一次评分运行后又新增 `r2e_tests/*`（48/48）与 `/testbed/.pytest_cache`（47/48，pillow 自定义 runner 那题不生成）。`.pytest_cache` 被仓库 `.gitignore` 挡住，**`git status` 看不见但文件系统基线看得见**。

### R2 逐题阻断（13 题，入口不能归一化）

| 子类 | 题数 | 题 |
| --- | --- | --- |
| 入口非 pytest | 1 | pillow `3ac9396e` |
| 目标包未安装、必须 `cwd=/testbed` | 12 | aiohttp 全 5 题、numpy 全 7 题 |

### R3 评分控制面可操纵（35 题）

隐藏测试 import 仓库自带测试支撑模块（§2.5）。severity P1，逐题模块名在 `M3_r2e_check_records.json` 的 M-07。

### R4 需记录、当前不直接改判分（17 题，与 R2/R3 有重叠）

| 子类 | 题数 | 题 |
| --- | --- | --- |
| 镜像自带未提交的**已跟踪**改动 | 12 | pandas 全 7 题（`M pandas/__init__.py`、`M pandas/_version.py`、**`D pyproject.toml`**、`M setup.cfg`、`M versioneer.py`，diff 94–135 KB）；aiohttp 全 5 题（3 题 `M Makefile`；`240da100` 改 `client.py/server.py/worker.py`；`61833518` 再加 `client_reqrep.py`） |
| 顺序/重试相关插件且 `addopts` 真的用了 | **5**（coveragepy 全部） | `016af5f6` `5dbbe143` `97997d2c` `f5eb5f21` `ea6906b0`：`setup.cfg` 的 `addopts` 都含 `-n3 … --no-flaky-report --failed-first`，即**默认 3 进程并行 + flaky 重试 + 读写 `.pytest_cache` 决定运行顺序**。判定依据是 noop 输出里的 xdist banner（`bringing up nodes…`，5/5 出现）加 `addopts`，不是 `pip list`——见 §2.6 |

另外 aiohttp 5 题镜像里带着未跟踪的 `process_aiohttp_updateasyncio.py`（R2E 的 py2→py3 改写脚本），orange3 7 题带未跟踪的 `datasets/`。

### R5 本轮机器证据未发现额外问题（11 题）

pillow 6、scrapy 4、orange3 1（`9b5494e2`）。**只表示"机器侧这一轮没发现"**，不能读成 pass：它们仍受 R1 三条全局问题约束，且 L4 的静态风险（期望键带 ANSI、非 PASSED 期望键等）照旧成立。

## 4. 接入 rh2（方案 A）前必须先处理的环境问题

按"不处理就一定出错"排序。前三条是**实现/派生镜像层面**，第四条起需要用户拍板。

1. **执行身份与解释器位置**（48/48，§2.1）。不处理的后果不是分数偏差，而是**任何非 root 身份都起不来**。**第二片 §8 已实测并给出定案**：派生镜像里做「把 uv 的 Python 从 `/root/.local/share/uv` 复制到 `/opt/py` 并改写 `pyvenv.cfg`/符号链接/shebang（中位 3.6 s）+ `chown -R <uid>:<gid> /testbed /r2e_tests`（中位 23 s、最长 157 s，overlay2 copy-up，必须 build 时做）+ `git config --system --add safe.directory '*'` + 建候选用户与 `$HOME`」，**全部 48 题 × noop/gold 共 96 次实跑，reward 与 root 基线逐键相同**。**不要用 `chmod o+rx /root` 那条捷径**：判分结果一样，但会把整个 `/root`（292 MB，含 `.cache`/`.config`/`.local`）暴露给候选。
2. **执行上下文必须 `cwd=/testbed` + 相对路径 `r2e_tests`**（12 题静默归零，§2.4）。建议 rh2 侧加断言：执行前检查 `cwd` 与目标包 `__file__` 落在 `/testbed` 下，不满足直接报错而不是给 0 分。
3. **逐题沿用 `run_tests.sh` 原文，不做入口归一化**（§2.4），并在评分前校验其 sha256（每题值已采，M-02）。**第二片 §8.4 把 L4 Q4 的答案实测出来了**：一旦按第 1 条 `chown /testbed`，候选即使不能改 `run_tests.sh` 的内容，也能 `unlink` 后换成自己的脚本（实测放入 `echo FAKE_ALL_PASS` 成功），把文件属主改回 root **无效**。所以 grader 必须**用自己保存的原文执行**，不要读 `/testbed/run_tests.sh`；同理隐藏测试必须由 grader 在候选回合结束后从 `/r2e_tests`（在 `/` 下，候选动不了）重新拷入。
4. **泄漏清理**（L4 Q3，§2.2 / §2.3）。本包给出的最小方案已在**全部 48 题**上实测：修复提交对象被彻底删除，noop 评分逐键不变，`.git` 总量从 6.3 GB 降到 3.2 GB。建议：派生镜像统一做这一步；落定前补跑 gold gate 与 `probe_unrelated` 各一轮。**清理落地前 R2E 不适合作为训练来源**（沿用 2026-09-15 决策包 §5）。
5. **候选 delta 的排除清单**：`r2e_tests/`（48/48 由评分 setup 拷入）与 `.pytest_cache/`（47/48 由运行生成、被 `.gitignore` 挡住）。与第四组 §0/§6.5"额外排除默认为空"的决定不冲突——那条讲的是**测试名通配**，这里是**候选文件 delta 的运行期产物**，属于两件事，但**需要单独立项**而不是默认生效。
6. **仓库自带测试支撑模块的恢复策略**（L4 Q5，§2.5）。35 题的 import 闭包已备齐（M-07），可以直接按闭包做"评分前恢复到 base 版本"。这一项只有在第 1 条放开 `/testbed` 权限之后才成为真实漏洞，两件事要一起决定。
7. **coveragepy 5 题的执行确定性**：`-n3` 并行 + `flaky` 重试 + `--failed-first` 读写 `.pytest_cache`。建议每次评分从干净容器起（rh2 现在就是这样），并把 `xdist` worker 数与插件版本写进 reward 元数据；若要在同容器复跑，必须显式 `-p no:cacheprovider`。

## 5. 与 L4 静态结论的核对

**确认**：`head_is_parent_of_fix` 48/48（`HEAD_IS_ANCESTOR_OF_FIX=yes`，距离 1–4 个提交）；`fix_reachable=commit` 48/48；`/r2e_tests` 之外无 expected 材料 48/48；`Config.User=""` 48/48；镜像自带脏树在新 24 的 aiohttp 3 题 / pandas 3 题——**旧 24 补齐后是 aiohttp 5/5、pandas 7/7 全部有已跟踪改动**。

**补齐（L4 记 unknown 的三类）**：

| L4 的 unknown | M3 结果 |
| --- | --- |
| 旧 24 的 `hidden_test_files` / `hidden_test_repo_imports` | 已采全 48 题 `/r2e_tests` 原文与 import 闭包；旧 24 另发现 3 个双测试模块题 |
| 48 题 `initial_dirty_tracked_files` | 已采全，逐文件清单见 M-06；只有 aiohttp 5 + pandas 7 有已跟踪改动 |
| 48 题 `key_collision_after_prime_normalize` | **48/48 无碰撞**。判据是**来源入口实跑的 `short test summary info` 行**：48/48 题「摘要行数 == Prime 折键数」且无跨文件同名。用实跑而不是 `--collect-only`，一是更贴近判分路径，二是本轮 `--collect-only` 沿用了仓库 `addopts`，多数题没有 `-q`，输出的是收集树而非 node id，coveragepy 的 `-n3` 与 pillow 自定义 runner 更是完全拿不到 node id。`M3_key_collisions.json` |

**新增量化**：

- **重复一致性**（L4 记 `unknown`）：48/48 题在**同一容器内连跑两次** `run_tests.sh`，解析键集与每个键的状态**完全一致**，无状态翻转、无键集差异——包括 5 个 `-n3 + flaky + --failed-first` 的 coveragepy 题。`noop_repeat.json`。**范围限制**：只覆盖"同容器、连续两次、noop gate"，跨容器/跨机器/gold gate 的抖动仍是 `unknown`。
- **跨机器可复现性**：机器 3 的 noop 解析结果对 48/48 题都满足 `parsed_n == expected_n`、`n_missing = n_extra = 0`、`noop reward = 0`（正确，噪声不该得分）。被 parser 丢弃的 SKIPPED/XFAIL 合计 **36 + 2 = 38 个用例、14 题**，与本机记录的 38 逐题**完全一致**（本机那 38 来自 gold 日志，机器 3 这 38 来自 noop —— 说明跳过条件由环境决定，与补丁无关）。
- **gold 可复现性**：机器 3 独立跑 gold gate，46/48 reward=1；2 个 0 与 L4 的 T1 前两题逐键吻合（§2.7）。L4 的 T1 第三题在忠实执行 `run_tests.sh` 时 reward=1，应从"来源信号缺陷"改判为"入口不可归一化"。
- **判别信号宽度**：noop 与期望不同的键数分布 —— 1 个键 **34 题**、2 个 10 题、3 个 1 题、6 个 2 题、15 个 1 题（期望键总数 2,650）。没有任何一题 noop 与期望完全相同，即 48 题都至少能判别出 noop。这把 L4 §3.4 的观察扩到了全 48 题。

## 6. 未完成与 `not_checked`

- **M-09（默认网络下的出网能力）48 题全部 `not_checked`**：本包机器纪律要求全部容器 `--network none`，未做例外。影响有限——§2.2 已证明**离线**就能从本地分支拿到修复提交，出网只是多一条同类通道。
- ~~`probe_unrelated` gate 一次都没跑~~ → **第二片 §10 已跑 10 题，10/10 判 0**；余下 38 题与更强的对抗型无关补丁仍 `not_checked`。
- ~~gold 只跑了 1 次/题~~ → **第二片 §9 已跑第二次，48/48 逐键一致**；跨机器一致性仍 `unknown`。
- **跨容器 / 跨机器重复一致性**、合法替代解与错误解的双向验证：`not_checked`。
- ~~第 2.1 条给出的权限修法没有实做过~~ → **第二片 §8 在一次性容器里实测了三种布置**；但仍**没有真的构建派生镜像**（没有 `docker build`、没有 `docker commit`），"build 时付一次 chown"的成本与镜像体积增量是推算，不是实测。
- §8 的布置 **b 已覆盖全部 48 题**；布置 a 与 c、以及替换攻击验证只做了 5 / 2 个代表镜像，其余题 `not_checked`。
- **27 题的依赖快照缺失**（venv 无 pip，§2.6）：这些题的 `pip freeze` 记 `unknown`，若配方需要逐题依赖清单，要换成 `importlib.metadata` 扫描或从镜像层反推。

## 7. 机器残留检查

- 采集结束后 `docker ps -a` 只有表头：**容器 0 个残留**。两个口径都查过：按名字 `--filter name=envscreen-m3` 为 0；按 `r2e_probe` 自带的 `--filter label=rh2probe=1` 也为 0。所有容器在各 pass 结束时 `docker rm -f`。
- 未执行任何 `docker commit`；未推送任何镜像。`docker images` 48 个、**非 `namanjain12/` 前缀的 0 个**，即没有本包创建的镜像；48 个拉取的镜像保留在机器 3 上（合计 75.9 GB，磁盘 776 G 用 11%），未清理——如需回收由协调者决定。
- 机器上的工作目录：`/work/envscreen/M3/{bin,facts,gold_ledger,probe_data,L4,inputs,images.txt,*.log}`；`facts/`、`gold_ledger/`、`bin/` 已全量 rsync 到本机 `runs/env_overnight_20260916/M3/`（48 MB），批处理日志在 `runs/.../M3/logs/`。
- 未改动 `rh2/src`、`rh2/tests`、`rh2/experiments`（`git diff rh2/experiments/env_probe_20260909/r2e_probe.py` 为空；用的是 `runs/.../M3/bin/r2e_probe_m3.py` 副本）；本机写入只落在本包目录与 `runs/env_overnight_20260916/M3/`。
- 本报告与所有文件未写入任何主机地址、端口或密钥。

---

# 第二片（2026-09-16 凌晨，同一台机器 3）

规则同第一片：`envscreen-m3-*` 前缀、`--network none`、用完即删、**绝不 `docker commit`**（下面所有"布置"都只发生在一次性容器里，原镜像不变）。

## 8. 候选身份修法实测（对应第一片 §2.1）

### 8.1 三种布置与实验协议

第一片证明 48/48 镜像里 uid 54322 既不能执行 `/testbed/.venv/bin/python`（真实解释器在 `/root`，mode 700），也不能写 `/testbed`。本轮在**一次性容器内以 root** 施加三种布置再实测：

| 布置 | 内容 |
| --- | --- |
| **a 就地放权** | `chmod o+rx /root`（打开解释器链路）+ `chown -R 54322:54322 /testbed /r2e_tests` + `git config --system --add safe.directory '*'` |
| **b 搬迁** | 把 `/root/.local/share/uv/python/<cpython-…>` 整个 `cp -a` 到 `/opt/py/`，改写 `.venv/pyvenv.cfg` 的 `home=`、重指 `.venv/bin/python*` 符号链接、修 `/testbed/.venv/bin` 里指向 `/root` 的 shebang；**`/root` 保持 700 不动**；其余同 a |
| **c = b + 评分面收回 root** | 在 b 之上把 `/testbed/run_tests.sh`、`/r2e_tests`、`/testbed/r2e_tests` 的属主改回 `root:root` 并去掉 group/other 写位 |

三种布置都额外 `useradd -u 54322 -g 54322 -d /home/agent` 并建好 `$HOME`（orange3 的 `xvfb-run --auto-servernum` 需要可写 HOME）。

**覆盖**：a 与 c 各做 5 个代表镜像 × noop/gold（各 10 次实跑）；**推荐的 b 做了全部 48 题 × noop/gold，共 96 次实跑**。5 个代表镜像覆盖第一片识别出的各类难点：aiohttp `1c1c0ea35304`（包未安装、必须 cwd=/testbed）、numpy `18b7cd9df7a4`（同上 + venv 无 pip）、pillow `3ac9396e8c99`（**非 pytest 入口**，自定义 runner）、pandas `19c5eea5db00`（初态脏树 + versioneer + 期望里有 ERROR 键）、orange3 `22e98f8f4ccc`（**xvfb-run 图形入口**）。

每个 `(镜像, 布置, gate)` 一个新容器，顺序：**布置 → [gold] `git apply` 补丁 → 评分 setup（拷 `/r2e_tests`）→ 以 uid 54322 跑一次 `run_tests.sh` → 同容器再以 root 跑一次 → 最后才做可写面探测**。最后一步的顺序很重要：探测会 `touch` 文件，放在实跑之前会污染评分（本轮第一次跑就因为探测脚本给 `run_tests.sh` 追加了一行、而该文件没有结尾换行，导致入口参数变成 `r2e_tests#x`、收集 0 个用例——这次失败本身也是"`run_tests.sh` 可被改坏"的旁证）。

### 8.2 结论一：三种布置都**不改变判分**（a/c 各 10 次，b 全部 48 题共 96 次）

| 观测 | a（5 题×2） | **b（48 题×2）** | c（5 题×2） |
| --- | --- | --- | --- |
| uid 54322 能执行 `.venv/bin/python` | 10/10 | **96/96** | 10/10 |
| uid 54322 解析键集与状态 == 未做布置的 root 基线 | **10/10** | **96/96** | **10/10** |
| 同容器内 uid 54322 结果 == root 结果 | 10/10 | **96/96** | 10/10 |
| gold reward | 5×1 | **46×1 + 2×0** | 5×1 |
| noop reward | 5×0 | **48×0** | 5×0 |
| `git status` 在 /testbed 可用（safe.directory） | 10/10 | **96/96** | 10/10 |
| `sys.path` 里还剩 `/root` 路径 | **3 条** | **0 条** | 0 条 |
| 候选能否列出 `/root` | **能** | 不能 | 不能 |

基线取第一片的 root 结果（noop 取 `facts/<c12>/noop_x2/out1.txt`，gold 取 `gold_ledger/logs_r2e/<repo>/<c12>/gold/a1/status_map.json`）。
b 的 2 个 gold reward=0 正是 coveragepy `016af5f6` 与 datalad `58ba5165` —— 与未做任何布置的 root 基线**完全一致**，是来源数据自身的缺陷（第一片 §2.7），不是布置引起的。
**pillow 的自定义 runner 与 orange3 的 `xvfb-run` 在 uid 54322 下都正常工作**（orange3 gold `rc=0`、10 s；pillow gold `rc=0`），这是接入前最担心的两个点。
pandas `19c5eea5db00` 的 gold `rc=1` 但 reward=1 —— 因为它的期望映射里本来就有 ERROR/FAILED 键（第一片 §2.7 / L4 §3.1），不是布置引起的。

### 8.3 结论二：**a 与 b 判分一样，但 b 不暴露 `/root`；成本几乎全在 `chown`，不在搬迁**

**48 题上布置 b 的实测成本**（每题一次，`facts/<c12>/uidfix/b_noop/arrange.txt`）：

| 步骤 | 范围 | 中位 | 48 题合计 |
| --- | --- | --- | --- |
| `chown -R` `/testbed`+`/r2e_tests` 的条目数 | 1,261 – 40,308 | 5,348 | — |
| `chown -R` 耗时 | **5.9 – 157.3 s** | **23.1 s** | 32.3 分钟 |
| 复制解释器到 `/opt` 耗时 | **1.2 – 6.2 s** | **3.6 s** | 3.0 分钟 |
| 布置总耗时 | 9.5 – 161.0 s | 28.3 s | 35.5 分钟 |
| 容器可写层体积 | 238 MB – 2.28 GB | 652 MB | 35.7 GB |

按仓库的 `chown` 条目中位：orange3 30,808（7 题，最慢 5 题全是它，114–157 s）、datalad 23,169（5 题）、aiohttp 9,253、pandas 6,547、pillow 5,272、coveragepy 3,801、scrapy 3,503、numpy 3,089。

两条要点：

1. **成本几乎全部来自 `chown -R /testbed`，不是来自搬迁解释器**（32.3 分钟 vs 3.0 分钟）。原因是 overlay2：`chown` 改每个 inode 的元数据，会把整棵树从只读层 **copy-up** 到容器可写层——所以容器可写层同时涨到中位 652 MB、最大 2.28 GB，48 题合计 35.7 GB。**这笔钱只能在派生镜像 build 时付一次**（`RUN chown -R` 会成为一个共享的镜像层）；放在每个 episode 开头做，就是每题 6–157 s + 每容器 0.24–2.28 GB 磁盘。
2. **a 把 `/root` 从 700 改成 705**：实测 uid 54322 之后可以 `ls -a /root`、可以遍历进 `/root/.cache`、`/root/.config`、`/root/.local`（这批镜像里 292 MB）。这批 R2E 镜像里没有凭据，但"给候选打开 `/root`"是个不该默认开的口子。**b 在 48 题上拿到与 root 基线完全相同的判分，却让 `/root` 保持 700、`sys.path` 里一条 `/root` 都不剩**，额外代价只有 1.2–6.2 s 和约 3.6k–5.7k 个文件。

→ **b（搬迁）应作为 R2E 适配器的默认布置**，且必须在派生镜像 build 时完成；a 只在"不允许改动镜像内容、只能改权限位"的场景下退而求其次。

### 8.4 结论三：**三种布置都挡不住候选替换评分面——因为 `/testbed` 目录本身可写**

`chown -R 54322 /testbed` 是候选能改仓库源码的前提，但它同时让候选拿到了 `/testbed` 的**目录写权限**。在一次性容器里以 uid 54322 实测（做完即还原）：

| 攻击动作 | a | c（`run_tests.sh` 与 `r2e_tests` 已改回 root:root 755） |
| --- | --- | --- |
| 直接改 `run_tests.sh` 内容（`>>`） | **OK** | DENIED |
| `rm` 掉 `run_tests.sh` 再写一个新的 | **OK** | **OK** ← 只需要 `/testbed` 目录可写 |
| 把 `/testbed/r2e_tests` 整个 `mv` 走、换成伪造的 `test_1.py` | **OK** | **OK** |
| `rm -rf /testbed/r2e_tests` | OK | DENIED |
| 替换 `.venv/bin/python` shim（目录可写） | **OK** | **OK** |
| 动 `/r2e_tests`（在 `/` 下） | DENIED | DENIED |

也就是说 **c 的"把评分文件改回 root 所有"是无效防护**：候选 `mv` 掉整个 `r2e_tests` 目录、`unlink` 掉 `run_tests.sh` 再放自己的版本，都只需要父目录可写。实测已把伪造的 `run_tests.sh`（内容 `echo FAKE_ALL_PASS`）和伪造的 `r2e_tests/test_1.py` 成功放进去（随后还原）。

**给方案 A 的直接结论**：R2E 的评分面不能靠文件权限保护，只能靠**协议**——
(i) 候选回合结束后，grader 以 root 重新 `rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests`（`/r2e_tests` 在 `/` 下，候选动不了，这一条实测成立）；
(ii) grader **不要读 `/testbed/run_tests.sh`**，而是用自己保存的原文执行，并对镜像内原文做 sha256 校验（每题值第一片 M-02 已采）；
(iii) 评分执行仍必须 `cwd=/testbed` + 相对路径 `r2e_tests`（第一片 §2.4，12 题否则静默归零）。
剩下的 R3 面（35 题的隐藏测试 import 仓库自带测试支撑模块）不在本节能解决的范围内——那是候选"合法可改"的源码，只能按第一片 §4.6 的恢复策略处理。

产物：`M3_uid_fix_probe.json`（116 次实跑 = a 10 + b 96 + c 10，外加 4 次替换攻击实验的逐项记录；替换攻击是 2 个镜像 × 布置 a/c，每次 6 项动作）、原始观测 `runs/.../M3/facts/<commit12>/uidfix/{a,b,c}_{noop,gold}/` 与 `attack_{a,c}/`。

## 9. gold 重复稳定性：48/48 两次完全一致

第一片只跑过 1 次 gold，稳定性记 `unknown`。本轮对 48 题再跑一次（同一 `r2e_probe/0.3` 副本、同 `--network none`、每题各自一次性容器；第一次 3 workers、第二次 4 workers）：

- **48/48 两次的解析键集与每个键的状态完全相同**（`status_map.json` 逐键比对），`reward` 48/48 相同（46 个 1、2 个 0，仍是 coveragepy `016af5f6` 与 datalad `58ba5165`）。
- 被 parser 丢弃的行也完全一致：两次都是 **SKIPPED 36 个用例 + XFAIL 2 行**，逐题相同，没有任何一题出现漂移。
- `test_rc` 48/48 相同；`fixture_digest`（gold 补丁）与 `image_digest` 48/48 相同。
- `log_sha256` 48/48 **不同**——这只是日志里的耗时、session header、临时路径不同，不影响解析结果；**不能拿日志哈希当判分稳定性的指标**。
- 耗时总量 382 s → 398 s；单题相对差最大的是 pillow `3a61c9e9`（2.79 s → 11.48 s，+311%），属于并行度不同带来的调度噪声。

产物：`M3_gold_repeat.json`、账本 `runs/.../M3/gold_ledger/r2e_gold_m3.jsonl`（96 行 = a1 48 + a2 48）、逐题日志 `.../gold/a2/`。
**范围限制**：两次都在**同一台机器**上跑，跨机器一致性仍是 `unknown`；noop 的同容器两次一致性在第一片已验，跨容器 noop 未单独验。

## 10. `probe_unrelated` gate：10/10 判 0

第一片与 L4 都记这条"一次没跑过"。本轮取 10 题（每仓库至少 1 题：aiohttp 2、numpy 2、coveragepy/datalad/orange3/pandas/pillow/scrapy 各 1），用同一 probe 副本打 `r2e_probe.py` 自带的无关补丁（在仓库根新增一个 `RH2_PROBE_UNRELATED.md`）：

- **10/10 `patch_apply=git_apply` 成功、`reward=0`、`result=passed`**（此 gate 下 `passed` 的定义就是"没给分"）。没有一题被无关改动骗到分。
- 更强的一条：10/10 的 `n_missing = n_extra = 0`，且**判别键数与同题 noop 完全相同**（9 题各 1 个、coveragepy `016af5f6` 2 个）。说明无关补丁确实没有改变任何一个测试的结果，不是"碰巧也是 0"。

产物：`runs/.../M3/unrelated_ledger/r2e_unrelated_m3.jsonl`（10 行）与逐题日志。
**范围限制**：只跑了 10 题、只用了这一条"新增一个 Markdown 文件"的无关补丁；更强的对抗型无关补丁（比如改动无关源码、加 `conftest.py`）没试过。

## 11. 第二片的机器残留检查

- `docker ps -a` 为空：**容器 0 个残留**（两个口径：`--filter name=envscreen-m3` 为 0、`--filter label=rh2probe=1` 为 0）。
- **未执行任何 `docker commit`**；`docker images` 仍是 48 个、全部 `namanjain12/` 前缀，非该前缀 0 个——所有权限布置都只存在于已删除的一次性容器里。
- `docker images -f dangling=true` 为 0；机器上无残留后台进程（`uid_one` / `run_uid` / `r2e_probe` 全部为 0）；磁盘 776 G 用 11%。
- 第二片总实跑量：uid 布置 116 次（a 10 + b 96 + c 10）+ 替换攻击 4 次 + gold 第二轮 48 次 + `probe_unrelated` 10 次 = **178 个一次性容器**，全部 `--network none`、用完即删。
- 中途有一次批处理需要重跑：第一次 uid 批的探测脚本在实跑**之前**给 `run_tests.sh` 追加了一行（该文件没有结尾换行，于是入口参数变成 `r2e_tests#x`、收集 0 个用例），且清理时残留进程把在跑的容器删掉了。已把探测挪到实跑之后、改成非破坏性判定，杀干净残留进程并清空 `uidfix/` 后重跑，最终 30/30 与 96/96 完成。**被污染的那一批结果没有进入任何产物**（对应目录已删除后重建）。
