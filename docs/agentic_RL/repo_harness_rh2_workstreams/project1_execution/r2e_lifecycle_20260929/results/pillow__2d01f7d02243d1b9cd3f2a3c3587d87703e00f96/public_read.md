# 公开读者报告：pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96

- 角色与范围：R2E 公开读者（单题闭环试行 2026-09-29）。只读了角色卡和本题公开包；没有读私有材料、历史材料、其它题或审查结论；没有运行项目代码。
- 公开包（仓库相对路径）：`runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`。下文路径都相对这个目录；`worktree/` 对应解题容器里的 `/testbed`。为简洁，`TiffImagePlugin.py:N` 指 `worktree/src/PIL/TiffImagePlugin.py` 第 N 行。
- base：`5db0969f6f98`（`user_prompt.txt:1` 与 `public_bundle.json:9` 一致），Pillow `8.4.0.dev0`（`worktree/src/PIL/_version.py:2`）。
- 术语：标签 262 是 TIFF 的 `PhotometricInterpretation`（像素值的解释方式）。0 = `WhiteIsZero`（0 表示白），1 = `BlackIsZero`（0 表示黑）。rawmode 是 Pillow 对“文件里像素字节布局”的命名；packer / unpacker 是 C 层在内存像素与该布局之间转换的函数。
- 所有命令都是“建议，未执行”；机器可读版在同目录 `commands.json`。

## 摘要

1. **题面要求**：保存 `'1'` 或 `'L'` 模式的 TIFF 时，如果用户在 `tiffinfo` 里把 262 设为 0，写出的文件要保留 0。重新打开后 `tag_v2[262]` 应为 0，base 上读到的是 1。
2. **成因能从 base 源码直接读出**：`_save` 先把 `tiffinfo` 抄进 `ifd`（`TiffImagePlugin.py:1507-1517`），随后在第 1571 行用 `SAVE_INFO` 的值无条件覆盖；`'1'` 和 `'L'` 的值都是 1（`:1459-1460`）。未压缩和压缩（libtiff）两条写出路径都在这一行之后才分开，所以两条都受影响。
3. **最大的未定项是像素语义**：读取端把 photometric 0 当作“0 是白”，读入时反相（rawmode `'1;I'`、`'L;I'`，`:136-137`、`:160-161`）。如果修复只改标签，题面示例的全黑图重新打开后像素变成 255；如果写入时同时反相像素，读回仍是 0。题面只要求标签值，两种做法都满足题面文字；公开材料无法判断评分测试取哪一种。
4. **开发条件的关键未知**：PIL 是否从 `/testbed/src` 可编辑导入。`install.sh` 不在公开包，看不到安装方式；如果不是可编辑导入，改源码不会生效，环境里也没有 pip 可以重装。另一个未知是 libtiff 是否编译进来，它决定压缩路径能不能自测。命令 `env_import` 可以一次核对这两点。

## 1. 需求表

