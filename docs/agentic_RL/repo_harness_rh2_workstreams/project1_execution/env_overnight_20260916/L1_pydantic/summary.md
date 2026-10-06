# L1_pydantic · 逐题静态审查汇总

负责人：Claude Opus 5（夜间工作包，2026-09-16）。逐题记录在 `records/<instance_id>.json`，脚本在 `scripts/`，中间产物在 `runs/env_overnight_20260916/L1_pydantic/`（`prescan.json`、`mat/`）。

## 仓库级发现（适用于本包全部 20 题，逐题记录里不再重复证据）

| 编号 | 发现 | 证据 | 影响 |
| --- | --- | --- | --- |
| R1 | **镜像出厂即脏**：每题容器起手 `git status` 都报 `pdm.lock`、`pyproject.toml` 已修改（`pyproject.toml` 的改动就是 `+ "pre-commit>=2.21.0",` 进 `dependencies`，`pdm.lock` 被重写约 3000 行加 `files=[...]` 哈希）。 | `runs/env_probe_stage1_20260910/.../pydantic__pydantic-5706/empty/offline/a1/test_output.txt:133-141`（20 题同形，已抽查 5706/8500/8977/9193） | 4 条 DeepSeek 候选补丁 100% 含这两个文件的 hunk（`runs/env_probe_20260909_final_sync/ledger/logs_cc/*/candidate.diff`），5706 的 candidate.diff 因此达 327 KB / 2504 行。补丁提取口径需要扣除 pre-existing。 |
| R2 | **install 阶段必然 rc=2**：安装串 `export PATH=$HOME/.local/bin:$PATH; pdm add pre-commit; make install;` 两步都要联网，离线下 `[ConnectError] Temporary failure in name resolution` → `make: *** [Makefile:14: install] Error 1`。 | 同上 `:3682-3708` | 20 题 stage1 的 `rc_install` 全是 2，而 gold 仍 19/20 RESOLVED_FULL：实际生效的是镜像预装 conda `testbed` 环境。`install rc != 0` 在 pydantic 上不是坏环境信号（检查 9 的解释项）。每题白烧约 19 秒。 |
| R3 | **agent 侧 Python 不是 testbed env**：4 条 pydantic 轨迹里 `python -m pytest` 全部返回 `/opt/miniconda3/bin/python: No module named pytest`，`import pydantic_core` 也失败；全文 grep `envs/testbed` 命中 0 次。而 `public_hints` 明确写“`python`、`pip` 和仓库测试工具已指向 testbed”。 | `logs_cc/pydantic__pydantic-5706/stream.jsonl:1260,6897`；8500/8793/9214 同形（另缺 `dirty_equals`、`typing_extensions`） | 检查 8/10 的 P1：agent 既跑不了题面复现也跑不了公开测试，只能靠读代码。当前接线是否已修：**not_checked**（e1 未含 pydantic）。 |
| R4 | **判分恢复面只有 test_patch 触碰的文件**：`eval.sh` 的 setup 只 `git checkout <base> <test_patch 路径>`。`tests/conftest.py`（定义 `create_module` fixture、`--test-mypy` 选项）与 `pyproject.toml` 的 `[tool.pytest.ini_options]`（`filterwarnings=['error']`、`xfail_strict=true`）都**不**恢复，且 `pyproject.toml` 本来就脏、改动不显眼。 | `eval.sh` setup 段；`git show <base>:pyproject.toml` 第 142-148 行 | 检查 17/31 的静态残余面。**这条路径是活的**：本包 20 题里有 **13 题**的判分测试文件用到 `tests/conftest.py` 定义的 `create_module` fixture（5706、8500、8793、9214、8977、6043、6104、6126、8511、8525、9066、9134、9193），候选改写该 fixture 即可影响这些测试的执行，而 conftest.py 从不恢复。真机反例未做（not_checked）。不改变“additional_exclusions 默认为空”的结论——这是仓库级恢复策略问题，不是逐题排除规则。 |
| R5 | **判分面本身很窄**：20 题里 17 题的 F2P+P2P 全部落在 1 个测试文件内，另 3 题落在 2–3 个文件内；所有被判分的文件都恰好等于 test_patch 触碰的文件（无“被判分却不恢复”的文件）。 | `runs/env_overnight_20260916/L1_pydantic/prescan.json` | 好消息：没有 unrestored graded file。坏消息：跨文件的行为破坏一律看不见（5706 是已证实的实例）。 |
| R7 | **test_patch 新增的测试被归入 P2P**（3 题，已用 base 文件核对排除 diff 上下文造成的误判）：9214 的 `test_model_with_both_docstring_and_field_description`、8977 的 `test_tuple_strict`、6104 的 `test_model_subclass_metadata`。它们钉的都是 base 已有的行为，作为回归护栏本身合理；问题出在 9214——被钉住的是一个**有争议的优先级**，而消歧信息只在不可见的 hints 里。另：8977 的 `test_model_validate_list_strict` 在 gold 上是 XFAIL，不判分是正确的。 | `scripts/prescan.py` + 逐题 base 文件核对；8977 gold `test_output.txt:838` | 需要区分“新增测试=回归护栏”与“新增测试=题面外新要求”。 |
| R8 | **跨题答案泄漏（同仓库内）**：把每题 gold 的新增行拿去 grep 更晚题目的 base 快照，命中 **20 对**，其中 5 对是逐行全中：5386→5662（10/10）、6043→6126（13/13）、6104→8583/9193/9214（5/5）、6126→9066（3/3）、8004→9134（7/7）、8500→8525（5/5）、6283→8500/8525（3/3）。最典型：8525(2024-01-09) 的 base 里 `pydantic/main.py::model_construct` 逐行就是 8500(2024-01-05) 的参考解。 | `runs/env_overnight_20260916/L1_pydantic` 下的跨题扫描（本报告正文列出全部 18 对） | 同仓库题目**不能随机切分训练/评测**：晚题的初始仓库直接包含早题的答案。至少要按 (文件, 函数) 同族整体划分。 |
| R9 | **status_map 解析器按空白切分，遇到含空格的测试 ID 会产生垃圾条目**：pydantic 的参数化 ID 常含空格（如 `test_annotated[<lambda>-value5-FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)])]`），解析后得到 key=`...FieldInfo(annotation=int,`、value=`required=True,`。本包 20 题 gold+empty 合计 **264 条**这种非法状态条目。 | `runs/.../pydantic__pydantic-8004/gold/offline/a1/status_map.json`（9 条）与 `test_output.txt:646`；全包统计见正文 | 本包**判分不受影响**（已核对：264 条垃圾 key 与判分 ID 碰撞 0 条，且 20 题的 F2P/P2P 里没有任何 ID 含空白字符）。但这些测试的真实状态被丢失，且一旦有含空格的 ID 进入 F2P/P2P 就会判错。 |
| R10 | **判分环境是 Python 3.8**（不是题面里报告者用的 3.10–3.12）：8583 的 `tests/test_discriminated_union.py::test_discriminated_union_enum[*]` 5 条在 gold 上是 SKIPPED，其 skipif 条件恰为 `sys.version_info[:2] == (3, 8)`。 | `runs/.../pydantic__pydantic-8583/gold/offline/a1/{status_map.json,test_output.txt:985-989}`；`grading.json.python_version == "3.8"` | 影响 8511（gold 的 `sys.version_info >= (3,10)` 分支在判分环境不执行）与 9193（题面说 3.9 才复现，实际 3.8 也复现）。另有 6 题存在 SKIPPED 条目（8316 九条、8977 二十五条、9134 二十二条、8511 七条、8583 五条、9193 一条）。 |
| R6 | 无跨题 F2P 同名、无 F2P∩P2P 重叠、无重复 ID、测试 ID 里无空白字符 → `-rA` 日志解析的截断/碰撞风险在本仓库为零；唯一的 ID 问题是 8977 的控制字符/非 ASCII（见该题记录）。 | `scripts/prescan.py` 输出 | 检查 19 的一部分。 |

