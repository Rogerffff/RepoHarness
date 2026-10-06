# pillow 4bc64835 题卡：让 `ImageOps.invert` 支持 mode "1"

私有主审定稿，2026-09-29 07:42 +08。

- 材料：静态筛查 v3，无材料修订；协调者确认本题 v3–v9 材料相同。
- 环境：新机派生镜像 `r2e_derive_v1+sysconfig_v1`，image `d6de4045…`。
- 前稿与历史对照：`analysis_before_history.md`、`old_findings_delta.md`。
- 路径缩写：
  - `LIFE/` = `runs/r2e_lifecycle_20260929/`；`INV/` = `LIFE/inv/pillow_4bc6/`；`DEV/` = `LIFE/devcheck_rev/unrev/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`
  - `PRIV/`、`wt/` 分别是 `runs/r2e_static_prep_20260924/v3/` 下本题的私有包和公开工作树。

## 结论

- **处置**：`needs_repair`（scope `static_review`），严重度 **S1**。
- **问题**：隐藏测试对本题只有一行 `ImageOps.invert(hopper("1"))`，只要不抛错就通过，不检查输出，也不检查副作用。
  - 退化候选 D1（对 mode "1" 原样返回副本）正式评分 **1.0**。
  - W1（结果对，但原地改掉调用者的图）正式评分 **1.0**。
- **环境与开发条件**：新机实测无阻塞（devcheck 8/8，R2E 预检 3/3；noop 0 / gold 1）。
- **修订是否必做**：
  - **训练用途必做**：走 R-c，补一个非题面示例的反相结果断言，加一条输入不变断言。gold 在新断言下按实测行为会通过，正对照用 gold 即可，不需要 D4。
  - 问题定位不需要修订。能力比较可以在预登记事后审计下先用。

| v1 用途 | 结论 | 差什么 / 依据 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 预登记事后审计：对每个得 1 的补丁跑公开命令 `check_mode1_invert_canonical`，原始 reward 与审计结果分列；或者直接用 R-c 后版本 |
| 训练候选 | no | 未处理的 S1。R-c 验收通过、Codex 复核后重评 |
| 留出评测候选 | no | 同上；另有同仓跨题包含关系（X1），修订后只能作"标明版本的自建题" |

## 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| mode "1" 不再抛 `OSError` | 题面 `user_prompt.txt:3-6, 19-26` | `test_sanity`，`test_1.py:66`，冒烟 | 覆盖 | noop 在 `ImageOps.py:58` FAILED（3 次）；gold PASSED（3 次） |
| 真正反相（核心要求） | 题面 L20；docstring `ImageOps.py:520` | 无 | **缺失（T2a）** | D1 1.0；私有检查显示 D1 的输出等于输入 |
| 不改调用者的图 | 操作返回新图、原地修改须注明（`Image.py:2418-2421`、`ImageOps.py:575-576`）；TIFF 调用方直接传入用户的图（`TiffImagePlugin.py:1666-1675`） | 无 | **缺失** | W1 1.0；私有检查显示输入被改 |
| L/RGB 反相值不变 | 旧行为 `255 - v` | 冒烟 | 部分（T3） | 公开命令 `check_l_rgb_unchanged` 在 noop 与 gold 下都通过 |
| 题面原例 `color=1` 的输出 | 两种读法（按字节取反，或按 1-bit 值取反） | 无 | 不宜断言 | gold 实测：原始值 254，按 1-bit 语义仍全白 |

## 八方面（已查 / 未查）

- **公开需求**：已读题面、提示、docstring 与文档。模型实际收到的完整任务消息仍未捕获（devcheck 用的是专用提示）。
- **材料与初态**：base blob 与 gold 前像一致；隐藏测试树 `7e15b739…` 在新旧日志中一致；题面原例在解题身份下可复现。
- **测试强度**：`test_1.py` 与 `helper.py` 逐行读完。除第 66 行外，其余都是公开旧测试的原文。
- **误拒合理解**：没有。替代解 A1、A2 均 1.0。
- **回归与 gold**：gold 只改 1 行，L/RGB 不受影响。gold 对原例的输出属于读法分歧，只登记。
- **开发条件**：解题身份下 PIL 从 `/testbed/src/PIL` 导入，编译扩展在树内；无 pip；不需要构建。
- **交付与评分**：投影包含 `src/PIL/ImageOps.py`；隐藏 helper 由 grader 恢复；没有撞键；没有期望非 PASSED 键。
- **题目关系**：已逐条核对两份跨题比对。
- **未查**：真实模型求解、经 adapter 的链路、正式链出网面（A 线）、同题在新镜像上与独立 runner 的对账。

