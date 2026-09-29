# pandas-dev__pandas-56849：公开视角静态审阅

依据仅为指定 `roles/public_reader.md` 与本题 `PUBLIC_DIR`。下文相对路径均相对于 `runs/swegym_quality_batch02_20260921_v2/public/pandas-dev__pandas-56849/`。未运行项目代码或测试、安装依赖、联网、访问 Git 历史或共享镜像；未修改 `base/`。

公开材料足以确定核心目标并定位调查入口：恢复小写 `freq="m"` 作为月末频率的兼容行为。现有代码已采用规范名称 `ME`，因此题面旧版本输出中的 `freq='M'` 不应被直接解释为必须恢复旧显示名称。小写输入的警告细节及是否一并恢复其他旧别名仍存在边界空间；实际编译、导入和测试条件尚未验证。

## 1. 输入层次与需求表

| 输入层次 | 材料事实 | 审阅时的解释 |
|---|---|---|
| Issue 需求 | `user_prompt.txt:3–7,62–77` 报告 `m` 原可生成月末序列，现在报错；标题明确称其为已弃用 `M` 的别名。 | 恢复兼容行为是目标；未要求撤销 `M` 的弃用。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求探索源码、仅修改非测试源码、不得修改测试、窄范围运行测试、完成后简短总结。 | 这是可见字段中的原指令。不能因未渲染进 `user_prompt.txt` 就称其不可见，也不能自行忽略禁止改测试的要求。 |
| 环境声明 | 同一字段称 `/testbed` 中已有激活的 `testbed` conda 环境；bundle 给出基础提交与镜像标识。 | 这些是声明，不是本次实际 actor 的导入、权限或资源证明。 |
| 当前说明对旧机制的修正 | `environment_brief.md:18–26` 说明已无按测试文件名统一排除，仍有官方文件恢复等具体限制，原指令是否实际应用待核对。 | “测试修改全部恢复、永不计分”不能作为当前机制事实。本报告不判断具体恢复文件，也不据此判题目无效。 |

