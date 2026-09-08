**I01：miles 进程内 C 的反证与最小边界（2026-09-08）**

结论：Claude 提出的进程内复用方向成立，不能据此认定“接上两个 helper 就覆盖所有回放差异”，也没有证据要求正式训练前或长期必须选 C。需要分开决定：已发生动作及其实际条件的训练保真，以及下一次推理应保留哪些历史内容。后者是上下文策略。

范围固定为 `reference/miles-rh2-integration` 的 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。下述六个相关文件与公开上游 `bc1233ee2c6032a59fce7112135a3a33d27a91f6` 逐文件 `git diff --exit-code` 为零；本轮联网核了上游源码和 Qwen 官方模型卡。没有扩大到 session server 全审、训练性能或 run8 发生率。

**1．loose 的能力与反例**

【源码实证】`strict_message_matches` 比 `role/content/reasoning_content/tool_calls`，只在工具调用内去掉 `index`，之后用 Python 相等比较；它不是 token 相等比较。`loose_tool_call_message_matches` 先调用 strict，失败才进入工具参数 JSON 对象规范化；它仍比较非空 thinking、工具名、调用顺序、其余调用字段。参见 [funcs.py:21–102](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/utils/chat_template_utils/message_matcher_hub/funcs.py#L21)。

【CPU 实证】同一工具调用的局部匹配结果如下，T/F 分别为接受/拒绝：

| 回放变化 | strict | loose_tool_call | role_content_only |
|---|---|---|---|
| dict 参数只变键插入顺序 | T | T | T |
| JSON 字符串参数只变键序 | F | T | T |
| 等值 JSON 字符串 ↔ dict | F | T | T |
| 非空 `reasoning_content` → 缺失 | F | F | T |
| 工具名或实参值变化 | F | F | T |
| dict 参数 `{"value": true}` → `{"value": 1}` | T | T | T |
| JSON 字符串参数的同样 bool → number 变化 | F | F | T |
| JSON 重复键折叠，或数组元素换序 | F | F | T |

【源码实证】JSON 规范化本身会排序对象键、保留数组顺序、区分 boolean/number，并拒绝重复键和非标准数字；但它不是所有匹配的必经路径。见 [utils.py:65–160](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/utils/chat_template_utils/message_matcher_hub/utils.py#L65)。

【反例及边界】dict 中 `True == 1` 导致 strict 接受，loose 的早返回继承了这个结果，绕过带类型的 JSON 规范化。这说明“loose 保证工具参数 JSON 语义不变”过强。触发需要回放实际把 boolean 改成 number；本轮没有发现 CLI 或 run8 做过这种改写，不能报成已发生生产事故。若 C 依赖该判定覆盖回放前缀，应以这个用例验收类型边界，或明确允许的等价关系。

【RH2 源码实证】`rh2/src/slime/agent/adapters/anthropic.py:_translate_messages`（81–118）经 `common.py:tool_call_dict`（110–117）保留 `arguments` 为 dict，并去掉 wire ID。因此 run8 类 dict 键序问题在 strict 层本就能匹配；漂移发生于后续重渲染。loose 额外解决字符串 JSON 表示差异，不能把它说成 RH2 键序匹配的唯一修法。

【边界】`role_content_only` 明确忽略整个 `tool_calls`，不是“只容忍省略 thinking”的替代选项。探针中 `Edit` 改为 `Delete`、`new_string` 改值都被接受；它会让存储动作覆盖含不同工具语义的回放。内置 strict/loose 只把缺失、空串、空列表归为同类，不接受非空 thinking 被省略。见 [funcs.py:106–113](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/utils/chat_template_utils/message_matcher_hub/funcs.py#L106)。

**2．外层 loose 通过，不等于可直接 merge 原请求**

【源码实证】`TITOTokenizer.tokenize_additional_messages` 第 209 行调用 append-only validator 时不传 matcher，因此内部仍用 strict。追加部分的 token 来自两次合成前缀渲染的字符串差；`Qwen3TITOTokenizer.merge_tokens` 再复制原 token，并仅在末尾是 `<|im_end|>` 时补换行。它不重算整个真实历史，也不核验传入 token 是否真是该消息历史的实际生成记录。见 [tito_tokenizer.py:160–287](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/utils/chat_template_utils/tito_tokenizer.py#L160)。

【源码实证】上游 `LinearTrajectory.build_prompt_tokens` 先用所选 matcher 验证请求，然后构造 `effective_messages = self.messages + request_messages[len(self.messages):]`，再交给内部严格 merge。这样 loose 认可的旧消息表示差异不会再次进入 strict；不是把原请求直接传下去。见 [linear_trajectory.py:89–142](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/rollout/session/linear_trajectory.py#L89)。

【CPU 实证】JSON 字符串只换键序，外层 loose 为 T；直接 merge 回放原请求报 `message mismatch at index 2`。使用上游的 stored-prefix + tail 后成功，原 65 个 token 逐位保留。这个准备步骤属于 C 的最小接入，不能略去。

**3．原生 HF、fixed 模板、缺 thinking、compaction 是四件事**

【源码实证】构造 `Qwen3TITOTokenizer(tokenizer)` 只合入 `clear_thinking=False`；不会自动将 `tokenizer.chat_template` 换成 `qwen3_fixed.jinja`。上游的模板安装另由 `arguments.py:3008–3024` 和 `sessions.py:38–40` 完成；RH2 的 `repoharness2/adapters/slime/bringup.py:861` 当前只调用 `load_tokenizer(args.hf_checkpoint, trust_remote_code=True)`。因此“使用哪个模板”必须核到实际 tokenizer 对象。

【源码实证】Qwen 原生模板不读取 `clear_thinking`；它按最后一个普通 user 消息的位置决定是否输出旧 assistant thinking。miles fixed 第 43 行加入 `not clear_thinking` 条件。对追加独立 user reminder，全量原生渲染会去掉此前 thinking，全量 fixed + False 会保留。见 [fixed 模板](https://github.com/radixark/miles/blob/bc1233ee2c6032a59fce7112135a3a33d27a91f6/miles/utils/chat_template_utils/templates/qwen3_fixed.jinja#L43)。

【CPU 实证】使用本机缓存的 `Qwen/Qwen3-30B-A3B` tokenizer，revision=`ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`；Python 及 transformers 版本、源文件 hash、输入和原始输出均在结果文件。合成输出采用紧凑 JSON，再以真实 tokenizer 编码，没有调用模型。

| 场景 | 全量渲染 / 增量 merge 的实际结果 |
|---|---|
| 原生模板传 `clear_thinking=False` | 与不传该参数的全文完全相等，参数未改变行为 |
| 消息保留 thinking，新增独立 user reminder | 原生全文不含 `TRACE_THINK`；fixed 全文包含 |
| 相同 reminder 走原生或 fixed 的 TITO | 两者都保留全部 65 个旧 token，补 token `198` 换行，总计 96 个 token |
| dict 键序改写 | 原生全量 render 的 token 改变；TITO merge 保留旧 prefix |
| 合成“客户端省略非空 thinking” | strict/loose 拒绝；fixed 本身不能从缺失字段恢复内容 |
| 合成 compaction：三条历史变为 system + summary 两条 | 内部严格 merge 拒绝；需要另起实际 prompt 的分段路径 |

【更正自己的预判】首跑预期“原生 TITO + reminder 必须 suffix-diff 失败”被反证。其 dummy 前缀没有 user，原生模板默认 `last_query_index` 就是末个 assistant 下标，故 dummy assistant 从一开始就未渲染 thinking；追加 reminder 后字符串前缀仍成立。结果保存了两次 dummy 全文。不能据全量渲染删 think，推断这里 fixed 是必要条件；也不能据这个局部成功推断原生与 fixed 对所有追加角色等价。

【区分】模板删 thinking 是 renderer 的既定上下文政策；客户端省略字段是回放信息减少；compaction 是历史被摘要/替换。它们都可能造成不匹配，但应分别记因。把前两者都计成“真正 compaction”，或称 loose 自动容忍省略 thinking，都不准确。此处省略与 compaction 均为合成输入，未证明当前 CLI 会这样发请求。

**4．C 可以缩小；“保真 ⇒ 必须长期保留所有 thinking”不成立**

【官方声明】Qwen 模型卡 Best Practices 第 4 项建议多轮历史只保留最终输出，旧 thinking 不必放入历史，并说明模板实现了这一策略。它不是 RL 数据导出的规定，但足以反证“保留全部旧 thinking 必然更符合该模型的使用方式”。见 [固定版本模型卡](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39/README.md#best-practices)。

【推论】对已采样动作 `a_t`，保真要求训练时使用当时实际的 `P_t` 和原始 `a_t`。这并不强迫下一步 `P_(t+1)` 永远包含全部 `a_t`；下一步可以采用删 thinking 或摘要后的上下文，只要各动作按其各自实际条件保存和训练。GRPO 使用最终结果奖励，也不能把这个时间差别抹掉。B 的精确分段可以满足该要求，C 则另外改变未来上下文及其成本。

【最小候选边界，非替 owner 定案】可以先只支持已固定 tokenizer/模板/工具定义、已验证追加角色、消息仅有受控表示差异的路径，复用上游 matcher 与 Qwen merge；遇到既定模板要删 thinking、历史改写或无法证明等价的情况，回到原始请求渲染 + 保留旧动作的分段路径。这样可先消除工具参数重排，不要求同时批准“永远保留 thinking”。若选择较宽的 C，应明确它对 reminder 的旧 thinking 保留策略。

【必须明确的接入责任】checkpoint 必须绑定同一次实际成功请求的完整 `P+a`、消息和调用身份，不能只缓存 SID 的最后一段 token；重试、并发调用与分支时不能把别轮前缀误接。匹配条件还需覆盖影响渲染的工具定义/模板参数；只比较 messages 不能证明这些条件没变。失配后旧动作仍需保存在训练分段中。上述是接口责任，不构成要求重造持久 session server 的理由。

【缺 thinking 的选项】保留 strict/loose 的拒绝并分段，是现成可解释的边界。若 owner 允许“只省略 thinking 仍复用存储前缀”，需独立窄匹配器、保留工具字段检查、计数和实际 wire 证据；不能换成 `role_content_only`。它不是仅改日志，而是让下一次推理重新看到客户端未回传的内容，属 T0 上下文政策。

【分期判断】正式训练前必须解决的是静默丢训练动作、实际条件不一致和无法核对的身份连接；不能把某个名为 C 的实现本身当闸门。如果 B 经真实路径验证可保留动作且成本可接受，暂留或长期保留 B 都有逻辑空间。C 的优先级应由真实漂移、训练成本、上下文效果和接入复杂度决定，本报告不估算性能，也不代 owner 选定。

**证据与停止点**

原样产物：[CPU 探针](miles_c_probe.py)、[输入、结果及 hash](miles_c_probe_result.json)。执行命令为 `rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/miles_c_probe.py`，最终退出码 0。首次错误预期及其被反证原因保留在结果中；产品代码没有变化。

matcher 两个依赖简单的源码模块完整执行；Qwen tokenizer 类及相关渲染函数通过 AST 原样提取，真实 HF tokenizer 执行编码。仅隔离非 Qwen 分支，并限定 `tools=None`，未运行 SGLang 工具 schema 校验。已完成 10 组匹配和 8 个 merge 场景的有界验证，到此停止；没有 CLI 端到端、run8 新渲染器回放、采样、训练或完整测试的成功声明。
