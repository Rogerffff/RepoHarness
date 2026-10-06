# pillow__3a61c9e9：静态审查短卡（2026-09-25，私有主审）

**题目**：Pillow 9.2.0.dev0（base `355820742bc2`）。`Image.remap_palette` 处理 RGBA 调色板时，按 RGB 每项 3 字节取项，也按 RGB 写回。结果是恒等映射后 `palette.palette` 从 1024 字节变成 768 字节，alpha 丢失。**建议用途**：development_diagnostic，作为静态候选；这不代表训练或评测已获批准。

**关键映射**（完整表见 analysis_before_history.md §3）

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据 / 下一验证 |
| --- | --- | --- | --- | --- |
| RGBA 恒等映射后 `palette.palette` 相等 | 题面示例与 Expected | `TestImage.test_remap_palette`，`test_1.py:614` | 覆盖（与示例逐字相同） | noop 两次都在 `:614` 失败；gold 两次 71/71；M3 两次 |
| 恒等映射不改变像素索引 | 公开 `Tests/test_image.py:604-605` | `:605`、`:613` 的 `assert_image_equal` | 覆盖 | 同上 |
| 非恒等 RGBA 重排按 4 字节整项搬动 | 题面 "does not correctly handle RGBA palette modes" | 无 | 缺失 | W3 与 C3 |
| C 层保留 alpha | docstring "reorder the palette"、C 层语义 | 无（只比较索引） | 缺失 | W2 与 C2/C3 |
| GIF 显式传入 RGB source 的路径保持不变 | `GifImagePlugin.py:509-536` | 无（隐藏测试不保存 GIF） | 缺失 | W1 与 C4 |
| 非 L/P 模式抛 ValueError；transparency 随映射改写 | 公开 `:607-624` | `:616-619`、`test_remap_palette_transparency` | 覆盖 | — |

**八方面**：
- **已查**：公开需求、材料与初态、测试映射、误拒、gold 与回归、开发条件（DEV 真实链加历史探针）、交付边界、题目关系（逐行比对了同仓其它题的公开包）。
- **未查**：实际渲染给模型的消息、真实模型求解、PNG 等其它插件、并发复用。
- **按 R2E 通用问题处理**：`.venv` 对 agent 可写、根 conftest 以插件加载 `Tests.helper`。

**问题与证据层次**
1. **测试偏宽**（清单 25/32，静态推断）：隐藏测试等于公开 `Tests/test_image.py` 加上题面示例这 8 行。只修 Python 层的 W2、对恒等映射直接返回副本的 W3，预计都能得 1。
2. **未测回归**（26，静态推断）：W1 让显式传入的 RGB `source_palette` 也按图自身的 RGBA 模式、用 4 字节步长读取，预计得 1，但会破坏 GIF 保存。
3. **题间包含**（5，已核对原文）：
   - 本题 gold 13/13 行和测试块逐字出现在 `pillow__f9d3ee0f…` 的初态里。
   - `pillow__a682ceaf…` 含 10/13 行和测试块，机械比对漏报了它。
   - 本题初态包含 2b061b68、2d01f7d0、4bc64835 的修复。
   - 划分训练/留出时，这些题要放在同一侧。
4. **低优先**：
   - 评分证据在镜像 `0fb6caf2` 上，actor 核对却在 `305f39cc` 上。
   - gold 在 GIF `palette=` 分支里，Python 调色板的 mode 与字节格式对不上（静态推断）。
5. **环境**：历史的环境资格结论确认成立。旧 issue "提示与无 pip 矛盾"已随 v3 提示过时。没有发现误拒，题内没有泄漏。

**建议**：
- 记录 `scope=static_review`，`state=needs_review`。理由：静态候选待 actor 验证；测试偏宽待 CPU 反例确认。这不是题意争议。
- 如果要作训练 reward，可以考虑补充有公开依据的断言：非恒等 RGBA 映射、C 层 alpha、GIF 往返。这属于测试标准修订，需要用户决定。
- 目前还没有独立 reviewer。

**唯一优先的下一步**：用正式评分代码实跑 C1、W1、W2（W3 可选），同一批里在 `305f39cc` 上补跑 noop 和 gold 各一次；同时在私有容器里跑附录中的命令。

## 实跑候选（都只改 `src/PIL/Image.py` 的 `Image.remap_palette`）

- **C1（对照，合理替代解）**：
  - 改法：
    1. 开头设 `palette_mode = "RGB"`、`bands = 3`。
    2. 只有 `source_palette is None` 且 `self.mode == "P"` 时，先 `self.load()`，再设 `palette_mode = self.im.getpalettemode()`、`bands = len(palette_mode)`、`source_palette = bytes(self.getpalette(None))`；循环按 `bands` 步长取项。
    3. 映射段保持 base 的 `"RGB;L"` 写法。
    4. 写回时，先设 `rgb = b"".join(palette_bytes[i:i + 3] for i in range(0, len(palette_bytes), bands))`，执行 `m_im.putpalette(rgb + (768 - len(rgb)) * b"\x00")`。
    5. 若 `bands == 4`，再执行 `m_im.im.putpalettealphas(bytes(palette_bytes[3::4]))`。
    6. 最后设 `m_im.palette = ImagePalette.ImagePalette(palette_mode, palette=palette_bytes)`。
  - 预期：1（71/71），没有不符键。如果得 0，先查 `TestImage.test_remap_palette`；得 0 说明测试含有无依据的实现约束。
