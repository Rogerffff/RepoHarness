# python__mypy-10174：独立初判

- 状态 `needs_review`；范围 `static_review`；用途 `development_diagnostic`。可解释的原问题和合理 gold，但评分的相关回归保护弱；建议优先做一个过宽修复的 CPU 校准，不直接称质量合格。
- ROOT=`${REPO_ROOT}`。P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-10174`；Q 为同根 `private/python__mypy-10174`；R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10174`；A=`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`。引用均相对 ROOT；源码行号以 P/base 为准。
- 暴露：本题公开/私有顶层原件（含隐藏测试、gold、环境记录自带 gold/noop 结果）、本题 inventory exact entry/common/install_wave1、指向的本题原始运行证据，以及 baseline 归档相关成员文本。此前按顺序独立处理15139、15184原件和初判。未读任一主审、公开读者、旧质量结论或批次聚合；未追 environment_record 的 analysis/history。不是无结果盲审。仅静态读/标准库文本JSONhash；没有项目执行、测试、安装、网络、Docker/SSH、解包、提交或题目修改。

## 结论与核心疑点

原问题是非 strict-optional 模式下 `Optional[Any] in tuple[int,...]` 被误报为不重叠；F2P 忠实重现题面且确实比较“无错误输出”。gold 把 Any 特例放到非 strict-optional 的 union 去 None 之后，静态上恰好修复 `Union[Any,None] → Any` 后漏过早期 Any 检查的缺口，并同时处理左右两侧。

**评分缺少与修复直接相关的负对照。** 冻结两项 P2P 全是“Any/any 未导入的提示”，没有验证真的不重叠的比较仍报错，也未直接保护 strict-optional 开启时的原好行为。可提出一个具体、非硬编码的过宽候选：在 `ExpressionChecker.dangerous_comparison` 中给 `not self.chk.options.strict_optional` 直接返回 False。它满足本题新增“无诊断”，不影响导入提示，却会禁止该模式的所有 strict-equality 告警。按调用/选择关系推断可通过本评分，**尚未执行，不能写成已证实 reward=1**。这不是 gold 缺陷；它是评分对合理旧行为的保护缺口，适合一个定点 CPU 校准。

## 需求—断言表（所有 F2P/P2P 与新增断言）

| 需求/旧行为 | 公开依据/源码 | 测试节点/关键断言 | 覆盖与证据 |
|---|---|---|---|
| no-strict-optional＋strict-equality 下 Optional[Any] 能与整型容器重叠 | user_prompt:3–17；meet.py:164–176；types.py:1777–1783、1801–1806 | F2P `mypy/test/testcheck.py::TypeCheckSuite::testOverlappingAnyTypeWithoutStrictOptional`；flags显式关闭strict optional、开启strict equality；`x:Optional[Any]; if x in (1,2):pass`，无 E/N/out，要求完整输出为空 | 直接覆盖题面。历史noop实际多报1条 `Non-overlapping container check ... Optional[Any] ... int`；gold通过 |
| Any 未导入时提示拼写与导入建议 | 公开旧 check-expressions.test:2771–2774 | P2P `mypy/test/testcheck.py::TypeCheckSuite::testUnimportedHintAny`：E `Name 'Any' is not defined`；N `Did you forget to import it from "typing"? (Suggestion: "from typing import Any")` | 实际已执行且两角色均通过；与 overlap修复不相关 |
| 小写 any 未导入时同样提示 | 同文件2777–2780 | P2P `mypy/test/testcheck.py::TypeCheckSuite::testUnimportedHintAnyLower`：同一两条提示但Name为`any` | 实际已执行且两角色通过；因 -k 子串匹配被选，不能称 test.patch 新增断言 |
| 真正不重叠比较仍应报错，None检查仍可放行 | docs/source/command_line.rst:562–580；error_code_list2.rst:87–106；旧testStrictEqualityEq/Is/Contains/Unions及FixedLengthTupleInCheck | 未列冻结P2P、未由本命令选择；同文件2764–2769已有`1 in ('x','y')`负例但其case名不在patch上下文 | **缺失相关回归保护**，过宽候选待CPU反证；不可用两项无关P2P代替 |
| strict-optional开启时原例仍正确；Any在左/右、Optional普通类型不被一概吞掉 | user_prompt最后一句；dangerous_comparison规则2293–2353；旧2514–2550 | 新F2P只一个开关组合/左侧Any/tuple；旧testStrictEqualityAny、StrictOptional、NoStrictOptional、EqNoOptionalOverlap未计分 | 覆盖有限；gold保留strict模式逻辑，尚未跑回归 |

