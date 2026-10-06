# R2E orange3：四题当前入口

更新：2026-10-04。本线程“R2E | orange3 题目修订”（`01a0fd63-ef54-7691-87db-e5124474f714`）持续负责四题的修订、CPU验收、探针提交、结果分析和后续修复。

**四题诊断CPU验收、两模型各一次首轮，以及作者轨迹分析和非作者语义核查均已完成。** 共8份有效首轮样本，7次原评分成功、1次有效模型漏修；没有因失败重试或为了成功补跑。当前没有已知CPU/GPU待执行步骤或活动请求。[本包当前收口](first_round_closeout_20261004.json)链接四题验收与最新采样政策。GPU v2覆盖优先已取代旧v1自动复采计划，Orange22 a2/a3明确暂缓；未来是否抽样复采由全批覆盖结果选择，暂缓计划不计为在途。

完整本包CPU-c归档已核1290文件，源复制前后一致；[历史CPU剩余依赖回执](cpu_retirement_dependency_20261003.json)保留原件，其生成时“GPU仍需”由上述当前收口接续。当前首轮完成不自动授予训练或留出资格，也不代表整机可退租；机器操作由资源负责线程按用户授权处理。[恢复检查点](resume_20261003.md)维护本包当前状态，旧证据不回写。

## 四题进度

| 题目 | 修订和验证 | 首轮结果、用途与剩余事项 |
| --- | --- | --- |
| [22e98f8f](tasks/22e98f8f/card.md) | 最终064/sysconfig材料、CPU真实CC与独立窄核通过，正确逆置换语义 | 两模型各1（23/23）、均正确；[作者分析](tasks/22e98f8f/probe_analysis_20261003.md)与[独立验收](tasks/22e98f8f/probe_first_round_acceptance_20261003.json)已完成、原请求ack。旧各补2次计划已被v2暂缓，[当前政策收据](tasks/22e98f8f/probe_repeat_deferred_receipt_20261004.json)已落账；没有当前必做复采，稳定性未知 |
| [4014f248](tasks/4014f248/card.md) | 089保留057断言并补小量级分箱；CPU八方、公开CC与独立验收通过 | Qwen1（27/27）正确，Coder0（26/27）有效漏修：返回compute points仍重复。[两模型分析](tasks/4014f248/probe_two_model_analysis_20261003.md)及[当前收据](tasks/4014f248/probe_first_round_owner_acceptance_20261003.json)已独立核、原请求ack/指针清。失败保留，不是验收过严，不重试；无材料必修项 |
| [50f6a758](tasks/50f6a758/card.md) | 090/091公开混合文件/匹配规则、fresh阅读、CPU八方/真实CC及独立验收完成 | 两模型各1（48/48）、一般未使用变量警告语义正确。[七维分析](tasks/50f6a758/probe_two_model_analysis_20261003.md)及[当前收据](tasks/50f6a758/probe_first_round_owner_acceptance_20261003.json)已独立核、原请求ack/指针清。Coder Qt自验中止、误读回退与最终夸大保留；无材料必修项 |
| [9b5494e2](tasks/9b5494e2/card.md) | 020/092、完整050316配方/084702镜像、CPU十方/真实公开CC及独立验收完成 | 两模型各1（13/13来源状态匹配）、L1条件换solver且保留默认行为；实际各11PASS/2既有expected FAILED/1skip、testRC1。[两模型七维分析](tasks/9b5494e2/probe_two_model_analysis_20261003.md)及[当前首轮收据](tasks/9b5494e2/probe_first_round_owner_acceptance_20261003.json)已独立核、原请求ack/指针清；Qwen确实重测原版两个scorer，但flaky声明无统计支持。无材料必修项 |

## 材料和检查边界

23／27／48／13键及既有expected映射均未改写。共享修订单、pins、ingest、环境批准摘要和公共源码不由本包修改；只使用共用维护者发布的不可变版本。历史证据原件保留。

- [本地材料检查](local_material_check.json)：三个完整新测试通过Python3.7语法解析、唯一替换与SHA核对，目标以外28／51／14个方法AST不变。方法数不能当正式测试通过数。
- [轻量行为检查](local_behavior_check.json)：4014为Cython数学转写；50f6只提取真实候选函数，使用数据描述、Qt、model及commit替身。它们不是Orange完整模块、actor或正式评分；该轻量脚本未拟合9b54。当前另有真实CPU三组概率校准，见[新收据](tasks/9b5494e2/probability_precheck_v2.json)；封存计划中的observed栏不回写；本轮50八方及独立结果核查均已完成，当前有效范围见单题CPU验收。
- [非作者材料核查](reviews/non_author_remaining_material_review_20261003.md)及[接收核对](independent_material_review_receipt.json)：9份材料SHA匹配，未发现静态阻断；没有运行CPU或作者探针。原生成时状态不回写，使用接收记录续接。
- [初轮完整性检查](verification.json)及两份准备脚本已完成本地语法、摘要与链接检查。[材料生成器](prepare_materials.py)绑定v11父摘要，公共父版本已推进后不得直接重跑覆盖；[行为检查脚本](local_behavior_probe.py)不是新评分器。

