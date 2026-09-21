# python__mypy-11236：历史对照

2026-09-21；B2 private investigator。结论仍为 **needs_review / static_review**，用途 **development_diagnostic**，`additional_exclusions=[]`。本阶段只静态阅读历史及其精确原件，没有新增项目运行、候选或测试修改。

本题无历史初稿已由协调者封存，SHA256=`2569d428660d3d94807b468a66f62d52733cabed9cc7b8ac71b6690efd8cc310`，本阶段不回写。下述结论补充该稿，不能倒填为历史前已知事实。

## 原件与暴露范围

所有路径相对 ROOT=`.`。

- H：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-11236.json`，由 `runs/swegym_quality_batch02_20260921_v2/history/python__mypy-11236/refs.json` 精确开放。本阶段读取全文。它是旧审查意见，不是运行结果。
- Raw：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:201`，只抽取 `instance_id=python__mypy-11236` 行。repo/base/version 对应 python/mypy、209a7193feb4bbfa38d09232b0a5a916e9d2e605、0.920；problem_statement 长1257字符，hints_text 长14157字符，均在封存后全文读到。没有访问其中网页、其它 issue 或 PR。
- 旧索引原件：H 中缩写的 docs 路径不存在；实际 `runs/env_overnight_20260916/L1_mypy_1/dupidx.txt:12,66` 和 `kcheck_all.txt:1–4` 存在。仅提取含本题 ID 的行及本题 kcheck 小块，没有读其它题结论或批次汇总。dupidx:66 同一行包含另一任务 ID，只用来核对 H 的路径唯一性主张，不跟进另一题。
- H 的 stage1 命令例子明确引用另一任务。没有读取它。本题已知 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/python__mypy-11236/` 下限定查找未定位到原件；因此没有本题 stage1 成功、失败或安装结论可引用。H 本来没有主张本题 stage1 对照，故不凭邻题构造 report-only 的本题成绩。
- E：`runs/swegym_quality_batch02_20260921_v2/private/python__mypy-11236/environment_record.json` 本阶段完整读取，包括 `verified_environment_pair`、install_wave1 和 checks 摘要。它指向的 `analysis_149.json` 未跟进。原始 G/N 账本、日志、image/build 和本题冻结工件在初稿阶段已读，以这些原件为证，E 不独立证明 actor 可用。

U、P、W、G/N 及精确日志缩写与封存初稿一致：U/P 为 I2 本题 public/private，W=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11236`。Glog=`W/gold/eval_logs/evallog_replay-er19-iw1-python___74f1c394.eval.log`，Nlog=`W/noop/eval_logs/evallog_replay-er19-iw1-python___32643f4f.eval.log`。账本均为对应目录 `ledger.jsonl:1`；run_id 分别 `er19-iw1-python__mypy-11236-gold/noop`、attempt=1。

## 旧主张逐项处理

