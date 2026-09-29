# Dask 两题跨包原件复核

2026-09-29；复核者：MONAI/Conan/Moto 题主。仅核本地已同步证据，未执行项目或远端作业。先读公开/私有命令、候选、正式导出与完整评分日志，再对照 root 的冻结 parser 分析。初判形成后，两题题主 `result.md` 已落盘并完成交叉核对：关键结果、失败归因和用途限制一致。该核对不把题主自查当作独立原件。

**独立结论：Dask7656 确认重建参数类型退化仍得分 1 的覆盖缺口；Dask6626 的固定 object 空类别候选被正式评分正确拒绝。** 两题当前正式 0 分均有真实测试断言/目标异常，不是安装、收集、超时或 parser 故障伪装。以下是题级实验结论，不是训练或模型能力准入。

## 正式结果与逐参考核对

| 题目 / 候选 | reward | F2P 通过 | P2P 失败 | 完整 pytest 汇总 |
| --- | --- | --- | --- | --- |
| 7656 noop | 0 | 0/1 | 0/48 | 1 failed, 49 passed, 2 xfailed |
| 7656 gold | 1 | 1/1 | 0/48 | 50 passed, 2 xfailed |
| 7656 opaque | 0 | 0/1 | 0/48 | 1 failed, 49 passed, 2 xfailed |
| 7656 wrong_result_type | 1 | 1/1 | 0/48 | 50 passed, 2 xfailed |
| 6626 noop | 0 | 0/1 | 0/14 | 1 failed, 15 passed |
| 6626 gold | 1 | 1/1 | 0/14 | 16 passed |
| 6626 fixed_object_empty | 0 | 0/1 | 1/14 | 2 failed, 14 passed |

F2P 是应由失败转为通过的参考；P2P 是应保持通过的参考。分别为 49 和 15 个正式参考，不能用 52/16 个 pytest 结果总数替代。已从冻结 host grading view 取完整参考键，与每份测试段的逐项终态独立对照；无缺失/跳过参考、无段外解析、无参考外失败。结果与 [7656 冻结 parser 分析](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/dask7656_setup900_v1.json)、[6626 分析](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/dask6626_followups_v1.json) 一致。

7 份正式完整 eval.log 的 SHA256 均与各自 ledger 匹配。安装日志显示固定兼容包安装成功、原 `python -m pip install --no-deps -e .` 完成；安装 RC=0、无失败命令，测试起止/footer 齐备。所有 import observation 均指向 `/testbed/dask/__init__.py`；setup 控制面文件齐备；candidate 与 grader 清理记录均成功。正式候选补丁与输入逐字节一致；解码 `frozen_patch.json` 后同 public base 比较，仅含预期源码差异，noop 无 entries，均无测试/fixture 路径或 excluded pathset 变化。未以 `git apply` 返回 0 单独推定已生效。

## Dask7656：漏判成立，局限具体可见

[正式评分原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/grading_setup900_v1) 的 F2P 是 `dask/tests/test_delayed.py::test_delayed_with_dataclass`。noop 在建图读取不存在的 `b` 字段时报 AttributeError；opaque 已绕过建图错误，却在嵌套值仍为 Delayed 时触发 `Truth of Delayed objects is not supported`，因此正式 0 是有效拒绝。

`wrong_result_type` 的冻结源码在 `unpack_collections` 重建参数时确实把原 dataclass `Entry` 替换成 `types.SimpleNamespace`，导致 `inspect_entry` 收到错误类型的参数；两个入口均过滤缺失字段。这里不指函数最终返回值类型错误：原例仍正确返回字符串。该候选原例输出 `Hack works`，现有窄回归 3 passed，正式 49 个参考全部通过。但 [私有 default_nested 输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/calibration_v1/private_behavior/wrong_result_type/default_nested.out) 明确在 `inspect_entry` 的 `isinstance(entry, Entry)` 断言失败；gold 同命令输出 `ENTRY_DEFAULT_NESTED_PASS`。正式测试只观察嵌套字段值，未检查重建对象类型。这里证实的是重建参数类型保持缺口，不把 opaque 的失败算作第二个漏判，也不推断所有嵌套行为都未覆盖。

“保持 dataclass 类型”的依据来自公开 base，并非以 gold 能通过新断言倒推题义：[delayed.py 第 91、110–115、175、188–193 行](../../../../../../runs/swegym_quality_expansion_20260925/public/dask__dask-7656/base/dask/delayed.py) 在两个既有入口均取 `typ = type(expr)`，并调用 `typ` 重建；同文件第 224–230、373–386 行的公开 `delayed` API 将 Delayed 定义为原对象的惰性代理，支持原对象方法和属性。[公开旧 test_delayed_with_dataclass（99–113 行）](../../../../../../runs/swegym_quality_expansion_20260925/public/dask__dask-7656/base/dask/tests/test_delayed.py) 明确把 dataclass 作为受支持的输入，虽只测字段值，恰说明类型断言缺口。另有 [公开旧 test_unpack_collections（472–508 行）](../../../../../../runs/swegym_quality_expansion_20260925/public/dask__dask-7656/base/dask/tests/test_base.py) 将原 dataclass 重建后的完整结构与仍含 `ADataClass` 的期望结构比较；它经过另一条 repack 路径，只作为同版本公开类型保持约定的旁证，不冒充本候选的动态验收。SimpleNamespace 替换会破坏原类方法、dataclass 身份及同类型值相等关系，超出了“跳过缺失 init=False 字段”的修复范围。

