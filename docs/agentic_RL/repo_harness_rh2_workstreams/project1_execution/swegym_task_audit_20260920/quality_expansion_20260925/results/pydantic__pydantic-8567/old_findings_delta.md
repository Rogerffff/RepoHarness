# pydantic__pydantic-8567 旧发现对照（明确release后）

初判SHA256 `a3b69af95c456ee37c25f7e09541d5a401ef181296d81f440d9bce1632999ffd` 已核保持不变。2026-09-25协调者明确释放本题history后，仅读取refs.json sources所列以下记录，不沿其链接扩读。H1=L1_pydantic；如有H2即pydantic_pilot。

- H1: `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8567.json`；SHA256 `f568e38fe2f5fe45219b162f649a7daabee94d96a8aa19ccb243c84fe5d9de9e`，先核一致再全文读取。

|旧主张（L1字段）|本轮判断|决定性证据与边界|
|---|---|---|
|public_view及checks1/2/23：两顺序序列化应相同、plain验证不变|确认并消除值歧义|题面两字段输入不同，应分别字符串'0'/'1'；不是值相等。base handler链与noop bar=True失败支持缺陷。|
|base定位称“排在它后面的metadata”丢失|纠正方向表述|源码1725–1734构造层叠handler，PlainValidator不调用的是此前内层handler；Annotated列表中位于plain之前的serializer受影响。|
|check3输入完整、4交付范围pass|收窄|计划题面可读，不等于真实actor消息已捕获；gold仅该非测试源码投影成立，不证明任意候选权限/交付。|
|check5本包唯一改该文件所以无重复|不采纳充分性|单文件唯一不能证明无派生/答案关系；本轮未读其它题/数据划分，check5未查。|
|check6/11旧install RC2、只有安装需网络|修订grader条件下过时；旧细节未核|本题09-19两安装RC0、deny_all与本地wheel层；actual actor网络/依赖可用性仍unknown。|
|check7无外部资产|收窄|题面本地CPU即可，但core/pytest/dirty-equals/benchmark均属依赖，实际actor位置权限未验。|
|check24无唯一实现|确认静态范围|断言只看输出类型，无强制wrap helper或修改文件；未实跑合法替代解，不能保证所有合法解不误拒。|
|check25(a)只有str类型，错误str化能过|确认缺测；坏解获分未核|test.patch两个isinstance直接可见；错误字符串也满足新增断言，但未执行错误补丁的整个评分。另新增公开model_dump_json路径缺失，初判已有。|
|check25(b)无serializer的三类plain只验值，test_serialize不在P2P|确认已读区段与选择|test_validators:81–89,164–181,2711–2718无dump；评分只选validators，serialize:83–146有相关模式契约但未入选择。不以158数量作充分性证明。|
|check26=issue，依据同25(b)|收窄为unknown|漏测/改变schema结构不能自动证明不合理行为退化，需要具体base/gold对照或完整静态证明。|
|check27/gold_scope_creep：无条件handler与无serializer时序列化委托有副作用|确认机制，行为结论待证|gold确无条件handler；未知类可进入_unknown_type_schema报错路径；InstanceOf有fallback先例。是否影响具体合法旧用法、无serializer时输出/warning怎样变化仍未实跑，不能笼统宣告所有新委托错误。|
|check29无泄漏、私有测试不为agent可见|29改unknown|静态包分开不证明actual actor挂载/消息；授权审查暴露放usage，测试issue链接未联网访问。|
|check31 R4控制面残余|未核|未读被链接的共享材料或完整grader控制面，不继承issue结论。|
|proposed_regression_tests：任意类对照、无serializer输出、serialize全量、精确值|采纳有依据的局部方向；收窄全量要求|唯一优先是未知类型构建base/gold对照；其它按改动路径选公开回归即可，不机械要求全文件/全仓成功。本轮不执行/派发。|
|disposition_hint needs_review、“收紧扩P2P后可入”与旧15分钟成本|保留needs_review，不接受准入充分条件|当前actor资格和gold边界仍未知；增强断言不是正式训练/评测批准。成本null，不继承旧时长。|

## 对初判的影响

历史阅读未改变初判的唯一优先下一步：未知底层类型+PlainValidator私有base/gold对照。旧record同样提出handler风险，但本轮以独立读到的代码链为依据；check26/27保留unknown，不把旧issue标签当成已证回归。

决定性本轮证据路径、行号与执行条件均见同目录analysis_before_history.md §§1–8及本题RUN/private/run_refs.json。原日志只是指定09-19grader，不是actual actor；旧记录引用但未核的跨题、stage1、R4、探针原件均明确未核。未读reviewer/其它包/根汇总，尚无独立reviewer分歧可报告。全部本轮行为仍为静态，未改原題/测试/gold/评分，未运行/派发任务二。
