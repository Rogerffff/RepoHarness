# Pydantic 包：三题静态复核完成

三题均完成公开读者、主审、独立reviewer和协调收口，21份逐题文件、9份封存初判齐全。[结构、阶段、请求配置与hash校验](pack04_output_verification.json)通过。6283保留为有条件开发候选；5386先处理公开接口与验收，8567先做私有参考诊断。三题均needs_review/static_review，仅供development_diagnostic，未获actor、探针、训练或正式评测资格。

| 题目 | 决定性结论 | 唯一优先下一步（未执行或派发） |
| --- | --- | --- |
| [5386](results/pydantic__pydantic-5386/card.md) | 公开需要定义时读字段；新F2P强制题面未命名的hook，测试类却无字段，只验calls。存在静态误拒机制与核心漏测，不能用环境跑通解决接口争议。 | 维护方先确定公开字段就绪接口及接受范围，再让验收实际读取继承/新增字段和examples。 |
| [6283](results/pydantic__pydantic-6283/card.md) | 新equality断言直接对应目标；gold避免RootModel内部字典污染，保留post-init。private×construct和共享BaseModel构造覆盖缺口仍在，不能概括为“仅actor未验”。 | 实际actor运行题面显式RootModel子类与BaseModel对照；候选触及共享构造时再核相关公开回归。 |
| [8567](results/pydantic__pydantic-8567/card.md) | 两新增assert仅验Python dump为str，未验JSON和值。gold无条件handler(source_type)可能使旧PlainValidator可接管的未知类型在构建时失败；不是已证动态回归。 | 一项私有CPU base/gold对照：默认配置、无schema的普通Custom类型加PlainValidator，观察类构建及精确异常。 |

原09-19 pydantic-install-v1运行均安装RC0：5386 noop120 passed/1 failed/29 skipped/9 xfailed→gold121 passed/29 skipped/9 xfailed，expected106 P2P逐身份通过，parser116不等于159 collected；6283为40 passed/1 failed/3 xfailed→41 passed/3 xfailed，expected38 P2P；8567为164 passed/1 failed→165 passed，expected158 P2P。主审与reviewer核选中原ledger、逐项状态、命令、投影和单文件恢复。语义阅读的P2P范围各自明确，没有把日志状态核对写成全部断言已读，也没有本轮新增项目运行。

5386的字段metadata就绪与前向引用全部解析不同，complete_model_class可能返回False；不能由gold文案推出所有模型此时可实例化。6283的construct跳过验证，不能强制非幂等validator的同一输入两路相等，也不归一化显式_fields_set。8567的validation仍走plain，新增内层schema用于serialization；不得把“生成schema”误述为“运行内层validator”。旧记录中按漏测判已证回归、按同文件自动同簇、无泄漏或补一条就准入等过强推论均未继承；具体跨题原件未追读。

协调者把5386/6283的check27从仅限目标路径的pass，收口为整体正确且完整问题的unknown，保留原局部正证据；26仍unknown。6283主审初判§6的“仅因actor”措辞由最终record明确限定。三份review称“15个必需顶层字段”是计数笔误：模板要求13个，原主审record实际也是13个，均齐全；review原文保持不变，纠正在最终record中记录。check33采用后稿unknown，check29与40均保持unknown。

五名审查角色显式请求gpt-6-astra/high/fork_turns=none；封存与release可追溯，不证明后端型号或OS隔离。六份主审card/record先逐一核完成hash后归档，见[协调修订链](coordinator_revisions/pack04_pydantic/revision_log.json)。初判、delta、review和历史原件未回改。主审usage仍描述其落稿时暴露；协调者阅读另行登记。

actual actor消息、真实初态、来源改动、权限/依赖资产和导入位置仍未知。历史pyproject/pdm.lock变更与gold分开，lock未全文语义核；source版本、base依赖、运行包版本和实际image ID不混填。历史grader成功与私有base/gold诊断都不能替代实际actor开发资格。

详细需求见[定向提案](pack04_followups.md)。任务二由Claude B执行和调度，本任务未执行或派发。首12静态交付已完成，合计七项有条件开发候选、五项优先质量处理；储备20题等待根任务对首12的验收与继续指令。
