# A → B 接线交接：下一轮基座诊断前要对齐的条件（2026-09-24）

Claude（A 线）。依据 [第六组 README §8.2](../batch6_efficiency_20260921/README.md)（Codex：接线不能只包括工具常量）。**本文是交接清单，不是已通知**：由用户转给 B；B 的文件由 B 改，A 只列生产包装的用法与验收方式。

## 1. 现状差距（B 探针 vs 正式链）

`rh2/experiments/base_probe_20260922/qwen_adapter_server.py` 直接构造 vendored `AnthropicAdapter`，会话由 `_Store` 首次请求自动建立。因此当前探针**没有**：#6(a) 提醒并入 tool_result、真实 `count_tokens`、溢出 400、#5 EOS 字面量剥离；只导入 `cc_launch_conditions` 拿不到这些。正式链在 `bringup.py` 的唯一生产构造点按下面顺序装配。

## 2. adapter 进程要改的四处（`qwen_adapter_server.py`，B 文件）

```python
from repoharness2.adapters.slime.count_tokens_wire import bind_count_tokens_adapter, install_count_tokens_wire
from repoharness2.adapters.slime.parse_wire import assert_parse_wire_installed, install_parse_wire, install_turn_terminal_publisher
from repoharness2.adapters.slime.prompt_overflow import install_overflow_400_wire
from repoharness2.adapters.slime.rh2_anthropic_adapter import rh2_anthropic_adapter_cls

install_count_tokens_wire()                       # 1) 先装 count_tokens 路由（必须在构造 adapter 之前）
install_parse_wire(eos_token=tokenizer.eos_token, eos_token_id=tokenizer.eos_token_id)
                                                  # 2) #5：只在"最后一个采样 id 是 EOS"时剥可见末尾字面量；悬空 <tool_call> 置 ill_formed
install_turn_terminal_publisher()                 # 2b) 探针没装 capture wire：给 call_sglang_generate 包一层发布 EOS 事实（生产由 capture wire 发布）
install_overflow_400_wire()                       # 2c) 探针没装 capture wire：真正溢出时回 Anthropic 形状的 400（与 capture wire 同一份构造）
assert_parse_wire_installed()
adapter = rh2_anthropic_adapter_cls()(tokenizer=..., sglang_url=..., tool_parser=..., reasoning_parser=...,
                                      fork_threshold_tokens=..., debug_callback=...)   # 3) #6(a) 生产子类
bind_count_tokens_adapter(adapter)                # 4) count_tokens 绑到这个 adapter 实例
```

- #5 修订（Codex R1/R2，2026-09-25）：字面量剥离不再靠字符串猜测——没有 EOS 事实（没装发布器）就**不剥**并计 `eos_fact_missing`；普通 token 拼出的 `<|im_end|>` 保留。悬空判据只看解析后可见残余的未闭合 `<tool_call>`（空 / `<function=` / `{` 续接），正文提到标签不算。

- 顺序原因：`install_count_tokens_wire` 改的是 vendored 类，路由在 `__init__` 里建；`rh2_anthropic_adapter_cls()` 是延迟绑定的子类工厂（vendored 模块可能被重置，不要在模块顶层 `class X(AnthropicAdapter)`）。
- **溢出 400**：正式链的 "prompt is too long" 400 在 capture wire；vendored adapter 溢出时只记 warning 并返回 `finish_reason="length"` 的空输出，CC 拿不到 400 就不会走被动压缩。**已完成（2026-09-25）**：响应构造抽到 `prompt_overflow.py`（capture wire 与探针共用），探针进程按上面第 2c 行装 `install_overflow_400_wire()` 即可（幂等；判据 = 会话配置了窗口且 prompt token ≥ 窗口，`_Store` 建会话时给的 `max_context_tokens` 就是这个窗口；真实 vendored adapter、不装 capture wire 的 HTTP 用例已覆盖）。
- 记录：`adapter_config.json` 追加 `rh2_wrappers: {count_tokens, parse_wire, rh2_subclass, overflow_400}` 四个布尔，逐项写实际是否装上；版本用 `git rev-parse HEAD` 与 `parse_wire_stats()`。

## 3. CC 启动条件（`solve_attempt.py` 等，B 文件）

- 命令行追加 `cc_tool_surface_args()`（`--tools Bash,Read,Edit,Write,NotebookEdit`，#10）。
- 环境：`CC_RH2_STATIC_ENV`（`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`，#9）+ `cc_context_env(max_context_len=<窗口>, max_new_tokens=<采样上限>, file_read_max_output_tokens=<Read 上限或 None>)`（#8：`CLAUDE_CODE_MAX_CONTEXT_TOKENS` / `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_CODE_MAX_OUTPUT_TOKENS` / `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`）。窗口取值与 adapter 的 `max_context_tokens` 必须是同一个数（正式链由 `SlimeBindingConfig` 单点给出）。
- 诊断预算可以比正式候选宽，但逐项记差异：25 次 / 600 s / 32K 不是新定案（README §8.2）。
- CC 版本仍 2.1.205；`#8` 的事实（Read 截断、无主动压缩默认、`AUTO_COMPACT_WINDOW` 100,000 下限、400 触发被动压缩）都绑定这个版本。

## 4. B 自有的两处修复（README §8.2 已列 owner）

- 探针网关（`model_gateway.py`）上游流中断时的 HTTP 收尾：#3 事实表证明"多块部分 SSE + 正常 HTTP 结束"会让 CC exit 0 且把残缺回复当完整交付（`stream3_repro_20260924.md` §7–§8）。网关应把上游中断传成异常结束（断连/RST，不 `write_eof` 正常收尾）或改回错误状态。
- `solve_attempt.py` 的宿主轨迹路径读取按 #2 的宿主收集语义（日志目录 `<artifact_dir>/<trajectory_id[:24]>/harness/<identity[:24]>-<sha256[:16]>`，bad stream 不标完整）。

## 5. R2E E09（A/B 明确交接项）

- 事实（B 决定 E09）：`rollout_spec_from_view` 未传激活脚本/解释器前缀，`RolloutTaskSpec.expected_interpreter_prefix` 默认 conda；R2E `.venv` 会被正式启动前核对拒绝；`PUBLIC_SYSTEM_HINTS` 写的是 conda。
- 分工：B 提供逐来源的公开激活/解释器事实（`--activation r2e_venv` 的内容、`python` 实际路径）并进任务面字段；`prepared_task_face.py` 当前单一写入者是 B（有未提交改动），字段接入由 B 落地、A 审；A 核对 `generate.py` 的启动前解释器核对接受 `.venv` 前缀且不放松 conda 题的核对；提示措辞按来源分开。
- 不阻塞只用 SWE-Gym 的工作；R2E 正式 actor 诊断前完成；不以关闭核对绕过。

## 6. A 待办（本文引出的）

1. ~~把 capture wire 的溢出 400 判断抽成共用小函数并给 B 用法~~——已完成（2026-09-25）：`prompt_overflow.install_overflow_400_wire()`，用法见 §2 第 2c 行。
2. 网络供应 Brief（1A+2A，[设计稿](../batch6_efficiency_20260921/network_supply_brief_20260924.md)）里需要 B 的逐题 `blocked_dists`、例外表与派生镜像 pip/uv 可用性——启用前才需要。

## 7. 不可外推（#11 保留）

探针没有 capture / backfill / 异步发布 / 训练行归属；其上得到的行为与成本不能推到训练链。
