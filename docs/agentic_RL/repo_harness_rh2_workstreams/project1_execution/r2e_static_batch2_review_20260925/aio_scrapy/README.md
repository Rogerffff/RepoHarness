# R2E 第二批：aiohttp / scrapy 四题独立复核

日期：2026-09-25。结论：**一项 P2 归因规则需修正；四题已有运行证据的主要语义结论成立。** 原始 reward 保留，不用 gold 或单个失败键定义正确性。

本复核只读题面、公开仓库、隐藏测试、gold / 候选补丁、各角色报告与既有运行材料；本机仅运行附带的材料审计脚本。没有启动 Docker、SSH、网络或项目测试，没有修改实现、维护测试、原始材料、作者报告，没有提交。本文是给主审的四题分报告，不替代全批 81 行账本。

## 路径约定与核验范围

以下缩写均为仓库相对路径，后文 `:数字` 为文件实际行号；JSON 单行字符串中的多行输出仍引用其所在行。

- `B`：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925`
- `G`：`runs/r2e_actor_20260925/grader`
- `C`：`runs/r2e_actor_20260925/grader_cands`
- `V`：`runs/r2e_static_prep_20260924/v3`
- `X`：`rh2/experiments/r2e_actor_20260925`
- `A1`：`aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`
- `A2`：`aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac`
- `S1`：`scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4`
- `S2`：`scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67`

本机执行：

```sh
python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/aio_scrapy/audit_evidence.py
```

结果：31 条本题组正式评分行的补丁 SHA、日志 SHA、当前固定解析器重算的逐键差异集合、匹配数与 reward 均一致；读取 25 条私有诊断命令结果、5 条 cleanup 后检结果。6 次并行 gold 的实际测试时间区间共同重叠 28.610 秒。产物见 [audit_evidence.py](audit_evidence.py) 与 [audit_evidence.json](audit_evidence.json)。这只是**重新解析既有证据**，不是新增 actor / grader / 握手 / 停服执行。私有诊断的 `apply` 成功记录与命令输出已经核对，不把外层退出码当语义验收。

维度适用性：A/E/G/L 深审异常传播、真实 TLS 路径、event loop 和反压；B/F/H/M 深审误拒、漏测、归因和证据口径；D/N 核对补丁身份、镜像与执行环境差异；I 给出分期；C/K 仅审后续诊断使用边界，不新增闸门；J 只审命令/报告含义。本任务没有运行时实现变更，训练链路、资源清理所有权和全系统容量验收不在本分报告范围。

## F1 — P2：不能按 aiohttp 失败键直接归为环境抖动

**当前行为。** `B/results/A1/screening_record.json:312` 建议“若在 RH2 中出现翻转，按环境抖动归因”；`B/results/A1/old_findings_delta.md:66` 同样写法。最终 `review.md:70,85` 已识别 C5 的同键失败来自候选本身，但没有明确撤销这条后续归因建议。

**违反的不变量。** 失败键只能定位检查对象，不能区分启动竞态与实现回归。只有异常、调用栈、发生阶段及必要的同条件对照支持时，才可归因；不能因为历史上同键抖动，自动给新候选免责。

**证据与具体位置。**

1. 原始来源 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl:6` 的 `execution_result_content` 中，old/new 两份日志的 `TestShutdown.test_shutdown_handler_cancellation_suppressed` 都是首次请求连接未就绪导致的 `ConnectionRefusedError`。附带审计保存了异常行。来源路径、pytest-asyncio 插件与当前镜像不同；这些信息本身不能证明来源一定是“裸机”。
2. `C/aiohttp_1c1c_C5_drop_main_cancel.patch:9` 删除 `_cancel_tasks({main_task}, loop)`，保留下一行对所有 task 的取消，破坏主任务先完成清理的顺序。该顺序有公开依据：`V/public/A1/worktree/docs/web_advanced.rst:948` 及 `CHANGES.rst:2076`。
3. `G/ledger_a1c1c_C5_drop_main_cancel.jsonl:1`：补丁 SHA 为 `sha256:a12aaaab59afa158f501008c18f22889c1b91568bfbb777e17b76e7389640a74`，49/56，reward=0。对应 `G/eval_logs/evallog_replay-9ccae004153d-aioh_2c5b8574.eval.log:1361` 已运行完 `web.run_app`，`:1362` 的 `t.exception()` 抛出 `CancelledError`；`:1365` 显示动作已有 `CANCELLED / SUPPRESSED / PRESTOP`，`:1375` 定位到 `test_1.py:1259`。这是同一个测试键的**另一种根因**，不是首次连接未就绪。

