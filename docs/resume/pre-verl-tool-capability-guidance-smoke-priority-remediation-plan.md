# Pre-verl 工具能力提示 smoke 后四项优先修复执行计划

更新时间：2026-05-09  
状态：正式二十三题评测前建议先完成的四项 Harness 修复计划  
证据目录：`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z/`

## 1. 结论

本轮 Docker targeted smoke 已经证明新增工具和首轮工具使用提示进入了模型可见上下文，并且 `017 astroid` 和 `020 pydicom` 能产生 accepted 样本。因此当前基础链路可以继续作为后续评测基础。

但是，正式二十三题评测前不建议直接继续放大运行规模。当前最先应该修复四个会影响评测可信度和模型实际表现的问题：

1. `grep` 在 Docker workspace 下仍可能因为逐文件读取而耗时数分钟，同时 `tool_completed.duration_ms` 缺失或者不可用，导致工具延迟不可观测。
2. pass-to-pass verifier 的逐用例解析不可信，已经出现原始 pytest 输出显示多数用例通过，但结果 JSON 把所有 selector 都记为失败的情况。
3. timeout、max turns、final verifier 未执行等失败归因在 `final_verifier_boundary`、`run_metadata`、metrics 和 reward 之间不一致，可能污染正式汇总和训练导出。
4. 临近预算时的收敛控制仍然偏软，模型可以在没有补丁或者已经有补丁的情况下继续大范围只读探索，最终把任务拖到 `max_turns` 或任务超时。

这四项修复的共同目标不是提高某个具体模型的“聪明程度”，而是消除 Harness 自身对模型行为、工具成本、失败分类和训练样本有效性的干扰。

## 2. 本计划的范围和非目标

本计划只处理和模型能力、工具使用、评测可信度直接相关的问题。

范围内：

- 工具执行性能，尤其是 `grep` 在 Docker workspace 中的批量搜索路径。
- 工具执行耗时在 transcript、event、run metadata 中的真实记录。
- pass-to-pass 和 fail-to-pass selector 结果的逐用例可信解析。
- timeout、max turns、final verifier 未执行、空补丁、错误补丁等失败归因的一致性。
- 临近预算时面向模型的收敛提示和 AgentLoop 控制策略。

范围外：

- 不修改数据集 hidden tests、gold patch、evaluator-only material。
- 不把 hidden selector、hidden test output 或 verifier 内部信息放入模型可见上下文。
- 不调整 Claude Code 参考项目本身。
- 不把 Docker execution mode 描述成生产级安全沙箱。
- 不处理和本轮模型交互能力无关的 snapshot、审计归档、展示页面美化等内容。

## 3. 推荐实施顺序

| 顺序 | 修复项 | 为什么排在这里 |
|---:|---|---|
| 1 | 修复 Docker `grep` 性能和耗时可观测性 | 这是直接导致 `001 sqlfluff` timeout 的工具问题。先修它可以缩短后续所有 smoke 和正式评测的运行时间。 |
| 2 | 修复 pass-to-pass 逐用例解析 | 这是结果可信度问题。它会把“多数 selector 通过”错误记录成“全部失败”，影响 verifier 诊断、reward 和简历展示指标。 |
| 3 | 统一 timeout、max turns、final verifier 未执行的失败归因 | 这是正式汇总和训练导出的基础。修完解析后再统一归因，可以让 reward 和 metadata 使用同一套事实。 |
| 4 | 增强临近预算收敛控制 | 这是模型交互策略问题。前三项先保证工具成本和结果记录可信，最后再评估收敛策略是否真正提升 accepted 率和有效补丁率。 |

## 4. 修复项一：Docker `grep` 性能和耗时可观测性

### 4.1 当前证据

本轮 smoke 中 `001 sqlfluff` 第 3 轮和第 18 轮都执行了类似下面的搜索：

```text
grep root="test" pattern="L031" output_mode="files_with_matches"
```

每次扫描约 1505 个候选文件，实际耗时约 6 分半，最终把任务拖到 `task_timeout`。这类耗时不是模型能力问题，而是工具执行路径在 Docker workspace 下过慢。

同时，工具生命周期事件中的 `tool_completed.duration_ms` 缺失或者不可作为可靠耗时指标。也就是说，即使工具实际执行了数分钟，汇总层也无法稳定知道是哪一个工具调用消耗了时间。

