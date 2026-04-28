# Safety And Scope Review

## 总体评价

只读审查完成，未修改任何文件。整体结论是：当前 `README.md` 和 `docs` 对安全边界、项目阶段和能力范围的控制比较好，没有发现高风险的“已经完成生产级安全沙箱、完整强化学习训练、完整 SWE-Bench 复现、复杂多代理平台”的直接声称。

`README.md` 明确写明尚未包含 agent loop、tool runtime、sandbox executor、verifier 或 reinforcement learning integration，`05-workspace-sandbox-and-permissions.md` 也清楚区分了 permission 与 sandbox。

## 主要问题

1. `01-project-positioning-and-requirements.md` 中“证明了……能力”的表述偏强。在简历或面试语境中，容易被理解为这些强化学习、异步 rollout 或 post-training 能力已经由本项目充分验证。建议改成“提供了相关经验基础”或“覆盖了相关方向”。

2. `01-project-positioning-and-requirements.md` 的简历推荐表述虽然以“设计面向……”开头，但后半句“统一工具执行、Docker-based executable environments、轨迹记录……”仍可能被误读为已经实现。建议明确加入“设计并规划”或“在设计文档和 Python 骨架中规划”。

3. `05-workspace-sandbox-and-permissions.md` 写到 “Docker execution mode 用于正式评测”。这个说法不是错误，但“正式评测”可能被听成具备生产安全保证。建议写成“用于本地或离线批量评测”，并补一句“面向可复现执行，不面向对抗性代码隔离”。

4. `05-workspace-sandbox-and-permissions.md` 的 “task-level isolated workspace” 比较接近安全隔离话术。建议改成 “task-level separated workspace” 或 “task-level workspace boundary”，避免让人联想到强安全沙箱。

5. `02-system-architecture.md` 提到 “SWE-Bench Lite 子集” 时没有在同一句中说明这是未来或预留能力。虽然任务适配器文档已经澄清，但建议在架构文档中也写成“未来 SWE-Bench Lite 子集”。

## 建议修改

- 把所有简历相关表述统一加上“设计阶段”“规划”“原型接口”“未来实现目标”等限定词。
- 把 Docker 统一描述为“可执行仓库环境”或“本地、离线评测执行模式”，避免使用容易暗示安全承诺的 “isolated sandbox”。
- 在架构总览中补一句：本文中的 sandbox 指执行边界设计，不等同于加固的生产级安全沙箱。
- 对 “planner-coder-verifier” 这类表述补充“顺序式多角色 scaffold，不是独立后台多代理系统”，避免多代理能力被夸大。
- 对 SWE-Bench 统一使用“预留 SWE-Bench Lite subset adapter”或“未来可接入”，不要写成当前已支持完整 SWE-Bench。

## 必须保留的优点

- `README.md` 明确说明不是 Claude Code、Cursor、OpenHands 或生产编码助手的复刻。
- `README.md` 的 “RepoHarness is not” 清单非常重要，建议保留。
- `00-reading-guide.md` 清楚说明第一阶段只交付设计文档和 Python 骨架，并否认生产级安全沙箱。
- `05-workspace-sandbox-and-permissions.md` 对 permission 与 sandbox 的区分非常清晰，应作为核心边界声明保留。
- `07-verifier-reward-and-evaluation.md` 明确说明 reward prototype 不是新的强化学习算法，也不是论文贡献，这一点很关键。
- `09-agent-scaffolds-and-multi-agent.md` 明确排除复杂多代理平台能力，边界很好。
