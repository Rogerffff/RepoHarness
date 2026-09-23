# python__mypy-10308：无历史私有初稿

2026-09-21；主审 B2；`disposition.state=needs_review`，`scope=static_review`；`usage.intended_use=development_diagnostic`。仅静态阅读既有源码、日志、工件及标准库 JSON/哈希检查，未运行项目代码、测试、安装、容器、网络或模型。本文保存后等待协调者封存，尚未读取 `I2/history/python__mypy-10308/refs.json` 或旧调查。

路径约定：`ROOT=${REPO_ROOT}`；`U=ROOT/runs/swegym_quality_batch02_20260921_v2/public/python__mypy-10308`；`P=ROOT/runs/swegym_quality_batch02_20260921_v2/private/python__mypy-10308`；`M=ROOT/runs/env_recipe_repair_20260919/materials_v2`；`G=M/runs/python__mypy-10308-gold`；`N=M/runs/python__mypy-10308-noop`。下文 `base/` 相对 U，RH2 源码路径相对 ROOT。日志简称：`Glog=G/eval_logs/evallog_replay-er19-mat1-python__e8bba825.eval.log`，`Nlog=N/eval_logs/evallog_replay-er19-mat1-python__4cc880f8.eval.log`。

**初判：**公开需求明确到可以独立调查；既存、带版本的 materials-v2 评分对照支持真实目标路径上的 no-op/gold 分差。它不是原 S2 材料原样验收，也不是正式 actor 开发条件验收。唯一冻结 F2P 具有正、负行为断言，不能称为只测“不崩溃”；但没有 P2P，且没有直接执行题面原例的证据。保留静态诊断候选，暂不判 reject、不自动改测试或评分、不宣称已经 ready_for_probe。

## 1. 公开需求、材料身份与初态

- 公开 issue 要求定义 `Vector`、`Matrix` 两个相关泛型协议时不出现 INTERNAL ERROR。`Vector` 有 `__len__`、`__add__`，`Matrix` 有 `__add__`；两者通过参数/返回注解关联而非继承。代码含默认不变的 `T1/T2`、`float` 上界、显式 self 注解、联合参数与递归返回类型。题面没有规定修复后必须完全无普通诊断、退出码必须 0，也没有指定补丁函数或实现方式（`U/user_prompt.txt:3–32,90–96`）。
- 公开旧语义要求结构子类型成员齐全且类型兼容，支持递归/互递归协议，并保留泛型推断、变型和可写属性规则（`base/docs/source/protocols.rst:6–22,384–411`，本稿 §4 的旧测试）。报告人的 mypy 0.790/Python 3.8.5/Windows 10 与任务基线版本有区别；真正目标是 bundle 指定的提交，不能下载安装较新 mypy 代替工作区。
- `base_commit=1567e36165b00d532f232cb3d33d1faf04aaf63d`，base tree `10a663a06c492e815950d648d3631868504e1f9e`；导出身份记录为 1470 个 blob、无 gitlinks/symlinks/LFS 缺件、无 `.git`。`P/source_refs.json` 指向的 S2 public/grading/validation 三个 JSONL **第 179 行**逐对象等于本题包。`P/gold.patch` 的 SHA256 为 `4d9843b52d969a2d73a05a4a00e6c5639a4d49706add7f11a6a2aa1321a3672e`，与 validation 和 gold ledger 一致。
- public image 是 `xingyaoww/sweb.eval.x86_64.python_s_mypy-10308:latest`，锚定 manifest `sha256:8204090027b336ea9218901ad8a83c34436f128a41041673243c25ff5fcc69c3`。两份历史诊断 stage 的 HEAD 都是该 base；两个 baseline 工件相等。用工件中的内容摘要对静态导出作元数据比对：1469 个公开文件一致，唯一不同是 `test-requirements.txt`；多 6 个 `mypy.egg-info/*` 文件。Nlog:130–149,208–217 显示初态已有 `types-typing-extensions==3.7.3` 这一行，不能把它归为候选修复或盲目清掉。
- 调用链有源码与已有运行相互支持：`checker.check_protocol_variance:1805–1830` → `subtypes.is_protocol_implementation:503–583` → 成员绑定/展开 `:586–631,674–702` → `expandtype:98–127` 的联合简化 → `typeops:317–387` 的 proper subtype → generic callable/constraint 推断 `subtypes:827–843,1049–1086` → `constraints:378–444`。递归假设可能先返回 True，而成员推断仍断言两侧成员都存在。Nlog:612–722 的真实 F2P traceback 落在 `constraints.py:437`；这不是仅凭 gold 差异猜初态。**原题 Vector/Matrix 代码本身尚未由本次允许日志直接证实。**
- `user_prompt.txt` 是静态渲染而非捕获消息。当前 `prepared_task_face.py:342–356` 使用 public image/digest、`render_user_prompt` 并传 public bundle；`bundles.py:282–290` 的渲染仅含 issue。`public_hints` 仍是模型可读字段，不能因没在 user_prompt 中出现就当作不可见。“conda 已激活”是待验声明；“所有测试修改都会恢复”不代表当前具体恢复规则。若“禁止改测试”操作指令适用，本题已有合法非测试源码修复路径，尚未发现它排除必要修复；其实际消息适用情况待核。

