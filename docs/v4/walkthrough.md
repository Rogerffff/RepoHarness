# RepoHarness V4 Walkthrough

## 使用顺序

RepoHarness V4 的审计入口从最终 bundle 开始：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

该命令会复核 acceptance bundle 绑定的 V4 acceptance report、acceptance inputs、acceptance command log 和 post-acceptance documentation refs。

## 验收输入

V4 acceptance inputs 位于：

```text
runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json
```

可以使用以下命令单独检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json --assert-complete
```

该文件显式绑定 V2 / V3 regression evidence、Stage 0 implementation inputs、Stage 2 task freeze、Stage 3 rollout evidence、Stage 4 tool lifecycle evidence、Stage 5 agent run evidence、Stage 6 export evidence、Stage 7 cards evidence、contamination scan report、pre-acceptance command log 和 pre-acceptance documents。

## 阶段证据

主要阶段证据目录如下：

- `docs/v4/evidence/implementation-inputs/`
- `docs/v4/evidence/task-source-freeze/`
- `docs/v4/evidence/rollout-orchestration/`
- `docs/v4/evidence/tool-lifecycle/`
- `docs/v4/evidence/agent-run-integration/`
- `docs/v4/evidence/export-quality/`
- `docs/v4/evidence/cards/`

## 复现入口

Stage 7 生成的 repro command index 位于：

```text
docs/v4/evidence/cards/repro_command_index.json
```

它列出 V2 regression、V3 acceptance、V3 bundle、V4 task freeze、rollout、tool lifecycle、agent run、export quality、cards 和 final acceptance 的主要 inspect 命令。

## 训练导出边界

V4 的训练导出证据位于：

```text
docs/v4/evidence/export-quality/
```

其中 outcome tier 和 trainability status 是分开的。Verifier accepted 不会自动等于 trainable，diagnostic-only failure 也不会被静默写成 trainable failure sample。

## 污染扫描边界

Stage 7 contamination scan report 位于：

```text
docs/v4/evidence/cards/contamination_scan_report.json
```

可以使用以下命令检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v4-contamination-scan docs/v4/evidence/cards/contamination_scan_report.json --assert-clean
```

该报告绑定 task visibility scan report 和 contamination summary，并记录 card claim deny policy 的版本和哈希。
