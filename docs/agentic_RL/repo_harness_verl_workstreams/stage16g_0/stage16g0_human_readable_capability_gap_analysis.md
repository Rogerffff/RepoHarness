# Stage 16G.0 人类可读能力差距分析

本文是 Stage 16G.0 与 Stage 16G.0 follow-up 的人工阅读版总结。它把多个机器可读 JSON 证据合并成一份面向人类决策的分析文档，目标是回答一个核心问题：

```text
当前 RepoHarness 是否已经适合作为 Claude Code 风格软件工程智能体强化学习的主训练环境？
如果不适合，主要差在哪里，应该先补哪些能力？
```

结论先说清楚：**当前 RepoHarness 不是没有工具，也不是简单“工具太窄像玩具”。它已经有较强的结构化读、搜、改、补丁清洁度、路径隔离、训练资格门禁和审计能力。真正的问题是：动态诊断、公开项目命令、受控复现脚本、多文件补丁能力和训练资格 linkage 还没有形成一个足够接近 Claude Code / mini-SWE-agent 实际解题闭环的主训练工具面。**

因此，Stage 16G.0 的结论不是“直接放开完整 shell”，也不是“马上进入 Stage 17 训练数据冻结”。正确方向是：**先定义并实现一个真实、可审计、可训练的 SWE public core profile，然后再进入代表性任务诊断和数据冻结。**

## 证据来源

本分析主要基于以下 Stage 16G.0 产物：

- `stage16g0_capability_gap_matrix.json`
- `stage16g0_capability_probe_report.json`
- `stage16g0_claude_code_tool_inventory.json`
- `stage16g0_claude_code_baseline_contract.json`
- `stage16g0_mini_swe_agent_baseline_contract.json`
- `stage16g0_per_capability_baseline_comparison.json`
- `stage16g0_stage16g_implementation_requirements.json`
- `stage16g0_stage17_readiness_gate_report.json`
- `stage16g0_acceptance_summary.json`
- `stage16g0_followup_acceptance_summary.json`

同时参考了：

- `docs/harness_improve/gpt_advice.md`
- `docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md`
- `reference/claude-code-typescript-src/AGENTS.md`
- 评测工作树保存的 mini-SWE-agent / DeepSeek 诊断运行摘要与配置摘录。

需要注意：mini-SWE-agent 的 follow-up 证据优先使用评测工作树中已有的真实运行配置和日志摘要，而不是完整官方源码深挖。因此它对外部行为层面，例如稳定 Bash 闭环、标准输出、标准错误、退出码、测试执行反馈，有中高置信度；对内部实现细节仍保留后续 primary source verification 空间。

## 总体数字

Stage 16G.0 follow-up 生成了：

```text
Claude Code baseline contract: 23 条能力契约
mini-SWE-agent baseline contract: 10 条能力契约
per-capability comparison: 27 条能力对照记录
blocking_for_main_swe_rl: 17 条
implementation requirements: 5 条
P0 requirement: 4 条
```

27 条能力对照的分类如下：

```text
present_and_sufficient: 7 条
partial: 11 条
missing: 3 条
present_but_weaker_than_claude_code: 2 条
present_but_weaker_than_mini_swe_agent: 1 条
present_diagnostic_only: 1 条
deferred_schema_only: 2 条
```

这个分布很重要。它说明 RepoHarness 当前不是“空工具面”，而是一个安全和审计很强、动态软件工程动作空间仍不足的 harness。

## 当前 RepoHarness 已经做得比较好的地方

### 1. 结构化读取、搜索和文件发现已经足够作为核心基础

RepoHarness 已有：

```text
read_file
grep
glob_files
list_files
read_tool_result_artifact
```

这些能力默认在 `simple_react` 中可见，并且比“只用 shell 的 cat / grep / find”更容易做路径可见性控制、输出截断、artifact 回读和训练导出绑定。

与 Claude Code 对比：

- Claude Code 有 Read / Grep / Glob 等分层工具。
- RepoHarness 的结构化读搜方向是对的。
- 当前不需要为了对齐 Claude Code 而让模型通过裸 shell 去读源码。