**影响。** 按旧建议解释未来记录，可能把真实 shutdown 回归计为环境异常，偏置诊断统计或训练样本归因。当前原始评分没有被豁免：C5 仍是 0；本发现针对后续解释规则，不声称已有自动改分代码。

**建议分期与最小修法。** 本轮报告收口时，由协调者在当前权威结论增加勘误并显式覆盖上述冻结快照建议；无需回写历史材料。建议改为：“该键失败仅作为疑似时序线索；核对异常、栈与发生阶段，必要时做同条件 gold 对照；不得仅凭键名归环境或免责，原始 reward 保留。”后续若要修订等待/重试，仍应先核定真实启动竞态，而非把所有失败一并屏蔽。

**复核命令。** 上述 `audit_evidence.py` 验证 C5 补丁/日志身份及历史来源异常；另读 `sed -n '1353,1378p' runs/r2e_actor_20260925/grader/eval_logs/evallog_replay-9ccae004153d-aioh_2c5b8574.eval.log` 即可看到当前根因。

**验收条件。** 权威结论显式撤销“按该键翻转直接归环境”的建议；历史连接失败与 C5 的取消顺序回归分别记录，C5 保留 reward=0；未来同键但未知根因的失败保持待查，不能自动免责。此项不要求重新运行全套测试。

## 四题语义裁定

| 题目 | 接受的结论 | 本次边界 |
| --- | --- | --- |
| A1 | C3 满分却吞 cleanup 异常；C1 是合理替代；C5 拒绝正确 | 未发现本题合理实现被误拒的实证；6 次并行只支持当前条件下稳定 |
| A2 | K2 / `abort()` 合理替代被误拒；K3 / K4 错误实现满分 | 真实握手与源码足以判定这几份具体补丁，不能推广为任意候选完整正确 |
| S1 | gold 对 None / serializer 返回值引入 TypeError；C2 漏普通 dict 仍满分 | C1 与 RC2 均被接纳；嵌套 key 策略与非字符串 key 需和已证实缺陷分开 |
| S2 | gold 满分却阻断 scraper 收尾；低阈值第二次 fetch 超时；K1 / K1b 合理 | K2 五次稳定失败，未证明永久无时序风险；K3 的 asyncio-await 缺陷仍属静态推断 |

### A1：重复启动异常与 cleanup 异常不能混为一谈

目标隐藏用例 `V/private/A1/hidden_tests/test_1.py:909` 检查启动抛 `RuntimeError("foo")` 且不重复调用异常处理器。C3 采用 `gather(..., return_exceptions=True)` 后 56/56，但将 shutdown 时的新异常也吞掉。既有真实后检 `G/postcheck_b2/a1c1c_C3_gather_swallow.json:8` 的 `check_rc=1`，`:12` 为 fail，`:16` 为 lost，`:17` raised=null，`:18` handler_calls=[]。base 和 C1 会报告，gold 会抛出；接受“抛出或报告”有旧行为和异常不丢失的语义依据，并非只接受 gold 写法。

后检脚本 `X/postcheck/aiohttp_1c1c0ea3_cleanup_error.py:26` 在 cleanup 中注入异常，`:43` 调真实 `web.run_app`，确实经过目标生命周期。其 `:46`–`:53` 只用异常字符串匹配并接受“抛出或报告”，适合说明已知 C3 的异常丢失；若升为通用验收，应保存异常对象身份、确认 cleanup 已执行，并识别无关异常，不能把同文案的其它异常当成功。现有证据未显示该宽松字符串诊断已被自动用来改分，因此不单列实现 finding。

### A2：真实握手对照足以支持已知误拒，仍不是全行为证明

`V/public/A2/worktree/aiohttp/connector.py:1046` 的 `_get_fingerprint` 先取请求级 `req.ssl`，再取 connector `_ssl`。`C/aiohttp_22a1_K2_fingerprint_without_helper.patch:10` 将同样选择逻辑内联到 TLS 建连后，普通配置语义一致。目标隐藏测试却在 `V/private/A2/hidden_tests/test_1.py:449` patch 私有 getter，而没有通过公开 ssl 配置注入 Fingerprint；K2 因拿不到这个 mock 而 17/18。这是实现耦合，而不是根据“只错目标键”免责。

