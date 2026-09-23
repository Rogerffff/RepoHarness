# python__mypy-10424：历史前私有主审稿

2026-09-21；主审 investigate_mypy。本文在获准读取本题旧调查前封存，之后不回写。仅做静态阅读与 JSON/散列校验，没有运行 mypy、pytest、安装、容器或模型。

路径约定：R=`${REPO_ROOT}`；P=`R/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424`；V 为同材料根的 `private/python__mypy-10424`；下文源码均相对 `P/base`。运行原件根 E=`R/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424`，G/N 分别为其 `gold`/`noop`；gold 日志名 `evallog_replay-er19-iw1-python___6bca9f92.eval.log`，noop 为 `evallog_replay-er19-iw1-python___bbc494ef.eval.log`，均在各自 `eval_logs` 下。

## 初判与八方面覆盖

公开要求明确，新增测试检查相关类型行为，gold 的五行保护条件有合理依据。原始日志足以说明在 09-19 派生 grader 环境中该 F2P 真实走到诊断比较，base 与 gold 有预期差别。尚不能以此宣布 actor 可用或评分充分。具体未保护旧行为是普通类型比较缩窄；优先做窄 CPU 负对照，暂记 `needs_review / static_review`，用途 `development_diagnostic`。

| 方面 | 已核事实与未查项 |
| --- | --- |
| 公开需求（3、23） | 已读题面、bundle、公开审查、类对象/元类文档及相关旧测试。目标是保留 `Type[C]`，非 `<nothing>`；实际模型请求与工具附加提示未捕获。 |
| 材料与初态（1、2、27） | S2 三份指定第 183 行与本题三 bundle 的 JSON 对象完全相等；test/gold 文件内容与内嵌补丁相等，原始日志散列相等。base 为 `4518b55663bc689646280a0ab2247c4a724bf3c0`。noop 在两个相关分支真实断言失败，非安装或收集失败；未单独运行完整题面示例。 |
| 测试性质（18–20、25、32） | 已展开唯一 F2P 全五断言、collector、临时目录、stub、build 与比较 helper；P2P=0。1 selected 是一个含五断言的数据驱动 case，不能说只检查一个分支；9492 deselected 不算回归执行。 |
| 合理解接受范围（24、28） | 无 gold 文本、函数名或调用次数断言；现有诊断格式有公开依据。可在比较约束层精确跳过类对象/元类的错误缩窄，未必修改 `meet.py`。没有找到需优先验证的误拒案例；未执行替代解。 |
| 回归与 gold（26、27） | 阅读比较/条件约束/binder 取值调用链、普通类型正负比较与 final、TypeType 交集旧测试。gold 只给相交前的 `TypeType + metaclass Instance` 增加保守返回，不修改普通 Instance 或 TypeType/TypeType 分支。未穷举全部缩窄、元类/联合/泛型组合，也未执行更宽回归。 |
| 开发条件（6–15） | 本题没有新资产、业务网络或必需编译。09-19 grader 依赖安装、editable 安装及目标测试成功可核；actor 的激活、权限、源码生效及公共复现待验。安装配方身份见账本，配方原件尚待协调者给路径。 |
| 交付与评分边界（4、16–17、21–22、29–31） | gold 投影仅 `mypy/meet.py`，无忽略；正式恢复 `test-data/unit/check-narrowing.test` 后打 test patch。补丁没有混入普通源码。runner/helper/config 是评分依赖，未做攻击或全平台保护复验；无证据新增排除规则。 |
| 关系与用途（5、29–30、37–40） | 未查其它题、未来 Git 或模型轨迹，不能据同仓同文件推定同族。已见 gold/hidden/environment 汇总与原始日志，全部本题审查产物不得给 solver。静态导出无 `.git` 不证明真实镜像无泄漏。 |

## 公开要求—断言双向映射

唯一冻结参考 F2P 为 `mypy/test/testcheck.py::TypeCheckSuite::testNarrowingUsingMetaclass`。`V/test.patch` 在 `check-narrowing.test` 末尾新增一整个 case；没有修改旧 case，也没有 fixture、Mock 或新增 helper。