| 编号 | 场景 | 要求 | 依据 | 明确程度 |
| --- | --- | --- | --- | --- |
| R1 | `'L'` 图，未压缩，`tiffinfo={262: 0}` | 重新打开后 `tag_v2[262] == 0` | 题面 `user_prompt.txt:6-7,10-23,25-29`；成因 `TiffImagePlugin.py:1460,1507-1517,1571` | 明示 |
| R2 | `'1'` 图，同样设置 | 同 R1 | 题面标题和描述 `user_prompt.txt:4,7`，没有示例；`SAVE_INFO["1"]` 同样是 1（`:1459`），经过同一行覆盖 | 明示，但无示例 |
| R3 | `tiffinfo` 里没有 262 | `'1'`、`'L'` 仍写 1；其它模式仍按 `SAVE_INFO` 写 | `:1456-1478`；题面只针对“已指定 0” | 可合理推知 |
| R4 | 带 `compression=` 保存（走 libtiff） | 也保留 0 | 覆盖发生在路径分开之前（`:1571` 早于 `:1607` 的 libtiff 分支和 `:1710` 的未压缩分支）；libtiff 分支先取 `ifd` 里的值（`:1656-1681`，`:1675` 先到先得）；题面示例只用默认的未压缩，但没有限定压缩方式 | 可合理推知，未明示 |
| R5 | 其它模式（RGB、P、I;16 等）在 `tiffinfo` 里给 262 | 题面未涉及；base 一律覆盖 | 标题限定 `'1'`/`'L'`；若对 RGB 照写 0，读取表 `OPEN_INFO`（`:133-249`）没有对应的键，重新打开会报 `unknown pixel mode`（`:1305-1309`） | 可合理推知：保持旧行为 |
| R6 | 写 262=0 时的像素数据 | 题面未规定 | 读取端对 photometric 0 反相：`'1;I'`（`:136-137`；`worktree/src/libImaging/Unpack.c:145-151`）、`'L;I'`（`:160-161`；`Unpack.c:438-443`）；题面 Expected Behavior 只说标签（`user_prompt.txt:25-26`） | 多种合理解释 |
| R7 | 重存一个本身 262=0 的已打开 TIFF，不传 `tiffinfo` | 题面未涉及；base 写 1 | 未压缩路径只沿用分辨率、IPTC、Photoshop、XMP（`:1521-1533`）；libtiff 路径 `ifd` 里的值优先；公开测试注释写明 photometric 取自 `SAVE_INFO` 而不是原图（`worktree/Tests/test_file_libtiff.py:151-152`） | 多种合理解释 |
| R8 | `tiffinfo` 的其它写法：`ImageFileDirectory_v1/_v2`、`{262: (0,)}`、`{262: "WhiteIsZero"}` | 题面只演示 dict 加整数 | v1 在 `:1510-1511` 转成 v2；写入 `ifd` 时 `_setitem` 会拆开单元素元组（`:603-615`），并把枚举名换成数值（`:594`；`worktree/src/PIL/TiffTags.py:29-33,98-114`） | 可合理推知：从 `ifd` 取值时都已规整为 0；是否支持这些写法由实现决定 |
| R9 | `'1'`/`'L'` 给 0、1 以外的值（如 2） | 题面未涉及 | base 覆盖成 1；照写的话读取端没有对应的键（同 R5） | 多种合理解释（忽略、照写或报错） |

### public_hints 的三类内容（`public_bundle.json:15`）

- **题目需求**：修改非测试源码来修复问题；不得修改仓库测试文件，评分使用另一组测试。影响：`worktree/Tests/test_file_libtiff.py:151-152` 的注释在修复后会过时，但只能保留。该测试忽略 photometric，不需要改动。
- **给解题者的操作指令**：测试范围尽量窄（单个文件或模块），在 `/testbed` 下用 `python -m pytest` 运行；完成后简短总结，然后停止调用工具。这些指令不影响合法解法。
- **环境事实声明**：`/testbed/.venv` 已经是 `python` 和测试工具的环境；没有网络，`pip` 可能不可用。`environment_brief.md:10-12` 进一步说明 pip、pip3、uv 都不在 PATH。影响：纯 Python 修改不受限制；如果选择改 C 代码（例如新增 `'L;I'` 写出 packer），就必须重新编译扩展，而环境有没有编译器和头文件没有说明（见 §4）。

## 2. 合理实现范围

必须满足 R1、R2，且不改变 R3 的默认行为。在此前提下，下面这些差异都应被接受；题面没有依据排除其中任何一种。

- **判定口径**：在 `'1'`/`'L'` 下“不覆盖用户给的 262”，或“只接受 0（以及 1）”。对题面示例，两者结果相同。
- **像素处理（R6）**：
  - 只写标签：像素字节不变，读回时被反相。题面示例的全黑 `'L'` 图读回后 `getpixel((0, 0))` 为 255；全黑 `'1'` 图读回也是 255。
  - 写入时同步反相：读回像素与原图一致，仍为 0。
  - 实现约束：`'1'` 在 base 已有写出用的反相 packer `'1;I'`（`worktree/src/libImaging/Pack.c:105-124,547`）。`'L'` 没有 `'L;I'` 写出 packer（`Pack.c:552-555` 只有 `L`、`L;16`、`L;16B`）。所以要在 `'L'` 上反相，只能在 Python 层处理，或者改 C 代码后重新编译。