## 2. 原 S2 与既存 materials-v2 修订，不能混记

`P/grading.json` 为 `rh2.private_grading_bundle.v2`、mypy 0.820/Python 声明 3.9、`eval_cmd=pytest -n0 -rA -k`，冻结 F2P 只有 `mypy/test/testcheck.py::TypeCheckSuite::testTwoUncomfortablyIncompatibleProtocolsWithoutRunningInIssue9771`，P2P 为空。

原 test patch 只改 `test-data/unit/check-protocols.test`：新增目标 case 和 `testHashable`，后者引用原 base 不存在的 `fixtures/object_hashable.pyi`；原 `typing-full.pyi` 也没有 Hashable。`mypy/test/data.py:69–81,238–248` 会在 setup 读取并复制这些 fixtures，因此原材料有具体的测试依赖缺件；本稿没有获准读取或声称重现原材料整套评分结果，也不从这个非引用 case 的失败推导原 reward 必为 0。

本次可核实的运行实际使用 **09-19 已存在的材料修订**：

| 项目 | 原件与核对结果 |
| --- | --- |
| 输入配置 | `M/materials.json` 仅抽取顶层 `version=materials-v2` 与 `tasks/python__mypy-10308`，没有查看其他 task 内容。 |
| 每次运行审计 | `G/materials/materials.json` 与 `N/materials/materials.json` 对象相等，输入条目字段逐个相等。审计文件是单条目加 digest/scope，**不是可直接传给 `--materials` 的输入配置**。 |
| test patch 身份 | 原 SHA256 `17e5df4826ca8f10bc17381a85a2f539c6001eee5a959dab39bd13c45423a42f`；修订 SHA256 `e139b55e06645736212fa707a276588537373d6b01be3d16d45532155d6c90ed`。去掉新增 index 元数据后，`check-protocols.test` 原有新增块逐字相等；没有改错误文本、输入或两个 case 的断言。 |
| 新材料 | 增 `object_hashable.pyi`（object.__hash__→int 和最低限度类型声明）；向 `typing-full.pyi` 增有抽象 `__hash__→int` 的 Hashable Protocol；向 `test-requirements.txt` 增 `types-typing-extensions==3.7.3`。不是只改两个 fixture，也不是本轮新加验收。 |
| 来源说明的限度 | 输入条目 `evidence.commit=c0490b4c2d2bc3f385c548089245c929ca4b0448` 并附 fixture patch；本轮读取了该内嵌补丁，未打开未来 commit/PR 或历史调查。不能把该说明当作已独立核验外部上游历史。 |
| grading digest | 按当前 `contracts/_base.py:86–96` 的排序、紧凑 JSON 算法仅作标准库元数据重算：原 `sha256:868b96a8cb7abe13a644884c99dcb33fb85f893865968526b64ad4520f6fb221`，仅替换 test_patch 后 `sha256:6fe0fad6693159c8f245f5627888efa35053e56843240729e971f9640fd331d4`，与两份审计完全匹配。F2P/P2P 未变。 |

真实入口的静态证据是 `M/run_material_cases.py:27–43,46–54`：选择本题 install_wave1 image，再由 RH2 Python 执行 `M/replay_with_install_recipe.py --code-root /work/full216_20260919/code/rh2 --materials M/materials.json --audit-dir <run>/materials -- run ... --task-ids python__mypy-10308 --candidate noop/gold-dir:...`。这里 M 在历史机上由 `RH2_MATERIALS_ROOT`/driver ROOT 指定；不要把本机 ROOT 或审计输出误拼作历史可执行命令。

