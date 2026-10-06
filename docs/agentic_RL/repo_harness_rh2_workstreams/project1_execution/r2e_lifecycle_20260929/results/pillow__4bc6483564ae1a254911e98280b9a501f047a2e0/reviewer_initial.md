# pillow `4bc64835` 独立复核初判（第一步：读主审产物之前）

2026-09-29 07:28（+08，本机时钟）· 独立复核者（Claude，干净上下文）· 单题闭环试行，按统一标准 v1。
只做静态阅读和已有原件核对：没有运行项目代码，没有开容器或远端，也没有改任何原件。下文的"预期"都是根据源码推断，不是实跑结果。

简写（都相对仓库根目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0`
- `WT` = `PUB/worktree`（解题者看到的初始 `/testbed`）
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0`

## 0. 结论先行

| 项 | 初判 | 证据级别 |
| --- | --- | --- |
| 题目目标 | 让 `ImageOps.invert` 处理 mode `"1"` 图像时不再抛 `OSError`，并且真正把图像反相 | 题面 `PUB/user_prompt.txt:3-26` |
| 严重度 | **S1**。第 1 步命中 **T2a**：唯一目标键 `test_sanity` 里与本题有关的只有一次调用 `ImageOps.invert(hopper("1"))`，没有检查结果（`PRIV/hidden_tests/test_1.py:66`）。第 3 步的退化候选 W1（mode "1" 时直接返回副本）按源码推断会得 1，即 **T2b**，还要正式评分确认 | 静态阅读 + 当前材料运行原件 |
| gold 自身的疑点（G1，条件项） | 题面原例 `Image.new("1", (128, 128), color=1)` 的内部像素值是 1。gold 用 `image.point(lut)` 把 1 映射成 254，而 Pillow 打包、保存和转换成 L 时都把非零值当白色。所以按源码推断，**gold 对题面原例的输出与输入看起来完全相同，并没有反相**。公开文档写明 "a 1-bit pixel has a range of 0-1"（`WT/docs/handbook/concepts.rst:28-29`），因此按 v1 第 4 步可能再命中一次 S1。但这要先做一次 CPU 核实，并统一"值 1 是否必须按白色处理"的口径 | 静态推断（base C 源码，推理链见附录 B），未实跑 |
| 误拒 | 当前材料里没有发现。24 个键的期望都是 PASSED，没有精确文案、mock 或内部名断言；按源码推断，三种不同于 gold 的合理实现（§7 A1–A3）都应得 1 | 静态推断 |
| 回归与 gold 完整性 | gold 只给 mode "1" 加了一个分支，其它模式的路径不变。但评分对 `invert` 在 L/RGB 下的输出也没有断言（T3） | 静态 |
| 材料一致性 | 一致。隐藏测试就是公开的 `Tests/test_imageops.py` 加 1 行；`helper.py` 与公开版逐字相同；各文件的 sha256 与 grading bundle 一致；4 条 current 运行用的是同一张派生镜像 | 原件核对 |
| 题目关系（X1） | 本题 gold 那一行逐字出现在同仓 3 道题（`3a61c9e9`、`f9d3ee0f`、`a682ceaf`）的公开初始工作树里。反过来，本题的初态里已经有 `2d01f7d0`（TIFF 保存 "1"/"L" 的反相）、`2b061b68`、`3ac9396e` 的修复或测试 | grep 核对 + 机械扫描 |
| 用途（v1） | 问题定位 yes；能力比较 conditional；训练候选 no（S1 未处理）；留出评测候选 no | 见 §9 |
| 唯一最值得先做的下一步 | 用正式评分跑 §6 的退化候选 W1（预期得 1）。同一轮里，在派生镜像中应用 gold 后跑一次题面原例（预期：`getpixel` 从 1 变成 254，两者 `tobytes()` 相同） | — |

## 1. 材料与运行原件核对

