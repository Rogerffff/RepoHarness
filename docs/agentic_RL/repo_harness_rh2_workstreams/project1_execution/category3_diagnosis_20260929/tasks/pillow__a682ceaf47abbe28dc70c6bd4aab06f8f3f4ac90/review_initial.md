# pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90 复核初判（封存）

2026-09-30 / 独立复核者（Claude，新会话，不继承作者上下文）。本文写于读作者 `result.md`、`initial_judgment.md`、`public_read.md`、`evidence/` 与实验目录之前，写完不再修改；复核结论另写在同目录 `review.md`。

**需要事先说明的接触面**：派发说明里已经转述了作者的几条结论，我在写本文前就看到了：原版判 S1（T2c、`w_literal`、第 4 步）；R-c v1 有 (a)(b)(b′)(c) 四段新增检查；作者建议保留 `pytest.warns(UserWarning)`；`q_prestrip` 在 v1 为 0、在去掉 `pytest.warns` 的变体为 1；“不作要求”的四处。除此之外，作者材料一概未读。下面的判断只依据原件、base 源码、公开测试、文档和我自己的探针。

## 0. 读过的原件

| 材料 | 版本 | 要点 |
| --- | --- | --- |
| 题面 | `public_bundles_v0.jsonl`，`problem_statement_sha256` `e2b89213…` | 标题 “Saving GIF with Tuple Transparency Raises TypeError”。示例：256×1 RGB 图，像素 `(x,0,0)`，`info["transparency"]=(255,255,255)`，`im.save("temp.gif")`。期望：“The GIF should be saved without using transparency, and no exception should be raised.” |
| gold | `validation_bundles_v0.jsonl`，sha256 `c08adef1…` | 只改 `GifImagePlugin._write_local_header`：透明度只从 `im.encoderinfo["transparency"]` 取，删掉回退到 `im.info["transparency"]` 的分支 |
| 隐藏测试 | `/r2e_tests/test_1.py` `ff7a439c…`（与评分包登记一致） | 等于公开 `Tests/test_file_gif.py` 原样加一个 `test_removed_transparency`，没有其它差异（已 `diff`）。新测试逐字使用题面示例的图和颜色，要求 `pytest.warns(UserWarning)` 包住 `save`，读回后 `"transparency" not in reloaded.info` |
| 期望映射 | 93 键，全部 `PASSED` | 唯一的目标键是 `test_removed_transparency`；其余 92 键都是公开测试 |
| `run_tests.sh` | `8285765f…` | `PYTHONWARNINGS='ignore::UserWarning,…' python -W ignore -m pytest -rA r2e_tests`。`pytest.warns` 在上下文内部会重设过滤器，所以全局忽略不影响它（待实跑确认） |
| 镜像 | `c3keep/pillow_a682:src` = `namanjain12/pillow_final@sha256:c9ee334c…`，Image ID `5831b933…` | Pillow 10.1.0.dev0，Python 3.9.21，HEAD `7a1e2840`，工作树只多 `install.sh`、`run_tests.sh` 两个未跟踪文件 |

读过的 base 源码：`GifImagePlugin.py` 的 `_normalize_mode`、`_normalize_palette`、`_write_single_frame`、`_write_multiple_frames`、`_save`、`_write_local_header`、`_get_optimize`、`_get_background`、`_get_global_header`、`_write_frame_data`、`getheader`/`getdata`；`Image.py` 的 `convert`（第 863–1090 行）与 `save`。公开测试：`Tests/test_file_gif.py` 全部透明度相关用例、`Tests/test_image_convert.py::test_trns_RGB`。文档：`docs/handbook/image-file-formats.rst` 的 GIF 与 PNG 节。

## 1. 缺陷机制（base）

1. `_write_single_frame` 先调 `_normalize_mode(im)`。RGB 图走 `im.convert("P", palette=ADAPTIVE)`。
2. `convert` 把元组透明色 `trns` 交给 `new.palette.getcolor(trns, new)`。调色板已满 256 色且没有这个颜色时，`getcolor` 抛 `ValueError`，被 `except Exception` 接住：删掉 `new.info["transparency"]`，发出 `UserWarning("Couldn't allocate palette entry for transparency")`（`Image.py:1027-1034`）。
3. 回到 `_write_single_frame`，`im_out.info` 已经没有透明度，所以 `im.encoderinfo` 里也没有。
4. `_write_local_header(fp, im, …)` 拿到的是**调用者原来的 `im`**，于是回退读 `im.info["transparency"]`，得到元组，`int(元组)` 抛 `TypeError`；那里只接 `KeyError`、`ValueError`。

所以触发条件是：单帧写出路径；原图 `info["transparency"]` 是元组；归一化时这个颜色分不到调色板项（调色板满、且没有这个颜色）。多帧路径把规范化后的帧交给 `_write_local_header`，本来就不会回退到原元组；但多帧合并成一帧（例如两帧完全相同）或 `save_all=True` 只有一帧时，会退回单帧路径，同样崩溃。

