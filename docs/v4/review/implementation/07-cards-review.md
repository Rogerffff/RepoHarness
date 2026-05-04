# V4 Stage 7 Cards Review

## 审查范围

本次审查覆盖 Stage 7 cards、provenance、contamination summary、contamination scan report、repro command index、implementation log index、相关 inspect 命令和单元测试。

## 初轮发现

- P1：dataset card 的任务分布不是从上游 task freeze evidence 派生。
- P1：统一 V4 contamination denylist 缺少 commit material 禁止项。
- P1：implementation log index 中列出的真实日志文件没有被读取和扫描。
- P2：cards manifest 中 contamination scan report 和 implementation log index 的 ref 没有校验 sha256。
- P2：run card 和 export card 与 Stage 5、Stage 6 上游 evidence 的交叉校验不足。

## 第一轮修复

- dataset card 改为从 Stage 2 task freeze manifest 派生 accepted、diagnostic、quarantined 和 rejected 分布。
- run card 改为从 Stage 5 agent run integration report 派生 selected run refs 和 run status counts。
- export card 改为从 Stage 6 sample tier 和 preference trainability evidence 派生 trainable / diagnostic split。
- cards manifest 的全部关键 ref 都进入 inspect 校验。
- implementation log index 中列出的真实文件进入 V4 contamination scan。
- 统一 V4 contamination denylist 增加 commit material 禁止项，并重新生成受 hash 影响的 Stage 0、Stage 2、Stage 3、Stage 5、Stage 6 和 Stage 7 evidence。

## 复审发现

- P2：export card 使用的 Stage 6 辅助报告没有全部绑定到 provenance summary，blocked sources 也没有从 blocked pair report 派生。
- P2：Stage 7 card claim deny policy 没有进入 contamination scan report 的 clean 判定。

## 第二轮修复

- provenance summary 增加 export quality refs，绑定 trajectory quality manifest、sample tier manifest、preference pair trainability report 和 blocked pair report。
- export card 的 blocked sources 从 blocked pair report 派生。
- inspect-v4-cards 递归读取并校验上述 export quality refs 的 sha256，并交叉校验 export card 内容。
- Stage 7 card claim deny policy 移入统一 visibility 模块，提供 policy version 和 hash。
- contamination scan report 记录 card claim deny policy version 和 hash，并将 card claim findings 纳入 clean 判定。

## 最终复审

最终只读复审未发现 P1、P2 或 P3。复审确认：

- export card 从 Stage 6 辅助报告派生，并通过 provenance refs 校验 sha256。
- contamination scan report 包含 card claim deny policy version 和 hash。
- 通用 inspect-v4-contamination-scan 强制校验 findings 为空。
- tests 覆盖缺少 card claim policy、clean 与 findings 不一致、export card 与 Stage 6 不一致、export quality ref sha256 篡改。
- Stage 7 implementation log 与实现一致，并且会被 inspect-v4-cards 读取和扫描。

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-cards docs/v4/evidence/cards --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-contamination-scan docs/v4/evidence/cards/contamination_scan_report.json --assert-clean`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_cards.py tests/unit/test_v4_export_quality.py tests/unit/test_v4_stage1_skeleton.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 结论

Stage 7 可以进入 Stage 8。
