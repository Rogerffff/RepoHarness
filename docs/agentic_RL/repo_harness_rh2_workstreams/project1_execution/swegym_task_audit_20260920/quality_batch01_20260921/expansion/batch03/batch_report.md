# Batch03 静态质量审查

固定11题已完成：11条完整角色链、77份逐题文件、33个不可变封存、11份最终review、22个先封存后放行记录。协调裁决为 **5个受限静态候选、6个暂不优先项、11个未执行CPU方案**。所有题仍为 `needs_review / static_review / development_diagnostic`；这不是正式模型探针、训练或评测准入。

## 逐题裁决与唯一优先后续

| 题目与短卡 | 静态建议 | 决定性依据及主CPU问题 |
| --- | --- | --- |
| [DVC6954](results/iterative__dvc-6954/card.md) | 受限候选 | 负数参数修复与历史分差成立；先核公开CLI→lock→跳过/再运行链及负float，保留安全表达式边界。 |
| [DVC3665](results/iterative__dvc-3665/card.md) | 暂不优先 | 4个F2P强制题面未要求的私有helper；先核合法内联路线。Windows目标行为与Linux原评分分别验证，不能仅改os.name代替Windows路径语义。 |
| [DVC4785](results/iterative__dvc-4785/card.md) | 暂不优先 | 401未测，异常类型契约有争议；优先base/gold HEAD405→GET404及成功控制，保留公开回退依据与规格不确定性。 |
| [Mypy15139](results/python__mypy-15139/card.md) | 暂不优先 | gold只修普通错误formatter，公开reveal路径仍固定Type/builtins.type；先核原三行CLI的完整note/error。 |
| [Mypy15184](results/python__mypy-15184/card.md) | 受限候选 | 同名类型消歧有依据；撤回“fullname不同必报错”，公开SupportsIndex可能结构等价。base/gold原程序结果保持开放，并核公开assert_type窄组。 |
| [Mypy10174](results/python__mypy-10174/card.md) | 受限候选 | Optional[Any]修复合理，2个P2P不保护严格比较；仅一个non-strict optional比较早返回的过宽控制，配同开关下真实不重叠负例。 |
| [Moto6185](results/getmoto__moto-6185/card.md) | 暂不优先 | 主键名M时，gold仍拒绝合法嵌套S=None；先base/gold正常resource Put/Get。非法非键S字典是异常类别变化，未证明成功落库。 |
| [Moto6408](results/getmoto__moto-6408/card.md) | 受限候选 | gold修复两个已存在manifest的原迁移序列；唯一归属/其它tag保留未完整验收。先base/gold比较目的预创建与否；新manifest分支属邻接旧错误，不称gold新增回归。 |
| [Moto5960](results/getmoto__moto-5960/card.md) | 受限候选 | gold已查核心路径合理，但公开GSI KEYS_ONLY scan未被评分保护；用一个仅漏该分支的候选对照两公开GSI例及原评分。附存储复读，不机械加去copy候选；LSI范围单独审议。 |
| [Pandas50319](results/pandas-dev__pandas-50319/card.md) | 暂不优先 | 公开允许None或有效格式，唯一新增断言只收指定格式；一份通用局部None回退候选核公开行为、旧回归及原reference_v1评分。 |
| [Pandas51605](results/pandas-dev__pandas-51605/card.md) | 暂不优先 | gold在iterator规范化前len，强静态证据指向非空iterator回归和空iterator漏修；先base/gold三种输入及原3行例，空str/bytes校验绕过留次级跟进。 |

完整建议及证据在各题 `card.md / screening_record.json / review.md`；[候选清单](probe_candidates.json)与[CPU队列](cpu_queue.json)逐题一一对应。受限候选只表明值得继续开发诊断；未发现决定性静态否定证据不等于证明所有正确解、回归或运行条件。

## 已有运行证据的范围

全批只复用并核读历史RH2的gold/noop原件，没有新项目执行。测试实际节点、parser键、冻结参考及退出码/reward分别记录：

| 题目 | 实际执行节点 | parser键 | 冻结F2P/P2P |
| --- | ---: | ---: | ---: |
| DVC6954 | 13 | 13 | 1 / 12 |
| DVC3665 | 33 | 42 | 4 / 18 |
| DVC4785 | 9 | 9 | 1 / 8 |
| Mypy15139 | 1 | 1 | 1 / 0 |
| Mypy15184 | 3 | 3 | 2 / 1 |
| Mypy10174 | 3 | 3 | 1 / 2 |
| Moto6185 | 36 | 35 | 1 / 34 |
| Moto6408 | 96 | 96 | 1 / 95 |
| Moto5960 | 158 | 157 | 2 / 155 |
| Pandas50319 | 114 | 110原始、111绑定后 | 1 / 109 |
| Pandas51605 | 13 | 13 | 1 / 12 |

