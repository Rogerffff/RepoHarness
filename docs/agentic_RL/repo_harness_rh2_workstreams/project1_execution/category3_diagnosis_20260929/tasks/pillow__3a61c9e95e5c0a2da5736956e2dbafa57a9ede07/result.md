# R2E pillow__3a61c9e9：第3类诊断结果（v2，经独立复核改判）

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“具体疑点缺辨别实验”。

**结论：问题和修法已明确，建议转第2类。** 首轮（v1）的结论是“疑点已消除，可申请转第1类”，被[独立复核](review.md)推翻。复核提出的现象我已全部亲自复现，据此改判：

- **N1，S1（§4 第 4 步）**：图的调色板是 RGBA，同时 `info["transparency"]` 为整数时，gold 的 `remap_palette` 抛 `ValueError('invalid palette size')`；base 不抛异常，但会丢 alpha，也就是题面缺陷本身。
  - 这仍是题面核心函数，输入也在它明确支持的范围内：公开测试 `test_remap_palette_transparency` 断言透明索引随映射移动。
  - 上游 Pillow 9.2.0 至 10.4.0 都有这个问题，11.0.0 才修好。
- **修法**：R-c v1 新增一个测试键，覆盖“RGBA 调色板＋透明索引”。私有评分结果：
  - gold 与 A1u 为 0，只错在新键上；
  - C1 和按上游 11.0 写法移植的 U11 为 1。

  按 D4，正对照从 gold 改为 C1，以 U11 作第二个正对照；两者都需要独立核实并跑正式评分。
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
| U11 | [`U11_trns.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/U11_trns.patch)，sha256 `1d48f9ad…`。在 gold 上移植上游 11.0.0 对 N1 的两处改动：`convert` 的透明度分支改为 `trns_im.putpalette(self.palette, self.palette.mode)`；`putpalette` 接受没有 rawmode 的 `ImagePalette` |

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

  参照先例：scrapy `e9387529` 中 gold 在有文档的路径上抛 `TypeError`，判 S1，走 R-c，并由 C1 作正对照。

  **反方理由**（复核也提到）：这种组合不常见，上游用了约两年才修；并且 base 在这些输入上同样不满足题面，只是没有抛异常。我按 D1 严格版判 S1：这是核心函数崩溃，不是输出细节差异，而且补一个断言的成本低。
- **N2–N4 判 T3**：
  - 触发条件是 GIF `palette=` 加元组背景色，文档只写“a palette color index”；
  - 所有保留 RGBA 调色板的合理修法都会暴露这个问题，也就是 GIF 插件在 `palette=` 分支写入 RGB 字节、却保留 RGBA mode；
  - 上游 11.0.0 在这条路径上仍然出错。

  这已超出本题范围，不补断言。
- **base 已有问题，与本题修法无关，单列 T3**：
  - RGBA 调色板配合换序 `palette=` 时颜色错位；
  - base 本身对 1024 字节的 RGBA Python 调色板加整数透明索引执行 `convert` 时也报同样的错（复核 exp5）；
  - `disposal=2` 时编码端和解码端对背景的处理不一致（复核 §3）。

## 5．修法：R-c v1（交第2类）

**修订测试**：[`hidden_test_1_revised_v1.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/hidden_test_1_revised_v1.py)，sha256 `87172901…`。基于 v4 的 `test_1.py`（`04f44d8a…`），在 `test_remap_palette_transparency` 之后新增 `test_remap_palette_rgba_transparency`：

- 2×1 图，像素为 `[0, 1]`，RGBA 调色板 `(10,20,30,40, 50,60,70,80)`，`info["transparency"] = 0`；
- 恒等映射 `[0, 1]`：像素不变，Python 调色板前 8 字节不变，透明索引仍为 0；
- 交换 `[1, 0]`：
  - 像素变为 `[1, 0]`；
  - Python 调色板前 8 字节变为 `(50,60,70,80, 10,20,30,40)`；
  - 透明索引变为 1；
  - `convert("RGBA")` 渲染为 `[(10,20,30,0), (50,60,70,80)]`，即透明项完全透明，另一项保留自身 alpha。

