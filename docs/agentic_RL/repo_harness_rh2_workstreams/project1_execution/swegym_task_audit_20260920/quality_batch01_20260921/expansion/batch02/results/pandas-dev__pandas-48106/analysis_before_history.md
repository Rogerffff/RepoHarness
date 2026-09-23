# pandas-dev__pandas-48106：历史开放前分析

日期：2026-09-21。角色：B2 私有主审。ROOT=`.`；下述仓库路径均相对此 ROOT。只静态读取文件、JSON、原始日志；未执行 pandas、测试、安装、容器、联网或模型，未改源码、测试、gold、reward。未读取历史目录、旧质量结论、reviewer 或其他题内容。公开视角来自本题 `public_read.md`，并自行复读下述决定性源码。材料身份与全 blob 核验沿协调者已完成的记录，不重复全量检查。

方法入口实际为 `swegym_task_audit_20260920/quality_review_protocol_20260920.md`（派发中的无日期同名路径不存在），另读 investigator、record_template、actor_environment_card 及记录定义/40项清单。

## 1. 公开契约、初态与版本

公开 base 为 `8b72297c8799725e98cb2c6aee664325b752194f`，tree 为 `3c8a3b297944a7804b18fceafd7e710af22e729b`。本题 public/grading/validation 的 S2 精确来源均是 `source_refs.json` 所指文件第152行；只提取本题。grading 版本1.5、vendor `swegym_constants_242429c1`。公开镜像 digest 为 `sha256:5300b53bb30e5b29f5425967f370e3a72c42b9bbffeb4c2fd1d3ba831716bdd5`。

Issue 明示：`Series(["a","b","c"], dtype="category").loc[3] = 0` 应保留原值、追加数值0、得到 object dtype；不能仅换异常。标题为 numeric value，故调查范围合理包括数值标量，但题面未逐一规定浮点/复数/类别集合/ordered/空 Series 的组合。题面没有要求改某个内部函数。源码与旧文档支持保留可承载值的 dtype、已存在类别及缺失值赋值规则；新增测试中的类别保留要求主要来自这些公开旧接口，而非标题逐字明示。

实际缺失标签链：`core/series.py:1092–1137` 的 `__setitem__` 可转入 `.loc`；`core/indexing.py:2082–2131` 在非空非object Series上调用 `maybe_promote`，再构造新单元素 Series、`concat_compat` 并保留 name/index。`core/dtypes/cast.py:528–731` 的数值分支可让 CategoricalDtype 到达 `dtype.type(value)`；`core/dtypes/dtypes.py:124–200` 说明其 type 是元类。历史 noop 原始日志在该调用链出现题面 TypeError，非仅由 gold 差异推断。

`public_hints` 的 NON-TEST 指令与 conda 声明分别是操作约束和待验条件；静态 `user_prompt.txt` 不包含所有 hints，不代表公开 bundle 对 actor 不可读。该修复无需修改测试文件，禁改测试指令若适用仍有合理源代码路线。实际CC消息、工具配置及激活未捕获。

## 2. 全部新增断言与需求双向映射

官方 patch 仅改 `pandas/tests/indexing/test_loc.py`：增加 CategoricalDtype 导入和4个测试方法，没有改旧断言或生产源码。四方法共16个 F2P 参数节点、30次 `assert_series_equal` 调用；noop 在失败点后的断言当然不会继续执行。`TestLocWithMultiIndex` 的类名不使这些测试自动使用 MultiIndex，四者都自行构造普通 Series，无Mock、服务或文件fixture。

| 公开要求/合理旧行为 | 公开依据 | 新测试与全部关键断言 | 判断 |
| --- | --- | --- | --- |
| 类别外整数扩容得到object，值及标签保留 | issue完整示例；`indexing.py:2107–2131` | `test_additional_element_to_categorical_series_loc`：`loc[3]=0` 后等于 `Series(["a","b","c",0], dtype="object")` | 直接覆盖原例；未直接枚举其它非零整数、float、complex。 |
| 已有类别扩容尽量保留categorical | `maybe_promote` 最小承载dtype契约；`categorical.rst:764–790,808–812`；同dtype concat路径 | `test_additional_categorical_element_loc`：追加"a"后与categorical期望完整相等 | 公开代码可推知的相邻契约；不要求某内部函数实现。 |
| 可空数值类别扩容/原位写NaN保留类别dtype与未改值 | `categorical.py:1556–1592`；旧 `test_setitem_nan_into_categorical`；`concat_compat` | `test_loc_set_nan_in_categorical_series[UInt8,UInt16,UInt32,UInt64,Int8,Int16,Int32,Int64,Float32,Float64]`：先追加NaN，断言 `[1,2,3,NaN]` 且categories仍用该EA dtype；再把标签1置NaN，断言 `[1,NaN,3,NaN]` | 十种fixture节点均展开。每个有两次比较，并非仅不抛异常。 |
| 字符串类别扩容NA与同位置原位设置一致且保留categorical | 同上既有赋值/NA规则与dtype保留链 | `test_loc_consistency_series_enlarge_set_into[nan,na1,None,na3]` 分别为 `np.nan,pd.NA,None,pd.NaT`：先比较扩容和原位结果，再与直接构造的categorical期望比较 | 四节点的两层断言防止“两边同样错误即通过”。 |

