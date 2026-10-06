# dask__dask-7138 独立公开静态审查

## 范围与证据属性

仅阅读派发卡、public_reader 角色卡和本题公开目录。以下 `P` 指 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7138`，源码路径均相对 `P/base`。未运行、导入或修改项目，未执行测试、网络或实验；本报告中的验证命令均为建议，未执行。

`base_identity.json` 声明 base_commit 为 `9bb586a6b8fac1983b7cea3ab399719f93dbbb29`，这是静态导出身份，不能证明实际 actor 工作树初态。`user_prompt.txt` 是计划输入；实际用户消息、系统消息、提示交付、工具及权限均 unknown。镜像名、摘要、`/testbed` 和预激活 conda 环境仅是公开字段声明，未验核。

## 先按题面的需求解读

目标：`dask.array.ravel([0,0])` 应接受列表形式的 array_like，正常返回展平结果，其值与 `numpy.ravel([0,0])` 一致。题面将一般 array_like 接受能力作为目的，并提出先转换再 reshape 的实现方向。

合理旧行为：原来可正常展平的 Dask 数组应继续工作，保持元素顺序、形状及 dtype；不应为了接受列表而提前计算既有惰性数组。题面也承认原函数能处理带 reshape 的数组，不能将所有数组旧行为视为错误。

初始疑义：`asasanyarray` 是否为笔误；转换后的返回类型及 ndarray 子类语义；是否要求改形参名为 `array_like`；是否要求所有 NumPy ravel 参数和行为完全兼容；测试新增建议如何与公开提示“不修改测试文件”协调；`numpy.append` 的动机是否隐含单独修改 append。

公开 bundle 的 hints 要求修改非测试源码、允许窄测试并说明测试修改不计入评分。若这些 hints 实际交付，应以不改测试为工作约束，可用临时命令检查回归；不能据题面的测试建议要求提交测试改动。但实际 hints 是否交付仍 unknown。派发卡的静态审查禁令只约束本次审查，不是原题修复约束。

## 源码和旧测试能够消解的事项

1. 根因直接可见：`dask/array/routines.py:1196–1198` 的 `ravel(array)` 直接 `return array.reshape((-1,))`。列表没有 reshape，足以静态解释题面 AttributeError；本次没有重现运行证据。
2. 正确可复用符号为 `asanyarray`：同文件 24–38 已导入它，`core.py:4058–4095` 给出实现和文档。题面 `asasanyarray` 应理解为拼写错误，不宜照抄成未定义符号。
3. `asanyarray` 文档承诺返回 Dask array、保留 ndarray 子类作为 chunks；普通无 shape 列表经 `np.asanyarray` 后 `from_array(..., chunks=a.shape, asarray=False)` 包装，既有 `Array` 在 4085–4086 原样返回。`asarray` 也接受列表，但转换和分块细节不同，不能仅凭列表样例认定二者完全等价。`test_array_core.py:2499–2507,2546–2553` 已分别检验列表、Array 身份、混合 Dask 元素列表及 matrix chunk 保留。
4. 公共入口为 `dask/array/__init__.py:27–36` 导出的 ravel；`core.py:1855–1861` 的方法和 flatten 别名也通过该函数。`core.py:1870–1881` 将 reshape 委托给专门实现。因而函数内归一化能同时服务函数和方法调用，不必另改导出或方法。
5. `test_routines.py:954–986` 覆盖 Dask 0/1/2/3 维、不同 chunks、任务图大小、flatten、函数入口和未知长度的一维 ravel。所读该组测试确实没有直接传列表给 da.ravel。保留这些断言比只检查“没有异常”更能约束回归。
6. `reshape.py:146–238` 文档及代码明确现有 row-major 假设、reshape 限制、1D 的 -1 快速返回（192–195），以及图构建。题面输入转换修复不应顺带要求取消这些限制或新增 order 参数。
7. `docs/source/array-api.rst:30–31,174,430–431,571` 把 asanyarray、asarray、ravel 列为公开 API；`docs/source/array-creation.rst:37–46` 说明包装数组的惰性设计。没有发现题目必须依赖外部服务或数据文件的直接证据。

## 合理实现范围与剩余不确定性

最小合理方向是在 ravel 函数的 reshape 前使用已有 Dask `asanyarray`，保留当前 reshape 路径及装饰器。这是公开信息可推导的方案，不是对 gold 的观察。本审查不实施补丁，也不要求唯一文本写法。

形参命名不是功能目标：保留 `array` 有利于已有 `array=` 关键字兼容；题面示例的 `array_like` 更像输入类别说明，没有充分依据要求破坏该兼容。可以用等价的局部变量表达归一化，但不应通过 NumPy 强制计算 Dask 数组，也不应只针对 `[0,0]` 特判。

返回 Dask array 是所选公开转换 API 的明确语义，即使旧代码对 NumPy 输入可能直接返回 NumPy reshape 结果。该变化与 Dask 公开接口惯例一致；题面本身没有单独写明返回类型。子类“作为 chunk 保留”不等于所有子类 ravel 都与 NumPy 完全同形；matrix、自定义 array protocol、ragged 输入、第三方后端的精确边界未充分验证，不作全覆盖承诺。标量、空序列和嵌套规则列表是合理的小型回归样本，仍需实际运行确认。

题面提及 append 是修复动机，所读材料不足以要求单独改动 append 或修复所有间接 NumPy 调用。没有读取 append 实现，不能声称其集成结果。未知长度多维 reshape 限制是既有行为，也不应从本题推导全面支持要求。

## 开发需求表

以下命令应在后续实际 actor 环境获得对应授权后执行，本次均未执行；表中代码路径相对该环境的 `/testbed`。

| 操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
| --- | --- | --- | --- |
| 确认源码初态与可编辑位置 | prompt 声明 `/testbed` 和 base commit；hints 指向非测试源码 | 静态 base 具备相关文件；实际 HEAD、status、初始改动、可写权限 unknown | `cd /testbed && git rev-parse HEAD && git status --short && git diff -- dask/array/routines.py`；核对 commit 与初态，不能预设工作树干净 |
| Python 和本地 Dask 导入 | hints 声明预激活 testbed；setup.py:70 Python >=3.6 | 解释器、conda、PATH、导入来源、工具是否可用 unknown | `python -c "import sys,dask; print(sys.executable); print(dask.__file__)"`；应指向获授权环境与待修源码 |
| 基础依赖及测试工具 | setup.py:10–11 array 依赖 NumPy >=1.15.1、toolz >=0.8.2；31 pyyaml；73 pytest；test_routines.py:4–10 | 声明已读；安装版本与兼容性 unknown；不推断缺包 | `python -c "import numpy,toolz,yaml,pytest; print(numpy.__version__,toolz.__version__,pytest.__version__)"`；导入成功并记录版本；这不是完整依赖锁定 |
| 验证直接问题及 array_like 扩展 | prompt 列表样例；routines.py:1197–1198；core.py:4058–4095 | 根因静态可见，实际修复及执行结果 unknown | `python -c "import numpy as np; import dask.array as da; from dask.array.utils import assert_eq; xs=([0,0],((1,2),(3,4)),[],7,np.arange(6).reshape(2,3)); [(assert_eq(da.ravel(x),np.ravel(x))) for x in xs]; assert all(isinstance(da.ravel(x),da.Array) for x in xs)"`；样本值、形状、dtype 对齐且返回 Dask array；旧列表路径预期 AttributeError |
| 保护既有 Dask 行为 | test_routines.py:954–986 | 旧测试文本已读，执行通过情况 unknown | `python -m pytest -q dask/array/tests/test_routines.py::test_ravel dask/array/tests/test_routines.py::test_ravel_1D_no_op`；两项应通过，保留图大小和未知长度 1D 支持 |
| 编辑约束与成果检查 | public_hints 要求非测试源码 | hints 交付、实际工具 bash/edit 权限 unknown | `git diff --stat && git diff -- dask/array/routines.py`；应显示与输入转换直接相关的源码变更，无测试文件改动 |
| 数据、网络与计算资源 | 题面内存列表；上述旧测试使用内存随机数组 | 未发现最小修复需外部数据、网络、GPU 或服务；实际资源/网络权限 unknown | 以上小型复现与窄测试即可作为最低验证；无必要网络验证命令，也不据此推断环境网络状态 |

## 实际阅读记录及未读范围

完整读取：派发卡、角色卡、`P/user_prompt.txt`、`environment_brief.md`、`base_identity.json`、`public_bundle.json`；`setup.py:1–77`、`setup.cfg:1–46`。

源码/测试实际读到的区段：`routines.py:1–65,1170–1210`；`core.py:1840–1895,4010–4110`；`reshape.py:130–238`；`__init__.py:1–45`；`test_routines.py:1–75,945–995`；`test_array_core.py:2495–2510,2545–2556`。文档读到 `array-creation.rst:1–95` 及 `array-api.rst:20–35,160–180,425–433,567–573`。另在相关文件用 rg 定位 ravel/asarray/asanyarray，文件名清单用于定位；搜索命中不等于完整阅读所在文件。

未读：其他源码和测试的主体、pytest fixtures/conftest、完整导入链、第三方库实现、未来历史、私有材料、gold、隐藏测试、其他题和其他角色结果。没有把静态导出缺失项当作镜像缺失项。本报告仅给出公开静态开发判断，不宣称实际 actor 资格、训练资格或成功率。