与 mini-SWE-agent 对比：

- mini-SWE-agent 主要依赖 Bash 查看文件和搜索。
- RepoHarness 在这一点上不是弱于 mini-SWE-agent，而是采用了更结构化、更可审计的实现方式。

因此，`structured_file_read`、`glob_file_discovery`、`grep_content_search` 被归类为 `present_and_sufficient`。

### 2. `create_file` 默认存在，不能再误判为完全缺失

Stage 16G.0 特别核实了一个容易误判的事实：

```text
默认训练 scaffold 是 simple_react。
simple_react 默认工具列表里包含 create_file。
patch_focused_react 不包含 create_file，但它不是当前默认训练 scaffold。
patch_focused_react_mini_shell 当前不存在。
```

这意味着“RepoHarness 完全不能新建文件”不是准确说法。更准确的说法是：

```text
RepoHarness 有 create_file，但写文件能力仍不完整。
它缺少 overwrite / write_file / delete / move / mkdir / apply_patch / multi-file edit 等更完整的结构化文件操作。
不同 scaffold 的工具可见性差异也必须在 profile 中明确记录。
```

### 3. patch capture、patch hygiene、Git diff 和训练导出已有坚实基础

经过 Stage 16E 和 Stage 16F，RepoHarness 已经把下面几件事情接到了较稳的链路上：

```text
final.patch
final.diff
final_patch_hygiene_report.json
official prediction builder
reward metadata
TrainingView / export projection
legacy entrypoint / run_episode entrypoint policy
```

这比 mini-SWE-agent 的“一个 shell 跑到底”更可审计。当前已经可以回答：

```text
最后训练目标使用的是 cleaned patch 还是 raw patch？
补丁里是否包含依赖目录、runtime-private 路径、gold/test patch 字段？
非 verl 路由是否被误算成 policy loss 候选？
旧 run_task 入口是否被误当成新训练入口？
```

这些是 RepoHarness 的优势，不应该在后续为了“更像 Bash agent”而破坏。

### 4. 安全边界和拒绝恢复信息已经不是从零开始

另一个容易误判的点是权限拒绝。当前 `execute_bash` 和相关工具的拒绝结果已经有：

```text
reason_code
recovery_hint
safe_argv
结构化错误类型
public-safe audit facts
```

所以 Stage 16G 后续不应该重新设计一套基础错误字段，而应该验证这些拒绝信号是否足够可学习：

```text
模型看到拒绝后，是否知道该换哪个安全工具？
拒绝是否会诱导模型减少验证、少用工具、静态猜 patch？
无效工具调用是被丢弃，还是作为负样本或局部反馈进入训练？
```

这部分差距不是“没有字段”，而是“字段如何进入训练信号和行为改进”。

## 当前最主要的差距

### 差距一：动态诊断能力弱于 mini-SWE-agent 的稳定 shell 闭环

mini-SWE-agent 的重要启发不是“我们也要给裸 Bash”，而是：

```text
一个软件工程 agent 至少要能稳定完成：
查看文件
搜索代码
写临时复现
运行公开测试
查看失败输出
修改源码
再次运行测试
查看 diff
提交最终答案
```

RepoHarness 当前能完成其中一部分，但主训练工具面仍有缺口。

当前状态：

```text
execute_bash 窄但不是空工具。
它允许安全 rg / grep、安全 Git 子集、pytest、受限 Python 诊断。
它拒绝动态 shell、脚本执行、包管理、网络下载、runtime-private 路径、Git history 等。
diagnostic_shell 存在，但属于 diagnostic profile，不是默认 formal training 工具。
```

问题是：

```text
当前还没有一个正式的 run_public_command 或 run_project_test 工具，
能够让模型表达“运行这个公开测试 selector”“运行这个项目允许的命令”“做这个受控 scratch Python 复现”。
```

这导致模型可能被训练成：

```text
少运行测试
少做复现
更多依赖静态阅读猜 patch
无法形成真实 SWE 闭环
```

