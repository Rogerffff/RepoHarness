# pillow__3a61c9e9 独立复核 · 第一步初判

2026-09-25 · 独立复核者（Claude，干净上下文，未参与主审）。本文写在读主审产物、公开读者产物和历史引用之前。所有"预期得分"如无特别说明都是**静态推断**，要由协调者用正式评分代码实跑确认。

## 0. 初判摘要

| 项 | 初判 | 证据级别 |
| --- | --- | --- |
| 题目 | `Image.remap_palette` 在调色板模式为 RGBA 时按 3 字节切片，输出 RGB 调色板，丢 alpha，且与原调色板字节不等 | 源码 + 执行 |
| 材料与初态 | 一致：各摘要彼此核对通过；noop 失败在 `test_1.py:614`，原因与题面一致；gold 71/71 | current 评分行 ×4 |
| 目标键 | 只有 `TestImage.test_remap_palette`；其余 70 键是同文件回归键 | current 评分行 |
| 误拒 | **未发现**。新增的精确断言与题面示例逐字相同；合理替代解 A1 预期仍得 1 | 静态推断 |
| 漏测（主要问题） | **测试偏宽**。新增断言只比 Python 侧 `ImagePalette.palette` 属性，RGBA 只测恒等映射，且在调用**之后**才读源图调色板。W1（只改 Python 侧对象）、W2（恒等映射短路）、W5（就地把源图调色板改成 RGB）预期都得 1 | 静态推断，待 CPU |
| 未评分回归 | 仓内唯一调用者是 GIF 保存（`GifImagePlugin._normalize_palette`），隐藏测试不存 GIF。R1（给了 `source_palette` 也按核心模式取 4 字节）会弄坏 GIF 颜色，预期仍得 1 | 静态推断，待 CPU |
| 非 PASSED 期望键 | 无（71 键全 PASSED），不存在"更完整修复翻转 FAILED 键被判 0"的风险 | 期望映射 |
| 题目关系 | 本题修复已出现在同仓 `f9d3ee0f`（逐字）和 `a682ceaf`（上游重构版；机械比对**漏报**）的公开初态中，这两题的公开 `Tests/test_image.py` 也已有本题新增断言 | 公开包实读 |
| 暂定处置 | 可作开发诊断候选，标"测试偏宽 + 同仓答案包含"；不宜只凭 reward=1 判为已修好 | — |
| 唯一优先下一步 | 正式评分代码实跑 **W1 与 A1**：W1 得 1 即坐实假阳性，A1 得 1 即坐实无误拒 | — |

## 1. 实际读取范围

- **角色与方法**：`roles/reviewer_r2e.md`（全文）；`roles/investigator_r2e.md`（Read 返回了 42 行全文，口径只采用"R2E 的评分口径""材料""第二批补充规则"三节，其余两节只是看到，未作依据）；`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`。
- **PUBLIC_DIR**：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`（结构与 `untracked_*`、`initial_diff` 字段）。`worktree/` 中读了：`conftest.py`、`Tests/conftest.py`、`setup.cfg` 的 pytest 段、`Tests/test_image.py` 与 `Tests/helper.py`（与隐藏版 diff）、`Tests/test_image_getpalette.py`、`Tests/test_image_putpalette.py` 的 RGBA 段、`Tests/test_file_gif.py` 的 RGBA 片段；源码读了 `src/PIL/Image.py`（`_new`、`load`、`getpalette`、`putpalette`、`putpixel`、`remap_palette`）、`src/PIL/ImagePalette.py`（类与 `raw`）、`src/PIL/GifImagePlugin.py`（`_normalize_mode`、`_normalize_palette`、`_save`、`_get_optimize`、`_get_palette_bytes`、`_get_background`、`_get_global_header`）、`src/_imaging.c`（`_getpalette`、`_getpalettemode`、`_putpalette`、`_putpalettealpha(s)`）、`src/libImaging/Palette.c`（`ImagingPaletteNew`）。
- **PRIVATE_DIR**：全部文件（`hidden_tests/{__init__,helper,test_1}.py`、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`=`[]`、`run_refs.json`）。
- **run_refs 原件**：4 个 current 账本行（均为第 39 行）和 4 份 `.eval.log`，摘要全部与 `run_refs.json` 一致；M3 独立 runner 的 2 份日志和账本第 13、61 行只作对照。
- **devcheck**：`orig/commands_with_preflight.json`、`orig/captures/*.out`（9 份全读）、`prelaunch.json`、`attempt.json`、`devcheck_stdout.json`、`post_run_facts_root.txt`（开头部分）、`bringup_artifacts/cc_version_observed.json`；`private_gold/private_control.json`。未读 `harness/trajectory.jsonl`、`stub/*`、`private_gold/stdout.log`。
- **跨题**：`cross_task_gold_scan.json`、`cross_task_test_scan.json` 的 pillow 行；同仓 7 题**公开包**的 `base_commit`、`src/PIL/Image.py` 中的 `remap_palette`（`f9d3ee0f`、`a682ceaf` 细读，其余 grep），以及 `Tests/test_image.py`（grep）。
- **暴露说明**：devcheck 命令清单里能看到公开读者建议的命令文本，但没读 `public_read.md` 本身。
- **未读**：OUTPUT_DIR 其它文件、任何 `history/`、`docs/.../r2e_env_repair_20260924/`、首批审查目录、Codex 复核目录、其它 `*review*` 目录、本批 README、`assignments.json`、`grader_candidates.md`、`runs/` 下的分析/汇总文件、其它题私有包。`runs/r2e_env_repair_20260924/_rerun2/` 下只打开了 `run_refs` 列出的两个账本和两份日志。