`replay_with_install_recipe.py:42–60` 读取 `materials["tasks"][view.instance_id]`，校验原 patch hash，用修订 test_patch 重新渲染官方恢复/应用脚本及精确文件保护；断言派生 candidate test script 完全不变。评分闭包仍使用原冻结引用。`grader_version` 后缀取输入 `materials-v2`；ledger 的 `derived_image_recipe=verified-assets-dependencies+materials-v1` 是旧标签，不能推翻实读审计或充当版本权威。审计 scope 明说 prepared source package 保留、production 前需 refreeze；不能宣称正式 face 已消费修订。

## 3. 每条新增断言、执行选集和真正奖励

测试没有 Mock 或网络服务。`TypeCheckSuite` 由 `mypy/test/testcheck.py:26–97` 收集 `.test` 数据；`data.py:522–565` 生成 pytest case，setup 在临时目录准备输入/fixture，`testcheck.py:137–234` 调用真实 `build.build` 并比较完整诊断数组。F2P 默认用 `test-data/unit/lib-stub/{typing,builtins}.pyi`：typing 的 Protocol、TypeVar、Union、cast 是类型检查器识别的特殊声明，不是运行时执行这些协议对象。`modulefinder.py:648–656` 和 `[builtins]/[typing]` 决定 fixture 来源。测试未开启题面全部 strict/CLI 选项，不比较 runtime 加法结果。

**F2P：**P1[T1]、P2[T1] 的 T1 协变且无上界，方法泛型 T2 默认不变；P1 有 `a(other:P1[T2])->T1`、`b()->int`，P2 只有接收 `Union[P1[T2],P2[T2]]` 的 a。`cast(..., 1)` 仅建立输入类型，目标是定义检查与四次赋值。以下覆盖原/修订中全部新增可观察断言：

| 断言/位置（P/test.patch） | 实际验证、公开依据与限度 |
| --- | --- |
| `p11:P1=cast(P1,1)`（:21）无诊断 | 自身协议可赋值，防止“一律拒绝所有协议”。由既有结构子类型语义支持。 |
| main:14 error（:26） | P2→P1 赋值不兼容；P2 缺 b。不是仅捕获不崩溃。 |
| main:14 note“missing following P1 protocol member”（:27）及 b（:28） | 同一错误的缺成员理由和成员名；来自公开结构兼容规则及已有诊断样式。 |
| main:15 error（:29） | P1→P2 也不兼容：P1.a 的参数只接受 P1，不能满足 P2.a 要求的更宽联合参数。 |
| main:15 note“Following member(s) ... have conflicts”（:30） | 明确以 a 的签名冲突解释第二次错误。 |
| main:15 note“Expected”（:31）及 `def [T2] a(self, other: Union[P1[T2], P2[T2]]) -> Any`（:32） | 比较所需泛型方法形状和 Union 顺序/格式；未给类 T1 实参导致 Any，不意味着测试允许将所有推断全退化为 Any。 |
| main:15 note“Got”（:33）及 `def [T2] a(self, other: P1[T2]) -> Any`（:34） | 比较实际泛型方法；与公开旧 `testGenericMethodWithProtocol2`、`testProtocolIncompatibilityWithGenericMethod*` 的现有诊断惯例一致。 |
| `p22:P2=cast(P2,1)`（:24）无诊断 | 第二个自身协议赋值合法。这里尾部裸 `# E` 没有冒号/消息，不生成预期错误；`data.expand_errors:421–445` 仅识别 `E: message`。p12 的裸 `# E` 同样只是注释，真正 oracle 来自 `[out]`。 |
| 整个 F2P 正常返回并且没有额外输出 | 定义/赋值触发实际协议推断，不允许 INTERNAL ERROR、SystemExit 2、漏报/多报。`assert_string_arrays_equal` 除路径规范化和 can't/cannot 等清理外比较顺序和文本（`testcheck:214–234`，`helpers:47–58,117`）。 |
| `testHashable` 的唯一 inline E（:44） | `f(Hashable)` 接收 `Iterable[str]` 应报参数不兼容，单看 Iterable 协议并不能保证 `__hash__`。修订 fixture 的 object 有 `__hash__`，使检查必须区分“协议承诺的成员”与所有对象的默认实现。它没有递归/泛型方法，扩大到同一成员集合语义的行为；**不是冻结奖励引用**。 |

