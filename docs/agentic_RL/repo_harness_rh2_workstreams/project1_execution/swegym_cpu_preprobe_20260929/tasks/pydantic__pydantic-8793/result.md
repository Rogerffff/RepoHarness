# Pydantic8793：CPU 结果（2026-09-29）

**已证实误奖：退化候选得1，却把真实默认值变成必填。** 按v1 §4第3步判S1/T2b；不是环境失败，也没有证实gold回归。当前可作问题定位；可列为**受限能力比较候选**，但须完成独立验收、实际解题入口/预算核验，并按下述预登记口径报告。**不进训练或留出评测。** 私有后检没有修好原正式评分。

| 候选 | 正式参考 | 实际行为 | 有效执行 |
| --- | --- | --- | --- |
| noop | 0；F2P 0/3，P2P 364/364 | 原例schema/字段必填/缺值三缺陷；真实默认值保留 | 安装0，测试1且完整，清理干净 |
| gold | 1；F2P 3/3，P2P 364/364 | 原例三语义修复；默认5/工厂7保留；旧开发测试72通过1跳过 | 安装0，测试0且完整，清理干净 |
| forced_required | **1**；F2P 3/3，P2P 364/364 | 原例修好，但`M().x`因默认5被清除而报missing；旧开发测试2失败70通过1跳过 | 安装0，测试0且完整，清理干净 |

三份正式日志都独立核过全部367个参考ID与状态、日志SHA、安装实际输出、完整段标记及manager收尾。正式raw pytest为noop 3失败377通过，gold/退化380通过；各另1skip/1xfail，不在冻结参考中。不能把总通过数当P2P分母。退化导出的frozen_patch仅修改`pydantic/fields.py`；解码源码与精确base加两行默认值清空改动逐字一致，原候选SHA及投影也对应，不是补丁没交付造成的假结论。

真实actor公开开发已验：UID54321、Python3.8.19/core2.16.2、checkout导入、源文件可写、四工具调用完整。actor消息是devcheck控制文本，不能据此宣称正式题面/public_hints交付已验。私有root三容器只证明行为，准备与清理均成功，不替actor权限证据。

本次grader由固定base加8个公开wheel恢复，实际ID与script digest记录在result.json；三方均使用2CPU/4GiB、deny_all、UID54322，安装后从/testbed加载，runner未变。内存峰值仅沿原resource字段报告，resource_facts为空，不能推CPU占用/全机余量。三次trusted_setup为282.232/216.979/189.364秒，实际测试仅9.088/5.838/5.799秒：这是准备效率成本，不是无效评分。没有使用preown优化层。

## 最小修订草案，尚未实施

只新增一项有公开语义依据的默认值行为断言，原必填F2P和P2P保持：

```python
from typing_extensions import Annotated
from pydantic import Field, create_model
M = create_model('Defaults', x=(Annotated[int, Field(description='x')], 5))
assert M().x == 5
assert not M.model_fields['x'].is_required()
```

依据是base的fields默认值文档、`test_annotated`两项default=5约束和`test_create_model_usage`；不要求内部helper或精确repr，也不裁决内层Field(3)+外层Ellipsis的歧义组合。当前私有对照已显示base/gold满足而退化失败，但**D6仅允许先探索SWE修订机制成本；本夜未获正式实施授权**，所以这里只给R-c草案，没有写入正式材料或参考。

授权并实现版本化入口后，需要在同一有效条件正式复验noop0/gold1/forced_required0，确认新增断言确实执行、原参考仍完整、错误候选因默认值违例而被拒，随后独立验收。既有有效证据按变化复用，不必为证明同一私有事实重跑旧实验。

## 受限比较口径与全部剩余项

若后续使用原题作受限比较，预登记：对本题所有原reward=1候选同样执行公开required/缺值脚本与真实默认值/工厂控制；涉及共享字段合并时核同一窄回归。原reward原样保留，语义审计另列pass/fail/unverified，审计失败不得称完整解，不把它包装成正式benchmark修好。共同题单、预算和有效分母必须明确。

本次结果已通过[root/独立复核](../../reviews/pydantic8793_result_review.md)，共用[D6成本设计](../../d6_revision_cost_note.md)已完成。仍待：D6实施授权；授权后的正式R-c三方CPU验收；实际题面/提示交付、GPU入口和预算；跨题关联与训练/留出划分、真实模型难度/成本；控制面准备效率按新版本另查。内外默认优先级保留观察边界，不新增硬规范。未处理S1前不训练，未解决公共条件前不称GPU-ready。

最小证据入口：本目录`result.json`（逐候选账本/日志/frozen源码SHA及资源）；`actor_original_v1_review.json`；`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8793/calibration_v1/`（三方正式与私有完整原件）；`runs/swegym_cpu_preprobe_20260929/analysis/pydantic8793_calibration_v1.json`（root冻结parser重放）。历史静态卡不回写。