## 2. 目标键展开

隐藏 `test_1.py` 与 base `Tests/test_image.py` 只差 `test_remap_palette` 里新增的 8 行（`test_1.py:607–614`）。`helper.py` 与 base `Tests/helper.py` 逐字相同（diff 退出码 0）。

`TestImage.test_remap_palette`（`test_1.py:602–619`）包含三段：
1. 旧断言：打开 `Tests/images/hopper.gif`（RGB 调色板），做恒等重映射，`assert_image_equal` 比较 mode、size 和 `tobytes()`（`helper.py:87–98`；P 模式下只比像素索引，不比调色板）。
2. **新增断言**：`Image.new("P",(256,1))`，逐像素写入索引 0..255，`putpalette(list(range(256))*4, "RGBA")`，恒等重映射，然后 (a) `assert_image_equal(im, im_remapped)`，(b) `assert im.palette.palette == im_remapped.palette.palette`。
3. 旧断言：对 RGB 图调用 `remap_palette(None)` 应抛 `ValueError`。

**base 下的执行路径**（`Image.py`）：
- `putpalette`（1782–1814）先存原始 RGBA 数据，再调 `load()`（823–838）把调色板写入核心，此时 `palette.mode="RGBA"`，`palette.palette` 取自 `im.getpalette("RGBA","RGBA")`，共 1024 字节。
- `remap_palette` 在第 1873 行取 `self.im.getpalette("RGB")[:768]`（去掉了 alpha），第 1882 行按 3 字节切片，第 1919–1920 行以 RGB 写回，得到 768 字节。
- 所以 (a) 通过、(b) 失败。

**执行证据**：current noop 日志 `…_5e035000.eval.log` 失败在 `r2e_tests/test_1.py:614`，报 `AssertionError … At index 3 diff: b'\x03' != b'\x04'`。第 4 个字节在左边是 entry0 的 alpha，在右边是 entry1 的 R，正是题面说的"palette byte arrangement"错误。R-f 组的 noop 日志与之相同。gold 两份日志都是 `71 passed, 1 skipped`。

## 3. 需求—断言双向映射

