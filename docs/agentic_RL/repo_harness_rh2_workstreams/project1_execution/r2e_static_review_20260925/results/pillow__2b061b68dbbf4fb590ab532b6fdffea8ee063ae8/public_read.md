# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：公开读者记录

- 角色：R2E 公开读者（静态审查，不解题），2026-09-25，干净上下文；全程只读角色卡与本题公开包，未接触任何私有材料。
- 路径约定：顶层文件（`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`）相对本题公开包目录 `runs/r2e_static_prep_20260924/v2/public/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/`；`Tests/…`、`src/…`、`docs/…` 以及根目录文件都在 `worktree/` 下，也就是解题者在 `/testbed` 看到的路径。`Image.py` 指 `src/PIL/Image.py`，`ImageShow.py` 指 `src/PIL/ImageShow.py`。
- 标注：**推断**表示由公开材料推出、未运行验证；**一般知识**表示依据对 pytest / CPython 的通用了解，本环境未核实。所有命令均为**建议，未执行**。

## 要点

1. 题面以"`Image.open` 已经引入 `formats` 参数"为前提，但 base 的签名只有 `open(fp, mode="r")`（`Image.py:2839`），仓库文档、`CHANGES.rst` 和公开测试里都找不到这个参数。据此推断，真正要做的是**给 `Image.open` 增加 `formats` 参数**。
2. 题面报告的 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>` 在 base 的 Pillow 源码中找不到来源。它与 pytest 拒绝 `pytest.warns(None)` 时的报错逐字一致（一般知识）。公开测试 `Tests/test_image.py` 中正好有一处"保存"（第 601 行）和一处"`show()`"（第 768 行）使用 `pytest.warns(None …)`，写法与题面示例吻合。据此推断，题面把测试工具层的报错误当成了 Pillow 缺陷。
3. `formats` 的具体语义公开材料没有约定；题面示例（用 `formats=['JPEG']` 打开 PNG，并期望成功）还与"限制格式"的描述互相矛盾。

## 1. 需求表

| 编号 | 需求：要改变的行为（N），或应保留的行为（K） | 明确程度 | 依据 |
|---|---|---|---|
| N1 | `Image.open` 接受名为 `formats` 的参数，示例取值为由大写格式名组成的 list：`['JPEG']` | 题面明示（标题、描述首句、示例）；但题面称其"已引入"，与 base 不符 | `user_prompt.txt`；`Image.py:2839`。全树检索 `formats=` 只命中无关的 `features.pilinfo(supported_formats=…)`（`src/PIL/features.py:216`、`Tests/conftest.py:9`） |
| N2 | `formats` 用来"restrict the supported image formats"，即限制识别时考虑的格式 | 明示，但只有这一句，没说明不匹配时怎么处理 | `user_prompt.txt` 描述首句 |
| N3 | 用 `formats=['JPEG']` 打开 `hopper.png` 时"should work without issues" | 明示，但按自然理解与 N2 冲突：`Tests/images/hopper.png` 是真 PNG（`file` 输出为 "PNG image data, 128 x 128, 8-bit/color RGB"） | `user_prompt.txt` Expected Behavior 第 1 条 |
| N4 | `save` 和 `show()` 不应抛 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`，应"妥善处理警告" | 明示；但 base 的 `Image.save`（`Image.py:2073-2154`）和 `Image.show`（`Image.py:2177-2204`）不会产生这个错误，见 §3.2 | `user_prompt.txt` Actual Behavior |
| N5 | "像 `show()` 这样的弃用方法应触发适当警告" | 明示，但与现有设计冲突：base 中无参 `show()` 并未弃用。已弃用的只有 `command` 参数（`Image.py:2197-2202`）和 `Image._showxv`（`Image.py:3157-3167`）。公开测试断言无参 `show()` 不发任何警告 | `docs/deprecations.rst:15-30`；`docs/releasenotes/7.2.0.rst` 的 Deprecations 节；`Tests/test_image.py:763-773` |
| K1 | 不传 `formats` 时识别流程不变：`preinit()` 只注册 BMP/GIF/JPEG/PPM/PNG；按注册顺序 `ID` 依次调用 accept 与 factory；首轮失败后调用 `init()` 载入全部插件，再试一轮（`init()` 只在第一次调用时返回 1） | 可从公开仓库推知（向后兼容） | `Image.py:347-390`、`393-412`、`2887-2920` |
| K2 | 识别失败时：关闭由 `open` 自己打开的文件；把 accept 返回的字符串作为 `UserWarning` 发出；再抛 `UnidentifiedImageError("cannot identify image file …")` | 可推知 | `Image.py:2926-2932`；`Tests/test_image.py:97-102`；`Tests/test_file_webp.py:23-31`（WEBP 不受支持时应同时出现 `UserWarning` 和 `OSError`） |
| K3 | `mode` 仍是第二个位置参数，不等于 `"r"` 时抛 `ValueError`；传入 `StringIO` 时抛 `ValueError`；支持 `pathlib.Path` | 可推知 | `Image.py:2862-2875`；`Tests/test_image.py:104-106`（以位置参数调用 `Image.open("filename", "bad mode")`）、`108-110`、`112-126` |
| K4 | 保存时不多发警告；无参 `show()` 不发警告，`show(command=…)` 发 `DeprecationWarning` | 可推知（公开测试的意图） | `Tests/test_image.py:593-601`、`763-773`；`Tests/test_file_jpeg.py:660-668` |
| K5 | 格式名的取值空间：`register_open` 把 ID 一律转成大写（`Image.py:3048`），ID 来自插件类的 `format` 属性，如 `"JPEG"`（`src/PIL/JpegImagePlugin.py:336`）、`"PNG"`（`src/PIL/PngImagePlugin.py:662`）、`"TIFF"`（`src/PIL/TiffImagePlugin.py:973`）；`python -m PIL` 通过 `pilinfo` 列出全部 `Image.ID`（`src/PIL/__main__.py`、`src/PIL/features.py:280-290`） | 可推知（`formats` 中"格式名"最自然的含义） | 同左 |
| A1 | `formats` 的精确语义：严格限制还是先试后回退、空列表如何处理、大小写、未知格式名、非 list 类型、尝试顺序、报错类型 | 存在多种合理解释 | 见 §2 |

