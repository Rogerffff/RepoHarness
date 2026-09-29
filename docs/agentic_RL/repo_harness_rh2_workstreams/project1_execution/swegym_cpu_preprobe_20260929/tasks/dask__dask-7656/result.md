# Dask7656：本批CPU结果与用途

2026-09-29。**环境恢复和CPU对照已完成；正式参考确实误奖将传入delayed函数的重建参数改为错误类型的候选。** noop=0、gold=1、opaque=0、wrong_result_type=1。最后一个候选在公开类型保持控制中失败，却通过全部正式参考，因此本题目前可用于环境校准和评分覆盖诊断，不能直接作为无条件正确性／训练资格样本。D6正式测试／评分修订仍未实施；本稿不修改原题。

这是题主完整读回，复用先前公开资料与静态审查，不是新盲审。旧 `result_partial.md/json` 和所有raw保留；actor/private已有跨包审查 `reviews/dask7656_actor_private_review.md`，本次完整正式结果及最终卡已通过[跨包独立复核](../../reviews/dask_pair_final_review.md)。CPU完成不代表自主模型、训练或GPU验证。

## 目标、处理与真实开发验证

题目要求dataclass含未初始化 `init=False` 字段时仍可作为delayed输入。原例只返回常量，不能独自验证dataclass类型及内部Delayed求值。公开增强控制因此同时检查原类、默认字段值及嵌套Delayed；依据是base的原类重建行为、公开delayed遍历语义及已有dataclass测试，不从私有测试发明新的公开要求。

固定base `07d5ad0ab1bc8903554b37453f02cc8024460f2a`、registry digest `27d11a07…`。actor只安装pandas1.3.5并经conda钩子设置stdlib distutils；真实CC2.1.205/UID54321/Python3.9.19工具输出确认其生效、源码来自`/testbed`、工作树未预改。5条工具调用完整，旧公开选择3 passed，base原例精确触发缺失primary_key，清理完整。该base增强控制在第一个对象已失败，未执行嵌套分支。

grader的`e4a2cbb1…`镜像只附加离线wheel；四次实际安装日志均显示export stdlib、pandas2.2.2→1.3.5和候选editable安装成功。它与actor预安装镜像分开记录，不能仅从actor环境推断grader环境。pip_check仍有distributed、fastparquet、xarray、chest约束冲突，当前验证范围限于已跑目标及相关测试。

## 私有行为与正式参考逐项对照

| 候选 | 公开原例 | 私有执行的公开增强控制 | 旧公开3测 | 正式F2P / P2P | 正式reward |
| --- | --- | --- | --- | --- | --- |
| base/noop | 缺失primary_key | 首个对象同样失败，嵌套未运行 | 3通过 | 0/1；48项全过 | 0 |
| gold | 通过 | 两个对象均通过，原类型／默认值／嵌套值保持 | 3通过 | 1/1；48项全过 | 1 |
| opaque_dataclass | 通过 | 默认对象通过；第二个对象仍含Delayed，触发布尔求值TypeError | 1失败、2通过 | 0/1；48项全过 | 0 |
| wrong_result_type | 通过 | 首个对象在isinstance(Entry)失败，嵌套未运行 | 3通过 | 1/1；48项全过 | 1 |

正式唯一F2P是 `dask/tests/test_delayed.py::test_delayed_with_dataclass`。它最终读取 `.a` 并比较计算值，能拒绝opaque的未求值Delayed，却没有核对象仍是原dataclass。wrong_result_type在`unpack_collections`中将传入delayed函数的dataclass重建参数替换为`types.SimpleNamespace`，仍能满足该属性值比较，导致误奖；原例fun最终返回的字符串仍正确，本次错误是函数收到的参数丢失原dataclass类型。不能将其类型失败外推成“本次嵌套分支也失败”，也不能只因opaque被拒就核销这个漏洞。

正式执行全日志：noop/opaque各1 failed、49 passed、2 xfailed；gold/wrong_type各50 passed、2 xfailed。正式参考只有1+48，不能把52个执行节点全部称为参考。root冻结parser重放的四份逐参考表与本次逐键原日志核对一致：所有49个参考均有状态，无缺席、无参考外失败、无测试前错误。

## 补丁、资源和清理证据

