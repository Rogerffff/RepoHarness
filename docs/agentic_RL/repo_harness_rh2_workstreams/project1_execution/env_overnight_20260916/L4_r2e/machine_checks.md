# L4 · R2E 镜像待查清单（给机器包 M3）

日期：2026-09-16 夜。作者：L4（静态分析，未起容器、未连机器）。对象：`r2e_tasks_48.json` 里的 48 个镜像（`namanjain12/<repo>_final:<commit>`）。
本文只列**必须进容器才能得到**的事实；已经能从本地证据确定的，写在 `r2e_task_facts.json` / `L4_r2e_adapter_card.md`，不要重复采。

## 0. 先读这一节：哪些已经有答案，别再花机器时间

| 事实 | 已知结论 | 证据 |
| --- | --- | --- |
| HEAD = 修复提交父提交 | 48/48 `head_is_parent_of_fix=yes` | `r2e_ledger_v3.jsonl` + `runs/env_probe_stage1_20260910/ledger/*/results.jsonl` 的 `facts` |
| 修复提交对象在镜像 git 库里可达 | 48/48 `fix_reachable=commit` | 同上 |
| `/testbed/r2e_tests` 起始不存在 | 48/48 `r2e_tests_in_testbed=0` | 同上 |
| `/r2e_tests` 根条目数 | 48/48 已知（1~5） | 同上 |
| `expected_test_output.json` 不在 `/testbed` 与 `/` | 48/48 `expected_file=0` | 同上（只查了这两条路径，见 M-08） |
| `run_tests.sh` 原文 | **旧 24** 从账本 `run_tests_sh` 字段可得（20 条纯 pytest、4 条 xvfb-run）；**新 24** 已有镜像内快照原文 | `runs/env_probe_stage1_20260910/ledger/r2e_fixture_snapshots_20260911/<commit>/testbed/run_tests.sh` |
| `/r2e_tests` 文件内容 | **新 24 已有完整快照**（含 pillow `3ac9396e` 的 `unittest_custom_runner.py`）；**旧 24 没有** | 同上目录 |
| 容器 `Config.User` | 新 24 的 56 次运行都是空串（用镜像默认） | `.../observations/<name>/initial.json` |
| 镜像自带脏工作区（已跟踪文件被改） | 新 24 里 aiohttp 3 题、pandas 3 题的 noop `git diff HEAD` 非空 | `.../observations/<name>/pre_test.diff` |
| `egress_pypi=fail` | **不是**"镜像不能出网"的证据：所有已知运行都用 `--network none` | `initial.json` 的 `host_config.NetworkMode=none`（56/56） |
| 双测试文件的跨文件同名塌陷 | **新 24 的 4 个双文件题已做 AST 级检查，全部无跨文件同名**（`3ac9396e` / `58ba5165` / `5dbbe143` / `87787609`） | `r2e_task_facts.json`；参数化展开后仍需实跑确认，见 M-11 |
| pillow `3ac9396e` 的自定义 runner | 已读全文：`unittest.TestResult` 子类，`loader.discover("r2e_tests")`，手工打印 `short test summary info`，行形如 `PASSED <module>::<Class>::<method>`，Prime 的键规则适用 | `.../r2e_fixture_snapshots_20260911/3ac9396e…/r2e_tests/unittest_custom_runner.py` |
| parser 丢弃的 SKIPPED/XFAIL | 14/48 题的 gold 日志摘要里有，单次运行合计 38 个用例；原因见适配器卡 §5 | `logs_r2e/<repo>/<c12>/gold/a1/test_output.txt` |

## 1. 采集方式与约束

- 每个镜像起一个**一次性**容器，`--network none`（除 M-09 单独一组用默认网络），`--memory 8g --cpus 3`，跑完 `docker rm -f`。
- **只读观测**：除 M-11 的 `--collect-only` 与 M-12 的一次计时外，不要跑完整测试、不要 `git` 写操作、不要装包。
- 每题产物写到机器上的 `<M3 工作目录>/r2e_image_facts/<commit>/`，回传到本机 `runs/env_overnight_20260916/L4_r2e/machine/`（M3 包自行决定回传方式）。
- 结果落 JSONL：每行 `{commit, image_ref, check_id, status(pass/issue/unknown/not_checked), value, evidence_path}`；未跑的写 `not_checked`，跑了但输出无法判断的写 `unknown`。
- 优先级：**P0 = M-01 / M-02 / M-03 / M-05 / M-06**（适配器接入必须；旧 24 的缺口最大）。P1 = M-04 / M-07 / M-08 / M-10 / M-11。P2 = M-09 / M-12 / M-13。
- 只跑不到一半也有价值：按 P0 先扫完 48 题，再回头做 P1。

