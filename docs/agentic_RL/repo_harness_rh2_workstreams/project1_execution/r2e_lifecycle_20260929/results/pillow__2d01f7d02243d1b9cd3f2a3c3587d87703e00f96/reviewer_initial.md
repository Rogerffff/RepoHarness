# pillow__2d01f7d0 独立复核初判（第一步：读主审与公开读者产物之前）

2026-09-29 · 独立复核（新上下文）。本文是初判：所有候选的得分都是源码推断，没有实跑；执行证据只来自已有的 current 账本与日志。

**缩写**（均为仓库根目录下的相对路径）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`，`WT` = `PUB/worktree`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`
- `T1PY` = `PRIV/hidden_tests/test_1.py`（评分时的路径是 `r2e_tests/test_1.py`）
- `TIP` = `WT/src/PIL/TiffImagePlugin.py`（base 版）
- 日志 noop-1、gold-1、noop-2、gold-2 与四本账本的完整路径见附录 B

## 0. 初判摘要

- **题目成立，材料一致。** base 的 `_save` 在写文件前无条件执行 `ifd[PHOTOMETRIC_INTERPRETATION] = photo`（TIP:1571），用户经 `tiffinfo` 给的 262 会被覆盖成 SAVE_INFO 里的 1（TIP:1459-1460）。当前材料下两次 noop 都只在两个目标键失败，失败点是 T1PY:456 的 `assert 1 == 0`，与题面 Actual Behavior 相同。gold、期望映射、隐藏测试和 `run_tests.sh` 的哈希都能对上账本与日志；本题没有材料修订。
- **没有发现误拒合理解（T1）。** 目标测试的第二条断言要求重开的图像与原图逐字节相同（T1PY:457）。题面没有明说这一点。但"只保留标签、不改像素"的实现会让图像重开后整体反相：base 读取端对 262=0 的 1 位和 8 位数据按反相方式解包（TIP:136-139、160-163）。这违反题面"accurately reflecting the specified photometric interpretation"和"display issues"的关切，也破坏了这个调用原来"存进去什么就读回什么"的行为，所以拒绝它是对的。按 P4 登记：题面描述不全，但公开代码能推出这项要求。
- **主要问题是漏测：预测 S1（T2b），需要正式评分确认。** 目标断言只有两条：标签为 0；重开的图像等于"保存之后的 `im`"。隐藏文件里没有任何键会解码 1 位或 8 位 WhiteIsZero（262=0）的像素；用到的 compression.tif 和 g4-multi.tiff 只读标签。按源码推断，下面三个补丁都能拿 1：
  - D1：对所有 1/L 模式的保存一律写 0 并反相；
  - A：只保留标签，写完文件后把调用者的图像原地反相；
  - B：只保留标签，同时把读取端 1 位和 8 位的 WhiteIsZero 解包改成不反相。这是第 4 步的构造候选。
- **期望为 FAILED 的两个键不影响判分。** `test_closed_file` 和 `test_context_manager` 在 pytest 8.3.4 下执行到 `pytest.warns(None)` 时抛 TypeError。这发生在任何 PIL 调用之前，候选改源码无法改变它们的结果。
- **题目关系（X1，已逐文件核对）。** 本题的修复和 `test_photometric` 逐字出现在同仓 3a61c9e9、4bc64835、a682ceaf、f9d3ee0f 四题的公开初态里。反过来，本题公开初态含有 2b061b68 和 3ac9396e 的测试与修复。
- **下一步。** 用正式评分实跑 D1、A、B，以及一个合理替代解 C。四个补丁都只改 TiffImagePlugin.py，是纯 Python 改动。若 D1、A、B 中任一得 1，就按 §7 在 `test_photometric` 内补三条断言；键集不变，期望映射不用改。

## 1. 八方面：看了什么，结论是什么

