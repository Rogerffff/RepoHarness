# Orange9b54 R9 诊断 CPU 独立结果审查

日期：2026-10-03。角色：题主安排的非作者结果核查 subagent。只读已回收原件，未运行 CPU、Docker、候选、模型或新测试，未改共享文件及旧封存报告。

当前固定 R9 的题级诊断 CPU 验收通过，独立结果核查完成，可以据此准备具体 probe 请求；必修项为空。依据是完整十方正式矩阵与新公开 base-only CC 的实际开发入口证据。该结论不批准或派发 GPU，不是模型能力或训练资格结论。结构化事实、逐方状态和完整原件 SHA 见[同名 JSON](orange9b_r9_cpu_review_20261003.json)。

## 固定身份与证据完整性

材料为020092，release为`cat2-cpu-r2e089092-swe13-git-20261003-v1`；base commit为`43f086f0bacccd69e514788ae55e7f7df2285937`。实际镜像为`08470256e1bdb8e6952a77280695ca7bdb89800d3409eca7cc0a24aa5b96d4d2`，含sysconfig的完整recipe为`050316e44910d53ea3ded25e5a510a01c43e1ed60e1034270385ff9dcbe7fff1`，base recipe为`7e1710…`。prepared replay manifest `25b300…`与host grading `4632b7…`在实际CC attempt中再次读得，与本次矩阵入口相符。

原件父目录为`runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003`：

| 原件 | 逐SHA/大小核对 | tar SHA | manifest SHA |
| --- | --- | --- | --- |
| `r9_9b_matrix_complete_v1` | 242文件，无差异 | `d410ffc79ccbb3550ca936ed7772a28839a5f3633ae08cedc21dcc0d0749ace4` | `267413b4249686826e58ddb65cb2f131f3a03f7164c15774ed92f9aac1091061` |
| `r9_9b_actor_complete_v1` | 53文件，无差异 | `adb4abafd2a8541a38f36eb3cfd1cab58c5b85d727e0583a45ecae531cbf6ac6` | `8ca25d59da6f11148a43d0d353b6f0bc57454696aa568d662e08e2715276bf5f` |

作者检查只作索引，结论来自原ledger、eval log、HTTP、trajectory、冻结工件及资源快照。新作者初收据`cpu_actor_result_20261003.json`的SHA为`8b8d32490e1606e45a0ef5557e0a1cafeaa21fc64b3b7586f619c474c00e18bd`，其决定性结果与本轮独立原件核对一致；生成时independent=false保留，不回写。

[旧概率关系复用核查](orange9b_probability_reuse_review_20261003.md)与[公开brief事实窄核](orange4014_9b_public_briefs_review_20261003.md)按原封存SHA复用。旧020/env_v2/image481eb85概率校准支持已核关系依据，不能替代本次020092/sysconfig矩阵或新公开CC。原release binding中的准备阶段qualification=false快照保留；当前验收以本报告实际结果字段为准。矩阵ledger中的grading revision/materials identity/derived recipe为null，具体身份依据来自固定release、prepared与bound inputs/overlay，不冒称这些null字段已提供完整身份。

## 十方正式结果与目标行为

| 控制 | reward | 预期状态匹配 | 原件中的决定性结果 |
| --- | --- | --- | --- |
| noop | 0 | 11/13 | 143：L1实际fit被lbfgs拒绝；另原probability在62失败 |
| gold | 1 | 13/13 | 全部预期状态匹配 |
| V1 | 1 | 13/13 | 全部预期状态匹配 |
| V3 | 1 | 13/13 | 全部预期状态匹配 |
| V4 | 1 | 13/13 | 全部预期状态匹配 |
| V5 | 1 | 13/13 | 全部预期状态匹配 |
| W1 | 0 | 12/13 | 144：显式l1被静默改为l2 |
| V7 | 0 | 10/13 | 151：默认solver变liblinear；另两个旧FAILED变PASSED |
| P1 | 0 | 12/13 | 158：默认无参repr未保留 |
| G1 | 0 | 12/13 | 173：默认与显式multinomial概率不符 |

十方job及每方正式CLI均结束0，matrix complete、stop reason为null；真实eval log SHA与ledger相符。每方13个评分键齐全，无missing、unexpected或段外解析状态。成功条件是逐键匹配13个预期状态，其中`test_learner_scorer`、`test_learner_scorer_multiclass`本来就是`FAILED`。五个正例原pytest为11 passed、2 failed、1 skipped，pytest rc仍是1；不能写全测试通过，也不能据此判infra失败。

原pytest collected14；第29行既有normalization skip对应`test_LogisticRegressionNormalization`，未进入13个评分键。它与已评分的`test_LogisticRegressionNormalization_todo`不同。V7两个旧scorer实际变为PASSED，形成额外mismatch；其主要失败明确在默认solver第151行，尾部skip摘要的29行不是失败位置。

负例确实到达对应目标：noop在143进行L1 fit；W1在144核实际penalty；V7在151核默认solver；P1在158核默认repr；G1在173核新的概率关系。G1此前L1、solver、penalty、repr、none检查已过；新关系实际450/450概率不符，日志最大绝对差0.38716698，容差rtol1e-5/atol1e-7。更高精度0.38716698009532013来自旧校准原件，不冒称新trace精度。

五个合理正例均正式通过，涵盖无auto sentinel、saga支持L1、fit时选择与映射表等方式，支持本轮评分对这组实现的语义宽容性；不据有限控制宣称任意实现都被覆盖。

