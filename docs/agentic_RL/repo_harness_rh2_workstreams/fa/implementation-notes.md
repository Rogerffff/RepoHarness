# FA 工作流 implementation-notes（三节制）

范围：`05-fully-async-execution-plan.md` 的 FA-0~FA-5 实现期记录。每任务一节，
只记重要事项。

## ⚡ 当前权威状态（2026-07-20，每次大轮次后更新——先读这页再读历史）

> 下面的历史轮次是**流水账**：早期结论可能已被后续轮次推翻。凡与本页冲突，
> 以本页为准；被推翻的机制在括号里标注了替代它的轮次。

**阶段状态**：FA-0 完成；FA-1 本机实现完成（codex 轮次 6~14 九轮审查全部
处置，closure 批次已落地）；FA-3 离线/FA-4 对拍完成（接线未做）；
**FA-2A 决策包 v4 已批准（2026-08-07，用户拍板 D1=A 带修订/D2=A/D3=A/
D4=A；D1b 延后清单见决策包 owner_decision）**；**F2-0 纯迁移已完成**
（commit f8580789，测试 917→921：capture_wire/glue→bringup/
docker_sandbox 三模块提升 src，experiments 留带 parity 测试的薄兼容壳，
GPU 链模块路径经壳保持可解析）；**F2-1a 四层身份：完成，codex 终核通过**（e5ddd13a 主体；一审 63e2772c；
二审 P0 触发修复循环熔断→所有权收敛重构 4e704d03；终核仅剩 P1
SessionAdapter Protocol 签名同步，已修）。**F2-2 验收前置登记**：稳定
SID 在 slime closed 集合下不可复用，需 F2-2 的每 physical attempt 新
session_auth_capability 解决（05 计划 F2-2 节已钉验收）。**F2-0b Observability V0：基础字段完成，生产接线未完成**（codex F2-0b
复核 4 P1 修正后的诚实口径——契约与提取器就位，但 43 个事件中生产代码
只命中约 4 个，其余按 owner 分批接线：**服务启动 6 事件归 BringupService
（startup_evidence timeline）**、execution 事件随各切片、model
调用区间填值随 F2-3、group/batch 事件随 F2-5/F2-6）。已闭合：clock_
domain=进程实例（同进程线程可互减，owner_role 区分线程）+ 原始
monotonic 时间戳；ModelCallAttempt 四原始区间（成对 start/end +
timing_clock_domain，**区间⟺domain 双向一致校验**——脱离时钟域的区间
拒绝构造）；server_timing = 严格模型 ServerTiming（白名单六键 + 非负
有限，污染键/负值挡在契约外；提取器只捕 ValidationError，程序错误照常
暴露）；audit 落**双时钟 wall 起止**（wall_start/end_monotonic +
epoch 副本 + wall_clock_domain_id，写 record 时各只读一次）不派生
chargeable。训前处理项（codex 复核二轮登记）：proc-{pid} 非严格进程
incarnation（fork 继承同值/pid 复用），F2-3/F2-4 前改含 incarnation 且
fork 后刷新的 ID；非法遥测计数随 F2-3。**F2-1b Outcome v2 与 crosswalk：
schema + crosswalk 完成（producer 接线不在本切片，归 F2-2 起——见 05
计划完成口径）**；codex F2-1b 审查三 P1 已闭合：① failure category
三分封闭集合（执行事实 7 值 = missing 唯一合法归因池 / grading 1 值 =
present_* 唯一 / 准入·控制·审计 5 值不进 finalize Outcome——staleness
是消费时刻判定，混入会把完整成员算成缺员）+ 13×3 显式矩阵测试；
② v2 强制四层身份（physical_attempt_id 必填、branch_id 必须 None），
crosswalk 加结构性前置门（branch 视角/身份不可重建 → legacy_unmappable，
证据可补 paid）；③ crosswalk fail-closed（证据 evidence_refs ≥1；结果
validator 强制 status ⟺ v2 在场性；permanent_rejection 迁移产物 =
**migrated_audit_only** 独立状态——只读 status/v2 的消费者拿不到被禁
轨迹）。二轮复核再闭 2 P1：④ 提取口改名 **migrated_v2()**（原名
trainable_v2 违反 v1 既有原则"训练资格唯一权威在 EligibilityReport"
——migrated 含 missing 迁移，迁移成功≠可训练；接口只过滤 audit-only
维）；⑤ 身份血缘矛盾 fail-closed（v1 与证据都带 paid 且不一致 →
identity_evidence_conflict/legacy_unmappable，不静默取舍）。非阻塞
递延：termination×failure 完整交叉表未拍板（schema 暂允许
completed+harness_crash+missing 组合），F2-2 producer 接线测试先行
兜底证明真实路径不产矛盾组合（05 计划已钉）。
`contracts/fa_runtime.py` 新增 TerminationKind 五族（与决策包 D1a 逐字
一致，集合等式测试保证并集=全集且两两不交）+ RolloutAttemptOutcomeV2
（completion 三值事实层 present_complete/present_truncated/missing；
三层分离钉子 model_call_regeneration_exhausted→model_proxy_failure→
max_regenerations_exceeded；勘误 2 通道 = reward_unavailable ⟺
task_outcome=unknown，评分基建故障不倒写 completion）；v1 冻结不改。
`contracts/outcome_crosswalk.py` = v1→v2 穷举规则表（42 组合全覆盖测试；
无证据不捏造→legacy_unmappable；permanent_rejection 永不映射 missing，
可迁移时落 present_* + legacy_admission_verdict 审计传递）+ 双版本读取
read_rollout_attempt_outcome。registry 注册 v2；"正式链只产 v2"守卫 =
src 扫描测试（v1 构造只许出现在契约定义/registry/crosswalk 三文件）。
待 S2 协调项：GradingFailureCategory 新值 test_execution_timeout
（contracts/grading.py S2 线程优先，D1a 第 2 条要求的三条件构造门随
其落地）。**F2-2 session capability + 会话面排空 + Outcome v2
producer：完成（codex 复核 3 P0 + 3 P1 全采纳后的语义）**。① 三层身份分离（复核 P0-3 重构）：
**公开稳定身份**（trajectory_id/rollout_execution_id）/ **非秘密会话
身份**（internal sid = `s-{paid}`，每 attempt 唯一——slime store/
closed/`_sid_turn_count`/日志/X-SMG-Routing-Key/异常消息全用它）/
**秘密凭证**（capability token `cap-{128bit}` = CC 的
ANTHROPIC_AUTH_TOKEN，**只做认证**：guard 验证后把 Authorization 重写
为 internal sid，token 不进任何下游；token 绑定的会话拿 internal sid
直接当 bearer 也被拒）。钉死验收四条全过（slime 源码语义钉住 + 忠实
复刻行为验收两层证明）；凭证卫生验收 = **完整持久 audit record 全文
扫描**无 token。poison 按 internal sid 键控 = 按 attempt 绑定（轮次
14 设计规则 1 病根治愈）。② 会话面排空（复核 P0-1 拆分）：事实拆成
`session_plane_drained`（revoke→drain→poison/边界断言，已实现）与
`runtime_quiescence_confirmed`（D1a 完整屏障：sandbox scope 终止/后台
进程归零/不可变 snapshot/只评冻结副本——**未落地恒 False**）；
completion 推导只信后者 ⇒ **完整屏障落地前正式模式不启动（启动闸门）
或显式 audit-only 探针下只产 missing + reason_code=
runtime_barrier_unavailable，不产 present_\***。正式链
adapter 缺 revoke_session 启动 fail-closed（不再 getattr 跳过）。
③ producer：终态 **CAS**（每 physical attempt 恒一条 Outcome，deliver
失败不追加/不改写——复核 P0-2）；slime exit=-1（EXIT_TIME_BUDGET_
EXCEEDED）→ termination=hard_wall_timeout（不再误归 harness_crash/
completed，不走 nonzero 拒绝，处置留 D1b——复核 P1-4）；正式路径身份
字段（group_index/prompt_group_id/member_slot/seq）不全时**不产 v2 不
补值**（entry 已戳 rh2_group_index 贯穿——复核 P1-5）。F2-2 递延：
workspace 冻结面（owner F2-3+，落地后 runtime_quiescence_confirmed 才
允许 True）；watchdog 本体（FA-2B/D1b）；outcomes assembler 消费
（F2-5）；**长运行无界状态**（复核 P1-6：orchestrator.audits/
outcomes 两内存列表 owner=F2-5/F2-6 durable manifest 落地时改滚动；
slime closed/`_sid_turn_count` 两容器 owner=FA-5 容量测试 + adapter
轮换机制，绑定 `rh2_formal_training_allowed` 闸门前置）。**F2-2 复核二轮（2 P0 + 3 一般 + T0 修订，全采纳）**：
① 正式路径完整屏障前 **audit-only 收口**——capture 关账后不评分（活动
workspace 上评分违反"只评冻结副本"）、不交付（abort 形状，collector
_member_ok 拒绝），Outcome=missing + reason_code=
runtime_barrier_unavailable；S1 兼容路径不变；② producer missing 归因
过滤到执行事实集合（评分故障不再制造内部 ValidationError，真实故障经
failed_component/evidence 保留）；③ fingerprint 机制彻底删除 + 模块
docstring 改为三层身份定稿（秘密只认证，标识符不保密）；④ T0 勘误 3
落地：RuntimeFailureCategory pre-formal 原地修订 +
runtime_quiescence_failure（仅屏障执行失败；未实现走启动闸门）+ D4
表 1 行 + 集合等式测试；⑤ DuplicateActiveSessionError 改判永久身份
碰撞守卫；中毒 SID 拒 register 挡板解除（poison 已按 attempt 绑定）。
**F2-2 复核三轮（2 P0 + 3 P1，全采纳）**：① 正式模式改**显式信号**
（require_real_weight_versions，不用"是否有 paid"推断）——修复
fail-open：正式配置 + 身份注入故障时曾绕过 audit-only 防线照常评分
交付；正式模式现在 materialize 前强制完整四层身份（缺任一 →
结构化 abort），且屏障缺位时**启动闸门**在 orchestrator 构造即拒绝
（勘误 3"未实现由启动闸门表达"的闸门本体），开发期需显式
fa_audit_only_probe=True（audit-only，产物不可训）；② trajectory_id
在 FA 路径直接取不可变 rh2_rollout_execution_id——修复 replay 污染
（sample.session_id 被改写成 internal sid 后经 _session_id existing
分支回流，attempt2 曾把 attempt1 的会话身份当成轨迹身份）；③ 勘误 3
五 reason code 双向封闭 validator（任意串/None/串门都拒）；④ audit-
only 收口持久 disposition = audit_only_rejected（不再落 unknown_
terminal，FA-2B 故障统计按此排除）；⑤ 权威页旧口径
runtime_quiescence_unconfirmed 清除。**F2-2 复核四轮（root-closure，3 P0 + 1 P1 全采纳）**：① 显式运行模式
`execution_mode ∈ {s1_compat, fa_audit_only, fa_formal}`——模式职责从
require_real_weight_versions（回归正交版本契约）与 paid 观测中彻底
剥离；`validate_execution_config` 集中校验（模式合法性/fa_formal 组合
/版本契约），bringup 在副作用前先调、orchestrator 构造再调防绕过；
② P0-1 修复：版本契约检查（数值版本/context_shrink 强制）曾被错误
缩进进屏障分支（屏障翻 True 即消失）——现平铺在 require 旗标分支下与
屏障无关，回归测试 = 屏障在场时契约仍拦截；③ 屏障改**注入式能力**
（RuntimeQuiescenceBarrier Protocol + QuiescenceResult 带证据；
RUNTIME_BARRIER_AVAILABLE 源码常量删除）：fa_formal 构造时必须注入
非空、执行时必须调用——确认后才评分交付（present_*），拒绝 →
runtime_quiescence_failure + 勘误 3 码 + abort；fa_audit_only 不评分
不交付照旧；s1_compat 完全不产 Outcome（producer 模式门控）；
④ P1-4：启动校验前移到 bringup 副作用之前 + grading queue 启动失败
回滚（adapter 线程在 __init__ 起，其生命周期回滚登记 FA-5 容量/启动
项）。生产旋钮 = RH2_EXECUTION_MODE（默认 s1_compat）。**F2-2 复核五轮（follow-up，2 P0 + 2 P1 全采纳）**：① 冻结评分输入
契约——QuiescenceResult 封闭化（confirmed ⇒ 必带
frozen_grading_workspace 且无 reason；rejected ⇒ 五码必配；矛盾态
构造即拒），正式链 _finalize 消费屏障产出的冻结句柄而非原
workspace（验收 = grading 收到的对象同一性断言）；② FA 专用入口拒绝
s1_compat（含未配置默认）——silent downgrade 关闭，旧 S1 入口不受
影响；③ 启动序列：影子配置删除（静态项按真实值直接校验；fa_formal
在 bringup 无屏障实现前直接拒启动），统一回滚补 app_handle.stop()
（queue + adapter 线程都不遗留）；④ barrier 未知异常按 D4 走
run_halt（FatalExecutionInfrastructureError，worker 停机），不再被
误归 capture_incomplete；evidence_refs 经 producer 入 Outcome。
**F2-2 复核六轮（ownership 收敛，2 P0 + 1 强 P1 全采纳；熔断第二次
触发——五轮声称的 run_halt/回滚被探针证伪）**：① 致命异常独立传播
通道——generate() 的 catch 链显式 `except Fatal...: raise` 在通用
Exception 之前（屏障系统故障不再被吞成缺员 + top-up；worker 既有
run_halt 通道承接），验收 = Fatal 从 generate 逃逸测试；② bringup
启动收敛单事务 owner：纯配置校验前移到 __init__ **线程启动之前**
（invalid mode/fa_formal 在任何资源起来前拒绝），async_start 主体
（探针/queue/config/orchestrator 装配）整体进 `_async_start_body`
单 try，统一回滚 = stop queue + app_handle.stop()；③ 屏障结果改
**封闭联合类型** QuiescenceConfirmed（typed 冻结 workspace +
snapshot_ref lineage + 非空证据，任一缺失构造即拒）/
QuiescenceRejected（五码），未知返回类型按 D4 → Fatal run_halt；
成功路径 snapshot lineage（snapshot:sha256:...）随 extra_evidence
进入成功 Outcome。**F2-2 复核七轮（2 强 P1 已修；P0 = capture wire 所有权 → T0 决策包
待拍板）**：① Fatal 路径先写结构化 failure_record 再抛（持久 audit
不再 unknown_terminal/空归因，JSON 断言）；② 联合类型钉死：冻结对象
必须实现 run_bash（裸 object 拒）、Rejected 必带证据、真 union 别名、
stale QuiescenceResult 引用清除。**待拍板 T0**：CaptureWireRuntime
（进程级，owns registry+monkeypatch）与 BringupService（可重启，owns
app 线程/queue/orchestrator）所有权拆分——install_capture_wire 首装
永久闭包 registry，重启后新老 registry 分家（codex 探针实锤）；codex
推荐进程级唯一 CaptureWireRuntime，不做反向 monkeypatch。
**→ 八轮改判为勘误 4（A′：单代启动 + fail-stop，用户批准）并已执行**：
四修复 = collect_batch 三重 fatal 门 + 隔离账目（含 backlog）、
BringupService 单代闩锁（NEW→STARTING→RUNNING|FAILED sticky，只
latch Exception）+ grading_queue.close(drain=False) 真回滚（旧 stop()
不存在 = 假回滚）+ CC guard 入事务、invalid_result 持久归因、wire
不同 registry typed fatal（legacy flag 收养）。**§10.4 双 subagent
首次实战**（Production Tracer + Falsifier 并行）：四修复功能全数成立；
合流处理 4 项缺陷（终核修正口径）：shutdown→collect 绕 sticky——
终核补 `_closed` 终态闭合；latch 吞 CancelledError——终核改"当前调用
传播取消 + 后续拿 typed fatal"闭合；backlog 组入隔离账（口径按终核
收窄：**内存账只保存已组装 candidate/backlog；queue/in-flight 可恢复
性归 F2-4 pending manifest**，不为"零丢失"提前复制完整训练数据）；
legacy flag——终核改判 typed fatal（monkeypatch 闭包持旧 registry，
改模块属性是假迁移，A′ 不支持进程内迁移）。登记递延：隔离账目 durable
导出（F2-5/F2-6）；__init__ 晚段 adapter 线程泄漏（FA-5；闩锁已防
端口二次抢占）；被 cancel 的 in-flight 协程不响应取消时收尾 await
无独立超时（F2-2b watchdog 面）；闩锁/回滚行为测试 F2-2b 前补齐。
审查机制收紧（review-standards §10）与勘误 4/F2-4 范围文档已单独
提交。**B1 BaselineWorkspaceManifestV1：完成**（contracts/baseline_manifest.py
+ adapters/slime/baseline_census.py）。契约 = 单一基线权威（path/type/
mode/content 或 symlink digest，lstat/no-follow；排序唯一；父子前缀
冲突拒；**大小写共存合法**；排除 namespace 显式版本化进 policy digest，
排除区独立 census digest——排除≠消失）；digest 由读写双方重算不自引用。
生成器 = materialize 尾部（harness 获写权前，树仍可信）census 脚本 +
确定性纯函数解析（UNSUPPORTED 对象 fail-closed）。接线 = 仅 FA 模式
（s1_compat 零改动）；manifest 内存 per-attempt 供 B2 消费，audit 只落
digest + entry 数（数万 entries 不进 JSONL——durable 持久化随 B5
receipt）。递延：真实 SWE 镜像全量 census 性能（FA-5）。**B1 closure（codex 聚焦
审查 3 P1 全 accepted，一次 commit 闭合）**：① lineage 事实收紧——
Sha256Digest/GitSha 类型全覆盖（`not-a-digest`/`local:tag`/`HEAD` 构造
即拒）；public_bundle_digest 按真实名记录；runtime_image_digest = lease
实测不可变 digest；environment_package_digest 未接通保持 None **不伪造**
（"正式链环境包 lineage 未接通"登记为 formal gate blocker）；② 服务级
_baseline_manifests 字典删除——baseline 为 execution-local 变量，B2 以
显式参数消费（无 cache/TTL/清理线程）；③ 真实临时树 census→parse→
digest 测试落地（644/755/symlink 不跟随/排除区留痕/重复执行 digest
一致）。residual risk 显式接受（换行文件名/罕见 symlink target/跨平台
兼容——fail-closed 不阻塞）。**B1 闭合**。**B2 trusted exporter + FrozenPatchArtifactV1：完成**
（contracts/frozen_patch.py + adapters/slime/patch_exporter.py）。
契约 = 结构化 delta（regular/symlink × add/modify/delete，mode 三值，
per-entry content_b64 + digest 互检，排序/唯一/前缀冲突拒，身份绑定
task/bundle/image/baseline/execution/attempt）；digest 外部重算不自
引用。exporter **全程不调 git**（post census 复用 B1 find/sha256sum
枚举，host 侧纯函数 diff——staged/unstracked 差别在字节比较下天然
消失，untracked 内容变化（旧指纹假阴性盲区）被 digest 捕获；mode-only
/类型变化/删除/二进制/symlink target 全检出）；census 与内容抓取双读
digest 互检（静止期写者 → content_digest_race fail-closed）；排除区
census 变化只记事实（excluded_census_changed），tamper 判定留 B3。
接线 = fa_formal 屏障确认后导出，artifact execution-local（B3 显式
消费），audit 落 digest/计数；失败码族入 producer 映射（missing 收口；
unsupported_object_in_patch 单列——B3 落地后改判 present_* +
permanent_rejection，已登记）。验收 = 真实树 e2e 含 **Git 注入负测试**（只声称 **B2 exporter 无
Git**——正式组合链的 DockerQuiescenceBarrier 指纹仍跑 git status/diff，
该 NO-GO 既有登记有效：B6/root-closure 用 git-free census 替换屏障
指纹并做屏障+exporter 组合负测试，此前 fa_formal 挡板不解除）+ 确定性
重导出同 digest。**B2 closure（codex 审查 4 P1 + oracle 全 accepted）**：
① baseline digest 单一事实源（exporter 内部重算，删调用方参数）；
② B1/B2 摘要键入持久 audit JSONL（读盘断言）；③ excluded_census_changed
改名 **excluded_pathset_changed**（只哈希路径集合——上轮"`.git/config`
改动落在标志里"陈述错误，已更正：内容篡改判定仍需权限/命令证据）；
④ exporter 消费屏障产出的冻结 workspace（不绕回 live sandbox）；
两处 `or True` 假断言修正；e2e 补生产顺序 oracle（quiescence < export
< grading + B2 digest 在场）。"双读 race guard"更名**变更内容一致性
检查**（不是全树 writer-zero——那是屏障的 owner 职责）。环境 lineage
裁决：不复制进 FrozenPatch（经 baseline digest 传递绑定已成立）；
formal 开闸前加具名检查 environment_package_digest is not None（只阻
开闸不阻 B3）。**B2 组件级完成**（终核 P1 oracle 补齐：_FrozenWs 记录脚本 + mutation
red-green 见证——期间发现同秒改写的 stale .pyc 会让 mutation 假红绿，
witness 流程加清缓存步骤）。**B3 hygiene 分类 + ScoringProjection：
完成**（contracts/scoring_projection.py）。HygieneReport 二值判定
（unsafe 必带 reasons/projectable 不得带）；v1 unsafe 规则 = entry 落
排除 namespace（结构矛盾）+ symlink target 逃逸（绝对路径/.. 段——
干净 checkout 隔离击穿面）；ScoringProjectionArtifactV1 **按引用**
（路径列表 + raw digest 锚，无内容字段——不成为第二本事实账）。
runtime 私有面：excluded_pathset_changed 只作事实进 report（**不判
tamper**——需权限/命令证据，A-prime 6）。接线 = export 后分类先于
grader（A-prime 5/7）；unsafe → **present_complete + 永久拒绝**
（reason_code=unsafe_artifact_permanent_rejection，不跑 grader、
reward 不可得、abort 剔除、audit 落 reasons）；unsupported 对象改判
兑现（B2 登记项：同 unsafe 收口）。**v2 契约 pre-formal 原地修订
（2026-08-17，A-prime 失败表 unsafe/评分不可得行的执行面）**：
present_* + reward_unavailable=True 时 eligibility_report_id 可为
None——资格链未运行是事实，不伪造引用；producer present-facts 门
同步。版本事实取 capture 真值（hook.records weight_version）。
**B3 closure（codex 4 阻塞 + 2 oracle 全 accepted）**：① symlink 判定
改**词法解析**（以 entry 父目录为基准归一化；只拒逃根与落排除区——
修复前双向错误：放行 `.git/config` 链接、误拒 `../shared` 合法链接，
三判例 + `docs/latest→../README.md` 误拒反例全钉）；② classifier 收
真实 baseline **内部重算互检**（raw digest 重算/baseline 锚互检/四重
lineage 互检/policy 取自 baseline——假 digest 与空 namespace 绕过关闭；
互检失败 = ProjectionContractError → quarantine 域收口）；③ v2
eligibility 豁免收窄**封闭集合**（grading_infra_failure 或
patch_hygiene 的 unsafe 永久拒绝；任意 reason_code 绕过关闭；两处旧
"present 必有 eligibility"说明修正）；④ unsafe 持久 disposition 从
outcome 事实派生 **permanent_rejected**（不再 unknown_terminal，
generate→JSONL 回归钉死）；oracle：unsupported 对象 e2e（present+拒+
无 grader+剔除）+ 旧 fallback missing 行删除防退回 + JSONL 三新键
断言。**B3 复核（3 P1 全 accepted）**：① 契约互检失败改走 **fatal/run-halt**
（系统性契约错误不伪装缺员——结构化归因后 Fatal 逃逸，worker 停机；
e2e 反例钉死不评分不继续）；② eligibility 豁免加 **reward_unavailable
必要条件**（resolved+reward 可得+unsafe reason 的矛盾形状构造即拒）；
③ permanent_rejected disposition 加 **completion=present_* 事实一致性**
（missing + reason 字符串不派生拒绝）。**B3 终核收口（1 P1 共同根因）**：unsafe 永久拒绝七字段全量组合收进
**唯一权威谓词** `is_unsafe_artifact_rejection_shape`（present_*/fc
None/patch_hygiene/unknown/reward_unavailable/无 eligibility）——schema
validator（声称该 reason 即全形状强制）/producer 豁免/audit disposition
三处共用；codex 两个矛盾反例（resolved+reward 可得、grading_infra 混
搭）构造即拒，表驱动逐字段翻转测试钉死。**B3 闭合**（全量 1034 绿）。递延：分类规则扩充（计划既定）；
AdmissionReport 本体（FA-2/F2-5）。**B4 fresh grader 消费 projection：完成（S2 协调确认：S2-1 闲置无并发，
2026-08-18 用户授权；同日 codex B4 审查 3 阻塞项全采纳后闭合）**。核心 =
`FrozenDeltaSource`（frozen_patch + baseline + projection + digest）作为
grade() 的新输入源：设置时 **grader 零 workspace 访问**（workspace 传
None，Poison 同一性负测试钉死"回读即炸"）。**P0-1 修复（首版靶向
pre-image 是对已批 T0 第 2 条的缩水，已推翻）**：apply 前先做纯绑定
检查（source 内部 digest 互检 + source⟷spec 的 task/workdir/base/head
四元组，起容器前 fail-fast），再在 fresh checkout 上**复用 B1 census
脚本/解析器重建完整 BaselineWorkspaceManifestV1 并比对 digest**（局部
import 避 adapters↔grading 模块环）；任何不一致 =
`BaselineIntegrityError`——**故意不被 grade() 捕获**，穿队列由 generate
`_grade` 转 FatalExecutionInfrastructureError（run-halt，与
ProjectionContractError 同通道，绝不转 failed_to_grade 成员损耗）。
镜像绑定说明：rollout 镜像（官方镜像+harness 层）与评分镜像合法不同，
不做相等断言——评分镜像自身走既有 RepoDigests fail-closed，树等价性由
census 重建比对直接证明。**P0-2 修复（写穿 symlink）**：应用命令改为
纯函数构造（build_delta_{delete,write,symlink}_command），regular
modify **先 `rm -f` unlink 旧对象再 `cat >`**（否则重定向跟随旧
symlink 把模型内容写穿进 target——真实文件系统测试确定性复现过）；
add 断言目标原不存在（exit 3）；路径操作数一律 `./` 前缀+单引号（`-`
开头路径免疫选项解析；BSD chmod 不认 mode 后的 `--`，realfs 测试在
macOS 抓到）；symlink target 逐字保留走 `ln -s --`。**P1 修复（generic
projectable ≠ task 级 clean）**：apply 前对 entries 做 task-aware
hygiene 筛查（`screen_frozen_entries`，复用同一 HygieneRules 匹配器）——
命中 test/forbidden 的 entry **剔除不应用**、事实如实进
PatchHygieneResult、既有"resolved 封顶降级"生效 = **与 S1 语义完全一致
（模型负样本 reward 0，不是训练面剔除；未新增拒绝路径，无准入语义
分叉）**。hygiene 契约面修正：新增 `digest_kind`
（cleaned_diff_text|applied_entry_set，默认前者保 S1），FA 路径记**实际
应用子集**的 canonical digest（compute_applied_entry_set_digest），
`replayed_on_clean_checkout` 只有应用完成才 True。**修正 c**：非 UTF-8
symlink target 在 B3 typed fail-closed（unsafe 家族
`unsupported_symlink_target_encoding`），B4 留 typed infra 兜底，不再有
裸 UnicodeDecodeError 逃逸面。失败语义按 A-prime 表：应用动作失败一律
GradingInfraError（reward=None，**不得记模型 reward 0**）；S1 的
patch_apply_failed 在 FA 路径消失。接线 = generate() fa_formal 分支组装
FrozenDeltaSource → _finalize → GradingQueue.submit 透传 →
manager.grade。**D1a 第 2 条兑现**：GradingFailureCategory 新增
`test_execution_timeout`（模型负样本：unresolved+reward 0；无可信
计数是其语义；三条件构造门注释进契约，producer = 未来 grading 超时
分类器——先行进契约防 schema 二次迁移）。S1 评分路径逐字不变
（frozen_delta 未设时新代码零执行）。已知 watch-item（B6 真实组合验证
时确认）：excluded census 的路径集与基线未跟踪文件在 rollout 物化与
评分 checkout 间必须同形——image_embedded 模式两侧都是"镜像原树+只读
探针"，预期成立；若真实镜像出现系统性漂移（如 .git/ORIG_HEAD），按
证据走 T0 复议缩小比对面，不得静默放宽。**§10.4 高风险边界双 subagent
复核（2026-08-18，文件系统应用语义 + 跨组件 fatal 通道）**：Production
Tracer 裁 BaselineIntegrityError 全链 CONFIRMED-run-halt（无吞点、S1 零
执行），发现潜伏 P2——bringup `_grading_submit` 转发缺 frozen_delta 形参
（今日 bringup 硬拒 fa_formal 不可达，但解禁时会 TypeError 塌成
per-member abort）→ 已补形参透传。Falsifier 11 项对抗探针：注入/dash
选项/写穿/intra-delta 软链祖先排序/崩溃面全 SAFE（builder 引号 +
frozen_patch 父子前缀校验 + `./` 前缀），另出两项已修：**F5**——
applied_entry_set canonical digest 用 `\t`/`\n` 拼接而 PatchEntry.path
曾允许控制字符 → 单 entry 可伪造多 entry 规范行致 digest 碰撞（今日仅
审计锚、非生产闸，P2）；修复 = 两个 `_check_canonical_path`（frozen_patch
+ baseline_manifest）统一拒绝 <0x20/0x7f 控制字符（空格保留），同时硬化
census 线协议；**F6**——baseline 树若自带逃逸目录软链 `d -> /outside`，
写入 `d/x` 会跟随软链写出 testbed（非模型可控：模型软链是 entry 被父子
前缀挡掉 + census 等价证明，只有官方镜像自带逃逸软链才可达；无上游拦截）
→ apply 前加 baseline 祖先软链检测，命中即 GradingInfraError 成员损耗
（不升 run-halt——树与 baseline 一致是环境形状问题；是否因系统性升级留
B6 真实镜像裁定）。**新增剔除面登记（§7）**：① 含控制字符路径构造即拒
（census tab/newline 线协议本就无法承载，无真实样本偏置）；② 祖先为
baseline 软链的写入被拒（环境决定、非模型行为相关；fa_formal 闭闸故当前
不可达）。**递延登记**：baseline_census 对 symlink target 做
`tr -d '\n'` 后哈希（`a\nb` 与 `ab` 不可分）——census-vs-census 两侧同法
计算内部自洽、非模型可控，归 B6/FA-5 与全树 census 性能一并处理。
**B4 二次复核闭合（2026-08-18，codex 1P0+2P1 全采纳）**：
**P0**——`materialized_head==spec.base_commit` 绑定会把官方 SWE 镜像全部
误杀（镜像 HEAD 是构建 overlay commit 且内容可非空，S0-7 实证，合法形态
HEAD^==base）；修复 = spec 绑定只留 task_base_commit==spec.base_commit，
`_clean_checkout` 返回探针实测 HEAD，`_verify_baseline_rebuild` 入口对账
grader 实际 HEAD == baseline.materialized_head（同镜像同 overlay；不等 =
grading_head_mismatch run-halt）；exact baseline digest 比对原样保留；
overlay 正例 + HEAD 漂移负例入册。**P1-1（推翻上轮"S1 镜像 strip+cap"
T1 决策）**：gate 对篡改事实 executed 级拒训（gate.py:406/442），strip+
cap 的 reward=0 记录根本进不了训练——只污染 reward/task_outcome/审计并
白跑一次 grader；且 T0 失败表 unsafe 行逐字要求"不运行 grader、
reward=None"。修复 = task 级 hygiene（同一 HygieneRules 权威）移到
generate 在 grader 之前判定，命中走既有 unsafe 永久拒绝闭合
（present_* + permanent_rejection + task_outcome=unknown + 不提交
grader，audit 落 test_file_modified/forbidden_path_touched 归因）；
manager 留 fail-closed 保险杠（漏筛 delta 到达 = unscreened_hygiene_hit
infra，容器都不起）。**P1-2**：`_verify_frozen_delta_binding` 升级为三
对象完整对账——artifact⟷baseline 血缘四元组、projection⟷artifact 身份、
路径集**相等**（只查"多出"会放过"隐去测试文件拿 resolved"）、逐 entry
前置状态（add 原先不存在/modify+delete 必须存在/delete 类型一致，防
"删除不存在路径"被 rm -f 幂等吞掉）；此对账即 B5 持久化再装配后的信任
边界。**B5 finalization receipt + cleanup 排序：完成（2026-08-18，复核
放行后实施）**。契约 = `contracts/finalization.py`：
`FinalizationReceiptV1`（disposition 四分 delivered/aborted/
fatal_run_halt/cancelled + outcome_v2 **verbatim** 内嵌 + handed_off
（F2-4 uncertain_trained 判据）+ frozen_patch/baseline digest 引用 +
grading/eligibility ids + `drain_receipt_ref` F2-3 占位恒 None；校验
哲学从宽——receipt 是 finally 段证据记录器不是语义执法者，outcome 生产
时已全量校验）+ `CleanupResultAppendV1`（独立追加记录）。generate()
finally 重排（A-prime 第 7 条尾段；revoke/drain/terminate 归属屏障已在
F2-2 落地）：**receipt 原子持久化 → cleanup（drop_session + 容器）→
poison release → cleanup 结果追加（独立文件，永不改写 receipt）→
audit sink**。失败语义：**artifact 本体持久化失败**（组装时刻，
content-addressed，receipt 之前）= T0 失败表第 1 行 → missing/abort
不评分；**receipt 持久化失败** = 第 2 行 durable handoff 失败 → 现场
保留（session 不 drop、容器不清入隔离队列、poison 不释放）+ run halt
（正常退出路径抛 Fatal；异常在途只落账不掩盖首因；s1_compat 容忍档与
audit sink 同口径照常清理）；**追加自身失败**只落账绝不反向掩盖。
fa_formal ctor 强制注入 finalization_store（缺失构造即拒——正式链评分
产物不许随容器清理蒸发）。文件实现 `FileFinalizationStore`（bringup）：
tmp+fsync+os.replace+**父目录 fsync**（rename 本身耐久）；artifact 本体
content-addressed 幂等去重（baseline 同任务跨 attempt 实际一份，frozen
patch 每 attempt KB 级）。验收测试 9 项全过：正序（bodies→receipt→
docker rm→append）、persist 失败保留现场+Fatal+无悬空追加、rm 失败追加
不改写 receipt（byte-equal）、F2-4 字段复用断言、abort/body-fail 路径
receipt、S1 无 store 逐字回归、文件实现原子/去重/独立追加。
**B5 复核闭合（2026-08-18，codex 1P0+4P1 全采纳）**：**P0**——receipt
在 finally 写入时结果还没离开 orchestrator（后有 worker queue/组装/
collect_batch 三道关），"delivered/handed_off"是结构上不可能成立的
声明；改为 **delivery_prepared** 定界并**删除 handed_off 字段**——
trainer HANDED_OFF 只能由 F2-5/F2-6 在 batch 真正交付时记录，F2-4 读法
= delivery_prepared 且无交付记录 → 未进训练（负测试：receipt 成功 +
audit sink 失败 → Fatal，receipt 无 handoff 语义可误读）。**P1-2**——
本体持久化移到 export 后、任何 hygiene 分支返回**之前**：unsafe 拒绝也
保留审计证据（T0 第 9 条 retention），负测试断言 unsafe 路径 bodies 已
落。**P1-3（纠正我对 T0 第 9 条的偏离）**——首版共享 digest CAS +
os.replace 覆盖违反"per-execution immutable 目录、不建全局 CAS"逐字
文本；重写为 attempts/<attempt_key>/ 独立目录、全文件 write-once（同
内容幂等 / 不同内容 FinalizationStoreConflict typed 拒绝，aborted 改
delivery_prepared、二次 cleanup 抹失败事实均有拒绝测试）；baseline 每
attempt 一份的存储成本登记 B6/FA-5 实测，共享 CAS 若确需按 T0 重新提案。
**P1-4**——跳过 cleanup 时不再写 cleanup_started/completed 假事件（标
cleanup_skipped_receipt_failure）；双存储失败时首因优先：sink 失败记
audit_sink_failed_secondary，最终抛 finalization_receipt_write_failed。
**P1-5**——两契约入 EXTRA_SCHEMA_REGISTRY（rh2.fa.finalization_receipt
.v1 / rh2.fa.cleanup_result_append.v1，unknown-field 参数化测试覆盖）；
`outcome_v2` 从裸 dict 改 **RolloutAttemptOutcomeV2 typed 嵌入**（构造
期复跑全量不变量），receipt **构造**失败也并入 durable-handoff 失败
通道（不从 finally 裸逃）。非阻塞登记：同步 fsync 阻塞 event loop
（探针 ~0.62s）——B6/FA-5 真实尺寸实测后再定 to_thread；bringup 改为
s1_compat 不注入 store（与"无 store S1 回归"口径一致，receipt 从
fa_audit_only 起生效）。**B5 三轮复核闭合（2026-08-18，codex 3 局部
P1 全采纳）**：**P1-1**——unsupported 对象（FIFO 等）在 artifact 建立前
永久拒绝，路径/类型证据原随 workspace 清理消失；修复 = census
UNSUPPORTED 行升 3 字段（type 探测 fifo/socket/block/char，解析双格式
兼容旧 2 字段）→ BaselineCensusError/PatchExportError 结构化携带
object_path/object_type → 新契约 `RejectedObjectEvidenceV1` 内嵌
receipt（audit.rejection_evidence 挂载；outcome evidence_refs 同步带
`object:<path>:<type>`）。**P1-2**——sink 失败首因保护从"仅 receipt
失败"扩到**任何在途异常**（finally 抛新异常会替换在途 Fatal/取消——
barrier fatal 曾被顶成 execution_audit_write_failed）；receipt 归因
统一为 `terminal_reason_code`（aborted/fatal/cancelled 全覆盖，fatal
取在途异常 reason_code，替换原 abort_reason 字段）。**P1-3**——
`FinalizationStoreConflict` 移居 contracts/finalization（adapters 互
import 成环故不能放 bringup），generate 单独捕获映射
FatalExecutionInfrastructureError("finalization_store_conflict") run-
halt——身份复用/事实矛盾绝不包装成 SlimeBindingError 缺员继续训练
（实测曾 remove_sample 后照常训练）。非阻塞登记（F2-4 前置）：①
artifact_bodies_persisted=True 与两 digest 皆 None 的矛盾组合 schema
校验（当前 producer 不产生）；② 固定 .tmp 名多进程竞争归 F2-4
fencing/恢复切片。**主线顺序（codex 提示 + 05 计划 :179 确认）**：B5
关闭后先做 **F2-3 typed drain receipt**，再执行并闭合 B6——B6 验收依赖
F2-3，可先备 fixture 但不得提前宣称 B6 完成。
**A-prime 定稿（2026-08-17 用户授权）+ B1~B6 切片已入 05 计划 5a 节**
（八要素逐片；B4 动 grading/manager.py 前须 S2 协调；fa_formal 开闸 =
B6 + F2-3 drain receipt + writer-scope T1 手段三前置）。**终核（四提交复核，2026-08-17，阻塞项 + P1 + 4 条件项全采纳）**：
fatal 发布时刻前移到 execution task 边界（_guarded_execute 捕获 Fatal
即写 worker 唯一 halt_reason——"task done 未 reap 仍交付 batch"窗口
关闭，账目仍由 reap 一次完成）；真实 worker+service 交错测试常驻（不
预填 halt_reason）；测试诚实化（install_capture_wire 真调用三分支/
闩锁 sticky 打桩/invalid_result 持久化断言）；Fatal docstring 恢复
语义改勘误 4 口径。**终核二（oracle 修正，2026-08-17）**：fatal 交错测试改 codex 规格
（batch_size=1 + 受控 sleeper 挡 reap；断言 fatal done/worker 未 done/
failed==0/第一次 collect 拒/好组留 queue 归 F2-4 manifest/放行后
failed==1 账目守恒）+ **mutation witness 常驻测试**（恢复旧
_guarded_execute 时同一交错必须交付 batch——oracle 判别力自证）；
invalid_result 补真实落盘 JSONL 断言；shutdown→service_closed 与
启动取消 sticky typed fatal 各补直接测试。**F2-2b Runtime 静止屏障：审查未通过、待重构（NO-GO，2026-08-17
codex 复核三 P0 全实锤）**。已落代码（quiescence_barrier.py）保留但
**fa_formal 拒启动挡板已恢复**（解除条件 = 冻结对象 T0 拍板 + 重构 +
复核通过）。三 P0：① 指纹双向失效——git status --porcelain 只列未跟踪
文件名不含内容（改内容不变=假阴性），评分器自跑 git add -N 改 index
（自触发 mismatch=假阳性），.harness/ 混入评分面；② pkill -u agent
不充分——slim 镜像无 ps 时 `ps|wc -l`=0 fail-open、真实镜像 zombie
永不归零、SimpleLoopDriver 的 root bash 完全绕过、root 跑模型可控
git config 的 diff 有 diff.external 代码执行面；③ session_plane_
drained 非可信收据——slime shutdown_session 吞跨 loop drain 异常只记
日志，RH2 无条件写 True（根治 = F2-3 adapter 单 owner 的 typed drain
receipt）。P1 已修：完整性失败路径先清 audit.finalized（missing 不与
disposition=finalized 并存）。原状态段（见下）作废保留存档：
DockerQuiescenceBarrier 按 D1a 序列：① pkill -9 -u agent + 有界重试
验证进程归零（超时 → execution_scope_termination_timeout）；② 会话面
未排空前提检查（→ late_model_request_detected）+ workspace 双读指纹
（git status --porcelain + diff 的 sha256，两读不一致 →
active_writer_detected；读失败 → snapshot_freeze_failed）；③ 冻结出具
FrozenWorkspace（snapshot_ref = 稳定指纹）——评分链只消费该封装，
评分后 orchestrator 调 verify_integrity() 复核，漂移 → **先撤销
runtime_quiescence_confirmed 事实再产 outcome**（missing +
runtime_quiescence_failure + snapshot_integrity_mismatch + abort，
评分结果作废）。冻结语义 v1 口径 = 写者集合证空 + 双读静止 + 评分后
复核（不做物理 cp 副本——写者为零时副本不增加保证；若审查要求可加
而不动调用面）。bringup fa_formal 拒启动挡板解除（async_start 事务内
构造 DockerQuiescenceBarrier 注入；validate_execution_config 仍强制
非空）。真实容器验证归 FA-5（本机 = 脚本路由假件 + 全链 e2e：真实
屏障类进正式链、评分收到 FrozenWorkspace 同一性断言、漂移收口）。
FA-5 未开工。闸门 `rh2_fully_async_training_path_verified` =
**false**。测试基线 1003。

