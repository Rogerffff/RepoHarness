<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审：读历史前分析 — pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605

- 角色：R2E 私有主审（静态审查），2026-09-25。按角色卡第 1–7 步完成，**尚未读本题任何历史调查**。
- 证据级别分四档：**静态**（读源码推断）；**评分实测**（current 材料的 RH2 账本与 `.eval.log`）；**镜像实测**（协调者 devcheck：正式启动路径、agent 身份；私有 gold 对照以 root、不联网运行）；**真实模型**（本题没有）。
- 行号都指 base 工作树（`PUBLIC_DIR/worktree/`，即容器里的 `/testbed`）。

## 0. 摘要

- **目标**：Pillow 3.1.0.dev0（base `48e4e072`）。给未注册标签 41988（DigitalZoomRatio，不在 `TAGS_V2` 里）赋 `IFDRational(0,0)` 后用 raw 方式保存，会抛 `struct.error`。要求修复后能保存，读回的 `tag_v2[41988][0]` 仍是 0/0。
- **根因**（静态推断，镜像实测证实）：`_setitem` 取 `TAGS_V2.get(tag, TagInfo())`，而 `TagInfo` 默认 `type=4`（`PIL/TiffTags.py:26`）。所以 `except KeyError` 里的猜类型分支（`TiffImagePlugin.py:499-517`）永远走不到，未注册标签一律按 LONG 写出；LONG writer 执行 `struct.pack("<L", IFDRational)` 时失败。**这与分母是不是 0 无关**：base 上 41988 写 1/2 同样失败，已注册的 282 写 0/0 正常。
- **评分**：期望映射 11 个键，全部 PASSED。唯一目标键是 `TestFileTiffMetadata.test_exif_div_zero`：noop 为 ERROR，gold 为 PASSED，4 组 current 运行结果一致。其余 10 个是回归键。期望里没有 FAILED / ERROR 键。
- **暂定处置**：保留为开发诊断用的静态候选（needs_review，理由是"静态候选，待 actor 验证"），不需要材料修订。发现的问题都属低严重度：
  - 题面把原因说成"零分母"。这有误导性，但不构成冲突。
  - 测试只覆盖题面的字面例子。只特判零分母、或只注册 41988 的部分修复也能得 1。
  - gold 顺带改变了未注册整数标签的类型码，这一点没有测试覆盖。
  - 公开提示推荐的 `python -m pytest`，在本仓的旧式 unittest 测试上会报出恒定的假失败。
  - 本题的修复已经出现在同仓另外 6 题的初态里。
- **最关键的未知**：
  - 候选 K1–K4 还没实跑。
  - 评分证据所在的镜像 build（`7a80aa71…`）与 devcheck 用的 build（`c9ec14f7…`）不是同一张。
  - 题面示例会在当前目录写 `temp.tiff`。RH2 投影怎样处理这种未跟踪的二进制文件，尚未核实。
  - 模型实际收到的消息和真实求解过程都没有验证。

## 1. 材料与初始问题（方面 2；清单 1、2、27）

| 项 | 结果 | 级别 |
| --- | --- | --- |
| 材料一致 | 隐藏测试 5 个文件的 sha256 与 `grading_bundle.json` 逐个相同；`gold.patch` 等于 `validation_bundle` 里的 `f5448ef9…`；`run_tests.sh` 为 `cb5074a9…`；`expected_output.json` 为 `11a66580…`；各日志的 `RH2_SETUP_HIDDEN_TESTS_TREE=43f98461…` 与 `run_refs.current_material` 一致；`revisions.json=[]` | 本地核对 |
| 初态 | `initial_diff` 为 0 字节；容器里 `git status` 只有 `?? install.sh`、`?? run_tests.sh`；HEAD 为 `48e4e072…`，没有 remote、reflog、refs，HEAD 也没有子提交 | 镜像实测（prelaunch / preflight） |
| 初态存在题述问题 | 4 次 noop（R-f 全池、代表题重复、重新定性、环境轮复跑）都只有 `test_exif_div_zero` 为 ERROR。traceback 依次经过 `TiffImagePlugin.py:1446 _save`、`:715 save`、`:571` LONG writer、`:546 _pack`，最后是 `struct.error: required argument is not an integer`，与题面 Actual Behavior 逐字相同 | 评分实测 |
| 以 actor 身份复现 | pr6_3（题面示例，图片路径换成 `Tests/images/hopper.png`）报同一个 traceback。pr3_2 中，41988 写 0/0 和 1/2 都 FAIL（tagtype 为 4）；282 写 0/0 成功，读回也是 0/0 | 镜像实测 |
| 公开读者的静态推断 | §3 Q2 的四点都被 pr3_2 证实 | — |

