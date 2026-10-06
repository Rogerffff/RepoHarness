# pillow `3a61c9e9`：R-c 修订方案（调用前快照、C 层调色板、非恒等重排、GIF）

2026-09-29，修订执行者（单题闭环试行）。**状态：修订草案定稿，一轮试跑验收通过（试跑不是正式评分）；待 Codex 复核；正式修订单与 pins 由协调者落。**

路径约定：`PUB/` = `runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/`，`W/` = `PUB/worktree/`，`PRI/` = `runs/r2e_static_prep_20260924/v3/private/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/`，`C/` = `runs/r2e_actor_20260925/grader_cands/`，`G/` = `runs/r2e_actor_20260925/grader/`，`B2/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/`，`T/` = 本目录 `trials/`。

## 1. 结论

- **模板**：R-c。v1 §11 为本题列的四处缺口在同一轮修完，每处只针对一个窄问题、各有公开依据与触发反例：
  1. **调用前快照**（触发反例 W5）；
  2. **C 层调色板保留 alpha**（W2）；
  3. **非恒等 RGBA 重排**（W3）；
  4. **GIF 保存路径不回归**（W1）。
- **改动**：只动隐藏测试 `r2e_tests/test_1.py`，两条 edit：第 1 条在原目标键 `TestImage.test_remap_palette` 的题面示例段加两处调用前快照与两条断言（缺口 1、2）；第 2 条在它后面新增两个测试函数（缺口 3、4）。期望映射加 2 个 PASSED 键（71 → 73），原有键不变。
- **试跑结果**（本机派生镜像，§8）：gold 1、noop 0；合理替代解 C1 与不补齐变体 A1u 都是 1；W1、W2、W3、W5 由 1 变 0，失败键与预期逐一相符。一轮修订、一轮验收即收敛。

## 2. 四处缺口：公开依据与触发反例

| # | 缺口 | 公开依据 | 触发反例（现材料 71/71 得 1） | 已有行为证据 |
| --- | --- | --- | --- | --- |
| 1 | 原断言在调用**之后**才读原图调色板（`PRI/hidden_tests/test_1.py:614`），就地改坏原图也能过 | 题面 Expected："the palette of the image should remain identical to the original when using an identical mapping"（`PUB/user_prompt.txt:26-27`）——"original" 是示例建立的 RGBA 调色板（`:17`；`putpalette` 随即 `load()`，Python 层为 1024 字节 RGBA，`W/src/PIL/Image.py:1814,836-838`）。base 本身不改原图（`m_im = self.copy()`，`:1905`） | W5：P 分支先 `self.putpalette(self.getpalette("RGB"))` 把调用者的原图改成 RGB，再走 base（`C/pillow_3a61_W5_mutate_source_to_rgb.patch`；`B2/grader_candidates.md:63`） | `G/private_public_b2/p3a61_W5_mutate_source_to_rgb.json`：原图与结果都成了 RGB、768 字节，"相等"只因两边都丢了 alpha |
| 2 | 只比 Python 层字节，C 层调色板（实际渲染用的那份）丢 alpha 也能过 | docstring "Rewrites the image to reorder the palette."（`W/src/PIL/Image.py:1856`）；P 图转 RGBA 时逐像素读调色板第 4 字节（`W/src/libImaging/Convert.c:1144-1153`）；base 用 RGB rawmode 写回，alpha 被置 255（`W/src/PIL/Image.py:1918-1919`）；公开读者 R3（`B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/public_read.md:23`） | W2：gold，但写回 C 层时只写 RGB（`C/pillow_3a61_W2_python_layer_only.patch`；`B2/grader_candidates.md:61`） | `G/private_public_b2/p3a61_W2_python_layer_only.json`：`getpalette_None_len: 1024 768`、`rgba_render_equal: False` |
| 3 | 只测恒等映射，非恒等 RGBA 重排仍按 3 字节搬 | 题面："does not correctly handle "RGBA" palette modes, leading to incorrect palette byte arrangement"（`PUB/user_prompt.txt:30`）；docstring "``[1,0]`` would swap a two item palette"（`W/src/PIL/Image.py:1858-1860`） | W3：恒等映射直接 `return self.copy()`，其余走 base（`C/pillow_3a61_W3_identity_shortcut.patch`；`B2/grader_candidates.md:62`） | `G/private_public_b2/p3a61_W3_identity_shortcut.json`：`[1,0]` 交换后 `swap_mode: RGB`、`[50, 60, 70, 10, 20, 30]`、渲染不同 |
| 4 | 隐藏测试不保存 GIF；仓内唯一传 `source_palette` 的调用者被改坏也能过 | GIF 保存对 P 图总以 RGB 字节作 `source_palette`（`W/src/PIL/GifImagePlugin.py:511`），优化调色板时调 `remap_palette(used_palette_colors, source_palette)`（`:536`）；`optimize` 默认开启（`:657`），文档见 `W/docs/handbook/image-file-formats.rst:219-222`；base 上这条路径正确（devcheck `runs/r2e_actor_20260925/devcheck/pillow__3a61c9e95e5c0a2da5736956e2dbafa5/orig/captures/pr4_3_cmd.out:1` 为 `gif_rgb_equal: True`）。docstring 只写 `source_palette: Bytes or None`（`W/src/PIL/Image.py:1861`），唯一调用者按 RGB 传 | W1：gold，但显式传入的 `source_palette` 也按图自身的 RGBA 模式、4 字节步长读（`C/pillow_3a61_W1_mode_for_explicit_source.patch`；`B2/grader_candidates.md:60`） | `G/private_public_b2/p3a61_W1_mode_for_explicit_source.json`：`gif_rgb_equal: False`；公开 `Tests/test_file_gif.py` 在 W1 下仍 73 passed / 2 skipped，公开测试发现不了 |

