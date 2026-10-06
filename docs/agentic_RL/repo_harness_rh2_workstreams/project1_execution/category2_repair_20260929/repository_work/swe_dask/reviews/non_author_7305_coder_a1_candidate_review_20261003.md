# Dask7305 首次真实 Coder 候选：非作者语义与验证窄核

整理：2026-10-03，16:12 SGT。对象仅为 `gpu1003-dask7305-coder-a1#p1`、原 FrozenPatch `5e64758c…4959e2`。结论：**修法只解决了已打印的单输出分区样例；最终候选仍有具体的大整数端点缺口。原正式评分没有执行安装或测试，保持 `infra_failure / reward=null`，不能记为模型 0，也不能认定 105 项通过。** 已有授权的原 FrozenPatch 重评分可以继续；本审查没有新增审批或训练准入。

我是非作者审查者；已读取私有评分材料和既有报告，不属于公开盲审。只做本机原件读取、SHA/大小重算、JSON/文本分析与内存中补丁绑定核对；没有 SSH、Docker、CPU/GPU 作业，没有导入、编译或执行候选，没有修改共享源码、历史证据或其它 chat。新增文件仅为本文及同名 JSON，采用只写一次方式。

## 对象与证据边界

- [闭合运输清单](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-dask7305-coder-a1_closed_manifest_v1.json) SHA 为 `1309a326fd4b94231c050a26c4659646286fa7a8f44e59d3b430e908dfd383a6`；174 文件、21,304,813 字节，全部实读大小/SHA 匹配。清单成员从 `runs/ordinary_gpu_probe_20261002/remote/<相对路径>` 读取，未把其它在途输出混入本样本。
- [FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-dask7305-coder-a1/attempt/frozen/frozen_patch.json) 文件字节 SHA 为 `aed0ad51…995844`；规范 JSON SHA 为 `5e64758cd92207d53d5ed93525a9f02d4e4e067a197a066b14e836a8974959e2`。两种摘要不能互换。15 条 regular entry 的内容摘要均匹配；[候选 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-dask7305-coder-a1/attempt/candidate/dask__dask-7305.diff) 在内存逐 hunk 应用到 baseline 后，15 路径逐字节等于 FrozenPatch，没有落盘或执行。
- `baseline.tar` SHA 为 `04c1663b…d6d6b`。只读取已确认 regular、非绝对、无 `..` 的成员正文；没有解压或执行。源码行号以下分别注明来自 FP entry 或 baseline tar member，不能误认为本工作区存在一份已运行候选源码。
- [真实首请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v21/coder/gateway/gpu1003-dask7305-coder-a1/requests.jsonl) 第 1 行，`body.model=Qwen3-Coder-30B-A3B-Instruct`；首个 user message 的 `content[1].text` 与 [actual prompt](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-dask7305-coder-a1/attempt/prompt.txt) 2721 字节完全相同，SHA `17fa4f73…bc752`。另一文本块是日期 reminder。题目块明确要求正确 min/max（prompt:6–10），并说明乱序输入、最小值靠后时 `set_index` 把该行留在末分区（prompt:37–57）；它没有要求特定内部量化值。
- [轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-dask7305-coder-a1/attempt/trajectory.jsonl) 有 672 行，末行记录 harness `success/completed`、59 turns。这是一个候选的工具交互完成状态，59 turns 不是 59 个样本，也不表示修复正确。

## 最终修法实际覆盖到哪里

唯一被修改的既有生产文件是 `dask/dataframe/partitionquantiles.py`，另新增 14 个根目录诊断脚本。最终 `percentiles_summary` 检测超出 `2**53-1` 的 signed/unsigned integer，直接取 `np.min/np.max`，以原 dtype 创建全为局部 min 的数组，仅将最后一项置为 max，再提前返回摘要（FP source:419–441；candidate diff:91–125）。它确实避免了这一步 `_percentile` 的 float 运算，也消除了中间数组未初始化的问题。

最终轨迹:606 对题面两数、1 输入/1 输出，打印精确首尾 `612509347682975743 / 616762138058293247`；对近 uint64 最大值的三数、1 输入/1 输出，打印精确首尾 `18446744073709551613 / 18446744073709551615`。这是这两个样例的实际观察，不能推广成多分区、auto 或正式参考通过。

旧路径对小整数和非整数保留 `_percentile` 与原 round/cast（FP source:443–448），空输入仍在 source:407–408 返回。trajectory:628 的五组脚本打印 min 相等，涵盖题面、极大 uint64、跨 `2**53-1` 的正 int64、小整数和浮点；其中比较本身没有 assert，正 int64 也只核一个最小值。trajectory:650 的负数仅为 `[-1000,-500,0,500,1000]`，没有验证大负整数。没有任何 helper 调用 `set_index`。这些有限观察不足以证明“全部既有功能或向后兼容”。题面附加的 `.min().compute()` dtype 疑问也没有在候选中修复；trajectory:606 仍打印题面 actual min 的类型为 `numpy.int64`。它不应被包装成已解决的新目标。

