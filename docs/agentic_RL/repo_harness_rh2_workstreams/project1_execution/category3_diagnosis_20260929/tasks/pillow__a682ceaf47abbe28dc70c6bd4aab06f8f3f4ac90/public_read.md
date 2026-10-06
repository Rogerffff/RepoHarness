# 公开读者报告：pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90

- 角色：R2E 公开读者（单题、干净上下文），按 `r2e_lifecycle_20260929/roles/public_reader_r2e.md` 执行。整理日期：2026-09-30。
- 依据：本题公开包 `runs/category3_cloud_20260929/pillow_a682/public/`（下文路径都相对这个目录）；base 提交 `7a1e28404`，Pillow `10.1.0.dev0`。
- 状态：**只读分析，没有执行任何命令**。本文和同目录 `commands.json` 里的命令都是“建议，未执行”；下文所说的“修复前 / 修复后预计”都是读代码得出的推断。

## 0. 结论摘要

- **题面要求**：一张 RGB 图的 `info["transparency"]` 是 RGB 元组，而且量化成调色板后没有空位留给透明色。这时保存 GIF 不应再抛 `TypeError`，而应**不带透明度**地正常保存。
- **从 base 源码能完整读出这个报错**。`Image.convert` 发现调色板已满，就从转换后的副本里删掉透明度，并发出 UserWarning。但单帧写入路径把**原图** `im` 交给 `_write_local_header`。它回退读取原图 `info` 里的元组，`int(tuple)` 抛出 `TypeError`，而那里只捕获 `KeyError, ValueError`（`worktree/src/PIL/GifImagePlugin.py:559, 686-691`）。
- **开发条件**：相关代码都是纯 Python（`GifImagePlugin.py`，可能还有 `Image.py`），改完不需要重建 C 扩展，也不需要联网或装包。
- **主要未知**（影响验收，不妨碍开发）：
  - 元组通过 `save(transparency=...)` 关键字传入时，是否也算题目范围。
  - 保存时应不应该保留 base 会出现的 UserWarning。

## 1. 需求表

性质分三档：**明示**（题面直接写了）、**可推知**（从公开代码、测试、文档能合理推出）、**多解释**（公开材料不足以确定）。

| 编号 | 行为 | 性质 | 依据 |
| --- | --- | --- | --- |
| R1 | 题面例子（256×1 RGB，256 种互不相同的红色，`info["transparency"] = (255, 255, 255)`）调用 `im.save("*.gif")` 不再抛异常 | 明示 | `user_prompt.txt:3-24`；base 报错点 `worktree/src/PIL/GifImagePlugin.py:686-691` |
| R2 | 该情形保存的 GIF 不使用透明度。可观测形式：重新打开后 `info` 里没有 `"transparency"` 键（加载器只在图形控制扩展的透明标志置位时才写这个键） | 明示（"saved without using transparency"）；可观测形式从代码推知 | `user_prompt.txt:20-21`；`GifImagePlugin.py:206-213, 387-392`；`worktree/docs/handbook/image-file-formats.rst:158-160` |
| R3 | 像素照常量化、写入，不因修复丢帧或出错 | 可推知（题面只说 "should be saved"） | 单帧写入流程 `GifImagePlugin.py:546-564` |
| R4 | 元组透明色**能**分到调色板索引时（如 1×1 图，调色板有空位），保存后仍带透明度。不能把“元组一律丢弃”当成修复 | 可推知（公开测试） | `worktree/Tests/test_file_gif.py:1089-1098`（`test_rgb_transparency` 单帧部分）；`worktree/src/PIL/Image.py:1027-1029`；`GifImagePlugin.py:548-549, 686-687` |
| R5 | 整数索引透明度的既有行为不变：<br>① 显式 `transparency=` 在调色板优化后重映射索引<br>② `info` 里的整数透明度触发 GIF89a<br>③ RGBA 归一化产生的透明索引<br>④ 多帧透明索引重映射<br>⑤ RGB 图的 `bytes` 透明度在多帧保存时告警并丢弃 | 可推知（公开测试） | `test_file_gif.py:1069-1086, 1010-1037, 1293-1300, 737-750, 1100-1108`；`GifImagePlugin.py:485-489, 697-703, 914-924` |
| R6 | `Image.convert` 在 RGB→P（ADAPTIVE）且元组透明色分配失败时“发 UserWarning 并删除透明度”，这个行为保持不变 | 可推知（公开测试）；只在修复改动 `convert` 时相关 | `worktree/Tests/test_image_convert.py:190-192`；`Image.py:1027-1034` |
| R7 | 元组通过 `save(..., transparency=(r, g, b))` 关键字传入（而不是放在 `info`）时，是否也应不报错 | 多解释：题面说 "the `transparency` attribute"，例子用的是 `info`；文档把这个保存选项定义为颜色索引 | `user_prompt.txt:5-6, 16`；`image-file-formats.rst:246-247`；base 在这种情况同样会走到 `GifImagePlugin.py:686-690` 抛 `TypeError`（推断） |
| R8 | 保存时应不应该有警告 | 多解释：题面只要求 "no exception"；base 在该情形会先由 `convert` 发出 "Couldn't allocate palette entry for transparency" | `Image.py:1034`；`user_prompt.txt:21` |
| R9 | `save_all=True` 但只有一帧时同样应修好 | 可推知：这种情况回落到同一个单帧写入函数；两帧及以上在 base 本来就不报这个错 | `GifImagePlugin.py:628-649, 664-665`（多帧路径用归一化后的帧：587, 596-597, 643, 970-975） |
| R10 | 旧接口 `getdata()` 遇到 RGB + 元组透明度 | 多解释，属边缘情况，不在题面范围 | `GifImagePlugin.py:1018-1048` 直接把传入图交给 `_write_local_header` |
| R11 | 文件版本（87a/89a）、是否写图形控制扩展块 | 未约定 | `GifImagePlugin.py:712-726, 914-924`；`image-file-formats.rst:113-115` |

