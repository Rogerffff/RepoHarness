# 公开读者记录：pillow__4bc6483564ae1a254911e98280b9a501f047a2e0

- 角色：R2E 公开读者（单题闭环试行，2026-09-29），使用干净上下文。只读了角色卡和本题公开包，没有接触私有材料。
- 路径约定：下文路径都相对于本题公开包 `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`。`worktree/…` 就是解题者在 `/testbed` 下看到的同名文件；为简洁，表格里常省略 `worktree/` 前缀。
- 证据性质：全部来自静态读码，没有运行任何项目代码。文中所有“运行时会……”都是读码推断，需要用同目录的 `commands.json` 在真实环境核实。

## 摘要

- **报错来源**：题面报错能从 base 源码逐行读出。`ImageOps.invert` 构造好查找表后交给 `_lut`；`_lut` 只处理 "P"、"L"、"RGB" 三种模式，"1" 会落到 `raise OSError("not supported for this image mode")`（`src/PIL/ImageOps.py:49-58, 518-528`），异常类型和消息都与题面一致。复现入口和调查入口都很清楚。
- **关键未知一（开发条件）**：`.venv` 里的 Pillow 是否从 `/testbed/src` 以可编辑方式安装，公开材料无法判断，因为 `install.sh` 没有随工作树提供。如果不是可编辑安装，改 `src/PIL/ImageOps.py` 不会影响 import 和测试，而环境里没有 pip，无法重装。用 `env_pil_import` 核实。
- **关键未知二（验收语义，R8）**：题面示例 `Image.new("1", (128, 128), color=1)` 在 base 里每个像素存成原始字节 1，而不是 255。
  - 按 1-bit 语义（非零即白），这张图是全白。
  - 如果实现是“255 − v”或按位取反，字节 1 会变成 254，按 1-bit 语义仍是全白，看起来没有反相。
  - 如果实现先把非零归一为白再反相，结果是全黑。
  - 题面没有规定输出像素值；隐藏测试取哪种，公开材料无法判断。
- **次要未知（R9）**：其它共用 `_lut` 的函数（autocontrast、equalize、posterize、solarize）是否也应接受 "1"。题面没有要求，公开测试也没有约束。

## 1. 需求表

“类别”一列取值：明示；可从公开仓库合理推知；仍有多种合理解释（简称“多解”）。

| 编号 | 行为 | 类别 | 依据 |
| --- | --- | --- | --- |
| R1 | 对 mode "1" 图调用 `ImageOps.invert` 不再抛错，尤其不再抛 `OSError: not supported for this image mode` | 明示 | `user_prompt.txt:3-6, 13-16, 19-26`；base 的代码路径 `ImageOps.py:525-528` → `49-58` |
| R2 | 结果是反相后的二值图：对规范像素（0 = 黑，255 = 白）做黑白互换 | “成功反相”是明示；具体取值可推知 | `user_prompt.txt:20`；docstring “Invert (negate) the image.”（`ImageOps.py:520`）；1-bit 约定见 `src/libImaging/Pack.c:85`（“black is 0”）、`Unpack.c:112`（“white is non-zero”）；查到的解码与转换路径写入 "1" 图时都只产生 0/255（`Unpack.c:117, 253`；`Convert.c:117, 228, 1484, 1515`） |
| R3 | 输出仍为 mode "1"，尺寸不变；返回新图，不修改输入 | 可推知 | `_lut` 返回 `image.point(lut)`（`ImageOps.py:56`），`point` 的输出模式默认与输入相同（`Image.py:1696`；`Point.c:143-155`）；L、RGB 反相同样保持模式；TIFF 调用方用反相结果替换 `im` 后按原模式写盘（`TiffImagePlugin.py:1666-1675`） |
| R4 | 保留：L、RGB 反相仍是逐通道 `255 - v`，模式不变 | 可推知；公开测试只做冒烟 | `ImageOps.py:53-56, 525-528`；`Tests/test_imageops.py:66-67` 只检查不抛错 |
| R5 | 保留：其它共用 `_lut` 的函数对 L、RGB 的现有结果不变 | 可推知；公开测试部分覆盖 | `ImageOps.py:153, 237, 383, 553, 570`；`Tests/test_imageops.py` 中 colorize、autocontrast、equalize 各用例 |
| R6 | 若改动 TIFF 调用方：mode "1"/"L" 用 `tiffinfo={262: 0}` 保存后读回，仍逐像素相等 | 公开测试 | `Tests/test_file_tiff.py:483-490`；`TiffImagePlugin.py:1664-1675` |
| R7 | 对其它模式调用 `invert` 的行为（"P" 目前抛 `NotImplementedError`；RGBA、LA、I、F、CMYK 等目前抛 `OSError`） | 多解：题面未涉及，保持现状或扩展都说得通 | `ImageOps.py:50-52, 57-58`；`docs/reference/ImageOps.rst:7-9`（“most operators only work on L and RGB images”） |
| R8 | "1" 图中既非 0 也非 255 的非零字节（题面示例 `color=1` 就会产生字节 1）反相后应得到什么 | 多解，且直接关系到题面示例 | 见下方说明 |
| R9 | autocontrast、equalize、posterize、solarize 是否也应接受 "1"（colorize 在 `ImageOps.py:181` 断言输入为 "L"，不涉及） | 多解 | 标题和描述只点名 `invert`（`user_prompt.txt:3-6`）；但 `user_prompt.txt:20` 的 “allowing operations on images with mode "1"” 措辞宽泛；`Tests/test_imageops.py` 唯一的 `pytest.raises` 在 146 行，检查的是 `ValueError`，没有任何用例期望这些函数对 "1" 抛 `OSError` |
| R10 | 只改非测试源码，不改仓库测试文件 | 明示（操作指令） | `public_bundle.json:15`（public_hints） |