**FA-2A 批准要点（实现必须遵守的边界）**：Observability V0 只记录不改
行为；audit_only 不放宽任何守卫、不产正式训练 batch；hard_wall 仅
termination trigger（completion 按事实推导，present_truncated 处置留
D1b）；不定义 chargeable_policy_seconds；不导出 trajectory.jsonl；
profile 选择/watchdog 数值/masked member 算法语义/熔断阈值全部延后
（D1b/FA-4/pre-RL）。

**当前有效的关键机制**（历史轮次里的旧形态全部作废）：

- capture 暂存：stage 单槽 + overlap **fail-closed**（轮次 9；轮次 8 的
  FIFO 已废弃）；commit 事务化 PENDING→COMMITTING→COMMITTED/ABANDONED
  （轮次 13）；registry/proxy 短临界区锁（轮次 13/14；终局 = FA-2A 单
  owner 重构，锁是明知要重写的脚手架）。
- poison 生命周期：active 绝不容量淘汰 → orchestrator 在**容器清理完成后**
  release 归档（轮次 11/12；轮次 10 的"unregister 即 release"已废弃）；
  poison 触发跨线程主动取消 harness（call_soon_threadsafe，轮次 10）。
- 交付定案：finalize 在 **commit（record_turn 成功）时刻**（轮次 8；stage
  时 finalize 已废弃）；abandon 事务化先关账再抛（轮次 12）。