## 2. 合理实现范围

**应接受的实现**（在题面例子上可观察结果相同：不报错、重新打开后无透明度）：

1. 局部图像头写入对“不是整数调色板索引的透明度值”宽容，视为无透明度。
2. 单帧写入以“模式归一化之后仍然存在的透明度”为准。归一化已经删掉了透明度，就不再回退读取转换前原图 `info` 里的元组。
3. 如果归一化后的调色板里能**精确**找到这个 RGB 颜色，就用它的索引，找不到才放弃。这与 base `convert` 的既有语义一致（`Image.py:1027-1029`），也满足 R1/R2：例子里的 `(255, 255, 255)` 不在红色渐变调色板中。

以上几类只在 R7、R8、R10 这些未约定情形下表现不同。例如只做第 2 类，关键字传元组（R7）时可能仍然报错；做第 1 类则会静默忽略。

**与明示要求冲突、不应接受的实现**：

- 想办法保留透明度（例如少量化一色，腾出一个索引）。功能上也许更好，但和 "saved without using transparency" 冲突。
- 改为抛出更清晰的异常：和 "no exception should be raised" 冲突。
- 对所有元组透明度一律丢弃：破坏 R4，公开测试 `test_rgb_transparency` 能发现。
- 改变 `convert` 的告警或删除语义：破坏 R6，公开测试 `test_trns_RGB` 能发现。

**公开测试能暴露的实现风险**：

- 如果把单帧路径改成把“已归一化、已重映射调色板的图像”交给 `_write_local_header`，那么 `GifImagePlugin.py:697-703` 的优化重映射会作用在已经重映射过的图像上，透明索引可能错位。`test_transparent_optimize`（`test_file_gif.py:1069-1086`）能发现这类回归。
- 过宽的异常捕获可能掩盖其它错误类型。这是代码风格问题，不作为判定依据。

**命名、输出、默认行为**：

- 不需要新增公开参数或函数，也没有必须使用的名字。
- 题面没有规定提示文字。默认行为是静默不写透明度。
- 是否保留 base 在这条路径上发出的 UserWarning，题面没有约定。最保守的做法是不改 `convert`，让警告与 base 一致。如果评测测试断言“有警告”或“无警告”，改动警告的实现就可能结果不同。这是一个条件性风险，不是对隐藏测试内容的判断。
- 工作树里的 `run_tests.sh:1` 以 `-W ignore` 和 `PYTHONWARNINGS=ignore::UserWarning,...` 运行，所以多出来的警告本身不会让测试失败。但按 pytest 的一般行为，`pytest.warns` 在自己的上下文里仍会记录警告。

## 3. 题面质量与初态线索

### 3.1 是否直接给出或强烈暗示修法

