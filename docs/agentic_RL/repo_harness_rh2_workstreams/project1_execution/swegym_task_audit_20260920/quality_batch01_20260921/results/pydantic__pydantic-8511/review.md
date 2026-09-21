# pydantic__pydantic-8511 — 第二阶段独立复核

2026-09-21。仅静态读取及元数据核验；所有新实验均未执行。本包两份 reviewer_initial.md 先封存，收到协调者统一开放通知后才读其他角色结论。本题初判 SHA256 保持 `0b9f131a37616082b6b6ce332d0cdaa315751e235bfae5e76291772986ba5069`，未回写。

**复核结论：同意主审 needs_review/static_review 和先做定点继承对照的优先级。** 核心公开要求与 F2P 对齐，受限的静态开发诊断候选资格可以保留；没有证据要求废弃原题。主审的 G1 是比普通漏测更具体的 gold 回归嫌疑，足以优先安排小型 CPU 确认，但目前没有运行反例，不能写为已确认 gold 错误。默认 repr=True 的漏测、Python 3.10+ 跳过及 Annotated 等扩展组合不应各自被当作阻断门。正式模型探针仍需实际 actor 条件验证；历史 grader reward1 不能替代它。

路径沿初判：`R=.`，`P=R/runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-8511`，`D` 为同材料根 private 本题目录，`L=R/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8511`，`O` 为本 review.md 所在输出目录。下列源码引用相对 `P/base/`。

## 初判独立发现与第二阶段新获内容

| 内容 | 何时形成 | 本次处置 |
| --- | --- | --- |
| 核心 repr 需求明确；F2P/stdlib与工厂P2P有公开依据；gold/noop原日志和身份边界 | 本 reviewer 第一阶段独立核实 | 保留；公开读者与主审结论相符。 |
| 没有 Field()/Field(repr=True) 的实例repr断言；隐藏所有FieldInfo是可区分错误候选 | 第一阶段独立提出 | 保留为T1，未执行，不声称假阳性已证实。 |
| Python3.8中kw_only/slots跳过，且这些ID不在冻结参考；Annotated repr仅是范围问题 | 第一阶段独立核实 | 保留普通覆盖限度，不扩大为题目必修全部组合。 |
| 旧Python、父类required/default_factory FieldInfo、无本地注解子类导致gold潜在失败 | **第二阶段从主审G1获知**，随后回查原源码 | 接受为具体新风险；这是我的初判遗漏，不能列成 reviewer 独立检出。它改变优先CPU次序。 |
| 09-16关于compare/hash/metadata扩题、scope creep、旧ready/安装表述及09-20纠正 | 第二阶段才读获准H16/H20记录 | 同意主审大部分纠正，详见下表；没有把旧报告标签作为原件事实。 |

新增读取范围为 O/public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json；本题 history/refs.json 指定的 H16（env_overnight_20260916/L1_pydantic/records/本题.json）与 H20（swegym_task_audit_20260920/pydantic_pilot/records/本题.json）。未读别题调查、主计划或汇总。另回查 `_decorators.py:414–500`、`_dataclasses.py:264–268`、`_fields.py:261–298`、`fields.py:609–644/736–744` 和继承P2P。H16中的其它题名/旧runner标签属于历史记录暴露，未沿其展开。H20没有本题新反例原件链接，本轮未据其泛化“新增纯Python探针”描述给本题补运行结论。

## 决定性主张逐项复核

