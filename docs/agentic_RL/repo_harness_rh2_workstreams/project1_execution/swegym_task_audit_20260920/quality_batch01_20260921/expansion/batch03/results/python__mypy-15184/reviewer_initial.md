# python__mypy-15184：独立初判

- 状态 `needs_review`，范围 `static_review`，用途 `development_diagnostic`。静态看可作为条件性开发诊断候选；不是环境已验或正式评测准入。
- 权威 ROOT=`.`。P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184`；Q 为同根 `private/python__mypy-15184`；R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-15184`；A=`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`。下述相对路径相对 ROOT，源码行号是 P/base 的本题版本。
- 暴露：四份共用方法、本题 P/Q 原件（已看到 test/gold、环境 gold/noop 摘要）、本题 inventory exact entry 与 common/install_wave1、精确指向的本题原始运行记录及 baseline 归档调用链。顺序上此前已独立检查 15139 的原件和写初判；未见任何题的主审/公开/旧质量结论，没有读取本批聚合或其它题调查。environment_record 的 analysis/history 链接未跟随。不是无结果盲审。只做文本/JSON/hash，未执行项目、测试、安装、网络、Docker 或解包归档。

## 结论

公开主目标是 **assert_type 失败消息在短名冲突时显示完整类型名**；末段“perhaps 两个同方法协议应判相同”是讨论，不是必须改变类型等价判断的要求。两个新增 F2P 精确验证冲突类型的 qualified names，新增 P2P 验证无冲突时保持短名。gold 只将 assert_type 的两次单独 format 改成既有成对消歧 helper，保留比较规则、错误代码、上下文与返回类型，静态看符合主目标。未发现需要先改题的决定性缺陷。

覆盖限度必须保留：新增测试全是 `array` 类型，没有直接使用题面 `typing_extensions.SupportsIndex`、`typing.assert_type`/extensions 两入口对照、嵌套类型参数内同名或递归 alias。原公开示例的两个 SupportsIndex 在本 base typeshed 仍是独立类，gold 的 Instance 消歧路径适用，属于有源码支持的推断，尚非执行证实。优先后续在精确 base/gold 上核原例与现有 assert_type 旧例即可；不必为了凑数构造双候选。

## 八方面及完整断言映射

新增文件 `test-data/unit/check-assert-type-fail.test` 共28行，三例全部读完；每例唯一 `# E:` 加“其它行无诊断”的完整输出数组比较：

| 要求/回归 | 公开依据 | 参考节点与决定性断言 | 覆盖与运行事实 |
|---|---|---|---|
| 两侧不同 fullname 的同名类型应明确区分 | user_prompt:3、23–26；messages.py:2584–2602 的既有 overlap 语义 | F2P `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::testAssertTypeFail1`：外部 `array.array[int]` 对当前模块 class array，要求 `Expression is of type "array.array[int]", not "__main__.array"` | 直接覆盖，noop 为 `"array[int]", not "array"`，gold PASSED |
| 内嵌 class 同名须保留完整路径 | 同一公开消歧目标；Instance fullname 规则 messages.py:2412–2415 | F2P 同文件 `testAssertTypeFail2`：本地 class array 内再定义 class array，要求 `"array.array[int]", not "__main__.array.array"` | 直接覆盖，同样 noop FAILED/gold PASSED |
| 无同名冲突不扩大为所有类型全限定 | 标题 when names are ambiguous；已有 assert_type 与普通错误保留短名 | P2P 同文件 `testAssertTypeFail3`：同样背景类，但比较 arr.array[int] 对 int，要求 `"array[int]", not "int"` | 完整 P2P，gold/noop 均 PASSED；能拒绝简单把两端总设 verbosity=2 的方案 |
| 原例 SupportsIndex 的 typing/typing_extensions 来源可分辨 | typeshed/stdlib/typing.pyi:308–312 与 typing_extensions.pyi:181–184 独立协议类；题面源码 | 无直接新增测试 | 部分：共用 Instance fullname 分支有依据；题面调用链/类型变量推断与两个协议本体未执行 |
| assert_type 成功时无误报并返回原类型；失败错误码、泛型和 unchecked 提示不回归 | checkexpr.py:3911–3932；docs/source/error_code_list.rst:884–896；check-expressions.test:931–990 | 冻结 P2P只有上面一例，未纳入旧 `testAssertType`/Generic/Unchecked/NoPromoteUnion | gold 不改判等，只改单个失败 renderer；现有旧例已静态读，未由历史本命令执行 |

