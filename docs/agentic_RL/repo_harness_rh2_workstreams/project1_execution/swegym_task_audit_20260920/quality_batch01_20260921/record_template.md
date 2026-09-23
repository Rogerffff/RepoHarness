# 逐题记录模板（引用原件，避免长报告）

同题输出固定在 `results/<instance_id>/`；不同角色只写自己的文件。以下是调查记录约定，不是生产 schema 或自动准入。

| 文件 / 写入者 | 必备内容 |
| --- | --- |
| `public_read.md` / 公开读者 | 公开需求、约束/疑义、合理路线、开发需求与建议命令、实际阅读/暴露范围。 |
| `analysis_before_history.md` / 主审 | 八方面覆盖、需求—断言双向表、相关调用者/回归、gold 检查、开发条件与证据、初步建议；在读历史前保存。 |
| `old_findings_delta.md` / 主审 | 旧主张对应确认/推翻/过时/未核实及决定性证据；主审改变自己初判的理由。 |
| `reviewer_initial.md`、`review.md` / 独立 reviewer | 读主审前的独立初判；随后逐项复核与新增发现、分歧。 |
| `card.md`、`screening_record.json` / 主审，协调者收口 | 一屏短卡和既有形状的结构化引用；reviewer 不改主审前稿。 |

`card.md` 建议 500–900 中文字左右，有实质复杂性时放证据附录，不硬限字数：

1. 题目目标/版本与建议用途。
2. 最重要的需求—测试映射（完整表留分析）：

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖/部分/缺失/冲突 | 执行证据或下一验证 |
| --- | --- | --- | --- | --- |

3. 八方面各自已查/未查范围；不能只填八个 pass。
4. 具体问题、影响与证据层次；环境修复是否已经被本次引用条件覆盖。
5. 静态建议、reviewer 分歧/结果、唯一优先下一步。多个独立问题仍分别保留，不为“唯一下一步”删记录。

`screening_record.json` 沿 [既有字段](../../environment_screening_definition_20260915.md#1-三类记录复用现有运行产物)：`task_id, task_revision, source_adapter_ref, recipe_ref, code_snapshot_ref, facts_ref, checks, issues, file_rules, revision_refs, disposition, usage, costs`。`checks` 仍用原 40 项编号，稀疏记录；状态只用 not_checked/pass/issue/unknown/not_applicable。八方面是阅读导航，不另建 8 项生产门。

- `facts_ref` 可指环境行/已有汇总和原账本，注明证据来源，不要求另造 facts 平台。运行引用写账本路径＋行号＋角色和条件；无法定位时保留证据缺项。
- 静态完成用 `disposition.scope=static_review`；运行条件未验时 state 保留 needs_review，reason 区分“静态候选待 actor 验证”和“题意/测试争议”。静态候选另列 `probe_candidates.json`，不冒用 ready_for_probe。
- `file_rules.additional_exclusions` 默认空；无证据不加路径规则。`revision_refs` 原版无修改时为空。
- `usage.intended_use=development_diagnostic`，记录审查者见过 gold、隐藏测试与旧答案的范围，不提供给模型 solver。并非正式训练/评测批准。
- `costs` 没有工具观测的 token/费用填 null；CPU 命令尚未执行，不造耗时。
- 把证据强度写在 issues 或引用说明中：静态推断、历史局部实验、历史真实 RH2、当前 CPU、真实模型。不要把“没有发现错误”等同证毕所有正确解/回归。
