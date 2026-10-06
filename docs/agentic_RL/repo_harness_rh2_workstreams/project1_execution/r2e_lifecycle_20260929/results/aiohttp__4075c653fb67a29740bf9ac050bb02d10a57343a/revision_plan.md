# aiohttp 4075c653：R-c 修订方案（第 2 轮：R-c #3 补 CR、TAB；gold 按设计为 0，ALT2 作主正对照）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态**

- **这是第 2 轮。** Codex 对第 1 轮的复核结论是“需小改”（`CR/review_revision_aiohttp_4075.md`）：
  - R-c #1、#2 可接受；
  - I4 确属 v1 §4 第 4 步的 S1；
  - ALT2 作主正对照、ALT1 作第二正对照，依据充分；
  - 对 ALT3 的更正成立。
- **本轮只补了 R-c #3 的两个参数**：请求目标里夹 CR、TAB 两例，仍断言 `BadHttpMessage`。期望从 134 键增到 136 键，两个新键都是 PASSED。
- **第 2 轮修订版试跑 7 个候选，全部与预期一致**（试跑工具，不是正式评分）：
  - ALT2、ALT1 仍为 1；
  - gold 为 0，失败只落在 R-c #3 的四个键上；
  - noop 为 0，仍只差 5 个键；DG1 为 0，仍只差 2 个键；
  - 过严性证据 ALT3、ALT4 仍为 1。
- **gold 按设计为 0，原因是 I4。** gold 接受请求目标里夹 LF、FF、CR、TAB 的请求行；这四种输入 base 原本就拒绝，题面也要求拒绝。按 D4 用 ALT2 作主正对照，不为保住 gold 放宽断言。
- **措辞已按 Codex 收紧**：
  - “gold 切分 + 只拒 LF、FF”的变体只作静态推断，从未实跑；
  - ALT3、ALT4 的相关行为是源码推导与标准库模拟，还没有容器矩阵实测；
  - 失败断言行与 DID NOT RAISE 都是按证据链推定的，正式评分要用完整 eval log 核对。
- **不需要用户决定。** 下一步由协调者送 Codex 复核本轮补改，然后落正式修订单、重建材料与镜像、跑正式评分（§8）。在此之前本题维持 `needs_repair`。

路径约定：仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本题目录。

| 简写 | 指向 |
| --- | --- |
| `PUB` | `runs/r2e_static_prep_20260924/v3/public/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/` |
| `W` | `PUB/worktree`，即解题者看到的 `/testbed` 初态 |
| `PRIV` | `runs/r2e_static_prep_20260924/v3/private/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/` |
| `HT` | `PRIV/hidden_tests/test_1.py`，父版本，1419 行 |
| `HT'` | 第 2 轮修订后的 `test_1.py`，1454 行 |
| `INV` | `runs/r2e_lifecycle_20260929/inv/aiohttp_4075/`，协调者的正式评分账本、私有矩阵与私有对照 |
| `CR` | `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/` |
| `NOOP_LOG` | `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-a_ad0193bb.eval.log`，同一份隐藏测试树的旧机 noop 日志，只用来看回溯行号的报告方式 |

## 0. 与第 1 轮的差异

| 项 | 第 1 轮 | 第 2 轮 |
| --- | --- | --- |
| R-c #3 的输入 | 请求目标里夹 LF、FF 两例 | 加上 CR、TAB，共四例；ids 相应扩成四个 |
| 期望映射 | 134 键（新增 5 键） | 136 键（新增 7 键） |
| 修订后 `test_1.py` | 1452 行，sha256 `81cb7bed…` | 1454 行，sha256 `ec2c2985…`；与第 1 轮只差 3 行：`HT':802-803` 两个新参数，`HT':805` 的 ids 行 |
| 试跑草案 | `draft.json`（`b76b555f…`）、`expected_after.json`（`3bf2e4fe…`） | `draft_r2.json`（`e453d34b…`）、`expected_after_r2.json`（`07341a5d…`） |
| gold 在修订版上失败的键 | LF、FF 两键 | LF、FF、CR、TAB 四键 |
| CR、TAB 的处理 | 以“没有新的已有候选”为由只登记 | 补进断言。Codex 指出第 1 轮的理由不足：gold 本身就是当前材料得 1、同时放行这两例的已有候选，I4 已据此成立（`CR/review_revision_aiohttp_4075.md` §4） |
| R-c #1 依据的措辞 | 把 `W/docs/client_advanced.rst:108-110` 和 `W/aiohttp/http_parser.py:59-65` 直接当作字段名的依据 | 按 Codex §1 更正：文档正文只讲字段名大小写不敏感，它链接的 RFC 7230 §3.2 才规定字段名为 token；源码注释是为 method 写的 token 定义 |
| 推定与实测的区分 | §5.2 写成“失败都是 DID NOT RAISE” | 改为“推定”；ALT3、ALT4 的相关行为注明是推导与模拟 |
| `env_reverify_positive_control` | ALT2，sha256 `f3c60564…` | 不变 |
| 试跑记录 | — | 第 1 轮的 11 份文件（9 份结果、2 份输入）移到 `trials/round1/`，第 1 轮方案与草案另存为 `trials/round1/revision_plan_round1.md`、`revision_draft_round1.json`；第 2 轮 7 份结果与 2 份输入在 `trials/round2/` |

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。三处修改各对应一组 S1，逐项写依据，合并在同一轮完成。

| 项 | 要纠正的 S1 | 触发反例 | 出处 |
| --- | --- | --- | --- |
| R-c #1 | I1（T2c）：R1 唯一的核心断言只用题面示例 `ÿ`（`HT:181`、`HT:184-187`；`PUB/user_prompt.txt:22`）。I3（T2b）：退化候选 DG1 只拒示例字节 | DG1 当前材料正式评分 1.0（`INV/ledger_DG1.jsonl:1`）；私有矩阵里 DG1 的 `hdr_name_cyr_o` 为 ACCEPT（`INV/pcheck_matrix_DG1.json`） | `card.md` §4；`review.md` §2 |
| R-c #2 | I2（T2c）：R2 唯一的核心断言只用题面示例那一行（`HT:683-686`；`PUB/user_prompt.txt:17`）。I3 同上 | 同一次 DG1 评分；矩阵里 DG1 的 `reqline_vt_sep` 为 ACCEPT | 同上 |
| R-c #3 | I4（v1 §4 第 4 步）：gold 把请求目标里夹 LF、FF、CR、TAB 的请求行从拒绝变成接受 | gold 当前材料正式评分 1（`runs/r2e_lifecycle_20260929/env_verify/ledger_gold.jsonl:4`）。矩阵 `target_lf/ff/cr/tab` 四行：base 都是 `BadStatusLine`，gold 都是 ACCEPT（`INV/pcheck_matrix_{none,gold}.json`）。gold 就是同时放行这四例的已有满分候选 | `card.md` §4、附录 G；`review.md` §3；`CR/review_revision_aiohttp_4075.md` §1、§4 |

