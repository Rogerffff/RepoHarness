# P3 包报告：orange3 ×7、pandas ×7（R2E 环境审查第一轮，2026-09-24）

P3 sub-agent（B 线）。流程、判据与词汇见 [本轮 README](../../README.md)、[checks_r2e.md](../../checks_r2e.md)、[decisions.md](../../decisions.md)。共享文件（本轮 README、decisions、known_issues、dispositions、recipes）本包没有改，需要合并的内容在 §3。下文用 **建议 / 已决定 / 已实施 / 已验证** 标明状态；远端时间为 UTC（09-23 18:1x–19:2x，对应本机 09-24 凌晨）。

## 0. 摘要

- **已实施、已验证**：14/14 题探针十项最小条件满足；14/14 公开复现脚本在 base 上复现题面问题（`REPRO_RC=0`、`REPRO_OBSERVED=1`）；14 份 `screening_record.json`（R01–R20 全覆盖）+ `findings.md`；8 份材料修订提案。
- **关键发现**
  1. **pandas 7 题的期望 ERROR 键（共 58 个）全部是 fixture 不可达**：隐藏测试被恢复到 `/testbed/r2e_tests/`，pytest 不加载 `pandas/` 下的 conftest。不是缺可选依赖、网络或资源。原位跑 base 版公开测试时这些同名测试都 PASSED。其中 `4ec87eb9` 被掩盖的恰是题面场景的测试。
  2. **orange3 峰值内存不需要档位（已验证）**：R-f 记录的 orange3 峰值（1.2–2.6 GB；c3fb72ba / f5026689 为 2580 / 2632 MB）主体是 `chown -R /testbed` 触发 overlay copy-up 产生的**可回收页缓存**（file），测试本身的匿名内存只有 0.17–0.25 GB。把内存限额降到 2 GiB（低于记录峰值），chown 与测试照常完成、`oom=0`；真实 grader 在 2 GiB 下复跑两题 gold，都是 reward 1、键全一致。R12 用 `memory.peak` / 4 GiB > 60% 作判据，会把这种情况误报。
  3. orange3 `9b5494e2` 的 4 个期望 FAILED 是 scikit-learn 0.22.2.post1 与 SciPy 1.7.3 不兼容造成的依赖伪影；`f237f968` 的 1 ERROR + 2 FAILED 是上游测试自身的确定性伪影（辅助函数被收集、2022-02-02 定时提醒测试、依赖字体的像素阈值）。
  4. 题面 / 题意观察（不属环境资格，交后续筛查）：`22e98f8f` 题面把修复写成了 “Example Buggy Code”；`32dd55cb` 有一个目标键检查题面没提的 Period 报错文案；`87787609` 题面示例本身构造即报错；`f237f968` 题面示例用了不存在的 API。
- **未决**：12 题的 R13 等中央复跑并入（`22e98f8f`、`19c5eea5` 已有两次一致）；材料修订提案等用户决定。

## 1. 逐题表

处置列：“待 R13” = `state: unknown` + `state_if_r13_passes: environment_qualified`（除 R13 外全部满足）。证据列是缩写（`material_revisions/…` 相对本轮目录，`runs/…` 相对仓库根，iid 截断）；完整、可打开的路径在各题 `tasks/<iid>/screening_record.json` 的 `evidence_refs` 里，每题另有 `findings.md`。

