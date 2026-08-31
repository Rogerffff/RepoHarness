# rh2-integration 语义 patch 存档

本目录是 `reference/miles-rh2-integration` 上全部 `[rh2-integration]` 语义 commit 的
可复跑存档（`git format-patch` 产物），与 `../integration_base_manifest.json` 的
patch 表一一对应（sha256 钉死，`rh2/scripts/miles_integration_lanes.sh` 前置校验）。

## 当前版本：rh2-integration-v3（2026-08-31 V1 vendor refresh 重排）

顶层 `0001-0007` 从 v3 分支重新导出（编号重排，非续排）。构造顺序见 manifest 的
`rebuild` 字段：pin `f2b7c7929` → cherry-pick 上游四选材（`29c2c3aee` #2595 已合并版 /
`3ac3adce3` #2596 新 head / `cd464a1c4` sglang 0.5.18 矩阵 / `dbbab1566` fla 0.5.2）
→ 依序 `git am 0001..0007`。

| patch | v3 SHA | 内容 |
|---|---|---|
| 0001 | bf5d2981c | sampling-mask wire 字段传输放宽为 replay-only（R6-ext B3） |
| 0002 | 32b749e9e | 精确零全局梯度跳过 optimizer step（F2） |
| 0003 | 68226dc2c | weights_dirty 门控 weight publish（F2） |
| 0004 | 68f2ac1c0 | 结构化 G1 验收事件 + integration-tree identity 断言 |
| 0005 | 6c6bebd4f | 租前审查事件层证据缺口收口（P0-1~P0-8/P1-2） |
| 0006 | fb17a5616 | leaf 身份 wire 列 + per-rank step 事实 + engine identity |
| 0007 | 62b476838 | **V1 新增**：Dockerfile 钉死 SGLANG_COMMIT/MEGATRON_COMMIT |

0001-0006 与 v2 存档语义相同（重铺产物，diff 内容一致；0006 文件名因 git
format-patch 命名截断算法差异略有不同）。0007 为 V1 批新增。

## v2/ 子目录：rh2-integration-v2 存档（回退面）

v2 分支保留不删。`v2/0001-0006` 是 v2 时代的原始导出（v2 本地 SHA
f6aab6542/620aa6924/51e3cd969/52040081a/2fff41c95/0853f027b），配合 manifest 的
`previous_base` 字段可完整重建 v2（cherry-pick 旧 PR head `9b6579a12`+`ee648b17d`
后依序 git am）。
