# scrapy__9a15fcf8 修订方案（修订执行者，2026-09-29）

单题闭环试行，按统一标准 v1 §5 执行。本文件与 `revision_draft.json` 是**修订草案**，不是正式材料：正式修订单、pins 与派生镜像材料步骤由协调者落，之后还要正式评分和 Codex 复核。路径均相对仓库根；`PUB` = `runs/r2e_static_prep_20260924/v3/public/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`，`OUT` = 本目录。

## 0. 结论

- **模板：R-a 为主，另合并两处 R-c**（v1 §5「一题有多个 S1 缺口时逐个列出、分别写依据，合并在同一轮修订里完成」）。
  1. **R-a**：删除两个在 py3 下必报 `TypeError` 的无效测试 `test_from_headers`、`test_from_args`，期望同步删两键。这是包里交代的范围。
  2. **R-c-1（Headers 契约守护）**：把公开旧测试 `tests/test_http_headers.py` 原样加入隐藏测试（`test_2.py`）。**原因：只做 R-a 时，已知错误候选 `bad_headers_str` 从 0 变成 1**（`OUT/trials/pure_bad_headers_str.json`），不满足 R-a 验收「已知相关的错误候选仍为 0」。
  3. **R-c-2（非示例实例）**：新增 `test_from_content_type_x_json`，断言不带参数、带别的 charset 的 `application/x-json` 也判为 `TextResponse`。**原因：目标断言只用了题面示例的字面值**（v1 §4 第 2 步严格版，D1）；逐字特判示例字符串的退化补丁在当前材料上得 1（`OUT/trials/cur_literal_hardcode.json`）。
- **试跑结果：全部符合预期**（§4）。gold 23/23 两次；noop 0；原先被误判为 0 的 P4 更完整修复变成 1；`bad_headers_str` 与逐字特判补丁都为 0。
- **与包描述的偏离**：包里只写了 R-a；R-c-1、R-c-2 是我按验收规则补的，三项彼此独立、可以拆开（§8）。请协调者与 Codex 复核时确认。

## 1. 触发问题与依据

| 问题 | 证据 | 公开依据 |
| --- | --- | --- |
| T5→无效断言：`test_from_headers`、`test_from_args` 期望 FAILED，是死键 | 当前材料 noop 与 gold 下两键都 FAILED（`OUT/trials/cur_noop.json`、`cur_gold.json`）；两测试都在第一个带头的映射处抛 `TypeError`（py3 下 `Headers` 存 bytes，`PUB/worktree/scrapy/responsetypes.py:67-76` 用 str 处理），断言到不了 | 上游在 py3 下整文件忽略 `tests/test_responsetypes.py`（`PUB/worktree/tests/py3-ignores.txt:40`，由 `PUB/worktree/conftest.py:25-29` 生效）；R2E 把文件搬进 `r2e_tests/` 后绕开了这条忽略 |
| 误拒：更完整的 py3 修复被判 0 | P4 更完整修复（在 `from_content_type` / `from_content_disposition` 边界解码 bytes）在当前材料、本机镜像上 mismatch：两死键 FAILED→PASSED（`OUT/trials/cur_p4_overfix.json`；历史正式评分同样 0，`runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl:1`） | 公开材料没有任何地方要求 py3 下 header 路径必须继续崩溃（首批复核 `r2e_static_review_20260925/results/scrapy__9a15…/review.md:151-156`） |
| 只做 R-a 会放过破坏 `Headers` 契约的补丁 | Codex 构造的 `bad_headers_str`（gold 表项 + `Headers.normvalue` 改返回 str）在只做 R-a 的中间稿上 5/5 match，得 1（`OUT/trials/pure_bad_headers_str.json`） | `PUB/worktree/scrapy/http/headers.py:14,18`（docstring「Normalize key/values to bytes」）；公开测试 `PUB/worktree/tests/test_http_headers.py:25-30` 断言返回 bytes，且该文件不在 py3-ignores 里；Codex 首批复核 `r2e_static_actor_review_20260925/semantics_b/review.md:37-49`（B2）、`README.md:67` |
| 示例拟合（T2c） | 逐字特判 `'application/x-json; encoding=UTF8;charset=UTF-8'` 的补丁（`OUT/cands/scrapy_9a15_literal_hardcode.patch`）在当前材料上 7/7 match（`OUT/trials/cur_literal_hardcode.json`） | 题面的一般表述：`PUB/user_prompt.txt:18`「Responses with the MIME type `application/x-json` should be interpreted as `TextResponse`」；示例只是其中一个带参数的实例（`:11-12`） |

