# MONAI3715 非作者 CPU 结果核查

2026-10-03 / Codex（GPT-6.1 Sol / high，非材料与运行脚本作者）。

**结论：本次限定 CPU 验收成立，未发现阻断提交探索性探针的题级问题。** 五个固定对照的正式原始 reward 为 **0／1／0／0／1**，逐参考结果和真实失败原因相符。公开开发能力、材料运输、两层清理与外层退出均有原件支持。这里不授予训练或留出评测资格，不证明模型求解能力、RL 信号、环境长期稳定性或平台安全全验收。评分容器实际 ID／HostConfig 和资源峰值观测仍有归档边界，详见第 5 节。

## 1. 上下文、授权与方法

按仓库 `AGENTS.md`、[审查标准](../../../../../review-standards.md)、[协作协议](../../../../../collaboration-protocol.md)及[当前剩余工作流程](../../../remaining_workflow_20261002.md)所述非作者核查执行。本次接续 [非作者静态材料窄核](non_author_material_review_20261003.md)，不重复从头盲审。核查者已经接触公开题面、base 源码、作者修订单、私有有效测试、gold／两个错修／合理替代、旧静态意见，以及题主发送的阶段状态和 owner 检查摘要；**不是 fresh 公开读者盲审，也不是独立重新运行实验**。原公开材料没有变动，因此无新公开读者要求。

本人只读本地原件，使用标准库核 JSON、SHA256、Base64 内容及日志；没有 SSH、Docker、安装、项目测试、付费模型、子 agent 或共享实现修改。仅新增本报告。对作者检查摘要的接受建立在下面的原件核对上，未把摘要当作运行证据。

证据根：[CPU-C 原件目录](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003)。固定作业如下：

- actor：`monai-3715-actor-20261003-1bc7e2d2`；prepared：`monai-release5-prepared-20261003-3537d9d8`。
- image：`monai3715-image-20261003-573e4e35`；正式矩阵：`monai-3715-formal-20261003-e9716177`。
- 正式矩阵 [campaign 原件](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/campaign.json) SHA256：`a343789e35821a76b9c9065642ea35b4626c8c1de204cf44bcac0d786ad60fa3`。

## 2. 固定身份与公开输入

release5 manifest SHA256 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。已对本地 release manifest 及 `release5_readonly/rh2/` 七份实际消费源码核 SHA／字节，全部匹配，包括 `devcheck.py`、`acceptance_startup_2.py`、`replay_with_cpu_budget_v2.py`、`scripts/replay_grade.py`、评分 manager 和 replay consumer。launcher 记录其远端验证 837 文件；本人核了以上七份源码，不把该记录称为本人逐份核完 837 文件。

输入包 manifest 为 `902e402a20724488b95df81d2d4ffbb198d8609f7bbccbd0db50b7a43673db77`，本人逐项核 174 份文件 SHA／字节全部一致。prepared 五件原件摘要均匹配 owner 清单；prepared manifest 为 `18da4cd12d7813fbef7348e300a94fefde0be18603298640127a11e7685df0cf`，私有 grading JSONL 为 `8e78e1bc655e7464ab93c587776289d0d939225378730baa32400cf2886c5a96`。actor／campaign 同指该 prepared job 和 replay summary，后者 SHA 为 `3058de8fffaafe21f7fe76ecf126c731d83748b9d8b595201a822fe166c0539d`。

三题 prepared public 与输入 source public 逐字段完全一致；2446／6975 grading 不变，本次只验 3715。3715 变化仅 `schema_id`、`revision`、`test_patch`、`fail_to_pass`。有效测试补丁为 `1e38b2d6a5dcfa2e2de5622c4db601a446da4e68ef1bd642d9c8100c3415565e`，与本地及输入包有效材料一致；原 F2P／P2P 保留，新增一条 F2P。五行 grading revision、diagnostics 和 prepared 的版本／分区一致：

- 修订：`monai3715-string-modes-forward-cpu-v1`；registry：`9fd5f38bbd3f0d09027d2270a6f3f3c1af1bae84da9c6b7c9b553bbafd7a9cb0`。
- grading digest：`201888c737af106b752d3fb3d3b92865118044d226e164313e3ec7307c6cbaba`；environment digest：`b837970c8f26bfd9475c19abe4b4cf3682315524a0851b1eb4e6ea27dee36222`。
- public digest：`06657b6749eed7e3f97e7968de3383f6a187d52b9f9dfc879f83115da23ada06`；materials identity：`a88992c71eed8c4b9ac3482294a198ba253b1467e6963e1078cd98f9c48abd03`，已按冻结源码的 grading digest／parser／binding 公式独立重算一致。

