# 48106：Coder 首轮轨迹与候选分析

整理于2026-10-03 20:10 SGT。仅适用于 `gpu1003-pandas48106-coder-a1`，材料 `pandas48106-complete-bindings-e19-v1`；另一模型首轮尚未返回，整项请求仍为 claimed。作者已完整核对546件、202,834,592字节的大小/SHA及本次候选、轨迹和原评分。新增非作者核查另留报告，不把本记录当作其结论。

**结论：正常结束后的部分修复，语义失败；原0分可信。** 候选修好了题面中的数值插入，却破坏了同一 categorical enlargement 路径的类别保留和缺失值一致性。没有发现需修改本题材料或阻断另一模型首轮的缺陷；不因失败追加采样，不为提高分数删减测试。保留原候选和原评分。

## 实际结果与失败边界

| 对照范围 | 本次结果 | 含义 |
| --- | --- | --- |
| 题面数值样例 | 通过；新元素为0，dtype为object | 原 TypeError 已解除，并保住题面中的值 |
| 插入已有类别值 | 失败1项；object与期望category不符 | 候选把合法类别值也统一转成object |
| 数值扩展类型类别中插入NaN | 失败10项；UInt/Int/Float参数均丢失category | 候选没有保留类别元数据 |
| 4种缺失值的扩大／原位置赋值一致性 | 失败4项；扩大为object，原位置赋值为category | 同一缺失值在两条路径上的dtype不一致 |
| 来源P2P | 1020/1020成功，缺席0 | 该参考集的旧行为保留，不能据此说所有回归都已排除 |

原正式分为 `0 / unresolved / tests_failed`，F2P为1/16；所有1036个来源参考均有有效状态，五组13个完整绑定成员逐一PASSED。pytest物理结果为15失败、1029通过、1 XFAIL；物理通过数和1020个来源P2P属于不同口径，XFAIL不充作来源成功。安装RC0、测试RC1，footer完整，runner摘要前后一致。实际资格读取当前NoOp记录；actor与grader正常清理，manager创建1、移除1，无未关资源。

候选在 `_maybe_promote` 中对 `CategoricalDtype` 无条件返回object；缺失值还先走原有 `isna` 分支，同样返回object。因此，不能只给这一新分支加“类别内值”条件就声称缺失值问题已解决。其余 ExtensionDtype 被改成跳过部分原转换逻辑；本次参考没有显示额外失败，不将静态风险冒填为已观察回归。补丁只修改一个生产文件 `cast.py`，另新增四个诊断脚本和一份PR说明，没有修改正式测试或评分保护面。

## 轨迹中怎样形成这一结果

下表的行号指原 `attempt/trajectory.jsonl`，不是去重后事件编号。

| 原轨迹行 | 实际行为 | 可判断的能力与缺口 |
| --- | --- | --- |
| 10–254 | 阅读cast/indexing/dtypes，复现原TypeError，确认 `CategoricalDtypeType` 是metaclass | 异常定位成立；最初完整读取cast，之后多次重复局部读取，未查实际相关测试目录 |
| 267–310 | 先绕开 `_ensure_dtype_type`，样例不报错却把0变成NaN；随后识别值丢失并撤回 | 有反馈纠错；中途一度把“不崩溃”当主要目标，后来按题面值和dtype纠正 |
| 358–410 | 第二次调整仍复现TypeError，再用公开debug脚本检查dtype判定，改成最终分支 | 有迭代定位，但修改条件从“值不适配类别”扩成“所有CategoricalDtype” |
| 419–445 | 原样例正确；自测五种值只打印结果，没有断言类别／缺失值保留 | 自测已经打印 `None → dtype: object`，仍称所有测试正确；没有测插入已有类别值 |
| 467–484 | 唯一pytest尝试报错后，改跑两条numpy promotion打印检查 | 未查路径、未恢复相关pytest验证，numpy检查不能证明categorical边界 |
| 489–512 | 最终宣称“minimal、preserves all existing functionality、thoroughly tested” | 完成声明超出实际验证；不是执行器强制截断后的未完成回答 |

