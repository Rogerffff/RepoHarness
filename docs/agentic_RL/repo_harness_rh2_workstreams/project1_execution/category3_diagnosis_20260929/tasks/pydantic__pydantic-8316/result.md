# pydantic__pydantic-8316：第3类诊断结果

2026-09-30 / Claude（云端，第3类第二批主审作者）。原分类：第3类“已有具体疑点，缺辨别实验”（alias 与数字边界）。工作清单登记的下一步：“对照 HTTPResponse、数字边界及 alias 模型填充／导出，明确实际影响。”

前一位作者留下 13 个候选和修订草案 v1，运行输出随容器重置丢失。本页核对并沿用这些材料，另补 7 个候选和修订草案 v2，全部运行重做并归档。

> **当前状态（09-30 更新：独立复核完成，采用复核草案 v3；v3 诊断评分进行中）**
>
> - **作者诊断与证据**：原材料正式评分 22 次、修订 v1 与 v2 诊断评分各 22 次、私有行为矩阵 22 个变体，见 [evidence/](evidence/)。
> - **独立复核完成**，结论“部分同意，阻断 1 项”，全文见 [review.md](review.md)（初判封存稿 [review_initial.md](review_initial.md)）：
>   - 同意：原版 S1（第 2 步同一输入形态、第 4 步多个错误候选错在常见输入上）；第 3 步不命中；`to_camel` 附注判 P4；alias 影响分析成立；gold 继续作正对照；v2 的 7 条断言都有公开依据、不过严；
>   - **B1**：v2 仍放过 7 个错误候选，都在没有歧义的“缩写＋单词”输入上出错：缩写长度设上限（作者的 `acr_max5`、复核者的 `w_acr_max8`）、缩写个数设上限（`w_count2`）、只拆起点在前 8 个字符内的缩写（`w_window8`）、输入超过 20 个字符就退回旧算法（`w_len_cap`）、串中下划线后面的缩写不拆（`w_mid_underscore`）、串里有非 ASCII 字符就退回旧算法（`w_skip_nonascii`）。作者原把 `acr_max5` 记 T3；按“已知错误不因少见放过”，须修；
>   - 根因是作者 §1 把“6 个及以上字母的缩写”列为非核心、把所有非 ASCII 情形都当作未规定（复核 N2），本页已更正；
>   - 数字边界维持 T3、不断言、不属 P5，但“两种读法都有依据”这条理由不对，已按复核 N3 改写（§3）。
> - **负责人决定**：采纳复核草案 **v3**（v2 的 7 条断言原样保留，追加 4 条），私有模拟下这 7 个错误候选都变为 0，gold 与 9 个合理实现仍为 1。
> - **进行中**：按复核停止条件，对 34 个变体跑一轮 `--materials` 诊断评分（base 以 noop 代替），逐格对照复核预期；一致即收口转第2类。停止条件写明聚焦复核只核对补丁 sha256 与这 34 格。

**结论：问题和修法已明确；采用复核草案 v3，待 34 格诊断评分与复核预期一致后转第2类。** gold 仍作正对照。

- **原测试只测了一种缩写形态（S1：v1 §4 第 2 步 T2c、第 4 步）。** 唯一 F2P 是 `CAMELToSnake → camel_to_snake`，与题面原例 `HTTPResponse` 同一形态：缩写在串首、只有一个、3 个以上字母。本页 15 个错误候选中有 **10 个在原材料正式评分得 1**，例如：
  - `lead_only` 只拆串首的缩写，`getHTTPResponseCode` 得到 `get_httpresponse_code`；
  - `acr3` 只认 3 个及以上字母的缩写，`userIDToken` 得到 `user_idtoken`；
  - `no_trailing_upper` 丢掉了 base 已有的 `userID → user_id`。

  noop 为 0，gold 为 1。
- **没有误拒。** 5 个与 gold 写法不同的合理实现，在原材料、v1、v2 上都得 1。其中 4 个保留 base 的数字规则，1 个是上游现行写法。
- **数字边界：gold 顺带改了一条旧行为。登记为 T3（gold 的范围外行为变化），不断言，不属 P5。**
  - base 在字母与数字之间一律断开，gold 只在小写字母与数字之间断开。例如 `A1` 从 `a_1` 变为 `a1`，`snakeV2` 从 `snake_v_2` 变为 `snake_v2`，`S3Bucket` 从 `s_3_bucket` 变为 `s3_bucket`；
  - 依据（09-30 按独立复核 N3 改写）：base 读法只有旧代码与 P2P“小写字母与数字之间断开”的类比，没有文档也没有直接测试；gold 读法在 base 当时的公开材料里没有依据。两者都不在题面要求内；
  - 上游来回改过（只作佐证，不构成本题公开依据）：2.6.0 起采用 gold 读法；2.8.0 恢复断开；2.8.1 以“Fix breaking change in `to_snake` from v2.7 -> v2.8”撤回，并新增测试钉住 `snakeV2 → snake_v2`，这比 base 提交晚约 7 个月；
  - 因此原测试与修订版都不断言，新旧数字行为都接受。小写字母与数字之间、数字与大写字母之间的断开，两种读法一致，由 17 个旧参数保护。
- **alias 的实际影响（私有矩阵）。** 在 `alias_generator=to_snake` 的模型上，`to_snake` 的输出就是字段的 alias：
  - **缩写字段**（`HTTPResponse`、`userIDToken`）：alias 从 `httpresponse`、`user_idtoken` 变为 `http_response`、`user_id_token`，所有合理实现一致。这是题面要的修复，副作用是按旧 key 发来的数据报 `missing`；
  - **大写字母后接数字的字段**（`fieldV2`、`S3Bucket`、`A1` 等）：只在 gold 读法下改变，例如 `field_v_2 → field_v2`。旧 key 报 `missing`，按别名导出与 JSON schema 也改用新 key。这部分不是题面要求的；
  - `populate_by_name` 与 `AliasGenerator` 路径没有额外差异。