## 逐题表

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| pydantic__pydantic-5706 | 判分面只有 tests/test_json_schema.py；base 自带 5 组 Sequence 行为测试（test_types.py -k sequence、test_edge_cases.py::test_sequences_str）全不在 P2P，把 Sequence 直接映射成 list 的补丁仍判 FULL（已由 DeepSeek 轨迹实测 6 failed 证实）。gold 另含题面范围外的 `item_type == Any` 分支改动。 | needs_review：先扩 P2P 再入训练集 | L3 counterexamples/pydantic__pydantic-5706/run_matrix.sh |
| pydantic__pydantic-8500 | **题面原例在 gold 上也不通过**（必填字段缺失时 model_construct 不写 __dict__，构造后赋值仍排最后），F2P 换成了另一个场景；且 F2P/P2P 的字段名恰好全是字母序，一句 `sorted(__dict__)` 的假修复能通过全部 45 条。轨迹另有下载上游 wheel/PR diff 的答案外取。 | needs_review：标注题面-验收面落差 + 补非字母序回归 | L3 counterexamples/pydantic__pydantic-8500/run_matrix.sh；另跑 sorted() 假修复验证 |
| pydantic__pydantic-8793 | 题面原例被 F2P 原样采纳、根因单点（fields.py:401-407 捷径分支 setattr 绕过 __init__ 的 Ellipsis 归一化）。缺口：F2P 只断言 is_required()，改 is_required() 的表面修复可全绿；merge_field_infos 的既有专项测试（test_annotated.py:261/293/320）与调用点（test_config.py:788）都不在判分面。 | ready_for_probe（可先扩 P2P） | 只改 is_required() 跑官方 367 条，验证假修复能否全绿 |
| pydantic__pydantic-9214 | 失分点“docstring 与 Field(description) 并存时 docstring 优先”只写在不可见的 hints_text 里；题面例子两处描述都是 'abc' 无法消歧。且该条是 test_patch **新增**却归入 P2P（base 没有任何测试钉住这个优先级）。 | needs_repair：补一句题面即可 | L3 counterexamples/pydantic__pydantic-9214/run_matrix.sh |
| pydantic__pydantic-8977 | **参考 ID 编码缺陷已定量定根因**：参考 ID = `unicode_escape_decode(运行时 ID)`，反解 5/5 命中且全为 PASSED → gold 的 RESOLVED_NO 是假阴性。**但不能无条件变换**：同题 2 条 `[\u26c4…]` 参考 ID 本来就匹配，盲变会改坏；须“精确匹配→失败再反解”。另有 1 条 test_patch 注入的测试在 gold 上是 XFAIL（上游自认 model_validate 的 list strict 未修完），不判分是正确的。 | needs_repair（改对账回退规则即可） | 把回退规则套到全部 216 题 stage1 status_map 验证 |
| pydantic__pydantic-5386 | 本包公开材料-验收面落差最大的一题：F2P 钉死一个 base 里完全不存在的新 API 名 `__pydantic_init_subclass__`、两个钩子的调用顺序与 kwargs 形状，而题面只说“拿不到字段”，且题面代码块缺 `class` 关键字、混用 v1 `root_validator`。 | needs_repair：补题面或剔除 | 实现等价但改名的钩子，确认 F2P 必然失败 |
| pydantic__pydantic-5662 | 题面的 **Possible solution** 段直接给出完整修复（`return NotImplemented`），难度 trivial；F2P 只有 1 条 `MyModel(...) == ANY`，连 `return other == self` 这种无限递归的坏实现都可能通过（其余 127 条 P2P 都走不到该分支）。 | ready_for_probe，但打 solution_in_statement / difficulty=trivial 标记 | 用 `return other == self` 跑官方 128 条 |
| pydantic__pydantic-6043 | 本包判分最弱的一题：题面 783 字符纯散文、无代码无验收标准；test_patch 不新增测试，F2P 是把既有 `test_by_alias` 的断言从 `["'Snap'","'Crackle'"]` 改成 `["'Crackle'","'Snap'"]`，只排顶层 properties 的最小 hack 即可满分；题面说排 "keys and items" 而 gold 对 list 只递归不排序。 | reject_revision | 只排顶层 properties，跑官方 304 条验证能否全绿 |
| pydantic__pydantic-6104 | F2P 额外要求两条题面推不出的形状：参数化 `RootModel[int]` 的 title 字符串、以及 `$ref` 必须重写成 `allOf` 包装；gold 第二处改动 `metadata={**metadata, **root_field["'metadata']}` → `metadata=metadata` 是有损的（丢弃 root 字段 metadata），判分面零覆盖。与 9214 改同一函数同一段逻辑，必须同侧划分。 | needs_review | root 字段挂 json_schema_extra，比较 base/gold 输出 |
| pydantic__pydantic-6126 | 判分只看 schema 输出里没有 `default` 键，**不看 default_factory 是否被执行**；而题面列出的核心风险正是工厂的副作用（数据库/网络调用、时间/uuid）。“照旧执行工厂但丢弃结果”的实现能全绿。F2P 之一是既有 `test_dataclasses.py::test_schema` 删掉一行断言得到的。 | ready_for_probe（补一条“工厂未被调用”断言） | 实现“执行但丢弃”版本跑官方 449 条 |
| pydantic__pydantic-6283 | F2P 是既有 `test_root_model_equality` 新增一行断言；P2P 仅 38 条（本包第二小）。gold 让 RootModel 的 model_construct 不再设置 `__pydantic_private__`，但**带 PrivateAttr 的 RootModel 子类走 model_construct** 这条路判分面完全没测。 | ready_for_probe（补私有属性回归） | 只在无私有属性分支生效的部分修复跑官方 39 条 |
| pydantic__pydantic-8004 | **P2P 只有 15 条（本包最小判分面）**，且私有属性的主回归文件 tests/test_private_attributes.py 完全不在判分面；F2P 用 `PrivateAttr(default=1)`，题面原例的 `default_factory=datetime.now` 路径不在判分面（只处理 `default=` 的部分修复能全绿）。 | needs_review：扩 P2P | 只处理 default= 的部分修复跑官方 16 条 |
| pydantic__pydantic-8316 | 三处问题：(1) 题面第二诉求（to_camel）被维护者在**不可见 hints** 里回绝，按题面去改会挂 P2P 的 test_snake2camel；(2) 题面原例 `to_snake('HTTPResponse')` 不在判分面，F2P 只是新增一组 parametrize 参数；(3) **gold 顺带把 `([a-zA-Z])([0-9])` 缩成 `([a-z])([0-9])`**，`to_snake('CAMEL2')` 从 `'camel_2'` 变 `'camel2'`、`A1B2` 从 `'a_1_b_2'` 变 `'a1_b2'`，判分面 18 组参数全部看不见（已用 `scripts/to_snake_diff.py` 实跑验证）。 | needs_review | 已跑 scripts/to_snake_diff.py；待做：按题面改 to_camel 看挂几条 |
| pydantic__pydantic-8511 | 判分环境实测为 **Python 3.8**（由 8583 的 `skipif(3,8)` 用例在 gold 上 SKIPPED 反推），因此 gold 里 `sys.version_info >= (3,10)` 的 kw_only 分支根本不执行，真正生效的是“在 <3.10 上启用整段 make_pydantic_fields_compatible + 透传 repr”。gold 只透传 `repr`，`compare`/`metadata` 等关键字仍丢失且零覆盖。 | ready_for_probe | 补 compare=False 等关键字透传断言 |
| pydantic__pydantic-8525 | **P1 跨题答案泄漏**：8525 的 base 里 `model_construct` 逐行包含 8500 的 gold（两题相隔 4 天、同文件同函数同测试文件）。题面 5092 字符（本包最长）且**自带错误根因诊断**（"caused by inheritance"，实际与继承无关）。判分面 46 条不含 tests/test_private_attributes.py。 | needs_review：与 8500 同侧划分 | 对 216 题跑“早题 gold 是否在晚题 base”扫描 |
| pydantic__pydantic-8567 | F2P 只断言 `isinstance(data['foo'], str)` 不查值（强制 str() 的错误实现也能过）；gold 让 **所有** PlainValidator 无条件 `handler(source_type)` 并挂 wrap serializer，改变了 PlainValidator 对任意类型可用这一既有性质，而序列化主回归文件 tests/test_serialize.py 不在判分面。 | needs_review | 对无法生成 schema 的 source_type 用 PlainValidator，比较 base/gold |
| pydantic__pydantic-8583 | **gold 是顺序变通而非修复**：`schema['definitions'] = list(reversed(schema['definitions']))`。F2P 又是约 60 行 definitions 精确字典断言（含 required 顺序），等于把实现顺序固化成验收条件。题面示例含字面量 `XXX`、拼写错误、类名 `List`，不可运行。另：由本题 5 条 `skipif(3,8)` 用例为 SKIPPED，**确定判分环境是 Python 3.8**。 | needs_repair | 把 reversed 换成别的顺序看 F2P 是否仍绿 |
| pydantic__pydantic-9066 | 题面原例与 F2P 一致、边界干净、判分面 369 条，是本包质量较好的一题。缺口：F2P 只有 IPvAnyAddress 两个参数，只特判 ipaddress 的硬编码能过；gold 新增的 `PydanticSerializationError` 失败路径零覆盖。base 含 6126 的 gold（跨题泄漏）。 | ready_for_probe | 只特判 ipaddress 的修复跑官方 369 条 |
| pydantic__pydantic-9134 | **本包质量最好的一题**：题面含完整 traceback、gold 一行且对应根因（`if private_attributes or base_private_attributes`）、F2P 与题面场景一一对应、判分面 177 条。唯一问题是 base 同时含 8004/5386/5662 三题的 gold，需同侧划分。 | ready_for_probe | 无（可直接进真机探针） |
| pydantic__pydantic-9193 | **题面唯一复现依赖未安装的 openai SDK**、无 traceback、且完全没提泛型与 extra='allow'，而 F2P 恰是这两者的组合；F2P 测试体**没有任何断言**（只要定义类不抛错就算过），吞异常式修复即可满分。gold 本身最小且正确。 | needs_repair：重写题面 + 给 F2P 补断言 | 实现吞异常版本跑官方 107 条 |

