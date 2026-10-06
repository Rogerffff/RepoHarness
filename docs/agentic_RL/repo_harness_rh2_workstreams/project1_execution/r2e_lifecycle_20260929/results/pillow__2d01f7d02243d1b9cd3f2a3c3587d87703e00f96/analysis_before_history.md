# 主审分析（读历史前封存）：pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96

- 角色：R2E 私有主审，单题闭环试行（2026-09-29），按统一标准 v1 给结论。本稿在读任何历史调查之前写成；devcheck 结果与历史引用都还没拿到。
- 证据层次标记：**[静态]** 读源码推断；**[RH2-current]** 本题当前材料下的历史真实 RH2 评分（`PRV/run_refs.json` 中 `material=current` 的行）；**[M3]** 来源镜像上的独立 runner 参考；**[镜像事实]** M3 在来源镜像里采集的原始环境事实。当前 CPU 实跑与真实模型证据：**无**。
- 路径缩写（都相对仓库根目录）：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`（`PUB/worktree/` 就是解题容器里的 `/testbed`）
  - `PRV/` = `runs/r2e_static_prep_20260924/v3/private/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`
  - `TIP:N` = `PUB/worktree/src/PIL/TiffImagePlugin.py` 第 N 行；`T1:N` = `PRV/hidden_tests/test_1.py` 第 N 行；`UP:N` = `PUB/user_prompt.txt` 第 N 行
  - `OUT/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`

## 0. 暂定结论

1. **题目**：保存 `'1'`/`'L'` 模式 TIFF 时，用户在 `tiffinfo` 里给的 `PhotometricInterpretation`（标签 262）= 0 要被保留。base 先把 `tiffinfo` 抄进 `ifd`（`TIP:1507-1517`），再在 `TIP:1571` 用 `SAVE_INFO` 的值无条件覆盖成 1（`TIP:1459-1460`）。
2. **评分链成立** [RH2-current]：noop 为 0（60/62，两次），gold 为 1（62/62，两次）；M3 独立 runner 上 gold 两次都是 1。目标键 2 个：`TestFileTiff.test_photometric[1]`、`[L]`。死键 2 个：`test_closed_file`、`test_context_manager`，在 pytest 8.3.4 下 `pytest.warns(None)` 直接抛 `TypeError`，任何源码改动都翻不动。其余 58 个是回归键。
3. **目标键同时断言标签和像素往返**：`T1:456` 断言标签为 0，`T1:457` 用 `assert_image_equal(im, reloaded)` 断言重新打开后像素不变。题面只写了标签，没写像素；但公开材料能推出像素要求（见 §3.2），所以记 **P4（登记）**，不记 T1。只改标签的候选 C2 预计得 0，它把图像存成了反相，不算"合理修复被误拒"。**这一点与公开读者"两种做法都合理"的判断不同，请复核专门核对。**
4. **主要缺口（待实跑）**：隐藏测试从不检查"不给 `tiffinfo`"或"显式 262=1"时 `'1'`/`'L'` 仍写 1。退化候选 D 让 `'1'`/`'L'` 一律写 WhiteIsZero（262=0）并反相数据，结果与输入无关，预计 62/62 得 1。实跑若得 1，按 v1 §4 第 3 步判 **S1（T2b）**，修订走 R-c1（附录 B）。
5. **次要缺口（取决于 libtiff）**：隐藏测试没有一个走 libtiff 写出路径。C3 是 gold 漏掉 `encoderconfig` 提升的版本，也是最自然的漏改，预计得 1，但压缩保存时会抛 `AttributeError`。如果镜像编译了 libtiff，我倾向按第 4 步判 S1，修订走 R-c2。
6. **题目关系（X1）**：同仓 4 道更晚的题（`4bc64835`、`3a61c9e9`、`f9d3ee0f`、`a682ceaf`），公开初态里逐字包含本题 gold 和 `test_photometric`；本题 base 包含 `2b061b68`、`3ac9396e` 的修复。
7. **暂定处置**：`needs_review`（静态审查已完成，待退化探测与 actor 验证）。四项用途：问题定位 yes；能力比较 conditional；训练候选在 R-c 前为 no，之后 conditional；留出候选 conditional。
8. **最关键的未知项**：D 的正式评分结果。其次是 actor 侧 devcheck：agent 身份下 PIL 是否从 `/testbed/src` 导入，以及 libtiff 是否可用。

## 1. 读取与暴露范围

- **读了**：
  - 方法文件：角色卡、八方面协议、R2E 环境卡、记录模板、40 项清单、统一标准 v1。
  - 公开侧：`OUT/public_read.md`、`OUT/commands.json`、`PUB/` 全部说明文件，以及 `PUB/worktree/` 中与本题相关的源码、文档和公开测试（见 §2.3 的范围）。
  - 私有包：`hidden_tests/`、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`（内容为 `[]`）、`run_refs.json`。
  - 运行证据：`run_refs.json` 指向的 4 份 eval log 与 3 个账本的第 38 行（sha256 与 `run_refs.json` 一致），M3 的 2 份 `test_output.txt` 和 `r2e_gold_m3.jsonl` 第 11、59 行。
  - M3 在来源镜像采集的原始事实（`runs/env_overnight_20260916/M3/facts/2d01f7d02243/facts/` 下的 `pip_freeze.txt`、`pytest_version.txt`、`pyver.txt`、`pth.txt`、`egg.txt`、`pkg_origin.txt`、`import_origins.json`、`run_tests_meta.txt`、`xvfb.txt`、`ls_testbed.txt`），只读原始输出。
  - 两份跨题扫描文件，以及同仓其它 6 题公开包中的题面标题、版本号，并用 grep 查了 gold 行与测试名。
- **没读**：任何 `history/`、审查目录、本批 README、`board.json`、`assignments.json`、`runs/` 下的分析或汇总文件、其它题的私有包。M3 目录里名称带 summary、leak、scrub 的文件也没有打开。
- **做过的"执行"**：没有运行项目代码。只在 scratchpad 里对 base `TiffImagePlugin.py` 的副本和隐藏测试副本做了 `git apply --check`，并用 `python3 -m py_compile` 检查语法。另外用标准库 `struct` 读了 5 张公开测试图片的 TIFF 头（只读字节，不导入 PIL）。

## 2. 公开读者没有捕获的真实条件（第 1 步）

公开读者的需求表（R1–R9）、成因链和命令基本准确。下面是它没有、也无法捕获的条件：