- **覆盖面（R4）**：修改点如果在两条路径分开之前，压缩与未压缩保存自然一致；如果只改未压缩路径，带压缩保存仍会写 1。题面没提压缩，但同一个函数、同一个标签，合理推知两者应该一致。
- **扩展行为（R5、R7、R9）**：保持 base 行为或适度扩大支持都说得通。但扩大到 RGB 等模式会写出 Pillow 自己读不回的文件，很难算合理。另外，多帧保存 `_save_all` 把同一个 `encoderinfo` 用于每一帧（`:1961-1983`）；如果对所有模式都放开 262，混合模式的多帧文件也会受影响。
- **命名、输出与默认值**：不需要新的公开 API、参数或报错文本。唯一可观察的结果是写出文件里的 262，以及 R6 涉及的像素。默认值不变（R3）。
- 我没有找不到替代做法的地方。真正无法从公开材料判断的，是评分测试在 R4、R6、R7 这些未规定处取哪一种。

## 3. 题面质量与初态线索

**题面是否给出或强烈暗示修法。** 题面没有给实现代码；示例是复现脚本，不是修好后的实现。它点名了标签 262、模式 `'1'`/`'L'` 和值 0，足以让解题者搜到写入点（`TiffImagePlugin.py:1571`），这属于正常的定位线索。标题把范围收窄到这两个模式和值 0，可能反映了修复提交的范围（R2E 题面由修复提交和测试生成），但没有透露像素怎么处理。

**描述的行为能否从 base 源码读出。** 能。链条是：`tiffinfo` 抄进 `ifd`（`:1508-1517`）→ 第 1571 行用 `SAVE_INFO` 的 `photo` 覆盖，`'L'` 的值是 1（`:1460`）→ 未压缩路径通过 `ifd.save(fp)` 写出（`:1711`）→ 读回 `tag_v2[262]` 为 1。这与 Actual Behavior（`user_prompt.txt:28-29`）一致。以上是静态推断，没有执行。

**示例在 base 接口下是否说得通。** 用到的接口都存在，用法也正确：`tiffinfo` 接受 dict（`worktree/docs/handbook/image-file-formats.rst:871-879`），`tag_v2` 的说明见同文件 `:824-829`。有三个小问题：

- 示例只定义了函数 `save_tiff_with_photometric()`，没有调用它（`user_prompt.txt:13-22`），原样运行不会输出任何内容。
- 示例把 `temp.tif` 写到当前目录，在 `/testbed` 下运行会留下未跟踪文件。下面的复现命令改为写 `/tmp`。
- `'1'` 模式只出现在文字里，没有示例。

**其它题面观察。** 两处影响描述很空泛：`user_prompt.txt:7` 的 “inconsistencies in how the images are processed or displayed”，以及 `:29` 的类似说法。它们没有给出期望的像素值，这正是 R6 多解的来源。这类句子更像自动生成时补的套话，不宜据此推断像素语义。

**初态线索。**

