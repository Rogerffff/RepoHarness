# 10174 GPU 安装问题：非作者反证与最小方案审查

日期：2026-10-03。角色：review-standards.md §10.4 的 Falsifier / Simplifier；已见原 FP、私有评分材料及旧 CPU 证据，非 fresh reader。

**限定收口：原 GPU 候选在同 source、同 wheel、同 R6 的可读 CPU 派生镜像下，正式重评分 reward1，四参考全部实际通过；足以保留本题候选能力结论。** 原 GPU 安装 RC1 是可达的环境准备缺陷，不能据此把候选能力改判为零。原 raw1 的“测试四参考通过、editable install 一条 RC1、段末 RC0”仍原样保留，CPU r16 是单独的新证据，不回填旧结果或证明旧 GPU 每个模块的加载来源。

r16 在正式评分前另执行三条安装命令作预热，动态来源观测来自独立 Python 进程；这两项限制直接保留。CPU 补证不表示新 GPU 镜像权限已经修正，也不新增训练资格。本 ownership 边界的能力补证已充分，停止扩跑。完整证据与剩余边界见 §5。

本审查没有 SSH、启动容器／模型、重跑矩阵／全测试，也没有修改旧材料、builder 或共享文件。唯一写入是本报告。运行由主审查者执行；本报告独立回读其窄复验原件后收口。

## 1. 范围与事实身份

GPU 原件根目录：`runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-mypy10174-qwen36-a1/`。下文 `GPU/` 均指此目录。

| 对象 | 核对结果 |
| --- | --- |
| 原始 frozen digest | `sha256:5772af211384a9828c83dd61c60c96a6447475e34c4b2bfb891f584ac4304664`。FP 文件字节 SHA 为 `d72699b958fc0f688d5e6c4d4fd5e93006bd18c4a4ea86a2f76c998a4bbeae07`；二者含义不同。 |
| baseline | manifest digest `sha256:337be5fc6ed9a5013249a17bcfb9e48cf7dce2aa3ca27cb4b8b9fd9f0efb7172`；tar 文件字节 SHA `714753b01aff10c04468da922f8e9e6bccb3e02223de96209cd9f532d7688437`。逐项读取 tar 验证 1472 个 manifest 条目，无内容摘要不符。 |
| FP 与投影 | FP 51 条：49 个 `.mypy_cache/` 文件、`mypy/meet.py`、候选修改的 `test-data/unit/check-expressions.test`。正式 projection 50 条，恰好排除后者，保留全部 49 个 cache 和目标源码。 |
| R6 材料 | `mypy10174-strict-equality-v1`；registry `a49edd0750cd45c880344bdda762bd757d8bdfddd09689c69cf2e46e316e3cf6`；grading bundle `b24e783218afdcf37c4717cf2702ad195e999e120683483269ac94de10802255`；materials identity `dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065`。原 GPU diagnostics 与 CPU 第六版回读一致。 |
| 实际 GPU 入口 | queue_v12 request 指向 `code_v4`；相应冻结 `swe_material_revisions.py:70–71,133–143` 绑定上述修订及 effective test patch SHA `91ea4e972129deaf770ef9e72aa26d11d9bafca85229eae6931f2b22568322cf`。 |
| 模块内容 | baseline `mypy/meet.py` SHA `8df49240a0aeea302ed7f07fdbdab35a6e6ff1ef2614bcd5db6ded89721a38f2`；候选 SHA `fda3ae751b225a484400198ff560bbaab9ec56d0dc5f54e3b2846a85c103a0a7`。候选在移除 Optional 的 None 并重新取 proper type 后，再判断 Any overlap。 |

## 2. 尝试推翻严重度的结果

### 安装失败没有被四参考通过否定

`GPU/grading/eval_logs/evallog_gpu1003-mypy10174-qwen36_193cc9fb.eval.log:462–488`：`python -m pip install -e .` 在隔离 build dependencies 阶段读取 setuptools wheel 时遇到 `Permission denied`，真实 RC1；ERR trap 留有 `RH2_INSTALL_CMD_FAILED=1`。随后 `pip install pytest pytest-xdist` 成功，脚本将段末状态写为 RC0（489–507）。这里的 RC0 是最后命令结果，不能解释为所有安装命令成功。

