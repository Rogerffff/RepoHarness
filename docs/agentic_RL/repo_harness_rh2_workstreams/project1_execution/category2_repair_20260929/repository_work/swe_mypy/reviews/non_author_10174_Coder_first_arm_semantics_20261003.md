# 10174 Coder 首轮：非作者语义与轨迹反证窄核

审查日期：2026-10-03。角色：review-standards.md §10.4 Falsifier / Simplifier。对象仅为 `gpu1003-mypy10174-coder-a1` 的本机冻结闭包。

结论：冻结候选确实修复了题面中的非 strict_optional、Optional[Any] 成员检查误报，并保留了本次有证据的真正不重叠诊断和 Tuple 行为。正式四参考均有候选测试段内的原始 PASSED 行；未发现需要改题、改候选或追加运行的语义／评分缺陷。存在一项 P3：模型的根因说明和自验结论有具体误读及范围过宽。此问题影响轨迹表述的准确性，不推翻这一次修复成功。

本审查已见本题 gold/private 与此前 Qwen 分析，**非 fresh 审查**。本轮只读本机 JSON、源码字节、tar 与日志；未运行项目代码、测试、模型、SSH、CPU 或 GPU 作业。只新建本报告，不回写历史原件。

## 原件范围与身份

[闭包 manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-mypy10174-coder-a1_closed_manifest_v1.json) 的字节 SHA256 为 `f7aa33ddcbc3500506477c6bac4fc1739f413dfd89e65564d53dc950432bdaa8`。闭包根为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-mypy10174-coder-a1/`；以下以 `J/` 指该根内的 `queue_v30/results/gpu1003-mypy10174-coder-a1/`。

独立核对的是目标 `J/` 文件、目标 `services_v14/coder/adapter/gpu1003-mypy10174-coder-a1.turns.jsonl`、目标 `prepared_swe_four_v1/mypy10174/` 材料，共 **36 件、24,116,510 字节**，其 manifest SHA／大小均一致；不宣称独立核完 manifest 的全部 552 件，不读取其它任务的内容。

| 对象 | 独立核对的 SHA256／身份 |
| --- | --- |
| `J/attempt/trajectory.jsonl` 字节 | `b21c5f45f3b81eaecd81eaeb27de9746d23e1064648dfb485324a5a7539acc38` |
| 目标 adapter JSONL 字节 | `2b1c4f244757f05ec88eef4d831a301e78bad7b4561d425654fba059ca3c6363` |
| FP 规范化摘要 | `172bffdc4938b68ee3bd6c80006a2cd8d02c2e16ff5cda6f6fa80f95b5b17c80` |
| baseline manifest 规范化摘要 | `4dd938f76acfcaaaefa50bbfde72605930b6fc43c84c27f821d0f652455cd38f` |
| 候选 `mypy/checkexpr.py` 内容 | `b6ccea9c19a1c71988968943cbd6118707d857bd8034bc96e1ec3d7ee2970c52` |
| 正式 eval.log 字节 | `effaa652c04deec6f2595b4389096afd290705e3886a80ea7d1655d6893da74e` |
| runtime image／base commit | `sha256:80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f`／`c8bae06919674b9846e3ff864b0a44592db888eb` |

## 修复为何有效，以及保留了什么

公开问题要求：`# mypy: no-strict-optional, strict-equality` 下，`x: Optional[Any]` 的 `x in (1, 2)` 不应报告 Non-overlapping container check。候选仅修改 `mypy/checkexpr.py`，在 `dangerous_comparison` 原有“两侧都是 Union”分支之后新增非 strict_optional 分支（候选 2334–2341）。它先通过 `relevant_items()` 去掉 None、再构造 Union 并取得 proper type，使 Optional[Any] 在进入 `is_overlapping_types` 前成为 Any。

baseline `mypy/meet.py` 165–166 的 Any guard 位于 171–176 的非 strict_optional 化简**之前**；旧路径化简出 Any 后不会重走该 guard。候选的前置化简因此让已有 Any guard 真正命中。这是一种局部有效修复，未改 `meet.py`；不能据此声称全局 overlap helper 的这个顺序问题也已修复。`mypy/checker.py` 288／323 在正常检查入口用 `state.strict_optional_set(self.options.strict_optional)` 同步状态，`types.py` 1801–1806 的 `relevant_items()` 与新分支的模式判断相符。

