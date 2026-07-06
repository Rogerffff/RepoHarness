# S0 implementation-notes（行车记录）

执行计划：`../01-s0-execution-plan.md`。本文分三节，发现即记，不事后补。规则：只记用户需要知道的事项（设计决策 / 偏离 / 权衡 / 开放问题），不记可自行判断的琐碎细节。

---

## Decisions（执行中做出的临时决策）

- [S0-0, 2026-07-07] AGENTS.md 采用"新内容置顶 + 旧章节原地保留标【legacy】"而非删除旧章节。理由：旧章节是理解被继承契约（五道防线、inspector 范式、原子语义）出处的最短路径，且删除会破坏旧 evidence 的上下文；代价是文件更长，已用标题前缀让新旧一眼可辨。
- [S0-0, 2026-07-07] 旧必读清单 B~G 未删除，段落标题全部改名（C 段显式标"已废弃"），置于"【legacy】旧架构选读清单"声明之下；段内条目的 ★ 标记在独立复核后二次清理（见 Deviations 第 1 条）。
- [S0-0, 2026-07-07] AGENTS.md"接手前最关键判断"从 3 条改为 4 条：新增第 4 条凭据安全（`deepseek_api.md` 只引路径不引内容），因为 rh2 阶段开始有真实 key 进入工作流。
- [S0-4, 2026-07-07] 计划预留的 `uv add --group dev transformers huggingface_hub` 实际未执行：两包已由 verifiers 传递依赖带入 uv.lock（transformers 5.13.0 / huggingface_hub 1.22.0），rh2 的 pyproject/uv.lock 零改动；renderers 库经 `sys.path` 从 `reference/renderers`（HEAD 5904fa2）只读引用。
- [S0-4, 2026-07-07] 实验脚本落位 `rh2/experiments/s0_renderer/`（计划产出只要求报告文件）。理由：scratchpad 属会话级易失目录，而该脚本是 24 项断言的可重跑回归（renderers/transformers 任一升级后 `cd rh2 && uv run python experiments/s0_renderer/v2_renderer_experiment.py` 一分钟内复验）；目录命名沿用计划里 S0-5 的 `rh2/experiments/` 惯例。

## Deviations（偏离计划的地方及原因）

- [S0-0, 2026-07-07] **首版实现有遗漏，被独立复核抓出后修复**：B/C 段内部条目上的 4 处 ★ 标记（AGENTS.md 原 463/472/474/476 行）第一遍只改了段落标题、没清条目标记，且本文件 Decisions 首版声明"全部去掉 ★"与事实不符。已修复（legacy 区现在 0 个 ★）并订正声明。教训：对"清理某类标记"的任务，验收要用 `grep -c` 全文计数而不是目测。复核同时发现并修复：两处"当前主战场/当前训练链路主路径"的现行语气残留、"等待 16G.3 引入"的失真未来时、README 免责声明未覆盖"推荐阅读"节、README"3 个错误"未同步为 4 个。
- [S0-0, 2026-07-07] **commit 拆分说明**：S0-0 会话开始时工作树里还带着上一轮讨论对 `01-s0-execution-plan.md` 的修订（codex 建议吸收 + C 系列定案，属实施前讨论的产物，非 S0-0 交付物）。为遵守"每任务独立 commit"，拆为两个 commit：先 `rh2(plan)` 提交计划修订，再 `rh2(s0-0)` 提交 AGENTS/README/notes。

## New-Unknowns（执行中新发现的未知，待消除）

- [S0-4, 2026-07-07] **U-G：本地路径加载 tokenizer 会静默降级 DefaultRenderer。**renderers 的 auto 解析用 `tokenizer.name_or_path` 精确匹配 `MODEL_RENDERER_MAP`（base.py:1478）；GPU 机上用本地权重目录（如 `/models/Qwen3-30B-A3B`）加载时不命中 → 回落 DefaultRenderer 且只打 INFO 日志，bridge 恒 None、`sampled_mask/is_content` 为空，token 保真链路整体失效。规避已写进 `s0/v2_renderer_report.md` 第 4 节：用 HF id 或显式 `Qwen3RendererConfig()`，启动时断言 renderer 类名。归 S0-5 落地为守门检查。
- [S0-4, 2026-07-07] transformers 版本敏感性：parity 在 rh2 锁定的 5.13.0 实测通过（renderers 官方下限 4.50）；GPU 机若因 vLLM 0.24.x 约束改变 transformers 版本，需随 S0-5 重跑 `rh2/experiments/s0_renderer/v2_renderer_experiment.py` 复验。
- U-E 静态部分已在 S0-4 消除（thinking 剥离 = 模板窗口语义，bridge 在 query 边界 fail-closed，量化见 `s0/v2_renderer_report.md` 第 3 节）；动态部分（真实 vLLM 采样的 `<|im_end|>` 尾 token、TrainClient 回退行为、截断路径 logprobs 对位）留 S0-5 观察。
