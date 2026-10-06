# aiohttp4075：评分修订验收通过，公开复现仍需修正

2026-09-29，Codex 本地独立读回。题目：`aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`。

**结论：v11 的 R-c 评分修订可验收，不必重跑七方矩阵；本题目前仍留第2类。** 当前公开原例1有已证错误，会影响合理复现，必须先做窄 R-f，再核实际公开交付。不能照旧卡把此项写成“可选、不阻塞”。这不推翻已完成的评分修订，也不把 R2E 的 expected FAILED 改成全 PASS。

阅读边界：开工已接触起始分类摘要和修订材料；随后先核公开原文、实际断言、候选补丁、七份正式原日志及 actor 开发原件，再对照旧独立审查结论。因此本报告是独立证据复核，**不是 fresh 公开阅读，也不是 fresh 求解**。本轮没有 SSH、启动容器或运行模型，没有覆盖旧卡、旧分数、共享看板或生产源码。

## 已独立核实的事实

正式证据根目录：`runs/r2e_lifecycle_20260929/codex_status_check_20260929_1020/formal_v11/`。本轮从七份完整 eval log 的逐测试状态重建 observed，按当前 expected 精确比较；不是只采用 `status.json`、退出码或作者摘要。可复算结果、每份日志路径及 SHA256 在 [r2e_inventory.json](r2e_inventory.json) 的 `aiohttp4075_log_recomputation`。

| 候选 | 正式槽位 | 状态匹配 | reward | 不匹配原因 |
|---|---|---:|---:|---|
| ALT2，主正对照 | s1 | 136/136 | 1 | 无 |
| ALT1，备选正对照 | s2 | 136/136 | 1 | 无 |
| ALT3 | s4 | 136/136 | 1 | 无；仅作解法空间对照，不宣称完整 HTTP 正确性 |
| ALT4 | s5 | 136/136 | 1 | 无；同上 |
| 原 gold | gold | 132/136 | 0 | 请求目标中的 LF、FF、CR、TAB 四键均 `DID NOT RAISE BadHttpMessage` |
| noop | noop | 131/136 | 0 | 非 ASCII 字段名两键、原请求行以及 FF/VT 分隔共五键未抛预期异常 |
| DG1，只拒题面字面样例 | s3 | 134/136 | 0 | 非示例字段名与 VT 分隔两键未抛预期异常 |

七份日志的字节 SHA256 全部与正式 ledger 一致；每份均有真实测试段起止、`RH2_TEST_RC=1` 和对应完整失败回溯，键集恰好相等，无 missing/extra。每行测试段均完成，`reference_missing_count=0`，`runner_integrity_changed=false`，`cleanup.removed=true`，候选投影只有 `aiohttp/http_parser.py`（noop 无修改）。七方配对结果不依赖脚本退出0：全体 pytest 都退出1，因为三个 C 扩展缺失键在该环境仍按 expected 记 FAILED。

这些原件把旧草案中“因试跑只留尾部而推定失败行”的限制消掉了。gold 的四项失败正是新断言要拒绝的请求目标回归，不能为保 gold 得1而放宽；环境正对照必须改用 ALT2，ALT1 作为备选。

## 材料与正对照身份

本轮直接对照当前 `s2_r2e/ingest/grading_bundles_r2e_v0.jsonl` 本题行及日志头：

- 修订号：`r2e-mr-061`、`r2e-mr-062`。
- 修订后 `test_1.py`：`sha256:ec2c29858ae4e71575f76864e994116ba2af1ff952a6c70a3df2045e720a8cfa`。
- 隐藏测试树：`sha256:3ff70876554bee932635b48cbf85bd988ac5b83df3e46a871b29ca1418d210d4`。
- 正式 expected 文本：`sha256:fdabd74b34e463b84e09abb2998b33ee5a7906fa2e7d662673ba73d376880491`，136键，133 PASSED＋3 FAILED。试跑文件序列化摘要不同不等于映射不同；本轮按实际映射重算。
- 测试入口：`sha256:8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`。
- 正式与 actor 镜像：`sha256:dbe77bf048e1e03d02ab678c2a7ef0fc4b5c4042e1d6aebbf4138e562a615e99`。
- 配方：`r2e_derive_v1+material_v2+sysconfig_v1`；正式 ledger 的内容摘要为 `sha256:e139ba5708390eca37d126e49637de55a69348a572e59f0dc914fba0b4e7db32`。
- ALT2：`sha256:f3c6056416e15fa36521dd196f66315cee5cc2197a555d4f8087fcc4304c20c2`；ALT1：`sha256:d3a4b23c79944783ad9abe1fd0d0b26c1fcc5e7e30d62da56605b2211d91f3f8`。补丁原件仍封存在旧结果目录 `cands/`，本轮不覆盖。

