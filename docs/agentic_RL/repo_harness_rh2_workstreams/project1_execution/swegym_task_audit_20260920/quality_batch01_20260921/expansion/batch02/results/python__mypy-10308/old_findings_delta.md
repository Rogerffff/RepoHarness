# python__mypy-10308：历史对照

2026-09-21。协调者封存无历史初稿 SHA256 `d93dc4f7fe8fea5d7b5c00c9ba2f679808679a287e859c7e7a716c610192c350` 后，才读取 I2/history/python__mypy-10308/refs.json 所列 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-10308.json`（下称 H）。未修改封存初稿。

沿 H 的原件线索查找：文档同目录的 dupidx/kcheck 文件不存在；实际找到并只取 `runs/env_overnight_20260916/L1_mypy_1/dupidx.txt:4,66`、`kcheck_all.txt:32–35` 本题行。前者给本题 base/test/gold 路径及 subtypes.py 共用路径；后者写两个新增 case、selectors=1、overselect=0。没有把文件名扫描当成已运行 selector 的证据。初次按 H 线索未定位 stage1 原件；协调者随后明确开放 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/python__mypy-10308/{gold,empty}/offline/a1/`（下称 Sg/Se），现已核两侧 eval.sh、status_map.json、关键 test_output 段及 Sg/patch.diff，不再把这些测试事实列为 report-only。另按新门禁只抽取 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:193`（下称 R193）；id/base/version 与本题一致。没有打开 signals、cross_task_leak、p2p 等未被 H 精确引用的文件。

路径 U/P/G/N 与日志简称沿初稿；base/ 为本题精确公开源码。

| H 的主张（检查编号） | 处置 | 新的决定性证据与当前判断 |
| --- | --- | --- |
| base/gold/test 身份、0.820、单 F2P/P2P空（1、2） | **确认** | S2三包第179行与本题包等同；G/N stage 与元数据 hash 核对、Nlog:612–728 的目标 AssertionError 支持初态问题。Sg/Se status_map 与原日志独立确认唯一 F2P 为 PASSED/FAILED；H 的 RESOLVED_FULL/NO 与冻结引用成功/失败相符，但未把它当作 stage1 全套测试干净或当前运行证据。 |
| 原 test patch 缺 object_hashable fixture（1、7） | **确认原版，修复状态过时** | base 无此文件，typing-full 还缺 Hashable；data.py:69–81 确实读取 fixture。既存 materials-v2 已补这两处并保留 stub pin，G/N 审计与日志四文件应用证明覆盖本次修订对照。不能继续要求本轮第一次补同一 fixture，也不能称原 S2 已同步修好。 |
| Hashable 不会被 -k 选中、仅整文件才暴露缺件（1、7、18） | **推翻** | Sg/Se eval.sh:74 原命令就含目标、testHashable 与上下文 -skip 名；Sg log:485、1075–1078 和 Se:446、1242–1245 均为两个实际选中 case，Hashable 两侧 setup/teardown ERROR。修订后 Glog:552–565、Nlog:513–747 也执行两例。kcheck_all:32–35 的 selectors=1 被原命令与收集证据直接推翻。 |
| F2P/P2P 仍不包含 Hashable（25） | **确认** | 原及修订 F2P=1/P2P=0，Hashable 只是执行选集；不能把执行等同奖励保护。其缺件/失败对 reward 的影响需按实际全局状态另判，不能仅看 pytest rc。 |
| 当前 issue 没有 hints_text 中缩小输入与字母序观察（3） | **确认原始 hints 及当前遗漏；不足以判缺必要规格** | R193 的 hints_text 恰1898字符，包含 self 非必要、constraints.py:437 的 inst 断言、P1/P2 缩小输入、a<b 与改 c>b 不崩溃的观察；其 SHA256 为 ba02254369e6ae9d60ba9dc30f2afd0a4e9bdb788b4a4799c7d185eca060a7d9。U/public_bundle、user_prompt 确未带入此段。它提供调试捷径；公开原例、traceback 与 nodes.py:2491–2501 仍能支持调查，不能自动认定不可解。当前 public_hints 只是通用 harness 指示。 |
| 只能推出不崩溃，完全推不出兼容性/诊断（23） | **推翻过强结论** | protocols.rst:6–22 明确成员与兼容类型规则，公开旧泛型方法测试已有相同诊断格式。两方向缺成员/窄参数不兼容均有公开依据。P/test.patch 实际显式 [out] 是9行，不是 H 的10行；p11/p22 是无诊断正例。精确格式仍可研究误拒，但未给案例。 |
| 缺成员 b 消息由 gold 的提前返回特有，因此强制唯一实现（24） | **推翻因果推断；替代解表现未核实** | 新补读公开 `checker.py:4558–4565` 在报告不兼容后统一调用 `report_protocol_problems`；`messages.py:1360–1368,1903–1912` 重新调用 find_member 计算缺成员并输出 b，与 gold guard 的返回位置无直接绑定。:1373–1405 对签名冲突另生成 Expected/Got。H 的递归保护替代解没有补丁/运行原件，不能当成已被误拒。 |
| 只要递归深度保护就是“真正修根因”，gold 只是启发式绕过（24、27、issues） | **推翻标签即证据的判断；正确性仍有限** | gold 先验证成员包含这一结构子类型必要条件，再允许递归假设，保留已有 init/new 忽略规则；注释的 circumvents 不是行为缺陷证明。若仅截断深度而破坏合法递归推断，也不自动是正确替代解。仍需原例/旧回归及替代实现 CPU 对照，初稿不宣称 gold 全面正确。 |
| 零 P2P、存在局部错误实现可能（25、26） | **确认范围，未核实误判** | 初稿列出合法旧行为和具体“仅协变 guard”待验候选；没有运行结果便不能把 P2P空升为 P1 坏题。F2P自身还有两条错误和两个自身赋值正例，H也承认恒False并非充分通过路线。 |
| docstring Fin→Find 是无关改动（27） | **确认，影响低** | gold第三hunk，仅拼写修正，无评分或公开行为影响。无需据此修订题目。 |
| 提前返回使协议 fine-grained 依赖少记（proposed_regression_tests） | **推翻所述直接机制；全量增量行为仍未核** | 原/gold 的 TypeState.record_protocol_subtype_check 都位于新 guard 前；新补读 `typestate.py:151–158` 一次记录被检查协议和它的全部成员。没有证据表明新 guard 跳过了该记录。其他间接增量影响未穷举，不能反向宣布全无回归。 |
| 没有源码混入 test patch、gold交付不受覆盖（4、17） | **确认并更新范围** | 原patch仅一个.test；既存修订保护四个具体路径，另含fixtures和test-requirements。gold只投影subtypes.py，实际恢复/应用未覆盖它；不能继续概括“只保护一个测试文件”或“所有测试都恢复”。additional_exclusions仍[]。 |
| 与其他题非重复（5） | **未核实** | dupidx:4,66只支持路径共用；不能从同文件或不同hunk描述证明问题关系。H暴露了另题ID与笼统“语义不同”，未读取其原件，本题不据此合格或聚类。 |
| rc_install=0 证明环境可用（6） | **推翻 stage1 推断；修订 grader 与 actor 分开** | Sg/Se eval.sh:14 用分号串安装并以 hash -r 结束，无 set -e；两侧日志明确 editable build isolation 无法获得 setuptools>=40.6.2（Sg:423–436；Se:384–397），最终 install rc 却为0（Sg:461–464；Se:422–425）。目标依然从 /testbed/mypy 跑出真实断言/通过，不能据此称 editable 安装成功。新的 G/N 每步安装、导入和目标日志支持指定派生 image 下 grader 可用；正式 public-image actor/54321 仍未验。 |
| 无网络需要（11） | **确认静态运行需求，配置未验** | 公开复现和相关测试仅本地源码/stubs；预置依赖足够时无需在线服务。不是以case无URL证明实际网络边界、安装供应链或actor已可用。 |
| 无静态泄漏（29） | **只确认本题题面无解法代码；整体未核实** | public导出无未来Git/gold；真实image、预装包/egg-info、可见挂载与访问事实未完整验收。私有case名不能当作已向solver泄漏。 |
| gold/no-op分差来自目标（20） | **确认目标差异，分开解释两代环境** | stage1 Sg:1075 与 Se:1190–1245、两侧 status_map 直接确认目标 gold通过/empty在 constraints.py:437 崩溃；Sg patch.diff 与 P/gold.patch 字节相等。stage1 Hashable两侧缺件且整体 pytest rc=1，不能称全套通过。材料修订后同 image 的 G/N 原账本与日志确认冻结得分1/0、目标差异真实且无缺引用；当前普通非引用失败规则不反向冒充 stage1 全局结果。 |
| 加Hashable进F2P、放宽oracle/补期望输出、同文件全部case是最小充分回归（issues、disposition） | **不采纳自动修改；验证建议缩小** | materials-v2未改变冻结引用；Hashable作为附带成员语义测试可有价值，但issue未把它列成独立要求。精确诊断未有已证误拒，不应为迎合猜测降低oracle或倒填题面。回归应按普通类、递归、变型、泛型推断等调用关系选窄集，同文件全跑既非“最小”也不保证“充分”。 |
| needs_repair和23分钟成本 | **处置过时；成本未核实** | 本轮为needs_review/static_review/development_diagnostic；区分已存在的材料修订、未验actor和未验原例。H的minutes是旧人工估计，不转换成当前wall/token/费用；本轮cost未知=null。 |

读历史后**没有改变**封存初稿的处置、空排除清单、冻结参考或优先实验。新增了更直接反证：通用诊断函数独立产生缺成员消息；协议依赖在guard之前已经记录。它们削弱H的“强制gold”和“必然漏依赖”判断，不能替代真正替代实现/原例/增量回归运行。

历史阶段新增暴露：H的完整旧结论与建议、其对另题共享路径的文字；dupidx本题行中含另题ID；kcheck本题块；第二次明确门禁后 Sg/Se 原始脚本/状态/日志及 R193 原始 hints。没有读其他题结论、批次汇总或未开放的17071/11236历史。追加源码只读本题messages.py:1324–1408,1903–1937、checker.py:4554–4568、typestate.py:151–163。未执行项目代码/测试，也未修改原件。

补充原件完整性：Sg/Se eval.sh 同 SHA256 `bf215e854ef642fad94ec787f90d476672e861253d138481bb8d44a2e56a96a8`；Sg test_output `53ac81d8db4d6e50a769a83afbacdeae63168ea3afe4f8f7ebda88c75555f0d2`，Se `7157b65d9d2ee9d454f60fca427617c63e3edacd25872f67455bc1d8567e8632`；Sg patch `4d9843b52d969a2d73a05a4a00e6c5639a4d49706add7f11a6a2aa1321a3672e`。脚本全文、状态全文、原始 hints 全文已读；日志只读安装、选择、缺件与目标 traceback/汇总相关段，未把两份日志逐行通读或把9461个 collected项目当成实际覆盖。stage1 原件补核不改变初稿处置或恢复边界。