当前耗时可以从 `container_execution_facts` 侧复核，而不是从 `tool_completed.duration_ms` 直接复核。建议使用下面的方式汇总当前 smoke 中每个 run 的容器命令语义和耗时：

```bash
python - <<'PY'
from pathlib import Path
import collections
import json

root = Path("runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z/run_task_runs")
for run_dir in sorted(root.iterdir()):
    summary = collections.defaultdict(lambda: [0, 0, 0])
    for fact_path in (run_dir / "container_execution_facts").glob("*.json"):
        fact = json.loads(fact_path.read_text())
        semantics = fact.get("command_semantics") or "unknown"
        duration_ms = int(fact.get("duration_ms") or 0)
        summary[semantics][0] += 1
        summary[semantics][1] += duration_ms
        summary[semantics][2] = max(summary[semantics][2], duration_ms)
    print(run_dir.name, sorted(summary.items(), key=lambda item: item[1][1], reverse=True)[:3])
PY
```

本轮可观察到 `001 sqlfluff` 和 `014 astroid` 都有大量 `file_read` 语义的容器事实，总耗时达到数百秒级。这和宽 `grep` 触发逐文件读取的判断一致。

对照 Claude Code TypeScript 参考实现后，需要把本项修复从“如果 `rg` 可用则优先使用”收紧为“正式 Docker 评测环境默认必须提供 `rg`”。Claude Code 的 `GrepTool` schema 直接使用 `rg` 语义，`GrepTool.call()` 最终调用 `ripGrep(...)`，`utils/ripgrep.ts` 的正常路径是系统 `rg`、bundled / embedded ripgrep 或 vendor ripgrep，而不是 Python 搜索。它在资源受限的 Docker / CI 场景下也优先用 `rg -j 1` 单线程重试，而不是切换到 Python 搜索。相关证据在：

- `reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts`
- `reference/claude-code-typescript-src/utils/ripgrep.ts`
- `reference/claude-code-typescript-src/utils/bash/ShellSnapshot.ts`
- `reference/claude-code-typescript-src/utils/sandbox/sandbox-adapter.ts`
- `reference/claude-code-typescript-src/components/sandbox/SandboxDependenciesTab.tsx`

当前 RepoHarness 的 Docker image 模板位于 `src/repo_harness/workspace/docker_adapter.py`，默认只安装了 `git`，没有安装 `ripgrep`。因此本项修复必须优先修改 Docker 环境，而不是只在 Python 工具层增加一个更快的 fallback。

### 4.2 目标行为

修复后需要满足：

- 正式 pre-verl、targeted smoke 和二十三题评测使用的 Docker image 默认安装 `ripgrep`，并在 workspace 初始化或 run preflight 阶段验证 `command -v rg` 和 `rg --version`。
- Docker workspace 中的 `grep` 和 `glob_files` 默认后端必须是 `rg`。正式评测路径中如果 `rg` 缺失、不可执行或者版本探测失败，应 fail fast，并把失败写入 dependency facts，而不是静默切换到 Python 搜索。
- `grep` 在 Docker workspace 中使用单次 `rg` 批量搜索，而不是对候选文件逐个执行 `read_file` 或逐个容器读取。
- 当 `rg` 在 Docker / CI 资源受限环境中出现线程创建失败、`EAGAIN` 或 `Resource temporarily unavailable` 之类错误时，优先使用 `rg -j 1` 单线程重试。
- Python 搜索只保留为显式降级路径，必须通过配置或者测试场景明确启用。只要触发 Python fallback，结果 envelope 必须写出 `search_backend=python_fallback`、`fallback_reason`、`semantic_complete` 和 `recovery_hint`。
- 搜索结果必须保留现有可信协议：分页、截断、partial scan、`semantic_complete=false`、`recovery_call` 和 `recommended_next_calls` 不能丢。
- 宽搜索可以被限时或者返回 partial result，但不能把不完整搜索伪装成可信的 no-match。
- 每次工具调用都必须记录真实 `duration_ms`，并在 transcript event 和 typed result envelope 中可恢复。

### 4.3 建议修改位置

主要修改：

- `src/repo_harness/tools/minimal.py`
  - 修改 `grep` 工具执行路径。
  - 补充 `result_envelope` 中的 `search_backend`、`fallback_reason`、搜索统计和耗时字段。
- `src/repo_harness/workspace/adapter.py`
  - 增加可选的批量文本搜索接口，例如 `search_text(...)`。
