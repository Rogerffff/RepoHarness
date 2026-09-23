# python__mypy-11707 — release 后独立复核

结论：**同意主审的两项核心发现与 `needs_review / static_review` 处置，要求修正检查项映射及状态范围；不沿用旧记录的“必然零分、诚实求解不可完成”判断。** 同意把第一优先实验缩为原四文件的 base/gold × Y/X；粗改回归候选独立保留，作为后续评分校准。未发现新的已证实 gold 实现缺陷或当前 actor 阻塞。

本稿是在协调者核验独立初稿 SHA256 并明确 release 后撰写。封存的 reviewer_initial.md 未改，重新读取计算仍为 `4f813ecd76d1699c7f83a4a64e9d8d37ed383f9584250065cde04a1634b65144`。本轮无项目执行/导入/测试/安装、网络、Docker、SSH、模型或新 agent；唯一写入为本 review.md。以下运行结论均来自已存在的 09-19 原始日志；其他行为判断明确为静态推断。

路径约定：

- ROOT=`${REPO_ROOT}`
- O=`${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch05/results/python__mypy-11707`
- P=`${REPO_ROOT}/runs/swegym_quality_batch05_20260921_v1/public/python__mypy-11707`
- V=`${REPO_ROOT}/runs/swegym_quality_batch05_20260921_v1/private/python__mypy-11707`
- E=`${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11707`
- A=`${REPO_ROOT}/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`
- CHECKLIST=`${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/environment_screening_checklist_20260915.md`
- OLD=`${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-11707.json`

## 主审决定性主张的逐项核验

| 主张及位置 | 复核判断 | 原件支持与边界 |
| --- | --- | --- |
| I1：题面“两种都接受”与公开旧契约/gold 方向冲突（analysis:7,29–35,79–81；card:3,7） | **同意** | P/user_prompt.txt 明示成功，P/base/docs/source/command_line.rst:568–572 明示改名不导出，check-modules.test:1819–1840 公开 stub 用例也作此区分。gold 仅把 module exception 限于 MypyFile；在 no-implicit-reexport 下 X/Y 两个改名导入均非 public。原四文件 base/gold 的实际输出尚未观察，不能写为运行结果。 |
| 隐藏测试并非完全没有公开依据，不能把它直接视作普通 `.py` 新语义的反面（analysis:57–65,73；delta:12–15） | **同意，保留这种精确区分** | F2P/P2P 依靠 `.pyi` 隐式关闭导出，不带原例的 CLI flags。公开语义允许分别讨论 `.py` 与 `.pyi`；隐藏 stub 断言检验旧契约的同名碰撞边界，而没有裁决普通 `.py` 任意 as 是否应扩展。 |
| I2：去掉模块豁免的粗改可能过现有评分却破坏真实子模块（analysis:8,53,61,75；card:14） | **同意，证据仍是静态候选** | 原码 semanal.py:1841–1925 与公开 `testReExportChildStubs` :1879–1895 足以预测：`module_hidden = not module_public` 隐藏包内 `from . import submod`，导致主文件的 from-import 被拒；F2P 同名 mod 与 P2P 的 D 仍 public，internal_detail/C 隐藏，两个参考没有该正例。历史实际命令仅选 F2P3/P2P，既没执行粗改，也没执行真正子模块正例。不能把 I2 改写成已证明 reward=1 或 gold 自身有回归。 |
| 两个参考的 helper 真实做类型检查，不强制 gold 内部表达式（analysis:47–69,73） | **同意其静态子结论；总体 check24 仍待替代解证据** | 初判已完整读新增 case、唯一 P2P、fixture、data.py 的 E/N 展开、testcheck.py:197–227 的 build.build 与完整诊断比较、helpers.py:46–120。没有 helper 名、源文本或操作顺序绑定；常规诊断和 reveal 类型有公开旧例依据。未运行不同于 gold 的合法替代解，也未完成公开规范裁决，因此不能据“未发现固定表达式”完成整个无误拒检查。 |
| 材料同题同版本，基线初始 bug 有证据（analysis:20–22,39–43） | **同意材料对应与 stub 初态；原例初态保留未知** | 本 reviewer 独立阶段已核 V 的 patch/bundle 相等、host grading 第193行、gold hash、plan index53、原日志 hash；noop 真实执行 F2P 且仅缺 internal_detail 错误。不能把报告者 0.910/Python3.10 输出或该 stub 失败当成当前 base 四文件 `.py` 的观测。 |
| 安装维修后历史 RH2 gold=1/noop=0，有实际测试体、安装和清理闭合（analysis:87,98–104；card:16） | **同意历史限定** | E/gold 与 noop ledger 第1行、对应 eval.log 和 diagnostics/driver 已独立核过；GLOG:651–668/NLOG:633–665 展示具体命令、收集10041选2、逐测试状态/错误栈和 test_rc。两边安装均出现成功 editable build/install，而非只看最后安装码；清理完成。env_qualification=absent，不等于正式资格或当前 actor 通过。 |
| 实际初态包含依赖 pin；镜像中的 typeshed `git show` 不应误认环境差异（analysis:104,126） | **同意** | NLOG:356–365 的 git diff 只有 test-requirements.txt 增加 types-typing-extensions==3.7.3；GLOG:357–383 再增加 gold 源码；大段 typeshed 文本位于 git show 的基线提交展示。noop projection=[]、gold projection=[mypy/semanal.py]，不将该 pin 算 solver 修改。 |
| historical replay 的派生镜像不能自动证明正式 actor 消费了维修（analysis:104；screening:21,397–410） | **同意** | 本阶段补读 A!src/repoharness2/adapters/slime/replay_grade.py:424–477，:455 将 grader spec 替换为派生镜像；初判读过 :293–374 的 candidate 派生镜像与 agent 应用步骤。A!src/repoharness2/adapters/slime/prepared_task_face.py:336–350 的正式 rollout 从 public.image 取值。代码路径边界明确，当前真实 actor 配方、shell、源码来源/权限/消息仍未知。 |
| 官方恢复不误删 gold，额外排除保持空（analysis:108–112；screening:413–429） | **同意，限定该源码路线与历史交付** | test_patch 只有 check-modules.test；GLOG:384–424 恢复并应用 official test，gold 源码正常投影。test_globs=() 不支持“所有测试文件都恢复”的通称。没有本题合理修复必须改被恢复文件的证据；未验证所有可能候选或评分绕过。 |
| 不猜重复关系、完整答案泄漏、模型成功率或训练价值（analysis:114–118；delta:24–26） | **同意** | 本题以外的 commit/补丁/环境都不在获准检查范围；本题 prompt 不含修复源码是窄事实。实际镜像、预装包、Git可见对象及真实消息未检查，不能外推无泄漏。只作 development_diagnostic。 |

