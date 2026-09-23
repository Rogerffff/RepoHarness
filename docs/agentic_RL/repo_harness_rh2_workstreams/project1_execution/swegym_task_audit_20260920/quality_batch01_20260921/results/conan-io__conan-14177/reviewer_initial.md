# conan-io__conan-14177：独立初判

2026-09-21。第一阶段原件复核，未读本题公开读者、主审、旧调查或其它总结；未运行项目代码、测试、安装、Docker、SSH 或模型。只写本文件，不改原件。此上下文此前完成了 15422 复核并见过该题 gold/私有测试；本题判断重新依据 14177 的精确 base 与原件，未读取任何跨题主审结论。本文是静态分析及既有日志复读，不是独立复现。

## 初判处置

**needs_review / static_review；优先校准公开规格与验收，不建议把当前题直接放入普通模型解题探针并将 reward 当作题面完成。** 题面明确提出 `apply_conandata_patches(conanfile, verbose=False)`，在 `verbose=True` 时逐项记录补丁文件；gold 仍保留单参数签名，测试却要求默认调用输出新增日志，还要求直接 `patch()` 调用改变旧文案。这个偏离不是一般漏测或环境故障。

同时存在独立的覆盖限度：有描述的补丁未保证记录文件名；批量测试只断言日志、选择版本和不变性，不检查实际应用；真实文件内容回归不在评分集。已有 gold=1 的 grader 记录不能消除这些质量问题。没有发现材料错配或正常生产修复被评分恢复覆盖的障碍。

## 原件与范围

所有路径以 `${REPO_ROOT}` 为根。`PUBLIC`=`runs/swegym_quality_batch01_20260921_v2/public/conan-io__conan-14177`，`B`=`PUBLIC/base`；`PRIVATE` 为同批 private/conan-io__conan-14177。`L`=`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/ledger.jsonl`；同 worker 的日志 `N`=`eval_logs/evallog_replay-f216-baseline01-w_be9aeaa5.eval.log`、`G`=`eval_logs/evallog_replay-f216-baseline01-w_7731a01a.eval.log`。

已读：既有 reviewer 角色卡及三份共用方法；本题 user_prompt/public_bundle/base_identity/environment_brief；test.patch、gold.patch、grading、validation、run_refs、source_refs、environment_record。environment_record 仅作元数据，其引用的 scope_reconciliation 总结未打开。读完 B/conan/tools/files/patches.py、B/conans/test/unittests/tools/files/test_patches.py 全文；追读 patch 导出、ConanOutput:1-190、ConanFileMock/RedirectedTestOutput、redirect_output；相关 functional/tools/test_files.py:1-375、functional/test_third_party_patch_flow.py:1-190、unittests/tools/files_patch_test.py:1-155；README 测试说明、test/README、requirements 三文件、pytest.ini、conftest 相关入口。未审全仓，也未逐行分析日志中 `git show` 打印的无关 base 提交差异。

## 八方面核对

### 1. 公开要求

题面不是泛泛要求“更多日志”：它给出新增布尔参数及默认值的签名 diff，并明确说 `verbose=True` 时输出两个 patch 文件名，以便构建日志记录应用了哪些补丁。可接受文字风格不必锁死 `Applying:`，但可调用该参数、默认不引入这组可选文件日志、启用时可辨识每个选中 patch，是公开要求的重要组成。

base 已有其它日志：B/patches.py:42-48 在有 patch_type 或 patch_description 时输出 `Apply patch...`；71-105 的 `apply_conandata_patches` 按当前版本/列表选取条目并调用 patch。因此 `verbose=False` 不应被扩大解释成整段执行绝对静默，已有元数据日志及错误日志应继续保留。公开 `ConanOutput.verbose()`/CLI `-v`（output.py:14,67-90,170-181）是另一种日志级别机制，不会让没有 verbose 形参的函数自动接受题面参数，也没有公开依据把题面改成默认 info 日志特性。

### 2. 材料与初态

