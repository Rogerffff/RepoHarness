# pandas-dev/pandas 与 modin-project/modin 仓库级共性事实（L1_modin_pandas，静态）

2026-09-16 夜 · 只读证据，未起容器、未装依赖、未连远程机器。
下面的结论对本包对应仓库的题共同适用；题级 JSON 用 `repo_level_findings.md#<锚>` 的方式引用，不逐题重抄。
证据里的相对路径都以 `${REPO_ROOT}/` 为根。
阶段一日志缩写：`LOG = runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<instance_id>/<gold|empty>/offline/a1/`。

---

## 第一节 · pandas-dev/pandas

### P1. 评分成本按构建后端劈成两类：setuptools 约 13 分钟，meson 约 8–50 秒

`eval.sh` 的 install 阶段在打完候选补丁之后、跑测试之前执行
`python -m pip install 'numpy<2'; python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true; pip uninstall pytest-qt -y;`
（pandas 3.0 的 56849 没有 `numpy<2` 那一段）。实测各阶段墙钟（从日志里的 `RH2_PHASE_START/END` 时间戳算）：

| 题 | version | base 日期 | 后端 | install | test |
| --- | --- | --- | --- | --- | --- |
| pandas-48106 | 1.5 | 2022-08-15 | setuptools（`Building wheels for collected packages: pandas`） | 779.3 s | 13.3 s |
| pandas-50319 | 2.0 | 2022-12-17 | setuptools | 824.7 s | 4.3 s |
| pandas-51605 | 2.1 | 2023-02-23 | setuptools | 829.6 s | 5.0 s |
| pandas-53958 | 2.1 | 2023-07-01 | meson-python（`meson setup --reconfigure /testbed /testbed/build/cp310` + `ninja`） | 7.7 s | 5.2 s |
| pandas-56849 | 3.0 | 2024-01-12 | meson-python，增量只重编 `offsets.pyx`（日志里是 `[3/4] Compiling C object ... offsets.cpython-310-...so.p/...`） | 49.7 s | 6.5 s |

证据：各题 `LOG/eval.sh` 与 `LOG/test_output.txt`（`RH2_PHASE_*` 行）。

含义：**三道 setuptools 后端的题（48106 / 50319 / 51605）每次评分要付约 13–14 分钟纯重编，而其中 51605 的 gold 是纯 Python 改动。**
若一次 rollout 评两遍（前后各一次），单题就是 26 分钟。选题单时这条比题目本身的难度更影响预算。

### P2. `.pyx` 修复点对 agent 的自测反馈是断的（50319、56849）

50319 的 gold 改 `pandas/_libs/tslibs/parsing.pyx`，56849 的 gold 改 `pandas/_libs/tslibs/offsets.pyx`。
评分是对的（`eval.sh` 在 setup/test 之前重跑 install，所以补丁会被编译），但 **agent 在 rollout 内改完 `.pyx` 后，不自己重编就跑不出任何变化** —— 已加载的 `.so` 不变。
setuptools 后端下这一轮自测约 13 分钟，meson 后端下约 50 秒（增量）。
证据：`validation.golden_patch`（两题目标文件）、各题 `LOG/eval.sh` 的 install 段、56849 `LOG/test_output.txt` 的 ninja 增量行。

### P3. `addopts` 含 `--capture=no`，测试期 stdout 直通日志，构成状态行注入面

四道 pandas 题的 base 都有
`addopts = "--strict-data-files --strict-markers --strict-config --capture=no --durations=30 --junitxml=test-data.xml"`
（3.0 的 56849 去掉了 `--strict-data-files`）。
证据：`repos/pandas@{8b72297c,1613f26f,b070d87f}:pyproject.toml` 与 `@612823e8:pyproject.toml` 的 `[tool.pytest.ini_options]`。

