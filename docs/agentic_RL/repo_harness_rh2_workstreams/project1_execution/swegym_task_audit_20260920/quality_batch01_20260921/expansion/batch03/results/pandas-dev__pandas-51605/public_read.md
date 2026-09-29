# pandas-dev__pandas-51605：公开初读（B3）

本次仅依据角色卡和本题 PUBLIC_DIR 内的公开原件静态审查，未运行项目代码、导入、测试或构建。下述路径均相对本题 PUBLIC_DIR；源码路径以 `base/` 开头。目标基线为 `b070d87f118709f7493dfd065a17ed506c93b59a`（`public_bundle.json:1`、`base_identity.json:3`）。未接触私有材料、历史、其他题或旧审查结论；这只是本次读取范围的记录，不是权限隔离或预训练无污染证明。

## 1. 公开目标与需求表

| 行为或约束 | 公开依据 | 判断 |
| --- | --- | --- |
| 对题面三行 DataFrame 的 MultiIndex 调用 `isin([])`，不应再抛 `TypeError`，应得到三个 False。 | `user_prompt.txt:3-16` 给出 1.5.x 输出、2.0.x 异常及期望。 | 明示的回归修复目标。历史版本表现仅由题面报告，本次未复核。 |
| 返回一维布尔 NumPy 数组，长度等于被查询索引长度，顺序逐项对应索引。 | `base/pandas/core/indexes/base.py:6182-6201` 的接口说明；`base/pandas/core/indexes/multi.py:3748-3749` 复用该文档；`base/pandas/tests/indexes/multi/test_isin.py:25-37` 检查数组及空结果 bool dtype。 | 可由接口和测试明确推知。题面“an Index consisting of False”是措辞不精确，不能据此要求改成 pandas Index 返回类型。 |
| 空候选值的语义应覆盖现有 API 接受的常规空 set/list-like，而非仅识别某一个字面量 `[]`。 | 标题称 empty iterable；`base/pandas/core/indexes/base.py:6192` 声明 set or list-like；`base/pandas/core/indexes/multi.py:559-563` 接受 list-like 并消耗 iterator；`base/pandas/tests/indexes/multi/test_constructors.py:367-375` 保护 iterator 构造；普通 Index 的空 list、Series、ndarray 测试在 `base/pandas/tests/indexes/test_base.py:905-912`。 | 合理推知：空列表、元组、集合、一维数组/Index、迭代器等正常候选容器值得验证。题面没有逐一枚举容器；普通 Index 的测试是邻近合同证据，不能冒称 MultiIndex 已有这些回归测试。 |
| 空的被查询 MultiIndex 仍返回长度 0、bool dtype 的数组；空候选值与空索引组合亦应遵守长度合同。 | `base/pandas/tests/indexes/multi/test_isin.py:33-37` 已覆盖空索引加非空候选值；`base/pandas/core/indexes/base.py:6186-6201`。 | 前者有明确公开测试，后者由接口长度及成员关系语义推知。 |
| 保留普通 tuple 匹配、缺失值匹配、候选 MultiIndex、level 的名称/位置选择及非法 level 的错误。 | `base/pandas/tests/indexes/multi/test_isin.py:8-22,25-31,40-87`；空候选值也不得绕过非法 level 检查的证据为 `base/pandas/tests/indexes/test_base.py:889-903`。 | 已有公开行为应保留。不能因为候选为空就在所有参数校验之前无条件返回。 |
| 直接调用 `MultiIndex.from_tuples([])` 且不给 names 时仍应抛原 TypeError；给 names 时可构造空 MultiIndex。 | `base/pandas/tests/indexes/multi/test_constructors.py:353-356,383-387`；实现见 `base/pandas/core/indexes/multi.py:578-595`。 | 明确的已有构造器合同。本题并未授权全局取消该异常。 |
| 修复范围不要求新增公共 API、改变默认 level、level 名称或候选输入的非空合法性。 | `isin(self, values, level=None)` 现有签名与文档，`base/pandas/core/indexes/multi.py:3749-3760`、`base/pandas/core/indexes/base.py:6210-6218`。 | 合理保留约束。异常自定义迭代器、形状不合法的数组和错误长度的 tuple 等边界没有被题面逐一重新定义。 |

## 2. 合理实现范围

接受标准应落在外部行为：空候选值产生与索引等长的全 False 布尔数组，同时保留上表旧行为。公开材料没有指定必须新增某个 helper、采用某种变量名、以特定分支顺序实现，或沿用某一内部查找算法。就公开合同而言，在已确认输入有效后直接产生空集合的成员判断结果，或在内部补足空候选表示所需的维度信息再沿用现有匹配流程，均属于可讨论的合理实现方向；本初读不编写补丁、不推测标准答案。

构造器的公开测试明确禁止用“让所有 `from_tuples([])` 都成功”作为没有边界的全局行为变化。对所有 TypeError 一概返回 False 也没有公开依据，可能吞掉真正无效输入。非空匹配、NaN 行为及 level 校验的保留应比具体内部写法更重要。题面没有额外性能阈值，不能从公开材料推出某种具体算法是唯一合法实现。

