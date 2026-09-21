# python__mypy-11707：历史解封前独立初判

本稿在未打开本题历史调查、旧 record、reviewer 或 root 聚合的条件下保存。结论是 **needs_review / static_review：先澄清题面与现有导出契约，再决定修订及诊断用途**。已有环境修复的 gold/noop 真实重放成立，但这不能消除题意冲突，也不构成本轮 actor 验证。

当前有两项独立发现：

- **I1，公开规格冲突，证据为公开原件与源码静态推导。** issue 明示希望两种改名导入都接受；base 文档明确只允许同名别名再导出。gold 采用后者，静态上把原例统一为两种都拒绝。不能将“消除不一致”直接替代题面写明的成功结果。新增隐藏测试本身符合公开 stub 旧规则，但没有直接验证原例的普通 `.py` 与命令行选项。
- **I2，具体回归漏测，证据为静态反例，尚未执行。** 删除所有子模块豁免、直接令 `module_hidden = not module_public`，静态上足以满足选中的 F2P/P2P，却会使公开 `testReExportChildStubs` 的真实子模块导入失败。两项参考通过不能证明保留了 gold 特意保留的模块语义。

## 引用与材料身份

本稿路径简称：

- `P` = `runs/swegym_quality_batch05_20260921_v1/public/python__mypy-11707`。
- `V` = 同材料根的 `private/python__mypy-11707`。
- `E` = `runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11707`。
- `A` = `runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`。下文 `A!路径:行` 为归档内原成员；只以 `tarfile.extractfile` 读取，未解包、导入或运行。
- `GLOG` = `E/gold/eval_logs/evallog_replay-er19-iw1-python___bab5562a.eval.log`；`NLOG` = `E/noop/eval_logs/evallog_replay-er19-iw1-python___521f6047.eval.log`。

`P/public_bundle.json:1`、`P/base_identity.json:3–15`、`V/grading.json:1` 与 host grading 原账本第 193 行一致指定 base `5d71f58b9dc5a89862253fef3d82356a7370bf8e`；导出声明 tree 为 `880d3d6572dfa456a5a96e752e1e0e49431da4ca`，1747 个跟踪 blob，无 gitlinks/LFS 指针/.git。未重新穷举复算所有 blob。base `mypy/version.py:8` 是 `0.920+dev`；报告者写 0.910/Python 3.10，不能把报告者输出视作本 base 的运行证据。

已核实 `V/test.patch` 与 grading 内补丁逐字相同，`V/gold.patch` 与 validation 内补丁逐字相同；gold SHA256 为 `1d25e148e9ab3295d29619c8941012b9186059c405a204d5dccceb941e89267c`。host 原件 `runs/full216_rh2_diagnostic_20260919/remote/replay/private/host_grading_views.jsonl:193` 的 raw-line SHA256 为 `cd08fb59d9cecc3a4c71ee969bb55765890db68a2bca4f4adb08cebb6a98baa3`，grading digest 为 `sha256:c7e5e87666dd69a913b6a9daff4501b4ceeccab322cc0a8161e47702538dfcc8`。只读取该行。

已读并核验封存 `public_read.md` 的 SHA256：
`053dddc06b6701bfbe5b97b98e0deddf0e048522756684059b94be0f553c39e3`。公开读者的观点不是代替原件的证据；下列关键文档、源码、测试及开发要求均已直接复读。

## 1. 公开需求（3、23）

`P/user_prompt.txt:10–70` 给出四文件包：`a/X.py` 定义类 X；`a/__init__.py` 同名导出 X 并设 `Y = X`；`c.py` 把 Y 或 X 改名为 W；`d.py` 导入 W。在 `--strict --no-implicit-reexport` 下，“两种都接受”是明确预期。标题的 `--no-explicit-reexport` 是误称；正文命令、`base/mypy/main.py:670–673` 足以消歧，不需要新增拼错的 CLI 选项。