同一原日志 517–536 记录实际 pytest 命令、9423 collected／4 selected、四条 `PASSED`、测试 RC0。diagnostics 同时保留 failed command 与四个参考分区的 success，missing／skipped／参考外解析均为 0。因而“没有真跑测试”被原日志反驳；“安装成功”同样被原日志反驳。

冻结 `grading/manager.py:1026–1061` 明确把 `install_rc_last_command` 与 `install_failed_commands` 分列，并将 test RC 用于诊断；2075–2109 的全局失败归因只在零解析／参考全缺席时触发。因此本题没有进入该归因分支，与 `execution_failure_decision=null` 一致。不能将现有代码行为误写为已有“任一安装失败直接取消 reward”的规则。

### 权限来源有具体差异，不能归因于候选源码

GPU 本地 builder `runs/ordinary_gpu_probe_20261002/tools/build_swe_four_v1.py:38,102–110` 设置 umask `077`，下载并核验三个公开 wheel 的 SHA／大小后，显式 `wp.chmod(0o600)`；Dockerfile 只有 `COPY wheels/ /opt/rh2/build-wheels/` 及离线 pip 环境，没有安装层权限规范化。grader UID 为 `54322`，无法读取 root 所有的 `0600` wheel，与真实 RC1吻合。

旧 CPU Dockerfile 字节与此四行配方一致；CPU wheel 为 `0644`，三份 wheel 的 SHA 与 GPU 准备材料逐一一致：packaging `5b8f2217…`、setuptools `35ab7fd3…`、wheel `2376a90c…`。旧 CPU `mypy10174-revised-r3-20261002T182535Z-f641d8` 的 noop／gold 原始日志分别在 468–474／495–501 记录 `Successfully built/installed mypy`，无失败命令。相同源码及 wheel 可安装的反例，排除了必须重换依赖版本或修改候选修法的解释。

现有本机 payload 权限为 `0644`，只证明本机副本；不能用它覆盖远端 builder 的显式 `0600`。原镜像没有 wheel `stat` 回执，故精确容器 mode 是待补实测项；日志与 builder 已足以定位可达权限缺陷。

### 缓存污染假设受到测试实现反证，但原始动态模块证据仍有限

baseline tar 及 grader rebuild census 都没有 `.mypy_cache`、`.so` 或 `.pyc`。`mypy/__init__.py` 只有空包注释，没有扩展 `__path__`。正式 diagnostics 观察到 `/testbed/mypy/__init__.py`，runner 前后 SHA 相同。失败发生在 build dependencies 读取阶段，日志没有进入本次 editable build 或编译成功。

候选的 49 个 cache 不是被静默清掉：baseline policy 仅省略 `.pytest_cache`、`__pycache__`；FP/projection 仍包含 `.mypy_cache`。其中 `debug_issue.meta.json` 来源为 `/tmp/debug_issue.py`，不会因其存在就证明四参考被污染。

从 baseline 原码读取的反证是：

- `mypy/test/data.py:238–255` 为每例建立独立 `TemporaryDirectory`，进入该目录，结束后清理。
- `mypy/test/testcheck.py:113–135,184–206` 对本题非 incremental 的普通 case 设置 `options.incremental=False`，非 writescache 时 `options.cache_dir=os.devnull`，随后直接调用 `build.build`。
- `mypy/test/testcheck.py:10` 导入 `mypy.build`；`mypy/checkexpr.py:48`、`mypy/checker.py:73` 导入 `mypy.meet.is_overlapping_types`。结合已知普通包位置及 baseline 无二进制扩展，目标源码是实际消费者的解释有很强支持。

因此本题 cache 暂无成立的污染路径，不值得为此扩大全矩阵或改公共缓存契约。严格的剩余未知是原 GPU 评分时 `mypy.meet/build/checkexpr` 的实际 `__file__`／loader／函数 `co_filename` 没有被记录；只看包的 `__init__.__file__` 不是完整模块来源证据。窄复验应记录目标模块来源，避免以推断代替直接观测。

## 3. Finding 与最小选项

