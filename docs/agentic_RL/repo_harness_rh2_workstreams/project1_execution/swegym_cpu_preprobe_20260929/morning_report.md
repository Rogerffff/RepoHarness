# 本夜 SWE-Gym CPU 处理结果

2026-09-29。**18题的CPU实验、逐题用途结论与独立最终复核已完成。** 本次从已审的新32题中处理14题、旧21个待处理项中处理4题，覆盖6个仓库：Dask 2题、Pydantic 6题、MONAI 4题、Conan 3题、Moto 2题、mypy 1题。原19个受限候选没有统一重跑，没有使用自主求解模型或GPU。

这18题原本就带着静态疑点，因此下面的比例不能用于估计整个SWE-Gym的质量。

## 得到了什么

| 结果 | 题数 | 含义 |
| --- | ---: | --- |
| 错误候选仍获原评分1 | 14 | 同一份候选源码在私有行为验证中违反公开要求或已有回归行为，原参考却没有拒绝它 |
| gold修复原例，却引入兼容性回归 | 2 | Pydantic8567、9066；还需能保留相关兼容行为的正对照，不能直接把gold当成完整正确答案 |
| 所测错误被拒，但示例覆盖限制仍在 | 1 | Pydantic6283；本次没有证明该候选误奖，不能与前14题混算 |
| 所测错误被正确拒绝，本轮未发现新的覆盖阻断 | 1 | Dask6626；可继续探针入口核验，不代表所有行为或训练资格已验证 |

实际完成 **54次有效RH2评分**，另有 **2次环境准备超时**，保留为基础设施失败、无奖励。它们是人工固定noop、gold和错误候选的对照，不是54次模型求解。每题都检查了与问题相关的公开开发操作；公开actor使用真实解题身份，私有gold/反例使用独立容器，二者证据不互相替代。

## 每题具体结论

“受限诊断”表示可以继续调查；若用于模型能力比较，须先统一公开行为验收和统计口径，原reward与语义审计分列。它不自动授予比较或训练资格。

| 题目 | 本夜实证 | 当前处理方向 |
| --- | --- | --- |
| [Dask7656](tasks/dask__dask-7656/result.md) | 补齐相关开发依赖后可复现。错误修法让传入delayed函数的参数丢失dataclass类型，却得1 | 受限诊断；补类型保持验收 |
| [Dask6626](tasks/dask__dask-6626/result.md) | pytest兼容修订后公开16测通过；固定object类型的错误被真实参考拒绝 | 可继续探针入口核验，保留配方及依赖范围限制 |
| [Pydantic8793](tasks/pydantic__pydantic-8793/result.md) | 强制required的错误得1，却破坏默认值5及两项已有测试 | 受限诊断；同时检查required和已有默认值 |
| [Pydantic5662](tasks/pydantic__pydantic-5662/result.md) | 仅特判ANY的错误得1，一般比较对象的委托仍不正确 | 受限诊断；补一般matcher，不只验证示例 |
| [Pydantic6283](tasks/pydantic__pydantic-6283/result.md) | 验证式构造错误被两项原参考拒绝；非42字符串补充也已执行 | 仍保留核心相等目标仅覆盖示例的限制 |
| [MONAI2446](tasks/Project-MONAI__MONAI-2446/result.md) | NiBabel兼容修订后公开7测通过；错误候选保护了调用方，却跳过内部shuffle/cache行为，仍得1 | 受限诊断；外部列表不变与内部洗牌都要验 |
| [MONAI5932](tasks/Project-MONAI__MONAI-5932/result.md) | 反转处理顺序能过原参考，却破坏长引用在前的同类表达式 | 受限诊断；两种引用顺序均有可执行控制 |
| [Conan11594](tasks/conan-io__conan-11594/result.md) | 补Ninja后真正越过配置阶段；错误候选把请求的Release变成Debug，仍得1 | 受限诊断；补真实CTest配置与输出验收 |
| [Moto5406](tasks/getmoto__moto-5406/result.md) | 硬编码East2得1，却破坏East1 ARN及已有公开测试 | 受限诊断；保留两地区行为 |
| [Moto6114](tasks/getmoto__moto-6114/result.md) | 查B的ARN却返回一个A的候选得1；参考只检查数量 | 受限诊断；同时检查对象身份和数量 |
| [mypy15139](tasks/python__mypy-15139/result.md) | 无条件小写得1却破坏既有显示规则；gold原例仍混用Type/type | **只作诊断**；目标范围争议未解除 |
| [Pydantic5706](tasks/pydantic__pydantic-5706/result.md) | 统一转list的错误得1，却破坏4项公开回归；公开说明与gold的支持/拒绝方向不同 | **只作诊断**；先明确JSON支持还是拒绝 |
| [Pydantic8567](tasks/pydantic__pydantic-8567/result.md) | gold得1，但普通Custom+PlainValidator从可构建变为schema错误 | 受限诊断；补有效正对照与兼容性检查 |
| [Pydantic9066](tasks/pydantic__pydantic-9066/result.md) | gold得1，但标准dataclass默认实例生成schema时报错 | 受限诊断；补有效正对照与默认值schema检查 |
| [MONAI4583](tasks/Project-MONAI__MONAI-4583/result.md) | 只修2D的候选得1，稀疏3D标签仍返回背景；gold所测8种组合正确 | 受限诊断；补实际3D标签，不只看box形状 |
| [MONAI6975](tasks/Project-MONAI__MONAI-6975/result.md) | 日志和lazy调用正确、却丢弃变换图像的候选通过63项参考 | 受限诊断；必须检查返回像素，不能只检查日志 |
| [Conan13230](tasks/conan-io__conan-13230/result.md) | 只修Android的候选得1，公开Linux host仍误取Apple SDK/flags | 受限诊断；按实际flags及失败位置验收 |
| [Conan13721](tasks/conan-io__conan-13721/result.md) | realpath候选得1，却把alpha/beta入口都变成_generator | **只作诊断**；软链缺口已证，后缀约定仍有争议 |

