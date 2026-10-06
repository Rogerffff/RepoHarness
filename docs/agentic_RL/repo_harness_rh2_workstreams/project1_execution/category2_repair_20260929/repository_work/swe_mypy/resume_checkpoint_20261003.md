# SWE mypy 恢复检查点

2026-10-03 04:31（Asia/Singapore）。用户已批准三方协作与继续实验，恢复通知接替行政暂停。本包仍负责10174/15184、cpu-a；普通进度只写本包与总账。未启动新的CPU作业、后台重试或子agent。

当前入口为 [preparation.md](preparation.md)。已用总账工具`todo/show`核迁移事实，再按revision更新两题自己的progress：10174原请求claimed，15184新发布请求queued；新请求提交通知的实际工具回执已登记notice。共用JSON没有手改。共享CPU文档当时仍保留派发门，不自行移除。

10174保留原请求`swe-mypy10174-strict-equality-v1-20261003`及输入SHA `117617f74e54c379022cb43e9679d0af07d3465c9f0c05eb03a33679db3c5f7c`。GPU intake已核R6 CPU0/1/0及四参考证据可接收；兼容freeze与实际GPU派发由GPU方接续，当前无本题模型回执，不重复提交。回执returned后先读原件，再ack并用update-task清空active_request_id，不能随回执自动清缺陷阻断。

15184固定[发布输入](publish_request_15184_nested_v2_20261003.json)，SHA `e6e0380752b6a0d7076278a237f6586f2f8dbfab8f2b540aeba031cc4c4db214`；请求`swe-mypy15184-nested-v2-publish-20261003`，版本`mypy15184-nested-v2-proposal-bd8ec9e6c8b6`。原提案bd8ec9…、effective nested_v2 patch e6d5eb…及fresh公开输入字节保持；原正式四对照、私有校准和非作者结果复用。尚缺受信五参考consumer/正式登记与不可变发布，所以准备版本仍blocked，不进入探针。

下一步：等发布回执，核固定材料/五参考身份和cpu-a实际部署；派发门开放后重建prepared，运行noop/gold/always_reject/top_only正式四候选矩阵，按新证据做增量非作者核查。新题面实际solver交付仍需核，不用CC控制prompt替代。等待期间不高频轮询、不通过管理线程转话；发布缺输入或回执直达本owner。