SWE-Gym parser 的判据是"整行以 `PASSED|FAILED|SKIPPED|ERROR|XFAIL` 开头 → 取第二个空白分词当 nodeid"
（`rh2/src/repoharness2/envpack/swegym_parsers.py` 的 `parse_log_pytest`：`test_status_map[test_case[1]] = test_case[0]`）。
两者叠加意味着：**候选可以在被判分的非测试源码里 `print("PASSED pandas/tests/x.py::test_y")` 直接伪造状态**。
本包四道 pandas 题的阶段一日志里，测试段内伪状态行都是 0（实测未被利用），只有 48106 与 53958 的 **安装段** 有一条 `ERROR: pip's dependency resolver ...`，被解析成 `status_map["pip's"] = "ERROR:"`。
该行落在 `RH2_PHASE_START test` 之前（48106 里是日志第 6056 行 vs 第 6082 行），所以**只要 v2 入口按约定只取 `>>>>> Start/End Test Output` 之间的段，就不会吃到它**；这是阶段一离线日志的伪影，不是现网缺陷。
证据：`LOG/status_map.json`（`pip's` 键）、`LOG/test_output.txt` 行号。

### P4. `filterwarnings` 在 2.1/3.0 把 pandas 自己发的警告转成错误

`repos/pandas@b070d87f:pyproject.toml` 与 `@612823e8:pyproject.toml` 的 `filterwarnings` 首条是 `"error:::pandas"`。
含义：候选若引入新的 `FutureWarning/DeprecationWarning`，同批测试会直接报错而不是警告。
56849 就是实例：test_patch 专门给 `pandas/tests/tslibs/test_to_offset.py::test_to_offset` 加了
`@pytest.mark.filterwarnings("ignore:.*'m' is deprecated.*:FutureWarning")` 来豁免修复新引入的警告。
**也就是说这道题的 P2P 能全绿依赖 test_patch 里那条豁免正则，而不是候选本身** —— 候选若把警告文本写成不匹配该正则的形状，P2P 会连带转红，而 agent 看不到这条约束。
证据：`LOG/eval.sh`（56849 的 test_patch 全文）、`repos/pandas@612823e8:pyproject.toml`。

### P5. 反斜杠转义层级不一致，让 3 道题里共 4 条 P2P 常量永远 missing

数据集常量里是**单反斜杠**，运行时 pytest 打印的是**双反斜杠**：

- 48106：常量 `...test_contains_raise_error_if_period_index_is_in_multi_index[Period\('2017',`；运行时 `...[Period\\('2019', 'A-DEC'\\), ...]`（`LOG/test_output.txt:6164-6170`）。3 条。
- 50319：常量 `...test_is_iso_format[%Y\%m\%d`；运行时 `...[%Y\\%m\\%d %H:%M:%S-True]`（`LOG/test_output.txt:6247`）。1 条。
- （modin 侧同样命中，见 M5。）

这些常量在 **gold 与 empty 两侧都 missing**，所以 gold 必然判 RESOLVED_NO。这正是 `task_signals_swegym.json` 里 `fragile_reference_id: true` 的具体机制。
与 L1_moto_2 记的 R8（按空白截断、两边"一致地错"、异常被吞掉）不同：**这里两边不一致，异常表现为永久 missing，直接把整题奖励压成 0。**
逐条清单见 `truncated_test_ids.json` 的 `escape_mismatch`。

### P6. 判分文件边界：四道 pandas 题的 test_patch 全部只碰 `pandas/tests/` 下既有文件

无一例新建/删除文件，也无一例碰到非测试源码。
证据：`test_patch_new_files.json`（`created` 全为空）。
因此第四组 B 的"`test_files` 由 test_patch 触碰路径生成会把正常源码恢复覆盖"这一残余风险在本包 pandas 侧未出现，`additional_exclusions` 逐题为 `[]`。
另注：`test-data.xml`（`--junitxml` 产物）与 `*.so` / `*.c` 在四个 base 的 `.gitignore` 里都已忽略（`@8b72297c:.gitignore:37,100,109`；3.0 在 `:73,108,110,120` 且额外 `!pandas/_libs/src/**/*.c`），构建产物不会污染候选 diff。