1. **公开需求（3/23）**：读 public_bundle/user_prompt/environment_brief，docs assert-type 说明。现有 messages.py 的 list item、setitem、comparison 等调用者已使用 `format_type_distinctly`（654–676、730–741、1518–1526），所以采用成对 fullname 策略可以从公开源码发现。公开原例允许失败，重点是解释失败原因；不应把“让两个协议相等”当唯一正确解。实际 CC 消息与 public_hints 注入未捕获。
2. **材料/初态（1/2/27）**：base_commit=`13f35ad0915e70c2c299e2eb308968c86117132d`，P/base_identity 记录1416 blob entries、无 gitlinks/LFS；未重哈希全部 base。Q/source_refs 的 ingest 第203行三份 raw SHA 已重核匹配；prepared_manifest tasks[202] exact entry 为本题；host_grading_views 第203行 SHA=`d190a0683ec0eb488dff1e37e1be9bf4a1da60e202d9ff2de0d4ea060637a259` 且 grading 与冻结 Q/grading.json 相等。gold SHA=`365adadcf2ad3dbed4dc98bf30ebda81f9c788a8ced939ff2a2abd8bfef1a280` 由 validation 和原 ledger 对应，本轮另核文件 hash。base `assert_type_fail` 在1658–1664分别 format 两端，无法知道彼此短名重合，noop 两个明确输出差异佐证初态。
3. **测试有效性（18–20/25/32）**：无新增 Python helper；三例都指定 `[builtins fixtures/tuple.pyi]`，fixture 全文已读：提供 object/type/int/tuple/list 等基本类型。typing stub 的 assert_type=0 是已有 semantic special form 标记（lib-stub/typing.pyi:1–23），不是运行时调用假断言。外部 array 的 typeshed 实体在 array.pyi:18，泛型和需要的类型声明已读。testcheck.py:93–184 调 build 并比较整个输出；data.py expand_errors/fixture 路径和 helpers.py parse_options 已核与15139对应文件逐字相同，复用了先前静态阅读。无 flags 时 helper 默认旧式测试选项；不是“pytest 有节点即业务通过”。
4. **误拒合理解（24/28）**：fullnames 和不冲突短名都有公开依据；测试不绑定 helper 名、调用顺序或代码结构。另一合理实现是按两侧各自所含 Instance 收集同名冲突，再把共同的 fullname 集合传 formatter，保持 quotes/error code。简单无条件全限定会被 P2P拒绝，但这与限定“when ambiguous”及旧文案一致，不是已证实误拒。原需求是否允许附加 note 来消歧而不是主句 fullname，有形式上的空间，公开明确“output fully qualified names”及既有格式使当前精确比较合理；没有具体已验证替代解被误拒。
5. **回归/gold（26/27）**：已读 gold 全部，两行只改变 assert_type_fail。`checkexpr.visit_assert_type_expr` 比较 is_same_type、保留 Literal last_known_value、unchecked note 和返回 source_type 均未改。`format_type_distinctly` 先以所有类型的重名集格式化，再在 verbosity0/1内尝试区分、quote；`CollectAllInstancesQuery`/typetraverser.py:75–104 覆盖 Instance、参数、tuple/union/TypeType；非递归 alias 的 target 在 messages.py:2578–2581跟随。已读旧 assert_type 五例和多个 formatter 公开调用者；未逐行审完整消息系统、递归 alias/TypeVar 同名、全部错误码或全仓 P2P。
6. **开发环境（6–15）**：CONTRIBUTING、test-requirements、setup.py、test README 与15139逐字相同并核过；入口 `python -m mypy`（__main__.py:9–15、36–37）、pytest 数据测试清楚。无需下载新的业务资产、服务或进行 C 编译；typing_extensions 的源 stub 在仓库内。actor 实际环境仍未知，见下表。
7. **交付/评分（4/16–17/21–22/29–31）**：官方 test_patch 只新增 `.test` 文件，没有普通业务源码混入。baseline/prepared_task_face.py:185–211 对 base 存在的官方文件逐一恢复，对新文件跳过 checkout 后 apply；本题 diagnostics trusted_setup RESTORED=0、APPLY_RC=0、TEST_FILES=1，与新增文件吻合。gold 的 messages.py 出现在 projection included_paths，ignored=[]；合法源码方案无需写被恢复/保护路径。test_globs=()，不把旧 public_hints 的“所有测试都恢复”解释当实现；此题非测试修复不受该指令实质限制。未审全平台攻击面或真实镜像泄漏。
8. **关系/用途（5/29–30/37–40）**：在本题 base/messages.py:2519–2521已直接看到15139 gold 的小写 TypeType 分支，这是具体后续版本含前题修复的关系；二者目标分别为大小写一致性与 assert_type 同名消歧，不能合并成同题。该关系来自本包两题原件，不是 Git/history结论。建议以后划分训练/评测集合时留意修复进入其它 base 的交叉信息。本上下文已见答案，不能充当模型独立求解；不评价真实能力/成本。

