# 评分性能交付：独立复核

日期：2026-10-04，Asia/Singapore。复核对象为 `rollout_v13`，补丁 SHA-256：`66cc2dc69533482fe9e03c4dea5be12211acf4d4126f2af6dd2234ef40e503ea`。

**结论：本地实现与历史 CPU 对账可以收口；两项独立反例已修复。尚未验证真实 Claude Code/GPU 原容器评分、Prime 线上环境，也没有启用相关默认开关。** 这份结论不授予题目训练资格，不替代上线前的窄验收。

## 两项发现及修复确认

| 发现 | 具体后果 | v13 独立复验 |
| --- | --- | --- |
| Prime 创建结果未知时，已经等待并发槽的请求仍会继续创建 | 第一条请求进入 `create_unknown` 后，第二条排队请求绕过停止检查，可能增加未收口资源 | 第二条取得槽后重新检查。原反例只有第一条实际发出创建请求，排队条目为 `not_created`；未知资源记录仍保留，`close()` 仍明确报未收口。 |
| 可选权限计时文件读取异常会改变评分 | 同一输入关闭诊断时得 1，打开诊断后因 `GradingInfraError` 提前停止，变成 infra；还可能覆盖原准备错误 | 普通读取异常记入诊断字段，不阻止原评分。原反例开关两侧都实际启动候选测试、得 1、容器清理为空；取消异常继续传播。 |

离线反例使用真实 backend / manager 控制流与受控故障替身，没有建立 Prime 资源、访问线上服务或调用模型。证据：

- [Prime 原反例](../../../../../runs/grading_performance_20261003/root_delivery_review_20261004/prime_queued_unknown_probe.py)及 [v13 结果](../../../../../runs/grading_performance_20261003/root_delivery_review_20261004/prime_queued_unknown_probe_after_v13.json)。
- [诊断读取原反例](../../../../../runs/grading_performance_20261003/root_delivery_review_20261004/diagnostic_readback_probe.py)及 [v13 结果](../../../../../runs/grading_performance_20261003/root_delivery_review_20261004/diagnostic_readback_probe_after_v13.json)。

## 版本与证据检查

独立目录按真实冻结父快照的 1046 个成员重建，逐个验证字节，再应用 v13 的 23 个文件改动。测试补充包共 275 件；其中 4 个与真实父版重叠且内容不同的旧测试，保留父版，不静默覆盖。没有修改共享生产源码。

独立运行 6 个相关测试文件：**44 passed**。作者完整相关检查为 343 passed、1 skipped、1 项历史模板材料缺失被明确 deselect；本次没有重复整套检查。

历史 CPU 证据重新读取了 73 个输入文件和 27 份评分日志：26 次原候选评分、1 次另行 noop 资格运行。日志长度与 SHA、冻结 parser 的逐参考状态、真实测试退出信息及 manager 收尾逐项对账；26 次原候选与相应 fresh 对照的状态映射相同，参考没有缺席，收尾没有未关闭容器或清理失败。最终 461 件证据索引另行逐件核验。资源空集是归档收尾检查，不冒充当前实时巡检。

复核原件位于 `runs/grading_performance_20261003/root_delivery_review_20261004/`，关键记录：`stage_v13_receipt.json`、`local_tests_v13.json`、`cpu_evidence_readback.json`、`final_evidence_index_readback.json`。

## 性能结论的适用范围

现有 CPU 证据支持固定三份原候选下的收益：DVC9395 中位评分耗时约 240.75→97.51 秒，Pandas48106 1132.49→813.13 秒，Coverage ea69 43.29→15.13 秒。DVC 四作业队列的墙钟时间约 386.17→207.40 秒，收益主要来自吞吐，单作业并行耗时反而略增。

这些是三个固定候选的重复对照，不是 26 道独立题的性能结论。准备模板有一次成本，必须分别报告。原容器路线并非总比优化后的 fresh 快：Coverage 不明显占优，Pandas 原型还要计入约 313.56 秒准备成本，正式 actor/grader 镜像不同会回退 fresh。现有编译探针证明旧扩展可能被复用、强制编译能更新二进制，不证明所有题的安装脚本都会重编候选改动。

## 后续边界

- 真实 Claude Code/GPU 原容器路线尚未运行，集成时先检查实际镜像、环境恢复、编译行为、评分、回退与清理；不直接全池开启。
- Prime 仅完成原 SDK 请求模型与离线传输检查。账户、费用、镜像发布、guest 权限、网络及真实线上创建/删除仍未验证；资源未知事实保留未知，不伪装成 Docker 等价资格。
- 原容器评分与性能诊断默认仍关闭。本次没有部署 GPU、修改题主账本、改变题目参考集合或使用付费资源。