同一隐藏测试 `test_1.py:400` 的 TransportMock 只实现 close。RC 使用真实库已有先例的 `abort()` 终止不匹配连接，真实握手行为正确，却因替身继承的 `asyncio.Transport.abort()` 抛 `NotImplementedError` 得 0。它没有义务照抄 gold 的 `close()` 加 cleanup 登记。既有 reviewer 对其调用栈的定位见 `B/results/A2/review.md:81`。

实际 C4 命令定义在 `X/commands/A2.json` 的 `pr4_7_cmd`：TLS origin + HTTP CONNECT proxy，覆盖 direct bad、proxy good、proxy bad connector、proxy bad request 四场景。`G/private_public_b2/a22a1_aiohttp_22a1_K2_fingerprint_without_help.json:10` 与 `a22a1_aiohttp_22a1_RC_gold_but_abort.json:10` 均表现为错误指纹拒绝、正确指纹连通，且真实证书摘要正确；base 的两个 proxy bad 场景仍连通。结合内联逻辑等价性、17 个公开回归通过，足以支持这两份具体补丁的误拒判断。

错误满分同样有独立判据：K3 检查未升级 TLS 的原始 proxy transport，`Fingerprint.check` 会在非 SSL transport 返回（`V/public/A2/worktree/aiohttp/client_reqrep.py:139`）；其 `G/private_public_b2/a22a1_aiohttp_22a1_K3_check_raw_proxy_transpor.json:10` 两个 proxy bad 仍 `CONNECTED 200`。K4 无条件拒绝所有指纹，其对应 `a22a1_aiohttp_22a1_K4_reject_any_fingerprint.json:10` 连 proxy good 也拒绝，且 got 不是证书摘要。两者都 18/18，说明测试漏测；不能用满分或与 gold 是否相同来推断正确。

C4 未覆盖“connector bad + request good”优先级、正常请求级 good、所有关闭路径、旧 TLS fallback 或 HTTPS proxy。将 C4 用于每个候选解释是合理建议；把四例全过直接当完整修复则过宽。若以后修订测试，最低应经公开配置注入指纹，覆盖正确/错误与请求级优先级，transport 替身支持 `abort()` / `is_closing()`，并接受合适的 close 或 abort。修订后重新核对已知正反例，再讨论扩展保证；本次不改材料。

### S1：gold 的 TypeError 是新回归，普通 dict 不属于私自扩充需求

公开 exporter 文档已支持普通 dict item（`V/public/S1/worktree/docs/topics/exporters.rst:170`）及字段 serializer（`:158`）；源码 `scrapy/exporters.py:54`–`:78` 会为缺失字段给 default None，而 `:257` 的 serializer 返回值本来不会再进 `_serialize_value`。gold 在序列化后再对整个 result 进行 `_serialize_dict`，让此前允许的 None / 整数返回值再次经过文本转换。

`G/private_public_b2/se938_scrapy__e938752973b4fc53e0fa0c0bc68a4316.json:10` 保存两种 TypeError（NoneType / int）；`se938_none.json:10` 及 C1、RC2 对照保留这些值。gold 仍 62/62，所以这是有旧行为依据的漏测与 gold 回归。不能把“gold 会这样”当规格，也不能把这些旧行为保护一概称为 reviewer 新增需求。

C2 只编码 BaseItem，`G/private_public_b2/se938_scrapy_e938_C2_items_only.json:17` 显示 binary=True 下普通 dict 顶层 key 仍为 str，仍 62/62；与公开支持 dict 的接口相冲突。C1 顶层编码、RC2 连嵌套 dict key 也编码，两者都 62/62；在题面没有锁定嵌套策略时，不据 gold 独断其中一个为错误。非字符串 key 在多份候选也可能失败，不能混归为 gold 的二次序列化回归；当前诊断未运行此例。

后续最小补测建议为普通 dict、export_empty_fields 的 None、serializer 保留返回值及 binary=False 回归；嵌套深度、非字符串 key、特定 encoding 的额外边界另行界定。旧 reviewer 中缺 noop 的记录已被 `G/ledger_se938_noop.jsonl:1` 补齐（61/62、0），不作为当前缺失 finding。

