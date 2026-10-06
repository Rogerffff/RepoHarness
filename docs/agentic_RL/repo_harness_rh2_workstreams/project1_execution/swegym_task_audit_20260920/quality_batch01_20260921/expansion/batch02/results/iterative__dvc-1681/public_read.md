# iterative__dvc-1681 公开阅读审查

本报告只依据本题 `public/iterative__dvc-1681/` 和指定 `roles/public_reader.md`。下列文件引用以本题公开目录为根；`base/` 指导出的 base 源码。基准提交是 `9175c45b1472070e02521380e4db8315d7c910c4`（`public_bundle.json:1`、`base_identity.json:3`）。没有执行项目代码、测试、安装、容器或网络操作，也没有修改源码或测试。所有运行命令均为**建议，未执行**。

公开材料足以把问题定位到 stage 元数据校验的兼容性，而不是首先怀疑大文件内容哈希。最强静态线索是：创建及加载 stage 时将工作目录变为绝对路径，`dumpd()` 原样返回它；写 YAML 时才改为相对路径，而校验计算仅排除字面值 `"."`。这与现存的默认工作目录兼容性注释不一致。该解释尚未经运行证实，不能称为已复现或已修复。

## 1. 需求与约定

| 行为 | 公开依据 | 解释层级与边界 |
|---|---|---|
| 旧版 `dvc add` 生成的 `.dvc` 文件及其数据未变时，新版 `dvc status <file>.dvc` 不应仅因升级而报告 `changed checksum`。干净状态应恢复既有提示。 | `user_prompt.txt:9-20,23-49`；提示常量在 `base/dvc/command/status.py:11,52-58`。 | **明示目标**。题面给出了旧顶层 `md5` 与输出文件 `md5`，无需另外发明成功文案。 |
| 区分 stage 校验值和数据文件校验值。顶层 `md5` 对 stage 定义计算；`outs[].md5` 对数据内容计算。 | `base/dvc/stage.py:182-183,558-577,748-769`；`base/dvc/output/base.py:114-150`。 | **由公开实现可合理推知**。题面中 `md5sum` 一致支持数据未改，但不能单独证明顶层 stage 校验应一致。输出文件改变通常报 `changed outs` / `modified`，题面字符串直接指向 `Stage.changed_md5()`。 |
| 省略 `wdir` 与默认 `wdir: .` 在 stage 校验上应等价，旧的无 `wdir` 文件仍可使用。 | `base/dvc/stage.py:509-512,567-572` 明确写有 backward compatibility 注释；`base/tests/test_stage.py:98-116`。 | **公开代码和旧测试明确约定**，不是额外猜测。默认值的等价应基于 `.dvc` 文件位置，不能直接拿运行时绝对路径与 `"."` 比较。 |
| 保留工作目录语义：运行时实际工作目录、相对于 stage 文件位置的持久化目录，以及输出相对于工作目录的路径。 | `base/dvc/stage.py:439-451,550-554,670-675`；`base/dvc/output/local.py:29-34,57-68`；`base/tests/test_run.py:617-665`。 | **可合理推知的兼容要求**。旧测试明确要求默认 `wdir` 写为 `"."`、子目录中的 stage 可写 `".."`，且 `stage.wdir` 保持实际绝对目录。真正不同的非默认工作目录不能一律从校验中删除。 |
| 真实的命令、依赖、输出或缓存语义变化仍应被检测；不能用隐藏提示、总是返回干净状态、忽略所有顶层校验等方式“修复”。 | `base/dvc/stage.py:239-242,558-577,748-764`；`base/dvc/output/base.py:137-150`。 | **由现有接口可合理推知**。输出缺失、缓存缺失和数据修改仍有独立状态；本题没有授权取消这些能力。 |
| 顶层 `md5` 不参与自身计算，但嵌套依赖/输出的校验值参与；`locked`、`metric` 不参与，`cache` 参与。 | `base/dvc/stage.py:563-577`；`base/dvc/utils/__init__.py:76-104`；固定哈希旧测试 `base/tests/unit/stage.py:6-16`、`base/tests/test_utils.py:40-60`。 | **公开代码/测试的约定**。修复无需改哈希算法或 JSON 排序规则，也不能把所有名为 `md5` 的键一起过滤。 |
| 保留 CLI 状态和返回码约定：正常模式成功查询即返回 0；quiet 模式干净为 0、有变化为 1。 | `base/dvc/command/status.py:52-63`；`base/tests/test_status.py:9-20`。 | **旧接口和公开测试明确约定**。判断复现结果应检查文本/状态对象，不能仅以正常模式退出码 0 作为“无变化”的证明。 |
| 保存与重新加载不应擅自改写现存顶层校验值；`.dvc` / `Dvcfile` 命名和 YAML 字段保持兼容。 | `base/tests/test_stage.py:72-95`；`base/dvc/stage.py:113-129,479-485,494-536`。 | **公开约定**。不应要求用户重新 `add` 所有数据或让 `status` 默默重写 stage 文件来规避升级问题。 |
| 同一相对布局在不同绝对检出目录下应具有稳定校验；新建、保存、加载、状态查询应使用一致定义。 | `base/README.rst:30-39,53-55`；`base/dvc/stage.py:509-512,550-577`。 | **合理推导的补充检查**。仓库目标包括共享与复现，持久化路径采用相对目录；题面没有单独提出跨机器迁移或全部平台路径边界，因此这些应作为修复一致性检查，不能把未给出的每个边界都当明示验收条件。 |