**文件一致性**（本机 `shasum -a 256` 结果，与 bundle 字段逐项对上）：
- 隐藏测试 `__init__.py` / `helper.py` / `test_1.py` 的哈希分别是 `e3b0c442…` / `d462a905…` / `016c2b06…`，与 `PRIV/grading_bundle.json:9-22` 一致。
- `expected_output.json` 的哈希 `d8bc5a2b…` 与 bundle 的 `expected_output_json_sha256` 一致。
- `gold.patch` 的哈希 `9b5c56bc…` 与 `PRIV/validation_bundle.json:7`、账本里的 `candidate.patch_sha256` 一致。
- `run_tests.sh` 的哈希 `8285765f…` 与 bundle、日志里的 `RH2_SETUP_ENTRY_SHA256` 一致。
- 隐藏测试与公开测试的差异：`WT/Tests/test_imageops.py` 与 `PRIV/hidden_tests/test_1.py` 对比，只多了一行 `ImageOps.invert(hopper("1"))`（隐藏文件 :66）。`hidden_tests/helper.py` 与 `WT/Tests/helper.py` 逐字相同。
- `PRIV/revisions.json` 是 `[]`；`PRIV/run_refs.json:3-9` 显示当前材料没有修订、环境配方和资源配方。
- 镜像初态：`PUB/worktree_manifest.json` 里 `initial_diff` 是 0 字节，即初态与 base 没有差异。未跟踪文件有 `install.sh`（未导出）和 `run_tests.sh`（已导出）。

**current 运行（共 4 条）。** 都用派生镜像 `rh2-r2e-derived/pillow:4bc6483564ae-r2e_derive_v1`（image ID `sha256:28c11ac277e6…`），recipe `r2e_derive_v1`（`0da821a1…`）。评分用户 54322，2 CPU / 4 GiB，断网。账本里 `RH2_OBS_IMPORT_PATH=/testbed/src/PIL/__init__.py`，`RH2_OBS_PKG_VERSION=9.1.0.dev0`。

| 运行 | 账本行 | 结果 | 日志要点 |
| --- | --- | --- | --- |
| R-f 全池 noop（09-23） | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:41` | reward 0，23/24，只有 `test_sanity` 不符，无 missing / unexpected | `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_8c5689aa.eval.log:70-93,119`：`r2e_tests/test_1.py:66` → `src/PIL/ImageOps.py:528 in invert` → `:58` 抛出 `OSError: not supported for this image mode` |
| R-f 全池 gold | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:41` | reward 1，24/24；`projection.included_paths` 只有 `src/PIL/ImageOps.py` | `…/evallog_replay-r2e-rf-all-gold-p_48c7d1b3.eval.log:27-51`，24 passed |
| 环境轮复跑 noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:41` | 结果同上 | 去掉时间和内存地址后，与 R-f 的 noop 日志逐行相同 |
| 环境轮复跑 gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:41` | reward 1，24/24 | 去掉时间后与 R-f 的 gold 日志逐行相同 |

- 由此确定**目标键只有 `test_sanity`**（noop 为 FAILED，gold 为 PASSED），另外 23 个键在 noop 和 gold 下都是 PASSED，属于回归键。
- 本题没有修订，所以标为"来源版材料"的 R-f 行就是当前材料。
- 独立参考：M3 在来源镜像上两次跑 gold（`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:19,68`），都是 24/24，两份日志去掉时间后相同。这只作对照。
- 测试阶段约 0.7–0.8 s，内存峰值约 510 MB。

## 2. 需求—断言双向表

