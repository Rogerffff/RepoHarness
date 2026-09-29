# pillow__2d01f7d0 独立复核（第二步：对照公开读者、主审产物、历史引用与今晚实跑）

2026-09-29 · 独立复核。初判见同目录 `reviewer_initial.md`（先于本文封存，未改动）。

**缩写**（均为仓库根目录下的相对路径）：

- `OUT` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`
- `INV` = `runs/r2e_lifecycle_20260929/inv/pillow_2d01`
- `DC` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`
- `T1PY` = `runs/r2e_static_prep_20260924/v3/private/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/hidden_tests/test_1.py`
- `TIP` = 公开工作树 `worktree/src/PIL/TiffImagePlugin.py`（base 版）

## 0. 结论

**同意主审的主干结论：**

- 处置为 `needs_repair`，两个 S1 都成立：
  - 退化候选 D 得 1，判 T2b；
  - C3 得 1，但压缩保存会崩溃，按 v1 第 4 步判 S1。
- 像素是否需要反相按 P4 登记，不交用户。
- T5、X1、G1 的登记，以及四项用途的当前取值，都同意。

**需要修改两处：**

1. **两个新的高影响问题。** 我提出的 A、B 两个候选，协调者已按我的描述写成补丁并正式评分，都得 1（62/62）：
   - A：写完文件后，把调用者的图像原地反相；
   - B：只保留标签，同时改读取端，让它读 WhiteIsZero 时不再反相。

   A 属于第 3 步退化探测，判 S1（T2b）。B 属于第 4 步，判 S1（T2），理由见 §4。因此，主审把"保存时就地改动调用者图像"记成 T3/S2（`OUT/analysis_before_history.md:201`、`OUT/card.md:37`、screening_record 的 T3 条目）需要改为 S1。
2. **主审的 R-c1 + R-c2 挡不住 A 和 B。** 按源码推断，A、B 在 R-c1 与 R-c2 的新键上都会通过（§3）。需要把我初判里的两条断言并入同一轮修订：保存前快照，以及直接检查文件里存储的像素字节。合并版见 §5。验收矩阵要加入 A、B。

**另有两处小的补正：**

- 能力比较如果选"原版加事后审计"，审计清单要补两项：保存不修改源图；未压缩存储样本确为反相（或读取 WhiteIsZero 文件的结果不变）。
- `OUT/analysis_before_history.md:44` 说"候选无法借改 helper 放宽断言"，这句话过强。隐藏测试导入的 helper 确实受保护，但根目录 `conftest.py` 会以插件方式加载仓库里的 `Tests.helper`，这两个文件候选都能改。这是通用控制面问题，归 A 线。账本有 `candidate_touched_conftest_or_fixture` 字段，但它是否覆盖 `Tests/helper.py` 我没有核实。

**修订可以开做。** 按 §5 的合并版 R-c 执行，属于预授权模板，不需要用户决定。建议先在一次性私有容器里用 gold 和 C1 预核新测试文件，再重建材料、正式验收 8 个候选，最后交 Codex 复核。

## 1. A、B 补丁是否忠实于我的描述，评分是否有效

| 候选 | 补丁 | 与 `reviewer_initial.md` §5 的描述对照 | 评分有效性 | 结果 |
| --- | --- | --- | --- | --- |
| A | `OUT/cands/pillow_2d01_revA.patch`（与 `INV/pillow_2d01_revA.patch` 逐字节相同，sha256 `79613b5e…`，与账本 `candidate.patch_sha256` 一致） | **忠实。**TIP:1571 换成"不在 ifd 里才写默认值"，并加了 `invert_after`；在 `_save` 末尾（`_debug_multipage` 那段之后、`class AppendingTiffWriter` 之前）原地反相 `im` 的像素。这两处都与描述逐行一致 | 日志 `INV/logs_revA/evallog_replay-r2e-inv-2d01-revA_472b5510.eval.log`：:1 为 ` M src/PIL/TiffImagePlugin.py`，:6 `RH2_SETUP_APPLY_RC=0`，:103 `test_sanity` PASSED，:141-142 两个目标键 PASSED，:167 为 summary | `INV/ledger_revA.jsonl:1`：1.0，62/62，`included_paths=["src/PIL/TiffImagePlugin.py"]` |
| B | `OUT/cands/pillow_2d01_revB.patch`（sha256 `fed050f2…`，与账本一致） | **忠实。**OPEN_INFO 中 WhiteIsZero 的 8 个条目（TIP:136-139、160-163）改成 `1`/`1;R`/`L`/`L;R`；`_save` 只保留用户给的标签，不反相 | `INV/logs_revB/evallog_replay-r2e-inv-2d01-revB_e3008f8d.eval.log`：行位同上，全部满足 | `INV/ledger_revB.jsonl:1`：1.0，62/62 |