题面没有指定新的公共函数名、辅助方法名、修改文件数量或唯一修复形式。`_compute_md5()` 是现有内部入口，旧单元测试使用它，不等于要求新增特定内部结构。

### 分开记录原提示的三种性质

- **Issue 需求**：上表中的升级后错误状态报告；Arch Linux、pip、Python 3.6.8 是报告者的复现背景（`user_prompt.txt:4-7`），不是实际 actor 环境已经具备这些条件的证明。
- **Harness 操作指令**：`public_bundle.json:1` 的 `public_hints` 要求调查根因、仅编辑非测试源码、不修改测试、窄范围运行测试、完成后短总结；公开工具字段为 `bash` / `edit`、工作区为 `/testbed`。这些应与 issue 行为需求分开。当前公开读者角色额外禁止执行代码，本次遵守该限制。
- **待验环境声明及旧机制说明**：原提示称 conda `testbed` 已激活，尚未通过 actor 身份验证。其“测试改动全部恢复、永不计分”不能当作当前已核实机制；`environment_brief.md:20-26` 说明已取消按测试文件名统一排除，但仍有官方文件恢复等具体限制。若原禁止改测试指令适用，本题可通过改源码并运行原有测试/临时诊断脚本完成开发，暂未发现必须修改测试才能成立的合理修复；若不适用，可补充旧哈希回归测试。是否适用须由实际共享输入核对，不能由本报告取消，也不能据旧说明判定本题无效。

`public_bundle.json` 会写到实际求解容器的公开路径；字段未呈现在 `user_prompt.txt` 不等于不可见。当前没有实际模型消息捕获，不能据此确认提示所在消息层级（`environment_brief.md:3-6,25-26`）。

## 2. 合理实现范围

可以提出至少两种不依赖隐藏实现的合理路线：

1. **统一 stage 序列化的路径表示**：使参与校验的 stage 字典使用相对于 stage 文件目录的工作目录；继续在实际执行和查找数据时使用真实目录。默认相对目录为 `"."` 时沿用既有忽略规则。若调整 `dumpd()`，需检查 `is_cached` 的旧/新 stage 比较（`base/dvc/stage.py:351-380`），以及 `dump(fname=...)` 按目标文件位置计算路径的行为（`:538-554`），不能只照顾原路径保存。
2. **限定在校验输入上做等价规范化**：保留内部字典/对象的现有表示，在计算 stage 哈希前将工作目录规范化为持久化语义，或抽出共用的规范化辅助过程，让保存与比较用相同规则。只要旧文件不误报、非默认目录仍有意义、相关调用者和旧测试保持兼容，不应因为没有采用上一种代码结构而否定。

这两种路线都是公开证据支持的实现范围，并非声称已经证明任何具体补丁正确。直接删除所有 `wdir`、只改 CLI 文案、把校验条件改成恒假、按题面文件名/哈希特判，都不能保留上述行为。