| 公开要求或合理旧行为 | 公开依据 | 对应断言/覆盖 | 执行与缺口 |
| --- | --- | --- | --- |
| `type(t) is not M` 后返回另一分支仍应为 `Type[C]` | `P/user_prompt.txt:3–24`；`docs/source/kinds_of_types.rst:577–583` | 新 case 的 `is not M` else 揭示 `Type[__main__.C]`，与原例的存活路径相同；核心覆盖 | N 日志 504、510 为期望与实际 `<nothing>`，G 508 为 case PASS；原例中的 early return 与 `f(D)` 未原样收入测试。 |
| 直接 `is M` 等价正分支不能推成空类型 | 同一题面语义；`checker.py:4232–4233` 否定交换分支 | 新 case 的 `is M` if 揭示 `Type[C]`；覆盖 | N 日志 501、507 出现对应差异。 |
| 未满足元类比较的分支保留原类型 | 子类可用元类；非 final 否定分支逻辑 `checker.py:4026–4033` | `is M` else 与 `is not M` if 均为 `Type[C]`；覆盖旧的负向行为 | N/G 同一完整诊断数组；N 两项本已正确（508–509），可阻止只改成另一错误类型。 |
| 分支合流后保持 `Type[C]` | 函数参数声明、已有 binder 语义 | case 最后一次 reveal 为 `Type[C]`；覆盖 | N 511 正确；这是第五项，不应遗漏。 |
| `D(C, metaclass=M)` 和 `f(D)` 合法，早返回后不误报 | 题面完整示例；类对象文档 | 没有 D、调用或 early return；部分 | 相同 binder/缩窄路径使 gold 很可能修复；这里只作源码推断，最小公开复现可单独核。 |
| 普通 `Any/Union[int,str]` 在 `type(x) is/== int` 的正分支仍为 int，否定侧保留联合 | `check-isinstance.test:2577–2608,2625–2646` | `testTypeEqualsCheck`、`testTypeEqualsCheckUsingIs`、`testTypeEqualsNarrowingUnionWithElse`、`testTypeNotEqualsCheck*`；本题没有参考保护，也没有执行 | 具体缺口：一律从 `find_type_equals_check` 返回空映射会避开本题 bug，但破坏这些旧行为。仅静态推断，未形成实际 RH2 假阳性证据。 |
| final、链式比较及共享 Type 交集旧行为 | `check-isinstance.test:2585–2592,2610–2624,2648–2673`；`testtypes.py:943–950` | 这些旧测试被本题 selector 排除；未评分 | 已阅读相关断言，不把只读或被收集计作通过；gold 的条件范围未直接更改这些普通分支。 |

隐藏测试反查：五条固定输出都来自明确期望及普通控制流合并语义；模块限定名 `__main__.C` 源于 runner 的主模块设置，符合公开旧 reveal 格式。`--strict-optional` 确保 bottom 显示为 `<nothing>`，不是隐藏的新 API 要求。没有强制 intersection types 或特定内部表示。题面没有要求全面解决动态元类或自定义比较运算；`docs/source/metaclasses.rst:103–106` 仍明确这些限制。

## 测试如何真正执行

`conftest.py:3–5` 加载 `mypy.test.data`；`pytest.ini:4,18–22` 配置路径并禁默认类/函数收集。`data.py:528–589` 将 DataSuite 的 `.test` 文件各 `[case ...]` 收集成独立 pytest Item，因此 `.test` 路径本身不是 pytest 节点。`TypeCheckSuite.files` 的第 51 行包含 `check-narrowing.test`；case 没有 skip、增量、平台或额外文件标记。

`data.py:31–81,168–183,445–473` 把每条 `# N:` 变成带源行号的 note，得到 `main:11/13/15/17/18` 五行。它为本 case 不添加外部文件。setup 在 `tempfile.TemporaryDirectory` 中建 `tmp`（262–272）；`testcheck.py:318–361` 默认主模块为 `__main__`、路径 `main`，随后 `run_case_once` 写程序、解析 flags、强制 builtins fixture 与 nonincremental，调用真实 `build.build`（138–208）。它读取 `res.errors`，CompileError 才用 `e.messages`，不会把任意异常当作期望成功。末端比较整段输出数组（215–235），helper 仅规范路径、行尾空白、`can't/cannot`（helpers 44–117、230–250、298–304），不能将 `<nothing>` 规范成 `Type[C]`。