pytest命令为 `python -m pytest pandas/tests/dtypes/test_cast.py::test_maybe_promote -v`，工具返回退出4及 `unrecognized arguments: --strict-data-files`。**实际baseline没有该文件**；测试位于 `pandas/tests/dtypes/cast/test_promote.py`，该选项由公开 `pandas/conftest.py::pytest_addoption` 注册。选错路径导致选项未按预期加载，是与源码相符的机制推断，本次没有另行动态复现这个报错机制。既有同源actor用有效路径运行14项公开测试通过、保留原addopts；因此没有证据把它认定为缺失pytest-datafiles插件或全题环境阻断。明确观察到的是“路径不存在、调用失败、模型未纠正”。

## 效率、预算与并行

| 指标 | 实际记录 |
| --- | --- |
| 求解墙钟 | 135.975秒；CC duration 132.087秒，API duration 124.403秒 |
| 生成／回合／工具 | 42个生成请求，CC记录42回合；41次工具：Read11、Bash21、Write5、Edit4；工具报错1次 |
| token | 累计input 1,807,416，output 12,378；cache read/create均0；单请求已报告input峰值56,308 |
| 预算 | probe-wide-v1：196,608上下文、每响应65,536输出、240回合、求解10,800秒；gateway实际请求输出上限均65,536 |
| 结束分类 | completed / end_turn，harness退出0；没有预算截断证据 |
| 评分成本 | 总评分1,241.206秒；受信准备段835.636秒，评估包装段332.903秒；原脚本安装323.765秒、测试包装7.665秒，pytest自身4.76秒 |

累计input是各次请求相加，不是单次上下文长达180万；不能把76个assistant分块重复计成76个生成请求。CC `modelUsage.maxOutputTokens=32000` 是原元数据，保留不改；本次实际gateway请求为65536，不能据这个元数据反推32000截断。排队字段记录0，只说明本job的该字段，不据此推算用户等待时长。评分包装包含安装；不能把332.903秒称为纯pytest耗时。

全部41次工具调用串行，每次assistant最多一个tool_use。实际工具列表不含Task／子agent入口，未观察跨agent并行，不能据此判断模型的跨agent并行能力。源码和测试目录发现、独立numpy／category检查可以批量执行；编辑与复现反馈存在先后依赖。本次更大的求解缺口是未选对验证目标和未断言dtype，增加并发本身不会补上这些语义检查。评分准备显著长于模型求解，环境等待与模型效率分别报告。

## 当前用途和后续

本题提供的是“定位正确、局部值修复成功、边界保留和验证不足”的可靠失败样本，适合进一步比较另一模型是否识别这些边界。已有CPU正负对照和独立材料审查继续有效，本次不重复CPU、不代模型补一个通过候选、不改变公开题面或奖励。当前优先补另一模型首轮；普通追加采样服从现行覆盖优先规则，旧默认每模型三次计划不再自动执行。单次不能判断稳定失败率或训练增益。

身份和训练边界仍保留：actual actor为原source `0e706113…c4b8`，grader记录固定E19 `53b17fe2…860a`；code_v8、材料摘要、NoOp资格和原镜像证据均有引用。原 `gateway_audit.checkpoint_identity_verified=false` 及input-check仅配置的运行标记保持原值；实际运行的模型下载绑定、engine／adapter inspect、BF16和服务读回证据另存于snapshot，不将旧布尔字段升级为已验证全链资格。模型名称依据这些实际绑定，训练typed actor租约与训练资格没有完成结论。

## 证据入口

- [执行回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/pandas48106_first_coder_execution_receipt_v1.json)：SHA `ee3e77426810e47d35c8ef4807c4431400371cee5cdd06eef7a2a3e7c26bd43b`。
- [作者逐项核验原件](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas48106_coder_a1_v1/evidence.json)：SHA `77905233687995d9bdbe0065b1494a65a43b2635a537e0bef0418eba4fdf5c50`，含原件路径/SHA、16项结果和阶段计时。
- [候选diff](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas48106-coder-a1/queue_v31/results/gpu1003-pandas48106-coder-a1/attempt/candidate/pandas-dev__pandas-48106.diff)、[原评分日志](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas48106-coder-a1/queue_v31/results/gpu1003-pandas48106-coder-a1/grading/eval_logs/evallog_gpu1003-pandas48106-code_05c7bb04.eval.log)、[去流式重复的阅读副本](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas48106_coder_a1_v1/trace_normalized.json)：副本保留每条原JSONL行号，原轨迹不回写。
