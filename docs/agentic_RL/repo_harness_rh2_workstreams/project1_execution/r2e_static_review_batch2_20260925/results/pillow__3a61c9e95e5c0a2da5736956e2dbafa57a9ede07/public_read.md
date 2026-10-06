# pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07：公开读者记录

- 角色：R2E 公开读者（静态审查，不解题），2026-09-25。
- 材料目录：`runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/`，下文称 PUBLIC_DIR。`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json` 相对 PUBLIC_DIR；其余路径都相对 `PUBLIC_DIR/worktree/`，即解题者看到的 `/testbed`，行号按这个工作树。
- base 提交：`355820742bc2ca8a90d9c25661e8988cbd7cb5de`（`public_bundle.json:9`，和 `user_prompt.txt:1` 的 `355820742bc2` 一致）；Pillow 版本 `9.2.0.dev0`（`src/PIL/_version.py:2`）。
- 下文所有"预计输出"都是读代码推出来的。没有运行任何项目代码。

## 0. 结论摘要

题面描述的现象可以从 base 源码确认。原因在 `remap_palette` 的三处写法：它只按 RGB 每项 3 字节读取源调色板（`src/PIL/Image.py:1873`、`:1882`），又把结果调色板固定建成 `"RGB"` 并用 RGB 格式写回底层（`:1918-1920`）。而 `putpalette(..., "RGBA")` 之后，`im.palette` 是 1024 字节、mode 为 `"RGBA"`（`:836-838`）。所以示例打印 `False`，而且结果图在 C 层（Pillow 的 C 扩展里实际存放调色板的那一层）的 alpha 全部变成 255。

主要开放点：显式传入的 `source_palette` 在 RGBA 图上应该怎么解释（GIF 保存路径会传入 RGB 字节）；C 层 alpha、部分映射时的长度和补齐方式是否也在隐藏测试的检查范围内。

## 1. 需求表

"明确度"一栏：明示＝题面或公开测试直接写出；合理推知＝可从公开代码或约定推出；多解＝仍有多种合理解释。

