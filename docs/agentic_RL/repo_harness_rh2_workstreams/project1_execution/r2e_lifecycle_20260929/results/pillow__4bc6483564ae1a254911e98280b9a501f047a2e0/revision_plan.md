# pillow 4bc64835：R-c 修订方案（补 mode "1" 反相结果与"不改调用者的图"断言）

2026-09-29 08:32（+08，本机时钟）· 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 一轮完成，试跑验收 6 个候选全部与预期一致（试跑工具，不是正式评分）；当前材料上的 noop / gold 环境对照也一致。** 本轮不需要用户决定。§7 有一项可选的用户决定（非规范取值是否按 1-bit 语义反相），不阻塞本轮。待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，475 行）；`HT'` = 修订后的 `test_1.py`（491 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/pillow_4bc6/`；`DEV` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。两个 S1 同根：隐藏测试不检查 `invert` 对 mode "1" 的输出和副作用。所以用同一个新测试修，依据逐项分写。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c-1 | T2a：核心要求"真正反相"没有断言，HT:66 只有一行 `ImageOps.invert(hopper("1"))`，不抛错就过。T2b：退化候选 D1（mode "1" 返回 `image.copy()`）得 1 | D1 正式评分 1.0，24/24（`INV/ledger_D1.jsonl:1`） | `card.md` 结论与问题第 1 条；`review.md` §1 第 1–2 行 |
| R-c-2 | v1 §4 第 4 步：得 1 的候选破坏有文档、常用的公开行为。W1 反相结果正确，但原地改掉了调用者的图 | W1 正式评分 1.0，24/24（`INV/ledger_W1.jsonl:1`） | `card.md` 问题第 2 条；`review.md` §2.1 |

**本轮不做**：
- 题面原例（非规范取值）的断言：复核已撤回初判的 R-c#2，改为可选的用户决定项（§7）；
- `card.md` 附录 A.3 的 L/RGB 反相值断言（T3，S2）：协调者定的是 24 → 25 键，本轮不加，见 §6。

## 2. 公开依据

### 2.1 R-c-1：规范 1-bit 图被真正反相，模式与尺寸不变

- **题面**：
  - 标题 `PUB/user_prompt.txt:3`；描述 `:6` 说报错使反相无法在二值图上进行；
  - Expected `:20`："The `invert` function should successfully invert the binary image without raising an error"。
  - 核心要求是"成功反相"，不只是"不报错"。
- **docstring**：`W/src/PIL/ImageOps.py:520` "Invert (negate) the image."
- **1-bit 约定**：规范取值是 0 = 黑、255 = 白，反相就是黑白互换。
  - 文档：`W/docs/handbook/concepts.rst:28-29`（1-bit 像素取值 0–1）、`:32`（mode "1" 每像素存一个字节）；
  - 源码：`W/src/libImaging/Pack.c:85`（"bilevel (black is 0)"）、`W/src/libImaging/Unpack.c:112`（"white is non-zero"）、`W/src/libImaging/Convert.c:58-61`（转 L 时非零 → 255）。
- **输入选 `hopper("1")`**：
  - 它由 RGB 抖动转换得到，只含 0/255（`W/src/libImaging/Convert.c:1484, 1515`），是规范图；
  - 它不是题面字面值（`PUB/user_prompt.txt:13` 的 `Image.new("1", (128, 128), color=1)`），满足 v1 §4 第 2 步"非示例实例"的要求；
  - 原测试 HT:66 已经在用这个输入。
- **期望怎么来**：
  - oracle 不调用 `ImageOps.invert`，而是对输入的 L 视图逐字节取 `255 - v`（HT':482-484），也就是规范图的黑白互换；
  - 比较放在 `out.convert("L")` 之后，实现输出 0/255 还是 0/1 结果一样（转 L 时非零即 255，`Convert.c:60`）；
  - 期望由输入与公开语义推出，不是 gold 的输出。
- **`out.mode == "1"`**（HT':488）：
  - `Image.point` 的输出模式默认与输入相同（`W/src/PIL/Image.py:1696`）；
  - `invert` 对 L/RGB 一直保持模式（`W/src/PIL/ImageOps.py:53-56`）；
  - 没看过 gold 与隐藏测试的公开读者独立推出了同一要求（`public_read.md:26` 的 R3；`:73` 把"对 "1" 输入返回 "L" 图"列为有风险的做法）；
  - 复核建议保留（`review.md` §3）。
- **`out.size == im.size`**（HT':489）：依据同上；`point` 按输入尺寸建新图（`W/src/libImaging/Point.c:155`）。

### 2.2 R-c-2：不修改调用者的图

按强弱排列。第 1 条是复核补的、最直接的依据（`review.md` §2.1）。

1. **`invert` 自己对 L/RGB 的既有行为**：
   - 调用链：`_lut` → `image.point(lut)`（`W/src/PIL/ImageOps.py:53-56, 525-528`）→ `return self._new(self.im.point(lut, mode))`（`W/src/PIL/Image.py:1723`）→ C 层 `imOut = ImagingNew(...)`（`W/src/libImaging/Point.c:155`）。
   - 所以 `invert` 一向返回新图、不改输入。把 mode "1" 纳入同一个函数，应沿用同一约定。
2. **公开读者独立推出**：R3 "返回新图，不修改输入"（`public_read.md:26`），并把"原地修改输入图"列为不宜接受的做法（`:74`）。
3. **文档惯例**：
   - `Image.thumbnail` 专门注明会原地修改（"modifies the Image object in place"），并建议先 `copy()`（`W/src/PIL/Image.py:2418-2421`）。可见原地修改是需要特别注明的例外；
   - `exif_transpose` 即使不做变换也 "return a copy of the image"（`W/src/PIL/ImageOps.py:575-576`）。
4. **同一功能区的做法**：TIFF 保存对 mode "1" 先 `im.copy()` 再逐像素改（`W/src/PIL/TiffImagePlugin.py:1668`），对 "L" 则把用户的图直接交给 `ImageOps.invert`（`:1675`）。

**误拒风险**：看不到。
- gold、A1、A2、`ImageChops.invert` 路线、"转 L 反相再转回"路线都返回新图；
- `hopper("1")` 返回缓存图的副本（`PRIV/hidden_tests/helper.py:249-258`），W1 这类原地修改不会串到其它测试。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即 `HT`。本题 `revisions.json` 为空，没有已批准的材料修订，不存在同目标冲突。
- **草案条目**：一条 `hidden_test_text_replace`，一处 edit，全文见 `revision_draft.json` 的 `revisions`。
  - `old` = `HT:474-475` 两行（`    )  # single color 10 cutoff` 与 `    assert_image_equal(img, out)`，各带换行），全文恰好出现一次。只用最后一行不行：`    assert_image_equal(img, out)` 在 HT:458 与 HT:475 各出现一次。
  - `new` = `old` + 两个空行 + 下面的新测试，追加在文件末尾（HT' 476–491）。
  - 文件里都是模块级测试函数，新键没有类名前缀。
