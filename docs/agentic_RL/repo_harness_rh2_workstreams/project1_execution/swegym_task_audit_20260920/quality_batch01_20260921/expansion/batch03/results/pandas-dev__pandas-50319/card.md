# pandas-dev__pandas-50319

base `1613f26ff0ec`；建议 `needs_review / static_review`，仅 `development_diagnostic`。目标是点分日期的格式猜测不报错，公开明确接受 `None` 或有效格式。**唯一隐藏新增断言只接受指定格式，存在规范冲突。**

| 需求/旧行为 | 依据与测试 | 覆盖/证据 |
| --- | --- | --- |
| 原例不报错，允许None | issue末句；F2P精确比较fmt | 成功猜测路线覆盖，None路线冲突；替代实现未执行。 |
| 已支持格式、dayfirst、无效值、小数秒 | test_parsing公开参数/警告helper | 62旧实际猜测节点/58参考键，G/N均过；51旁路另计。 |
| 上层回退/数组推断 | datetimes.py129-146、432-462 | 调用者及公开测试已读，未在本题命令执行。 |

八方面已查：公开要求与base/原件对应；完整test.patch、helper、全部F2P及相关P2P；合法替代路线；gold和调用者；开发依赖/编译/权限；官方恢复/评分边界；本题关系和暴露。未查真实actor消息、镜像资产、全仓回归及模型表现。

真实reference_v1日志：两侧收集114节点，gold114通过、pytest rc0，noop在题面ValueError失败、113通过、rc1；冻结参考1 F2P+109 P2P，绑定后111解析键且参考全命中。反斜杠缺席已修，旧“gold恒失败”过时。两个空格alias仍合并2/4成员，现有成员都PASS；不能据此声称已发生错分。详情见封存初稿及历史增量。

原入口使用baseline.tar.gz和原bindings输入，run下文件是审计输出。镜像实际ID为null；历史grader54322、apply54321不证明正式actor。Cython需重建，历史安装成功；agent环境/当前镜像可用性待验。仅业务pyx交付，无额外排除规则。已暴露私有测试/gold/环境摘要及唯一旧记录，禁止给solver。

独立复核已完成，见[复审](review.md)。#24由pass改issue，#3实际输入仍unknown；“不强制gold正则”不消除对None路线的限制。唯一优先下一步：一份通用、局部的ValueError→None合理候选，配合base/gold控制，对照公开原例、旧格式/调用者回归与原reference_v1评分；当前未创建或执行候选。 正式模型开发前另验actor与重编译生效。

协调裁决（2026-09-20T22:14:39.224798+00:00）：暂不优先普通能力探针：题面明确允许None或有效格式，唯一新增断言却只接受指定格式。历史reference_v1已修反斜杠引用缺席，不消除接受范围冲突；合理None路线保留全部旧行为和实际reward尚待CPU确认。 51605公开base的_fill_token核心和注释包含50319 gold实现；仅源码包含事实，不证明Git祖先、题目重复或真实solver已见答案。
