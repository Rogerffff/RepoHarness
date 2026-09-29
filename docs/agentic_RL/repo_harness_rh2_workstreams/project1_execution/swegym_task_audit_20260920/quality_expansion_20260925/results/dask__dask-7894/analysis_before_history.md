# dask__dask-7894：历史释放前静态主审

判断者：main_pack11_dask；日期：2026-09-25。状态为 **needs_review / static_review**，用途仅 **development_diagnostic**。本稿在阅读任何 history、旧质量结论或 reviewer 产物前形成；只读本题公开/私有包、已封存 public_read.md、中性方法及 run_refs 精确授权原件。本轮没有执行/导入项目、运行测试、访问网络、安装、容器操作或修改题目。历史 noop/gold 运行事实与当前 actor 条件分列。

## 证据路径与版本

下文 ROOT=/Users/roger/Desktop/claude-code-verl-stage0h；P=ROOT/runs/swegym_quality_expansion_20260925/public/dask__dask-7894；Q=同级 private/dask__dask-7894。base 源码行号均相对 P/base。R=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3。

- 计划题面、public_bundle、grading、baseline 指针一致指向 `bf4bc7dd8dc96021b171e0941abde7a5f60ce89f`；base tree `f3f257dc6aabf1b0286de596991c5d49264b31a6`。base_identity 声明429个 Git 跟踪条目、无 LFS 指针/gitlink，含一个软链且无已登记目标缺口；这不是 actor 资产普查。
- gold.patch SHA256 `a9c18255a00d60d785d7bb9cd1cb459503261d5cf669d0bf028db8ce3cbb8f1c`；test.patch `0220c0cf26f78d2a549778bf476bf884d40bcb4ee0deb0c4db1d4f63d0ba08cf`。已核原 gold candidate.patch 与本题 gold 字节完全一致；原件投影只含 `dask/array/overlap.py`。baseline、stage 指定 HEAD 均等于 base。
- 源镜像 tag 为 `xingyaoww/sweb.eval.x86_64.dask_s_dask-7894:latest`；期望 manifest digest 为 `sha256:e66d08cf5c0343503a41646a0a3b027a13562246d0cb7eb28c553e6cbb8c236a`；该组运行 actual image ID=null，不把 digest 当实际 ID。scripts_digest=`sha256:57eda7b39bbd851b8146a797356324cf2ea218fe6db6c64b1dd12d0afa0b03a8`，grader=`swebench-4.1.0+swegym_parsers@242429c1`。
- 题面 Dask `2012.7.0` 与 setup.py 配套 distributed `2021.07.0` 不同，疑似题面笔误；实际旧 grader 报 `2021.07.0+3.gbf4bc7dd8.dirty`、Python3.9.19，而题面报 Python3.8.10。明确 base 的对应性成立，实际 actor 安装版本、消息、初态仍 unknown。

## 公开目标、初态与调用链

题面要求 trim=True 且 drop_axis 非空时，删除 depth/boundary 对应项并按输出轴重新编号。二维例子沿轴0取均值，深度(0,2)，要求 `.compute()` 后长度10。合理目标包括计算值与保留轴对齐，不只修正 shape 元数据。不能把 gold 的具体字典推导式或 Number 导入提升为规格。

`overlap.py:658–674` 为每个输入正规化配置并保留零深度快捷路径；`:691–699` 先 overlap，再 map_blocks，再直接使用最高维输入的原 depth/boundary trim。`core.py:659–686` 已在 map_blocks 输出轴删除位置；`overlap.py:103–120,142–168` 却按输出轴号读取原字典，静态根因明确。`core.py:477–481` 允许 number/iterable 并说明先 drop 后 new；现版本实际实现没有负轴正规化，不能把负轴当已支持目标。

最高维输入选择、同维首个优先是原代码规则；gold 保持它。`overlap.py:285–307,416–433` 在函数执行前生成边界/共享块；删除输出轴不应撤回输入重叠。无深度、trim=False、已有多输入对齐规则是需保留的行为。

## 全部新增断言、逐个 F2P 与 P2P

完整读 Q/test.patch。唯一新增测试 `dask/array/tests/test_overlap.py::test_map_overlap_trim_using_drop_axis_and_different_depths` 参数序列为 ((0,),(1,),(2,),(0,1),(1,2),(2,0),1)。局部 helper `_mean(x)` 调用 `x.mean(axis=drop_axis)`；参考值从同一 Dask 随机数组 x 求均值，候选值先 `.compute()`，最终 `assert_array_almost_equal(expected,y)`。随机数组固定在同一个图中，未见参考端另取独立随机样本；本次未重复执行，不能宣称重复稳定性已验。NumPy assertion 导入见 test_overlap.py:3–6，其外部实现未在授权源码中展开；原失败 traceback 明确检查形状，且该断言比较数值容差。新增测试没有用项目 `assert_eq`，故没有直接验证候选 y 的 chunks、shape 元数据、dtype 和图一致性。