**R8 的依据：**

- **字节 1 的来源**：`Image.new` 调用 `core.fill`（`Image.py:2785`）；`getink` 对单波段 8 位图只做 `CLIP8`，不对 "1" 归一（`_imaging.c:525-538`）；`ImagingFill` 按原始字节填充（`Fill.c:53-57`）；`getpixel` 返回原始字节（`_imaging.c:458-459`）。
- **仓库对这类值的既有处理并不一致**：
  - 逻辑运算把非零当白，输出 0/255（`Chops.c:116-128`）。公开测试 `Tests/test_imagechops.py:408-428` 把 1、128、255 都当作“开”。
  - TIFF 保存时的手写反相只把 255 当白（`TiffImagePlugin.py:1672`）。字节 1 会被写成 255，仍是白。

## 2. 合理实现范围

以下几类做法只要满足 R1–R6，都应被接受。

**改动位置：**

1. **放宽共享的 `_lut`**，让 "1" 走 `Image.point`。读码看，`Image.point`（`Image.py:1719-1723`）→ `_point`（`_imaging.c:1413-1451`）→ `ImagingPoint`（`Point.c:143-166`）在不指定输出模式时，不限制单波段 8 位图，包括 "1"。所以阻断点只在 Python 层的模式白名单。副作用是 R9 的几个函数对 "1" 也不再抛错，结果可能出现非 0/255 的原始字节。
2. **只在 `invert` 里对 "1" 特判**，其余函数保持现状。
3. **复用现有原语**。例如 `ImageChops.invert`（`ImageChops.py:39-51` → `Negative.c:35-39`，逐字节按位取反），或者先转成 "L" 再转回 "1"。
4. **在 C 层实现**。功能上可行，但需要重编译扩展，环境说明没有给出构建条件（见第 4 节）。

**语义差异：**

- **规范输入（只含 0/255）**：上面各做法结果一致，都是 0↔255，打包后逐位取反。
- **非规范的非零字节（R8）**，结果分三类：
  - “255 − v”或按位取反：得到 254，按 1-bit 语义仍是白（`Pack.c:89`、`Convert.c:58-61`）。
  - 先把非零归一为白再反相，或经 "L" 中转：得到 0。
  - 仿照 TIFF 手写逻辑、只把 255 当白：得到 255，仍是白。

  公开材料无法确定验收取哪一类。如果按“题面示例应被成功反相”来读，第一类和第三类会让示例图保持全白。
- **输出字节取值**：有的实现可能输出 0/1 而不是 0/255。按 `tobytes`、`convert` 的 1-bit 语义两者等价，但与仓库“写入 1 模式图时只产生 0/255”的惯例不一致。公开材料没有规定原始字节值。

**命名、输出与默认行为：**

