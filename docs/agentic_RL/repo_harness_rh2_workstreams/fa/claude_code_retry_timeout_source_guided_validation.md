# Claude Code 重试与超时：源码引导的本地验证

> 日期：2026-07-13  
> 源码参考：`reference/claude-code-typescript-src` 本地快照  
> 黑盒客户端：Claude Code `2.1.205`，macOS arm64  
> 可重复套件：`rh2/experiments/fa_bringup/claude_code_http_probe_suite.py`  
> 机器证据：`fa/claude_code_http_probe_evidence/source_guided_suite/`

## 1. 最终结论

源码快照与黑盒实验共同证明，RH2 可以显著收窄 Claude Code 自己的重试面：

```text
CLAUDE_CODE_MAX_RETRIES=0
CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1
CLAUDE_CODE_UNATTENDED_RETRY=0
```

在当前 `2.1.205` 二进制上，以上配置使 `500`、`429`、响应头前断连和流式
响应中途断连都只产生一次 `/v1/messages` 请求。它应成为正式训练子进程的强制
环境，而不是 FA-5 临时调试参数。

但这不是绝对的“零额外请求”保证。流式请求创建阶段收到 `404` 时，Claude Code
仍会立即转为一次非流式请求；即使 `MAX_RETRIES=0` 且
`DISABLE_NONSTREAMING_FALLBACK=1`，请求数仍为 2。源码也显示，这条 `404`
fallback 分支没有检查禁用变量。

因此正式设计仍必须保留：

```text
session poison + RolloutExecution 主动终止 + request/turn 身份去重
```

环境变量只是第一道减负防线，不能取代服务端可控的不变量。

## 2. 源码确认的机制

### 2.1 普通 API 重试

`services/api/claude.ts:1778-1785` 将 Anthropic SDK 的 `maxRetries` 设为 0，
Claude Code 改用 `services/api/withRetry.ts:170-516` 自己重试。

默认行为是：

```text
最大重试数：10，即最多 11 次请求
基础退避：500ms
指数退避上限：32s
随机抖动：0%~25%
```

`withRetry.ts:696-786` 表明连接错误、408、409、符合条件的 429、401、特定
403 和 5xx 等均可重试。`x-should-retry: false` 对 external build 的普通 5xx
有效，但连接断开时不存在该响应头，所以只能作为附加防线。

`withRetry.ts:789-796` 读取 `CLAUDE_CODE_MAX_RETRIES`。代码只做 `parseInt`，
没有验证 NaN 或负数，因此 RH2 必须写入并检查精确字符串 `"0"`，不能允许任意
用户值透传。

### 2.2 流式中断后的非流式 fallback

`claude.ts:2464-2502` 显式说明流式中断后转为非流式请求可能造成工具重复执行，
并由 `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` 控制。

但是 `claude.ts:2607-2666` 的“流式请求创建阶段返回 404”分支不检查这个变量，
会直接执行 `executeNonStreamingRequest()`。本轮黑盒实验复现了该例外。

### 2.3 请求超时与流式 idle timeout

`services/api/client.ts:141-145` 的 API client 默认 timeout 是 600 秒，可由
`API_TIMEOUT_MS` 修改。实验确认：`API_TIMEOUT_MS=1000` 时，服务端完全不发送
响应头，当前客户端约一秒后取消，且在 `MAX_RETRIES=0` 下不再发第二条请求。

但在已经收到 `message_start` 后让 SSE body 永久停住，`API_TIMEOUT_MS=1000`
不能终止请求；三秒探针窗口结束时仍需外部 SIGTERM。它与源码注释一致：SDK
timeout 主要保护初始 fetch，不可靠地覆盖流式 body idle。

源码还有：

```text
CLAUDE_ENABLE_STREAM_WATCHDOG=1
CLAUDE_STREAM_IDLE_TIMEOUT_MS=<毫秒>
```

但 `2.1.205` 黑盒中将 idle timeout 设为 1000ms 后，五秒内仍未退出。探针已改用
HTTP/1.1 chunked framing排除常见的 body 缓冲问题，结果不变。二进制字符串确实
包含这两个变量，因此目前只能登记为“源码意图与当前行为不一致”，不能把
watchdog 当作正式正确性依赖。

### 2.4 external build 与源码快照并不完全相同

源码中的 unattended persistent retry 受 build-time feature 控制。当前
`2.1.205` external binary 中找不到 `CLAUDE_CODE_UNATTENDED_RETRY` 字符串，说明
这段代码被 tree-shake；显式设置为 `0` 无害，但不能据此宣称当前 external build
真的执行了这项检查。

二进制还含源码快照未出现的环境变量，进一步证明本地源码只能用来设计实验，
不能替代固定版本的黑盒验收。

## 3. 本轮实验结果

| 场景 | 防线 | 请求形态 | 结果 |
|---|---|---|---|
| 延迟 1 秒后成功 | 三项防线 | `stream=true` × 1 | exit 0 |
| HTTP 500 | 三项防线 | `stream=true` × 1 | exit 1 |
| HTTP 429 | 三项防线 | `stream=true` × 1 | exit 1 |
| 响应头前断连 | 三项防线 | `stream=true` × 1 | exit 1 |
| 部分 SSE 后断连 | 三项防线 | `stream=true` × 1 | exit 1，无非流式 fallback |
| HTTP 404 | 三项防线 | `stream=true` × 1，随后 `stream=false` × 1 | exit 1，确认例外 |
| HTTP 500 + `x-should-retry:false` | 默认 retry 配置 | `stream=true` × 1 | exit 1 |
| 响应头前挂起，`API_TIMEOUT_MS=1000` | 三项防线 | `stream=true` × 1 | 客户端主动结束 |
| 部分 SSE 后挂起，只有 `API_TIMEOUT_MS=1000` | 三项防线 | `stream=true` × 1 | 3 秒后仍挂起，探针终止 |
| 部分 SSE 后挂起，watchdog=1000ms | 三项防线 | `stream=true` × 1 | 5 秒后仍挂起，探针终止 |

