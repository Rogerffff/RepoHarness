# python__mypy-11236：无历史私有审查初稿

2026-09-21；B2 private investigator。**needs_review / static_review；intended_use=development_diagnostic；additional_exclusions=[]；未知cost=null。** 本稿保存前未打开本题history、旧调查或environment_record.json。只作静态原件/源码阅读、必要JSON与hash/文本比较；没有运行项目代码、测试、安装、网络、Docker/SSH或付费模型，没有修改源码、原测试、gold、reward或共享镜像。

所有路径相对权威 ROOT=.。U=`runs/swegym_quality_batch02_20260921_v2/public/python__mypy-11236`；P=对应private/python__mypy-11236；`base/`指U/base。W=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11236`；G=W/gold，N=W/noop；Glog=`G/eval_logs/evallog_replay-er19-iw1-python___74f1c394.eval.log`，Nlog=`N/eval_logs/evallog_replay-er19-iw1-python___32643f4f.eval.log`。Ga/Na为两侧 `artifacts/swe_gym_lite--python__mypy-11236/a1-c1f6bc21`、`a1-3d8f796c`。已读本题封存public_read.md，其提出的上下文推断路线与本稿gold路线独立区分；未把公开读者读过的所有文件算成本主审已读。

## 1. 公开目标、保持项与可解性

U/user_prompt.txt:14–21给出显式标注 `Union[Tuple[str], Tuple[Literal[1]]]` 的函数，分别返回`("a",)`和`(1,)`；后者错误地被报告为Tuple[int]不兼容。标题“Cannot infer return type”不是要求推断未标注函数签名，实际是返回表达式推断和兼容性判断。期望栏虽空，错误说明与合法注解足以推出应接受这两个分支；无需补答案型规格。题面代码有导入和future annotations，可直接组织成CLI输入。Python目标版本3.7、strict、strict-optional、warn_return_any来自题面:27；宿主Python版本与目标版本须分开。

| 公开行为/合理旧行为 | 公开根据 | 新测试映射与边界 |
|---|---|---|
| 正确单元素整数Literal元组与普通str元组均可作所示Union返回 | 题面原例；subtypes.py:114–143联合按完整分支检查 | 唯一F2P用布尔标签的双元素Union和Final单元素元组覆盖同类机制，没有原样覆盖题面str/int单元素Union或其CLI flags |
| Literal按具体值和类型约束，不能把2或True当Literal[1] | literal_types.rst:6–9；LiteralType.__eq__同时比较fallback与value（types.py:1628–1630） | F2P分别拒绝Final(2,)和Final(True,)，直接保护两种错误 |
| 元组分支关联、长度及普通未知bool约束保持 | 完整Union任一分支语义；subtypes.py:350–355长度/逐项规则；旧tuple长度测试 | F2P拒绝(False,5)/(True,'oops')交叉搭配及bool()未知标签；没有长度错误样例 |
| 推断型Final可以保留原字面值，普通未标注变量仍推为一般类型 | literal_types.rst:93–142；types.py:809–833；checker.py:2227–2231 | F2P接受Final(1,)和显式Tuple[Literal[1]]；没保护普通赋值清除last_known_value的行为 |
| 已有函数实参、直接Literal/元组上下文、泛型容器/变长元组/星号展开保持 | 相关公开旧case及共享子类型调用路径，详§5 | P2P=0；有目的地静态读取，未执行。不能据没有P2P判坏题，也不能称已保持所有回归 |

基本因果链可在公开源码定位：checker.py:3313–3334将声明返回类型传给表达式推断；checkexpr.py:3306–3315遇到多个同长度tuple上下文时不选择其中一项，3350–3355无位置上下文推断元素。infer_literal_expr_type:2088–2114在普通上下文产生带last_known_value的Instance，Literal上下文才产生真正LiteralType。原SubtypeVisitor.visit_instance:243–297对右侧LiteralType没有承认已知值的分支，最终False；visit_tuple_type逐项调用它，造成误拒。Gold可利用已经保存的值修子类型判断，不必强迫所有候选实现改变元组推断器。

公开文档、源码、现有测试足够调查。没有必需外部附件、服务或祖先历史。原public_hints是通用操作指示，包含只改NON-TEST、窄测及conda已激活等；实际actor消息尚未捕获。其“所有测试修改恢复、永不计分”文字不能代替当前精确恢复机制。合法修复位于subtypes.py/checkexpr.py等源码，可用CLI字符串与既有测试验证，无需为了本题违反不改测试指示。

## 2. 材料与运行条件对应

U/base_identity指定base `209a7193feb4bbfa38d09232b0a5a916e9d2e605`、tree `b032d831a01ba53aea221e5a9355e218dca0a77e`，声明1722个blob、无导出Git/symlink/LFS缺件/gitlink。P/source_refs把三个包定位到S2/ingest public_bundles_v0、grading_bundles_v2_v0、validation_bundles_v0的第187行。协调层已完成整包源行、blob/mode、日志引用身份核验；遵照新增节奏，本主审不重复逐blob或整包校验，只核本题base/patch/运行与语义。没有将“声明/协调层核验”冒称本主审独立读完1722个文件。

本题grading版本0.920、Python3.9、eval_cmd=`pytest -n0 -rA -k`，F2P仅 `mypy/test/testcheck.py::TypeCheckSuite::testLiteralAndInstanceSubtyping`，P2P=[]。Gold SHA256=`96d1a2e3a08c9f52d7a7ce94fa2de15ee638beba3817cc14394b9426d3f17dc1`，与Ga/candidate.patch及ledger候选摘要相符；Ga frozen只含mypy/subtypes.py。只解码该文件作精确文本比较，确认是公开base加gold两行，无其它算法改动。Na frozen entries=[]。两侧stage HEAD等于base、classification=projectable、stage_error=null，baseline_manifest_digest同为 `fd0214a7ee032c21366f570d277c79bebf004f64a6265e06a7e13856656b6ef7`，public_bundle_digest同为 `6b4766513389eb70737240fc4c9d78b15f75ab1bd712680478e9ea58480c19d9`。

初态不是简单“git完全干净”：Glog:272–294、Nlog:271–280相对base的diff均有test-requirements.txt新增 `types-typing-extensions==3.7.3`；gold另有预期subtypes两行。该依赖pin是既存运行初态，本轮没添加，也不是候选投影。日志前面的git show展示base提交自身的checkstrformat等diff，不是当前未提交污染；已经按命令边界区别。未删初态文件、未擅自reset。这对比证明的是带此既存依赖条件的本题源码对照，不宣称纯base任意环境已验证。

原G/N使用同一派生image `sha256:853ffff2219f5167a87f7f310b17b8362d098f66745c20d0406c44c2c708edd0`，recipe=`install-wave1:python__mypy-11236`，scripts_digest=`3877bc8ad683910926b4ab2a8144a30986cd6a88d16cabb6676f852b36697c18`。P/run_refs精确给Glog/Nlog，日志引用SHA分别b3c642eaa547d3305fdbd1c430ac75b056dc7e79e31dbd5035b911b98d56c2d2、66b83257ad1498dc45040afb402d02d3f6248a6c8981e1c6d8bcd3ee15b187ba；身份由协调层核验，本审实际读相应原日志关键段。

| 历史真实RH2对照，均attempt1 | 安装/测试原事实 | 冻结评分与限制 |
|---|---|---|
| G/ledger.jsonl:1 | install6.212s，test3.951s/rc0；editable build isolation与wheel安装成功；Glog:560–579显示1 passed/9845 deselected | F2P1/1，P2P0/0，reward1；1解析、无missing/skipped/outside，无全局失败；不是9846项全部通过 |
| N/ledger.jsonl:1 | install6.7s，test4.266s/rc1；Nlog:564–580显示合法bool元组两分支及Final(1,)多出错误，随后1 failed | F2P0/1，P2P0/0，reward0；真实断言差异、不是空补丁早退/安装失败/零解析 |

两侧观察从/testbed/mypy/__init__.py导入，runner digest前后相同、cleanup removed=true、stage_error=null；pkg_version观测为“?”，不能据此填成一次独立版本验证。editable产物名与stage HEAD提供该次代码版本对应。每个候选仅一条原执行证据，不宣称复测稳定或真实actor成功。

## 3. 所有新增/修改断言与F2P语义

**新增case** `testLiteralAndInstanceSubtyping` 位于P/test.patch:23–66。一个pytest node包含多个独立语义点；完整预期为一条reveal note和六条error，另有四个合法return位置不得产生额外错误。具体如下。

| patch行/函数 | 断言或隐式成功要求 | 防止的错误与范围 |
|---|---|---|
| 31–35，f的两return | `(True,5)`及`(False,'oops')`均符合标签关联的Union，输出不得加错误 | 同原例“联合元组中的Literal不能被普通Instance丢失”机制；是bool双元素形状而非原样int单元素原例 |
| 37，reveal_type(f()) | 精确显示声明的 `Union[Tuple[Literal[True],builtins.int],Tuple[Literal[False],builtins.str]]` | 检查调用的公开类型表示；f已有返回注解，单凭此note不证明自动推断了函数签名或每一return正确，须结合额外错误检查 |
| 39–41，does_work | 推断型Final `x=(1,)`可返回Tuple[Literal[1]]，无错误 | 覆盖带last_known_value实例经Final元组传递；Nlog:575的main:18确为这个额外误报 |
| 43–45，also_works | 显式Tuple[Literal[1]]变量可正常返回，无错误 | 保留已经是Literal的正常行为；no-op日志未在此位置报错 |
| 47–49，invalid_literal_value | Final(2,)须有“got Tuple[int], expected Tuple[Literal[1]]” | 不能只看fallback为int就接受任意值 |
| 51–53，invalid_literal_type | Final(True,)须有“got Tuple[bool], expected Tuple[Literal[1]]” | 不能只用Python值相等，因为True==1；fallback类型也必须相符 |
| 55–59，incorrect_return1两分支 | (False,5)、(True,'oops')分别报错，got显示Tuple[bool,int]/Tuple[bool,str] | 保留整条Union分支关联；不能把各位置分别合成宽联合后无条件接受 |
| 61–65，incorrect_return2两分支 | (bool(),5)、(bool(),'oops')各报错，got同上 | 一般bool不能因为可取True/False就满足固定标签；类型检查不执行bool()，也不要求运行期常量折叠 |

Fixture为已有 `fixtures/bool.pyi`（patch:66），定义bool(int)、tuple、str等；lib-stub/typing_extensions.pyi:17/20已有Final/Literal。不需要新增fixture。测试通过data.py:69–75读取stub、267–277创建临时目录，testcheck.py:161–181配置非incremental数据测试，再194–224调用真实build.build并比较完整diagnostics。没有mock、内部helper名或调用次数断言。打印出的失败diff以“...”截短部分尾部，这是原测试helper的展示，不代表源断言只有显示的前五条；六error来自完整patch、完整列表由源码比较。

**修改旧case** `testLiteralFinalGoesOnlyOneLevelDown`（base/check-literal.test:2677–2696），对应patch:4–17，不能遗漏：保留a/b已有两条reveal（Literal[1]?及Tuple[Literal[1]?,Literal[2]?]）；移除known-broken TODO和issue7399链接；将`force1(reveal_type(a))`的额外Literal[1] note换成`force1(a)`无错误；将`force2(reveal_type(b))`原不兼容error及reveal note换成`force2(b)`无错误。它不只是删除错误行，还移除了reveal调用形式和相应观察。checkexpr.py:3093–3104显示reveal本来会带当前上下文访问并返回其真实类型。本次不得把删去的旧期望当新增回归“应继续失败”的规范，也不能无运行就证明替换后的两项都已通过。

**三种范围严格分开：** vendor从test.patch可见的`[case ...]`抽选择器；修改旧case的hunk没有携带其case header，所以Glog:560、Nlog:546真实命令仅 `pytest -n0 -rA -k testLiteralAndInstanceSubtyping`。9846 collected中只有1 selected。冻结F2P也是该1项、P2P空；旧修改case既没执行也没被冻结引用。主审实际还读过old Final case和下述旧回归/调用者，不等于这些行为已被奖励保护。

## 4. 合理解法与具体可区分疑点

Gold在一般Instance→Literal子类型判断中利用last_known_value，是最小而自然的路线。另一个合理路线是在固定TupleType逐元素比较中，仅当目标是Literal时使用元素的已知Literal，继续保持相同长度、完整分支与fallback检查；这与gold修改层次不同，却可保留相同诊断输出。还可像公开读者提出的那样，在多候选tuple上下文中建立位置级推断上下文或逐分支受控尝试，最后仍做完整Union兼容性检查；Final既有值需要一并处理，不能只修立即返回表达式就宣称覆盖整个F2P。

有直接证据的两项待验问题如下，不强制把每项可能性升级为已证缺陷。

1. **漏掉长度检查的tuple局部部分实现。** 一个具体候选是在visit_tuple_type的TupleType分支中用 `all(self._is_subtype(as_known_literal(l, r), r) for l, r in zip(left.items, right.items))`提前返回，其中as_known_literal仅在右侧Literal且左侧有last_known_value时使用该值，却遗漏原350–355的长度检查与后续fallback约束。当前F2P所有对应元组长度相同，六个值/类型/分支负例仍可正常拒绝，静态上可能获得1；但是题面原Union下`return (1,999)`会被zip忽略尾项而误接收。错误长度拒绝有原subtypes规则和check-tuples旧例支持，不是审查者新增业务要求。候选未写入、未评分，故只记unknown的具体假设；最小CPU对照要同时记录冻结F2P与该独立长度负例，不能用静态预测宣布false positive。
2. **上下文推断路线的诊断文本可能被误拒。** 若合理实现为多个同长候选提供位置级 `Union[Literal[True],Literal[False]]` 上下文并仍保留完整联合检查，checkexpr.py:2106–2114会推真正LiteralType。于是incorrect_return1仍正确拒绝交叉搭配，但messages.py:1682–1708可能把got打印为Tuple[Literal[False],int]等，而F2P要求Tuple[bool,int]。公开issue没有要求该更宽的got字面形式；已有直接Literal上下文也会打印Literal，见旧case:1458/1520。这是具体可解释的精确文案约束风险，不等于已经找到完整正确而被拒的补丁；尚需含Final、分支关联和旧行为的完整替代解验证。不能仅凭推测放宽oracle，也不能说测试只能接受gold。

相反，很多简单假修复会被此单F2P排除：无条件接受Instance/Literal、只比值不比fallback、独立合并元组每位置后直接接受、把所有bool当固定标签、吞掉全部return错误，都会撞上现有六条负例。因此P2P空或“只有一个F2P”不自动意味着奖励只测一件事。尚未发现已执行的错误实现满分或正确实现误拒证据。

## 5. Gold与相关旧回归/调用者

Gold仅两行（P/gold.patch:8–9）：右侧为LiteralType且left.last_known_value非None时，递归调用原 `_is_subtype(known_value,right)`。其self._is_subtype:204–209保留原比较选项；visit_literal_type:397–401比较真正Literal或退回fallback；LiteralType.__eq__:1628–1630同时比较fallback和值，故不会因True==1错放类型。它不改变元组长度/Union分支规则，不直接重写错误文本、正常推断类型或变量赋值。静态上题面(1,)在第二Union分支可使用已知1匹配，而("a",)仍匹配str分支；这支持公开目标，但本轮没有题面CLI原样执行证明。

已读Instance注释、checker:2147–2151/2227–2231和erasetype:134–151：普通赋值清除last_known_value，推断型Final保留。这解释为什么修复不应扩大成“普通变量永远保留Literal”；Gold没有改这条边界。一般is_subtype是共享入口，函数实参checkexpr:1527–1539与返回checker:3363–3371都用它；影响不限于本测试或return语句。未穷举所有generic/overload/protocol/enum/增量调用者。

| 静态读到的旧case/接口 | 所保护的合理行为 | 本轮执行/奖励范围 |
|---|---|---|
| check-literal.test:1448–1467，testLiteralInferredInReturnContext | 直接返回1可匹配Literal[1]，2与Literal[2]不能；普通int仍合法 | 未执行、非P2P |
| :1512–1526，testLiteralInferredInTupleContext | 显式位置Literal、嵌套tuple、交换值拒绝；无上下文d=(1,2)仍reveal Tuple[int,int] | 未执行、非P2P；直接监督不可过度收窄普通变量 |
| :2677–2696，testLiteralFinalGoesOnlyOneLevelDown | 原来记录Final tuple限制，官方patch把force2改为合法 | 被修改但未被选择；应跑官方修订后case，不能把旧known-broken错误期望保持当硬回归规范 |
| :2698–2726，testLiteralFinalCollectionPropagation | implicit list的元素不自动保留可替换Literal；显式List[Literal]接受；相应正负实参/reveal | 未执行、非P2P；读过不代表一般容器边界已验证 |
| check-tuples.test:1207–1233 | 元组过长/过短拒绝；已有单个tuple候选Union与变长Tuple上下文合法 | 未执行、非P2P；直接支撑§4长度负例，及替代推断器方案的回归范围 |
| :978–1003，testTupleWithStarExpr1–4 | tuple/list星号展开、join类型和赋值保持 | 未执行、非P2P；gold未改推断器，若替代实现改checkexpr则应按影响纳入窄回归 |

目前没有未交付源码依赖证据；派生环境成功交付该两行，F2P完整通过。Gold不是免审参考：通用Instance/Literal比较的更广语义、题面strict/Python3.7目标和未执行修改旧case仍待验证。没有因为源码短或一个分数1就给“完整正确”结论。

## 6. 开发依赖、身份、资源与环境层次

W/image.json/build.log核对本题依赖修订：FROM固定public manifest `6b6a59ea714d1d4e1bf5c09d2e576aed035532099c8634a750ab738e33d9cc9e`；base ID `d64f775bd6258407d6fe847af333afd1f8666c69f38751eef7d6b2b4eb34aa37`；只COPY轮子并设置PIP_NO_INDEX/PIP_FIND_LINKS。pins为setuptools75.1.0、wheel0.44.0、packaging24.1，结果image如§2。通用run_install_wave1.py:24–62此前按授权读过，只复用构建机制知识，不复用别题合格结论；本题参数和原日志独立读取。build.log的ARG默认值警告不等于构建失败，实际FROM参数及输出image均有记录。

Glog:472–555、Nlog:458–541提供requirements已满足、editable isolation完成、wheel构建/安装成功及pytest工具已满足的原始行；不以分号安装末尾hash -r的rc0单独判断。环境有runtime typing_extensions4.12.2、mypy_extensions0.4.4、tomli1.1.0、typed_ast1.4.3；types-typing-extensions3.7.3是另一项stub pin，不混为runtime版本。Python3.9.19/pytest6.2.5/xdist1.34.0见测试头；题面目标Python3.7不要求把宿主降为3.7。fastparse.py:48–82在宿主>=3.8可使用内置ast；测试依赖仍列typed_ast。setup.py:77–85默认不开mypyC，193–200给兼容依赖与Python>=3.6；本题纯Python语义修复没有独立GPU、外部服务或C编译前提。

| 必要开发动作/资产 | 已知支持 | 正式actor仍待核的事实 |
|---|---|---|
| 加载基线与CLI复现 | 公开源码/类型stub齐全；grader导入/testbed/mypy/__init__.py、editable真实成功 | agent/54321的sys.executable、PATH、subtypes/checkexpr实际加载路径及编译模块遮蔽未知；仅导入__init__不穷尽这些问题 |
| 本地窄测试 | pytest.ini:22默认-nauto；官方命令显式-n0；data.py临时目录；bool/tuple fixtures与Final/Literal stub已读 | actor是否有兼容pytest/xdist、临时目录写权限、工作区/home容量须实际验证 |
| 安装（若必须） | derived grader已有离线wheel，conda prefix允许写入且实际成功 | formal public image是否有相同wheel、prefix权限或其它可用依赖未知，不能假定公网pip成功 |
| 资源/网络 | 原grader2CPU/4GiB/PID512、shm64MiB、tmp1GiB、deny_all；单case峰值122.664/130.535MiB，无原件中的OOM/超时失败 | 不代表整文件/并发/真实actor稳定；actor计划tmp1GiB/home256MiB等不等于实测 |

两侧candidate.apply_user写agent/54321只说明脚本应用补丁阶段；实际评分policy明确rh2grader/54322，conda prefix owner也是54322。正式rollout_spec_from_view仍取U/public_bundle的public.image `xingyaoww/sweb.eval.x86_64.python_s_mypy-11236:latest`及其manifest，并使用actor身份；不能用这对派生grader账本认证真实actor开发条件。env_qualification或实际actor资格未在本轮证据中成立。

建议但未执行：先在正式actor的/testbed用`id`和`python -c 'import sys,mypy.subtypes,mypy.checkexpr; print(sys.executable); print(mypy.subtypes.__file__); print(mypy.checkexpr.__file__)'`核身份与源码；再按公开reader B的 `python -m mypy --python-version 3.7 --strict --strict-optional --warn-return-any --no-incremental --cache-dir=/dev/null -c ...`跑原题两分支，C跑非法(2,)；另用同一目标Union的(1,999)作长度负例。窄回归选择上表直接相关case，官方修改旧case应使用官方test.patch后的版本；所有命令和预期均是后续统一CPU负责人建议，本轮没有执行。

## 7. 恢复、投影、评分、泄漏与控制面

当前RH2 prepared_task_face.py:312–338根据grading.test_patch生成精确test_files，并设置test_globs=()。本题官方只触碰 `test-data/unit/check-literal.test`；Glog:295–302、Nlog:281–288实际checkout该文件并应用test.patch。不会把所有测试或fixtures恢复，额外排除=[]。Gold两行subtypes.py保持在投影里；test-requirements初态pin也不是本轮改进后的新官方测试材料。存在合法非gold源码路线，不应据目录名称新增大范围排除。

scoring.py:234–269用标记段解析后只对冻结F2P/P2P计分；vendor派生命令是另一路。manager.py:1197–1249把普通完整pytest rc0/1与启动、收集、内部等全局失败分开。若某个未引用旧case普通断言失败，并不自动令reward0；本次只选F2P，N失败正是参考目标，所以reward0有直接含义。G/N均1解析、missing/skipped=[]、outside0、execution_failure_decision=null；没有用删除失败项或吞安装失败得到分差。

恢复后的.test是实际断言来源，但其helpers/fixture/导入路径与候选源码也构成可信边界；本次只核读到的恢复、runner前后digest、投影，没做任何控制面绕过候选或全平台安全验收。public任务面grading_spec=None、导出无Git元数据和gold文本，支持静态分层；实际actor镜像/历史对象、预装包、缓存、mount与网络工具取得答案能力仍未验证。不能把本主审见过gold/隐藏测试等同于solver泄漏，也不能由公开包干净推出全环境没有泄漏。

本题没有另加路径规则的证据；原生源码subtypes/checkexpr是正常修复路径。涉及测试辅助修改的合法性与可能绕过应由统一机制负责人用正反候选检验，不在此凭假设修改共享保护规则。全部审查产物为特权材料，不能交给未来solver。

## 8. 暂定处置、关系、用途与唯一下一步

八方面均有具体证据边界：公开需求与可解性清楚；材料/初态与这对派生运行对应；所有新增/修改断言已展开；合理替代、长度部分实现和精确诊断风险有源码依据；gold及相关旧回归/调用者已核；actor条件未验；恢复/评分与泄漏层次明确；跨题关系、盲解、训练适用性与成本未知。

本题保留为needs_review/static_review/development_diagnostic。支持继续审查的是目标链可解释、gold两行与公开原例同向、真正F2P有多项正负保护、原运行0/1分差可信。未解决的是正式actor、原题CLI/flags、修改旧case未执行、替代实现与具体部分实现得分、广泛子类型回归和重复稳定性。零P2P、单F2P或一项覆盖缺口都不是自动拒收理由；也不能据此声称高质量训练题已验收。

**唯一优先下一项实验：**统一CPU负责人在确认真实actor身份与所载源码后，做题面完整单元素Union示例的base/gold对照，并附(2,)及长度不符(1,999)这两个有公开依据的负例。这先回答实际开发可达性与gold是否修到原例。此后再安排官方修改旧case、tuple局部候选及诊断变化替代解的冻结评分/独立行为对照，不在本轮自动扩P2P或改oracle。

未做跨题去重，也不从相同文件或patch里的issue7399/11232链接自动推断重复家族；链接未访问。未读其它题结论作证。没有真实模型轨迹、盲解或成功/失败归因样本，故不评定当前基座难度或训练收益。已有账本阶段耗时/内存只是该次评分运行数据，不转换成本轮静态审查或解题成本；未知wall/token/费用=null。独立reviewer待审，历史门禁尚未开放。

## 阅读/暴露清单

方法沿已授权investigator、record_template、actor_environment_card、quality_review_protocol及明确链接定义；未读B1/B2汇总、manifest、method_adjustments。本主审顺序上已审前两题，仅复用当前RH2机制与方法，不用其结论代替本题证据。11236特权暴露限本题包、gold/test/reference、原运行及sealed public_read；没有读environment_record、history或旧答案。

| 实际读取 | 范围与限制 |
|---|---|
| U/base_identity、public_bundle、user_prompt；P/source_refs/run_refs/grading/validation/test.patch/gold.patch；sealed public_read | 本题全文/结构化字段；按协调者新要求不再重复S2精确行对象或逐blob全包核验，source_refs仍保留第187行位置 |
| W/image.json/build.log，G/N ledger:1 | 图像原件与逐题账本对应字段；不读全批计划或environment汇总；沿run_refs读取真实日志 |
| Ga/Na stage/classification/projection/frozen_patch，Ga/candidate.patch | 对应HEAD、entry名单、共同baseline/public digest；解码并精确比较唯一gold源码entry。未遍历baseline_manifest的全包blob/mode |
| Glog/Nlog | 身份/命令界限、初态diff、精确恢复、安装和全部本case运行/摘要；重点G132–142、272–305、472–579，N132–141、271–291、458–595。日志git show中可见base提交其它文件改动，但没有跟进另一任务历史；旧例没有执行。原输出自身“...”未伪装成逐条完整打印 |
| base/mypy/subtypes.py | 45–145、180–214、243–309、335–377、397–408、493–513；关键被截断的278–297和tuple比较后单独重读。不是全仓子类型调用图审阅 |
| base/mypy/checkexpr.py、checker.py、types.py、typeops.py、erasetype.py、messages.py | checkexpr1517–1540、2080–2116、3088–3117、3288–3361及相关搜索；checker2135–2158、2208–2243、3308–3376；types793–836、1593–1658；typeops652–668；erasetype134–151；messages1635–1658、1651–1690、1703–1714。类型表示关键段在大输出截断后小段重读 |
| base/test-data/unit/check-literal.test | 1–97、1448–1468、1510–1531、2664–2726；不称全文件已读/已跑 |
| base/test-data/unit/check-tuples.test | 978–1004、1207–1235；围绕长度、上下文和星号展开 |
| fixture、harness与文档 | bool.pyi/tuple.pyi全文；typing_extensions.pyi1–34并精确核Final/Literal行；testcheck137–181、189–225；data44–82、260–281；literal_types1–16、93–151 |
| 开发配置 | setup77–86、193–202；mypy-requirements、test-requirements、pyproject全短文件；pytest.ini1–24；fastparse48–82。CONTRIBUTING/main CLI定义等由sealed public_read引用，未冒称本主审再次阅读全文 |
| 当前RH2共用机制 | 已读prepared_task_face312–357、spec_vendor183–191、scoring234–270、manager243–261/594/1197–1249、sandbox_profile311–340；复用同ROOT的机制阅读，未复制前题处置 |

静态提取日志时一次自写Python索引因真实命令含`git -c ... diff`而StopIteration，已按真实命令边界修正后重读；这只是元数据提取错误，非项目执行或任务失败。其它工具仅作读/搜索/JSON/hash/文本比较和写本稿。保存后暂停待协调者封存及本题历史门禁。
