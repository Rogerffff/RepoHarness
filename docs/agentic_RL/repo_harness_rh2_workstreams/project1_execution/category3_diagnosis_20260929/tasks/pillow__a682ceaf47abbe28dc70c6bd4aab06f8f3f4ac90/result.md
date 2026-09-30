# R2E pillow__a682ceaf：第3类质量调查结果

2026-09-30 / Claude（第3类第二批主审子代理）。原分类为第3类“题目质量调查未完成”（未审题）。前序步骤：公开读者稿 [public_read.md](public_read.md)、[commands.json](commands.json)；负责人开发核对 [evidence/devcheck/](evidence/devcheck/)。读历史前的初判已封存在 [initial_judgment.md](initial_judgment.md)。本页的去向（R-c 后转第2类）与初判一致；初判列出的错误写法都已实测，另补了初判没列的 `w_notin_image`、`w_drop_big`、`w_convert_mutate`，修订也因此比初判多了 (b)、(b′)、(c) 三段。历史记录只有 09-24 环境审查与 09-23 正式评分，没有旧的质量结论可推翻。**本页所有分数都是私有模拟**，不是 R2E 正式评分。

> **当前状态（09-30 更新：独立复核完成，采用复核者 v2，转第2类）**
>
> - **独立复核**结论“部分同意，阻断 3 项”，全文见 [review.md](review.md)（初判封存稿 [review_initial.md](review_initial.md)）：
>   - 同意原版 S1（T2c＋T2b，另 6 个错误候选在主路径上）；作者 20 个候选在原测试、v1、v1 无 warns 三版上的 60 格逐格复现；v1 的四段检查都有公开依据、不过严（复核者另写的 3 个合理实现与上游 10.1.0、10.4.0、11.3.0 都通过）；gold 仍可作正对照；
>   - **B1 `w_mutate_kept`**：透明色能用时，把调用者 `im.info` 里的元组改成调色板索引；v1 的 (c) 只在丢弃透明度的两种情形后检查。后果是这张图接着存 PNG 会抛 `TypeError`；
>   - **B2 `w_nosaveall`**：只修了 `save_all=False` 的入口；`save_all=True` 只有一帧或两帧完全相同时仍抛 `TypeError`（作者原把 S02 登记为“没有已知候选利用”）；
>   - **B3 `w_order_cache`**：用模块缓存记住分配失败过的颜色，之后同色在调色板有空位的图上也被丢弃，且不再警告；
>   - **`pytest.warns` 保留**：不属于没有依据的实现约束，也不满足 P5 第二分支，不交用户；去掉它还会放过 `w_filter_leak`（留下全局警告过滤器，整个进程里 `Image.convert` 的这条公开警告都不再出现）。
> - **负责人决定**：采纳复核者的合并草案 **v2**（v1 加三处，修法都已私测）。私有模拟下 gold 与 7 个合理实现为 1；noop、作者 13 个与复核者 5 个错误候选、`q_prestrip` 为 0。
> - **停止条件**（review.md §7）：第2类在正式评分链上跑一轮，与复核 §3.2 表的 h4 列一致即完成，不再需要聚焦复核。R2E 在云端没有正式评分链，本页全部是私有模拟。
> - 交接见[交接清单](../../handover_to_category2_20260930.md)。

**结论：问题和修法已明确，转第2类（采用复核者 v2）。**

- **环境**：无问题。09-24 环境审查已合格；09-30 负责人照跑公开读者的 5 条命令，全部符合预期，最小公开验证约 3 秒。本题材料修订单 v1–v11 中没有本题条目，当前生效的是原始材料 v0。
- **测试问题（S1）**：唯一目标键 `test_removed_transparency` 的输入与题面示例逐字相同：256×1 红色渐变图，透明色 `(255, 255, 255)`。这是 §4 第 2 步的示例拟合（T2c）。在原测试下，下列 7 个错误候选也得 1：
  - `w_literal`：只特判示例颜色 `(255, 255, 255)`。这是第 3 步指定的退化探测，命中 T2b；
  - `w_count256`、`w_notin_image`：只修了一部分情形，多于 256 色的照片或“颜色在图中、但量化后分配不到”时仍抛 `TypeError`；
  - `w_drop_full`、`w_drop_big`：调色板满、或原图多于 256 色，就丢弃透明度，连本来能用的透明色也丢；
  - `w_mutate`、`w_convert_mutate`：删掉调用者 `im.info` 里的透明度。这张图接着另存 PNG 时，透明色就没了。
- **修法：R-c v1**。在原测试函数末尾追加 4 段检查，键集和期望映射（93 键）都不变，gold 仍作正对照。私有模拟下：
  - gold 与 4 个合理替代实现为 1；
  - noop 与 13 个错误候选为 0，其中原测试放过的 7 个全部改为 0；
  - root 与评分 UID 54322 结果相同；
  - 上游 Pillow 10.1.0、10.4.0、11.3.0 都通过修订后的测试函数，修复前的 10.0.0 不通过。
