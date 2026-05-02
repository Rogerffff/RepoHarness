# V3 Stage 07 Implementation Review

## 审查范围

本审查覆盖阶段 7 的 `run_task` 集成改动、SWE-Bench-like final-only runtime helper、Stage 7 build / inspect 命令、真实仓库 Docker Agent Loop run、SWE-Bench-like Agent Loop diagnostic run、tool call 终态配对和 V3 contamination scan。

本审查不覆盖阶段 8 可恢复 Experiment Runner、阶段 9 context compaction、阶段 10 failure diagnostics、阶段 11 export audit 或阶段 12 acceptance bundle。

## 子代理状态

按照阶段要求，优先尝试创建只读子代理做审查；当前环境返回 `agent thread limit reached`，无法新建审查子代理。因此本阶段执行等价独立只读自审，并在本文件记录审查维度、发现、修复和结论。

## 自审维度

自审检查：

- `run_task` 是否仍保持 V2 replay、mock provider、workspace、trajectory、reward 和 metadata 主线兼容。
- SWE-Bench-like final-only baseline 是否避免运行或暴露隐藏 F2P/P2P selector。
- SWE-Bench-like Agent Loop 后是否先冻结 `final.patch`，再在独立 verification workspace 中 strict patch replay。
- Stage 6 F2P/P2P final verifier 是否由 RepoHarness 自己执行，且不使用 official harness report。
- 真实仓库 run 是否在 Docker backend 下完成 accepted final verifier。
- 每个实际启动的 run 是否包含 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`run_config_facts.json`、`run_metadata.json` 和 final patch artifact。
- tool call 是否都有终态 tool result。
- prompt、prepared messages、tool observation 和 transcript 是否通过 V3 denylist scan。
- Docker backend 是否没有静默回退到 `local_process`。

## 自审发现和修复

### P2：系统提示暴露内部 reward artifact 名称

初次 Stage 7 构建后，污染扫描发现 prompt 和 prepared messages 中包含 `reward_metadata`。来源是 Context Builder 的系统提示直接要求模型不要访问 `reward metadata`。

风险：即使这是安全提示，内部对象名也进入了模型可见上下文，不符合 V3 对 reward metadata / hidden reward facts 的边界要求。

修复：将模型可见系统提示改为不暴露内部对象名的 `scoring artifacts`。重新构建 Stage 7 产物后，真实仓库和 SWE-Bench-like 污染扫描均为 clean。

### P2：公开 issue 中的 `/home/...` 示例路径被误判为本机路径泄漏

初次 Stage 7 构建后，SWE-Bench-like prompt 中的公开 issue 文本包含 `/home/lhn/src/...`，被 broad host path denylist 的 `/home/` 前缀命中。

风险：该路径来自公开问题描述，不是当前本机绝对路径；如果继续 broad match，会导致固定公开输入无法通过污染扫描。

修复：V3 denylist 改为记录当前 `Path.home()`、`/Users/`、`/private/` 和 Windows 盘符等本机路径前缀，不再把所有 `/home/...` 文本都视为本机泄漏。重新运行相关单元测试和 Stage 7 inspect 通过。

### P3：SWE-Bench-like Agent Loop run 是 diagnostic failed run

SWE-Bench-like Agent Loop run 使用不含隐藏解法材料的 diagnostic patch，因此 final verifier 完成但 `accepted=false`。

判断：阶段 7 的目标是证明常规 Agent Loop、final patch freeze、strict replay 和 RepoHarness 自有 final verifier 已经贯通；不要求用 evaluator-only gold patch 伪装模型成功。该项记录为允许的阶段性限制，不阻断进入阶段 8。

## 负例覆盖

新增 `tests/unit/test_v3_agent_loop.py`：

- `test_scan_v3_run_surfaces_detects_model_visible_forbidden_term`：模型可见 transcript 出现 `gold_patch` 时扫描失败。
- `test_inspect_v3_agent_loop_integration_rejects_unclean_scan`：Stage 7 report 引用 dirty contamination scan 时 inspect 拒绝。

既有 `tests/unit/test_v3_visibility_policy.py` 继续覆盖 hidden marker、official status、provider raw、credential 和 reward marker 的 denylist 行为。

## 验证结果

- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_agent_loop.py tests/unit/test_v3_visibility_policy.py -q`：`6 passed`。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_agent_loop.py tests/unit/test_v3_visibility_policy.py tests/unit/test_v3_swebench_like.py tests/integration/test_single_shot_patch.py -q`：`14 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-agent-loop-integration runs/v3-stage-07-agent-loop-20260502T203000Z --report runs/v3-stage-07-agent-loop-20260502T203000Z/v3_agent_loop_integration_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator/docker_backend_status.json --assert-docker-backend`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`421 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。

## 复审结论

复审确认：

- 真实仓库 run 通过常规 Agent Loop、Docker backend 和 final verifier，最终 accepted。
- SWE-Bench-like run 通过常规 Agent Loop，生成 final patch，在 Docker backend 中执行 strict replay，并通过 Stage 6 verifier plan 执行 RepoHarness 自有 F2P/P2P final verifier。
- Stage 7 contamination scan clean，未发现 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、gold patch、official harness report、provider raw marker、credential marker 或本机绝对路径进入模型可见 surface。
- tool call pairing 完整，真实仓库 run 的 3 个 tool call 均有终态 tool result。
- V2 acceptance regression 通过。

当前未发现剩余 P1/P2/P3 阻断项。阶段 7 允许进入阶段 8。