| 行为/约束 | 明确程度 | 公开依据与应保留内容 |
|---|---|---|
| `pd.date_range("2010-01-01", periods=20, freq="m")` 应成功产生 20 个逐月月末时间点。 | 题面明示 | `user_prompt.txt:7,68–77`；首项 `2010-01-31`，末项 `2011-08-31`，其中二月为正确月末。不能把 `m` 当分钟，也不能只吞掉异常或返回任意序列。 |
| `m` 应与当前月末偏移量等价；当前返回频率规范名称为 `ME`。 | 可由源码、文档、旧测试合理推知 | `base/pandas/_libs/tslibs/offsets.pyx:2923–2958` 定义 `MonthEnd` 及 `_prefix="ME"`；`base/doc/source/user_guide/timeseries.rst:1243` 列 `ME`；`base/pandas/tests/tseries/offsets/test_offsets.py:824–830` 检查 `ME` 的 `rule_code`。旧题面表示法不是要求回退的接口。 |
| 默认返回 `DatetimeIndex`、纳秒精度、默认无时区；其他参数继续由原接口处理。 | 题面示例及接口约定 | `user_prompt.txt:72–77`；`base/pandas/core/indexes/datetimes.py:821–879,1005–1019`；`base/pandas/core/arrays/datetimes.py:445–449`。不需要修改默认 `freq`、`normalize`、`inclusive`、`unit` 等行为。 |
| `M`、`2M` 等已弃用输入仍按 `ME` 处理并发出现有 `FutureWarning`。 | 已有代码与公开测试约定 | `base/pandas/_libs/tslibs/dtypes.pyx:248–250`；`base/pandas/_libs/tslibs/offsets.pyx:4863–4871`；`base/pandas/tests/indexes/datetimes/test_date_range.py:149–166` 比较 `2M` 与 `2ME` 并断言弃用警告。修复不能使规范 `ME` 也变为弃用名称。 |
| 小写 `m` 也走弃用兼容语义。 | 强合理推知，精确警告细节仍不唯一 | 标题明确与已弃用 `M` 等价，现有 `M` 路径使用 `FutureWarning`。沿用这类警告比悄悄取消弃用更符合仓库约定；但题面及已读旧测试没有规定小写 `m` 警告里应显示 `m` 还是规范化后的 `M`，也没有给出专门的警告文本断言。 |
| 合法倍数、负数等通用频率语法应继续有效；现有非法输入仍报错。 | 接口与公开测试可推知 | `base/pandas/core/indexes/datetimes.py:854–857`；`base/pandas/_libs/tslibs/offsets.pyx:4901–4935`；`base/pandas/tests/tslibs/test_to_offset.py:12–44,47–100,104–131`。例如 `2m` 合理地应表示两个日历月末间隔；`-m`、`2h20m` 属已有非法输入，不能因恢复 `m` 而变成有效频率。 |
| 保留大小写有语义差异的频率，以及仍有效的旧大小写兼容。 | 文档和公开测试约定 | `MS` 为月初，`ms` 为毫秒，`min` 为分钟，见 `base/doc/source/user_guide/timeseries.rst:1247,1259–1266`；`base/pandas/tests/tseries/offsets/test_offsets.py:787–804` 公开测试了 `b`、`bme`、`Bme`；`base/pandas/tests/tslibs/test_to_offset.py:17–27` 检查分钟与亚秒组合。不能不加区分地统一全部输入大小写。 |
| 保留 Period 与 Datetime offset 的频率名称差异。 | 明确旧接口与公开测试约定，非本 issue 新增目标 | `base/pandas/_libs/tslibs/offsets.pyx:4788–4790,4826–4835,4872–4896`；`base/doc/source/user_guide/timeseries.rst:1315–1326`；`base/pandas/tests/scalar/period/test_period.py:60–63,78–92` 和 `base/pandas/tests/indexes/period/test_constructors.py:22–49`。Period 的月度名称仍是 `M`，`ME` 输入有明确报错。 |
| 是否同时恢复 `bm`、`cbm`、`sm`、`q`、`y`、锚定后缀及混合大小写等旧别名。 | 有合理扩展依据，但不是题面逐项明示 | `base/pandas/_libs/tslibs/dtypes.pyx:248–331` 列出同族大写旧名；`base/pandas/_libs/tslibs/offsets.pyx:4755–4760` 有一般大小写处理。共用缺陷路径支持做一致修复，但本题没有枚举完整兼容矩阵。不能把任意新大小写拼写也自动列成必需支持。 |

## 2. 合理实现范围

可接受的实现不应绑定某个新增函数名、字典名、代码位置或补丁形状。公开目标允许在共用频率解析过程中适当调整旧名识别与大小写规范化的顺序，也允许用受控的兼容映射达到相同可观察行为。两者都需保留日历月末对象、`ME` 规范名称、既有弃用行为、合法倍数与错误输入边界，并避免混淆 `MS`/`ms`。这只是实现自由度描述，本次没有编写或验证修复。

只在 `date_range` 对例中字符串做特判虽能覆盖字面复现，但还应审视 `to_offset("m")` 的一致性：`date_range` 明确调用共享转换器，而 `pandas.tseries.frequencies` 也导出同一 `to_offset`（`base/pandas/core/arrays/datetimes.py:434`；`base/pandas/tseries/frequencies.py:30–34`）。公开仓库支持在共享行为层处理，而不是仅对这组日期、20 个 periods 或单个入口进行专门编码。

