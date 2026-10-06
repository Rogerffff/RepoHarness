# pillow 2d01f7d0：R-c 修订方案（合并版四项：默认值与显式 1、压缩路径、保存前快照、存储字节）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 四项合并为一轮修订，全部并入已有目标测试 `test_photometric`，不新增键，期望映射不变。试跑验收 8 个候选全部与预期一致（用的是试跑工具，不是正式评分）。不需要用户决定。** 下一步由协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。R-a、R-f 本轮不做。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`，`W` = `PUB/worktree`，`UP` = `PUB/user_prompt.txt`，`TIP` = `W/src/PIL/TiffImagePlugin.py`（base 版）。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，734 行）；`HT'` = 修订后的 `test_1.py`（773 行）；`HLP` = `PRIV/hidden_tests/helper.py`。
- `INV` = `runs/r2e_lifecycle_20260929/inv/pillow_2d01/`；`DC` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。四处修改各对应一个 S1 触发反例，依据逐项写在 §2，合并在同一轮、同一个目标测试里完成。R-c1、R-c2 来自主审（`analysis_before_history.md` 附录 B），R-c3、R-c4 来自复核补充（`review.md` §5）。

| 项 | 要纠正的 S1 | 触发反例（当前材料，正式评分） | 出处 |
| --- | --- | --- | --- |
| R-c1 默认值与显式 262=1 | T2b（第 3 步）：隐藏测试从不检查"不给 262"或"显式给 1"时仍写 1 | D（`'1'`/`'L'` 一律写 262=0 并反相）得 1.0，62/62（`INV/ledger_D.jsonl:1`）。私有对照里 D 把默认值和显式 1 都写成 0（`INV/pcheck_default_photometric_kept_D.json`、`INV/pcheck_explicit1_D.json`） | `card.md` §4；`review.md` §2 |
| R-c2 压缩（libtiff）保存 | 第 4 步 S1：隐藏测试里没有一处走 libtiff 写出路径 | C3（gold 去掉 `encoderconfig` 提升）得 1.0（`INV/ledger_C3.jsonl:1`）。私有对照里两种压缩保存都抛 `AttributeError: encoderconfig`（`INV/pcheck_compressed_path_observe_C3.json`、`INV/pcheck_g4_whiteiszero_roundtrip_C3.json`） | `card.md` §4；`review.md` §2 |
| R-c3 保存前快照 | T2b（第 3 步，"就地改坏被比较的输入"）：原断言 `HT:457` 拿**保存之后**的 `im` 作参照 | A（写未反相的数据并标 0，写完把调用者的图像原地反相）得 1.0（`INV/ledger_revA.jsonl:1`） | `review.md` §0、§4 |
| R-c4 存储字节 | 第 4 步 S1：写入端只借读取端来验证，而读取端候选也能改 | B（只保留标签，同时把读取端的 WhiteIsZero 解包改成不反相）得 1.0（`INV/ledger_revB.jsonl:1`） | `review.md` §0、§4 |

另有已知错误候选 C2（只改标签、不反相像素）：当前材料得 0.0（60/62，`INV/ledger_C2.jsonl:1`），修订后必须仍为 0。

**本轮不做：**
- **R-a**：两个期望 FAILED 的死键（T5：pytest 8.3.4 不接受 `pytest.warns(None)`）照旧。它们在任何 PIL 调用之前失败，源码改动翻不动（`analysis_before_history.md` §3.3、`review.md` §2）。
- **R-f**：像素语义按 P4 登记。它可以从公开材料推出，依据与 §2 R-c4 相同，所以不改题面。

## 2. 公开依据

### R-c1：不给 262 时默认仍写 1；显式给 1 时写 1

- **题面范围**：题面只针对"已指定 0"的情形（`UP:7`），没有要求改默认值。"retain the specified photometric interpretation"（`UP:7`）和 "accurately reflecting the specified photometric interpretation"（`UP:26`）是一般表述，显式指定 1 同样适用。
- **默认值来源**：`SAVE_INFO` 里 `'1'`、`'L'` 的 photometric 都是 1（`TIP:1459-1460`）。公开测试注释也写明 "PhotometricInterpretation is set from SAVE_INFO"（`W/Tests/test_file_libtiff.py:151-152`）。
- **独立佐证**：没看隐藏测试的公开读者也把"`tiffinfo` 里没有 262 时，`'1'`、`'L'` 仍写 1"列为可合理推知的要求 R3（`public_read.md:22`），并写了同样的自检命令 `default_photometric_kept`（`public_read.md:117-123`）。
- **这是回归断言**：base 在这两个输入上本来就写 1（`TIP:1571` 无条件写 `photo`），不扩大需求。默认情形用最常见的调用 `im.save(filename)`，与 `tiffinfo={}` 走同一行（`TIP:1508`）。

