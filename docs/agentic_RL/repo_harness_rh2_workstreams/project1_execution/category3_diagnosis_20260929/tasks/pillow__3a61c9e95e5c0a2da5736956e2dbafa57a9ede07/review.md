# pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07 独立复核

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。初判已封存在同目录 [review_initial.md](review_initial.md)，写于读作者材料和做实验之前，之后未改。

## 总判断：不同意

作者结论是“疑点已消除，可申请转第1类；不需要新的正对照或修订；S2 登记为无可观察后果”。这个结论不成立。

- **I5 属实，而且有可观察后果。** 只要元组背景色经过 `getcolor`，gold 就会写出错误的背景颜色，全局色表多出几项，色表后面多一个游离字节；`palette=` 为 256 项时，读回像素颜色也会出错。把 Python 调色板 mode 改回 RGB 的消融实验能让这些差异全部消失，所以原因确实是 I5。
- **新发现一个 gold 独有的异常，比 I5 更重。** 调用 `remap_palette` 时，只要图的调色板是 RGBA、`info["transparency"]` 又是整数，gold 就抛 `ValueError('invalid palette size')`，base 不抛。受影响的包括题面示例本身加上 `info["transparency"]=0`，也包括作者自己的测试图加上 `transparency=3`。GIF 保存用 `palette=` 时同样会抛：对 RGBA 模式图基本总是触发，因为 `_normalize_mode` 会给它补上 `info["transparency"]`。
- 部分同意的地方：I5 的不一致确实存在；换序 `palette=` 导致颜色错位是 base 已有问题；公开测试数字（base、gold）属实。

## 0. 复核范围与材料

- **规则**：`task_screening_standard_v1_20260925.md` §0–§4。
- **原件**：
  - `public_bundles_v0.jsonl` 的题面；
  - `validation_bundles_v0.jsonl` 的 gold，sha256 为 `2edc27cd2e64…`，与作者 `rh2/experiments/category3_cloud_20260929/pillow3a61/gold.patch` 逐字相同，已用 `diff` 核对；
  - 镜像 `namanjain12/pillow_final@sha256:bdd3d967…8813`，Pillow 9.2.0.dev0，Python 3.9.21。
- **读过的源码**：`GifImagePlugin.py`、`ImagePalette.py`、`Image.py` 相关函数，以及 `_imaging.c` 的调色板接口（行号见初判 §0）。
- **作者材料**：第三步才读，包括：
  - `result.md` 全文；
  - `evidence/` 下 30 个文件：`evidence_manifest.json`、`semantic_v1/{base,gold,C1,A1u}` 的 g1/g2/g3/rc/prep、`summary.json`、`extra/gif2_*.json`；
  - `candidate.diff`：C1、A1u 与 `pillow3a61/` 下同名补丁逐字相同；gold 的只少末尾一行空白上下文，内容等价；
  - `pillow3a61/` 下的 `gif_behavior.py`、`gif_behavior2.py`、`_edit_C1.py`、`C1.patch`、`A1u.patch`、`semantic_spec.json`。
- **运行方式**：全部在一次性容器中执行（`docker run --rm --network none`），gold 用 `git apply`；每次运行不超过 10 秒。没有跑正式评分，没有删镜像，没有提交。
- **脚本位置**：都在本会话 scratchpad，不入库；sha256 前 12 位为 `exp.py 4a7dc99e29cd`、`exp2.py 1c404f2d4716`、`exp5.py 349772f49aa8`、`repro.py 1168b66c4740`。关键复现见 §3，已写成可直接粘贴的形式。

## 1. 我的实验与结果汇总