- 初态改动为空：`worktree_manifest.json` 中 `initial_diff.bytes` 为 0，工作树就是 base 的跟踪文件加上 `run_tests.sh`。`install.sh` 在镜像里存在，但不在公开包里（`untracked_missing`），因此看不到 PIL 的安装和编译方式。
- `worktree/run_tests.sh:1` 运行的是 `r2e_tests`，即不在工作树里的隐藏测试目录；开发时不应依赖它。
- 现有公开测试把 base 行为当作已知情况，并跳过这项比较（`worktree/Tests/test_file_libtiff.py:151-158`）。该测试用 `tiffinfo=img.tag` 重存 `hopper_g4.tif`，而这张图的 262 为 0（`worktree/Tests/test_file_tiff_metadata.py:83-102`，第 94 行）。修复后，这里写出的 262 会从 1 变成 0；由于该字段被忽略，测试应仍能通过。这也是 R6 会产生可见差别的真实场景：从 WhiteIsZero 源文件拷贝标签重存时，“只写标签”的做法会让读回的图整体反相。
- 读写不对称：读取端早已支持 photometric 0 的 `'1'`/`'L'`，覆盖 1、2、4、8 位（`:136-139,144-147,152-155,160-163`）；写出端 `SAVE_INFO` 每个模式只有一种 photometric。

**缺失信息的分量。**

- 真正可能阻碍开发：PIL 是否从 `/testbed/src` 导入。如果不是，改源码不生效，又没有 pip 可以重装。用 `env_import` 核对。
- 只影响自测范围：libtiff 是否可用。它决定压缩路径能否自测，以及 `test_file_libtiff.py` 的用例是否会跳过。
- 影响“修复能否被接受”，但不属于开发条件：R6 等题面未规定的项。
- 只需正常读代码：定位 `_save`、`SAVE_INFO`、`OPEN_INFO` 和 packer 表。这不算题面缺陷。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令（建议，未执行） |
| --- | --- | --- | --- | --- |
| 导入仓库内的 PIL（Python 源码加已编译的 `_imaging`） | 测试直接 `from PIL import ...`；`*.so` 被 git 忽略（`worktree/.gitignore:5-6`）；开发方式是 `setup.py develop build_ext --inplace`（`worktree/Makefile:52-53`；`worktree/tox.ini:13-17`） | `python` 指向 `/testbed/.venv/bin/python`，Python 3.9.21（`:10`） | 安装方式和 `.so` 的位置未知；`install.sh` 不在公开包 | `env_import` |
| 复现题面（未压缩路径） | `user_prompt.txt:10-23` | `/tmp` 可写，1 GiB；解题身份可写 `/testbed`（`:12`） | 无，纯 Python | `repro_issue_mode_l`、`repro_mode_1` |
| 默认行为回归自检 | `TiffImagePlugin.py:1456-1478` | 同上 | 无 | `default_photometric_kept` |
| 相关公开测试 | `worktree/Tests/test_file_tiff.py`；`worktree/Tests/test_file_tiff_metadata.py`；`worktree/Tests/test_file_libtiff.py:139-185`；`worktree/setup.cfg:8-10`；根目录 `worktree/conftest.py:1` 加载 `Tests.helper` | public_hints 说测试工具已指向 venv；brief 没有列 pytest 或 `packaging` 的版本 | pytest 与 `packaging`（`worktree/Tests/helper.py:14`）是否可用，未实测 | `public_tiff_tests` |
| libtiff 压缩路径 | `TiffImagePlugin.py:1499,1607-1708`；`worktree/Tests/test_file_libtiff.py:25` 按特性跳过 | 未提及 | 是否编译了 libtiff 未知 | `compressed_path_observe`（`env_import` 也会打印） |
| 重新编译 C 扩展（仅当修复要改 C，如新增 `'L;I'` packer） | `Pack.c:552-555`；`tox.ini:15` | 没有 pip/uv，没有出网（`:11`）；编译器和头文件未说明 | 未知；而且编译会改写 `/testbed` 下的构建产物 | 不给命令；纯 Python 修复不需要编译 |
| 网络 | 不需要 | 无出网 | 无 | 无 |
| `run_tests.sh` / 隐藏测试 | `worktree/run_tests.sh:1` 运行 `r2e_tests` | brief 说明隐藏测试不在工作树（`:6`） | 容器里是否有 `r2e_tests` 未知 | 不用于开发自检 |

以下命令都可以在 `/testbed` 下原样运行，只写 `/tmp`，内容与 `commands.json` 一致。全部为**建议，未执行**。

