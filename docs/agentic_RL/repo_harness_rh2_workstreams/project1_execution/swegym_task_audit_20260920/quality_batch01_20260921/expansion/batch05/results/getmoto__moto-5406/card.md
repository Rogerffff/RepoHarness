# getmoto__moto-5406

**独立静态复核完成；保留 `needs_review / static_review`，暂不列模型优先候选。** 目标是DynamoDB表ARN使用客户端地区；base=`87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。backend已按地区存表；Table收到region却未保存供ARN使用，helper写死East1。region仍用于默认加密键，不能说完全丢弃。gold保存并使用地区，核心修复合理。

| 要求/旧行为 | 覆盖与结论 |
| --- | --- |
| East2描述表ARN应为East2 | 唯一F2P完整ARN断言；历史noop目标失败、gold通过 |
| 保留East1及其它地区ARN | 26项P2P不查ARN；已有公开 `test_create_table_standard:43–45` 的East1断言未选入评分 |
| 原例和派生ARN保持一致 | 原例表名不一致可公开消解；Create返回、完整stream/SSE/TableClass组合及tags/backup/CFN未执行验收，gold有静态调用链支持 |

八方面已核：公开需求、材料初态、全部27项/helper、合理替代解、gold与相关回归、开发依赖、交付评分、暴露用途。未验真实actor、实际镜像ID、完整原例、扩展回归、替代候选、跨题关系及模型能力。check3/7/24/26收窄为unknown；East1缺少保护归check25，不等于已证gold回归。

原证据为baseline01，无install_wave1/derived覆写。安装RC0；noop 1失败26通过、RC1，gold27通过、RC0，参考无缺席/跳过。`image_id_actual=null`，期望manifest不能代填。原 `mem_peak_mb=250.824/230.828` 保留，单位实现未核。ThreadedMotoServer的git show属于base，noop显式git diff为空。

主要风险：把地区常量直接改成East2可能获满分。**唯一优先未来CPU：该候选的原27项评分加已有公开East1 ARN断言，与base/gold对照。** 全部尚未执行；两个结果分开记录，不改变reward。这是针对具体风险的优先顺序，不否定题目价值，也不要求全仓/流/CFN回归先于任何有限模型诊断。

复核纠正旧“26项P2P全改名且不保护旧行为”：实际22改名、4原名，测试体仍有回归意义。当前hints无旧L569链接；实际消息可见性未知。公开封存稿的流测试路径笔误由review更正为 `tests/test_dynamodbstreams/test_dynamodbstreams.py`。

证据：[封存初判](analysis_before_history.md)、[历史差异](old_findings_delta.md)、[独立复核](review.md)、[结构化记录](screening_record.json)。仅 `development_diagnostic`；私有审查材料不可提供给独立solver，未批准正式训练或评测。