**不在本轮做的事**：

- I5（P4，题面例 1 的字面代码复现不出问题）：可选的 R-f，card 标为不阻塞。
- I6（T5，3 个期望 FAILED 的死键）：不做 R-a。
- I7（T3）：只登记。

## 2. 公开依据

期望值都由下列公开语义推出，没有照抄 gold 的输出。gold、ALT1、ALT2 通过与否是验证结果，不是依据。

### R-c #1：字段名中部的非 ASCII 字符

- **题面的一般表述**：标题 `PUB/user_prompt.txt:4` 写的是 "Headers with Invalid Characters"；Expected `:22` 要求因为头里有无效字符 `ÿ` 而抛 `BadHttpMessage`。`ÿ` 只是其中一个实例。
- **字段名只能由 token 字符组成**：
  - `W/docs/client_advanced.rst:108-110` 链接 RFC 7230 §3.2。文档正文只讲字段名大小写不敏感，但所链章节规定字段名为 token（Codex 复核 §1 已核对）。
  - 仓库在 `W/aiohttp/http_parser.py:59-65` 按 RFC 9110 写了 tchar 与 token 的注释。这段注释是为 method 写的，但它给出的 token 字符全是 ASCII。
- **为什么选这个字符**：西里尔小写字母 о（U+043E，UTF-8 编码 `d0 be`），放在字段名中部。它不是 `ÿ`，首字节不是 `c3`，也不含 `bf`。下面三种示例拟合都会被它拦下：只拒 `ÿ` 或 `c3 bf`；只检查首字节；只往字符类里加 `\xc3` 或 `\xbf`（card 附录 C）。
- **显式 id**：用 `pytest.param(..., id="nonascii-mid-name")`，键名里不会出现 pytest 对非 ASCII 字符的转义。
- **刻意不测**：原始非 UTF-8 字节的字段名，例如 `f\xe9o`（复核 §6 的可选补强）。gold、ALT1、ALT2 实测都拒绝它（矩阵 `hdr_name_raw_e9`），不加不影响任何已知候选的判定。

### R-c #2：FF 单独作分隔、VT 作分隔

- **题面**：
  - 标题 `:4` 是 "Malformed Status Lines"，描述 `:7` 是 "improperly formatted status lines"；
  - Expected `:23` 把示例 `GET\n/path\x0cHTTP/1.1`（`:17`）判为 "contains improper whitespace and control characters"。
  - 示例里 LF、FF 都用作分隔。VT 与 FF 同属空白类控制字符。
- **请求解析按设计是严格的**：
  - `W/aiohttp/http_parser.py:639` 的注释写明 "Lax mode should only be enabled on response parser."；
  - 作参照的 C 解析器只对响应设宽松标志（`W/aiohttp/_http_parser.pyx:574-586` 与 `:651-655` 对照）。
- **范围（M1）**：为保持最小修订，只收 FF 单独分隔和 VT 两例；HTAB 同理可收，但不必须。
  - 原稿的理由是“RFC 9112 §3 允许接收方宽松处理 HTAB”，已删去：RFC 同一句也允许宽松处理 VT、FF 和裸 CR，这个理由区分不开 HTAB 与 VT（Codex 复核 §1 确认这一更正）。
- **两例各自的作用**：
  - FF 单独作分隔，拦“只拒 LF”式的部分解（复核 §6 M1）；
  - VT 作分隔，拦“只拒示例里那两个字符”的 DG1。
- **不收 HTAB 分隔不影响已知候选的判定**：gold、ALT1、ALT2 实测都拒绝 HTAB 分隔（矩阵 `reqline_tab_sep`），ALT3、ALT4 按标准库模拟也拒绝；DG1 接受 HTAB 分隔，但已被 VT 键拦下。

### R-c #3：请求目标里夹 LF、FF、CR、TAB

- **题面**：Expected `:23` 的理由是状态行 "**contains** improper whitespace and control characters"，说的是“含有”，不是“用它们分隔”。LF、FF 正是示例里的字符；CR、TAB 与它们同属空白类控制字符。
- **base 原本就拒绝这四例**：
  - 四例在 base 上都抛 `BadStatusLine`（`INV/pcheck_matrix_none.json` 的 `target_lf`、`target_ff`、`target_cr`、`target_tab`）。
  - 机制：base 用 `str.split(maxsplit=2)`（`W/aiohttp/http_parser.py:550`），目标里的空白会把目标切成两段，剩下的部分落进版本位，于是 `VERSRE` 校验失败（`:564-566`）。
  - gold 改成只按 SP 切分后，目标原样进入 `URL.build(..., encoded=True)`（`:583-588`），这一步不检查字符，于是四例都被接受（`INV/pcheck_matrix_gold.json`）。
  - 所以这不是“更完整的修复翻转了旧键”，而是修复把题面要求拒绝、base 本来就拒绝的输入放行了。
- **仓库与规范**：
  - 头字段值里的裸 CR、LF、NUL 按 RFC 9110 §5.5-5 拒绝（`:208-210`）；
  - 公开测试 `test_cve_2023_37276`（`W/tests/test_http_parser.py:165-168`），以及 `test_bad_headers` 的 `Foo: abc\rdef`、`Bar: abc\ndef` 两个参数（`:176-177`），都把裸 CR、LF 当作必须拒绝的走私输入；
  - RFC 9112 §3.2 禁止请求目标含空白（Codex 复核 §1 引用并核对）。