## 问题（v1 编号、严重度与证据层次）

1. **T2（T2a + T2b），S1**。核心的反相结果没有断言；D1 得 1.0。证据为当前 CPU：正式评分、日志中 `test_sanity` PASSED，以及私有行为检查。
2. **第 4 步命中，S1，与第 1 条同根**。W1 得 1.0，破坏了"不改调用者输入"这一有文档、常用的行为。证据同上。
3. **P4 / G1 登记，S2**。题面示例用非规范存储值 1；gold 输出 254，按 1-bit 语义看不出反相。测试和修订草案都不对它断言。证据为 devcheck 的私有 gold 对照。
4. **T3 登记，S2**。L/RGB 的反相值只做冒烟检查。可在同一轮 R-c 顺带补（附录 A.3）。
5. **X1 登记**。
   - 本题 gold 逐字出现在 pillow `3a61c9e9`、`f9d3ee0f`、`a682ceaf` 的初始工作树里。
   - 本题初态含 `2b061b68`、`2d01f7d0` 的修复，以及三题的新测试。
   - 训练时控制重复采样，留出评测按仓库划分。
6. **环境：无问题**。旧 issue"提示说 pip 可用"已过时，现行提示写 "`pip` may be unavailable"。

## 修订建议：R-c（全文与验收矩阵见附录 A）

- **改动**：在 `hidden_tests/test_1.py` 末尾加 `test_invert_mode_1`，期望映射加 1 个 PASSED 键（24 → 25）。新测试做四件事：
  - 用 `hopper("1")`（规范 0/255，不是题面字面值）作输入；
  - 用不经过 `ImageOps.invert` 的 oracle 核对反相结果；
  - 断言输出为 mode "1" 且尺寸不变；
  - 断言调用者的输入不被修改。
- **刻意不做**：不断言原始字节必须是 0/255，也不对题面原例断言。
- **验收**：gold 1、noop 0、D1 0、W1 0、A1 1。这是按私有行为检查实测结果做的预测，还需要正式评分实跑，再交 Codex 复核。

## 复核与分歧

独立复核的初判由协调者转述，我没有读原文。

- 复核同判 S1（T2a），并预测 D1 得 1，已坐实。
- 复核指出 gold 对原例没有反相。这一事实已由实测确认。本卡把它定为 P4 / G1 登记，理由见 `old_findings_delta.md` §2 第 3 条。这不影响处置与修订内容。
- 若复核坚持判为第 4 步 S1，就转到下面"待用户决定"。

## 待用户决定（可选，不阻塞）

是否要求非规范存储值（题面示例 `color=1`）也按 1-bit 语义反相。这等于在两种有依据的读法里选一种，还会让 gold 失败，超出模板。**建议否**。

## 唯一优先下一步

协调者按附录 A 实施 R-c：按现有修订单机制改隐藏测试文本与期望映射，重建本题派生镜像，跑验收矩阵，然后交 Codex 复核。

## 探针就绪差距

按派发指令，我没有读本批 README §3，下面对照 v1 §2 与本角色卡来写。

- **已满足**：
  - 公开开发路径已实测：devcheck 8/8，`.venv` 激活，CC 2.1.205 经桩端点；
  - 评分条件已实测：新镜像 noop 0 / gold 1，键级与旧机一致；
  - 退化探测已完成（D1）；T1 核对已完成（A1、A2）；
  - 不需要环境修复。
- **未满足**：
  1. S1 未修，所以不能进训练。由协调者实施 R-c 并验收，Codex 复核。
  2. 修订前若进基座探针，需要预登记事后审计与计分口径（见上表"能力比较"一行）。由协调者登记。
  3. 独立复核的终稿待出，由复核者负责。
  4. 各题共同的未验项：模型实际收到的完整消息、经 Qwen adapter 的链路、真实模型求解。由 A 线和探针阶段补。

---

## 附录 A：R-c 草案（可直接实施）

**A.1 隐藏测试改动**

改的是 `PRIV/hidden_tests/test_1.py`，即评分时的 `r2e_tests/test_1.py`。原 sha256 为 `016c2b06…`（与评分面一致），改后为 `9bdba0cc…`。

```diff
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -473,3 +473,19 @@
         img, cutoff=10, preserve_tone=True
     )  # single color 10 cutoff
     assert_image_equal(img, out)
+
+
+def test_invert_mode_1():
+    # canonical 0/255 bilevel image, not the issue's literal example
+    im = hopper("1")
+    original = im.copy()
+    expected = Image.frombytes(
+        "L", im.size, bytes(255 - v for v in im.convert("L").tobytes())
+    )
+
+    out = ImageOps.invert(im)
+
+    assert out.mode == "1"
+    assert out.size == im.size
+    assert_image_equal(out.convert("L"), expected)
+    assert_image_equal(im, original)  # the caller's image is left untouched
```