## 2. 合理实现范围

公开材料只确定了两点：参数名是 `formats`，示例取值是由大写格式名组成的 list。以下各项都没有约定，列出的做法在公开依据下都说得通。如果隐藏测试只认其中一种，其它合理实现就会被误判；这里记录的是风险，不是结论。

1. **核心语义（分歧最大）**
   - 严格限制：只尝试 `formats` 中列出的格式，全部不匹配就走现有失败路径，抛 `UnidentifiedImageError`。这符合 "restrict" 一词，但会让题面示例（PNG 配 `['JPEG']`）失败。
   - 先试后回退：先试列出的格式，再试其余格式。这能让示例的字面期望成立，但不符合 "restrict"。
   - 两种信号在题面中同时出现，公开材料无法判定哪一种被期望。**我想不出能同时满足两者的实现**，如实保留为开放问题。
2. **签名位置**：作为第三个参数（可按位置或关键字传入，默认 `None`），或设为仅关键字参数，都合理。但不能放到 `mode` 前面（K3）。若设为仅关键字参数，`Image.open(fp, "r", [...])` 这类按位置传入的调用会被拒绝；公开材料里既没有这种调用，也没有反例。
3. **默认值与空值**：`None` 表示"所有格式"最自然。`[]` 应解释为"一个都不试"（从而抛 `UnidentifiedImageError`）还是等同于"所有格式"，没有约定。
4. **类型与校验**：list 是明确可接受的。tuple 或其它可迭代对象是否接受，没有约定；传入字符串 `"JPEG"` 时是报错（`TypeError` 或 `ValueError`）还是当作单个格式处理，也没有约定。若实现不检查类型，字符串会被逐字符迭代，这属于实现疏漏。
5. **大小写**：注册 ID 一律为大写（`Image.py:3048`），示例也用大写。是否对用户输入做大小写归一，没有约定。
6. **未知或尚未注册的格式名**：可以忽略、报错（`KeyError` 或 `ValueError`），也可以先调用 `init()` 再判断，都没有约定。base 的 `_open_core` 只吞掉 `SyntaxError, IndexError, TypeError, struct.error`（`Image.py:2905`）；其它异常，包括直接用 `OPEN[i]` 查找未注册格式时的 `KeyError`，会在关闭文件后原样抛出（`Image.py:2910-2913`）。这是读代码就能发现的问题，不算题面缺陷。
7. **插件加载时机**：`preinit()` 之后只注册了 5 种格式。请求 `TIFF` 等格式时，沿用"首轮失败后 `init()` 再试"，或者在进入循环前按需调用 `init()`，都合理，但必须在某处触发 `init()`。否则在新进程里用 `formats=['TIFF']` 打开 TIFF 会失败（推断）。
8. **尝试顺序**：按用户列表的顺序还是按注册顺序 `ID`，没有约定。只有当多个列出格式的 accept 同时接受同一文件头时，两种顺序的结果才会不同。
9. **被排除格式的 accept 警告**：严格限制时，是否仍调用被排除格式的 accept，以及是否仍发出 K2 所述的 `UserWarning`，没有约定。
10. **结果格式不在列表中**：`jpeg_factory` 遇到多帧 MPO 文件时会返回 `MpoImageFile`（`src/PIL/JpegImagePlugin.py:780-798`），因此 `formats=['JPEG']` 可能得到 `im.format == "MPO"`。是否需要额外过滤，没有约定。
11. **附带改动**：更新 docstring、`docs/reference/Image.rst:50`（`.. autofunction:: open`）和 release notes，或让内部调用方改为传入 `formats`，题面都没有要求，做不做都可以。
12. **警告相关部分**：从公开证据看，合理的解法不需要改动 `save`、`show` 或任何 `warnings.warn` 调用。若给无参 `show()` 加弃用警告，反而会与 `Tests/test_image.py:763-770` 和 `docs/deprecations.rst` 冲突。题面报告的 TypeError 无法通过修改库代码消除，见 §3.2。

