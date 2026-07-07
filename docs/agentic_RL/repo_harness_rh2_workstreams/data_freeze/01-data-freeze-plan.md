# 数据冻结包 v0 执行计划（P1 并行工作流，与 S1 执行线并行）

定位：实验设计线程（检查线程）主导的数据侧前置工作流。把 F3 排到"S1 末启动、S2 完成"的数据任务中**不依赖 rh2 代码**的部分现在做完，产出"数据冻结包 v0"，供 S2 的 ingestion 执行 agent 直接消费。

输入：实验设计文档 E4/E5 定案（bring-up / success run 拆分、R2E ≥50%、静态预筛、held-out repo 切分、污染核查清单）、附录 B/C（数据集核实、SPICE/UTBoost 出处）。

**执行边界（防撞车）**：本工作流不写 `rh2/` 代码、不改 01/02/03 执行文档；ingestion 代码与 envpack 格式转换归 S2 执行 agent。本目录（`data_freeze/`）是本工作流唯一写入区。

---

## 任务分解（DF 系列）


| #    | 任务                                           | 执行方                        | 依赖     |
| ---- | -------------------------------------------- | -------------------------- | ------ |
| DF-1 | 数据集元数据获取 + repo 交集断言产物                       | 本线程（curl HF API + 脚本）      | —      |
| DF-2 | R2E 镜像修复前状态核验（线程 6 遗留待核）                     | codex（需 docker）            | —      |
| DF-3 | 行内泄漏字段剥离规格（机器可读）                             | 本线程                        | DF-1   |
| DF-4 | SPICE 式静态打标：prompt 设计 + 20 题试点 + Lite 230 批量 | 本线程设计 / claude headless 批量 | DF-1   |
| DF-5 | problem statement 泄漏扫描（正则 + LLM 复核）          | 与 DF-4 合并跑                 | DF-1   |
| DF-6 | 镜像清单 + 磁盘核算 + 本地 registry 同步方案               | codex（清单/核算），拉取等机器就绪       | DF-1   |
| DF-7 | held-out repo 切分冻结提案                         | 本线程                        | DF-1   |
| DF-8 | 冻结包 v0 汇总（manifest 草案 + 报告）                  | 本线程                        | DF-1~7 |




### DF-1 元数据 + repo 交集断言

从 HF datasets-server API 拉取 SWE-Gym（含 Lite split）、R2E-Gym-Subset、SWE-bench_Verified 的行级元数据（instance_id/repo/base_commit + 各自字段清单），落地为 `data_freeze/meta/*.jsonl`。产出 `assert_repo_disjoint.py` 规格与运行记录：训练候选 repo ∩ Verified 12 repos = ∅、∩ held-out repos = ∅。**验收：断言脚本可重跑、输出进 evidence。**

### DF-2 R2E 修复前状态核验（治理硬前提）

线程 6 待核项：R2E 行内 `commit_hash` 指 fix commit 还是其 parent、`docker_image` 内 repo 是否处于**修复前**状态。方法：任取 2~3 个 R2E-Subset 实例，拉镜像，容器内 `git log -1` / 对照 `parsed_commit_content` 的 diff 是否**尚未**应用、F2P 测试是否在容器内当前状态下 fail。**验收：逐实例记录 + 明确结论（若发现镜像已含修复，立即上报——这会推翻 R2E 的可用性）。**

### DF-3 泄漏字段剥离规格

把 E4 污染核查清单第 2 条落成机器可读 spec（YAML）：每数据集一节，字段 → 处置（`model_visible` / `strip` / `grader_only`），SWE-Gym 的 patch/test_patch/FAIL_TO_PASS/PASS_TO_PASS/hints_text 与 R2E 的六个答案字段全部 `strip` 或 `grader_only`。供 S2 ingestion 直接加载执行。**验收：spec 覆盖两数据集全部字段，无未分类字段。**

### DF-4 SPICE 式静态打标

三标签：issue_clarity / test_adequacy / solution_leakage（各 pass|warn|fail + 一句理由）。流程：本线程写打标 prompt（含评分锚点样例）→ 20 题试点（本线程亲自标 5 题作对照，校准 prompt）→ claude headless（`claude -p`）批量跑 SWE-Gym Lite 230 题 → 门控相关标签全量复核（fail/ps-warn），随机抽检视校准结果减免。产出 `labels/swe_gym_lite_quality_v0.jsonl`。**验收：试点与人工对照一致率 ≥80%；批量产物含逐题理由；fail 题带触发证据。**

### DF-5 描述泄漏扫描

正则层（修复 PR/commit URL、40 位 hash、"Fixes #N"、diff 片段特征）+ LLM 复核层（并入 DF-4 的 solution_leakage 标签）。SWE-Bench+ 基准数字（32.67% / 4.3%）作为预期命中率参照：若我们的扫描命中率远低于此，怀疑扫描而不是数据。**验收：扫描器规格 + Lite 230 扫描结果。**

### DF-6 镜像清单与 registry 方案

按 DF-1 元数据生成候选题镜像引用清单（SWE-Gym `xingyaoww/sweb.eval.x86_64.*`、R2E 行内 `docker_image`），抽样 10 个核对 DockerHub manifest 可达性与体积，外推磁盘总量；写 registry:2 本地镜像同步的操作方案（含限流规避：分批 + 认证账号）。实际全量拉取等训练机就绪后执行。**验收：清单 + 体积核算 + 同步 runbook。**

### DF-7 held-out 切分冻结提案

按 E5 定案：R2E 留 tornado(261)+pyramid(189)、SWE-Gym 留 hydra(66)+bokeh(26) → 候选 ~540 题清单落地；定义其冻结流程 = 与训练集**同一套** DF-4/5 标签门 + （S2 后）环境验证门 + pass-rate 中段筛，最终冻结 T≥50。本阶段产出候选清单与流程定义，最终冻结在 GPU 预筛后。**验收：候选清单 + 流程文档。**

### DF-8 冻结包 v0 汇总

`data_freeze/freeze_manifest_v0.json`：数据源版本（HF dataset revision）、各 DF 产物 digest、标签统计、剔除漏斗（原始 → 静态筛后）、held-out 候选、待 GPU 步骤清单（pass-rate 预筛 + pre-RL 诊断，指向 8 卡前的单卡作业规格）。附 `data_freeze_report.md`。

---



## 产物目录约定

```text
docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/
  01-data-freeze-plan.md      本文
  implementation-notes.md     三节制，全程维护
  meta/                       DF-1 元数据与断言输出
  labels/                     DF-4/5 标签与扫描产物
  r2e_prefix_check.md         DF-2 报告
  strip_spec.yaml             DF-3
  image_manifest.md           DF-6
  heldout_proposal.md         DF-7
  freeze_manifest_v0.json     DF-8
  data_freeze_report.md       DF-8
```



## 与 S2 的交接面

S2 ingestion 执行 agent 消费：strip_spec.yaml（物化时剥离）、labels/*（静态筛结果直接过滤）、freeze_manifest_v0.json（数据源 pin）、image_manifest.md（registry 同步）。本工作流不做的：envpack 格式转换、环境验证门执行（需 rh2 库）、GPU pass-rate 预筛（单卡作业，规格在 DF-8 里定义、执行排 S2/S3）。