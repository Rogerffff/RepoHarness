# dask__dask-7894 公开阅读记录

本记录仅作静态公开审查，未实际修题、导入项目或执行测试。阅读范围限派发卡、public_reader 角色说明及本题公开包；未读取私有测试、gold、history、其他题或其他角色结果。下文 `P` 指 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7894`，`base/…` 均相对 `P`。运行边界来自审查派发，不是给原题追加的要求。

## 先读题面所得目标、旧行为和疑义

题面 `P/user_prompt.txt:3–23` 要求修复 `map_overlap(..., trim=True, drop_axis=...)` 的裁剪：删除输入轴时，同步删除该轴在 `depth`、`boundary` 中的项，使剩余配置与输出轴对应。例子由 `(5, 10)` 的全一数组沿轴 0 求均值，深度 `(0, 2)`、删除轴 `(0,)`，要求计算后的形状为 `(10,)`。按例子语义，值也应仍为 1，而不是只修正 shape 元数据。

只据题面，应保留未删除轴时的既有重叠与裁剪语义；`trim=False` 不应额外裁剪；异轴配置可能在深度、边界任一项出现，不能只处理深度或只特判这个二维例子。题面没有要求改变函数实际执行的降维方法，也没有要求改变创建重叠区的方法。

读源码前的疑义包括：删除轴的参数形式、多个轴如何重新编号、负轴支持、多个输入选择谁的裁剪配置、与 `new_axis` 的组合、`chunks=(0,)` 的元数据含义以及题面环境版本。下面分别记录公开材料能消解的部分，而不把所有疑义扩大为必须新增的功能。

## 公开代码及旧测试的证据

1. **缺陷位置可静态定位。** `base/dask/array/overlap.py:658–664` 先将深度、边界转成每个输入各一份的字典；`:691–699` 创建重叠输入，调用 `map_blocks`，随后直接把所选输入的 `depth[i]`、`boundary[i]` 交给 `trim_internal`。此处没有删除轴或重新编号的步骤。`base/dask/array/core.py:685–686` 已按 `drop_axis` 从输出轴删除对应位置，因此这时输出轴与原配置不再总是一一对应。
2. **不仅要删除键，还要压紧编号。** `overlap.py:103–120` 按输出 `x.chunks` 的轴号读取配置；`:135–168` 的 `_trim` 按实际块 `x.ndim` 和 `block_info` 产生切片。保留输入轴 1 的配置但仍用键 1，会让一维输出的轴 0 读到缺省值；合理修复必须把存留轴按原顺序映射到连续输出轴号。边界为 `none` 时，外沿与内部块使用不同裁剪规则，因此只移动深度仍可能得到错误数值或尺寸。
3. **参数形式有公开依据。** `overlap.py:495–510,704–736` 定义深度的标量、tuple、dict、按输入分列的 list，以及边界的标量、tuple、dict、list；缺省深度 0，边界 `reflect`。非对称深度由字典中的二元 tuple 表示，且 `:676–683` 仅允许其边界为 `none`。修复不应破坏这些已支持的值。`core.py:477–481,659–662` 允许删除轴为 number 或 iterable，并将标量转为列表；因此整数 `drop_axis=0` 与 `(0,)` 都有依据，不能用真假值判断漏掉整数零。
4. **多输入选择规则已存在。** `overlap.py:695–699` 选择维度最高的输入，同维时取首个。应在这个参考轴空间处理删除，保持已有选择规则。`test_overlap.py:335–367,369–447` 覆盖不同维数、块对齐、不同深度与变参数输入，其中现有删除多个轴的例子使用 `trim=False`；它不是本题 `trim=True` 错位的回归覆盖。
5. **合理旧行为有具体测试。** `test_overlap.py:276–315` 覆盖普通裁剪、不同轴深度与边界、非对称深度；`:319–332` 覆盖零深度返回普通 `map_blocks` 的快捷路径；`:450–462` 覆盖 `trim=False` 默认块形状；`:712–727` 覆盖 `trim_overlap` 多种边界。`overlap.py:582–594` 公开示例还说明：删除所有轴时，函数看到的仍是扩展块，深度为 1 的求和得到 12；本题不应将删除轴理解为在函数运行前撤销该轴的重叠。
6. **文档支持裁剪的目的。** `base/docs/source/array-overlap.rst:126–130,149–179` 说明变形函数需提供 chunks，且裁剪应移除此前扩展的边界。`core.py:473–481,524–542` 说明 chunks 描述函数输出块，新增轴在删除轴之后应用。`test_array_core.py:3065–3126` 覆盖删除轴、增加轴及二者组合，但这是 `map_blocks` 的证据，不能直接当成 `map_overlap` 的所有组合已经正常工作的证据。

## 合理实现范围及仍未消解的疑义

可接受的实现方向是在 `map_overlap` 的裁剪阶段，从参考输入的已正规化字典生成删除轴后的深度、边界映射，再交给现有裁剪函数；也可用独立辅助函数表达相同语义。不要求某种代码结构或与不可见答案一致。应同时覆盖单轴、多轴、删除首轴或中间轴、整数和可迭代轴参数，并保留无删除、全部删除与不裁剪的行为。应让实际切片与块元数据使用同一份映射。

仍需保留以下边界：

- **负轴及非法轴：** 已读 `core.py:659–686` 只做标量包装，再按非负枚举位置删除；没有负轴正规化。相关已读文档、旧测试没有提供负轴契约。不能声称负轴已受支持，也不能仅在裁剪端将负轴正规化而使其与 `map_blocks` 的实际删除不同步。是否扩展负轴或改变异常属于另行确定的范围。
- **新增轴：** `map_blocks` 明确支持先删后增，且可根据 chunks 隐式新增左侧轴。公开 issue 只要求删除轴的配置同步；`map_overlap` 裁剪对显式或隐式新增轴应如何调整，没有在已读旧测试中直接规定。实际实现需避免误伤已有组合，但完整新增轴语义属于需要澄清的邻近问题，不能从题面推导出任意新轴都必须支持。
- **chunks 元数据：** 题面显式提供 `chunks=(0,)`，断言只针对 `.compute()` 后形状。源码会以该 chunks 构造映射结果，再在裁剪时扣减深度。该例可用于检验实际裁剪，但不足以建立通用零 chunks 元数据契约。建议另加 chunks 与函数输出块大小一致的例子，同时核对实际值、形状及块元数据；本次未执行，所以不报告具体运行异常或通过结果。
- **环境版本：** 题面写 Dask `2012.7.0`、Python `3.8.10`、Linux、conda-forge；公开 `setup.py:16` 的 distributed 配套版本为 `2021.07.0`。题面版本可能有笔误，但无法据此证明实际安装版本。以明确的源码声明与实际 actor 后续核验为准。

## 开发需求表

以下命令仅是将来在获得授权的实际 actor 环境中可使用的公开验证建议，本轮全部未执行。`/testbed` 只是题面声明的工作目录；不得据此认定真实工作树已位于该路径。

| 需要的操作或资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
| --- | --- | --- | --- |
| 实际消息、起始源码和可编辑工作树 | 题面首行声明 `/testbed`、commit `bf4bc7dd8dc9`；environment_brief 明确静态导出不等于 actor 初态 | 本次只见计划题面与静态 base；实际消息、HEAD、diff、权限均 unknown | 在 actor 捕获消息后，`git -C /testbed rev-parse HEAD` 与 `git -C /testbed status --short`；应能识别真实源码状态与既有改动，而非假定空净工作树 |
| Python、NumPy、Dask 必要依赖及正确导入来源 | `setup.py:12–31,71–75`；NumPy >=1.16、Python >=3.7；旧测试开头 `importorskip("numpy")` | 声明可见，实际解释器、安装依赖、激活和导入路径 unknown | 在实际源码目录执行 `python -c 'import sys, numpy, dask; print(sys.executable, numpy.__version__, dask.__file__)'`；预期可导入且指向待修源码，缺依赖应与代码失败区分 |
| 复现公开问题及核对计算值 | `user_prompt.txt:14–23` | 仅静态确认配置错位链条，未复现 | `python -c 'import dask.array as da; x=da.ones((5,10),dtype=float); y=da.map_overlap(lambda x:x.mean(0),x,depth=(0,2),drop_axis=(0,),chunks=(0,),dtype=float).compute(); assert y.shape==(10,); assert (y==1).all()'`；修复后预期两条断言成立 |
| pytest 与既有公开回归 | `setup.py:22,74`、`setup.cfg:40–52`、`conftest.py:18–32`、上述旧测试 | 文件静态存在；pytest、收集结果、兼容性及运行权限 unknown | `python -m pytest dask/array/tests/test_overlap.py -k 'map_overlap or trim_internal or trim_boundry or asymmetric_overlap_boundary_exception'`；预期被选测试运行并通过，不能把缺 NumPy 导致跳过当通过 |
| 轴变换回归与本题新增边界检查 | `core.py:477–481,659–709`；`test_array_core.py:3065–3126` | 已见旧测试；新增回归尚未编写，实际结果 unknown | `python -m pytest dask/array/tests/test_array_core.py::test_map_blocks_with_changed_dimension`；预期旧轴变换不回退。未来本题公开新增用例应覆盖异深度、异边界、多块、多轴删除与整数零，并比较计算值和有效 chunks；这不是声称已有该新增测试 |
| 本地生成的小数组与执行资源 | MCVE 仅用 `da.ones`；相关旧测试用 NumPy 生成数组 | 无证据表明本题核心复现需要外部数据、网络、服务或 GPU；实际可用资源 unknown | 上述 MCVE 本身即可验证核心资产需求；预期无需外部数据访问。不得把当前静态包未列出的资产称为 actor 缺失 |

## 实际读取及未读范围

完整读取：派发卡、`roles/public_reader.md`、`P/user_prompt.txt`、`P/environment_brief.md`、`base/setup.py`（1–78）、`base/setup.cfg`（1–55）、`base/conftest.py`（1–46）。

源码逐段读取：`base/dask/array/overlap.py:1–168,473–736`，涉及 `_overlap_internal_chunks`、`overlap_internal`、`trim_overlap`、`trim_internal`、`_trim`、完整 `map_overlap` 及配置正规化函数；此外见到 171–176 与 739–740 的相邻定义头。`base/dask/array/core.py:445–559,650–772`，涉及 `map_blocks` 参数/示例、轴变换、blockwise 调用与部分 block_info 构造；未完整读取该函数其他区段。

测试逐段读取：`base/dask/array/tests/test_overlap.py:1–35,120–132,268–483,650–688,708–750`；末端的部分测试或相邻函数只读到片段，不声称完整覆盖。`base/dask/array/tests/test_array_core.py:3054–3130`（完整相关 `test_map_blocks_with_changed_dimension` 为 3065–3126，旁侧为片段）。文档读取 `base/docs/source/array-overlap.rst:1–35,115–182`。另对上述 overlap/core 源码、两份测试和该文档执行了定向 rg，匹配输出不等于通读文件。

执行过本题公开目录的文件名枚举，其输出被截断；它只用于定位文件，不是内容阅读。未读取 `public_bundle.json`、`base_identity.json`，没有跟随文档或测试里的 URL；未读剩余源码/文档/测试内容，没有读取私有材料或历史。本报告不判定实际 actor 资格、训练适用性或成功率；所有实际运行条件与结果仍为 unknown。
