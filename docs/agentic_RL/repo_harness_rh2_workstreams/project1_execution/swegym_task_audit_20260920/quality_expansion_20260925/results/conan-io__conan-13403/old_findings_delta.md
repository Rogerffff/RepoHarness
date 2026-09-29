# conan-io__conan-13403 — old findings delta

root已明确release；封存初稿SHA256 `5d91b41b280b2345a9bb0f66c5950bd0f6489fe8be4bef076ad9938ee9492ddf`，本轮核未变。只读取本题history/refs.json指定的两份原记录；未沿其链接扩读。

L1 = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-13403.json`，SHA256 `e865e310c1d2a243ecda3b4c1a92c70bca3ec957dd0599686c1cfc687688cd24`（全文读、hash核一致）

pilot = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-13403.json`，SHA256 `c748ad98e93c64dd19b1c1bae2bb6ae3b5e4cca4e8c9fb4e6cd1e2dbaa5d4610`（全文读、hash核一致）

## 逐项历史主张复核

| 精确旧字段 | 旧主张 | 处理 | 决定性证据与边界 |
|---|---|---|---|
| L1 /public_view、/checks/23；pilot /public_sufficiency | 关键字测试下新参数位置不影响；参数和语义可类比configure | 确认类比、纠正位置无影响 | 测试用keyword确不受位置影响，但旧公开autoreconf(args=None)允许列表位置调用。gold把列表绑定路径，join会TypeError。封存稿已独立给出静态推导。 |
| L1 /checks/25、26、/issues/0；pilot /old_claim_reviews/0 | P2P=0就是零回归保护，必须补全量P2P | 纠正L1、确认pilot | 唯一F2P仍含旧configure相对/默认命令及新增默认autoreconf目录/命令；计数不等于语义。漏cwd/args是25；本次有独立位置参数证据才记26。 |
| L1 /checks/24、/issues/1；pilot /old_claim_reviews/1 | 模块级chdir和位置形状被锁定 | 确认静态约束 | helper支持同名keyword/recipe参数，测试assert_called_with固定(autotools,path)；未执行替代候选，不泛称runtime错误已复验。 |
| L1 /checks/24；pilot /old_claim_reviews/2 | abspath会因规范化失败 | 纠正L1、确认pilot | /path/to/sources/subfolder已经规范绝对路径，abspath不会改变该测试字符串。Path对象/传参形状另论，不混同。 |
| L1 /checks/27；pilot /requirements、/unknowns | gold正确完整 | 纠正完整性判断 | 方向对应且唯一F2P过，但旧位置参数列表被join处理的兼容性破坏有源码证据；没有CPU复验，仍是静态推导。pilot未讨论这项。 |
| L1 /checks/6_7_11 | 测试改变cwd不恢复；依赖外部mock | 确认源码事实、收窄影响 | 测试确os.chdir(temp)，requirements_dev明确mock依赖、历史已执行。没有跨测试污染运行反例，不能说更宽选择必污染；当前actor未知。 |
| L1 /checks/20；pilot /test_assessment、/old_claim_reviews/3、/next_action/1 | 分差来自目录功能；mock工厂被调用不等于进入context | 确认局部与漏测 | noop在unexpected keyword失败，gold过；不代表真实cwd。丢弃context仍调用工厂的错误候选尚未执行。 |
| L1 /proposed_regression_tests、/disposition_hint；pilot /next_action/0、/recommendation | 扩gnu目录或等价keyword反例；needs_counterexample | 优先级更新、实验状态未核 | 不机械全量GNU测试。现有更明确位置参数兼容问题优先用最小行为探针；keyword误拒/不进context漏测仍保留。 |

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

封存初判核心保留：目录目标明确，但gold破坏旧位置args调用；mock实现锁定和真实cwd漏测；actor条件未知。 后稿新增历史主张的精确分级与本题conftest静态取证，不回写初稿；没有新运行结果。以同一最小私有行为探针对比 base/gold/保留 args 首位的兼容实现，记录位置参数、新目录、实际run时cwd及恢复；优先验证gold兼容性，无需系统autoreconf或全仓。

新增静态阅读：本题S/conans/test/.gitignore全文；S/conans/test/conftest.py :212–253。其余证据范围见封存稿，不把后读内容写成封存前已知。
