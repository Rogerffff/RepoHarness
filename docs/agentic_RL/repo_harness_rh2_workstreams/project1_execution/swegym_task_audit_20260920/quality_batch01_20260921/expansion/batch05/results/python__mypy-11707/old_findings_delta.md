# python__mypy-11707：自身历史核对差异

协调者先核验并登记 `analysis_before_history.md` 的 SHA256 `4af4a43553f63a0ea9c1655d0822b4369a9d626afc382621bf3e5da8c941bc87`，随后明确授权解封。本阶段只读 `runs/swegym_quality_batch05_20260921_v1/history/python__mypy-11707/refs.json` 及其唯一目标 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-11707.json`（下称旧记录），没有沿旧引用访问其他题或聚合。refs SHA256 为 `c1db522802d8b9550a1f08011df075b817f3bfc8ebac6aac5cec7a1114593a59`；旧记录 SHA256 为 `0f1cf549ee3d807610ad48820d55c6837b40a1ffb72bda96558e2bf36bc8feba`。

本次维持封存初判的两项独立发现与 `needs_review / static_review` 处置。旧记录补充了曾引用上游 hints 的线索，但没有提供可在本次授权范围内核验的 hints 原件；这条转述不作为新决定性证据，也不冒充当前 public_hints。

下列 P、V、E、GLOG、NLOG 与归档 A 的绝对路径见封存初判“引用与材料身份”。所有“新证据”均为先于历史读取而独立读到的原件或源码静态推导，没有新增执行实验。

| 旧主张与位置 | 处置 | 本轮决定性证据与改变理由 |
| --- | --- | --- |
| base、版本、参考 IDs、补丁路径对应；data collector 支持带 check-modules.test 的 nodeid（旧:6–10,21–23,27） | **确认本题部分；跨题部分未核实** | P/base_identity 与 V/grading、host 原账本:193 一致；gold/test patch 与 bundle 逐字一致。P/base/mypy/test/data.py:598–635 与两份原日志的已执行 nodeid 相符。旧记录拿另一题作比较的论证未复核，不需要它来证明本题。 |
| issue 明示两种都接受，方向冲突实质存在（旧:14,29,33,47,57） | **确认冲突，收窄对象** | P/user_prompt:46–70 明示原四个普通 .py 文件应通过；base docs/command_line:568–572 明示改名 from-as 不导出；gold 条件使两个非模块符号均 hidden（semanal:1844–1845,1870–1895）。冲突准确表述为题面字面预期与公开旧契约/gold 的方向冲突。隐藏 stub 断言本身符合公开旧契约，不能仅因“增加错误”就说它直接否定 .py 新语义。 |
| “决定方向的唯一信息只在不可见 hints”“公开材料没有任何反向线索/推不出 F2P”（旧:17–18,29,33,57） | **推翻绝对表述** | 当前 base 的 command_line.rst:568–572 直接列出改名不导出；check-modules.test:1819–1840 公开测试 C as C 可用而 C as D 不可用；semanal:1841–1845 说明禁隐式导出与 stub 使用相同规则。故反向维护路线可从公开仓库提出。题面没有明确确认这一路线的问题仍然存在。 |
| 上游 hints 说“两者都应报错”，引用 PEP 484/python/peps#1630（旧:17,29,47） | **未核实来源** | 唯一可读旧记录是转述。当前 P/public_bundle.json 的 public_hints 为通用开发/环境操作指令，没有这段上游说明。未访问链接、历史源数据或其他 hints 原件，不能确认原话来源、当时可见性或其权威适用范围。旧转述可登记线索，不可直接复制进新公开题面作为已核事实。 |
| “按题面正确作答必然判0”“不改题面诚实求解者不可完成”（旧:33,57） | **推翻必然性；保留歧义风险** | F2P 的来源、包与 util 都是 .pyi；P2P 也只验证 stub。普通 .py 在 no-implicit-reexport 下允许任意改名 as、同时保留并修正 stub 隐藏规则，是可分别实现的静态路线，现有两项参考不能排除其得分。没有证明它真实通过，但足以说明“所有字面解必为0”缺少论证。现有公开旧契约仍要求澄清取舍，不因存在这种路线自动判好题。 |
| gold 只改一个条件、无未交付依赖，原例是否修好需实跑（旧:28,37） | **确认实现范围；补足静态对应，执行仍未知** | gold 全文只收紧 MypyFile 豁免；GLOG:357–383 和 ledger:1 projection 验证该源码交付。X 是类节点、Y 是非模块别名，两个改名均非 public，因此可静态预测 gold 两者拒绝。NLOG 仅证明 stub F2P 初态，不能把原四文件的预测写为已观察结果。 |
| 未强制 isinstance 实现或 helper 名，标准诊断/reveal_type 有依据（旧:34） | **确认有限结论** | 完整 test patch、P2P 及 testcheck/helpers 链只比较对外诊断/类型。未见内部实现绑定。“任何实现都能过”仍应限定为保留这些既有输出语义的等价实现，不作全称保证。 |
| 真子模块正例未入 P2P，回归保护不对称（旧:35–36,48,52） | **确认，并独立细化为 I2** | 实际命令 GLOG:651/NLOG:633 只选 testReExportChildStubs3 与 testNoReExportChildStubs；public check-modules:1879–1911 的两项真子模块正例未选中。封存初判已提出“module_hidden = not module_public”的具体错误简化：静态上满足两参考，却隐藏真正 submod。这是待验证反例，不是已跑出的 reward=1。gold 自身保留了 MypyFile 豁免，不能把测试缺口等同 gold 已回归。 |
| 将多项同族用例及 pep561.test 都补成前置回归（旧:48,51–55） | **保留窄候选；广泛扩充未证必要** | 已直接读子模块、stub、flags、__all__/star、缓存相关片段，最直接的区分点是真子模块正例。未读 pep561.test，不把“最贴近题面”照单接受；没有必要先跑全族再允许任何模型诊断。是否扩充由具体反例及目标语义决定。 |
| 无 stage1/环境未检查（旧:11,39,44） | **当前适用性过时；原 stage1 状态未核实** | 新环境原件 E/{gold,noop}/ledger.jsonl:1 与各 eval log 证明 install-wave1 派生镜像下两项真实执行，gold=1/noop=0，无缺席/跳过，安装、测试及清理闭合。它们是 09-19 grader 重放，不能回填 09-16 stage1，也不能填当前 actor pass。 |
| 选择无歧义，nodeid 可信（旧:42–43） | **确认本次命令与参考命中；旧聚合未复核** | A!spec_vendor.py:134–137,183–197 对 patch case 名构造 -k；GLOG:656–664/NLOG:638–661 实际仅选2、参考全命中。无需访问旧 kcheck_all.txt 或另一题来支撑本题。 |
| test_patch 纯测试、无覆盖风险、additional_exclusions 空（旧:30–31,50） | **确认并限定** | patch 只改 check-modules.test；GLOG:384–424 恢复该官方文件并成功应用 patch；gold projection 仅 semanal.py，源码未被覆盖。不是“所有可能修复均无覆盖风险”：候选对官方 check-modules.test 的修改确会恢复，其他测试名没有统一排除。additional_exclusions 保持空。 |
| 无外部资产/网络需要（旧:40–41） | **确认测试执行阶段；补足准备与 actor 边界** | 内联文件及 module/lib-stub fixtures 足够，真实 grader deny_all 下以离线 wheels 完成 editable install。Python/pytest/build 依赖要在准备期备齐；当前 actor 解释器、读写权、导入路径、镜像修复消费与资产可达性未验。不能将“case 无 URL”当全部准备流程无需资产的证明。 |
| 同文件家族应同侧且非重复（旧:32） | **未核实关系；推翻仅凭同文件分组的充分性** | 本次没有读取任何被提及的其他题、commit 或 patch。不能确认重复或独立，更不能仅凭 check-modules.test/semanal.py 共用路径形成泄漏簇；须未来以具体相同需求/补丁血缘证明。 |
| 题面无泄漏（旧:38） | **确认窄文本观察，扩大结论未知** | 本题 prompt 未含修复源码/答案链接；未检查真实镜像、安装包、Git 可见历史和实际消息，不能据此宣布 actor 全环境无泄漏。 |
| 直接 reject_revision；成本21分钟（旧:57–58） | **不沿用处置或成本** | 本次初判已先于历史给出 needs_review：真实规格冲突需裁决，但旧“无公开线索/必然零分”的主要支撑不成立。token/费用/本轮CPU实验成本没有可归属观测，均用 null；旧21分钟不移植为本次成本。 |

## 对本轮初判的影响

没有回写或推翻封存初判。历史与 I1/I2 有重合，新的决定性论据仍来自本轮独立阅读：公开文档的明确反例、区分 .py/.pyi 的实现自由、具体错误简化的真子模块回归，以及 gold/noop 原始执行链。新增暴露只有上述唯一旧记录；其中关于其他题和外部 hints 的转述按未核实标注，不沿引用扩读。

唯一优先未来 CPU 实验仍是**原四文件 base/gold × Y/X**：记录加载的源码、实际选项、退出码和诊断，区分“字面预期满足”与“按旧规则消除不一致”。预计 base 为 Y 拒绝/X 接受，gold 为两者拒绝；尚未执行。它提供语义裁决证据，不会自行决定哪种公开规格应当生效。I2 的错误简化+真子模块正例是后续窄验证候选；不强制全部诊断及广泛回归都先于任何模型探针。

本阶段严格静态。只写本 delta、card 与 screening_record；reviewer 待复审，actor 条件保持未知。
