# 公开读者记录：pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605

- 角色：R2E 公开读者（静态审查，不解题），2026-09-25，干净上下文；未接触本题任何私有材料。
- 只读了角色卡和 `PUBLIC_DIR` 下的文件，没有运行项目代码。下文所有"会报错 / 能通过"的判断都是**按 base 源码做的静态推断**；所有命令都是**建议，未执行**。
- 文件路径都相对 `worktree/`，也就是解题者在 `/testbed` 看到的目录。

## 0. 初态与公开提示

**初态**

- base 提交 `48e4e0722e6afd4cf38ffc70d9eeea235085ff4e`，与 `user_prompt.txt:1` 的短哈希 `48e4e0722e6a` 一致。版本是 Pillow `3.1.0.dev0`（`PIL/__init__.py:15`）。
- 据 `worktree_manifest.json`，`initial_diff` 为 0 字节，即镜像初态相对 base 没有改动。镜像里有两个未跟踪文件：`run_tests.sh` 收进了工作树，`install.sh` 缺失。工作树也不含 `.git`、`.venv` 和编译扩展：`PIL/*.so` 被 `.gitignore` 忽略，工作树里确实一个都没有。
- `run_tests.sh` 只有一行：`.venv/bin/python -W ignore r2e_tests/unittest_custom_runner.py`。`r2e_tests/` 不在工作树里（属于隐藏测试），所以解题者跑不了这条命令。它只说明评分用 unittest 风格的自定义运行器。

**`public_hints` 分三类**

| 类别 | 内容 | 对合法解法的影响 |
| --- | --- | --- |
| 题目需求 | 找到根因，修改**非测试**源码；评分用另一组测试 | 修复落在 `PIL/` 下的 `.py`（如 `PIL/TiffImagePlugin.py`、`PIL/TiffTags.py`）即可，没有额外限制。 |
| 操作指令 | 不改仓库测试文件；只跑单个测试文件或模块；在 `/testbed` 用 `python -m pytest`；确认完成后简短总结并停止 | 不限制修法。如果 pytest 不在环境里，可以退回 unittest（见 §4 T1'）。 |
| 环境事实声明 | 仓库在 `/testbed`；`python` 和"仓库的测试工具"都指向 `/testbed/.venv`；不联网；pip 可能不可用 | `environment_brief.md` 证实了 `python` 指向 `.venv`（Python 3.9.21）、没有 pip/uv、不能出网。**没有证实**两点：一是 pytest 已安装，而仓库自带的说明用的是 unittest/nose（`Tests/README.rst:4,20-28`、`requirements.txt`）；二是 `/testbed/PIL` 带有编译好的 `_imaging`，并且就是被导入的那个包。 |

## 1. 需求表

"类别"一栏分三种：明示、可推知、多解（仍有多种合理解释）。

| # | 行为 | 依据 | 类别 |
| --- | --- | --- | --- |
| R1 | 在 `ImageFileDirectory_v2` 里给标签 41988 赋值 `IFDRational(0, 0)`，再用 `tiffinfo=info, compression='raw'` 保存 TIFF，不再抛 `struct.error` | 题面的 Example / Actual Behavior | 明示 |
| R2 | 重新打开后，`reloaded.tag_v2[41988][0].numerator == 0` 且 `.denominator == 0` | 题面的 Expected Behavior 和示例里的 `print` | 明示 |
| R3 | `tag_v2[41988]` 仍是可下标的元组，不能变成标量 | 示例用了 `[0]`。base 里不在 `TAGS_V2` 的标签按 `TagInfo` 默认的 `length=0` 存成元组（`PIL/TiffTags.py:26`，`PIL/TiffImagePlugin.py:527-532`） | 可推知（由示例接口约束） |
| R4 | 文件里的字段要写成有理数类型，读回时才能还原成 `IFDRational` | 题面要求"保留有理数值"。只有类型 5 和 10 的读取器会构造 `IFDRational`（`TiffImagePlugin.py:600-605, 620-625`）。如果写成 LONG，读回的是 int，而 `int.denominator == 1`，满足不了 R2 | 必须写成有理数类型可推知；用 5（RATIONAL）还是 10（SIGNED RATIONAL）属多解 |
| R5 | 非零分母的 `IFDRational`（如 1/2）写进同一类未注册标签时也应能保存 | base 的触发条件与分母无关（见 §3 Q2）。文档说数值和字符串的字段类型会自动识别，有理数应以 `IFDRational` 传入（3.1.0 新增，`docs/handbook/image-file-formats.rst:503-518`） | 可合理推知，但题面只要求 0/0，属多解；隐藏测试是否覆盖未知 |
| R6 | 其它未注册标签和其它值类型（float、str）也能自动识别类型 | 同一段文档承诺了自动识别，而 base `_setitem` 的猜类型分支执行不到（§3 Q2） | 题面没要求，属可选扩展，多解 |
| R7 | 用 libtiff 压缩保存（`compression` 不是 `'raw'`）时处理 0/0 | 题面明确用 `'raw'`。静态看，libtiff 分支对标量 `IFDRational` 调 `float(v)`（`TiffImagePlugin.py:1416-1417`）。`IFDRational` 没有自己的 `__float__`，继承的 `numbers.Rational.__float__` 计算 numerator/denominator，遇到 0/0 会抛 ZeroDivisionError。元组值传进 C 编码器后落到 "Unhandled type in tuple" 分支，最后报 `RuntimeError("Error setting from dictionary")`（`encode.c:759-805`） | 题面范围外 |

