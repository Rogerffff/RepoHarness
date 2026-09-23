# python__mypy-16869：history 解封前静态调查

2026-09-21；B4 fresh 私有主审。权威根为 `${REPO_ROOT}`。本稿保存后封存，不回写。暂定 `needs_review / static_review`，用途限 `development_diagnostic`；不构成 actor 就绪、训练准入或所有合理解均可接受的证明。

## 范围、身份和证据层次

以下缩写均相对权威根：

- `P = runs/swegym_quality_batch04_20260921_v1/public/python__mypy-16869`，`S = P/base`。
- `Q = runs/swegym_quality_batch04_20260921_v1/private/python__mypy-16869`。
- `E = runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16869`。
- `N = E/noop/eval_logs/evallog_replay-er19-iw1-python___fd19ff5b.eval.log`；`G = E/gold/eval_logs/evallog_replay-er19-iw1-python___13fbae98.eval.log`。
- `A = runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`；以下 `A::member:line` 是只用 `tarfile.extractfile` 读取的归档成员，未解包、导入或执行。

已读指定协议、investigator 角色卡、record_template、actor_environment_card 和本题封存 `public_read.md`。后者 SHA256 实测为 `46fc57ff7a95e8801f87f43d7daafb9d514cc23423922904882e985646928ed8`，与指定值相符。已全读本题 `test.patch`、`gold.patch`、`grading.json`、`validation.json`，并读公开包、关键源码/测试/helper及本题环境原件。

**暴露声明：**已见 gold、隐藏断言和既有 noop/gold 结果；私有初判只对旧质量调查保持顺序隔离，不是 result blind。`Q/environment_record.json` 还附有一个名为 `history` 的环境批次来源字段，已随获准的环境记录看见；未据此读取任何旧质量调查。inventory 仅打印 `common` 和精确 `instance_id=python__mypy-16869` 的 entry；plan 只打印该 ID。未打开本题 `run_refs.json`、`source_refs.json`、quality history、旧报告、其他题 entry 或聚合质量结论。共用归档源码注释中的其他任务示例 ID 只作为代码文本出现，未追查其他任务。

证据严格区分：本稿代码/断言判断为**静态推断**；N/G 和 ledger 为 **2026-09-19 既有真实 RH2 重放**；建议实验均为**未来未执行**。本轮没有项目 import、测试、安装、下载、Docker/SSH、网络、GPU或模型运行。

## 1. 公开目标与初态

题面给出 Python 3.12.0、mypy 1.8.0、`stubgen test.py`，输入为 `from typing import Generic, TypeVarTuple`、`_Ts = TypeVarTuple("_Ts")` 和 `class ClassName(Generic[*_Ts]): pass`。明确目标是处理该星号泛型基类而不发生内部 TypeError，并生成该类的 stub。题面没有给完整期望 `.pyi`，没有规定访问器方法名或唯一解包拼写。

公开合理约束来自 `S/docs/source/stubgen.rst:8–16,50–53` 的公共类型接口/草稿 stub 用途、`S/test-data/unit/stubgen.test:1198–1212` 的普通泛型保留，以及 `1349–1425` 的 TypeVar/ParamSpec/TypeVarTuple 与导入别名保留。删除类、删除泛型基类、吞异常且无输出、把解包参数改成普通 `Ts` 都不是有力的修复。保持所有私有变量定义则不能自动扩成此次硬要求：文档 `165–168` 和旧测试 `297–313` 明确默认过滤私有名称。

公开/私有 base 均为 `8c2ef9dde8aa803e04038427ad84f09664d9d93f`；`P/base_identity.json` 给 tree `ae2a9a48c9cf641dd90d5bbabf3e4f5a6ae6e073`，1454 个已核 blob，无缺失 gitlink/LFS。其导出校验是材料记录，本轮未重算全树。实际评分安装版本为 `1.9.0+dev.8c2ef9...dirty`（N:395–408、G:422–435）；题面报告旧版本与当前 base 名称不同，但同一故障路径在 base 的真实重放成立，不据版本文本差异判错题。