## 原始评分证据与机制分账

所有日志为09-19历史 RH2 replay 复读，不是本轮 CPU/模型执行。

- **原 inputs/spec**：install_wave1/run_install_wave1.py:32–47 只 COPY wheel 和设离线 pip ENV；53–62 调 baseline 的 `/work/full216_20260919/code/rh2/scripts/replay_grade.py`，本题 R/status.json印证。recipe/materials/reference_bindings 未覆盖原 spec。A 中 `spec_vendor.py` 按 pinned JSON 取 python/mypy 1.4：Python3.11，安装 `python -m pip install -r test-requirements.txt; python -m pip install -e .; hash -r`，test_cmd `pytest -n0 -rA -k`。spec JSON SHA=`0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925` 已核。A 成员只用 extractfile 阅读。
- **镜像/离线准备**：R/image.json与plan本题entry的 pins为 setuptools72.1.0、wheel0.43.0、typing-extensions4.12.2、mypy-extensions1.0.0、tomli2.0.1、types-psutil6.0.0.20240621、types-setuptools74.0.0.20240830、types-typed-ast1.5.8.7、packaging24.1。derived=`sha256:38c3651c72ac2fe7ce40e3cf3e2a6056f8e983fe325d0fed771124e5827a829e`，base digest 与 public `affb…4835` 对应；构建context/wheel payload未在本地副本保存，目标机可用性未验。
- **安装确实执行**：gold `…d57f367c.eval.log`:379–443、noop `…0ecfe8ca.eval.log`:355–419 的全部安装段已读；test requirements satisfied、editable backend/build完成、成功卸载重装。RC仅反映最后hash命令，单靠它或 COPY 不足以证明安装。导入观测 `/testbed/mypy/__init__.py`；不能外推正式 actor 的 PATH或所有子模块。
- **实际运行**：gold log:457–477，noop:433–480，命令均 `pytest -n0 -rA -k 'testAssertTypeFail1 or testAssertTypeFail2 or testAssertTypeFail3'`。11322 collected、11319 deselected、3 selected。gold三节点全PASSED/RC0；noop前两FAILED、第三PASSED/RC1。两个失败都是 `array[int]`/`array` 无限定，非安装错误。
- **解析 vs 冻结参考**：A/spec_vendor.py:183–190 按 patch 所有 case 名拼命令，未按参考清单选 test；恰好该题 F2P2+P2P1与selected3一致。A/scoring.py:229–269对标记段调用 swegym_parsers.py:44–56（按PASSED/FAILED摘要提取节点），再对 Q/grading.json 的冻结集合评分。diagnostics parsed3/outside0/missing[]/skipped[]；ledger第1行 gold reward1/F2P2/2/P2P0失败，noop reward0/F2P0/2/P2P0失败。这是三层核对，未执行 parser。
- **字节身份**：两份 ledger/log 全文件 SHA 重算与 Q/run_refs一致；gold log=`e06184386f8ab460257827569e55ad82919eab83bbc6f9f9179db7e9bb4c9ac2`，noop=`7befac324497988833415f0e838d78bcde3170f24be37efd2d78d8c6434fc30e`。scripts_digest=`d5e85ab29feb4acc296eac3254cc9f2314e3c369316a531b25b7c88d00774091`；baseline四个inventory成员SHA已在本包核对。
- **角色/政策**：候选 apply agent/54321，grader rh2grader/54322，deny_all，2CPU/4GiB/PID512、tmp1GiB/shm64MiB，可写testbed conda prefix，qualification absent。原 ledger cleanup removed=true，runner_integrity_changed=false。这些不是正式actor验收；baseline/prepared_task_face.py:336–350正式rollout取public image，派生环境是否供CC模型使用没有原证据。

