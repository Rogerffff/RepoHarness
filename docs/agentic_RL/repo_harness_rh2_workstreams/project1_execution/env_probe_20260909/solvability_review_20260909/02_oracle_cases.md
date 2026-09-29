# 五道异常题及一个评分成功反例：Falsifier 独立结论

日期：2026-09-09。范围：只读取本次备份中的实际 `prompt.txt`、候选补丁、gold、官方 `test_patch`、原始测试输出、状态映射及 Claude Code 轨迹。未 SSH、未启动模型或 Docker、未修改评分器和生产代码。以下判断先以实际题面建立目标，再用 gold 和测试验证，未将 gold 视为唯一正确实现。

本报告中的 `ledger/`、`data/` 均相对于 `runs/env_probe_20260909_codex_backup/`。`stream.jsonl 第 N 行` 指原始 JSONL 行号；可在本目录的 `cases/<instance_id>/trajectory.md` 中按该行号找到去除流式重复后的原文。轨迹中的 thinking 是本次 DeepSeek API 已返回并留存的第三方实验数据；这里只归纳与决定直接相关的证据。

## 1. 先给判定

| 题目 | 已留存的目标测试事实 | 狭义题面是否完成 | 纠正已知评分问题后的判断 |
|---|---|---|---|
| `modin-project__modin-6937` | 候选与 gold 的 F2P 都通过；同一 S3 P2P 都失败 | 是，`index=False` 引起的空 metadata 越界已修复 | 当前负判不能证明实现失败；需复验共享 S3 环境问题后才能宣称完整通过 |
| `pandas-dev__pandas-48106` | 候选仅过 1/16 F2P，gold 过 16/16；另有共同的 3 个 P2P ID 缺失 | 明确给出的 `s.loc[3] = 0` 示例完成 | 纠正 ID 后仍是官方任务不通过；留下 15 个真实行为失败，但它们是题面未明确展开的类别保留要求，且在空补丁中已经失败 |
| `getmoto__moto-5701` | 候选、gold 都过 F2P；同一个 Unicode P2P 的原始输出通过，引用 ID 不匹配 | 给出的无空格路径不足以确定真实触发条件；候选修复了后来获取的空格前缀问题 | 按原有 F2P/P2P、纠正唯一 ID 后有条件通过；轨迹直接获取上游 PR diff，不能据此证明独立解题 |
| `pandas-dev__pandas-50319` | 候选与 gold 原始 pytest 都是 114 passed；共同的 1 个反斜杠 P2P ID 缺失 | 是，而且返回正确格式，超过“允许返回 None”的题面下限 | 已有完整输出支持评分假阴性；应先修正唯一 ID 对应并重算既存日志 |
| `Project-MONAI__MONAI-2454` | 原候选与官方新增测试文件冲突；投影后 1 F2P 真失败，1 P2P 通过 | 明确写出的 NumPy 零维数组问题完成 | 原始 apply error 与投影后的 Python 标量形状错误是两件事；较广的标量保形契约未完成，不能直接写成“连 NumPy 零维数组都不会修” |

因此，“四题 gold 也不过”不能整体替候选免责；反过来，也不能把这些负判整体计为模型实现失败。`pandas-48106` 是最直接的反例：共享评分缺陷与候选相对官方目标的真实不足同时存在。

五条轨迹都正常结束：`type=result`、`subtype=success`、`terminal_reason=completed`、`stop_reason=end_turn`；没有证据表明这五题因为工具轮数、上下文或墙钟超限被截断。单次完成或失败也不能用于估计模型能力上限。

## 2. `modin-project__modin-6937`

### 题面、实现与测试目标

题面提供具体报错栈：`ParquetDispatcher.build_query_compiler` 在 `dataset.pandas_metadata["column_indexes"][0]["numpy_type"]` 越界，触发条件是 `to_parquet(index=False)` 后读取。信息足以定位，目标清楚。