- **新测试**（`HT':478-491`，即 `card.md` 附录 A.1 原文）：

```python
def test_invert_mode_1():
    # canonical 0/255 bilevel image, not the issue's literal example
    im = hopper("1")
    original = im.copy()
    expected = Image.frombytes(
        "L", im.size, bytes(255 - v for v in im.convert("L").tobytes())
    )

    out = ImageOps.invert(im)

    assert out.mode == "1"
    assert out.size == im.size
    assert_image_equal(out.convert("L"), expected)
    assert_image_equal(im, original)  # the caller's image is left untouched
```

- **设计说明**：
  - 只用 `HT:3-11` 已导入的 `Image`、`ImageOps`、`hopper`、`assert_image_equal`，不新增依赖；
  - 没有时间、随机、网络或写文件，结果确定；
  - `assert_image_equal` 先比模式、尺寸，再比 `tobytes()`（`PRIV/hidden_tests/helper.py:87-98`）；
  - 调用前先存快照 `original`（HT':481），最后一行才比较输入，所以"输出对但改了输入"（W1）会单独在 HT':491 失败。
- **刻意不测**：
  - 输出的原始字节是 0/255 还是 0/1；
  - 题面原例与其它非规范取值（§6、§7）；
  - L/RGB 的反相值（T3）；
  - 其它共用 `_lut` 的函数是否接受 "1"（公开读者的 R9）；
  - 其它模式报什么错（R7）。

