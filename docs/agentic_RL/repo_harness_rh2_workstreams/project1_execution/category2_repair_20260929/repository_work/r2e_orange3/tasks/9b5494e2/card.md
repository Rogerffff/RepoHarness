# orange3 9b5494e2：当前修订与验收

更新：2026-10-04。**最终R9/020092 CPU十方、公开CC及独立验收，两模型首轮、完整作者七维与非作者必要实际链/语义核查均已完成。两模型各raw1/13of13来源期望状态匹配，实际各11PASS/2既有expectedFAILED/1skip、testRC1、安装SKIPPED。最终L1条件换solver与默认L2概率/none/repr保留受支持，无材料必修项；原请求returned已ACK，活动指针已清。** [当前两模型验收](probe_first_round_owner_acceptance_20261003.json)、[七维分析](probe_two_model_analysis_20261003.md)、[独立审查](../../reviews/orange9b_two_model_semantic_behavior_review_20261003.md)为当前入口；旧[单Coder局部接收](probe_coder_first_owner_acceptance_20261003.json)保留生成时Qwen待齐状态，由新收据接续。[CPU验收](cpu_acceptance.json)、[CPU记录](cpu_validation_20261003.md)、[固定测试](files/r2e_tests/test_1.py)按有效范围复用。

复用已通过方向核查的A＋B′：用真实拟合核L1，不再要求`auto`字面量／私有helper／必须liblinear；L2默认solver／penalty保留，`none`能拟合；保留公开默认repr断言。已有试跑只证明旧A／B′，不覆盖本轮最终材料。

G1曾正式得1，但将默认多分类从multinomial改成OvR，不能沿用旧S2归因。公开本题构造函数默认`multi_class="auto"`、`solver="lbfgs"`；[scikit-learn0.22文档](https://scikit-learn.org/0.22/modules/generated/sklearn.linear_model.LogisticRegression.html)说明此组合在多分类选择multinomial。本轮补默认模型与显式multinomial对同一iris数据的概率预测关系，不抄gold数值、不检查私有params布局。在cpu-c实际Python3.7.9／NumPy1.17.5／SciPy1.5.4／sklearn0.22.2.post1中，base与gold对显式multinomial的最大概率差均为0；G1默认OvR的最大差为0.38716698009532013。此iris数据上rtol1e-5／atol1e-7可保留，仍须正式十方核合理替代解。

保留13键及exact expected，含两个既有scorer expected FAILED，不能写全测试通过；`r2e-mr-020`／SciPy1.5.4／`+env_v2`不省略。其它14个方法AST不变。正式目标：gold／V1／V3／V4／V5=1；noop／W1／V7／P1／G1=0。

R9已按新hidden内容与SciPy1.5.4登记base配方`7e1710…`、含sysconfig完整配方`050316…`，原020保留。旧020-only的`512277…`只用于历史校准，旧`caa2db…`拒绝记录不回写；最终镜像／consumer及完整组合已由本轮十方与新版公开CC核实，详见当前CPU记录，步骤名字不能代替内容摘要。公开题面没有改动，不另派公开读者。[非作者静态窄核](../../reviews/non_author_remaining_material_review_20261003.md)未发现需先改的材料阻断，SHA匹配，但该静态核查没有拟合；当前容差由独立实际运行的作者校准支持，仍不等于新版正式矩阵或最终结果独立核查。

继续第2类。概率关系校准、最终十方、新版公开CC与非作者实际结果终审均已完成；已按固定材料提交普通探针。CPU诊断验收不等于模型能力、训练或留出资格。

9b54前置CPU检查：原020＋env_v2＋sysconfig镜像构建22项通过，但consumer拒绝完整`caa2db…`摘要，CC／拟合／模型请求均未开始；[首轮诊断收据](probability_precheck_v1.json)保留原异常和清理。公共维护者已通知，不能绕过批准检查。另建实际镜像`481eb85…`，完整已批准`env_v2`／`512277…`配方，21项复核通过；真实CC七步均返回0，三组概率拟合和原生最后G1工件保存，actor／gateway／网络全部清理。省略sysconfig只限Python校准，不代替最终开发配方，也未运行新隐藏评分。

[等待回执](probability_precheck_wait_receipt.json)保留前三次75未获槽的记录；总协调轮转后prepare v4及actor v1均返回0，资源等待已解除。不能将75记为题目失败。

当前接续：第九版材料020/092已封包，cpu-c部署与实际镜像绑定已核，最终十方、新版公开CC及独立终审完成，固定GPU请求已登记并实际发送，两模型首轮与独立分析已完整核收，原请求ACK/指针清，当前无已知CPU/GPU待执行步骤，以[恢复检查点](../../resume_20261003.md)及总账为准。固定草案／计划生成时状态不回写。

当前采样按GPU v2覆盖优先，不自行追加。每模型一次不能判稳定能力；Qwen实际原版两scorer失败对照成立，最终“flaky”缺统计依据；Coder构造/拟合误读及自验局限保留，不回写原分/FP。
