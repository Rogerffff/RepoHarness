# Dask 线程预算适用范围独立窄核（2026-10-03）

结论：不能因三题都使用 Dask，就认定它们重现7305的默认多进程池与原生库线程叠加。7138、9378的固定模块可达默认 **threaded** 调度器，但常用 `assert_eq` 明确同步执行；未发现两模块或其仓库测试配置创建默认 processes 池。8801是配置测试，仅有一次串行子进程导入诊断；新增 `DASK_NUM_WORKERS` 与其读取 ambient 环境的严格断言不相容，应在无具体需求时避免加入。以上是固定版本的静态路径判断，没有运行三题，也没有新增分数或训练资格。

## 版本与证据绑定

| 题目 | base commit | revision | 固定模块 / 参考数 |
| --- | --- | --- | --- |
| 7138 | `9bb586a6b8fac1983b7cea3ab399719f93dbbb29` | `dask7138-array-keyword-v1` | `dask/array/tests/test_routines.py` / 470 |
| 9378 | `8b95f983c232c1bd628e9cba0695d3ef229d290b` | `dask9378-mask-route-b-v1` | `dask/array/tests/test_masked.py` / 137 |
| 8801 | `9634da11a5a6e5eb64cf941d2088aabffe504adb` | `dask8801-behavior-semantic-v7-compat1` | `dask/tests/test_config.py` / 45 |

固定命令分别为 `pytest -n0 -rA  --color=no dask/array/tests/test_routines.py`、`pytest -n0 -rA  --color=no dask/array/tests/test_masked.py`、`pytest -n0 -rA  --color=no dask/tests/test_config.py`；`-n0` 不启用 pytest 分布式 worker，但不限制源码内部线程或子进程。参考数取各CPU noop ledger的固定参考分区并集：7138为1 original_f2p + 468 original_p2p + 1 added_p2p；9378为3 + 134；8801为2 + 41 + 2。这些数是参考范围，不是本次测试结果。

对各题 `base_identity.json`、`revision.json` 与 CPU baseline manifest 的 head/base commit 做了相等核对。报告引用的 root `conftest.py`、system/threaded/config、原测试模块及两题 array core/utils 字节SHA，均与CPU manifest的 regular成员一致。各导出base的递归 `conftest.py` 清点只有根文件。完整文件清单、SHA与精确行范围见[JSON证据索引](non_author_dask_thread_budget_applicability_review_20261003.json)；没有将实际actor worktree未知的静态导出当成当前运行工作区。

三个 `dask/system.py` SHA均为 `fb9ff8c2f9d6dcdafc3c764c089103d08e313f91443c86bfcb3c87f51e808b95`：L22/L27读取 `os.cpu_count()`/affinity，L36–48只尝试cgroup v1 `cpu.cfs_quota_us`/`cpu.cfs_period_us`，L53缓存 `CPU_COUNT`。它们不读取cgroup v2 `cpu.max`；因此CPU quota=2不能单独证明可见CPU或默认池为2。**三题现场的可见CPU、native backend、线程env与pids事件尚未独立读取。** 三份历史CPU ledger均 `resource_facts=null`，不能据历史CPU通过记录推断当前GPU并发事实。

## 逐题适用性

### 7138：默认线程池可达，无同一多进程机制证据

`base/dask/array/core.py` L1174指定 `threaded.get`。`base/dask/threaded.py` L59读取 `num_workers` 配置；L64–72在没有显式池/worker预算时可创建 `ThreadPool(CPU_COUNT)`。`base/dask/array/utils.py` L223–261中，普通 `assert_eq` 最终通过L234的 `compute(scheduler="sync")` 执行，不以默认线程池运行。

有效 `test_routines.py` 有未指定 scheduler 的直接 `.compute()`：L179、183、545、555、696、1191、1392、1407、1420、1434、1454、1554、1910。这些调用在无外部scheduler覆盖时可走默认线程池。整个固定模块及根 `conftest.py`（完整L1–36）未发现显式 processes、进程池、cluster、子进程或自动生效的进程fixture；根配置只做可选库导入及slow项选择。不能将“线程池可达”改写成“已观察到24 spawn × OpenBLAS”，也不能因此暂停本题。默认worker/native线程的实际放大程度待现场事实。

### 9378：同样可达默认线程池，保持在途原配置

`base/dask/array/core.py` L91/L1416将默认Array scheduler设为threads（threads不可用时退回sync）；`base/dask/threaded.py` L70/L75–83可创建 `ThreadPoolExecutor(CPU_COUNT)`。`base/dask/array/utils.py` L293的 `assert_eq` 默认 `scheduler="sync"`，L310/L318传入计算helper，L263–264继续使用该参数。因此普通 `assert_eq` 不证明默认线程池已执行。