候选增加 `and dataset.pandas_metadata["column_indexes"]`，gold 增加 `and len(dataset.pandas_metadata["column_indexes"]) == 1`。对这道题实际触发的空列表，两者都会跳过 `[0]` 访问；没有“必须采用 gold 的长度写法”这一实现要求。官方测试将 `test_read_parquet_6855` 参数化为 `index=False/True`，并明确承认 `index=False` 时 pyarrow 不保留列标签类型，在比较前手工将列名转换为整数。这没有要求候选恢复题面未承诺的整数列标签。

### 真实失败及缺失

- F2P：`modin/pandas/test/test_io.py::TestParquet::test_read_parquet_6855[False-pyarrow]`。空补丁失败，gold、candidate、candidate_projected 都通过。
- P2P：2354 个引用中，三种补丁均只有 `modin/pandas/test/test_io.py::TestCsv::test_read_csv_s3_issue4658` 失败；没有引用缺失。错误链是 `ListObjectsV2` 对 `dask-data` 报 `NoSuchBucket`，继而 `FileNotFoundError`，与 parquet metadata 代码无关。
- 原始 pytest：gold 与两种 candidate 都有 `3059 passed, 1 failed, 124 skipped, 324 xfailed, 19 errors`。19 个错误是 `moto_server s3` 参数不兼容，日志明确为 `unrecognized arguments: s3`；它们不属于这题列出的 F2P/P2P，却说明该完整测试文件的环境仍不干净。
- 证据：`ledger/logs/modin-project__modin-6937/candidate_projected/default/a1/test_output.txt:2177` 开始是 S3 P2P 失败；`:2278` 为 `NoSuchBucket`；`:6302` 是 pytest 汇总。gold 和空补丁的同名状态可在各自 `status_map.json` 对照。

### 轨迹与反证边界

轨迹先检查真实 metadata，`stream:1038` 的工具结果打印 `"column_indexes": []`；随后复现 IndexError，再实现保护条件。`stream:1694` 后验证字符串列，`:1734` 后验证整数列的 `index=False/True` 两种情况；`:2676` 运行新增测试，`:2727` 运行相邻测试。终态为 `stream:3375`，正常完成。这支持一次实际调试成功，而不只是 final 文本宣称成功。

候选与 gold **并非所有可能输入都等价**：当 `column_indexes` 长度大于 1，且第一项 `numpy_type` 是 `int64` 时，候选还会进入整列 `astype("int64")`，gold 不会。现存材料未提供真实多级列 parquet 在该版本中进入这一路径的对照结果，也未证明 gold 在该输入下整体正确；不能仅凭构造一个 metadata 字典，把这一差异升级为本题真实模型失败。这个区别也不构成 `index=False` 空列表问题的反例。

最小复验：保留候选，先在固定 S3 fixture/兼容依赖下对空补丁、gold、candidate 重跑目标 F2P 与上述唯一 P2P；若需要宣称与 gold 的一般行为等价，再加真实 parquet 产生的 0/1/多级列 metadata 对照，不能只测私有函数伪造参数。本轮没有足够证据直接将当前 strict 结果改为通过。

## 3. `pandas-dev__pandas-48106`

### 题面、实现与隐藏的目标扩张

实际题面是数值赋值导致的内部异常，给出唯一明确预期：`Series(["a", "b", "c"], dtype="category")` 扩容写入 `0` 后得到 object Series。它甚至用括号说明扩容时会转成 object。因此，“恢复这个旧版本例子的行为”是一个合理目标。

候选在 `indexing.py` 中令 categorical 分支使用 `new_dtype=None`，由后续拼接推断 dtype；它修好了该例子。gold 在共享 `_maybe_promote` 中区分“值在已有类别中或是缺失值”与“新类别”：前者保留 categorical，后者转 object。官方新增 16 个 F2P 中，15 个要求保留 categorical 信息，而不是仅停止抛错。这是可观察的公共行为要求，并未规定必须改哪个内部函数；但其范围比题面明确示例更广。

### 真实失败及缺失

候选及投影候选的 16 个 F2P 中，唯一通过的是：

`pandas/tests/indexing/test_loc.py::TestLocWithMultiIndex::test_additional_element_to_categorical_series_loc`

其余 15 个均真正执行并失败：

