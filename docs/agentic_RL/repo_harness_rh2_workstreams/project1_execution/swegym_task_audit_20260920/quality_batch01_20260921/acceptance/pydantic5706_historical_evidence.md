# Pydantic5706：补齐历史原件

总协调者 / 2026-09-21。第二阶段补证，不回写 reviewer 初判；只读归档，没有执行项目或测试。

此前 reviewer 将旧满分和 source-only 矩阵保留为“报告转述”，符合当时阅读范围。根任务已沿 `pydantic_pilot/verification.json#historical_runs.L3_5706` 找到并核读原件，应将这一部分升级为**已回读历史运行证据**；仍不能叫当前 RH2 复现。

| 历史证据 | 本次核对结果 | 限制 |
| --- | --- | --- |
| 09-09 独立 swegym_probe 的完整候选评分 | `cc_candidate_grading.jsonl` 第19、44行：F2P 2/2、P2P 273/273，RESOLVED_FULL；两份原日志SHA与账本一致，均277 passed/1 xfailed。 | 当时root、默认网络、patch fallback，候选含元数据/测试改动；不是source-only三方矩阵或当前RH2。 |
| 09-16 独立脚本的 base/gold/source-only 对照 | agent/54321与rh2grader/54322两种身份均记录：base/gold的旧Sequence测试各16 passed，candidate 6 failed/10 passed；gold/candidate的官方完整文件均277 passed/1 xfailed，base为2 failed/275 passed/1 xfailed。 | 断网、显式testbed解释器；脚本默认使用仅增加 `collections.abc.Sequence: list` 的生产补丁，并逐态复位/恢复出厂元数据。它不是正式actor流程，也没有使用09-19修订安装配方。 |

12份矩阵原日志、两份旧计分日志、脚本和source-only补丁路径/摘要已记录在 [原件索引](pydantic5706_historical_evidence.json)。矩阵的旧 `result.json` 未识别 rich 输出格式，counts 为空；不能将空字段误读为没执行，以上数字直接取原日志末尾。未把 EXPECTED.md 的预期表当作实测，尤其未据它扩大generator/string结论。

本次补证足以确认历史条件下的覆盖缺口，不必为了再次证明同一个历史事实重跑旧脚本。后续若做选定配方的真实 RH2 对账，其新增目标应明确为：相同生产单行候选经过当前投影/安装/评分后是否仍获分，同时range/tuple/deque旧行为如何；不是从零确认这条线索是否存在。

原题“应拒绝还是支持”的方向歧义仍在；旧候选得分不能替代需求决策。公开读稿和reviewer初判保持原字节，新证据只进入后续增量和汇总。