### R-c2：压缩（libtiff）保存同样保留 0，且往返不变

- **题面与文档**：题面没有限定压缩方式；`compression` 是有文档的 TIFF 保存选项（`W/docs/handbook/image-file-formats.rst:906-912`，"valid only with libtiff installed"）。
- **两条路径受同一行影响**：覆盖 262 的 `TIP:1571` 在写出路径分叉之前（libtiff 分支 `TIP:1607`，未压缩分支 `TIP:1710`），bug 与修复都同时作用于两条路径。公开读者同样推出"压缩与未压缩保存应当一致"（R4，`public_read.md:23`、`:45`）。
- **为什么选这两个实例**：
  - `'1'` 配 `group4`、`'L'` 配 `tiff_lzw`，都是无损压缩，往返应逐字节不变。
  - WhiteIsZero 的 G4 是二值传真图的通行形态：公开测试图 `hopper_g4.tif`、`hopper_g4_500.tif`、`g4-fillorder-test.tif` 都是 262=0、259=4（本轮用 `struct` 读了文件头，只读字节，没有运行项目代码）。
- **前提**：派生镜像要带 libtiff。当前镜像为 `libtiff True 4.3.0`（`DC/orig/captures/env_import.out`），解题侧也能自测这条路径。

### R-c3：保存不修改被保存的图像；往返比较以保存前的快照为参照

- **原断言的本意**：`HT:457` 想检查"重开的图等于被保存的图"，但参照取的是保存之后的 `im`，默认了 `save()` 不改源图。修订把这个默认前提写明，并把参照换成保存前的快照。它不对合理实现增加任何要求。
- **公开行为**：
  - `Image.save` 的公开说明只描述写文件、返回 None，没有改动图像的副作用（`W/src/PIL/Image.py:2156-2184`）；
  - base 的 `_save` 对任何模式都不改调用者的像素（`TIP:1481-1720`）；
  - 公开测试 `test_g4_write`（`W/Tests/test_file_libtiff.py:110-122`，docstring 为 "Checking to see that the saved image is the same as what we wrote"）保存 `rot` 之后，拿同一个 `rot` 与重开的结果比较，同样依赖这一点。
- **模板依据**：v1 §4 把"就地改坏被比较的输入"列为退化方向。同仓 `3a61c9e9` 已批准的 R-c 也补过"调用前快照"（v1 §11）。

### R-c4：文件里存的未压缩样本按 WhiteIsZero 存储（即原图逐字节取反）

- **读取端语义**：Pillow 对 262=0 的 1 位和 8 位数据按反相解包，`'1;I'`/`'1;IR'` 见 `TIP:136-139`，`'L;I'`/`'L;IR'` 见 `TIP:160-163`。这是 base 既有、有公开测试保护的行为：`test_g4_eq_png`、`test_g4_fillorder_eq_png`（`W/Tests/test_file_libtiff.py:99-108`）读 262=0 的 G4 图，并与 PNG 参考图比较。
- **WhiteIsZero 文件存的是取反样本**：公开测试 `test_gray_semibyte_per_pixel`（`W/Tests/test_file_tiff.py:487-518`）断言 262=0 的 `hopper2I.tif`、`hopper4I.tif` 与 262=1 的 `hopper2.tif`、`hopper4.tif` 解出同一张图。文件头已读，两组的 259 都是 1（未压缩）。
- **题面**：`UP:26` 要求 "accurately reflecting the specified photometric interpretation"；`UP:29` 说标签不对会 "affects how the image is interpreted and rendered"。
- **不扩大需求**：
  - 只要读取端不变，这条断言就与已有的往返断言等价，因为 `'1;I'`、`'L;I'` 解包都是逐字节的一一对应。
  - 它只额外拒绝一种做法：改读取端，让往返看起来通过（B）。B 会让所有已有的 WhiteIsZero 文件被读反，包括上面两条公开测试用的 G4 图，以及无压缩的 `W/Tests/images/issue_2278.tif`（262=0，1 位）。
