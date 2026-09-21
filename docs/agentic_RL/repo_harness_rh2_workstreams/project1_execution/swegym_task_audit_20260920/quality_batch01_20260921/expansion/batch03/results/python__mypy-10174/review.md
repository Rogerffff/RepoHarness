# python__mypy-10174 · B3 独立 reviewer 最终复核

结论：与主审一致，保留 `needs_review / static_review`，用途仅 `development_diagnostic`。官方原题 F2P 的历史失败/通过分差可信，gold 的规范化顺序修复有源码支持；两条 P2P 只检查未导入 Any/any 的提示，不能保护严格比较。最有价值的下一步是一个候选的窄负例对照，而非先扩大到全仓、强制造三个破坏补丁或把静态疑点写成已验证满分错误解。

## 1. 独立性、封存及暴露

权威 ROOT=`.`；P=`ROOT/runs/swegym_quality_batch03_20260921_v1/public/python__mypy-10174`，Q=同根 `private/python__mypy-10174`；源码位置相对 P/base。独立初判 SHA256=`7c3c3267b5688fa42a023c5f7b07bafb4766cf61649d3533ab78f4774236ef5d`。三题整包经协调者 `2026-09-20T21:51:03.612934Z` 正式封存放行之后，才读取本题 public_read、主审 analysis_before_history、old_findings_delta、card、screening_record 有关字段，以及 I3/history/python__mypy-10174/refs.json 唯一指向的旧单题记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-10174.json`。

旧记录出现其它任务名字、全仓统计及 stage1/dupidx/kcheck/p2p_mechanism 路径，已形成文字暴露；没有打开那些文件、其它任务结果或聚合，没有把转述算成已核事实。独立阶段已见本题 environment_record 的 gold/noop 摘要并核精确原运行资料，不称为结果盲审。封存初判未回写。全程仅静态文本/JSON/哈希与归档成员读取，未导入/执行项目、测试、安装、网络、容器、模型或候选。

## 2. 公开需求与全部断言、helper

题面明确的是 `no-strict-optional + strict-equality` 下 `Optional[Any]` 的 tuple 成员检查不应误报，并说 strict optional 开启时已正常。公开 strict-equality 文档同时要求保留真正不重叠的 equality/identity/container 诊断。不能把关闭所有比较检查算作合法修复。inline 配置与 data flags 是语义等效的两种表达，不宜写成“逐字一致”。

| 验收/行为 | 独立复核结论 |
|---|---|
| F2P testOverlappingAnyTypeWithoutStrictOptional | 新增唯一 case，两个 flags、Any/Optional 导入、x 注解和成员条件，加 tuple/typing-full fixtures；没有 E/N/out，因此完整预期错误数组为空，直接对应题意。未赋值 x 不构成运行期缺陷，因为输入只作类型检查。 |
| P2P testUnimportedHintAny | base check-expressions:2771–2774；未导入 Any 的错误和 typing.Any 导入建议各一条，不涉及成员比较。 |
| P2P testUnimportedHintAnyLower | 同文件2777–2780；小写 any 的对应错误和同一建议，不是 Any 与其它类型重叠的对照。 |
| helper/fixture | 独立初判已展开 testcheck/data/helpers 的收集、flags、build 和完整诊断数组比较；tuple.pyi 与 typing-full.pyi 全文已读。tuple/Sequence/Container 的静态成员类型送入真实 checker，没有 Mock、运行时 tuple 操作、外部数据或新增 helper 断言。 |
| 受影响公开行为 | 已查公开严格比较各组及 meet/checkexpr/checker 的收窄调用者；strict optional 正对照、真不重叠负例、直接 Any/None、数值提升、自定义eq/contains、收窄均不在本题两条 P2P 内。未运行这些回归。 |

主审对所有新增断言及两个 P2P 的展开与本人初判一致。旧记录对 P2P 无关性的提醒有依据；它不能反过来抹去两条 P2P 的实际执行，也不能由“空输出”断言本身判定题目无效，问题在缺少行为相反的相关约束。

## 3. base 因果、gold 与合理替代

`meet.py:130–176` 的 is_overlapping_types 在移除非严格 Optional 的 None 前检查直接 Any。`types.py:1777–1783,1801–1806` 可将 Union[Any,None] 规范化为单项 Any；原先的 guard 已错过，后续 proper-subtype 并不将 Any 当任意类型通配。原日志确有该成员检查误报，但未捕获逐函数 trace，内部传播仍按源码推断。

gold 仅把相同的双侧 Any guard 移到上述规范化之后，没有新依赖、错误文案或实现名字约束。strict optional 下规范化块不执行，直接 Any 仍重叠；没有静态证据说 gold 破坏 None、tuple/TypedDict、TypeVar 或收窄。但 guard 位于共享函数，官方三条通过也不证明全部这些行为正确。主审“gold静态合理而回归不全”的区分应保留。

不同实现可以在比较入口完成等效规范化和 Any 处理，或复用统一规范化入口；只要满足公开行为与合法的共享函数约定即可。测试没有规定必须修改 meet.py、必须移动这几行。尚未发现可复现的合理方案误拒，不强制另造第二个正确补丁。

补充精确命名：`meet.py:142–149` 确有一个嵌套 `_is_overlapping_types` wrapper，真正公共入口为外层 `is_overlapping_types`。旧建议不能把二者当作同一插入位置；本次优先实验具体选危险比较入口，避免“随便恒返回True”掩盖路径差异。复读 `checker.py:5304–5321` 也确认 overload 相容性使用 is_overlapping_types_no_promote，不能以一个过宽共享函数补丁替代窄实验。

## 4. 具体漏测路线与唯一优先实验

独立初判和主审都提出同一个较窄的部分修复：在 dangerous_comparison 中，遇 non-strict optional 就直接返回 False。`checkexpr.py:2293–2353` 当前只按 strict_equality 总开关和若干特例决定是否放行，没有“非严格 Optional 就取消全部比较”这项公开行为。该候选预期让原 F2P 的诊断消失，而两条不走比较路径的未导入提示仍成立。

公开旧例 `check-expressions.test:2764–2769` 要求 `if 1 in ('x','y'): pass` 报 int/str 的 Non-overlapping container check。未来把 **同一 no-strict-optional + strict-equality** 显式加入该输入作负对照，base/gold 应保留该诊断；部分修复会丢失。该负例只用公开严格比较要求，不是新加功能或私有实现细节。

建议一次干净 base、gold、该一个候选的固定 grader 实验，同时保存：①原官方 F2P1/P2P2 的得分和逐项状态；②公开同开关负例的诊断/错误码/返回码。若候选原官方得1且漏掉负例，才能记为“已验证错误解满分”；若未得1，应保留实际失败原因并重新判断，不能按预期填结果。候选、negative case、实验均未写入或运行。当前只记具体静态漏测风险。

strict optional 开启的公开正对照可在需要时追加；CLI 应替换输入中的 inline no-strict-optional，不能只在命令行给反向开关。若证实漏测，再独立版本化验收修订，保留原 gold/test/reference/reward/expected 与原运行记录。没有要求全文件/全仓先跑，更没有必需双候选。

## 5. 实际执行、解析、冻结引用分账及选择机制

独立初判已经核精确 base=`c8bae06919674b9846e3ff864b0a44592db888eb`、0.820/spec Python3.9、public/grading/raw row/manifest、gold哈希、原日志/ledger/diagnostics、镜像身份及脚本；最终复核沿用原件证据，不继承旧 stage1 转述。

| 层次 | 已核事实与边界 |
|---|---|
| 执行 | noop原日志 `e59bc664` 收集9422、未选9419、选3；F2P失败、两P2P通过、rc1。gold原日志 `f589d38e` 同命令3通过、rc0。空预期与 Optional[Any]/int 误报的差异明确，不是依赖失败。 |
| 解析 | 原 diagnostics 3个键，段外0、missing/skipped空；不得把9422收集数当执行或评分覆盖。 |
| 冻结参考 | 原 grading 的 F2P1/P2P2，三段历史节点ID与日志一致；gold f2p1/1、noop0/1，P2P均0失败/2总数，reward1/0。不是仅依据进程退出码打分。 |
| selector | 历史 spec_vendor 提取整个 test.patch 的 case 头；上下文包含 testUnimportedHintAny，`-k` 子串又命中 AnyLower，故2个选择词产生3个节点。三者均在冻结参考中，没有额外未评分节点。 |

同意主审收窄旧机制结论：本题可证明邻接上下文标签和子串匹配如何影响**本次执行选择**，不能单凭它证明参考集最初生成的因果，更不能继承“40/40、14题空P2P”统计或全仓风险排名。没有读取旧汇总，未知仍未知。

## 6. 历史 harness、交付及两个环境层次

历史机制来自 baseline.tar.gz 的 spec_vendor、prepared_task_face、replay_grade、scoring 和 swegym_parsers 相关成员，均只通过 extractfile 读取文本，未解包/执行，不拿当前 ROOT/rh2 字节代替。official 只恢复 `test-data/unit/check-expressions.test`；原日志/diagnostics restored=1、test_files=1、apply_rc0、setup/protect成功，gold投影仅mypy/meet.py且ignored=[]。test.patch不混入源码，合法源码修复不被恢复覆盖；test_globs为空，不能说整个测试目录受保护。additional_exclusions=[] 无新实证反对，仍不等于已做完平台控制面审计。

本题 install_wave1 派生镜像 `sha256:1a440521871061d2e8db3fa660c7bf1a225d7fed9ac82d70dbda6cd726af7369` 只提供COPY wheels和ENV，原spec未被recipe/materials/bindings覆盖。离线pins只有 setuptools75.1.0、wheel0.44.0、packaging24.1，不能套用两个1.4任务的9包清单。原spec requirements、editable、随后 `pip install pytest pytest-xdist` 都有原日志成功依据，实际 typed_ast1.4.3、mypy_extensions0.4.4、pytest6.1.2、xdist1.34.0。原preinstall包含types-typing-extensions3.7.3替换，属于已记环境条件，不能改回基础源码后仍声称同条件；本轮未动任何文件。

评分已观察 grader=rh2grader/54322、candidate apply=agent/54321、deny_all、2CPU/4GiB、tmp1GiB、顶层mypy导入位置及一次cleanup成功。正式 actor 的派生镜像消费、shell激活、模块/扩展真实来源、可写权限、工具消息、当前离线资产仍没有验证。旧文档提到Python2不构成本题Python3窄测试的必需前置，新依赖安装也不应默认可联网。

**需修改主审 record 的一句范围：** `formal_actor_and_replay_assets_unverified.proposed_action` 写成了 “Before future CPU use, verify formal actor ...”。固定 grader 的语义诊断只需先确认该次 grader 的身份、源码/依赖和镜像资产等实际条件；不必等待正式 actor 全面验收。正式 actor 验收是后续模型开发门槛，应分别登记。card 的“核正式身份”也宜明确是哪一层。此纠正不降低正式模型准入要求，也不把历史 grader通过冒充actor通过。

将来新 replay 的 prepared summary/manifest 必须从历史 `/work/...` 创建独立重定位副本；本轮不修改原副本、镜像或当前环境，也未确认当前镜像存在和wheel payload齐备。

## 7. 关系、旧结论及用途

旧记录的 needs_repair、18分钟、无泄漏、其它meet任务同族及全仓重建建议均不作为本次已核事实。公开题面无修复代码不等于实际actor的Git对象、缓存、网络和镜像资产无答案，真实模型数据和成本也未知。

本人独立阶段新增的包内代码关系有原件支撑：两个1.4 base 的 `meet.py:300–312` 已含本题“非严格 Optional 规范化后检查Any”的关键结构；15184 base的messages TypeType分支还含15139gold。只证明三个已授权原件间的代码包含，不证明Git祖先、题目重复、污染传播或其它未读任务关系。原任务目标仍分别审查。

审核产物已见私测、gold、环境结果及旧单题结论，不得用作solver公开材料；不据此批准训练/正式评测，不填真实求解成功率或成本。状态仅 `needs_review / static_review`、用途 `development_diagnostic`。

## 8. 未查范围与最终处置建议

未执行候选、公开原CLI、扩展回归、重复/并发或当前镜像/actor检查；未穷尽共享overlap组合、所有调用者/插件/fixtures；未核实际Git/缓存/网络答案资产、独立来源runner或真实模型轨迹。当前没有新CPU成绩、修复实施或验收升级。

建议协调者保留具体比较负例的优先校准任务，区分评分历史已证事实、静态候选预测和未来CPU条件，并将正式actor门槛从全部CPU实验前置中移出。原gold和局部评分分差可解释，回归缺口也真实存在；两者同时保留，不互相替代。