## 2. 隐藏测试展开（方面 3；清单 18–20、25、32）

**运行方式。** `run_tests.sh` 执行的是 `.venv/bin/python -W ignore r2e_tests/unittest_custom_runner.py`，不是 pytest。

- runner 调用 `loader.discover("r2e_tests")`。每个测试的 ID 是 `模块::类::方法`（runner:121-126），解析时去掉模块名，得到 `类.方法` 形式的键。
- 如果测试模块导入失败，键会变成 `_FailedTest.test_1` / `_FailedTest.test_2`。设计对照的日志里已经出现过这种情况。
- 共两个类：`TestFileTiffMetadata`（test_1.py）和 `Test_IFDRational`（test_2.py）。没有撞键，没有参数化，也没有 SKIP。

**与公开测试的差异**（diff 结果）：

- test_1.py = `Tests/test_file_tiff_metadata.py` 加上新增的 `test_exif_div_zero`。
- test_2.py = `Tests/test_tiff_ifdrational.py` 加上新增的 `test_ifd_rational_save` 及其 import。
- `helper.py` 与 `Tests/helper.py` 逐字相同，随隐藏测试一起放入，不是候选能改到的那份。

**目标键 `TestFileTiffMetadata.test_exif_div_zero`**（test_1.py:188-198）

- **输入**：`hopper()` 打开 `Tests/images/hopper.ppm`（相对于 cwd=/testbed，不需要 zlib）；`info[41988] = IFDRational(0,0)`；然后 `im.save(tmp, tiffinfo=info, compression='raw')`。
- **调用链**：
  1. `_setitem`（:491-532）在 base 上把 tagtype 设为 4。
  2. `_save`（:1290）中 `libtiff=False`（:1302）。
  3. 复制循环先执行 `ifd[key] = info.get(key)`（值是元组 `(IFDRational(0,0),)`），**再执行 `ifd.tagtype[key] = info.tagtype[key]`**（:1316-1321）。所以最终类型取自用户传入的 IFD。
  4. `ifd.save` 在 :715 按类型分派 writer。
- **断言**：`reloaded.tag_v2[41988][0]` 的 `.numerator == 0` 且 `.denominator == 0`。
- **通过条件**（静态）：
  - 文件里的类型必须是 5 或 10。只有这两种类型的 loader 会构造 IFDRational（:600-605、:620-625）。
  - 未注册标签读回时仍是元组（`TagInfo` 默认 `length=0`，:527-532）。
  - 反例：写成 LONG 时读回的是 int，分母为 1，断言失败；写成 UNDEFINED 时根本写不出去（`len(IFDRational)` 抛 TypeError）。
- **公开依据**：每一步都照题面示例来——同一个标签、同一个值、同样用 `compression='raw'`、同样的读取写法，只是把 png 换成了 ppm。没有题面以外的要求：不检查类型码，不检查保存前的 `tagtype`，也不检查非零分母或其它标签。

**新增的回归键 `Test_IFDRational.test_ifd_rational_save`**（test_2.py:49-60）