| 题 | 分类 | 处置 | 关键 issue | 主要证据 |
| --- | --- | --- | --- | --- |
| orange3 `22e98f8f` | env_ok | environment_qualified | 题面泄漏修复（题目质量） | `docs/…/r2e_env_repair_20260924/tasks/orange3__22e98f8f…/findings.md` |
| orange3 `4014f248` | env_ok | 待 R13 | 无 | `runs/r2e_env_repair_20260924/p3/dev_probe/orange3__4014f248…/dev_probe.json` |
| orange3 `50f6a758` | env_ok | 待 R13 | 峰值 58%（同 §2.3 成因） | 同上目录 `orange3__50f6a758…/` |
| orange3 `9b5494e2` | material | 待 R13 | 4 FAILED = sklearn / SciPy 不兼容（提案 A） | `material_revisions/orange3__9b5494e2….md` |
| orange3 `c3fb72ba` | env_ok | 待 R13 | R12 自动 issue（63%）= chown 页缓存；2 GiB gold 复跑 reward 1（44/44） | `runs/r2e_env_repair_20260924/p3/memprobe/c3fb72ba_mem4g/summary.txt`、`runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl` |
| orange3 `f237f968` | env_ok | 待 R13 | 3 个非 PASSED 键 = 上游测试伪影（不提案） | R-f gold 日志 `…-o_fda27ddb.eval.log` |
| orange3 `f5026689` | env_ok | 待 R13 | R12 自动 issue（64%）= chown 页缓存；2 GiB 下 oom=0，gold 复跑 reward 1（8/8） | `runs/r2e_env_repair_20260924/p3/memprobe/f5026689_mem2g/summary.txt`、`runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl` |
| pandas `19c5eea5` | material | environment_qualified | 17 ERROR = fixture 不可达（提案 A）；9 个缺 SciPy 的 skip | `material_revisions/pandas__19c5eea5….md` |
| pandas `294cbc8d` | material | 待 R13 | 1 ERROR = fixture 不可达（A） | `runs/r2e_env_repair_20260924/p3/fixture_check/pandas__294cbc8d…/result.txt` |
| pandas `32dd55cb` | material | 待 R13 | 13 ERROR（A）；R16 目标键含题面未提的 Period 报错文案 | `material_revisions/pandas__32dd55cb….md` |
| pandas `4ec87eb9` | material | 待 R13 | 2 ERROR 掩盖了题面场景的两个测试（提案 B） | `material_revisions/pandas__4ec87eb9….md` |
| pandas `7dd34ea7` | material | 待 R13 | 4 ERROR（A） | `material_revisions/pandas__7dd34ea7….md` |
| pandas `87787609` | material | 待 R13 | 9 ERROR（A，占 26% 键）；题面示例有错 | `material_revisions/pandas__87787609….md` |
| pandas `f656217a` | material | 待 R13 | 12 ERROR（A） | `material_revisions/pandas__f656217a….md` |

“material” 在这里表示“有材料修订提案”，不表示环境不合格：8 道 material 题都是 gold=1、期望确定且与参考一致，环境层面支持解题与判分。

## 2. 族级发现

### 2.1 pandas：期望 ERROR 键 = fixture 不可达（7 题，已验证）

- gold 日志逐键看：58 个 ERROR 键全部是 setup 阶段 `E fixture '<名>' not found`，计数与每题 ERROR 键数逐一相等（例：`19c5eea5` 5+4+4+2+1+1=17）。缺的 fixture 都定义在 `pandas/conftest.py` 或 `pandas/tests/**/conftest.py`（`fixture_check/<iid>/result.txt` 第一段）。
- 机制：隐藏测试在 `/testbed/r2e_tests/test_*.py`，pytest 只加载 rootdir 到测试文件目录这条路径上的 conftest（`/testbed/conftest.py`、`/testbed/r2e_tests/conftest.py`，都不存在）。
- fixture 可达时（同一派生镜像、base 代码、仓库原位置跑公开测试文件）这些同名测试全部 PASSED；`4ec87eb9` 的两个是修复提交新增的测试，base 里没有。
- 后果：① 这些键对任何候选恒为 ERROR，没有回归信号；② 候选若新增 `/testbed/conftest.py` 让 fixture 可达，正确解也会因键翻成 PASSED 而得 0（`r2e_tests/` 下的 conftest 会被可信 setup 清掉，根目录的不会）；③ `4ec87eb9` 的题面例子（部分 NA → 2.5）没有任何运行中的键在检查。
- 另：`19c5eea5`（9 个）与 `32dd55cb`（1 个）有因 “Missing SciPy requirement” 被 skip 的测试，不在 expected 里；装上 SciPy 会多出期望之外的键（RH2 要求键集相等 → 0）。所以这两题的 expected 绑定“无 SciPy”。

### 2.2 orange3：期望非 PASSED 键

