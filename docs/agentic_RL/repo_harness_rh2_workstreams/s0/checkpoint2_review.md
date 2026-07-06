# 检查点 2 汇总复核报告（S0 批次 2：S0-1 ~ S0-4）

- 复核者：干净上下文 sub-agent（fail-closed 视角），2026-07-07。
- 复核对象：baseline `c9577f1e` 之后的 6 个 commit——`37b11239`（计划修订）、`969bb191`（s0-0，检查点 1 已单独复核）、`c6a9488e`（s0-1）、`169f5d6a`（s0-4）、`a18fc381`（s0-2）、`810d0f0c`（s0-3）。
- 方法：逐条对照 `01-s0-execution-plan.md` S0-1~S0-4 验收标准 → 核对 evidence 文件 → 独立重跑客观验证器 → `git show --stat` 核对每个 commit 边界 → 全量 secret 扫描 → notes 声明与实际产物交叉核对（含源码行号抽查）。

---

## 0. 总判定

**有条件通过。** 四个任务的客观验收全部独立复现为绿（17 passed / FAIL=0 / 6 dump 结构与声明一致 / 无 key 泄漏入库），evidence 与 notes 声明未发现不实（与 S0-0 首版不同，本批次声明可信度良好）。两个收口条件：

1. **轮换 OPENAI key**（问题 1，安全遗留动作，notes 只记了 bug 修复、没提轮换）。
2. **执行已解锁的 deepseek 复跑或显式豁免**（问题 3，`deepseek_api.md` 在 s0-3 提交后已补入 key，原阻塞不复存在）。

---

## 1. 独立重跑结果

| 验证器 | 命令 | 声明 | 实测（本次复核） |
| --- | --- | --- | --- |
| S0-2 契约测试 | `cd rh2 && uv run pytest tests/contract_verifiers -q` | 17 passed | **17 passed in 1.73s** ✅ |
| S0-4 渲染回归 | `cd rh2 && uv run python experiments/s0_renderer/v2_renderer_experiment.py` | 12/12 + 12/12，FAIL=0 | **parity 12/12、bridge 12/12、FAIL=0，exit code 0** ✅ |
| S0-3 dump 校验 | 脚本解析 6 个 JSON + secret 形态扫描 | 可解析、无 secret | **6/6 可解析；`sk-*`/`Bearer *`/`r-sA`/AWS 形态 0 命中** ✅ |
| S0-1 import 冒烟 | `uv run python -c "import verifiers.v1, renderers"` | 成功 | **成功（renderers 0.1.8.dev54）** ✅ |

toy loop 本体按任务要求未重跑（涉及外部端点）；上游 smoke（9 passed）未重跑（需 standalone uv 0.11.x，接受 contract_baseline 第 1 节的记录及其 AST 佐证方法）。

---

## 2. 逐任务验收对照（结论：4/4 达标，S0-3 有一项已留痕的偏离）

### S0-1（deps_report.md，commit c6a9488e）

| 计划验收项 | 复核结果 |
| --- | --- |
| `rh2/` 独立子项目、name=repoharness2、Python 3.12、src 骨架、根 pyproject 不动 | ✅ `rh2/pyproject.toml` name=repoharness2、`requires-python = ">=3.12,<3.14"`、`.python-version=3.12`、`src/repoharness2/__init__.py` 空壳；根 pyproject 无改动 |
| verifiers git pin 用完整 40 位 hash | ✅ `[tool.uv.sources]` rev=`5885ab9c54152e707af2a11797aa52c3eb1752da`；`uv.lock` 同 hash；`reference/verifiers` HEAD 实测一致 |
| pytest、pydantic>=2、锁定 uv.lock | ✅ pydantic>=2（锁 2.13.4）；pytest>=8 + pytest-asyncio 在 dev group（锁 pytest 9.1.1） |
| 记录 prime 生态实际版本 | ✅ deps_report 所列 5 个版本与 uv.lock 逐项核对一致（verifiers 0.1.15.dev419 / renderers 0.1.8.dev54 / prime-sandboxes 0.2.28 / prime-tunnel 0.1.10 / pydantic 2.13.4） |
| V1 安装层判定 | ✅ 判定口径与计划同义（"全部依赖可安装、verifiers 可 import"），import 冒烟本次复现 |

### S0-2（contract_baseline.md，commit a18fc381）