但 `base/docs/source/command_line.rst:556–576` 明示 `from foo import bar as bang` 不导出，同名 `as bar` 与 `__all__` 才导出；`config_file.rst:592–610` 与 CLI 帮助 “unless aliased” 更简略，容易造成题面的误解。公开旧测试 `check-modules.test:1819–1840` 也区分 C as C 与 C as D。题面没有提供维护者澄清，也没有非包例子的完整文件布局；非包范围不能随意扩大为每种布局的明确需求。

因此至少两条维护路线都能从公开材料提出：扩展普通 `.py` 改名别名的导出规则且保留 stub 旧行为；或者保留既有规则、修正包中类名恰与子模块同名造成的偶然放行，并澄清文档。第二条直接不满足 issue 的字面预期，必须公开说明取舍，不能由隐藏 gold 默默裁决。

`public_hints` 的 NON-TEST/禁止改测试是操作指令，conda 已激活是环境声明，不是问题规格。其是否进入实际 system message 未捕获；静态 prompt 不包含它，不代表公开 bundle 不可读。`P/environment_brief.md:18–26` 已限定“所有测试都会恢复”的旧说明不能代表当前机制；本审查不自行解除禁令。

## 2. 初始问题与调用链（1、2、27）

已沿 `fastparse.py:903–914` → `nodes.ImportFrom.accept:393–409` → `build.py:755–785,3124–3140` → `semanal_main.py:66–85,299–331` → `semanal.py:389–422,1817–1925` 阅读。文件系统中的 `a.X` 被加入模块依赖，但导入的值可以是 TypeInfo/TypeAlias，而不是模块对象。

base `semanal.py:1841–1845` 为 stub 或关闭 implicit_reexport 的文件只把同名 as 标为 public；`:1895` 却仅因 `fullname in self.modules` 就不隐藏。对原例，`a.X` 恰存在，而 `a.Y` 不存在，因而与报告的不对称相符。下一次 `from c import W` 经 `:1870–1878` 检查 module_hidden；`:1939–1955` 产生已有导出错误并填未知符号。不能只把 module_public 改为 False 就解决显式导入：`nodes.py:3138–3142` 说明其主要控制星号导入，module_hidden 才控制对外可见性。

这不是单凭 gold 差异推断初态：`NLOG:643–655` 实际进入 `testcheck.py:140,227`，预期两条输出，实际只有正确的类构造器 reveal_type，缺少 `internal_detail` 应报的错误。故本 base 在**隐藏 stub 场景**的 bug 有真实执行证据；四文件 `.py` 原例的 base/gold 结果仍是静态推导，没有本轮或已读日志的直接复现。

## 3. 测试展开与双向映射（18–20、25、32）

完整阅读 test patch 的全部 18 行新增用例与 gold 全部改动。唯一 F2P 是 `mypy/test/testcheck.py::TypeCheckSuite::check-modules.test::testReExportChildStubs3`；唯一 P2P 是同前缀的 `testNoReExportChildStubs`。无 Mock、外部服务或运行时用户程序；真实调用 `build.build` 做类型检查。

F2P 的 `package/mod.pyi` 定义类 mod；包 `__init__.pyi` 同名导出此类；`util.pyi` 同时将它同名导出为 mod、改名为 internal_detail。主程序必须只得到：
1. `main:2: note: Revealed type is "def () -> package.mod.mod"`；
2. `main:4: error: Module "util" has no attribute "internal_detail"`。

P2P（base `check-modules.test:1913–1930`）的包 stub 从子模块导入 C 与 D as D，内部 `x: C` 合法；主程序的 `from mod import C, D` 对 C 报错，`mod.C` 再报成员错误，而 `mod.x` 为 `mod.submod.C`，`mod.D().a` 为 str。它保护了隐藏的普通类、显式导出的类与内部可用类型，**没有从包导出真正模块对象的正例**。

