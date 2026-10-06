# iterative__dvc-9395：公开视角静态审查

审查对象为公开包指定的 `c75a5583b3840ba90a8e800a0f42c1cb120916db`。下文路径均相对于 `PUBLIC_DIR`，源码路径以 `base/` 开头。只读取角色卡及本题公开包，未运行项目代码、安装依赖、访问网络、查看私有材料或修改 base。

核心需求可定位：让 `dvc repro --pull` 也恢复本次复现需要的、无命令数据源的缺失输出，同时保留已有运行缓存恢复功能。公开源码和旧测试足以构造一个仅使用本地目录远端的复现；真实解释器、依赖和 actor 运行条件仍未验证。以下不作通过或淘汰判断。

## 1. 需求表

| 行为 | 约束性质 | 公开依据及解释 |
| --- | --- | --- |
| `dvc repro --pull` 拉取此次 repro 必需的缺失文件，不能仅支持运行缓存输出 | 明示 | `user_prompt.txt:3–11`，尤其第 9 行明确指出只有输出、没有命令的 `.dvc` 数据源目前需要另行 `pull`；第 11 行将范围限定为本次 repro 所需。 |
| 需要恢复数据源到工作区，使依赖它的后续阶段能够继续 | 可合理推知 | `base/dvc/stage/utils.py:140–143` 检查输出路径是否存在；`base/dvc/stage/__init__.py:563–584` 对无命令阶段只做该检查。只把对象下载进 cache、仍让工作区源文件缺失，不能满足用户诉求。 |
| 保留现有运行缓存恢复，并在有可用缓存时避免无谓重跑命令 | 题面描述既有能力；公开测试约束 | `user_prompt.txt:4–9`；`base/dvc/stage/cache.py:178–213`；`base/tests/func/test_run_cache.py:161–185` 要求 `pull=True` 后恢复输出、不调用命令运行函数、重建 lock 文件。 |
| `--pull` 仍为显式选项，默认关闭；普通 repro 的已有行为保持 | 接口与公开测试可合理推知 | `base/dvc/commands/repro.py:129–137`；`base/tests/unit/command/test_repro.py:4–28` 检查默认 `pull=False`；`base/tests/func/test_repro.py:656–668` 在未加 pull 时删除数据源，期望 `ReproductionError`。 |
| 拉取范围应随本次目标、依赖图及已有筛选参数确定 | 明示限定加现有接口 | `user_prompt.txt:11`；`base/dvc/repo/reproduce.py:79–128,230–266`；`base/dvc/commands/repro.py:52–105,114–127`。标题的 “all missing files” 不能单独解释为无条件拉取全仓所有无关数据。 |
| 不覆盖仍存在的用户数据源修改 | 公开旧行为可合理推知 | `base/tests/func/test_repro.py:270–284,671–685` 明确先修改源数据，再要求 repro 使用新内容、记录新 hash。自动拉取应避免把“已修改”简单当作“缺失”而还原旧数据。 |
| `--dry` 不实际执行阶段，也不引入新的下载/检出副作用 | 接口、代码和公开测试可合理推知 | `base/dvc/commands/repro.py:138–145`；`base/dvc/stage/cache.py:201–213` 以 `not dry` 保护下载和检出；`base/tests/func/test_repro.py:287–305`、`base/tests/func/test_run_cache.py:54–67` 检查 dry 行为。 |
| frozen 阶段不重新运行命令、不遍历其被切断的上游依赖；其缺失输出可能仍需恢复 | 前半是现有约定；新增恢复范围需区分 | `base/dvc/repo/reproduce.py:230–239`；`base/dvc/stage/__init__.py:573–584`；`base/tests/func/test_repro.py:508–536,559–599`。题面未单独点名 frozen；把所需的 frozen 输出当作数据源式恢复是合理扩展，不能以此授权重新运行 frozen 命令。 |
| 文件、目录、工作区缺失和缓存缺失应分别分析 | 目录支持可合理推知；部分组合未定 | `base/dvc/commands/stage.py:159–166` 明确输出可为目录；`base/dvc/output.py:576–611` 区分缓存和工作区状态，`1034–1129` 支持目录对象和子对象。题面没有给出部分目录文件缺失、目录同时有本地修改时的合并规则。 |
| 帮助文案应反映扩展后的用途，但没有指定新文案或内部方法名 | 合理推知；具体文字未定 | 题面正是引用旧帮助来解释限制；当前帮助在 `base/dvc/commands/repro.py:133–135`。无任何公开要求固定新增 helper 名称、日志全文或内部调用次数。 |

