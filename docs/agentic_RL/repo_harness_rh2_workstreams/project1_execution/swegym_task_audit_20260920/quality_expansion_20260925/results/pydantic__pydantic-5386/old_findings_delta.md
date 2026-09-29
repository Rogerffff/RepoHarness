# pydantic__pydantic-5386 旧发现对照（明确release后）

初判SHA256 `f6313f84d67dd0f2f8e127c8d8090cb5715111128dabb505ea35d3b795caeb9f` 已核保持不变。2026-09-25协调者明确释放本题history后，仅读取refs.json sources所列以下记录，不沿其链接扩读。H1=L1_pydantic；如有H2即pydantic_pilot。

- H1: `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-5386.json`；SHA256 `fc5978e797c2bbbc5bcf606de3d3e2cb41a0fdeafc73f1f24331cdc54c87a8ce`，先核一致再全文读取。
- H2: `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-5386.json`；SHA256 `ef2bb4cbea0c98add062d1404bed5b66062fb1b3e388533dcd30777ce8105a41`，先核一致再全文读取。

|旧主张（记录/字段）|本轮判断|决定性证据与收窄|
|---|---|---|
|L1 public_view：定义时model_fields为空，属于特性请求|收窄|main.py:109先创建类、148才收字段，可能缺属性或看到继承映射，不能一律称“空”；特性请求/bug分类不决定可评分性。|
|L1 checks1/2：材料同题、base无能力|确认指定范围|grading/base身份、gold/test原件一致；09-19 noop目标失败。日志只证明该命名钩子未调用，不证明用户字段场景实跑。|
|L1 check3：语法错误、v1 API和隐藏hints使实际输入质量差|部分确认/其余未核|user_prompt确少class且单数example不匹配所读Field接口。公开意图仍可辨；actual actor消息及历史hints交付未知，不由计划模板给check3判已验。题意争议归23。|
|L1 checks23/24；pilot old_claim_reviews[0]：固定新名称、类方法、super协议没有公开唯一依据|确认|test.patch精确调用__pydantic_init_subclass__并比较轨迹；题面没有该接口。kwargs保留有旧普通hook契约支持，但不能从它推导新名称。|
|L1 issues.spec_underspecified_api：模型“不可能猜到”，任何替代均拒；pilot[1]收窄|采纳pilot收窄|另一名称或只重排原hook的实现会被此接口测试拒绝，是静态机制；不是所有合理代码形状都会拒，也无真实模型概率证据。不作“不可能解出”的结论。|
|L1 check25/26：末尾加调用即可通过，未测多层/泛型；pilot[2]指出空字段|确认25，26收窄为unknown|两测试类无字段；最关键漏测是回调在set_model_fields前仍可能过。影响元类全路径与未测边界不足以证明gold造成回归。多层泛型仅合理回归面，不全升级新要求。|
|L1 check27：gold自洽无题外改动|确认目标范围/收窄文案|gold父类分派在字段设置后，源码路径支持目标。但complete_model_class可能False，“fully initialized”不保证模型可实例化；完整正确性未证。|
|L1 check5：同测试/源码文件即同侧；pilot[3]否定自动同簇并给出跨题包含证据|否定推理；具体关系未核|共文件不是答案复用证据。按授权未读取其它题/提交，旧记录中的包含关系不作为本轮已核事实，不沿引用扩读。|
|L1 check6/11 install rc2、需网络；pilot[4]说已替代|确认对修订grader过时；旧失败细节未核|run_refs指定本题09-19两账本/原日志：安装RC0，deny_all，wheel层；不代表当前actor可安装或任何依赖无需网络。未重读stage1旧失败原件。|
|L1 check7无外部资产、4可改范围pass、file_rules无排除|收窄|最小用户路径没有额外数据/服务需求；依赖与actor资产/写权限未知。指定gold只投影main.py及单测试文件恢复成立，可保留additional_exclusions=[]，不能证明任意交付。|
|L1 check29无泄漏；check31 R4残余面|29改unknown；31未核|实际actor可见性未取得，私有审查暴露属授权usage。R4共享材料未授权读取，不能继承其漏洞结论。|
|pilot environment verified_pair/边界、recommendation needs_revision与两项next_action|确认历史pair边界；不自动继承标签|初判已独立得出规格维护优先。记录needs_review/static_review，先定义公开接口，再评估字段断言；不修改生产题面或评分。|
|pilot unknowns、verification_scope、formal_admission=false；旧costs|确认本轮未作模型/替代运行；旧探针细节未核|旧记录自述纯Python探针未追读原件，不升级证据。本轮成本unknown/null，不继承旧16分钟；无正式准入。|

## 对初判的影响

历史阅读没有改变初判的主要技术结论和唯一优先下一步。后稿明确把“所有替代均误拒”“模型不可能猜到”等过强表达排除；初判check26本已unknown，不升级。

决定性本轮证据路径、行号与执行条件均见同目录analysis_before_history.md §§1–8及本题RUN/private/run_refs.json。原日志只是指定09-19grader，不是actual actor；旧记录引用但未核的跨题、stage1、R4、探针原件均明确未核。未读reviewer/其它包/根汇总，尚无独立reviewer分歧可报告。全部本轮行为仍为静态，未改原題/测试/gold/评分，未运行/派发任务二。