- **题面附注的 `to_camel` 例子不是本题缺陷（P4）。** 22 个变体的行为完全相同：`HTTPResponseCode` 报 `missing`，`httpResponseCode` 与字段名都能填充。按 `populate_by_name` 的公开说明，这是预期行为。
- **修法：R-c 修订版 v3（独立复核草案，采用）。** 在唯一 F2P 的测试体里追加 11 条断言，测试 ID 不变：
  - v1 的 4 条（前一位作者）：题面原例、非开头缩写、两字母缩写、两个缩写；
  - v2 补 3 条：缩写挨着下划线、缩写挨着数字、末尾缩写；
  - v3 补 4 条（复核者）：长缩写 `loadCONFIGURATIONFile`、三个缩写 `convertXMLToJSONViaHTTPRequest`、下划线后的缩写 `get_HTTPResponse`、含非 ASCII 字母的 `ÜberHTTPClient`（补丁中写作 `\u00dcberHTTPClient`，测试文件保持纯 ASCII）。

  v2 正式诊断评分：noop 0；gold 与 5 个合理实现 1；15 个作者错误候选中 14 个为 0，`acr_max5` 仍为 1。复核另造的 6 个错误候选在 v2 下也为 1（私有模拟）。v3 私有模拟下这 7 个都为 0；v3 的 34 格诊断评分进行中（§4 v3 小节）。
- **gold 仍作正对照**，不需要 D4 替代正对照。
- **实施依赖 D6 的“测试补丁替换”切片。** 派生镜像是云端等效重建。

## 1．公开要求

**题面**（标题“`to_snake` alias generator bug”）：
- `to_snake` 把 CamelCase 串直接转小写，词与词之间没有下划线；
- 期望 `to_snake("HTTPResponse")` 返回 `"http_response"`，“maintaining the standard snake_case convention where words are separated by underscores”，实际返回 `"httpresponse"`；
- 附注：`to_camel` 作 alias 生成器、`populate_by_name=True` 的模型上，`Foo.model_validate({"HTTPResponseCode": "200"})` 报 `Field required`，报告者认为是“同一个问题”。

**核心要求**（按题面的一般性理解，v1 §4）：连续大写字母组成的缩写后面接首字母大写的单词时，`to_snake` 要在缩写与单词之间断开。这一要求不限于题面原例的形态：
- 不限于串首：例如 `getHTTPResponseCode` 中间的 `HTTP`；
- 不限于 3 个及以上字母：例如 `userIDToken` 的 `ID`；
- 不限于一个缩写：例如 `XMLToJSONConverter`；
- 不限于题面的 `HTTP`。

**需要保留的已有公开行为**：
- `tests/test_utils.py::test_camel2snake` 的 17 个旧参数：小写字母与大写字母之间断开，小写字母与数字之间、数字与大写字母之间都断开（`camel2Snake → camel_2_snake`），前后的单、双下划线原样保留（`__CamelToSnake__ → __camel_to_snake__`）；
- base 的 `([a-z0-9])([A-Z])` 规则对末尾缩写的拆分：`parseURL → parse_url`、`userID → user_id`；
- `to_camel`、`to_pascal` 不受影响（P2P 中有 21 项）。

**核心要求的范围说明（09-30 按独立复核 N2 更正）**：缩写长度、缩写个数、在串中的位置与串长都不限；串里含非 ASCII 字母、但断开边界都在 ASCII 字符之间时（例如 `ÜberHTTPClient`），仍是核心要求的实例：Python 标识符可以含这类字母（PEP 3131），base 的 `str.lower()` 把它们原样小写，base 对 `ÜberClient` 也照常输出 `über_client`。此前本页把“6 个及以上字母的缩写”与所有 Unicode 情形列为非核心，这是 v2 放过 7 个错误候选的根源。

**不属于核心要求**，题面没有提，而且没有唯一切法或没有公开依据：
- **大写字母与数字之间是否断开**：base 断开（`A1 → a_1`，`snakeV2 → snake_v_2`）；gold 不断开（`a1`，`snake_v2`）。base 读法只有旧代码与 P2P 类比，gold 读法没有 base 当时的公开依据；base 的 docstring 只写“Convert a PascalCase or camelCase string to snake_case”，公开测试里没有这种输入。
- **单个大写字母后接单词**：例如 `XAxis → x_axis` 或 `xaxis`；`OAuth` 按缩写规则会变成 `o_auth`。
- **两个缩写直接相连**：例如 `XMLHTTPRequest`，没有小写字母提示边界。
- **复数缩写**：例如 `getURLs`，gold 与多数实现输出 `get_ur_ls`。
- **非 ASCII 字母处在断开边界上**：例如 `parseÜBERDoc`、`getÄnderung`。
- **kebab-case**：上游到 2.8 才支持。

**附注的 to_camel 例子不是本题要修的缺陷**，公开材料能消解：
- base `ConfigDict.populate_by_name` 的说明是，字段可以用字段名或 alias 填充；
- alias 由生成器从字段名生成，`to_camel('http_response_code')` 是 `httpResponseCode`（由 base 源码可推出，私有矩阵实测）；
- `HTTPResponseCode` 既不是字段名也不是 alias，报错符合契约。

## 2．实测

