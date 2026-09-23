# python__mypy-12417 — reviewer 独立初判（封存）

日期：2026-09-21。范围：static_review / development_diagnostic。本文件在读取任何本轮其他角色结论及质量历史之前写成；写成后不回写，后续分歧另记 review.md。本题与 16963 两份初判全部封存后才进入统一开放的第二阶段。

**初判：needs_review。原崩溃、gold 的局部防护、历史 F2P/P2P 对照均有直接证据；存在具体的合理替代解误拒疑点，建议先做一次 CPU 校准。** 隐藏测试除“不崩溃并报告未定义名字”外，还精确要求已知 object 主体变为 Any，以及未知捕获变量出现额外诊断。这些结果与 gold 一致，但不由题面唯一确定；可保留主体原类型的局部修复具有公开合理性。当前是静态疑点，未执行替代补丁，不直接宣布原题无效或已证实误拒。

## 暴露、执行与材料身份

- 我未参与两题主审；同一上下文读取 12417、16963 原始 public/private，未读任一题其他角色结论、质量历史。因同时审两版本，已知较新 16963 base 中存在本题 gold 同形 guard；这次交叉版本暴露明确记录，不声称仅凭本题 public 的盲审。
- 已读本题全部 user_prompt、public_bundle、base_identity、environment_brief；全部 test.patch、gold.patch、grading、validation、run_refs、source_refs、environment_record。environment_record 的 verified_environment_pair、reward 汇总和 analysis/history 路径已暴露，**未沿链接读取旧汇总**。
- 已读 reviewer 角色卡、共用环境卡、记录模板、协议及下文明确引用的源码/runner/fixture/旧测试。未读 public_read、analysis_before_history、old_findings_delta、card、screening_record、任何其他 review、质量 history、manifest、主计划或 method_adjustments。为定位构建脚本只列过 env_recipe_repair 中路径名，未读其他题 build.log。
- 仅做静态阅读、JSON/文本一致性与 SHA-256 元数据核对，及本文件写入。**本轮未运行 mypy、pytest、安装、Docker、SSH、模型或新实验。** 历史 09-19 日志不是本轮重跑。
- base 三份元数据一致：47b9f5e2f65d54d3187cbe0719f9619bf608a126，mypy 0.950；导出 tree 3e4b07470568ec645531cdc3ddd5e10abfcdd566，无 .git。题面 traceback 指向同一函数/断言。
- 当前核对 test.patch=grading.test_patch，gold.patch=validation.golden_patch；gold hash 为 4dc3dcbd7f5410bca0c9a02e543a32bbdb7dac0ba7c6c0f8933ca7101d618e7b，匹配 validation 与 gold ledger。两个日志各自哈希与 run_refs/ledger 一致。未重算整个导出 tree，不能把材料的 blob_bytes_verified 当独立逐 blob 验收。

## 公开目标、初态与合理路线

公开题面（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/user_prompt.txt`）只有一个核心目标：对未定义/拼错类名的 class pattern（o: object; case xyz(): pass），mypy 应正常产生错误诊断而不是 AssertionError。题面未要求吞掉 Name “xyz” is not defined，也没有指定主体/捕获变量错误恢复后的精确类型。

公开源码可定位完整原因：

1. MatchClass 解析（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/fastparse.py`）建立 class_ref、位置子模式和 keyword 子模式。
2. semantic class pattern（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/semanal.py`）先访问 class_ref，再分析捕获变量；NameExpr 查找（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/semanal.py`）找不到符号时不绑定 node，未定义名字诊断（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/semanal.py`）正常生成 name-defined 错误。
3. visit_match_stmt（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checker.py`）对每个 pattern 做两轮分析；visit_class_pattern（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checkpattern.py`）在处理任何位置/keyword 子模式之前断言 class_ref.node 非空，故错误恢复阶段崩溃。
4. 无需改 parser、类型声明或运行环境才能消除这个断言；可以在缺 node 分支返回保守 PatternType。正常 TypeInfo/TypeAlias 与已解析非法对象的路径应保留。

历史 noop 的具体堆栈证实该初态路径，而不只是 gold 差异：noop 失败原件（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/noop/eval_logs/evallog_replay-er19-iw1-python___3aeba4ff.eval.log`）先打印两条 Name “xyz” is not defined，再在 checkpattern.py:466 触发断言、SystemExit:2。

## Data-driven runner、fixture 与全部新增断言