## R8 明细：同仓库跨题答案泄漏（早题 gold 出现在晚题 base）

复现命令：`python3 scripts/crossleak.py`（只读裸克隆，无需容器）。判据：早题 gold 新增的有效行（去掉纯注释与 <15 字符的行）在晚题 base 的**同一文件**里出现，命中 ≥ 半数。

| 早题（gold） | 晚题（base 已含答案） | 文件 | 命中 |
| --- | --- | --- | --- |
| 5386 (2023-04-05) | 5662 / 6283 / 8500 / 8525 | pydantic/main.py | 10/10、8/10、8/10、8/10 |
| 5662 (2023-05-01) | 6283 / 8500 / 8525 | pydantic/main.py | 4/8 ×3 |
| 5706 (2023-05-06) | 6104 / 8583 / 9193 / 9214 | pydantic/_internal/_generate_schema.py | 10/11、5/11 ×3 |
| 6043 (2023-06-08) | 6126 | pydantic/json_schema.py | 13/13 |
| 6104 (2023-06-13) | 8583 / 9193 / 9214 | pydantic/_internal/_generate_schema.py | 5/5 ×3 |
| 6126 (2023-06-13) | 9066 | pydantic/json_schema.py | 3/3 |
| 6283 (2023-06-28) | 8500 / 8525 | pydantic/main.py | 3/3 ×2 |
| 8004 (2023-11-03) | 9134 | pydantic/_internal/_model_construction.py | 7/7 |
| 8500 (2024-01-05) | 8525 (2024-01-09) | pydantic/main.py | 5/5 |