相关源码补核：本阶段直接读 P/base/mypy/fastparse.py:891–920、build.py:755–788、test/data.py:594–636，确认导入别名保留、同名子模块依赖和 DataFileCollector 来源；读 semanal-modules.test:808–866 及 check-modules.test:2870–2922，确认默认 `.py`/stub、缺失来源、__all__/星号的主审引文。没有把主审多读过的所有文件自动登记成本 reviewer 已完整阅读。初判已覆盖的核心导入、可见性消费者、测试与原始日志证据继续有效，不为了交叉阶段重复打印全部材料。

## 40 项编号与状态修正

CHECKLIST:17 说明这些是责任分类，不是 40 个代码闸门，未查不能因没发现问题填 pass。以下建议应写入可更新的收口材料；**不改任何封存初稿**。我本次也没有编辑 screening_record/card。

| 当前记录 | 建议收口 | 理由与仍可保留的已证事实 |
| --- | --- | --- |
| checks.3=issue，以规格冲突为证（screening:181–190） | **改 unknown；把规格冲突留在23，不作为3的已发现输入故障。** | CHECKLIST:25 的3问实际 solver 收到的消息/公开文件是否完整准确。当前只有静态渲染及 bundle，真实 CC 请求、system/public_hints 注入未捕获。原件规格冲突是23的问题，不能用其替代输入运输证据；也没有证据证明实际消息丢失或损坏。 |
| checks.7=pass，note 仅为“无业务外部资产”（screening:220–229） | **改 unknown。** | CHECKLIST:34 要实际加载、实际用户可读路径、来源版本及缓存/wheel不带答案。已证：两项历史 grader 测试消费本地 fixture 成功，公开源码中相关资产可定位，未见运行期业务资产需求。未证：actor 权限/当前资产完整性、目标镜像可得、wheel/context重新提供、答案污染。资产需求已盘点不等于实际资产齐全。 |
| checks.24=pass，限定“未见固定gold表达式”（screening:294–303） | **改 unknown，note 保留静态子结论。** | CHECKLIST:66 要核约束依据，并有目的检查合法替代解。此处无不合理内部实现绑定的静态观察充分，但没有替代解运行；公开规则尚有分歧。unknown 不表示已发现误拒，也不要求穷举所有合法程序，更不自动增加统一实验前置。 |
| checks.2=pass，但 note 明确只验证 stub（screening:171–179） | **建议总体改 unknown，保留“历史 stub 初态已确认”的子结论。** | 这是本 reviewer 对三项协调者提醒之外的范围补充。CHECKLIST:24 问题面初始问题，明确包括题面复现。当前原四文件行为只静态预测；单一 pass 会高估对原例的直接确认。若收口继续保留 scoped pass，必须在任何摘要中显示 stub 范围，不能汇总成“原例初态已实跑”。我更倾向 unknown 与原例第一优先实验一致。 |
| checks.4=pass，证据仅指 test_patch 是纯测试（screening:192–198） | **可保留本题 gold 源码路线的 scoped pass，但补引用及 note。** | CHECKLIST:26 的4问合法修改的可读/可改/可提交范围；“纯测试补丁”不足以独立证明此点。应复用已经核验的 gold projection、官方恢复与 test_globs=() 原件，明确仅支持 mypy/semanal.py 这条已交付路线；不把一般配置/辅助文件修改全部判通过。 |
| checks.27 note 写“依赖齐”（screening:328） | **改为“gold未引入额外交付依赖；指定历史grader安装完成”。** | 现有证据足以支持这两点；“依赖齐”脱离主体容易误读为当前 actor 的开发环境已齐，后者仍未知。保留27的规格对应 issue，别将其写成已证实 gold 回归。 |

