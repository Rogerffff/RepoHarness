# B3 mypy 三题 CPU 交接补审

2026-09-21。仅审 `expansion/batch03/cpu_queue.json` 中15139/15184/10174三条、各题最终card/review及必要原件；未重审整题，未读取已验收DVC包或仍收口的Moto/Pandas包。

**结论：未发现阻塞交接的设计问题。** 三条均有可定位的base/gold、明确的最小问题和开放判据；只有10174需要另构造一个范围明确的错误控制。全部保持未执行，不把历史grader通过、静态机制或未来方案写成新CPU结果。

## 逐题判据与实施提醒

| 任务 | 交接判断 |
| --- | --- |
| 15139 | base/gold原题三行CLI足以检验错误与reveal是否仍混用别名；题面代码和 `public_read.md` D2命令可定位。固定诊断的 `--python-version 3.10` 是检查目标，不能当作实际运行解释器版本；原1.4 spec声明Python3.11，执行时另记 `sys.executable/version`、配置、桩与模块来源。保存完整note/error/退出码，正常类型诊断导致非零退出不是依赖或环境失败。无需先造第二候选，也不能用八个容器类型旧case充当TypeType分支保护。 |
| 15184 | 当前队列和最终card/review已经撤回“SupportsIndex的fullname不同，所以必然不等价/必报错”的旧预测。完整程序用受控目标3.10、包内桩和配置比较base/gold；两侧都无错时记录该条件原例不触发，有错才比较限定名与错误码。不得复用封存公开初读C3的固定错误预期。原2F2P/1P2P全部是应报错的例子；公开既有 `testAssertType` 窄组另验成功、普通失败、返回、Literal/泛型/unchecked语义，不能把那条P2P冒称成功断言回归。 |
| 10174 | 候选作用点可定位到精确base的 `mypy/checkexpr.py:2293` `ExpressionChecker.dangerous_comparison`；仅在non-strict optional条件早返回False，保持严格模式和未导入提示原路径。这是故意过宽的错误控制，不能称合法修复，也不能替换成共享overlap函数恒真或关闭全部错误。与base/gold同时核原1F2P/2P2P、原Optional[Any]目标和相同开关下 `if 1 in ('x','y'): pass` 真不重叠负例。只有候选原reward1且实际漏负例才确认该具体漏收；strict-optional对照若追加，先移除输入里相反inline配置。 |

15139/15184优先只有base/gold，不要求先实现更多formatter变体；10174只需上述一个负控制。三个原题程序应由mypy分析，不能当作普通Python程序执行含reveal_type或未赋值变量的输入。

## 入口、身份与未来准备

- 三题原输入grading、gold patch、install_wave1 plan及指定ledger均可定位。本轮核了plan索引62/63/37及所列规范JSON摘要、账本任务/派生镜像ID与image.json、各题9/9/3个pins一致。10174不能套用两个1.4题的九包清单；其requirements/pre_install初态仍按原记录保留。
- 三个image.json均为wheel COPY与离线pip ENV增层，没有revised_install。队列正确使用原direct replay和derived-image，recipe/materials/bindings均为null，不应套安装wrapper。
- 只读 `frozen_sources/baseline.tar.gz` 中列出的4个成员，字节数与SHA均匹配队列；历史CLI支持所列prepared-summary、裸instance_id、patch候选、derived-image和输出flags。未解包、导入或执行归档，未拿当前RH2冒充历史字节。
- 实际目标镜像/离线payload、受信Python运行环境、新code-root，以及从历史 `/work` 输入另建的重定位summary/manifest，仍待执行者准备。候选diff冻结、实际源码/扩展加载、安装和清理须由新运行留证。这些是明确披露的runtime准备，当前不能宣称命令已经可直接开跑；没有因此发现新的实验设计阻塞。
- **固定grader语义诊断无需先完成正式actor全面验收。** 先确认该次诊断身份、镜像、源码、依赖和输入即可推进；正式actor镜像消费、shell、工具消息、权限与公开开发路径仍是后续模型开发的独立条件。三条队列已正确分开两层，不增设全批或全仓必过门。

## 本轮验证范围

只读了三题最终card/review、队列、公开原程序、10174候选作用点及必要入口/身份原件；自行元数据脚本核引用、plan摘要、镜像/pins和归档成员摘要。没有执行项目、测试、安装、容器、SSH、模型或新CPU实验，也未重核全部历史测试输出。只新增本文件，未改协调产物、原题、评分参考或封存稿。
