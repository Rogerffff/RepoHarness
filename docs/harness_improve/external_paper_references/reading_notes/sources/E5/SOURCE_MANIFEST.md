# E5 阅读来源与版本登记

读取日期：2026-09-07。此目录仅为任务11阅读证据，不是训练数据或运行依赖包；没有下载模型权重、完整任务数据或环境镜像，没有执行第三方代码。原文附件保持原貌，内含原作者链接/示例路径，不能当成本项目运行说明。

| 来源 | 固定版本 | 本目录附件 | 范围 |
| --- | --- | --- | --- |
| [SWE-smith论文](https://arxiv.org/abs/2504.21798v2) | arXiv v2，2025-05-21，46页 | [PDF](paper.pdf)、[全文提取](paper.txt)、[TeX压缩包](arxiv-v2.tar.gz)、[TeX入口](tex/main.tex)、`rendered/` | 正文/全部附录/图表/算法；关键图表回PDF。参考文献概要浏览，未展开所引论文 |
| [SWE-smith代码](https://github.com/SWE-bench/SWE-smith/tree/9b74ac08118a85c39c356802f7961893af73e07f) | `9b74ac08118a85c39c356802f7961893af73e07f` | [官方README](official-code/README.md)、`official-code/` | profiles、验证/评分、轨迹转换与合并、32B SFT配置/启动器、训练指南。只读机制，不做全库审计 |
| [任务卡](https://huggingface.co/datasets/SWE-bench/SWE-smith) | `ea6d7173829c7ec8fa16c22055699ff2e9188091` | [卡片](SWE-smith-card.md)、[API元数据](SWE-smith-metadata.json) | 只读metadata/card，未下parquet |
| [轨迹卡](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories) | `08e109b4a59eaeebf80e4675cd125d42e7ac99a4` | [卡片](SWE-smith-trajectories-card.md)、[API元数据](SWE-smith-trajectories-metadata.json) | split行数/公开叙述，不把不同序列化相加 |
| [32B模型卡](https://huggingface.co/SWE-bench/SWE-agent-LM-32B) | `6b6b924ea6f17aeff85e5228772df8fff3aab62d` | [卡片](SWE-agent-LM-32B-card.md)、[API元数据](SWE-agent-LM-32B-metadata.json) | 只读卡/元数据，未下权重 |
| [SkyRL当前main](https://github.com/NovaSky-AI/SkyRL/tree/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518) | `0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518` | `skyrl/`、`skyrl-tree.json` | 沿官方RL链接有限追踪；所读SWE示例默认R2E-Gym，不能归给SWE-smith |
| [SkyRL历史swe-smith分支](https://github.com/NovaSky-AI/SkyRL/commit/58cfc213c0f7b44a0b5033e68d65782d05f8a13d) | `58cfc213c0f7b44a0b5033e68d65782d05f8a13d`，2025-06-05，`support swesmith` | `skyrl-swe-smith/`、`skyrl-swe-smith-tree.json`、`skyrl-swe-smith-commit.json` | README、SWE示例、三个环境/评分接线文件；未据README成绩推成SWE-smith RL结果 |

作者主任务ID：`01a07827-1e3f-7bb0-85d6-7ac47489ae64`；会话turn_context核实`model=gpt-6-astra`、`effort=high`。独立审查ID、结果与逐项修订以[审查记录](../../reviews/11_E5_review.md)为准。

[固定初稿](E5_swe_smith.draft-20260907.txt)在提交独立审查前创建，保持原文字节，不因最终修订覆盖。它是文本存档，其中Markdown相对路径以正式笔记原位置为基准。[RL补充交审稿](rl-addendum-draft.md)记录审查期间新增来源；原初稿没有因此被修改。正式交付以[最终笔记](../../E5_swe_smith.md)为准。