- 模型边界：未知 SID fail-closed + 会话守卫 middleware 403（轮次 13）；
  404 一律转 503 + x-should-retry:false（轮次 9/10）。
- 审计：execution 终态 audit sink（含 timeline/timing/disposition）+
  attempt ledger **snapshot→写成功→ack** 事务（轮次 14；先 drain 后写已
  废弃）；正式链审计写失败 = FatalExecutionInfrastructureError → worker
  停机（轮次 14）。
- 非零 harness exit：与正式链的启动断言**硬耦合已解除**（轮次 14 推翻
  轮次 9——slime episode 超时返回 EXIT_TIME_BUDGET_EXCEEDED=-1 是正常
  终止；旋钮保留、glue 默认仍联动；结构化终止枚举是 FA-2A 前置定义项）。
- 恢复语义（勘误 4 修正，2026-08-16；旧表述 superseded）：halt = **fail-stop
  终止当前训练 run**——WorkerHalted 令 rollout RPC/ray.get 失败，不自动
  杀死或替换 Ray Actor；受控恢复（checkpoint replay/fencing）属 F2-4。

**临时挡板登记（每个都有替代任务与移除条件；FA-2A 完成时逐个显式裁决）**：

| 挡板 | 加于 | 移除条件 |
|------|------|----------|
| overlap fail-fast（并行 subagent 被拒） | 轮次 9 | F2-3 request 级归属落地；且列入 `rh2_formal_training_allowed` 前置 |
| ~~DuplicateActiveSessionError~~ | 轮次 12 | **改判永久身份碰撞守卫**（2026-08-15 F2-2 复核二轮）：per-attempt internal sid 下重复注册不该自然发生，该守卫从"临时挡板"转正为不变量（碰撞 = 身份铸造/贯穿 bug 的第一现场），不再列移除条件 |
| ~~中毒 SID（含归档）拒绝 register~~ | 轮次 11 | **已解除**（2026-08-15 F2-2：poison 按 internal sid = 按 attempt 绑定，稳定 SID 拉黑面消失；register 前置 poison.check 保留为常规防御） |
| StaticActiveCoordinator（永远 ACTIVE，只保守缺员） | 轮次 7 | FA-4 真协调器（consensus version） |
| ~~capture_wire/glue 住在 experiments/~~ | S1 沿革 | **已解除**（2026-08-07 F2-0，commit f8580789——src 唯一权威 + 薄兼容壳；壳兼容范围 = 导出对象 identity + 旧动态入口可解析，**不承诺旧模块全局变量重绑传播**） |
| ruff F401 豁免（s2_1_ingestion/resolve_image_digests.py） | 2026-07-24 | owner = S2 线程；S2 收敛后清理并删豁免；gate = 训前总审计前 |
| physical_attempt_seq 重启后从 1 重数 + `_attempt_seq` 随执行数无界 | 2026-08-07 F2-1a | owner = F2-4 checkpoint（seq 纳入 pending checkpoint / 有界化）；gate = 训前总审计前（codex F2-1a 复核递延项） |
| V0 timeline 43 事件仅约 4 个有生产调用点 | 2026-08-07 F2-0b | owner = 各切片（execution 事件随切片接线 / model 区间填值 F2-3 / group·batch 事件 F2-5-F2-6）；gate = 训前总审计前（codex F2-0b 复核 P1-1） |

