# 数据冻结包 v0.1 报告（P1 工作流收口，DF-8；v0.1 含评审修复轮）

日期：2026-07-08。执行：实验设计/检查线程（协议与规格）+ codex（DF-2/6）+ claude headless（DF-4 批量）；评审修复轮回应 codex + claude 检查意见（P0：真实 HF revision pin + digest 账本扩全 24 项；门控标签全查代替随机抽检，记录见 implementation-notes D11）。全部产物 digest 见 `freeze_manifest_v0.json`（version=v0.1）。

## 一句话结论

**DF-1~DF-7 全部完成，无推翻性发现**：R2E 镜像修复前状态确认（注意范围：3 仓库抽样 git 语义核验，不等于环境质量验证——golden/empty/determinism 门在 S2）；SWE-Gym Lite 静态门存活 216/230（2 个 fail 剔除已人工复核正确），bring-up 数据充足；三方互斥断言 PASS；两个高危工程坑在进训练流程前被排掉（SWE-Gym 镜像命名 `_s_` 规则、codex 后台 stdin 阻塞）。

## 关键数字

```text
静态门漏斗（Lite 230）：
  230 → 剔 held-out repo 12（D5 不变量）
      → 剔 test_adequacy fail 1
      → 剔 题面泄漏 fail 1
      → 存活 216（后续进 GPU pass-rate 预筛，最终 bring-up 用 100~200）

治理证据（供 E8 数据证据直接引用）：
  hints 剥离中和泄漏：109/230 = 47.4%（LLM 语义层）；正则层 ps 命中仅 0.9%
  → "剥离 issue 评论区"这一条 strip 决策消掉了绝大部分泄漏面
  打标质量：人工校准 15/15 = 100%，批量 230 题零解析错误

held-out 候选：542 题（tornado 261 / pyramid 189 / hydra 66 / bokeh 26）
  → 四道门后冻结 T=50~80（流程见 heldout_proposal.md）

磁盘规划（朴素压缩和，registry 去重后更低）：
  Lite ~0.5 TiB / SWE-Gym Full ~5.3 TiB / R2E ~2.3 TiB
  ⚠ 高于早前 0.5~2TB 粗估——success run 扩容前按 image_manifest.md 重新规划
```

## 已定不变量（S2 ingestion 消费，完整清单以 manifest invariants 为准）

1. 训练池 ∩ Verified = ∅（断言脚本可重跑）；一切训练 run 含 bring-up 排除 held-out repos。
2. 字段处置按 `strip_spec.yaml`，未列字段 fail-closed；hints_text 全量剥离。**S2 若重新抓取完整行/parquet，必须重跑该 fail-closed 检查**（本包 meta/*.jsonl 已是裁剪后字段集）。
3. 泄漏门只对模型可见面生效（D7）；仅 hints 来源的泄漏记录不剔题。**ps-warn 存活题带 leakage_watch 标记进池，leakage_evidence 随行保留供事后归因**。
4. R2E 物化断言：容器 HEAD == commit_hash 的 parent（DF-2 语义）。**R2E 行序按 repo 聚集，任何抽样必须跨 offset/分层，禁止取前 N 行**。
5. SWE-Gym 镜像名 `__`→`_s_`（D9 实测）；直接消费 `meta/image_refs_*.txt`，不要重新拼名。
6. 数据源 pin：四源真实 HF revision 已入 manifest（v0.1 起）；本地产物以 24 项 artifact digest 为账本，改动即可被 inspector 发现。

## 遗留（按归属）

- **GPU 步骤（S3/S4 前单卡作业）**：pass-rate 中段预筛 + pre-RL 行为诊断（同批 rollout）；环境验证门需 rh2 S2 库。
- **P5 勘误清单新增两条**：Lite 230（非 234）；镜像命名 `_s_`（非 `_1776_`）——待统一回写实验文档附录 B。
- **R2E 打标**：success run 需要 R2E ≥50%，其静态打标（约 300~800 题按需分批）排在 success run 题单确定时，复用本轮 prompt v1 与归因流程（R2E 无 hints 字段，只扫 problem_statement）。