校验逻辑还被 `changed()`、`check_can_commit()`、`_already_cached()` 使用（`base/dvc/stage.py:239-242,598-617,771-779`），前者又影响 `reproduce()`（`:272-276`）。修复不能只让 `status` 输出看似正常。新写入 `.dvc` 的 `wdir: .`、`..` 等格式已有旧测试约束；不要求重设计整个 stage 格式。

一个仍可有多种解释的扩展问题是：是否还要兼容“已经被有缺陷版本写入绝对路径相关校验值”的 stage。题面明确的目标是升级后读取旧版文件；没有提供这类中间版本写入数据的格式或迁移政策。本报告不把接受所有历史错误哈希、自动迁移、或维护双算法判断列成必需需求。若拟扩大修复范围，应先明确其不会掩盖真正的元数据修改。

## 3. 初态入口、已有测试与真正未知

**静态调用链可定位。** `CmdDataStatus.do_run()` 调用 `Repo.status()`；本地状态经 `_local_status()` 遍历 stage；`Stage.status()` 根据 `changed_md5()` 加入题面原文（`base/dvc/command/status.py:39-58`、`base/dvc/repo/status.py:6-25,67-90`、`base/dvc/stage.py:748-769`）。无需公网或私有测试才能找到调查入口。

**路径表示不一致的证据链。** `Stage.create()` 在返回前将 `wdir` 绝对化（`base/dvc/stage.py:439-451`）；`Stage.load()` 对缺省 `wdir` 取 `"."` 后也转为绝对路径（`:506-520`）；`dumpd()` 放入 `self.wdir`（`:524-535`）；`dump()` 只在写文件时替换为相对值（`:548-554`）；`_compute_md5()` 使用 `dumpd()`，却只删除 `wdir == "."`（`:558-577`）。因此旧的“省略默认目录”的校验定义可能被运行时绝对路径污染。这是静态推断；本次没有计算或比较实际哈希输出。

**旧测试的有效覆盖与盲区。**

- `base/tests/unit/stage.py:6-16` 用 mock 的 `dumpd()` 检查固定哈希，输入没有 `wdir`，能约束嵌套 MD5 等旧规则，不能暴露真实加载后的绝对 `wdir` 问题。
- `base/tests/test_stage.py:98-116` 在当前版本创建 stage，再删除 YAML 中的 `wdir` 并加载。新建和加载都可能使用同一个错误的绝对路径哈希，所以该测试即使通过也不能证明旧版兼容。
- `base/tests/test_stage.py:72-95` 覆盖保存时保留已有顶层哈希；`base/tests/test_run.py:617-665` 覆盖工作目录与 stage 文件路径；`base/tests/test_status.py:9-20` 覆盖 quiet 返回码。
- 本次查阅的旧测试没有直接以题面旧顶层 `fc2ea87b490d2f382601c489822a1e96` 作为加载后的期望值。用题面 YAML 做专门校验探针，比只重新 `add` 再 `status` 更有区分力。

**缺项及影响。**

| 未知/缺项 | 实际影响 |
|---|---|
| 未提供 `plwiki-latest-pages-articles.xml`、对应缓存及完整原仓库。 | 无法原样重跑完整原 CLI 场景并验证文件内容；但只计算 stage 元数据哈希不需要这些大文件。也可用小型本地文件构造旧格式 stage 验证端到端状态。不是调查根因的硬阻塞。 |
| 没有 0.28 源码或运行环境、公开祖先历史。 | 不能声称实际对比过 0.28，也不能断定所有历史版本的哈希规则。题面实例、当前源码兼容注释与旧测试足以开始修复；目前不需请求祖先历史。若扩大到中间版本迁移，可能需要仅含公开祖先且不含未来修复的材料。 |
| 题面正文写 `0.3.0`，标题和安装指令是 `0.30`，其中一次版本输出为 `0.29.0+220b4b.mod`。 | 复现历史存在文字/版本标识不一致；指定 base commit 和末段 `0.30.0+9175c4` 明确了调查对象（`user_prompt.txt:1,3,9,32-46`）。不妨碍以给定 base 为准，无需先澄清才能查代码。 |
| 没有全文贡献指南或外部教程。 | README 中的链接未访问；已有安装元数据、CI 脚本、测试入口足以形成最小开发建议。没有发现必须补入某个外链内容才能解释本题需求。 |
| 实际解释器、依赖解析结果、可写权限、资源限制、测试运行状态未知。 | 属于 actor 验证事项，不能据静态包宣称可运行或不可运行；也不能把未验证记成题面缺陷。 |