| 计划验收项 | 复核结果 |
| --- | --- |
| 四个测试文件、覆盖计划列出的断言 | ✅ 4 文件 17 用例，是计划断言集的超集（graph 4 / lifecycle 4 / wire 6 / trainclient 3） |
| 上游 smoke 在 reference/verifiers checkout 跑 | ✅ 已跑（9 passed）；uv 版本门槛、工作树非干净两项环境事实已记录且给出 AST 对比佐证方法 |
| 测试全绿 + 行为清单 | ✅ 本次独立重跑 17 passed；G1-G6/R1-R7/W1-W8/T1-T8 行为清单带源码出处 |

### S0-3（toy_trace_dump/ + field_check.md，commit 810d0f0c）

| 计划验收项 | 复核结果 |
| --- | --- |
| ToyTaskset 两题（bash 建文件 / edit 改名），@reward 在 runtime 里读文件断言 | ✅ `rh2/tests/fixtures/toy_taskset.py`：`bash_create_file` + `edit_rename_function`，`task_completed` 用 `runtime.read()` 断言 |
| default + null 各跑一次，入口 `Environment.episode` | ✅ dump 实测：default 角色链 `[system,user,assistant,tool,assistant]`、sampled `[F,F,T,F,T]`、reward 1.0/1.0；null 退化为 `[user,assistant]`、reward 0.0/0.0——工具归属边界成立 |
| 端点指向 deepseek（C5） | ⚠️ **偏离已留痕**：执行时 `DEEPSEEK_API_KEY:` 行为空（dump meta `deepseek_key_status="missing"`、created_at 04:39:13、401 掩码 `****MPTY` 三处佐证），改用进程内 mock 完成结构层验收。见问题 3：key 现已补入，复跑已解锁 |
| 只验收结构层（拓扑/messages/工具往返/错误归因/RolloutLimits） | ✅ 六项逐一有 dump 佐证；`default_subprocess_maxturns1` 两题 stop=`max_turns`；`deepseek_attempt` 两题 stop=`error`、`ProviderError` 归因正确；token 字段空置符合 EvalClient 预期声明 |
| subprocess + docker 两 runtime 都本机跑 | ✅ 四格矩阵齐备，docker 分支 per-rollout 容器生命周期 = V1 使用层通过，判定口径与计划 S0-1 "DockerRuntime 起容器执行 run() 成功" 同义（该判定不依赖模型提供方，mock 不削弱它） |

抽查数字全部对上：task0 usage 168/48、tool 结果 head `hello rh2`、finish_reason 序列 `[tool_calls, stop]`、num_branches=1。

### S0-4（v2_renderer_report.md，commit 169f5d6a）

| 计划验收项 | 复核结果 |
| --- | --- |
| 读 qwen3.py 确认 tool call 格式 / thinking 策略 / bridge 实现 | ✅ 报告 §1 四小节齐备，行号抽查属实（`base.py:998` 处 `"Qwen/Qwen3-30B-A3B": "qwen3"`；`base.py:~1478` 用 `tokenizer.name_or_path` 精确匹配——U-G 声明成立） |
| 30B-A3B tokenizer 实测对照 apply_chat_template | ✅ 12/12 parity 本次独立复现；MoE vs dense 同一性（模板 sha256 `a55ee1b1660128b7`、vocab 151669）与 v2_results.json 一致 |
| V2 明确判定 | ✅ "hand-coded renderer 覆盖 30B-A3B = 通过"，与计划判定标准逐字同义 |

---

## 3. 问题清单（按严重度排列）

### 【高】问题 1：真实 OPENAI key 曾外发到 deepseek 端点，事后补救缺"轮换"这一步；key 尾指纹已入 git 历史

- **定位**：事件记录在 `s0/implementation-notes.md`（Deviations S0-3 第 2 条，随 commit `a18fc381` 入库）与 `s0/toy_trace_dump/field_check.md` 发现 2（commit `810d0f0c`）。
- **复核实证**：本地 `deepseek_api.md` 的 OPENAI key 实测 164 字符、**尾部确为 `r-sA`**——即文档里写的指纹是真实存活凭据的最后 4 字符，且该指纹在 c9577f1e..HEAD 的提交内容里出现 2 次（上述两个文件），已永久进入 git 历史。事故本身：runner 首版 `\s*` 跨行解析 bug 把完整 OPENAI key 放进 Authorization 头发到了 `https://api.deepseek.com`（对方 401 响应回显了掩码后的尾部）。
- **好的一面**：bug 已修复（`s0_toy_loop.py:100` 现为同行匹配 `[ \t]*` + `(\S+)`），修复后 401 回显 `****MPTY` 证明不再外发；`scrub_secrets`/`assert_no_secret` 两道防线实现与声明一致；6 个 dump 与全部提交内容扫描 0 泄漏。
- **缺口**：凭据已经到达过第三方（deepseek 服务端日志可能留有完整 key），fail-closed 原则下该 key 应视为已泄漏，但 notes/field_check 只记录了"修复 + 不再外发"，**没有提出轮换**。另外"绝不允许出现 key 内容"的项目红线按严格口径也覆盖尾部 4 字符指纹。
- **建议修法**：（a）立即在 OpenAI 控制台轮换该 key 并更新 `deepseek_api.md`——轮换后历史里的尾指纹自然失效，无需重写 git 历史；（b）在 implementation-notes 补一条"已轮换"记录；（c）以后文档记录同类事件用"尾部指纹（略）"或哈希代替字面片段。