1. `env_import`（预期退出码 0）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "import sys, PIL, pytest; from PIL import Image, TiffImagePlugin, features; print(sys.executable, sys.version.split()[0]); print('PIL', PIL.__version__, PIL.__file__); print('TiffImagePlugin', TiffImagePlugin.__file__); print('core', Image.core.__file__); print('libtiff', features.check('libtiff'), features.version('libtiff')); print('pytest', pytest.__version__)"
   ```

   预计 Python 3.9.21，PIL `8.4.0.dev0`，`PIL.__file__` 和 `TiffImagePlugin.__file__` 都在 `/testbed/src/PIL/` 下，`core` 指向某个 `_imaging*.so`；libtiff 的结果未知。修复前后输出相同。如果 PIL 不在 `/testbed/src`，说明改源码不影响测试，属于开发阻塞。

2. `repro_issue_mode_l`（预期在 base 上退出码非 0）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; p='/tmp/r2e_pi_L.tif'; Image.new('L', (100, 100)).save(p, tiffinfo={262: 0}); r=Image.open(p); print('tag262', r.tag_v2[262], 'mode', r.mode, 'pixel00', r.getpixel((0, 0))); assert r.tag_v2[262] == 0, 'PhotometricInterpretation not kept'"
   ```

   修复前：打印 `tag262 1 mode L pixel00 0`，随后 `AssertionError: PhotometricInterpretation not kept`。修复后：打印 `tag262 0`，退出码 0。`pixel00` 取决于实现：只改标签时为 255，写入时同步反相则为 0。

3. `repro_mode_1`（预期在 base 上退出码非 0）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; p='/tmp/r2e_pi_1.tif'; Image.new('1', (100, 100)).save(p, tiffinfo={262: 0}); r=Image.open(p); print('tag262', r.tag_v2[262], 'mode', r.mode, 'pixel00', r.getpixel((0, 0))); assert r.tag_v2[262] == 0, 'PhotometricInterpretation not kept'"
   ```

   修复前：打印 `tag262 1 mode 1 pixel00 0`，随后 `AssertionError`。修复后：`tag262 0`，退出码 0。`pixel00` 只改标签时为 255，用 `'1;I'` 反相写出时为 0。

4. `default_photometric_kept`（预期退出码 0，修复前后都应如此）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; a=Image.new('L', (8, 8), 77); b=Image.new('1', (8, 8), 255); c=Image.new('RGB', (8, 8), (1, 2, 3)); a.save('/tmp/r2e_pi_def_L.tif'); b.save('/tmp/r2e_pi_def_1.tif'); c.save('/tmp/r2e_pi_def_RGB.tif'); ra=Image.open('/tmp/r2e_pi_def_L.tif'); rb=Image.open('/tmp/r2e_pi_def_1.tif'); rc=Image.open('/tmp/r2e_pi_def_RGB.tif'); print('L', ra.tag_v2[262], ra.getpixel((0, 0)), '| 1', rb.tag_v2[262], rb.getpixel((0, 0)), '| RGB', rc.tag_v2[262], rc.getpixel((0, 0))); assert (ra.tag_v2[262], rb.tag_v2[262], rc.tag_v2[262]) == (1, 1, 2); assert ra.tobytes() == a.tobytes() and rb.tobytes() == b.tobytes() and rc.tobytes() == c.tobytes()"
   ```

   预计打印 `L 1 77 | 1 1 255 | RGB 2 (1, 2, 3)`。如果修复改了默认 photometric，或者破坏了像素往返，这里会出现 `AssertionError`。