本次 `default_nested` 在 base 的缺失属性处已经失败，所以该命令本身不是“base 正常而候选回归”的独立差分证明；类型保持判断依赖上述公开规范/既有实现，当前运行仅证明候选实际违反该约定。未声称运行了另一个无缺失字段的类型保持探针，也不凭这条新 assert 单独定级。

原镜像与 pandas 1.3.5 兼容 actor 都以 uid 54321、testbed 解释器和 `/testbed` 导入执行公开原例；base 目标 AttributeError 与窄回归 3 passed 均抵达。私有矩阵是 root 行为诊断，不能替代 actor 证明，也没有证明模型能自主修复。正式测试复验只把 setup/reset 预算由 300 改为 900 秒；镜像、配方、参考和测试超时未改。旧 `calibration_v1/noop` 的 control_surface_protect 超时、reward=null 保留为独立 infra 失败，不能改写为本次 0 分。

用途：可用于环境/开发条件与评分覆盖诊断。按当前冻结评分，不宜直接纳入无额外说明的正确性比较分母或训练奖励；若后续修订质量验收，须另留版本及批准，不能回写本次正式测试。

## Dask6626：修复环境后，正式测试能识别本次退化

[完整原 actor 回归输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/actor_original/captures/public_regression.out) 的单个失败是 pytest 8.3.2 不接受 `pytest.warns(None)`，不是目标 metadata 缺陷。pytest 7.4.4 预装后的 actor 16 项公开回归通过；两条 compute 路径完成，同时 base `dask_set_index` 的 metadata 仍为 `['a','b']`、真实结果为空，目标断言准确复现。不能把 compute 返回正常等同于 metadata 正确。

私有 gold 与 fixed_object_empty 都能修好题面 object 类别例子；[固定 object 候选的数值空类别输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/private_behavior/fixed_object_empty/nonexample_numeric_empty.out) 显示预期 `Int64Index([], dtype='int64')` 被改为 object Index。正式冻结输出同样确认 `cats = pd.Index([], dtype="object")` 真正生效。其 F2P `test_meta_nonempty` 在新增 K 列 dtype 保持断言失败，P2P `test_meta_nonempty_empty_categories` 在 Float64Index 类型保持断言失败；gold 用 `s.cat.categories[:0]`，全部通过。因此本候选是被评分检出的退化，不支持宣称当前题已发生漏判，也不证明评分覆盖完备。

三份正式 ledger 的 runner_integrity_changed=true 均保留。[runner 文件级受控复验](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/runner_inventory/runner_file_comparison.json) 显示 pytest 8.3.2→7.4.4 改变 70 个 runner 文件，pluggy 保持 1.5.0；随后原 editable 安装改变 0 个 runner 文件，前后 aggregate digest 与三份正式 observation 一致。可将本次变化归因于已声明 pytest pin；历史缺失的文件清单仍然缺失，当前复验不等于补齐历史原件。

用途：支持该明确兼容配方下的公开开发条件、noop/gold 区分及本次退化拒绝证据，可保留后续探针候选身份；模型能力、未测行为、任务划分、预算和正式准入仍需另行满足。

## 证据完整性与边界

[root 远端/本地 SHA 对账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_dask_pair_v1.json) 记录 293 份、2,338,594 bytes、0 差异；本 reviewer 未重做远端对账。[资源采样分析](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_dask_pair_v1.json) 按评分 report 后缀匹配，未观察 OOM/PID 拒绝；采样不覆盖全部退出时刻，不能表述为全程零事件。两题 actor、私有行为和正式评分权限不同，不能互相替代。

题主结果一致性：已核对 [7656 result.md](../tasks/dask__dask-7656/result.md) 与 [6626 result.md](../tasks/dask__dask-6626/result.md)，没有需改写的关键结论。两份 result 当前“完整结果仍待独立复核”的状态可由题主链接本审查更新。额外核实两套 actor 构建 image.json 均保留 pip_check 非零（distributed/fastparquet 及 xarray 或 zarr 等版本约束冲突）；不能宣称整个镜像依赖健康。原始 stub 首条用户消息确为 Devcheck 控制文本，本批没有证明正式题面/public_hints 真正交付，也没有自主模型求解；这些剩余项仍有效。

本轮适用维度为失败归因、测试有效性、冻结契约与来源一致性、真实评分入口、资源和可诊断性、依赖漂移及用途边界。未审新的生产实现、训练 loss 或调度并发修改；本结果复核不重复静态题目整套审查。没有发现需要重跑这 7 个已完成正式候选来确认上述结论的证据缺口。
