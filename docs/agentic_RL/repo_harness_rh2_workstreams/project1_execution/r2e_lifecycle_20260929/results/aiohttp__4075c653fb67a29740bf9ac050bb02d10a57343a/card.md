# aiohttp__4075c653 题卡（R2E 单题闭环，统一标准 v1）

2026-09-29 · 私有主审。依据：`analysis_before_history.md`（读历史前封存）、`old_findings_delta.md`，以及新机器上的实跑结果。新机器镜像为 `sha256:f483bab4…`，配方 `r2e_derive_v1+sysconfig_v1`。独立复核尚未进行。

**结论：`needs_repair`，修订必做。**

- 新机器上已复验环境与评分条件：noop 0、gold 1，devcheck 的全部检查都为真。
- 测试层有 3 个 S1，都要修：
  - 两条核心断言只用题面示例的字面值（T2c ×2）；
  - 退化候选 DG1 正式评分 1.0（T2b）；
  - gold 让请求目标里的 LF、FF、CR、TAB 从拒绝变成接受（第 4 步）。
- 三处修订都在预授权模板 R-c 内。其中 R-c #3 会让原 gold 判 0，按 D4 用替代解作正对照。

## 1. 题目与版本

- **任务**：加固 aiohttp 3.9.0b0 的纯 Python 请求解析器，有两条核心要求。
  - R1：头字段名含非 ASCII 字符（题面例子是 `ÿ`）时，抛 `BadHttpMessage`。
  - R2：请求行含不当空白或控制字符（题面例子是 `GET\n/path\x0cHTTP/1.1`）时，抛 `BadStatusLine`。
- **gold 的改法**：`HDRRE` 的字符类加上 `\x7F-\xFF`；请求行改为 `split(" ", maxsplit=2)`。
- **材料**：
  - expected sha256 `79a761b4…`，共 129 个键：126 个 PASSED，3 个 FAILED（C 扩展缺失造成的死键）；
  - 隐藏测试树 `eb81f695…`；
  - 没有材料修订；v3–v7 的材料对本题相同。

## 2. 关键映射

| 需求 | 公开依据 | 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| R1：字段名含非 ASCII → `BadHttpMessage` | 题面 L4、L22；RFC 9110 的 token 定义（`HP` L59-65 注释） | `test_bad_headers[py-parser-pyloop-\xffoo: bar]` | 只有示例一例（T2c） | noop F / gold P。DG1 也是 P，但它接受西里尔字母和 `\xe9` 字段名（私有矩阵） |
| R2：请求行含不当空白/控制字符 → `BadStatusLine` | 题面 L4、L7、L23 | `test_http_request_bad_status_line_whitespace[py-parser-pyloop]` | 只有示例一行（T2c） | noop F / gold P。DG1 也是 P，但它接受用 VT、TAB 分隔的请求行 |
| R2'：请求目标里夹 LF/FF 同样要拒绝 | 同上；另有 base 旧行为和仓库的严格解析约定（附录 G） | 无 | 缺失，而且 gold 在这里回归 | 私有矩阵：base 抛 `BadStatusLine`，gold 接受 |
| 旧行为：头字段值和路径里的 UTF-8、`\xff` 目标 → `InvalidURLError`、`getpath `、`LineTooLong` 口径、响应解析宽松 | 公开测试 | 其余 127 个键 | 覆盖 | gold、ALT1、DG1 三者都是 129/129 |

## 3. 八方面：已查与未查