- **补 CR、TAB 的理由（第 2 轮）**：
  - gold 本身就是当前材料得 1、同时放行这两例的已有候选，I4 已据此成立。所以这是补完已确认的同一窄问题，不是扩大范围（Codex 复核 §4）。
  - 它们不会误拒按空白宽松切分的实现：即使把 HTAB、裸 CR 也当分隔符（例如 base 的 `str.split()`），目标里夹它们也会切出四段，照样被拒。只有“只按 SP 切分、不检查字符”的写法才会放行它们。
- **断言用父类 `BadHttpMessage`**：
  - C 解析器把状态行、方法、版本错误映射为 `BadStatusLine`，把 `HPE_INVALID_URL` 映射为 `InvalidURLError`（`W/aiohttp/_http_parser.pyx:829-834`）；两者都是 `BadHttpMessage` 的子类（`W/aiohttp/http_exceptions.py:96-106`）。
  - 报状态行错误或报 URL 错误都算对，不会在子类上造出 T1。
- **范围**：只收空白类控制字符夹在请求目标里、且 base 原本就拒绝的情形，不要求任何 base 没有的新行为。题面的 "contains" 已经覆盖这一要求，所以不另做 R-f（复核 §4）。
- **代价**：上游到 3.11.0.dev0 仍是 gold 写法（同仓 `aiohttp__22a12cc2` 公开工作树 `aiohttp/http_parser.py:575-579`），修订后上游同款修复会判 0。本题从此只能作“标明版本的自建题”，批次汇报要显式列出（复核 §3；Codex 复核 §3）。

**I4 与 I7 的分界（M2）**

I4 升为 S1、I7 只登记为 T3，用了两条标准：

- v1 §4 第 4 步：只影响边缘输入、罕见路径的，降为 S2；
- base 是否原本拒绝：区分“修复带来的回归”和“base 已有的旧缺口”。

两条标准指向同一结论，不是按“是不是旧缺口”来挑。

| 输入 | base | gold | 归类 | 理由 |
| --- | --- | --- | --- | --- |
| 请求目标里夹 LF、FF、CR、TAB（四例现在都有断言） | 拒绝 | 接受 | I4，S1 | 修复带来的回归；LF、FF 正是题面示例的字符；可以出现在目标的任意位置；裸 CR、LF 是请求拆分与走私的典型载荷，不是边缘输入 |
| 请求目标里的 `\x01` | 接受 | 接受 | I7，T3 | 不是空白类字符，与题面并举的“不当空白”不同类；base 从未拒绝过它，不是修复引入的 |
| 版本号里的 FF（`HTTP/1\x0c1`） | 接受 | 接受 | I7，T3 | 只在 FF 恰好替代版本点号这一个位置能通过，原因是 `VERSRE` 里的 `.` 没有转义（`W/aiohttp/http_parser.py:67`）。`HTTP/1.1\x0c`、`HTTP\x0c/1.1` 在 base 和 gold 上都被拒（标准库模拟）。属于版本校验的旧缺陷，输入极窄 |
| 字段名里的 `/`（`Fo/o`） | 接受 | 接受 | I7，T3 | ASCII 标点，与题面的非 ASCII 示例不同类；它不是 token 字符，但 base 与 gold 都接受，属于旧缺口 |

修订没有暗中要求关闭 I7：按源码推导与标准库模拟，ALT4 放行上表后三行，而它在修订版上试跑仍得 1（§5.4）。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即 `HT`。同目录的 `conftest.py`、`__init__.py` 不动。
- **草案条目**：一条 `hidden_test_text_replace`，`target` 为 `test_1.py`，三处 edit 按顺序应用。每处 `old` 在当时的文本里恰好出现一次，这与试跑工具和正式修订单的纪律相同。
  1. `old` = `HT:181-184`（从 `"\xffoo: bar",` 到 `def test_bad_headers(...)` 这一行）。`new` 在 `"\xffoo: bar",` 之后插入 R-c #1 的 `pytest.param`。
  2. `old` = `HT:683-686`，即 `test_http_request_bad_status_line_whitespace` 整个函数。`new` = 原函数 + 两个空行 + R-c #2 的新测试。
  3. `old` = `HT:773-775`，即 `test_http_request_parser_bad_nonascii_uri` 整个函数。`new` = 原函数 + 两个空行 + R-c #3 的新测试。
  - 前两处 edit 与第 1 轮逐字节相同；第 3 处只多了两个参数和两个 id。
- **修订后的文件**：`HT'` 共 1454 行，sha256 `ec2c2985…`，`py_compile` 通过。
  - 它与第 1 轮文件只差 3 行，而第 1 轮文件与 card 附录 C、D 两份 diff 应用后的文件逐字节相同（仓库外副本上 `git apply` 核对，两种叠加顺序结果相同）。
- **修订后的位置**：
  - R-c #1 在 `HT':182-185`，断言沿用 `HT':190-191`；
  - R-c #2 在 `HT':693-705`；
  - R-c #3 在 `HT':797-810`。

R-c #1，插在 `test_bad_headers` 参数表的 `"\xffoo: bar",` 之后（新键 `test_bad_headers[py-parser-pyloop-nonascii-mid-name]`）：

```python
        pytest.param(  # non-ASCII (Cyrillic o, UTF-8 d0 be) inside the field name
            "f\N{CYRILLIC SMALL LETTER O}o: bar",
            id="nonascii-mid-name",
        ),
```

R-c #2，插在 `test_http_request_bad_status_line_whitespace` 之后（新键 `test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-ff-separator]` 与 `[py-parser-pyloop-vt-separator]`）：

```python
@pytest.mark.parametrize(
    "line",
    (
        b"GET /path\x0cHTTP/1.1",  # FF alone as a separator
        b"GET\x0b/path HTTP/1.1",  # VT as a separator
    ),
    ids=("ff-separator", "vt-separator"),
)
def test_http_request_bad_status_line_other_whitespace(
    parser: Any, line: bytes
) -> None:
    with pytest.raises(http_exceptions.BadStatusLine):
        parser.feed_data(line + b"\r\n\r\n")
```

R-c #3，插在 `test_http_request_parser_bad_nonascii_uri` 之后（新键 `test_http_request_ctl_in_target_rejected[py-parser-pyloop-<id>]`，`<id>` 为 `lf-in-target`、`ff-in-target`、`cr-in-target`、`tab-in-target`）：

