# 外部 RL 基础设施源码阅读快照

日期：2026-10-04。用途：供云端阅读与设计比较；不是 RH2 的运行依赖。文件逐一与上游 Git blob 核对，保留源码、许可证和可执行位，不包含 `.git`。

| 仓库 | 固定提交 | 阅读目录 |
| --- | --- | --- |
| [XiaomiMiMo/mimoagent](https://github.com/XiaomiMiMo/mimoagent) | `467f0a19016f0ac4d63b8d17a1f0da9ba07f232c` | [XiaomiMiMo__mimoagent](XiaomiMiMo__mimoagent/) |
| [XiaomiMiMo/uni-agent](https://github.com/XiaomiMiMo/uni-agent) | `c63e0b01c375ebede95e01fe92bc367df24e5bf3` | [XiaomiMiMo__uni-agent](XiaomiMiMo__uni-agent/) |
| [XiaomiMiMo/verl](https://github.com/XiaomiMiMo/verl) | `e2b9fc03c6e01247f5d93c44201b068ea320b7de` | [XiaomiMiMo__verl](XiaomiMiMo__verl/) |
| [kvcache-ai/AgentENV](https://github.com/kvcache-ai/AgentENV) | `5843159b1eaf235a45a08a5329fc6647c6e5bc31` | [kvcache-ai__AgentENV](kvcache-ai__AgentENV/) |

MiMo 的 mimoagent 和 uni-agent 提交严格对应所选 verl 的配套 gitlink。原仓库里的子模块入口没有递归展开；三仓库为并列阅读目录，不能直接当作已经配置好的训练工程。uni-agent 自身的 verl gitlink 是另一版本，不要将它与用户指定的顶层 verl 混为一谈。缺省子模块及逐文件 SHA-256 见 [manifest.json](manifest.json)。

DeepSeek Harness 已在本机调查，但本次未复制其约 116 MiB 源码；可按固定版本 [5badb15009ae1756c3afe0ae0cef1faafc290ccc](https://github.com/deepseek-ai/deepseek-harness/tree/5badb15009ae1756c3afe0ae0cef1faafc290ccc)阅读。它是 agent 执行框架，不是完整 DSec 或 RL trainer。

完整阅读路线、项目现状和报告入口：[云端 Pro 阅读入口](../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_rl_infra_survey_20261004/cloud_reading.md)。
