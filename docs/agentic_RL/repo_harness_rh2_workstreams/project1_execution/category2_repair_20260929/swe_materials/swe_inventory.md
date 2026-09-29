# SWE 第2类28题：分批材料与验收顺序

整理：2026-09-29。**当前28题均保持第2类；本页是材料计划，不是正式评分修复完成。** 首包为两道mypy，直接复用公开旧测试。常规公开依据修订已在本轮授权内，当前未发现新的必须用户选择事项。D6正式版本入口由共用机制负责人核，本目录不实现公共机制。

只按固定起始SWE28题推进，不领取第3类。每个小包完成新版本验收与独立复核即可逐题交接，不等全28题。旧“受限比较＋事后审计”不是普通探针豁免。

材料入口：[首包说明](first_mypy_bundle/README.md)、[首包验收计划](first_mypy_bundle/acceptance_plan.md)、[完整机器清单](swe_inventory.json)。

## 顺序小包

| 顺序 | 范围 | 准备重点 |
| --- | --- | --- |
| 01 | 现成 mypy 旧测试引用：python__mypy-10424、python__mypy-17071 | 复用现成节点、安装有效性、D6选择器和引用联动。 |
| 02 | 已有对照的原五题余项：pydantic__pydantic-8511、conan-io__conan-15422 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 03 | 地区、对象身份及默认值：getmoto__moto-5406、getmoto__moto-6114、pydantic__pydantic-8793 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 04 | 内外行为及返回参数类型：Project-MONAI__MONAI-2446、Project-MONAI__MONAI-5932、dask__dask-7656 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 05 | 图像标签及真实返回像素：Project-MONAI__MONAI-4583、Project-MONAI__MONAI-6975 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 06 | 真实构建与双 profile：conan-io__conan-11594、conan-io__conan-13230 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 07 | 非示例相等行为：pydantic__pydantic-5662、pydantic__pydantic-6283 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 08 | 已有公开行为的核心缺口：iterative__dvc-5839、iterative__dvc-6954、python__mypy-10174 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 09 | 完整投影与标签归属：getmoto__moto-5960、getmoto__moto-6408 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 10 | 训练模式与完整配置键：Project-MONAI__MONAI-3715、conan-io__conan-12397 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 11 | 节点身份及文件目录成对控制：iterative__dvc-4166、pandas-dev__pandas-48106 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |
| 12 | 公开复现与合理解接受性：python__mypy-15184、pandas-dev__pandas-50319、dask__dask-7138 | 沿用已有环境与对照，按下列逐题缺口作窄修订。 |

顺序反映材料成熟度与准备成本；同包不是可盲目并发的授权。root维护唯一远端队列。共用入口未验收时可以继续准备后包材料，不能用私有后检代替正式评分。

## 逐题处理

### 01 · python__mypy-10424

**缺口：** 关闭收窄的错误补丁得 1，公开回归四项失败；安装子命令 rc=1 曾被段末 rc=0 掩盖。
**已有依据：** 已实证 C1 原 reward=1 且四项旧收窄失败；gold 保护旧行为。
**所需准备：** 复用两个现成 TypeEquals case，追加 P2P 和实际 selector；保留原 F2P 与题面；重新绑定可离线 editable 安装的派生 grader。
**建议矩阵：** noop→0（F2P失败）；gold→1；C1_disable_narrowing→0（新P2P失败）。
**附加阻塞：** D6消费者、固定离线安装及逐步rc未验；不能将09-25失败安装当已完成。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 01 · python__mypy-17071

**缺口：** 禁用 unbound 检查可得 1，却接受真实未绑定类型；安装子命令失败仍需单列。
**已有依据：** 已实证 C1 原 reward=1；真正unbound被放过，testUnboundTypeVar失败；四份历史成功模型补丁已有负例复核。
**所需准备：** 复用 check-typevar-unbound.test::testUnboundTypeVar；保留TypeGuard/TypeIs两F2P及两P2P；核collector文件层和安装。
**建议矩阵：** noop→0；gold→1；C1_disable_check→0；可选q36_a1旧成功工件→1（只在接受性需要时加一行）。
**附加阻塞：** D6与离线安装未在当前链验；旧summary rc0是echo/tail外层值，必须读诊断正文。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/python__mypy-17071/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 02 · pydantic__pydantic-8511