| # | 需求 | 改变/保留 | 依据 | 明确度 |
|---|---|---|---|---|
| R1 | P 图带 RGBA 调色板时，`remap_palette(list(range(256)))` 之后 `im.palette.palette == im_remapped.palette.palette` 应为 True | 改变 | 题面 Expected（`user_prompt.txt:26-27`）和示例（`:10-24`） | 明示 |
| R1a | R1 的直接推论：结果的 `palette.palette` 必须是逐项交织的 RGBA 字节，即 RGBARGBA…，恒等映射时正好 1024 字节。格式要和 `load()` 用 `getpalette("RGBA", "RGBA")` 生成的一致（`src/PIL/Image.py:836-838`）。"RGB 段加 alpha 段"或只有 768 字节，都不会相等 | 改变 | R1 与代码 | 明示（R1 的推论） |
| R2 | 结果图的 Python 层调色板仍是 RGBA：`palette.mode == "RGBA"`；非恒等映射时按整项（4 字节）搬动 | 改变 | 题面 "does not correctly handle 'RGBA' palette modes"（`user_prompt.txt:30`）。RGBA 调色板的既有约定：`putpalette` 加 `load` 把 mode 设为 `"RGBA"`（`src/PIL/Image.py:836-838`）；`Tests/test_image_putpalette.py:74-78` 断言 `im.palette.colors == {(1, 2, 3, 4): 0}` | 合理推知 |
| R3 | C 层调色板也保留 alpha：重排后 `convert("RGBA")` 的渲染结果不变，`getpalette(None)` 返回 RGBA | 改变 | docstring "Rewrites the image to reorder the palette."（`src/PIL/Image.py:1856`）；`p2rgba` 读取调色板第 4 字节（`src/libImaging/Convert.c:1144-1153`）；base 用 RGB rawmode 写回（`src/PIL/Image.py:1919`），`ImagingUnpackRGB` 把 alpha 置为 255（`src/libImaging/Unpack.c:583-600`） | 合理推知（题面只比较 Python 层字节） |
| R4 | 像素索引的重映射逻辑不变（恒等映射时像素不变） | 保留 | `Tests/test_image.py:602-605`，用 hopper.gif 做恒等变换。`assert_image_equal` 只比较 mode、size、`tobytes()`（`Tests/helper.py:87-98`） | 明示（公开测试） |
| R5 | 模式不是 `"L"`/`"P"` 时先抛 `ValueError`，而且要在使用 `dest_map` 之前抛出。测试传入 `None`，图是 RGB 的 `hopper()`，其 `palette` 为 None | 保留 | `src/PIL/Image.py:1867-1868`；`Tests/test_image.py:607-610` | 明示 |
| R6 | `info["transparency"]` 随映射改成新索引；映射里没有它时删除 | 保留 | `src/PIL/Image.py:1922-1927`；`Tests/test_image.py:612-624` | 明示 |
| R7 | RGB 调色板（最常见情况）的结果不变。Python 层是 `ImagePalette("RGB", palette=palette_bytes)`，长度 `len(dest_map)*3`，不补齐；C 层补到 768 字节 | 保留 | `src/PIL/Image.py:1918-1920`。`Tests/test_file_gif.py:120-136`（`test_optimize`）断言 1x1 的 L 图开启 optimize 后文件为 43 字节，这依赖 Python 层调色板不补齐。其它 GIF 测试也会间接调用 `remap_palette`：`:139-173`、`:1059`、`:1124-1150` | 长度不补齐由 `test_optimize` 间接固定；其余属合理推知 |
| R8 | `"L"` 模式输入默认用灰度 RGB 源调色板 | 保留 | `src/PIL/Image.py:1874-1875`。GIF 测试（`Tests/test_file_gif.py:120-136`、`:176-180`）虽然对 L 图调用了 `remap_palette`，但 GIF 代码自己算好灰度 `source_palette` 并显式传入（`src/PIL/GifImagePlugin.py:513-515`、`:536`），所以函数内部的默认分支没有公开测试覆盖 | 合理推知 |
| R9 | GIF 保存路径：`_normalize_palette` 对 P 图总是取 `im.im.getpalette("RGB")[:768]`（每项 RGB 3 字节）作为 `source_palette` 显式传入（`src/PIL/GifImagePlugin.py:511`、`:534-536`）。结果的 `palette.palette` 被原样写进 GIF 颜色表（`:862-869`、`:912-926`），所以必须仍是 RGB 三元组。RGBA 调色板的 P 图确实会走到这条路径：一是用户直接保存这种图，GIF 默认 `optimize=True`（`:657`）；二是 RGBA 图经 `_normalize_mode` 转成 P 后得到 RGBA 调色板（`src/PIL/Image.py:944-945`、`:1141-1143`；`src/PIL/GifImagePlugin.py:480`） | 保留 | 调用者代码 | 合理推知；是否在隐藏测试范围内未知 |
| R10 | 源调色板短于 `dest_map` 引用的位置时不报错：切片越界得到空字节，后面再补零 | 保留 | `src/PIL/Image.py:1882`、`:1918` | 合理推知（低优先） |
| R11 | 三项未定约定：显式 `source_palette` 在 RGBA 图上用什么格式；部分映射时 RGBA 结果在 Python 层的长度（`len(dest_map)*4` 还是 1024）；补齐字节的 alpha 取 0 还是 255 | 未定 | docstring 只写 "Bytes or None."（`src/PIL/Image.py:1861`）；题面没有涉及 | 多解 |

## 2. 合理实现范围

只要满足 R1 到 R10，下面这些差异都应被接受：

- **怎么判定是 RGBA**：读 `self.palette.mode`（在 `load()` 之后）或读 C 层的 `self.im.getpalettemode()` 都合理。后者不依赖 Python 层对象。base 对 `palette` 为 None 的 P 图也能 remap，因为它只读 C 层调色板（`src/PIL/Image.py:1873`、`:531-544`；新建 P 图总有 C 层调色板，`src/libImaging/Storage.c:71-75`）。如果实现直接读 `self.palette.mode`，这种边界情况会变成 `AttributeError`。公开测试没有覆盖，属低优先。
- **怎么取源字节**：可以用 `self.im.getpalette("RGBA", "RGBA")` 或 `self.getpalette(None)`，也可以分别取 RGB 和 alpha 再交织。仓库里已有同类写法：`quantize` 用 `getpalettemode()` 加 `getpalette(mode, mode)` 构造 `ImagePalette(mode, ...)`（`src/PIL/Image.py:1141-1143`）。
- **怎么写回**：可以 `putpalette(..., "RGBA")` 后再设 Python 层的 `ImagePalette("RGBA", ...)`；可以先写 RGB，再用 `putpalettealphas` 补 alpha，并同步 Python 层（`putpalettealphas` 会把 C 层 mode 改成 RGBA，`src/_imaging.c:1709`、`:1727`）；也可以直接沿用 `load()` 生成的 Python 层调色板。结果满足 R1a、R2、R3 即可。
- **代码结构**：写一套"每项字节数 = len(mode)"的统一逻辑，或者 RGB、RGBA 各写一个分支，都可以。
- **显式 `source_palette`**：有三种说得通的做法：继续按 RGB 解释（改动最小，GIF 路径不受影响）；按长度或新增的可选参数识别 RGBA；同时修改 GIF 调用者。前提是 R9 的 GIF 输出仍然正确。
- **接口**：不需要新增公开 API。可以加可选参数，但 `remap_palette(dest_map)` 的默认行为必须满足 R1。
- **C 代码**：不需要改。C 层对 RGBA 调色板的读写已经支持（`src/_imaging.c:1064-1097`、`:1641-1681`；`src/libImaging/Pack.c:588`、`src/libImaging/Unpack.c:1584`）。代码需兼容 `python_requires = >=3.7`（`setup.cfg:36`），环境是 3.9.21。

