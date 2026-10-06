# Dask6626：本批CPU结果与用途

2026-09-29。**公开开发依赖修复、runner差异归因及三候选CPU评分均已完成；本次固定object空类别候选被正确拒绝，没有证实该候选的正式误奖。** noop=0、gold=1、fixed_object_empty=0。当前可保留为修订环境下的条件候选；正式题面交付和独立结果验收尚未完成，CPU结果不授予模型／训练或GPU资格。D6正式修订未实施，也没有因本次结果擅改原评分。

这是题主读回，复用先前公开资料与静态审查，不是新盲审。旧 `result_partial.md/json`、原日志及历史runner未知均保留；本次新证据不倒签旧完整性。

## 开发缺口与实际修复

固定base `56cd4597630feb1b01501c16d52aa862dd257a83`，registry digest `a182a6a7…`、config ID `fd456e2b…`与历史一致。原actor UID54321、CC2.1.205、Python3.8.19、pandas1.0.5、numpy1.17.5，从`/testbed`导入Dask。原两路径compute均正确，但Dask先分区再set_index的空类别metadata变成['a','b']；pandas先set_index路径仍为空。目标断言在`PUBLIC_COMPUTE_PASS`后精确失败。

原公开旧测15 passed/1 failed，失败是pytest8.3.2不再支持旧`pytest.warns(None)`。actor只预装pytest7.4.4后16 passed，项目bug继续复现，环境修复没有预改目标代码。两轮均4条Bash工具／5条桩消息，prelaunch/activation、完整日志、清理和工作树检查均正常。actor派生`a1f28fbc…`与COPY-only grader `d3befac6…`用途分开：grader三次实际日志均卸载pytest8.3.2、离线安装7.4.4并完成候选editable安装。

pip_check仍有distributed/Dask、fastparquet/pandas、zarr/numpy及chest冲突。当前验证只是实际公开开发命令和相关测试，不声称全镜像依赖无冲突。实际CC消息为Devcheck控制文本，无自主模型推理，不能当作完整题面/public_hints已交付。

## 行为与正式参考

| 候选 | 题面两路径compute | object空类别metadata | 非示例int64空类别 | 旧公开测试 | 正式F2P / P2P | reward |
| --- | --- | --- | --- | --- | --- | --- |
| base/noop | 通过 | Dask路径错误 | 类别集合从[]变成[1,2] | 16通过 | 0/1；14项全过 | 0 |
| gold | 通过 | 两路径通过 | 空集合及int64类型保留 | 16通过 | 1/1；14项全过 | 1 |
| fixed_object_empty | 通过 | 两路径通过 | 变成object Index，失败 | 1失败、15通过 | 0/1；13通过、1失败 | 0 |

非示例控制来源是公开dataframe metadata保持dtype不变量（base `docs/source/dataframe-design.rst`）与已公开空类别测试，不以私有新增要求判错。base数值类别仍是int64，失败在CategoricalDtype内类别集合变化；错误候选则实际把类别Index换成object，二者不混写。gold采用原类别切片保持dtype；错误候选硬编码`pd.Index([], dtype="object")`只适配题面的object例子。

正式F2P `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty` 对noop和错误候选失败、gold通过；错误候选还被P2P `test_meta_nonempty_empty_categories` 拒绝，在已有float64例子中类别类型从Float64Index变成Index。故这里是参考已覆盖的dtype退化，不是“错误候选虽然原例过便得到满分”。私有int64例子支持同一一般不变量，并未改变正式评分。

正式全日志：noop1 failed/15 passed，gold16 passed，错误候选2 failed/14 passed，各有2 warnings。root冻结parser重放与本次逐参考原日志核对一致：1+14个参考全部有状态，无缺席或参考外失败，无测试前错误。16个实际测试不等于15个正式参考。私有三变体matrix均有四条命令完整起止、预期行为输出及完成marker，准备与逐容器清理正常；root诊断不替代actor权限证明。

## 导出补丁与runner实际差异

gold正式导出patch与私有输入逐字相同，SHA256 `cbbe53717dcb84886245a407920e3981b914948a28db3e81d3c51ea2a93e8e47`；错误候选为 `4d2d08220ab0fa4e5238f79a04dedacdaf8c87feae41ee4124dc05473139cc4f`。两者只改`dask/dataframe/utils.py`，未改测试、安装或评分。正式apply、候选安装与test均完整，三个eval日志SHA与ledger一致，清理removed=true。

runner安装前摘要 `0f3527775c70cece62a1cb6aebd15f554bceee5d03e6f54575b5af67d5068f43`，pin后摘要 `a7b7f1e4d9d840b38dcc19daa1f46d09c0cb3e558d41c91f1c5e08dcfcb509cc`：本次root受控81文件清单精确重建两个历史摘要，70路径因pytest降级改变（_pytest68、pytest2，pluggy不变），随后editable清单0变化。三个正式受限grader安装也记录相同前后摘要及pytest降级成功，故本批`runner_integrity_changed=true`有具体、重复一致的环境配方依据，不能机械判作候选破坏runner。

本次逐文件重建强化了历史差异解释，但历史当时逐文件原件仍缺失，不宣称历史完整性已经通过，也不说root清单就是正式grader逐文件清单。恢复输入已明确：固定base、COPY-only compat_v1、pytest7.4.4 wheel SHA `b090cdf5ed60bf4c45261be03239c2c1c22df034fbffe691abe93cd80cea01d8`与离线pin后editable配方。

## 资源、用途与全部剩余项

三次正式配置2CPU/4GiB，使用本批统一CPU准备上限900秒，与旧300条件分开。trusted setup按noop/gold/错误候选依次665.921、601.471、648.309秒；mem_peak_mb为2115.551、2094.328、2113.641。三次正常完成且清理成功；resource_facts为空，不补写未采的OOM统计。安装/test分别完整、原失败是具体测试断言，不是时间预算或收集错误。

本次没有依据要求为已拒绝的固定object候选追加正式评分规则。可保留公开metadata/dtype控制作为开发回归依据，后续是否扩大题目覆盖仍按公开需求和D6决策处理。相邻空CategoricalIndex问题不自动扩成该题必修要求；一个错误候选被拒绝不证明所有退化都被覆盖。

已完成CPU开发修复、三变体行为、三份正式导出/评分、runner重建和清理读回。剩余为跨包完整结果独立验收、正式题面/public_hints实际交付、既有环境限制与历史缺证在用途中的明确保留，以及另行授权的模型／训练／GPU资格；D6仍未实施。不需重复本次完整对照。

证据入口：`runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/`（actor、runner inventory、私有matrix、正式三候选）；`runs/swegym_cpu_preprobe_20260929/analysis/dask6626_followups_v1.json`（root冻结parser重放）。本目录`result.json`保存全部逐参考、资源、补丁一致性、runner文件变化及证据SHA。

root另已完成两题已结束证据同步核验：293文件、2,338,594字节远端／本地SHA一致，见`analysis/evidence_manifest_dask_pair_v1.json`。`analysis/resource_dask_pair_v1.json`按实际grading容器后缀匹配采样，采到的OOM/PID拒绝计数为0；采样未必覆盖最终退出，不能据此宣称完整零事件。该采样证据与ledger峰值及空resource_facts分开保留。
