# #3 上游流中断：正式传输链复现事实表

2026-09-24 / Claude（A 线）。**状态：事实表已完成；结论 = 正式链现状不需要新的准入规则或 relay 加固（见 §4），一条待 B 线核对的差异（§5）。** 依据：[交接包 §3](../base_model_probe_20260922_aline_handoff.md)（B 线观测）、[§14.2](../base_model_probe_20260922_aline_handoff.md)（Codex 收窄：保留"adapter 写出中途失败（未 commit）"与"服务端已 commit、下游未完整接收"两个边界；完整流正控、缺 `message_stop` 的干净 EOF、异常断连分别核对；`abort()` 只作 T1 候选须先验证）。

## 1. 夹具（只有引擎与 tokenizer 是替身，其余全是正式实现）

`rh2/experiments/base_probe_fixes_20260923/stream3_formal_chain.py`（未跟踪的实验脚本）。链路：

真实 CC 2.1.205（容器：真实 `conan-io__conan-15422` 镜像、正式 profile / relay / 可信初始化 / 激活文件，经正式 `ClaudeCodeDriver.run`）→ RH2 relay 容器（`sandbox_profile._RELAY_SCRIPT`）→ **宿主侧故障代理**（本脚本；HTTP/1.1 感知，解析 SSE 分块流，按响应序号动手）→ 真实 vendored `AnthropicAdapter` app（`run_app_in_thread`，与生产同一入口；`build_session_guard_middleware`）→ 真实 `capture_wire.install_capture_wire` → 进程内假引擎（`/generate` 应答按剧本；`weight_version=5`）。编排：真实 `RolloutOrchestrator(execution_mode="fa_formal", require_real_weight_versions=True, reject_on_nonzero_harness_exit=True)` + 生产 `make_per_rollout_adapter` + `make_threadsafe_session_drain_owner` + registry poison / cap 接线 + 生产 `build_grading_spec_from_host_view` 评分材料（评分执行是 `GradingSubmitStub` 罐头报告，评分本身不是对象）。

假 tokenizer 前缀一致（assistant 渲染 = 生成提示 token + 该轮引擎输出 id），剧本按"请求里 tool 消息数"选轮（同一轮重试拿同一应答）：T0 `Bash echo RH2S3T0` → **T1 `Bash echo RH2S3T1 > /tmp/rh2s3_t1_ran`（被切的轮，tool_use）** → T2 `Bash cat /tmp/rh2s3_t1_ran`（切后若继续，能看见 T1 是否执行）→ T3 文本 end_turn。所有切断落在第 2 个 SSE 响应（T1）。

边界 A（未 commit）：A1 进程内注入——目标轮的第 3 次 `StreamResponse.write`（`content_block_start` 之后）抛 `ConnectionResetError`，走 vendored `_run_turn` 的 except 路径（499、不 `record_turn`）。边界 B（已 commit）：代理在 relay→CC 段动手，上游照常排空让 adapter 正常收尾并 commit。

## 2. 事实表（每场景一次真实运行；证据 `runs/base_probe_fixes_20260923/remote/s3_<场景>/facts.json`）

| 场景 | 流形态（第 2 个 SSE 响应） | 边界 | CC：请求数 / `result` / 退出码 | 被切轮工具是否执行 | adapter commit | 编排收口 | 交付 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | 完整（正控） | — | 4 / `success, is_error=false, num_turns=4` / 0 | 是 | 4 轮 capture | `completed / present_complete` | 交付：121 tokens、可训 24、`online_policy_loss_eligible`，评分 1 次 |
| S1 | `content_block_start` 之后 **RST** | B | 2 / `success, is_error=true, stop_reason=stop_sequence, num_turns=2` / **1** | 否（CC 没看到 T1 的 tool_use） | 2 轮（第 2 轮已 commit） | `harness_crash / missing`，`nonzero_harness_exit_in_formal_chain` | ABORTED、`remove_sample=True`，评分 0 次 |
| S3 | `content_block_start` 之后 **FIN**、无 chunk 结束标记 | B | 同 S1 | 否 | 同 S1 | 同 S1 | 同 S1 |
| S5 | `content_block_start` 之后截断、**chunked 正常结束**（HTTP 完整 / SSE 在消息中途截断 = B 线旧网关 EOF 即 `write_eof` 的形态） | B | 同 S1 | 否 | 同 S1 | 同 S1 | 同 S1 |
| S6 | `content_block_delta` 之后截断、chunked 正常结束（工具入参已到，无 `content_block_stop` / `message_delta`） | B | 同 S1 | 否 | 同 S1 | 同 S1 | 同 S1 |
| S2 | 缺 `message_stop`、chunked 正常结束 | B | 4 / `success, is_error=false` / 0 | **是**（继续 T2、T3） | 4 轮 | `completed / present_complete` | 交付（与 S0 同形：可训 24） |
| S4 | `message_delta` 之后 FIN、无 chunk 结束标记（只缺 `message_stop`） | B | 4 / 同 S2 / 0 | 是 | 4 轮 | 同 S2 | 交付 |
| S8 | 整个响应换成 **529 overloaded + `x-should-retry: true`** | B | 2（**无重试**）/ `is_error=true` / 1 | 否 | 2 轮 | 同 S1 | ABORTED |
| A1 | adapter 第 3 次 write 抛 `ConnectionResetError` → 499、不 commit | A | 2 / `is_error=true` / 1 | 否 | 第 2 轮 **未** commit（499） | `session_plane_drain_unclean`（drain 见 `pending=1`）→ `completed / missing` | ABORTED、`remove_sample=True`，评分 0 次 |