这就是 `bash_or_public_command_execution` 被标为 `present_but_weaker_than_mini_swe_agent`，并且阻塞主 SWE 强化学习的原因。

### 差距二：公开测试命令和项目命令路由不足

当前 `run_tests` 是固定 public feedback path，不接受任意参数。它适合安全，但不足以覆盖真实项目诊断。

真实 SWE 任务经常需要：

```text
python -m pytest tests/test_x.py::test_case -q
python -m unittest package.tests.test_mod.TestClass.test_name
tox -e py311 -- tests/...
nox -s tests
django-admin test app.tests.TestCase.test_method
sphinx-build ...
项目自带脚本命令
```

当前 RepoHarness 的状态是：

```text
run_tests 无参数。
execute_bash 允许一部分安全 pytest。
final-only / hidden verifier 场景可能禁用 run_tests。
没有统一 project command router。
没有任务声明的 public command template / selector schema。
没有把 dependency setup、public command、private overlay 和 verifier facts 统一建模。
```

这会直接影响训练，因为真实模型需要学会根据失败定位到具体测试，而不是只能“跑默认测试”或“完全不能跑”。

因此 `parameterized_public_test_command`、`project_command_routing` 都是 Stage 16G.3 的 P0 阻断项。

### 差距三：scratch Python / 复现脚本还不是正式训练能力

真实软件工程智能体经常会写小脚本验证边界条件，例如：

```text
构造一个最小输入；
解析一个日志片段；
复现一个正则或路径问题；
调用项目函数做单步检查；
比较两种算法输出。
```

当前 RepoHarness 有两类相关能力：

```text
execute_bash 允许非常轻量的 Python literal 诊断；
diagnostic_shell 可以运行更真实的复现命令，但默认属于 diagnostic side channel。
```

这还不等于正式训练工具面里的 `scratch_python`。

正式 `scratch_python` 至少需要回答：

```text
临时脚本写在哪里？
临时脚本是否允许 import 项目代码？
是否允许读写 workspace 文件？
是否允许访问依赖环境？
输出如何截断和脱敏？
脚本是否进入 final.patch？
脚本产生的事实是否进入 TrainingView / reward / export？
失败时是否是模型错误、环境错误还是 harness 错误？
```

Stage 16G.0 follow-up 已经把这点改正：当前 evidence 不再声称已经真实跑通 diagnostic shell scratch，而是明确记录为 `static_policy_probe_only` 和 `not_run_in_stage16g0`。这很重要，因为不能用静态 allowlist 决策冒充真实 scratch 能力。

### 差距四：编辑能力还不接近 Claude Code 的多文件修改体验

Claude Code 类工具环境通常不仅有“替换一段文本”，还需要：

```text
新增文件
覆盖写文件
多文件编辑
应用统一 diff
删除文件
移动 / 重命名文件
创建目录
处理 rename / copy / mode change
失败时给出可恢复提示
```

RepoHarness 当前有：

```text
edit_file: 精确 old_text -> new_text 替换
create_file: 新建文件
git_diff: 查看 diff
patch hygiene: 捕获 cleaned final patch
```

但仍缺少：

```text
apply_patch 或等价多文件编辑工具
write / overwrite 语义
delete_file
move_file
mkdir
更接近 Claude Code MultiEdit / Write / Patch 的能力
```

这会影响复杂任务。只靠 exact replace，模型在多文件修改、移动文件、删除过时代码、添加目录结构时会比较笨拙，也更容易因为上下文轻微漂移而失败。

因此 Stage 16G.2 的 implementation requirement 被列为 P0：必须补齐结构化文件和补丁工具面，并且全部接入 Stage 16E 的 patch hygiene。

### 差距五：persistent diagnostic session 现在是 diagnostic-only，不是训练主路径

Stage 16B 已经实现了 diagnostic shell 和 Docker/local session 相关能力，方向是对的。但当前定位是：

```text
diagnostic_shell 是 diagnostic profile。
它不是默认 formal training surface。
它的结果能用于诊断和 side channel，但不能默认进入 policy loss。
```

