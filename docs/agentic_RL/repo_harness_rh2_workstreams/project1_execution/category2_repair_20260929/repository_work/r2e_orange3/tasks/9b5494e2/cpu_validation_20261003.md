# Orange9b54：当前CPU验收

2026-10-03。**R9/020092及批准050316配方的十方已完整核对；新版公开CC及非作者实际终审完成，无必修项；固定单题请求已登记并送GPU，尚无本题模型结果。** 242份原件已回收逐文件核大小/SHA。

| 对照 | 正式reward | 参考状态匹配 | 实际目标结果 |
| --- | ---: | ---: | --- |
| noop | 0 | 11/13 | 第143行L1实际拟合报solver/penalty ValueError；公开L1概率方法也失败 |
| gold | 1 | 13/13 | 合理自动solver修复 |
| V1 | 1 | 13/13 | 不使用auto字面哨兵的合理解 |
| V3 | 1 | 13/13 | L1使用saga的合理解 |
| V4 | 1 | 13/13 | 拟合时解析solver的合理解 |
| V5 | 1 | 13/13 | 映射表选择的合理解 |
| W1 | 0 | 12/13 | 第144行，静默改penalty为l2 |
| V7 | 0 | 10/13 | 第151行，默认solver变成liblinear；另外两个旧FAILED变PASSED |
| P1 | 0 | 12/13 | 第158行，默认repr多出solver参数 |
| G1 | 0 | 12/13 | 第173行，默认与显式multinomial的450/450概率不符、最大绝对差0.38716698 |

13键精确expected中，test_learner_scorer及test_learner_scorer_multiclass两个既有FAILED保持原映射。正例13/13表示全部参考状态匹配，不是所有pytest通过；V7的另两个mismatch实际是这两项由FAILED变PASSED，不能写成三个新错误，但其默认solver目标断言独立支持拒绝。原expected映射和13个参考键均未改写。

每方pytest收集14项，其中既有normalization skip不计入13评分键。完整TEST段、原13键无missing/reference skip/额外key，实际before300/after1200/test1800与footer/清理已核，无基础设施评分失败。97次有限旁路样本覆盖十方candidate/grader共20容器，实际2CPU/4GiB/512、swap0、network none；ledger.resource_facts为空。P1 candidate在22:38:37 UTC出现删除态/PID0/exit137/OOMKilled=false，cgroup不可读，保留原件；不能称测试OOM，也不推断全程无OOM。

[十方结果收据](cpu_matrix_result_20261003.json)绑定完整原件manifest、作者逐键/断言和资源核对。原捕获block的V7尾部还包含第29行skip summary；目标失败仍是第151行，范围说明另存而不回写原check。

[旧三组概率校准](probability_precheck_v2.json)与[独立复用接收](probability_reuse_review_receipt_20261003.json)限定用于旧020/env_v2环境的关系和容差。最终R9的正式G1现在已实测被拒，而正确五解仍通过；不把旧481eb85镜像/512277配方当最终084702镜像/050316配方。

新版公开CC（2.1.205）已在最终084702镜像正常完成，53份原件逐文件SHA/大小已核。四个Bash实际rc为0／0／1／1：preflight和实际Python3.7.9／SciPy1.5.4／sklearn0.22.2.post1身份正常，logistic模块路径为/testbed/Orange/classification/logistic_regression.py；默认公开test_LogisticRegression通过，penalty=l1的test_probability按base缺陷失败（1 failed／1 passed），全iris L1拟合同样明确solver/penalty ValueError。原题面HTTP后缀逐字相同；原生FrozenPatch为空、base未改、无grade、本作业清理正常。[实际CC收据](cpu_actor_result_20261003.json)绑定原件和逐步核查。旧stepID public_default_regression不是两个默认测试，工具is_error=false来自末尾echo，不能当真实rc0；基础实现的L1错误不是导入/环境故障。本次固定合成端点只验证开发链，不能作为基座模型结果。

中性[公开开发说明](public_development_brief.md)已独立核事实与可见边界，本轮CPU未实际交brief，须GPU实际交付/readback。用途限题目/环境质量与基座修法诊断，CPU合格不等于GPU准入、模型能力、训练或留出资格。

[独立实际终审](../../reviews/orange9b_r9_cpu_review_20261003.md)已封，必修项为空；[当前CPU验收收据](cpu_acceptance.json)接续生成时状态，[固定探针输入](probe_request.json)绑定R9/020092、完整050316配方及两模型各1次首轮。请求`r2e-orange9b-r020092-cpu-sysconfig-v1-20261003`已落账并定向送GPU，真实发送工具回执与notice见[提交回执](probe_submission_receipt.json)。提交不等于GPU实际准入或模型结果；本题主持续负责后续语义及七维分析、重复采样和可能修复。