| 条件 | 事实 | 证据 | 影响 |
| --- | --- | --- | --- |
| pytest 版本 | 8.3.4 | eval log 第 16 行 [RH2-current]；`pytest_version.txt` [镜像事实] | `PUB/worktree/Tests/test_file_tiff.py:67,75` 的 `pytest.warns(None)` 在 base 和修复后都会失败，所以 `commands.json` 中 `public_tiff_tests` 写的 `expect: zero` 在这个环境下**必然不成立**。这是命令预期写错，不是题目或环境缺陷（见 §8.1）。 |
| PIL 导入方式 | 通过 `__editable__.Pillow-8.4.0.dev0.pth` 可编辑安装，指向 `/testbed/src`；导入路径是 `/testbed/src/PIL/__init__.py` | `pth.txt`、`pkg_origin.txt` [镜像事实，root]；账本观测 `RH2_OBS_IMPORT_PATH` [RH2-current，评分用户 54322] | 公开读者的头号未知项在评分侧已经回答：改源码会生效。agent 身份下仍待 devcheck `env_import` 确认。 |
| pip / defusedxml / packaging | venv 里没有 pip；没有 defusedxml，所以 `test_getxmp` 走告警分支，仍然 PASSED；有 packaging | `pip_freeze.txt`、`import_origins.json` [镜像事实] | 纯 Python 修复不受影响。 |
| libtiff | **未知** | 没有证据 | 决定压缩路径能否自测，也决定 C3 和 R-c2 是否有意义。 |
| 根目录 conftest | `PUB/worktree/conftest.py:1` 写着 `pytest_plugins = ["Tests.helper"]`，隐藏测试运行时也会导入 base 的 `Tests/helper.py` | 源码 [静态]；日志显示能正常收集 | 候选如果改坏 `Tests/helper.py`，会让整次收集出错。隐藏测试用的是自带的 `r2e_tests/helper.py`，与 base 逐字相同，所以候选无法借改 helper 放宽断言。 |
| 颜色与键格式 | `setup.cfg` 的 `addopts = -ra --color=yes`（`PUB/worktree/setup.cfg:9`），期望键外面包着 ANSI 粗体码 | `PRV/expected_output.json` | parser 已按 `prime_decolor_v1` 处理；noop 与 gold 两次 `keys_equal=true`。 |
| 实际发给模型的消息 | 未捕获，只有静态渲染的 `user_prompt.txt` | 环境卡 §2 | 记为未验证。 |

## 3. 隐藏测试展开（第 2 步）

`PRV/hidden_tests/test_1.py` 就是 base 的 `Tests/test_file_tiff.py` 加上 `test_photometric`：两者 diff 只有 `T1:450-458` 这 9 行。`helper.py` 与 base 的 `Tests/helper.py` 逐字相同。收集到 64 项：62 个成键，另有 2 个 SKIPPED（`test_string_dimension` 缺附加图片；`TestFileTiffW32.test_fd_leak` 只在 Windows 上跑）。

### 3.1 目标键：`TestFileTiff.test_photometric[1]`、`[L]`（`T1:450-457`）

- **调用路径**：先调 `hopper(mode)`（`helper.py:242-260`）：读 `Tests/images/hopper.ppm`，`convert` 成 `'1'`（抖动后只有 0 和 255）或 `'L'`，再 `.copy()`。然后 `im.save(filename, tiffinfo={262: 0})`，经 `Image.save` 设置 `encoderinfo` 和 `encoderconfig=()`（`Image.py:2208`），进入 `TiffImagePlugin._save`。因为 `compression` 缺省为 `raw`，所以走未压缩分支 `TIP:1710-1715`。最后 `Image.open` 重新打开。
- **断言 1（`T1:456`）**：`reloaded.tag_v2[262] == 0`。直接对应题面（`UP:7,22,26`）。noop 在这里失败，报 `assert 1 == 0`，两个参数都是 [RH2-current]，与题面 Actual Behavior（`UP:28-29`）一致。
- **断言 2（`T1:457`）**：`assert_image_equal(im, reloaded)`，比较 mode、size 和 `tobytes()`（`helper.py:89-100`）。比较对象是**调用方在保存之后的** `im`。
  - 读取端对 262=0 会反相解码：`'1'` 用 `'1;I'`（`TIP:136`），`'L'` 用 `'L;I'`（`TIP:160`）。
  - 所以要通过这一条，写 0 时必须把像素反相后再写（gold 就是这么做的），或者用等价的 packer，例如 `'1'` 已有的 `'1;I'`（`Pack.c:547`）。
  - noop 在断言 1 就失败了，没走到这里。按源码推断，base 若能走到这一步是会通过的，因为 base 写 1、像素原样写出 [静态]。
- **这组键测到什么**：两种模式都有，而且是 hopper 这种非恒定内容，不是题面那张全黑图；只走未压缩写出；`tiffinfo` 只用 dict 形态。

### 3.2 像素断言的公开依据（决定 P4 还是 T1）

题面只说标签要保留（`UP:26`）。但以下公开材料都指向"写 0 时图像内容要往返不变"：

1. **Pillow 自己的读取语义**：262=0 的 `'1'`/`'L'` 文件读入时会反相（`TIP:136,160`；`Unpack.c:1474,1491`）。所以内存里的 `'1'`/`'L'` 永远是 0 表示黑。文档把这两个模式描述为 black and white 像素（`PUB/worktree/docs/handbook/concepts.rst:32-33`）。
2. **公开测试明确把 WhiteIsZero 文件与 BlackIsZero 文件断言为同一图像**：`test_gray_semibyte_per_pixel`（公开 `Tests/test_file_tiff.py` 中的同名测试，也就是隐藏的 `T1:496-527`）比较 `hopper2I.tif` 与 `hopper2.tif`。我读了图片头：前者 262=0，后者 262=1。
3. **公开往返惯例**：`PUB/worktree/Tests/test_file_libtiff.py:110-122` 的 `test_g4_write`，docstring 写着 "saved image is the same as what we wrote"，并断言 `assert_image_equal(reread, rot)`。
4. **base 对题面原例本来就往返一致** [静态]：标签错了，但像素对。只改标签的修复会让题面这张全黑图重新打开后变成全白（`pixel00` 255），新引入的正是题面说的 "inconsistencies in how the images are processed or displayed"（`UP:7`）。
5. **公开工作流**：公开测试 `test_file_libtiff.py:139-158` 用 `tiffinfo=img.tag` 重存一张 WhiteIsZero 的 G4 图（`hopper_g4.tif`，262=0，我读了文件头）。修复之后这个常见的"拷贝标签重存"会写出 262=0；如果只改标签，写出的图就会整体反相。
6. **结构性标签的一致性**：`_save` 在抄完 `tiffinfo` 之后，会覆盖 BitsPerSample、SamplesPerPixel 等所有决定数据解释方式的标签（`TIP:1562-1571`），为的是让文件自洽。262 正属于这类标签，所以改它时必须同时改数据。

