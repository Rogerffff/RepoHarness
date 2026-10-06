# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：独立复核初判（第一步，读主审前）

2026-09-25，独立复核者，只做静态审查。我没有参与本题主审；写本文前没有读公开读者、主审产物或历史材料。没有运行代码或容器，也没有修改原件。本文中"C1–C5"是建议做的 CPU 反例，都**未执行**。

## 结论摘要（初判）

1. **评分侧一致、可复现。** 目标键只有 `TestImage.test_open_formats`。noop 的失败原因是 `TypeError: open() got an unexpected keyword argument 'formats'`，gold 得到 55/55。4 条 `material=current` 运行与 2 次 M3 来源镜像参考的结果相同。
2. **最重要：题面和真实目标错配，并会误导解题者。**
   - 题面的核心症状是 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`。这条报错来自 pytest 8.3.4 已经不支持的 `pytest.warns(None)`，只出现在两个**期望 FAILED 的非目标键**中。它与 Pillow 源码无关，gold 也不能消除；期望映射还要求这两个键继续失败。
   - 题面原例和"期望行为"第 1 条说，用 `formats=['JPEG']` 打开 hopper.png 应该正常工作。隐藏断言 L96-98 却要求这一调用抛出 `UnidentifiedImageError`，两者直接冲突。
   - 真实需求是给 `Image.open` 新增一个限制识别格式的 `formats` 参数。这一点只能从题面前提句（"After introducing the `formats` parameter … to restrict the supported image formats"）和例子的调用写法推断出来。
3. **R2E 专有陷阱。**
   - 事实（代码配置）：候选对根 `conftest.py`、`Tests/helper.py`、`setup.cfg` 的改动会被重放到评分环境，并在评分进程中生效。
   - 推断：如果解题者按题面去"修"这个 TypeError，比如让 `pytest.warns(None)` 兼容为只记录警告，两个 FAILED 键就会变成 PASSED，整题得 0 分。
   - 只改 Pillow 源码的修复不会翻转这两个键，包括比 gold 更完整的修复。
4. **隐含要求（低风险）。** `formats=123` 必须抛 `TypeError`（L93-94），题面没有说明。多数自然实现会自然抛出这个错误，但也存在能满足题面全部明示语义、却被判 0 的实现（C2）。
5. **漏测和 gold 缺口（静态推断，不影响本题评分）。**
   - gold 在 `init()` 之前遇到尚未预加载的格式（如 `"TIFF"`），或遇到小写格式名，会抛 `KeyError`。
   - 如果实现把 `formats=None` 写成复制 `ID`，新进程首次打开 TIFF 等格式时会退化。按隐藏测试的执行顺序，这两类问题都测不到。
6. **暂定处置。** 评分侧可以用来做开发诊断。题面需要做公开规格修订，才适合用于训练或正式评测；在修订前，本题应标注为"题面误导：环境噪声被写成症状"。优先下一步是 C1（见 §8）。

## 0. 实际读取范围与暴露

- **角色与方法。** 读了复核卡全文。主审卡在工具中一次显示了全文；按指示，我只把"R2E 的评分口径"和"材料"两节当作口径依据。还读了八方面协议、R2E 当批环境卡和记录模板。第一步用不到 40 项清单，因此没有读。
- **公开包。**
  - 读了 `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`，以及 `worktree_manifest.json` 的头部。
  - `worktree/src/PIL/Image.py` 读了 L340-415、L2170-2210、L2815-2940、L3035-3050、L3148-3175。
  - 读了 `src/PIL/features.py` L214-232，并定位了 `src/PIL/__init__.py` 中 `_plugins` 的位置。
  - 读了根 `conftest.py`、`Tests/conftest.py`、`setup.cfg`；对 `tox.ini` 只做了 grep。
  - 把 `Tests/test_image.py`、`Tests/helper.py` 与对应的隐藏文件做了 diff，读了 `CHANGES.rst` 头部。
  - 在 `Tests/` 中 grep 了 `pytest.warns(None`，在 docs、src、CHANGES 中 grep 了 `formats`，并核对 `Tests/images/hopper.{png,jpg,tif,ppm}` 是否存在以及文件头。
- **私有包。** 读了 `gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`expected_output.json`（包括原始字节）、`hidden_tests/` 下三个文件的全文、`grading_bundle.json`、`validation_bundle.json`。
- **运行原件。**
  - `run_refs.json` 中 4 条 current 账本行：各文件第 37 行，只提取字段。
  - 对应 4 份 `.eval.log` 全文。sha256 都与 `run_refs.json` 一致；09-24 两份复跑日志去掉地址和时间戳后，与 09-23 的两份逐字相同。
  - M3 参考 a1 读了全文，a2 与 a1 归一化 diff 后相同。
- **RH2 源码。** 只用来确认本题是否适用这些机制，不是平台审计。读了：
  - `rh2/src/repoharness2/grading/trusted_projection.py` L1-29
  - `rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py` L1-24、L80-84、L275-278
  - `rh2/src/repoharness2/grading/manager.py` L569-590
- **未读。**
  - OUTPUT_DIR 中的其它文件、`history/`、环境阶段记录与审查目录、`r2e_static_review_20260925/README.md`、`runs/` 下的分析汇总。
  - Jpeg 等插件的实现、52 个回归键中与 `open` 无关的断言细节。
  - 上游 Pillow 的后续提交：无网络，未核对。

## 1. 材料与初始问题

- **材料身份。**
  - base：`608ccd05…`，与题面中的 commit 一致。
  - `gold.patch` 的 sha256 为 `1b14f5d1…`，与两条 gold 账本的 `candidate.patch_sha256` 相同。
  - `expected_output.json` 为 `b62258a3…`，与 `run_refs.current_material.expected_sha256` 及 `grading_bundle` 行一致。
  - `run_tests.sh` 为 `8285765f…`，与日志中的 `RH2_SETUP_ENTRY_SHA256` 一致。
  - 三个隐藏文件的 sha 与 `grading_bundle.row.hidden_test_files` 逐一一致；树摘要 `ee7e03a0…` 见 noop 日志 L3。
  - `revisions.json = []`，`env_recipe` 和 `resource_recipe` 都是 null。
  - 4 条运行使用同一个派生镜像 `sha256:006d96ed…`，配方为 `r2e_derive_v1`，`recipe_sha256` 为 `0da821a1…`。
  - 小注：标为"09-24"的复跑，其 `started_at_utc` 是 `2026-09-23T19:28Z`，应当是本地时区造成的标签差，不影响对应关系。
- **目标键与死键。**
  - noop 账本的 `verdict_diagnostics.expected_match.mismatched = ["TestImage.test_open_formats"]`，`keys_equal=True`，观测到 55 个键。gold 账本的 `match_count=55`。
  - 因此：目标键只有 `test_open_formats`；52 个 PASSED 键是回归键；2 个 FAILED 键在 noop 和 gold 下都失败，是死键。
- **初态失败位置（noop 日志：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_90eb28b3.eval.log`）。**
  - L34-42：第一段 `pytest.raises(TypeError)`（`formats=123`）在 base 上是"空过"。base 的 `open(fp, mode="r")`（`Image.py` L2839）拒收未知关键字，这本身就是 TypeError。
  - 真正的失败在 `r2e_tests/test_1.py:98`，也就是 `formats=["JPEG"]` 那一行，报错仍是 unexpected keyword（L40、L184）。
- **两个 FAILED 键的原因。**
  - 在同一 noop 日志的 L56/L84-87 和 L98/L126-129，TypeError 由 `.venv/lib/python3.9/site-packages/_pytest/recwarn.py:279` 中的 `WarningsChecker.__init__` 抛出。环境是 pytest-8.3.4（L16）。
  - `test_show_deprecation` 在调用被测的 `im.show()` 之前就报错；`test_no_resource_warning_on_save` 在 `Image.open` 之后、`im.save` 之前报错。
  - 其它日志中同样如此：gold 日志 `…rf-all-gold-p_d21a126c.eval.log` 的 L169-170，以及 M3 参考 `…/gold/a1/test_output.txt` 的 L154-156（root 用户、来源镜像）。
- **公开包与隐藏测试的关系。**
  - 隐藏的 `test_1.py` 等于公开的 `Tests/test_image.py` 加上 `test_open_formats`（diff 只多出 L89-107）。`helper.py` 与公开的 `Tests/helper.py` 逐字节相同。
  - 所以这两条失败本来就在公开测试中（公开 `Tests/test_image.py` 的 L601、L768）。解题者一跑公开测试，就会"复现"题面描述的报错。
  - 公开 `Tests/` 下共有 16 个文件使用 `pytest.warns(None)`，说明这是整个仓库在 pytest 8 下的不兼容，不是 Pillow 的 bug。

## 2. 公开需求（只用公开包）

| # | 要求 | 公开依据 | 备注 |
| --- | --- | --- | --- |
| R1 | `Image.open` 接受 `formats=`，值为格式名列表 | 题面标题、描述首句、例子第 1 行 | base 没有这个参数（L2839）；docs、CHANGES、src 中 grep 不到任何 `formats` 说明，**只能从题面得知** |
| R2 | 语义是限制可识别的格式 | "to restrict the supported image formats" | 未匹配时应抛什么，可以从现有 `open` 的结尾推知：`UnidentifiedImageError`（L2930-2932） |
| R3 | 不传参数时行为不变 | 合理旧行为 | — |
| R4 | 原例 `Image.open('hopper.png', formats=['JPEG'])` "should work without issues" | Expected 第 1 条 | **与 R2 矛盾**：hopper.png 是 PNG（文件头 `\x89PNG`），按 R2 限定 JPEG 后不可能打开 |
| R5 | save / show 不应再抛 "exceptions must be derived from Warning, not NoneType" | Expected 第 2、3 条，Actual 两条 | 普通 Python 调用中没有这个症状：`show()` 只有在 `command is not None` 时才发 DeprecationWarning（L2197-2204）；`_show`→`_showxv` 带 `_internal_pillow`，不发警告（L3152-3168）。这条消息来自 pytest。另外 `show()` 本身并未弃用，弃用的是 `command=`（CHANGES.rst "Deprecate Image.show(command=\"...\") #4646"） |

题面没有说明以下几点：是否接受 tuple；`None` 的含义；类型不对时报什么错；格式名是否区分大小写；尚未预加载的格式怎么处理。

`public_hints` 写着 "Do NOT modify test files: grading resets the test files…"。这不是 R2E 的机制（环境卡 §3），在本题会和 P3 叠加。

## 3. 需求与断言的双向映射

| 公开要求 / 旧行为 | 依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- |
| R1+R2：限定 JPEG 时，JPG 文件可以打开 | 标题 / 描述 / 例子 | `test_open_formats` L100-102（list、tuple 各一次；mode RGB，尺寸 128×128） | 覆盖（接受 tuple 属于隐含要求） | gold 日志 L120 PASSED |
| R2：限定 JPEG 时，PNG 文件抛 `UnidentifiedImageError` | 描述中的 "restrict"；L2930 | L96-98 | 覆盖 R2，**与 R4 冲突** | 同上；C3 |
| R3：`formats=None` 等同于不传 | 合理默认 | L104-107 | 覆盖（只测了预加载格式 PNG / JPEG） | 同上 |
| 非 list / tuple 时抛 TypeError | 无公开依据（只有 Python 惯例） | L93-94 | 隐含要求 | noop 上空过；C2 |
| R5：save / show 不抛该 TypeError | Expected 第 2、3 条 | `test_no_resource_warning_on_save` L613-621、`test_show_deprecation` L783-793，期望 **FAILED** | **冲突**：期望映射要求继续失败，只改源码无法改变 | noop L185-186、gold L169-170、M3 L154-155；C1 |
| `open` 的旧行为：bad mode、StringIO、空 BytesIO、Path、文件对象、非独占 fp 不关闭、overrun 报错 | L2862-2932 | `test_bad_mode`、`test_stringio`、`test_invalid_image`、`test_pathlib`、`test_tempfile`、`test_readonly_save`、`test_load_on_nonexclusive_multiframe`、`test_overrun`、`test_registered_extensions*` 等 | 覆盖（受测试顺序影响，见 P5） | 4 条 current 运行都是 PASSED |
| 尚未预加载的格式、小写格式名、新进程中 `formats=None` 首次打开非预加载格式 | R2 的自然推论 | 无 | **缺失** | C4、C5 |

反向核对：L96-98 只能从 R2 找到依据，并且与 R4 冲突；L93-94 没有公开依据；两个 FAILED 键找不到支持"应当失败"的公开依据，反而与 R5 的字面相反。

## 4. R2E 专项

**(a) 非 PASSED 期望键会不会惩罚正确修复？**
- 期望中有 2 个 FAILED 键，原因是 pytest 8 不再支持 `pytest.warns(None)`。
- 只改 Pillow 的修复不会翻转它们，包括比 gold 更完整的修复（大小写处理、在 `init()` 时补救、补文档）。原因是报错发生在进入被测代码之前，或与被测代码无关。
- 能翻转它们的只有改测试基础设施，或在被测包的导入期代码里改 pytest 的行为。这条路在本题是开着的：
  - R2E 评分只替换 `r2e_tests/` 和 `run_tests.sh`（`r2e_grading_scripts.py` L11-12）。
  - R2E 的 `HygieneRules` 中 `test_globs=()`（L275-278）。
  - conftest 和 setup.cfg 的 pytest 段不在控制面内，这是已登记、暂不修的已知不足（`trusted_projection.py` L18-20）；DR4 明确不处理候选在测试进程中运行代码的问题（`r2e_grading_scripts.py` L22-23）。
  - 根 `conftest.py` 通过 `pytest_plugins = ["Tests.helper"]` 在评分进程中加载仓库的 `Tests/helper.py`。
- 后果：如果候选在上述位置把 `pytest.warns(None)` 兼容为只记录警告，两个键都会变成 PASSED，本题得 0 分。题面恰好把这个报错当作要修的症状，公开提示又声称测试文件会被重置，所以诱导风险真实存在，但实际发生率未知。
- 是否翻转也取决于兼容写法：如果把 None 映射成 `Warning`，`test_no_resource_warning_on_save` 可能因为 DID NOT WARN 继续失败。这不改变结论的方向。
- 证据级别：机制来自代码配置加 pytest 语义推断，未执行（C1）。

**(b) 题面描述的报错是否出现在 noop 目标键中？** **没有。**
- 目标键在 noop 下的报错是 `open() got an unexpected keyword argument 'formats'`（noop 日志 L40、L184）。
- 题面引用的报错只出现在两个非目标键中（noop 日志 L85、L127、L185-186），在 gold 下依旧存在（gold 日志 L169-170）。
- 推测：生成题面的模型把环境导致的失败当成了 bug。

**(c) 题面是否泄漏修法？** 程度低。题面给出了新参数名和用途，这相当于需求本身，没有它题目无法求解。它没有给出实现方式、tuple 支持、类型校验，也没有说 `init()` 重试时必须传入 formats。

**(d) 测试支撑与撞键。**
- 只有一个测试文件，55 个键没有撞键：`collected 55 items`（noop 日志 L20），期望也是 55 个。
- 隐藏测试通过 `.helper` 导入随包下发的 helper，不导入仓库自己的测试模块。
- 但根 `conftest.py` 会把仓库的 `Tests/helper.py` 当作插件加载。这是 base 版本，候选可以修改，评分时不会重置。资源路径 `Tests/images/...` 相对于 `/testbed`。
- **搬迁伪影。**
  - 原位置的 `Tests/conftest.py` 中，`pytest_report_header` 会调用 `features.pilinfo()`，进而调用 `Image.init()`（features.py L230）。评分时这个文件不会被加载：日志头部 L15-20 中没有 pilinfo 输出。
  - 因此评分中第一次 `init()` 发生在 `test_open_formats` 内部；而解题者在本地跑 `Tests/test_image.py` 时，会话一开始就已经执行过 `init()`。
  - 影响：对"`init()` 重试时丢掉 formats"这类 bug，评分比本地测试更严格。这是正确检出，不会误伤正确解，但解题者在本地看不到这个差异。
- **ANSI。**
  - 期望键中含有 `\x1b[1m…\x1b[0m`，来源是 `setup.cfg` L12 的 `addopts = -ra --color=yes`。
  - bundle 声明了 `normalization_version=prime_decolor_v1`，账本中的键已经去掉颜色码。这属于共享解析器的口径，本次未复核。

**(e) 时间、随机和资源。**
- `test_effect_noise` 和 `test_effect_spread` 含随机因素，但阈值很宽，6 次运行全部通过。
- 没有时间依赖。内存峰值约 466 MB（账本 `resource.mem_peak_mb`），测试耗时 0.28 s。
- `test_registered_extensions_uninitialized` 会改全局 `Image._initialized`，在默认顺序下结果稳定。
- 总体低风险。

**(f) 材料修订。** 本题没有修订，不适用。

## 5. 问题清单（按影响排序）

| # | 问题 | 影响 | 证据级别 |
| --- | --- | --- | --- |
| P1 | 题面和目标错配，题面症状无法通过修改源码修复 | 高。解题者必须忽略题面的主症状才能得分，训练信号等于奖励"不管题面报错"。gold 也不满足题面期望的字面：它把第 1 条变成了 `UnidentifiedImageError`（这正是 L96-98 要求的）；第 2、3 条所说的报错只在两条测试里出现，gold 下仍然失败，期望映射也要求它失败 | 当前运行日志 + 源码 + 公开测试 |
| P2 | 原例 / Expected 第 1 条与 L96-98 冲突 | 中。C3 的实现方式是"先试 formats，都不匹配再回退到全部格式"：它满足第 1 条，但一定得 0 分。C3 违背了描述中的 "restrict"，所以测试的取舍更有依据；问题在于公开材料内部自相矛盾 | 静态推断，C3 |
| P3 | FAILED 键加上会被重放的测试基础设施，使"按题面修症状"得 0 分 | 中。机制是配置事实，解题者实际会不会这样做未知 | 代码配置 + 推断，C1 |
| P4 | `formats=123` 必须抛 TypeError，没有公开依据 | 低。C2 的写法是把成员检查放进 `_open_core` 原有的 `try`（L2895-2909）：`i not in 123` 抛出的 TypeError 会被 L2905 吞掉，最后抛 `UnidentifiedImageError`，L93-94 失败；这个实现对 list、tuple、None 的行为全部正确。另一种写法把非 list 的值包成 `[formats]`，结果 `OPEN[123]` 抛 `KeyError`：该异常不在 L2905 的捕获元组里，经 L2910-2913 原样抛出 | 静态推断，C2 |
| P5 | 漏测与 gold 缺口 | 低，本题评分不受影响。① `register_open` 会把格式名转成大写（L3048），gold 不转，所以 gold 下 `formats=["jpeg"]` 一定抛 KeyError；`formats=["TIFF"]` 在新进程执行 `init()` 前也抛 KeyError（C5）。② gold 的 `formats = ID` 依赖同一个列表对象在 `init()` 之后被原地追加（L3049）。如果实现写成 `list(ID)`，新进程首次打开 TIFF 等格式会失败。但按隐藏测试的顺序，在这之前 `init()` 总已被 `test_open_formats` 或 `test_invalid_image` 触发，所以测不到（C4）。③ gold 没有更新 docstring，不计分 | 静态推断，C4 / C5 |
| P6 | 两个死键丢失了原有的回归保护 | 低。它们原本保护的行为——`show()` 不带 command 时不告警、带 command 时告警，以及 save 不产生资源告警——在本题评分中没有保护 | 期望映射 + 测试源码 |

池级问题（不是本题特有）：正式 actor 使用来源镜像，在那里 `/r2e_tests` 可读、git main 上有修复提交（环境卡 §2），本题同样受影响，属于 actor 待验。

## 6. 八方面覆盖

| 方面 | 已查 | 未查 / 未知 |
| --- | --- | --- |
| 公开需求 | 题面、提示、base 的 `open` / `show` / `_show`、docs 与 CHANGES 的 grep、公开测试 | actor 实际收到的提示渲染未核 |
| 材料与初始问题 | 摘要链、noop 失败位置、FAILED 键原因、M3 对照 | 上游同一 PR 的后续提交（无网络） |
| 测试是否测到要求 | 目标键的全部断言；测试顺序对 `init()` 路径的影响 | 52 个回归键中只细读了与 `open` 相关的约 10 个 |
| 误拒 | 设计了 C2、C3；核对了 tuple 和关键字形态 | 未执行 |
| 回归与 gold | 逐行读了 gold；插件注册 / `init` 调用链；C4、C5 | 插件实现未读；仓库其它测试文件不参与评分 |
| 开发条件 | brief、环境卡、导入路径观测、公开测试会有 2 条无关失败 | 正式 actor 链路待验 |
| 交付与评分边界 | 投影规则、根 conftest 生效路径、gold 投影只含 `src/PIL/Image.py`、ANSI 与 addopts | 共享解析器的去色实现未复核 |
| 题目关系与用途 | 题面生成方式（推测）；公开测试中有 16 个文件用 `pytest.warns(None)` | 同一 PR 的其它 R2E 题是否也在池中（本角色不能读其它题）；同仓其它题是否有同类题面污染，建议协调者核查 |

## 7. 开发需求（actor 侧）

- **导入。** `python` 指向 `/testbed/.venv/bin/python`，版本 3.9.21（brief L10）。评分侧观测到 PIL 从 `/testbed/src/PIL/__init__.py` 导入（账本 `observations`），因此只改纯 Python 的 `src/PIL/Image.py` 就能生效，不需要重新编译。这是静态推断；actor 侧的导入路径待验。
- **依赖与网络。** 不需要新包；没有 pip，也没有出网（brief L11）。
- **资产。** `Tests/images/hopper.png` 和 `hopper.jpg` 都在工作树中。题面原例写的是 `'hopper.png'`，这个文件不在 `/testbed` 根目录，解题者需要改路径。
- **验证。** 建议用 `python -m pytest Tests/test_image.py -q`。即使修复正确，`test_no_resource_warning_on_save` 和 `test_show_deprecation` 仍会因 pytest 8.3.4 失败，与本题无关。裸 `pytest` 能否运行未核（环境卡只点名 aiohttp 和 numpy 需要 `python -m`）。
- **权限。** agent（uid 54321）可以写 `/testbed`（brief L12）。
- **提交边界。** 只需要改 `src/PIL/Image.py`（gold 投影为 `included_paths=['src/PIL/Image.py']`）。不应改根 `conftest.py`、`Tests/helper.py` 或 `setup.cfg`：在 R2E 中这些改动不会被重置，而且会进入评分。
- **正式链路。** 来源镜像泄漏隐藏测试、conda 前缀和提示措辞三项，都是 actor 待验（环境卡 §2）。

## 8. 暂定处置与建议实验

- **评分侧。** 一致、稳定，可以作为开发诊断题。
- **题面。** 不宜原样用于训练或正式评测，建议做**公开规格修订**：
  - 把题面改写为 `formats` 功能需求：限制可识别的格式；限定后不匹配时沿用 `UnidentifiedImageError`；修正原例的期望行为。
  - 删掉关于 pytest TypeError 的叙述。
  - 题面是否写明 TypeError 校验，由协调者决定。写明可以降低 P4 的误拒，但等于把测试要求搬进题面，需要权衡。
- **可选：测试支撑修订。**
  - 做法：把隐藏测试中两处 `pytest.warns(None)` 改成 pytest 8 下可用的等价写法（例如 `warnings.catch_warnings(record=True)`），期望改为 PASSED。
  - 好处：恢复原有的回归意图，并去掉 P3 陷阱。
  - 代价：这会改变期望映射，需要保存独立版本，并用 noop 和 gold 复核。
- **最小 CPU 实验**（在当前派生镜像上，用 RH2 回放评分，均未执行）：
  - **C1（优先）**：gold 加上根 `conftest.py` 中的兼容 shim，让 `pytest.warns(None)` 只记录不断言。预期两个键由 FAILED 变为 PASSED，得 0 分。
  - **C2**：成员检查放在 `try` 内的非 gold 实现。预期只有 L93-94 失败，得 0 分。
  - **C3**：采用"回退"语义的实现。预期 L97-98 失败，得 0 分。
  - **C4**：把 gold 的 `formats = ID` 改成 `formats = list(ID)`。预期得 1 分；但在新进程中执行 `Image.open("Tests/images/hopper.tif")` 会得到 `UnidentifiedImageError`，说明这一回归没有受到保护。
  - **C5**：用 gold，在新进程中执行 `Image.open("Tests/images/hopper.tif", formats=["TIFF"])` 和 `formats=["jpeg"]`。预期都抛 KeyError（gold 缺口，不计分）。
- **需要真实模型才能回答的问题**（清单 33–36）：在题面误导下，解题者会不会去改 conftest，或花时间追查 pytest 报错？静态阅读答不了。
- **为什么优先 C1。** P1（题面误导）不需要实验就已经成立。C1 成本最低，能判断误导是否还会变成一条"按题面修症状反而得 0"的评分路径。这决定了除公开规格修订之外，是否还必须做测试支撑修订。
