# dask__dask-7305 独立公开静态阅读

## 题面优先的需求理解

先读取 `user_prompt.txt`、公开环境说明和身份说明，再查源码及旧测试。仅据题面，目标是使 `dask.dataframe.partitionquantiles.partition_quantiles` 在大整数输入上返回正确最小值和最大值。两元素 uint64 示例的期望端点是 **612509347682975743**、**616762138058293247**，不能分别增加 1。输出示例的 Series 名为 a，索引为 0.0、1.0，dtype 为 uint64；保持这些合理旧行为比只打印正确数字更符合原接口。

题面关联 `set_index`：未排序数据的最小值位于末尾时，不应因 divisions 下界大于真实最小值而放错分区。实际 CSV 未公开，但核心分位数错误已有完全自包含的两整数示例，不需要原始 CSV 才能开展该核心修复。题面的“buffer overflow”是报告者猜测，不能当作根因；`index.min().compute()` dtype 从 uint64 变为 int64 是额外观察，是否必须同时修复所有标量归约的 dtype 未明确。标题聚焦无符号大整数，正文也写 large integer inputs，因此相邻有符号大整数精度是合理回归范围，不意味着无限扩展所有 dtype 的行为。

公开 `public_bundle.json.public_hints` 声明仅改非测试源码、可运行窄测试、/testbed 的 testbed conda 环境已激活。这里只记录来源约束；提示是否实际交付、环境是否就绪均 unknown。本审查的禁止执行等边界不构成原题的新要求。

## 公开代码能消解的事项