| 公开要求或合理旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 运行证据或下一步 |
| --- | --- | --- | --- | --- |
| R1：`invert` 处理 mode "1" 时不抛错 | 题面标题和 Expected Behavior | `test_sanity` :66 只是调用，抛异常才算失败。输入是 `hopper("1")`（抖动后的照片），不是题面里的字面值 | 覆盖（隐式） | noop 抛 `OSError` 而 FAILED，gold PASSED |
| R2：mode "1" 图像真的被反相（黑白互换） | Expected Behavior "should successfully invert the binary image"；docstring "Invert (negate) the image"（`WT/src/PIL/ImageOps.py:518-524`）；仓库里现成的 "1" 反相逻辑（`WT/src/PIL/TiffImagePlugin.py:1666-1673`）；`ImageChops.invert` 的 "out = MAX - image"（`WT/src/PIL/ImageChops.py:39-51`） | 无 | **缺失** | §6 的 W1 |
| R3：结果仍是 mode "1"，尺寸不变 | "invert the binary image"；L/RGB 路径经过 `point` 本来就保持模式 | 无 | 缺失 | R-c#1（这条依据较弱，见 §8） |
| R4：题面原例（值 1 表示白色）反相后变成黑色 | 题面示例；文档写 1-bit 范围是 0–1 | 无 | 缺失，且 gold 疑似不满足 | 附录 B，需 CPU 核实 |
| O1：`invert` 对 L/RGB 的行为不变 | 既有文档和实现 | `test_sanity` :67-68 只调用、不检查结果 | 部分（只防抛错） | T3 |
| O2：`_lut` 其它 5 个调用者（autocontrast、colorize、equalize、posterize、solarize）在 L/RGB 下的行为 | 既有实现（`WT/src/PIL/ImageOps.py:153,237,383,553,570`） | autocontrast 和 colorize 系列有像素或直方图断言（`test_1.py:187-307, 370-475`）；equalize、posterize、solarize 只调用 | 部分 | 改动 `_lut` 本体时，L/RGB 路径有间接保护 |
| O3：其它模式（P、RGBA 等）继续报错 | 既有实现 | 无 | 未测 | 题面没有要求，不作要求 |

反查：23 个回归键全部来自公开的 `Tests/test_imageops.py`，都有公开的旧行为作依据；唯一的新增行（:66）对应 R1。没有发现缺少公开依据的断言。

## 3. 八方面（看了什么、结论、没查什么）

1. **公开需求（3、23）。** 读了题面、`invert` 的 docstring、公开文档对模式的说明，以及 TIFF 插件里现成的 "1" 反相代码。
   - 题面要求两件事：不抛错，并且成功反相。
   - 题面没有规定：输出模式（合理推断是 "1"）、怎样处理非规范的像素值、posterize / solarize 是否也要支持 "1"（没有要求）。
   - 按文档，题面示例里的 `color=1` 是白色。
2. **材料与初始问题（1、2、27）。** base 是 `a6efaa1ae1d0`。在 base 上，原例一定走进 `_lut` 的 else 分支而抛错（`WT/src/PIL/ImageOps.py:49-58, 528`），这与 noop 日志一致。材料一致性见 §1，没有发现错配。
3. **测试是否测到要求（18–20、25、32）。** 目标键 `test_sanity`（`test_1.py:23-80`）逐行读过，与本题相关的只有 :66 这一次调用，没有检查结果，所以 R2 缺失（T2a）。另外 23 个键是同文件的回归键，重点读了与 `_lut` 相关的那几个。
4. **误拒（24、28）。** 没有精确字符串、mock、内部 helper 或执行顺序断言，期望全是 PASSED。按源码推断，A1–A3 都能得 1。没有发现误拒。
5. **回归与 gold（26、27）。**
   - gold 只有 1 行：mode 为 "1" 时改走 `image.point(lut)`，`_lut` 本体和其它调用者都不变。
   - 评分对 `invert` 在 L/RGB 下的输出没有断言，这是 T3。
   - 对规范值（0 和 255）的 "1" 图像，gold 是正确的；对题面原例（值 1），gold 疑似没有反相（G1，见 §5 第 4 步和附录 B）。
6. **开发条件（6–15）。**
   - 修复是纯 Python，不需要编译：导入路径是 `/testbed/src/PIL`。
   - 环境说明写的条件：`.venv` 下 Python 3.9.21，没有 pip，不能联网，uid 54321 可写 `/testbed`（`PUB/environment_brief.md:10-12`）。
   - 公开的 `Tests/test_imageops.py` 可以运行，但里面没有 "1" 的用例，复现要靠题面示例。
   - 公开的 `run_tests.sh` 指向 `r2e_tests`，而解题侧没有这个目录，照跑只会报找不到路径，不影响解题。
   - 本步没有拿到 devcheck 证据，所以解题侧记为"actor 待验"。
