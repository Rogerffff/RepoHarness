# mypy CPU 非作者核查：Falsifier / Simplifier

2026-10-03。完成本批核查；已补核10174第六版正式矩阵完整原件。

## 范围与当前判断

本次按 `review-standards.md` §10.4 的 Falsifier / Simplifier 角色，只核两题当前 CPU 批次的公开要求、材料与已取回原件。已见作者题卡、提案、回读以及 gold/私有候选和测试；**不是 fresh 公开读者**，不替代已有公开静态读题审查。没有启动 CPU、Docker、SSH 或测试，也没有修改共享源码、登记或题卡。

目前未找到足以推翻既有缺口诊断或新增最小护栏依据的反证。原评分确实接受错误源码候选；新增 case 能在私有 root 行为入口区分对应负对照与 gold。15184 嵌套首版曾因格式误拒 gold，第二版已按精确公开 base 的 suite 格式修正，不能删掉首版失败史。

10174 第六版正式四参考已独立回读为 noop0/gold1/bad0，本角色未见阻塞它进入普通 GPU 观察的评分或 CPU 材料问题；后续须使用这次已验证的发布/材料/环境身份，GPU 和实际模型求解仍未验证。15184 尚无正式新材料发布、新五参考成绩或正式 solver 消息交付证据，不能批准普通探针。CPU 原评分、私有行为与 actor 命令检查是三个不同范围，均不增加训练或留出资格。

## 公开依据与对抗候选

| 项目 | 核对原件后得到的事实 | 反证尝试与限制 |
| --- | --- | --- |
| 10174 新 P2P | 精确 base 的 `check-expressions.test:2764` 已有 `1 in ('x', 'y')` 与相同桩；新增仅增加 `--no-strict-optional`。`docs/source/command_line.rst:562` 将 strict-equality 定义为拒绝不重叠比较与成员检查，`:392` 的 no-strict-optional 只放松 Optional/None 检查。 | “允许 no-strict-optional 时关闭一切比较”与公开开关语义不符。候选在 `dangerous_comparison` 增加直接返回 False，不是合法修复。新保护不是从 gold 推导，且不要求指定 gold 实现。 |
| 15184 有效断言 P2P | 精确 base 的 `check-expressions.test:931` 已同时保护 `assert_type(a, int)`、合法 Literal、失败诊断与返回 `builtins.int`；`docs/source/error_code_list.rst:884` 规定推断类型匹配请求类型。 | 负对照保留 gold 文案消歧，同时把 `is_same_type` 条件替换为 True，使 `int/int`、`Literal[42]/Literal[42]` 也报错。这违反既有语义。仅复用 `testAssertType` 已足以发现此退化，另外四个开发 case 无需全部进入评分。 |
| 15184 嵌套 F2P v2 | 公开原题与修订题面均要求同短名歧义使用限定名称；`list[a.C]` 与 `list[b.C]` 只是把公开两个模块的 C 放入既有类型构造器。原 Fail1 本身已经包含 `array.array[int]` 的限定诊断。 | `top_only` 只在最外层 Instance 名同、fullname 不同时收集名称；外层都是 list，内部 C 因而仍有歧义。候选能修原三参考，不代表完成公开消歧目标。新增一个嵌套失败 case 足够针对这一缺口，不需要新增泛型功能要求或扩到 union/unchecked/Self。 |

上述 base 位于 `runs/swegym_quality_batch03_20260921_v1/public/python__mypy-{10174,15184}/base/`。原、新测试补丁的添加正文作静态逐字比较：10174 原 F2P、15184 原三个 case 完整保留。新有效补丁 SHA 分别为 `91ea4e972129deaf770ef9e72aa26d11d9bafca85229eae6931f2b22568322cf`、`e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532`。

## 原正式评分：真实错误接受，未被环境故障替代