完整新增 case（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/private/python__mypy-12417/test.patch`）为 testMatchInvalidClassPattern，一个 F2P。用两个未定义类模式分别覆盖位置捕获 y 和 keyword 捕获 x；没有原题空括号 xyz()。原题空括号进入同一前置 guard，静态预期受修复覆盖，但未在该参考集单独运行。

runner 的关键实现已逐版本核对，不借用 16963 版本：

- 收集条件（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/testcheck.py`）只有宿主 Python≥3.10 才加入 check-python310.test；DataFileCollector（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/data.py`）把每个 case 拆为 pytest item。
- 续行折叠（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/data.py`）把反斜杠后的 N 注释合回同一逻辑行；expand_errors（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/data.py`）产生行号/严重性/文案；setup（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/data.py`）在临时目录建立输入和替换 stub。
- run_case_once（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/testcheck.py`）执行 build.build，捕获 CompileError 而非把所有异常当成功；第 227 行比较完整输出。比较函数（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/helpers.py`）只做有限清理及 can't/cannot 归一化，不能随意省略诊断或 reveal_type。
- 选项（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/test/helpers.py`）默认 strict_optional=False、error_summary=False，check-python310.test 的目标版本固定 3.10。宿主解释器历史为 3.10.14。
- F2P 没有显式 fixture 段，使用 默认 builtins stub（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/test-data/unit/lib-stub/builtins.pyi`）（全文已读）；测试搜索路径（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/modulefinder.py`）加入 lib-stub。三个 P2P 使用 dataclasses builtins fixture（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/test-data/unit/fixtures/dataclasses.pyi`）（全文已读），同时抽查 typeshed dataclasses 的 match_args/field(init) 签名及 __match_args__ 生成（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/plugins/dataclasses.py`）。没有测试特有 Mock 或外部服务。

F2P 的七条期望输出及隐式约束全部对照如下：

| 需求/行为 | 输入与关键断言（test.patch 行） | 公开依据及判断 |
| --- | --- | --- |
| 位置捕获下未定义类被诊断，检查不中断 | xyz(y) → Name “xyz” is not defined（:12） | 直接支持题目；原题是同一 class_ref 失败但无捕获。 |
| 未定义类之后继续检查主体 | reveal_type(m) → Any（:13） | 继续检查合理；把已声明 object 精确变为 Any 是错误恢复策略，公开目标没有唯一指定。 |
| 位置捕获变量后续检查 | reveal_type(y) → Cannot determine type of “y” 和 Any（:14–15） | 公开旧 analyze_var_ref 支持未推断变量的该诊断；“必须不为 y 分配保守类型”仍非唯一正确恢复方案。 |
| keyword 捕获下未定义类也诊断 | xyz(z=x) → Name “xyz” is not defined（:18） | 核心 bug 的另一合法语法位置，直接相关。 |
| keyword 捕获变量后续检查 | reveal_type(x) → Cannot determine type of “x” 和 Any（:19–20） | 同上；精确要求第二组恢复输出。 |
| 无内部崩溃、无额外诊断 | 完整数组相等、case 到达结尾 | runner 与历史运行均支持；不是只凭 parser PASSED 字样推断执行。 |
| 题面 xyz() 原样 | 未直接出现 | 同一前置 guard 的静态泛化；应补一次公开复现，不能标原例已实跑。 |

“存在两个错误例”不表示测试只有负行为。此 F2P 同时保护错误后的正常分析继续、类型 reveal 和两种捕获路径；三个 P2P 再提供正常类模式与有意义的非法参数保护。

## 三个 P2P 与已读旧行为

参考列表（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/private/python__mypy-12417/grading.json`）选中的三个 P2P 全部读完：

| P2P | 公开旧 case | 保护的行为 |
| --- | --- | --- |
| testMatchClassPatternCaptureDataclass | :570–584（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/test-data/unit/check-python310.test`） | 正常 dataclass A(str,int) 的 A(i,j) 分别推断 i:str、j:int；防止不加条件地跳过所有 class pattern。 |
| testMatchClassPatternCaptureDataclassNoMatchArgs | :586–599（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/test-data/unit/check-python310.test`） | @dataclass(match_args=False) 不能位置捕获，必须报没有 __match_args__；正常非法行为仍被拒。 |
| testMatchClassPatternCaptureDataclassPartialMatchArgs | :601–616（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/test-data/unit/check-python310.test`） | field(init=False) 不计入 __match_args__；两个位置参数报 Too many，单参数 A(k) 仍推断 str。 |

这三个都走已绑定 TypeInfo；并不保护未定义类分支的主体类型保存、原例无捕获、OR/嵌套 pattern、guard、后续 case 或 match 后的类型恢复。

另外实际抽查 check-python310.test:468–513 普通/成员类的位置与 keyword 捕获、514–568 自匹配 builtins、670–820 泛型与 alias、主体缩窄、Union、继承、缺失属性。它们是公开可运行旧行为，**不在本题被选中的 P2P，也未由所读历史 -k 命令执行**。checkpattern.py:155–189 的 OR/value 路径、:459–592 的 class 检查和 :669–670 的 early_non_match，以及 checker.py:4109–4190 的两阶段分析/捕获传播已读；没有穷举全文件、所有嵌套模式和增量缓存。

## gold 与合理替代解的具体疑点

gold（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/private/python__mypy-12417/gold.patch`）只把缺 node 的 assert 改为 PatternType(Any from_error, Any from_error, {})，其他 TypeInfo/TypeAlias/Var 的分支不变。对公开空括号例和 F2P 的两个子模式都在前置 guard 返回，静态没有漏到任何一个参数形状；历史 gold F2P/P2P 全通过。没有其他源码改动/安装依赖才生效的迹象。

