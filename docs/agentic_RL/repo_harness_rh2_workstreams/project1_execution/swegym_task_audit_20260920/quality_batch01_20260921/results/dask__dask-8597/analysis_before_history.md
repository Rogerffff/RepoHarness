# dask__dask-8597：读历史前的独立主审

2026-09-21。静态范围；未执行项目代码、安装、容器、SSH 或模型。已读本题公开阅读产物、原题、精确 base 导出、全部 test patch / gold、F2P/P2P 清单及所引运行原件；此稿保存时尚未获提供或读取本题历史调查，未读 reviewer 文件。所有 `runs/` 与 `rh2/` 引用均相对权威根 `${REPO_ROOT}`。

**初判：公开目标、唯一新增测试与 gold 一致，初态故障有真实 RH2 证据；没有发现误拒合理解或 gold 漏修原例的证据。存在一个具体评分回归缺口，宜先做定点 CPU 对照，再决定优先模型探针。** 状态保留 `needs_review` / `static_review`；actor 条件未验。这里不是判原题无效，也不把全模块成功等同所有旧行为进入奖励判定。

## 1. 材料、公开要求及初态

下文 `PUB` / `PRIV` 分别指 `runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597` 与同级 `private/dask__dask-8597`；`B` 指 `PUB/base`。公开 base 为 `c1c88f066672c0b216fc24862a2b36a0a9fb4e22`，tree 为 `bd0e4fc24106244ba2713e90efa250b78210d1e4`。`public_bundle.json`、`grading.json`、`validation.json` 已逐对象与 `source_refs.json` 指向的 S2 原件第 47 行比较，一致；两份独立 patch 文本与 bundle 内文一致。gold SHA-256 为 `e1ed047ba04029e62bc4fb82b16717dc7d6f7f7ce03ac859c2e0bb5e6aec22e4`。

正文要求 `da.from_array(np.zeros((3, 0)))[[0]]` 能构图，并得到与 NumPy 相同的 `(1, 0)`、float64 空结果。标题的“0-D”是术语不准确：输入为二维、含零长度轴，不是零维标量；正文不含需要猜测的新 API、错误字符串或补丁位置。公开仓库支持单轴整数列表、保留 Dask Array 与延迟语义、合法块信息、索引边界校验及大块配置行为（`B/docs/source/array-slicing.rst:4–22,51–98`；`B/dask/array/core.py:1797–1855`）。不能由标题推出要支持所有真正零维对象或已明示不支持的多轴高级索引。

调用链为 `from_array` 的默认自动分块 → `Array.__getitem__` / `normalize_index` → `slice_array` → `slice_with_newaxes` → `slice_wrap_lists` → `take` → 计算时的 `chunk.getitem`。示例 chunks 为 `((3,), (0,))`；`take` 用非索引轴尺寸乘积 `other_numel=0` 计算 `ceil(nbytes/(other_numel*itemsize))`，base 只特判 NaN（`B/dask/array/slicing.py:625–650`）。

这不是仅据 gold 差分推断：noop 原始日志 N:775–863 展示该完整栈、上述 chunks、`index=array([0])`、`axis=0`、`itemsize=8`，最终在 `slicing.py:647` 因除零 `RuntimeWarning` 失败。`B/setup.cfg:46–52` 将相关警告升为错误，因此日志先于题面 `OverflowError` 中止，仍是同一零分母根因，不是无关环境失败。

`public_hints` 的“预激活 conda”是声明；`user_prompt.txt` 为静态渲染，尚未捕获真实 CLI 消息。禁止改测试若生效不阻碍本题源代码修复；它的“所有测试编辑都会恢复”解释不能泛化为当前机制，具体恢复范围见第 6 节。

## 2. 新增断言与双向映射

test patch 仅在 `dask/array/tests/test_slicing.py` 尾部新增 `test_slice_array_null_dimension`（应用后 1070–1073 行），无 fixture、参数、Mock 或外部资产。测试分别构造两个 float64 `np.zeros((3, 0))`，一份经 `da.from_array` 默认 chunks，再作 `[0]` 列表索引；另一份直接作 NumPy 索引；唯一语句为 `assert_eq(array[[0]], expected)`。

