# dask__dask-8597：公开材料阅读

本记录仅基于指定角色卡及本题 `PUBLIC_DIR` 的静态材料。未运行项目代码、安装依赖、修改 `base/`、联网或读取私有评分材料、未来修复、其它题及旧结论。以下文件定位均相对于 `PUBLIC_DIR`，行号来自静态文件；`public_bundle.json` 为单行 JSON，字段引用均定位到第 1 行。

公开材料足以明确主要目标并定位调查入口：对含长度为零的轴的数组执行有效列表索引，应能构造 Dask Array，计算后的形状、dtype 和内容与 NumPy 一致。标题写作“0-D”，但复现输入 `numpy.zeros((3, 0))` 是二维数组，第二轴长度为零，并非形状为 `()` 的零维标量。正文示例足以消除此处对核心修复目标的歧义；标题本身不能扩张为“重做所有零维数组索引”。

## 1. 需求表

| 需求或应保留行为 | 判断层次 | 公开依据与边界 |
| --- | --- | --- |
| `dask.array.from_array(numpy.zeros((3, 0)))[[0]]` 不应抛出所报 `OverflowError` | 明示 | `user_prompt.txt:5–14,24–34`；调用没有 `.compute()`，因此至少要求构图阶段成功，不能仅把失败推迟到计算阶段。 |
| 结果与 `numpy.zeros((3, 0))[[0]]` 一致：空数组，形状 `(1, 0)`，dtype `float64` | 明示；计算阶段一致性亦由接口惯例支持 | `user_prompt.txt:16–22`。`base/docs/source/develop.rst:187–210` 说明以 NumPy 和 `assert_eq` 比较 Dask 集合；该辅助函数会计算结果并核对形状、dtype、图与元信息（`base/dask/array/utils.py:229–287,289–319`）。 |
| 保留 Dask Array 类型、延迟计算和可用的块元信息；无需令交互式字符串等于 NumPy 的字符串 | 公开仓库可合理推知 | `Array.__getitem__` 构造 HighLevelGraph 并返回 `Array`（`base/dask/array/core.py:1846–1855`）；文档展示的索引结果为 `dask.array<...>`（`base/docs/source/array-slicing.rst:60–82`）。题面 NumPy 输出是数值语义参照，不是 Dask repr 的逐字要求。 |
| 有效列表/NumPy 整数数组索引的一般语义，包括保留非索引轴、重复或乱序索引及负索引，不应因空轴修复退化 | 公开仓库可合理推知；并非题面逐一枚举 | 单轴列表/数组索引在支持范围内（`base/docs/source/array-slicing.rst:4–12`）；普通 `take` 的公开测试验证图和分块（`base/dask/array/tests/test_slicing.py:316–372`），负列表索引已有比较测试（同文件 `820–824`）。因此其它位置的空轴、其它有效列表和明确分块是合理回归范围，而不是只认可字面 `(3, 0)`、`[0]` 的特例。 |
| 空列表、空切片继续保留预期形状与 dtype；零长度轴仍有合法块表示 | 公开仓库可合理推知 | `base/dask/array/tests/test_slicing.py:497–501,536–542`；`base/dask/array/tests/test_array_core.py:4155–4160`。`normalize_chunks` 明确要求零长度轴以 `0` 块表示，拒绝空块元组（`base/dask/array/core.py:2800–2803,2867–2887`）。 |
| 越界列表索引、轴数错误和布尔掩码长度不匹配仍应被检查 | 公开仓库可合理推知 | `base/dask/array/slicing.py:902–920,964–982`；`base/dask/array/tests/test_slicing.py:510–533,616–627`。不能因为数组总元素数为零就跳过所有索引合法性检查。 |
| 普通非空数组的大块警告、拆分开关和分块语义保持原约定 | 文档及公开测试已有约定 | `array.slicing.split-large-chunks` 默认 `null`（`base/dask/dask.yaml:12–16`）；默认警告、显式 `False` 接受大块、显式 `True` 拆块见 `base/docs/source/array-slicing.rst:88–95` 和 `base/dask/array/tests/test_slicing.py:875–964`。未知块大小已有专门测试和一个已标记 xfail（同文件 `906–926`）。 |
| 零元素结果不应因“大块字节数估算”而出错；在三个拆分配置状态下有效索引均可用 | 可由共同代码路径合理推知 | `base/dask/array/slicing.py:638–650` 在读取拆分开关前先计算大小；空结果没有由此产生大数据块的理由。但题面没有明示零元素图的精确任务数或固定拆分布局。 |
| 修复所有真正零维标量索引、所有 NumPy 高级索引或所有数组后端 | 不能从本题推出 | 正文没有零维标量复现；现有 `test_index_with_int_dask_array_0d` 是“用零维数组作索引”，也不同于本题输入（`base/dask/array/tests/test_slicing.py:652–658`）。多轴列表及多维 Dask 整数数组索引在文档中明确尚不支持（`base/docs/source/array-slicing.rst:14–22`）。 |

