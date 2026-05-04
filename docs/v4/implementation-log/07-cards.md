# V4 Stage 7: Cards

## 目标

阶段 7 的目标是生成 dataset card、run card、export card、provenance summary、contamination summary 和 repro command index，并用统一 V4 污染扫描规则检查这些卡片和阶段 7 实施日志。

## 实现内容

- 新增 `repo-harness build-v4-cards`。
- 新增 `inspect-v4-cards --assert-complete` 强检查器。
- dataset card 从 task freeze 和 export quality 产物派生任务来源与分布。
- run card 从 agent run integration 产物派生 selected run refs 和 run status counts。
- export card 从 export quality 产物派生 sample tiers、trainable / diagnostic split 和 blocked sources。
- provenance summary 绑定 task freeze、agent run integration、export quality manifest、sample tier manifest、preference pair trainability report 和 blocked pair report。
- contamination scan report 绑定 task freeze 的 task visibility scan report 和 Stage 7 contamination summary，可被全局 contamination inspect 递归复核。
- contamination scan report 记录 Stage 7 card claim deny policy version 和 hash，并把 card claim findings 纳入 clean 判定。
- repro command index 覆盖 V2 / V3 回归、V4 task freeze、rollout、tool lifecycle、agent run、export、cards 和 final acceptance inspect。
- 统一 V4 contamination denylist 增加 commit material 禁止项，并重新生成受 denylist hash 影响的 Stage 0、Stage 2、Stage 3、Stage 5、Stage 6 和 Stage 7 evidence。

## 主要修改文件

- `src/repo_harness/v4_cards.py`
- `src/repo_harness/v4_visibility.py`
- `src/repo_harness/v4_stage1.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_cards.py`
- `tests/unit/test_v4_stage1_skeleton.py`

## 机器产物

目录：`docs/v4/evidence/cards/`

- `dataset_card.md`
- `dataset_card.json`
- `run_card.json`
- `export_card.json`
- `provenance_summary.json`
- `contamination_scan_summary.json`
- `repro_command_index.json`
- `cards_manifest.json`
- `contamination_scan_report.json`
- `implementation_log_index.json`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-cards --output-dir docs/v4/evidence/cards --task-freeze docs/v4/evidence/task-source-freeze/task_freeze_manifest.json --agent-run-integration docs/v4/evidence/agent-run-integration --export-quality docs/v4/evidence/export-quality`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-cards docs/v4/evidence/cards --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-contamination-scan docs/v4/evidence/cards/contamination_scan_report.json --assert-clean`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_cards.py tests/unit/test_v4_export_quality.py tests/unit/test_v4_stage1_skeleton.py -q`

## 验证结果

- Compileall 通过。
- 阶段 7 build 通过。
- `inspect-v4-cards --assert-complete` 通过。
- `inspect-v4-contamination-scan --assert-clean` 通过。
- 阶段 7、阶段 6 和阶段 1 组合单元测试通过，57 个测试通过。

## 正例证据

- dataset card 记录任务来源、许可与来源摘要、accepted / diagnostic / quarantined / rejected 分布。
- run card 记录 selected run refs、provider mode、scaffold id、budget policy、Docker facts 和 resource usage summary。
- export card 记录 sample tiers、trainable / diagnostic split、blocked sources 和 export policy。
- contamination summary 和 contamination scan report 记录 clean 状态。
- contamination scan report 通过 artifact refs 绑定 `task_visibility_scan_report.json` 和 `contamination_scan_summary.json`。
- `inspect-v4-contamination-scan` 会校验 card claim deny policy 的版本、hash 和空 findings。
- provenance summary 通过 export quality refs 绑定 Stage 6 中用于 export card 派生的全部辅助报告。
- repro command index 覆盖 V2 baseline checks、V3 acceptance checks、V4 task freeze、rollout、tool lifecycle、agent run、export audit、card inspect 和 final acceptance inspect。

## 负例证据

测试覆盖以下失败场景：

- dataset card 声称可以跳过人工审查直接使用。
- dataset card 声称公开榜单可比。
- run card 声称 Docker backend 是生产安全隔离能力。
- card 缺少 contamination summary。
- card 或 provenance 中出现禁止的 source、provider、verifier、session 或 commit material marker。
- repro command index 缺少必需 inspect 命令。
- repro command index 依赖 latest run。
- implementation log 索引指向不存在文件。
- contamination scan report 缺少 bound artifact refs。
- export card 与 Stage 6 辅助报告不一致。
- export quality refs 的 sha256 被篡改。
- contamination scan report 缺少 card claim deny policy。
- contamination scan report 标记 clean 但仍包含 findings。
- cards manifest 中关键 ref 的 sha256 被篡改。

## 允许降级项

- cards 只作为审计摘要和复现入口，不声称数据可以免人工审查直接训练。

## 禁止降级项

- 不允许 card 声称公开榜单可比。
- 不允许 card 声称 Docker backend 是生产安全隔离能力。
- 不允许 card、provenance、repro command index 或阶段 7 实施日志包含被统一 V4 污染扫描规则禁止的内容。

## 已知限制

- cards 不是 post-acceptance final walkthrough。`docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md` 只能在 V4 final acceptance 通过后编写。

## 是否偏离设计文档

没有偏离。阶段 7 保持在 P1-4 轻量 cards、provenance、污染摘要和复现命令索引范围内。

## Subagent 或等价自审结论

阶段 7 初轮只读审查发现 dataset card 分布未从上游证据派生、统一污染规则缺少 commit material marker、implementation log 实际文件未扫描、cards manifest 两个关键 ref 未校验、run / export card 与上游证据交叉校验不足。上述问题已经修复并补充负例。最终复审结论见 `docs/v4/review/implementation/07-cards-review.md`。

## 是否可以进入下一阶段

最终复审通过后可以进入阶段 8。
