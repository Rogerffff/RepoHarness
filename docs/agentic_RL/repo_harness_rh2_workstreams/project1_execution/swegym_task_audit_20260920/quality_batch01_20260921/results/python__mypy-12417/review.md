# python__mypy-12417 — 独立复核

**复核建议：保持 needs_review / static_review，仅用于 development_diagnostic。** 同意主审确认目标崩溃、gold 的局部修复和三个 P2P 的实质保护；也同意将错误恢复验收争议保留为未执行的具体假设。建议修改下一步对照：除主审的 base/gold/early_non_match 外，加入我在封存初判提出的保留 current_type 候选。它与 gold 的预计差异较窄，能单独检验 subject 必须变 Any 的要求。两条替代路线都未经 CPU 验证，当前不登记误拒、不裁定 gold 错、不改原题。

## 封存、暴露与原件边界

日期：2026-09-21；reviewer：review_mypy_tail，未参加本题主审。[独立初判](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/reviewer_initial.md) SHA-256 为 `f41bb7a2d7b5ff87156ae1c2b99a120eee0fdaa95876b3a7bdbd58fc501d2f3a`。两题初判全部完成并由协调者核 SHA 后才开始本阶段；初判保持原字节。

本阶段完整读了本题 [public_read](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/public_read.md)、[analysis_before_history](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/analysis_before_history.md)、[old_findings_delta](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/old_findings_delta.md)、[card](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/card.md)、[screening_record](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417/screening_record.json)，以及 [history/refs](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/history/python__mypy-12417/refs.json) 唯一指定的 [历史原件](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-12417.json)。另读同样获准的 16963 第二阶段材料；未读 10424、acceptance 或其余题历史/结论，没有沿 environment_record 中旧汇总链接扩展。

第一阶段已直接读本题 public/private、全部新增断言与 gold、相关旧测试/runner/fixture、指定 image/build/ledger/log，并作本地 JSON/patch/hash 核对。本阶段补核下文列出的 binder/分支/旧错误恢复代码、默认 typing/dataclasses stub 与 CLI 退出逻辑。主审另报告的 ingest 第 199 行三份逐对象匹配，本 reviewer 未重读三条原 ingest；不能算作我的新增独立核对。环境摘要的 both_roles=true 已暴露，指历史 gold/noop，未当作 actor/grader 两身份均通过。

以下 `S=${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base`；`D=${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-12417`；`E=${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417`。所有源码位置限定 base `47b9f5e2f65d54d3187cbe0719f9619bf608a126`，mypy0.950、Python3.10。

**没有执行项目、安装、Docker、SSH、模型或任何新 CPU 实验。** 以下“历史执行”是重读冻结的 09-19 RH2 原件；候选输出全部是静态预测，不能与真实得分混写。

## 原始需求、全部断言与保护范围

公开原例 `o: object; match o: case xyz(): pass` 的目标是未定义类名不触发内部错误。S/mypy/semanal.py:3788–3803、4288–4293、5097–5098 给出先检查 class_ref 并报告 Name 错误、未绑定 node 仍为 None 的路径。S/mypy/checkpattern.py:459–466 的断言解释原始 traceback；历史 noop 也实际命中此断言，但运行的是两种带捕获隐藏输入，零捕获公开原例没有独立运行。题面未规定恢复后 subject/capture 的唯一类型或所有附带诊断。

| 要求 / 行为 | 来源 | 测试及全部决定性断言 | 复核范围 |
| --- | --- | --- | --- |
| 未定义类名正常诊断且不内部崩溃 | 题面与 semantic 名称查找 | F2P testMatchInvalidClassPattern 的 xyz(y)、xyz(z=x)，各一条 Name "xyz" is not defined | 主错误合理；历史 noop 在该入口崩溃、gold 通过。零捕获共有入口为静态支持。 |
| 第一个无效分支 subject 变 Any | 公开未指定这一恢复选择 | 同一 F2P 的 reveal_type(m) = Any | 恰是 preserving-current_type 候选的预计失配行；需要执行。 |
| 位置捕获不推断且给后续错误 | 已有 Var 未就绪规则；是否保持空 captures 是恢复选择 | reveal_type(y)：Cannot determine type of "y"，然后 Any | 两条正式 expected；gold 可达分支+空 captures 产生。 |
| 关键字捕获同样恢复 | 同上 | reveal_type(x)：Cannot determine type of "x"，然后 Any | 两条正式 expected；第二个 match 没有 m reveal。F2P 共七条输出，不能缩为“不崩即可”。 |
| 有效 dataclass 位置捕获 | base:570–584 | P2P testMatchClassPatternCaptureDataclass：i=str、j=int | base/gold 两端真实通过，保护精确类型。 |
| match_args=False 禁止位置捕获 | base:586–599 | P2P …NoMatchArgs：缺少 __match_args__ 错误 | 真正负行为，不能泛称三 P2P 都只查 reveal。 |
| init=False 字段不计位置、有效分支仍工作 | base:601–616 | P2P …PartialMatchArgs：过多位置错误，以及下一分支 k=str | 正负约束同在一个 case，两端通过。 |