F2P 共 **1 条**，就是该新增用例，已完整展开。`array[[0]]` 在进入 helper 前求值，故只把错误推迟或只改断言 helper 不能避开构图异常。`assert_eq` 对 Dask 输入验证图命名/层、persist 后每块形状与 dtype、同步计算后的形状、声明 dtype 与期望 dtype、元信息维数/后端类型以及数值（`B/dask/array/utils.py:192–225,229–340`）。空数组的值比较本身没有数据元素，但 `(1,0)`、dtype、有效图与可计算性并非空断言。

限制是这些 Dask 专有检查以 `isinstance(x, Array)` 为前提；单个 F2P **没有直接要求返回值必须为 Array**，若错误修复在空输入分支直接返回等形状 NumPy 结果，helper 可以接受。这是静态测试边界，不宣称已有候选实际拿到奖励。

| 公开要求／合理旧行为 | 公开依据 | 测试及决定性断言 | 覆盖结论与证据 |
| --- | --- | --- | --- |
| 原例不异常，结果 `(1,0)` / float64，能够计算 | `PUB/user_prompt.txt:5–34`；`B/docs/source/develop.rst:187–210` | F2P `test_slice_array_null_dimension`；`assert_eq` 计算、形状、dtype、块/图检查 | 直接覆盖；N:775–863 真失败，G:790,932 真通过 |
| 合法单轴列表、排序/乱序/重复、axis=1、块布局不退化 | 切片文档 `51–69`；`B/dask/array/slicing.py:585–703` | P2P `test_take`、`test_take_sorted`、`test_take_semi_sorted`、三参数 `test_slicing_plan`、`test_slicing_chunks` | 普通非空覆盖；断言图、块长度、局部索引，已读测试体并核日志 |
| 空列表/空切片、负列表、越界与布尔长度校验继续有效 | `normalize_index/check_index:855–984`；公开旧测试 | P2P `test_empty_list`（三轴）、`test_empty_slice`、`test_negative_list_slicing`、`test_oob_check`、两种 boolean slicing | 覆盖普通/结果为空的相邻行为；未验证零输入轴与所有无效索引交叉 |
| 普通非空 `split=True` 拆块，用户块尺寸配置生效，未知尺寸不错误拆分 | 文档 `88–98`；`take:638–703` | P2P `test_take_avoids_large_chunks`（四组，含 axis=1，具体 chunks 和图条数）、`test_take_uses_config`、`test_getitem_avoids_large_chunks_missing[chunks0]` | 直接覆盖这些分支；NaN 索引轴参数 chunks1 已 xfail，不能记通过 |
| 普通非空默认大块警告，显式 False/True 的用户行为 | 文档 `73–95`；`B/dask/dask.yaml:12–16` | 旧 `test_getitem_avoids_large_chunks:875–903` 同时检查默认警告、False/True、结果和 chunks | **实际执行但不在 P2P**；G:908 / N:747 为 PASS，仅证明 gold/noop 条件，不是奖励保护 |
| 普通小型整数列表不产生警告 | 旧 `test_slicing_integer_no_warnings:784–790` | `pytest.warns(None)` 记录为空 | **实际执行但不在 P2P**；G:898 / N:736 为 PASS |
| 空轴在其它位置、显式 chunks、多个有效/负索引与配置 None/False/True | 一般单轴列表接口；零轴块规范 `core.py:2800–2803,2867–2887` | F2P 仅 `(3,0)`、默认 chunks、axis=0、`[0]`、默认配置 | 部分；没有这些交叉输入，不能由 116 个非空/其它路径 P2P 推出全覆盖 |
| 保留 Dask Array 返回与延迟调用约定 | `core.py:1846–1855`；切片文档的 Dask 输出 | F2P 的 Dask 检查是条件式；P2P `test_index_with_int_dask_array_nocompute` 只保护 Dask 索引器场景 | 对本题空输入返回类型/延迟分支缺显式保护；尚无实测误收候选 |

反向核查：唯一新增验收约束全部来自原例及公开 `assert_eq` 惯例，没有新增精确字符串、内部 helper 名称、Mock 调用形状或专用图哈希要求。旧 P2P 对非空图/块的精确断言原本公开，部分对应文档的块行为；未发现必须照写 gold 才能通过的隐藏约束。

## 3. P2P、调用者与 gold 范围

