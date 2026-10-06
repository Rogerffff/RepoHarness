# Moto 6114／5960／6408 新测试草案非作者窄核

日期：2026-10-03。审查者：Codex，非草案作者；已读私有测试、部分 gold／负对照及计划，不是 fresh 盲审。仅核本包 `preparation.md`、三题的 `revised_test_draft_v1.patch`、`revision_request.json`、`acceptance_matrix.json`，沿其指针读取最少公开题面、base 测试和调用／fixture 源码。没有复审 5406／6185／7584，也没有重审旧运行历史。

**结论：本轮未发现三份草案的具体误拒、漏检、fixture／调用错误或分组错误，无必须先改的材料问题。可沿已有授权继续受限登记与实际运行验收。新候选尚未评分，本结论不能证明旧正式评分漏洞成立，不能称新版 CPU 通过、材料已发布或具备探针／训练资格。**

## 6114：必须返回请求的集群

- 公开来源为 `runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/public_bundle.json`：题面要求 ARN 和名称均能定位已有集群。base `moto/rds/models.py:1951` 按标识符查对象，`responses.py:584` 将返回对象序列化。草案使用 create 返回的 ARN，没有硬编码账户、region 或 ARN 结构。
- `tasks/getmoto__moto-6114/revised_test_draft_v1.patch:23`–`:26` 同时核 ARN 查询数量 1、Identifier 为 `cluster-id2`、ARN 等于创建值；`:29`–`:32` 对名称查询核同样身份。两个集群先后建立，返回首个集群不能满足第二个 Identifier 断言；只返回一项已不足以通过。
- 原不加筛选返回 2 个、名称筛选返回 1 个的断言保留；原 ARN 查询的数量断言以等价 `assert len(clusters) == 1` 保留。未比较整份响应或对象身份，不会因状态字段、排序、内部存储或 ARN 解析实现差异误拒。
- 分组仍为原 1 F2P＋34 P2P，共 35 条；没有新增节点。acceptance_matrix 的 wrong-first 原分 1 是材料引用的已有事实，本轮没有重审其历史日志；新版 0／1／0 仍是待执行预期。

## 5960：独立 GSI KEYS_ONLY、完整投影与原表保留

- 公开 `runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-5960/public_bundle.json` 明确要求 GSI 的 INCLUDE／KEYS_ONLY scan 返回投影属性。base `moto/dynamodb/models/table.py:802` 的 scan 返回原 items，`:39` 的 index.project 包含表键、索引键及相应投影规则；`responses.py:754` 的实际 scan 输出 Count 和 Items。新增不同表键 `id`／索引键 `gsi_id` 的用例符合该语义，未要求隐藏的新能力。
- `tasks/getmoto__moto-5960/revised_test_draft_v1.patch:25`–`:56` 新增独立 `@mock_dynamodb` 方法，使用 us-east-1、PAY_PER_REQUEST、有效表名／索引名、两条完整 AttributeDefinitions 和两行已含索引键的数据。不缺必需吞吐配置；既有 base 的 GSI fixture 也使用 PAY_PER_REQUEST。调用 `boto3.resource.create_table` 获得 Table，并用该 Table 的 put_item／scan／get_item，调用形式相容。
- `:49`–`:54` 同时验 Count、实际 Items 数为 2、两行完整字典精确等于表键和索引键，按 id 排序而不限定扫描返回顺序。额外 payload、缺键、漏行或重复行均不能通过。`:55`–`:56` 逐行 get_item 复读完整原表，能检出通过原地删除 payload 获得投影的破坏性实现；不要求 deepcopy 等具体路线。
- 原 INCLUDE F2P 的 query、投影内容断言保留；`:9`–`:22` 补 scan 数量与原表复读。原 LSI F2P 方法应用前后 AST 完全相等，其原 scan 断言也保留；所有旧 P2P 和顺序保持。
- 新方法只追加为 1 F2P：原 2 F2P＋155 P2P → 新 3 F2P＋155 P2P，共 158 条。没有将预计 base 失败的 GSI scan 行为塞入旧 P2P。实际 collection／参数节点合键／parser 绑定仍待发布后的正式证据，本轮不改 parser 或参考清单。
- `omit_keys_only` 在矩阵中标为 constructed_negative_unrun、original_reward_observed=null，并计划单独复查原材料分数。静态源码支持其漏做 GSI KEYS_ONLY 投影的推导，但不证明旧正式漏判已实测成立。