第一阶段已读 data-driven runner，确认反斜杠续行合并、E/N 展开、临时输入与 fixture 装配、build.build 和整个错误数组比较；不是只收集 nodeid 或搜索 gold 文本。F2P 没有专用 fixture，但依赖默认 lib-stub；P2P 使用 dataclasses builtins fixture、dataclasses stub 与 plugin 生成的 __match_args__。本阶段补读 lib-stub/typing.pyi 与 lib-stub/dataclasses.pyi 全文，补足初判读取范围。case 输入只交给 mypy 分析，没有执行输入中的 xyz。

三 P2P 确实会阻止“所有 class pattern 都返回 Any/空 captures”的粗暴修法；两端四项实际选中，10300 deselected 不算回归通过。其余已读 class pattern、alias、keyword、继承等旧测试只是静态相关证据，不是假称额外 P2P 已执行。

## 两种替代 guard 的可达性与预计差异

只考虑在 `type_info = o.class_ref.node` 之后，把原 None 断言改成局部 guard；不改正常 TypeInfo/TypeAlias 分支、runner 或 expected。四个版本的静态区别为：

| 版本 | None 分支返回 | 无效分支 body | 隐藏 F2P 静态预计输出 |
| --- | --- | --- | --- |
| base | 原 assert | 到达断言即内部错误 | 历史已观察 Name 错误后 AssertionError。 |
| gold | PatternType(error Any, error Any, {}) | 可达，仍检查 | 七条输出；仅这一版本已有历史 F2P 通过记录。 |
| reviewer 候选 P | PatternType(current_type, current_type, {}) | 可达，保留当前 subject 信息 | 仍有七条；m 预计为 builtins.object，另外六条与 gold 一致。未执行。 |
| 主审候选 E | self.early_non_match() | binder 标为不可达，跳过 body | 预计只剩两条 Name 错误，少五条 body 输出。未执行。 |

这不是从 gold 输出猜测实现，已沿原始调用者核查：

1. [checkpattern.py:459](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checkpattern.py:459) 在 guard 前已经取得 `current_type = get_proper_type(self.type_context[-1])`；两候选可以在同一 None 入口返回，无需解析未绑定节点或处理位置/关键字子模式。捕获数量不改变能否到达 guard。
2. [checker.py:4109](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checker.py:4109) 第一遍收集 captures、第二遍缩窄并检查 body。三方案 captures 均为空，不为 y/x 建立推断类型。
3. P 的 type/rest_type 都是当前 object；[conditional_types_to_typemaps:5730](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checker.py:5730) 为 subject 建 object 映射，而非 None 不可达标记；push_type_map:5555–5560、binder.put:138–148 存该类型。checkexpr.py:4238–4260 读取限制，meet.py:58–65 在 declared==narrowed 时保留 object。因此首个 F2P 的 m reveal 预期是 object，且 body 仍可达。
4. E 的 helper 在 checkpattern.py:669–670 返回 UninhabitedType/current subject/空 captures；checker.py:4131–4134 调 push_type_map(None)，binder.py:150–162 标记不可达，visit_block:2139–2151 随后停止检查分支语句。因此 body reveal 及 y/x 的 Cannot determine type 都不会产生；更早的 Name 诊断不被删除。此预测限定无 guard 的现有 F2P，不能把所有 guarded 模式行为一概而论。
5. gold 与 P 的空 captures 均让 y/x 保持未就绪；checkexpr.py:264–277 与 checker.py:405–419 解释后续 Cannot determine type/Any。P 仅保留已知 subject 的信息，并未自行给捕获变量补类型。三项 dataclass P2P 的 class_ref.node 非 None，三种局部 guard 静态都不改其原路径。

