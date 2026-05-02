# V3 Stage 06 Implementation Review

## 审查范围

本审查覆盖阶段 6 的 SWE-Bench-like environment spec、verifier plan、selector 转换、baseline F2P/P2P evidence、gold patch evidence、独立 final verifier result 和 `inspect-swebench-like`。

本审查不覆盖阶段 7 Agent Loop 集成、真实 provider 运行、训练导出审计或最终 acceptance bundle。

## 本地自审

本地自审检查：

- 是否为 3 个 accepted task 都生成 `SweBenchLikeEnvironmentSpec` 和 `SweBenchLikeVerifierPlan`。
- 是否解析 evaluator-only `FAIL_TO_PASS` 和 `PASS_TO_PASS`，并通过 selector cache 记录原始 selector 与 expanded selector。
- 是否覆盖 `sympy__sympy-24909` 裸函数名 selector 转换。
- 是否执行 baseline fail-to-pass、baseline pass-to-pass、gold patch 和 final patch verifier。
- 是否明确记录 official harness report 未作为 final verifier。
- `inspect-swebench-like --assert-complete` 是否重新读取并执行 verifier plan command。

## 自审发现和修复

### P1：阶段 6 机器产物不完整

只读子代理第一次复审时，阶段 6 产物正处于被清理后重建的中间窗口，因此看到 `swebench_like_task_manifest.json` 缺失、任务目录不完整。

修复：从干净的阶段 5 source materialization 产物重新构建 `runs/v3-stage-06-swebench-like-20260502T191500Z/`，随后运行 `inspect-swebench-like --assert-complete` 通过。当前产物包含 3 个 accepted task 的 manifest、environment spec、verifier plan、selector cache、baseline/gold/model final evidence 和 `final_verifier_result.json`。

### P2：`environment_setup_commit` 写成字段哈希

只读子代理指出，初版从 `hidden_row.model_visible_field_sha256.environment_setup_commit` 读取值，写入的是字段哈希，不是真实环境设置提交号。

修复：builder 现在从阶段 5 task definition snapshot 的 metadata 读取真实 `environment_setup_commit`。inspect 要求该字段是 40 位提交号。重建后 `pytest-dev__pytest-7220` 记录为 `678c1a0745f1cf175c442c719906a1f13e496910`，`sympy__sympy-24909` 记录为 `be161798ecc7278ccf3ffa47259e3b5fde280b7d`。

### P3：旧 pytest parametrized selector 命令行选择问题

真实构建初次运行时，`pytest-dev__pytest-7220` 的部分 PASS_TO_PASS selector 参数值包含 `::`。旧 pytest 可以 collect 这些 node id，但命令行精确选择会把参数里的 `::` 当作 node 层级解析，导致 `not found`。

修复：当 selector 参数值包含 `::` 时，plan command 转换为同文件 `-k` 函数表达式。修复后重新构建阶段 6 产物，并运行 `inspect-swebench-like --assert-complete` 通过。

### P3：hidden verifier stdout/stderr artifact ref 标记偏松

只读子代理指出，初版 hidden verifier stdout/stderr 嵌套 ArtifactRef 使用默认 `not_required` redaction status。

修复：Docker verifier command stdout/stderr 和 patch apply stdout/stderr 现在标记为 `evaluator_only`。inspect 会递归检查 final verifier、baseline 和 gold evidence 中的 `stdout_ref` / `stderr_ref`。

## 负例覆盖

单元测试覆盖：

- 裸函数名 selector 可以映射到 test patch 中唯一测试文件。
- 多个 test patch 文件下的裸函数名 selector 会 fail closed。
- selector cache 的 expanded fail-to-pass 为空时 inspect 拒绝。

## 子代理审查

只读子代理第一次复审发现：

- P1：阶段 6 机器产物当时不完整。
- P2：`environment_setup_commit` 来源错误。
- P3：hidden verifier stdout/stderr ref 标记偏松。

上述发现均已修复并重新验证。最终只读复审结论为 P1 无、P2 无、P3 无。

最终复审确认：

- `runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json` 完整，`task_count=3`，3 个 accepted task 都包含 environment spec、verifier plan、selector cache、baseline evidence、gold evidence、model final evidence 和 `final_verifier_result.json`。
- `environment_setup_commit` 已是 task definition metadata 中的真实 40 位提交号。
- verifier evidence 和 final verifier result 中的 stdout/stderr refs 均为 `evaluator_only`。
- `inspect-swebench-like --assert-complete` 会重新读取并执行 baseline、gold、model final 的 fail-to-pass 和 pass-to-pass 命令。
- 未发现 official SWE-Bench harness report 被当作 final verifier。
- 未发现阶段 7 Agent Loop 越界实现。

## 结论

当前本地自审和最终只读复审均未发现剩余 P1/P2/P3 阻断项。阶段 6 允许进入阶段 7。
