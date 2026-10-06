# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：历史主张对照

- 本文写于 `analysis_before_history.md` 保存之后，由私有主审完成，日期 2026-09-25。
- **读过的历史材料**：`history/.../refs.json` 列出的全部 9 项。
  - `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json`：三个列名族，加上 `no_pip`、`conda_wording`、`flippable`、`relocation`、`timing` 等相关族；
  - `decisions.md`：T0-3、E06、E09、E10、E14；
  - `results_20260924.md`、材料修订提案、复现脚本、P4 README。
- **读过的原始证据**（由这些历史材料指向）：
  - `runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68…/agent_probe.log`；
  - `runs/r2e_env_repair_20260924/p4/targeted_public_tests/pillow__2b061b68…/{agent_probe.log,dev_probe.json}`；
  - `runs/r2e_env_repair_20260924/p4/image_readout/pillow__2b061b68….txt`（只看了 install.sh 段）。
- **暴露登记**：此前读过批次协调记录 `assignments.json`，协调者已登记；此后不再读批次协调文件。
- **判定用词**：确认、推翻、过时、未核实。"补充"表示历史没有涉及、本轮新增的内容。

## 1. 结论变化

- **处置判断不变**：题面是唯一的实质缺陷；隐藏测试、期望映射、gold 与环境彼此自洽。
  - 历史推荐 C：本轮隔离，留到题意筛查时再评估 B（修订题面）。本轮就是那次被延后的题意筛查。
  - 本轮建议走 B：修订公开题面，隐藏测试与期望映射不改。
- **证据级别上调**：以下几项在初稿中写的是"actor 待验"，历史已有派生镜像内以 agent/54321 身份做的探针实测，现改为"镜像层面实测；正式 actor 链待验"：
  - 解题侧的导入与 pytest 版本；
  - 无 pip、无出网；
  - 公开 `Tests/test_image.py` 有 2 例预存失败；
  - 题面示例中的调用在 base 上的真实表现。
- **本轮新增、历史未涉及的发现**：见 §3 的 N1–N6。

## 2. 逐条对照