- **误拒核查（负责人原则 1）**：
  - 4 个与 gold 写法不同的合理实现在原测试和 v1 下都是 1；
  - 原测试的 `pytest.warns(UserWarning)` 有公开依据：base 在这条路径上本来就发出这个警告，公开测试 `test_trns_RGB`、`test_rgb_transparency` 也对同类情形断言警告。它只要求“有一条 UserWarning”，不限文案：自发另一句警告的 `alt_prestrip_warn` 为 1。只有主动去掉警告的 `q_prestrip` 为 0。
  - 用 `save(transparency=元组)` 关键字传元组时，测试不作要求，报错与静默忽略都能通过。

  **不需要用户决定。** `pytest.warns` 的取舍请复核重点看，§4 附了去掉它的对照变体及影响。
- **登记**：公开读者自述可能对上游修法有模糊的训练记忆，但它每条结论都对应到了公开文件与行号（public_read.md §5）。主审同样可能有上游记忆，所以本页涉及上游的判断都以 PyPI wheel 的代码、GitHub raw 上按 tag 取的测试文件和 CHANGES 为据。

## 1．公开要求与测试覆盖

题面：`info["transparency"]` 是元组时，保存 GIF 抛 `TypeError`；期望“saved without using transparency, and no exception should be raised”。

base 的根因可以从源码读出：
- `Image.convert` 在调色板满、元组分配不到索引时，只从转换后的副本里删掉透明度，并发出 “Couldn't allocate palette entry for transparency” 警告（`Image.py:1027-1034`）；
- 单帧写入随后把原图交给 `_write_local_header`，后者回退读取原图 `info` 里的元组，执行 `int(元组)`，抛出 `TypeError`（`GifImagePlugin.py:686-691`）。

gold 只改 `_write_local_header`：删去回退，只读 `encoderinfo`。这与上游 10.1.0 的该函数逐字相同，对应 CHANGES 10.1.0 “Do not use transparency when saving GIF if it has been removed when normalizing mode #7284”。

| 要求 | 性质与公开依据 | 原测试 | 修订 v1 |
| --- | --- | --- | --- |
| R1 元组分配不到调色板项时，保存不抛异常，GIF 不带透明度 | 明示（题面 Expected Behavior）。按题面的一般表述，适用于任何这类图与颜色 | 只有示例：256×1 红色渐变＋`(255, 255, 255)` | 加非示例实例 (a)：hopper 照片，多于 256 色，透明色取像素 (0, 0) 的颜色。这正是公开测试 `test_image_convert.py::test_trns_RGB`（172-192 行）断言“分配失败、警告并删除”的同一输入 |
| R2 元组能用时仍保留透明度，不能一律丢弃 | 可推知：公开测试 `test_rgb_transparency`（1×1 图）；`convert` 先查调色板里已有的颜色（`Image.py:1029`，`ImagePalette.getcolor`） | 只有 1×1 图 | 加 (b)、(b′) 两例“调色板已满、但透明色本来就在调色板里”：(b) 256 色红色渐变＋`(255, 0, 0)`；(b′) hopper 照片加一条纯色 `(0, 255, 0)` 背景，并以该色为透明色。断言透明索引等于该颜色像素的索引，写法沿用公开 `test_transparent_optimize` |
| R3 保存不改被保存的图 | 可推知：PNG 文档把 RGB 图 `info["transparency"]` 定义为该图的透明色（`image-file-formats.rst:666-673`），PNG 保存时会用它；GIF 文档只说保存选项“默认取 `info` 值”（244-247），即只读不写；base 与上游都不改。同仓先例：修订 r2e-mr-063（pillow 2d01）已加“saving does not modify the image that is saved” | 无 | 加 (c)：示例和 (a) 保存后，断言调用者 `im.info["transparency"]` 不变 |
| R4 丢弃透明度时的既有警告 | 旧行为（base 在该路径发出）；公开测试 `test_trns_RGB` 对 `convert` 断言；GIF 公开测试 `test_rgb_transparency` 的多帧部分，对保存时丢弃 bytes 透明度断言 `pytest.warns(UserWarning)` | `pytest.warns(UserWarning)` | 保留，不新增 |
| R5 整数索引透明度等既有行为 | 公开测试 | 其余 92 个回归键 | 不变 |
| 不作要求 | 用 `save()` 关键字传元组；旧接口 `getdata()`；RGB 图放整数透明度；RGBA 图带元组 | — | 不断言，理由见 §3.3 |

## 2．私有实测

### 2.1 条件