“全部”仍受可恢复信息约束：公开对象收集逻辑排除 `cache: false`、未记录 hash 的输出和部分导入情形（`base/dvc/output.py:1069–1101`，`base/dvc/stage/__init__.py:713–724`）。这不等于必须为缺失的任意 Git 文件、未跟踪文件或根本未上传的数据寻找下载来源。缺失数据不可恢复时不应报告成功；准确错误类型、错误文案及是否继续尝试其他输出，题面没有新增规定。

### issue、harness 指令与环境声明分开记录

- **Issue 需求**：`user_prompt.txt:3–11`，以及 `public_bundle.json:1` 的 `problem_statement`。内容一致，指向 repro 的行为扩展。
- **Harness 操作指令**：`public_bundle.json:1` 的 `public_hints` 要求探索代码、修改非测试源码、不得修改测试、测试运行保持窄范围。它们不是 DVC 产品需求。本题从公开结构看可以用非测试源码完成核心行为，无需修改测试才能表达的配置或测试资产；尚未发现该限制直接排除核心修复。
- **待验环境声明**：同一字段声称 shell 在 `/testbed`、`testbed` conda 已激活，Python/pip/测试工具已对准它。这里均未验证；`environment_brief.md:3–13` 明确静态包不能证明这些运行条件。
- **旧解释的限制**：原提示将“禁止改测试”解释为所有测试改动都会恢复、永不计分；`environment_brief.md:18–24` 已说明这不能代表当前机制。当前取消按测试文件名统一排除，仍有官方文件恢复等具体限制。若禁改指令适用，开发者可执行现有测试与临时复现而不改测试文件；若不适用，可补回归测试，但不能据此推断其保留或评分规则。实际适用指令和恢复文件由协调者另核实，本审查不静默取消禁令。
- `public_bundle.json` 会写入实际容器公开路径；未出现在静态 `user_prompt.txt` 的字段不等于解题者不可见。实际消息位置和工具行为仍未知（`environment_brief.md:23–24`）。

## 2. 合理实现范围

可接受实现不应被限定为某一个 helper 或某条内部调用链。例如：在选定阶段的恢复/校验流程中按需拉取并检出，或在执行已确定的 repro 子图之前集中恢复缺失数据源，都有实现同一公开行为的空间。后一种方案需要继续遵守目标选择、dry、frozen 和本地修改等既有语义；无条件执行全仓 `pull` 不符合“本次 repro 必需”的范围。

也可以复用现有 fetch/checkout 能力，或在适当层组合对象下载与检出。公开代码提供两层不同接口：`base/dvc/data_cloud.py:164–190` 的 `pull` 下载对象到缓存；`base/dvc/repo/pull.py:35–55` 则组合 fetch 与工作区 checkout。审查不要求选定其中一层，也不提供修复代码。

确有约定的是 CLI 名称 `--pull`、默认关闭、`Repo.reproduce(..., pull=True)` 能接收这个选项、工作区恢复结果和原有阶段执行语义（`base/dvc/commands/repro.py:13,27–49,129–145`；`base/tests/func/test_run_cache.py:178–185`）。内部函数签名和精确调用次数不属于题面新约定。公开旧测试有较窄的 mock 断言：例如 `test_restore_pull` 要求 `restore(stage, pull=True, dry=False)`、checkout 调用两次，而普通恢复测试要求不显式传 `pull=False`（`base/tests/func/test_run_cache.py:24–41,169–185`）。这是真实的现有测试约束，但不能把其内部形状等同于唯一合法设计；实现时需兼顾既有测试，协调者也应区分行为回归和等价重构导致的 mock 差异。

