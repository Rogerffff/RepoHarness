# S0-4 V2 报告：renderers 库对 Qwen3-30B-A3B 的覆盖核实

日期：2026-07-07。对应执行计划 `../01-s0-execution-plan.md` 的 S0-4 节。被核实对象：`reference/renderers`（本地 HEAD `5904fa2`，只读，未做任何修改）。目标模型：`Qwen/Qwen3-30B-A3B`（训练目标，MoE，总参 30B / 激活 3B）。

## 0. 判定结论

**V2 通过。**

| 判定项 | 结果 |
| --- | --- |
| hand-coded renderer 覆盖 30B-A3B | 通过：`MODEL_RENDERER_MAP` 精确注册 `"Qwen/Qwen3-30B-A3B": "qwen3"` → `Qwen3Renderer`（非 DefaultRenderer） |
| 渲染一致性（renderer vs `apply_chat_template`） | 通过：12/12 用例逐 token 一致（用真实 30B-A3B tokenizer，transformers 5.13.0） |
| `bridge_to_next_turn` 可用 | 通过：12/12 检查，含两轮链式 bridge 前缀保持、与全量重渲染逐 token 相等、截断合成 close |
| thinking 剥离策略对 token 保真的影响（U-E） | 已量化：工具循环内零影响；仅当出现**第二个 user query** 时 bridge 主动回退全量重渲染（fail-closed，不产生静默漂移）。对 rh2 的 SWE 单任务 episode 形态影响≈0，详见第 4 节 |

一句话版本：30B-A3B 走的就是 dense Qwen3 同一条 hand-coded renderer 路径（tokenizer、chat template 与 Qwen3-8B 逐字节一致，实测验证），渲染保真和 bridge 语义全部实测通过，无需降级到 DefaultRenderer。

---

## 1. 静态核实（源码走读）

### 1.1 (a) 注册方式与模型匹配规则

- 注册表是**精确字符串匹配**，不是前缀匹配：`renderers/base.py:988` 起的 `MODEL_RENDERER_MAP`。注释（base.py:980-987）明确说明：同架构模型可能带不同 chat template，前缀匹配会静默路由错误，所以改名/微调后的 checkpoint 必须显式传 renderer 配置，否则 auto 路径回落 `DefaultRenderer` 并只打一条 INFO 日志。
- 30B-A3B 系列条目（实测读取）：

```python
"Qwen/Qwen3-30B-A3B": "qwen3",                  # base.py:998，本次训练目标
"Qwen/Qwen3-30B-A3B-Instruct-2507": "qwen3",
"Qwen/Qwen3-30B-A3B-Thinking-2507": "qwen3",
# dense 系列 0.6B/1.7B/4B/8B/14B/32B 和 235B-A22B 也全部 → "qwen3"
```

- 解析链路：`create_renderer_pool(model_id)` / `create_renderer(tokenizer)`（base.py:1341/1379）→ `AutoRendererConfig` 用 `tokenizer.name_or_path` 查 `MODEL_RENDERER_MAP`（base.py:1478-1479）→ `RENDERER_REGISTRY["qwen3"] = Qwen3Renderer`（base.py:1319）。
- 公开 API 入口（S0-5 会用到）：`pool.render_ids(...)` / `pool.render(...)` / `pool.parse_response(...)` / `pool.bridge_to_next_turn(...)`；`renderers/client.py` 的 `generate(...)` 走 `messages → render_ids → POST /inference/v1/generate`（client.py:1-3, 144）。
- tokenizer 加载策略：`load_tokenizer`（base.py:1266）默认 `trust_remote_code=False`；Qwen3 家族不在 `TRUSTED_REVISIONS` 白名单里也能正常加载（无 custom tokenizer 代码）。

### 1.2 (b) tool call 渲染格式

hermes 风格 JSON（qwen3.py:31-45 的 `_TOOLS_HEADER/_TOOLS_FOOTER`，qwen3.py:490-521 的 assistant tool_calls 渲染）：

- 工具声明：注入进 system 块 `<tools>` 标签内，每个工具一行 `json.dumps(tool, ensure_ascii=False)`（传什么 dict 就 dump 什么，与 HF 模板的 `tool | tojson` 逐字节一致；OpenAI wrapper 形态 `{"type":"function","function":{...}}` 原样透传）。
- 模型输出的调用：`<tool_call>\n{"name": "bash", "arguments": {...}}\n</tool_call>`，`<tool_call>`/`</tool_call>` 是真特殊 token（id 层 emit，防止正文同形文本误判；解析同理走 token id 层，qwen3.py:281-294 → `parsing.parse_qwen3`）。
- 工具返回：渲染为 **user 角色块**内的 `<tool_response>\n正文\n</tool_response>`（qwen3.py:530-574）；连续多条 tool 消息合并进同一个 `<|im_start|>user` 块（`prev_is_tool/next_is_tool`，qwen3.py:547-550）——并行工具调用场景实测通过（见 2.2 表）。
- 归因信号：工具返回正文 `is_content=True` / 包裹 `False`；assistant 采样区（含 `<tool_call>` 块和 `<|im_end|>`）`sampled_mask=True`，role tag 和轮间 `\n` 为 `False`（qwen3.py:457-528 注释与实现）。这正是 rh2 训练侧要的 loss mask 原料。

