# Claude 设计审查：评分性能下一阶段

日期：2026-10-04（Asia/Singapore）。审查对象：[experiment_design.md](experiment_design.md)（SHA-256 `2f56d45be34e8e5e2c9f2eb906fa8a89e5f42364d54eefecc1966f3b1200febf`）与 [README](README.md)（`5ef80bb7f8d702b100091992fc5486a20e68aa3cae1b3cc0a84409f907d44c1e`）。审查人：Claude（本批拟定实现者，跨模型审设计）。

状态：**设计审查，提出修改建议和待用户决定事项。** 没有改代码，没有运行新实验，没有登录机器或调用付费服务。新数字全部取自前一批已回传的原始日志与诊断（路径见 §7）；估计值逐处标明。

## 0. 结论

1. **同意设计的正确性边界。** FrozenPatch 是唯一候选输入；缓存放在评分源码树之外，不改基线摘要；缓存缺失或无法可靠失效时回到原全量构建，沿用原期限；不新增拒绝路径；失败、回退、准备与闲置全部入账；付费分阶段、到限即停。这些不需要改。
2. **不同意现有优先级。** 已回传的日志里有两项事实设计没有用上，它们会改变实验排序：
   - **git 清理（git_sanitize）是最大的候选前成本，设计没有覆盖。** 它占 DVC 评分耗时的 47%、Coverage 的 33%、Pandas 的 16%；actor 每次 attempt 开始时也跑同一脚本，Pandas 真实 GPU 运行中用了 69 秒，而模型求解本身只有 136 秒。它只依赖镜像，可以预做进可信模板。
   - **Pandas 约 10 分钟的"安装"已能定位。** `pip install -e .` 每次在新建的随机临时目录里串行重编全部 42 个 C 扩展，不读取树里已有的任何编译产物，也没有重新生成 Cython 代码。所以"树外基线构建缓存"只能做成编译器级缓存；同容器保留 actor 的编译结果在这条官方安装命令下没有作用。
3. **建议：** S1 的核心改为"预清理的可信模板 + 编译器缓存"；E3（同容器）缩成一次确认；E5 的远端 actor 递延；E6 按训练实际需要的并发重设；E7 明确模型后端。同时把已审过的 v13 权限优化并入发布线，满足本轮"接入实施"的要求。原设计的 8 项实验、6 个切片、最多 168 次 Prime 创建，比"简单实验并接入"重得多。
4. 需要用户决定的四项见 §5；其余按 T1 推进（§6）。

## 1. git 清理：最大的候选前成本

v13 优化后的 fresh 评分（CPU 主机，每次评分 2 vCPU／4 GiB，各两次）：

| 题 | 评分总耗时 | git 清理 | 占比 | 其余主要项 |
| --- | ---: | ---: | ---: | --- |
| DVC9395 | 97.4／97.6 秒 | 45.9／45.9 秒 | 47% | 测试执行 35 秒（安装约 9.5 秒＋测试约 25 秒）、解析 5 秒、官方文件保护 4 秒 |
| Pandas48106 | 770.6／855.6 秒 | 119.8／140.9 秒 | 16% | 安装 606／669 秒、测试 13–16 秒、保护 9–10 秒、解析 7 秒 |
| Coverage EA69 | 14.8／15.3 秒 | 4.8／5.4 秒 | 33–35% | 测试 4.4–4.7 秒；R2E 评分没有安装段 |

actor 侧来自真实 GPU 运行 `gpu1003-*` 的 attempt 记录（`timings.git_sanitize` 与 `solve_seconds`）：Pandas 清理 69.3 秒、求解 136.0 秒；DVC 17.8 秒、215.5 秒；Coverage 2.7 秒、72.7 秒。

**为什么这么慢。** 10-03 为了让 actor 与 grader 清理后的 git 打包文件逐字节一致，脚本改为 `git repack -a -d -q -F --threads=1`（[sandbox_profile.py:1373](../../../../../rh2/src/repoharness2/adapters/slime/sandbox_profile.py)）：单线程、不复用已有压缩差量、全量重压缩。[当时的复核](../ordinary_probe_20260929/git_pack_fix_review_20261003.md)只测了 Moto（12.5 秒增至 23 秒），并写明实际耗时须由真机记录。现在有了：约 3 万次提交的 Pandas 仓库每次约 2 分钟。actor 在 [generate.py:4937](../../../../../rh2/src/repoharness2/adapters/slime/generate.py) 每个 attempt 都执行一次。

