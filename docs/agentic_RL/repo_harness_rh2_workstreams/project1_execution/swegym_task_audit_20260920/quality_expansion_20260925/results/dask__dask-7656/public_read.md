# dask__dask-7656 公开静态审阅

范围：只读角色卡及本题 PUBLIC_DIR；未执行、导入项目或测试，未联网、安装、修题或派生 agent。本文不作成功率或训练资格判断。以下 `user_prompt.txt` 等路径相对 PUBLIC_DIR：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7656`；`base/...` 是其静态导出，不是实际 actor 工作树。

## 先按题面确定的目标与疑义

- 目标：`Entry.primary_key` 使用 `dataclasses.field(init=False, repr=False)` 且没有初值时，`fun(Entry())` 建图及 `.compute()` 应成功，例子结果为 `"Hack works"`（`user_prompt.txt:11–30,49–50`）。`other_field` 默认值 4 应仍能正常传递。
- 原问题是不存在的属性被读取而触发 `AttributeError`，不是 SQL 连接问题；“Sql database entry”只是类说明，本例没有数据库操作（`user_prompt.txt:13–19,33–47`）。
- 合理保留行为：正常 dataclass 构造字段仍可传递；不能仅使这个返回常量的函数成功，就忽略 dataclass 的字段内容及其中的 Dask 对象。
- 初始疑义：是只过滤缺失属性，还是过滤所有 `init=False` 字段？已赋值的 `init=False` 属性、默认值/`default_factory`、`__post_init__` 应如何重建？是否需要覆盖其它 dataclass 遍历入口？题面没有明确这些边界。
- 题面 hack 用 `field.init or hasattr(expr, field.name)` 保留已有属性，不是“删除所有 `init=False` 字段”的明确要求（`user_prompt.txt:62–75`）。它是建议方向，不要求原样 monkey-patch 标准库。
- 来源公开提示声明 `/testbed`、预激活 conda `testbed`、允许 `bash`/`edit`、只改非测试源码及窄范围验证（`public_bundle.json:1` 的 `public_hints`、`allowed_tools`）。实际消息及 hints 是否送达均 unknown，不能把提示当作本轮已验环境事实（`environment_brief.md:3–10`）。

## 公开源码和旧测试能消解什么

1. **直接故障位置已可定位。** `base/dask/delayed.py:110–115` 的 `unpack_collections` 对 `fields(expr)` 每项无条件 `getattr(expr, f.name)`。`call_function` 在 `:609–615` 对位置参数和关键字参数都做此遍历，所以异常在建图时出现，与题面一致。直接 `delayed(obj)` 也在 `:432–433` 走此入口。
2. **题面旧版本 hack 的落点已经变化。** 当前文件 `base/dask/delayed.py:6` 直接从标准库导入 `fields, is_dataclass`，而 `base/dask/compatibility.py:1–21` 没有 `dataclass_fields`。因此不能机械照搬 traceback 或对 compatibility 同名属性打补丁；应修改当前公开源码实际使用的路径。
3. **存在相关同类入口，但不能由此声称全部是题面硬要求。** 弃用的 `to_task_dask` 仍有相同字段读取与重建形式（`base/dask/delayed.py:155–159,188–193`）。`base/dask/base.py:424–436` 的 `unpack_collections` 也无条件读取字段，供 compute/persist 等提取及重包装使用（`:373–397`）。统一边界处理是合理扩大修复范围；最小复现直接要求的是 delayed 调用路径。
4. **不能把所有 dataclass 当不透明对象。** `base/dask/tests/test_delayed.py:99–113` 要求嵌套字典中 `ADataClass(a=dask.delayed(3))` 最终解析为 3。`base/dask/tests/test_base.py:472–527` 要求提取嵌套集合、重包装 dataclass、保持类对象及 `traverse=False` 行为。`base/dask/base.py:424` 明确排除 dataclass 类对象；若修改公共遍历逻辑，应保留这点。
5. **“只加 hasattr”解决了所报缺失属性，却不自动解决全部 init=False 语义。** 三个相关入口均把读取结果作为关键字参数传入 `typ`（`base/dask/delayed.py:115,193`，`base/dask/base.py:425–436`）；`base/dask/utils.py:32–36` 的 `apply` 实际执行 `func(*args, **kwargs)`。按 dataclass 的 `init=False` 含义，已存在但不接受为构造参数的字段仍可能引发构造错误。这是静态推论，未运行证实；题面没有要求所有这类情况都成功。
6. **遍历与原样传递已有独立语义。** `delayed` 的 docstring 说明 `traverse=False` 跳过内部遍历（`base/dask/delayed.py:261–265`），旧测试验证内部 Delayed 不求值、顶层仍识别 Dask 对象（`base/dask/tests/test_delayed.py:280–312`）。不宜为本问题改变这个开关或要求用户改用它。

## 合理实现选择及仍开放的边界

- 可在相关字段枚举处仅跳过缺失的非初始化字段，或抽取内部公共辅助逻辑；两者都能保持常规字段递归处理，且无需更改用户代码或标准库全局行为。这是公开材料推得的实现空间，不是对 gold 的描述。
- `if f.init or hasattr(expr, f.name)` 与仅 `hasattr` 的差别在于：前者仍让异常缺失的初始化字段暴露错误，后者还容忍该类对象的其它不完整状态。题面只要求缺失的 `init=False` 字段，不能据此强制普遍吞掉 `AttributeError`。
- 仅向构造器传 `init=True` 字段也可满足本例，但可能丢失用户手工赋值的非初始化状态；若要支持这类状态，需要决定是否在重建后恢复字段，及如何处理 frozen、`__post_init__`、默认工厂和副作用。这属于更宽的兼容设计，公开旧测试没有给出唯一答案。题面 hack 保留已有字段的意图值得尊重，但它本身没有解决构造器限制。
- 不应从未覆盖的情况推定精确异常类型/文案、必须使用某 helper、必须扩大至所有入口，或必须支持全部 dataclass 特性。当前读到的旧测试只有普通单字段 dataclass，没有 `init=False`、frozen、`InitVar`、自定义构造器等专门断言。

## 开发需求与建议的最小公开验证

下列命令仅供实际 actor 后续验证，**本轮未运行**，不是强制评分规范；应在已核验的真实 checkout 中执行，不在此静态 base 中执行。题面声明位置为 `/testbed`，其实际存在性 unknown。

| 需要操作/资产 | 公开依据 | 实际证据或未知 | 最小公开验证命令及预期现象 |
|---|---|---|---|
| 正确源码版本和可编辑非测试源码 | `user_prompt.txt:1`；`base_identity.json:3–5`；公开 hints | 静态 base commit 为 `07d5ad0ab1bc8903554b37453f02cc8024460f2a`；实际 HEAD、初始 diff、权限 unknown | `pwd`；`git rev-parse HEAD`；`git status --short`；预期确认真实位置、版本及既有修改，不假定干净 |
| Python、Dask 核心依赖、pytest | `base/setup.py:22–30,63–70`；`base/docs/source/develop.rst:113–119` | 源码声明 Python >=3.7；核心依赖含 pyyaml、cloudpickle、fsspec、toolz、partd；实际解释器/依赖/导入路径 unknown | `python -c 'import sys, dataclasses, dask, pytest; print(sys.executable); print(sys.version); print(dask.__file__)'`；预期可导入且指向待修 checkout |
| 复现并确认最小问题已修 | `user_prompt.txt:11–30`；`base/dask/delayed.py:110–115` | 静态路径吻合题面异常；没有实际失败/成功结果 | 运行下面内联复现；预期输出 `Hack works`，建图及求值均不出现缺失 primary_key 异常 |
| 保护正常字段、嵌套求值、旧遍历行为 | `base/dask/tests/test_delayed.py:99–113,280–312` | 旧测试资产已读；依赖兼容及测试结果 unknown | `python -m pytest dask/tests/test_delayed.py -q -k 'delayed_with_dataclass or traverse_false'`；预期既有测试通过，不把 collection 字段留为 Delayed |
| 若改 base 或旧兼容入口，检查其回归 | `base/dask/tests/test_base.py:472–527`；`base/dask/tests/test_delayed.py:44–83` | 相关旧测试已读；实际运行 unknown | 分别执行 `python -m pytest dask/tests/test_base.py::test_unpack_collections -q` 与 `python -m pytest dask/tests/test_delayed.py::test_to_task_dask -q`；预期旧重包装、类对象、容器行为仍通过 |

建议内联复现（与题面核心相同，额外确认默认字段与嵌套 Delayed 字段；不写测试文件）：

```bash
python - <<'PY'
from dataclasses import dataclass, field
import dask

