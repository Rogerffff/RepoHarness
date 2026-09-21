# dask/dask 仓库级共性事实（L1_dask，静态）

2026-09-16 夜 · 只读证据，未起容器、未装依赖、未连远程机器。以下结论对本包 14 题共同适用，题级 JSON 用 `repo_level_findings.md#R<n>` 引用，不逐题重复抄。
证据路径约定：`s2/...` = `docs/agentic_RL/repo_harness_rh2_workstreams/s2/...`；`stage1/...` = `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<instance_id>/<gold|empty>/offline/a1/`；base 代码用 `git -C runs/env_overnight_20260916/repos/dask show <commit>:<path>` 读取（COMMON.md 允许的只读操作），未建 worktree。

## R0. 配方与判分口径（14 题一致）

- `SPECS_DASK` 对 2.11 … 2024.5 共 59 个版本用同一个字典，**没有 `python` 键**（源码里被注释掉），`packages="environment.yml"`，`install='python -m pip install --no-deps -e .'`，`test_cmd="pytest -n0 -rA  --color=no"`。
  证据：`s2/vendor/swegym_constants_242429c1.py:1755-1774`。
- 本包 14 题的 `eval_cmd` 全部等于上面的 `test_cmd`，**都带 `-n0`**，不存在 mypy 那种"部分题在 xdist 并行下评分"的分裂。镜像里确实装了 `xdist-3.6.1`（`stage1/.../test_output.txt` 的 `plugins:` 行），但被 `-n0` 关掉。
  证据：各题 `mat/<tid>/grading.json` 的 `eval_cmd`；`runs/env_overnight_20260916/L1_dask/prescan.json`。
- parser = `parse_log_pytest`（`s2/vendor/swegym_log_parsers_242429c1.py:338` `parse_log_dask = parse_log_pytest`，`:340` 注册到 `"dask/dask"`），即"逐行 `split()`，`[1]` 当测试 ID、`[0]` 当状态，后写覆盖先写"。
- 仓库自带 `addopts`：2.25–2021.02 是 `-rsx --durations=10`；2021.04 起加 `-v`；2021.07 起是 `-v -rsxfE --durations=10`；2022.01 起再加 `--color=yes`（被 eval_cmd 的 `--color=no` 覆盖）。**没有任何版本带 `-n auto`**。
  证据：各 base 的 `setup.cfg` `[tool:pytest]`；2024.2 改到 `pyproject.toml` `[tool.pytest.ini_options]`（`9c20facdfb:pyproject.toml`）。
- 全部版本 `xfail_strict=true`，并声明 `network` / `slow`（2022.01 起还有 `gpu`）marker。`eval_cmd` **不带** `-m "not network"`，但本包 14 题的 F2P/P2P 所在测试文件里 `@pytest.mark.network` 命中为 0（逐题 grep，见各题 checks.7）。

## R1. 参数化 ID 被按空格截断（与 L1_moto_2 的 R8 同一机制，dask 侧实证）

`parse_log_pytest` 取 `line.split()[1]`，pytest 参数化 ID 里只要含空格就在第一个空格处被截断。SWE-Gym 的参考集是用同一 parser 生成的，两边"一致地错"，所以 `f2p_missing/p2p_missing` 恒为 0，异常被吞掉。

本包命中 2 题、各 3 条 P2P（`dask__dask-10972`、`dask__dask-6818`，同一测试文件 `dask/dataframe/io/tests/test_csv.py`）：
```
dask/dataframe/io/tests/test_csv.py::test_skiprows_as_list[read_csv-read_csv-files0-str,
dask/dataframe/io/tests/test_csv.py::test_read_csv[read_table-read_table-name
dask/dataframe/io/tests/test_csv.py::test_skiprows_as_list[read_table-read_table-files1-str\t
```
真实 ID 见 `stage1/dask__dask-10972/gold/.../test_output.txt`（`...files0-str, int, int\n]`、`...name   amount\nAlice    100...-\s+]`）。

与 moto 的差别：**本包这 6 条当前没有塌缩**（每个截断键仍只对应 1 条真实用例），因此没有产生直接的假阳性。但 `...test_read_csv[read_table-read_table-name` 同时是另一条**未被截断**的真实 ID（`...name\tamount\n...`，其中 `\t` 是字面反斜杠-t，不含真空格）的前缀，参数化内容一动就会塌缩。
`task_signals_swegym.json` 对这 2 题记 `fragile_reference_id=false`，与 moto 的漏检情况一致。

