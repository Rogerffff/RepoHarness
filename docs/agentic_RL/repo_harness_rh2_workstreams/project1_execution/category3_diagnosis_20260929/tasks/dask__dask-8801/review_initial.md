# dask__dask-8801：独立复核初判（封存稿）

2026-09-29，独立复核者。本稿写于读作者 `result.md`、`evidence/` 以及 `rh2/experiments/category3_cloud_20260929/dask8801/` 下除 gold 与原 test_patch 以外文件之前；写完不再修改。

**已读范围**：标准 v1 全文（重点 §3 P5/T1/T2、§4、§5、§9）；`s2/ingest/` 三个 jsonl 中本题记录（题面、public_hints、gold、test_patch、F2P 2 项、P2P 41 项）；既有调查 `quality_batch01_20260921/results/dask__dask-8801/` 的 `card.md`、`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`review.md`；镜像 `c3keep/dask8801:src` 中 `/testbed/dask/config.py`（1–290、400–480、640–720 行）、`dask/tests/test_config.py:95–137`、`docs/source/configuration.rst:50–140` 与关键词检索。`dask8801/` 目录只看到了文件名列表（`ls`），未打开任何文件。

**已运行**（一次性容器 `rv8801-review-*`，root，`--network none`，base 未改）：
- 目录里放 `a.yaml` 内容 `{`：`collect_yaml` 抛 `yaml.parser.ParserError`，消息里的位置是 `"<unicode string>"`，**不含文件名**；
- 内容 `hello`：`collect_yaml` 返回 `['hello']`，`collect(paths=..., env={})` 抛 `AttributeError: 'str' object has no attribute 'items'`；`DASK_CONFIG=<该目录> python -c "import dask"` 复现题面同一栈尾（`config.py:114 update`）。

## (a) 题面核心要求

题面是求助帖，标题 “Dask config fails to load”，没有“期望行为”段。能确定的只有：某个配置文件的顶层是字符串，`import dask` 在 `refresh → collect → merge → update` 里以 `AttributeError: 'str' object has no attribute 'items'` 崩溃，用户看不出是哪个文件、什么原因。按“一般性理解”，核心要求是：**顶层不是映射的配置文件不应再以内部 `AttributeError` 崩在合并阶段，用户应能知道是哪个文件、出了什么问题**；同时保留正常映射合并、搜索路径、环境变量优先级与不可读文件的忽略。

题面**没有**提到 YAML 语法错误。隐藏测试 `test_collect_yaml_malformed_file` 要求语法错误也包成带路径的 `ValueError`，这比题面多出一块（见 (c)、(d)）。

## (b) “报错并点名文件” vs “警告后跳过”的公开依据

| 读法 | 公开依据 | 强弱 |
| --- | --- | --- |
| 报错并点名文件 | ① base 对**内容错误**的现行政策就是致命：语法错误直接抛 `yaml` 异常（上面实跑），只是不点名文件；② `collect_yaml` 注解 `list[dict]`、`merge(*dicts: Mapping)`、`configuration.rst:55–94` 把 YAML 文件描述为键值映射，非映射违反契约；③ 同模块对无效配置值已有 `raise ValueError('Configuration value "..." has been removed')` 的先例（`config.py:649`） | 直接：同一函数、同一类输入的现行行为 |
| 警告后跳过 | ① 同一函数对 `OSError` 静默跳过，且有公开旧测试 `test_collect_yaml_permission_errors`；② 用户诉求是“能 import”；③ `collect_env` 对 `literal_eval` 失败静默回退为字符串；`get` 对改名键用 `warnings.warn` | 类比：跳过只针对权限错误，注释写明 “Ignore permission errors”，base 对语法错误并不跳过 |

初判：**两种读法都能找到公开材料，但强度不对等**。base 在同一函数里已经把“读不到（权限）→跳过”和“内容坏（语法）→报错”分开处理，报错读法有直接依据；跳过读法只有跨错误类别的类比。我倾向于认为 P5 第一分支（测试读法有公开依据 → R-f 补一句）**站得住**，但这是判断题，不是无争议事实；若用户或 Codex 认为 OSError 先例足以构成“跳过”的依据，就落到第二分支，交用户。

另一个独立于 P5 的问题：异常**类型** `ValueError`。依据只有 ③ 这类同模块先例和 Python 惯例；对“顶层是 list 不是 dict”，`TypeError` 同样合乎惯例。若 R-f 句子写明 `ValueError`，需要说明依据，否则是把隐藏测试细节写进题面；若不写，抛 `TypeError` 的合理解会被误拒（T1）。

## (c) 隐藏测试断言了哪些细节

两个 F2P 都在 `tmpdir` 里写 `a.yaml`，调用 `collect_yaml(paths=[dir_path])`（传**目录**，不是文件）：

| 测试 | 输入 | 断言 |
| --- | --- | --- |
| `test_collect_yaml_malformed_file` | `b"{"` | `pytest.raises(ValueError)`；`repr(fil_path)` 在消息中（带引号的完整文件路径）；`"is malformed"`；`"original error message"` |
| `test_collect_yaml_no_top_level_dict` | `b"[1234]"` | `pytest.raises(ValueError)`；`repr(fil_path)`；`"is malformed"`；`"must have a dict"` |

没有公开依据的细节：三个英文短语、`repr` 引号格式；`ValueError` 依据偏弱（见上）。没有覆盖的：**题面自身的字符串顶层**（只测了 list）、数字/布尔等其它非映射、解析器原因是否真的保留（`"original error message"` 只是字面短语）、直接传文件路径的形态、`import dask`/`collect`/`refresh` 端到端。`test_collect_yaml_permission_errors[directory|file]` 不在 41 项 P2P 内；它们在 root 下连 base 都会失败（root 绕过 chmod），既有调查记录非 root grader（`rh2grader/54322`）下两项 PASS。

## (d) 合理实现与错误实现

**合理（应得 1）**：
- gold：`_load_config_file`，`OSError` 返回 None，其它异常包成 `ValueError(... {path!r} ... is malformed, original error message ...)`，非 None 非 dict 抛 `ValueError(... must have a dict ...)`；
- 同样结构、换措辞（如 `Invalid Dask config file '{path}': expected a mapping at the top level, got list`）→ 原测试因短语误拒（T1）；
- 路径不加 `repr` 引号（`{path}`）→ 原测试误拒（T1）；
- 非映射抛 `TypeError`、语法错误抛带路径的 `yaml.YAMLError` → 原测试因类型误拒（T1/P5 边界）；
- 用 `Mapping` 判断、保留 `or {}` 使 `false/0/''` 仍视为空配置 → 原测试不区分，可接受；
- 只修非映射、不包装语法错误 → 按题面字面是完整修复，但会挂 `malformed_file`；是否算误拒取决于“语法错误点名文件”算不算核心要求（我倾向算“同一核心要求的另一实例”，但需要 R-f 句子覆盖）。

**错误（应得 0）**：
- 只拒 `list`（`isinstance(data, list)`），题面自己的字符串仍崩在 merge → 原测试**会给 1**（静态推断，第二步实跑）→ §4 第 3/4 步 S1；
- 把 `OSError` 也包成 `ValueError`（不可读文件变致命）→ 原测试给 1，破坏有公开测试的权限忽略行为 → S1；只有把 `permission_errors[file]` 加进 P2P 且非 root 评分才能拦；
- 消息只写字面 `"original error message"` 却丢掉解析器原因 → 原测试给 1；
- 校验只放在“目录枚举到的文件”上、不管直接给出的文件路径（`DASK_CONFIG=/path/x.yaml` 是公开用法）→ 原测试（只传目录）给 1；
- 静默跳过所有坏文件 / 吞错误 → 原测试给 0（正确拒绝）；
- 报错里只点目录名而不点文件名 → 原测试给 0。

## (e) 初判处置

- 严重度：**S1**。依据：§4 第 3/4 步（只拒 list、`OSError` 致命、丢原因三个候选预计在原测试下得 1，待实跑），外加 T1（短语、`repr`、类型）。
- 修订方向：R-b 把短语放宽为“消息含文件路径 + 原因”（非映射：类型名或“映射/dict”一类词；语法错误：解析器原文的一部分）；R-c 补字符串顶层（题面原例）与一个标量顶层、直接文件路径形态，把 `permission_errors[file]`（及 `[directory]`）加进 P2P，但要写明**只在非 root 评分下有效**，root 下 base/gold 都会挂；R-f 补一句“配置文件无法作为映射加载时应报错并指出文件”，依据见 (b)。是否写 `ValueError` 需单独给依据。
- P5：暂按第一分支；复核重点是作者给的依据是否足以排除“跳过”读法。
- 用途：SWE-Gym 修订机制按 D6 尚未实现，修订前**不进训练**；误拒未消解，按 §11 SWE-Gym 条只作问题定位。