没有明确约定的：命名；Python 层结果调色板用 `bytes` 还是 `bytearray`（两者相等比较不受影响）；R11 的长度与补齐。按 R7 的 RGB 行为类推，RGBA 不补齐、长度为 `len(dest_map)*4` 更一致，但这不是硬性要求。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出修法

没有。"Buggy Code Example" 是复现脚本，不是修好后的实现（`user_prompt.txt:10-24`）。标题和描述点名了 `remap_palette` 与 "RGBA" palette mode（`:4`、`:7`、`:30`），相当于给出了定位和方向（按 RGBA 处理调色板字节），属中等强度的方向提示。解题者仍需自己找到 `src/PIL/Image.py` 里的三处 RGB 假设：`:1873` 只取 RGB，`:1882` 按 3 字节步长取项，`:1918-1920` 按 RGB 补齐并建 `"RGB"` 调色板；还要自己决定怎样写回 C 层。

### 3.2 题面描述的行为能否从 base 读出

能。以示例输入为例：

1. `putpalette(list(range(256)) * 4, "RGBA")` 先生成 `ImagePalette.raw("RGBA", data)`（`src/PIL/Image.py:1810`、`src/PIL/ImagePalette.py:178-183`）。
2. 随后的 `load()` 调用 C 层 `putpalette("RGBA", 1024 字节)`。C 层调色板的 mode 为 `"RGBA"`，共 256 项（`src/_imaging.c:1658`、`:1674-1677`）。
3. Python 层的 `palette.mode` 设为 `"RGBA"`，`palette.palette` 设为 `getpalette("RGBA", "RGBA")` 的结果，共 1024 字节（`src/PIL/Image.py:836-838`）。
4. `remap_palette` 取 `self.im.getpalette("RGB")[:768]`（`:1873`，得到 768 字节，alpha 被丢掉），按 3 字节拼出 `palette_bytes`（`:1882`）。
5. 它用 RGB rawmode 写回 C 层（`:1919`，alpha 被置 255），再设 `ImagePalette("RGB", palette=palette_bytes)`（`:1920`）。
6. 结果：768 字节、mode `"RGB"`，与原来的 1024 字节比较得到 `False`。

题面措辞有两处不准，但不影响定位：

- 标题说 "Fails"，但不会抛异常，而是静默地给出错误结果。
- "incorrect palette byte arrangement" 描述不准：字节没有乱序，而是 alpha 字节被丢弃、调色板降级为 RGB，C 层渲染用的 alpha 也变成 255。

另外，仓库里现有的相等检查都发现不了这个 bug：`assert_image_equal` 只比较 mode、size、`tobytes()`（`Tests/helper.py:87-98`）；`Image.__eq__` 用默认 rawmode `"RGB"` 比较 `getpalette()`（`src/PIL/Image.py:625-634`），不含 alpha。

### 3.3 题面示例在 base 接口下是否说得通

说得通。示例用到的 `Image.new`、`putpixel`、`putpalette(data, "RGBA")`（docstring 明确支持，`src/PIL/Image.py:1792-1799`）、`remap_palette(dest_map)`、`.palette.palette` 在 base 里都存在。

几个小问题：