### 环境与材料

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8316:latest`，本机标签 `c3keep/pydantic8316:src`；RepoDigests `sha256:3cbc02f3…9e0c`，与 ingest 冻结摘要一致；image ID `sha256:add19c29…cac4` |
| 派生镜像 | 负责人按作者须知 §4 重建的 pydantic_v1 等效派生镜像 `sha256:a764474e…3dfe`（标签 `rh2-envrepair/pydantic__pydantic-8316:c3cloud-install-v1-equiv`）：保留 base 的 13 层，只加 1 层离线 wheel（8 个，固定版本与 pydantic-9066 相同，清单与 sha256 见 [evidence/derived_image.json](evidence/derived_image.json)）。**这是等效重建，不是 09-19 原版的逐字节重建** |
| 安装配方 | 09-19 `pydantic_v1` 修订 [`pydantic__pydantic-8316.json`](../../../env_recipe_repair_20260919/pydantic_v1/pydantic__pydantic-8316.json)，sha256 `a6fe422e…620c` |
| 运行时 | Python 3.8.19、pydantic 2.6.0a1（`/testbed` 可编辑安装）、pydantic-core 2.14.5；Docker 29.3.1、overlay2、cgroup v1 |
| 材料 | 题面 sha256 `d7f27663…7eb4`；gold `290e4011…35d7`（与 ingest 一致）；原 test_patch `9d47a611…fc18`；F2P 1 项、P2P 143 项，全部在 `tests/test_utils.py` |
| 评分 | grader `swebench-4.1.0+swegym_parsers@242429c1`；profile `sha256:3ec1bfa8…`：UID 54322、`deny_all`、2 CPU／4 GiB；候选以 UID 54321 `git apply`，投影只含 `pydantic/alias_generators.py` |
| 代码 | 分支 `claude/category3-20260929`。评分路径与 `a31cdcd` 逐字相同（`git diff` 为空），诊断包装同 [环境说明](../../environment.md) §2 |

### 候选

全部候选由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/make_candidates.py) 在 base `to_snake` 函数体上做逐字替换生成。前 13 个是前一位作者的，重新生成后与已提交的补丁逐字节相同；后 7 个是本页补的。按公开要求判对错，不以 gold 为答案。

**（a）合理实现（查误拒 T1）**

| 候选 | sha256 前缀 | 做法 | 数字读法 |
| --- | --- | --- | --- |
| gold | `290e4011` | 四条正则：缩写＋单词、小写→大写、数字→大写、小写→数字；替换后的文件与上游 2.6.0 逐字相同 | 大写字母→数字不断开 |
| `keep_digit` | `2c6f4518` | 在 base 两条规则前加一条“缩写＋单词”规则 | 保留 base（断开） |
| `lookaround` | `2be37fd6` | 上游 2.8.0 的单条环视正则，去掉 kebab 分支 | 保留 base |
| `scan` | `6b0be169` | 逐字符扫描，不用正则，用 `str.isupper` 等判断 | 保留 base |
| `upstream_main` | `c7906241` | 上游 2.8.1–2.11.0 的函数体：gold 的四条正则，另把 `-` 换成 `_` | 同 gold |
| `normalize` | `a2154e26` | 先把后接单词的缩写改成首字母大写（`HTTPResponse → HttpResponse`），再走 base 两条规则 | 保留 base |

**（b）错误候选（查漏判）**，类别对应作者须知 §2.3：

| 候选 | sha256 前缀 | 构造 | 类别 | 违反公开要求的输入（私有矩阵实测） |
| --- | --- | --- | --- | --- |
| `lead_only` | `f8c19970` | 只拆串首的缩写（允许前导下划线） | 位置子集 | `getHTTPResponseCode → get_httpresponse_code`，`myHTTPResponse → my_httpresponse` |
| `first_only` | `24f8262b` | 缩写规则只替换第一处（`count=1`） | 依赖出现次序 | `XMLToJSONConverter → xml_to_jsonconverter` |
| `acr3` | `85341b09` | 只认 3 个及以上字母的缩写 | 阈值 | `userIDToken → user_idtoken`，`IOError → ioerror` |
| `lower_or_start` | `f3e7f4d9` | 缩写只在串首或小写字母之后才拆，匹配时吞掉前一个字符 | 位置子集 | `XMLToJSONConverter → xml_to_jsonconverter`，`_HTTPResponse → _httpresponse` |
| `lower_or_start_la` | `59b6af87` | 同上，但用零宽断言，不吞字符 | 位置子集 | `__HTTPResponse__ → __httpresponse__`，`base64URLEncode → base_64_urlencode` |
| `skip_if_underscore` | `9f1efdca` | 输入含下划线就沿用 base 算法 | 数据形态子集 | `_HTTPResponse`、`__HTTPResponse__`、`get_HTTPResponse` 都不拆 |
| `skip_if_digit` | `961d39e3` | 输入含数字就沿用 base 算法 | 数据形态子集 | `base64URLEncode → base_64_urlencode`，`sha256HMACKey → sha_256_hmackey` |
| `no_lower_upper` | `2516d519` | 只在“大写字母＋小写字母”之前断开，删掉 base 的“小写／数字→大写”规则 | 丢旧规则 | `getHTTPResponseCode → gethttp_response_code`，`userIDToken → userid_token` |
| `no_trailing_upper` | `cade993b` | 只在“后面还跟着小写字母的大写字母串”之前断开，末尾的缩写与单个大写字母不再拆 | 丢旧规则 | `parseURL → parseurl`，`userID → userid`（base 为 `parse_url`、`user_id`） |
| `acr_max5` | `62b5cdf3` | 只认 1–5 个字母的缩写 | 上限阈值 | `NASDAQTicker → nasdaqticker`（6 个字母） |
| `acr_max4` | `e809eb14` | 只认 2–4 个字母的缩写 | 上限阈值 | `CAMELToSnake → camelto_snake` |
| `literal` | `40f4362c` | 只认一张固定缩写表（HTTP、URL、ID 等） | 示例字面值，退化 | `CAMELToSnake`、`IOError` 不拆 |
| `only_if_no_us` | `7df58192` | 旧结果里完全没有下划线时才用缩写规则 | 只在症状出现时修，退化 | `CAMELToSnake → camelto_snake` |
| `no_digit_split` | `8024590e` | 修了缩写，但字母与数字之间都不再断开 | 丢旧的数字规则 | `camel2 → camel2`（P2P 期望 `camel_2`） |
| `no_digit_upper` | `aea90402` | 修了缩写，但数字与大写字母之间不再断开 | 丢旧的数字规则 | `Camel2Snake → camel_2snake` |

“吞掉错误”一类在本题不适用：`to_snake` 是纯字符串函数，没有异常可吞。最接近的构造是“只在症状出现时修”（`only_if_no_us`）和“对旧测试覆盖的输入形态保留旧行为”（`skip_if_underscore`、`skip_if_digit`）。

### （1）私有行为矩阵

条件：root 身份、断网、一次性容器，原镜像（不是派生镜像）。用 [`semantic_control.py`](../../../../../../../rh2/experiments/task2_swegym_dev_20260925/semantic_control.py) 跑 [`semantic_spec_full.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/semantic_spec_full.json)，22 个变体（base、gold、20 个候选）。每个变体执行：
- [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/behavior.py)：`to_snake` 在 79 个输入上的输出、alias 生成器下的模型行为、`to_camel` 附注；
- 相关公开测试 `tests/test_utils.py tests/test_aliases.py tests/test_config.py`（未应用 test_patch）；
- 私有模拟评分：分别应用原 test_patch、修订 v1、修订 v2，跑 `tests/test_utils.py`，按参考名单（F2P 1 项、P2P 143 项）逐项计分。