## R2. `-rA` 的 SKIPPED 行不是测试 ID：跳过的用例在 status_map 里**完全消失**，并额外注入伪键

pytest 短摘要里 SKIPPED 的格式是 `SKIPPED [<计数>] <文件>:<行号>: <原因>`，不带 `::` 测试 ID。parser 取 `split()[1]` 得到的是 `[3]` 这种**计数括号**：
```
SKIPPED [3] dask/dataframe/io/tests/test_parquet.py:146: fastparquet not found
```
证据：`stage1/dask__dask-6801/gold/.../test_output.txt:1726-1729`；`status_map.json` 里因此出现 `"[18]": "SKIPPED"`、`"[1]"`、`"[2]"`、`"[3]"`、`"[4]"`、`"[6]"`、`"[7]"`、`"[8]"`、`"[22]"` 共 9 个伪键（`runs/env_overnight_20260916/L1_dask/scripts/extrakeys.py` 输出）。

两个后果，都是结构性的：
1. **被跳过用例的真实 ID 一条都不进 status_map。** 如果某条 F2P/P2P 在重建后的镜像里因缺可选依赖变成 SKIPPED，它在 status_map 里既不是 PASSED 也不是 FAILED，而是"不存在"。RH2 把"参考 ID 缺失"算失败还是算基础设施异常，会直接决定这类环境漂移是被判 0 还是被判 infra —— 这是需要用户裁定的口径问题。
2. **伪键污染计数。** `status_map` 的条目数不再等于真实用例数：6801 是 255 条结果行 → 191 个键（74 条 SKIPPED 塌进 9 个伪键 + 1 个日志伪键，见 R4）。任何按 `len(status_map)` 做健康度判断的逻辑都会被误导。

本包各题 gold 侧 SKIPPED 结果行数：6801=74（其中 72 条 `fastparquet not found`）、8792=13、9212=13、10972=8、6818=8、8597=4、7656=2（XFAIL）、8820=2（XFAIL）、7305=1；7894/6626/7138/8801/9378 = 0。
所幸本包 14 题的 F2P/P2P **没有**任何一条落在被跳过的用例上（参考集是在同一镜像上生成的，跳过的用例自动落选），所以当前判分未受影响。

## R3. 工具链是"现代 pytest + 历史 dask"，导致大批既有用例在镜像里恒失败并被排除出参考集

全部 14 题的镜像都是 `pytest-8.3.2`（Python 3.8.15/3.8.19/3.9.19/3.10.14 不等）。
证据：各题 `stage1/.../gold/.../test_output.txt` 的 `platform linux -- Python x.y.z, pytest-8.3.2` 行。

`pytest.warns(None)` 在 pytest 8 已被移除（`TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`），而 2020–2022 年的 dask 测试大量使用它。逐题统计（gold 侧 FAILED 且不在参考集内的条数 / 参考集条数）：

| 题 | 恒失败条数 | 参考集条数 | 主因 |
| --- | --- | --- | --- |
| dask__dask-7138 | **92** | 469 | 92 条全是 `pytest.warns(None)`（test_cov / test_isin_rand 系列） |
| dask__dask-8792 | 11 | 93 | 7 条 `pytest.warns(None)` + pandas/scipy 版本漂移 |
| dask__dask-9212 | 10 | 105 | pandas 内部 API 漂移 + emscripten 用例 |
| dask__dask-6801 | 7 | 173 | pandas `_mgr` 内部 API 漂移（pyarrow 路径） |
| dask__dask-8597 | 2 | 117 | `pytest.warns(None)` |
| dask__dask-6818 | 2 | 122 | pandas `_mgr` 漂移 |
| dask__dask-8801 | 2 | 43 | `test_collect_yaml_permission_errors`（容器内 root，chmod 去权限无效） |
| dask__dask-6626 | 1 | 15 | `pytest.warns(None)`（`test_nonempty_series_sparse`） |
| dask__dask-7656 / 8820 | 1 | 49 / 46 | `test_check_meta_flag`（上游库 API 变更） |
| 7894 / 10972 / 7305 / 9378 | 0 | — | — |

证据：`runs/env_overnight_20260916/L1_dask/scripts/prefail.py` 的输出；逐条 FAILED 名见 `scripts/extrakeys.py`。