| 方面 | 已查 | 未查或未知 |
| --- | --- | --- |
| 公开需求 | 题面、公开测试、调用方、C 解析器的错误映射 | 模型实际收到的完整消息 |
| 材料与初始问题 | 哈希；隐藏测试 = 公开测试 + 两处新增；noop 失败原因是 DID NOT RAISE | — |
| 测试是否测到要求 | 隐藏测试 1419 行全读，129 个键逐组看过 | — |
| 是否误拒合理解 | ALT1（比 gold 更严）得 1，没有 T1 | — |
| 回归与 gold | 发现 gold 的请求目标回归 | multipart 与客户端的行为变化没跑 |
| 开发条件 | 新机 devcheck：agent 身份、正式启动链，7 条命令约 27 秒跑完 | — |
| 交付与评分边界 | 投影只含 `aiohttp/http_parser.py` | 镜像里两个未导出的 untracked 文件的内容 |
| 题目关系 | 同仓 1c1c0ea3、22a12cc2 的初态含本题修复和隐藏目标测试原文（X1） | — |

## 4. 问题与证据

| ID | v1 编号 | 严重度 | 内容 | 证据层次 |
| --- | --- | --- | --- | --- |
| I1 | T2c | S1 | R1 的断言只用示例 `ÿ` | 读码；DG1 实跑佐证 |
| I2 | T2c | S1 | R2 的断言只用示例那一行 | 读码；DG1 实跑佐证 |
| I3 | T2b | S1 | DG1 只拒示例字节，正式评分得 1.0 | 当前 CPU，正式评分 |
| I4 | G1，经第 4 步 | S1 | gold 接受请求目标里的 LF/FF/CR/TAB，而 base 会拒绝 | 当前 CPU，私有矩阵 |
| I5 | P4 | 登记 | 题面例 1 的字面代码在 base 上已经会抛异常，照抄复现不出问题 | devcheck |
| I6 | T5 | 登记 | 3 个期望 FAILED 键是 C 扩展缺失造成的，正确修复不会翻转 | 当前 CPU |
| I7 | T3 | 登记 | 旧缺口：字段名里的 `/`、`?`；请求目标里的 `\x01`；版本号里的 FF；空字段名会抛 `IndexError` | 读码；私有矩阵 |
| I8 | X1 | 登记 | 本题答案和目标测试原文出现在同仓两题的初态里 | 核对过公开包 |
| I9 | E3（通用问题） | 事后审计项 | 评分时会加载候选能改的 `aiohttp/pytest_plugin.py` 和 `setup.cfg` | 读码 |

环境层面不需要修复，本次引用的新机条件已经覆盖。

## 5. 修订（必做）与验收

- **R-c #1**（对应 I1）：在 `test_bad_headers` 里加一个非示例的非 ASCII 字段名 `f` + 西里尔字母 о + `o`，id 为 `nonascii-mid-name`（附录 C）。
- **R-c #2**（对应 I2、I3）：新增两例，各用 FF 单独分隔、VT 分隔，都要求抛 `BadStatusLine`（附录 C）。
- **R-c #3**（对应 I4）：新增两例，请求目标里分别夹 LF、FF，断言抛父类 `BadHttpMessage`（附录 D）。依据和可推翻条件见附录 G。
- expected 新增 5 个键，状态都是 PASSED，总数从 129 变为 134（附录 E）。
- **可选 R-f**（对应 I5）：把题面例 1 的 `.encode()` 去掉。base 上的证据 devcheck 已经给出，不做也不阻塞。

验收矩阵：

| 候选 | 当前材料（新机实跑） | 加上 R-c #1/#2 后（按私有矩阵推定） | 再加上 #3 后（按私有矩阵推定） |
| --- | --- | --- | --- |
| noop | 0（127/129） | 0（新增 3 键 F） | 0（#3 两键 P，因为 base 拒绝） |
| gold | 1 | 1 | **0**：#3 两键 F，记录在案 |
| ALT1 | 1 | 1 | 1 |
| ALT2（gold 加请求行控制字符检查，附录 F） | 未跑，预测 1 | 预测 1 | 预测 1 |
| DG1 | **1**（T2b） | 0：西里尔字母键和 VT 键 F | 0 |

- 验收还要补三件事：
  - 修订版材料上，对上表 5 个候选各跑一次正式评分；
  - 以 ALT1、ALT2 各跑一次私有对照：公开的 `tests/test_http_parser.py`、`test_multipart.py`、`test_client_proto.py`、`test_http_exceptions.py`，确认没有公开回归；
  - Codex 复核。
