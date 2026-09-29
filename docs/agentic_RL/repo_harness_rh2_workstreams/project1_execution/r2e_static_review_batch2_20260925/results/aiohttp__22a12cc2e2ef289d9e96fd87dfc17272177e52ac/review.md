# 独立复核·第二步：aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac

2026-09-25 · 独立复核者（Claude）。我的第一步封存稿是 `reviewer_initial.md`，本文不改它。本文基于三部分材料：
- 主审产物（`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`）；
- 公开读者 `public_read.md` 与历史引用；
- 协调者新取得的正式评分和私有行为核对。

## 0. 结论

- **同意主审的处置与主结论。** 处置 `needs_review`。题面误导（缺触发条件，示例不成立）；目标键只检查 mock 交互。
- **两条主要问题已由正式评分实跑坐实。** 主审稿里它们还是静态推断：
  - K3 什么都没修好，却拿 1；
  - K4 把正确指纹也拒掉，同样拿 1。
- **在 K2 之外，另有一类误拒：** 我初判中的 C（不匹配时调用 `abort()`）实测判 0，主审没有想到。**K2 与 C 都归为"合理修复被误拒"**，归类依据见 §3。原始 reward 保留。
- **需要修改主审的三处表述：**
  1. card §3 说"唯一的硬约束是经 `_get_fingerprint` 取指纹、调用 `.check`"，不准确。K4 没调用 `check` 也拿了 1；C 说明 TLS transport 的测试替身本身也构成约束。
  2. 测试修订建议要补两点：怎样注入指纹、替身要支持哪些 transport 方法。否则 K2 和 C 的误拒不会消失，还可能引入新的误拒。
  3. card 说附录补丁"都已 `git apply --check` 通过"，这与附录 K1 的实际文本不符。
- **保留一处分歧：** 本题能否进入模型探针的成功率统计（§6）。

## 1. 本步新增的读取范围

