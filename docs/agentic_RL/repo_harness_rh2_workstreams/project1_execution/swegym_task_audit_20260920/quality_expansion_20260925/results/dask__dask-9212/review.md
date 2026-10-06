# dask__dask-9212 独立交叉复核

审查者：e25_review_pack11_dask；2026-09-25。root明确cross_review release后形成。reviewer_initial封存SHA256 `5bbf5cc5420a764f8112a086b05b6f50d3c6071e0046da6c4ecdc4025bfbc064`，保持不变。

**维持 needs_review / static_review、development_diagnostic；采纳主审更具体的唯一优先下一步。** 核心Enum/Flag修复有真实历史正反对照；同名不同模块枚举的表示碰撞可由源码确定，完整用户计算结果回归尚未运行。公开题面自带修法、actor未知及历史parser范围均已正确分开。

## 获准阅读与证据层次

新增读本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，以及history/dask__dask-9212/refs.json授权的L1/Pilot两份原件。L1 SHA `7207b1eb9e4c59bb06006e067531ecda0b56e3a2fdea01e9eaf945fab8cf7df8`、Pilot SHA `ba6dd136a8cb37064545baa0a0e704e60182b82fdedc4a77902fcdde07046538` 均核对一致。没有追读旧记录引用的8792、raw hints、旧status_map或其他源文件；其中关系/旧parser细节只能作为历史报告。

第一阶段已读原件和区段见reviewer_initial。主审screening_record.facts_ref的两条历史运行，其candidate、projection、install、test、observations、report、parser_diagnostics、cleanup字段已与 `runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-9212/{noop,gold}/ledger.jsonl:1` 逐字段机械比对，全部一致。本轮无项目运行/导入/测试、网络、安装、容器或模型，也未修改已有初判/主审稿。

## 技术复核表

| 要求/主张 | 复核判断 | 决定性依据与限制 |
| --- | --- | --- |
| 普通Enum稳定 | 确认 | base.py:923–1021、Dispatch utils.py:578–607；普通Enum/Flag默认object→UUID，gold新增Enum注册；不是pickle路径 |
| 四参数与两关系断言 | 确认 | 新test_tokenize_enum[Enum]/[Flag]为2 F2P，[IntEnum]/[IntFlag]为2 P2P；都仅RED=1/BLUE=2，先同成员相等，再异成员不等；两F2P noop在第一assert失败 |
| int混合类型原行为 | 确认但不能过度解释 | MRO先命中int identity；两个P2P的通过不证明一定继续走同一路径，也不锁修前token字节；不能升为新Enum handler四类全覆盖 |
| 合法非gold与误拒 | 确认局部空间 | 新测试无helper名、三元组或固定摘要要求。未执行替代候选全P2P，不证明全称无误拒；交叉复核采用主审check24=unknown，保留我的初判pass所限定的“已读断言无实现锁定”正证据 |
| 同名不同模块表示碰撞 | 确认静态事实 | gold对A=Enum('Color',{'RED':1},module='audit_a')和B=Enum('Color',{'RED':1},module='audit_b')均返回('Color','RED',1)，base.tokenize对相同表示得到相同摘要；非随机MD5碰撞 |
| delayed用户结果回归 | 具体静态假说，未运行 | delayed.py:213–229、618–641以pure token生成任务键；同一函数可观察type(e).__module__。需要一次成对compute结果，不把表示相同直接写成已观测错误计算 |
| 任意value/严格模式/容器 | 覆盖有限 | 新测试只有简单int值。e.value直接进入str、未递归normalize的风险成立，但任意对象必可确定性hash不是已定契约；不机械新增全部为硬门 |
| 自定义Enum hook | 不能仅凭绕过认定gold违规 | object优先hook，但Enum注册改变MRO命中；custom-collections:498–503及test_tokenize_method有注册父类/dispatch优先先例。主审保留兼容性争点正确 |

主审新增“先记录token/同函数key，再一次compute用户结果”的I1设计，比我的初判只保留跨模块疑点更具体。它以公开token按参数值建图及可观察类型差异为依据，不要求某个固定类表示格式；不应因公开Possible Implementation用了短类名便排除该合理回归问题。

## 运行、版本、实际环境

原选择为 `pytest -n0 -rA --color=no dask/tests/test_base.py`。compat_v2b先离线安装pandas1.4.4/numpy1.24.4，再editable install；两次安装RC0。noop在两目标第一assert失败：2 failed/124 passed/3 skipped，RC1；gold126 passed/3 skipped，RC0；129 collected，2个F2P及103个P2P全部逐ID核对存在且没有expected skip/xfail。原日志没有被“总reward成功”代替解释。

