# L1_modin_pandas · 逐题静态审查小结（2026-09-16 夜）

范围：`ASSIGNMENT.json` 的 10 题（pandas 5 题、modin 5 题），按优先级顺序做。
题级记录在 `records/<instance_id>.json`；仓库级共性事实在 `repo_level_findings.md`；
复用脚本在 `scripts/`（`prescan.py` / `collide.py` / `leak.py` / `optdeps.py`，前三个改编自 `L1_moto_1/scripts/`）；
大文件产物在 `runs/env_overnight_20260916/L1_modin_pandas/`
（`mat/`、`prescan.json`、`collide.json`、`collide_detail.json`、`leak.json`、`optdeps.json`）。

## 逐题表

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| pandas-dev__pandas-48106 | 3 个 P2P 常量 `Period\('2017',` 是单反斜杠、运行时是双反斜杠，gold/empty 两侧都 missing → gold 恒判 RESOLVED_NO；题面字面说「放大时 categorical 转 object」，而 15/16 个 F2P 要求「赋已有分类值或 NA 时保持 category」，方向相反 | needs_repair | 真机 `pytest --collect-only -q pandas/tests/indexing/test_loc.py` 导出运行时 ID 全集与常量对拍 |
| pandas-dev__pandas-50319 | gold 改 `.pyx`（Cython），agent 不重编自测看不到效果；题面写「return None 或 猜出格式都行」，F2P 只认后者；1 个 P2P 同样因反斜杠层级 missing；F2P 仅 1 条、可被硬编码通过 | needs_repair | 用假补丁（只对该输入返回目标格式）真机跑一次，确认会被判 RESOLVED_FULL |
| modin-project__modin-6298 | 39 个常量全部唯一命中，无截断无冲突；gold/DeepSeek 都 RESOLVED_FULL；install 3.7 s + test 39 s，本包最便宜；只有 F2P 覆盖偏窄（单样例、只 axis=1） | ready_for_probe | 真机全量跑 `modin/numpy/test/test_array.py` 验证扩展断言 |
| modin-project__modin-6937 | 127 个 P2P 键各折叠多个运行时测试（最大一个键 = 108 个测试，2355 常量 ↔ 3060 实际测试）；124 个 skip 在 status_map 里不可见、反塞 5 个垃圾键 `[48]/[64]/…`；19 个 s3 用例因镜像 moto 版本不认 `moto_server s3` 各重试 50 次才 ERROR；题面把 gold 要改的那行源码原样打印出来 | needs_review | 同时导出 `-rA` 与 junitxml，量化折叠比例（预期 3060→2355） |
| modin-project__modin-6780 | 3 个 P2P 因反斜杠层级 missing → gold 恒判 RESOLVED_NO；102 个折叠键吞掉 362 个 ID；**题面复现代码写错**（`pd.Series(True, False, False)` 不是 `pd.Series([True,False,False])`）；base 有 28 条常红用例（`__add__() got an unexpected keyword argument 'level'`），测试段 rc 恒为 1 | needs_repair | `pytest --collect-only` 导出运行时 ID 对拍；base 上复跑确认 28 条常红集合 |
| modin-project__modin-5940 | **P2P 里 19 条 s3 用例**：`test_read_parquet_s3[object-pyarrow]` 直连真实 `modin-datasets.s3.amazonaws.com`，离线两侧都 FAILED → gold 恒判 RESOLVED_NO；另 18 条靠 `eval_general`「两侧抛同类型异常即通过」空洞通过；测试段 1379 s，本包最贵 | needs_repair | 有网/无网各跑一次 `-k s3`，确定要剔除的 P2P 范围 |
| modin-project__modin-6400 | ID 干净（10 个折叠键各只吞 1 条）、gold RESOLVED_FULL、install 3.4 s + test 401 s；F2P 只覆盖 gold 两处改动中的第二处，二维 modin array 那处零测试保护 | ready_for_probe | 构造 `array(np.array([[1],[2],[3]]))` 调 insert，确认 base/gold 差异存在 |
| pandas-dev__pandas-51605 | 13 个 ID 全唯一命中、gold RESOLVED_FULL、题面明写期望值，题目本身最干净；但 gold 是纯 Python 改动却要付 **829.6 s 的 setuptools 全量重编**（测试只要 5.0 s） | ready_for_probe | 镜像里试 `build_ext --inplace -j` 预热能否持久化，量化可省时间 |
| pandas-dev__pandas-53958 | **题面逐字给出 gold 的两行 import 并明写目标模块 `pandas.api.typing`**（leak 扫描 2/2 命中），几乎无搜索难度；F2P 只比较 `dir()` 名字集合、不验证对象身份，`NaTType = None` 也能满分；评分仅 15 s（meson 缓存） | needs_review | 用 `NaTType = None` 假补丁跑一次，确认被判 RESOLVED_FULL |
| pandas-dev__pandas-56849 | F2P 用 `match` 要求警告文本回显**小写 `m`**，而「先 `name.upper()` 再查表」这种等价实现会回显 `M` 被拒；题面对「要发 FutureWarning / 文本长什么样 / freq 是 ME」零信息；P2P 全绿依赖 test_patch 自带的 `filterwarnings` 豁免正则 | needs_review | 写 `name = name.upper()` 的替代补丁跑一次，确认被判 RESOLVED_NO |

