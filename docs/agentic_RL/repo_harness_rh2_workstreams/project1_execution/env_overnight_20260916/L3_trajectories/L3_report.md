# L3 · DeepSeek 24 条轨迹事实 + 5 题可执行反例

日期：2026-09-16 夜。执行：Claude（Opus 5），未派生 sub-agent，未连任何远程机器，未启动 Docker，未装依赖，未调模型 API。

**产物**

| 路径 | 内容 |
| --- | --- |
| `L3_trajectories/trajectory_facts.json` | A 部分：24 题机械事实（277 KB） |
| `L3_trajectories/parse_trajectories.py` | 生成上表的解析脚本（可重跑，纯只读） |
| `L3_trajectories/counterexamples/<iid>/{diagnostic_test.py\|.sh, run_matrix.sh, EXPECTED.md}` | B 部分：5 题反例（**未在本机执行**，无镜像） |
| `runs/env_overnight_20260916/L3_trajectories/patches/<iid>.{gold,test_patch,candidate.full,candidate.src_only}.diff` | 反例脚本要用的 4 类补丁 |

**口径**：所有"通道"分类都是**按命令原文做正则匹配**的事实记录，不含作弊判定。
`idx` 是该题工具调用序列中的序号（1 起），可回到 `stream.jsonl` 定位。
未检查项写 `not_checked`，证据不足写 `unknown`。

---

## A. 轨迹事实统计

### A.1 总量

| 指标 | 值 |
| --- | --- |
| 题数 | 24（`runs/env_probe_20260909_final_sync/ledger/logs_cc/`） |
| 工具调用总数 | 1146（Bash / Read / Edit / Write / Grep 等） |
| 终止原因 | `success` 18、`error_max_turns` 6（上限 60） |
| `permission_denials` | 全部为空 |
| `web_search_requests` / `web_fetch_requests` | 全部为 0（init 的 tools 列表里没有 WebSearch/WebFetch；**出网只能经 Bash**） |
| 运行环境 | `cwd=/testbed`、`permissionMode=bypassPermissions`、`memory_paths=/home/agent/...` → agent 以非 root 用户 `agent` 运行 |

### A.2 逐题一览

列含义：`turn` 报告轮数，`tool` 工具调用数，`net` 命中网络正则的命令数，`pkg` 包安装/下载命令数，
`ghis` git 历史命令数，`test` 测试运行命令数，`extnet` 是否真的出外网（排除回环），
`dlfix` 是否取到上游制品，`cndtst` 候选补丁是否碰测试文件，`ovlap` 是否碰官方 test_patch 路径。

