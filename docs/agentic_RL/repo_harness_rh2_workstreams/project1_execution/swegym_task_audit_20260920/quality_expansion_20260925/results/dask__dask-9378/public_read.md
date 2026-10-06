# dask__dask-9378 公开静态审阅

本报告只依据角色卡与本题 PUBLIC_DIR；未执行、导入项目或测试，未联网、读私有/历史/其它报告，也未修题。下述命令仅为开发建议，不是已执行记录或强制评分规范。本角色不可见 gold，不判成功率或训练资格。

路径约定：`PUBLIC_DIR=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-9378`；下文 `base/...` 均相对于该目录。公开版本为 `8b95f983c232c1bd628e9cba0695d3ef229d290b`（`base_identity.json:3`），是静态 Git blob 导出，实际 actor 源码初态 unknown。

## 先从题面形成的判断

- 目标：为 masked Dask array 提供保留逐元素 mask 的 `ones_like`、`zeros_like`、`empty_like`。`user_prompt.txt:5–24` 对比 `da.ones_like(array).compute()` 的 `[1 1 1]` 与 NumPy 的 `[1 1 --]`；题面明确的是 mask，不是保留原数据。
- 合理旧行为：普通输入仍产生相应形状、dtype 的全一、全零或未初始化数组；不能把 `empty_like` 变成数值固定的函数。
- 初始疑义：必须改 `da.*_like`，还是新增 `da.ma.*_like`？参数、分块、shape 覆盖及 mask 填充值是否也须完全兼容？`full_like` 是否包含在范围内？题面最后一段只说 “perhaps” 使用 `map_blocks`，是方案建议，不是唯一实现规范（`user_prompt.txt:26`）。
- 公开提示约束：`public_bundle.json:1` 的 `public_hints` 声明只改 NON-TEST 源码、不改测试、验证应窄范围；其中 `/testbed`、预激活 conda `testbed`、bash/edit 工具均为来源声明。实际消息是否交付与工具/权限/依赖状态仍 unknown（`environment_brief.md:3–10`）。本审阅按角色限制不执行这些开发操作。

## 源码、文档、旧测试可以消解的部分

1. 丢失 mask 的结构性原因可静态定位：`base/dask/array/creation.py:75–84,124–133,173–182` 只向 `empty/ones/zeros` 传入形状、dtype、chunks、name 和 `a._meta`。`base/dask/array/wrap.py:60–78` 用各输出块的形状构造图；`:132–167` 对空元数据调用 NumPy `*_like` 再 broadcast。图不依赖输入数据块，不能获得它们的逐元素 mask。`base/dask/array/utils.py:23–38,81–94` 说明 meta 是零元素的类型/维度样本，不是完整 mask。题面实际运行结果未在本轮复现。
2. 不能简单归咎于 `asarray` 必然剥离 mask：`base/dask/array/core.py:4518–4520` 对已有 Dask Array 直接返回。`asanyarray` 则明确保留 ndarray 子类（`:4541–4544,4589–4615`），与 `ma.py` 现有包装惯例一致。
3. 新增 `da.ma.*_like` 有公开架构依据：`base/dask/array/ma.py:21–24,56–70,100–115` 已使用 `asanyarray` 和 `map_blocks`；该文件全篇没有三种新入口。`base/dask/array/__init__.py:2` 已导入 `ma`，普通 `da.*_like` 来自 `creation.py`（`:26–43`）。`base/docs/source/array-api.rst:352–375` 的 Masked Arrays 清单尚无这些函数，若新增接口可同步补文档。
4. `map_blocks` 默认保留输入块结构，支持显式输出 meta/dtype（`base/dask/array/core.py:523–589`）。需注意其 `dtype` 是 Dask 参数，不能假定它自动转交给 NumPy 内核；实现若支持 dtype 覆盖，应保证真实数据块也转换，不能只改元数据（`:808–814,866–879`）。`ma.masked_array` 用 `masked_dtype` 避免此类冲突已有先例（`base/dask/array/ma.py:118–121,146–151`）。
5. 普通创建接口确有 `dtype/order/chunks/name/shape`，默认继承原形状和 chunks，指定 shape 且未指定 chunks 则使用 `auto`（`base/dask/array/creation.py:31–52,239–250`）。旧 `test_arr_like`、`test_arr_like_shape` 验证形状、dtype、名称和 shape 覆盖，并跳过 `empty` 的数值比较（`base/dask/array/tests/test_creation.py:15–109`）。这些是修改普通入口时应保留的兼容性证据，不能直接推成新增 ma 接口的完整参数要求。旧测试 `:69` 比较的是常量字符串 `"order" == "F"`，因此不能据此宣称 F-order 已被有效覆盖。
6. masked 旧测试采用 NumPy 对照、多块输入、类型和 mask 检查（`base/dask/array/tests/test_masked.py:28–31,82–96,167–214,228–238`）。已读部分与全文关键字检索未发现 `*_like` 的 masked 专项旧测试；并非全部旧测试都已细读。

## 合理实现范围与保留的不确定性

最直接的公开可解释选择，是在 `dask.array.ma` 增加三个惰性、按块调用对应 NumPy ma 函数的入口，并保持未遮蔽元素为 1/0、mask 不变，`empty_like` 只约束类型、shape、dtype、mask。可以写三个显式函数，也可以共用包装辅助函数；允许从 NumPy 推断 meta 或显式提供正确 meta。不得用提前 `.compute()` 取全量 mask 来破坏 Dask 惰性模型。

