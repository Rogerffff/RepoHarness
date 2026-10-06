# Dask7305 评分线程预算：非作者恢复方案窄核

2026-10-03，16:37 SGT。**支持在一个新的评分运行中设置默认 Dask worker=2、数值库线程请求=1，作为当前 PID 预算问题的最小恢复方案；尚未证明恢复成功或产生新评分。** 当前2 CPU是时间配额，实测可见CPU、affinity和旧Dask的 `CPU_COUNT` 均为24；现场24个spawn与数值库线程叠加，已经触发 `pids.max=512`。必须保留processes与threads测试，不能通过改成同步执行或skip消除问题。

本报告只读固定现场回执、原174件包中的安全regular源码成员和历史CPU v2的noop/gold_full_auto ledger/log；没有SSH、Docker、候选导入/执行、CPU/GPU作业或在途修改。只新增本文与同名JSON，原候选审查及原评分均未修改。结论是环境恢复建议及验收范围，不授训练资格。

## 现场已经证明什么

[08:27现场回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/dask7305_setup900_live_stall_0827_v1.json) SHA为 `7349bb2dbbc0c956d8014ab8a4c13b21d9670c8d9b9cd2b32a5b9c0ecee2bf46`，9214字节。容器实际inspect字段为 `NanoCpus=2000000000 / Memory=4294967296 / PidsLimit=512`（:5–9）；cgroup记录 `pids.current=500 / peak=512 / max=512 / events.max=1`，`oom=0 / oom_kill=0`（:12–18）。:21的进程表包含pytest、resource_tracker和24个spawn子进程。这个快照证明PID限制曾被命中，不能把它说成OOM；也不能仅从pool规模猜可见CPU数量。

[08:35追加运行时回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/dask7305_thread_runtime_readback_0835_v2.json) SHA为 `f85a3fbb41df8bc200e2ada0e94b1b5824001cc7a6efbb96bb63681d31b2e7d5`，9791字节。两份回执的container ID与镜像config ID一致（:3–4）。它进一步记录：

- `cpu.max="200000 100000"`，即每100000微秒周期最多200000微秒CPU时间；`pids.events.max=1`、OOM相关计数仍0（:10–15）。这不是限制进程只能看到两个CPU的cpuset。
- 只读probe的stdout实测 `os_cpu_count=24 / affinity_count=24 / dask_CPU_COUNT=24 / num_workers=null`（:237–240）。字段名与GPU描述将该probe归于candidate UID；stdout没有新增 `id -u`，本报告不将其包装成独立UID实测证明。
- 26个Python进程的 `threads` 合计495；其中parent pytest为39（:19–21），resource_tracker为1（:28–30），24个spawn合计455：5个32线程、12个24线程、7个1线程。逐项可从 `python_processes` 复算，和cgroup.current=500相符；不同字段不是原子同时采样，不能据差5证明完整瞬时账目守恒。
- parent及17个spawn实际maps含 `libopenblasp-r0.3.25.so`，共18个Python进程（如:23–25、:35–41、:44–50）。因此OpenBLAS已从“可能backend”提升为现场实际加载的库；32或24是整个进程线程数，不是每条线程的OpenBLAS归属trace。
- 各 `allowed_thread_env` 均为 `{}`（如:22、:38、:47）。这只表示此次**选定线程变量白名单**未发现值，不表示整个进程环境为空，也不证明所有可能控制变量都不存在。该JSON未枚举白名单键名；新运行须显式保存拟设五个变量的键和值，避免扩大缺证结论。

这些事实足以支持“旧Dask默认池与实际OpenBLAS等数值线程并发叠加，使当前512 task/PID预算被命中”的恢复方向。它们没有追踪每线程库归属、失败的那一次clone/pthread调用或具体测试栈；不能声称OpenBLAS是唯一充分原因，或五个env设置必然消除所有停滞。

## 旧Dask为何不会自动变成两个worker

原 `baseline.tar` SHA为 `04c1663b90bbf92af12e50c2cb1e22c935686136388312c1953ea054890d6d6b`。本次只read已确认regular、非绝对、无 `..` 的成员，没有解压；成员内容SHA保存在同名JSON。以下行号属于该tar成员正文：

| 源码 | 实际路径与含义 |
| --- | --- |
| `dask/system.py`:22–29、33–48、53 | 先取 `os.cpu_count` 并取affinity最小值，只读 `/sys/fs/cgroup/{cpuacct,cpu\|cpu,cpuacct}/cpu.cfs_quota_us` 与 `cpu.cfs_period_us`。没有读取cgroup v2 `cpu.max`，失败异常被忽略，最后把结果缓存为 `CPU_COUNT`。现场probe实测24，与这个缺口一致。 |
| `dask/config.py`:171–205、399–402、647；:40–60、355 | 启动时读取DASK前缀环境；`DASK_NUM_WORKERS=2`变成 `num_workers`，通过 `ast.literal_eval`得到整数2。underscore/hyphen键名按canonical_name归一，所以当前scheduler的 `config.get("num_workers")`能取到它。 |
| `dask/multiprocessing.py`:141–152、184–198、220–234 | 默认保持spawn；worker优先级为显式参数、config、CPU_COUNT，未传pool时调用 `context.Pool(num_workers)`。设env后默认池可静态推导为2；实际传入已有pool时 `get_async`仍用 `len(pool._pool)`，不会强行改该pool。 |
| `dask/threaded.py`:58–74、76–84 | 同样先取config。为2时进入 `ThreadPool(2)`而非 `ThreadPool(CPU_COUNT)`；仍是线程调度与并发执行，未改成同步scheduler。 |
| `dask/dataframe/tests/test_shuffle.py`:265–279、292–318 | 原测试显式选择threads/processes、tasks/disk，并执行processes清理与异常传播。调整默认worker数量没有删除这些scheduler分支，也没有改其断言。 |