| 公开要求 / 合理旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据或下一验证 |
| --- | --- | --- | --- | --- |
| RGBA 调色板、恒等映射后，调色板字节与原图相同 | 题面示例与 Expected Behavior | `test_1.py:614` | 覆盖（示例逐字进入测试） | noop 失败 / gold 通过（current） |
| 恒等映射不改变像素 | 题面"identical mapping"（隐含） | `test_1.py:613` | 覆盖 | base 下同样通过（日志中 613 行未失败） |
| 非恒等映射也能正确重排 RGBA 条目（4 字节步长） | 标题"Fails with RGBA Palettes"；描述"does not correctly handle RGBA palette modes" | 无 | **缺失** | devcheck pr3：base 得 `swap_mode: RGB`、`swap_render_equal: False`；私有 gold 对照得 RGBA `[50,60,70,80,10,20,30,40]`、`True`。W2 可利用 |
| 输出图的**核心**调色板保留 alpha（`getpalette(None)`、`convert("RGBA")`、存 PNG 时的 tRNS） | 同上；公开测试 `test_image_getpalette.py:24–44` 说明 RGBA 调色板是已支持特性 | 无（只比 Python 属性） | **缺失** | devcheck pr1：base 得 `getpalette_None_len 1024 768`、`rgba_render_equal False`；gold 得 `1024 1024`、`True`。W1 可利用 |
| 调用不修改源图 | 一般 API 语义（返回新图） | 无；断言在调用后才读 `im.palette.palette` | **缺失** | W5 可利用 |
| RGB 调色板与 L 模式行为不变 | 旧行为 | `test_1.py:604–605`、`test_remap_palette_transparency`（621–633） | 部分（只测恒等映射与 transparency 下标） | gold 通过 |
| 给了 `source_palette` 的路径（GIF 保存用） | docstring "source_palette: Bytes or None"；`GifImagePlugin.py:536` | 无（隐藏测试里没有 GIF 保存；grep 确认只有 JPEG/BMP/WEBP/PNG 保存） | **缺失** | devcheck pr4：base 与 gold 都得 `gif_rgb_equal: True`。R1 可利用 |
| 非 RGB/L 模式抛 `ValueError` | 旧行为 | `test_1.py:617–619` | 覆盖 | — |

反查：新增断言 (b) 直接来自题面示例；(a) 来自"identical mapping"的自然含义。两者都没有超出公开要求的隐藏约束，也没有内部 helper 名、精确文案或 Mock 形状之类的要求。

## 4. 可区分候选（改补丁即可跑；文件都是 `src/PIL/Image.py::Image.remap_palette`）

- **A1｜合理替代解，预期 1（71/71）。** 在 `if source_palette is None` 之前设 `palette_mode="RGB"`。P 分支里 `self.load()` 之后改为 `palette_mode = self.im.getpalettemode()`，`source_palette = bytes(self.getpalette(None))`（用公开 API，返回 list，要转成 bytes）。`bands = len(palette_mode)`，切片改用 `bands`。像素映射一步**保持 base**（`"RGB;L"` + `mapping_palette*3`）。删掉填充到 768 字节的代码，改为 `m_im.putpalette(palette_bytes, palette_mode)`（依赖 `_putpalette` 支持可变尺寸，`_imaging.c:1665/1676`）。最后设 `m_im.palette = ImagePalette.ImagePalette(palette_mode, palette=palette_bytes)`。它和 gold 有三处不同：用了公开 API、映射步不改、不填充。上游后来的 `a682ceaf` 初态也不做填充。`test_remap_palette_transparency` 用的是 `Image.new("P")` 的 256 项灰阶（`Palette.c:43`），不填充也安全。
- **W1｜只改 Python 侧调色板对象，预期 1（假阳性）。** base 的 RGB 流程全部保留（1873 行的 RGB 源、1918–1919 行填充并以 RGB 写回核心）。只把 1920 行改成：若原参数 `source_palette is None`、`self.mode=="P"` 且 `self.palette.mode=="RGBA"`，则取 `rgba = self.im.getpalette("RGBA","RGBA")`，设 `m_im.palette = ImagePalette.ImagePalette("RGBA", palette=b"".join(rgba[o*4:o*4+4] for o in dest_map))`；否则按 base。后果是核心调色板仍为 RGB、alpha 全 255，`r.getpalette(None)` 只有 768 项，`convert("RGBA")` 与原图不等，存 PNG 时没有 tRNS。但 `test_1.py:613–614` 只比像素索引和 Python 属性，所以 71/71。用题面示例自查也得 `True`，模型会以为修好了。区分方法：devcheck pr1 的 `getpalette_None_len` 和 `rgba_render_equal`。
  - 同类变体 **W5**：在 P 分支开头就地执行 `self.putpalette(self.getpalette("RGB"))`，把源图调色板改成 RGB，再走 base。因为断言在调用之后才读 `im.palette.palette`，两边都是 768 字节 RGB，仍是 71/71，代价是改坏了调用者的原图。