所需名字（`Image`、`ImageOps`、`hopper`、`assert_image_equal`）都已在 `test_1.py:3-11` 导入。我在本地只做了语法解析，没有运行。

**A.2 期望映射改动**

在 `PRIV/expected_output.json` 末尾加一键，沿用 ANSI 键形：

```json
"\u001b[1mtest_invert_mode_1\u001b[0m": "PASSED"
```

原文件能用 `json.dumps(indent=4)` 逐字节重现，原 sha256 为 `d8bc5a2b…`；加键后为 25 键，sha256 为 `b2a68136…`。修订单里要逐键声明"新增 1 键"，保证键集严格相等。

另一种写法：把 A.1 的断言并入 `test_sanity`，放在第 66 行之后。这样键集不变，期望映射不用改，但失败时不如单独的键好定位。

**A.3 可选的 T3 项**（不影响本题处置）

```python
def test_invert_l_rgb_values():
    for mode in ("L", "RGB"):
        im = hopper(mode)
        out = ImageOps.invert(im)
        assert out.mode == mode
        assert out.tobytes() == bytes(255 - v for v in im.tobytes())
```

期望映射相应加一个 PASSED 键。现有候选在这一键上都会通过（公开命令 `check_l_rgb_unchanged` 在 noop 与 gold 下都通过）。

**A.4 公开依据**

- 核心要求：题面 L20 "successfully invert the binary image"；docstring `wt/src/PIL/ImageOps.py:520`。
- 1-bit 约定：`wt/src/libImaging/Pack.c:85`、`Convert.c:58-61`、`docs/handbook/concepts.rst:28-32`。
- 输入不变：见"关键映射"第 3 行。
- `out.mode == "1"` 是推断：`Image.point` 的输出模式默认与输入相同（`wt/src/PIL/Image.py:1696`），L/RGB 反相也保持模式。复核若认为依据不足，删掉这一行，其余不变。

**A.5 验收矩阵**

| 候选 | 预测 reward | 预测新键 | 预测依据（已实跑的私有检查，同一镜像） |
| --- | --- | --- | --- |
| gold（正对照） | 1 | PASSED | `INV/pcheck_canon_gold.json`：规范图逐位反相、模式为 "1"、输入不变 |
| noop | 0 | FAILED（OSError） | `INV/pcheck_canon_none.json`；devcheck 中 noop 的输出 |
| D1（触发反例，退化） | 0 | FAILED（输出等于输入） | `INV/pcheck_canon_D1.json` 第 8 行 |
| W1（触发反例，改输入） | 0 | FAILED（输入被改） | `INV/pcheck_canon_W1.json` 第 9 行 |
| A1（合理替代解） | 1 | PASSED | `INV/pcheck_canon_A1.json` |
| A2（放宽 `_lut`，可选） | 1 | PASSED | 静态推断：与 gold 同走 `Image.point`；没有做私有检查 |

- 验收时还要核对：键集严格相等（25 键）；正式日志中新键确实执行；保存新旧版本、理由与触发反例（D1、W1）；Codex 复核。
- R-c 后的版本只能作"标明版本的自建题"。

## 附录 B：证据索引

- **新机正式复验**：`LIFE/env_verify/ledger_l1_noop.jsonl:11`（0.0，只有 `test_sanity` 不匹配）；`ledger_l1_gold.jsonl:11`（1.0，24/24）。
- **候选评分**：`INV/ledger_{D1,A1,W1,A2}.jsonl`（均 1.0，`keys_equal=True`，`included_paths=['src/PIL/ImageOps.py']`）；日志 `INV/logs_*/…eval.log`，第 27 行 `test_sanity` PASSED，第 51 行 24 passed。补丁见本目录 `cands/`。
- **私有行为检查**：`INV/pcheck_canon_{none,gold,D1,A1,W1}.json`（root、不联网、一次性容器；不是评分）。
- **devcheck**：`DEV/devcheck.log`；`DEV/orig/captures/*.out`（解题身份）；`DEV/orig/attempt.json`（git_sanitize、激活、CC 版本）；`DEV/private_control.json`（gold 下原例输出 254 / `equals all-black: False` / L 极值 (255, 255)）。
- **旧机与独立 runner**：`PRIV/run_refs.json` 所列 4 行 current 与 M3 两行。
- **历史**：`runs/r2e_static_prep_20260924/v3/history/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/refs.json`。