- `src/repo_harness/workspace/docker_adapter.py`
  - 修改 `DEFAULT_DOCKERFILE_TEMPLATE`，默认安装 `ripgrep`。
  - 在 Docker backend 初始化后执行 `rg` dependency probe，并把 `rg_path`、`rg_version`、`rg_probe_exit_code`、`search_backend_default` 写入 Docker backend facts 或 run metadata facts。
  - 实现 Docker workspace 下的批量搜索。
  - 默认调用容器内 `rg`。正式评测路径不允许静默使用 Python fallback。
- `src/repo_harness/config/schemas.py`
  - 如有必要，增加 Docker 搜索后端策略字段，例如 `require_ripgrep_for_docker_search=true` 和 `allow_degraded_python_search_fallback=false`。
- `src/repo_harness/agent_loop/loop.py`
  - 在工具执行包装层记录真实开始时间和结束时间。
  - 确保 `tool_completed.duration_ms` 对成功、失败、超时三类结果都存在。
- `src/repo_harness/context/manager.py`
  - 如有必要，确保上下文压缩后仍保留慢工具的恢复调用和关键 envelope 字段。

### 4.4 实施步骤

1. 梳理当前 `grep` 的候选文件获取路径，确认 Docker workspace 下是否通过逐文件 `file_read` 完成内容扫描。
2. 修改 Docker image 默认构建模板：
   - 在 `src/repo_harness/workspace/docker_adapter.py` 的 `DEFAULT_DOCKERFILE_TEMPLATE` 中把 `ripgrep` 加入 `apt-get install -y --no-install-recommends`。
   - 保持 `git`、`pytest`、`mpmath` 等既有依赖不变。
   - 对基于 `python:*slim` 的默认评测镜像，预期安装命令类似 `apt-get install -y --no-install-recommends git ripgrep`。
3. 增加 Docker dependency probe：
   - image build 或 container 初始化后执行 `command -v rg`。
   - 执行 `rg --version` 并记录第一行版本信息。
   - 在 `docker_backend_facts.json`、run metadata facts 或等价 artifact 中写入 `rg_available`、`rg_path`、`rg_version`、`rg_probe_exit_code`。
   - 如果当前运行是正式 pre-verl Docker 评测，并且 `require_ripgrep_for_docker_search=true`，则 `rg_available=false` 必须直接阻断运行。
4. 在 workspace adapter 增加批量搜索能力，接口至少包含：
   - `pattern`
   - `root`
   - `glob`
   - `output_mode`
   - `case_sensitive`
   - `max_results`
   - `timeout_seconds`
5. Docker 实现中默认使用单次 `rg` 命令完成批量搜索：
   - `files_with_matches` 使用 `rg -l`。
   - `count` 使用 `rg -c`。
   - `content` 使用 `rg -n`，并根据 `context`、`-A`、`-B`、`-C` 加上下文参数。
   - `glob` 映射为 `--glob`。
   - Python 文件类型等标准类型优先映射为 `--type`，如果输入工具 schema 暂时没有 `type` 参数，可以先只保留 `glob`。
   - 默认排除 `.git`、`.svn`、`.hg`、`.bzr` 等版本控制目录。
   - 默认加上 `--hidden` 和合理的 `--max-columns`，避免漏掉隐藏文件和被超长行污染上下文。
6. 明确处理 `rg` exit code：
   - exit code `0` 表示有匹配。
   - exit code `1` 表示搜索完成但没有匹配，可以返回可信 no-match。
   - exit code `2` 或其他错误表示搜索失败，不能伪装成 no-match。
7. 处理 Docker / CI 资源限制：
   - 如果 stderr 包含 `os error 11`、`Resource temporarily unavailable` 或同类线程创建失败信号，重试一次 `rg -j 1`。
   - 单线程重试仍失败时，返回 recoverable search error，并给出缩小搜索范围的 `recovery_call`。
8. Python fallback 只作为显式降级路径：
   - 默认正式评测配置为 `allow_degraded_python_search_fallback=false`。
   - 只有本地开发、单元测试或特殊兼容配置明确打开时，才允许调用一次容器内 Python 搜索脚本。
   - fallback 结果必须标记 `search_backend=python_fallback`，并写出 `fallback_reason`。
   - 正式 smoke 和二十三题评测中如果出现 Python fallback，应作为 Harness 环境问题处理，而不是正常工具成功路径。
