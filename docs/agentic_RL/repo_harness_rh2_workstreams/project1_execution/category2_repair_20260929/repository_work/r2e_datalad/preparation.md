# DataLad 6b6f：当前处理入口

2026-10-03。负责人 `R2E | DataLad 题目修订`（线程 `01a0fd64-754d-7a90-8e97-2ae0f2907bb7`）。本包一题：`r2e_gym_subset::datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`。

**本题088修订、CPU对照、双模型首轮及题主／独立验收已完成。** CPU的noop=0、C-A=1、gold=0，各一次。Qwen3.6和Coder均正常完成、raw=0、17键匹配16，修好原例但各自引入转义冒号本地路径回归。七维轨迹／效率分析与非作者关键原件复核完成，未发现新增材料阻断。双模型执行回执已核收ack并清活动指针，当前没有本题CPU／GPU待运行或补评分依赖。

当前用途限固定版本基座诊断。CPU replay和两臂GPU baseline的环境包血缘字段仍为null，冻结contract把该既有缺口列为formal gate blocker；本次材料／诊断验收不授完整formal、训练、留出或一般模型比较资格。按最新覆盖优先规则，普通追加采样暂缓，不机械要求本题每模型三次；单次稳定性仍未知。

## 修了什么，怎样验收

原题要求含下划线的SSH隐式URL正确拆分scheme、hostname和path。065处理了合理解C-A误拒、用对象相等绕过解析和仅特判题面示例三类问题；其原七组CPU成绩和真实CC公开检查已验。GPU准入复核随后确认，065仍放过gold的两个已有公开行为回归：绝对本地路径误判SSH、crawler模板query抛异常。

088仅在私有test_1.py补这两个已公开读者列为K7/K8、且公开调用方实际依赖的行为断言；公开题面、开发说明、runner、其它hidden文件和17键expected不变。C-A是有效正对照，gold成为已知回归负对照。固定FAILED的`~`编码兼容项继续保留，yield XFAIL仍不产评分键。

| 当前088对照 | raw reward | 17键状态匹配 | 实际依据 |
| --- | ---: | ---: | --- |
| noop | 0 | 15/17 | 原例字段与URL识别失败 |
| C-A | 1 | 17/17 | 新旧约束均吻合 |
| gold | 0 | 15/17 | 新query ValueError和绝对路径scheme断言真实失败 |

[CPU验收报告](followup_k7_k8/cpu_acceptance_20261003.md)给出原日志、ledger、构建、原FrozenPatch及清理索引；[非作者增量报告](followup_k7_k8/independent_review_20261003.md)直接重建相同结果与工件身份，已接触私有材料，不是fresh公开盲审。两层driver／slot均正常结束，没有以infra当0分，也没有自动重评。新分只属于088；旧四个负例仅复用于未变机制，见[验收矩阵](followup_k7_k8/acceptance_matrix.json)。

## 已收到的真实模型结果

| 模型首轮各一次 | 实际成绩 | 决定性回归 |
| --- | --- | --- |
| Qwen3.6-35B-A3B | completed，raw0，16/17状态匹配 | 转义冒号也选SSH，host空，字符串重建断言失败 |
| Qwen3-Coder-30B-A3B-Instruct | completed，raw0，16/17状态匹配 | 转义冒号进入新elif但拆不成两段，漏设本地默认scheme，字段断言失败 |

两臂都在旧有转义case失败，不是088新两项触发，也不是infra／截断；固定`~`FAILED与expected吻合。088 query增量实际通过，同函数较后的绝对路径断言未执行，不据静态条件填动态PASS或FAIL。每模型正常完成1/1、raw成功0/1、完整样本语义正确0/1；指定模型覆盖2/2，仍是同一题，不当两个独立题。

[首轮成对报告](model_probe_reviews/pair_first_round_analysis_20261003.md)给出两种修法、具体定位／工具／验证差异、token／时间与限制，并链接两份完整题主分析和两份独立核查。题主核Qwen80成员、Coder固定snapshot492成员（含接续身份），保留原候选和全部失败。当前没有需改材料或重跑求通过的问题；未建立重复稳定性，不外推来源整体或一般模型排序。

## 固定版本与公开条件

实际R7发布 `cat2-cpu-r2e088-swe12-git-20261003-v1`，registry v19／pins v20，manifest `f9dfcd16…`，本机和CPU-c均核905成员及可信48 R2E／216 SWE读回。有效隐藏全文SHA `7649b82f…`、私有树 `2a62382c…`。