`testWeirdRecursiveInferenceForProtocols-skip` 只是 diff 上下文，未新增/修改它的断言。vendor 正则从整个 patch 的 `[case ...]` 抽名（`spec_vendor.py:183–190`），所以命令也出现它；mypy collector 把 `-skip` 拆成标志、case 名不带该后缀，实录只选到上述两个测试，不能把它计为第三个已执行或已保护回归。

三种集合分别记录：

1. **命令选择表达式**：`pytest -n0 -rA -k 'testTwoUncomfortablyIncompatibleProtocolsWithoutRunningInIssue9771 or testHashable or testWeirdRecursiveInferenceForProtocols-skip'`。
2. **实际执行/解析**：9461 collected，9459 deselected，2 selected；Glog:552–569 两项 PASSED，Nlog:513–754 两项 FAILED；ledger 各解析 2 个 ID，reference missing/skipped 都空、段外解析 0。没有把收集数量当成 9461 项已验证。
3. **冻结奖励引用**：只有第一项 F2P；P2P=0。当前 `scoring.py:234–269` 按 Start/End 段解析并用冻结 F2P/P2P 生成 report。普通完整 pytest rc=1 的非引用断言失败不自动将 reward 变 0；`manager.py:1197–1248` 另判全局启动/收集失败等。Hashable 的执行证据有意义，但不是 reward 门。

同条件既有运行证据：

| 引用 | no-op | gold |
| --- | --- | --- |
| 原始定位 | `N/ledger.jsonl:1`，run_id `er19-mat1-python__mypy-10308-noop`，attempt 1 | `G/ledger.jsonl:1`，run_id `er19-mat1-python__mypy-10308-gold`，attempt 1 |
| 安装/选测 | 三段安装可读成功，最后 RC 0；test RC 1 | 三段安装可读成功，最后 RC 0；test RC 0 |
| 目标失败/成功 | Nlog:523–728，F2P 调到真实 build 后 `constraints.py:437` AssertionError → SystemExit 2；Hashable 的 actual 为空（:729–742） | Glog:563–565，两个完整 ID PASSED |
| 冻结得分 | F2P 0/1，P2P 0，reward 0，tests_failed | F2P 1/1，P2P 0，reward 1，resolved |
| 工件/清理 | 空投影；stage_error null，cleanup removed，driver close 无遗留/失败 | 仅投影 `mypy/subtypes.py`；stage_error null，cleanup 同上 |

两份日志 SHA256 分别为 G `be717835596068b80d595f76d518350d5eb28ae3f4251e00533d2ea2395fae64`、N `2d4db3977187a6ca65850d1b39afb3c869fb5ed25105e543ba8cb2a54eb0c398`，本轮重算与 run_refs、ledger 一致。日志内包含真实调用栈、fixture 输出比对以及最终 summary，比仅 parser 的 PASSED/FAILED 标签多一层执行证据；仍非本轮新运行。

## 4. 需求—测试双向映射、回归与合理替代解

| 公开要求或合理旧行为 | 对应验收/公开回归 | 覆盖判断 |
| --- | --- | --- |
| 题面两个协议定义正常完成检查 | F2P 同样经历协议变型→Union→泛型方法→约束断言；真实 no-op traceback 命中 | **部分**。测试名、普通方法 a/b 不是题面 add/len；类参数协变而非不变，没有 float 上界、显式 self、递归联合返回类型，未直接运行原 CLI/原例。 |
| 缺成员不得接受，较窄 callable 不得满足较宽参数契约 | F2P 两个错误及对应 notes | **覆盖这两组输入**；不是任意协议关系的证明。关键错误依据来自公开旧规则，未要求 gold 内部 helper/集合实现。 |
| 合法自身协议赋值不报错 | F2P p11/p22 | **覆盖**，所以不能说 P2P=0 就“毫无正例”。 |
| 普通类可以结构实现协议，动态属性受已有规则约束 | `testSimpleProtocolOneMethod`（base:13–40）；`testClassesGetattrWithProtocols`（:1902–1935）含 C2 可写属性、C 的只读 property 合法与 D 类型不匹配 | **冻结缺失**，这些 case 不在实际命令或 P2P；本轮只静态读取。 |
| 递归合法推断与互递归不匹配 | `testRecursiveProtocols1/2`、`testRecursiveProtocolSubtleMismatch`、`testMutuallyRecursiveProtocols`、两个 `...SubteMismatch*`（:770–887）；`testInferProtocolFromProtocol`（:1281–1299） | **冻结缺失**。有明确 int/Box[int]/str 推断与负例可作窄回归，不以同文件数量代替覆盖。 |
| 变型/可写属性/泛型方法签名不能退化 | `testAutomaticProtocolVariance`、`testProtocolVarianceWithCallableAndList`（:436–487），`testGenericSubProtocolsExtension{Invariant,Covariant}`（:624–683），`testBadVarianceInProtocols`/`testSubtleBadVarianceInProtocols`（:730–765），泛型方法正负测试（:403–434,1957–2015） | **冻结缺失**；F2P 自身的泛型方法冲突覆盖一个局部，不覆盖这些旧行为。 |
| `__init__`/`__new__` 忽略规则继续适用 | `subtypes:531–534`；公开 `testProhibitSelfDefinitionInProtocols:336–362` 保留构造签名不参与结构兼容的行为 | gold 显式继续忽略两者；**新增验收没有专门测此规则**。未找到/未逐条展开所有 `__new__` 回归。 |
| 不从协议继承的 object.__hash__ 推出 Hashable 契约 | 新 `testHashable`，`nodes.protocol_members:2491–2501` 排除 object | **实际执行覆盖、冻结奖励缺失**。没有把此附带 case 扩写成 issue 新硬要求。 |