- `9b5494e2`（4 FAILED）：lbfgs 在 heart_disease 上未收敛时，scikit-learn 0.22.2.post1 的 `optimize.py:243` 对 SciPy 1.7.3 返回的 str 调 `.decode` → AttributeError；交叉验证留下未初始化预测值 → accuracy ValueError；两个 scorer 测试特征排序不符（推断同源，未单独验证）。参考 old / new 两次运行同样失败。目标测试 `test_auto_solver` 要求 l2 仍用 lbfgs，所以正确解都会走到这条不兼容路径——假阴性风险低，损失的是 4 个 P2P 信号。
- `f237f968`（1 ERROR + 2 FAILED）：`test_filename` 是 `from Orange.tests import test_filename` 引入的辅助函数被 pytest 收集（fixture 'path' not found）；`test_end_support_for_version_1` 在 2022-02-02 之后必然 fail；`test_minimum_size` 的 815 ≥ 800 px 取决于镜像字体与 `QT_QPA_PLATFORM=minimal`。都是确定性的，参考一致，不写提案；但换镜像 / 换 Qt 平台时 `test_minimum_size` 可能翻转。
- 未跟踪资产 `?? datasets`：7 题都是 install.sh 的 `check_orange` 在安装成功后建的软链 `datasets -> Orange/tests/datasets/`（目标是 24–25 个已跟踪数据文件），与修复无关。

### 2.3 内存：orange3 峰值的来源与档位结论（已验证）

**方法**：`runs/r2e_env_repair_20260924/p3/memprobe/memprobe.sh`——派生镜像起容器（资源、能力与探针相同），root 做与可信初始化相同的 `chown -R /testbed`，再以 agent 身份、入口前缀跑该题对应的仓库公开测试文件；宿主侧每 0.5 s 采样容器 cgroup 的 `memory.current` 与 `memory.stat`（anon / file / kernel），前后记 `memory.peak` 与 `memory.events`。之后用真实 grader 在 2 GiB 限额下复跑两题 gold（§2.3 末）。

| 运行 | /testbed | chown 秒 | chown 后 file / kernel / anon | 测试段 anon 峰值 | memory.peak | memory.events |
| --- | --- | --- | --- | --- | --- | --- |
| c3fb72ba，4 GiB | 2109 MB / 41,696 文件 | 217 | 3091 / 163 / 0.7 MB | 247 MB（43 passed） | 3527 MB | max 0、oom 0 |
| f5026689，4 GiB | 2181 MB / 41,377 文件 | 212 | 2430 / 164 / 0.7 MB | 173 MB（6 passed） | 2795 MB | max 0、oom 0 |
| f5026689，**2 GiB** | 同上 | 225 | 1902 / 144 / 0.1 MB | 175 MB（6 passed） | 2048 MB（顶到限额） | **max 2249、oom 0** |
| pandas 19c5eea5，4 GiB（对照） | 689 MB / 6,728 文件 | 37 | 684 / 38 / 0.1 MB | 192 MB（160 passed） | 926 MB | max 0、oom 0 |

（MB = MiB；chown 后三项取 `memory.stat` 快照。）

**结论**：
1. R-f 账本的 `mem_peak_mb` 读的是 `memory.peak`，其中绝大部分是 chown 在 overlay 上逐文件 copy-up 写出的页缓存（file，本包实测约为 /testbed 数据量的 1.0–1.5 倍）加约 150–170 MB 内核 slab；测试本身的匿名内存只有 0.17–0.25 GB。noop 与 gold 的峰值几乎相同（例：f5026689 2550 / 2632 MB），也说明峰值与候选和测试无关。
2. 页缓存可回收：2 GiB 限额下 cgroup 顶到上限 2249 次，内核回收页缓存，没有 OOM，chown 耗时基本不变（225 s 对 212 s），测试结果与 4 GiB 相同。
3. 不同运行测得的量差别不小：同一题 R-f grader 记录的峰值是 2580 / 2632 MB，memprobe 是 3527 / 2795 MB（c3fb72ba / f5026689），取决于宿主当时的页缓存与回写状态——`memory.peak` 本身不是稳定的资源需求量。
4. **建议**：不给 orange3 设仓库级内存档位；R12 改判据（见 §7）。`50f6a758`（58%）等同仓题同理。
5. **2 GiB 真实 grader 复跑（已验证）**：`runs/r2e_env_repair_20260924/p3/rerun_mem2g.sh`（systemd unit `r2e-p3-rerun-1908`，`MILES_RH2_RUN_ID=r2e-envrepair-p3-gold-mem2g`，`RH2_GRADER_MEMORY_BYTES=2147483648`，只跑 gold，一个进程两题顺序跑）。结果见 `runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl`：

   | 题 | reward | 键 | mem_peak_mb | 可信 setup | 测试 | 派生镜像 ID |
   | --- | --- | --- | --- | --- | --- | --- |
   | f5026689 | 1.0（resolved） | 8/8，无 missing / unexpected | 2048（顶到限额） | 185 s | 4.9 s | 与 R-f 同一 `sha256:e2381e00…` |
   | c3fb72ba | 1.0（resolved） | 44/44 | 2048（顶到限额） | 188 s | 8.2 s | 与 R-f 同一 `sha256:c12e2576…` |

   `final_status.exit_code=0`，评分容器全部清理。内存减半后 gold 仍达到来源定义，默认 4 GiB 至少有 2 倍余量——**不设档位**。本包只跑了 gold（2 次尝试，未超过 4 次上限）；noop 没有在 2 GiB 下复跑，因为问题只是“内存够不够”，noop 的峰值与 gold 相同（R-f 账本）。

