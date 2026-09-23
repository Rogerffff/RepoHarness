# Batch02 静态审查交付

固定十二题的公开阅读、主审、独立初判和最终复核全部完成。交付84份逐题文件与5份协调汇总；36份封存稿未改。协调裁定为**10题受限静态候选、2题不优先**，用途均为 `development_diagnostic`，所有记录仍保持 `needs_review/static_review`。这不是正式训练、评测或actor启用批准，也不能据这12题推算全池质量比例。

本轮只做静态文件、源码和既有日志审查及元数据校验，**未执行新项目/CPU/容器/模型运行**。12条未来CPU方案均未执行；DVC3576为诊断备选，其余也不是一次性全部必跑的要求。固定grader语义诊断、解析器控制和正式actor开发验证分别记账。

## 十二题裁定与唯一优先方向

下表F2P/P2P是冻结评分参考数，不是完整执行数或审查者实际读过的测试体数。每题阅读边界、原件路径和分歧保留在七份逐题文件中。

| 题目 | F2P/P2P | 协调裁定及关键限制 | 唯一优先方向（未执行） |
| --- | --- | --- | --- |
| [DVC3576](results/iterative__dvc-3576/card.md) | 1/6 | 不优先，诊断备选；helper返回约束与CLI目标有差异。允许沉默是合理解释，不能单凭未发stderr判gold错误。 | base/gold/调用层替代路线的公开CLI对照。 |
| [DVC4166](results/iterative__dvc-4166/card.md) | 1/58 | 受限候选；目录模式处理明确，参数身份合并与自然部分实现待诊断。参数0仅证明可见，不证明重新包含。 | 目录/普通文件及否定模式的三路对照。 |
| [DVC1681](results/iterative__dvc-1681/card.md) | 1/12 | 受限候选；内部dumpd表示断言可能限制校验和局部修复，Mock不能替代真实非默认路径。 | 固定旧stage、gold和checksum局部替代的三路对照。 |
| [mypy10308](results/python__mypy-10308/card.md) | 1/0 | 受限候选，明确限既存materials-v2。原缺fixture材料不因修订成功自动通过；目标是无internal error，可有正常诊断。 | 公开原始Vector/Matrix例base/gold对照。 |
| [mypy17071](results/python__mypy-17071/card.md) | 2/2 | 受限候选；TypeIs有公开结构依据，issue没逐字提到它不证明误拒。 | TypeGuard公开正例及真正未绑定另一类型变量负例。 |
| [mypy11236](results/python__mypy-11236/card.md) | 1/0 | 受限候选；一个F2P含4个合法返回、1条note和6条负断言。另一修改旧case未被选中。 | 公开单元素Union与值/长度负例base/gold对照。 |
| [Moto7584](results/getmoto__moto-7584/card.md) | 1/19 | 不列能力评估候选；仅为已知规范冲突诊断。gold漏公开先订阅→删除→重订路径，私测错误文案多拼arn。 | base/gold/公开合规候选的操作顺序和消息对照。 |
| [Moto5752](results/getmoto__moto-5752/card.md) | 1/79 | 范围待定的受限候选；新增BeginsWith有公开依据，但与原顺序缺陷可分离。raw hints除拼写还缺continue。 | 独立“等值命中后continue”候选，定位w/world拒绝原因。 |
| [Moto5134](results/getmoto__moto-5134/card.md) | 2/12 | 受限候选；null存在性与Logs投递语义一致，未发现具体gold冲突，不强造反例。 | 正式public-image actor的窄开发路径核验。 |
| [pandas56849](results/pandas-dev__pandas-56849/card.md) | 1/419 | 受限候选；warning小写措辞有误拒疑点，DatetimeIndex.freq未被直接断言；10完整节点合为4键但本次全PASS。 | 保持月末语义、发规范名M警告的正常替代对照。 |
| [pandas48106](results/pandas-dev__pandas-48106/card.md) | 16/1020 | 受限候选，限明确pandas_meta_v3+reference-bindings-v1；剩余2组tz别名合并2+4节点，未证错分。 | 真实完整摘要次序下混合状态/缺席聚合诊断。 |
| [pandas53958](results/pandas-dev__pandas-53958/card.md) | 1/10 | 受限候选；公开命名空间选择与对象身份漏检分别保留。协调者采用reviewer的身份优先方案。 | gold与把单例误导出成类型的候选对照，直接核类型身份。 |