两次运行都用当前派生镜像 `sha256:2a981728…`（配方 `r2e_derive_v1+sysconfig_v1`）。隐藏测试树的哈希是 `d1a4b965…`，与原材料一致；grader、scripts 和 profile 的摘要与 D、C1、C2、C3 那组相同。

## 2. 主审的决定性主张逐项核对

| 主张 | 核对结果 | 依据 |
| --- | --- | --- |
| 新机器上 noop 为 0、gold 为 1 | **确认** | `runs/r2e_lifecycle_20260929/env_verify/ledger_l1_noop.jsonl:10`：0.0，60/62，只错两个目标键；`ledger_l1_gold.jsonl:10`：1.0，62/62；同一张新镜像 |
| D 得 1，判 S1（T2b） | **确认** | `INV/ledger_D.jsonl:1`：62/62，应用与执行有效（日志 :1、:6、:141-142）。违例：`INV/pcheck_explicit1_D.json` 输出 `tag262 0 pixel00 77` 后抛 AssertionError；`INV/pcheck_default_photometric_kept_D.json` 输出 `L 0 77 \| 1 0 255`。D 与我初判的 D1 属于同一类（丢掉"用户指定"这个条件），D 用的是 `1;I` packer，gold 用的是逐像素循环，不影响结论 |
| C3 得 1，但压缩保存崩溃，按第 4 步判 S1 | **确认，同意不是罕见路径** | C3 就是 gold 去掉 `encoderconfig` 的提升（我用 diff 核对过，只差这两处）；`INV/ledger_C3.jsonl:1` 为 62/62；`INV/pcheck_compressed_path_observe_C3.json` 与 `pcheck_g4_whiteiszero_roundtrip_C3.json` 在 TiffImagePlugin.py:1710 抛 `AttributeError: encoderconfig`，gold 两项都通过。262=0 加压缩保存属于核心要求的另一个实例；G4 压缩的 WhiteIsZero 是二值 TIFF 最常见的形态，仓库测试图里就有 13 张以上 |
| C1 得 1（替代正对照） | **确认** | `INV/ledger_C1.jsonl:1`，62/62。C1 与我初判的 C 逻辑相同 |
| 只改标签的 C2 得 0，失败在像素断言 | **确认** | `INV/logs_C2/…9bed30ef.eval.log`:113/134 与 :149/170 报 `got different content`，:237-239 为 summary |
| libtiff 可用；PIL 以可编辑方式从 `/testbed/src` 导入；公开测试有 2 个基线失败 | **确认** | `DC/orig/captures/env_import.out`（`libtiff True 4.3.0`）；`DC/orig/captures/public_tiff_tests.out`（2 failed / 80 passed / 2 skipped，两个失败都是 `pytest.warns(None)`）；`DC/devcheck.log` 里只有 `all_match_expect=false`，原因是公开读者把 `public_tiff_tests` 的预期写成退出 0 |
| gold 满足全部公开要求 | **确认（限已查项）** | `DC/private_control.json`：原例 `tag262 0 … pixel00 0`，默认值不变，LZW 路径 `tag262 0`；`INV/pcheck_*_gold.json` 四项都通过 |
| 历史只做过环境资格审查，"不需要材料修订"被推翻 | **确认** | 历史 `r2e_env_repair_20260924/tasks/pillow__2d01…/findings.md`:1-18 只涉及环境，没有需求—断言对照和退化探测 |
| 保存时就地改动调用者图像：记 T3/S2，"太刻意，未构造" | **推翻** | A 正式评分 1.0（§1）。"就地改坏被比较的输入"是 v1 §4 明列的退化方向，而且只凭 gold 的修改位置就能写出，构造成本很低。改为 S1（T2b） |
| 隐藏测试用自带 helper，"候选无法借改 helper 放宽断言" | **修改措辞** | 根目录 `conftest.py:1` 为 `pytest_plugins = ["Tests.helper"]`，评分时会以插件方式加载候选可改的 `Tests/helper.py`，理论上可以塞入 pytest hook。属于 E3 通用面，归 A 线，不影响本题结论 |

