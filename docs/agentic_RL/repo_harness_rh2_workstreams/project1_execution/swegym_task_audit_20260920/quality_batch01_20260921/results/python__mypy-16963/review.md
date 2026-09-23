# python__mypy-16963 — 独立复核

**复核建议：保持 needs_review / static_review，用途限 development_diagnostic。** 同意主审没有因零 P2P 否定本题，也没有把 gold 的一项评分通过扩展为完整题面已修复。首要未决点仍是同一 base/配方下完整公开原例的 base/gold 对照，尤其 Boat 的返回推断。现有证据足以保留返回精度漏测与 gold 支持边界疑点；不足以登记已执行的错误解获分、合理解误拒或 gold 回归。本轮未执行任何新测试。

## 封存、暴露与证据层次

日期：2026-09-21；reviewer：review_mypy_tail，未参与本题主审。[独立初判](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/reviewer_initial.md) 已先于本题及 12417 的其他角色结论完成；封存 SHA-256 为 `c0067e6bbeca4d7fe47c26647e416b9447e13c993b516544440b22b638ad0617`，本复核不修改其字节。协调者确认两份初判均已登记后，才统一开放第二阶段。

第一阶段原件阅读与摘要核对以初判逐项记录为准。本阶段另完整读取本题 [public_read](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/public_read.md)、[analysis_before_history](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/analysis_before_history.md)、[old_findings_delta](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/old_findings_delta.md)、[card](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/card.md)、[screening_record](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-16963/screening_record.json)，及 [history/refs](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/history/python__mypy-16963/refs.json) 唯一指向的 [历史原件](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-16963.json)。没有沿 environment_record 的旧汇总链接扩展，也未读 10424、acceptance 或其他题历史原件。本上下文另见 12417 的公开/私有材料与获准第二阶段结论，不是盲 solver。

以下缩写均限定本题：`S=${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base`；`D=${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-16963`；`E=${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963`。源码行号均属于 base `f19b5d3a026319687dd81a5c7c976698bbe948a8`，不是 issue 自报 0.910 的源码。

“历史执行”仅指初判已直接核读的 E/gold、E/noop 原始 ledger/log；不是本 reviewer 重跑。“冻结参考”仅指 grading 列明并在该运行选中的项。所有候选实现、完整原例及边界预测均为静态推断。主审另报告的三条 ingest 第 210 行逐对象核对，本 reviewer 没有重新读这三条 ingest；我独立核过本地 bundle/patch/validation/账本与日志摘要，不把主审附加核对冒充自己的读取。

## 决定性主张复核

| 主审主张 | 复核结论与原件依据 |
| --- | --- |
| base 含 Type[TypedDict] 调用缺口，noop 失败确属本题 | 同意。S/mypy/checkexpr.py:1593–1595、1818–1860 将 TypeType 送入 constructor 分析，base 无 TypedDictType 分支。noop 原始日志 500–543 是同一 case 中合法调用和三项非法调用均出现 Cannot instantiate；不是安装、收集或资产失败。 |
| F2P 有正负判别力，P2P=[] 不能独立决定质量 | 同意。D/test.patch 全部新增内容是一项 testInitTypedDictFromType：输入 cls reveal、一个合法 keyword 调用、位置参数/缺 y/多 key 三个负例。完整输出数组比较会拒绝额外或缺失诊断；把整个 callee 直接变 Any 会丢掉三项负例。没有把一个 case 当一个无信息断言。 |
| 参数 reveal 不等于结果精度，完整题面覆盖缺失 | 同意，且在初判中独立得出。case 没有 func(Point)、结果 reveal、返回 D 的函数或 --warn-return-any，也没有空 D、Union、Car/Boat/Truck。noop 原本已满足 cls 的 reveal。只把新 callable 的 ret_type 置 Any、保留参数签名，是更具体的潜在错误解；它尚未执行。 |
| gold 修核心分支，但完整原例/可选 key 未验 | 同意。gold 仅在 TypeType callee 中调用既有 typeddict_callable_from_context；不能由两行 diff 推出当前 base 重现 issue 的全部五条历史错误，也不能由唯一 F2P 通过推出 Boat 已修。可选 key 的担忧是新增支持范围不完整，不是已证明 base-to-gold 回归。 |
| 另一条 direct TypedDict 检查路线可能因诊断形式被拒 | 保留待核。S/mypy/checkexpr.py:736–776、958 起和旧 check-typeddict.test 说明 Missing key/Extra key 等也是既有 API 诊断；而 F2P 指定普通 callable 的 Missing named argument/Unexpected keyword argument。尚未构造覆盖公开正负要求的可交付替代实现，因此不能只凭字符串不同登记误拒。 |
| 历史 grader 成功不是 actor 已验或可正式探针 | 同意。image/build/ledger/log 对应本题派生镜像和 rh2grader/54322；真实 agent/54321 的环境、消息、权限与源码导入尚无执行记录。主审 card 和结构化 disposition 均明确此边界。 |