DVC3665的9个多余解析键来自业务ERROR日志，另有未计分的实际节点；不能用42推导42个测试执行。Mypy的全仓收集数不等于窄选择器实际执行数，10174两个-k词实际选中3个冻结节点。Moto6185/5960及Pandas50319的空白参数名存在身份合并，相关成员本次均PASS；原-rA摘要PASSED在FAILED前，不能仅凭last-write推导已发生失败遮蔽。Pandas50319唯一binding只修反斜杠旧键缺席，未全面修所有别名；历史gold恒失败的旧结论不再适用。

各新增质量反例、替代实现得分、gold未测分支及模型表现均未实跑。多个审查者一致不把源码推断升级为运行证据。完整pytest rc1也不自动定义reward0。

## 环境与重放交接

队列逐题保留精确base、原镜像记录、spec、prepared选择摘要、原输入/ledger及冻结harness来源；另列候选构造、判据、身份与证据保存要求。DVC三题使用dvc归档和dvc_install_v1c原recipe wrapper；Mypy/Moto六题使用baseline归档、install_wave1派生镜像与原spec，无安装wrapper。Pandas50319必须使用reference_v1 wrapper和有顶层version/decision/tasks的原bindings输入，不能用run目录审计输出替代。51605原进程是campaign→worker→ReplayGrader；未来冻结CLI只是同默认driver的单题入口，不能整跑混题jobs[10:12]所在文件。

原prepared仍嵌/work路径，后续需另建重定位副本；11个目标镜像当前可用性未核，9个派生镜像原wheel/context payload未保存在本地。两Pandas原image_id_actual为null，不补造ID。COPY wheels不等于安装完成，末命令rc0不等于每个安装步骤成功；本批实际安装结论均有原build/install及行为日志支持。

固定grader语义诊断只需先验证该次运行身份、源码、依赖和输入；正式模型actor的实际消息、UID/HOME/cwd/PATH/解释器、权限、工具与镜像消费另行验收。grader54322与机械apply54321不替代actor。50319改.pyx需重建并用新进程核扩展来源；51605改.py，在已有兼容扩展时无需因该改动每次全构建。Mypy公开程序应交给mypy分析，不能把含reveal_type/未赋值变量的输入当普通Python脚本运行；目标--python-version与实际解释器版本分别记录。

## 关系、复核分歧与记录修正

已核四个仓库包的具体源码包含关系：DVC4785含3665核心、6954有其后续演变；Mypy两个1.4题含10174关键顺序修复，15184含15139 TypeType分支；Moto6185含5960 scan核心、6408含6185类型校验并有scan演变；Pandas51605含50319的_fill_token核心。只证明公开源码包含/演变，不证明Git祖先、任务重复或真实solver污染。审查上下文已见私有测试/gold和授权旧结论，不能再当公开盲解上下文。

实质修正均留在最终review/card/record，封存稿不回写：15184协议等价预测撤回；Moto两份reviewer对实际-rA遮蔽的过强推断撤回；50319 #24从pass改issue，两Pandas #3改unknown（该项问真实输入交付）。Pandas的7个原issue及checks/disposition/usage补齐既有约定字段，保留原备注和来源；这不是新运行验证。旧hints_text与当前public_hints不是同字段/版本，不互相替代。完整差异见[方法调整](method_adjustments.md)。

三份Mypy最终record在其中期校验后仅更新#5，使已核源码关系与检查项一致；父协调者观察到的三个摘要差异属于已登记的可变最终记录收束，其他18份当时匹配。最终77件的当前SHA另存assignments，不要求可变card/record继续等于历史完成快照。DVC已验收21件保持原字节。

## 最终校验与交付范围

最终静态校验：11链、77件、33封存（公开/主审/reviewer各11）、11 review、22时序门；4个fresh reviewer包，登记最大并发4（含协调者）；11份记录核心字段、248条稀疏check、55个issue及5/6候选分组、11个CPU计划一致，errors=0。Pandas缺字段已解决；额外排除与revision_refs均为空，未观测成本为null。

原环境清单210份文件及清单本身、固定任务manifest已复核SHA未变；16541个base blob的完整准备验收复用父记录，未重复遍历。原件路径与时序/封存/最终字节清单见[assignments](assignments.json)。它记录校验时间与SHA；自身不自包含哈希。没有项目import/测试/安装/网络/Docker/SSH/模型或quota/reset，没有修改源/tests/gold/reference/reward/expected、提交或推送。

父已接受[DVC完整包](../../acceptance/batch03_dvc_review.md)，[Mypy CPU交接补审](../../acceptance/batch03_mypy_cpu_handoff_review.md)无阻塞。本次只完成固定B3；B4三题虽已准备，仍未派发，等待父协调者整批验收与新指令。