**可以怎样省。** 清理发生在候选介入前，输入只有镜像，输出确定（`-F --threads=1` 正是为此加的）。可在构建可信模板时跑一次同一脚本，把结果固化进模板；评分时核对模板证明（同一脚本摘要、同一源镜像）后跳过重压缩。评分侧的完整基线比对本来就比较排除区摘要，模板与 actor 的清理结果若不一致，会按原规则失败，不会静默放过。

**不能做的。** 不能直接改脚本（例如去掉 `-F`）：清理结果会变，旧 FrozenPatch 绑定的基线摘要就对不上了。

**预计收益（估计，待 E1 实测）：** DVC 97 秒降到约 52–57 秒；Coverage 15 秒降到约 10 秒；Pandas 每次评分省约 2 分钟。actor 侧若也使用预清理镜像，Pandas 每个 attempt 再省约 1 分钟；这会改变 actor 的运行镜像身份，见 §5 D4。

## 2. Pandas 安装：机制已能从现有日志确定

证据来自 `gperf-pandas48106-dependencies-run-01` 的评分日志：

- 官方安装命令是 `python -m pip install -ve . --no-build-isolation`。新版 setuptools 走 PEP 660 的 `editable_wheel`：`build_ext` 的输出写进每次新建的随机目录 `/tmp/tmp….build-temp` 与 `/tmp/tmp….build-lib`，编完再 `copying … .so -> pandas/_libs`。
- 日志中有 42 个 `building '…' extension`、63 条编译命令和 41 条链接命令；Cython 的 `Compiling` 行为 0。
- 结论：每次评分都把 42 个扩展从头串行编一遍，约 10 分钟。镜像里已有的 .so、actor 留在树里的 .so，这条命令一律不读；Cython 代码生成没有重做（生成的 .c 文件已在镜像里）。

**推论 1：缓存只能做在编译器层。** 设计 §3.1 的"可信基线构建缓存"如果是预先放一个 build 目录，不会被用上，因为构建目录每次随机。推荐 ccache：一个包在编译器外面的缓存，以源码、所含头文件的内容和完整编译参数的哈希为键，命中时直接返回以前编出的目标文件。做法：在一次性容器里用基线源码编一次，把缓存目录导出到模板中评分树外、root 所有的只读位置；评分时把它作为只读的二级存储，另给本次评分一个私有可写目录。旧 mtime、头文件改动、编译参数变化都会使键不同而失配；缓存缺失或损坏时 ccache 自动回到真实编译，正好满足设计 §3.2 的回退要求。/testbed 不被改动，基线摘要不变。

**推论 2：需要实测的风险。** 若编译命令行带有随机临时路径（例如某个 `-I` 指向 build-temp），命中率会是 0，需要用 ccache 的路径相关设置处理；Cython 的重新生成仍按 mtime 判断，FrozenPatch 回放时 .pyx 与生成的 .c 的写入先后会影响是否重新生成（见 §3 E2）。

**推论 3：同容器保留 actor 编译成果对 Pandas 无效。** 即使 actor 编过，评分时官方命令也会全部重编。设计"旧原容器实验没有保留 actor 新编译结果，所以不能否定构建复用"这句话本身成立，但更根本的事实是这条命令根本不消费任何已有构建产物。

**推论 4：E0 对 Pandas 可以缩成一次带时间戳的确认运行，** 不需要从零拆解依赖、元数据、生成和编译。

**预计收益（估计，待 E1 实测）：** 安装约 600 秒降到约 1–2.5 分钟（剩 pip 自身开销、两次 setup.py 求值、41 次链接与复制）；叠加 §1，Pandas 评分从约 13 分钟降到约 2–4 分钟。

## 3. 对各实验的具体意见