`exp run` 复用 repro 参数和 `_common_kwargs`（`base/dvc/commands/experiments/run.py:6–7,14–42,81–84`），因此共享层变更应留意这个调用者。它的队列、远程机器和完整实验执行流程不是本 issue 明示的新增需求。

## 3. 初态线索与疑义

**静态定位链条充分。** CLI 在 `base/dvc/commands/repro.py:40` 将 pull 传入；`base/dvc/repo/reproduce.py:174–223` 按已选依赖顺序调用阶段，并包装异常为 `ReproductionError`。阶段 `reproduce` 先检查变化，再进入 `run`（`base/dvc/stage/__init__.py:422–442`）。有命令阶段进入 `run_stage`，后者尝试运行缓存恢复（`base/dvc/stage/run.py:136–151`），该恢复在 `pull and not dry` 时下载对象（`base/dvc/stage/cache.py:201–203`）。无命令数据源则走只检查输出存在的分支，缺失便抛出 `MissingDataSource`（`base/dvc/stage/__init__.py:576–584`；`base/dvc/stage/utils.py:140–143`）。这与 issue 所述现象一致；属于静态推断，不是已运行复现。

`is_data_source` 的代码定义是 `cmd is None`，注释包含 `dvc add` 和 `dvc import`（`base/dvc/stage/__init__.py:241–278`）；题面举的是“只有输出、没有命令”的狭义数据源。因此以下边界有多种合理解释，核心修复可先以已配置远端、普通 `.dvc` 数据源和完整缺失输出为基础：

| 疑义 | 公开材料能够说明什么 | 是否阻碍核心开发 |
| --- | --- | --- |
| 目录仍存在，但部分子文件缺失，同时可能有本地新增或修改 | `check_missing_outputs` 只检查根路径存在；对象层另有目录 hash/树（`base/dvc/stage/utils.py:140–143`；`base/dvc/output.py:1034–1129`）。不能把所有 hash 变化都当作用户要还原的删除。 | 不阻碍完整缺失源文件复现；若验收要求具体的合并/恢复策略，需要明确该策略。 |
| 导入、部分导入和 frozen 的来源选择 | `run` 将 import 单独交给 `_sync_import`；`base/dvc/stage/imports.py:41–64` 可能直接从依赖来源下载；`get_used_objs` 又有 import 排除。 | 正常查调用者能定位差异，不是必须补充仓库材料；题面没有穷举新增恢复承诺。 |
| 无远端、远端没有对象、缺 hash 或未缓存输出 | 对象层和远端配置有既有错误/排除规则（`base/dvc/data_cloud.py:55–110`；`base/dvc/output.py:1074–1101`）。 | 不阻碍使用本地远端的核心复现；不应把这些情况默认为成功或规定题面未要求的错误全文。 |
| `--single-item`、`--downstream`、`--force`、`--no-run-cache` 与 pull 的组合 | 现有选图、跳过和强制机制可直接查到；`base/dvc/stage/run.py:139–146` 中 force 会跳过运行缓存尝试。 | 不需要先向用户询问才能开发，但不能只修默认路径就声称全部组合已覆盖。单项选图是否也主动恢复被跳过上游属于需要谨慎解释的边界。 |
| `--no-commit` 与 pull 同用时缓存写入的含义 | CLI 说不把文件放入 cache；旧测试只验证未加 pull 的 no-commit（`base/dvc/commands/repro.py:166–179`；`base/tests/func/test_repro.py:831–844`）。pull 本身通常要写 cache。 | 组合语义未由本题澄清；不阻碍普通 `--pull` 核心行为。 |

