# pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07 独立复核：初判（读作者结论前封存）

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。

**封存说明**：本文写于读取作者的 `result.md`、`evidence/` 与 `rh2/experiments/category3_cloud_20260929/pillow3a61/` 之前，也写于我自己跑任何实验之前。对作者产物只看过本目录的文件名（`result.md`、`evidence/`），没有读内容。任务说明里转述了作者的四条主张（gold 与 base 读回逐项相同；唯一差别是背景索引 3 与 4、颜色正确；颜色错位是 base 已有问题；可转第1类），我读到了这几句摘要，但没看其依据。写完后不再修改，后续核对写入同目录 `review.md`。

## 0. 本次实际读过的材料

- 规则：`task_screening_standard_v1_20260925.md` §0–§4（重点 §2 用途、§3 G1/T3、§4 第 4 步）。
- 本题既有材料：`r2e_lifecycle_20260929/results/pillow__…/probe_card.md` 全文；`r2e_static_review_batch2_20260925/results/pillow__…/screening_record.json` 中 `id == "I5"` 一条。其余旧卡文件（`card.md`、`review.md`、`revision_plan.md` 等）未读。
- 原件：`s2_r2e/ingest/public_bundles_v0.jsonl`（题面、镜像、base_commit `355820742bc2…`）与 `validation_bundles_v0.jsonl`（gold，`sha256:2edc27cd2e64…`），按 `instance_id` 取本题。
- base 源码：镜像 `namanjain12/pillow_final@sha256:bdd3d96728209c98e23507a55d2c086fe0a89a106c0d23bfb4854663d8f48813`（本机 image ID `sha256:56fc18ef3ebc…`），`/testbed` HEAD `355820742`，Pillow `9.2.0.dev0`，Python 3.9.21，PIL 从 `/testbed/src` 导入。读了：
  - `src/PIL/GifImagePlugin.py`：`_normalize_mode`（464–486）、`_normalize_palette`（489–539）、`_write_single_frame`、`_write_multiple_frames`（563–644）、`_save`、`_write_local_header`、`_get_optimize`、`_get_color_table_size`（834）、`_get_header_palette`（844）、`_get_palette_bytes`、`_get_background`（872–889）、`_get_global_header`（892–）、读取侧 `_open`/`_seek`/`load_prepare`/`load_end`；
  - `src/PIL/ImagePalette.py`：`palette` setter（52–60）、`getdata`、`tobytes`、`getcolor`（100–150）；
  - `src/PIL/Image.py`：`load`（808–）、`putpalette`（1782–1814）、`remap_palette`（1854–1925）、`convert` 中 P/ADAPTIVE 与 `quantize` 的调色板 mode 处理；
  - `src/_imaging.c`：`_getpalette`、`_getpalettemode`、`_putpalette`、`_putpalettealpha(s)`；
  - `docs/handbook/image-file-formats.rst` GIF 一节（`background` 写明是调色板索引；`palette` 保存参数写明是 RGBRGB… 字节或 `ImagePalette`）。
- 未读：Pillow 上游 issue/PR；`libImaging/Quant.c`（RGBA 图量化后 C 调色板 mode 是否为 RGBA 未核）；隐藏测试与修订材料 `r2e-mr-024/025` 的内容。

## 1. 机制（静态）

gold 让 `remap_palette` 在 `source_palette is None` 且 C 层调色板 mode 为 `RGBA` 时按 4 字节读写，返回图的 Python 调色板为 `ImagePalette("RGBA", palette_bytes)`，C 层调色板为 RGBA 256 项。base 同一情形返回 `ImagePalette("RGB", …)`，C 层为 RGB（丢 alpha）。

`_normalize_palette` 的 `palette=` 分支（519–538）先按 `im.palette.colors[3 元组]` 算 `used_palette_colors`，再 `im.remap_palette(used_palette_colors)`（不传 source），最后 `im.palette.palette = source_palette`。`source_palette` 是调用者给的 RGB 字节（≤768）。于是在 gold 下，返回图的 Python 调色板 **mode 为 `RGBA`，字节却是 3 字节一项**；`palette` setter 会按 4 字节步长重建 `colors`，得到错位的 4 元组键。I5 的静态描述成立。