含义（两条都影响结论的解释方式）：
- **不是**"参考集被污染"——SWE-Gym 在同一镜像上生成参考集，恒失败的用例本来就没进 F2P/P2P，判分自洽。
- **是**"回归保护被系统性削弱"：被排除的往往正是与题目同函数、同族的用例。最刺眼的是 `dask__dask-6626`：与 gold 改的 `_nonempty_series` 直接相关的另一分支用例 `test_nonempty_series_sparse` 恰好恒失败被排除。7138 更极端：同文件 16%（92/561）的用例是死的。
- 另一后果：`environment_screening_definition` 里检查 6 的"该版本历史工具链已恢复"在 dask 上**不成立**，`SPECS_DASK` 甚至没有声明 `python`，一切以镜像为准。

## R4. 捕获日志里的 `ERROR ...` 行会被当成一条"测试"写进 status_map

`-rA` 之前的失败详情段里有 `------ Captured log call ------`，其中 logging 的 ERROR 记录以 `ERROR` 开头顶格输出：
```
ERROR    dask.dataframe.shuffle:shuffle.py:1205 ignoring exception in ensure_cleanup_on_exception
```
证据：`stage1/dask__dask-6801/gold/.../test_output.txt:1322`；结果是 `status_map.json` 里多出一个键 `"dask.dataframe.shuffle:shuffle.py:1205": "ERROR"`。

即 **parser 会摄入任何顶格以 `PASSED/FAILED/ERROR/SKIPPED/XFAIL/XPASS` 开头的输出行**，不限于短摘要段。本包只观察到这一条（6801），不影响判分（不在参考集里）。风险边界（未验证，`not_checked`）：短摘要段出现在捕获日志之**后**（6801 里摘要头在 1552 行、日志在 1322 行），所以正常情况下真实结果会覆盖注入值；能否构造出"在摘要之后再打印"的注入，取决于 R5 的 conftest 面。

## R5. `conftest.py` 不在任何 test_patch 里，因而不属控制面 —— dask 上这个已知缺口是**直接可达**的

- RH2 的控制面 = `HygieneRules`，其中 `test_files` = `private.test_patch` 触碰的精确路径，`test_globs=()`（第四组 P-B 已取消测试名通配），`forbidden_globs=(".rh2*", "rh2/*")`。
  证据：`rh2/src/repoharness2/grading/manager.py:656,671-673`、`:581`。
- 该缺口已被登记："conftest.py / pytest.ini / tox.ini / setup.cfg·pyproject 的 pytest 段 / 插件 / 启动脚本等真正能改变测试收集的文件并不在上述规则内，本批不设计通用规则引擎"。
  证据：`rh2/src/repoharness2/grading/trusted_projection.py:22-24`。
- dask 侧的具体性：仓库根有 `conftest.py`（2024.x 还有 `dask/conftest.py`），里面已经定义了 `pytest_addoption` 与 `pytest_runtest_setup`（`--runslow` 逻辑）。
  证据：`git show 9c20facdfb:conftest.py`、`git ls-tree -r --name-only 9c20facdfb | grep conftest`。
- 本包 14 题的 test_patch **每题只碰 1 个测试文件**，没有一题碰 `conftest.py`。因此对 14/14 题而言，候选写 `conftest.py` 属于"solution surface"，会被重放进评分容器并在收集/执行阶段生效。

结论口径：这**不是**本包新发现的漏洞，而是已登记缺口在 dask 上的可达性证据 —— dask 是本轮 9 个仓库里 conftest 钩子最实（自带 `pytest_runtest_setup`）的一个，适合用来做该缺口的最小反例。建议的下一实验（不在本包执行）：在任一 dask 题上提交一个只改 `conftest.py`、加 `pytest_runtest_call` 包装吞异常的候选，观察 outcome 是 RESOLVED_FULL 还是被拦。

## R6. 判分"文件边界"（第四组 B）在本包无争议：14/14 题 `additional_exclusions = []`

- 14 题的 `test_patch` 全部只触碰 1 个测试文件（`dask/tests/test_*.py`、`dask/array/tests/test_*.py`、`dask/dataframe/**/tests/test_*.py`），无一碰源码、无一碰 `conftest.py`；
- 14 题的 `golden_patch` 全部只触碰 1 个源码文件（`dask/delayed.py`、`dask/base.py`、`dask/config.py`、`dask/array/{overlap,routines,slicing,ma}.py`、`dask/dataframe/{utils,partitionquantiles}.py`、`dask/dataframe/io/csv.py`、`dask/dataframe/io/parquet/core.py`），无一碰测试路径。
  证据：`runs/env_overnight_20260916/L1_dask/prescan.json` 的 `tp_paths` / `gold_paths` / `tp_nontest` / `gold_touches_test`（后两项全为空）。