### 【中】问题 2：S0-3 的 implementation-notes 条目混进了 s0-2 commit，s0-3 commit 自身漏交 notes

- **定位**：`git show a18fc381 -- .../implementation-notes.md` 显示该 commit（标签 `rh2(s0-2)`）加入了全部 `[S0-3]` 条目（mock 决策、deepseek key 偏离、安全事件、macOS docker shim、New-Unknown）；而 `git show 810d0f0c --stat`（`rh2(s0-3)`）9 个文件里没有 implementation-notes.md。`git log --follow` 证实该文件只被 969bb191 / 169f5d6a / a18fc381 三个 commit 碰过。
- **影响**：计划 §2.1 的设计是"用户可按 commit 逐个 diff 复查"——现在按 s0-2 的 diff 看会读到 S0-3 的偏离与安全事件（当时 s0-3 的产物还不在库里），按 s0-3 的 diff 看则缺少其应有的 notes 交付。审计对应关系被破坏，功能无损。时间线（s0-4 04:34 → s0-2 04:44 → s0-3 04:45）表明四个 commit 是批末集中整理提交的，notes 文件被整体带进了先提交的那个。
- **建议修法**：不重写历史（成本大于收益）；在 implementation-notes 的 Deviations 补一条勘误，说明"a18fc381 的 notes 变更中 [S0-3] 条目属于 810d0f0c 的交付范围"；后续任务 commit 前用 `git diff --cached -- <notes>` 检查 hunk 归属，必要时 `git add -p` 拆分。

### 【中】问题 3：`deepseek_api.md` 已在 s0-3 提交后补入 key——原阻塞不复存在，待办复跑尚未执行，相关文档描述已过时

- **定位**：`deepseek_api.md` mtime = 2026-07-07 04:49:14（晚于 s0-3 commit 04:45 与 dump 生成 04:39），`DEEPSEEK_API_KEY:` 行现有 35 字符值。`field_check.md` 发现 1 与 implementation-notes Deviations 里"只有 OPENAI/CLAUDE key 有值"的描述在**执行当时属实**（有 dump meta 三重佐证，不属声明不实），但对现状已过时。
- **影响**：S0-3 唯一未闭环项（真实 provider 经 docker 容器到宿主 interception server 的往返，New-Unknowns S0-3 条目）现在可以消除了，但没人跑。
- **建议修法**：检查点 2 收口前执行 `cd rh2 && uv run python experiments/s0_toy_loop.py --harness default --runtime docker --endpoint deepseek`（runner 防线已复核可信），把结果 dump 追加进 toy_trace_dump/ 并在 notes 勾销该 New-Unknown；若用户决定推迟到 S0-5 一并做，需在 notes 显式记录豁免。

### 【低】问题 4：implementation-notes 分节结构被 S0-3 插入打乱（两个 Deviations、两个 New-Unknowns 标题）

- **定位**：`s0/implementation-notes.md` 第 21/27 行（"Deviations（S0-3 追加）"、"New-Unknowns（S0-3 追加）"）插在 Decisions 与原 Deviations（第 31 行）/原 New-Unknowns（第 36 行）之间，与开档声明"分 Decisions / Deviations / New-Unknowns 三节"不符。
- **建议修法**：把 S0-3 条目并入原三节（条目自带 `[S0-3]` 标签已足够溯源），恢复三节结构。

### 【低】问题 5：per-task 独立复核折叠为本次汇总复核，该工作流偏离只在 commit message 留痕，notes 无对应条目；批内执行顺序重排同样未留痕