fixture 没继承前一 case 的 `[builtins fixtures/dict.pyi]`：collector 按 case 分割（data 555–578）。新 case 使用 `modulefinder.py:676–684` 的 `lib-stub`；已读默认 `builtins.pyi` 全 22 行（type/object/int 等最小定义）及 `typing.pyi:1–48` 的 Type/Union/Any 特殊定义。`helpers.parse_options:383–399` 加 `--no-site-packages`；本题数据驱动检查不需第三方业务类型包或服务。

## 根因路径与 gold

`visit_if_stmt` 应用两侧映射（checker 3243–3266）；比较分派经 `find_type_equals_check` 把 `type(t)` 的 t 和 M 转成条件约束（3960–4034、4201–4204）。`get_isinstance_type` 从 M 类对象取 M 的 Instance（5309–5335），`conditional_type_map` 在有交叠时给出 `{t: M}`（5044–5083）。表达式从 binder 读取限制后进入 `narrow_declared_type`（checkexpr 4170–4194）。`meet.py:264–285` 已允许默认元类与任意元类交叠，但 `visit_type_type:630–641` 的 Instance 特例仅支持 `builtins.type`，其余落到 bottom，因此产生 `<nothing>`。

gold 只在 `narrow_declared_type` 的 TypeType/TypeType 分支后插入：declared 为 TypeType、narrowed 为 Instance、其 TypeInfo `is_metaclass()` 时返回 declared。它仍先经过非重叠检查及 Union 分解，保留普通缩窄。`nodes.py:2547–2549` 定义元类判定为 type 子类/ABCMeta/fallback-to-any；该谓词在 base 已存在，无缺交付依赖或新外部资产。没有无关源码修改。对原例的正确性有同路径静态支持和等价分支 F2P 的 grader 支持；未把这两者提升为完整原例/所有元类边界已运行。

合理不同路线：只在比较约束生成层对类对象与元类相交时保持原类型，继续为普通实例产生约束。当前行为断言没有迫使它采用 gold 的 `meet.py` 插入点；是否精确保留复杂联合中的其它限制需对应回归核对。无需为形式差异制造误拒结论。

## 原始运行、环境及边界

两份账本均为第 1 行，attempt=1、真实 RH2 replay、grader `rh2grader/54322`、2 CPU/4 GiB、deny_all、派生镜像 `sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08`；不是 public bundle 的原镜像实际 actor 验证。G candidate.patch_sha256 与 validation 一致；N apply_method=noop、included_paths 为空。日志散列分别 `6249d881…d34d73` 与 `536f23ae…b2a28a5`，已用标准库按整文件核对 run_refs 和账本。

N 日志 130–141 确认 base HEAD，唯一初始跟踪差异为 test-requirements.txt 增 `types-typing-extensions==3.7.3`（205–213）；G 另有 gold 的 meet.py（205–230）。因此不是纯干净源码镜像；该环境差异与业务修复分开。G 408–487、N 391–470 显示 requirements、editable 安装、pytest 依赖成功，安装 RC=0；两者 `RH2_OBS_IMPORT_PATH=/testbed/mypy/__init__.py`，此为账本观测，不是所有内部模块导入路径的独立证明。G 497–516：9493 collected、9492 deselected、目标一项 PASS、RC=0；N 480–526：同数量且实际经过 `assert_string_arrays_equal`，目标 FAIL、RC=1，差异正是两处 `<nothing>`。parser 两者均只解析一个测试，missing/skipped/outside_segment 都为空。这里有测试体 traceback 与完整断言差异，不只依赖 parser 标签。未读重复运行，稳定性未知。

G 安装 6.571s、测试 3.781s；N 安装 6.690s、测试 3.496s；峰值约 124.168/123.559 MiB。它们是历史 grader 阶段值，不能相加冒充本审 container wall 或 actor 成本。cleanup removed=true；未由本次检查容器状态。

