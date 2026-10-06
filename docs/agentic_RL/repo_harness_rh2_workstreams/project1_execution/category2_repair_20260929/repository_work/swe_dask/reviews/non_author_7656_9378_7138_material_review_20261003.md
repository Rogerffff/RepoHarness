# Dask7656 / 9378 / 7138 材料非作者窄核

2026-10-03。结论：**三题现行材料均无静态阻断项，可以进入固定正式版本的后续 CPU 验收；本报告不授予已验证、探针或训练资格。** 每题结论和历史实证范围分别写在下文。本次为非作者静态审查，复用已有公开依据和历史独立审查，属于非 fresh 读题；未导入 Dask、运行 pytest、历史项目、容器或 SSH，未改题主材料与生产。唯一落盘文件为本报告。

本次依据本包 `preparation.md` 及三份现行 `tasks/<id>/revision.json`、有效测试、矩阵和接续计划；未把旧传输快照或原五题正式发布版本当成这三题已发布身份。8801 的原因草案因 `wrong_missing_file_reason` 已明确 not_adopted，7305 的 auto 正对照未完成，均不在本次审查范围。

静态交叉核验结果：三题各 6 份来源资产（合计 18 份）SHA 与现行登记吻合，原 test.patch 与 grading 中 test_patch 字节相同，base/public/grading/image 绑定一致；有效 patch 在各自导出 base 上 `git apply --check` 与静态应用成功，生成内容与 `effective_test.py` 逐字相同且 AST 可解析。原 F2P/P2P 数组与原 grading 的次序和内容相同；有效数组按原数组加登记追加项形成，无重复或交集。测试命令保留原 `pytest -n0 -rA  --color=no`。矩阵引用的 10 份非 noop 候选 SHA 均吻合，静态应用与 AST 通过，且只修改生产文件，不修改测试或评分。

## 7656：原 dataclass 类型、默认值与嵌套求值

**无静态阻断项。** 原 1 F2P + 48 P2P 原样保留，仅 `test_delayed_with_dataclass` 的 AST 改变；其余原模块节点不变。原 `init=False` 缺失字段和嵌套 `Delayed(3)` 场景仍在，最终字段值比较保留；增加默认值和第二个默认对象，并在被调用函数内检查 `isinstance(obj["a"], ADataClass)` 与字段值。`compute(scheduler="sync")` 只固定本测试调度方式，没有要求特定生产函数、任务图或重建算法。未要求 `post_init`、已初始化的 init=False 字段状态恢复或精确内部实现。

公开依据复用 [09-29 非作者最终审查](../../../../swegym_cpu_preprobe_20260929/reviews/dask_pair_final_review.md)：base 的两条既有 dataclass 入口取原 `typ` 重建，公开旧测试也以 dataclass 作为合法输入；题面原例有默认字段，原测试已要求嵌套 Delayed 求值。新增原类检查因此直接针对公开类型保持缺口，允许采用其它算法的正确实现，不是从 gold 反推需求。

已核矩阵冻结原件：`wrong_result_type` 在 unpack 重建时改用 `types.SimpleNamespace`，当前函数内类型检查直接针对该错误；`opaque` 保留原对象却不求值其嵌套 Delayed，原字段求值控制仍受保护。gold 的过滤缺失字段并以原类重建与这些断言相容，实际新分仍待执行。历史 09-29 正式结果是 noop/gold/opaque/wrong_result_type = **0/1/0/1**，49 个正式参考均有状态；wrong_type 同时在公开类型控制失败，因此旧材料误奖已经被实证。历史类型控制首个对象失败时嵌套分支未执行，不能外推为那次嵌套也失败。本轮新 patch 的预期 0/1/0/0 仍不是实测。

## 9378：按用户选 B 验收入口与 mask

**无静态阻断项。** 3 F2P + 134 P2P 的编号、数组和次序不变，仅原补丁新增的 `test_like_funcs` AST 改变，其余 base/原模块节点不变。对应 `da.ma` 函数存在则检查它，缺失才使用顶层 `da.<name>`，准确执行 [09-30 交接的最终 B 规格](../../../../category3_diagnosis_20260929/handover_to_category2_20260930.md)；不沿用已经撤回的强制新增 ma API 题面。题面保持原样。

三个 like 函数都比较 NumPy `getmaskarray` 的逐元素 mask；ones/zeros 继续保留原 `assert_eq(res, sol)`，empty 仍只核 mask，不读取未初始化数值。比较输出行为，没有要求 map_blocks、实现源码或 gold 的函数结构。缺 ma 入口的正确顶层修法在该分支可被接纳；存在但错误的 ma 入口不会被正确顶层入口遮掩。

`ma_mask_none` 在原 mask 为 true 的位置退化，`ma_mask_invert` 翻转全部位置，都直接被新增 mask 比较针对。新 `wrong_values_seven` 保持正确 mask，却把未屏蔽的 ones/zeros 值填成 7；mask 相等后仍保留的值比较针对该错误。它是本轮新控制，不能冒称历史 `invert_values7` 原件。矩阵的 gold 和 `toplevel_only` 分别覆盖 ma 与顶层合理路径；本次只确认静态相容，不给新 B 测试发放动态通过资格。

