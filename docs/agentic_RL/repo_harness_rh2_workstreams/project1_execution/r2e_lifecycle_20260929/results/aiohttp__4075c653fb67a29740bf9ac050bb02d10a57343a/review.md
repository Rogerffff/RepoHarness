# aiohttp__4075c653 独立复核（review，第二步）

2026-09-29 · 独立复核者（Claude）。第一步初判见同目录 `reviewer_initial.md`，写于读主审产物之前；本文在读完公开读者产物、主审产物、历史引用和新机实跑之后写。只做静态阅读与已有证据核对，没有运行项目代码。“本地标准库核对”指在 scratchpad 里只用 Python 标准库模拟正则与分割语义（不导入 aiohttp），不是评分证据。

## 0. 结论

- **同意主审定稿 `needs_repair`，修订可以开做。** 4 个 S1 都成立：I1、I2（T2c）、I3（T2b）、I4（第 4 步）。R-c #1–#3 都在预授权模板内，按附录 C、D 的补丁实施。
- **I4 我独立判为 S1。** gold 把请求目标里夹 LF / FF / CR / TAB 的请求行从 base 的 `BadStatusLine` 改成了接受。这类请求行“contains improper whitespace and control characters”，按题面一般表述属于同一核心要求，也不是边缘输入。我初判只看了 `\x01`（base 同样接受），漏掉了空白类控制字符在 base 上本来会被拒绝，现据私有矩阵改判。
- **R-c #3 不扩大需求。** 它只收题面自己的两个字符（LF、FF），而且只放 base 原本就拒绝的位置。修订后原 gold 判 0，按 D4 用替代解作正对照。我建议把 ALT2（gold 加请求行控制字符检查）作为主正对照、ALT1 作第二正对照；两者都要在修订版上正式评分，并跑公开测试私有对照。
- **ALT1 比 gold 严的三处**（字段名里的 `/`、目标里的 `\x01`、版本号里的 FF）都符合 RFC，隐藏回归 129/129，公开测试里也没找到冲突；R-c 断言也不依赖这三处（§3）。
- **P4、X1 与主审一致。** P4 现已由 devcheck 实证。240da100 那条关系的措辞两边略有出入（§5）。
- **需要修改的地方**（都不阻塞开工，见 §6）：R-c #2 排除 HTAB 的理由写法；I4 与 I7 的分界理由；正对照的主次；修订后环境复验的正对照要从 gold 换成存档的 ALT 补丁。

## 1. 实际读取范围（第二步）

- 公开读者：`public_read.md`、`commands.json` 全文。
- 主审：`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json` 全文；`cands/` 下两个补丁与 `pcheck_matrix.sh`。
- 历史（`runs/r2e_static_prep_20260924/v3/history/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/refs.json` 所列）：本题 `findings.md`、`screening_record.json`（R01–R20 全部字段）、`facts.json` 前约 5000 字符、`repros/…py` 全文；`known_issues.json` 中两个相关族；`results_20260924.md`、`packages/p1/README.md` 按本题 grep；`decisions.md` 按本题 grep，无命中。
- 新机实跑（`runs/r2e_lifecycle_20260929/`）：
  - `env_verify/` 下全部账本按本题 grep，只有 `ledger_{noop,gold}.jsonl` L4 有本题行；
  - `inv/aiohttp_4075/` 下 `ledger_{DG1,ALT1}.jsonl` L1 全字段、两份 eval 日志的关键行、`pcheck_matrix_{none,gold,DG1,ALT1}.json` 全文、`run.sh`、`run.log`；
  - `devcheck/aiohttp__…/` 下 `devcheck.log`、`private_control.json`、`private_control.log`、`orig/captures/*.out` 全文。