### 2.4 解题侧条件（14 题共同 + 仓库差异）

- 共同：解释器 `/testbed/.venv/bin/python`（镜像 ENV 让 PATH 首项为 `.venv/bin`）；cwd 不限（`.pth` 路径项 `/testbed`，cwd=/tmp 也导入工作区包）；**pip 都有**（24.0 / 24.3.1，pip check 通过）但无网络；gcc、make 在；uv 不在；`/testbed`、site-packages、HOME、`/tmp` 可写，`/usr/local` 不可写。
- orange3：widget 相关测试与复现必须带入口同样的 `QT_QPA_PLATFORM=minimal … xvfb-run --auto-servernum` 前缀（xvfb-run 在 `/usr/bin`）；`Orange/tests/sql/*` 需要 postgres，整体 skip；rollout 初始化里 `chown -R /testbed` 实测 82–231 s（4 包并行、与中央复跑争 CPU）。
- pandas：工作区内编译（Cython 0.29.37、gcc、make 在；本包 gold 都只改 .py）；`pandas.__version__` 是 `0+untagged.<n>.g<sha>.dirty`；来源 install.sh 用 versioneer 重写了 `setup.cfg`、删了 `pyproject.toml`，pandas 自带的 pytest 配置不生效（跑公开测试的口径与上游 CI 不同）；工作区 5 个已跟踪改动是构建环境的一部分，不要 reset / stash（回退后果未测）。

### 2.5 题面 / 题意观察（交后续题目筛查，不影响环境资格）

| 题 | 观察 | 依据 |
| --- | --- | --- |
| orange3 `22e98f8f` | “Example Buggy Code” 的函数体逐行等于 gold 修复，按字面执行输出期望值 | 公开 prompt 与 `validation_bundles_v0.jsonl` |
| pandas `32dd55cb` | 目标键 `test_mean_datetimelike_numeric_only_false` 在 noop 下失败只因 Period 列 mean 的报错文案，题面没提 | R-f noop 日志 `…-p_75e948f0.eval.log` 第 215 行附近 |
| pandas `4ec87eb9` | 题面场景的测试被 ERROR 掩盖，F2P 只剩“整列全 NA” | §2.1 |
| pandas `87787609` | 题面示例 right 的 'y' 3 个值对 4 行索引，构造即 ValueError | 探针 REPRO_OUTPUT `LITERAL_RIGHT=ValueError …` |
| orange3 `f237f968` | 题面示例的 `set_context` / `send_data` 不是真实 API | base 源码 `Orange/widgets/data/owselectrows.py` |
| orange3 `9b5494e2` | `test_auto_solver` 要求 `solver="auto"` 参数值，题面只说“自动选择” | 私有测试代码（写脚本后读） |
| orange3 `50f6a758` | 题面的 TypeError 是测试读“没被调用的 mock”的 `call_args[0]` 产生的，产品行为是“不给警告” | 公开测试 `test_owcolor.py` 同类写法 |

## 3. 提案清单（供主会话合并，均为 **建议**）

**资源档位**
- 不设 orange3 仓库级内存档位（**已验证**：§2.3 的 memprobe 与 2 GiB gold 复跑，两题 reward 1、键全一致）。`known_issues.json` 的 `resource:orange3_memory_headroom` 建议改为 `not_an_issue`（或 `verified: no recipe needed`），证据指向 `runs/r2e_env_repair_20260924/p3/memprobe/` 与 `ledger_gold_mem2g.jsonl`。
- `recipes/task_resources_v1.json` 不需要新增条目。