## 跨题发现

### A. 参考 ID 有两种坏法，影响 7/10 题，后果完全不同（P1）
- **转义层级不一致**（48106 3 条、50319 1 条、6780 3 条，共 7 条 P2P）：常量是单反斜杠 `Period\('2017',` / `%Y\%m\%d` / `([ab])(\d)`，运行时 pytest 打的是双反斜杠。gold 与 empty **两侧都 missing** ⇒ **gold 恒判 RESOLVED_NO，这三题在 RL 里恒定 0 奖励**。这正是 `task_signals_swegym.json` 里 `fragile_reference_id: true` 的具体机制。
- **截断折叠**（6937/5940 各 127 键、6780 102 键、6400 10 键、56849 4 键、48106/50319 各 2 键）：常量与运行时**一致地**被按空白截断，所以不 missing，但一个键代表多个测试。最极端的 `modin/pandas/test/test_io.py::TestCsv::test_to_csv[None-New` **一个 P2P 键 = 108 个运行时测试**；parser 是 `test_status_map[test_case[1]] = test_case[0]`（后写覆盖先写），所以只保留 `-rA` 摘要里最后打印那条的判定。候选弄挂组内 107 个、留最后一个通过，该 P2P 仍判 PASSED。
- 逐条佐证：`truncated_test_ids.json`。与 L1_moto_2 的 R8 是同一 parser 根因，但**转义层级这一支是本包新增的证据**（moto 侧是"两边一致地错"，这里是"两边不一致"）。

### B. 训练/评测划分必须按仓库 + 时间切（P1）
同仓库 40 对做 `git apply -R --check`，**18 对命中**——早期题的 golden_patch 逐字存在于晚期题的 base 里（pandas 7 对、modin 11 对），全部时间正向、无倒置。未命中的 22 对只是上下文漂移导致 `apply` 失败，**不能判为"不含"**（unknown）。佐证：`contamination_pairs.json`。

### C. modin 的 P2P 有大量"空洞绿灯"（P1）
`modin/pandas/test/utils.py` 的 `eval_general` 在 pandas 侧抛异常时，只要 modin 抛出**同类型**异常就算通过（`assert isinstance(md_e.value, type(pd_e))`）。离线时 modin-5940 的 18 条 s3 用例两侧都因 DNS 失败抛同类型异常 ⇒ 判 PASSED。这意味着**环境退化时，所有基于 `eval_io`/`eval_general` 的 P2P 会集体变绿并掩盖真实回归**。

### D. 被 skip 的测试在 status_map 里不可见（P2）
pytest `-rA` 对 skip 只打聚合行 `SKIPPED [48] <file>:<line>: <reason>`，parser 把 `[48]` 当成 nodeid。后果：(1) 124/122 个被跳过用例在 modin-6937/5940 的 status_map 里没有任何条目；(2) status_map 被塞进 `[48]/[64]/[4]/[2]/[1]` 等垃圾键；(3) **若某个 F2P/P2P 因缺可选依赖被 skip，它的表现是 missing 而不是 SKIPPED**，排障时容易误判成 ID 写错。本包 10 题的 F2P/P2P 都不含被跳过用例，判分未受影响。

### E. 评分成本按 pandas 的构建后端劈成两类，差 100 倍（P2）
setuptools 后端（48106 / 50319 / 51605）每次评分重编全部 Cython 扩展：install 779 / 825 / 830 秒，而测试只要 4–13 秒；meson-python 后端（53958 / 56849）靠镜像里的 `/testbed/build/cp310` ninja 缓存，install 7.7 / 49.7 秒。modin 侧 install 一律 3.4–3.7 秒，成本全在测试段（39 s 到 1379 s）。本包 10 题一次 gold 评分的墙钟合计约 **99 分钟**，其中 modin-5940 + modin-6937 占 44 分钟、三道 setuptools pandas 占 41 分钟。

### F. 两个仓库都有 agent 不可见的隐藏实现约束（P1/P2）
- pandas-56849：F2P 的 `match` 固化了「警告里回显小写 `m`」；P2P 全绿依赖 test_patch 自带的 `filterwarnings` 豁免正则。
- pandas-53958：`Base.check` 是命名空间**全等**比较，多留任何顶层名都会失败。
- pandas-48106：题面说「放大时 categorical 转 object」，15/16 个 F2P 要求相反（保持 category）。
- pandas-50319：题面写「return None **或** 猜出格式都行」，F2P 只认后者。
这四条都不是"测试太严"，而是**公开材料与判分标准方向不一致**，会稳定地把合理解答判成 0。