四处都是 v1 §4 第 4 步（已有构造候选得 1、违反同一核心要求的其它实例或有文档的公开行为）判出的 S1；第 1、2 处同时是第 2 步的"只按示例字面值检查"（v1 §11）。Codex 第二批复核 NP-1 已给出同一验收方向：调用前快照、gold 与 C1 应过、W2/W3/W5 分别因渲染、非恒等映射、源对象变化失败、W1 由 GIF 往返拒绝（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/numpy_pillow/README.md:43-60`）。

**断言约束（避免误拒合理解）**：期望值只用字面量或调用前快照，不照抄 gold 输出；部分映射只比前 N 项与实际渲染，不断言 Python 层调色板总长度、也不断言补齐项的 alpha——gold 补 0、C1 补 255、A1u 不补齐，三种都合理（公开读者 R11，`B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/public_read.md:31`；复核 `B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/review.md:136`）；不限定写回方式（`putpalette(…, "RGBA")` 或 `putpalettealphas` 都行）；GIF 只比读回的 RGB 像素，不比文件字节或调色板长度。

## 3. 具体改动（完整测试代码）

一条 `hidden_test_text_replace`，目标 `test_1.py`（即 `PRI/hidden_tests/test_1.py`），两处 edit，`old` 在当前文本里各恰好出现一次。

**edit 1**（缺口 1、2；`old` = `:611-614` 四行）。修订后题面示例段为：

```python
        im.putpalette(list(range(256)) * 4, "RGBA")
        # Snapshot the source palette and its RGBA rendering before the call
        palette_before = bytes(im.palette.palette)
        rgba_before = im.convert("RGBA").tobytes()
        im_remapped = im.remap_palette(list(range(256)))
        assert_image_equal(im, im_remapped)
        assert im.palette.palette == im_remapped.palette.palette
        # The result keeps the original RGBA palette ...
        assert im_remapped.palette.palette == palette_before
        # ... and the palette used for rendering keeps the alpha values
        assert im_remapped.convert("RGBA").tobytes() == rgba_before
