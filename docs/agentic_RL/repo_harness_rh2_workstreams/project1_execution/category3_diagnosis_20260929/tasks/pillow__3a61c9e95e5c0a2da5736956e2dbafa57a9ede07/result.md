# R2E pillow__3a61c9e9：第3类诊断结果（v2，经独立复核改判）

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“具体疑点缺辨别实验”。

**结论：问题和修法已明确，建议转第2类。** 首轮（v1）的结论是“疑点已消除，可申请转第1类”，被[独立复核](review.md)推翻。复核提出的现象我已全部亲自复现，据此改判：

- **N1，S1（§4 第 4 步）**：图的调色板是 RGBA，同时 `info["transparency"]` 为整数时，gold 的 `remap_palette` 抛 `ValueError('invalid palette size')`；base 不抛异常，但会丢 alpha，也就是题面缺陷本身。
  - 这仍是题面核心函数，输入也在它明确支持的范围内：公开测试 `test_remap_palette_transparency` 断言透明索引随映射移动。
  - 上游 Pillow 9.2.0 至 10.4.0 都有这个问题，11.0.0 才修好。
- **修法**：R-c v2 新增一个测试键，覆盖“RGBA 调色板＋透明索引”，包括 2 项和满 256 项两种调色板。14 个候选的私有评分结果：
  - gold 与 A1u 为 0，只错在新键上；
  - 6 个合理实现为 1，包括 C1、按上游 11.0 写法移植的 U11，以及复核构造的 4 个；
  - noop 与另外 5 个错误候选为 0。

  按 D4，正对照从 gold 改为 C1，以 U11 作第二个正对照；两者都需要独立核实并跑正式评分。v1 的测试被 v2 聚焦复核指出能放过一个错误候选，已补上。
- **I5 的后果（N2–N4）**：确实可见，v1 写的“无可观察后果”不对。但这些后果只在 GIF 用 `palette=` 保存、并传入元组背景色时出现，文档没有这种用法。所有保留 RGBA 调色板的修法（gold、C1、A1u、U11）表现相同，上游 10.4.0 也相同，所以按 T3 登记，不修。

## 1．背景

题面要求 `remap_palette` 正确处理 RGBA 调色板：恒等映射后调色板应与原来相同。R2E 线已按 R-c 修订到材料 v4，即 `r2e-mr-024/025`，新增 `…_rgba_reorder`、`…_rgba_gif_save` 两键，共 73 键。v4 已完成正式评分：gold、C1、A1u 为 1，noop 和 W1–W5 为 0。准入卡记为 `probe_ready`，见[准入卡](../../../r2e_lifecycle_20260929/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/probe_card.md)。

v2 分类把本题留在第3类，只因为旧静态观察 I5：GIF 的 `_normalize_palette` 在 `palette=` 分支调用 `remap_palette(used)` 时不传 source，gold 返回 RGBA mode 的 Python 调色板，随后调用者写入 RGB 字节，mode 与字节格式不一致。

## 2．首轮哪里错了

v1 只测了一张 4×1 的 RGBA 调色板图，没有透明索引，背景只用了一种元组。在这类输入上，gold 与 base 的读回确实相同，于是得出“无可观察后果、疑点已消除”。复核扩大到 426 例后发现两类问题：

1. 加上透明索引后 gold 直接抛异常（N1），这比 I5 严重；
2. 元组背景色会把 I5 的后果暴露出来（N2–N4）。

v1 的 `semantic_v1/` 数据本身没错，只是覆盖面不够，不能支撑“疑点已消除”。

## 3．实测（全部为私有对照）

实验方式：原镜像 `namanjain12/pillow_final@sha256:bdd3d967…8813`，root、断网、一次性容器。比较的版本：

