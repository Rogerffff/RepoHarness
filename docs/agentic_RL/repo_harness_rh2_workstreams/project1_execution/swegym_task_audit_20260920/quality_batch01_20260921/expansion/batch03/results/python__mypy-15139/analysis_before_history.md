# python__mypy-15139 · 独立私有初稿（历史放行前封存）

封存时间：2026-09-20T21:20:57.441077+00:00。静态暂定：`needs_review / static_review`；用途仅 `development_diagnostic`。**官方一条 F2P 的真实分差成立，但 gold 没有修改题面明确展示的 reveal 输出路径，不能把 reward=1 解释为公开问题完整解决。** 优先做一次 base/gold 的原题 CLI 对照，连同原官方评分保存，而不是立即做模型探针。

## 身份、暴露和证据范围

权威 ROOT=`${REPO_ROOT}`。P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139`，Q=同根 `private/python__mypy-15139`；以下源码路径相对 `P/base`。已先读本题封存 `public_read.md`；base=`16b936c15b074db858729ed218248ef623070e03`，tree=`319db706885eb99e59f4b37054559d23d7561d3b`，沿用父协调者材料验收，不重做 blob 遍历。公开 bundle、grading 和 validation 的 base 一致；gold SHA256=`581a925ac3731600ced8561881f41bf083dd569b192dad1ce1f5370c88c9cfc5`。

已读私有 test/gold/validation/grading、environment_record、run_refs、source_refs。本题 environment_record 自带 `verified_environment_pair`、noop=0/gold=1 等结果摘要；这些已暴露，随后核了精确原账本和原日志，**本稿不是未见运行结果的盲审**。未读 history/refs、旧质量报告、B1/B2 结果、本批聚合、他题结果或 reviewer。未运行项目、导入项目模块、测试、安装、下载、联网、Docker/SSH 或模型。文档写入与 stdlib 文本读取/哈希不是行为验证。

运行证据简称：R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-15139`；G=R/gold，N=R/noop。两份 ledger 均第1行；GL=`G/eval_logs/evallog_replay-er19-iw1-python___bb2c55ae.eval.log`，NL=`N/eval_logs/evallog_replay-er19-iw1-python___d3434699.eval.log`；同前缀 `.diagnostics.json` 也已读。

## 1. 公开要求与双向映射

题面要求消除 type、builtins.type、Type 在错误和 note 中的混用，并明确允许“选一个别名统一”或“用代码中的别名”。它没有指定新增 API 或内部 helper。base 是 1.4.0+dev，题面所报 0.961 只是报告环境。`options.py:358-364` 的 Python≥3.9/force-uppercase 政策与 `check-lowercase.test:2-44` 是真实公开约定；大小写政策、全限定名消歧、来源别名保留不能混为一件事。

| 公开要求/旧行为 | 依据 | 实际测试/断言 | 覆盖结论 | 证据/后续 |
|---|---|---|---|---|
| 3.9 默认普通错误使用现代 type 拼法 | 题面；options.py:361-364；原 lowercase 测试的同类约定 | 唯一 F2P `mypy/test/testcheck.py::TypeCheckSuite::check-lowercase.test::testTypeLowercaseSettingOff`；`y=x` 要求 expression `type[type]`、variable `int` 的一条错误 | 覆盖这个输入，且不能以删错误/Any 混过 | NL:863-874 只差 Type/type；GL:879-884 通过 |
| 题面 reveal_type(x) 的 note 与错误保持命名一致 | user_prompt:6-21；messages.py:1630-1632 → types.py:3188-3189 | 新测试没有 reveal；没有其它 F2P/P2P | **缺失，gold 未改此分支** | 静态可见仍固定 `Type[...]`；原题 CLI 待验 |
| 题面 `reveal_type(type[type])` 不可索引错误及 Any note | user_prompt:9-10；messages.py:410-424 | F2P 只有赋值，未含表达式索引 | 部分：共用 format_type 的错误可受修复；原例整体未执行 | 不把对共用 helper 的推断写成完整复現 |
| Python<3.9、force-uppercase=True 的旧显示；参数和 class constructor 显示 | options.py:361-364；messages.py:2521-2526；check-generics:503-505；check-classes:3989-4019 | 无 P2P；现有公开 runner 会对非 lowercase 测试强制大写 | 缺少评分保护；gold 的条件分支静态保留它们 | 不以零 P2P 判坏题；应按修改范围跑公开回归 |
| 同名类型应能区分；类型参数含义不变 | messages.py:2409-2415,2583-2601,2637-2660；types.py:2747-2759 | 一个固定 int/type 赋值不能覆盖嵌套/同名/泛型 | 未覆盖但有公开回归依据 | gold 保留递归 format 与 fullnames 参数；未实测全部调用者 |
| 合理别名路线可以接受 | 题面明确 OR；typeanal.py:549-570 会归约到 TypeType | F2P 精确要求 `type[type]`，但不限定代码形态/helper/调用顺序 | 小写有公开选项政策支持；其它规范化或来源保留路线可能有规格争议 | **未证实误拒**；不能以不同于 gold 直接拒绝 |