7. **交付与评分边界（4、16–17、21–22、29–31）。**
   - 修改的文件 `src/PIL/ImageOps.py` 能被投影出去（见 gold 账本的 `projection`）。
   - 评分只替换 `r2e_tests/`。根目录的 `conftest.py:1` 用 `pytest_plugins = ["Tests.helper"]` 把公开的 `Tests/helper.py` 当插件加载，`setup.cfg` 是 pytest 的配置文件；这两个文件候选都能改，评分时也不会重置。这是 pillow R2E 共用链路的性质（账本里已有 `candidate_touched_conftest_or_fixture` 字段记录这类改动），不是本题特有的问题；公开提示也禁止改测试文件。
   - 可见资产里没有答案。
8. **题目关系与用途（5、29–30、37–40）。**
   - X1 关系见 §0。
   - 本题与 `2d01f7d0` 同一主题：那道题的修复在 TIFF 保存时手写了一个 "1" 反相循环（`WT/src/PIL/TiffImagePlugin.py:1666-1673`）。本题修复之后，上游仍保留这个循环（`3a61c9e9`、`f9d3ee0f` 的同一位置）。
   - 题面没有给出修法代码（不属于 P1）。按报错文案 grep 就能定位到 `_lut`，修复只有 1 行，难度低。

## 4. R2E 专项

- **(a) 非 PASSED 的期望键：** 没有，24 个键全是 PASSED，不存在"更完整的修复把 FAILED 键翻成 PASSED 反被判 0"的风险。修复也不影响参数化或收集结果。
- **(b) 题面报错是否出现在 noop 目标键里：** 是。`test_sanity` 失败的原因就是 `OSError: not supported for this image mode`，位置在 `ImageOps.py:528 → :58`（noop 日志 :70-93、:119），与题面逐字一致。
- **(c) 题面是否泄漏修法：** 没有，题面不含实现代码。只是报错文案能直接定位到 `_lut`。
- **(d) 测试支撑、搬迁伪影与撞键：**
  - `from .helper import …` 用的是隐藏测试自带的 helper（与公开 base 版逐字相同，评分方控制）。
  - 根 `conftest.py` 另外把公开的 `Tests/helper.py` 作为插件加载（候选可改，属共用问题，见 §3 第 7 条）。
  - 测试用相对路径 `Tests/images/...` 读图，28 个图片文件（14 个固定文件，加上 hopper_orientation_2–8 的 jpg 和 webp 共 14 个）都在 `WT` 里。
  - 只有一个测试文件，没有跨文件撞键。
- **(e) 时间、随机或资源敏感的键：** 没有。`test_exif_transpose` 会按 `features.check("webp")` 分支，但同一镜像里结果是确定的，noop 和 gold 下都 PASSED。
- **(f) 材料修订：** 没有（`revisions.json` 为 `[]`），不适用。

## 5. v1 严重度五步

1. **核心要求有没有直接断言？** "不抛错"有隐式覆盖，"成功反相"没有任何断言，因此**命中 T2a，定为 S1**。
2. **核心断言是否只用题面示例的字面值？** 没有命中：唯一一次调用用的是 `hopper("1")`，不是题面的 `Image.new("1", (128, 128), color=1)`。不过这里本来就没有检查结果的断言，这一步意义不大。
3. **退化探测：** W1（§6）按源码推断会得 1，即 **T2b**。它是否命中，要由协调者正式评分确认，并核对补丁确实交付、`test_sanity` 确实执行。
4. **已有候选：** 目前没有真实模型的候选，只有 gold。gold 对题面原例（内部值 1，按文档是白色）很可能输出 254，看起来仍是白色。如果 CPU 核实成立、并且大家接受"值 1 是题面原例、必须按白色处理"这个口径，那就是"得 1 的候选在同一核心要求的另一个实例上违反公开要求"，按严格版 D1 属于 S1。反方依据：仓库自己的 TIFF 反相循环（`TiffImagePlugin.py:1672`：`0 if px == 255 else 255`）也把值 1 变成 255，仍是白色，说明上游代码本身没有处理这种值，这一点存在读法争议。因此**第 4 步记为 conditional**。
5. 不适用：前面已经命中。

结论：**S1**。第 1 步已由静态阅读确定，第 3 步待跑，第 4 步 conditional。另有 T3（L/RGB 的输出没有断言），登记即可。

