# conan-io__conan-13788 — analysis_before_history

日期：2026-09-25。判断者：私有主审 /root/e25_main_pack10_conan。本稿在读取任何 history、reviewer 或旧质量结论前写成；仅静态读取授权材料，未运行、导入项目/测试、安装或访问网络，未派生 agent。报 SHA 后永久封存。

## 结论

公开材料支持按有效上下文保留同名构建依赖，而非全局禁止同名版本。新增 F2P 揭示了锁文件重放时 host/build 同名项按名字覆盖的真实问题；授权原运行为 noop 1 failed/9 passed，gold 10 passed，均完成目标测试且无安装阻断。gold 的联合键解决局部碰撞，但它把所有未设置 build_require_context 的普通依赖按 host 查询；build 上下文工具的普通依赖实际上继承 build。此路径不在这十项中，是明确且高优先的静态回归疑点，尚无本轮运行证明。保持 needs_review/static_review、development_diagnostic，不能将 gold 10 passed 推成完整正确或 actor 已可开发。

证据根固定 `/Users/roger/Desktop/claude-code-verl-stage0h`。P=`runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788`；V=`runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788`；源码路径相对 P/base。原 ledger/log 的全路径与 identity 见附录。

## 1. 公开目标、版本与初态

P/user_prompt.txt:3–13 报告 Conan1.59 的锁文件中同时出现来自 profile 和 recipe 的同名不同版本，询问是否允许、安装选哪个。未给复现资产/命令/锁文件，也没有说全局去重是确定规格。源码 graph_manager.py:21–43,336–367 以 (name, context) 区分构建依赖，在同上下文已有 profile 覆盖；graph_lock_build_requires_test.py:52–144 公开测试允许 host/build 两个节点，179–194 允许不同消费者需要不同 cmake 版本。因此“一律拒绝两版本”会破坏已有合理行为。

P/base_identity.json 为精确 base `c1b3978914dd09e4c07fc8d1e688d5636fda6e79`、tree `7d5ed9cff5f8265f1c67fc899d7edab378cc9d8d`、1276 个 blob；V/grading.json 版本1.60，原运行包为1.60.0-dev。用户报告1.59而选中修复基线1.60开发版并不自动构成错题；具体静态/原运行均能命中目标。这里不证明在1.59任何部署复现。

base导出非实际actor checkout。原noop日志135–139显示评分阶段clean/正确HEAD，243行 diff <base> 为空；gold 135–144 显示唯一 graph_lock.py 修改，248–276 为实际候选diff。139或144之后的 `git show` 展示base提交自带的 Windows测试变更，不是隐藏的初始未提交修改；不能把该输出误当环境修复。实际 actor 的原始状态、准备后 porcelain/RC、忽略资产、模型消息仍unknown。

## 2. 全部新增断言、helper与双向映射

test.patch 全部读过：仅增加 pytest import 和两个参数化实例。`test_duplicated_build_host_require[True]` 是唯一 F2P；False 是 P2P。两者在新文件272–289行使用同一fixture：本地 create tool3.0与4.0；profile的 `[tool_requires] tool/[^3.0]`；pkg在True时通过 build_requirements 调 tool/[^4.0] 并 force_host_context=True，False时通过 requirements 调普通 tool/[^4.0]；先 `install pkg -pr:b=default -pr:h=profile --build`，断言tool4.0来自cache；再 `install pkg --lockfile=conan.lock`，同样断言tool4.0。没有显式 lock create；首次 install 写出的锁文件由第二次消费。

GenConanfile:106–123,262–299,405–427 确认真正生成普通/构建依赖声明，force_host_context=True没有被丢掉。TestClient:326–346 从本地初始化配置/默认profile后复制cache；365–434创建临时目录；458–466默认TestRequester；547–581调用真实CLI、每次重置输出；591–616强制默认命令成功并保存真实文件。断言不是从前一命令输出串起来；但只查输出子串，未读JSON锁定边或检查tool3.0仍存在。测试所用本地包为空Python recipe，无真实编译或远程包需求证据。

下表中 B=`conans/test/integration/graph_lock/graph_lock_build_requires_test.py`；旧类方法完整 ID 均为 B`::GraphLockBuildRequireTestCase::<方法>`。