下表取自各候选 `ledger.jsonl`、`eval_logs/*.eval.log` 与 `*.diagnostics.json`，没有把包装器返回 0 当成 reward。运行根统一为 `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/`。

| 题／原 job | 候选及源码投影 | 三个实际参考状态 | reward |
| --- | --- | --- | --- |
| 10174／`mypy10174-original-r2-20261002T171442Z-f5b43f` | noop，空投影 | OverlappingAny 失败；两个 UnimportedHintAny 通过 | 0 |
| 同上 | gold，`mypy/meet.py`，patch SHA `7f94c5b7…` | 三项通过 | 1 |
| 同上 | 关闭非 strict-optional 比较，`mypy/checkexpr.py`，SHA `07b2dc85…` | 三项通过 | 1 |
| 15184／`mypy15184-original-r1-20261002T174349Z-51ce62/attempt` | noop，空投影 | Fail1/Fail2 失败；Fail3 通过 | 0 |
| 同上 | gold，`mypy/messages.py`，SHA `365adadc…` | 三项通过 | 1 |
| 同上 | always_reject，`mypy/messages.py`、`mypy/checkexpr.py`，SHA `8e5df3cb…` | 三项通过 | 1 |
| 同上 | top_only，`mypy/messages.py`，SHA `707f1748…` | 三项通过 | 1 |

七份原件均记录 `git_sanitize` HEAD 为各题精确 base，投影只有表中源码，没有测试/fixture 路径。可信测试补丁应用成功、预期文件 1/实际文件 1、保护成功。实际日志有三项选择和三项 PASSED/FAILED，诊断均为 `num_parsed_tests=3`、缺席与 skipped 空、段外解析 0。0.820 节点没有 `.test` 层，1.4 节点有该层，原件与原参考一致。

七份日志中的 `pip install -r test-requirements.txt`、`pip install -e .` 均完成，editable 构建/安装成功，无 `RH2_INSTALL_CMD_FAILED`，安装 rc 为 0；源码观察为 `/testbed/mypy/__init__.py`，runner 前后摘要相同，清理 removed=true。因此 noop 的失败来自目标诊断差异，负对照的 reward=1 也不是缺失参考或基础设施误判。

10174 原矩阵用 `runtime/rh2/.venv/bin/python`；15184 原矩阵及后续诊断用 `runtime_cpu_v2/rh2/.venv/bin/python`。两者不合并成同一运行。10174 初态已有 `test-requirements.txt` 添加 `types-typing-extensions==3.7.3`，noop/gold/bad 都带该环境初态；未观察到候选把它投影进修复。15184 noop 工作区干净。

## 私有 root 行为：判别点而非正式新 reward

原件为 `mypy-private-controls-r3-20261002T173657Z-cdd6d3/` 中各题的 `summary.json`、各变体 `identity.out`、`collect.out`、`case.out`，以及15184的 `nominal.out`、`generic.out`。

- 10174 新 P2P 真实收集一个完整节点。base 与 gold 各 1 passed；bad 为 1 failed，预期有 `int/str` 不重叠诊断而实际为空。失败进到 `assert_string_arrays_equal` 的输出比较，未落到安装/导入错误。
- 15184 私有开发选择精确五项 `testAssertType*`（没有 Self）。base/gold/top_only 各 5 passed；always_reject 为 3 failed、2 passed。`testAssertType` 的实际输出增加 `int/int` 和 `Literal[42]/Literal[42]` 错误，足以证明拟新增唯一正式 P2P 有判别力。这个结果还没有新正式评分语义。
- 15184 nominal 和 generic 复现中各变体 mypy 均退出 1，因为输入本来不匹配。nominal gold/top_only 输出 `a.C/b.C`；generic gold 输出 `list[a.C]/list[b.C]`，base/top_only 仍为 `list[C]/list[C]`。不得用“gold 应退出 0”来验收。