| 实验 | 意见 |
| --- | --- |
| E0 | 保留，但改为整次评分的分段（诊断里已有 `host_events`），不只看安装段；Pandas 只需一次确认运行；同时收集 actor 侧清理耗时。 |
| E1 | 阶梯改为 L0（v13）→ L1（L0＋预清理 git，三题都测）→ L2（L1＋编译器缓存，Pandas）。原 L1"完整固定依赖／工具链"对 Pandas 基本为空：第三方依赖 v13 已预装，剩下的是编译 pandas 本身。新模板仍按设计做 noop／gold／已知错误的资格检查。 |
| E2 | 八类反例保留，映射到具体机制：增加编译器身份变化、只读基础缓存不可被候选写入、缓存缺失或损坏时自动回退三项；增加一条 Cython 层反例——FrozenPatch 同时含修改过的 .pyx 与 actor 遗留的过期 .c。**去掉 Coverage CTracer**：Coverage 是 R2E 题，评分脚本为 `RH2_INSTALL_SKIPPED=1`，生产评分不编译，缓存影响不到它。另把"私有伪造产物不能进入评分"改准确：FrozenPatch 内的文件按契约就是候选内容，候选的 setup.py 本来就在安装时运行；要保证的是 FrozenPatch 之外的 actor 产物（HOME、/tmp、私有缓存）不进评分，以及候选代码改不了共享的可信缓存。 |
| E3 | v13 数据显示，同容器在 DVC 上的收益基本就是跳过了 git 清理：原容器评分 55.8 秒（没有清理，环境普查 10.5 秒），fresh 97.4 秒（清理 45.9 秒）。Coverage 无收益；Pandas 更慢（封存 165 秒、恢复核对 143 秒，环境树 280,070 项）。预清理模板做好后，fresh 预计与原容器持平，还省掉封存（DVC 13.3 秒）和等评分期间占用的 actor 容器。建议在最终配方上每题做一次配对确认加分段核算，给出"不采用"或适用范围结论；不为此专门构建 Pandas 的 actor／grader 共同镜像。 |
| E4 | 同意。建议把 DVC 的三个资格输入从 E5 挪到这里——它们同属"接入资格"，这样 E5 做不做都不影响 E6。 |
| E5 | 远端 actor 建议递延：要把模型网关暴露到公网或建隧道（新的安全面）；每轮模型调用多一次跨云往返；GPU 主机本来就要有，其 CPU 余量可以跑 actor（项目默认单 VM 同机）；`set_network` 不切断已建连接；同容器收益在 §1 之后接近零。若要给这条路线一个有证据的结论，可只用 1–2 个 sandbox 测网络撤销语义（已建 TCP 流在 `set_network` 之后是否断开），不移植 actor。 |
| E6 | 1 路档与 E4 重复；1／2／4／8 都在一台本地主机能承受的范围内，测不出托管扩容的价值。建议按训练预期并发选档，至少一档明显超过单机（例如 32），每档 2 波；放在 E1 之后（评分变短，费用和墙钟都下降）。成本对比应包含"按需租一台合适规格的 CPU 机"：Prime 每 vCPU 小时约 US$0.049（含 2 GiB 内存），整机计费的 CPU 机满载时明显更便宜，Prime 的理由应落在弹性和运维，不在单价。 |
| E7 | 设计写"使用已确认的模型、工具与预算"，本批没有对应授权，需要选定后端（§5 D3）。 |

## 4. 其它核对结果

- **父版。** `frozen_code_v9` 已存在（10-03 21:28 生成，状态 `local_frozen_candidate_not_deployed`）。v13 修改的 5 个既有文件在 v8 与 v9 中摘要完全相同，所以 v13 可原样落到 v9。共享工作树的 `grading/manager.py` 已与 v8 不同（`b6b10f98…` 对 `1783533e…`），进共享树需按语义移植。
- **v13 尚未并入任何发布版本。** 前一批的实施建议正是"优先集成权限预制加全新容器评分"。建议 S0 的交付物包括"v13 落到最新冻结版"，交发布线程纳入下一封板，避免在未并入的补丁上继续叠加。
- **共享 CPU 主机。** cpu-a／cpu-c 每机 2 个作业槽，与第 2 类工作共用。每次计时运行记录同机其它作业，避免把同机竞争算进收益或损失。
- **顺带发现（B 线评分语义，本批不处理）。** R2E 评分脚本不含安装或构建步骤，候选对 C／Cython 源码的修改在评分时不会被编译。R2E 题池里有 numpy、pillow、orange3、pandas、coverage 等编译型仓库，建议 B 确认题目筛选是否已考虑这一点；可能已知。