调用链：`generate_stubs` → `generate_asts_for_modules`（parse-only 或 semantic analysis）→ `generate_stub_for_py_module` → `ASTStubGenerator.visit_class_def` → `get_base_types` → `AliasPrinter.visit_index_expr` → `visit_tuple_expr`。对应 `S/mypy/stubgen.py:703–758,1557–1601,1634–1683`。原文件输入经 `collect_build_targets:1414–1421`，测试模块输入加 `no_import=True` 经 `1403–1407`；两者共享后续生成链，不能把模块测试称为逐字原 CLI 重放。

`fastparse.py:1611–1631` 把星号下标解析成 `IndexExpr`/`StarExpr`；`nodes.py:1726–1744` 分派 `visit_star_expr`；base `AliasPrinter:262–340` 没有该方法；`visitor.py:351–359,483–484` 继承空方法默认返回 None，最终 `', '.join(...)` 失败。N:434–479 和 480–525 分别证实两个 F2P 都沿此路径抛出 `TypeError: sequence item 0: expected str instance, NoneType found`。这是原问题的实际失败证据，不只是从 gold 反推 bug；与题面编译版 TypeError 文案不同不影响根因对应。

## 2. 六个实际评分用例和 helper

所有 ID 前缀均为 `mypy/test/teststubgen.py::StubgenPythonSuite::stubgen.test::`。

| ID 后缀 / 角色 | 输入和真实断言 | 测试模式 / 公开依据 | 既有真实执行 |
| --- | --- | --- | --- |
| `testGenericClassTypeVarTuplePy311` / F2P | `TypeVarTuple('Ts')`、`class D(Generic[*Ts])`；输出固定 typing 导入、Ts 声明及 `class D(Generic[*Ts]): ...`（Q/test.patch:55–65） | `--python-version=3.11`；parse-only，no_import；直接覆盖星号崩溃及公开泛型信息保留 | N:434–479 FAIL；G:465 PASS |
| `testGenericClassTypeVarTuplePy311_semanal` / F2P | 与上一项相同的完整输出（Q/test.patch:67–77） | semantic analysis，no_import；覆盖分析后移出的 Generic 基类仍可打印（stubgen.py:753） | N:480–525 FAIL；G:466 PASS |
| `testGenericClassTypeVarTuple` / P2P | typing.Generic + typing_extensions.TypeVarTuple/Unpack，保留 `Generic[Unpack[Ts]]` 和声明/导入（Q/test.patch:29–40） | parse-only；旧支持的显式解包拼写不得退化 | N:528 PASS；G:462 PASS |
| `testGenericClassTypeVarTuple_semanal` / P2P | 同上一项（Q/test.patch:42–53） | semantic analysis；显式解包的第二条路径 | N:531 PASS；G:467 PASS |
| `testObjectBaseClass` / P2P | `class A(object): ...` → `class A: ...`（S/test-data/unit/stubgen.test:1214–1217） | parse-only；get_base_types 既有 object 过滤 | N:529 PASS；G:464 PASS |
| `testObjectBaseClassWithImport` / P2P | `import builtins as b; class A(b.object)` → `class A: ...`，不保留无用 import（同文件:1219–1223） | parse-only；object 别名解析与导入跟踪 | N:530 PASS；G:463 PASS |

测试不是 Mock 或仅检查异常文案。`S/mypy/test/teststubgen.py:685–727` 写入临时 `main.py`，根据 `_semanal` 后缀选择路径，调用 `generate_stubs`，读生成的 `.pyi`，经 `assert_string_arrays_equal` 比较。`add_file:760–767` 在无输出文件时产生明确缺失行，因此单纯跳过类/模块不能满足完整期望。`helpers.py:107–139,217–237` 只清理行尾空格、CR和 driver 路径后比较数组，不做类型语义等价归一化，也不再次解析/类型检查生成的 stub。

fixture范围已读：`data.py:309–320,334–380` 建立每例 TemporaryDirectory 并恢复/清理；`helpers.py:240–253` 暂时添加当前目录到 sys.path；`conftest.py` 注册 mypy.test.data；`mypy/test/config.py` 定位仓库内 test-data 和 tmp。六例没有外部数据 fixture、网络服务、随机数或 Mock 时序要求。

