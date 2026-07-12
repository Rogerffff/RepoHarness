# S2-1 T0 开工自检报告

日期：2026-07-12。执行：S2-1 线程（本机）。依据：`s2_1_data_ingestion_execution_plan.md` §4 T0。判定：**两项全 PASS，T1 可开工**。

## 检查 1：freeze_manifest_v0.json（v0.1）24 项 artifact digest 复验

方法：逐项对 `data_freeze/` 下 24 个文件重算 sha256 与 manifest 记录值比对（含四源元数据 jsonl、labels 全套、镜像清单、strip_spec、断言脚本与其冻结报告——完整清单见 manifest `artifact_digests` 键）。

```text
结果：24/24 OK，0 FAIL，0 MISSING
含关键消费面：meta/swe_gym_lite.jsonl、labels/static_gate_survivors.txt、
  strip_spec.yaml、meta/image_refs_swegym.txt 自 2026-07-08 冻结以来无任何改动。
```

## 检查 2：`meta/assert_repo_disjoint.py` 重跑

```text
train_pool ∩ verified   = []   PASS
heldout ∩ verified      = []   PASS
train_pool ∩ heldout    = []   PASS
heldout ⊆ 数据集        = []   PASS
跨源重复（swe_gym ∩ r2e）= ["pandas"]   —— 已知事实（DF-1 即发现），不违反
  互斥（两者都在训练侧）；(repo, base_commit) 去重断言在 T2 ingestion 实现。
verdict: PASS，退出码 0
脚本重写的 meta/repo_disjoint_report.json 与冻结版逐字节一致
（该报告本身在 24 项 digest 内，检查 1 的通过同时证明这一点）。
```

## 结论

数据面自 v0.1 冻结后零漂移，互斥不变量在当前文件上仍然成立。T1（完整 11 列 raw 重抓 + 键控镜像清单）的输入前提就位。