未读全仓用例、daemon/incremental 等所有调用者，也未运行任何上述旧回归。零 P2P 是明确范围限制，不等于已证明存在回归或题目无效。

**合理非 gold 路线：**在结构约束推断入口/成员配对阶段先确认此次推断需要的两侧成员齐全；遇到暂时递归假设但缺成员时，保守放弃此次结构约束推断，仍让外层正常兼容检查拒绝关系。需要避免保留一半约束，并保持合法递归推断。它修改 `constraints.py` 而非 gold 的协议集合预检，公开语义允许此路线；新增测试只观察行为，没有指定 guard 的位置、helper 名或调用次数。其是否生成原有两条诊断和 notes，仍须执行，本文没有宣布所有替代解都能通过。精确消息在公开旧 suite 有充分先例，现无具体已证实的误拒解。

**一个有针对性的部分实现候选（仅静态推断，未写补丁、未运行、未宣布 reward 1）：**把成员预检错误地限制为“两侧协议的所有类 TypeVar 均为 COVARIANT”，其余关系继续原路径。F2P 的 P1/P2 类 T1 都协变，它在目标关系上将执行与完整预检相同的行为；题面 Vector/Matrix 的 T1 是默认不变，关键关系仍绕开预检。`check_protocol_variance` 使用 ignore_declared_variance 判断，但不会改写声明的 tvar.variance（`checker:1815–1830`），因此这是可区分的真实输入差异。用原题原例与修订版真实 RH2 同测该候选，才能确认是否出现“原例仍崩溃而冻结得分 1”。这属于待验证的 coverage 线索，不是已经成立的假阳性或自动改题理由。

## 5. Gold 按公开要求检查

gold 在递归 assuming 短路之前，对两个协议的必要成员集合作包含判断，忽略原本就不参与检查的 `__init__`/`__new__`；普通类不走此新集合检查。`nodes.protocol_members` 包括各协议基类声明、排除 object，且排序使 a/`__add__` 先于 b/`__len__`，能解释为何预检缺成员避免尚未检查 b/len 时的递归 True。它保留普通/proper 两条判断和后续成员签名、可写、ClassVar/static 规则，也在早退前继续调用 TypeState 记录协议依赖。

这支持 gold 处理公开根因的静态合理性，没有需要另外交付的新包、fixture 或编译产物；但“原例全部已修复”仍缺原例执行证据。它同时修正了 Hashable case 所揭示的协议成员集合行为；该行为由同一 guard 导致，不是额外独立生产补丁。唯一无关改动是 find_member docstring 的 `Fin`→`Find`，无行为影响。

`G/artifacts/swe_gym_lite--python__mypy-10308/a1-11e70e2b/candidate.patch` 与 P/gold.patch 字节相等；frozen_patch 只有 subtypes.py 一项，解码后内容 hash `3180a2f9535a32572487c2e7957e95b32327ea94a156e4673b0aff1a900de313` 匹配工件，静态与 base 的 diff 等于该 gold 变更。无项目代码执行参与此核对。该证据支持这次得分确有源码变更交付，不能只用 editable 安装版本的 `.dirty` 字样作候选生效证明。

## 6. Actor 开发条件与既有 grader 环境的范围