**判断**：只改标签（C2）会写出标签和数据互相矛盾的文件，而且破坏了 base 在这个输入上原本正确的往返，不满足"不破坏受影响旧行为"。因此不是被误拒的合理解，而是"只符合题面某一句的候选"（第二批规则 1）。按 v1 §3，这里记 P4（描述不全，公开材料能消解），登记即可。公开读者从字面出发认为两种都合理，说明题面措辞确实会让一部分解题者走错。是否用 R-f 补一句，见 §10。

### 3.3 回归键与死键

- **死键 2 个**：`test_closed_file`（`T1:66-72`）和 `test_context_manager`（`T1:74-79`）。期望为 FAILED；noop、gold 和 M3 都失败在 `pytest.warns(None)`，报 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`（`.venv/.../_pytest/recwarn.py:279`）。测试体在执行任何 Pillow 代码之前就失败了，**更完整的修复也翻不动**，只有改测试基础设施才会改变结果。属于 T5，无害（见 §9）。
- **保存类回归键 14 个**，都会经过 `_save`，因此保护了 gold 对 `encoderinfo` 的提升改动：`test_sanity`（RGB/1/L/P/I 的保存和打开）、`test_save_float_dpi`、`test_save_setting_missing_resolution`、`test_save_rgba`、`test_save_unsupported_mode`、`test_with_underscores`、`test_roundtrip_tiff_uint16`、`test_palette`（P/PA）、`test_tiff_save_all`（`_save_all` 加追加帧）、`test_saving_icc_profile`（`compression="raw"`）、`test_save_icc_profile`、`test_discard_icc_profile`、`test_close_on_load_exclusive`、`test_close_on_load_nonexclusive`。
- **读取类回归键 44 个**：只断言读取行为；本题改的是写出端，逐条没有展开。
- **没有被任何键覆盖的**：
  1. `'1'`/`'L'` 不给 `tiffinfo` 时写出的标签值（`test_sanity` 只保存再打开，不看标签）；
  2. 显式 262=1；
  3. libtiff 写出分支 `TIP:1607-1708`（隐藏测试里所有保存都是未压缩）；
  4. `tiffinfo` 用 IFD 对象或元组值的形态；
  5. 其它模式或其它 262 值；
  6. 保存过程中调用方的图像有没有被改动。
- **阅读范围**：`test_1.py` 全文；`helper.py` 中目标键用到的函数；`TIP:128-170`、`TIP:417-646`、`TIP:1295-1315`、`TIP:1440-1740`、`TIP:1961-1983`；`ImageOps.py:49-58,516-526`；`Image.py:166,199,2208`；`ImageFile.py:488-528`；`Pack.c:538-560`；`Unpack.c` 的查表行；相关文档和公开测试段落。**没读**：libtiff 编码器和解码器的 C 实现（`encode.c`、`TiffDecode.c`）、`_load_libtiff`、`AppendingTiffWriter` 的细节、`setup.py`。

## 4. 双向映射（第 3 步）

**公开要求 → 断言**

| 编号 | 要求或合理旧行为 | 公开依据 | 测试与断言 | 覆盖 | 证据或下一步 |
| --- | --- | --- | --- | --- | --- |
| R1 | `'L'`、未压缩、`tiffinfo={262:0}` → 重新打开后 262 为 0 | `UP:7,13-22,25-26` | `test_photometric[L]`，`T1:456` | 覆盖 | noop 失败于 `assert 1 == 0`；gold PASSED [RH2-current] |
| R2 | `'1'` 同上 | `UP:4,7` | `test_photometric[1]`，`T1:456` | 覆盖（非示例实例） | 同上 |
| R6 | 写 0 时图像内容往返不变 | §3.2 的六条 | `T1:457` | 覆盖；依据来自推断，题面未明写 → P4 | gold PASSED；C2 预计失败于 `T1:457` |
| R3 | 不给 `tiffinfo` 时 `'1'`/`'L'` 仍写 1 | `TIP:1459-1460`；`PUB/worktree/Tests/test_file_libtiff.py:151-152` 的注释；题面只针对"已指定 0"的情况 | 无 | **缺失** | D 预计得 1 → 实跑 |
| R3′ | 显式 262=1 保持 1 | `UP:7,26`："retain / accurately reflecting the specified photometric interpretation" | 无 | **缺失** | 同上 |
| R4 | 压缩（libtiff）保存同样保留 0，且往返不变 | 题面没有限定压缩方式；`image-file-formats.rst:906-912` 把 `compression` 列为 TIFF 保存选项；覆盖发生在路径分叉之前（`TIP:1571`，早于 `TIP:1607`） | 无 | **缺失** | C3 预计得 1；取决于 libtiff |
| R8 | `tiffinfo` 用 IFD v1/v2 或 `{262: (0,)}` | `image-file-formats.rst:871-879`；`TIP:1510-1517` | 无 | 缺失（边缘） | 登记为 T3 |
| R5/R9 | 其它模式或其它值（例如 RGB 给 0，`'L'` 给 2） | 题面没有涉及 | 无 | 未规定 | gold 扩大了行为，见 §6 |
| O1 | 其它保存选项不回归 | base 行为 | 14 个保存类键 | 覆盖（未压缩路径） | noop 与 gold 都 PASSED |
| O2 | 读取行为不变 | base 行为 | 44 个读取类键 | 覆盖 | 同上 |

**关键断言 → 公开依据**：`T1:456` 直接来自题面；`T1:457` 来自公开推断（§3.2），题面没有字面；`T1:67,75` 与本题无关（环境里 pytest 的版本问题）。

## 5. R2E 专项（第 4 步）

- **(a) 期望里的非 PASSED 键**：只有上面两个死键，原因是 pytest 8.3.4 不再接受 `pytest.warns(None)`。它们在执行任何项目代码之前失败，正确修复、包括更完整的修复都不会把它们变成 PASSED。其它 60 个键都是 PASSED，没有需要继续失败的目标键。
- **(b) 题面描述的报错是否出现在 noop 失败原因里**：出现了。两个目标键都失败在 `T1:456`，报 `assert 1 == 0`，与 `UP:28-29` 一致 [RH2-current]。
- **(c) 题面是否泄漏修法**：没有。题面只描述症状，没提反相，也没给代码。`CHANGES.rst` 和 `docs/releasenotes/` 里查不到 photometric 相关条目。不构成 P1。
- **(d) 测试支撑与搬迁伪影**：
  - `from .helper import ...` 用的是隐藏目录里的 helper，与 base 相同，由 grader 控制。
  - 图片按 cwd 相对路径 `Tests/images/...` 读取，cwd 是 `/testbed`，所以搬迁不影响。
  - 根目录 conftest 会导入 base 的 `Tests.helper`，改坏它只会让收集失败（§2）。
  - 只有一个测试文件，不存在跨文件撞键。
- **(e) 时间、随机、资源敏感**：没有。整套 0.28–0.32 s，内存峰值约 503 MB（账本）。
  - `test_unclosed_file` 依赖 CPython 用引用计数回收文件对象时发出的 `ResourceWarning`，结果是确定的；四次运行都是 PASSED。
  - `test_getxmp` 在有无 defusedxml 两个分支下都有断言；这个镜像没有 defusedxml。
- **(f) 材料修订**：没有（`revisions.json` 为 `[]`）。

## 6. gold 检查（第 5 步）

- **原例与目标**：按源码推断（[静态]），gold 修复了 R1、R2、R3、R3′、R8，也修复了 R4 的标签与像素。R4 是因为修改点位于分叉之前，并且提升了 `encoderconfig`。隐藏测试实际验证了 R1、R2 和 R6（gold 62/62 [RH2-current]、[M3]）。题面原例本身没有逐字实跑，devcheck 的私有 gold 对照会跑 `repro_issue_mode_l`，预期输出 `tag262 0 mode L pixel00 0`。
- **题面之外、没有测试覆盖的改动（G1，不作为处置依据）**：
  1. **范围扩大**：`if PHOTOMETRIC_INTERPRETATION not in ifd` 对**所有模式、所有值**都尊重用户给的 262。结果是 RGB 配 `{262: 0}`、`'L'` 配 `{262: 2}` 都会写出 Pillow 自己打不开的文件（`OPEN_INFO` 里没有对应键，`TIP:1305-1308`），而 base 会把它覆盖成正确的值。常见触发方式是把源图的 `tag` 当 `tiffinfo` 用来保存另一种模式的图。
  2. **`'1'` 用 Python 逐像素循环反相**，耗时 O(W·H)。对大幅二值图（几百万像素）会很慢，但结果正确。
  3. **libtiff 分支里原图标签不再合并**：反相后 `im` 换成新对象，`TIP:1653-1657` 不再合并原 TIFF 的 `tag_v2` 和 `tag`。只有"打开的 TIFF + 压缩 + 262=0"这个组合会丢失未经 `tiffinfo` 传入的标签。
  4. **`_debug_multipage`** 被设置到新对象上，只影响调试辅助。
  - 以上都不影响本题评分。其中 1 说明 gold 不是唯一合理实现：更窄的实现（C1）同样应当得 1。
- **无关改动**：没有。对 `encoderinfo`、`encoderconfig` 的提升是反相后重新赋值 `im` 的必要配套。

## 7. v1 §4 严重度五步（读历史前）

| 步骤 | 判断 | 证据 | 结论 |
| --- | --- | --- | --- |
| 1 核心要求有无直接断言 | 有：`T1:456` 覆盖两种模式 | §3.1 | 未命中 |
| 2 是否只用题面示例的字面值 | 模式维度超出了示例（多了 `'1'`），图像内容也不同（hopper，不是全黑图）。但保存调用的形态与示例相同：dict 形式的 `tiffinfo`、未压缩写出 | §3.1 | **未命中**。压缩路径留给第 4 步由 C3 判断 |
| 3 退化探测 | D：`'1'`/`'L'` 一律写 WhiteIsZero 并反相，与输入无关 | 附录 A.1；违例依据见 §8.2 | **待实跑**。预计得 1，若成立即 **S1（T2b）** |
| 4 已有候选在同一核心要求的其它实例上违例 | 没有真实模型候选。构造候选 C3 若得 1，就在压缩保存（有文档、而且是 262=0 最常见的 G4 用法）上崩溃 | 附录 A.4 | **待实跑，取决于 libtiff**。我倾向判 S1；如果复核认为压缩属于罕见路径，则为 S2（T3） |
| 5 以上都不命中 | — | — | 暂不适用 |

**暂定严重度**：conditional，预计为 S1（T2b）。D 的实跑结果是决定性证据。

## 8. 候选与需要协调者实跑的内容（第 3 步输出）

### 8.1 devcheck 读数（已在跑）

逐条记录退出码与关键输出；预期都是 [静态] 推断。

| id | base（noop） | gold 对照 | 备注 |
| --- | --- | --- | --- |
| `env_import` | `/testbed/.venv/bin/python 3.9.21`；`PIL 8.4.0.dev0 /testbed/src/PIL/__init__.py`；`TiffImagePlugin` 在 `/testbed/src/PIL/`；`core` 是 `_imaging*.so`；**`libtiff` 为 True 还是 False**；`pytest 8.3.4` | 相同 | libtiff 的结果决定 C3 与 R-c2 是否有意义 |
| `repro_issue_mode_l` | 非 0；`tag262 1 mode L pixel00 0` | 0；`tag262 0 mode L pixel00 0` | 同时核实"原例可复现" |
| `repro_mode_1` | 非 0；`tag262 1 mode 1 pixel00 0` | 0；`tag262 0 mode 1 pixel00 0` | |
| `default_photometric_kept` | 0；`L 1 77 \| 1 1 255 \| RGB 2 (1, 2, 3)` | 相同 | 这条也是 D 的违例对照 |
| `public_tiff_tests` | **非 0**：只有 `test_closed_file`、`test_context_manager` 失败（`TypeError ... NoneType`） | 同样只有这 2 个失败 | 公开读者写的 `expect: zero` 是命令预期错误；如果还有其它失败，必须逐个解释。表头的 pilinfo 也会显示 libtiff 支持情况 |
| `compressed_path_observe` | libtiff 可用：`tag262 1 compression tiff_lzw pixel00 0`；不可用：先打印 `libtiff False`，再抛 `OSError` | libtiff 可用时 `tag262 0 ... pixel00 0` | |

修正后的命令（按公开依据：环境里的 pytest 版本；两处失败与本题无关）：
`public_tiff_tests_v2`（`timeout_s` 900，`expect` zero）：

```bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider Tests/test_file_tiff.py Tests/test_file_tiff_metadata.py Tests/test_file_libtiff.py::TestFileLibTiff::test_write_metadata --deselect Tests/test_file_tiff.py::TestFileTiff::test_closed_file --deselect Tests/test_file_tiff.py::TestFileTiff::test_context_manager
```

### 8.2 正式评分候选（当前材料、新机器重建的 `r2e_derive_v1` 派生镜像，每个跑 1 次）

| 候选 | 改哪里、怎么改 | 预计结果 | 能区分什么 | 优先级 |
| --- | --- | --- | --- | --- |
| **D（退化，v1 §4 第 3 步）** | `TIP:1571`：`'1'`/`'L'` 一律 `ifd[262] = 0`；`'1'` 改用 rawmode `'1;I'`，`'L'` 用 `ImageOps.invert` 并复制 `encoderinfo`/`encoderconfig`；其它模式不变。完全不看 `tiffinfo` 给了什么（"与输入无关的固定结果"，也是"关掉检查"）。补丁见附录 A.1 | **1**（62/62） | 得 1 → S1（T2b） | **最高** |
| C1（合理替代解） | 只在 `'1'`/`'L'` 且用户给 0 时保留 0；`'1'` 用 C 层现有的 `'1;I'` packer，`'L'` 用 `point` 反相并复制属性；其它模式和其它值保持 base 的覆盖行为（范围比 gold 窄）。见附录 A.2 | **1** | 核实没有对 gold 的实现方式和扩大后的范围过拟合；也可作 R-c 的替代正对照 | 高 |
| C3（可能蒙混的部分实现） | gold 去掉 `encoderconfig = im.encoderconfig` 的提升，libtiff 分支仍用 `im.encoderconfig`（只差两行）。见附录 A.4 | **1**（隐藏测试都不走 libtiff） | libtiff 可用时，第 4 步判 S1 还是 S2 | 中（libtiff 为 False 时跳过） |
| C2（只改标签） | `TIP:1571` 改为：只有 `'1'`/`'L'` 且 `ifd.get(262) == 0` 时不覆盖；像素不处理。见附录 A.3 | **0**：60/62，`test_photometric[1]`、`[L]` 失败于 `T1:457`，报 "got different content" | 为 P4 判断补执行证据（结果静态上已经确定） | 低（可选） |

**评分有效性核对**（每个候选都要做）：eval log 头部有 `M src/PIL/TiffImagePlugin.py`；账本 `projection.included_paths` 包含这个文件；`test_photometric[1]`、`[L]` 和 `test_sanity` 实际执行了；`keys_equal=true`。应用失败或收集错误都不能当作"被测试拒绝"的证据。

**D 的违例证明**（私有容器，应用候选，不评分）：

1. 复用公开命令 `default_photometric_kept`：gold 和 base 退出 0；D 预计打印 `L 0 77 | 1 0 255 | RGB 2 (1, 2, 3)` 后抛 `AssertionError`。违反的是 base 的默认值（`TIP:1459-1460`）和 R3。
2. 显式写 1（`explicit1`，`expect` zero）：gold 预计 `tag262 1 pixel00 77`；D 预计 `tag262 0` 并抛 `AssertionError`。违反 `UP:7,26`，即"保留指定的 photometric interpretation"。

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; p='/tmp/r2e_pi_explicit1.tif'; Image.new('L', (8, 8), 77).save(p, tiffinfo={262: 1}); r=Image.open(p); print('tag262', r.tag_v2[262], 'pixel00', r.getpixel((0, 0))); assert r.tag_v2[262] == 1, 'explicit BlackIsZero not kept'"
   ```