## 6. 退化候选 W1（可直接改成补丁）

- **文件与函数：** `src/PIL/ImageOps.py` 中的 `invert`（base :518-528），改动位置就是 gold 改的那一行。
- **改法：**

```diff
--- a/src/PIL/ImageOps.py
+++ b/src/PIL/ImageOps.py
@@ -525,7 +525,9 @@ def invert(image):
     lut = []
     for i in range(256):
         lut.append(255 - i)
-    return _lut(image, lut)
+    if image.mode == "1":
+        return image.copy()
+    return _lut(image, lut)
```

- **违反哪条公开要求：** 题面 Expected Behavior "should successfully invert the binary image"。W1 不抛错，但返回的图与输入完全相同，属于"抑制症状 / 与输入无关的固定结果"这一类。
- **用什么输入能看出来：** `im = hopper("1")` 或 `Image.new("1", (4, 4), 255)`。W1 下 `ImageOps.invert(im).tobytes() == im.tobytes()` 为 True；正确的修复会让每一位都翻转。
- **预期正式得分：** 1。`test_sanity` 在 :66 只是调用，不会失败；另外 23 个键与 `invert` 的 mode "1" 分支无关，所以是 24/24。
- **协调者要核对：** 投影后的 `included_paths` 里有 `src/PIL/ImageOps.py`，日志里有 `PASSED … test_sanity`。

## 7. 用于区分结论的候选（协调者按需实跑）

| 候选 | 改法（`src/PIL/ImageOps.py`） | 现材料预期 | 加 R-c#1 后预期 | 再加 R-c#2 后预期 |
| --- | --- | --- | --- | --- |
| A1 合理替代 | 在 `_lut` 里把 `elif image.mode in ("L", "RGB"):` 改成 `("1", "L", "RGB")`，`invert` 不动 | 1 | 1 | 0（与 gold 一样得到 254） |
| A2 合理替代（对任意取值都正确） | 在 `invert` 里：`if image.mode == "1": return image.point(lambda v: 0 if v else 255)` | 1 | 1 | 1 |
| A3 合理替代 | 在 `invert` 里：`if image.mode == "1": return _lut(image.convert("L"), lut).convert("1")`（输入只有 0/255 时，抖动不改变结果） | 1 | 1 | 1 |
| W2 部分实现 | `return _lut(image.convert("L"), lut) if image.mode == "1" else _lut(image, lut)`，返回的是 mode "L" | 1 | 0（被模式断言拒绝） | 0 |
| W3 固定结果 | mode 为 "1" 时 `return Image.new("1", image.size)` | 1 | 0 | 0 |

`ImageChops.invert` 这条路线（按位取反，~1 = 254）的预期与 A1 相同。

## 8. 修订建议

### R-c#1（在模板内，建议执行）

- **公开依据：** 题面 Expected Behavior、`invert` 的 docstring、仓库现成的 "1" 反相语义（TIFF 插件，黑白互换）。
- **改动：** 在 `PRIV/hidden_tests/test_1.py` 的 `test_sanity` 之后（:80 之后）新增下面这个函数，并在 `expected_output.json` 里加一个键 `"\u001b[1mtest_invert_mode_1\u001b[0m": "PASSED"`（沿用现有键的格式）。这里选择新增函数而不是把断言塞进 `test_sanity`，是为了让失败原因可读，代价是要同步改 expected。

```python
def test_invert_mode_1():
    # non-example instance: dithered hopper with mixed black and white pixels
    im = hopper("1")
    before = list(im.convert("L").getdata())
    assert 0 in before and 255 in before

    out = ImageOps.invert(im)
    assert out.mode == "1"
    assert out.size == im.size
    assert list(out.convert("L").getdata()) == [255 - v for v in before]

    # solid images with canonical values: white -> black, black -> white
    assert ImageOps.invert(Image.new("1", (16, 16), 255)).convert("L").getextrema() == (0, 0)
    assert ImageOps.invert(Image.new("1", (16, 16), 0)).convert("L").getextrema() == (255, 255)
```

