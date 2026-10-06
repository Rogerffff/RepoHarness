# getmoto__moto-7584 历史差异

历史门禁在协调者确认初稿 SHA256 `7e72e50b585fb413f2b077c6d557bba96525fedff2a6af35c274995a016263e4` 后开放；初稿没有回写。历史入口为 `runs/swegym_quality_batch02_20260921_v2/history/getmoto__moto-7584/refs.json`，仅打开其指定 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_3/records/getmoto__moto-7584.json`（下称旧记录）。沿原始指针读取 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-7584/gold/offline/a1/{eval.sh,test_output.txt,status_map.json,patch.diff}`（下称 S1）。未读旧包 summary/其他题记录，未运行项目或联网。

| 旧主张 | 处置 | 新决定性证据与影响 |
| --- | --- | --- |
| 题面消息少一个 `arn`，照题面会被精确断言拒绝 | 确认静态冲突；实际替代解判分待验 | `PUB/user_prompt.txt:4` 对照 `PRI/test.patch:41-44`；`models.py:347` 确认请求 ARN 已以 `arn:` 开头。不是仅格式审美差异。 |
| AWS 真实消息一定有该额外 `arn`，是报告者省略 | 未核实 | 旧记录只引用 gold 注释；`aws_verified` 标记和 gold 注释不是本轮 AWS 调用证据。本轮本地 mock 日志不验证外部 AWS 报文，不采纳此事实断言。 |
| 题面没说已有订阅删除后怎么办；应加断言要求继续返回旧订阅 | 推翻 | `PUB/user_prompt.txt:23-39` 正是成功订阅→删除→同参 Subscribe，明确末次应抛异常。旧建议与公开原例冲突，不加入新验收。 |
| gold 正确、位置有依据；在查重前校验是漏测的错误解 | 推翻 | `gold.patch:5-18` 把验证放在提前返回后；`models.py:714-718` 不移除旧订阅。查重前验证是满足题面的一条合理路线，gold 是自然部分实现。初稿已独立发现，历史未改变结论。 |
| 20 项全过证明回归通过；正常 application 订阅有间接覆盖 | 缩小范围 | 本轮已读全部19个P2P及新增函数，没有成功 application Subscribe。P2P 对 publish/endpoint生命周期有价值，却不执行 Subscribe 正例；`test_subscriptions_boto3.py` 相关公开旧测试不在冻结选集。不把普通覆盖缺口自动判坏。 |
| stage1 gold 20 passed/1.34s，同时安装 rc=2 | 确认历史事实；环境缺陷对当前派生 grader 已过时 | S1/test_output:392-422 是 setuptools>=40.6.0 离线构建依赖找不到、make rc2；:438-480 仍继续执行20项并全部通过。09-19 原日志 gold/noop 都完成 make init 两次 editable 安装、RC0，见初稿§4。旧 S1 不是当前正式 actor 验收。 |
| aws_verified 路径会读 SSM/Firebase 密钥，因此本题需秘密资产/应新增准入限制 | 确认条件分支，否定无条件归纳 | 公开 fixture:22-47 只有显式 MOTO_TEST_ALLOW_AWS_REQUEST=true 才走该路径；默认本地 mock。NLOG:592 明示 mock_api_key。最小开发不需要 AWS/第三方密钥；显式关闭在线模式可作为诊断条件，不能由静态分支推出当前发生真实密钥读取或需要新增路径排除。 |
| finally 在 topic 创建失败后可能遮蔽原异常 | 确认窄静态风险；本次未触发 | `test.patch:14-49` 中 topic_arn 在 application 创建之后赋值，finally 仅以 application_arn 判定。本轮已有完整日志达到目标 Subscribe，无该故障；不把此测试卫生风险混成已发生的运行失败。 |
| 测试名 publish 与实际 Subscribe 不符 | 确认，但不单独改题/判坏 | `test.patch:10,34`。阅读测试体足以消歧，名字不改变执行语义。 |
| 6355 的 gold 已逐字在本题 base，必须同组、构成污染 | 未独立核实，且结论过强 | 旧记录称做过反向 apply，但未给该实验的精确原件；本轮未跨题读6355材料。即使上游修复被后续版本继承，也仍需任务关系与评测划分语义，不能自动等同答案污染。保留关系线索，不据此成组。 |
| raw hints 只是复现，无静态泄漏 | 未重新核实原 hints；运行泄漏未知 | 本轮正式 public bundle 的 public_hints 是操作指令；旧记录的 raw hints 未给精确文件。限定 s2/ingest 文件名检索未定位 raw。实际 actor Git/包/挂载未验；不能把旧静态 pass 外推到当前完整可见面。 |

当前结论不因历史标签改变：`needs_review/static_review`，用途仅 `development_diagnostic`；不列 `ready_for_probe`。唯一优先实验沿初稿§6：同一配方下将题面原例与冻结评分对照，用现有 base/gold 加一份公开合规候选同时区分漏测与精确消息误拒。未改题面/测试/gold/reward；正式 actor/54321 的 public-image、实际消息、激活与权限仍待验。历史只增加了安装失败的原始对照及需保留未核实的跨题线索。