### G. 环境前提清单（供准入检查用，P2/P3）
- modin：`modin/conftest.py` 模块级 `import boto3 / requests / s3fs`；`setup.cfg` 的 `addopts` 带 `--cov`（pytest-cov 是硬依赖）；引擎实测是 **PandasOnRay** 且 `/dev/shm` 只有 64 MB（日志自述"需要至少内存的一半 = 24.6 GB"），容器要显式加 `--shm-size`；引擎由运行时探测决定，agent 动 pip 环境会静默切换引擎。
- pandas：`addopts` 含 `--capture=no`，测试期 stdout 直通日志 + parser 只认行首状态词 ⇒ 候选可在被判分源码里 `print("PASSED <nodeid>")` 伪造状态（本包实测未被利用，测试段内伪状态行 = 0）；2.1/3.0 的 `filterwarnings` 首条是 `error:::pandas`，候选引入新警告会直接把同批测试变成错误。

## 收尾

**覆盖数：10 / 10**（`ASSIGNMENT.json` 全部完成，每题一份 `records/<instance_id>.json`）。
处置建议分布：`needs_repair` 4（48106、50319、6780、5940）、`needs_review` 3（6937、53958、56849）、`ready_for_probe` 3（6298、6400、51605）。
检查项：pass 105、issue 45（未使用 `unknown` 作为检查状态；个别 note 里标注了未核实项）。问题严重度：P1 14、P2 12、P3 7。静态审查合计约 265 分钟（题级自估）。

**未做 / 未验证清单**
- 所有 `next_experiment` **一次都没跑**（本包按 COMMON.md 不启动 Docker、不装依赖、不连远程机器，只做静态审查）。最该先跑的三条：(1) 在真机镜像上 `pytest --collect-only -q` 导出运行时 ID 全集，把 A 类的 7 条转义不一致常量一次性坐实；(2) modin-5940 有网/无网各跑一次 `-k s3`，确定要剔除的 P2P 范围；(3) pandas-56849 用 `name = name.upper()` 的替代补丁验证会被判 RESOLVED_NO。
- `contamination_pairs.json` 里未命中的 22 对是 `git apply -R --check` 上下文漂移，**不能当作"不含污染"**，状态是 unknown；216 题的全量污染扫描未做。
- modin 的 `filterwarnings = error:.*defaulting to pandas.*:UserWarning` 名义上应把 default-to-pandas 警告转成错误，但 6937 日志里它们仍是警告形态。**机制未核实，记 unknown。**
- modin-6780 那 28 条常红用例是"上游该 commit 本身就红"还是"镜像组合问题"，**未核实**。
- 本包 10 题里只有 48106（e2 A/B）、50319（e2 B）、6298（e2 B）、6937（e2 A/B）有 e2 记录；DeepSeek 候选只有 48106（RESOLVED_NO）、50319（RESOLVED_NO）、6298（RESOLVED_FULL）、6937（RESOLVED_NO）四条，其余六题没有候选轨迹可交叉验证。所有"某某假修复能拿满分"的判断都是静态推理 + 证据引用，**未经实跑确认**。
- 没有读 `rh2/src` 之外的接线代码去确认 v2 入口是否确实只解析 `>>>>> Start/End Test Output` 之间的段；P3 里关于 `pip's` 伪影不影响现网的结论依赖 COMMON.md 转述的既有约定，**未独立核对**。

**最值得用户裁定的 3 个问题**
1. **7 条转义层级不一致的 P2P 常量怎么处置？** 它们让 48106 / 50319 / 6780 三题的 gold 恒判 RESOLVED_NO，占本包 30%。可选项：(a) 直接从常量里剔除；(b) 按运行时实际 ID 重写常量并锁定 pytest 版本；(c) 在 parser 侧做转义归一。(a) 最省事但改变判分口径，(b) 与上游数据集不再逐字一致，(c) 偏离"逐字移植上游 parser"的既有约定。这条与 L1_moto_2/L1_moto_3 报的同一根因，建议统一定夺。
2. **P2P 的"名义条数"要不要纠正为"独立信号数"？** modin-6937/5940 名义 2354/1931 条 P2P，实际只覆盖 2228/1804 组、其中 127 组各只留一个代表；再叠加 C（`eval_general` 空洞通过）与 M3（19 条 s3 依赖外部服务），modin 题的 P2P 保护力被系统性高估。是接受上游口径不动，还是在题级记录里登记"折叠倍率"并对 N>1 的键降权？后者会让分数与上游 SWE-Gym 不可比。
3. **题面与判分方向不一致的四题（48106 / 50319 / 53958 / 56849）怎么办？** 48106 与 50319 是"照题面字面实现必挂"，56849 是"等价实现因警告文本大小写被拒"，53958 是"题面逐字给出答案、F2P 只查名字不查身份"。是剔除、改写题面、还是保留并在解题率统计里单列？另外 53958 这类"只改公共命名空间导出"的题，是否还值得放进 RL 题单（gold 就是把题面里的两行贴进一个 `__init__.py`）？