- 公开包补读：`worktree/aiohttp/_http_parser.pyx` 570–590、645–660、805–840 行；`worktree/docs/client_advanced.rst` 100–115 行；`worktree/tests/test_http_parser.py` 232–240、855–866、1084–1090 行；`worktree/tests/test_proxy.py` 601–615 行。同仓公开包 aiohttp__22a12cc2 的 `worktree/aiohttp/http_parser.py` 560–640 行，aiohttp__240da100 的 `public_bundle.json` 题面开头。
- 本地核对：把 `card.md` 附录 C、D 的补丁 `git apply` 到隐藏测试副本，`py_compile` 通过；附录 F（ALT2）`git apply` 到 base `http_parser.py` 副本，`py_compile` 通过；用标准库模拟 gold、ALT2 和“只拒空白类控制字符”的最小变体在 R-c 输入上的结果（§3）。临时文件都在 scratchpad。
- 未读：其它题私有包；`r2e_*review*` 等审查目录；本批 README、board、assignments；`attempt.json` 等 devcheck 细节文件（CC 版本号未核）。

## 2. 主审决定性主张逐项核对

| 主张 | 结论 | 核对依据 |
| --- | --- | --- |
| 当前材料、新机复验：noop 0、gold 1 | **同意** | `env_verify/ledger_noop.jsonl` L4：127/129，mismatched 就是两个目标键；`ledger_gold.jsonl` L4：129/129。镜像 `f483bab4…`，配方 `r2e_derive_v1+sysconfig_v1`，与主审引用一致。旧机 `0d785442…` 的行只作对照，主审没有混用 |
| I1、I2：T2c ×2 | **同意**（与我初判相同） | 隐藏测试只比公开测试多两处，输入都是题面示例的字面值（`test_1.py:181`、`:684`） |
| I3：DG1 正式评分 1.0 → T2b | **同意，已坐实** | DG1 与我初判的退化候选 D 逐字相同（`|\xc3\xbf` 交替分支，外加 `"\n"` / `"\x0c"` 检查）。`ledger_DG1.jsonl` L1：`git_apply`，投影 `["aiohttp/http_parser.py"]`，129 键全解析，`keys_equal=true`，测试段完成；日志 L6 隐藏树 `eb81f695…`、L8 `RH2_SETUP_APPLY_RC=0`、L39 / L89 两个目标键 PASSED。补丁已交付，相关测试已执行，结果有效 |
| I4：gold 接受请求目标里的 LF / FF / CR / TAB，base 拒绝 | **同意，S1**（理由见 §3） | `pcheck_matrix_none.json`：`target_lf/ff/cr/tab` 都是 `BadStatusLine`；`pcheck_matrix_gold.json`：四行都是 `ACCEPT`，例如 `('GET', '/pa\nth', [])`。矩阵与评分同一镜像；以 root 运行，只作行为检查，这类主张用它合适。yarl 确实不拦（gold 行已接受），主审分析稿里“yarl 待跑”一项已关闭 |
| I5：P4 | **同意** | devcheck `repro_parser_issue_cases.out`：`issue_ex1_literal` 在 base 上已抛 `InvalidHeader`，另外两行 FAIL，`FAILS 2`。我初判时这一点还只是源码推断，现在已实证 |
| I6：3 个期望 FAILED 键是 C 扩展缺失造成的死键（T5） | **同意** | 新机 `env_import_versions.out`：`c_parser_available False`、`no aiohttp/*.so`。ALT1（比 gold 严）也是 129/129，说明正确修复不会翻转它们。补充一点：历史 R05 记载镜像里有 Cython 3.0.4、gcc 和 `aiohttp/_http_parser.c`。能否离线构建取决于镜像里 `vendor/llhttp` 有没有内容，目前两边都没查（§6 M5） |
| I7：T3 旧缺口 | **同意登记**，但分界理由要补（§6 M2） | `\x01` 在目标里、版本号里的 FF、字段名里的 `/`：base 与 gold 都接受（矩阵） |
| I8：X1 | **同意** | 与我初判相同；240da100 的措辞差异见 §5 |
| I9：E3 通用控制面 | **同意** | 与我初判的 §4(d) 相同 |
| 无 T1 | **同意** | 目标键只断言题面点名的异常类；ALT1 得 1 |
| 用途：定位 yes，比较 conditional，训练 no，留出 no | **同意** | 与我初判一致 |
| devcheck：公开开发路径可用 | **同意**（按 agent 身份的执行事实） | `env.out`：uid 54321、`/testbed/.venv`、pip 23.2.1；`public_http_parser_tests.out`：设 `AIOHTTP_NO_EXTENSIONS=1` 后 124 passed / 5 skipped；`public_related_tests.out`：135 passed；服务端复现两例都是 `HTTP/1.1 200 OK`。gold 私有对照：两例都是 `HTTP/1.0 400`，公开测试结果不变 |