| 需求或合理旧行为 | 公开依据 | 测试ID / 决定性断言 | 覆盖和原运行 |
| --- | --- | --- | --- |
| host构建依赖与profile build同名项各取正确引用 | graph_manager.py:21–43,336–395；graph_builder.py:90–113 | B::test_duplicated_build_host_require[True]，两次install输出均含tool4.0 | F2P目标覆盖；noop仅第二次断言失败（原日志513–517），gold通过。未直接断言tool3.0/build边或节点数量 |
| 普通host依赖与build工具同名也可共存 | graph_builder.py:134–139,240；既有两context测试 | B::test_duplicated_build_host_require[False]，同样两次tool4.0输出 | 新增P2P，noop/gold均pass；普通host依赖和build_requires分列表，不能代替混合build_requires列表的检查 |
| 同一build requirement在多个消费者共享，build-order准确 | B:11–50 | test_duplicated_build_require：br ref/prev、完整build-order与install建包信息 | P2P pass→pass；此例单profile，节点context=host |
| 同包可同时host/build | B:52–92 | test_package_both_contexts：节点3、两个context的完整build-order、install包revision | P2P pass→pass；工具protobuf无普通requires，未覆盖build工具的子依赖 |
| 不同context可有不同package ID | B:94–144 | test_package_different_id_both_contexts：Linux/Windows两个ID、build-order及install命令成功 | P2P pass→pass；末段自己说明安装哪个context有歧义，没有最后节点ID断言 |
| 未构建时保持锁定build requires；重建补prev | B:146–177 | test_build_require_not_removed：三次检查flac ref、package_id与prev变迁 | P2P pass→pass；保护锁文件保留行为 |
| 不同消费者的同名版本不被全局禁止 | B:179–194 | test_multiple_matching_build_require：范围安装被拒绝，明确cmake1.1安装输出存在 | P2P pass→pass；没有强制全局唯一名称 |
| profile/recipe不同名依赖均不可丢 | B:196–218 | test_unused_build_requires：base.lock→full lock→install，cmake/gtest各自cache和Applying信息 | P2P pass→pass；同时检查两条来源 |
| 条件声明消失须报错 | B:220–242 | test_conditional_env_var：锁中两依赖；移除USE_DEP后必须错误且指定locked requirement not found | P2P pass→pass；错误有真实文本断言 |
| test_package的范围build requirement仍能使用 | B:245–268 | test_test_package_build_require：root ref=None/path、create中Applying cmake1.0 | P2P pass→pass；覆盖未锁test_package的特殊分支 |
| 同上下文profile覆盖recipe | graph_manager.py:359–364；build_requires_test.py:334–359 | 该公开旧测试检查Tool0.3并排除0.1/0.2，未纳入本题expected | 静态依据；运行未验，未完整读其上方所有fixture，不能声称本轮证明全组通过 |
| build上下文的普通requires应继承父节点context | graph_builder.py:193–208,437–479；requires.py:14–32 | 本题10项无此构图；新增tool recipe为空、旧两context protobuf亦为空 | 确定覆盖缺口；gold else CONTEXT_HOST带来具体回归疑点，未执行 |
| 锁定结果应忠实到版本、边、context，而非仅打印存在 | GraphLock构建/序列化:279–328,251–276 | 新增两个实例只检查tool4.0存在，不检查tool3.0/context/边，也无cache变化重放 | 部分覆盖；可漏掉锁文件被忽略或部分丢失的修复，尚未做变异实验 |

反向看所有新增条件：双profile、host与build的区分、range语法都有公开代码支撑，是一个合理具体化；不能由此反推出用户场景一定正是force_host_context。验收不要求某函数或字典结构，未发现实现形状绑死；日志子串约束了既有用户输出格式，纯格式改进可能需兼容，尚未验证替代解公平性。

## 3. Gold全量与调用者/回归审查

gold仅改 graph_lock.py：导入CONTEXT_HOST；将 locked_requires 的name键改为(name,locked_node.context)；查找时用require.build_require_context，否则CONTEXT_HOST。序列化/加载字段与其余特殊分支均未变。V/gold.patch、validation golden hash和原candidate hash一致。

