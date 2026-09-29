# dask__dask-6801 公开静态审查

## 题面先读结论

公开题面要求修复多个 DataFrame 共享 delayed 上游时，联合 `dask.compute` 写入 Parquet 导致重复执行的问题。示例有两个 `create_2_dataframes` delayed 调用，每个返回两个 DataFrame；合理目标是在一次联合计算中每个调用执行一次，即共两次，而不是普通写入四次、`schema="infer"` 写入八次。三个独立 `dask.compute` 调用之间不应推定有缓存或只执行一次的要求。

在读源码前可合理保留的旧行为：`meta=df` 避免 `from_delayed` 为确定结构额外执行用户代码；`compute=False` 返回可联合计算的对象；写入正确的分区数据、索引和 Parquet 元数据；显式 schema 和默认写入保持可用。题面没有明确要求具体实现方式、跨 compute 缓存或更改 scheduler。

初始疑义：未指定 Parquet 引擎及其版本；八次日志可能混合构图阶段与最终计算；两个输出写入同一个 `/tmp/test` 可能覆盖；object 列推断是否必须读取真实数据、如何兼顾现有类型推断语义尚不明。以上为读源码前的问题，后续消解程度如下。

公开 `public_bundle.json.public_hints` 声明应只改 NON-TEST 源码、不得改测试，并允许窄范围验证；另声明 `/testbed` 与预激活 conda `testbed`。这只是来源声明；`environment_brief.md` 明确实际消息交付及环境均未捕获。审查派发卡的只读/禁执行边界属于本轮审查规则，不是原题功能要求。

## 公开源码与旧测试支持的判断