主审没有把 superseded 行、M3 独立 runner、root 身份的矩阵和 agent 身份的 devcheck 混为一谈。各证据的用途与主张的类型对得上。

## 3. 重点一：I4 是否构成第 4 步 S1

**事实**（私有矩阵，新机同一镜像）：

| 请求行 | base | gold | DG1 | ALT1 |
| --- | --- | --- | --- | --- |
| `GET /pa\nth HTTP/1.1` | `BadStatusLine` | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |
| `GET /pa\x0cth HTTP/1.1` | `BadStatusLine` | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |
| `GET /pa\rth HTTP/1.1` | `BadStatusLine` | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |
| `GET /pa\tth HTTP/1.1` | `BadStatusLine` | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |

机制：base 用 `str.split(maxsplit=2)`，目标里的空白会把目标切成两段，剩下的部分落进版本位，于是 `VERSRE` 失败。gold 改成只按 SP 切分后，目标原样进入 `URL.build(..., encoded=True)`，这一步不检查字符。

**我的判断：S1 成立。** 依据从强到弱：

1. **题面字面。** Expected Behavior 写的是“because the status line **contains** improper whitespace and control characters”（`user_prompt.txt:23`），说的是“含有”，不是“用它们分隔”。LF 和 FF 正是题面示例里的字符。gold 让含 LF / FF 的请求行通过，违反了题面自己给的理由。按 v1 §4，核心要求按题面的一般表述理解，gold 的实现范围不决定它。
2. **不是边缘输入。** v1 第 4 步只对“边缘输入、罕见路径”降为 S2。这里的情形不属于那一类：
   - 目标里的裸 CR / LF 是请求行拆分和走私的典型载荷；
   - 覆盖面是整个请求目标的任意位置，不是某个特殊位置；
   - base 原本拒绝它们，所以这是修复带来的回归，不是旧缺口没修。
3. **仓库与规范。**
   - 请求解析器按设计是严格的（`http_parser.py:639–640`，只有响应解析器 lax）；C 解析器对请求不开宽松标志，只对响应开（`_http_parser.pyx:645–655`）。
   - 公开测试把头部里的裸 CR / LF 当必拒输入（`test_cve_2023_37276`、`test_bad_headers` 的 `\r` / `\n` 参数）；公开测试注释承认 Py 解析器接受 UTF-8 路径属于“Not valid HTTP”（`tests/test_http_parser.py:1087–1088`）。
   - 代码注释引用了 RFC 7230 §5.3 的 origin-form 语法，该语法不允许空白与控制字符。RFC 9112 §3.2（RFC 7230 §3.1.1 同文）写明“No whitespace is allowed in the request-target”，接收方 SHOULD 返回 400 或 301，SHOULD NOT 自行纠正后照常处理。此条凭记忆引用，未联网核对原文，也不是仓库直接引用的章节，只作辅助。
4. **反证检查。** 我没有找到任何公开依据说请求目标里的 LF / FF 可以接受。几个可能的反方理由都不成立：
   - RFC 9112 §3 的宽松 MAY 是把空白当分隔符，那样会切出 4 段，照样非法，推不出“接受”。
   - 公开读者把 A4 列为“可选加固”，但他写的是“只改成单 SP 切分，这两例**仍**会被接受”，说明他没注意到 base 本来就拒绝它们。
   - 上游到 3.11.0.dev0 仍是 gold 写法（22a12cc2 公开初态 `http_parser.py` 575–578 行附近，切分后没有字符检查）。这只说明上游实现范围比题面表述窄，而且上游 CHANGES 的意图是“不再接受 LF 作请求行分隔符”，比题面窄。按 v1，这不决定核心要求。