- **适用前提**：
  - 默认的未压缩写出只有一个条带：非 libtiff 时 `rows_per_strip = im.size[1]`（`TIP:1584-1585`），写出器也只调整单条带偏移（`TIP:867-873`）；
  - 不写 FillOrder（即取 1）；
  - hopper 宽 128，`'1'` 模式每行正好 16 字节，逐字节 XOR 0xFF 不会碰到行尾填充位。
  - gold（逐像素反相的副本配 rawmode `'1'`，以及 `ImageOps.invert`）和 C1（`'1;I'` packer，以及 `point`）两种机制都满足这些前提，试跑都通过（§5.2）。只有写成非基线 FillOrder=2 的实现会被误伤，那不是合理实现。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即唯一的隐藏测试文件 `HT`。
- **草案条目**：一条 `hidden_test_text_replace`，只有一处 edit。
  - `old` 是父版本 `HT:451-457`，即 `def test_photometric` 的整个函数体，在全文中恰好出现一次；装饰器 `HT:450` 不动。
  - `new` 是下面的函数体。
- **修订后位置**：`HT':450-496`。其后的测试整体下移 39 行；试跑日志里两个 SKIPPED 的行号从 700/714 变为 739/753，与此一致。

```python
    @pytest.mark.parametrize("mode", ("1", "L"))
    def test_photometric(self, mode, tmp_path):
        filename = str(tmp_path / "temp.tif")
        im = hopper(mode)
        original = im.copy()
        im.save(filename, tiffinfo={262: 0})
        # saving does not modify the image that is saved
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 0
            assert_image_equal(original, reloaded)
            offsets = reloaded.tag_v2[TiffImagePlugin.STRIPOFFSETS]
            counts = reloaded.tag_v2[TiffImagePlugin.STRIPBYTECOUNTS]
        # WhiteIsZero: the stored (uncompressed) samples are the inverse of
        # the image values; checked on the file bytes, not via the TIFF reader
        with open(filename, "rb") as fp:
            data = fp.read()
        stored = b"".join(data[o : o + n] for o, n in zip(offsets, counts))
        assert stored == bytes(b ^ 0xFF for b in original.tobytes())

        # BlackIsZero is still the default
        filename = str(tmp_path / "default.tif")
        im = hopper(mode)
        im.save(filename)
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 1
            assert_image_equal(original, reloaded)

        # an explicitly requested BlackIsZero is kept as well
        filename = str(tmp_path / "explicit1.tif")
        im = hopper(mode)
        im.save(filename, tiffinfo={262: 1})
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 1
            assert_image_equal(original, reloaded)

        # the requested WhiteIsZero is also kept when libtiff writes the file
        compression = "group4" if mode == "1" else "tiff_lzw"
        filename = str(tmp_path / "compressed.tif")
        im = hopper(mode)
        im.save(filename, tiffinfo={262: 0}, compression=compression)
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 0
            assert_image_equal(original, reloaded)
```

**各行对应哪一项：**

| 行（`HT'`） | 内容 | 项 |
| --- | --- | --- |
| 454、457 | 保存前快照；保存后源图不变 | R-c3 |
| 459 | 标签为 0（原有断言） | 原核心要求 |
| 460 | 重开的图等于快照（原有断言，参照改为快照） | 原核心要求 + R-c3 |
| 461-468 | 未压缩条带的字节等于原图逐字节取反 | R-c4 |
| 470-477 | 默认保存：源图不变、标签为 1、往返不变 | R-c1（及 R-c3） |
| 479-486 | 显式 262=1：同上 | R-c1（及 R-c3） |
| 488-496 | 压缩保存 262=0：源图不变、标签为 0、往返不变 | R-c2（及 R-c3） |

**设计说明：**