## 3. 主审的 R-c1、R-c2 能否挡住 A 和 B

依据 `OUT/analysis_before_history.md` 附录 B.1、B.2 做源码推断，与已实跑的 A、B 行为一致：

| 候选 | 原 `test_photometric` | R-c1：默认值与显式 262=1 | R-c2：`'1'`+group4、`'L'`+tiff_lzw | 结果 |
| --- | --- | --- | --- | --- |
| A | 通过（已实跑） | **通过**：标签为 1 时 `invert_after` 为假，不改源图，往返一致 | **通过**：libtiff 分支写入未反相的数据并标为 0，写完再原地反相调用者图像；R-c2 同样拿保存之后的 `im` 与重开图比较，两边都是反相图 | **仍得 1** |
| B | 通过（已实跑） | **通过**：262=1 的读取条目没有改 | **通过**：libtiff 解码时 tile 的 rawmode 也来自被改过的 OPEN_INFO，不再反相，存储值等于原图 | **仍得 1** |

结论：R-c1 与 R-c2 只能挡住 D 和 C3，挡不住 A、B。问题有两个根源：

- 比较参照是保存之后的 `im`，候选可以把它改坏；
- 写入端对不对，只借读取端来验证，而读取端候选也能改。

## 4. B 判第 4 步 S1 还是 S2

**判 S1。** 按 v1 §4 第 4 步，只要"破坏了有文档、常用的公开行为"或"在同一核心要求的其它实例上违反公开要求"之一就命中。B 两条都命中：

1. **它违反了核心要求本身。** B 写出的文件标签是 262=0（WhiteIsZero），存储的却是 BlackIsZero 的数据。除了被 B 改过的 Pillow，任何读者都会把它显示成反相：libtiff 工具、看图软件、base 版 Pillow 都是如此。这与题面 "accurately reflecting the specified photometric interpretation" 相冲突。测试之所以看不出来，只是因为验证用的读取端也被 B 改了。
2. **它破坏了有文档、常用的公开行为：读取 WhiteIsZero 的 1 位和 8 位文件。**
   - 这是 base 的既有语义（TIP:136-139、160-163）；
   - 有公开测试保护：`worktree/Tests/test_file_libtiff.py`:99-108 的 `test_g4_eq_png`、`test_g4_fillorder_eq_png`，用到的 `hopper_g4_500.tif`、`g4-fillorder-test.tif` 都是 262=0；
   - WhiteIsZero 是传真类 G3/G4 二值 TIFF 的通行编码，仓库测试图里有 13 张以上，不是边缘输入。
3. **"要 libtiff、且不在隐藏集"不构成降级理由：**
   - 本镜像 libtiff 4.3.0 可用（`DC/orig/captures/env_import.out`），那些公开测试在解题环境里是能跑的；
   - 未压缩的 WhiteIsZero 文件（例如 `Tests/images/issue_2278.tif`，262=0，1 位，无压缩）根本不需要 libtiff，同样会被读反；
   - "不在隐藏集"正是这次漏测的原因，不能反过来当作减轻严重度的理由。
