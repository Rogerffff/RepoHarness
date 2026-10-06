# mypy-15184 Qwen3.6 首臂：非作者语义与评分反证审查

日期：2026-10-03。角色：按 `review-standards.md §10.4` 的 Falsifier / Simplifier 要求，尝试推翻“候选已修复公开行为目标”和“正式五参考真实通过”的解释。已见 R10 私有、gold 与作者上下文，**不是 fresh 公开读者**。

本次只读冻结本地原件、计算 SHA、解码 FP、比较 baseline 与候选源码、解析日志和模型轨迹。未 SSH、运行容器、CPU、测试或模型；唯一写入是本报告，未修改代码、共享记录、旧报告或历史证据。

## 结论与实际用途

**本范围没有可证实的新 finding；支持本首臂的限定语义通过。** 结论来自源码因果链与原始五参考执行，未由 `reward=1` 单独推导：候选联合格式化两个类型，能发现顶层及泛型参数内的同名冲突；未更改类型比较或表达式返回值。正式原两 F2P、新嵌套 F2P、原简洁名称 P2P、有效断言 P2P 均真实执行并通过。

模型验证过程有两次自写测试失败，随后修正；最后“七个 assert_type 测试通过”有完整、未管道截断的对应日志。八个 `is_error=true` 工具结果中，六个是故意不匹配类型的预期退出 1，两个是测试编写错误，没有发现本轨迹中的安装、运行环境或工具调用接口故障。

这支持登记 **Qwen3.6 本题本次普通 GPU 首臂的具体求解结果**。它不证明重复稳定性、另一模型或整批题目的能力；闭包自身 `paired_request_closed=false`，不应把本臂完成写成配对请求完成。环境资格与执行资源由相应审查入口核，不在此增加门槛。

## 原件身份、baseline 与投影

入口为 [闭包 manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/gpu1003-mypy15184-qwen36-a1_closed_manifest_v1.json) 和 [GPU readback](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/gpu1003-mypy15184-qwen36-a1_closed_evidence_readback_v1.json)。实际证据根为 `runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/`；以下原件链接均指向该根。

- 独立重算 manifest 列出的 **95/95 文件** SHA 和字节数，无差异，合计 21,307,412 bytes。manifest 本身 SHA 为 `63f34446034872a4433719ade72a7ba15d1be095226e317933d95a337f4db367`。manifest 内其他作业的配置或 prompt 不构成其他作业已完成的证据。
- [FP](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/attempt/frozen/frozen_patch.json) 的规范化 digest 独立重算为 `41adba1ea7056b5ac16b09ebdcb69ac59954c0f6ea6243cf5855adfb7e57c4aa`；两项均为普通 `100644` 文件：`mypy/messages.py` 与 `test-data/unit/check-expressions.test`。解码内容 SHA 分别为 `2ca8bce8da916a44cf9ef4e598085f1dcd9575a0bf1c4cba71869f6f0ebe330f`、`ca27d822671bb113d5ff76539f76f94b8ddc25a832095a3a8dccf471aa16f1ea`，均匹配条目声明。
- [baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/attempt/frozen/baseline_manifest.json) 规范化 digest 为 `fdd59f846a872a5fb2680de446faf5d8a286db2237559c43c8b43874e82df1a5`；[baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/attempt/frozen/baseline.tar) 恰好 1,422 个条目，逐文件内容与规范化可执行 mode 匹配，无额外路径。冻结与评分重建的 census 字节相同，SHA 为 `5d6f0d161a576c62b4161ad3114dfa586e579f4a5ca5485b053fa021984f3fd5`。
- [projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/grading/projection.json) 只包含 `mypy/messages.py`。模型新加的两个公开开发 case 留在原 FP，**没有进入正式评分**。classification 为 projectable，runtime private pathset 未变。
- 精确 base 为 `13f35ad0915e70c2c299e2eb308968c86117132d`；实际 GPU 镜像为 `cda77e2d613176919d3c6fb8a0f1aae952a1f77a5d0170602db93c432867c025`。正式 revision 为 `mypy15184-nested-nominal-types-v2`，材料 identity 为 `bf000616fc92f2d7869bdb2039ab1fe0d9167e507a5bb15e6c5987ab033d8053`，与 R10 在用身份一致。

## 源码为何支持顶层、嵌套与有效断言

候选的唯一实现改动在 baseline `mypy/messages.py:1658` 的 `assert_type_fail`：把分别调用 `format_type(source_type, ...)`、`format_type(target_type, ...)` 改成一次 `format_type_distinctly(source_type, target_type, options=self.options)`，然后使用返回的两个已加引号字符串生成同一错误消息。`codes.ASSERT_TYPE` 和错误发出位置保留。