public、grading 与 base_identity 的 base 为 `b43eb83956f053a47cc3897cfdd57b9da13a16e6`；tree=`7de5dff0544d679a376d53ff7ad501f9505f068e`，973 个跟踪条目，物化记录称字节已核、无 .git。只读标准库比较 source_refs 指向的三份 S2 JSONL 第 36 行，本题 public/grading/validation 均等值；test.patch/gold.patch 与内嵌值一致。

base 的 apply_conandata_patches 只有一个形参；无描述/类型的 file patch 没有这组 info 日志（patches.py:42-48,71）。N:135-139 显示 clean、精确 base；N:524-611 中三个失败对应当前新日志断言，支持初态缺少评分所要求的输出。**这不等于日志已复现题面 verbose=True 调用；该调用未被执行。**

### 3. 全部新增断言、F2P 与需求映射

test.patch 只修改一个纯测试文件的三个既有测试，不改生产源码。全部 F2P 就是这三项；所有改动、原断言和 fixture 已读。

| 需求或行为 | 来源 | F2P/P2P 实际断言 | 判断 |
| --- | --- | --- | --- |
| 新签名接受 verbose，默认 False，True 才启用额外文件日志 | 题面签名 diff 和 when verbose=True | 没有任何参考测试传 verbose；两个批量 F2P 都默认调用，并要求新增文件日志 | 核心 API 未测，默认行为与题面预期冲突；gold 未实现参数 |
| 逐项识别所应用的 patch 文件 | 题面两条文件日志及动机 | `test_multiple_no_version` 和 `test_multiple_with_version` 新增包含首个无描述文件名的断言 | 部分覆盖；第二项有描述，仅检查描述而不检查其文件名 |
| 默认直接 patch() 输出应变成 `Apply patch (file): patch_description` | 无相应公开新增要求；base 原测试期望不含 `(file)` | `test_single_patch_description` 从旧精确字符串改为新精确字符串，整段输出必须相等 | 验收新增了题面之外的直接 API 文案约束；合理的 wrapper-only 解会保持旧行为 |
| 批量描述/自定义类型仍可见 | base patches.py:42-48 与旧测试 | 两个批量 F2P 将原 backport 描述的全字符串相等改为 `in`；已有 `single_patch_type`、`single_patch_extra_fields` P2P 仍精确检查 | 旧元数据输出部分保护；新增日志的顺序、额外重复和完整文件身份没检验 |
| 按版本选择，不修改 conan_data | base patches.py:88-100 | with_version 保留：version 缺失的 AssertionError 及确切文案；不匹配版本输出长度为零；1.11.0 两条日志；末尾 conan_data 相等 | 有选择/不变性保护；没有实际调用次数/每个 patch 应用断言 |
| patch 文件、字符串及路径/参数转发保持正确 | base patches.py:54-68 | 10 P2P 全文已读，详见下段 | 直接 patch() 的 mock 调用受到保护；批量 wrapper 的调用和真实文件修改没有被这些 P2P 保护 |

`mock_patch_ng` 将 fromfile/fromstring 替换为同一个 MockPatchset（test_patches.py:12-36）。apply() 总返回 True，并仅覆盖记录最后一次参数。F2P 并非错误地读取未执行代码的日志：它们确实调用生产 helper 和 ConanOutput。但两个批量 F2P 从不检查 mock 的 filename/string/apply_args，也不读真实补丁文件，更不检查源文件修改。不能以“3 F2P 通过”证明多个补丁真的应用。

10 P2P 的具体覆盖：`single_patch_file`、`single_patch_file_from_forced_build` 核相对/绝对路径；`base_path`、`apply_in_build_from_patch_in_source` 核 root 与 source/build 的关系；`single_patch_string` 核 UTF-8 bytes 和参数；`single_patch_arguments` 核 strip=23/fuzz=True；`single_patch_type`、`single_patch_extra_fields` 核显式元数据文案；`single_no_patchset`、`single_apply_fail` 核解析/应用失败异常。它们都直接调用 patch()，未调用 apply_conandata_patches。无参考 skip。

### 4. 合理解的误拒与错误解的漏收