完整候选分区见[probe_candidates.json](probe_candidates.json)，入口、身份、具体候选构造及所需证据见[cpu_queue.json](cpu_queue.json)。新诊断候选补丁均未创建；53958的_libs真类方案和其它可选部分实现不叠加为第二个必测。规范分歧不能由一次得分或多名审查者同意决定。

## 原运行、修订和开发边界

- 10308的输入materials.json与逐运行同名审计输出已区分；原grading与既有修订grading身份均保留，正式prepared不自动重冻。原stage1安装失败和脚本末尾状态掩盖问题不混作修订运行成功。
- 48106现有3组Period绑定映射7个完整节点，两个原审计证实实际消费；剩余6个tz节点本次全PASS，既有0/1不被推翻。noop的FAILED摘要实际在PASSED后，不能用测试执行顺序推出失败被覆盖。合成输入控制须单独标记，不能冒作真实候选错分。旧resources_v1代码快照未在本地认证，当前ROOT/rh2不冒作历史同字节代码。
- Moto5134旧stage1的14个引用全过，同时3个非引用SQS失败；当前消费sqs_v1后17项全过。这两项事实并存，普通完整pytest rc1不自动令reward0，安装/收集/超时等全局失败另判。
- COPY wheels不等于完成安装。各配方消费链与原安装日志按题核到；wrapper的code-root应指向rh2目录。未来prepared-summary位置和实际镜像可用性仍需执行负责人落实，不编造可直接运行的路径。
- 实际历史grader为54322；candidate.apply_user=54321不代表正式actor开发会话。正式public-image actor的解释器、导入、写权限、源码修改/必要扩展重编和实际消息可见性尚未验证。固定grader诊断不须先证明actor合格，但不能据其成功启用模型。
- 官方只恢复test.patch精确路径，当前test_globs为空；12题附加排除均为空。无任务、源码、test、gold、expected、reward或冻结参考修改，无真实求解轨迹、模型成本或重复稳定性结论。

## 独立性、暴露与分歧

每题主审无历史稿先落盘封存，再开放本题历史；同仓reviewer三份独立初判全部封存后，才统一开放任何主审/历史结论。36份SHA与24条保存/开放时序登记可核；部分封存/开放共用一次登记时间，不虚构亚秒级顺序或系统强制访问隔离。

原pandas主审在56849初稿封存且本题历史开放后，误用head读取历史聚合前三行，看到48106题键及一个计数，随即报告并停止。56849后历史产物保留披露，封存稿不改；未开始的48106/53958改由fresh主审接手，不转交该事件或数字。此处理已获总协调接受。另一次pandas reviewer完整读取授权environment_record的环境摘要、原运行结果与history路径/roles索引，已如实披露；没有跟进质量历史正文。两次事件不同，均以代理报告和落盘材料为证，不声称OS级访问审计。

独立复核还确认若干后期公开base包含先前题修法：Moto5752/7584含5134存在性机制，7584含5752标签路线；pandas53958/56849含48106分类分支，56849含53958类型导出。mypy同包的版本包含关系亦按题保留。它们是具体跨版本暴露关系，不自动等同重复任务或已发生的solver泄漏；特权审查上下文不能作为盲解solver上下文。

53958保留主审“先查_libs方案误拒”与reviewer“先查singleton误收”的分歧。协调者采纳后者，因为它直接检验公开的类型目标；前者即使得0也不能裁决两公开位置哪一个应被接受。其余重要历史纠正和方法变更见[method_adjustments.md](method_adjustments.md)，封存初稿与历史差异稿均未回写。

## 交付核验与交接

最终输出核验记录在[assignments.json](assignments.json)：12题×7文件、13个必需JSON顶层字段、稀疏1–40检查编号、用途/成本/排除边界、36份封存SHA、12份最终review摘要、24条保存/开放记录、候选分区和12条未执行队列关联。稀疏checks允许未列项，不强填40项。登记最高并发含协调者为4。原材料完整性沿用已完成的36源行、19188 blob/mode、24日志/账本等检查，没有重跑全材料审计。

总协调此前已验收[DVC三题](../../acceptance/batch02_dvc_review.md)和[mypy三题](../../acceptance/batch02_mypy_review.md)。后续整包验收以本次最终文件为准；10308的revision reviewer旧pending字段与56849一处旧待核备注在收口时更正，未改变语义裁定或封存稿。本协调链只交付固定B2，未派发B3质量审查。