CPU-c新镜像 `sha256:6cb609c6ef96764ae05e502b535a786aa30e45d594f971f604c881c1cbd2317a`，配方ID `r2e_derive_v1+material_v2+sysconfig_v1`。配方摘要包含新材料而更新为 `0385a505…`；prepared环境包更新为 `677b5a1a…`。新baseline重算为 `4522e693…`，只绑定新实际镜像／public／head；environment_package_digest在baseline内实际为空，不能伪填新env或改绑旧工件。

构建原完整性清单证实源码与依赖未变，公开row／1203字符prompt和中性说明未变。因此复用065真实CC＋CPU桩的公开命令、身份预检及题面交付证据；它不是模型成绩。两模型实际首HTTP请求均逐字核原题面＋批准说明。两臂实际GPU镜像为`sha256:c5d390400a668256e8946daeefe9758a9064f64d518418727cdb013a907ec346`，baseline为`ee60bf13…`、246项，环境字段仍null；不能以CPU镜像或prepared环境包冒充已绑定。运行接续代码分别为Qwen code_v4、Coder code_v8，单次差异不能用于稳定效率排名；新作业未沿用旧绝对路径或改写旧历史。

## 交接和当前安排

按[三方工作流](../../coordination_workflow_20261003.md)和[总账工具](../../task_board_usage_20261003.md)，题主维护本题progress并端到端分析模型结果；公共发布/CPU环境归“负责处理分类二的明确问题”，GPU链路/队列归“负责处理第一类的模型探针”。先工具登记，再发请求ID＋总账路径，真实发送成功后记notice；普通进度不经总协调转发。

1. 旧请求 `r2e-datalad-6b6f-r065-20261003-v1` 已confirm-cancel，题主核无在途/未启动模型及回执SHA，完成ack并清指针。旧065输入与原结果保持原样。
2. [088固定请求](probe_request_r088.json)已用新ID `r2e-datalad-6b6f-r088-20261003-v1` 工具submit并完成定向通知，输入SHA `c8c879cf…`，仅申请Qwen3-Coder-30B-A3B-Instruct、Qwen3.6-35B-A3B各一次，沿用统一probe-wide-v1。实际GPU代码／镜像／预算和准入由执行者核定，CPU镜像ID不等于GPU已存在。
3. 两臂完整轨迹、原候选、逐键评分、题面／brief、预算／终止和清理均已核；题主分析成功的局部修复与失败的回归，非作者决定性核查通过。成对执行回执SHA `2b7911d2…`绑定原请求和两臂safe_closed；总账ack后请求revision5，清活动指针后progress revision9。ack仅核收执行交付，不是候选通过或训练准入。

按最新[覆盖优先标准](../../overnight_watch_20261003.md)，已就绪未测题与缺失另一模型首轮优先，未开始的普通追加采样暂缓。DataLad不在当前窄校准预案中，本题没有追加请求。若跨题分析提出具体校准问题再安排，不自动恢复旧每模型三次、多数修好后全量重复或退租流程。旧Qwen单臂报告保留写作时的“Coder未到／重复待接续”，由本入口及成对报告更新现状。

每条轨迹的根因／修法、定位／纠错、工具／并行、验证、效率和终止均已引用实际步骤。无多工具重叠及支持核验的维度记不可判断；环境准备与模型求解分别统计。不把截断／infra当能力失败，不为通过无限重跑。[results.json](results.json)保留当前状态和逐版本事实。

## 资源与保留边界

新build c3及matrix c1已正常结束，CPU原件完整回收到本地并核归档SHA；两模型及grader／gateway已安全结束。当前没有本题CPU作业、补评、GPUsolve或已授权追加采样依赖；若新证据暴露题级缺陷再定向复验。资源动作服从最新用户安排，本线程不修改control/setup、自行退租或恢复已停止的自动销毁流程。

同仓另外四题初态含本修复、重复采样／整仓划分、固定FAILED兼容项及完整formal gate限制继续保留。当前是明示版本的自建诊断题，不自动取得训练／留出资格。旧[065 CPU验收](cpu_acceptance_20261003.md)、[旧非作者报告](cpu_result_review_20261003.md)、[旧探针输入](probe_request.json)及[暂停断点](pause_checkpoint_20261003.md)均保留原件；历史阶段数不与当前新分相加。
