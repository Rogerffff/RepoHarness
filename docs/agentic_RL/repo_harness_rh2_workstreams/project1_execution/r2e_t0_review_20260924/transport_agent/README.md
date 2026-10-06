# R2E T0 材料修订：Production Tracer 窄复核

2026-09-24；独立于实施上下文。对象为共享 dirty tree（HEAD `6b023ebeb83718b22ab406777e33e77106372cda`），按 `review-standards.md` 复核本轮 E13 消费接缝。本报告不覆盖主审负责的对账工具版本选择和测试顺序问题。

**结论：本分工范围未发现新的生产消费缺陷。** T0-1 的新 expected 确实进入评分 parser 闭包，T0-2 的隐藏测试修订确实进入派生配方与 grader 的树摘要校验；修订字段没有进入求解 payload。当前 12 条归档评分与其 prepared 快照准确绑定，不能把这项结论推广成“旧账本可自动按当前版本重解释”。后一问题交主审的工具 P2，不在这里重复立项。

## 生产调用链与所有权

```text
受信 host 的准备步骤（同步）
  固定代码 pins v2 → 五项输入摘要核验
  原始行/镜像事实 + material_revisions_v1.json
    → ingest_r2e_subset（原文唯一替换；核前后摘要）
    → grading_bundle（新 expected 或隐藏测试摘要；material_revisions）
    → EnvironmentPackage.grading_bundle_digest
    → manifest v2 的四文件摘要 + 修订记录

实际消费（受信 host，同步）
  load_trusted_r2e_ingest_outputs
    → load_r2e_ingest_outputs → verify_r2e_package_relations
    → TrustedTaskController.from_repo_root 再验（含 revisions）
    → prepare_tasks
        public: prompts / rollout_task_views / prepared_manifest
        private: host_grading_views（权限 0600；父目录 0700）
    → load_context / PreparedTaskFace.load（权限、摘要、身份复核）
    → build_grading_spec_from_host_view → build_r2e_grading_spec
        parser 闭包捕获上述完整私有 bundle

派生构建 host（同步 subprocess；已有输出目录锁）
  load_trusted_r2e_ingest_outputs → build_one(revisions=trusted.revisions[iid])
    → recipe_v1 → material_v1.sh（只 datalad）
    → 写前摘要/写后摘要 → 私有树复核 → EnvironmentOverlayV1

ReplayGrader（一个 asyncio loop；此次无新增并发 owner）
  overlay 静态核验 → 镜像 ID 固定 → 候选容器/冻结 delta
    → SWEGradingManager
        root setup: 私有隐藏测试复制进 /testbed、重写入口、核树摘要
        candidate uid: 执行 bash run_tests.sh
        host: spec.parse_log → verdict → GradingReport → 账本
```

源码锚点：`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:289,313,335,577,656,787,879`；`training_view.py:318,342`；`prepared_tasks.py:224,439`；`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:304,401,458`；`r2e_grading_scripts.py:96,250`；`replay_grade.py:190,458,781`；`rh2/scripts/build_r2e_derived.py:395,605`；`rh2/scripts/r2e_derive/material_v1.sh:17`。入口/runner/parser 仍由既有机制消费，没有新增运行期材料覆盖分支。

## 跨接缝不变量与实证

| 不变量 | 结果及证据 |
| --- | --- |
| 新输入受代码锚约束，不能仅凭修订字段自称可信 | 当前 pins v2 自摘要 `60e187a0…` 通过；五项输入全部核对。重放真实 48 条后四面对象均与当前产物相等，重序列化 manifest 为 `706abc8a…`，与代码 pin 相同。 |
| T0-1 只改一个 expected 状态 | coveragepy 仅 `expected_output_json` 和其摘要变化；15 键不增删。当前 prepared 的 parser 重算两次 noop 都为 14/15、reward 0，两次 gold 都为 15/15、reward 1。 |
| T0-2 只改隐藏测试导入 | datalad 仅 `hidden_test_files` / 树摘要变化，expected 不变。修订全文摘要与受信修订单相同；派生事实的组合配方摘要重算为 `sha256:0ca00d15d6a993eecb9484f7670223fe678b8b6fbcd3d66c004ac4a01ab12f9f`；build.log 有 `RH2_MATERIAL_APPLIED=test_1.py`、`OK=1`，树为 `86561f1a…`，与 grading bundle 一致。 |
| 修订版必须一路传到 prepared 与 spec | 对当前全部 48 题，实际 `prepare_for_replay` → `load_context` 和 `PreparedTaskFace.load/grading_spec` 均通过；host bundle 往返相等。再以真实 ReplayGrader + SWEGradingManager、Docker 替身注入四份真实 noop/gold 日志，产出的 reward 与 match/total 均吻合；真正写给 manager 的 setup payload 含新树摘要。 |
| 求解面不带私有修订内容 | 48 个 `rollout_spec.public_bundle_payload` 以及实际 prompts/rollout JSONL 无 `material_revisions`、`r2e-mr-`，无完整 expected。public 与历史文件逐字节相同，gold/validation 文件也逐字节相同。 |
| 错误版本不能静默混用 | 两道 strict 关系检查在不给修订单时拒绝两题修订 bundle；旧 package digest 在 `PreparedTaskFace.grading_spec` 的真实分派入口被拒；旧 datalad 树摘要覆盖表在 `ReplayGrader.replay_one` 得到 `overlay:hidden_tests_tree_mismatch`，无 report、零 Docker 调用。 |
| 本轮未改材料的题不发生内容漂移 | 去掉新增 `material_revisions` 后，**46 题评分内容完整相等**。其中 numpy `43e333e2` 只在镜像环境配方变化，扣除它即本轮其余 **45 题**。只有 coveragepy 的 expected、datalad 的隐藏测试摘要发生语义变化。 |
| SWE 旧序列化与默认范围保持 | 当前真实 SWE 216 题四面及 manifest 重序列化摘要与既有封板产物完全相同；默认 controller 仍为 216 题 SWE，SWE bundle 不增加 `material_revisions`。 |