- 不需要新 API 或新参数，`invert(image)` 的签名不变。
- 输出模式应为 "1"。这是 R3 的推断，没有明文约定。
- 仍不支持的模式抛什么异常、带什么消息，没有约定。
- 是否更新文档（`docs/reference/ImageOps.rst:7-9`）和 `CHANGES.rst` 不属于功能要求。

**有风险或不宜接受的做法：**

- 对 "1" 输入返回 "L" 图，与 R3 的推断冲突。
- 原地修改输入图。
- 修改 `Tests/` 下的测试，public_hints 明确禁止。

公开材料能支持的替代实现就是上面这些。标准答案具体取哪一种，本记录不猜测。

## 3. 题面质量与初态线索

### 3.1 题面质量

1. **是否给出或强烈暗示修法**：题面没有给出修复代码，示例代码只是复现。`user_prompt.txt:6` 说 “indicating that this image mode is not supported for inversion”，加上报错消息，指向“模式白名单”这个位置。这属于正常的定位线索，不算泄露实现。
2. **题面描述的报错能否从 base 源码读出**：能。
   - `Image.new("1", (128, 128), color=1)` 在 base 可以正常创建（`Image.py:2749-2785`；`_imaging.c:604-634`）。
   - `ImageOps.invert` 构造 256 项查找表后调用 `_lut`（`ImageOps.py:525-528`）。"1" 既不是 "P"，也不在 ("L", "RGB") 中，于是落到 `ImageOps.py:57-58`。异常类型和消息都与 `user_prompt.txt:22-26` 一致。
3. **示例在 base 接口下是否说得通**：说得通，两个调用的签名都与 base 一致。但有一处会影响验收的细节：
   - 示例用 `color=1` 建图，base 里按原始字节 1 存储（见 R8），不是解码或转换产生的 255。
   - 题面的 Expected Behavior 只说 “successfully invert … without raising an error”（`user_prompt.txt:20`），没有给出输出像素。
   - 结果是：对这张示例图，不同的合理实现会得到“看起来仍全白”或“全黑”两种输出，题面本身不足以定义正确输出。

### 3.2 public_hints 分三类（`public_bundle.json:15`）

- **题目需求**：“Explore the code, find the root cause, and edit NON-TEST source files to fix the issue.”
- **给解题者的操作指令**：
  - 不改仓库测试文件；
  - 测试范围要窄，只跑单个文件或模块；
  - 在 `/testbed` 下用 `python -m pytest` 跑；
  - 完成后简短总结并停止调用工具。
- **环境事实声明**：
  - bash 已经在 `/testbed` 下；
  - `python` 和测试工具都指向 `/testbed/.venv`；
  - 没有网络，`pip` 可能不可用；
  - 修复由另一组测试判定。

  `environment_brief.md:10-12` 更具体：pip、pip3、uv 都不在 PATH；解题身份是 uid 54321；资源为 2 CPU / 4 GiB；`/tmp` 为 1 GiB。与 hints 不冲突。
- **对合法解法的影响**：
  - 不能改 `Tests/`，意味着回归测试不能加进仓库测试文件，但不影响修复本身。
  - 没有 pip，就不能重装包。如果 Pillow 不是可编辑安装，“改完即测”会失效（见关键未知一）。
  - 纯 Python 修改不需要构建；改 C 源码需要重编译，环境没有说明编译条件。

### 3.3 初态