真正不重叠的 Optional[str] 被化简为 str，仍经原 overlap 判断报告与 int 不重叠；工具 51 的诊断从修复前 Any＋str 两条减少到仅 str 一条。Optional[int] 的原通过行为由工具 47、52 保留。`strict_equality=False` 的立即返回、None 特例、原两 Union 分支、bytes、AbstractSet whitelist、bool Literal 特例均保留；strict_optional=True 不进入新增分支。该 helper 也服务 `==`／`!=`／`is`／`is not`，所以改动影响不只成员检查，但没有据当前原件发现具体新增回归，不能将保留路径扩大成所有组合都经过动态验证。

Tuple 的容器元素提取没有改动。公开 `testStrictEqualityWithFixedLengthTupleInCheck` 在改前工具 35、改后工具 58 都有 `1 passed`；其 oracle 是 strict_optional 默认模式下 `1 in ('x', 'y')` 应报告 int／str 不重叠。正式新增 P2P 在 no-strict-optional 下重复这一真正不重叠检查，并实际 PASSED；由此排除“简单关掉成员诊断”的解释。

## 正式四参考与供应边界

[正式原日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-mypy10174-coder-a1/queue_v30/results/gpu1003-mypy10174-coder-a1/grading/eval_logs/evallog_gpu1003-mypy10174-coder-_8acef403.eval.log) 536–555 是未经 pipe／`|| echo` 包装的候选 pytest 段：收集 9423、选中 4、`4 passed, 9419 deselected`、`RH2_TEST_RC=0`。547–550 四个 PASSED 逐项等于 private 的 1 F2P＋3 P2P 集合，均位于 Start／End Test Output 内，段外解析项 0，无缺失或跳过。

| 参考 | 实際所证明的行为 |
| --- | --- |
| F2P `testOverlappingAnyTypeWithoutStrictOptional` | 题面 Optional[Any] 成员检查不再误报 |
| 新增 P2P `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional` | 非 strict_optional 下 int／Tuple[str, str] 仍须报不重叠 |
| 原 P2P `testUnimportedHintAnyLower`、`testUnimportedHintAny` | 原未导入 Any 的诊断保留；不是本次 Union 化简的完整覆盖 |

private 有效 test patch 内容 SHA 为 `91ea4e972129deaf770ef9e72aa26d11d9bafca85229eae6931f2b22568322cf`，与其声明一致；baseline test-data 原文件 SHA `faf0a2a1512eba689901ec6a4df57bc1be9183d2616f6846c8dc9ada181884ec` 亦一致。trusted setup 记录恢复 1 文件、apply RC0、保护文件完整（1 文件／3 目录）；FP 没有修改测试源、fixture、conftest、pytest.ini、安装要求或控制文件。runner 前后摘要均为 `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4`。

FP 为 66 项：55 项 `.mypy_cache`、10 个开发脚本、1 个实现文件；65 add＋1 modify。66 项内容摘要均重算相符，projection 的 66 条路径与 FP 同序相等，未通过排除路径过滤负面测试。1472 条 baseline 内容逐项与 tar 一致，原 census／评分重建 census 字节相等，SHA 均为 `67c508e55dd3aa024a3e1f1c9c2f5e5e09b370ea02757740724344978a19bcf7`。10 次 Write 的实际 content 精确等于相应 FP 脚本；工具 49 的单次 Edit 应用 baseline 后精确生成上述候选源码。

10 脚本包括复现、Optional[Any/int/str]、严格模式对照和 Union 示例。正式 pytest 的 testpaths 为 `mypy/test mypyc/test`，普通 python_files 为 `test*.py`，这些根目录脚本不会代替四参考。baseline data suite 为每个 case 建新临时目录（`mypy/test/data.py` 238–247），非增量案例设 `incremental=False`，非写缓存案例设 `cache_dir=os.devnull`（testcheck.py 184–191）；这四参考不是增量／写缓存案例。结合实际四条执行结果，没有证据表明携带的开发缓存绕过了 oracle；缓存和脚本数量本身不是缺陷。

raw 安装段显示三条原安装命令，editable 构建及安装明确成功（479–507），没有 `RH2_INSTALL_CMD_FAILED`，安装终值 RC0。当前 job 未出现旧 GPU wheel Permission denied 安装故障；它是这次新的 Coder solve 样本，不能与旧 Qwen raw1、CPU r16 或旧 FP 新镜像重评分混记。观测 import 仅为 `/testbed/mypy/__init__.py`，包版本 `?`，不将其冒充全部实现模块的 pytest 进程内来源证明。源码／供应、实际安装与四参考共同支持当前有限结论。

## P3：根因与自验表述超出实际原件

[完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-mypy10174-coder-a1/queue_v30/results/gpu1003-mypy10174-coder-a1/attempt/trajectory.jsonl) 的以下误读真实存在，最低处理是修正解读与验证标签，不改冻结样本或重跑：