“需要继续检查调用者与序列化”是正常开发工作，不是用户遗漏需求。`base_identity.json:5-12` 声明 220 个跟踪项均导出、没有 gitlinks/LFS 未物化指针，且未导出 Git 元数据；本次没有另行重新验证这些声明，也没有访问共享镜像克隆。

## 4. 开发条件与建议验证

下表的命令均为**建议，未执行**，供实际 actor 在 `/testbed` 内使用；本次没有在桌面导出目录运行它们。先确认解释器和依赖，再进行小范围 CPU 验证。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口、建议命令与预期 |
|---|---|---|---|
| Python 与基础依赖导入 | 报告者使用 3.6.8（`user_prompt.txt:7`）；旧 CI 包括 Python 2.7、3.4–3.7（`base/.travis.yml:20-37`）；核心依赖在 `base/setup.py:5-25`。 | 提示声称 conda `testbed` 已激活；环境说明要求 actor 另验（`:8-13`）。 | **建议，未执行**：`python --version`；`python -m pip --version`；`DVC_TEST=true python -c 'import sys, sqlite3, yaml, schema, mock; import dvc; from dvc.stage import Stage; from dvc.repo import Repo; print(sys.executable); print(dvc.__file__)'`。预期导入成功且路径指向 `/testbed`；导入错误是环境证据，不是本题 bug 的复现。不能假定今天最新版依赖与这份旧源码兼容。 |
| 源码可写、Git 可调用、版本辅助文件生成 | `base/dvc/__init__.py:21-45,54-63` 在源码 Git 检出导入时可能写 `dvc/version.py`；测试初始化 Git 并提交（`base/tests/basic_env.py:80-100`）。 | 说明 actor 为 `agent/54321`，工作区/home 可写，解释器与系统包权限待查（`environment_brief.md:8-12`）。 | **建议，未执行**：`id`；`git --version`；`test -w /testbed/dvc`。正式测试还需 Git 身份；可用命令级 `GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME`、`GIT_COMMITTER_EMAIL` 提供测试身份，无需改全局配置。桌面 `base/` 无 `.git` 与实际检出不等价。 |
| 旧 stage 的元数据校验复现 | 题面 YAML；`Stage.load()` / `_compute_md5()`；不访问数据内容的哈希路径在 `base/dvc/stage.py:494-577`。 | 只提供静态源码和题面，未提供原 XML/缓存。 | 下方 A 探针使用公开 YAML 和临时 DVC 仓库，只验证顶层校验。预期原基准断言失败、修复后通过；尚未执行，实际输出未知。原 XML 不构成该探针的必要资产。 |
| 本地缓存、状态数据库、临时目录和 shell | `base/tests/basic_env.py:58-74,112-116`；`base/dvc/state.py:6,210-225`；`base/dvc/remote/local.py:35-40,62-63`；`base/dvc/stage.py:670-675`。 | 默认 2 CPU / 4 GiB / PID512、tmp 1 GiB / home 256 MiB，仅为计划值（`environment_brief.md:11-12`）。 | 需要可写临时目录、SQLite、普通本地文件操作；运行相关 `run` 测试还需可用 shell 和 `python`。**建议，未执行**：下方 B 的单模块/单类测试。相关 fixture 使用小文件；无需下载 Wikipedia dump、GPU、外部模型或云服务。不以静态规模推断资源已通过。 |
| 测试运行器、资源上限及窄范围回归 | `base/tests/requirements.txt:1-5`；`base/tests/__main__.py:15-25`；`base/tests/__init__.py:3-15`。 | 依赖是否预装、测试能否执行仍未验证。 | `unittest` 可运行这些 `TestCase`，需要第三方 `mock`；导入 `tests` 会设定 fd 上限 2048 并调整进程软上限，actor hard limit 太低可能先失败。**建议，未执行**：下方 B；原仓库入口 `DVC_TEST=true python -m tests tests.unit.stage` 也可参考，但默认 nose 命令带 `--processes=-1`，此题优先串行窄测。 |
| 网络、遥测和更新检查 | `base/dvc/updater.py:42-44` 与 `base/dvc/analytics.py:205-212` 支持 `DVC_TEST` 关闭相关行为；`base/tests/__main__.py:12-13` 同样设置它。 | 环境仅允许模型代理和已声明内部服务，不能假定公网（`environment_brief.md:10`）。 | 建议命令设置 `DVC_TEST=true`；本地任务无需远程数据服务。CLI 仍可能创建用户配置目录（`base/dvc/analytics.py:49-66`），home 可写须实验确认。没有发起任何网络访问。 |
| 缺依赖时的安装/构建 | `base/README.rst:87-105`；`base/setup.py:5-32,43-62`；旧 CI 安装命令在 `base/scripts/ci/install.sh:17-19`。 | 未提供实际安装清单、离线 wheelhouse 或解释器写权限；不可默认联网下载。 | 本问题修复不需要发布包或执行全套打包。若环境缺依赖，需准备兼容版本的离线包；**建议，未执行，仅当已提供相应包目录时**：`python -m pip install --no-index --find-links="$DVC1681_WHEELHOUSE" -e .`。测试依赖另按需要补齐 `mock`/运行器；不要求为本地问题安装全部云客户端和 PyInstaller。**建议，未执行，可选包装检查**：`python setup.py check`，只检查包装元数据，不代替行为验证。 |