test.patch 还在 `run_case_inner` 增加 `sys.version_info < options.pyversion` 时 `pytest.skip()`（Q/test.patch:8,16–18）；这是测试适配，不是业务源码。3.10 及以下无法将这些新语法用例当成已执行；但本次 N:424/G:451 明确 Python 3.12.4，六例全部实际执行，ledger 的 `reference_skipped=[]`、`reference_missing=[]`。没有把 skip/解析命中冒作 pass。

实际命令是 N:422/G:449：`pytest -rA -k 'testGenericClassTypeVarTuple or testGenericClassTypeVarTuple_semanal or testGenericClassTypeVarTuplePy311 or testGenericClassTypeVarTuplePy311_semanal or testObjectBaseClass'`。`testObjectBaseClassWithImport` 由子串匹配选中。`A::src/repoharness2/envpack/spec_vendor.py:137,183–197` 从 test.patch 中所有 `[case ...]`（包括上下文）拼 `-k`，不是根据 F2P/P2P逐一运行 nodeid。日志的 `11 workers [6 items]` 及六个状态与 grading.json 完全对应；公开普通 `testGenericClass`、类型变量别名及其余 AliasPrinter 调用者并未纳入该评分命令。

## 3. 需求—断言双向映射

| 公开需求或合理旧行为 | 公开依据 | 对应断言 | 覆盖判断 / 证据或缺口 |
| --- | --- | --- | --- |
| 星号泛型类不崩溃且实际生成 | 题面原例、stubgen 公开用途 | 两个 Py311 F2P 的完整 D 类输出 | 核心路径覆盖；真实 noop/gold 差异确认。原 `_Ts` / `ClassName` /文件 CLI 被改成 Ts / D /模块 helper，非原例逐字覆盖 |
| 保留可变参数解包的类型含义 | 普通 Generic 旧测试；check-typevar-tuple.test:98–121 | F2P 固定 `Generic[*Ts]`，P2P 固定 `Generic[Unpack[Ts]]` | 有实质语义断言，但仅字符串；等价 Unpack 输出可能被误拒，待具体替代解实验 |
| 解析和分析两条链均可用 | teststubgen.py:655–713；stubgen.py:1579–1601 | 两对同输入、不同后缀用例 | 已覆盖；不是重复计数成四种语法 |
| 普通 Generic[T]、多参数顺序、导入别名不退化 | stubgen.test:1198–1212,1381–1425；check-typevar-tuple.test:108–112 | 六例中没有普通 T、`T,*Ts`、`*Ts,T`、重命名变量或别名导入 | 部分/缺失；存在公开回归依据，未运行新反例；不据此声称 gold 回归 |
| 保持 object 基类省略及无用导入清理 | stubgen.test:1214–1223 | 两个 Object P2P | 窄回归已实际保护，不能代表 AliasPrinter 全面回归 |
| 原 `_Ts` 输入默认生成结果如何处理私有声明 | 原例；stubgen.rst:165–168；stubgen.py:826–834,1121–1126 | 全部新例使用公开 Ts | 未覆盖且规格边界有疑义：gold 静态仍过滤 `_Ts` 声明，却在基类引用它；应另记输出完整性限度，不能自动等同未修 crash |
| 保持 NamedTuple/TypedDict/dataclass/别名等共享打印器行为 | stubgen.py:719,792–800,886–898,965–984,1045–1049 | 本题参考集中没有这些调用者 | 已追调用点，未读完所有对应测试/全仓；无全回归结论 |
| 不需要新 API、CLI 标志、额外服务或测试源码修复 | 单文件原例；现有生成入口 | 隐藏测试只消费现有 API；gold 只改 stubgen.py | 静态可行，且该文件在 gold ledger 投影保留 |