1. **公开需求（3/23）**：题面目标/复现/开关明确；docs规定strict-equality检查真正不重叠，no-strict-optional只放松None/Optional，不应关掉该检查。合理修复需同时消除假阳性并保持真实错误。public_hints禁止改测试对修复meet/checkexpr源码无冲突；其激活/可见消息声明仍不是运行记录。
2. **材料/初态（1/2/27）**：base=`c8bae06919674b9846e3ff864b0a44592db888eb`，私有version0.820/Python3.9。P/base_identity记录1466blob/无gitlinks/LFS，未重验所有blob。三份ingest第177行raw SHA均重核匹配；prepared_manifest tasks[176] exact本题；host_grading第177行SHA=`c0440b05b335ca461e8532089ebcc0c3d40e3d45d07ddb5f32d019ee4c0342b6`且grading与Q相等。gold文件/validation/原candidate SHA=`7f94c5b71301dbbf5ccce1af8b274444ab5c0de5010f92109e11549154066f6c`。noop失败位置与公开复现吻合，不是错版/已修或无关依赖故障。
3. **测试有效性（18–20/25/32）**：test.patch全文只新增一例、两fixture指令，无业务源码或新增helper。已读两个fixture全文：tuple.pyi提供tuple的__contains__(object)、int/bool/str及序列；typing-full.pyi提供Any/Optional special forms、Container/Sequence等。data.py:69–81加载fixture，421–449把E/N转换为完整行号期望；testcheck.py:171–234 parse flags/build/完整数组比对，因此空输出是有效无误报断言，不是测试体未运行。helpers.py:372–404显式flags不被测试默认覆盖；本文件名不是optional，不触发另设strict_optional=True。
4. **误拒（24/28）**：F2P不要求内部helper或gold排序，只要求指定例无多余诊断。另一合理路线可把Any判定放入共用归一化步骤，或在使用overlap之前正确归一化Union并保留所有分支；没有已知正确替代解被这些断言误拒。只在比较入口对Optional[Any]做适当处理可能满足公开例，但应再核对右侧、同模式其它比较，不能默认gold是唯一解法。
5. **gold/回归（26/27）**：gold只移动Any早返回，未改types或状态、未屏蔽诊断。已读meet.py:130–355完整overlap主体：strict模式不归一化；非strict模式Union去None后重新get_proper_types；make_union一元素直接返回该元素；ProperSubtypeVisitor.visit_any(subtypes.py:1218–1219)只把Any看作Any的proper subtype，解释base漏检路径。影响不仅是in：checkexpr.py:2176–2261涉及==/!=/is/in；meet.narrow_declared_type:53–85、checkexpr.narrow_type_from_binder:4164–4185、checker.py:4335–4356、4970–4994消费overlap推断。已抽查旧strict equality13个左右case/关键负例及MeetSuite少量Literal/narrow声明用例，未穷举overload、TypedDict、Tuple、TypeType、TypeVar/None禁止重叠参数或全仓回归。两冻结P2P对这些无保护。
6. **开发条件（6–15）**：README:182–216与test README:28–47、83–127给出安装和窄pytest入口；__main__.py:6–23为mypy入口。只需Python、项目依赖、fixtures/typeshed，无新增外部业务资产/服务。setup.py:77–83默认非mypyc；本题不要求C编译，typed_ast已有版本依赖需准备。旧文档提Python2全套测试，不等于此Python3复现/所选三例必须有Python2运行期。actor条件未知，见下文。
7. **交付/评分（4/16–17/21–22/29–31）**：官方恢复文件仅`test-data/unit/check-expressions.test`，gold改`mypy/meet.py`历史included_paths且ignored=[]。baseline/prepared_task_face.py的逐文件restore/apply、test_globs=()适用；diagnostics恢复1、apply0、testfiles1与本题吻合。合理业务修复不需修改无法提交/被恢复文件。静态未做runner/配置攻击，也未核真实镜像/祖先Git是否含答案。
8. **关系/用途（5/29–30/37–40）**：本题是overlap/归一化逻辑错误，与本包前两题错误字符串目标不同；不能同仓即并簇。尚未用Git历史确认更广重复关系。已见私有答案和历史结果，不可作为公开solver独立成功证据；模型成功率/训练价值/费用未知。

