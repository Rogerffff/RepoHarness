# pydantic__pydantic-8511 — 历史主张复核

2026-09-21。协调者确认前稿存在并登记 SHA256/保存时间后，才开放本题 history/refs.json。前稿未修改。只读取其中明确列出的 09-16 L1 与 09-20 pydantic_pilot 本题记录，没有沿旧记录继续读其它题、总报告、catalog 或 verification 汇总。

路径缩写沿 `analysis_before_history.md`。两份历史原件分别为 `R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8511.json`（H16）与 `R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-8511.json`（H20）。

| 旧主张 | 处置 | 本轮决定性证据与边界 |
|---|---|---|
| 题面与 F2P 的 repr 契约一致 | 确认 | 当前 public prompt、Field 明示 repr 参数（fields.py:625,670）、test.patch:29-38；原始 noop:867-874 在隐藏字段负断言失败，gold:831-832 通过。 |
| Python<3.10 支持与 getattr 容错是题外 scope creep（H16）；H20 推翻此说 | 确认 H20 对范围的纠正 | pyproject:46-50,64 声明旧 Python 支持，repr 是公开 Field 功能；要修该环境中的功能必须覆盖 <3.10。不能因为 helper 重构就判越界。但“属需求内”不证明实现无回归：前稿 G1 是独立的具体继承风险，仍待 CPU。 |
| 必须新增 compare/hash/metadata 透传断言（H16）；H20 推翻 | 推翻 H16、确认 H20 | 本轮新增读取 Field 完整签名609-641及 extra处理736-744：没有这三个 stdlib 参数，未知额外项进入弃用警告/json_schema_extra。题目未要求新增这些功能；不把它们当验收缺陷。 |
| Field 默认值/工厂只有薄弱兜底 | 部分确认并细化 | 已读补丁全部工厂断言与 P2P defaults/schema/signature/alias/继承正文；两种工厂确实受到 P2P 保护。仍缺 required/工厂 FieldInfo 的无本地注解子类，以及默认 Field repr=True 的直接表示断言。不能用同文件169条概括所有组合。 |
| 旧安装 rc=2、必须联网是当前阻塞（H16） | 在已引用 grader 配方范围内过时 | 09-19 两条原始 ledger:1、已复算哈希的原始日志：deny_all、uid54322、build-wheels、editable安装和测试依赖安装均rc0。对正式actor仍未知；旧原始失败日志没有再读，不评价其当时真假。 |
| gold 169 PASSED +7 SKIPPED可表述全部运行（H16） | 数量表述纠正 | 当前原件收集180项，gold169 passed/11 skipped，noop168 passed/1 failed/11 skipped；parser给176条而非真实执行总数。所有169个冻结参考均命中；10个>=3.10测试和1个不支持的stdlib+Field组合均在参考外。 |
| 同文件169条足以 ready_for_probe（H16）；H20确认且推荐普通探针 | 不沿用该准入状态 | 该数量支持核心和已列回归，不能代证actor。前稿发现 G1 静态回归嫌疑，建议先跑单一继承矩阵。维持 needs_review/static_review、development_diagnostic；并非确认gold错误或拒绝题目。 |
| 漏扫0命中等于“无泄漏”、与6126是不同修复（H16） | 未核实 | 本轮未审实际镜像完整资产/Git历史，也未跨题读取6126。公开导出无.git只证明材料导出形状，不能延伸成运行镜像无答案或完整题间关系结论。 |
| H20 “尚无证据说明 getattr 容错造成越界行为” | 保留其历史时间范围，增加新嫌疑 | 新证据是 gold.patch:39-56、collect_dataclass_fields:281-292、空子类继承 P2P只用default=1的组合分析。没有当前执行反例，因此不能宣称已推翻H20的运行事实。 |

历史阅读没有改变前稿 G1/T1/V1、actor未知或唯一优先实验；只是核准并明确拒绝 H16 的 compare/hash/metadata 扩题建议，纠正将 parser skip 数当全部执行数及旧 ready 状态。没有在本轮运行任何项目代码。

唯一优先实验仍为前稿中的完整类定义：Python3.8，同配方、base/gold/本地annotations窄修正版；父类分别使用 Field()、Field(repr=False)、Field(default_factory=lambda:3)、Field(default=3)，子类不定义任何本地注解，核创建与校验结果，并与官方得分并列。可增加3.9作为后续确认，但不是本轮已执行事实。