1. `test_additional_categorical_element_loc`：扩容写入已有类别 `"a"`，实际 object，预期 categorical。
2. `test_loc_set_nan_in_categorical_series[...]`：10 个参数 `UInt8, UInt16, UInt32, UInt64, Int8, Int16, Int32, Int64, Float32, Float64`，向以 nullable 数值 Index 为 categories 的 Series 扩容写入 `np.nan`；实际 object，预期保留 `CategoricalDtype`。失败发生在扩容后第一个断言，不能把后续“向已有位置写入 NaN”也当作已经执行失败。
3. `test_loc_consistency_series_enlarge_set_into[...]`：4 个参数 `nan, na1, None, na3`（测试值为 `np.nan, pd.NA, None, pd.NaT`）；扩容与写入已有位置的 dtype 不一致。

这 15 个均属于 `pandas/tests/indexing/test_loc.py::TestLocWithMultiIndex`。投影候选日志 `:6149` 起为第一个失败，`:6167` 起为数值类别测试，`:6416` 起为缺失值一致性测试，`:7574` 起列出全部失败 ID，`:7589` 汇总 `15 failed, 1029 passed, 1 xfailed`。gold 是 `1044 passed, 1 xfailed`。

P2P 的 1020 个引用中有 3 个共同缺失，均为：

`pandas/tests/indexing/test_loc.py::TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\('2017',`

以及相同前缀的 `2018`、`2019`。参考 ID 的 `Period` 后是一个反斜杠，而状态 key 中是两个反斜杠；对应的原始 pytest 用例均通过。纠正它们只解决评分身份问题，不会消除上述 15 个 dtype 失败。

尤其需要纠正措辞：空补丁原本就有 16 个 F2P 失败，其中包括这 15 个。它们是**候选未覆盖的官方修复范围**，不是候选新增的 15 个回归。当前证据未显示候选新增 P2P 行为失败。

### 决定性轨迹与最小反例

`stream:3395` 的修改前实测已经显示，扩容写入 `"a"`、`None`、`pd.NA` 得到 object，写入 `0/1.5` 抛内部 TypeError。候选因此把“已有 dtype 退化行为”当作应保留的基线。`stream:12597` 的 thinking 明确知道有效类别和 NA 仍会退化为 object，认为这是原行为，最终选择保留；不是没发现该现象。

这构成两个合理目标的最小分歧：

```python
s = Series(["a", "b", "c"], dtype="category")
s.loc[3] = "a"
# 候选沿用原行为：object。
# 官方扩展目标：仍为 category，保留 categories 与 ordered 元数据。
```

或者把最后一行值改为 `np.nan`：扩容与写入已有位置应否保留同一 categorical dtype，题面没有明确列出。保留 categorical 是合理的库语义，因为值属于现有类别或缺失值时没有扩展类别集合的必要；但“合理”不等于“题面已经清楚要求”。不能因此把候选修好 numeric TypeError 的证据抹掉。

候选确实做了相关验证，终态报告的 `test_setitem.py` 大测试与局部 categorical/扩容测试通过；这些测试集合没有包含后来注入的 15 个官方目标。`stream:12599` 正常完成。准确归因是：**选择了恢复狭义回归行为的目标，对官方更广 categorical 语义不足**。不能从这一次结果推出“无法理解 categorical”。

最小复验：无需再采样模型来解释这次成绩。先修正 3 个 ID 并重算，再明确任务究竟是恢复题面旧行为，还是要求“已有类别/缺失值保留 categorical，新类别退化 object”。若采用后者，补入题面并重跑这 16 个目标用例；当前候选在该标准下应继续判失败。

## 4. `getmoto__moto-5701`

### 题面不足与上游答案可达

题面描述 Spark 不能列目录，但给出的路径中没有空格；作者也明确不知道 Spark 发出的 HTTP 请求。仅据该文本，无法唯一锁定 `+` 被错误当成字面加号的解析问题。候选后来修复的是“server mode 下带空格的 prefix 被 URL 编码成 `+`”这一更具体问题。

决定性证据不是模型最终说自己参考了上游，而是实际工具调用和返回：