`install_wave1/tasks/python__mypy-10308/image.json` 和 build.log:8–28 记录在 public manifest 所指 base（本地 ID `sha256:594e6750e110f7675fd6d49c3d6dd3c7018c6b276eeab9c9d95b31d8607f1f40`）上 COPY build wheels，设置 `PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`，派生 ID `sha256:9acbdc2f996afc47c0f85a9b3f6cb67d62055a22bf1545d29f26e44ee1a8b51d`。pins 是 setuptools 75.1.0、wheel 0.44.0、packaging 24.1；通用构建机制只加 wheel 层并校验旧层保留（`run_install_wave1.py:24–47`）。这是准备阶段离线资产，不能当作允许 actor 运行时访问公网。

两份修订对照使用上述派生 image，grader 为 rh2grader/54322、deny_all、2 CPU、4 GiB、PID512、shm64 MiB、tmp1 GiB，允许候选安装写 `/opt/miniconda3/envs/testbed`。Glog:462–538、Nlog:423–486 及其后安装尾段显示 requirements、editable mypy、pytest/xdist 安装均有具体完成记录，而非只看最后 RC；实测 Python 3.9.19、pytest 6.1.2、xdist 1.34.0，导入观测为 `/testbed/mypy/__init__.py`。观测可被候选代码影响，需结合投影与目标失败/成功解读。

正式 actor 的代码事实则是 agent/54321（`sandbox_profile.py:311–339`）及 public image（`prepared_task_face.py:342–356`），并非自动选择上述派生 image，也没有本题 actor 可写解释器前缀验收。candidate.apply_user=agent/54321 只证明历史回放应用补丁所用身份，不证明 CC shell、导入、安装或测试在 actor 完整链已通过。

| 必要操作/资产 | 公开依据 | 已有证据和适用范围 | 当前缺口与最小验证（均建议，未执行） |
| --- | --- | --- | --- |
| 定位工作区、解释器、导入目标 mypy | 公开 traceback、`base/test-data/unit/README.md:126–143` 支持源码 `python -m mypy` | grader 安装/导入和冻结源码相符 | 在正式 actor shell 记录 UID/HOME/cwd、PATH，执行 `python -c 'import sys,mypy,mypy.main; print(sys.executable); print(mypy.__file__); print(mypy.main.__file__)'`；预期目标工作区。 |
| Python 3 parsing 与运行依赖 | `setup.py:194–203`、mypy-requirements；`fastparse.py:42–81` | 历史 grader Python3.9、typing_extensions/mypy_extensions/toml 等可用；≥3.8 的 Python3 parser 使用 stdlib ast，不能把 typed_ast 或 Python2 运行时列作该复现绝对前提 | actor 包版本和读取权限未验；准备期固定所需包，解题期无需额外网络。 |
| 公开 typeshed、fixture、pytest 插件 | `pytest.ini:4–22`、conftest:3–11、data:69–81,238–248 | public 含默认 lib-stub；隐藏 Hashable fixture 已在 grader 修订中恢复 | actor 应可运行公开旧 case；不需要提供隐藏 fixture/gold 给 solver。-n0 仍要求 xdist 插件存在。 |
| 原题自包含输入、临时缓存/测试目录 | 题面只有 typing；data:238–255 | 不需数据集、远程服务、凭证；grader 本组选测约 127 MiB 峰值、3.8–4.6 秒为已记历史观测 | actor /tmp、home、工作区实际权限/资源未验；历史窄测不推断全套测试或模型工具成本。 |
| 修改和验证算法 | 原 traceback；setup.py:77–85,155–156 的 mypyc 编译可选 | 合法修复 subtypes.py/constraints.py 可交付，已有依赖时可源码运行，无需 C 编译 | 真实 actor 执行公开原例和一组窄回归；无需系统提权、改不能提交的镜像文件。 |
| 候选安装阶段 | setup.py 和原 vendor 安装 | grader 在离线 wheels 条件下完成 editable install；test-requirements 已有 stub pin 并被修订恢复 | 正式 actor 不继承 grader UID/可写前缀；可先验证源码入口，是否需要 actor 安装由实际缺依赖决定。 |

原例建议命令：将题面代码原样保存为临时输入，在 `/testbed` 用 `python -m mypy --python-version 3.8 --follow-imports=silent --show-error-codes --warn-unused-ignores --warn-redundant-casts --strict --show-traceback --no-incremental /tmp/mypy10308_repro.py` 类型检查；不执行该输入 Python 文件。新增的 `--python-version 3.8`/`--no-incremental` 是固定语义/排除缓存的诊断设置，应在结果中注明。验收关注内部崩溃消失，普通类型诊断另作语义解释。