也可考虑修复普通 `da.*_like` 的 masked 路径，但必须同时处理既有参数与非 masked 行为，范围明显更大。公开题面不足以把“新增 ma 入口”和“直接修普通入口”判为唯一必选答案，需在实现说明中说明所选接口。普通 `full_like` 与其它函数共享结构（`creation.py:185–236`），可作邻接影响检查；题面没有明确要求为它新增 ma 版本。

shape 改变后如何映射 mask、是否支持 `subok`、mask 的 `fill_value`/hardmask 细节及混合 masked/普通块的完整兼容范围，题面和已读旧测试未给出专门契约。不能把全局 `shape` 原样传进每块的 NumPy 调用就声称正确。合理最小实现可限定于题面明确的同形状调用；若扩大参数支持，应以目标 NumPy 版本作对照验证并说明限制。本轮未读取 NumPy 实现，也未运行核验其边界语义。

## 开发需求与最小公开验证建议

命令以未来实际 actor 的仓库根目录为前提；不建议在本静态导出中执行。每一行都需要真实环境另行取得证据。

| 需要操作/资产 | 公开依据 | 实际证据或未知 | 最小建议命令及预期现象 |
|---|---|---|---|
| 确认实际源码版本、改动范围及可编辑的非测试源码 | prompt:1；public_hints；environment_brief:3 | 静态 base 已读；actor HEAD、diff、权限 unknown | `git rev-parse HEAD`；`git status --short`；`git diff --name-only`。应解释与公开版本的关系；修复不依赖测试文件改动。 |
| Python、Dask array、NumPy 及 pytest 可用且导入本仓库 | `base/setup.py:14–15,27–42,90–94`：Python >=3.8、NumPy >=1.18、核心依赖及 pytest | 安装版本、解释器、导入路径 unknown；静态最低版本不是环境已满足证明 | `python -c 'import sys,dask,numpy,pytest; print(sys.executable); print(dask.__file__); print(numpy.__version__); print(pytest.__version__)'`。应导入所修源码，版本可识别；不推定需下载或 GPU。 |
| 验证核心新语义 | prompt:5–26；masked 旧测试 NumPy 对照模式 | 无本轮运行结果；数据可在内存自建，无外部数据资产需求 | 下方短脚本；同形状多块输入应保留 mask，ones/zeros 的未遮蔽数据与 NumPy 一致，empty 不比较未初始化数值。 |
| 保持 ma 相关旧行为 | `base/dask/array/tests/test_masked.py` | 旧测试静态存在；能否收集/通过 unknown | `python -m pytest dask/array/tests/test_masked.py -q`。预期无新增失败；跳过不能视为通过核心语义。 |
| 若修改普通创建入口，检查普通数组兼容性 | `base/dask/array/tests/test_creation.py:15–109` | 静态读取，无运行证据 | `python -m pytest dask/array/tests/test_creation.py -q -k arr_like`。预期已有形状、dtype、chunks/name 相关用例不回归。 |

核心建议脚本以新增 `da.ma` 方案为例；若实际选择修改普通入口，把 `namespace = da.ma` 改成 `namespace = da`。这项选择不是评分入口要求。

```bash
python - <<'PYTEST'
import numpy as np
import dask.array as da
namespace = da.ma
for mask in ([0, 0, 1], [1, 1, 1], [0, 0, 0]):
    x = np.ma.masked_array([2, 3, 4], mask=mask)
    dx = da.from_array(x, chunks=2, asarray=False)
    for name in ('ones_like', 'zeros_like', 'empty_like'):
        out = getattr(namespace, name)(dx)
        assert isinstance(out, da.Array)
        assert out.chunks == dx.chunks
        y = out.compute(scheduler='sync')
        expected = getattr(np.ma, name)(x)
        assert isinstance(y, np.ma.MaskedArray)
        assert y.shape == x.shape and y.dtype == x.dtype
        np.testing.assert_array_equal(np.ma.getmaskarray(y), np.ma.getmaskarray(x))
        if name != 'empty_like':
            np.testing.assert_array_equal(y.compressed(), expected.compressed())
print('mask preservation checks passed')
PYTEST
```

该脚本只覆盖核心同形状案例；dtype 覆盖、零维/空数组、不均匀多维分块及可选参数需要按实际实现范围再作窄范围对照，不能声称已覆盖。

## 实际阅读边界

- 完整读取：角色卡 `.../quality_expansion_20260925/roles/public_reader.md`；本题 `user_prompt.txt:1–26`、`environment_brief.md:1–10`、`public_bundle.json:1`、`base_identity.json:1–21`；`base/dask/array/ma.py:1–192`、`base/dask/array/wrap.py:1–217`、`base/setup.py:1–97`、`base/setup.cfg:1–89`。
- 区段读取：`base/dask/array/creation.py:1–260`；`base/dask/array/tests/test_creation.py:1–180`；`base/dask/array/tests/test_masked.py:1–240`；`base/dask/array/core.py:523–645,790–888,4457–4617`；`base/dask/array/utils.py:23–110,282–343`；`base/dask/array/__init__.py:1–48`；`base/docs/source/array-api.rst:343–385`；`base/docs/source/develop.rst:125–213`。
- 另作文件列表及限定关键词检索，涉及上述文件、`base/docs/source/array-creation.rst`、`base/dask/array/backends.py`；有较宽检索输出被截断，未视为通读证据。未读其余源码/文档/测试全文、外部链接或 NumPy 实现。列表中出现的文件名不等于已读内容。
- 实际 actor 消息、工具呈现、源码初态、环境资产与权限均 unknown；未接触隐藏测试/gold，不推断其内容。未宣称 OS 隔离或预训练无污染。
