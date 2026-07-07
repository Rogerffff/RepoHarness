# S2 阻塞项登记（S1-9 收口时建档，用户指示显式登记、不淡化）

本文件是三处登记之一（另两处：`s1_acceptance_summary.json` 的 `blockers` 字段、
`implementation-notes.md` 的 S1-9 条目）。每一项都必须在其点名的后续阶段被
显式关闭或显式改判，不允许静默消失。

---

## s2_blocker_offline_export_thinking_models

**S1-8 离线导出器对真实 CC（thinking 模型）轨迹当前全量不可用——E3 warm-start 回退预案的前置依赖。**

### 现象（S1-7a run8/run9 实测，非理论推演）

- `adapters/offline_export/exporter.py` 的 token 重建是**线性追加式**：
  分支 token 序列 = 末轮 prompt_ids + 末轮 output_ids，随后逐轮验证
  "每轮 prompt 是重建序列前缀 + 每个 mask=1 段逐位等于该轮 output_ids"。
  该算法隐含假设**分支首轮 == capture_record_refs[0] 对应的轮**。
- 真实 Claude Code 轨迹全部打破该假设：CC 按 Anthropic 协议在后续请求中
  **剥离历史 thinking 块**，Qwen3 thinking 输出的重渲染必然 token 漂移，
  TrajectoryManager REALIGN 把上一轮整轮降为 mask=0 上下文——实测 run8 的
  60 条交付分支 capture 回链**全部不含 t0**（首轮整轮掉落）。
- 后果：重建出的序列与实际叶链 tokens 错位，导出器 fail-closed 拒绝
  （reason_code = `token_reconstruction_mismatch`）。**这是设计按预期工作**
  （绝不静默导出错位 token），但意味着离线导出/warm-start 路线对 thinking
  模型产生的真实轨迹当前 0 可导出（run6 的单轮交付轨迹是唯一可导样本，
  `texp_16f847ff…`，见 `7a_artifacts/export_sample/`）。

### 影响面（为什么是 S2 阻塞级而不是"已知边界"）

1. **E3 warm-start 回退预案的前置依赖**：预案 = RL 行为崩坏时用离线过滤后的
   SFT 数据回锚；SFT 数据的出口正是 TrainingExportRecord。导出器修不好，
   预案对 thinking 模型（30B-A3B 主线即 thinking 模型）不可执行。
2. warm-start 离线过滤契约（`offline_filter_report_ref` 挂点）整条消费链
   同时被阻塞。
3. 评测/审计导出面（project_from_verifiers 之外的 slime token-faithful 导出）
   同样受限。

### 升级路径：分叉感知重建（技术要点，S2 实施）

核心转变：**放弃"从 capture 记录重建全序列再比对"，改为"以叶链自身 tokens 为
权威序列，用 capture 记录逐段锚定其中的可训练段"**——与 S1-7a 已实证的两个
同法组件对齐：

1. **锚定算法复用**：`adapters/slime/generate.py::_match_turns_to_runs`
   （token 同一性锚定回填）与 `s1_7a_bringup/verify_transport.py`（27/60/65 条
   逐位核对全过）已经解决同构问题——每个 mask=1 连续段必须被按序若干**入训轮**
   的 output_ids 逐位精确平铺；掉落轮（REALIGN 整轮降级）不参与、不回链。
   导出器重建器改成同一裁决：
   - 输入 = 叶链 tokens + loss_mask + branch.capture_record_refs（S1-7a 起
     只回链入训轮）+ 各 ref 的 output_ids artifact；
   - 校验 = mask=1 段逐位 == 按序入训轮 output_ids（digest 照旧逐 artifact
     重算）；mask=0 段不要求可重建（工具输出/掉落轮残留上下文本来就无 capture
     凭据），但必须逐段有 LossMaskSpan 理由码；
   - 产出 = ExportBranchTokens 直接取叶链 tokens（不再拼接重建）。
2. **树侧前缀血缘（备选/增强）**：hook TrajectoryManager 树快照导出 fork 点与
   REALIGN 覆盖区（S1-6 假设 2 已证实无现成 API，需自建提取器），lineage 记录
   补 `fork_point_token_index` 的真实值，使 compaction 分支
   （`lineage_reconstruction_not_supported` 当前同样拒绝）一并解锁。
3. **契约面升级（显式，不是配置开关）**：
   - `ExportTokenFidelity` 需新增枚举（如 `token_faithful_anchor_verified`）
     或升 `EXPORTER_VERSION`，让"线性重建"与"锚定重建"两种证据形态在记录上
     可区分；
   - 幂等语义保持：同输入 + 显式 exported_at_utc 逐字节相同；
   - audit 档双防线（schema 不可表示 + 导出器显式拒绝）原样保留。
4. **验收判据（S2 关闭本条的标准）**：对 run8/run9 的真实 CC 轨迹（60+65 条
   交付样本）导出成功，且导出 token 与训练侧 rollout dump 逐位一致（与
   verify_transport 交叉验证）；t0 掉落形态、REALIGN 平铺形态、fan-out 多叶
   形态各至少一条覆盖；线性假设的旧路径对错位输入仍 fail-closed。

### 状态

- 登记于：2026-07-07（UTC）/ S1-9 收口。
- 关闭责任：S2（若 S2 范围裁剪，必须显式改登记到 S3 并同步 E3 预案状态，
  不允许无声顺延）。