```python
@pytest.mark.parametrize(
    "line",
    (
        b"GET /pa\nth HTTP/1.1",  # LF inside the request-target
        b"GET /pa\x0cth HTTP/1.1",  # FF inside the request-target
        b"GET /pa\rth HTTP/1.1",  # CR inside the request-target
        b"GET /pa\tth HTTP/1.1",  # HTAB inside the request-target
    ),
    ids=("lf-in-target", "ff-in-target", "cr-in-target", "tab-in-target"),
)
def test_http_request_ctl_in_target_rejected(parser: Any, line: bytes) -> None:
    # BadStatusLine (issue wording) or InvalidURLError (C-parser mapping) both ok
    with pytest.raises(http_exceptions.BadHttpMessage):
        parser.feed_data(line + b"\r\n\r\n")
```

**设计说明**：

- **只用文件里已有的名字**：`Any`、`pytest`、`http_exceptions`（`HT:5`、`:9`、`:14`），以及 fixture `parser`（`HT:56-66`）。不新增对仓库测试辅助的依赖，也没有时序、随机或资源因素。
- **裸 CR 不会被当成行尾**：请求解析器只按 `\r\n` 分行，所以 `GET /pa\rth HTTP/1.1` 整个仍是第一行。私有矩阵的 `target_cr` 行用的是同一串字节，base、gold、DG1、ALT1、ALT2 的结果都与上文一致。
- **新键名**：
  - 参数 id 都是显式的 ASCII 串。
  - 键名按现有规则推出：fixture 的 `py-parser`、`pyloop` 在前，参数 id 在后，例如已有的 `test_max_header_field_size[py-parser-pyloop-40960]`。
  - 试跑的 short summary 已逐一核对：第 2 轮 7 次修订版试跑都解析出 136 键，没有 missing，也没有 extra。
- **收集结果**：修订后共收集 141 项，其中 3 项 dev_mode 被排除、2 项因 C 解析器不可用而跳过，剩 136 个键。试跑 summary 为 `3 failed, 133 passed, 2 skipped, 3 deselected`（ALT1–ALT4）。
- **没有扩大 X1 暴露**：按新测试名、参数 id 和新输入 grep 了 v3 的 5 个 aiohttp 公开工作树，都没有命中。第 2 轮新增的 `GET /pa\rth`、`GET /pa\tth` 和 `cr-in-target`、`tab-in-target` 也 grep 过，同样没有命中。
- **刻意不测**：HTAB 作分隔；I7 各项；原始非 UTF-8 字节的字段名。理由见 §2 与 §7。

## 4. 期望映射逐键变化

- **原 129 键逐键不变**：126 个 PASSED；3 个死键 `test_c_parser_loaded`、`test_invalid_character[pyloop]`、`test_invalid_linebreak[pyloop]` 仍为 FAILED。
- **新增 7 键，状态都是 `PASSED`**。按收集顺序插在各自的锚点键之后，FAILED 键仍排在最后，与父版本的排法一致：
  - `test_bad_headers[py-parser-pyloop-nonascii-mid-name]`，插在 `test_bad_headers[py-parser-pyloop-\xffoo: bar]` 之后（R-c #1）；
  - `test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-ff-separator]`、`[...-vt-separator]`，插在 `test_http_request_bad_status_line_whitespace[py-parser-pyloop]` 之后（R-c #2）；
  - `test_http_request_ctl_in_target_rejected[py-parser-pyloop-lf-in-target]`、`[...-ff-in-target]`、`[...-cr-in-target]`、`[...-tab-in-target]`，插在 `test_http_request_parser_bad_nonascii_uri[py-parser-pyloop]` 之后（R-c #3）。
