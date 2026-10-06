# 016a 本轮材料非作者静态窄核

2026-10-03。身份：非材料作者；已接触私有测试、候选与旧审查记录，**不是 fresh 公开盲读者**。仅做本轮材料窄核，未执行项目代码或测试，未运行 SSH、容器或正式评分，未修改题主材料与生产代码。文本、JSON、SHA-256、AST 和内存文本重放均属静态检查，不能作为 CPU 通过证据。

结论：未发现本轮材料的具体误拒、漏检、调用错误或 source 合并错误。可接续既有 v2 材料审查；不代表正式验收。新公开读者、材料发布、真实 actor 身份和矩阵评分仍按 preparation/card 的既有计划完成。

公开原题明确允许跳过不能按 UTF-8 编码的文件名，或在内部处理编码错误。`statement_v1.txt` 只修正示例：先 `cov.start()`，再执行带不可编码 filename 的 `compile`；保留原 Expected Behavior，没有增加告警、指定数据层修法或新的公开 API 要求。本次不能代替干净上下文公开读者。

`materials/test_1_v2.py:566` 的原目标测试各语句按原顺序完整保留，文件中其他函数 AST 全部不变。新增分支模式依次执行另一不可编码 filename 与正常非 ASCII filename，检查正常模块和 `café_中.py` 的测量记录及独立 `CoverageData.read()` 读回；没有断言坏 filename 的最终表示，因此跳过与内部转义都可接受，也不强制告警。公开 `tests/coveragetest.py:117` 的 helper 确实在 coverage 生效期间 import；`coverage/sqldata.py:748` 新数据对象首次使用会 erase，第二段分支记录不会混入第一段 line 数据；`:739` 的 read 读取已经存在的保存文件。材料与既有 `cov016/hidden_test_1_revised_v2.py` 字节相同。

矩阵14行、13个现存补丁引用，全部 `not_run`。skip_write/rv_skip_write 跳过、convert/rv_convert 转义、rv_collector_warn 收集层处理列作正对照，和断言允许范围相符。lines_only、ascii_only、吞掉 flush/save、循环提前终止、仅 Latin-1、单名特判等已有反例保留；本轮未新增机械候选，也未声称它们已正式达到预期分数。

从静态 source 重放901和902，old 匹配唯一，before/after SHA 均一致，重建 test 与映射工件、重建题面与 statement 均逐字相同。manifest 明确保留001、不替换其他既有条目。私有 source expected 已是001修后版本，SHA 为 `f353157ec8e86a79e172920a44f6cbbdc8d1bb049c77f8292f7bd70dfc713e3e`，实际15键；001仍仅把 `MockingProtectionTest.test_os_path_exists` 从 FAILED 改为 PASSED。不得把001再次应用到该已修后 source，也不能发布时丢失001。901/902仍是临时草案编号。

## 核对版本

来源 base：`5bb5da50b182583036b7808bb32f2c8c191d9d26`。公有 bundle 与其声明哈希实算相同：`5a019798f87369a0ab579fd100ecf9f9cf2f62fdf332f6983f7c89cfb60df8fa`。共同父登记表 v11 SHA：`03acd34d7421bcf9c379612d0b8a5ce3d4292fdee0ee67327661eae5169d5c33`。

| 工件 | 实算 SHA-256 |
| --- | --- |
| `statement_v1.txt` | `e654fab906c8c9b5a994aed85c7e924c2389f10842dc319d0249060d3ee7d1e1` |
| `test_1_v2.py` | `ccdd7d89bb17177ab5922577be001e1f3000c0a2f53be8ec10eba2b3b849706b` |
| `revision_draft.json` | `bdbf6e0f54ab97130cc96a3c7d05f0c84c1bac9388be7e72a8279ab6b9996b96` |
| `cpu_matrix.json` | `89b7c7e1e0739ae8edecf08e532501d78543312317a3c3dc88b1d5750df22ff7` |
| `results_manifest.json` | `ed185be7d58fcca8ab503b836a8427ff08d0c9b07895d70d00bceb5a0f33c3e8` |

本记录只新增自身；材料、候选、历史证据与正式登记表未改。