其它观察：S1 与 S3 的 CC 侧事实完全相同——relay 的 `pipe` 把上游 RST 变成对 CC 的正常 FIN（交接包注 ②），对 CC 的行为没有影响；A1 在代理处看到的是"两个事件后上游 EOF、无终止 chunk"（aiohttp 在 handler 异常后关连接）；所有场景 poison 均未触发、cap 均未耗尽；各场景容器 / 网络零残留。

## 3. 由事实得出的判断

1. **CC 2.1.205 不重试**：无论 RST、FIN、HTTP 完整但截断、还是 529+`x-should-retry`，adapter 都只收到 2 个请求。"重试 → 同一轮重复 commit"的风险在本形态下不存在。
2. **`message_delta` 是 CC 的完整性分界**：`message_delta` 之前任何截断 → `result{subtype:success, is_error:true, stop_reason:stop_sequence}` + **退出码 1**；`message_delta` 之后（缺 `message_stop`、缺 chunk 结束标记）→ CC 视为完整、正常继续，样本与 CC 所见一致，属良性。
3. **正式链现状已经挡住交接包担心的形态**：已 commit 但 CC 未执行的工具轮（S1/S3/S5/S6/S8）全部因 `reject_on_nonzero_harness_exit=True` 被 `nonzero_harness_exit_in_formal_chain` 拒绝，不评分、不交付；未 commit 的 A1 由 drain 干净态检查拒绝。**不依赖 CC 的 `result` 事件**，与 §14.2"不把 result 新设准入规则"一致。
4. **relay `abort()` 加固（T1 候选）不改变结果**：RST 与 FIN 在 CC 侧等价（S1 = S3）。按"先复现→窄改→复验"的口径，复现显示无需改；不动 relay。
5. `_render_stream` 无显式 `write_eof()`、随后 commit（§14.2 指出的点）在正式链里的后果只是 S2/S4 这种良性形态或 S1/S3 这种被拒形态；正式 SGLang 上游是完整 JSON，adapter 不会自己产生 S5/S6（HTTP 完整但 SSE 中途截断）——那是 B 线旧探针网关 `write_eof()` 的产物。

## 4. 处置建议（不含新 T0）

- 正式链：**不加"末轮未完整交付即剔除"准入规则**（交接包列为 T0 候选）——现有非零退出码 + drain 干净态已覆盖全部实测形态；不改 relay；不改 `_render_stream`。
- 观测：A1 的收口码是 `session_plane_drain_unclean`（`termination_kind=completed`）而不是 harness_crash——两者都不交付，但诊断口径不同；记为已知，不改。
- 探针网关（B 线）：`model_gateway.py` 未见 `message_stop` 不应 `write_eof()`（交接包已列为 B 线待补）——本表说明即便如此 CC 也会退出 1，风险在探针侧只是"退出码解释"而非训练污染。

## 5. 待 B 线核对的差异

交接包记录 DVC6954/DeepSeek/a1 第 11 次响应停在 `content_block_start` 时 CC "仍报 `subtype=success`、退出码 0"。本表 S5（同一形态、同一 CC 版本、正式链）得到 `is_error=true`、退出码 1；四种截断都没有一例退出 0。可能的解释是旧启动路径的退出码来自 agent 可写的 `/tmp/.run.done` 标记（#2 已消除）或探针记录的是别的退出事实；请 B 线用 `AT/*/attempt.json` 与 `trajectory.jsonl` 的 `result.is_error` 复核那一条。若 B 线能给出 CC 退出 0 的真实形态，再补一个场景。

## 6. 本轮没有做的事

没有跑真实 SGLang / GPU；评分执行是罐头报告（交付判定只看编排收口与 `remove_sample`）；没有测 CC 的其它版本；没有测 `message_start` 之前的断连（那是 HTTP 层错误，adapter 尚未 commit，与 A1 同类）。