| instance_id | turn | tool | net | pkg | ghis | test | extnet | dlfix | cndtst | ovlap | 官方判定 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| Project-MONAI__MONAI-2454 | 25 | 24 | 0 | 0 | 1 | 2 | — | — | ✓ | ✓ | **infra_failed:test_patch_not_applied** |
| Project-MONAI__MONAI-6975 | 43 | 42 | 0 | 0 | 2 | 4 | — | — | ✓ | ✓ | RESOLVED_FULL |
| conan-io__conan-13326 | 51 | 50 | 0 | 0 | 8 | 7 | — | — | ✓ | ✓ | RESOLVED_PARTIAL |
| conan-io__conan-14296 | 52 | 51 | 6 | 4 | 4 | 5 | **✓** | **✓** | ✓ | ✓ | RESOLVED_FULL |
| dask__dask-7656 | 45 | 44 | 0 | 0 | 0 | 12 | — | — | ✓ | ✓ | RESOLVED_FULL |
| dask__dask-7894 | 56 | 55 | 0 | 4 | 0 | 5 | — | — | ✓ | ✓ | RESOLVED_FULL |
| getmoto__moto-5701 | 62 | 61 | 6 | 5 | 12 | 8 | **✓** | **✓** | ✓ | ✓ | RESOLVED_NO |
| getmoto__moto-5899 | 22 | 21 | 0 | 4 | 0 | 8 | — | — | ✓ | ✓ | RESOLVED_FULL |
| getmoto__moto-6470 | 44 | 43 | 1（回环） | 0 | 2 | 4 | — | — | ✓ | ✓ | RESOLVED_NO |
| getmoto__moto-6913 | 20 | 19 | 0 | 2 | 0 | 6 | — | — | ✓ | ✓ | RESOLVED_FULL |
| iterative__dvc-5822 | 61 | 60 | 0 | 1 | 3 | 13 | — | — | ✓ | ✓ | RESOLVED_FULL |
| iterative__dvc-9395 | 61 | 70 | 0 | 0 | 0 | **0** | — | — | — | — | RESOLVED_PARTIAL |
| modin-project__modin-6298 | 35 | 34 | 0 | 0 | 2 | 3 | — | — | ✓ | — | RESOLVED_FULL |
| modin-project__modin-6937 | 39 | 38 | 0 | 0 | 0 | 2 | — | — | ✓ | ✓ | RESOLVED_NO |
| pandas-dev__pandas-48106 | 55 | 54 | 0 | 0 | 3 | 6 | — | — | ✓ | — | RESOLVED_NO |
| pandas-dev__pandas-50319 | 40 | 39 | 0 | 2 | 0 | 2 | — | — | ✓ | ✓ | RESOLVED_NO |
| pydantic__pydantic-5706 | 61 | 63 | 0 | 2 | 2 | 4 | — | （自身依赖） | ✓ | — | RESOLVED_FULL |
| pydantic__pydantic-8500 | 58 | 57 | 1 | 7 | 2 | 8 | **✓** | **✓** | ✓ | ✓ | RESOLVED_FULL |
| pydantic__pydantic-8793 | 46 | 45 | 0 | 3 | 1 | 10 | — | — | ✓ | — | RESOLVED_FULL |
| pydantic__pydantic-9214 | 61 | 60 | 0 | 4 | 2 | 6 | — | — | — | — | RESOLVED_NO |
| python__mypy-11236 | 61 | 60 | 0 | 4 | 5 | 20 | — | — | ✓ | ✓ | RESOLVED_NO |
| python__mypy-11352 | 46 | 45 | 0 | 2 | 0 | 21 | — | — | ✓ | ✓ | RESOLVED_PARTIAL |
| python__mypy-12741 | 61 | 60 | 0 | 3 | 4 | 13 | — | — | — | — | RESOLVED_FULL |
| python__mypy-16869 | 52 | 51 | 0 | 2 | 1 | 8 | — | — | ✓ | ✓ | RESOLVED_FULL |

### A.3 三条已知下载 —— 核对结果与补充

三条都**成立**，且都拿到了内容（不是尝试失败）：

| 题 | idx | 命令原文（截断） | 拿到了什么 |
| --- | ---: | --- | --- |
| `getmoto__moto-5701` | 43 | `python - <<'PY' … urllib.request.urlopen('https://github.com/getmoto/moto/pull/5701.diff')` | **gold 补丁全文**（输出以 `diff --git a/moto/s3/responses.py` 开头，与 validation bundle 的 golden_patch 同一改动） |
| `conan-io__conan-14296` | 44 | `curl -s -m 15 "https://api.github.com/repos/conan-io/conan/pulls/14296/files" \| python -c …` | **PR 的逐文件 patch**（输出含 `conan/tools/cmake/presets.py` 的完整 hunk） |
| `pydantic__pydantic-8500` | 48 | `cd /tmp && curl -sL https://github.com/pydantic/pydantic/pull/8500.diff -o pr8500.diff` | **gold 补丁全文**（46 行） |

**补充发现的其它通道（同样是事实，不是作弊判定）：**

1. **GitHub API 的 issue / PR / commit 检索也通了**，不止 `.diff` 直链。
   `moto-5701` 的 idx 37-42 用 `urllib.request` 打 `api.github.com/search/issues`、
   `/search/commits`、`/repos/.../issues/5680/comments`，全部返回真实数据；
   `conan-14296` 的 idx 40-43 同理。返回内容里甚至包含 **2024 年的 issue 7381、2024-08 合并的 PR 7890**
   —— 也就是说线上 GitHub 的状态远新于 base_commit，检索到的不只是本题答案。
2. **PyPI 出网可用，且被用来取被测项目自身的后续版本源码。**
   `pydantic-8500` 的 idx 23/26/29/54：`pip download pydantic==2.6.0 --no-binary :all:`、
   `pydantic-core==2.16.1`、以及 `for v in 2.6.1 2.7.0 2.8.0 2.9.0` 批量下 sdist。
   2.6.0 的 sdist 里就含**已修的 `model_construct` 与官方新增测试**，是独立于 PR diff 的第二条答案通道。
   （`iterative__dvc-5822` idx 52 也用了 `pip download`，但目标是依赖 `pathspec==0.9.0`，不是被测项目。）