### 1.3 (c) thinking（`<think>`）在历史消息里的处理策略

`_render_assistant`（qwen3.py:445-488）复刻官方 Qwen3 Jinja 模板语义：

1. reasoning 来源两条路：显式 `reasoning_content` 字段，或从 `content` 里切 `<think>…</think>`（两种形态实测渲染结果逐 token 相同）。
2. **保留窗口**：`emit_in_template_window = msg_idx > last_query_index and (is_last or reasoning_content)`。翻译成话：只有**最后一个真实 user query 之后**的 assistant 消息才保留 `<think>` 块；更早的历史 assistant 消息一律剥离 thinking、只留正文。
3. `last_query_index`（qwen3.py:98-113）認定"真实 user query"时排除首尾被 `<tool_response>...</tool_response>` 包住的伪 user 消息——所以**工具循环不推进 query 边界**，同一任务内所有 assistant thinking 都在保留窗口内。
4. 生成提示：`enable_thinking=True`（`Qwen3RendererConfig` 默认，configs.py:178）时生成提示就是 `<|im_start|>assistant\n`，模型自己接着吐 `<think>`；`enable_thinking=False` 时强制附加空块 `<think>\n\n</think>\n\n`（qwen3.py:250-257）。

### 1.4 (d) `bridge_to_next_turn` 实现与前缀保持逻辑

已实现（qwen3.py:299-431），核心步骤：

1. 防御闸：空输入 → None；`new_messages` 含 assistant → None（拒绝重新 tokenize 模型采样内容，base.py:1847）；`should_rerender_for_thinking_retention` 命中 → None（见下）。
2. `trim_to_turn_close`（base.py:1705）在 `previous_completion_ids` 里从后往前找 `{<|im_end|>, <|endoftext|>}`；找不到（max_tokens 截断）就**合成** canonical close `<|im_end|>`（作为非 loss 的 prompt 上下文，`sampled_mask=False`）。
3. 之后只追加：轮间 `\n`（vLLM 在 `<|im_end|>` 停止，这个 `\n` 不会出现在 completion 里，qwen3.py:382-385 注释）+ 新 tool/user/system 消息 + 下一轮 `<|im_start|>assistant\n`。
4. 前缀契约：`B.token_ids[:len(P+C)] == P + C`（干净停止时逐 token 成立，截断时成立到截断点+合成 close）。实测两轮链式 bridge 均逐 token 保持，且与全量重渲染完全相等（见 2.3）。

thinking retention 与 bridge 的联动（base.py:1875-1902，qwen3.py:58-61）：`enable_thinking=True` 派生 `effective_thinking_retention="tool_cycle"` —— `new_messages` 引入新的真实 user query 时 bridge 返回 None、调用方回退全量重渲染（重渲染会按 1.3 的窗口规则剥离历史 thinking）。这个设计让 bridge 的输出永远与全量渲染语义一致：**要么逐 token 等价延长，要么显式拒绝**，不存在"bridge 保留了 thinking 而模板剥离了"的静默分叉。`enable_thinking=False` 时派生 `"all"`，跨 user query 也允许 bridge（此时历史里本来就没有实质 thinking）。

### 1.5 (e) 30B-A3B（MoE）与 dense Qwen3 是否共用同一 renderer 路径

- 共用。注册表里 MoE（30B-A3B、235B-A22B）与 dense 全部映射到 `"qwen3"`；renderer 只消费 tokenizer + chat template，MoE/dense 差异在权重结构层，与渲染无关。
- 实测补强：30B-A3B 与 Qwen3-8B（renderers CI 矩阵里 qwen3 的代表机型，tests/conftest.py:22）的 chat template **sha256 完全一致**（前 16 位 `a55ee1b1660128b7`）、vocab 完全一致（151669 词条）、同一 fixture 渲染逐 token 一致。
- 一个此前未知的缺口被本实验补上：renderers 自己的 CI 矩阵**没有直接跑 30B-A3B**（只用 8B 代表 qwen3 家族）；本报告的 12+12 项实测等于把 30B-A3B 的直接验证做完了。