**合理性判断仍未闭合。** P 的优势是继续检查 body，同时保留已声明 subject 类型，能把差异集中到一条 oracle 要求；但尚未验证 OR 子模式、guard、后续 case、函数内延迟检查等上下文，不能先命名为“已知正确解”。E 的跳过策略会同时抑制 body 中与错名无关的类型错误，确实改变更多行为；然而这也不能直接证明 E 不合理：同一函数对 filled generic alias、非类型 class_ref 等走 early_non_match，旧 testMatchClassPatternCaptureFilledGenericTypeAlias（base:689–703）及 testMatchClassPatternIsNotType（861–868）有 body reveal 却不期望 note，说明跳过部分无效分支是已有惯例。

反过来，主审历史差异稿指出的 Any 惯例也成立：checkexpr.py:258–260 对 unknown reference 返回错误 Any；checkpattern.py:576–580 对无效 keyword 类型同样使用 Any。这解释 gold 的选择，却不能自动推导必须把已知 subject 也改为 Any、同时让捕获产生额外错误。该入口在 base 必崩，尚无旧的 m/y/x 后续输出可作为唯一兼容契约。精确输出比较本身不是问题，争议是这个新增恢复契约是否排除符合公开要求的另一种实现。

## 主审、历史与独立发现的对照

| 决定性结论 | 复核结果 |
| --- | --- |
| gold 是局部 guard，未见正常模式回归 | 同意其限定范围。None guard 位于零/位置/关键字捕获分歧前，依赖符号已有导入；历史 gold 四项通过。未因此宣布所有上下文正确或公开原例已实跑。 |
| public reader 不能从公开材料推出唯一 Any 恢复 | public_read 独立指出两种旧惯例；我在读它之前已发现 P 候选及恢复不唯一。多方静态重合支持需要对照，不能代替对照。 |
| 主审以 early_non_match 作为唯一优先替代 | 修改实验设计，保留其候选并加入 P。P 的预计差异仅一条 subject note，E 的预计差异五条及 body 可达性不同；只测 E 会把两个问题混在一起。 |
| 旧报告“近乎唯一实现；完全合理解被判 0” | 不采纳。历史原件明确 runtime_evidence 无，也没有该候选日志；静态预计评分失败不是实际 RH2 判零，合理性更未实证。主审已撤回这一口吻，纠正恰当。 |
| P2P 是子串过选产物，因此非设计、应全文件回归 | 不采纳动机推断。原始 -k 的子串形状与恰好四项执行是事实；为何选这些参考项不能据此得知。优先比较三 P2P 与两项直接恢复惯例控制，不把全文件未跑自动记为回归。 |
| 原报告无 runtime / F2P 无 fixture / traceback 属泄漏 | 分别更新为：本题 09-19 grader 原件已有执行；F2P 使用默认 stubs；公开 crash traceback 本身不等于未来修复泄漏。实际镜像/挂载/网络答案可达性仍未知。 |
| 应加全仓目录排除，或按同主题题目归族 | 不采纳。未执行 helper 攻击、未查对应平台版本；没有具体谱系即不追加规则。additional_exclusions 维持空，未改共享实现。 |
| 旧 ready_for_probe → 当前 needs_review | 同意。actor 条件及恢复契约尚未验证；本次独立 review 补足 reviewer 角色，不能把其他未决项自动变 pass。 |

我独立提出的 P 候选是对主审实验设计的实质补充，不是新的已证实缺陷。初判对 E 抑制独立 body 错误的担忧仍保留；本阶段补读两项旧错误类模式 body 的 expected 后，应更明确承认 E 具有真实公开先例，不能仅因“跳过 body”否定它。两者优先级不同、合理性均待验，不需要强行消除这一判断差异。

初判还直接观察到 16963 的更晚公开 base（checkpattern.py:520–522）已含本题 gold 的同形 guard。这比历史“同文件/同主题”更具体，但只证明该源码内容已存在另一授权 base；没有读取 Git 谱系，也不因此把 TypedDict 构造问题与本题当作重复任务。

## 八方面、原始执行条件与下一步