三份正式导出candidate.patch与本批私有输入逐字一致，只改`dask/delayed.py`，未改测试、安装或评分：gold SHA256 `2f6f59d094834f3e8db2d1e5332f1415ff65d151678d5cc6c6590f1883de63e9`；opaque `f6a357f6b5a69c91d4d9b5e40d3df13e79e0099f75265537a9ffa1241b1cae84`；wrong_type `d422554ec399b5540bc3492c8fcddf0b2c06246ec842545f6fb33ff7cc38d066`。投影/apply及完整安装/test均成功，参考缺席0；四次runner前后不变，全部清理removed=true。全部eval日志SHA与ledger记录一致。

首次300秒CPU准备上限在control_surface_protect超时，reward=null，安装/test未开始，明确无OOM且清理成功；该失败不记为noop=0。随后独立`grading_setup900_v1`仅使用本批统一CPU准备上限900秒，image/code/recipe及评分不变。四次trusted setup分别347.769、355.131、531.685、505.693秒；mem_peak_mb分别2882.219、2065.551、2069.871、2041.305，均在2CPU/4GiB配置下完成。新四次resource_facts为空，不据此宣称独立OOM计数已采齐。

私有root对照使用actor派生镜像，逐变体补丁准备、完整输出及rm/query成功；它不替代actor权限证明。actor的实际用户消息仍是Devcheck控制文本，正式题面/public_hints实际交付尚未由本批证明，没有自主模型推理；桩token/cost不记模型成本。

## 建议与尚未完成项

本次确立S1误奖。最小可复用验收草案已经是可执行输入，不需重新读题或另造测试：`runs/swegym_cpu_preprobe_20260929/task_inputs/dask__dask-7656/public_commands.json`中的`issue_original`、`default_nested`和`public_regression`可直接给冻结devcheck入口；私有多候选配方在同目录`private_semantic_spec.template.json`。材料边界及已有判据为：

- 题面原例：`Entry.primary_key=field(init=False, repr=False)`、`other_field=4`传给delayed函数不应因缺失属性建图失败；`issue_original`复用原例，gold应输出`Hack works`。
- base已有契约：`dask/delayed.py`原代码以`typ`重建dataclass，因此传入函数的对象应保留原类；`default_nested`中的`assert isinstance(entry, Entry)`直接检查这一点，不来自gold新断言。
- 题面已有默认字段与base嵌套契约：同一命令先检查普通`Entry()`的`other_field==4`，再检查`Entry(other_field=dask.delayed(4))`；后者由base已有`test_delayed_with_dataclass`的嵌套求值要求支持。最终marker `ENTRY_DEFAULT_NESTED_PASS`只在两个对象完整通过后出现。
- 原公开测试回归：`public_regression`选择base已有`delayed_with_dataclass or traverse_false or to_task_dask`三个测试；本次gold全过、opaque被旧dataclass测试拒绝、wrong_type三项仍过，必须与类型控制联合读结果。

已有实测验收表可直接复用：base原例／增强都失败；gold两命令和三旧测均过；opaque原例过但增强嵌套与旧测失败；wrong_type原例及三旧测过，但增强首个对象的类型断言失败。两个错误候选都必须被综合验收拒绝，不能把仅原例过视作修复。D6后续可把这组公开依据控制接入正式验收；目前只交付草案和实测正负对照，**尚未修改正式测试或评分**。公开Fix提示会降低独立定位难度，应在用途说明保留；已存在init=False/post_init状态仍为未覆盖扩展边界，不能以gold为oracle扩大题意。

当前已完成CPU目标复现、公开开发配方、gold/两类错误候选、原正式评分和日志清理读回；剩余为完整正式结果跨包验收、D6处置及新版本验证（若决定实施）、正式题面/public_hints真实交付，以及另行授权的模型／训练／GPU资格。无须重复本批已完整actor/private对照来伪装进展。

最少证据：`runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/calibration_v1/`（actor、private、首轮超时）；同级`grading_setup900_v1/`（四候选完整ledger、导出patch、eval、预算）；`runs/swegym_cpu_preprobe_20260929/analysis/dask7656_setup900_v1.json`（root冻结parser重放）。本目录`result.json`保存逐参考状态、资源、补丁一致性及SHA索引。

root另已完成两题已结束证据同步核验：293文件、2,338,594字节远端／本地SHA一致，见`analysis/evidence_manifest_dask_pair_v1.json`。`analysis/resource_dask_pair_v1.json`按实际grading容器后缀匹配采样，采到的OOM/PID拒绝计数为0；采样未必覆盖最终退出，不能据此宣称完整零事件。该采样证据与ledger峰值及空resource_facts分开保留。
