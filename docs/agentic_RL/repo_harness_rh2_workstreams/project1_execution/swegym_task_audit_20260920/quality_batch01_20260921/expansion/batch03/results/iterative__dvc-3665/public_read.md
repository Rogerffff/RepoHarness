# iterative__dvc-3665 公开要求静态审查

审查依据限于指定角色卡及本题 `PUBLIC_DIR`。下文路径均相对本题公开目录；只进行了文本读取和检索，没有执行项目、安装依赖、修改 `base/`、联网或访问 Git 历史。所有开发与验证命令均为**建议，未执行**。未接触本题私有材料；这一阅读范围是协作约定，不是文件权限隔离或预训练无污染证明。

**1. 需求表**

| 行为 | 公开依据 | 要求强度及边界 |
| --- | --- | --- |
| 相同相对缓存位置的配置不因 Windows/Unix 切换而出现分隔符差异 | `user_prompt.txt:3-19`：Windows 写入 `..\..\xyz`，Linux 写入 `../../xyz`，造成 Git 噪声；Windows 手工使用 Posix 风格可工作 | 消除跨平台配置差异是明示目标。统一保存为 `/` 是由给出的 Linux 示例及 Windows 兼容声明可合理推知的预期；题面未给形式化输出规范，但不能仅隐藏 diff 或改变显示而保留文件差异。 |
| `dvc cache dir` 的输入相对当前目录解释，持久化时相对配置文件所在目录 | `base/dvc/command/cache.py:53-57`；`base/tests/func/test_cache.py:160-178` | 接口明文约定；仓库根目录下输入 `../xyz` 对应 `.dvc/config` 的 `../../xyz`。更换分隔符不应改变目标目录，也不应把相对设置全部变成绝对路径。 |
| 配置加载后仍可实际使用该缓存，默认缓存位置不变 | `base/dvc/config.py:289-310`；`base/dvc/cache.py:52-65`；`base/dvc/remote/local.py:49-64`；`base/tests/func/test_cache.py:172-178` | 由代码和公开测试合理推知。序列化格式与运行时路径表示可不同，只需解析、读写和缓存存放位置正确。没有要求运行时所有字符串也使用 `/`。 |
| 绝对缓存路径继续受支持 | `base/tests/func/test_cache.py:152-158`；`base/dvc/config.py:318-324` | 旧测试明确要求保存输入的绝对路径字符串。题面未要求将绝对路径也统一为 Posix 风格；将所有 Windows 绝对字符串改写作为硬性验收，不能仅由题面推出，且会与此旧测试发生冲突。 |
| 保持命令名、参数、配置键及配置层级 | `base/dvc/command/cache.py:7-11,39-59`；`base/dvc/command/config.py:52-74`；`base/dvc/config.py:216-220,248-259` | `cache dir <value>`、`[cache] dir`、默认 repo 层及 `--local/--global/--system` 已有约定；无参数返回值 254 有旧测试依据（`base/tests/func/test_cache.py:147-150`）。题面未要求新的 CLI 选项或输出。 |
| 其他配置编辑不应把相对缓存路径重新写回平台分隔符 | `base/dvc/config.py:293-310,342-357`；`base/dvc/command/config.py:25-31` | 由目标和共享保存路径合理推知：任何 `Config.edit` 会重新保存路径字段。仅首次调用产生 `/`、随后编辑无关选项又产生反斜杠，会重新制造所述噪声。 |
| 共享路径处理不能破坏 remote URL、本地目录及配置合并 | `base/dvc/config.py:307-331,333-357`；`base/dvc/command/remote.py:26-44`；`base/tests/func/test_remote.py:41-66`；`base/tests/func/test_config.py:93-109` | 合理的回归约束。`remote.*.url` 与 `cache.dir` 共享转换，但 issue 只明确点名缓存。是否同步统一本地 remote 相对路径属于合理扩展范围，不能直接当作题面单独明示的需求；带 scheme 的 URL 现有代码直接保留。 |

**2. 合理实现范围**

可以在共享配置序列化层制定路径格式，也可以为缓存字段制定专用持久化策略；只要上述可观察行为一致，内部辅助函数、类名、转换位置和字符串组织方式不应被唯一限定。已有 `PathInfo.as_posix()` 表明仓库具备按平台路径规则输出 `/` 的概念（`base/dvc/path_info.py:23-43`），其公开测试覆盖 Windows 相对路径和深层 `..`（`base/tests/unit/test_path_info.py:65-91`），但没有证据要求修复必须调用这个具体方法。

