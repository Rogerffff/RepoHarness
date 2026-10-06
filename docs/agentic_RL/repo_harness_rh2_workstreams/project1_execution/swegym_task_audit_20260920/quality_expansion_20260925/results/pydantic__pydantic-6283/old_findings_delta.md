# pydantic__pydantic-6283 旧发现对照（明确release后）

初判SHA256 `0bc2ac2f9f61d5ebc0af730d6fc005646217a362d5d4f4751ebc292b2322c0a2` 已核保持不变。2026-09-25协调者明确释放本题history后，仅读取refs.json sources所列以下记录，不沿其链接扩读。H1=L1_pydantic；如有H2即pydantic_pilot。

- H1: `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-6283.json`；SHA256 `0282525f595fe6be68e91f52888b7def4ed544b91c7b44de19fea32e5743061a`，先核一致再全文读取。
- H2: `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-6283.json`；SHA256 `a7b3b640f0feaed56f5a75f1cd3c96ac5bc578b6b4839bcfd8499fabd8ccf335`，先核一致再全文读取。

|旧主张（记录/字段）|本轮判断|决定性证据与边界|
|---|---|---|
|L1 public_view、1/2/23；pilot[0]：根模型构造相等诉求明确，根因公开可定位|确认并限定有效内容|root_model:35–37,48–66与main:193–223,773–788支持内部状态差异；09-19目标断言确失败。不能把有非幂等validator的“同一合法输入”强制判相等，construct不验证契约不变。|
|L1 public_view称“题面不可能推出根因”|不作为规格问题|solver可以读公共源码定位；题面不必披露内部修复机制。输入目标足够不等于actual输入已捕获。|
|L1 check3输入完整；4路径支持|收窄|计划题面含对照与示例；真实actor消息/权限未知。已见本gold非测试文件投影，不证明所有候选交付。|
|L1 check24：BaseModel分支或RootModel覆写“都能过”；pilot[0]合理替代|静态合理，运行未核|新增仅输出相等性，无强制文件/if形状；未运行完整替代解，不把“都能过”当实测。|
|L1 check25：private×construct缺测；pilot[1]确认|确认|private/equality既有断言只走Model(42)，construct测试无PrivateAttr组合；P2P选择不含test_construction.py的共享BaseModel回归。不是仅因38条数量少而降级。|
|L1 check25/26把gold解作不再设private；pilot[2]否定|采纳pilot纠正，26=unknown|main:218–223仍优先执行model_post_init；gold只限制无post-init的None fallback。覆盖缺口不证明gold损坏私有初始化。|
|L1提议部分修复能全绿；pilot[3]未核|未核实跑，保留静态机制|不存在授权范围内已运行坏解补丁/日志；不能把“只修无私有分支”写成已获满分。|
|L1 check27两个条件无题外改动|确认目标范围|非root仍走原写入分支；字段集合、默认值、post-init不变。未检全部旧行为，不称完整正确。|
|L1 check5/same_family_split同侧划分；pilot[4]否定按主题自动聚类|否定自动推理，具体跨题关系未核|本轮未读其它题；同文件/RootModel/相等主题不足以证明答案复用或真实留出污染。|
|L1 check6/11旧安装RC2/需网络；pilot[5]已替代|指定修订grader过时；actor unknown|本题09-19pydantic-install-v1两安装RC0，deny_all+wheel；旧stage1失败详情未再核。历史actor PATH/写权限不由grader推出。|
|L1 check7无外部资产、29无泄漏、31 R4残余|收窄/未核|本地操作无额外服务需求，但core/pytest等实际actor资产未知；29实际暴露unknown；共享R4未读，不继承控制面问题。|
|L1 small_oracle_surface、proposed_regression_tests推荐test_main与fields_set一致|收窄选择和契约|本base实际已读相关用例在test_construction.py；字段集合显式可不同且不参与eq，不能强制所有construct fields_set与正常构造相同。要保留显式_fields_set与默认推断语义。|
|L1 ready_for_probe、“补一条即可”；pilot probe_candidate与private组合建议|不继承准入标签/充分性|仅静态候选needs_review，actor公开smoke优先；私有组合是后续相关验证范围，不证明加一条就完备。|
|pilot环境边界、unknowns/formal_admission=false、旧成本|确认限定范围；旧探针未核|本轮无actor/模型/合法替代动态事实，未追读旧verification探针原件；成本null，不继承16分钟。|

## 对初判的影响

历史阅读未改变初判：这是公开目标与验收基本一致的静态候选。保留private×construct和共享BaseModel评分覆盖缺口；不采纳“gold不初始化私有属性”或“坏解已满分”的过度结论。唯一下一步仍为实际actor公开smoke，而非因旧ready标签直接准入。

决定性本轮证据路径、行号与执行条件均见同目录analysis_before_history.md §§1–8及本题RUN/private/run_refs.json。原日志只是指定09-19grader，不是actual actor；旧记录引用但未核的跨题、stage1、R4、探针原件均明确未核。未读reviewer/其它包/根汇总，尚无独立reviewer分歧可报告。全部本轮行为仍为静态，未改原題/测试/gold/评分，未运行/派发任务二。