**缺口：** gold 在字段继承组合引入 TypeError，窄修可用；两者原评分均 1，安装也并非全成功。
**已有依据：** R4：gold与窄修原分均1；gold引入三类继承TypeError，窄修原例/继承均过。
**所需准备：** 复用R4三类无本地注解继承控制与只读本地annotations窄修；固定Python3.8及pydantic-install配方，先处理pdm/make失败。
**建议矩阵：** noop原例失败；窄修→1；原gold→0（继承保护）；保留正常repr/default/factory。
**附加阻塞：** 正确对照存在；安装pdm rc127、make rc2须收口，不能为保gold删护栏。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/pydantic__pydantic-8511/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 02 · conan-io__conan-15422

**缺口：** 真实得 1 的候选漏掉默认 jobs 或多配置路径；开发工具与 G1 exec 已修。
**已有依据：** 已有12个正式1；3份真实候选漏默认jobs或多配置；DS a4纯生成器差异按既定范围不判错。
**所需准备：** 复用CMake3.23.5、真实conan入口及G1修复；默认CPU helper结果、显式2/7、多配置追加纳入断言，并核生成schema能被所用CMake读取。
**建议矩阵：** noop→0；gold及已核正确候选→1；Coder a1/a3与DS a1→0；Q36 a2单核schema兼容原因。
**附加阻塞：** 须保留既定生成器范围；工具已修勿重列缺失，schema4兼容风险不能自动算已失败。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/conan-io__conan-15422/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 03 · getmoto__moto-5406

**缺口：** 恒返回 East2 ARN 的错误补丁得 1；公开 East1 行为失败。
**已有依据：** CPU18：noop0/gold1/恒East2错解1；East1公开行为失败。
**所需准备：** 优先复用公开test_create_table_standard的East1 ARN断言，与East2 F2P同版选入；复用原actor/27项证据。
**建议矩阵：** noop→0；gold→1；constant_east2→0（East1 ARN）。
**附加阻塞：** D6新引用实际执行；不扩成全流/备份/CloudFormation回归。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/getmoto__moto-5406/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch05/results/getmoto__moto-5406/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 03 · getmoto__moto-6114

**缺口：** 按 B ARN 返回 A、数量仍为 1 的错误补丁得满分。
**已有依据：** CPU18：noop0/gold1/按B ARN返回A错解1；正式35项只核长度。
**所需准备：** 把已有双集群请求B/返回Identifier和ARN断言并入版本；复用离线构建资产层。
**建议矩阵：** noop→0；gold→1；返回首对象→0；原名称查询和旧列表行为保留。
**附加阻塞：** 不把creating/available状态差异整包判错；跨账号/服务ARN未定范围不混入。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/getmoto__moto-6114/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/getmoto__moto-6114/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 03 · pydantic__pydantic-8793

**缺口：** 强制 required 的补丁得 1，却破坏公开默认值 5 和两项旧测试。
**已有依据：** CPU18：noop0/gold1/forced_required1；默认5和两项公开旧测试被破坏。
**所需准备：** 复用create_model+Annotated真实默认值/工厂控制；优先用现成default测试能否直接入P2P，否则将已跑最小断言独立版本化。
**建议矩阵：** noop→0；gold→1；forced_required→0（M().x或is_required）。
**附加阻塞：** 保持内外Field默认优先级争议在范围外；不要求内部字典形状。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-8793/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8793/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 04 · Project-MONAI__MONAI-2446

**缺口：** NiBabel 开发缺口已修；只保外部数组顺序、破坏内部 shuffle／cache 的补丁得 1。
**已有依据：** CPU18：noop0/gold1/只保护外部数组列表错解1；内部shuffle/cache顺序错误。
**所需准备：** 复用NiBabel修复和同输入内外顺序/缓存矩阵；使用确定随机种子或受控排列核实际行为。
**建议矩阵：** noop→0；gold→1；不打乱数组列表候选→0（内部shuffle/cache）。
**附加阻塞：** 4GiB出现回收压力须保留；不把私有root行为等同actor权限。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-2446/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-2446/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 04 · Project-MONAI__MONAI-5932

**缺口：** 反转顺序的错误修法得 1，另一长短引用顺序失败。
**已有依据：** CPU18：noop0/gold1/反转引用顺序错解1；长名在前原本正常路径退化。
**所需准备：** 复用short_first/long_first同一表达式双顺序，核真实解析值；原解析18旧测已验。
**建议矩阵：** noop→0；gold→1；reverse_order→0（long_first）。
**附加阻塞：** 别用只无异常替代真实数值；保留requirements初态。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-5932/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-5932/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 04 · dask__dask-7656

