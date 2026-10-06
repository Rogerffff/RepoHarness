# 首包：mypy 10424 / 17071

整理：2026-09-29。**两题都可复用现成公开旧测试，不需要改题面或再造测试。** 本包已准备评分材料增量、候选、准确节点和安装复用依据；尚未接入D6、未执行当前版本正式评分，两题保持第2类。常规公开依据修订已有授权，本包没有新的必须用户决定事项；D6公共入口的决策与实现由根线程处理。

## 实际要改什么

| 题目 | 原参考 | 拟追加P2P（通过后仍应通过的旧测试） | 拟用参考总数 |
| --- | --- | --- | --- |
| mypy10424 | 1 F2P / 0 P2P | `testTypeEqualsCheckUsingIs`、`testTypeEqualsNarrowingUnionWithElse` | 1 F2P / 2 P2P |
| mypy17071 | 2 F2P / 2 P2P | `testUnboundTypeVar` | 2 F2P / 3 P2P |

10424两例分别要求普通`Any`和`Union[int,str]`在`type(x) is int`分支缩为`int`，并保护else结果。17071旧例要求真正未绑定的无约束、带上界和受约束类型变量继续报错。原有TypeGuard/TypeIs正例与bool/分支收窄P2P保留。已有`TypeGuard[U]`回调却返回另一`T`的诊断继续作为语义核对，复用原命令，不复制成另一份正式测试；它目前尚未成为正式评分节点，不能写为已纳入覆盖。

**引用、选择和可信恢复须一起变化。** 原mypy命令按原`test.patch`提取case形成`-k`；仅追加P2P JSON不会执行新节点。10424新增公开文件`test-data/unit/check-isinstance.test`、17071新增`test-data/unit/check-typevar-unbound.test`均未被各自原`test.patch`触及，必须纳入可信base恢复/候选保护。不能让候选修改这些旧测试后仍作为新增P2P评分。这是给D6负责人的具体消费要求，本包不实现它。

[材料manifest](materials_manifest.json)含完整base commit/tree、原件SHA、case行号/字节SHA、历史真实pytest节点证据、完整拟用引用集合及显式命令。10424节点没有`.test`中间层，17071节点包含该层；不得用统一字符串模板猜节点。新容器的`--collect-only`核验仍待root执行，不能把历史真实节点证据称为本轮新收集。

## 现有正反证据

| 候选 | mypy10424 | mypy17071 |
| --- | --- | --- |
| base / noop | 原metaclass例为`<nothing>`，普通收窄正确；原评分0 | 合法guard/is错误报unbound；真正unbound正确报警；原评分0 |
| gold | 原例为`Type[C]`，TypeEquals 6通过；原评分1 | 合法guard/is通过、str推断保持，真正unbound报警；135通过/1 xfail；原评分1 |
| 已知C1错解 | 关闭普通收窄，原评分1；4旧测失败，其中包含拟增两节点 | 禁用unbound检查，原评分1；`testUnboundTypeVar`失败，134通过/1 xfail |

这些来自09-19与09-25不同固定条件，不能拼成已完成的新版本矩阵。首包冻结了gold和C1补丁；17071另留一份已有真实成功`q36_a1`补丁作按需接受性控制，不要求无变化重跑四份成功候选。现有正对照在声明行为范围内成立；没有已证gold回归。历史完整账本、逐参考摘要、导入、安装和清理的读取结果在`runs/category2_repair_20260929/swe_materials/first_mypy_bundle/historical_evidence_readback.json`。

17071历史`rc.json`的0来自`echo rc=$?`/`tail`包装，不能当内部mypy/pytest通过。C1的“真正unbound”输出是错误的`Success`；已有公开测试正文明确1失败。10424该版本仅打印`reveal_type`也可返回1，必须按输出类型判原例行为。

## 安装已经有修法，缺的是正确消费

09-25的10424 gold/C1及17071 C1使用公开原镜像：`image_local_build=false`、`derived_image_recipe=null`。完整错误均为`pip install -e .`的PEP517隔离构建尝试联网获取`setuptools>=40.6.2`，在deny_all网络下DNS失败，最后找不到分发包；子命令rc1被后续命令的段末rc0掩盖。测试确实运行，不等于安装全成功。

09-19的`install_wave1`已给两题补了离线wheel资产；原base层不变，原安装命令不变，gold/noop日志均有实际build/install成功和完整测试/清理。应直接复用：

| 题目 | 既有派生grader image ID | 离线wheel |
| --- | --- | --- |
| 10424 | `sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08` | setuptools75.1.0、wheel0.44.0、packaging24.1 |
| 17071 | `sha256:65be15358f008d20c0dd256c9e70e3f09c85154113ea04875f1a71e98ed751fe` | setuptools68.2.2、wheel0.43.0、typing-extensions4.8.0、mypy-extensions1.0.0、tomli2.0.1、types-psutil5.9.5.17、types-setuptools68.2.0.0、packaging23.2 |

[安装复用清单](installation_reuse.json)绑定原镜像digest、历史build/image/plan/catalog、全部wheel SHA/大小、原安装失败完整段和复用入口。wheel SHA来自历史资产清单，本目录没有wheel payload，也未核当前远端镜像存在；root需核实际资产后使用。pins不是完整依赖锁，不能脱离原base初态声称等价。

D6前可先做的CPU工作，是在既有修复配方上补C1及新增case证据；没有必要重新发明安装或无变化复跑整套开发检查。具体执行、停止条件和正式版本矩阵见[验收计划](acceptance_plan.md)。

本包是已见私有材料的准备产物，不可交solver；没有SSH、容器、模型或项目测试运行，没有修改旧卡、历史分数、生产源码或共享分类。
