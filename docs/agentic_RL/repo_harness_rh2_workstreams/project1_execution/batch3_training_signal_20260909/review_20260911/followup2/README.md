# I20 R4 / R6 修后窄复核（2026-09-15）

**结论：R4 余项与 R6 均通过，I20 离线报告首版的本轮实施审查可以收口。没有新增阻塞项或 T0。** I19 原通过结论不变；I18 未定与目标 CC 真实压缩请求核对的安排不变，不能据此宣称第三组所有工作已完成。

被审对象为 HEAD `4529ebd77fa27bc4c3bb4f1bffe9657c0af78abb` 上 Claude 尚未提交的 `run_report.py`、维护测试及 manifest 计数改动；具体字节见 [source_snapshot.json](source_snapshot.json)。本轮未修改这些文件，也未提交、回退或清理共享工作区。按 [上一轮停止条件](../followup1/README.md)，只复核 R4 / R6 和直接回归，没有扩展到训练算法、第四组评分或硬件实验。

## 1. 两项验收

| 项 | 独立验证 | 结论 |
|---|---|---|
| R4：无事件 bundle 被唯一可见 run 认领 | A 有 r1 事件和 audit / bringup，B 只有 audit / bringup。指定 r1 与默认输出均为 r1 的 audit / bringup 各 1 条，未知归属各 1 条，task 分布不含 B。B 单独输入且没有事件时，仍输出未绑定 run 的本地摘要；DIS 为 `not_collected`。给 B 补 r2 事件后，各 run 独立统计；共同父目录作为单 bundle 输入时，归属不明如实计数。 | 通过。两条归属循环及默认汇总中的兜底已删除，不再用全体输入中的唯一 run 替无事件目录证明归属。 |
| R6：成员版本只取首叶 | 使用实际 rollout emitter 的事件形状：`[['5'], ['6']]` 为 1 个多版本成员；交换叶顺序不变；`[['5'], ['5']]` 为 1 个单版本成员；部分叶缺版本与全部缺版本分别核验。 | 通过。按成员汇集全部叶的版本并集，缺失事实没有被补成已确认版本。 |

R6 的 `single_version` 表示**已知版本集合**大小为 1。有叶缺版本时，`members_with_leaves_missing_versions` 会同时计数，不能把该成员解释为已确认全程单版本；这是重叠的事实完整性计数，不能再加进成员总数。全部叶缺版本才归 `unknown`。这符合上一轮“汇集所有叶并显式保留部分事实”的验收要求。

直接回归正控也通过：FORK 的 `[10,10,10,11]` 四行仍归并为 2 个成员，reward 均值 0.5、优势符号近似正负各 1；两 run 的同名 step 分别还原为 16 / 40 token；logprob 对拍的 TP 副本模拟仍得到 16 个可比动作。

## 2. 证据与边界

- [verify_fixes.py](verify_fixes.py) 复用前两轮的真实 rh2 writer、fork 原函数 AST emitter 和 loader 探针；[verify_fixes_result.json](verify_fixes_result.json) 为本次独立执行结果。历史反例及其输出未回写。
- [focused_tests.txt](focused_tests.txt)：报告、真实 emitter、I19 表示、消费陈旧度、丢组汇总、masked logprob 六个相关测试文件，**73 passed，5.51 秒**。
- 相关源码、维护测试和本轮探针的 [ruff](ruff.txt) 通过；[lanes 前置检查](lanes_checks.txt) 通过。`--checks-only` 未运行双 lane pytest，不构成完整 lane 资格。
- [verification.json](verification.json) 记录命令、退出状态及被审源码在复核期间未变化的核对结果。没有独立重跑作者报告的全量 2266 或完整双 lane；没有真实 run 文件、CC、Docker、API 或 GPU 验证。

R5 原适用限制保留：`logprob_compare` 已按身份去副本；`sample_dis_accounting` 缺少足以安全去重的事件身份，TP>1 明示不支持，不能把本次收口解释为所有指标都支持 TP>1。实际 run 输入的完整性与缺口仍随既定诊断作业核对，不新增实施前闸门。

本轮只关闭两项纯消费者统计问题，不改变 reward、loss、准入、预算、路由或 staleness 规则。没有需要用户补充决定的内容。