若共享转换也统一本地 remote 相对路径，在保持目标位置和 URL 语义的前提下是合理设计；只针对缓存建立稳定持久化规则也有题面支持。只在命令入口替换字符串而忽略之后的配置重写，需要额外说明怎样满足稳定性。直接对任意输入全局替换反斜杠则须检查 POSIX 本地文件名语义、Windows 盘符/UNC 路径及 URL：这些不是题面逐一要求的新特性，但不能借修复破坏已有路径含义。`base/dvc/utils/__init__.py:315-324` 已保留 Windows 跨盘相对化的处理；不宜用本题推导出新的跨盘规则。

题面没有要求主动扫描/迁移既有配置文件、在 Linux 自动理解所有 Windows 历史路径、重新定位绝对路径、改变 CLI 日志、统一文件换行符或更改缓存内容布局。这些扩展有多种合理解释，不能凭当前公开材料设为唯一结果。

**3. 初态线索与疑义**

公开入口足够明确：`CmdCacheDir.run` 将参数交给 `Config.edit`（`base/dvc/command/cache.py:7-11`）；`Config._save_paths` 对相对值调用 `relpath`（`base/dvc/config.py:315-326`）；该帮助函数最终使用 `os.path.relpath`（`base/dvc/utils/__init__.py:315-324`）。这条链与平台分隔符差异相符，是静态调查线索，不是已执行的根因复现。`_load_paths`、缓存消费者和 CLI 帮助可解释多出来的一层 `..`，无需为此要求额外题面信息。

真正需要区分的未知：

- **Windows 验证条件**：题面报告 Ubuntu 与 Windows 10，bundle 提供一个镜像名及 digest，但未证明存在可运行的 Windows actor。Linux 上普通 `cache dir ../xyz` 原本即写入 `/`；Linux 测试通过不能证明 Windows 问题被触发或修复。可通过受控 Windows 路径语义实验缩小问题，但其结果不等于原生 Windows 文件系统/CLI 验证。
- **旧公开测试与目标发生具体冲突**：`base/tests/func/test_cache.py:168-170` 以 `os.path.join` 生成预期，因此原生 Windows 上要求反斜杠；按题意统一为 `/` 后，该旧相对路径断言预计失败。若共享转换改变 remote，相同问题还出现在 `base/tests/func/test_remote.py:48-50`。Linux 上两者的预期已经是 `/`，不会暴露此冲突。这里是静态预期，没有运行结论。
- **共享输入中的操作限制**：`public_bundle.json:1` 的 `public_hints` 要求只改 NON-TEST 源码、不得改测试、测试保持窄范围；这是 harness 操作指令，不是 issue 功能要求。若“禁止改测试”适用，可进行源码修复并用独立临时实验验证，但不能修正上述 Windows 旧断言；若不适用，则可以更新旧格式断言并增加回归验证。实际适用范围待协调者核对，审查不自行取消原指令。该字段关于“所有测试修改都会恢复、永不计分”的旧解释不是当前机制证明；`environment_brief.md:20-26` 明确当前没有按测试文件名统一排除，仍存在官方文件恢复等具体限制。本角色未读取私有恢复清单，不能断言本题哪些文件会被恢复。
- **实际开发环境**：conda 已激活是 `public_hints` 的环境事实声明，尚未验证。源码、历史依赖版本、actor 身份权限、文件描述符限制以及是否能够收集公开测试均待 CPU actor 核验。缺少这些运行证据不等于题目不可开发。
- **外链和历史**：README/CONTRIBUTING 的完整安装与贡献指南是外链，未随包给出且未访问（`base/README.rst:88-92,149-153,202-203`；`base/CONTRIBUTING.md:1`）。当前局部任务已有 CLI 帮助、安装元数据、代码和测试，未发现必须补充这些外链或公开祖先历史才能开始调查的理由。`base_identity.json:8-11` 显示无 gitlinks、无未物化 LFS 指针且未导出 Git 元数据；没有本题必须补子模块的线索。

**4. 开发需求表**