9. 本地 workspace 实现也走同一抽象，优先使用本机 `rg`，再根据配置决定是否 fallback 到 Python 搜索。
10. 保留现有文件可见性过滤和 workspace boundary 检查，严禁搜索 evaluator-only 路径。
11. 为宽搜索增加明确的超时和 partial result：
   - 超时后返回 `status="ok"` 或工具协议当前允许的 recoverable 状态，但必须设置 `semantic_complete=false`。
   - 返回 `recovery_call`，建议模型缩小 `root`、补充 `glob` 或使用 `repository_action_index` / `symbol_search`。
12. 在工具执行外层统一记录耗时：
   - `tool_requested` 记录开始时间或者调用序号。
   - `tool_completed` 写入 `duration_ms`。
   - typed result envelope 写入同一个 `duration_ms` 或 `execution_duration_ms`。
13. 对 Python fallback 保留单元测试，但测试名称和断言必须明确它是 degraded fallback，不是 Docker 正式评测默认路径。

### 4.5 验证方式

新增或更新单元测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_tools.py \
  tests/unit/test_agent_loop_protocol.py
```

重点断言：

- Docker 默认 Dockerfile template 包含 `ripgrep`。
- Docker backend 初始化会探测 `command -v rg` 和 `rg --version`，并把结果写入 facts。
- 当 `require_ripgrep_for_docker_search=true` 且 `rg` 探测失败时，正式 Docker 运行会 fail fast。
- `grep` 返回 no-match 时，如果搜索被截断或者超时，必须是 `semantic_complete=false`，不能是可信 no-match。
- `grep` 返回 partial result 时必须包含 `recovery_call` 或 `recommended_next_calls`。
- `tool_completed.duration_ms` 在工具成功、工具失败、工具 recoverable error 三种路径下都不是空值。
- Docker adapter 的批量搜索路径不会对每个候选文件触发一次独立 `file_read`。
- 对一次宽 `grep` 调用，应能断言 Docker adapter 只执行一次 `rg` 命令，而不是生成上千条候选文件级 `file_read` container facts。
- 对资源类错误，应先触发 `rg -j 1` 单线程重试；只有显式允许 degraded fallback 时才允许 Python fallback。
- Python fallback 测试必须显式设置 `allow_degraded_python_search_fallback=true`，并断言结果 envelope 中出现 `search_backend=python_fallback` 和 `fallback_reason`。

建议增加一个轻量 Docker adapter 测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_workspace_lifecycle.py
```

同时增加一个真实容器依赖探测验证，可以在 smoke 前对即将使用的 image 执行：

```bash
docker run --rm IMAGE_REF sh -lc 'command -v rg && rg --version | head -1'
```

正式 smoke 前的验收标准：

- Docker backend facts 中 `rg_available=true`，并且有 `rg_version`。
- `grep` / `glob_files` 的正式 Docker 工具结果中 `search_backend` 为 `ripgrep` 或 `ripgrep_single_thread_retry`。
- 正式 targeted smoke 中 `python_fallback_count=0`。如果出现 Python fallback，应先修 Docker 环境或搜索后端，不应直接进入二十三题评测。
- 同一类宽 `grep` 不应再出现数分钟耗时。
- 如果某次搜索确实因为仓库规模或者容器性能超时，run artifact 中能看到该工具调用的真实 `duration_ms`、`semantic_complete=false` 和可执行恢复调用。
- `001 sqlfluff` 不应再因为两次宽 `grep` 被拖入 `task_timeout`。

## 5. 修复项二：pass-to-pass 逐用例解析

### 5.1 当前证据

本轮 smoke 的 `015 astroid` 中，pass-to-pass raw output 显示 pytest 实际执行结果是“大多数通过、少数失败”的形态，但结果 JSON 记录成 `passed_count=0`，并把所有 selector 都归为失败。

这说明当前链路可能把 suite-level exit code 直接映射到了每个 selector 上：只要整个 pytest 命令 exit code 非零，就把全部 selector 标记为 failed。这会严重污染 pass-to-pass 统计。

### 5.2 目标行为

修复后需要满足：