**摘要变化的精确口径：** 48 个 R2E `EnvironmentPackage` 的唯一变动字段均为 `grading_bundle_digest`；因而 48 个环境包总摘要都变化。两道材料修订外的 46 题，是新增空列表 `material_revisions: []` 参与规范序列化导致评分 bundle 摘要变化，不是材料内容变化。公开面和 gold 字节不变，不应把“内容不变”表述成“所有旧 R2E package digest 不变”。当前 loader 面向 pins v2；本轮未宣称旧 R2E prepared 工件可直接由新模型兼容消费。

## 本批真实证据绑定

归档入口 `runs/r2e_t0_revisions_20260924/replay/`：

- `prepared_r2e/prepared_manifest.json` 的摘要为 `d73c3b0c2d3a71558f6811816aeeb2e0dea9266db09caab90102f53a67ec7967`，与归档 `replay_summary.json` 相同。
- `private_r2e/host_grading_views.jsonl` 的摘要为 `d8e2a1a362eaff0cd106c3cc03863234dcf2dd02c08d7bd1d3b486e279b60008`；经真实权限与摘要 loader 成功读取，并与当前受信输入新生成的私有文件**逐字节相同**。两边 rollout/host 对象均 48/48 相等。
- `ledger_t0_noop.jsonl`、`ledger_t0_gold.jsonl`、`ledger_env43_noop.jsonl`、`ledger_env43_gold.jsonl` 合计 **12 行**；引用的实际 eval log 摘要全部核对。当前 bundle 构造的 spec 对全部日志重算的 reward、match/total 与报告相同，`scripts_digest` 与账本/sidecar 相同，overlay 镜像 ID 相同，`stage_error=None` 且 candidate cleanup 成功。
- coveragepy 与 datalad 各 noop/gold 两次，共 8 行；numpy 环境配方对照 4 行。每行实际日志摘要和重算计数保存在 [`transport_probe.json`](transport_probe.json) 的 `archived_reports_recomputed`。

边界：没有重新执行真实容器或访问远端；真实执行依据是归档 build/grade 原始日志及事实表。Docker 替身四例只证明当前真实 driver/manager 的编排和判分接缝，不能替代镜像内行为验证。构建 context 未在本机归档，本次以受信修订全文摘要、组合配方摘要和已归档 `RH2_MATERIAL_TREE`/root facts 互核，不声称逐字节核对了远端 context。

## 失败模型、范围与成本

- 本轮新增的是不可变输入及构建步骤，无新的 queue、线程或 event-loop ownership。crash/cancel/timeout/retry/sink failure/queue full 没有新增执行分支；本次不重审 manager 已有生命周期。材料步骤任一摘要失败会终止 docker build，trusted-prep 的既有工件事务/摘要边界继续生效。
- 本次故障注入覆盖本轮版本接缝：缺修订单、旧 package digest、旧隐藏测试树。前者属于受信材料错误，后两者属于混版工件，均不产模型 reward；未增加对正常 candidate 类型的拒绝。
- A/D/E/F/G/H/J/K/N 已由上述输入重放、消费分派和兼容检查覆盖；B 仅涉及已批准的两题材料语义，未变训练运输；C/I 不新增挡板，不解除正式 actor 接线前置；L 无新增每 token 热路径；M 的历史账本材料版本识别交主审工具项处理。
- 对 `material_revisions` 的机制判断：两类修订只用于摄入，派生配方只补实际被改的隐藏文件；没有为本轮引入新状态机、公共运行期覆盖平台或新的人工审批闸门。未要求把修订明文字段复制到 solver/训练 payload。
- 停止条件已经满足：本轮 source→ingest/pins→prepared→spec→grader/report 接缝有实证，兼容面明确，错误版本能在本轮实际消费入口被拒。正式 actor 派生镜像接线仍属既有后续任务，此处不扩大。

## 运行记录

1. [`transport_probe.py`](transport_probe.py)：从 `rh2/` 执行 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_review_20260924/transport_agent/transport_probe.py`。结果 [`transport_probe.log`](transport_probe.log)：通过，48 题真实 ingest/prepared、12 份归档报告、4 次真实 driver/manager + Docker 替身、4 条拒绝证据。
2. 定向维护测试：`test_ingest_r2e_subset.py` 的五条 revision 用例、SWE 重序列化、默认来源，加 `test_r2e_parsers.py::test_revised_expected_resolves_the_source_defect_logs`；**8 passed / 0 skipped / 0 xfailed**，3.00 s，日志 [`targeted_pytest.log`](targeted_pytest.log)。未跑全套 pytest/Docker/远端。
3. 仅新增本目录审查产物，未修改生产代码、受信输入、原始运行证据或提交。

标准复盘：本分工未新增 finding；主审正在处理的历史版本对账属于 H/M/N，现有维度可覆盖，无需新增审查机制。