- `ImagePalette` 被导入但没有使用。
- `list(range(256)) * 4` 当作 RGBA 数据时只有 64 种不同颜色，第 i 项和第 i+64 项相同。这对恒等映射没有影响。
- 示例只覆盖恒等映射，不覆盖非恒等重排、显式 `source_palette` 和 C 层 alpha。

### 3.4 `public_hints` 三分类（`public_bundle.json:15`）

- **题目需求**："find the root cause, and edit NON-TEST source files to fix the issue"。
- **给解题者的操作指令**：不要改仓库的测试文件；测试只跑单个文件或模块；在 `/testbed` 用 `python -m pytest` 运行；确认完成后简短总结并停止调用工具。
- **环境事实声明**：bash 已经在 `/testbed`；`python` 和测试工具指向 `/testbed/.venv`；没有网络，`pip` 可能不可用；修复由另一组测试评判。`environment_brief.md:10-12` 进一步给出：Python 3.9.21；pip、pip3、uv 都不在 PATH；agent（uid 54321）可写 `/testbed`。提示里说这是 "a real GitHub issue"，但 R2E 题面是自动生成的，这句不准确，不过不影响解法。
- **对合法解法的影响**：修复是纯 Python，改 `src/PIL/Image.py`，可能再改 `src/PIL/GifImagePlugin.py`。不需要装包、联网或重新编译 C 扩展。"不改测试文件"只意味着不能把回归测试加进 `Tests/`，不影响修复的正确性。`user_prompt.txt` 本身不包含这些提示；它们在真实容器里以什么形式送达模型，本次没有核实。

### 3.5 初态线索

- `worktree_manifest.json` 里 `initial_diff.bytes = 0`：镜像初态相对 base 没有改动。工作树就是 base 的跟踪文件加上 `run_tests.sh`，没有影响题意的初态改动。
- `run_tests.sh` 是评分入口，内容为 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。工作树里没有 `r2e_tests/`（隐藏测试）。如果解题时容器里也没有这个目录，直接运行它预计会报 pytest 找不到路径（exit code 4）。这和本题的 bug 无关。
- 镜像里有 `install.sh`，但公开包里缺这个文件（`untracked_missing`）。所以 Pillow 在 `.venv` 里是可编辑安装、就地构建还是普通安装，从公开材料无法确认。编译好的扩展和 `.venv` 也不在工作树中。
- 根目录 `conftest.py:1` 以插件方式加载 `Tests.helper`，后者导入 `packaging`（`Tests/helper.py:14`）。缺少 `packaging` 时，从 `/testbed` 发起的任何 pytest 运行都会在启动阶段失败。

### 3.6 公开材料能否定位复现与调查入口

能。示例是自包含的，不需要数据文件。调查入口：

- `remap_palette`：`src/PIL/Image.py:1854-1929`。
- 调色板的写入、建立和读取：`putpalette`（`:1782-1814`）、`load`（`:808-838`）、`getpalette`（`:1430-1450`）；`src/PIL/ImagePalette.py:25-183`。
- C 层：`src/_imaging.c:1064-1097`、`:1641-1735`。
- 调用者：`src/PIL/GifImagePlugin.py:489-539`。
- 公开测试：`Tests/test_image.py:602-624`、`Tests/test_image_putpalette.py:50-78`、`Tests/test_image_getpalette.py:24-44`、`Tests/test_file_gif.py`。

### 3.7 缺失信息

- **可能真正影响结果的**：R11 的几项约定，以及是否也检查 C 层 alpha（R3）。只有隐藏测试检查到这些细节时才要紧。题面给不出答案，解题者只能按一致性自行选择。
- **正常读代码就能获得的**：RGBA 调色板在 Python 层和 C 层怎么表示；GIF 调用者怎么传参；C 层对 `"RGBA"` rawmode 的支持。这些不算题面缺陷。

## 4. 开发需求表

所有命令都是建议，未执行，均在 `/testbed` 下运行；预计输出来自静态阅读。