| 版本 | 来源 |
| --- | --- |
| base | 原镜像 |
| gold | 题目参考修复 |
| C1 | 按旧卡描述重建：C 层写 RGB，再 `putpalettealphas` 补 alpha |
| A1u | 同仓后续写法，不补齐到 256 项 |
| U11 | [`U11_trns.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/U11_trns.patch)，sha256 `1d48f9ad…`。在 gold 上按上游 11.0.0 改两处：`convert` 的透明度分支改为 `trns_im.putpalette(self.palette, self.palette.mode)`（11.0.0 新增）；`putpalette` 与 11.0.0 逐行一致，其中接受无 rawmode 的 `ImagePalette` 是 11.0.0 新增，按 rawmode 设置 mode 那一行 10.4.0 已有。`remap_palette` 仍是 gold 版，11.0.0 的版本不补齐到 256 项（复核核对） |

**（1）N1**：[`n1_probe.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/n1_probe.py)

| 输入 | base | gold | A1u | C1 | U11 |
| --- | --- | --- | --- | --- | --- |
| 题面示例（不加透明索引） | 丢 alpha（题面缺陷） | 正确 | 正确 | 正确 | 正确 |
| 题面示例加 `transparency=0` 或 `3` | 不抛异常，丢 alpha | **ValueError** | **ValueError** | 正确，透明索引保留 | 正确 |
| 4 色 RGBA 调色板图加 `transparency=3`，恒等映射或交换 | 同上 | **ValueError** | **ValueError** | 正确 | 正确 |
| RGBA 图 `quantize(16)` 后加透明索引，再重映射 | C 层变 RGB | **ValueError** | **ValueError** | RGBA，透明索引 0 | 同 C1 |
| RGBA 模式图用 `palette=` 保存 GIF（文档化的保存参数；`_normalize_mode` 会自动补透明索引） | 不抛异常，颜色错位（base 已有） | **ValueError** | **ValueError** | 同 base | 同 base |
| RGBA 模式图不带 `palette=` 保存 GIF | 正确 | 正确 | 正确 | 正确 | 正确 |

**上游核对**：把 PyPI wheel 解压到同一镜像，用 `PYTHONPATH` 加载后运行同一脚本。

| 上游版本 | N1 行为 |
| --- | --- |
| 9.2.0（gold 所在版本）、9.3.0、10.4.0 | 与 gold 相同，都抛 `ValueError` |
| 11.0.0 | 正确 |

11.0.0 的 changelog 中相关条目是“Improved handling of RGBA palettes when saving GIF images #8366”。该条目与具体行的对应关系没有逐行核对，因为云端无法访问 GitHub PR。wheel 的 sha256 见 `evidence/upstream_check/wheels_sha256.txt`。