以下命令拟在真实 actor 的 `/testbed` 使用；本审查没有运行它们。Windows 可执行相同 Python 代码，命令块的 heredoc 为 Bash 包装。只需局部 CPU 工作，不需要 GPU、云存储账号、网络数据集或外部缓存服务。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令与预期（全部建议，未执行） |
| --- | --- | --- | --- | --- |
| 身份、解释器、工作区和包导入 | `public_bundle.json:1`；`base/setup.py:49-85,162-174` | `/testbed`、bash/edit、agent/54321、默认资源仅为说明（`environment_brief.md:8-13`） | conda 激活、解释器兼容性、实际包版本、可写空间未验；README 的较旧 Python 说明不能替代安装元数据与实测 | `id`；`pwd`；`python -c 'import os, sys; print(sys.executable, sys.version, os.environ.get("CONDA_DEFAULT_ENV"))'`；`DVC_TEST=true python -c 'import dvc; from dvc.config import Config; from dvc.main import main; print(dvc.__version__)'`。预期身份与目录符合 profile，关键模块可导入；缺模块/版本错误属于环境入口失败。 |
| Python 依赖与离线安装资产 | 配置直接依赖 `funcy/configobj/voluptuous`（`base/dvc/config.py:8-11`）；完整运行与测试依赖在 `base/setup.py:49-136` | 网络仅模型代理和声明的内部服务，不保证公网下载（`environment_brief.md:10`） | 是否预装或有内部 wheels 未给出；不能假设可用最新 PyPI 依赖替代历史环境 | `python -m pip check`。若源码需要注册且依赖已齐，`python -m pip install --no-deps --no-build-isolation -e .`；若依赖缺失，应先补与环境相容的离线资产，再按安装元数据安装。以上均建议，未执行；不需要为本题预先安装所有 cloud extras。 |
| pytest 收集所需包、系统限制与临时目录 | `base/tests/conftest.py:3-8` 在收集时导入 mockssh/SSH/http 工具；`base/tests/__init__.py:3-36` 设置资源限制，Windows 需 win32file；`base/tests/basic_env.py:78-95,153-156` 创建小型本地无 SCM 仓库 | 仅声称可写工作区/home 和默认 CPU/内存，未核验实际运行（`environment_brief.md:9-12`） | 即使只选缓存测试也可能因公共 conftest 依赖或资源 hard limit 失败；无须据 SSH 导入推断本测试需要 SSH 服务 | `DVC_TEST=true python -m pytest --collect-only -q tests/func/test_cache.py::TestCmdCacheDir`。静态预计收集该类 3 项；若导入/资源设置失败，先处理环境。POSIX 可补查 `python -c 'import resource; print(resource.getrlimit(resource.RLIMIT_NOFILE), resource.getrlimit(resource.RLIMIT_NPROC))'`；以上均建议，未执行。 |
| 原问题的本地端到端复现 | 题面及 `base/dvc/command/cache.py:53-57`；测试验证缓存实际写入（`base/tests/func/test_cache.py:160-178`） | 当前包不是容器，未给 Windows actor；没有实际运行结果 | 需要原生 Windows 或明确标注局限的路径语义实验；全局/本地 actor 配置不得意外覆盖本例 | 下方 R1（建议，未执行）创建临时仓库。原 Windows 预期 `..\..\xyz`，最终格式断言失败；Unix 原版预计 `../../xyz`，断言通过；修复后两平台均应为 `../../xyz` 且数据仍写入选定缓存。 |
| 缓存和配置的窄范围公开测试 | `base/tests/func/test_cache.py:147-178`；`base/tests/func/test_config.py:34-114` | public_hints 允许窄范围验证，但未证明可执行 | 旧 Windows 相对断言与新目标冲突；Linux 通过仅表示现有回归检查通过 | `DVC_TEST=true python -m pytest -q tests/func/test_cache.py::TestCmdCacheDir`；`DVC_TEST=true python -m pytest -q tests/func/test_config.py`。建议，未执行；原实现可能全部通过，不能将其当作能捕捉本 bug 的现成回归测试。 |
| 共享 remote 转换及已有路径表达能力 | `base/dvc/config.py:329-331`；`base/tests/func/test_remote.py:41-66`；`base/tests/unit/test_path_info.py:65-91` | 同上；本地路径测试本身不要求远程服务 | remote 测试模块完整导入依赖未逐项核验；Windows 旧断言冲突同前 | 若改共享转换，建议、未执行：`DVC_TEST=true python -m pytest -q tests/func/test_remote.py::TestRemote::test_relative_path tests/func/test_remote.py::TestRemote::test_referencing_other_remotes`。辅助能力检查建议、未执行：`DVC_TEST=true python -m pytest -q tests/unit/test_path_info.py -k as_posix`；后者原版即应通过，不是本题修复证明。 |
| 构建/语法检查 | `base/setup.py:36-46,174-175` 是 Python 包；未见局部配置改动必须重新构建二进制的依据 | 未证明解释器/包目录可写 | 与实际安装是否指向工作树有关 | 无需整仓构建。可选建议、未执行：`python -m compileall -q dvc/config.py dvc/command/cache.py`，预期无语法错误；只验证语法，不验证 Windows 路径行为。 |

