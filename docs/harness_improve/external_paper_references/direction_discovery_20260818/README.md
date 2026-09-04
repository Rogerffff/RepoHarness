# Agentic post-training 第一阶段方向发现包

状态：**首轮 Blind / Seeded Pro 已完成；Codex 独立核验与方向综合已完成；最终方向未定案**
首次检索日期：2026-08-18
Codex 整理日期：2026-08-19

这个目录只服务第一轮方向发现，不预先决定后续研究阶段，也不把多
harness、OPD 或环境生产当作已定结论。

## 文件

- `common_project_brief.md`：Blind 和 Seeded 两边共用的项目事实与资源边界。
- `pro_blind_discovery_prompt.md`：不提供任何既有资料或候选方向的发现任务。
- `pro_seeded_discovery_prompt.md`：提供中性资料地图，同时强制向 seed 之外搜索的发现任务。
- `seed_source_packet.md`：Seeded Pro 使用的论文、技术报告、开源项目和数据集导航。
- `responses/pro_blind_discovery_raw_20260818.md`：Blind Pro 完整原始回复。
- `responses/pro_seeded_discovery_raw_20260818.md`：Seeded Pro 完整原始回复。
- `analysis/codex_evidence_review_and_direction_synthesis_20260819.md`：Codex 对两份回复的
  一手来源抽查、仓库适配审查、方向归并和后续目标建议。
- `analysis/claude_direction_synthesis_and_firsttraining_20260902.md`：Claude 的独立核验
  （含对 codex 一处事实修正）、对 A/B/C 主干的四点修正建议（分层交付兜底 / OPD 升格 /
  tool-fault 槽位 / 8 卡可行性），以及首训阶段重定位（"完整性短跑"取代独立首训）的分析。
  2026-09-02 补记，讨论材料非定案。

## 首次运行记录

1. 两个 Pro 会话相互隔离，使用相同模型档位和相近研究预算。
2. Blind 会话只收到 `common_project_brief.md` 和 `pro_blind_discovery_prompt.md`。
3. Seeded 会话收到 `common_project_brief.md`、`pro_seeded_discovery_prompt.md` 和
   `seed_source_packet.md`。
4. 两边完成前没有互相查看输出，也没有在中途加入 owner 偏好的候选。
5. 两份完整原文已分别保存；Codex 综合意见单独保存，没有改写或混入原始回复。

## 原始回复完整性

`apply_patch` 保存 Markdown 时统一补上了 POSIX 文件末尾换行；除此之外，正文文本保持原样。
为同时记录输入和仓库副本，保留下列两组 SHA-256：

| 会话 | 输入文本 SHA-256 | 仓库副本 SHA-256 | 文件 |
|---|---|---|---|
| Blind | `5a975e917c191fd5e2ed1f862eb1ab451ca7c94d75f3bb60315c5e81225a8d33` | `b9562a4e75b9574e7c70e731daedeb0c9caa38883cbed09ef7f8552505c160a0` | `responses/pro_blind_discovery_raw_20260818.md` |
| Seeded | `77769d77e0e85097265c565b0a2faaf0315d64e9b9aabb53eb2f0f8511db1e55` | `65fb934084fc8eb2ee4756e734cc13c4a05c58c46d75f737a94b8da5e18fdfc0` | `responses/pro_seeded_discovery_raw_20260818.md` |

两份 Pro 来自相同模型并共享项目说明，检索时间窗口也相同。它们的结论重合属于交叉支持，
不等于不同团队对论文结果的独立复现。

首轮没有使用固定的 100 分评分表。Codex 后续核验重点是：是否真正找到 seed 之外的方向、
承重引用是否为一手资料、代码和训练成熟度是否被混淆、资源未知是否诚实标注，以及候选能否
组织成“系统贡献 + 可证伪模型命题”的完整后训练闭环，而不是一张新论文或流行组件清单。

本目录不包含给 Claude 或其他模型的固定提问模板。后续审查要求由 owner 单独决定。