## 具体缺口与待评分项

### R1：最后补插值再次损失精确端点，已有最终候选的实际反例

**当前行为。** 最终摘要只保留各输入分区的 min/max；压缩后唯一摘要值不足 `npartitions+1` 时，未改动的 `process_val_weights` 仍走 `np.interp`，最后才 cast 回原 dtype（FP source:319–343、381–383）。局部摘要的精确值没有保证最终端点精确。

**证据。** 最终 edit 在 trajectory:593，成功在 :597；随后 :646 执行最终 `test_edge_cases.py`，:650 打印 2 输入/2 输出的结果：`[612509347682975744, 614635742870634496, 616762138058293248]`。该 helper 输入的真实 min/max 是 `612509347682975743 / 616762138058293247`（FP helper `test_edge_cases.py`:10–15；candidate diff:800–810），首尾均偏大 1。这是实际生产入口 `partition_quantiles(...).compute()` 的打印观察，不是本审查新运行，也不是 pytest 的断言失败。

**违反的不变量与影响。** 公开要求正确 min/max；内部近似不能使首尾也偏移。[effective test](../tasks/dask__dask-7305/effective_test.patch):20–25 使用 Python int 核精确端点及排序。其 :69 的题面两数、1 输入/3 输出也会使最终两唯一摘要值进入补插值分支；从源码可预期端点错误，但本样本正式测试未运行，不能填写实际 F2P 失败数或首个失败行。

**建议分期与验收。** 这是候选语义缺口，进入“修法已通过”或训练资格前必须处理；原 FP 重评分仍应完整保留此观察，不用修订候选替代原样本。已存在的最小探针是 trajectory:646 的 `python test_edge_cases.py`，本审查未重跑。后续验收应按冻结 v3 真正执行题面 1/3 及其它显式分区组，确认 Python-int 首尾精确、分界非降与每行归属；不能仅加一条浮点/NumPy 的“相等”打印。可达性标签：`production_observed`，仅限上述实际多分区调用；正式模块结果仍待评分。

### R2：auto 的 float 插值和行归属没有被修复或验证

**当前行为与调用链。** FP 没有修改 `dask/dataframe/shuffle.py`。baseline tar member 的 `set_index` 对 `auto` 先使用 `max(100,df.npartitions)` 量化（shuffle:474–489），再根据体积缩减输出数量，直接以 `np.interp(...,fp=divisions).tolist()` 重取分界（:499–510）。随后 `set_partition` 按 index dtype 构造分界（:604–624），`set_partitions_pre` 用 `searchsorted(...)-1` 分配行（:1090–1093）。本候选既未关闭摘要末端的 float 路径，也未关闭这个 auto 路径。

**公开依据与影响。** 最小值不能小于首分界，全部行必须落在自身区间；这正是 prompt:37 的现象。v3 的 auto 实例为 1000 个乱序大 uint64、最小值置末尾、4 输入分区（effective_test.patch:78–83）；auto 只传给 `set_index`，没有传给只接受整数分区数的 `partition_quantiles`。其 :29–39 核精确两端、每个分区范围及全部行保留，并不钉 auto 的输出分区数或内部值。

**证据强度与分期。** 这是源码可达的未修复路径（`production_reachable`），不是本样本已经执行的 auto 失败。14 个 helper 均无 `set_index` 调用，轨迹没有 auto 实测；正式 F2P 若在早先显式分区断言失败，也不会运行到该 auto 分支。后续必须在受信评分中记录是否实际到达 :83、首次失败断言和行归属；本审查不编造 auto 的实际测试结果或 reward。修法验收条件仍是冻结 v3 的 Python-int 端点、逐分区范围与行量守恒。

### 其它明确保留的限制

- FP source:436 把所有内部百分位数都填成 min，丢掉了大整数的内部样本分布。例如 `[0,50,100]` 的三个请求被返回为 `[min,min,max]`，经 source:261–263、282–285 合并，原中间权重也累到 min。这会改变近似质量和分区负载；**当前测试允许近似内部分界，不按它与 gold 不同就判错**，本次没有性能实测，不额外创造评分要求。
- `process_val_weights` source:320 从 Python 列表重建 `np.array` 时没有指定原 dtype；跨 `2**63` 的 uint64 组是冻结范围（effective_test.patch:72）。本次没有执行该组，不承诺 dtype/端点/排序已通过；正式评分须保留真实结果，不用历史控制标签替代。
- 104P 包括现有的小整数、浮点、categorical、空分区、shuffle 等行为。本候选的窄 min 打印没有执行这些参考，不能据代码表面保留旧分支填成 104/104。

## 初版、最终版与模型最终说法的区别