真正已有约定的是 `MonthEnd`/`ME` 语义、当前公开接口名称、`M` 的 `FutureWarning` 和 Period 的独立名称规则。没有依据要求恢复题面 2.1.2 的整段 `repr` 字面格式，也没有依据把新增小写 `m` 警告中的大小写、任意内部 helper 名称、额外性能阈值或未枚举别名集合当成唯一答案。新名 `me`、`qe`、`ye` 在 `_dont_uppercase` 中有专门处理（`base/pandas/_libs/tslibs/offsets.pyx:4714–4736`），不能从旧 `m` 的兼容要求直接推导它们必须获得新的大小写容错。

## 3. 初态线索、疑义与实际阻碍

调查入口充分。题面同时给出输入、错误链、调用栈、旧版本号和完整旧结果（`user_prompt.txt:3–77`）。静态可追到：

1. `date_range` 将 `freq` 传给 `DatetimeArray._generate_range`，后者调用 `to_offset`（`base/pandas/core/indexes/datetimes.py:1008–1019`；`base/pandas/core/arrays/datetimes.py:411–434`）。
2. `to_offset` 先按输入原样检查 `c_OFFSET_DEPR_FREQSTR`，该表有 `M -> ME`，没有小写 `m`（`base/pandas/_libs/tslibs/offsets.pyx:4855–4871`；`base/pandas/_libs/tslibs/dtypes.pyx:248–331`）。
3. 后续 `_get_offset` 才把 `m` 转成 `M`，并用其查询以当前 `_prefix` 为键的映射；该映射包含 `MonthEnd` 的 `ME`，不是 `M`（`base/pandas/_libs/tslibs/offsets.pyx:4656–4691,4755–4773,4927–4939`）。这解释了题面 `KeyError('M')` 被包装成 `ValueError` 的结构。此结论来自静态路径，不是实际复现结果。

| 疑义/缺项 | 是否阻碍开发与所需后续 |
|---|---|
| Issue 未说明小写警告全文、其他旧别名与所有后缀范围。 | 不阻碍恢复明确的 `m` 行为；需要保持公开旧约定，并把额外范围与措辞要求单独说明。读取相关调用者是正常开发工作，不是题面缺陷。 |
| 原禁止改测试指令是否进入实际求解消息，以及哪些文件会恢复。 | 属共享输入/运行条件问题。若原指令适用，仍可修改非测试源码、用临时命令复现并运行原测试；若不适用，添加回归测试和调整确实过时的警告断言是合理开发活动，但也不能据此推断这些文件均被保留。当前静态材料不授权忽略原指令。 |
| 修改警告发出时机可能影响原有非法输入测试。 | `base/pandas/tests/tslibs/test_to_offset.py:50,66,83–90` 对 `2h20m`、`-m` 只断言 `ValueError`；`base/pyproject.toml:494–501` 将 pandas 警告当错误。若某种修复在发现非法语法前新增弃用警告，原测试可能出现不同失败。应在 actor 下查验；这既不是已观测到的失败，也不证明合法源码修复必须改测试。 |
| 实际解释器、依赖、Cython 编译产物、重编译路径及写权限未知。 | 这是运行验证的关键缺口。静态源码不能代替可用 C 扩展；如缺必需依赖又无离线资产，才会实际阻碍开发。需在 actor 身份先导入并确认所加载代码路径。 |
| 公开祖先历史未导出。 | 本题现有复现、源码和旧测试已足以开始，不需要历史才能理解明确目标。若要核实完整历史别名矩阵，可请求限于本基准之前的公开材料；本次没有访问历史或共享镜像。 |
| 外部文档、附件、数据集或服务。 | 复现完全由字面日期与本地计算构成，没有必需外部附件。已读 README 的安装外链在包内也有对应开发说明。没有发现必须联网补充的业务材料；不需要数据库、远端数据服务或 GPU。 |

## 4. 开发需求表与建议验证命令