反向核验：测试要求存在 D 类、Ts 声明及相关 import 有正常 stub 生成和已有泛型行为依据；object 省略有直接公开旧测试依据；固定 `*Ts` 而拒绝等价 `Unpack[Ts]` 没有题面明确约束。精确空行/单引号沿用既有套件约定，暂不单独判缺陷。测试没有绑定 `visit_star_expr` 名、内部对象、Mock 参数或 gold 行数，因此保持同样输出的非 gold 架构实现有空间。

## 4. gold、合法替代路线及具体疑点

`Q/gold.patch` SHA256 实测 `c48adbd28c5b5542afb4875ef6be5109a2907ab95cbbae216d8be9e8b879d421`，与 validation 和 gold ledger 一致；只增加 StarExpr import 与 `AliasPrinter.visit_star_expr` 的递归打印 `*{o.expr.accept(self)}`。递归能沿已有名称/成员访问器记录 import（stubgen.py:290–303），不限定 Ts 字面值；非星号访问器没有修改。这与两个真实 F2P 的根因一致，六例通过由 G 证实。更宽边界、原 CLI `_Ts` 和跨调用者回归仍未运行，不能以小补丁宣告全修复。

**合理的非 gold 实现路线：**在类基类的递归序列化/类型表达式层处理 StarExpr，也可规范化成 `Generic[Unpack[Ts]]`；通过 `BaseStubGenerator.add_name('typing.Unpack')` 一类现有导入设施处理 import/同名冲突（stubutil.py:607–615），递归保留内层表达式和参数位置。公开 `check-typevar-tuple.test:98–121` 已证明这种泛型表达法是仓库支持的形式；AliasPrinter 本身也把 Union/Optional 改写成 `|`（stubgen.py:308–315），所以“所有生成语法必须逐字保留来源拼写”不是统一公开契约。该路线没有写成补丁、没有执行；需确认原例、普通泛型、Unpack旧例和导入冲突都正确后，才能用来证实误拒。

- **I-16869-1：等价输出可能遭精确文本误拒（静态疑点，优先实验）。** 若上述候选对 Py311 新例输出 `Generic[Unpack[Ts]]` 并加正确 import，`assert_string_arrays_equal` 必然与隐藏 `Generic[*Ts]` 不同。静态已确认评分只认后一拼写，但尚未提供一个经过执行证明的完整合法候选，因此不是“已观测误拒”。不据此立即改测试或拒绝题目。
- **I-16869-2：原复现和名称/组合泛化覆盖有限（静态事实）。** 两个 F2P 只覆盖单个公共名称 Ts。一个仅处理单项 NameExpr、或更窄只处理 Ts 的不完整修复可能通过六例，却仍在题面 `_Ts` 或混合 `Generic[T,*Ts]` 上失败。这是可区分负对照思路，未编写/运行；不是新发现真实奖励漏洞的宣告。gold 的递归代码本身不表现出这种名称特化。
- **I-16869-3：私有 `_Ts` 声明仍被过滤（静态推断/需求边界）。** 过滤路径在 gold 未变；原例可能得到引用未声明 `_Ts` 的草稿 stub。它说明“无 crash”与“完整可用接口”不同，且六例无法发现；但公开默认过滤和草稿定位使其不能直接上升为本题必须另修的 gold 错误。将原命令输出、`--include-private` 变体和公共 Ts 对照一起留给实验核清。
- **I-16869-4：actor消费修复镜像与实际输入未验（证据缺口）。** 有完整 grader 结果，不代表 solver得到同一离线 wheel、可写解释器或真实消息。见下一节。

## 5. 既有环境事实与逐题开发要求

N/G 的 SHA256 实测分别为 `44113d4526300b34bba9b09012a74dff713f1fd70f0f5031b3e7c3f001438a2c`、`7b6f37747435fb991f2bfe225e9bf873fbad77a6351158523282927eff56a1ce`，与 `Q/environment_record.json`、各 `ledger.jsonl:1` 一致。