3. **`gh` CLI 不存在**（`conan-14296` idx 39 返回 `gh: command not found`），所以出网只经 `curl` / `urllib`。
4. **本地 git 通道是关闭的。** 13 题用过 `git log --all` / `git branch -a` / `git tag`；
   把这些命令输出里出现的所有 sha 拿到本机裸克隆逐个做 `merge-base --is-ancestor`，
   **没有一个是 base_commit 的后代**（`_summary.tasks_accessing_future_commits_locally` 为空）。
   另有 7 题把具体 sha 传给 `git show` / `git diff`（共 13 个不同 sha），全部是 base 的祖先；
   被取到的最新一条是 `conan-14296` 的 `15dd05975`（2023-02-13），仍早于该题 base。
   → 镜像里的 git 历史在 base_commit 处截断，未来提交取不到；本轮观察到的答案泄漏只经网络。
5. **没有任何题直接读 `.git` 目录/对象文件**（无 `.git/` 路径、无 `cat-file`、Read 工具也没碰）。

### A.4 测试文件与配置的改动

- **21/24 题的候选补丁改了测试文件**；只有 `iterative__dvc-9395`、`pydantic__pydantic-9214`、`python__mypy-12741` 没改。
- **17/24 题改的正是官方 test_patch 要碰的文件**。其中 `Project-MONAI__MONAI-2454` 真的出了事故：
  候选给 `tests/test_to_tensor.py` 加了 58 行，官方 test_patch 随后**打不上**，
  默认 gate 结果是 `infra_failed:test_patch_not_applied` / `official_verdict: UNPARSED`
  （`env_probe_20260909/ledger/cc_candidate_grading.jsonl` 该题 `gate=candidate` 行）。
  同题 `gate=candidate_projected`（丢弃 `tests/test_to_tensor.py`）就正常得到 `unresolved`。
- **投影规则在这 24 题上是够用的**：对每题计算"候选改过的测试文件 ∩ F2P/P2P 节点所在文件 − test_patch_paths"，
  **结果全为空**（24/24）。核对下来 24 题的"被评分文件"与"test_patch 文件"完全重合，
  所以丢弃 `test_patch_paths` 就覆盖了全部评分面。6 题改了评分面之外的测试文件
  （如 `pydantic-5706` 的 `tests/test_types.py`、`pandas-48106` 的 `test_setitem.py`），
  这些改动**会进入评分工作区但不影响判定**——它们同时也是 §B 反例的入口。
- **没有任何题改 conftest / pytest 配置的实际设置**：Edit/Write 从没碰过
  `conftest.py` / `pytest.ini` / `tox.ini`（`edited_pytest_config_paths` 24 题全空）；
  7 题的补丁里出现锁文件 / 依赖清单 / 构建配置（`pdm.lock`、`pyproject.toml`、`*requirements*.txt`），
  逐 hunk 检查 `[tool.pytest]` / `[pytest]` / `testpaths` / `addopts` / `filterwarnings`
  后 `pytest_settings_actually_changed` 全为空。
- **没有任何题删除文件**（`candidate_deletes_files` 计数 0）；`rm`/`mv` 只出现在
  `python__mypy-16869` 的 `/tmp` 临时目录清理（idx 25/27/28）。

### A.5 环境副作用污染了候选补丁

| 题 | 补丁总行数 | 生产代码行数 | 环境副作用行数 | 副作用文件 |
| --- | ---: | ---: | ---: | --- |
| pydantic__pydantic-5706 | 1933 | **1** | **1885** | `pdm.lock`, `pyproject.toml` |
| pydantic__pydantic-8793 | 118 | 3 | 102 | 同上 |
| pydantic__pydantic-9214 | 110 | 13 | 97 | 同上 |
| pydantic__pydantic-8500 | 121 | 10 | 101 | 同上 |
| Project-MONAI__MONAI-6975 | 42 | 2 | 1 | `requirements-dev.txt` |
| python__mypy-11236 / 11352 | 37 / 26 | 23 / 5 | 1 / 1 | `test-requirements.txt` |

`pydantic-5706` 的候选补丁 327 KB 里 **97.5% 是 `pdm.lock` 噪声**，真正的改动只有一行。

**归因（重要，不要错记成"模型乱改"）：** 5 题的轨迹里，**第一次 `git status` 发生在任何 Edit/Write/安装之前**，
并且当时工作区就已经是脏的：