- 没有给出修法。示例是出错的用法（`user_prompt.txt:8-18`），不是修好后的实现。
- "Expected Behavior" 规定了结果：丢弃透明度、不抛异常。对这个问题，“保留透明度 / 报清晰错误 / 丢弃透明度”都是可能的产品选择，题面选定了其中一种。这是有用的行为规格，没有泄漏修改位置。
- 题面没说明触发前提（调色板已满、`convert` 已经丢掉透明度），也没点出根因（单帧路径回读原图 `info`）。这两点正常读代码就能得到。

### 3.2 题面描述的报错能否从 base 源码读出

能。调用链如下：

1. `Image.save` 设置 `self.encoderinfo = params`（`Image.py:2378-2380`），调用 GIF 插件的 `_save`；非 `save_all` 时进入 `_write_single_frame(im, fp, palette)`（`GifImagePlugin.py:664-665`）。
2. `_normalize_mode(im)`（547）对 RGB 图调用 `im.convert("P", palette=Image.Palette.ADAPTIVE)`（483-484）。
3. `convert` 先用 `_new` 复制原图 `info`（`Image.py:517`），把元组换算成 `trns`（966-1003）。量化后执行 `new.palette.getcolor(trns, new)`（1027-1029）。失败时删掉**副本**的 `transparency`，并 `warnings.warn("Couldn't allocate palette entry for transparency")`（1030-1034）。原图 `info` 不受影响。
4. `getcolor` 什么时候失败：调色板 256 项已满、而且直方图里没有未用索引（`worktree/src/PIL/ImagePalette.py:129-147`）。量化结果的调色板总是按 256 项返回（`worktree/src/_imaging.c:1123`、`worktree/src/libImaging/Palette.c:43`、`worktree/src/libImaging/Quant.c:1828-1845`）。
   - 例子是 256 个像素、256 种互不相同的颜色，量化后很可能 256 个索引全被占用，于是分配失败。这是推断，未执行。
   - 公开测试 `test_image_convert.py:190-192` 在 hopper 照片上断言了同一种“分配失败 → 警告并删除透明度”的行为。
5. 回到 `_write_single_frame`：归一化后的 `im_out.info` 已经没有 `transparency`，548-549 行的 `setdefault` 不会写入这个键。但 559 行 `_write_local_header(fp, im, (0, 0), flags)` 传入的是原图 `im`。
6. `_write_local_header` 在 `encoderinfo` 里找不到这个键，就回退到 `im.info["transparency"]`（686-689），也就是 `(255, 255, 255)`。690 行 `int(transparency)` 抛 `TypeError`，而 691 行只捕获 `KeyError, ValueError`。
7. 报错文本 "int() argument must be a string, a bytes-like object or a number, not 'tuple'" 是 CPython 3.9 及以前的措辞（3.10 起改为 "a real number"）。环境是 3.9.21（`environment_brief.md:6`），与题面一致。
8. 附带现象：出错前全局头已经写出（552-553）。`Image.save` 捕获异常后会关闭并删除新建的文件（`Image.py:2412-2422`）。

对照：`test_rgb_transparency` 的单帧用例（1×1 图）在 base 能通过。原因是那里 `convert` 分配成功，`im_out.info` 里是整数索引，经 548-549 行进入 `encoderinfo`，`_write_local_header` 走 686-687 行的分支。所以 base 的问题只出现在“分配失败”这一支。

### 3.3 题面示例在 base 接口下是否说得通

说得通：`Image.new`、`putpixel`、`info` 字典、按扩展名保存 GIF，在 base 都存在。两点小瑕疵：

- `user_prompt.txt:12-17` 只**定义**了函数 `save_gif_with_tuple_transparency()`，没有调用。原样粘贴运行不会有任何输出或异常，需要自己补上调用。
- 示例把 `temp.gif` 写到当前目录，在 `/testbed` 下会留下一个未跟踪文件。命令清单改写到了 `/tmp`。

### 3.4 措辞与遗漏

- `user_prompt.txt:6` 把 `int()` 的报错复述成“保存流程期望 string、bytes 或 number”，这不是 Pillow 的接口约定：
  - 文档里 GIF 的 `transparency` 是调色板索引（`image-file-formats.rst:158-160, 246-247`）。
  - base 对能换算的 RGB 元组本来就支持（`Image.py:966-1003, 1027-1029`）。
  - 这句话可能把人引向“把元组转成数字”这类方向。
- `user_prompt.txt:5` 的 "the `transparency` attribute" 没有区分 `info` 键和 `save()` 关键字，见 R7。
- 题面没说“元组透明度在调色板有空位时本来能用”，"saved without using transparency" 容易被推广成“元组一律丢弃”（R4）。
- 题面没提到 base 在这条路径上会先出现一条 UserWarning（R8）。

