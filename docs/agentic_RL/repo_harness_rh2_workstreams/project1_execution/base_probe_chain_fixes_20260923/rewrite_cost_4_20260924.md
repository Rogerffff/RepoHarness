# #4 CC 改写回放参数：表示成本核验（正式链夹具，真实 CC 2.1.205）

2026-09-24 / Claude（A 线）。**状态：事实表完成；改匹配规则的取舍待用户决定（T0），只加观测为 T2。** 依据：[交接包 §5](../base_model_probe_20260922_aline_handoff.md)、[第六组 README §8.1 第 4 条](../batch6_efficiency_20260921/README.md)（Codex：有边界的表示成本核验，不是吞吐定论或重开 I01 的前置；记录消息树分支、训练行、总输入 token 与唯一可训 token；剧本只能证明改写怎样产生多行，发生率复用下一轮 B 流量，GPU 吞吐留 E5）。

## 1. 夹具与边界

`rh2/experiments/base_probe_fixes_20260923/stream3_formal_chain.py` 场景 W1 / W0：真实 CC 2.1.205 + 正式 relay + 真实 vendored adapter（生产子类、count/parse wire）+ 真实 capture wire + 真实 `RolloutOrchestrator(fa_formal)` + 生产 `bringup_leaf_facts`（I01 `turn_coverage`）；引擎是剧本，tokenizer 是真实 Qwen3-30B-A3B。**分叉阈值取生产值 `FORK_THRESHOLD_TOKENS = 0`**（改写不合并，成死端叶各训练一次）。

渲染闭环：CPU 夹具没有 sglang 解析器，工具调用走 XML 回退格式；tokenizer 包装把 CC 回放的 assistant（text + tool_calls）渲染回引擎当初发出的 XML 文本，引擎输出 id 末尾带 EOS（#5 parse wire 剥掉可见字面量）。这样 prompt(k+1) 的 assistant 段 token 与采样 id 逐位一致，漂移只来自 CC 对参数的改写——与生产"模板原生格式 + sglang 解析器"是同一种闭环，不是同一份字节。首轮没做这个闭环的运行（`w4_*a`）每轮都因格式漂移被 realign / merge，只训了末轮，已作废。

剧本（各 5 轮，最后一轮文本收尾）：

| 轮 | W1 改写组（引擎原样） | W0 对照组 |
| --- | --- | --- |
| 1 | Write 内容含行尾空格与 tab（`x = 1   \n y = 2\t\n`） | Write 内容无行尾空白、无末尾换行 |
| 2 | Bash `cd /testbed && cat …` | Bash `cat …` |
| 3 | Edit 不带 `replace_all`，`new_string` 带行尾空格 | Edit 显式 `replace_all=false`（引擎参数顺序：file_path, old, new, replace_all） |
| 4 | Bash `cd /testbed && cat …` | Bash `cat …` |

## 2. 事实（`runs/base_probe_fixes_20260923/remote/w4_W1/`、`w4_W0/`，各一次运行）

**CC 2.1.205 实测的回放规范化**（与 CCS `normalizeToolInput` 三类一致，另加一类）：Bash 去掉 `cd /testbed && ` 前缀；Edit 补 `replace_all: false` 且放在**首位**；Edit `new_string` 与 Write `content` 去行尾空白；Write `content` 的**末尾换行也被去掉**（首轮对照组意外发现）。

| 指标（`turn_coverage`） | W1 改写组 | W0 对照组 |
| --- | --- | --- |
| 生成轮 / 训练轮 | 5 / 5 | 5 / 5 |
| 训练行 | **5** | **2** |
| 各行 token（含前缀） | 3,211 / 3,290 / 3,359 / 3,449 / 3,476 | 3,366 / 3,476 |
| 各行可训 token | 40 / 39 / 46 / 39 / 4 | 126 / 38 |
| 可训 token 合计 | 168 | 164 |
| 输入 token 合计 | **16,785** | **6,842** |
| 末行之外的输入 token | 13,309 | 3,366 |
| realign / merge 掉轮 | 0 / 0 | 0 / 0 |
| 交付 | 5 条 `present_complete` 样本 | 2 条 |

- W1 的每一次改写都让下一请求的 assistant 段 token 与采样 id 不同 → 阈值 0 下**每轮一个新训练行**，每行重复约 3.2K 前缀：同样约 165 个可训 token，输入 token 是对照组的 2.45 倍。
- W0 仍剩 1 次分叉：Edit 的 `replace_all` **键序**——引擎发出时在末位，CC 回放时在首位，dict 相等但渲染文本不同（交接包"51 个调用 dict 相等但键序不同"的形态）。其余三轮 CLEAN。
- 本剧本 5 轮、前缀 3.2K，只说明机制与比例：真实发生率（交接包复算 13.8% 的工具轮）与真实前缀长度（32K 窗口下常见 1–3 万）下的绝对成本要用下一轮 B 流量的 `turn_coverage` 实测；GPU 吞吐损失留 E5。`input_tokens_excluding_last_row` 不是精确的额外训练成本。

## 3. 选项（不作决定）

| 选项 | 内容 | 对策略可见输入 | 等级 |
| --- | --- | --- | --- |
| (i) 维持 I01 B（现状） | 改写轮成死端叶各训练一次 | 模型看到 CC 规范化后的历史（与它自己说的不同） | 无改动 |
| (ii) 按采样消息匹配与渲染 | 回放的 assistant tool_use 若与树上记录的采样输入只差 CC 已知规范化（cd 前缀、`replace_all` 默认、行尾空白、键序），翻译时改用记录的采样输入渲染 → 无分叉 | 模型看到自己原来的输出；CC 实际执行的是规范化后的命令（语义等价：cwd 就是 /testbed、`replace_all` 默认即 false、空白只影响文本） | **T0**（接近已暂缓的 I01 C 路线） |
| (iii) 只做键序归一 | 只在 dict 相等时按记录轮的键序渲染回放参数 | 只改变参数在文本里的顺序，回到采样顺序 | T1 建议，仍请用户确认 |

**建议**：先不改匹配规则；把 `turn_coverage` 的行数 / 输入 token 作为下一轮 B 流量的固定观测（已有 producer，无需新 producer），拿到真实发生率后再决定 (ii)/(iii)。若要先动手，(iii) 是零语义风险的一半收益。

## 4. 没做的事

没有跑真实模型（发生率未测）；没有 GPU 吞吐；夹具用 XML 回退格式而非生产模板原生格式（闭环等价，字节不同）；每组各一次运行。