公开交付按题主本次安排为 `public_delivery.mode=unchanged`，使用原问题文本与已有 `public_hints`；`public/monai3715_solver_notes.md` 是未交付的可选草稿，不算新增公开输入。必须区分：本次 actor 首个真实请求使用通用 `Devcheck run: execute exactly the tool calls you are given, then stop.`，**没有把原问题／public_hints 交付给这个桩 actor**。首请求原件：[messages_000.json](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-actor-20261003-1bc7e2d2/stub/requests/messages_000.json)，SHA256 `4886e03428db9548947c1b0bc6fb6e22eec25ca1677be9d64f2e61142524618f`；后续请求未用于补装缺席题面。它证明公开命令的执行能力；prepared 内容一致证明未改变公开材料。后续探针仍应保存原题面／hints 的实际消息交付证据，不能用此次桩请求替代。

## 3. 真实公开 actor 的 CPU 开发能力

[actor attempt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-actor-20261003-1bc7e2d2/attempt.json) 与六份原始 capture、完整 trajectory／stub 请求对应。24 份 owner 清单原件 SHA 独立匹配；六条清单与 attempt 命令逐元素一致。完整 trajectory 为 49,514 字节、76 个事件，六个 Bash 调用逐 tool ID 关联六个结果，七个请求与 message_start 相符，最终 `success`、harness RC0、日志完整且 stderr 空。

| 命令 | 实际 RC | 原始行为 |
| --- | --- | --- |
| identity | 0 | UID 54321；Python `/opt/miniconda3/envs/testbed/bin/python`；MONAI `/testbed/monai/__init__.py`；HEAD `d36b835b226ab95ffae5780629a5304d8df5883e`；工作树干净、源码目录可写；CUDA false |
| enum_train | 0 | forward training／grad_enabled 为 true／true；prediction `[[2.0,4.0]]`；requires_grad true；输入梯度 `[[2.0,2.0]]` |
| enum_eval | 0 | forward false／false；相同预测值；requires_grad false |
| string_train | 1 | Evaluator 构造处 `ValueError: unsupported mode: train`，与公开 bug 一致 |
| string_eval | 1 | Evaluator 构造处 `ValueError: unsupported mode: eval` |
| public_existing | 0 | 未注入隐藏测试的原公开模块两个节点 PASSED；无 skip，17 warnings |

依赖是 numpy 1.24.4、torch 1.13.1+cu117、ignite 0.4.8，CUDA false；没有把带 cu117 的 wheel 当 GPU 执行。独立 identity 镜像记录的相关源码 SHA 与已核 base 相符。六份 capture 最大只有 3,327 字节，低于 200,000 字节采集限额；tool_result 对公开 pytest 输出只带 1,500 字节尾部，完整 capture 已单独核读，未从尾部推定全日志。

原 Runner 的 `interpreter_in_tool_result=false` 与 `bashenv_denied_for_agent=false` 保留。冻结源码分别搜索 `RH2_SYS_EXECUTABLE=` 和 `RH2_BASHENV_WRITE=DENIED`；本清单打印 `PY_CHECK`、未安排写 BASH_ENV 探针。直接 identity 与 activation_check 足以核本题解释器，不足以核销 BASH_ENV 保护或平台全安全边界。

actor inspect 实录 2 CPU／4 GiB；effective profile 的 PID512、tmp tmpfs1 GiB、home tmpfs256 MiB、可写层8 GiB是配置记录，未据此声称所有上限均由独立 HostConfig 证明。`cpu_actor_bounded.py` SHA `f5afc1428f12b10d6fbb042e5a9d954c91216ed402d78385c5c43b8c0c342e6f` 匹配冻结 shim；源码与 bounded 请求证据确认只给 root image_facts 探针加资源参数，原非 root actor 沿用正式 Runner 装配。

actor 收尾原件记 git status 0 行、agent 进程0、harness／launcher marker 不存在；新文件310项为记录事实，不声称零写入。container rm／stub RC0、relay／network 清理无失败，按 attempt 标签再查无容器／网络残留。最新 [四作业外层完成记录](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/outer_completions_latest-d8beb14d.json) 的 actor／prepared／image／tag 全为 finished、cpu_slot RC0、launcher exit RC0，与内部完成时间一致。launcher_log 只是单行 jobs 目录打印，未用于替代内部运行日志。

## 4. 五行正式评分：逐参考、真实执行和冻结投影

参考名称如下，表中分别列出原 F2P、新 F2P、原 P2P，三键每行都实际出现，**无 missing／skipped／unaccounted**。日志摘要逐字与 ledger／diagnostics 分区对应，15 个题目×参考结果全部核对。

