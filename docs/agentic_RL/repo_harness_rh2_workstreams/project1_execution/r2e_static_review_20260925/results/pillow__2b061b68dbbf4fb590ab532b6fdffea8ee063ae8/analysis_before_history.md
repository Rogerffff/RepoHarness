<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：私有主审初判（读历史前）

- 角色：R2E 私有主审（静态审查），2026-09-25，干净上下文。本文在读任何历史调查之前保存。没有打开：`history/`、`docs/.../r2e_env_repair_20260924/`、任何 `*review*` 目录、本批 `README.md`、OUTPUT_DIR 中除 `public_read.md` 以外的文件、`runs/` 下的分析与汇总文件。
- 暴露范围：读过 gold、隐藏测试、期望映射、4 份当前材料评分日志及其账本行、2 份 M3 独立参考日志。为核对题目关系，另读了同池另外 6 道 pillow 题的公开包，只看了题面标题、`base_commit`、`Image.open` 的签名与实现片段（附录 D）。
- 路径约定：`H/` 指 `PRIVATE_DIR/hidden_tests/`，评分时放到 `/testbed/r2e_tests/`；`W/` 指 `PUBLIC_DIR/worktree/`，也就是解题者看到的 `/testbed`；`Image.py` 指 `W/src/PIL/Image.py`。
- 证据级别：
  - 【执行】：当前材料下已有的 RH2 评分日志或账本（09-23 R-f、09-24 复跑），或 M3 独立 runner 在来源镜像上的日志。
  - 【源码】：读代码推断，没有运行。
  - 【一般知识】：pytest / CPython 的通用知识，没有在镜像里核实。
  - 本轮没有运行任何代码。

## 0. 摘要（暂定）

1. **实际任务**：给 `Image.open` 新增 `formats` 参数。取值为格式名组成的 list 或 tuple，用来严格限制识别时尝试的格式；`None` 表示尝试全部格式；传入非 list/tuple 时抛 `TypeError`。
   - 唯一的目标键是 `TestImage.test_open_formats`：noop 为 FAILED，gold 为 PASSED。
   - 其余 54 键在 noop 和 gold 下结果相同：52 个 PASSED 是回归键，2 个 FAILED 是死键。
2. **评分材料自洽，环境正常**：
   - 期望映射共 55 键，其中 53 个 PASSED、2 个 FAILED。
   - 在当前派生镜像上，noop 两次都得 0（54/55，唯一不匹配的是目标键），gold 两次都得 1（55/55）。M3 在来源镜像上跑 gold 两次，逐键状态与期望一致。【执行】
   - 两个 FAILED 键（`test_no_resource_warning_on_save`、`test_show_deprecation`）失败的原因是：`.venv` 里的 pytest 8.3.4 拒绝 `pytest.warns(None)`，测试体根本没有执行。任何合法的库改动都无法让它们翻转。