## 2. 合理实现范围

公开证据不限定补丁位置、条件表达式写法、辅助函数名称或内部变量名称。至少有两种实现组织方式可以合理评估：在现有列表索引路径的大小估算中明确处理零元素情形，继续使用现有索引计划；或在共同切片路径中为合法空结果安排适当的图与元信息。这只是可接受实现边界，不是修复代码或标准答案推测。后一种组织方式仍须保留索引检查、维数、dtype、块表示与延迟语义，不能直接返回 NumPy 数组或仅吞掉异常。

现有公开测试对普通非空 `take` 的图结构、块顺序、拆分结果作了具体断言（`base/dask/array/tests/test_slicing.py:316–372,929–964`），不能把所有内部图结构都视作自由变化项。重复相同切片的图键一致性也已有测试（同文件 `553–574`）。但公开材料没有为本题空结果指定一个唯一图键哈希、任务条数、函数名或 repr 字符串；不应凭空增加这些验收条件。

按现有分块规则，保留空轴的零长度块是自然做法，且输出块尺寸必须能组成结果形状；题面没有要求某个特定空结果优化。是否为零元素情形增加新测试，与合理实现本身是不同问题，须受实际 harness 的测试编辑指令约束。

## 3. 初态线索、疑义及旧提示

### 可直接调查的入口

1. `user_prompt.txt:1` 指定仓库、`/testbed` 和短提交；`public_bundle.json:1` 的 `base_commit` 为 `c1c88f066672c0b216fc24862a2b36a0a9fb4e22`，并提供镜像名和 manifest digest。包中没有完整运行容器，这些标识不等于环境验证。
2. `from_array` 默认 `chunks="auto"`（`base/dask/array/core.py:3057–3066`），先归一化块，再构造 Array（同文件 `3231–3233,3247–3261,3292–3295`）。正常调查应覆盖默认分块，无需向题目作者索要额外分块参数。
3. `Array.__getitem__` 先归一化索引，再调用 `slice_array`（同文件 `1832–1847`）；列表与全切片组合进入 `slice_wrap_lists → take`（`base/dask/array/slicing.py:180–196,221–264`）。实际块取值最终使用 `obj[index]`（`base/dask/array/chunk.py:401–428`）。这是从接口到执行的公开调用链。
4. 明显静态线索位于 `take`：其它轴的总长度乘积 `other_numel` 用于 `math.ceil(nbytes / (other_numel * itemsize))`，只对 NaN 特判（`base/dask/array/slicing.py:638–648`）。示例的其它轴长为零，分母因此为零；NumPy 标量除法产生非有限值，再转整数，与所报错误相符。此处是静态因果推断，未作运行复现。若测试把相关警告升级为错误，首先观察到的异常也可能不同（`base/setup.cfg:46–53`）。

### 缺失信息的实际影响