这个设计安全，但训练上会有一个问题：

```text
最有价值的动态调试行为，如果全部被归为 diagnostic-only，
模型在 policy loss 主轨迹里就学不到这些行为。
```

后续不能简单把 diagnostic shell 全量放进主训练。更合理的是：

```text
swe_public_core:
  结构化 run_public_command / run_project_test / scratch_python

swe_public_extended:
  controlled diagnostic shell
  persistent session
  Docker-backed shell
  更强调生命周期、cleanup、dependency 和 artifact 审计
```

也就是说，persistent shell 应该是扩展能力，不应该成为唯一主路径。但它也不能永远只是“训练外诊断”，否则模型学不到真实调试闭环。

### 差距六：依赖环境和项目 setup 还没有成为正式能力

真实 SWE 任务经常需要：

```text
安装项目依赖；
生成本地构建文件；
运行项目 setup；
使用缓存；
区分共享只读环境和每题私有 overlay。
```

RepoHarness 现在在安全方向上做得很保守：

```text
共享依赖写入被严格保护；
package manager 命令在 execute_bash 中大多被拒绝；
diagnostic_shell 对 dependency mutation 也有拒绝和训练资格门禁。
```

这是必要的，但还不是完整能力。

后续需要设计：

```text
每题私有依赖 overlay；
共享环境只读证明；
任务声明 setup command；
依赖变更 facts；
构建缓存和清理策略；
哪些 setup 结果可以进入训练，哪些只能进入 diagnostic side channel。
```

如果不补这块，RepoHarness 在需要真实环境构建的任务上会弱于 OpenHands、SWE-Gym、DeepSWE 这类更强调 executable environment 的系统。

### 差距七：新工具必须接入 final patch、verifier、reward、TrainingView 和 export

Stage 16F 统一了 `run_episode` 测评入口，这是重要基础。但 Stage 16G 之后会新增工具能力，新增工具不能只做到“模型能调用”。

每一种新增工具都必须回答：

```text
工具动作是否会改变源码？
改变是否进入 final.patch？
是否经过 patch hygiene？
是否进入 official prediction？
是否进入 TrainingView？
是否影响 reward metadata？
是否进入 SFT / preference / policy loss 导出？
失败、拒绝、无效调用是否进入负样本或 diagnostic side channel？
```

如果新增 `apply_patch`、`scratch_python`、`run_project_test`、`diagnostic_shell` formal profile，却没有这些 linkage，就会产生“看起来模型做了事，但训练目标没有正确记录”的问题。

这就是 `final_answer_verifier_reward_linkage`、`training_eligibility_and_export_projection`、`hooks_tool_lifecycle_audit` 被放在 Stage 16G.4 的原因。

## 和 Claude Code 的差距画像

Claude Code 的核心启发不是“给模型一个 Bash 就完事”，而是分层工具系统：

```text
Read
Grep
Glob
Edit
Write
Bash
Todo / task management
权限、hooks、approval
长输出 artifact 和上下文管理
可能的 MCP / 插件 / 技能扩展
```

RepoHarness 已经覆盖或部分覆盖：

```text
Read: 基本覆盖
Grep: 基本覆盖
Glob: 基本覆盖
Edit: 部分覆盖
Write / create: 部分覆盖
Git diff / patch capture: 基本覆盖
Tool result artifact replay: 基本覆盖
权限拒绝结构化字段: 已有基础
runtime-private / hidden verifier 防护: 较强
```

RepoHarness 明显弱于 Claude Code 的地方是：

```text
多文件 patch / apply_patch / move / delete / mkdir
正式 public command / project test routing
scratch Python / 复现脚本
可训练的动态诊断 profile
TodoWrite 类长期任务状态
更完整的 Bash 生命周期和后台任务管理
更完整的语言服务 / LSP 诊断
插件、MCP、子代理等扩展能力
```

其中，LSP、MCP、子代理、非文本文件读取可以后置；它们不应该阻塞 Stage 16G 主线。真正阻塞主 SWE 强化学习的是：

