# Brief：#5 采样输出的 EOS 字面量与悬空 `<tool_call>`——窄修（T1）

2026-09-24 / Claude（A 线）。**状态：已实施；Codex 聚焦复核（[review_next_slices §1](../batch6_efficiency_20260921/review_next_slices_20260924/README.md)）的 R1/R2 两项 P2 已于 2026-09-25 修订（§6），待针对性复核。** 依据：[交接包 #5](../base_model_probe_20260922_aline_handoff.md)、[第六组 README §8.1 第 2 条](../batch6_efficiency_20260921/README.md)（Codex：先说明挂接点与输出范围；只去除真实终止 token 在可见末尾的表现；采样 ID / logprob / mask / capture 原样；悬空调用只修 `ill_formed` 事实；不新增拒样、不改 reward）。

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

## 6. Codex 聚焦复核（2026-09-25）

状态：**已实施，R1/R2 两项 P2 待修**。详见[复核报告 §1](../batch6_efficiency_20260921/review_next_slices_20260924/README.md)。

- R1：普通 token 也能拼出末尾 `<|im_end|>`。真实 tokenizer / adapter HTTP 探针在没有 EOS ID、finish 为 length 时复现正文被误删；应在已有采样事实的边界确认末尾 EOS，再裁剪解析视图。原始训练 token 不变不代表 CC 所见与回放历史不变。
- R2：正常正文提及 `<tool_call>` 会误报；完整工具调用后另有悬空片段又会漏报。收窄为明确坏调用的事实识别，不新增拒样或 reward 规则。
- 维护测试正控通过；补上述反例与既有正控即可收口，无需重跑完整启动链或 GPU。

## 6. Codex R1/R2 修订（2026-09-25）

- **R1（可见字面量 ≠ 真实 EOS token）**：原实现只看 `raw.rstrip().endswith(eos)`，Codex 探针用真实 tokenizer 证明普通 token 能拼出 `The token is <|im_end|>`（全序列无 EOS id、finish=length）却被剥掉。修法：剥字面量只认**采样事实**——产出 `TurnRecord` 的一方在 `_run_turn` 的任务上下文里发布 `publish_turn_terminal(output_ids, finish)`（最后一个采样 id 是否等于服务 tokenizer 的 `eos_token_id`），解析时取走并清空（一次性）。生产由 capture wire 的 `rh2_call_sglang_generate` 在返回 TurnRecord 前发布；没装 capture wire 的部署（探针）用 `install_turn_terminal_publisher()` 包一层当前 `call_sglang_generate`。没有事实 → 不剥并计 `eos_fact_missing`（fail-closed）；最后一个 id 不是 EOS → 保留并计 `eos_literal_kept`。`install_parse_wire(eos_token=…, eos_token_id=…)` 取 tokenizer 同一对值；bringup 生产构造点与正式链夹具都已传 id。vendored 仍零改动。
- **R2（`ill_formed` 误报 / 漏报）**：判据改为只看**解析后的可见残余** `parsed.text`：最后一个 `<tool_call>` 之后没有 `</tool_call>`，且其后为空或以已支持语法开头（XML `<function=` / JSON `{`）→ 悬空；正文提到标签后跟普通文字不算；已解析出有效调用不掩盖其后的悬空片段。解析器若吞掉片段（可见残余无标签），对去掉 `</think>` 之前 reasoning 的原文尾部用同一规则。**覆盖范围**就是这两种形态（空续接 / XML 或 JSON 片段续接），不宣称完整坏调用检测；仍只改事实，不拒样、不改 reward。
- **验收**（`test_parse_wire.py` 14 例）：真实 EOS 正控剥除且工具调用不变；普通 token 拼出的字面量保留（计数 `eos_literal_kept`）；无事实不剥（`eos_fact_missing`）；正文中间字面量只剥末尾一个；事实一次性不串轮；未配 id 不剥；正文提到标签不误报；完整调用 + 悬空片段 → `ill_formed=True` 且调用保留；单独悬空 / XML 片段 / JSON 片段三形态；挂接点（原函数同时含 `parse_model_output(` 与 `call_sglang_generate(`）；发布器包装幂等且事实在同一任务里被解析取走。
- **B 接线**：[交接 §2](b_wiring_handoff_20260924.md) 的示例已改为传 `eos_token_id` 并装发布器。