**C3 的违例证明**（只在 libtiff 可用时做）：复用 `compressed_path_observe`。gold 预计 `tag262 0 ... pixel00 0`；C3 预计抛 `AttributeError: 'Image' object has no attribute 'encoderconfig'`（原因：`Image.py:2208` 只在 `save()` 里设置这个属性，而新对象没有）。另外用下面的 `g4_whiteiszero_roundtrip` 先核 gold 能否通过 R-c2：gold 预计 `tag262 0 same True`，C3 预计 `AttributeError`。

```bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; im=Image.open('Tests/images/hopper.ppm').convert('1'); p='/tmp/r2e_pi_g4.tif'; im.save(p, tiffinfo={262: 0}, compression='group4'); r=Image.open(p); print('tag262', r.tag_v2[262], 'same', r.tobytes() == im.tobytes()); assert r.tag_v2[262] == 0 and r.tobytes() == im.tobytes()"
```

## 9. 问题清单（v1 §3 编号）

| 编号 | 内容 | 证据层次 | 暂定严重度与去向 |
| --- | --- | --- | --- |
| **T2（T2b，待实跑）** | 默认值和显式 1 没有断言；D 预计得 1 | [静态] | 若 D=1 → **S1**，走 R-c1 |
| T2 或 T3（待实跑） | libtiff 写出路径没有覆盖；C3 预计得 1 | [静态] | libtiff 可用且 C3=1 → 倾向 S1，走 R-c2；libtiff 不可用 → 在本环境不可观测，只登记 |
| P4 | 题面没写像素语义（像素要求有公开依据，§3.2）；示例只定义函数、没有调用（`UP:13-22`）；示例把 `temp.tif` 写到 cwd | [静态]；公开读者对这点有不同读法 | 登记；R-f 可选（§10） |
| T3 | `tiffinfo` 的 IFD 或元组形态、其它模式和值、多帧保存、保存时调用方图像被就地改动（像素断言比的是保存后的 `im`，所以"只改标签，再把调用方图像就地反相"的候选也能通过，但这太刻意，本轮没有构造运行），都没有覆盖 | [静态] | S2 级缺口，登记 |
| T5 | 2 个死键（pytest 8.3.4 与 `pytest.warns(None)` 不兼容），期望为 FAILED 且稳定，对判别无害 | [RH2-current]、[M3] | 不必处理；如果本题进入 R-c 修订，可顺带做 R-a（删测试并删期望键） |
| X1 | 4 道更晚的题公开初态含本题 gold 和 `test_photometric`；本题 base 含 2 道更早的题的修复 | 两份扫描文件加公开包 grep 核实 | 登记；训练时控制重复采样；按仓库划分留出（D3） |
| G1 | gold 对所有模式和值都放行用户给的 262；`'1'` 逐像素循环很慢；libtiff 分支丢失原图标签 | [静态] | 不作处置依据 |
| H1 | 照原样运行题面示例，会在 `/testbed` 留下 `temp.tif` | [静态] | 训练设计侧处理 |
| E | 评分侧没有问题；actor 侧待 devcheck。另外有 2 个与本题无关的公开测试恒失败（环境卡 §2 已预告"与本题无关的恒失败公开测试"） | [RH2-current] | 按 §8.1 修正命令，并在开发说明里如实交代 |