- selector 级别结果必须来自 pytest 输出中的逐用例事实，而不是只来自整条命令的 exit code。
- 如果 pytest 输出能证明某个 selector 失败，则该 selector 记为 failed。
- 如果 pytest 输出能证明命令正常执行，并且某个 selector 没有出现在 failed、error、skipped、xfailed 等异常集合中，则该 selector 可以记为 passed。
- 如果输出不足以证明某个 selector 的状态，应该记为 unknown 或当前 schema 中等价的“不可信状态”，不能默认全部 failed。
- 解析失败必须显式写入 `parser_confidence`、`parse_warning` 或等价诊断字段。

### 5.3 建议修改位置

主要修改：

- `src/repo_harness/verifier/pytest_parser.py`
  - 增加或增强 pytest 输出解析。
  - 解析 summary counts、failed node ids、error node ids、skipped counts 等结构化事实。
- `src/repo_harness/pre_verl_agentloop.py`
  - 修改 `_selector_result_payload` 或相邻构造逻辑。
  - 不再用整条命令的 exit code 直接覆盖每个 selector 状态。
- `src/repo_harness/reward/calculator.py`
  - 如 reward 使用 pass-to-pass 统计，需要确认它读取的是修复后的逐 selector 结果。
- `src/repo_harness/evaluation/metrics.py`
  - 如 metrics 使用 pass-to-pass 统计，需要确认汇总口径同步。

### 5.4 实施步骤

1. 在 `pytest_parser.py` 中实现明确版本号，例如 `pytest_parser_v1`。
2. 解析 pytest 输出中的短摘要和失败列表，至少支持：
   - `N failed, M passed`
   - `FAILED path::Class::test_name`
   - `ERROR path::Class::test_name`
   - collection error
   - timeout 或命令未完整执行
3. `_selector_result_payload` 接收 selector 列表和 parser 输出后逐个构造状态：
   - selector 在 failed 集合中：`failed`
   - selector 在 error 集合中：`error` 或当前 schema 允许的失败状态
   - suite 完整执行且 selector 未出现在异常集合中：`passed`
   - suite 未完整执行或 parser 置信度不足：`unknown`
4. 在结果 JSON 中写入解析依据：
   - `parser_version`
   - `parser_confidence`
   - `summary_counts`
   - `unknown_count`
   - `parse_warnings`
5. 测试 fixture 使用合成 pytest 输出，不要把当前 run 中的 hidden selector 全量复制进测试源码。
6. 检查 fail-to-pass 和 pass-to-pass 两条路径，避免只修一边。

### 5.5 验证方式