| # | 历史主张 | 出处 | 判定 | 新的决定性证据或理由 |
| --- | --- | --- | --- | --- |
| 1 | 环境与评分可用：noop 为 0，唯一不符键是 `test_open_formats`；gold 为 1（55/55）；重复运行一致（R13）；与参考对账一致（R15） | findings；R02、R08、R13、R15 | 确认 | 4 个 current 账本第 37 行都显示 `segment_completed=True`、`num_parsed_tests=55`，没有 missing 或 unexpected 键。两组 noop / gold 日志把地址和时间戳归一化后逐行相同。M3 的两份 gold 日志逐键状态与 RH2 相同。R15 的 `reconcile.json` 本身没有打开 |
| 2 | R03①：题面所述 TypeError 来自测试代码里的 `pytest.warns(None)`，在 pytest 8.3.4 下被拒；库函数调用触发不了它 | R03、提案 | 确认 | 评分日志的 traceback 落在 `_pytest/recwarn.py:279`，发生在调用 Pillow 之前。探针以 agent/54321 在派生镜像中复现：`SAVE_JPEG=ok warnings=[]`、`SHOW_NOARGS=ok warnings=[]`、`SHOW_COMMAND=ok warnings=['DeprecationWarning']`。pytest 8 的来源：install.sh 执行 `uv pip install setuptools pytest pytest-cov PyQt5`，没有固定版本（见 image_readout） |
| 3 | R03② / R16：题面说用 `formats=['JPEG']` 打开 PNG 应该成功，目标测试要求它抛 `UnidentifiedImageError`；照题面实现会得 0 | R03、R16、提案 | 确认（由测试代码可以确定，未实跑） | `H/test_1.py:96-98` 的 `pytest.raises(UnidentifiedImageError)` 包住的，正是题面示例里的同一个调用。按"先试后回退"语义实现时，这里会报 `DID NOT RAISE`。这个回退语义候选已排为题面修订的触发反例 |
| 4 | R03②：测试还要求 `formats=123` 抛 TypeError，题面没有提到 | R03 | 确认；补充：这条断言区分力弱 | base 对未知关键字参数本来就抛 TypeError，所以 noop 能通过 `:93-94`，直到 `:98` 才失败。不做类型检查的实现在迭代 `123` 时同样抛 TypeError。真正会被这条断言拒绝的，只有显式抛 `ValueError` 的实现 |
| 5 | R03③：base 的 `Image.open` 没有 `formats` 参数，标题却暗示已有 | R03、提案 | 确认 | `Image.py:2839` 为 `def open(fp, mode="r")`；探针输出 `OPEN_SIGNATURE_HAS_FORMATS False` |
| 6 | R06：两个期望 FAILED 的键是死键，合法的源码改动无法让它们翻转，因此不改 | R06、issues[2]、`expected_non_passed_keys`、P4 README §2.4 | 确认（静态推断），并补充风险 | 两个键都在构造 `WarningsChecker` 时就失败，测试体里的 `im.save`、`im.show()`、`assert not raised`、`show(command=)` 的 DeprecationWarning 断言一句都没有执行。所以"不误伤正确解"成立。但这也意味着 `save` / `show` 的警告行为在评分中完全没有保护，而题面 Expected 第 2、3 条恰好诱导解题者去改这里（N1）。"不改"在题面修订之后可以接受；按原题面，它会放过有害改动。唯一能让这两个键翻转的途径是改测试设施：根 `conftest.py` 通过 `pytest_plugins = ["Tests.helper"]` 加载 `Tests/helper.py`，二者评分时都不会被重置。一旦翻转，结果就是 0 |
| 7 | R06 附注：`collate_facts` 产出的 `non_passed_reasons` 为空，因为日志行带颜色码 | R06 | 过时 | 当前 `facts.json` 中四次运行的 `rh2_runs[].non_passed_reasons` 都已填出原因行 |
| 8 | R04：重放的测试文件集与 gold 修改的路径不相交；解题不需要改 `r2e_tests` 以外的测试辅助文件 | R04 | 确认，并补充 | 隐藏的 `helper.py` 与 base 的 `Tests/helper.py` 逐字相同，随隐藏测试一起放入。补充：根 `conftest.py` 会把候选可以修改的 `Tests/helper.py` 当作插件导入，`setup.cfg` 的 `addopts` 在评分时也会生效；解析器对两侧都去色，所以不影响键。这属于 R2E 通用的控制面问题，没有逐题做攻击验证 |
| 9 | R05 / R07 / R10 与 `solver_conditions`：`.venv` 为 3.9.21；pytest 8.3.4；没有 pip；导入指向 `/testbed/src`（cwd=/tmp 时也如此）；`/testbed` 和 site-packages 可写；无出网 | R05、R07、R10 | 确认；据此上调初稿的证据级别 | `agent_probe.log` 中：`WHICH_pip=MISSING`、`PYTEST_VERSION=pytest 8.3.4`、`WHICH_pytest=/testbed/.venv/bin/pytest`、`IMPORT_FROM_TMP=/testbed/src/PIL/__init__.py`、`WRITE_SITE=ok`、`NET_CONNECT_RC=1`。这些是用 `docker exec -u 54321` 得到的镜像层面证据，不是正式 actor 链的证据 |
| 10 | R09：公开 `Tests/test_image.py` 为 2 failed / 52 passed；题面所述 TypeError 复现不出，求解者无法按题面复现问题 | R09、issues[3] | 确认，并细化 | `targeted_public_tests/.../agent_probe.log` 记录 `2 failed, 52 passed in 0.31s`，失败的正是两处 `pytest.warns(None)`。细化：用库函数调用复现不出这个错误，但运行公开测试会看到**逐字相同**的报错（出自 `_pytest/recwarn.py`）。求解者可能误以为"已经复现"，反而加深误导 |
| 11 | R17：派生镜像内没有泄漏：修复不在镜像中；私有目录权限 700；base 之后无子提交，无 refs、reflog 或补丁残留；install.sh 不含修复 | R17 | 确认，但只限派生镜像 | 探针输出：`R2E_TESTS_ROOT=absent`、`PRIVATE_LS … Permission denied`、`GIT_REFS_COUNT=0`、`GIT_REFLOG_COUNT=0`、`STRAY_PATCH_FILES` 为空。但按 09-25 R2E 环境卡 §2（代码事实），正式 actor 目前用的是**来源镜像**：`/r2e_tests` 可读，git 中有修复提交。R17 的结论只覆盖派生镜像 |
| 12 | R14：镜像自带的 pyc 由 base 源码编译 | R14、P4 README §3 | 未核实 | 本轮没有复核 pyc 文件头，这一点与本题判断无关 |
| 13 | 提案：R2E 题面由测试失败信息生成，"把 harness 伪影写成缺陷"可能是同源数据的系统性问题 | 提案、P4 README §4 | 未核实；本题支持这一假说 | 本题题面 Actual Behavior 中的报错，与 gold 日志里两个死键的失败行逐字相同。其它题没有扫描 |
| 14 | 提案推荐 C：本轮隔离，到题意筛查时再评估 B | 提案、decisions T0-3 | 推进（不是推翻） | 本轮就是被延后的题意筛查。静态结论是：测试、期望、gold 与环境都自洽，缺陷只在公开题面，所以建议 B，隐藏测试与期望不改。题面修订以三点为核心："restrict"、没有列出的格式能识别时抛 `UnidentifiedImageError`、`None` 表示全部格式。"接受 list 或 tuple"是 API 约定，上游后来的 docstring 也写明了，可以写进题面；不必逐条照抄测试断言 |
| 15 | 处置为 `grading_ok_open_items`：待办项 `statement_conflict`，`deferred_to` 为题意与评分质量筛查 | disposition | 确认为环境阶段的结论 | 本轮在 `static_review` 范围内给出新处置：`needs_review`，理由是题意/测试争议，建议走 B |
| 16 | 建议增加自动检查：题面 Actual Behavior 里的报错文本应当出现在 noop 目标键的失败原因中 | P4 README §7.7、known_issues | 确认（本题就是反例） | noop 目标键的失败原因是 `unexpected keyword argument 'formats'`；题面所述报错只出现在两个死键里 |