**（2）N2–N4**：[`gif_bg_probe.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/gif_bg_probe.py)。自写 GIF 头解析：`gct_entries` 为全局色表项数，`next_byte` 为色表后第一个字节，正常应为 `0x2c`。

| 场景（都传元组背景 `(0,255,0)`） | base | gold = C1 = A1u = U11 = 上游 10.4.0 | 上游 11.0.0 |
| --- | --- | --- | --- |
| 原序 `palette=` | 4 项，`0x2c`，背景正确 | **8 项，游离字节 `0x00`**，背景色正确 | 背景索引越界 |
| 反转 `palette=` | 背景索引 2，指向 `(0,255,0)`，正确 | **背景索引 1，指向 `(0,0,255)`，颜色错** | 像素错 |
| 256 项 `palette=`，像素用到索引 255 | 像素 `(255,0,249)`，正确 | **像素 `(255,255,0)`，错** | 像素错 |
| 换序 `palette=` 配整数背景色 | 全部相同 | 全部相同 | 像素错 |

我这次用的换序与作者原配置略有不同，游离字节在“原序＋元组背景”中复现；复核在作者原配置下也观察到游离字节（review.md R3）。

**（3）公开测试**：`Tests/test_image.py`、`test_file_gif.py`、`test_image_convert.py`、`test_image_putpalette.py`、`test_imagepalette.py`、`test_image_quantize.py` 合计 199 passed / 4 skipped，五个版本相同。U11 改了 `convert` 与 `putpalette`，但没有破坏这些公开测试。

## 4．判定

- **N1 判 S1（§4 第 4 步）**：gold 在原材料与 v4 都得 1，但在同一核心要求的另一个实例上抛异常。这个实例是“RGBA 调色板图重映射”，只多了一个整数透明索引。不按边缘输入处理，理由有三：
  - `remap_palette` 自己的代码专门处理 `info["transparency"]`（base `Image.py` 约 1924–1928 行），公开测试 `Tests/test_image.py:612-624` 断言透明索引随映射移动，文档写明 `transparency` 是 “Transparency color index”；
  - Pillow 自己的 GIF 保存流程会生成这种组合：`_normalize_mode` 给 RGBA 图补透明索引。于是文档化的 `palette=` 保存对 RGBA 模式图全部抛异常；
  - 上游在 11.0.0 修了这个问题，说明它是真实缺陷。

  参照先例：
  - 标准 §10 的 numpy `5e8301c2`：同样是第 4 步，gold 在同一要求的另一实例上失败，按 D4 改用替代正对照。这是最贴近的成文先例；
  - scrapy `e9387529`：gold 在有文档的路径上抛 `TypeError`，判 S1，走 R-c，并由 C1 作正对照。

  **反方理由**（复核也提到）：这种组合不常见，上游用了约两年才修；并且 base 在这些输入上同样不满足题面，只是没有抛异常。我按 D1 严格版判 S1：这是核心函数崩溃，不是输出细节差异，而且补一个断言的成本低。
- **N2–N4 判 T3**：
  - 触发条件是 GIF `palette=` 加元组背景色，文档只写“a palette color index”；
  - 所有只改 `Image.py` 的修法都会暴露这个问题：gold、A1u、C1、U11 以及复核构造的几种写法，输出逐字相同。原因是 GIF 插件在 `palette=` 分支写入 RGB 字节、却保留 RGBA mode；
  - 复核构造的 G_gif（U11 加 4 行 GIF 插件改动）能消除 N2–N4，并且在修订版上同样得 1，说明修订材料不惩罚更完整的修法；
  - 上游 11.0.0 在这条路径上仍然出错。

  这已超出本题范围，不补断言。
- **base 已有问题，与本题修法无关，单列 T3**：
  - RGBA 调色板配合换序 `palette=` 时颜色错位；
  - base 本身对 1024 字节的 RGBA Python 调色板加整数透明索引执行 `convert` 时也报同样的错（复核 exp5）；
  - `disposal=2` 时编码端和解码端对背景的处理不一致（复核 §3）。

## 5．修法：R-c v2（交第2类）

**修订测试**：[`hidden_test_1_revised_v2.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/hidden_test_1_revised_v2.py)，sha256 `78631c73…`。

- 版本链：v4 的 `test_1.py`（`04f44d8a…`）→ v1（`87172901…`）→ v2。
- 修订都放在 `test_remap_palette_transparency` 之后新增的测试函数 `test_remap_palette_rgba_transparency` 里。

v1 部分（小调色板）：
- 2×1 图，像素为 `[0, 1]`，RGBA 调色板 `(10,20,30,40, 50,60,70,80)`，`info["transparency"] = 0`；
- 恒等映射 `[0, 1]`：像素不变，Python 调色板前 8 字节不变，透明索引仍为 0；
- 交换 `[1, 0]`：
  - 像素变为 `[1, 0]`；
  - Python 调色板前 8 字节变为 `(50,60,70,80, 10,20,30,40)`；
  - 透明索引变为 1；
  - `convert("RGBA")` 渲染为 `[(10,20,30,0), (50,60,70,80)]`，即透明项完全透明，另一项保留自身 alpha。