已分段读完 `B/dask/array/tests/test_slicing.py:1–1067`，包括参数、helper 和 skip/xfail。P2P 共 **116 条**，全部位于该模块；静态解析原始日志短摘要并逐 ID 对照，gold/noop 均无参考缺席、无参考 skip、全部 116 条 PASS。整模块还有两个上述未入参考但 PASS 的旧测试、两个 skip（穷举与 slow）、两个 xfail（cull 与未知索引轴 chunks1）。gold 的 119 PASS = 116 P2P + 1 F2P + 2 非参考旧测试。不能将 123 collected 或 119 passed 都写为 P2P。

受影响调用者除 `__getitem__` 外，还读了 `B/dask/array/routines.py:1945–1959` 的公开 `da.take`（Dask 输入经索引操作）、`slice_wrap_lists` 的全切片/混合切片两条 take 路径、空列表转零切片路径、归一化/越界检查、`chunk.getitem:401–428`。`B/dask/array/tests/test_array_core.py:4155–4166` 提供空索引 dtype 和后续 blockwise 的额外旧行为依据，**不在本题评分模块**。没有穷尽 routines、其它数组后端、分布式调度或全仓所有调用者。

gold 仅在 `take` 的 NaN 保护条件增加 `other_numel == 0`，使零字节结果的 `warnsize/maxsize` 为正无穷，保留原 slicing plan、图和块，避免无意义拆分。索引边界在此之前已检查；正常非零和 NaN 路径不变。无新增依赖、附件、测试夹带源码、跨文件未交付修改或无关改动。G:350–363 确认实际重放的确是这行补丁；G:790,937–944 证实原例与模块通过。静态上该处理同时适用于零轴不同位置及配置状态，但没有把未运行的扩展输入写成执行通过。

不同于 gold 的合理路线：保留既有 NaN 路径，在大小估算模块外显式跳过零元素情形的阈值计算/警告/拆分，再沿原 slicing plan 构图；不必用同一条件表达式。新增 F2P 没有排斥这种组织方式。若改成独立空图优化，还需保留 Array 类型、dtype、维数、边界校验与可用块信息。

## 4. 新发现与最小可区分实验（仅建议）

**I1：与改动直接相关的默认警告旧测试没有计入 P2P。** 缺席是已核事实。当前 `rh2/src/repoharness2/envpack/scoring.py:250–268,301–308` 将 F2P/P2P 清单交给来源评分函数；`grading/manager.py:1864–1909,2997–3015` 对正常完成测试保留该结论，没有把普通测试退出 1 一概转为失败。因此未入参考的默认警告回归有可能仍得到 1 分；这项最终判断需要真实候选重放，不能仅从参考列表宣布已经误收。

可区分的部分修复：将 base 的 NaN 特判条件概念性改为 `math.isnan(other_numel) or config.get("array.slicing.split-large-chunks", None) is not True`。它只在显式 True 时算有限阈值；默认原例因跳过除法而恢复，但普通默认大块警告消失，空轴显式 True 仍会除零。已读的 P2P 中，正常 True 拆块/配置和 NaN 行为保留，乱序警告在阈值逻辑之前；故它是有明确路径依据的疑似误收候选，而非字面硬编码原例。**本轮没有写入或运行此补丁。**

唯一优先下一步：在现有 compat-v1 条件下，对这个部分修复做一次定点 CPU/RH2 对照，同时记录实际奖励、参考状态、完整模块退出码；独立运行原有 `test_getitem_avoids_large_chunks`，并对原例加 `split=True`。gold 作控制。预期部分修复暴露默认警告回归和 True 空轴失败；是否奖励仍为 1 必须以新原始日志确认。若确认，应单独版本化参考补全/窄配置测试，并复验合理替代解；不直接修改原题包或为保 gold 放宽标准。

**I2：新增空轴覆盖仍是单个默认用例。** 显式 False/True、其它零轴/分块/索引和 Array 返回类型没有直接保护；第 2 节已分别列出公开依据。这是明确覆盖边界，不自动要求所有组合全穷举，不自动拒绝该题。I1 的一个实验已能同时检验最关键配置漏测；其它建议按实际候选形态再扩展。

未发现静态误拒证据；也没有证明所有正确实现都会被接受。gold 对具体原例成立不等于只有该实现正确。