下列命令全部为**建议，未执行**，用于真实 actor 的 `/testbed` 工作区，不在本审阅导出的 `base/` 上执行。旧测试通过只能证明其覆盖的行为未退化，不能替代小写 `m` 的直接复现。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小验证 |
|---|---|---|---|---|
| 指定源码、可读可写工作区与正确 actor | `user_prompt.txt:1`；`public_bundle.json:1`；`base_identity.json:3–12` | `environment_brief.md:5–9` 称导出跟踪文件，计划使用 `/testbed`、`agent/54321`，workspace/home 可写。identity 声明无 gitlinks、无未物化 LFS 指针。 | 静态导出没有 `.git`、真实镜像附加提交或产物；identity 声明未独立复核。建议 C0、C1 验证身份、路径和实际导入来源。 |
| Python 与 pandas 硬依赖、已编译 `_libs.tslibs.offsets` | `base/pyproject.toml:1–38`；`base/pandas/__init__.py:8–35` | 仅 public_hints 声称 conda 已激活；`environment_brief.md:12` 明确要求另做 CPU 验证。 | Python 至少 3.9；NumPy 版本依 Python 而异，另需 dateutil、pytz、tzdata。正确 C 扩展必须能导入。建议 C1；缺依赖或未构建错误属于环境问题，不能当本 issue 原 bug。 |
| 修改 Cython 源码后的重编译 | `base/README.md:121–143`；`base/pyproject.toml:1–18`；`base/requirements-dev.txt:4–8`；`base/doc/source/development/contributing_environment.rst:211–230,260–275,292–310` | `environment_brief.md:9–12` 仅说明部分写权限和默认 2 CPU/4 GiB、tmp 1 GiB、home 256 MiB，未验证实际资源。 | 需可用编译器、Cython 3.0.5、Meson 1.2.1、meson-python 0.13.1、Ninja 等当前构建路径所需工具。Meson editable 可在 import 时重建；setuptools 路径需重新编译。建议先 C1 确认方式，再按需要 C2；不能认为修改 `.pyx` 后原 `.so` 自动更新。资源峰值与构建目录可写性未知。 |
| 本地最小复现与行为比较 | `user_prompt.txt:7,68–77`；`base/pandas/_libs/tslibs/offsets.pyx:2923–2958` | 公开包有全部字面输入；环境未验证实际可导入。 | 无数据文件、网络或外部服务需求。建议 C3；基础版本预计按题面出现 `Invalid frequency: m` 包装错误，修复后应与 `ME` 结果相等。 |
| 窄范围公开 pytest | `base/pyproject.toml:66,482–525`；`base/pandas/conftest.py:38–60,201–218`；`base/doc/source/development/contributing_codebase.rst:746–774` | 仅列 bash/edit 工作流和测试工具环境声明，未证明测试能收集。 | 需 pytest、Hypothesis、NumPy/dateutil/pytz 与可导入 pandas；配置默认写 `test-data.xml`，需目录可写。建议 C4–C7。未要求全仓可跑，也不推断全部可选依赖必须安装。 |
| 离线依赖与环境写入 | `environment_brief.md:9–12`；构建依赖清单同上 | 网络限模型代理及声明内部服务，不能假设能访问 PyPI、conda 或公网文档。 | 若需重装/补包，必须已有离线依赖或可用内部资产；C2 故意禁止依赖解析下载。解释器目录是否可写仍待核对；现有 editable 重建可能无需重新安装。 |

C0 — 身份、工作目录和解释器入口（建议，未执行）：

```sh
id
pwd
command -v python
```

预计应与实际 actor profile 及 `/testbed` 相符；conda 环境名称不能仅凭旧提示认定。

C1 — 最小导入与编译产物来源（建议，未执行）：

```sh
python -c "import sys, pandas as pd; import pandas._libs.tslibs.offsets as offsets; print(sys.executable); print(pd.__version__); print(pd.__file__); print(offsets.__file__); print(getattr(pd, '_built_with_meson', None))"
```

预计成功导入与目标 checkout 对应的 pandas 和扩展；Meson 下扩展可能位于 build 目录，不能仅凭路径不同就判失败。若提示硬依赖缺失或 C extension 未构建，应先解决环境/构建问题；这一步本身不验证 `m`。