- **W1（较自然的错误实现）**：
  - 改法：在 gold 基础上，把模式判定从 `if source_palette is None:` 块内移到块前，只对 P 模式执行 `self.load(); palette_mode = self.im.getpalettemode(); bands = 4 if palette_mode == "RGBA" else 3`。块内的 P 分支只保留 `source_palette = self.im.getpalette(palette_mode, palette_mode)`。这样显式传入的 `source_palette` 也按这个步长读取。
  - 预期：1（71/71），没有不符键；但 C4 会输出 False 或读回时报错。
- **W2（部分实现：只修 Python 层）**：
  - 改法：在 gold 基础上，只把写回 C 层的两行改成 RGB：`new_palette_bytes = rgb + (768 - len(rgb)) * b"\x00"`，其中 `rgb` 同 C1；再执行 `m_im.putpalette(new_palette_bytes)`（默认 rawmode 为 RGB）。gold 的其余部分保持不变，包括最后的 `m_im.palette = ImagePalette.ImagePalette(palette_mode, palette=palette_bytes)`。
  - 预期：1，没有不符键；C2 中 `getpalette_None_len` 为 1024 768、`rgba_render_equal` 为 False，C3 的 render 为 False。
- **W3（可选，硬编码）**：
  - 改法：在 base 的模式检查之后插入 `if self.mode == "P" and source_palette is None and list(dest_map) == list(range(256)): return self.copy()`，其余保持 base。
  - 预期：1，没有不符键；C3 的输出与 base 相同。

**判读方式**：如果 W1、W2、W3 得 1，偏宽成立，作为清单第 25、26 项的具体反例记录。原始 reward 保留，不按失败键自动免责。

## 附录：私有容器命令与预期输出

**运行方式**：与 private_gold 相同。在本题派生镜像（`305f39cc…`）的一次性容器里运行，身份用 root 或 agent 都可以，不联网。先在 `/testbed` 执行 `git apply <候选>.patch`，再依次运行 C2、C3、C4（原文来自 public_read.md §4，在 DEV 里分别对应 pr1_1_cmd、pr3_2_cmd、pr4_3_cmd）。

**需要跑的代码状态**：base 和 gold 已经有结果（见 DEV `orig/captures/` 和 `private_gold/private_control.json`），只需要跑 C1、W1、W2、W3。另外：
- 每个候选再跑一次 `python -m pytest -p no:cacheprovider --color=no -rfE Tests/test_image.py`。base 上的结果是 71 passed / 1 skipped。
- W1 再跑一次 `python -m pytest -p no:cacheprovider --color=no -rfE Tests/test_file_gif.py`，用来看公开测试能不能自己发现这个回归。base 和 gold 上都是 73 passed / 2 skipped；W1 下的结果未知，取决于 quantize 之后索引有没有空洞。

```bash
# C2：恒等映射（题面示例加上 C 层检查）
cd /testbed && python - <<'EOF'
from PIL import Image
im = Image.new("P", (256, 1))
for x in range(256):
    im.putpixel((x, 0), x)
im.putpalette(list(range(256)) * 4, "RGBA")
r = im.remap_palette(list(range(256)))
print("same_palette_bytes:", im.palette.palette == r.palette.palette)
print("palette_mode:", im.palette.mode, r.palette.mode)
print("palette_len:", len(im.palette.palette), len(r.palette.palette))
print("getpalette_None_len:", len(im.getpalette(None)), len(r.getpalette(None)))
print("rgba_render_equal:", im.convert("RGBA").tobytes() == r.convert("RGBA").tobytes())
print("indices_equal:", im.tobytes() == r.tobytes())
EOF
# C3：非恒等交换
cd /testbed && python - <<'EOF'
from PIL import Image
im = Image.new("P", (2, 1))
im.putpixel((1, 0), 1)
im.putpalette((10, 20, 30, 40, 50, 60, 70, 80), "RGBA")
s = im.remap_palette([1, 0])
print("swap_mode:", s.palette.mode)
print("swap_first_bytes:", list(s.palette.palette)[:8])
print("swap_indices:", list(s.getdata()))
print("swap_render_equal:", list(im.convert("RGBA").getdata()) == list(s.convert("RGBA").getdata()))
EOF
# C4：GIF 往返（RGBA 调色板 + 稀疏索引，触发 optimize 以显式 RGB source 调用 remap_palette）
cd /testbed && python - <<'EOF'
from io import BytesIO
from PIL import Image
im = Image.new("P", (4, 1))
for x, v in enumerate((10, 20, 30, 40)):
    im.putpixel((x, 0), v)
im.putpalette([c for i in range(256) for c in (i, 255 - i, i // 2, 128)], "RGBA")
buf = BytesIO()
im.save(buf, "GIF")
buf.seek(0)
with Image.open(buf) as reloaded:
    print("gif_rgb_equal:", list(reloaded.convert("RGB").getdata()) == list(im.convert("RGB").getdata()))
EOF
```

| 代码状态 | C2（六行依次） | C3（四行依次） | C4 |
| --- | --- | --- | --- |
| base（已测） | False；RGBA RGB；1024 768；1024 768；False；True | RGB；[50, 60, 70, 10, 20, 30]；[1, 0]；False | True |
| gold（已测） | True；RGBA RGBA；1024 1024；1024 1024；True；True | RGBA；[50, 60, 70, 80, 10, 20, 30, 40]；[1, 0]；True | True |
| C1 | 同 gold | 同 gold | True |
| W1 | 同 gold | 同 gold | **False，或读回时报错**：768 字节的 RGB 源被按 4 字节步长读取，写进 GIF 头的是 16 字节；补齐后变成 25 字节，而头部声明的是 8 项（24 字节），后面的数据会错位 |
| W2 | True；RGBA RGBA；1024 1024；**1024 768**；**False**；True | RGBA；[50, 60, 70, 80, 10, 20, 30, 40]；[1, 0]；**False** | True |
| W3 | 同 gold | 同 base | True |