## 2. 探针（base 对 gold，一次性断网容器，`probe0.py` `b967631d…`，输出 `probe0_out.txt` `f1e5a9de…`，都在会话 scratchpad）

| 情形 | base | gold |
| --- | --- | --- |
| S0 题面示例原样 | 先警告，再 `TypeError` | 警告，保存成功，无透明度 |
| S1 同一张图换透明色 `(0,255,0)`、`(1,2,3)` | 同 S0 | 同 S0 |
| S2 256 级灰 `(x,x,x)`，透明色 `(1,2,3)` | 同 S0 | 同 S0 |
| S3 `hopper` 照片（远多于 256 色），透明色取像素 `(0,0)` | 同 S0 | 同 S0 |
| S9 同 S3 先存 PNG 再读回（PNG 读入的 RGB 图 `info["transparency"]` 就是元组，这是现实中最常见的来源） | 同 S0 | 同 S0 |
| S14 300 色图，透明色 `(255,255,255)` | 同 S0 | 同 S0 |
| S4 示例图，透明色 `(255,0,0)`、`(7,0,0)` 已在满调色板里 | 保存成功，透明索引指向该颜色，无警告 | 同 base |
| S5 1×1 图，透明色 `(255,0,0)`，调色板有空位（公开 `test_rgb_transparency` 单帧部分） | 保留透明度 | 同 base |
| S6 示例 `save_all=True`（只有一帧） | `TypeError` | 成功，无透明度 |
| S7 示例两帧完全相同 | `TypeError`（合并后走单帧） | 成功 |
| S7b 两帧不同、`disposal=2` | 成功，无透明度，有警告 | 同 base |
| S8 示例加 `optimize=False` 或 `palette=` | `TypeError` | 成功 |
| S11 保存关键字 `transparency=(255,255,255)` | `TypeError` | **仍然 `TypeError`** |
| S12 RGB 图放整数透明度 5 | 成功（索引恰好指向 `(5,0,0)`） | 同 base |
| S13 旧接口 `getdata`，P 图 `info["transparency"]=3` | 写出透明索引 3 | **不写透明块**（gold 改变了旧接口行为） |
| S15 同一张图连续保存两次 | `TypeError` | 两次都成功，调用者 `im.info` 保持元组 |
| S16 RGBA 图放元组透明度；S17 P 图放元组透明度 | S16 成功；S17 `TypeError` | 同 base |

## 3. 公开要求（初判）

**核心要求**（题面标题与期望行为，按一般性理解）：
- K1：保存 GIF 时，图的 `info["transparency"]` 是元组也不能抛异常。
- K2：元组颜色无法放进 GIF 调色板时，写出的 GIF 不带透明度。

K1、K2 不限于示例的那张图和那个颜色：任何元组颜色、任何导致调色板放不下的图（正好 256 色、多于 256 色的照片、PNG 读回的 RGB 图）都属于同一要求的实例。

**相关的既有公开行为（修复不应破坏）**：
- P1：元组颜色能放进调色板时照常写出透明度。依据：公开 `test_rgb_transparency` 单帧部分；base 的 S4、S5。
- P2：P、L 图 `info["transparency"]` 里的整数索引，不传关键字时照常沿用。依据：文档 GIF Saving 节“if you do not pass them in, they will default to their info values … transparency: Transparency color index”；公开 `test_remapped_transparency`、版本号测试。
- P3：透明度无法使用时发出 `UserWarning`。这是 base 在这条路径上已有的行为，见 §5。

## 4. §4 判定（初判）

- **第 1 步（T2a）**：不命中。`test_removed_transparency` 直接断言“不抛异常”和“读回无透明度”。
- **第 2 步（T2c）**：**命中，S1**。唯一目标键逐字使用题面示例（同一张 256×1 `(x,0,0)` 图、同一个 `(255,255,255)`）；其余 92 键是 base 就能通过的公开测试，不碰这条路径。按 D1 严格版，走 R-c 补非示例实例。
- **第 3 步（T2b）**：预计命中。在 gold 的修改位置只特判 `(255,255,255)`（`w_literal`），原测试应得 1，而 S1 中的其它颜色仍会 `TypeError`。待实跑确认。
- **第 4 步**：计划自造下列候选，看原测试与作者修订版是否放过：
  - 规模阈值：只在图恰好 256 色时丢弃元组（`getcolors(256)` 非空才处理），多于 256 色（S3、S9、S14）仍崩溃；
  - 数据形态子集：只认 3 元组、只认 `(r,0,0)` 一类、只处理 RGB 不处理 PNG 读回图（后者其实同为 RGB，预计与主路径相同）；
  - 吞错：`_write_local_header` 多接一个 `TypeError`。我**预计它是合理实现**：它在主路径上与 gold 行为相同，还额外容忍 S11 的关键字元组；
  - 抑制症状：改调用者 `im.info`（删掉透明度），或在归一化前预先剥掉元组；
  - 顺序：依赖第一次保存留下的状态；
  - 合理但不同：例如把不可用的透明度在 `_write_single_frame` 里显式记为“无”，而不是删掉回退分支。