## 10. 修订建议（按模板，条件触发）

- **R-c1**（D 实跑得 1 就做）：
  - 在 `PRV/hidden_tests/test_1.py` 的 `test_photometric` 之后加 `test_photometric_blackiszero_kept`，补丁见附录 B.1。新增 4 个键，期望全为 PASSED：`[1-default]`、`[L-default]`、`[1-explicit1]`、`[L-explicit1]`，写法按现有键格式。
  - 公开依据：`UP:7,26`（保留指定的值，覆盖显式 1）；`TIP:1459-1460` 和 `PUB/worktree/Tests/test_file_libtiff.py:151-152`（默认值）；题面范围只涉及"已指定 0"。
  - 验收：gold 为 1；noop 为 0（新键在 noop 上 PASSED，只有目标键失败）；D 为 0（4 个新键失败，触发反例得到纠正）；C1 为 1（替代正对照）；C2 为 0；C3 不受影响。
  - 修订后仍受保护的公开要求：R1、R2、R6、R3、R3′。
- **R-c2**（libtiff 可用且 C3=1 时做，可与 R-c1 同一轮完成）：
  - 加 `test_photometric_compressed`，覆盖 `'1'` 配 `group4`、`'L'` 配 `tiff_lzw`，补丁见附录 B.2。
  - 前提：派生镜像确实有 libtiff，否则所有人都会失败。gold 要先用 §8.2 的 `g4_whiteiszero_roundtrip` 和 `compressed_path_observe` 预核通过。
  - 验收：gold 为 1；noop 为 0；C3 为 0；C1 为 1；C2 为 0。
