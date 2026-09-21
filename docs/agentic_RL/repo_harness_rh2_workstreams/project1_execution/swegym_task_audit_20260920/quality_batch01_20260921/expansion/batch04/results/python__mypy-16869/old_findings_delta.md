# python__mypy-16869：旧调查差异核对

2026-09-21。初稿已由协调者核 SHA256 `0e9064f9f2f19653995f7717c2e894b3d4b8a172d5744166b29029f47341d3f0` 后明确解封。此阶段仅新读 `runs/swegym_quality_batch04_20260921_v1/history/python__mypy-16869/refs.json` 及其唯一 own record：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-16869.json`。未读其引用的其他题、dupidx、聚合或别的旧报告。公开稿与初稿没有回写。

本文件引用的 P/S/Q/E/N/G/A 缩写沿封存初稿，精确原件路径与行号在该稿。旧调查是新增曝光，不能传给 solver。

| 旧主张 | 本轮处置 | 决定性证据与解释 |
| --- | --- | --- |
| check1/2：材料匹配，AliasPrinter缺StarExpr导致崩溃；当时未实跑 | 确认并增强 | Q/grading、validation与public base一致；N:434–525两个F2P实际到达visit_tuple_expr并抛NoneType TypeError，G:462–468六例pass。不是只有gold差异推断。 |
| check3：题面完整，所以pass；且是旧包“最好的一题” | 推翻该pass依据；跨题排名未核实 | check3须核真实solver rendered消息。P/environment_brief明确user_prompt为静态渲染，public_hints注入未知；本轮为unknown。完整复现支持check23，不支持check3。未读其他题，不能确认排名。 |
| check23：公开目标清楚，保留`*Ts`最自然 | 核心目标确认，唯一拼写推断收窄 | 题面清楚要求修crash和保留泛型语义，没有给完整pyi；S/check-typevar-tuple.test:98–121支持Unpack，AliasPrinter:308–315也会规范化Union/Optional。最自然的格式不等于排除等价输出的公开契约。 |
| check24：断言对外输出，因此任何正确实现都能过 | 推翻其充分性；实际误拒仍未核实 | Q/test.patch:55–77固定`Generic[*Ts]`；helpers.py:107–139是清理后的逐行相等。带正确导入的Unpack候选可能满足语义却不匹配。尚无完整合法候选执行证据，最终check24=unknown，保留静态疑点，不冒充已观测误拒。 |
| check25：完整stub断言使硬编码难以通过，覆盖优于其他题 | 不接受其泛化结论；确认核心输出覆盖 | 六例已全读，两F2P只有同一个公共Ts/单参数/D类。完整输出能拒绝无输出，但不能证明名称特化或单项修复不能过；原`_Ts`与混合泛型未覆盖。跨题覆盖排名未核。 |
| check26：四P2P窄，建议全文件作为“最小充分回归” | 覆盖限度确认；扩大范围的必然性未核实 | 实际选中两Unpack和两object，普通Generic、导入别名、NamedTuple/TypedDict等未被六例保护。gold局部递归添加未显示已发生回归。验证范围应随候选影响确定，整文件不是静态证明的最小充分条件。 |
| check27：gold无题外变更/未交付依赖 | 在已查范围确认 | Q/gold仅StarExpr import和递归打印；G六例通过，hash与validation/ledger一致。但原`_Ts`默认声明过滤未改变、原CLI输出未运行，不能据此声明完整输出/所有回归均正确。 |
| check4/17：两个官方测试路径恢复不覆盖源码修复 | 确认 | A::prepared_task_face.py:179–228,298–331和N:162–212核官方恢复2文件/应用成功；gold ledger:1只投影mypy/stubgen.py。additional_exclusions仍空。“所有测试文件统一排除”并非当前规则。 |
| check5：与另一题同文件，建议stubgen整族同侧切分 | 未核实关系；同文件证据不足以形成重复簇 | 未获准/未读取另一题需求、commit或补丁；旧记录自身也说不同缺陷。只能保留待查关系，不把同文件自动升级为重复、家族泄漏或强制切分证据。 |
| check13/issue：缺-n0必须先修，统一为串行 | 作为本题当前阻断已过时；执行差异观察保留 | N:424–430/G:451–457记录Python3.12.4、11 workers、6 items；noop按目标失败、gold全过；ledger记2CPU/4GiB且无stage/cleanup错误。没有证据支持只因和别题不同就改官方命令。串并比较未做、稳定性未证；actor资源仍unknown。 |
| check18/issue：低于3.11可能skip并伪装通过 | 当前已读条件下无该问题；一般parser命题未核实 | 版本guard静态真实，但N/G为3.12.4且两F2P真执行，ledger reference_skipped=[]、reference_missing=[]、noop reward0。本轮未审共享parser对人工skip的全部语义；不以该未发生情形要求改Python/官方flags或新增实验。 |
| check6未查安装；check7/11无外部资产/网络 | 评分侧证据更新；actor仍待验 | E/image.json固定离线wheel；N:349–408/G:376–435显示依赖和editable完整安装。没有任务特有外部服务需求，但base镜像是否向actor消费修复、实际激活/权限/本地资产未验，不能把grader安装当actorpass。 |
| check29：题面无答案链接，所以无泄漏pass | 推翻此项覆盖范围 | check29须核真实actor可用资产。公开base导出不含真实镜像的未跟踪资产/安装包/历史，实际可见性未知。P/public_bundle的public_hints当前非空（通用操作指令，无具体修法），不能沿用“空hints”描述完整输入。未发现显式答案不等于完整资产验核通过。 |
| disposition_hint ready_for_probe；costs.minutes=24 | 不继承 | 静态建议保留needs_review/static_review；有等价输出疑点与actor缺口。旧分钟数是旧审查自报，不计为本轮或真实模型成本；本轮无观测成本均null。 |

**对独立初判的影响：**没有改写核心初判。旧记录本身承认`*Ts`与Unpack存在公开不确定性，却仍把check24填pass，本轮将这项矛盾明确保留。新补充的是逐条处理旧xdist/skip/跨题分组建议的适用性；它们没有取代初稿的`_Ts`过滤边界和名称/组合覆盖问题。

最终只保留一个优先CPU实验：在精确base的隔离副本实现保留语义、导入和正常回归的Unpack规范化候选，先验证公开行为，再用冻结候选比较base/gold/候选的RH2六例结果。具体前置条件和判别标准见初稿末节；本轮未执行任何项目代码/测试，也未改正式题目或评分标准。