**未闭合项**：见 05 计划 §6.1 递延表（P1×8 + P2×4）与 FA-2A 批次定义。

## FA-0 身份、版本与执行结果契约（2026-07-12 完成）

**交付**：`contracts/fa_runtime.py`（ExecutionIdentity / RolloutAttemptOutcome /
TrainingRuntimeWindow / ModelCallAttempt 四契约 + 三层身份与 mask 分离的模块级
定义）；真实 weight_version 管道（TurnTape/capture 记录逐轮透传 →
backfill 逐入训轮回填 → 握手 staleness 真实计算）；正式链启动断言；
`routed_experts_start_len` 扩展位（非 0 fail-closed）；D-FA-6 环境注入 helper +
上下文收缩检测；fully_async 表面契约测试 7 条。测试 647 → 684 全绿。

### 设计决策

1. **FA 契约注册走 CLI 聚合表**（`registry.EXTRA_SCHEMA_REGISTRY`），S1 核心
   registry 保持验收口径的 15 个冻结。`inspect_s1` 的收编对照相应改为
   "S1-9 五个是下界 + `rh2.fa.*` 前缀放行、未知前缀仍 FAIL"——S1 账本对
   S1 面的保护强度不变，FA 面归未来 `inspect-rh2-fa`。
2. **上下文收缩不加 gate 第八维**：七维是封闭枚举（`failed_dimensions`
   校验器拒绝未知名），加维度牵动 `GATE_VERSION`——而升版机制是 S2-0/S2-7
   的 TIER_CAP 解封职责，FA 不越权。改为**装配期 fail-closed**：
   `detect_context_shrink` 检出 → `SlimeBindingError("context_shrink_detected")`
   → 既有 abort 收口（`remove_sample=True`），语义同样是"轨迹退出基线"。
   检测默认只记录（`reject_context_shrink=False`，S1 行为逐字不变），
   正式 GRPO 基线配置必须置 True。
3. **fully_async 表面契约测试是源码级结构断言**：本地 venv 无 torch，
   slime 模块不可 import；文本 pin 足以在升级 pin 时抓住承重事实漂移
   （N1 吞异常形态、组长断言、阻塞 put、`_key`、pause/continue 端点、
   weight_version 记账）。行为级验证归 FA-5。
4. **weight_versions 回填语义**：逐入训轮真实值优先 → 缺失回退
   policy_version → 部分轮两者皆无则**整字段不写**（宁可无事实让 gate
   降级，不拼"真实+猜测"混合序列）。正式链（require_real_weight_versions）
   下任何入训轮缺真实值直接 fail-closed。
5. **staleness 真实计算只在正式链启用**（current − min(seen)，数值版本），
   S1 兼容路径恒 0/True 逐字不变——避免翻动 S1 已验收的握手 evidence 语义。
6. **consume-time 字段冻结禁令**：Outcome 的 `current_version_at_consume` /
   `worst_token_lag` 在 finalize 校验器强制 None；FA-3 assembler 消费时另行
   落账，不回写冻结记录。

### 偏离说明

- 计划原文写"上下文收缩 → gate 维度"，实现为装配期 fail-closed（理由见
  决策 2）；语义等价、机制不同，05 计划不改文（该节本就写的是目标语义）。
- "DISABLE_COMPACT inspector 探针在本地 harness 冒烟中验真"以 **stub 子进程**
  实现（`test_compaction_disabled_env_reaches_child_process`：env 准备 →
  子进程读回 `SLIME_AGENT_CC_EXTRA_ENVS`）；真实 CC 子进程的验真按计划
  挂 FA-5 短租。glue 的实际接线（在 GPU 机器的启动路径调用
  `ensure_claude_code_compaction_disabled`）留 FA-1——本地无法冒烟真实
  glue 路径，helper 与探针已就绪。