其他已填状态按证据范围保留：1为本题材料绑定；11为所审测试无需运行期外部服务、指定历史 deny_all 安装/测试成功；17–20为该历史 RH2 配方、该 gold/noop与两项参考；5/6/26/29的 unknown 合适。23的 issue 是公开文本冲突；25的 issue 是已观察的关键回归覆盖缺失加静态反例候选，不是实际漏洞命中；27是 gold 与题面字面期望的静态对应问题。未列检查仍不补 pass。编号修正不改变 needs_review 的核心理由，也不抹去环境已修复的历史证据。

## 自身初稿资源单位更正

协调者提醒有效，我独立重新读取 E/{gold,noop}/ledger.jsonl 第1行确认：

| role | 原字段和值 | 能支持什么 |
| --- | --- | --- |
| gold | `resource.mem_peak_mb = 126.641`；`mem_peak_unavailable_or_zero = false` | 该次历史记录的原始观测值；单位换算实现未核。 |
| noop | `resource.mem_peak_mb = 131.801`；`mem_peak_unavailable_or_zero = false` | 同上。 |

封存 reviewer_initial.md 将其概括成“约127–132MiB”没有已核的单位实现依据，应撤回该单位表述；这里保留原字段与值，不补做换算。主审 analysis:102 写为 MB 也宜在可更新收口材料中统一改为原字段表述。政策的 `memory_bytes=4294967296`、`shm_bytes=67108864`、`tmpfs_bytes=1073741824` 则有明确字节字段，和该峰值单位问题不同。测试 `test.seconds=4.165/4.311` 与 rc=0/1 也由原字段明确记录；这些均不是 actor 求解的资源承诺。封存初稿不回写。

## 自身历史复核：确认、收窄与未核实

本次只按 release 读取 history/python__mypy-11707/refs.json 及唯一 OLD，未跟随它关于其他题、聚合、PEP 或 GitHub hints 的任何链接。

- **同意 delta 对旧绝对结论的修正。** OLD:17、29、33、57 称“没有任何公开反向线索/唯一依据只在 hints”，被本题 base 文档中 bar as bang 不导出的明确例子和公开 C as D stub 测试反驳。不能因报告者期待不同而忽略完整公开仓库；反过来，仓库旧契约也不能默默覆盖题面的新行为请求。
- **“字面正确解必得0”没有成立。** OLD:33/57 的论证把普通 `.py` 与 `.pyi` 合并了。实现可以将 `.py` 改名导出按字面请求扩展，同时保留 stub 的同名导出规则并修正 stub碰撞；当前两个参考全部为stub，静态上没有理由排除这条路线。此思路不是已经实现/跑过的合法替代解，也不代表其与所有旧 `.py` 契约自动兼容；它足以说明旧记录未证明“必然”这个全称命题。
- **旧 hints 只能保留转述。** OLD:17/29/47 引述的维护者结论与 PEP 链接没有获准可核的原件。当前 public_hints 是通用操作/环境指令，两者不能混名；不能把旧引文直接作为本次公开需求裁决依据或抄入新题面。
- **同意保留具体回归缺口，反对无条件扩充整个家族。** OLD:35–36/48 的真实子模块正例未入P2P得到当前原始命令确认；其他同族、pep561 全部前置的必要性没有论证。最窄区别是直接的 from-import 正例，既有广泛测试名单只能作待选资料。
- **历史环境未查的旧表述已过时，但不能回填旧 stage1 或当前 actor。** 09-19 install_wave1 原始证据已补足指定 grader 的安装、测试与清理；没有访问旧stage1或外部聚合。旧nodeid对另一题的比较、同文件分簇、无泄漏全称结论和21分钟成本均不移植。