每个参数都有相同两侧参考逻辑；为了让均值等价，被删除轴的 depth 被设为0，其他轴沿用(1,3,2)。边界固定 `(0,"reflect","nearest")`。

| 参数后缀 / 实际 drop_axis | expected 组别 | noop → gold | 原失败证据与解释 |
| --- | --- | --- | --- |
| drop_axis0 / (0,) | F2P | FAILED → PASSED | noop log:774，(10,8) 与 (22,4) 不同；保留轴1、2须移动 |
| drop_axis1 / (1,) | F2P | FAILED → PASSED | :826，(5,8) 与 (5,16) 不同；原轴2须移到1 |
| drop_axis2 / (2,) | P2P | PASSED → PASSED | 只删除末轴，其他轴号不变 |
| drop_axis3 / (0,1) | F2P | FAILED → PASSED | :878，(8,) 与 (16,) 不同 |
| drop_axis4 / (1,2) | P2P | PASSED → PASSED | 只保留原轴0，映射无需移动 |
| drop_axis5 / (2,0) | F2P | FAILED → PASSED | :929，(10,) 与 (22,) 不同；删除顺序非递增 |
| 1 / 标量1 | F2P | FAILED → PASSED | :981，(5,8) 与 (5,16) 不同；约束标量形式 |

noop 的七项状态在日志:675–681；gold 在:711–717。expected 全部5 F2P、75 P2P 已机械逐 ID 对照原日志总结行，无缺席、skip、xfail；noop 5 F2P 全失败，75 P2P 全通过；gold 全80通过。这个逐 ID 状态核查不等于75项语义全部通读。

P2P 语义重点完整阅读：test_map_overlap、zero-depth escape、六个 no_depth 参数、multiarray/defaults/different_depths/uneven_numblocks/block_broadcast/variadic、trim=False defaults、deprecated_signature、no_shared_keys_with_different_depths、overlap_few_dimensions[_small]、四种 trim_boundry、两种 rechunk、test_trim_internal。项目 assert_eq 的检查路径见 array/utils.py:218–362，包含实际 chunks/shape/dtype 检查；它增强已读旧测试，但不能转移为新增降维测试已经检查元数据。相关 map_blocks changed_dimension 测试3065–3126已完整读；它不在本题 expected 文件选择内，也不能证明 map_overlap 的 new_axis 组合。

未完整阅读其余 low-level boundary/overlap、ensure_minimum_chunksize、sliding_window_view/errors 参数测试；其中只有局部片段与全部状态核查。其未读范围不宣称为语义覆盖。

## 需求—断言双向表

| 公开要求或合理旧行为 | 依据 | 断言/测试 | 结论与证据级别 |
| --- | --- | --- | --- |
| drop 后 depth 随保留轴重新编号 | 题面；trim_internal 按输出轴访问 | 新增七参数数值/形状比较 | 核心覆盖；静态＋原真实RH2 |
| drop 后 boundary 随保留轴重新编号 | 题面明确说 depth **或** boundary；_trim 外沿 none 分支 | 新增仅0/reflect/nearest；旧none测试不drop | **缺失**：这些值在裁剪端均落非none分支；不是独立 boundary 约束 |
| 首/中/末轴、多轴、整数输入 | core.py:477,659–660；题目广义drop | 新增七参数；旧 map_blocks 测试 | 部分：标量1覆盖，无整数0、全部删除、空drop专门新增断言 |
| 数值正确，裁剪不只是改元数据 | 题面 shape 例与操作含义 | assert_array_almost_equal | 实际数组覆盖；chunks/元数据缺失 |
| 不drop、trim=False、零深度保持旧语义 | 原分支与旧测试 | 上述已读P2P | 所读场景有正证据，非全部组合证明 |
| 不撤回被drop轴在函数前的重叠 | map_overlap docstring:582–594 | 新测试把drop轴depth置0 | 没覆盖非零drop-depth；旧示例非本次选中的doctest |
| none/非对称depth、多个输入与drop组合 | coerce/overlap公开支持；不是新需求 | 旧测试各自覆盖，未组合drop=True | 缺少交互覆盖；gold保留值无类型变换，未证其回归 |
| 合理不同实现可通过 | 题面只约束行为 | 无源代码/函数名/精确图比较 | 未见强制唯一实现；未执行替代解，不能声称普遍无误拒 |
| 任意new_axis、负轴语义 | map_blocks参数/现代码 | 新增未覆盖 | 邻近边界，负轴非当前明示契约；不新增硬门 |

