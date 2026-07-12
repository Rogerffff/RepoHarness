# Claude Code 黑盒 HTTP 等待、重试与断连本地基线

> 后续源码引导的环境变量、超时、404 fallback 和版本冻结验证见
> `claude_code_retry_timeout_source_guided_validation.md`。后者是 FA 实施的当前
> 权威补充，本文件保留第一轮纯黑盒基线。

> 日期：2026-07-13  
> 被测客户端：Claude Code `2.1.205`（macOS arm64 本机二进制）  
> 探针：`rh2/experiments/fa_bringup/claude_code_http_probe.py`  
> 证据：`fa/claude_code_http_probe_evidence/*.json`

## 1. 结论

本轮补测纠正了此前过强的表述。严谨结论是：

1. Claude Code 在**尚未收到任何 HTTP 响应头**时，至少可以等待 120 秒；本轮
   没有测出它自己的最终 request timeout，因此不能声称它一定会在某个时刻
   取消，也不能把 120 秒当作配置常量。
2. `500`、`429` 和响应头前断连都会触发 Claude Code 发起新的 HTTP 请求；
   20 秒窗口内它没有自行放弃。
3. `500`、`429` 和响应头前断连的多次请求 body 完全一致；但**部分 SSE 已经
   交付后断连**时，Claude Code 会立即换一种请求形态重试（本轮从
   `stream=true` 改成 `stream=false`），所以只按 request body hash 去重不是
   可靠安全边界。
4. 外部终止 Claude Code 进程组后，fake server 能在没有发送响应头的挂起请求
   上观察到 socket 关闭。它只证明 TCP 取消可见，不等于 RH2 的
   aiohttp handler、ModelCallProxy、SGLang `/abort_request` 和 execution 账目
   已经接通；后者仍需本地 adapter 集成测试和 FA-5 真机验收。
5. 因此首版正确性仍必须依靠：episode 绝对 deadline、proxy 总 turn 预算、
   cancellation 传播、不可归因故障的 session poison、主动终止 harness
   execution。Claude Code 的经验 timeout 只能用于校准，不能成为正确性前提。

## 2. 测试方法

探针只监听 `127.0.0.1`，将以下环境变量指向本地 fake Anthropic Messages
endpoint，不访问真实模型服务，也不产生 API 费用：

```text
ANTHROPIC_BASE_URL=http://127.0.0.1:<ephemeral-port>
ANTHROPIC_AUTH_TOKEN=<fixed-dummy-token>
ANTHROPIC_MODEL=rh2-local-probe-model
```

Claude Code 使用与 slime harness 关键部分一致的调用面：`-p`、
`--permission-mode bypassPermissions`、`--output-format stream-json`、
`--include-partial-messages`、`--include-hook-events`、`--verbose`。探针在空临时
目录运行 CLI，避免项目 prompt、工具和 hooks 干扰 HTTP 行为；
`--no-session-persistence` 只避免测试会话污染本机历史。

`delay_success` 在 delay 结束前**不调用 `send_response()`**，因此不会提前发送
HTTP 状态行或响应头。这与当前 slime adapter“先完整等待 SGLang，再向 Claude
Code 写 SSE”的边界一致。

## 3. 结果

| 场景 | 观察窗口 | 请求数 | 进程结果 | 关键事实 |
|---|---:|---:|---|---|
| 无响应头 1 秒后成功 SSE | 2.38s | 1 | exit 0 | 正常成功 |
| 无响应头 30 秒后成功 SSE | 31.19s | 1 | exit 0 | 无并行/串行重试 |
| 无响应头 60 秒后成功 SSE | 61.01s | 1 | exit 0 | 覆盖当前 proxy 60s wait 下界 |
| 无响应头 120 秒后成功 SSE | 121.01s | 1 | exit 0 | 客户端 timeout 下界提高到 >120s |
| 连续 HTTP 500 | 20.08s | 6 | 探针终止 | 退避约 0.60/1.05/2.32/4.51/9.21s；body 相同 |
| 连续 HTTP 429 + Retry-After: 2 | 20.08s | 5 | 探针终止 | 前两段约 2.01s，随后 2.42/4.27s；body 相同 |
| 响应头前立即断连 | 20.08s | 6 | 探针终止 | 退避约 0.61/1.07/2.06/4.36/9.07s；body 相同 |
| 部分 SSE 后断连 | 0.85s | 2 | exit 1 | 7.3ms 后立即重试；第二次 stream=false，body 不同 |
| 无响应头挂起，5s 时外部终止进程组 | 5.08s | 1 | SIGTERM | server 观察到 `client_closed_before_response_headers` |

### 3.1 HTTP 500

请求到达时间约为：

```text
0.80s, 1.40s, 2.45s, 4.77s, 9.29s, 18.50s
```

六次 body digest 完全相同。结论是：adapter 将不可归因错误直接暴露为 500，
不会让 Claude Code 立即退出，反而会产生多个新的 HTTP 请求。真实 slime
`BaseAdapter._check_turn_cap()` 每个请求都会递增一次计数，因此这还会消耗
turn cap。Claude Code 的 `stream-json` 事件还明确报告
`max_retries=10`；本轮在第 6 次请求后的退避期间由 20 秒探针上限主动终止，
没有等待它耗尽全部重试。

### 3.2 HTTP 429

`Retry-After: 2` 被明显采用：前两个间隔分别约 2.007 秒，之后客户端继续采用
更长退避；事件同样报告 `max_retries=10`。返回 429 也不能作为“让黑盒
harness 停止”的机制。