- 需要保存：父版本（`79a761b4…` / `eb81f695…`）、理由、触发反例（DG1 的账本，以及私有矩阵里 gold 的 `target_*` 各行）。

## 6. v1 四项用途

| 用途 | 结论 | 条件或理由 |
| --- | --- | --- |
| problem_localization（问题定位） | yes | — |
| capability_comparison（能力比较） | conditional | 需满足两项：<br>1. 完成独立复核；<br>2. 用原版时预登记事后审计（见下方"事后审计"），或者等修订版验收完再用 |
| training_candidate（训练候选） | no | R-c #1–#3 验收通过并经 Codex 复核后，可改为 yes |
| heldout_candidate（留出候选） | no | 修订后只能作"标明版本的自建题"；X1 使答案暴露在同仓两题初态里，要按仓库整体留出 |

## 7. 进探针还差什么

- **已满足**：
  - 公开开发路径：新机 devcheck，真实 CC 2.1.205 配桩，agent 身份，全部检查为真；
  - 评分依据：新机 noop 0、gold 1，另有 DG1、ALT1 实跑；
  - 运行条件：镜像 `f483bab4…`、默认资源、不需要网络；
  - 跨题关联已登记。
- **未满足**：
  1. 独立复核，由协调者派人；
  2. S1 还没处理：
     - 用原版进探针，只能作能力比较，而且要按下方三项做预登记的事后审计；
     - 用修订版，要由协调者实施 R-c 并跑完第 5 节的验收，再经 Codex 复核；
  3. 真实模型求解（清单第 33–36 项），这由探针本身回答。
- **事后审计**（用原版时预登记）：用附录 E 的私有矩阵脚本跑候选补丁，逐行判定。以下任一条成立即判 FAIL：
  1. `hdr_name_cyr_o`、`reqline_vt_sep` 输出 ACCEPT（说明只拒了示例）；
  2. `target_lf`、`target_ff`、`target_cr`、`target_tab` 任一输出 ACCEPT（说明有请求目标回归）；
  3. 补丁改了 `aiohttp/pytest_plugin.py`、`aiohttp/test_utils.py`、`setup.cfg`，或者动了扩展检测、构建了 `.so`。

## 8. 复核与下一步

- **请复核者重点反驳 I4**：只要拿出公开依据，证明"请求目标里的 LF/FF 可以被接受"，I4 就降为 S2，R-c #3 撤回。
- **唯一最值得先做的下一步**：由协调者实施 R-c #1–#3（附录 C、D、E），在修订版上跑第 5 节的验收矩阵（含 ALT2）和 ALT1/ALT2 的公开测试私有对照，交 Codex 复核；I4 同批给独立复核。

---

## 附录 C：R-c #1、#2（隐藏测试补丁）

- 路径按评分容器写；在私有包里对应 `PRIV/hidden_tests/test_1.py`。
- 已在副本上验证：与附录 D 以任意顺序叠加都能 `git apply`，结果能通过 `py_compile`。

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -179,6 +179,10 @@ def test_c_parser_loaded():
         "Foo : bar",  # https://www.rfc-editor.org/rfc/rfc9112.html#section-5.1-2
         "Foo\t: bar",
         "\xffoo: bar",
+        pytest.param(  # non-ASCII (Cyrillic o, UTF-8 d0 be) inside the field name
+            "f\N{CYRILLIC SMALL LETTER O}o: bar",
+            id="nonascii-mid-name",
+        ),
     ),
 )
 def test_bad_headers(parser: Any, hdr: str) -> None:
@@ -686,6 +690,21 @@ def test_http_request_bad_status_line_whitespace(parser: Any) -> None:
         parser.feed_data(text)
 
 