- **说明：**
  - 比较都在 `convert("L")` 之后做，所以只看黑白语义、不看内部存的是 1 还是 255；内部用 0/1 存储的实现也能通过。
  - 输入是非题面实例，满足第 2 步的要求。
  - `out.mode == "1"` 这条的依据相对弱。如果协调者或 Codex 认为依据不足，可以只删这一行，其余断言不受影响。
- **验收：**
  - gold 得 1（按源码推断：两类输入都只含 0/255）；noop 得 0（`test_sanity` 和新键都因 `OSError` 而 FAILED）。
  - W1、W2、W3 都得 0。
  - A1 得 1，作为独立的替代正对照。
  - 保存新版本、父版本、理由和触发反例（W1），交 Codex 复核。
  - 修订后仍受保护的公开要求：R1、R2，以及对规范值的 R3。
- **可选的顺带补充（T3，同一处改动的受影响范围）：** 在同一个函数里加 `assert ImageOps.invert(hopper("L")).tobytes() == hopper("L").point(lambda v: 255 - v).tobytes()`，保护 L 路径的输出。依据是既有的文档化行为；它不属于核心要求，可以不做。

### R-c#2（条件项，不阻塞 R-c#1）

- **前提：** 先用一次性 CPU 核实确认附录 B 的推断，即 gold 应用于题面原例后得到 254，而且 `tobytes()` 与输入相同。
- **改动：** 新增一个函数，对应的 expected 键记为 PASSED：

```python
def test_invert_mode_1_issue_example():
    # the issue's example; for a 1-bit image, color=1 is white (docs: range 0-1)
    im = Image.new("1", (128, 128), color=1)
    assert im.convert("L").getextrema() == (255, 255)
    out = ImageOps.invert(im)
    assert out.mode == "1"
    assert out.convert("L").getextrema() == (0, 0)
```

- **后果：**
  - gold、A1 和 `ImageChops.invert` 路线都会得 0。
  - 按 v1 D4，正对照要改用经过独立核实的 A2 或 A3，并记录原 gold 的失败；修订后的题只能作"标明版本的自建题"。
- **需要决定的点：** 公开依据有两条，即文档写明 1-bit 的范围是 0–1，以及这正是题面自己的原例。但仓库自身代码对值 1 的处理也不一致，接近两种读法（字节取反，还是黑白互换）。
  - 建议按 v1 §4 的分歧处理：由主审和 Codex 各做一次聚焦复核。
  - 如果不能收敛，就暂挂为 conditional，登记为已知缺口，并在探针后检里对得 1 的补丁补跑一次题面原例。
  - 这件事不必上报用户，除非有人主张把它当作任务目标选择（P5）来处理。

### 不建议的修订

- R-f：题面对 base 行为的陈述是对的（原例在 base 上确实抛 `OSError`），也没有泄漏答案，所以不需要改题面。
- R-a / R-b / R-e：不适用。

## 9. 用途结论（v1 四项，复核者独立意见）

- `problem_localization`：**yes**。
- `capability_comparison`：**conditional**。还差两件事：
  1. 解题侧的 devcheck 执行证据（真实 Claude Code 加桩端点、公开命令、私有 gold 对照），本步没有提供；
  2. R-c#1 落地之前，得 1 的补丁需要预先登记事后审计：对 `hopper("1")` 和规范值的纯色图各跑一次反相核对，题面原例单独记录。
- `training_candidate`：**no**（当前材料）。原因是 S1 未处理（T2a 已确定，T2b 待跑）。R-c#1 验收并经 Codex 复核后可以重评；届时还要登记 T3、G1 / R-c#2 的结论和 X1 关系。
- `heldout_candidate`：**no**。除上面的原因外还有 X1：本题 gold 已在 3 道同仓题的初态里，按 D3 按仓库划分时 pillow 整仓会在同一侧；修订后也只能作"标明版本的自建评测"。
- `intended_use`：`development_diagnostic`。

## 10. 探针就绪差距

按协调者的指示，本批 README 我没有读，所以下表不是对照 README §3 逐条写的，而是按 v1 §2 和两张角色卡的要求列出；请协调者把它映射到 README §3 的条目上。