- **定位**：计划 §2.1 要求"每个任务完成后由新开 sub-agent 干净上下文复核"；实际为 orchestrator 自复跑（s0-2/s0-4 commit message 有记录）+ 本次汇总复核，折叠决定仅见于 `169f5d6a` 的 commit message（"full per-task review folded into checkpoint-2 sweep"）。另外批内实际顺序为 S0-1→S0-4→S0-2→S0-3（S0-4 无前置依赖，重排无实质风险），计划写的是 S0-1→S0-2→S0-3→S0-4。
- **建议修法**：在 implementation-notes 的 Deviations 补一条，把两点一并记录（notes 是计划指定的统一留痕位置，commit message 检索性差）。

### 【低】问题 6：V2 证据链存在"双源 renderers"，等价性本次实测成立但未固化

- **定位**：S0-4 实验经 `sys.path`（`v2_renderer_experiment.py:23`）验证的是 `reference/renderers` HEAD `5904fa2`；而 rh2 venv 里 TrainClient 将实际 import 的是 **PyPI 的 renderers 0.1.8.dev54**（uv.lock source=registry）。本次复核 diff 了 qwen3.py/base.py/parsing.py/configs.py 四个关键文件：**逐字节一致**，V2 结论可传递到运行时依赖。
- **风险**：这一等价性没有任何检查固化——reference HEAD 前移、或未来 uv.lock 重解析出别的 renderers 版本时，"实验验证的代码"与"运行时代码"会静默分叉。
- **建议修法**：在 `v2_renderer_experiment.py` 启动时加一段守门（对比 site-packages 与 reference/renderers 两处关键文件的 sha256，不一致即 FAIL），或至少在 v2_renderer_report.md 补记本次核对结果；S0-5 的"启动断言 renderer 类名"守门（U-G 对策）保持不变。

---

## 4. 安全专项核查记录（全部通过）

| 检查 | 命令/方法 | 结果 |
| --- | --- | --- |
| deepseek_api.md 未追踪 | `git ls-files -- deepseek_api.md` 空输出 | ✅ |
| 被 ignore | `git check-ignore -v` → `.gitignore:23:deepseek_api.md` | ✅ |
| 从未入历史 | `git log --all -- deepseek_api.md` 空输出 | ✅ |
| HEAD 追踪内容无 key 形态 | `git grep -nIE "sk-[A-Za-z0-9]{10}"`（排除 reference/、runs/） | ✅ 仅历史文档里 `swe-task-feasibility` 之类子串误命中，无真实 key |
| 批次提交内容无 key 形态 | `git log -p c9577f1e..HEAD` 扫 `sk-*`/`api_key=…`/`Bearer …` | ✅ 0 命中；`r-sA` 尾指纹 2 次命中即问题 1 所述两处文档 |
| 6 个 dump 无 secret | 脚本扫 `sk-*`/`Bearer`/`r-sA`/AWS 形态 | ✅ 0 命中；401 回显为掩码 `****MPTY` |
| runner 防线与声明一致 | 读 `s0_toy_loop.py:82-128` | ✅ `[ \t]` 同行匹配、`scrub_secrets` 键名+字符串双掩码、`assert_no_secret` 拒绝落盘，三者与 field_check §6 描述逐条吻合 |

## 5. 交叉一致性抽查记录（notes 声明 vs 实物）

核对过且一致的声明（挑有分量的列）：verifiers pin 完整 hash（pyproject/uv.lock/reference HEAD 三点一致）；deps_report 5 个版本号 vs uv.lock；"transformers/hf_hub 已在锁文件、pyproject 零改动"（锁内 5.13.0/1.22.0，s0-4 commit 未触碰 pyproject/uv.lock）；"renderers 经 sys.path 只读引用"（实验脚本第 23 行）；U-G 的 `base.py:1478` 行号与语义；`MODEL_RENDERER_MAP` 的 30B-A3B 条目（base.py:998）；macOS shim 只 patch `verifiers.v1.rollout.reachable_url` 且带 Darwin 守卫（s0_toy_loop.py:288-312,393）；maxturns1 的 stop=max_turns 与 reward=1.0 语义说明；deepseek_attempt 的 ProviderError 归因。未发现声明不实。

## 6. 建议的收口动作清单

1. 轮换 OPENAI key（问题 1）→ notes 记录。
2. 跑 deepseek 复跑或显式豁免（问题 3）→ dump + notes 勾销 New-Unknown。
3. notes 补两条 Deviations（问题 2 勘误、问题 5 工作流折叠+顺序重排）并顺手合并重复分节（问题 4）。
4. （可选）v2 实验加双源等价性守门（问题 6）。
5. 完成 1~3 后即可按计划进入租 GPU 机的 S0-5。
