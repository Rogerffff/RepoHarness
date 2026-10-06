# pydantic__pydantic-5386 独立交叉复核（release后）

## 结论与分歧

采纳主审和公开读者的主结论：5386存在公开接口未定、私有验收固定新名称的误拒机制，以及未测试字段可用性的核心漏测。保持needs_review，不作无争议评测候选。与独立初判无实质技术冲突；下一步优先级作明确收窄：**先由规格维护方确定字段就绪接口与可接受方案**，再安排actor字段读取烟测。仅修好actor入口无法解决这个验收争议。

|复核项|采纳/收窄及依据|
|---|---|
|公开需求|采纳“定义时读取字段及examples”，而非默认强制所有字段有示例。源码ModelMetaclass在type创建后才set_model_fields，与公开读者描述一致。回读fields.py:291–323确认仅examples参数，原example不能当作可运行复现；修正草图不应扩成额外兼容任务。|
|新增断言与反例|test.patch全文只有精确calls列表，MySubModel无字段。早调用同名hook的反例机制成立，但未运行完整反例候选；不能声称已满分或测得误拒率。kwargs保留/普通hook不重复有旧行为依据，新hook精确名称没有。|
|gold与27|采纳字段收集后父类分派的局部正确性。主审27=pass的note限此目标路径；我的初判27=unknown按完整性口径。接受局部pass可保留，最终描述必须同时写完整性未知；不是已经证明所有MRO/泛型或前向引用场景正确。complete_model_class可能False已由原源码证明，不等于该时点一定能实例化。|
|P2P|主审真实语义覆盖只5项，card准确，未把106个状态当完整assert审查。我的初判读过更多main.py测试主体，但它们也没有进入新hook读字段，不能消除缺口。|

## 历史复述审核

L1 checks23/24确实指出新名称、classmethod/super协议缺公开依据；pilot首项确认。delta正确保留机制并排除L1“模型不可能猜到”“只会学猜PR命名”的未经模型验证推断。L1 check25主要指多层/泛型薄弱，pilot明确指出空字段和早回调负例；delta没有把pilot这一强化内容错归为L1已做运行。L1把广泛元类影响记check26 issue不足以证明回归，delta收窄unknown合理。

对L1“model_fields为空”的收窄为可能缺属性或继承映射正确。旧hints实际交付、stage1安装失败详情和R4不在已核原件内，delta均标未核，没有将历史来源声明当actor事实。pilot中的跨题源码包含关系及自动同簇争议仅核其文字，未沿链接验证；不能使用本复核证明跨题关系不存在。旧install rc2不再阻断已引用09-19修订grader，但actor开发仍未知。历史L1/pilot被准确复述，没有发现改变核心结论的误述。

## 原运行和可执行后续范围

独立初判已经逐expected状态核106 P2P，两次全部PASSED；唯一F2P noop日志591/597仅有普通hook记录，gold630通过。两次159 collected；noop120 passed+1 failed+29 skipped+9 xfailed，gold121 passed+29 skipped+9 xfailed，parser116。不是字段读取动态验证。主审card计数一致；skip/xfail和expected身份差异被保留。

回读run_refs指向的image/build及recipe记录确认本地wheel层和editable安装方案；gold日志setup 264–269/276记录apply_rc=0、恢复1个预期测试文件、无absent/irregular。它仅证明此文件恢复与该运行成功，不证明整个fixture树或实际actor干净。初态pyproject的[tool.pdm]/pre-commit改动不是gold，原git diff和projection一致。

唯一优先：规格维护方决定是否把字段就绪hook明确为公共契约以及接受哪些方案；本轮不改题面/测试。后续私有诊断可检早回调负例，公开actor验证应使用Field(examples=...)并在最终公开接口内读取继承和新增字段，而不只复跑空类calls。未执行、未派发任务二。

## 复核程序、结构字段与证据边界

本稿仅在 root 明确 cross_review release 后形成。已读本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json 五份开放稿；先按 history/本题/refs.json SHA 验证再读获准历史记录，未追读其跨题链接、共享R4、stage1或旧探针原件。没有改初判或其它角色文件；本阶段仅写本题 review.md。宽输出截断后，关键正文、结构字段及争议处均定向重取，未以截断输出冒充全文核对。

结构核验：15个必需顶层字段齐全；40个checks均含status/evidence_refs/by且状态合法、实际by标为主审；issues均含category/scope/evidence_refs/proposed_action/status，并区分static inference、缺当前actor观测与未知风险。facts_ref两角色的run_id、started_at_utc、image_id_actual、scripts_digest、policy、budgets、install、test、report、resource、projection与原ledger逐字段相同，parser字段与原verdict_diagnostics一致。初判SHA与code_snapshot_ref记录相同。source tag/expected manifest与derived实际image ID分列；version是grading原字段，未冒充导入包版本。引用可以追到本题run_refs及账本第1行，未发现原运行身份或计数抄错。

check1/2/6/9/13/16–21/37的pass均有明确局部条件：固定静态版本、指定09-19修订grader、该gold源码投影、该受测文件恢复、原测试身份及安装/wheel修订。接受这些局部证据，不把pass聚合成当前actor资格、完整环境可恢复或任意候选安全交付证明。27若给pass也只能读其note限定的目标路径；完整性/无回归仍未知。28仅证明建议可回溯公开目标/旧契约，不授权改评分。主审初判§7对33写not_checked，结构稿改为unknown并解释无真实CC轨迹，这是合理后稿澄清；建议最终汇总采用unknown，勿更改封存原稿。

当前actor消息、public_hints交付、初始HEAD/status/diff/来源规定变更、忽略资产、准备后状态、UID/HOME/cwd/PATH、导入、依赖和权限、真实image ID仍unknown/null；6的历史pass与这些unknown并不矛盾。29实际actor答案可见性unknown，审查暴露另列usage；40保持unknown，封存和独立复核不能证明无漏检/误拒或抽样偏差。未查的重复/并发/控制面/跨题划分不继承旧结论。

file_rules.additional_exclusions=[]、revision_refs=[]，没有新路径禁令或题目修订；disposition.scope=static_review、state=needs_review、formal_admission=false、usage.intended_use=development_diagnostic与当前证据相符。tokens/usd/current_cpu_seconds=null，无项目runtime实验。record内reviewer_status和card的“reviewer未读”是主审落稿时状态，协调者收口时应引用本复核结果更新后稿；本 reviewer 不代改。

## 历史身份与初判封存

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-5386.json`，SHA256 `fc5978e797c2bbbc5bcf606de3d3e2cb41a0fdeafc73f1f24331cdc54c87a8ce`（先核hash再读）。
- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-5386.json`，SHA256 `ef2bb4cbea0c98add062d1404bed5b66062fb1b3e388533dcd30777ce8105a41`（先核hash再读）。

reviewer_initial.md SHA256 `32a1c0e83e351a7e6c36f1668fc9c506d864bfb66da2fbc853adf2d084782677`，本阶段复算一致，封存稿未变。

本阶段授权暴露增量：本包三题开放的15份角色稿、refs明列5份历史记录及本题原件定向复核；不代表actual actor暴露。报告与gold/隐藏test/私有历史不得给独立solver。本稿只支持有范围的静态开发诊断，不批准训练、正式评测或ready_for_probe。