既有条件：`install-wave1:python__mypy-16869`，派生 image ID `sha256:5cb7a943ddd7b212706e5413fedc61c8e8cccf3edc8f73e583c06e967b4f2ce1`，原镜像 digest `sha256:37fb1870cc8802ad1f6d3f87ff294181c9dcd86f4d13a7533ea76a875f9a6a02`，scripts digest `sha256:f3e13f2518ab8a2ae6396c156ad5805fd2f106d818b1d9db76991b78d11615df`。`E/image.json` 和 launcher `run_install_wave1.py:30–61` 只添加固定 wheel 目录与 `PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`；无源码/材料/参考绑定覆写。plan 精确 entry 和 image.json 的 pins 包括 setuptools 68.2.2、wheel 0.43.0、typing-extensions 4.8.0、mypy-extensions 1.0.0 等。

N:349–408 / G:376–435 显示测试依赖安装和 editable 安装完成（不是只读最终 rc）；N:295–342 显示评分 shell 激活 conda/testbed，N:424 和 G:451 显示 Python 3.12.4。两 ledger 的 import observation 为 `/testbed/mypy/__init__.py`，只证明包级来源；具体 stubgen/nodes 模块路径和 actor shell 仍应验证。`E/{noop,gold}/ledger.jsonl:1` 记 rh2grader/54322、deny_all、2 CPU/4 GiB/PID512、tmpfs1 GiB、shm64 MiB，解释器前缀可写且 owner=54322。候选补丁以 agent/54321 apply，不等于运行真实 solver。

noop 安装5.339秒、测试19.506秒、2 F2P失败/4 P2P通过、reward0；gold 安装5.339秒、测试18.619秒、2/2 F2P和4/4 P2P通过、reward1。日志摘要分别18.89/18.26秒，是pytest内部时长，与阶段计时口径不同。ledger 的峰值约912.902/880.328 MB，无完整 resource_facts；11 xdist workers 在该历史2 CPU档上完成，不能推断所有 actor资源/稳定性。cleanup removed=true；driver.log最后一行报告无open containers、无cleanup failures。两次 env_qualification=absent，没有因此改写成正式actor验收。

| 操作/资产 | 公开依据 | 既有证据范围 | 缺口与最小未来验证 |
| --- | --- | --- | --- |
| Python及工作区代码可导入 | 题面3.12；setup.py:209–234；mypy-requirements.txt | 上述grader3.12.4、editable成功、包级导入路径 | 在真实actor shell打印sys.executable/version和stubgen/nodes/visitor.__file__，再跑原文件CLI；区分环境错误与目标TypeError |
| star语法和本地typing/typeshed | fastparse.py:1611–1631；stubgen.py:1557–1601；base有本地源码 | 六例在历史grader实际解析/分析 | actor至少能解析3.11星号下标；建议3.12；验证typeshed/test-data可读，不要求公网资料 |
| pytest、xdist、临时输出可写 | pyproject.toml:89–110；conftest.py；data.py:334–380 | 历史grader pytest7.4.2/xdist3.3.1、六例完成 | actor运行公开窄回归可用 `python -m pytest -n0 mypy/test/teststubgen.py -k 'GenericClass or TypeVar or PrivateVar or AliasPullsImport'`；本轮未执行 |
| 如需editable重装，离线构建依赖/前缀权限 | pyproject.toml:1–16；setup.py:88–96,178–179 | grader修复镜像提供wheel并允许写conda前缀 | actor镜像消费路径、wheel可读、解释器可写未验；不假设必须重装，也不把grader权限搬给actor。纯Python默认不需C编译/GPU |
| 资产与服务 | 单文件复现；本地typeshed/测试数据 | 本题没有发现运行期外部服务需求 | 准备阶段可固定依赖；解题/最小测试不需外网、权重、凭据或大型数据 |
| 交付内容 | 合理修复位于mypy/stubgen.py | gold ledger projection included_paths仅该源码，ignored_paths空 | 无证据要求写无法提交或官方恢复覆盖的文件；不增加路径排除 |

inventory 的 common/本题entry明确目标机镜像存在性未核，原summary保留不可达历史`/work`路径，本地对应wheel构建context缺失。它们是未来重放准备缺口，不推翻已有执行，也不证明本题不可解。正式 `rollout_spec_from_view` 仍取public.image（A::prepared_task_face.py:336–350），没有证据已自动采用上述派生镜像。`P/user_prompt.txt`是静态渲染，实际solver消息、public_hints的system注入、工具和激活均未知（check3不能pass；check29不能以grader资产pass）。

