# 第三批：11题材料预备，未派发

2026-09-21 03:24 SGT。已导出并静态核验11题材料，尚未派发阅读、主审或 reviewer 角色。任务质量及 actor 实际环境未在本批验证；后续结果目录为本目录 `results/`。

实际目标为 DVC、mypy、Moto 各3题，Pandas 2题。原请求12个名额；与第二批相同的 `not_reviewed` 原池中，Pandas共5题，第二批已选48106、53958、56849，排除后仅剩50319、51605。根任务已接受11题规模；这是原池耗尽造成的调整，无待补的虚构第12题。

选题固定按 `SHA256('swegym-quality-batch03-20260921|' + instance_id)` 升序，每仓库取前3题或剩余全部。原池、第一/二批完整排除名单、逐项哈希排序和精确来源hash见 [batch_manifest.json](batch_manifest.json)，不按问题标签或导出结果换题。

| 仓库 | 选中题号（哈希顺序） |
| --- | --- |
| DVC | 6954、3665、4785 |
| mypy | 15139、15184、10174 |
| Moto | 6185、6408、5960 |
| Pandas | 50319、51605 |

材料位于 `runs/swegym_quality_batch03_20260921_v1/`；public/private/history 分离，public只含原公开bundle、当前函数渲染prompt、第二批沿用的中性环境说明及精确base导出。导出器复用第二批v2的Git blob方法，并增加磁盘字节、执行位、路径集合和固定抽样复核；未运行历史项目代码、测试、容器、SSH或模型，未下载子模块或依赖。

[material_check.json](material_check.json) 保留导出检查及另一次独立读回核验：33个源行、16,541个base blob、266,184,982字节、150个执行文件、11个prompt、22个noop/gold账本及日志引用均通过。Git跟踪项共16,544个，额外3项为Moto三题的 `tests/terraformtests/terraform-provider-aws` gitlink，内容未导出：6185/6408固定于 `a8163ccac8494c5beaa108369a0c8531f3800e18`，5960固定于 `f9a6db6e3c3f3299701747972fd6c37ba4af36f4`。无symlink或LFS指针；gitlink与运行环境缺口不能据此判题目无效。

冻结manifest SHA256：`424ad043fda8c3171109faa0d6acf9354da8011e6f5c625f24308fdcf19ea3b3`。材料目录在独立核验报告写入前共16,674个文件，其路径/字节/权限清单摘要为 `acbe726ca41e5e014e4d2877db31d3bc71fa187e70c5fa44ec8d74e8f6c6f916`；摘要规则和排除范围见run目录 `verification.json`。原run检查保持不变，本文档检查以hash引用它。
