# conan-io__conan-11560 — old findings delta

root已明确release；封存初稿SHA256 `fbfbab248b92297acdeae98fbb3d443fe55f73b678305559d5c86d763e644ca0`，本轮核未变。只读取本题history/refs.json指定的两份原记录；未沿其链接扩读。

L1 = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-11560.json`，SHA256 `d6b7e64e4a031235776cf30fccbc364641a50d71c65079381e7175238f769bcb`（全文读、hash核一致）

pilot = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-11560.json`，SHA256 `3c7ecf09e9a11ad370647b40af2c550b750632b704b6dd553513529e8a873317`（全文读、hash核一致）

## 逐项历史主张复核

| 精确旧字段 | 旧主张 | 处理 | 决定性证据与边界 |
|---|---|---|---|
| L1 /checks/1、/checks/23、/issues/0；pilot /old_claim_reviews/2 | 题面要求 alwayslink，验收要求保序注释 | 确认，编号收敛到23 | P/user_prompt.txt、V/gold.patch、V/test.patch；静态材料身份对应不等于需求与断言一致。 |
| L1 /checks/24；pilot /old_claim_reviews/1 | 四处均逐字符锁死8空格、任何合法替代都必败 | 纠正 L1、确认 pilot 的收窄 | 两处 substring 钉空白；transitive 正则容忍空白；shared 全文先删空白。四处都要求小写指令，不等于所有合法实现必败。封存稿已逐项区分。 |
| L1 /checks/25、/checks/27；pilot /old_claim_reviews/0、3 | 自由文本注释无作用、gold 不修真实问题；pilot 称是 Buildifier 功能指令 | L1 断言过强；pilot 外部机制本轮未核 | 源码已保留 libs 输入次序；未取得 Buildifier 参与原用户流程的证据。pilot 引用 buildtools 5.1.0 rewrite.go SHA 与 Bazel 5.3.0 CcImportRule，但该外部原件不在授权范围，未联网/跟随引用。可记录有依据的历史机制主张，不能升格本轮独立验证。 |
| L1 /issues/1/proposed_action；pilot /old_claim_reviews/4 | 只检 lib1 在 transitive 前可替换现断言 | 纠正 L1、确认 pilot | base 模板与旧 transitive 正则本已具有该顺序，此检查会让 base 过，未验证格式化保护或链接。 |
| L1 /checks/2、/checks/20 | base 无注释且4 F2P失败；分差来自目标行为 | 确认文本差分，收窄目标范围 | 本轮原日志四处注释断言失败、gold过；不等于题面真实多库链接已复现。check2 的链接问题仍 unknown。 |
| L1 /checks/26、/checks/27 | 3 P2P 全过即无回归；gold 与题对应弱 | 收窄 | 同文件头文件/主BUILD/build-dep 的具体断言已读，提供局部证据；完整无回归未知。gold 确无 alwayslink，公开输出分歧保留；不称实际链接必失败。 |
| L1 /disposition_hint；pilot /recommendation、/next_action | 只能记忆PR通过；needs_counterexample及大写注释反例 | 不采纳必然性，候选实验保持未核 | 没有真实盲解证据，不能断言只能记忆。DO NOT SORT 等价性依赖未独立核过的 Buildifier 外部机制；pilot 明写未运行。当前唯一下一步仍先定公开契约。 |
| L1 /proposed_regression_tests | 扩展 BazelToolchain 与已有main测试 | 未执行、不强制扩仓 | 该主测试本就在已核 P2P；新工具链范围未验证，不能取代双静态库行为。 |

## 跨记录共用口径复核（仍只指本题）

| 旧字段/主张 | 本轮处理 | 证据/限制 |
|---|---|---|
| L1 checks.3 题面完整故pass，checks.29无泄漏 | 收窄；actual actor两项unknown | 计划user_prompt/public_bundle不是实际消息、工具呈现或可见工作树；旧raw.hints_text仅历史记录所述，未重读来源，也不等于本轮public_hints或实际交付。审查者私有暴露单列usage。 |
| L1 checks.4_17 路径分离即pass | 确认静态分路径和历史局部恢复；4与17分开编号 | 封存稿核gold投影、base checkout/test.patch apply及selected IDs；actor权限与任意候选恢复完备性未验。 |
| L1 checks.5 无同族 | 未核跨池、保留unknown | 旧包限定推断不支持全池去重/留出重叠。未跟随其他题引用。 |
| L1 checks.6_7_11、pilot environment verified_original_baseline | 确认对应RH2窄命令可执行，收窄至历史grader | 安装末命令RC0、noop目标断言失败/gold选中测试通过已在封存稿核原件；实际image ID缺失，actor资产/安装恢复/网络/资源未验。旧stage1/prescan/envscan未在本次授权范围复读。 |
| L1 checks.19 / collide扫描 | 确认当前授权expected与原日志逐ID映射；未核旧扫描 | 全部F2P/P2P已读，选中测试无missing/skip/xfail，原parser标识记录；不是控制面安全证明。 |
| L1 checks.31及control_surface_conftest_user；pilot unresolved | 确认本题静态导入线索，当前攻击可达性unknown | release后只补读本题conftest导入区与.gitignore；可能导入用户模块不代表它能穿越当前候选投影/可信恢复。未读旧仓库总报告、未运行篡改、未删配置/清整个测试树。 |
| L1 proposed_action清配置/扩大测试；costs.minutes | 不执行；不继承费用/资格 | additional_exclusions=[]，revision_refs=[]，本轮token/费用/新CPU时间null。是否扩大测试需具体行为疑点，不机械求全仓绿。 |
| pilot evidence_level 的其他日志/16份hash、外部引用 | 仅承认本题已授权并实际核过的材料 | 不按历史报告内链接扩读共享总结、外部网页或其他题；本次六个记录逐字读取和hash核对，未独立重做其全部取证。 |

本轮 reviewer 未授权且未读，不能填写一致/通过。check40不能由封存流程推断无偏差。最终disposition保持needs_review/static_review、usage=development_diagnostic，非训练/正式评测准入。

## 初判变化及唯一优先下一步

封存初判核心保留：公开 alwayslink 方案与强制小写注释验收错位，实际多静态库链接未核；当前 actor 条件未知。 后稿新增历史主张的精确分级与本题conftest静态取证，不回写初稿；没有新运行结果。先由题目维护方裁定公开契约：保留 alwayslink，或为防排序方案提供公开依据；据此设计行为验收，当前不优先机械 CPU/模型/全仓运行。

新增静态阅读：本题S/conans/test/.gitignore全文；S/conans/test/conftest.py :137–166。其余证据范围见封存稿，不把后读内容写成封存前已知。
