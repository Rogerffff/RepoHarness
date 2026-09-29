# dask__dask-6626 公开静态阅读报告

## 范围与证据性质

- 本题 `PUBLIC_DIR`：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-6626`。下文 `base/...`、`user_prompt.txt` 等均相对此目录；行号指实际读取的静态文件。
- 角色卡：`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/roles/public_reader.md`，全文已读。
- `base_identity.json:3–5` 声明 base commit 为 `56cd4597630feb1b01501c16d52aa862dd257a83`，静态导出不是实际 actor 工作树。本文仅作公开材料推理，没有执行项目、导入 Dask/Pandas、测试、安装、联网或修改题目源码。
- `environment_brief.md:3–10` 限定实际 actor 的消息、初始源码状态、依赖、资产、工具权限均未验核；本文记为 **unknown**。没有读取隐藏测试、gold、历史或其他角色报告，也不声称 OS 隔离或未受预训练影响。不作成功率或训练资格判断。

## 先按题面确定的目标、约束和疑义

`user_prompt.txt:3–44` 要求两种建表顺序一致：Pandas 先把 `col1`、`col2` 转成 category，随后 `dd.from_pandas(..., npartitions=2).set_index('i')`，与 Pandas 先 `set_index('i')` 再转 Dask 相比，不应使 `col1.cat.categories` 从空集合变成 `['a', 'b']`。题面给出的第一种路径计算结果已为空类别（行 25–26），所以主要可见错误是静态类别元数据；不应以让计算结果也变成虚构类别来“统一”两者。

合理保留的行为：`i` 成为索引，原有两行、缺失值、`col2` 的 `'A'` 类别及正常排序/分区语义保持正确。两种路径的任务图或分区实现无需完全相同。题面“empty categories”指 `col1` 全缺失、类别集合为空，DataFrame 本身有两行（行 16），不能替换成零行 DataFrame 问题。

`public_bundle.json:1` 的 `public_hints` 声明只改 NON-TEST 源码、不修改测试、验证保持单文件/模块范围；声明工作目录 `/testbed`、预激活 conda 环境 `testbed`、工具 `bash`/`edit`。这些是公开来源约束和计划条件，实际交付/可用性仍为 unknown。问题作者环境是 Dask 2.19、Python 3.8.2、Ubuntu 18.04.3、pip（`user_prompt.txt:47–52`），不是已核实的 actor 环境。

初始疑义包括：空类别是否等于未知类别；`a/b` 来自真实数据还是样本推断；应该修 `set_index` 还是通用元数据生成；应支持哪些类别 dtype、排序标记与索引形式。以下由公开材料消解或收窄。

## 公开源码、文档与旧测试能解释的部分

1. **空类别是已知状态，不能当作未知类别处理。** `base/docs/source/dataframe-categoricals.rst:4–22` 规定已知类别存在 `_meta` 中，各分区必须与其一致；未知类别用 `UNKNOWN_CATEGORIES` 哨兵标记。`base/dask/dataframe/utils.py:201–212` 检查该哨兵是否存在，而不是类别长度。`base/dask/dataframe/categorical.py:153–182,213–225` 说明 `.cat.categories` 直接读取 `_meta`，未知类别反而会报错。因此把空类别标成未知、要求用户先 `.categorize()`，不能满足题面。

2. **`a/b` 有直接源码来源。** `base/dask/dataframe/utils.py::_nonempty_series`（552–559）遇到空类别时调用 `_nonempty_index(s.cat.categories)`，并设 `cats = None`，让 Pandas 从假数据推断类别；`_nonempty_index` 的普通 `pd.Index` 分支（411–412）正好返回 `['a', 'b']`。同一文件 `_nonempty_index` 的 `CategoricalIndex` 分支（445–452）也在空类别时从类别索引生成假值。这是静态可见的共同风险，非真实记录生成 `a/b` 的证据。

3. **元数据传播机制解释了两条路径差异。** `base/docs/source/dataframe-design.rst:20–57` 说明 `_meta` 存名称和 dtype，通常在 `_meta_nonempty` 的小型假样本上推断操作结果。`base/dask/dataframe/core.py:347–350,5129–5156,5203–5222` 给出实际实现。`base/dask/dataframe/io/io.py:208–227` 的 `from_pandas` 用原数据分片并把原数据传入新对象，不走本次 `set_index` 后的样本推断。

4. **不能只盯住真正发生 shuffle 的分支。** `base/dask/dataframe/core.py:3746–3769` 默认进入 `shuffle.set_index`；`base/dask/dataframe/shuffle.py:112–119` 检测数据已排序后调用 `set_sorted_index`，再执行未显式传 `meta` 的 `result.map_partitions(M.sort_index)`。`set_sorted_index` 本身（949–955）先从空 `_meta` 设置索引并显式传 meta，因此后续 `sort_index` 的推断是重要传播点。题面 `i=[0,1]` 分成两块，静态推理符合此快速路径，但未实际运行确认。普通 `set_partition` 路径（199–243）还有 `assign`、后处理、`sort_index` 等操作，范围不宜仅限一个已排序出口。

5. **旧测试给出兼容性边界，但未完整断言该缺陷。** `base/dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty_empty_categories`（172–190）覆盖类别索引 dtype `O`、`f8`、`M8[ns]`、Series/Index、`ordered=True`、名称；它检查类别索引类型，却没有断言类别值/长度仍为空。`test_meta_nonempty`（123–157）检查普通类别 dtype 与 `UNKNOWN_CATEGORIES` 样本，`test_meta_nonempty_index`（228–239）检查非空类别索引、排序标记与未知类别。修复应兼顾这些现有语义，不能只消除字符串 `a/b`。

6. `base/dask/dataframe/tests/test_shuffle.py::test_set_index_categorical`（781–794）检查非空 ordered 类别作为索引时的 divisions 顺序；`test_set_index_empty_partition`（744–761）和 `test_set_index_on_empty`（764–778）分别是空分区、整表过滤为空，与本题不同。`test_set_index_detects_sorted_data`（491–497）保护已排序快速路径。`base/dask/dataframe/tests/test_categorical.py:414–425` 另有空类别访问不抛 `IndexError` 的旧回归。以上都不能代替本题对静态类别与计算结果的直接比较。

## 合理实现范围与选择

- 优先考虑通用 `meta_nonempty` 的 categorical Series 与 CategoricalIndex 构造，保持原始 `categories`（包括空集合及其索引 dtype）、`ordered`、名称，同时仍返回两行样本。原 dtype、空类别和两条记录可以同时成立：两条样本均为 categorical 缺失值即可。
- 一种合理实现选择是在空类别分支显式传原 categories，并生成两条缺失值；另一种是用 `pd.Categorical.from_codes` 的缺失编码构造。旧源码 449–450 已使用 `from_codes` 和 `-1`，给出本地惯例，但不要求特定 API、字面量、函数拆分或补丁形状。非空类别分支可以保留现有逻辑。
- 也可在受影响操作显式传播可靠 `_meta`，但须检查已排序和普通路径；仅给题面路径补 meta 容易留下通用样本生成问题。是否采取局部或通用修复应由公开回归表现支持，不能从不可见 gold 推断。
- 不应删除有效类别、去掉 categorical dtype、把正常类别一律改空，或通过计算整表重新确定已知类别；后者引入额外执行成本，也不是这类元数据错误所必需。无需外部数据集、网络服务、GPU 或分布式集群来表达最小回归。磁盘 shuffle 的临时目录需求与实际权限另行核验。
- 题面没有明确要求零行数据、空 categorical 索引作为新索引、所有扩展 dtype 或新 Pandas 版本的全部行为。Series/Index 的空类别 dtype 保持是公开旧测试支持的邻近范围；更广范围不能当作强制评分规范。

## 开发需求与建议验证

以下仅是建议，在实际授权 actor 的仓库根目录进行，**本轮均未运行**；不是强制评分规范，不需修改测试文件。

| 需要操作/资产 | 公开依据 | 实际证据或未知 | 最小公开验证命令及预期 |
|---|---|---|---|
| 确认源树、解释器、导入来源与编辑权限 | `user_prompt.txt:1`；`public_bundle.json:1` | 静态 base 可读；actor HEAD、diff、cwd、工具与权限 unknown | `pwd`、`git rev-parse HEAD`、`git status --short`；另运行下列环境检查。预期明确实际状态，不能预设工作树干净。写权限应在实际实施非测试源码修改时确认。 |
| 相容 Python 与 DataFrame 依赖 | `base/setup.py:18–24,31,70–74`；`base/docs/source/develop.rst:124–127` | 声明 Python >=3.6、Pandas >=0.23、NumPy >=1.13、toolz、partd、fsspec、pyyaml；pytest 用于测试。实际版本/导入 unknown，最低版本声明不保证任意最新版本兼容 | 下列环境检查应能导入所需组件并打印版本/路径；如失败，先区分环境与源码错误。 |
| 最小题面回归，无外部文件 | `user_prompt.txt:16–44` | 两行内存数据足够；执行结果 unknown | 下列直接回归命令应通过：`col1` 静态类别为空，两路径 `_meta` 与计算结果相等，`col2` 仍为 `'A'`。 |
| 元数据构造兼容性 | `test_utils_dataframe.py:123–190,228–239` | 旧测试存在；未执行；旧空类别测试单独通过不能证实修复 | `python -m pytest -q dask/dataframe/tests/test_utils_dataframe.py -k meta_nonempty`。预期旧语义保持；另可用同样输入逐项断言类别索引精确相等、两行样本、ordered/名称保持。 |
| 索引操作回归及类别访问 | `test_shuffle.py:491–497,744–794`；`test_categorical.py:414–425` | 测试存在；运行依赖及临时目录权限 unknown | `python -m pytest -q dask/dataframe/tests/test_shuffle.py -k 'set_index_categorical or set_index_detects_sorted_data or set_index_empty_partition or set_index_on_empty'`；必要时单独 `python -m pytest -q dask/dataframe/tests/test_categorical.py -k categorical_empty`。预期维持已有排序、空分区和访问行为。 |

环境检查建议（不是本轮已执行命令）：

```sh
python -c 'import sys, dask, pandas, numpy, pytest, toolz, partd, fsspec, yaml; print(sys.executable); print(sys.version); print(dask.__file__); print(dask.__version__, pandas.__version__, numpy.__version__, pytest.__version__)'
```

最小直接回归建议（无需落地测试文件）：

```sh
python - <<'PYCODE'
import pandas as pd
import dask.dataframe as dd
from pandas.testing import assert_frame_equal, assert_index_equal
pdf = pd.DataFrame({'i': [0, 1], 'col1': [None, None], 'col2': [None, 'A']})
pdf = pdf.astype({'col1': 'category', 'col2': 'category'})
a = dd.from_pandas(pdf, npartitions=2).set_index('i')
b = dd.from_pandas(pdf.set_index('i'), npartitions=2)
assert a.col1.cat.known
assert len(a.col1.cat.categories) == 0
assert_index_equal(a.col1.cat.categories, pdf.col1.cat.categories)
assert_index_equal(a.col2.cat.categories, pdf.col2.cat.categories)
assert_frame_equal(a._meta, b._meta)
assert_frame_equal(a.compute(scheduler='synchronous'), b.compute(scheduler='synchronous'))
PYCODE
```

## 实际已读与未读范围

已完整读取角色卡、`user_prompt.txt:1–53`、`environment_brief.md:1–10`、`public_bundle.json:1`、`base_identity.json:1–23`。对目录执行 `rg --files`；首次全目录输出被截断，因此不声称所有文件名或文件内容均已读。

正文涉及的主要源码实际阅读区段：`base/dask/dataframe/utils.py:201–215,369–465,535–604`；`core.py:268–291,304–351,3666–3698,3736–3835,4750–4870,4875–4980,5129–5160,5180–5230`；`shuffle.py:27–198,199–257,812–858,949–972`（首次 27–270 的合并输出部分截断，不引用未完整显示的末段）；`io/io.py:207–251`；`categorical.py:153–183,210–241`。还对这些文件及 `accessor.py` 做了相关符号检索，未通读整个文件。

旧测试实际阅读：`test_utils_dataframe.py:1–24,123–193,220–244`；`test_shuffle.py:1–35,488–517,744–812`，另检索 set_index/category/empty 测试名；`test_categorical.py:400–443`。文档实际阅读：`dataframe-categoricals.rst:1–83`、`dataframe-design.rst:1–68`、`develop.rst:85–129`；另检索 `develop.rst` 和 `CONTRIBUTING.md` 的 pytest/pip 文字。配置实际阅读：`setup.py:1–77`、`setup.cfg:1–48`、根 `conftest.py:1–25`。检索 `base/dask/conftest.py` 返回路径不存在，仅说明此公开导出路径未见该文件，不能推断 actor 镜像缺资产。

未读其余源码/文档/测试全文、任何导出外链接、实际 actor 环境、历史、私有材料、gold 和其他报告。所有因果路径与预期结果均为静态判断；没有运行通过记录。报告保存后封存，不再修改。