本轮适用维度为 A/E/G/M/N（真实失败、验证有效性、正式消费者、诊断、依赖环境差异），B/I/K（不能把环境错误转成模型负例，控制补证成本）。D/F/H 以本表身份及 frozen code 消费者核对；L 仅涉及一次窄评分成本。没有新增并发、公共 owner、恢复机制或状态机，C/J 的相关实现改动不在本次只读范围。

**F1：公开 wheel 被宿主私有权限复制进 grader 可达安装路径。**

| finding 要素 | 内容 |
| --- | --- |
| 当前行为／证据 | builder chmod0600；原正式 candidate install 读 setuptools wheel RC1。具体行号见 §2。 |
| 违反的不变量 | 已验 SHA 的公开安装资产应可被实际安装 UID 读取；字节正确和镜像 build 成功不替代该权限条件。 |
| 影响 | 环境准备未完成；可造成后续评分依赖旧已安装环境。本题仍有实际测试结果，不足以认定模型失败或 reward 污染已经发生。 |
| 建议分期 | 当前补证前修正公开 wheel materialization 权限；不要求改变 reward、样本拒绝或公共失败语义。 |
| 最小探针 | 原三条安装命令以真实 candidate UID 分别保留 RC；读取 wheel SHA/mode；观测 meet/build/checkexpr 的实际来源和目标源码 SHA；只评分原 FP 的四参考。 |
| 验收条件 | 实际 UID 三条命令 RC0、正式 candidate 段 failed commands 为空；原 FP/完整 baseline 身份不变，正式 manager 完成 baseline 重建／投影、四参考实际执行解析；模块来自候选源码，runner 未变。 |

| 选项 | 用途、代价与限制 |
| --- | --- |
| 保留 raw1、仅补静态解释 | 零运行成本；可报告四参考原始通过及权限异常，不能补上缺失的目标模块动态来源。适合历史留档，不是本轮完整收口。 |
| **推荐：同 source／同三 wheel 的已验可读 CPU 派生镜像，正式 manager 重评原 FP 一次** | 一次窄评分，无模型成本，49 cache 保留，完整 baseline/投影仍需真消费。补候选在完整安装环境下的能力证据；不追溯证明原 GPU 模块加载，也不表示原 GPU 镜像已修好。 |
| 新 GPU 派生镜像修正公开 wheel 权限后重评原 FP | 需要一次镜像准备及窄评分。能补当前 GPU 环境消费证据；未来同 builder 作业继续派发前应采用这类权限规范化。此审查不运行。 |
| `--no-build-isolation`／root 安装／关闭安装 | 看似便宜，但改变原安装条件，掩盖公开 wheel 权限问题；当前有更小且保留原配方的修复，不推荐。 |
| 重模型／完整 noop-gold-bad 矩阵／全测试 | 不解决本次明确的权限及模块来源缺口；R6 已有 CPU 矩阵，当前没有证据要求重跑。 |

最小修复可以只对公开 wheel 路径规范化：文件可读（如 `0644`）、目录可搜索（如 `0755`），或在新派生镜像仅对 `/opt/rh2/build-wheels` 设置相同条件。私有 grading 材料继续使用既有私有权限。不要把新镜像身份回写旧 FP/baseline 或原结果。

## 4. 窄复验回读与停止条件

主审查者实际采用 CPU 可读派生镜像 `sha256:9d63f1ddcbd277fa62d49e10d800908cfec54544e890fc5fe741d2101ca8eb7e`，消费原 FP／完整 baseline manifest，保留 49 cache，走正式 manager；另外以同 UID 逐条核原三条安装命令及模块来源。以下四项在 r16 已核齐，具体原件见 §5；中间 owner 探针停止记录保留在 §4.1–4.3。

本轮必要核对项：

1. 输入身份确为本报告 §1 的原件；R6 材料／四参考不变，实际采用的新镜像单独登记；不放宽 baseline 重建或改 candidate projection。
2. 前置安装窄验与正式安装段分别记录，各步 RC 与 wheel 实读 SHA；前置成功不能替代正式安装证据。记录候选目标源码 SHA、runner SHA 在前置前后不变。
3. 目标模块实际路径／loader／函数文件来自候选 `/testbed`，目标 meet SHA 为 `fda3ae…`；如出现 `.so`、意外 sys.path 或源摘要不符，只归档具体矛盾，不继续扩跑。
4. 四参考逐项实际执行与解析，missing／skipped／参考外解析为0；保留正式 diagnostics/report、baseline rebuild 与 cleanup 原件。

