# python__mypy-10424

目标是在 base `4518b55663bc` 上修复元类比较把 `Type[C]` 错缩窄为 `<nothing>`。建议保持 `needs_review / static_review`，仅作开发诊断；先验一个具体漏测候选，再讨论是否修订参考集。

| 要求/旧行为 | 依据与测试 | 结论 |
| --- | --- | --- |
| 元类正分支保留 Type[C] | 题面；唯一 F2P 的 `is M` if、`is not M` else | 历史 noop 两处 `<nothing>`，gold 通过 |
| 另一分支及合流保留类型 | 非 final 比较规则；另三条 reveal | F2P 内有保护，不能说只有单一负断言 |
| 普通类型比较仍能缩窄 | 公开 `testTypeEqualsNarrowingUnionWithElse`、`testTypeEqualsCheckUsingIs` | 未纳参考、未执行；全部禁用比较缩窄可能逃过评分 |

八方面已查公开要求、版本材料、全部新增断言与 runner/默认 stub、实现自由度、相关旧行为、gold、开发需求、官方恢复及暴露范围。跨题重复关系、完整元类边界、真实消息、actor 与模型能力未验。详细证据见 analysis_before_history；历史前稿保持不改。

09-19 原始账本/日志确认真实数据驱动 case 执行：F2P=1、P2P=0；gold 1 passed，noop 因类型输出错误失败，9492 项仅被收集后排除。安装均成功、无参考缺席。配方仅预置三个固定构建 wheel 并禁 pip 公网，未改评分语义。它证明派生 grader 条件，不能证明 actor 已消费该环境。

gold 只对 TypeType 与元类 Instance 保守处理，没有发现缺交付依赖或已证实回归；测试也不强制改 meet.py。旧报告的“一行就满分”仍无候选运行证据；把等价 `is M` 分支视作题面缺口、按同文件归同族均不沿用。独立 reviewer 已完成，认可上述有界结论。

唯一优先 CPU：base/gold/令 `find_type_equals_check` 直接返回空映射的错误候选，对照原例、冻结 F2P 及上述两个公开旧测试；只有错误候选获原 reward=1 而旧缩窄失败，才能确认假阳性。没有执行该实验。审查已见私有测试、gold 与历史结论，产物不得给 solver；额外文件排除为空。

复核补记：主审与reviewer在读历史前分别发现同一普通收窄风险；首个CPU仅需两个已有Any/Union case。三个预置wheel不是完整依赖锁，须保留固定base镜像初态；精确候选diff和CPU命令见 review.md。原稿封存，actor及当前候选得分仍未知。
