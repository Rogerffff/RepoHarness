# conan-io__conan-11594 解封复核

结论：主审核心事实、历史delta和最有价值下一步与独立初判一致；在“限定版本下的静态开发候选”范围支持收口。没有新增已证gold回归或当前actor资格。

## 解封与证据边界

协调者明确 cross_review release 后才读本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，以及 RUN/history/本题/refs.json 所列两份旧记录。旧记录先核完整文件SHA256与refs相同，再读全文；没有沿旧记录链接打开stage1、其它题、聚合报告或控制面实现。下称A为L1_conan旧记录，B为conan_pilot旧记录。初判保留原文，后续解释只写本稿。

本次逐一核主审正文、附录命令/node表、结构化字段。用stdlib JSON按字段将主审附录中两次运行记录与原ledger选中行对照，全部对应字段一致；facts_ref的ledger路径/行号及conditions与本题run_refs原值一致，analysis_sha256也匹配。未执行项目/测试、安装、联网、容器或模型；未派发任务二。原件的历史pass仅按记录的grader版本、身份和选择器解释。

## 结构化记录复核（共同适用）

- checks均带真实`by=/root/e25_main_conan (private investigator)`；状态均在原允许枚举内，未用八方面替代40项编号。遗漏的40按约定是not_checked；没有以封存合规推导无漏检、误杀或抽样偏差。5/14及未核跨池范围没有升级为通过。
- issues全部有scope=static_review、proposed_action、evidence_refs和证据层次，未把建议当已执行。具体议题见下文。additional_exclusions和revision_refs均空，未继承旧清理测试目录的建议。
- 29=unknown，usage.actor_answer_exposure=unknown；授权私有审查所见gold、隐藏测试、旧记录在usage单列。它们不证明actor已泄漏或未泄漏。本review新增读取主审/公开读者/两旧记录，是审查侧暴露，禁止传给独立solver。
- 1/4/6/9/11/16–21/27的pass均需连同note中的“静态材料/计划范围/选中历史grader”限定阅读。尤其requirements已满足的历史安装不是任意干净环境可恢复证明；deny_all不是本轮actor网络配置；普通gold投影/setup成功不是恶意候选安全证明。3/8/10/26/31/33/34/36/38仍保留unknown或未验边界，未发现把未知actor实际身份伪装成已测值。
- disposition为needs_review/static_review、intended_use=development_diagnostic；无训练/正式评测批准，成本字段全部null。reviewer_status=pending/reviewer_outputs_read=false是主审写作时事实，协调者收口时应引用本review更新状态，不应回改主审封存初判。


## 关键证据、分歧及历史delta

| 主张 | 复核结论与决定性依据 |
| --- | --- |
| 根因是把多配置等同RUN_TESTS | 确认。初判已独立读CMake.test:151–159、utils:4–7及_build:103–111；gold仅修目标分派，不取消Multi-Config身份。 |
| 新增六case/四P2P，短Ninja参考合组 | 确认。reference_v1日志gold578/583/595–600与noop559/564/620–625命令、收集数和逐node状态与主审附录一致；原bindings明确两完整Ninja node全通过。六执行node与五解析参考键不是少跑。 |
| 新建测试文件导致本次恢复失效 | 不成立。A确把new file列作1 issue，并说明旧stage1裸checkout风险；当前恢复数0是文件原本不存在，apply0/present1且gold生产文件存活。主审将旧边界按17收窄正确，未验证任意候选安全。 |
| A称FAILED最后覆盖，同时Makefiles单独回归不可见 | A原文确有两种相冲突表述；B和本次delta的逻辑反驳成立。未重新执行旧parser，不能把反驳扩大为已实测旧stage1的所有顺序。 |
| 全局is_multi_configuration排除Ninja也是等价解 | A此说法错误。_build使用同helper产生--config；只改全局分类可满足target substring却丢配置。此为25的静态漏测反例，不是26的gold回归。 |
| 旧helper/None范围 | 主审处理恰当。旧API同型缺陷未修但题面缺import，新接口日志是线索；公开reader“两套都修”不得变新增门槛。人工__new__把generator设None不证明标准CMakeToolchain路径产生None；不能据此断言gold新增生产回归。 |
| 命令文本格式可能误拒、真实执行缺失 | 确认边界。新增断言固定POSIX引号，只看Mock.command；格式等价实现尚未实跑。24应始终保留“潜在”，25的--config、显式target、skip和真实执行未测不能写成已破坏。 |

A/B两份旧记录确有stage1/共享安全和环境标签等不同时间范围；主审没有把它们挪作本轮actor事实。A29仅基于题面无gold命中，A5仅本包路径比较，均不足以证明实际actor无答案或跨池独立；本次unknown恰当。A31的conftest_user入口值得保留线索，但这里没有投影/恢复后的恶意候选实证，维持unknown及空排除正确。

主审delta纠正自己“5个公开元数据文件”为4个，符合P中bundle/identity/prompt/brief加base目录的形状；未改封存初判。B的旧probe_candidate仅是当时模型建议，不继承为本轮ready_for_probe。

## 下一步与收口范围

支持唯一优先下一步：由任务二在真实actor正式入口跑临时、无外部依赖、无编译语言的Ninja Multi-Config公开recipe/CMakeLists流程；观测工作区源码生效、--config Release、默认test target和实际测试执行。只运行已有参数透传Mock测试不足；无需完整mp-units、编译器矩阵或为None人工状态单独做CPU。

本题没有影响收口的实质分歧。源码和相关helper/断言的独立已读范围以reviewer_initial.md为准；本轮新增主审五文件和A/B全文，未新增全仓审读或运行。主审卡可保留，但应由协调者把reviewer状态更新为“复核完成，actor仍未验”。

## 本次输入指纹

初判SHA256（核验未变）：`b0b89c6c9248b6634acc7813c5b1ec96152a78f1128f7d20993cac26ffd8bef1`。

| 本题获准文件 | SHA256 |
| --- | --- |
| public_read.md | `193f4b3d6f6d7c8bcbb102f979582b8b4c62cca3a4d777b9fabcd658d373f77c` |
| analysis_before_history.md | `fd6bbb7f7cf05c855e59f5225d351f512fb99c3b81b1a09f5ed00e091c06f319` |
| old_findings_delta.md | `9f6a23fc23a2776910a54ca9ae82979adb895f3d0dd94490364f4111b7876204` |
| card.md | `723e76df008d5c588940142c3201b08ae7fadbe255a1460c1b7eb8a907d7d401` |
| screening_record.json | `697ea7e56c807d80858bbe3661e98216fa794d0d211326e7c1f0a299588757a0` |

旧记录只读以下两件（路径相对ROOT=/Users/roger/Desktop/claude-code-verl-stage0h；SHA与RUN/history/本题/refs.json一致）：

- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-11594.json`：`58e7ed564888683294caf9c5e0a11b78830cc41e31b533a30f528b284438d1f2`。

- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-11594.json`：`abb4c739ed6579b671d48127225a3f08ef8e30fcfa6b7bcf0933ec1fecd7eedd`。