局部根因链可静态追踪：graph_manager生成两个context的同名build_require；graph_builder:90–101显式给Requirement设置context；旧lock_node:535–545对父节点build_requires所有ID仅按name建字典，后项覆盖先项；require.lock在requires.py:28–32实际替换ref/range_ref/locked_id。因此旧重放可丢失host4.0。联合键针对这条链合理，且原运行的target F2P提供局部执行正证据。

具体回归疑点不是单凭漏测猜测：

1. 普通Requirement在requires.py:14–26默认build_require_context=None；全conans限定rg显示只有graph_builder:94为构建依赖赋值，没有普通依赖填父context的赋值点。
2. graph_builder._create_new_node:440–446,467把非context_switch的子节点设为current_node.context；故build工具T的普通依赖D实际为build节点。
3. _get_node_requirements:193–208在T展开普通requires时调用同一graph_lock.lock_node；GraphLock:296–324记录的是实际目标D的context=build。
4. gold却以(D,host)查(D,build)，严格锁模式将走KeyError→ConanException；旧name键在单一D的例子不会因context不符失败。这个分支不需要同名双版本就可能回归。

这是高置信静态路径推断，尚未构造和运行真实CLI对照，不将它写成“已证gold运行回归”。`graph_lock_ci_test.py:863–971` 的片段虽有双profile/build-order，但br recipe无普通requires，同样不能反驳这条疑点；该函数起始fixture未完整读，不计完整语义覆盖。旧锁文件context缺省也值得保留不确定性：deserialize:244使用data.get('context')，没有默认host；未读迁移契约，不另定兼容必须性。

合理非gold实现可在build_requires分支按context筛选后以name匹配，而普通requires保留原行为；或把默认context取node.context并正确处理显式构建依赖。数据结构并非唯一，测试原则上容纳；本轮未执行，不能声称所有合法解可过。全局删除同名节点或固定选最大版本不符合已有上下文/消费者语义。只让输出出现tool4.0、忽略锁或在cache未变时重新解析，也可能绕过新增两断言；这是检查25的覆盖推断，不等于已验证可作弊candidate。

## 4. 原运行、安装、expected与可信交付

V/run_refs只授权baseline01/workers/w01-2本题第15、16行，机械选择后读取；没有浏览邻题。

- noop log `evallog_replay-f216-baseline01-w_869b80b6.eval.log`：243–284恢复base B并cleanly apply test.patch，RESTORED=1/EXPECTED=1/ABSENT=0/SETUP_OK=1。419–477安装；482命令 `pytest -n0 -rA conans/test/integration/graph_lock/graph_lock_build_requires_test.py`；487 collected10；目标第二次install本身成功、但289行期待tool4.0子串失败（513–517）。534–543逐项9 PASSED/唯一True FAILED；test RC=1。
- gold log `evallog_replay-f216-baseline01-w_423e6042.eval.log`：248–276完整source diff；277–317同样恢复及应用可信测试；452–510安装；515同测试命令，520 collected10；541–550上述所有10 ID逐项PASSED，test RC=0。
- 原shell source/activate testbed、cd /testbed、设置PYTHONPATH；依次 `python -m pip install -r conans/requirements.txt`、server、dev。依赖already satisfied；Python2专属Jinja2/MarkupSafe/configparser及pytest声明被marker正常忽略，不是测试skip。两次安装最后命令RC0。Python3.10.14、pytest6.2.5、xdist3.5.0；三条DeprecationWarning没有阻断执行。
- expected=1F2P+9P2P，与10条完整pytest ID一致，无skip/xfail，reference_missing/skipped=[]、outside_segment=0。source parser swegym_parsers@242429c1，grader swebench4.1.0；本轮未读内部parser/评分实现，未测重复评分。
- gold included_paths仅conans/model/graph_lock.py；原candidate hash匹配，noop无patch；projection物理attempt、base/head授权指针匹配。诊断可信测试数1、PROTECT_OK1、missing0、runner_digest前后相同；cleanup.removed=true。仅说明这对已知候选的恢复投影和运行，不证明任意actor可交付或无控制面绕过。

## 5. 真实开发需要与缺证据