## 2. 初态与完整新增测试/helper

test.patch 仅向 `test-data/unit/check-lowercase.test` 增加一个 case，七行：`--python-version 3.9 --no-force-uppercase-builtins`，`x: type[type]`、`y: int`、空行、`y=x` 的 E 注释。名称虽然叫 SettingOff，实际 flags 明确关闭强制大写；不能按名称反推执行语义。没有新增/修改 helper、Mock 或 fixture；不含普通业务源码。

解析链已展开：`mypy/test/data.py:52-107,210-229,438-480,518-544` 解析 case 和 E 注释，生成 `main:5: error: ...`；`helpers.py:358-390` 从 flags 建 Options 并隐藏 error code；`testcheck.py:93-155` 使用真实 `build.build`，`use_builtins_fixtures=True`，且文件名 lowercase 避开强制大写覆盖；`:162-184` 比较全部输出；`helpers.py:46-58,118` 除 can't/cannot 归一及 cleanup 外比较字符串数组，不是检查字符串存在。fixture 路径由 `modulefinder.py:793-801` 指向 `test-data/unit/lib-stub`；已读 `builtins.pyi:7-19` 的 object/type/int 定义。新 case 无自定义 builtins 段、网络、随机数或时间依赖。日志是真实一次构建产生的差异，非零解析或安装失败伪造。

原始 NL:847-878：`pytest -n0 -rA -k testTypeLowercaseSettingOff`，收集 11308、选中1、实际失败1，期望 `type[type]`、实际 `Type[type]`；测试 rc1。GL:866-884 同命令选中1、通过1、rc0。两个 ledger 第1行与 diagnostics：解析键各1，冻结参考 F2P=1/P2P=0，reference_missing/skipped 均空，段外解析0，reward 分别0/1。**11308是收集数，1是执行节点/解析键/参考数在本题恰好相等；不把三个概念合并。**

## 3. 合理替代与可能漏测

合理替代：保留公开版本政策，将 type 命名选择抽为共享显示规则，再由错误 formatter 与 TypeStrVisitor 各自保留既有短名/fullname 策略；也可独立修改两处。这与 gold 的单点实现不同，无 helper 形状断言妨碍。来源别名路线更复杂，因为 TypeType 只有 item、原别名在 typeanal 归约时消失，但题面允许它；没有原型实验，不声称已构造可接受而被拒的完整补丁。

不完整解有具体依据：gold 本身只改 `messages.py:2519-2520`；`types.py:3188-3189` 的 `Type[...]` 留存，所以题面两个输出入口仍可能分别显示 Type/type。另一个窄风险是把错误 formatter 无条件改小写：唯一 F2P 也只能看到小写配置，不能区分其对 Python<3.9/force-uppercase 的破坏。这里只记录静态漏测推断，未写/运行这些候选，不夸大为新 RH2 反例。

## 4. 回归调用者与 gold 完整性

gold 一处两行，依据 options.use_lowercase_names() 在 type/Type 间选名；没有依赖、API、类型检查语义或无关文件变更。赋值路径被真实官方测试证明修到，嵌套 TypeType 与 class constructor 经 `format_type_inner` 递归应共享选项（messages.py:2365-2366,2519-2526）。但原例的 reveal 路径独立，**不能将此 gold 称为完整统一显示**。固定 `unsupported_type_type` 文案（messages.py:1646-1649）也仍为 Type，但“everywhere”是否包括该诊断是范围疑义，不把它自动升格为原例已证回归。

零 P2P 后主动追了：普通索引错误、reveal_type/reveal_locals、格式化消歧、FunctionLike→TypeType；公开旧 `check-lowercase` 全部8 case，`check-generics::testTypeApplicationCrash`，`check-classes::testTypeTypeOverlapsWithObjectAndType/testTypeConstructorReturnsTypeType/testObfuscatedTypeConstructorReturnsTypeType`，`check-generic-alias::testGenericAliasBuiltinsReveal`。这些文本支撑回归范围，但均未执行且不在冻结 P2P，不能说回归已过。未穷举 attrs 插件等全部 format_type_bare 调用者，也未审全仓类型语义。公开旧 Type 快照许多是 runner 强制大写所致，不构成现代默认 reveal 必须继续大写的证据。

## 5. agent 开发条件