```text
文件和 patch 操作不完整；
公开测试和项目命令表达能力不足；
scratch / dynamic diagnosis 不成正式训练能力；
新增工具的 reward / export / policy loss linkage 还没有固定。
```

## 和 mini-SWE-agent 的差距画像

mini-SWE-agent 的优势是简单直接：

```text
一个稳定 shell；
能看文件；
能搜索；
能写脚本；
能运行测试；
能看 stdout / stderr / exit code；
能迭代修改；
能形成完整诊断闭环。
```

它的缺点也明显：

```text
结构化工具少；
路径和 hidden artifact 防护依赖外层 sandbox；
训练导出、patch hygiene、reward linkage 不如 RepoHarness 精细；
安全审计粒度不如 RepoHarness。
```

所以 RepoHarness 不应该复制 mini-SWE-agent 的裸 shell 设计。但 RepoHarness 至少要达到 mini-SWE-agent 的动态解题下限：

```text
模型必须能稳定执行公开诊断命令；
必须能运行定向测试；
必须能写和运行受控复现脚本；
必须能看到足够完整的失败输出；
必须能根据反馈迭代 patch。
```

当前 RepoHarness 最大的问题正是在这里：安全和审计比 mini-SWE-agent 强，但动态诊断闭环弱于 mini-SWE-agent。

这就是为什么 `bash_or_public_command_execution` 被标为：

```text
present_but_weaker_than_mini_swe_agent
blocking_for_main_swe_rl = true
required_stage = 16G.3
```

## 当前不应该做什么

### 不应该直接进入 Stage 17B 或 Stage 20

Stage 16G.0 follow-up 明确给出：

```text
Stage 17A schema-only 可以继续。
Stage 17B real data freeze 不应放行。
Stage 20 warm-start data generation 不应放行。
Stage 21 formal RL 不应放行。
```

原因不是所有工具都缺，而是主训练工具面还没有定型。现在冻结数据或开始生成训练轨迹，会把模型训练到一个不稳定、不完整、和目标 Claude Code 风格环境不一致的工具面上。

### 不应该把完整 shell 作为简单解决方案

完整 shell 确实能快速提高解题能力，但也会带来：

```text
hidden verifier 泄漏风险
runtime-private 泄漏风险
Git history 作弊
依赖环境污染
测试篡改
路径脱敏失败
训练轨迹不可复现
reward hacking
```

Stage 16G 的方向不是“全放开 Bash”，而是：

```text
结构化工具优先；
public command 受控；
scratch Python 受控；
diagnostic shell 扩展化；
所有动作都有 audit、patch hygiene、reward linkage 和训练资格门禁。
```

### 不应该把 Stage 16G.5 当成第一次认真对比

这是本次 follow-up 的一个关键修正。

原来如果把 Claude Code / mini-SWE-agent 对照推迟到 Stage 16G.5，就会出现：

```text
16G.1 到 16G.4 改完；
16G.5 才发现和 Claude Code 仍有关键差距；
然后重新返工。
```

现在的正确分工是：

```text
Stage 16G.0:
  建立 baseline contract 和逐能力对照。

Stage 16G.1 - 16G.4:
  按 baseline contract 实现缺失能力和训练资格门禁。

Stage 16G.5:
  改完后做 Claude Code / mini-SWE-agent parity probe，验证实现效果。
```

也就是说，Stage 16G.5 是验收和补漏，不是第一次定义目标。

## 后续阶段建议

### Stage 16G.1：固定工具 profile 和训练资格门禁

目标是先定义清楚：

```text
safe_structured_only
swe_public_core
swe_public_extended
redteam_restricted
```

并明确每个 profile：

```text
有哪些工具；
哪些工具结果能进训练；
哪些只能进 diagnostic side channel；
哪些 provider route 可以成为 policy loss candidate；
哪些失败必须 invalid_for_training。
```

这是后续实现的地基。

### Stage 16G.2：补齐结构化文件和 patch 工具

优先补：

```text
apply_patch 或等价多文件编辑工具；
write / overwrite；
delete_file；
move_file；
mkdir；
更好的 edit recovery；
所有文件变更进入 final.patch、hygiene、export。
```