三skip为matplotlib缺失1和未启用slow2，不能称全文件129全执行通过。parser num_parsed_tests=125与pytest129不是相同集合；本次只对105 expected证实状态映射。旧L1/Pilot称emscripten空白截断合并和skip伪键，主审delta没有把这个历史细节冒充本次独立审过parser源码。没有证据将这些未核非expected映射指控为本题F2P/P2P错分。

exact base aa801de0f42716d977051f9abb9da2c9399da05c，gold SHA/原candidate一致。expected manifest 1ebd1560…ed60、derived actual image ID 5b69493366c23ca4871f1011097747345c49cb6c4f8408cac7fc6a8125fff122、本地base ID 974b8bd9…d982、scripts_digest db692fb6…bb39已分开。历史grader UID54322、Python3.10.14、源码导入位置及pins不能证明当前actor的解释器/写权限/资产可读。git show的dataframe内容是HEAD基线提交；noop clean/gold base.py修改是grader staging状态，不是当前actor准备初态。

主审facts原账本字段比对成立，安装阶段完整路径/RC、skip、资源原字段与clean-up均保留。未以旧环境维修原因文本推导本次未读修前失败，也未因静态public包不含wheel就称actor缺wheel。

## 历史复述与独立判断变化

L1确实把UUID和pickle混写、把注册文本位置当优先依据、把回归建议当check26 pass、把关系测试保护说得过满；主审delta纠正与源码一致。Pilot已收窄运行/资格和训练表述，但其check3/29 confirmed也仍不能代替当前actor实际消息/可见性，主审再次收窄合理。

L1和Pilot都报告8792关联；本轮没读8792原件，主审将其登记为historical report/unverified且不决定同侧划分，边界正确。不能以同仓同文件推断重复修复，也不能把历史关联信息删除成“确定无关系”。旧10项恒失败在本次修订pair已无同样表现，但这不证明当年没发生或当前actor已经修好。

公开Possible Implementation正文与gold核心相同、import示意不完整是原公开材料事实；适合标statement_contains_fix以解释诊断能力维度，不等于私有审查泄露，也不是训练批准。actual actor是否收到它仍为unknown。

**对本人初判的修订仅在下一步优先级**：初判优先actor入口与MCVE泛核验，保留碰撞为后续。现在采纳主审的同函数pure delayed最小对照作为此题质量判断的唯一优先步骤，因为它能直接确认/撤回用户可见新增回归，而重复简单Color MCVE只会再确认已知核心缺陷。actor资格缺口仍保留，作为执行该对照时要明确记录的条件，而不拿它替代具体质量问题。

## 结构核验与收口意见

主审record含全部13规定顶层字段；所有所列checks均含status/evidence_refs/by，issues均含category/scope/evidence_refs/proposed_action/status。稀疏编号按原1–40索引，未混成八项门；3 unknown与23核心pass分开，25 issue不挪成26已证回归，27 unknown保留局部gold正证据，29与usage分开，40 unknown不能由封存升级。additional_exclusions=[]、revision_refs=[]、null当前成本、needs_review/static_review、development_diagnostic均正确。

9/16–21的pass注释清楚限制在两次历史普通候选/105 expected；没有越权证明任意候选不可伪造、全parser正确或当前actor可用。37 pass限制在读到的配方/wheel镜像层/测试选择未变，无全池修复承诺。没有需要以修改封存稿解决的事实错误。card/record中的reviewer未读是生成时状态，协调者最终引用本review时可明确其已复核；我不改主审文件。

## 唯一优先下一步

任务二在独立私有CPU base/gold副本执行一组同条件公开API对照：创建两个module不同、短类名Color和RED=1相同的Enum；使用**同一个** `delayed(pure=True)` 函数返回 `type(e).__module__`；记录A.RED/B.RED的token、任务key以及一次 `dask.compute(left,right,scheduler='synchronous')` 的结果。预期语义分别为audit_a/audit_b；同步本地执行避免引入虚构module导入或分布式序列化需求。

如base结果可区分、gold重复/错误，则形成check26的实际用户结果新增回归证据；如不成立，按实际key/图/计算链收窄I1。先打印源码来源、解释器和初态并记录各命令RC，不以对照成功替代actor完整资格。无需全仓、网络、GPU或模型；本review未执行或派发此步骤。全部审查稿含私有答案/旧结论，不进入独立solver输入。
