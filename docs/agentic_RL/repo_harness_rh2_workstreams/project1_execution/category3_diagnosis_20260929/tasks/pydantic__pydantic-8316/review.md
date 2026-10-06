# pydantic__pydantic-8316 独立复核

2026-09-30 / 独立复核者（Claude 子代理，不继承作者上下文）。初判见同目录 [review_initial.md](review_initial.md)，写于读作者 `result.md`、`evidence/` 与实验目录之前，之后未改；sha256 `3c95dafb4d70448f07b2b29a9f0ed0843594da96ef019283102cce969f21c294`。该文件已被负责人提交 `c2499125` 一并提交，不是我提交的，内容与本地一致。

**总判断：部分同意，有 1 项阻断。**

- **同意的部分**：
  - 原版 S1：第 2 步 T2c 与第 4 步成立，第 3 步不命中，原测试没有误拒；
  - 附注里的 `to_camel` 例子判 P4；
  - alias 实际影响的分析；
  - gold 继续作正对照；
  - v2 的 7 条断言都有公开依据，也不过严：我另写的 4 个写法不同的合理实现，在原测试和 v2 上都得 1。
- **数字边界**：同意原测试与修订版都不断言、只登记，也同意它不属 P5、不必交用户。但作者“两种读法都有依据”这条理由要改：
  - gold 读法（`A1 → a1`）在 base 当时的公开材料里没有依据。作者引用的上游 2.8.1 回滚和 `snakeV2` 测试都发生在 base 之后，只能作佐证；
  - base 读法（`a_1`）有旧代码和 P2P 类比作依据，但没有文档，也没有直接测试，不属于 R-c 能补断言的“有文档的常用行为”。

  不断言的结论不变，只是理由要换成上面这一条（§3 N3）。
- **阻断项（1 项）**：v2 不满足 v1 §5“已知相关的错误候选仍为 0”。
  - 在 v2 下得 1 的错误候选共 7 个：作者已知的 `acr_max5`，加上我构造的 6 个。它们都在“缩写＋单词”这一核心要求的其它实例上出错：
    - 缩写长度设了上限：`acr_max5`、`w_acr_max8`；
    - 缩写个数设了上限：`w_count2`；
    - 只处理起点在前几个字符内的缩写：`w_window8`；
    - 输入超过一定长度就不修：`w_len_cap`；
    - 串中下划线后面的缩写不修：`w_mid_underscore`；
    - 串里有非 ASCII 字母就退回旧算法：`w_skip_nonascii`。
  - 按负责人补充的原则 2，不能以“少见”或“实现不自然”为由放过。
  - 修法：在 v2 后追加 4 条中性断言，形成草案 v3。私有模拟下，这 7 个都变为 0；gold 与 9 个合理实现仍为 1；其余 16 个错误候选仍为 0。

## 1．复核范围与证据层级