## (a) 在什么输入下出现，可能影响哪些可观察输出

**出现条件**（三者同时满足）：

1. 送进 `_normalize_palette` 的图是 P 模式、C 层调色板 mode 为 `RGBA`。已读到的来源：`putpalette(…, "RGBA")`；`putpalettealpha/putpalettealphas`（C 代码把 mode 改成 `RGBA`）；`quantize()` 对 RGBA 图（`mode = im.im.getpalettemode()`）；可能还有 RGBA 图经 `_normalize_mode` 的 `convert("P", ADAPTIVE)`（Python 调色板记为 RGB，但 C 层 mode 取决于 `Quant.c`，未核）；以及 gold 自己的 `remap_palette` 输出。GIF 读入的首帧即使带透明，C 层仍为 RGB（首帧不调 `putpalettealpha`），不在此列。
2. 保存时给了 `palette=`（`encoderinfo` 或 `info["palette"]`）。
3. 之后有代码按 mode 解释这个调色板。能找到的只有 `ImagePalette.getcolor`，以及调色板被标脏后 `load()` 按 mode 重装 C 调色板。

**只有 mode 不一致本身时**，写出的 GIF 字节不受影响：全局色表写的是 `im.palette.palette`（与 base 相同的 source 字节），像素写的是重映射后的索引（映射只由 `dest_map` 决定，base/gold 相同），透明度按整数索引处理，`_get_optimize` 只看直方图。

**会消费它的路径**：

- **元组背景色** → `_get_global_header` → `_get_background` → `getcolor`（单帧、多帧首帧、`getheader()` 都走这里）。背景可以来自 `save(background=(r,g,b))`，也可以来自 `im.info["background"]`（例如 WebP 读入的 RGBA 元组）。
  - base（mode RGB）：已有颜色直接返回原索引，不改调色板；新颜色在第 n 项追加 3 字节；满 256 项时用直方图找未用索引，替换 3 字节。
  - gold（mode RGBA）：3 元组补成 `(r,g,b,255)`，在错位键里几乎查不到，于是**即使颜色已存在也会新分配**。`getcolor` 的分配算术写死了 `//3`、`*3`，却写入 `bytes(color)` 共 4 字节。
  - 预期可观察差异：
    - 逻辑屏幕描述符里的**背景索引**（base 给已有索引，gold 给新索引 n）。
    - **全局色表字节**：多一项 `(r,g,b)`，另多出 1 个游离字节。按 `_get_header_palette` 的补齐算术，写出总长 = 3T+1，T 为色表项数，所以色表后恰好多 1 字节。Pillow 读取器忽略未知字节（`else: pass`），读回可能看不出；更严格的解码器可能报错。
    - 若 `palette=` 给满 256 项且图有未用索引 i：gold 在 i 处用 4 字节替换 3 字节，**i 之后的各项整体错一个字节**。若像素用到 i 之后的索引，读回颜色会错，这是像素级差异。base 此时是正确的 3 字节替换。
    - 4 元组背景：alpha=255 时 base 截成 3 元组可正常处理，gold 不截；alpha≠255 时 base 也写 4 字节。后者是 base 已有问题。
- **多帧 `save_all` + `disposal=2` + 源图无 transparency**：`_write_multiple_frames` 第 598–601 行用默认 `(0,0,0)` 调 `_get_background(im_frame, …)`，走同一个 `getcolor`。这条路径**不需要用户给元组背景**。gold 下会给后续帧的调色板追加或插入 4 字节并置脏。随后 `_get_palette_bytes(im_frame) == _get_palette_bytes(base_im)` 的比较结果可能与 base 不同，进而走 `convert("RGB")` 分支；该分支 `load()` 时按 `RGBA` 重装 3 字节数据，得到错乱的 C 调色板。可能改变差分帧的 bbox、偏移与帧数（bbox 为空时帧会被合并）。解码像素是否变化，要看 bbox 是变大还是变小，需实测。
- **透明度**：索引经 `remap_palette` 的 `dest_map.index` 重映射，base/gold 算法相同；`getcolor` 分配时会避开透明索引。预计透明索引本身不变，但满 256 项插入错位时，透明色所在项之后的 RGB 值可能随之错位。