| 方面 | 已核 | 仍未知 |
| --- | --- | --- |
| 公开需求 | 四行原例、traceback、semantic 正常错误、两种旧恢复惯例 | 真实 hints/消息渲染；该入口恢复策略是否有未见契约。 |
| 材料与初态 | base/patch/validation/hash，历史 noop 同 assert | 零捕获原例没有独立 CPU 记录。 |
| 测试测量 | 七条输出、runner/stubs、三个 P2P 正负行为，四项历史实跑 | 零捕获、后续分支/OR/guard 不在当前参考集。 |
| 合理解接受 | P/E 两候选的源码可达性与区别已核 | 没有替代实现的执行、实际得分或完备正确性。 |
| 回归/gold | guard 与 PatternType 两遍调用者，dataclass plugin/旧 case | 仅三 P2P 动态通过，其他读取不算通过。 |
| 开发条件 | 本题离线 image/build、安装与 /testbed 导入记录 | agent/54321 的 Python、激活、安装权、资源与配方消费。 |
| 交付评分 | gold 仅 checkpattern.py 投影；官方恢复 check-python310.test | helper/fixture 的实际防篡改、共享 runner 对照、真实资产泄漏。 |
| 关系用途 | 修复内容已在 16963 base；所有私有暴露已标记 | 不据主题推重复，不据静态推模型难度/能力，不能正式准入。 |

本题 [配方](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/image.json) 派生镜像为 `sha256:854faf11b77e78836444b9be7ef9c2fea5255da422fac6aa07dead9e7a63cca7`，只加入 setuptools72.1.0、wheel0.43.0、packaging24.1 的离线构建 wheels。历史 Python3.10.14、pytest8.3.2、xdist3.6.1；真实命令 `pytest -n0 -rA -k 'testMatchInvalidClassPattern or testMatchClassPatternCaptureDataclass'`。gold 安装/测试 rc=0/0、F2P1/1、P2P3/3、reward1；noop=0/1、F2P0/1、P2P3/3、reward0。均 rh2grader/54322、2CPU/4GiB、deny_all，import /testbed/mypy/__init__.py。不得套用 16963 的 eight-pin、Python3.12 或 11-worker 条件。源码收集门槛是运行解释器至少3.10，不是只设置 target version 即可。

**唯一优先 CPU 对照：同一固定配方、同一 base，隔离比较 base、原 gold、P、E 四种源码状态。** 此为对主审单组对照的扩充，未创建补丁、未执行：

1. 原封保存公开零捕获例，用 `python -m mypy --config-file /dev/null --no-incremental --python-version 3.10 --show-error-codes --show-traceback /tmp/review12417/original.py`，记录普通 Name 诊断、INTERNAL ERROR 与退出码。S/mypy/main.py:112–141 支持普通非 blocker 错误为1；不能把 pytest 正常校验预期错误的 rc=0 与输入 CLI 的 rc=1 混淆。
2. 特权调查侧注入原 test.patch，按原四项参考集评分，逐项保留原始诊断与 RH2 得分。预测需检验的是 P 是否只在 m 的 object/Any 一行失配、E 是否只剩两条 Name；若实际更复杂，重新检查候选，不按预测填结果。隐藏材料不提供给未来 solver。
3. 三个已列 P2P 之外，补跑公开的 testMatchClassPatternIsNotType 与 testMatchClassPatternCaptureFilledGenericTypeAlias，作为“已知无效类模式可以跳过 body”的控制；这两项不会擅自加入冻结 P2P 或改变当前分数。
4. 一份小的观察输入同时包含已知 object subject、无效 xyz(y) 分支中的 subject reveal 与独立 `n: int = "bad"` 类型错误、随后有效 `case int()` 的 reveal，以及 match 后的 subject reveal。比较 P/E/gold 的 body 与后续分支行为。E 跳过无效 body 是预期策略差异，不能单凭少一个独立错误就宣布不合法；需结合既有恢复约定判断。P 若也出现隐藏崩溃、错误缩窄或相关旧行为破坏，就撤回其候选资格。

只有某替代实现消除公开/相关捕获崩溃、保留应有主错误及相关旧行为，却因公开未指定的恢复选择被参考集拒绝，才能记录有界误拒证据。若对照说明现有 Any 恢复具有必要兼容性，则收窄或撤销该疑点；不要先照抄 gold 输出进题面，也不要预先把验收放宽为任意“不崩”。actor 的公开开发条件仍需统一工作流实际核验。全部新实验未执行，原题/spec/gold/expected/规则未修改。

