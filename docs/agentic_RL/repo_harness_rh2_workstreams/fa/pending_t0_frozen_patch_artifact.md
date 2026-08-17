# 待拍板 T0：冻结对象 = A-prime（FrozenPatchArtifact v1 + fresh clean grading）

状态：**pending owner 拍板**（2026-08-17，codex 设计反馈后重写；批准前
`fa_formal` 保持 fail-stop，F2-2b 状态 = review_failed_pending_redesign）。

## 拍板文本（批准即逐字生效）

1. FA formal 评分只消费不可变 FrozenPatchArtifact 经 hygiene 后得到的
   ScoringProjectionArtifact；grader 不得回读 rollout workspace。
2. delta 相对于 control plane 冻结的**精确初始 workspace tree**（
   baseline_tree_manifest + baseline_untracked_census，lstat/no-follow
   语义）；`base_commit` 只作 lineage，不单独充当评分基线。
3. 正式 exporter 不得执行或信任模型可控 repo 的 Git 配置、hooks、
   attributes、filters、external diff、textconv 或 index。具体提取机制
   （host-side archive / 非 root trusted helper / 临时复制后结构化比较）
   属 T1。
4. canonical artifact 是结构化、排序、可重算 digest 的文件 delta；v1 支持
   regular file / symlink × add / modify / delete 与 mode
   {100644,100755,120000}；FIFO/socket/device/大小写冲突/父子前缀冲突
   fail-closed；submodule：任务含 submodule 即不进首训（或 gitlink 变化
   永久拒绝），v1 不实现嵌套仓库 patch。
5. raw artifact 先过 schema/digest/精确 baseline/hygiene/security 检查，
   之后才产生 grading projection；private tests 只由 fresh grader owner
   在 projection 应用后注入一次（复用 SWEGradingManager 既有能力）。
   `.harness/**` 不静默剔除：runtime 私有文件独立落 audit ref；模型改
   runtime-owned path = tamper/security fact 交准入层。
6. workspace cleanup 必须晚于 typed drain、scope termination、artifact
   持久化与 durable attempt manifest handoff（复用 F2-4 pending/attempt
   manifest，不建 FrozenPatch 专用账本）；artifact digest 单独存在不足以
   授权删除；cleanup failure 记额外事实，不覆盖首因。
7. export/baseline/replay 基建失败不得伪装 reward=0（按 §9 失败语义表：
   exporter 失败=missing/None；baseline 不匹配=quarantine 或 run halt；
   artifact 不安全=present_*+permanent rejection 不跑 grader；apply 失败
   =contract failure/None；测试真失败才是 task negative；present_truncated
   的 group/reward/gradient 参与仍属 D1b 不预决）。
8. FA v1 不提供同 workspace formal grading（历史 S1 兼容路径冻结，比较用
   离线诊断），不建全局 CAS，不承诺 exporter/grader 自动恢复；retention =
   per-execution immutable artifact 目录，完整 artifact 至少保留到 run
   关闭 + 训练准入 + checkpoint 对账 + 预注册 regrade 窗口。
9. F2-3 typed drain receipt、formal non-root execution（SimpleLoopDriver
   降权或禁入 formal）、真实 Git/grader/Docker 组合测试未通过前，
   `fa_formal` 闸门保持关闭。

## 与被否掉的原方案 A 的差异

| 维度 | 原 A（已否） | A-prime |
|---|---|---|
| 评分基线 | `base_commit` 锚 | control plane 冻结的精确初始 tree（含 untracked census）；base_commit 仅 lineage |
| 提取机制 | 钉死"临时 GIT_INDEX_FILE + --no-ext-diff" | T0 只冻结"不执行/不信任模型可控 Git 元数据"不变量；机制归 T1 |
| artifact 形态 | unified diff 字节 | 结构化 delta（路径/操作/类型/mode/内容 digest 逐项校验） |
| `.harness/**` | 显式剔除 | 不静默剔除——私有文件独立审计，模型触碰 = tamper fact |
| hygiene 时序 | 未定义 | 必须在 fresh grader apply 之前（raw artifact 不得先进容器再清理） |
| cleanup | 未定义 | 晚于 durable attempt manifest handoff（复用 F2-4） |
| 失败语义 | 未定义 | 八行表逐场景钉死（见拍板文本 7） |

## 推荐

采纳 A-prime。理由：它把我原 A 的三个未定义面（真实初始环境、Git 信任
边界、持久交接）补成了不变量，且全部修正都有实锤证据（P3 评分日志
`.harness/` 混入、GIT_INDEX_FILE 仍读 repo config、SWE 镜像 overlay
commit 存在）。批准后我出 exporter/artifact/grader/cleanup 的小切片
顺序与回滚点，再开工。
