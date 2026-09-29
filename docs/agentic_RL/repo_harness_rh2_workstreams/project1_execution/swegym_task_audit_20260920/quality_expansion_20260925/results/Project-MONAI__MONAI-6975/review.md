# Project-MONAI__MONAI-6975 — cross_review

审查者：e25_review_pack09_monai；日期：2026-09-25。root明确cross_review release后读取获准后稿/旧记录。

ROOT=`/Users/roger/Desktop/claude-code-verl-stage0h`；PUBLIC=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975`；PRIVATE=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-6975`；本题主审稿位于`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-6975`。源码短路径相对PUBLIC/base。封存初判SHA256=`88254d9e12a77cbcbd1bb248c500a3a652885ab6700ab85d36cef65949ef1a41`，本轮复验不变。

## 复审结论

支持主审的 `needs_review/static_review`、`development_diagnostic` 结论。独立初稿已经发现并保留：四F2P仅比较日志、ds[0]返回值被丢弃、新空P2P没有Dataset调用/断言、旧flags部分assertTrue不做等值比较、公共helper默认值的影响超出普通Dataset。主审前稿独立定位相同限制，并给出具体“执行后错误返回原输入”的漏测路径；静态断言检查支持该推断，不能冒称已运行坏补丁。

原题限定的普通Dataset修复可在调用点传lazy=None，不能因它不等于gold的公共默认值修法就认定不合格。已核原日志证明核心参数传播和日志用例fail→pass，仍不能证明所有图像/其他调用者行为完整正确。没有已证gold新增回归，也没有当前actor开发可用证据。

## 独立发现、交叉新增与分歧

| 项目 | 封存独立初判 | 本轮复核结果 |
|---|---|---|
| 根因 | Dataset省略lazy；apply_transform默认False；显式覆盖实例True | 原链和gold两个hunk与主审一致；不是根据旧模型满分反推正确 |
| 日志oracle限制 | 四F2P只精确字符串，没有返回tensor/affine检查 | 主审坏修法条件限定lazy=True组合类时执行后返回data_i，其余路径保持；旧Dataset shape用默认False，direct测试不走错误分支，静态可漏测成立 |
| 无断言/弱P2P | 新数组赋值函数；flags assertTrue(expected,actual)；部分空循环 | 主审全部保留，63/59状态数量未冒充语义强度；空测试已执行，缺判别力属25，不属18未完成 |
| 其他调用者 | 初稿读多个wrapper调用点；未证明gold回归 | 主审指出直接apply_transform(Flip(lazy=True),tensor)可能返回pending；这是配置继承导致的真实静态变化，但Flip公开契约支持延迟，不能自动称错误 |
| 调用点类名 | 初稿把相关组简称“Zip/ArrayDataset” | 本轮AST与源码确认1279=ZipDataset，1432=NPZDictItemDataset；初稿对1432的简称不准确，此处纠正，封存初稿不改。主审delta纠正旧Cache/Persistent定位是准确的 |
| 题面图像资产 | actor原图像位置/权限unknown，不从静态包猜缺失 | 旧record断言离线必FileNotFoundError缺依据，主审已撤回；不据此擅改题面或下载 |
| 合理非gold | Dataset调用适配层保留默认也合理 | 旧record的DeepSeek满分仅旧自述；原candidate/轨迹未授权未读，不将其登记为本轮实际模型证据 |
| 下一步选择 | 我的初稿偏原题固定seed RandAffined，资产不明时用合成dict | 主审优先内存确定性Flipd的True/False/None矩阵，更小且有明确像素oracle；采纳它为唯一优先。原题资产检查保留为后续范围，不要求现在多条并列实验 |
| check27口径 | 我用unknown同时列核心正证据 | 主审用pass且note只限核心、完整性unknown；事实无分歧。若汇总丢note，建议单状态unknown；不得把pass解作全面正确 |

