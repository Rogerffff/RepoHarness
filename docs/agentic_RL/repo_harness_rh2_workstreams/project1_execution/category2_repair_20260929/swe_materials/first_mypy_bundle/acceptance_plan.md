# 首包验收计划

整理：2026-09-29。状态：**待root执行；不是验收回执。** 仅两题；原件、候选及准确命令以[manifest](materials_manifest.json)为准。新产物放本批新run目录，历史材料不回写。

## 1．先补既有配方的消费证据

1. 核09-19 `install_wave1`固定派生image是否仍在，核原base digest、派生层和wheel资产SHA。不存在时按已保存recipe与确切wheel清单重建，记录新image ID；无需改变公开题意、测试或安装语义。完整依赖以固定原镜像初态为准。
2. 核实际grader使用该派生层及`install-wave1:<instance_id>`身份。10424初始`test-requirements.txt`已有修改须保留并记录，候选仅修改指定mypy源码；不能清理掉镜像自带依赖改动。
3. 用真实grader身份及deny_all网络核`pip install -r test-requirements.txt`、`pip install -e .`和其余既有安装命令的逐步退出、完整输出。已有安装成功证据可复用，但新增C1/新增case这一行必须没有失败子命令；段末rc0不足以证明。
4. 记录Python/pytest、实际`mypy.checker`与`mypy.meet`（10424）或`mypy.typetraverser`（17071）来源，核实际导出补丁和源码SHA。仅`mypy.__init__`来自checkout不证明所有模块生效；若加载编译模块，核其确由该候选源码产生。
5. 在此配方上先做两题各自C1的新增公开case。已有base/gold窄旧测证据可复用；若运行条件/源码身份不等价，只补受影响base/gold控制。保留完整stdout/stderr、真实子命令退出与测试汇总，不用`tail`或`grep PASSED`裁决。

这一阶段只确认环境和待接入判据。D6未接入时，不改正式reward、不转第1类。安装失败须先解释、修复消费后续接；不会把缺少wheel等infra问题写成候选0分。

## 2．D6接入后冻结正式版本

D6负责人须证明：同一个版本对象被真实评分入口用于题面/测试材料、选择器和参考；原参考仍在；追加旧测试文件按固定base字节恢复并受到候选保护；材料版本、运行配置、结果引用能追溯。该公共实现不在本包代码范围。

10424：原`testNarrowingUsingMetaclass` F2P，新增以下完整P2P节点：

```text
mypy/test/testcheck.py::TypeCheckSuite::testTypeEqualsCheckUsingIs
mypy/test/testcheck.py::TypeCheckSuite::testTypeEqualsNarrowingUnionWithElse
```

17071：保留manifest中的2 F2P和2 P2P，新增：

```text
mypy/test/testcheck.py::TypeCheckSuite::check-typevar-unbound.test::testUnboundTypeVar
```

正式首片按[D6方案](../../d6/implementation_brief.md)保留vendor命令前缀，只扩展受信`-k`选择，并核真实收集节点集合与完整参考集合严格对应。manifest的显式节点argv仅用于材料说明或私有定点诊断，不直接替代正式命令。预期收集分别为3项/5项，须以实际运行确认，不能以选择词数或解析键数代替。记录pytest collector版本，防不同mypy版本的`.test`层级混淆。

新增可信恢复文件为`check-isinstance.test`和`check-typevar-unbound.test`，不是更改原`test.patch`来复制同名case。保护应覆盖测试内容与调用入口的既有安全边界；本包只提出新增文件需求，不改变公共安全政策。

## 3．最小正式正反矩阵

| 题目/候选 | 原版事实 | 新版预期 | 必须说明的失败/通过原因 |
| --- | --- | --- | --- |
| 10424 noop | 0（09-19派生） | 0；F2P 0/1，P2P 2/2 | metaclass原缺陷仍触发，普通收窄正常 |
| 10424 gold | 1 | 1；F2P 1/1，P2P 2/2 | 原例修复且普通收窄保持 |
| 10424 C1 | 1（09-25原镜像，安装失败另列） | 0；F2P 1/1，新增P2P 0/2 | Any/Union不再缩为int，不能只说reward变0 |
| 17071 noop | 0（09-19派生） | 0；F2P 0/2，P2P 3/3 | 合法guard/is仍误报，真正unbound继续拒绝 |
| 17071 gold | 1 | 1；F2P 2/2，P2P 3/3 | 合法guard/is通过，真正unbound继续拒绝 |
| 17071 C1 | 1（09-25原镜像，安装失败另列） | 0；F2P 2/2，P2P 2/3 | 新testUnboundTypeVar因缺应有诊断失败 |

这些是**预期**；新版六行均未执行，不预填结果。新D6版本需要这六行作为机制与材料联合验收；D6前的准备阶段不要求另做一套相同正式矩阵。17071 q36_a1是可选的已有真实成功候选，仅在需要证明接受性时加一行；没有必要重放全部历史成功模型尝试。原始奖励原样保留，修订奖励带新版本另列。

## 4．完整性与独立验收

每行至少保留：候选patch及实际投影SHA；base/镜像/离线资产身份；安装所有子命令/实际源码来源；完整测试段及真实终止；每个F2P/P2P的唯一节点与状态；缺席/skip/xfail/全局失败的解释；候选容器与manager清理。新引用不得缺席或跳过，正常已知失败应有目标断言，不能由导入/收集/安装故障替代。

独立reviewer复用既有公开语义与旧运行审查，只定向核新材料、可信恢复/选择的真实消费者、安装消费和六行关键原件。作者准备或本地SHA校验不算独立正式验收。全部通过后逐题给根线程交接：版本、已修内容、证据、独立意见、剩余用途限制；由根线程汇总转类，不回写旧卡或历史分数。

## 5．停止条件与范围

- 新节点不存在、被截断/合并、未恢复固定测试、候选源码未生效、安装子命令失败、日志不完整或清理不明：保留第2类，先解决具体原因，不把异常记作有效模型失败。
- gold在新增既有case失败：暂停该题准入，核材料/安装/源码与真实行为；不能删掉公开护栏来保gold，也不直接宣布无正确解。
- 当前没有需要用户重新选择的题意范围。若后来出现真正互斥的公开规格选择，带具体证据单独提交；常规公开依据修订继续按授权推进。
- 只修评分与grader资产；题面与原测试字节保持。没有新的模型调用、GPU、全仓回归或第三类调查要求。正式训练/留出资格仍未授予。