**含义**：在 pydantic 这 20 题里，按时间随机切分训练/评测会直接漏答案。最小可用的同族分组（组内不得跨训练/评测边界）：
`{5386, 5662, 6283, 8500, 8525}`（pydantic/main.py）、`{5706, 6104, 8583, 9193, 9214}`（_generate_schema.py）、`{6043, 6126, 9066}`（json_schema.py）、`{8004, 9134}`（_model_construction.py）。剩下 4 题（8316 alias_generators、8511 dataclasses、8567 functional_validators、8793 fields、8977 _std_types_schema）互不重叠。
这条规则**大概率适用于本批 216 题的其它仓库**，但本包只验证了 pydantic。

## 覆盖与结论

- **覆盖**：分配的 20 题全部完成逐题记录（`records/*.json`，20 个文件），summary 逐题表 20 行。实际墙钟 03:06–03:55（约 50 分钟，本机时间 2026-09-16）。逐题记录里的 `costs.minutes`（13–38）是**分析工作量估计**，不是墙钟耗时，两者不可比——请以墙钟为准。
- **处置建议分布**：`ready_for_probe` 7（5662、6126、6283、8511、8793、9066、9134）、`needs_review` 7（5706、6104、8004、8316、8500、8525、8567）、`needs_repair` 5（5386、8583、8977、9193、9214）、`reject_revision` 1（6043）。
- **`file_rules.additional_exclusions` 20 题全部为空**，与第四组 B 的默认一致：每题 test_patch 只触碰纯测试文件，gold 不触碰任何测试路径，且**判分涉及的测试文件恰好等于 test_patch 触碰的文件**（无“被判分却不恢复”的路径）。真正的残余面是仓库级的 R4（conftest.py / pyproject.toml 不恢复），不属于逐题排除规则。

