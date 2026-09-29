# scrapy__e9387529 修订方案（修订执行者，2026-09-29）

单题闭环试行，按统一标准 v1 §5 执行。本文件与 `revision_draft.json` 是**修订草案**；正式修订单、pins、派生镜像材料步骤由协调者落，之后还要正式评分与 Codex 复核。路径均相对仓库根；`PUB` = `runs/r2e_static_prep_20260924/v3/public/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4`，`OUT` = 本目录，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925`。

## 0. 结论

- **模板：R-c**（v1 §10 表中本题一行、§11「dict item；gold 回归用 C1 作正对照」）。在 `PythonItemExporterTest` 里补三个 `binary=True` 测试：普通 dict item、`export_empty_fields` 的缺省值、字段 serializer 返回非字符串。
- **正对照：C1**（`runs/r2e_actor_20260925/grader_cands/scrapy_e938_C1_bytes_keys_when_binary.patch`），gold 在两个新键上失败，按 v1 §5 / D4 记录为原 gold 的失败，不为保住 gold 放宽断言。
- **试跑结果：全部符合预期**（§4）。C1、RC2 都是 65/65；noop、gold、C2、C3 都为 0，且各自只错在预期的键上。
- 没有需要用户决定的事项；有两处刻意不测的歧义点写在 §6。

## 1. 触发问题与依据

| 问题 | 证据 | 公开依据 |
| --- | --- | --- |
| 同一核心要求的其它实例（dict item）没测：只对 `Item` 生效的 C2 得 1 | C2 在当前材料、本机镜像上 62/62 match（`OUT/trials/cur_C2.json`）；私有对照里 C2 对顶层 dict item 仍返回 str 键（`B2/grader_candidates.md:197-207`） | 题面说的是「the exported item's keys」（`PUB/user_prompt.txt:8`，`:19`）；文档写明可以导出原生 dict（`PUB/worktree/docs/topics/exporters.rst:170-172`，`:202`，`:210`）；`PUB/worktree/docs/news.rst:319`「Allow spiders to return dicts」；公开测试 `PUB/worktree/tests/test_exporters.py:54-55`（`test_export_dict_item`） |
| 目标断言只用题面示例的字面值（v1 §4 第 2 步） | 唯一目标键 `test_export_binary` 就是题面原例 | 同上，题面按一般表述理解 |
| gold 的未测回归：`binary=True` 时 `export_empty_fields` 的缺省值、serializer 返回非字符串都会抛 `TypeError` | 私有对照 E1a / E1b（`B2/grader_candidates.md:199-207`）；本次试跑 gold 在两个新键上分别报 `to_bytes must receive a unicode, str or bytes object, got NoneType` / `got int`（`OUT/trials/draft_gold.json`） | `export_empty_fields` 会导出未填字段（`exporters.rst:204-210`），base 以 `default_value=None` 产出（`PUB/worktree/scrapy/exporters.py:54-78`）；声明了 serializer 时导出的就是它的返回值（`exporters.rst:93-95`，`:164-166`；`exporters.py:257-259`）；`encoding` 只作用于 unicode 值，其它类型原样交给序列化库（`exporters.rst:212-217`）。v1 §10 已判为「有文档的常用行为」 |

Codex 第二批复核对本题的最小补测建议（`docs/.../r2e_static_batch2_review_20260925/aio_scrapy/README.md:86`）是「普通 dict、`export_empty_fields` 的 None、serializer 保留返回值及 binary=False 回归」，并要求嵌套 key 策略、非字符串 key、特定 encoding 另行界定（同文件 `:84`）。本方案逐条对应，binary=False 回归由现有三个键承担（§6）。

## 2. 具体改动

`r2e_tests/test_1.py`，一条 `hidden_test_text_replace`、一处 edit：old 为 `test_export_binary` 整个方法（原文第 119–123 行），new 为原方法加上下面三个方法（插在 `PythonItemExporterTest` 末尾、`PprintItemExporterTest` 之前）：

```python
    def test_export_binary_dict_item(self):
        exporter = PythonItemExporter(binary=True)
        value = {'title': u'Caf\xe9', 'price': u'3'}
        expected = {b'title': b'Caf\xc3\xa9', b'price': b'3'}
        self.assertEqual(expected, exporter.export_item(value))

    def test_export_binary_empty_fields(self):
        exporter = PythonItemExporter(binary=True, export_empty_fields=True)
        value = TestItem(name=u'Maria')
        expected = {b'name': b'Maria', b'age': None}
        self.assertEqual(expected, exporter.export_item(value))

    def test_export_binary_serializer_output(self):
        class CustomFieldItem(Item):
            name = Field()
            age = Field(serializer=lambda value: int(value) + 2)

        exporter = PythonItemExporter(binary=True)
        value = CustomFieldItem(name=u'Maria', age=u'22')
        expected = {b'name': b'Maria', b'age': 24}
        self.assertEqual(expected, exporter.export_item(value))
