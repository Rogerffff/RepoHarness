# T0（已批准）：冻结对象 = A-prime（FrozenPatchArtifact v1 + fresh clean grading）

状态：**approved 2026-08-17**（用户授权"由 Claude 判断 codex 修订后定稿
实施"；本文为定稿文本，含 codex 二轮七项修订）。`fa_formal` 在第 9 条
前置满足前仍保持 fail-stop。

## 拍板文本（逐字生效）

1. FA formal 评分只消费不可变 FrozenPatchArtifact 经 hygiene 后得到的
   ScoringProjectionArtifact；grader 不得回读 rollout workspace。
2. 评分基线唯一权威 = **BaselineWorkspaceManifestV1**：trusted
   materialization 完成后、harness 获得写权限前生成；覆盖全部
   score-relevant tracked/untracked 文件；记录 path/type/mode/content
   或 symlink digest（lstat/no-follow）；绑定 image、environment、
   materialized head 与 base_commit lineage；fresh grader 应用
   projection 前必须重建并验证同一 manifest digest。base_commit 与
   untracked census 只是 lineage/派生报告，不是第二事实源。
3. 正式 exporter 不得执行或信任模型可控 repo 的 Git 配置、hooks、
   attributes、filters、external diff、textconv 或 index；T0 冻结的
   scope 不变量 = **所有模型 writer 都属于可撤销且可确认归零的
   execution scope**。提取机制与 non-root/SimpleLoopDriver 处置均属
   T1 手段。
4. canonical artifact 是结构化、排序、可重算 digest 的文件 delta；v1
   支持 regular/symlink × add/modify/delete 与 mode
   {100644,100755,120000}；FIFO/socket/device/大小写冲突/父子前缀冲突
   fail-closed。**submodule 定案**：ingestion 先统计受影响题数，v1 不
   接收含 submodule/gitlink 的任务；覆盖率损失显著再回 owner 决策；
   不实现嵌套仓库 patch。
5. artifact 身份：FrozenPatchArtifact 绑定 task/environment/image/
   baseline/logical execution/physical attempt，不同 physical attempt
   禁止覆盖；ScoringProjectionArtifact 是**引用** raw entries/blobs 的
   派生 manifest（不复制内容，不成为第二本事实账）。raw artifact 先过
   schema/digest/baseline/hygiene/security 检查再产 projection；
   private tests 只由 fresh grader owner 在 projection 应用后注入一次。
6. **runtime 私有文件（.harness/** 等）**：优先移出 scoreable tree；
   暂不能移出的单独记录并从 projection 排除。仅凭 .harness/** 变化
   **不得**推断模型篡改（harness 正常写 trajectory.jsonl，P3 实测）；
   tamper fact 必须有权限、命令或 ownership 证据。
7. cleanup 顺序（**不依赖完整 F2-4**）：revoke capability → typed
   drain → terminate execution scope 并确认 writer 归零 → 冻结、评分、
   Gate → 原子持久化 **per-attempt finalization receipt** → cleanup →
   追加 cleanup result（不改写之前事实）。F2-4 后续复用该 receipt 做
   恢复，不要求 F2-2b 先实现 cursor/replay/恢复状态机。
8. 失败语义表（逐字）：
   - 无法建立可信 artifact（exporter 读取/持久化/digest 失败）：
     missing + reward=None；有限幂等重试后 fail-stop/缺员。
   - artifact 已建立但 durable handoff 失败：completion 不变，run halt
     并保留 workspace。
   - exact baseline 不一致：reward=None，quarantine/run halt（完整性
     矛盾，不当任务失败）。
   - unsafe artifact（路径/类型/内容契约不安全）：present_* +
     permanent_rejection，不运行 grader，reward=None。
   - exact-baseline replay/apply 失败：contract/infra failure，
     reward=None，不得记模型 reward 0。
   - grader infra failure：不倒写 completion，reward=None。
   - deterministic test timeout / tests failed：真实模型负样本，通常
     reward 0。
   - cleanup failure：附加运维事实，不覆盖首因。
   - present_truncated 的 group/reward/gradient 参与仍留 D1b。
9. retention：完整 FrozenPatchArtifact 保留到 grading、admission 与
   finalization receipt 得到 durable ACK；不预设 regrade window（长期
   retention 后定）；per-execution immutable artifact 目录；不建全局
   CAS；FA v1 不提供同 workspace formal grading（S1 历史路径冻结，
   比较用离线诊断）。
10. F2-3 typed drain receipt、模型 writer 全部纳入可撤销 scope 的 T1
    手段（non-root 或等效）、真实 Git/grader/Docker 组合测试未通过前，
    fa_formal 闸门保持关闭。

## 与原 A 的差异（保留供审计）

原 A 的 base_commit 锚 / GIT_INDEX_FILE 命令级保证 / unified diff 单一
事实 / .harness 静默剔除 / 未定义 hygiene 时序与 cleanup 交接 / 未定义
失败语义——均被上文取代。codex 二轮再修七项：baseline 单一权威、
.harness 误杀修正、cleanup 脱钩 F2-4、失败表落地、artifact 身份绑定、
submodule 定案、non-root 降 T1 + regrade window 删除。