## 未做 / 仍是 not_checked 的项

1. **全部结论都是静态的**：没有起容器、没有跑任何 pytest、没有连任何远程机器。实际执行过的只有本机只读脚本：`scripts/{prescan,dump,src,crossleak,crossleak_216,idfix_216,to_snake_diff}.py`。逐题 `issues[].next_experiment` 里需要容器的那些**全部未执行**。
2. **检查 8/9/12–16/18/21/22/28/30 基本未覆盖**：本包只做 L1 静态审查，`not_checked`。检查 10（agent 本地验证）只有 4 题有 2026-09-09 的轨迹证据（R3），其余 16 题未核实。
3. **R3（agent 侧 Python 不是 testbed env）是 2026-09-09 的证据**，当前接线是否已修**未验证**（e1 不含 pydantic）。这是本包唯一一条 P1 但证据可能过期的发现，建议优先复核。
4. **R4 的真机反例未做**：改 `tests/conftest.py` 或 `pyproject.toml` 的 `filterwarnings` 能否真的改变判分，只有静态推断。
5. ~~8977 的 ID 回退规则只在本包 20 题上验证~~ **已扩到全部 216 题**（见附-1，`scripts/idfix_216.py`）；R8 的跨题泄漏扫描也已扩到 9 个仓库（见附-2，`scripts/crossleak_216.py`）。仍未做的是把回退规则真正接进 RH2 的对账代码并重跑 gold 基线。