## 6408：完整数量与两图标签归属

- 公开 `runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6408/public_bundle.json` 的复现先创建两个已有 manifest，再把共享 tag 从第一图移到第二图。草案沿相同路径，不扩大到目的 manifest 尚未创建的邻接问题。
- 已核 base `tests/test_ecr/test_ecr_boto3.py:20` 导入的 `test_ecr_helpers._create_image_manifest`，以及 `moto/ecr/models.py` 的 put_image、batch_get_image 和 describe_images 返回结构。两个 manifest 仍沿用原题／原私有测试的随机 helper；本轮未新引入随机机制，也不宣称 fixture 是确定性生成。
- `tasks/getmoto__moto-6408/revised_test_draft_v1.patch:59`–`:62` 验一次单 tag 查询无 failures、完整 images 数量为 1、目标 manifest 正确。只反转返回列表不能掩盖仍返回两项的问题。
- `:65`–`:77` 验仓库完整 details 数为 2、digest 数为 2、digest 集合恰等于先前两个 manifest 对应的实际 digest，并对第一图 `{image_001}`、第二图 `{image_002, mock-tag}` 逐图核标签数量和完整集合。可发现删除来源整图、丢来源其它 tag、丢目标旧 tag、共享 tag 两图都保留和重复 tag；既不依赖 describe_images 顺序，也不依赖 imageTags 顺序。
- 原私有测试主体的 AST 是新版该方法的完整前缀，原全部断言保留；全部旧 P2P 不变。分组仍 1 F2P＋95 P2P，共 96 条。
- reorder_only 的旧正式分数仍为 null，矩阵计划先核原材料，并在已被旧 P2P 拒绝时才定向补整图删除反例。这是合理的待验安排，本轮不把构造反例等同于已证旧漏洞，也不要求机械增加候选。

## 本轮实际静态检查与停止条件

仅运行标准库文本／JSON／SHA256／AST 检查；没有导入 Moto／boto3、执行项目／测试／SDK、CPU 验收、网络、SSH、容器、安装、生产修改或旧历史复审。

| 核对 | 6114 | 5960 | 6408 |
| --- | --- | --- | --- |
| 源材料 7 项＋矩阵 patch 2 项 SHA／长度 | 9 项匹配 | 9 项匹配 | 9 项匹配 |
| 原 patch、参考清单和 base 与源 grading／public 相符 | 相符 | 相符 | 相符 |
| 原／新 patch 按统一 diff 上下文在内存中精确应用，AST 可解析 | 完成 | 完成 | 完成 |
| 指定变更方法外的全文件 AST 保留 | 相等 | 相等 | 相等 |
| proposed = original + added，次序与矩阵数量相符 | 35 条 | 158 条 | 96 条 |
| 新节点／新断言真实执行及候选评分 | 未执行 | 未执行 | 未执行 |

本轮补丁身份（SHA256）：6114 `fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f`；5960 `b9a656bde376f6fefa3dd33b16dad74704b50213795b3c52dfcecfa3c57c296e`；6408 `00546841fca20f0b6b781fb49124370d0dab60bf99fdcd01e55aa947b4b65365`。

停止条件：三个指定窄核问题已有静态答案，未发现必须先修的草案问题；由题主／共用维护者继续既定登记、完整逐参考 CPU 验收与相应 actor 检查。新增方法收集、有效正对照、新反例原／新分数均仍未知，需真实运行后收口。作者离线检查未被当成本轮项目运行。仅新增本报告，未改题主材料或生产文件。