- 镜像：`namanjain12/pillow_final@sha256:c9ee334c…5733`，与冻结摘要一致，本机标签 `c3keep/pillow_a682:src`；root、`--network none`、一次性容器。驱动为 `semantic_control.py`，每个候选一个新容器。
- 评分材料都从镜像取出，并与评分包核对：
  - `/r2e_tests/test_1.py` sha256 `ff7a439c…`；
  - `helper.py` `2454534c…`；
  - `run_tests.sh` `8285765f…`；
  - 期望映射 `a465b6c9…`，93 键，全部 PASSED。
- **私有模拟评分**：把（修订后的）隐藏测试放进 `/testbed/r2e_tests`，运行评分包的 `run_tests.sh`，再用 `grade_r2e.py` 逐键对照期望映射。`grade_r2e.py` 使用 RH2 移植的上游 `parse_log_pytest`＋`prime_calculate_reward`。
  - 另按 RH2 生产口径核对：要求键集相等且逐键相等，即 `scoring.expected_map_matches`。4 次运行共 106 格，两种口径全部一致（`summarize_grades.py` 的输出）；
  - 各 `rc.json` 只是管道末端命令的退出码，得分以 `grades.jsonl` 为准。
- **评分 UID**：v1 另以 UID 54322 跑一遍。做法是在一次性容器里放开 `/root` 的遍历权限，再用 `setpriv` 降权；这是私有近似，没有套正式 profile。
- **可信度对照**：原材料上 noop 为 0，只错目标键；gold 为 1。这与 09-23 R2E 正式评分一致（noop 92/93、gold 93/93，见 `r2e_env_repair_20260924/tasks/<本题>/screening_record.json` R02、R08）。
- 候选补丁由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/make_candidates.py) 按精确文本替换生成，完整 sha256 见同目录 `candidates_and_materials_sha256.txt`。

### 2.2 候选与得分

逐键结果见 `evidence/revised_v1/grades.jsonl` 与 `evidence/revised_v1_extra/grades.jsonl`（后者是补充的 3 个候选）。括号内是失败的键；“v1 无 warns”是 §4 的对照变体。

| 候选 | 类别 | 做法 | sha256 | 原测试 | **v1** | v1 无 warns | v1 UID 54322 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base（noop） | — | — | — | 0 | **0** | 0 | 0 |
| gold | 参考修复 | `_write_local_header` 只读 `encoderinfo` | `c08adef1` | 1 | **1** | 1 | 1 |
| `alt_typeerror` | 合理替代 | `_write_local_header` 多捕获 `TypeError`，保留 `info` 回退 | `b260a6a6` | 1 | **1** | 1 | 1 |
| `alt_frame` | 合理替代 | `_write_single_frame`：归一化丢掉透明度时，用去掉该键的副本写局部图像头 | `35a249a2` | 1 | **1** | 1 | 1 |
| `alt_integral` | 合理替代 | 只接受 `numbers.Integral` 索引，其它类型视为无透明度 | `0b351960` | 1 | **1** | 1 | 1 |
| `alt_prestrip_warn` | 合理替代 | `_normalize_mode` 里自己用 `getcolor` 分配，分配不到时自发一条措辞不同的 UserWarning | `48f04053` | 1 | **1** | 1 | 1 |
| `q_prestrip` | 查误拒 | 同上，但不发警告 | `6b9728fb` | 0（目标键） | **0**（目标键） | 1 | 0 |
| `deg_off` | 退化：关掉检查 | 局部图像头永不写透明度 | `b0e6069d` | 0（7 个回归键） | **0** | 0 | 0 |
| `w_literal` | **第 3 步退化探测**：硬编码示例 | `_write_local_header` 只特判 `(255, 255, 255)` | `25569789` | **1** | **0**（目标键） | 0 | 0 |
| `w_count256` | 阈值 | 原图恰好 256 色才丢弃元组 | `1be11b3a` | **1** | **0** | 0 | 0 |
| `w_notin_image` | 数据子集 | 只在颜色不出现在图中时丢弃 | `6bc34501` | **1** | **0** | 0 | 0 |
| `w_drop_full` | 过度丢弃 | 调色板 256 项都用到就丢弃 | `116388ae` | **1** | **0** | 0 | 0 |
| `w_drop_big` | 过度丢弃（按规模） | 原图多于 256 色就丢弃 | `4d13339d` | **1** | **0** | 0 | 0 |
| `w_mutate` | 改坏调用者的图 | `_write_single_frame` 删调用者 `im.info["transparency"]` | `37ca7ded` | **1** | **0** | 0 | 0 |
| `w_convert_mutate` | 改坏调用者的图 | `Image.convert` 分配失败时连源图 `self.info` 一起删 | `9ba1147b` | **1** | **0** | 0 | 0 |
| `w_silent` | 压掉警告 | gold 加上静默 `convert` 的全部警告 | `75d5018c` | 0（目标键、`rgb_transparency`） | **0** | 0（`rgb_transparency`） | 0 |
| `w_swallow_save` | 吞掉错误 | `_save` 外层吞 `TypeError` | `a3f0c037` | 0 | **0** | 0 | 0 |
| `w_keep_trns` | 与题面相反 | 分配不到时改量化为 255 色，保留透明度 | `4e05bd71` | 0 | **0** | 0 | 0 |
| `w_nearest` | 与题面相反 | 改用最接近的调色板颜色作透明色 | `3ba559cf` | 0 | **0** | 0 | 0 |
| `w_imout` | 实现错误 | 把已重排调色板的图交给 `_write_local_header` | `c296cac7` | 0（`transparent_optimize`） | **0** | 0 | 0 |