## 静态复核补强：把 5 条“假修复能过关”的推测变成可核对的断言级证据

下面 5 条原本只是“看上去能过”的推断，已经逐条在 base 测试文件 + test_patch 上做了断言级扫描确认（仍是静态，未实跑）：

| 题 | 推测 | 复核方法与结果 |
| --- | --- | --- |
| 8500 | 在 model_construct 末尾按 key 字母序重排 __dict__ 即可满分 | 判分文件里依赖 key 顺序的断言共 4 个测试函数，其中**经过 model_construct 的只有 2 个**（F2P 的 `test_retain_order_of_fields` 字段 a/b、P2P 的 `test_construct_keep_order` 字段 a/b/c），**两者声明顺序都等于字母序**；另两个走 model_copy。→ 假修复成立 |
| 6043 | 只对顶层 properties 排一次序即可满分 | tests/test_json_schema.py 的 184 个测试块里，依赖 schema key 顺序的**非平凡断言只有 1 条**（F2P 的 `test_by_alias`）。其余 3 处是单元素列表、set 比较、或 `json.dumps` 后只做子串检查。→ 假修复成立，本题判分面实质为 1 条断言 |
| 8793 | 只改 `is_required()` 即可满分 | 在判分文件里 grep `.default` / `PydanticUndefined`，**命中 0**——没有任何断言检查 FieldInfo.default 本身。→ 假修复成立（default 仍是 Ellipsis 却判满分） |
| 8004 | 只处理 `default=`、不处理 `default_factory=` 即可满分 | tests/test_annotated.py 里 `default_factory` 只出现在普通 `Field(...)`，**没有一条用 Annotated + PrivateAttr(default_factory=...)**——题面原例的写法不在判分面。→ 假修复成立 |
| 8567 | gold 对“无 PlainSerializer 的 PlainValidator”的序列化改变不可见 | 判分文件里三处这类用法（`test_annotated_validator_plain`、`test_annotated_validator_typing_cache` 参数、`test_plain_validator_field_name`）**全部只断言校验后的值，无一做 model_dump**。→ 改变不可见成立 |