| 批次 | 内容 | 结果（base 对 gold） |
| --- | --- | --- |
| 第1轮 `exp.py`，394 例 | 输入：RGBA 调色板 P 图、RGBA 模式图、RGB 调色板 P 图（对照）。`palette=`：原序、反转、交换、子集、满 256 项，形式为 bytes、list、`ImagePalette`。背景：无、整数、已有色三元组、新色三元组、alpha=255 与 alpha=0 的四元组。透明度：无或 `transparency=2`。另有 `optimize=True`、不带 `palette=` 的对照、多帧 `save_all`（`disposal` 取 0、2、`[0,2,2]`）。每例都用自写的严格块解析器检查文件字节，并用 Pillow 读回，与源像素逐点比较 | 222 例完全相同。**85 例只有 gold 抛异常**，即全部 RGBA 模式输入：单帧 60、多帧 24、单元探针 1。**83 例有差异，且全部带元组背景**；消融后这 83 例都与 base 一致。4 例单元探针只是内部状态不同 |
| 第2轮 `exp2.py`，32 例 | 直接调用 `remap_palette`；从 GIF/PNG 回读；RGBA 图用 `palette=` 保存（同序或按图自身调色板顺序）；256 项插入错位；`disposal=2` 走默认黑色背景 | 12 例相同。**12 例只有 gold 抛异常**。4 例差异可由消融还原：2 例是像素损坏；另 2 例 `disposal=2` 是 gold 碰巧正确、base 错。其余 4 例：A1、A5、A7 是题目要的修复效果（gold 保留 alpha）；A6 两边都抛异常，只是信息不同 |
| `exp5.py` | 作者原图，调色板 4 项或补齐到 256 项，透明度无或 3；分别测 `convert`、`remap_palette`、三种保存方式 | 见 §3 N1。另用作者的 C1、A1u 补丁跑了同一组输入，结果见 §3 |
| 公开测试 | `Tests/test_file_gif.py`、`Tests/test_image.py` | base、gold 都是 73 passed / 2 skipped 和 71 passed / 1 skipped |

**消融**只做一件事：`_normalize_palette(palette=…)` 返回后，把 Python 调色板 mode 从 RGBA 改回 RGB，字节不动。gold 加消融后，第1轮与第2轮所有“有差异但不抛异常”的例子都与 base 逐字节一致；抛异常的例子依旧抛，因为异常发生在 `remap_palette` 内部，比消融钩子更早。

## 2. 逐条核对

| # | 作者主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | I5 的不一致确实存在（Python 调色板为 RGBA，字节为 12） | 同意 | 单元探针 U1、U2、U4、U7：gold 返回 `palette.mode='RGBA'`，字节 3 个一组；base 为 RGB。U3（RGB 对照）两边相同；U5（RGBA 模式图）在 gold 抛异常 |
| 2 | 在该分支上，gold 与 base 的保存读回像素、调色板、索引逐项相同 | **不同意**。只在作者测过的那一类输入上成立：RGBA 调色板 P 图、无透明信息、无元组背景 | ① 抛异常：N1 的 R1、R2，以及作者原图加 `info["transparency"]=3`（`exp5`），base 能正常保存或重映射，gold 抛 `ValueError`。② 像素：N4 的 R5 中，gold 读回坐标 `(4,0)`（索引 255）的像素为 `(255,255,0)`，应为 `(255,0,249)`；第2轮 C 例 52/256 像素、多帧 `MF_full256` 第 2 帧 16 像素出错，base 都是 0。③ 调色板：N3 全局色表 4 项变 8 项 |
| 3 | 唯一可观察差别是背景索引（3 与 4），两者都指向正确颜色 | **不同意** | 按作者原配置重跑（换序 `palette=` 加 `background=(0,255,0)`）：gold 文件 59 字节，base 46 字节；全局色表 8 项（base 4 项）；色表后的下一个字节是 `0x00`，base 是 `0x2C`（R3）。Pillow 读取器会跳过未知字节，所以作者读回时看不到。另外，把 `palette=` 反转后，gold 背景索引 1 对应 `(0,0,255)`，颜色错了；base 背景索引 2 对应 `(0,255,0)`，正确（R4） |
| 4 | RGBA 调色板图配合换序 `palette=` 颜色错位，是 base 已有问题，登记 T3 | **同意错位本身；“与本题无关”部分不同意** | 反转 256/256、交换 128/256，base 与 gold 完全相同；RGB 调色板对照 0/256。但同一分支里 gold 另外引入了 N1–N4，所以这个分支与本题并非无关 |
| 5 | 公开测试 73/2、71/1，四个版本相同 | base、gold **同意**；C1、A1u 未查 | 我只在 base、gold 上跑过公开测试 |
| 6 | “要求 gold 保持 RGB mode 没有公开依据，属无依据的格式扩张” | **部分同意** | 元组背景用于 GIF 保存确实没有文档：`image-file-formats.rst` 写的是“a palette color index”，元组只来自 WebP 的 info。所以 N2–N4 按罕见路径处理是合理的。但它们的后果是背景颜色错、文件结构错、像素错，不是“格式扩张” |
| 7 | 不需要新的正对照或修订，可转第1类；S2 写“无可观察后果” | **不同意** | “无可观察后果”已被 N2–N4 推翻。N1 需要按 §4 第 4 步重新判定（见 §4），在此之前不能写“疑点已消除” |

