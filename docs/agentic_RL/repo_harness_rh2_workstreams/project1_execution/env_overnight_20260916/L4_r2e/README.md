# L4 · R2E 48 题材料与适配器一致性（2026-09-16 夜）

全静态分析：未起 Docker、未连远程机器、未调模型 API、未改 `rh2/src`。

| 产物 | 内容 |
| --- | --- |
| `r2e_tasks_48.json` | 合并去重后的 48 题清单（repo / commit / image / source revision / group / expected 计数 / run_tests.sh / 材料引用），含 `reconciliation` 核对结果。**机器包 M3 取用这份。** |
| `machine_checks.md` | 需要进容器才能得到的事实，13 项（M-01…M-13）带命令模板与判据；§0 先列"已经有答案、别再花机器时间"的 11 条。**机器包 M3 取用这份。** |
| `r2e_task_facts.json` | 逐题静态事实：expected 形态、noop/gold 账本、gold 排除清单、隐藏测试与 import、容器初态、初态脏树、风险旗标与分层、`unknown_checks`。 |
| `L4_r2e_adapter_card.md` | 来源适配器一致性卡（定义文档 §2 的九项 + 接入 rh2 的 9 个实现点与验收样例）。 |
| `L4_report.md` | 清单核对、风险分层、五个最值得注意的事实、方案 A 接入前必须先决定的 6 个问题、未检查项。 |
| `build_tasks_48.py` / `build_task_facts.py` | 生成上面两个 JSON 的脚本，可重跑（只读本地证据）。 |

早上先看 `L4_report.md` §4（待决问题）与 §5（未完成项）。
