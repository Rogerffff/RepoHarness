# Scrapy a95a：CPU修订验收

2026-10-03。rev4／修订066、067的正式8候选全部符合预期；新宿主上的真实Claude Code开发检查和目标Python3.9警告观测已完成。非作者核查的最终结论见[独立报告](review_cpu_acceptance_20261003.md)，逐键及原件路径见[机器记录](cpu_acceptance.json)。本页不记录基座模型成绩，也不授予训练或heldout资格。

## 修订效果

原测试会放过“吞掉TypeError后恒False”和关闭警告的候选。rev4在原partial键中增加已有公开依据的True断言，并在22个原警告记录块内恢复Warning记录。保留原条数、文案及五键集合；两个死键改为PASSED，评分脚本不变。类别没有被限制成UserWarning。

| 候选 | 实际分数 | 确认的失败机制 |
| --- | ---: | --- |
| C1 | 1 | 五键通过，有效正对照 |
| C1_RuntimeWarning | 1 | 五键通过，合理类别差异未被误拒 |
| gold | 0 | 带返回值partial绑定方法漏判 |
| noop | 0 | 原partial实现抛TypeError |
| D | 0 | 吞异常后恒False，漏掉有返回值partial |
| C2 | 0 | 警告关闭，且保留gold绑定方法缺陷 |
| C2b | 0 | 恰好只在两个警告键失败，partial通过 |
| C3 | 0 | 恒False，漏掉普通带返回值生成器和partial |

每个唯一候选1次，均完整解析5键，无missing／extra。八份原日志SHA、实际测试退出码、补丁apply、投影、runner完整性、原baseline与FrozenPatch对应，以及评分管理器清理均已核。原gold保留为负对照，不把它包装成正确答案；正对照使用此前独立依据的C1。旧rev2九次试跑仍是历史证据，不与本轮数量相加。

## 版本与实测

正式矩阵绑定第四版`cat2-cpu-r2e070077-swe6-20261003-v1`／manifest`621e7366…`；开发检查重新绑定含Git窄修的第五版`cat2-cpu-r2e078079-swe7-git-20261003-v1`／manifest`80ee228d…`和`runtime_cpu_v2`。分别用各版本受信loader读回，Scrapy public／grading bundle及066、067条目完全一致；R5重新生成prepared/private，正式任务面接受既有overlay，实际镜像ID匹配。没有改绑旧FrozenPatch或重写旧尝试。

派生镜像实际ID为`sha256:ac29555d3b7cceaf6d2ce5654eda8d04408bcea370e6373963a04565b7d05ded`；配方`r2e_derive_v1+material_v2+sysconfig_v1`，SHA`22f7c2ec…`。镜像保留原依赖，没有pytest降级或Scrapy依赖改装；本题env_pins为空。共享builder的daemon build资源限制没有被本题声明为已验证。

真实CC2.1.205通过本地桩发出5次Bash操作：R2E预检、解释器／导入、核SHA后应用私有C1、文件形式公开复现、现有公开测试。五条均退出0；agent UID54321，解释器`/testbed/.venv/bin/python`、Python3.9.21、Scrapy2.7.0来自`/testbed/scrapy/__init__.py`。复现返回False，公开4个测试通过。实际容器为2CPU／4GiB／512进程；隐藏测试不可读、未来提交不可达、激活文件不可写。CC正常结束，6次桩消息与轨迹对应，无真实模型调用，容器、relay、网络和桩清理均无残留。

原记录保留两个通用检查的false：它们只搜索`RH2_SYS_EXECUTABLE`和`RH2_BASHENV_WRITE`标记，而本题清单未输出这些标记。解释器和激活保护由上述实际capture、activation_check和prelaunch证明；没有改写false，也没有声称额外标记命令已跑。

两份私有警告观测各执行5用例，22个原记录块均为16个空块＋6个单警告。C1全为UserWarning，类别对照全为RuntimeWarning；类别以外的文案、文件和行号相同，均来自目标`test_1.py`的79／84／89／94／99／277行，没有无关依赖警告替代或混入。原断言通过、过滤器恢复、退出0，观测容器均已删除。该root观测补充正式评分与actor，不能代替二者。

## 证据边界与后续

build、矩阵及开发原件位于`runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/`对应唯一作业目录，完整索引与摘要在机器记录。开发包56份文件逐SHA／长度核回，无省略；它们是字节证据副本，没有复制源chmod／mtime，本地回收的private view不是运行输入。GPU执行者须在其宿主从固定发布版重新生成prepared/private，保留私有权限并核实际镜像身份。矩阵大binary snapshot未纳入回收包，独立核查没有离线重建全树census；正式执行的原baseline重建及逐候选清理记录正常。

CPU条件收口后提交统一单卡队列，每模型先1次，预算引用`probe-wide-v1`。只有原题面及[中性开发说明](public_dev_notes.md)进入fresh solver；本包私有候选、gold、验收矩阵和诊断不得进入模型上下文。执行回执后，本题主继续审实际候选、评分及必要修复。

历史已确认本题答案／隐藏测试出现在Scrapy75450e75初态，本题初态还包含9a15fcf8和e9387529修复。同源关联题按D3放在同一侧并控制重复采样；当前只申请标明材料版本的普通基座诊断。