一个合理公开实现是在原批量 helper 加 `verbose=False`，在每个选中 file 条目即将应用时按 verbose 输出其原始文件名，保持现有 patch() 的日志格式、参数与异常行为不变。它满足题面 API、开关和原日志兼容性；静态上仍会失败于三条当前 F2P：默认调用不打印新增文件日志、直接 patch() 不增加 `(file)`。这是具体可区分的误拒候选，**尚未运行该候选或取得其 RH2 得分**。

反方向，gold 已在既有 grader 中得满分，但 apply_conandata_patches 的签名未改。普通 Python 参数绑定下，题面 `apply_conandata_patches(conanfile, verbose=True)` 会在函数体开始前遭遇不接受关键字的 TypeError；这是源码可直接判断的 API 不满足，非本轮运行捕获。

另一个独立漏测候选是保持原版本选择/不变性、只输出批量日志却不调用 patch()。三个 F2P 与直接 patch() 的 10 P2P 缺少能直接排除它的批量应用断言。此处只登记静态候选，不声称已经证明它满分。修订时用真实小补丁的文件结果或记录每次调用的 spy，可以校准此问题，而无须改变为某个私有 helper 的固定调用形状。

### 5. gold 完整性与相关回归

gold 仅改 patches.py 两处：给 patch_type 增加 file/string 后备；批量 file 条目没有 patch_description 键时，以原 patch_file 作为描述。应用路径 join、entry.copy、版本选择、patch_string 分支、失败异常都基本沿用，未新增依赖或未交付文件。

对当前公开题面，它仍缺 verbose 开关，并改变默认及直接 patch() 输出。后备类型还使直接 patch_string 也默认输出 `Apply patch (string)`；已有 P2P 不限制该输出。不能将这种扩大范围的日志改变自动当成题面必需功能。

文件识别还有独立边界：一旦条目已有 patch_description，gold 不附加文件名；值为空字符串或 None 时也因“键存在”而不做文件名后备，patch() 最多输出类型。两个批量 F2P 的第二个文件恰有描述，但只断言原 backport 描述。这不足以实现题面示例的每个文件身份记录。实际 patch_ng 可能另发诊断消息，不能依赖其偶发诊断当作每次成功应用的稳定文件记录；本轮未运行实际 patch_ng 日志验证。

相关公开调用者已查：functional/tools/test_files.py:179-253、288-346 覆盖 recipe 的批量 helper、source 子目录、相对 base_path、字符串条目；其中部分仍 mock patch_ng，且不在本题 P2P。`test_patch_real`（120-175）通过真实补丁修改文件，`functional/test_third_party_patch_flow.py:10-109` 通过批量 helper 连续修复三个文件内容错误；它们同样不在评分运行范围。后者使用本地 Git 创建 diff，但可用直接写好的最小 diff 验证本题而不要求 Git。没有依据认为本题需编译器、外部补丁命令或在线源码资产。

### 6. 开发条件

公开实现入口 `conan.tools.files.apply_conandata_patches` 由 files/__init__.py:5 导出，开发路径明确。需要可导入工作区 Conan、patch-ng（requirements.txt 固定范围 >=1.17.4,<1.18）及 Python 测试依赖；redirect_output 来自 tools.py，导入它还涉及 mock/WebTest/bottle 等（tools.py:20-49），不应以测试很短就省略这些依赖。

| 操作/资产 | 公开依据与已有证据 | 当前缺口及最小验证（均未执行） |
| --- | --- | --- |
| 正确解释器、源码导入及测试辅助类 | README:90-114、requirements；grader 包来源 `/testbed/conans/__init__.py` | actor 下记录 id、pwd、PATH/sys.executable，打印 conan/conans/patch_ng 来源，并导入 ConanFileMock/redirect_output；不能以 grader 身份成功代填 |
| 窄公开旧测试 | 本题 base test_patches.py 全文及 fixture | actor 可运行 `python -m pytest -n0 -rA conans/test/unittests/tools/files/test_patches.py`；这是未加私有补丁的公开基线，预期原版通过。原测试对默认文案的保护也应纳入解释 |
| 公开 API 调用 | 题面签名；base helper:71 | 在临时脚本以空 patches 列表调用 verbose=True/False，首先区分 API 参数不支持与环境 ImportError；随后两个本地 file diff 检查日志及文件结果 |
| 真正应用本地补丁 | patch-ng 调用；公开 test_patch_real | 在临时目录写小文本及 diff，不需 zlib 下载、ConanCenter、账户、模型服务或编译器；actor temp/home 权限待验 |
| 安装/网络与资源 | requirements 三文件；N/G 安装均 already satisfied；旧 grader deny_all、2CPU/4GiB | actor 实际环境及离线依赖是否已备未知；若缺包应准备阶段预置，而不是让 solver 假定联网安装或系统前缀可写 |