- 原 F2P：`test_content`。
- 新 F2P：`test_evaluator_string_modes_forward_and_restore_cpu`。
- 原 P2P：`test_empty_data`；该节点通过仍是空数据直接返回的原回归，不能当 train 运行证据。

| 候选 | 原 F2P | 新 F2P | 原 P2P | reward | test RC | 真实依据与原件 |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 失败 | 失败 | 通过 | 0 | 1 | 字符串 eval／train 在构造处 unsupported mode；[账本](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/noop/ledger.jsonl)／[完整日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/noop/eval_logs/evallog_replay-monai-3715-formal_bdc61446.eval.log) |
| gold | 通过 | 通过 | 通过 | 1 | 0 | 三键通过；16 个 mode／进入状态子场景全部完成；[账本](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/gold/ledger.jsonl)／[完整日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/gold/eval_logs/evallog_replay-monai-3715-formal_7fc80d14.eval.log) |
| eval_only | 通过 | 失败 | 通过 | 0 | 1 | 字符串 train 构造处 unsupported mode；[账本](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/eval_only/ledger.jsonl)／[完整日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/eval_only/eval_logs/evallog_replay-monai-3715-formal_93eed3ee.eval.log) |
| always_eval | 通过 | 失败 | 通过 | 0 | 1 | 真实 forward 为 (False, False)，应为 (True, True)；[账本](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/always_eval/ledger.jsonl)／[完整日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/always_eval/eval_logs/evallog_replay-monai-3715-formal_a662876f.eval.log) |
| alternative_local_mode | 通过 | 通过 | 通过 | 1 | 0 | 三键通过；不同局部变量规范化路线被接受；[账本](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/alternative_local_mode/ledger.jsonl)／[完整日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177/alternative_local_mode/eval_logs/evallog_replay-monai-3715-formal_1dbb1647.eval.log) |

新增节点经 CPU 非空单批 `SupervisedEvaluator.run()`，覆字符串／枚举 train/eval 和进入前模型／梯度状态，共16个子场景；真实 forward 记录、退出恢复、预测 requires_grad 和输入导数均有断言。gold／替代无失败／skip，使这16个子场景完整跑通；没有每子场景独立事件日志，不伪称逐场景观测另行归档。两份错修新增失败分别发生于构造的 train 和真实 forward 状态，证实新增键不是仅靠构造成功。合理替代用 `forward_mode` 局部变量规范化，未绑定 gold 的变量名或上下文函数身份。

本人直接读五份完整 eval.log，字节依次为 73,684／66,033／70,798／68,795／66,278；其 SHA 全与 ledger 相符、`partial=false`。每份只有一对真实测试 Start／End 输出标记；原件含依赖安装与测试命令，不是只有摘要。`RH2_SETUP_APPLY_RC=0`、测试恢复／保护成功；安装真的执行 `python -m pip install types-pkg-resources==0.1.3 pytest`、`pip install -r requirements-dev.txt` 和既定后续安装步骤，实际 `RH2_INSTALL_RC=0`，没有 ERR trap 失败记录，未跳安装。测试段 `RH2_TEST_RC` 为1／0／1／1／0，与表相符；外层 exec RC0不代替内层 pytest RC。负例的 ValueError／AssertionError 均是目标行为失败，不是依赖导入、collection、超时、OOM 或环境 infra 失败。

五行 FrozenPatch／baseline JSON 的 canonical digest 均独立重算匹配 projection 和 ledger；五份 baseline 逐字段完全相同，HEAD 与公开 base 一致。noop 无条目，baseline evaluator SHA 为 `97b99b4ef4a524ec976d5370de8ea5eb8cefc55830bd8fc79caa08693e5a60b4`。其它四行只投影 `monai/engines/evaluator.py`，operation modify、regular 100644，Base64 解码后的整文件 SHA 与 entry／controls applied_source_sha256 相符：

| 候选 | 解码源码 SHA256 |
| --- | --- |
| gold | `e340acf9daaceb37dea8b0f5c9eb05f84ea6278ac7ea071a28c2b330d61f2434` |
| eval_only | `0754c350b06613f2a3539f77f9f004a5f07739177c0ea54e3649e5ec87834397` |
| always_eval | `1b8b2d819f64e6e2fdb1e7525ca64c2dd551c08f1aec971badc69e2bdc06c333` |
| alternative_local_mode | `f48d6dd7c70e61f67c90cb1b0ffd5397b8a5d661a9cabd0cef93bfd26652a1e2` |