| 未知或表面缺项 | 是否阻碍当前开发，以及需要什么 |
| --- | --- |
| 标题“0-D”不准确 | 不阻碍核心修复，正文的 `(3, 0)` 和 `(1, 0)` 已明确目标。若验收另要求真正零维数组的新语义，那属于公开材料尚未说明的扩展。 |
| traceback 被 `...` 省略 | 不阻碍开始调查，完整最小复现及源码调用链已足够；actor 可自行取得本机完整 traceback。 |
| 没有报出 NumPy、pytest、依赖精确版本 | 不影响行为目标，但影响复现及旧测试可执行性。需实际 actor 记录版本及导入位置；不能把导入失败或测试 API 不兼容误当目标 bug。公开测试使用 `pytest.warns(None)`（`base/dask/array/tests/test_slicing.py:788,891,898`），版本兼容应实测；仓库依赖声明没有锁住 pytest 版本。 |
| 实际 conda 激活、目录、权限、资源、预装资产不明 | 真正运行前的条件缺口。环境说明明确这些均待 actor 核验；不是本次静态阅读能补足的事实。 |
| 无额外数据、外链附件或公开祖先历史 | 题面不依赖任何外部数据或附件，本地 NumPy 构造即足够；现有源码足以调查，此时无需申请历史。README/安装文档的站外链接不构成本题必要缺项。 |
| “需要阅读调用者与公开测试” | 正常代码调查，不是题面缺陷。本记录已追踪主要调用链；不要求隐藏验收测试向开发者公开。 |

### 分开记录 issue、harness 与环境声明

- **Issue 目标**：修复所给空轴数组列表索引，结果匹配 NumPy；报告环境是 Linux、Python 3.9、Dask 2022.01.0、pip 安装（`user_prompt.txt:3–43`）。这是报告者的环境，不是当前容器版本证据。
- **Harness 操作指令**：`public_bundle.json:1` 的 `public_hints` 要求调查并编辑非测试源文件、禁止修改测试、仅窄范围运行测试、完成后简述并停止；`allowed_tools` 为 `bash/edit`。这些与 issue 的数值行为要求应分别处理。
- **待验证环境声明**：同一字段声称 bash 已处于 `/testbed`、`testbed` conda 已激活、`python/pip` 和测试工具已指向该环境。本次没有验证这些声明；`environment_brief.md:3–12,18–24` 明确要求实际 actor 检查。
- **旧测试机制说明**：原提示“所有测试修改都会恢复、永不计分”不能当作当前机制事实。环境说明称当前已取消按测试文件名统一排除，但仍有官方文件恢复等具体限制（`environment_brief.md:18–23`）。哪些文件被恢复未在本公开包中核实。本记录没有据此取消原“禁止改测试”指令。
- **两种指令适用情况**：若禁止改测试仍适用，本题可在非测试源文件中修复，并用原有测试及不写测试文件的内联 Python 比较验证，未见它阻止合理源代码修复；若该指令不适用，增加相应公开回归测试也是合理开发活动。两种情况下数值目标相同；指令是否生效和具体恢复行为属于共享输入/运行条件待核对项，不能仅据旧解释判题无效。
- **输入可见性限制**：`user_prompt.txt` 只是静态渲染，未证明真实模型消息；bundle 会写入解题工作区的公开路径，字段未进入该文本不等于不可读（`environment_brief.md:3–6,23–24`）。

## 4. 开发需求表

下面命令均为**建议，未执行**；面向后续真实 actor 在 `/testbed` 下执行，不是让本次公开读者运行。除非另有说明，使用镜像已有依赖，不预设公网可达或允许写解释器目录。