50f6 [公开包](tasks/50f6a758/public_reader_package/)、[阅读报告](tasks/50f6a758/public_reading.md)、原命令保持不变。[阅读接收记录](tasks/50f6a758/public_reading_receipt.json)核10文件SHA；actor命令副本仅支持警告正文的`text`关键字，不增加格式要求。原base-only剧本保留未运行；实际私有gold对照使用独立v3副本，事实见当前验收。

## 发布与CPU接续

本包固定在cpu-c，网关18196／桩18197，同包串行；所有Docker操作使用统一`cpu_slot.py`，每机2作业／1prepare。75表示未入槽，不是失败评分，不高频重试。原cpu-a输入及75回执保留。

22e98首轮使用 `cat2-cpu-r2e064065-swe5-20261003-v1`（material_v13／pins_v14），新题面SHA `f8701d3a…`已与首HTTP用户正文逐字核对，旧答案段不存在。原来源`public_hints`未随这次CPU的`spec.prompt`送出；GPU由统一入口交独立的[当前公开说明](tasks/22e98f8f/public_development_brief.md)，不会把来源元数据假称已交付。

[首轮CPU收据](tasks/22e98f8f/cpu_actor_v1_receipt.json)明确保留局限：新镜像`29d371…`使用未叠加sysconfig的配方，而历史noop/gold/DG使用 `r2e_derive_v1+sysconfig_v1`／`e2e17bf…`。该首轮证据保留；最终补建已恢复历史配方一致性，见[最终CPU证据](tasks/22e98f8f/cpu_acceptance.md)；桩用量／费用不是模型成绩。数值断言失败后字符串例未执行。

补建采用已部署第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228…`，新runtime_cpu_v2及已验builder限制/label/cleanup参数。第五版四个22e98任务面与首版逐行相同，recipe/sysconfig脚本相同；重新生成本机prepared路径，不热换旧作业，不重跑共用daemon smoke。第五版共用Git修复不代表另三题新草案已发布。详见[CPU记录](cpu_preparation.md)、[资源规则](../../cpu_resources_20261003.md)及[题级绑定](tasks/22e98f8f/cpu_release_binding.json)。

共用维护者已在R9解决两个发布接续缺口：4014以089完整保留057的断言；9b54新material登记最终组合配方050316…。旧020批准`512277…`只用于历史概率校准，不能冒称最终配方。正式runner复用共用入口，一题完成即提交，不等四题齐备。

grader准备预算沿历史有效`env_reset_timeout_seconds=1200`，最终consumer登记实际值；50本轮八方已实际核该值，22的CPU `--no-grade`未执行grader，而其两臂GPU正式评分已实际1200。模型和求解预算只引用统一探针的`probe-wide-v1`。这批工作不自动授予训练或留出资格。

依据：[分工](../../repository_work_packages_20261002.md)、[当前流程](../../remaining_workflow_20261002.md)、[旧库存](../../r2e/r2e_inventory.md)。旧库存的fresh未完成／G1旧S2判断以更晚证据接续，不改写历史原件。

9b54历史预校准首轮：原020＋env_v2＋sysconfig镜像完整性通过，但当时consumer拒绝未批准的完整配方摘要，CC和拟合未启动，异常及清理保存在[首轮收据](tasks/9b5494e2/probability_precheck_v1.json)。已通知公共维护者。另用原已批准完整env_v2配方／实际镜像481eb85完成base／gold／G1私有Python概率校准：base/gold最大差0，G1约0.387，原容差可保留；七步RC0、实际来源与最后G1原生工件绑定、45份原件及清理已核。未用新隐藏测试，不代替最终组合环境或正式十方评分。

模型结果分析遵循[轨迹分析要求](../../overnight_watch_20261003.md)，采样安排以GPU最新[覆盖优先v2](../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/stage2_repeat_plan_v2_coverage_first.json)为准。四题每模型各一次，首轮覆盖/原评分/语义/正常结束分列；单次不作稳定能力或模型排名。当前没有题级阻断或已知待执行CPU/GPU步骤。未来材料修复、选题复采或训练准入按新依据接续，旧计划和原分保留。