- **W2｜恒等映射短路，预期 1（假阳性）。** 在 1867–1868 行的模式检查之后加 `if source_palette is None and list(dest_map) == list(range(256)): return self.copy()`，其余不改。`copy()` 经 `_new` 逐字节复制调色板，所以恒等映射两段都通过；transparency 测试用 `[1,0]`，走的是 base 路径。结果 71/71，但非恒等的 RGBA 重排仍然丢 alpha（devcheck pr3 在 base 下的表现）。
- **R1｜未评分回归，预期 1。** 以 gold 为底，把 `palette_mode/bands` 的探测移出 `if source_palette is None`，即无论是否给了 `source_palette` 都按核心调色板模式取 `bands=4`。GIF 默认保存（`_save` 第 657 行默认 `optimize=True`，`_get_optimize` 在第 808 行后返回用到的颜色）会走 `_normalize_palette` 第 536 行，以 RGB 的 `source_palette` 调 `remap_palette`，R1 按 4 字节去切 RGB 数据，颜色就错了。隐藏测试不存 GIF，仍是 71/71。区分方法：devcheck pr4 的 `gif_rgb_equal`（base/gold 为 True，R1 预期为 False）。公开 `Tests/test_file_gif.py` 能否抓到未知。

## 5. R2E 专项

- **(a) 非 PASSED 期望键**：没有。`expected_output.json` 71 键全是 PASSED（sha256 `0421915b…`，与 grading bundle 和 `run_refs` 一致）。唯一跳过的是 `test_pathlib`：先存 `.jpg`，到 `.jp2` 时因 OPENJPEG 缺失而跳过（`test_1.py:165`），不成键。若候选弄坏 Path 存 JPEG，这个用例会变成 FAILED、多出一键而判 0，这属于合理的回归检出。
- **(b) 题面报错出现在 noop 目标键中**：是。见 §2 的 `test_1.py:614` 与字节 3 的差异。
- **(c) 题面泄漏修法**：属于定位级提示。题面点名 `remap_palette`、"RGBA palette modes"、"palette byte arrangement"，但没给代码。题面示例就是新增断言本身，按示例修到 `True` 就能拿到目标键，这也是 W1、W2、W5 都能蒙混的原因之一。
- **(d) base 版测试辅助、搬迁伪影、撞键**：
  - 隐藏测试用的是随包的 `r2e_tests/helper.py`（与 base 相同）。
  - 根目录 `conftest.py:1` 是 `pytest_plugins = ["Tests.helper"]`：评分时仍会以插件形式导入候选可写的 `Tests/helper.py`（base 版，本身无钩子）。
  - `Tests/conftest.py` 负责注册标记和打印报告头，但它不作用于 `r2e_tests`。旁证：评分日志的头部没有 Pillow 特性报告，devcheck 在 `Tests/` 下运行时有。因此 `pil_noop_mark`、`valgrind_known_error` 是未注册标记，只产生警告；`addopts` 里没有 `--strict-markers`。
  - 资产靠相对路径 `Tests/images/*` 从 `/testbed` 读取。
  - 只有一个测试文件，63 个方法加参数化共收集 72 项、跳过 1 项、得 71 键，没有重名。
  - 期望键带 ANSI 粗体码，因为 `setup.cfg:67` 是 `addopts = -ra --color=yes`。grading bundle 标了 `normalization_version: prime_decolor_v1`，账本里的失配键已去色，gold 71/71 也说明本题可正常适用该去色规则。
- **(e) 时间、随机、资源敏感**：`test_effect_noise`、`test_effect_spread` 带随机性，但阈值很宽；有若干用例改全局注册表（`test_registered_extensions_uninitialized`、`test_register_extensions`、`test_encode_registry`），依赖文件内的执行顺序，四次 current 运行都稳定。测试耗时约 0.3 秒，内存峰值约 510 MB，资源默认 2 CPU / 4 GiB。未见风险。
- **(f) 修订**：没有（`revisions.json` 为 `[]`）。不适用。

## 6. gold 检查