```

原有两条断言原样保留（题面示例本身的比较不删）。

**edit 2**（缺口 3、4；`old` = `    def test_remap_palette_transparency(self):\n`，即 `:621`）。在它前面插入：

```python
    def test_remap_palette_rgba_reorder(self):
        # Test a non-identity transform with an RGBA palette: entries move as
        # whole RGBA entries and the image renders with the same colours
        im = Image.new("P", (2, 1))
        im.putpixel((1, 0), 1)
        im.putpalette((10, 20, 30, 40, 50, 60, 70, 80), "RGBA")
        im_remapped = im.remap_palette([1, 0])
        assert list(im_remapped.getdata()) == [1, 0]
        assert bytes(im_remapped.palette.palette[:8]) == bytes(
            (50, 60, 70, 80, 10, 20, 30, 40)
        )
        assert list(im_remapped.convert("RGBA").getdata()) == [
            (10, 20, 30, 40),
            (50, 60, 70, 80),
        ]

    def test_remap_palette_rgba_gif_save(self):
        # Saving a P image with an RGBA palette as GIF optimizes the palette
        # through remap_palette with an RGB source_palette; colours must survive
        im = Image.new("P", (4, 1))
        for x, v in enumerate((10, 20, 30, 40)):
            im.putpixel((x, 0), v)
        im.putpalette(
            [c for i in range(256) for c in (i, 255 - i, i // 2, 128)], "RGBA"
        )
        out = io.BytesIO()
        im.save(out, "GIF")
        out.seek(0)
        with Image.open(out) as reloaded:
            assert list(reloaded.convert("RGB").getdata()) == [
                (10, 245, 5),
                (20, 235, 10),
                (30, 225, 15),
                (40, 215, 20),
            ]
```

字面量都由测试自己的输入推出：交换后第 0 项是原第 1 项 `(50,60,70,80)`、第 1 项是原第 0 项，像素索引随之变成 `[1, 0]`，渲染结果与交换前相同；GIF 用到索引 10/20/30/40，第 i 项 RGB 为 `(i, 255-i, i//2)`（alpha 128 在 GIF 中本就不保存）。输入与公开读者的 C3、C4 命令相同（`B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/public_read.md:163-199`）。`io` 已在文件头导入（`PRI/hidden_tests/test_1.py:1`）。本机已对修订后文本做语法编译检查，未执行。修订前后摘要见 `revision_draft.json` 的 `local_private_copy_sha256`（本机私有副本，仅供核对）。

## 4. 期望映射的逐键变化

| 键（期望文件里带 ANSI，写作 `\u001b[1m…\u001b[0m`） | 修订前 | 修订后 |
| --- | --- | --- |
| `TestImage.test_remap_palette_rgba_reorder` | —（无此键） | PASSED |
| `TestImage.test_remap_palette_rgba_gif_save` | — | PASSED |
| `TestImage.test_remap_palette`（断言加强，键不变） | PASSED | PASSED |
| 其余 70 键 | PASSED | PASSED（不变） |

71 键 → 73 键。键带 ANSI 是因为 `W/setup.cfg:67` 的 `addopts` 含 `--color=yes`；解析器对期望侧与观测侧都去色（`rh2/src/repoharness2/envpack/r2e_parsers.py:114-127`），新键沿用原文件写法。两个新名字在 `test_1.py` 里不存在，不撞键；新测试不带参数化，不改变其它键的收集结果（试跑里 missing / extra 都为空）。

## 5. 验收（试跑）

正对照用 gold。试跑工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，结果都在 `T/`。

| 候选 | 补丁 | 应得 | 应在哪些键上失败 | 试跑结果 | 文件 |
| --- | --- | --- | --- | --- | --- |
| 现材料 noop | — | 0 | `test_remap_palette` | mismatch，该键 FAILED | `base_noop_current.json` |
| 现材料 gold | `PRI/gold.patch` | 1 | — | match 71/71 | `base_gold_current.json` |
| gold | `PRI/gold.patch` | 1 | — | match 73/73 | `rev_gold.json` |
| noop | — | 0 | `test_remap_palette`、`…_rgba_reorder`（GIF 键应 PASSED：base 保存 GIF 本来正确） | mismatch：前两键 FAILED（原示例断言；交换后 Python 层仍是 `[50, 60, 70, 10, 20, 30]`），GIF 键 PASSED | `rev_noop.json` |
| C1（合理替代：RGB 加 `putpalettealphas`） | `C/pillow_3a61_C1_rgb_plus_alphas.patch` | 1 | — | match 73/73 | `rev_C1.json` |
| A1u（合理替代：不补齐到 256 项） | 本目录 `pillow_3a61_A1u_unpadded_putpalette.patch` | 1 | — | match 73/73 | `rev_A1u.json` |
| W1（触发反例 4） | `C/pillow_3a61_W1_mode_for_explicit_source.patch` | 0（现材料 1） | 只 `…_rgba_gif_save` | mismatch：只 GIF 键 FAILED（读回 `(242, 6, 14)…` ≠ `(10, 245, 5)…`） | `rev_W1.json` |
| W2（触发反例 2） | `C/pillow_3a61_W2_python_layer_only.patch` | 0（现材料 1） | `test_remap_palette`（渲染断言）、`…_rgba_reorder`（渲染断言） | mismatch：两键 FAILED，分别停在 `convert("RGBA")` 渲染比较与交换后渲染（alpha 成了 255） | `rev_W2.json` |
| W3（触发反例 3） | `C/pillow_3a61_W3_identity_shortcut.patch` | 0（现材料 1） | 只 `…_rgba_reorder` | mismatch：只 reorder 键 FAILED（Python 层 `[50, 60, 70, 10, 20, 30]`） | `rev_W3.json` |
| W5（触发反例 1） | `C/pillow_3a61_W5_mutate_source_to_rgb.patch` | 0（现材料 1） | `test_remap_palette`（快照断言）、`…_rgba_reorder` | mismatch：两键 FAILED，前者停在 `assert im_remapped.palette.palette == palette_before` | `rev_W5.json` |

A1u 是按复核建议（`B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/review.md:138`）补的"不补齐"正对照：在 gold 上把"补齐到 256 项再写回"换成 `m_im.putpalette(palette_bytes, palette_mode)`，即同仓后续版本的写法（`runs/r2e_static_prep_20260924/v3/public/pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90/worktree/src/PIL/Image.py` 的 `remap_palette`）。上传试跑的补丁 sha256 为 `12e49af5e367067c9b598b1ffb42ec6d0675b024bc6a50b4851e874728530e89`；本目录的副本经 Write 保存时空白上下文行去掉了行首空格，本机用 `git apply` 核对过两份应用到 base 后结果逐字节相同。

逐项核对：每条试跑都 `RH2_APPLY_RC=0`、`RH2_TRIAL_EDITS_APPLIED=1`、测试段标记齐全、没有 missing / extra 键；失败都落在新断言或原示例断言上，不是收集或环境错误。

## 6. 修订后仍受保护的公开要求与已知缺口

- **受保护**：RGBA 恒等映射后结果调色板等于**调用前**的原调色板（缺口 1）；恒等映射后实际渲染（含 alpha）不变（缺口 2）；非恒等映射按整项搬动、像素索引随之改写、渲染不变（缺口 3）；RGBA 调色板 P 图经 GIF 优化保存后颜色不变（缺口 4）；原有回归键：hopper.gif 恒等映射、非 L/P 模式抛 `ValueError`、`transparency` 随映射改写（`test_remap_palette_transparency`）。
- **已知缺口（S2，登记）**：
  1. 显式传入 `source_palette` 时，除 GIF 路径外的格式约定（按 RGB 还是按图的模式）公开材料没写（R11），不测；
  2. 部分映射时 Python 层调色板的总长度与补齐项 alpha 不测（有意不约束）；
  3. gold 在 GIF `palette=` 分支里 Python 层调色板的 mode 与字节格式可能对不上（复核 I5，静态推断，未实跑）；
  4. PNG 等其它插件对 RGBA 调色板的保存路径没覆盖；"把所有 P 图都输出为 RGBA 调色板"一类候选没跑。

## 7. 需要决定的事项

无模板外事项。本修订只补有公开依据的断言，没有改题面、没有改变任务目标、没有放宽任何原断言。

## 8. 试跑条件，以及与正式评分的差别

- 机器：本批 R2E CPU 机；派生镜像 `sha256:f402f387fddcf3e0e49661cf765165527c71996d842c7c6eaa00d2827d50e549`，配方 `r2e_derive_v1+sysconfig_v1`（每个结果文件的 `image`、`recipe_id` 字段）。
- 工具与正式评分的差别（`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py:2-9`）：不做基线重建比对；不核隐藏测试树与入口摘要；权限布置简化为整个 `/testbed` 给评分用户。**定稿后仍要走正式材料与正式评分**（至少 gold、noop、W1、W2、W3、W5；C1、A1u 建议各跑一次）。
- 每次试跑约 75–100 秒，测试段约 3 秒。

## 9. 探针就绪差距（对照本批 README §3）

1. noop 0 / gold 1：试跑已满足（现材料与修订草案都是）；正式材料落地后的正式评分待协调者。
2. 真实解题身份的开发命令：第二批 devcheck 已在旧镜像上跑通（`runs/r2e_actor_20260925/devcheck/pillow__3a61c9e95e5c0a2da5736956e2dbafa5/orig/`）；本题只改 Python，不涉及编译链；新机器新镜像上待协调者复验。
3. S1：四处已按模板修订并试跑验收；**待 Codex 复核**。
4. 公开包泄漏预检：本修订只动隐藏测试与期望，公开包不变；R2E rollout 预检由协调者跑。
5. 题卡四项用途（修订定稿、Codex 复核与正式评分之后）：`problem_localization=yes`；`capability_comparison=conditional`（评分依据已核；差新机器新镜像上的公开开发命令复验）；`training_candidate=conditional`（再差 Codex 复核与正式评分）；`heldout_candidate=no`（审查者见过 gold 与隐藏测试；本题 gold 逐字出现在同仓 `f9d3ee0f` 初态、`a682ceaf` 含其 10/13 行，`B2/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/card.md:24-28`）。