| 操作／资产／服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小验证与预期 |
| --- | --- | --- | --- | --- |
| 在正确源码目录、解释器及 actor 身份下工作 | `user_prompt.txt:1`；bundle 的 `workdir/public_hints` | 声明拟以 `agent/54321`、`/testbed` 工作；源码和 home 可写（`environment_brief.md:8–9`） | 实际 UID、cwd、Python 路径、conda 状态、Dask 导入来源未验证 | C1（建议，未执行）：应导入该 checkout 的 Dask；若导入别处或失败，先处理环境关联。 |
| NumPy 与 Dask Array 的最小本地执行 | `base/setup.py:13,32–39,79`；`base/docs/source/install.rst:32–44` | 声称解释器和依赖预装，但要求 actor 验证（环境说明 `12`） | NumPy、Dask 核心依赖的安装和版本兼容性未知 | C1、C2（建议，未执行）：导入成功；原始源码预计在列表索引构图时出现所报异常或相关警告升级错误，修复后 NumPy 比较成功。 |
| 小型内存数组与 CPU 调度 | 题面 `numpy.zeros((3, 0))`；`assert_eq` 使用同步计算（`base/dask/array/utils.py:243`） | 默认计划 2 CPU / 4 GiB / PID512，tmp 1 GiB、home 256 MiB；本题未验（环境说明 `11`） | 资源为计划值，未量测；核心复现无大数据需求 | C2（建议，未执行）：仅使用本地内存，打印形状、dtype 和块信息。无需 GPU、数据库、对象存储、分布式集群或外部数据文件。 |
| 原有公开回归测试 | `base/dask/array/tests/test_slicing.py`；`base/setup.py:25–30`；`base/docs/source/develop.rst:165–169` | 允许窄范围测试；未证明 pytest 能收集和执行 | pytest 及插件版本未知；NumPy 缺失会导致 array 测试跳过（`base/conftest.py:21–25`；测试文件 `6`） | C3（建议，未执行）：相关已有用例应保持通过，显式 xfail/skip 要按报告区分；只有跳过不能证明环境支持。旧用例通过本身不证明题面 bug 已修复。 |
| 分块配置、零轴位置等合理回归 | `base/dask/dask.yaml:12–16`；切片文档与本记录需求表 | 不需要额外服务或资产 | actor 运行结果未知，不能从静态材料证明所有组合已通过 | C4（建议，未执行）：默认／False／True 均获得与 NumPy 一致的合法结果；不是强加隐藏测试清单。 |
| 源码安装或构建（仅必要时） | `base/docs/source/install.rst:69–71`；`base/docs/source/develop.rst:110–112` | 解释器／系统包写权限待核实；不假设能下载依赖（环境说明 `9–12`） | 如果已有安装不关联 checkout，需要可写安装位置和已有构建工具；如缺依赖，需镜像或声明的离线依赖供给 | C5（建议，未执行）：仅在 C1 显示需要且权限允许时建立源码安装；本题最小导入和测试不要求全仓构建或完整文档构建。 |

**C1：身份、解释器及导入位置（建议，未执行）**

```bash
id
pwd
python - <<'PY'
import os
import sys
import numpy as np
import dask
import dask.array as da
import pytest
print("python:", sys.version, sys.executable)
print("conda:", os.environ.get("CONDA_DEFAULT_ENV"))
print("numpy:", np.__version__)
print("dask:", dask.__version__, dask.__file__)
print("pytest:", pytest.__version__)
print("split-large-chunks:", dask.config.get("array.slicing.split-large-chunks", None))
PY
```

其中 NumPy/Dask 导入是最小复现前提；pytest 导入用于确认公开测试前提，若它缺失不应混同于 Dask 的索引错误。conda 名称环境变量仅为线索，还须结合解释器与模块路径判断。

**C2：题面最小复现并校验计算语义（建议，未执行）**

```bash
python - <<'PY'
import numpy as np
import dask.array as da
from dask.array.utils import assert_eq
x = np.zeros((3, 0))
y = da.from_array(x)[[0]]
assert y.shape == (1, 0)
assert y.dtype == x.dtype
assert_eq(y, x[[0]])
print(y.shape, y.dtype, y.chunks)
PY
```

预计原 bug 在构造 `y` 时失败；修复后应输出 `(1, 0)`、`float64` 和合法的 chunks，并完成计算比较。这里不以某个完整打印字符串作为验收标准。

**C3：与修复相关的原有公开测试（建议，未执行）**

```bash
python -m pytest dask/array/tests/test_slicing.py -q -k 'take or getitem_avoids_large_chunks or empty or negative_list_slicing or boolean_list_slicing or oob_check'
```