只改非测试源码即可表达此修复需求，没有发现必须修改测试文件才能实现的功能条件。若原禁止改测试指令适用，可通过临时命令和现有公开测试验证；若不适用，新增回归测试有助于维护，但不是新的产品行为需求，也不能把“测试修改永不计分”当当前已验证机制。

## 3. 初态线索与已有公开支持

静态调用链已足以定位调查入口：

1. `MultiIndex.isin` 在 `level is None` 且候选不是 MultiIndex 时无条件调用 `MultiIndex.from_tuples(values)`（`base/pandas/core/indexes/multi.py:3749-3753`）。
2. `from_tuples` 会先把 iterator 转为 list，再在长度为 0 且 names 未给出时抛出与题面逐字一致的 TypeError（`base/pandas/core/indexes/multi.py:559-563,578-580`）。题面空列表将走此路径，这是静态解释，不是已执行复现。
3. 后续匹配为 `values.unique().get_indexer_for(self) != -1`；`get_indexer_for` 的分派在 `base/pandas/core/indexes/base.py:5814-5835`。报错发生在该匹配之前。
4. level 分支先解析 level，再转为单层 Index 的 `isin`；空被查询层显式返回 bool 空数组（`base/pandas/core/indexes/multi.py:3754-3760`）。普通 Index 将处理交给 `algos.isin`（`base/pandas/core/indexes/base.py:6263-6265`），后者有 list-like 验证和普通 iterable 归一化（`base/pandas/core/algorithms.py:466-494`）。
5. 公开调用者依赖数组掩码：`NDFrame._drop_axis` 的非唯一轴分支使用 `~axis.isin(labels)` 并以 `mask.nonzero()` 得到位置（`base/pandas/core/generic.py:4582-4615`）。这支持保留 bool 数组合同；未据此声称某个 drop 调用已复现相同错误。

现有 `base/pandas/tests/indexes/multi/test_isin.py:1-87` 覆盖正常匹配、NaN/缺失值、空被查询索引以及 level，但该文件没有针对空候选 iterable 的用例。因此“现有文件全部通过”本身不足以证明题面已修复，应另跑题面复现。构造器测试可保护无需改变的相邻 API。

核心目标无需缺失外链或祖先历史即可理解。进一步检查其他调用者是正常开发工作，不是题面缺陷；本次未发现真正阻碍静态定位的公开信息缺口。

## 4. 开发需求表与最小公开验证

将 issue 目标、harness 操作指令和环境声明分开：

- issue 目标来自 `user_prompt.txt:3-16`。
- `public_bundle.json:1` 的 public_hints 要求编辑非测试源码、禁止改测试、测试保持窄范围、完成后简要总结。它可在公开 bundle 中读取，不因未写入 user_prompt 就视作隐藏。
- 同一字段称 conda 的 testbed 环境已激活；这只是待验声明。`environment_brief.md:3-12,20-26` 明确真实消息、shell、依赖与 actor 身份仍待验证，并指出旧“所有测试修改都会恢复、永不计分”说明不能代表当前机制。当前禁止改测试指令是否实际应用仍需协调者核对，本角色不自行取消。
- 环境说明给出计划工作目录 /testbed、bash/edit、agent/54321、默认 2 CPU/4 GiB 等条件；它同时明确未验证本题实际资源、预装资产和运行能力（`environment_brief.md:8-13`）。这些不是运行通过证据。

| 操作、资产或服务 | 公开依据 | 环境说明支持到哪层与缺口 | 最小建议及预期 |
| --- | --- | --- | --- |
| 在 /testbed 使用当前源码及可导入的 pandas/NumPy | `public_bundle.json:1`；`base/pyproject.toml:24-30` 要求 Python ≥3.8 及 NumPy/dateutil/pytz；`base/README.md:101-120` | 仅声明已激活 testbed；未验证解释器、实际导入位置、依赖版本或编译扩展。 | V1（建议，未执行）：应打印实际解释器及源码导入位置并成功导入。导入失败或导到无关已安装包，应先记录环境问题，不能算题面复现结果。 |
| 题面小型内存复现 | `user_prompt.txt:6-14`；静态路径 `base/pandas/core/indexes/multi.py:3749-3753,578-580` | 输入全由代码内构造，不见数据集、凭证、数据库或外部服务需求；资源仍未实测。 | V2（建议，未执行）：未修复基线预计在 isin([]) 处抛题面 TypeError；修复后通过 dtype、形状和全 False 断言。 |
| 现有窄范围 pytest | `base/pandas/tests/indexes/multi/test_isin.py:1-87`；`base/pyproject.toml:58,388-394`；`base/pandas/conftest.py:39-50,369-374` 导入 hypothesis 并提供缺失值 fixture | test_isin 内容只构造内存对象，不见外部文件/网络 fixture；收集仍依赖 pandas conftest 与测试包。pytest/hypothesis 等是否可导入待验。pytest 默认生成 test-data.xml，需可写目录。 | V3（建议，未执行）：该模块应正常收集且通过；这是旧行为保护，须与 V2 合用。V4 是可选相邻构造器保护。 |
| 必要时恢复本地构建能力 | `base/doc/source/development/contributing_environment.rst:9-10,207-228`；`base/pyproject.toml:1-10` | pandas 从源码运行依赖已构建扩展或 C/C++ 工具链与构建依赖。镜像是否已有产物、可写位置及 4 GiB 下构建是否可行均未知；公网下载不能假定可用。 | B1（建议，未执行）仅在缺构建产物且依赖已备齐时作为候选构建步骤；若已有可导入源码环境，纯 Python 修复不需先重建。无依据要求全仓构建或全仓测试。 |