**材料修订（T0，只提案）**
- pandas 族 7 题：`material_revisions/pandas__{19c5eea5,294cbc8d,32dd55cb,4ec87eb9,7dd34ea7,87787609,f656217a}….md`。推荐：6 题 **A 维持现状**；`4ec87eb9` 进入正式池前做 **B**（私有 conftest 补 fixture、生成 expected_v1），或在题目筛查里降级。若要强 P2P 信号，7 题一起做 B（同一机制、可脚本化）。
- orange3 `9b5494e2`：`material_revisions/orange3__9b5494e2….md`，推荐 **A**；以后统一重建 orange3 依赖时再做 B。
- 建议在 `known_issues.json` 新增族：`test_material:pandas_fixture_unreachable`（7 题，status proposed）；`dependency_artifact:orange3_9b5494e2_sklearn_scipy`（proposed）；把 `f237f968` 的三键记为 `upstream_test_artifacts`（not_an_issue）；`expected_non_passed_keys` 族里 P3 的 9 题都已归因。
- 建议在 decisions “待用户决定”加两行：pandas fixture 族（A / B / C）与 `4ec87eb9` 是否在进入正式池前做 B；`9b5494e2` 默认 A 可并入同一行。

**解题侧条件（E10，只进记录）**
- `solver_condition:no_pip_in_venv`：P3 14 题都**有** pip，不进该族。
- `solver_condition:import_requires_cwd_testbed`：P3 14 题都不需要 cwd=/testbed。
- orange3 的 xvfb 前缀、pandas 的“pytest 配置不生效 / 不要 reset 自带改动”写在各题 `solver_conditions`，是否进公开提示由任务面决定。

**dispositions.json**：本包没有需要隔离的题。

## 4. 未解决项

- R13：12 题等中央复跑（`/work/envrepair/_rerun2/`）并入；本包没有等它。
- 材料修订的用户决定（§3）。
- 题意观察（§2.5）没有展开核实影响面，交后续题目筛查。
- 探针的“公开测试”只取仓库第一个 `test_*.py`（orange3 是 1 个测试的 `Orange/tests/test__orange.py`，pandas 是 8 个测试的 `test_aggregation.py`），覆盖面弱；本包用 fixture_check（pandas 7 题的原位公开测试）与 memprobe（c3fb72ba / f5026689 / 19c5eea5 的对应公开测试）补了一部分，orange3 其余 5 题没有跑对应公开测试文件。

## 5. 远端产物与本地回传

远端 `/work/envrepair/p3/`，已全部回传到本地 `runs/r2e_env_repair_20260924/p3/`（`dev_probe/` 本地另用更新后的解析器 `--reparse` 重算过 `dev_probe.json`，原始 `agent_probe.log` 不变；远端那份仍是旧解析，**不要再用远端覆盖本地 `dev_probe/`**，需要时对本地重跑 `--reparse` 即可）。

| 路径 | 内容 |
| --- | --- |
| `repros/` | 本包 14 个复现脚本（与仓库 `repros/` 同 sha256） |
| `dev_probe/<iid>/`、`dev_probe/summary_{pandas,orange3}.json` | 探针输出（两批；`summary.json` 是最后一批的） |
| `logs/` | `probe_pandas.log`、`probe_orange3.log`、`fixture_check.log`、`hygiene_check.log`、`memprobe.log`、`rerun_gold_mem2g.log` |
| `fixture_check/` | `run.sh`、`inner.sh`、`<iid>/result.txt`、`orange3_9b5494e2_versions.txt` |
| `hygiene_check/` | `run.sh`、`images.txt`、`<iid>.txt`、`pandas_dirty_diffs.txt`（后者本地生成） |
| `memprobe/` | `memprobe.sh`、`run_all.sh`、`{c3fb72ba_mem4g,f5026689_mem4g,f5026689_mem2g,pandas19c5_mem4g}/`（summary、samples.tsv、chown.log、public_test.log） |
| `rerun_mem2g.sh`、`ledger_gold_mem2g.jsonl`、`eval_logs/`、`artifacts/` | 2 GiB gold 复跑 |

残留检查（远端 09-23 19:25 UTC）：`docker ps -a` 里没有本包起的容器（`rh2-p3-*`、本包 14 题的 `rh2-devprobe-*`、`r2e-envrepair-p3` 的评分 / 候选容器都已删除；当时在跑的 `rh2-grading-replay-r2e-envrepair-rer-*` 属中央复跑）；没有遗留的 `r2e-p3-*` systemd unit；`df -h /` 可用 45 GB（开工时 45–46 GB）。

## 6. 耗时（远端 UTC，4 包并行 + 中央复跑，不作校准）