独立阅读全部新增断言后的需求映射如下，供协调者保持结论范围：

| 要求 / 合理行为 | 公开依据 | 冻结测试及关键断言 | 保护范围 / 待验 |
| --- | --- | --- | --- |
| 接受合法的 Type[TD] keyword 构造 | 题面 f、Car/Truck；TD 文档构造器 | 唯一 F2P 的 cls(x=1,y=2) 无错误 | 历史 noop 失败、gold 通过；只覆盖 total=True、两 int 字段。 |
| 拒绝两个位置实参、漏必填 key、多 key | 旧 check-typeddict.test:47–69 与 required/extra key 规则 | 同一 F2P 的三条精确错误 | 实质负行为保护；没有错字段值的负例。 |
| cls 参数类型保留字段定义 | type[D] 注解与 Type 展示 | reveal_type(cls) | 只观察输入；不能代替构造结果。 |
| 返回仍为 D / Union，不能靠 Any 消错 | 题面 f/g 与 --warn-return-any | 无结果断言、无相应 flag | 静态漏测；需要原例与受控 ret_type=Any 对照才可证明获分漏洞。 |
| 传 D、Union、三类完整复现无错 | 题面全部代码与 Expected Behavior | 没有直接输入 | base/gold 原例优先；当前不把旧报告五错误当成当前 base 实测。 |
| 非必填字段及相关旧 Type/TD 行为 | 文档 totality、已读旧测试 | 无 P2P；已读旧 case 没被该 selector 执行 | 选择与可疑路径直接相关的回归；不要求凭测试数量全文件升级。 |

## Boat 与返回精度：静态证据可推进到哪里

原题 [完整复现与 flags](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/user_prompt.txt:38) 包含 Car、Boat、Truck，并要求无错。其 NamedTuple 替换后另一个问题的说明不构成明确删除原 TypedDict Boat 目标。主审与我独立保留这一题意边界，未替题面缩窄需求。

本阶段再次检查源码，并补读 TypeType 规范化与 union call：S/mypy/types.py:2984–2999 将 Type[Union] 规范化为 Type 的 union；checkexpr.py:3210–3224 逐分支检查调用，再 union 返回值。因此“gold 只有两行，所以不可能处理任何 Union”不成立。Car/Truck 的显式注解路线有现有 Union/子类型代码支持，但仍需原例实测。

Boat 的具体推断链不同：

1. S/mypy/plugins/dataclasses.py:123–133、249–262 为 Point 两个无默认常规字段生成 ARG_POS 参数。
2. S/mypy/checkexpr.py:925–956 为 PointDict 构造 callable，字段参数均为 ARG_NAMED；S/mypy/types.py:1845 的 min_args 只数 ARG_POS，因此两 callable 的 min_args 不同。
3. S/mypy/checkexpr.py:5681–5688 在无 Union 上下文的条件表达式中选择 join；S/mypy/join.py:396–422、705–713 对不相似 callable 进入 fallback 合并。Boat 的未注解属性因而有推断为 builtins.type 的具体路径。
4. S/mypy/typeshed/stdlib/builtins.pyi:196 的 type.__call__ 返回 Any；S/mypy/checker.py:4455–4476 会在 --warn-return-any 且声明返回 PointLike 时报告 Any 返回。gold 修改的是 TypeType 分支，未修改这条条件表达式推断链。

这是可定位、较强的静态推断；仍未运行 base/gold 原例来排除上下文、插件生成或其他路径影响。因此本复核不将“Boat 仍报错”写成已观察事实，也不由它直接裁定 gold 漏修。先验证原例，再决定是否需要解释原需求边界。

另一独立边界是 helper 把所有字段都设 ARG_NAMED，没有查看 required_keys；旧直接 TD constructor 会检查 required_keys。对 Type[total=False TD] 的省略字段存在合理疑点，但 base 的这一间接调用原本也不支持。不得把新增功能不完整改写成破坏了原先通过的路径。

## 与历史及独立初判的差异

| 历史说法 / 主审纠正 | 复核处理 |
| --- | --- |
| “非法调用规则公开推不出来；实现近乎唯一” | 不采纳。旧 TD 测试/文档支持拒绝多 key、漏必填、非法位置参数；争议只在具体诊断路线与未规定的新支持边界。主审纠正有原件基础。 |
| 单独删除 unsupported_type_type 即满分 | 不采纳。这样只剩 Any，会缺少 F2P 三条负诊断。若同时实现 TD 分支再删除其他类型的 fallback，才是另一未执行候选；不能用旧泛称代替运行证据。 |
| P2P=0 因而应判坏或补整文件 | 不采纳自动结论。F2P 自身包含正负行为；真实缺口是已定位的返回、Union、可选 key 与旧 Type 边界。 |
| gold 两行无法覆盖报告的所有五错误 | 当前未知。报告与 base 版本不同，传参/Union 关系可能已先修；Boat 的新静态链比“行数少”更有证据，但仍须 base/gold 原例。 |
| 环境未实跑 / raw hints 已缩窄需求 | 前者被 09-19 本题原始 RH2 配对更新；后者原文未在当前 public_hints 中出现，旧历史的转述不能替换实际 actor 输入。 |
| 测试目录应全部排除、helper 改动可满分、同主题任务应同侧 | 本轮未验证，不采纳规则变更或分组。官方实际仅恢复指定 .test 文件；不因 gold 未改某目录推导禁止该目录全部合法改动。 |