C2 — 仅在需要且现有离线构建依赖与写权限具备时建立/刷新 Meson editable 安装（建议，未执行）：

```sh
python -m pip install -ve . --no-build-isolation --no-deps --no-index --config-settings=editable-verbose=true
```

基于包内开发安装命令加上禁止下载选项。预计构建成功后 C1 加载更新产物。若当前实际使用 setuptools，应依据 `base/doc/source/development/contributing_environment.rst:260–275` 采用现有构建方式；不应未经检查混用两个 backend，也不建议在本任务中抓取最新上游 tags。此处没有确认完整构建能在声明资源内完成。

C3 — 题面复现与规范月末结果比较，保留警告供检查（建议，未执行）：

```sh
python - <<'PY'
import warnings
import pandas as pd
from pandas.testing import assert_index_equal

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    result = pd.date_range("2010-01-01", periods=20, freq="m")
expected = pd.date_range("2010-01-01", periods=20, freq="ME")
assert_index_equal(result, expected)
print(len(result), result[0], result[-1], result.dtype, result.freqstr)
print([(w.category.__name__, str(w.message)) for w in caught])
PY
```

基础源码预计在第一处 `date_range` 按题面报 `ValueError`；修复后应输出 20、`2010-01-31`、`2011-08-31`、`datetime64[ns]`、`ME`，并检查符合弃用语义的警告。这里没有预设小写警告全文。

C4 — 现有转换器公开测试，覆盖非法输入、倍数、组合单位（建议，未执行）：

```sh
python -m pytest -q pandas/tests/tslibs/test_to_offset.py
```

C5 — 既有日期范围弃用行为（建议，未执行）：

```sh
python -m pytest -q pandas/tests/indexes/datetimes/test_date_range.py -k 'frequency_M_SM_BQ_BY_deprecated or frequencies_H_T_S_L_U_N_deprecated or frequencies_A_deprecated_Y_renamed'
```

C6 — 现有偏移量名称、大小写兼容与规范代码（建议，未执行）：

```sh
python -m pytest -q pandas/tests/tseries/offsets/test_offsets.py -k 'get_offset or rule_code'
```

C7 — 若修改共享转换逻辑，检查 Period 名称边界（建议，未执行）：

```sh
python -m pytest -q pandas/tests/scalar/period/test_period.py::TestPeriodDisallowedFreqs::test_invalid_frequency_period_error_message pandas/tests/scalar/period/test_period.py::TestPeriodConstruction::test_construction
python -m pytest -q pandas/tests/indexes/period/test_constructors.py::TestPeriodIndexDisallowedFreqs
```

C4–C7 的目标是原有公开断言继续通过；没有运行前的绿灯证据。这些测试多数不包含题面小写 `m`，因此它们即使在基础版本通过，也不否定回归。若 C4 因新增警告提前失败，需要结合非法输入语义和原指令分析，不能直接把该失败归为依赖故障或擅自修改测试。

## 5. 实际阅读范围与限制

实际全文读取：指定 `roles/public_reader.md`、`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`、`base/README.md`、`base/pandas/tests/tslibs/test_to_offset.py`（1–173）、`base/pandas/tests/tseries/frequencies/test_frequencies.py`（1–29）、`base/pandas/tests/tseries/frequencies/test_freq_code.py`（1–69）。

实际读取的主要片段（均在本题公开包内）：