**需要保留的旧行为**

| # | 行为 | 依据 | 类别 |
| --- | --- | --- | --- |
| P1 | 已注册标签用 `TAGS_V2` 里的类型；用户显式设置的 `tagtype` 优先于任何推断 | `test_rt_metadata` 先赋值，再把 RollAngle/YawAngle 的类型改成 11/12（`Tests/test_file_tiff_metadata.py:47-50`）；`_save` 会复制 `info.tagtype`（`TiffImagePlugin.py:1316-1321`） | 明示（公开测试） |
| P2 | 已注册 RATIONAL 标签的现有往返行为：int 写进分辨率、读回 `IFDRational`、`_limit_rational` 的输出、整份元数据往返 | `Tests/test_file_tiff.py:78-91, 306-316, 340-374`；`Tests/test_file_tiff_metadata.py:113-155` | 明示 |
| P3 | 旧 API `tag`（v1）里的有理数是 `(num, den)` 元组 | `Tests/test_file_tiff.py:242-259`；`Tests/test_file_tiff_metadata.py:95-111` | 明示 |
| P4 | `IFDRational` 自身语义：0/0 是合法值；分母为 0 时 `limit_rational` 返回 `(num, 0)`；现有的相等比较测试 | `TiffImagePlugin.py:228-233, 263-265, 293-294`；`Tests/test_tiff_ifdrational.py:19-45` | 明示 |
| P5 | 未注册标签的整数值目前一律按 LONG(4) 写出，原因是猜类型分支执行不到 | 没有公开测试直接断言这一点 | 改动它算行为变化，是否允许未说明，属多解 / 风险 |
| P6 | JPEG/WebP/MPO 读 EXIF 时也用 `ImageFileDirectory_v2`（`PIL/JpegImagePlugin.py:397-436`）。读取时类型来自文件，不经过推断；但如果改了 `TAGS_V2`（例如注册 41988），这些读取结果的形状（标量还是元组）会跟着变 | 公开代码 | 可推知 |

## 2. 合理实现范围

**按题面都应接受的做法（不写具体修复）**

- **A. 在推断处修。** 在 `ImageFileDirectory_v2._setitem` 的类型推断里，让未注册标签在值是 `IFDRational`（或更宽一些，任何非整数的有理数，如 `Fraction`）时得到有理数类型。好处是用户自己的 IFD 和 `_save` 新建的 IFD（`TiffImagePlugin.py:1297, 1316-1317`）走同一段逻辑；以 dict 形式传入的 `tiffinfo`，以及 v1 IFD（经 `to_v2()`，`:1314-1315`）也一并覆盖。
- **B. 更宽的版本：修好整个执行不到的猜类型分支**（`TiffImagePlugin.py:499-517`）。要注意两点：
  - 只让原分支变得可达还不够。`IFDRational` 既不是 int 也不是 float，会落到 7（UNDEFINED）；`write_undefined` 原样返回这个对象，接着 `len(data)` 就会失败（`:616-618, 727`）。必须另加有理数分支。
  - 这会改变未注册标签的整数类型：现在都是 LONG；原分支对小于 2\*\*16 的整数给 SHORT(3)（`:504-508`）。读回的值不变，但 `tagtype` 变了（P5）。
