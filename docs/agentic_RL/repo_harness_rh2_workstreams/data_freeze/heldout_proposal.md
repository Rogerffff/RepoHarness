# DF-7 主判据 held-out 切分冻结提案 v0

依据：实验设计文档 E5 第四轮定案（主判据面 = 自建 frozen held-out，与训练同分布、同 harness、同推理栈）。

## 切分

按 repo 整体切出，四仓库共 **542 题候选**（`meta/heldout_candidates.jsonl`，DF-1 元数据实测）：

| 来源 | repo | 题数 |
| --- | --- | --- |
| R2E-Gym-Subset | tornado | 261 |
| R2E-Gym-Subset | pyramid | 189 |
| SWE-Gym | facebookresearch/hydra | 66 |
| SWE-Gym | bokeh/bokeh | 26 |

互斥性已断言（`meta/repo_disjoint_report.json`，PASS）：held-out ∩ Verified = ∅、训练池 ∩ held-out = ∅。

## 不变量（本提案新增，来自 implementation-notes D5）

**一切训练 run（含 bring-up）的数据都排除 held-out repos。** 实测 SWE-Gym Lite 230 含 hydra 11 题 + bokeh 1 题——bring-up 训练集须剔除这 12 题（剩 ~218 题再进预筛）。该规则写入 freeze manifest，S2 ingestion 断言执行。

## 从 542 候选到冻结 T≥50 的流程（顺序执行，每步记录剔除漏斗）

```text
1. 静态质量门（DF-4/5 同款）：三标签打标 + 正则泄漏扫描，任一 fail 剔除。
2. 环境验证门（S2，rh2 库就绪后）：golden patch 必过 / 空 patch 必败 /
   重复执行确定（每题 2 次）。
3. GPU pass-rate 中段筛（S3/S4 前的单卡作业，与 pre-RL 诊断同批 rollout）：
   目标模型 n=8 采样，保留 pass-rate ∈ [0.1, 0.8] 的题。
4. 分层冻结：按四仓库比例分层抽 T=50~80 题（方差允许时取上限），
   来源比例尽量贴近训练集的 R2E/SWE-Gym 配比；
   冻结记录 = 题 id + 镜像 digest + 题面 sha256 + 各门通过证据 ref，
   进 freeze_manifest（final），此后不可增删改。
5. 评测用采样参数与训练 rollout 同值（E5：n=8、T=1.0、top_p 同 E2）。
```

## 风险注记

- 步骤 3 后若存活 <50 题：优先降低方差要求用 T≥30（标注低功效版本，E5 已预留此口径），
  不得回头放宽步骤 1/2 的门（fail-closed）。
- tornado/pyramid 的 R2E 题面为程序化生成风格，与训练集同分布（这正是主判据面的设计意图）；
  与 Verified 风格的差异由外部参考面负责覆盖，两面不可互替。
