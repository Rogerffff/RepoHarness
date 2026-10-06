# pydantic__pydantic-8567 独立交叉复核（release后）

## 结论与分歧

采纳主审needs_review：两个新增isinstance不能证明公开JSON和值目标，gold无条件内层schema生成的兼容风险待具体对照。与独立初判无实质技术分歧。优先级接受主审更明确表述：**私有未知底层类型+PlainValidator的base/gold构建对照**最能判定gold边界；公开actor烟测仍是独立开发事实需求，不能由私有对照替代。

|复核项|判断及原件|
|---|---|
|需求/公开读者|采纳两种顺序均应用serializer，而不是让不同输入字段值相等。Python always/json-only公开契约支持不只修JSON；回读test_serialize.py:83–146见三种dump及when_used，作为评分外回归，不计入158 P2P。|
|test.patch全部assert|两个isinstance及局部lambda/MODEL已独立逐行读；只返回错误常量str或只修Python可满足这些新断言的必要表象。未执行完整错误候选，因此只叫缺口/可漏测机制，不宣称实测满分。|
|gold路径|validation仍走plain，新增handler为了serialization不是等同执行内层validator。回读functional_validators.py:638–655的InstanceOf fallback、680–689的SkipValidation wrapper，支持分离设计和异常边界；先例不证明gold对所有输入正确。|
|具体兼容风险|独立初判已读_apply_annotations及_unknown_type_schema链，未知Custom类+PlainValidator旧路径不生成基础schema，gold新增handler(Custom)可抛错。主审26/27 unknown恰当；不是仅从覆盖不足推出已证回归。|
|P2P归属|nested、runs_before_field_validators实际用AfterValidator，不能当plain组合证明；主审把它们列为阅读范围而未用作消除缺口。plain/typing_cache/field_name三类都不dump，所见范围确未保护无serializer输出。|

## 历史复述审核

L1 base定位把丢弃metadata写作“排在它后面”，delta纠正为Annotated列表中位于plain之前的内层serializer；与_apply_annotations顺序一致。L1 checks25两个弱点（只查str、无serializer plain仅查validation）被保留；delta另指出JSON未测，确实来自本题公开例与patch。

L1 check26 issue只凭25(b)不足以确认gold已破坏行为；主审收窄unknown正确。L1 check27记无条件handler和没有serializer也委托这两个扩大影响机制，delta没有否认机制，而是拒绝直接把所有变化都叫不合理回归；这比原标签更精确。旧“收紧assert扩P2P后可入”不是充分准入证据，被明确拒绝。

旧check3输入完整、7无资产、29无泄漏以及5本包唯一改文件所以无重复的推理均被合理收窄；只有一个L1原记录获准读取，没有额外pilot或跨题证据。安装旧rc2仅对已引用修订grader条件过时，历史旧失败和R4原件未核，delta如实标注。

## 原运行和后续事实

noop原日志1500执行validators文件，165 collected；1668 failed，1672–1675在bar instanceof str断言显示True，foo断言先过；gold1693 passed。两次expected158 P2P均有PASSED，noop164 passed+1 failed/gold165 passed，parser165，无skip/xfail。card及record计数、rc、条件一致。与原账本核对后，没有误将题面2.5.3/core2.14.6写成base/运行事实；base core2.15.0、运行包2.6.0a1分开。

gold投影只functional_validators.py；历史pyproject增加pre-commit及lock变更是保留来源差异。run_refs指向image/build显示派生层只COPY wheels并设置离线pip环境；不证明当前actor拥有这些资产。gold setup日志1282–1287/1294仅证明一个目标测试文件恢复/apply条件成立。

唯一优先：私有CPU对照普通未知类U配Annotated[U,PlainValidator(...)]在base/gold能否完成类构建，若不同，再判其是否违背合理旧用法；应保存精确异常/退出码，不以“全测试通过”替代该性质。公开actor还需从工作区执行题面JSON样例并核内部False/True及'0'/'1'输出，同时记录实际环境；二者事实用途独立。无serializer输出/warning及with-info/when_used按候选影响范围验证，不要求无目的全仓重跑，不扩张为JSON Schema新功能。本轮未执行或派发任务二。

## 复核程序、结构字段与证据边界

本稿仅在 root 明确 cross_review release 后形成。已读本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json 五份开放稿；先按 history/本题/refs.json SHA 验证再读获准历史记录，未追读其跨题链接、共享R4、stage1或旧探针原件。没有改初判或其它角色文件；本阶段仅写本题 review.md。宽输出截断后，关键正文、结构字段及争议处均定向重取，未以截断输出冒充全文核对。

结构核验：15个必需顶层字段齐全；40个checks均含status/evidence_refs/by且状态合法、实际by标为主审；issues均含category/scope/evidence_refs/proposed_action/status，并区分static inference、缺当前actor观测与未知风险。facts_ref两角色的run_id、started_at_utc、image_id_actual、scripts_digest、policy、budgets、install、test、report、resource、projection与原ledger逐字段相同，parser字段与原verdict_diagnostics一致。初判SHA与code_snapshot_ref记录相同。source tag/expected manifest与derived实际image ID分列；version是grading原字段，未冒充导入包版本。引用可以追到本题run_refs及账本第1行，未发现原运行身份或计数抄错。

check1/2/6/9/13/16–21/37的pass均有明确局部条件：固定静态版本、指定09-19修订grader、该gold源码投影、该受测文件恢复、原测试身份及安装/wheel修订。接受这些局部证据，不把pass聚合成当前actor资格、完整环境可恢复或任意候选安全交付证明。27若给pass也只能读其note限定的目标路径；完整性/无回归仍未知。28仅证明建议可回溯公开目标/旧契约，不授权改评分。主审初判§7对33写not_checked，结构稿改为unknown并解释无真实CC轨迹，这是合理后稿澄清；建议最终汇总采用unknown，勿更改封存原稿。

当前actor消息、public_hints交付、初始HEAD/status/diff/来源规定变更、忽略资产、准备后状态、UID/HOME/cwd/PATH、导入、依赖和权限、真实image ID仍unknown/null；6的历史pass与这些unknown并不矛盾。29实际actor答案可见性unknown，审查暴露另列usage；40保持unknown，封存和独立复核不能证明无漏检/误拒或抽样偏差。未查的重复/并发/控制面/跨题划分不继承旧结论。

file_rules.additional_exclusions=[]、revision_refs=[]，没有新路径禁令或题目修订；disposition.scope=static_review、state=needs_review、formal_admission=false、usage.intended_use=development_diagnostic与当前证据相符。tokens/usd/current_cpu_seconds=null，无项目runtime实验。record内reviewer_status和card的“reviewer未读”是主审落稿时状态，协调者收口时应引用本复核结果更新后稿；本 reviewer 不代改。

## 历史身份与初判封存

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8567.json`，SHA256 `f568e38fe2f5fe45219b162f649a7daabee94d96a8aa19ccb243c84fe5d9de9e`（先核hash再读）。

reviewer_initial.md SHA256 `60ec6800d9ae085479fb340786b313169246bd926a5295bfa5d6cba871df65c9`，本阶段复算一致，封存稿未变。

本阶段授权暴露增量：本包三题开放的15份角色稿、refs明列5份历史记录及本题原件定向复核；不代表actual actor暴露。报告与gold/隐藏test/私有历史不得给独立solver。本稿只支持有范围的静态开发诊断，不批准训练、正式评测或ready_for_probe。