复核只用 `git show <base>:<file>` 与正则扫描，命令见 `scripts/src.py`。仍需真机确认的是这些假修复**实际跑起来**是否还有别的副作用，见各题 `issues[].next_experiment`。

## 附：把本包的两条发现扩到全部 216 题（超出分配范围，供协调者参考）

这两条都是从本包 8977 的调查里长出来的，跑在本机只读材料上，不需要容器。

### 附-1 参考 ID 编码缺陷：一条回退规则可挽回 10 题（约占 216 题的 4.6%）

规则：**先按原样匹配运行时 ID，失败时再用 `ref.encode('unicode_escape').decode('ascii')` 匹配一次**。在全部 181 个有 stage1 gold 日志的题上跑完：`missing 18 → 回退后修复 18 → 仍缺 0`，且**没有任何被修复的 ID 与已有 ID 碰撞**。

被挽回的 10 题恰好就是 `task_signals_swegym.json` 里 `fragile_reference_id=True` 的全部 10 题，回退后它们缺失的 P2P 全部是 `PASSED`，即 gold 应判 `RESOLVED_FULL` 而非当前的 `RESOLVED_NO`：

| 题 | 缺失条数 | in_e2 |
| --- | --- | --- |
| getmoto__moto-5417 / 5545 / 5562 / 6308 | 各 1 | — |
| getmoto__moto-5701 | 1 | B |
| iterative__dvc-4185 | 1 | — |
| modin-project__modin-6780 | 3 | — |
| pandas-dev__pandas-48106 | 3 | A、B |
| pandas-dev__pandas-50319 | 1 | B |
| pydantic__pydantic-8977 | 5 | — |

对照：181 题里 stage1 gold 非 `RESOLVED_FULL` 的共 16 题（15 NO + 1 PARTIAL）。上面 10 题修好后只剩 6 题（MONAI-1121、MONAI-3205、moto-4799、moto-4833、moto-7105、modin-5940），它们的 `f2p_missing`/`p2p_missing` 都是 0，属于**真实的非 PASSED 状态**，与 ID 编码无关。换句话说，**当前 gold 基线里 10/16 的失败是对账缺陷，不是题目或补丁的问题**。