四份实际 candidate.patch 与固定 controls 字节／SHA一致；noop 是空 patch。stage 到达 projection、无 stage_error；全部 projectable，无忽略路径、unsupported shape、候选测试／fixture 修改或 excluded pathset 变化。已核静态原件对 controls 的应用结果作为语义依据，本轮未另外执行 git apply 或导入候选。

## 5. 命令、镜像、预算、资源及清理边界

编排脚本 SHA `f2651a7d32cc26438b23a1dc7be65bb39e8104a81708c4c88d7c883a7d819f8c` 与 frozen launcher／campaign 一致。五行共用 release5 direct replay，candidate prepare900s、整体评分3600s、cleanup120s、image pull1800s；四个非 noop 引用本次 noop qualification ledger。budget 原件逐份为 env reset300→900s、测试1800s不变；冻结预算 wrapper 仅替换 `env_reset_timeout_seconds`，没有改测试／奖励／保护或生产文件。该变更针对 prefix chown 准备耗时，未据此宣称效率根因已修。

image/tag/campaign 启动前 actual image ID 是 `6cbdf6b5eefbe27e97db5839aa8586584cc57f20759fb6c408690fddc8202e38`；固定 vendor manifest 为 `503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8`。五行 ledger 保留 `image_id_actual=null`、`image_local_build=false`、原 public tag、expected／identity 为上述manifest，不能把 campaign actual ID回填为每行事实。冻结 manager 的 `_verify_image_digest` 启动后 inspect **运行容器.Image**，再按该实际ID查 RepoDigests；非 local_build 不匹配即 infra，因此此处不是仅按 mutable tag 信任身份。正常评分结合已核代码与无 infra，足以接受本批固定manifest身份，但**每行评分容器的实际 ID 原始 inspect 未单独归档**。

正式五行 policy 为2 CPU／4 GiB／PID512、网络 deny_all、grader UID54322，实际 HostConfig 与 `resource_facts` 未归档；只能核配置来源，不能宣称逐行实际资源上限全证。五行 `mem_peak_mb=4096` 保留原值；冻结源码通过 cgroup `memory.peak`／v1回退读取，而本包没有原始读取输出或 cgroup归属证据，故**真实进程／容器峰值与资源余量未由这些数字证明**，也不把它自动改写为OOM。运行无实际OOM／超时迹象，本报告不因此要求无目的重跑。

两层清理分别核：每行 ledger 的候选容器 `removed=true`／`rm:ok`；完整 runner.log 的 manager_close 每行 created1／removed1、open为空、cleanup failures为空、final exit0；campaign按本行 run_id 查询 RC0、无容器残留。五份 runner.log 摘要与campaign SHA均匹配，实际 final JSON与campaign副本完全相同。最新 [正式外层完成记录](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-3715-formal-20261003-e9716177.snapshot-6d399d4a.json) 为 finished／cpu_slot returncode0／launcher exit0，时间在五行完成后。无强杀／cleanup-unconfirmed 标志或需要补核的悬挂行。

## 6. 审查覆盖与后续用途

| 维度 | 本次处理 |
| --- | --- |
| A／E／G 正确性、有效测试、真实路径 | 真实 actor／Evaluator.run、目标负例、完整正式参考与评分段、FrozenPatch运输已核；并发只顺序五行，不外推并发正确性 |
| B／C 训练分布与挡板 | 本轮只收口探索性CPU证据；不改变准入、不解除训练挡板，训练分布未在本轮评估 |
| D／F／H 所有权、决定一致性、事实源 | 固定输入／发布版本／prepared／ledger一致；保留null／false字段及原始reward，不用摘要改原件 |
| I 分期止损 | 当前可提交探索性探针；实测模型候选与评分再由题主审计；不因CPU验收提前给训练用途 |
| J／K 代码质量与演进成本 | 未改共用实现；窄核两份冻结shim消费范围，不作完整生产代码质量审查 |
| L 资源／活性 | 有界命令预算、正常退出与清理已核；峰值／实际HostConfig／长期稳定性证据不足明确保留 |
| M 可观测性／可诊断性 | 原始capture/log与摘要对账、角色上下文披露、非zero目标异常区分与逐分区结果已核；平台安全与模型求解未扩大宣称 |
| N 外部兼容性／依赖漂移 | 固定CC 2.1.205包摘要、实际版本与本题Python依赖／镜像身份已核；未升级依赖，不外推其它版本兼容性 |

当前未发现必须先修的材料误拒／漏判或运行阻断。公开输入保持unchanged后可按既有约定提交统一探索性探针；题主仍负责保存实际solver输入、分析回传候选、发现实际控制篡改时分列raw reward与可信语义。CPU五行通过不等于该题后训练可用或留出评测成立。本轮没有修正原reward、热改正式版本、覆盖历史失败或新增授权闸门。
