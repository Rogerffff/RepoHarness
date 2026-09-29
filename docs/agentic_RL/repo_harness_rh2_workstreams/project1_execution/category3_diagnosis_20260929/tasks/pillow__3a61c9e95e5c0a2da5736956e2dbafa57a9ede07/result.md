# R2E pillow__3a61c9e9：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“具体疑点缺辨别实验”。

v2 分类指出一个只有源码推断的风险：gold 在 GIF `palette=` 分支里 Python 调色板的 mode 与字节格式不一致，可能涉及同一调色板要求，不能只写 S2 放行。要做的是核实际 mode、字节和保存读回，区分真实回归与无依据的格式扩张。

**结论：疑点已消除，可申请转第1类。**

- 在该分支上，gold 与 base 的保存读回像素、调色板和索引逐项相同。唯一的可观察差别是元组背景色的索引，两者都指向正确颜色。
- RGBA 调色板图配合换序 `palette=` 保存时颜色会错位，这是 base 已有的 GIF 插件问题，与本题无关，登记为 T3。
- 不需要新的正对照或修订。本题的修订材料 v4 与既有准入卡仍然适用。

独立复核待做。

## 1．背景

题面要求 `remap_palette` 正确处理 RGBA 调色板：恒等映射后调色板应与原来相同。R2E 线已按 R-c 修订为 `r2e-mr-024/025`（v4），并完成正式评分（8 行符合预期）、devcheck 与 Codex 复核，登记为 `probe_ready`，见 [准入卡](../../../r2e_lifecycle_20260929/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/probe_card.md)。

v2 分类把本题留在第3类，只因为旧静态观察 I5：`GifImagePlugin._normalize_palette` 的 `palette=` 分支调用 `remap_palette(used)` 时不传 source。对 RGBA 调色板图，gold 返回 mode 为 RGBA 的 Python 调色板，随后调用者写入 RGB 字节，mode 与字节格式不一致；base 在这里是 RGB。

## 2．实验

- 镜像：原 R2E 镜像 `namanjain12/pillow_final@sha256:bdd3d967…8813`，与冻结摘要一致。
- 方式：root、断网、一次性容器（`semantic_control.py`）。gold 只改 Python，不需要重编。
- 版本：base、gold，以及 R2E 线已验证的两个合理替代解 C1（RGB 写回＋`putpalettealphas`）和 A1u（不补齐）。C1 按旧卡描述重建；A1u 取自既有补丁，应用时忽略空白差异。

**RGBA 调色板图**：4 种颜色，alpha 分别为 255/128/255/0。

| 检查 | base | gold | C1 | A1u |
| --- | --- | --- | --- | --- |
| `_normalize_palette(im, 换序的 palette=)`：Python 调色板 mode／长度 | RGB／12 | **RGBA／12**（mode 与字节不一致，I5 属实） | RGBA／12 | RGBA／12 |
| 同上：C 层调色板 mode、像素索引、RGB 渲染 | RGB、`[0,1,2,3]`、正确 | RGBA、`[0,1,2,3]`、正确 | 同 gold | 同 gold |
| 以换序 `palette=` 保存后读回的像素颜色 | **错位** | **错位**（与 base 逐项相同） | 同左 | 同左 |
| 以换序 `palette=` 加元组背景色 `(0,255,0)` 保存：背景索引／颜色 | 3／`(0,255,0)` | **4**／`(0,255,0)` | 4／同 | 4／同 |
| 以原序 `palette=` 保存后读回 | 正确 | 正确 | 正确 | 正确 |
| 不带 `palette=` 保存后读回 | 正确 | 正确 | 正确 | 正确 |

**RGB 调色板图（对照）**：上述各项在四个版本中完全相同，并且全部正确。

**公开测试**：`Tests/test_file_gif.py` 为 73 passed / 2 skipped，`Tests/test_image.py` 为 71 passed / 1 skipped，四个版本相同。

## 3．判定

- **I5 的不一致确实存在，但没有造成可观察的回归。** 在测试的输出上（读回像素、调色板、索引），gold 与 base 完全相同。背景色索引多占一个调色板项（4 与 3），但写入文件的颜色正确，GIF 读者看到的背景相同。要求 gold 在这个内部分支保持 RGB mode，没有公开依据，属于“无依据的格式扩张”。
- **颜色错位是既有问题。** `_normalize_palette` 用 RGB 三元组去查 RGBA 调色板的 `colors` 字典，查不到，于是不做重映射；按原序传 `palette=` 时不受影响。这一问题在 base 上已经存在，题面也没有涉及 GIF 保存，登记为 T3。
- 因此本题**不需要新的正对照、修订或正式评分**。R2E 线 v4 的正式评分、devcheck 与 Codex 复核结论不受影响。

## 4．建议的转类

建议申请转回第1类，沿用 R2E 线准入卡的材料 v4、派生镜像和用途结论。需要补登记的剩余事项：

- **T3**：RGBA 调色板图在 GIF `palette=` 换序时颜色错位，base 已有，本题不修，也不测。
- **S2**：GIF `palette=` 分支的 Python 调色板 mode 与字节格式不一致，无可观察后果。

转类前还需要：本题独立复核，以及第1类线程接收时核对准入卡的版本与链路条件（准入卡已写明）。

## 5．版本与证据

- C1、A1u、gold 补丁及行为脚本：`rh2/experiments/category3_cloud_20260929/pillow3a61/`
  - `gif_behavior.py`
  - `gif_behavior2.py`：原序／换序补充
- 原始输出：[evidence/](evidence/)
  - `semantic_v1/`：四个版本的矩阵与公开测试
  - `extra/gif2_*.json`
  - `evidence_manifest.json`
- 没有做正式评分：本题的问题是 gold 在评分集之外的行为风险，由私有对照即可回答。R2E 派生镜像没有在云端重建。