@dataclass
class Entry:
    primary_key: int = field(init=False, repr=False)
    other_field: int = field(default=4)

@dask.delayed
def fun(entry):
    assert entry.other_field == 4
    return "Hack works"

print(fun(Entry()).compute(scheduler="sync"))
assert dask.delayed(lambda entry: entry.other_field)(
    Entry(other_field=dask.delayed(4))
).compute(scheduler="sync") == 4
PY
```

此最小功能验证不涉及数据库、远程服务、GPU 或外部数据集。`base/setup.py:18` 的 delayed extra 为空；这不等于无核心依赖。根 `base/conftest.py:19–32` 可选导入 NumPy/pandas/SciPy，`base/dask/tests/test_base.py:40–44` 也探测可选包；窄测试可能仍受已安装但不兼容的可选包影响，实际状况 unknown。无需预先假定需要下载或全套完整依赖。

## 实际阅读与未读范围

- 全读：指定角色卡；`user_prompt.txt:1–113`；`environment_brief.md:1–10`；`base_identity.json:1–23`；`public_bundle.json:1`（单行 JSON 全部公开字段）；`base/setup.py:1–77`；`base/setup.cfg:1–55`；`base/conftest.py:1–46`；`base/dask/compatibility.py:1–21`。
- 源码区段：`base/dask/delayed.py:1–210,225–270,420–451,589–640`；`base/dask/base.py:350–455`；`base/dask/utils.py:25–60`。
- 旧测试区段：`base/dask/tests/test_delayed.py:1–180,270–317`；`base/dask/tests/test_base.py:1–85,455–555`。
- 文档区段：`base/docs/source/develop.rst:70–126`；`base/docs/source/delayed.rst:1–90`。另外仅查看 `rg` 的 dataclass/is_dataclass 命中行，以及上述测试和 delayed/develop/setup 的 traverse/pytest 等命中行；`changelog.rst` 仅在公开文档搜索结果中出现两个命中，没有沿链接或读取历史。
- 做过 PUBLIC_DIR 文件名清单（首个输出被截断）及定向文件名搜索；清单不代表读取全部文件。误查 `base/dask/conftest.py` 得到不存在，随后定位并读取根 `base/conftest.py`；不据此推断运行镜像缺文件。
- 未读：其余源码/测试/文档全文、任何外部链接、私有材料、Git 历史、gold、隐藏测试、其它题或其它角色报告。未读取或验证实际 actor 消息、源码初态、镜像内部资产、工具、权限或解释器；均为 unknown。此报告基于 fresh 任务上下文及约定文件边界，不宣称 OS 隔离或不存在预训练影响。