| 操作 / 资产 | 公开依据 | environment_brief 支持到哪一层 | 缺口 | 命令 |
|---|---|---|---|---|
| D1 确认 `import PIL` 来自 `/testbed/src`（这样改动才生效），并确认测试依赖齐全 | `setup.py:1000-1001` 的 `package_dir={"": "src"}`；`Makefile:50-51` 的就地可编辑构建；提示称 python 和测试工具指向 `.venv` | 解释器路径与版本（3.9.21） | 缺 `install.sh`，安装方式和 `_imaging*.so` 位置未知；`packaging` 是否已装未知 | C1 |
| D2 复现，并区分修复前后（恒等映射） | 题面示例 | 只需要 Python 和已编译的 `_imaging` | 无 | C2 |
| D3 非恒等重排与 alpha 渲染 | R2、R3 的推断 | 同上 | 无 | C3 |
| D4 GIF 调用者回归（显式传入 RGB `source_palette`） | `src/PIL/GifImagePlugin.py:489-539`、`:657` | 同上（只写内存，不落盘） | 无 | C4 |
| D5 窄范围公开测试 | `Tests/test_image.py:602-624`、`Tests/test_file_gif.py`、`Tests/README.rst` | 提示称 pytest 可用；2 CPU / 4 GiB / `/tmp` 1 GiB 对这些检查足够 | pytest 和 packaging 是否已装未证实（见 D1） | C5 |
| D6 构建 | 修复只涉及 Python，C 层已支持 RGBA | 无 pip，无网络 | 如果改 C 代码，无法确认能否重新编译（是否有编译器未知）。本题不需要改 C | 无 |

C1：检查导入来源和测试依赖。

```bash
cd /testbed && python -c "import PIL, PIL._imaging as c; print(PIL.__version__); print(PIL.__file__); print(c.__file__)" && python -c "import pytest, packaging; print(pytest.__version__, packaging.__version__)"
```

预计输出 `9.2.0.dev0`；如果是可编辑安装或就地构建，两个路径都在 `/testbed/src/PIL/` 下；最后打印 pytest 和 packaging 的版本号。如果 PIL 的路径在 `/testbed/.venv/lib/python3.9/site-packages/` 下，改 `src/` 不会影响测试，应先报告这一点。

C2：复现，并区分修复前后。

```bash
cd /testbed && python - <<'EOF'
from PIL import Image
im = Image.new("P", (256, 1))
for x in range(256):
    im.putpixel((x, 0), x)
im.putpalette(list(range(256)) * 4, "RGBA")
r = im.remap_palette(list(range(256)))
print("same_palette_bytes:", im.palette.palette == r.palette.palette)
print("palette_mode:", im.palette.mode, r.palette.mode)
print("palette_len:", len(im.palette.palette), len(r.palette.palette))
print("getpalette_None_len:", len(im.getpalette(None)), len(r.getpalette(None)))
print("rgba_render_equal:", im.convert("RGBA").tobytes() == r.convert("RGBA").tobytes())
print("indices_equal:", im.tobytes() == r.tobytes())
EOF
```

修复前预计：

```
same_palette_bytes: False
palette_mode: RGBA RGB
palette_len: 1024 768
getpalette_None_len: 1024 768
rgba_render_equal: False
indices_equal: True
```

修复后，`same_palette_bytes: True` 是题面明示的要求，`indices_equal: True` 必须保持。按 R2、R3 的合理预期还有 `palette_mode: RGBA RGBA`、`palette_len: 1024 1024`、`getpalette_None_len: 1024 1024`、`rgba_render_equal: True`，但这几项取决于具体实现。

C3：非恒等重排。

```bash
cd /testbed && python - <<'EOF'
from PIL import Image
im = Image.new("P", (2, 1))
im.putpixel((1, 0), 1)
im.putpalette((10, 20, 30, 40, 50, 60, 70, 80), "RGBA")
s = im.remap_palette([1, 0])
print("swap_mode:", s.palette.mode)
print("swap_first_bytes:", list(s.palette.palette)[:8])
print("swap_indices:", list(s.getdata()))
print("swap_render_equal:", list(im.convert("RGBA").getdata()) == list(s.convert("RGBA").getdata()))
EOF
```

修复前预计：`swap_mode: RGB`、`swap_first_bytes: [50, 60, 70, 10, 20, 30]`、`swap_indices: [1, 0]`、`swap_render_equal: False`。修复后的合理预期：`RGBA`、`[50, 60, 70, 80, 10, 20, 30, 40]`、`[1, 0]`、`True`。

C4：GIF 调用者回归。修复前后都应输出 True。

```bash
cd /testbed && python - <<'EOF'
from io import BytesIO
from PIL import Image
im = Image.new("P", (4, 1))
for x, v in enumerate((10, 20, 30, 40)):
    im.putpixel((x, 0), v)
im.putpalette([c for i in range(256) for c in (i, 255 - i, i // 2, 128)], "RGBA")
buf = BytesIO()
im.save(buf, "GIF")
buf.seek(0)
with Image.open(buf) as reloaded:
    print("gif_rgb_equal:", list(reloaded.convert("RGB").getdata()) == list(im.convert("RGB").getdata()))
EOF
```