公开窄回归可用 `python -m pytest -q -n0 mypy/test/testcheck.py -k 'SimpleProtocolOneMethod or RecursiveProtocols or MutuallyRecursiveProtocols or InferProtocolFromProtocol or AutomaticProtocolVariance or GenericMethodWithProtocol or ClassesGetattrWithProtocols or ProhibitSelfDefinitionInProtocols'`。仅作为已有公开测试建议，不能把未运行的用例填 pass。当前不要求全仓测试、不要求 solver 获取私有 F2P。

## 7. 投影、官方恢复、泄漏与评分控制面

- 当前 `test_globs=()`（`prepared_task_face:332–336`、`manager:253–258`）。原 S2 官方恢复精确文件只有 `check-protocols.test`；诊断修订是该 `.test`、`fixtures/object_hashable.pyi`、`fixtures/typing-full.pyi`、`test-requirements.txt` 四个路径，**不是所有测试文件**。Glog:258–280 显示恢复 base 中已有的三个路径，新增 fixture 无 base 路径可恢复，然后四个 patch 都应用成功；:313–325 自证为四文件在位、无缺失/异常。普通生产源码没混入 test_patch；依赖配置被纳入受保护范围需明确记录。
- 合法算法修复不会触碰上述四路径；gold 的 subtypes.py 完整投影，潜在 constraints.py 路线也未被精确清单命中。若候选确需修改 test-requirements，其修改会被官方恢复覆盖；目前没有本题合法解决必须如此的证据。`additional_exclusions=[]`，不基于文件名增加排除。
- 测试使用工作区的 `conftest.py`、`mypy/test/data.py`、`mypy/test/helpers.py` 和配置；这些不是本题官方 patch 触碰路径，因此属于值得识别的评分控制面。篡改测试收集或输出比较不是业务修复，但本轮未做漏洞候选，也没有因静态可见性就宣布已能伪造 reward 或追加路径规则。ledger 记录 runner_integrity_changed=false，只支持这两次既有回放的观测。
- 静态 public 导出没有 gold/test patch/未来 Git；诊断 baseline 多出的六个 egg-info 路径只核了名称与摘要，未读内容。派生镜像 recipe 不 COPY gold/私有测试，官方修订在 grader 可信 setup 注入。真实 public image 的包、祖先 Git 对象、可见挂载、自动附加消息与工具访问未做 actor 验收，不能宣称“零泄漏”。
- 题面给了完整 traceback，正常提供根因入口而非指定答案；gold 注释中的 issue 9771 和材料 evidence commit 属私有暴露。未打开外链、未核网络获取答案；正式网络代码/共用卡的限制不等于本题实测。未读取其他题以检查重复/派生，故跨题关系未知，不按同仓或同文件聚类。
- 只确认历史 fresh grader 交付/评分/清理的这对运行；没有多次稳定性、并发、重置压力、真实 CC 求解成功率、token 或金钱成本证据。未知成本保留 null。

## 8. 八方面结论、优先下一步与暴露

| 方面 | 本次已查 | 未证/初步处置 |
| --- | --- | --- |
| 公开需求 | 完整题面/提示、公开协议契约、核心调用链 | 实际模型消息和原例运行未知；需求本身无已确认冲突。 |
| 材料/初态 | S2 精确行、base 元数据、原/修订 patch/hash/digest、历史初态和 F2P 崩溃 | 原 S2 缺 fixture 不混作已修订运行；正式 refreeze/actor 消费未验。 |
| 测试目标 | 全部新增输入与诊断、fixtures、runner、选择/解析/引用三集合 | 唯一 F2P 非完整题面原例；P2P 空；没有已执行的错误解对照。 |
| 合理解接受 | 公开诊断惯例、非 gold 约束推断路线 | 无具体已证误拒；替代实现的实际行为/得分未验。 |
| 回归/gold | gold 全 patch；递归、普通类、变型、generic callable、构造/动态属性旧测试 | 只静态抽查，未声明无回归；原例直接验证缺项。 |
| 开发条件 | 原始 wheel recipe/build、两次完整安装段、grader UID/资源、公开最小入口 | 正式 actor image、依赖、解释器、权限、消息/工具闭环未知。 |
| 交付/评分边界 | 原/修订精确恢复清单、实际 gold frozen artifact、当前冻结评分语义 | 未攻击运行器/控制面；公开提示的概括不替代机制；不加 exclusions。 |
| 关系/用途 | 本题修订关系、答案暴露、方法范围 | 跨题关系/真实模型能力不推断；仅 development_diagnostic。 |