**base 已有、与 gold 无关的同类问题**（静态）：

- 对 RGBA 调色板图，`palette=` 分支用 3 元组查 4 元组键，永远查不到，`used_palette_colors` 退化为恒等。换序的 `palette=` 在 base 与 gold 下都会让颜色错位（索引不动，颜色被换）。
- 不带 `palette=` 且不优化时，第 538 行直接把 RGB 字节写进原图的 RGBA 模式 Python 调色板（P 图时 `im` 就是调用者的原对象）。base 同样存在 mode/字节不一致。
- `getcolor` 对 RGBA 调色板的分配算术本身就按 3 字节计。

## (b) 区分"gold 引入的回归"与"base 已有问题"的实验设计

1. **单元级确认**：同一输入分别在 base 与 gold 容器中直接调用 `GifImagePlugin._normalize_palette`，记录返回图的 `palette.mode`、`len(palette.palette)`、`im.getpalettemode()`，以及 `getcolor` 前后的调色板字节。确认 I5 的不一致只在 gold 出现，并确认 base 另两条路径（无 `palette=`、RGBA 调色板查表）已有的不一致。
2. **端到端矩阵**（单帧，一次性容器，base 与 `git apply` gold 各跑一次同一脚本）：
   - 输入：RGBA 调色板 P 图（`putpalette RGBA`）、RGBA 模式图、RGB 调色板 P 图（对照）；
   - `palette=` 形态：原序、换序（整体反转与两两交换）、子集（少于图用色）、满 256 项，形式为 bytes / list / `ImagePalette`；
   - 背景：无、整数、已有颜色 3 元组、新颜色 3 元组、4 元组 alpha=255 / alpha=0；
   - 透明度：无、`transparency=` 整数；
   - 附加变量：`optimize=True`。
3. **多帧矩阵**：2–3 帧 RGBA 调色板 P 图或 RGBA 图，`save_all` 给 `palette=`，`disposal` 取 0 / 2 / `[0,2]`，有无 transparency，有无元组背景。
4. **每例记录**：
   - 文件 sha256；
   - 自写的严格块解析：色表标志与项数、背景索引、原始色表字节、色表后与块间是否有游离字节、每帧偏移与尺寸；
   - Pillow 读回：mode、`n_frames`、每帧调色板、索引、RGBA 像素、`info` 中的 background 与 transparency；
   - 异常。
5. **判定**：
   - 对每个 base≠gold 的差异，用一个**与实现无关的期望**判断谁对：换序 `palette=` 应保留原像素颜色；背景应解析为该颜色的索引；文件应符合 GIF 块结构。
   - 只有"base 符合期望、gold 不符"才算 gold 引入的回归；两者一样错归 base 已有问题；两者错得不同则分开写。
   - 再做一次最小消融：在 gold 下把 `_normalize_palette` 返回图的 `palette.mode` 改回 RGB，或传 `source_palette`，看差异是否消失，把原因钉在 gold 改动上。

## 初判结论（待实验检验）

- I5 所说的不一致在 gold 下**确实存在**，触发条件是"C 层 RGBA 调色板的 P 图 + `palette=`"。
- 只有经 `getcolor` 消费时才会影响输出：元组背景，或多帧 `disposal=2` 且无 transparency 时的默认黑色。
- 我预期至少能在元组背景上看到 base≠gold：背景索引、全局色表多一项与一个游离字节；满 256 项且有未用索引时，可能出现读回像素颜色错误。这类差异由 gold 暴露，底层同时依赖 base 已有的 `getcolor` 与 GIF 插件缺陷。
- 按 §4 第 4 步，若只落在"未写入文档的元组背景 / `palette=` + RGBA 调色板"这类少见组合，归 T3（S2，登记）；若多帧 `disposal=2` 默认路径造成像素级错误，需要再判断是否属于有文档、常用的公开行为。
- 在实验前我**不同意**"gold 与 base 读回逐项相同"可以一般化；是否可转第1类取决于实测范围与 §4 第 4 步的归类。
