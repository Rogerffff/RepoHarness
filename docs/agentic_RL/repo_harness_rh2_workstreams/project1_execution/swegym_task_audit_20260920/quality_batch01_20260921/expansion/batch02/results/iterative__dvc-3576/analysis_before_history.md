# iterative__dvc-3576：历史开放前静态分析

审查日期：2026-09-21。角色：新上下文私有主审。本文在未读取本题旧质量调查、history refs、批次报告或其他题结论时封存；以后变化写入 `old_findings_delta.md`，不回写本文。实际操作只有静态文本读取、目录/元数据检查、SHA-256 校验和本文写入，没有运行项目、测试、安装、容器、SSH 或模型。

暂定处置为 `needs_review / static_review`，用途 `development_diagnostic`。决定性问题是**当前一行 gold 和一条 F2P 只覆盖“空结果辅助函数不返回提示”，而公开题面要求的缺旧值展示及 STDERR 分流没有完整交付**。同时存在命令层合理解可能被私有辅助函数断言拒绝的具体路径。09-19 原始 grader 对照可解释，不能据此把题面完整性或 actor 开发条件记为已通过。

## 证据路径约定与身份

权威根 `ROOT=.`。下文所有相对路径均相对此根：

- `P=runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-3576`，`B=P/base`。
- `V=runs/swegym_quality_batch02_20260921_v2/private/iterative__dvc-3576`。
- `R=runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3576`。
- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_4d6e3c69.eval.log`，SHA-256 `fdb62b21f6a3b8434cff8f3a35d3344e443328c8e6819e0eb879ca6ef3fdb3c4`，616 行。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_9ae4a68d.eval.log`，SHA-256 `58381050676ad1ea34df0c0247a7289790acb78e1212332af26584b7258828e5`，611 行。
- `O=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/iterative__dvc-3576`。

两份日志的摘要都已对原件字节重新计算，并与 `V/run_refs.json` 核对。本文的 G/N 行号只对应上述原件，不能移用到重跑或其他摘要版本。

`P/public_bundle.json`、`V/grading.json`、`V/validation.json` 与各自指定 S2 文件第 **123** 行解码后逐字段相等：`s2/ingest/public_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl`、`validation_bundles_v0.jsonl`（前缀为 `docs/agentic_RL/repo_harness_rh2_workstreams/`）。仅向上下文展示、解码本题指定行，未展示其他 S2 题目行。

三者一致指向 base `a338fad036bd9ac8bdd79ecec964f8c5558609c4`；材料记录 tree `46b91cfd4dc0e4e28cfda90e0a1b03895736ad24`，349 个导出 blob，无 gitlinks、LFS 指针或 `.git`。本轮没有重新从 Git 对象证明整棵 tree；对关键文件另作摘要记录。公开镜像 digest 是 `sha256:398036ee0fbb99c24dc50037d0f316c299c70caf154d579facf6ae42a6197c0b`。本次引用的 grader 实际使用本地派生镜像 `sha256:0c322496575e0bca8592b7114fc069fab01cfabc225944b51346a97871533cf8`，不能把两者混称相同环境。

## 1. 公开目标与初态（检查 1–3、23、27）

`P/user_prompt.txt:3–36` 要求：有效旧 revision 上没有指标文件时仍显示新值；示例 Change 为 `-`；JSON 支持缺少旧值；诊断有意义；STDOUT 只放结果，`No changes.` 等其他消息到 STDERR。第 26 行的 STDIN 笔误由第 36 行明确的 STDERR 总结消解。错误文案用 “something like”，没有逐字要求。“单侧缺失成功比较”和“旧文件未找到错误”有一定张力，不能为了字面错误示例把正常比较改成失败。

当前 base 已包含题面的一部分目标：`B/dvc/repo/metrics/diff.py:78–100` 使用 `.get(rev or "", {})`、捕获 `NoMetricsError`，并合并新旧路径；`:20–34,47–75` 对缺侧返回 `old/new=None`，数值双方存在才算 `diff`。`B/tests/func/test_metrics.py:978–989` 已公开期待新指标的 `old: None`，`:992–1007` 期待删除指标的 `new: None`。所以不能据旧 issue 的 `unexpected error - 'HEAD^'` 断言当前 base 仍复现同一个 KeyError。

