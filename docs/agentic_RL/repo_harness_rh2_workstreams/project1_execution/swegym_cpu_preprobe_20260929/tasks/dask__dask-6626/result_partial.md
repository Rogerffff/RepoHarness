# Dask6626：开发路径与 runner 差异部分结果

2026-09-29。**已确认公开开发缺口是pytest8与既有测试不兼容；只将pytest降至7.4.4后，真实actor的16项公开旧测全部通过，题目metadata错误继续精确复现。** 本次受控runner清单精确重建历史前后摘要，可解释差异机制；正式评分和完整私有正负对照尚待回传，本题未最终通过。

证据根目录：`runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/`。本稿只读取已完成原件；此快照的status停留在private gold开始，未因存在中间目录认定gold完成。不修改在途脚本或输入，不重复actor。

## 原条件与修订效果

两次actor均UID54321、CC2.1.205、Python3.8.19，HEAD `56cd4597630feb1b01501c16d52aa862dd257a83`，Dask从`/testbed/dask/__init__.py`导入，版本2.25.0+23.g56cd4597；pandas1.0.5、numpy1.17.5不变。初态与收尾工作树均清净。

两条题面路径的实际compute值都正确；只有Dask先分区再set_index路径的空类别metadata变成 `Index(['a','b'], dtype='object')`，实际compute和pandas先set_index路径仍为空类别。`PUBLIC_COMPUTE_PASS` 后精确在 `AssertionError: dask_set_index` 失败，说明已到达目标语义，非导入失败或任意非零。

原条件pytest8.3.2下旧测15 passed、1 failed：`test_nonempty_series_sparse` 在 `pytest.warns(None)` 抛 `TypeError: exceptions must be derived from Warning`，属开发依赖不兼容，并非本题metadata行为。修订actor只预安装pytest7.4.4，随后16 passed、2 warnings；旧API仍有弃用警告，目标bug仍可复现，修订没有把项目代码提前修好。

两次均4条Bash工具调用／5条桩消息，命令输出未截断，prelaunch和activation通过，harness日志完整、正常返回；容器、网络、relay和stub清理成功，无残留。原运行起止271秒（包括镜像准备），solve16.172秒；修订54秒、solve16.593秒。桩统计不是自主模型推理或付费成本。实际输入为Devcheck控制文本，不能据此称完整题面/public_hints交付已验证。

原actor实际image config ID `fd456e2b…`；固定registry digest `a182a6a7…`的构建记录也确认同一base，与历史ID一致。actor派生镜像`a1f28fbc…`，grader COPY-only镜像`d3befac6…`；两者分工不同。构建保留base层，pytest wheel摘要匹配。全环境pip_check仍为1：distributed/Dask、fastparquet/pandas、zarr/numpy版本约束及chest平台问题未全部清理；当前证据仅覆盖实际目标命令与相关测试。

## 本次 runner 文件差异及历史解释范围

`runner_inventory/inventory/`保存真实安装前、pin后、editable后三份81文件清单及命令输出；`runner_file_comparison.json`可追溯逐路径差异。再次直接比较三个清单得到相同结论：

| 阶段 | pytest / pluggy | runner digest | 文件变化 |
| --- | --- | --- | --- |
| 安装前 | 8.3.2 / 1.5.0 | `0f3527775c70cece62a1cb6aebd15f554bceee5d03e6f54575b5af67d5068f43` | 起点，81文件 |
| 离线pin后 | 7.4.4 / 1.5.0 | `a7b7f1e4d9d840b38dcc19daa1f46d09c0cb3e558d41c91f1c5e08dcfcb509cc` | 70路径变化：_pytest68、pytest2；含新增nose.py、移除_io/pprint.py |
| `pip install --no-deps -e .`后 | 7.4.4 / 1.5.0 | 同pin后 | 0变化，清单逐项相同 |

安装输出确认pytest8.3.2卸载、7.4.4离线安装成功；随后Dask editable安装成功。inventory matrix完整结束，清理rm/query为0、remaining为空。清单算法覆盖pytest/_pytest/pluggy的非pyc文件路径与内容，与先前冻结runner算法已静态对齐。

本次两个摘要与历史分别完全相等，因此历史摘要变化有明确、可重建的配方解释，不再仅有“可能来自降级”的猜测。但这是**本次root受控重建**，历史当时的逐文件清单仍未存在，不能倒签历史未知为完整性通过，也不将root安装等同正式grader受限身份已验。正式回传仍须核自己的安装日志和摘要是否落在该预期变化上。

## 当前私有结果及待办

已完整回传的private base重复了两路径compute正确、metadata失败及16项旧测通过。额外int64空类别控制输出：预期 `Int64Index([], dtype='int64')`，实际 `Int64Index([1,2], dtype='int64')`，在类别dtype相等断言失败。这里标量dtype仍是int64，问题是CategoricalDtype中的类别集合改变；不应误写成基础数值dtype变成object。该base变体matrix完整、清理成功。gold和fixed_object_empty的完成与具体输出，本快照尚未核验。

当前可用于公开开发配方恢复及runner差异归因证据，尚不授予正式比较／训练资格。剩余事项：读取私有gold/错误候选完整输出；核正式noop/gold/错误候选的安装消费、1个F2P与14个P2P逐参考、实际runner变化、清理；判断固定object空类别候选是否被正式评分误奖及应如何限制用途；独立结果复核；正式题面/public_hints真实交付证据。正式评分使用本批统一CPU准备上限900秒，必须与旧300条件分开记录；GPU入口、模型和预算不在本结果范围。