| 轨迹行 | 实际证据 | 不能推出什么 |
| --- | --- | --- |
| 85 | 未改源码复现题面首尾各 +1，极大 uint64 为 0。 | 不是最终修法结果。 |
| 151、226、243 | 初版主要仍对 float percentile cast；第二版将 min/max 写回 float 数组；:243 仍打印原错误。 | 不能把初版失败当最终版已经评分。 |
| 199、204–217 | 诊断脚本因缺 `pd` 出现真实 exit 1；随后补 import 并成功运行。 | 这是 helper 运行失败，不是正式 F/P 判分。 |
| 396、431、444 | 三次 Edit 的目标字符串未找到。 | 这些 proposed new_string 不等于实际落盘候选。 |
| 466、483、505、549、584 | 中间版以 `np.empty` 仅设首尾，未初始化内值；题面暂正确、极大例仍为 0，后续打印出未初始化内值。:584 是复制的 debug helper。 | 未初始化问题属于中间版；复制 helper 不能替代生产全链验证。 |
| 593、597、606 | 最终改成 `np.full(min)` 并应用成功；两个 1/1 样例打印精确首尾。 | 不保证 1/3、多输入、auto 或104P。 |
| 628、633 | 综合脚本五组 min 打印相等；模型称“all tests passing”。 | 脚本没有 assert，不是既有模块全过。 |
| 650、655、668 | 最终多分区脚本首尾已偏一；模型仍称多分区正确、全部功能保留。 | :655/:668 的完成说法超过实际证据，且与 :650 的公开端点要求冲突。 |

未用历史 `gold`、`gold_full_auto` 或机制控制的名称/分数来推断本 Coder 候选的分数。[既有正式 CPU 审查](non_author_7305_formal_cpu_r15_review_20261003.md)只用于理解被冻结的接受边界，不转移其 105 项结果。

## test-like helpers 与正式测试污染

FP 共 15 项：1 个既有生产文件修改，14 个新增诊断脚本；全部内容摘要和 diff 绑定已核。diagnostics 明列 `comprehensive_test.py`、`test_edge_cases.py` 为 `candidate_test_like_paths`，二者都保留在 scoring projection 中，不能说它们被过滤了。14 份 helper 都是 NumPy/pandas/Dask 数据计算和打印，未含 assert，未调用 `set_index`；未见修改评分文件、conftest、fixture、pytest 配置、导入钩子或替换正式 oracle 的代码。

冻结命令是 `pytest -n0 -rA  --color=no dask/dataframe/tests/test_shuffle.py`（diagnostics `grading_revision.test_command`），只指定正式模块。正式模块不导入这些根目录 helper，原 conftest 的行为没有被候选改变。**从本次路径和代码可判断，它们不会自动成为105个正式参考或替代其断言。** 若未来改成根目录全量收集，两个 test-like 文件含顶层计算，需要另审收集行为；不能把这个未来条件当当前污染实测。

原 report 的 `test_files_modified=false / forbidden_path_touched=false / patch_hygiene=clean` 与 entry 核对一致；这只是补丁路径卫生。`control_surface=null`、`runner_integrity_changed=null`，正式准备保护没有完成，因此本报告没有声明全程运行完整性或正式抗污染检查已验证。

## 原评分、剩余工作与停止条件

[原 report](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-dask7305-coder-a1/grading/report.json):8–15 原样为 `failed_to_grade / infra_failure / reward=null`、F/P 数量全 null；:30 为 `grading_control_surface_protect_timeout_after_300s`，:44 的 `test_seconds=0.0`。diagnostics 为 `grading_revision.state=not_evaluated`，`candidate/compile_probe/control_surface/observations/verdict=null`、`env_qualification=absent`，phase `test=null`。日志在可信测试 patch 恢复及应用成功后终止（eval.log:1341–1385）；没有安装或 pytest 执行记录。测试补丁恢复成功不等于后续控制面保护完成，更不等于测试已跑。

正式参考按 diagnostics 独立计数为 **1F/104P，共105项**；auto 是这一个 F 的嵌套断言组，不能再加成第106项。`test_set_index_interpolate_large_uint` 是原来源 P 参考；不因为 v3 patch 中有该函数就改写其来源或多算新P。当前所有105项及模块 skipped/warnings 的实际状态都未知；本报告未填写或推测通过数。

剩余工作由既有分工继续：GPU 对同一原 FP 做已授权的准备预算恢复和重评分，不重求解、不改写原 infra；新评分另留原件，记录安装是否真正开始、105项逐参考状态、auto 是否实际执行、失败阶段与清理。仓库题主再结合本报告的语义缺口与正式结果决定必要复修。另一模型结果不在闭合清单，`paired_request_closed=false`；本报告只覆盖一个 Coder 样本，不判断另一臂是否已完工或比较两模型。

本轮停止条件已满足：原件和候选绑定闭合、初版/最终版分开、公开目标与源代码缺口定位、test-like 边界核清、未执行正式评分范围明确。无需追加本机候选执行来完成这次只读窄核。**可以进入原 FP 重评分切片；不能进入“候选通过/双模型首轮完整/可训练”状态。** 单样本、另一模型缺项、后续重评分未完成、环境资格缺失均保留；不授训练资格。