以下源码路径均相对于本题 `PUBLIC_DIR/base/`；PUBLIC_DIR 为 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-6801`。

1. `dask/dataframe/io/io.py:587–599`：显式 meta 走 `make_meta(meta)` 而非对第一个分区 `.compute()`，并合并各 delayed 的图。题面已经排除常见的 `from_delayed` 元数据采样原因。
2. `dask/dataframe/io/parquet/core.py:540–572`：先执行引擎初始化，再用 `df.to_delayed()` 构造逐分区写任务。`dask/dataframe/core.py:1474–1497` 明确 `to_delayed` 默认先优化图；`dask/dataframe/optimize.py:12–41` 包含 blockwise/root fusion 及条件性低层 fuse。每个 DataFrame 在最终联合计算前独立优化，可能将共享上游融合进不同任务，提供了普通写入重复执行的具体候选机制。`dask/base.py:205–239` 在一次计算中按优化函数分组、抽取并优化图，支持“保留共同图直到联合计算”这一修复方向。这里只是静态因果分析，没有实测任务图，不能把精确四次视为已复现。
3. `dask/dataframe/io/parquet/arrow.py:834–873`：`infer` 或字典先以 `_meta_nonempty` 建 schema；仅 `infer` 且有 object 列并支持 schema field 时，循环分区并直接 `.compute()` 提取 schema，直到所需列获得非 null 类型。此初始化发生在 `compute` 判断之前，因此 `compute=False` 不阻止这部分执行。空 object 列示例可持续扫描所有分区，且两次写调用各自推断，能解释题面额外执行的机制。`arrow.py:24` 将此分支限定在 PyArrow >= 0.15.0。
4. `core.py:426–435` 的公开 API 文档明确旧 `infer` 从首个非空且非 null 分区推断 object 列；字典未覆盖字段来自 `_meta_nonempty`；`None` 逐分区推断；fastparquet 忽略 schema。`docs/source/dataframe-api.rst:450` 通过 autofunction 暴露该文档。因此只用 `_meta_nonempty` 替换真实采样会改变已有公开语义，特别是 object dtype 容纳列表、数字等非字符串值时。题面目标与采样兼容性的取舍未被完全消解。
5. `core.py:608–629`：auto 优先 fastparquet，再 pyarrow，最低 PyArrow 0.13.1。fastparquet `initialize_write`（`fastparquet.py:504–526`）还有独立的 `object_encoding="infer"` 拒绝逻辑，不能混同为题面的 schema 推断。未指定引擎的示例并非在所有安装组合下都会出现八次。
6. `core.py:553–554` 为每次写入生成 `part.N.parquet`，例子两次写同路径确有文件名重叠风险。计数验证可保留原题复现，同时使用两个独立临时子目录作诊断对照；不应将目录覆盖修复擅自升级为题目主要求。
7. 已读旧测试：`test_pyarrow_schema_inference`（1080–1124）覆盖 `infer`/字典、索引以及读回相等；`test_to_parquet_lazy`（1405–1415）检查可延迟对象与 threads/processes 写入；`test_delayed_no_metadata`（204–220，未读完函数）覆盖延迟且不写元数据；`test_timeseries_nulls_in_schema`（2124–2161）覆盖含 null 数据及 schema 选择；手动 schema 测试（991–1047，未读完函数）包含列表、字符串、时区时间；默认不一致 schema 测试（956–980，未读完函数）说明 `None` 与元数据验证的关系。已读测试均未直接检查共享 delayed 上游的执行次数，不能以这些回归通过代替题面计数验证。

## 合理实现范围与保留问题

可在 Parquet 图构造局部保留未分别优化的共享任务，再让联合计算优化；无需改变所有 DataFrame 的 `to_delayed` 默认行为。对 schema，可考虑把必要采样及其依赖放进同一延迟图并复用数据，但追加写入的初始化/元数据依赖也需核对。另一选择是基于已有 metadata 推断，并让更复杂的 object 内容使用显式 schema；该选择涉及上述公开语义变化，必须使文档与错误提示一致，不能凭题面认定它与旧行为完全等价。这里未见 gold，也不选定唯一实现。

应该分别验证构造输出对象前后及最终 compute 的调用数；一次正常完成、无重试的联合计算应只执行两个上游调用。用户代码有副作用时可用同步 scheduler 和计数器取得清晰证据；题面没有承诺故障重试下的严格 exactly-once。应覆盖空分区、全 null object、字符串及显式复杂类型 schema，避免只满足空 DataFrame 日志而损坏写入结果。

## 开发需求表

下列命令仅为未来实际 actor 核验建议，本轮没有执行；命令假定在经核验的 `/testbed` 仓库根目录运行，不针对静态导出执行项目。

| 操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
|---|---|---|---|
| 核对工作树与初始改动 | user_prompt 的 commit；base_identity 的精确导出身份 | 静态 base 为 `5589bfddb5982777d29e424fa438f1667a74a60a`；实际 HEAD/status/diff unknown | `pwd`、`git rev-parse HEAD`、`git status --short`：确认来源初态；差异需解释而非抹除 |
| 确认 actor 用户、工具与 Python 来源 | public_hints 声明 bash/edit、conda testbed | 实际消息、权限、UID/HOME/cwd/PATH、环境激活 unknown | `id`、`command -v python`、`python -c 'import sys; print(sys.executable)'`：确认实际执行身份和解释器 |
| 本地 dataframe 与 delayed 依赖 | setup.py:10–31、70–74；测试 imports | 公开依赖声明可见；已安装版本和源码导入 unknown | `python -c 'import dask, pandas, numpy, fsspec, pytest; print(dask.__file__, dask.__version__, pandas.__version__)'`：成功并来自目标源码 |
| PyArrow 引擎及可选 fastparquet 对照 | core.py get_engine、arrow.py:24、测试 skip 条件 | 实际引擎/版本 unknown | `python -c 'import pyarrow; print(pyarrow.__version__)'`：覆盖 object 采样需 >=0.15.0 且与旧代码兼容；fastparquet 对照需另确认安装，不把 skip 当成功 |
| 可写本地临时目录 | 题面 `/tmp/test`；core.py 文件写入；旧测试 tmpdir | 实际写权限、磁盘、并发冲突 unknown | `python -c 'import tempfile; t=tempfile.TemporaryDirectory(); print(t.name); t.cleanup()'`：能创建并清理目录；无需远程数据、网络、GPU |
| 验证共享执行次数 | 原题最小示例、两处静态候选机制 | 运行次数与修复效果 unknown | `python -` 输入题面示例，显式 `engine="pyarrow"` 并分阶段计数；再以两个临时目录对照：普通及 infer 联合计算各两次，不随输出数翻倍；若调整推断语义，记录构图阶段行为 |
| 窄范围兼容性验证 | 已读公开旧测试符号 | 测试能否收集及通过 unknown | `python -m pytest dask/dataframe/io/tests/test_parquet.py -q -k 'pyarrow_schema_inference or to_parquet_lazy or timeseries_nulls_in_schema or delayed_no_metadata'`：目标引擎参数实际执行、读回及延迟写入成功；再针对修改涉及的显式/不一致 schema 测试补验 |
| 源码编辑与交付边界 | public_hints 的 NON-TEST/不改测试 | 实际编辑权限与该提示是否交付 unknown | `git diff --stat`、`git diff --name-only`：修改限定合理源码/文档范围，无测试改动；不能从静态 base 推定权限 |

## 阅读边界与证据限制

完整阅读了派发卡、public_reader 角色卡、user_prompt.txt、environment_brief.md、base_identity.json、public_bundle.json。对本题 base 做文件名清单及相关符号 rg 定位，真正阅读源码区段为：`core.py`（Parquet）368–605、605–644；`arrow.py` 1–48、800–930；`fastparquet.py` 500–550；DataFrame `core.py` 1474–1502；`optimize.py` 1–85；`dask/base.py` 205–250；`io/io.py` 552–620；`setup.py` 1–77；API 文档 440–454；Parquet 测试 1–85、204–220、956–980、991–1047、1080–1130、1395–1416、2120–2165。对 `dask/delayed.py` 仅做符号 rg，不声称读其实现。

未阅读全文库、全部测试、完整引擎写入/元数据/追加路径、底层融合算法和 scheduler；未跟随外部链接。没有读取私有、历史、其他题、其他角色结果或隐藏测试/gold；没有执行、导入项目、跑测试、联网、安装或修题。base 是静态 Git 导出，不是 actor 工作树；导出中有无文件不证明实际镜像有无资产。本文仅给出公开可解释性与开发条件的静态判断，不宣称隔离、无预训练污染、训练资格或实际 actor 资格。