+@pytest.mark.parametrize(
+    "line",
+    (
+        b"GET /path\x0cHTTP/1.1",  # FF alone as a separator
+        b"GET\x0b/path HTTP/1.1",  # VT as a separator
+    ),
+    ids=("ff-separator", "vt-separator"),
+)
+def test_http_request_bad_status_line_other_whitespace(
+    parser: Any, line: bytes
+) -> None:
+    with pytest.raises(http_exceptions.BadStatusLine):
+        parser.feed_data(line + b"\r\n\r\n")
+
+
 def test_http_request_upgrade(parser: Any) -> None:
     text = (
         b"GET /test HTTP/1.1\r\n"
```

**公开依据**：

- R-c #1：
  - 题面 L4、L22 说的是一般情形——字段名里的无效字符应当被拒；
  - 仓库在 `HP` L59-65 用 RFC 9110 的 tchar 定义 token，全是 ASCII；
  - `WT/docs/client_advanced.rst` L109-110 引用 RFC 7230 §3.2 讲头字段名。
  - 选这个字符的理由：它的 UTF-8 首字节是 `d0`，不在字段名首位，也不含 `c3`、`bf`。所以"只拒 `ÿ`"、"只查首字节"、"只加 `\xc3`/`\xbf`"三种示例拟合都会被它拦下。
- R-c #2：
  - 题面 L23 把示例里的 FF 称为不当空白、控制字符；
  - 请求解析器按设计是严格的（`HP` L639：lax 只用于响应解析）。
  - VT 与 FF 同属一类，所以一并要求拒绝。
  - 没有加 HTAB 分隔的例子：RFC 9112 §3 允许接收方宽松处理 HTAB，而且仓库文档没有引用这一节，不强加。

## 附录 D：R-c #3（隐藏测试补丁）

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -775,6 +775,20 @@ def test_http_request_parser_bad_nonascii_uri(parser: Any) -> None:
         parser.feed_data(b"GET \xff HTTP/1.1\r\n\r\n")
 
 
+@pytest.mark.parametrize(
+    "line",
+    (
+        b"GET /pa\nth HTTP/1.1",  # LF inside the request-target
+        b"GET /pa\x0cth HTTP/1.1",  # FF inside the request-target
+    ),
+    ids=("lf-in-target", "ff-in-target"),
+)
+def test_http_request_ctl_in_target_rejected(parser: Any, line: bytes) -> None:
+    # BadStatusLine (issue wording) or InvalidURLError (C-parser mapping) both ok
+    with pytest.raises(http_exceptions.BadHttpMessage):
+        parser.feed_data(line + b"\r\n\r\n")
+
+
 @pytest.mark.parametrize("size", [40965, 8191])
 def test_http_request_max_status_line(parser, size) -> None:
     path = b"t" * (size - 5)
```

## 附录 E：expected 增量与私有矩阵

- 新键的键名按现有参数化命名规则推出（例如 `test_bad_headers[py-parser-pyloop-...]`），落盘前以实跑的 short summary 核对。
- 状态按语义给出，都是 PASSED，没有照抄 gold 的输出：

```json
{
  "test_bad_headers[py-parser-pyloop-nonascii-mid-name]": "PASSED",
  "test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-ff-separator]": "PASSED",
  "test_http_request_bad_status_line_other_whitespace[py-parser-pyloop-vt-separator]": "PASSED",
  "test_http_request_ctl_in_target_rejected[py-parser-pyloop-lf-in-target]": "PASSED",
  "test_http_request_ctl_in_target_rejected[py-parser-pyloop-ff-in-target]": "PASSED"
}
```

- 私有矩阵脚本就是 `analysis_before_history.md` 的附录 E，协调者的副本在 `cands/pcheck_matrix.sh`。
- 事后审计只读第 7 节列出的那几行，判定规则也见第 7 节。

## 附录 F：ALT2（最小的 D4 正对照：gold 加请求行控制字符检查）

已在 base 副本上验证 `git apply --check` 与 `py_compile` 通过；还没做正式评分。

```diff
diff --git a/aiohttp/http_parser.py b/aiohttp/http_parser.py
--- a/aiohttp/http_parser.py
+++ b/aiohttp/http_parser.py
@@ -65,7 +65,10 @@ ASCIISET: Final[Set[str]] = set(string.printable)
 #     token = 1*tchar
 METHRE: Final[Pattern[str]] = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
 VERSRE: Final[Pattern[str]] = re.compile(r"HTTP/(\d).(\d)")
-HDRRE: Final[Pattern[bytes]] = re.compile(rb"[\x00-\x1F\x7F()<>@,;:\[\]={} \t\"\\]")
+HDRRE: Final[Pattern[bytes]] = re.compile(
+    rb"[\x00-\x1F\x7F-\xFF()<>@,;:\[\]={} \t\"\\]"
+)
+REQUEST_LINE_CTL: Final[Pattern[str]] = re.compile(r"[\x00-\x1f\x7f]")
 HEXDIGIT = re.compile(rb"[0-9a-fA-F]+")
 
 
@@ -546,8 +549,10 @@ class HttpRequestParser(HttpParser[RawRequestMessage]):
     def parse_message(self, lines: List[bytes]) -> RawRequestMessage:
         # request line
         line = lines[0].decode("utf-8", "surrogateescape")
+        if REQUEST_LINE_CTL.search(line):
+            raise BadStatusLine(line)
         try:
-            method, path, version = line.split(maxsplit=2)
+            method, path, version = line.split(" ", maxsplit=2)
         except ValueError:
             raise BadStatusLine(line) from None
 
```

## 附录 G：I4（第 4 步）的依据，以及为什么不因 gold 失败而放宽

**公开依据**（从强到弱）：

1. **题面。**
   - 标题："Fails to Reject ... Malformed Status Lines"（L4）。
   - 描述："improperly formatted status lines, leading to potential mishandling of HTTP requests"（L7）。
   - 期望："because the status line contains improper whitespace and control characters"（L23）。
   - 用的词是 "contains"，不是 "separated by"；LF 和 FF 正是示例里的字符。
2. **合理旧行为。**
   - 对 `GET /pa\nth HTTP/1.1` 这类请求（请求目标里夹 LF、FF、CR 或 TAB），base 都抛 `BadStatusLine`（私有矩阵的 none 行）；gold 全部接受（gold 行）。
   - 所以这不是"更完整的修复翻转了旧键"，而是修复把题面要求拒绝的输入放行了。
3. **仓库自身的约束。**
   - 请求解析器按设计是严格的（`HP` L639）。
   - 消息头里的裸 CR、LF、NUL 按 RFC 9110 §5.5-5 拒绝（`HP` L208-210）。
   - 公开测试 `test_cve_2023_37276`（公开 tests L165-168）和 `test_bad_headers` 里的 `Foo: abc\rdef`、`Bar: abc\ndef`（L176-177），把消息头里的裸 CR/LF 当作必须拒绝的走私输入。
   - 请求目标的形式按 `HP` L571-594 引用的 RFC 7230 §5.3.1–5.3.3，这些语法都不允许空白。
4. **C 解析器的做法。**
   - 公开测试注释把 C 解析器当作参照（公开 tests L237、L862-863、L1087-1088）。它对请求不设宽松标志，非法 URL 映射为 `InvalidURLError`（`_http_parser.pyx` L829-834）。
   - 所以 R-c #3 的断言用父类 `BadHttpMessage`，`BadStatusLine` 和 `InvalidURLError` 两种都算对。

**为什么不因 gold 失败而放宽**：

- v1 §4 规定，核心要求按题面的一般表述理解，gold 的实现范围不决定核心要求；v1 §5 规定，任何情况下都不为保住 gold 而放宽需求。
- 不补这条的话，奖励会给"把题面点名的 LF/FF 从拒绝改成接受"的补丁满分，RL 会把这种切分方式当成正确范式学进去。
- 满足这条的实现很常见，不需要特殊设计：
  - gold 加一个检查（ALT2）；
  - ALT1；
  - 保留 base 的 `split(maxsplit=2)`，再要求分隔符必须是单个 SP。
  - 会失败的只有"改成只按 SP 切分、其它都不管"这一种写法。
- 上游到 3.10.6.dev0 仍是 gold 的写法（同仓 1c1c0ea3 的公开工作树，`aiohttp/http_parser.py` L572）。这说明上游的实现范围比题面表述窄，不是后来修掉的笔误。修订后本题只能作"标明版本的自建题"。

**范围控制**：

- R-c #3 只收题面自己的两个字符（LF、FF）出现在请求目标里的情形，这两例 base 都拒绝。
- `\x01` 这类非空白控制字符 base 也接受；版本号里的 FF 是 `VERSRE` 里的 `.` 没转义造成的，base 也接受。这两类只登记为 T3，不写进断言。

**判断什么情况下可以推翻**：

- 如果能给出公开依据，证明题面只约束分隔位置、并且请求目标里的 LF/FF 可以被接受，I4 就降为 G1/T3（S2），R-c #3 撤回，改成探针的事后审计项。
- 这不属于 P5（两种读法对示例给出相反结果），因为只看分隔位置的读法并不要求接受这类输入。

## 附录 H：ALT1 比 gold 更严的几处，是否构成冲突

| 输入 | base | gold | ALT1 | 与 R-c 断言 | 与公开回归 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| `Fo/o: bar` | 接受 | 接受 | 拒绝 | 无关 | 隐藏测试和公开测试里都没有这类字段名；RFC 9110 的 token 不含 `/`（`HP` L59-65）；上游后来的 `TOKENRE` 也拒绝它（1c1c0ea3 L73-74、L172） | 不冲突 |
| `GET /pa\x01th HTTP/1.1` | 接受 | 接受 | 拒绝 | R-c #3 不要求处理 `\x01`，ALT1 多拒一个不影响结果 | 没有公开要求接受它 | 不冲突 |
| `GET /path HTTP/1\x0c1` | 接受 | 接受 | 拒绝（DG1 也拒绝） | 无关 | 隐藏测试里的版本号输入不受影响；上游后来把 `VERSRE` 改成 `\.` 加 `re.ASCII`（1c1c0ea3 L75） | 不冲突 |

- 私有矩阵里 `keep_*` 各行，四个候选的结果一致。
- ALT1 正式评分 129/129。
- 还缺：ALT1 在公开测试文件上的私有对照（第 5 节），作为 D4 正对照之前要补上。

## 附录 I：证据索引

新机器的运行结果都在 `runs/r2e_lifecycle_20260929/` 下：

- 正式评分：
  - noop：`env_verify/ledger_noop.jsonl` L4，127/129；
  - gold：`env_verify/ledger_gold.jsonl` L4，129/129；
  - DG1：`inv/aiohttp_4075/ledger_DG1.jsonl` L1，1.0；日志 `logs_DG1/evallog_replay-r2e-inv-4075-DG1-_74541a2c.eval.log` 的 L39、L89、L472-475；
  - ALT1：`inv/aiohttp_4075/ledger_ALT1.jsonl` L1，1.0。
- 私有矩阵：`inv/aiohttp_4075/pcheck_matrix_{none,gold,DG1,ALT1}.json`，root 身份、不联网。
- devcheck：`devcheck/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/` 下的 `devcheck.log`、`orig/captures/*.out`、`private_control.json`。
- 候选补丁：
  - DG1：`cands/aiohttp_4075_DG1.patch`，sha256 `f2d8d6f0…`；
  - ALT1：`cands/aiohttp_4075_ALT1.patch`，sha256 `d3a4b23c…`；
  - 两者与 `analysis_before_history.md` 附录 A、B 逐字相同。