新增或更新单元测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_pytest_parser.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_reward.py
```

重点断言：

- 合成输出中如果 summary 是 `1 failed, 23 passed`，selector 结果必须是 `failed_count=1`、`passed_count=23`，不能是全部 failed。
- collection error 或 timeout 时不能伪造 passed。
- parser 不能解析时必须暴露 unknown 或 parse warning。
- pass-to-pass 和 fail-to-pass 统计都使用 selector 级别事实。

正式 smoke 前的验收标准：

- `015 astroid` 类型的结果不会再出现 raw output 和 JSON summary 明显矛盾。
- final verifier rejected 可以仍然 rejected，但 pass-to-pass 细分统计必须可信。

## 6. 修复项三：统一 timeout、max turns、final verifier 未执行的失败归因

### 6.1 当前证据

本轮 smoke 中 `001 sqlfluff` 的 final verifier boundary 正确记录为：

```text
failure_category = task_timeout_before_final_verifier
failure_owner = budget_or_timeout
```

但 `run_metadata.failure_diagnostics` 仍然是 `unknown_failure`。同时，部分 metrics 和 reward 字段没有把 task timeout、final verifier 未执行、invalid training sample 这几件事情统一起来。

如果正式二十三题评测直接读取 `run_metadata` 或 reward 汇总，就可能把 Harness timeout 误认为未知失败，或者把无效样本的 reward 误用于训练统计。

### 6.2 目标行为

修复后，同一个 run 的失败事实必须在以下位置一致：

- `final_verifier_boundary.json`
- `run_metadata`
- evaluation metrics
- reward metadata
- export manifest 或训练导出过滤逻辑

建议统一成下表：

| 情况 | boundary | run metadata | metrics | reward / export |
|---|---|---|---|---|
| 任务超时且 final verifier 未执行 | `task_timeout_before_final_verifier`，owner 为 `budget_or_timeout` | 同一 failure type，不能是 `unknown_failure` | `timeout=true`，final verifier status 为 `not_executed` | `invalid_for_training=true`，训练使用的 reward 置为 `0.0`，RL export 排除该样本 |
| `max_turns` 且空补丁 | `budget_exhausted_empty_patch`，owner 为 `budget_or_timeout` | 同一 failure type | `max_turns=true` 或等价预算耗尽字段 | `invalid_for_training=true`，训练使用的 reward 置为 `0.0`，RL export 排除该样本 |
| final verifier 执行但 rejected | `model_wrong_fix` 或等价模型错误修复分类 | 同一 failure type | final verifier status 为 `rejected` | 可以作为 rejected 样本进入评估，训练使用策略由 reward schema 明确 |
| final verifier accepted | 无失败归因 | 无失败诊断 | accepted | 有效 accepted 样本 |

### 6.3 建议修改位置

主要修改：

- `src/repo_harness/pre_verl_agentloop.py`
  - 确认 final verifier boundary 的失败分类是统一事实来源之一。
- `src/repo_harness/evaluation/runner.py`
  - task timeout、max turns、final verifier skip 的状态写入要完整。
- `src/repo_harness/evaluation/metrics.py`
  - 修正 timeout 和 final verifier not executed 的汇总口径。
- `src/repo_harness/run_metadata/writer.py`
  - 使用 boundary 或统一 helper 生成 `failure_diagnostics`。
- `src/repo_harness/reward/calculator.py`
  - invalid training sample 的 reward 处理需要明确。
- `src/repo_harness/export/exporter.py`
  - 确认 invalid sample 不进入 RL 训练样本，或者 reward 被置为零并带有 invalid reason。

### 6.4 实施步骤

1. 增加一个统一归因 helper，例如：

```text
derive_final_outcome(...)
```

输入至少包括：

- agent stop reason
- task timeout flag
- max turns flag
- final verifier execution status
- final verifier boundary failure category
- patch 是否为空
- final verifier accepted / rejected

输出至少包括：

- `failure_owner`
- `failure_type`
- `failure_category`
- `final_verifier_status`
- `timeout`
- `invalid_for_training`
- `invalid_reason`

2. `final_verifier_boundary` 可以继续由现有逻辑生成，但 `run_metadata`、metrics、reward 不应各自重新猜测失败原因。
3. 对 invalid sample 采用明确 reward 规则：
   - 本计划采用的规则是：`invalid_for_training=true` 时，训练使用的 `final_reward` 置为 `0.0`。
   - 如果仍想保留诊断分数，则新增 `diagnostic_reward_before_invalid_clip`，避免正式训练和展示误读。
   - RL export 必须继续排除 invalid sample；即使后续导出路径误读了 reward 字段，也只能看到 `0.0`，不能看到可被训练误用的非零 reward。
   - 这条规则只影响 timeout、max turns、final verifier 未执行等无效训练样本，不应改变 final verifier 已经正常执行后的 accepted / rejected 评测统计。
4. 更新 inspect 命令，增加一致性断言，例如：
   - `--assert-run-metadata-attribution-consistent`
   - `--assert-metrics-timeout-consistent`
   - `--assert-invalid-reward-excluded`
5. 对已有 timeout 和 max turns 测试补充断言，不只检查 boundary，还要检查 metadata、metrics 和 reward。

### 6.5 验证方式

新增或更新测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/integration/test_pre_verl_agentloop_runtime.py \
  tests/integration/test_eval_runner_quality_gate.py \
  tests/unit/test_run_metadata.py \
  tests/unit/test_reward.py \
  tests/unit/test_export.py
```

重点断言：

- task timeout before final verifier 不再产生 `unknown_failure`。
- `final_verifier_boundary` 和 `run_metadata.failure_diagnostics` 的 failure type 一致。
- metrics 中 timeout 状态和 boundary 一致。
- invalid sample 不会以非零训练 reward 进入 RL export。
- final verifier rejected 和 final verifier not executed 不会被混成同一类。

正式 smoke 前的验收标准：

- `001 sqlfluff` 类型的 timeout run 在所有汇总文件中都被归因为预算或超时问题。
- `014 astroid` 类型的空补丁 max turns run 不再显示未知失败。
- accepted run 的 reward 和 metadata 不受影响。

## 7. 修复项四：增强临近预算收敛控制

### 7.1 当前证据

本轮 smoke 中：