v1 下各错误候选失败的位置（v1 行号，见 `evidence/revised_v1*/<候选>/h1_rev1.out`）：
- `w_literal`、`w_count256`、`w_notin_image`：1110 行 (a) 的保存抛 `TypeError`；
- `w_drop_full`：1124 行 (b)，读回没有透明度，报 `KeyError`；
- `w_drop_big`：1133 行 (b′)，同样是 `KeyError`；
- `w_mutate`、`w_convert_mutate`：1104 行 (c)，调用者 `im.info` 已没有该键；
- 其余在原测试已有的断言处失败：`q_prestrip` 在 1098 行报 “DID NOT WARN”；`w_keep_trns`、`w_nearest` 在 1101 行，读回仍带透明度；`w_swallow_save` 在 1100 行，读回报 `UnidentifiedImageError`。

公开测试 `Tests/test_file_gif.py`＋`Tests/test_image_convert.py`：base、gold 和全部合理实现都是 119 passed / 2 skipped（跳过的是缺 Netpbm 的两项）。有公开测试失败的只有 3 个候选：
- `deg_off`：7 项失败；
- `w_silent`：`test_rgb_transparency` 失败；
- `w_imout`：`test_transparent_optimize` 失败。

原测试放过的 7 个错误候选，公开测试全部通过。

### 2.3 行为矩阵（摘录）

脚本为 `probe_matrix_v2.py`，`v3` 另加 RGBA 场景；全表见 `evidence/revised_v1*/<候选>/probe.out`，可用 `tabulate_probe.py` 汇总。记法：`TypeError` 表示保存抛异常；`无` 表示读回没有透明度；数字是读回的透明索引。

| 场景 | base | gold 与 4 个合理实现 | 与 gold 不同的候选 |
| --- | --- | --- | --- |
| S01 题面示例 | `TypeError` | 无，1 条警告，像素与原图完全相同 | `w_keep_trns` 255；`w_nearest` 0；`w_swallow_save` 读回失败；`q_prestrip`、`w_silent` 没有警告 |
| S03 hopper＋像素 (0,0) 颜色（v1 的 (a)） | `TypeError` | 无 | `w_literal`、`w_count256`、`w_notin_image` 仍 `TypeError` |
| S04／S18 hopper（或加纯色条）＋不在图中的颜色 | `TypeError` | 无 | `w_literal`、`w_count256` 仍 `TypeError` |
| S05 另一张恰好 256 色的图＋不在图中的颜色 | `TypeError` | 无 | `w_literal` 仍 `TypeError` |
| S06 示例图＋`(255, 0, 0)`（v1 的 (b)） | 0，指向该颜色 | 同 base | `w_drop_full`、`deg_off` 为无 |
| S17 照片加纯色条，透明色为纯色（v1 的 (b′)） | 90，正好 4096 个像素透明，即纯色条 | 同 base | `w_drop_full`、`w_drop_big`、`deg_off` 为无 |
| S07／S08／S11 元组可分配（1×1、255 色、真实 tRNS PNG） | 保留 | 保留 | `deg_off` 为无 |
| S12 同一张图先存 GIF、再存 PNG | GIF 抛错；PNG 保留 `(255, 255, 255)` | PNG 保留 | `w_mutate`、`w_convert_mutate`：PNG 丢失透明色 |
| S02 `save_all=True` 只有一帧；S10 两帧；S16 写入 BytesIO | S02、S16 抛错；S10 正常 | 均正常 | 所有候选在 S02 与 S01 结果相同 |
| S09 用 `save()` 关键字传元组 | `TypeError` | gold、`alt_frame`、`alt_prestrip_warn` 抛 `TypeError`；`alt_typeerror`、`alt_integral` 为无 | 不作要求（§3.3） |
| S13 旧接口 `getdata`，P 图 `info` 里有整数透明度 | 写出透明标志 | gold、`alt_prestrip_warn` 不写；`alt_typeerror`、`alt_frame`、`alt_integral` 写 | 不作要求（§3.3） |
| S14 RGB 图放整数 0（非标准），且分配失败 | 写出透明索引 0 | gold、`alt_frame`、`alt_prestrip_warn` 为无；`alt_typeerror`、`alt_integral` 同 base | 不作要求（§3.3） |
| S19／S20 RGBA 图带元组 | 不报错：`_normalize_mode` 用调色板里 alpha 为 0 的项覆盖了元组。S19 中这一项是没有像素使用的 `(0, 0, 0, 0)`（`evidence/rgba_check/`） | 同 base | — |

