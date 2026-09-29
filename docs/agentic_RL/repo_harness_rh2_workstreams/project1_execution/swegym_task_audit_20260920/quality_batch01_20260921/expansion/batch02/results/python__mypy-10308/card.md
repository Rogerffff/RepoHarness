# python__mypy-10308

**保留明确 materials-v2 版本的受限静态候选；needs_review / static_review，仅 development_diagnostic。** 目标是在 base `1567e36165b0` 上修复 Vector/Matrix 泛型协议定义导致的内部崩溃。公开复现、协议规则与调用链足够开始解题；实际actor消息和开发条件未验。

| 需求/旧行为 | 决定性检查 | 范围 |
| --- | --- | --- |
| 递归协议检查不崩溃 | 唯一F2P真实build→constraints.py:437；no-op失败、gold通过 | 同根因，非题面原例；未测float上界、显式self等原例组合 |
| 缺成员/较窄方法参数应拒绝，自身赋值应接受 | F2P两条错误、缺成员与签名notes、p11/p22无诊断 | 有正负行为断言，非只查不崩溃 |
| 合法递归推断、普通类结构兼容、变型等保持 | 公开旧case已沿调用关系静态读 | P2P=0；这些旧回归未运行 |
| Iterable不保证Hashable | testHashable在G/N日志确实执行 | 不属冻结奖励引用 |

新开放的 stage1 原件证实 Hashable 当时已被选中并缺件，gold目标通过、empty目标崩溃；两侧整体 pytest rc=1。stage1 的安装 rc=0 还掩盖了 editable build isolation 缺 setuptools 的失败。原始1898字符 hints 有缩小输入与字母序观察，当前公开包未带入；这是调试信息遗漏，尚非不可解证明。

原S2测试缺Hashable fixtures；09-19既存materials-v2补齐两个fixture并保留stub依赖pin，未改原断言或F2P/P2P。原/修订grading digest已重算核对，不能混称原版通过。修订版两次原始账本、日志、投影证明目标得分0/1；gold仅改subtypes.py。普通完整pytest rc=1的非引用失败不自动使奖励0，全局失败另判。

八方面均作静态检查：公开需求、材料初态、全部新增断言、合理替代路线、gold与相关旧回归、依赖/actor需求、投影恢复/控制面、关系与用途。未做原例CPU对照、替代/部分实现重放、重复稳定性、实际泄漏与真实求解验证。历史“精确诊断强制gold”的因果推断被通用诊断源码反驳，仍未证明所有替代解都会接受；不能从零P2P直接判坏题。

修订评分用派生image `9acbdc2f…`、grader/54322；正式face仍取public image、actor/54321，依赖与权限不能互借。`test_globs=()`，修订仅恢复`.test`、两个fixture、test-requirements四个精确文件；合法算法源码可交付，额外排除=[]。

**唯一优先下一步：**固定已核派生grader和materials-v2输入，对公开Vector/Matrix原例做base/gold对照；记录实际算法模块来源，目标是消除internal error，允许正常类型诊断。仅协变guard候选保留为按结果选择的后续假说。独立[复核](review.md)已完成；实际actor是模型开发前的单独核验，不前置阻塞该语义实验。原prepared并未自动重冻结，不能把修订成功称原版通过。无本轮运行或费用估计。

原件定位：`runs/env_recipe_repair_20260919/materials_v2/runs/python__mypy-10308-{gold,noop}/ledger.jsonl:1`；完整映射、版本/入口、阅读范围及暴露见同目录封存初稿和old_findings_delta。主审已见隐藏测试、gold和本题历史，不可把审查产物交给solver。