- `worktree_manifest.json:14-16` 显示 `initial_diff` 为 0 字节：镜像初态相对 base 没有改动。工作树就是 base 的跟踪文件，外加 `run_tests.sh`。
- `install.sh` 在镜像里存在，但没有随工作树提供（`worktree_manifest.json:20-32`），所以 Pillow 的安装方式未知。
- `run_tests.sh:1` 表明评分是在仓库根下运行 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests` 目录不在工作树里，是隐藏测试，内容不可见。
- 版本信息：`src/PIL/_version.py:2` 为 `9.1.0.dev0`；`CHANGES.rst:5` 为 “9.1.0 (unreleased)”。

### 3.4 调查入口（公开材料足够定位）

- 报错消息在 `src/PIL` 中只出现在 `ImageOps.py:58`。
- `_lut` 被 6 个函数共用：`ImageOps.py:153, 237, 383, 528, 553, 570`。
- `ImageOps.invert` 在源码中唯一的内部调用方是 `TiffImagePlugin.py:1675`。紧挨着的 `1667-1673` 对 "1" 模式手写逐像素反相，正是绕开本限制的现有代码。
- `ImageChops.invert`（`ImageChops.py:39-51`）是现成的按字节取反原语。
- 相关公开测试：
  - `Tests/test_imageops.py`：只对 L、RGB 做 invert 冒烟（66-67 行）；
  - `Tests/test_file_tiff.py:483-490`；
  - `Tests/test_imagechops.py:408-428`：体现 "1" 模式“非零即开”的约定。

### 3.5 缺失信息：哪些真正阻碍开发，哪些只需正常读代码

- **真正可能阻碍的**：
  - Pillow 的安装方式未知。这决定了修改能否生效，也决定了能否在本地验证。
  - 非规范像素的期望输出没有定义。这影响验收，不影响写出修复。
- **只需正常读代码的**：`_lut` 的结构和调用方、C 层 `point` 是否支持 "1"、mode "1" 按“每像素一字节、0/255”存储的约定（`Storage.c:66-69`、`docs/handbook/concepts.rst:32`）。这些都能在工作树里读到，不算题面缺陷。

## 4. 开发需求表

下表所有命令均为**建议，未执行**；可机读的版本见同目录 `commands.json`。命令都能在 `/testbed` 下原样运行，不联网、不装包、不改仓库文件：每条都设了 `PYTHONDONTWRITEBYTECODE=1`，pytest 带 `-p no:cacheprovider`，pytest 的临时文件写在 `/tmp`。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令 |
| --- | --- | --- | --- | --- |
| 导入 Pillow（含已编译的 `_imaging`） | `run_tests.sh:1` 用 `.venv/bin/python`；`Image.py:132` 导入 `_imaging` | 第 10 行：`python` 指向 `/testbed/.venv/bin/python`，版本 3.9.21 | 没有说明 Pillow 是否从 `/testbed/src` 可编辑安装；`install.sh` 不在工作树；工作树不含 `.venv` 和 `.so` | `env_pil_import` |
| 复现题面报错 | `user_prompt.txt:8-26`；`ImageOps.py:49-58` | 同上；只需核心模块，不需要编解码器或网络 | 无 | `repro_issue_example` |
| 核对 1-bit 反相语义 | `Unpack.c:111-117`；`Pack.c:83-102`；`Tests/images/hopper.ppm` 在工作树中 | 同上 | 非规范像素的期望没有定义（R8），因此命令只对规范输入做断言 | `check_mode1_invert_canonical` |
| 核对需要保留的行为 | `ImageOps.py:53-56, 525-528` | 同上 | 无 | `check_l_rgb_unchanged` |
| 运行公开测试 | `setup.cfg:66-68`（testpaths = Tests）；`conftest.py:1` 加载 `Tests.helper`；`Tests/helper.py:13-16` 需要 pytest 和 packaging；hints 要求用 `python -m pytest` | 没有列出已装的包；`run_tests.sh` 用到 pytest，说明至少装了 pytest | packaging 是否已装、JPEG 解码是否编入，都没有说明。`Tests/test_imageops.py:127-129, 310-314, 402` 会读 .jpg | `pytest_imageops`；改到 TIFF 时再跑 `pytest_tiff_photometric` |
| 临时文件 | pytest 的 `tmp_path` | 第 12 行：`/tmp` 1 GiB | 无 | — |
| 构建或重编译 C 扩展 | 仓库的构建方式都经 pip（`Makefile:49-51`、`tox.ini:17`） | 第 11 行：没有 pip / uv，也不能出网 | 改 C 源码时，是否有编译器、能否就地重建都没有说明。只改 Python 文件则不需要构建，前提是可编辑安装（见第一行） | 不提供；先跑 `env_pil_import` |
| 网络 | 本题不需要 | 不能出网 | 无 | — |
| 资源 | 只跑单个模块的测试 | 2 CPU / 4 GiB | 无 | — |

各命令在修复前后的预期（`expect` 以 base 状态为准）：

| id | expect | 修复前预计 | 修复后预计 |
| --- | --- | --- | --- |
| `env_pil_import` | zero | 打印 `.venv` 的 python 3.9.21、PIL 9.1.0.dev0、PIL 和 ImageOps 的文件路径（关键看是否在 `/testbed/src/PIL`）、`_imaging` 路径、jpg/zlib/libtiff 是否可用、pytest 和 packaging 的版本 | 与修复前相同 |
| `repro_issue_example` | nonzero | 先打印 `input: 1 (128, 128) raw getpixel: 1 extrema: (1, 1)`（读码推断），然后以 `OSError: not supported for this image mode` 结束，退出码 1 | 退出码 0，输出为 mode 1、(128, 128)。其余几行随实现不同：254 且按 1-bit 语义全白，或 0 且全黑。只作为判断 R8 的信息，不做断言 |
| `check_mode1_invert_canonical` | nonzero | 打印 `in: [255, 0, 255, 0, 0, 255, 0, 255]` 后抛 `OSError`，退出码 1 | 打印 `out: 1 (8, 1) …` 和 `OK: …`，退出码 0。断言只检查：打包后的位逐位取反、反相两次复原、输入没被修改、模式和尺寸不变；原始字节是否为 0/255 只打印，不断言 |
| `check_l_rgb_unchanged` | zero | `OK: L/RGB invert unchanged` | 与修复前相同；失败说明改动波及了 L/RGB |
| `pytest_imageops` | zero | 24 passed（静态计数） | 仍是 24 passed。这组用例不能区分修复前后，只用来防回归；如果修复前就因 jpeg 失败，属于环境问题 |
| `pytest_tiff_photometric` | zero | 2 passed（参数为 1 和 L） | 2 passed |

## 5. 阅读范围

**实际打开的文件**，全部在公开包内：

- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `worktree_manifest.json`：只看了顶层元数据（export、initial_diff、untracked_*、not_included）和条目格式；没有打开其中指向公开包以外的路径，例如 `initial_diff.source`。
- 工作树中的构建与配置文件：`run_tests.sh`、`conftest.py`、`setup.cfg`、`tox.ini`、`.gitignore`、`Makefile`（grep）、`CHANGES.rst:1-40`。
- Python 源码：
  - `src/PIL/_version.py`、`src/PIL/__init__.py`（grep）；
  - `src/PIL/ImageOps.py`：1-245、350-390、495-575 行；
  - `src/PIL/Image.py`：point、tobytes、getpixel、getextrema、new，以及 core 的导入；
  - `src/PIL/ImageChops.py:36-52`、`src/PIL/TiffImagePlugin.py:1640-1699`、`src/PIL/features.py`（codecs 与 check）。
- C 源码：
  - `src/_imaging.c`：getpixel、getink、`_fill`、`_point`、`_chop_invert`；
  - `src/libImaging/`：`Point.c` 与 `Negative.c` 全文；`Fill.c:1-80`；`Storage.c`、`Unpack.c`、`Pack.c`、`Convert.c`、`Chops.c`、`GetBBox.c` 的相关片段；`ImagingUtils.h`、`Access.c` 只用 grep。
- 测试：
  - `Tests/test_imageops.py` 与 `Tests/test_image_point.py` 全文；
  - `Tests/test_imagechops.py`：195-206、408-428 行；
  - `Tests/test_file_tiff.py`：1-40、475-504 行；
  - `Tests/helper.py`：1-40、75-140、238-258 行。
- 文档：`docs/reference/ImageOps.rst`、`docs/handbook/concepts.rst:32`。

**用 grep 扫过的**：`src/PIL` 和 `Tests` 中的 `ImageOps.invert`、报错消息、`_lut(`、photometric；`docs` 中关于 mode "1" 的描述。

**没有查的**：

- 其它插件和模块、上面以外的测试文件、完整文档、`selftest.py`；
- 不在工作树里的 `.venv`、编译产物、`install.sh`、隐藏测试 `r2e_tests`；
- 上游的后续提交和网络资料（按角色卡不查）。

**本记录的限制**：

- `user_prompt.txt` 只是静态渲染，不等于模型实际收到的消息；public_hints 另行注入。
- 工作树不是完整的运行容器。
- 本记录没有验证模型实际收到的消息、运行资源或开发条件。
- 所有运行时结论都是读码推断，例如“base 上示例图的 `getpixel` 返回 1”“`Image.point` 能处理 "1"”。

本次没有读到任何私有材料、隐藏测试、gold 补丁或审查结论。