## 执行、解析、冻结引用各自的证据

全部为09-19历史RH2 replay原件的复读，未本轮重跑。

- **原spec与输入**：A内pinned `envpack/data/swegym_specs_242429c1.json`（已核SHA=`0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`）python/mypy0.820指定Python3.9，install为 `python -m pip install -r test-requirements.txt; python -m pip install -e .; pip install pytest pytest-xdist; hash -r;`。与1.4两題不同，不删最后pip命令。pre_install还声明typeshed submodule更新以及向test-requirements首行插入`types-typing-extensions==3.7.3`；这是原spec，不是本轮修改授权或安装段重执行证据。实际日志已看到该首行pin生效。
- **派生镜像**：install_wave1 launcher:32–47只COPY离线wheel与PIP_NO_INDEX/PIP_FIND_LINKS；53–62调用baseline `scripts/replay_grade.py`，R/status核原命令，无recipe/materials/reference_bindings覆盖。plan本题entry及R/image.json pins只有setuptools75.1.0、wheel0.44.0、packaging24.1；不是本包前两题的九pins。derived ID=`sha256:1a440521871061d2e8db3fa660c7bf1a225d7fed9ac82d70dbda6cd726af7369`，base digest=`ede92…691a6`对上public。原build context/wheel payload本地未保存，当前目标机镜像未验。
- **安装实证**：gold `…f589d38e.eval.log`:430–507，noop `…e59bc664.eval.log`:403–480全部段已读，requirements satisfied、editable build/install完成、第三条pip pytest/xdist也satisfied。包含typed_ast1.4.3、mypy_extensions0.4.4、types-typing-extensions3.7.3、pytest6.1.2/xdist1.34.0。不能把COPY/ENV或最后hash的RC0代替这段证据。导入观测`/testbed/mypy/__init__.py`、版本字段`?`，未据此夸成所有模块/actor已验。
- **实际执行**：gold log:521–539、noop:494–527，命令为 `pytest -n0 -rA -k 'testOverlappingAnyTypeWithoutStrictOptional or testUnimportedHintAny'`，9422collected/9419deselected/3selected。gold3PASS/RC0；noop新增F2P FAILED（Expected为空、Actual一条Optional[Any]不重叠错误），另外两节点PASS/RC1。
- **为何选到3例**：A/spec_vendor.py:136–137、183–190从test_patch所有`[case...]`提名字：新增case和上下文`testUnimportedHintAny`。pytest -k子串匹配又选中`testUnimportedHintAnyLower`。紧邻负例FixedLengthTuple只在hunk文本中出现语句而无case header，未选中。这是实际执行集合，不是全文件。
- **解析与参考**：A/prepared_task_face:308–310 → scoring.py:229–269，只对Start/End标记段用swegym_pytest摘要解析；冻结Q/grading参考是F2P1/P2P2。diagnostics parsed3、outside0、missing[]、skipped[]。R/{gold,noop}/ledger.jsonl:1分别报reward1(F2P1/1)与reward0(F2P0/1)，P2P均0失败。按源码/摘要/冻结集合三层核对，未运行parser；不存在由parsed count直接推定业务运行。
- **身份/字节**：两log与ledger SHA均重算对上Q/run_refs；gold log=`972f0896b4f421ed102b7dcc55989276414bed3c3d9518207ee0e2c20c4dbb70`、noop=`57654a66e8dd753ca1d00674ec9055b0c02c6f009ba443edc656674aee7a6272`。scripts_digest=`189eec402958038c0c5aebade55f0b026f82c0e8c7173700e7140bd86c60af85`。原candidate apply是agent/54321，grader是rh2grader/54322、deny_all、2CPU/4GiB/PID512/tmp1GiB/shm64MiB、可写conda prefix；qualification absent、cleanup removed=true。baseline四成员SHA已核；只用tarfile.extractfile沿函数调用读归档文本，未解包/import。
- **正式actor边界**：临时候选apply身份不能证明CC正式actor能开发；baseline/prepared_task_face:336–350正式rollout取public.image，派生镜像消费/激活/工具/目录权限未验。静态包也未捕获真实用户消息与public_hints注入。