| 主审/历史主张 | reviewer 判断与决定性证据 |
| --- | --- |
| 题面赋值式Field(repr=False)与F2P一致 | 同意。原题同列stdlib/pydantic对照；fields.py:201/670给repr默认/用途。test.patch真实构造对象，以正负子串检查两字段；初判已核全部新增修改断言和真实noop失败，不是只从gold猜根因。 |
| 所有新增helper/fixture及相关P2P已查 | 主审记录范围恰当。两个新增/修改测试无专用fixture，conftest autouse仅关URL；dataclass_decorators影响旧组合P2P。168参考ID状态核对不等于168测试体全文检查，主审明确未穷举，未发现以测试数替代覆盖论证。 |
| G1：gold的getattr注解枚举可能使空子类重新写入无本地注解字段 | **同意静态风险及优先级。** gold.patch先`getattr(cls,'__annotations__',[])`再setattr当前类；_fields.py:290–292只有default非PydanticUndefined时才把类属性换成普通默认值。因此Field()/Field(repr=False)/Field(default_factory=...)和Field(default=1)不同；现有继承P2P:1948–1969只覆盖后者。_decorators.build:414–500没有补本地annotations；_dataclasses.is_builtin_dataclass:264–268因继承validator不会把这种子类当纯stdlib重新包装。这些原件支持具体触发路径。尚未读取评分容器Python3.8 stdlib实现或执行矩阵，异常及版本边界仍待验证。 |
| G1应修改我第一阶段的优先实验 | 同意。我原先优先隐藏所有Field的负对照；现在先查gold在评分Python版本的合法继承是否失败，再做普通覆盖负对照。初判中的“未发现已证实gold错误”仍成立；应补的是已出现更具体的未证实风险。 |
| T1：默认Field显示漏测 | 同意。fields.py默认True；新增visible字段无Field；现有defaults/schema/signature不直接检查实例repr。错候选可设计，但当前未计分。它支持补小对照，不足以单独废弃任务。 |
| V1：全模块通过不证明>=3.10分支 | 同意。原日志的6个kw_only及4个slots节点SKIPPED且reference不含它们；test_dataclasses_with_slots_and_default在3.8的通过也不说明真实slots生效。单个actor无需预装所有支持版本；实际候选改到相应分支时再定点验证即可。 |
| gold/ref原运行可靠、安装旧阻塞过时 | 同意其限定范围。L/gold和noop/ledger.jsonl:1、散列已核日志记录rh2grader/54322、deny_all、派生镜像、editable安装rc0及包来源/testbed。gold169 passed/11 skipped、noop168 passed/1 failed/11 skipped；参考分别1+168全部出现。历史事实只适用于pydantic-install-v1，不是本轮执行，也不是正式actor验收。 |
| H16的Python<3.10修复属于scope creep | 同意主审/H20推翻。项目公开支持>=3.8，Field.repr是已有接口；解决该支持分支的同一功能不能仅因改了版本分支就算题外需求。范围合理与G1实现是否正确应分开。 |
| H16要求新增compare/hash/metadata透传 | 同意主审/H20推翻。Field显式参数609–641不含这些stdlib功能，extra在736–744转弃用警告/json_schema_extra；repr问题未承诺扩展到这三项。不能为了“更多回归”扩大公开需求。 |
| H16的169+7 skip足以描述本次执行/证明ready | 需要精确措辞：它是旧status_map计数，不据此断言旧原运行当时统计错误；本轮引用的09-19原日志实际是169+11。主审已采用后者，正确。旧ready_for_probe标签和H20对它的confirmed不能移植到当前正式actor；也不能用该确认覆盖G1。 |
| 无泄漏/与6126不同修复 | 主审留未核实正确。未审真实镜像资产/未来对象，也未读6126；静态包没有.git不是完整防泄漏证据。 |
| projection与测试恢复无任务特有交付阻塞 | 同意。test.patch只改tests/test_dataclasses.py；gold业务路径被projection包含；恢复官方文件不妨碍普通源码修复。无需新增exclusion，也不需要取消公开禁改测试指令。 |

未发现主审把真实actor、候选补丁应用身份、grader或旧局部实验混用。`screening_record.json` 的26标issue须随其明确的static_hypothesis一起解释，不能脱离scope读为已运行回归；27保持unknown及G1 status=needs_review与现有证据相称。card的“没有独立reviewer结论”是写作时状态，收口时应换成对此文件的引用；由协调者修改，我没有改动他人文件。

## 处置和最小下一步

**受限静态开发诊断候选：可以保留。** 核心要求、代码入口、参考测试和历史评分条件可解释。用途限观察solver能否修正赋值式repr，并单独检查其源补丁；不把reward等价为整个dataclass公共API正确。G1宜在模型探针前用短CPU实验收敛，理由是具体gold风险，非要求先填完所有覆盖空白。formal actor、真实输入消息、派生配方消费仍是运行侧条件，不冒用ready_for_probe。

**唯一优先CPU：** 在评分同配方Python3.8中跑主审定义的base/gold/只枚举`cls.__dict__.get('__annotations__',{})`的窄修正版。父类字段用Field()、Field(repr=False)、Field(default_factory=lambda:3)、Field(default=3)；子类无本地注解；分别记录类装饰是否成功、Child的校验后值、repr和与原例一致的隐藏行为。使用显式默认值作为现有P2P形状的控制。局部复现出现差异后，再为gold/修正版并列相同RH2参考得分；无需为首次分辨就重跑全部环境。

若G1不成立，撤销该嫌疑而保留记录；若成立且gold仍reward1，则记录gold回归和评分漏项，补有公开旧行为依据的窄断言。T1的Field默认True显示、隐藏属性仍可访问/验证/序列化可在同一短复现中顺手检查，不强制另造大量错误候选。Python3.9/3.11对照按观察到的版本依赖再扩展，未执行前不宣传跨版本结论。

本次第二阶段没有运行项目、容器、模型或反例；只新建本review.md，两份初判及主审文件保持不变。