- **为什么并进已有目标测试、不新增键**（这是与 `review.md` §5 唯一的结构差别）：
  - R2E 的评分要求观测映射与期望映射逐键完全相同才得 1。把四项断言放进 `test_photometric[1]`/`[L]`，与拆成 6 个新键相比，对得分的区分力相同：任一断言失败，都会让对应的目标键 FAILED，整题得 0。
  - 不新增键就不需要期望修订，正式材料只需落一条 `hidden_test_text_replace`。这也是本次派发的要求。
  - 代价有两点：只看状态映射分不出是哪一项失败，要看评分日志里的失败行；同一个键里先失败的断言会挡住后面的断言。每个已知错误候选都在不同的行首次失败（§5.2），足以区分。
  - 断言内容与复核合并版相同，写法上有两处小差别：默认情形用 `im.save(filename)`（复核版是 `tiffinfo={}`，两者走同一行 `TIP:1508`）；压缩实例按 `mode` 选 `group4` 或 `tiff_lzw`，组合与复核版相同。
- **每个子情形都重新取 `hopper(mode)`**：`hopper` 每次返回缓存图的副本（`HLP:242-260`），所以前一段即使被候选原地改坏，也不会影响后一段。所有往返比较都以第一张图保存前的快照 `original` 为参照，它的内容与每次新取的 `hopper(mode)` 相同。
- **依赖与环境**：只用文件头已经导入的 `hopper`、`assert_image_equal`、`Image`、`TiffImagePlugin`（`HT:6-17`），不依赖 `Tests/` 下 base 的辅助代码；只写 `tmp_path`；没有时间、随机或网络因素。
- **刻意不测**（属于 T3，或题面没有规定，见 §6）：
  - `tiffinfo` 用 IFD 对象或元组值传入；
  - 其它模式与其它 262 取值（gold 对所有模式都放行用户给的值，属于 G1）；
  - 多帧 `save_all`，写入 BytesIO；
  - 压缩数据的存储字节：压缩数据不能逐字节比较，这条路径靠往返断言约束，读取端被改的情况由 R-c4 的未压缩实例挡住。

## 4. 期望映射逐键变化