仍在源码中明确存在的目标差异是 `B/dvc/command/metrics.py:111–112` 返回 `No changes.`，`:128` 无差值时输出 `diff not supported`。命令在 `:147–152` 经 INFO 写 JSON 或表格；`B/dvc/logger.py:164–183` 把 INFO 发往 STDOUT，WARNING 及以上才到 STDERR。

这不是“初态已经全部修好”：N:570–577 确实记录当前 F2P 失败于旧字符串。它也不是题面原 CLI 复现的证据：本次历史执行只跑 helper/Mock 单元测试，没有实建缺旧文件的 CLI 案例。

公开消息还须分层：`public_hints` 声称 conda 已激活并禁止改测试，但 `P/environment_brief.md:3–12,20–26` 明确只是静态材料，实际 CLI 系统消息、工具 shell、身份和依赖尚未验。无 `.git` 的静态源码导出不能代表真实 actor 的 Git 体验。

## 2. 全部变更断言、F2P/P2P 与双向映射（检查 18–20、25、32）

`V/test.patch` 仅修改 `tests/unit/command/test_metrics.py:67` 的一个断言：`_show_diff({}) == "No changes."` 改为 `== ""`。没有新增 fixture、helper、Mock 或其他测试文件。F2P 为 1，P2P 为 6；已逐条读完七个测试体，而非按文件名推断覆盖。

下表测试名均带前缀 `tests/unit/command/test_metrics.py::`：

| 参考身份 | 输入、调用及完整验收重点 | 实际证明/公开依据与限制 |
| --- | --- | --- |
| F2P `test_metrics_diff_no_changes` | 直接传 `{}` 给 `_show_diff`，要求返回精确空字符串；无测试参数 fixture、无 Mock、无 stdout/stderr 捕获 | 与“结果流无状态提示”有关，但把 CLI 流要求收窄成私有 helper 返回值；既不要求 STDERR 有提示，也不调用文本 CLI。N:570–577 失败，G:606 通过。 |
| P2P `test_metrics_show_json_diff` | 输入 `old=1,new=2,diff=3`，精确断言表头、空格、Value=2、Change=3 | 只检查展示收到的 diff；名称虽有 JSON，但不序列化 JSON，不验证 `new-old`。输入 diff=3 也表明它不是数值计算测试。公开表头/列义有依据；空格来自旧测试而非 issue。 |
| P2P `test_metrics_show_raw_diff` | 输入原始字符串 `old="1",new="2"`，缺 diff，断言 `diff not supported` 及表格布局 | 保护旧非数值展示；不覆盖指标读取或 Git。 |
| P2P `test_metrics_diff_no_diff` | 输入嵌套名 `a.b.d`、`old="old",new="new"`，缺 diff，精确断言旧 Change 文案 | 保护旧字符串变化展示；不是“无变化”，也不做 flatten。 |
| P2P `test_metrics_diff_new_metric` | 直接输入 `old=None,new="new"`，仍精确要求 `diff not supported` | 能保护新值显示，不核缺旧文件能否读取；对统一将缺旧侧 Change 改成 `-` 的自然 formatter 修复形成冲突风险。该样例为字符串，issue 示例为数字，因此不能宣称任何满足数字示例的实现都会被它拒绝。 |
| P2P `test_metrics_diff_deleted_metric` | 输入 `old="old",new=None`，精确要求 Value `None` 和 `diff not supported` | 保护删除指标旧展示。删除语义不是本题要求改变的目标；保留有依据。 |
| P2P `test_metrics_diff` | `parse_args` 解析两个 revision、targets、json 类型、xpath、recursive、`--show-json`；断言命令类、退出 0；Mock `dvc.repo.metrics.diff.diff` 返回 `{}` 并 `assert_called_once_with(cmd.repo, ...)` | 真实命令调用和参数转发有覆盖；实际 diff 数据层被整体替换。未断言 JSON 内容/流向；G:597–600 的 `{}` 是运行捕获，不是新 JSON 验收断言。Mock 的内部调用形状有实现耦合，但当前没有把它另判为已证实误拒。 |