- `RolloutAttemptOutcome` 本任务只交付契约与测试，编排循环的发射接线归
  FA-2（PromptGroupAssembler 是它的消费者，先有消费者再接生产者）。

### 权衡

- 三层身份暂未强制挂进 TrajectoryProjection（会动 S1 冻结契约的必填面）；
  FA-1/FA-2 接线时以 sidecar/metadata 承载，投影 schema 是否升版随
  FA-2 定。
- `BackendHandshake` 未加 `attempt_outcome_ref` 字段（codex 轮次 3 曾建议
  方向）：等 FA-2 的 Outcome 发射点定了再挂引用，避免先造空字段。

### 开放问题

- `context_shrink_ratio=0.6` 是预注册黄线，FA-5 用真实 CC 轨迹校准
  （thinking 剥离的真实收缩幅度分布未实测）。
- P3 夹具往返测试依赖本地 evidence 目录（浅 checkout 自动 skip）——
  `inspect-rh2-fa` 建账时把该测试列为必跑项（evidence 在库，正常 clone
  不会 skip）。

## FA-0 follow-up（2026-07-12，codex FA-0 审查全 12 项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 4）

- **严重 1（staleness 事实矛盾被 clamp 掩盖）**：`max(current-min(seen), 0)`
  的 clamp 删除——任何 seen 版本比 current 新即
  `weight_version_ahead_of_current` fail-closed（codex 反例 current=3/
  seen=[5] 现在必炸）。新增 `current_policy_version_provider` 注入点
  （FA-1 接 `engine.get_weight_version` 包装）；provider 缺席时回退
  config 值，注释明确该口径是"相对启动版本"、不得称实时 staleness。
- **严重 2（session 级收缩检测误杀子 agent）**：核实 CC 子 agent 与主
  agent 共享 session id（`claude_code.py` ANTHROPIC_AUTH_TOKEN=session_id
  → adapter 按 token 归组）。重构：session 级检测降为纯 audit 信号；
  **硬拒绝只在叶链自己的入链轮序列上执行**（lineage 内比较，子 agent 是
  独立叶链天然免疫）。负测试：主 agent 长上下文 + 子 agent 短上下文不拒；
  真 e2e：叶链内坍缩 → abort 形状 remove_sample=True。已知边界（诚实
  记录）：compaction 延续分支若经 REALIGN 把压缩前轮全部掉落，叶链级
  检测也看不见——正式基线的完整防线 = DISABLE_COMPACT 验真 + session
  级 audit 信号复核 + 叶链级硬拒绝三层，缺一不可。
- **严重 3（评分枚举统治执行期归因）**：新增 `RuntimeFailureCategory`
  13 值（proxy/推理服务/沙箱/harness/worker/评分基建/capture/对齐/
  staleness/安全/身份/契约/清理），`RolloutAttemptOutcome.failure_category`
  改用之；评分故障映射 grading_infra_failure + evidence 回链 GradingReport。
- **一般项**：present 强制 `current_version_at_finalize`；窗口
  old==target 拒绝（无前进的更新窗口是事实矛盾）；delivered attempt 强制
  weight_version；aborted attempt 加 `abort_fencing_token`（窗口归因双
  凭据）；`shrink_ratio` 域校验 (0,1) 开区间；正式链启动断言强制
  `reject_context_shrink=True`（不再只是注释）；混合序列注释改为精确
  两档口径（正式链 100% 真实、非正式链允许显式回退混合）。
- **测试项**：pin 守卫测试（reference/slime HEAD 必须 e848052a，在场即
  校验；缺席仍 skip，`inspect-rh2-fa` 建账后升为 fail）；误名的收缩测试
  重写为真 e2e（orchestrator 全链 + remove_sample 断言）+ audit-only
  对照。测试 684 → 692。

## FA-3 离线部分（2026-07-12 完成；接线部分待 FA-2）

**交付**：`adapters/slime/batch_admission.py`（预检器 + 层次化归一化 +
三视图纯函数）+ P3 事件夹具加载器 + 21 条测试（单元 15 + 差分 6）。
测试 692 → 713。

### 设计决策

1. **差分测试是预检器的正确性权威**：slime `utils/dp_schedule.py` 模块
   自述纯 Python、CPU-only 可测——差分测试直接 import **真函数**，同一
   输入比对成功/失败类别 + step 数 + 每 rank microbatch 数三项（J4/J5
   夹具 + 200 例随机扫，seed 固定）。预检器镜像 first-fit 装箱与对齐
   判定；`balance_by_flops`/`balance_data` 未镜像（P3/首训均关闭），
   开启即 fail-closed 拒绝——防止镜像面静默失真。
2. **B 类失败的机制确认**：J5 gbs16 的 "could only produce 23 mbs;
   need 24" = step0 恰 23 个样本（前 16 个有效 rollout 的真实 fan-out
   分布，事件元数据核实）+ align_to=dp2×1=2 + K0=23（全单箱）→
   round_up(23,2)=24 > 可拆分上限 23。夹具结构 100% 真实；样本 token
   总长不在事件元数据里（.pt 未同步），用校准值 20000 保持全单箱——
   报错里的 23/24 两个数字由结构决定，与校准值无关（测试 docstring
   已声明口径）。
3. **归一化实现放 adapter 纯函数层**（不进契约、不碰队列）：五条 E
   不变量以构造保证 + 属性测试钉死；广播不一致/身份矛盾 fail-closed。
   group5×8branch 定向回归直接吃 J4 真实事件（8 branch = 1 execution，
   分母 = 8 branch token 和）。
4. **torch 加入 dev 依赖组**（torch 2.13 CPU）：dynamic_filter 真调用
   测试（P3 崩溃形状复现 + 平铺形状通过）与 FA-4 torch 对拍都需要；
   运行时依赖面不变（只进 dependency-groups.dev）。

### 偏离说明

- 05 计划离线验收 5 要求 dynamic_filter 与 `_key` 都做真函数直接单测：
  **`_key` 的真调用做不到**——import 链穿 `sglang_rollout`（需要 sglang/
  ray，本机不装）。dynamic_filter 真调用已做；`_key` 保持源码级 pin
  （test_fully_async_surface），真调用留 FA-1 的 GPU 环境。如实降级，
  不冒充。

### 开放问题

- J5 gbs20 对照在预检器下 num_steps=1（41 样本中后 9 个 rollout 不足
  第二个 step 被真函数同款丢弃）——"尾部 rollout 静默丢弃"是 stock
  语义，FA-3 接线的 assembler 必须把它变成显式记账（丢弃即 log）。

## FA-4 对拍部分（2026-07-12 完成；custom loss 接线待 GPU 环境）

**交付**：`training/faithful_dis.py`（参考 loss + 解析梯度 + 指标）+
11 条对拍测试。测试 713 → 724。

### 设计决策

1. **三方对拍**：手算逐位 / 冻结权重有限差分（专测 detach 语义——若实现
   忘了 detach，接受 token 上必失配）/ torch autograd 同构实现
   （`ratio.detach()`，loss 与逐 token 梯度 1e-9 容差逐位）。torch 同构
   函数就是未来 Megatron custom loss 的形状雏形与对拍权威。
2. **denominator 语义预注册 v1 = provenance_tokens**（被拒 token 留分母、
   梯度为零）：与 slime stock TIS 的 `rollout_mask_sums` 口径一致，使
   IcePop 近似对照可同分母比较；`accepted_tokens` 第二实现保留用于消融。
   **FA-4 接线时须对照论文原文最终定死并回写**（codex 轮次 3 #7 的
   预注册要求——两档差异测试证明它直接改变有效学习率，不能含糊）。
3. ε 区间 0.8/3.0 按 codex 引注写入常数并标注"接线时对照原文复核"；
   区间语义 = 闭区间（边界测试用实际 ratio 值构造，避开 exp/log 浮点
   回环的 1ulp 假失败——这是实现细节里唯一踩过的坑）。
4. 全零有效 token → `zero_grad_step=True` + loss 0 + 无除零：FA-4 接线
   的"跳过 optimizer step"信号在参考层就位。

### 开放问题

- 论文忠实性只到"公式语义"层：denominator 档位、以及 top-p replay 是否
  参与 current logprob 计算（对拍清单第 5 项）要在接线时对照实测定死——
  参考实现把每个自由度做成显式参数，就是为了那时不需要改结构。

## FA-3/FA-4 follow-up（2026-07-12，codex 审查 12 项全部采纳；原文存档
## `../s2/codex_reviews.md` 轮次 5）

- **严重 1（DIS 区间勘误——本轮最重要修正）**：对照 SAO 论文 p.4 原文
  裁决，式 3 = `f(x)=x if 1−ε_ℓ < x < 1+ε_h else 0`——**开区间、
  (1−ε, 1+ε) 参数化**；coding 配置 ε=(0.8, 3.0) → 信任区间 **(0.2, 4.0)**。
  轮次 3 的"直接 ratio 边界"读法与我方闭区间实现 [0.8, 3.0] 都是错的，
  已改并在 05 计划 §5 勘误。注：论文正文写 "[1−ε_ℓ, 1+ε_h]" 闭括号与
  式 3 严格不等号自相矛盾，预注册以正式定义（式 3）为准并留注。
  detach 补记为 RH2 显式算法决策（论文未写 stop-gradient）。
- **严重 2（selected/deferred 报告）**：预检 `ok` 现在返回逐 step
  selected_rollout_ids + deferred_rollout_ids + 双侧 sample positions
  ——尾部不足一 step 的 rollout 是"延后"不是"丢弃"，lease/ACK 接线
  的 READY 回队语义有了数据面。差分测试同步比对 selected 集合
  （真函数 partitions 并集 == 预检 selected）。
- **严重 3（prompt_group_id 权威键）**：BranchDelivery 补 FA-0 稳定身份，
  归一化/三视图全部改键 prompt_group_id（group_index 降为 slime 批次内
  编号）；重复 (pg, exec, branch) 身份 fail-closed。
- **严重 4（execution 级归约层次）**：新增 `faithful_dis_loss_by_execution`
  ——branch 分子 → execution 共享分母（与 FA-3 rollout_loss_denominator
  互检）→ batch 按 execution 等权平均；branch-split 不变性、fan-out 隔离
  （对照平铺单分母的可区分差异）、DP 分区加权重组不变性三组测试钉死。
  CP/VPP 分布式归约留接线期真实并行环境。
- **严重 5（torch 全零 NaN）**：codex 实测属实——torch 对拍 helper 改
  clamp+门控（全零 → 可微零，backward 不断图，无 NaN），加专测。
- **输入校验全套**：NaN reward/advantage、重复 branch、零 token
  execution、非法并行/装箱参数全部 fail-closed；DIS 阈判移到 log-ratio
  空间（巨大 logp 差先拒绝、不执行 exp，溢出免疫）。
- **遗漏项处置**：失败类别差分比对（不再只"两边都失败"）；P3 分母回归
  改用 `loss_mask_ones`（可训练 token 口径，不是 response_lengths）；
  跨版本双 turn 场景测试（同 execution 内逐 token 各判各的）。
  仍留接线期的：top-p replay 进对拍、DIS 旁路启动负测试（接线配置面）、
  CP/VPP 分布式归约、lease/ACK 本体（FA-3 接线，等 FA-2）。
- codex 附加验证留档：5000 例随机调度差分全部一致（我方 200 例 seed 扫
  的独立加强）。测试 724 → 732。

## FA-1 持续 worker、有界队列与 proxy 边界（2026-07-12 完成；slime 薄壳入口留 FA-5）

**交付**：`adapters/slime/async_worker.py`（ContinuousExecutionWorker /
BoundedDeliveryQueue / ResourceLimits / ModelCallProxy / 重试白名单）+
17 条故障注入测试 + glue 两处接线。测试 732 → 749。

### 设计决策

1. **零 slime import 的运行时层**：所有组件可注入（task_source /
   execute_fn / coordinator / send_fn），本地故障注入即 FA-1 验收；
   slime `--rollout-function-path` 薄壳在 FA-5 短租的 glue 层落地——
   与 FA-0"slime 不可本地 import"的诚实分界一致。
2. **N1/N2 修复形态**：worker 账目守恒（dispatched == delivered + failed，
   异常执行必经 failure_sink 落账，sink 自身异常也不炸 worker）；交付
   走非阻塞 try_put + 待投列表，队列满只计数反压并暂停 top-up（反压
   传导到生产侧），reap 与主循环永不停摆。ABORTED 回队完全不使用
   （abort 在 proxy 层内部重生成，worker 面不存在 ABORTED 样本）。