## 最小后续（均未执行）

| 需要 | 公开依据 | 现证据/缺口 | 后续验证 |
|---|---|---|---|
| 工作区mypy源码生效 | README安装说明、__main__.py | 历史grader安装成功/导入顶层来自testbed；actor未知 | actor记录UID/HOME/cwd、Python/包路径，再 `python -m mypy` 检查题面小程序 |
| Python3.9与旧pytest/typed_ast | requirements与原spec | 原日志有准确版本；目标机image/wheel资产待准备 | 准备时固定所需离线版本；运行公开窄测试 `pytest -n0 -k 'testStrictEqualityAny or testStrictEqualityWithFixedLengthTupleInCheck'` |
| 保留非strict模式真实不重叠告警 | docs strict-equality与no-strict-optional说明 | 当前三个计分节点无相关负对照 | 另备公开性质复现：同两flags，`if 1 in ('x','y'):pass`应报错；原Optional[Any]例不报错；切strict_optional开启两者仍合理 |
| 交付 | tracked meet.py/checkexpr.py | 无系统修改/新资产需求，官方恢复仅上述.test | 看frozen projection和实际源码生效，不修改expected/reference/reward |

**唯一优先CPU实验**：在新重定位的固定baseline replay条件下，做一个仅“非strict_optional时dangerous_comparison早返回False”的静态候选，对照base/gold。每者同时记录原三节点评分与上表真正不重叠的公开例。预期该候选若评分1却漏报负例，即实证评分过宽；若没有拿分，先定位实际链路差异，不反向认定评分已充分。候选尚未写/执行；不需要另加第二个新候选。后续修订应依据公开旧行为补负例，再查合理替代解，不能为了gold或分数改期望。

固定grader语义校准不以正式actor全验为硬前置；真实模型开发需要另补actor镜像消费、激活、工具、写权限、资源与清理证据。未来运行必须另建重定位summary/manifest与输出，原prepared内`/work/...`不能直接充当本机入口，历史账本不写。未查完整全仓回归、全部类型/调用者、真实模型交互和成本；未知未假填pass。

## 整包独立阶段结束前的关系补记

三题均已有初稿后、任何主审/旧结论暴露前，追加核对自己三题的精确源码：15184 base/messages.py:2519–2521已含15139 gold的lowercase分支；15139和15184各自base/meet.py:300–312均已将Any检查放在非strict optional的Union去None之后，即10174的关键修复结构已经存在。只说明后题base包含前题修复信息，不证明Git谱系/同问题重复，也不合并三种目标。此补记新增暴露范围仅为同包三题这些源码行；无其它题或history读取。三题gold文件hash均已重算，与validation/原ledger相符。
