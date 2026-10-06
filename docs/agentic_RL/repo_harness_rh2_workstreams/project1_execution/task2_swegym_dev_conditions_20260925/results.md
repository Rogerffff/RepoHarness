# 任务二结果（逐题，滚动更新）

> **Codex 独立复核补记（09-25）：**见[完成复核](codex_completion_review_20260925.md)。主要开发证据接受，探针批次仍有四项窄修；W4 是已知超窗缺口的观测，不是验收通过。下文 R6“SIGTERM 尚未验证”已过时，现有证据支持工具运行中取消后的清理；私有 gold 并非同身份、同 profile 的 actor 对照。作者原始记录保留。

> **G1 状态更新（09-25，Codex）：**`83760b15` 已独立复核通过，见[完成复核 §6](codex_completion_review_20260925.md#6-g1-追加复核接受修复与定向验证--2026-09-25)。新 profile 下 Conan 两项 noexec 失败均已消除，选定功能测试组为 10 pass / 0 fail；下文是修复前历史记录。Conan 的题意覆盖限制、其它探针脚本问题不由本次修复核销。

更新：2026-09-25。执行条件：任务二 CPU 机（x86_64，16 vCPU / 62 GB，Docker 29.8.1，已关闭 containerd 镜像存储、改用 overlay2，镜像 ID 与历史记录可比）。仓库 HEAD `0ef2e617`，外加本目录未提交的实验脚本。CC 平台包 2.1.205（npm integrity 已核）。

**入口**：[`devcheck.py`](../../../../../rh2/experiments/task2_swegym_dev_20260925/devcheck.py)。它走 A 线 `acceptance_startup_2` 的正式装配，只把模型换成桩，并按命令清单逐条发出 Bash 调用，所以每条命令都是真实 CC 2.1.205 在 agent（UID 54321）子 shell 里执行的。每条命令的 rc 和截尾输出由 root 事后从容器取回、按命令 ID 关联；取不到 rc 就记为"未运行"。

- 容器资源为正式 profile 默认值：2 CPU、4 GiB 内存、`/tmp` 1 GiB、home 256 MiB，已由 `docker inspect` 回读。
- 派生镜像用 [`build_actor.py`](../../../../../rh2/experiments/task2_swegym_dev_20260925/build_actor.py) 构建：wheel 按 sha256 固定，装进解题解释器；同时记录 `pip freeze` 前后差异、`pip check` 结果，以及基础层是否保留。
- 私有对照用 [`private_control.py`](../../../../../rh2/experiments/task2_swegym_dev_20260925/private_control.py)：在不联网的一次性容器里只应用 gold 的源码段，执行同一批命令。这个容器不交给求解者。

原始证据在机器的 `/work/task2/runs/<题>/<条件>/`（`attempt.json` 和 `captures/*.out`），收口时回传到本地 `runs/task2_swegym_dev_20260925/`。

## 09-25 更新（Codex 完成复核之后）

- **R4 前提已完成**：
  - mypy10424：错误候选 C1 拿到 reward 1，说明官方 P2P 为空；
  - pydantic8511：gold 在继承场景下确实会装饰失败，窄修正版与 gold 都得 1。

  两题都转为"可进探针"，得 1 的补丁要走事后审计。
- **G1 已修复**（A 线 `83760b15`）：Conan 受 noexec 影响的 2 项功能测试限制撤销，题意覆盖缺口仍保留。
- **首轮 7 题的行为裁决**已完成（Dask 不需要），全部 T0 项已裁决，见 [t0_decisions_20260925.md](t0_decisions_20260925.md)。给评分补参考测试需要新的 SWE-Gym 修订机制，因此只定方向、暂不实施；在此之前用事后行为审计兜底（`rh2/experiments/task2_swegym_dev_20260925/post_hoc_audits.json`）。
- **当前分类**：
  - 可进探针 19 题（其中 6 题用 actor 派生镜像；mypy15184、DVC1681、pandas53958 带题面限制；mypy10424、mypy17071、Conan15422、Moto5134、pydantic8511 得 1 后要做事后审计）；
  - 只作诊断 2 题：Moto5752、mypy11236。

## 次晨摘要：21 题开发条件（正式入口实测）

21 题（原 21 个候选 = 首轮 8 题 + 未求解 13 题）全部在正式 actor 入口下跑过。每题都做了原条件实测，需要修订的题修订后用同一份清单复验，并都做了私有 gold 对照。

**按状态分：**

| 状态 | 题目 | 说明 |
| --- | --- | --- |
| 可进探针，用公开镜像 | mypy10174、mypy16869、moto5960、moto6408、mypy10308、pandas48106、pandas56849、DVC1681* | 原例能复现缺陷，相关测试能执行，gold 对照通过 |
| 可进探针，要用 actor 派生镜像 | Dask8597（pytest 7.4.4）、Moto5134（boto3/botocore 与 grader 一致）、DVC6954（pygit2 1.14.1）、DVC4166（pathspec 0.8.1 + networkx 兼容）、DVC5839（pathspec 0.8.1）、Conan15422* | 派生只加公开开发依赖或工具链，wheel / 文件都按 sha256 固定 |
| 可进探针但带题目限制（*） | mypy15184（题面原例在该 base 不复现，需自造复现）、DVC1681（原例依赖老版本文件，需自造复现）、pandas53958（正确修复会让公开 `test_api.py` 失败）、Conan15422（2 个功能测试受 G1 noexec 影响） | 限制是否要在题面说明属于 T0 |
| 开发已验，语义对照待做（R4） | mypy10424、pydantic8511 | 首批候选要求的前提对照还没做，完成前不进模型能力比较 |
| 开发可用，题意争议待裁定 | Moto5752、mypy11236、mypy17071（以及 Conan15422 的覆盖缺口） | 沿用首轮处置卡的 T0 项 |

**actor 派生镜像清单**（都在任务二机器上，`rh2-task2/<名字>:20260925`；配方在 `rh2/experiments/task2_swegym_dev_20260925/plans/`）：

- `actor_dask8597_v1`
- `actor_moto5134_v1`
- `actor_dvc6954_v1`
- `actor_conan15422_v2`
- `actor_dvc4166_v1`
- `actor_dvc5839_v2`

**本轮发现的新问题：**

- 题目层面：
  - mypy15184 的题面原例在该 base 不复现；
  - DVC4166 的 actor 与 grader 用的 pathspec 版本不同，会直接改变题目语义；
  - Conan15422 的 agent 身份下没有 `conan` 命令；
  - pandas53958 的公开 API 测试与正确修复相冲突。
- 通用层面：G1（`/tmp` 与 HOME 是 noexec），移交 A 线。

## 共同事实（来自前两题）

A 线 #1 修复在正式路径上已生效：两题的 agent 身份都拿到了 `/opt/miniconda3/envs/testbed/bin/python`，项目包从 `/testbed` 导入，激活核查通过（`ACT_CONDA_DEFAULT_ENV=testbed`）。容器里没有 `.harness`，跑完无残留容器或网络。

## 逐题

| 题目 | 原条件（正式入口，公开镜像） | 修订 | 修订后同一清单 | 私有 gold 对照 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Dask8597 | 题面原例 `OverflowError`（目标缺陷）；相关窄测试 2 失败：`TypeError: exceptions must be derived from Warning`（pytest 8.3.2 不接受 `warns(None)`）；`test_slicing.py` 116 通过 / 2 失败 | `actor_dask8597_v1` = 公开镜像 + pytest 7.4.4（与 grader compat_v1 同一 wheel sha256），`image sha256:1af84acd…`，基础层保留；`pip check` 只剩 base 原有的 distributed/dask 版本冲突 | 原例仍 `OverflowError`；窄测试 3 通过；整文件 118 通过 / 0 失败；工作区无改动 | 原例、窄测试、整文件全部 rc=0 | **可进探针**（actor 用 `actor_dask8597_v1`；grader 沿用 compat_v1，不受影响） |
| Moto5134 | 公开 API 原例：null / 有值 / 缺键 = `[False, True, False]`（目标缺陷）；端到端 Events→Logs 投递 0 条；`test_events_integration.py` 3 个 SQS 用例 `KeyError: 'QueueUrl'`（botocore 1.35.9 对 SQS 走 JSON 协议，本 base 的 moto 只回 query 格式）；`test_events.py` 103 通过 | `actor_moto5134_v1` = 公开镜像 + boto3 1.28.57 / botocore 1.31.57 / s3transfer 0.7.0 / urllib3 1.26.20（与 grader sqs_v1 同一组 wheel sha256），`image sha256:6d375738…`，`pip check` 通过 | 两条原例仍暴露缺陷；集成 4/4 通过；模式 12 通过；archive 回归面 103 通过 | 原例 API 与端到端、集成、archive 全部 rc=0 | **可进探针**（actor 用 `actor_moto5134_v1`）。限制：跑端到端需自设 `AWS_DEFAULT_REGION` 等变量，这是题目本身的公开前提 |
| DVC6954 | 题面 CLI（`stage add -p params.py:…` → `repro`）：`Parameters 'my_int, my_float' are missing from 'params.py'`（目标缺陷）；pygit2 1.15.1 已移除 `GIT_OBJ_COMMIT`，而 base 的 `dvc/scm/git/backend/pygit2.py:112` 仍导入 → 有提交后的 `params diff HEAD` 报 `unexpected error`，`tests/func/params` 16 失败 / 8 通过 | `actor_dvc6954_v1` = 公开镜像 + pygit2 1.14.1（cp39 wheel，自带 libgit2 1.7.2），`image sha256:92433fa5…`，`pip check` 通过。依据：`setup.cfg` 只写 `pygit2>=1.5.0`，1.14 是保留该常量的最后一个系列；同仓 DVC9395 的 grader 配方也用过它，但本题是**实测验证**，没有直接套用 | CLI 原例仍暴露缺陷；`params diff HEAD` 可运行；`tests/func/params` 24/24 通过；序列化单测通过 | CLI 原例（dvc.lock 记下 `my_int: -1`、`my_float: -0.5`）、git 修订路径、功能测试、单测全部 rc=0 | **可进探针**（actor 用 `actor_dvc6954_v1`；grader 的 `dvc_install_v1c` 不变） |
| Conan15422 | agent 身份下**没有 `conan` 命令**：testbed 没装该包（源码靠 cwd 导入），`setup.py` 声明了入口 `conan=conans.conan:run`；题面 CLI 与"真实 CMake 消费预设"两条公开路径都跑不了。功能测试：6 个 ERROR（`Required 'cmake' tool version '3.23' is not available`，仓库 `conftest.py` 约定 Linux 的 3.23 在 `/usr/share/cmake-3.23.5/bin`） | v1：解释器 bin 目录加 `conan` 入口（等价于声明的入口，把 `/testbed` 放上路径，**不写 `/testbed`**）+ Kitware 官方 CMake 3.23.5 装到约定路径（sha256 取自官方 SHA-256.txt）。v2（采用）：在 v1 基础上让 PATH 上的 `cmake` 默认为 3.23.5，`image sha256:5fe4796d…` | 题面 CLI：`buildPresets [('conan-release', None)]`（目标缺陷）；真实 CMake 3.23.5 能 configure 并构建 Conan 生成的预设（3.22.1 下报 `Unrecognized "version" field`）；集成测试通过；功能测试 8 通过 / 2 失败，2 个失败都是 `/tmp` noexec 造成的 `Permission denied`（见下文通用问题 G1），root 下同两项通过 | CLI 原例得 `('conan-release', 42)`；真实 CMake 消费、集成测试 rc=0 | **可进探针，带限制**：actor 用 `actor_conan15422_v2`；需要执行 `/tmp` 下构建产物的 2 个功能测试在正式沙箱中不可用（G1）。题意覆盖缺口（三条断言）仍待你裁定 |

### 13 道未求解候选：A 组（已有 install_wave1 配方的 6 题）

全部在**原公开镜像**、正式入口下验证，不需要 actor 派生。窄测试在 agent 身份下都真实执行（数量见下）。每题都做了私有 gold 对照：原例与窄测试全部 rc=0，所以 base 上的失败来自目标缺陷。

| 题目 | 原例（公开路径） | 相关公开测试（agent 身份） | 既有模型前提（R4） | 状态 |
| --- | --- | --- | --- | --- |
| mypy10174 | `Non-overlapping container check`（目标误报）复现 | strict equality 32 通过 | 队列项"严格比较负例"（只关非严格 optional 下危险比较的候选能否满分）待做，不阻塞开发 | **可进探针** |
| mypy10424 | `reveal_type(t)` 得 `<nothing>`（目标缺陷）复现 | 收窄相关 133 通过 / 1 跳过 | **有前提**：首批候选说明要求先做窄化对照（完全关闭 type 比较收窄的错误候选能否满分）→ 标"开发已验、语义对照待做"，前提完成前不进模型能力比较 | 开发已验、语义对照待做 |
| mypy15184 | **题面原例在该 base 不复现**：默认、3.8、3.11 目标都输出 `Success`；3.7 下 `typing.SupportsIndex` 未定义。原因是 base 自带的 typeshed 里，`typing_extensions` 在 ≥3.8 直接复用 `typing.SupportsIndex`，两个名字是同一类型。公开替代复现（两个模块各有同名类 `C`，对其 `assert_type`）得 `Expression is of type "C", not "C"`，正是题目缺陷 | assert_type 6 通过 | 队列项"原例是否仍触发"：**已回答——不触发** | **可进探针，带限制**：模型无法用题面原例验证修复，需要自己构造复现。是否在题面补一句说明属于 T0，由你决定；不补的话，这道题额外考"自造复现"的能力 |
| mypy16869 | 公开 CLI `stubgen` 崩溃（`TypeError: sequence item 0: expected str instance, NoneType found`，位置与题面一致） | stubgen 29 通过 / 1 xfail | 队列项"合法 Unpack 规范化输出是否被隐藏 `*Ts` 精确文本误拒"待做（固定 grader 语义诊断） | **可进探针**（语义诊断另列） |
| moto5960 | 题面两个 pytest 用例（本地 mock DynamoDB）都失败：GSI INCLUDE / KEYS_ONLY 下 scan 返回全部属性 | DynamoDB gsi/scan/projection 29 通过 | 队列项"只漏 KEYS_ONLY scan 的部分实现能否满分"待做 | **可进探针** |
| moto6408 | 题面回归用例失败（tag 移到新镜像后 `batch_get_image` 仍返回旧镜像） | ECR put_image/tag 29 通过 | 队列项"目的 manifest 预创建对标签归属的影响"待做 | **可进探针** |

说明：这 6 题的 actor 与首轮一样用公开镜像里的 pytest / boto3（moto 两题是 boto3 1.35.9）。相关测试在这些版本下都能执行，所以没有做派生。

### 13 道未求解候选：B、C 组（DVC 两题、pydantic8511、mypy10308）

| 题目 | 原条件（正式入口，公开镜像） | 修订 | 修订后 / 私有 gold 对照 | 既有模型前提（R4） | 状态 |
| --- | --- | --- | --- | --- | --- |
| DVC4166 | 公开 Tree API 原例：`/*` + `!/scripts/` 把 `scripts/a.py` 隐藏（目标缺陷）。**actor 的 pathspec 是 0.12.1，而 grader（`dvc_install_v1c`，E13）固定 0.8.1**：相关公开测试 4 失败，其中 3 个是 `re.error: redefinition of group name`（与首轮 DVC5839 同一问题），1 个是 networkx 2.3 在 Python 3.9 下导入失败（`fractions.gcd` 已移除）。pathspec 版本会直接改变 `.dvcignore` 匹配语义：0.12.1 下 `*`+`!scripts` 可见，0.8.1 下隐藏 | `actor_dvc4166_v1` = 公开镜像 + pathspec 0.8.1（与 grader 同一版本）+ networkx 2.3（PyPI 源码包，sha256 `8311ddef…`，PyPI 没有 2.3 的 wheel）并按 grader 的 `networkx_backport.json` 做同一处 `dag.py` 替换。grader 用的是重打包 wheel `2.3+rh2.1`，两边代码等价，但包元数据版本不同。`image sha256:d7997ec4…`，`pip check` 通过 | 修订后原例仍暴露缺陷；dvcignore 测试 29 通过。gold 对照：原例与测试 rc=0。**更正我原先的判断**：`*`+`!scripts` 在 gold 下同样隐藏目录内文件，这与 gitignore 语义一致（题面六种写法不等价），所以断言只检查 `/*` 开头的两种写法 | 队列项"目录专属规则与否定模式的自然过窄实现能否绕过"待做 | **可进探针**（actor 用 `actor_dvc4166_v1`） |
| DVC1681 | 题面原例依赖老版本生成的 `.dvc` 文件和大文件，无法原样重跑。公开可构造形态：同一仓库复制到另一个绝对路径后，`dvc status` 报 `changed checksum`（目标缺陷；原因与公开阅读一致，`wdir` 在校验计算时是绝对路径）；status / stage 公开测试通过 | 无 | gold 对照：构造原例与测试 rc=0 | 队列项"只在 checksum 内规范化的正常解是否被误拒"待做 | **可进探针，带限制**：题面原例不能原样复现，需要模型自己构造复现 |
| pydantic8511 | 题面原例输出 `x(y=3) a(b=1, c=2)`（目标缺陷）；`tests/test_dataclasses.py` 在 agent 身份下通过 | 无 | gold 对照：原例与测试 rc=0 | **有前提**：首批候选要求先收敛继承 / G1 语义对照（gold 在无本地注解的子类继承 `FieldInfo` 时可能装饰失败）→ 标"开发已验、语义对照待做" | 开发已验、语义对照待做 |
| mypy10308 | 题面原例（`--python-version 3.8`）触发 INTERNAL ERROR（`constraints.py:437` 的 `assert inst is not None and temp is not None`）；协议相关测试 15 通过 / 1 跳过 | 无（actor 用公开镜像；grader 的 `materials_v2` 是评分侧材料修订，私有补件不进 actor） | gold 对照：原例与测试 rc=0 | 队列项"原例在固定来源 base/gold 是否消除 internal error"：**已回答——base 崩溃、gold 消除** | **可进探针** |

另：DVC1681、pydantic8511 的镜像里没有 pytest-xdist，`-n0` 参数不被识别。这是我写命令时的错误，已改正后重跑，不属于环境缺口。

### 13 道未求解候选：D 组（pandas 三题）

都在原公开镜像、正式入口下验证，不需要 actor 派生。私有 gold 对照：三题的原例都 rc=0；相关测试除 53958 的 `test_api.py` 外都 rc=0（原因见下）。

| 题目 | 安装形态与开发路径 | 原例 | 相关公开测试 | 状态 |
| --- | --- | --- | --- | --- |
| pandas56849 | meson-python 可编辑安装（pandas 3.0.0.dev0）；可信初始化后 `/testbed/build` 属 agent。**改 Cython 源后能否重编**：触碰 `offsets.pyx` 再 import，meson 增量重编该模块（Cython → C → 链接 4 步）用时 19 秒，`.so` 已更新 | `freq="m"` 报 `Invalid frequency: m`（目标缺陷） | date_range 频率相关 119 通过 | **可进探针**；修复在 `.pyx`，模型需要触发重编（import 即可），2 CPU 下约 20 秒 |
| pandas48106 | setuptools 可编辑安装（pandas 1.5.0.dev0，Python 3.8）；修复在纯 Python 文件，不需要重编 | Categorical 扩增赋 `0` 抛内部 `TypeError: type.__new__() takes exactly 3 arguments`（目标缺陷） | setitem / categorical / 扩增 14 通过 | **可进探针** |
| pandas53958 | meson 可编辑安装（pandas 2.1.0.dev0）；修复在纯 Python | 题面给了两种方案（放进 `pandas._libs` 或 `pandas.api.typing`），不指定唯一答案，所以只记录现状：`_libs` 有 NaTType、没有 NAType；`api.typing` 两者都没有 | 公开 `test_api.py` 在 base 11 通过；**在 gold 下失败**，因为旧测试写死了原来的 API 名单，gold 加名字后与之不符（评分用的是更新后的隐藏测试） | **可进探针，带限制**：正确修复会让公开的 `test_api.py` 失败，模型需要理解并同步更新名单。队列项"typing 新名字绑定单例而不是真实类型的错误候选能否被名单式断言放过"待做 |

### 首轮 8 题中另外 4 题：在正式入口下复核

首轮这 4 题的 actor 证据都来自诊断变体 `bash_env_v1`。这次在正式入口下重跑首轮的同一份开发检查脚本，并补上首轮缺的原例与窄测试（首轮脚本对 Moto5752 和两道 mypy 只核了导入）。

| 题目 | 正式入口下的结果 | gold 对照 | 结论 |
| --- | --- | --- | --- |
| DVC5839 | 公开镜像：`dvc metrics show` 的 5 种参数组合全部报 `redefinition of group name 'ps_d'`（rc=255），与首轮一致。`actor_dvc5839_v2`（公开镜像 + pathspec 0.8.1，按 `build_actor` 重建，`image sha256:58420372…`）：5 种都 rc=0，窄测试 2 通过 | 首轮脚本 rc=0 | **可进探针**（actor 用 `actor_dvc5839_v2`），首轮结论可以迁移 |
| Moto5752 | 题面 MWE 原样执行：`hello` 放第二个时 1 条，放第一个时 2 条（目标缺陷）；SSM describe_parameters 相关 28 通过 | MWE 两种顺序都得 1 条；测试 rc=0 | 开发条件可用。题目范围争议（BeginsWith 断言）仍待你裁定 |
| mypy17071 | 题面原例报 `A function returning TypeVar should receive at least one argument…`（目标误报）；TypeGuard / TypeIs / 未绑定相关 135 通过 / 1 xfail | 原例与测试 rc=0 | 开发条件可用。P2P 覆盖缺口（"关掉检查"的短路候选）仍待你裁定 |
| mypy11236 | 题面原例（`--strict --python-version 3.7`）报 `Incompatible return value type`（目标缺陷）；Literal / Tuple / Union 相关 18 通过 | 原例 `Success`；测试 rc=0 | 开发条件可用。Final 与消息措辞两处争议仍待你裁定 |

## 对 Codex 计划复核 R1–R6 的落实

| 项 | 落实 |
| --- | --- |
| R1 版本与实际消费 | `--image` 显式覆盖 actor 镜像；每次运行记录 `image_facts`（镜像 ID、RepoDigests、HEAD、`git status --porcelain` 及其 rc）和 `container_inspect`（容器实际镜像 ID）。两题公开镜像 ID 与历史一致（Dask `f6d90e1b…`，digest `ab148b56…`），初态 porcelain 为空。pandas / mypy10308 的版本来源按复核更正：只有 48106 用 `pandas_meta_v3` + `reference_bindings_v1`；56849、53958 属于沿用原始对照的 50 题；mypy10308 复用已有 `materials_v2`，私有补件不进 actor |
| R2 独立判据 | 每条命令包一层：`timeout` 执行 → 写 `.rc` 文件和截尾输出（20 万字节）。root 事后按 ID 取回；rc 缺失 = 未运行，124/137 = 超时；期望分 zero / nonzero / any 三种。回合数给到命令数 + 3，不再用"工作区无写入"作为判据 |
| R3 有效资源 | `effective_profile` 与 `container_inspect` 均回读为 2 CPU / 4 GiB（正式默认值）。pandas 等重任务前先串行一题，再决定是否用 `RH2_SANDBOX_*` 调整，调整时另行记录 |
| R4 既有模型前提 | 结果表会加一列"既有模型前提"。pydantic8511（inheritance/G1）和 mypy10424（窄化对照）如果前提没完成，会标"开发已验、语义对照待做" |
| R5 旧 checks | 运行 `checks/dvc6954.py`、`moto5752.py` 前先按复核修：坏行改用 Python 写文件；Moto5752 补题面原样的 MWE |
| R6 停止与清理 | SIGTERM / SIGINT 会取消主任务，但仍执行清理；清理后按本次 `rh2.run_id` 标签强删残留，残留不为空则以退出码 4 结束。两次运行的 `residual_after_force` 都为空。"工具执行中收到 SIGTERM"已验证（`runs/diag_sigterm`：`result=cancelled`，清理完整、零残留，Codex 完成复核已核实） |

## 通用问题（移交 A 线）

**G1 正式 actor 的 `/tmp` 和 `/home/agent` 是 `noexec`。** 在 actor 容器里回读 `/proc/mounts`：

```
tmpfs /tmp tmpfs rw,nosuid,nodev,noexec,relatime,size=1048576k
tmpfs /home/agent tmpfs rw,nosuid,nodev,noexec,relatime,size=262144k,mode=750,uid=54321,gid=54321
```

在这两处建一个脚本并执行，都报 `Permission denied`（证据 `runs/diag_mounts`）。

原因：`RolloutSandboxProfile.expected_tmpfs()` 用 `--tmpfs /tmp:size=…,mode=1777` 挂载，没写 `exec`，而 Docker 对 `--tmpfs` 默认加 `noexec`。

影响：任何"在临时目录构建再运行"的开发路径都跑不了。

- 已实证的是 Conan 两个功能测试：pytest 的临时目录下，编出来的 `./build/Debug/foo` 和 `mytool.sh` 无法执行。
- 推断还会波及：`pip install --user` 装进 `~/.local/bin` 的命令、在 `/tmp` 下建的 venv、C 扩展测试产生的可执行文件。

这属于沙箱安全边界。是改成 `exec`、只对 `/tmp` 放开，还是保持现状并写进题目限制，需要 A 线评估、由你决定；本线程不在镜像里绕开。

**G2 首轮诊断变体的结论需要重新核对。** 首轮的 `bash_env_v1` 也跑在同一个 profile 上，挂载选项相同（推断，未回读），所以当时"测试可运行"的判断没有覆盖需要执行构建产物的路径。

## 探针接线（§6）

**改动**（都是 B 线自己的文件，未提交）：

- `qwen_adapter_server.py`：按 `bringup.py` 生产构造点的顺序装配 RH2 包装：
  1. `install_count_tokens_wire`
  2. `install_parse_wire`（`eos_token` / `eos_token_id` 取自当前 tokenizer）
  3. `install_turn_terminal_publisher`
  4. `assert_parse_wire_installed`
  5. 构造 `rh2_anthropic_adapter_cls()` 子类
  6. `bind_count_tokens_adapter`

  `adapter_config.json` 记录 `adapter_class` 和 `rh2_wrappers`（其中 `overflow_400: false`），另加 `/__probe_stats` 用于运行中回读 #5 的计数。
- `solve_attempt.py`：
  - 激活文件改写 `spec.env_activation_script`（与 `generate.py` 同一份）；
  - 启动前核对带上 `activation_file`，另加 `run_rollout_activation_check`；
  - `driver.run` 传入逐次执行的 `env_injections`（`agent_shell_env` + `cc_context_env`）和 `harness_log_dir`，轨迹从宿主读；
  - 去掉 `bash_env_v1`、`--harness-out` 和 `--disallowedTools`（工具白名单与关闭自动记忆由 `bringup` 追加，不重复加）；
  - 新增 `--max-context-len`（必须与 adapter 的 `--max-context-tokens` 同一个数）和 `--max-new-tokens`。

  `run_matrix.py` 相应改了参数。

**CPU 窄验收**（`wiring_check.py`：假 SGLang `/generate` + 真实 Qwen3-Coder tokenizer + 探针 adapter 进程，证据 `runs/wiring/wiring_check.json`）：

| 项 | 结果 |
| --- | --- |
| W1 启动 | 按生产顺序装配后正常启动；`adapter_class = …rh2_anthropic_adapter_cls.<locals>.Rh2AnthropicAdapter`；包装 4 个为 true，`overflow_400` 为 false |
| W2 count_tokens | 真实计数：短消息 14、长消息 209（不再恒 0） |
| W3 #5 EOS | 最后一个采样 id 是 EOS 时，可见的 `<|im_end|>` 被剥掉，文本为 `Done.`，计数 `eos_stripped=1`；普通 token 拼出的同名文本保留，计数 `eos_literal_kept=1` |
| W4 超窗 | 首次（未接 400）：返回 HTTP 200 空文本，**不算通过**。接入 A 线 `9d741bd4` 的 `install_overflow_400_wire()`（交接 §2 第 2c 行）后重测（`runs/wiring_v2`）：返回 **HTTP 400** `prompt is too long: 6009 tokens > 3000 maximum`，`rh2_wrappers.overflow_400=true` |

**没覆盖的**：

- 工具调用和推理解析，因为需要 SGLang 解析器；
- #6(a) 提醒并入 tool_result（A 线已有单测）；
- 真实模型下的首个请求回读（工具列表、窗口变量是否生效）。

这几项在租 GPU 后的冒烟测试里补做。

**网关断流收尾（A→B 交接 §4）**：`model_gateway.py` 原本只在上游抛异常时中止下游。现在加了一条：SSE 响应在上游 HTTP 干净结束、但没有 `message_stop` 时，同样记为 `stream_error=sse_missing_message_stop`，并中止下游连接，不再正常收尾。

CPU 窄验收（`gateway_check.py`，受控上游经网关到客户端）：

| 上游形态 | 客户端 | 网关记录 |
| --- | --- | --- |
| 完整 SSE | 完整读完 | `stream_error` 为空 |
| 干净结束、缺 `message_stop` | `ClientPayloadError` | `sse_missing_message_stop` |
| 首事件后直接断连 | `ClientPayloadError` | 传输错误 |

真实 CC 收到中止后的退出形态以 A 线 #3 事实表为准，没有在本机复测。

## Codex 完成复核（09-25）的处理

复核原文见 [codex_completion_review_20260925.md](codex_completion_review_20260925.md)。F1–F4 均已修复，并补了窄对照（`probe_fix_checks.py`，结果在 `runs/task2_swegym_dev_20260925/probe_fix_checks.json`）：

| 项 | 修改 | 窄对照 |
| --- | --- | --- |
| F1 导出失败被送去 noop | `solve_attempt` 导出失败时记 `result=infra_failed:candidate_export_failed`，候选记录新增 `export_ok`；`run_matrix.grade` 只有 `export_ok` 且确认为空时才送 noop，导出失败或记录缺失一律不评分 | 导出失败、记录缺失：不调用评分器；合法空补丁：送 `noop`；非空：送 `patch-dir` |
| F2 清理失败不停派发 | `solve_attempt` 计算 `cleanup_ok`，查询失败记为未知（`None`），残留或未知时以 4 退出；`run_matrix` 在新跑和恢复两条路径上都检查，不通过就写 `STOP`、不评分；`devcheck` 同时复查容器和网络，查询失败记 `<query_failed>`；`run_batch.sh` 在 rc=4 或汇总不可读时停止 | `cleanup_ok=False`：写 STOP、不评分；`True`：进入评分 |
| F3 终局按子串判断 | 网关改为按完整 SSE 事件识别 `message_stop`（`event:` 行，或 data 行 JSON 的 `type`） | 真实终局 → 有终局；正文含同名词但无终局 → 无终局；只有开头 → 无终局 |
| F4 dirty 文件编辑后导出基线不对 | 物化时用 `git stash create` 生成基线快照（不改工作区、索引和 refs），候选相对它导出；初态没有已跟踪改动时基线就是 HEAD | 小型 git 仓库：相对 HEAD 导出的补丁在 dirty 初态上 apply 失败，相对快照导出的 apply 成功 |

**完整链路冒烟**（真实 CC 2.1.205 + 桩，mypy10424，其镜像初态带已跟踪改动 `test-requirements.txt`；证据在 `runs/smoke_e2e`）：

- 桩让 CC 改一个源码文件，再改那个脏文件；`solve_attempt` 结束为 `completed`，宿主日志完整。
- 实际注入了 `CLAUDE_CODE_MAX_CONTEXT_TOKENS/AUTO_COMPACT_WINDOW=32768` 和 `MAX_OUTPUT_TOKENS=4096`；首个请求的工具只有 Bash/Edit/NotebookEdit/Read/Write，`max_tokens=4096`。
- 候选相对快照导出（`baseline_commit_is_head=false`），脏文件的 diff 只含 agent 新加的一行。
- 用 `replay_grade.py run` 真实评分：`git_apply` 成功，没有 stage_error，`reward 0`（unresolved，符合预期，因为只加了注释）。
- 清理 `cleanup_ok=true`。

**G1**：A 线 `83760b15` 已同步到任务二机器（`sandbox_profile.py` 的 sha256 为 `7ffec82e…`，与本地一致）。Conan 的两项开发限制按 Codex §6 撤销，它的题意覆盖缺口仍然保留。

**仍未验证**：两款真实模型的工具调用和推理解析，以及真实窗口，这些留到 GPU 冒烟。