常规修复只需改生产 Python 文件，使用临时脚本验证也无需修改受保护测试。public_hints 中禁改测试操作指令的实际呈现仍待核；本题正常解法不依赖取消该限制。“conda 已激活”是声明，“所有测试修改永不计分”也不能取代本题实测恢复路径。

### 7. 既有运行与交付评分边界

只读核对 N SHA256=`07fdea4883056813e8de95915344bda63a1a31cc2d1233192bec935b5d0ea1d3`，G=`0d4867d9271b23c7fa35ed067914021b63934f02785a3b5540f235b8d2450772`，与 run_refs/L 一致。gold.patch SHA256=`8c14b0347a1b722381729138a21265e1861dd3039d287280cb94b9684a8c5d7d`，与 validation/L:16 一致。

- L:15 / N:515-634：13 collected，3 failed、10 passed，rc=1，F2P=0/3、P2P fail=0/10、reward=0。三个失败均为新增文案/输出断言，并无安装失败；N:464-505 的 Python 依赖已满足、install rc=0。
- L:16 / G:547-596：13 collected、13 passed、rc=0，F2P=3/3、P2P fail=0/10、reward=1。G:288-314 的实际候选差异与本题 gold 一致；G:557-577 还显示直接 patch() 在成功或失败前增加了 `(file)` 输出。
- 两条账本参考 missing/skipped 均空，parser 计数13与当前参考总数一致。原镜像与 public digest 相符，derived_recipe=null；grader 是 rh2grader/54322、deny_all、2CPU/4GiB，Python3.10.14/pytest6.2.5。env_qualification=absent、image_id_actual=null，不能补成当前 actor 验收。

N:284-324 / G:316-356 显示恢复并应用官方补丁的路径仅为 `conans/test/unittests/tools/files/test_patches.py`。L:16 的生产投影包含 `conan/tools/files/patches.py`、ignored_paths 为空，不阻断正常修复。test_patch 未夹带普通源码。不新增额外路径排除；未重审统一 parser/隔离/清理链，不声称完整防篡改或镜像无泄漏。

### 8. 关系、用途与未查项

本题为公开提出新 API 的日志功能请求；题面提供签名与示例，属于明确规格，不是完整实现答案。虽已审同仓 15422，但两题具体文件/功能不同；没有在本轮建立跨题派生关系，也没有读取其它题补丁来作去重。真实镜像的 Git 历史、未跟踪文件和预装资产未核，静态包无 .git 不代表实际不存在这些信息。

已见 14177 gold/隐藏测试和评分日志，不能再担任本题未见答案的 solver。不得由静态题意冲突推断模型能力低或成功率；也不得因运行条件旧账本成功就宣布此题质量合格。

## 唯一优先下一步

先用获授权的 CPU 定点对照将公开语义与评分差异具体化：gold 的 verbose=True 调用；遵循公开签名、保留默认旧日志的最小替代解；对照每个版本/列表中的两个真实小文件补丁（含有描述、无描述），检查默认/False/True 三种调用的额外文件日志与文件结果，并单独记录官方评分。这些实验尚未执行；已有 gold=1 与静态签名足以登记高影响语义冲突，不必先跑大规模模型才能处理。

若后续确认应采用“默认增强类型/描述日志”这一不同需求，应显式修订公开规格并保存独立题目版本；若保留原请求，则需修订测试及参考实现，使 verbose 开关与文件识别得到验证。不能静默删除题面开关，也不能为保 gold 满分把所有隐藏字符串直接抄成新题面要求。批量真实应用漏测作为独立问题保留，不因解决规格冲突而删去。

第一阶段至此封存，等待协调者开放第二阶段材料。