**（a）`to_snake` 的输出**。“gold 读法”指 gold 与 `upstream_main`；“base 读法”指 `keep_digit`、`lookaround`、`scan`、`normalize`，它们保留 base 的数字规则。

| 输入 | base | gold 读法 | base 读法 | 说明 |
| --- | --- | --- | --- | --- |
| `HTTPResponse`（题面原例） | `httpresponse` | `http_response` | `http_response` | 题面要求 |
| `CAMELToSnake`（原 F2P） | `camelto_snake` | `camel_to_snake` | `camel_to_snake` | |
| `getHTTPResponseCode`、`userIDToken`、`XMLToJSONConverter`、`IOError` | 缩写未拆 | 拆开 | 拆开 | 非开头、两字母、两个缩写 |
| `__HTTPResponse__`、`get_HTTPResponse`、`base64URLEncode` | 缩写未拆 | `__http_response__`、`get_http_response`、`base_64_url_encode` | 同左 | 缩写挨着下划线或数字 |
| `parseURL`、`userID`、`getX` | `parse_url`、`user_id`、`get_x` | 同 base | 同 base | base 已有行为 |
| `A1`、`API2`、`HTTP2`、`snakeV2` | `a_1`、`api_2`、`http_2`、`snake_v_2` | `a1`、`api2`、`http2`、`snake_v2` | 同 base | **大写字母→数字** |
| `S3Bucket`、`EC2Instance`、`ipV4Address`、`HTTP2Response` | `s_3_bucket`、`ec_2_instance`、`ip_v_4_address`、`http_2_response` | `s3_bucket`、`ec2_instance`、`ip_v4_address`、`http2_response` | 同 base | **大写字母→数字** |
| `camel2Snake`、`Camel2`、`sha256Hash` | `camel_2_snake`、`camel_2`、`sha_256_hash` | 同 base | 同 base | 小写→数字、数字→大写：两种读法一致，P2P 保护 |
| `XAxis`、`ATest`、`OAuth2Token` | `xaxis`、`atest`、`oauth_2_token` | `x_axis`、`a_test`、`o_auth_2_token` | `normalize` 同 base，其余同 gold 读法 | 单字母缩写，有歧义 |
| `getÄnderung` | `getänderung` | 同 base | `scan` 为 `get_änderung`，其余同 base | 非 ASCII 字母，题面未要求 |
| `kebab-case` | `kebab-case` | gold 不变；`upstream_main` 为 `kebab_case` | 不变 | 题面未要求 |

在 79 个输入上逐一比对，5 个合理实现与 gold 的差别只在四类输入：大写字母→数字、单字母缩写（`normalize`）、非 ASCII 字母（`scan`）、kebab-case（`upstream_main`）。四类都是题面没有规定的地方。15 个错误候选的违例见上面候选表的最后一列：每个都在某个“缩写＋单词”实例或 base 已有行为上与 gold、base 两种读法都不同。

**（b）alias 生成器下的实际影响**。模型 `ConfigDict(alias_generator=to_snake)`，字段名是 camelCase。`to_snake` 的输出直接成为字段的 `alias`、`validation_alias` 与 `serialization_alias`：base `_generate_schema.py` 的 `_apply_alias_generator_to_field_info` 把字段名传给生成器。

| 字段 | base alias | gold 读法 | base 读法 | 按 base 旧 key 验证 | 性质 |
| --- | --- | --- | --- | --- | --- |
| `HTTPResponse` | `httpresponse` | `http_response` | `http_response` | 两种读法都报 `missing` | 题面要求的变化 |
| `userIDToken`、`myHTTPResponse`、`XMLToJSONConverter` | `user_idtoken`、`my_httpresponse`、`xmlto_jsonconverter` | `user_id_token`、`my_http_response`、`xml_to_json_converter` | 同 gold 读法 | 两种读法都报 `missing` | 题面要求的变化 |
| `fieldV2` | `field_v_2` | `field_v2` | `field_v_2` | gold 读法报 `missing`，base 读法通过 | **题面未要求** |
| `S3Bucket`、`A1`、`API2`、`EC2Instance`、`ipV4Address`、`HTTP2Response` | `s_3_bucket` 等 | `s3_bucket` 等 | 同 base | gold 读法报 `missing`，base 读法通过 | **题面未要求** |
| `camelToSnake`、`Camel2Snake`、`parseURL`、`userID` | 不变 | 不变 | 不变 | 都通过 | 无变化 |

其余核对项，所有变体都与上表一致：
- 按新 alias 验证都通过；
- `model_dump(by_alias=True)` 与 JSON schema 的属性名都用新 alias；
- 不开 `populate_by_name` 时字段名不被接受，开了则接受（与 base 相同）；
- `AliasGenerator(validation_alias=to_snake, serialization_alias=to_snake)` 与直接传函数结果相同。

组合模型 `Resp`（字段 `HTTPResponse`、`userIDToken`、`fieldV2`、`camelToSnake`）收到按 base alias 组织的旧数据时：
- base：通过；
- base 读法：2 个 `missing`（两个缩写字段）；
- gold 读法：3 个 `missing`，多出的一个是 `fieldV2`。

`model_dump_json(by_alias=True)` 对应输出：
- gold：`{"http_response":0,"user_id_token":1,"field_v2":2,"camel_to_snake":3}`；
- base 读法：`field_v_2`。

**（c）题面附注**：22 个变体的 `to_camel`、`to_pascal` 输出与附注模型的行为完全相同：
- 字段 `http_response_code` 的 alias 是 `httpResponseCode`；
- 用 `httpResponseCode` 或字段名 `http_response_code` 都能验证；
- 用 `HTTPResponseCode` 报 `missing`。

