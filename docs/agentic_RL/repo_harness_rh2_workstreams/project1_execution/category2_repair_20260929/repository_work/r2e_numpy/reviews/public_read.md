# NumPy 修订题面：新公开读者报告

整理日期：2026-10-03。性质：非作者的公开材料静态核查；没有运行验证。

## 结论

修订题面足以推导本题的核心要求：一维 masked array 的 `repr` 数据区应按 NumPy 当前打印选项选择摘要或全量显示；摘要中实际省略的中间元素应有省略号，全量显示不得先行丢掉中间值。题面 Actual 的元素范围与公开初态源码一致。未发现要求扩张至性能或多维处理，也未发现修法、隐藏测试或评分细节泄漏。

“after a certain number of elements” 单独看不够具体，但紧接着的打印选项约束已经明确：不能把示例的首尾各三项或任何固定截断长度当作所有情况下的要求。这里没有阻碍实现的实质歧义。公开预期输出是默认选项下的示例；本报告不把文本块的每处空格、换行或末尾换行推定为独立验收条件。

## 阅读范围与隔离声明

仅阅读了以下材料：

- 本题 `public/user_prompt.txt`、`public/public_bundle.json`、`public/environment_brief.md`、`public/problem_statement.txt`。
- 指定公开初态 `runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/worktree/` 中的 `numpy/ma/core.py`、`numpy/core/arrayprint.py`、`numpy/ma/tests/test_core.py`、`CONTRIBUTING.md` 的相关片段；在该公开工作树内做过轻量文本检索和文件名检索。

没有阅读 sibling `private/`、历史审查、gold、隐藏测试、`revision_draft`、`acceptance_matrix`、`static_checks`、`publication_handoff` 或其他题。没有私有材料暴露，没有据评分断言反推要求。未运行 NumPy、测试、Docker、远端命令，也未安装依赖；本次只运行文本读取、检索和本报告写入。

## 公开题面能支持的实现范围

1. 修复示例的一维 masked array：`a = np.ma.arange(2000)`，索引 `1:50` 被遮蔽，默认表示中数据区应显示首尾摘要，并用省略号表示中间被省略的值。
2. 保留打印选项的实际意义：应以原数组元素数量判断是否摘要，尊重摘要首尾保留数量；选项要求全量时，应显示所有元素的位置，遮蔽位置仍使用 masked 标记。
3. 保持既有 masked array 表示的基本结构与小数组行为。公开 `test_str_repr` 已说明 `[0 -- 2]`、`mask` 和 `fill_value` 的既有表示。题面没有要求重新设计这些字段。

公开 `MaskedArray.__repr__` 的数据区来自 `str(self)`，因此合理的源码调查和修改范围包含共享的 `__str__` 路径；这不是把任务扩大为任意字符串 API 重构。题面不指定必须使用哪一段辅助函数或哪一种实现算法，也没有要求性能优化、多维行为设计或全项目审查。公开提示要求只修改非测试源码，验证时可运行现有公开测试。

## Actual 与公开初态是否一致

一致，依据为以下静态调用链；这不是实测输出记录：

- `numpy/ma/core.py:2713` 定义 `_print_width = 100`。
- `numpy/ma/core.py:3189` 的赋值逻辑说明 `a[1:50] = np.ma.masked` 将索引 1 至 49 的 mask 置为真，共 49 项。
- `numpy/ma/core.py:3767` 的 `__str__` 在普通 dtype 且有 mask 的路径中，对超过 `_print_width` 的轴先保留首尾各 50 项，然后转换为 object array 并插入 masked 显示标记。对本题数组，保留下来的索引为 0 至 49、1950 至 1999，共 100 项；索引 50 至 1949 的 1900 项已经从待打印数据中消失。
- `numpy/ma/core.py:3830` 附近的 `__repr__` 把 `str(self)` 用于数据字段，却直接对完整的 `self._mask` 求字符串。
- `numpy/core/arrayprint.py:38` 附近的默认打印设置为 `threshold=1000`、`edgeitems=3`；`:252` 附近仅在待打印数组的 `size > threshold` 时启用摘要。被预先缩为 100 项的数据区因此没有摘要省略号；完整的 2000 项 mask 则进入摘要分支。