## 2. 逐项检查

以下命令都以 `C=<容器名>`、`FIX=<commit_hash>` 为占位，在容器里执行。

### M-01（P0）`/r2e_tests` 完整内容 — 只缺旧 24

**为什么**：隐藏测试的文本决定了 (a) 测试身份与 expected 键的对应、(b) 是否 import 仓库自带 test 模块（fixture 风险 + agent 可写的控制面）、(c) 是否有自定义 runner。新 24 已有快照，旧 24 完全空白。

```bash
docker cp "$C:/r2e_tests" "<out>/<commit>/r2e_tests"
docker exec "$C" bash -lc 'ls -la /r2e_tests; find /r2e_tests -type f -printf "%p %s %M %U:%G\n" | sort'
docker exec "$C" bash -lc 'sha256sum $(find /r2e_tests -type f) 2>/dev/null'
```

回传 `r2e_tests` 整个目录（旧 24 单个 `test_1.py` 通常 10–50 KB，48 题合计预计 < 20 MB）。同时记：

```bash
docker exec "$C" bash -lc 'grep -nE "^\s*(from|import)\s+[A-Za-z_][A-Za-z0-9_.]*" -r /r2e_tests | sed -E "s/.*(from|import)\s+//" | sort -u'
```

判据：import 目标里出现 `*.test*` / `*.tests.*` / `conftest` / `*testutils*` 的，记 `issue`（fixture 依赖 + 可写控制面），并把具体模块名写进 `value`。

### M-02（P0）`run_tests.sh` 原文、权限与实际入口 — 旧 24 要原文，48 题都要权限

**为什么**：账本里的 `run_tests_sh` 被截断到 400 字符（`r2e_probe.py:304` `[:400]`），且没记权限。rh2 若要复用来源入口，必须知道谁能改它。

```bash
docker exec "$C" bash -lc 'ls -la /testbed/run_tests.sh; sha256sum /testbed/run_tests.sh; echo ----; cat /testbed/run_tests.sh; echo ----; wc -c /testbed/run_tests.sh'
docker exec "$C" bash -lc 'ls -la /testbed/*.sh 2>/dev/null; ls /testbed | head -50'
```

判据：`run_tests.sh` 对 agent 身份可写 → `issue`（控制面）；与本地账本字段逐字节不同 → `issue`（账本截断或镜像漂移，要说明是哪一种）。

### M-03（P0）venv 属主、可写性、以及"测的是不是候选代码"

**为什么**：适配器要知道 agent 能不能装包、能不能改解释器，以及 `/testbed` 的源码是不是真的被 import（editable/`.pth` 还是 site-packages 里的独立副本）。清单第 8、9 项。

```bash
docker exec "$C" bash -lc 'id; whoami; echo HOME=$HOME; pwd'
docker exec "$C" bash -lc 'stat -c "%n %U:%G %a" /testbed /testbed/.venv /testbed/.venv/bin/python /r2e_tests /testbed/run_tests.sh'
docker exec "$C" bash -lc 'ls /testbed/.venv/lib/*/site-packages/*.pth 2>/dev/null; cat /testbed/.venv/lib/*/site-packages/*.pth 2>/dev/null | head'
docker exec "$C" bash -lc 'ls -d /testbed/*.egg-info /testbed/*.egg-link 2>/dev/null'
docker exec "$C" bash -lc 'cd /testbed && .venv/bin/python -c "import importlib,sys; m=importlib.import_module(\"PKG\"); print(m.__file__, getattr(m,\"__version__\",\"?\"))"'
docker exec "$C" bash -lc 'cd /testbed && .venv/bin/python -m pip freeze 2>/dev/null > /tmp/pip_freeze.txt; wc -l /tmp/pip_freeze.txt'
docker cp "$C:/tmp/pip_freeze.txt" "<out>/<commit>/pip_freeze.txt"
```

`PKG` 按仓库替换：aiohttp→`aiohttp`，coveragepy→`coverage`，datalad→`datalad`，numpy→`numpy`，orange3→`Orange`，pandas→`pandas`，pillow→`PIL`，scrapy→`scrapy`。

判据：包的 `__file__` 不在 `/testbed/` 下 → `issue`（改源码可能不生效，清单第 9 项）；`.venv` 在 `/testbed` 内且 agent 可写 → 记为控制面事实（不自动判坏）。

### M-04（P1）`pip freeze` 与系统侧快照（配方引用用）

M-03 已导出 `pip_freeze.txt`，再补：