4. **证据层次。** B 的得分是执行证据。违例本身目前是源码推断，加上公开测试的明确断言，按 v1 §4"可复用明确的源码推导、已有公开测试"已经足够。如果想把违例也变成执行证据，可以做 §8 的可选私有对照（成本很低）。

A 按 v1 §4 第 3 步判 S1（T2b）。它违反两点：

- 文件内容没有按 WhiteIsZero 存储：用题面原例保存全黑图，任何读者看到的都是全白；
- `save()` 修改了调用者的图像。

判断输入：`im = hopper("L"); ref = im.copy(); im.save(p, tiffinfo={262: 0})`，之后 `im != ref`，重开的图也 `!= ref`。

## 5. 合并后的修订（R-c，一轮完成）

放进 `PRIV/hidden_tests/test_1.py`：替换 T1PY:450-457，并在其后加入两个新测试。原来两个目标键的键名不变，新增 6 个键，全部期望 PASSED，总数 62 + 6 = 68，与主审的计数相同。死键不动；R-a 仍为可选，不建议在本轮做。

```python
    @pytest.mark.parametrize("mode", ("1", "L"))
    def test_photometric(self, mode, tmp_path):
        filename = str(tmp_path / "temp.tif")
        im = hopper(mode)
        original = im.copy()
        im.save(filename, tiffinfo={262: 0})
        # saving does not modify the image being saved
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 0
            assert_image_equal(original, reloaded)
            offsets = reloaded.tag_v2[TiffImagePlugin.STRIPOFFSETS]
            counts = reloaded.tag_v2[TiffImagePlugin.STRIPBYTECOUNTS]
        # WhiteIsZero: the stored (uncompressed) samples are the inverse of the
        # image values; checked on the file bytes, not through the TIFF reader
        with open(filename, "rb") as fp:
            data = fp.read()
        stored = b"".join(data[o : o + n] for o, n in zip(offsets, counts))
        assert stored == bytes(b ^ 0xFF for b in original.tobytes())

    @pytest.mark.parametrize(
        "mode, tiffinfo",
        [("1", {}), ("L", {}), ("1", {262: 1}), ("L", {262: 1})],
        ids=["1-default", "L-default", "1-explicit1", "L-explicit1"],
    )
    def test_photometric_blackiszero_kept(self, mode, tiffinfo, tmp_path):
        filename = str(tmp_path / "temp.tif")
        im = hopper(mode)
        original = im.copy()
        im.save(filename, tiffinfo=tiffinfo)
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 1
            assert_image_equal(original, reloaded)

    @pytest.mark.parametrize(
        "mode, compression", [("1", "group4"), ("L", "tiff_lzw")]
    )
    def test_photometric_compressed(self, mode, compression, tmp_path):
        filename = str(tmp_path / "temp.tif")
        im = hopper(mode)
        original = im.copy()
        im.save(filename, tiffinfo={262: 0}, compression=compression)
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 0
            assert_image_equal(original, reloaded)
```

**四处改动，各针对一个窄问题：**

| 编号 | 改动 | 公开依据 | 挡住 |
| --- | --- | --- | --- |
| R-c1（主审） | 不给 262 或显式给 1 时仍写 1，像素往返不变 | 题面 "retain the specified photometric interpretation"；SAVE_INFO TIP:1459-1460；公开测试注释 `Tests/test_file_libtiff.py`:151-152 | D |
| R-c2（主审） | 压缩（libtiff）保存同样保留 0，且往返不变 | 题面没有限定压缩方式；文档列出 `compression` 选项；覆盖 262 的那一行在两条写出路径分叉之前 | C3 |
| R-c3（复核补） | 保存前做快照；比较对象改为快照；断言保存后源图不变 | 保存不修改被保存的图像，这是常用的公开行为；原测试比较"保存后的 `im`"，其实默认了这一点，这里只是把它写明 | A |
| R-c4（复核补） | 直接取文件里的未压缩条带字节，断言等于原图取反 | TIFF 对 WhiteIsZero 的定义；base 读取端的反相映射（TIP:136-139、160-163）；题面 "accurately reflecting…"。在读取端不变的前提下，这条等价于原有的往返断言，所以不会扩大对合理解的要求 | B，以及只改标签的 C2 |

