# python__mypy-17071：历史对照

初稿 SHA256 `8bd71d787909640b0e6e8eb6e07bfc29c8107f059e08032cc39ce10331ddacf4` 经协调者封存后，才读 I2/history/python__mypy-17071/refs.json 指向的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-17071.json`（H）及本题 environment_record。未回写初稿。路径 U/P/W/G/N/Glog/Nlog 沿初稿。

原件追溯：H说本题不在stage1样本；限定的 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/python__mypy-17071/` 下也未找到文件，不伪造stage1通过或缺失分数。实际找到 `runs/env_overnight_20260916/L1_mypy_2/{prescan,kscan}.json`，只抽本题条目。另仅抽S2/raw/swe_gym_lite_full_f70b1a29.jsonl中本题行，定位为第226行（R226），id/base/version一致。本题environment_record的report/install/policy/image字段与G/N原账本逐项相同；没有跟进其 analysis_149.json 批次链接，不能将环境摘要当替代原件。

| H的主张 | 处置 | 决定性证据与本轮判断 |
|---|---|---|
| 材料身份、两个新增F2P/两个旧P2P、gold/test路径（1、2、4） | 确认，并补真实运行 | 初稿已核S2第212行、base/gold/test、两侧投影与原日志；Nlog:504–524真实多报UNBOUND_TYPEVAR，且str推断已正确。不是仅凭代码推断初态含错 |
| 没有运行证据（materials_refs、6） | 对当前版本过时，不改写当时事实 | prescan本题stage1=null、gold/empty=NO_LOG，限定stage1目录也无原件；09-19 G/N ledger:1及完整目标日志提供派生grader条件下0/1对照。没有真实actor证据，仍不填actor已通过 |
| 题面1638字符=819×2、缩进/import缺失（3） | 确认 | R226 problem_statement 与当前public逐字相同、两半各819字符相等；初稿已按公开惯例说明最小补全。重复影响清晰度但没有互相矛盾的新要求，不自动使任务不可解 |
| hints473字符“重复两遍”，提示往TypeGuard内看；当前未公开（3、29） | 确认内容重复，精化格式与因果 | R226 hints是两个相同的236字符段，中间一个换行（不是把473字按等长两半直接比较）；SHA256=e6b972f27a08e2f9ea078bcd8034522e29b24782e13fcc8cdcf7d844d6d34a0d。含1.9.0仍复现的playground链接及根因方向，两次出现。当前bundle没有该原始hints，只有通用public_hints。未访问链接。无法仅从结果证明具体是何抽取步骤拼接，也未核其全池出现次数 |
| 全池/40题中唯一文件、无重复，且与若干版本邻题相关（5） | 未核实 | H中这些是跨题汇总主张，没有本题允许范围内的语义关系原件；只改不同文件不足以证明非重复。不读邻题或批次清单补证，本题关系unknown |
| TypeIs为自然对称扩展、str为自然结果，所以总体可接受（23） | 保留依据，最终范围未决 | 公开types.py:1802–1803、constraints.py:1020–1037、成对高阶/别名旧例支持对称；但issue仍只明示TypeGuard。保留初稿的TypeGuard-only具体候选，需公开契约裁定及CPU配对，不能由旧“可接受”标签代替判断。str推断有公开返回T语义且no-op已能做到 |
| 局部override更窄、更安全，并一定同样过F2P/P2P（24） | 合理路线确认；通过/安全程度未核实 | 收集器方案与公共visitor方案均可行且测试未指定实现文件。但H无补丁/运行原件，不能写成已验通过或一定更安全；必须保持嵌套/别名等旧行为 |
| 共享visitor影响6个子类、P2P窄（25、26） | 确认静态影响，推翻“只有副作用方向”的排他判断 | 已逐个读调用者；P2P只保护bool表示和TypeIs Union收窄。运行这些case不等于其他visitor消费者“零调用”，缺覆盖结论应指独立行为断言不足。初稿新增了更直接的“关闭check_unbound_return_typevar”候选：已有str结果使其可能满分却漏报公开unbound负例。该具体false-positive假设未跑，不以低覆盖直接判坏题 |
| 应将两测试全文件及semanal/merge/serialize都纳入P2P（issues、proposed_regression_tests） | 不采纳自动扩大奖励 | 共享visitor影响值得窄回归，但H没有证明所列系列是最小/充分集或已有回归。先核公开原例与unbound负例，再按实际候选影响选回归；不修改冻结引用。check-errorcodes的[type-var]负例有直接依据，已在初稿静态读过 |
| gold正确、完整、没有未交付依赖（27） | 对应与最小源码改动确认；完整性措辞过强 | gold两个字段访问与目标链相符、独立投影只该文件、原G/N四引用对照成立。原题补全CLI、共享消费者回归、合理替代未运行；仍是static_review而非全面正确证明 |
| fixtures齐全、无外部依赖、纯离线（7、11） | fixtures与静态服务需求确认；限定运行条件 | exception.pyi及typing_extensions stub已存在、四case真实通过。仍需Python/pytest/构建依赖；G/N成功依赖离线wheel派生image。没有外部服务需求不等于actor依赖或网络边界已验收 |
| 默认-nauto，建议补-n0（18） | 默认和实际并行确认；不自动改配方 | Glog:509–517/Nlog:487–495实际11workers四items，pyproject:111一致；该次未见资源失败。无-n0不是自动失效理由；保持正式配方与开发建议区分，稳定性/资源对照未做 |
| -k无过选、四段nodeid可解析（18、19） | 在本次原件中确认 | kscan本题四行over_select=[]；更直接的G/N日志与账本均为四个精确引用，无missing/skipped/outside。不是只凭文本shape宣称真正执行 |
| 本题两.test受保护，但helper/fixture仍可能改写断言（17、file_boundary） | 精确恢复确认；具体控制面假设待验 | 当前prepared_task_face:312–338 test_globs=()，manager:243–261、594禁区仅.rh2*/rh2/*；Glog:249–262只恢复两.test。补读公开helpers.py:107–139：assert_string_arrays_equal比较后pytest.fail；testcheck.py:195调用它。把helper变为直接return是有代码依据的绕过候选，但H未给真实投影/评分原件，不能说已确认满分 |
| 给mypy/test/*、test-data/*统一加排除（file_rules） | 不采纳自动规则；保持[] | H“40题gold不碰”不证明这些路径不存在合法修复；本轮也未做正反交付验证。控制面问题需负责人验证并按已批规则处理，不因目录名称封死潜在合法变更 |
| 题面无修复链接/代码所以无泄漏（29） | 只确认题面范围；整体未核实 | 当前任务正文不含修复补丁；真实image、缓存、包与mount、访问能力未按actor验收。R226 hints含公开playground调试链接但没进入当前bundle，不等于actor已取答案或全环境无泄漏 |
| ready_for_probe、26分钟 | 处置更新；成本未核实 | 当前needs_review/static_review/development_diagnostic，固定排除[]。H的minutes不是本轮工具观测费用，不转成token、wall、解题成本；未知=null |

历史没有改变初稿的处置、优先原例/负例实验或TypeIs疑义。新增原始hints来源与格式确认，并将旧helper候选沿当前源码细化为另一项待验控制面问题；它不同于初稿“取消诊断”的语义漏判候选，不能相互替代。旧记录的“无运行”已由后来的RH2原件更新，不把stage1或脚本应用gold称作真实actor/盲解。

历史阶段暴露：H全文含另题ID、批次数量及旧建议；只抽本题prescan/kscan条目、R226 hints，读取本题environment_record全文（含状态/check摘要及analysis_149链接名称），未跟进批次链接或其他题结论。新增源码仅helpers.py:107–148、当前manager.py:243–261、590–598。未打开11236历史，未执行任何项目或测试。