## 5. 需要用户决定

| ID | 事项 | 选项 | 建议 |
| --- | --- | --- | --- |
| D1 | 是否按本审查调整范围 | (a) S1 核心为预清理模板＋编译器缓存；E3 缩为确认；E5 远端 actor 递延，可选 1–2 个 sandbox 的网络探针；E6 按需重设。(b) 维持原设计 8 项。 | (a)。三条路线都会有结论；同容器与远端 actor 给出有证据的"不采用／适用范围"结论。 |
| D2 | Prime 额度 | A 阶段 US$5；B 阶段追加 US$20 上限。 | 现在批 A（接入资格，便宜，且决定 Prime 能否承接我们的镜像）；B 在 E4 结果和 D1 确定后再批。 |
| D3 | E7 的模型后端 | (a) 沿用第 1 类探针用过的 DeepSeek 收费网关，小额按次计费；(b) 搭下一次 GPU 运行；(c) 本批不做 E7，只交 CPU 与 Prime 证据。 | (a) 或 (b)，看哪个先可用。 |
| D4 | actor 侧是否也使用预清理镜像 | 可以晚点定。 | 本批先在评分侧实现，并测出 actor 侧能省多少；actor 镜像身份变化涉及 B 线的环境资格，单独决定。 |

## 6. 按 T1 处理、不再请示的部分

预清理模板的具体核验方式（至少不弱于现有自证，或绑定到模板证明与排除区摘要）；ccache 的版本与配置（只读二级存储、私有一级目录、编译器身份按内容核对）；E0／E1 的计时埋点；实验入口位置。实施中若发现需要改变 FrozenPatch 或基线契约、放宽隔离、新增拒绝路径，停下来另起决策包。

## 7. 证据索引

以下路径相对仓库根目录，均为已回传的本地忽略目录或跟踪源码。

- 评分分段：`runs/grading_performance_20261003/results/cpu-a/gperf-dvc9395-optimized-0{1,2}/`、`cpu-c/gperf-pandas48106-dependencies-run-0{1,2}/`、`cpu-a/gperf-coverageea69-repository-0{1,2}/` 下的 `eval_logs/*.diagnostics.json`（`git_sanitize.seconds`、`performance.host_events`、`candidate.install_seconds`）。
- Pandas 构建机制：`cpu-c/gperf-pandas48106-dependencies-run-01/…/eval_logs/*.eval.log`，`pip install -ve .` 之后的 `building '…' extension`、`/tmp/tmp….build-temp`、`copying … .so` 各行；评分脚本见同目录 `scripts.json`。
- 原容器对照：`cpu-a/gperf-dvc9395-handoff-01/…/eval_logs/*.diagnostics.json`（`exec:in_place_environment_census` 10.51 秒，无 `git_sanitize` 计时）；Pandas 封存与恢复数字见[前一批结果](../grading_performance_20261003/README.md)。
- actor 侧：`runs/grading_performance_20261003/inputs/remote/queue_v{27,29,31}/results/gpu1003-*/attempt/attempt.json`。
- Coverage 评分脚本：`cpu-a/gperf-coverageea69-repository-01/…/scripts.json`（`RH2_INSTALL_SKIPPED=1`）。
- 父版核对：`runs/ordinary_gpu_probe_20261002/frozen_code_v{8,9}/` 与 v13 [manifest](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13/manifest.json) 的 `before_sha256`。
- Prime 费率：[官方 Overview](https://docs.primeintellect.ai/sandboxes/overview)，2026-10-04 核对为每 vCPU 小时 US$0.02、每 GiB 内存小时 US$0.0125、每 GiB 磁盘小时 US$0.0002，有效至 2026-12-22；2 vCPU／4 GiB／40 GiB 合计 US$0.098／小时，与设计一致。