| 方面 | 实际阅读范围 | 结论 |
| --- | --- | --- |
| 公开需求 | `PUB/user_prompt.txt`:1-30；`PUB/environment_brief.md`；`PUB/public_bundle.json` 的 public_hints；TIP 的 OPEN_INFO、SAVE_INFO、`_setup`、`_save`；`WT/docs/handbook/image-file-formats.rst` 第 871 行起的 tiffinfo 说明；公开旧测试 `WT/Tests/test_file_libtiff.py`:1-185、`WT/Tests/test_file_tiff_metadata.py`:80-180 | 核心要求：1/L 模式经 tiffinfo 指定 262=0 保存后，标签应保留为 0。像素要按 WhiteIsZero 存储（重开后图像不变），需要从读取端语义推出，题面没写（P4）。文档没有提 photometric。公开测试注释 `test_file_libtiff.py`:151-152 记录了旧行为："PhotometricInterpretation is set from SAVE_INFO"。 |
| 材料与初始问题 | gold.patch 全文；base `_save`（TIP:1481-1720）；两组 current noop/gold 日志与账本第 38 行；M3 独立参考 a1；manifest 的 initial_diff 与 untracked 字段 | bug 在 TIP:1571；noop 的失败点与题面一致（执行证据）。gold 的 sha256 190a8e47… 与两本 gold 账本和 validation bundle 一致。M3 a1 的 `git_gold.diff`（上游 base→修复提交的源码 diff）与当前 gold.patch 的增删行完全相同。M3 账本里 `gold_matches_git_diff_changed_lines=False` 的原因是 M3 当时应用的 gold.diff 在一处空行上的 hunk 写法不同，不是材料错配。初态没有脏改动（initial_diff 0 字节），镜像里另有未跟踪的 install.sh 和 run_tests.sh。 |
| 测试是否测到要求 | T1PY 全文（734 行）；与 `WT/Tests/test_file_tiff.py` 做 diff，只多出 T1PY:450-458；`hidden_tests/helper.py` 与 base 同 sha；用自写脚本扫描图像头（附录 A） | 目标键 `TestFileTiff.test_photometric[1]` 和 `[L]`：输入是 `hopper(mode)`（128×128，内容不均匀）、`tiffinfo={262: 0}`，走默认的未压缩路径。断言有两条：T1PY:456 检查标签；T1PY:457 `assert_image_equal(im, reloaded)`（helper.py:89-100，比较 mode、size、tobytes）。两种模式和非均匀内容都覆盖到了。没有覆盖：保存不改源图；显式 262=1 会被保留、不指定时默认值不变；读取端没有被改；压缩（libtiff）路径；tiffinfo 以 IFD 对象或 legacy v1 形式传入；save_all。 |
| 误拒 | §5 的 C 与"只改标签"参照 | 没有发现。合理替代解 C 预测得 1：它用 `1;I` packer 或 `point` 实现反相，只在"1/L 模式且值为 0"时保留用户给的值。 |
| 回归与 gold | gold 的全部改动；受影响的调用：`Image.save`（`WT/src/PIL/Image.py`:2204-2238，把 `self` 交给 `_save`）、libtiff 合并段 TIP:1647-1681、`_debug_multipage` TIP:1717-1720；60 个回归键 | gold 能修好题面原例（源码推断）。G1 有三处边缘问题，都没有测到：①gold 对所有模式都不再覆盖用户给的 262，不只 1/L 模式的 0；例如 RGB 图用 `tiffinfo={262: 1}` 保存会写出 Pillow 自己打不开的文件（读取时找不到对应键，TIP:1295-1309）。②`im` 被换成副本后，libtiff 分支不再合并原 TIFF 的 `tag_v2`/`tag`。③`_debug_multipage` 被设到副本上。这些都不会让更窄的实现被判错。回归键与本路径的交集很小，只有 `test_sanity` 以默认参数保存 1/L 图像，而且只打开、不检查内容。 |
| agent 的开发条件 | `PUB/environment_brief.md`:8-12；`r2e_environment_card.md` §2；`WT/conftest.py`、`WT/Tests/conftest.py`、`WT/setup.cfg` | 纯 Python 改动，不需要构建、pip 或网络。复现只需要 `Tests/images/hopper.ppm`，它在初态里。公开的 `Tests/test_file_tiff.py` 在 pytest 8.3.4 下有 2 个与本题无关、始终失败的用例（原因同 §3a）。actor 侧：我没有拿到 devcheck，所以**未验**。libtiff 是否可用未知，它只影响 §7 里的可选压缩实例。 |
| 交付与评分边界 | 账本的 projection 字段；`run_tests.sh`；隐藏包里的 helper | gold 只交付 `src/PIL/TiffImagePlugin.py`。隐藏测试导入自带的 `r2e_tests/helper.py`。根目录 `conftest.py`:1 用插件方式加载仓库里的 `Tests.helper`；候选可以改这个文件，但这是 R2E 的通用边界，不是本题特有的问题。题面示例会在当前目录写 `temp.tif`；如果解题者在 /testbed 下运行，这个二进制文件会留下并进入导出（H1，未验，不影响评分）。 |
| 题目关系与用途 | 两份跨题扫描；同仓另外 6 题公开包的 base_commit、TiffImagePlugin.py、test_file_tiff.py 与 CHANGES.rst | X1 的双向包含已核实（§4、附录 B）。题面没有给出修法。 |