1. **顶层歧义：** baseline `find_type_overlaps`（2584–2602 行）跨传入的两个类型汇集 `Instance` 的短名与 fullname。同一短名对应多个 fullname 时，返回需要完整限定的集合。原先分别格式化只看各自一个类型，无法识别两边的 `a.C`／`b.C` 冲突；候选共同传入两边，消除这一原因。
2. **嵌套歧义：** `CollectAllInstancesQuery.visit_instance`（2574–2576 行）记录实例后调用父 visitor；baseline `mypy/typetraverser.py:80–81` 继续遍历 `t.args`。`format_type_inner`（2365–2369、2412–2424 行）递归格式化参数并沿用同一 fullname 集合。因此 `list[a.C]`／`list[b.C]` 中的 `C` 也会被限定，修法不只检查外层实例。
3. **简洁与有效断言：** fullname 只用于有短名冲突的实例，联合 formatter 从低 verbosity 开始，因此无冲突的 `MyInt`／`MyStr`、`array[int]`／`int` 可保持简洁。未投影改动的 baseline `mypy/checkexpr.py:3911–3932` 仍只在 `not is_same_type(source_type, target_type)` 时调用错误 formatter，并返回 `source_type`，包括原有 Literal 处理。候选没有把有效断言改成无条件报错，也没有改变其表达式类型。

以上是所核代码路径的解释，另有正式嵌套与有效断言 case 的实际运行支持；不扩成所有可能类型形式均已证明。

## 正式五参考：执行与解析一致

[原始 eval](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/grading/eval_logs/evallog_gpu1003-mypy15184-qwen36_11516763.eval.log) 478 行实际命令为 `pytest -n0 -rA` 加五个完整节点，没有额外 `-k`。490–495 行列出五个不同 `PASSED` 和 `5 passed`；测试 RC 为 0。我独立取 Test Output 段重建节点集合，恰等于正式五参考，FAILED、missing、skipped、额外节点均为 0，与 [diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/grading/eval_logs/evallog_gpu1003-mypy15184-qwen36_11516763.diagnostics.json) 四个分区及 report 一致。

下表前三及简洁名称 case 的文件均为 `check-assert-type-fail.test`，有效断言来自 `check-expressions.test`；完整节点前缀都是 `mypy/test/testcheck.py::TypeCheckSuite::`。

| case 名 | 正式用途 | 实际结果与含义 |
| --- | --- | --- |
| `testAssertTypeFail1` | 原 F2P | PASSED；冲突的 `array.array[int]` 与 `__main__.array` 被区分 |
| `testAssertTypeFail2` | 原 F2P | PASSED；`array.array[int]` 与 `__main__.array.array` 被区分 |
| `testAssertTypeFailNestedNominalTypes` | 新 F2P | PASSED；诊断为 `List[a.C]`／`List[b.C]`，内层名被限定 |
| `testAssertTypeFail3` | 原 P2P | PASSED；无冲突时保持 `array[int]`／`int` |
| `testAssertType` | 新增已有 P2P | PASSED；合法 `int/int`、`Literal[42]/Literal[42]` 无额外错误，返回值 reveal 仍为 `builtins.int` |

这里 PASSED 表示 pytest 对完整诊断的预期比较通过；前三 case 仍要求 mypy 报告类型不匹配，不意味着不匹配断言变为合法。嵌套 case 使用测试框架的 uppercase builtins 选项，`List[...]` 与 R10 在用 oracle 相符。

## 尝试推翻来源、保护和安装解释

- **候选测试放宽了 oracle：证据不支持。** projection 已去掉候选 `check-expressions.test` 改动。eval 209–222 行真实从精确 base 恢复该公开文件，SHA 为 `f541a8781c01edf4a27209cc1569e61d1d8a4741c3d4bc381548d0b1239ce3b9`，随后干净应用私有新建测试 patch。setup 实际恢复 1 个 base 既有文件，预期/实际测试文件为 2/2，缺失与不规则为 0；diagnostics 记保护 2 文件、6 目录，`RH2_PROTECT_OK=1`。
- **安装失败被末条 RC 掩盖：本臂未见该情况。** eval 398–462 行完整记录 requirements 安装与 editable 构建、卸载旧 mypy、安装新 `...dirty` 版本成功；ERR trap 无失败记录，安装未跳过、日志完整、安装段完成且最后 RC0。两条命令没有分别记录数值 RC，所以不冒称“逐条 RC0”；依据是成功正文与无失败 trap。该证据不同于 10174 的 wheel Permission denied 原件。
- **原 FP 或 baseline 缓存带来结果：未见具体支持。** FP 仅两源码/测试路径，没有 `.mypy_cache`；baseline 1,422 条目也没有 `.mypy_cache`、`.pyc` 或 `.so`。diagnostics 的 baseline 省略缓存计数为 1 目录/3 文件，未列具体路径，不能补写为某种缓存命中。正式五 case 的普通非 incremental 分支在 `testcheck.py:133–140` 关闭 incremental 并使用 `os.devnull` 缓存；本题不是写缓存回归。
- **实际加载的是别处实现：没有支持该解释的阳性证据。** editable 安装成功，观测包入口为 `/testbed/mypy/__init__.py`，runner 前后 digest 均为 `bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548`。baseline 无编译模块，投影仅改 formatter，而原三 F2P 的具体诊断变化与源码相符。动态观测只记录包入口，**没有 pytest 进程内 `messages.py.__file__`／loader 的单独采样**；本报告不把静态与功能证据写成该采样已存在，也不因纯假设要求新探针。