- **C. 在保存阶段修。** 在 `_save` 复制 `tiffinfo` 时，或在 `ImageFileDirectory_v2.save` 选 writer 时，按值的类型改用有理数 writer。前提是不能覆盖用户显式设置的 `tagtype`（P1）。这种做法下，保存前 `info.tagtype[41988]` 可能仍是 4；如果隐藏测试检查这一点，结果会不同，公开材料无法判断。
- **D. 在 `TAGS_V2` 里注册 41988（DigitalZoomRatio）为 RATIONAL。** 这只能修这一个标签：
  - 按 EXIF 规范写 `length=1` 时，`tag_v2[41988]` 会变成标量 `IFDRational`，题面示例的 `[0]` 会抛 TypeError（`IFDRational` 不支持下标），与 R3 冲突。
  - 写 `length=0` 能让示例通过，但与规范的计数不符，其它未注册标签也照样失败。
  - 它还会改变 JPEG EXIF 读取结果的形状（P6）。适合作补充，不宜单独作为修复。

**不应接受的做法和容易踩的坑**

- **让 LONG writer 接受 `IFDRational`**，例如给它加 `__index__` / `__int__`，或在 writer 里取整。这样保存不再报错，但读回的是 int：`int.numerator`、`int.denominator` 都存在，示例会打印 `0 1` 而不是 `0 0`，违反 R2 和 R4。
- **只改零分母相关的代码**（`_limit_rational`、`IFDRational.limit_rational`、`__float__` 等）。按静态推断修不了示例：失败发生在 LONG writer 里，而零分母在 RATIONAL writer 下本来就能写（§3 Q2 第 4 点）。
- **用 `isinstance(v, numbers.Rational)` 判断时要小心。** `int` 也是 `numbers.Rational`（它是 `Integral` 的子类）。如果这个判断放在整数判断之前，未注册标签的整数会被改成按 RATIONAL 写出。
- **选 SIGNED RATIONAL(10)** 时，0/0 和正数的往返（静态看）没问题。但 `write_signed_rational` 用无符号的 `"2L"` 打包（`TiffImagePlugin.py:627-630`），负值会因超出范围而失败。这是既有问题，题面没涉及。

**约定**

- 命名、报错信息、警告：题面都没有约定，也不需要新增公开 API。
- 字段类型码：没有约定。5 最符合 EXIF 对 DigitalZoomRatio 的定义，但这是领域常识，不是题面要求。
- 默认行为：显式设置的 `tagtype` 仍应优先（P1）。未注册标签返回元组的形状应保持（R3）。
- 0/0 的 `IFDRational` 与任何值都不相等，包括另一个 0/0：`__eq__` 委托给 NaN（`TiffImagePlugin.py:305-306`）。所以自测只能比较 `.numerator` 和 `.denominator`。题面没要求改相等语义。

## 3. 题面质量与初态线索

**Q1 题面是否直接给出或强烈暗示修法：否。** 示例是复现脚本，不是修好后的实现。题面没提类型推断、`TAGS_V2` 或 writer 分派。

**Q2 题面描述的报错能否从 base 读出：能，报错信息也吻合；但把原因归到"零分母"不准确。** 静态推导链如下：

1. 41988 只出现在旧的名字表 `TAGS` 里（`PIL/TiffTags.py:233`），不在 `TAGS_V2` 里（`:44-169`）。
2. `_setitem` 取 `TAGS_V2.get(tag, TagInfo())`（`TiffImagePlugin.py:496`）。`TagInfo` 默认 `type=4`（`TiffTags.py:26`），所以 `self.tagtype[tag] = info.type` 永远不会抛 `KeyError`，`except KeyError` 里按值猜类型的代码（`TiffImagePlugin.py:500-517`）执行不到。标签类型因此定为 LONG(4)。
3. `_save` 把 `info` 的值和 `tagtype` 复制到新 IFD（`:1316-1321`）。`ImageFileDirectory_v2.save` 按类型 4 调用 `_register_basic` 注册的 writer（`:570-571, 574, 715`），实际执行的是 `struct.pack("<L", IFDRational(...))`。`IFDRational` 没有 `__index__`，Python 3 于是报 `struct.error: required argument is not an integer`，与题面一致。
4. 由此推出两件事：
   - `IFDRational(1, 2)` 写进 41988 会**同样**失败。
   - 反过来，把 0/0 写进已注册的 RATIONAL 标签（如 282 XResolution，`TiffTags.py:77`）走的是 `write_rational` → `_limit_rational` → `IFDRational.limit_rational`，分母为 0 时直接返回 `(0, 0)`（`TiffImagePlugin.py:217-220, 293-294, 607-610`）。按静态推断，base 就能保存并读回 0/0。

