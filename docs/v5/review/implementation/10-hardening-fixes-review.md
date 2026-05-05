# V5 Hardening Fixes Review

## 审查范围

本轮审查覆盖上一轮复核提出的 P1 / P2 问题：

- acceptance inputs evidence ref 不校验路径、哈希和大小。
- acceptance core inspect 忽略 reference integrity failure。
- V5 bundle 没有把 final command log 作为 immutable evidence ref 绑定。
- 未通过 final verifier 的记录进入 trainable export。
- core matrix 文档口径高于实际证据。
- Stage 6 日志和审查记录没有进入新的证据链。
- Stage 5 result summary 和 repro command index 存在硬编码路径。

## 审查发现

P1 问题已经通过代码和测试修复：

- `tests/unit/test_v5_acceptance.py` 覆盖 tampered evidence ref、tampered acceptance report ref 和 tampered final command log。
- `tests/unit/test_v5_export_pack.py` 覆盖未执行 final verifier 时 trainable 分区为空。
- `tests/unit/test_v5_demo_artifacts.py` 覆盖任务库存数字和 export pack 路径来自显式输入。

P2 问题处理结果：

- `docs/v5/implementation-plan.md` 已把 scaffold / budget 双轴比较从 core 口径移到 resume-ready comparison 口径。
- 新的 hardening implementation log 和 review record 将作为本轮 Stage 6 acceptance inputs 的输入。
- Stage 5 hardening 产物已经重新生成，不再引用旧 Stage 4 hard-coded 路径。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_*.py -p no:cacheprovider
```

结果：

```text
57 passed
```

已通过：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-20260505T184706Z/v5_resume_artifact_index.json --assert-share-safe
```

## 当前验收判断

本轮 hardening 后不能继续声明 V5 core acceptance passed。原因是 trainable export 已按 final verifier 边界降级为 `real_provider_trainable_records=0`，所以 `inspect-v5-acceptance --assert-core-complete` 必须失败。

这不是回归，而是修复假阳性后的正确状态。当前允许声明的是 evidence chain hardened、public-safe demo artifacts generated 和 immutable bundle passed。

## 是否允许进入最终提交

允许进入最终提交，前提是：

- 新的 Stage 6 hardening acceptance inputs、acceptance report 和 acceptance bundle 生成完成。
- `inspect-v5-inputs --assert-complete` 通过。
- `inspect-acceptance-bundle --assert-immutable` 通过。
- `inspect-v5-acceptance --assert-core-complete` 的失败被明确记录为预期失败，而不是忽略。