```bash
docker exec "$C" bash -lc 'cat /etc/os-release | head -3; .venv/bin/python -V; .venv/bin/python -m pytest --version 2>&1 | head -3'
docker exec "$C" bash -lc 'cd /testbed && .venv/bin/python -m pip list 2>/dev/null | grep -iE "pytest|mock|hypothesis|xdist|randomly|timeout|cov"'
```

判据：装了 `pytest-randomly` / `pytest-xdist` / `pytest-timeout` 之类会影响顺序或选择的插件 → `issue`（重复评分一致性，清单第 14 项）。

### M-05（P0）修复提交的可发现性（泄漏通道的实际难度）

**为什么**：已知 `fix_reachable=commit`，但"对象存在"和"agent 能在几步内找到"是两件事。方案 A 接入前要做派生镜像/git 清洗，清洗方案取决于泄漏面有多宽。

```bash
docker exec "$C" bash -lc "cd /testbed && git remote -v; git config --get-regexp '^remote\.' | head"
docker exec "$C" bash -lc "cd /testbed && git for-each-ref --format='%(refname)' | head -20; git for-each-ref | wc -l"
docker exec "$C" bash -lc "cd /testbed && git branch -a --contains $FIX | head; git tag --contains $FIX | head -5"
docker exec "$C" bash -lc "cd /testbed && git rev-list --count HEAD..$FIX; git log --oneline -1 $FIX; git log --all --oneline | head -5"
docker exec "$C" bash -lc "cd /testbed && git log --all --oneline --follow -- \$(git show --name-only --pretty=format: $FIX | head -1) | head -5"
docker exec "$C" bash -lc "cd /testbed && ls .git/refs/remotes/*/ 2>/dev/null | head; cat .git/packed-refs 2>/dev/null | wc -l"
```

判据：`git branch -a --contains $FIX` 有输出 → 一条 `git log <branch>` 就能翻到修复提交，记 `issue` 且 severity P1；只有 reflog/游离对象可达 → P2。另记 `git remote -v` 是否有可用 URL（联网时可直接 `git fetch` 取答案）。

### M-06（P0）初态脏工作区的完整文件清单 — 旧 24 空白，新 24 只有 noop 的 `git diff HEAD`

**为什么**：R2E 镜像把"让老代码在新 Python 上跑起来"的补丁留在**未提交**状态（新 24 已见 aiohttp 把 `asyncio.async` 改成 `asyncio.create_task`、pandas 删掉 `pyproject.toml` 改 `setup.cfg`/`versioneer.py`）。任何"恢复干净初态"的实现（`git checkout .` / `git reset --hard` / `git clean -fd`）都会**破坏环境**。rh2 的候选提取也不能直接用 `git diff HEAD`。

```bash
docker exec "$C" bash -lc 'cd /testbed && git status --porcelain=v1 -uall'
docker exec "$C" bash -lc 'cd /testbed && git diff HEAD --stat; git diff HEAD --no-ext-diff --no-color > /tmp/initial.diff; wc -c /tmp/initial.diff'
docker cp "$C:/tmp/initial.diff" "<out>/<commit>/initial.diff"
docker exec "$C" bash -lc 'cd /testbed && git ls-files --others --exclude-standard | head -50'
```

判据：已跟踪文件有修改 → 记 `issue`（初态基线，清单第 2 项），把文件清单写进 `value`；未跟踪文件里出现 `r2e_*`、`expected*`、`*.json` 之类疑似评分材料 → 单列并与 M-08 合并判断。

### M-07（P1）隐藏测试依赖的仓库模块是否落在 agent 可写范围

依赖 M-01 的 import 清单。对每个形如 `a.b.tests.c` 的 import：

```bash
docker exec "$C" bash -lc 'cd /testbed && .venv/bin/python -c "import importlib.util as u; print(u.find_spec(\"MOD\").origin)"'
docker exec "$C" bash -lc 'stat -c "%n %U:%G %a" <上一步的 origin 路径>'
```

再与本地 `r2e_task_facts.json` 里该题的 `gold_included` / `gold_excluded` 比对：**gold 排除了该文件但隐藏测试 import 它** → 就是 datalad `58ba5165` 那类 fixture 缺失，记 `issue` severity P1。

### M-08（P1）镜像里还有没有别的答案/期望材料

```bash
docker exec "$C" bash -lc 'find / -xdev \( -iname "*expected*test*output*" -o -iname "expected_output*.json" -o -iname "r2e_*" \) -not -path "/proc/*" 2>/dev/null | head -40'
docker exec "$C" bash -lc 'ls -la /; ls -la /root 2>/dev/null | head -20'
docker exec "$C" bash -lc 'ls -la /testbed/.git/ | head -20; ls /testbed/.git/*.pack 2>/dev/null; du -sh /testbed/.git'
```