影响：标题和描述把问题说成"零分母处理"，可能把解题者引向 `_limit_rational`、`__float__` 这类零分母代码。不过照示例复现一次，traceback 会落在 LONG writer 上，方向可以纠正过来。零分母在本题的实际作用有两个：往返后必须仍是 0/0；而且没法用相等比较来验证。

**Q3 题面示例在 base 接口下是否说得通：基本说得通，有一处路径问题。**

- 示例用到的接口 base 都有：`ImageFileDirectory_v2()` 无参构造（`TiffImagePlugin.py:405-427`）、`IFDRational(0, 0)`（`:242-265`）、`save(..., tiffinfo=..., compression='raw')`（`:1299-1321`；文档 `image-file-formats.rst:503-518`）。
- `Image.open('hopper.png')`：仓库里的文件是 `Tests/images/hopper.png`（RGB，128×128），在 `/testbed` 下照原样运行会抛 FileNotFoundError，需要改路径。另外，PNG 解码依赖编译进 `_imaging` 的 zlib 解码器，环境说明里没提。`'temp.tiff'` 会写到当前目录。
- `reloaded.tag_v2[41988][0]` 与 base 对未注册标签返回元组的行为一致（R3），而且对实现有约束（§2 D）。
- 41988 是 EXIF 的 DigitalZoomRatio（`PIL/ExifTags.py:137`）。`IFDRational` 的 docstring 正是拿 DigitalZoomRatio 的 0/0 作动机（`TiffImagePlugin.py:229-232`），说明 0/0 是有意支持的值。

**Q4 能否定位复现与调查入口：能。**

- 示例加 traceback 直接指向 `PIL/TiffImagePlugin.py`（`ImageFileDirectory_v2._setitem` / `save`、`_save`）和 `PIL/TiffTags.py`（`TagInfo`、`TAGS_V2`）。
- 相关公开测试：`Tests/test_file_tiff_metadata.py`、`Tests/test_file_tiff.py`、`Tests/test_tiff_ifdrational.py`。
- 文档 `docs/handbook/image-file-formats.rst:503-518` 给出了 `tiffinfo` 类型自动识别的预期行为。

**Q5 缺失信息**

- **可能真正影响结果的**：隐藏测试是否检查字段类型码（5 还是 10）、是否检查保存前的 `tagtype`、是否覆盖非零分母或其它未注册标签。按角色卡的说明，题面是由修复提交和测试自动生成的；隐藏测试里是否还有题面没描述的断言，公开材料无法判断。
- **只需正常读代码的**：类型推断在哪、writer 怎么分派、读回的形状由什么决定。这些都能从上面列的文件里读出来，不算题面缺陷。
- **环境层面（不是题面缺陷）**：编译扩展和 pytest 是否可用，见 §4。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令（建议，未执行）与预期 |
| --- | --- | --- | --- | --- |
| 从 `/testbed` 导入带编译核心的 PIL | `run_tests.sh` 用 `.venv/bin/python`；`_imaging` 缺失时 `PIL/Image.py:60-99` 直接抛 ImportError | `python` 指向 `/testbed/.venv/bin/python`（3.9.21） | 工作树不含编译扩展和 `install.sh`，看不出 `_imaging` 在哪，也看不出 `/testbed/PIL` 是否就是被导入的包 | E1：预期打印 `3.9.21 /testbed/PIL/__init__.py 3.1.0.dev0` 和一个 `_imaging` 扩展路径 |
| 评分运行器能否看到 `/testbed/PIL` 的改动 | 运行器是 `r2e_tests/` 下的脚本，`sys.path[0]` 是脚本所在目录，不是 `/testbed` | 未涉及 | 安装方式未知（可编辑安装、就地构建或其它） | E2：预期打印 `/testbed/PIL/__init__.py`。如果打印 site-packages 路径或 ImportError，只说明自测和评分的导入路径可能不同（运行器也可能自己调整 `sys.path`），不影响题意 |
| 样例图片 | `Tests/images/hopper.png` 和 `hopper.ppm` 都在工作树里 | — | PNG 需要 zlib 解码器 | E1 第二行 `zip_decoder` 应为 True；主复现 R 改用 PPM 来避开这个依赖 |
| 写临时 TIFF | 题面写到 `temp.tiff` | `/testbed` 和 home 可写，`/tmp` 有 1 GiB | 无 | R 和 I 写到 `/tmp/rh2_ifdr_*.tiff` |
| 跑公开测试 | `public_hints` 让用 `python -m pytest`；仓库测试是 unittest（`Tests/README.rst:4`） | 没提 pytest | pytest 是否安装未知 | E3、T1 / T1'、T2 |
| libtiff 编解码 | 只有压缩不是 raw 时才用到；`Tests/test_file_libtiff.py:17-21` 在缺 codec 时跳过 | 没提 | 未知 | 本题不需要；E1 第二行的 `libtiff_encoder` 仅供参考 |
| 构建、依赖、网络 | 修复只需改 `.py`，不必重编 C 扩展，也不必装包 | 无 pip，无出网 | 编译器是否可用未知（也用不到） | **不要运行**：`make`（默认目标 release-test 会先 `pip install`，`Makefile:3, 48-52`）、`make clean` 或 `make inplace`（都会执行 `rm PIL/*.so`，`Makefile:5-9, 41-42`）、`tox`、`python setup.py clean` 或 `build_ext` |