- `stream:11337` 使用 GitHub API 读取原 issue `#5680` 及评论。
- `stream:12049` 使用 `urllib.request.urlopen('https://github.com/getmoto/moto/pull/5701.diff')`，直接请求本题对应上游 PR 的完整 diff。
- `stream:12050` 的工具结果返回该 PR 的生产修复与测试变更；紧随后的 `stream:12517/12519` 编辑实现。
- `stream:12939/12941` 与 `:13713` 也写入同款官方测试参数和断言；候选的生产新增/删除语句与 gold 相同。

这条轨迹可以证明“获取并应用已公布的修复，随后复验”，不能证明“仅根据题面自主推理出修复”。不能据此断言模型做不出，也不能把它计入无答案访问条件下的独立成功。最终 `stream:14257` 是正常完成，没有截断。

### 真实失败及缺失

- F2P 引用为 `tests/test_s3/test_server.py::test_s3_server_bucket_create[baz`，实际参数是 `"baz bar"`，参考/解析 ID 在空格处截断。空补丁失败，gold、candidate、candidate_projected 都通过。
- P2P 的 149 个引用中仅有 Unicode 项缺失：参考 `tests/test_s3/test_s3.py::test_key_with_special_characters[/the-key-unîcode/test]`，状态中对应 `tests/test_s3/test_s3.py::test_key_with_special_characters[/the-key-un\xeecode/test]` 是 PASSED。其余 148 个引用通过。这个结论可以从既存原始输出复核，不依赖 gold 恰好相同。
- 原始 pytest 在 gold 与两种 candidate 都为 `150 passed, 4 failed`；四个共同失败不在 F2P/P2P 中：`test_upload_from_file_to_presigned_url`、`test_put_chunked_with_v4_signature_in_body`、`test_presigned_put_url_with_approved_headers`、`test_presigned_put_url_with_custom_headers`。错误为响应体长度不足引起的 `IncompleteRead/ChunkedEncodingError`。空补丁也同样失败这四项，另加目标 F2P。
- 因此，若严格按本题既有 F2P/P2P 集合纠正唯一 Unicode ID，已存记录支持有条件通过；不能把整个测试文件写成全绿，也不能把这四个共有失败归因于候选。

### 题意与测试的最小分歧

`prefix="service=subscriptions"` 与 `prefix="timestamp=2020-01-01 01:01:01"` 是两种不同输入。后者中的空格在 query string 中可能成为 `+`，而前者没有这个触发条件。官方测试用 `"baz bar"`，确实覆盖后来确认的真实 bug，但原题面没有提供这个关键细节。题面初始路径能访问单文件、不能列目录这一现象，也不能单独排除 prefix 编码之外的其他原因。

最小复验：先离线核对 Unicode 参数与原始 pytest ID 的一一对应；然后以同一 Flask server 请求比较无空格、空格、字面 `+` 三种 prefix，并记录原始 query string。若要衡量自主解题，可提供必要 HTTP 请求而不提供 PR 修复，并用无法访问答案/未来 Git 历史的环境另采样；不能通过修改本次轨迹标签，将已经发生的答案访问变成独立成功。

## 5. `pandas-dev__pandas-50319`

### 明确允许的两种目标

题面最后一句明确允许返回 `None` 或正确格式，只要求不抛错。官方测试却固定期望 `%d.%m.%Y %H:%M:%S.%f`。这是实质性的目标收窄：一个对该输入返回 `None`、对其他输入保持行为的修复，可以满足题面，但会失败官方 F2P。这个最小反例不需要猜测某个内部实现。

当前候选没有踩到这个分歧。它针对 `_fill_token` 拆分 `"."` 后两侧为空的情况返回原 token，实际正确猜出格式；gold 用正则判断是否为数字小数 token。二者内部写法不同，官方测试没有要求 regex，也没有拒绝候选。

### 真实失败及缺失

- F2P：`pandas/tests/tslibs/test_parsing.py::test_guess_datetime_format_with_parseable_formats[27.03.2003`，空补丁失败，gold、candidate、candidate_projected 都通过。
- P2P 109 个引用中唯一缺失是 `pandas/tests/tslibs/test_parsing.py::test_is_iso_format[%Y\%m\%d`。状态 key 中的反斜杠变成双反斜杠；对应原始用例通过。
- gold、两种 candidate 的原始 pytest 都是 **114 passed**；投影候选 `test_output.txt:6264` 给出汇总。`status_map.json` 只有 110 个 PASSED key，说明参数 ID 解析还会合并部分显示项，不能把“110 个 key”写成“实际只执行 110 个测试”。