- 用 `dpi=(IFDRational(301,1),)*2`，先 `WRITE_LIBTIFF=True`、再 `False` 各保存一次，比较 `float(tag_v2[282])`。
- base 已经能通过（libtiff 分支做了 `atts[k] = float(v)`，:1416-1417），4 次 noop 都是 PASSED。它是同一上游提交新增的，但不是本题目标。
- 需要 libtiff 编码器；镜像实测 `libtiff_encoder` 为 True。
- 循环结束时全局 `WRITE_LIBTIFF` 复位为 False。即使中途失败，后面也只剩不保存文件的两个测试，不会串扰。

**其余 9 个回归键**（与公开测试同文，已全部读过）：

- `test_rt_metadata`：用显式 tagtype 11/12 覆盖已注册的类型 10，读回 float / double，对应 P1。
- `test_read_metadata`：读 hopper_g4.tif，检查 v2 的值和 v1 的 `(num,den)` 形状，对应 P2 / P3。
- `test_write_metadata`：hopper.tif 用 `tiffinfo=img.tag` 往返，比较经 `_limit_rational(v, 2**31)` 处理后的值，对应 P2。
- 其余 6 个：`test_no_duplicate_50741_tag`、`test_empty_metadata`、`test_iccprofile`、`test_iccprofile_binary`、`test_sanity`、`test_nonetype`。

这些键都只用到已注册标签或从文件读出的类型；`_save` 的复制循环会用文件或用户给的类型覆盖推断结果。因此 gold 和下文的候选都不会改变它们的结果（静态推断）。

## 3. 需求—测试双向映射（核心）

| # | 公开要求 / 合理旧行为 | 公开依据 | 测试键与决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- | --- |
| R1 | 41988 存 `IFDRational(0,0)` 后 raw 保存，不抛 struct.error | 题面 Example / Actual | `test_exif_div_zero` 中 `save(...)` 不抛异常 | 覆盖 | noop 4 次 ERROR；gold 4 次加 M3 2 次 PASSED；私有 gold 对照 pr6_3 打印 `0 0` |
| R2 | 读回 `[0]` 的分子、分母都是 0 | 题面 Expected 与 `print` | 同一个键的两处 `assertEqual(0, …)` | 覆盖 | 同上 |
| R3 | 读回仍是可下标的元组 | 示例里的 `[0]`；base 对未注册标签的 `length=0` | 同一个键（使用了 `[0]`） | 隐式覆盖 | 静态；K4 可证 |
| R4 | 写成有理数类型 | "retain the rational value" | 同一个键隐式要求：只有类型 5 / 10 能读回分母为 0 | 覆盖，不限定 5 或 10 | 静态；K1b、K3 可证 |
| R5 | 未注册标签写非零分母（1/2） | 由根因推知，题面没要求 | 无 | 缺失（题面范围外） | base 上 FAIL，gold 后 OK（pr3_2，两侧都是镜像实测） |
| R6 | 未注册标签的 float / str 自动识别类型 | 文档 `image-file-formats.rst:503-510` | 无 | 缺失（题面范围外） | — |
| R7 | 走 libtiff 压缩时保存 0/0 | 题面限定 raw | 无 | 不适用 | — |
| P1 | 显式设置的 tagtype 优先 | 公开测试 | `test_rt_metadata` | 覆盖（回归键） | noop 与 gold 都 PASSED |
| P2 | 已注册 RATIONAL 标签的往返（含 IFDRational 形式的 dpi，raw 与 libtiff 两条路径） | 公开测试与 base 代码 | `test_write_metadata`、`test_read_metadata`、`test_ifd_rational_save` | 覆盖 | 同上 |
| P3 | 旧 API `tag` 中有理数是 `(num, den)` | 公开测试 | `test_read_metadata`、`test_rt_metadata` | 覆盖 | 同上 |
| P4 | IFDRational 自身语义 | 公开测试 | `test_sanity`、`test_nonetype` | 部分（0/0 的相等语义不测） | 同上 |
| P5 | 未注册整数标签按 LONG 写出 | 无公开测试，公开材料也没约定 | 无 | 缺失（gold 自己改变了这一点，见 §6） | 静态 |
| P6 | JPEG / MPO 读 EXIF 的结果形状 | 公开代码 | 隐藏测试只含 TIFF 的两个文件 | 缺失（只在改了 `TAGS_V2` 时相关） | — |