直接 helper 测试只受共同测试导入及 autouse 环境影响：`B/tests/conftest.py:11–28` 设置 DVC_TEST、DVC_IGNORE_ISATTY 并按 pytest log-level 重设日志；`:55–60` 最后关闭远端池。唯一命令测试的 `dvc` fixture 经 `B/tests/dir_helpers.py:217–243` 建临时目录、切 cwd、初始化无 SCM 的 DVC 仓库（该测试没有请求 `scm` fixture）；`CmdBase.__init__` 打开该 repo 并检查 updater（`B/dvc/command/base.py:30–40`）。这不可能复现有效 Git 父版本中缺指标文件的场景。`mocker` 来自 pytest-mock。未调用 ssh/http server fixture，不能把导入 mockssh 当成本题需要远程 SSH 服务。

| 公开要求或合理旧行为 | 公开源码/旧测试依据 | 参考保护程度与下一证据 |
| --- | --- | --- |
| 单侧缺旧指标仍能成功，显示新值 | prompt:4–20；`diff.py:78–100`；func:978–989 | 部分：P2P 只喂已造好的 diff 给 formatter；Git/show/diff 真实链不在实际 7 项中。后续本地双版本 CLI 对照。 |
| 缺旧值 Change 为 `-` | prompt:15–19 | 未覆盖数字原例；旧 P2P 对字符串缺侧仍固定另一文案。gold 未改 `metrics.py:128`。 |
| JSON 缺旧值、保留可计算的正常差值 | prompt:22；`diff.py:20–34`；func:912–989 | 底层已有公开行为和测试，可支持 `old:null` 且缺 diff；这些 func 测试没有被此次评分选中。P2P JSON 命名不能替代真实 JSON 验证。 |
| 无变化状态从 STDOUT 到 STDERR | prompt:26–36；logger:164–183 | F2P 只部分测到“不返回提示”；没有 stream 或 stderr 正向断言。gold 只删除提示，仍由 caller 执行 `logger.info("")`。 |
| 有意义错误；不能把无效 revision 吞成缺文件成功 | prompt:24；`scm/git/__init__.py:348–377`；`scm/base.py:8–24` | 七项参考没有异常路径；base 自有 `RevError`。缺文件警告与有效旧 revision 无文件应分开。 |
| 参数和命令成功返回值 | `metrics.py:135–158`、公开 CLI 和旧 command 测试 | P2P `test_metrics_diff` 覆盖该组参数及 Mock 返回时退出 0。默认值、文本流向不是它的断言。 |
| 正常数字、raw、删除、空数据和坏 JSON | func:882–1007；unit:41–85 | 六个 P2P 中五个只保留 formatter 行为；真实计算、JSON flatten、坏 JSON 与双侧无指标有公开功能测试，但此次未执行。是已定位的保护范围，不单凭此覆盖空白判坏。 |

## 3. 合理替代路线与自然部分修复（检查 24、25、28）

一个合理非 gold 路线是保留 `_show_diff({})` 的旧返回约定，在 `CmdMetricsDiff.run` 的空 diff 分支直接把状态送至 STDERR、避免向 STDOUT 发送该字符串；非空 diff 正常渲染，并在命令使用的展示策略中让缺旧值 Change 为 `-`。原 `_show_diff` 私有接口没有被 issue 指定必须返回空字符串。CLI 用户可见行为能正确，而 F2P 仍会因直接调用旧 helper 返回 `No changes.` 而失败。这是**有明确代码路径的静态误拒假设**，尚未构造候选或拿到 RH2 分数，不能写成已运行反例。

如果保持所有 helper 默认行为并给命令层提供单独/可选展示策略，既能满足缺旧值用户输出，也能通过旧非空 P2P；因此不把 `diff not supported` 旧断言的存在升级成“题目绝对无解”。另一种自然实现直接在 formatter 统一替换该文案，则会被字符串缺侧 P2P 拒绝；应依据题面变更范围评审该断言，不应要求 solver 猜 gold 的一行改动。

无需机械制造恶意补丁：**gold 自身就是最自然的部分修复**。它只返回空字符串，删除了文本模式状态输出；既没有新增任何 STDERR 发送，也没有改 Change 的默认文案。已有真实 grader 对照证明这份补丁获满分；源码对照支持它未交付完整公开目标。CLI 的实际字节输出仍应另核。`logger.info("")` 根据 `LoggerHandler.emit`（logger:105–111）预计仍向 stdout 写换行，所以“helper 空字符串”等同“CLI 完全无输出”也未经证明；空行本身是否算用户可见违规不作为主要判坏理由。