因此我同意主审维持 needs_review 而不照搬 reject_revision；这不是因为 gold 满分而放宽题意，而是旧拒绝论证过强、当前仍有可解释的维护路线与可定位的剩余问题。

## 最小下一实验与安排取舍

**采纳主审的第一优先：原四文件 base/gold × Y/X。** 用两份固定初态源码、各自独立的临时MWE，运行题面相同命令，先记录真实入口、镜像/配方、UID/HOME/cwd、解释器及 mypy.main/semanal 加载位置，再保存四项退出码与诊断。实际命令仍是公开的 `PYTHONPATH=/testbed python -m mypy --strict --no-implicit-reexport .`；只在发现配置/缓存干扰时追加隔离配置、禁增量的诊断对照。本轮没有创建这些目录或执行任何命令。

| 要观察的组合 | 静态预测；不得作既有结果 |
| --- | --- |
| base + Y as W | 下游 d.py 导入 W 被拒。 |
| base + X as W | 原意外放行仍存在。 |
| gold + Y as W | 仍拒绝。 |
| gold + X as W | 从意外放行变为拒绝。 |

这四项是确认“原不对称是否成立、gold 如何改变它”的最小完整对照，不需要先创建错误候选或改评分。文本冲突本身已由公开原件成立；实验只验证行为及版本适用性，不能替协调者决定究竟保留旧规则还是扩展普通文件规则。如果选择修改公开规格或验收，应形成独立修订版；不能因观察与gold相符就追认该方向为原题唯一正确答案。

**粗改候选作为第二个独立问题。** 后续授权的窄实验可在 base/gold/`module_hidden = not module_public` 三方对照官方两参考及公开精确 `testReExportChildStubs`。该正例已足以分辨去掉真正模块豁免的回归；ChildStubs2 是补充另一种导入方式，不必与全部同族/pep561一起形成前置。若错误候选真获官方通过且该合理旧例失败，才形成已执行的评分假阳性反例；再以依据选择最窄补测，同时保留合理替代实现，不仅检查gold。

我初稿将原例与粗改三方验证合在一个“唯一实验”，优点是同一配方一次获得规格与验收两类证据，适合资源已准备好的私有校准批；缺点是把无需依赖粗改的问题捆在一起，扩大首步候选、评分及回归成本。当前首先要解释公开结果方向，主审的拆分更节省决策成本，所以修改的是建议顺序，I2 的实质判断不变。

这不是所有模型观察的通用闸门：若目标是研究模型如何处理冲突题面，可以记录其解释与实际候选，同时明确当前reward不能独自代表完整公开目标正确性；不必先完成全部扩展诊断。若目标是无歧义的正式能力/训练解释，则需要公开语义及实际actor条件相应明确。具体调度交给协调者；本review不追加统一“全族通过后才允许观察模型”的要求。

## 证据快照与剩余未知

本次读取时 SHA256：

- public_read.md：`053dddc06b6701bfbe5b97b98e0deddf0e048522756684059b94be0f553c39e3`
- analysis_before_history.md：`4af4a43553f63a0ea9c1655d0822b4369a9d626afc382621bf3e5da8c941bc87`
- old_findings_delta.md：`52355bbc81a58153f8357f0ed15213bbb101a2a8713199d1cba191106bcdd535`
- card.md：`35fc5da456ba6787e10a974c6b17c41246e787902737bb6ba205e24d276b4f1d`
- screening_record.json：`06c1278674c234803ca8bc511e4b7a5a31c45580ac6cd8a8ffe6597cef3cbc4a`
- history/refs.json：`c1db522802d8b9550a1f08011df075b817f3bfc8ebac6aac5cec7a1114593a59`
- OLD：`0f1cf549ee3d807610ad48820d55c6837b40a1ffb72bda96558e2bf36bc8feba`

八方面在初判中已有独立覆盖，本阶段逐项复核公开目标、材料/初态、全部参考及选择器、误拒边界、gold/回归、开发条件、交付/评分及关系/用途。仍未知：四文件实际行为、粗改/合法替代解的实测、复杂类型与增量回归、当前actor镜像/消息/资产/权限、重复稳定性、可见答案渠道与跨题关系；没有用“未发现”把这些未知补成pass。没有把重读日志称为独立重跑，也没有以本review批准正式训练/评测。收口应引用本稿补正，而不改封存证据链。完成后报告本稿SHA256并停止。