**E1 环境与导入检查（建议，未执行）**

```bash
cd /testbed && python - <<'PY'
import sys, PIL
from PIL import Image
print(sys.version.split()[0], PIL.__file__, PIL.PILLOW_VERSION, getattr(Image.core, "__file__", None))
print("zip_decoder" in dir(Image.core), "libtiff_encoder" in dir(Image.core))
PY
```

**E2 在不含 `/testbed` 的工作目录下导入（模拟运行器的 `sys.path`；建议，未执行）**

```bash
cd /tmp && /testbed/.venv/bin/python -c "import PIL; print(PIL.__file__)"
```

**E3 检查 pytest（建议，未执行）**

```bash
cd /testbed && python -m pytest --version
```

**R 主复现：只经过公开 API，能区分修复前后（建议，未执行）**

脚本跑三组：第 1 组是题面场景，第 2 组验证失败与分母无关，第 3 组是已注册 RATIONAL 标签的对照。

```bash
cd /testbed && python - <<'PY'
from PIL import Image, TiffImagePlugin
from PIL.TiffImagePlugin import IFDRational
cases = [(41988, IFDRational(0, 0)), (41988, IFDRational(1, 2)), (282, IFDRational(0, 0))]
for i, (tag, val) in enumerate(cases):
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[tag] = val
    label = "tag=%d %d/%d tagtype_before_save=%s" % (tag, val.numerator, val.denominator, info.tagtype[tag])
    out = "/tmp/rh2_ifdr_%d.tiff" % i
    try:
        Image.open("Tests/images/hopper.ppm").save(out, tiffinfo=info, compression="raw")
        r = Image.open(out)
        v = r.tag_v2[tag]
        first = v[0] if isinstance(v, tuple) else v
        print(label, "-> OK", type(v).__name__, "filetype=%s" % r.tag_v2.tagtype[tag], first.numerator, first.denominator)
    except Exception as e:
        print(label, "-> FAIL", type(e).__module__ + "." + type(e).__name__, e)
PY
```

修复前预计输出（静态推断）：

```
tag=41988 0/0 tagtype_before_save=4 -> FAIL struct.error required argument is not an integer
tag=41988 1/2 tagtype_before_save=4 -> FAIL struct.error required argument is not an integer
tag=282 0/0 tagtype_before_save=5 -> OK IFDRational filetype=5 0 0
```

修复后预计输出（以"通用修复、写成 RATIONAL"为例）：

```
tag=41988 0/0 tagtype_before_save=5 -> OK tuple filetype=5 0 0
tag=41988 1/2 tagtype_before_save=5 -> OK tuple filetype=5 1 2
tag=282 0/0 tagtype_before_save=5 -> OK IFDRational filetype=5 0 0
```

哪些差异取决于实现：

- 只在保存阶段修的实现，`tagtype_before_save` 可能仍是 4。
- 选 SIGNED RATIONAL 的实现，`filetype` 会是 10。
- 只特判零分母的实现，第 2 行仍会 FAIL。题面本身只要求第 1 行。
- 第 1 行的 `tuple` 和 `0 0` 是题面要求（R2、R3）。
- 第 3 行修复前后都应是 OK。如果修复前它就失败，说明 §3 Q2 第 4 点的静态推断有误。

**I 题面原样版（换成仓库里的真实路径；需要 zlib；建议，未执行）**