- **R-c4 的前提：** 默认未压缩、单条带、FillOrder 1。hopper 宽 128，每行正好是整字节，mode "1" 用 XOR 0xFF 取反不会碰到行尾填充位。gold 和 C1（`1;I` packer）都满足这个前提。只有写成非基线的 FillOrder=2 才会被误伤，而那不是合理实现。
- **R-c2 的前提：** 派生镜像带 libtiff。这点已实测为 4.3.0，镜像重建后要复核。
- **合并后仍受保护的公开要求：** 两种模式下都保留 0（未压缩与压缩）；文件内容按 WhiteIsZero 存储；Pillow 读回原图；保存不修改源图；默认值和显式 1 都写 1。

**验收矩阵**（预测值；"执行"表示对应补丁已有正式评分）：

| 候选 | 改后 `test_photometric` | `blackiszero_kept` ×4 | `compressed` ×2 | 预期 reward |
| --- | --- | --- | --- | --- |
| gold | 通过 | 通过（pcheck 默认值与显式 1 已通过） | 通过（pcheck G4 与 LZW 已通过） | **1** |
| C1 | 通过（`1;I` 存储即为取反） | 通过 | 通过（libtiff 编码器按 rawmode 找 packer，`worktree/src/encode.c` 中 `get_packer`，需实跑确认） | **1** |
| noop | 失败（标签） | 通过 | 失败（标签） | **0** |
| D | 通过 | 失败（写成 0） | 通过 | **0** |
| C3 | 通过 | 通过 | 失败（`AttributeError: encoderconfig`） | **0** |
| C2 | 失败（往返与存储字节） | 通过 | 失败（往返） | **0** |
| A | 失败（快照与存储字节） | 通过 | 失败（快照） | **0** |
| B | 失败（存储字节） | 通过 | 通过 | **0** |

另外还要：保存新版本、父版本 `expected_v0`、修订理由和触发反例（D、C3、revA、revB），并交 Codex 复核。

## 6. P4 复核：只改标签有没有公开依据

**维持 P4，不交用户；但公开读者的分歧说明这是真实风险。**

- 公开读者从题面字面出发，认为两种做法都满足题面（`OUT/public_read.md`:13、42-43），并说 "display issues" 之类的句子是套话，不宜据此推断像素语义（:62）。我同意那句话不能作为主要依据。但主审的主要依据不是它，而是公开代码与公开测试的语义：
  - 读取端对 262=0 反相解码；
  - 公开测试 `test_gray_semibyte_per_pixel` 断言 262=0 的 `hopper2I.tif` 与 262=1 的 `hopper2.tif` 解出同一张图，我在初判里读过两张图的文件头；
  - `_save` 会覆盖 BitsPerSample 等结构性标签，以保证文件自洽（TIP:1562-1571）；
  - base 对这个调用本来就是往返一致的。

  公开读者自己也指出，只改标签会让拷贝标签重存的图整体反相（`OUT/public_read.md`:68）。
- 我没有找到任何公开材料支持"只写标签、数据不动"是正确行为，所以不属于 P5。只改标签会破坏受影响的旧行为（往返一致），按第二批规则 1，它是"只符合题面某一句的候选"，不是被误拒的合理解。
- **建议：**
  - R-f 仍为可选。若本题要优先用于能力比较，可以在修订版上补一句只描述行为的说明，例如主审给的措辞。
  - 探针分析时，把"标签断言通过、只在像素断言失败"的补丁标为"疑似规格争议的待复核样本"，原始 reward 保留，不自动免责。

## 7. 反查主审可能没想到的范围