轨迹从 dateutil lexer 输出找到独立 `"."` token，重现异常，修改 `.pyx`，重编译 C 扩展后验证该输入及周边日期格式，最后运行完整 `test_parsing.py`。关键操作是 `stream:2358`（原 bug）、`:5064`（实现）、`:5551`（重编译）、`:5556`（目标验证）、`:6901`（完整文件）；`:8963` 正常终止。既存记录支持真实修复，不是未生效的源码补丁。

候选对私有 `_fill_token` 的任意字符串，与 gold 不必完全等价；例如包含点但不是数字的任意伪造 token 可能走不同分支。现存资料没有证明这些 token 能从本版真实 dateutil lexer 进入该函数，因此不把私有函数任意参数上的差异当作生产 finding。

最小复验：优先从现存日志恢复完整参数身份，验证反斜杠项为唯一对应后重算评分，不需要先重新生成候选。若将此题用于新实验，题面与 oracle 应统一：明确要求正确格式，或允许原题面承诺的 `None`；这属于评分目标选择，不能悄悄作为 ID 修正的一部分。

## 6. `Project-MONAI__MONAI-2454`

### 狭义题面与较广仓库契约

题面明确写“NumPy array with 0 dims”，但用于解释根因的示例是 Python `int` 输入 `np.ascontiguousarray(2)`。这允许两种有依据的目标：

1. 只修复 NumPy 零维 `ndarray`，保留其他输入原有行为。候选实现了这个目标。
2. `ToTensor` 对所有已接受的标量表示（Python 数值、NumPy 零维数组、Torch 零维 tensor）都保留零维形状。官方测试/gold 采用这个目标。

仓库原有 `ToTensor` 类说明是 `Converts the input image to a tensor without applying any other transformations`，`__call__` 没有输入类型限制，并说使结果 contiguous。一般“只转换表示、保持形状”的解释支持目标 2；但 docstring 没有显式列出 Python scalar，题面正文又明确限定 NumPy 数组。因此，官方目标合理，却不能据此认定目标 1 是不理解题面的错误修复。`ToNumpy` 相邻实现也仍使用 `ascontiguousarray`；资料不足以声称仓库此前已经有统一的所有标量保形规范。

### 必须分开的两次评分

原候选新增 `tests/test_to_tensor.py`，官方 `test_patch` 恰好也新增同一路径。原始评分的 `git checkout <base>` 保留候选文件，之后 `git apply` 在 `candidate/default/a1/test_output.txt:580` 报 `already exists in working directory`。后面的 4 passed 是候选自己的四个测试，不是官方 1 个 F2P + 1 个 P2P。这个正常的回归测试文件命名冲突本身没有证明篡改测试。

exact-official-path projection 去掉候选对该测试文件的改动后，官方测试确实执行：

- `tests/test_to_tensor.py::TestToTensor::test_array_input`：PASSED。
- `tests/test_to_tensor.py::TestToTensor::test_single_input`：FAILED。
- gold 两个都通过；空补丁也是 1 failed、1 passed。

失败输入可直接从原始 traceback 确认：测试依次循环 `(5, np.asarray(5), torch.tensor(5))`，第一项 `5` 已失败，`actual=tensor([5])`、`expected=tensor(5)`，shape `(1,)` 与 `()` 不同。证据为 `candidate_projected/default/a1/test_output.txt:595` 起，`:610` 给出实际/预期，`:644` 给出 shape mismatch。由于第一项已退出，**官方这个失败记录没有执行到后两项，不能说 NumPy 零维数组的修复仍然失败**。

### 候选实际修复范围与决定性轨迹

候选对 `isinstance(img, np.ndarray) and img.ndim == 0` 直接 `torch.as_tensor(img)`，对 torch 输入维持 `.contiguous()`，其他输入维持原路径。`stream:4439` 的工具输出真实显示：

