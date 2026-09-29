你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。项目文档与协作规则见 AGENTS.md；审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 Claude（B 线 R2E）今晚的两处未提交代码改动，用 `git diff` 看改动：

A. R2E 材料修订新增第五类 `statement_text_replace`（题面文本替换）。文件：rh2/src/repoharness2/envpack/ingest_r2e_subset.py；测试 rh2/tests/envpack/test_ingest_r2e_subset.py 的新增部分。依据：v1 §5 R-f 与 §9 D6（"R2E 在现有材料修订框架内新增一类题面文本替换，实现后经 Codex 复核再用"）。实现由一个子代理写、中途断连，Claude 读过 diff 并在本机跑过该测试文件（60 passed、ruff 通过）。请重点看：题面修订在构建公开面之前应用、sha 前后校验、拒绝情形、修订号是否可追溯（修订后的题可识别为标明版本的自建题）、消费期重验、对现有四类修订与 v3 修订单是否零影响、公开面泄漏扫描是否仍覆盖修订后题面。

B. R2E 派生配方新增构建配置步骤 `sysconfig_v1.sh`，由 `build_r2e_derived.py --sysconfig-fix` 启用。文件：rh2/scripts/r2e_derive/sysconfig_v1.sh（新）、rh2/scripts/build_r2e_derived.py、rh2/tests/envpack/test_build_r2e_derived_sysconfig.py（新）。依据：v1 §5 R-d；用户 09-25 批准"C 扩展重建可以修"。证据：runs/r2e_lifecycle_20260929/evidence/sysconfig_manual_before_after_20260929.txt（同镜像、同编辑、同命令的修前修后对照）、evidence/facts_orange3_4014_sysconfig.json（新配方构建的复核事实）、evidence/overlays_all_45.jsonl。请重点看：是否只改搬迁后解释器的构建配置、不动 /testbed 与 .venv 与 /root；配方身份叠加（+sysconfig_v1、tag 后缀 s、摘要口径）与既有材料 / 环境步骤及 REVISION_ENV_REQUIREMENTS（环境要求按叠加前的原配方核对）是否一致；不带开关时是否逐字节兼容；复核项 sysconfig_paths_relocated 是否足够。

请输出（中文、简洁）：
1. 每处改动的 P0 / P1 / P2 问题，附文件与行号、反例或复现方式；没有就写没有。
2. A 是否可以用于正式材料（给 pillow 2b061b68、orange3 22e98f8f 的 R-f 修订）；需要先改什么。
3. B 的 v1 §5 "R-d 验收"四点逐条：已满足、未满足、还缺什么证据（例如"改源码 → 构建 → 正式导出 → 全新 grader 加载新产物"的端到端尚未做）。
4. 其它你认为必须在今晚正式使用前处理的事项。