- **题面原例与非默认值：** 原例的全黑 `'L'` 图，gold 重开后像素为 0（`DC/private_control.json`）。`'1'`/`'L'` 配 262=4、2 这类值，gold 会原样写出并得到打不开的文件，base 会覆盖成 1。这属于 G1 的范围扩大，测试不要求，也不应要求。
- **多帧保存：** `_save_all`（TIP:1961-1983）会把同一个 `tiffinfo` 用于每一帧。gold 对所有模式都放行用户给的 262，所以混合模式多帧保存时，RGB 帧也会写成 262=0，读不回来（公开读者 `OUT/public_read.md`:46 也指出了这一点）。登记为 G1/T3，不影响修订。
- **不同的合法实现：** C1 已得 1。"保存前原地反相、写完再恢复"这类实现，在合并版的快照和存储字节断言下都能通过，不会被误拒。
- **R2E 专项：**
  - 新测试只用了已导入的 `hopper`、`assert_image_equal`、`TiffImagePlugin` 常量；
  - 新键名不与现有键冲突；
  - 没有时间或随机敏感的键；
  - R-c2 依赖 libtiff，这一前提已写进验收；
  - 死键不受影响。

## 8. 最小后续实验

1. **（建议，先做）** 在一次性私有容器里对合并后的测试文件跑 gold 和 C1，确认 R-c4 的字节断言和 R-c2 的 C1 路径都按预期通过，再重建材料。
2. **（必做）** 按 §5 正式验收 8 个候选：gold、C1、noop、D、C3、C2、revA、revB。每个都要核对补丁已交付、新键确实执行（出现在 short summary 里）。
3. **（可选，不阻塞）** 把 A、B 的违例也补成执行证据：
   - A：在私有对照里执行 `im=hopper('L'); ref=im.copy(); im.save(p, tiffinfo={262:0}); assert im.tobytes()==ref.tobytes()`，预期 A 失败、gold 通过；
   - B：应用补丁后跑公开的 `Tests/test_file_libtiff.py::TestFileLibTiff::test_g4_eq_png` 与 `::test_g4_fillorder_eq_png`，预期 B 失败、gold 通过。

## 9. 用途与处置

- **处置：** `needs_repair` 不变。修订理由改为四个 S1 触发反例：D（T2b）、A（T2b）、C3（第 4 步）、B（第 4 步）。
- **能力比较：** conditional。若走"原版加事后审计"，审计项要补上"保存不修改源图"和"未压缩存储样本为反相（或读取 WhiteIsZero 文件结果不变）"。
- **训练候选：** no（当前版本）。合并版 R-c 通过验收并经 Codex 复核后，再评估是否转为 yes。
- **留出候选：** no（当前版本），同意主审的理由。
- **分歧保留：** 无实质分歧。P4 与公开读者读法的分歧已按 §6 处理，只作风险登记。

## 附录：读取范围

- **本步新读：**
  - `OUT/public_read.md`、`OUT/commands.json`；
  - `OUT/analysis_before_history.md`、`OUT/old_findings_delta.md`、`OUT/card.md`、`OUT/screening_record.json`；
  - `OUT/cands/` 下的 6 份补丁（pcheck 脚本读的是 `INV` 下的副本）；
  - 历史：refs.json 所列 findings.md、screening_record.json、repro 脚本全文，以及 decisions.md:18、results_20260924.md:49、packages/p4/README.md:17/49/59/66/117、known_issues.json 中本题所在的条目；
  - `INV` 下 6 本账本、revA/revB/D/C3/C2 的 eval log（只看关键行）、全部 pcheck JSON 与脚本、`run_b.sh`、`run_b.log`；
  - `DC` 下的 `devcheck.log`、`private_control.json` 与 `orig/captures/*.out`；
  - env_verify 中本题的两行；
  - 公开工作树的 `src/encode.c`（grep libtiff 编码器的 `get_packer`）和 TIP:1961-1990。
- **没读：** `INV/private_check.py`、`run.sh`、`run.log`、`run_b_failed_quoting.log`、`art_*` 目录；facts.json 与 known_issues.json 的其余部分；其它题的私有包。
