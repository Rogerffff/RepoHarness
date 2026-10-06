# Project-MONAI__MONAI-5932 — cross_review

审查者：e25_review_pack09_monai；日期：2026-09-25。root明确cross_review release后读取获准后稿/旧记录。

ROOT=`/Users/roger/Desktop/claude-code-verl-stage0h`；PUBLIC=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5932`；PRIVATE=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-5932`；本题主审稿位于`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-5932`。源码短路径相对PUBLIC/base。封存初判SHA256=`9a209c37e6efad9804ac6bcb0cb709eb9dc2649c0c55570c8f9391dfd8c0dacf`，本轮复验不变。

## 复审结论

支持主审将本题保留为 `needs_review/static_review`、仅供 `development_diagnostic` 的静态候选。公开目标、根因、全部gold和新断言、14个P2P语义及历史原命令/状态的判断，与我的封存独立初判相符。没有已证 gold 新增回归或当前 actor 开发资格。旧记录的 ready_for_probe、全面无泄露/无多进程判断不能继承。

本次不是按意见一致投票：决定性依据仍是 PUBLIC/base 的引用替换链、PRIVATE/test.patch 的公开返回值断言、run_refs 指定 ledger3/4 与两个原日志。新增阅读主审与旧记录后，核心技术结论不变；补充的是历史断言的证据分级、TimedCall 完整尾段与状态口径说明。

## 独立发现、交叉新增与分歧

| 项目 | 我的封存初判 | 交叉复核与最终判断 |
|---|---|---|
| 同式前缀故障 | 完整正则匹配被按出现顺序的全串replace破坏 | 主审独立描述相同；reference_resolver.py:212–244 与原noop SyntaxError支持，不依赖旧标签 |
| 新F2P语义 | A/A_B数值返回4，只一种两项短在前组合 | 主审给出更具体坏修法：简单反转匹配列表能过本例，却在长在前失败。由替换顺序静态可推出，未执行，不作为新的硬性验收 |
| 合理替代解 | 原串匹配跨度/正则callback，不必排序 | 主审一致；新增断言不检查内部实现。我初稿check24为限定意义pass，主审unknown更适合表达“没有普遍无误拒证明”；保留局部不锁算法正证据 |
| gold完整性 | 核心修复正确有正证据，check27 unknown | 主审结构记录check27=pass，但note明确仅核心且完整性unknown。事实无分歧，单状态口径有差异：若汇总不携带note，我建议仍用unknown，不能把该pass当完整正确证明 |
| 缺失引用+前缀 | 初稿仅列未覆盖组合 | 主审明确：缺失长引用continue后可能被短引用replace改写；路径原来就存在，不能据此称gold新回归。静态机制成立 |
| 多进程与helper | 初稿已读TimedCall前段，列进程需求 | 本轮补读tests/utils.py:605–637，确认返回值/异常/timeout传播；旧“无多进程”“helper只影响skip/超时且没有正收益”不成立，主审delta的纠正准确。攻击可达性仍未审 |
| 其他题关系、skip parser | 初稿未读旧主张 | 本轮只读指定旧record；MONAI-6756关系与SKIPPED→缺席→失败链仅有旧自述，不沿链接核其他题/parser，主审保留unknown正确 |

主审card中的“全14 P2P语义已读”与其前稿逐项表相符；我的初判也独立读完全部定义。`test_parse_0`的torchvision守卫是真实公开代码，历史本次实际PASSED，不能把条件性风险写成当前环境故障。额外公开reference_resolver测试不在历史pytest选择中，双方均未混入15项历史结果。

## 旧记录逐类核验

获准旧件为 `ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_2/records/Project-MONAI__MONAI-5932.json`；SHA256=`574f987d1cb269131ee8c08edeaf2286e8b7ee8485cdab8da870b7914f20fed1`，本轮字节hash与history refs一致。

- 旧1/2/23/27：根因、公开同构算式、局部gold正确，由本轮已读源码与09-19授权原运行独立支持；不继承旧stage1结论作新的运行证据。
- 旧3/29：计划题面完整且无修复代码，不能证明实际actor全部输入/可见材料；当前public_bundle有hints字段，旧raw hints为空不是当前交付事实。主审改3/29 unknown正确。
- 旧25：两引用形状有限属覆盖问题；整串引用的旧分支并非完全没有P2P覆盖。反转顺序变体是有效具体限制，不能把所有建议都当原题明示要求。
- 旧26：14 P2P有实质作用，但不证明无gold回归。主审26 unknown、25 issue分类准确。
- 旧13/31：TimedCall启动spawn/Queue/Process并执行被装饰函数、传播异常；旧描述不准确。旧定位torch.rand在TEST_CASE_1也不符已读test_non_str_target。不能从测试恢复清单直接证实任意候选攻击能力，更不能证明修改helper无收益。
- 旧5/19的外题/评分链原件未开放，不确认亦不否定；旧ready_for_probe和16分钟不转成当前资格/成本。