**反查。** `test_exif_div_zero` 的每条断言都能追到题面示例；`test_ifd_rational_save` 的依据是 base 已有行为（:1416-1417）；其余 9 个键的依据是公开旧测试。**没有找到只能从隐藏材料得知的要求。**

## 4. 可区分的候选（交协调者用正式评分代码实跑）

- **K1 合理替代解（保守推断）**
  - 改法：在 `PIL/TiffImagePlugin.py` 的 `ImageFileDirectory_v2._setitem` 中，`if tag not in self.tagtype:` 之内、原有 `try:` 之前加一段：若 `tag not in TAGS_V2 and values and all(isinstance(v, IFDRational) for v in values)`，就令 `self.tagtype[tag] = 5`；否则走原逻辑。不改 `TiffTags.py`，未注册整数标签仍按 LONG 写出。
  - 预期得 **1**（11/11）。
  - **K1b**：把 5 换成 10（SIGNED RATIONAL），预期同样得 1，用来证明隐藏测试不限定类型码。
- **K2 可能蒙混的部分实现（只特判零分母）**
  - 改法：位置同 K1，条件改成 `all(isinstance(v, IFDRational) and v.denominator == 0 for v in values)`，同样限定 `tag not in TAGS_V2`。
  - 预期得 **1**（11/11）；但 `info[41988] = IFDRational(1, 2)` 仍会抛 struct.error（在同一容器跑 pr3_2，第 2 行应仍是 FAIL）。
  - 这说明测试只覆盖题面字面范围。题面标题本身就在引导这种修法。因为题面本来就只描述了零分母的情形，这不算违背题意。
- **K3 错误实现（让 LONG writer 接受 IFDRational）**
  - 改法：给 `PIL/TiffImagePlugin.py` 的 `IFDRational` 类加 `def __index__(self): return int(self._numerator)`，其它不动。
  - 预期得 **0**。`TestFileTiffMetadata.test_exif_div_zero` 应观测为 FAILED（`AssertionError: 0 != 1`：按 LONG 读回的 int 分母为 1），其余 10 个键 PASSED。
- **K4 遵循冲突示例的候选（按 EXIF 规范注册 count=1）**
  - 改法：在 `PIL/TiffTags.py` 的 `TAGS_V2` 里加 `41988: ("DigitalZoomRatio", RATIONAL, 1),`。
  - 预期得 **0**。`test_exif_div_zero` 应观测为 ERROR（`TypeError: 'IFDRational' object is not subscriptable`，因为读回的是标量）。
  - 它满足题面文字（保存成功、保留 0/0），但违背示例里的 `[0]`。这正是现代 Pillow 的行为：同仓较新题的初态里，同名测试写的是 `tag_v2[41988].numerator`。
  - **K4b**：把长度写成 0，预期得 1。

**只做静态判断、不必实跑的做法：**

- 只改零分母相关代码（`_limit_rational`、`IFDRational.limit_rational`、`__float__`）：仍在 LONG writer 处失败，得 0。
- 只把猜类型分支变成可达、不加有理数分支：类型变成 7，`len(IFDRational)` 抛 TypeError，得 0。
- 在 `ImageFileDirectory_v2.save` 里、或在 `_save` 复制类型之后，按值的类型把 4 改成 5：得 1。

## 5. R2E 专项