我没有发现需要撤回当前静态候选结论的技术矛盾。保留的分歧是状态汇总和下一步范围，而非借一致人数提升证据。图像shape或最后像素相等本身不能证明lazy生效；对应模式日志/执行证据与返回数据需要联合检查。`applied_operations`数是变换记录长度，不等于resample调用次数，不能据日志计数声称性能或实际重采样次数已经验证。

## 对主审历史差异稿的原件复核

唯一获准旧件：`ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_monai_1/records/Project-MONAI__MONAI-6975.json`；SHA256=`d6d1b51eaa8aeb8374dec26cb387d0ab5ced14da8ece5e02e2207fff899dd473`，本轮hash与history refs相符。没有追随任何旧链接。

- 旧3：题面确实重复两次，但内容一致；实际actor输入仍未知。Git不跟踪原nii.gz不能证明镜像/忽略资产不存在，旧“离线跑不起来”推断不能成立。当前hints字段和旧raw hints不能混同。
- 旧23：原题明确log_stats=True，base有公开日志测试，不能说日志毫无公开依据；完整精确文字仍有潜在过约束。旧引用False日志属于新增反向P2P，四目标F2P都是True累计；主审已准确区分。
- 旧25：为了强迫公共helper或所有Dataset入口同时修复而扩测试，会把gold范围当规格；普通Dataset局部方案不能仅据不同位置判partial_fix。当前更扎实的漏测是返回值完全未观察及None组合未覆盖。
- 旧26：缺别类测试是覆盖缺口，不是gold已回归；59 P2P并非全都具有强断言。默认传播影响其他wrapper可以列风险，但未取得消费契约反例。
- 旧proposed_regression_tests错把1279/1432当Cache/Persistent；本轮stdlib AST显示类跨度分别为ZipDataset 1237–1281、NPZDictItemDataset 1383–1436。主审定位纠正准确，也促成我对初稿简称的纠正。
- 旧10：F2P内存案例无worker要求，不代表所选整套无多进程。已读test_compose.py:201–244包含DataLoader num_workers=1/2；具体共享内存需求量仍未核。
- 旧24/35/ready_for_probe：DeepSeek候选/模型结果没有获准原件，不能认证本轮替代解或真实模型已解；路径索引唯一也不证明全池无语义重复/留出重叠。主审保留5/35 unknown正确。

## 技术、测试与运行核验范围

公开需求—断言双向表及所有4 F2P/59 P2P完整ID状态在封存初判中。本轮读主审表后再次核分类：_0 Compose Flip+Spacing，_1 SomeOf、_2 RandomOrder、_3 OneOf各单Flip；Dataset _4和direct-call _4是False反向P2P。新增空函数不验证数据；旧map/unpack flags弱断言不等于全部其它强断言无效。

Dataset→apply_transform→_apply_transform→Compose.__call__→execute_compose的None传递与末尾flush机制都已有独立源码证据。lazy/functional.py决定性helper在初稿已读到结尾；本轮补读公开lazy_resampling.rst:144–193，三态和log_stats支持该解释。主审提到的返回pending风险并不把“pending非空”当正确目标。主审只rg定位而我已读的engine/grid/WSI/Zip/NPZ调用区段，也仍不是这些类全部路径或底层resampling kernel审计。

历史原运行限定ledger5/6；命令 `pytest -rA tests/test_compose.py tests/test_dataset.py`，63 collected；noop4个目标日志AssertionError/59 pass/RC1，gold63 pass/RC0，无expected skip/xfail/缺项。安装最后RC0，真实工作树diff有MetricsReloaded依赖删除，gold另含默认值/文档改动；git show的SwinUNETR提交内容不是未提交diff。原件candidate/projection绑定、workspace导入和脚本摘要已在初判核；actual image ID=null。当前actor身份、消息、工作树、依赖和图像资产未知。