## 3. 历史没有涉及、本轮新增的发现（均为静态推断，待 CPU 验证）

- **N1：两个死键使 `save` / `show` 的警告行为不受保护。** 题面 Expected 第 2、3 条诱导出的有害改动（例如给无参 `show()` 加 DeprecationWarning，或在 `save` 里屏蔽警告）预测仍然得 1。这类改动违背公开依据：`Tests/test_image.py:763-773` 与 `docs/deprecations.rst`。对应 CPU 候选 (iii)。
- **N2：新进程里第一次调用默认 `open` 的路径没有覆盖。**
  - 评分会话中第一次 `init()` 发生在 `test_open_formats` 的 A2 分支；所有 `formats=None` 的调用都在它之后。
  - 因此，若实现写成 `formats = list(ID)`（或 tuple、列表推导）这类快照，且在 `preinit()` 之前取值，预测仍得 1。
  - 但在一个新进程里，`Image.open('Tests/images/hopper.png')` 会抛 `UnidentifiedImageError`。
  - 对应 CPU 候选 (ii)。
- **N3：gold 不完整。**
  - 在新进程中传 `formats=['TIFF']`、传小写格式名或未知格式名，都会抛 `KeyError`。原因是 `Image.py:2905-2913` 只吞掉 `SyntaxError`、`IndexError`、`TypeError`、`struct.error`。
  - 上游后来补上了 `i.upper()` 和"格式未注册时先 `init()`"。
  - 这些情况都没有测到，所以更完整的实现不会被误拒。
- **N4：题目之间存在关系。**
  - 同池 pillow 题 `2d01f7d0`、`3a61c9e9`、`4bc64835`、`a682ceaf`、`f9d3ee0f` 的公开 base 中，已经有上游终版的 `formats` 实现（docstring 里写有 TypeError 约定）和公开的 `test_open_formats`，后者是本题隐藏测试的超集。`3ac9396e` 早于这个特性，不相关。
  - 如果本题留作评测，而这几道题进入训练，那么答案对训练过程是可见的。
- **N5：题面 Expected 第 3 条"`show()` 是弃用方法"与公开文档和公开测试相反。** 历史只记录了 `show(command=)` 的复现行为，没有指出这一条矛盾。
- **N6：低风险误拒。** 以下几种实现会被拒：`formats=123` 时显式抛 `ValueError`；只接受 `list`；没有匹配格式时抛自定义异常。

## 4. 改判与未改判的理由

- **处置没有改**：历史证据全部指向同一结论，即题面是唯一缺陷，没有推翻初稿的任何实质判断。
- **证据级别改了**：见 §1 第二条。
- **与历史的主要分歧**：
  1. 历史认为两个死键"不改"即可。本轮认为，按原题面，它们会放过题面诱导出的有害改动（N1），所以修订题面是必要条件；在测试侧改用与 pytest 8 兼容的写法，可以作为可选项。
  2. 历史 R17 的无泄漏结论只覆盖派生镜像；正式 actor 链目前走的是来源镜像。
  3. 历史没有记录跨题可见的答案（N4）。