- **没有变化**。62 键照旧：60 个 PASSED；`TestFileTiff.test_closed_file`、`TestFileTiff.test_context_manager` 仍为 FAILED（死键）。`revision_draft.json` 的 `expected_after` 与父版本期望映射逐键相同，键保留原来的 ANSI 粗体包裹格式。
- **变的是两个目标键 PASSED 的含义**：`TestFileTiff.test_photometric[1]`、`[L]` 原来只要求"标签为 0，且与保存后的 `im` 往返一致"；现在还要求满足 §2 的四项。期望值仍是 PASSED，依据是 §2 的公开语义（题面、公开代码与公开测试），不是复制 gold 的输出。gold 通过是验证结果，不是依据。
- **正式修订单**：只需一条 `hidden_test_text_replace`，不需要 `expected_file_replace`。
- **版本记录**（全长哈希见 `revision_draft.json`）：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，734 行） | `3351f53a…` |
  | 父版本 `expected_output.json`（62 键） | `28da3c25…` |
  | 父版本隐藏测试树 | `d1a4b965…`，`material_revisions` 为空 |
  | `helper.py`（不改） | `6e00e34c…` |
  | 修订后 `test_1.py`（`HT'`，773 行） | `179b8ff3…` |
  | 试跑用 `draft.json` | `77b524af…` |
  | 试跑用 `expected_after.json`（62 键；内容与父版本逐键相同，文件经重新序列化，字节摘要不同） | `ddd8f521…` |

  父版本各项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:38` 一致（该行 sha256 `7fd25db5…`）；`s2_r2e/revisions/material_revisions_v1…v8.json` 里都没有本题条目。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化为整个 `/testbed` 交给评分用户。测试以 uid 54322 跑来源入口 `run_tests.sh`，用正式解析器逐键比较。
- 派生镜像 `sha256:2a981728…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV` 下六本正式账本的 `image_id_actual` 相同。
- 补丁都从磁盘原件上传：`cands/` 下六份补丁的 sha256 与 `INV` 下的副本、正式账本的 `candidate.patch_sha256` 一致。上传前在仓库外的 base 副本上 `git apply --check -v` 全部通过。
- 每次试跑 `RH2_APPLY_RC=0`；修订草案都报 `RH2_TRIAL_EDITS_APPLIED=1`；62 键全部解析，没有 missing / extra。
- 单次试跑墙钟 29–79 s，其中 pytest 本身 0.71–1.18 s。
- 远端目录 `/work/r2e/trials/lc_pillow_2d01/2d01f7d0/`，命令形如 `trial_grade.py --task pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96 --patch <补丁|none> --edits draft.json --expected expected_after.json --out rev_<候选>.json`；当前材料对照不带 `--edits`，用 `--expected current`。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差两个目标键，失败在 `HT:456` `assert 1 == 0` | `trials/env_noop_current.json`（试跑）；正式：`runs/r2e_lifecycle_20260929/env_verify/ledger_l1_noop.jsonl:10`，60/62 |
| gold | 1：62/62 | `trials/env_gold_current.json`（试跑）；正式：`runs/r2e_lifecycle_20260929/env_verify/ledger_l1_gold.jsonl:10` |
| D、C1、C3、A、B | 都是 1.0，62/62 | `INV/ledger_{D,C1,C3,revA,revB}.jsonl:1`（协调者正式评分） |
| C2 | 0.0，60/62，两个目标键失败在 `HT:457` "got different content" | `INV/ledger_C2.jsonl:1`（正式） |

### 5.2 修订草案下的验收

两个目标键 `TestFileTiff.test_photometric[1]`、`[L]` 在每个候选上的结果相同，下表只列一次。结果文件为 `trials/rev_<候选>.json`。

| 候选 | 补丁 | 角色 | 应得 | 预测的首个失败行（`HT'`） | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | **1**，62/62 | 1 |
| C1 | `cands/pillow_2d01_C1.patch` | 合理替代解（机制与 gold 不同） | 1 | — | **1**，62/62 | 1（正式） |
| noop | 无 | 空补丁 | 0 | 459：`assert 1 == 0` | **0**，恰好两个目标键；两键都在 459 失败 | 0 |
| D | `cands/pillow_2d01_D.patch` | 第 3 步退化，R-c1 的触发反例 | 0 | 476：默认保存后 `assert 0 == 1` | **0**，恰好两个目标键；两键都在 476 失败 | **1**（正式） |
| C3 | `cands/pillow_2d01_C3.patch` | 第 4 步候选，R-c2 的触发反例 | 0 | 492：压缩保存抛 `AttributeError: encoderconfig` | **0**，恰好两个目标键；两键摘要都是 `AttributeError: encoderconfig`，可见的回溯在 492 | **1**（正式） |
| C2 | `cands/pillow_2d01_C2.patch` | 已知错误候选（只改标签） | 0 | 460：往返 "got different content" | **0**，恰好两个目标键；`[L]` 的回溯在 460，`[1]` 摘要同为 "got different content" | 0（正式） |
| A | `cands/pillow_2d01_revA.patch` | 第 3 步退化，R-c3 的触发反例 | 0 | 457：保存后源图已变，"got different content" | **0**，恰好两个目标键；`[L]` 的回溯在 457，`[1]` 摘要相同 | **1**（正式） |
| B | `cands/pillow_2d01_revB.patch` | 第 4 步候选，R-c4 的触发反例 | 0 | 468：存储字节不等于原图取反 | **0**，恰好两个目标键；两键都在 468 失败（`[1]` 首字节 `\x00` 对 `\xff`，`[L]` 首字节 `\x1a` 对 `\xe5`） | **1**（正式） |

说明：试跑结果只保存日志末尾 8000 字符，部分候选（C3、C2、A）有一个参数的回溯被截掉；这一参数的失败原因取自 pytest 的 short summary，与另一参数的同一代码路径一致。

### 5.3 判读

- **正对照为 1，noop 为 0**：成立。
  - gold 本身满足四项公开要求：私有对照里默认值不变（`INV/pcheck_default_photometric_kept_gold.json`：`L 1 77 | 1 1 255 | RGB 2 (1, 2, 3)`）；显式 1 保留（`INV/pcheck_explicit1_gold.json`：`tag262 1 pixel00 77`）；LZW 路径保留 0（`INV/pcheck_compressed_path_observe_gold.json`）；G4 往返一致（`INV/pcheck_g4_whiteiszero_roundtrip_gold.json`：`tag262 0 same True`）；题面原例 `tag262 0 mode L pixel00 0`（`DC/private_control.json`）。
  - gold 把"尊重用户给的 262"扩大到所有模式和取值（G1），本修订不测，也不要求。