以下路径均相对于本题公开包的 `base/`，完整根目录是 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7305/base`。

1. **分位数允许近似，但端点承担真实边界职责。** `dask/dataframe/partitionquantiles.py:1–68` 说明算法无统计保证、用于近似分区；其中 48–54 明确需要全局 min/max，取各分区 0th/100th percentile。`sample_percentiles:144–157` 包含端点。`docs/source/dataframe-design.rst:81–121` 说明 divisions 的索引边界用途。因此“近似算法”不能成为示例端点取错值的理由；也不能要求所有内部百分位都等于精确 Pandas 分位数。
2. **存在直接的数值精度风险链。** `percentiles_summary`（386–420）默认 `interpolation="linear"`；只对分类数据改为 nearest。整数会在 `_percentile` 后通过 `np.round(vals).astype(data.dtype)` 转回原类型（417–418）。`dask/array/percentile.py:_percentile:13–34` 对数值输入调用 `np.percentile`；57–76 的接口文档描述 linear 的分数插值。大整数经过浮点线性插值再转回整数，可能丢失低位；转回 uint64 并不能恢复已经丢失的值。报告中“两个值各加 1”的形态与这一精度机制相符，比尚无证据的缓冲区溢出解释更有公开依据。这是静态根因候选，未执行 NumPy 或读取其内部实现，具体依赖版本下的逐步输出仍 unknown。
3. **仅处理第一处插值还不足以覆盖所有合理输入。** `percentiles_to_weights:259–263` 将值转列表；`merge_and_compress_summaries:274–293` 合并并压缩相等值；`process_val_weights:319–343` 将列表重新构造成未显式指定 dtype 的数组，且唯一值不足 `npartitions + 1` 时用 `np.interp` 补 divisions；381–382 最后才转回输入 dtype。因此必须审查下采样和补边界分支以及无符号类型恢复，不能从两元素、一个输出分区成功推出所有大整数正确。空数据、分类、带时区 datetime 各有独立处理（312–317、375–380）。这里不声称已证实未显式 dtype 的构造对每种输入都会失败。
4. **与 set_index 的关系有公开调用证据。** `core.py:3029–3033` 将 `_repartition_quantiles` 接到此函数。`shuffle.py:487–493` 计算 divisions，并在 522–530 对已经排序的输入使用分区 min/max 快捷路径；验证乱序症状须避免仅覆盖该快捷路径。`shuffle.py:605–614` 已用目标 dtype 构造非空整数 divisions，说明“所有 divisions 从未保持 dtype”并不成立；下游恢复类型也不能修复上游数值丢失。`set_partitions_pre:1090–1093` 用 searchsorted 减 1，仅对达到最大边界的值特殊处理；若最小值小于首边界，该表达式可能产生 -1。没有继续阅读所有 shuffle 路由，故不把“必然进入末分区”写成已验证结论。
5. **旧测试限制可接受实现。** `test_shuffle.py:test_set_index_interpolate:608–619` 要求小整数 x 的 divisions 集合为 {1,2,3,4}，并要求浮点 y 的两个内部分界严格处于 1 与 2 之间；`test_set_index_interpolate_int:622–627` 要求整数 divisions。`test_set_index_timezone:630–656`、`test_set_index_datetime_precision:671–688`、`test_set_index_empty_partition:783–800`、`test_set_index_on_empty:803–817`、`test_set_index_categorical:820–833` 约束时区、日期精度、空数据及分类顺序。全局取消所有线性插值可能破坏这些公开旧行为。

## 合理实现范围与待保留疑义

合理实现可以在整数摘要阶段选用保持原整数值的离散分位选择，同时在不足样本分支提供不会损坏端点的处理；也可以保留允许的插值路径并另行精确保留、合并、恢复端点，或采用精确整数计算。公开需求没有指定某个补丁、插值名称或内部 helper。任何方案都应检查大整数端点、Series dtype、顺序与分区边界，并保持小整数补间和非整数类型旧行为。选择离散分位可能改变内部近似分界，需以旧测试与公开算法契约判断，不能要求与不可见答案实现一致。

仍 unknown：实际 actor 收到的消息与提示、实际工作树 HEAD/status/初始改动、权限和工具、依赖版本及导入位置、原 CSV 内容、实际 runtime 复现、隐藏测试覆盖范围。没有进一步追踪标量 min reduction，因此其 dtype 变化原因和是否独立缺陷均未判定。对 uint64 上界、混合跨越 int64 上界的值、空值/扩展整数类型的全部行为没有静态证明；这些是候选边界验证，不能当作题面已要求的完整新增 API。

## 开发需求表

下列命令是供后续获准的实际开发环境核验的建议，本轮**一条也未执行**；假定工作目录为实际 /testbed，不能在静态 base 导出上宣称测试结果。

| 操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
|---|---|---|---|
| 确认源码初态与编辑权限 | user_prompt 指定 commit；public_hints 指定 /testbed 与非测试源码修改 | base_identity 声明静态 commit 为 8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0；实际 actor worktree/权限 unknown | `pwd`；`git rev-parse HEAD`；`git status --short`；`test -w dask/dataframe/partitionquantiles.py`。应核对实际位置、commit 和允许初始改动，源码可编辑；不能由静态导出替代。 |
| 可用 Python、NumPy、Pandas、Dask 与 pytest | 示例导入；setup.py:10–24,31,70–74 给出 dataframe 依赖和 pytest | 实際版本、激活环境、导入路径 unknown | `python -c "import sys,numpy,pandas,dask,pytest; print(sys.executable,numpy.__version__,pandas.__version__,dask.__file__)"`。应导入成功且 dask 来自待修工作树；不需要安装或网络作为题目固有步骤。 |
| 精确最小复现，不需要私有数据 | user_prompt 两元素示例 | 数值和 dtype 明确；执行现象 unknown | 运行下方最小命令，应得到两个原始 uint64 端点、名称 a、分位索引 0.0/1.0；修复前观察值需现场确认。 |
| 小范围公开回归 | test_shuffle.py 上述已有测试；develop.rst:107–115 的 pytest 指南 | 测试文件已静态读取，测试运行与收集依赖 unknown | `python -m pytest dask/dataframe/tests/test_shuffle.py -q -k 'set_index_interpolate or set_index_timezone or set_index_datetime_precision or set_index_empty_partition or set_index_on_empty or set_index_categorical'`。上述旧行为均应通过；不修改旧测试。 |
| 乱序分区集成与边界数据 | issue 的 set_index 症状；shuffle.py:487–530,1090–1093 | 核心路径公开；原 CSV 未给出，实际分区路由 unknown | 先以 `python -m pytest dask/dataframe/tests/test_shuffle.py::test_set_index -q` 检查公开普通集成；另用内存 uint64 合成乱序多分区并把最小值放末尾，检查首尾 divisions 等于真实端点、各分区索引落在其范围内且与 Pandas set_index 数据一致。需额外覆盖一个/多个输出分区、重复与不足唯一值、大有符号整数；这些检查应使用精确整数比较，不能仅用浮点容差。 |

最小命令（不写或改测试文件）：

```sh
python - <<'PYCODE'
import numpy as np
import pandas as pd
import dask.dataframe as dd
from dask.dataframe.partitionquantiles import partition_quantiles
values = [612509347682975743, 616762138058293247]
pdf = pd.DataFrame({'a': np.array(values, dtype=np.uint64)})
r = partition_quantiles(dd.from_pandas(pdf, npartitions=1).a, npartitions=1).compute()
assert [int(x) for x in r] == values
assert r.dtype == np.dtype('uint64')
assert r.name == 'a' and list(r.index) == [0.0, 1.0]
print(r)
PYCODE
```

合成数据足以验证核心问题；没有公开依据要求网络、GPU、分布式集群、外部服务或原始 CSV。验证中可能需要的本地临时空间和 shuffle 依赖仍须在 actor 身份核对。setup.py 的最低依赖范围不是对所有现代版本组合兼容的保证。

## 阅读范围与封存声明

完整读取：本题派发卡、public_reader 角色卡；本题 `user_prompt.txt`、`environment_brief.md`、`base_identity.json`、`public_bundle.json`；`base/dask/dataframe/partitionquantiles.py:1–483`；`base/setup.py:1–77`。

局部读取：`base/dask/array/percentile.py:1–90`；`base/dask/dataframe/core.py:3024–3036`；`base/dask/dataframe/shuffle.py:480–530,600–625,1088–1102`；`base/dask/dataframe/tests/test_shuffle.py:1–75,580–690,780–845`；`base/docs/source/dataframe-design.rst:75–128`；`base/docs/source/develop.rst:1–140`。在本题公开文件内运行了文件清单与相关符号 rg 搜索，`test_dataframe.py` 仅见 quantile 搜索命中，未读其测试函数正文。清单输出截断部分不视作内容已读。

未读取其余源码/文档/测试正文、公开文件中的外部链接、私有材料、历史、其他题、其他角色结果或根汇总。没有执行或导入项目、运行测试、安装、联网、实验或实际修题；唯一写入为本报告。此报告仅为独立静态判断，不代表 OS 隔离、实际 actor 环境验核、成功率或训练资格。保存并计算 SHA256 后停止，不再回写。