**需要如实登记的代价**：修订后，与上游维护者同款的“只按 SP 切分”修复会判 0。本题从此只能作“标明版本的自建题”，能力比较报告要写明这一点。这是 D4 已授权的后果，不需要另请用户决定，但批次汇报要显式列出。

**分界（与 I7 的关系）**：我同意只把“目标里的空白类控制字符”升为 S1，不把 `\x01`（目标内）和版本号里的 FF 升级。理由应写成 v1 第 4 步的边缘性判断，而不只是“base 也接受”，因为 v1 并不按“是否旧缺口”豁免：

- `\x01` 不是空白、不是分隔符类字符，与题面“improper whitespace and control characters”并举的那类字符不同；
- 版本号里的 FF 只在“FF 恰好替代版本点号”这一个位置能通过（源于 `VERSRE` 的 `.` 没转义，属版本校验旧缺陷），`HTTP/1.1\x0c`、`HTTP\x0c/1.1` 都已被拒；
- 两者都是 base 已有、影响面窄的缺口，登记 T3，并由事后审计与正对照覆盖。

## 4. 重点二：R-c #3 是否在模板内，ALT1 是否会造成过严

**R-c #3 在模板内，不扩大需求。**

- 按 v1 §5，R-c 用于“补有公开依据的断言：非示例实例、核心场景”。R-c #3 的两例（`lf-in-target`、`ff-in-target`）是 R2 的非示例实例，只用题面自己的两个字符，也只放在 base 原本就拒绝的位置，不要求任何 base 没有的新行为。
- 断言用父类 `BadHttpMessage`，有依据：C 解析器把状态、方法、版本错误映射成 `BadStatusLine`，把 `HPE_INVALID_URL` 映射成 `InvalidURLError`（`_http_parser.pyx:829–834`）。这样两种合理实现（报状态行错误或报 URL 错误）都算对，不会在子类上造出 T1。
- 补丁已核：附录 C、D 依次叠加到隐藏测试副本上能 `git apply`，结果通过 `py_compile`。新键使用显式 id，不会出现转义字符。
- 不需要为 R-c #3 另做 R-f：题面的“contains”已经覆盖这一要求。补写一句会削弱题目的区分度，也有把隐藏测试细节写进题面的风险。

**R-c 断言不依赖 ALT1 更严的三处。** 本地标准库模拟（对照矩阵里 gold 的实测结果）显示：一个最小变体“gold 的字段名检查 + 请求行里出现 `[\t\n\x0b\x0c\r]` 就抛 `BadStatusLine`”能通过 R-c #1–#3 全部断言，同时仍接受字段名 `Fo/o`、目标里的 `\x01` 和版本号里的 FF。所以修订只要求补上“空白类控制字符”这一处，不会把 ALT1 的额外严格性变成隐性要求。

| R-c 输入 | gold | ALT2（模拟） | 最小变体（模拟） |
| --- | --- | --- | --- |
| `GET /path\x0cHTTP/1.1`（#2） | `BadStatusLine` | `BadStatusLine` | `BadStatusLine` |
| `GET\x0b/path HTTP/1.1`（#2） | `BadStatusLine` | `BadStatusLine` | `BadStatusLine` |
| `GET /pa\nth HTTP/1.1`（#3） | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |
| `GET /pa\x0cth HTTP/1.1`（#3） | **ACCEPT** | `BadStatusLine` | `BadStatusLine` |
| 保留行：UTF-8 路径 / `GET \xff …` / `getpath ` | 接受 / `InvalidURLError` / `BadStatusLine` | 同左 | 同左 |

**ALT1 更严的三处会不会被其它公开回归拒绝**：