- **合计 136 键**。完整映射见 `revision_draft.json` 的 `expected_after`。正式修订单 expected 部分的 `added` 为这 7 键，`changed`、`removed` 为空。
- **期望从哪里来**：由输入与公开语义推出。gold 恰恰在 R-c #3 四键上是 FAILED，这说明期望不是从 gold 输出抄来的。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，1419 行） | `e9652674…` |
  | 父版本 `expected_output.json`（129 键） | `79a761b4…` |
  | 父版本隐藏测试树 | `eb81f695…`，`material_revisions` 为空 |
  | 第 2 轮修订后 `test_1.py`（`HT'`，1454 行） | `ec2c2985…` |
  | 第 2 轮试跑用 `draft_r2.json`（副本在 `trials/round2/`） | `e453d34b…` |
  | 第 2 轮试跑用 `expected_after_r2.json`（136 键，副本在 `trials/round2/`） | `07341a5d…` |
  | 第 1 轮修订后 `test_1.py`（1452 行） | `81cb7bed…` |
  | 第 1 轮试跑用 `draft.json`、`expected_after.json`（134 键，副本在 `trials/round1/`） | `b76b555f…`、`3bf2e4fe…` |

  父版本三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:4` 一致，也与正式评分日志头部的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致（例如 `INV/logs_ALT2/evallog_replay-r2e-inv-4075-ALT2_a8dbd4a8.eval.log:6`）。本题至今没有材料修订。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**

- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置也做了简化。
- **镜像**：两轮都用派生镜像 `sha256:f483bab46f9e…`，配方 `r2e_derive_v1+sysconfig_v1`。它与 `runs/r2e_lifecycle_20260929/env_verify/ledger_{noop,gold}.jsonl:4`、`INV/ledger_{DG1,ALT1,ALT2}.jsonl:1` 的 `image_id_actual` 相同。
- **输入**：
  - 补丁、草案与期望文件都从磁盘原件上传，没有经过 Write 工具。第 2 轮沿用第 1 轮上传的 6 个补丁，只新传了 `draft_r2.json`、`expected_after_r2.json`；远端文件名与第 1 轮不同，没有覆盖第 1 轮的输入。
  - `draft_r2.json` 由脚本生成，并核对过：前两处 edit 与第 1 轮逐字节相同；按试跑工具的算法应用后，与第 1 轮文件只差 3 行。
  - 6 个补丁都在仓库外的 base 副本上 `git apply --check -v` 通过（输出都点名了 `aiohttp/http_parser.py`），应用后 `py_compile` 通过。副本里 `aiohttp/http_parser.py` 的 blob 是 `0a1586b8`，与 gold 补丁 index 行一致。
- **应用与解析**：
  - 所有带补丁的试跑都是 `RH2_APPLY_RC=0`，只应用 `aiohttp/http_parser.py`。
  - 修订版试跑都报 `RH2_TRIAL_EDITS_APPLIED=1`。第 2 轮每次都解析出 136 键，没有 missing 或 extra。
- **耗时与并发**：
  - 第 2 轮 2026-09-29 07:54–08:04（本机时间 +08），7 次试跑，同一时间最多 2 个；单次墙钟 91–168 s，测试阶段 13.5–15.4 s，pytest 自报 10.7–12.2 s。
  - 第 1 轮 07:06–07:17，9 次试跑。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop（试跑） | 0：只差两个目标键（`\xffoo` 与原例请求行），129 键齐全 | `trials/round1/env_noop_current.json` |
| gold（试跑） | 1：129/129 | `trials/round1/env_gold_current.json` |
| noop、gold（正式） | 0（127/129）、1（129/129） | `runs/r2e_lifecycle_20260929/env_verify/ledger_{noop,gold}.jsonl:4` |
| DG1（正式） | **1.0**：129/129，即触发反例 | `INV/ledger_DG1.jsonl:1` |
| ALT1（正式） | 1.0：129/129 | `INV/ledger_ALT1.jsonl:1` |
| ALT2（正式，协调者跑） | 1.0：129/129，`keys_equal` 为 true | `INV/ledger_ALT2.jsonl:1` |

ALT2 正式评分的细节：

- 走 v8 任务面、缺省时限。本题 v3–v8 的材料相同。
- 补丁 sha256 为 `f3c60564…`，与 `cands/` 存档一致；投影只含 `aiohttp/http_parser.py`。
- 日志 `INV/logs_ALT2/evallog_replay-r2e-inv-4075-ALT2_a8dbd4a8.eval.log`：
  - L6 隐藏测试树为 `eb81f695…`；
  - L8 `RH2_SETUP_APPLY_RC=0`；
  - L39、L89 两个原目标键 PASSED；
  - L475 汇总为 `3 failed, 126 passed, 2 skipped, 3 deselected`。

**公开测试私有对照**（协调者跑的）：

- 条件：agent 身份、一次性容器，脚本 `cands/pcheck_public_tests.sh`。C 解析器不可导入，所以按公开命令设了 `AIOHTTP_NO_EXTENSIONS=1`，与 devcheck 的公开命令相同。
- 结果：ALT1、ALT2、gold 三者相同（`INV/pcheck_public_{ALT1,ALT2,gold}.json`）：
  - `tests/test_http_parser.py`：124 passed、5 skipped、3 deselected，退出 0；
  - `tests/test_http_exceptions.py`、`test_multipart.py`、`test_client_proto.py`：135 passed，退出 0。
- 结论：两个替代正对照都没有公开回归。数字与 devcheck 在 base 上的公开命令结果相同（`review.md` §2）。

**ALT2 私有矩阵**（`INV/pcheck_matrix_ALT2.json`，root 身份，只作行为检查）。我逐行比对了它与同目录 none、gold、DG1、ALT1 的矩阵：

- **ALT2 与 gold 不同的行**：
  - `target_lf`、`target_ff`、`target_cr`、`target_tab`：gold 接受，ALT2 抛 `BadStatusLine`，即恢复了 base 的拒绝。这正是 I4，四行现在都有断言。
  - `target_ctl01`、`version_ff`：base 与 gold 都接受，ALT2 抛 `BadStatusLine`。原因是 `REQUEST_LINE_CTL` 覆盖全部 C0 控制字符，所以 ALT2 在这两行上和 ALT1 一样比 base 严（T3 行）。
- **ALT2 与 ALT1 不同的行**：只有 `hdr_name_slash`，ALT1 拒绝，ALT2 与 gold 一样接受。
- **其余行**：`keep_*` 各行与 `resp_no_reason` 五个候选一致。`resp_nonascii_name` 上 base 接受、其余四个候选拒绝：`HeadersParser` 是请求与响应共用的，这属于 A2 的未测范围，两种做法都可以。

### 5.2 第 2 轮修订版验收

结果文件为 `trials/round2/rev_<候选>.json`。“失败断言”一列写 `HT'` 的行号；失败行与失败类型（DID NOT RAISE）都是按 §5.3 的证据链推定的，正式评分时用完整 eval log 核对。

| 候选 | 补丁（sha256 前 8 位） | 角色 | 应得 | 应不符的键 → 失败断言（推定） | 第 2 轮试跑 | 第 1 轮修订版 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALT2 | `cands/aiohttp_4075_ALT2.patch`（`f3c60564`） | **主正对照**（D4 替代正对照） | 1 | — | 1：136 键逐键一致 | 1 | 1.0（正式） |
| ALT1 | `cands/aiohttp_4075_ALT1.patch`（`d3a4b23c`） | 第二正对照，比 gold 更严 | 1 | — | 1：136 键逐键一致 | 1 | 1.0（正式） |
| gold | `PRIV/gold.patch`（`f99fe925`） | 原 gold，**按设计为 0**（I4） | 0 | `lf-in-target`、`ff-in-target`、`cr-in-target`、`tab-in-target` → 810 | 0：`status_diff` 恰为这 4 键；#1、#2 的 3 个新键 PASSED | 0（只差 LF、FF 两键） | **1**（正式） |
| noop | 无 | — | 0 | `\xffoo`、`nonascii-mid-name` → 191；原例 → 690；`ff-separator`、`vt-separator` → 705 | 0：`status_diff` 恰为这 5 键；#3 四键 PASSED | 0（同样 5 键） | 0 |
| DG1 | `cands/aiohttp_4075_DG1.patch`（`f2d8d6f0`） | 第 3 步退化候选（I3） | 0 | `nonascii-mid-name` → 191；`vt-separator` → 705 | 0：`status_diff` 恰为这 2 键；#3 四键 PASSED | 0（同样 2 键） | **1.0**（正式） |
| ALT3 | `cands/aiohttp_4075_ALT3.patch`（`653546cb`） | 过严性证据，不是正对照（协调者建议） | 1 | — | 1：136 键逐键一致 | 1 | 未跑，静态推断为 1 |
| ALT4 | `cands/aiohttp_4075_ALT4.patch`（`0ef49961`） | 过严性证据，不是正对照（补 ALT3 覆盖不到的版本号 FF） | 1 | — | 1：136 键逐键一致 | 1 | 未跑，静态推断为 1 |