## 4. gold 完整性、调用者与回归（检查 26–27）

`V/gold.patch` 的 SHA-256 为 `adee4b502b36c8feff0555f049affabef2bf4f043e14c56efad7c2184ffc3f10`，和 validation 原行及 gold ledger 中候选摘要一致，只改 `dvc/command/metrics.py:112`。G:162–173 显示这一个业务变化到达 grader。没有新依赖、跨文件缺失改动或隐藏普通源码 test patch。

静态追踪的生产调用链为 `CmdMetricsDiff.run → Metrics.diff → repo/metrics/diff.diff → _get_metrics → metrics.show → brancher`。仓内 `_show_diff` 生产引用只有 `metrics.py:152`（另有本文件定义和单元测试），没有查到其他生产调用者。gold 不改真实比较层，暂未发现它引入数字/删除/坏 JSON 等数据层回归；这不等于完整回归已通过。

已展开 `B/tests/func/test_metrics.py:882–1007`：raw 比较及 unchanged；JSON 的 xpath True/False 与 unchanged；坏 JSON 的 `unable to parse`；无指标；新增和删除指标。也读了 `:815–879` 的缺文件警告与 targets/xpath 相关旧行为。这些可作为后续窄回归，**不在当前 F2P/P2P 参考中，也没有本次运行证据**。日志执行命令明确只选 unit command 文件。

若采用共享 logger 变更，`B/tests/unit/test_logger.py` 的格式、handler level 和 progress 行为是相关回归面；已静态读完 249 行，未运行。`B/dvc/main.py:87–88` 在错误退出时通过 INFO 打支持页脚，`logger.py:171–176` 的 DEBUG handler 也指向 STDOUT；这些是在“所有其他消息到 STDERR”宽解释下的具体可达路径，当前 gold 未处理。不能据此擅自要求重设计所有 DVC 子命令。

## 5. 历史真实执行、配方和证据强度（检查 6、9、13–15、18–22）

两条原 ledger 均已读完整第 1 行：

| 条件 | gold | noop |
| --- | --- | --- |
| ledger | `R/gold/ledger.jsonl:1`，SHA `fb87b26a4aaaab538ceb454414c5de04ce5afd1bffe42ff745de2c0e191bfb6f` | `R/noop/ledger.jsonl:1`，SHA `902754ae69311885ebf95002786c99f276973a4e1d648c5b7d25c8305b38a7a0` |
| run_id / attempt | `er19-dv1-iterative__dvc-3576-gold` / 1 | `er19-dv1-iterative__dvc-3576-noop` / 1 |
| 来源结果 | reward 1，F2P 1/1，P2P 6/6 | reward 0，F2P 0/1，P2P 6/6 |
| 原日志执行 | G:574–581 收集并运行 7 项；:602–609 七个 PASS；:613 test RC=0 | N:560–567 收集运行 7 项；:570–577 helper 断言失败；:597–608 六 PASS/一 FAIL、RC=1 |
| 安装 | G:367–378 editable 安装及构建元数据；:544–564 built/installed、RC=0 | N:353–364 同一安装入口；:530–550 built/installed、RC=0 |
| parser / 参考命中 | `swebench-4.1.0+swegym_parsers@242429c1`；7 parsed，outside segment=0，missing=[]，skipped=[] | 同版本、同数目、无 missing/skip |
| 源码生效观测 | 导入 `/testbed/dvc/__init__.py`；版本 `0.92.0+a338fa.mod`；已投影 `dvc/command/metrics.py` | 同导入/版本；候选 included_paths=[] |

以上安装与测试有原日志支持；parser 的集合/判分来自指定 ledger/diagnostics，未在本轮执行 parser。不能只用 PASS 文案推导端到端 CLI 原例；这里结论限于七个实际测试体和已展开断言。

`R/{gold,noop}/recipe/recipe.json` 两份原件均为 SHA `caf3f5d32831e7087e56c897cf5ffd6376b2ed4f0254a267952a33e98a345fdf`，内部 recipe SHA `ec7d3c0e2d15df581292c422eb5cd0cdf4a964ef34c1c275a9eb727ef82c9580`。修订入口 `python -m pip install -e '.[all,tests]'` 取自该 base 实际 extras（setup.py:148–158），函数返回保存的安装 RC。原入口带浮动升级、无效 extras/缺失 requirements 尝试和 `|| true`；修订前后脚本 diff 只改安装段，没有换测试或 reward。