验收重点不是“工具能改文件”，而是：

```text
改动能被 final verifier 看到；
cleaned patch 只包含允许内容；
official prediction 和 training export 使用 cleaned patch；
非法路径或依赖目录被过滤。
```

### Stage 16G.3：补公开命令、项目测试和 scratch Python

这是最关键的一阶段。它要让模型具备接近真实 SWE 的动态诊断能力，但不回到裸 shell 风险。

建议工具形态：

```text
run_public_command
run_project_test
scratch_python
```

这些工具必须支持：

```text
任务声明的公开命令模板；
测试 selector；
项目命令参数；
受控 cwd；
输出截断和 artifact 回读；
拒绝时提供 safe alternative；
不能访问 hidden verifier / runtime-private / gold patch / test patch；
不能污染共享依赖环境。
```

### Stage 16G.4：收口 diagnostic shell、依赖环境、reward 和 export linkage

这一阶段应该处理更复杂的真实环境问题：

```text
persistent diagnostic shell 是否进入 extended profile；
Docker-backed session 如何进入训练资格；
共享依赖只读如何证明；
每题私有 overlay 如何记录；
final answer 中“我跑了测试”的说法如何和工具事件交叉校验；
无效工具调用、拒绝、失败是否进入负样本或辅助信号。
```

它的关键不是再加工具，而是把所有工具动作接回：

```text
verifier
reward
TrainingView
SFT export
preference export
policy loss gate
quarantine / diagnostic side channel
```

### Stage 16G.5：改造后的 parity probe

Stage 16G.5 应该做实证验证：

```text
同一批小任务，用 RepoHarness 新工具面能否完成 Claude Code / mini-SWE-agent 类闭环；
模型是否能定位、复现、修改、验证、查看 diff；
失败输出是否足够；
patch 是否进入 final.patch；
reward 是否合理；
无效工具调用是否被正确记录；
hidden / runtime-private 是否仍不泄漏。
```

Stage 16G.5 的作用是防止“实现看起来完整，但模型实际仍然解不了题”。

## 最终判断

当前 RepoHarness 的核心优势是：

```text
结构化工具；
路径和 hidden artifact 防护；
patch hygiene；
formal online RL gate；
run_episode 统一入口；
provider route 训练资格；
reward / export / projection 绑定；
公开 evidence 和 runtime-private 分层。
```

当前 RepoHarness 的核心短板是：

```text
动态诊断能力不足；
公开项目命令和定向测试不足；
scratch Python 复现能力不足；
复杂文件和多文件 patch 操作不足；
diagnostic shell 还没有转化为可训练的 public diagnostic profile；
依赖 setup / private overlay / project command routing 未成体系；
新增工具的 reward/export/policy-loss linkage 尚未固定。
```

和 Claude Code 相比，RepoHarness 更像一个安全、审计、训练导出很强的研究 harness，但还缺少真实产品级 SWE agent 的行动空间。

和 mini-SWE-agent 相比，RepoHarness 安全和可审计性强得多，但动态 Bash 诊断闭环还不如 mini-SWE-agent 稳定直接。

因此，后续不应该直接进入大规模数据冻结或强化学习训练。更稳的路线是：

```text
Stage 16G.1 固定 profile 和训练资格门禁；
Stage 16G.2 补结构化文件和 patch 能力；
Stage 16G.3 补 public command / project test / scratch Python；
Stage 16G.4 收口 diagnostic shell、依赖环境和训练 linkage；
Stage 16G.5 做 Claude Code / mini-SWE-agent parity probe；
之后再进入 Stage 17B、Stage 20 和正式强化学习。
```

这条路线能避免两个极端：

```text
过度保守：模型学不到真实软件工程调试能力；
过度放开：训练轨迹泄漏、污染环境、奖励被 hack、不可复现。
```

Stage 16G.0 + follow-up 的价值，就是把这个平衡点从“感觉判断”变成了可审计的 baseline contract 和逐能力实施要求。