- 隐藏回归：ALT1 正式评分 129/129（`ledger_ALT1.jsonl` L1），没有冲突。
- 公开测试文件：我 grep 了 `tests/` 下的原始请求字节串，没找到字段名含 `/`、`?` 等非 token 字符、又要求被接受的用例；也没找到请求行含控制字符、又要求被接受的用例（`test_http_writer.py:270` 那一处是写出方向，与解析无关）。静态看不冲突，但 ALT1 在 `test_http_parser.py`、`test_multipart.py`、`test_client_proto.py`、`test_http_exceptions.py` 上的私有对照还没跑（主审 card §5 已列），跑完才算“经独立核实”。
- 语义上：`/` 不是 RFC 9110 的 tchar（`http_parser.py:59–66` 注释列出的集合）；目标里的 `\x01` 和版本号里的 FF 都是“状态行含控制字符”。三处更严都比 gold 更贴近题面，不属于错误行为。

**正对照的主次（修改建议）**：D4 要求“经独立核实的合理替代解”。ALT2 与 gold 只差一处请求行控制字符检查，最能说明修订要求的正是 gold 缺的那一点，建议作**主正对照**；ALT1 作第二正对照，同时验证“更严的修复不被误拒”。ALT2 已核：能直接应用到 base、语法通过。它的两部分分别等于 gold 的字段名检查（gold 129/129）和 ALT1 的请求行检查（ALT1 129/129），预计 129/129，但仍须正式评分。

## 5. 重点三：P4、X1 与主审的登记是否一致

- **P4：一致。**
  - 双方都登记，可选 R-f。
  - 主审的 R-f 只删掉例 1 的 `.encode()`，改动比我初判的写法更小，我采纳主审版本。
  - devcheck 已提供两份 base 实证：字面例 1 抛 `InvalidHeader`；意图输入不抛异常（`repro_parser_issue_cases.out`、`NOOP_LOG` L236–240）。R-f 的“base 实跑证实”条件已满足。
  - 做不做仍是可选：不做时，探针分析要记住“照抄例 1 复现不出”。
- **X1：一致。**
  - 双方都指出 aiohttp__1c1c0ea3、aiohttp__22a12cc2 的公开初态含本题修复（重构后的 `TOKENRE` 与逐字相同的 `split(" ", maxsplit=2)`）和两个目标测试原文；
  - 都指出 gold 逐字扫描因上游重构而漏报；
  - 处置都是训练时控制重复采样、留出按仓库整体划分。
- **240da100 的措辞有小差异。** 我初判写“本题 base 已含 240da100 的修复”，主审写“只是名字层面命中，语义无关”。核对 `worktree/tests/test_proxy.py:601–615`，它是同一个“代理请求保留端口”测试的后续版本，不是巧合同名；240da100 是 2014 年的 0.9 版本，本题 base 晚约 9 年。更准确的说法是：240da100 要求的行为在本题 base 里早已存在，关系只影响 240da100 一侧的记录，对本题无影响。建议主审把“语义无关”改成这个说法；对本题处置没有影响。

## 6. 修改建议（不阻塞开工）