- `014 astroid` 到 48 轮仍然没有提交补丁，`first_edit=None`，最终 `max_turns`。
- `020 pydicom` 虽然 accepted，但第 41 轮才第一次编辑，第 48 轮才结束，说明任务成功也接近预算上限。
- 当前 convergence nudge 已经存在，但它更像温和提醒。模型在收到提醒后仍然可以继续大范围只读探索，没有被更强地引导到“最小补丁、最后一次精确读取、或者明确放弃”。

### 7.2 目标行为

修复后需要满足：

- 当剩余 turn 数已经很少且没有补丁时，模型必须收到明确的临近预算决策提示。
- 当已经存在补丁但仍在大范围探索时，模型必须收到明确的 finalize 提示，优先 `git_diff`、小范围修正和最终回答。
- convergence nudge 不能因为早期已经发过一次普通提醒，就阻止后期更高优先级的预算提醒。
- 提示内容不能泄漏 hidden tests、gold patch、verifier 内部信息。
- AgentLoop 要记录每次收敛提示的触发原因、预算状态和模型后续是否采取行动。

### 7.3 建议修改位置

主要修改：

- `src/repo_harness/agent_loop/loop.py`
  - 修改 `_should_inject_convergence_nudge`、`_record_convergence_nudge` 和相关进度摘要逻辑。
  - 增加临近预算分级策略。
- `src/repo_harness/agent_loop/schemas.py`
  - 如需要，补充 convergence event 或 progress summary 字段。
- `src/repo_harness/context/builder.py`
  - 确保首轮工具提示和后续收敛提示语义一致。
- `src/repo_harness/run_metadata/writer.py`
  - 记录是否触发过 near-budget decision nudge，以及触发后是否出现 edit 或 final answer。

### 7.4 实施步骤

1. 增加新的策略版本，例如：

```text
convergence_nudge_policy_v2
```

2. 在 AgentLoop 状态中持续记录以下事实：
   - 当前 turn index
   - 最大 turn 数
   - 剩余 turn 数
   - 是否已有非空 patch
   - 第一次编辑发生在哪一轮
   - 最近一次 mutating tool 发生在哪一轮
   - 连续只读工具调用数量
   - 是否已经调用过 `git_diff`
   - 是否出现重复搜索或者重复读取同一文件
3. 将 convergence nudge 分成至少三个等级：

| 等级 | 触发条件 | 模型可见意图 |
|---|---|---|
| 普通探索提醒 | 多轮只读、重复搜索、没有明确工作状态 | 要求缩小搜索范围，使用 `update_working_state` 记录假设 |
| 临近预算且无补丁 | 剩余 turn 数小于等于 6，且没有非空 patch | 必须选择最小补丁、最后一次精确读取后编辑，或者明确给出无法安全修改的最终回答 |
| 临近预算且已有补丁 | 剩余 turn 数小于等于 4，且已有非空 patch | 必须调用 `git_diff`，只做必要的小修正，然后最终回答 |

4. 修改去重逻辑：
   - 普通探索提醒不能阻止后续临近预算提醒。
   - 无补丁提醒和已有补丁提醒按不同 escalation level 去重。
   - 如果补丁状态从空变成非空，应允许新的 finalize 提醒。
5. 对无补丁临近预算提示使用清晰但不泄漏答案的内容，例如：

```text
剩余工具轮数已经很少。请停止大范围探索，并在接下来的操作中选择一个可完成路径：
1. 如果已经知道最小安全修改，请读取必要的精确上下文并提交补丁。
2. 如果只缺少 edit_file.old_text，请只读取目标文件的最小范围，然后编辑。
3. 如果仍然无法定位安全修改，请直接给出最终回答，说明未提交补丁。
```

6. 对已有补丁临近预算提示使用 finalize 内容，例如：

```text
当前已经存在补丁且剩余工具轮数很少。请调用 git_diff 检查真实补丁，只做必要的小范围修正，然后给出最终回答。
```

7. 将每次提示写入 transcript event 和 run metadata：
   - `nudge_level`
   - `nudge_reason`
   - `turns_remaining`
   - `has_patch`
   - `first_edit_turn`
   - `post_nudge_action`
8. 不要把这类 nudge 作为训练目标的隐藏答案。export 时继续保留已有的训练有效性过滤策略。

### 7.5 验证方式

