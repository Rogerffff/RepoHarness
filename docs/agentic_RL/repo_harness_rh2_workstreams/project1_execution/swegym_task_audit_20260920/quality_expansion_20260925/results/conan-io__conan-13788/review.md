# conan-io__conan-13788 — 独立交叉复核

结论：维持 `needs_review / static_review`、`development_diagnostic`。局部同名host/build碰撞和历史noop→gold目标分差成立；gold对普通build-context传递依赖的fallback有明确静态疑点，尚未运行。接受主审保留check26/27 unknown；不接受旧记录用9个P2P推导gold完整正确。

## 阶段、暴露与实际复核

/root明确 cross_review release后，读获准public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，及history本题refs.json唯一指定旧记录。未沿旧hints/stage1/扫描/仓库汇总或跨题链接扩读，未读根汇总。封存reviewer_initial.md仍为 `3ab0e3b373f8649d72205bccd4037b9ad56303e5783ad2f8ea2e132244f9a08b`，未改。

完整F2P/9P2P、新断言/helper、gold/调用者及原日志的第一阶段阅读范围见初稿。交叉核查在已有直接证据上对照主审关键段与历史文本；大合并输出截断后用分段/结构字段提取补核，没有把截断或其他角色的阅读量算成自己的。新增直接读取build_requires_test.py:334–360的profile覆盖断言；conans/test/.gitignore、conftest.py:178–205；在本题conftest/tools.py限定检索default_profiles/conftest_user；完整补读两份run_refs授权diagnostics，并机械比对record选中运行字段与原ledger15/16行。未执行项目/测试/导入/安装/网络/CPU或攻击，唯一新文件为本review.md。

## 核心技术及历史处置

| 主张/风险 | 原件支持及复核结论 |
|---|---|
| 用户问“是否禁止”不是全局禁止规格 | 公开graph_manager既以(name,context)管理，旧双context/不同消费者版本测试允许多节点；补读profile_override还直接要求profile Tool0.3覆盖recipe版本而不报错。公开reader的同方向分析有原件支持；旧“题面方向相反，所以禁止解应算正确”须纠正 |
| 目标F2P真正暴露锁重放错误 | 新True为force_host_context，False为普通host要求；原noop在第二次install成功后缺tool4.0字符串，首个断言已过。gold10项全过，实际版本输出被pytest截断，不能声称完整原依赖图已取得 |
| 不同context联合匹配能修局部碰撞 | graph_builder为build requirements赋build_require_context，lock_node原name字典会覆盖；Requirement.lock真实改ref/range_ref/locked_id。原gold绑定与局部运行构成正证据，不能推整体正确 |
| 10项不含build工具的普通依赖 | 新tool为空recipe，旧双context protobuf也无普通requires；False是普通host依赖。各P2P实际语义已在独立初稿逐项核过。旧“9P2P守住双context，所以回归pass”的结论超过覆盖 |
| build普通传递依赖疑点 | 普通Requirement.build_require_context默认None，非context_switch的新图节点继承父context，GraphLock记录目标context；gold把None固定解释为host。T是build、T普通依赖D也是build时可能查(D,host)却仅有(D,build)。主审与我初稿都由此链独立得到疑点；一致不增加证据等级，仍未运行 |
| 新断言只查tool4.0不是完整锁一致性 | 不直接核profile的3.0、锁边、context或cache变化，可能漏掉不完整修复。不能据未执行的“忽略lock/重新解析”想法宣称已经验证作弊成功。完整锁行为比输出子串更强，但后续断言须对应公开语义 |
| 可选conftest_user存在，actual利用未知 | 本题conftest仅try-import tools_locations；限定检索未见default_profiles，不能复制2.x配置影响。文件被.gitignore忽略不自动证明它会进入当前candidate投影或绕过可信恢复。旧记录同时说1.x不消费default_profiles又称影响更大，自相矛盾；主审纠正成立 |

**术语修正（仅在本review说明，不改封存或主审文件）**：主审old_findings_delta.md在check26对应行写“普通Requirement.context=None”不准确。源码实际字段是 **`Requirement.build_require_context`**；图节点的 **`Node.context`** 和锁节点的 **`GraphLockNode.context`** 是另两个属性。准确说法应为“普通requirement的build_require_context=None，而build父节点的普通子图节点继承Node.context='build'，gold查询默认host”。这处简称/笔误没有推翻其调用链，但必须在后续摘要使用准确字段。

旧记录SHA `7876fdd3127594308e30a856ea2fd8c7d4d8a5e1ef807dddb6f3a826c9dd4748`已核。delta对各旧主张的处置有依据：hints字数/内容、旧stage1与扫描原件未开放，因此只记旧主张，不当当前消息事实；09-19本题RH2能独立支持1F2P+9P2P的窄分差。用户缺复现仍为规格缺口，但“必须记忆才能做”“盲解禁止分支是公平误拒反例”未证。python_requires独立字段/访问不能仅凭名字断言与本次索引共享，所以不机械扩跑。全tests清理/新增排除不获当前交付证据支持。

## 原运行、环境和八方面限制