| 必要操作/资产 | 公开依据 | 已有证据适用范围 | 缺口与建议（全未执行） |
|---|---|---|---|
| 定位源码并运行原题 | user_prompt；messages.py/types.py；CONTRIBUTING:73-95 | 公开 base 可定位；静态 public_hints 声称已激活环境 | 实际 actor 消息、PATH、Python、工具版本未知；用 agent shell 打印解释器/模块来源后执行公开三行案例 |
| 运行依赖、typeshed、pytest fixture | setup.py:223-236；testcheck/modulefinder；包内存根 | 原 grader 在 conda Python3.11.9、deny_all 下安装、导入和测试成功；`RH2_OBS_IMPORT_PATH=/testbed/mypy/__init__.py` | 只证明 grader；actor 是否消费该派生镜像、是否有.so遮蔽及相同资产未验 |
| 离线安装/源码生效 | CONTRIBUTING:39-44；image.json | 派生镜像只 COPY wheels 并设 PIP_NO_INDEX/PIP_FIND_LINKS；原 spec 仍跑 `pip install -r test-requirements.txt` 与 `pip install -e .`。NL:769,809-837、GL:788,828-856 真正安装成功 | COPY 本身不等于安装通过；本地原 wheel payload/context 未保存，镜像目标机存在性未验；新运行需另准备 |
| 临时写入、身份及资源 | runner 临时文件与 cache_dir；环境卡 | grader=rh2grader/54322、prefix可写、2CPU/4GiB、tmp1GiB；patch apply=agent/54321；ledger 峰值约136/141MiB | 正式 actor=agent 不等同 patch apply 用户或 grader；实际激活、HOME/tmp权限、资源与清理仅一次评分条件，不证明并发稳定 |
| 外部服务/编译/交付 | 本题为本地诊断字符串；gold 仅.py源码 | 窄测不需 GPU、在线服务或新增依赖；原离线安装使用原 spec | 无据要求运行期公网或C编译；必要时离线 editable 安装，合法修复可在 messages.py/types.py 交付 |

## 6. 交付和评分边界

静态读取既存 `runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz` 相关成员文本，未解包/导入/执行：`src/repoharness2/envpack/spec_vendor.py` SHA256=`8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`（:183-197 mypy case名生成-k）；`adapters/slime/prepared_task_face.py` SHA256=`3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`（:185-211恢复、:305-330 test_files与test_globs空）；`adapters/slime/replay_grade.py` SHA256=`b8f1fbe2f37032e52b496f2eb9296c8a647a3072af2b7def600809544c9999fb`（相关导入/投影及执行段匹配行）；`envpack/scoring.py` SHA256=`b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`（:189-270参考清单评分）；`envpack/swegym_parsers.py` SHA256=`995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`（:88映射 pytest parser）。路径均在 `src/repoharness2/` 下；没有用当前 ROOT/rh2 冒充历史代码。

本题 official 恢复路径**仅** `test-data/unit/check-lowercase.test`，来自 test.patch 的精确触碰路径；NL:595/GL:614 checkout 与 diagnostics trusted_setup restored=1/apply_rc=0/expected=1 对应。gold projection included=`mypy/messages.py`、ignored=[]；合法替代涉及 types.py 也不在 official 路径。test_globs=()，不能把所有 test 名称文件说成自动排除；`public_hints` 的“所有测试均恢复”不是实际机制完整描述。test.patch 不混入源码，无具体新增排除建议，additional_exclusions=[]。既存 runner/helpers/config 是评分控制面，但本次没有验证伪造成功路线，不凭理论可能性加排除。缺实际 actor 可见资产/Git/安装缓存泄漏验收。

## 7. 题目关系与用途

仅记录本题精确 base、补丁和显示范围；未读他题，不能按同仓或文件自动聚类。题面给症状和两种政策，未给完整修复。公开包无.git 不等于真实镜像无未来对象/答案；未访问网络答案，也无当前模型成功率/成本证据。审查上下文已见 gold、隐藏测试和评分结果，未来 solver 不得消费四件审查产物。当前不批准正式训练/评测或 ready_for_probe。

## 8. 暂定问题和唯一优先下一步

1. **覆盖与 gold 完整性（静态强证据，需行为确认）**：原例 reveal 输出独立且未修，隐藏测试只有赋值错误。影响：奖励只能说明窄格式化分支修复，不能说明公开一致性目标。保留为待审问题；若 CPU 对照确认，补有公开依据的原例验收并修 gold/明确任务版本，不能默默缩窄原题。
2. **规格多路线与精确输出（未证实误拒）**：测试选择小写有版本政策支持，但题面 OR/全限定名范围仍不唯一。修订验收时需接受合理实现，不强制内部代码形态；目前不要把“非 gold”当错。
3. **评分侧已恢复、actor 未验证**：历史安装失败泛化不成立；原角色/配方已成功，但正式 actor 条件仍未知。

唯一优先 CPU 实验（仅建议）：在经身份/导入来源验明的 base 与 gold 两个干净环境，用目标 Python3.10 对原题 `x: type[type]; reveal_type(x); reveal_type(type[type])` 做 CLI 检查，保存完整 stdout/rc；同条件保留该官方单 case 得分。预期区分“错误与note统一”与“官方通过但note仍为Type”。这不是运行被检查程序；有类型错误的 CLI 非零不自动算环境坏。若成立，再为默认/强制大写/旧版本、reveal与普通错误设计有限验收修订。未执行，成本未知。

尚未查：history（等待协调者放行）、独立 reviewer、真实 actor、当前 CPU 原例/替代解、全部调用者回归、重复稳定性/并发、实际 Git与可见资产、外部解答可达性、独立来源runner对账、真实模型轨迹和成本。历史前初稿保存后不回写。