**唯一优先下一步：**由统一 CPU 负责人在明确版本的正式 actor 开发条件下先验证解释器/源码来源，再作原题 Vector/Matrix 的 base/gold 对照，并保留普通诊断与内部异常区别。这同时填补最重要的开发条件和原例证据缺口；期间把 materials-v2 配方的实际消费、四个恢复路径与冻结引用版本写清楚。之后若要判断覆盖是否足以支撑该用途，再将 §4 的“仅协变 guard”候选与相同原例及真实冻结评分配对，不能先把怀疑写成坏题或改 oracle。本轮不执行这些建议。

暴露/阅读范围：

- 方法只读 investigator、record_template、actor_environment_card、quality_review_protocol 及其记录定义/40 项编号；没有跟进 B1/B2 汇总、batch manifest、chain_readiness、method_adjustments 或其他题结论。
- 本题 public bundle、user_prompt、environment_brief、base_identity、已封存 public_read；P 的 source_refs/run_refs/grading/validation/test/gold。主审是私有角色，不称自己的阅读为公开盲审。
- **明确披露：**完整打开了 P/environment_record.json，已看到 `issues=[install:python/mypy,mypy_fixture]`、`status=verified_environment_pair`、checks 的 gold/noop/安装/清理摘要及 history/analysis 链接名称；这些是预暴露的旧环境摘要，未用其标签定案，决定性事实在本文回到 ledger、log、工件核对。没有跟进其 `analysis_149.json`、`analysis_9.json`、`analysis_2.json` 或任何旧调查链接。两份材料审计中的 decision/evidence/scope 也已见，是授权的既存修订原件。
- 源码实际阅读：subtypes:251–275,503–718,818–851,1049–1088,1260–1302；constraints:285–444；checker:1805–1833；nodes:2350–2388,2491–2508；expandtype:12–31,98–128；typeops:317–337,350–387；modulefinder:640–658；fastparse:39–85；parse:13–35；setup:75–85,151–156,190–206；三份 requirements 全文；公开 protocols 文档6–24,384–420（另一次无关段230–249无判断用途）。
- 测试实际阅读：check-protocols:1–55,331–364,400–488,620–683,730–927,1280–1315,1900–1935,1957–2022；默认 typing/builtins stub 的开头；typing-full:1–65,140–154；testcheck:1–247；data:31–90,123–151,155–283,365–445,500–575；helpers:47–72,86–126；config/pytest.ini/conftest 全文；unit README:110–144。未完整阅读上述文件其余内容或全仓 9461 测试。
- 历史运行只读本题 G/N ledger:1、driver.log、指定 eval log 的安装/选择/结果/决定性 traceback、官方恢复段、stage/projection/candidate/frozen 工件与 baseline 元数据；未读其他 task 的原始运行。原始 log 未逐行阅读所有重复 conda 激活输出与 base commit 的无关 diff；未将这些段落记为人工核实内容。frozen artifact 曾输出一段 base64，随后只解码作静态源码 diff/hash，没有执行。
- 本题 install_wave1 image.json/build.log；构建脚本通用24–60；材料 wrapper1–60、driver 路由和39–54。**最小范围偏离披露：**一次读取 driver1–62 时也看到了其中25–26及44–45的非本题路由分支和 case 名，仅源代码路由，未打开它们的材料、运行、结论或答案；未把那些信息用于本题判断。
- 当前 RH2 只读本文引用的 bundle/render/spec_vendor/parser/scoring/manager/profile 函数；没有执行或修改 RH2。关键源码读取时 SHA256：prepared_task_face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`；scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`；spec_vendor `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`；manager `eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342`；sandbox_profile `698edb1740907f4255363d047e126d7f6b401677d907b1c1fcd694beb1fe5899`。wrapper hash `76cb33277bc2c013d37882afe89fc272a6a26ae0f2cea2adcb39fb2f1633b01c`，driver hash `3e85772f9726b4917517a63559c42b919587fe65b2f4a24dde4adb1d72cd079c`。

本轮唯一写入是本 `analysis_before_history.md`。历史 delta、card、screening JSON 留待封存及本题历史开放后完成，不提前读下一题历史。