## 最小后续与未查范围

| 开发需要 | 公开入口/资产 | 已知/缺口 | 最小后续命令或观察 |
|---|---|---|---|
| mypy源代码生效 | __main__.py，CONTRIBUTING:39–44 | grader editable成功；actor PATH、UID/HOME/cwd、包来源未知 | actor记录环境身份及 `python -V`、mypy来源；用 `python -m mypy` 检查题面保存的小程序 |
| 原 SupportsIndex 示例 | 仓库typing/typing_extensions stubs，无运行时服务 | 两协议定义可静态定位，具体输出未跑 | 在固定grader诊断入口对base/gold核原例，预期保留失败但两个协议各有正确模块限定；保留实际返回码 |
| 旧 assert_type 回归 | check-expressions.test:931–990 | 评分仅一P2P，旧成功/泛型/unchecked测试未执行 | `pytest -n0 -k 'testAssertType and not testAssertTypeFail'`，观察成功返回/普通短名不回归 |
| 提交与测试资产 | tracked messages.py；fixture/stdlib stubs 已具备 | 不需改系统文件/expected，新增官方.test受可信setup保护 | 记录候选projection及解释器读取工作区源文件，不据包顶层导入推断全部 |

唯一优先下一步为上述 **原例＋窄旧assert_type回归的base/gold对照**，同时保留原评分结果作诊断背景。固定grader语义诊断无需先要求正式actor全验；如进入模型开发，另完成正式actor镜像消费、shell激活、离线依赖、工具、权限与资源验收。未来新run须创建独立重定位summary/manifest（原副本内仍是 `/work/...`），不回写历史prepared/ledger。

未查：所有类型形状、递归/同名TypeVar可区分性、真实CC交互/消息、当前目标机镜像身份与可用性、全仓回归、未来镜像/祖先历史答案可见性、模型性能与费用。未知均未填通过；本轮未改题/源码/tests/gold/reference/reward/expected或提交推送。

## 整包独立阶段结束前的关系补记

三题均已有初稿后、任何主审/旧结论暴露前，追加核对自己三题的精确源码：15184 base/messages.py:2519–2521已含15139 gold的lowercase分支；15139和15184各自base/meet.py:300–312均已将Any检查放在非strict optional的Union去None之后，即10174的关键修复结构已经存在。只说明后题base包含前题修复信息，不证明Git谱系/同问题重复，也不合并三种目标。此补记新增暴露范围仅为同包三题这些源码行；无其它题或history读取。三题gold文件hash均已重算，与validation/原ledger相符。
