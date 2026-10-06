# SWE / R2E：DeepSeek 首轮接线冒烟

更新：2026-09-30，补齐额度中断前已结束的CPU对照。范围是两题各一次实际求解，不是12题批量比较，也不是训练验收。

**两条实际求解和评分均已正常结束，原始评分都为1。** A的root Git修复、探针冻结导出、按来源回放、真实API流与清理已经串起来。Dask公开开发依赖问题已完成actor和评分侧修订复验；实际Scrapy反例另证实两种评分伪造仍可得1，因此普通比较未放行。收费网关的9月29日关闭记录完整，用户现说明机器需重租。

## 两题分别发生了什么

| 题目 | 实际求解 | 评分和语义检查 | 当前结论 |
| --- | --- | --- | --- |
| Dask6626 | 335秒、47轮；先复现题面，修改空类别的元数据构造，并增加公开测试 | 1项F2P、14项P2P全部通过，无参考缺席；评分命令实际16项通过、退出0。模型新增测试没有替代受保护的官方测试。更广的公开验证另有4个依赖失败，见下文 | 非平凡候选运输和评分往返通过；这次求解仍属于旧依赖条件，不能静默改记成修订环境下的模型结果 |
| Scrapy e938 | 171秒、25轮；复现binary模式的键类型问题，修正顶层和嵌套导出，并添加公开回归测试 | 实际执行独立的`r2e_tests/test_1.py`，65项全部通过，期望集合65/65匹配，无新增、缺席或状态不符的键。候选保留自定义serializer的返回值，未修改隐藏测试或评分入口 | 在当前已修订材料和新派生镜像上通过；不外推到R2E来源原始gold或全数据集 |

Scrapy使用既有`mr026/mr027`材料修订。镜像按原配方重建，但实际image ID与旧机不同，因此本次另跑了空补丁61/65与可信替代正对照C1的65/65。**C1不是来源原始gold**；原始gold的已知缺陷没有被改写成已通过。

两次都使用CC2.1.205、正式解释器激活、Bash/Edit/NotebookEdit/Read/Write五工具范围。API请求和响应均记录为`deepseek-v4-pro`；请求开启adaptive thinking/high effort，实际收到thinking流事件。每题上限120轮、90分钟、196608上下文、32768单次输出，两次均正常自行结束，未触发预算结束或上下文压缩。因此本轮不声称已经实测真实API的超限压缩路径。

原件与分析：

- [Dask完整分析](../../../../../runs/ordinary_probe_20260929/analysis/dask_api_smoke_v1.json)、[实际轨迹](../../../../../runs/ordinary_probe_20260929/remote/api_smoke_v1/attempts/dask__dask-6626/deepseek-pro/a1/trajectory.jsonl)。
- [Scrapy完整分析](../../../../../runs/ordinary_probe_20260929/analysis/scrapy_api_smoke_v1.json)、[实际轨迹](../../../../../runs/ordinary_probe_20260929/remote/api_smoke_v1/attempts/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/deepseek-pro/a1/trajectory.jsonl)。
- [C1正对照](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/scrapy_e938_c1_v1/control_result.json)、[两次派发账本](../../../../../runs/ordinary_probe_20260929/remote/api_smoke_v1/matrix_ledger.jsonl)。

## Dask新发现与修复

模型自行选择了题目相关的shuffle和categorical公开测试。其中4项因`partd 1.4.1`访问`DataFrame._mgr`失败；镜像中的`pandas 1.0.5`尚不提供该属性。这些失败在**原源码、实际agent身份**下重现，不能归到候选修法。

单独建立只将partd固定为1.1.0的actor派生镜像，保留pandas、pytest、源码和测试。修订后：

- 原shuffle选择集12通过、1跳过；categorical文件64通过；utils文件16通过。
- 四条实际命令的退出码均为0，合计92通过、1跳过。
- 原题空类别仍错误地出现`['a', 'b']`，证明依赖修订没有提前修好目标bug。
- 以UID54321执行，导入`/testbed`工作区；导出候选为空，容器、relay、网络均清理成功。