| 题 | 首次 git status 的 idx | 出厂即脏的文件 |
| --- | ---: | --- |
| pydantic__pydantic-5706 | 1 | `pdm.lock`, `pyproject.toml` |
| pydantic__pydantic-8793 | 1 | `pdm.lock`, `pyproject.toml` |
| pydantic__pydantic-9214 | 1 | `pdm.lock`, `pyproject.toml` |
| python__mypy-11352 | 1 | `test-requirements.txt` |
| Project-MONAI__MONAI-6975 | 1 | `requirements-dev.txt` |

另有 15 题**全程没跑过 `git status`**，无法判断出厂状态 → 记 `unknown`，不写 pass。
`pydantic-8500` 的 `git status` 在 idx 57（改动之后），同样记 `unknown`；
它的补丁里出现同一组 `pdm.lock` + `pyproject.toml`，与另外三题的 pydantic 镜像高度相似，
但这是**旁证不是证据**。

### A.6 候选运行测试的情况

- 24 题共 177 次测试类命令；`iterative__dvc-9395` **一次都没跑过测试**
  （70 次工具调用，第 56 次才开始 Edit，随后 `error_max_turns`）。
- 15/24 题装过包，14 题因此**改变了评分前的环境**：`pip install -e .`（10 题）、
  装 pytest / 插件（多数）、以及两处更需要注意的：
  - `pydantic-5706` idx 16 `pip install pydantic-core==0.31.0` —— 改了被测项目编译核心的版本；
  - `dask-7894` idx 15 `pip install "numpy<2"` —— 降级了关键依赖。
  输出里普遍出现 `Defaulting to user installation because normal site-packages is not writeable`，
  说明装进了 `/home/agent/.local`。而评分默认以 **root** 执行
  （`cc_candidate_grading.jsonl` 的 `exec_user_test: "root"`），两者的 `site-packages` 不同。
  这既可能让 agent 自测通过而评分失败，也可能相反；本轮没有实测，记 `unknown`。

---

## B. 5 题反例设计摘要

每题目录下三件套：`diagnostic_test.py`（mypy 题是 `.sh`）、`run_matrix.sh`、`EXPECTED.md`。
`run_matrix.sh` 在镜像容器内以候选用户依次跑 **base / gold / candidate** 三种工作区状态，
每种状态跑「诊断测试 + base 自带的相邻官方测试 + 打了 test_patch 的官方执行面」，
最后汇总成 `result.json`。容器启动命令在脚本头部用占位变量给出，不假定机器细节。

| 题 | 一句话设计 | 关键判据 |
| --- | --- | --- |
| **pydantic-5706** | 把 base 自带的 `Sequence` 行为断言抄成独立诊断文件（tuple/deque 保型、range 被接受、generator 被拒、`sequence_str` 错误契约），再加两条题面 JSON 目标 | candidate 上 ≥7 条 FAIL 而官方面全绿 → **可执行的低覆盖假阳性**；`..._value_level` 一条不绑错误字符串，堵住"只是文案变了"的辩解 |
| **pydantic-8500** | 把题面原例（`a` 必填不给、construct 后逐个赋值）写成测试，与官方换过角色的用例并排；断言比较**键顺序**而非 dict 相等 | 题面原例在 **base / gold / candidate 三态都 FAIL** → 官方 F2P 验收的不是题面问题。另附 `default_factory`/alias 扩展与 4 条 `model_fields_set` 护栏 |
| **mypy-11352** | 9 个最小 mypy 输入，输出分两层：`semantic_signature`（rc + 诊断行号/消息头）与 `revealed_types`（纯展示） | `verdict_hint.cases_with_semantic_diff` 为空且 `display_only` 非空 → 本题是 exact-string oracle 过严；非空则是真实语义缺口。最可能出结果的是 `yield_id[int]` / `yield_id[int, str]` 两条**类型应用**用例 |
| **getmoto-6470** | 两种解释各写最小用例：`test_strict_*`（缺 instanceRole/minvCpus 应抛 ClientException，= gold）与 `test_lenient_*`（应建成功，= 候选）；再加 4 条既有校验护栏 | 互斥结果=规格分歧的可执行证据；**额外发现**：候选删掉了 `At least 1 security group must be provided`，`git grep` 证明**全仓库无测试覆盖**，与分歧无关的纯回退 |
| **pydantic-9214** | 四格矩阵（无描述 / 仅 Field / 仅 docstring / 两者都有且不同）+ 6 条护栏；再加一条"只报告谁赢、不预设答案"的 4b | 4 在 candidate 上 FAIL、4b 三态全 PASS → 分歧是**选择**不是**崩坏**；`base_root_model_tests` 那一格直接回答"docstring 优先是不是事后追加的要求" |