### 3.5 `public_hints` 分类（`public_bundle.json:12`，`user_prompt.txt:28-33`）

- **题目需求**：修复这个 issue，修改的是非测试源码（"edit NON-TEST source files to fix the issue"）。
- **给解题者的操作指令**：
  - 先探索代码、找根因。
  - 不要修改仓库测试文件。
  - 测试跑得窄一些，在 `/testbed` 用 `python -m pytest`。
  - 有把握后简短总结并停止调用工具。
- **环境事实声明**：
  - 仓库在 `/testbed`；`.venv` 已是 `python` 和测试工具的指向。
  - 无网络；`pip` 可能不可用；只能用已装的包。
  - "the fix is judged by a separate set of tests"（评测事实）。
- **对合法解法的影响**：
  - 本题修改点是纯 Python，不需要联网、装包或重建。
  - 不许改测试文件，不妨碍在 `/tmp` 写临时脚本验证。
  - 这些环境声明与 `environment_brief.md` 一致：Python 3.9.21 venv、pytest 8.3.4 已核实；pip 是否可用未核对，与“may be unavailable”不矛盾。

### 3.6 初态线索与缺失信息

- **复现入口**：题面例子，补上调用、改写到 `/tmp`。traceback 会直接指向 `GifImagePlugin.py:690`。
- **调查入口**：
  - `_write_single_frame`（`GifImagePlugin.py:546-564`）
  - `_normalize_mode`（469-491）
  - `_write_local_header`（683-746）
  - `Image.convert` 的 ADAPTIVE 分支（`Image.py:1017-1035`）
  - 对照用的多帧路径：`GifImagePlugin.py:577-649, 970-983`
  - 元组透明度的真实来源之一：带 tRNS 的 RGB PNG（`worktree/src/PIL/PngImagePlugin.py:471`）
- **相关公开测试**：`Tests/test_file_gif.py` 的 `test_rgb_transparency`、`test_transparent_optimize`、`test_version`、`test_saving_rgba`、`test_remapped_transparency`，以及 `Tests/test_image_convert.py::test_trns_RGB`。仓库**没有**覆盖“调色板已满 + 元组透明度 + 保存 GIF”的现成测试，公开测试只能发现回归。
- **工作树初态**：
  - `install.sh`、`run_tests.sh` 是未跟踪的构建文件，与题意无关。
  - `run_tests.sh` 指向工作树里不存在的 `r2e_tests` 目录（评测用），解题用不到。
  - `worktree/` 没有 `.git`，无法比对是否还有其它初态改动；`environment_brief.md:5` 只列了这两个未跟踪文件。
- **真正阻碍开发的缺失信息**：没有。只影响验收判断的未知：R7、R8，边缘上还有 R10。

## 4. 开发需求表

所有命令都是**建议，未执行**；完整命令和预期写在同目录 `commands.json`。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令与预期 |
| --- | --- | --- | --- | --- |
| Python 解释器与可编辑安装的 PIL | `worktree/install.sh:19-22` | 已核实：CPython 3.9.21；`import PIL` 得到 10.1.0.dev0，来自 `/testbed/src` | 无 | `env_import_version`：打印版本和路径，退出码 0，修复前后相同 |
| C 扩展（量化、GIF 编码器） | `src/_imaging.c`、`src/libImaging/Quant.c`、`GifEncode.c` | 已核实：C 扩展由 `install.sh` 构建，只改 Python 无需重建；离线能否重建未核对 | 本题修改点是纯 Python，无实际缺口；若有人改 C 源码，离线重建未验证 | `env_import_version` 打印 `Image.core.__file__` 和 `gif_encoder` 是否存在；不需要构建命令 |
| 题面复现 | `user_prompt.txt:8-24` | 不依赖外部资源 | 题面例子缺调用、写当前目录，命令里已补上调用并改写 `/tmp` | `repro_issue_example`：修复前退出码 1，打印 `BASE BUG REPRODUCED: TypeError: ...`，位置 `GifImagePlugin.py` 第 690 行，并伴随 convert 警告；修复后退出码 0，`transparency in reloaded info: False` |
| 边界探针（R4、R7、R9 与真实 PNG） | `GifImagePlugin.py`、`Image.py` 的读码结论；`Tests/images/hopper.ppm`、`rgb_trns.png` | 资产在工作树中（已对照 manifest） | R7 和 F 用例的结果题面没有约定 | `probe_tuple_transparency_boundaries`（expect any），逐项预期见 `commands.json` |
| 公开测试 | `worktree/conftest.py`（`pytest_plugins = ["Tests.helper"]`）、`Tests/conftest.py`、`Tests/helper.py` | 已核实：pytest 8.3.4 可用，测试在 `Tests/` | `Tests/helper.py` 需要 `packaging`（pytest 8 的依赖，brief 没有单列）；两个 netpbm 测试在缺工具时会 skip | `pytest_gif_file`、`pytest_image_convert_file`：修复前后都预计通过 |
| 网络 / pip / uv | 解题不需要 | 无网络；pip 未核对 | 对本题无影响 | `env_import_version` 顺带打印 pip / uv 是否可用，不影响退出码 |