### A. 直接使用题面 YAML 的最小校验探针（建议，未执行）

在实际 `/testbed` 工作目录中执行；创建的临时仓库无需原始 XML。此探针只验证 `Stage.load()` 后的校验兼容性，不把缺失数据的完整 `status` 当成应当干净。

```bash
DVC_TEST=true python - <<'PY'
import os
import tempfile
from dvc.repo import Repo
from dvc.stage import Stage

payload = """md5: fc2ea87b490d2f382601c489822a1e96
outs:
- cache: true
  md5: 068b1464866e460e58ce216cd82dcf9b
  metric: false
  path: plwiki-latest-pages-articles.xml
"""

with tempfile.TemporaryDirectory(prefix="dvc-1681-") as root:
    repo = Repo.init(root, no_scm=True)
    path = os.path.join(root, "plwiki-latest-pages-articles.xml.dvc")
    with open(path, "w") as stream:
        stream.write(payload)
    stage = Stage.load(repo, path)
    print("stored:", stage.md5)
    print("computed:", stage._compute_md5())
    assert not stage.changed_md5(), "unchanged legacy stage checksum differs"
PY
```

预计原基准因绝对 `wdir` 进入哈希而出现断言失败；修复后应与题面顶层校验值一致。若在导入/初始化阶段先失败，须把该环境故障与校验回归分开。该脚本使用 Python 3 的 `TemporaryDirectory`，与题面 Python 3.6 背景相符；不要求实现放弃仓库原有 Python 2 兼容。

### B. 相关旧测试与补充检查（建议，未执行）

以下每行可单独运行，优先执行所改动路径相关的行；建议的测试身份只作用于当前实际 actor shell：

```bash
export DVC_TEST=true
export GIT_AUTHOR_NAME='DVC test'
export GIT_AUTHOR_EMAIL='dvc-test@example.invalid'
export GIT_COMMITTER_NAME='DVC test'
export GIT_COMMITTER_EMAIL='dvc-test@example.invalid'
python -m unittest -v tests.unit.stage.TestStageChecksum
python -m unittest -v tests.test_stage
python -m unittest -v tests.test_status
python -m unittest -v tests.test_run.TestCmdRunWorkingDirectory
python -m unittest -v tests.test_run.TestRunDeterministic
python -m unittest -v tests.test_add.TestAdd
python -m unittest -v tests.test_utils.TestUtils.test_dict_md5
```

这些旧测试预期在合理修复后通过，部分很可能在原基准也通过；不能把它们全当成必然的原 bug 失败测试。最低补充检查是 A 中的公开旧哈希；还应在小型临时仓库检查默认目录显式/省略相同、嵌套 stage 的非默认目录、保存后重载、整体目录迁移，以及真实数据修改仍出现输出状态。若禁止修改测试适用，可通过临时诊断脚本完成这些检查。

