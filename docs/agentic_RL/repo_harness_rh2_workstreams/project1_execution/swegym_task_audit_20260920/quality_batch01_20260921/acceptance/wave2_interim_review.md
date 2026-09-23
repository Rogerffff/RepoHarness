# 余八题中途抽验

总协调者 / 2026-09-21（SGT）。独立 reviewer 尚在进行，本页不替代最终逐题复核，也未运行历史项目或候选。

| 项目 | 根任务核对 | 当前处置 |
| --- | --- | --- |
| Pydantic8511 空子类继承 | 直接读 gold、base `create_dataclass` 及 `collect_dataclass_fields`：新 helper 确实用继承式 `getattr(cls, '__annotations__', [])` 取字段，并向当前类设置标准库 Field；required/default_factory 的 FieldInfo 也可能仍留在父类属性上。 | 路径值得指定 Python 3.8 的 CPU 对照；本轮未读该镜像标准库、未运行装饰器，保留回归假设，不写成已证 gold 错误。等待 reviewer 初判。 |
| DVC9395 dry 行为 | gold 新增顶层 `stage_cache.pull(None)` 与逐 stage 的 `repo.pull`，均没有检查 dry；base 的 `StageCache.restore` 对 pull/checkout 有 `not dry`，`repo.pull` 内实际 fetch/checkout。CLI 说明和既有 dry 测试支持继续调查。 | 用工作区与缓存快照判断实际副作用，区分输出恢复、缓存下载与命令执行；不把仅未带 dry 条件直接当作所有场景必然失败。无 remote 的另一假设保留，尚未验。 |
| DVC9395 历史 PARTIAL 归因 | 直接读旧候选补丁，以及 `test_output.txt:1290–1340`。失败在 `dvc.reproduce(...)` 内保存不存在的 `bar`，尚未到 checkout 次数断言；候选主要补了数据源分支，没有先恢复丢失的 run-cache 记录。 | 同意撤回“这个候选已证被次数误拒”。PARTIAL 结果不变；三次调用的实现耦合仍可单独静态记录，真正误拒需另做合理替代解对照。 |

原件：

- [Pydantic gold](../../../../../../../runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-8511/gold.patch)、[封存分析](../results/pydantic__pydantic-8511/analysis_before_history.md)。
- [DVC gold](../../../../../../../runs/swegym_quality_batch01_20260921_v2/private/iterative__dvc-9395/gold.patch)、[历史更正与原日志路径](../results/iterative__dvc-9395/old_findings_delta.md)。

本轮新疑点来自重新读题与源码；旧报告也确有需撤回的归因。这支持继续当前方法。CPU 仍只形成方案，不新增运行授权；协调者按固定题单继续完成独立复核。

## Pydantic 两题复核完成后的补证

两题 reviewer 已完成；根任务核到六份封存稿摘要不变、全包初判早于主审开放，见 [元数据复核](pydantic_metadata_check.json)。接受8511的有限候选及继承CPU优先级；reviewer明确该具体风险是第二阶段从主审获知，没有冒称独立发现。

5706的公开题面与全部新增断言已定点复读：支持JSON是合理方向，但题面也有拒绝叙述，gold不能代替需求决策。旧容器行为损坏与未纳入参考的风险仍成立；此前仅能转述的旧满分与source-only矩阵，根任务现已补齐原始日志，见 [历史补证](pydantic5706_historical_evidence.md)。该增量已交协调者，只需补证复核，不重做整题。它证明历史条件下的缺口；当前安装配方与真实RH2仍需后续有目标的对账，实际actor也尚未验。