## 实际修了什么，哪些还没修

本夜完成四项新的题级开发配方修订并复验：Dask7656相关pandas/distutils条件、Dask6626的pytest版本、MONAI2446的NiBabel版本、Conan11594的Ninja工具。其它题复用原镜像或已验证的历史配方。安装/导入及相关命令可用，不等于整个镜像的依赖都健康；Dask既有pip check冲突等边界仍在题卡中。

还修正了两处**本批实验代码**的归因：Pydantic5706的异常类型预期与固定base不一致；MONAI6975先比较空参考计数，掩盖了真正的准备超时。均另建版本、保存旧失败，没有修改生产评分语义。

**正式题面、测试和参考集合没有改。** 多数题下一步需要的是把已有行为控制接入可追溯的修订版本。共用[D6成本设计](d6_revision_cost_note.md)已完成，建议先做MONAI5932与Conan11594两题的窄切片；实现尚未授权，也尚未验证。增加私有后检不能包装成正式评分已修好。本批没有新增训练或留出评测准入。

效率方面，Dask/MONAI的控制面准备曾耗时数百秒，个别超时发生在conda前缀chown、测试之前；MONAI评分容器达到4GiB限额并发生回收压力。改用更长准备上限并调整并发后，对照已完成；这不是单变量实验，**不能声称准备成本已修好，也没有测出最低测试内存**。原失败与有效运行分开，资源采样缺口保留。

## 接下来如何接续

1. 复用现有19个受限候选和本批明确的逐题记录，先核统一模型入口与预算；不能把本批18题直接加入普通模型比较分母。
2. 对有明确公开依据的覆盖缺口，优先落地上述两题的版本化修订与正式noop/gold/错误候选复验，再推广已有控制。三道目标或口径争议题继续只作诊断。
3. 本夜以18题收口；原登记的另6个备用题未执行，不算失败或完成。此时继续增加同类反例，优先级低于把已证缺口真正接入验收。

证据：结束原件去重 **1981件、26,100,155字节**，远端/本地逐SHA256一致，含历史准备失败和6283补充；不含镜像、wheel与宿主持续资源日志。逐评分清单见[56条账本汇总](../../../../../runs/swegym_cpu_preprobe_20260929/analysis/grading_inventory_v1.json)，逐题原件、独立审查和适用边界见各题卡及[根验收记录](reviews/root_progress_review.md)。

收口状态（06:58 SGT）：资源观察器与本地同步器已停止，最后一次同步成功；宿主观察日志及调度收口回执另8件逐SHA核对一致。自动巡检已通过官方工具暂停并回读确认；CPU实例保留运行，没有残留容器或任务网络。未提交或推送。