所以题面所述“0、49 个 masked 值、1950 至 1999；没有省略号”的数据内容，以及 mask 有摘要的差别，都能从公开初态解释。默认 masked 标记为 `--`，整数默认 `fill_value` 为 `999999`，也有公开源码和小数组测试支持。未实测核对 Actual 文本块逐字符的行宽与排版。

## 打印选项怎样影响一维数组

`threshold` 是启用摘要的总元素数阈值，不是允许显示的最大元素数量。此公开版本的判断是严格的 `size > threshold`：2000 项数组在默认 1000 下进入摘要；设为 2000 或更大时应全量显示。该版本直接存储阈值并作比较，`threshold=np.inf` 同样可以关闭有限大小数组的摘要。

`edgeitems` 是摘要时首尾各保留多少项，默认各三项。对本题默认例子，前三项是 `0 -- --`，末三项是 `1997 1998 1999`，中间省略须明确可见。`numpy/core/arrayprint.py:473` 附近还说明：即使超过阈值，一维数组长度不大于 `2 * edgeitems` 时，也没有需要省略的中间区间，应显示所有项；例如本题设 `edgeitems=1000` 就覆盖了完整数组。不能因为启用了摘要判断就强行插入省略号。

`linewidth` 只决定换行，不能成为丢元素的理由。题面的打印选项约束至少明确覆盖摘要与全量之间的选择、首尾数量以及换行不丢值；没有据此新增浮点精度、自定义 formatter 或其他类型打印的专门修复任务。本报告也不推断任何隐藏验证用例。

## 歧义、扩张与泄漏检查

- `user_prompt.txt` 和 bundle 的问题正文与独立 `problem_statement.txt` 在本次阅读中表达相同需求；wrapper 只补充仓库和 base commit。
- Actual 给出公开可复现的初态现象与元素范围，不给出具体修复步骤。新增“选项请求全量时不得静默丢值”是在限定显示正确性的语义，不是新增性能或多维目标。
- 未见内部函数名、指定 patch、隐藏测试路径、评分断言、私有预期或对解法的强制选择。bundle 中的“由另一组测试评判”只是公开作业提示，没有透露那组测试的内容。
- `environment_brief.md` 说明这是静态快照，缺少编译扩展、`.venv` 等忽略产物，不能在这个快照未运行的情况下声称容器不可解。其 `/testbed`、Python 3.7.9、已有 venv、无 pip 和无联网条件与本题开发方式相容；这些环境条件来自公开说明，本轮没有重新实测。

## 最少必要公开开发命令（均未运行）

以下命令面向题目描述的实际 `/testbed` 环境，不是当前静态快照。无需联网或安装包；使用 `python` 和 `python -m pytest`，避免裸 `pytest` 的公开已知导入问题。

先复现默认摘要、较少首尾项、阈值要求全量以及首尾范围覆盖全数组的四种情况；保存并恢复打印设置。这里打印可人工检查的公开需求，不猜评分断言：

```bash
cd /testbed
python - <<'PY'
import numpy as np
options = np.get_printoptions()
try:
    a = np.ma.arange(2000)
    a[1:50] = np.ma.masked
    for threshold, edgeitems in [(1000, 3), (10, 2), (2000, 3), (1000, 1000)]:
        np.set_printoptions(threshold=threshold, edgeitems=edgeitems)
        print('threshold={}, edgeitems={}'.format(threshold, edgeitems))
        print(repr(a))
finally:
    np.set_printoptions(**options)
PY
```

修改非测试源码后，运行已有的小数组公开回归测试：

```bash
cd /testbed
python -m pytest numpy/ma/tests/test_core.py::TestMaskedArray::test_str_repr -q
```

上述单个公开测试只能检查既有小数组表示，不能单独证明本题的大数组修复；四种选项下的人工检查也需要实际执行后才构成运行证据。本轮到此停止，不扩展验证范围。