### 3.3 部分 SSE 后断连

第一条请求是 `stream=true`；发送 `message_start` 后断开，约 7.3ms 后出现第二
条 `stream=false` 请求，body 长度和 digest 都变化。随后客户端以
“empty or malformed response (HTTP 200)”结束。

该结果有两个直接含义：

1. Proxy 内部重生成之前绝不能向 Claude Code 发送响应头、SSE heartbeat 或
   partial token，否则“未交付 attempt”不再成立。
2. 不可归因故障不能只依赖 `(session_id, request_body_hash)` 去重。首版应 poison
   整个 RolloutExecution 对应的 adapter session，并主动终止 harness。

## 4. 对 FA-1 的必需补充

### 4.1 同一个 HTTP handler 内部重生成

```text
Claude Code request
-> adapter 分配 server-side logical_turn_id
-> 等 TrainingRuntimeCoordinator.phase == ACTIVE
-> ModelCallProxy attempt_1
-> 更新窗口可归因 abort：不发送任何 HTTP 响应头，不提交 capture
-> 在同一个绝对 deadline 内等待并执行 attempt_2
-> 成功后一次性写完整 SSE
```

`delay_success` 证明这类形态在 120 秒内不会触发本机 2.1.205 的额外请求，但
正式实现不能据此允许 120 秒无限额预算。

### 4.2 统一 deadline

必须把 episode 绝对 deadline 挂进 adapter session，而不是让三个相对 timeout
各自运行：

```text
remaining = episode_deadline - monotonic_now - cleanup_reserve
attempt_timeout = min(configured_attempt_timeout, remaining)
update_wait_timeout = min(configured_update_wait_timeout, remaining)
proxy_turn_total_timeout = min(configured_proxy_turn_cap, remaining)
```

尤其要增加 `proxy_turn_total_timeout`：`attempt_1 生成 + 60s 更新等待 + attempt_2
生成` 的总时间可能远大于 60 秒。剩余时间不足时直接走不可归因缺员，不再开始
下一次生成。

### 4.3 不可归因错误

```text
ModelCallProxy 判定不可归因
-> 原子地将 session OPEN -> POISONED
-> 在返回/关闭当前 HTTP 请求前通知 RolloutExecution owner
-> 取消 harness task；必要时终止/删除 sandbox，使 detached Claude Code 真正停止
-> 后续任何同 sid 请求在 turn-cap 递增前拒绝
-> 不 commit capture，Outcome=missing_after_local_retry
```

只返回 500/429/503 都不够；本轮已证明客户端可能持续重试。只关闭 adapter
session 也只能阻止训练污染，不能阻止黑盒进程继续耗费 CPU、网络和 turn 请求，
所以 execution owner 必须主动结束 harness。

### 4.4 Cancellation

本轮外部终止证明未发送响应头的 socket 关闭可被 server 观察。接线后还必须有
本地集成测试证明：

```text
client disconnect / handler CancelledError
-> 取消 proxy wait 或 send task
-> SGLang /abort_request 被调用
-> staged capture 被 discard
-> delivered attempt 数不增加
-> session poisoned + execution missing
```

## 5. 仍未证明的内容

1. Claude Code 2.1.205 自身最终 request timeout 的精确值。本轮只得到
   `timeout > 120s` 的下界；没有为了一个不能承载正确性的经验常量继续等待
   300～900 秒。
2. 客户端自身 timeout 后会重试多少次、最终 exit code 是什么。要观察它必须等
   到真实 timeout，且结果仍只对该版本有效。
3. RH2 production adapter 的 poison、harness cancellation、SGLang abort 和
   capture rollback。当前功能尚未接入，不能用 fake server 代替代码验收。
4. FA-5 容器里的 Claude Code tarball 是否也是 2.1.205。若版本不同，本报告
   只作本机基线，关键场景必须用同一 tarball 重跑。

## 6. 后续验收分层

### 本地、FA-2 前

- 将 ModelCallProxy 接入真实 adapter handler。
- fake SGLang 注入 update abort，证明 Claude Code request 数仍为 1。
- 注入不可归因错误，证明先 poison、再终止 fake harness，后续请求数不增加。
- 取消 handler，证明 `/abort_request`、capture rollback、Outcome 三方对账。
- deadline 剩余 5 秒时拒绝开启 60 秒 wait 的负测试。

### FA-5 同版本容器

- 用实际部署 tarball 重跑 60/120 秒、500、断连和部分 SSE。
- 实测 pause_generation 是 abort 还是 hold。
- 验证真实 Claude Code 进程被 execution owner 主动终止，不靠 HTTP 状态码自退。
- 对账 model request 数、SGLang rid/abort_request、ModelCallAttempt、capture 和
  RolloutAttemptOutcome。

## 7. 复跑命令

在 `rh2/` 下执行：

```bash
python3 experiments/fa_bringup/claude_code_http_probe.py \
  --scenario delay_success --delay-seconds 60 --process-timeout-seconds 75

python3 experiments/fa_bringup/claude_code_http_probe.py \
  --scenario http_500 --process-timeout-seconds 20

python3 experiments/fa_bringup/claude_code_http_probe.py \
  --scenario partial_sse_disconnect --process-timeout-seconds 20
```

每次结果都包含 CLI 版本、请求时间线、body digest、是否由探针终止、退出码和
经过白名单提取的 `api_retry` / 最终 result 字段；不保存原始 stdout/stderr，
不记录 token、完整 prompt、session id 或本机绝对路径。
