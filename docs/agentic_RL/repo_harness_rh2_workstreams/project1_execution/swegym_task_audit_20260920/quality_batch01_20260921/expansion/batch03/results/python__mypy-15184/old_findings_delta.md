# python__mypy-15184 · 历史差分

2026-09-20T21:27:47.992539+00:00。封存初稿SHA256 `30ccec9075c23bf2bb10b687f084f19e1a519cde4b4ab78f3e0587b25ae7b9bd`；父协调者UTC 2026-09-20 21:26:21.983183明确放行。仅打开I/history/python__mypy-15184/refs.json及唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-15184.json`；未扩查raw hints、其它记录或聚合。前题历史中本题路径级热点线索暴露已在封存稿披露；不充当本题证据。初稿未回写。

| 旧主张 | 结论 | 决定性证据与变化 |
|---|---|---|
| 无运行/安装证据 | **过时** | 当前原NL:355-423、GL:379-447完成安装；NL:433-480实际2fail+1pass，GL:457-477三过，ledger第1行奖励0/1、参考2/1、解析3且无缺席。 |
| 原SupportsIndex复现可能已不报错 | **保留待验，独立初稿已识别** | 精确base subtypes.py:251-267,602-605,990-1064支持结构协议proper subtype；原题完整输入没有运行原件。旧上游评论只是该旧记录转述，未读取原raw hints，不能据此宣布本base原例已修复。两个名义类F2P已证明一般诊断缺陷仍在。 |
| protocol等价讨论不是必需需求 | **确认** | user_prompt用perhaps并征求意见；gold不改is_same_type，官方不验该扩展。 |
| __main__.array/嵌套完整名完全无法从公开材料推出 | **推翻** | 公开check-basic.test:69-86已有__main__.Any/List等错误；formatter使用TypeInfo.fullname（messages.py:2412-2415）；本地嵌套class结构和runner模块名也公开。查代码属于合理开发。 |
| 测试实际上锁死format_type_distinctly，源array[int]本身不冲突 | **推翻** | 碰撞比较的是TypeInfo.name，不是整个带参数字符串：双方短名都是array；find_type_overlaps(:2584-2602)在verbosity=0也将两侧fullname加入集合，非提高verbosity的副产物。成对收集冲突并各自格式化可等效实现，无helper调用断言。未证误拒。 |
| 把helper名写入题面，或仅要求两个字符串不同 | **不采用** | 前者不必要地规定实现，后者会放过随意改名/丢参数等不满足fully-qualified目标的结果。不能为保gold或消除旧疑问弱化公开标准。 |
| P2P3阻止一律限定名 | **确认但限定** | 它实际要求array[int]/int，原双角色均过；不是全部回归，也不是正向assert_type成功测试。 |
| assert_type其它行为缺评分回归 | **确认有限范围** | 封存稿已完整读check-expressions:931-990五组、semanal-errors:845-852；它们不在冻结P2P。gold未动判定/返回路径；新增泛型内部同名冲突覆盖限度仍保留。 |
| gold完整且无未交付依赖 | **确认窄证据，不作全域证明** | 原2/1测试通过，已有helper、错误码与句式保留；原题protocol输入及更宽边界未运行。 |
| 新测试缺末尾换行是卫生问题 | **事实确认但非质量阻塞** | test.patch标记无末尾换行；真实收集执行成功，未见影响题义、断言或评分的证据。本轮不修改原件。 |
| 新文件自动收集、-k无过选、身份正确 | **确认** | testcheck.py:35-55目录扫描；原日志实选3，与三参考节点逐项吻合。diagnostics restored=0是新增文件的正常setup，不是漏保护。 |
| 所有test目录统一排除/按唯一新文件断言无重复 | **不采用/未核实** | test_globs=空，official仅精确新文件；旧gold路径统计不能排除合法路径需求。没有具体绕过CPU证据。重复关系需具体需求/补丁证据，不按文件名给pass。 |

初判保持 `needs_review/static_review`：可作为静态开发诊断候选，但actor待验且原题复现应优先核对。旧报告并未提供已执行反例，故不继承“字符串只有gold路线能做到”的标签，也不把其成本分钟数填成当前观测成本。唯一优先CPU仍是base/gold原题程序与既有assert_type窄组；若原例失效，用公开同名类示例修订须单独版本，不照抄隐藏测试到题面。