嵌套 v1 原件 `mypy15184-nested-r1-20261002T175423Z-e27fcb/attempt/gold/case.out` 的预期为小写 `list[a.C]`，实际为大写 `List[a.C]`，这是已发生的错误 oracle。精确公开 base 的 `mypy/test/testcheck.py:129` 在非 lowercase 文件强制 `force_uppercase_builtins`，`mypy/messages.py:2409` 使用既有 builtin alias 输出 List。因此 v2 的唯一格式修正有非 gold 来源依据。

v2 原件 `mypy15184-nested-r2-20261002T175739Z-090d84/attempt/` 真实收集一个完整嵌套节点：base/top_only 各 1 failed，实际均为 `List[C]/List[C]`；gold/always_reject 各 1 passed。后者通过符合预期：这个嵌套 F2P 保护失败文案，不能代替有效断言 P2P。所有 variant 补丁应用成功、identity 正确、清理无残留；第二版未以副作用、额外节点或错误退出条件拒绝 gold。

## Actor 与公开说明

直接核 `mypy-actor-r1-20261002T180207Z-3a9dcf/attempt/` 的两题 `prelaunch.json`、`activation_check.json`、`attempt.json`、`captures/*` 及 `harness/trajectory.jsonl` 的实际 tool_result。两题五条命令均为 `identity/public_repro/public_collect/public_regression/tree = 0/1/0/0/0`，tool_result 与捕获输出一致；单项输出最多 603 bytes，低于 200000-byte 截尾阈值。

10174 公开复现实际是 Optional[Any] 误报，公开回归只选 1 项；15184 公开复现实际是 C/C 歧义，公开回归选 6 项，包括 `testTypingSelfAssertType`。后者六项不与私有五项相加，也不当成五个拟正式参考。无候选修复由 actor 本次产生。

两题实测 CC2.1.205、UID54321、2 CPU/4 GiB、确切派生镜像，宿主 binds/mounts 为空；激活解释器位于 testbed，源码导入来自 /testbed。prelaunch 为 activation 文件 root:644、实际 `ACTIVATION_WRITE=DENIED`，初始化和激活成功。actor 与容器/网络/relay/stub 清理均有成功、空残留记录。

`bashenv_denied_for_agent=false` 不能写成全 checks 通过。冻结第五版 `repo/rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py:346` 只搜索 tool_result 中的 `RH2_BASHENV_WRITE=DENIED`；本次公开命令清单没发相应写入命令。它是继承检查未执行，已有 prelaunch 实际拒写证据；没有理由因此扩成全角色隔离审或另发本轮命令。

两题 `public/development_note_20261003.md` 只说明已核解释器、公开复现和公开选测；15184 新题面也没有 gold 函数、私有候选/case 名或隐藏输入。说明 mypy 退出 1 表示类型错误与原件一致。开发控制 prompt 是 `execute exactly the tool calls ...`，不能充作正式新题面已交付给 solver 的证据。

## 10174 第六版正式四参考增量

只补核 `cpu_a_round1/mypy10174-revised-r3-20261002T182535Z-f641d8/` 完整原件。归档 SHA 复算为 `fdf053f08922562526074eacb659d5132b017b167e1a49d9f0c3ed45a9e7e955`；`slot/status.json` 为 finished/rc0，逐题结果取自 `attempt/{noop,gold,bad}/ledger.jsonl`、各 `eval_logs/` 原日志与诊断，而不是 slot/driver 退出码。

| 候选 | 原 F2P | 原两 P2P | 新 P2P | 新正式 reward |
| --- | --- | --- | --- | --- |
| noop | 失败：Optional[Any]误报 | 2通过 | 通过 | 0 |
| gold | 通过 | 2通过 | 通过 | 1 |
| 关闭非 strict-optional 比较 | 通过 | 2通过 | 失败：真正不重叠诊断消失 | 0 |