- pandas 探针 18:25–18:32（7 题，52–65 s/题，其中 chown 36–47 s）。
- orange3 探针 18:32–18:55（7 题，103–255 s/题，其中 chown 82–231 s）。
- fixture_check 约 40 s；hygiene_check 约 1.5 min；memprobe 18:55–19:08（4 次，orange3 每次约 4 min，其中 chown 212–225 s）；2 GiB gold 复跑 19:08–19:22（2 次尝试，各约 7 min：候选段与评分段各做一次 chown，且与中央复跑的同题容器同时在跑）。
- 预检（写复现脚本前看 base 源码、以 root 在一次性容器里试跑 3 个 widget 复现）约 5 min。

## 7. 对流程 / 工具的改进建议

1. **R12 判据**：`memory.peak` 包含可回收页缓存；对 /testbed 大、需要 `chown -R` 的镜像（orange3 约 2.1 GB / 4.1 万文件），60% 阈值会误报。建议 grader 在读 `memory.peak` 的同时记 `memory.stat` 的 anon / file / kernel 与 `memory.events`（max / oom / oom_kill），R12 用“anon 峰值占比”或“有无 oom 事件”判定；需要时再用降限额复跑确认。
2. **rollout / grader 初始化成本**：orange3 每次容器都要 `chown -R /testbed`（2–4 分钟、约 2–3 GB 页缓存与同量可写层）。可考虑在派生配方里预先改好属主以免每次 copy-up——但 grader 用 uid 54322、rollout 用 54321，要先定统一方案；属 A 线 / 配方版本问题，这里只提出。
3. **探针的公开测试选择**：取第一个 `test_*.py` 太弱。建议优先跑“隐藏测试在仓库里的对应文件”（来源记录 `modified_files` 里的测试路径，或按隐藏测试类名在公开树里定位），这样还能顺带暴露 fixture / conftest 依赖（pandas 这次就是靠原位跑才看清的）。
4. **汇总器的 `non_passed_reasons`**：现在只有 `-rA` 摘要里的状态词（多数只是 “ERROR” / “FAILED”），原因要人工去 ERRORS / FAILURES 段找。建议从这两段抽每键第一条 `E   …` 行（如 `fixture 'float_frame' not found`），能自动归出“fixture 不可达”“AttributeError …decode”这类族。
5. **探针 `summary.json` 会被下一批覆盖**：同一 `--out-dir` 分批跑时建议按时间戳或批次命名，或追加写。本包手工复制成了 `summary_{pandas,orange3}.json`。
6. **WHICH_* 键丢失**：远端冻结快照里的解析器正则丢掉 `WHICH_gcc` 等键（P1 已报，主会话已改并加 `--reparse`）；远端 `/work/code` 没同步新版本，本包是本地 `--reparse` 补的。
7. **流程文字**：派发说明写 pandas “dirty tree 6 行”，实际是 7 行（5 个已跟踪改动 + 2 个未跟踪脚本）；不影响结论。

## 8. 先后说明（E06）与越界自查

- 复现脚本只据公开 prompt 与**公开工作区的 base 源码**写成（为了用对真实 API，在一次性容器里只读看了 `owcreateclass.py`、`owcolor.py` + 公开 `test_owcolor.py`、`owlinearprojection.py` + 公开测试、`owselectrows.py` + 公开 `test_owselectrows.py`、`owdatasets.py`、`logistic_regression.py`、`discretize.py`；没有读 `/rh2_private`）。例外：`c3fb72ba` 写脚本前已读过它的 `facts.json`（含目标键名与 gold 触碰路径，不含 diff）。写完脚本、推上远端之后才读 gold 补丁、私有测试代码（`s2_r2e/raw` 的 `execution_result_content`）与期望映射。
- 写正式探针前，以 root 在一次性容器里试跑了 3 个 widget 复现（`50f6a758`、`c3fb72ba`、`f237f968`），只为检查脚本本身；正式结论只取探针结果。
- 额外起过的容器都是一次性的（`--rm` 或脚本末尾 `docker rm -f`）：`rh2-p3-src-*`、`rh2-p3-pretest-*`、`rh2-p3-fix-*`、`rh2-p3-hyg-*`、`rh2-p3-hyg2-*`、`rh2-p3-mem-*`；复跑容器由 replay_grade 自己清理。没有改 `/work/replay`、`/work/r2e_derived`、`/work/code`，没有构建或删除镜像，没有动中央复跑。
