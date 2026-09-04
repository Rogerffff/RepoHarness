# rh2-integration 语义 patch 存档

本目录是 `reference/miles-rh2-integration` 上全部 `[rh2-integration]` 语义 commit 的
可复跑存档（`git format-patch` 产物），与 `../integration_base_manifest.json` 的
patch 表一一对应（sha256 钉死，`rh2/scripts/miles_integration_lanes.sh` 前置校验）。

## 当前版本：rh2-integration-v3（2026-08-31 V1 vendor refresh 重排;2026-09-02~04 续排至 0016）

顶层 `0001-0016`（manifest 十二张 patch 表共 15 个语义 patch 文件 + 0001 传输 patch）。其中 `0001-0007` 是 V1 vendor refresh 时从 v3 分支重新导出
（编号重排，非续排）；`0008/0009` 为其后的续排新增。构造顺序见 manifest 的
`rebuild` 字段：pin `f2b7c7929` → cherry-pick 上游四选材（`29c2c3aee` #2595 已合并版 /
`3ac3adce3` #2596 新 head / `cd464a1c4` sglang 0.5.18 矩阵 / `dbbab1566` fla 0.5.2）
→ 依序 `git am 0001..0016`。

| patch | v3 SHA | 内容 |
|---|---|---|
| 0001 | bf5d2981c | sampling-mask wire 字段传输放宽为 replay-only（R6-ext B3） |
| 0002 | 32b749e9e | 精确零全局梯度跳过 optimizer step（F2） |
| 0003 | 68226dc2c | weights_dirty 门控 weight publish（F2） |
| 0004 | 68f2ac1c0 | 结构化 G1 验收事件 + integration-tree identity 断言 |
| 0005 | 6c6bebd4f | 租前审查事件层证据缺口收口（P0-1~P0-8/P1-2） |
| 0006 | fb17a5616 | leaf 身份 wire 列 + per-rank step 事实 + engine identity |
| 0007 | 62b476838 | **V1 新增**：Dockerfile 钉死 SGLANG_COMMIT/MEGATRON_COMMIT |
| 0008 | 2f3786950 | **V2 新增**：per-token weight-version spans 入 Sample 记账 + rollout_group 事件列 |
| 0009 | 63c7a94e7 | **复核 P2 #1/#5**：spans 校验 assert→真异常并补齐 writer 合同全量结构不变式（null/空表 fail-closed、version 必须字符串等）；versions.md v0.5.16/空 commit 漂移修正 |

| 0010 | 69696cd85 | **W5a**：FullyAsyncRolloutFn/DataBuffer aclose、RolloutManager.dispose 接 rh2 关停链、train_async try/finally |
| 0011 | c3168e207 | **W5a 复核**：dispose 投回 owner loop + 有界期限（rh2_shutdown.py）|
| 0012 | 21261acf0 | **W5a 复核**：关停残留上提为 run 失败 verdict（ShutdownFailure、driver/worker 首因优先级）|
| 0013 | d66576aea | **W5a 复核**：serialize_driver_cause 严格同源判定、ruff 清理 |
| 0014 | 5c5c45331 | **W4**：consume-time staleness 唯一权威、三分支 drop 事件、no-progress、JIT drain |
| 0015 | c97d8c201 | **W10**：publish 后逐 engine actor 核对版本收敛 |
| 0016 | 98a0272e4 | **W5b**：最小冷恢复（已发布版本状态文件、updater 版本续接、状态缺失报错、run_restarted）|

0001-0006 与 v2 存档语义相同（重铺产物，diff 内容一致；0006 文件名因 git
format-patch 命名截断算法差异略有不同）。0007 为 V1 批新增，0008 为 V2 批
新增，0009 为 vendor refresh 复核（2026-08-31）批新增。

## v2/ 子目录：rh2-integration-v2 存档（回退面）

v2 分支保留不删。`v2/0001-0006` 是 v2 时代的原始导出（v2 本地 SHA
f6aab6542/620aa6924/51e3cd969/52040081a/2fff41c95/0853f027b），配合 manifest 的
`previous_base` 字段可完整重建 v2（cherry-pick 旧 PR head `9b6579a12`+`ee648b17d`
后依序 git am）。