| 需要的操作/资产 | 公开依据 | 现有证据适用范围与缺口 | 最小公开命令/预期（本轮未执行） |
| --- | --- | --- | --- |
| 正确源码初态、非测试源修改和交付 | P/public_bundle与environment_brief；base身份 | 历史grader在所示base；当前actor消息/HEAD/diff/UID/HOME/cwd/PATH/写权限unknown | 在实际actor保存pwd、git rev-parse HEAD、git status --porcelain=v1及RC，保留来源初改；确认能编辑源码而非重置它 |
| Python/Conan/pytest环境与source生效 | 三份requirements、test README:11–24 | 历史grader1.60.0-dev从/testbed导入且安装成功；actor解释器及包来源unknown | 打印sys.executable与conans.__file__；窄公开 `python -m pytest conans/test/integration/graph_lock/graph_lock_build_requires_test.py -q`，记录实际节点/RC而非只collect |
| 本地cache、recipe/profile/lockfile读写 | TestClient:326–346,365–434；B中的本地构造 | 已有grader测试能创建；actor HOME/TMP、资产位置和权限unknown | 公开fixture export/lock create/install应能读写cache和lock，不应权限失败；无需由静态缺失猜镜像缺件 |
| 用户实际锁重放而非内部helper替身 | graph_builder/graph_lock既有流程与公开双profile测试 | TestClient经真实命令逻辑，但当前实际shell CLI未验 | 构造root→build tool→普通dep，`conan lock create root/conanfile.py -pr:h=default -pr:b=default --build --lockfile-out=conan.lock`后`conan install root --lockfile=conan.lock --build`；实际边context保持build，详见唯一下一步 |
| 依赖供应/资源 | requirements；test README将integration定义为纯Python | 历史graderdeny_all下依赖已满足；actor网络资源unknown | 若缺依赖先用批准供应路径；本题目标无GPU/模型/真实远端包/C++编译必需证据，不需全仓工具链验证 |

## 6. 用途与泄漏、关系、流程

本题与同包13610分别是Conan1.x锁文件和2.x日志参数，base/gold/测试独立；未做跨数据集重复或留出重叠普查。实际actor可见答案、网络取答案、写控制面能力皆unknown；主审合法见过private test/gold和原运行，应记录usage中的授权私有暴露，不能把此写成check29实际泄漏。未读history、reviewer、旧质量结论或根汇总，未跟随测试注释URL。报告不可给独立solver。

usage.intended_use=development_diagnostic；disposition.state=needs_review、scope=static_review（有具体回归疑点且actor未验）；additional_exclusions=[]、revision_refs=[]；没有执行候选或改动源题。未观测成本字段null。没有真实Claude Code尝试，故能力、训练难度、训练资格和成功解完整性不能判定。按阶段封存只证明流程遵守，不证明无漏检/误拒/抽样偏差。

## 7. 稀疏检查、问题与唯一下一步

各项by均为本文主审；evidence_refs为对应节与源码/原件定位；未列项not_checked。

| checks | status | evidence_refs与边界 |
| --- | --- | --- |
| 1 | pass | §1/4、附录：静态包与原candidate对应；actual image ID不在此pass范围 |
| 2 | pass | §2/4：base对新增True重放断言失败，gold局部通过 |
| 3,4 | unknown | §1/5：实际actor输入/工作树/权限未验，规格是否可推导另归23 |
| 6,7,8,9,10,11,13 | unknown | §4/5：历史grader的执行正证据不等于当前actor资格 |
| 16,17,18,19,20,21 | pass | §4：仅原noop/gold候选投影、可信测试恢复、实际10项执行和目标分差 |
| 23 | unknown | §1/2：语义能由代码推导，但原用户具体复现/上下文缺失；不推定全局禁止重复 |
| 24 | unknown | §3：不限制字典形状；未运行替代解检验误拒 |
| 25 | issue | §2/3：未测build工具的普通依赖、锁边/context和build3.0保留 |
| 26 | unknown | §3：高置信gold回归疑点待真实CLI对照，未写成已证运行失败 |
| 27 | unknown | §3/4：碰撞修复有正证据，整体正确完整未成立 |
| 28 | pass | §1/3：沿已有上下文语义提疑点，不擅加全局去重或锁格式迁移要求 |
| 29,30,31,33,34,35,36,38,39,40 | unknown | §5/6：无实际solver/攻击面/当前复验或完整筛查证明 |