保留processes=2和threads=2，可以保留多进程/多线程路径、spawn、序列化与清理行为；它减少并发基数，因此不证明所有24-worker交错仍被覆盖。当前测试没有要求默认worker必须等于24；这里只调整运行预算，不改变候选、oracle、参考集或测试marker。

## 新运行的最小设置与库证据限度

在**新的安装/pytest进程启动之前**设置，并让spawn子进程继承：

```text
DASK_NUM_WORKERS=2
OPENBLAS_NUM_THREADS=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

不要仅在已导入Dask/NumPy的在途进程里改env；Dask config与数值库可能已初始化。设置应归于新评分运行的环境配置，留新脚本/运行身份、env键值及原FP绑定；当前镜像、测试和候选材料不因此重写。保持既定CPU/内存/PID资源策略，不通过提高 `pids.max` 掩盖此次默认并发问题。

`DASK_NUM_WORKERS`的生产消费者已由上表源码确认。OpenBLAS实际加载已有maps证据，`OPENBLAS_NUM_THREADS=1`与该现场库直接相关。`OMP_NUM_THREADS`、`MKL_NUM_THREADS`、`NUMEXPR_NUM_THREADS`是对可能叠加的相应数值线程运行时的预设预算；当前现场没有OpenMP/MKL/NumExpr实际线程池或逐库线程数的证据。已有pip冻结只表明NumPy、pandas、NumExpr等包存在，不证明MKL不存在或NumExpr已创建池。因此后三项可随新运行统一设置，但不能声称已实测需要它们、已验证每库线程=1，或把总线程数直接除为某库池规模。

## 显式八池：保留原语义，额外检查可选

baseline `test_shuffle.py`:434–439明确调用 `mp.get_context("spawn").Pool(processes=8)`，执行100次 `set_index` 的divisions一致性检查。`DASK_NUM_WORKERS=2`**不能限制该显式8个子进程**；它只能限制这些子进程内部使用的Dask默认池。数值库线程env仍须在这些spawn子进程启动前继承，以免8池再叠加各自数值线程。

该测试在:424被标为slow，原 `conftest.py`:30–36要求 `--runslow`，否则跳过。当前正式命令没有该选项，故这一项不是当前105正式参考的新增必过条件。**最小恢复验收无需执行八池；如另做额外环境检查，必须单独加 `--runslow` 并确认该node实际通过而非skip**：

```text
pytest -n0 -rA --color=no --runslow dask/dataframe/tests/test_shuffle.py::test_set_index_consistent_divisions
```

它的结果另记，不改正式105参考分母，也不能把原模块说成全无skip。

## 历史CPU完成不能证明本次线程预算已验证

本次读取并核对历史CPU v2两份ledger与其所引日志SHA；JSONL均为第1行：

| 历史对象 | 原日志与资源证据 |
| --- | --- |
| noop | ledger SHA `65d269be…7dc84`；log SHA `6669caea…e6ff`。log:1621–1626记录threads/processes四种rearrange及processes清理/异常测试通过；:1699保留3个slow skip；:1701为1 failed/104 passed/3 skipped/2 warnings。 |
| gold_full_auto | ledger SHA `0ad635d2…82075`；log SHA `3ecab158…f819`。log:1642–1647记录对应调度和清理测试通过；:1721保留3个slow skip；:1722为105 passed/3 skipped/2 warnings。 |

两ledger的policy均写cpus=2、memory=4GiB、pids_limit=512，但 `resource_facts=null`；没有本次需要的实际visible CPU、affinity、worker、native线程env或 `pids.events` 原件。noop的peak_memory=4096MiB也不能据此断言当时OOM；gold的3114.652MiB同样不是PID预算证明。两者cleanup.removed=true与测试完成可照实使用；不能从policy和历史通过反推其池实际为2、native线程已为1，或本次恢复可直接判PASS。历史slow八池未执行的范围保持不变。

## 最小必要验收与停止条件

先用同来源、同resource policy、新env，在受信评分路径定向运行原 `test_rearrange[processes-tasks]` 与 `[processes-disk]`；二者须真正进入spawn多进程路径并正常结束。无需改scheduler或测试。此项只验证恢复的并发入口，不代替正式结果。

随后评分**同一个原FrozenPatch** `5e64758cd92207d53d5ed93525a9f02d4e4e067a197a066b14e836a8974959e2`，保持当前v3材料及原命令：

```text
pytest -n0 -rA  --color=no dask/dataframe/tests/test_shuffle.py
```

新原件必须保留：实际env五键及Dask默认worker=2的消费证据、同FP/材料/镜像绑定、定向processes实际结果、正式105参考逐状态、模块3个原slow skip及warnings、真实候选失败和首次断言位置、执行时间和完整清理。**要求正式测试完整可判分，不要求候选105项全部通过**；候选可能真实失败，这是有效模型结果，不能伪装成env失败或改写旧评分。auto若被前面的F断言提前阻止，按真实执行范围报告。

对新的独立cgroup记录测试前后的 `pids.events`，验收 `max=0`（至少增量为0；fresh容器初值也须记录），同时记录pids峰值、OOM计数和运行后清理；只有env字面值或单个瞬时pids.current不足以证明预算有效。完整模块保留threads和processes原参数组，不重新跑17行控制矩阵。额外八池 `--runslow` 可选，独立留结果。

本轮窄核停止条件已满足：静态Dask配置消费链闭合，现场CPU/PID/native库证据与历史缺证已分开，最小恢复设置与必要/可选验收边界明确。原300秒infra报告仍原样；setup900现场仅证实pytest在运行并受PID限制，不能认定其最终补分已成功。本审查没有新分数，不授训练资格。