| 公开要求或旧行为 | 公开依据 | 测试/关键断言 | 覆盖判断及证据 |
| --- | --- | --- | --- |
| 原四文件 Y as W、X as W 都接受 | prompt:46–70 | 无对应 `.py` 或 CLI flag 用例 | 缺失；gold 静态方向与字面预期冲突。 |
| stub 同名 as 导出类，保持类身份 | command_line:571–572；check-modules:1822–1838 | F2P reveal 构造器返回 package.mod.mod | 已覆盖，gold 实测通过；不能用模块或 Any 顶替。 |
| stub 改名 as 不再导出，即使类名撞上子模块名 | command_line:568–569；check-modules:1821,1832 | F2P internal_detail 应报缺失属性 | 已覆盖；noop 实测缺此错误、gold 通过。它是旧契约的碰撞边界，不是 issue 新 API。 |
| stub 无别名类不导出、D as D 导出、内部类型可用 | check-modules:1913–1930 | P2P C 两种访问报错；x 与 D().a 的 reveal | 已覆盖，gold/noop 都通过。 |
| 真子模块 `from mod import submod` 仍可用且类型正确 | check-modules:1879–1911 | 公开 testReExportChildStubs / ChildStubs2 | 已读，但不在评分选择器/参考中；I2 的可区分正例。 |
| 普通文件默认导出、关闭选项、__all__、星号、配置作用域 | check-flags:1541–1648；semanal-modules:825–864；check-modules:2901–2917 | 多项既有公开用例 | 已读相关测试；未被此两项评分保护，未运行。 |
| 限定名访问、缓存/循环导入可见性 | semanal:4348–4418；nodes:3239–3242,3277–3280；check-incremental:5589–5612 | 唯一 P2P 有 mod.C；循环用例另在公开库中 | 成员访问部分覆盖；F2P/P2P 均非 incremental，冷热缓存未覆盖。 |

反向检查：F2P/P2P 的每项隐藏/导出及类型要求都能追到公开旧语义；没有要求 gold helper 名、条件写法、操作顺序或具体源码文本。错误文本与 reveal_type 严格比较是已有 mypy 测试接口，当前未发现不合理额外格式约束，不能据此证明所有等价实现都会接受。

helper 已追到 `mypy/test/data.py:31–81,168–183,244–295,459–487`：解析 [file]、复制 builtins fixture、把 E/N 注释变为期望输出、为每个 case 创建可写临时目录并调用 suite。`testcheck.py:118–227` 禁用这两个 case 的 incremental/cache，调用 `build.build(..., alt_lib_path='tmp')`，归一化路径后比较完整输出。`helpers.py:46–120,301–307` 只做既有输出清理/比较，差异会抛 AssertionError。完整读了 `fixtures/module.pyi` 和对应 lib-stub types/typing；fixture 给出基本 object 无参构造器、str 等，未伪造业务答案。`modulefinder.py:714–740` 确认测试 lib-stub 搜索路径。

`A!src/repoharness2/envpack/spec_vendor.py:134–137,183–197` 从 test patch 中所有 [case] 名产生 -k，包括上下文的 P2P。实际命令 `GLOG:651` / `NLOG:633` 是 `pytest -n0 -rA -k 'testReExportChildStubs3 or testNoReExportChildStubs'`；各收集 10041 项、仅选 2 项。因此“2 passed”不能称全模块/全仓回归通过。原 ledger/diagnostics 均为参考缺席 0、跳过 0、标记段外解析 0，且日志展示真实断言执行，超过单纯 parser 状态的证据强度。

## 4. 合理解与部分解（24、28）

合理的非 gold 组织路线可以在导入解析处先区分真正 MypyFile 与普通符号，集中计算可见性，或把该谓词提取为内部 helper；保持同名导出、__all__、模块豁免和原节点身份即可。测试没有固定这些实现细节。若公开裁决选择“普通 .py 的任意 as 都算显式导出、stub 保持现状”，也可以分别计算这两类文件的 public 规则并修复 stub 碰撞；现有两项参考不能裁决该路线与 gold 的区别。当前未证明误拒了一个同时满足完整公开契约的实现。