v2 新增部分（满 256 项调色板），来自 v2 聚焦复核的阻断项 B-v2-1：
- 题面示例的 256 项 RGBA 调色板，加 `info["transparency"] = 0`；
- 恒等映射后，调色板与调用前快照相同，透明索引为 0；
- 交换前两项后，前 8 字节互换，透明索引为 1。

新增原因：复核构造的错误候选 G_small 只按源调色板长度截取映射调色板，在 v1 上得 1。但调色板超过 192 项再加透明索引时，它仍抛同一个 `ValueError`，题面示例加 `transparency=0` 就能触发。复核给出的补法只断言透明索引；这里改为与 v4 一致的调用前快照，并加一条交换后前 8 字节的检查。

**修订期望**：[`expected_output_revised_v1.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/expected_output_revised_v1.json)，sha256 `af126a3c…`。
- 在 v4 的 73 键（`3d86300f…`）上加一个新键 `TestImage.test_remap_palette_rgba_transparency: PASSED`，共 74 键，写法沿用原文件的 ANSI 键格式，其余键不变；
- v2 没有新增键，期望文件沿用 v1 版。

**断言依据与宽严**：
- 依据是两份公开约定的交集：题面要求 RGBA 调色板按整项搬动、恒等映射保持不变；公开测试和 base 代码要求透明索引随映射移动。期望值都是字面量或调用前快照，不照抄 gold 输出。
- 沿用 v4 的约束：小调色板只比前 8 字节，不对补齐长度或补齐项的 alpha 作要求（gold 补 0、C1 补 255、A1u 不补齐，都允许），也不限定写回方式。
- 渲染断言依赖 `convert` 的既有行为：整数透明索引转 RGBA 时 alpha 置 0（base `Image.py` 第 1000–1009 行）。所有候选（包括 U11）都没有改这条分支。
- 透明项的 alpha 取 40 而不是 0，用来区分“把透明烘进 alpha”的写法（A0K、A0D）。它们改变了恒等映射后的调色板，违反题面。

**私有评分**：
- 测试命令：`run_tests.sh`，与评分包一致，sha256 `8285765f…`；
- 解析：用 RH2 移植的上游解析器（`parse_log_pytest` 与 `prime_calculate_reward`）逐键对照，脚本为 [`grade_r2e.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/grade_r2e.py)；
- 结果：`evidence/revised_v2/grades.jsonl`，共 14 个候选。

| 候选 | 来源 | 做法 | v4（73 键） | v1（74 键） | **v2（74 键）** |
| --- | --- | --- | --- | --- | --- |
| base（noop） | — | — | 0 | 0 | 0 |
| gold | 参考修复 | — | 1 | 0 | **0**（`ValueError`） |
| A1u | R2E 线 | 同仓后续写法 | 1 | 0 | **0**（同上） |
| C1（新正对照） | 主审重建 | C 层写 RGB 加 `putpalettealphas` | 1 | 1 | **1** |
| U11（第二正对照） | 主审 | gold 加上游 11.0.0 的透明度改动 | 1 | 1 | **1** |
| G_del | 复核 | gold，内部 `convert("L")` 前去掉透明键 | 1 | 1 | **1** |
| G_cim | 复核 | gold，映射那一步改走 C 层转换 | 1 | 1 | **1** |
| HYB | 复核 | 有透明索引时走 C1，否则走 gold | 1 | 1 | **1** |
| G_gif | 复核 | U11 加 4 行 GIF 插件改动 | 1 | 1 | **1** |
| A0K、A0D | 复核 | 把透明项 alpha 写成 0（保留／删除透明键） | 1 | 0 | **0** |
| FB | 复核 | 遇 `ValueError` 退回 RGB 源调色板，丢 alpha | 1 | 0 | **0** |
| DROP | 复核 | RGBA 调色板时丢弃透明键 | 1 | 0 | **0** |
| G_small | 复核 | 映射调色板只取源调色板长度 | 1 | **1** | **0** |