## 2. 需求—断言映射

| 需求或旧行为 | 公开依据 | 键 / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 1/L 以 262=0 保存后，标签为 0 | 题面标题、描述、示例 | `test_photometric[1]/[L]`，T1PY:456 | 覆盖（两种模式都测了） | noop 失败于 `assert 1 == 0`，gold 通过（current 各两次） |
| 像素按 WhiteIsZero 存储，重开的图像与原图相同 | 题面 "accurately reflecting…"、"display issues"；读取端 TIP:136-139、160-163 | T1PY:457，但比较对象是**保存之后**的 `im` | 部分：比较对象可以被原地改坏（A），而且验证依赖候选能改的读取端（B） | gold 通过；A、B 待跑 |
| 指定其它值（262=1）同样保留；不指定时仍写 1 | 题面 "retain the specified photometric interpretation"；SAVE_INFO TIP:1459-1460；公开测试注释 `test_file_libtiff.py`:151 | 无 | 缺失（D1 可以钻这个空子） | D1 待跑 |
| 保存不修改被保存的图像 | `Image.save` 的常用约定：返回 None，不改像素 | 无；T1PY:457 恰好拿保存之后的 `im` 当参照 | 缺失（A 可以钻） | A 待跑 |
| 读取已有的 1 位、8 位 WhiteIsZero 文件，结果不变 | 读取映射 TIP:136-139、160-163；公开测试 `test_file_libtiff.py`:99-108（hopper_g4_500.tif 与 g4-fillorder-test.tif 都是 262=0）、`test_file_tiff_metadata.py`:94 | 隐藏键只读 compression.tif（T1PY:120-133）和 g4-multi.tiff（T1PY:442-448）的标签，不解码像素 | 缺失（B 可以钻） | B 待跑 |
| 压缩（libtiff）保存时同样保留 | 题面没有限定压缩方式；G3/G4 压缩是 WhiteIsZero 二值图最常见的形式 | 无 | 缺失（T3） | grader 镜像里 libtiff 是否可用未知 |
| 其它模式与读写的旧行为 | 同文件 60 个回归键 | T1PY 其余测试 | 与本路径交集很小 | noop、gold 都通过 |

## 3. R2E 专项