缺点与风险分开记录：

1. **具体误拒候选：保存原主体类型。** 同一 if type_info is None 分支可返回 PatternType(current_type, current_type, {})。未定义名字诊断仍来自 semantic analyzer；不会触发原断言；后续 body 仍检查；有类型的主体 m 仍是 object。由 body 缩窄逻辑（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/mypy/checker.py`）可推断它与 gold 的关键差异在 reveal_type(m)。它只改变此前必崩溃路径，三个已绑定 dataclass P2P 静态不受影响。公开“拼错名字不应崩溃”并不要求丢弃主体的 object 类型，但 F2P 精确要求 Any，故此替代解**静态预计会被拒**。未创建、未执行该候选；最终合理性还要核原例、后续模式、独立 body 错误，以及实际 RH2 得分，当前不宣称已经证实误拒。
2. **其他恢复方案也不唯一。** 将未知捕获变量显式赋 Any 以避免级联 Cannot determine type 错误，或沿现有 early_non_match 跳过无效分支，都可能是常见恢复路线。前者会减少 F2P 要求的两条错误；后者会省略全部 body reveal。后一种会跳过 body 的独立错误，不能不验证就算完整合理解；这里只优先验证第 1 项保存主体类型且继续检查的较窄方案。
3. **gold 未见正常已绑定类回归，但错误路径类型退化未覆盖。** 两个 Any 加空 captures 的设计会让主体/后续模式的分析更宽。题面没有规定诊断恢复精度，不能仅因 Any 判 gold 错；OR 子模式捕获、guard、后续 case 和 match 后已知变量类型需定点检查，当前未知。
4. **小覆盖限度不是自动缺陷。** 原例 xyz() 没直接测，但 guard 位于所有子模式处理前，有明确的源码泛化依据。现有 P2P 也包含正负约束，不能用“只有 4 个 case”或“只有三项 P2P”判测试无效。尚未证明存在违反核心“不崩溃”要求却通过全参考集的实际补丁。

## 历史执行证据与环境范围

逐题 image 配方（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/image.json`）：public digest 44be0de1…0d52 → derived image 854faf11…cca7，pins 仅 setuptools 72.1.0、wheel 0.43.0、packaging 24.1。不混用 16963 的 eight-pin/Python 3.12 配方。共同脚本 23–58（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py`）核 base ID、原 layers、把离线 wheel COPY 到 /opt/rh2/build-wheels 并设 PIP_NO_INDEX/PIP_FIND_LINKS，再显式把派生 image 传给 replay_grade。build 原件（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/build.log`）记录该 digest 与最终 image ID。

- noop ledger 第 1 行（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/noop/ledger.jsonl`）：rh2grader/54322，2 CPU/4 GiB，deny_all，允许写 /opt/miniconda3/envs/testbed；安装 rc=0，test rc=1，reward=0，F2P 0/1、P2P 3/3；runner integrity 未变。原始测试段（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/noop/eval_logs/evallog_replay-er19-iw1-python___3aeba4ff.eval.log`）选择 4 项、10300 deselected，F2P 命中原 assert，三个 P2P 通过。
- gold ledger 第 1 行（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/gold/ledger.jsonl`）：同一 image/profile，安装 rc=0，test rc=0，reward=1，F2P 1/1、P2P 3/3；import_path=/testbed/mypy/__init__.py，投影只有 mypy/checkpattern.py。安装与测试原件（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/gold/eval_logs/evallog_replay-er19-iw1-python___e26620f5.eval.log`）显示本题 0.950 editable 安装成功，Python 3.10.14、pytest 8.3.2、xdist 3.6.1；实际命令 -n0 -rA -k 'testMatchInvalidClassPattern or testMatchClassPatternCaptureDataclass'，4 passed。
- 环境里已有 typing_extensions 4.12.2、mypy_extensions 1.0.0、tomli 2.0.1 等，不是本轮复核安装。历史峰值 129/134 MiB、测试 3.620/3.735 秒只是冻结 grader 记录。
- **actor 未验**：以上 rh2grader/54322 的 conda 安装权、路径和离线 wheel 消费不自动属于 agent/54321；正式 public image、BASH_ENV/PATH、实际 Python≥3.10、源码生效、可写 cache/tmp、资源和当前 CLI 渲染均未捕获。verified_environment_pair 是材料中的评分配对标签。