**缺口：** 错误候选改变传给 delayed 函数的 dataclass 参数类型仍得 1；题面自带修法提示。
**已有依据：** CPU18：noop0/gold1；opaque错解0，另一候选1但传给delayed函数的dataclass类型改变。
**所需准备：** 复用现成类型和字段值诊断；加入被调用函数实际收到的参数类型及值，而非只验最终字符串。
**建议矩阵：** noop→0；gold→1；类型退化→0；已被拒opaque不必无变化重跑。
**附加阻塞：** 准备曾300秒超时，采用已验setup900；题面修法提示如实披露。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/dask__dask-7656/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7656/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 05 · Project-MONAI__MONAI-4583

**缺口：** 只修 2D 的补丁得 1，公开稀疏 3D 标签仍错误；CPU 范围已固定。
**已有依据：** CPU18：noop0/gold1/2D-only1；稀疏3D标签被误算背景。
**所需准备：** 复用2D/3D、numpy/torch、真实标签及dtype矩阵，固定CPU身份；把3D护栏入正式引用。
**建议矩阵：** noop→0；gold→1；2D-only→0（稀疏3D标签）。
**附加阻塞：** CPU校准不声称CUDA已验；尊重dtype/device已有条件。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-4583/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-4583/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 05 · Project-MONAI__MONAI-6975

**缺口：** 退化补丁正确打印 lazy／resample 信息却丢掉返回图像，仍得 1。
**已有依据：** CPU18新正式0/1/1；退化日志正确但丢弃返回图像；旧setup900超时另列。
**所需准备：** 复用direct/Dataset×True/False/None六行矩阵，核实际像素和有效lazy语义，不约束唯一resample调用次数。
**建议矩阵：** noop→0；gold→1；丢弃返回值候选→0。
**附加阻塞：** 沿用已验setup1800版本，测试预算不混改；4GiB压力与并发变化记录。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-6975/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-6975/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 06 · conan-io__conan-11594

**缺口：** Ninja 已补；Release 变 Debug 的错误补丁仍得 1。
**已有依据：** CPU18：补Ninja后actor可真实配置；noop0/gold1/丢配置1，实际Debug而非Release。
**所需准备：** 复用Ninja1.10.2.4离线wheel、未改CMake3.22.1及真实CTest marker；核构建配置与marker内容。
**建议矩阵：** noop→0；gold→1；drop_configuration→0（Release未执行）。
**附加阻塞：** 需要真实构建资产与双Ninja节点绑定；只命令字符串不够。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/conan-io__conan-11594/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-11594/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 06 · conan-io__conan-13230

**缺口：** Android-only 修法得 1，公开 Linux host 路径仍生成错误 xcrun flags。
**已有依据：** CPU18：noop0/gold1/Android-only1，公开Linux host仍生错误Apple flags。
**所需准备：** 复用Macos build/Linux host双profile的真实conan CLI输出；核精确flags并保留有意raise终止。
**建议矩阵：** noop→0；gold→1；Android-only→0（Linux flags）；原Android参考保留。
**附加阻塞：** 无需无关SDK/交叉编译；CLI退出1按目标raise解释，不当环境失败。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/conan-io__conan-13230/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13230/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 07 · pydantic__pydantic-5662

**缺口：** ANY-only 修法得 1，一般 matcher 委托仍错误。
**已有依据：** CPU18：noop0/gold1/all_nonmodels_equal0/any_only1，普通matcher未收到委托。
**所需准备：** 复用普通true/false/NotImplemented matcher行为，保留dict/object及7项旧比较护栏。
**建议矩阵：** noop→0；gold→1；any_only→0；all_nonmodels_equal→0。
**附加阻塞：** 不以精确内部调用次数定义正确性；setup900版本已验。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-5662/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-5662/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 07 · pydantic__pydantic-6283

