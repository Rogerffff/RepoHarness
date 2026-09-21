# Moto 零分审查 / Codex / 2026-09-19

只读本次已回传的原始日志、账本、宿主采样和冻结题目；没有重跑容器、修改评分或覆盖历史证据。完整覆盖 **67 条零分：59 条 noop、8 条 gold**，同时回读每题 gold 对照。其它 campaign 没有 Moto。

## 结论

| 本次分类 | 行数 | 含义 |
| --- | ---: | --- |
| 有任务缺陷证据，未见额外测试执行/参考映射问题 | 45 | 目标 F2P 的业务错误实际出现，足以解释 0；不表示安装完备。其中 32 条的安装段仍失败。 |
| 有任务缺陷，同时混入其它执行或参考契约问题 | 14 | 目标负信号存在，但同次还有参考 ID、外部服务或参考集外运行问题。 |
| 零分由环境/参考映射解释，不能当成 gold 未修复 | 8 | 5 条 Unicode ID 不匹配、2 条 EC2 DNS、1 条 Batch 缺 Docker 服务。 |

**59 条 noop 的 102 个 F2P 都有实际 FAILED 状态；没有 F2P 仅因 MISSING 被计失败。** 逐条 traceback 已与题面缺陷/gold 变化核对。不过 Moto-7105 多个用例在 mock 装饰器的 reset 中就失败，不能称测试正文全部执行；这里 reset/join 正是题目要修的缺陷。4799 同一参考有 call FAILED 与 teardown ERROR 两个真实阶段，不能当成 stdout 伪造。

逐条结果：`runs/full216_rh2_diagnostic_20260919/zero_audit/moto/reviewed_rows.jsonl`；包含每个参考 ID 的状态和原始行号、失败解释、同题 gold、安装问题是否致分、宿主采样、未证实部分。`summary.json` 和 `build_audit.py` 保存计数与核对方式。67 个键与全量账本精确一致，parser 重放计数全部一致。

## 哪些 0 混入了什么

| 题号 | 直接证据与解释 |
| --- | --- |
| 4799、4833 | noop 的 bucket 生命周期错误是真实题目缺陷；但 noop/gold 的两个 P2P 都请求 `ec2.us-west-1.amazonaws.com`，发生 DNS/EndpointConnectionError。gold F2P 全过，0 完全来自这两个环境失败。 |
| 5417、5545、5562、5701、6308 | noop F2P 有真实错误；gold F2P 全过，却因一个 P2P Unicode ID 缺席得 0。实际输出能看到同一参数用例以 `\U0001f4a9` / `\xee` 转义形式 **PASSED**，不是没执行测试。 |
| 4975、5347 | 参考外两个 EC2 no-warning 用例用 `pytest.warns(None)`，当前 pytest 8.3.2 抛 TypeError；noop/gold 都出现。目标 F2P 仍独立说明 unhashable list / 多余 KeyName 缺陷。 |
| 5980 | 同名 no-warning 用例已换捕获方式，但 Python 3.12 的 `datetime.utcnow()` DeprecationWarning 被升为异常；noop/gold 都出现。目标 F2P 的标签过滤错误是独立事实。 |
| 5134 | 参考外三个 SQS 集成用例在 `create_queue(...)["QueueUrl"]` 失败，noop/gold 都出现；精确版本/协议原因尚未确定。不能把合法 EventBridge 负信号一起否掉。 |
| 5562、5701 | 另有四个参考外 S3 上传/预签名用例抛 IncompleteRead / ChunkedEncodingError，noop/gold 同现。尚未证明是公网依赖或哪个库版本造成。 |
| 6121、6157 | 参考外 CORS 用例解析 `testcors.localhost:6789` 失败，gold 虽得 1，整套测试并未全绿。这是本地服务/名称准备缺口，不能据此开放公网。 |
| **7105** | noop 的 `cannot join thread before it is started` 与题面及 gold 的 `is_alive()` 修复一致。gold 剩余 F2P `test_cancel_pending_job` 在 `statusReason` 处失败；同一段先记录 Docker API `FileNotFoundError`，前置 Job 无法启动，依赖 Job 提前失败。另有 10 个参考外 Job 用例同样受影响。 |

Moto-7105 的关键原证据：noop 日志 `.../baseline01/workers/w05-1/eval_logs/evallog_replay-f216-baseline01-w_1e377be4.eval.log` 第 535–593 行呈现 reset/join；gold 的 `..._2e98e36e.eval.log` 第 781–817 行呈现 `@requires_docker`、依赖任务设计、缺 `statusReason` 与 Docker 启动失败。这里已经比“Job 状态波动”更具体，但仍需补齐隔离 Docker 服务后小批复验，不能直接挂宿主 socket。

## 安装与资源的独立判断

**39 条零分记录有安装失败：37 noop、2 gold。** `make init` 的隔离构建尝试联网获取 `setuptools>=40.6.0`，DNS 失败后 make rc=2，脚本继续 pytest。其余 28 条零分日志有成功安装和 rc=0。本次没有发现“安装 rc=0 掩盖内部安装失败”的 Moto 反例。

这 39 条不能统称“安装失败造成 reward 0”：37 条 noop 有更直接的实际业务失败；两条 gold 分别由参考 ID 和 Docker 服务解释。对照表明源码变更可以被当前可编辑安装读到，但**没有验证依赖或构建文件变更也能生效**，这仍是下一轮安装敏感候选的验收项。

67 条零分的日志没有 OOM、PID 耗尽、磁盘耗尽或评分超时签名。已有宿主采样中最大 PID 数为 8，未观察到 OOM/oom_kill；sidecar 缺完整终止资源事实，轮询之间的事件不能被严格排除。不要把这些零分称为“完全排除所有资源问题”，也不要因为未知事实就否定已经可见的业务断言失败。

建议先修/准备 **7105 的隔离 Docker 服务、6121/6157 的本地名称/服务、三类兼容性问题与离线构建依赖**，分别用小对照验证。Unicode ID 的规范化仍涉及来源契约，应由既有决策流程处理。本审查不改变参考集合、二值 reward 或训练池准入。