`any_numeric_ea_dtype` 来自公开 `pandas/conftest.py:1524–1541`，参数实际是 `_testing` 的8种nullable整型加Float32/Float64。`assert_series_equal` 默认检查 dtype、索引、name、categorical/category order；实际读其参数和dtype/值/category比较分支。这里没有对内部helper名、调用次数、缓存形状或修复后错误文案的约束。P2P 的 Period KeyError 文案来自既有测试，不是本patch新加要求。

合理非gold路线：只在 Series 缺失标签的构造路径识别 categorical，令已包含值及合适NA沿原categories拼接、类别外数值转object；可以不改 `_maybe_promote`。新断言只观察Series结果，应能接受这种路线（静态判断，未运行替代实现）。自然部分实现如 categorical 一律转object，或仅在原TypeError处退回object，会修好原例但仍破坏已有类别/NA的dtype保留，新增15节点会拒绝。没有发现需要为凑数制作反例的具体误拒或假阳性疑点。未穷尽所有合法解，不把上述判断扩展为完备性证明。

## 3. 执行、冻结参考、实际阅读三套集合

- **实际执行命令**：两run的 `recipe/candidate_test_script.after.sh` 为 `pytest -rA --tb=long pandas/tests/indexing/test_loc.py`。原始日志均收集1045项；gold为1044 passed/1 xfailed，noop为1028 passed/16 failed/1 xfailed。
- **冻结评分参考**：原 `grading.json` 是16 F2P+1020 P2P，全部路径在该模块；不等于1045个执行项。原parser按空白切nodeid，3个含Period文本/空格/反斜杠的P2P别名缺席。`reference_bindings_v1` 将3别名显式绑定7个完整参数node，任一成员缺席则整组不成立，任一失败优先；保留原参考分组，不重写成1045项。
- **实际读过**：全部新测试/F2P、相关23个旧测试方法，对应74条冻结P2P引用；不是读完1020 P2P。23方法包括 `TestLocSetitemWithExpansion` 全部12方法、两个categorical列赋值方法、Period映射方法、setitem dtype/cast2/cast3/consistency/consistency_empty、Series setitem/corner，以及uint8 upcast。展开对应 `ordered`、`index/indices_dict`、`frame_for_consistency`、`string_series` 及索引/Series生成helper。其余P2P仅核集合/状态范围，没有逐测试体审阅。

这些旧测试实际保护空Series扩容、混合标签、日期键/DST、非唯一索引及Series整数保留、nullable列赋值、categorical列赋值、dtype转换及uint8提升；不能因它们数量大就称共享 `maybe_promote` 全部回归已测。额外读了**不在本次评分执行集合**的 `series/indexing/test_setitem.py:459–651`（对象扩容、Timedelta、nullable精度/NA、categorical原位赋值）和 `dtypes/cast/test_promote.py:1–125` 的类型/值比较helper。后者特别检查返回标量类型；该模块没有被此次评分命令运行。

## 4. Gold及回归边界

Gold仅在 `_maybe_promote` 新增CategoricalDtype分支：在categories内或NA时保持dtype/value，否则返回object及转换后的值；无新依赖、无测试修改、无无关文件。它使原例避开元类调用，并令新单元素Series使用原categorical dtype再由 `concat_compat` 保持类别。

读过的调用者还包括 `maybe_upcast` 与 `array_algos/take.py` 的分派：take对EA使用其自身take，共享NumPy提升路径仍保留原代码；gold以具体CategoricalDtype限域，未全局禁用 `_ensure_dtype_type` 或吞异常。未发现明确gold回归；不声称全部category类型、空/ordered/无categories对象或全仓调用者已穷举。其它数值标量、ordered categorical、新标签/名称的组合没有由本F2P直接测全，这些一般覆盖范围未知暂不设硬门。

## 5. 原始环境、配方消费与历史执行证据