这些项齐备即足以结束本 ownership 边界的聚焦补证。失败也可以达到停止条件：明确是权限、模块来源或基线身份的哪一项未成立，再列最小下一步，不因还能想出理论反例而扩大全矩阵。旧 GPU raw1 保留原状，新证据与能力结论分列；不新增训练资格、状态机或样本拒绝规则。

### 4.1 v2 worker 的静态窄核与时间戳修正

仅阅读 `swe_mypy/gpu_original_regrade.py`，没有运行。v2 worker 字节 SHA `64754d020213034bcc64c10c8572a8401ee92e3254aee88a35c7da621e54f696`，`binding_v2.json` 字节 SHA `6bbcb0ea7d151a92e19a86f6294d25a4e6d9c30e40b4efa620cf60d4b19147cd`，均独立计算核实。原四份 original_file SHA、build/checkexpr 预期 SHA 仍与原件相符；新增第五份 prepared manifest 原件 SHA `54ddb36d25290e1daa12a0dfc8e5f58e71ce3b6c3ce8af9f14ca0c5831aa0ffe`。下列行号为 v2 版本；后续 v3/v4 仅修正安装元数据定位，见 §4.2–4.3。

初版 worker SHA `709ec88b62c040e18fd5d56e4996c10b5567cbe5752406299267925f7c57aaa8` 及 binding SHA `947f492e4c337e9196514e4e48e734e857b59e1d50d10b2a2986a4e9dee7b1d6` 曾完成静态窄核；r3 的原 slot stderr 证明其在 prepare 后第57行 manifest 全文件 SHA 相等断言失败。此时尚未构造 manager、创建 grader 容器或执行评分，不能把此停止当成候选失败。

独立比较 r3 fresh manifest 与 GPU 原 manifest：唯一变字段为顶层 `prepared_at_utc`，从 `2026-10-02T18:25:52.104300Z` 到 `2026-10-02T23:53:56.474301Z`；fresh 实际 SHA `262493d06bf5662392e8edd06dd0e959db0b8e3112dfbabd211b96debebb40c0`。其余全部字段相等，prompts／rollout／private 三份实际字节也分别相等。v2 57–78 行仅允许此顶层时间字段变化，保留 old/fresh 真 SHA／时间，以 fresh SHA 进入 load_context；未回填旧时间，也未放宽其他字段。binding 的其余变化仅为新不可变输入目录及此比较说明。这一修正合理，不是材料身份变化。

- worker 49–50、87–101 行校验输入字节、FP/baseline canonical digest、原 runtime identity、public identity、classification，重建正式 projection 并逐字段等于原 projection；没有改 FP 的原 GPU image 字段。CPU 实际 image 单独写到 spec。
- 31–34、55–86 行固定 release manifest／consumer SHA、prepared 的非时间字段／private SHA、材料 identity 及 scripts digest。binding 已说明三个兼容消费者与 GPU 有差异，不能宣称整个 code_v4 全树逐字一致；相等的是本题正式材料／脚本，manager 源码按绑定核验。
- 107–160 行以单独 `set -e` exec 逐条运行三个原安装命令，保存每次实际 exec 的 RC/stdout/stderr，任一步非0就停止。probe 强制验证实际 UID54322，实读 wheel SHA，验证目标模块文件／SHA／SourceFileLoader 与 meet 函数 `co_filename`。安装前后完整 modules 字典相同，覆盖前置安装对这些源码的影响。
- 146–163 行保留原 `_observe`，在 pre hook 中先执行原观测再插入前置安装，在 post hook 中先执行原观测再补动态来源。正式 manager 的 `RH2_OBS_RUNNER_DIGEST_PRE` 采于前置之前，后摘要采于正式段之后，可覆盖这一区间的 runner 文件变化。worker 没有替换 candidate test 脚本或修改其命令；正式评分仍由 manager 消费原 spec 脚本。
- 181–206 行不钉死预期 reward，只保存真实报告；无论成功失败都调用 manager.close，最后复核五份输入 SHA。worker 自报 completed 仍不是验收结论；必须回读 diagnostics、原日志及 close。