- **(a) 非 PASSED 键**：没有。更完整的修复不会有键被翻转；得 0 的风险只来自改变读回形状（违背示例，见 K4）或破坏 P1–P4。
- **(b) 题面报错是否出现在 noop 目标键的失败里**：是，逐字一致，出现位置正是 LONG writer（4 份 noop 日志都一样）。
- **(c) 题面是否泄漏修法**：没有。标题和描述把原因归到"零分母"，这不准确（pr3_2 证明 1/2 同样失败），但示例本身准确，traceback 指向正确位置。属于误导，不算冲突。
- **(d) 测试辅助、搬迁伪影、撞键**：
  - `helper` 随隐藏测试放入，内容与 base 相同；`r2e_tests` 在 `sys.path[0]`，所以不会用到候选能改的 `Tests/helper.py`。
  - 图片用相对 cwd 的 `Tests/images/...` 路径，runner 的 rootdir 是 `/testbed`。
  - 没有撞键；不用 pytest，所以没有 conftest 问题。
- **(e) 时间 / 随机 / 资源敏感**：没有。测试约 0.02 s，容器内存峰值约 362 MB。唯一的全局状态 `WRITE_LIBTIFF` 已复位。
  - 旁注：noop 里 `test_exif_div_zero` 失败后，后续测试会打印 "orphaned temp file"。这是 helper 只在测试整体成功时才删临时文件造成的，不影响解析。
- **(f) 材料修订**：本题没有修订，不适用。

## 6. gold 检查（方面 5；清单 26、27）

**修到了。**

- 原例：私有对照 pr6_3 打印 `0 0`，隐藏测试 PASSED。
- 根因也修了：41988 写 1/2 能往返，文件类型为 5（pr3_2 私有对照）。
- 做法是把死分支变成可达（`if info.type:`），并在最前面加了 `IFDRational → 5`。因此未注册标签的 float、str、bytes 也能写出了，这与文档 :503-510 说的"自动识别"相符。
- `TagInfo` 默认值改成 `type=None` 的影响：`.type` 在全仓只有 `_setitem` 读取（:496-501）；`named()` 和 DEBUG 只用 `.name`（`grep` 结果）；docs 里也没有 `TagInfo` 的说明。

**附带的行为变化（低严重度，没有测试覆盖，公开材料也没约定）**：未注册的整数标签，若所有值都小于 2\*\*16，类型码从 LONG(4) 变成 SHORT(3)。读回的值不变。

**没修（都在题面范围外、也没测）**：

- libtiff 分支对元组形式的 IFDRational 的处理（公开读者 R7）。
- 负数有理数：`write_rational` 用 `"2L"` 打包会失败，这是原本就有的问题。

没有无关改动，不含测试改动，也不依赖任何未交付的改动。

## 7. 开发需求（方面 6；清单 6–11）