## 原件与运行边界复核

原件详表保存在封存reviewer_initial.md，此轮未重复执行项目。历史原命令是 `pytest -rA tests/test_config_parser.py`，15 collected；noop唯一F2P SyntaxError、14P2P pass，RC1；gold15 pass、RC0，expected逐ID无skip/xfail/缺项。四条安装命令和last-command RC0已保留；不能将其等同所有准备阶段普遍可恢复。日志未提交diff为MetricsReloaded依赖删除，gold另加resolver改动，邻近git show是base提交内容。actual image ID=null；源码版本、expected manifest digest、scripts_digest与实际运行ID边界均被主审保留。

八方面已复核：公开目标；静态版本/实际初态区分；完整新assert/helper/P2P；合理替代与覆盖缺口；gold/调用者和未知回归；开发依赖/权限/资产；可信恢复/候选投影和评分状态；私有暴露/用途/偏差。实际actor消息、初态、权限、工具、网络和源代码导入仍unknown，历史grader的54322身份不是actor身份。

## screening_record结构与状态审查

本轮用stdlib JSON读取全文并检查：13个必需顶层字段恰好齐全；所有checks均含status/evidence_refs/by，编号属于原1–40；所有issues均含category/scope/evidence_refs/proposed_action/status。additional_exclusions=[]、revision_refs=[]；disposition为needs_review/static_review；usage.intended_use=development_diagnostic；未观测token/货币/current_cpu_seconds均null。历史运行成本单列facts，不混为本次成本。所有被引用的证据路径来自本题已授权材料或主审/旧record，未沿未开放链接扩读。

3与23分开、25与26分开、29与usage分开、40 unknown均合规。9/16–21的pass notes明确限制为本题历史noop/gold，我接受其局部证据含义，不能当当前actor/任意候选通行证。27的pass/unknown口径差异见上表；主审已显式写完整性unknown，不要求改写封存初稿。主审usage.reviewer_read=false描述其出稿时状态，不能当本轮reviewer尚未读取的事实。

## 当前保留问题

| category | scope | evidence_refs | proposed_action | status |
|---|---|---|---|---|
| coverage_gap | check25，同式前缀变体 | PRIVATE/test.patch；base/reference_resolver.py:212–244 | 保留单例边界；如未来修改验收应依据公开完整ID语义，不锁gold算法 | open_static |
| actor_evidence_gap | checks3/4/6/8/10/33 | PRIVATE/environment_record.json；PUBLIC/environment_brief.md | 按唯一下一步取得实际公开开发证据 | unknown |
| historical_claim_unverified | checks5/19/31 | 指定旧record；主审old_findings_delta | 需要相应决策时再由获授权者核外题/parser/控制面，当前不继承标签 | pending_verification |
| status_scope | check27 | screening_record.json#/checks/27；独立初判 | 汇总保留“核心正证据、完整性unknown”；若只有单状态建议unknown | documented |

## 唯一优先下一步

由任务二在正式actor入口记录实际消息、HEAD/status/diff（输出/RC/阶段）、UID/HOME/cwd/PATH、解释器和monai.__file__，执行公开题面ConfigParser内存算式及窄公开parser/resolver测试。base应暴露目标SyntaxError，修后应得到4；将skip、目标失败、环境阻断分开。该步骤能改变当前“只有历史grader局部正证据”的判断。不派发、不执行任务二，不要求全仓、GPU或附加反例实验。

## 读取与暴露登记

封存后新增完整读取本题public_read、analysis_before_history、old_findings_delta、card及screening_record JSON（长路径输出曾截断，随后全量JSON解析并逐check/note、issue和引用集合窄输出补核）；history refs及其中唯一旧record；本题tests/utils.py:605–637补充尾段。其他源码与原运行实读范围沿独立初判，不借主审阅读范围声称自己读过。未读MONAI-6756、旧stage1/parser/控制面链接、模型轨迹、其他包/聚合或未授权材料。

审查者私有暴露已包含本包gold/隐藏test/expected、原运行、本题公开读者及主审和旧record；不能进入solver。此次只写review.md，初稿SHA保持。全程静态，无项目导入、测试、网络、容器、实验或子agent；不能据封存流程证明check40无漏检/误拒/偏差。