## 3. 题面质量与初态线索

### 3.1 是否直接给出或强烈暗示修法

- 题面没有给出实现代码。它提供的是接口形状（关键字 `formats`，取值为大写格式名 list），属于需求描述，不算泄露答案。
- 反而存在误导：标题和 Actual Behavior 把问题定位为"处理警告时出现 TypeError"，而 base 实际缺少的是 `formats` 参数本身。照字面去排查 `Image.py` 中的 `warnings.warn` 调用（第 110、115、950、1006、1033、2198、2832、2929、3163、3244、3250、3371 行），找不到任何能产生该错误的位置。

### 3.2 题面描述的报错和行为能否从 base 源码读出

- `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`：**不能**。
  - 在整个工作树中检索 "derived from Warning"，零命中。
  - `Image.save` 不涉及警告类别；`Image.show` 只在 `command is not None` 时发出 `DeprecationWarning`。
  - CPython 的 `warnings.warn` 在 `category=None` 时默认使用 `UserWarning`；类别不合法时的报错文字是 "category must be a Warning subclass"，与题面不同（一般知识）。
- 这段报错与 pytest 在 `pytest.warns(None)` 下抛出的错误逐字一致（一般知识）：pytest 7 弃用了传入 `None`，8 系列移除了支持，此后 `WarningsChecker` 对 `None` 抛出 `TypeError("exceptions must be derived from Warning, not %s" % type(None))`。它是异常而不是警告，所以 `run_tests.sh` 中的 `-W ignore` 挡不住。镜像 `.venv` 中的 pytest 版本在公开材料里看不到：`requirements.txt:10` 的 `pytest` 没有固定版本，`install.sh` 也未纳入公开包。
- 公开测试中共有 26 处 `pytest.warns(None …)`（`grep -rn 'warns(None' Tests/`）。其中 `Tests/test_image.py` 的两处与题面的两条症状一一对应：
  - 保存：`test_no_resource_warning_on_save`（`Tests/test_image.py:593-601`）打开 `Tests/images/hopper.png`，再用 `pytest.warns(None, im.save, temp_file)` 保存为 `temp.jpg`。这与示例"打开 hopper.png、保存为 .jpg"是同一个写法。
  - `show()`：`test_show_deprecation` 第 768 行 `with pytest.warns(None) as raised:` 包住了 `im.show()`（`Tests/test_image.py:763-773`）。
  - `Tests/test_file_jpeg.py:666` 的 `test_exif_x_resolution` 也是"保存 + `pytest.warns(None)`"。
- 推断：Actual Behavior 来自在较新 pytest 下运行含 `pytest.warns(None)` 的测试所得的输出，并非 Pillow 缺陷。如果镜像中的 pytest 确实拒绝 `None`，这些用例在 base 上和任何合法修复之后都会报同样的错。