| issue/category | scope | evidence_refs | proposed_action | status |
| --- | --- | --- | --- | --- |
| BUILD-NORMAL / potential_gold_regression | build工具内部普通requires的锁重放 | requires.py:14–32；graph_builder.py:193–208,437–479；graph_lock.py:296–324及gold.patch | 用三节点纯Python公开CLI fixture做同条件base/gold对照，核边context与错误位置 | open, static_inference |
| COVERAGE / test_coverage | 缺失锁边、tool3.0存在性与普通build子依赖 | test.patch全量；§2表 | 根据验证结果补充有公开依据的断言评估，不能用10个pass代替语义覆盖 | open |
| SPEC / specification_gap | 用户未给具体profile/recipe/context | P/user_prompt:3–13；公开reader | 保持条件化问题描述，避免以用户疑问创造全局禁止多版本规格 | open |
| ACTOR / evidence_gap | 当前actor输入和开发可用性 | P/environment_brief；§5 | 任务二取得实际入口/权限/导入与窄CLI证据 | unknown |

唯一优先下一步：由任务二做“build工具T带普通依赖D”的最小公开CLI对照。使用本地空D/1.0，T/1.0的`requires='D/1.0'`，root的`build_requires='T/1.0'`；export D/T，再按§5两profile lock create和install --build重放；在相同实际入口/依赖下分别用base和私有gold。保存两条命令RC、完整异常栈/CLI错误以及lock中T→D的context。预期base可重放而gold可能报Require D cannot be found；若gold通过，需要查明哪条实际路径为普通require提供context或绕过了推断。该结果会改变check26与gold完整性判断；仅重跑既有10项或全仓测试不是优先步骤。本文没有执行或派发这项实验。

## 8. 实际阅读与未读范围

完整直接读取：中性角色/模板/检查编号/环境卡/开发方法、本包卡、本题public_read；P/user_prompt、base_identity、environment_brief/public_bundle；V/grading/test.patch/gold.patch/validation/source_refs/run_refs的结构化内容；B全文1–268及新增patch所有行；三份requirements、pytest.ini。较大的首轮合并输出曾截断，决定性材料均分段补读，没有将截断输出视为完整覆盖。

源码分段：graph_lock.py:1–94,94–138,138–280,279–330,500–590（其中最初输出中94–137被截断后已补）；graph_builder.py:1–160,175–250,437–481；requires.py:1–150；graph_manager.py:21–48,310–421；GenConanfile:1–45,90–136,262–307,405–427；TestClient tools.py:300–435,447–470,470–583,591–626；build_requires_test.py:334–360；graph_lock_ci_test.py:863–972；测试README:1–36。仅对graph_lock测试目录相关参数与全conans的build_require_context赋值做rg定位，不据命中声称全文已读。

原件直接核：两条ledger仅15/16行；两份diagnostics完整；baseline/projection/stage仅授权JSON指针；candidate原hash对照，实际diff由对应log展开。关键log连续段为noop:130–225,237–298,418–551；gold:130–225,242–319,420–558。初轮整体输出/摘段有截断，关键恢复、安装命令、逐项结果和目标失败已补读；重复conda展开及git show的无关base提交正文未逐行审。日志原文件hash与指定值相符。

未读：其余源码和测试、完整conftest/测试环境设置、完整CLI安装/锁创建内部入口、完整graph_lock_ci fixture及其余函数；未读历史或reviewer；未读归档成员/host_grading_view或parser实现，未执行项目或替代解。source_refs只是来源身份定位，没有沿它跨题扩读。公开reader读到的额外范围不算本主审直接阅读。

## 9. 精确原件、身份与资源附录

以下 identity/resource 值机械摘自本题 run_refs 与授权账本行；原字段单位未另推断。历史成本不是本轮工具观测成本。image tag、expected manifest digest 与 actual ID 分开；未拿 image_identity 代替 actual ID。

- source image tag: `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13788:latest`
- expected manifest digest: `sha256:c61a9b9f87dcee19aff867f583028bd115f6fcf3487c2c603471787a9eb7472d`
- actual actor image ID: unknown；两个历史 grader 的 image_id_actual 均 null。来源单题inventory原定位未存在不证明镜像缺件。
- V/test.patch SHA256: `a64a72011ace2494d53cb58b05646d63bf1418f97ad75cf0c3ae23d15260d0a5`
- V/gold.patch SHA256: `6abb6d5db6bf7eeb7f44aa9aa0da9b3823256b63ff94fdcda85c6c9b50869366`