反向检查：测试要求不同成员数值相等、非递增删除顺序、标量1均可从降维/参数契约解释；对 drop 轴设0只是建立有效均值 oracle 的 fixture，不是让 solver 永远清零这些轴的要求。测试没有要求采用某个内部 helper 或 patch 字节。

## Gold、替代实现与具体问题

完整 gold 只改 import 与 trim=True 分支：挑选已有参考输入，包装标量drop，按输入原序枚举保留轴，重建 depth 和 boundary 连续编号，再调用 trim_internal。映射在用户函数执行后进行，保留 depth 值（含tuple）、no-drop、trim=False、zero-depth逻辑。核心七例与原真实RH2正证据支持局部正确；不能由80通过宣布完整正确。

**I1 / coverage_gap / check25 / open：boundary 重映射未被实际判别。** 如果合法源文件候选只按 gold 重映射 depth，而仍传原 boundary，新增七例所有边界在 trim_internal/_trim 中仍按“不是 none”裁剪，语义上无法区分该不完整实现；已读含none的P2P均不drop，不会补足此缺口。静态可构造公开反例：`x=da.from_array(np.arange(50).reshape(5,10),chunks=(5,5))`，`map_overlap(lambda b:b.mean(0),x,depth=(0,2),boundary=("reflect","none"),drop_axis=0,dtype=float)` 应为 `np.arange(50).reshape(5,10).mean(0)`。正确保留none外边界得到10个元素；只映射depth会在两个外侧再裁2个，静态预测6个。未运行此候选或反例；该问题是漏测，不等于gold回归。

**I2 / coverage_gap / open：降维结果元数据未直接断言。** 新增 y 立即compute，失去检查懒数组shape/chunks机会。只改元数据不能解释已有失败并通过数值断言，但另一类实际值正确/元数据错的候选仍可能漏过。不能要求所有合理实现保持完全相同图或分块；应只验证元数据与实际块一致。

**I3 / boundary_uncertainty / unknown：new_axis/iterator-drop交互。** gold 只考虑删除、不插入新轴；map_blocks 支持先删后增。这个未覆盖组合可能维持旧bug或形成新差异，当前没有构造经验证的base通过/gold失败例；check26保持unknown。单次可消耗iterator作为drop虽符合宽泛iterable文字，但下层也重复使用它，本次不将其硬判为gold独有回归。

合理非gold实现可以抽出映射helper、统一输出轴变换或用已有正规化结构，保持数值与合理元数据即可。未见测试误拒此类路线。额外限制提交文件为gold唯一文件没有依据，故 additional_exclusions=[]；revision_refs=[]。

## 原运行条件、合法交付与可信恢复

引用账本仅 R/ledger.jsonl:7（noop）与:8（gold）。两行 SHA 与run_refs相符。对应日志 `eval_logs/evallog_replay-f216-baseline01-w_ef6aaeb0.eval.log` 与 `_81567ca7.eval.log` 的全文件SHA已核对；阅读内容为授权单题范围的定向区段/关键词，并机械核全部expected状态，不声称全文逐行细读。

历史准备阶段 noop log:210–212 的 git status 为clean，:361 的相对base diff为空；gold :210–217仅overlap.py修改，:366–397实际diff与gold一致。`:213/218 git show` 是基线提交正文，绝非未提交diff。两份证据都是grader staging后的状态；没有当前actor准备前后 porcelain输出、退出码或忽略资产记录。

可信恢复：noop :363–402 / gold :399起对 test_overlap.py checkout至base再git apply；attestation apply_rc=0、expected/restored/present=1、absent=0、irregular空。诊断显示保护1个文件，runner_integrity_changed=false；候选无test-like路径。只证明这两个普通候选的交付/恢复路径，不证明任意攻击均无法伪造结果。两次cleanup账本removed=true、rm:ok。

实际安装命令 `python -m pip install --no-deps -e .`（noop:617，gold:653），RC均0。实际测试命令 `pytest -n0 -rA --color=no dask/array/tests/test_overlap.py`（noop:641，gold:677）。Python3.9.19、pytest8.3.2，源码import path=/testbed/dask/__init__.py。noop测试RC1、gold RC0；原安装耗时2.854/2.623秒，test字段5.785/3.958秒；pytest自身3.90/2.50秒，两者不同计时边界不混用。noop失败都位于目标新断言，无安装失败、缺失expected或跳过。没有本轮执行。

历史policy原值：user=rh2grader、uid=54322，candidate apply_user=agent/54321；cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824、network=deny_all；candidate_writable_prefixes=[/opt/miniconda3/envs/testbed]。budgets candidate_stage_seconds=900、cleanup_seconds=120、grading_deadline_seconds=3600、image_pull_seconds=1800。mem_peak_mb=429.758/295.465，原名原值保留，不推断单位实现或换算。尚无actor同条件证据，不能推断其HOME/PATH/写权限/资源或实际模型成功率。