3. **ModelCallProxy 守卫三条件的协议化**：重叠判定 = 失败时刻窗口
   phase != ACTIVE 或 update_epoch 相对发起时刻前进；版本前进等待 =
   phase==ACTIVE ∧ active_version 数值 > 发起时刻版本 ∧ fencing 与观测
   abort 窗口一致（epoch 更新时放行新窗口）。上限 max_regenerations=3
   （更新风暴防线），超限/超时/围栏不符/非重叠一律不可归因缺员。
   delivered 缺 weight_version 也按不可归因处置（契约强制 provenance）。
4. **半截输出的物理隔离**：non-delivered attempt 的响应只进
   proxy.audit_artifacts（审计面），capture_record_ref 强制 None——
   旧 token 悬挂负测试断言交付面只含最终 attempt 的 token。
5. **重试白名单代码化**（讨论稿 §4 逐行）：默认不在表中 = 只执行一次；
   评分段 max_attempts=2（首次+1）；full-jitter 封顶 min(8s, 0.5·2^k)。

### 偏离/递延说明

- `_key` 真函数单测仍不可本地做（import 链穿 sglang_rollout）——FA-1 的
  GPU 侧遗留，与 FA-3 时的口径一致；源码 pin 在位。
- glue 接线两处：async_start 急切合并 DISABLE_COMPACT（幂等，evidence 记
  `cc_compaction_guard_envs`）+ SlimeBindingConfig 两旋钮
  （RH2_REQUIRE_REAL_WEIGHT_VERSIONS / RH2_REJECT_CONTEXT_SHRINK，默认 0
  = S1 行为逐字不变）。glue 在本机不可冒烟（aiohttp/slime/docker 链），
  改动为静态审查级——FA-5 短租首个验证项。
- 协调器的**生产端**（trainer 侧发布 TrainingRuntimeWindow 的 Ray actor）
  属 FA-4 接线/FA-5；本轮交付其消费端协议（CoordinatorView）与全部
  边界行为。

### 开放问题

- worker 退出语义 = 显式 stop + 账目清零；若消费者死亡且队列满，run()
  不自行放弃（待投样本不丢）——FA-2 assembler 侧需要配 watchdog/超时
  策略（组 deadline 已在计划内）。
- max_regenerations=3 是预注册值（更新间隔 » 单轮解码时长时理论上
  1 次就够）；FA-5 实测更新风暴形态后校准。

## FA-1 follow-up（2026-07-13，codex 审查全项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 6）

- **严重 1（组件未进生产路径）**：新建 `experiments/fa_bringup/rollout_entry.py`
  ——slime `--rollout-function-path` 的真实 FA 入口，组装 worker/queue/
  limits，从 data_buffer 取组、逐 execution 分派 `args.rh2_orchestrator.
  generate`、interim 聚合器按组收齐/整组显式弃置/收满批次返回。**零
  slime import**（Sample 全程鸭子类型）→ 本地假件测试覆盖全部编排逻辑，
  GPU 侧只剩"slime 真把它当入口调"（FA-5 首检项）。FA-2 接缝显式：
  interim 聚合器整体替换为 assembler，worker 输出形状保持。开发中自查
  补了一个真缺口：源枯竭 + 批次未满会永久空转 → 加 `batch_starved`
  饥饿超时。
- **严重 2（sink 失败静默）**：failure_sink 抛异常 → worker 内部
  `unrecorded_failures` durable fallback + **run-halt**（停止 top-up、
  drain 后抛 `WorkerHalted`）——"账平但无记录"形态被消灭。
- **严重 3（生命周期）**：取消的 execution 按失败落账；task_source 异常
  → halt（在途照常收尾）；worker 自身被取消 → finally 取消并 await 全部
  在途、逐个落账再传播；stop 后消费者死亡 → `drain_timeout_seconds` 到期
  把未投样本进 `abandoned` 显式记账退出。账目守恒扩为
  dispatched == delivered + failed + abandoned。
- **严重 4（attempt 身份）**：`proxy.call(execution_scope, turn, send)`
  ——attempt id = `{scope}/{turn}_a{n}`，并发 rollout 同名 turn 不冲突
  （交错鲁棒的并发测试）。
- **严重 5（capture 事务）**：delivered 改**两阶段**——proxy 返回
  `DeliveredDraft`，调用方 capture 持久化后 `finalize_delivered(ref)` 落账；
  未 finalize 的交付在 `unfinalized_deliveries` 对账可见。悬空 evidence
  修复：所有 evidence_refs 先 `_store_artifact` 再引用（存在性测试）。
- **严重 6（版本放行漏洞）**：恢复必须**达到 abort 窗口 target_version**
  ——同 epoch 要求 active==target（fence 一致）；更晚 epoch 要求
  active>=target；codex 反例（before 3/target 5/恢复 4）现在正确拒绝
  （version_regressed_across_epochs），另加同 epoch overshoot 矛盾检查。
- **遗漏项**：audit_artifacts 改有界（digest+256B 预览，FIFO 淘汰计数，
  完整体交可注入 artifact_sink）；ResourceLimits 真实接入（worker 的
  execution 圈 sandbox 类、proxy 的 send 圈 model_call 类，各有生效
  测试）；`max_pending_out` 改 `>=` 并校验；retry 加 `NonRetryableError`
  + `retryable` 谓词（永久错误不烧预算）+ RetrySpec 域校验；proxy 加
  `attempt_timeout_seconds`；glue 布尔旋钮改 `parse_bool_env_flag` 严格
  解析（只认 0/1，拼错即炸）；glue 注入 `current_policy_version_provider`
  （= capture registry 逐轮引擎版本的数值最大值，回退启动探针值）。
- **场景 21 的落点修正（重要）**：初版把 eval fail-fast 放进
  `orchestrator.generate`，被既有测试当场揪出——**eval 占位形状是 S1 的
  正式面**（E10 定案：训练与评测同链路）。拒绝移到 FA 入口
  `generate_rollout_async(evaluation=True)`（与 stock fully_async 的
  raise 同位）；S1 路径支持 eval、FA 路径拒绝 eval 是设计差异，两条路径
  各有测试钉死。
- 测试 749 → 768（worker/proxy 重写 29 条 + 薄壳 7 条）。

## FA-1 follow-up 2（2026-07-13，codex 轮次 7 全项采纳；原文存档
## `../s2/codex_reviews.md` 轮次 7——五个 P0 全部属实）

- **P0-1（同步接口不兼容）**：slime `call_rollout_fn` 不 await——注册路径
  改为同步 `generate_rollout`（内部用 slime `run()` 驱动，本地回退
  asyncio.run）。**真 slime 契约测试**落地（torch dev 依赖使
  `slime.rollout.base_types` 可本地 import）：用 slime 自己的
  `call_rollout_fn` 调我们的入口，断言产物是 `RolloutFnTrainOutput` 且
  samples 不是 coroutine——codex 探针的直接回归。
- **P0-2（启动挂载缺失）**：glue 新增 `ensure_fa_started(args)`（与
  custom_generate 首调用共用 BringupService 单例）+
  `build_fa_sampling_params(args)`（从 slime args 字段构造，缺字段
  fail-closed——仓库此前没有任何代码写 rh2_sampling_params）；FA 入口
  缺挂载时先经 glue 引导再 fail-fast。
- **P0-3（预取丢失）**：FaRolloutService 持久化——worker/queue/collector
  跨 collect_batch 保温（真 fully-async：训练时后台继续生成），多出的
  完整组留在队列/结余表供下批消费；显式 `shutdown()` 走 drain 协议。
  codex 探针（batch=1/concurrency=8 丢 15 个执行）转为零丢失回归测试
  （5 组 5 批全取回）。
- **P0-4（proxy 未接线）**：capture_wire 的 `rh2_call_sglang_generate`
  现在经 proxy 调用（send 闭包抽出，原直连路径仅在 proxy 未装配/非 rh2
  会话时保留）；glue 启动时装配 proxy + StaticActiveCoordinator（真协调
  器 FA-4 接线前的保守替身：**任何中断不可归因 → poison + 缺员**——
  没有窗口事实就不猜归因）。新增：`SessionPoisonRegistry`（不可归因/
  预算耗尽/客户端取消 → 整 session 中毒，后续 CC 退避重试快速拒绝——
  codex 实测 CC 2.1.205 对 5xx 指数退避且 20s 不放弃，仅 turn 去重不够）；
  **episode deadline 传播**（attempt 超时与等待超时被剩余预算截断，
  不足一次重生成即 poison+缺员）；**发前 ACTIVE 等待**（明知更新中不发
  注定被 abort 的请求）；CancelledError 原样传播但先落账+poison（aiohttp
  handler_cancellation 链保持）；两阶段 finalize 接到 stage 点（暂存即
  本进程持久化点）。
- **P0-5（provider 语义）**：`_latest_engine_version` 权威化——先取引擎
  `/get_weight_version`（trainer 更新后即便无新成功响应也是新版本）；
  registry 最大值降为**交叉检查**（大于权威值 = 版本管道错乱 fail-closed）；
  HTTP 失败时正式链 fail-closed、bring-up 如实降级为"相对最近观测"。
- **一般项**：audit 淘汰改 live-count + digest tombstone（`audit:` 引用
  永远可解析；sink 成功直接返回持久外部引用）；`abandon_delivered(reason)`
  给 unfinalized draft 显式出口；interim collector 弃置即删桶 + 迟到成员
  计数（100 组泄漏回归）；dead-consumer 测试改真实分派后 stop（原
  dispatched=0 空验证）；`_build_service` 构造并传入 ResourceLimits。
- **CC 重试实测留档**（codex 本机 2.1.205，fake endpoint）：连接保持时
  至少等 12s 不重试；对 500 指数退避（0.58/1.17/2.08/4.80/8.20s，20s 内
  6 次不放弃）。FA-5 用容器内同一 tarball 复测；本地 fake-endpoint 故障
  注入战役（30/60/120/300s 延迟、429+Retry-After、半 SSE 断连、重试 body
  一致性等）列为 FA-5 前的独立本地任务。
- 测试 768 → 797。仍留 FA-2/FA-5 的：assembler 替换 interim 聚合器、
  真机验证 slime 调用入口与 CC 真实二进制行为。

## FA-1 follow-up 3（2026-07-13，codex 轮次 8：6 P0 + 源码引导 CC 实验；原文
## 存档 `../s2/codex_reviews.md` 轮次 8，CC 行为证据见本目录两份报告）

- **P0-1（finalize 早于真实 SSE flush）**：finalize_delivered 从 wire 的
  stage 时刻移到 **commit（record_turn 成功）时刻**——CC 的 SSE flush 发生
  在 slime `_respond()`（wire 返回之后），stage 时 finalize 会造成"delivered
  但 CC 没收到"虚假交付。ProxyCallResult 挂进 PendingTurn；unregister 对
  未 commit 的 draft 显式 `abandon_delivered`。capture ref 改用真实
  request_id（不再是复用的 `staged:sid:tN`）。
- **P0-2（poison/非零 exit 不强制拒绝）**：orchestrator 加可注入
  `session_poison_check`（glue 接 `registry.poison.is_poisoned`），harness
  返回后复检——执行期中毒即整 execution 缺员（SlimeBindingError 收口成
  abort 形状），已捕获的 partial trace 全部作废；正式链另加
  `reject_on_nonzero_harness_exit`（默认 False = S1 兼容，非零退出可能是
  合法任务失败负样本；True 时训练守卫下的非零退出可疑到拒绝）。
- **P0-3（不可归因分支漏 poison + 恢复等待无视 episode deadline）**：
  call() 改薄包装——**任何** UnattributableModelCallError 在外层统一 poison
  （发前等待超时/版本恢复超时/fencing 不符/版本回退此前漏 poison）；
  `_wait_version_advance` 接 episode 绝对 deadline（此前独立固定 60s，
  与 attempt1+attempt2 生成叠加可远超 episode 预算）。
- **P0-4（重生成复用同一 rid）**：rid 生成移进 `_send_once`——每个 attempt
  独立 rid，`/abort_request` 精确指向被 abort 的那次。
- **P0-5（worker 跨 batch 崩溃静默重启）**：`_ensure_worker` 发现旧 task
  已 done 时**先 `.result()` 传播异常**——WorkerHalted 必炸给启动方，
  正常退出则报 `worker_already_exited`（已 shutdown 不自动重启）；重启只
  能走显式新建 service。"故障后训练不得继续"成为硬规则。
- **P0-6（同 session 并发覆盖 capture）**：`pending` 改 **FIFO 队列**
  （dict[sid, list]）——并发暂存不再静默覆盖丢数据，commit 按序弹最旧，
  `concurrent_overlap_seen` 计数。完整 request/turn 级归属（record_turn
  传 request_id）需改 slime 签名，留 FA-2/FA-5；本版消除的是静默丢数据。