没有给出用户原始仓库、原始缺失文件或一键复现脚本，但已有 `dvc add`、pipeline、`local_remote` 夹具足以生成小样例。这属于常规开发复现工作，不是阻断性缺项。README 的完整安装、命令参考与 CONTRIBUTING 均指向包外网站（`base/README.rst:37,109–110,198–204`；`base/CONTRIBUTING.md:1`），这些外链内容未查；核心行为无需它们即可定位。没有题面外链附件需要补入，也没有发现必须依赖公开祖先历史的调查步骤。

真正可能阻碍验证的是实际 actor 环境缺依赖或无可写缓存/临时目录。它们是运行条件待验，不是已证实缺失，也不是题目不可解的证据。

## 4. 开发需求表与建议命令

下列所有命令均为**建议，未执行**，供实际 actor 在真实 `/testbed` 检查；不应直接把静态 `base/` 导出当成已安装运行环境。无需 GPU、云账号、外部数据集或公网服务来验证核心问题。

| 操作/资产/服务 | 公开依据 | 环境说明支持层次 | 缺口与最小检查 |
| --- | --- | --- | --- |
| 正确源码及可编辑工作区 | `user_prompt.txt:1`、`public_bundle.json:1` 指定 commit 和 `/testbed`；`base_identity.json:3–11` 声明导出 tree、608 条目、无导出 Git 元数据 | `environment_brief.md:5–9` 提供静态来源及拟用 actor/profile | 尚未验证真实工作目录和 checkout。建议未执行：`pwd`、`id`；在真实 Git checkout 运行 `git rev-parse HEAD`。静态导出没有 `.git` 不能据此判真实环境无 Git。 |
| Python 与 DVC 核心依赖 | `base/pyproject.toml:22–67`，含 `dvc-data>=0.47.1,<0.48`、`scmrepo>=1.0.0,<2`；CI 使用 Python 3.8–3.11（`base/.github/workflows/tests.yaml:25–26`） | conda 预激活仅为原提示声明；actor 导入未验（环境说明第 12 行） | 需证明实际解释器能导入本 checkout 及外部包。下方导入命令预期打印解释器/源码路径并退出 0；导入失败先登记环境问题。 |
| pytest 收集及插件 | `base/pyproject.toml:90–109,122–123,139–140`；`base/tests/conftest.py:8–12,176–208` | 仅声明测试工具可用，没有收集证据 | 即使仅测本地远端，`tests/remotes/__init__.py:1–7` 在收集时导入 `dvc_ssh.tests`，session fixture 导入 `pygit2`；自动插件还导入 `pytest_virtualenv`（`base/dvc/testing/plugin.py:1`、`base/dvc/testing/benchmarks/fixtures.py:6–10`）。需 `pytest`、mock、cov、xdist 等配置依赖；不等于必须启动 SSH/Docker。建议先 collect-only。 |
| 本地 cache、临时仓库和本地目录远端 | `base/dvc/testing/fixtures.py:36–85,89–94,125–131,176–178`；`base/dvc/testing/tmp_dir.py:58–70,89–103` | 声明工作区/home 可写、有限 tmp/home 额度，实际配额和权限未验（环境说明第 9–12 行） | 需能建立、读写和重命名少量文件、创建锁/缓存。下面使用新建临时目录并指定 copy cache，无需真实数据或网络。预期 setup/push 成功，base 最后 repro 因缺源失败。 |
| 执行简单阶段命令 | `base/dvc/stage/run.py:46–75,78–105,119–151`，测试脚本由 `base/tests/scripts.py:3–12,38–41` 生成 | 拟用 CPU 环境，不证明子进程/shell 已可用 | 需可调用 shell、Python，建议 CLI 复现还用 `cp`、`mv`、`cmp`。小文件规模不要求大型资产或长时计算，资源成功仍待 actor 证据。 |
| 窄范围公开回归 | `base/tests/func/test_run_cache.py:161–185`；`base/tests/func/test_repro.py:287–305,656–685`；`base/tests/unit/command/test_repro.py:24–38` | 允许执行测试，但没有任何已执行结果 | 下方测试应作为既有行为基线；这些旧测试通过不证明新 bug 已修复，仍需本地复现从失败变成功。 |
| 如需安装/构建 | 构建后端与版本生成：`base/pyproject.toml:1–3,132–133`；上游 CI 用 `pip install -e ".[dev]"`（`base/.github/workflows/tests.yaml:38–41`） | 公网下载不被假定可用；系统/解释器包写权限待验（环境说明第 9–10 行） | 优先使用预置环境。只有依赖与构建后端已备好、actor 有权限时，才考虑下方离线式 editable 安装命令。它不会补齐缺依赖；缺包需预置安装资产。静态导出无 Git 不能保证 setuptools-scm 的构建版本推导，`dvc/version.py:1–7` 的 UNKNOWN 导入回退也不是构建已通过证据。 |