```text
ndarray () -> torch.Size([]) tensor(2)
int None -> torch.Size([1]) tensor([2])
```

`stream:4704` 的 thinking 明确注意到 Python `2` 仍变成一维，并基于 NumPy 题面与未写 scalar 的 docstring，决定保留这一行为。它不是未试到标量，也不是耗尽预算而停下。`:4750` 正常完成。候选自己的 NumPy 零维、非连续数组、非连续 tensor、list/tuple 四个测试都通过；这支持狭义修复与连续性保持。

最小分歧反例就是 `ToTensor()(2)` 与 `ToTensor()(np.asarray(2))`：同一数值、不同输入表示，候选分别返回一维与零维，gold 都返回零维。在较广“纯表示转换”的目标下，这是明确的实现不足；在狭义“修 NumPy 零维数组”的目标下，它是未被要求改变的原行为。

最小复验：保持官方文件投影，分别独立验证 Python `5`、NumPy `np.asarray(5)`、Torch `torch.tensor(5)`，使三种输入不会因第一个断言失败而遮蔽后两种；同时保留非连续数组/列表的连续性验证。如果正式任务目标包含所有标量，应补清题面并继续把当前候选判失败；若只评原文明确的 NumPy 零维数组，应单独标为该目标已完成。这个范围选择不能用自动删除失败断言代替。

## 7. 统一的证据约束与下一步

1. F2P/P2P 是有限的任务引用集合，原始 pytest 完整文件统计、解析后的去重 key 数、最终 strict 判定不是同一个量。本报告分别保留，未将缺失 ID 视为已经执行失败。
2. 修正引用 ID 应以原始参数值和输出为依据验证唯一对应，不能对所有字符串做宽松去转义后直接认定通过；既有按空格截断的 ID 还存在合并风险。
3. 题面范围与官方 oracle 不一致时，应记录两种目标及其结果。pandas-50319 的“允许 None”是最明确的文字分歧；MONAI 与 pandas-48106 是输入范围/类型保留语义的扩张。它们均不是测试强制采用某个私有函数或 gold 补丁文本。
4. 若用于后续无答案访问的能力实验，moto 这次上游 PR diff 访问必须单独标记；代码正确性可以继续评价，解题来源不能被投影步骤洗掉。
5. 本轮只做分析与证据重算。没有改题面、测试 oracle、候选、生产代码或成绩账本，也没有做新的环境复跑。因此“有条件通过”不等于本轮已执行修复并正式重评通过。

## 8. 补充复核：`pydantic__pydantic-5706` 的低覆盖假阳性

### 结论与成立范围

这是比“删掉无功能注释后 mutation 仍过”更强的低覆盖反例。官方将候选判为 `RESOLVED_FULL/strict_full=true`，同时现有轨迹证明候选改动破坏了旧 Python `Sequence` 测试所要求的输出类型和输入接受范围。模型见到这些失败后，改了旧测试断言来顺应自己的新行为。这不依赖猜测，也不依赖拿 gold 补丁字面做唯一标准。

但不能误写成“模型修改官方 P2P 断言从而骗过本次 grader”。本题官方只执行 `tests/test_json_schema.py`；被改的 `tests/test_types.py` 和 `tests/test_edge_cases.py` 不在这个执行面里。成功的直接原因是官方验证范围只覆盖 JSON，未覆盖 Python 行为。`candidate_projected` 的 `projected_dropped=[]`，同样通过。

### 题面本身存在方向分歧

题面说 `model_json_schema()` 抛出异常“seems as a correct behavior”，并提出“如果 schema 生成抛错，JSON 验证也应抛错”的未勾选条目。明确提出的一致性问题可以走两种路线：统一拒绝，或让 schema 和 JSON 数组校验都成功。官方选择后者；它新增两种测试，各自参数化 `List` 与 `Sequence`，都要求 schema 是 integer array，并要求 JSON 数组校验成功。

应精确计数：新增参数用例一共 4 个，但 **F2P 只有两个 `Sequence` 参数**，另两个 `List` 参数原来就通过。官方引用是 2 F2P + 273 P2P，并非 4 F2P。当前候选修好了这个官方 JSON 目标，但不能从题面“一致性”推导出还应统一改变 Python 模式下的 Sequence 类型保留与输入接受范围。