## 5. 原始执行证据与开发条件

原件简称：

- **G**：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-8597/gold/eval_logs/evallog_replay-er19-cv1-dask__da_cb209d73.eval.log`，SHA-256 `4ada7bf0ddf6c18c4cda78ca70e91426f95c57fe42c08b2b7ada896381a944cb`。
- **N**：同路径 `noop/eval_logs/evallog_replay-er19-cv1-dask__da_50713119.eval.log`，SHA-256 `523554351e52e3593ea705193878caaaa4e5e8281dd78afe6ee14683c78d8e4e`。
- 对应 gold/noop `ledger.jsonl` 均第 **1** 行；两个日志哈希已重新核对匹配 `PRIV/run_refs.json`。所引是 09-19 真实 RH2 grader 运行，不是本次执行。

| 事实 | 原始证据及范围 |
| --- | --- |
| base / 生效补丁 | N:210–214,345 初态干净且 HEAD 为精确 base；G:210–219,350–363 仅目标源文件已改 |
| 官方测试恢复及应用成功 | N:345–386；G:364–404；各 1 文件，apply rc=0、setup OK |
| 兼容修复 | N:602–612；G:620–630：离线 wheel 将原 pytest 8.3.2 改为 7.4.4；非业务补丁。recipe 是 `compat-v1:dask__dask-8597` |
| 安装、解释器 | N:613–648；G:631–666：`pip install --no-deps -e .` 成功，Python 3.9.19，pytest 7.4.4，`/opt/miniconda3/envs/testbed/bin/python`；ledger 观察导入 `/testbed/dask/__init__.py` |
| 测试真实执行与结果 | N:775–863,1004–1016：F2P 根因失败、118 PASS、2 skip、2 xfail、rc=1；G:790,932–944：119 PASS、2 skip、2 xfail、rc=0；账本评分分别 0/1 |
| 条件 | 两账本第 1 行：本地派生 image `sha256:065c32c154a13335b5363bd7969d0c79bd19f7dee23b9a1000b5650ac9cd78e0`；rh2grader/54322，2 CPU、4 GiB、PID512、shm64 MiB、tmp1 GiB、deny_all；解释器前缀允许写入 |
| 资源／收尾 | 账本记录峰值约 gold1536.57 / noop1609.496 MiB，cleanup.removed=true；未重新实测。依赖安装使 runner digest 改变，两边都有；不能把它单独解释为候选作弊。 |

上述条件不是 public bundle 原镜像被 actor 自动消费的证明；当前静态材料没有正式 actor 过程。整个模块含 `test_getitem_avoids_large_chunks_missing[chunks0]` 的大数组，而题面最小复现很小，不能用单例轻量推导全模块资源。历史 grader 4 GiB 成功，actor 实際 limit/激活/包源仍未知。

| 逐题开发需求 | 公开依据 | 既有支持／缺口 | 建议最小验证（本轮未执行） |
| --- | --- | --- | --- |
| 定位修复、读取与写入源文件 | prompt 的 `/testbed`；`__getitem__→take` 公开调用链 | base 导出足够定位；真实 UID/cwd/写权限仍待验 | actor shell 下 `id; pwd`，打印 `sys.executable`、`dask.__file__`；检查对工作区可写 |
| 导入 Dask Array 与 NumPy | `B/setup.py:13,32–39,79`；安装文档 `32–44` | grader 在指定 Python/compat 镜像可导入；actor 未验 | 打印 Python、NumPy、Dask、pytest 版本和路径，再执行公开原例并 `.compute()` 比 NumPy |
| 运行公开窄测试 | `B/setup.py:25–30`；开发文档 `165–174`；slicing 测试 import | pytest-xdist 支持官方 `-n0`；P2P sanitizer 使用 pandas，grader已运行，actor不明；`pytest.warns(None)` 需要兼容 pytest | `python -m pytest dask/array/tests/test_slicing.py -q -k 'take or getitem_avoids_large_chunks or empty or oob_check'`；记录 skip/xfail/退出码，不能只看收集数 |
| 安装关联 checkout（只在需要时） | 安装文档 `69–71`；开发文档 `110–112` | grader editable 安装成功且前缀归54322；agent/54321能否写同前缀未验 | 先核源码导入是否已正确；必要时用已有离线依赖/可写安装位置做 `pip install --no-deps -e .`，不假设公网 |
| 资产、服务、编译、网络 | 原例本地 `np.zeros`；setup.py 无本题编译步骤 | 无外部数据、权重、数据库、GPU 或服务需求；无需为合法修复新增包 | 准备阶段固定兼容 Python/NumPy/pytest及插件即可；解题/运行无需公网；缺轮子不能要求 actor 临时下载 |
| 交付文件 | gold 为 `dask/array/slicing.py`；也可在既有调用链合理重组 | 源文件是可投影交付；不需要改镜像、系统包或被恢复的官方测试才能修业务 | actor候选导出后核实际包含改动；环境修复走配方，不假装是源码补丁 |

## 6. 交付、控制面、关系与暴露

gold 账本第 1 行 `projection.included_paths=["dask/array/slicing.py"]`，ignored 为空；官方恢复仅 `dask/array/tests/test_slicing.py`（recipe `eval_script.after.sh` 及 G/N setup）。test patch 没有普通源码。禁止改测试的操作指令若适用，仍可通过源文件加内联公开复现完成开发；若不适用，新增开发测试也不代表会改变已恢复官方文件。

本题新增断言导入普通源码 `dask/array/utils.py::assert_eq`，它是测试依赖边界，但只将 helper 改为 no-op 仍不能防止参数 `array[[0]]` 的构图失败。helper 后续检查与 `setup.cfg` 警告策略会影响候选验证；本轮没有执行绕过探针。当前 manager 对官方文件恢复/保护的适用点已读（`manager.py:2838–2844,2882–2944`），不重新宣称全平台抗篡改已验，也不因泛化风险给合法源文件追加排除。`file_rules.additional_exclusions=[]`。

公开包没有未来 git 元数据；实际镜像的可见祖先、资产和公网答案可达性未查，不能据静态包宣布无泄漏。题面没有直接给出修复代码；repo/题目标识可指向外部答案，但没有联网检索。不读取其它任务就不推断跨题簇；当前无已核同问题/派生补丁关系。此次主审已见 gold、隐藏测试、评分清单与私有运行信息，此上下文及产物不能交给未来 solver，也不能作为独立求解成功。用途限 `development_diagnostic`。

## 7. 八方面覆盖与未查项汇总

| 方面 | 本次已查 | 未查／结论边界 |
| --- | --- | --- |
| 公开需求 | 原题、静态提示、公开阅读报告、接口/文档 | 真实模型消息及 hints 的具体注入未验 |
| 材料与初始问题 | S2逐对象一致、base身份、gold/test文本、noop实际失败链 | 未独立重建整棵Git tree或启动原镜像 |
| 测试测到要求 | 唯一 F2P 全断言/helper、116参考状态、全部 slicing 测试体 | 配置/空轴交叉和直接Array类型保护不足；I1奖励后果未实测 |
| 误拒合理解 | 无新增内部格式要求；不同组织方式可行 | 未实现/运行替代解，不能声称接受全部合理解 |
| 回归与 gold | 相关调用者、切片模块、额外零块旧测试；gold原例通过 | 非参考警告测试遗漏；全仓/其它后端未审 |
| agent开发条件 | 逐题依赖、资源、安装、网络/资产和 grader原件 | actor身份、激活、权限、兼容配方消费全部待验 |
| 交付与评分边界 | 官方恢复范围、gold投影、清单评分语义、helper入口 | 不代替平台整体控制面/镜像泄漏审计 |
| 关系与用途 | 本题标识、无题面修法、审查暴露登记 | 未读其它题，不做同文件聚类或模型难度/学习价值预测 |

原始运行日志已读实际基线/差分、恢复/apply、安装、测试状态、完整失败栈、警告和退出收口；重复 conda 激活及 `git show` 展示的无关 bag 提交没有逐行审计。读取工具曾出现合并输出截断，关键测试/栈/评分代码随后按片段重读，并以本题清单对原始日志做静态逐ID核对。没有将未显示片段写成已读证据。

当前 RH2 源码证据快照（不等同09-19执行版本）：`envpack/scoring.py` SHA-256 `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`；`grading/manager.py` SHA-256 `eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342`。后续参考旧调查时保留本稿，不以旧标签替换本次证据。
