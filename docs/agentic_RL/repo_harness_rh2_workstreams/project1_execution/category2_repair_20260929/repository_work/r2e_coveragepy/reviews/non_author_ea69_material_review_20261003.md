# ea69 本轮材料非作者静态窄核

2026-10-03。身份：非材料作者；已接触私有测试、候选与旧审查记录，**不是 fresh 公开盲读者**。仅做本轮材料窄核，未执行项目代码或测试，未运行 SSH、容器或正式评分，未修改题主材料与生产代码。文本、JSON、SHA-256、AST 和内存文本重放均属静态检查，不能作为 CPU 通过证据。

结论：未发现本轮新断言、open 替身修订或合并的具体错误。新增保留要求有当前已授权 inventory §6 的依据；不能伪称原 ISSUE 明文要求该覆盖策略。新矩阵8行仍全部未运行，safe_append 与 encoding 正对照尚未证明正式得1。

公开 ISSUE 要求生成报告真正被 Git 忽略；base `coverage/html.py:195` 先分析数据，没有数据则在`:210` 抛错，生成成功后才在`:218` 复制静态文件。既有无数据不建目录断言因此保留合理。原 ISSUE 没有明确已有 `.gitignore` 的覆盖策略，新增范围沿 `category2_repair_20260929/r2e/r2e_inventory.md:100` 的明确续接要求：保留已有内容且新报告实际被忽略。card 对两者来源的区分准确。

`materials/test_1_open_args_v1.py:104` 只为 `FileWriteTracker.open` 增加并转交 `*args, **kwargs`，原写文件记录和 HTML 测试行为未改，避免仅因 `encoding=` 把合理实现挡掉。不能据此宣称 actor 公开替身兼容问题已解决；公开测试没有由本批私有改动修改。

`materials/test_2_preserve_v1.py:38` 的旧 Git 测试以及`:95` 无数据测试与v11中036的文件函数 AST完全一致；逐字核对也只新增保留测试。`:65` 新测试先建立有效、非空用户规则，首次与再次报告都核 prior 字节片段仍在、index.html确已生成、真实 `git status --porcelain --untracked-files=all -- report_out` 成功且未出现生成报告。`:84–88` 明确排除 `report_out/.gitignore` 本身，与旧测试一致，允许用户维护/跟踪规则文件；其余报告文件出现任何未忽略行都会失败。这里不是读取一个空状态的替身，不要求新文件固定文案、固定写模式或特定参数。

两个新正候选在报告成功后的静态文件阶段追加规则，保留 prior 内容；其中一份带 `encoding="utf-8"`，替身允许参数转交。gold/CC覆盖内容、CA仅空目录写入、CB空文件、RE无数据先建目录分别是当前范围下有独立缺陷的负对照，标签没有把 encoding 写法本身误判为缺陷。结论来自代码与断言静态关系，分数/失败原因待真实正式矩阵。

906从原始test_1唯一重放到材料；907新增test_2，before为null且全文SHA与材料一致；908从原始46键 expected 合并到49键，原键值全保留，只加旧036/037两节点和新保留节点。manifest替换036/037，不能继续叠加旧同目标条目。所有 publication_files 映射与实际工件一致。旧两节点的运行只能按旧版本复用，不覆盖新节点或新正候选。

## 核对版本

来源 base：`7fd1ea39925f0856ff607bb30796bc948a8c829d`。公有 bundle 与其声明哈希实算相同：`d3ef6553fb3c5abf959c93c924da05414056978d7e6c03ecd2f7bf6fa32360f0`。共同父登记表 v11 SHA：`03acd34d7421bcf9c379612d0b8a5ce3d4292fdee0ee67327661eae5169d5c33`。

| 工件 | 实算 SHA-256 |
| --- | --- |
| `expected_v1.json` | `b3482977f4b14e436b61638b92950c68bea93f5cda15cf7854d4c87ff3627527` |
| `test_1_open_args_v1.py` | `30f34e643804fbe5c2575ce8469c1bf4dd5f912f1214ade93fbd9968759e9361` |
| `test_2_preserve_v1.py` | `e5fee9fb81700d682e45c5c25cdc18035000e1dd86bf78fb2c8391ee61105497` |
| `revision_draft.json` | `920785d94723bed790bf2c61e87d78985aa2bb5d6fbc169f28428a88b9cc0808` |
| `cpu_matrix.json` | `957b41ae44d5c6aeeb93387bcd31088d7cfe0a0e85dc067d35d73fe337931c5d` |
| `results_manifest.json` | `a54e230041deeb61d1c7ae2ec91e62cd904555a7bc0abaeacd57327dda60f49d` |

本记录只新增自身；材料、候选、历史证据与正式登记表未改。