### S2：gold 的“没有报错”掩盖了未完成的异步工作

目标测试 `V/private/S2/hidden_tests/test_1.py:120` 只执行一次 shell fetch 并检查未出现指定 RuntimeError。gold 为工作线程创建/设置的 event loop 没有运行；协程 future 留在那里，scraper 完成回调不能释放 active size。源码链为公开 `scrapy/core/scraper.py:69` 增加至少 1024 的 active size，`:80` 完成后减去，`:90` 用阈值判断反压，`scrapy/core/engine.py:164` 据此暂停请求。

既有 E1 设置公开配置 `SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000` 后连续两次 fetch：`G/private_public_b2/s7545_scrapy__75450e75d269b2a2b00b6303af1033df.json:9` 是原命令，`:10` 为 `rc=124 / FIRST_DONE / crawled=1 loop_err=0`，第二次没有完成。相同命令的 base、K1、K1b 均完成两次。配套单 fetch 后 `slot.is_idle()` 在 gold 为 False（同文件 `:17`），base / K1 / K1b 为 True。由源码和对照可把超时归到 gold 的未驱动 loop 与收尾缺失；它不是随意把任意超时都说成 gold 问题。

实测结论是该配置下 60 秒超时；永久等待是静态机制推断。默认 5 MB 阈值的长期累积、定制 asyncio-await middleware 均未在当前证据中执行。gold 的 17/17 仍不足以覆盖公开要求的异步操作继续推进，既有 gold 假阳性结论成立。

K2 仅修改 `deferred_from_coro`，仍在 `deferred_to_future` 取当前线程 loop。五次都 16/17，调用链 `spidermw.py:225 → defer.py:355 → defer.py:325` 的 RuntimeError 有实际日志支持，拒绝合理。K3 的 fallback 会返回原始 Deferred / `ensureDeferred`，对 asyncio-await 的兼容风险可由源码推断，但现有 E1/C2 没跑 K3，不应提升为已实测失败。以后若要判定更广泛替代，应加真正等待 asyncio future 且验证完成副作用的案例；当前 E1 + idle 诊断只证明收尾与反压这一族行为。

## 重复实验与诊断命令的使用条件

1. **A1 的 6 次确为并行测试。** `G/b2_par_a1c1c.sh:6` 后台启动；6 份 gold 日志测试时间戳存在 28.610 秒共同区间，均 56/56，补丁/镜像一致。这支持“本次并行条件下未复现该启动竞态”，不证明训练负载、其它机器或极小概率事件均稳定。保留 watch 合理，按键免责不合理。
2. **S2 K2 的 5 次为串行。** `G/b2_chain_s7545.sh:8` 的循环执行 5 次，均稳定暴露剩余转换错误。`B/results/S2/review.md:47` 中“时序风险可关闭”应收窄为“本次条件下 5 次未观察到翻转”；不据此推导稀有假通过概率已排除。这是措辞收窄，不推翻 K2 当前被正确拒绝的结论。
3. **外层 rc 与被诊断动作不是同一判据。** A2 C4、S1 E1 用 print/捕获异常呈现各分支，因此错误实现也可 wrapper rc=0。S2 E1 的外层 rc=0，但内部 timeout 的 rc=124 在 stdout；S2 C2 外层 rc=1 是最终 grep 没找到错误文本，内部 shell 已 exit=0（上述 gold JSON `:8`–`:17`）。当前未发现直接以这批 wrapper rc 自动判语义 pass 的消费代码，所以作为解释/复用条件记录，不升级为新的自动误判 finding。
4. **诊断不是完整规格。** A1 字符串匹配、A2 四个握手场景、S1 两类 serializer 值、S2 低阈值两次 fetch 都可有效区分已有候选，但不能因此笼统给任意候选“完整正确”。后续使用应保留每例输出和源码复核，报告实际覆盖；进入自动验收前再将断言、超时传播和正反例标定做实。

收口建议：本轮修正 F1 的归因口径并收窄重复实验措辞；已知误拒/漏测/gold 缺陷继续显式登记。材料修订、通用后检自动化、更多 asyncio/TLS 边界实验可按后续用途另定，本分报告不要求为当前只读审查追加执行或改分。