### 2.4 上游对照（只作佐证）

做法：从 PyPI 下载 cp39 wheel，sha256 与 PyPI 登记值一致，记录在 `evidence/upstream_check/wheels_sha256.txt`；解压后在同一镜像里用 `PYTHONPATH` 加载，并确认 `PIL.__file__` 指向解压目录。结果：
- 10.0.0 与 base 相同，在 v1 的 `test_removed_transparency` 上失败（`TypeError`）；
- 10.1.0、10.4.0、11.3.0 都通过 v1 的该函数，也通过 `test_rgb_transparency`、`test_transparent_optimize`。它们的行为矩阵与 gold 相同，包括 S09 仍抛 `TypeError`、S13 不写透明标志。
- 上游 11.3.0 的同名测试把警告断言收紧为 `pytest.warns(UserWarning, match="Couldn't allocate palette entry for transparency")`（取自 GitHub raw 上 11.3.0 tag 的 `Tests/test_file_gif.py`）。可见上游把这条警告当作行为的一部分。这只作佐证，不当公开依据。

## 3．判定（v1 §4）

### 3.1 五步

| 步 | 结果 | 证据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有 | `test_removed_transparency`：保存不抛异常、读回无透明度 |
| 2 是否只用示例字面值 | **是，S1（T2c）**：图、像素、元组与题面示例逐字相同 | 隐藏测试 1089-1101 行对照题面 |
| 3 退化探测（指定 `w_literal`） | **得 1，S1（T2b）** | 它在 gold 的修改位置 `_write_local_header` 里只特判示例颜色，是“与输入无关的固定结果”。违反 R1：S03–S05、S18 的其它元组仍抛 `TypeError`。另两个退化方向为 0：`deg_off`（关掉检查）被 7 个回归键挡住；`w_swallow_save`（吞错）写出残缺文件，读回失败 |
| 4 已有候选 | **S1** | 本题没有真实模型候选，下列都是主审构造的候选：`w_count256`、`w_notin_image` 在同一核心要求的其它实例上仍崩溃；`w_drop_full`、`w_drop_big` 破坏 R2；`w_mutate`、`w_convert_mutate` 破坏 R3。理由见 3.2 |
| 5 | — | 前面已命中 S1 |

### 3.2 为什么第 4 步的候选不算“边缘”

- **`w_drop_full`、`w_drop_big` 丢掉本来能用的透明色**：RGB 图带 tRNS 时，透明色通常就是图里的一大片背景色，S17 正是这种情况。这时透明色通常能精确落进调色板（S17 中正是如此），base 与 gold 都保留透明度。过度丢弃会让这类最常见的图存成 GIF 后失去透明背景。公开测试 `test_rgb_transparency` 只测了 1×1 图，挡不住它们。
- **`w_mutate`、`w_convert_mutate` 改写调用者的图**：一次 GIF 保存之后，这张图的透明色就没了。接着另存 PNG（文档里 RGB 图透明色的标准用法），PNG 也丢了 tRNS（S12c）。题面示例本身就是在内存里给图设 `info["transparency"]`，这种副作用正落在核心场景上。
- **`w_count256`、`w_notin_image` 仍会崩溃**：多于 256 色的照片带 tRNS 是这个报错的现实来源之一；hopper＋像素颜色也是公开测试 `test_trns_RGB` 的原输入。

### 3.3 测试不作要求、也不补断言的几处（负责人原则 2：逐条写明为什么不违反公开要求）

- **关键字传元组（S09，公开读者 R7）**：文档把 GIF 保存选项 `transparency` 定义为 “Transparency color index”（`image-file-formats.rst:246-247`）。题面说的是图像 `info` 里的元组，示例写的是 `im.info["transparency"] = …`。关键字传元组属于文档外用法，报错与静默忽略都不违反公开要求。gold 与上游 10.1.0–11.3.0 都仍抛 `TypeError`。原测试与 v1 都不断言，两类实现都能通过。
- **旧接口 `getdata`（S13，gold 的旁支变化）**：`getdata` 标为 “Legacy Method”，手册没有写它。它的 docstring 说 `**params` 就是 encoder info，透明度应作参数传入；以参数传入 `getdata(im, transparency=1)` 时，base、gold、`alt_typeerror`、`alt_frame` 都写出透明度（`evidence/getdata_check/`）。GIF 文档里“未传入时取 `info` 值”指的是 `save()`。上游从 10.1.0 到 11.3.0 都保持 gold 的行为。所以这不是 gold 的缺陷，也不要求替代实现跟随，不补断言。
- **RGB 图放整数透明度且分配失败（S14）**：base 与 `alt_typeerror`、`alt_integral` 会把原图的整数当作透明索引写出，于是另一种颜色变透明；gold、`alt_frame` 与上游不写。但文档里 RGB 图的透明度是颜色（`image-file-formats.rst:670-671`），题面只谈元组。Pillow 自己产生这种组合的途径只有把 “1”“I” 模式直接转成 RGB（整数没有被换算成颜色），属于非标准表示。这是 base 在非标准输入上的旧问题，与本题无关。把它写进测试，等于把 gold 的附带行为升格为要求（负责人原则 1），所以不补。`alt_typeerror`、`alt_integral` 在题面范围内的全部场景都正确，属于合理实现。
- **`save_all=True` 只有一帧（S02）**：与 S01 走同一个单帧写入函数，全部候选在 S02 与 S01 的结果相同，没有已知候选利用这一点。可选加固：在示例部分再存一次 `im.save(out, save_all=True)`。本页不建议加。
- **警告（R4）**：见 §4“对照变体”。