I2 的错误简化是 `process_imported_symbol` 中直接用 `module_hidden = not module_public`。F2P 的同名 mod 和 P2P 的 D 都 public，私有 internal_detail/C 都非 public，故静态预测两项仍过；但 `check-modules.test:1879–1895` 的 `from . import submod` 会把真实 MypyFile 标 hidden，主程序 `from mod import submod` 随后失败。此预测未写成候选补丁、更未跑分，不能写“已证实 reward=1”。另一个边界是仅修 stub 碰撞：两项参考可能接受，而题面普通 .py 不对称仍在。两种局限均不需要改测试或评分控制面才能触发。

## 5. gold 与回归完整性（26、27）

gold 只改 `mypy/semanal.py` 的一处条件：只有节点真为 MypyFile 且 fullname 在模块表里才享有模块豁免。它保持原 SymbolTableNode.node、module_public、__all__ 后处理、已有诊断及序列化字段，未带入新依赖、无关源码或 test helper。对保留旧导出契约的目标，这一修法有具体代码理由。

对 issue 原例，X 分支是 TypeInfo，Y 别名也不是 MypyFile，且两个改名导入都非 public；gold 静态上会令两者都 hidden。因此 gold 消除不一致，却不使 `d.py` 两版通过；原例 Y 分支本来也不会被这个补丁放行。此处是规格选择冲突，不把“与 gold 不同”当判错标准，也未把尚未执行的原例输出称为实验。

已读相关 from-import、import-all、get_module_symbol、lookup_qualified、__all__、符号序列化与公开回归。Placeholder 延迟解析、复杂循环/daemon/缓存和其他类型的重名符号未穷举，不能据两个参考宣称 gold 全面无回归。当前未发现第二个已成立的 gold 实现缺陷；I2 说明验收保护不足，不等于 gold 自身损坏真子模块。

## 6. 开发条件与原始环境证据（6–15）

环境取自 B5 inventory 的 common 与本题 entry；未读取环境聚合质量分析。install_wave1 `plan.json` 仅选本题 index 53，canonical SHA256 为 `7a8bd1773676e876f92b61416f451d124f1805dae9b39e4df4a7ff1ecc68e7e6`。`E/image.json:2–11` 记录基镜像 digest `b3f866b27cdaaa85800026ad13c38cf762c2f6ebcf03fb24a7d7c351e844969e` 与派生 image ID `e3e933e4d2db3fb698b543dc0b878dbcb24beace775bc9ad3eb25e7a873eab1f`：仅 COPY 离线 wheels、设置 PIP_NO_INDEX/PIP_FIND_LINKS，pins 为 setuptools 69.5.1、wheel 0.43.0、packaging 24.1。`E/status.json:3–22` 的实际 gold 命令显式使用该派生镜像与 install-wave1 recipe，无任务材料/测试覆写。

| 开发需要 | 公开依据 | 已有事实及适用范围 | 缺口与建议最小验证（全部未执行） |
| --- | --- | --- | --- |
| 运行当前源码 mypy，保持正确 Python/PATH/包来源 | setup.py:8–20,195–202；__main__.py:6–12；fastparse.py:49–83 | 历史 grader Python 3.9.19，pytest 6.2.5；ledger 记录 import path=/testbed/mypy/__init__.py | actor 实际 shell、semanal 模块路径、激活与候选生效待验；打印 sys.executable/version、mypy.main/semanal.__file__，再跑公开原例。 |
| 运行/测试依赖与可编辑安装 | mypy-requirements:1–4；test-requirements:1–17；pyproject:1–6；CONTRIBUTING:28–35 | GLOG:561–637 / NLOG:543–619 显示依赖已有、离线 editable build/install 成功及末条 pip 满足依赖；不是只看安装 rc | actor 系统前缀写权不由 grader 推定；仅缺依赖时用准备好的离线资产。库存说明原 build context 在权威主机不存在，当前镜像存在性未查。 |
| 临时四文件目录、缓存、测试临时目录可写 | prompt:10–44；data.py:269–295；test config | 历史两 case 已能创建 fixture 并执行；共享卡仅声明 actor workspace/home 默认权限 | actor 创建目录与写缓存需验；不需要业务资产/远程服务。建议在获准临时根用 PYTHONPATH=/testbed 运行题面两版。 |
| typeshed、module fixture、lib-stub | setup.py:70–73；test README:53–77；modulefinder:732–740 | 公开包有相应 fixture，历史 grader 已实际消费此类测试资产 | actor 读取当前资产待验；无需为本题联网查询或下载业务数据。 |
| 窄公开回归 | test README:47；pytest.ini:21–24；testcheck.py:118–227 | 历史 only F2P/P2P 已运行；并非相关公开边界全过 | 后续可用 `python -m pytest -n0 -q mypy/test/testcheck.py -k 'ReExportChildStubs or NoReExport or NoImplicitReexport'`；不是本轮运行授权。 |
| 编译/网络/提交 | setup.py:77–85（mypy compilation 可选）；本例及 gold 仅 Python 语义代码 | grader deny_all 下离线安装成功；没有 GPU/模型/服务需要 | 准备期固定依赖即可；本题不需 C 编译、Python 2.7 执行、运行期公网。源码修复无需写系统包或不可提交资产。若改文档，Sphinx 构建另按已有依赖验证，本轮未核。 |

