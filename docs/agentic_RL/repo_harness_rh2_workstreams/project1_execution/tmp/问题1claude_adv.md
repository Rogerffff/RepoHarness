清单读完，问题一的原始证据也重新核过。先说清单，再进问题一。

对清单本身
整体公允，纠正了我上一轮的过度概括，也没有把已知前置和新回归混在一起。两处补充：

I01 缺了最关键的输入：上游 miles 已经有进程内可用的 TITO tokenizer，不需要起 session server。miles/utils/chat_template_utils/tito_tokenizer.py 的 Qwen3TITOTokenizer.merge_tokens 只渲染新追加的消息，把上一轮引擎实际看到的 token 当不可变前缀，并处理 <|im_end|> 后换行的边界；配套 message_matcher_hub/funcs.py 有 strict、loose_tool_call、role_content_only 三种匹配器，其中 loose 会把工具参数按 JSON 对象规范化后再比，正好解决 run8 那种键顺序漂移。设计建议要求"修 REALIGN 前先核能否窄接入上游机制"，答案是能，而且是纯库函数。
I01 的发生率我补了一个数。run8 唯一保留的那条样本有 6 轮，我对全部 5 个轮边界做了 token 前缀比对：只有 t0 到 t1 漂移，落在 Edit 工具参数的键顺序上；t1 到 t5 四个边界全是精确前缀，CLEAN。所以漂移是工具相关的，不是每轮都有。这同时纠正我之前"最坏每轮都丢"的推断，也说明"60/60 缺 t0"里 t0 是不是都因 REALIGN 丢的仍未证。
问题一：已核实的事实
每轮请求把 Claude Code 回放的完整历史重新渲染、重新 tokenize。历史 assistant 轮的 token 不是引擎生成的那份，而是翻译后再过模板的那份。
只要重渲染在上一轮响应区间内分叉、且本轮输出短于 1024 token，上一轮整段响应被覆盖成 mask 0。rewrite-merge 是第二条销毁路径，条件是旧输出短于 1024。
漂移来源已见两种：Claude Code 回传 tool_use 时改写了参数键顺序，run8 样本里 replace_all 从末位跑到首位；独立 user 文本块让模板剥掉之前的 thinking，Codex 探针复现。前者不可能靠模板参数消除，因为是 harness 侧改写。
全链没有 generated、trained、dropped 的逐轮计数，eligibility 只要求可训 token 大于 0。
决策包
要决定什么：训练样本里"历史 token 以谁为准"。今天是"以 harness 回放的重渲染为准，对不上就把旧动作删掉"。

方案	做法	改动	训练语义	代价
A 只计数	加逐轮 generated/trained/dropped 与 fork 计数，进事件	约 40 行，rh2 侧	不变，仍丢动作	只能作为过渡测量
B 漂移即 FORK	构造 adapter 时传 fork_threshold_tokens=0，REALIGN 与 rewrite-merge 同时关闭	1 行，不碰 vendored 字节	不再静默丢任何动作；漂移轮成为独立叶，共享前缀在其它叶上以 mask 0 重放	每次漂移多一片带全量 prompt 的样本，训练侧 forward 重复；25 轮里有 k 次漂移就约 k+1 倍前缀计算。这就是 Polar 与 Agent Lightning 的"精确前缀才合并、否则新开一行"
C 引擎 token 为准	rh2 侧替换 _render_token_ids：按 sid 维护若干检查点，每个检查点是一段消息历史加引擎实际看到的 token；新请求用 loose 匹配器找最长匹配检查点，前缀直接复用，只渲染追加的消息；匹配不上才全量渲染并 FORK。复用上游 Qwen3TITOTokenizer 与匹配器	约 150 到 250 行加测试，和 capture_wire 同样的 monkeypatch 方式	重渲染漂移从源头消失，一条轨迹仍是一条样本；真正的历史改写如 compaction 才分叉	模型上下文改为"自己生成过的 token 加新增消息"，与 vendor 模板在有 system-reminder 时的剥 thinking 行为不同；B 的基座诊断要用同一 adapter 才可比
D 接上游 session server	走 miles 形态乙	大	与 C 同	8 月 25 日已因三条 fail-closed 理由否决，C 在进程内得到同样语义，不需要重开
推荐：先 A 加 B 一起落，作为不再丢动作的地板；C 作为首个正式训练前的修法。理由：B 一行就把静默损失变成可见的训练成本；C 是上游对同一问题的标准解法，并且让 I18 的路由来源问题也有了按轮拼接的自然落点。不建议长期停在 B，漂移次数多的轨迹会把训练侧算力放大数倍。

长期代价：C 让模型看到的历史保留早期 thinking，这与 Qwen3 官方模板在多次 user 文本块时的行为不同，但与引擎实际采样时的上下文一致，这正是 RL 需要的一致性。C 依赖 miles fork 里的 tokenizer 与匹配器，属于对已选后端的正常依赖。

以后还能改什么：匹配器的宽松度、是否容忍回放省略 thinking、模板选 HF 原生还是上游 qwen3_fixed，都可以后改。不可逆的是首训数据一旦按现状采集，被删的动作补不回来。

验收：合成用例覆盖键重排、reminder 文本块、省略 thinking、compaction 四种，断言分类与 generated 等于 trained；用 run8 的 6 段 capture 回放新渲染器，要求 t0 边界变 CLEAN、其余逐位不变；生产计数器上线；B 的第一批真实请求体用来量旧路径的漂移率，作为这项修复的前后对照。

需要你决定的
是否接受"引擎实际看到的 token 为准，harness 回放只做匹配不做重渲染"作为轨迹表示合同。这是 T0，决定 C 能不能做。
过渡期是否先落 A 加 B。B 会在漂移轨迹上增加训练算力，但 GPU spike 前没有正式训练，代价现在是零。
匹配器对"回放省略了 thinking"是判 FORK 还是容忍。我倾向容忍并计数，因为存储的 token 里 thinking 本来就在。