### 3.4 其它登记

- **题面**：示例只定义了函数，没有调用；补上调用即可复现（devcheck `repro_issue_example` 在 690 行得到 `TypeError`）。Description 里 “expects … a string, bytes-like object, or number” 是转述 `int()` 的报错，不是接口约定；Expected Behavior 写得明确，不会把人引到“把元组转成数字”。不需要 R-f。
- **X1**：本题 base（2023-07）是同仓其余 6 道 R2E pillow 题的后代。它们的 base 与修复提交都是本题 HEAD 的祖先，所以本题工作树含有那 6 题的修复；反过来，本题修复不在任何一题的工作树里。登记，训练时控制同仓重复采样。
- **E3，已由 A 线覆盖**：来源镜像的 `.git` 里有修复提交 `a682ceaf` 的对象（不可达）。M3 的 git 清理探针在清理后已取不到该对象（`env_overnight_20260916/M3/M3_git_scrub_probe.json`）；09-24 环境审查 R17 记派生镜像 `fix_present=no`。本页的私有对照用的是来源镜像，只由 root 在断网容器里运行，不涉及解题。
- **E／D 类**：无。修改点是纯 Python，没有网络或装包需求（解题环境没有 pip）。公开测试两个文件合计约 2 秒。

## 4．修法：R-c v1（交第2类）

状态：草案已写成文件，并做了私有模拟验证；未入库，未经正式评分，未经复核。

**修订文件**：[`hidden_test_1_revised_v1.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/hidden_test_1_revised_v1.py)
- sha256：父版本 `ff7a439c…` → `7f247bf4…`；
- 改动：只在 `test_removed_transparency` 末尾追加，原有 13 行一字未改；键名不变，期望映射不用改；
- 编辑块（R2E `hidden_test_text_replace` 格式）：[`revision_draft_v1.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/revision_draft_v1.json)。已核对：把编辑块应用到原文件，得到的正是 v1 文件。

```python
    # Saving does not change the image that was saved
    assert im.info["transparency"] == (255, 255, 255)

    # An RGB image with more than 256 colours, where the transparent colour
    # cannot be allocated in the palette either
    im = hopper("RGB")
    im.info["transparency"] = im.getpixel((0, 0))
    im.save(out)

    with Image.open(out) as reloaded:
        assert "transparency" not in reloaded.info
    assert im.info["transparency"] == im.getpixel((0, 0))

    # A transparent colour that is already in the full palette is still used
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0))
    im.info["transparency"] = (255, 0, 0)
    im.save(out)

    with Image.open(out) as reloaded:
        assert reloaded.info["transparency"] == reloaded.getpixel((255, 0))

    # Also when the image has more than 256 colours
    im = hopper("RGB")
    im.paste((0, 255, 0), (0, 0, 128, 32))
    im.info["transparency"] = (0, 255, 0)
    im.save(out)

    with Image.open(out) as reloaded:
        assert reloaded.info["transparency"] == reloaded.getpixel((0, 0))
```

| 段 | 针对的窄问题 | 挡住的候选 | 为什么不误拒 |
| --- | --- | --- | --- |
| (a) hopper＋像素颜色 | T2c／T2b：示例拟合 | `w_literal`、`w_count256`、`w_notin_image` | 只要求 R1；输入取自公开测试 `test_trns_RGB`。它的颜色在图中、但量化后分配不到，所以“只看颜色在不在图里”的写法也挡得住 |
| (b)、(b′) 颜色已在满调色板中 | 第 4 步：过度丢弃 | `w_drop_full`、`w_drop_big` | 这是 base 已正确处理的情形，断言沿用公开 `test_transparent_optimize` 的写法；5 个合理实现与上游 10.1.0–11.3.0 都通过 |
| (c) 调用者 `im.info` 不变 | 第 4 步：改坏调用者的图 | `w_mutate`、`w_convert_mutate` | 只要求“不改”，不限定实现方式；先例 r2e-mr-063 |