即 gold 与所有候选都没有改变附注里的现象，隐藏测试也不涉及。

**（d）相关公开测试**（未应用 test_patch）：20 个变体都是 274 passed、17 skipped，`no_digit_split`、`no_digit_upper` 分别有 8、2 项失败，都是 `test_camel2snake` 的数字参数。公开测试对缩写问题**没有任何区分力**，base 与 10 个在原测试上得 1 的错误候选结果相同。

### （2）原材料正式评分

`replay_grade.py run` 经 `replay_with_install_recipe.py --recipe`，共 22 次。所有行：派生镜像 `a764474e…`，grader `swebench-4.1.0+swegym_parsers@242429c1`，安装 rc 0，参考缺席 0，清理成功，投影只含 `pydantic/alias_generators.py`。每次约 25 秒。

| 候选 | sha256 前缀 | reward | F2P | P2P | 日志 passed／failed／skipped | 失败原因（评分日志逐字） |
| --- | --- | --- | --- | --- | --- | --- |
| `noop` | — | 0 | 0/1 | 143/143 | 158／1／14 | `assert 'camelto_snake' == 'camel_to_snake'` |
| `gold` | `290e4011` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `keep_digit` | `2c6f4518` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `lookaround` | `2be37fd6` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `scan` | `6b0be169` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `upstream_main` | `c7906241` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `normalize` | `a2154e26` | 1 | 1/1 | 143/143 | 159／0／14 |  |
| `lead_only` | `f8c19970` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `first_only` | `24f8262b` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `acr3` | `85341b09` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `lower_or_start` | `f3e7f4d9` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `lower_or_start_la` | `59b6af87` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `skip_if_underscore` | `9f1efdca` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `skip_if_digit` | `961d39e3` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `no_lower_upper` | `2516d519` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `no_trailing_upper` | `cade993b` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `acr_max5` | `62b5cdf3` | **1** | 1/1 | 143/143 | 159／0／14 |  |
| `literal` | `40f4362c` | 0 | 0/1 | 143/143 | 158／1／14 | `assert 'camelto_snake' == 'camel_to_snake'` |
| `acr_max4` | `e809eb14` | 0 | 0/1 | 143/143 | 158／1／14 | `assert 'camelto_snake' == 'camel_to_snake'` |
| `only_if_no_us` | `7df58192` | 0 | 0/1 | 143/143 | 158／1／14 | `assert 'camelto_snake' == 'camel_to_snake'` |
| `no_digit_split` | `8024590e` | 0 | 1/1 | 135/143 | 151／8／14 | `assert 'camel2_snake' == 'camel_2_snake'` |
| `no_digit_upper` | `aea90402` | 0 | 1/1 | 141/143 | 157／2／14 | `assert 'camel_2snake' == 'camel_2_snake'` |

noop 与 gold 的日志计数与旧题卡记录的 09-19 历史一致：noop 为 158 passed、1 failed、14 skipped，gold 为 159 passed、14 skipped。

## 3．判定（v1 §4）

**原版：S1。** 命中第 2 步与第 4 步；第 1、3 步不命中，也没有误拒。

| 步 | 结果 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有 | 唯一 F2P `CAMELToSnake → camel_to_snake` 直接断言“缩写＋单词”要断开。题面原例 `HTTPResponse` 本身没有断言，但形态相同 |
| 2 是否只用了题面示例的形态 | **是 → S1（T2c）** | F2P 换了字面值（`CAMEL` 而不是 `HTTP`），所以只认固定缩写表的 `literal` 得 0；但它与题面原例是同一输入形态：缩写在串首，只有一个，3 个以上字母，没有下划线或数字。只处理这一形态的部分修复都能得 1 |
| 3 退化探测 | 不命中 | 在 gold 的修改位置构造了两个退化候选，正式评分都是 0：与输入无关的固定缩写表 `literal`；只在症状出现时修的 `only_if_no_us` |
| 4 已有得 1 的候选是否在同一核心要求的其它实例上违例 | **是 → S1** | 10 个错误候选原材料正式得 1，详见 §2（2）。其中非开头缩写（`lead_only`）、两字母缩写（`acr3`）、一串里的第二个缩写（`first_only`）、末尾缩写（`no_trailing_upper`，破坏 base 已有的 `userID → user_id`）都是常见的 camelCase 标识符形态，不是罕见路径 |
| T1 | 不命中 | 5 个合理实现原材料都得 1，其中 4 个保留 base 的数字规则，1 个是上游现行写法 |

**登记，不判 S1：**
- **G1 → T3：gold 改变了“大写字母→数字”的旧行为**，例如 `A1`、`snakeV2`、`S3Bucket`。经 alias 生成器，这会改变这类字段的 alias，按旧 key 发来的数据报 `missing`，按别名导出的 key 与 JSON schema 也随之改变，见 §2（1）（b）。不判 S1 的理由：
  - 题面没有提数字；base 的 docstring 与公开测试都没有这种输入，不属于 v1 §4 第 4 步所说“有文档、常用的公开行为”；
  - 上游的处理也来回改过（只作佐证）：2.6.0 起采用 gold 读法，changelog 只写“Fix `to_snake` conversion”，没有当作兼容性变化；2.8.0（#9747 提速）改回断开；2.8.1（#9812，changelog 原文“Fix breaking change in `to_snake` from v2.7 -> v2.8”）又改回 gold 读法，并新增测试 `('snakeV2', 'snake_v2')`，此后到 2.11.0 不变。即上游后来把 gold 读法当作已有行为来保护，而不是 base 的断开。PR 页面读不到，当时是否讨论过 base 读法，未知；
  - 公开依据的强弱（09-30 按独立复核 N3 改写，原写“两种读法都有依据”不成立）：base 读法只有旧代码 `([a-zA-Z])([0-9])` 与 P2P 已测“小写字母与数字之间断开”的类比，没有文档也没有直接测试；gold 读法在 base 当时（提交日期 2023-12-04）的公开材料里没有依据，上面引用的 2.8.1 changelog 与 `snakeV2` 测试发布于 2024-07，只能作佐证。两者都不属于题面要求；
  - 为什么仍不断言、也不交用户：P5 不适用，任务目标（缩写断开）只有一种读法，数字边界不是任务目标，原测试与修订版都不选边，没有合理实现被判 0；按 §4 第 4 步，gold 改的是无文档、无测试的旧行为，不构成 S1；按 R-c 只能补“有文档的常用行为”，base 的数字读法不属此类，若为它加断言，gold 与上游 2.6–2.7、2.8.1 以后的写法都会被判 0；反过来断言 gold 读法则没有公开依据，会误拒 5 个保留旧行为的合理实现；
  - 登记口径：“gold 的范围外行为变化，新旧数字行为都接受”。在 `alias_generator=to_snake` 的模型上它会改变 `fieldV2`、`S3Bucket` 这类字段的序列化 key 与 JSON schema 属性名，旧 key 报 `missing`（复核已复现）。事后审计与探针分析时两种都不算错，也不算额外的语义正确。“小写字母→数字”“数字→大写字母”两处两种读法一致，由 17 个旧参数保护：`no_digit_split`、`no_digit_upper` 被 P2P 判 0。