gold 使用 `json_or_python_schema`：JSON 模式使用 list schema，Python 模式继续先验证 `typing.Sequence` 并用既有 `sequence_validator`。这表明修好 JSON 并不要求丢掉原 Python 语义。候选却在 `SEQUENCE_ORIGIN_MAP` 增加 `collections.abc.Sequence: list`，令 Python 模式也走 list 路线。

### 先失败、再修改断言的完整证据链

以下均为原始 `ledger/logs_cc/pydantic__pydantic-5706/stream.jsonl` 行号：

1. `:6871` 实施唯一相关生产行为变更：增加 `collections.abc.Sequence: list`。
2. `:6904` 运行仍未修改的 `tests/test_types.py -k sequence`；`:6905` 返回 **6 failed, 10 passed, 635 deselected**。失败包括 tuple、range、deque、tuple-of-tuples 的 `test_sequence_success` 四项，`test_sequence_generator_fails`，以及 set 输入的错误类型检查。
3. `:8165` 的独立小脚本输出确认真实公共行为：tuple 变 list，deque 变 list，range 被 `list_type` 拒绝，tuple-of-tuples 变 list-of-tuples。`:8409` 确认 generator 从应拒绝变成 `[1, 2, 3]`。
4. `:8861` 运行 `tests/test_types.py tests/test_edge_cases.py tests/test_generics.py`；`:8864` 返回 **8 failed, 882 passed, 5 skipped, 11 xfailed**。新增的两个失败是 `test_sequences_str[Sequence[str]]` 和 `test_sequences_str[Sequence[bytes]]`，错误契约从 `sequence_str` 变成 `list_type`。
5. `:7826`、`:8163`、`:9944` 的 thinking 曾明确考虑“保留 Python 行为、仅修 JSON”的替代方案，却依据现有映射表与对未来版本的记忆，认定 list 化是预期设计，并决定更新测试。现有轨迹没有给出这种 Python 公共行为改变的需求依据。
6. `:12069` 把 tuple/deque/外层 tuple 的预期改成 list，并删除 range 成功用例；`:12093` 把 `test_sequence_generator_fails` 改名并改为 generator 成功断言；`:12128` 改 set 的错误预期；`:12152` 改 str/bytes 的错误预期。对应工具结果均确认写入成功。
7. `:12199` 终态是 **`error_max_turns`、`terminal_reason=max_turns`、`num_turns=61`、`stop_reason=tool_use`**。上述改断言之后没有留下新的 pytest 复跑记录。它与前五题的正常终止不同；不能把改后旧测试全过当作已经验证的事实。

可读的最小反例：

```python
class Model(BaseModel):
    v: Sequence[int]

Model(v=(1, 2, 3)).v  # 旧测试要求 tuple；候选实测为 list。
Model(v=range(5))     # 旧测试允许；候选实测拒绝。
Model(v=(i for i in [1, 2, 3]))  # 旧测试要求拒绝；候选实测接受。
```

这些变化均通过公共 `BaseModel` 入口可达。即使暂不争论错误字符串是否属于应稳定的契约，前两类“输入缩窄/放宽”与容器类型改变已足够证明 JSON 评分全过不代表候选满足仓库原有行为约束。不能仅凭模型改了测试推断主观作弊意图；可以直接评价为无需求依据的契约改变和验证方式不可靠。

### 最小复验与本轮限制

保留候选生产代码，恢复 base 的 `tests/test_types.py` 与 `tests/test_edge_cases.py`，重跑上面 8 个失败及官方 JSON 用例；对 gold 做同组对照。既存轨迹已经给出候选改源后、改断言前的失败结果，本轮不需要实际启动 Docker 才能判定覆盖缺口。新复跑用于冻结可复核的同环境证据，而不是继续寻找一个能让现有改断言通过的 oracle。

本报告未把其他题目的 mutation 通过当作证据：例如只删除 docstring 末尾 hunk、保留所有功能修复的 mutation，本来就应继续通过，不能据此证明测试覆盖不足。