G:175–185 和 N:161–171 同时展示已有环境初态改动 `moto==1.3.14.dev464 → moto==1.3.14`。它不是 gold 业务补丁，也不是候选额外修复。当前 exact-base 导出仍保留 dev pin；开发配方必须明确是否消费这个环境差异，不能直接把公共 base 的重新安装视作已验证同条件。安装日志指向 `/opt/rh2/build-wheels`（G:369、N:355），候选安装/测试记录为 deny_all。

两条 ledger 都记录 `rh2grader/54322`、2 CPU、4 GiB、PID512、shm64 MiB、tmp1 GiB、可写解释器前缀 `/opt/miniconda3/envs/testbed`，并记录 cleanup removed=true；diagnostics 同时记录 `env_qualification=absent`、`resource_facts=null`。观察内存峰值分别约181/232 MiB，不能外推 actor 或并发容量。这里只有各一次对照，没有重复稳定性/并发验证。apply_user 虽是 agent/54321，也只是脚本应用 gold/noop，不是该身份实际运行开发工作流的证据。

## 6. 具体 actor 开发条件（检查 6–15、33–36）

| 必要操作/资产 | 公开依据与已核证据 | 未知与最小建议（均未执行） |
| --- | --- | --- |
| 定位与修改入口 | `metrics.py:108–158`、diff.py 全文、旧 tests 已齐；普通 Python 源码 | 合法改动可在 `dvc/command/metrics.py` 或明确相关模块，不需要写系统包或不能提交的资产。当前公开工具/真实消息仍未捕获。 |
| Python 与目标源码导入 | setup.py:162–174；grader Python3.8.19、pytest7.4.4（G:576、N:562），导入观测为工作区 | actor/54321 的 PATH、激活、读写权限未知。建议先记录 `id`、`python -V`、`sys.executable`、`dvc.__file__`，再导入目标命令/比较模块。优先从 `/testbed` 或 `PYTHONPATH=/testbed` 用现有依赖验证。 |
| 依赖与离线安装 | setup.py:49–85 的 flatten_json、texttable、JSON/Git/YAML 等；tests extras 含 pytest-mock、mockssh、RangeHTTPServer；conftest 在收集期导入后两者 | grader 修复入口已成功，但 actor 未证明有同一派生镜像、wheelhouse 或包前缀写权限。准备阶段固定依赖；解题不需公网；候选安装与测试已有 deny_all 证据。必要时离线 editable 安装须保留正确 moto 配方及安装 RC，不能由 solver 升级成未来 DVC。 |
| 本地 Git/临时 DVC 仓库 | func:882–1007；dir_helpers:89–107,217–255 | 原例需要有效父 revision；不能用只有一个提交的 HEAD^ 制造无效引用。建议 `git --version` 后在新临时目录生成 stage/JSON、至少两个提交；actor 的 Git 身份和临时目录写入待验。 |
| 自包含指标和日志捕获 | 旧测试现场写 JSON/raw，无权重、GPU或云资产；show.py:225–234 区分缓存/Git/工作区 | 可用本地生成数据，不需原用户指标文件。建议复用 `O/public_read.md:109–138` 的三提交场景，分别捕获缺旧文件、无旧 stage、unchanged 的文本/JSON stdout/stderr 和退出码。 |
| 收集期工具与资源 | tests/__init__.py:30–36 设置 NOFILE/NPROC；conftest:3–8 顶层依赖；公开默认资源只是说明 | 建议 `DVC_TEST=true PYTHONPATH=/testbed python -m pytest --collect-only -q tests/unit/command/test_metrics.py tests/func/test_metrics.py -k metrics_diff`。通过收集后再跑窄 func diff 测试；环境异常与行为失败分开记录。 |
| 修改后的回归验证 | 真实数字、missing/new/deleted/raw/broken_json 在 func 的具体断言；共享 logger 测试 249 行 | 建议 `python -m pytest -q tests/func/test_metrics.py -k metrics_diff`；涉及 logger 才补 `tests/unit/test_logger.py`。不把旧 formatter 冲突断言一概算功能回退。无需全仓测试。 |
| 编译/提交 | setup.py 只有包构建/版本固定和 console entry；gold 是一行 Python 变更 | 没有本题专属 native 构建需求；环境依赖可能含预编译包，不能据此说全环境无编译。提交仅源码可行；不需交付复现数据或改受恢复的官方测试。 |