- **CC 训练守卫升级**：`ensure_claude_code_compaction_disabled` →
  `ensure_claude_code_training_guards`（四变量：DISABLE_COMPACT=1 +
  CLAUDE_CODE_MAX_RETRIES=0 + DISABLE_NONSTREAMING_FALLBACK=1 +
  UNATTENDED_RETRY=0，源码 + CC 2.1.205 实测背书）；冲突检测（用户不得
  覆盖）；`assert_adapter_status_not_404`（CC 对流式创建阶段 404 绕过
  fallback 开关，adapter 任何错误路径不得返 404）。
- **P1**：host_launch.sh 固定 **CC 2.1.205 + sha256 校验**（原 `latest`
  不可复现）；session_deadlines/turn_seq 在 unregister 时清理（有界）；
  provider 同步 requests.get 保持同步但注释澄清它只在握手构造时算一次、
  不在 wire finalize 热路径。
- **CC 行为证据入库**（codex 本机 2.1.205 + fake endpoint，两份报告 +
  探针套件 + 34 个 JSON 证据）：500/429/断连指数退避实测、120s+ 无重试
  等待下界、404 fallback 例外、`proxy_deadline < CC API timeout <
  harness hard-kill` 不变量。**探针套件是版本画像/漂移检测器**，升级 CC
  必须先生成新证据人工裁决，不许改旧期望值让测试变绿。
- 测试 797 → 831。**明确留 FA-5 真机**（本机 fake endpoint 代替不了）：
  真 CC 二进制被 execution owner 主动终止（sandbox kill）、真 SGLang
  rid/abort_request 四方对账、容器内 tarball sha256/版本 fail-fast、
  pause_generation abort/hold 语义、Linux x64 vs macOS arm64 行为差异。
  **明确留 FA-2**：request/turn 级 capture 归属（改 slime record_turn 签名）、
  interim collector 替换为 assembler、worker 显式 recovery API。

## FA-1 follow-up 4（2026-07-13，codex 轮次 9：2 个确定性 P0 + 4 个接线缺口；
## 原文存档 `../s2/codex_reviews.md` 轮次 9）

- **P0-1（deadline 仍漏传——轮次 8 修复失败的修复）**：守卫 3 调用点真正
  传入 `deadline_monotonic`。**过程教训（重要）**：轮次 8 的修复用了无
  assert 的文本替换（静默未生效），而配套测试设 deadline=3 < 发前预算 5，
  在进入恢复等待前就以预算不足退出——**修复没生效 + 测试假阳性双重漏网**。
  新测试断言三件事：send 恰被调用一次（真进入 abort→恢复分支）、失败原因
  是 `version_did_not_advance`、失败时钟 ≤ episode deadline（不是独立 500s）。
  规矩固化：文本替换必须带 assert；修复测试必须证明"真走到了目标分支"。
- **P0-2（FIFO 乱序串账）**：轮次 8 的 FIFO 在并发完成乱序时会把请求 A 的
  token/logprob/weight_version 记到 B 名下（slime 同 session 请求是独立
  asyncio task、record_turn 按完成序到达；串账比丢数据更危险——结构合法
  内容错误的训练轨迹）。改 **fail-closed**：stage 遇 overlap → poison +
  两轮全 abandon（完成序未知，都不可信）+ `CapturePendingOverlapError`。
  含义：request 级归属（record_turn 传 request_id，改 slime 签名）落地前，
  并发同 session 模型调用（CC 并行 subagent）会 fail-fast——这是**正确性
  优先于可用性**的显式取舍，request 级归属定为 **FA-2 第一验收项**。
- **P0-3（formal 链没启用非零 exit 拒绝）**：接受 codex 对我轮次 8 理由的
  纠正——任务失败负样本 = CC **exit 0** + grader reward=0；CC 非零退出只
  可能是 harness/API/进程失败。启动断言强制耦合：`require_real_weight_
  versions=True` 必须同时 `reject_on_nonzero_harness_exit=True`；glue 默认
  联动（RH2_REJECT_NONZERO_HARNESS_EXIT 默认随 require 旗标）。
- **P0-4（poison 不主动终止）**：SessionPoisonRegistry 加 `subscribe/
  unsubscribe`（poison 同步回调通知，已中毒立即回调）；orchestrator 把
  harness run 包成 task，poison 即 `task.cancel()`——不再等 CC 自退（404
  fallback 已证明客户端自退不可靠）。取消区分：poison 触发 → 收口缺员
  abort；外层取消 → 原样传播。e2e 测试：挂起 driver 被主动取消 + abort
  形状 + 订阅清理 + sandbox 照常清理。
- **一般项**：404 守卫真接线——`rh2_no_404_middleware`（纯 aiohttp，路由级
  本地测试：未知路径/显式 404 → 503 + `x-should-retry:false`）+ install 时
  patch `BaseAdapter.__init__` 挂进 app；host_launch.sh **每次校验** sha256
  （缓存坏文件不再绕过）+ 临时文件下载 + 校验通过原子 mv；
  StaticActiveCoordinator 加 TTL 缓存（默认 2s——provider 是同步 HTTP，
  此前 proxy 热路径每次窗口读取都打一次引擎端点，32 路并发会串行阻塞
  event loop；版本至多滞后 TTL 秒，FA-4 用 consensus version 取代）；
  有界性收口：poison registry max_entries=4096 FIFO 淘汰、audit tombstone
  上限 8×max_artifacts（超限丢最旧只留计数）、weight_versions 随会话清理
  （registry 交叉检查从此只覆盖存活会话，如实降级）。
- 测试 831 → 835（+deadline 真分支、overlap fail-closed、poison 主动取消
  ×2、404 路由级、订阅即回调；净数受重写抵消）。
- FA-2 验收项排序更新：**第一项 = request 级 capture 归属**（改 slime
  record_turn 签名或 ContextVar 传 rid），落地后解除 overlap fail-fast。

## FA-1 follow-up 5（2026-07-13，codex 轮次 10：双线程拓扑 2 P0 + registry
## 并发/生命周期 2 P0；原文存档 `../s2/codex_reviews.md` 轮次 10）

本轮主题：**所有既有测试都跑在单事件循环里，而生产是"Ray actor loop +
aiohttp adapter 线程"双线程拓扑**——四个问题全是这个盲区的产物。

- **P0-1（跨线程取消不生效）**：poison 从 adapter 线程发出，回调里直接
  `harness_task.cancel()` 非跨线程安全（codex 双线程探针：task 未取消、
  账面却显示 subscriber 已处理——`_invoke` 吞异常加重了误导）。修复：
  orchestrator 捕获 `owner_loop = get_running_loop()`，回调走
  `owner_loop.call_soon_threadsafe(task.cancel)`；`notify_failures` 计数
  取代纯吞。新测试从**真 threading.Thread** 发 poison，断言 owner loop
  中的 task 收到 CancelledError（修复前该测试永久挂起）。
- **P0-2（middleware 没装到唯一的生产 adapter）**：glue 顺序是先
  `AnthropicAdapter(...)` 再 `install_capture_wire()`——构造器 patch 只
  影响之后创建的 adapter，对已存在的生产 adapter 无效（codex 探针：
  before=false / after=true）。修复：`ensure_no_404_middleware(app)`
  幂等直挂 + `assert_no_404_guard_installed` 启动前断言；glue 按生产序
  直挂到 `self.adapter.app`；测试按生产序复现（裸 app 断言先红后绿）。
- **P0-3（registry 跨线程丢通知竞态）**：check-then-subscribe 与
  poison-then-extract 之间的窗口会让回调永不执行。修复：threading.Lock
  原子化全部状态转换，回调复制后**锁外**调用（防死锁）；200 轮双线程
  barrier 交错测试钉死。
- **P0-4（FIFO 淘汰活跃毒）**：max_entries 淘汰假设"最旧已终止"但没有
  termination ACK（反例：max=1 时 A 被 B 挤出，A 的后续请求重新通过
  check）。重构生命周期：**active poison 绝不容量淘汰**（数量受 rollout
  并发自然约束），`release()`（= CaptureRegistry.unregister 的清理 ACK）
  后转有界归档摘要（归档后 is_poisoned 仍真，audit 面保留）。
- **一般项**：glue 配置**持久 artifact_sink**（落盘 ARTIFACT_DIR/
  model_call_audit/{attempt}.json，evidence_refs 从此指向外部持久路径，
  不受内存 tombstone 上限影响；正式链断言 sink 在场）；容器内
  `claude --version` **精确比较**（观测值含 RH2_CLAUDE_CODE_VERSION=
  2.1.205 才放行，结果存 self.cc_version_observed 供 startup evidence）；
  TTL 轮询的残余同步阻塞如实记录——FA-4 用 coordinator 发布的全引擎
  ACK consensus version 彻底替换（05 计划 FA-4 增补项）。
- 测试 835 → 852（+真线程取消、竞态窗口 200 轮、active 不淘汰、
  unregister→release、生产序 middleware；847 基线含并行 S2 变更）。
- codex 确认已修好的部分（轮次 9 全项）与"FA-2 第一验收项 = request 级
  capture 归属"维持不变。artifact sink 与容器版本断言已按其要求在租卡
  前完成，不留真机现场。

## FA-1 follow-up 6（2026-07-13，codex 轮次 11：2 正式链阻塞 + 2 身份/生命
## 周期项；原文存档 `../s2/codex_reviews.md` 轮次 11）

- **P0-1（启动探针必崩）**：轮次 8 把 `registry.pending` 改成
  `list[PendingTurn]` 时漏改了 `_run_startup_checks` 的消费点（仍按单对象
  取 `.raw_response`）——真实 GPU 启动会在训练前 AttributeError。修复：
  新增形状权威 `CaptureRegistry.single_pending_turn(sid)`（恰好一条；空/
  多条显式报错），glue 探针改走它；本地测试覆盖三种形状。**这是"改容器
  形状必须全仓搜消费点"的教训**——852 条测试没有一条走到该入口。
- **P0-2（正式链 sink fail-open）**：`_store_artifact` 此前吞 sink 磁盘
  错误退回内存 `audit:` 引用（磁盘满/权限错时训练继续、evidence 悬空）。
  修复：`ModelCallProxy(sink_required=True)`（glue 接
  `require_real_weight_versions`）下 sink 写失败抛
  `ArtifactSinkWriteError`（UnattributableModelCallError 子类 → 外层统一
  poison + 缺员）；bring-up 保留退回。glue sink 加固：sha256(attempt_id)
  文件名（清洗截断不再碰撞）、临时文件 + fsync + os.replace 原子落盘、
  内容含完整 payload sha256（repr 截断只是预览）、返回相对 opaque 引用
  （不泄漏绝对路径）；async_start 做一次 write/read/delete 启动探针。
- **身份 3（SID 复用 vs 毒归档）**：`_session_id` 的稳定 ID（task+index+
  group）跨补采/epoch 会复用。registry 侧兜底两条：`subscribe` 对**归档
  毒**也立即回调；`CaptureRegistry.register` 对中毒 SID（含归档）直接
  SessionPoisonedError（不让 harness 带毒起跑）。**execution 唯一身份
  （SID 绑 RolloutExecutionIdentity + nonce，poison 以 execution 为键）
  与 request 级 capture 归属并列为 FA-2 第一项硬验收**。
- **身份 4（release 不是真 ACK）**：轮次 10 把 release 挂在 unregister
  （drop_session 时）——但容器清理在其后。修正时序：unregister 只关会话
  不释放；orchestrator 注入 `session_poison_release`，在 finally 的
  `cleanup_completed` 之后调用（harness 终止 + 会话撤销 + 容器清理全完成
  才归档）。
- **一般项**：容器版本改 **token 精确比较**（子串判断会放过
  `12.1.205-x`）；`cc_version_observed` 落盘为独立 evidence 文件
  `cc_version_observed.json`（安装晚于 startup_evidence.json 写出，修正
  轮次 10 "进 startup evidence"的不实表述）；notify_failures 上锁 + 有界
  失败记录（64 条）；TTL 轮询/consensus version 如实递延 FA-4。
- 测试 852 → 870。codex 确认轮次 10 四项修复全部成立。
- **FA-2 第一项硬验收（更新）**：execution 唯一身份 + request 级 capture
  归属（两者一体：SID/poison/capture 都以 execution identity 为键）。

## FA-1 follow-up 7（2026-07-13，codex 轮次 12：abandon 绕过 fail-closed 的
## P0 + 重复注册守卫；原文存档 `../s2/codex_reviews.md` 轮次 12）

- **P0（abandon 路径绕过 sink fail-closed）**：轮次 11 的 sink fail-closed
  只覆盖 call() 内部；`abandon_delivered` 在 call() 返回**之后**被调，sink
  失败会抛 ArtifactSinkWriteError 但不经过外层统一 poison——draft 仍
  pending、账上零记录，且 unregister 的清理路径把异常当普通 cleanup
  failure 吞掉，**构造好的训练样本可能带着不完整交付账继续走**（codex
  确定性探针复现）。按其建议落三层防线：
  1. **评分/Gate 前边界断言**：`CaptureRegistry.assert_session_clean(sid)`
     （pending 暂存轮或该 sid 前缀的 unfinalized draft 在场 → poison +
     拒绝），orchestrator 注入 `capture_boundary_check` 在 assemble 前调用；
  2. **unregister 先 poison 再 abandon**：leftover draft 存在即先
     `uncommitted_draft_at_unregister` poison，abandon 的 sink 异常不传播
     （`abandon_evidence_failures` 计数可见）；
  3. **abandon 事务化**：先关 draft、落最小 FailureFact（evidence_refs=[]），
     再抛 ArtifactSinkWriteError——"抛了异常但 draft 还 pending"的中间态
     被消灭。组合测试按 codex 点名补齐（成功交付 + flush 失败 + sink 失败）。