- **镜像**：`c3keep/pydantic8316:src`，即 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8316:latest`。
  - image ID `sha256:add19c29…cac4`；RepoDigest 摘要 `3cbc02f3…9e0c`，与 ingest 冻结值一致；
  - base `20c0c6d9`；Python 3.8.19、pydantic 2.6.0a1、pydantic-core 2.14.5；
  - 镜像初态有 `pdm.lock`、`pyproject.toml` 两处改动，与旧题卡记录一致。
- **材料**：直接从 ingest 取出。
  - gold `290e4011…35d7`、原 test_patch `9d47a611…fc18`、题面 `d7f27663…7eb4`，与作者一致；
  - v2 补丁 `f0b7b090…e917`，与 `materials_revised_v2.json` 的 `revised_patch_sha256` 一致，也与 `formal_revised_v2/audit_acr_max5/materials.json` 一致。
- **我的运行**：都是私有对照与私有模拟评分，不是正式评分。
  - `review/run_review.py` 逐个变体调用 `semantic_control.py`，每个变体一个一次性、断网、root 容器。每个变体启动前先等机器上的容器数少于 3，同一时间只有我的 1 个容器。
  - 每个变体执行三类命令：
    - `review_behavior.py`：37 个输入上的 `to_snake` 输出；另查 7 个字段在 `alias_generator=to_snake` 下的 alias，以及按 base 旧 key 能否验证；
    - 分别套原 test_patch、作者 v2、我的 v3 草案，用评分包的测试命令（另加 `-p no:cacheprovider`）跑 `tests/test_utils.py`；
    - v3 另用 `setpriv` 以 UID 54322 复跑一次。
  - `grade_review.py` 按参考名单（F2P 1 项、P2P 143 项）逐项判分。34 个变体在 4 组运行中都没有参考项缺席。
  - 34 个变体为：base、gold、作者的 20 个候选、我的 12 个候选。
- **与作者正式评分的交叉核对**：作者的 22 个变体在原测试与 v2 上共 44 格，我的私有模拟与作者的正式账本逐格相同，包括 reward、F2P 与 P2P 计数。
- **上游佐证**：我自己从 PyPI 下载了 13 个版本的 wheel：2.5.3、2.6.0、2.6.4、2.7.0、2.7.4、2.8.0、2.8.2、2.9.0、2.9.2、2.10.0、2.10.6、2.11.0、2.11.7。
  - 每个 wheel 的 sha256 都与 PyPI 登记一致；
  - 其中 `alias_generators.py` 的 sha256 与作者 `upstream/upstream_to_snake_history.txt` 对应 tag 一致，按阶段分别为：2.5.3 是 `f7917dc7`（与 base 相同），2.6.x–2.7.x 是 `43e2fa3c`（与 gold 相同），2.8.0 是 `0437c395`，2.8.2 起是 `28cd67de`；
  - 2.8.1 的 wheel 与 HISTORY.md 没有另取。
  - 这些只作佐证，不当公开依据。
- **没做的**：
  - 正式评分（按要求不跑）；
  - 派生镜像与正式 grader profile；
  - v1 的复跑；
  - actor 开发条件。

**我构造的候选**：脚本 `review/make_review_candidates.py`，做法同作者，只替换 base `to_snake` 的函数体。

| 候选 | sha256 前缀 | 性质 | 做法 |
| --- | --- | --- | --- |
| `rv_tokens` | `abacfc40` | 合理 | 正则分词后用 `_` 拼接，而不是逐处插入下划线。数字按 base 读法；非 ASCII 字符原样保留，不参与断开 |
| `rv_scan_gold` | `1df814ad` | 合理 | 逐字符扫描，用 `str.isupper`／`islower` 判断（Unicode 感知）；数字按 gold 读法 |
| `rv_split_join` | `be4d3512` | 合理 | 用 `re.split` 在零宽边界处切分，再 `'_'.join`；数字按 gold 读法 |
| `rv_acr_min2` | `520f3eb7` | 合理：单字母词属未规定行为，见 §3 N4 | gold 的规则，但缩写至少 2 个字母，所以 `XAxis`、`getAValue` 不拆 |
| `w_acr_max8` | `c41061bd` | 错误：长度阈值 | 只认 1–8 个字母的缩写 |
| `w_count2` | `35a803e5` | 错误：个数阈值 | 缩写规则只替换前两处 |
| `w_len_cap` | `7d2721a1` | 错误：规模阈值 | 输入超过 20 个字符就沿用 base 算法 |
| `w_window8` | `8945a222` | 错误：位置子集 | 缩写起点在前 8 个字符内才拆 |
| `w_mid_underscore` | `3857015f` | 错误：与下划线相邻 | 先剥掉首尾下划线；中段的缩写只在串首或小写字母、数字之后才拆 |
| `w_last_only` | `57da42b1` | 错误：依赖出现次序 | 只拆最后一个缩写 |
| `w_skip_nonascii` | `f7d492f9` | 错误：编码子集 | 输入里有非 ASCII 字符就沿用 base 算法 |
| `w_example_only` | `5f7bf5d3` | 退化探测：示例字面值 | 只特判题面原例 `HTTPResponse` |

## 2．作者主张逐条核对

| # | 作者主张（result.md） | 核对方式 | 结论 |
| --- | --- | --- | --- |
| 1 | 核心要求：连续大写字母组成的缩写后接首字母大写的单词时要断开，不限位置、长度、个数，也不限 `HTTP` | 读题面与 base 文档，见初判 | **同意**。但作者 §1 把“6 个及以上字母的缩写”列进“不属于核心要求”，这与本条矛盾，见 N2 |
| 2 | 要保留 17 个旧参数、`parseURL`／`userID`，以及 21 项 `to_camel`／`to_pascal` 的 P2P | 按参考名单计数：`test_camel2snake` 17 项；`test_snake2camel`、`test_snake2camel_start_lower` 各 9 项；`test_on_lower_camel_*` 3 项 | 属实 |
| 3 | 附注的 `to_camel` 例子不是本题缺陷，判 P4 | 自己在 base 与 gold 上实跑：`HTTPResponseCode` 都报 `missing`，`httpResponseCode` 和字段名都能验证。另读了 `populate_by_name` 的公开说明 | **同意**。`to_camel` 无从知道 `http` 是缩写。探针分析时，模型若据附注去改 `to_camel` 或别名匹配，应按误读题意处理 |
| 4 | 20 个候选的分类：5 个合理、15 个错误 | 逐个读 `make_candidates.py` 的函数体，并在私有矩阵中复现 | 同意。`normalize` 不拆单字母词，我也认为属合理实现，见 N4 |
| 5 | 原材料正式评分 22 次：noop 0、gold 1、5 个合理实现 1；错误候选 10 个为 1、5 个为 0 | 读 `formal`、`formal_revised_v1`、`formal_revised_v2` 三份 `summary.json`，共 66 行；抽查原始账本 `formal_revised_v2/ledger_acr_max5.jsonl` 的镜像、候选 sha 与材料；我的私有模拟与原材料这 22 格逐格相同 | 属实。66 行都是：安装 rc 0、参考缺席 0、`stage_error` 为空、清理成功、派生镜像 `a764474e…` |
| 6 | 原版 S1（第 2 步 T2c） | 对照 F2P 与题面原例 | **同意**。`CAMELToSnake` 换了字面值，但输入形态与 `HTTPResponse` 相同：缩写在串首，只有一个，3 个以上字母，没有数字或下划线。按 D1 严格版，“同一输入形态”也算示例拟合 |
| 7 | 原版 S1（第 4 步），用了 10 个原测试得 1 的错误候选 | 按违例输入判断是否主路径 | **同意，而且不依赖边缘候选**。下列候选的违例都落在主路径输入上：<br>- `lead_only`：串中缩写（`getHTTPResponseCode`）；<br>- `acr3`：两字母缩写（`userIDToken`、`IOError`）；<br>- `first_only`、`lower_or_start`：第二个缩写（`XMLToJSONConverter`）；<br>- `no_trailing_upper`：破坏 base 已有的 `userID → user_id`；<br>- `no_lower_upper`：`getHTTPResponseCode → gethttp_response_code`。<br>只有 `acr_max5` 的违例偏边缘 |
| 8 | 第 3 步不命中：`literal`、`only_if_no_us` 正式评分为 0 | 读账本；我另造 `w_example_only`（只特判 `HTTPResponse`），私有模拟原测试为 0 | **同意**。F2P 用的不是题面字面值，所以“硬编码示例输出”这类退化候选过不了；要硬编码 `CAMELToSnake` 就得看到隐藏测试，不算“只凭 gold 修改位置”能写出的退化候选 |
| 9 | 原版无误拒（T1 不命中） | 作者 5 个与我 4 个合理实现在原测试下都是 1 | 同意 |
| 10 | 数字边界：G1 → T3，原测试与修订版都不断言；“两种读法都有依据” | 读 base 代码、文档、P2P；上游只作佐证 | **处置同意，理由不同意**，见 N3 |
| 11 | P5 不适用 | 对照 v1 §3 P5 | 同意。P5 的前提是“任务目标有两种读法，测试只接受一种”。本题目标只有一种读法；数字边界不是任务目标，测试也不选边 |
| 12 | alias 的实际影响：缩写字段的 alias 按题面要求改变；“大写字母→数字”字段只在 gold 读法下改变，旧 key 报 `missing` | 自己的行为探针：7 个字段 × 34 个变体 | 属实。gold、`upstream_main`、`rv_scan_gold` 下 `fieldV2 → field_v2`、`S3Bucket → s3_bucket`，按 base 旧 key 验证都报 `missing`；`keep_digit`、`rv_tokens`、`acr_max5` 下旧 key 仍能验证。缩写字段在所有合理实现下都改用新 key |
| 13 | v2 的 7 条断言都有公开依据 | 逐条对照题面、P2P 与 base 行为 | 同意，见 §3.3 |
| 14 | v2 没有引入误拒 | 我的 4 个合理实现：`rv_tokens` 取 base 数字读法，`rv_scan_gold` 是 Unicode 感知的扫描，`rv_split_join` 用 split／join，`rv_acr_min2` 不拆单字母词。v2 下都是 1 | 同意 |
| 15 | v2 验收：“已知相关的错误候选都为 0，唯一例外 `acr_max5` 记为 T3” | 对照 v1 §5 与负责人补充原则 2；另造阈值、位置、编码类候选 | **不同意，列为阻断**，见 N1 与 §4 |
| 16 | gold 仍作正对照，不需要 D4 | 私有模拟：gold 在 v2、v3 上都是 1，UID 54322 下也是 1 | 同意 |
| 17 | 私有模拟与正式评分在 66 组上逐一相同 | 我复现了其中原测试与 v2 的 44 组，v1 没有复跑 | 已核部分属实 |
| 18 | 上游历史：2.6.0 起为 gold 写法；2.8.0 恢复断开；2.8.1 撤回，并新增 `snakeV2 → snake_v2` | 自取 PyPI wheel 比对 `alias_generators.py` 的哈希；2.8.1 本身未取 | 已核部分属实，只作佐证 |
| 19 | 交接：“经 D6 的测试补丁替换形成正式版本” | 对照 README 09-30 的更正 | 措辞需改，见 §5 第 4 条 |

## 3．反例与新问题

### 3.1 私有模拟评分（本人实跑，root 身份，原镜像，按参考名单逐项判）

| 组 | 候选 | 原测试 | v2 | v3 草案 |
| --- | --- | --- | --- | --- |
| 对照 | base | 0 | 0 | 0 |
| 正对照 | gold | 1 | 1 | 1 |
| 合理（作者） | `keep_digit`、`lookaround`、`scan`、`upstream_main`、`normalize` | 1 | 1 | 1 |
| 合理（复核） | `rv_tokens`、`rv_scan_gold`、`rv_split_join`、`rv_acr_min2` | 1 | 1 | 1 |
| 错误（作者，v2 已挡） | `lead_only`、`first_only`、`acr3`、`lower_or_start`、`lower_or_start_la`、`skip_if_underscore`、`skip_if_digit`、`no_lower_upper`、`no_trailing_upper` | 1 | 0 | 0 |
| 错误（作者，原测试已挡） | `acr_max4`、`literal`、`only_if_no_us`、`no_digit_split`、`no_digit_upper` | 0 | 0 | 0 |
| **错误（作者，v2 放过）** | `acr_max5` | 1 | **1** | 0 |
| 错误（复核，v2 已挡） | `w_last_only` | 1 | 0 | 0 |
| **错误（复核，v2 放过）** | `w_acr_max8`、`w_count2`、`w_len_cap`、`w_window8`、`w_mid_underscore`、`w_skip_nonascii` | 1 | **1** | 0 |
| 退化探测（复核） | `w_example_only` | 0 | 0 | 0 |

- P2P 都是 143/143，只有 `no_digit_split` 为 135/143、`no_digit_upper` 为 141/143。所有变体在各组运行中参考项缺席都是 0。
- v3 以 UID 54322 复跑，34 个变体的结果与 root 下逐一相同。
- 各变体的逐项结果：`rh2/experiments/category3_cloud_20260929/pydantic8316/review/out/review_summary.json`。原始输出在 `review/out/sem/<变体>/`，该目录被 .gitignore 忽略，需要时由负责人 `git add -f`。

### 3.2 N1（阻断）：v2 放过 7 个错误候选

下表的违例输入与输出取自我的行为矩阵，每一行都与 gold 和 9 个合理实现的输出不同：

| 候选 | 违反公开要求的输入（私有矩阵实测） | v3 下的首条失败断言 |
| --- | --- | --- |
| `acr_max5`（作者） | `NASDAQTicker → nasdaqticker`、`getWYSIWYGEditor → get_wysiwygeditor` | `'load_configurationfile' == 'load_configuration_file'` |
| `w_acr_max8` | `loadCONFIGURATIONFile → load_configurationfile`（`CONFIGURATION` 有 13 个字母） | 同上 |
| `w_count2` | `convertXMLToJSONViaHTTPRequest → convert_xml_to_json_via_httprequest`、`parseXMLToJSONToCSVToYAMLFile → parse_xml_to_json_to_csvto_yamlfile` | `'convert_xml_to_json_via_httprequest' == …` |
| `w_window8` | `aVeryLongPrefixBeforeTheHTTPResponse → a_very_long_prefix_before_the_httpresponse` | `'convert_xml_to_jsonvia_httprequest' == …` |
| `w_len_cap` | `convertXMLToJSONViaHTTPRequest → convert_xmlto_jsonvia_httprequest`、`loadCONFIGURATIONFile → load_configurationfile`：超过 20 个字符的输入完全退回 base 结果 | `'load_configurationfile' == …` |
| `w_mid_underscore` | `get_HTTPResponse → get_httpresponse`、`my_XMLParser → my_xmlparser` | `'get_httpresponse' == 'get_http_response'` |
| `w_skip_nonascii` | `ÜberHTTPClient → über_httpclient`、`naïveHTTPResponse → naïve_httpresponse` | `'über_httpclient' == 'über_http_client'` |

- **违反的公开要求**：题面的一般表述“words are separated by underscores”，即核心要求本身（结论第 1 条），它不限缩写长度、个数、位置与串长。
- **为什么 v2 放过**：v2 的 7 条输入里，缩写最长 5 个字母（只有原 F2P 的 `CAMEL`），一串最多 2 个缩写，缩写起点都在前 7 个字符内，串长不超过 19；与下划线相邻的只有串首的 `__`；全是 ASCII。
- **严重度**：
  - 7 个候选都是“得 1、但在同一核心要求的其它实例上违反公开要求”；
  - 按 v1 §5，它们属于“已知相关的错误候选”，修订验收要求它们为 0；
  - 按负责人补充原则 2，不能因为输入少见（如 6 个字母以上的缩写、非 ASCII 标识符）或写法不自然而记 T3 放过；
  - 我也不认为它们不违反公开要求：七组输入的期望输出都没有歧义，gold 与 9 个写法各异的合理实现给出同一结果。

### 3.3 v2 的 7 条断言：依据与是否过严

| # | 断言 | 依据 | 是否过严 |
| --- | --- | --- | --- |
| 1 | `HTTPResponse → http_response` | 题面 Expected Result | 否 |
| 2 | `getHTTPResponseCode → get_http_response_code` | 一般表述：串中缩写 | 否 |
| 3 | `userIDToken → user_id_token` | 一般表述：两字母缩写 | 否；`normalize`、`rv_acr_min2` 这类不拆单字母的实现也通过 |
| 4 | `XMLToJSONConverter → xml_to_json_converter` | 一般表述：两个缩写，中间隔着小写单词 | 否 |
| 5 | `__HTTPResponse__ → __http_response__` | 一般表述；P2P 的 `__CamelToSnake__` 规定首尾下划线原样保留 | 否 |
| 6 | `base64URLEncode → base_64_url_encode` | 一般表述；P2P 的 `camel2Snake` 规定“小写→数字”“数字→大写”都断开 | 否。两种数字读法在这里一致：`rv_tokens`（base 读法）和 `rv_split_join`（gold 读法）都通过 |
| 7 | `parseURL → parse_url` | 一般表述（`URL` 是一个词），也是 base 已有行为 | 否 |

9 个合理实现与 gold 在我的 37 个输入上的差别，只出现在四类未规定的输入上：
- 大写字母→数字：`keep_digit`、`lookaround`、`scan`、`normalize`、`rv_tokens`；
- 单字母词：`normalize`、`rv_acr_min2`；
- 非 ASCII 字母处在断开边界上：`scan`、`rv_scan_gold`；
- kebab-case：`upstream_main`。

v2 与 v3 草案都不触及这四类，所以没有误拒。

### 3.4 N2：作者 §1 的“不属于核心要求”清单有两项不对，这是 N1 的根源

- **“6 个及以上字母的缩写”不是歧义输入，而是核心要求的实例。** 题面没有限制缩写长度；`NASDAQTicker`、`getWYSIWYGEditor`、`loadCONFIGURATIONFile` 都只有一种合理切法，所有合理实现一致。
- **“Unicode 字母”要拆开看：**
  - 非 ASCII 字母**处在断开边界上**时（`parseÜBERDoc`、`getÄnderung`），属于未规定行为：`scan`、`rv_scan_gold` 会断开，gold 不断开，都可以接受；
  - 串里有非 ASCII 字母、但**断开边界都在 ASCII 字符之间**时（`ÜberHTTPClient`、`naïveHTTPResponse`），仍是核心要求的实例。Python 标识符可以含这类字母（PEP 3131），base 的最后一步 `str.lower()` 会把它们原样小写，base 对 `ÜberClient` 也照常输出 `über_client`。

### 3.5 N3：数字边界的处置同意，理由要改

- **事实**（已复现）：
  - base 下：`A1 → a_1`、`snakeV2 → snake_v_2`、`S3Bucket → s_3_bucket`、`HTTP2Response → http_2_response`；
  - gold 与 `upstream_main` 下：`a1`、`snake_v2`、`s3_bucket`、`http2_response`；
  - 原测试、v2 与 v3 草案都没有“大写字母紧邻数字”的输入；
  - 两种读法的合理实现都得 1：保留 base 读法的 `keep_digit`、`lookaround`、`scan`、`normalize`、`rv_tokens`，采用 gold 读法的 gold、`upstream_main`、`rv_scan_gold`、`rv_split_join`。
- **公开依据**（按 base 当时可见的材料）：
  - **base 读法**：
    - 旧代码明确写了 `([a-zA-Z])([0-9])`；
    - 与 P2P 已测的“小写字母与数字之间断开”（`camel2 → camel_2`）是同一套分词规则，即数字自成一词；
    - 但没有文档，也没有直接测试。
  - **gold 读法**：base 当时的公开材料里没有依据。题面不谈数字，文档没有例子；只有“缩写加数字是一个词”（`S3`、`SHA256`）这种一般直觉。作者 §3 引用的 2.8.1 changelog（“Fix breaking change in `to_snake` from v2.7 -> v2.8”）和 `snakeV2` 测试发布于 2024-07，比 base（提交日期 2023-12-04）晚约 7 个月，只能说明上游后来把 gold 读法当作要保护的已有行为，不构成本题的公开依据。
  - 所以“两种读法都有依据”不成立，应改为：“base 读法只有旧代码与 P2P 类比的依据；gold 读法没有公开依据。两者都不属于题面要求。”
- **为什么仍然不断言、也不交用户**：
  1. P5 不适用：任务目标（缩写断开）只有一种读法；数字边界不是任务目标，原测试和修订版都不选边，没有任何合理实现被判 0。
  2. 按 v1 §4 第 4 步，gold 改掉的是无文档、无测试的旧行为，不属“有文档、常用的公开行为”，不构成 S1。
  3. 按 v1 §5 R-c，能补的断言是“非示例实例、核心场景、有文档的常用行为”，base 的数字读法三者都不是。若为它加断言，gold 以及上游 2.6–2.7、2.8.1 以后的正式写法都会被判 0，还得启用 D4 替代正对照，依据与代价不相称。
  4. 反过来断言 gold 读法，则没有任何公开依据，会误拒 5 个保留旧行为的合理实现。
- **需要写进题卡的影响**：在 `alias_generator=to_snake` 的模型上，gold 读法会改变 `fieldV2`、`S3Bucket` 这类字段的 alias，也就是序列化 key 和 JSON schema 的属性名；按旧 key 发来的数据会报 `missing`（我已复现）。这是题面没要求的线上 key 变化。登记时写成“gold 的范围外行为变化，新旧数字行为都接受”；事后审计与探针分析时，两种都不算错，也不算额外的语义正确。

### 3.6 N4：其它未规定的输入（登记，不断言）

- **单字母词**：`XAxis`、`getAValue`、`OAuth2Token`。拆开（`x_axis`、`o_auth_2_token`）对普通单词正确，对 `OAuth`、`IPhone` 这类品牌词不对；不拆则反过来。启发式规则分不出这两种情况，题面也没有给出取舍。我的初判原先把 `getAValue` 算作核心实例，读到 OAuth 类反例后改判为未规定行为。因此同意作者不断言，`normalize`、`rv_acr_min2` 都算合理实现。
- **两个缩写直接相连**：`XMLHTTPRequest → xmlhttp_request`，同意不断言。
- **复数缩写**：`getURLs`。gold、上游与多数合理实现都输出 `get_ur_ls`，读起来不自然；`URLs` 也可以理解为 `URL` 加复数 `s`。建议登记为已知现象，不断言。
- **kebab-case**：只有 `upstream_main` 会改，题面未要求，同意不断言。

## 4．阻断项

**B1：v2 不满足 v1 §5“已知相关的错误候选仍为 0”。**

- **当前行为**：`acr_max5`、`w_acr_max8`、`w_count2`、`w_len_cap`、`w_window8`、`w_mid_underscore`、`w_skip_nonascii` 在 v2 下得 1（§3.1 私有模拟；`acr_max5` 另有作者的正式诊断评分为 1）。
- **违反的不变量**：v1 §5 R-c 验收的“已知相关的错误候选仍为 0”；负责人补充原则 2。
- **修法**：草案 v3，文件 `rh2/experiments/category3_cloud_20260929/pydantic8316/review/revised_test_v3_draft.patch`，sha256 `b248daa2eaf1ee37523ba03b078d768a9790a5db234813ee2b8b239b774a81e0`，由 `review/make_v3_draft.py` 从 base 测试文件生成。
  - v2 的 7 条断言原样保留，只在其后追加 4 条（外加 2 行注释）；
  - 测试 ID、F2P／P2P 名单与测试命令都不变；
  - 非 ASCII 用 `\u` 转义写，测试文件保持纯 ASCII。

  ```python
          # ... whatever its length, however many there are and wherever they appear
          assert to_snake('loadCONFIGURATIONFile') == 'load_configuration_file'
          assert to_snake('convertXMLToJSONViaHTTPRequest') == 'convert_xml_to_json_via_http_request'
          assert to_snake('get_HTTPResponse') == 'get_http_response'
          # other (non-ASCII) letters are kept as they are and do not change how the acronym is split
          assert to_snake('\u00dcberHTTPClient') == '\u00fcber_http_client'
  ```

  | 新增断言 | 挡住的候选 | 公开依据 | 为什么不会误拒 |
  | --- | --- | --- | --- |
  | `loadCONFIGURATIONFile` | `acr_max5`、`w_acr_max8`、`w_len_cap`（21 个字符） | 一般表述，缩写长度不限；原 F2P 自己就把全大写单词 `CAMEL` 当作一个缩写 | 没有数字，没有单字母；全大写段恰好是一个词 |
  | `convertXMLToJSONViaHTTPRequest` | `w_count2`、`w_window8`、`w_len_cap` | 一般表述，每个缩写都要断开，不限个数、位置与串长 | 三个缩写之间都隔着小写单词，最后一个 `HTTP` 从下标 19 开始，全长 30 |
  | `get_HTTPResponse` | `w_mid_underscore` | 一般表述；base 本来就处理含下划线的串里的驼峰（`get_fooBar → get_foo_bar`），P2P 规定已有下划线原样保留 | 不产生双下划线；9 个合理实现输出相同 |
  | `ÜberHTTPClient`（补丁里写作 `\u00dcberHTTPClient`） | `w_skip_nonascii` | 一般表述；Python 标识符可含非 ASCII 字母，base 的 `str.lower()` 把它们原样小写（base 对 `ÜberClient` 输出 `über_client`） | 两处断开（`r` 与 `HTTP` 之间、`HTTP` 与 `Client` 之间）都在 ASCII 字符之间，非 ASCII 字母不在任何断开边界上；ASCII 实现与 Unicode 感知实现结果相同 |

- **修后预期**（私有模拟，已实跑）：
  - base 为 0；
  - gold 与 9 个合理实现为 1，以 root 和 UID 54322 运行结果相同；
  - 23 个错误候选全为 0：作者 15 个，我的 8 个；
  - 新增的 0 都停在为它设计的断言上，见 §3.2 最后一列。
- **验收命令**：用 `--materials` 跑一轮修订版诊断评分，命令同作者 `run_formal.sh`／`run_chain.sh`，材料 JSON 的 `revised_patch_sha256` 换成上面的值，父版本记 v2 `f0b7b090…e917`。
  - 候选集为本页 §3.1 的 34 个变体，其中 base 以 noop 代替；
  - 结果应与“修后预期”逐项一致。
- **停止条件**：
  1. 作者采纳 v3 或等价的修法，并完成上面这一轮诊断评分，结果与预期一致，就可以收口，转第2类做正式材料接线与最终复验。
  2. 聚焦复核只核对两件事：补丁 sha256，以及这一轮的 34 格结果。不再追加新的构造维度。
  3. v3 之后仍能通过的更大阈值，只登记为 T3，不再阻断，包括：
     - 缩写长度上限 ≥ 13；
     - 缩写个数上限 ≥ 3；
     - 起点窗口 ≥ 20；
     - 串长上限 ≥ 30。
  4. 未规定行为只登记，不断言：大写字母→数字、单字母词、两个缩写相连、复数缩写、非 ASCII 字母处在断开边界、kebab-case。
  5. 若作者认为某一条新增断言缺依据，应指出它会误拒哪个合理实现；不能只以“少见”为理由删掉。

## 5．非阻断建议

1. **改写 result.md §3 的数字边界理由**，按 N3：处置不变，删去“两种读法都有依据”，改为“base 读法只有旧代码与 P2P 类比的依据，gold 读法无公开依据，两者都不在题面要求内”。上游来回改动只写作佐证。
2. **改正 result.md §1 的“不属于核心要求”清单**，按 N2：
   - 删去“6 个及以上字母的缩写”；
   - “Unicode 字母”改为“非 ASCII 字母处在断开边界上时”。

   同时改 §3 的 T3 条目和 §4 的“验收要点”：原文说 `acr_max5` 记为 T3，采纳 v3 后它为 0。
3. **补登 T3 与未规定行为**：§4 停止条件第 3 条的阈值余量；复数缩写 `getURLs → get_ur_ls`；非 ASCII 字母处在断开边界上。
4. **D6 措辞**：按 README 09-30 的更正，D6 目前已验收的首片只有 `append_mypy_p2p`。result.md §5 的“经 D6 的测试补丁替换形成正式版本”应写明：这是已获总体授权、尚未实现的后续实施项；`--materials` 诊断评分也不等于正式 actor 已消费修订版。
5. **交接时的候选集**：第2类复验时，建议把我的 12 个候选一并纳入，理由是 `rv_tokens`（base 数字读法、分词写法）与 `rv_scan_gold`（Unicode 感知）能同时检查两类未规定行为没有被误拒。第二、第三正对照沿用作者的 `keep_digit` 与 `upstream_main` 即可。
6. **探针与事后审计**：数字边界、单字母词的改动，不作为扣分项，也不作为额外的语义正确。若模型据附注去改 `to_camel`，按 P4 视为误读题意。

## 6．未查

- 正式评分：按要求没跑。v3 的正式诊断评分待作者或第2类完成；本页 v3 的数字都是私有模拟。
- 派生镜像 `a764474e…` 与正式 grader profile（UID 54322、`deny_all`、2 CPU／4 GiB）：我的 UID 54322 复跑，是在 root 容器里用 `setpriv` 降权，不等于正式 profile。
- v1 修订版：没有复跑，只读了作者账本。
- 作者私有矩阵的 79 个输入：只读了汇总表，没有逐项核对。我用自己的 37 个输入核对了“合理实现与 gold 只在四类未规定输入上不同”这一结论。
- 测试范围：只跑了 `tests/test_utils.py`，没有跑全量测试，也没有跑 `test_aliases.py`、`test_config.py`。
- 真实 actor 的开发条件、模型求解、跨题关联。
- 上游 PR 讨论（#8316、#9747、#9812）读不到；2.8.1 的 wheel 与 HISTORY.md 没有另取。

**复核产物**（都在 `rh2/experiments/category3_cloud_20260929/pydantic8316/review/`）：

| 文件 | sha256 前缀 | 说明 |
| --- | --- | --- |
| `make_review_candidates.py` | `84ea5a60` | 生成 12 个复核候选 |
| `candidates/*.patch` | 见 §1 表 | 12 个复核候选 |
| `make_v3_draft.py` | `7714e4b7` | 生成 v3 草案 |
| `revised_test_v3_draft.patch` | `b248daa2` | v3 草案 |
| `review_behavior.py` | `6ddb78ed` | 行为探针 |
| `run_review.py` | `7107d1c1` | 驱动 |
| `grade_review.py` | `3a5afcad` | 按参考名单判分 |
| `out/review_summary.json` | — | 逐项结果 |
| `out/sem/<变体>/` | — | 原始输出 |
| `out/inputs/gold.patch` | — | 从 ingest 取出的 gold，sha256 `290e4011…` |