## 5. 阅读范围

**实际打开的文件**（`worktree/` 下，除注明外均为只读查看）：

- 角色卡本身；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `worktree_manifest.json`：只看了结构、`excluded` 两项，并用脚本比对文件清单与 `worktree/` 实际文件（1615 个，一致）。没有打开它指向的外部路径。
- 构建与配置：`install.sh`、`run_tests.sh`、`pyproject.toml`、`conftest.py`、`setup.cfg`、`tox.ini`、`.gitignore`（前 40 行）、`CHANGES.rst`（前 60 行）、`src/PIL/_version.py`（grep）。
- `src/PIL/GifImagePlugin.py`：1-130、185-410、460-760、795-1064 行。
- `src/PIL/Image.py`：500-524、860-1094、2328-2431 行。
- `src/PIL/ImagePalette.py`：`getcolor`，105-165 行。
- `src/PIL/PngImagePlugin.py`：只 grep 了透明度赋值行（463-471）。
- `src/_imaging.c`：`_getpalette`，1100-1143 行。
- `src/libImaging/Quant.c`：1285-1320、1400-1490、1810-1865 行。
- `src/libImaging/Palette.c`：grep。
- `Tests/test_file_gif.py`：函数索引，加 1-35、586-755、890-920、1005-1130、1225-1301 行。
- `Tests/test_image_convert.py`：函数索引，加 1-45、105-224 行。
- `Tests/conftest.py`；`Tests/helper.py`（导入、`hopper`、`netpbm_available`）。
- `docs/handbook/image-file-formats.rst`：108-257 行。

**没查的范围**：

- 其它插件的保存路径、`ImageFile._save`、C 的 GIF 编码器。
- 中值切分量化是否对 256 种颜色恰好产生 256 个互不相同的调色板项：只做了推断。
- `Tests/` 的其它文件；`worktree/` 没有 `.git`，所以没有看提交历史。
- 按规则没有查询上游仓库、PR 或后续提交，也没有读取公开包以外的任何路径、隐藏测试或旧审查结论。
- 本上下文没有接触私有材料。模型可能从训练中带有对 Pillow 项目的一般背景知识，无法完全排除；本文每条判断都附了公开依据。

**保留的限制**：

- `user_prompt.txt` 只是静态渲染，模型实际收到的消息没有核实。
- `worktree/` 不是完整的运行容器（缺 `.venv/`、`.git/`）。
- 没有运行任何项目代码。运行资源、开发条件和各命令的实际结果都未验证，全部待负责人在一次性容器里照跑 `commands.json` 后确认。

## 6. 命令清单（`commands.json`，共 5 条，均为建议，未执行）

| id | expect | 要看什么 |
| --- | --- | --- |
| `env_import_version` | zero | 解释器、PIL 版本和路径、C 扩展是否加载；pip / uv 是否可用（仅作信息） |
| `repro_issue_example` | nonzero | 题面例子。修复前退出码 1（`TypeError` 出现在 `_write_local_header` 第 690 行）；修复后退出码 0，重新打开后无透明度；退出码 2 或 3 表示其它情况 |
| `probe_tuple_transparency_boundaries` | any | 6 个边界用例：`save_all` 单帧、hopper 照片、调色板有空位的小图（必须保留透明度）、关键字传元组、两帧、真实 tRNS PNG |
| `pytest_gif_file` | zero | `Tests/test_file_gif.py` 全部，修复前后都应通过，用于发现回归 |
| `pytest_image_convert_file` | zero | `Tests/test_image_convert.py` 全部，重点是 `test_trns_RGB` 约束的 `convert` 告警与删除语义 |
