# 15184：题面与评分修订分开核查

2026-10-03。已收到[非作者材料窄核](../reviews/non_author_material_review_20261003.md)，题面材料可接受；本轮采纳仅新增一个正式P2P的建议。该核查不是新公开读者核查，也不替代CPU验收。以下说明拟新增参考的依据和取舍。

**R-f题面修订**只替换原例的失效复现。公开a.C/b.C程序由历史actor与私有gold对照核实；失败诊断须能区分类型，无歧义保持简洁。题面-only操作保持原F2P/P2P/test.patch不变，需要新的公开读者及实际消息交付核查。

**R-c护栏草案**针对原三条官方参考全部是失败断言、没有有效assert_type保护这一缺口。主要判别候选是“保留gold的失败文案修复，同时无条件让有效assert_type报错”；原评分是否放过它尚未实测。不得由候选修改了判断入口这一事实直接判定新评分要求必要或原题已误奖。

| 拟复用的公开case | 已有公开行为与本题关系 | 取舍 |
| --- | --- | --- |
| `testAssertType` | 精确base公开case同时保护合法断言、失败断言与返回表达式的int类型；base公开文档 `docs/source/error_code_list.rst` 的assert-type条目说明推断类型须匹配请求类型 | 唯一新增正式P2P；仍需CPU证明正/负对照与实际执行 |
| `testAssertTypeGeneric` | 精确base既有泛型成功断言和返回类型上下文；保护原assert_type语义，不要求泛型内部名称消歧 | 仅开发回归 |
| `testAssertTypeUncheckedFunction` | 精确base既有unchecked函数中推断为Any的失败与说明 | 仅开发回归 |
| `testAssertTypeUncheckedFunctionWithUntypedCheck` | 精确base既有启用check-untyped-defs后的普通失败诊断 | 仅开发回归 |
| `testAssertTypeNoPromoteUnion` | 精确base既有union类型合法断言 | 仅开发回归 |

`revision_proposal.json` 的 `added_mypy_cases` 只包含 `testAssertType`，另外四项单列于 `development_regression_cases`；没有发布或执行。保留原F2P2/P2P1后，共4个拟评分键。`-k testAssertType` 会命中不止一个case，因此最终参考集合要与正式消费者的实际选择、收集和解析结果配对；执行到某节点本身不是增加评分要求的理由。

“泛型内部同名类型是否漏判”是另一项已有静态疑问，没有新case、没有新评分参考，也没有证实错误候选得1。它与上述 `testAssertTypeGeneric` 的合法泛型断言不同；CPU窄校准有证据后再决定是否修订，不能提前写成必需消歧门槛。