## 3. 反例与新问题

以下复现均在一次性容器中执行：base 与 gold 各跑一次 `repro.py`，gold 先 `git apply`。

```python
from PIL import Image
im = Image.new("P", (4, 1)); im.putdata([0, 1, 2, 3])
im.putpalette(bytes([255,0,0,255, 0,255,0,128, 0,0,255,255, 10,20,30,0]), "RGBA")  # 作者用的颜色和 alpha
im.info["transparency"] = 3
im.remap_palette([0, 1, 2, 3])     # base: 正常返回；gold: ValueError('invalid palette size')
```

| 编号 | 复现 | base | gold | 与 I5 的关系 |
| --- | --- | --- | --- | --- |
| R1 | 上面的 `remap_palette` 恒等映射，`info["transparency"]=3` | `[0,1,2,3]` | `ValueError('invalid palette size')` | 新问题 N1 |
| R2 | 4 色不透明 RGBA 图 `.save(GIF, palette=同色)` | 54 字节 | `ValueError` | N1 经 I5 分支触发 |
| R3 | 作者原配置：换序 `palette=` 加 `background=(0,255,0)` | 色表 4 项，背景 3，下一字节 `0x2C` | 色表 8 项，背景 4，下一字节 `0x00`（游离） | N3，消融可还原 |
| R4 | 反转 `palette=` 加 `background=(0,255,0)` | 背景 2 → `(0,255,0)` | 背景 1 → `(0,0,255)` | N2，消融可还原 |
| R5 | 256 项 `palette=`，像素用到索引 255，`background=(0,255,0)` | 像素 `(255,0,249)` 正确 | 像素 `(255,255,0)` | N4，消融可还原 |

- **N1：gold 独有的 `ValueError`**（阻断）
  - **机制**：gold 的 `remap_palette` 在 RGBA 时构造 `ImagePalette("RGBA", mapping_palette*4)`，共 1024 字节，然后调用 `convert("L")`。`convert` 遇到整数透明度会执行 `trns_im.putpalette(self.palette)`（`Image.py:975`）。`putpalette` 把这 1024 字节当 RGB 解读，得到 341 项，于是报错。调用链为 `Image.py:1924 → 975 → 1814 → 826`。base 的映射调色板固定是 768 字节 RGB，不会走到这里。
  - **触发条件**：C 层调色板为 RGBA、`info["transparency"]` 为整数、不传 `source_palette`，调色板大小无关（4 项与 256 项都触发）。
  - **实际入口**：
    - 直接调用 `remap_palette`：题面示例加 `transparency=0`（A4）、`quantize()` 后加透明度（A8）都会触发；
    - GIF 用 `palette=` 保存 RGBA 模式图：`_normalize_mode` 对 RGBA 图量化后总会设置 `info["transparency"]`。不透明的 hopper 也被设为 231，因为调色板里有 alpha=0 的补齐项。所以这条入口几乎必然触发：`H1`、`H2`、`H4` 以及第1轮全部 84 例 RGBA 模式保存都抛异常。
  - **不触发的情况**：`transparency=` 作为保存参数传入（B6）；PNG/GIF 回读的图（C 层调色板是 RGB，A9、A10）；不带 `palette=` 保存（B3、H3）。
  - **base 在这些输入上的行为**：
    - `remap_palette` 能返回结果：透明索引保留在 info 里，但其他项的 alpha 丢失，这本来就是题面缺陷；
    - GIF 保存：`palette=` 与量化顺序一致时读回正确（B4 0/256、B5 0/256），不一致时颜色错位（B1 128/256，属 base 已有问题）。
  - **相关的 base 已有缺陷**：base 自己对“1024 字节 RGBA Python 调色板加整数透明度”的图调用 `convert("RGB")` 或 `convert("L")` 也会报同样的错（`exp5` 的 `pal256_trans3`）。gold 把 `remap_palette` 引到了这个缺陷上。
  - **替代解**：作者重建的 C1（RGB 映射调色板加 `putpalettealphas`）在 A2–A5、A7、A8、B1–B5 上都不抛异常；A6 是元组透明度，C1 与 base 一样报 `Transparency for P mode should be bytes or int`。A1u 与 gold 一样抛 `invalid palette size`。