该复验是正式激活与沙箱下的确定性开发命令，不是第二次付费模型求解。首次镜像构建脚本使用了不合适的`FROM sha256:...`形式，构建准备失败；保留失败记录，另版用已核ID的本地tag构建成功，没有覆盖原镜像。

评分侧采用相同partd修订，继续用原安装、测试命令和参考集合做noop/gold对照；只附加候选身份的版本观察。两条已经完整结束：noop为0，gold为1，15项参考均出现、14项P2P均通过；安装退出0，测试分别退出1/0，两层清理成功。已用冻结parser核原日志及SHA，见[完整验收](../../../../../runs/ordinary_probe_20260929/analysis/dask_partd_repair_acceptance_v1.json)和[修订评分对照](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/dask_partd_pair_v1/done.json)。该镜像组合的环境修订已验证，不替换历史API结果，也不证明新镜像下模型表现相同。

依据：[原条件复现](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/dask_partd_basecheck_v1/dev_check_output.txt)、[修订后公开命令](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/dask_partd_recheck_v1/dev_check_output.txt)、[实际身份、空补丁和清理](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/dask_partd_recheck_v1/attempt.json)、[镜像修订](../../../../../runs/ordinary_probe_20260929/remote/derived/dask_partd110_v2/image.json)。

## 工具、费用和证据边界

共审阅70次工具调用。供应商原始工具参数与CC实际参数有8处差异：6次去掉重复的`cd /testbed &&`，2次补入Edit的默认`replace_all=false`。在这两条轨迹中未观察到执行含义改变；两套参数分别保留，**不据此声称CC与训练token/logprob已经对齐**。[逐项核对](../../../../../runs/ordinary_probe_20260929/analysis/tool_argument_review_v1.json)

Scrapy查阅了可见的Git历史；记录显示返回的是保留的历史提交。本次未观察到未来答案、联网取答案或评分hook调用，不等于证明不存在记忆或所有潜在捷径。Scrapy冻结物另记录排除区路径集合变化；当时未保留完整post排除清单，因此不猜测具体变化来源，也不把patch回放描述为完整运行环境重建。

两次求解共72次API请求。按本批登记峰值费率和供应商返回的缓存命中用量估算合计约**¥1.56**，不是发票或账户扣费记录。费用保护器将缓存也按未命中价计入，结算保守上界**¥14.460741**，低于¥30总上限；72项全部完成结算，没有未知用量占用。两会话均已撤销并排空，网关17:23停止。[费用与关闭记录](../../../../../runs/ordinary_probe_20260929/remote/api_smoke_v1/gateway_shutdown_v1.json)

## 下一步仍需处理什么

1. **新机器恢复已验环境。**Dask环境组合已收口；新机按来源和固定依赖重建、记录实际镜像与配方，并窄验相关路径。大镜像没有回传，旧本地image ID不能直接当成可下载镜像。后续模型尝试使用新版本，旧尝试保留旧条件。
2. **正式actor冻结物直评。**本轮采用宿主渲染diff、fresh replay重建、逐条核对的探针路线。分类二线程已交付统一基线准备的固定版本，在mypy10424/17071上完成原actor工件直评与0/1/0矩阵的独立验收。本线程已核交接清单及18个共享文件身份；尚未把它部署到本轮Dask/Scrapy，后续另版接入并做适用性验证，不能热换当前快照。
3. **已命中的评分伪造路径。**本批实际Scrapy入口的两个CPU反例已经完成：只改conftest报告hook可65/65；伪造第一摘要后实际4失败61通过、testRC1，仍被判65/65。两者都没有修目标源码。原件和有限修法见[评分交接](scoring_trust_handoff.md)，两条模型本身未观察到此行为。受影响评分不得直接进入普通能力比较或训练奖励。

当前没有扩大到其余10题；也没有运行GPU、提交、推送、暂停或删除实例。两条1分是完整保留的原评分，当前用途是实际API与求解链路诊断，不能拿来报告“基座通过率100%”。