```bash
cd /testbed && python - <<'PY'
from PIL import Image, TiffImagePlugin
im = Image.open("Tests/images/hopper.png")
info = TiffImagePlugin.ImageFileDirectory_v2()
info[41988] = TiffImagePlugin.IFDRational(0, 0)
im.save("/tmp/rh2_issue_temp.tiff", tiffinfo=info, compression="raw")
reloaded = Image.open("/tmp/rh2_issue_temp.tiff")
print(reloaded.tag_v2[41988][0].numerator, reloaded.tag_v2[41988][0].denominator)
PY
```

修复前：traceback 以 `struct.error: required argument is not an integer` 结尾。修复后：打印 `0 0`。

**T1 公开测试回归（建议，未执行）**

```bash
cd /testbed && python -m pytest -q Tests/test_file_tiff_metadata.py Tests/test_tiff_ifdrational.py Tests/test_file_tiff.py
```

预计修复前后都通过。这几个文件不覆盖"未注册标签 + 有理数"，主要用来守住 P1 到 P4。缺 JPEG 支持时 `test_gimp_tiff` 等用例可能跳过。Python 3.9 下可能出现 `collections.MutableMapping` 的 DeprecationWarning（来自 `TiffImagePlugin.py:352`），3.9 里仍能用，不影响结果。如果修复前就有失败，记为基线噪声。

**T1' 没有 pytest 时的替代（建议，未执行）**

```bash
cd /testbed && PYTHONPATH=Tests python -m unittest test_file_tiff_metadata test_tiff_ifdrational test_file_tiff
```

**T2 只在改了 `TAGS_V2` 或 libtiff 分支时才需要（建议，未执行）**

```bash
cd /testbed && python -m pytest -q Tests/test_file_jpeg.py Tests/test_file_mpo.py -k exif
cd /testbed && python -m pytest -q Tests/test_file_libtiff.py
```

## 5. 阅读范围

**打开过的文件**

- 角色卡本身。
- `PUBLIC_DIR` 下：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`。manifest 只看了 `export`、`initial_diff`、`untracked_*`、`not_included` 几个字段，以及 `files` 的少量样例；`initial_diff.source` 指向 `PUBLIC_DIR` 之外，没有打开。
- 工作树中全文读过：`PIL/TiffImagePlugin.py`、`PIL/TiffTags.py`、`Tests/test_file_tiff_metadata.py`、`Tests/test_file_tiff.py`、`Tests/test_tiff_ifdrational.py`、`Tests/helper.py`、`Tests/README.rst`、`run_tests.sh`、`requirements.txt`、`tox.ini`、`.gitignore`。
- 工作树中读过部分：
  - `PIL/Image.py`：36-100 行、1601-1690 行，另加 grep。
  - `PIL/JpegImagePlugin.py`：395-480 行。
  - `PIL/ExifTags.py`：1-30 行、130-140 行。
  - `PIL/__init__.py`：只看了版本行。
  - `Tests/test_file_libtiff.py`：1-44 行、120-176 行、228-245 行。
  - `Tests/test_file_jpeg.py`：160-245 行。
  - `Tests/test_file_webp_metadata.py`：20-40 行。
  - `Tests/test_file_mpo.py`：40-60 行。
  - `docs/handbook/image-file-formats.rst`：470-565 行。
  - `encode.c`：728-812 行。
  - `Makefile`：1-10 行、40-56 行。
  - `test-installed.py`：前 30 行。
  - `CHANGES.rst`：前 40 行，另加 grep。
- 目录列表：`worktree/`、`PIL/`、`Tests/`、`Tests/images/`（只 grep 了 hopper）、`docs/reference/`。

**没查的范围**

- 其它图像插件、除 `encode.c` 片段外的 C 源码、`libImaging/`、`setup.py`、其余文档和测试。
- 真实容器里的任何东西：`.venv` 内容、编译扩展、pytest、`r2e_tests/`。

**保留的限制**

- `user_prompt.txt` 只是静态渲染，不等于模型实际收到的消息。
- `worktree/` 不是可运行的容器。
- 本文所有运行结果都是静态推断，命令都没有执行。模型实际收到的消息、运行资源和开发条件都没有验证过。

## 关键未知（汇总）

1. 隐藏测试对字段类型码（5 还是 10）、保存前的 `tagtype`、非零分母或其它未注册标签有没有要求。
2. `/testbed/PIL` 是否带编译好的 `_imaging`，并被 `python` 和 `r2e_tests` 运行器导入（E1、E2）。
3. pytest 是否已安装（E3）。
4. zlib 解码器是否可用。这只影响照题面原样用 PNG 复现（I）。