动态观测的限制明确保留：probe 是正式评分前后单独启动的 Python 进程，不是 pytest 进程内 `sys.modules` 跟踪；`SourceFileLoader` 仍可能读取 pyc，`PYTHONDONTWRITEBYTECODE=1` 只禁止新写入。结合 exact baseline 无 pyc／so、所测源码不变、四例不读增量缓存及正式 runner 不变，当前没有证据值得为此再修改测试脚本或扩大全套；如回执出现加载矛盾，再按具体矛盾止损。也不以这三个目标模块的来源声称所有第三方依赖均为纯 Python。

### 4.2 r8 原件回读与 v3 元数据探针修正

已回读根目录：`runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy10174-gpu-original-regrade-r8-20261003T000817Z-cca2a8/`。

| 可直接成立的事实 | 原件与限制 |
| --- | --- |
| 实际执行，未完成评分 | slot/status 为 slot1，child／wrapper RC1。slot/stderr 的调用栈停在 manager `_run_eval` 的 pre observation hook 中：after-install owner probe 返回后，host 对默认 distribution 的 `direct_url=null` 调用 `json.loads(None)` 产生 TypeError。attempt 下无 eval_logs、无 report；正式 candidate script／四参考尚未执行。 |
| 完整 baseline 与原投影被真消费 | 对 `baseline_rebuild_census.txt` 逐条比对：1472 个条目的 type／mode／内容 SHA 与原 manifest 全相等，无额外普通条目；仅 `.git` 排除记录及 cache omission 计数。projection 与 GPU 原文件字节相同。 |
| 三安装命令真实成功 | `install_step_1/2/3.json` 各 exec RC0。step2 stdout 包含 editable wheel build、卸载旧安装和 `Successfully installed mypy`，没有用段末 RC 替代这三份逐条结果。 |
| 前后候选源码未改 | `candidate_before_install.exec.json` 与 `candidate_after_install.exec.json` 的 exec 均 RC0；stdout 末行 JSON 内 UID/GID54322、正确 testbed Python，四模块完整字典逐项相同。目标 meet 的源码 SHA、SourceFileLoader、函数 co_filename 均正确。 |
| wheel 可读且字节相同 | 三 wheel 实测 owner0／0644，UID54322 实读 SHA 与绑定一致；前后 wheel 字典相同。 |
| 容器清理正常 | manager_close 实际 created1／removed1，containers_open／supply_open／cleanup_failures 均空。 |

r8 的默认 distribution 记录只有版本及 `direct_url=null`，未记录元数据路径。因此“源码目录的 egg-info 优先被选中”是合理解释，尚不能仅从旧 probe JSON 证明其精确路径；安装成功与 metadata 默认定位结果不是同一个判据。

v3 worker 独立实算 SHA `86ed921a2796bb389f7dc118e84fa1f69919485032132625d142da2a9ac7ee16`，binding 仍为 `6bbcb0ea7d151a92e19a86f6294d25a4e6d9c30e40b4efa620cf60d4b19147cd`。修正只在 probe 内枚举全部 mypy distributions，保存每份真实 path／version／direct_url，并在安装后要求至少一份位于 `site-packages/*.dist-info`，且 direct_url 为 `file:///testbed`、editable 为 true。默认 distribution 的 null 仍原样保存，没有改 sys.path，没有改 FP／baseline／投影／材料／正式脚本。这是探针定位修正，未把缺失安装元数据当作成功，也未改评分判据；静态范围合理。

r8 只补安装与源码来源证据，不能代替正式评分验收；须回读后续实际入 slot 作业的正式安装段、四参考、runner、cleanup 和输入 SHA，之后才作最终判断。v3 实际入 slot 的 r15 又暴露旧环境 finder 兼容问题，见下一节。

### 4.3 r15 停止原件、v4 最小简化及 r13 更正

已回读 `cpu_a_round1/mypy10174-gpu-original-regrade-r15-20261003T003159Z-762691/`：slot0 实际 child／wrapper RC1。完整 baseline census 的1472条 type／mode／SHA仍逐项等于原 manifest，无额外普通条目；projection 仍与原文件字节相同。`candidate_before_install.exec.json` 真 RC1，stderr 显示 stdlib `importlib.metadata.distributions()` 经旧 backport `importlib_metadata.find_distributions` 时，收到 Context 而非预期字符串，产生 TypeError。state 的 candidate_install_steps 为空，无 install_step 文件、无 eval_logs/report；这次既没有 owner 安装，也没有正式测试。manager 创建1／移除1，三类遗留均空。

