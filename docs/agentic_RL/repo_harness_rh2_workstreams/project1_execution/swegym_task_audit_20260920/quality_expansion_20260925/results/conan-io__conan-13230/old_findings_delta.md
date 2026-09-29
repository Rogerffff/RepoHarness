# 13230：旧结论逐项对照

在明确history release后，仅读A=env_overnight_20260916/L1_conan/records本题JSON、B=swegym_task_audit_20260920/conan_pilot/records本题JSON。

| 旧主张 | 判定 | 决定性证据与影响 |
|---|---|---|
| A1/4_17是正常_test.py测试文件、恢复不吃源码 | 确认本次条件 | base测试文件及patch已读；历史恢复该文件、生产autotoolstoolchain.py独立投影，attest正常；不继承跨仓误报故事 |
| A2/20、B原始noop/gold有效对照 | 确认，但解释需具体 | ledger13/14：noop构造时xcrun127，尚未达三assert；gold35pass，34P2P均保留；安装rc0 |
| A27只修Apple flags因此漏改compiler选择 | 推翻 | 生产39–49、73已读host settings；正文描述flags污染，标题是用户归因，不能增加另一未证需求。B推翻成立 |
| A23公开可推出非Apple目标禁Apple flags | 确认 | Linux正文、is_apple_os定义、Android代理根因；属性名在base可读，但不等于题面要求精确None内部表示 |
| A24多内部路线可过、无唯一实现 | 确认主要结论并收窄 | helper/内联目标OS条件等可用；None/空串等价过滤存在潜在误拒，但旧P2P也规定None，不据此宣称整个oracle无效 |
| A25三断言充分覆盖三个新泄漏出口 | 推翻“充分/三个新增” | min_version输入无os.version/os.sdk，本来空串；官方缺题面Linux及最终flags；Android-only错误分支静态可能通过。B反驳成立 |
| A26“macOS→macOS”由isysroot/min_os守住 | 部分纠正 | isysroot前半为Macos build→iOS host，后半native Macos；min_os是native Macos。确有Apple回归检查，但不是全Macos交叉矩阵 |
| A19参数化config0..11、35参考无碰撞 | 数量/无碰撞确认，参数范围纠正 | 实际libcxx是config0..13共14条；两architecture参数、msvc等完整无空格。初判已列完整34P2P |
| A6_7_11纯Mock所以无需外部进程 | 限定修正 | gold窄路径无真实交叉工具链；base错误分支确会调用xcrun，不可说所有路径无子进程。缺xcrun是错分支症状，不宜先安装SDK |
| B Linux/最终flags遗漏与诊断建议 | 确认；仍未运行 | 初判独立发现同缺口；有SDK的参数检查可诊断，但优先公开profile生成流程更能同时检验actor入口 |
| A ready_for_probe / B优先模型 | 不继承资格 | 缺actual actor证据，保持needs_review/static_review；本题不需要先真实M1、openssl、交叉编译器或全仓测试 |
| A回归建议、额外排除空 | 空排除确认，建议不作验收 | 其它GNU单测/集成可作为后续窄测；本轮不执行也不从路径存在声称已覆盖 |

初判核心未改变；旧B支持主审根因与覆盖判断，未带来新运行。旧A“标题未修”issue应撤回；不把这个撤回错误地变成全覆盖pass。

## 共同边界修正及未核范围

- 旧check3把“题面完整”记pass，不满足本批“实际输入”定义。计划题面可读，实际actor user/system/tool消息及hints仍unknown；规格问题归23。
- 旧check5关于本包无同族/某其它题不同文件的结论未核。本轮未读取其它题或跨池划分，记unknown，不能沿旧结论推导去重完成。
- 旧check29从题面无gold行/无PR指针推导“无泄漏”不足。实际actor工作树、未来Git历史、忽略资产和工具可见面未采集，29为unknown。授权私有审查见gold/测试/旧记录只记录usage，不记actor泄漏事件。
- 旧check31的conftest_user入口是仓库线索；本题原运行只说明普通noop/gold的可信setup/控制面attest成功，不证明恶意候选能否存活投影/保护并伪造评分。未执行攻击或读取完整当前恢复实现；判定unknown，额外排除列表保持空，不能照旧建议直接清整个测试目录。
- 旧环境pass/verified仅适用于其明确grader条件，不迁移到当前actor。旧成本minutes没有本轮工具观测，成本字段一律null。
- 未打开旧报告内的stage1工件、repo_level_findings、CODEX_REVIEW、repair_catalog、scope_reconciliation、analysis聚合或其它题；因此对这些原件未独立核实的旧主张明确保留未知。

本次仅新增读取本题history/refs.json以及其中两份sources旧记录全文。初判全文与SHA未改，历史未提供任何新运行；没有项目执行、测试、安装、联网或模型调用。reviewer尚未完成/未读取。

## 已释放旧记录身份
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-13230.json`；SHA256 `c6eaec8463f43a09d071f3006affbb31608b328e6073cbbcd0d3a1c57fd03ab8`。
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-13230.json`；SHA256 `c00523ad468fa45dfb206bfbc8247d1093e036f5d1b4f3fe67f8d3ad2d7a3005`。