所选测试覆盖普通 `take`、大块配置、空列表／切片、负列表、布尔列表和越界。`test_getitem_avoids_large_chunks_missing` 的一个参数已有 xfail；需保留原有预期，并记录测试是否实际执行。需要进一步扩大到单模块时，可使用下列命令（**建议，未执行**）：

```bash
python -m pytest dask/array/tests/test_slicing.py -q
```

**C4：不修改测试文件的补充比较（建议，未执行）**

```bash
python - <<'PY'
import numpy as np
import dask
import dask.array as da
from dask.array.utils import assert_eq
cases = [
    ((3, 0), [0]),
    ((3, 0), [2, 0, 2, -1]),
    ((0, 3), (slice(None), [0, 2])),
    ((3, 2, 0), ([1, 0], slice(None), slice(None))),
]
for split in (None, False, True):
    with dask.config.set({"array.slicing.split-large-chunks": split}):
        for shape, index in cases:
            x = np.zeros(shape)
            for chunks in ("auto", 1):
                assert_eq(da.from_array(x, chunks=chunks)[index], x[index])
print("empty-axis comparisons passed")
PY
```

这是从公开接口推出的少量邻近回归建议，未运行，也不表示所有变体都由 issue 逐字指定。它不取代 C3 的普通非空行为保护。

**C5：有必要且安装位置可写时的源码安装（建议，未执行）**

```bash
python -m pip install --no-deps --no-build-isolation -e .
```

该命令不补齐依赖，依赖和本地构建工具必须事先存在。若 C1 已从 `/testbed` 正确导入源码，本题不需要先安装或构建。不得从此建议推断实际解释器位置可写或离线安装一定成功。

## 5. 阅读范围与限制

实际打开／按片段阅读的材料：

- 指定的 `roles/public_reader.md`；本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `base/README.rst`、`base/CONTRIBUTING.md`、`base/setup.py`；`base/setup.cfg:30–56`、`base/conftest.py:1–70`、`base/continuous_integration/environment-mindeps-array.yaml:1–21`。
- `base/docs/source/install.rst:24–72`、`base/docs/source/develop.rst:98–122,158–212`、`base/docs/source/array-slicing.rst:1–98`；安装与开发文档还作了关键词检索。
- `base/dask/array/core.py:1797–1885,2720–2895,3057–3100,3196–3345`；`base/dask/array/slicing.py:1–320,550–710,741–868,888–985`。这些为片段阅读，不是全文件审查。
- `base/dask/array/tests/test_slicing.py` 的导入、底层切片／take、空切片／空列表、索引检查、标量索引、负索引、警告与分块配置等片段；主要区间为 `1–260,316–390,434–580,614–680,720–1045`。首轮合并显示有截断，关键调用与测试段随后单独重读；未把截断段作为独立证据。
- `base/dask/array/tests/test_array_core.py:2188–2218,3112–3145,4143–4172`；`base/dask/array/utils.py:228–333`、`base/dask/array/chunk.py:401–435`、`base/dask/array/__init__.py:1–75`、`base/dask/dask.yaml:1–24`。
- 使用 `rg --files` 盘点本题包；对上述源码、测试及 `base/docs/source/array.rst`、`base/dask/dask-schema.yaml` 作定向关键词检索。文件清单和搜索命中不表示逐文件全文阅读。

未查项包括其余测试和数组后端、完整自动分块算法、全仓依赖图、镜像内实际文件／资产、Git 历史、运行日志、真实 CLI 消息及私有验收机制。未需要任何外部附件补充。包中 `base/` 为 Git 跟踪文件导出，没有 `.git` 和完整运行环境（`environment_brief.md:3–6`）；本记录不声称已验证模型实际收到的输入、资源配置、环境激活、开发条件或测试结果。角色隔离是本次协作范围约定，不是文件权限隔离或预训练无污染证明。

关键待核实事项为：实际 actor 的依赖与导入位置；原禁止测试编辑指令的应用情况及当前官方文件恢复限制；若任何验收超出正文空轴示例，是否有相应公开契约。现有公开正文与仓库已能支持核心修复调查，不需预先索要隐藏测试或未来修复。