以下命令仅供后续实际 actor 在 /testbed 中验证，本角色全部未执行：

**V1：建议，未执行——导入与位置检查**

```bash
python -c "import sys, numpy, pandas; print(sys.executable); print(pandas.__file__); print(pandas.__version__, numpy.__version__)"
```

**V2：建议，未执行——题面最小复现**

```bash
python - <<'PY'
import numpy as np
import pandas as pd

df = pd.DataFrame({'a': [1, 1, 2], 'b': [3, 4, 5]}).set_index(['a', 'b'])
result = df.index.isin([])
assert isinstance(result, np.ndarray)
assert result.dtype == np.dtype(bool)
assert result.shape == (3,)
assert np.array_equal(result, np.array([False, False, False]))
print(result)
PY
```

**V3：建议，未执行——已有直接相关测试**

```bash
python -m pytest pandas/tests/indexes/multi/test_isin.py -q
```

**V4：建议，未执行——可选构造器合同保护，尤其在改动触及构造路径时**

```bash
python -m pytest pandas/tests/indexes/multi/test_constructors.py -q -k from_tuples
```

**B1：建议，未执行——仅在需要时的条件构建入口**

```bash
python setup.py build_ext -j 2
```

B1 根据本仓文档的 build_ext 命令把并发数从 4 调到公开默认 2 CPU；它不独自证明完整可导入环境已建立。文档随后还有 editable install 步骤（`base/doc/source/development/contributing_environment.rst:213-214`），是否需要及其离线依赖、写权限应由环境验证判断，本审查不执行安装或下载。

V2 通过后，合理的少量补充探针包括：空 tuple/set/iterator/一维 ndarray/Index；空的 self；有/无 level 名称；三层 MultiIndex；重复索引；空候选配合法与非法 level。预期仍由上表合同决定。这是公开语义的建议覆盖，不是对隐藏验收内容的推断。

## 5. 阅读范围与关键未知

实际打开或检索的公开文件：

- `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- `base/pandas/core/indexes/multi.py`（构造器和 isin 相关片段）、`base/pandas/core/indexes/base.py`（isin 文档、get_indexer/get_indexer_for 相关片段）、`base/pandas/core/algorithms.py:452-540`、`base/pandas/core/generic.py:4530-4625`。
- `base/pandas/tests/indexes/multi/test_isin.py` 全文件；`base/pandas/tests/indexes/multi/test_constructors.py:328-401`；`base/pandas/tests/indexes/test_base.py:768-819,870-925`；`base/pandas/conftest.py` 的导入、pytest 选项及 nulls_fixture 片段。
- `base/README.md`、`base/pyproject.toml`、`base/environment.yml`、`base/doc/source/development/contributing_environment.rst`、`base/doc/source/development/contributing_codebase.rst` 的依赖、构建及测试相关内容；曾检索 `base/setup.cfg`。
- 在上述本题 base 内用文件名/文本检索定位相关文件，检索了 `pandas/core/indexing.py` 及 `pandas/tests/indexes/base_class`、`pandas/tests/indexes/common.py` 的 isin 线索，未全面阅读它们。尝试读取路径 `base/conftest.py` 的检索返回该文件不存在；实际公共配置位于 `base/pandas/conftest.py`。未据此认定环境缺文件。

关键未知：

1. 实际 actor 能否从 /testbed 导入本次源码、依赖和 C 扩展是否匹配、上述命令能否收集和运行，均需后续 CPU 验证。没有执行结果可报告。
2. public_hints 进入真实 CLI 消息的位置、实际工具环境、禁止改测试指令的本次适用状态及具体文件恢复机制，仍是共享输入/运行条件问题。公开源码显示可只改非测试实现，未见该指令必然阻断合理修复。
3. 题面只直接复现空列表；“empty iterable”的合理泛化有接口与构造器证据，但异常自定义容器、无效维度等边界没有穷尽定义。输出类型歧义可由公开 API 与测试消解，不需要要求用户改题。
4. 未复核 1.5.x/2.0.x 历史、未读公开祖先历史、未检查外链、未做全仓调用者或测试穷举。现有材料足以提出本地最小验证，当前不需请求额外外链或历史。

`user_prompt.txt` 只是静态渲染，不能代表已捕获的真实模型消息。`base/` 是源码导出，不是完整运行容器；`base_identity.json:8-15` 记录没有 symlink、LFS 缺件或 gitlink，并声明导出校验状态，这不等于运行环境已验证。本次无修复代码、无项目执行、无测试改动、无网络访问，也不对题目给出通过/淘汰标签。