- **R-a（可选）**：删除 `T1:66-79` 的两个死测试，同时删除两个 FAILED 期望键，确认没有 unexpected。证据是 eval log 里 pytest 自身抛出的 `TypeError`。不影响判别，只在做 R-c 时顺带处理。
- **R-f（暂不建议）**：像素语义有公开依据（§3.2），我判断不属于"解题必需"。如果复核认为公开材料消解不了，或者探针里大量出现只改标签的尝试，可以按 R-f 第 3 类补一句已有公开依据的说明。示例措辞："Reopening the saved file should still give the same image as the one that was saved, just as when no PhotometricInterpretation is given."（只陈述行为，不含隐藏测试的输入或 helper 名）。
- **待用户决定**：无。

## 11. 开发需求（第 6 步）

| 项 | 需求 | 证据与级别 |
| --- | --- | --- |
| 导入 | 改 `/testbed/src/PIL/*.py` 直接生效，不需要重装 | 可编辑 `.pth` [镜像事实，root]；评分用户下导入路径为 `/testbed/src/PIL/__init__.py` [RH2-current]；**agent 身份待验**（`env_import`） |
| 依赖 | 纯 Python 修复只用仓内的 `ImageOps` 和 C 层现有 packer；venv 没有 pip，也不联网 | [镜像事实]；环境简报 `PUB/environment_brief.md:10-12` |
| 资产 | `Tests/images/hopper.ppm` 等图片在工作树里；缺 `string_dimension.tiff`，对应测试跳过 | [RH2-current] |
| 权限 | agent（uid 54321）要能写 `src/PIL/TiffImagePlugin.py`；评分时以 `agent/54321` 身份应用 gold，`APPLY_RC=0` | 账本 `candidate.apply_user` [RH2-current]；解题中的写权限见简报 `:12`，待 devcheck 核实 |
| 网络 | 准备、解题、安装、测试四个阶段都不需要 | [静态] |
| 构建 | 纯 Python 修复不需要构建。若走 C 路线（例如新增 `'L;I'` packer），需要在容器里重编译，并确认正式导出带上 `.so`、grader 实际加载了新产物；编译器是否可用未知。这条路线**不是必需的**，也未验证 | [静态] |
| 自测 | 复现与默认值命令按 §8.1；公开测试有 2 个基线失败；libtiff 决定能否自测压缩路径 | devcheck 待给 |
| 提交边界 | 只需改 `src/PIL/TiffImagePlugin.py`；不要改 `Tests/`（根目录 conftest 会导入 `Tests/helper.py`）；照原样跑示例会在 `/testbed` 留下 `temp.tif`（H1） | [静态] |
| 资源与时间 | 隐藏测试 0.3 s；公开最小验证预计几秒（devcheck 会记录墙钟时间） | [RH2-current] |

## 12. 用途结论（v1 §2，暂定）

- `problem_localization`：**yes**。
- `capability_comparison`：**conditional**。还差三件事：
  1. 新机器重建的派生镜像上，noop 为 0、gold 为 1（旧镜像 `sha256:b4030960…` 的结果不能直接替代）；
  2. actor devcheck 证明 agent 身份下能导入并复现；
  3. 如果 D 得 1，在修订前参与比较的题，其得 1 的补丁要按预登记做事后审计，核对"默认值和显式 1 是否保持"。
- `training_candidate`：**no（R-c1 之前）**。若 D 得 1，需要 R-c1（加上 libtiff 情况下的 R-c2）验收并经 Codex 复核后才能转 conditional 或 yes；若 D 意外得 0，要看第 4 步的 C3 结果和第 5 步。
- `heldout_candidate`：**conditional**。除训练候选的条件外，还要满足：X1 的 4 道更晚的题与本题同仓，按仓库划分会落在同一侧；修订后只能作为"标明版本的自建题"。

## 13. 缺口、未知与唯一下一步

- **未知**：
  1. D、C1、C3 的正式评分结果；
  2. libtiff 是否可用；
  3. actor 身份下的导入、写权限和公开命令行为；
  4. 新镜像上 noop 与 gold 的复核；
  5. 真实模型会产出什么样的补丁（例如只改标签的比例）。
- **探针就绪差距**：本批 README §3 按派发说明没有读；写 `card.md` 时请协调者提供 §3 的条款原文，我再逐条对照。
- **唯一最值得先做的下一步**：用正式评分跑一次退化候选 D（附录 A.1），同时核对补丁确实交付、目标键确实执行；并从 devcheck `env_import` 读出 libtiff 状态，决定是否还要跑 C3。

---

## 附录 A：候选补丁

四份补丁都能对 base 的 `src/PIL/TiffImagePlugin.py` 直接 `git apply`（已用 `git apply --check` 验证，打补丁后的文件已通过 `py_compile`）。

### A.1 D：退化候选（一律 WhiteIsZero）

