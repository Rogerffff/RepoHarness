# Stage 16D.0 cross-worktree verifier / harness 同步清单

生成时间：2026-05-23T15:48:16Z

## 1. 输入基线

| 字段 | 值 |
| --- | --- |
| source_worktree_label | evaluation_worktree |
| source_commit | 70547d7b3582876d2814cc065e5a501effcd83fd |
| target_worktree_label | training_worktree |
| target_commit_before_stage16d_0 | 4711573cf40ff50fabfebe6cdb79518a906b1625 |
| source_sync_doc_sha256 | 92c3ce78a55e710c0a3c1cd6e161cfd4354298e4f0c2e0ef57711de0664f68dc |
| source_score_gap_doc_sha256 | cac1c779c3620528d8972f7b8e145fdd38bf478165feffacb4488fb0a7d1d06e |
| source_diagnostic_session_doc_sha256 | e1a916cac1d7708045ad3da03699e2519fa83d4211d7d306e8d124ca5a0beaf4 |
| source_dirty_status | dirty |
| source_dirty_file_count | 1 |
| source_dirty_files_sha256 | 06ba22a7b570379f5058a19fbe0e49b7f4370e29006ecebeb4d27ad0c06be1d0 |
| source_dirty_participates_in_claims | false |

`source_dirty_status=dirty` 的唯一已知差异是 `reference/verl` 子模块指针变更。Stage 16D.0 的同步结论来自已提交的评测 worktree 提交和文档，不依赖该未提交子模块指针。

公开产物只使用 worktree label、提交哈希、文档摘要和相对引用，不记录本机绝对路径。

## 2. 总体判断

评测 worktree 的同步说明与已提交代码总体一致：它确实包含持久诊断会话、依赖变更拦截、公开测试提示、官方预测输入清洁和补丁清洁相关修复。训练 worktree 在 Stage 16A、Stage 16B、Stage 16B.5 和 Stage 16C 中已经用更严格的方式覆盖了一部分能力，因此不能机械 cherry-pick 评测 worktree 的旧实现。

Stage 16D.0 本轮实际同步了一项必要代码能力：

```text
scripts/pre_verl/build_swebench_official_inputs.py
tests/unit/test_pre_verl_swebench_official_inputs.py
```

它用于构建 SWE-bench official harness 输入，并在导出 predictions 时剥离测试文件改动和诊断临时产物。该能力在训练 worktree 之前不存在，不能仅凭 Stage 16E 的未来计划视为已经覆盖。

## 3. 已核验主题

| 主题 | 评测 worktree 证据 | 训练 worktree 状态 | 同步决定 |
| --- | --- | --- | --- |
| 持久诊断会话生命周期 | `a0cd2fa3` 及后续修复 | Stage 16B 已有 `diagnostic_shell`、投影工作区、清理事实、训练资格门闸 | already_equivalent |
| Docker 诊断会话隔离 | `a0cd2fa3`、`6c7757b9`、`f6ead6f5`、`aaec6639` | Stage 16B 和 Stage 16B.5 已覆盖容器标签、孤儿容器清理、运行目录不挂载、投影写回 | sync_recommended |
| 依赖环境只读和依赖变更拦截 | `13437b12`、`48a66da3` | Stage 16A 和 Stage 16B 已有失败关闭策略；诊断 shell 依赖变更会结构化拒绝 | already_equivalent |
| 超时、用户 site 和 Bash 语义 | `368ad041`、`6c7757b9` | Stage 16B 已覆盖 timeout invalidation 和 Bash 入口；用户 site 行为仍建议后续远端复验 | sync_recommended |
| 公开测试入口和公开环境提示 | `c0cc1b40`、`cfbbe4b5`、`dd3a6ec1` | Stage 16C 已提供通用公开环境上下文；仓库 profile 级公开测试提示仍未同步 | sync_recommended |
| 诊断 shell 防泄漏 guard | `d2fc8e7d`、`07f8c90f` | Stage 16A / Stage 16B 当前更严格，评测侧旧 guard 只作为测试样例参考 | conclusion_only |
| 官方预测输入清洁 | `9c9daf4a`、`71b1ae5b`、`32309442`、`5f3a88f0`、`2cffe78b` | 本轮新增 official input builder 和单元测试 | sync_required |
| 补丁清洁和拒绝产物过滤 | `7cb8c25e`、`8e3e916a`、`c8867f55` | 部分由官方输入 builder 覆盖；最终训练标签清洁度仍属于 Stage 16E | sync_recommended |
| repr60、repr50、repr40、repr30 文档结论 | 文档提交 `70843853`、`eb8a8676`、`e25f56ce`、`910b6695` | 只作为 Stage 16D seed 和诊断背景，不作为训练结论 | conclusion_only |