**修订期望**：[`expected_output_revised_v1.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/expected_output_revised_v1.json)，sha256 `af126a3c…`。在 v4 的 73 键（`3d86300f…`）上加一个新键 `TestImage.test_remap_palette_rgba_transparency: PASSED`，写法沿用原文件的 ANSI 键格式，共 74 键。其余键不变。

**断言依据与宽严**：
- 依据是两份公开约定的交集：题面要求 RGBA 调色板按整项搬动、恒等映射保持不变；公开测试和 base 代码要求透明索引随映射移动。期望值都是字面量，不照抄 gold 输出。
- 沿用 v4 的约束：只比前 8 字节，不对补齐长度或补齐项的 alpha 作要求（gold 补 0、C1 补 255、A1u 不补齐，都允许），也不限定写回方式。
- 渲染断言依赖 `convert` 的既有行为：整数透明索引转 RGBA 时 alpha 置 0。这一行为与修法无关。

**私有评分**：用 `run_tests.sh`（与评分包一致，sha256 `8285765f…`），按 RH2 移植的上游解析器（`parse_log_pytest` 与 `prime_calculate_reward`）逐键对照，脚本为 [`grade_r2e.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pillow3a61/grade_r2e.py)。

| 候选 | v4 材料（73 键） | 修订 v1（74 键） | v1 失败键与原因 |
| --- | --- | --- | --- |
| base（noop） | 0 | 0 | `test_remap_palette`、`…_rgba_reorder`、新键（调色板前 8 字节丢 alpha） |
| gold | 1 | **0** | 只有新键：`ValueError: invalid palette size` |
| A1u | 1 | **0** | 只有新键：同上 |
| C1（新正对照） | 1 | **1** | — |
| U11（第二正对照，上游 11.0 写法） | 1 | **1** | — |

v4 列的 gold、C1、A1u 都为 1，noop 为 0，与 R2E 线的正式评分一致，说明私有模拟可信。W1–W5 的补丁不在云端（在本地 `runs/r2e_actor_20260925/grader_cands/`）。修订只新增一个键，它们在 v4 各自失败的键不受影响，但仍需正式复验。

**交接给第2类**：

1. 在 R2E 修订单中登记两项修订（`hidden_test_text_replace` 与 `expected_file_replace`），版本接在 v5 之后，并构建派生镜像。
2. **正式评分**：noop 0、C1 1、U11 1、gold 0、A1u 0，W1–W5 保持 0。
   - C1 必须用正式评分过的原补丁 `pillow_3a61_C1_rgb_plus_alphas.patch`。本页的 C1 是按描述重建的，它在 v4 上的结果与正式 C1 一致，但没有逐字核对。
3. 按 D4 独立核实 C1 与 U11 可以作正对照。gold 在修订版上失败，这一点也要记入准入卡。
4. 准入卡的 S2 与 T3 按 §4 改写，删去 “I5 静态推断、未测”。
5. Codex 复核。

## 6．当前用途

| 用途 | 结论 |
| --- | --- |
| 问题定位 | yes |
| 能力比较 | 沿用准入卡结论（yes，按 v4 标明版本）。注意 gold 式实现在 v4 上得 1，但带透明索引时会崩溃 |
| 训练候选 | **在 R-c v1 落地并验收前为 no**：存在未处理的 S1 |
| 留出评测 | 跟随训练结论 |

## 7．未做与证据

- 本页所有评分都是私有模拟；R2E 正式评分和派生镜像没有在云端重建。
- 修订 v1 还没有独立复核。
- C1 是按描述重建的版本，见 §5。
- 其它 GIF 解码器对游离字节的处理未查；PNG、WebP 保存 RGBA 调色板的路径未查。
- 真实 actor 开发条件未验；没有模型求解证据。
- 证据：[evidence/](evidence/)
  - `semantic_v1/`、`extra/`：v1 的四版本对照
  - `revised_v1/`：修订版私有评分；`grades.jsonl` 为逐键结果，`n1_probe.out` 为 N1 矩阵
  - `gif_bg_v1/`：N2–N4
  - `upstream_check/`：上游 9.2.0、10.4.0、11.0.0 的对照，以及 changelog 摘录
  - `evidence_manifest.json`

  补丁与脚本在 `rh2/experiments/category3_cloud_20260929/pillow3a61/`。
