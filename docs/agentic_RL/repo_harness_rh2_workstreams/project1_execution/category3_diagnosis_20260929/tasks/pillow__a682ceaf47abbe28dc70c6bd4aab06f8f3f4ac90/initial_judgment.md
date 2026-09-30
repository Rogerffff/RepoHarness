# 主审初判（读历史前封存，写完不再改）

2026-09-30 / Claude（第3类第二批主审子代理）。本文按 v1 §7.1 第 3 步，在读 R2E 线看板、旧题卡与旧审查之前写成。此时已读：
- 本批公开读者稿 `public_read.md`、`commands.json`，负责人的 `evidence/devcheck/` 与 `evidence/public_environment_brief.md`；
- 原件：`s2_r2e/ingest/` 三个包中的本题记录（题面、`public_hints`、gold、期望映射 93 键、`run_tests.sh`）；
- 从镜像 `c3keep/pillow_a682:src`（RepoDigests 与冻结摘要 `sha256:c9ee334c…5733` 一致）取出的 `/r2e_tests`：`test_1.py`、`helper.py`、`__init__.py` 三个文件的 sha256 与评分包一致；
- `s2_r2e/revisions/material_revisions_v1–v11.json`：都没有本题条目，评分包 `material_revisions: []`。**当前生效的是原始材料 v0**；
- base 源码：`GifImagePlugin.py` 的写入路径、`Image.convert`、`ImagePalette.getcolor`，以及文档 `image-file-formats.rst` 的 GIF 部分。

## 1．原件要点

- **题面**：`info["transparency"]` 为元组时保存 GIF 抛 `TypeError`；期望“saved without using transparency, and no exception should be raised”。示例为 256×1 的 RGB 红色渐变、元组 `(255, 255, 255)`。
- **gold**：只改 `_write_local_header` 一处，删掉回退读取 `im.info["transparency"]` 的分支，只读 `im.encoderinfo["transparency"]`。单帧路径中，`encoderinfo` 由归一化后图像的 `info` 用 `setdefault` 补全，所以 `convert` 删掉的透明度不会再从原图读回。
- **隐藏测试**：`test_1.py` 与公开 `Tests/test_file_gif.py` 只差一个新函数 `test_removed_transparency`，内容就是题面示例：
  - 同一张图、同一元组；
  - `with pytest.warns(UserWarning): im.save(out)`；
  - 重新打开后断言 `"transparency" not in reloaded.info`。

  其余 92 个键都是公开测试原样，包括 `test_rgb_transparency`（1×1 图，元组能分配时保留透明度）、`test_transparent_optimize` 等。两个 netpbm 测试会跳过，不在期望里。
- **期望映射**：93 键，全部为 PASSED。

## 2．初判（v1 §4）

**核心要求**：元组透明色无法放进量化后的调色板时，保存 GIF 不抛异常，文件不带透明度。按题面的一般表述，这适用于任意这类图与元组，不限于示例。题面没说但公开材料能推出、需要保持的行为：元组能分配时仍保留透明度（公开测试 `test_rgb_transparency`），以及整数索引透明度的既有行为。

| 步 | 初判 |
| --- | --- |
| 1．核心要求有无直接断言 | 有：`test_removed_transparency` 覆盖“不抛异常”和“读回无透明度” |
| 2．是否只用了示例字面值 | **是**：图、像素、元组与题面示例逐字相同。按 D1 严格版判 **S1（T2c）**，走 R-c 补一个非示例实例，例如 hopper RGB 照片（多于 256 色）配另一个元组。要先实跑确认 base 在该实例上同样抛 `TypeError`。gold 的修法不依赖具体取值，预计能通过 |
| 3．退化探测 | 计划在 gold 的修改位置 `_write_local_header` 构造：(a) 只特判 `(255, 255, 255)`，预计原测试得 1，即 T2b；(b) 完全不写透明度（关掉检查），预计被 `test_rgb_transparency` 等公开测试拒绝，得 0 |
| 4．已有候选 | 尚未读历史，不知道有无真实候选；自造候选见下 |

**误拒风险（T1／P3），初步看法**：
- `pytest.warns(UserWarning)`：题面没提警告。但 base 在这条路径上本来就会由 `Image.convert` 发出 “Couldn't allocate palette entry for transparency”，公开测试 `test_image_convert.py::test_trns_RGB` 对同一种转换断言了这个警告；GIF 公开测试 `test_rgb_transparency` 的多帧部分，也在保存时丢弃 bytes 透明度的场景断言 `pytest.warns(UserWarning)`。所以“保留既有警告”有旧行为和公开测试作依据。只有主动压掉警告，或绕开 `convert` 自己实现分配的写法会被拒。**初判：不算 T1，登记即可**，要用一个“静默”候选实测确认。
- 用 `save(transparency=(r, g, b))` 关键字传元组：gold 仍抛 `TypeError`。文档把保存选项 `transparency` 定义为调色板索引，测试也不断言这种用法。**初判：超出题面，不要求，两种行为都接受。**

**gold 的旁支变化（G1，初判 T3）**：旧接口 `GifImagePlugin.getdata()` 直接调用 `_write_local_header`，gold 删掉 `info` 回退后，带整数透明度的 P／L 图不再写出透明度。这是未写入文档的旧接口，公开测试 `test_getdata` 不带透明度。准备用上游后续版本核对。

**可能放过的错误写法**（待实测）：
- 只特判示例字面值；
- 只在恰好 256 色时处理；
- 调色板一满就丢掉元组透明度，即使颜色本来就在调色板里（过度丢弃）；
- 改写调用者的 `im.info`，也就是就地改坏输入；
- 在 `_save` 外层吞掉异常：文件会残缺，预计读回时失败。

**合理的替代实现**（查误拒用）：在 `except` 里加 `TypeError`；只接受整数透明度；在归一化后的调色板中精确查找；移植上游后续写法。

**初步结论**：大概率是“问题和修法已明确，转第2类”。修法是 R-c `hidden_test_text_replace`：在 `test_removed_transparency` 末尾追加非示例实例，键集不变。候选矩阵跑完后再定。