### 3.3 题面示例在 base 的接口下是否说得通

- **说不通**。在 base 上执行示例，第一步 `Image.open('hopper.png', formats=['JPEG'])` 就会因为未知关键字抛出 `TypeError: open() got an unexpected keyword argument 'formats'`（签名见 `Image.py:2839`，推断），根本走不到 `save` / `show`。报错位置与题面描述的不同。
- **路径**：`/testbed` 根目录下没有 `hopper.png`，文件在 `Tests/images/hopper.png`。即使 `formats` 被接受，在 `/testbed` 下原样运行示例也会得到 `FileNotFoundError`（推断）。
- **内在矛盾**：`hopper.png` 是 PNG，按"限制"语义，`formats=['JPEG']` 应拒绝它（走现有失败路径 `Image.py:2926-2932`，抛 `UnidentifiedImageError`），题面却期望 "work without issues"。
- **`image.show()` 在容器中的表现**：Linux 下 `ImageShow` 只有找到 `display` / `eog` / `xv` 命令时才注册查看器（`ImageShow.py:223-229`）；没有查看器时 `show()` 静默返回 0（`ImageShow.py:55-58`）；有查看器时会启动外部进程（`ImageShow.py:178-189`）。因此示例中的 `show()` 在容器里既演示不了"警告"，还可能带来副作用。公开测试用 `monkeypatch.setattr(Image, "_show", …)` 绕开了这一点（`Tests/test_image.py:764`）。
- **"deprecated methods like `show()`"** 与 base 不符，见 N5。

### 3.4 `public_hints` 分类

提示原文见 `public_bundle.json` 的 `row.public_hints`。

| 提示（摘要） | 类别 | 与本题实际情况 | 对合法解法的影响 |
|---|---|---|---|
| "fixing a real GitHub issue … /testbed" | 题目需求 + 环境事实（工作目录） | `/testbed` 与 brief 一致；但题面由模型自动生成，不是原始 issue | 可能让解题者过度相信题面中的错误细节（TypeError、`show()` 已弃用） |
| "pre-activated conda env named `testbed` … `pip` … already point at it" | 环境事实声明 | 不符：`python` 实际指向 `/testbed/.venv/bin/python`（3.9.21），没有 pip / pip3 / uv，也不能出网 | 无法安装或更换 pytest，因此在环境内无法绕开 `pytest.warns(None)` 的问题；本题只需改 Python 代码，不需要装包 |
| "Explore the code, find the root cause, and edit NON-TEST source files" | 操作指令 + 题目需求 | — | 真正要改的是 `Image.py` 中的 `open`（推断） |
| "Do NOT modify test files: grading resets the test files … never count" | 前半句是操作指令；后半句是评分机制声明 | 后半句不是本来源的实际机制（据角色卡）；`run_tests.sh` 跑的是隐藏目录 `r2e_tests` | 题面报告的 TypeError 只能靠以下方式"消除"：改测试代码；改根目录 `conftest.py` 或 `Tests/helper.py`（`conftest.py:1` 把 `Tests.helper` 作为 pytest 插件加载，推断对 `r2e_tests` 同样生效）；或在库代码里给 pytest 打补丁。这些都不是合法修复。该指令把它们排除在外是对的，但照字面追求"消除 TypeError"的解题者可能在这里浪费时间，甚至越界修改。若评分不重置 `conftest.py` 和 `Tests/helper.py`，这里就存在一条旁路（推断） |
| "keep runs narrow (a single test file or module)" | 操作指令 | 与 2 CPU / 4 GiB 的资源匹配 | 没有负面影响；但若 pytest 拒绝 `None`，即使只跑单个文件也会看到与本题无关的失败（见 §4） |
| "reply with a short summary and stop calling tools" | 操作指令 | — | 无 |

### 3.5 初态线索与调查入口

- 初态相对 base 没有改动（`worktree_manifest.json` 中 `initial_diff.bytes = 0`）。镜像里的未跟踪文件只有两个：`run_tests.sh`（已包含在公开包中）和 `install.sh`（公开包中缺失）。版本号为 `8.0.0.dev0`（`src/PIL/_version.py`）；`CHANGES.rst` 顶部的 8.0.0 (unreleased) 段落没有 `formats` 条目。
- 公开材料足以定位调查入口：`Image.py` 中的 `open`（2839-2932 行）、注册表 `ID` / `OPEN`（206-213、3038-3050 行）、`preinit` / `init`（347-412 行）。回归参照是 `Tests/test_image.py` 和 `Tests/test_file_webp.py`。TypeError 的来源可以用 `grep -rn 'warns(None' Tests/` 定位。

