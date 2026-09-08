阅读综合和资产盘点都做完了，结论和建议已写成文件：

建议稿：00_B_reading_synthesis_and_first_round_plan.md
仓库资产盘点：repo_asset_inventory.md
16 篇技术报告类笔记的 B 线抽取：reading_extract_recipe_notes.md
在 env_data_eval.md 第 7 节加了一条指针，标明是建议稿，不构成批准。
最重要的发现
资产盘点不是读文档，是实际跑了 loader、swebench 查表和 parser 探针：

216 题的四面 bundle 和 pins 全部复核通过，但只覆盖 9 个仓库，hydra 和 bokeh 作为 held-out 已被剔除。文档里的"11 个仓库"说的是 Lite 全集。
当前评分链对 216 题必然失败。 swebench 4.1.0 的两张映射表和 vendored fork 都没有这 9 个仓库的 parser 条目，parse_log 对真实题直接 KeyError，manager 会把它判成 infra 故障并整组丢弃。216 题从未在任何容器里跑过一次评分，四门 runner 零代码，train/dev/test 无产物。
06 计划把 T2-d 和 T2-e 写成"由数据线继续"，但数据线自 7 月 20 日后没有任何新产物。
唯一的基座实测是 7 月用 Qwen3-4B 跑 8 题 Verified，run8 5/32 和 run9 1/32，没有轮数和失败位置的归因。本机没有模型权重、没有 Claude Code 的 linux tarball，x86 镜像只能 QEMU 模拟。
阅读综合与 Codex 收口稿的关系
我读了 Codex 的 00_reading_synthesis.md。它停在原则层，主张先定"首轮要证明什么能力、在什么条件下证明"再选题源，我同意。两份材料在核心判断上一致：环境有效、当前难度、学习价值三层分开测；固定 harness 版本；基座诊断先于配方终选；不叠加多种配方。我的稿子补的是 Codex 明确没做的部分：资产现状、单位成本、同量级基座的期望锚点、以及一份可执行的首轮清单。

几个对 B 最有用的外部锚点：SWE-bench Verified 里 o3 稳定失败的 138 题有 59.4% 存在题意或测试问题，Pro 约 30% 坏题，所以我们的 20 题要做题意与测试对照审查。N06 显示收紧 verifier 会把良性通过率压低约 10 个百分点，任何反作弊改动都要同时报 gold 和合法替代解的通过率。同为 30B-A3B 的基座在 OpenHands 300 轮下 Verified 只有 23.0，Claude Code 加 600 秒 25 轮的条件更紧，216 题的基座通过率大概率低于 20%，0/8 组可能过半。

建议的首轮
按依赖顺序，前两项不需要等任何决定：

parser 适配。 9 个仓库的 eval_cmd 全是 pytest 变体，接 swebench 现成的 pytest parser 约 30 行加单测，落在 envpack/scoring.py，属任务适配归 B，A 复核。
租一台 x86 CPU 机，起本地 registry，拉首批 20 题镜像约 45 GiB。
20 题题单：9 个仓库都有，8 种 eval_cmd 都有，含 mypy 的 -k 边界 3 题和 conan 的 eval_commands 边界 2 题，各含 P2P 为空与 leakage warn 的题。
四门加语义审计：empty 必败、golden 必过、各 3 次 fresh 容器确定性、无关 patch 探针，加 3 到 5 题的合法替代解探针。产出一张 20 题的账，这张账也是 A 线判断"超时和零解析改判 reward 0"是否安全的证据。
基座诊断准备：记录 schema 抄 GLM-5.2 的脚注格式，失败分类先用 Intern-S2 的类别只统计不惩罚，请求体原样保存供 A 线查 REALIGN 根因。需要 A 提供只起推理不起 learner 的入口，盘点显示现在没有这样的脚本。
划分：216 题内按仓库分层抽不超过 40 题作 dev 探针集，其余为候选训练池；最终坐标用 Verified 的 100 到 200 题分层子集。这一项是 T0。
需要你决定的
parser 适配由 B 做、A 复核，是否接受。
x86 CPU 机的租用形式和预算，20 题一天内 10 美元以内。
基座诊断的推理载体，单张 5090 量化还是双卡 bf16，以及要不要先用 API 模型跑一遍环境有效性。
20 题题单，我可以直接给候选。
划分方案。
是否补读 SWE-Gym 原论文和 SWE-rebench 经验谈，都很短，前者是我们数据源本身，其余未读来源我在建议稿第 5 节按价值排了序。
Remote Control is active · Continue here, on your phone, or at claude.ai/code