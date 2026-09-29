# 独立reviewer：pack10_conan

工作区固定ROOT=/Users/roger/Desktop/claude-code-verl-stage0h，所有exec显式使用该workdir，不用默认cwd。B=/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925；RUN=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925。本轮只做静态质量审查，任务二由Claude B负责。
禁止执行或导入项目、测试、安装下载/网络、容器/SSH/GPU/模型实验、修改原题/测试/gold/评分/生产、commit/push和派生agent。允许静态文件/rg、只读Git、纯stdlib JSON/hash/AST及按授权选定的tar元数据/成员阅读。不得跟随链接扩读未授权题目或历史结论。实际actor消息/工作树/权限/资产/工具条件未取得则unknown，不能以Git base或历史grader代替。

先读B/roles/reviewer.md、B/record_template.md、B/check_number_reference.md、B/actor_environment_card.md以及ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/actor_development_validation.md。这些为中性方法；不要读batch_report、manifest、assignments、准备汇总、其他包/角色结果或根验收。
每题围绕八方面及需求—断言双向表，完整读新/改断言和决定性helper，逐个F2P、受影响P2P与实际选择/日志。P2P很大可风险抽查，但真实区段/未读范围明确，不以状态数量冒充语义覆盖。阅读全部gold改动及相关调用者，考虑合理非gold实现/误拒/漏测/回归，gold不是规格。原日志只核private/run_refs精确授权的本题行/成员；其他题共享文件只能机械选定行/指针。保留原命令、RC、安装/目标失败位置、初态差异、skip/xfail与expected映射，版本/source digest/actual image ID分开。不能从目录缺失猜镜像缺资产。
record规定13个必需顶层字段；checks用原1–40稀疏编号，每项status/evidence_refs/by，issues含category/scope/evidence_refs/proposed_action/status。check3实际输入与23规格分开，25覆盖不等于26已证gold回归，27局部正证据与完整性分开；29 actual actor泄露unknown与usage授权私有暴露分开，40流程不能证明无漏检/误拒/抽样偏差。additional_exclusions=[]、revision_refs=[]，disposition=needs_review/static_review，usage.intended_use=development_diagnostic；成本未观察为null，不造资格。每题唯一优先下一步，有具体可改变判断的疑点才提CPU，不机械凑反例或全仓运行。

本包只有以下2题：
- conan-io__conan-13610: PUBLIC=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13610; PRIVATE=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13610; OUTPUT=/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13610
- conan-io__conan-13788: PUBLIC=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788; PRIVATE=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788; OUTPUT=/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13788
初期只允许各题PUBLIC/PRIVATE及run_refs精确原件，禁止全部public_read、主审稿、history/旧质量结论和根汇总。不要查看其他OUTPUT文件，即使已存在。各题独立复核公开目标、全部新assert/helper、相关P2P、gold/调用者及原运行证据。
第一阶段唯一输出为各OUTPUT/reviewer_initial.md。必须本包2份都完成后计算SHA256，报告并结束等root明确cross_review release；封存不可改。不得自行提前读本题其他角色结论或历史。
收到root后续release后，才读获准public_read、主审四稿与本题历史，核技术判断、原件/历史复述与结构字段，主动找遗漏而不按意见人数表决，只写各OUTPUT/review.md并报告SHA，随后停止。