补充说明：
- v2 的所有失败都只在新键上，base 另外失败两个 v4 已有的键。
- 6 个公开测试文件对全部 14 个候选都是 199 passed / 4 skipped。
- 复核候选由 `reviewer_cands/mkcand.py` 生成补丁：脚本来自复核者，补丁由主审生成。
- v4 列的 gold、C1、A1u 为 1，noop 为 0，与 R2E 线的正式评分一致，说明私有模拟可信。
- W1–W5 的补丁不在云端（在本地 `runs/r2e_actor_20260925/grader_cands/`）。修订只新增一个键，它们在 v4 各自失败的键不受影响，但仍需正式复验。

**交接给第2类**：

1. 在 R2E 修订单中登记两项修订（`hidden_test_text_replace` 按 v2 文本、`expected_file_replace` 为 74 键），版本接在 v5 之后，并构建派生镜像。
2. **正式评分**：
   - noop、gold、A1u 为 0；
   - C1、U11 为 1；
   - W1–W5 保持 0；
   - 建议加跑 G_small、HYB、G_gif。

   C1 必须用正式评分过的原补丁 `pillow_3a61_C1_rgb_plus_alphas.patch`。本页的 C1 是按描述重建的，它在 v4 上的结果与正式 C1 一致，但没有逐字核对。
3. 按 D4 独立核实 C1 与 U11 可以作正对照。v2 聚焦复核已在私有层面核实：U11 满足题面；全量公开测试中，U11 与 base 逐测试结果相同。
4. 准入卡相应修改：
   - gold 在修订版上失败，正对照改为 C1；
   - A1u 由“合理替代解，期望 1”改为期望 0，理由是透明索引下同样崩溃；
   - S2 与 T3 按 §4 改写，删去 “I5 静态推断、未测”。
5. 在训练价值备注中写明：修订后 gold 式的自然写法得 0，题目难度上升。
6. Codex 复核。

## 6．当前用途

| 用途 | 结论 |
| --- | --- |
| 问题定位 | yes |
| 能力比较 | 沿用准入卡结论（yes，按 v4 标明版本）。注意 gold 式实现在 v4 上得 1，但带透明索引时会崩溃 |
| 训练候选 | **在 R-c v2 落地并验收前为 no**：存在未处理的 S1 |
| 留出评测 | 跟随训练结论 |

## 7．未做与证据

- 本页所有评分都是私有模拟；R2E 正式评分和派生镜像没有在云端重建。
- **复核经过**：
  - 独立复核推翻首轮结论；
  - 主审 v2 的聚焦复核同意 N1 判 S1、新断言有依据且不过严、U11 可作第二正对照、N2–N4 判 T3，只有一项阻断 B-v2-1（G_small）；
  - 已按其补法改为 R-c v2，14 个候选重新评分，结果与复核者的扩展版私测一致。

  R-c v2 本身未再复核，交第2类时由 Codex 复核一并确认。
- C1 是按描述重建的版本，见 §5。
- 其它 GIF 解码器对游离字节的处理未查；PNG、WebP 保存 RGBA 调色板的路径未查。
- 真实 actor 开发条件未验；没有模型求解证据。
- 证据：[evidence/](evidence/)
  - `semantic_v1/`、`extra/`：v1 的四版本对照
  - `revised_v1/`：修订版私有评分；`grades.jsonl` 为逐键结果，`n1_probe.out` 为 N1 矩阵
  - `gif_bg_v1/`：N2–N4
  - `upstream_check/`：上游 9.2.0、10.4.0、11.0.0 的对照，以及 changelog 摘录。做法是把完整 wheel 解压后用 `PYTHONPATH` 加载，并确认 `PIL.__file__` 指向解压目录；复核另测了 9.3.0–10.3.0，结果相同
  - `revised_v2/`：14 个候选 × v4、v1、v2 的私有评分
  - `evidence_manifest.json`

  补丁与脚本在 `rh2/experiments/category3_cloud_20260929/pillow3a61/`。
