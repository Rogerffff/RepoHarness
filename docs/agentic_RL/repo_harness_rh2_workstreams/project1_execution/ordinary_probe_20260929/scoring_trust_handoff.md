# 当前 Scrapy 评分误接收：已完成反例与有限修复交接

2026-09-30整理，实验于9月29日17:44–17:46完成。代码为本批code_v2；本地恢复检查确认`scoring.py`、`r2e_parsers.py`当前共享源码与该版本相同。没有改写生产评分规则。

## 已证实的问题

固定任务Scrapy e938，材料mr026/mr027，实际派生镜像、prepared和65键参考均与本批CPU/API对照相同。两份候选只在原`conftest.py`后追加代码，不改目标`exporters.py`或隐藏测试。正式冻结投影确实只包含`conftest.py`；现有路径标记已记录触碰，但没有阻止以下误接收。

| 候选 | 真实发生的行为 | RH2结果 |
| --- | --- | --- |
| report_hook | pytest的makereport hook将失败报告改为passed；测试进程退出0，目标源码未修 | 65/65，reward1 |
| fake_first_summary | 在pytest配置阶段提前输出65条PASSED和同形摘要；之后真实测试4失败61通过，测试退出1 | parser接受第一份摘要，65/65，reward1 |

两条driver均退出0、完整记录测试终止、容器删除及manager收尾。故这不是日志截断或资源故障。probe的运输有效性判定也未阻止这两个1分，说明运输完整与评分语义可信必须分开验证。

**这是本线程构造的CPU反例，不是两条DeepSeek轨迹中观察到的作弊。** 第二案使用私有证据中的65个键，是白盒反例，不能声称普通模型知道这些隐藏ID。第一案不依赖预先知道参考ID。Scrapy本配方跳过安装，因此没有在本题复验安装脚本生成hook的旧SWE路径。

对照已在同一入口完成：空补丁61/65、reward0；可信替代正解C1为65/65、reward1。C1不是已知有缺陷的来源原始gold。无需为了交接重复已结束的同版本矩阵。

## 证据与重放材料

- [两案正式结果及收尾](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/scrapy_scoring_controls_v1/done.json)。
- [原始失败日志](../../../../../runs/ordinary_probe_20260929/remote/cpu_controls/scrapy_scoring_controls_v1/fake_first_summary/eval_logs/evallog_replay-ordinary29-scrapy_a3b96db6.eval.log)：第一摘要、实际失败traceback、最终4失败61通过和`RH2_TEST_RC=1`均保留。
- [候选清单与SHA](../../../../../runs/ordinary_probe_20260929/remote/inputs/scoring_controls_scrapy_v1/manifest.json)、同目录两份diff；[执行脚本](../../../../../runs/ordinary_probe_20260929/tools/scrapy_scoring_controls_v1.py)。脚本带旧机绝对路径，只作原运行依据；新机先重新生成配置与输出位置，不原地重跑。
- [恢复审计](../../../../../runs/ordinary_probe_20260929/analysis/resume_evidence_audit_20260930.json)：以冻结parser重放两日志，核候选与日志摘要，保留原始reward。

## 建议怎么修、怎样算完成

以下是有界实施建议，**尚未实施**；按原[独立复核§4](reviews/falsifier.md#4-评分信任必须处理的具体问题与可递延范围)继续。不是要求证明任意候选程序无法影响同进程测试。

1. 由评分／材料负责人确认本题哪些文件只负责测试控制。在候选安装结束后、测试启动前，从可信版本恢复并校验相应控制材料；合法库helper或题目本身要修的文件不能全局剔除。控制文件与合法修复面冲突时需记录具体冲突，不能静默抹掉候选后声称评分了它。
2. 本线程的探针消费者补有限的输出歧义校验。需要用实际runner的正常日志、正常失败、嵌套输出／多命令、来源允许的FAILED/ERROR作正控。不能简单“取最后一段”或“testRC非零一律无效”；report_hook的测试退出码本来就是0。
3. 固定以上版本，验证两份未修目标的候选不再获**可采信的1分**；原空补丁、可信正解与合法候选仍按原语义得到结果。新公共拒绝类型、作弊记0、训练组过滤及评分架构变更另行说明，不混入窄修。
4. 将验收的runner／控制政策适用范围写入接收记录。同一实现可复用证据；Pillow的可信unittest入口不能直接套pytest结论。既有SWE安装期生成hook的反例，按其有安装段的实际入口核对，不能因Scrapy通过便宣布它关闭。

目前动作是暂停受影响评分的普通能力比较扩量，保留计划题目和原因；不是把这两条模型原分数改成0，也不是把它们删掉后美化分母。题目修订、环境重建和本地接入准备可以继续。此问题没有被A的root Git修复或分类二的初态修复解决。