5. `public_tiff_tests`（预期退出码 0）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider Tests/test_file_tiff.py Tests/test_file_tiff_metadata.py Tests/test_file_libtiff.py::TestFileLibTiff::test_write_metadata
   ```

   base 上预计全部通过或跳过：libtiff 不可用时，libtiff 那条用例跳过；缺 `string_dimension.tiff` 的用例也会跳过（`worktree/Tests/test_file_tiff.py:692-696`）。修复后应仍全部通过。如果 base 上就有失败，先记为环境基线，不归因于修复。

6. `compressed_path_observe`（只看输出）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image, features; print('libtiff', features.check('libtiff')); p='/tmp/r2e_pi_lzw.tif'; Image.new('L', (100, 100)).save(p, tiffinfo={262: 0}, compression='tiff_lzw'); r=Image.open(p); print('tag262', r.tag_v2[262], 'compression', r.info.get('compression'), 'pixel00', r.getpixel((0, 0)))"
   ```

   libtiff 可用时，修复前预计打印 `libtiff True` 和 `tag262 1 compression tiff_lzw pixel00 0`；修复覆盖到压缩路径后应为 `tag262 0`。libtiff 不可用时，会先打印 `libtiff False`，再在 `save` 处抛出 `OSError: encoder libtiff not available`（`worktree/src/PIL/Image.py` 的 `_getencoder`）。这只说明环境里没有压缩路径。

## 5. 阅读范围

**实际打开的文件：**

- 角色卡全文；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 全文。
- `worktree_manifest.json`：只看了顶层键和计数（base、export、initial_diff、untracked_*、not_included），没有逐项看 `files` 列表，也没有打开 `initial_diff.source` 指向的公开包以外的路径。
- `worktree/run_tests.sh` 全文。
- `worktree/src/PIL/TiffImagePlugin.py`：第 1-290、417-646、955-1000、1060-1739、1955-1998 行。
- `worktree/src/PIL/TiffTags.py`：第 25-34、96-115、466-476 行。
- `worktree/src/PIL/_version.py`；`worktree/src/PIL/features.py`（函数列表，第 95-115、173-200 行）；`worktree/src/PIL/Image.py`（只用 grep 查了 `_getencoder` 与 `_imaging` 的导入）。
- `worktree/src/libImaging/Pack.c`：第 80-125、538-560 行；`worktree/src/libImaging/Unpack.c`：第 145-170、436-445、1470-1495 行；`worktree/src/encode.c`：`get_packer` 与 `PyImaging_LibTiffEncoderNew` 的开头；`worktree/src/libImaging/TiffDecode.c`：只用了 grep。
- `worktree/Tests/test_file_libtiff.py`：第 1-330 行；`worktree/Tests/test_file_tiff.py`：第 1-60、300-440、479-725 行及测试名列表；`worktree/Tests/test_file_tiff_metadata.py`：第 1-200 行及测试名列表；`worktree/Tests/helper.py`：第 1-110、155-262 行；`worktree/Tests/conftest.py`；`worktree/conftest.py`。
- `worktree/setup.cfg`、`worktree/tox.ini`、`worktree/.gitignore`、`worktree/requirements.txt`；`worktree/Makefile`（grep）；`worktree/docs/handbook/image-file-formats.rst`：第 780-960 行；`worktree/CHANGES.rst`：第 1-40 行（另 grep）。
- 在 `worktree/Tests/`、`worktree/src/`、`worktree/docs/` 里 grep 过 `tiffinfo`、`262`、`photometric`；确认了几张测试图片存在，但没有解析图片内容。

**没有查的范围：** 其它测试文件；`TiffImagePlugin.py` 中 IFD 写出细节的其余部分和 `AppendingTiffWriter` 的大部分；libtiff 编码器的内部行为（例如 CCITT 压缩与 photometric 的交互）；`setup.py` 的构建流程；`depends/`、`winbuild/`、`.ci/`、`.github/`；git 历史（公开包不含 `.git`）；上游仓库和 PR。

**限制：** `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获到的模型实际消息。工作树也不是完整的运行容器：没有 `.venv`、编译好的扩展、`install.sh` 和隐藏测试。模型实际收到的消息、运行资源和开发条件都没有经过验证；上面所有命令都未执行，其中的预期输出是根据源码推断的。本上下文没有接触过本题的私有材料。