| 开发需要 | 公开依据及已有证据 | 当前缺口/最小待验 |
| --- | --- | --- |
| 找到崩溃并编辑源文件 | 题面 traceback 直指 checkpattern.py；base 有完整调用链 | 静态入口明确；actor 工作区实际权限待验。 |
| Python 3.10+ 与当前源码导入 | match 语法；testcheck.py:107 收集门槛；CONTRIBUTING:32 editable 安装 | actor 中打印 Python/sys.executable/mypy.__file__，确认导入 /testbed；宿主不足 3.10 会导致相关测试不收集。 |
| 依赖/构建 | setup.py:77 默认纯 Python；pyproject 仅 setuptools/wheel；历史离线安装成功 | 不需强制 mypyc 或 C 编译；准备时固定可安装依赖即可，不能假定 actor 可写 conda 前缀。 |
| 资产/服务 | 复现只有 object/match；测试使用仓库 stubs、typeshed、dataclass plugin | 未见运行期公网/外部资产/服务需求；actor 能读源码与 stub 仍待验。 |
| 最小公开验证 | 单测说明（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417/base/CONTRIBUTING.md`），题面原例 | agent 上以 --python-version 3.10 --show-traceback 检查原例：正常 name-defined 诊断，无 INTERNAL ERROR；再 -n0 跑公开三个 dataclass case。 |
| 交付文件与写入 | 业务修复在 mypy/checkpattern.py；账本 projectable 且 included | 不需写不可提交的系统文件；临时复现/cache 不计交付。不能改 runner 来抹去崩溃。 |

## 八方面覆盖、边界与用途

| 方面 | 实际已核 | 限制/未知 |
| --- | --- | --- |
| 公开需求 | 全 issue/traceback、public hints、环境 brief；目标为正常错误恢复 | 主体必须 Any/捕获必须“不能确定”未见公开唯一约束；真实消息渲染未知。 |
| 材料与初始问题 | base/补丁/hash/日志对应；noop 命中相同断言 | 原题 xyz() 未在本轮或指定历史直接运行。 |
| 测试测量 | 新 F2P 七条输出、runner、fixture；P2P 三例全读 | 原例零参数、后续 case/OR/guard 未覆盖；不据少量 case 自动判坏。 |
| 合理解接受 | 给出保存主体 current_type 的具体替代路线及预计失配行 | 未执行替代解，误拒尚需 CPU 证据。 |
| 回归/gold | 局部 guard、相邻分支、两阶段 checker、dataclass plugin/旧测试已查 | 未证明错误后的类型恢复全面合理、未跑全仓或增量场景。 |
| 开发条件 | 逐题 pinned recipe、build/log/ledger、公开验证路径 | actor 解释器/安装权/派生配方消费待验。 |
| 交付评分 | test.patch 纯 .test 数据；gold 源码可投影；官方只恢复该 .test 文件 | 未独立重审全平台 parser/隔离与真实镜像可见答案资产。 |
| 关系与用途 | 16963 更晚 base 的 checkpattern.py:520–522 已含本题同形 guard；是版本继承线索，两题不是同一问题 | 无 Git 祖先链证明；已见私有答案，不是盲 solver；不推断模型成功率或学习价值。 |

官方恢复文件的原件为 test-data/unit/check-python310.test 恢复日志（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417/gold/eval_logs/evallog_replay-er19-iw1-python___e26620f5.eval.log`）。public hints“所有测试修改都会恢复”的笼统说法不能替代这个具体边界；本题正常业务修复无须修改测试，故暂未发现由该提示导致的修复阻塞。共享 parser/隔离审计引用共用环境卡的静态范围，不宣称本 reviewer 重新完成运行验收。

**唯一优先后续：** 在本题 pinned 配方下比较 base、gold、仅缺 node 分支返回 PatternType(current_type,current_type,{}) 的候选：运行公开 xyz()、F2P 两种带捕获模式（另加已知主体的 reveal 与独立 body 错误）、三个现有 P2P，并记录实际 RH2 分数。若候选保留公开目标、正常旧行为且只因 reveal(m) 不是 Any 而失分，即得到具体误拒证据；若出现语义或崩溃回归，收回该候选。所有此类实验尚未执行，actor 验证也另待共享入口；不标 ready_for_probe。

