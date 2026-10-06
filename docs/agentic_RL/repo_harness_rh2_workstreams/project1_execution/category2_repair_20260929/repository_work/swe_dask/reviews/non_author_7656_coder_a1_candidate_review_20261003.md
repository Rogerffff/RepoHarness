# Dask7656 首次真实 Coder 候选：非作者语义窄核

2026-10-03。对象：`gpu1003-dask7656-coder-a1`，base `07d5ad0ab1bc8903554b37453f02cc8024460f2a`。审查者为非候选作者的独立上下文；只读已有原件，未运行新 CPU/GPU、未执行候选或解压归档、未改共享源码或历史证据。

## 结论与用途

**当前正式批准范围内正确；原 reward=1 有代码和逐参考证据支持，可保留为一次真实 Coder 基座诊断成功样本。** 未见评分绕过或正式测试污染。候选没有修复已有 `init=False` 字段的重建限制；轨迹中的额外失败真实存在，最终说明对兼容性的概括过宽。该说明问题应在题主的诊断收口中明确记录，但不否定本题当前正式范围内的得分。

这是单模型、单样本结论。Qwen 另一模型尚未运行，不能据此完成双模型整题回传、估计成功率或稳定性。正式训练 typed actor 尚未接入；本次诊断 `image_override`、reward=1 与本审查均不授训练或留出资格。当前 card 末尾“尚无模型结果”是交接前状态，本报告只补充本次候选事实，不回写旧快照。

## 当前要求为何满足

[题卡第5–7行](../tasks/dask__dask-7656/card.md)限定：未初始化的 `init=False` 字段不妨碍 delayed 输入；被调函数收到原 dataclass 类型和正确字段值；嵌套 `Delayed` 求值；同类默认对象可用。题卡明确不新增 `post_init` 或已存在 `init=False` 字段状态恢复要求。这里的“同类默认对象”是 `a` 的 `init=True, default=3`，而 `b` 仍为没有默认值、没有实例属性的 `init=False` 字段；不能误读成要求支持 `init=False, default=...`。[有效补丁第9–30行](../tasks/dask__dask-7656/effective_test.patch)与[验收矩阵](../tasks/dask__dask-7656/acceptance_matrix.json)一致，参考仍为 1 F2P、48 P2P。

以 FrozenPatch 为事实来源：`dask/delayed.py` entry 内容 SHA 为 `dc88f58eb4a341bd6bb67dcbe88a393427168997d9312e5d4d97df8c4da7f74d`。只改第110–119行的 dataclass 分支：第114行筛选 `f.init or hasattr(expr, f.name)`，第115–117行保留递归解包，第119行继续 `(apply, typ, (), (dict, args)), collections`，`typ` 在第91行仍为 `type(expr)`。因此缺失的 `b` 被跳过，`a` 的嵌套图仍提取、求值，构造器还是原类，普通默认 `a=3` 仍传入构造器。这不是将对象改成 `SimpleNamespace`，也不是把 dataclass 当不透明对象跳过求值。

独立安全读取 `baseline.tar` 的三个 regular members 后，比对得到唯一生产代码差异正是上述筛选，基线第110–115行原本遍历所有字段。[正式报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/grading/report.json)为 resolved/reward=1，F2P 1/1、P2P 48/48；我把 [diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/grading/eval_logs/evallog_gpu1003-dask7656-coder-a_87804fb0.diagnostics.json) 两个参考集合逐项与 [eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/grading/eval_logs/evallog_gpu1003-dask7656-coder-a_87804fb0.eval.log) 的 `PASSED` 摘要核对，49个参考唯一、全到场，无失败、缺席、skip 或 unaccounted。日志第650/712行是强化后的 `test_delayed_with_dataclass` 通过；第762行总计 50 passed、2 xfailed。两个 XFAIL 是 `test_pickle[f1/f2]` 非参考，另有一个非参考 PASS；不能把52项写成全PASS。

## 已见失败：保留缺口，没有成功变失败的证据

本表行号均指 [完整 `attempt/trajectory.jsonl`](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/attempt/trajectory.jsonl)；与 harness 副本字节一致，SHA `b8fc1465395a130f394d3d129c041304cf8280389181c204fe1f58464e35da59`。已读完整403行中的全部正式 assistant/tool/result 内容，流事件只作运输重复记录。

| 证据行 | 实际结果与解释 |
| --- | --- |
| 71/75 → 97/101 | 原示例先在基线因缺失 `primary_key` 报 AttributeError，第一次筛选后打印 `Hack works`。 |
| 110/119/123 | `comprehensive_test.py`：基本示例成功；含默认 `init=False` 的多字段及混合字段分别因 `field2`、`init_false_field` 被传入构造器报 TypeError。脚本捕获异常，因此 tool `is_error=false` 不代表这些分支通过。 |
| 145/154/158 → 167/176/180 | 调试脚本误调用不存在的 `Field.has_default()`，第一次退出1；脚本后改正。这是探索脚本错误，不是 Dask 修复失败。后续调试同时证实构造器拒绝 `primary_key` 参数。 |
| 202/211/215；224/246/250 | 手动设置 `primary_key=100` 后，两次仍报 unexpected keyword argument。第224行第二次 Edit 只是把同一筛选移到局部变量并加注释，没有修复构造器路径。 |
| 333/342/346 | 作者新增 `test_dataclass_init_false.py`：基本测试通过，第二个含 `init=False, default="default"` 的多字段测试退出1，堆栈落到 `dask/utils.py::apply` 的构造器调用。 |
| 351/364/386 | 作者承认已有字段重建问题尚在，选择保留原示例的最小修复；第386行较长总结仍提到这个限制。 |
| 355/359；377/381 | 最终补丁的公开 delayed 文件实测 50 passed、2 xfailed；原始精确示例再测得到 `Hack works`。这不是作者执行了私有强化测试，私有版本的通过另见正式 grader。 |

