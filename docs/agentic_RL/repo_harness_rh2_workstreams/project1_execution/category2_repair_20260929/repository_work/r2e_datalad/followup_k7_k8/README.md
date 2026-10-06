# DataLad 6b6f：绝对本地路径与 crawler query 增量修订

2026-10-03。088/R7已发布、CPU-c新镜像已构建，noop／C-A／gold各一次实际0／1／0，题主和非作者原件核查通过，仅支持固定版本诊断用途；formal gate限制保留。旧065请求已安全取消并ack；088双模型首轮均正常完成raw0、17键匹配16，题主七维／效率与独立关键核查完成：各自修好原例，却以不同控制流破坏转义冒号本地路径。未发现新材料阻断，成对执行回执已ack并清指针。按最新覆盖优先安排暂缓本题普通追加采样，当前无CPU／GPU补跑依赖；单次稳定性仍未知。065原材料和证据保持原样。

## 为什么补这两项

原公开读者把绝对本地路径和 crawler 模板 query 列为应保留的旧行为 K7/K8；旧调查已有 base/gold/C-A 的执行对照。gold 的广泛冒号判断会把 `/some/dir:x` 解析为 SSH，并把 `openfmri_s3?_url=s3://b/k` 判为 SSH 后抛 `ValueError`。C-A 保留这两项行为。065 正式评分仍把 gold 和 C-A 都判为1，所以满分不能排除这两种已知回归。

历史题卡将它们归为 G1→T3/S2。本次不回写历史严重度或原成绩；按当前 workflow 中“已知影响普通求解或评分的缺陷已处理”的提交条件，先补这两项有公开依据的行为，不能只更换诊断名称放行。

公开依据与原件：

- [原公开读者](../../../../r2e_lifecycle_20260929/results/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/public_read.md) §1.2 K7/K8；[旧结论核对](../../../../r2e_lifecycle_20260929/results/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/old_findings_delta.md) §2。
- 公开 `datalad/support/network.py` 的 URL/`parse_url_opts`/`is_url` 文档与初态行为；`datalad/crawler/pipeline.py:465–469,485–487` 支持模板的 URL 式 query，并实际调用 `parse_url_opts(template)`。
- 原行为对照 `runs/r2e_lifecycle_20260929/inv/datalad_6b6f/pcheck_public4_gold.json`，SHA `53b2cd90f0673be30d61139c2586e2e31c820b8ed67340c790bef15d39b98147`；C-A 同目录 `pcheck_public4_CA.json`，SHA `10b036ece2092beb64b13d74fbdfcd243893d9a4c68847929080fc796dcbd4e7`。这些是历史行为检查，不冒称本次正式评分。

## 精确改动和边界

只在065的私有 `test_1.py` 增加两处断言：

1. 既有 `test_url_samples` 直接核 `/some/dir:x` 的公开字段为 `file:implicit`、path 为原绝对路径。使用已有固定字段 helper，不依赖候选 `URL.__eq__`。
2. 既有 `test_parse_url_opts` 核公开模板 query 返回 `('openfmri_s3', {'_url': 's3://b/k'})`；它检查调用方实际使用的输出，不只检查是否未抛错。

保留065全部原断言；仍不限定 `example.com/path/sp1:fname` 的分类，只要求从字段重建原串。没有要求 SSH query 的新语义，不修 `~` 编码，不更改公开题面、公开说明、expected、runner 或其他隐藏文件。评分仍为相同17键，含固定 FAILED。

见[精确草案](revision_draft.json)、[两处补丁](private/test_1.py.patch)和[私有有效全文](private/hidden_tests/test_1.py)。全文 SHA 为 `7649b82fb114a9bbdfa3a73148c4d8f1ee8bed926dd2d7853c6385379b88c8b6`；隐藏树 SHA 为 `2a62382c32a9def6a9ccf42c27fb938b7e4c0c0747805bafeaa605afce6b4724`。

## 定向验收

本地检查只抽取 URL 代码和断言，用标准库检查草案，不能代替容器或正式17键评分。正式新增矩阵为 noop=0、C-A=1、gold=0，各一次；gold 应分别由绝对路径字段和模板 query 的目标失败拒绝。旧065的四个错误候选证据只复用于未变机制，不冒称在新版本重新跑过。

共用维护者已登记088及不可变R7发布，题主核完905个文件、新构建身份、实际CPU评分和清理；非作者原件核查通过后才提交088新GPU请求。隐藏测试变化不影响公开开发条件，按实际构建事实复用已验CC开发环境证据；两模型实际首HTTP请求的原题面和批准说明均已另核。


当前原件结论见[CPU增量验收](cpu_acceptance_20261003.md)与[非作者增量核查](independent_review_20261003.md)，后续路由/模型结果状态统一见[当前准备入口](../preparation.md)。