- 旁证：`docs/.../swe_grading_wiring_20260915/precheck_after_pb.md:12,38-39` 对 dask 两题的记录与此一致（gold 无被忽略路径；DeepSeek 候选改了 official test file 会被忽略/拒绝）。
- 一个需要注意的不对称：候选若把新测试写进**不在 test_patch 里的**测试文件（如 7656 的候选往 `dask/tests/test_base.py` 加用例，见 `runs/env_probe_20260909_final_sync/ledger/logs_cc/dask__dask-7656/candidate.diff`），该文件不会被恢复。本包各题的 F2P/P2P 都集中在同一个（被恢复的）文件里，所以当前无自判风险；但换一道 P2P 跨文件的题就有。

## R7. 安装 rc 只对 2024.x 题为 1，且与判分结果无关

- 13 题 `rc_install=0`；只有 `dask__dask-10972`（2024.2，唯一 2024.x）rc=1：`pip install --no-deps -e .` 走 PEP 517 构建隔离，离线下要现下载 `setuptools>=62.6`，DNS 失败。
  证据：`stage1/dask__dask-10972/gold/.../test_output.txt:485-515`。
- 与 moto 4.1 同型：镜像自带的 editable 安装已指向 `/testbed`，安装失败不影响候选代码被测（10972 的 gold 仍 RESOLVED_FULL，empty 仍 RESOLVED_NO）。**`rc_install` 不可作为健康度或候选失败归因信号。**
- 可选修法（未实施）：dask 2024.x 配方加 `--no-build-isolation`，或镜像预置 setuptools wheel；只影响 2024.x，需按检查 39 重验。

## R8. 可选依赖：`fastparquet` 缺失是本包唯一有规模的缺口

- 逐题 grep 测试文件里的 `pytest.importorskip`：命中的模块是 `numpy`、`pandas`、`dask.array`、`dask.dataframe`、`dask.array.ma`、`dataclasses`、`cloudpickle`、`psutil`、`graphviz`、`matplotlib.pyplot`、`ipycytoscape`、`jsonschema`、`pyarrow`、`fastparquet`、`snappy`。无一条通过网络获取。
- 实际在镜像里缺席（由 gold 日志的 SKIPPED 原因反推）：`fastparquet`（6801，72 条）、`matplotlib`（8792/9212）、`lz4` / `lzma` 压缩函数（10972/6818）、`ipycytoscape`（9212）。`pyarrow` **在 6801 的镜像里存在**（该题 F2P 全是 `[pyarrow-...]` 参数且 PASSED）。
- 本包 14 题的 F2P/P2P 无一条落在被 skip 的用例上，所以"F2P/P2P 因缺可选依赖被 skip"在**当前镜像**下没有发生。但若换镜像/重建环境，R2 说明这类回归会表现为"参考 ID 从 status_map 里消失"，而不是一条明确的 SKIPPED 记录。
- 网络类依赖（s3/http fsspec、requests、boto3、torch.hub）：逐题 grep 全部测试文件，命中的只有注释里的 GitHub issue 链接和 `dask/tests/test_base.py` 里 `"s3fs"` 出现在一个**字符串列表**（`test_persist_*` 的模块名清单）里，不构成真实网络访问。判为 `pass`。

## R9. 题面质量分布（14 题）

- 题面自带可执行修复代码：`dask__dask-7656`（**Fix** 段给出 `if field.init or hasattr(...)`）。
- 题面与评分目标不是同一问题：`dask__dask-10972`（题面要"让 strict xfail 行为一致"，评分要"BOM 编码下 read_csv 结果正确"；且题面现象归因 s390x 大端，x86_64 镜像上不可复现）。
- hints 含题面没有的**定位级或裁定级**信息（逐题核对，见各自 checks.3）：
  - `6626`：维护者点名 meta_nonempty + 报告者的 pdb 跟踪（core.py:5174/5190）。
  - `10972`：指向 issue #5787 与 "split in the middle of a two byte character sequence" 的（部分错误的）根因判断。
  - `6801`：诊断结论 + 可用修法 `to_delayed(optimize_graph=False)` + arrow.py 行级 permalink + "4x 是预期行为" 的裁定。
  - `7305`：三条互斥修法的完整取舍讨论，以及维护者对最终采纳方案的告诫；本题唯一的 F2P 正是该方案的副作用。
  - `8597`：完整 traceback 与精确到行的 `slicing.py:647 divide by zero`（题面的 traceback 被省略号截断）。
  - `8801`："we should provide a better error message ..." 这条裁定 —— **题面里根本没有任务**，要做什么只在 hints 里。
  - 反例（hints 无额外信息）：`7894`、`8792`（两句寒暄）、`8820`/`7656`/`7138`（hints 为空）、`9212`（一句"欢迎提 PR"）、`6818`（一句与题面同向的猜测）、`9378`（讨论 numpy issue #15200，并给出一条**指向顶层 creation.py 的 permalink**，反而可能把人引到错误的修改位置）。
  hints 不可见，因此前 6 题的公开难度显著高于其"表面难度"。