判据：`/r2e_tests` 以外还能找到 expected 映射或 gold patch → `issue` severity P1。注意 `facts.expected_file=0` 只查过 `/testbed/expected_test_output.json` 与 `/expected_test_output.json` 两条路径。

### M-09（P2）默认网络下的实际出网能力 — 只挑 8 题（每仓库 1 题）

**为什么**：此前所有观测都在 `--network none`，`egress_pypi=fail` 不能解释成"镜像无出网"。清单第 11、30 项要区分四段网络。

```bash
# 这一组用默认网络启动容器
docker exec "$C" bash -lc 'curl -sI --max-time 8 https://pypi.org/simple/ -o /dev/null -w "pypi=%{http_code}\n" || echo pypi=fail'
docker exec "$C" bash -lc 'cd /testbed && timeout 20 git ls-remote origin 2>&1 | head -3'
```

判据：能 `git ls-remote origin` → 记 `issue` severity P1（联网时可直接取上游修复），与 M-05 合并成"泄漏通道"结论。

### M-10（P1）测试收集的外部影响因素

```bash
docker exec "$C" bash -lc 'ls -la /testbed/conftest.py /testbed/pytest.ini /testbed/setup.cfg /testbed/tox.ini /testbed/pyproject.toml 2>/dev/null'
docker exec "$C" bash -lc 'grep -nE "\[tool:pytest\]|\[pytest\]|addopts|testpaths|\[tool\.pytest" /testbed/setup.cfg /testbed/tox.ini /testbed/pytest.ini /testbed/pyproject.toml 2>/dev/null'
```

判据：根 `conftest.py` 或 `addopts` 存在 → 记事实；其中含 `-p`、`--import-mode`、`--rootdir`、覆盖率参数的 → `issue`（rh2 若换入口会改变收集集合）。注意 pandas 三题的初态把 `pyproject.toml` 删了，别把"文件不存在"当成异常。

### M-11（P1）收集到的 node id 与 expected 键的对账

**为什么**：Prime 的键是 `nodeid.split("::")[1:]` 用 `.` 拼接，丢掉了文件路径。多文件（`test_1.py` + `test_2.py`，48 题里新 24 有 4 题、旧 24 未知）时**不同文件的同名测试会塌成同一个键**。这是 parser 层的正确性问题，静态查不出来。

```bash
docker exec "$C" bash -lc 'cd /testbed && rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests && .venv/bin/python -m pytest -q --collect-only r2e_tests 2>&1 | tail -n +1 > /tmp/collect.txt; wc -l /tmp/collect.txt'
docker cp "$C:/tmp/collect.txt" "<out>/<commit>/collect.txt"
```

（orange3 七题前面加 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`；pillow `3ac9396e` 用自定义 runner，跳过本项并注明。）
判据：把 node id 按 Prime 规则折成键后出现重复 → `issue` severity P1，并把重复键与来源文件写进 `value`。
**范围已收窄**：新 24 的 4 个双文件题已在 AST 层排除了跨文件同名，本项主要用来覆盖 ①参数化展开后的重名，②旧 24（连测试文件个数都不知道）。旧 24 优先。
顺带记 `--collect-only` 的总数与后面实跑摘要里 `SKIPPED`/`XFAIL` 的行数差，这是"环境条件改变键集"的直接观测量。

### M-12（P2）单次实跑的资源与时长（只在 P0/P1 扫完后做）

账本已有 `t_test`（旧 24 三次、新 24 一次）。只在需要复算稳定性时重跑，命令沿用 `r2e_probe.py` 的 gate 语义，不要自造新入口。
若有余量，对 14 个有 SKIPPED/XFAIL 的题（清单见适配器卡 §5）额外记一次 `SKIPPED [N]` 行的 N 值合计，和本机已记录的 38 对照——数值不同说明跳过条件在机器间会变，这是 `L4_report.md` Q1 的直接输入。

### M-13（P2）`xvfb` / 图形依赖

```bash
docker exec "$C" bash -lc 'command -v xvfb-run; command -v Xvfb; echo $QT_QPA_PLATFORM'
```

只对 orange3 的 7 题（旧 4 + 新 3）有意义。

## 3. 回传后 L4 会做什么

拿到 `r2e_tests/`、`initial.diff`、`collect.txt` 后，L4（或接手方）补完 `r2e_task_facts.json` 里现在标 `unknown` 的三类字段：旧 24 的 `hidden_test_files` / `hidden_test_repo_imports`、48 题的 `initial_dirty_tracked_files`、48 题的 `key_collision_after_prime_normalize`，并据此更新 `L4_r2e_adapter_card.md` §7 的"已知限制"与 `L4_report.md` 的风险分层。