- **误判已纠正**：D、C3、A、B 在当前材料上都得 1，修订后都得 0，而且各自首先失败在针对它的那一项：D 在 R-c1（476），C3 在 R-c2（492），A 在 R-c3（457），B 在 R-c4（468）。D 通过了 457–468，C3 通过了 457–486，B 通过了 457–460，说明每一项都挡住了其余几项挡不住的候选。
- **已知错误候选仍为 0**：C2 在 460 失败，与修订前的失败点（`HT:457`）是同一条往返断言。
- **没有误拒**：C1 得 1。它在四项上都用了与 gold 不同的机制：只对 1/L 且请求 0 时保留；`'1'` 用 C 层 `'1;I'` packer，`'L'` 用 `point`；libtiff 路径也经 `'1;I'` packer 写 G4。`review.md` §5 要求实跑确认的"C1 的压缩路径"由此确认。
- **旧键不受影响**：8 次试跑里，另外 60 个键全部与期望一致（`status_diff` 只含两个目标键）；两个死键仍因 `TypeError` 失败。
- **未跑**："保存前原地反相、写完再恢复"这类实现，按 `review.md` §7 的静态判断得 1；它不改变本轮结论，本轮不为它造候选。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（都在 `test_photometric[1]`、`[L]` 两个键里）：
- 两种模式、未压缩与压缩（G4 / LZW）保存时，都保留用户指定的 262=0；
- 文件里的未压缩样本按 WhiteIsZero 存储（原图逐字节取反），不依赖读取端验证；
- Pillow 重开后得到原图；
- 保存不修改被保存的图像；
- 不给 262 时仍写 1，显式给 1 时写 1。

**仍未覆盖，维持登记：**
- **T5 死键**：R-a 可选，本轮不做。
- **T3**：
  - `tiffinfo` 用 IFD 对象或元组值传入；
  - 多帧 `save_all`（gold 对所有模式放行，混合模式多帧时 RGB 帧也会被写成 262=0，见 `review.md` §7）；
  - 写入 BytesIO；
  - 一种双重错误的构造：未压缩路径写对，压缩路径只改标签，同时只改 libtiff 读取分支让往返通过。它会被公开 G4 测试（`W/Tests/test_file_libtiff.py:99-108`）挡住，但隐藏测试挡不住。目前没有具体实例，只登记。
- **P4**：维持登记，R-f 可选。探针分析时，"标签断言通过、只在像素或存储字节断言失败"的补丁建议标为"疑似规格争议的待复核样本"，原始 reward 保留（`review.md` §6）。
- **G1、X1、H1**：照 `card.md` 与 `review.md` 登记，不变。
- **A 线通用面**：根目录 `conftest.py` 以插件方式加载候选可改的 `Tests/helper.py`（`review.md` §0）。本修订不涉及。

## 7. 边界与交接

- **只做 R-c**：
  - 不改题面，不删键，不放宽已有断言，没有复制 gold 的输出作期望；
  - 四项都有公开依据，不涉及 P5 或其它模板外事项，**不需要用户决定**。
  - 一轮修订、一轮验收即收敛，没有触发 v1 §7.2 的停止条件。
- 没写 `s2_r2e` 下的正式修订单与 pins，没改生产代码；远端只在 `/work/r2e/trials/lc_pillow_2d01/2d01f7d0/` 上传文件和跑试跑。
- **协调者待办：**
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单：一条 `hidden_test_text_replace`，不加期望修订；可用 `revised_hidden_test_sha256`（`179b8ff3…`）核对重算结果。
  2. 重建材料与派生镜像。重建后必须仍带 libtiff：gold 正对照为 1 就同时确认了这个前提；如果缺 libtiff，gold 会在 `HT':492` 失败。
  3. 正式评分跑 8 个候选：gold、C1、noop、D、C3、C2、A（`revA`）、B（`revB`），按 §5.2 判读。每个都要核对补丁确已交付、两个目标键确实执行。
  4. 送 Codex 复核。
- **之后重判 v1 用途**：按 `card.md` §1 与 `review.md` §9 重判。训练候选需要的正面证据（核心断言、noop 0 / gold 1、第 2、3 步结果）届时齐全；留出评测仍受 D3 按仓库划分和"标明版本的自建题"的限制。修订版落地后，"原版加事后审计"这条能力比较路线不再需要（`review.md` §9 补的两项审计只对原版有意义）。