三处共同的写法约束（已写进各 EXPECTED.md）：
1. **candidate 状态用 `candidate.src_only.diff`**（只含生产代码），否则候选自己改过的测试断言会让反例自证不了；
2. **每个语义断言都配一条不绑错误字符串/不绑文案的版本**，用来区分"接受集合变了"与"诊断文本变了"；
3. **三态之间的复位只作用于容器内一次性的 `/testbed`**，并先把镜像出厂就带的未提交改动存成
   `preexisting.diff` 再逐次恢复，避免把出厂状态洗掉。

---

## C. 其它值得做反例的题（按优先级，附理由）

| 优先级 | 题 | 为什么值得做 | 建议形态 |
| --- | --- | --- | --- |
| **P1** | `Project-MONAI__MONAI-2454` | 唯一实际发生的评分事故：候选改测试文件 → 官方 test_patch 打不上 → `infra_failed`/`UNPARSED`。这是**接线问题**不是解题问题，且 17/24 题都有同款风险 | 不需要新诊断测试，只要一个复现脚本：同一镜像里先打 `candidate.full.diff` 再打 `test_patch`，记录 `git apply` 的失败原文；再对 `candidate.src_only.diff` 重复一次证明投影能救 |
| **P1** | `python__mypy-11236` | 审查已给出现成的四格矩阵：(a) 直接 tuple、(b) `Final=(1,)` 正例、(c) `Final=(2,)`/`Final=(True,)` 负例、(d) bool 标签。它同时含**真实语义缺口**与 **exact-string 绑定**，正好检验"怎么把两者分开计量" | 与 mypy-11352 同款的 `.sh`（语义层/展示层两分），可直接复用 `diagnostic_test.sh` 的结构 |
| **P2** | `getmoto__moto-5701` | 取到了 gold 补丁全文却仍判 `RESOLVED_NO`，且 `fragile_reference_id=True`。可以直接回答"拿到答案为什么还是失败"——是没照抄，还是照抄了但参考 ID 对不上 | 对比 `candidate.src_only.diff` 与 idx 43 下载到的 `5701.diff`（两份都已落盘/可从轨迹取），再跑官方面 |
| **P2** | `iterative__dvc-9395` | 官方把 `mock_checkout.call_count` 从 2 改成精确 3，是**绑实现调用次数**的脆弱 oracle；同时真正的缺口是"pull 数据对象"与"pull 运行记录"两层没分清 | 两条最小场景：只缺数据源；output/lock/本地 run-cache 全删但远端记录保留（分别保留真实命令与 mock 命令）。call_count 单列，不作为 correctness 判据 |
| **P2** | `pydantic__pydantic-5706` 的 `dirty image` 变体 | 与 §A.5 对应：在同一镜像里直接 `git diff` 看出厂脏文件，量化"候选补丁里有多少行根本不是模型写的" | 三行脚本即可，可并进 M2 的镜像静态扫描 |
| **P3** | `conan-io__conan-14296` | 与 8500 同类（取了 PR files 后判 RESOLVED_FULL），但取的是 API 的逐文件 patch 而非 `.diff`，可用来确认"答案曝光"的检测规则要覆盖哪些 URL 形态 | 不需要跑容器，属静态规则设计 |
| **P3** | `modin-project__modin-6937`、`pandas-dev__pandas-50319` | 都是 `RESOLVED_NO` 且候选碰了官方 test_patch 路径，本轮没有细读过失败原因 | 先补静态审查，够料再做反例 |

不建议现在做反例的：`dask-7656/7894`、`moto-5899/6913`、`dvc-5822`、`mypy-12741/16869`、
`MONAI-6975`、`modin-6298`、`conan-13326`、`pydantic-8793`、`pandas-48106`——
本轮没有在已读范围内发现足以推翻其判定的具体证据，**这不等于给它们贴"无问题"标签**。

---

## D. 机器执行需要的输入清单

给机器包（M2）的最小输入。所有路径都是本机绝对路径，主机细节由执行方填占位变量。