## 2. 具体改动

全部在隐藏测试目录 `r2e_tests/` 内；`run_tests.sh` 不改（它在公开工作树里可见）。

**(1) `test_1.py`，一条 `hidden_test_text_replace`，三处 edit（依次执行，每处 old 恰好出现一次）：**

- edit 1：删除 `test_from_headers` 整个方法（原文第 55–65 行，含其后空行），new 为空。
- edit 2：删除 `test_from_args` 整个方法（原文第 66–79 行，含其后空行），new 为空。
- edit 3：在 `def test_from_body(self):` 之前插入：

```python
    def test_from_content_type_x_json(self):
        mappings = [
            ('application/x-json', TextResponse),
            ('application/x-json; charset=latin-1', TextResponse),
        ]
        for source, cls in mappings:
            retcls = responsetypes.from_content_type(source)
            assert retcls is cls, "%s ==> %s != %s" % (source, retcls, cls)
```

写法照搬同文件 `test_from_content_type` 的映射表风格。两个实例都是题面一般表述（MIME 类型为 `application/x-json`）的直接实例，不涉及 header 路径（那条路径在 py3 下本来就坏，不属于本题）。`from scrapy.http import ... Headers` 这一行在删掉两个方法后不再被用到，保留不动（无害，减少 edit）。

**(2) `test_2.py`，一条 `hidden_test_file_add`**：内容逐字等于公开文件 `PUB/worktree/tests/test_http_headers.py`（157 行，`HeadersTest` 17 个方法，sha256 `686d5738fd76…`）。文件名沿用 R2E 的 `test_N.py` 约定；键是 `HeadersTest.<方法名>`，与 `ResponseTypesTest` 不撞键。

完整修订条目见 `OUT/revision_draft.json` 的 `revisions`（与试跑所用 `OUT/trials/inputs/draft_9a15_final_v2.json` 逐字相同，已用脚本比对）。

## 3. 修订后期望映射（7 键 → 23 键）

| 变化 | 键 | 状态 |
| --- | --- | --- |
| 删除 | `ResponseTypesTest.test_from_args`、`ResponseTypesTest.test_from_headers` | 原为 FAILED |
| 不变 | `ResponseTypesTest.test_custom_mime_types_loaded`、`test_from_body`、`test_from_content_disposition`、`test_from_content_type`、`test_from_filename` | PASSED |
| 新增（R-c-2） | `ResponseTypesTest.test_from_content_type_x_json` | PASSED |
| 新增（R-c-1） | `HeadersTest.` + `test_basics`、`test_single_value`、`test_multivalue`、`test_encode_utf8`、`test_encode_latin1`、`test_encode_multiple`、`test_delete_and_contains`、`test_setdefault`、`test_iterables`、`test_update`、`test_copy`、`test_appendlist`、`test_setlist`、`test_setlistdefault`、`test_none_value`、`test_int_value`、`test_invalid_value`（17 个） | PASSED |

期望里不再有非 PASSED 键。新增键的状态不是抄 gold 输出：`HeadersTest` 是公开测试在 base 上的既有结果（noop、gold、P4 下都通过），`test_from_content_type_x_json` 来自题面一般表述。

## 4. 验收计划与试跑结果