---

## 第二节 · modin-project/modin

### M1. 引擎在运行时自动探测，实测是 Ray；`/dev/shm` 只有 64 MB

`Engine._get_default()` 按 ray → dask → hdk → unidist 的顺序探测，都没有才退回 `"Python"`
（`repos/modin@d54dcfd8:modin/config/envvars.py:186-246`）。
阶段一日志证实实际用的是 **PandasOnRay**（`LOG/test_output.txt` 里成片的 ``UserWarning: `to_csv` is not currently supported by PandasOnRay, defaulting to pandas implementation.``）。
同一份日志里有一条：
`UserWarning: The size of /dev/shm is too small (67108864 bytes). The required size at least half of RAM (26413930496 bytes). ... increase size of /dev/shm with --shm-size in Docker.`
（modin-6937 `LOG/test_output.txt:2187`）。

含义两条：
1. **容器要显式加大 `--shm-size`**，否则 Ray 的对象存储退化到磁盘溢写，是 modin 题动辄 7–23 分钟的部分原因。
2. **引擎是环境的隐式函数**：agent 若在 rollout 里 `pip install/uninstall` 动了 ray/dask，引擎会静默切换，P2P 结果会整体改变。这条目前没有任何准入检查兜着。

### M2. `modin/conftest.py` 模块级 import `boto3` / `requests` / `s3fs`，是全仓测试的硬前提

`repos/modin@d54dcfd8:modin/conftest.py:25-30`。缺任一包 → 整份收集失败，而不是单个测试 skip。
本包五道 modin 题的测试文件本身（`test_array.py` / `test_series.py` / `test_map_metadata.py`）并不用 S3，但都受这条约束。

### M3. S3 用例分两类，都不是自足环境；5940 因此 gold 恒判 RESOLVED_NO

- **本地 moto server 类**：`modin/conftest.py` 的 `s3_base` fixture 用 `subprocess` 起 `moto_server s3 -p 555<worker_id>`（单 worker 时端口 5000），只建 `modin-test` 桶，连不上就重试 50 次再 `RuntimeError`（`@d54dcfd8:modin/conftest.py:620-745`）。
  modin-6937 的镜像里 moto 已是新版 CLI，不认 `moto_server s3` 这种旧写法，19 个 s3 用例全部 ERROR：
  `RuntimeError: Could not connect to moto server after 50 tries. See stderr for extra info: b'usage: moto_server [-h] ... moto_server: error: unrecognized arguments: s3\n'`（modin-6937 `LOG/test_output.txt`）。
  modin-5940（0.23 镜像）里同一 fixture 起得来，18 条 s3 读通过。**同一晚、同一宿主、不同镜像，行为相反。**
- **真实 AWS 类**：`test_read_parquet_s3*` 直接读公共桶 `s3://modin-datasets/...`（`@e1d42410:modin/pandas/test/test_io.py:1635-1656,1786-1793`）。
  离线下 modin-5940 的 `TestParquet::test_read_parquet_s3[object-pyarrow]` 报
  `aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host modin-datasets.s3.amazonaws.com:443 ssl:default [Temporary failure in name resolution]`。
  **这一条在 5940 的 P2P 里，gold 与 empty 两侧都 FAILED ⇒ gold 恒判 RESOLVED_NO。** 这就是 5940 stage1 gold 非 FULL 的全部原因（`f2p_missing=0`、`p2p_missing=0`，只有这一条 `p2p_notpass`）。

### M4. `eval_general` 把"两侧抛同类型异常"算作通过 —— 环境坏掉时 P2P 集体空洞通过

`repos/modin@e1d42410:modin/pandas/test/utils.py:896-913`：