R1：跨平台本地场景，**建议，未执行**。使用真实 actor 环境，运行前确认没有覆盖本例的既有全局/system 缓存设置；此脚本不是对本地导出 `base/` 的执行授权。

```bash
# 建议，未执行；Bash 包装的 Python 代码
python - <<'PY'
import os
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["DVC_TEST"] = "true"
import configobj
from dvc.main import main

original_dir = os.getcwd()
with TemporaryDirectory(prefix="dvc3665-") as task_temp:
    root = Path(task_temp) / "repo"
    root.mkdir()
    try:
        os.chdir(str(root))
        assert main(["init", "--no-scm"]) == 0
        assert main(["cache", "dir", os.path.join("..", "xyz")]) == 0
        saved = configobj.ConfigObj(".dvc/config")["cache"]["dir"]
        print("saved:", repr(saved))
        Path("sample").write_text("sample data", encoding="utf-8")
        assert main(["add", "sample"]) == 0
        assert any((Path(task_temp) / "xyz").iterdir())
        assert saved == "../../xyz", saved
    finally:
        os.chdir(original_dir)
PY
```

`DVC_TEST` 禁用更新检查及 analytics 有公开代码依据（`base/dvc/updater.py:50-52`；`base/dvc/analytics.py:53-55`）。Linux 不应直接把 `..\xyz` 当作 Windows 复现输入：POSIX 上反斜杠不是同一目录分隔符。若另做 Windows 语义模拟，需要同时控制路径运算与平台选择，不能仅修改 `os.name` 就声称已验证完整 Windows CLI。已有 `PathInfo` 单测仅证明可在窄范围模拟其平台选择。

**5. 阅读范围与证据限制**

实际完整打开：角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；`base/README.rst`、`base/CONTRIBUTING.md`、`base/setup.py`、`base/setup.cfg`；`base/dvc/config.py`、`base/dvc/command/cache.py`、`base/dvc/command/config.py`、`base/dvc/version.py`、`base/dvc/__main__.py`、`base/dvc/__init__.py`；`base/tests/func/test_cache.py`、`base/tests/func/test_config.py`、`base/tests/conftest.py`、`base/tests/__main__.py`、`base/tests/__init__.py`、`base/tests/basic_env.py`、`base/tests/dir_helpers.py`。

实际局部打开：`base/dvc/utils/__init__.py:300-350`、`base/dvc/path_info.py:1-92`、`base/dvc/cache.py:1-73`、`base/dvc/remote/local.py:1-90`、`base/dvc/command/remote.py:1-125`、`base/dvc/analytics.py:38-68`、`base/dvc/updater.py:42-67`、`base/tests/unit/test_path_info.py:1-110`、`base/tests/func/test_remote.py:1-88`。

检索但未完整展开：本题文件路径清单；`base/pyproject.toml`、`base/dvc/main.py`、`base/dvc/repo/__init__.py`、`base/tests/unit/utils/test_utils.py` 的有关匹配；`base/tests/` 中 `cache dir`、路径转换与 `RelPath` 等相关引用，包括 `tests/remotes.py`、`tests/utils/__init__.py`、`tests/func/test_checkout.py` 等。全量路径列表输出有截断，不声称逐文件审阅。未查整仓测试、完整依赖导入图、完整 remote 后端、外链文档、资产实际可用性及任何历史/私有/其他题材料。

`user_prompt.txt` 只是当前函数的静态渲染，不能据此声称已经看过真实模型消息。`public_bundle.json` 会进入解题工作区的公开路径，其 hints 未出现在渲染消息中不代表 actor 不可读；它是否进入 CLI system message、原“禁止改测试”的实际适用范围以及 bash/edit 的真实执行状态仍未验（`environment_brief.md:3-12,20-26`）。`base/` 是指定提交的跟踪内容导出，未提供完整运行容器；本报告没有声称模型消息、运行资源、依赖、权限、原问题复现或开发条件已通过验证。