环境材料从分析开始纳入；`environment_record.json` 只作导航，以下结论核到原件。

| 原件/条件 | 已核事实及范围 |
| --- | --- |
| `pandas_meta_v3/tasks/pandas-dev__pandas-48106/image.json`、`build.log`、`assets_manifest.json` | base image ID `sha256:0e706113dce17d30fade5723a2a71c162afa253d777fd7fa139c5b89cf05c4b8`，派生ID `sha256:7fce0487dca32159e8480a7426e1f7cddeadeb60fd9687fb41617266f56c0ec7`。从公开digest构建，COPY-only增加10个依赖wheel，非目标pandas替代wheel。COPY本身不证明已消费。 |
| 输入 `pandas_meta_v3/recipes/pandas-dev__pandas-48106.json` 与两run审计 `recipe/recipe.json` | revised_install预装 fastparquet0.8.3/Fiona1.9.6/click-plugins1.1.1/cligj0.7.2/fsspec+s3fs+gcsfs2021.9.0/nbsphinx0.8.9/build1.2.2.post1/pyproject-hooks1.2.0，再源码editable install并 `python -I -m pip check`。审计文件附recipe_sha256是输入字节hash，不能与审计自身hash混用。 |
| `run_compat_cases.py`、`replay_with_install_recipe.py` | runner传 `--recipe`，本题plan的bindings=true导致 `--bindings`；wrapper核original_install后在eval及candidate脚本各替换一次，并将 `parse_log` 替换为绑定入口。两run的before/after与reference审计提供实际消费证据。旧plan本题code_root为 `/work/env_recipe_repair_20260919/resources_v1/code/rh2`；本地同层副本不存在。当前机制核读ROOT/rh2；不冒称当前字节就是旧run的harness快照。 |
| `preflight_pip_check.log` | 10依赖安装并No broken requirements，且root warning明确它是准备预检；不能替代候选用户安装和actor条件。 |
| noop ledger第1行、日志 `...67b00d26.eval.log` | rh2grader/54322、deny_all、2 CPU/4 GiB、tmp1GiB、shm64MiB、可写conda前缀；安装708.235s，rc0，无命令失败标记；日志3118/4866/4872显示依赖、pandas源码构建和pip check，4894收集1045；6968–6983列全16失败，6984摘要，6992 test_rc1。首节点为题面TypeError，余15为dtype为object而期待category。 |
| gold ledger第1行、日志 `...1160016c.eval.log` | 同派生镜像与策略；安装708.967s，rc0，日志3140/4888/4894为依赖、pandas构建、pip check；4916收集1045，5541–5556全部16 F2P PASSED，6005摘要1044 passed/1 xfailed，6013 rc0。投影仅 `pandas/core/dtypes/cast.py`；导入观察为 `/testbed/pandas/__init__.py`、`1.5.0.dev0+1299.g8b72297c87.dirty`。 |
| 输入 `reference_bindings_v1.json` 的本题对象，`reference_bindings.py`，两run `recipe/reference_bindings.json`、`pandas-dev__pandas-48106.reference.json` | 两次raw_node_states的7个完整node均PASSED，原日志分别5969–5975/4990–4996也可对照。original解析1017/1020 P2P且missing3，revised为1020/1020且missing0；F2P仍分别0/16、16/16，最终reward0/1。原冻结参考未改。绑定所列更早baseline日志尚未打开，不把其路径当本轮读过的证据。 |

这些是已有真实RH2的**评分侧**证据，且有日志/账本、完整测试摘要与安装观察相互支撑；不是本轮重新运行、actor开发成功或真实模型解题。`apply_user=agent/54321` 仅指提交应用环节，不能证明曾有该身份的开发会话。历史峰值约1GiB也不能证明未来actor构建预算足够。

## 6. Actor开发需求与最小验证

| 需求 | 公开依据 | 现证据 | 缺口/最小验证（建议未执行） |
| --- | --- | --- | --- |
| 定位及修改Python源码 | 题面堆栈、base调用链 | 明确入口在indexing/cast；gold只改Python | actor实际 `id`/cwd/可写checkout与提交投影待验。无需写官方恢复文件。 |
| 正确解释器、NumPy/dateutil/pytz和pandas C扩展 | `setup.cfg:31–58`、`pandas/__init__.py:5–32` | grader Python3.8.20、pytest8.3.3、NumPy1系及editable源码导入 | 在正式actor shell打印 `sys.executable,pd.__file__,pd.__version__` 并导入 `_libs`；public image不能自动继承派生grader修复。 |
| pytest/Hypothesis及配置插件 | `pyproject.toml:34–64`、conftest直接import | 历史grader plugins包括hypothesis6.112.4/asyncio0.24.0等 | actor窄公开测试的收集与运行待验，导入/配置故障不得混成目标bug。 |
| 构建/安装（仅需要时） | pyproject要求Cython>=0.29.32,<3、setuptools/wheel、NumPy构建依赖 | grader实际editable安装成功，可写prefix属于54322 | actor系统prefix写权限未证；Python源码若现成扩展可用可无需重编。准备固定资产可离线；解题/安装/测试不应假定公网。 |
| 内存数据与外部服务 | 最小例与所读测试 | 无外链、附件、远程服务、GPU或专属数据需求 | 最小例仅内存Series；不需新增资产或额外路径排除。 |