| 文件 | 已打开/重点核对范围 |
|---|---|
| `base/pandas/_libs/tslibs/offsets.pyx` | 1–180、2923–2987、4635–4955；另外对转换器、映射和异常关键词检索。 |
| `base/pandas/_libs/tslibs/dtypes.pyx` | 170–355；另外检索月度映射及频率名称。 |
| `base/pandas/core/indexes/datetimes.py` | 821–881、994–1023；另检索 `date_range` 与 `to_offset` 调用。 |
| `base/pandas/core/arrays/datetimes.py` | 404–459；另检索 `_generate_range` 与 `to_offset`。 |
| `base/pandas/tseries/frequencies.py` | 1–105。 |
| `base/pandas/__init__.py` | 1–78。 |
| `base/pandas/tests/tseries/offsets/test_offsets.py` | 205–245、745–850、860–910、1125–1160；另检索 freqstr/弃用关键词。 |
| `base/pandas/tests/indexes/datetimes/test_date_range.py` | 请求读取 1–215 时批量输出曾截断；随后明确重读 1–70、149–166，并读取 765–835、1675–1710；其余可见片段与关键词结果只作线索。 |
| `base/pandas/tests/scalar/period/test_period.py` | 1–155。 |
| `base/pandas/tests/indexes/period/test_constructors.py` | 1–52；另有频率关键词检索。 |
| `base/pandas/conftest.py` | 1–110、196–222；另对 pytest/Hypothesis 关键词检索。 |
| `base/pyproject.toml` | 1–170、482–540；另检索 pytest 配置。 |
| `base/requirements-dev.txt`、`base/environment.yml` | 分别 1–25、1–30，并检索构建/测试依赖。 |
| `base/doc/source/development/contributing_environment.rst` | 28–175、204–315；另检索安装/构建关键词。 |
| `base/doc/source/user_guide/timeseries.rst` | 1227–1283、1300–1341；另检索 offset aliases、大小写及月末说明。 |
| `base/doc/source/development/contributing_codebase.rst` | 通过带上下文的检索读取约 738–878，重点为 746–774 的窄范围测试说明。 |

其他仅检索/目录清单项：

- 对本题 `PUBLIC_DIR` 做过一次文件名清单查询，输出被截断；不能当作所有文件内容均已阅读。没有打开清单中的 `MANIFEST.in` 或其他无关文件。
- `base/pandas/_libs/tslibs/dtypes.pxd` 只纳入一次关键词搜索，没有匹配正文；`base/doc/source/development/contributing.rst` 只见安装命令匹配行 327。
- `base/pandas/tests/tslibs/`、`base/pandas/tests/tseries/offsets/` 做过有限频率词检索；其中 `base/pandas/tests/tslibs/test_parsing.py:98` 只出现一条 `m` 匹配，未据此推导频率规则。
- `base/pandas/tests/tseries/frequencies/test_inference.py:98` 只读取匹配行，没有完整审阅频率推断测试。曾查询不存在的 `base/pandas/tests/tseries/test_frequencies.py`，之后从公开目录清单定位到上述真实子目录。
- 对 `base/pandas/tests/arrays/period/` 和 `base/pandas/tests/indexes/period/` 做频率/弃用关键词检索，仅阅读返回的匹配行；除了表内文件，命中包括 `arrays/period/test_constructors.py`，以及 `indexes/period/` 下的 `test_period_range.py`、`test_tools.py`、`test_setops.py`、`test_formats.py`、`test_scalar_compat.py`、`test_freq_attr.py`、`test_period.py`、`methods/test_shift.py`。未完整阅读这些文件。

未检查全仓调用者、完整测试集合、全部月份/锚点/大小写组合、完整构建脚本、实际 C 扩展、容器、消息注入、shell 激活、权限、资源上限或运行结果。未读取其他题、私有包、gold、历史答案、汇总或其他角色产物。`user_prompt.txt` 只是当前函数的静态渲染，`base/` 是源码导出而非完整运行容器（`environment_brief.md:3–6,12,26`）。本次范围约定不等同文件权限隔离，也不证明预训练无污染。

关键待核对项为：actor 是否能加载并重编译正确 checkout、原禁止改测试指令的实际适用情况、小写警告与扩展别名集合是否另有明确公开约定。前两项属于共享输入/运行条件；后者不妨碍依据现有公开证据开始修复核心月末回归。