---

## 2. 实测记录

### 2.1 环境与素材

- 运行环境：`cd rh2 && uv run python experiments/s0_renderer/v2_renderer_experiment.py`。Python 3.12.13，transformers 5.13.0，huggingface_hub 1.22.0——**全部已在 rh2 现有锁文件里**（verifiers 传递依赖带入），计划里预留的 `uv add --group dev transformers huggingface_hub` 实际不需要，pyproject/uv.lock 零改动。renderers 以 `sys.path` 方式从 `reference/renderers` 导入（只读）。
- tokenizer 下载：`Qwen/Qwen3-30B-A3B` revision `ad44e777`，仅 5 个配置文件共约 15.9 MB（tokenizer.json 11.42 MB + vocab.json 2.78 MB + merges.txt 1.67 MB + 两个小 json）；对照组 `Qwen/Qwen3-8B` revision `b968826d` 同规模。直连 huggingface.co 成功，未用镜像，未下载任何权重。加载得到 `Qwen2Tokenizer`（transformers 5.x 命名，fast 后端，`return_offsets_mapping` 可用——`attribute_text_segments` 的硬性要求满足）。
- 对话素材：SWE agent 形态的 7 消息对话（system + user 任务 + 3 个带 reasoning 的 assistant 轮 + 2 个 tool 结果，工具为 bash/read_file），另有并行工具调用、含 `<tool_call>` 同形文本/unicode/diff 的工具输出、第二个 user query 等变体。工具 schema 与 tool_calls 采用 OpenAI wrapper 形态（与 renderers 自测 fixture 同构）。

### 2.2 渲染一致性（`render_ids` vs `apply_chat_template`，逐 token 比较）

12/12 通过，两边 token 序列完全相等（`first_diff = -1`）：

| 用例 | token 数 | 说明 |
| --- | --- | --- |
| basic_system_user_assistant | 27 | 冒烟 |
| swe_full_7msgs_reasoning_field | 390 | 全对话，reasoning 走字段 |
| swe_full_7msgs_inline_think | 390 | 同上，reasoning 内联 `<think>` 进 content（两形态等价） |
| gen_prompt_enable_thinking_true | 244 | 首轮 prompt + 生成提示（默认 thinking 开） |
| gen_prompt_enable_thinking_false | 248 | 同上，强制空 `<think>\n\n</think>\n\n`（多 4 token） |
| full_render_enable_thinking_false | 390 | nothink 配置全量渲染 |
| mid_rollout_prompt_4msgs / 6msgs | 309 / 368 | 工具循环中段的下一轮 prompt |
| second_user_query_strips_history_think | 395 | 9 消息、双 query：历史 thinking 两边一致剥离 |
| second_user_query_prompt | 359 | 双 query 下一轮 prompt |
| parallel_tool_calls_consecutive_tool_msgs | 313 | 并行 2 个 tool_call + 连续 2 条 tool 消息合并 |
| tool_output_with_special_lookalikes | 324 | 工具输出含字面 `'<tool_call>'`、unicode、git diff |

### 2.3 bridge 语义（12/12 通过）

模拟真实采样流：completion 从 canonical 全量渲染切出、以 `<|im_end|>`(151645) 结尾、不含轮间 `\n`（等价 vLLM 停止行为）。

| 检查 | 结果 |
| --- | --- |
| 第 1 轮 bridge 前缀保持 | prompt(244)+completion(48)=292 token 逐 token 保留，bridge 总长 309 |
| 第 1 轮 bridge == 全量重渲染 | 309 == 309，`first_diff = -1` |
| 第 2 轮链式 bridge 前缀保持 | 353 token 前缀保留，总长 368；且仍以第 1 轮 tape(292) 为前缀 |
| 第 2 轮 bridge == 全量重渲染 | 逐 token 相等 |
| completion 解析回结构化消息 | `parse_response` 还原 tool=bash、参数、reasoning_content，status=ok |
| 新 user query → 回退 | 返回 None（tool_cycle 策略，符合设计） |
| 扩展消息含 assistant → 拒绝 | 返回 None |
| 截断 completion（去掉尾部 3 token） | 前缀保留 + 紧跟合成的 `<|im_end|>`(151645) |
| 并行 tool 消息作为扩展 | bridge == 全量重渲染，合并进同一 user 块 |
| `enable_thinking=False` 派生 retention | `"all"`（跨 query 可 bridge） |

### 2.4 MoE vs dense 同一性