`bad/eval_logs/evallog_replay-swe-mypy-mypy1017_141d6c38.eval.log:537` 预期为 `Non-overlapping container check (element type: "int", container item type: "str")`，实际为空；`:544` 开始的三个原参考均 PASSED，`:547` 唯一 FAILED 为新增 P2P。错解从原 reward1 降到0的原因确实是新保护，不是额外选择、安装失败或原参考损坏。gold四项真实通过；noop只在原F2P失败。

三份日志实际都是9423 collected／4 selected／9419 deselected；解析均为4项、段外0、missing/skipped空，revision分区中 unaccounted 空。选择串明确加入完整新增case名，两个 UnimportedHintAny 仍以既有子串同时选中，没有额外未评分节点。

材料链已核到原件：`attempt/material_identity.log` 与冻结第六版 registry/public/grading 相符；新 prepare 的 manifest SHA 为 `54ddb36d25290e1daa12a0dfc8e5f58e71ce3b6c3ce8af9f14ca0c5831aa0ffe`，host grading artifact SHA 为 `a9e4d375a3f127a53944f92b4badb48d9a1834e5bd455ac36ff8416ea61f5ea8`，均复算匹配。三份ledger一致使用 public `e1cc57ae…`、grading `b24e7832…`、registry `a49edd07…`、revision `mypy10174-strict-equality-v1`、materials identity `dca86b80…` 和环境包 `a79297ff…`。发布目录为 `runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/`，manifest SHA 为 `ab0a3a13…`。

三份新 FrozenPatch 带本次r3的 execution/attempt身份和同一新 baseline manifest `c600eabe…`，不是把旧产物改绑；HEAD仍为精确base，镜像仍为 `9d63f1dd…`。gold与bad的源patch SHA与原矩阵一致，投影仍分别只含 `mypy/meet.py`、`mypy/checkexpr.py`；payload内容摘要复算匹配，没有测试路径。两项安装均真实完成、安装失败列表空，测试补丁应用/恢复与保护成功、文件1/1、缺失0，mypy导入为/testbed，runner前后摘要一致，三容器清理 removed=true。新job使用runtime_cpu_v2，未将它声称成旧runtime下的同一运行。

因此10174可在上述第六版绑定下进入普通GPU观察；观察要回答实际模型轨迹/求解行为，不能复用CPU桩端点命令结果填作GPU结果，也不能据三候选校准推断总体模型能力。此结论只解除本角色的本题CPU评分核查条件，不替代协调者对实际探针入口及其他既定条件的核销。

## 最小处置、代价与停止条件

原评分缺口通过当前正式 replay-grade CPU 入口实测（`production_observed`，限于该材料版本）。10174 已有第六版取代旧材料；15184 仍待取代原材料。错解被赋 reward=1 会污染该任务奖励，但它不等于已进入训练。候选出现频率未知，没有据此推导模型总体错误率。

最小充分方案就是当前窄修订：10174 加一个有公开依据的 P2P；15184 复用一个有效断言 P2P，并加一个同目标的嵌套 F2P。没有必要新增状态机、owner、retry/fallback，或把另外四个开发回归全部升格。删除任务能止误奖，却丢掉有真实修复信号的任务；简单 fail-stop 也无法拒绝这种完成所有测试仍得1的错解。当前新增拒绝只针对取消真正比较、破坏合法断言或保留同名歧义的源码；未见已证合理修复被新 case 拒绝，其他替代正确补丁仍未知。

成本限于材料登记、既定三/四候选正式矩阵及15184的新题面实际交付，增加正式参考数量不改变 solver 公共任务目标；不应为理论上还可构造的泛型、union、错误处理形式另扩本轮 CPU 或全仓回归。

10174已有新正式三候选四参考完整证据，当前公开目标、候选与新增拒绝原因足够评估，达到本角色停止条件。15184 草案材料与私有 case 证据可用于发布准备，正式发布/矩阵/solver交付未齐时保持 ordinary_probe_ready=false；不重复 fresh 公共静态审，不拓到新共享边界。当前未知项不得填 PASS。