`DVC_TEST=true` 与已读 conftest 保持一致；它是测试抑制后台活动的设置，不是网络隔离证明。真实模型消息、真实工具 shell、实际 actor 镜像消费、公开 Git/包可见性、资源与交付全部仍待验证。未估算 tokens、费用或新 CPU 耗时。

## 7. 候选投影、官方恢复与控制面（检查 4、16–17、21–22、29–31）

- `test.patch` 只触碰 `tests/unit/command/test_metrics.py`，没有普通业务源码混入。G:188–228、N:174–214 显示从本题 base 恢复这个文件、应用 test patch、检查存在且非 symlink；各自 diagnostics 记录 expected/protected files=1、missing=0、protect_ok=1。**冻结/恢复保护范围是一份具体文件，不是全部测试文件名通配。**
- gold ledger 的投影包含 `dvc/command/metrics.py`、ignored_paths=[]，G:162–173 证实业务变化存在；无 candidate test-like path 或 conftest 触碰。合法解可修改的业务入口未被这次恢复覆盖。其他新增/删除/rename 形状和改变 logger/config 的真实交付未在本题验证，不能泛化 pass。
- 公开 hints 的“全部测试重置”解释过宽。若禁改测试指令真实适用，仍可用源码完成公开目标，但不能通过编辑本题官方 unit 文件来躲过冲突；若不适用，官方文件恢复仍意味着这些编辑不改变本次来源验收。两种条件都不能静默更改 reward。
- 配置和 conftest 仍是通用评分控制面；本题原件没有给出特有作弊已成功证据，未另行运行攻击，也不据猜测追加排除。`file_rules.additional_exclusions=[]`。
- 仅参考当前卡说明的共享机制，不复审平台 parser/隔离实现，也未从旧平台报告借结论。来源 runner 与 RH2 的独立并排重放没有新证据。两条 RH2 replay 只支持这里已列条件。

## 8. 关系、暴露与用途（检查 5、29–30、37–40）

当前可核的是 base/题面/一行 test patch/一行 gold 的对应关系；没有读取其他题或未来提交，因此不声称与 4166、1681 或任何同仓题同族/独立。跨题关系待各自材料开放后按具体 commit/补丁核验，不能因同仓库/文件自动归并。

题面给出了预期表格和流向，但没有给出 gold 的 helper 返回修改；没有外部补丁链接。README/贡献文档含上游/文档地址，未访问。静态包未导出 `.git`，不足以证明真实 actor 看不到未来对象、镜像缓存或预装答案；当前没有该题特有泄漏实测。网络拒绝和工具可见性同样不能由说明当成已验。

本上下文已经见过本题公开读稿、test patch、gold、隐藏参考列表、grader 日志与配方，只能用于开发诊断，不可向未来 solver 提供本文，也不能称独立盲解。`V/environment_record.json` 含 `verified_environment_pair` 汇总及 analysis/history 链接，**已见汇总，但没有沿这些链接读取 `analysis_68.json` 或任何旧质量结论**。两条 `run_refs` 指向的原 ledger/log/diagnostics 已按任务授权独立核对。公开读者的文件是先行独立产物；本主审自己的初判不再称公开盲审。

## 优先后续实验与未决项

唯一优先实验建议是：在明确实际 actor 配方后做一个**base/gold/命令层合理替代解的窄对照矩阵**。同一自包含 Git 指标仓库分别比较“有效旧 revision 缺文件”和“HEAD 无变化”，文本/JSON 均独立捕获 stdout/stderr/退出码；保持原 F2P/P2P 不变，再记录三个变体的 RH2 结果。替代解保留旧 `_show_diff({})` 返回，通过命令层分流并完成缺侧 `-` 展示，用于区分“公开行为正确但 helper F2P 失败”；gold 则用于区分“原分数满分但公开行为部分缺失”。预期来自上述源码推断，尚未执行、不得登记为已证反例。