| H 中主张 | 处置 | 决定性证据与当前边界 |
|---|---|---|
| 材料版本、补丁路径对应同一题（checks 1/4） | 确认，限定为已核对照 | source_refs 指向 S2 第187行；Raw:201 的 base/version 相符；原 G/N HEAD、gold 两行与冻结源码对应。Gold 只改 subtypes.py，test.patch 只改 check-literal.test。协调层全包验证与本主审必要文件验证分开记录。 |
| 基线缺少 Instance 已知值到 Literal 的判断、多个同长 Tuple 的 Union 丢失上下文（2） | 确认 | base/checkexpr.py:3306–3315、subtypes.py:278–297；Nlog:572–575 在正确布尔标签返回与 Final(1,) 上增加错误，Glog:571–572 通过。原题 CLI/flags 本轮仍未执行。 |
| 公开题面完整，1257字符（3） | 确认原材料；实际消息未核 | Raw 与 U/user_prompt 的原例、导入、flags 可读；实际 actor 渲染、截断和工具工作流未捕获。把 check3 一概写 pass/issue 都会混淆完整材料与真实输入。 |
| hints 含修复思路，14157字符（3/29） | 确认内容，暴露边界待核 | Raw 同时讨论 tuple 上下文拼接、Final 元组、is_subtype/last_known_value 方案及条件性风险。其一处文字把 subtype 方向写为 Literal 到已知值 int，gold 实际做相反方向的 Instance 到 Literal，故不称逐字 gold 代码。但它足以透露修复思路，若进入 actor 就是实质暴露。当前 public face 不传 raw hints；真实 actor 尚未审计。 |
| 不见 hints 就只能猜 gold，因而要求不足（3/23） | 推翻这一推论 | 公开复现、已有 Literal/Final 文档、last_known_value 注释与调用者足以支持调查；任务未规定唯一修改层。初稿已在不见 raw hints 时提出 tuple 局部比较和上下文推断两类替代路线。隐藏讨论不应成为求解前提。 |
| Final 元组没出现在 issue，故测试这族必属要求不足（23） | 未核实；缩小为合理范围争议 | Final(1,) 是同一已知字面值兼容性机制，公开 literal_types.rst:93–142、types.py:809–833 能解释它。不能只因题面未列举就判额外要求；原题、Final、精确诊断及旧行为仍须分别验证。 |
| 精确 got 文案可能拒绝上下文推断路线（23/24） | 保留具体风险，未证实误拒 | 初稿独立指出 incorrect_return1 在真 Literal 上下文中可能显示 Tuple[Literal[False],int]，而 patch:57/59 固定 Tuple[bool,int/str]。有 checkexpr.py:2106–2114、messages.py:1682–1708 因果依据；没有完整正确替代补丁和运行，不能提升成已发生 false negative。 |
| 测试强制唯一 subtypes 修法（24） | 推翻“唯一”断言 | tuple 局部逐元素子类型比较也能利用已知值并保持原 Instance 表示；尚无证据它必被拒。上下文方案也可调整推断边界。没有测试 helper 名、调用序或 gold 文本匹配。保留诊断契约争议，不规定只接受 gold。 |
| 仅做 Union tuple splice 就会令 invalid_literal_value 的 got 变成 Tuple[Literal[2]]（24） | 推翻所述直接因果 | patch:47–49 的赋值是 `x: Final=(2,)`，没有多候选 Union 上下文，返回时只是读取 x。仅改多候选 tuple 推断并不自动改变这个赋值。真正可解释的文本风险在带 Union 上下文的错误 return；不能把它扩展到每条反例。 |
| hints 中 splice 是更根本、同样正确的首选解（24） | 未核实，不采纳优劣排序 | Raw 用试探语气提出方案；后续回复明确指出两个二元 Union 位置拼接通常生成四种组合。它可以只作推断上下文，但必须最终按原完整 Union 保持分支关联，并另处理 Final。作者讨论不是完整可通过回归的候选。 |
| P2P=[]，所以任意放宽 Literal 子类型仍得满分（25/issues） | 前半确认，因果推翻 | F2P 虽只有1个 ID，实际有4个合法返回位置、1个 note、6条期望 error。把右侧 LiteralType 直接判 True 会接受 Final(2,)、Final(True,) 及错误标签等，令完整输出缺少期望错误，F2P 失败。不能由 P2P 空推出零保护。 |
| 修改旧 case 没被评分（25） | 确认，且本次也没执行 | test.patch:4–17 不含旧 case header；spec_vendor 按 patch 中 case header 抽 selector。Glog:560/Nlog:546 只运行新 case；各9846 collected、9845 deselected、1 selected。旧 `testLiteralFinalGoesOnlyOneLevelDown` 既不在执行选集，也不在冻结 F2P/P2P。 |
| 漏掉旧 case 就是漏一半目标，必须立即新增 F2P/P2P（25/26/disposition） | 推翻自动处置；实际缺口保留 | F2P 已覆盖 Final 元组正例和6条负例，不能按 case 数等分行为。修改旧 case 的两次调用仍值得验证，但候选得分需单列；普通未引用测试断言失败并不自动把当前冻结奖励变0。新增参考属于任务修订，不能本轮自动实施。 |
| 旧 case 在 base+test.patch 必 fail、加 gold 必 pass（issues） | 未核实的预测 | base/gold 语义支持此方向；原命令未选它。patch 同时把 reveal_type 包装调用改成直接调用并移除相关输出，不能只按删一个 error 当作实测。下一阶段应运行官方 patch 后版本。 |
| Gold 两行、无题外源码依赖（27） | 确认已核范围 | frozen 仅 subtypes.py，与公开 base+gold 精确文本相符；真实 editable 构建后 F2P 通过。初态另有两侧共同 test-requirements stub pin，已作为配方事实保留，不算 gold 交付。 |
| Gold 是 unsafe 的弱参考解（27） | 推翻确定性定性；更广安全性未核实 | Raw 风险有前提：若其它地方忘记清除 last_known_value。当前读到 checker.py:2227–2231 与 erasetype.py:134–151 存在普通变量清除边界；gold 使用原 subtype 选项与 Literal fallback+value 等价判断。未找到具体残留值反例，也未穷举全部调用者，因此既不判已知不安全，也不证明全局无回归。 |
| 本包只有本题 gold 碰 subtypes.py，故无重复（5） | 推翻路径唯一性；重复关系未知 | 旧 dupidx.txt:66 将本题与另一 ID 同列在 subtypes.py。共享源码文件不证明重复或同一修复；没有全面家族/留出重叠审计，check5 保留 unknown。 |
| fixture 齐全、测试正文离线（7/11） | 确认已执行测试，阶段范围缩小 | 已有 bool.pyi、Final/Literal stub；当前派生 grader 在 deny_all 下真实完成安装和该 case。准备、formal actor、本地安装权限及来源 expected 生成条件不能由测试正文无 URL 推出。 |
| 尚无安装执行证据（6） | 对当前引用配方已过时 | 当前 Glog:472–555/Nlog:458–541 有完整 editable build isolation、wheel 构建及安装成功；不是只看最后 hash -r 的 rc0。W image/build 对应派生镜像，但正式 actor 仍使用 public image/UID54321，不等于 grader/UID54322 资格已验。 |
| -k 子串风险使本题 check18=issue（18） | 对本题证据推翻 | 本题 kcheck_all.txt:1–4 报 selector1、overselect0；真实 G/N 各只有目标1项完成。H 引用的另一题 stage1 命令不用于本题判断。通用子串风险可存在，但本题当前没有过选证据。 |
| 问题因 P2P 空需 needs_repair | 过时/证据不足，改 needs_review | 静态风险和覆盖缺口不自动等于可复现缺陷。当前有解释清楚的0/1分差，actor、原题 CLI、修改旧 case、具体部分实现、替代解及回归待验。保持 static_review，不授予正式训练/评测资格。 |