来源adapter材料只使用本题导出字段；未展开共享源文件：
- public: `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl:35`；line SHA `69615cf262127797f293646c0dea113d44882cd2c711ae2e7f37b7d6ead458df`。
- grading: `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl:35`；line SHA `2f543e641dc881e97ad927a97aef5f5af9741fab771fe7cd4c0c0f3f8ae9a84a`。
- validation: `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/validation_bundles_v0.jsonl:35`；line SHA `7e55b35b4f1142cba958f928f525c60b96a0fef66d8752b22b189b2f92035623`。

### noop

- ledger: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:15`；line SHA `761c82a9980be582c64bf1dcb81bf842e99059af798f22496817f719ae4e719e`（本轮机械核对一致）。
- log: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_869b80b6.eval.log:1–551`；SHA `6f8090872bfc8a51b6d69ebdc9f35059f6701187423d1504309174c5737c737b`（原文件hash核对一致；正文阅读范围见§8）。
- diagnostics: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_869b80b6.diagnostics.json`。
- scripts_digest: `sha256:47ec952aaa32c5c07cab7035fdb11bfc9866e916cb500380e9d6519aba1f8355`；baseline policy: `baseline_policy_v2`；derived_image_recipe: `None`。
- 原 policy: `{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`。
- 原 budgets: `{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`。
- 原 resource: `{"mem_peak_mb": 95.371, "mem_peak_unavailable_or_zero": false}`；resource_facts=null。
- 原 install/test: `{"install_rc_last_command": 0, "install_seconds": 2.419, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 5.234}`。
- projection: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-5b67255a/projection.json`；仅授权指针 `{"/frozen_patch_digest": "sha256:7b0ff21feda9b556a32929f038ae05ae72657dd42b972122e6753fef670a1f61", "/included_entry_paths": [], "/physical_attempt_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-13788-5b67255a", "/rollout_execution_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-13788"}`。
- baseline: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-5b67255a/baseline_manifest.json`；仅授权指针 `{"/materialized_head": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79", "/task_base_commit": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79", "/task_id": "swe_gym_lite::conan-io__conan-13788"}`。
- stage: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-5b67255a/stage.json`；仅授权指针 `{"/apply_method": "noop", "/head": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79"}`。

### gold

- ledger: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:16`；line SHA `14c24e47e78e1c6316f1e5f2e80d9ca55499157d576bc2e5bcbe771f930b4ab1`（本轮机械核对一致）。
- log: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_423e6042.eval.log:1–558`；SHA `10e3bda4ae29d3f3550877ed51ceac14e567c5d65e20ecd7a3b4db2eeea1a9d9`（原文件hash核对一致；正文阅读范围见§8）。
- diagnostics: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_423e6042.diagnostics.json`。
- scripts_digest: `sha256:47ec952aaa32c5c07cab7035fdb11bfc9866e916cb500380e9d6519aba1f8355`；baseline policy: `baseline_policy_v2`；derived_image_recipe: `None`。
- 原 policy: `{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`。
- 原 budgets: `{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`。
- 原 resource: `{"mem_peak_mb": 91.129, "mem_peak_unavailable_or_zero": false}`；resource_facts=null。
- 原 install/test: `{"install_rc_last_command": 0, "install_seconds": 2.355, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 5.093}`。
- projection: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-1fb10712/projection.json`；仅授权指针 `{"/frozen_patch_digest": "sha256:b171ccc5bc7654db7472a2591f8ea50b51e67f906b869940dbfcc9d1bcc116cf", "/included_entry_paths": ["conans/model/graph_lock.py"], "/physical_attempt_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-13788-1fb10712", "/rollout_execution_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-13788"}`。
- baseline: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-1fb10712/baseline_manifest.json`；仅授权指针 `{"/materialized_head": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79", "/task_base_commit": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79", "/task_id": "swe_gym_lite::conan-io__conan-13788"}`。
- stage: `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-13788/a1-1fb10712/stage.json`；仅授权指针 `{"/apply_method": "git_apply", "/head": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79"}`。

环境记录列出的历史source_snapshot/归档只作为未展开的身份定位；本轮未核archive成员字节、未审原runner源码，当前实际入口代码也未获取。因此source digest与实际运行镜像/actor接线不互相替代。
