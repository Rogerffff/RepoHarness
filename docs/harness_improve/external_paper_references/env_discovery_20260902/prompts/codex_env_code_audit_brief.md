# codex 环境层代码级审计 Brief

先读 `common_env_brief.md` 与同目录 `../analysis/rh2_env_layer_status_20260902.md`（环境层现状盘点）。本轮请 codex 做**本地代码级核验与实现切片规划**，不改任何定案文档、不动 `reference/`。三件事：

## 任务 1：E-Wave1 ①② 实现切片规划

对象：`grade_controlled_patch` 受控评分入口（S2-1 T2-d）+ 环境验证四门 runner（T2-e）。

- 读 `rh2/src/repoharness2/grading/manager.py`（尤其 `grade()` 的 workspace 导出入口 `:769` 附近）、`rh2/src/repoharness2/envpack/{materialize,scoring,bundles_v2}.py`、`docs/agentic_RL/repo_harness_rh2_workstreams/s2/s2_1_data_ingestion_execution_plan.md`（T2-d/T2-e 规格）。
- 产出：`grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)` 与现有 workspace 入口的**共用面 vs 新增面**拆分（image check / clean checkout / apply / eval / parser 哪些直接复用）；四门 runner 消费 v2 三分 bundle 的 `GateInputs` 适配器（v1 `from_v1_pair` / v2 `from_v2_package`）需要哪些字段；`EnvValidationReport` 契约落到 `contracts/` 的注册点。给出实现批次的切片建议（哪些能先独立测、依赖顺序）。
- 特别核验单点瓶颈判断是否成立：是否所有下游（四门/mutation probe/golden 门/held-out 第 2 步/bring-up 题单）真的都堵在 `grade_controlled_patch` 上。

## 任务 2：BringupService 换表的接线面

对象：让 miles 链从"固定 8 题 Verified 探针表"改为消费 216 题 trusted ingest。

- 读 `rh2/src/repoharness2/adapters/slime/bringup.py:729`（`load_bundle_pairs()` 固定 8 题）、`generate.py:1749`（`RolloutTaskSpec`，当前携带 `public.digest()` 而非 `EnvironmentPackageV1.digest()`）、`envpack/ingest_swegym_lite.py:554`（`load_trusted_ingest_outputs`）、plan-06 的 W2a 条款、就绪稿 `miles_spike/formal_first_training_readiness_scope.md:303` 附近。
- 产出：`RolloutTaskSpec` 要新增/替换哪些字段才能携带 `EnvironmentPackageV1.digest()` 贯穿 baseline/grading/eligibility join；v2 只有 `eval_cmd` 而 grading manager 只认 v1 的 `eval_script` 全文——v2 评分正链缺口的最小补法；`test_bringup_vendor_only.py:81` 的 `assert len==8` 等钉死现状的测试改动面。这是 W2b 的前置，标注哪些属数据线、哪些属 infra 线。

## 任务 3：W3b anti-cheat 归属线的代码影响

对象：确认 git 净化从"环境生产期动作"改为"运行期沙箱正向能力核实"后，环境包侧还需要保留什么。

- 读 plan-06 W3b 条款、设计文档 2 §5.3（`docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`）、`environment_production_and_quality_pipeline_design.md` §6、`contracts/anti_hack.py`。
- 产出：`AntiCheatSpec` / `git_sanitizer_report` 如果不再是环境包冻结产物，`EnvironmentPackageV1` 的 `anti_cheat_spec_ref` 字段是删除还是改指向运行期证据；八步流水线第 6 步（Anti-cheat Preparation）里哪些是"镜像清理类生产期动作"（可能仍需环境侧做，如 future git object 净化必须在物化前），哪些纯属运行期能力核实（W3b 已接管）。给一个清晰的归属划分建议。

## 任务 4（可选，原独立调查被取消后并入）：Harbor⇄miles 集成两形态审计

背景：terminal 第二域倾向 Harbor 载体，两种接入形态——T-a（miles 官方 Harbor agent server：agent loop 在 Harbor 侧，黑盒式，绕过我们 capture 链）vs T-b（我们的 CC harness 跑 terminal 任务，只复用 Harbor 任务格式 + verifier 边界〔rollout 后注入 tests/、跑 test.sh、读 /logs/verifier/reward.txt〕）。暂定判断"T-b 主线 + T-a 对照"见 `../analysis/claude_env_layer_analysis_20260902.md` 第三节。

- 读 `reference/miles/examples/swe-agent-harbor-docker/`（README + swe_agent_function.py + generate.py）确认 T-a 回传的数据结构（有无 token ids / logprobs / tape？）能否满足 fa_formal 的 token provenance 要求；T-a 下四层身份铸造是否可行。
- 如需上游代码，clone `harbor-framework/harbor` 的 `harbor-miles-v0.20.0` 分支到临时目录（不动 reference/），读 `miles_agent_server.py`。
- 产出：T-b 需要新建/修改的组件清单（Harbor task 目录→EnvironmentPackage 映射字段、verifier 执行接进 grading manager 的改动面、CC harness 的 terminal 任务面）+ 粗粒度工作量估计；T-a 作为对照/评测面的价值与成本；对"T-b 主线 + T-a 对照"结论的确认或修正。

## 输出

四份（任务 4 可选）可以合并成一份报告，写入 `docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/codex_env_code_audit_<date>.md`。要求：每个论断附文件路径+行号；实现切片给依赖顺序但不写实际代码（本轮是规划不是实现）；发现现状盘点报告有误的地方直接指出并纠正。
