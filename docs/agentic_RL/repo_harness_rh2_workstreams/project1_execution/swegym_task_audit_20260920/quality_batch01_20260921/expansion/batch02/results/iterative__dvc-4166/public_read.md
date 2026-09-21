# iterative__dvc-4166：独立公开阅读记录

本记录只依据角色卡和本题公开包，未运行项目代码、测试、安装、容器或网络请求。所有源码路径均相对本题 `PUBLIC_DIR`，不是继承的工作目录。静态证据足以定位调查入口；实际复现结果、依赖版本和运行条件仍未核验。

- `PUBLIC_DIR`：`runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-4166/`
- 基线：`520e01f11305aba1994df354adef86e6d90180de`，见 `public_bundle.json:1`、`base_identity.json:3`。
- 角色卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md`。

## 1. 需求与依据

### 三种输入应分开理解

1. **Issue 需求**：全量排除后，通过否定规则重新包含 `scripts`。题面列出六组失败规则、一组工作规则，没有提供具体目录树、DVC 命令、实际输出、OS 或依赖版本（`user_prompt.txt:3-46`）。
2. **Harness 操作指令**：公开 bundle 指定 bash/edit、`/testbed`，要求调查原因、只改非测试源码、可运行窄范围测试、完成后简述并停止（`public_bundle.json:1`）。这是解题流程指令，不是 `.dvcignore` 语义。
3. **环境事实声明**：同一 bundle 声称 conda `testbed` 已激活。`environment_brief.md:3-12,20-26` 明确它未经 actor 验证，当前材料也不是实际模型请求。不能据此确认解释器、依赖和工具可用。bundle 会写入真实解题容器的公开路径，不能因 hints 未出现在 `user_prompt.txt` 中就判断不可见。

| 需求或应保留行为 | 确定程度 | 公开依据与边界 |
|---|---|---|
| 修复“先全量排除、再否定包含 `scripts`”不能正常工作的情况 | 题面明示 | `user_prompt.txt:3,8-38`。行为目标是保留选中的内容，同时继续忽略未选中的内容。 |
| 保留 `/*` 加 `!/scripts` 的有效行为 | 题面明示的旧行为 | `user_prompt.txt:40-44`。这是很有价值的对照组；本次未证实它在实际镜像中确实成功。 |
| `!` 规则必须参与匹配，且同一文件中后面的匹配规则覆盖前面规则 | 公开测试明确 | `base/tests/unit/test_ignore.py:70-71,104-116`；实现见 `base/dvc/ignore.py:68-73`。不能简单实现为“任何否定规则永远优先”。 |
| 普通文件和目录排除、`*`/`**` 的层级差别、以 `/` 开头的根相对匹配应保留 | 公开测试明确 | `base/tests/unit/test_ignore.py:17-32,35-88`。例如 `/*.txt` 不匹配更深层的同名后缀文件。 |
| 同名普通文件与目录应按模式语义区分；目录规则不应靠额外文件系统探测才可工作 | 合理推知，具体机制未约定 | 题面刻意列出 `/scripts/`、`scripts/`；`DvcIgnorePatterns.__call__` 本来就收到分开的 dirs/files（`base/dvc/ignore.py:45-49`）。Git 分支树也经由同一层过滤（`base/dvc/repo/__init__.py:136-144`、`base/tests/func/test_ignore.py:112-124`）。 |
| 文件访问和遍历应一致地反映目录是否可见 | 接口和调用者可合理推知 | `CleanTree.exists/isdir/isfile/_parents_exist/walk` 都使用过滤层，见 `base/dvc/ignore.py:161-197,202-241`。仅改善某条 CLI 输出而保留树接口矛盾，不是充分的行为修复。 |
| 默认忽略 `.git`、`.hg`、`.dvc`；保持嵌套 DVC 仓库边界 | 公开代码及旧测试明确 | `base/dvc/ignore.py:85-126`；`base/tests/unit/test_ignore.py:91-101`；`base/tests/func/test_tree.py:226-243`。 |
| 保留 Unicode、空行、子目录调用、外部路径和分支读取现有约定 | 公开测试明确 | `base/tests/func/test_ignore.py:21-35,112-175`。外部 walk 与 exists 的边界细节依既有接口，不应笼统改成全局路径规则。 |
| 被忽略目录内的 `.dvcignore` 不应被无条件收集；收集输出目录中的 `.dvcignore` 原有错误仍适用 | 公开测试明确 | `base/tests/func/test_ignore.py:82-109`。因此“为寻找否定规则而遍历所有原本忽略目录”会影响已有行为。 |
| 六组失败写法是否都必须获得完全相同的递归包含结果 | 仍有多种合理解释 | 题面是试用报告，没有给出正式模式语义。尤其“包含目录本身”和“仅包含目录内容”不等价，见下表。 |

### 题面规则矩阵与实质歧义

以下都是两行规则；“候选解释”是调查方向，不是已经执行得到的结果。

| 第一行 / 第二行 | 题面观察 | 合理调查点 |
|---|---|---|
| `*` / `!scripts` | 失败，`user_prompt.txt:10-13` | 无根锚定的名称规则可能适用于多个层级。检查是否在根层保留 scripts，以及子文件是否再次被 `*` 排除。 |
| `*` / `!/scripts` | 失败，`:15-18` | 明确根相对的 scripts；不能凭 `*` 与 `/*` 外观相近而预设完全相同的匹配结果。 |
| `/*` / `!/scripts/` | 失败，`:20-23` | 目录型否定规则是否能命中目录本身。源码在目录输入上没有保留末尾分隔符或显式类型信息，是直接调查入口。 |
| `/*` / `!/scripts/*` | 失败，`:25-28` | 规则针对 scripts 的下级路径；若 scripts 自身仍被排除，遍历会提前剪枝。需明确是否要求自动重新开放父目录。 |
| `/*` / `!/scripts/**` | 失败，`:30-33` | 同样存在父目录可达性问题，同时应区分单层与递归通配。不能由题面推导出一种新的父目录重开规则。 |
| `/*` / `!scripts/` | 失败，`:35-38` | 目录型名称规则，另需检查非根位置的同名目录。 |
| `/*` / `!/scripts` | 工作，`:40-44` | 最小基线对照，修复应保持其既有作用。 |

题面没有说明 `scripts` 是文件、非空目录还是空目录，也没有列出预期保留的后代路径。最自然的调查假设是“根下 scripts 目录及其中脚本应可见，其他根路径仍被忽略”；这个假设足以构造复现，但不能把六种写法一律判为语义等价。特别是仅否定后代、没有否定父目录的组合，在当前剪枝结构下应独立说明，而不是通过无条件深入所有目录来满足。

## 2. 可定位的初态与合理修复范围

静态调用链很短：

1. `base/dvc/ignore.py:26-43` 读取 `.dvcignore`，调用外部 `GitWildMatchPattern.pattern_to_regex`，把相邻同极性的规则合并为正则组。
2. `:45-49` 对 files 和 dirs 调用完全相同的 `matches(root, basename)`。`:51-66` 只构造相对路径并在非 Unix 下标准化，没有传递目录类型。
3. `:68-73` 按顺序保留最后一次匹配的 include/exclude 结果。旧测试已约束这条顺序规则，不能为了否定修复改成无序集合匹配。
4. `:116-137` 收集忽略文件并在扫描时剪枝。`:175-197,202-241` 把相同机制用于目录/文件可见性、父目录检查和 walk。
5. `WorkingTree.walk` 返回可变 dirs 列表（`base/dvc/scm/tree.py:70-79`）；`GitTree._walk` 也先 yield dirs，再递归其剩余项（`base/dvc/scm/git/tree.py:113-129`）。目录早期被过滤会使后代没有再次匹配机会。

这支持一个**需复现确认的根因假设**：目录语义在交给 pathspec 生成的正则前丢失，带末尾 `/` 的否定规则不能正确匹配被遍历的目录；另外一些题面组合可能涉及父目录剪枝。它不是已验证根因，也不足以解释全部六组观察。当前包没有 pathspec 的安装版本、供应商源码或运行生成的正则；不能据此编造每组的基线输出。

合理实现可以有不同内部形式：

- 由 dirs/files 调用方明确传递类型，在匹配层为目录构造符合现用匹配器约定的路径；或分别处理目录匹配和普通文件匹配。应保持返回的 basename 不被附加分隔符污染。
- 保留现有规则分组并修正类型/路径处理，或换成按原顺序逐条评估的等价实现。分组优化不是题面指定接口，但处理大量文件的性能不能无理由严重退化；源码 `base/dvc/ignore.py:52-60` 已注明路径处理性能考虑。
- 若调查证明需要修正规则预处理，可以在转换边界实现与匹配器一致的语义；不应直接删除模式末尾 `/`，因为那会混淆目录与普通文件。
- 内部辅助函数名称、新增参数名、正则字符串形式、具体代码位置均未被题面指定。旧测试直接使用 `DvcIgnorePatterns(...).__call__`、`matches(dirname, basename)`，若改接口，应兼容其既有调用或提供默认值；这里是公开兼容面，不是要求某个新命名。
- 工作树与 GitTree 都有 dirs/files 信息。为了辨别类型而对真实磁盘调用 `os.path.isdir` 并不足够：旧测试要求读取某个 Git 分支的树，分支中的路径不一定存在于当前工作树。无需因此把所有树类重构。

没有需求要求新增 CLI、配置键、警告文字或修改用户的 `.dvcignore`。也没有公开依据把这次修复扩大为多层 `.dvcignore` 优先级重设计：`DvcIgnoreFilter.ignores` 当前为集合且逐个过滤（`base/dvc/ignore.py:120-137`），但本题例子只给了一份忽略文件。

关于测试修改限制：原“禁止改测试”若适用，仍可在非测试源码修复，并运行已有测试与终端临时复现；本题没有证据显示测试文件本身是必要的产品修复位置。若该原指令不适用，补充目录否定、同名文件、父目录剪枝的回归测试会更完整。`environment_brief.md:20-25` 已说明“所有测试修改都会恢复、永不计分”不能代表当前机制；本审查既不沿用该解释，也不自行取消原禁止指令。实际适用性是共享输入/运行条件待核对项。

## 3. 信息缺口及其影响

| 缺项或未知 | 对开发的影响 | 是否阻碍开始 |
|---|---|---|
| 原报告没有目录树、触发命令、实际/预期输出 | 需要从上述 Tree API 构造小型复现；应分别检查根目录、直接文件、深层文件、同名普通文件 | 不阻碍。接口和旧测试已经提供正常调查入口。 |
| 六种规则是否意在完全等价；仅否定后代是否应重开父目录 | 影响要求的语义边界。不能把“让六组输出都相同”当成唯一验收解释 | 不阻碍修复明确的目录匹配问题；若要求改变父目录规则，需补充明确的公开约定或示例。 |
| 实际 Python、pathspec、pytest 及其他依赖版本 | 直接关系到能否导入、收集测试和重现。`setup.py:66` 只有 `pathspec>=0.6.0`，不是锁定版本 | 静态分析可继续；实际开发须先做 actor 导入及版本核验。 |
| README 的 Conda 段提到 Python 2.7，而 setup 要求 3.6+ | 安装说明存在陈旧信息（`README.rst:134` 对 `setup.py:162-168`） | 不阻碍；此基线以 setup 和代码兼容性为准，旧 CI 覆盖 3.6–3.8（`.travis.yml:36-60`）。 |
| 公开贡献指南和完整安装指南在外链 | 本包仅有链接（`CONTRIBUTING.md:1`、`README.rst:91-92`），未访问 | 当前无需外链即可定位问题和测试。若需确切历史模式规范，可请求补充相应公开文档，而不是搜索未来修复。 |
| 实际容器的解释器、资源、可写路径和工具 | 包中只是声明（`environment_brief.md:8-13`） | 必须由实际 actor 验证，不能判定环境已通过或失败。 |

本题不需要远程数据集、训练资产或线上云存储服务。测试样本可由本地几层目录和小文本文件生成。`base_identity.json:8-12` 记录无 symlink、无未实体化 LFS 指针、无 gitlink，且不导出 Git 元数据；这是包的元数据声明，并非本次重新校验所有 blob 的结果。没有看到必须补子模块或历史才能理解该问题的证据。

## 4. 开发需求与建议命令（全部未执行）

下列命令仅供实际解题 actor 在 `/testbed` 中验证，不在静态导出的 `base/` 执行。所有“预计”都是基于公开代码的预期，不是运行结果。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小建议，未执行 | 预计现象 |
|---|---|---|---|---|
| Python 导入、规则转换 | `base/dvc/ignore.py:1-13,32-43`；`base/setup.py:49-82,162-168` | bundle 声称 conda 激活；brief 明确未验 | 命令 A：记录解释器及包版本，导入项目模块 | 成功导入是后续前提；若缺依赖或 API 不兼容，应归环境问题，不能当作 negation 复现。 |
| 最小目录匹配复现；临时文件系统 | `base/dvc/ignore.py:45-73`；`base/tests/unit/test_ignore.py:9-32` | brief 声称 workspace/home 可写；tmp 配额仅是默认声明 | 命令 B：创建小目录、打印七组规则的目录列表和可见文件；每组新建 CleanTree，避免缓存污染 | 工作对照应保留 scripts 内容并排除 outside；目录型否定的基线可能把 scripts 剪掉。确切结果取决于待验 pathspec；仅后代否定组只做诊断，不预设通过。 |
| 旧单元测试及 pytest 收集依赖 | `base/tests/unit/test_ignore.py`；`base/tests/conftest.py:3-6`；`base/tests/remotes/s3.py:7` | 测试工具路径由旧 hints 声称；没有导入或测试输出 | 命令 C：单个测试文件。除了 pytest/mock，公共 conftest 会导入 remotes，进而顶层导入 `moto.mock_s3` | 应保留所有旧断言。旧测试缺本题组合，因此全通过也不能证明新问题已修复。没有云凭据需求，但测试收集可能需要额外包。 |
| 功能级树行为、临时 DVC repo | `base/tests/func/test_ignore.py`；`base/tests/dir_helpers.py:90-108,250-288` | writable workspace/home 只是计划；实际权限/依赖未验 | 命令 D：整个 ignore 功能文件；命令 E：必要时补 tree 的两项相关测试 | 支持 Unicode、嵌套忽略、分支读取和子仓库边界。包含 scm fixture 的用例需本地 Git 和临时提交身份。 |
| Git 可执行程序及本地提交身份 | `base/tests/dir_helpers.py:99-108,279-289`；`base/scripts/ci/install.sh:13-14` | bundle 没有单独证明 Git 可用 | 命令 D/E 用调用级 Git 身份变量；可先执行 `git --version`（建议，未执行） | 应能初始化和提交本地临时 repo，无需公网 remote；不需要改全局 Git 配置。 |
| 可编辑源码与依赖安装 / 构建 | `base/setup.py:138-175`；`base/scripts/ci/install.sh:11` | 解释器/系统包写权限和网络可用性未验；brief 不允许假定公网 | 如果已导入本地源码，无需重装或完整构建。确需 editable 安装时建议 `python -m pip install --no-deps --no-build-isolation -e .`（未执行，先核对写权限和 setuptools）。缺包需预装或声明的离线包源 | 本地源码应成为实际导入路径。不能照抄旧 CI 下载全部远端依赖作为最低条件，也不能把安装失败误记为源码失败。 |
| CPU、内存、网络服务 | 本题逻辑是本地路径/正则；`environment_brief.md:10-12` | 默认 2 CPU / 4 GiB / PID512、tmp1 GiB、home256 MiB，均非本题实测 | 窄测试单进程即可；不用完整 runner 的 4 workers。无额外服务命令 | 预计规模很小，不需要 GPU、模型、云存储。资源能否实际满足仍未验。 |

**命令 A：最小导入与版本记录，建议，未执行。**

```bash
python - <<'PY'
import sys
import pkg_resources
import dvc.ignore
from pathspec.patterns import GitWildMatchPattern

print(sys.executable)
print(sys.version)
print(dvc.ignore.__file__)
for name in ("pathspec", "funcy", "pytest", "mock", "moto"):
    try:
        print(name, pkg_resources.get_distribution(name).version)
    except pkg_resources.DistributionNotFound:
        print(name, "MISSING")
for pattern in ("*", "/*", "!scripts", "!/scripts", "!/scripts/",
                "!/scripts/*", "!/scripts/**", "!scripts/"):
    print(repr(pattern), GitWildMatchPattern.pattern_to_regex(pattern))
PY
```

**命令 B：规则与树行为矩阵，建议，未执行。** 这段诊断只在临时目录生成小样本，不修改仓库测试文件；它输出观察值，不把有歧义的六组一律写成相同断言。

```bash
python - <<'PY'
import os
import tempfile
from pathlib import Path
from dvc.ignore import CleanTree, DvcIgnorePatterns
from dvc.scm.tree import WorkingTree

cases = [
    "*\n!scripts\n", "*\n!/scripts\n", "/*\n!/scripts/\n",
    "/*\n!/scripts/*\n", "/*\n!/scripts/**\n",
    "/*\n!scripts/\n", "/*\n!/scripts\n",
]
for rules in cases:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "scripts" / "nested").mkdir(parents=True)
        (root / "other").mkdir()
        for rel in ("scripts/keep.txt", "scripts/nested/deep.txt",
                    "other/drop.txt", "outside.txt"):
            (root / rel).write_text("x", encoding="utf-8")
        ignore_file = root / ".dvcignore"
        ignore_file.write_text(rules, encoding="utf-8")
        raw_tree = WorkingTree(str(root))
        matcher = DvcIgnorePatterns(str(ignore_file), raw_tree)
        print("rules", repr(rules))
        print("directory input", matcher(str(root), ["scripts"], []))
        print("file input", matcher(str(root), [], ["scripts"]))
        tree = CleanTree(raw_tree)
        print("walk", sorted(os.path.relpath(p, root)
                             for p in tree.walk_files(str(root))))
        print("isdir", tree.isdir(str(root / "scripts")))
        print("isfile", tree.isfile(str(root / "scripts" / "keep.txt")))
PY
```

**命令 C：旧单元测试，建议，未执行。**

```bash
python -m pytest -q tests/unit/test_ignore.py
```

**命令 D：旧功能测试，建议，未执行。**

```bash
GIT_AUTHOR_NAME='DVC Tester' GIT_AUTHOR_EMAIL='dvctester@example.com' GIT_COMMITTER_NAME='DVC Tester' GIT_COMMITTER_EMAIL='dvctester@example.com' python -m pytest -q tests/func/test_ignore.py
```

**命令 E：仅在改动影响 CleanTree 集成时追加，建议，未执行。**

```bash
GIT_AUTHOR_NAME='DVC Tester' GIT_AUTHOR_EMAIL='dvctester@example.com' GIT_COMMITTER_NAME='DVC Tester' GIT_COMMITTER_EMAIL='dvctester@example.com' python -m pytest -q tests/func/test_tree.py::TestWalkInGit tests/func/test_tree.py::test_cleantree_subrepo
```

旧 CI 是 `python -mtests`（`base/scripts/ci/script.sh:6`），其 runner 默认启用 `-n=4`、覆盖率和 timeout 插件（`base/tests/__main__.py:19-23`）；本题最小检查不需要照搬这一全仓配置。不建议为了纯 Python 匹配修复执行系统包、snap 或跨平台安装构建。

## 5. 实际阅读与暴露范围

### 实际打开的材料

以下只记录读取文本，不表示执行其内容。

| 文件 | 阅读范围 |
|---|---|
| 指定的 `roles/public_reader.md` | 全文，仅这一角色卡，没有打开其父目录或其他角色产物。 |
| `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json` | 全文；其中 prompt 仅是静态渲染。 |
| `base/dvc/ignore.py` | 全文，1–250。 |
| `base/tests/unit/test_ignore.py` | 全文，1–116。 |
| `base/tests/func/test_ignore.py` | 全文，1–175。 |
| `base/dvc/scm/tree.py` | 全文，1–97。 |
| `base/dvc/scm/git/tree.py` | 全文，1–191。 |
| `base/dvc/repo/__init__.py` | 40–155；另有忽略相关搜索命中行。 |
| `base/tests/func/test_tree.py` | 全文，1–243。 |
| `base/tests/conftest.py`、`base/tests/func/conftest.py` | 全文。 |
| `base/tests/dir_helpers.py` | 76–116、235–291，及导入/fixture/ignore 相关搜索命中行。 |
| `base/tests/remotes/__init__.py` | 全文，1–66。其他 remotes 文件只读顶层 import 搜索行。 |
| `base/setup.py` | 1–176。最初长工具输出有截断，随后明确重读 1–85、101–176；85–100 的 remote extras 在首轮返回中可见。 |
| `base/setup.cfg`、`base/pyproject.toml`、`base/CONTRIBUTING.md` | 全文。 |
| `base/README.rst` | 最初请求 1–235，但批量返回截断；明确完整复读 88–190。另见部分前段及安装关键词搜索上下文，不宣称已完整审阅 1–235。 |
| `base/.travis.yml` | 全文，1–170，包含与本题无关的旧部署配置；未使用其中配置或变量。 |
| `base/scripts/ci/install.sh`、`base/scripts/ci/script.sh`、`base/tests/__main__.py` | 全文。 |

### 文件发现与搜索记录

- 对本题公开目录运行过 `rg --files`，只列出路径；该列表输出截断。未把路径列表中所有文件当成已读内容，未打开 `MANIFEST.in`。
- 在本题 `base/dvc`、`base/tests`、安装说明及配置中检索了 `DvcIgnore`、`dvcignore`、`CleanTree`、`GitWildMatchPattern`、`pathspec`、`gitignore`、安装和测试关键词。第一轮把 `pytest` 关键词用于 `tests/func` 范围，返回较多旧测试命中且发生截断；这些仅为搜索片段，未据此声称全仓测试已审阅。
- 在本题 `base` 内使用 `rg --files --hidden` 寻找 tree 测试、conftest、pytest/tox/Makefile 和 `.gitmodules` 路径；未返回 `.gitmodules`，元数据也记录 gitlinks 为空。
- 搜索 `.github`、`.travis.yml`、`.coveragerc`、`.pre-commit-config.yaml` 的安装/pytest关键词，只见 `.github/workflows/check-patch.yaml:15` 的 Python 3.8 行；没有读取该 workflow 全文。尝试的 `appveyor.yml` 不存在。
- 初次按 `tests/remotes.py` 查 fixture 导入时该文件不存在，随后确认并读取 `tests/remotes/__init__.py`。这些是静态查找失配，不是测试失败。

### 未查项与限制

没有读取其他题、私有评分材料、gold、历史、批次 manifest/结论、其他角色输出或权威 ROOT 外的仓库材料；没有访问 `.git`、镜像、公共祖先历史或外链。没有执行 Python、Git 命令、测试、安装、构建或容器，也没有调用模型或网络服务。所建议的复现和测试全部未执行。

因此不声称已经看到实际模型消息、CLI system message、actor shell、包版本、运行资源或测试结果。隔离范围是本轮遵守的阅读约定，不是文件权限隔离或预训练无污染证明。本轮未发生已知私有材料误读。

最值得交给后续实际开发核验的两个未知是：实际 pathspec 版本及七组规则的行为矩阵；仅否定后代路径是否应自动重新开放父目录的语义边界。它们不妨碍根据公开源码开始正常调查。