**ALT3 与 ALT4 的写法**：两者都以 gold 原样为基础，只多一处检查（与 gold 的逐行差异各为 4 行、5 行）。

- ALT3：请求行里出现 `[\t\n\x0b\x0c\r]` 就抛 `BadStatusLine`，即复核 `review.md` §4 的“最小变体”。
- ALT4：先按 SP 切分，请求目标里出现 `[\t\n\x0b\x0c\r]` 时抛 `BadStatusLine`。
- 两个补丁都由脚本从 gold 应用后的副本生成 diff，再在仓库外的 base 副本上 `git apply --check -v` 并 `py_compile`；往返应用后与生成源逐字节相同。

### 5.3 失败断言的定位依据

**限制**：试跑结果只保留 stdout 的最后 8000 个字符，只剩 short summary；长键名的 FAILED 行被截断，看不到回溯。所以失败行和失败类型都按下面的证据链推定，不能当作已核实的日志全文；正式评分时要用完整 eval log 逐行核对。

1. **每个相关测试只有一处可失败的断言**。目标键与新键的测试体，都是一个 `with pytest.raises(...)` 块包住一次 `feed_data`。所以这些键上的任何 FAILED，都是这一个块的失败。
2. **失败类型推定为 DID NOT RAISE**。私有矩阵给出了各候选对这些输入的真实行为（`INV/pcheck_matrix_*.json`，root 身份、一次性容器），应不符的键全部对应 ACCEPT：
   - noop：`ex_hdr_name_ff`、`hdr_name_cyr_o`、`ex_reqline_lf_ff`、`reqline_ff_sep`、`reqline_vt_sep`；
   - gold：`target_lf`、`target_ff`、`target_cr`、`target_tab`；
   - DG1：`hdr_name_cyr_o`、`reqline_vt_sep`。
   矩阵的构造参数与隐藏测试的 fixture 相同，输入字节也与新测试逐字节相同。
3. **回溯行号的报告方式**。同一份隐藏测试树的 noop 日志把 DID NOT RAISE 报在 `with` 块内的 `feed_data` 行：`NOOP_LOG:236,242` 报 `test_1.py:187`，`NOOP_LOG:251,256` 报 `:686`。在 `HT'` 里，对应行分别是 191（test_bad_headers）、690（原例）、705（R-c #2）、810（R-c #3）。
4. **试跑确实用的是 `HT'`**。第 2 轮修订版试跑的 SKIPPED 行从父版本的 `test_1.py:233`、`:1120`（`INV/logs_DG1/evallog_replay-r2e-inv-4075-DG1-_74541a2c.eval.log:470-471`）移到 `:237`、`:1155`。这与三处插入的 +4、+15、+16 行一致；第 1 轮是 `:1153`，差的 2 行正是 R-c #3 新增的两个参数。

### 5.4 ALT3、ALT4 与过严性

**要回答的问题**：两个正对照都拒绝目标里的 `\x01` 和版本号里的 FF，ALT1 还拒绝字段名里的 `/`（T3 行）。需要证明：只放行这些输入、其余都对的实现，在修订版上仍得 1，即修订没有暗中要求关闭 I7。

**ALT3 不能单独回答“版本号 FF”这一半**：

- FF 本身就在 `[\t\n\x0b\x0c\r]` 里，整行检查会拒绝 `GET /path HTTP/1\x0c1`。
- 所以 `review.md` §4 所说“最小变体……仍接受……版本号里的 FF”不成立（Codex 复核 §2 确认）。ALT3 只能说明 `/` 和目标里的 `\x01` 没有被暗中要求。
- ALT4 只检查请求目标，三项都放行。

**证据层次**：下表里 ALT3、ALT4 一列是源码推导与标准库模拟，还没有容器矩阵实测。

- 模拟脚本不导入 aiohttp，按各候选的正则与切分逻辑推演。
- 我先用它复现协调者对 none、gold、DG1、ALT1、ALT2 的 5 份实测矩阵，请求类 20 行 × 5 个候选共 100 格，全部一致；再用它推 ALT3、ALT4。
- 协调者落材料后对 ALT3、ALT4 各跑一次私有矩阵，才能把这两列换成执行证据（§8 第 5 条）。

| 输入 | base | gold | ALT1 | ALT2 | ALT3 | ALT4 |
| --- | --- | --- | --- | --- | --- | --- |
| `Fo/o: bar`（`hdr_name_slash`） | 接受 | 接受 | 拒绝 | 接受 | 接受 | 接受 |
| `GET /pa\x01th HTTP/1.1`（`target_ctl01`） | 接受 | 接受 | 拒绝 | 拒绝 | 接受 | 接受 |
| `GET /path HTTP/1\x0c1`（`version_ff`） | 接受 | 接受 | 拒绝 | 拒绝 | **拒绝** | 接受 |
| R-c 新键的 7 个输入 | 只拒 #3 四例 | 只拒 #1、#2 三例 | 全拒 | 全拒 | 全拒 | 全拒 |
| 证据 | 矩阵实测 | 矩阵实测 | 矩阵实测 | 矩阵实测 | 推导与模拟 | 推导与模拟 |

**对 129 个原键**：按源码推导，ALT3、ALT4 的行为与 gold 相同。我用 AST 扫描了 `HT'` 的全部字面量，请求行含 `[\t\n\x0b\x0c\r]` 的只有原例和新增的 6 个输入；原例在 gold 下已因 SP 切分失败而抛 `BadStatusLine`，两个变体的检查只是更早抛同一个异常。

**结论**：ALT3、ALT4 在第 2 轮修订版上都得 1（136/136，试跑实测）。结合上表的推导，修订不要求关闭 I7 的三项，也不要求比“拒空白类控制字符”更严。

### 5.5 判读（按 v1 §5 的验收要求）

- **正对照 1、noop 0**：成立。
  - 主正对照 ALT2 满足公开要求：字段名检查与 gold 相同；请求行拒绝全部 C0 控制字符和 DEL，并按单个 SP 切分。
  - 当前材料上正式评分 1.0；公开测试私有对照无回归；第 2 轮修订版试跑 136/136。
  - ALT2 由主审编写，经复核推荐、协调者正式评分；它不是独立求解。