- 修到了原例：私有对照 pr1 得 `True`、调色板模式 RGBA/RGBA、长度 1024/1024、`rgba_render_equal True`；非恒等交换也正确（pr3）。
- RGB 调色板、L 模式、给了 `source_palette` 的路径都保持 `bands=3/"RGB"`，与 base 等价（只少了 `[:768]` 截断，而调色板最多 256 项，截断本来就无效）。
- 没有无关改动；投影后的 `included_paths` 只有 `src/PIL/Image.py`。
- 一个静态边角点，影响低，不列为问题：GIF 用户 `palette=` 分支（第 532 行，调用时不带 `source_palette`）在 RGBA 源图上现在会拿到 RGBA 调色板，随后第 538 行把 `im.palette.palette` 覆盖成 RGB 源字节，写出的调色板字节不变。只有再配上元组形式的 `background`，经 `_get_background → getcolor` 时才可能行为不同。未验证。

## 7. 开发条件（解题侧）

- **已实测**（devcheck，镜像 `305f39cc…`，真实 Claude Code 2.1.205 + 桩端点，agent uid 54321）：
  - `python` 指向 `/testbed/.venv/bin/python`（3.9.21）；PIL 从 `/testbed/src/PIL` 导入，编译扩展就地放在 `src/PIL/_imaging.cpython-39-x86_64-linux-gnu.so`，所以改 Python 立即生效。
  - 没有 pip；外部 DNS 被拒；`/testbed` 可写、属主是 agent；激活文件不可写；预检三项都通过。
  - 题面示例能复现（pr1 得 `same_palette_bytes: False`）。
  - 公开测试可运行：`Tests/test_image.py -k remap_palette` 2 passed。注意 base 版这个测试本身不暴露 bug，agent 只能靠题面示例或自写脚本验证。另外 `test_file_gif.py` 73 passed / 2 skipped，`test_image_putpalette.py` 5 passed，`test_image_getpalette.py` 2 passed。
  - 私有 gold 对照（同一镜像，root）下，这些公开测试的通过数相同。
- **需要注意**：
  - devcheck 与私有对照用的镜像 `305f39cc…`（`derived9` overlays），和 current 评分行用的 `0fb6caf2…`，**不是同一个 image ID**。两者同为 `r2e_derive_v1` 配方、同 tag 名的不同构建，只能按"同配方"引用，不能写成同一镜像。
  - `install.sh` 在镜像里未跟踪、也没导出到公开 worktree（manifest 里记为 `untracked_missing`），与本题无关。
  - 改 C 扩展需要重新编译，编译器是否可用未验证，本题也不需要。
- **actor 待验**：真实模型求解、经 Qwen adapter 的链路、模型实际收到的完整消息。

## 8. 交付与评分边界

- 合法修复只涉及 `src/PIL/Image.py`，不会被投影忽略。
- 评分时仍生效、且候选可写的是：`setup.cfg` 的 `addopts`、根目录 `conftest.py`、以插件形式加载的 `Tests/helper.py`、`Tests/images/*`。这些属于共享投影与测试路径规则（账本里有 `candidate_test_like_paths`、`candidate_touched_conftest_or_fixture` 字段），本题只记下这些杠杆存在，处理方式未核。

## 9. 题目关系

- 我核实了机械比对。本题 gold 的 13 行在 `pillow__f9d3ee0f`（base `df4bb346`）的公开初态里逐字出现，属实。此外 `pillow__a682ceaf`（base `7a1e2840`）的初态也包含这个修复，只是上游后来做了重构：去掉填充、改用 `msg=` 写法，逐字命中不到 80%，所以 **gold 扫描漏报了它**。
- 这两题公开的 `Tests/test_image.py` 都已有 "Test identity transform with an RGBA palette"。测试扫描看不出这层关系，因为本题改的是已有测试，没有新增函数名。
- 反方向：`2b061b68` 的 gold（9/9 行）和 `2d01f7d0` 的 gold（22/24 行）在本题初态里；`4bc64835` 只命中 1 行，证据弱。`2b061b68` 的新测试 `test_open_formats` 在本题中是一个回归键（PASSED），对本题无害。
- 影响：同仓 7 题可按时间排序。`f9d3ee0f` 与 `a682ceaf` 的初态暴露了本题的答案和测试，如果它们与本题分进不同的数据划分（训练 / 评测），就会互相泄漏。建议同簇划分。