status 记 `baseline_rebuild_passed=true`、manager 创建/移除各 1、open/supply/cleanup_failures 均空及 `cleanup_ok=true`。diagnostics 的 `resource_facts=null`、`env_qualification=absent`、包版本观测为 `?` 原样保留；成功安装正文可确认具体版本，不等于取得新的 HostConfig 或训练资格验收。

## 模型验证过程与八次工具错误

[trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v13/results/gpu1003-mypy15184-qwen36-a1/attempt/trajectory.jsonl) 有 39 次工具调用、39 次对应结果，恰好 8 个 `is_error=true`。下表调用序号只按这 39 次排序；行号指原 JSONL。

| 调用／结果行 | 分类 | 实际影响 |
| --- | --- | --- |
| 1／19 | 预期负例 | 修前复现退出 1，诊断为 `C`／`C`，没有环境错误 |
| 15／231、37／561 | 预期负例 | 修后同一不匹配断言退出 1，诊断为 `a.C`／`b.C` |
| 18／281 | 预期负例 | `Container[int]`／`Container[str]` 不匹配，退出 1；这不是嵌套同短名消歧验证 |
| 19／295、38／575 | 预期负例 | `MyInt`／`MyStr` 不匹配，退出 1并保留简洁名称 |
| 23／355 | 自写测试错误 | 两新增 case 失败：用了 `--- a.py` 等错误文件分隔语法，且 fixture 下 `typing_extensions` 不提供所用 `assert_type` |
| 29／439 | 自写测试错误 | 修正为 `[file a.py]` 后仍两 case 失败，剩余原因是 fixture 下的 `typing_extensions.assert_type` 导入 |

模型随后参考既有公开 case，把新增测试改为 `from typing import assert_type`。调用 32／结果 481 行是直接 pytest、非管道：`-k testAssertType` 收集 7 项，五个旧公开 case 和两个新增 case 全部通过。调用 33／499 行选中 8 项也真实通过，额外项是 `testTypingSelfAssertType`，不与前七项累加成新分母。直接合法 `a.C/a.C` 调用在 267 与 589 行均显示无问题。

最终输出在 599／603 行声称“七个 assert_type 测试通过”，与调用 32 的七项日志一致；其模糊的中间表述 “All tests pass” 只能理解为当时所选测试，不能登记成全仓库通过。调用 34 的 `-k distinct` 选中另外五个主题的 case，不能称为联合 formatter 专项覆盖。调用 35、36 用 `pytest ... | tail`，没有 pipefail；尾部确有 `44 passed`、`181 passed`，但工具成功只证管道末条退出，**不能记为独立 pytest RC0**。正式五参考是另一次原始、无该管道的评分运行，未借这些开发测试增加正式分母。

模型没有自己新增或明确运行 `list[a.C]`／`list[b.C]` 的开发回归；本报告对这一嵌套行为的运行判断来自正式新 F2P，源码遍历解释与其一致，不把模型的泛型 `Container` 示例替代该证据。

## 复用既有反证与停止条件

复用 [R10 非作者反证审查](non_author_15184_r10_falsifier_20261003.md) 和 [CPU 条件验收](../python__mypy-15184/cpu_probe_acceptance_20261003.json)：同版五参考已取得 `noop/gold/bad/top_only=0/1/0/0`。noop 在三 F2P 上真实失败；始终拒绝合法断言的 bad 只在有效 P2P 失败；仅限定外层的 top_only 只在嵌套 F2P 失败。GPU diagnostics 的 revision、四分区与五键保持该条件，故无需重做矩阵来确认本次已知语义区分。

停止条件已满足：原件完整性、候选唯一实现改动、顶层/嵌套遍历及有效断言 guard、正式五节点执行与解析、测试恢复/投影、八错误分类和最终验证陈述已分别核清。当前没有具体题面、评分或候选缺陷需要修复；最低接续是由题主合并本报告与执行链路审查并登记本首臂结果。只有后续出现材料身份变更或新的实际失败，才按具体影响追加验证；不新增 metadata、全套测试、CPU、模型或训练准入条件。

本报告保留一次运行、动态目标模块采样缺席、资源与资格另核、配对请求未闭合的边界。未更改冻结 GPU readback 中“审查 pending”的历史状态，也未回写旧原件。