```

设计取舍：
- 三个测试都只有**扁平的顶层键**，键全是 ASCII，不涉及嵌套 dict 的键（R6）、非字符串键（R9）、键的编码（R10）这三处公开材料多解的地方。
- dict item 用了与题面示例不同的键和值，满足「非示例实例」；值含非 ASCII，只是沿用既有的值编码行为（题面 Actual 与 Expected 的值相同，`user_prompt.txt:21,27`）。
- 缺省值断言 `None`、serializer 断言 `24`：两者都是 base 在 `binary=True` 下的既有输出（E1a / E1b 的 base 列），题面只要求改键，文档说非 unicode 值原样传递。
- 写法沿用同文件 `test_export_binary` 与 `test_field_custom_serializer` 的风格。

完整条目见 `OUT/revision_draft.json`（与试跑用的 `OUT/trials/inputs/draft_e938.json` 逐字相同，已比对）。

## 3. 修订后期望映射（62 键 → 65 键）

原 62 键全部保留、状态不变（都是 PASSED）；新增三键，状态 PASSED：

- `PythonItemExporterTest.test_export_binary_dict_item`
- `PythonItemExporterTest.test_export_binary_empty_fields`
- `PythonItemExporterTest.test_export_binary_serializer_output`

没有删除或改状态的键。新键的状态来自上面的公开依据，不是抄 gold 输出（gold 在其中两键上失败）。

## 4. 验收计划与试跑结果

镜像 `sha256:b9f99c7d16d1b77a8f268040407f186fa820bf7930f232a5a0a0974137632c54`，配方 `r2e_derive_v1+sysconfig_v1`；结果文件在 `OUT/trials/`。补丁都在 `runs/r2e_actor_20260925/grader_cands/`（sha256 前缀与第二批账本一致）。

| 材料 | 候选（补丁，sha256 前缀） | 应得 | 实得 | 不符的键 | 结果文件 |
| --- | --- | --- | --- | --- | --- |
| 当前 | noop | 0 | 0 | `test_export_binary` | `cur_noop.json` |
| 当前 | gold（19ae84d4） | 1 | 1 | — | `cur_gold.json` |
| 当前 | C2 只处理 `Item`（`scrapy_e938_C2_items_only.patch`，35775c88） | 漏判 | 1 | — | `cur_C2.json` |
| **草案** | C1 顶层键转 bytes（`scrapy_e938_C1_bytes_keys_when_binary.patch`，c218113f）**正对照** | 1 | 1（65/65，两次） | — | `draft_C1.json`、`draft_C1_r2.json` |
| **草案** | RC2 连嵌套 dict 的键也转（`scrapy_e938_RC2_keys_everywhere.patch`，978ced96） | 1 | 1 | — | `draft_RC2.json` |
| **草案** | noop | 0 | 0 | `test_export_binary`、`test_export_binary_dict_item`、`test_export_binary_empty_fields`、`test_export_binary_serializer_output` | `draft_noop.json` |
| **草案** | gold | 0（D4 记录） | 0 | `test_export_binary_empty_fields`（TypeError got NoneType）、`test_export_binary_serializer_output`（TypeError got int） | `draft_gold.json` |
| **草案** | C2 | 0 | 0 | 仅 `test_export_binary_dict_item` | `draft_C2.json` |
| **草案** | C3 不看 `binary` 总转 bytes（`scrapy_e938_C3_always_bytes_keys.patch`，8e12bb8c） | 0 | 0 | `test_nested_item`、`test_export_list`、`test_export_item_dict_list`（与修订前相同） | `draft_C3.json` |

对照 v1 §5 R-c 验收：正对照 1、noop 0 ✓；要纠正的漏判（C2）已纠正，gold 的两处回归现在能被测出 ✓；已知错误候选 C2、C3 为 0 ✓；所有行 `missing` / `extra` 为空 ✓。RC2 通过说明新测试没有替 R6（嵌套 dict 的键要不要转）选边。

## 5. 正对照：C1 的独立核实

- **静态与复核**：第二批独立复核把 C1 定为「合理替代解（在 R6 多解的前提下）」（`B2/results/scrapy__e938…/review.md:69`，理由见 `:76`）；Codex 第二批复核「C1 与 RC2 均被接纳」（`docs/.../r2e_static_batch2_review_20260925/aio_scrapy/README.md:84`）。
- **行为**：私有对照中 C1 对缺字段给 `None`、对 int serializer 保留 `22`，dict item 的键为 bytes（`B2/grader_candidates.md:203`）。
- **评分**：修订前 62/62（第二批正式评分，`B2/grader_candidates.md:66`）；修订草案下 65/65 两次。
- C1 只改 `PythonItemExporter.export_item`：`binary` 时把 `_get_serialized_fields` 产出的顶层键逐个 `to_bytes(k, encoding=self.encoding)`，值不再二次序列化。
- **原 gold 的失败**：在两个新键上抛 `TypeError`，原因是 gold 在 `binary` 时对结果再跑一遍 `_serialize_dict`，让 `None` 与 int 进入 `to_bytes`。按 D4 记录，不改题意、不放宽断言。

## 6. 修订后仍受保护的公开要求与刻意不测的地方

- **核心要求**（`user_prompt.txt:18-22`）：`test_export_binary`（原例）+ `test_export_binary_dict_item`（非示例实例、dict 输入）+ 两个新测试里的 bytes 键断言。
- **既有行为**：`binary=False` 保持 str 键（`test_nested_item`、`test_export_list`、`test_export_item_dict_list`，C3 仍被拒）；其它 8 个 exporter 的 53 个键；`binary=True` 下缺省值 `None` 与 serializer 返回值原样保留（新增）。
- **刻意不测**（公开材料多解或没有已知错误候选，不在本次修订内）：
  - 嵌套普通 dict 的键（R6）、非字符串键（R9）、键的编码（R10）：公开读者列为多解，Codex 要求另行界定。
  - serializer 在 `binary=True` 下返回 **str** 时要不要再编码成 bytes：题面一句「Both the keys and values … should be in bytes」（`user_prompt.txt:19`）与文档「返回 serializer 的结果」（`exporters.rst:164-166`）指向不同做法，gold（编码）与 C1（保留）也不同，所以不断言。
  - 反过来，「把 `None`、int 也转成 bytes」这种读法没有公开依据：`to_bytes` 本身拒收非文本（`PUB/worktree/scrapy/utils/python.py:110-120`），文档说非 unicode 值原样传递，所以新测试按保留原值断言，不属于两种读法都有依据的 P5。
  - `fields_to_export` 在 `binary=True` 下的键（R8）：可推知，但没有已知的错误候选，按「没有误拒或漏判案例的不专门造」不加。

## 7. 版本记录

- **父版本**：来源材料，无修订；期望 `sha256:51436068b6603499581b8d7a6a15deda94dc9742e73dfe53b8966bd7a78b1541`；隐藏测试树 `sha256:58e496ececeac8aa4b3502022909fe4e29a932caa12941e7c04ae4792e4a550a`；`test_1.py` `sha256:21ec99b12c8e8a9cf72a34c273ebe4443303eb818fdad8c5a6637046e40df169`。
- **新版本**：`test_1.py` 修订后 `sha256:fe29720c728847dbf89da3ce2992e0dd70bbcfe33ee964779921a03189123e2d`；期望 65 键（`OUT/trials/inputs/expected_e938.json`）。
- **触发反例**：C2（dict item 漏修得 1）、gold 的 E1a / E1b 回归。

## 8. 试跑与正式评分的差别

`trial_grade.py` 不做基线重建比对、不核隐藏测试树与入口摘要，权限简化（见脚本文件头）。定稿后需协调者写正式修订单（一条 `hidden_test_text_replace`；期望用 `expected_file_replace`，`added` 3 键），重建派生镜像材料步骤，用正式评分复验 C1 / noop / gold / C2 / C3（可加 RC2），再交 Codex 复核。