| 条件 | 状态 | 由谁补 |
| --- | --- | --- |
| 当前材料下 gold 为 1、noop 为 0（同一版本，各至少两次） | 已满足（§1 的 4 条 current 运行，同一派生镜像） | — |
| 核心要求有决定性断言 | 未满足（R2、R3 没有断言） | 协调者按 R-c#1 实施并实测，Codex 复核 |
| 第 2 步：用非示例实例 | 现有调用已是非示例输入；R-c#1 继续用非示例输入 | 协调者 |
| 第 3 步：退化探测 | 还没做 | 协调者用正式评分跑 W1 |
| 第 4 步：gold 对题面原例 | 疑点待核实 | 协调者做一次性 CPU 核实；口径由主审、复核和 Codex 聚焦复核决定 |
| 解题侧开发路径 | actor 待验（本步没有 devcheck 证据） | 协调者跑 devcheck |
| X1 关系登记 | 本文已列出 | 主审写进 card 和 screening_record |
| 修订版的正负对照与 Codex 复核 | 未开始 | 协调者 + Codex |

## 11. 未查与未知

- 没有实跑任何代码。附录 B 的推理链和 W1 的预期都是源码推断。
- 没有读 40 项清单：它不在给我的方法文档列表里。八方面的编号取自八方面协议里的表格。
- 没有 devcheck 证据：解题侧的实际导入路径和 pytest 行为都是"actor 待验"。
- 没有核 `install.sh`（未导出）；也没有核派生镜像里的 `.so` 是否由 base 源码编译，只以账本版本号 `9.1.0.dev0` 与 base 一致作为旁证。
- 23 个回归键只核了与 `_lut` / `invert` 有调用关系的那几个；其余键与本题的改动没有调用关系，没有逐条评语。
- "他题 gold 包含在本题初态里"这个方向，因为他题的私有 gold 不能读，没有逐字核对，只靠机械扫描，加上本题初态里的测试名（如 `Tests/test_file_tiff.py:484 test_photometric`、`Tests/test_file_tiff_metadata.py:244 test_exif_div_zero`）和 `2d01f7d0` 的题面标题作旁证。

## 附录 A：实际读取范围

- **角色与方法：**
  - 复核卡全文。
  - 主审卡：Read 工具一次读入了全文（53 行），口径只采用指定的四节（评分口径、材料、第二批补充规则、单题闭环试行补充）。读入时也看到了页首说明、"对每题按顺序完成"和"边界"两节，都是通用流程文字，不含任何题目结论。
  - 八方面协议、R2E 环境卡、记录模板、统一标准 v1，均为全文。