```diff
diff --git a/src/PIL/TiffImagePlugin.py b/src/PIL/TiffImagePlugin.py
--- a/src/PIL/TiffImagePlugin.py
+++ b/src/PIL/TiffImagePlugin.py
@@ -48,7 +48,7 @@ from collections.abc import MutableMapping
 from fractions import Fraction
 from numbers import Number, Rational
 
-from . import Image, ImageFile, ImagePalette, TiffTags
+from . import Image, ImageFile, ImageOps, ImagePalette, TiffTags
 from ._binary import o8
 from .TiffTags import TYPES
 
@@ -1568,7 +1568,18 @@ def _save(im, fp, filename):
     if format != 1:
         ifd[SAMPLEFORMAT] = format
 
-    ifd[PHOTOMETRIC_INTERPRETATION] = photo
+    if im.mode in ("1", "L"):
+        # always store bilevel / greyscale images as WhiteIsZero
+        ifd[PHOTOMETRIC_INTERPRETATION] = 0
+        if im.mode == "1":
+            rawmode = "1;I"
+        else:
+            inverted = ImageOps.invert(im)
+            inverted.encoderinfo = im.encoderinfo
+            inverted.encoderconfig = im.encoderconfig
+            im = inverted
+    else:
+        ifd[PHOTOMETRIC_INTERPRETATION] = photo
 
     if im.mode in ["P", "PA"]:
         lut = im.im.getpalette("RGB", "RGB;L")
```

### A.2 C1：合理替代解（范围更窄，用 packer 反相）

```diff
diff --git a/src/PIL/TiffImagePlugin.py b/src/PIL/TiffImagePlugin.py
--- a/src/PIL/TiffImagePlugin.py
+++ b/src/PIL/TiffImagePlugin.py
@@ -1568,7 +1568,20 @@ def _save(im, fp, filename):
     if format != 1:
         ifd[SAMPLEFORMAT] = format
 
-    ifd[PHOTOMETRIC_INTERPRETATION] = photo
+    requested_photo = ifd.get(PHOTOMETRIC_INTERPRETATION)
+    if im.mode in ("1", "L") and requested_photo == 0:
+        # WhiteIsZero was requested: keep the tag and store inverted samples,
+        # so that readers (Pillow included) decode the same image.
+        ifd[PHOTOMETRIC_INTERPRETATION] = 0
+        if im.mode == "1":
+            rawmode = "1;I"
+        else:
+            inverted = im.point(lambda v: 255 - v)
+            inverted.encoderinfo = im.encoderinfo
+            inverted.encoderconfig = im.encoderconfig
+            im = inverted
+    else:
+        ifd[PHOTOMETRIC_INTERPRETATION] = photo
 
     if im.mode in ["P", "PA"]:
         lut = im.im.getpalette("RGB", "RGB;L")
```

### A.3 C2：只改标签（可选）

```diff
diff --git a/src/PIL/TiffImagePlugin.py b/src/PIL/TiffImagePlugin.py
--- a/src/PIL/TiffImagePlugin.py
+++ b/src/PIL/TiffImagePlugin.py
@@ -1568,7 +1568,8 @@ def _save(im, fp, filename):
     if format != 1:
         ifd[SAMPLEFORMAT] = format
 
-    ifd[PHOTOMETRIC_INTERPRETATION] = photo
+    if not (im.mode in ("1", "L") and ifd.get(PHOTOMETRIC_INTERPRETATION) == 0):
+        ifd[PHOTOMETRIC_INTERPRETATION] = photo
 
     if im.mode in ["P", "PA"]:
         lut = im.im.getpalette("RGB", "RGB;L")
```

### A.4 C3：gold 去掉 `encoderconfig` 提升（与 gold 只差 `encoderconfig = im.encoderconfig` 一行，以及 libtiff 分支里仍用 `im.encoderconfig`）

```diff
diff --git a/src/PIL/TiffImagePlugin.py b/src/PIL/TiffImagePlugin.py
--- a/src/PIL/TiffImagePlugin.py
+++ b/src/PIL/TiffImagePlugin.py
@@ -48,7 +48,7 @@ from collections.abc import MutableMapping
 from fractions import Fraction
 from numbers import Number, Rational
 
-from . import Image, ImageFile, ImagePalette, TiffTags
+from . import Image, ImageFile, ImageOps, ImagePalette, TiffTags
 from ._binary import o8
 from .TiffTags import TYPES
 
@@ -1487,7 +1487,8 @@ def _save(im, fp, filename):
 
     ifd = ImageFileDirectory_v2(prefix=prefix)
 
-    compression = im.encoderinfo.get("compression", im.info.get("compression"))
+    encoderinfo = im.encoderinfo
+    compression = encoderinfo.get("compression", im.info.get("compression"))
     if compression is None:
         compression = "raw"
     elif compression == "tiff_jpeg":
@@ -1505,7 +1506,7 @@ def _save(im, fp, filename):
     ifd[IMAGELENGTH] = im.size[1]
 
     # write any arbitrary tags passed in as an ImageFileDirectory
-    info = im.encoderinfo.get("tiffinfo", {})
+    info = encoderinfo.get("tiffinfo", {})
     logger.debug("Tiffinfo Keys: %s" % list(info))
     if isinstance(info, ImageFileDirectory_v1):
         info = info.to_v2()
@@ -1534,7 +1535,7 @@ def _save(im, fp, filename):
 
     # preserve ICC profile (should also work when saving other formats
     # which support profiles as TIFF) -- 2008-06-06 Florian Hoech
-    icc = im.encoderinfo.get("icc_profile", im.info.get("icc_profile"))
+    icc = encoderinfo.get("icc_profile", im.info.get("icc_profile"))
     if icc:
         ifd[ICCPROFILE] = icc
 
@@ -1550,10 +1551,10 @@ def _save(im, fp, filename):
         (ARTIST, "artist"),
         (COPYRIGHT, "copyright"),
     ]:
-        if name in im.encoderinfo:
-            ifd[key] = im.encoderinfo[name]
+        if name in encoderinfo:
+            ifd[key] = encoderinfo[name]
 
-    dpi = im.encoderinfo.get("dpi")
+    dpi = encoderinfo.get("dpi")
     if dpi:
         ifd[RESOLUTION_UNIT] = 2
         ifd[X_RESOLUTION] = dpi[0]
@@ -1568,7 +1569,18 @@ def _save(im, fp, filename):
     if format != 1:
         ifd[SAMPLEFORMAT] = format
 
-    ifd[PHOTOMETRIC_INTERPRETATION] = photo
+    if PHOTOMETRIC_INTERPRETATION not in ifd:
+        ifd[PHOTOMETRIC_INTERPRETATION] = photo
+    elif im.mode in ("1", "L") and ifd[PHOTOMETRIC_INTERPRETATION] == 0:
+        if im.mode == "1":
+            inverted_im = im.copy()
+            px = inverted_im.load()
+            for y in range(inverted_im.height):
+                for x in range(inverted_im.width):
+                    px[x, y] = 0 if px[x, y] == 255 else 255
+            im = inverted_im
+        else:
+            im = ImageOps.invert(im)
 
     if im.mode in ["P", "PA"]:
         lut = im.im.getpalette("RGB", "RGB;L")
@@ -1605,8 +1617,8 @@ def _save(im, fp, filename):
             ifd.setdefault(tag, value)
 
     if libtiff:
-        if "quality" in im.encoderinfo:
-            quality = im.encoderinfo["quality"]
+        if "quality" in encoderinfo:
+            quality = encoderinfo["quality"]
             if not isinstance(quality, int) or quality < 0 or quality > 100:
                 raise ValueError("Invalid quality setting")
             if compression != "jpeg":
@@ -1715,7 +1727,7 @@ def _save(im, fp, filename):
         )
 
     # -- helper for multi-page save --
-    if "_debug_multipage" in im.encoderinfo:
+    if "_debug_multipage" in encoderinfo:
         # just to access o32 and o16 (using correct byte order)
         im._debug_multipage = ifd
 
```

