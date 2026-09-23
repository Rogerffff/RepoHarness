# getmoto__moto-7584

固定 base `cc1193076090f9daf90970db286b6b41581dd8bc`。目标是 application Subscribe 拒绝不存在 endpoint，包括题面明确的先订阅、删除、再订阅。建议 `needs_review / static_review`；仅作 `development_diagnostic`，暂不列能力探针候选。

| 需求 | 决定性依据 | 结论 |
| --- | --- | --- |
| 删除后首次订阅应拒绝 | 唯一F2P `test_publish_to_deleted_platform_endpoint`；NLOG:619-622 | no-op未抛异常；gold通过该路径。 |
| 已订阅后删除再订阅应拒绝 | prompt:23-39；gold.patch:5-18 | F2P省略第一次订阅，gold在查重早返回后才校验，静态上漏修原例。 |
| 错误正文使用请求ARN | prompt:4；test.patch:41-44；models:347 | 隐藏断言多加`arn`，形成`arnarn:aws:...`；公开合规实现有具体误拒疑点。 |
| 保留endpoint生命周期与NotFound | 全部19个P2P已读 | 两角色均通过；这些测试没有成功application Subscribe，不等于订阅回归全过。 |

八方面已查：题意与静态输入、S2版本/初态、全部新增断言及fixture、合理替代解、相关调用者/旧行为、开发条件、官方恢复/投影、用途与暴露。相关公开subscriptions选段已读但不在此次执行选集；完整SNS/CFN回归、真实actor、重复稳定性、运行可见答案与基座能力未验。

09-19真实RH2派生grader以54322、deny_all完成离线editable安装，gold20通过/reward1，noop19通过+目标失败/reward0。镜像COPY构建工具wheels本身不是安装证明。正式actor仍指public image/54321；candidate.apply_user=54321只代表应用补丁阶段。实际激活、权限、消息及派生配方消费待验。

`test_globs=()`；官方精确恢复`tests/test_sns/test_application_boto3.py`，gold的`moto/sns/models.py`已纳入投影。额外排除为空。历史旧安装rc2已被派生grader对照覆盖；历史把gold注释当作AWS事实、据此要求旧订阅继续成功的解释不采纳。标记和注释不等于本轮AWS实测，6355关系线索未独立核实。

唯一优先下一步：隔离CPU中用已有base/gold与一个公开合规候选，对照题面原例、有效订阅和原冻结评分；预计可同时区分gold漏修及精确消息误拒，尚未执行。独立reviewer已完成并支持该用途限制。完整路径、日志行号、证据限制见封存初稿；历史差异另存，未回写初稿。

独立复核补充：本题后期base已含5134的缺键/存在性机制和5752的标签列表匹配路线；这是版本包含关系，不等于重复题或已证运行泄漏。总协调者已核对应源码，旧6355关系仍未知。最终复核见[review.md](review.md)。