## 4. 期望映射逐键变化

- **原 24 键不变**：全部 PASSED。
- **新增 1 键**：`test_invert_mode_1`: `PASSED`。
  - 键形沿用源文件的 ANSI 写法 `"\u001b[1mtest_invert_mode_1\u001b[0m"`，来源是 `W/setup.cfg:67` 的 `--color=yes`；
  - 评分两侧用同一函数去色（`rh2/src/repoharness2/envpack/r2e_parsers.py` 的 `normalize_status_map`）。
- **合计 25 键**，完整映射见 `revision_draft.json` 的 `expected_after`。正式修订单的 expected 部分：`added` 为这一键，`changed`、`removed` 为空。
- **期望从哪里来**：新键的 PASSED 是满足 §2 公开要求的实现应有的结果；gold 通过是验证结果，不是依据。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（HT，475 行） | `016c2b06…` |
  | 父版本 `expected_output.json`（24 键） | `d8bc5a2b…` |
  | 父版本隐藏测试树 | `7e15b739…`，`material_revisions` 为空 |
  | 修订后 `test_1.py`（HT'，491 行） | `9bdba0cc…` |
  | 修订后期望映射（25 键；`json.dumps(indent=4)`、无尾换行，与父版本同格式） | `b2a68136…` |
  | 试跑用 `draft.json` | `0073c532…` |

  - 父版本三项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:41` 一致。
  - 修订后两项与主审 `card.md` 附录 A.1–A.2、复核 `review.md` §1 第 9 行的本地重建一致。
  - 全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- 派生镜像 `sha256:d6de4045…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV` 下四本正式账本的 `image_id_actual` 相同。
- 补丁校验：
  - 5 个补丁（gold 与 D1、W1、A1、A2）先在仓库外的 base 副本上 `git apply --check -v` 通过，输出都列出了 `src/PIL/ImageOps.py`；
  - 副本的 `ImageOps.py` blob 是 `c6201d8`，与补丁 index 行一致；
  - 四个候选补丁与协调者正式评分所用的 `INV/pillow_4bc6_*.patch` 逐字节相同。
- 每次试跑 `RH2_APPLY_RC=0`；修订草案下都报 `RH2_TRIAL_EDITS_APPLIED=1`；每次 25 键全部解析，没有 missing / extra。
- 08:16–08:26（+08）跑完，同时最多 2 个；单次墙钟 46–62 s，其中测试 1.9–2.3 s。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差 `test_sanity`（FAILED，HT:66 `OSError: not supported for this image mode`） | `trials/env_noop_current.json` |
| gold | 1：24/24 | `trials/env_gold_current.json` |
| D1、W1、A1、A2 | 都是 1.0，24/24，`included_paths=['src/PIL/ImageOps.py']` | `INV/ledger_{D1,W1,A1,A2}.jsonl:1`（协调者正式评分） |

### 5.2 修订草案下的验收

结果文件为 `trials/rev_<候选>.json`。

| 候选 | 补丁 | 角色 | 应得 | 应失败的键与行 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，25/25 | 1 |
| noop | 无 | 未修复基线 | 0 | `test_sanity`（HT:66）、`test_invert_mode_1`（HT':486），都是 OSError | 0，恰好这 2 键、这 2 行 | 0 |
| D1 | `cands/pillow_4bc6_D1.patch` | 第 3 步退化候选，R-c-1 的触发反例 | 0 | `test_invert_mode_1`，HT':490（输出等于输入） | 0，恰好此键；HT':490 `AssertionError: got different content` | **1**（正式） |
| W1 | `cands/pillow_4bc6_W1.patch` | 第 4 步错误候选，R-c-2 的触发反例 | 0 | `test_invert_mode_1`，HT':491（输入被改） | 0，恰好此键；HT':491，信息同上；HT':488-490 已通过 | **1**（正式） |
| A1 | `cands/pillow_4bc6_A1.patch` | 合理替代解（先按 1-bit 值归一再反相） | 1 | — | 1，25/25 | 1（正式） |
| A2 | `cands/pillow_4bc6_A2.patch` | 合理替代解（`_lut` 放行 "1"），复核要求本轮实跑 | 1 | — | 1，25/25 | 1（正式） |

**判读**：
- **正对照 1、noop 0**：成立。
  - gold 本身满足 §2 的公开要求：规范输入上逐位反相、模式为 "1"、不改输入（`INV/pcheck_canon_gold.json`；`DEV/private_control.json` 的 `check_mode1_invert_canonical`），L/RGB 反相结果不变（同文件 `check_l_rgb_unchanged`）。
  - gold 对非规范取值的行为属于 §6 登记的读法分歧，新测试不涉及。
- **误判已纠正**：
  - D1、W1 在当前材料正式评分都得 1，修订后都得 0，而且各自只在新键、在预定的那一行失败。
  - W1 通过了模式、尺寸、像素三项（HT':488-490），只被 HT':491 挡住，说明"输入不变"这一行不是多余的。
- **没有误拒**：A1、A2 仍得 1。A2 从复核时的"静态推断"变成了试跑证据。
- **旧键不受影响**：
  - noop、gold 的旧 24 键状态，修订前后逐键相同（两份试跑结果逐键比对）；
  - D1、W1、A1、A2 的旧 24 键也全部与期望一致，`status_diff` 只含新键。
- **未跑**（沿用 `review.md` §3 的静态判断，不改变结论）：
  - 应得 1：`ImageChops.invert`、"转 L 反相再转回"、输出 0/1 的实现；
  - 应得 0：输出 mode "L"、固定全黑或全白、只反相一部分。

## 6. 修订后仍受保护的公开要求、未覆盖范围与剩余事项

**受保护的公开要求**：
- **mode "1" 不再报错**：`test_sanity`（HT:66）与 `test_invert_mode_1`（HT':486）。
- **规范 1-bit 图被真正反相**：像素 HT':490，模式 "1" HT':488，尺寸 HT':489。
- **不改调用者的图**：HT':491。
- **L/RGB 反相不报错**（HT:67-68，冒烟）；其它 `ImageOps` 函数的回归键不变。

**仍未覆盖，维持登记**：

1. **非规范存储值（G1 / P4，S2）。理由按复核改写**（`review.md` §2.2）：
   - **事实（实测）**：
     - 题面原例 `color=1` 每个像素存为字节 1；
     - gold 把它变成 254，任何按 1-bit 解读的视图（`tobytes`、保存、`convert("L")`）都与输入一样是全白（`DEV/private_control.json` 的 `results.repro_issue_example`：输出原始值 254，`equals all-black: False`，L 极值 (255, 255)）；
     - 按 1-bit 语义看，gold 与 D1 在这个例子上无法区分，所以题面原例本身不适合作"反相正确"的验收实例。
   - **两种读法的依据并不对等**：
     - **"按 1-bit 值取反"**（非零即白，反相后为黑）有**公开文档**支持：1-bit 像素取值 0–1（`W/docs/handbook/concepts.rst:28-29`）。所有输出路径也都把非零当白：打包 `Pack.c:89`，转 L `Convert.c:60`，逻辑运算 `Chops.c:116-128`，以及公开测试 `W/Tests/test_imagechops.py:408-428`（1、128、255 都当作"开"）。
     - **"按存储字节取 `255 - v`"**：依据是实现一致性（L/RGB 的查找表，`ImageOps.py:525-528`）、`ImageChops.invert` 的**实现**（`Negative.c:37` 按位取反）和上游 gold 本身，**没有文档依据**。
     - **更正**：主审把 `ImageChops.invert` 当成了文档依据（`analysis_before_history.md:104`、`old_findings_delta.md:60`，原话大意是"文档写 `MAX - image`，对 "1" 也得到 254"）。文档只写 `out = MAX - image`（`W/src/PIL/ImageChops.py:45`），没有规定 mode "1" 的 MAX；按文档的 0–1 取值算，MAX − 1 = 0，结果是黑。254 来自实现，不来自文档。
   - **字节 1 不是罕见输入**：
     - 下面几种常见写法都经过 `getink`：`Image.new("1", size, 1)`（`W/src/PIL/Image.py:2785` → `core.fill`）、`ImageDraw` 的 `fill=1` / `outline=1`（`W/src/PIL/ImageDraw.py:113, 119` → `draw_ink` → `W/src/_imaging.c:2783`）、`putpixel(xy, 1)`（`_imaging.c:1761`）；
     - `getink` 对单波段 8 位图只做 `CLIP8`，不对 mode "1" 归一（`_imaging.c:537`），所以按原始字节 1 存储；
     - 因此这个缺口应写成："用户用这些常见写法自建的 1-bit 图（例如掩膜），在 gold 式实现下反相后看起来不变；评分对此保持中立"，而不是"罕见的边缘值"。
   - **仍然不断言**，理由：
     - 断言 1-bit 读法，会让上游 gold 和最自然的几种实现（gold、A2、`ImageChops.invert`）判 0，而 Pillow 自己的代码对这类值也不一致：TIFF 反相循环（`W/src/PIL/TiffImagePlugin.py:1672`）同样让字节 1 保持白；
     - 断言原始值 254，又会反过来拒绝 A1；
     - 两种断言都等于替任务选口径（§7）。

     现行测试与本次 R-c 对两种读法都中立：不产生误拒，也不奖励退化解（D1 已在规范输入上被拒）。在"两种约定都接受"的默认口径下，第 4 步不命中，登记为 G1 / P4、S2。
   - **建议**：
     - 撰写准入卡时，把 `screening_record.json` 里 `P4-G1-noncanonical-example`（第 101 行起）的 summary 按上面三点改写。本轮没有改动 `screening_record.json` 与 `card.md` 原件；
     - 探针与训练阶段，把"对得 1 的补丁跑一次 `repro_issue_example`"列进 v1 §8 的抽查与事后审计，原始 reward 与语义结果分列。
2. **L/RGB 反相值只有冒烟（T3，S2）**：
   - `card.md` 附录 A.3 的可选键本轮不加（协调者定为 24 → 25 键）；公开命令 `check_l_rgb_unchanged` 可用于事后审计；
   - 以后若补，它在 base 上也通过，是回归键，noop 下也是 PASSED。
3. **题面未涉及、测试中立的两项**：
   - 其它共用 `_lut` 的函数是否接受 "1"（R9）。A2 的副作用就是放行这几个函数；25 键里没有期望它们对 "1" 抛错的键；
   - 其它模式报什么错（R7）。
4. **TIFF photometric 路径**：不在隐藏测试里；公开测试 `W/Tests/test_file_tiff.py:483-490` 覆盖，只作开发自查。
5. **X1**：
   - 本题 gold 逐字出现在 pillow `3a61c9e9`、`f9d3ee0f`、`a682ceaf` 的初始工作树里（`card.md` 问题第 5 条），这三题的公开 `Tests/test_imageops.py` 也含原冒烟行 `ImageOps.invert(hopper("1"))`；
   - 新测试是新写的：按测试名 grep，`test_invert_mode_1` 在 v3 的 7 个 pillow 公开工作树里都没有出现。
6. **平台面（不属本题）**：devcheck 期间 agent 对 `.venv` 下部分 `__pycache__` 可写（`review.md` §3 末条），归 A 线。

**剩余事项（谁来补）**：
1. **协调者落正式材料**：
   - 把 `revision_draft.json` 的 `revisions` 落为正式修订单（一条 `hidden_test_text_replace`），另加期望修订（`added` 一键）；
   - 重建本题派生镜像（隐藏测试在镜像的 `/rh2_private/r2e_tests` 里）。
2. **协调者跑正式评分**：
   - gold、noop、D1、W1、A1、A2 六项，按 §5.2 判读；
   - 每项核对：25 键严格相等；日志里新键确实执行；`included_paths` 为 `src/PIL/ImageOps.py`；隐藏测试树哈希与修订单一致；
   - 再跑一次 devcheck。
3. **Codex 复核**。
4. **之后重判 v1 用途**（`card.md` 的用途表）：
   - 训练候选要的正面证据（核心断言、noop 0 / 正对照 1、第 2、3 步结果）在正式评分后齐全；
   - 把第 1 条改写后的 S2 一并登记；
   - 留出评测仍受 D3 按仓库划分、"标明版本的自建题"与 X1 的限制。

## 7. 待用户决定（可选，不阻塞本轮）

**问题**：mode "1" 图里的非规范存储值（字节 1–254，例如题面原例 `color=1`），是否也要求按 1-bit 语义反相，即非零当白、反相后为黑？

| | A：不要求（默认） | B：要求（严格口径） |
| --- | --- | --- |
| 测试 | 本轮 R-c 即定稿，对非规范取值保持中立 | 再补非规范取值的断言，另起新键，便于把"只错这一点"与其它错误分开 |
| 正对照 | gold | gold 在新键上失败；按 D4 改用 A1，并记录 gold 的失败 |
| 哪些实现得 1 | gold、A1、A2、`ImageChops.invert` 路线、"转 L 再转回"路线 | 只有先把非零归一再反相的实现（A1、"转 L 再转回"）；gold、A2、`ImageChops.invert`、仿 TIFF 循环的实现都得 0 |
| 与上游的关系 | 与上游 Pillow 发布的行为一致 | 与上游修复的行为相反。题目本来就只能作"标明版本的自建题"，但正对照不再是原修复 |
| 风险 | 训练可能学会 gold 式实现：用 `color=1`、`fill=1`、`putpixel(…, 1)` 建的图，反相后看起来不变，评分不罚。已登记为 S2，列入抽查与事后审计 | 惩罚上游认可、也最常见的写法；Pillow 自己的 TIFF 反相对字节 1 也不按 1-bit 处理，题目会要求一个仓库本身都没贯彻的约定 |
| 规则归属与成本 | 无额外成本 | 在两种读法里替任务选口径，属 v1 §5 的"改变任务目标"，在模板外。落实步骤：先在 A1、A2 下各跑一次 `repro_issue_example` 留证（预期 A1 原始值 0、全黑；A2 为 254、仍白）；再做一轮修订，试跑与正式评分约 6–7 次（gold 应为 0），最后 Codex 复核 |

**建议选 A。**主审与复核都推荐 A，我同意，理由有三：
1. 本题的两个 S1（不检查输出、原地修改）由本轮 R-c 修好，与这个选择无关；
2. B 会把正对照从上游修复换成替代解，并拒绝最自然的写法，而拒绝的依据是 Pillow 自己都没贯彻的约定；
3. A 的风险已登记，可以在抽查和事后审计里看到。

**支持 B 的理由也成立**：题面原例本身就是非规范取值，公开文档也偏向 1-bit 读法。如果用户更看重"题面原例必须看得出反相"，选 B 有依据。这是取舍，不是对错。用户不决定时维持 A，不影响本题后续推进。

## 8. 边界与交接

- **只做 R-c**：
  - 没有改题面，没有删键，没有放宽已有断言；
  - 没有复制 gold 输出作期望；
  - 没有替任务选择非规范取值的读法（§7 交用户）。
- **没写**：`s2_r2e` 下的正式修订单与 pins、生产代码；也没有改 `card.md`、`screening_record.json` 等原件。
- **远端操作**：
  - 建了目录 `/work/r2e/trials/lc_pillow_4bc6/4bc64835/`；
  - 上传 7 个文件：`draft.json`、`expected_after.json`、`gold.patch` 与 4 个候选补丁；
  - 跑了 8 次 `trial_grade.py`，同时最多 2 个；
  - 取回 8 份结果到 `trials/`；
  - 没有构建、删除，也没有动其它目录。
- **本地**：只在本代理的 scratchpad 里生成草案、算哈希、做 `ast` / `py_compile` 语法检查，以及在仓库外副本上 `git apply --check`。