- OUTPUT_DIR 下全文：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`。
- 历史（按 `history/.../refs.json`）：
  - 全文：`r2e_env_repair_20260924/tasks/<本题>/findings.md`。
  - 前约 9000 字符及尾部：`screening_record.json`。
  - 只看了两个相关族：`known_issues.json` 的 `solver_condition:testbed_must_be_on_sys_path` 与 `prompt_quality_candidates`。
  - grep 本题：`decisions.md`、`results_20260924.md`。
  - 未读：`facts.json`、repro 脚本、`packages/p1/README.md`、posthoc 脚本与 `agent_probe.log`。这些是主审读过的，我只核对了它们在 delta 中的引用方式。
- 新运行证据（`runs/r2e_actor_20260925/`）：
  - `grader_cands/aiohttp_22a1_{K1..K4,RC}.patch` 全文，并本地复算了 sha256。
  - `grader/ledger_a22a1_{gold,K1..K4,RC}.jsonl`，各 1 行，抽取了字段。
  - 对应 eval.log：用 grep 看关键行；RC 那份读了 L112–124 与 L240–275。
  - `grader/private_public_b2/a22a1_*.json`，全部 7 份的 stdout。
  - `grader/b2_chain_a22a1.sh`。
- 另外用 `git hash-object` 核了公开 `connector.py` 的 blob。
- 未读：本批 README、`assignments.json`、`grader_candidates.md`、首批审查目录、Codex 复核目录、其它题的私有包。

## 2. 主审决定性主张逐项核对

| # | 主审主张（出处） | 核对 | 判定 |
| --- | --- | --- | --- |
| 1 | 题面示例构造时即 `ValueError`；直连已经会校验；缺陷只在 HTTP 代理 CONNECT 后的 `start_tls` 路径；题面没提代理（card §4 问题 1，analysis §0.1） | 引用都支持，且对应当前镜像、agent 身份与正式启动路径：devcheck `pr2_2`、`pr3_6`、`pr4_7`（base，uid 54321），私有 gold 对照（root，不联网）。本次私有核对 `a22a1_none.json` 在 derived9 上复现了同样的 base 行为 | **同意** |
| 2 | 公开读者靠读代码推出了代理路径，所以可以推知（card §4 问题 1） | 公开读者确实在读隐藏材料之前推出了代理路径（`public_read.md` §0.3、R2、§3.4），不是看了答案再说"显然"。但公开读者自己也把它列为"多解，代码给出一个候选"，并说"最关键的未知是隐藏测试针对哪条路径"（§0.4） | **同意，但需加限定**：应写"可推知为最可能的候选"，而不是"可推知" |
| 3 | 目标键会误收未修复的实现 K3（card §4 问题 2，check 25、32） | 正式评分：K3 得 1（18/18，账本 `ledger_a22a1_K3…` 与日志 `668a0b4e` L193）。私有 C4：`proxy+bad_fp` 与 `proxy+bad_fp_per_request` 仍是 `CONNECTED 200`，与 base 相同（`a22a1_aiohttp_22a1_K3…json`） | **同意；证据由静态推断升级为正式评分 + 私有行为核对** |
| 4 | 正例缺失，K4 会被误收（card §4 问题 3，check 26） | K4 得 1（18/18，日志 `a313025f`）；C4 中 `proxy+good_fp -> SFM got_is_cert=False`（SFM 即 `ServerFingerprintMismatch`），正确指纹也被拒 | **同意，已实测** |
| 5 | K2（不经 `_get_fingerprint`）预计判 0，可能性较低（card §4 问题 4，check 24 记为 unknown） | K2 得 0（17/18）。日志 `dc7251fa` L156 为 `AssertionError: ServerFingerprintMismatch not raised`，L173 为 `test_1.py:475`；C4 结果与 gold 完全相同 | **同意；check 24 应由 unknown 改为 issue** |
| 6 | "唯一的硬约束是必须经 `self._get_fingerprint(...)` 取指纹、调用 `.check(...)`"（card §3、analysis §1） | 有两处不准。(a) K4 不调用 `check`，直接 `raise`，也拿 1。主审附录的"预测依据"自己写了"经 helper 取到指纹并调用 check 或直接 raise"，与 card §3 矛盾。(b) 目标测试的 TLS transport 替身 `TransportMock` 只实现了 `close`。补丁如果在不匹配时调用 `abort()` 或 `is_closing()`，就判 0（见 §3 的 RC，已实测）。实际的约束是：经 `_get_fingerprint` 取指纹；抛出 `ServerFingerprintMismatch` 或其子类；不在 TLS transport 上调用 `asyncio.Transport` 基类里未实现的方法 | **修改** |
| 7 | 回归键就是整个公开 `tests/test_proxy.py`，只差类型注解（analysis §2） | 我的 diff 也显示 `test_https_connect` 的签名多了注解。我第一步写的是"只差 import 与新增测试"，漏了这一点，以主审为准 | **同意，并更正我的表述** |
| 8 | pytest 8.3.3 没装 subtests 插件，`subTest` 不起作用，第一个失败就结束（analysis §2） | 与 noop 日志的局部变量 `cleanup = True` 一致。机制是 stdlib 的 `subTest` 在 result 没有 `addSubTest` 时直接 `yield`，这一层是静态推断 | **同意** |
| 9 | 附录四份补丁"都已在 base `connector.py` 上 `git apply --check` 通过"（card §5、record `candidates_patch_ref`） | 协调者说附录 K1 用 `git apply` 报 corrupt。我数了一下：card L81 的 hunk 头写 `-1457,13 +1457,23`，但附录正文只有 12 行旧、22 行新，缺了末尾那一行空白上下文；协调者重新生成的 K1 文件里有这一行。base blob `6bc3ee54cdfd…` 本身无误（`git hash-object` 已复算） | **修改**：这可能是转录时丢了行，但按已保存的附录文本，"都已通过"的说法不成立。结论不受影响，因为协调者按同样改法重新生成的 K1 得 1 |
| 10 | 同仓跨题：本题修复不在其它题的初态里；反向包含只影响那几题（card §3） | 与我第一步的核对一致 | **同意** |
| 11 | 历史 R16 的 `pass` 只成立在"症状对应"这一层；环境资格 `environment_qualified` 确认（`old_findings_delta.md`） | 历史 `findings.md` 与 screening_record 的 R03、R09、R16 引用方式与主审描述一致。历史范围是环境资格，不涉及测试强度，主审没有把它当作质量合格 | **同意** |
| 12 | 镜像身份：评分用的镜像 `dfd6021f…` 与 devcheck 用的 `2b571f22…` 没有逐层比对（card 附录 B） | 新的正式评分都在 `2b571f22…`（derived9）上跑。gold 在这张镜像上也是 18/18，隐藏测试树摘要同为 `80d242d6…`（日志 `843e4076` L6、L193）。两次构建在本题判分上的等价性已有直接证据；逐层等价仍未核，但对本题结论已无影响 | **同意，并缩小这项缺口** |

## 3. 实测候选归类（按第二批补充规则 1）

失败键相同，不代表同样合理。本题 noop、K2、RC 以及"照题面只放宽构造器"的候选，都只错同一个键 `TestProxy.test_https_connect_fingerprint_mismatch`（17/18）。所以"只错目标键"只能用来筛出待复核样本，**原始 reward 一律保留**。

| 候选 | reward | 私有 C4 行为 | 归类 | 依据 |
| --- | --- | --- | --- | --- |
| gold | 1 | 两个"代理 + 错指纹"场景抛 SFM；"代理 + 对指纹"连通 | 参照 | — |
| K1：在 `_create_proxy_connection` 里校验 TLS transport | 1 | 同 gold | 正确接受：合理替代解 | 日志 `066bc253` 18 passed |
| **K2**：位置同 gold，指纹直接取 `req.ssl`/`self._ssl` | **0** | 同 gold | **合理修复被误拒（出现概率低）** | 见下 |
| **RC**（我的 C）：gold，但不匹配时调用 `tls_transport.abort()`，不登记 cleanup | **0** | 同 gold | **合理修复被误拒（出现概率低到中）** | 见下 |
| K3：校验连到代理的原始 TCP transport | 1 | 同 base（缺陷仍在） | **误收：错误修复得 1** | §2 第 3 行 |
| K4：只要配置了指纹就一律抛 | 1 | 对指纹也被拒 | **误收：破坏合理旧行为却得 1** | §2 第 4 行 |
| 照题面放宽 `Fingerprint` 构造器、代理路径不改（主审 §5 与我初判的 D） | 未跑；静态推断为 0 | — | 正确拒绝：遵循冲突示例的候选 | 缺陷没修 |
| 放宽构造器，同时修代理路径（主审 §5） | 未跑；静态推断为 1 | — | 误收：破坏公开的构造契约（`test_client_request.py::test_bad_fingerprint` 等），隐藏集不测 | 静态推断 |

**K2 为什么算合理误拒：**
- **逐条满足公开要求。** 它抛的是题面要求的 `ServerFingerprintMismatch`；请求级指纹优先于连接器级（公开读者 R3），因为取指纹的表达式与 `_get_fingerprint`（`connector.py:1046-1053`）逐项等价，这一点是静态核对。关闭与 cleanup 的处理与 gold 相同。
- **不破坏旧行为。** 17 个回归键就是整份公开 `test_proxy.py`，全部通过；C4 的四个场景与 gold 逐行一致，包括 `proxy+good_fp` 连通。
- **判 0 的唯一原因**是目标测试只通过 patch 私有方法 `connector._get_fingerprint` 来注入指纹（`test_1.py` L449–455），而这时 `req.ssl` 和 `connector._ssl` 都是 `True`。
- **不属于"遵循冲突示例"。** K2 与题面示例无关。
- **出现概率低。** 直连路径紧挨着就是复用 `_get_fingerprint` 的先例（L1279），多数解题者会直接复用。

**RC 为什么算合理误拒：**
- **满足公开要求，行为与 gold 相同。** C4 四个场景与 gold 一致。
- **`abort()` 有代码库先例。** 代码库本身就用 `abort()` 处理"可能关不干净"的 SSL transport：`_cleanup_closed`（`connector.py:410`）和 `close`（L455）。`abort()` 立即断开，不再登记 `_cleanup_closed_transports` 在语义上说得通。公开读者 R14 也把"是否关闭、是否登记 cleanup"列为多解。
- **判 0 来自测试替身。** `TransportMock` 继承 `asyncio.Transport`，只重写了 `close`。于是 `abort()` 在 `asyncio/transports.py:145` 抛 `NotImplementedError`，在异常链上盖掉了原本的 SFM（日志 `4c93d991` L120 是 SFM 被抛出，L269–273 是 `NotImplementedError`）。
- **出现概率低到中。** 20 行外的直连路径先例用的是 `close()`，照抄的解题者会用 `close`。
- **同类写法：** `if not tls_transport.is_closing(): tls_transport.close()` 也会触发 `NotImplementedError`（stdlib 静态推断，未实跑）。

## 4. 反查：主审没覆盖或写得不准的范围

1. **TLS transport 替身与候选的耦合**（新发现，已实测，见 §3 RC）。它应并入 issue `aio22-mock-coupling`，check 24 应改为 issue。
2. **测试修订建议需要补的具体约束**（主审 card §5 修订建议 1、issue `aio22-mock-coupling`）。主审说"改用真实 `Fingerprint` 和带 extras 的 TransportMock，耦合随之消失"。这只在下面三个条件都满足时才成立：
   - **指纹经公开配置注入**：用 `TCPConnector(ssl=Fingerprint(...))`，并且另有一例用请求级 `ssl=`。不能继续 patch `_get_fingerprint` 去返回一个真实 `Fingerprint`，否则 K2 仍判 0。
   - **transport 替身支持 `abort()`、`is_closing()`**，或者改用记录调用的替身。否则 RC 仍判 0。
   - **断言"不匹配后 transport 已关闭"时，接受 `close` 或 `abort` 任一方式**，不绑定 `close`。异常的 `host`/`port` 也不要断言是代理地址还是目标地址：公开读者 R5 把它列为多解；gold 报的是代理端口，K4 报的是目标端口。
3. **未测的构造契约回归**：见 §3 末行。主审已经指出，我同意，只是还没实跑。
4. **不关闭 TLS transport 也不会被隐藏测试发现。** 公开读者推测"遗留 transport 在 `filterwarnings = error` 下会以 ResourceWarning 让测试失败"（`public_read.md` §2），但这对隐藏目标键不成立：`TransportMock` 不是真实的 socket transport，没有 `__del__` 告警，`close` 也没被监视（静态推断）。这属于漏测，影响小。
5. **新运行证据未登记。** 本次 6 条账本（derived9）还没进 `run_refs.json` 或 `screening_record.facts_ref`，建议协调者登记为当前材料下的诊断行。

## 5. 与我初判的差异

- **我的 B 与主审 K3 同类。** 我的 B 是在 `_start_tls_connection` 里校验 `underlying_transport`；主审 K3 是在 `_create_proxy_connection` 里校验原始代理 transport。两者机制相同：`check` 被 mock，传什么 transport 都会抛。K3 已实测得 1，B 未单独实跑，按同一机制推断同样得 1。
- **我的 E 即主审 K2，C 即 RC。** 两者实测都得 0，与我的初判一致。
- **"代理 + 对指纹"会被一律拒绝的实现误收：** 初判时我把它列为 B′（静态推断），现在 K4 已实测。
- **更正两处表述：** 回归文件与公开文件的差异还包括类型注解（§2 第 7 行）；stdlib `abort` 的 `NotImplementedError` 已由 3.9.21 的真实日志确认，初判时是用本机 3.12 源码推断的。
- **补上漏项：** 主审提出的"放宽构造器同时修代理 → 误收"我初判没写，这里补上。

## 6. 处置、用途与"可探针"

- **处置：** 同意 `needs_review`。两层原因中，第二层（题意/测试争议）的实跑已经完成，现在可以直接进入"是否修订"的用户决策。
- **修订建议是否扩大原需求：**
  - **题面**补"经 HTTP 代理（CONNECT）访问 HTTPS"，并把示例改为 `ssl=aiohttp.Fingerprint(<32 字节>)`。这只是写明真实的、用户可见的触发条件，缩小了题面与测试之间的落差，没有扩大需求，也没有泄漏实现位置之外的修法。
  - **测试**要补的内容：负例（真实 `Fingerprint`，传入带 `sslcontext`/`ssl_object`/`peername` 的 transport）与正例（"代理 + 对指纹"能连通）。正例保护的是 base 已有的行为（base C4 中 `proxy+good_fp` 为 CONNECTED），属于合理旧行为，不算新需求。只要遵守 §4 第 2 条的约束，就不会引入新的误拒。
  - 两项修订都是**测试标准与公开规格的变更，需要用户决定**。主审已经这样标注，同意。
- **"可探针"与剩余条件是否分开：** 主审把"开发条件已由 devcheck 实测"和"真实模型求解、adapter 链路待验"分开写了，也没有把 `environment_qualified` 当作质量合格。同意。
- **保留的分歧（用途）：**
  - 主审的写法是"可作开发诊断，暂不作评测题"，并附两条注意事项。
  - 我的意见：修订前，如果要把本题放进基座探针，**不能直接用 reward 计入成功率**。reward 在两个方向上都不可靠：K3、K4 是 1 却没修好；K2、RC 是 0 却修好了；题面误导还会产生"判断无需修改"或"去改构造器"的轨迹。
  - 最低要求：对每个 reward=1 的补丁，在私有容器跑一次 C4（`pr4_7_cmd`，现成脚本，约几秒），以确认修复有效。reward=0 的补丁也要跑 C4，找出 K2、RC 类的误拒。
  - 如果做不到，本题应单独报告，不并入汇总成功率。这项要求不属于评分规则，只是诊断时的解释口径。

## 7. 最小后续实验

1. **现在不需要新实验。** 现有各项结论都已有正式评分或私有行为核对支撑。
2. **如果用户批准测试修订：** 用修订后的测试重跑 gold、noop、K1–K4、RC，再加一个 `is_closing()` 变体。预期：gold、K1、K2、RC、`is_closing` 变体得 1；noop、K3、K4 得 0。任何偏离都说明修订引入了新的耦合。
3. **可选，低优先：** 实跑"放宽构造器并修代理"这个候选的正式评分，以及公开的 `test_client_request.py -k fingerprint` 和 `test_client_fingerprint.py`。目的是把"未测的构造契约回归"从静态推断升级为实测。