## 开发条件表（建议均未执行）

| 操作/资产 | 公开依据 | 现有证据适用范围与缺口 | 最小公开命令及预期 |
| --- | --- | --- | --- |
| 实际输入、初态、源文件可写 | user_prompt/public_hints；NON-TEST约束 | 只有计划输入；actor消息/status/diff unknown | 捕获实际消息；`git -C /testbed rev-parse HEAD`、`git -C /testbed status --porcelain=v1`、`git -C /testbed diff -- dask/array/overlap.py`、`test -w /testbed/dask/array/overlap.py`；保留RC和阶段 |
| Python与NumPy，导入工作区源码 | setup.py Python>=3.7、numpy>=1.16 | 旧grader导入成立，actor未知 | `python -c 'import sys,numpy,dask; print(sys.executable,numpy.__version__,dask.__file__)'`；应能导入且指向候选源码 |
| 原MCVE可执行 | 题面具体二维例 | 静态根因＋旧隐藏测试目标失败 | 原样执行公开MCVE；base预期目标shape断言失败，合法修复应成功；不把chunks=(0,)提升为普遍有效元数据契约 |
| 公开窄回归与新boundary区别 | setup extras、conftest、旧测试 | grader选整个overlap文件成立，actor未知 | `python -m pytest dask/array/tests/test_overlap.py -k 'map_overlap or trim_internal or trim_boundry'`；应真正收集运行；另执行I1确定性用户API例 |
| 数据、网络、资源 | MCVE与I1仅本地生成小数组 | 无核心外部数据/GPU需求证据；实际权限未知 | 无需远端服务；准备阶段依赖获取与运行期网络分开，不从静态目录缺失判镜像缺件 |

## 原40项稀疏判断与用途

本稿 by=main_pack11_dask，证据引用为以上节中明确文件/行。1、2：pass限静态任务身份与旧grader目标失败；3：unknown（实际消息）；4：pass限计划NON-TEST规则可表达合法修复，actor权限unknown；6/7/8/9/10：旧grader有局部正证据，当前actor均unknown；11/13：保留上述原条件，不作资格；16/17/18/19/20/21：pass限本题这对历史候选、选中expected与恢复记录；23：pass限drop后配置映射核心；24：unknown但未见实现锁定；25：issue（I1、I2）；26：unknown（无已验证gold新增回归）；27：pass限核心局部、完整性unknown；28：pass限本稿没有把邻近边界新增为硬要求；29：actual actor泄露unknown；31/32：普通对照路径有正证据，攻击面完整性unknown；33–36、38–40未作资格判定。未列项not_checked。尤其check40不能由流程封存或这两题结果推导无漏检/误拒/选择偏差。

公开题面提及已有解和将发PR，但没有给实现正文；base静态导出无.git未来历史。只核本题局部关系，不读跨题材料，重复/留出重叠unknown。审查者已见gold、隐藏断言、本题原grader日志与public_read，属授权私有暴露；不得把本稿或私有包放进独立solver环境。实际actor可见性另核；token/费用未观察为null。

## 阅读范围与唯一优先下一步

完整读：中性 investigator/record_template/check_number_reference/actor_environment_card/actor_development_validation、派发卡、本题user_prompt/environment_brief/public_bundle/base_identity、gold/test patch、grading expected、validation，以及已封存public_read。run_refs/source_refs/environment_record用于本题定位，部分大段输出曾截断，所引用字段已用定向读取补核；未沿历史/共享总结链接扩读。

源码直接阅读：overlap.py 1–168、283–738；core.py445–559、630–812、2371–2405、2430–2450（后两段仅方法文档，未声称完整method）；array/utils.py218–362。测试直接阅读：test_overlap.py1–40、120–168、268–485、650–750（切断的相邻测试仅片段）；test_array_core.py3065–3126。文档array-overlap.rst115–182；setup.py/setup.cfg/conftest.py/CONTRIBUTING.md全读。其余未读源代码/测试、外部NumPy helper和全仓回归均未验证。日志仅授权本题范围、精确ledger行、baseline/stage/projection指定JSON指针与gold候选；无history/reviewer/根结果。

**唯一优先下一步：由任务二在独立私有CPU环境做I1的一组窄对照**：保留base、gold、只映射depth而不映射boundary的候选，执行原选中overlap测试与I1的none边界公开API例，记录actual shape/value/chunks和各RC。它能直接把“静态漏测推断”提升或推翻为实际false acceptance证据，不需全仓测试或GPU。本主审不执行该步骤；本稿封存后不改写，报告SHA后等待root明确history release。
