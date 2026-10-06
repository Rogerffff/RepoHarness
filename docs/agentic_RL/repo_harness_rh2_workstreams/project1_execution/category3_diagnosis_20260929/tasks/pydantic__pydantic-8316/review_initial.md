# pydantic__pydantic-8316 复核初判（读作者材料之前封存）

2026-09-30 / 独立复核者（Claude 子代理，不继承作者上下文）。本文写于阅读作者 `result.md`、`evidence/` 与实验目录之前，写完不再修改。

## 读过的原件

- 题面、gold、test_patch、参考名单：取自 `s2/ingest/` 的 `public_bundles_v0.jsonl`、`validation_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl`。gold sha256 `290e4011…3835d7`，test_patch `9d47a611…efc18`；F2P 1 项 `tests/test_utils.py::test_camel2snake[CAMELToSnake-camel_to_snake]`，P2P 143 项，都在 `tests/test_utils.py`。
- 镜像 `c3keep/pydantic8316:src`（RepoDigest 摘要 `3cbc02f3…9e0c`，与 ingest 冻结值一致），base `20c0c6d9`，pydantic 2.6.0a1、Python 3.8.19。读了 `pydantic/alias_generators.py`、`pydantic/config.py` 的 `alias_generator` 文档、`docs/concepts/alias.md`、`tests/test_utils.py` 的三组转换测试。
- 自己在断网一次性容器里对 base 与 gold 跑了 40 个输入的行为探针（只作初判依据，不是评分）。
- 上游 PyPI wheel（只作佐证）：2.5.3 与 base 相同；2.6.0–2.7.4 与 gold 相同；2.8.0 改成单个正则，恢复“任意字母与数字之间断开”；2.8.2 起又回到 gold 的写法（加 kebab 处理），2.11.7 仍如此。

## 公开要求（按题面一般表述）

1. **核心**：`to_snake` 遇到连续大写字母（缩写）后接首字母大写的单词时，要在两者之间断开：`HTTPResponse → http_response`。依据是题面“standard snake_case convention where words are separated by underscores”。按一般表述，它不限于题面示例的位置、长度与个数：中间位置（`getHTTPResponse`、`MyHTTPClient`、`userIDField`）、多个缩写（`XMLToJSONConverter`）、单字母词（`getAValue → get_a_value`）、长缩写都属于同一核心要求。
2. **保留旧行为**：现有 P2P（`Camel2Snake → camel_2_snake`、`camel2 → camel_2`、首尾下划线等）必须继续通过。
3. **alias 的实际影响**：题目标题是“alias generator bug”，`to_snake` 作为 `alias_generator` 时别名随之改变（base 下字段 `HTTPResponse` 的别名是 `httpresponse`，gold 下是 `http_response`）。这是核心修复的直接结果，不是另一项要求；直接断言 `to_snake` 已经覆盖。
4. **`to_camel` 附注**：题面说 `Foo.model_validate({"HTTPResponseCode": "200"})` 报错。实测 base 与 gold 都报错，`to_camel('http_response_code')` 为 `httpResponseCode`，用别名或字段名都能验证。`to_camel` 无从知道 `http` 是缩写，文档写明 `populate_by_name` 只接受字段名本身。这是误解，公开材料能消解，初判 **P4**（登记，原例可复现但不是缺陷），不构成第二项要求，也不属 P5。

## 对原测试的初判：S1

- **第 1 步**：核心要求有一条直接断言（`CAMELToSnake → camel_to_snake`），不命中。
- **第 2 步（T2c）**：这条断言的字面值不是题面的 `HTTPResponse`，但输入形态相同，都是“缩写在字符串开头，后接首字母大写的单词”。按 D1 严格版，“同一输入形态”也算示例拟合。只处理开头缩写的补丁（如 `^([A-Z]+)([A-Z][a-z])`）会通过原测试，却在 `getHTTPResponse` 上仍输出 `get_httpresponse`。中间位置的缩写在 camelCase／PascalCase 标识符里很常见，属主路径，不是边缘输入。初判**命中，S1**。
- **第 3 步**：在 gold 修改位置能写出的退化候选，是“只特判题面示例 `HTTPResponse`”或把整个串小写，前者被 F2P（`CAMELToSnake`）拒，后者被 P2P 拒。预计不命中；以作者或我的实跑为准。
- **第 4 步**：预计会有构造候选（位置子集、只处理第一个缩写、缩写长度阈值）在原测试下得 1、在同一核心要求的其它实例上出错，支持 S1。
- 结论：原版只作问题定位；需要 R-c 补非示例实例。

## 数字边界的初判

- **事实**：base 在任何字母与数字之间断开（`A1 → a_1`、`snakeV2 → snake_v_2`、`S3Bucket → s_3_bucket`、`HTTP2Response → http_2_response`）；gold 只在小写字母与数字之间断开（`a1`、`snake_v2`、`s3_bucket`、`http2_response`）。原测试与现有 P2P 都没有“大写字母后接数字”的用例。
- **公开依据**：
  - 保留旧读法（断开）有公开依据：base 代码明确写了 `[a-zA-Z]`，并与已测试的“小写字母与数字之间断开”一致；
  - gold 读法（不断开）在公开材料中**没有直接依据**：题面不谈数字，文档没有例子；只有“缩写加数字是一个词”（`S3`、`SHA256`）这种一般直觉。上游来回改动只是佐证，说明两种都有人支持。
- **影响**：作为 `alias_generator` 时，这会改变 `fieldV2` 一类字段的别名（`field_v_2 → field_v2`），也就是改变序列化键名，是真实的兼容性影响。但这一行为没有文档，也不是题面的核心要求。
- **初判处置**：这不是核心要求，测试**不应断言任何一种读法**，两种都接受。它**不属 P5**：P5 的前提是“测试只接受一种”，而这里原测试和合理的修订都不选边，任务目标（缩写断开）本身没有两种读法。它也不宜按第 4 步判 S1，因为它不是“有文档、常用的公开行为”。建议登记为 gold 的范围外行为变化（G1 → T3），在题卡写明“新旧数字行为都接受”；并要求修订断言里**不出现大写字母紧邻数字的输入**，否则会暗中选边、误拒保留旧行为的合理实现。

## 修订测试应满足什么（用来核对作者的修订版）

- 补非示例实例：中间位置、多个缩写、单字母词、较长的缩写、与下划线相邻的缩写；
- 不断言：大写字母与数字相邻的输出、非 ASCII 大写字母、`ABCd` 这类歧义拆分（缩写后只跟一个小写字母）、`to_camel` 行为；
- 参考名单：新增的参数化用例会产生新的测试 ID，不在 F2P／P2P 里就不会计分。修订要么保持 F2P ID 不变、在其测试体内加断言，要么明确需要改参考名单；
- 正对照：gold 应能通过上述中性断言；
- 验收时要专门构造：位置子集、只处理第一个缩写、缩写长度上下限（例如最少 2 个或最多 5 个字母）、依赖出现次序、只处理示例字面值、Unicode、与下划线／数字相邻，以及至少一个与 gold 不同的合理实现（例如保留旧数字行为的写法、逐字符状态机、`str.isupper()` 版）。