八方面均已交叉核范围：公开目标与随机性；版本/初态；完整新增断言/helper/P2P；非gold与漏测/误拒；公共helper回归；开发资产/资源/网络；候选投影/恢复及评分状态；私有可见性/用途/偏差。没有把历史grader当actor，也没有把旧模型标签当本轮运行。

## 结构字段与编号审查

stdlib JSON全量解析确认13个必需顶层字段齐全；每个check有status/evidence_refs/by，保留原1–40稀疏编号；每个issue有category/scope/evidence_refs/proposed_action/status。additional_exclusions=[]、revision_refs=[]、disposition=needs_review/static_review、usage.intended_use=development_diagnostic，未观测本轮costs均null。事实引用保留ledger行号及运行条件，镜像tag/expected digest/actual ID分开。

3=unknown而23=pass；25=issue而26=unknown；29=unknown而审查暴露放usage；40=unknown。18的历史完成不被空断言混淆，19/20等历史局部pass都有scope说明。check27的核心pass与完整性unknown已在note分开，仍建议只消费单状态的汇总采用unknown。主审出稿时reviewer_read=false不是此次review未发生。未见结构缺字段或未经证据支持的训练/评测准入。

## 保留问题与行动口径

| category | scope | evidence_refs | proposed_action | status |
|---|---|---|---|---|
| returned_value_coverage_gap | check25，Dataset lazy路径 | PRIVATE/test.patch；base/tests/test_dataset.py；主审前稿坏实现分析 | 下一步联合检查真实返回数据和lazy模式，不能只看日志 | open_static |
| weak_assertions | check25，已选P2P | base/tests/test_compose.py:684–705；PRIVATE/test.patch | 限定59pass证据强度，本轮不改测试 | documented |
| potential_log_overconstraint | check24 | 精确StringIO日志assert | 尚无已证合法解误拒；后续若出现文本差异应回到公开语义判断 | pending_verification |
| broader_helper_behavior | check26 | base/transform.py:46–141；Flip:693–703及wrapper调用 | 记录调用者消费契约风险，不把变化自动当错误 | unknown |
| actor_asset_unknown | checks3/7/10/33 | environment_record、environment_brief | 实际入口与资产取证，不由Git缺文件判失败 | unknown |
| locator_correction | 本文与初稿调用点简称 | dataset.py:1279/1432，stdlib AST类跨度 | 后续统一称ZipDataset/NPZDictItemDataset；不改封存初稿 | corrected_here |

## 唯一优先下一步

采纳主审更小的公开内存字典Flipd direct/Dataset对照：实际actor记录消息、初态HEAD/status/diff及RC/阶段、身份/PATH/解释器/monai.__file__；对True、False、None+Flipd(lazy=True)观察累计/即时/完成边界，并将返回image与独立torch.flip期望比较。它针对当前日志oracle遗漏和actor可开发性未知，既不依赖私有测试，也不因原题NIfTI资产未核而阻塞最小路径。原题RandAffined若后续验证，需固定同一随机状态，不能拿连续调用像素差异当bug。此处不派发/执行任务二，不强制全Dataset、全仓、GPU或模型实验。

## 本轮真实阅读/暴露范围

完整读取本题public_read、analysis_before_history、old_findings_delta、card、screening_record JSON；首次大输出截断的主审P2P/替代/运行段已以53–111行补读，JSON则逐check/note、issue、引用集合补核。完整读取history refs及唯一旧record并核hash。本轮新增本题dataset.py:1250–1285、1405–1445和AST类边界；公开lazy_resampling.rst:144–193。其余原件阅读范围沿封存独立初判，不借主审阅读清单冒认已读。

未读旧DeepSeek轨迹/candidate、stage1/dupidx/其他题链接、全仓helper、其他角色包或聚合；没有新运行。审查私有暴露含本包gold/test/expected、历史原运行、各题获准公开读者/主审及旧record，不能进入solver。只写review.md，初稿不改。全程静态，无项目导入/测试、网络、容器或子agent；独立封存与交叉流程不是check40无偏差证明。