## 附录 B：R-c 草案

两份补丁都作用于隐藏测试目录（按 `r2e_tests/test_1.py` 的路径写）：B.1 直接打在当前的 `test_1.py` 上，B.2 打在 B.1 之上。已验证能依次应用，结果通过 `py_compile`。

### B.1 R-c1

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -456,6 +456,21 @@ class TestFileTiff:
             assert reloaded.tag_v2[262] == 0
             assert_image_equal(im, reloaded)
 
+    @pytest.mark.parametrize(
+        "mode, tiffinfo",
+        [("1", {}), ("L", {}), ("1", {262: 1}), ("L", {262: 1})],
+        ids=["1-default", "L-default", "1-explicit1", "L-explicit1"],
+    )
+    def test_photometric_blackiszero_kept(self, mode, tiffinfo, tmp_path):
+        # BlackIsZero stays the default, and an explicitly requested
+        # PhotometricInterpretation of 1 is written as requested.
+        filename = str(tmp_path / "temp.tif")
+        im = hopper(mode)
+        im.save(filename, tiffinfo=tiffinfo)
+        with Image.open(filename) as reloaded:
+            assert reloaded.tag_v2[262] == 1
+            assert_image_equal(im, reloaded)
+
     def test_seek(self):
         filename = "Tests/images/pil136.tiff"
         with Image.open(filename) as im:
```

### B.2 R-c2（只在 libtiff 可用、且 gold 预核通过时使用）

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -471,6 +471,19 @@ class TestFileTiff:
             assert reloaded.tag_v2[262] == 1
             assert_image_equal(im, reloaded)
 
+    @pytest.mark.parametrize(
+        "mode, compression", [("1", "group4"), ("L", "tiff_lzw")]
+    )
+    def test_photometric_compressed(self, mode, compression, tmp_path):
+        # The requested PhotometricInterpretation is also kept (and the
+        # image still reads back unchanged) when libtiff writes the file.
+        filename = str(tmp_path / "temp.tif")
+        im = hopper(mode)
+        im.save(filename, tiffinfo={262: 0}, compression=compression)
+        with Image.open(filename) as reloaded:
+            assert reloaded.tag_v2[262] == 0
+            assert_image_equal(im, reloaded)
+
     def test_seek(self):
         filename = "Tests/images/pil136.tiff"
         with Image.open(filename) as im:
```

新增期望键全部为 PASSED：
- R-c1：`TestFileTiff.test_photometric_blackiszero_kept[1-default]`、`[L-default]`、`[1-explicit1]`、`[L-explicit1]`；
- R-c2：`TestFileTiff.test_photometric_compressed[1-group4]`、`[L-tiff_lzw]`。

## 附录 C：证据索引

| 证据 | 路径 | 要点 |
| --- | --- | --- |
| noop（R-f，09-23） | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` 第 38 行；log `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_0edb86ea.eval.log`（sha256 `4411a919…`） | 60/62；目标键失败于 `T1:456`，报 `assert 1 == 0`；死键报 `TypeError`；pytest 8.3.4；镜像 `sha256:b4030960…`；导入路径 `/testbed/src/PIL/__init__.py` |
| gold（R-f，09-23） | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl` 第 38 行；log `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-p_6fdf1e36.eval.log`（sha256 `2e91098d…`） | 62/62；`included_paths=["src/PIL/TiffImagePlugin.py"]`；以 `agent/54321` 身份应用 |
| 中央复跑 noop / gold（09-24） | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl`、`ledger_gold.jsonl` 第 38 行；log `…/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_ff5b0a6f.eval.log`、`…rer_6fe1c2f5.eval.log` | 与 09-23 那组相比，只有耗时和对象地址不同 |
| M3 gold 两次 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 11、59 行；`…/logs_r2e/pillow/2d01f7d02243/gold/a1/test_output.txt`、`a2/test_output.txt` | 来源镜像上 60 passed、2 failed（死键）、2 skipped；两次一致 |
| 镜像事实 | `runs/env_overnight_20260916/M3/facts/2d01f7d02243/facts/{pth,pkg_origin,pytest_version,pip_freeze,import_origins}.*` | 可编辑安装；pytest 8.3.4；没有 pip；没有 defusedxml |
| 跨题扫描 | `runs/r2e_static_prep_20260924/cross_task_gold_scan.json`、`cross_task_test_scan.json` | 本题 gold 在 4 道题中命中 21–23/24 行；`test_photometric` 也出现在这 4 道题中；`2b061b68`、`3ac9396e` 包含在本题 base 中 |
| 公开包核实 | `runs/r2e_static_prep_20260924/v3/public/pillow__{4bc64835…,3a61c9e9…,f9d3ee0f…,a682ceaf…}/worktree/src/PIL/TiffImagePlugin.py` 中的 `inverted_im` 循环，和 `Tests/test_file_tiff.py` 中的 `test_photometric` | 版本依次为 9.1.0.dev0、9.2.0.dev0、9.3.0.dev0、10.1.0.dev0；`4bc64835` 的题面正是"模式 `'1'` 调 `ImageOps.invert` 报 `OSError`"，也就是 gold 用逐像素循环绕开的那个限制 |