- **根因顺序读反。** 轨迹 465／504 把 meet.py 171–176 的化简叙述成随后进入 165 Any guard；最终 805／809 仍称 underlying helper 正确处理这一情况。实际 guard 顺序如上。源码修法有效，但说明没有准确解释为什么原 helper 失败。
- **预期负例被误称验证通过。** 工具 62 的 `comprehensive_test.py` 把 `Union[str, float]` 与 int 的成员比较标为应报错；工具 63／64 的输出（752／765）只有 Optional[str] 一条错误，模型 757 却列出该 Union 已报错并称全部案例正确。原实现允许 numeric promotion（`semanal_classprop.py` 的 int→float、`subtypes.py` proper subtype promotion 路径，且调用仍为 `ignore_promotions=False`），实际不报该错误符合保留行为；错在模型预期和读结果，不是修复吞掉真正不重叠。
- **两次严格模式对照误用。** 工具 53／64 仅从命令去掉 `--no-strict-optional`，但所用文件首行仍含 `no-strict-optional`；build.py 2074–2079 将 inline 配置应用到模块 options，因此这两次仍是非严格模式。后来工具 55／57 的文件首行仅为 strict-equality，确有默认严格模式下 Any/int 通过、str 保留错误的有限证据，不能反过来把前两次标成严格模式。
- **“All existing tests continue to pass”过宽。** 工具 58 为公开选中 1 例；59–61 仅分别显示 strict 125、container 6、equality 41 的筛选组通过。集合可能重叠，不能相加为不同案例总数，更不是全套测试。59–61 接 `head`、无 pipefail，shell 成功不能独立证明 pytest RC；完整可见的 PASS 汇总仍是相应组选测证据。工具 35 带 `|| echo` 同样不能仅凭 shell RC 判断，但此次实际输出为 1 passed。

这里不把“不重叠负例返回 1”当安装／环境失败，也不因为验证措辞过宽而否认正式四参考的实际 PASSED。

## 工具过程、效率与停止条件

完整轨迹有 68 turn、67 工具调用及 67 回执，12 个 `is_error=true`。其中 5 个为改前复现误报（2／25／27／29／45；29 同时保留 str 负例），4 个为改后预期 str 负例（51／55／63／64），2 个为在错误目录／仅 `.py` 中寻找 data-driven case 的 xargs 返回 123（37／38），最后 1 个为 test-requirements.txt 的 old/new 相同而被 Edit 拒绝（67，未形成 FP 改动）。工具 43 的 API 明确打印 mypy 状态 1，外层 Python 命令没有传递它，不能算通过。不存在由这些 12 条工具错误推出的实际基础设施失败。

模型从实际复现、调用方、容器元素提取追到 overlap helper 后，仅作一次实现 Edit；这支持局部定位与纠错能力。另一方面，多轮重复读取／复现没有解决 guard 顺序误读；30–38 找 data case 时反复限于 `mypy/test/*.py`，应直接定位 `test-data/unit/check-expressions.test`。`debug_test.py` 没有成员表达式，工具 24 的成功不能验证问题；模型 311 又把差异归因于缺少 strict-equality，但工具 24 实际带此参数。这些是可具体解释的低效或验证误用。

目标 adapter 为 68 条响应，每条最多 1 工具，实际工具过程串行；独立搜索／读文件可合并，后续独立验证可并行，而修改后依赖验证应顺序执行。`pytest -n 2` 是测试 worker 并行，不是模型多工具并行。trajectory result 记录 146652 ms／68 turn，只代表该 result 的范围，不外推端到端效率或成本优劣。

adapter 与执行工具 49 的 `old_string`、`new_string` 已专门逐值比对，二者相等且都有完整 AbstractSet whitelist；执行参数只多 `replace_all=False` 默认值。其它已见参数差异为两处移除冗余 `cd /testbed &&`、四个 Write 的行尾空格。曾将长输出误读为该分支缺失，随后用专门 diff、原始 adapter 输出及 FP 撤回；不形成 finding，也不推断有语义保护改写。

推荐保留“同一冻结 Coder 候选、公开问题与正式四参考支持的一次成功”这一用途，并记录上述 P3 的准确表述。报告修正即可，运行代价为零；没有现存矛盾需要新 CPU／GPU 或扩展矩阵。单次样本不能估计稳定性／成功率，也不证明全套兼容性或训练资格；resource_facts 为 null、env_qualification 为 absent，本审查不补作新 HostConfig 或训练准入判定。新增范围已完成，按停止条件收口。