## 对初稿的增量与下一步

历史原件没有推翻初稿的核心语义判断。它增加了 raw hints 的实际暴露、旧索引路径及旧论证错误：确认历史作者确实讨论两条路线，但不能据讨论把某条路线宣布正确或 gold 宣布不安全；确认旧路径唯一性说法与其索引不符。E 的 `verified_environment_pair` 仅概括已读派生 grader 对照，不能补足正式 actor 证据。

保留初稿提出的具体部分实现：tuple 局部比较若只用 zip 逐项检查而漏长度约束，可能通过当前同长度 F2P，却误接收原题 Union 下 `(1,999)`。这比旧记录的“无条件接受 Literal”更有区分力，但依然**未实现、未运行、未证明满分假阳性**。精确 got 文案的替代实现风险也保持同样证据等级。

唯一优先下一实验仍是：统一 CPU 负责人先验证正式 actor 的身份和所载源码，再对题面完整单元素 Union 原例及 `(2,)`、`(1,999)` 两个有公开语义依据的负例做 base/gold 对照。官方修改旧 case、具体 tuple 局部候选和正确上下文替代解随后分开验证冻结评分与独立行为；不自动补 P2P、放宽 oracle 或新增 exclusions。本轮没有执行这些建议。

没有读取 reviewer/其它角色或聚合结论；独立复核结果未知。历史耗时 `minutes=38` 是 H 自述，不换算本轮成本。原账本阶段秒数也不是审查或模型求解成本；未观测成本保持 null。全部特权产物不交给 solver。