chat template sha256 前 16 位均为 `a55ee1b1660128b7`；vocab 151669 逐项相等；同一 fixture 两 tokenizer 渲染逐 token 一致。结论：30B-A3B 在渲染层就是 dense Qwen3 的同一路径，CI 用 8B 代表 qwen3 家族对 30B-A3B 是有效代表（本实验又做了直接验证双保险）。

---

## 3. U-E 评估：thinking 剥离策略对 token 保真的影响

### 3.1 量化实测

在 7 消息对话第 3 轮结束后（真实 tape = 389 token），注入第二个 user query 并全量重渲染下一轮 prompt（359 token）：

```text
公共前缀长度 = 244  （恰好等于第 1 轮生成提示的长度）
tape 中 244 之后的 145 个 token 全部不再是新 prompt 的前缀
分歧点 tape 侧解码 = '<think>\nI need to create the file...'（第 1 个采样 token 就是分歧点）
重渲染结果与 HF apply_chat_template 仍逐 token 一致（剥离行为两边同步）
```

也就是说：一旦出现新 user query，从**第一个 assistant 轮的第一个采样 token 起**整段历史都会因 thinking 剥离而偏离原 tape——不是只丢 thinking 那几段，而是前缀性质整体失效（thinking 被抽走后所有后续 token 位置全部前移）。

### 3.2 对 rh2 训练链路的影响判断

- **工具循环内（SWE episode 的正常形态）零影响**：rh2 的 taskset 是"开局一条任务描述，之后全是 assistant↔tool 循环"，`<tool_response>` 包裹的伪 user 消息不推进 query 边界，整个 episode 处在同一保留窗口，bridge 全程可用且与全量渲染逐 token 等价。每轮的 (prompt_ids, completion_ids) 训练对 token 保真成立。
- **query 边界是显式失效而非静默污染**：bridge 返回 None 逼调用方重渲染，重渲染又与 HF 模板一致。风险形态是"多轮人机对话式"任务（mid-episode 注入新 user 指令），那时 trajectory 会断成多段独立 tape：每段内部保真，但跨段不能拼成单一 token tape，前缀缓存也会 miss。rh2 若未来在 episode 中途注入 user 角色的引导消息，要么接受重渲染断点，要么把注入消息包成 `<tool_response>` 形态/改用 system 角色（system 不触发 query 边界，bridge 路径实测支持 system 扩展）。
- **留给 S0-5 的动态观察项**（对应计划"S0-4 静态核实 + S0-5 动态观察"）：真实 vLLM 采样下 completion 是否如假设含 `<|im_end|>` 尾 token；verifiers TrainClient 在 bridge 返回 None 时的回退行为是否正确；截断（length 停止）路径合成 close 后 logprobs 对位是否符合预期。

---

## 4. 新发现的未知 / 风险（进 implementation-notes）

1. **U-G（新增）：本地路径加载会静默降级 DefaultRenderer。**`AutoRendererConfig` 用 `tokenizer.name_or_path` 精确匹配注册表（base.py:1478）。GPU 机上如果用本地权重目录加载（如 `create_renderer_pool("/models/Qwen3-30B-A3B")`），`name_or_path` 是路径字符串、注册表不命中 → 回落 DefaultRenderer，**只打 INFO 日志**——bridge 永远 None、`sampled_mask/is_content` 为空，token 保真训练目标全部失效。规避：S0-5 起所有脚本要么用 HF id 加载 tokenizer，要么显式传 `Qwen3RendererConfig()`，并在启动时断言 `type(renderer).__name__ == "Qwen3Renderer"`（一行代码的守门检查）。
2. renderers CI 矩阵未直测 30B-A3B（用 8B 代表）：已由本实验补齐直接证据，后续升级 renderers 版本时需重跑 `rh2/experiments/s0_renderer/v2_renderer_experiment.py` 回归（tokenizer 已缓存，重跑不到 1 分钟）。
3. transformers 5.13.0（rh2 锁定版本）与 renderers（pyproject 要求 `>=4.50.0`）的 parity 在 5.13 实测成立；GPU 机若因 vLLM 0.24.x 约束换 transformers 版本，parity 需随 S0-5 一并复验。

## 5. 复现与 evidence 指针

```text
实验脚本  rh2/experiments/s0_renderer/v2_renderer_experiment.py   （验证级，24 项断言，exit code 即结论）
          rh2/experiments/s0_renderer/v2_evidence_extras.py       （tokenizer 快照信息 + 分歧点解码）
机读结果  rh2/experiments/s0_renderer/v2_results.json
运行方式  cd rh2 && uv run python experiments/s0_renderer/v2_renderer_experiment.py
依赖说明  零新增依赖（transformers/hf_hub 已在 uv.lock）；renderers 经 sys.path 引用 reference/renderers（HEAD 5904fa2，未修改）
```