## R10. 评测容器以 root 运行，权限类测试恒失败

`dask__dask-8801` 的 `test_collect_yaml_permission_errors[directory]` / `[file]` 在 gold 与 empty 两侧都 FAILED；日志里 `tmpdir = local('/tmp/pytest-of-root/pytest-0/...')` 说明测试以 root 身份运行，用例靠 `chmod` 去掉读权限来构造 OSError 的做法对 root 无效。
证据：`stage1/dask__dask-8801/gold/.../test_output.txt:1382-1383,1424-1436`。
后果与 #R3 同型但成因不同（不是工具链版本，是运行身份）：这两条恰好是保护 8801 gold 里 `except OSError: return None` 分支的唯一用例，被排除后，把该分支整段删掉的候选仍能拿满分。
本包只有 8801 命中；其它 13 题的测试不依赖文件权限。

## R11. 跨题泄漏：本包内有两对"后一题的 base 已含前一题的 gold"

| 前题（答案） | 后题（base 已含答案） | 证据 | P2P 交集 |
| --- | --- | --- | --- |
| `dask__dask-7656`（delayed.py 的 `if hasattr(expr, f.name)`） | `dask__dask-8820`（base `4e5dfe7463`） | `4e5dfe7463:dask/delayed.py:112-116,194-198` 逐字含 gold 及其注释 | 43 / 45 |
| `dask__dask-8792`（base.py 的 `clone_key` 新实现 + 新 docstring） | `dask__dask-9212`（base `aa801de0f4`） | `aa801de0f4:dask/base.py:1503-1515` 逐字含 gold；且 9212 的 P2P 里就有 `test_clone_key`（带 8792 修好后的哈希常量） | — |

两对都不是"同一 PR 的重复题"（间隔 10 个月 / 4 个月，修的是不同问题），所以按 `problem_statement` 或 `base_commit` 去重都不会命中；但它们构成**直接答案泄漏**：把后一题放训练、前一题放评测，模型在后一题的工作树里就能读到前一题的完整答案与期望常量。
建议（未实施）：对 216 题做一次"A 的 golden_patch 的新增行是否已出现在 B 的 base 树中"的全量交叉检查，并把命中的对强制同侧划分。

## R12. 题面质量的三类结构性问题（本包分布）

按"公开材料能否推出 F2P"分档（只统计结论明确的）：
- **推不出 / 与评分冲突（4 题）**：`10972`（题面要改 xfail 行为、评分要 BOM 修复，且题面现象在 x86_64 不可复现）、`8801`（题面是无任务的求助帖）、`7305`（唯一 F2P 是修法副作用，维护者自己倾向的另一种正确修法会被判 0）、`8792`（题面逐字给出的"应有实现"与 F2P 要求的哈希不一致，照题面做必判 0）。
- **要求不充分但方向正确（3 题）**：`6801`（隔着一条从"代码跑 4 次"到"图层优化幸存"的长推理链）、`6626`（F2P 不覆盖题面的 set_index 场景）、`9378`（题面复现用顶层 `da.ones_like`、评分要 `da.ma.*`）。
- **题面自带可执行修复（3 题）**：`7656`、`7138`、`9212` —— 三题的题面里都有可直接粘贴的修复代码，且与 gold 等价。适合做训练轨迹，不适合做定位能力评测。


## R13. 逐条核对"F2P/P2P 会不会因缺可选依赖被 skip"（协调者点名的问题）

方法：`scripts/refskip.py` —— 对 14 题的每一条参考 ID，从 base 树取出其所在测试文件，按顶层 `def`/`class` 切段定位函数体，扫描**模块级**与**函数体内**的 `pytest.importorskip` / `@pytest.mark.skipif`。结果落 `runs/env_overnight_20260916/L1_dask/refskip.json`。