- **N2：背景颜色错**（非阻断，T3 候选）。gold 下 Python 调色板按 4 字节步长建 `colors` 键，而字节是 3 字节一组，于是查到的是错位窗口。反转 `palette=` 时，`(0,255,0,255)` 恰好匹配第 2 个窗口，返回索引 1，而该项实际是蓝色。
- **N3：色表多项加游离字节**（非阻断，T3 候选）。`getcolor` 分配新项时按 `//3` 计算位置，却写入 4 字节，所以色表后恰好多 1 字节，不符合 GIF 块语法。作者原配置也会触发。base 走不带 `palette=` 且 `optimize=False` 的路径时也有同一现象（`S_rgbaP_NOPALETTE_noopt_*`，base 与 gold 相同），说明这个机制在 base 已存在，gold 把它扩展到了 `palette=` 分支。
- **N4：256 项 `palette=` 时像素损坏**（非阻断，T3 候选）。gold 在最高未用索引处用 4 字节替换 3 字节，之后各项整体错一个字节。背景色已存在时 base 返回原索引；背景色是新颜色时 base 做 3 字节替换。两种情况 base 都正确。多帧时，帧 1 未用、帧 2 在用的索引会被改成背景色（`MF_full256` 中 16 个像素）。C1、A1u 同样会出现（C 例 52/256）。
- **非回归的差异**：`disposal=2` 且无透明度时，编码端默认按黑色背景计算 bbox，解码端却恢复为背景索引 0 的颜色。base 因此在 RGB 与 RGBA 调色板上都错 240/256，这是 base 已有问题。gold 因 I5 走了 RGB 差分，bbox 取满帧，碰巧读回正确。
- **初判中被实验纠正的两处**：
  - RGBA 图经 `convert("P", ADAPTIVE)` 后 Python 调色板就是 RGBA，因为 `convert` 直接 `return self.quantize(colors)`；初判写的“记为 RGB”是错的。
  - 初判认为“透明度只影响索引”，漏掉了 N1。

## 4. 阻断项与非阻断建议

**阻断项**

1. **N1 未处理，不能写“疑点已消除”，也不能转第1类。** N1 发生在题目的核心函数 `remap_palette` 上，输入是 RGBA 调色板图，题面示例本身加上 `transparency=0` 就会触发，base 不会抛异常。按 §4 第 4 步，这属于“得 1 的候选在同一核心要求的其它实例上违反公开要求”。
   - **我的倾向**：判 S1 候选。
   - **反方理由**：“RGBA 调色板加整数透明度”可以算作不常见的组合；而且 base 在这些输入上本来也不符合题面要求，只是没有抛异常。
   - **请主审决定**：主审需写出判定和依据；按 §4“分歧处理”，一次聚焦复核解决不了就记 conditional。
   - **若判 S1**：走 R-c，新增断言 `remap_palette` 在 RGBA 调色板加整数透明度时不抛异常、调色板与透明索引保持不变；可选再加一条“RGBA 图用 `palette=` 保存 GIF 不抛异常”。gold 过不了这些断言，需要改用经核实的替代正对照。C1 类实现在我的探针上通过，但要用正式评分核实 73 键。作者的 C1 是按旧卡描述重建的，是否与探针卡里正式评分过的 C1 相同，我未核对。
2. **S2 的登记文本要改。** 应写成：“I5 属实。元组背景经 `getcolor` 时，gold 会写错背景颜色、在色表后留下游离字节；`palette=` 为 256 项时读回像素出错。消融已确认原因；背景元组未写入 GIF 文档，按罕见路径登记 T3。”不能写“无可观察后果”。

**非阻断建议**

- 把 base 已有问题分开登记，避免记到 gold 名下：
  - RGBA 调色板配合换序 `palette=` 时颜色错位；
  - 1024 字节 RGBA Python 调色板加整数透明度时，`convert("RGB"/"L")` 报错；
  - 不带 `palette=` 的路径上，元组背景也会留下游离字节；
  - `disposal=2` 编码端与解码端的背景不一致。
- 证据中应加入对文件字节的逐块解析。Pillow 读取器会跳过游离字节，只看读回结果会漏掉 N3。
- 作者矩阵只覆盖一张 4×1 图、一种背景，没有覆盖透明度、RGBA 模式输入、多帧和 256 项调色板；本复核补上了这几项。

## 5. 未查

- 其它 GIF 解码器（浏览器、giflib）对游离字节的处理。
- Pillow 上游是否修过 N1。
- 隐藏测试 `r2e-mr-024/025` 的内容。
- 正式评分，以及 C1、A1u 的公开测试。
- PNG、WebP 等其它插件保存 RGBA 调色板的路径。
- `LoadingStrategy` 非默认值下的 GIF 回读。
