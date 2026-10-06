# 给无历史上下文的协调任务

**复制本节作为新任务消息；现在尚未派发。**

> 你负责 SWE-Gym 首批 12 题质量复核。先读本目录 README.md、materials.md、actor_environment_card.md 和 batch_manifest.json；再读上级 quality_review_protocol_20260920.md。先检查用户提供的计划审查结论，落实必要修订；当前消息本身不是已经通过审查的证明。开工范围以用户实际授权为准。目标是独立调查题目是否描述充分、评分是否对应公开要求、是否有合理开发手段，随后核对旧报告；不是只给旧报告背书。
>
> 授权开工后，按 S0–S5 组织 sub-agent，允许 sub-agent 再安排独立 reviewer，但协调者统一登记角色，避免重复或自审。公开读者每题新上下文，使用 fork_turns=none，只转发 roles/public_reader.md 与该题公开目录；不要转发本消息、manifest、主计划、旧结论或整段会话。私有主审/独立 reviewer 同样用新上下文，按各自角色卡提供路径，不继承协调者的旧结论。无需指定模型或推理档位，沿执行任务配置即可。
>
> 先完成 Conan/Dask 四题的角色链，检查有无只读 diff、不追断言、把 grader 当 actor、把待验写成已验等方法问题，再执行固定的余八题。并行上限取工具实际容量。某题材料缺失时登记并继续独立题，不能换题掩盖缺失。
>
> 每题结果写本目录 results/<instance_id>/，只改自己的输出；基础材料当前为仓库根 runs/swegym_quality_batch01_20260921_v2/，以 manifest 路径为准。禁止改源题、生产代码、旧证据或其他 agent 输出，不提交推送，不租机、不访问旧远端、不运行付费模型。静态读源码及已有日志不需要机器。要执行项目代码、反例或容器验证时先形成 CPU 队列，按后续授权在隔离环境执行，不在本机宿主直接安装/运行历史项目。第一波即交接成熟单题的 CPU 清单，余八题继续，不等全批。
>
> 每题保存公开阅读、独立私有分析、旧结论变更、reviewer 初判和复核、短卡及 screening_record.json。收口只写一份简短 batch_report.md、probe_candidates.json 和 cpu_queue.json；未知保留，不能为了产出 3–5 题强行通过。不完整之处明确交接，不把静态候选标成运行已验 ready_for_probe。

## 协调者执行顺序

1. 只读核验当前 `material_check_v2.json` 与输入是否仍一致；若来源变化另立下一版本材料目录，历史 v1/v2 保留。所有路径相对仓库根，当前工作区为 `claude-code-verl-stage0h`。
2. 更新 `actor_environment_card.md` 的共享事实时另加日期/证据，不悄悄覆盖旧快照。只把中性公开摘录交公开读者；私有评分配方和故障线索不转发。
3. `assignments.json` 记录题、角色、实际 agent ID、输出目录、输入路径与时间。一个私有主审可拥有同仓 2–3 题，一个 reviewer 可复核多个小包，但不得复核自己主审的题。不要向公开角色提供整仓多题知识笔记。
4. S2 落盘后开始该题 S3；S3 先完成 `analysis_before_history.md`，再按 manifest 本题的 **`history_refs` 字段**取得 `history/<id>/refs.json`，最后读其中的旧报告，追加 `old_findings_delta.md`，保留前稿。没有名为 history_refs.json 的实际文件。无相关新发现也须完成基本映射。
5. S4 reviewer 先只获得原始 public/private 材料和 roles/reviewer.md，写 `reviewer_initial.md`；随后协调者用 followup 提供主审输出路径。主审可答复，但不替 reviewer 修改结论。
6. 证据强弱用文字说明：源码可达推断、历史局部实验、历史正式 RH2、当前 CPU 实验、模型轨迹各自标范围。reviewer 没有独立运行就写证据复读，不能改称独立复现。
7. 第一波校正角色卡或记录格式可继续；若需要改变题目含义/评分规则，提交具体修订建议留待决定，不以方法校正名义实施。已批准的环境修复可引用；新工作按实际授权。

## 汇总格式（保持短）

- `batch_report.md`：12 题实际完成数；已知校准/固定抽样分别发现什么；重要分歧/遗漏；候选与最重要的下一步。不给无依据的“全池坏题率”。
- `probe_candidates.json`：`instance_id, task_revision, reason, evidence_refs, actor_pending, grader_pending, intended_use`。筛查用的八方面结论本身不进入求解 prompt。
- `cpu_queue.json`：`instance_id, question, source_condition, command_draft, controls, expected_distinction, evidence_to_save, depends_on`。围绕真实疑点排优先级，不给每题强塞反例。
- 记录模板见 [record_template.md](record_template.md)。静态候选保留 `disposition.state=needs_review`、`scope=static_review`；在 reason 和候选清单中明确“静态候选，只待哪项 actor/CPU 证据”。不扩生产枚举。

## 后续 CPU 片的执行约束

由统一环境负责人为选中题固定实际入口和镜像版本，复用 `generate.py` 的物化/初始化和正式 rollout profile；现有 `verify_sandbox_profiles` 只验证通用边界，不是逐题开发条件验收。若需要薄诊断入口，单独编写并核对它与真实准备路径的差异，再运行；本轮没有假称这个入口已经实现。

同一身份、HOME、cwd、shell/环境注入下，先检查 Python/包导入的实际来源，再执行题面复现和窄公开测试、必要读写/构建。原 bug 的预期失败与环境失败分记。需验证评分误判时才构造有依据的替代解/错误解，用实际冻结、投影和 grader 对照；局部验证不可替代此结论。

保存实际镜像/HEAD/初态差异、有效配置、命令/退出码/日志、候选生效证据、资源与清理。若实际公开工作区与本批 base 导出不同，补交可见差异并复核受影响结论；不向公开角色交 gold 推导的提示。隐藏测试无需让 actor 执行。CPU 结果足够后再安排 GPU，不以所有 216 题完美为前置。