镜像 `sha256:1de7669dacf64c8a067200844da065064e3f840d4afb009bab4361b2c2891af8`，配方 `r2e_derive_v1+sysconfig_v1`；每行一次试跑（`trial_grade.py`，结果文件在 `OUT/trials/`）。

| 材料 | 候选（补丁，sha256 前缀） | 应得 | 实得 | 不符的键 | 结果文件 |
| --- | --- | --- | --- | --- | --- |
| 当前 | noop | 0 | 0 | `test_from_content_type` | `cur_noop.json` |
| 当前 | gold（`gold.patch`，dcb13cf5） | 1 | 1 | — | `cur_gold.json` |
| 当前 | P4 更完整修复（`runs/r2e_env_repair_20260924/p4/overfix/scrapy__9a15….diff`，81cedada） | 误拒 | 0 | 两死键 FAILED→PASSED | `cur_p4_overfix.json` |
| 当前 | 逐字特判（`OUT/cands/scrapy_9a15_literal_hardcode.patch`，b488c890） | 漏判 | 1 | — | `cur_literal_hardcode.json` |
| 中间稿：只做 R-a | gold | 1 | 1（5/5，无 missing / extra） | — | `pure_gold.json` |
| 中间稿：只做 R-a | `bad_headers_str`（`OUT/cands/scrapy_9a15_bad_headers_str.patch`，f15878d7） | 应为 0 | **1** | — | `pure_bad_headers_str.json` |
| 中间稿：R-a + R-c-1 | gold / noop / P4 / `bad_headers_str` | 1 / 0 / 1 / 0 | 1 / 0 / 1 / 0 | noop：`test_from_content_type`；bad：`HeadersTest` 13 键 | `final_gold.json`、`final_gold_r2.json`、`final_noop.json`、`final_p4_overfix.json`、`final_bad_headers_str.json` |
| **定稿** | gold（正对照） | 1 | 1（23/23，两次） | — | `v2_gold.json`、`v2_gold_r2.json` |
| **定稿** | noop | 0 | 0 | `test_from_content_type`、`test_from_content_type_x_json` | `v2_noop.json` |
| **定稿** | P4 更完整修复（被纠正的误判） | 1 | 1 | — | `v2_p4_overfix.json` |
| **定稿** | `bad_headers_str`（已知错误候选） | 0 | 0 | `HeadersTest` 的 `test_appendlist`、`test_basics`、`test_encode_latin1`、`test_encode_multiple`、`test_encode_utf8`、`test_int_value`、`test_iterables`、`test_multivalue`、`test_setdefault`、`test_setlist`、`test_setlistdefault`、`test_single_value`、`test_update` | `v2_bad_headers_str.json` |
| **定稿** | 逐字特判（退化候选） | 0 | 0 | `test_from_content_type_x_json` | `v2_literal_hardcode.json` |

对照 v1 §5 的 R-a / R-c 验收：正对照 1、noop 0 ✓；要纠正的误判（P4）已纠正 ✓；已知相关错误候选（`bad_headers_str`、逐字特判）为 0 ✓；**没有 unexpected 键**：定稿与中间稿所有行 `missing` / `extra` 都为空 ✓。

候选说明：`bad_headers_str` 按 Codex 首批复核 B2 的描述写成补丁（gold 那一行加 `scrapy/http/headers.py:26` 改为 `.decode(self.encoding)`）；逐字特判是 §4 第 3 步式的退化候选（只凭 gold 所在文件写出的与输入无关的特判），违反的公开要求是 `user_prompt.txt:18`，用 `application/x-json` 这个输入即可看出。两者都只改库源码。

## 5. 正对照

默认 gold，修订后仍为 1（两次），不需要替代解。gold 只加一行表项，天然满足非示例实例和 `Headers` 契约。

## 6. 修订后仍受保护的公开要求与未覆盖范围

