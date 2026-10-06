# f5eb 本轮材料非作者静态窄核

2026-10-03。身份：非材料作者；已接触私有测试、候选与旧审查记录，**不是 fresh 公开盲读者**。仅做本轮材料窄核，未执行项目代码或测试，未运行 SSH、容器或正式评分，未修改题主材料与生产代码。文本、JSON、SHA-256、AST 和内存文本重放均属静态检查，不能作为 CPU 通过证据。

结论：未发现采用版 rb3h 的具体误拒、漏判、fixture/调用错误或 source 合并错误。已定A的每文件两字段可选且成对正确范围得到保留；新正式评分尚未运行，旧私有模拟结果不能改记为本版正式通过。

公开 ISSUE 要求 JSON totals 增加 covered_branches 与 missing_branches。base `coverage/jsonreport.py:33` 从 measured data 判断 has_arcs，`:43` 只累加实际报告文件，`:59` 输出 branch totals；`coverage/results.py:138` 的 branch_stats 返回每个分支行的 total/taken destinations。因此按目的地数而非分支行数累计、多文件合计、保存后无 branch config 报告、子集与零分支输出均有公开代码/契约依据。

`materials/test_1_rb3h.py:16` 保留完整旧 JSON 等式，只有已定A允许的每文件 covered/missing pair 可选：任一存在就核两者和值，再从比较对象移除这两键，其余字段继续精确比较。源文件原4测试和其他 helper无删除；除上述 helper及branch测试传参外原函数AST不变。`:215` 的6 destinations（f/g两路执行，h不执行）对应4covered/2missing且0partial；`:231` 真 save/load，新report对象不设branch config；`:239` 检两文件8/5/3及partial1，随后仅报告已测量子集核6/4/2；`:279` 仍要求branch模式下无分支时0/0/0，避免条件漏键。可选每文件字段在多文件及零分支段也核成对正确，不仅放宽原一文件样例。

测试与既有 reviewer 工件 `cov_f5eb/review/materials/test_1_rb3h.py`、expected 与 `expected_rc3.json` 分别逐字相同。矩阵16行15个现存补丁，全部 `not_run`；C1与rv_sym_xml作为每文件扩展的合理正路线，wr_alldata_proj由新增子集断言拒绝；C3、LF与NB分别针对保存后数据、多文件、零分支，expected_only_mismatch 仍是计划值，正式失败节点须运行确认。本轮不要求机械增加候选或重新全题盲审。

904从原始test_1重放，old唯一、before/after SHA及映射工件一致。905从原始4键 expected 重建到8键，原4键值保留，只增四个节点；manifest整体替换053/054，不应将新全文件再应用在旧053产物上，也不能叠加同目标修订。历史053已有的两个新增有效断言保留；保存、多文件、零分支、子集断言均在采用完整文件内。临时编号904/905不代表正式发布。

## 核对版本

来源 base：`17204597c33db2cc396d32b8f9931c35f2518675`。公有 bundle 与其声明哈希实算相同：`23f9a5e4c91270b2136bc4e3564cba68e73e4ef5db99e46c12330e583e407ce4`。共同父登记表 v11 SHA：`03acd34d7421bcf9c379612d0b8a5ce3d4292fdee0ee67327661eae5169d5c33`。

| 工件 | 实算 SHA-256 |
| --- | --- |
| `expected_v3.json` | `e150a338879b6703fba4950e2f3eeb284ea415140a6f68c1c80cf085aca6e0d9` |
| `test_1_rb3h.py` | `fd4d6ac9ca8e1edbe148e30cc73a1f48c9a3eecb4ffbaef5a388dbd430de2050` |
| `revision_draft.json` | `b97ffe13d1c4b35b03bb267d97393d3b360528f4faa1c327ecf7c1e550cfddf1` |
| `cpu_matrix.json` | `55977e1d3dee87cf2afa391902cfa5ee370bddcc131fa86716b837b9c89a119f` |
| `results_manifest.json` | `7364301f42222fb6894b9b370b54fffdebe7b5f2f3b36f023b1982546016e03d` |

本记录只新增自身；材料、候选、历史证据与正式登记表未改。