- **误判已纠正**：
  - DG1 在当前材料上正式评分 1.0，修订后为 0，失败恰在它拟合示例的两处；
  - gold 式修复（包括上游同款）当前为 1，修订后为 0，失败恰在 R-c #3 四键。这是按设计的结果（I4、D4）。
- **已知相关的错误候选为 0**：DG1；gold 式修复。
- **没有误拒**：比 gold 更严的 ALT1 得 1；在 I7 上比两个正对照更宽的 ALT3、ALT4 也得 1。
- **旧键不受影响**：第 2 轮 7 次修订版试跑里，父版本 129 键的观测状态都与父版本期望一致；唯一的例外是 noop 的两个原目标键，它们本来就失败。
- **三处的分工**：
  - 只有 #1 拦得住 DG1 的字段名拟合；
  - #2 的 VT 键拦得住 DG1 的请求行拟合；
  - 只有 #3 拦得住 gold 式修复，因为 gold 通过 #1、#2；
  - #2 的 FF 单独分隔键，在已知候选里与 VT 键的作用重叠。按 card 附录 C 保留它，作为“示例字符本身是唯一分隔符”的非示例实例；它不会误拒任何正对照。
- **仍待**：Codex 复核本轮补改；正式评分（§8）。

## 6. M1–M5、协调者建议与 Codex 复核意见的落实

| 项 | 要求 | 落实 | 位置 |
| --- | --- | --- | --- |
| M1 | 改写 R-c #2 不收 HTAB 的理由 | 改成“为保持最小修订，只收 FF 单独分隔和 VT 两例；HTAB 同理可收，但不必须”，删去“RFC 允许宽松处理 HTAB”这一理由 | §2 R-c #2；`revision_draft.json` 的 `items[1].scope_note_M1` |
| M2 | 写清 I4 与 I7 的分界 | 按“base 是否原本拒绝”和“输入是否窄而罕见”分列四类输入；用 ALT4 说明修订没有暗中要求关闭 I7 | §2 末尾的分界表；§5.4；`items[2].boundary_M2` |
| M3 | 定正对照主次 | ALT2 为主、ALT1 为第二；gold 按设计为 0，只在 R-c #3 四键失败、#1 与 #2 三键通过，两轮试跑都证实；理由为 I4 | §5.2、§5.5；`positive_control*`、`gold_expected_after`、`gold_status` |
| M4 | 修订生效后，批量环境复验的正对照换成存档补丁 | 写入落地后事项；`revision_draft.json` 有 `env_reverify_positive_control`（ALT2 路径与 sha256），另有备选 `env_reverify_positive_control_fallback`（ALT1）。第 2 轮不改 | §8 第 6 条 |
| M5 | 核对 C 扩展能否离线构建（可选） | 协调者已核，见下；结论写成推断 | 本节下方；`dead_keys` |
| 协调者建议 | 加 ALT3（复核 §4 的最小变体）作过严性证据 | 已做，两轮修订版试跑都得 1。因为 ALT3 覆盖不到版本号 FF，另加 ALT4，同样得 1 | §5.2、§5.4 |
| Codex 第 1 条 | R-c #3 补请求目标里的 CR、TAB，期望 134 → 136 | 已补，第 2 轮试跑 7 个候选全部与预期一致 | §2 R-c #3、§3、§4、§5.2 |
| Codex 第 3 条 | 分清推定、推导与实测 | “gold 切分 + 只拒 LF、FF”的变体只作静态推断；ALT3、ALT4 的相关行为注明是推导与模拟；失败行与 DID NOT RAISE 注明为推定 | §5.2–§5.4、§7 |
| Codex §1 核对 | R-c #1 依据的出处措辞 | 改为“文档链接的 RFC 7230 §3.2 规定字段名为 token”；源码注释注明是为 method 写的 | §2 R-c #1 |

**M5 的核对与推断**：

- 核对条件：agent 身份、一次性容器，脚本 `cands/pcheck_cext.sh`，结果在 `INV/pcheck_cext_agent.json`。
- 核对结果：
  - `/testbed/vendor/llhttp` 是空目录，只有 `.` 与 `..`；
  - 没有 `aiohttp/*.so`；
  - 有 `/usr/bin/gcc`、`/usr/bin/cc`，也有预生成的 `aiohttp/_http_parser.c` 与 `.pyx`；
  - `aiohttp.http_parser.HttpRequestParserC` 为 None。
- **推断**（没有实际尝试构建）：
  - `aiohttp._http_parser` 扩展需要 `vendor/llhttp/build/c/llhttp.c`、`vendor/llhttp/src/native/{api,http}.c`，以及 `vendor/llhttp/build` 下的头文件（`W/setup.py:29-42`）。
  - 这些源码要从 GitHub 子模块拉取，再用 npm 构建（`W/.gitmodules:1-4`、`W/vendor/README.rst:7-21`），而解题环境不联网。
  - 所以离线构建不出 C 扩展，期望为 FAILED 的三个死键不受修订影响。
  - 探针事后审计里“构建了 `.so`”一条仍保留，但按理论风险对待。

## 7. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**：