完整 CLI 的补充复现可以用自建小文件：先得到有效本地数据及缓存，将 stage 改为旧格式、用公开旧规则设置顶层哈希，再运行状态命令；不要仅从有缺陷版本新建一份 stage 就期待复现升级问题。**建议，未执行**：对已准备好的这种临时 fixture 运行 `DVC_TEST=true dvc status fixture.dvc` 及 `DVC_TEST=true dvc status --quiet fixture.dvc`。原 bug 预计表现为前者出现 `changed checksum`、后者返回 1；修复后无其他变化时应显示既有干净提示且 quiet 返回 0。随后修改真实内容，应仍报告 `changed outs`。本报告未创建该 fixture，也未验证这些预期。

## 5. 实际阅读与暴露记录

本角色仅收到当前角色任务、指定路径及通用环境信息后开展阅读，没有读取此前题目结论。读取遵循“角色卡 → 三个公开说明 → 本题源码/测试”的顺序。

**完整打开的公开文件：**

- 指定 `roles/public_reader.md`（仅该文件，未查看其父目录内容）。
- 本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- `base/README.rst`、`base/setup.py`、`base/setup.cfg`、`base/requirements.txt`、`base/.travis.yml`、`base/scripts/ci/install.sh`、`base/scripts/ci/script.sh`。
- `base/dvc/stage.py`（分段读取，合计覆盖全文件）、`base/dvc/output/base.py`、`base/dvc/output/local.py`、`base/dvc/output/__init__.py`、`base/dvc/repo/status.py`、`base/dvc/command/status.py`、`base/dvc/repo/add.py`、`base/dvc/repo/run.py`、`base/dvc/repo/init.py`、`base/dvc/__init__.py`、`base/dvc/main.py`。
- `base/tests/requirements.txt`、`base/tests/__init__.py`、`base/tests/__main__.py`、`base/tests/basic_env.py`、`base/tests/unit/stage.py`、`base/tests/test_stage.py`、`base/tests/test_status.py`、`base/tests/test_utils.py`。

**分段打开的公开文件：**

| 文件 | 实际查看行段 |
|---|---|
| `base/dvc/utils/__init__.py` | 1–118；另请求 375–430，工具未返回该范围正文。 |
| `base/dvc/repo/__init__.py` | 1–155、260–315。 |
| `base/dvc/updater.py` | 1–100。 |
| `base/dvc/analytics.py` | 40–77、202–233。 |
| `base/dvc/remote/local.py` | 1–152、437–463。 |
| `base/dvc/state.py` | 1–14、205–236。 |
| `base/tests/test_run.py` | 1–105、210–265、600–715。 |
| `base/tests/test_add.py` | 1–190。 |

另用 `ls -la` 列出本题公开目录，用 `rg --files` 列出本题 base 的非隐藏文件路径；用 `rg -n` 在本题 `dvc/`、`tests/` 和指定 CI/配置文件中搜索 checksum、wdir、dumpd 调用者、状态文案、测试入口、SQLite、`DVC_TEST` 等关键词。检索还呈现了少量未全文打开的 `tests/test_data_cloud.py`、`tests/unit/command/run.py`、`tests/utils/__init__.py`、`tests/test_logger.py`，以及 `tests/unit/remote/` 下的若干文件、`tests/unit/daemon.py`、`tests/unit/progress.py`、`tests/unit/prompt.py`、`tests/unit/utils/fs.py` 的相关行，另有 `dvc/cache.py`、`dvc/remote/base.py` 的匹配行；不据此声称已审查这些完整模块。`base/.coveragerc`、`base/pyproject.toml`、`base/dvc/cli.py` 仅纳入相关关键词检索，未完整阅读。文件枚举不是内容审查。

**未查与未执行：**没有读其它题、任何私有评分材料、gold、history、manifest、批次结论或其它角色产物；没有使用继承 cwd 的新 worktree 作为材料；没有 Git 历史、网络搜索、外部附件、容器检查、项目导入、测试、安装或资源试跑。唯一输出是本报告。没有已知误读私有材料事件。

`user_prompt.txt` 是静态渲染，`base/` 是源码导出而非完整运行容器；镜像中的依赖、构建产物、数据资产和公开祖先历史可能与该导出不同（`environment_brief.md:3-6`）。本报告不声称实际模型消息、工具调用边界、conda 激活、资源或开发条件已经验证。阅读边界是协作约定，不能证明文件权限隔离或预训练无污染。