这张图只用了 4 个稀疏索引，所以 GIF 默认的 optimize 会调用 `remap_palette(used, RGB source_palette)`（`src/PIL/GifImagePlugin.py:511`、`:534-536`、`:808-831`）。修复前预计输出 `gif_rgb_equal: True`，修复后必须仍为 `True`。有两类实现预计会让它变成 `False`：把显式传入的 RGB `source_palette` 按 4 字节读取；或者在这条路径上让 `palette.palette` 变成 RGBA 字节。

C5：窄范围公开测试，逐个文件运行。

```bash
cd /testbed && python -m pytest Tests/test_image.py -k remap_palette
cd /testbed && python -m pytest Tests/test_file_gif.py
cd /testbed && python -m pytest Tests/test_image_putpalette.py
cd /testbed && python -m pytest Tests/test_image_getpalette.py
```

- 第一条：修复前后预计都是 `2 passed`，其余用例被 deselect。它区分不了修复前后，只用来防回归。
- 第二条（GIF 测试文件）：建议先在未改动时跑一次作为基线，修复后的结果应和基线一致。其中 `test_optimize`（`:120-136`）对 L/RGB 路径的调色板长度敏感。
- 后两条：只有改动了 `putpalette`、`load` 或 `ImagePalette` 时才需要跑，应保持通过。

## 5. 阅读范围与限制

实际打开的文件：

- 角色卡；PUBLIC_DIR 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。`worktree_manifest.json` 只看了开头片段、`files` 以外的键和文件条目数（1511），没有打开它引用的 PUBLIC_DIR 以外的路径（例如 `initial_diff.source`）。
- 工作树里的配置和说明：`run_tests.sh`、`conftest.py`、`setup.cfg`、`tox.ini`、`.gitignore`、`Makefile`（前 80 行）、`Tests/README.rst`（前 40 行）、`src/PIL/_version.py`、`src/PIL/__init__.py`（开头）。以下只看了片段或 grep 结果：`setup.py`、`.github/CONTRIBUTING.md`、`docs/installation.rst`、`docs/releasenotes/4.1.0.rst:50-75`、`docs/reference/Image.rst:205-225`、`docs/releasenotes/9.1.0.rst`、`docs/releasenotes/9.2.0.rst`、`CHANGES.rst`。
- 源码：
  - `src/PIL/Image.py`：`_new`、`__eq__`、`load`、`convert` 的相关片段、`copy`、`quantize` 片段、`getpalette`、`putpalette`、`putpixel`、`remap_palette`、`new`。
  - `src/PIL/ImagePalette.py:1-255`。
  - `src/PIL/GifImagePlugin.py:440-935`、`:975-1000`。
  - `src/_imaging.c:1060-1112`、`:1636-1740`。
  - `src/libImaging/Palette.c:24-80`、`src/libImaging/Storage.c:71-75`、`src/libImaging/Unpack.c:583-600`、`src/libImaging/Convert.c:1100-1160` 与 `:1220`；`Unpack.c` 和 `Pack.c` 的格式对照表只 grep 了相关行。
- 测试：
  - `Tests/test_image.py:1-40`、`:590-640`。
  - `Tests/helper.py`：开头、`:75-112`、`:230-245`、`:315-320`。
  - `Tests/test_image_putpalette.py`、`Tests/test_image_getpalette.py` 全文。
  - `Tests/test_file_gif.py` 的片段：`:118-200`、`:580-700`、`:975-1160`。
  - `Tests/test_imagepalette.py` 只 grep 了相关行。

没有查的：

- 其它插件（PNG、TIFF 等）里的调色板处理。
- 完整的公开测试套件。
- 调色板读写与格式转换以外的 C 代码。
- 按角色卡不能看的材料：隐藏测试 `r2e_tests/`、`install.sh`、`.venv` 内容、编译扩展、`.git`。

限制：

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获的模型实际消息。
- 工作树不是完整的运行容器。
- 本记录没有运行任何项目代码，没有验证模型实际收到的内容、运行资源或开发条件；所有预计输出都是静态推断。
- 本上下文没有读过本题的私有材料、gold 补丁、隐藏测试或旧的审查结论。