已存在的 `init=False` 字段因 `hasattr` 为真而继续进入 kwargs；默认值可来自类属性，注释中的“actually set on the instance”并不精确。基线对已有字段也会 `getattr` 并把它们放入同一构造器 kwargs，`apply` 的实现未变。默认 `init=False` 但无缺失字段的 `MixedFields`，基线同样会向构造器传 `init_false_field`；手动设置的 `Entry.primary_key` 也相同。混合“缺失字段＋已有字段”的基线先 AttributeError，修后走得更远再 TypeError。**这是原有重建缺口未闭合／失败位置变化，不能归成已证新回归。** 这部分基线判断来自同源代码的静态比较，本审查没有新跑基线对照。

最终 FrozenPatch 仍保留 `test_dataclass_init_false.py` 第35–62行、`test_set_field.py` 第31–40行等原探针，内容与轨迹最后 Write 字节一致。第224行 Edit 后生产代码再无改动；不能把第346行失败解释为“早期实现已被最终修复”。这些额外输入不在 card 已批新增要求内，故当前不新增正式 oracle 或以它们否定 reward=1。

## 评分污染与最终说明

FrozenPatch 共8个 entry：1个 `dask/delayed.py` modify，另有 README 与6个探索脚本 add。实际 [scoring projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/grading/projection.json)包含全部8项，未在审查或评分前去掉失败脚本。diagnostics 也明确列出5个 test-like paths；`test_files_modified=false`只表示没有修改受信正式测试，不能据此声称候选没有新增测试文件。

未发现改 `dask/tests/test_delayed.py`、conftest、pytest配置、runner、报告hook、评分文件或环境导入替身的候选 entry；生产补丁没有按测试名特判、伪造输出或绕过求值。正式日志第324–340行恢复并核对基线正式测试后应用受信修订；第639行仅执行 `dask/tests/test_delayed.py`，因此根目录新增脚本未被收集，不能污染本次52项测试的结果。runner 摘要前后相同、`runner_integrity_changed=false`，无 conftest/fixture touch。这里对评分控制面的判断限定于已读原件，不扩展成全局安全保证。

**R1（P2，诊断报告问题，当前单样本用途不阻塞）：最终输出和 README 省略了已知额外失败。** 轨迹第399/403行最终回答的“原示例可用”和“50 passed、2 xfailed”有实测支持；“Backward compatibility is maintained”只能收窄为已测公开 delayed 文件未见回归，不能推成完整兼容性证明。其对 `init=False` dataclass 可用性的概括没有说明已知默认／手动设置字段仍失败。FrozenPatch README 第27–29行重复同一概括；作者此前在第386行知道这个限制，最终仍未带出。

- 当前行为／违反的不变量：已有失败未修，却以没有必要限定的兼容性和可用性表述收尾；诊断结论须与实际验证范围一致。
- 证据与位置：trajectory 第123、215、250、346、386、399、403行；FrozenPatch `dask/delayed.py` 第114–119行、README 第27–29行、`test_dataclass_init_false.py` 第35–62行。
- 影响／分期：可能使题主把“本题批准范围已修”误读成“已有字段状态恢复也已支持”。在本次题主诊断总结中纠正口径即可，不要求重跑本臂或扩大材料范围。
- 既有复现命令：轨迹第342行 `python test_dataclass_init_false.py` 和第246行 `python test_set_field.py`；本审查只引用它们，未新增执行。
- 收口条件：明确写出本题范围通过、已有默认／手设 `init=False` 重建仍失败且为原有缺口，并将单样本、Qwen未跑、训练actor未接入一起保留。原候选／轨迹／README无需被改写。

## 固定证据与停止条件

[FrozenPatch JSON](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/attempt/frozen/frozen_patch.json)文件 SHA 为 `c0498bb1a740d47107fd656e7d8d35bb72e0ad34dadc8c5ce7a2ac67bfed8658`；sorted compact canonical JSON 摘要为 `4191ab2dc23721fecbfbbc446dba1ae7122a1e28c97e55e5525e01555f405114`，与 grading status/projection 的 FrozenPatch digest 一致，两者不是同一种字节口径。[候选 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/attempt/candidate/dask__dask-7656.diff) SHA `6f87500991135e6e1a12a893c697ba746f37c249456a4a99ff109dbfcf7259ff`；[baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-dask7656-coder-a1/attempt/frozen/baseline.tar) SHA `99bfbf420a4a4d585a71ac780ac5c247883cf8f7e939b84ad64cebd2504a569b`。其余证据 SHA、字节与逐entry内容摘要见同名 JSON 报告。

已有 [GPU非作者执行审查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/dask7656_coder_a1_execution_review_v1.json) SHA `6d76e0aac1ba75c642f252a686dd6be1051290a95dc7a5ecd1335f9254f34307` 只作为身份、交付、执行与清理的窄证据；它明确没有题级候选语义终审，本报告没有借它替代上述代码判断。

**停止条件已满足：** 当前单Coder样本的正式范围语义、已见失败归属、评分污染面和验证表述均已核清，无当前诊断用途的语义阻断。余下是题主记录R1口径、继续尚未运行的既定另一模型（另按原授权执行），以及以后若扩展已有字段状态恢复要求再单独决定和验收；本报告不请求新CPU/GPU、不新增准入规则或审批。