- **(a) 期望为 FAILED 的键。** 两个：`TestFileTiff.test_closed_file`（T1PY:66-72）和 `test_context_manager`（T1PY:74-79）。两次 noop、两次 gold，以及 M3 在来源镜像上的 gold，都在 `with pytest.warns(None)` 这一行失败，报 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`（noop-1:31、60、68、97；gold-1:165-166；M3 a1:150-151）。失败发生在任何 PIL 调用之前，所以只改源码的候选（包括更完整的修复）不可能把它们变成 PASSED。只有改测试基础设施（例如根目录 conftest）才可能改变结果，而这类候选本来就应判 0。按 T5 登记，不需要 R-a。
- **(b) 题面报错是否出现在 noop 目标键里。** 出现了。noop 的两个目标键都失败于 T1PY:456 `assert 1 == 0`（noop-1:111-112、126-127；noop-2 相同），与 "tag is incorrectly set to 1 instead of 0" 一致。注意：noop 在第一条断言就失败了，第二条（像素）断言在 noop 上没有执行证据。"只改标签会导致反相"是源码推断。
- **(c) 题面是否泄漏修法。** 没有。题面只给出症状和示例输入 `tiffinfo={262: 0}`，没有提到反相、`ImageOps` 或修改位置。
- **(d) 测试支撑、搬迁伪影与撞键。** 隐藏文件从 `.helper` 导入，用的是隐藏包自带的副本，sha 6e00e34c 与 base 的 `Tests/helper.py` 相同。图像路径 `Tests/images/...` 相对于 cwd=/testbed，搬到 r2e_tests/ 后照常解析。只有一个测试文件，不会撞键。两个 SKIPPED（string_dimension 图不在、仅 Windows）不成为键。期望的 62 个键等于收集到的 64 个减去跳过的 2 个，与观测键集相同（账本 `keys_equal=true`）。
- **(e) 时间、随机、资源敏感的键。** 没有。整个测试 0.28-0.32 s。`test_unclosed_file` 依赖 CPython 引用计数触发 ResourceWarning，在 5 份日志里都稳定通过。
- **(f) 材料修订。** 无（`PRIV/revisions.json` 为 `[]`）。

## 4. 问题清单（按 v1 编号，初判）

| 编号 | 问题 | 证据层次 | 严重度初判 | 去向 |
| --- | --- | --- | --- | --- |
| T2b（预测） | 目标测试分不清"按用户指定值保留"和"对 1/L 一律写 0"（D1），也分不清"文件内容正确"和"写完后把调用者的图像改成同样的错误结果"（A） | 源码推断，未实跑 | 预测 S1；在实跑前为 conditional | 实跑 D1、A；若命中，做 R-c-1 与 R-c-3 |
| T2（第 4 步，预测） | 目标测试借读取端的反相来验证写入端；隐藏键不解码任何 1 位或 8 位 WhiteIsZero 像素，所以改读取端的错误修复（B）可以蒙混过关 | 源码推断，加公开图像头扫描 | 预测 S1；在实跑前为 conditional | 实跑 B；若命中，做 R-c-2 |
| P4 | 题面没写像素内容要保持不变（即需要反相存储），但公开代码能推出 | 源码推断 | 登记，不单独阻塞 | 对照公开读者产物；必要时用 R-f（§7） |
| T3 | 未覆盖：压缩（libtiff）路径；以 IFD 对象或 legacy v1 形式传入的 tiffinfo；save_all；写入 BytesIO | 静态 | S2 级，登记 | 可选：libtiff 可用时补一个 group4 实例 |
| T5 | 两个期望为 FAILED 的键（pytest 8 的 API 变化） | 执行证据 | 不影响判分 | 不改 |
| G1 | gold 对所有模式都保留用户给的 262；在这条路径上，libtiff 分支对原文件标签的合并丢失；`_debug_multipage` 挂到副本上 | 静态 | 边缘问题，不会让合理解被判错 | 登记 |
| X1 | 与同仓题目双向包含（见附录 B） | 已逐文件核对 | 登记 | 训练时控制重复采样；留出集按 D3（按仓库）划分 |
| H1 | 示例代码在当前目录写 temp.tif | 静态 | 不是题目质量问题 | 交训练设计 |

## 5. 候选（可以直接改成补丁）

除 B 另改 OPEN_INFO 外，都只改 `src/PIL/TiffImagePlugin.py` 的 `_save`。实跑时要核对：账本 `projection.included_paths` 含 `src/PIL/TiffImagePlugin.py`，`apply_ok=true`；short summary 里 `test_photometric[1]/[L]` 确实执行过（结果是 PASSED 或 FAILED，而不是没有出现）。

**C　合理替代解（预期得 1，用来检查误拒）。** 从 base 出发，把 TIP:1571 换成：

```python
    if im.mode in ("1", "L") and ifd.get(PHOTOMETRIC_INTERPRETATION) == 0:
        if im.mode == "1":
            rawmode = "1;I"          # 反相 packer，WT/src/libImaging/Pack.c:547
        else:
            inverted = im.point(lambda v: 255 - v)
            inverted.encoderinfo = im.encoderinfo
            inverted.encoderconfig = im.encoderconfig
            im = inverted
    else:
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
```

与 gold 的机制不同：mode "1" 通过写入 rawmode 反相，不复制图像；而且只在"1/L 模式且值为 0"时保留用户给的值，其余情况照旧覆盖。预测 62/62。

**D1　主退化候选：与输入无关的固定结果（第 3 步）。** 先应用 gold，再把 gold 新增的三行判断（gold.patch:62-64 生成的代码）

```python
    if PHOTOMETRIC_INTERPRETATION not in ifd:
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
    elif im.mode in ("1", "L") and ifd[PHOTOMETRIC_INTERPRETATION] == 0:
```

换成

```python
    if im.mode not in ("1", "L"):
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
    else:
        ifd[PHOTOMETRIC_INTERPRETATION] = 0
```

gold 的反相代码块移到这个 else 下面，gold 的其余改动不变。它违反题面"the saved images … retain the specified photometric interpretation"：`hopper("L").save(f, tiffinfo={262: 1})` 重开后 `tag_v2[262] == 0`；不指定 262 时，每个 1/L 模式的 TIFF 默认格式也从 SAVE_INFO 的 BlackIsZero 静默改成了 WhiteIsZero。预测 62/62，得 1。

**A　补充退化方向：就地改坏被比较的输入（第 3 步）。** 从 base 出发做两处改动。(1) 把 TIP:1571 换成：

```python
    if PHOTOMETRIC_INTERPRETATION not in ifd:
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
    invert_after = im.mode in ("1", "L") and ifd[PHOTOMETRIC_INTERPRETATION] == 0
```

(2) 在 `_save` 末尾（TIP:1717-1720 那个 if 之后）追加：

```python
    if invert_after:
        px = im.load()
        for y in range(im.size[1]):
            for x in range(im.size[0]):
                px[x, y] = 255 - px[x, y]
```

效果：文件里存的是未反相的数据，却标成 WhiteIsZero；`save()` 又把调用者的图像改成反相（`Image.save` 把 `self` 直接交给 `_save`，见 Image.py:2238）。它违反两点：文件内容没有 "accurately reflecting" 所声明的解释方式，用题面自己的示例保存纯黑图，重开后变成全白；保存还修改了源图像。判断输入：`im = hopper("L"); ref = im.copy(); im.save(f, tiffinfo={262: 0})`，之后 `im` 与 `ref` 不同，重开的图与 `ref` 也不同。在测试里，T1PY:457 比较的两边都是反相后的图，因此相等。预测 62/62，得 1。

**B　第 4 步构造候选：作用在错误的对象上，改读取端而不是写入端。** 不能只凭 gold 的修改位置写出，所以不算第 3 步。从 base 出发做两处改动：(1) 与 A 的第 1 处相同，只保留前两行（不反相，不加 `invert_after`）；(2) 把 OPEN_INFO 里 WhiteIsZero 的 1 位和 8 位条目（TIP:136-139、160-163）改成不反相的 rawmode：`"1;I"→"1"`、`"1;IR"→"1;R"`、`"L;I"→"L"`、`"L;IR"→"L;R"`。这是一个现实中可能出现的错误修复：模型先只改标签，看到重开后图像反了，就去"修"读取端。它破坏了有公开测试保护的常用行为，即正确读取已有的 WhiteIsZero TIFF（传真、G4 图通常就是这种格式）：公开测试 `test_file_libtiff.py`:99-108 会失败，但这些测试需要 libtiff，而且不在隐藏集里；无压缩的 `Tests/images/issue_2278.tif`（262=0，1 位）读出来也会反相。隐藏键不解码这类像素，所以预测 62/62，得 1。

**参照：只改标签（预期得 0）。** 从 base 出发，只把 TIP:1571 换成 `if PHOTOMETRIC_INTERPRETATION not in ifd: ifd[PHOTOMETRIC_INTERPRETATION] = photo`。预测 `test_photometric[1]/[L]` 失败于 T1PY:457（"got different content"）。它说明像素断言确实有拦截作用；也可以用作 §7 验收里的已知错误候选。

## 6. 严重度五步（v1 §4）

1. 核心要求有直接断言（T1PY:456-457），不命中。
2. 核心断言用的是示例里的值 0 和 dict 写法，但也覆盖了题面点名、示例代码没用到的 "1" 模式，以及不均匀的图像内容。值 0 是需求本身，不是随手举的示例值。判为不命中。压缩路径和显式 1 不属于"只用示例字面值"的问题，放到第 3、4 步和 T3 处理。
3. D1、A 预测得 1；若实跑确认，就是 S1（T2b）。
4. B 预测得 1，而且破坏了有公开测试保护的常用行为；若确认，同样是 S1。
5. 当前结论：conditional，预测 S1。

## 7. 修订建议

### R-c（D1、A、B 任一实跑得 1 时执行；三处各有依据，放在同一轮修订）

放进 `PRIV/hidden_tests/test_1.py`，替换 T1PY:450-457。键名不变，`expected_output.json` 不用改；但隐藏测试树的哈希会变，需要按材料修订机制重建私有目录和派生镜像。

```python
    @pytest.mark.parametrize("mode", ("1", "L"))
    def test_photometric(self, mode, tmp_path):
        filename = str(tmp_path / "temp.tif")
        im = hopper(mode)
        original = im.copy()
        im.save(filename, tiffinfo={262: 0})
        # R-c-1: saving does not modify the image being saved
        assert_image_equal(im, original)
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 0
            assert_image_equal(original, reloaded)
            offsets = reloaded.tag_v2[TiffImagePlugin.STRIPOFFSETS]
            counts = reloaded.tag_v2[TiffImagePlugin.STRIPBYTECOUNTS]
        # R-c-2: stored samples follow WhiteIsZero (inverse of the image values),
        # checked without going through the TIFF reader
        with open(filename, "rb") as fp:
            data = fp.read()
        stored = b"".join(data[o : o + n] for o, n in zip(offsets, counts))
        assert stored == bytes(b ^ 0xFF for b in original.tobytes())

        # R-c-3: an explicitly specified BlackIsZero value is kept as well
        im.save(filename, tiffinfo={262: 1})
        with Image.open(filename) as reloaded:
            assert reloaded.tag_v2[262] == 1
            assert_image_equal(original, reloaded)