**必须条件性应用**：pydantic-8977 里另有 2 条参考 ID（`test_constrained_str_too_long[\u26c4…]`）本来就精确匹配，无条件做 unicode_escape 变换会把它们的反斜杠二次转义、反而匹配不上。所以只能做“精确匹配失败后的回退”，不能做预处理。

### 附-2 跨题答案泄漏：216 题里 80 对、涉及 95 题（44%）

明细见 `runs/env_overnight_20260916/L1_pydantic/crossleak_216.txt`（判据同 R8：早题 gold 新增的有效行在晚题 base 的同一文件里命中 ≥ 半数）。

| 仓库 | 题数 | 泄漏对 | 涉及题数 |
| --- | --- | --- | --- |
| python/mypy | 40 | 24 | 26 |
| getmoto/moto | 59 | 23 | 32 |
| pydantic/pydantic | 20 | 20 | 15 |
| iterative/dvc | 35 | 7 | 10 |
| Project-MONAI/MONAI | 26 | 3 | 6 |
| dask/dask | 14 | 3 | 6 |
| conan-io/conan / modin / pandas | 12 / 5 / 5 | 0 | 0 |

逐行全中的极端例子：`python__mypy-9909 → python__mypy-11420` 与 `→ python__mypy-11945`，`mypy/checker.py` 32/32 行；`Project-MONAI__MONAI-4676 → MONAI-6523`，`monai/data/meta_tensor.py` 28/28 行；`pydantic-5386 → pydantic-5662`，`pydantic/main.py` 10/10 行。

**含义**：这不是“模型预训练污染”那种不确定性，而是**评测题的初始仓库里直接可读到另一道题的参考解**。只要两题被分到训练/评测两侧（或同一批 rollout 里都出现过），泄漏就成立。约束：本扫描只比对**同一文件**、只比对 gold 的新增行，会漏掉跨文件与被重构过的修复，所以 80 对是**下界**。

## 最值得用户裁定的 3 个问题

1. **同仓库题目的划分规则**（R8，已扩到全部 216 题，见下节）：**80 对**“晚题 base 含早题 gold”的关系，涉及 **95 题（44%）**；pydantic 密度最高（20 题 20 对），mypy 24 对、moto 23 对、dvc 7 对、MONAI 3 对、dask 3 对，conan/modin/pandas 为 0。按时间或随机切分训练/评测必然漏答案。是否采纳“按 (仓库, 被改文件) 同族整体划分”，并接受由此减少的可用评测题数？

2. **对“题面-验收面落差”类题目的处置口径**：本包有 6 题（8500、9214、5386、8316、9193、6043）的判分要求无法从 agent 可见材料推出（关键信息在不可见的 `hints_text` 里，或压根不存在于任何材料）。是选择 (a) 补写 `public_view` 把缺失要求交代清楚（改变了“真实 GitHub issue”的分布）、(b) 直接剔除、还是 (c) 保留并接受这部分噪声？三条路线对训练信号的含义完全不同，且影响约 30% 的题量。
3. **判分面是否要统一扩到“被改文件的既有回归测试”**：本包 17/20 题的 F2P+P2P 落在**单个**测试文件内，5706 已被实测证明会放过破坏公开语义的补丁（`tests/test_types.py -k sequence` 实测 6 failed 却不在判分面），8004/8525/9134 的私有属性主回归文件、8567 的 `tests/test_serialize.py` 同样缺席。扩判分面能减少假阳性，但会提高 gold 通过门槛（8316 的 gold 就会因为 `to_snake('CAMEL2')` 行为变化而变得可疑）、增加每题运行时间，并需要重新跑 gold/empty 基线。是否要做、按什么规则选、成本由谁承担？
