# Orange9b 两模型首轮：独立语义与行为窄核

核查时间：2026-10-04，Asia/Singapore；文件名沿用约定的20261003。非作者subagent，结论适用于请求 `r2e-orange9b-r020092-cpu-sysconfig-v1-20261003` 的两份首次真实样本。

**两份最终补丁均符合当前公开要求，原 reward 各1，来源预期状态各13/13匹配。无题目材料、consumer或候选必修项，新增Qwen及两模型分析独立核查完成，可由题主核收当前返回请求。** 正式日志实际各为11 PASS、2个来源 expected FAILED、1个未计分SKIP，testRC均1；13/13不能改写为全部测试通过。每模型只有一次，不能推断稳定能力、模型排名或训练资格。

本轮只读本地原件，未运行CPU/GPU/SSH、候选、新测试或模型。未改旧sealed报告、作者文件、成绩、总账或请求，未ACK或清active。范围复用[已封Coder审查](orange9b_coder_first_semantic_behavior_review_20261003.json)和[已封R9 CPU验收](orange9b_r9_cpu_review_20261003.json)，本轮不重验Coder390成员或旧CPU十方，不重复fresh/static/common101。Qwen机械执行收据按其运输范围复用；补读原候选、完整325事件中的全部模型文本/21工具输入输出与必要实际链，未把缓存码、上报布尔或机械收据当语义证明。

## 最终修法与原评分

Qwen原FrozenPatch只有 `Orange/classification/logistic_regression.py` 一项modify。它保留原初始化与 `self.params=vars()`，随后仅在 `penalty=="l1" and solver=="lbfgs"` 时将 `self.params["solver"]` 改为 `liblinear`。原 `SklLearner.params` setter筛入sklearn参数，`_initialize_wrapped()` 和 `fit` 使用该参数字典。Coder在原赋值前改局部solver，最终参数行为等价。L1没有被降为L2，也没有吞异常、伪造输出或放宽库校验。

默认L2/lbfgs/`multi_class="auto"`、none和原来可用的显式solver不进入新分支；默认repr、score/Normalize/coef路径没有改动。默认多分类概率关系仍是L2 auto/lbfgs与显式multinomial的关系，新L1/liblinear的OvR符合当前要求，不能把它等同于旧G1全局改默认OvR的退化。没有据此认证所有不兼容显式solver、dual、多分类组合或整个Orange参数空间。

Qwen FP canonical为 `9767856092f13273070586236318c4bee3b2b4f4783a199e94dad0c8b0b0360b`，源码内容SHA为 `9b1a23c683c2109647607c28aa26cd05e77a4df697593e632c28cd78b4b37952`。独立校验FP内容和canonical；822B审阅diff按实际baseline源码作纯文本重建后逐字等于FP。投影包含唯一原entry，原FP重放、完整baseline重建census与原census相等。Coder保留源码和新增helper共两项，按旧sealed范围复用，没有事后替模型删脚本。

[正式Qwen日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/eval_logs/evallog_gpu1003-orange9b-qwen36-_593ba0d3.eval.log)的13个来源键逐状态等于host expected map，安装SKIPPED/null，apply成功、完整结束、正式testRC1，未发现新增默认退化。两个FAILED实质如下：

| 来源expected FAILED | 实际首失败 | 没有达到的后续断言 |
| --- | --- | --- |
| test_learner_scorer | 第70行：major vessels colored ≠ chest pain | 第71行形状 |
| test_learner_scorer_multiclass | 第92行：aquatic ≠ legs | 第93–100行排名与形状 |

两方法都使用默认L2，新条件不进入。Qwen 239→243实际stash候选后重测这两个公开selector，原版仍以相同行和不等值失败；257→261成功pop，275→279读回正确候选，最后两selector再次通过。这个实际对照支持旧失败归因；没有跑完整baseline文件，没有重复统计证明“flaky”。来源允许FAILED也不证明特征排序在所有用途都正确。原FAILED和RC保持原样。

## 七维决定性事实

下列事件号为[原harness trajectory JSONL](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/harness/trajectory.jsonl)的1-based行号；完整工具ID、输入和对应结果位于同名审查JSON，分清捕获的语义错误与工具is_error。