## 5. `pytest.warns(UserWarning)`：初判倾向保留，不属 R-b，也不属 P5 第二分支

理由：
1. **这是 base 在同一路径上已有的行为，不是新加的实现约束。** 警告由 `Image.convert` 发出，发生在 `TypeError` 之前；修复只要不去动它，自然保留。
2. **公开测试对同一机制直接断言了这个警告。** `Tests/test_image_convert.py::test_trns_RGB` 用 `hopper("RGB")` 加像素 `(0,0)` 的元组透明度转 `P`/ADAPTIVE，断言 `pytest.warns(UserWarning)` 且结果无透明度。GIF 保存走的正是这次转换。
3. **公开 GIF 测试对“透明度用不上”的兄弟情形也这样断言。** `test_rgb_transparency` 多帧部分：RGB 图放 `b""` 透明度，`pytest.warns(UserWarning)` 包住 `save`，读回无透明度。隐藏测试的新用例就是这个结构的元组版。
4. 只检查警告类别，不查文案，不涉及内部 helper。

反方理由（如实登记）：
- 题面期望只说“无透明度、不抛异常”，没有提警告；
- `convert` 的非 ADAPTIVE 分支（`Image.py:1080-1087`）和 `_get_background` 遇到“256 色已满”时都静默处理，注释写 “there is no need for transparency”。

我的判断是：题面没提警告，只说明它“不要求去掉警告”，不能当作“必须静默”的依据；静默的先例在别的分支和别的属性上，而 GIF 保存实际走的 ADAPTIVE 分支在 base 里会警告，并有公开测试断言。因此，测试采用的“有警告”读法有公开依据，“必须静默”这个读法没有直接依据，不满足 P5 第二分支“两种读法都有依据”。要去掉警告，解题者必须主动改变既有行为，要么在 GIF 路径绕开这次转换，要么压掉警告。

待核：作者的 `q_prestrip` 具体怎么写。如果它只是一种自然写法、顺带没有警告，而不是有意压制，我会再衡量它算不算“合理实现被误拒”。但只要警告有上述公开依据，拒绝它仍属“改变了有公开测试的既有行为”，不是误拒。

## 6. “不作要求”四处（初判）

- **`save()` 关键字传元组（S11）**：同意不作要求。文档把保存参数 `transparency` 写成 “Transparency color index”，gold 在这里也抛 `TypeError`。修订测试也**不应**要求它抛异常，因为多接 `TypeError` 的合理实现会静默忽略。
- **旧接口 `getdata`（S13）**：同意不作要求，但要注意 gold 改变了它的行为：base 从 `im.info` 取透明索引，gold 不取。它不在 handbook 文档里；公开 `test_getdata` 用的是 `info={"background":0}`，不涉及透明度。两种行为都不应被断言。
- **RGB 图放整数透明度（S12）**：同意不作要求。这不是文档里的合法状态；在我的探针上 base 与 gold 相同。
- **`save_all=True` 只有一帧（S6）**：初判**倾向不同意**完全不管。`save_all` 是文档化的保存选项，单帧图加 `save_all=True` 会退回同一个单帧写出函数，base 同样崩溃，属于同一核心要求的另一个实例。是否要补断言，取决于有没有候选只修了 `save_all=False` 的入口而放过这里。待核作者理由。

## 7. 对修订 R-c v1 四段检查的预期（只凭派发说明的一句话描述，未读草案）

- **(a) hopper 照片、透明色取像素 (0,0)**：依据充分。这正是公开 `test_trns_RGB` 的输入，base 在 GIF 保存时崩溃（S3）。它能挡住“只在恰好 256 色时处理”的阈值候选。
- **(b)(b′) 调色板已满，但透明色本来就在调色板里**：依据是 P1（`test_rgb_transparency` 与 base 行为）。它能挡住“调色板一满就丢弃元组透明度”的候选。要核对期望值是否对所有合理实现都成立，例如透明索引的具体数值会不会随 `optimize` 变化。
- **(c) 保存后调用者的 `im.info` 不被改**：依据较弱。没有公开测试直接断言“保存不改 `info`”；只能援引一般 API 语义，以及 `_write_multiple_frames` 里“a copy is required here since seek can still mutate the image”这类项目自身的做法。它的可见后果是真实的：同一张图接着存 PNG 会丢透明度，再存一次 GIF 不再警告。我倾向接受，但要看作者写的依据是否站得住。

## 8. 初步结论

- 原版 S1（T2c）成立；第 3 步预计也命中。
- 修订方向正确：补非示例实例，并保护相关既有行为。
- 需要实测的点：
  1. 修订版有没有误拒合理实现，例如多接 `TypeError`、显式记“无透明度”；
  2. 修订版是否仍放过阈值、子集、顺序类错误候选；
  3. `save_all` 单帧是否需要纳入；
  4. `pytest.warns` 在 `-W ignore` 与 `PYTHONWARNINGS` 下是否仍然生效；
  5. 评分身份（UID 54322）下结果是否一致。