- **M1（R-c #2 理由的写法）。** card 附录 C 说不加 HTAB 是因为“RFC 9112 §3 允许宽松处理 HTAB”。但 RFC 同一句也允许宽松处理 VT、FF 和裸 CR，这个理由区分不开 HTAB 和 VT。收 VT 的真正依据是题面明确把 FF 判为不当，而 VT 与 FF 同类（HTAB 其实也同类）。建议改成“为保持最小修订，只收 FF 单独分隔和 VT 两例；HTAB 同理可收，但不必须”。选 FF 单独分隔我认为很好：它能拦住只照上游 CHANGES 说法（“不再接受 LF 作分隔符”）实现的部分解。
- **M2（I4 / I7 的分界）。** 在 I7 里写明 §3 末尾的边缘性理由（非空白控制字符；只在版本点号这一个位置能通过的 FF），免得 Codex 读成“按是否旧缺口挑选”。版本号里的 FF 同样是题面的字符，只写“base 也接受”不够。
- **M3（D4 正对照）。** ALT2 作主正对照，ALT1 作第二正对照。验收时写明 gold 的失败只落在 R-c #3 的两个键上（gold 应通过 #1、#2 的 3 个新键），把 gold 判 0 的原因限定在 I4。
- **M4（修订后的复验流程）。** 修订生效后，批量环境复验里本题的正对照要从 gold 换成存档的 ALT2 或 ALT1 补丁（连同 sha256），并在修订元数据里注明“gold 按设计为 0”。否则以后按“48 题 gold 都是 1”复验时，会把本题误报成环境回归。
- **M5（可选、秒级）。** 以 agent 身份在镜像里 `ls /testbed/vendor/llhttp /testbed/vendor/llhttp/build/c`。历史 R05 记载有 Cython 3.0.4、gcc 和 `_http_parser.c`；如果 llhttp 生成的 C 源也在，agent 就可能离线构建出 `.so`，评分时键集会变（新增 c-parser 键、3 个死键翻转，判 0）。这不改处置，只决定事后审计里“构建了 `.so`”那一条是现实风险还是理论风险。
- **可选补强（不必须）：**
  - R-c #1 再加一个原始非 UTF-8 字节的字段名（如 `b"f\xe9o"`，需单独写一个测试函数，因为 `test_bad_headers` 走 UTF-8 编码），拦截“按严格 UTF-8 解码字段名、遇坏字节抛 `UnicodeDecodeError` 而非 `BadHttpMessage`”的实现；
  - R-c #2 加 HTAB 分隔一例。
  - 这两项都不影响 DG1 判 0，由协调者决定是否并入同一轮。

## 7. 对我初判的修正

- **撤回**初判 §5 第 4 步的“解读未定、倾向否”。那一句只用 `\x01` 做了例子，而 base 对 `\x01` 同样接受；空白类控制字符在目标里时 base 会拒绝、gold 会接受，这一点我当时漏了。现同意 I4 为 S1。`\x01` 维持 T3。
- 我初判的退化候选 D 与 DG1 相同，T2b 已由正式评分确认。
- 我初判的 R-c-1（CJK、é、原始 0xE9）和 R-c-2（HTAB、VT）改为采纳主审的 R-c #1（西里尔字母 о 在字段名中部）和 R-c #2（FF 单独分隔、VT）。两者都能让 DG1 判 0，主审版本已有可直接应用的补丁；我的额外实例降为 §6 的可选补强。
- 初判 §4(a) 说“C 扩展不可构建”写得太满，改为“取决于镜像里 `vendor/llhttp` 的内容，未核”（见 M5）。

## 8. 最小后续实验（按顺序）

1. 在当前材料上正式评分 ALT2，预期 1（129/129）。
2. 实施 R-c #1–#3（card 附录 C、D、E），在修订版上正式评分 noop、gold、ALT1、ALT2、DG1。预期：
   - noop 为 0：新增的 #1、#2 三键 FAILED，#3 两键 PASSED；
   - gold 为 0：只有 #3 两键 FAILED，#1、#2 三键 PASSED；
   - ALT1、ALT2 为 1；
   - DG1 为 0：西里尔字母键与 VT 键 FAILED。
   - 可加“只拒 LF”的部分解，预期 0（FF 单独分隔键 FAILED）。
3. ALT1、ALT2 在公开测试文件上跑私有对照（设 `AIOHTTP_NO_EXTENSIONS=1`，与 devcheck 的公开命令相同），预期全部通过。
4. 存档新版本、父版本（expected `79a761b4…`、隐藏树 `eb81f695…`）、理由、触发反例（DG1 账本与 gold 矩阵的 `target_*` 行），并按 M4 更新复验用的正对照；交 Codex 复核。
5. 可选：M5 的 `ls` 核对。

## 9. 保留的分歧与未知

- 与主审没有未决分歧。§6 的几条是写法与流程上的修改，不改变任何结论。
- 未知：
  - 镜像里 `vendor/llhttp` 的内容（M5）；
  - ALT1、ALT2 在公开测试文件上的实际结果（待跑）；
  - 模型实际收到的完整消息与真实求解（清单 33–36，由探针回答）；
  - RFC 9112 §3.2 原文是凭记忆引用，未联网核对。
