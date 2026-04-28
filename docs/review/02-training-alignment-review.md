# Training Alignment Review

## 总体评价

本次审查只读取了 `docs` 和 `README.md`，没有修改任何文件。

RepoHarness 当前文档整体贴合“面向大语言模型智能体训练、后训练、软件工程智能体评测与轨迹采集框架”的简历叙事。主线非常清楚：`task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export`，并且 README 明确说明项目仍处于设计阶段，不包含可工作的 agent loop、工具运行时、沙箱执行器、verifier 或强化学习集成，这一点有效避免了过度声称。

文档最强的方向是“训练感知的软件工程智能体 Harness”，而不是“新的强化学习算法”或“已经训练出 coding agent”。这个定位是正确的，也和 CaRR DeepSearch、Coding GRPO 两个既有项目形成了较自然的三段式组合：CaRR DeepSearch 偏长轨迹搜索智能体与异步 rollout，Coding GRPO 偏 verifier-based coding post-training，RepoHarness 则补上真实或半真实仓库、多文件编辑、测试反馈、patch、轨迹采集和训练导出这一块。

## 主要问题

1. verifier reward 和 training export 的设计方向正确，但 schema 仍偏概念级。`07-verifier-reward-and-evaluation.md` 已经给出 verifier 输出字段，`08-trajectory-store-and-training-export.md` 也列出 SFT、reinforcement learning rollout、preference pair 三类导出。但是导出样例目前还是占位式，不足以说明训练样本到底如何从 transcript、events、verifier result 和 final patch 组装出来。

2. reward prototype 有价值，但需要补充边界条件和字段来源。当前 reward 公式明确说明不是新强化学习算法，这是优点。不过 `cost_penalty`、`patch_size_penalty`、`accepted` 的数值化方式、`fail_to_pass.total = 0` 时如何处理、flaky test 如何排除、pass-to-pass regression 如何强惩罚，目前还没有定义。对于 post-training 叙事来说，这会影响“verifier reward 是否可复现、可审计、可用于训练数据筛选”的可信度。

3. 与 CaRR DeepSearch 和 Coding GRPO 的互补关系只在定位文档中出现，还没有贯穿 README 和核心模块文档。后续做简历包装时，读者可能只看到 RepoHarness 本身，而看不到它如何承接 CaRR DeepSearch 的长轨迹诊断能力、Coding GRPO 的 shared verifier / verl / vLLM / SandboxFusion 经验。

4. 少数表述可能被误读为已经实现。整体没有发现严重过度声称。README 明确写了尚未实现关键 runtime，这是非常重要的安全阀。但部分模块文档里类似“第一版支持 YAML 或 JSON”“每次运行保存到”“批量评测至少输出”这类句式，虽然上下文是设计文档，仍可能被外部读者误读为实现已经完成。建议统一改成“未来实现计划支持”“未来实现应保存到”“批量评测设计应输出”。

5. 简历项目包装还缺少一个“可展示成果形态”的文档。当前文档讲清楚了架构，但还缺一个面向招聘者或面试官的展示页，例如：一个示例任务、一段示例轨迹、一个 verifier 输出、一个 metrics summary、一个 reinforcement learning rollout JSONL 样例、一个 preference pair 样例。即使是设计阶段，也可以明确标注为 illustrative example，用来展示项目最终会产出什么。

## 建议修改

1. 在 README 增加一个简短的 “Project Lineage / Complementarity” 小节，说明 RepoHarness 和 CaRR DeepSearch、Coding GRPO 的关系：不是重复训练项目，而是把长轨迹智能体训练经验与 verifier-based coding post-training 经验迁移到 repository-level software engineering harness。
2. 在 `07-verifier-reward-and-evaluation.md` 中补充 reward metadata schema，至少包括：原始 verifier 输出、归一化后的 reward components、cost 字段、patch size 字段、regression penalty、flaky/invalid 标记、最终 reward、计算版本号。
3. 在 `08-trajectory-store-and-training-export.md` 中把三类导出格式从占位样例扩展成最小可执行 schema，说明 SFT 样本的 prompt/completion 或 messages 如何构造，reinforcement learning rollout 中每一步 action-observation 如何表示，preference pair 的 chosen/rejected 来自同任务多次 rollout、gold patch 对比还是 verifier 分数排序。
4. 增加 run reproducibility 字段：`model_id`、`scaffold_id`、`task_version`、`repo_base_commit`、`docker_image`、`test_command`、`timeout_sec`、`seed`、`temperature`、`max_turns`、`tool_policy`。这会显著增强 evaluation metrics 和 training export 的可信度。
5. 增加一篇 `11-resume-narrative-and-demo-artifacts.md` 或类似文档，专门服务后续简历包装，包含：一句话项目定位、三段项目谱系、核心技术难点、不会过度声称的边界、未来实现后可展示的 artifacts。

## 必须保留的优点

- README 明确声明项目是 design-stage，并明确否认已经有 working agent loop、verifier、sandbox executor 或 reinforcement learning integration。
- 非目标写得克制：不是新强化学习算法，不是完整 SWE-Bench 复现，不是生产级安全沙箱，不声称训练出 frontier coding agent。
- shared verifier 作为训练奖励和离线评测共同来源，是非常强的 post-training 叙事核心。
- transcript 和 events 分离的设计很好，能同时服务对话重放、评测统计、失败诊断和训练导出。
- permission 与 sandbox 分离、Docker execution mode 的保守表述非常稳，适合面试中解释工程边界。
- scaffold 设计保留了 single-shot、simple ReAct、planner-coder-verifier 的可比较实验框架，能体现 agentic evaluation harness 的价值。