## 10. 八方面小结

| 方面 | 已查 | 未查 / 未知 |
| --- | --- | --- |
| 公开需求 | 题面、提示、docstring、公开 RGBA 调色板测试 | 模型实际收到的渲染消息 |
| 材料与初始问题 | 各摘要、base 路径、noop 失败位置（执行） | — |
| 测试是否测到要求 | 全部新增断言与 helper；70 个回归键只按名称和受影响接口抽查 | 与本题无关的回归键逐条语义 |
| 误拒 | 无具体路径（A1） | A1 未实跑 |
| 回归与 gold | gold 语义、唯一调用者 GIF 路径、transparency 测试 | GIF 用户 palette + 元组 background 的边角；R1 未实跑 |
| 开发条件 | devcheck 与私有对照 | 真实模型、adapter；两镜像不同 ID |
| 交付边界 | 投影路径；conftest/插件/addopts 杠杆 | 共享规则对这些杠杆怎么处理 |
| 题目关系 | 两份扫描 + 公开包人工核对 | 上游公开导致的预训练暴露（静态无法判断） |

## 11. 暂定处置与建议队列

- 暂定：`needs_review`，理由是"静态候选（开发诊断）+ 测试偏宽"。没有误拒证据，也没有材料错配。
- 建议队列（交协调者安排，用正式评分代码）：
  1. **W1 与 A1**，优先。W1 得 1 即确认假阳性，A1 得 1 即确认无误拒。
  2. W2、W5，确认恒等映射、事后读源图这两个缺口。
  3. R1，跑正式评分并对照 pr4 公开检查。
- 可选修订方向（**不是本步结论**；按协议 §4 属于测试标准修订，要单独立版本）：
  - 调用前先快照 `im.palette.palette`；
  - 加断言 `im_remapped.getpalette(None) == im.getpalette(None)`；
  - 加一个非恒等的 RGBA 重排用例。
  - 依据是题面标题和描述。gold 与 A1 应当仍能通过（私有对照 pr1/pr3 支持 gold 通过），W1、W2、W5 作为触发反例。
- 原始 reward 保留，不做任何按失败键免责的规则。

## 附录：证据定位

- **current 评分行**（`run_refs.json` 中 `material=current`）：
  - noop：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:39`、`runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:39`，均为 70/71，`mismatched=["TestImage.test_remap_palette"]`。
  - gold：对应的 `ledger_*gold.jsonl:39`，均为 71/71，`patch_sha256=2edc27cd…`，与本地 `gold.patch` 一致。
  - 日志 `…_5d729b91`（noop，第 122–123 行）、`…_5e035000`（noop，第 26–48、122–123 行）、`…_32a54898`（gold，第 69、100 行）、`…_43e0bbe6`（gold，第 69、100 行）。四份日志的 sha256 均与 `run_refs` 一致。
  - 日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE=d3180199…` 和 `RH2_SETUP_ENTRY_SHA256=8285765f…` 分别与 `run_refs` 和 `run_tests.sh` 一致。
- **M3 对照**：`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pillow/3a61c9e95e5c/gold/a{1,2}/test_output.txt`，gold 71 passed / 1 skipped（来源镜像）。
- **devcheck**：`runs/r2e_actor_20260925/devcheck/pillow__3a61c9e95e5c0a2da5736956e2dbafa5/`：
  - `orig/captures/{r2e_preflight,env,pr1_1_cmd,pr3_2_cmd,pr4_3_cmd,pr5_4..7_pytest}.out`；
  - `orig/attempt.json`（`overlay.derived_image_id=305f39cc…`、`GIT_HEAD=355820742bc2…`）；
  - `private_gold/private_control.json`。
- **源码**（base worktree）：
  - `src/PIL/Image.py`：808–838、1430–1450、1782–1814、1854–1929；
  - `src/_imaging.c`：1064–1107、1641–1681；
  - `src/libImaging/Palette.c`：24–47；
  - `src/PIL/GifImagePlugin.py`：489–538、651–657、797–831、862–869；
  - `setup.cfg`：66–68；`conftest.py`：1。