两份 ledger 的 line 1 已完整复读，raw-line SHA256 分别：
- gold：`2fc5a2fa7deaca31a1a641bdbded2542ea6a9fbe9ff970219f39912dd4a9dd80`；log SHA256 `e4aeeba767741438779a16c3ca753049183bd412e2dfa822374bf771098603c0`。
- noop：`6848d28605595596f23d421feb05033fead38ec9426d3634c1c40863f913fc7d`；log SHA256 `231d81906905f1f462e655a8b9f534153b9ecd1ca0c66611b17a14fc11ab37e1`。

历史 run ID 为 `er19-iw1-python__mypy-11707-{gold,noop}`。gold `GLOG:662–671` 为 2 passed、test rc=0、reward=1；noop `NLOG:651–668` 为缺 internal_detail 错误、1 failed/1 passed、test rc=1、reward=0。安装末码分别 0，完整日志还显示 editable build/install 完成。执行用户为 rh2grader/54322，候选 apply 为 agent/54321，2 CPU/4 GiB/PID512/tmp1 GiB/shm64 MiB/deny_all；测试时间 4.165/4.311 秒，记录峰值约 126.641/131.801 MB，仅属历史运行，不是 actor 资源承诺。ledger cleanup.removed=true；两份 driver.log:3 均无 open containers/cleanup failures。env_qualification=absent，不能改写成正式资格验收通过。

`GLOG:132–142,357–383` 还显示 HEAD 为指定 base，工作区除 gold 外有镜像预存 `test-requirements.txt` 首行 `types-typing-extensions==3.7.3`。该差异不在 gold 投影中，必须保留在运行条件说明，不能把公开纯 base 导出等同容器初态。`A!src/repoharness2/adapters/slime/replay_grade.py:293–351,435–455` 说明重放将派生镜像同时用于候选与 grader；`A!src/repoharness2/adapters/slime/prepared_task_face.py:336–350` 的正式 rollout 仍从 public.image 取镜像。当前正式 actor 是否消费修复配方、真实 CC 消息/工具、完整环境与可见资产均未知。

## 7. 交付、恢复与评分边界（4、16–17、21–22、29–31）

test patch 只修改 `test-data/unit/check-modules.test`；没有普通业务源码混入测试补丁。历史可信 setup `GLOG:384–424` 恢复该文件到 base、干净应用 official patch、expected=present=1。gold ledger:1 的 projection 只包含 `mypy/semanal.py`，ignored_paths=[]，projectable，故这一合理源码修复没有被恢复覆盖。

`A!src/repoharness2/adapters/slime/prepared_task_face.py:194–211,305–330` 以 test_patch 触碰路径决定恢复/保护，且 test_globs=()。这与“所有测试修改都会恢复”的旧 public_hints 解释不等价。对本题可明确说 check-modules.test 内的候选测试修改将被恢复；不能推定全部测试路径都排除。若禁测操作指令适用，源码路线仍可实施，但常规提交新增回归测试受限；若不适用，正常新回归仍需考虑该具体恢复边界。没有必要额外排除源码文件，additional_exclusions 暂空。

