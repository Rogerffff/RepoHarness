# iterative__dvc-9395：历史核对增量

协调者核实前稿后才开放历史。analysis_before_history.md的SHA256=d0e40446c231503234c863bacf13208ea5e2d2ed8eee2b6eee9acdbd4c6071ab，保持不变。

本轮已读history/iterative__dvc-9395/refs.json唯一指定旧记录：
R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-9395.json（H）。
另按H明确引用读本题candidate.diff、旧候选账本第17/40行、对应candidate/default/a1/test_output.txt、旧stage1本题gold/empty status_map和gold test_output的指定错误/summary。R及P/Q/T/GL/NL沿前稿。未看其他题、全批结论或hints历史正文，未运行项目。

旧候选证据记为C=R/runs/env_probe_20260909_final_sync/ledger/logs_cc/iterative__dvc-9395/candidate.diff，CL=R/runs/env_probe_20260909_final_sync/ledger/logs/iterative__dvc-9395/candidate/default/a1/test_output.txt，CB=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/ledger/cc_candidate_grading.jsonl:17、40。CL SHA256=aed853c7b1b95aafe3842a43381467e7948d51f18a6950edf0cca0bb8273639d，与第17行一致；只读CL目标失败栈与summary，不称全轨迹审核。

| 旧主张 | 处理 | 决定性新证据 |
| --- | --- | --- |
| base不具备数据源恢复，材料对应；test patch与gold文件不重合 | 确认 | S2三原行146相等；NL:698–746；GL:169–255；当前投影/恢复范围一致 |
| 只有hints中的最终设计才能确定修法，公开输入不足 | 未核实历史hints内容；不接受不足的必然推论 | 公开需求与现有源码/fixture已足以定位并实现按需恢复。没有义务公开最终内部设计；真实消息注入仍独立待验 |
| test_restore_pull强制“repro开始时拉整份远端run-cache” | 推翻对实现方式的推论；功能边界保留解释空间 | 测试只构造所需记录在远端、在本地缺失，要求不执行命令且恢复产物；不要求拉所有记录或在顶层做。题面已有run-cache能力和“missing and necessary”至少支持按需恢复；是否扩张原窄需求可讨论，不能直接据未点名索引就删除F2P |
| checkout精确3次无公开依据 | 确认静态耦合 | Q/test.patch:81；GL:3607、3614有一次缺hash且不创建文件的pre-pull checkout。已有2次正常restore+commit路线有行为等价可能，但未做新对照 |
| DeepSeek候选已证明合理解因次数被拒 | 推翻其作为次数误拒的实证；保留真实PARTIAL事实 | C仅在非dry数据源/frozen分支按缺失输出pull，不取丢失run-cache。CB第17/40行确为数据源PASS/restore_pullFAIL，但CL:1297–1332是OutputDoesNotExistError(bar)→ReproductionError，失败发生在reproduce调用，尚未到mock_checkout断言。候选缺该测试所需恢复行为，不是已证“只有次数不符” |
| gold import永久失败；应钉pygit2<1.14 | 旧故障确认；当前条件已过时，版本建议被现证替代 | 旧stage1 gold/test_output:598–601确有GIT_OBJ_COMMIT ImportError。当前recipe用1.14.1，GL安装:394–625，import:3644通过且30全过；不存在“永久失败”证据。不能将<1.14猜测当仍需执行的修复 |
| import被从参考排除，故失败被藏起 | 当前参考缺席事实确认；历史因果未核实 | Q/grading不含它，GL/NL额外实际执行，F→P。没有数据集生成过程证据证明是为隐藏该环境失败才剔除；本轮不私自补参考 |
| 新intermediate_out在base过即“无效P2P” | 确认base过，推翻无效判断 | NL:4063、GL:3645均通过；P2P本就保护旧能力，不需F→P判别力。该测试也不阻止echo重算，只说明恢复结果局部保护 |
| P2P27覆盖良好、gold无已知业务问题 | 确认具体参考通过，缩小整体评价 | 全27体已读且原日志均过，但dry测试不加pull；gold新增两处pull越过dry保护。无remote无缺失路径亦无参考。详前稿第4节，不用历史全绿消去新疑点 |
| 旧parser额外键 | 确认旧状态图，当前计数差仍待核 | 旧gold/empty status_map确有Could=ERROR:和dvc.commands.freeze:freeze.py:19=ERROR，旧原日志:981有caplog。当前实际30 vs parser31不能据旧映射确定现多余键；当前全部29参考身份/状态相符 |
| 同包版本/文件不重叠即无题族问题 | 未核实；依据不足 | 版本或文件是否重合不能替代commit/需求派生关系审查；未读其它题，不作同族/独立保证 |
| 别题测试被投影丢弃可证明本题恢复风险 | 不适用 | 本题当前projection包含唯一gold源码，恢复两个纯官方测试；H引用5822不属于本题证据。本轮不跨题查证 |
| needs_repair由于依赖漂移与已有误拒 | 对当前版本不沿用 | 依赖已在引用grader条件修复；次数误拒未证；新gold回归是静态待验，因此needs_review/static_review，不是原题自动reject或当前正式ready |

主审初判的dry、无remote、用户修改交互风险在旧报告未覆盖，继续分别保留：dry与无remote有明确控制流推断，用户修改需外部checkout语义/运行补证。唯一优先实验仍是固定本地remote的base/gold pull+dry文件/缓存快照与dry=False正对照，不改成追逐旧候选的次数差。若以后确认次数误拒，测试修订应采用有公开依据的产物/无重算断言，不能为了保住gold随意放宽为>=2。

前稿中的两个表达限度补充：所提“仅普通source候选可能绕过import参考”只是拟议评分校准，不把额外测试失败直接等同奖励1；不借前题差异证明本题风险。当前没有已执行CPU反例、模型轨迹完整性或actor资格结论。