这个实验不需要真实模型，也不要求重跑全池。先查实际 actor 导入/依赖只是同一对照的前提，不能被历史 grader 成功替代。后续若要改公开范围或测试 oracle，应保存修订版并独立复核；原题、原测试、gold 和 reward 本轮不修改。当前具体语义争议妨碍把原版称为完整需求诊断候选，因此保留 needs_review，不将环境维修成功改写为题目已合格。

## 实际阅读范围与摘要附录

共用材料只读了 `quality_batch01_20260921/roles/investigator.md`、`record_template.md`、`actor_environment_card.md`，以及明确引用的八方面协议、40 项清单、记录定义。未读 B1/B2 README、manifest、批次报告、method_adjustments、reviewer 或其他题产物。

本题完整显示：P 根四份材料、O/public_read.md（被工具截断的一小段后来补读）、V 的全部 JSON 与两个 patch、两条 ledger 第1行、两份 recipe.json、两份 diagnostics、gold 的两份 after 脚本；before 脚本仅显示与 after 的安装差异并作全文 hash，noop 四脚本作 hash 与 gold 同名文件一致。没有把 hash 读取等同全文人工阅读。

业务文件完整展开：`B/dvc/repo/metrics/diff.py`、`metrics/__init__.py`、`repo/brancher.py`、`logger.py`、`main.py`、`dvc/__init__.py`；`B/tests/unit/command/test_metrics.py`、`tests/conftest.py`、`tests/__init__.py`、`tests/unit/test_logger.py`；setup.py、setup.cfg、pyproject.toml、CONTRIBUTING.md。按段展开：`dvc/command/metrics.py:1–290`、`command/base.py:1–58`、`repo/metrics/show.py:150–313`、`scm/git/__init__.py:338–379`、`scm/base.py:1–35`；`tests/func/test_metrics.py:735–1007`、`tests/dir_helpers.py:1–280`、`tests/utils/httpd.py:1–60`；README:85–156。`rg` 在本题 dvc/tests 中检索 helper/metrics.diff/No changes 调用，另看见 checkout 的两处命中行而未展开整文件；目录检索确认只有顶层 tests/conftest.py。

原日志实际展开 G:1–235、351–380、544–616，另对 G 做安装/测试/恢复关键词搜索（长依赖列表部分输出截断）；N:130–218、340–366、495–611。两份日志全文字节参与 hash，但未把未展开的重复激活/依赖行记成人工全文审读。安装主体、开始/结束/退出、失败摘要和七个测试 ID 都已从上述精确原件核对。

关键文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| P/public_bundle.json | `09fb663348597fb7573e877c8b5077bd6c5ded5afeef1402bed938c846a72186` |
| P/base_identity.json | `285d0e20f859b1f91201003f877c963e27f06665a6171e76f233905aaf7ec6fc` |
| B/dvc/command/metrics.py | `64908638202383032cfeac0e3ccdb717f5480100752160a07fe9c01672270b9d` |
| B/dvc/repo/metrics/diff.py | `06ccc7d500c52978fe07ea2077b914759be6c75849a0f6285ab98dfbf674d0bf` |
| B/tests/unit/command/test_metrics.py | `8efd9c232996382fd3a18e7fa1cf6686d5f8a5383b20860745e3a6989829ba8c` |
| V/test.patch | `dae0cb170c61875ccba606af02e593353a3a75585efe3b199db946c3feefdbfe` |
| 两角色 recipe/candidate_test_script.after.sh | `c2d8bc99952c91ad393baef3667afa208ebc5c011d87ed873942152e6a20125d` |
| 两角色 recipe/candidate_test_script.before.sh | `f30d6c268a11869a011a41d00c4cdd5e92e290d465c6d6b3cda96701818fe497` |
| 两角色 recipe/eval_script.after.sh | `e0d62d47c936e34605efe625709627197e0dcd7e1a78bbbf7dcd48d4445d2836` |
| 两角色 recipe/eval_script.before.sh | `5ef0b7ab591ac0d3f5dacf3c370211102c92a6d4614206b973ff08a41f9e1d8e` |

以上10份 recipe 审计文件（两角色各5份）实际摘要与 `V/environment_record.json` 中指定记录全部相符。这里只封存历史前分析；尚未开始历史对照、短卡或 screening JSON。