已读 conftest.py、pytest.ini、data.py/testcheck.py/helper，知道它们参与测试收集/执行；未进行控制面攻击或证明这些文件可被篡改评分。原 diagnostics 的单一 official file protection、runner digest 不变只证明该历史 run 的观测，不能泛化为所有候选的防绕过保证。公开包无 .git 不证明实际镜像无答案；镜像文件、安装包、公开祖先历史与实际消息未验，未发现具体本题泄漏证据。共享 parser/隔离平台不在此重审。

## 8. 题目关系、用途与暴露（5、29–30、37–40）

仅审本题。未读取其他题、历史 refs/record 或跨题补丁，不能据同仓/同文件宣称同题、独立题或无泄漏关系。公开 issue 给具体复现和成功期待，没有给修复源码；标题误称可消歧，预期方向冲突则影响可解释性。类型为导入可见性/语义分析 bug；不从补丁短或环境跑通推断模型成功率、训练价值或正式评测准入。

当前材料可用于私有 development_diagnostic 的规格/回归校准；**不建议以未经澄清的原题直接进入优先 actor 探针**。先确定要保留旧语义还是扩展普通文件别名规则，必要时做独立版本的公开澄清与测试补充，不能倒推隐藏测试内容充当题意。历史环境安装问题不应继续作为已证实阻塞重复维修。

**唯一优先下一步：**获授权后，在明确记录条件的 CPU/actor 路径上对 base 与 gold 运行题面原四文件的 Y/X 两版，记录退出码、诊断与实际加载源码；以此让“题面两者成功”与“维护旧规则、两者拒绝”的语义选择成为可审查事实，再裁定公开修订。静态预测 base 为 Y 拒绝/X 接受，gold 为两者拒绝；这尚非实验结果。随后针对 I2 再用上述错误简化候选与公开真子模块正例做窄对照，不为第一优先级删掉独立漏测问题。

## 实际阅读、未查与封存约束

完整读 P 的 prompt/bundle/identity/environment brief，V 七个文件（source_refs/run_refs 是本题材料引用，不是旧调查），本题已封存 public_read；完整读本题 gold/test patch、唯一 F2P 与唯一 P2P、module fixture/types/typing lib-stub。按上列行段读公开导入调用链、文档、相邻回归、开发配置、测试 helper；没有通读全仓或全部 10041 个测试。补读的 checkexpr.py:386–410 与 2082–2144 只是相关成员访问上下文，不当作完整 checker 审计。

环境只读指定 inventory 的 common+本题 entry，再读本题 plan entry/status/image、host grading 第193行、本题两份 ledger 第1行、两份 diagnostics/driver log 和 log 中上述相关区段。归档四个指定成员的 SHA256 均与 inventory 相符：scripts/replay_grade.py（61157146…0311）、slime/replay_grade.py（b8f1fbe2…9fb）、prepared_task_face.py（3a3d7bca…aa27）、spec_vendor.py（8e0037b2…4d41d）。log 内自带 base 的 git show 内容是运行原件的一部分，未查询额外 Git 历史。

未访问环境聚合 analysis_149、其他 task entry、root 聚合、history 目录/历史调查引用、reviewer、未来源码、网络网页/外链、容器/SSH/GPU/模型；没有项目 import/测试/安装/下载/运行，没有改源码、测试、gold、评分或提交，也未使用 quota/reset 或创建子 agent。标准库脚本只做文件读取、JSON/tar 文本解析、哈希与写本稿；首个 inventory 解析因 tasks 为 list 而失败，已改为仅筛选本题，未输出其他任务内容。初次本题文件名枚举过大，后续限于明确文件，不将截断输出当成完整阅读。

本阶段唯一写入为本文件。历史仍封存；等待协调者明确解封后才读本题历史并另写 delta/card/record，不回写本初稿。当前执行成本与 token/费用没有可归属观测，不虚填。