## 4. 逐项同步明细

| source_commit | topic | current_verl_worktree_status | sync_decision | sync_method | risk_if_skipped | risk_if_synced |
| --- | --- | --- | --- | --- | --- | --- |
| a0cd2fa3 | persistent diagnostic sessions | Stage 16B 已有独立 `diagnostic_shell`，不进入默认工具集合 | already_equivalent | no_action | 如果忽略该主题，真实软件工程诊断能力不足 | 直接覆盖会放松 Stage 16A / Stage 16B 已有边界 |
| 13437b12 | dependency environment read-only | 依赖变更命令在 Stage 16A 和 Stage 16B 均失败关闭 | already_equivalent | no_action | 共享依赖环境可能被污染 | 旧实现可能不如当前正式训练工具面严格 |
| 368ad041 | diagnostic timeout and user site | timeout 已结构化；用户 site 行为建议后续远端复验 | sync_recommended | new_stage_specific_implementation | 远端环境可能因为用户 site 路径产生不可复现行为 | 直接 cherry-pick 可能引入旧路径假设 |
| 48a66da3 | dependency mutation guard | Stage 16B `diagnostic_shell` 已拒绝依赖变更 | already_equivalent | no_action | 依赖安装可能被误当成可训练行为 | 无明显同步收益 |
| f6ead6f5 | dependency image preparation | Stage 16B.5 已验证 Docker 能力，但未完整实现评测侧依赖镜像准备 | sync_recommended | new_stage_specific_implementation | 真实任务可能缺少可复用依赖准备层 | 直接迁移会和当前 Docker profile 发生职责重叠 |
| 6c7757b9 | Bash diagnostic shell | Stage 16B Docker 和 local 后端使用 Bash 语义 | already_equivalent | no_action | `source`、`pipefail` 等语义不一致 | 无明显同步收益 |
| aaec6639 | isolate dependency preparation | 当前训练后端更倾向禁用未验证依赖写入；完整依赖准备隔离尚未实现 | sync_recommended | new_stage_specific_implementation | 依赖准备可能污染 agent workspace | 直接迁移会扩大 Stage 16B 范围 |
| c0cc1b40 | repo-specific public test hints | Stage 16C 只有通用公开入口，没有仓库 profile 推导 | sync_recommended | new_stage_specific_implementation | 模型不知道合理公开测试入口 | 直接迁移具体命令可能违反 Stage 16C 可见性规则 |
| cfbbe4b5 | score-gap public test hint derivation | 同上 | sync_recommended | new_stage_specific_implementation | 公开测试统计可能被误读 | 需要先适配 Stage 16C visibility gate |
| dd3a6ec1 | targeted public test guidance | 同上 | sync_recommended | new_stage_specific_implementation | 模型可能反复跑过宽测试或完全不跑目标测试 | 具体提示不能包含 hidden selector 或本机路径 |
| d2fc8e7d | diagnostic shell audit guards | Stage 16A / Stage 16B 已有更严格 guard | conclusion_only | document_only | 可作为补充测试样例来源 | 直接覆盖会降低当前策略严格度 |
| 9c9daf4a | strip diagnostic temp files from official predictions | 本轮新增 official input builder；覆盖 `.repo_harness_tmp` 和临时诊断文件 | sync_required | manual_port | official predictions 可能包含诊断临时产物 | 迁移后需要确认不写本机路径到提交产物 |
| 7cb8c25e | diagnostic shell patch cleanliness | 部分由 official input builder 覆盖；final patch 清洁度待 Stage 16E | sync_recommended | new_stage_specific_implementation | 训练标签可能混入诊断产物 | 过早过滤可能误删真实源码改动 |
| 8e3e916a | diagnostic shell test patch false positive | 当前 official builder 会默认剥离测试文件改动；更细 false positive 留待 Stage 16E | sync_recommended | new_stage_specific_implementation | 公开测试改动可能污染官方预测或训练标签 | 过宽过滤可能丢失合法源码改动 |
| c8867f55 | diagnostic backup files | official builder 已处理 `.orig`、`.rej`；其他备份模式留待 Stage 16E | sync_recommended | new_stage_specific_implementation | 备份文件可能进入 predictions | 过早扩大过滤范围需要更多测试 |
| 32309442 | diagnostic reject artifacts | 本轮 official builder 已覆盖 reject artifacts 的核心路径 | sync_required | manual_port | reject artifacts 可能进入 predictions | 需要确保过滤只作用于导出层 |
| 5f3a88f0 | quoted diagnostic leftovers | 本轮 official builder 已覆盖异常 quoted path | sync_required | manual_port | 异常路径可能破坏 official prediction patch | 过滤规则需避免误删正常文件 |
| 2cffe78b | tmp diagnostic leftovers | 本轮 official builder 已覆盖顶层 `tmp/` 诊断产物 | sync_required | manual_port | 临时文件可能进入 official predictions | 需要后续扩展到训练导出清洁度 |
| 71b1ae5b | broader diagnostic artifacts | 本轮 official builder 已覆盖顶层诊断脚本和二进制样式临时产物 | sync_required | manual_port | 诊断产物可能导致官方验证噪声 | 过滤范围需要单元测试保护 |
| 07f8c90f | diagnostic shell environment guidance | Stage 16C 已有通用公开环境说明；仓库 profile 还需新实现 | sync_recommended | new_stage_specific_implementation | 模型可能误用环境或依赖入口 | 直接复用可能泄漏旧评测环境习惯 |
| 70843853 | repr60 official audit | 只作为诊断背景和 seed 候选来源 | conclusion_only | document_only | 忽略会丢失样本选择依据 | 不能外推为 Verified 500 稳定结论 |
| eb8a8676 | repr50 official audit | 同上 | conclusion_only | document_only | 同上 | 同上 |
| e25f56ce | repr40 official audit | 同上 | conclusion_only | document_only | 同上 | 同上 |
| 910b6695 | repr30 dependency findings | 只作为依赖准备风险参考 | conclusion_only | document_only | 忽略会低估依赖准备风险 | 不能直接证明训练后端已支持依赖准备 |
| 118e518c | public test hint probe | 作为 Stage 16C profile adapter 输入 | conclusion_only | document_only | 忽略会削弱公开测试提示设计 | 不能直接写入模型提示 |
| a514409a | targeted public test guidance | 作为 Stage 16C profile adapter 输入 | conclusion_only | document_only | 忽略会削弱目标化测试提示设计 | 不能直接写入模型提示 |
| 531625ac | cross-worktree sync inventory | 本文件承接其结论并重新核验 | conclusion_only | document_only | 缺少同步追踪 | 无代码风险 |

## 5. 后续进入 Stage 16D 前仍需注意

1. `sync_recommended` 的公开测试提示类工作不应直接使用评测 worktree 中的具体命令文本覆盖 Stage 16C。它应实现为 repository profile / public test metadata adapter，并通过 Stage 16C 的可见性校验。
2. official input builder 现在只保证 SWE-bench official predictions 的导出清洁度。训练标签、偏好样本、强化学习 reward evidence 的补丁清洁度仍需要 Stage 16E 单独验收。
3. 本阶段 seed manifest 只产生诊断输入。任何 seed 在 Stage 16D healthcheck 通过前都不能进入训练。