| 条件 | 事实 | 级别 |
| --- | --- | --- |
| 导入 | `python` 是 `/testbed/.venv/bin/python`（3.9.21）；无论在 `/testbed` 还是 `/tmp` 下，`import PIL` 都得到 `/testbed/PIL`；`_imaging.cpython-39-x86_64-linux-gnu.so` 就地编译在 `/testbed/PIL/` 下；zip 解码器和 libtiff 编码器都可用 | 镜像实测（agent 54321，devcheck env / pr0_1） |
| 评分侧导入 | `RH2_OBS_IMPORT_PATH=/testbed/PIL/__init__.py`；noop 的 traceback 也在 `/testbed/PIL` 下 | 评分实测 |
| 依赖 | 不需要新包；没有 pip；有 pytest 8.3.4（带 cov-6.0.0 插件） | 镜像实测 |
| 资产 | `Tests/images/hopper.{ppm,png,tif}`、`hopper_g4.tif`、两个 iccprofile tif 都在工作树里 | 实测 + 本地 |
| 权限与资源 | agent 可写 `/testbed`、`/tmp`（1 GiB）、`/home/agent`（256 MiB tmpfs）；激活文件只读；2 CPU / 4 GiB / pids 512 | 镜像实测（prelaunch） |
| 网络 | 解题不需要网络；外部 DNS 与直连都 DENIED，只能连 relay | 镜像实测 |
| 构建 | 纯 Python 修复，不需要重新编译。不要运行 `make` 或 `make clean`，它们会删掉 `PIL/*.so`（Makefile） | 静态 |
| 公开测试 | 提示推荐的 `python -m pytest` 在本仓 unittest 时代的测试上有**恒定假失败**：凡是用到 `self.tempfile()` 的用例，清理阶段都会报 `AttributeError: 'TestCaseFunction' object has no attribute 'wasSuccessful'`（`Tests/helper.py:32/35`）。计数：三份 TIFF 测试文件 9/42 失败；jpeg/mpo 加 `-k exif` 1/5；libtiff 13 个 FAILED 加 2 个 ERROR，共 22 个。base 与 gold 两侧计数完全相同。改用 `PYTHONPATH=Tests python -m unittest …`，两侧都是 42 个 OK | 镜像实测（pr7_4、pr8_5、pr9_6、pr9_7，私有对照） |
| 自测复现 | 公开读者建议的 R、I 命令能区分修复前后（pr3_2、pr6_3，两侧实测） | 镜像实测 |
| 提交边界 | 改 `PIL/TiffImagePlugin.py`、`PIL/TiffTags.py` 会被投影进去（gold 账本的 `included_paths`）；`__pycache__` 被 `.gitignore` 忽略（运行后 `RH2_GIT_STATUS_LINES=2`） | 评分实测 + devcheck |
| 实际消息 | devcheck 用的是合成的 user 消息（"Devcheck run: …"），`public_hints` 在真实运行时怎样呈现没有抓到 | actor 待验 |
| 镜像 build | 评分证据在 `7a80aa71…`（R-f 机）；devcheck 和私有对照在 `c9ec14f7…`（`derived9` 重建）。两者 recipe `r2e_derive_v1`、来源镜像和 ref 都相同，但隐藏测试没在 `c9ec14f7` 上跑过 | 缺口（低风险） |

## 8. 交付与评分边界（方面 7；清单 4、16–17、21–22、29–31）

- **可交付范围**：合法修复只涉及 `PIL/*.py`，投影能收进去，`ignored_paths` 为空。评分时跳过安装（`RH2_INSTALL_SKIPPED=1`），所以 C 源码的改动不会被重新编译；本题不需要改 C。
- **可信测试恢复**：`RESTORED=5`，隐藏测试树的哈希一致；runner 摘要前后不变。候选可以改 `Tests/images/*`（隐藏测试会读），但这对目标键没有取巧价值。
- **任务相关的交付疑点**：题面示例把 `temp.tiff` 写到当前目录，而 `.gitignore` 不忽略 `*.tiff`。求解者如果在 `/testbed` 照原样运行（或者把 `hopper.png` 复制到根目录），会留下未跟踪的二进制文件。RH2 投影对这类文件是收进、忽略还是判为 unsupported，本次**没有核实**；它属于共享机制，按本题的触发条件列入建议队列 S2。
- **泄漏**：git 没有未来对象的通道（预检和 prelaunch 探针）；工作树里 grep 不到 `test_exif_div_zero`、`test_ifd_rational_save` 或 gold 的代码（本地核对）。网络被禁。
- **共享控制面**（候选代码在评分进程内执行等）：不是本题特有，未重审。
- **旁注（不影响本题）**：设计对照 c（`pillow_sleep.patch`）实际在导入阶段就报了 `SyntaxError: from __future__ imports must occur at the beginning of the file`，测试 0.13 s 就结束了，并没有测到"期限耗尽"。

## 9. 题目关系与用途（方面 8；清单 5、30、37–40）

**同仓包含关系**