- **P4：附注的 to_camel 例子是报告者对 `populate_by_name` 的误解**，公开的 `ConfigDict` 说明能消解，见 §1。gold 与所有候选都不改变它，隐藏测试也不涉及。不需要 R-f。探针分析时，若模型据附注去改 `to_camel` 或 alias 匹配，应看作对题意的误读，不算题目缺陷。
- **原登记的“`acr_max5` 记 T3”已撤销**（09-30 独立复核 B1）：6 个及以上字母的缩写是核心要求的实例，`acr_max5` 与复核者另造的 6 个同类错误候选由 v3 断言拦下。
- **T3（v3 之后只登记、不再阻断）**：
  - 比 v3 实例更宽的阈值写法：缩写长度上限 ≥ 13、缩写个数上限 ≥ 3、起点窗口 ≥ 20、串长上限 ≥ 30；
  - 未规定行为，不断言：大写字母→数字、单字母词（`XAxis`、`OAuth`）、两个缩写相连（`XMLHTTPRequest`）、复数缩写（`getURLs`）、非 ASCII 字母处在断开边界、kebab-case。

P5 不适用：任务目标只有一种读法；有两种读法的只是题面没有提到的数字细节，修订版对它不作要求。

## 4．修法：R-c 修订版 v3（v1、v2 留档）与诊断评分

本节先保留 v2 的内容（它的依据表仍然适用），采用版本 v3 见本节末尾的 v3 小节。