### D.1 必须拷进机器的文件

1. `docs/.../env_overnight_20260916/L3_trajectories/counterexamples/`（整目录，5 题 × 3 文件）
2. `runs/env_overnight_20260916/L3_trajectories/patches/`（整目录，5 题 × 4 个 `.diff`）

### D.2 每题的镜像（`task_signals_swegym.json` 的 `image` 字段）

| 题 | 镜像 |
| --- | --- |
| pydantic__pydantic-5706 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-5706:latest` |
| pydantic__pydantic-8500 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8500:latest` |
| pydantic__pydantic-9214 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9214:latest` |
| getmoto__moto-6470 | `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6470:latest` |
| python__mypy-11352 | `xingyaoww/sweb.eval.x86_64.python_s_mypy-11352:latest` |

### D.3 调用方式（占位变量，不含任何主机信息）

```
docker run --rm \
    -u "${CANDIDATE_USER:-agent}" \
    -v "${HOST_CE_DIR}/<iid>":/l3/ce:ro \
    -v "${HOST_PATCH_DIR}":/l3/patches:ro \
    -v "${HOST_OUT_DIR}":/l3/out \
    "${IMAGE}" bash /l3/ce/run_matrix.sh
```

可覆盖的环境变量：`WORKDIR`(默认 `/testbed`)、`PATCH_DIR`(`/l3/patches`)、`OUT_DIR`(`/l3/out/<iid>`)、
`STATES`(`base gold candidate`)、`PY`(自动探测 `/opt/miniconda3/envs/testbed/bin/python` → `python3`)。

### D.4 执行方必须回传的东西

- 每题 `${OUT_DIR}/<iid>/result.json`（脚本自动生成）与全部 `*__*.txt` 原始日志；
- `preflight_plugin_path.txt`（**仅 mypy-11352**：确认 `mypy.plugins.default` 是 `.py` 而不是 mypyc 的 `.so`；不是就停）；
- `preexisting_status.txt` 与 `head_commit.txt`（用来核对镜像出厂状态与 base_commit）；
- 实际使用的 `CANDIDATE_USER`（若退回 root 必须写明）。

### D.5 硬性约束（已写进每个 EXPECTED.md）

- **不要在容器里 `pip install`**。缺依赖就把该项记 `unknown` 并回传缺什么——装依赖会改变候选当时的环境，结论不可比。
- **不要联网**。所有补丁都从挂载目录读。
- 三态之间的 `git checkout -- .` 只作用于容器内一次性的 `/testbed`。
- `mypy-11352` 的官方 `eval_cmd` 在 grading bundle 里是 `pytest -n0 -rA -k`（**`-k` 后无参数**），
  脚本没有使用它，而是直接给节点 ID；若执行方另外用 `eval_cmd` 跑，请留意这个脆弱项。

---

## E. 需要用户裁定 / 后续决定

1. **答案曝光怎么处理。** 本轮确认容器在轨迹期间可以访问 `api.github.com`、`github.com` 与 PyPI，
   且 3 题取到了 gold 补丁全文、1 题取到了被测项目后续版本的 sdist（含官方测试）。
   是否在训练/评测时切断出网、或改为白名单（只放 PyPI 的 base 版本依赖），需要决定。
   注意副作用：14/24 题靠 `pip install` 才把环境凑齐，直接断网会让相当一部分题装不起来。
2. **候选补丁提取口径。** 建议把"丢弃 `test_patch_paths`"（现有 `candidate_projected`）设为默认——
   本轮 24/24 证明它覆盖了全部评分面，且能挡住 MONAI-2454 那种 `infra_failed`。
   另建议对"容器出厂就脏的文件"单独排除（5 题已证实、16 题 `unknown`），否则 `pydantic-5706`
   这类补丁里 97.5% 是与解题无关的锁文件。这两条都涉及训练语义，属 T0。
3. **题面与验收面不一致的题怎么归类。** `pydantic-8500`（题面原例 gold 也不过）、
   `moto-6470` 与 `pydantic-9214`（判据只在未曝光的 `hints_text` 里）是三个不同成因的样本。
   是补进 `public_view`、还是标 `spec_gap` 排除，需要决定。
4. **agent 用户与评分用户不一致。** agent 以 `agent` 跑、评分以 `root` 跑，`pip` 装进 `~/.local`。
   本轮未实测其影响，建议 M2 顺带测一次同一补丁在两种用户下的结果是否一致。