- 逐字比对的 gold 扫描**没有**报出本题（上游后来重构了这段代码：拆出 RATIONAL / SIGNED_RATIONAL，改用 `TiffTags.UNDEFINED` 常量，条件写成 `0 <= v < 2**16`）。
- 测试名扫描报出了 6 对。我逐个打开了对方的公开工作树：`src/PIL/TiffTags.py` 的 `TagInfo.__new__(…, type=None, …)`、`src/PIL/TiffImagePlugin.py` 的 `if info.type: … if all(isinstance(v, IFDRational) …)`，以及 `Tests/` 下的 `def test_exif_div_zero`、`def test_ifd_rational_save`，**6 题都有**。
- 这 6 题是：`2b061b68`（8.0.0.dev0）、`2d01f7d0`（8.4.0.dev0）、`4bc64835`（9.1.0.dev0）、`3a61c9e9`（9.2.0.dev0）、`f9d3ee0f`（9.3.0.dev0）、`a682ceaf`（10.1.0.dev0）。
- 反方向：本题 base 是 3.1.0.dev0，在这批里最早，不可能包含其它题的修复（gold 扫描也没有反向命中）。
- **影响**：按题目族记录。如果把后 6 题放进训练、把本题放进评测，训练工作树里就能看到本题的答案，所以两者不宜拆到不同划分。

**外部可达线索**：这个修复存在于 3.1.0 之后的所有 Pillow 版本中，预训练很可能见过。另外，现代 Pillow 对单值标签返回标量，模型如果照现代写法改 `length`，会违背题面示例而得 0（K4）。这一点静态无法度量。

**任务类型**：小型的类型推断 / 序列化缺陷修复；1 个目标键加 10 个回归键。求根因的修法和特判的修法都能得 1，所以本题的奖励**不能区分**"找到了执行不到的分支"与"做了特判"。

## 10. 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 限度 |
| --- | --- | --- |
| 公开需求 | 题面、`public_hints`、环境说明、公开读者记录；base 的 `TiffImagePlugin.py` 相关段、`TiffTags.py` 全文、文档 tiffinfo 一节 | 真实运行时渲染的消息 |
| 材料与初态 | 各项哈希；4 份 noop 日志；devcheck 在 base 上的复现 | — |
| 测试是否测到要求 | 隐藏测试、helper、runner 全读并与公开测试做了 diff；目标键追到 writer 与 loader | — |
| 误拒合理解 | 静态分析 K1–K4 及 3 种不必实跑的做法 | 候选都没实跑 |
| 回归与 gold | gold 全读；查了 `TagInfo` 的所有用户；做了 P1–P6 映射 | 没细追 JPEG / MPO 写 EXIF 的路径（读取路径用的是文件里的类型） |
| 开发条件 | devcheck 的 9 条命令、私有 gold 对照、activation 与 prelaunch 探针 | 真实模型求解；`install.sh` 内容；`.venv` 把 `/testbed` 加进 `sys.path` 的具体机制 |
| 交付与评分边界 | 账本里的 projection、setup 标记、import 路径、runner 摘要 | 未跟踪二进制文件的投影行为；共享控制面 |
| 题目关系 | 两份扫描，外加 6 个工作树的逐个核对 | 同仓以外的重复关系 |

## 11. 缺口与建议队列（交协调者安排）

- **S1（唯一最优先）**：在正式 actor 覆盖表所指的派生镜像上，用正式 grader 跑一批：noop、gold、K1 / K1b、K2、K3、K4 / K4b。这一步同时补上"镜像 build 不同"（§7）和"候选未实跑"两个缺口。
- **S2**：做一次交付形状对照：在 gold 基础上加一个未跟踪的 `/testbed/temp.tiff`（模拟照题面示例原样运行），看投影是收进、忽略还是判 unsupported，以及对得分的影响。若有问题，应在共享机制层面处理，不是本题缺陷。
- **S3**：可以考虑在本题的环境说明里写明"本仓测试是 unittest 风格，pytest 下临时文件的清理报错属于已知噪声，可改用 `PYTHONPATH=Tests python -m unittest`"。这属于环境说明，不是修改题面或测试，也不泄漏答案；是否采纳由协调者决定。
- **S4（actor 待验）**：真实消息的渲染方式与 `public_hints` 的送达；真实模型的求解与交付（清单 33–36）。
- **旁注**：如果还需要"期限耗尽"对照，得重做 `pillow_sleep.patch`，把 sleep 放到 `from __future__` 之后。