旧独立审查 `review_revision_aiohttp_4075_r2.md` 只批准落正式材料；本轮补验的是它要求的正式评分、完整日志与身份一致性。此处确认的是题级评分修订，不是当前机器可立即派发、更不是训练/留出准入。

## 开发路径与合理替代解

actor 原件在 `runs/r2e_lifecycle_20260929/codex_status_check_20260929_1020/devcheck_v11/<本题>/orig/`：7条命令全部执行并符合已登记预期，13项检查全真；身份 `agent/54321`，Python 3.9.21，导入来自 `/testbed/aiohttp/__init__.py`，Claude Code 2.1.205＋桩。解析层和本地 HTTP 服务均复现缺陷；“符合预期”包含复现命令预期非零，不是说 base 已修好。

公开回归结果：parser 文件124 passed、5 skipped、3 deselected；共享 multipart、client_proto、http_exceptions 合计135 passed。缺 C 扩展时公开命令显式设置 `AIOHTTP_NO_EXTENSIONS=1`，让 C-only 公开检查跳过。它是可用的公开开发路径，不冒称 C 扩展已构建或已测。

ALT1/ALT2 的独立于正式评分的公开回归已存在于 `runs/r2e_lifecycle_20260929/inv/aiohttp_4075/pcheck_public_ALT{1,2}.json`：两者都记录 `user=agent`、补丁成功应用，124＋135 passed，脚本 rc0。它们是私有行为对照，不是 fresh 模型求解；镜像为修订前 `f483bab4…`。正式 v11 随后在新材料镜像上接受相同补丁，支持复用开发回归证据。`private_control.json` 的原 gold 检查是 root 身份，不能冒充 actor 正对照。

## 尚未通过的公开复现

当前正式公开 bundle 与 v3 `user_prompt.txt` 仍写：

```python
invalid_header = "\xffoo: bar".encode()
request = f"POST / HTTP/1.1\r\n{invalid_header}\r\n\r\n".encode()
```

这里会插入 bytes 的文本表示，例如 `b'\\xc3\\xbfoo: bar'`，并不发送题面所指的非 ASCII 字段名。actor 原件 `captures/repro_parser_issue_cases.out` 明确显示：`issue_ex1_literal` 在 base 已抛 `InvalidHeader`，而按真实字符串组成的非 ASCII 字段名被 base 接受。公开题面的“两个例子均不抛异常”因此不成立；这不是理论风险。

最小修法已有证据：去掉 `invalid_header` 赋值处第一次 `.encode()`，保留构建整个请求时的编码。它只改复现，不写修法、不增加隐藏输入，也不变原有核心要求。旧 actor base 与 gold 私有对照已分别实测同等请求的失败和修好；正式落 R-f 后应由新公开读者读出同一需求，核实际送达题面与新 hash，并对最终公开命令做与变化相称的 agent 验证。评分材料未变时，不必重复七方矩阵。

## 三个 C 扩展死键怎样处理

三个键是 `test_c_parser_loaded`、`test_invalid_character[pyloop]`、`test_invalid_linebreak[pyloop]`。完整日志分别显示缺少 `HttpRequestParserC` 的断言失败与 NameError；不是核心输入的接受性断言失败。既有 `pcheck_cext_agent.json` 证明没有 `.so`、`vendor/llhttp` 为空，虽有 gcc 和预生成 parser C 文件，离线构建缺少 llhttp 子模块产物。公开开发已验证纯 Python路径。

**本次不因“存在 expected FAILED”单独判评分修订不通过，也不擅自删键。** 在声明的离线纯 Python开发范围内，三键是固定环境事实，ALT1/ALT2 的合理源码修复没有翻转它们；尚无本题合理修法被它们误拒的具体证据。若主线程改变构建/网络条件、允许生成 C 扩展，或发现有依据的合理候选翻转它们，应先恢复或移除对应无效断言并同步 expected，不能把新的翻转当候选错误。该边界与 240da 的相关客户端兼容阻塞不同。

已有 HTTP 全协议覆盖限制（例如字段名 `/`、目标 `\x01`、版本号里的 FF）仍是公开要求范围核定中的已登记项，本轮没有新实验证明它们属于此次两项修复的未收口路径，也不声明已修整个协议实现。跨题答案关联仍要求整仓划分；共享控制面、正式consumer、模型与预算由主线程核对。

## 交付状态

- 已验收：v11 评分修订、136键精确映射、替代正对照、已有公开开发条件与回归证据。
- 必须继续：错误公开复现的窄 R-f、fresh 公开阅读、正式公开版本与实际消息验证。
- 当前分类：第2类；不再写“只差补卡”，但也不重复已结束的七方实验。

所有引用原件的 SHA256 与结构化证据见 [r2e_inventory.json](r2e_inventory.json)。
