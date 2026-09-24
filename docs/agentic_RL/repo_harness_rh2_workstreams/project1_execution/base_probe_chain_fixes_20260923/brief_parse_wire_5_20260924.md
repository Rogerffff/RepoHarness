# Brief：#5 采样输出的 EOS 字面量与悬空 `<tool_call>`——窄修（T1）

2026-09-24 / Claude（A 线）。**状态：已实施，本地回归通过，待 Codex 聚焦复核。** 依据：[交接包 #5](../base_model_probe_20260922_aline_handoff.md)、[第六组 README §8.1 第 2 条](../batch6_efficiency_20260921/README.md)（Codex：先说明挂接点与输出范围；只去除真实终止 token 在可见末尾的表现；采样 ID / logprob / mask / capture 原样；悬空调用只修 `ill_formed` 事实；不新增拒样、不改 reward）。

## 1. 挂接点

- vendored `slime.agent.adapters.common.BaseAdapter._run_turn` 按**模块全局名**调用 `parse_model_output(raw_text, tools_schema=…, tool_parser_name=…, reasoning_parser_name=…)`（`common.py` 第 26 行 import、第 347 行调用）。替换模块属性 `slime_common.parse_model_output` 即生效，与 capture wire、turn 预算 wire 同机制，vendored 零改动。
- 新模块 `rh2/src/repoharness2/adapters/slime/parse_wire.py`：`install_parse_wire(*, eos_token)` 保存原函数并替换；`assert_parse_wire_installed()` 在生产构造点核对；`parse_wire_stats()` 给出 `eos_stripped` / `dangling_tool_call` 计数。生产安装点：`bringup.py` 唯一生产构造点，在 `install_count_tokens_wire()` 之后、构造 adapter 之前，`eos_token = tokenizer.eos_token`。
- Anthropic 的 reply 构造只收到 parsed output / finish，收不到采样 ID；wire 作用在文本解析这一层，**根本拿不到** `output_ids`、logprob、mask 与 capture 记录——它们原样。

## 2. 输出范围（只做两件事）

1. `raw` 的**可见末尾**恰好是一个 EOS 字面量（如 `<|im_end|>`）时去掉这一个；正文中间的同名字面量、连续多个末尾字面量的前几个都不动（"只去除真实终止 token 在可见末尾的表现"）。
2. 去掉末尾后 `raw` 含 `<tool_call>` 而解析结果没有任何 `tool_uses` → 只把 `ill_formed=True`；`text` / `tool_uses` / `finish` 不改，不拒样，不改 reward，不纠正模型动作。

不做：不全局替换、不改 sglang 解析器选择、不处理 `<think>`、不新增 finish 语义。

## 3. 验收（`rh2/tests/adapters/test_parse_wire.py`，7 例）

反例文本取自 B 线探针留证（coder_adapter `dask-8597-a2` turns.jsonl 的工具轮/末轮、q36 纯文本末轮）的真实形状：

| 用例 | 输入 | 断言 |
| --- | --- | --- |
| 工具调用轮 | 文本 + `<tool_call>…</tool_call>` + EOS | 解析出 Bash 调用、参数原样；`eos_stripped` +1 |
| 悬空调用 | 总结文本 + `<tool_call>` + EOS | `ill_formed=True`，无 tool_uses，文本保留；`dangling_tool_call` +1 |
| 纯文本末轮 | 文本 + EOS | 文本不含 EOS，`ill_formed=False` |
| 正文含字面量 | `… <\|im_end\|> …` + EOS | 只去末尾一个，中间的保留 |
| 无 EOS | 文本 | 原样，计数不变 |
| 未安装即用 | — | `assert_parse_wire_installed()` 抛错 |
| 挂接点 | — | vendored 原函数（`_rh2_original_run_turn` 或类方法）源码里含 `parse_model_output(`，且模块属性已是 `rh2_parse_model_output` |

全量套件里 turn 预算 wire 会把 `BaseAdapter._run_turn` 换成 `rh2_run_turn`（原函数留在 `_rh2_original_run_turn`），挂接点用例据此断言 vendored 原函数而不是当前包装——首轮全量跑因此失败 1 例，已修（只改测试）。

## 4. 回归

- 五目录（`tests/contracts tests/adapters tests/governance tests/grading tests/envpack`，本机 Docker 在线）：**1748 passed / 1 skipped**；双 lane：A 463p/343s、B 806p/0s，全部精确计数通过；ruff 通过。
- 首轮全量 1746 passed / 1 failed（§3 的挂接点用例受 turn 预算 wire 影响），只改测试后 `tests/adapters` 775 passed，再全量为上行数字。计数含 B 线同工作区未提交的新增测试，不是本片新增量。

## 5. 边界

- 只对文本层生效；训练行的 token 仍含 EOS（采样 id 原样），与 #4/I01 无关。
- `ill_formed` 目前只是事实字段，消费者（是否拒样、如何计 reward）是另外的决定；本片不改。