草案演变：首稿只有 (a)、(b)、(c)。首次评分前，`probe_v2_check` 发现 `w_drop_big` 能过 (b)，于是补入 (b′)，并在 (a) 后也检查 `im.info`。没有更早的已评分版本。

**验收（v1 §5 R-c）**，全部为私有模拟：

| 验收项 | 结果 |
| --- | --- |
| 正对照 gold 为 1、noop 为 0 | 满足，root 与 UID 54322 都是如此 |
| 要纠正的误判已纠正 | 原测试得 1 的 7 个错误候选全部改为 0 |
| 已知相关错误候选仍为 0 | 另外 6 个错误候选仍为 0 |
| 合理替代实现不被误拒 | 4 个为 1 |
| 公开核心要求有直接断言 | 原测试的示例部分，加上 (a) |
| 键集严格相等 | 93 键，无 unexpected |
| 版本、父版本、理由与触发反例已保存 | `revision_draft_v1.json`，触发反例即上表的 7 个候选 |
| Codex 复核 | **未做**，交第2类 |

**对照变体（不推荐，供复核判断）**：[`hidden_test_1_revised_v1_nowarn.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/hidden_test_1_revised_v1_nowarn.py)（`7ca12079…`）与 v1 只差一处：示例部分去掉 `pytest.warns`。在 20 个候选中，它只让 `q_prestrip` 从 0 变为 1；`w_silent` 仍被公开回归键 `test_rgb_transparency` 挡住。我建议保留 `pytest.warns`，理由有三：
- 这条警告是 base 在该路径已有的公开行为，公开测试对同类情形都断言了它；
- 它只要求有一条 UserWarning，不限文案，`alt_prestrip_warn` 可以通过；
- `q_prestrip` 不只在崩溃路径上去掉了警告：base 本来能正常保存的多帧路径 S10，它也把警告去掉了，这改变了既有行为。

如果复核认为这属于没有依据的要求（T1），改用此变体即可，不影响其它结论。

### 4.x v2：独立复核后的采用版本

**草案**（复核者，`rh2/experiments/category3_cloud_20260929/pillow_a682/review/materials/`）：`hidden_test_1_review_v2.py`（`3573f459…`）、编辑块 `revision_draft_review_v2.json`（`21581578…`，已用 RH2 的 `_apply_edits` 重放、字段合规）；对照变体 `hidden_test_1_review_v2_nowarn.py`（`6fd35e4b…`）。键集与期望映射（93 键）不变。相对 v1 加三处：

| 新增检查 | 依据 | 拦下 |
| --- | --- | --- |
| (b) 之后 `assert im.info["transparency"] == (255, 0, 0)` | 保存不改被保存的图（R3，同 (c) 的依据），透明色能用时同样适用 | B1 `w_mutate_kept` |
| 示例部分另存一次 `im.save(out, save_all=True)`，断言读回无透明度 | 题面的一般表述：保存不抛异常，与 `save_all` 选项无关 | B2 `w_nosaveall` |
| 示例之后加一张 1×1 图，透明色同为 `(255,255,255)`，断言保留透明度 | R2：元组能用时仍保留透明度；与之前保存过什么图无关 | B3 `w_order_cache` |

**私有模拟（复核者，全部 164 格，上游口径与 RH2 生产口径逐格一致，每格都解析到 93 键；关键候选另以 UID 54322 复跑）**：

| 候选 | 原测试 | v1 | **v2** |
| --- | --- | --- | --- |
| gold、`alt_typeerror`、`alt_frame`、`alt_integral`、`alt_prestrip_warn` | 1 | 1 | **1** |
| `r_retry`、`r_none_marker`、`r_kwtuple`（复核者的合理实现） | 1 | 1 | **1** |
| noop | 0 | 0 | 0 |
| 作者的 7 个触发反例 | 1 | 0 | 0 |
| 作者其余 6 个错误候选 | 0 | 0 | 0 |
| `w_getcolors256`（复核者；`getcolors()` 默认只数 256 色） | 1 | 0 | 0 |
| `w_mutate_kept`、`w_nosaveall`、`w_order_cache`（B1–B3） | 1 | **1** | **0** |
| `w_filter_leak`（只靠 `pytest.warns` 拦下） | 0 | 0 | 0（无 warns 变体下为 1） |
| `q_prestrip`（只比 gold 少了警告） | 0 | 0 | 0（无 warns 变体下为 1） |

B1–B3 与 `w_filter_leak` 在全部公开测试上都通过，只能靠隐藏测试拦下。

## 5．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 v0 | 是 | 否：原版有已证的 S1 未修，7 个错误候选能得 1。按 09-30 Codex 复核后的统一口径，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不与原分数混用 | 否（S1 未处理） | 否 |
| R-c v2（复核草案） | 是 | 经 Codex 复核、入库和正式评分验收后重新评估 | | 修订后的题只能作“标明版本的自建题” |

## 6．未做与证据

**未做**：
- R2E 正式评分链与派生镜像没有在云端重建，本页分数都是私有模拟；
- 独立复核已完成（review.md）；Codex 复核未做；复核未查：正式评分链与派生镜像、UID 54321 的开发条件、上游 10.0.0 重跑、16 位 PNG 的 tRNS、其它平台上的量化结果（review.md §8）；
- 没有真实模型候选，全部候选由主审构造；
- 解题身份（UID 54321）的开发条件：沿用 09-24 环境审查的 agent 探针与 09-30 负责人 devcheck，本页未重做；
- 上游 PR #7284 页面未读（云端读不到 GitHub PR）；
- 其它 GIF 解码器未查。

**证据**（[evidence/](evidence/)，各子目录有 `evidence_manifest.json`）：
- `devcheck/`、`public_environment_brief.md`：负责人的开发核对，本页未改动；
- `semantic_v1/`：第一轮，14 个候选 × 原测试，`probe_matrix.py`；
- `probe_v2_check/`：纯色条场景的可行性检查（base、gold、`w_drop_full`、`w_drop_big`）；
- `revised_v1/`：17 个候选，4 组材料（原测试、v1、v1 无 warns、v1 UID 54322），外加公开测试与 `probe_matrix_v2.py`；
- `revised_v1_extra/`：补充的 3 个候选加 base、gold，同样 4 组材料，`probe_matrix_v3.py` 含 RGBA 场景；
- `upstream_check/`：上游 10.0.0、10.1.0、10.4.0、11.3.0，wheel 的 sha256 与 CHANGES 10.1.0 摘录；
- `getdata_check/`：旧接口 `getdata` 以 `info` 或参数给出透明度时的对照（base、gold、`alt_typeerror`、`alt_frame`）；
- `rgba_check/`：RGBA 图带元组时 `_normalize_mode` 的处理（base、gold）。

脚本、补丁与修订草案都在 [`rh2/experiments/category3_cloud_20260929/pillow_a682/`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow_a682/)。`runs/…/pillow_a682/public/`（公开包的工作树副本）与 `materials/`（从镜像取出的评分材料，已按 sha256 核对，内容与实验目录中的 `hidden_test_1_orig.py`、`run_tests.sh` 相同）没有归档。

## 7．交接清单（给第2类）

1. **落地版本**：R2E 材料修订一条，接在 `material_revisions_v11`（最后一条为 r2e-mr-063）之后，编号由第2类分配。
   - 类型：`hidden_test_text_replace`，目标 `test_1.py`；
   - 采用复核者 v2：编辑块 `review/materials/revision_draft_review_v2.json`（`21581578…`），修订后测试文件 `hidden_test_1_review_v2.py`（`3573f459…`）；也可以对作者 v1（`revision_draft_v1.json`，`ff7a439c…` → `7f247bf4…`）做逐字等价的三处改动；
   - 期望映射不变：`a465b6c9…`，93 键。
2. **补丁与哈希**：作者 19 个候选补丁与 gold 在实验目录（`candidates_and_materials_sha256.txt`、`make_candidates.py`，其中 `w_convert_mutate` 另需 base 的 `Image.py`）；复核者 8 个候选在 `review/cands/`（`make_review_candidates.py`）。
3. **正式评分时的预期分数**：与复核 §3.2 表的 h4 列一致即完成，不再需要聚焦复核。最少要跑：
   - 期望为 1：gold、`alt_typeerror`、`r_kwtuple`；
   - 期望为 0：noop、作者 7 个触发反例、`w_mutate_kept`、`w_nosaveall`、`w_order_cache`、`w_filter_leak`、`q_prestrip`。
4. **只登记、不再阻断**（review.md §7）：只在多于 256 色的图上改调用者 `info`（可选在 (b′) 后再加一行）；只在示例以外的路径去掉警告；关键字元组、`getdata`、RGB 整数透明度、RGBA 或 P 图带元组；GIF 版本号；其它解码器。新反例要阻断，必须落在复核 §7 列出的主路径上，并能指出违反哪条公开要求。
5. **`pytest.warns`**：保留（复核 §4）。代价是有意去掉警告的写法（`q_prestrip` 一类）得 0，建议在题卡的训练价值备注里写明。
6. **登记**：X1（本题工作树含同仓其余 6 道 R2E pillow 题的修复，复核已实核）；E3（来源镜像的 `.git` 里有修复提交对象，派生镜像已清理，属 A 线范围）。
7. **前置条件**：修订的 Codex 复核；在本地的 R2E 正式评分链上，用派生镜像加修订材料跑第 3 条；环境与题面都没有改动，不需要重做 actor 开发核对或公开读者验收。
