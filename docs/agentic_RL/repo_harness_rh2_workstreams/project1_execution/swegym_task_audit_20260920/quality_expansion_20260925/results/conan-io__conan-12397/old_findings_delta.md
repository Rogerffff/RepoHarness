# conan-io__conan-12397 — old findings delta

root已明确release；封存初稿SHA256 `522f157716606ea84dcc9e492c5dd74229b630872c90e7a5170d571c127efe52`，本轮核未变。只读取本题history/refs.json指定的两份原记录；未沿其链接扩读。

L1 = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-12397.json`，SHA256 `ccff761d0c0d558e26d4a4818ea52084734fdd44a6fbdafd492051cd8559eed0`（全文读、hash核一致）

pilot = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-12397.json`，SHA256 `bee3b541f681712dd9c65749cc6ffa577bd468f51679703355598bbeec05abe6`（全文读、hash核一致）

## 逐项历史主张复核

| 精确旧字段 | 旧主张 | 处理 | 决定性证据与边界 |
|---|---|---|---|
| L1 /checks/1、/issues/0；pilot /old_claim_reviews/1 | P2P test_extra_flags_via_conf 被改写 | 确认事实，纠正其被当材料错误的倾向 | test.patch第二三hunk更换libcxx并增加ABI0；本轮noop该P2P通过，P2P是补丁后基线状态，不要求原文不变。无需改评分语义。 |
| L1 /checks/2、23、27；pilot /public_sufficiency、/old_claim_reviews/0 | 缺link stdlib，公开提示充分，gold一行正确 | 确认局部、收窄完整性 | helper分离libcxx与ABI，统一_context同时输出native/cross；当前gold新增cpp_link_args符合目标，但无真实链接/全分支证据。 |
| L1 /checks/24；pilot /old_claim_reviews/2 | 逐字符相等且stdlib必须最后，是过严顺序要求 | 纠正比较类型、保持争议未知 | 实际是in子串而非全文相等；精确列表顺序存在，但冲突flags有先后语义，未提供等价重排运行反例，不仅因题面未写顺序就判必须修订。 |
| L1 /checks/25；pilot /old_claim_reviews/3、/next_action/1 | 仅Apple修复可过，native GCC不证明Linux clang | 确认静态缺口 | F2P Apple cross；2P2P Windows gcc。没有正式错误候选评分，新反例状态仍not_run。 |
| L1 /checks/26、27；pilot /test_assessment | 同文件全测即gold无回归/完整 | 收窄 | 3测试全文已读，不计全仓语义覆盖；重复content副作用多为base既有，sun/qcc/冲突flag/真实链接未核。 |
| L1 /disposition_hint；pilot /recommendation、/next_action/0 | ready_for_probe / 可进模型探针 | 不继承资格 | 现有历史是grader生成文件测试，actor未知；保持needs_review/static_review，优先特定生成物漏检验证而非直接模型。 |
| L1 /proposed_regression_tests | 扩展 Meson 单测/功能构建 | 范围收窄 | 功能工具链需要actor资产；不机械全仓。先按确切键核Linux生成物更能改变本题判断。 |
| 封存独立稿新增，与两旧记录比较 | cpp_link_args 子串可误匹配 objcpp_link_args | 新增确认的静态线索，不是旧结论沿用 | 模板有objcpp_link_args；F2P子串无键首锚定。只修Objective-C++列表可能满足断言而cpp仍坏；尚未运行，记录25而非26。 |

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

封存初判核心保留：目标与gold局部一致，但验收缺Linux native Clang且未锚定cpp键名；当前actor与真实链接未核。 后稿新增历史主张的精确分级与本题conftest静态取证，不回写初稿；没有新运行结果。补按完整配置键读取的 Linux clang/libc++ native 最小验收，比较只修 objcpp_link_args 的错误候选；局部 CPU 可判定后缀匹配漏检，当前未执行。

新增静态阅读：本题S/conans/test/.gitignore全文；S/conans/test/conftest.py :178–210。其余证据范围见封存稿，不把后读内容写成封存前已知。