与主审没有处置上的实质分歧。返回精度、Boat、非必填字段、诊断路线和 grader/actor 区分均在我读主审前已记录；因此这些是独立重合，不能称为本阶段新发现或新的 CPU 证据。主审原稿更完整展开 Type[Union] 的规范化，本阶段已直接补核。我的初判未读 typing-full 导入的 lib-stub/abc.pyi 与 _typeshed.pyi，本阶段补读两文件全文；未发现改变结论的内容。这是阅读范围补足，不能回写为初判已全读。

题目关系方面，我在初判另核过本题 base 的 checkpattern.py:520–522 已含 12417 gold 的同形 None guard。这是两份已授权源码中的具体修复内容继承线索；不证明 Git 祖先、不意味着两个问题重复，也不能验证历史关于另外题目的并簇建议。

## 八方面收口与有界下一步

| 方面 | 当前已核及证据层次 | 未决边界 |
| --- | --- | --- |
| 公开需求 | 全原例、flags、hints、文档/旧测试，静态 | Boat 范围需以当前原例行为澄清；真实消息渲染未验。 |
| 材料与初始问题 | 本地 patch/metadata/hash；历史 noop 的目标错误 | 未重建整个 tree；原例当前 base 未执行。 |
| 测试是否测到要求 | 全新增断言、runner/fixture；历史一项真实执行 | 返回/Union/完整原例缺覆盖；冻结 P2P 确实为空。 |
| 是否误拒合理解 | 直接 TD 诊断路线有旧行为来源 | 没有已执行合格替代解或误拒证明。 |
| 回归与 gold 完整性 | Type/TD/Union/条件推断调用链，旧测试静态 | Boat、可选 key、未选中旧行为均未当前执行。 |
| agent 开发条件 | 本题配方、构建、历史安装/导入/资源原件 | agent/54321 配方消费、权限、激活、当前稳定性未知。 |
| 交付与评分边界 | gold 仅 checkexpr.py 被投影；官方恢复 check-typeddict.test | helper 防篡改、真实可见答案与来源 runner 对照未验。 |
| 题目关系与用途 | 12417 guard 已存在本 base；完整暴露记录 | 不据静态阅读推模型成功率、训练价值或正式准入。 |

**唯一优先 CPU：固定原 base 与本题派生配方，分别运行 base/gold 的完整公开原例。** 独立保存题面完整 Car/Boat/Truck 代码，另保存题面空 D 的 f(D) 与 Union 的 g(int)/g(D) 小例（只补必要公开 imports），不要预加属性注解绕开 Boat。建议命令形状为：

```text
python -m mypy --config-file /dev/null --no-incremental --show-error-codes --warn-return-any /tmp/review16963/original.py
```

另外两份小例用相同 flags。记录逐行诊断、退出码、解释器/target version、mypy 导入路径与 base/gold 差分；保留本次运行目标版本，勿把隐藏 case 默认 target 3.8 当成 issue 或宿主版本。若需对比 issue 的 target 3.9，单列条件，不能与首轮输出混算。只有该对照才能将“Boat 残留”升为实测问题，或撤销静态预测。

本题配方是 [image.json](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/image.json)：派生镜像 `sha256:ab5d4a172a64f9969e2264af18f6389a7c688cad8e7cdfb417c96be961771add`；pins 为 setuptools68.2.2、wheel0.43.0、typing-extensions4.8.0、mypy-extensions1.0.0、tomli2.0.1、types-psutil5.9.5.17、types-setuptools68.2.0.0、packaging23.2。历史宿主 Python3.12.4，实际 -nauto 启动 11 workers 执行一项；没有 OOM 证据。不得套用 12417 的 Python3.10/packaging24.1 条件。

完成原例对照后，若需验证覆盖问题，才追加保持 constructor 参数签名、仅令新增 callable.ret_type=Any 的受控候选，同时跑原例与冻结 F2P：公开返回目标失败而 F2P 仍过，方可记具体错误解获分。可选 key 与旧 Type/TD 对照、等价诊断路线保留为条件性后续，不以未执行方案要求立即改题。原题、gold、expected、文件规则均未修改；actor 基本开发验证仍待统一工作流完成。

