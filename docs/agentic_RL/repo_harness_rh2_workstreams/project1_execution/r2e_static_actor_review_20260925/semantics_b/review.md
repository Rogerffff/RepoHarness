# R2E 四题语义与评分证据独立复核

Codex，2026-09-25。范围：numpy `18b7cd9d`、aiohttp `61833518`、pillow `2b061b68`、scrapy `9a15fcf8`。仅审查；没有改题面、材料、生产代码、维护测试或原始 evidence；没有运行 Docker、远端或网络，也没有扩大取题范围。

**结论：评分数值与主要漏测结论成立；有两处诊断归因需要收窄。** pillow P1 证明“遵循冲突示例的候选被拒”，不能无条件计为满足公开要求的合理修复；scrapy A′ 的两键翻转模式只能定位疑似期望冲突，不能直接免除模型失败。numpy 与 aiohttp 仍可作为附条件的诊断探针候选；aiohttp 的后检条件须落实为完整的分块与解压检查，现有 C3 前缀检查不能代替它。以上不构成训练或正式 actor 准入批准。

## 1. 范围与证据口径

本报告路径均相对仓库根。简写：

- `R/`：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/`
- `P/`：`runs/r2e_static_prep_20260924/v2/`
- `G/`：`runs/r2e_actor_20260925/grader/`
- `D/`：`runs/r2e_actor_20260925/devcheck/`
- `P4/`：`runs/r2e_env_repair_20260924/p4/`

已读根 `AGENTS.md`、审查标准、协作协议、当批入口，四题公开需求和相关 base 源码、公开/隐藏测试差异、gold、候选补丁、题卡/复核/记录及相关原始运行件。gold 仅作参考实现；语义依据来自题面、base 和公开测试。不是重演一次盲审角色链；本次审的是已经形成的结论与证据。

适用维度：A/E（行为正确性、断言区分力）；B/F/H/I/M（评分归因、用途、记录与证据层次）；N（Python/pytest、材料与镜像版本）。C/D/G 的平台准入和生产接线由主审负责，本子审只核已有逐命令证据；J/K/L 不作新实现质量或性能验收，因为没有实现变更。

只读审计脚本与结果：[`evidence_audit.py`](evidence_audit.py)、[`evidence_audit.json`](evidence_audit.json)。独立去色、抽取日志测试状态，重算匹配数与 reward，并核对补丁/日志 SHA、隐藏文件/入口摘要、两个候选副本、投影路径。**12 条本批行 + 1 条旧 P4 行全部一致**。具体完整路径、SHA 和 devcheck 输出引用都在 JSON 中。

补充 CPU 探针：[`semantic_probe.py`](semantic_probe.py)、[`semantic_probe.json`](semantic_probe.json)。本机 Python 3.12.13；aiohttp 只解析已有输出，Scrapy 仅执行原件 AST 的纯 Python 节点，响应类用相异类型标记、six 用必要属性桩。**不是容器重跑，也不是新增真实评分。**

## 2. 两项需修正的归因

### B1 · P2：pillow P1 的“合理误拒”只能附带题面读法

- **当前表述与定位**：`R/README.md:49,87` 将 pillow 回退候选与明确的合理修复并列为“误拒已由执行证实”；`R/grader_candidates.md:85` 虽补了“满足题面示例的字面说法”，仍将其计入“这些实现都满足题面字面要求”的总数。
- **违反的边界**：运行能证明得分；不能从相互矛盾的公开要求中选取一个分支，再把该分支无条件当作正确规范。
- **证据**：`P/public/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/user_prompt.txt:7,13` 明说限制格式；`:14,24` 又要求 PNG 配 `['JPEG']` 的示例成功。P1 补丁 `G/cands/pillow_2b06_P1_fallback_to_all_formats.patch:49-51` 在列表不匹配时尝试整个 `ID`，遵循了示例读法，却取消了“限制”的效力。P1 也没有加入题面 `:26` 所述的无参 `show()` 警告；这进一步说明“完全满足字面要求”不成立。
- **已验证事实**：`G/ledger_pil_P1.jsonl:1` 为 reward 0、54/55；对应日志 `evallog_replay-9da9b69fb074-pill_f97c21e5.eval.log:38-43` 只在 PNG/`['JPEG']` 应抛异常的断言失败。不是执行错误。
- **最小反例**：同一 PNG/`['JPEG']` 调用必须在“只接受 JPEG”与“成功打开 PNG”之间选择；P1 不能同时满足两者。无需另跑容器即可成立。
- **影响与分期**：本轮汇总前修正文案和计数口径，防止把已证实的题面冲突升级成无争议的评分误拒。保留 `needs_review`、诊断用途和 T0-3 不变。
- **最小验收**：分别记录“P1 得 0 已执行”“P1 对应示例优先读法”“公开要求本身矛盾”。若列确定合理误拒总数，应把 P1 单列为争议解；如仍计入更宽口径，必须明确分母包含这种争议解。由用户决定公开规格后，再判对应候选合规；不需要为改这句结论重跑 P1。

### B2 · P2：scrapy A′ 不能只靠两键翻转判定合理修复

- **当前行为与定位**：`R/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/card.md:91`，以及同目录 `screening_record.json:369`：reward 0、只有两键 FAILED→PASSED，就记“过度修复误判”“不算失败”。review 补充的“只改库源码、没碰 fixture”仍不足以证明行为正确。
- **违反的不变量**：评分诊断不能把破坏公开旧契约的源码修改自动归为正确修复。
- **反例**：加 x-json 表项，同时把 `scrapy/http/headers.py:26` 的
  `return [self._tobytes(x) for x in value]`
  改成
  `return [self._tobytes(x).decode(self.encoding) for x in value]`。
  这是只改源码、直观地消除 str/bytes TypeError 的做法；但破坏 `normvalue` 的 bytes 约定（`:18`）及公开 `tests/test_http_headers.py:28-30` 的返回 bytes 断言。
- **CPU 证据**：隔离执行的 base/gold/P4 对照与已有真实结果的状态模式一致。上述 `bad_headers_str` 变体使七个隐藏测试方法全部通过，而公开 `HeadersTest.test_single_value` 失败：`'text/html' != b'text/html'`。对当前期望图重算仍是 reward 0、恰好两键不符，完全命中 A′。这里只有原件 AST 隔离证据，**没有声称新变体已获真实 RH2 分数**。
- **真实参照**：P4 的合理候选在 `from_content_type` / `from_content_disposition` 边界解码 bytes，保留 Headers 契约。其真账本和日志核对通过（§3）；它不能证明所有相同状态图的补丁都同样合理。
- **影响与分期**：在用 A′ 汇总模型诊断前修正。否则“修掉了不该保留的失败”与“为消除失败破坏 API”会被合并，能力失败可能被错误豁免。
- **最小验收**：两键模式先记“疑似期望死键冲突”，保留 raw reward；核补丁只修正输入边界、未改测试控制面，且保留公开 bytes 契约后，才可判合理误拒。如果候选涉及 `Headers`，至少核 `test_single_value` 这条明确契约。P4 应被确认；上述 str 变体应被拒绝豁免。T0-4 的 B/D 选择无需因此重开。

## 3. 四题逐项核对

| 题 | 评分与行为证据 | 判断及边界 |
|---|---|---|
| numpy `18b7cd9d` | 本批 gold/A/D/N/I = **1/1/0/1/1**。D 10/11，唯一不符 `test_poly_eq`；其它均 11/11。行为输出 gold/A 为 `False True False True`；D 的 `p != None` 为 False；N 的 `p == 3` 抛 AttributeError；I 的等值不同对象比较为 False | N、I 是有公开依据的错误实现得 1；D 得 0 有依据，不是误拒。A 证明至少一种与 gold 返回协议不同的合理替代解能通过，不能外推“没有任何误拒” |
| aiohttp `61833518` | gold/AP1/AP2 均 **1、47/47**。AP1 只修 length 写出器；C3 输出先有终止块再有正文。AP2 修 length/chunked 两个写出器；gold/AP2 的捕获正文经本次分块与解压检查恢复 `b'data'` | AP1 的漏测成立。隐藏测试 `test_1.py:427-477` 新增三处 `all(chunks)`，有压缩置后时都走 Content-Length 路径；覆盖不到压缩末端向 chunked 写出器输出空数据的场景。AP2 没改 EOF 写出器，不应描述成所有写出器修复 |
| pillow `2b061b68` | gold/P1/P2/P3 = **1/0/1/1**，分别 55/55、54/55、55/55、55/55。P2 在 fresh PNG/TIFF 检查均报 UnidentifiedImageError，gold 正常。P3 的 show 警告改动仍满分 | P2 是明确旧行为回归得 1；P3 违背公开 `Tests/test_image.py:768-770` 的无警告约定，但评分测试在 `pytest.warns(None)` 处失败、恰好符合 FAILED 期望。P1 见 B1；不能用 gold 的实现作为消除题面冲突的依据 |
| scrapy `9a15fcf8` | **本批 grader 行为 0 条**。引用的是旧 `P4/ledger_overfix.jsonl:1`：开始时间 2026-09-23T18:48:15Z，单次、源码候选；实际七键全 PASSED，期望匹配 **5/7、reward 0**，只有 from_args/from_headers 两键不符 | P4 合理误拒成立，原件未变，属于历史证据复核。`P/private/.../expected_output.json` 的两键是 FAILED；`P/public/.../worktree/tests/py3-ignores.txt:40` 原本忽略整文件，R2E 搬迁后进入评分。没有本批 over-fix 重跑，也没有修订 B 的真实验收；B 目前仍是待用户决定的建议 |

12 条本批行全部只有对应库源码进入投影，测试/fixture 改动字段为空。log SHA 与账本一致、日志状态重解析与匹配数一致；不能把 P4 的旧一条算入本批 26 次新评分。P4 本次核的是相同隐藏文件、入口与观察状态图；旧账本未直接记录 expected 摘要，对所用期望版本的判断仍含“当前材料/当时无本题修订/不符模式一致”的推定。

### numpy 的附条件探针

建议方向合理。公开题面要求非 poly1d 比较不崩溃，base `polynomial.py:1201-1207` 给出系数按值比较与 shape 检查；额外检查 plain `object()`、等值不同对象、不同长度，依据充分，不必模仿 gold 返回 NotImplemented。

最低判读集合可沿用 reviewer 的七项：`p == None`、`p != None`、`None == p`、`p == 3`、`p == object()`、`p == P([1,2,3])`、`p != P([3,4])`；期望 `False True False False False True True`。逐项捕获异常，记录返回类型；允许 Python bool 和 numpy 标量 bool，不能仅凭打印像 False 就接受数组。现有四项探针确实在 N 的第三项中断，扩展版尚无本批真实执行件。它是后续诊断条件，不是已经完成的证明。不要新增“`__eq__` 必须返回 NotImplemented”或未澄清的 ndarray 比较规格。

### aiohttp 的附条件探针

方向合理，**现有实跑 C3 与拟采用的语义 C3 需要区分**。`rh2/experiments/r2e_actor_20260925/commands/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2.json:21` 仅断言正文不以 `0\r\n\r\n` 开头。它抓住了 AP1，但空正文、错误载荷、缺终止块也会通过；本次 CPU 反例均复现。

首次按 C3 生成“校正结果”前，应真正解析分块帧，确认唯一正常结束、无终止块后的遗留数据，并把 deflate 数据完整解压为原载荷；若检查空 `transport.write`，另外保留逐次实参，不能从拼接正文反推。避免要求分帧或压缩字节逐字等于 gold。本次同一合法压缩流改为 2+4 分帧仍通过语义校验，说明按 gold 字节相等会过度约束。README 已采纳“语义化 C3”，但本题 `screening_record.json:452` 仍建议“正文精确等于 gold”，应以最新条件统一。

本次对已有正文的检查：gold/AP2 通过、AP1 在终止块后仍有数据而失败；这增强已有反例解释，不能替代在未来模型补丁上执行完整 C3。仍应分列 raw reward 和后检结果。兼容改写回退导致的 import 失败必须由实际日志定位到 `client.py`/`client_reqrep.py` 后归因，不能仅因修改过这些文件就豁免模型失败。

## 4. devcheck 与 T0 建议边界

四题的 `orig/attempt.json`、每条 captures 和 `private_gold/private_control.json` 都核过：base 是 uid 54321，Python 为 `/testbed/.venv/bin/python`，CC 2.1.205；base/gold/overlay 镜像 ID 相同；三项预检标记为 ok；清理记录无残留。`all_match_expect` 含 `expect=any`，因此本报告依据逐命令输出判断，不把它本身视为语义验收。

| 题 | base→私有 gold 的公开命令结果 |
|---|---|
| numpy | 原例 AttributeError→False；公开 polynomial 10→10 过，regression poly 9→9 过；gold 的其它比较输出与汇总一致 |
| aiohttp | C2 有空写→无空写；C3 提前终止→正常正文；http_protocol 47→47 过，邻近测试均 3 败68过，三败均 cookie 断言 |
| pillow | 原例因缺 formats 报 TypeError→因格式不符报 UnidentifiedImageError；JPEG正例 TypeError→JPEG；公开测试均2败52过，失败来自 pytest 8.3.4 的 warns(None)；viewer列表空 |
| scrapy | 原例 Response→TextResponse；显式公开测试均2败5过，两败为 bytes/str TypeError |

这些与 `R/actor_devcheck.md:39-46` 一致。gold 是明确标注的 root 私有对照，不能算“agent 已应用补丁”；没有 Qwen adapter、真实求解或正式完整消息证明。本子审不代替主审的 actor 接线验收。

T0 建议的证据充足性：

- **pillow T0-3**：足以要求先消除公开题面矛盾，也足以保留原题仅诊断。严格限制是有公开依据的修订方向；需由用户选择并版本化。仅改题面仍消除不了 P2 首次打开回归，也恢复不了两个警告断言的保护。不要以“gold 暂时做不到”为理由裁剪新规格；例如修订后若承诺一般的受限格式识别，示例避开 TIFF 并不能消除 gold 在插件未加载时的 KeyError，至少应如实保留参考实现限度。
- **scrapy T0-4**：P4 足以支持修订 B（对称删除两个无有效保护的键）或隔离 D。只删 expected 会产生 unexpected 键，不能解决问题。B 的最小验收应在修订材料上核定实际键集为五键，再核 noop=0、gold/P4/只解码 content_type 的候选=1；现有旧日志离线重算不能冒充该验收。B 也不会自动新增 Headers 契约保护，仍需保留覆盖边界。
- **numpy**：已证实两类漏测；诊断用途可用补丁后检承接，训练前是否修订测试由用户定。不为简单诊断引入额外全池闸门。
- **aiohttp Q2**：标题和描述直接支持 chunked+deflate 场景，补语义测试不扩大原问题。训练用途不能继续让 AP1 拿满分；修订后须以原 47 键及新场景验证 noop/AP1=0、gold/AP2=1，并保留上游与修订版口径区别。

## 5. 记录一致性与未验证范围

原题卡/结构化记录尚未全部吸收各自 reviewer 已提出的更新：numpy 的 N/I 仍标静态、A/D/N/I 仍“待评分”；aiohttp 仍写待 AP1/A1、gold 精确字节判据；pillow/scrapy 仍留旧 actor 状态。主审可统一做当前结论索引或勘误，不能回写封存初判。复核期间批次 README、grader_candidates 与 actor_devcheck 出现了并发更正；本报告定位按落盘前读到的版本，文档摘要保存在 `evidence_audit.json`。

本子审没有新增这四题的真实容器评分，没有检验模型实际写出这些候选的概率，没有重审跨题污染全池、未开展正式训练准入。除了 B1/B2 的归因收窄和后续 C3 条件落实，没有发现推翻 numpy/aiohttp 附条件诊断候选、或推翻 pillow/scrapy 仍需处理的证据。

复跑本次只读核对（仓库根）：

```bash
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/semantics_b/evidence_audit.py
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/semantics_b/semantic_probe.py
```