v4 worker SHA 独立实算为 `2dd00b90921ff0ff13e97237db2816ef5dc8d93d5ccdb7b2532a3fc063cb9a67`，binding SHA仍为 `6bbcb0ea7d151a92e19a86f6294d25a4e6d9c30e40b4efa620cf60d4b19147cd`。当前 probe 116–125 行只用 `sysconfig.get_paths()['purelib']` 定位当前候选解释器的实际 site-packages，读取 `mypy-*.dist-info/direct_url.json`、METADATA 并记录文件 SHA；不再调用有兼容问题的 metadata finder，也不改 sys.path。安装后仍要求至少一份真实 site-packages dist-info 指向 `file:///testbed` 且 editable=true；源码／UID／wheel／原件身份及正式脚本限制全部保留。这一有限文件读取方案比继续修 finder 兼容链更小，静态修正合理。它只检查实际存在 direct_url 的 dist-info，不冒称完整枚举所有安装元数据；原 r8 的 null 观测已原样保留。

`gpu_install_revalidation_20261003/incorrect_admission_notice_and_correction.json` 记录 r13 曾误发 admission 后立即更正：实际 wrapper RC75、slot=null、没有 admission 文件。消息投递工具成功不是 slot 支持，r13 不计 CPU 执行或评分，亦不改任何成绩原件。编排方指出原因是本地 assert 退出后未检查返回码而继续发送文本，本报告保留此错误事实。

后续实际完成的作业为 `mypy10174-gpu-original-regrade-r16-20261003T003832Z-5650b3`，验收见 §5。停止条件保持 §4 四项，不因 owner 探针修复历史再追加 finder、metadata 版本或完整矩阵要求；探针失败不作为候选评分失败。

## 5. r16 完整原件验收与最终边界

原件目录：`runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy10174-gpu-original-regrade-r16-20261003T003832Z-5650b3/`。归档 `.evidence.tgz` 字节 SHA 独立实算 `e99e28b328b77da775c1271e270a6fb1633fd4a2fea2cb298e52086af506fb19`；归档内27个文件与已回传目录逐个字节相同。下面证据路径均相对该目录。