结论（静态 + stage1 日志双向核对）：

- 参考 ID 总数 **1706**（14 题 F2P+P2P 之和），其中被任何守卫覆盖的 **103 条**，**F2P 只有 1 条**：
  `dask__dask-7656::test_delayed_with_dataclass`，守卫是 `pytest.importorskip("dataclasses")` —— dataclasses 自 Python 3.7 起是标准库，镜像最低是 3.8，实际不可能触发。
- **模块级**（一旦缺席整文件被跳过）的守卫只有 5 个模块：`numpy`（test_overlap/test_routines/test_slicing）、`pandas` + `dask.dataframe`（test_csv）、`dask.array.ma`（test_masked）。全部在镜像里存在（对应各题 gold 侧参考集 100% PASSED）。
- **函数体内**的 `importorskip` 命中模块：`dask.array`、`dataclasses`、`numpy`、`pandas`、`psutil`、`graphviz`、`ipycytoscape`、`jsonschema`、`pyarrow`、`fastparquet`、`snappy`。前 4 个在镜像里都有；后几个需要分情况：
  - `psutil`（10972 `test__infer_block_size` / `test_auto_blocksize_csv`、6818 `test_auto_blocksize_csv`）、`graphviz`（8792/9212 的 visualize 系列）、`jsonschema`（8801 `test_schema`）：这些用例都在 P2P 且在 gold 日志里 **PASSED**，说明三个包都装了。
  - `fastparquet` / `snappy`（6801）：我的扫描器把它们标成"守卫"，但**核对源码后发现两处都是条件守卫**，只在参数选中缺席引擎时才执行 —— `test_filters_v0` 的 `if write_engine == "fastparquet" or read_engine == "fastparquet": pytest.importorskip("fastparquet", ...)`（`5589bfddb5:dask/dataframe/io/tests/test_parquet.py:1270-1272`）、`test_writing_parquet_with_compression` 的 `if compression in ["snappy","default"]: pytest.importorskip("snappy")`（同文件 :1521-1523）。参考集里只有 `[pyarrow-*]` 参数，日志里 `test_filters_v0[pyarrow-pyarrow]` 与 `test_writing_parquet_with_compression[pyarrow-snappy]` 都 **PASSED**（`stage1/dask__dask-6801/gold/.../test_output.txt:1617,1626`），说明 snappy 实际也在镜像里，缺的只有 fastparquet。
- 对照 stage1 日志：14 题 gold 侧 **没有任何一条 F2P/P2P 被 SKIPPED**（所有 SKIPPED 行都落在参考集之外的用例上）。

因此对协调者的问题，本包的答案是：**当前镜像下 0 条 F2P/P2P 因缺可选依赖被 skip，唯一的 F2P 守卫是标准库。真正的风险不在"现在"而在"换镜像之后"**，且风险的表现形式被 #R2 掩盖：一旦某条参考用例变成 SKIPPED，它在 status_map 里是"不存在"而不是"SKIPPED"，判分侧看到的是 `f2p_missing`/`p2p_missing`，而不是一条可解释的跳过记录。

关于协调者另外点名的两项：
- **xdist**：14 题 `eval_cmd` 全带 `-n0`，镜像虽装了 `xdist-3.6.1` 但被关闭；dask 各版本的 `addopts` 也没有 `-n auto`（与 mypy 的情况相反）。判为 `pass`（#R0）。
- **时间敏感 / 随机性**：`@pytest.mark.slow` 因未传 `--runslow` 全部跳过且不在参考集内；唯一的随机性来自 `dask__dask-7894` 的 F2P 用 `da.random.standard_normal` 且**不设种子**（该题 checks.11）。没有发现依赖 wall-clock 超时或 sleep 的参考用例。
- **网络（s3/http fsspec）**：14 题的参考测试文件里没有 `@pytest.mark.network`、没有真实 s3/http 端点、没有 `requests.get` / `boto3` / `torch.hub`；`"s3fs"` 只在 `dask/tests/test_base.py` 里作为字符串出现在模块名清单中。需要网络的只有**题面里的复现脚本**（6818 的 `s3://nyc-tlc/...` + distributed 集群、10972 的 s390x 机器），它们不进判分，但意味着 agent 无法在容器内复现这两题的题面现象（#R12）。
