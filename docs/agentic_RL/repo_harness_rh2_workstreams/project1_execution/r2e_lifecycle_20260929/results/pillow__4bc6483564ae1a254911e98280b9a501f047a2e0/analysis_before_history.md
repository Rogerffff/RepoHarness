# 私有主审初判（读历史前）：pillow__4bc6483564ae1a254911e98280b9a501f047a2e0

- 角色：R2E 私有主审（单题闭环试行，按统一标准 v1），干净上下文。整理时间 2026-09-29 07:07 +08。
- 本稿封存于读历史之前：没有打开本题 `history/`、任何 `*review*` 目录、`docs/.../r2e_env_repair_20260924/`，也没有读本批 README、`board.json`、`assignments.json`。
- 没有运行项目代码、没有开容器或远端。唯一的本地计算是用 `git hash-object` 算文件哈希、用 `diff` 比对文件。
- 路径约定：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`；`wt/` = `PUB/worktree/`（即解题者看到的 `/testbed`）。
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`。
  - `noop.log` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_8c5689aa.eval.log`；`gold.log` = 同目录 `evallog_replay-r2e-rf-all-gold-p_48c7d1b3.eval.log`。
- 证据层次分四种写：静态推断、历史运行（旧机 09-23 / 09-24 的 current 行，以及 M3 独立 runner）、当前 CPU（待协调者）、真实模型（无）。

## 0. 结论先行（暂定）

- **题目目标**：让 `ImageOps.invert` 能处理 mode "1"（二值）图，不再抛 `OSError: not supported for this image mode`，并且真的输出反相后的二值图。
- **主要问题：S1（T2a；T2b 待退化探测实跑确认）**。
  - 隐藏测试里与本题有关的只有一行冒烟调用：`ImageOps.invert(hopper("1"))`（`PRIV/hidden_tests/test_1.py:66`）。它只检查"不抛错"，对输出不做任何断言。
  - 因此，对 mode "1" 原样返回输入副本这种不反相的补丁，按静态推断会得 1。
  - 其余 23 个键是同文件的旧测试，与公开 `wt/Tests/test_imageops.py` 逐字相同（`diff` 只差第 66 行）。
- **没有发现误拒合理解的风险（T1）**：没有精确文案、内部 helper 或 mock 形状断言，期望映射 24 键全是 PASSED。
- **gold 的边界（登记为 S2，不作处置依据）**：
  - 题面示例 `Image.new("1", (128, 128), color=1)` 在 base 里每个像素的原始字节是 1。
  - gold 用 `255 - v` 把它变成 254。按仓库的 1-bit 语义（非零即白），结果仍是全白，看起来没有反相。
  - 公开材料里两种读法都有依据，测试也没有断言这一点，所以不构成误拒或漏判。修订时不应对非规范值断言，见 §4、§10。
- **暂定处置**：`static_review` / `needs_review`，理由是题意与测试（S1），不是环境。
  - 建议走 R-c：在 `hidden_tests/test_1.py` 补一个非示例实例（`hopper("1")`）的反相结果断言，草案见 §10。
  - R-c 验收通过、Codex 复核后，可作训练候选。
- **v1 用途（暂定）**：

  | 用途 | 暂定 | 说明 |
  | --- | --- | --- |
  | 问题定位 | yes | 无门槛 |
  | 能力比较 | conditional | 还差 devcheck 的 actor 条件，以及预登记的事后审计（对得 1 的补丁查反相是否真实发生），或者改用 R-c 后版本 |
  | 训练候选 | no | 当前材料有未处理的 S1；R-c 验收后重评 |
  | 留出评测候选 | no | 同上；另有同仓跨题包含关系（X1） |

- **最关键的未知项**：
  1. 退化候选 D1 在新机器的正式评分里是否得 1。静态推断几乎确定会得 1，但 v1 要求实跑，并核对补丁确实交付、目标测试确实执行。
  2. 解题侧（uid 54321）的 `PIL` 是否从 `/testbed/src/PIL` 导入。评分侧已实测是，解题侧待 devcheck。
- **唯一最值得先做的下一步**：用正式评分实跑 D1（§6），同时收 devcheck 的公开命令结果。

## 1. 八方面覆盖（已查 / 未查）

| 方面 | 已查 | 未查或待查 |
| --- | --- | --- |
| 公开需求 | 题面全文（`PUB/user_prompt.txt:1-26`）、`public_hints`（`PUB/public_bundle.json:15`）、`environment_brief.md`、公开读者产物；base 的 docstring 与文档：`wt/src/PIL/ImageOps.py:518-528`、`wt/docs/reference/ImageOps.rst:7-9`、`wt/docs/handbook/concepts.rst:28-32`（"a 1-bit pixel has a range of 0-1"） | 模型实际收到的完整消息（环境卡 §2 标为未知） |
| 材料与初始问题 | base `ImageOps.py` 的 git blob 是 `c6201d8ff…`，与 gold 的 index 前像一致；题面 commit `a6efaa1ae1d0` 等于 `base_commit`；`initial_diff` 为 0 字节；隐藏测试树 sha `7e15b739…` 与日志 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致；noop 在 `ImageOps.py:58` 抛出题面所述的 `OSError`（noop.log:70-93, 119） | 题面示例原样复现只有静态推断，待 devcheck 的 `repro_issue_example` |
| 测试是否测到要求 | 逐行读完 `test_1.py` 与 `helper.py`；目标键 `test_sanity` 只有冒烟调用，没有值断言 | — |
| 是否误拒合理解 | 查了所有断言的公开来源；没有文案、helper 或 mock 约束；三条替代路线（改 `invert`、放宽 `_lut`、复用 `ImageChops.invert` / 经 "L" 中转）都不会触发任何键变化 | 替代解 A1 的正式评分（可选，主要给 R-c 验收用） |
| 回归与 gold 完整性 | gold 只改 `invert` 的一行，L/RGB 路径不变；`_lut` 的其它使用者不受影响；`ImageOps.invert` 在源码中唯一的内部调用方 `wt/src/PIL/TiffImagePlugin.py:1675` 只用于 L，不受影响 | invert 的 L/RGB 输出值在隐藏测试中没有值断言（T3）；gold 在非规范值上的行为只有静态推断 |
| agent 开发条件 | 评分侧：`RH2_OBS_IMPORT_PATH=/testbed/src/PIL/__init__.py`（ledger 第 41 行），pytest 8.3.4，JPEG 可用，内存峰值约 510 MB，测试 <1 s | 解题侧 uid 54321 的导入路径、公开命令实际结果、墙钟时间、HEAD 无子提交与隐藏测试不可读的预检：都等 devcheck |
| 交付与评分边界 | gold 实测投影 `included_paths=['src/PIL/ImageOps.py']`；隐藏 `helper.py` 与 base `wt/Tests/helper.py` 相同（`diff` rc=0），并由 grader 恢复；资产用相对路径 `Tests/images/...`，从 `/testbed` 运行可解析；原 `wt/Tests/conftest.py` 只加报告头和 marker，搬迁后失效不影响本题 | 共享平台机制（conftest 篡改等）不在本题复查 |
| 题目关系与用途 | 核对了两份跨题比对，并打开同仓其它题的公开包逐条确认（§9） | 不猜基座成功率 |

## 2. 需求—断言双向表（核心映射）

**正向：公开要求 → 测试**

| # | 公开要求或合理旧行为 | 公开依据 | 测试 ID 与决定性断言 | 覆盖 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- | --- |
| R1 | mode "1" 调 `invert` 不再抛 `OSError` | `user_prompt.txt:3-6, 19-26` | `test_sanity`：`test_1.py:66` `ImageOps.invert(hopper("1"))`，只要不抛错就通过 | 覆盖，但只有"不抛错"；输入是 `hopper("1")`，不是题面示例的字面值 | noop FAILED（noop.log:91, 119）；gold PASSED（gold.log:27）；旧机各 2 次，M3 独立 runner 2 次 |
| R2 | 输出是反相后的二值图（核心） | `user_prompt.txt:20` "successfully invert the binary image"；docstring `ImageOps.py:520` "Invert (negate) the image" | **没有任何断言** | **缺失 → T2a** | 退化探测 D1 待实跑（§6） |
| R3 | 输出仍为 mode "1"、尺寸不变、不修改输入 | 推断：`Image.point` 的输出模式默认与输入相同（`wt/src/PIL/Image.py:1696`）；L/RGB 反相都保持模式；TIFF 写入时把用户图交给 `ImageOps.invert`，再写返回值（`TiffImagePlugin.py:1666-1675`），而 mode "1" 分支先 `im.copy()` 再改（`:1668`），说明不应改动调用者的图 | 没有断言 | 缺失（并入 R-c） | — |
| R4 | L/RGB 反相仍是逐通道 `255 - v` | `ImageOps.py:525-528`；docstring | `test_1.py:67-68` 只做冒烟 | 部分 → T3 | gold 未改这条路径（静态） |
| R5 | `_lut` 的其它使用者对 L/RGB 结果不变 | `ImageOps.py:153, 237, 383, 553, 570` | colorize 三个测试有像素值断言；autocontrast 的 cutoff、mask、preserve 系列有中位数、直方图或相等断言；equalize、posterize、solarize 只做冒烟（`test_sanity`、`test_pil163`） | 部分 | 23 个回归键在 noop 和 gold 下都是 PASSED |
| R6 | 候选若改 TIFF 调用方，photometric=0 的往返仍相等 | 公开测试 `wt/Tests/test_file_tiff.py:483-490` | 不在隐藏测试里 | 缺失（只在候选改 TIFF 时相关） | 公开命令 `pytest_tiff_photometric` |
| R7 | 其它模式（P、RGBA 等）的行为 | 题面未涉及；文档说 "most operators only work on L and RGB images"（`ImageOps.rst:8-9`） | 无 | 不要求 | — |
| R8 | 非规范存储值（题面示例 `color=1`）反相后应得到什么 | 两种读法都有依据，见 §4 | 无 | **不应断言**（避免 P5） | devcheck 的 gold 对照：`repro_issue_example` |

**反向：关键断言 → 公开依据**

- `test_1.py:66`（不抛错）→ 题面的期望行为与实际行为。
- 其余断言都与公开 `wt/Tests/test_imageops.py` 逐字相同，属于已有公开测试所保护的旧行为。
- 没有找到无公开依据的断言。

## 3. R2E 专项

- **(a) 非 PASSED 键**：没有。期望映射 24 键全是 PASSED（`PRIV/expected_output.json`），不存在"更完整的修复把 FAILED 翻成 PASSED 而判 0"的风险。
  - 更完整的修复不会改动任何键：例如放宽 `_lut` 让 autocontrast、equalize、posterize、solarize 也接受 "1"，或给 P 模式实现调色板反相。没有键对 "1" 或 P 期望抛错。
  - 唯一的 `pytest.raises` 在 `test_1.py:147`，检查的是 `scale` 的 `ValueError`，与本题无关。
- **(b) 题面报错是否出现在 noop 目标键的失败原因里**：出现了。
  - 调用链：`r2e_tests/test_1.py:66` → `src/PIL/ImageOps.py:528` `invert` → `:58` `_lut` → `OSError: not supported for this image mode`（noop.log:70-93）。
  - 摘要行：`FAILED ... test_sanity - OSError: not supported for this image mode`（noop.log:119）。
  - 异常类型与消息都与题面 `user_prompt.txt:25` 一致。noop 结果是 1 failed / 23 passed，RC=1（noop.log:120-122）。
- **(c) 题面是否泄漏修法**：没有。题面没有修复代码；"indicating that this image mode is not supported" 只是正常的定位线索，不算 P1。
- **(d) 测试辅助、搬迁伪影、撞键**：
  - `test_1.py` 从 `.helper` 导入。`r2e_tests/helper.py` 是 base `Tests/helper.py` 的隐藏副本（相同），由 grader 放入，候选改不到。
  - 根目录 `conftest.py` 以插件方式加载 `Tests.helper`（`wt/conftest.py:1`），这个文件候选可以改，但隐藏测试的 `hopper` 不来自它。
  - 资产路径都相对 `/testbed`，`run_tests.sh` 就在 `/testbed` 下运行。
  - 只有一个测试文件，不会撞键。
  - 期望键带 ANSI 粗体码（`setup.cfg` 的 `addopts = -ra --color=yes`）。解析器规范化 `prime_decolor_v1`，实测 24/24 匹配。
- **(e) 时间、随机、资源敏感键**：没有。`hopper("1")` 是确定性抖动转换；测试耗时 0.2–0.44 s；`test_exif_transpose` 在 webp 可用时会多测一组，但同一镜像下结果稳定（旧机 2 次、M3 2 次一致）。
- **(f) 材料修订**：`PRIV/revisions.json` 为 `[]`，不适用。

## 4. gold 检查

- **改动**：只把 `invert` 的最后一行改为 `return image.point(lut) if image.mode == "1" else _lut(image, lut)`（`PRIV/gold.patch:10`）。
  - 没有无关改动。上游 fix 只动了 `src/PIL/ImageOps.py` 与 `Tests/test_imageops.py`（M3 ledger 第 19 行的 `gold_meta`）。
- **规范输入（0/255，例如 `hopper("1")`）**：`Image.point` 对 "1" 走 `im_point_8_8`（`wt/src/libImaging/Point.c:143-166`），逐字节查表，0 与 255 互换，输出仍是 mode "1"、新图，所以是正确反相（静态推断）。
- **题面示例（非规范值）**：
  - 存储：`Image.new("1", …, color=1)` → `core.fill` → `getink` 对单波段 8 位图只做 `CLIP8`（`wt/src/_imaging.c:527-538`），`ImagingFill` 按原字节填充（`wt/src/libImaging/Fill.c:53-57`），所以每个像素的原始字节是 1。
  - gold 把 1 变成 254。
  - 仓库各处都把非零当白：打包 `Pack.c:85-90`；转 L `Convert.c:58-61`；逻辑运算的公开测试 `wt/Tests/test_imagechops.py:408-428` 把 1、128、255 都当"开"；文档说 1-bit 像素取值范围是 0–1（`concepts.rst:28-32`）。
  - 因此示例图在 gold 后 `tobytes()` 不变、`convert("L")` 仍全为 255：**看起来没有反相**。
  - 另一方面，读法"`255 - 存储字节`"也有公开先例：L 模式的 invert 就是这样做；`ImageChops.invert` 文档写 "out = MAX - image"，对 "1" 同样得到 254（`wt/src/PIL/ImageChops.py:39-51`、`Negative.c:35-39`）。
  - 结论：两种读法都有依据，测试不断言，所以不是误拒也不是漏判。登记为 G1/P4 的 S2 注记。
  - 顺带一点：在题面示例上，gold 与退化候选 D1 按 1-bit 语义不可区分，只有原始 `getpixel` 不同（254 与 1）。所以题面示例本身不宜作为"反相正确"的验收实例。
  - 本条待 devcheck 的 gold 对照确认：`repro_issue_example` 预计打印原始值 254、`equals all-black: False`、L 极值 `(255, 255)`。
- **未测回归**：没有发现 gold 自身的回归；L/RGB 路径不变。
- **运行证据**：
  - noop：RC=1，只有 `test_sanity` 不匹配，23/24（R-f 与环境轮复跑各 1 次，同一派生镜像 `28c11ac2…`、配方 sha `0da821a1…`，日志去掉时间戳和地址后相同）。
  - gold：RC=0，24/24，投影包含 `src/PIL/ImageOps.py`（ledger 第 41 行，两次）。
  - M3 独立 runner 在来源镜像上 gold 两次 24/24。
  - 这些都是旧机器上的历史运行；新机器上的派生镜像是重建的，待协调者给出身份核对（§7）。

## 5. v1 §4 五步（暂定）

1. **核心要求有无直接断言**：核心要求是"成功反相二值图、不抛错"（`user_prompt.txt:20`）。只有"不抛错"被间接断言，反相结果没有断言 → **S1（T2a）**。
   - 即使把核心要求窄读成"不抛错"，第 3 步仍会命中。
2. **是否只用题面示例的字面值**：没有命中。测试输入是 `hopper("1")`，不是 `Image.new("1", (128, 128), 1)`。但因为没有值断言，这一步不起作用。
3. **退化探测**：D1（对 mode "1" 原样返回副本，§6）预计得 1 → **S1（T2b）**，待正式评分实跑，并核对交付与执行。
4. **已有候选**：没有真实模型候选。审查中构造的 W1（就地修改输入后返回）也会得 1，与第 3 步同一根因。gold 在非规范值上的行为属于读法分歧，不计为违例。
5. 因为第 1、3 步已命中，不走第 5 步。

## 6. 候选（写成可直接改成补丁的描述；请协调者用正式评分实跑）

所有候选都只改 `src/PIL/ImageOps.py`，在 base 上应用。

**D1：退化候选（v1 §4 第 3 步，必跑）**

- 改法：函数 `invert`，把 `return _lut(image, lut)` 改为：

  ```python
  return image.copy() if image.mode == "1" else _lut(image, lut)
  ```

- 违反的公开要求：`user_prompt.txt:20` "successfully invert the binary image"，以及 docstring `ImageOps.py:520` "Invert (negate) the image"。
- 看得出违例的输入：
  - `Image.frombytes("1", (8, 1), bytes([0xA5]))` 反相后应为 `0x5A`，D1 仍返回 `0xA5`；
  - `hopper("1")` 反相后与输入逐字节相同。
- 预期得分：**1**（24/24）。`test_sanity` 第 66 行不再抛错，其余键不受影响。
- 请核对：
  - ledger 的 `projection.included_paths=['src/PIL/ImageOps.py']`、apply 成功；
  - eval 日志里 `test_sanity` PASSED；
  - 在同一候选状态下跑公开命令 `check_mode1_invert_canonical`，应在 `assert out.tobytes() == bytes([0x5A])` 处失败。这一条证明候选确实生效，且确实违例。

**A1：合理替代解（1-bit 语义归一；当前材料可选，R-c 验收时作经独立核实的正对照）**

- 改法：函数 `invert`，在 `return _lut(image, lut)` 之前加：

  ```python
  if image.mode == "1":
      return image.point(lambda v: 0 if v else 255)
  ```

- 预期：当前材料得 1；R-c 后得 1。
- 附带观察：在题面示例上，原始值为 0，`equals all-black: True`，也就是按 1-bit 语义真的反相了。

**W1：已知错误候选（就地改坏被比较的输入；只在 R-c 保留"输入不被修改"断言时需要跑）**

- 改法：函数 `invert`，在 `return _lut(image, lut)` 之前加：

  ```python
  if image.mode == "1":
      px = image.load()
      for y in range(image.height):
          for x in range(image.width):
              px[x, y] = 0 if px[x, y] else 255
      return image
  ```

- 违例依据：调用者的图被改掉。TIFF 写入路径把用户图交给 `ImageOps.invert`，而 mode "1" 分支刻意先复制（`TiffImagePlugin.py:1666-1675`）。
- 预期：当前材料得 1；R-c 后得 0。

**A2（可选，低优先）：放宽 `_lut`**

- 改法：函数 `_lut`，把 `elif image.mode in ("L", "RGB"):` 改为 `elif image.mode in ("1", "L", "RGB"):`。
- 预期：当前材料得 1，没有任何键变化。
- 用途：只用来证实公开读者给的第一条路线不会被隐藏测试误拒。静态把握很高，结果不改变处置，可以不跑。

## 7. 请协调者提供或实跑的证据

1. **devcheck（正在跑）**：对 6 条公开命令，分别给出 noop 与私有 gold 下的退出码和关键输出，重点看：
   - `env_pil_import`：解题身份（uid 54321）下 `PIL.__file__` 和 `ImageOps.__file__` 是否在 `/testbed/src/PIL`，`core.__file__` 的路径，jpg / zlib / libtiff 是否可用，pytest 与 packaging 的版本。
   - `repro_issue_example`：noop 下应以 `OSError` 结束且退出码 1；gold 下的原始值、`equals all-black`、L 极值（用来核对 §4）。
   - `check_mode1_invert_canonical`：noop 下应为 `OSError` 且退出码 1；gold 下应打印 `OK` 且 `canonical 0/255: True`。
   - `pytest_imageops`：两种状态下都应是 24 passed。
   - 各命令的墙钟时间。
   - R2E 预检三项（解释器可执行、隐藏测试不可读、HEAD 没有子提交）。M3 facts 显示来源镜像有 6472 个后续提交，派生配方应已清除。
2. **D1 正式评分**（必需）：reward、逐键结果、交付与执行核对（见 §6）。
3. **新机器环境身份**：派生镜像 image ID 与配方 sha（对照旧机的 `28c11ac2…` / `0da821a1…`）、Docker 版本与存储后端、`RH2_SETUP_HIDDEN_TESTS_TREE` 是否仍为 `7e15b739…`。
4. **可选**：A1 在当前材料上的正式评分。W1、A1 主要放到 R-c 验收时跑。

## 8. 开发需求（逐阶段）

| 阶段 | 需求 | 依据 | 证据级别 |
| --- | --- | --- | --- |
| 准备 | 派生镜像 `rh2-r2e-derived/pillow:4bc6483564ae-r2e_derive_v1`；不需要网络，不需要额外资产 | run_refs 与 ledger | 评分侧实测（旧机）；新机身份待给出 |
| 解题：导入 | 修改 `src/PIL/ImageOps.py` 后，能在下一次导入时生效：`PIL` 从 `/testbed/src/PIL` 导入 | ledger 第 41 行 `RH2_OBS_IMPORT_PATH=/testbed/src/PIL/__init__.py`（评分用户 54322，4 次） | 评分侧实测；解题侧待 devcheck 的 `env_pil_import` |
| 解题：依赖 | `/testbed/.venv` 的 Python 3.9.21、pytest 8.3.4、packaging（helper 需要）、pytest-cov；JPEG 已编入 | noop.log:16-19；helper 导入 packaging 且测试通过；读 .jpg 的键都 PASSED | 评分侧实测；解题侧同一镜像，待 devcheck |
| 解题：资产 | `Tests/images/` 下的 hopper.ppm、imageops_pad_*.jpg、iptc.jpg、bw_gradient.png、p_16.tga 等 | 工作树文件存在 | 静态 |
| 候选安装 / 构建 | 纯 Python 修复不需要构建；评分侧 `RH2_INSTALL_SKIPPED=1`。改 C 源码要就地重编，编译条件未知，本题不需要 | gold 只改 .py；ledger `install_skipped` | 评分侧实测；C 路线未验（非必需） |
| 权限 | agent 可写 `/testbed` | `environment_brief.md:12` | 环境阶段实测（按 brief）；本题待 devcheck |
| 网络 | 各阶段都不需要；评分 `network=deny_all` | ledger `policy` | 评分侧实测 |
| 测试 | `python -m pytest Tests/test_imageops.py` 可跑到 23 个与隐藏回归键相同的测试；没有公开测试覆盖 mode "1" 反相，需要自写复现脚本（公开命令已给出） | `diff` 结果 | 静态；待 devcheck |
| 资源 | 2 CPU / 4 GiB / `/tmp` 1 GiB；评分内存峰值约 510 MB，测试约 0.7–0.8 s，评分可信准备约 24 s | ledger 的 `resource` 与 `phases` | 评分侧实测 |
| 提交边界 | 只需 `src/PIL/ImageOps.py`；投影实测包含该文件 | gold ledger | 评分侧实测 |

公开读者的命令对本题的开发验证是够的：`check_mode1_invert_canonical` 能区分正确反相与 D1 类退化，也可以作为能力比较时预登记的事后审计。

## 9. 题目关系（第 8 方面，X1）

我用 grep 逐条打开同仓公开包确认了两份跨题比对的命中。

**本题 gold 出现在更晚三题的公开初始工作树里**（逐字，行号不同）：
- `pillow__3a61c9e9…`（9.2.0），`wt/src/PIL/ImageOps.py:528`；
- `pillow__f9d3ee0f…`（9.3.0），`:528`；
- `pillow__a682ceaf…`（10.1.0），`:534`。

这三题的题面（调色板 remap、`pad()` 取整、GIF 透明度）与本题无关，但它们的初态都带着本题答案。

**本题初态包含更早几题的修复或测试**：
- `pillow__2b061b68…` 的 gold（9/9）与 `test_open_formats`；
- `pillow__2d01f7d0…` 的 gold（23/24）与 `test_photometric`。2d01f7d0 修的是 TIFF photometric，正是它加入了 `TiffImagePlugin.py:1666-1673` 对 mode "1" 的手写逐像素反相，与本题属于同一功能区；
- `pillow__3ac9396e…` 的 `test_exif_div_zero`、`test_ifd_rational_save`。

**处理**：登记关联；训练时控制重复采样；留出评测按 D3 按仓库划分，pillow 各题同组。本题题面与 gold 不重叠，不算 P1。

## 10. 问题清单与修订建议

| 编号 | 问题 | 严重度 | 证据层次 | 去向 |
| --- | --- | --- | --- | --- |
| T2（T2a；T2b 待实跑） | 核心要求"反相结果"没有断言；D1 预计得 1 | **S1** | 静态（断言阅读），加历史运行（noop/gold）；T2b 待当前 CPU | R-c（下文） |
| T3 | invert 的 L/RGB 输出值在隐藏测试中只做冒烟 | S2 | 静态 | 登记；可在同一轮 R-c 顺带补（可选） |
| G1 / P4（注记） | 题面示例为非规范值；gold 输出 254，按 1-bit 语义仍为白 | S2 | 静态（源码逐层）；待 devcheck 的 gold 对照 | 登记；不对非规范值断言 |
| X1 | 同仓跨题包含（§9） | 登记 | 静态（逐条 grep 核对） | 登记；控制重复采样 |

**R-c 建议（针对 T2，按 v1 §5）**

- **公开依据**：
  - `user_prompt.txt:20` "successfully invert the binary image"；
  - docstring `ImageOps.py:520`；
  - 1-bit 约定：`Pack.c:85`、`Convert.c:58-61`、`concepts.rst:28-32`；
  - 输入不被修改：见 §2 的 R3。
- **改动**：在 `PRIV/hidden_tests/test_1.py` 末尾新增一个函数，只用规范输入（`hopper("1")`，非题面示例），oracle 不经过 `ImageOps.invert`：

  ```python
  def test_invert_mode_1():
      im = hopper("1")  # canonical 0/255 bilevel image, not the issue's literal example
      original = im.copy()
      expected = Image.frombytes(
          "L", im.size, bytes(255 - v for v in im.convert("L").tobytes())
      )

      out = ImageOps.invert(im)

      assert out.mode == "1"
      assert out.size == im.size
      assert_image_equal(out.convert("L"), expected)
      assert_image_equal(im, original)  # input left untouched
  ```

  - 期望映射加一键：`"\u001b[1mtest_invert_mode_1\u001b[0m": "PASSED"`，沿用现有 ANSI 键形。也可以把这些断言并入 `test_sanity`，键集就不变。
  - 刻意不断言原始字节必须是 0/255，也不对题面示例的非规范值断言，以免把 gold 的读法强加给其它合理解。
  - `out.mode == "1"` 的依据较弱（推断）。复核若认为不足，删掉这一行，其余不变。
- **可选（T3）**：同一轮加一个 L/RGB 值回归：

  ```python
  def test_invert_l_rgb_values():
      for mode in ("L", "RGB"):
          im = hopper(mode)
          out = ImageOps.invert(im)
          assert out.mode == mode
          assert out.tobytes() == bytes(255 - v for v in im.tobytes())
  ```

  期望映射对应加一个 PASSED 键。
- **验收计划**：

  | 对照 | 预期 |
  | --- | --- |
  | gold（正对照） | 1 |
  | noop | 0 |
  | D1（本次要纠正的触发反例） | 0 |
  | W1（仅在保留输入不变断言时） | 0 |
  | A1（经独立核实的合理替代解） | 1 |

  还要逐键核对：键集严格相等，新键在 gold 与 A1 下都是 PASSED；保存新旧版本、理由与触发反例；Codex 复核。
- **待用户决定（可选，不建议）**：是否要求非规范存储值（题面示例 `color=1`）也按 1-bit 语义反相。这等于在两种有依据的读法中选一种，还会让 gold 失败，属于 P5，超出模板。建议不做。

## 11. 缺口与未知

- 解题侧条件都还没有当前证据：导入路径、公开命令结果、墙钟时间、R2E 预检三项。devcheck 在跑。
- D1 的正式评分还没跑，T2b 目前只是静态推断。
- 新机器的派生镜像是重建的，身份与旧机 current 行的对应关系待核对。
- 模型实际收到的消息、经 adapter 的链路、真实模型求解：都未验（清单 3、33–36）。
- "探针就绪差距"一节要求对照本批 README §3，而本次派发指令禁止读本批 README。写 `card.md` 时，请协调者提供 §3 的标准条文，或者允许我引用。目前只能按 v1 §2 的条件写。

## 附录 A：40 项 `checks` 初稿（稀疏）

| 编号 | 状态 | 依据 |
| --- | --- | --- |
| 1 | pass | blob 与 commit 对应；隐藏树 sha 与日志一致 |
| 2 | pass | noop.log:70-93 |
| 3 | unknown | 只有静态渲染 |
| 4 | pass | 投影包含 `ImageOps.py` |
| 5 | issue | X1 |
| 6 | pass（评分侧） | — |
| 7 | pass | — |
| 8 | pass（评分侧）；unknown（解题侧） | — |
| 9 | pass | 导入路径观测，以及 noop→gold 翻转 |
| 10 | unknown | 待 devcheck |
| 11 | pass | 不需要网络 |
| 13 | pass | — |
| 14 | pass（有限） | noop 与 gold 各 2 次一致，另有 M3 2 次 |
| 16 | pass | gold |
| 18 | pass | 24 收集、24 执行 |
| 19 | pass | — |
| 20 | pass | 唯一不匹配的键因目标 `OSError` 失败 |
| 23 | issue（S2） | R8 非规范值 |
| 24 | pass | — |
| 25 | issue（S1） | T2 |
| 26 | issue（S2） | T3 |
| 27 | issue（S2 注记） | G1 |
| 32 | issue | 与 25 同根：只验证"不抛错" |

其余编号 not_checked 或 not_applicable（33–40 需要真实模型或修订流程）。

## 附录 B：阅读与暴露范围

- **方法**：角色卡、八方面协议、R2E 环境卡、记录模板、40 项清单、统一标准 v1。
- **公开**：本题公开包全文件；`wt/` 中 `ImageOps.py`（1-160、160-245、345-395、495-590）、`Image.py`（new、point）、`ImageChops.py:36-52`、`TiffImagePlugin.py:1655-1685`、`_imaging.c`（getink、`_fill`、`_point`）、`Fill.c`、`Point.c:130-175`、`Negative.c`、`Pack.c:80-105`、`Convert.c` 的 1-bit 与 L↔1 片段、`Tests/test_imagechops.py:404-430`、`Tests/test_file_tiff.py:478-495`、`Tests/conftest.py`、`conftest.py`、`setup.cfg`、文档两处；公开读者产物两份。
- **同仓其它题的公开包**：只用 grep 看了 `ImageOps.invert`、`getink`、`TiffImagePlugin` 相关片段、`CHANGES.rst` 版本行和题面标题。
- **私有**：`PRIV/` 全部文件；run_refs 所列 4 个 ledger 的第 41 行、M3 ledger 第 19、68 行，以及 6 份日志（sha256 均与 run_refs 一致）；两份跨题比对中与本题有关的条目。
- **未读**：任何历史调查、审查目录、`history/`、本批 README / board / assignments、`runs/` 下其它分析文件。
