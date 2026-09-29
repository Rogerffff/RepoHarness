# MONAI 首包：静态复核完成，待根任务抽验

三题已完成公开阅读、私有主审、独立reviewer和协调收口，共21份逐题文件；9份初判封存未改。结构、实际署名、角色阶段、请求配置及SHA检查通过，见[校验记录](pack01_output_verification.json)。校验不证明语义穷尽、后端模型身份或实际actor可开发。用途仍为development_diagnostic，三题均needs_review/static_review，非ready_for_probe或训练/正式评测批准。

| 题目 | 关键结论与证据 | 唯一优先下一步 |
| --- | --- | --- |
| [2446](results/Project-MONAI__MONAI-2446/card.md) | 浅复制外层列表保留原输入与内部shuffle；历史compat-v1已覆盖nibabel问题。F2P用数组列表，shuffle P2P用字典列表，缺少同类型的联合约束；这是静态覆盖缺口，未运行错修，未证gold新增回归。 | 取得正式actor交付初态与开发条件。后续actor资格还须公开功能执行，metadata/import不能单独证明。 |
| [3715](results/Project-MONAI__MONAI-3715/card.md) | 新验收仅eval字符串，P2P是默认空流程；题面核心train模式及forward时训练/梯度行为未覆盖。gold单行规范化静态合理，eval有公开依据，不是隐藏规格冲突。 | [提出公开API的train行为验收](pack01_followups.md)，不用函数对象身份限制合法实现；不为选择器静态缺失另跑CPU。 |
| [5686](results/Project-MONAI__MONAI-5686/card.md) | 2F2P仅requires_grad标志，8P2P仅常量前向数值；公开C5例经过多通道递归再次detach，gold留下原缺陷，归27参考不完整而非26新增回归。 | [选择性私有CPU提案](pack01_followups.md)：固定无梯度data_range，比较B1C1/B1C5的flag、backward/y.grad及前向值。只确认参考范围，不证明actor资格。 |

所有F2P及相关P2P、新增断言/helper、公开—验收双向映射、gold/替代与回归、开发需求、提交/恢复和暴露用途在各题analysis_before_history.md中。实际执行证据仅来自本题被精确绑定的历史RH2账本和日志：2446 compat-v1为7pass+1目标fail→8pass；3715 w05-1 ledger15/16为1fail1pass→2pass；5686 w06-1 ledger3/4为2fail8pass→10pass。没有新增项目执行、安装、网络、容器、SSH、GPU或模型实验。

已纠正旧结论：2446旧环境失败及dataset[0]描述不适用于所引日志/源码；3715旧“直接删train分支满分”缺少先修eval前提；5686旧“调用私有helper本身错误”和“CUDA追加项改变既有ID语义”缺少依据。同族/划分旧线索未跨题认证。主审与reviewer对核心结论一致；协调者采纳reviewer对2446数组分支漏测的补充。reviewer也收窄了其5686初判中私有gold诊断可检验actor的表述，封存初判未回改，修正见review.md。

协调者补齐了117个checks署名及issues的scope/proposed_action；将三题check40从pass改unknown：阶段合规不能证明无漏检、误杀或样本偏差。主审原card/record六份均逐字节归档，前后hash与变更理由见[修订记录](coordinator_revisions/pack01_monai/revision_log.json)。初判、历史delta和review没有被协调者改写。check29保持actual actor暴露unknown；授权私有审查暴露单列usage。

角色均由实际成功工具调用登记：三名fresh公开读者、fresh三题主审及fresh三题reviewer，全部显式请求gpt-6-astra/high/fork_turns=none。主审三份初判全部封存后才release各自旧记录；reviewer三份初判全部封存后才release主审/公开稿/各自历史。时间及实际canonical agent ID见[assignments](assignments.json)。此处不声称OS隔离、无预训练暴露或后端独立验真。

准备阶段跨任务候选引用错误已在任何私有角色读取前修正，并获根任务逐原件复核，属于准备问题，不计为本包题目缺陷。当前材料hash入口见[引用修正](material_reference_correction.json)和[协调复核](coordinator_reference_correction_review.json)。公开包及冻结题单未变。实际actor消息、准备后工作树、镜像资产和权限仍未知；缺少导出/库存记录不等于镜像缺资产。

根任务优先抽验：5686公开C5→递归detach链；3715 train语义与两个参考项的差距；2446同类型联合shuffle约束与compat-v1原日志。任务二由Claude B负责，本包仅交提案，不派发运行。其余首12题继续静态复核；冻结储备20题尚未导出或派发，待首12题根验收。