3. **主要问题在题面**，属于题意与测试的争议，不是环境问题：
   - (a) 标题和 Actual Behavior 描述的 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`，恰好是两个死键的失败原因，noop 和 gold 下都会出现，不是 Pillow 的缺陷。noop 下目标键的失败原因是 `TypeError: open() got an unexpected keyword argument 'formats'`。
   - (b) 示例加上 Expected 第 1 条要求 `Image.open('hopper.png', formats=['JPEG'])` "should work without issues"；隐藏断言却要求**完全相同的调用**抛 `UnidentifiedImageError`（`H/test_1.py:96-98`）。二者直接冲突。
   - (c) Expected 第 3 条说"`show()` 是弃用方法、应发警告"，与公开文档和公开测试相反。
4. **次要问题**（覆盖缺口，题面恰好诱导解题者去碰这些地方）：
   - 两个死键使 `save` / `show()` 的警告行为完全不受保护。若照题面给无参 `show()` 加 `DeprecationWarning`，仍会得 1。【源码】
   - 新进程里第一次调用默认 `open` 的路径没有任何键覆盖：若 `formats=None` 时取 `list(ID)` 快照，会在新进程里打不开任何图片，却仍能得 1。【源码】
   - gold 对尚未注册、小写或未知的格式名会抛 `KeyError`。这一点没有测到，因此更完整的修复同样能通过。
5. **暂定处置**：`needs_review`，理由为"题意/测试争议：题面叙述与隐藏断言冲突"。
   - 建议先修订公开题面，再考虑列为静态候选。
   - 隐藏测试和期望映射不需要为了接纳合法解而修改。
   - 唯一优先的下一步见 §9。

## 1. 公开读者产物核对（第 1 步）

`public_read.md` 的判断与私有证据的对照：

| 公开读者的疑点 | 私有证据 | 结论 |
| --- | --- | --- |
| 题面的 TypeError 来自 pytest 的 `pytest.warns(None)` | 日志头显示 `pytest-8.3.4, pluggy-1.5.0`。两个死键都在 `.venv/lib/python3.9/site-packages/_pytest/recwarn.py:279` 抛出这个 TypeError，noop 和 gold 下相同【执行】 | 成立 |
| `import PIL` 是否来自 `/testbed/src` | 账本记录 `observations.RH2_OBS_IMPORT_PATH=/testbed/src/PIL/__init__.py`、`RH2_OBS_PKG_VERSION=8.0.0.dev0`（评分用户 uid 54322）【执行·评分侧】 | 评分侧成立；解题侧用的是同一个 venv，属推断，actor 待验 |
| `formats` 取严格语义还是先试后回退 | 隐藏断言按严格语义写（§3） | 公开材料无法判定，是真实的冲突 |
| 题面报告的 TypeError 是否计分 | 两个死键期望 FAILED，必须继续失败 | 计分，方式是"保持失败" |
| 解题时 `/testbed/r2e_tests` 是否存在 | 环境卡 §1：派生镜像已把隐藏测试移到 root 私有目录；正式 actor 目前用来源镜像，`/r2e_tests` 可读（环境卡 §2） | 派生镜像下不存在；正式链路是平台阻塞项 |
| 不重置 `conftest.py` / `Tests/helper.py` 可能构成旁路 | 环境卡 §3：只删除并重放 `r2e_tests/` 和 `run_tests.sh`；根 `conftest.py` 是 `pytest_plugins = ["Tests.helper"]`（`W/conftest.py:1`） | 通道确实存在，影响见 §6(d) 和 §8 |

公开读者**没有捕获**以下内容：实际渲染的模型消息（只有静态 `user_prompt.txt`）；容器内的工具和图像查看器；以 actor 身份实际运行测试的结果。

## 2. 八方面覆盖

| 方面（清单编号） | 已查 | 初判 | 未查 / 缺项 |
| --- | --- | --- | --- |
| 公开需求（3、23） | 题面逐句核对 base 源码、公开测试与文档；公开读者产物 | **issue**：题面四项主张中三项与事实不符或相互冲突（§0-3），只有"`formats` 用来 restrict"可用 | 实际渲染消息缺失（只有静态渲染） |
| 材料与初始问题（1、2、27） | base `608ccd05`；gold 是 `2b061b68` 去掉测试路径后的部分（M3 `gold_meta` 显示上游提交只改了 `src/PIL/Image.py` 和 `Tests/test_image.py`）；隐藏的 `test_1.py` 等于 base 的 `Tests/test_image.py` 加上新增的 `test_open_formats`（diff 为 +20 行）；隐藏的 `helper.py` 与 base 的 `Tests/helper.py` 逐字相同；初态 diff 为 0 字节 | 材料对应。初态缺的是 `formats` 参数【执行】；题面描述的 TypeError 不是初态的库缺陷 | — |
| 测试是否测到要求（18–20、25、32） | 55 键全读；目标键逐条断言；死键追到 pytest 源码行 | 目标键能区分"不实现 / 回退 / 严格"三种做法；两个死键的测试体没有执行（18 issue）；默认路径只在 `init()` 之后被测到（25 issue） | 反例未运行 |
| 是否误拒合理解（24、28） | 题面冲突与各断言的依据 | 按题面示例实现的回退语义必判 0（与题面冲突的直接后果）。低风险误拒：`formats=123` 抛 `ValueError`；只接受 list；自定义异常 | 均未运行 |
| 回归与 gold 完整性（26、27） | `open` 的调用路径、52 个回归键中走 `Image.open` 的用例、gold 的异常分支 | 默认路径在 `init()` 之后覆盖较好；`show` / `save` 的警告行为、新进程首次 `open` 不受保护；gold 对未注册、小写格式名抛 `KeyError`（未测） | 没有逐条评述全部回归键（§3.2 列出了阅读范围） |
| agent 开发条件（6–15） | 环境卡、brief、账本 observations、日志头 | 纯 Python 改动，不需要装包、联网或构建；公开测试有 26 处 `pytest.warns(None)` 必然失败，这是与本题无关的噪声，而且会"印证"误导性题面 | actor 身份下的实际运行：actor 待验 |
| 交付与评分边界（4、16–17、21–22、29–31） | 投影、重放、解析器去色、根 conftest 插件链 | 合法修复只需改 `src/PIL/Image.py`（gold 投影 `included_paths=['src/PIL/Image.py']`）。候选可以改根 `conftest.py`、`Tests/helper.py`、`setup.cfg`，而且评分时都会生效，属于 R2E 通用机制 | 通用控制面没有逐题攻击验证 |
| 题目关系与用途（5、29–30、37–40） | 同池 pillow 题的 base 与 `Image.open` 片段 | 同池 5 道 pillow 题的 base 已含上游终版 `formats` 实现和公开的 `test_open_formats`（附录 D） | 预训练暴露情况未知 |

## 3. 隐藏测试展开

### 3.1 目标键 `TestImage.test_open_formats`（`H/test_1.py:89-107`）

所有调用都通过 cwd 相对路径 `Tests/images/hopper.png` 和 `hopper.jpg`；评分在 `/testbed` 下运行，所以路径可用。本测试在全会话中第一次调用 `Image.open`，此前的 4 个用例只调用 `Image.new`。因此进入本测试时 `_initialized == 0`，`ID` 为空。【源码】

旁证：日志头里没有 `Tests/conftest.py` 的 `pytest_report_header` 输出。那个 hook 会调用 `features.pilinfo`，进而调用 `Image.init()`；它没有输出，说明这个 conftest 没被加载，全部插件也就没有在会话开头预先载入。【执行】

| 断言 | 输入 → 期望 | 公开依据 | 区分力 |
| --- | --- | --- | --- |
| A1 `:93-94` | `Image.open(PNG, formats=123)` → `TypeError` | 公开材料没有；属于 Python 惯例。上游后续版本的 docstring 才写明 `:exception TypeError`（见同池题 base，附录 D） | **弱**：base 对未知关键字本来就抛 `TypeError`，noop 能过这一步。不做类型检查的实现，在迭代 `123` 时也会抛 `TypeError` |
| A2 `:96-98` | `["JPEG"]` 和 `("JPEG",)` 打开 PNG → `UnidentifiedImageError` | 题面 "restrict the supported image formats"；现有失败路径（`Image.py:2926-2932`）。**与题面示例及 Expected 第 1 条冲突** | 强：能排除"只加参数不用"和"回退"两种做法。noop 在此失败：`TypeError ... unexpected keyword argument 'formats'`（`test_1.py:98`）【执行】 |
| A3 `:100-102` | 同样的 formats 打开 JPG → 成功，RGB，128×128 | 同上 | 能排除"把列出的格式也排除掉"的实现 |
| A4 `:104-107` | `formats=None` 打开 PNG 和 JPG → 成功 | 无明文；属于向后兼容的自然默认值 | 要求显式传入 `None` 时等同于全部格式 |

A2 第一次迭代会触发会话里第一次 `init()`（返回 1）。所以"第二轮忘了传 formats"这类实现会在这里暴露：第二轮试遍全部格式，PNG 被打开，于是 `DID NOT RAISE`。【源码】

### 3.2 回归键（52 个 PASSED）

同一文件中的回归检查。与本改动相关的回归键都经过 `Image.open` 的默认路径：

- `test_invalid_image`：空 `BytesIO` 抛 `UnidentifiedImageError`。
- `test_bad_mode`：以位置参数传入的 mode `"bad mode"` 抛 `ValueError`，这一条保护了"`mode` 仍是第二个位置参数"。
- `test_stringio`。
- `test_pathlib`：TIFF 与 JPEG 的 `Path`。
- `test_tempfile`、`test_readonly_save`（BMP）、`test_registered_extensions`。
- `test_load_on_nonexclusive_multiframe`（MPO）：不关闭由调用者传入的 fp。
- `test_exif_*`、`test_overrun`（FLI / SGI / PCX）。
- `hopper()` 辅助函数打开 PPM，多个用例使用它。

**这些调用全部发生在 `init()` 之后。** 其余回归键（mode、alpha、effect、gradient、registry 等）只做了抽读，没有逐条评述。

### 3.3 死键（期望 FAILED）

| 键 | 失败位置【执行】 | 测试体执行到哪里 |
| --- | --- | --- |
| `test_no_resource_warning_on_save`（`:613-621`） | `pytest.warns(None, im.save, temp_file)` → `recwarn.py:279` `TypeError` | 在构造 `WarningsChecker` 时就失败，`im.save` 没有被调用 |
| `test_show_deprecation`（`:783-793`） | `with pytest.warns(None) as raised:` 同一处 | `im.show()`、`assert not raised`，以及 `show(command="mock")` 的 `DeprecationWarning` 断言都没有执行 |

## 4. 双向映射

### 4.1 正向：公开要求 / 合理旧行为 → 键

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 新增 `formats` 关键字 | 题面标题、首句、示例 | `test_open_formats` 整体 | 覆盖 | noop FAILED → gold PASSED（current 4 次，M3 2 次）【执行】 |
| 限制语义：列表外的格式无法识别 | "restrict…"；`Image.py:2926-2932` | A2 | 覆盖，但与题面示例冲突 | 回退语义候选静态必判 0，待 CPU |
| 列表内的格式正常打开 | 同上 | A3 | 覆盖 | gold PASSED |
| `None` 等于全部格式 | 默认值，向后兼容 | A4 | 覆盖 | gold PASSED |
| 非 list/tuple 抛 `TypeError`；接受 tuple | 公开材料没有（惯例） | A1；A2 中的 `("JPEG",)` | 覆盖但无公开依据（风险低） | 静态 |
| 大小写、空列表、未知名、未注册插件（如 `TIFF` 需要 `init()`）、尝试顺序、以位置参数传入、MPO | 未约定（public_read §2） | — | 未覆盖（宽松） | gold 自身会抛 `KeyError`（§7） |
| 不传 `formats` 时行为不变（K1） | base 源码 | 52 个回归键 | 部分：只覆盖 `init()` 之后；新进程首次 `open` 未覆盖 | `list(ID)` 快照候选（§5），待 CPU |
| `mode` 仍是第二个位置参数；非独占 fp 不被关闭 | base 源码与公开测试 | `test_bad_mode`；`test_load_on_nonexclusive_multiframe` | 覆盖 | gold PASSED |
| 保存时不多发警告；无参 `show()` 不发警告，`show(command=)` 发 `DeprecationWarning` | `W/Tests/test_image.py:593-601、763-773`；`docs/deprecations.rst` | 两个死键 | **未覆盖**（测试体未执行） | gold 加上 `show()` 警告的候选，静态判 1，待 CPU |
| 题面要求"消除 save / show 的 TypeError" | 题面 Actual / Expected | 两个死键期望 FAILED | **冲突**：题面要消除的错误，期望映射要求保留；合法的库改动也消除不了 | noop 和 gold 日志中都出现【执行】 |
| 题面称"`show()` 已弃用，应发警告" | 题面 Expected 第 3 条 | 无键 | 冲突（与公开文档相反），而且不被测 | — |

### 4.2 反向：关键断言 → 公开依据

- A2 / A3 可追到 "restrict"。但题面示例把严格语义的必然结果（`UnidentifiedImageError`）写成了"应该正常工作"。
- A1、tuple 的要求、A4 只有惯例可依，公开材料没有写明。它们与上游后续文档一致，但本题的公开材料里看不到。
- 两个死键不来自任何公开要求，是环境伪影（pytest 8 不再支持 `None`），刚好又被写进了题面的 Actual Behavior。

## 5. 替代实现与蒙混实现（有具体疑点才列）

| 候选 | 合理性 | 静态预测得分 | 应得分 | 可区分实验 |
| --- | --- | --- | --- | --- |
| 上游终版：`i = i.upper()`，未注册时先 `init()`，并补 docstring | 更完整，同池题的 base 就是这一版 | 1 | 1 | 可选的 CPU 正例 |
| 先正常打开，再检查 `im.format in formats`，不符则抛 `UnidentifiedImageError` | 合理的不同路线（MPO 行为不同，但没有测到） | 1 | 1 | — |
| **回退语义**：先试列出的格式，都不行再试其余格式 | 照题面示例和 Expected 第 1 条的字面意思写 | **0**（A2 报 `DID NOT RAISE`） | 有争议：题面同时支持两种读法 | CPU：派生镜像评分，预测 0。这是题面修订的触发反例 |
| `formats=123` 时抛 `ValueError`；只接受 `list`；不匹配时抛自定义异常 | 少见但说得通 | 0 | 有争议（风险低） | 不必专门跑 |
| **`formats = list(ID)` 快照**（或 `tuple(ID)`、`[f.upper() for f in (formats or ID)]`），且在 `preinit()` 之前取 | 常见的防御性拷贝写法 | **1**：所有 `formats=None` 调用都发生在 A2 触发 `init()` 之后 | 0：新进程里第一次 `Image.open('x.png')` 时快照为空，抛 `UnidentifiedImageError`；若快照取在 `preinit()` 之后，则非预载格式（TIFF 等）在新进程里打不开 | CPU：评分，另跑 `python -c "from PIL import Image; Image.open('Tests/images/hopper.png')"` |
| **gold 加上"无参 `show()` 发 `DeprecationWarning`"**（或在 `save` 里压掉警告） | 题面 Expected 第 2、3 条直接诱导 | **1**：只有死键会检查这个行为 | 0：违背公开文档和公开测试 | CPU：评分，预测 1 |
| 改根 `conftest.py` 或 `Tests/helper.py`，给 `pytest.warns` 打补丁使其接受 `None` | 照题面字面"消除 TypeError"的唯一办法，但属于越界改测试设施 | 若死键因此变成 PASSED，得 0 | 0（不合法） | 不必专门跑 |

## 6. R2E 专项

- **(a) 非 PASSED 键**：
  - 失败原因：两个键都在 pytest 8.3.4 的 `WarningsChecker.__init__` 里对 `None` 抛 `TypeError`，发生在调用 Pillow 代码之前。noop、gold 和 M3 来源镜像的失败原因逐字相同。【执行】
  - 合法修复能否翻转：任何合法修复都翻不动它们，包括更完整的上游终版。只有改 pytest 的行为才能翻转，例如借根 `conftest.py` 加载的 `Tests.helper` 插件打补丁，而这样做会判 0。
  - 结论：对合法解没有风险；对照字面去"修 TypeError"的解题者是陷阱。
- **(b) 题面报错是否出现在 noop 目标键里**：没有。
  - noop 目标键报的是 `TypeError: open() got an unexpected keyword argument 'formats'`（`test_1.py:98`）。
  - 题面那句报错只出现在两个死键里，gold 下照样出现。【执行】
  - 可以推断：题面生成时把 gold 运行中失败的两个用例当成了缺陷。
- **(c) 是否泄漏修法**：没有泄漏。题面只给了参数名和用途，没有给实现。问题是误导，不是泄漏。
- **(d) base 测试辅助、搬迁伪影、跨文件撞键**：
  - 隐藏的 `helper.py` 随隐藏测试一起放入，`from .helper` 解析到的是隐藏副本，内容与 base 逐字相同。根 `conftest.py` 还会把候选可以修改的 `Tests/helper.py` 作为插件导入。它没有 hook，只有导入时的副作用，正常解法不受影响；但它提供了一条改变测试进程的通道（§5 最后一行）。
  - 搬迁伪影：`Tests/conftest.py` 不生效，会话开头不会调用 `init()`。这反而让 A2 能抓到"第二轮忘了传 formats"的错误；但新进程首次默认 `open` 的路径，无论搬迁与否都没有测试覆盖。
  - cwd 相对路径的资源正常。
  - 只有一个测试文件，没有跨文件撞键。55 个键去色后仍各不相同：54 个 `def test_`，其中 `test_pillow_version` 参数化为 2 个键。
  - `setup.cfg` 的 `addopts = -ra --color=yes` 可以被候选修改。但解析器对期望和观测两侧用同一规则去色（`rh2/src/repoharness2/envpack/r2e_parsers.py` 的 `decolor_keys`），所以不影响键的身份。
- **(e) 时间、随机、资源敏感的键**：
  - `test_effect_noise` 和 `test_effect_spread` 用 C 的 `rand()`，而 `src/libImaging/Effects.c:104-137` 里没有 `srand`。在固定测试顺序下，结果基本是确定的。【源码 + 一般知识】
  - 6 次运行的逐键状态都一致；测试本身耗时约 0.3–0.6 s；内存峰值约 466 MB。【执行】
  - 风险低。
- **(f) 材料修订**：`revisions.json` 为 `[]`，不适用。

## 7. gold 检查

- **修到的部分**：新增参数（第三个位置参数，默认 `None`）；`None` 直接别名为 `ID`，而 `init()` 会就地扩充同一个列表，所以第二轮能看到全部插件；非 list/tuple 在打开文件之前就抛 `TypeError`，不会泄漏文件句柄；两轮都只遍历 `formats`。没有无关改动。
- **没修的部分**（未测到）：
  - `formats=['TIFF']` 在新进程里：`OPEN['TIFF']` 抛 `KeyError`，这个异常不在 `except (SyntaxError, IndexError, TypeError, struct.error)` 之列，会走 `except BaseException` 关闭文件后原样抛出（`Image.py:2905-2913`）。
  - 小写名（`['jpeg']`）和未知名同样抛 `KeyError`。
  - 没有更新 docstring。
  - 上游后来补上了这些（同池题的 base 里有 `i = i.upper()` 和"未注册则 `init()`"，附录 D）。
  - 这些都属于 gold 不完整，而不是测试过严，所以更完整的实现不会被误拒。
- **与题面字面要求对照**：gold 自己也不满足题面 Expected 第 1–3 条。示例 `Image.open(..., formats=['JPEG'])` 打开 PNG 会抛 `UnidentifiedImageError`；两处 TypeError 在 gold 日志里照样出现。这说明错的是题面，不是 gold。

## 8. 开发需求（逐题）

| 项 | 需求 | 证据级别 |
| --- | --- | --- |
| 导入 | `python` 为 `/testbed/.venv/bin/python` 3.9.21；`import PIL` 指向 `/testbed/src/PIL`，改源码即生效 | 解释器：镜像层面实测（环境卡、brief）；导入路径：评分侧实测（账本 observations）；解题侧 actor 待验 |
| 依赖 | 不需要新依赖；`.venv` 已有 pytest 8.3.4、pytest-cov 6.0.0 | 评分日志实测；解题侧是同一 venv（推断） |
| 资产 | `Tests/images/hopper.{png,jpg}` 等图片在工作树中 | 公开包，评分实测 |
| 权限 | agent（54321）可写 `/testbed` | 镜像层面实测（brief） |
| 网络 | 准备、解题、评分各阶段都不需要 | gold 在 `deny_all` 下得 1【执行】 |
| 构建 | 不需要；不要执行 `make clean`（会删除 `src/PIL/*.so`） | 源码（Makefile） |
| 提交边界 | 只需改 `src/PIL/Image.py`；gold 投影 `included_paths=['src/PIL/Image.py']` | 评分侧实测 |
| 本地验证 | 自写复现命令（public_read §4）；`python -m pytest Tests/test_image.py` 会有 2 例 `pytest.warns(None)` 必然失败，全树共 26 处，分布在 16 个文件，与本题无关 | actor 待验；失败原因由评分日志推断 |
| 正式 actor 链 | 当前用来源镜像：`/r2e_tests` 可读，git 中有修复提交；解释器前缀和提示仍写 conda；`public_hints` 说"有 conda 和 pip""测试文件会被重置"，都不符合实际 | 代码事实（环境卡 §2、§3），B 线待改；**进正式 actor 前必须改** |

## 9. 缺口与建议队列（由协调者安排）

1. **题面修订**（改的是公开规格，属修订类型"题面纠错"）：
   - 删除 TypeError、`save`、`show()` 的叙述，以及"formats 已经引入"的前提。
   - 把示例改成与"restrict"一致：PNG 配 `['JPEG']` 无法识别，JPEG 文件可以打开，`None` 表示全部格式。
   - list/tuple 与 `TypeError` 是否写进题面，由修订审定；不必把测试要求全抄进去。
   - 触发反例是回退语义候选。
   - 隐藏测试和期望映射不变。
2. **CPU 对照**（派生镜像，当前材料），把静态推断转成执行证据：
   - (i) 回退语义 → 预测 0；
   - (ii) gold 改为 `formats = list(ID)` → 预测 1，同时新进程默认 `open` 失败；
   - (iii) gold 加上无参 `show()` 的 `DeprecationWarning` → 预测 1；
   - (iv) 可选：上游终版 → 预测 1。
3. **可选的测试支撑修订**，需用户决定是否偏离来源期望：
   - 把两处 `pytest.warns(None)` 换成语义等价的 `warnings.catch_warnings(record=True)` 加 `simplefilter("always")`，恢复原断言。这样两个键会从 FAILED 变为 PASSED，从而重新保护 `save` / `show` 的警告行为。
   - 是否再加一个"新进程默认 `open`"的子进程检查，有公开依据（向后兼容），但属于新增断言，需要单独审定。
4. **数据划分**：同池 5 道 pillow 题（`2d01f7d0`、`3a61c9e9`、`4bc64835`、`a682ceaf`、`f9d3ee0f`）的 base 可以看到本题答案的上游终版和对应的公开测试。若本题留作评测，需要记录这层关系。
5. **尚未掌握**：实际渲染消息；actor 身份下的公开测试运行；上面四个候选的执行结果；预训练暴露程度。

**唯一优先的下一步**：起草题面修订版，并以回退语义候选作为触发反例，在派生镜像上评分确认得 0，然后交给用户决定。第 2 项的 (ii)、(iii) 可以放在同一个 CPU 小批里一起跑。

## 10. 暂定处置

- `disposition.scope=static_review`；`state=needs_review`。
- reason：题意/测试争议，题面误导且与目标断言冲突，不是环境问题。修订题面后，本题可以作为"静态候选，待 actor 验证"。
- 目前能肯定的事实：
  - 测试、期望与 gold 在当前环境中自洽，重复评分稳定。
  - 合法修复不会翻转两个 FAILED 键。
- 按原题面直接用于训练，会同时惩罚照示例实现回退语义的解，并放过照题面给 `show()` 加警告的有害改动。
- `usage.intended_use=development_diagnostic`；审查者见过 gold 和隐藏测试。

---

## 附录 A　运行证据（全部 `material=current`，另有 M3 独立参考）

| 组 | 账本:行 | 候选 | 结果 | 日志（sha256 已与 run_refs 核对一致） |
| --- | --- | --- | --- | --- |
| R-f 09-23 | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:37` | noop | 0，54/55，不匹配 `test_open_formats` | `.../evallog_replay-r2e-rf-all-noop-p_90eb28b3.eval.log` |
| R-f 09-23 | `.../ledger_r2e_all_gold.jsonl:37` | gold | 1，55/55 | `.../evallog_replay-r2e-rf-all-gold-p_d21a126c.eval.log` |
| 复跑 09-24 | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:37` | noop | 0，54/55，同上 | `..._118b9a70.eval.log`（把地址和时间戳归一后，与 R-f noop 日志逐行相同） |
| 复跑 09-24 | `.../_rerun2/ledger_gold.jsonl:37` | gold | 1，55/55 | `..._ed596d34.eval.log`（归一后与 R-f gold 日志相同） |
| M3 来源镜像 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:10、57` | gold | passed ×2 | `.../pillow/2b061b68dbbf/gold/a{1,2}/test_output.txt`（两份一致；53 PASSED + 2 FAILED） |

- 4 次 current 运行使用同一个派生镜像：`rh2-r2e-derived/pillow:2b061b68dbbf-r2e_derive_v1`，镜像 ID `sha256:006d96ed…`，`recipe_sha256 0da821a1…`。
- 运行条件：评分用户 uid 54322，2 CPU / 4 GiB，`/tmp` 1 GiB，`network=deny_all`，`install_skipped`。
- 各次运行都满足：`segment_completed=True`，`num_parsed_tests=55`，没有 missing 或 unexpected 键。

## 附录 B　失败位置摘录（去色）

- noop：`FAILED ...::TestImage::test_open_formats - TypeError: open() got an unexpected keyword argument 'formats'`，位置 `r2e_tests/test_1.py:98`。
- noop 和 gold 都有：`FAILED ...::TestImage::test_no_resource_warning_on_save - TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`，位置 `recwarn.py:279`，调用自 `test_1.py:621`。`test_show_deprecation` 同一原因，调用自 `test_1.py:788`。

## 附录 C　`checks` 预填（40 项编号，稀疏；写 `screening_record.json` 时再定）

| 状态 | 编号 |
| --- | --- |
| pass | 1、6、7、9、11、13、14、16、17、19、20、21、22、32 |
| issue | 2（题面描述的问题不是初态的库缺陷；真正的初态缺口"缺 `formats` 参数"是存在的）、3、5、18（死键）、23、24、25、26、27（轻微） |
| unknown | 8、10（actor 待验）、29（正式链用来源镜像，是平台阻塞项）、30、31（R2E 通用控制面，未逐题验证） |
| not_checked | 15、33–36 |
| not_applicable | 28、37–39 |

## 附录 D　实际阅读范围

- **方法**：角色卡；四份方法文档（八方面协议、R2E 环境卡、记录模板、40 项清单）。
- **公开**：`public_read.md`；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json`（只看了非 `files` 的键）。`worktree` 内读过：
  - `src/PIL/Image.py` 的 200-216、340-415、2175-2210、2836-2945、3030-3060、3150-3180 行；
  - `conftest.py`、`Tests/conftest.py`、`setup.cfg` 的 pytest 段；
  - `Tests/helper.py`，与隐藏副本做了 diff；
  - `Tests/test_image.py`，与隐藏的 `test_1.py` 做了 diff；
  - 全树 grep：`formats`、`warns(None`、`srand` / `rand()`。
- **私有**：`hidden_tests/*` 全文、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`。
- **运行证据**：附录 A 的 4 个账本行和 6 份日志。列目录时误看到其它题复跑日志的耗时 grep 输出，只有文件名和耗时，与本题判断无关。
- **代码**：`rh2/src/repoharness2/envpack/r2e_parsers.py` 模块头与 `parse_log_pytest`、`decolor_keys`，用于核对键的规则。
- **其它题公开包**：7 道 pillow 题（含本题）的题面标题和 `base_commit`；另外 6 道题中，5 道看了 `W/src/PIL/Image.py` 中 `open` 的签名和 `formats` 片段，以及 `Tests/test_image.py` 是否有 `test_open_formats`；`3ac9396e` 只看了 `PIL/Image.py` 中 `open` 的签名，它早于 `formats`，与本题无关。另外打开过 `assignments.json`，只见到分派元数据。
- **没有读**：任何历史调查或审查；OUTPUT_DIR 中的其它文件；`install.sh`（公开包缺失，镜像内存在；导入路径已由账本 observations 确认，所以不需要）；C 源码只 grep 了 `rand`。