- **重复注册守卫（FA-2 硬阻塞的临时挡板）**：健康 SID 并发重复 register
  此前会静默覆盖 hook/pending/weight_versions——现抛
  `DuplicateActiveSessionError`（顺序关旧开新仍放行）。FA-2 第一项验收含：
  并发同题组不共享 SID、attempt id 全局唯一、artifact 禁静默覆盖、poison
  按 execution 隔离。
- **一般项**：`_cleanup_container` 意外异常（docker socket OSError 等）
  结构化收口——CleanupFailureRecord(step=container_cleanup_exception) +
  `cleanup_quarantine` 隔离队列，异常不再覆盖 rollout 结果；**清理未确认
  成功时 poison 不 release**（active 保持拒绝力）。版本 evidence：进程内
  只写一次 + 临时文件原子 replace（并发竞写消除）+ 失败计数打印不静默。
  artifact digest 统一 canonical 口径（`canonical_artifact_bytes` 内外共
  用）；sink 文件已存在时 digest 相同幂等返回、不同即身份碰撞报错（禁
  静默覆盖）；契约显式定名 **digest-only evidence**（刻意不存完整私有
  payload——与密钥/最小化纪律一致，preview 有界）。
- codex 澄清其看到的 inspect 失败是并行 S2 线程的瞬时脏工作树（我方验证
  当前 PASS，bundles_v2/spec_vendor 已由 S2 线程收敛）。
- 测试 870 → 878。codex 认可"可以开始 FA-2，但先修本 P0 + SID 唯一化为
  FA-2 第一个提交"——本 P0 已闭合。

## FA-1 closure（2026-07-13，codex 轮次 13 完整审计第一批；原文存档
## `../s2/codex_reviews.md` 轮次 13——全链路审计，非增量 diff 审查）

codex 本轮从 slime 调用入口走完全链（RolloutManager→entry→worker→
orchestrator→adapter 线程→proxy→SGLang→capture→评分→collector→转换器），
判定："FA-1 不是失败实现……问题主要来自把局部正确组件接入真实三线程
拓扑、长运行状态和安全边界时的所有权缺口"。按其实施顺序执行第一批：

- **P0-1（未知 SID 直连 SGLang 的安全旁路）**：wire 对未注册 SID 从
  "直连放行"改 **fail-closed**（`UnknownSessionError`——旧行为 = 绕过
  proxy/poison/版本/deadline/限额/capture 的未登记推理代理，adapter 又
  绑 0.0.0.0）；新增 `build_session_guard_middleware`（bearer 能力预检：
  未知/已关/中毒会话 HTTP 层 403 + x-should-retry:false，不产生 SGLang
  请求；/healthz 放行），glue 挂到生产 adapter app。启动探针的会话是
  显式 register 的，不受影响。绑定地址默认值改动风险大（容器桥接可达性
  依赖 GPU 环境），FA-5 用 ADAPTER_BIND_HOST 显式设定——递延已登记。
- **P0-2（边界检查在 drain 屏障之前）**：`finish_session`（内部
  shutdown_session 才等/取消 in-flight turn）**前移**到一切检查之前；
  顺序改为 drain → poison 复检 → 非零 exit → 边界断言 → 冻结
  hook.records 快照。消除 false reject（正常轮还在 flush 就被拒）与
  false accept（drain 期间才 commit/overlap/sink 失败无第二次检查）。
- **P0-3（CaptureRegistry/proxy 非线程安全 + commit 中点悬挂）**：
  registry 全部共享容器进短临界区 `threading.Lock`（锁内只移动所有权，
  hook/磁盘/回调全在锁外）；commit 事务化 PENDING→COMMITTING→
  COMMITTED/ABANDONED——hook 中点异常 poison + abandon draft（codex 探针
  的"永久悬挂"消灭）；hook 后复检会话仍在（与 unregister 竞态时本轮
  poison+abandon，不给已销毁会话追加版本——KeyError('race_sid') 根修）；
  重复 finalize 不再静默吞 ValueError（poison + 计数 = 契约违规可见）。
  proxy 的 attempts_ledger/_pending_drafts 加 `_ledger_lock`。50 轮真双
  线程压力测试 + 中点异常 + 竞态复检三条回归钉死。
- **P0-4（limiter 假配置）**：model_call 限额真接生产 proxy（glue
  `model_call_limits`，env RH2_FA_LIMIT_MODEL_CALL；所有权 = adapter
  线程 loop）；评分并发接 GradingQueueConfig（env RH2_FA_LIMIT_GRADING）；
  FA 入口删掉无消费者的 model_call/grading_container 假键（只留 worker
  真消费的 sandbox 类，绑 AsyncLoopThread）——**不跨 loop 共享 semaphore**。
- **P0-5（FA 路径审计只在内存）**：orchestrator 注入 `audit_sink`，每个
  execution 终态写一次 `fa_execution_audit.jsonl`（steps/失败/清理/收缩
  + **按 execution drain 的 ModelCallAttempt ledger**——drain 后热内存即
  清，P1-4 的 ledger 项随之闭合）；正式链落盘失败 fail-closed 上抛。
  audit 增 `session_id` 字段（drain 键）。
- **P1-6（open_session 泄漏）**：glue PerRolloutAdapter.open 事务化——
  底层 open 失败回滚 registry 注册。
- **05 计划更新**：FA-2 分批重排（第一批 = F2-1~6 身份基座：身份贯穿/
  身份凭证分离/request 级归属/预取恢复语义三选一/collector 组不变量/
  attempt manifest；第二批才是 assembler 状态机）；§6.1 新增 P1×8+P2×4
  递延登记表；FA-5 验收增项 10 条；闸门重申（P0 已闭但 F2 完成前
  `rh2_fully_async_training_path_verified` 保持 false；StaticActive 在位
  期间不得声称生产透明重生成）。
- 测试 878 → 895。codex §8 确认的 15 项正确实现保持不动。

## FA-1 closure 批次 2 + 过度防御评估落地（2026-07-20，codex 轮次 14；
## 原文存档 `../s2/codex_reviews.md` 轮次 14——含对"过度防御"评估的裁决）

本轮双重输入：codex 对轮次 13 的复查（4 项仍需修正 + 测试缺口）+ 它对
我方"过度防御/可维护性"评估的裁决（八成同意，给出可执行设计规则）。

- **仍需修正 1（provider 无锁遍历）**：`_registry_max_version` 直接遍历
  `weight_versions.values()`——并发 commit/unregister 复现
  `dictionary changed size during iteration`（变成未归因 adapter 500）。
  新增 `CaptureRegistry.snapshot_weight_versions()`（锁内深拷贝）；
  `session_deadline`/`next_turn_seq`/overlap 路径 stats 增量一并补锁。
  双线程 churn+reader 回归测试。
- **仍需修正 2（审计非事务）**：先 `drain_attempts()` 再写 JSONL——磁盘
  满时既拒 rollout 又丢内存证据。改 **snapshot → 持久写成功（fsync）→
  ack 移除**（proxy 新增 snapshot_attempts/ack_attempts，drain 降为二者
  合成）。写失败回归测试断言 ledger 完好。
- **仍需修正 3（审计失败没有真 run-halt）**：正式链裸 raise 被 worker 当
  普通成员失败（codex 探针：failed=4、halt=None、继续 top-up）。新增
  `FatalExecutionInfrastructureError`；orchestrator 审计失败（正式链）
  包装之；worker `_account_failure` 识别后置 halt（WorkerHalted）。
- **仍需修正 4（审计丢时间线）**：记录补 `timeline_dicts()` /
  `timing_summary()` / disposition / eligibility_report_ref /
  delivered_sample_count / lease_released。
- **测试缺口**：drain 先于边界断言的顺序录制测试、生产装配 limiter 测试、
  open rollback 测试、审计成功/失败/Fatal 三态测试、worker fatal 停机
  测试——为此把 glue 的三个装配件提取为模块级可测函数
  （`build_production_model_call_proxy` / `make_per_rollout_adapter` /
  `write_execution_audit_record`，也是 F2-0 提升方向的第一步）。
- **设计规则采纳（写入 05 计划 FA-2A 节）**：F2-4 恢复语义先于 F2-1 编码
  定案（replay-stable 公开 id + 每会话新 capability + cursor 语义，拒绝
  裸 at-least-once）；F2-0 代码提升；poison 只绑 session/attempt 不绑
  任务槽位；**结构化终止枚举**（episode_time_limit 可为截断有效样本——
  事实纠正：slime 超时返回 EXIT_TIME_BUDGET_EXCEEDED=**-1**（sandbox.py:60），
  非我方评估里说的 SIGKILL/137；Docker RPC 超时才是 124）；require ↔
  非零 exit 启动断言**硬耦合解除**（轮次 14 推翻轮次 9，代码已改，glue
  默认联动保留）；熔断按 **fault domain** 六分类（不隔离任务的类别明确
  列出），载体 = Outcome + 纯函数 RecoveryPolicy + AdmissionReport，不
  新增报告层；正式训练闸门补两条前置（overlap 挡板已替代 + 熔断在位）。
- **文档收敛**：notes 顶部新增"⚡ 当前权威状态"页（有效机制 + 临时挡板
  登记表含移除条件 + 被推翻结论标注）——历史轮次保留为流水账但不再是
  现状权威；05 计划重启语义统一为"halt → 整 actor 重启"（FA-5 N6 场景
  改写）、顶部状态行更新；AGENTS/00-status 进度与测试数刷新。
- **环境漂移排查（本轮额外）**：全量跑出 1 个与 FA 无关的失败——
  `test_request_carries_token_ids_not_messages` 断言 `X-Session-ID` 精确
  大小写，而依赖重锁后新版 httpx/h11 把线上头名规范成 `X-Session-Id`。
  HTTP 头名按 RFC 9110 大小写不敏感，属测试过度约束；改为小写键匹配。
  排查过程排除了 openai 2.44/verifiers pin/renderers pull 三个嫌疑
  （逐层最小复现定位到 wire 大小写）。
- 测试 903 → 911。


## F2-1a 二审（2026-08-07，codex 复核 P0 → **修复循环熔断首次触发**；
## 原文存档 `../s2/codex_reviews.md`）

**熔断事实**：一审的 P0-1 修复（fail-closed setter）自身引入新 P0——
预登记的 paid 在 materialize 失败后永久残留（session_open 未置位 →
finally 不清理），而 fail-closed 又拒绝 replay 的新 paid → 可恢复的
基建故障变成该 SID 永久拒绝 + prompt group 持续缺员。按协议 §5"修复
引入新 P0"触发熔断：停止给 setter 叠补丁。

**根因分析**：paid 生命周期被拆成两个 owner——orchestrator 在 audit
构造时（T1）经 registrar 预登记，registry 在 open_session（T3）绑
hook，清理却统一挂在 T3 之后才置位的 session_open 标志。T1~T3 之间
任何失败（materialize 在 T2）都产生无主状态；一审只是把无主状态的
症状从"可被覆盖"改成"永久拒绝"，没有消灭无主窗口本身。

**替代设计（所有权收敛，codex 处方 + 实施）**：paid 与 hook **同生命
周期**——`register(sid, hook, physical_attempt_id)` 单锁原子绑定；
绑定发生在 open_session 事务内（materialize 之后），underlying open
失败走既有 rollback unregister 连带清 paid；drop 后整体释放。**删除**
预登记 setter 与 registrar 注入点——无预登记 = 无残留窗口（消灭状态而
不是防御状态）。验收：materialize 失败无残留、replay 新 paid 畅通、
open 失败整体回滚、活跃冲突仍拒绝、失败均有结构化审计。测试 930→931。

**提交纪律违规自查（codex 指出）**：`63e2772c` 因 `git add -A` 混入
约 2600 行非本切片内容。provenance 声明：`python_async_concurrency_
foundations.md`、`repo_harness_code_walkthrough.md`、
`rh2_training_path_and_batch_scheduling_tutorial.md`（增量）、
`training_design/repoharness_validation_experiment_design_review.md`
（增量）属**并行教学/设计线程**产出；`fa/fa_onboarding_walkthrough.md`
是本线程此前的走读文档。内容全部保留（不删并行线程成果），但该
commit 不可作为干净切片回滚单元——回滚 F2-1a 一审需按文件而非按
commit。纪律修正：此后 git add 只用显式路径清单，禁 `-A`。