G 日志 231–271、N 214–254 恢复官方 `test-data/unit/check-narrowing.test` 后应用测试补丁；gold 的 `mypy/meet.py` 正常投影，无忽略。普通源码修复不需改不可提交文件。runner 数据读取还依赖 `mypy/test/data.py`、`testcheck.py`、helper、conftest、pytest.ini 与 fixtures；本次只确认真实历史路径，未证明任意候选不能操控它们。账本 runner_integrity_changed=false 只说明本次 gold/noop 未变。额外 exclusions 保持空。

| 开发需求 | 公开依据 | 已有证据 | actor 缺口与建议验证（未执行） |
| --- | --- | --- | --- |
| 定位源码、解释器与导入 | 比较/meet 调用链；setup.py 194–202 | grader Python 3.9.19、工作区 editable 安装 | 用实际 agent shell 打印 sys.executable 与 mypy/checker/meet 文件路径，再运行 public_read 的 C2 原例；预期修复后 Type[C] 且 f(D) 无新增错误。 |
| pytest collector、fixtures、可写临时目录 | conftest、data 262–272、testcheck 174–207 | 指定 grader 成功收集并运行 | actor 运行公开 `testTypeEqualsNarrowingUnionWithElse` 等，`-n0` 覆盖默认并行；导入或 temp 权限故障与任务语义分开。 |
| 历史依赖及安装 | requirements、pyproject 1–6 | 派生镜像用预置 `/opt/rh2/build-wheels` 完成安装 | 真实 actor 是否消费该派生配方、能否写 conda prefix 未验；没有理由让 solver 运行期下载依赖。 |
| 资产/服务/编译 | repo 自带 stubs；setup.py 77–85,155–156 默认无扩展 | 本 case 无外部文件/Mock/网络 | 准备阶段固定 Python/test 包即可；无必需 GPU、C 编译或业务服务证据。actor assets/PATH 仍须实测。 |
| 文件交付 | gold 仅 meet.py；官方恢复上述 .test | 历史投影保留业务源码 | 禁改测试的 public_hints 是否实际呈现待查；本题有源码-only 合理解，但提示“所有测试修改永不计分”不是当前机制全貌。 |

## 唯一优先 CPU 对照（建议，未执行）

先在固定配方的隔离诊断环境对 **base、gold、一个错误候选** 做同组对照：错误候选仅令 `find_type_equals_check` 一开始返回 `({}, {})`，其它代码不变。每变体先运行题面原例和冻结 F2P，再额外运行公开 `testTypeEqualsNarrowingUnionWithElse`（输入 `x: Union[int,str]; if type(x) is int`，正分支期望 int，else 期望 Union）及 `testTypeEqualsCheckUsingIs`（Any→int）。额外测试单列诊断，不悄悄加入 reward。

可区分结果：若错误候选获得 F2P=1/原 RH2 reward=1，却在公开普通类型 case 将正分支保留为 Union/Any，而 base 与 gold 保持旧期望，才确认一个语义漏测反例；若候选不通过 F2P或旧测试也不是预期，则收回这项具体反例。失败须定位到输出断言，不能以安装/收集失败代替。此实验源于具体旧行为，目的不是因零 P2P 强行判坏题；在结果前只称窄覆盖缺口与静态风险。actor 验证仍是后续使用条件。

## 阅读与暴露记录

已读 investigator、共用八方面协议、环境卡、record template 及其明确引用的 40 项清单/记录约定；清单含通用既有案例举例，不作为本题结论。已读已封存 public_read、本题公开四元文件、私有 grading/test/gold/validation/source_refs/run_refs/environment_record；后者自带 verified_environment_pair 等标签与 checks，已暴露，结论已另查账本日志，不沿其 analysis/history 链接。按 source_refs 仅取 S2 对应第 183 行，没有阅读别题行。

源码实际阅读范围为本文引用的 checker/meet/checkexpr/nodes/modulefinder、测试 collector/parser/helpers/config、旧比较测试、TypeType meet 断言、stubs、相关文档与安装文件。曾有合并输出截断，关键 runner/fixture、原始日志安装和断言片段随后按范围重读；不称读完全部 mypy 或整个 9493 测试。未读 manifest、主计划、method_adjustments、其它角色结论、旧质量报告、未来 Git、任何其它题的材料或环境汇总 analysis/history。未做 actor、替代解、错误候选或真实模型执行。