有效 `test_masked.py` L46、48、95、163、229、400有默认 `.compute()`；特别是自定义 `assert_eq_ma` L228–238先在L229直接compute，再调用普通assert_eq，不能把整个helper都称为sync。固定模块及根 `conftest.py` 未发现显式 processes/进程池/cluster/子进程；根conftest L67–70的 `shuffle_method` 不是autouse，也没有在本模块被请求。源码中 `threaded.py` L86–87可适配外部提供的multiprocessing Pool，但本模块未提供它；仅有适配分支不等于本次可达进程扇出。

在途9378不热改环境、不套7305线程恢复方案。准备阶段耗时或超时本身不能证明进入测试线程/BLAS路径；若需重跑，准备故障与测试资源事实应分别记录。本审查未独立核在途现场，既不把它判为7305同因，也不声称无其他资源风险。

### 8801：串行导入子进程，新增DASK变量会触碰既有测试边界

有效 `test_config.py` L339–343把ambient环境传给一次串行 `subprocess.run([sys.executable, "-c", IMPORT_CAPTURE_PROGRAM], ...)`，用于损坏配置的import诊断；固定模块没有Dask `.compute()`、processes调度器、进程池或cluster创建。根conftest L23/L28/L33可导入NumPy/Pandas/SciPy，因此单进程加载原生库仍可能产生线程；这不等同于默认Dask多进程池扇出，也未证明本题实际native backend。

具体边界：有效测试L399–402的 `test_collect_env_none` 只设置 `DASK_FOO=bar`，随后 `collect([])` 严格等于 `{"foo": "bar"}`。base `dask/config.py` L206–223读取 `os.environ` 中所有 `DASK_*` 并解析数值，L433–438将env配置合入collect结果。若 `DASK_NUM_WORKERS=2` 到达此路径，结果会增加 `num_workers: 2` 键，与现有严格断言不相容；BLAS/OMP/MKL/NumExpr四键不满足 `DASK_` 前缀，不通过此收集路径。

这里的root `conftest.py` 确实存在，完整L1–70无清理ambient `DASK_*` 的autouse fixture或setup；SHA `7377b1eb6821ad93b02e541153547e32ae24641a0dff8477682730d9e0460d8b` 与8801 CPU v2 noop baseline manifest entry完全一致。有效测试也未定义此类fixture/setup。**这足以证明已核源码中的环境冲突，但没有证明实际运行必然失败：外部pytest插件、启动脚本是否清理环境、真实候选是否改相关路径未独立核实，也未执行本测试。** 无具体资源需求时8801不增加 `DASK_NUM_WORKERS`，不把7305的统一五键方案机械套入配置题。

## 建议与验收上界

对未来新的7138/9378 array运行，可考虑在进程首次导入库前设置 `DASK_NUM_WORKERS=2` 及 `OPENBLAS_NUM_THREADS=1`、`OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1`、`NUMEXPR_NUM_THREADS=1`，作为一致的防守性并发预算。其Dask env解析路径分别为7138 config L171–205/L396–402/L647和9378 L206–239/L449–455/L718，threaded实际消费见上文。该建议保留默认threads及显式sync语义，不用scheduler切换掩盖问题；它是**建议，非三题均有必要修复的已证结论**，更不是在途变更决定。四个native键的实际适用库待现场核实。

7305现场已读到24 spawn及映射的OpenBLAS库；这份证据的SHA为 `f85a3fbb41df8bc200e2ada0e94b1b5824001cc7a6efbb96bb63681d31b2e7d5`，仅约束7305对应容器。其恢复建议/最小验收保留在[7305独立预算审查](non_author_7305_grader_thread_budget_review_20261003.md)，不扩大到本三题。若为新的array运行采纳预算，最小记录应绑定原FP/固定命令、上述参考全集（470/137）、清理结果，并观察所需非敏感CPU/affinity/Dask worker/native env事实以及独占运行的 `pids.events max` 增量；不能用自测总数代替参考归属，不必重跑17矩阵。8801继续以原固定45参考及原环境边界验收，不新增processes压力项。

本审查没有SSH/Docker/实验、候选导入执行或新评分；仅新增本对报告，不改旧报告、源代码、在途进程或历史产物。未见直接进程调用只限定这些固定模块与已核仓库fixture，不能保证未来候选、间接依赖、外部pytest插件或用户配置永不创建进程。正式评分仍需另行完成，静态环境建议不授训练资格。