- **核心要求**（`user_prompt.txt:17-18`）：`test_from_content_type`（题面原例）+ `test_from_content_type_x_json`（两个非示例实例）直接断言。
- **既有行为**：html / xml / xhtml / wap / octet-stream 映射，`from_filename`、`from_content_disposition`（str 输入）、`from_body`、自带 mime.types 加载；`Headers` 在 py3 下存取 bytes 的契约（17 键）。
- **仍未覆盖（登记，不在本次修订内）**：header 路径（`from_headers` / `from_args`、`content_encoding → Response`）没有测试——删掉的两个死键本来也保护不了它；`application/json` 等其余表项不变（旧 K1′，T3，低）；模型会不会被公开测试里的两个 `TypeError` 引去改 header 路径，要看真实轨迹。

## 7. 版本记录

- **父版本**：来源材料，无修订（`material_revisions: []`）；期望 `sha256:2fefa8a5287028e9c4f3b428fa82308f457794887fc8e98a78ded9c9be420f6b`；隐藏测试树 `sha256:a3f0f6e4f494ed95a249c323f144f83442f1f484bdaeedd52b130d46ca9b4bf5`；`test_1.py` `sha256:5a84fa9f7508ec7fee0640bcb2886b34842d32243608e95778bcb8bf2e8ee74f`。
- **新版本**：`test_1.py` 修订后 `sha256:bb261b3d19e1dbf70cc8e02946de657101c0fa6c852a3a864408f9bbe54be5aa`；新增 `test_2.py` `sha256:686d5738fd76fa95e1b0dcab620aff3530f79c30a2dc88223986d4187f915116`；期望 23 键（`OUT/trials/inputs/expected_9a15_final_v2.json`）。
- **触发反例**：P4（误拒）、`bad_headers_str`（只做 R-a 后的漏判）、逐字特判（示例拟合）。补丁与结果见 §4。
- 中间稿（`draft_9a15_pure.json`、`draft_9a15_final.json`）及其期望保存在 `OUT/trials/inputs/`，便于复核拆分方案。

## 8. 交协调者确认的事项（不需要用户决定）

1. **是否接受在 R-a 之外合并 R-c-1、R-c-2。** 我的建议是接受：两者都在 v1 §5 模板内（复用公开旧测试；补有公开依据的非示例实例），没有扩大需求，也没有为 gold 放宽要求。拆分方式：
   - 只要 R-a：用 `trials/inputs/draft_9a15_pure.json` + `expected_9a15_pure.json`（gold 5/5 已试跑）。但按 v1 §4 第 4 步（`bad_headers_str` 得 1 且破坏有文档、公开测试保护的 `Headers` 契约）和第 2 步（逐字特判得 1），本题仍有未处理的 S1，不能按 README §3 进探针。
   - R-a + R-c-1：`draft_9a15_final.json`（已试跑，见 §4 中间稿行），但第 2 步的 S1 仍在。
2. **R-c-1 用整份公开文件还是只取 `test_single_value`。** 我选整份：来源可逐字核对，17 键在 noop / gold / P4 下全部通过，都是纯单元测试、与时序无关。Codex B2 的最低要求是 `test_single_value`；若协调者要更窄，只保留该方法即可，`bad_headers_str` 仍会在该键上失败（它在定稿里命中 13 键，包含 `test_single_value`）。
3. v1 §11 把本题列为「R-a 后为训练候选」，没有记第 2 步的示例拟合；这是本次新发现，建议在题卡与批次汇总里补记。

## 9. 试跑与正式评分的差别

`trial_grade.py` 不做基线重建比对、不核隐藏测试树与入口摘要，权限布置简化为整个 `/testbed` 归评分用户（见该脚本文件头）。所以以上只是修订方向的依据；定稿后需要协调者写正式修订单（`test_1.py` 的三处 edits 应放在同一条 `hidden_test_text_replace` 里，另一条 `hidden_test_file_add`；期望用 `expected_file_replace` 并逐键声明 `removed` 2 个、`added` 18 个），重建派生镜像材料步骤，再用正式评分复验 noop / gold / P4 / `bad_headers_str` / 逐字特判，并交 Codex 复核。
