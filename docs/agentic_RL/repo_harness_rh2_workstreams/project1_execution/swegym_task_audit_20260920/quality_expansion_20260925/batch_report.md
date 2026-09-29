# 09-25 扩大静态复核：产物导航

**冻结32题静态交付已全部获根任务验收：12项有条件开发候选、20项质量优先处理，全部ready_for_probe=false。** 新增20题为5候选/15质量优先，见[根最终验收](root_final_review.md)、[最终报告](reserve20_final_report.md)、[140份产物及来源清单](reserve20_final_inventory.json)。新增最终结构/封存与40份原稿来源校验均通过；后11题已验收，当前无待验收题。没有新项目执行或任务二派发。已提交快照保留，MONAI1121与Conan13610的压缩措辞以[最终勘误](final_acceptance_errata.md)为准。

首12题静态交付完成：**7项有条件开发候选、5项优先质量处理**。全部仍为needs_review/static_review，actual actor、探针及训练资格未验；无新项目运行。见[整批报告](first12_report.md)。首12题已获[根整批验收](root_first12_review.md)；根任务已明确授权继续冻结清单剩余20题，新增20题材料已完成导出及原件身份核对。

[84份逐题输出校验](first12_output_verification.json)、[24份修订来源校验](first12_revision_provenance_verification.json)、[材料冻结复查](first12_material_freeze_verification.json)均通过。20名审查角色另加2名材料角色，全部显式请求Astra/high/fork_turns=none，实际角色、封存及release见[台账](assignments.json)；不声称后端验真或OS隔离。

| 包 | 静态处置 | 报告与验收 |
| --- | --- | --- |
| MONAI：2446、3715、5686 | 1候选、2先处理质量 | [提交报告](pack01_report.md) · [根验收](root_pack01_review.md) |
| Conan：11594、13230、13721 | 3候选 | [提交报告](pack02_report.md) · [根验收](root_pack02_review.md) |
| Dask：6626、7656、9378 | 2候选、1先处理质量 | [提交报告](pack03_report.md) · [根验收](root_pack03_review.md) |
| Pydantic：5386、6283、8567 | 1候选、2先处理质量 | [提交报告](pack04_report.md) · [根验收](root_pack04_review.md) |

[候选清单](probe_candidates.json)全部ready_for_probe=false。[选择性后续](cpu_queue.json)当前区分12项actual actor证据需求、12项私有CPU诊断、7项验收设计提案和1项参考兼容审查，均未执行或派发。任务二由Claude B负责。

选样为216减五批已审task_ids并集40，余176；按公开类型及材料定位冻结32，首12不在该40内，但部分有L1历史记录。Modin5940/6937隔离；不估计全池缺陷率。manifest不变；整批验收及继续指令已收到，储备20按[八个小包](reserve20_packages.json)完成，新增9题时已交中期摘要。

材料依据：[准备目录](material_preparation_notes.md)、[结构化目录](preparation_catalog.json)、[环境边界](actor_environment_card.md)、[记录格式](record_template.md)、[引用修正](material_reference_correction.json)及[逐原件复核](coordinator_reference_correction_review.json)。历史grader与当前actor分开，未导出资产不代表镜像缺失。

本导航和assignments反映最新验收；逐题card/record及包报告保留各次提交时点，后续根验收不回写已提交hash。最终处置看card/record与review/协调裁定；封存初判和delta保留判断过程，不将被后稿纠正的旧句当最终结论。

新增20题当前阶段：pack05–12全部完成静态收口，累计32/32题完成，最终汇总与来源校验均已完成。新增脚本与检查记录单列reserve20；不改首12提交快照或root_dispatch，不重扫已验首12源码。

| 储备包 | 静态处置 | 报告 |
| --- | --- | --- |
| MONAI：1121、3566、4583 | 1候选、2先处理质量 | [pack05](pack05_report.md) |
| Conan：11560、12397、13403 | 3先处理质量 | [pack06](pack06_report.md) |
| Dask：6801、7138、7305 | 3先处理质量 | [pack07](pack07_report.md) |
| Pydantic：5662、6043、8316 | 1候选、2先处理质量 | [pack08](pack08_report.md) |
| MONAI：5932、6975 | 2候选 | [pack09](pack09_report.md) |
| Conan：13610、13788 | 2先处理质量 | [pack10](pack10_report.md) |
| Dask：7894、9212 | 2先处理质量 | [pack11](pack11_report.md) |
| Pydantic：8793、9066 | 1候选、1先处理质量 | [pack12](pack12_report.md) |

新增材料证据：[材料检查](reserve20_material_check.json) · [协调原件核对](reserve20_coordinator_material_review.json)。1121历史收集修订单列[补充身份记录](pack05_monai1121_material_override_review.json)，原冻结材料不改。

新增9题[中期报告](reserve20_midpoint9_report.md)与[63份产物快照](reserve20_midpoint9_inventory.json)已获根任务中期验收；快照记录当时余11题，当前静态审查余0题，后续不回写此中期快照。

中期反馈的三处措辞仅更新可变短卡并保留前版本：1121区分预定hints/actual消息；6801保留PyArrow/schema支持/object采样条件；7305明确quantiles调用已执行但未单独验收精确端点。原中期快照和封存稿未改。