- **R1**：字段名含非 ASCII 字符 → `BadHttpMessage`。示例 `\xffoo`（`HT':181`）与非示例的 `nonascii-mid-name`（`HT':182-185`）。
- **R2**：请求行含不当空白或控制字符 → `BadStatusLine`。示例那一行（`HT':687-690`），以及 FF 单独分隔、VT 分隔（`HT':693-705`）。
- **R2'**：请求目标里夹 LF、FF、CR、TAB → `BadHttpMessage`（`HT':797-810`）。
- **旧行为 P1–P8**（`card.md` §2，`analysis_before_history.md` §3）：原有 127 个回归键不变。包括：头字段值里的 UTF-8 与 cp1251 仍接受；非法或非 ASCII 的请求目标抛 `InvalidURLError`；Py 解析器接受路径里的 UTF-8；`getpath ` 的消息里没有转义换行；`LineTooLong` 的长度口径不变；已有的各项拒绝不变；响应解析保持宽松。

**仍未覆盖，维持登记**：

- **HTAB 作请求行分隔**：见 M1。gold、ALT1、ALT2 实测拒绝，ALT3、ALT4 按模拟拒绝；DG1 接受，但已被 VT 键拦下。
- **I7（T3）**：目标里的 `\x01`、版本号点位的 FF、字段名里的 `/`，以及空字段名会抛 `IndexError`。只登记，不断言。
- **原始非 UTF-8 字节的字段名**（`f\xe9o`）：gold、ALT1、ALT2 实测都拒绝，没有断言。
- **“gold 切分 + 只显式拒 `\n`、`\x0c`”的变体**：只作静态推断，从未实跑。按推断，它在第 1 轮修订版上可得 1；第 2 轮补上 CR、TAB 后，它会在 `cr-in-target`、`tab-in-target` 两键失败而得 0。第 1 轮方案把这一点列为缺口，本轮已由新断言关闭。
- **响应解析与 multipart 共用的 `HeadersParser`**：gold 和各替代解都拒绝响应里的非 ASCII 字段名，base 接受（矩阵 `resp_nonascii_name`）。这是 A2 的未测范围，两种做法都可以。
- **I6（T5）死键**：见 §6 的 M5。另外，如果以后派生配方构建了 C 扩展，死键会翻转，新增的测试也会多出 `c-parser` 参数键，期望要同步修订。这是旧风险 R20，仍然有效。
- **其它**：
  - I5（P4）：可选的 R-f 照旧；
  - I8（X1）：修订后本题比上游更严，上游同款修复判 0；
  - I9（E3）：控制面暴露，已交 A 线，照旧作事后审计项。
- **探针事后审计在修订后的变化**（`card.md` §7）：
  - 第 1 条（`hdr_name_cyr_o`、`reqline_vt_sep`）已由测试覆盖；
  - 第 2 条（`target_lf`、`target_ff`、`target_cr`、`target_tab`）四行现在都由测试覆盖，修订版上不必再作审计项；
  - 第 3 条（改控制面文件、构建 `.so`）不变。

## 8. 落地后事项与交接

**协调者待办**：

1. **Codex 复核本轮补改**（R-c #3 加 CR、TAB 与相关措辞）。通过后再落正式材料。
2. **落正式修订单**：
   - 把 `revision_draft.json` 的 `revisions` 落为一条 `hidden_test_text_replace`（`target` 为 `test_1.py`，三处 edit）；
   - expected 部分 `added` 7 键，`changed`、`removed` 为空，修订后 136 键；
   - reason 写明“gold 按设计为 0（I4）；正对照为 ALT2（D4），备选 ALT1”。
3. **重建材料与派生镜像**。派生镜像里的 `/rh2_private/r2e_tests` 会随之更新。核对只有本题的评分包变化，公开包不变。
4. **正式评分**，按 §5.2 判读：

   | 候选 | 应得 | 应不符的键 |
   | --- | --- | --- |
   | ALT2 | 1 | — |
   | ALT1 | 1 | — |
   | gold | 0 | 只有 R-c #3 四键 |
   | noop | 0 | 5 键 |
   | DG1 | 0 | 西里尔字母键与 VT 键 |
   | ALT3 | 1 | —（协调者已说明落材料后补跑） |
   | ALT4 | 1 | —（可选） |

   同时核对三项：投影只含 `aiohttp/http_parser.py`；隐藏测试树摘要为新版本；136 键严格相等。
5. **用完整 eval log 核对失败行与失败类型**（本方案里都是推定），应当都是 DID NOT RAISE：
   - gold 在 810；
   - noop 在 191、690、705；
   - DG1 在 191、705。
   另外，用 `cands/pcheck_matrix.sh` 对 ALT3、ALT4 各跑一次私有矩阵，把 §5.4 的推导与模拟换成执行证据。
6. **M4**：修订生效后，批量环境复验里本题的正对照从 gold 换成存档的 ALT2，备选 ALT1：
   - ALT2：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/cands/aiohttp_4075_ALT2.patch`，sha256 `f3c6056416e15fa36521dd196f66315cee5cc2197a555d4f8087fcc4304c20c2`；
   - ALT1：同目录的 `aiohttp_4075_ALT1.patch`，sha256 `d3a4b23c79944783ad9abe1fd0d0b26c1fcc5e7e30d62da56605b2211d91f3f8`；
   - 复验记录和修订元数据里写明“gold 按设计为 0”。否则按“gold 都是 1”复验时，会把本题误报成环境回归。
   - `INV/aiohttp_4075_ALT2.patch` 是同一文件，摘要相同。
7. **devcheck**：公开包不变，在新镜像上按原命令复跑一次即可，预期结论不变。
8. **保存**父版本、新版本、理由和触发反例：
   - DG1 的正式账本 `INV/ledger_DG1.jsonl:1`；
   - gold 私有矩阵的 `target_*` 四行（`INV/pcheck_matrix_gold.json`），对照 `INV/pcheck_matrix_none.json`。
9. **之后改题卡**：
   - 正对照改为 ALT2（D4），记录 gold 在修订版上为 0；
   - 采用 M1、M2 的措辞，以及 Codex §1 对 R-c #1 依据的更正；
   - X1 补一句“修订后比上游更严”；
   - 记录对 `review.md` §4 最小变体说法的更正；
   - 事后审计规则按 §7 更新；
   - 正式验收与 Codex 复核通过后，按 v1 §2 重判四项用途。

**边界**：

- **只做 R-c**：不改题面，不删键，不放宽已有断言，期望也没有照抄 gold 的输出。三处都有公开依据，不涉及 P5，**不需要用户决定**。
- **没有越界**：
  - 没写 `s2_r2e` 下的正式材料与 pins，没改生产代码；
  - 远端只在 `/work/r2e/trials/lc_aiohttp_4075/4075c653/` 下上传文件并运行试跑工具（第 1 轮 9 次，第 2 轮 7 次），结果已取回 `trials/round1/`、`trials/round2/`。
- **本轮写或改的文件**：
  - `revision_plan.md`：按第 2 轮重写；第 1 轮原文存为 `trials/round1/revision_plan_round1.md`。
  - `revision_draft.json`：由脚本生成，保证 `revisions` 与 `expected_after` 与试跑所用的 `trials/round2/draft_r2.json`、`expected_after_r2.json` 一致；第 1 轮原文存为 `trials/round1/revision_draft_round1.json`。
  - `trials/round1/`：第 1 轮的 11 份文件从 `trials/` 移入，加上两份第 1 轮原文。
  - `trials/round2/`：7 份试跑结果与 2 份试跑输入。
  - `cands/` 下的补丁本轮没有改动。