### 建议，未执行：最小导入及测试收集

```bash
cd /testbed
python -c 'import sys, dvc, dvc_data, dvc_objects; from dvc.repo import Repo; print(sys.executable); print(dvc.__file__); print(dvc.__version__)'
python -m pytest --collect-only -q tests/func/test_run_cache.py::test_restore_pull
```

预期：核心导入成功且 DVC 路径指向实际解题 checkout；收集出指定测试，不因缺插件、`dvc_ssh` 或包版本冲突而提前报错。这只验证导入和收集，尚未验证 fixture 执行。

### 建议，未执行：纯本地 CLI 复现

```bash
(
  set -eu
  export DVC_TEST=true
  dvc9395_tmp="$(mktemp -d)"
  mkdir "$dvc9395_tmp/work" "$dvc9395_tmp/remote"
  cd "$dvc9395_tmp/work"
  dvc init --no-scm
  dvc config cache.type copy
  dvc config cache.dir "$dvc9395_tmp/cache"
  printf 'source data\n' > source.txt
  dvc add source.txt
  dvc stage add -n consume -d source.txt -o result.txt cp source.txt result.txt
  dvc repro consume
  dvc remote add -d local "$dvc9395_tmp/remote"
  dvc push
  mv source.txt "$dvc9395_tmp/source.saved"
  mv result.txt "$dvc9395_tmp/result.saved"
  mv "$dvc9395_tmp/cache" "$dvc9395_tmp/cache.saved"
  dvc repro --pull consume
  cmp source.txt result.txt
)
```

此命令要求 `dvc` CLI 已绑定实际 checkout。它只在新建临时目录操作，通过移动数据/cache 构造“本地缺失、远端存在”，保留原始内容。选用 `--no-scm` 的依据为 `base/dvc/repo/init.py:15–20,40–50,68–72`；本地远端由既有夹具证明可构造，不需要云凭证。

静态预计：base 在最后的 `dvc repro --pull consume` 处理 `source.txt.dvc` 时失败，原因链为缺失 data source，再包装为 `ReproductionError`，CLI 返回非零；源文件应不会因现有 run-cache pull 而恢复。满足核心需求的实现应恢复 `source.txt`、完成所选阶段复现，使 `source.txt` 与 `result.txt` 内容一致。命令中的 `set -e` 会让 base 的预期失败终止子 shell，因而 `cmp` 只在 repro 成功后执行。

这是完整缺失普通源文件的核心探针，不是所有边界的验收集。后续可分别生成目录源、多个源、无关断开的源；分别检查仅工作区缺失、本地缓存也缺失、远端缺对象、已有源文件被修改、dry、frozen 和未传 pull。每个场景的操作均应限定在自己的临时仓库，不必改公开测试文件。已有运行缓存缺输出但源仍在的场景由下一个公开测试覆盖。

### 建议，未执行：公开回归与可选构建

```bash
cd /testbed
python -m pytest -q tests/func/test_run_cache.py::test_restore_pull
python -m pytest -q tests/func/test_repro.py -k 'non_existing_output or repro_data_source or repro_dry or repro_frozen or repro_no_commit'
python -m pytest -q tests/unit/command/test_repro.py
```