- **PUB：**
  - `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（结构、export、initial_diff、未跟踪项）、`worktree/run_tests.sh`。
  - `worktree/` 下的源码：`src/PIL/ImageOps.py`（:1-80、:490-580，以及 `_lut` 调用点的 grep）、`src/PIL/Image.py`（`point` :1679-1723，`new` :2749-2785）、`src/PIL/ImageChops.py:39-51`、`src/PIL/TiffImagePlugin.py:1655-1690`、`src/_imaging.c`（`getink` :486-546、`_fill` :604-634、`_point` :1375-1450）、`src/libImaging/` 下的 `Fill.c:23-63`、`Access.c:85-88,151-153,199`、`Point.c:29-40,131-202`、`Pack.c:83-102,546`、`Convert.c:58-72,875,1481-1487,1512-1518`、`Negative.c:22-42`、`Storage.c:66-69,218-230`。
  - `worktree/` 下的测试与文档：`conftest.py`、`Tests/conftest.py:1-31`、`Tests/test_imagechops.py:190-205`；`Tests/test_imageops.py` 与 `Tests/helper.py` 只做了与隐藏版的 diff；`docs/handbook/concepts.rst:18-40`；`docs/reference/ImageOps.rst`、`ImageChops.rst`、`CHANGES.rst` 只做了 grep；另外对测试和源码 grep 过 `invert(`、报错文案，并核对了 28 个测试图片是否存在。
- **PRIV：** 全部文件，即 `gold.patch`、`expected_output.json`、`revisions.json`、`run_tests.sh`、`validation_bundle.json`、`grading_bundle.json`、`run_refs.json`、`hidden_tests/`（`__init__.py`、`helper.py`、`test_1.py` 全文）。
- **运行原件：**
  - 4 条 current 账本的第 41 行（全字段）和对应的 4 份 `.eval.log`（全文，或做了去噪后的 diff）。
  - M3 参考账本 `r2e_gold_m3.jsonl` 的 :19、:68 行，a1 日志全文，a2 只与 a1 做了 diff。
- **跨题材料：**
  - 两份扫描文件 `runs/r2e_static_prep_20260924/cross_task_gold_scan.json`、`cross_task_test_scan.json`（method 字段与涉及本题的条目）。
  - 同仓 7 道题公开包的 `public_bundle.json`（base_commit）和 `_version.py`；`3a61c9e9`、`f9d3ee0f`、`a682ceaf` 的 `src/PIL/ImageOps.py`（grep gold 行，分别在 :528、:528、:534）；`3a61c9e9`、`f9d3ee0f` 的 `TiffImagePlugin.py`（同一段）；`a682ceaf` 的 `_imaging.c`、`Image.new` 和 `concepts.rst` 的 grep；`2b061b68`、`2d01f7d0`、`3ac9396e` 的 `user_prompt.txt` 开头 300 字节。
- **没有读：** `OUTPUT_DIR` 里的其它文件、任何 `history/`、各审查目录、本批 README / `board.json` / `assignments.json`、`runs/` 下的分析与汇总（上面明确给出的路径除外）、他题私有包、devcheck 目录（未提供）、40 项清单。

## 附录 B：gold 对题面原例的推理链（静态推断，待 CPU 核实）

1. `Image.new("1", (128, 128), color=1)`：颜色既不是字符串，模式也不是 "P"，所以直接调用 `core.fill("1", size, 1)`（`WT/src/PIL/Image.py:2771-2785`）。
2. `_fill` 调用 `getink`（`WT/src/_imaging.c:604-634`）。对单波段 UINT8 图像执行 `ink[0] = (char)CLIP8(r)`，得到 1（`:537`）。
3. `ImagingFill`：mode "1" 的 pixelsize 是 1，所以 `image32` 为空（`Storage.c:66-69, 221-229`），于是每行都 `memset` 为 1（`Fill.c:43-57`）。结果是内部像素值全为 1。
4. gold 调用 `image.point(lut)`，依次经过 `Image.py:1719-1723`、`_imaging.c:1413-1450`（256 项查找表），最后在 `Point.c:29-40` 执行 `out[x] = table[in[x]]`。其中 `table[1] = 255 - 1 = 254`。
5. 解释这个 254：`pack1` 只要值非零就置位（`Pack.c:83-102`，`tobytes()` 和保存都走这里）；`bit2l` 只要值非零就给 255（`Convert.c:58-61`）。所以原图和 gold 输出的 `tobytes()` 相同，`convert("L")` 后都是全 255。按位取反的路线结果一样：`Negative.c:37` 的 `~1` 也等于 254。
6. 对照测试输入：`hopper("1")` 由 RGB 转换得到，只含 0 和 255（`Convert.c:1484/1515`：`(l > 128) ? 255 : 0`），所以 gold 对测试输入是正确的；问题只出在题面原例这种内部值为 1 的图像上。
7. 上游后来没有改这一点：`a682ceaf`（10.1.0.dev0）的 `getink` 仍是 `CLIP8(r)`（`_imaging.c:540`），`invert` 仍是 gold 那一行（`ImageOps.py:534`），文档仍写 1-bit 的范围是 0–1。
8. 一次性核实命令（在派生镜像中应用 gold 后执行，以 root 或 agent 身份均可；只是事实核对，不是评分）：

```python
from PIL import Image, ImageOps
im = Image.new("1", (128, 128), color=1)
out = ImageOps.invert(im)
print(im.getpixel((0, 0)), out.getpixel((0, 0)), im.tobytes() == out.tobytes(), out.convert("L").getextrema())
```

   预期输出 `1 254 True (255, 255)`。如果实际输出是 `1 0 False (0, 0)`，就推翻本附录的推断，§5 第 4 步和 R-c#2 随之撤销。