唯一优先下一步：由统一CPU负责人通过**正式actor入口**、公开镜像与UID54321，核实际shell/解释器/包来源，执行公开原例并跑 `pandas/tests/series/indexing/test_setitem.py -q -k 'TestSetitemWithExpansion or categorical'`。初态目标TypeError应与导入/权限错误区分；所需本地依赖与写权限以实际过程记录。若必须选择actor派生配方，先明确加载/消费条件再做同一窄验证。此步骤区分“评分环境已修复”和“开发端实际可用”，不需要额外人为造错补丁。固定grader的oracle语义判断已由本节映射与已有对照支持，但不代替actor验证；本次没有具体oracle疑点要求先另做语义反例。

## 7. 交付、评分与用途边界

当前 `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:304–339` 取官方patch精确路径，`test_globs=()`。本题官方恢复/保护仅 `pandas/tests/indexing/test_loc.py`；不能说“所有test_文件都排除”。源代码cast/indexing合法修复不会被该恢复覆盖。`render_v2_trusted_setup_script` 及历史原始setup证明官方patch应用/文件保护的路径；无需附加排除，`additional_exclusions=[]`。

当前评分静态读 `scoring.parse_eval_log_v2/grading_outcome_fields`、`swegym_parsers.parse_log_pytest`、manager的执行故障入口：普通完整pytest rc1不直接令reward0，冻结F2P/P2P决定正常评分；零解析、全部参考缺席、全局启动/收集/资源异常另走故障判断。本题旧run未显示这些全局故障；未重复整套平台隔离/泄漏审计。公开bundle与base导出没有实际镜像未跟踪文件或全部Git资产，因此不能宣称镜像绝无答案。

未读他题原件，不按同仓/同文件推断题间关系；测试注释GH47677是本题内线索，不构造跨题簇。审查者已暴露gold/官方测试，后续还将读本题历史；不得作为盲解solver上下文。用途仅 `development_diagnostic`，不是训练或正式评测批准。

## 8. 暂定处置与实际阅读范围

暂定 `needs_review / static_review`：静态候选，公开主例、断言、gold及修复后grader对照可解释；等待独立reviewer与真实actor条件。保留非主例dtype语义主要由代码/旧文档推知、一般覆盖有限、旧harness字节快照未本地核对三个边界，不把这些自动设为拒绝门。

实际阅读：完整 public_bundle/user_prompt/environment_brief/base_identity、private grading/validation/test.patch/gold.patch/source_refs/run_refs/environment_record、本题public_read；S2只读第152行。base已展开 `cast.py:515–740,933–986`、`indexing.py:2070–2190`、`dtypes.py:120–200`、`categorical.py:1540–1610`、`concat.py:60–161`、`series.py:1092–1137`、`take.py:45–120`；`test_loc.py:1–75,207–273,365–382,531–560,597–609,1387–1427,1587–1606,1855–2090,2840–2848,2974–2979,3077–3101`，上述其它两个旧测试文件与helpers/fixtures、categorical文档、setup/pyproject/pandas导入。conftest读1–149、295–307、590–656、706–733、1500–1547；`_testing/__init__.py:124–146,335–478`、asserters签名与1000–1138比较分支。未逐层展开所有随机字符串底层/C实现。

原始环境阅读包括本题image/build/assets/preflight、输入recipe、本题plan对象、三个通用脚本、输入bindings本题对象、两run ledger第1行及recipe审计、gold driver.log，原始eval日志的安装、测试启动、所有F2P状态/错误形状、Period节点及终态段。大型日志的其它编译输出/所有P2P文本未逐行阅读。全文文件名扫描有输出截断；另一次定位环境脚本的文件名检索返回其他批次脚本路径，未打开其内容，不计入材料证据或结论。

本文件先保存并由协调者封存SHA；历史开放后改变仅记入 `old_findings_delta.md`，不回写本稿。