九份payload SHA与固定plan/bound inputs一致，实际git_apply成功；noop为空应用。各方共有1531项baseline，canonical digest为`df404e5…`；冻结/投影digest与内容SHA一致。独立在内存反向恢复每份补丁到base模块`ad54fe8…`，再正向逐字得到Frozen源码。每份只改`Orange/classification/logistic_regression.py`，无测试或fixture改动，excluded pathset未变，runner前后SHA一致。实际grader直接观测仅`Orange/__init__.py`及版本/runner，没有logistic模块加载SHA；原生字节、fresh正式结果与目标对照支持生效，但不改写为直接加载hash实测。

每方config只调整setup_seconds1200；probe audit记录300→1200、test1800；候选阶段900、grading deadline3600、cleanup120分别保留。每方ledger为removed=true/rm:ok，正式footer无open容器、cleanup failures或regrade。审查未仅凭总分或退出0放行。

## 新公开 base-only CC

job `orange-9b5494e2-r9-actor-c-20261003-v1`正常结束0；实际CC ran/completed、harness0，trajectory46行，四次Bash与四份完整tool_result，终止end_turn。命令明确`--no-grade`，没有新增评分或修题步骤；固定stub不构成模型成绩。

首HTTP中的任务prompt与`prompt.txt`逐字相同。完整prompt SHA为`2d087618457963804c3b4f5e687c12dbcd3f3e82bcbaff582da0dd492f4b079c`；原ISSUE后缀SHA为`687b44de0c1c54495a92186594e86d44c3f4b1288bfdac1a6a49650e1d1ab4a8`，与R9题面绑定一致。neutral brief未实际交付，静态窄核不等于HTTP交付验收。

| 步骤 | tool use / result事件行 | 工具ID | 实际内部RC与结果 |
| --- | --- | --- | --- |
| r2e_preflight | 6 / 10 | `toolu_fec100a157e718f4` | 0；interpreter、hidden tests、git history均ok |
| public_identity | 15 / 19 | `toolu_9cf9c56620bec4f7` | 0；uid54321、Python3.7.9、SciPy1.5.4、sklearn0.22.2.post1，Orange及logistic模块均在/testbed |
| public_default_regression | 24 / 28 | `toolu_787efd3a5a6e91c1` | 1；原默认test_LogisticRegression通过，test_probability失败；1 failed/1 passed |
| public_l1_issue | 33 / 37 | `toolu_b9617b75fc27e0a9` | 1；构造l1 learner成功，完整iris实际fit触发题面ValueError |

`test_probability`实际使用penalty=l1，在iris[:100]拟合，失败于公开源码62行；不是默认概率测试。内部RC从完整tool_result中的RH2_STEP_RC读取。工具层均is_error=false、interrupted=false，因为尾部echo成功；原件没有独立工具Exit code字段，不能混写为工具外层RC1，也不能将内部检查1写成通过。旧step ID public_default_regression只作标识，按实际内容判断。

新CC的baseline tar中1525个常规文件内容/规范可执行位及6个链接目标逐项吻合，共1531项。logistic模块SHA为`ad54fe8199ca3c91f34285fbb145c6e3f473261fa11d8a1219a150ef8800830a`，公开test文件SHA为`8eb5fca4f4adf5535a548037d21f46f7d43838c852f06596fd25aa821c53dc91`。identity直接输出模块路径，未直接输出模块SHA；base归档与空投影提供间接字节绑定。FrozenPatch canonical digest为`a031886…`、0entry且projectable，但excluded_pathset_changed/runtime_private_pathset_changed=true，不能称整个工作区零变化。pip freeze前后逐字相等；NumPy1.17.5来自pip记录，未冒称本次identity直接打印NumPy运行版本。

prelaunch、activation及公开CC preflight均通过，实际解释器为/testbed/.venv/bin/python。quiescence确认agent进程零与工作区digest双读稳定；gateway revoke/drain、active0；main/relay/network清理无失败，endpoints停止RC为0/0，最后容器及网络residual为空。

## 资源、剩余边界与当前用途

矩阵97个时间快照覆盖20个容器，即十方各自candidate及fresh grader。实际HostConfig/cgroup为2CPU、4GiB、pids512、swap0、network none、无bind。唯一非零状态是P1 candidate在22:38:37 removing/PID0/ExitCode137/OOMKilled=false，cgroup已不可读；发生在candidate移除阶段，后续grader原日志完整、正式评分为预期0，ledger rm:ok/CLI清理成功。不能称全程exit0、全程OOM0，或将137直接定为OOM。

新CC的7个有限快照覆盖main与relay：main实际2CPU/4GiB/512/swap0；relay256MiB/64/swap0，cpu.max为max100000，relay没有2CPU配额。main经隔离relay连接端点，prelaunch外部DNS、forbidden目标及直接upstream均拒绝。样本均running/ExitCode0/OOMKilled=false；有限采样不构成连续资源证明，清理另据实际结束记录。

必修项：无。现有材料足以封固定R9题级诊断CPU验收。必须保留既有expected FAILED与unscored skip、V7差异方向、有限资源与P1清理137、矩阵缺直接模块加载SHA，以及新公开CC无修题/无评分/固定stub、neutral brief未实际HTTP交付的边界。GPU与真实模型表现须由随后实际请求和原件判断；训练与holdout资格不在本轮。