预期上述既有测试在合适环境的 base 与修复后均通过；参数化测试可能产生多个实例。失败需区分新行为回归、旧 mock 调用形状变化和环境导入/fixture 问题。这里只建议窄范围，不要求云远端、benchmark、所有 experiment 或全仓 suite 均可运行。

仅在实际 checkout 需要 editable 安装，且后端/依赖已预置、有写权限时，**建议，未执行**：

```bash
cd /testbed
python -m pip install --no-deps --no-build-isolation -e .
```

预期建立当前 checkout 的可编辑安装；不把该命令当作联网补依赖方案。核心验证不需要打包发布制品或安装全部云存储 extras。

## 5. 阅读范围与限制

实际打开的公开输入：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`，以及指定 `public_reader.md` 角色卡。先读取前三项，之后查源码。执行过本题目录内的文件名枚举和针对性 `rg` 检索；匹配行不等于完整读取该文件。

实际打开的 base 文件（括号表示主要阅读范围，未列范围的为整文件）：

- 文档/构建：`README.rst`、`CONTRIBUTING.md`、`pyproject.toml`、`.github/workflows/tests.yaml`、`dvc/__init__.py`、`dvc/version.py`。
- 核心路径：`dvc/commands/repro.py`、`dvc/repo/reproduce.py`、`dvc/stage/run.py`；`dvc/stage/__init__.py`（210–448、450–730）；`dvc/stage/cache.py`（1–220）；`dvc/stage/utils.py`（120–155）；`dvc/stage/exceptions.py`（65–93）。
- 恢复和调用者：`dvc/data_cloud.py`、`dvc/output.py`（552–625、875–980、1030–1160）、`dvc/repo/pull.py`、`dvc/repo/fetch.py`（1–175）、`dvc/stage/imports.py`（1–64）、`dvc/cachemgr.py`、`dvc/repo/init.py`、`dvc/commands/experiments/run.py`（1–135）、`dvc/commands/stage.py`（1–180）。
- 公开测试：`tests/unit/command/test_repro.py`、`tests/unit/repo/test_reproduce.py`；`tests/func/test_run_cache.py`（1–185）；`tests/func/test_repro.py`（1–90、270–322、490–720、790–880、1070–1140）；`tests/unit/stage/test_cache.py`（1–65、199–215）；`tests/unit/stage/test_run.py`（1–22）。
- 测试环境与资产生成：`tests/conftest.py`、`tests/remotes/__init__.py`、`tests/remotes/git_server.py`、`tests/scripts.py`、`tests/dir_helpers.py`；`dvc/testing/fixtures.py`（1–218）、`dvc/testing/tmp_dir.py`（1–165）、`dvc/testing/plugin.py`、`dvc/testing/benchmarks/fixtures.py`（1–70）、`dvc/testing/benchmarks/plugin.py`（1–90）。

检索时尝试的 `tests/scripts/__init__.py` 和 `tests/func/test_freeze.py` 并不存在；随后定位到了实际 `tests/scripts.py` 和 `tests/func/test_repro.py` 中的 frozen 测试。这是查找路径更正，不是缺失运行资产。

未查项目：私有评分材料、gold、未来修复或历史、其他题、角色卡父目录、项目调查文档、真实容器与 actor shell、外部依赖的实际安装源码、联网文档、全部测试和完整实验/云端流程。对 `dvc_data` 下载/checkout 的深层实现未作运行或包外源码验证。

`user_prompt.txt` 仅为当前函数的静态渲染；本包不是实际模型消息记录，也不是完整可运行容器。`base_identity.json` 中的完整性字段是公开包声明，没有在本审查重新核验导出。未声称 conda 激活、依赖、权限、资源、资产或任何测试已经通过；没有执行上列任何建议命令。未接触本题私有材料；阅读范围约定不构成操作系统权限隔离或预训练无污染证明。