## 12. 暂定处置与 checks 草稿

- **处置**：`scope=static_review`；state 保留 `needs_review`，reason 为"静态候选，待 actor 验证"；不修订，`revision_refs` 为空；`intended_use=development_diagnostic`。审查者见过 gold、隐藏测试和运行日志，还没读历史。
- **checks 草稿**（稀疏记录）：
  - **pass**：1、2、4、6、7、8、9、11、13、14、17、18、19、20、21、22（M3 只跑了 gold）、24（静态，待 K1 / K4 实跑）、27、29、30、32。
  - **pass（附说明）**：16——源码改动这种形状已由 gold 实测；未跟踪二进制文件这种形状未知，见 S2。
  - **unknown**：3（真实消息）。
  - **issue（均为低严重度）**：5（被同仓 6 题的初态包含）、10（pytest 的恒定噪声）、23（题面把原因归到零分母）、25（部分修复也能过，见 K2）、26（gold 改变了整数类型码，没有测试）。
  - **not_checked**：15、31、33–36。
  - **not_applicable**：12、28、37–40。

## 附录 A：证据路径（仓库相对路径，已核对 sha256 前缀）

- **评分实测，current**：
  - noop：`runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:40`（日志 `…rer_f4b992c4.eval.log`，2fa76e0c）；`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:40`（7ff66963）；`ledger_r2e_reps_noop.jsonl:2`（6ff6cb73）；`ledger_r2e_requal_noop.jsonl:1`（cef60b11）。
  - gold：`_rerun2/ledger_gold.jsonl:40`（35d322a6）；`ledger_r2e_all_gold.jsonl:40`（a9b2ee4f）；`reps_gold:2`（cb2875ab）；`requal_gold:1`（4747c8eb）。
- **独立参考**：M3 的 gold a1 / a2，`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pillow/3ac9396e8c99/gold/a{1,2}/test_output.txt`（8d37d376 / 613846ec），均为 11 passed。
- **设计对照**：`ledger_r2e_contrast2_{a,b,c}.jsonl:1`，3 次都在导入阶段 SyntaxError，得到 `_FailedTest.test_1/2`。
- **镜像实测**：`runs/r2e_actor_20260925/devcheck/pillow__3ac9396e8c991e7baab66187af2a35c3/orig/{captures/*.out, commands_with_preflight.json, devcheck_stdout.json, prelaunch.json, activation_check.json, post_run_facts_root.txt, attempt.json}`，以及 `private_gold/private_control.json`。

## 附录 B：阅读范围

- **读了**：
  - 角色卡与四份方法文档；`public_read.md`；公开包（`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、manifest 的相关字段）。
  - base 源码：`TiffImagePlugin.py` 的 40-120、200-900、1059-1140、1270-1467 行；`TiffTags.py` 全文；`Tests/test_file_tiff.py` 的 236-320 行；`.gitignore`；docs 的 tiffinfo 一节。
  - 私有包全部内容。
  - 上面列出的账本行与日志；devcheck 目录（`stub/requests/messages_000.json` 只看了首条 user 消息；没读 `harness/trajectory.jsonl`、`stub_log.json`）。
  - 两份跨题扫描；6 个同仓题的公开工作树（只看 `TiffTags.py`、`TiffImagePlugin.py` 的 `_setitem`，以及测试名）。
  - 在 `runs/r2e_env_repair_20260924/` 下只打开了 `_rerun2` 的两个账本行和两个 eval 日志，没读任何汇总文件。
- **没读**：任何 history、review 目录；`docs/.../r2e_env_repair_20260924/`；本批的 README、`assignments.json`、`grader_candidates.md`（只在目录列表里看到文件名）；其它题的私有包；`runs/` 下的分析与汇总文件。