套件执行结果：`hard_pass=true`。这里的 pass 表示 `2.1.205` 行为与预注册画像
一致，不代表 `404` fallback 或 watchdog 不生效是我们期望的产品行为。

## 4. 版本冻结事实

本机被测二进制：

```text
version = 2.1.205
macOS arm64 sha256 = 33e28624c5ae84f2bd7d2d8761e5d2e77997ba965cb11b6448de6b6e2c566f9c
签名主体 = Developer ID Application: Anthropic PBC (Q6L2SF6YDW)
```

精确下载的 Linux x64 平台包：

```text
package = @anthropic-ai/claude-code-linux-x64@2.1.205
sha256 = d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4
npm integrity = sha512-VkmVjAIW28gZ0ef+uEBJxEkzQbKVulRY789mbMALJ8Zvb6nG0pl+ykGOdF1CQnRR7wmm+rR+EoiuhnFWu59D/Q==
```

当前 `experiments/s1_7a_bringup/host_launch.sh` 仍读取 npm `latest`，并在 volume
已有 tarball 时不重新核验版本。这不满足 FA-5 可复现性要求，应改为固定
`2.1.205`、校验 SHA-256、核对 bootstrap/platform 版本一致，并在容器内执行
`claude --version` fail-fast。

## 5. 对 RH2 实现的直接要求

### 5.1 子进程环境必须成为硬契约

当前代码只强制合并 `DISABLE_COMPACT=1`。应把它升级为统一的 Claude Code
训练守卫：

```json
{
  "DISABLE_COMPACT": "1",
  "CLAUDE_CODE_MAX_RETRIES": "0",
  "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": "1",
  "CLAUDE_CODE_UNATTENDED_RETRY": "0"
}
```

启动 inspector 必须验证真实 Claude Code 子进程收到精确值。任何值缺失、被用户
覆盖或无法验真都应 fail-closed。

### 5.2 Adapter 不得返回 404

RH2 model adapter 的所有路径都不应以 404 表示 session、route、model 或内部
状态错误，因为当前版本会绕过 fallback 开关再发一条非流式请求。

不可归因故障的主路径仍是：先 poison session、通知 execution owner 终止
harness，再关闭当前请求。若技术上必须发出 HTTP 错误，使用非 404 状态并附
`x-should-retry:false`，但它不能替代 poison/cancellation。

### 5.3 Timeout ownership

`API_TIMEOUT_MS` 只能作为 Claude Code 进程级外层保险。每个 execution 启动时可
根据 episode 预算设置它，但 RH2 proxy 的绝对 deadline 必须更早到期并保留清理
时间：

```text
proxy_deadline < Claude API timeout < harness hard-kill deadline
```

正确性不能依赖未验证的 stream watchdog。当前 slime adapter 在完整模型结果返回
前不向 Claude Code 发送 SSE，因此正式链首先要保护的是响应头前等待、client
cancellation、SGLang abort 和 capture rollback。

### 5.4 仍需保留服务端防线

即使关闭客户端 retry，也必须实现并测试：

```text
session OPEN -> POISONED 原子转换
RolloutExecution 主动取消 Claude Code / sandbox
同 session 的 request_id / logical_turn_id 去重
非零 harness exit 强制 execution 缺员
client cancellation -> SGLang abort -> capture abandon
```

## 6. FA-5 前与 FA-5 中的测试边界

本地必须先完成：

1. 真实 adapter handler 中，proxy 内部 abort 后重生成仍只对应一个 Claude Code
   HTTP 请求。
2. 环境守卫确实进入子进程；删除任一变量时 inspector 红灯。
3. adapter 任何路由均不返回 404。
4. cancellation、poison、harness 终止、capture abandon 四方对账。
5. 非零 Claude Code exit 不允许已有 partial trace 继续评分或训练。

FA-5 使用固定 Linux tarball 重跑：

1. 本套件全部场景，确认 Linux x64 与 macOS arm64 的行为差异。
2. 60/120 秒单请求透明等待。
3. 真 SGLang request id、`/abort_request`、ModelCallAttempt 和 Trace 对账。
4. watchdog 只作诊断，不作为闸门正确性的唯一依据。

## 7. 复跑命令

```bash
python3 rh2/experiments/fa_bringup/claude_code_http_probe_suite.py \
  --claude-bin /Users/roger/.local/share/claude/versions/2.1.205 \
  --expected-version 2.1.205 \
  --expected-sha256 33e28624c5ae84f2bd7d2d8761e5d2e77997ba965cb11b6448de6b6e2c566f9c \
  --evidence-dir docs/agentic_RL/repo_harness_rh2_workstreams/fa/claude_code_http_probe_evidence/source_guided_suite
```

这个套件是版本画像和 drift detector。未来升级 Claude Code 时，应先生成新的证据
目录并人工裁决差异，不能直接改掉旧版本的期望值让测试变绿。