| 维度 | 独立核到的行为与边界 |
| --- | --- |
| 方法与纠错 | 7读题、19公开测试、34源码、56/57真实fit失败，继而129追踪参数/fit链，157→161唯一Edit。135错误地将fit校验归到构造阶段；153说liblinear唯一支持L1，与此前列出的saga矛盾。实际Edit保留窄条件，没有按错误文字扩大。 |
| 定位 | 11→19首读公开测试，30→34读43行目标源码，40已正确定位默认lbfgs/L1冲突，48→56实际复现。brief已给模块、fit和selector，不能称从未知仓库独立发现。 |
| 工具 | 21调用/21结果：Read5/Bash15/Edit1，2个is_error是215候选全文pytest与243原版两scorer。143→147重复未变Read收到“Wasted call”。57的liblinear OK只来自构造；56/57的异常捕获后RC0不是需求成功。175→179真实liblinear拟合成功。 |
| 批量与并行 | 首msg组11/15为Read+Bash，另一组48/52为两Bash，确有两组同message工具。20实际generation/HTTP不同于CC22回合或21工具；没有执行起止区间，真实重叠与并行收益未知。Coder单工具组按旧审查复用，不推出模型不会并行。 |
| 验证 | 179真实L1 fit、197两公开selector PASS；215全文2FAIL/10PASS/1SKIP；243原版两FAIL对照；261恢复、279读回；293六配置真实fit成功及第七概率布尔True；311最后两selector PASS。第七项没有assert，沿用公开all()表达式，不是严格逐概率误差验证，七项打印不能叫七个pytest PASS。正式auto_solver另通过L1多类/二类、保留L1、默认L2/lbfgs、repr、none及默认概率严格allclose；这些属于grader，不冒充模型自验。 |
| 效率 | Qwen solve48.526s、CC45.202s/API28.050s、gateway20响应总时长27.559s。重复未变Read、碎片查base、再跑相同selector有额外往返；原版scorer控制解决了真实不确定性。相对Coder略短3.666s只是本次观测，没有测节省秒或稳定效率。 |
| 结束与稳定性 | 325 success/end_turn/completed、harness0。321准确披露两个公开selector PASS和原版相同FAIL；“flaky”没有统计支持，概率sum-to-1表述也比布尔打印证据更宽。候选正确与中间推理/自验局限分别保留；每模型首次一次。 |

Coder旧审查已确认其反复将构造成功误当L1支持、怀疑版本/校验，后来读真实_check_solver并正确修复；最终两公开selector通过属实，full backward compatibility超出自验覆盖。Qwen更早承认真实fit失败并实际核了两个原版scorer，仍有上述推理、重复Read和概率自验局限。这些行为差异不转换为总体模型优劣。

## 计量、身份与可比性

| 口径 | Coder范围复用 | 本轮Qwen |
| --- | ---: | ---: |
| 工具 / CC回合 / HTTP生成 | 23 / 24 / 24 | 21 / 22 / 20 |
| 累计input / output tokens | 209848 / 4589 | 203005 / 4543 |
| 单次max input / output | 13609 / 682 | 15719 / 787 |
| solve秒 | 52.192 | 48.526 |
| CC总秒 / API秒 | 48.834 / 33.347 | 45.202 / 28.050 |
| gateway响应时长总和 | 32.786 | 27.559 |
| trusted_init秒 / actor墙钟秒 | 114.785 / 201.451818 | 105.515 / 187.608427 |
| grader总秒 / wrapper测试秒 | 124.793 / 3.482 | 125.113 / 3.540 |
| TEST marker秒 | 2.463198（旧报告口径复用） | 2.490122751（日志字面Decimal） |
| 派发后整个job秒 | 327.728305 | 314.232041 |

Qwen actor墙钟由实际started_at `14:41:20.926838` 至finished_at `14:44:28.535265` 相减；冻结入口源文件在清理后记录finished_at，不能因字段不叫ended_at就认缺失。它含准备、求解、冻结和清理，不是solve。pytest正文1.93s、TEST marker2.490122751s、wrapper3.54s是不同区间。纯工具/GPU时间及派发前排队未知，grader queue0只限评分管理器；CC cost是元数据估算。累计输入不是上下文峰值。

首源码Read结果距首次generation请求1.810078s，首次真实fit失败5.886078s，Edit结果25.501078s，修后fit成功27.396078s；各自所属generation→结果分别0.438317、4.068047、4.510256、1.878653s。这些都含生成、工具和往返，不能当纯定位或纯工具耗时。