| 验收项 | 独立回读结果 |
| --- | --- |
| 实际执行与退出 | `slot/status.json` 为 slot0，固定 v4 worker，child RC0；`launch/receipt.json` wrapper RC0。不是仅派发／消息回执。 |
| 原输入身份 | state binding 的五份原件 SHA 与当前保留原件逐一相同；FP51条及原 runtime `32f313c8…` 未改，原投影50条／49cache未改。`attempt/projection.json` 与原 GPU projection 字节相同。 |
| 真实基线 barrier | `attempt/baseline_rebuild_census.txt` 的1472条 type／mode／SHA逐一匹配完整原 manifest，无额外普通条目；state 为 baseline_rebuild_passed=true。没有换小型基线、删去49个候选 `.mypy_cache` 条目或跳过 barrier。 |
| fresh 材料身份 | 当前 fresh manifest SHA `9712a5c400a73c731a02d6fd8c314f90212706a6ed0231404c92bb7819309831`；与原 manifest 仅 prepared_at_utc 不同。实际 prompts／rollout／private 字节均与旧 GPU 相同；R6 材料 identity 仍为 `dca86b80…`，scripts digest仍为 `f111e77d…`。 |
| 独立三步安装 | `attempt/install_step_1/2/3.json` 三条原命令实 exec RC0，无 Permission／ERROR／Traceback。step2 为成功 editable build／安装。这些属于前置窄验，不替代下一项正式段。 |
| 正式安装段 | `attempt/eval_logs/evallog_mypy10174-gpu-original-r_218c88d8.eval.log:426–514` 原三命令原样再跑，editable build dependencies 和 editable wheel build／安装均成功；diagnostics install_failed_commands为空、段末 RC0、install_skipped=false。 |
| 正式四参考 | 同日志519–541实际 pytest，9423 collected／4 selected，四个登记参考均 `PASSED`，test RC0；diagnostics parsed4、missing0／skipped0／outside0、candidate exec RC0、非partial。report 为 resolved／reward1／F2P1 of1／P2P fail0 of3。 |
| 模块与 wheel 来源 | 三份 `candidate_before_install`／`candidate_after_install`／`candidate_after_formal_tests` JSON及 exec 原件均成立：UID/GID54322，testbed解释器；四模块全部来自 `/testbed`、SourceFileLoader，三阶段完整模块字典相同。meet 为候选 SHA `fda3ae…`，函数 co_filename为 `/testbed/mypy/meet.py`。三 wheel owner0／0644且由实际 UID 实读正确 SHA，三阶段字典相同。 |
| editable 元数据 | purelib 为 testbed Python 的实际 site-packages，真实 mypy dist-info 内 direct_url为 `file:///testbed`、editable=true；direct_url SHA `de2b6e0a…`、METADATA SHA `7a8616ac…`，三阶段不变。此文件在前置安装前已存在，因此其存在本身不证明本次安装；本次安装证明来自独立 RC和正式安装日志。 |
| 可信测试与 runner | diagnostics 的 trusted restored／setup OK／保护OK均为1，apply RC0、absent／missing0；原候选测试修改未进入投影。runner前后均 `2f4655b6…`，runner_integrity_changed=false。 |
| 日志与清理 | 正式 eval.log 28740字节，独立SHA `6361be301a3e3d50c92e42024b64c654b363c31e9a35c2eb9f9fa2be670a8d29` 与report一致；manager创建1／移除1，containers_open／supply_open／cleanup_failures均空。没有额外regrade。 |

四个正式参考逐题结果：

| 参考 | 作用 | r16 实际结果 |
| --- | --- | --- |
| `testOverlappingAnyTypeWithoutStrictOptional` | 原 F2P：修复 Optional[Any] 比较误报。 | PASSED |
| `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional` | 新 P2P：仍应诊断真正不重叠的固定长度 tuple。 | PASSED |
| `testUnimportedHintAny` | 原 P2P。 | PASSED |
| `testUnimportedHintAnyLower` | 原 P2P。 | PASSED |

**F1 处置：accepted；本题能力补证已完成。** 本次 CPU正式重评分与原 GPU 四参考通过一致，且在安装成功、原FP/完整baseline、原投影含49cache、正确目标源码及可信测试条件下再现。没有成立的证据支持把原 GPU安装缺陷直接转成模型负例，也没有发现该49cache造成这四参考假通过的实际路径。

剩余边界直接保留：

- 这次正式评分前额外执行了完整三步安装，随后原正式脚本再次安装；它证明该预热条件下候选四参考通过，不冒称一模一样的冷安装复现。
- 来源 probe 是独立 Python进程，不是pytest in-process跟踪；SourceFileLoader／源码SHA／函数文件及既有测试实现共同支持本题模块来源，不能追溯证明旧GPU未记录的具体加载状态。
- diagnostics 的 `resource_facts=null`、`env_qualification=absent`；回传包没有另附 ledger。仅依据实际slot、manager close、diagnostics及原日志判断执行与清理，不冒称新增HostConfig检查或完整账本审计。
- CPU可读镜像是 `9d63f1dd…`，旧 GPU镜像是 `32f313c8…`。GPU builder公开wheel权限修复仍由GPU方按其运行入口处理，本报告不声称GPU新镜像已修好，不改原FP runtime字段、不回填旧raw1。
- r3、r8、r15的owner工具问题和r13误通知仍保留；它们不计候选分数，也不增加模型尝试次数。r16是同一候选的窄重评分，不是第二次模型解题。

停止条件已满足：本题有限能力结论可保留；当前边界不再扩跑，不新增metadata／版本／旧矩阵／训练资格门槛。若后续新的GPU派发仍使用旧权限缺陷镜像，应按具体环境缺陷处理，不能以本次CPU补证替代该环境修复。

**最终状态：限定通过——原候选 CPU 正式重评分及所需补证核实；旧 GPU 安装异常历史保留，GPU新镜像修复不在本次已验证范围。**