```
try:
    pd_result = fn(pandas_df, **pd_kwargs)
except Exception as pd_e:
    if check_exception_type is None: return None
    with pytest.raises(Exception) as md_e:
        repr(fn(modin_df, **md_kwargs))
    if check_exception_type:
        assert isinstance(md_e.value, type(pd_e)), ...
```

离线时 18 条走 `eval_io` 的 s3 用例两侧都因网络失败抛同类型异常，于是**判 PASSED**。
这不是 s3 专属：**modin 里所有基于 `eval_io`/`eval_general` 的 P2P，在环境退化时都会变成无信息的绿灯，掩盖真实回归。**

### M5. 截断与折叠在 modin 上比 pandas 严重一个量级

modin 的测试大量使用含空格的参数 id（`"New index"`、`"separator data"`、`"empty sep"`、`"plus one"`），
而 SWE-Gym 的参考集与 RH2 的 parser 都按空白切第一个分词当 nodeid，**后写覆盖先写**。实测（`collide_detail.json` / `truncated_test_ids.json`）：

| 题 | 常量数 | 运行时实际测试数 | 折叠键数 | 被吞掉的额外 ID | 最大一组 |
| --- | --- | --- | --- | --- | --- |
| modin-6937 | 2355 | 3060 | 127 | 705 | **108**（`test_to_csv[None-New`） |
| modin-5940 | 1935 | 2640 | 127 | 705 | 108（同一批键，同一测试文件） |
| modin-6780 | 2837 | 3196 | 102 | 362 | 25（`test_str_slice_replace[empty`） |
| modin-6400 | 692 | 702 | 10 | 10 | 2 |
| modin-6298 | 39 | 39 | 0 | 0 | — |

含义：`test_to_csv[None-New` 这**一个 P2P 键代表 108 个运行时测试**，最终记录的是 `-rA` 摘要里最后打印那条的判定。
候选把组内前 107 个弄挂、只留最后一个通过，该 P2P 仍判 PASSED。**P2P 的实际保护力远低于名义条数。**
另外 modin-6780 有 3 条 P2P 命中 P5 的反斜杠层级问题（常量 `test_str_extract[([ab])(\d)-...` vs 运行时 `([ab])(\\d)`，`LOG/test_output.txt:9047-9049`），gold 恒判 RESOLVED_NO。

### M6. 被 skip 的测试在 status_map 里完全不可见，还会塞进垃圾键

pytest `-rA` 对 skip 只打**聚合行**：`SKIPPED [48] modin/pandas/test/test_io.py:321: some parameters combiantions fails: issue #2312`。
parser 取第二个分词 `[48]` 当 nodeid，于是：

- modin-6937 的 124 个被跳过用例在 `status_map.json` 里没有任何条目，`status_map` 反而多了 `['[48]','[64]','[4]','[2]','[1]']` 五个垃圾键；modin-5940 同理（122 个 skip → 四个垃圾键）。
- 本包这两题的 F2P/P2P 都不含被跳过的用例，所以判分未受影响。
- **但这条决定了排障形态**：如果某个 F2P/P2P 因缺可选依赖被 skip，它在 status_map 里是 **missing 而不是 SKIPPED**，容易被误判成"ID 写错"。

跳过原因里有几条值得记：`test_io.py:2561: Skip the test when the test SQL server is not set up.`、`:2586: postgres server is not set up`、`:2914/:2922: Can not pass without GBQ access`、`:2765: No clipboard in CI` —— 这些都是"外部服务缺失就跳过"的自我保护，上游把它们排除在 P2P 之外是对的。

### M7. `setup.cfg` 的 `addopts` 带 coverage，`filterwarnings` 把 default-to-pandas 警告转错

- 0.23（`@5cd15a51`/`@2a6aafed`）与 0.25（`@76d741be`）：`addopts = --disable-pytest-warnings --cov-config=setup.cfg --cov=modin --cov-append --cov-report=`
- 0.27（`@d54dcfd8`）：`addopts = --cov-config=setup.cfg --cov=modin --cov-append --cov-report= -m "not exclude_by_default"`
- 三个版本都有 `xfail_strict=true` 与 `filterwarnings = error:.*defaulting to pandas.*:UserWarning`