两臂原题面/brief逐字交付、baseline manifest、020/092材料、prepared `25b300…`、host `4632b7…`、expected map `cd0340…`、完整recipe `050316e44910d53ea3ded25e5a510a01c43e1ed60e1034270385ff9dcbe7fff1`、实际actor/grader镜像 `08470256e1bdb8e6952a77280695ca7bdb89800d3409eca7cc0a24aa5b96d4d2`、评分脚本/预算与entry `bdf806…`一致。实际Qwen容器和评分容器镜像另由旁路样本支持，不单靠模板/声明。baseline tar文件SHA各不同，manifest相等，不误称归档字节一致。两个模型服务、checkpoint/采样和现场状态不同，不称整个runtime一致。

Qwen首次实际HTTP中的solver prompt SHA `23b45f…`与原prompt逐字相等，neutral brief `33d7e3…`与题主源文件逐字相等，仅拼接去末端空白；其中test_probability明确penalty=l1。20 HTTP实际max_tokens均65536、模型Qwen3.6-35B-A3B，全部200、无stream_error。context196608、240 CC回合、solve10800、1024请求是固定配置；本次峰值未触顶，不能证明满预算承载。CC元数据maxOutputTokens32000不替代实际HTTP65536或成为32K截断证据。

预启动capture实际时间14:41:20.229311–.387601 UTC，关联13:24/13:26启动、restart0的实际engine/adapter ID、只读checkpoint mount和37文件sizes。实际配置/HTTP支持本job服务身份；没有重验每个权重SHA或逐POST物理GPU权重attestation。原input_check config_only/readback=false、checkpoint_identity_verified=false、code_snapshot_id和typed grading identity/qualification空均保留；补证只覆盖明确的操作范围。

## 清理与资源证据边界

原FP评分status、实际projection、baseline重建和完整日志互相绑定；runner SHA前后不变、无regrade，actor及grader清理无遗留，管理器创建/删除各1，open/supply/failure列表空，gateway撤销active0/drained和静止屏障成立。终端原job0及确切PID1“Deactivated successfully”日志支持正常结束，未用systemd not-found默认0冒充实际退出。

Qwen22份有限旁路样本，actor/relay各13、grader8：实际cgroup观测memory.peak最大分别2055983104、27602944、992952320B，采样中oom_kill未见非零。原grader另报告peak1185.148MB，保留它与旁路峰值的不同口径。没有本job HostConfig/cpu.max/memory.max/PidsLimit限额直接快照，profile声明2CPU/4GiB/512/swap0不能当本次独立实测；resource_facts=null、env_qualification absent。空containers不代表资源用量0；不外推全程无OOM/连续峰值、不把relay说成同actor限额，也不把宿主GPU占用归本job。

实际直接加载观测只给Orange/__init__.py，没有logistic模块加载字节SHA；原FP/投影/重建及实际结果支持当前归因，保留这个观测缺项。excluded_pathset_changed=true与projectable分类照原件保留，不声称所有排除路径从未变化。未观察到hidden/gold/未来Git答案或联网读；不能排除模型先验记忆。

## 作者复核与当前接续

[最新作者MD](../tasks/9b5494e2/probe_two_model_analysis_20261003.md) SHA `1d0f1b79b26d07649d9f834810c099846f7ea476c2993764822a9477dba64bda`；
[最新作者JSON](../tasks/9b5494e2/probe_two_model_analysis_20261003.json) SHA `64cee10244084e728762ba3d6dbfac5e0095d493292ec13739099ca310b7f8c7`。40项作者ref的SHA/size和40链接核对通过；决定性修法、七维、数值与原件一致。作者初稿actor时戳遗漏经本审查指出后已在未封修订中补187.608427；当前重复采样政策也已纠正为v2覆盖优先/复采暂缓。旧sealed和ignored原索引没有回写。

本报告直接核55项证据引用SHA/size；Qwen191选中成员/71,270,833B的全体运输完整性按原mechanical receipt/sync范围复用，不冒称本轮重验191或Coder390成员。旧Coder JSON SHA `3c9948f5206676d83f85f3fb2cf839812c2f45fe3aa6013cbe17a03c06198146`，旧CPU JSON SHA `9f43232b76507f893c986e510739cc0183b57c9e3a2ce04d6bd7f123896e7466`；完整引用与事件绑定见[审查JSON](orange9b_two_model_semantic_behavior_review_20261003.json)。

两臂首轮执行与当前题级分析均已齐；本审查未改request/ACK/active，题主据当前独立报告另存核收。作者JSON独立核查=false是生成时快照，保留原件；当前独立完成由本报告与后续接收收据承接。有效v2明确ordinary_repeat_dispatch_allowed=false、Orange22 a2/a3 deferred，不把暂缓复采当在途或当前必做。本结论只核Orange9b，不核整包关闭、退租、训练或留出资格。

