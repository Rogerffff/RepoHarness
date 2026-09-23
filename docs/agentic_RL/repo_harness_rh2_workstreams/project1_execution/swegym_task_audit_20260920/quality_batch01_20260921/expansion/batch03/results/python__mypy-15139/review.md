# python__mypy-15139：独立复核收口

维持 `needs_review / static_review`，用途 `development_diagnostic`。**同意主审的核心结论：历史reward1只证明普通赋值错误的小写分支，gold未修题面直接列出的reveal输出路径。** 应先做精确base/gold原例对照，不能由环境成功或唯一F2P通过推成完整修复。

## 封存与暴露

本包三份独立初判全部保存后，root核对SHA并于21:51:03.612934Z明确整包封存/放行。该题 `reviewer_initial.md` SHA256=`813fb27f19244baae23cf0c720fce1a9cc623a68a91029e0aa7128ed794fbd18`；本复核未回写它。

放行后新增阅读本题 `public_read.md`、主审 `analysis_before_history.md`、`old_findings_delta.md`、`card.md`，`screening_record.json` 的issues/disposition/usage/file_rules/revision_refs，并按I3/history/python__mypy-15139/refs.json读取唯一旧单题 `env_overnight_20260916/L1_mypy_2/records/python__mypy-15139.json`。只读该旧记录内部提及的其它ID/路径文字，没有沿它访问其它题或聚合。独立阶段已见环境原件自带gold/noop摘要，故不称无结果盲审。本轮仍完全静态。

下述源码均在权威ROOT `runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base`，运行路径与完整身份见封存初判。

## 对决定性主张的核对

| 主张 | 复核 | 决定性证据/限制 |
|---|---|---|
| gold没有覆盖reveal | 同意，独立阶段已得相同结论 | messages.py:1630–1632调用TypeStrVisitor，types.py:3188–3189仍固定Type；Instance:2992–2998用fullname；gold只改messages.py:2519–2520。静态预期仍`Type[builtins.type]`，不是旧记录写的`builtins.type[...]`。完整CLI尚未执行。 |
| 唯一F2P与原题部分对应，非空操作/纯解析假通过 | 同意 | 新例整个输出精确比较；noop原日志847–878的Type/type差异、gold866–884选中且通过1例。实际执行1、解析1、冻结F2P1/P2P0在本题恰好相等，仍分别记账。 |
| 缺公开开关名字足以判题意不可得 | 同意主审推翻此旧断言 | options.py:358–364、已有lowercase八例、runner的强制大写约定均是公开源码。要求开发者查代码合理；题面OR/全限定名的作用域疑义仍应保留。 |
| 可能误拒其它统一别名方案 | 保留为解释风险，不提升为已证误拒 | exact `type[type]`有现代版本/选项政策支持；测试不绑helper。尚无满足所有合理旧行为的替代补丁被实际拒绝。 |
| 无条件小写会漏过评分且可能破坏兼容 | 同意静态候选/范围，尚无新执行 | 冻结P2P为空；force-uppercase与Python<3.9要求不同。主审历史后补的直接旧例比“同文件8例”更合适，见下。 |
| 八条tuple/list/dict/set旧例就能挡住Type无条件小写 | 同意主审纠错 | 它们不进入TypeType分支。放行后已回原件读check-classes.test:3377–3385，`testTypeUsingTypeCTypeAnyMember`的`y:int=arg`明确要求`Type[Any]`，是直接错误formatter回归；其reveal(x)只验Any，不能混为同一断言。 |
| 旧TypeType.__str__替代路线肯定能过 | 不采纳该强断言 | format_type_inner直接递归typ.item，不经TypeType.__str__。共享命名规则/修改两个真实输出入口是合理路线，单改__str__未证明有效。 |
| 所有测试目录应追加排除 | 同意不采用 | baseline归档的test_globs=()与本题精确official恢复路径是一回事；旧gold从未改某目录不足以证明所有合法解都不需要它。无本轮绕过实验，additional_exclusions应继续[]。 |
| 旧“无运行证据”仍成立 | 同意主审标过时 | install_wave1原日志有两条实际pip命令、editable安装完成和测试摘要；派生COPY/ENV本身不能证明安装。历史grader仍不能证明正式actor。 |

## 需要保留的边界与补充

公开读者也从公开材料识别了错误formatter与reveal两个入口，不是私有答案暴露后才把reveal补成隐藏要求。其关于`builtins.`限定名和版本政策的谨慎是必要的：若未来修订，不能简单要求所有字符串完全一样而破坏同名消歧；先确定具体公开行为，再选有限断言。`unsupported_type_type`仍拼Type是额外静态范围线索，不等于已经跑出的另一个原例失败。

我在封存初判中已独立记下跨题代码包含关系：15184 base/messages.py:2519–2521含本题gold，而15139与15184的meet.py:300–312含10174的关键归一化后Any检查结构。这是同包原件事实，不是Git谱系或重复题证明；可用于后续数据划分，不能把三个目标并为一题。

保留原运行身份：baseline.tar.gz历史harness、原python/mypy1.4 spec、install_wave1本题derived image与九pins、candidate apply54321、grader54322/deny_all、qualification absent。prepared的原`/work`路径和本地缺失wheel payload意味着新run要另建重定位输入/确认镜像，不允许回写原账本；不应改用当前harness字节来解释旧日志。

**固定grader语义诊断与模型开发资格分开。** 在身份、代码、依赖和导入来源确认的固定grader/诊断入口即可核base/gold原例；正式actor的镜像消费、激活、工具及可写路径未验，并不自动阻止这个语义实验。进入真实模型开发才需要补正式actor验收。该题card的优先实验表述总体已经如此；共享的“probe前验actor”应明确是模型probe，避免扩大到每个CPU诊断。

## 唯一优先实验及未查范围

保留主审提出的原题三行CLI base/gold配对：目标Python3.10、受控配置/包发现，记录`x:type[type]; reveal_type(x); reveal_type(type[type])`完整输出/退出码，再关联同条件原官方单case结果。含预期类型错误的非零退出不能叫环境失败。若确认gold普通错误已小写但note仍Type，按公开需求讨论版本化的测试/参考解修订；不得为保住gold默默缩窄目标。

如后续检查兼容，选直接Type[Any]赋值错误、默认/force/旧目标版本对照；八个容器旧例可做周边烟测，不能充当Type分支负对照。当前无需强制两个新候选。

复核没有新增项目执行证据。未查全部类型/调用者回归、原例当前真实输出、所有合法替代、真实CC与资源/并发、镜像/历史答案泄漏和模型表现。保持未知，不改源码/tests/gold/reference/reward/expected，不批准ready_for_probe或训练/评测。