**草案**：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/revised_test_v2.patch)，sha256 `f0b7b090…e917`，由 `_edit_revised_test_v2.py` 从 base 测试文件生成。材料 JSON 为 [`materials_revised_v2.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/materials_revised_v2.json)，grader 后缀 `+c3-pyd8316-acronym-position-v2`。父版本是 v1（`f98096e9…d1e3`），原 test_patch 为 `9d47a611…fc18`。

**改法**：保留原 test_patch 新增的参数 `('CAMELToSnake', 'camel_to_snake')`，只在 `test_camel2snake` 的测试体里加一段 `if value == 'CAMELToSnake':`。这段只在 F2P 参数下执行，17 个 P2P 参数的语义不变，测试 ID 与 F2P／P2P 名单都不变。段内 7 条断言：

| # | 断言 | 针对的缺口 | 公开依据 | 来源 |
| --- | --- | --- | --- | --- |
| 1 | `to_snake('HTTPResponse') == 'http_response'` | 题面原例本身没有断言 | 题面的 Expected Result | v1 |
| 2 | `to_snake('getHTTPResponseCode') == 'get_http_response_code'` | 非开头的缩写 | 题面的一般表述：词与词之间要有下划线 | v1 |
| 3 | `to_snake('userIDToken') == 'user_id_token'` | 两字母缩写 | 同上 | v1 |
| 4 | `to_snake('XMLToJSONConverter') == 'xml_to_json_converter'` | 一串里有两个缩写 | 同上 | v1 |
| 5 | `to_snake('__HTTPResponse__') == '__http_response__'` | 缩写挨着下划线 | 同上；另有 P2P `__CamelToSnake__ → __camel_to_snake__`：下划线原样保留 | v2 |
| 6 | `to_snake('base64URLEncode') == 'base_64_url_encode'` | 缩写所在的串含数字 | 同上；另有 P2P `camel2Snake → camel_2_snake`：小写字母→数字、数字→大写字母都断开。两种数字读法在此一致，base 也只差缩写这一处（`base_64_urlencode`） | v2 |
| 7 | `to_snake('parseURL') == 'parse_url'` | 末尾缩写，base 已有行为 | base 的 `([a-z0-9])([A-Z])` 规则；gold 保留 | v2 |

**有意不断言**：
- 大写字母与数字之间是否断开（§3 G1 → T3）；
- 单字母缩写、两个缩写相连、6 个及以上字母的缩写、Unicode、kebab-case。

**v1 到 v2 的过程（留档）**：
- v1 是前一位作者的草案，只有 1–4 条；
- v1 的正式诊断评分见下表：`lead_only` 等 5 个候选被纠正；但本页补的 `skip_if_underscore`、`lower_or_start_la`、`skip_if_digit`、`no_trailing_upper` 在 v1 下仍得 1。按它们的违例补了 5–7 条，形成 v2；`acr_max5` 在 v1、v2 下都得 1，见 §3 T3；
- v2 起草时先加了第 5、7 两条；运行前自查构造 `skip_if_digit`，宿主机预检发现它能通过，又补了第 6 条。此后 v2 没有改动，私有矩阵与正式评分用的都是同一份补丁 `f0b7b090…`。

**修订版正式诊断评分**：`--recipe` 加 `--materials`。所有行：派生镜像 `a764474e…`，安装 rc 0，参考缺席 0，清理成功。v1、v2 的 grader 后缀分别为 `+c3-pyd8316-acronym-position-v1`、`-v2`。

| 候选 | 原材料 | v1 | v2 | v2 的首条失败断言（正式评分日志） |
| --- | --- | --- | --- | --- |
| `noop` | 0 | 0 | 0 | `'camelto_snake' == 'camel_to_snake'` |
| `gold` | 1 | 1 | 1 |  |
| `keep_digit` | 1 | 1 | 1 |  |
| `lookaround` | 1 | 1 | 1 |  |
| `scan` | 1 | 1 | 1 |  |
| `upstream_main` | 1 | 1 | 1 |  |
| `normalize` | 1 | 1 | 1 |  |
| `lead_only` | 1 | 0 | 0 | `'get_httpresponse_code' == 'get_http_response_code'` |
| `first_only` | 1 | 0 | 0 | `'xml_to_jsonconverter' == 'xml_to_json_converter'` |
| `acr3` | 1 | 0 | 0 | `'user_idtoken' == 'user_id_token'` |
| `lower_or_start` | 1 | 0 | 0 | `'xml_to_jsonconverter' == 'xml_to_json_converter'` |
| `lower_or_start_la` | 1 | 1 | 0 | `'__httpresponse__' == '__http_response__'` |
| `skip_if_underscore` | 1 | 1 | 0 | `'__httpresponse__' == '__http_response__'` |
| `skip_if_digit` | 1 | 1 | 0 | `'base_64_urlencode' == 'base_64_url_encode'` |
| `no_lower_upper` | 1 | 0 | 0 | `'gethttp_response_code' == 'get_http_response_code'` |
| `no_trailing_upper` | 1 | 1 | 0 | `'parseurl' == 'parse_url'` |
| `acr_max5` | 1 | 1 | 1 |  |
| `literal` | 0 | 0 | 0 | `'camelto_snake' == 'camel_to_snake'` |
| `acr_max4` | 0 | 0 | 0 | `'camelto_snake' == 'camel_to_snake'` |
| `only_if_no_us` | 0 | 0 | 0 | `'camelto_snake' == 'camel_to_snake'` |
| `no_digit_split` | 0（P2P 135/143） | 0（P2P 135/143） | 0（P2P 135/143） | `'camel2_snake' == 'camel_2_snake'` |
| `no_digit_upper` | 0（P2P 141/143） | 0（P2P 141/143） | 0（P2P 141/143） | `'camel_2snake' == 'camel_2_snake'` |

- **私有模拟与正式评分**：root 身份的私有模拟评分与正式评分在 66 组（22 个候选 × 原材料、v1、v2）上的 reward 逐一相同。
- **验收要点（v1 §5）**：
  - 正对照 gold 为 1，noop 为 0；
  - 原版的漏判已纠正：10 个原版得 1 的错误候选中 9 个在 v2 为 0；
  - 已知相关的错误候选都为 0；唯一例外是 `acr_max5`，它只在 6 个及以上字母的缩写上出错，当时记为 T3（**09-30 独立复核改判为须修，见 v3 小节**）；
  - 5 个合理实现仍为 1，没有引入新的误拒。
- **修订后仍受保护的公开要求**：
  - 缩写与后面单词之间的拆分，覆盖串首、串中、两字母、两个缩写、挨着下划线、挨着数字、末尾缩写；
  - 17 个旧参数：大小写、数字、下划线的旧行为；
  - 21 项 `to_camel`／`to_pascal` 的 P2P；
  - `tests/test_utils.py` 的其余 P2P。
- **R-f**：不需要。修订测试的每项要求都能从题面的一般表述、base 行为与公开旧测试推出；附注的误解由公开文档消解（§3 P4）。

### v3：独立复核后的采用版本

**草案**：[`revised_test_v3.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/revised_test_v3.patch)，sha256 `b248daa2…81e0`，由复核者的 `review/make_v3_draft.py` 从 base 测试文件生成（原件 `review/revised_test_v3_draft.patch`，逐字节相同）；材料 [`materials_revised_v3.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8316/materials_revised_v3.json)，版本 `c3-pyd8316-acronym-position-v3`。父版本 v2（`f0b7b090…e917`）留档。v2 的 7 条断言原样保留，其后追加 4 条（外加 2 行注释）；测试 ID、F2P／P2P 名单与测试命令都不变。

| # | 新增断言 | 挡住的候选 | 公开依据 | 为什么不会误拒 |
| --- | --- | --- | --- | --- |
| 8 | `to_snake('loadCONFIGURATIONFile') == 'load_configuration_file'` | `acr_max5`、`w_acr_max8`、`w_len_cap`（21 个字符） | 一般表述，缩写长度不限；原 F2P 自己就把全大写单词 `CAMEL` 当作一个缩写 | 没有数字，没有单字母；全大写段恰好是一个词 |
| 9 | `to_snake('convertXMLToJSONViaHTTPRequest') == 'convert_xml_to_json_via_http_request'` | `w_count2`、`w_window8`、`w_len_cap` | 每个缩写都要断开，不限个数、位置与串长 | 三个缩写之间都隔着小写单词 |
| 10 | `to_snake('get_HTTPResponse') == 'get_http_response'` | `w_mid_underscore` | base 本来就处理含下划线串里的驼峰（`get_fooBar → get_foo_bar`），P2P 规定已有下划线原样保留 | 不产生双下划线；9 个合理实现输出相同 |
| 11 | `to_snake('\u00dcberHTTPClient') == '\u00fcber_http_client'` | `w_skip_nonascii` | Python 标识符可含非 ASCII 字母；base 的 `str.lower()` 原样小写（base 对 `ÜberClient` 输出 `über_client`） | 两处断开都在 ASCII 字符之间，ASCII 实现与 Unicode 感知实现结果相同 |

**复核者的候选**（`review/candidates/`，已复制到实验目录）：
- 4 个合理实现，写法与 gold 和作者的都不同：`rv_tokens`（分词写法，保留 base 数字读法）、`rv_scan_gold`（Unicode 感知扫描，gold 数字读法）、`rv_split_join`、`rv_acr_min2`；
- 8 个错误候选：`w_acr_max8`、`w_count2`、`w_window8`、`w_len_cap`、`w_mid_underscore`、`w_skip_nonascii`（v2 下为 1），`w_last_only`、`w_example_only`（v2 下已为 0）。

**私有模拟（复核者，root；v3 另以 UID 54322 复跑，结果相同）**：base 为 0；gold 与 9 个合理实现为 1；23 个错误候选（作者 15 个、复核者 8 个）全为 0，新增的 0 都停在为它设计的断言上。复核者的私有结果与作者正式评分在原测试和 v2 的 44 格上逐格相同。

**v3 诊断评分（进行中）**：按复核停止条件，对 34 个变体跑一轮 `--materials` 诊断评分，base 以 noop 代替，逐格对照上面的预期。

## 5．交接给第2类

1. **落地**：以 R-c 草案 v3（`b248daa2…81e0`）替换原 test_patch 形成正式版本。测试 ID、F2P／P2P 名单与测试命令都不变，不需要改参考分组。所需的 D6“测试补丁替换”是已获总体授权、尚未实现的后续实施项（D6 已验收的首片只有 `append_mypy_p2p`）；本页的 `--materials` 诊断评分也不等于正式 actor 已消费修订版。
2. **正对照**：gold（`290e4011…`）在修订版上为 1，不需要 D4 替代正对照。`keep_digit`（base 数字读法）与 `upstream_main`（上游 2.8.1 起的函数体）作第二、第三正对照，用来确认两种数字读法都能通过。
3. **复验**：落地后复验 v3 的 34 个变体：noop 0；gold 与 9 个合理实现 1；23 个错误候选 0。建议把复核者的 12 个候选一并纳入：`rv_tokens`（base 数字读法、分词写法）与 `rv_scan_gold`（Unicode 感知）能同时检查两类未规定行为没有被误拒。
4. **登记**：§3 的数字边界（gold 的范围外行为变化，新旧数字行为都接受）、P4（附注）与 T3 各项，写进题卡的已知缺口。数字边界、单字母词的改动在探针与事后审计中不作扣分项，也不作额外的语义正确；若模型据附注去改 `to_camel`，按 P4 视为误读题意。
5. **镜像**：正式入库时固定一份 wheel 清单并登记来源，因为本页派生镜像是等效重建。
6. **复核**：独立复核已完成（review.md）；按其停止条件，聚焦复核只核对补丁 sha256 与 34 格结果。Codex 复核照常。

## 6．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否：S1 未修，10 个错误候选能得 1（09-30 按 Codex 复核更正：原版有已证的 S1 未修，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不混用原分数） | 否 | 否 |
| 修订版 v3（草案） | 是 | conditional：D6 落地并复验 | conditional：同左，另加 Codex 复核；T3 各项登记 | 否（修订题只能作标明版本的自建题） |

## 7．未做与剩余事项

- **独立复核**：已完成，阻断 1 项由 v3 处理；v3 的 34 格诊断评分进行中。
- **真实 actor 开发条件**：未验。私有矩阵以 root 身份跑；正式评分以 grader UID 54322 跑，候选以 UID 54321 应用。`to_snake` 是纯字符串函数，两种身份下 66 组结果逐一一致，未见身份影响。
- **模型求解**：没有模型求解证据。
- **全量公开测试**：只跑了 `tests/test_utils.py`、`tests/test_aliases.py`、`tests/test_config.py` 三个相关模块；复核只跑了 `tests/test_utils.py`。
- **§3 的 T3 项**：只登记，没有设计断言。
- **修订版进训练前的条件**：还需要 v1 §2 的其它正面证据，本页未做。
- **派生镜像**：是等效重建，不是 09-19 原版。
- **上游资料来源**：只来自 raw.githubusercontent.com 上各 tag 的源码、测试与 HISTORY.md；PR 页面（#8316、#9747、#9812）在本容器读不到，未读。
- **复核未查**（review.md §6）：没在正式 grader profile 下跑（UID 54322 复跑是 root 容器内 `setpriv` 降权）；v1 没有复跑；作者私有矩阵的 79 个输入只读了汇总表。

## 8．版本与证据

- **代码与运行环境**：见[环境说明](../../environment.md)。
- **既有材料**：
  - [题卡](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8316/card.md)
  - [复核](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8316/review.md)
- **实验文件**：`rh2/experiments/category3_cloud_20260929/pydantic8316/`
  - 候选：`make_candidates.py` 与 20 个候选补丁；
  - 私有矩阵：`behavior.py`、`semantic_spec_full.json`（旧的 `semantic_spec*.json` 是前一位作者的，未再使用）、`summarize_semantic.py`；
  - 修订测试：`original_test.patch`；v1 为 `_edit_revised_test.py`、`revised_test_v1.patch`、`materials_revised_v1.json`；v2 为 `_edit_revised_test_v2.py`、`revised_test_v2.patch`、`materials_revised_v2.json`；
  - v3（复核草案）：`revised_test_v3.patch`、`materials_revised_v3.json`；复核材料在 `review/`（`make_review_candidates.py`、`candidates/` 12 个候选、`make_v3_draft.py`、`review_behavior.py`、`run_review.py`、`grade_review.py`、`out/review_summary.json` 与原始输出），12 个候选已复制到实验目录；
  - 正式评分：`run_formal.sh`、`run_batch.sh`、`run_chain.sh`、`summarize_formal.py`；`run_all.sh`、`run_extra.sh` 是前一位作者的驱动，本页未用；
  - 上游佐证：`upstream/upstream_to_snake_history.txt`，包含 2.5.3–2.11.0 各 tag 的 `to_snake`、2.6.0／2.8.0／2.8.1／2.8.2／2.11.0 的相关测试，以及 changelog 相关行，并附各文件 sha256。
- **原始证据**：[evidence/](evidence/)
  - `formal/`：原材料评分，22 次；
  - `formal_revised_v1/`、`formal_revised_v2/`：修订版诊断评分，各 22 次；
  - 以上三个目录各含账本、评分日志、审计与 `summary.json`，`summary.json` 为逐项摘要；
  - `semantic_full/`：私有矩阵，每个变体一个目录，`semantic_summary.json` 为汇总；`semantic_full_summary.md` 为汇总表；
  - `derived_image.json`、`derived/`：派生镜像的 wheel 清单与重建记录；
  - `evidence_manifest.json`：全部文件的 SHA256。
- **归档前扫描**：已扫描凭据字样与本机私有路径，未命中。