**缺口：** 验证式构造退化已被原 P2P 拒绝，但目标相等性仍只直接验示例；非 42 控制已跑。
**已有依据：** CPU18：noop0/gold1/validate_construct0；非42 TextRoot补充base失败、gold与退化相等。
**所需准备：** 把已验TextRoot另一合法值的相等断言入版本，保留原test_construct/test_construct_nested无验证护栏。
**建议矩阵：** noop→0；gold→1；validate_construct仍0；可用示例特判候选校准新增断言（尚未执行）。
**附加阻塞：** 不能因旧退化已拒绝就免补核心非示例；不要求内部__dict__精确结构。
**材料：** [result.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-6283/result.md)；[card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-6283/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 08 · iterative__dvc-5839

**缺口：** 开发依赖已修；模型失败已确认为舍入语义过度修改，没有已证评分假阳性。
**已有依据：** 默认/4/8真实CLI已有行为证据及10个成功候选；硬编码8未评分。
**所需准备：** 复用pathspec0.8.1和固定YAML，直接核输出小数位数/数值，维持默认5；准备硬编码8窄候选。
**建议矩阵：** noop→0；gold/真实成功候选→1；硬编码8→0预期未实测。
**附加阻塞：** 标量float旧不舍入不当新缺陷；不改为有效数字。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/iterative__dvc-5839/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 08 · iterative__dvc-6954

**缺口：** pygit2 已补；六条有效模型尝试通过公开数值与锁文件检查，另一次为 infra。
**已有依据：** 公开负int/float/nested、lock更新已验；int-only退化未评分。
**所需准备：** 复用pygit2 1.14.1，负float及容器负值用parse→run/repro→lock实际输出验证，新增引用避免旧参数空白合键。
**建议矩阵：** noop→0；gold/成功候选→1；int-only→0预期未实测。
**附加阻塞：** 非法调用/算术表达式不扩题；旧坏行gold shell引号错误不能当DVC缺陷。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/iterative__dvc-6954/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 08 · python__mypy-10174

**缺口：** 公开开发验证通过；过宽关闭比较检查只是尚未运行的疑点。
**已有依据：** 正式actor原例复现/32旧测通过；公开同开关负例缺正式保护，错解得分未实测。
**所需准备：** 从已有公开strict-equality用例选同no-strict-optional条件的不重叠成员检查，或复用已提1 in tuple[str]行为；固定派生安装与dirty初态。
**建议矩阵：** noop→0；gold→1且真不重叠报警；关闭全部比较候选→0预期。
**附加阻塞：** 不要把未执行错解写误奖；切换strict-optional须清除相反inline flags。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/python__mypy-10174/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 09 · getmoto__moto-5960

**缺口：** GSI KEYS_ONLY 核心断言缺失；参数节点合键已见，尚未造成当前对照错分。
**已有依据：** GSI INCLUDE/KEYS_ONLY公开行为已有base/gold；KEYS_ONLY评分缺失，错解未评分；158执行/157解析有合键。
**所需准备：** 加入两种GSI scan全部项目字段集合/数量和索引投影后原表保持；同时核引用全节点身份。
**建议矩阵：** noop→0；gold→1；漏KEYS_ONLY→0预期；只复用一份目的明确错解。
**附加阻塞：** LSI保持原参考；额外范围争议不扩大；先修已确认节点身份。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/getmoto__moto-5960/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 09 · getmoto__moto-6408

**缺口：** 公开开发条件可用；首项断言未完整约束 tag 归属，尚无错误候选得分证据。
**已有依据：** 原actor题面失败，29旧测过；gold修两已有镜像迁移；首项断言不保护完整tag归属。
**所需准备：** 用两已有manifest核全部标签集合、唯一归属和来源其它tag；准备只排序、误删其它tag候选。
**建议矩阵：** noop→0；gold→1；只排序/全删来源→0预期。
**附加阻塞：** 新manifest目的邻接旧缺陷另列范围，不能静默扩入本包。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/getmoto__moto-6408/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 10 · Project-MONAI__MONAI-3715

**缺口：** 公开 train 目标没有决定性验收，当前主要覆盖 eval。
**已有依据：** 公开train核心目标缺验收；旧两参考只保护eval/空构造；gold静态合理。
**所需准备：** 先备CPU合成数据和Ignite，定义forward时training/梯度及with退出恢复断言，保留eval/枚举。
**建议矩阵：** noop→0；gold须先验正对照；eval-only或强制eval→0预期。
**附加阻塞：** actor与可信train运行正对照仍待；未通过不转第1类，不要求完整GPU训练。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-3715/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 10 · conan-io__conan-12397

**缺口：** cpp 键匹配不完整、Linux native Clang 路径缺测，公开目标明确。
**已有依据：** cpp_link_args子串可匹配objcpp_link_args；Linux native缺测，只有静态候选。
**所需准备：** 原Apple与公开Linux clang/libc++配置按完整键读取；复用公开生成helper，不安装无关完整编译器。
**建议矩阵：** noop→0；gold先验证→1；objcpp-only及Apple-only→0预期。
**附加阻塞：** 实际actor配置生成待验；顺序接受性只在相关差异发生时调查。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-12397/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 11 · iterative__dvc-4166

**缺口：** pathspec 与 networkx 开发修订已验；需要固定与 grader 一致的版本及初态。
**已有依据：** pathspec/networkx actor已修；两参数节点合键，文件/目录成对判据仍不足。
**所需准备：** 固定pathspec0.8.1/networkx2.3兼容配方及setup.py初态；绑定完整节点，构造混合状态和同名普通文件/目录。
**建议矩阵：** 旧gold→1；noop→0；只裁尾/候选应被文件目录护栏拒；混合PASS/FAIL不可覆盖。
**附加阻塞：** 公共parser/绑定消费者由D6负责人核；不回溯修改旧分数。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/iterative__dvc-4166/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 11 · pandas-dev__pandas-48106

**缺口：** 安装及三组 Period 绑定已修；两组 tz 别名仍合键，当前成员均通过。
**已有依据：** pandas_meta_v3及3组Period绑定已验，剩两tz别名仍各合并2/4节点，六节点均PASS。
**所需准备：** 复用现行安装/参考版本；列全六tz节点，补完整身份绑定及混合状态/缺席回放，保留3组Period。
**建议矩阵：** noop0/gold1原事实保留；新绑定gold1；混合失败/缺席必须如实拒绝，正常六PASS接受。
**附加阻塞：** 尚无候选错分实测；合成摘要控制不冒作真实候选；重编译源码生效检查。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/pandas-dev__pandas-48106/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 12 · python__mypy-15184

**缺口：** 题面原例在 base 上已成功；公开替代复现可用，旧决定保留该限制，现按普通探针标准先修说明。
**已有依据：** 原SupportsIndex题面例base成功；公开a.C/b.C同名类复现已验且gold修。
**所需准备：** 中性改公开复现，保留限定名目标；准备新的公开读者，不给其gold/隐藏测试；核assert_type正例及失败文案。
**建议矩阵：** 新公开例base失败/gold通过；无歧义短名不退化；旧错误候选按新复现核。
**附加阻塞：** 公开材料变更需新版本/干净尝试；旧模型行为不能直接当新题面成绩。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/python__mypy-15184/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 12 · pandas-dev__pandas-50319

**缺口：** 题面明示返回 None 或猜出格式均可，测试仅接受格式；另有参数合键记录。
**已有依据：** 公开允许None或格式，唯一F2P只接受格式；None合理路线未运行；两参数别名合键。
**所需准备：** 构造局部ValueError→None候选并核原有格式及调用者回退；修oracle接受公开两路线，并补全节点绑定。
**建议矩阵：** noop→0；gold→1；保留其它行为的None解→1；恒None/吞掉其它错误→0预期。
**附加阻塞：** Cython重建/当前actor待验；None路线未证前不声称已解除误拒。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/pandas-dev__pandas-50319/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

### 12 · dask__dask-7138

**缺口：** gold 重命名参数会破坏旧 array= 调用；题面包含修法提示。
**已有依据：** gold重命名形参使旧array=调用失效，静态确定；旧pytest兼容配方已验。
**所需准备：** 保留array形参而添加转换主体的兼容候选；加入array=调用和原标量/list/ndarray行为，固定pytest7.4.4配方。
**建议矩阵：** noop原目标失败；兼容候选→1；原gold→0（array=护栏）。
**附加阻塞：** 先验兼容正对照/actor；题面自带修法提示保留说明；不要求未承诺零拷贝。
**材料：** [card.md](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/card.md)。完整SHA与所有独立复核/任务二入口见JSON。

## 共用验收与停止条件

冻结代码、base、镜像/离线资产、原材料与修订材料SHA、命令/预算、实际选择节点和参考绑定。公开面改动、评分改动、环境改动分开记。相关旧证据仅在适用版本复用；没有变化的整套矩阵不机械重跑。

每行核完整安装子命令、实际源码与模块来源、全部新增及旧引用状态、终止事实和双层清理。正确对照不成立或安装仍不明时保留第2类，并列出具体辨别动作；原分数保留，不能改写为新版本分数。只有验收后才能提出转第1类，训练/留出资格仍另议。

所有材料已见私有测试与gold，只能用于准备/校准，不能提供给solver或冒作独立公开初判。