新增或更新测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_agent_loop_protocol.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_run_metadata.py
```

重点断言：

- 早期普通 convergence nudge 不会阻止后期 near-budget nudge。
- 当剩余 turn 数小于等于阈值且没有补丁时，会注入 `near_budget_patch_or_stop` 等价事件。
- 当已有补丁且剩余 turn 数小于等于阈值时，会注入 `near_budget_finalize_patch` 等价事件。
- nudge 内容不包含 hidden tests、gold patch、verifier 输出。
- metadata 能记录 nudge 后模型是否编辑、是否调用 `git_diff`、是否最终回答。

正式 smoke 前的验收标准：

- `014 astroid` 类型任务不应再静默消耗到 48 轮且没有任何高优先级临近预算提示。
- 如果模型仍然不提交补丁，metadata 中必须清楚显示“已经触发临近预算决策提示，但模型仍未提交补丁”，不能继续表现为普通 max turns。
- `020 pydicom` 类型任务即使 accepted，也应减少补丁后无效探索，并在接近预算时优先 finalize。

## 8. 综合验证清单

完成四项修复后，先执行非 Docker 验证：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_tools.py \
  tests/unit/test_agent_loop_protocol.py \
  tests/unit/test_pytest_parser.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_run_metadata.py \
  tests/unit/test_reward.py \
  tests/unit/test_export.py \
  tests/integration/test_pre_verl_agentloop_runtime.py \
  tests/integration/test_eval_runner_quality_gate.py
git diff --check -- \
  src/repo_harness/tools/minimal.py \
  src/repo_harness/workspace/adapter.py \
  src/repo_harness/workspace/docker_adapter.py \
  src/repo_harness/agent_loop/loop.py \
  src/repo_harness/pre_verl_agentloop.py \
  src/repo_harness/verifier/pytest_parser.py \
  src/repo_harness/evaluation/metrics.py \
  src/repo_harness/run_metadata/writer.py \
  src/repo_harness/reward/calculator.py \
  src/repo_harness/export/exporter.py \
  tests/unit/test_tools.py \
  tests/unit/test_agent_loop_protocol.py \
  tests/unit/test_pytest_parser.py \
  tests/unit/test_pre_verl_agentloop.py \
  tests/unit/test_run_metadata.py \
  tests/unit/test_reward.py \
  tests/unit/test_export.py \
  tests/integration/test_pre_verl_agentloop_runtime.py \
  tests/integration/test_eval_runner_quality_gate.py
```

然后再执行同一组五题 Docker targeted smoke。smoke 后必须检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index \
  RUN_DIR \
  --assert-all-formal-runs-bound \
  --assert-command-order \
  --assert-clean-source-origin \
  --assert-run-task-lineage \
  --assert-no-legacy-adapter
```

如果实现了新的归因一致性断言，也应加入：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index \
  RUN_DIR \
  --assert-run-metadata-attribution-consistent \
  --assert-metrics-timeout-consistent \
  --assert-invalid-reward-excluded
```

对每个 task run 继续执行模型可见上下文检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context \
  TASK_RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable \
  --assert-no-over-redaction
```

## 9. 正式二十三题评测前的放行标准

四项修复完成后，建议满足以下标准再进入正式二十三题：

1. `grep`：
   - 没有数分钟级宽搜索。
   - 每次 `grep` 都有真实 `duration_ms`。
   - partial search 不会被记录成可信 no-match。
2. pass-to-pass：
   - raw pytest summary 和 selector JSON summary 不再明显矛盾。
   - 解析置信度不足时使用 unknown 或 parse warning，而不是全部失败。
3. 失败归因：
   - timeout、max turns、final verifier 未执行在 boundary、metadata、metrics、reward 中一致。
   - invalid sample 不会以非零训练 reward 污染 RL export。
4. 收敛控制：
   - near-budget nudge 能在无补丁和已有补丁两类场景分别触发。
   - 模型仍失败时，run metadata 能明确显示是模型没有响应临近预算决策，而不是 Harness 没有提供收敛信号。
5. 审计检查：
   - boundary index 通过。
   - model visible context 检查通过。
   - 没有 hidden tests、gold patch、hidden selector 泄漏进入模型可见上下文。

如果上述标准全部满足，可以把下一轮 targeted smoke 作为正式二十三题前的最终健康检查。若 targeted smoke 中 accepted 数量没有提升，也仍然可以进入正式二十三题，但需要在结果说明中明确区分“模型错误修复”和“Harness 工具或归因问题已经修复”。