### 3.6 缺失信息

- **真正阻碍开发**（读代码也解决不了）：
  1. `formats` 的精确语义（§2 第 1-10 项），尤其是"严格限制"还是"先试后回退"，因为题面本身自相矛盾。
  2. 题面报告的 TypeError 是否属于评分要求。如果隐藏测试包含 `pytest.warns(None)` 用例，且 `.venv` 里的 pytest 拒绝 `None`，这些用例在任何合法修复之后仍会失败。它们是否计入评分，公开材料看不出来。
- **只需正常读代码**：插件的两阶段加载、注册 ID 统一大写、`_open_core` 对异常的分类处理、`jpeg_factory` 的 MPO 分支、`show()` 的弃用范围。

## 4. 开发需求表

以下命令都在 `/testbed` 下执行，均为**建议，未执行**。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令 → 预期现象 |
|---|---|---|---|---|
| Python 解释器 | `run_tests.sh:1` 调用 `.venv/bin/python` | 明确：`python` 指向 `/testbed/.venv/bin/python`，Python 3.9.21 | 无 | `python --version` → `Python 3.9.21` |
| 能导入、且指向工作树的 PIL（含已编译的 `_imaging`） | `Image.py:88-118` 导入 `_imaging`；`.gitignore` 忽略 `*.so`；公开包不含编译产物；缺少 `install.sh` | 没有说明 Pillow 的安装方式 | 不知道 `import PIL` 解析到 `/testbed/src/PIL`（可编辑安装或就地编译），还是 site-packages 中的副本。若是后者，修改 `src/` 不会生效 | `python -c "import PIL, PIL.Image as I; print(PIL.__version__, PIL.__file__, I.core.__file__)"` → 预期输出 `8.0.0.dev0` 和 `/testbed/src/PIL/__init__.py`；若路径在 site-packages，应上报 |
| pytest | `requirements.txt:10`（未固定版本）；`run_tests.sh:1` 用 `python -m pytest` | 只说明没有 pip，没给 pytest 版本 | 版本未知，而版本决定那 26 处 `pytest.warns(None …)` 会不会报错；也无法重装 | `python -m pytest --version` → 若是已移除 `None` 支持的版本，下一行命令会复现题面报错 |
| 复现题面 TypeError（发生在测试层） | `Tests/test_image.py:601`、`768` | 无 | 同上 | `python -m pytest -q Tests/test_image.py -k "no_resource_warning_on_save or show_deprecation"` → 若 pytest 拒绝 `None`：2 failed，报 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`；否则 2 passed，说明题面症状在本环境不复现 |
| 复现 base 缺少 `formats` 参数 | `Image.py:2839` | — | 无 | `python -c "from PIL import Image; Image.open('Tests/images/hopper.png', formats=['JPEG'])"` → `TypeError: open() got an unexpected keyword argument 'formats'` |
| 测试图片 | `Tests/images/hopper.{png,jpg,tif,gif}` 和 `flower.jpg` 都在工作树中（已用 `file` 核对类型） | 工作树即初态 | 示例中的路径 `hopper.png` 要改成 `Tests/images/hopper.png`。`.gitignore` 列出的额外图片（`Tests/images/msp`、`picins`、`sunraster`）不在工作树中，相关用例会被跳过，与本题无关 | — |
| 修改后自检（依所选语义而定） | K1-K3；§2 | — | 语义没有约定 | `python -c "from PIL import Image; print(Image.open('Tests/images/hopper.jpg', formats=['JPEG']).format)"` → `JPEG`。在新进程中运行 `python -c "from PIL import Image; print(Image.open('Tests/images/hopper.tif', formats=['TIFF']).format)"` → `TIFF`（检验插件按需加载）。`python -c "from PIL import Image; Image.open('Tests/images/hopper.png', formats=['JPEG'])"` → 严格语义下抛 `PIL.UnidentifiedImageError`，回退语义下成功（格式为 `PNG`）。不传 `formats` 时行为应与 base 相同 |
| 公开回归测试 | `Tests/test_image.py:97-126`、`349-376`；`Tests/test_file_webp.py:23-31`；`Tests/test_file_png.py`、`Tests/test_file_jpeg.py` | 资源为 2 CPU / 4 GiB；`/tmp` 为 1 GiB，而 pytest 的 `tmp_path` 默认建在 `/tmp` 下 | 若 pytest 拒绝 `None`，会出现与本题无关的失败，分布在那 26 处所在的文件中 | `python -m pytest -q Tests/test_image.py Tests/test_file_webp.py` → 预计除 `pytest.warns(None …)` 用例外，其余通过或被跳过 |
| 图像查看器（`show()` 用到） | `ImageShow.py:46-58`、`170-229` | 未提及 | 不知道容器里有没有 `display` / `eog` / `xv`，也没有图形显示 | 不建议直接调用 `im.show()`。`python -c "from PIL import ImageShow; print(ImageShow._viewers)"` → 预计输出 `[]` |
| 隐藏测试与 `run_tests.sh` | `run_tests.sh:1` 运行 `r2e_tests` | 公开包不含隐藏测试 | 解题时 `/testbed/r2e_tests` 是否存在，未知 | 不建议依赖 `bash run_tests.sh`；若该目录不存在，预计 pytest 报告找不到 `r2e_tests` |
| 网络、装包、重新编译 | `Makefile`：`clean` 会执行 `rm src/PIL/*.so`，`inplace` 需要重新编译 | 明确：没有 pip，不能出网 | 本题只改 Python 代码，不需要这些。不要运行 `make clean` / `make inplace`：若扩展是就地编译的，删掉后可能无法重建（推断） | — |

## 5. 阅读范围

- **打开或检索过的文件**
  - 角色卡。
  - 本题公开包：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json` 只看了结构（`export`、`initial_diff`、`untracked_*` 与 `files` 键），**没有**打开其中指向公开包以外的路径（例如 `initial_diff.source`）。
  - `worktree/` 下的文件：
    - 根目录：`run_tests.sh`、`requirements.txt`、`setup.cfg`、`tox.ini`、`conftest.py`、`.gitignore`、`Makefile`（前 60 行）、`CHANGES.rst`（前 60 行）。
    - `src/PIL/`：`_version.py`、`__init__.py`、`__main__.py`、`ImageShow.py`（全文）；`Image.py` 的第 1-130、195-424、2073-2209、2800-3059、3100-3179 行，外加若干 grep；`JpegImagePlugin.py` 第 780-810 行；`WebPImagePlugin.py` 第 24-33 行；`features.py` 第 270-310 行。
    - `Tests/`：`test_image.py` 的第 1-200、340-385、575-610、700-800 行；`test_file_jpeg.py` 第 640-690 行；`test_file_webp.py` 第 23-31 行；`test_imagefile.py` 第 90-105 行；`Tests/conftest.py`；`Tests/README.rst` 前 40 行；`Tests/helper.py` 只做了 grep。
    - `docs/`：`docs/reference/Image.rst`（第 40-60 行及 grep）、`docs/deprecations.rst` 前 40 行、`docs/releasenotes/7.2.0.rst` 前 60 行。
  - 全树检索的关键词：`formats`、`warns(None`、`derived from Warning`、`Image.open(` 的调用方、`DeprecationWarning`。
  - 对 `Tests/images/hopper.{png,jpg,tif,gif}` 和 `flower.jpg` 运行了 `file` 核对类型。
- **没有查的范围**：其余插件、C 源码（`src/*.c`）、`depends/`、`winbuild/`、`.ci/`、`.github/`、其它测试与文档；角色卡中链接的 SWE-Gym 公开读者卡（在公开包之外，按协调者要求没有打开）；公开包以外的任何路径。没有联网，也没有查上游的后续提交或 PR。
- **限制**
  - `user_prompt.txt` 只是静态渲染，不是捕获到的模型实际消息。
  - `worktree/` 不是完整的运行容器：不含 `.venv`、编译扩展、`.git` 和隐藏测试，`install.sh` 也缺失。
  - 没有运行任何项目代码，表中的预期现象都是推断。
  - 关于 pytest / CPython 行为的判断来自一般知识，未在镜像中核实。
  - 模型的实际消息、运行资源和开发条件均**未经验证**。