证据：各 base 的 `setup.cfg` `[tool:pytest]` 段。

含义：(a) **pytest-cov 是硬依赖**，缺了 pytest 会因无法识别 `--cov` 直接失败；(b) coverage 追踪跑在 2800–3000 个用例上，是 modin 题墙钟成本的一部分；(c) `--cov-append` 会往仓库根写 `.coverage` 并跨次累积；(d) 0.27 用 `-m "not exclude_by_default"` 主动反选一部分测试。
关于 (e)：`filterwarnings` 名义上把"defaulting to pandas"的 UserWarning 转成错误，但 6937 的日志里这些警告是以**警告**形态出现在 warnings summary 里、没有变成错误；具体机制（是否被 `catch_warnings` 吞掉、或 `--disable-pytest-warnings`/插件次序影响）**未核实，记 unknown**。

### M8. modin 题的 install 极便宜，成本全在测试段

`pip install -e .`，3.4–3.7 秒，rc=0，无编译扩展、无下载。
测试段：6298 = 39.3 s / 6400 = 401.2 s / 6780 = 452.5 s / 6937 = 1271.4 s / 5940 = 1378.7 s。
其中 6937、6780、5940 的测试段 **rc=1**（gold 侧仍有既有失败），所以**不能用测试段 rc 当健康判据**。
6780 的 28 条常红用例全是 `test___<op>__` 家族，报 `TypeError: __add__() got an unexpected keyword argument 'level'` 后被 `pytest.warns` 判 `DID NOT WARN`；它们被上游排除在 P2P 之外。

---

## 第三节 · 跨仓库共性（两个仓库都成立）

### X1. 训练/评测划分必须按"仓库 + 时间"切，不能随机切

用 `git apply -R --check` 检查"A 的 golden_patch 是否已逐字存在于 B 的 base"，同仓库 40 对里 **18 对命中**（`contamination_pairs.json`）：

- pandas：48106 的 gold 在 50319 / 51605 / 53958 / 56849 的 base 里；50319 的 gold 在 51605 / 53958 / 56849 的 base 里；53958 的 gold 在 56849 的 base 里。
- modin：6298 的 gold 在 6937 / 6780 / 6400 的 base 里；5940 的 gold 在 6298 / 6937 / 6780 / 6400 的 base 里；6400 的 gold 在 6937 / 6780 的 base 里；6780 的 gold 在 6937 的 base 里。

全部是**时间正向**（早期题的答案出现在晚期题的 base 里），没有倒置（base commit 日期见下）。
未命中的 22 对只是 `git apply -R --check` 因上下文漂移失败，**不能判为"不含"**，记 unknown。

base commit 时间序：
modin 5940 (2023-06-16) → 6298 (2023-06-26) → 6400 (2023-07-19) → 6780 (2023-11-29) → 6937 (2024-02-14)；
pandas 48106 (2022-08-15) → 50319 (2022-12-17) → 51605 (2023-02-23) → 53958 (2023-07-01) → 56849 (2024-01-12)。

### X2. 参考 ID 的两种坏法要分开处理

- **截断/折叠**（P5 的另一半、M5）：常量与运行时**一致地被截断**，所以不 missing，但一个键代表 N 个测试，判定被压缩。影响 7/10 题。
- **转义层级不一致**（P5、M5 末段）：常量单反斜杠、运行时双反斜杠，**永久 missing**，gold 恒判不通过。影响 3/10 题（48106、50319、6780），共 7 条 P2P。

两者的修法不同：前者要换 ID 来源（junitxml / json-report），后者可以直接剔除或按运行时重写常量。
逐条清单：`truncated_test_ids.json`。