精确w01-2 ledger:15/16与run_refs、record的patch hash、日志hash、included_paths、RC机械比对一致；历史candidate只改graph_lock.py，base/stage指针为c1b3978914dd09e4c07fc8d1e688d5636fda6e79。原测试命令 `pytest -n0 -rA conans/test/integration/graph_lock/graph_lock_build_requires_test.py`，noop RC1/1failed9passed、gold RC0/10passed，均collected10，无skip/xfail，parsed=10/段外0/reference_missing和skipped空。安装三个requirements命令最后RC0；3个DeprecationWarning不是测试skip或安装失败。诊断SETUP_OK/PROTECT_OK=1只能证明已知noop/gold条件下的局部处理。

`git show`中VS2017变动属于base提交展示，不是初始未提交差异；历史noop git diff为空、gold只有目标diff。actual actor HEAD/status原输出及RC/阶段、源镜像规定初改、忽略资产、UID/HOME/cwd/PATH/导入/权限仍unknown。expected manifest digest、actual image ID=null、scripts digest分别保留；grader workspace import/1.60.0-dev不是当前actor资格，也不是用户1.59现场复现。

八方面（版本初态、公开目标、断言覆盖、gold回归、评分执行、开发需求、暴露/提交边界、用途和流程偏差）的实读范围均能由初稿/主审找到，不存在“八项全pass”的虚构门。缺口仍包括全仓/完整调用者、parser实现、真实actor、所有替代解、跨集重复/留出重叠与真实模型结果；没有从材料未导出推断镜像缺资产。

## 结构与独立初判差异

stdlib JSON验核通过：13个必需顶层字段齐全；36项稀疏checks保留原1–40编号与允许状态，各有status/evidence_refs/by；issues有category/scope/evidence_refs/proposed_action/status；additional_exclusions=[]、revision_refs=[]；disposition=needs_review/static_review、usage.intended_use=development_diagnostic；未观测成本null。checks中未列12/14/15/22视为not_checked。实际actor check3与规格23分离，25缺覆盖不冒充26已证回归，27局部正证据与完整性分离，29 unknown与usage的合法审查暴露分离，40 unknown不以封存合规作无漏检保证。

我初稿24=pass只限定“未见实现形状断言”，主审24=unknown额外保留未测替代解公平性；本复核采用unknown并保留这条局部正证据，避免把无结构断言扩成无任何误拒。1的pass/unknown、9的unknown/pass差异也来自静态材料/历史候选与当前actor的不同scope，主审note已明示，不要求改稿。26/27与我的独立初判均unknown；未因交叉一致而升级为已证回归。card/record的reviewer_result未取得是释放前快照，协调者可引用本review更新收口状态，我未改主审稿。

唯一优先下一步仍是**任务二同条件base/gold私有CPU验证root→build T→普通D的双profile锁重放**。三节点空Python recipe即可，使用主审的 `conan lock create root/conanfile.py -pr:h=default -pr:b=default --build --lockfile-out=conan.lock` 后 `conan install root --lockfile=conan.lock --build` 路线，记录RC、lock的T→D context、实际错误与源码生效。该lock create路线先保留待构建状态，与“先install生成已含prev的锁再强制build”不同；若采用我初稿install生成完整锁的路线，第二次install无需强制--build，避免把已锁prev的重建限制混入目标疑点。具体命令仍须任务二按实际入口记录环境和生成fixture，不当现成运行结果。

若base可重放而gold在D锁定处失败，才把26升级为已证功能回归；若gold成功，应保存实际图与调用证据解释静态推断为何不触发。两题历史grader成功均不解除actor待验。无需先全仓或机械补第二个反例；含gold环境与私有结论不得交给独立solver。

## 精确审查材料

- [reviewer_initial.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/reviewer_initial.md)；SHA256 `3ab0e3b373f8649d72205bccd4037b9ad56303e5783ad2f8ea2e132244f9a08b`。
- [public_read.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/public_read.md)；SHA256 `7b79f4b0ecaeb8ac819931f1b65b80c26aba168fea6b4d5534c34beba8b46eb9`。
- [analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/analysis_before_history.md)；SHA256 `508a697338f38cdde6e9b6cc111654d60d4f72a64be8e6e0312707a0aee81c95`。
- [old_findings_delta.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/old_findings_delta.md)；SHA256 `0ccc7a47141fc7f1b115c04e6718d0d8d80e6836d5f89f86f6efb9a431131606`。
- [card.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/card.md)；SHA256 `6fdba2744a0f33f9133062ae0a42d4a526e8afd76d6bffcec81358dcc9dcacdc`。
- [screening_record.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788/screening_record.json)；SHA256 `4be363e110f01721ff8f0c5784379422bcf2835280bc08c279238d760c5eab35`。
- 唯一获准旧记录：[conan-io__conan-13788.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-13788.json)。
- 公开源码根：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788/base`；原运行精确引用根：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788/run_refs.json`。

本次by=reviewer_pack10_conan；审查者已接触本包两题gold、隐藏测试、主审与获准旧记录；actual actor私有暴露unknown。成本tokens/usd/current_cpu_seconds均null。无生产/题目修订，无新排除，无项目执行。