复用 [历史诊断及独立复核记录](../../../../category3_diagnosis_20260929/tasks/dask__dask-9378/result.md)：原材料曾给两个 mask 错解正式 1；旧 R-c 的 mask 修订诊断已拒绝它们，但当时强制 ma 的版本仍拒绝 `toplevel_only`。320 个公开创建测试和旧诊断只对应当时补丁与材料，不能替代当前 B 版本 CPU 验收。记录中的惰性、empty 返回类型/未初始化值及额外 creation 测试覆盖边界继续有效，本轮没有扩大为新增规则。

## 7138：array-like 输出与旧关键字兼容

**无静态阻断项。** 保留原 `test_ravel_with_array_like` 的四类输入及全部值/类型检查；新增非零、负数嵌套数组的展开与 Dask Array 类型检查，直接防止只适配全零示例的退化。原模块其它节点不变，另加 `test_ravel_keyword_array`，参考由原 1 F2P + 468 P2P 变为 **1 F2P + 469 P2P**，原 468 条 P2P 顺序和内容不变，追加项唯一且存在于有效文件。

公开题面要求 array-like 能正确展开；导出 base 的公开签名明确为 `ravel(array)`。新增 `array=` P2P 因而保护旧合法调用，未限制必须使用 asanyarray、参数重命名方式或内部算法，也未增加零拷贝要求。`compatible_ravel.patch` 保留 `array` 并先转换，静态上可同时满足原/新增控制；其它保留旧调用的正确实现也可通过这些断言。原 gold 改名为 `array_like`，直接关键字绑定会失败，矩阵将它列为 incomplete_gold 的预期 0 与该事实一致，未将 gold 当唯一 oracle。

[旧题卡与实证范围](../../../../swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/card.md) 只证明原材料在 Python3.8.15/pytest7.4.4 的 noop/gold = 0/1、468 P2P 通过；不能继承为当前 469 P2P 或替代正对照通过。本轮 `compatible_ravel` 正对照、新增 keyword P2P 和 gold 的真实失败仍须 CPU 执行。题面原有转换修法提示应继续标注，当前没有新增公开提示或隐藏 oracle。

## 材料边界与后续范围

三题均声明题面不改，公开来源文件的 SHA 不变；当前测试、gold、候选、预期矩阵与作者分析明确为 host 私有输入，solver_boundary 只允许原公开题面、干净源码和中性环境说明。本次材料静态核查未发现将新私有断言、参考或候选混入公开资产；尚未审实际 actor 运输，不能把这句话扩大为运行时无泄漏证明。

三题 `formal_ingest_version` / `formal_material_digest` 和计划 `formal_revision_identity` 都尚未填写，当前矩阵观察分为 null。后续须由共用维护者生成受信正式版本并按各题已登记矩阵完成 CPU 与逐参考读回；7138 还需真实接入追加 P2P，不能只替换 test.patch。宿主或运行配方变更、实际题面交付及 actor 条件按已有接续要求处理；本审查不重做全生命周期，也不额外制造候选数量门槛。

当前审查绑定 SHA256：

| 题目 | revision.json | effective_test.patch | effective_test.py |
| --- | --- | --- | --- |
| 7656 | `0b70310018821b5cff83d81a89bcfdca820a198b85c94d246ed91e37500cfcd3` | `d3b711c9eb53cbdb6477314eae82f3ae5ca49e5c052a352c7da3959289c287db` | `45947718a1d33637e37a61781a80af280910bba53599f0e6de8952a5fd31403d` |
| 9378 | `2020dc58319e23c27b289cd68b6b7e147b6de736015876e2f16ea53ed8dbf9d5` | `9fc1a9d5ae885d9cc30388a875ab7ed629081de7ba7bdcc8571f3aca604a248a` | `c834df1a5aeb1596ff637ab7bcf79f9001d8b5d347023ca1a60f74d1ec3190e9` |
| 7138 | `fb29e9e0f0a6457d974256b95678b753f9c700e7051c5fb3d8c2dfec61b767cc` | `2f3c5c539816149a06b6c460b5d79d6b3223f452cd5862bcdbac41faf76bc44a` | `70c4e3bbadcdda5e78b624b7c51c49976485a1110f0952558c5c41b0f7231fae` |

当前 `acceptance_matrix.json` SHA256（预期均不是新观察分）：

- 7656：`5da46b2ddb0407b61492c546a323a12b6b55f6417b48fd91044ff83a3a856f8f`。
- 9378：`3274063f9713d20982c84ce0f69a72f3fac6dd589c2b7070c92e8589bb58e9d6`。
- 7138：`2e581e4a566d0b909796fa803f5722c166f5714798c041bcb9b2c1fdaf564586`。