## 6. 交付和评分边界

test.patch只修改 `mypy/test/teststubgen.py` 和 `test-data/unit/stubgen.test`，无业务源码。归档 `A::prepared_task_face.py:179–228,298–331` 明确从test.patch触碰路径计算官方文件，恢复到base后应用官方patch，并设置 `test_globs=()`；N:162–212实证恢复2文件、apply_rc0、setup_ok1。它们会覆盖同文件候选测试改动；mypy/stubgen.py不在官方恢复清单中，gold投影并实际生效。

实际候选链 `A::replay_grade.py:293–378` 是agent身份apply、受信基线差分/导出/投影，然后独立grader；不是正式模型交互。这里只核本题合法源码修复的投影适用性。公开hints“全部测试修改永不计分”的泛化已过时，但“不要改测试”操作指令是否进入实际消息未知；本题存在不触碰测试的合理修复，因此没有发现此指令妨碍必要交付。未审计所有可变pytest插件/config控制面、共享parser安全或真实actor镜像泄漏；不得因此填全面安全pass，不扩文件排除规则。

## 7. 八方面覆盖及初步处置

| 方面 | 已查 | 明确保留的未知 |
| --- | --- | --- |
| 公开需求（3、23） | 原例、公开旧行为、hints与说明；核心crash目标清楚 | 真实消息未捕获；新输出规范/私有声明边界 |
| 材料与初态（1、2、27） | base对齐、全test/gold、真实F2P故障路径与gold命中 | 未重算整树或重跑当前环境；原CLI尚无记录 |
| 要求—测试（18–20、25、32） | 六参考逐个、helper、版本skip、真实选择/执行 | 精确语法误拒和非原例泛化；无生成stub语义校验 |
| 合理解（24、28） | 非gold递归路线及Unpack等价路线，明确潜在误拒条件 | 合法替代补丁尚未实现/实际评分 |
| 回归/gold（26、27） | 两object和两Unpack P2P、共享调用者、普通Generic/类型变量公开用例 | 更宽回归及原私有名输出未执行；不声明gold全面正确 |
| 开发条件（6–15） | 本地入口/依赖/资产、离线配方、原始安装与资源记录 | 实际actor镜像、权限/激活/工具、目标机准备 |
| 交付/评分（4、16–17、21–22、29–31） | 官方恢复两路径、源码投影、生效及历史cleanup | 完整安全、泄漏、消息/真实可见资产未验 |
| 关系/用途（5、29–30、37–40） | 任务为局部崩溃修复；没有源码外必需资源；记录privileged曝光 | 未读其他题/历史，不推断重复簇、训练污染、学习价值或模型成功率 |

**初步建议：**保留 `needs_review`，scope=`static_review`；原因是有可定位的公开目标和可信历史运行，但等价输出接受性待证、actor条件待验。当前不建议修改题面/隐藏测试或直接reject，也不将其标为ready_for_probe。无观测的当前模型token/费用/CPU实验成本均为null。

**唯一优先下一实验（未来未执行）：**做一轮小型base/gold/合理替代候选的定点CPU对照，核心是验证“将星号基类规范化为带正确导入的Unpack”的候选。先在隔离复制的精确base验证原`_Ts` CLI不崩溃、公共Ts输出可被mypy解析/类型检查、已有Unpack和普通Generic仍成立，再以同一冻结候选走现有RH2六例评分。原`_Ts`另输出默认和`--include-private`结果以区分私有过滤边界；不要把gold同样遗漏的声明强制算替代解违规。若候选语义/回归成立而F2P只因拼写不同失败，才确认误拒并讨论最小规范/断言修订；若候选不合法或退化，则保留精确断言，继续actor验证。使用已记录派生镜像/相同script digest，或先明确重建等价条件；不要跳过当前目标机路径与镜像准备缺口。

本稿仅写入自身 `analysis_before_history.md`。保存封存后停止，等待协调者明确开放本题history；届时另写delta/card/record，保留本初判。