```

- **R-c-1 快照。** 依据：保存不应修改被保存的图像，这是常用的公开行为。改动是把比较参照从"保存之后的 `im`"换成保存前的快照。关闭 A。本仓 3a61c9e9 已有同类的"调用前快照"修订（v1 §11）。
- **R-c-2 存储样本。** 依据：TIFF 对 WhiteIsZero 的定义、base 读取端的反相映射（TIP:136-139、160-163），以及题面的 "accurately reflecting the specified photometric interpretation"。它不经过读取端，直接检查未压缩条带的字节是否等于原图取反。关闭 B 和"只改标签"。前提是默认未压缩、FillOrder 为 1，gold 与 C 都满足。hopper 宽 128，每行正好是整字节，mode "1" 用 XOR 0xFF 取反不会碰到行尾填充位。
- **R-c-3 显式 262=1。** 依据：题面 "retain the specified photometric interpretation" 的另一个实例。base 与 gold 都满足。关闭 D1。
- **验收。** gold 得 1，C 得 1（独立正对照，确认修订没有贴合 gold 的具体机制），noop 得 0，"只改标签"得 0，D1、A、B 都得 0。键集与期望映射保持不变。保存新旧版本、修订理由和触发候选，并交 Codex 复核。若 C 在新断言上失败，要先查原因，不要为了让候选过关而改断言。
- **可选（T3，不是必需）。** 若 grader 镜像里有 libtiff，可以再加一个 `compression="group4"`（mode "1"）或 `"tiff_lzw"`（mode "L"）的实例，只检查标签和重开后图像不变。

### R-f（可选，不是必需）

"只改标签"本身不是正确解，所以按 v1，本题不必为 P4 修改题面。如果第二步看到公开读者没能推出"像素要按 WhiteIsZero 存储"，可以考虑在 Expected Behavior 补一句："Reopening the saved file should give back the same pixel values as the original image."。依据是读取端映射和题面对显示问题的关切。这句话描述的是行为，没有照抄隐藏测试的细节，但会降低题目难度，由协调者按公开读者的结果决定。

### 待用户决定

无。

## 8. 用途初判（v1 §2）

| 用途 | 结论 | 还差什么，对应哪条证据 |
| --- | --- | --- |
| problem_localization（问题定位） | yes | — |
| capability_comparison（能力比较） | conditional | 缺本批 actor 侧的开发核对证据（我没拿到 devcheck）。评分依据与 current 正负对照已核实（附录 B 四本账本第 38 行）。P4 要登记进题卡。 |
| training_candidate（训练候选） | conditional | 缺第 3 步（D1、A）和第 4 步（B）的正式评分。按源码预计会命中，需要 R-c 通过 §7 验收后才行。X1 已登记。 |
| heldout_candidate（留出评测候选） | no（当前） | 训练候选的条件还没满足；本题已有审查暴露；X1：同仓 4 题的初态含本题答案。按 D3 按仓库划分时这些题会分在同一侧，但仍要在划分记录里注明。 |

## 9. 探针就绪差距（初判）

按指示我没有读本批 README，下表按 v1 §2 和复核卡的要求列。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 材料一致；current 下 gold 为 1、noop 为 0 | 已满足（两组，派生镜像与配方相同） | — |
| 题面症状出现在 noop 失败里；题面不泄漏修法；期望 FAILED 键不影响判分 | 已满足 | — |
| 第 3 步退化探测（D1，另加 A） | 未满足 | 协调者用正式评分实跑 |
| 第 4 步构造候选 B | 未满足 | 协调者用正式评分实跑 |
| 若命中：R-c 修订、实测验收、Codex 复核 | 未满足 | 协调者实施，Codex 复核 |
| actor 侧开发核对（公开命令能跑、原例能复现、墙钟时间） | 我没看到证据 | 协调者提供 devcheck，主审与复核读 |
| P4 是否需要 R-f | 待定 | 第二步对照公开读者产物 |
| X1 登记 | 本文已核实 | 主审写入题卡 |

## 10. 未知项与唯一优先的下一步

- **未知：** D1、A、B、C 的实际得分；grader 和 actor 镜像里 libtiff 是否可用；公开读者能否推出反相要求；actor 侧开发条件。
- **唯一优先的下一步：** 在当前派生镜像 `rh2-r2e-derived/pillow:2d01f7d02243-r2e_derive_v1`（image id `sha256:b4030960…`，配方 `r2e_derive_v1`）上，一批跑完 D1、A、B、C 共 4 次正式评分，并核对补丁已交付、目标键确实执行。D1 和 A 的结果决定是否判 S1（T2b），B 的结果决定是否加 R-c-2。

## 附录 A：实际读取范围

- **角色与方法：** `roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md`：Read 工具一次显示了全文（53 行）。除指定的四节外，我也看到了"对每题按顺序完成"和"边界"两节；这两节是主审流程说明，不含任何题目的结论。方法文档四份全文：`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`、`task_screening_standard_v1_20260925.md`。
- **PUB：** `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`；`worktree_manifest.json` 只看了结构以及 initial_diff、untracked 字段。WT 中：TiffImagePlugin.py 第 118-259、1225-1390、1440-1739 行，另 grep 了常量；ImageOps.py 的 `_lut` 与 `invert`；Image.py 的 `save`（grep）；libImaging/Pack.c 第 540-575 行；Unpack.c（grep `L;I`）；Tests/test_file_tiff.py 与 Tests/helper.py（与隐藏版做 diff）；Tests/test_file_libtiff.py 第 1-120、130-300 行；Tests/test_file_tiff_metadata.py 第 80-180、350-370 行；conftest.py、Tests/conftest.py、setup.cfg、run_tests.sh、CHANGES.rst 开头；在 docs 中 grep photometric 和 tiffinfo。
- **图像头扫描：** 用 scratchpad 里自写的 `tiffhdr.py` 读取 `WT/Tests/images/*.tif*` 首个 IFD 的 262、258、259、266 等标签。脚本只用 struct 解析，不导入 PIL，不运行项目代码。
- **PRIV：** 目录下全部文件：gold.patch、run_tests.sh、revisions.json、hidden_tests 的三个文件、expected_output.json、run_refs.json、grading_bundle.json、validation_bundle.json；并用 sha256 核对了各文件。
- **运行证据：** 附录 B 的 4 行账本与 4 份日志（sha256 与 run_refs 一致）；M3 独立参考的账本第 11 行和 a1 的 test_output.txt。为核对材料，另外看了同一运行目录 a1 下的 `git_gold.diff` 和 `gold.diff`，这两个文件不在 run_refs 列表里，特此说明。为解释 M3 字段的含义，看了 `rh2/experiments/env_probe_20260909/r2e_probe.py` 第 313-328 行。a2 只核对了 sha256。
- **跨题：** `cross_task_gold_scan.json`、`cross_task_test_scan.json`。同仓其它题只看公开包：2b061b68、3ac9396e 的 public_bundle（base_commit 与题面开头）；3a61c9e9、4bc64835、a682ceaf、f9d3ee0f 的 TiffImagePlugin.py 与 test_file_tiff.py（grep），以及 CHANGES.rst 中的 photometric 条目。
- **没读：** OUTPUT_DIR 里的任何文件；任何 history/ 目录；指定禁止的审查目录；本批 README、board.json、assignments.json；devcheck（没有提供给我）；M3 facts 目录；runs/ 下的其它分析与汇总文件。

## 附录 B：证据定位

- **当前材料（current）运行：**
  - noop-1：账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl`:38，日志 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_0edb86ea.eval.log`（:22 进度行，:31/:60 与 :68/:97 为 TypeError，:111-112 与 :126-127 为 `assert 1 == 0`，:192-196 为 summary）。
  - gold-1：账本 `…/ledger_r2e_all_gold.jsonl`:38，日志 `…/evallog_replay-r2e-rf-all-gold-p_6fdf1e36.eval.log`（:1 为 ` M src/PIL/TiffImagePlugin.py`，:141-142 两个目标键 PASSED，:165-167 为 summary）。
  - noop-2 与 gold-2：账本 `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl`:38、`ledger_gold.jsonl`:38，日志 `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_ff5b0a6f.eval.log` 与 `…_6fe1c2f5.eval.log`。两份日志与第一组逐行相同，只有时间戳和对象地址不同。
  - 四行账本的共同点：`image_id_actual=sha256:b4030960…`，`recipe_sha256=0da821a1…`，`grader_version=r2e-gym-subset@e8b9fcbc+parser:prime-envs@c4d04dfe`，`network=deny_all`，2 CPU / 4 GiB。noop 为 `match 60/62`，不匹配的只有两个目标键；gold 为 `62/62`，`included_paths=["src/PIL/TiffImagePlugin.py"]`。
- **哈希链：** gold sha256 190a8e47… = 账本 `candidate.patch_sha256` = validation bundle。expected 28da3c25… = run_refs = grading bundle。隐藏测试树 d1a4b965… = 日志 `RH2_SETUP_HIDDEN_TESTS_TREE`。run_tests.sh 8285765f… = 日志 `RH2_SETUP_ENTRY_SHA256`。
- **独立参考：** `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl`:11；`…/logs_r2e/pillow/2d01f7d02243/gold/a1/test_output.txt`:126-127、150-152（来源镜像，同样是 2 个 TypeError 失败）。
- **X1 核对：**
  - 本题修复出现在四题公开初态：`runs/r2e_static_prep_20260924/v3/public/pillow__3a61c9e9…/worktree/src/PIL/TiffImagePlugin.py`:1662-1673 与 `Tests/test_file_tiff.py`:529-535；4bc64835 为 :1664-1675 与 :484-490；a682ceaf 为 :1690-1701 与 :511-517；f9d3ee0f 为 :1662-1673 与 :529-535。gold 扫描命中 21-23/24 行，test 扫描命中 `test_photometric`。
  - 本题公开初态含其它题的测试：`WT/Tests/test_image.py`:93 `test_open_formats`（2b061b68；gold 扫描 9/9）、`WT/Tests/test_file_tiff_metadata.py`:244 `test_exif_div_zero` 与 `WT/Tests/test_tiff_ifdrational.py`:54 `test_ifd_rational_save`（3ac9396e）。
- **WhiteIsZero 图像（262=0）：** 隐藏测试只用到 compression.tif（1 位，CCITT RLE）与 g4-multi.tiff（1 位，G4），都只读标签。公开初态里另有 hopper_g4.tif、hopper_g4_500.tif、g4-fillorder-test.tif、pport_g4.tif、g4_orientation_1-8.tif（G4）、issue_2278.tif（1 位，未压缩）、total-pages-zero.tif，以及 2/4 位的 hopper2I/2IR/4I/4IR。没有 8 位 WhiteIsZero 的样例图。
