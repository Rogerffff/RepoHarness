# iterative__dvc-3620 公开材料静态审查

本报告只依据角色卡及本题公开包；没有运行项目代码、安装依赖、修改 base、联网或读取私有评分材料。下列路径均相对于 PUBLIC_DIR。题目指定 base commit 为 `e05157f8e05e856d2e9966c30a3150c26b32b86f`（`public_bundle.json:1`）。

公开材料足以定位主要调用链并设计小规模复现。最重要的公开输入冲突是：issue 要消除软链接输出 unprotect 对缓存权限的副作用，而一条现有公开测试明确要求这种副作用发生。需要把旧测试期望与操作指令的适用范围分开核实，不能将旧测试全部通过直接等同于 issue 已修复。

## 1. 需求表

| 行为 | 要改变或保留的内容 | 依据及确定程度 |
|---|---|---|
| 软链接输出 unprotect | 用独立副本替代输出软链接时，不应因删除链接而修改缓存目标权限。仅在后续 status 中恢复权限不足以满足该目标。 | **明示**：`user_prompt.txt:3–7,21–34`。它指出 `os.chmod(p, perm)` 改的是缓存目标。 |
| 输出仍可修改且内容不变 | 保留 unprotect 的目的：脱离原链接关系，内容不丢失，最终输出按本地 remote 的文件模式可写。 | **合理推知**：`base/dvc/remote/local.py:412–432`；`base/tests/func/test_checkout.py:488–501` 检查链接被解除；`base/tests/func/test_unprotect.py:19–25` 检查输出变为可写。 |
| 替换期间的完整数据 | 保留先完整复制到临时文件、再替换输出的性质，避免原路径在复制过程中暴露半份文件。不得据此额外声称原实现具有无间隙、跨平台的原子替换保证。 | **合理推知**：`base/dvc/remote/local.py:415–424` 的注释和顺序。 |
| 默认权限与 cache 类型 | 缓存保护模式为 `0o444`；默认输出模式 `0o644`，shared=group 为 `0o664`；默认 cache 类型仍是 reflink/copy。此修复没有要求修改这些默认值。 | **公开代码约定**：`base/dvc/remote/local.py:34–37`；`base/dvc/remote/base.py:95–112`。因此复现必须主动建立软链接，不能依赖默认 cache 类型。 |
| 其他 unprotect 输入 | 普通文件保留无需复制、只调输出权限的行为；目录继续处理其文件；不存在的路径仍报告错误；硬链接输出仍能解除链接并可写。 | **合理推知**：`base/dvc/remote/local.py:412–450`；`base/dvc/command/unprotect.py:12–21,25–37`。issue 没要求改变这些接口。 |
| 通用删除接口 | 如果修改共享 `remove`，仍应支持字符串/PathInfo、普通文件及目录、断链删除，并保留“目标不存在时不报错”的语义；有需要时仍要处理文件权限导致的删除失败。 | **代码和测试约定**：`base/dvc/utils/fs.py:118–143`；`base/tests/unit/utils/test_fs.py:163–172`；`base/tests/func/test_remove.py:39–65`。权限回调具有跨平台背景，见 `base/tests/func/test_unprotect.py:27–30`。不代表所有任意权限失败必须成功。 |
| 硬链接缓存权限 | issue 明指软链接；是否一并改变 POSIX 硬链接删除前无条件 chmod 的旧行为，公开要求未唯一确定。必须保留硬链接输出能解除链接，但不能把“硬链接缓存必须继续变可写”不加区分地当作用户新增目标。 | **多种合理范围**：相同 `remove` 调用见 `base/dvc/remote/local.py:412–424`；旧硬链接测试明示接受缓存先可写后恢复，见 `base/tests/func/test_unprotect.py:7–34`。 |
| 目录软链接、并发竞争、特殊文件系统 | 已有实现对目录使用 `os.path.isdir` 和递归删除；题面说的是 symlinked files。是否顺带新增目录软链接支持、处理所有竞争窗口、在特殊文件系统上保证目标权限完全不动，未获充分规定。 | **仍有合理边界差异**：`base/dvc/utils/fs.py:132–143`、`base/dvc/remote/local.py:440–450`。这些属于实现审查边界，不是最小复现缺失。 |

### 公开旧测试与 issue 的冲突

`base/tests/unit/remote/test_local.py:34–61` 的 `test_is_protected` 同时参数化 hardlink/symlink，先保护 foo，再 unprotect link。在非 Windows 的 symlink 分支，最后要求 `not remote.is_protected(foo)`。而 `is_protected` 直接比较目标文件权限与 `CACHE_MODE`（`base/dvc/remote/local.py:532–538`）。若修复使 foo 权限保持 `0o444`，这个旧断言将与新目标冲突；这是源码级推断，未实跑。

`base/tests/func/test_unprotect.py:27–34` 是另一项相关历史约定，但它使用 hardlink，不能与软链接冲突混为一谈。只修软链接可保留该硬链接旧期望；若采用更普遍的“删除成功时不预先 chmod”策略，POSIX 硬链接的这一旧期望也可能变化。相反，relink、repeated add 后重新保护 cache 的测试属于后续行为要求，不直接要求 unprotect 短暂放开 cache 权限（`base/tests/func/test_checkout.py:504–519`；`base/tests/func/test_add.py:617–636`）。

## 2. 合理实现范围

公开需求约束可观察结果，没有规定新增 helper 名称、精确补丁位置或内部调用次数。以下实现方向在保留相关接口与异常语义时都有合理性，不应仅因与某一种代码结构不同而排除：

- 在通用删除路径区分软链接，避免为删除链接而修改其目标权限。
- 调整删除及权限重试的安排，使不需要权限调整的删除先完成，同时保留必要的错误处理。
- 在 unprotect 的链接替换流程中保证不触发目标权限修改，并保持复制完成后才替换原输出的性质。

前两种更广泛地处理题面指认的共享函数；第三种可能只覆盖 unprotect 场景。题面把共享 `remove` 指为原因，因此应额外检查其它删除调用者，但没有明示要求重构整个文件系统工具层。仅在删除后再把缓存设成固定 `0o444`，不能自然证明任意原权限未被改动，也可能存在副作用窗口；应以“保持原目标权限”的实际行为评估，而不是固定函数名。

跨平台细节需要保留：源码声称支持 Python >=3.5，并有 Linux 3.5–3.8、Windows 3.7/3.8、macOS 的历史 CI（`base/setup.py:162–169`；`base/.travis.yml:36–63`）。只在部分平台可用的 chmod 选项不能仅凭 Linux 复现成功就被视为已验证全部支持范围。公开测试已明确区分 Windows 软链接权限行为（`base/tests/unit/remote/test_local.py:57–59`）。

已有外部命名和 CLI 返回值有约定：`dvc unprotect`、`targets`、成功返回 0、捕获 DvcException 后返回 1（`base/dvc/command/unprotect.py:12–39`）；题目没有新日志或输出文本要求。

## 3. 初态线索、输入分层与疑义

调查入口清楚：`CmdUnprotect.run → Repo.unprotect → RemoteLOCAL.unprotect → _unprotect_file → dvc.utils.fs.remove → _chmod`。对应位置为 `base/dvc/command/unprotect.py:12–21`、`base/dvc/repo/__init__.py:158–159`、`base/dvc/remote/local.py:412–450`、`base/dvc/utils/fs.py:118–143`。输出对象和 stage 也有调用入口（`base/dvc/output/base.py:336–338`；`base/dvc/stage.py:357–379`）。阅读这些调用者是正常开发工作，不是题面缺陷。

题面两处粘贴代码换行损坏（`user_prompt.txt:10,26,31`），但 base 中完整函数可直接读到，不阻碍定位。报告者只给 DVC 0.91.1，没有 OS、Python、文件系统或缓存共享配置（`user_prompt.txt:4–7`）。缺这些信息限制“原报告环境完全复刻”，但普通 POSIX 文件/软链接即可检验核心权限副作用，不需要用户数据或外部附件。

输入需区分为三层：

| 层次 | 内容及影响 |
|---|---|
| Issue 需求 | 消除软链接输出 unprotect 对缓存目标权限的修改，见 `user_prompt.txt:3–34`。 |
| Harness 操作指令 | `public_bundle.json:1` 的 public_hints 要求改 NON-TEST 源码、禁止改测试、窄范围运行测试并简短收尾。这些不是 DVC 产品行为要求。若禁改测试适用，源码修复仍可做，但不能通过编辑旧冲突断言使本地旧套件一致；应显式报告旧测试与新要求不符。若该指令不适用，同步调整旧测试及增加回归测试才成为允许的开发路径。此审查不授权取消原指令。 |
| 待验环境声明 | public_hints 宣称 /testbed、testbed conda 已激活、工具可用；bundle 给出镜像标签/digest。它们不是实际 actor 验证结果。环境说明要求另做身份、解释器、依赖及测试可执行性验证（`environment_brief.md:3–13,18–24`）。 |

“所有测试改动都会恢复、永不计分”是旧提示中的机制解释，不能当作当前事实：环境说明称已取消按测试文件名统一排除，仍有具体官方文件恢复限制（`environment_brief.md:18–23`）。哪些文件恢复、本题旧冲突断言最终是否参与验收、实际禁改测试指令如何注入，公开包不能确认。它们需登记为共享输入/运行条件问题，不据此判断题目无效。

bundle 会进入真实解题工作区可见路径；其字段不在静态 user_prompt 中，不代表解题者读不到（`environment_brief.md:23–24`）。本报告不推断实际 system message 或模型收到的消息。

没有发现核心需求依赖缺失外链内容。README/CONTRIBUTING 的安装及贡献指南外链没有打开；本地 setup、CI、调用者和公开测试已足以形成最小开发步骤。未请求祖先历史，定位此副作用目前不需要历史。

## 4. 开发需求表

以下全部命令均为**建议，未执行**，面向实际 actor 在 /testbed 工作区执行，不是在本静态 base 导出中执行。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 待验缺口 | 最小命令及预计现象 |
|---|---|---|---|---|
| 解释器、身份和可导入源码 | `base/setup.py:49–85,162–169`；bundle 的 conda 声明 | 仅声明 profile=agent/54321、工作区/home 可写；解释器与依赖仍待验（`environment_brief.md:8–12`） | 实际 UID、Python 版本、import 路径、conda 是否生效、旧依赖组合 | C1（建议，未执行）。预计应打印解释器信息并成功导入目标模块；失败则先归因环境，不能当作原 bug 复现。 |
| 本地缓存文件、软链接、chmod/unlink/rename | `base/dvc/utils/fs.py:118–143,174–205`；`base/dvc/system.py:45–50,105–122`；`base/dvc/remote/local.py:412–450` | 可写目录及资源限额是说明层声明；未验证文件系统语义 | actor 对临时目录与自建目标的写/改权限；软链接支持；普通 POSIX 权限语义。无需 GPU、大数据或公网。reflink 不支持时有复制回退，不应要求 reflink 必须成功 | C2（建议，未执行）。预期原代码在普通 POSIX 上把缓存从 0444 改成其它权限（常见 0777），最后模式相等断言失败；符合 issue 的行为应保持 0444，输出成为内容相同、模式 0644 的普通文件。 |
| pytest 与公共 fixture 导入 | `base/setup.py:110–133`；`base/tests/conftest.py:3–8`；`base/tests/utils/httpd.py:6` | 没有依赖安装或可运行测试证据；不假定公网下载（`environment_brief.md:10–13`） | pytest、mock/pytest-mock、mock-ssh-server、RangeHTTPServer 等兼容版本；窄测试也会加载公共 conftest。SSH/HTTP fixture 未被这些节点使用，不因此要求启动服务或云凭据 | C3（建议，未执行）先收集。预计节点能收集；ModuleNotFoundError/插件或 pathlib 兼容错误属于环境缺口。 |
| 普通删除和公开 unprotect 测试 | `base/tests/unit/utils/test_fs.py:163–172`；`base/tests/unit/remote/test_local.py:34–61`；`base/tests/func/test_remove.py:39–65` | 2 CPU/4 GiB 等仅默认声明，不是实测；测试临时资产由 fixture 生成 | 应以实际 actor 跑，尤其 os.access 的结论受身份影响；不应以 root 跑出的可写判断替代 agent。旧 symlink 断言与目标相反 | C4、C5（均建议，未执行）。基础删除/断链测试预计仍成功；旧 `test_is_protected[symlink]` 原代码预计成功，而符合新要求的修复在 POSIX 上预计触发旧断言失败，须解释冲突。 |
| 硬链接与后续 relink 行为 | `base/tests/func/test_unprotect.py:7–34`；`base/tests/func/test_checkout.py:488–519` | 文件系统和资源未实际验证 | 硬链接支持；窄化到 symlink 的修复与普遍改变预先 chmod 的修复，对旧硬链接权限断言有不同影响 | C6（建议，未执行）。解除输出链接、输出可写、relink 重新链接应保留；若同时改善硬链接缓存权限，TestUnprotect 的“缓存先可写”断言可能不再成立。 |
| 本地构建/安装资产 | `base/setup.py:17–46,138–176`；`base/scripts/ci/install.sh:11`；`base/scripts/ci/script.sh:6` | 镜像可能预装包/构建产物，但包内没有运行事实；解释器包目录写权限待验 | 已安装依赖及 setuptools；若缺包，需离线可用依赖资产或声明的内部来源。不能从 README 的联网安装命令推定联网许可 | C7（建议，未执行，可选）。预计构建本地 Python 包文件；此题本身不需要完整发布构建。历史 CI 的全量 extras 安装与 `python -mtests` 不作为最小前置条件。 |

**C1 — 建议，未执行：身份、解释器与最小目标导入。**

```bash
id
python -c "import os, sys; print(sys.executable); print(sys.version); print(os.getuid()); from dvc.utils.fs import remove; from dvc.remote.local import RemoteLOCAL; from dvc.path_info import PathInfo; print('target imports OK')"
```

**C2 — 建议，未执行：直接覆盖 RemoteLOCAL.unprotect 的本地复现。** 以普通 POSIX 文件系统为前提；只用自建临时资产，比较 mode bits 而非依赖 os.access。

```bash
python - <<'PY'
import os
import stat
import tempfile
from pathlib import Path
from dvc.path_info import PathInfo
from dvc.remote.local import RemoteLOCAL

with tempfile.TemporaryDirectory(prefix="dvc-3620-") as tmp:
    cache = Path(tmp) / "cache"
    output = Path(tmp) / "output"
    cache.write_text("foo")
    cache.chmod(0o444)
    os.symlink(str(cache), str(output))
    before = stat.S_IMODE(cache.stat().st_mode)
    RemoteLOCAL(None, {}).unprotect(PathInfo(str(output)))
    after = stat.S_IMODE(cache.stat().st_mode)
    print("cache before/after:", oct(before), oct(after))
    print("output is symlink:", output.is_symlink())
    assert not output.is_symlink()
    assert output.read_text() == cache.read_text() == "foo"
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert after == before, "unprotect changed cache permissions"
PY
```

**C3 — 建议，未执行：窄范围收集检查。**

```bash
python -m pytest --collect-only -q tests/unit/utils/test_fs.py tests/unit/remote/test_local.py
```

**C4 — 建议，未执行：普通删除及目录/断链删除。**

```bash
python -m pytest -q tests/unit/utils/test_fs.py::test_remove tests/func/test_remove.py::TestRemoveBrokenSymlink tests/func/test_remove.py::TestRemoveDirectory
```

**C5 — 建议，未执行：显示旧公开期望冲突。** 此节点本身不是 issue 修复的正向验收标准。

```bash
python -m pytest -q 'tests/unit/remote/test_local.py::test_is_protected[symlink]'
```

**C6 — 建议，未执行：硬链接及 relink 回归。** 应分别解读行为断言和历史副作用断言。

```bash
python -m pytest -q tests/func/test_unprotect.py tests/func/test_checkout.py::test_checkout_relink tests/func/test_checkout.py::test_checkout_relink_protected
```

**C7 — 建议，未执行：可选本地构建。** 不应在未确认依赖可用时盲目重建环境。

```bash
python setup.py build_py
```

README 的安装说明在 `base/README.rst:88–153`；历史 CI 安装 `.[all,tests]`，运行入口包装器默认 4 workers、覆盖率和超时插件（`base/scripts/ci/install.sh:11`；`base/tests/__main__.py:14–19`）。本题建议直接使用上述单进程窄 pytest 命令，无须全量云服务测试或发布构建。所有成功/失败现象均为静态预计，尚无实跑记录。

## 5. 阅读范围与限制

实际完整或分段打开：

- 公开元信息：`user_prompt.txt:1–36`、`public_bundle.json:1`、`environment_brief.md:1–24`；另读协调者给定的公开阅读角色卡。
- 主要实现：`base/dvc/utils/fs.py:1–211`；`base/dvc/remote/local.py:1–190,195–230,380–490` 及检索上下文 `529–538`；`base/dvc/remote/base.py:1–180,730–805`；`base/dvc/system.py:1–216`；`base/dvc/compat.py:1–42`。
- 调用者：`base/dvc/command/unprotect.py:1–39`；`base/dvc/repo/__init__.py:145–170`；`base/dvc/output/base.py:320–355`；`base/dvc/stage.py:350–400`；`base/dvc/repo/destroy.py:1–15`。
- 测试及 fixture：`base/tests/unit/remote/test_local.py:1–88`；`base/tests/unit/utils/test_fs.py:1–262`；`base/tests/func/test_unprotect.py:1–34`；`base/tests/func/test_remove.py:1–98`；`base/tests/func/test_checkout.py:475–540`；`base/tests/func/test_add.py:612–660`；`base/tests/func/test_run.py:335–415`；`base/tests/func/test_repo.py:1–73`；`base/tests/func/test_utils.py:1–44`；`base/tests/func/test_system.py:1–17`；`base/tests/conftest.py:1–66`；`base/tests/basic_env.py:1–208`；`base/tests/dir_helpers.py:1–296`；`base/tests/__main__.py:1–20`。
- 安装/环境线索：`base/README.rst:1–230`；`base/CONTRIBUTING.md:1`；`base/setup.py:1–177`；`base/setup.cfg:1–2`；`base/pyproject.toml:1–17`；`base/.travis.yml:1–161`；`base/scripts/ci/install.sh:1–22`；`base/scripts/ci/script.sh:1–11`；`base/tests/utils/httpd.py:1–50`；`base/dvc/remote/ssh/connection.py:1–65`。
- 另对上述 base 中的 tests、dvc/utils、dvc/repo、dvc/output、dvc/command 和配置文件做文件名/关键词检索；其它命中文件只看到了检索返回行，没有逐个完整审查。

未查：其它题、角色卡父目录调查、私有评分/gold/旧结论、真实镜像、实际 actor shell、依赖版本清单、隐藏验收、官方文件恢复列表、完整仓库测试、公开祖先历史、任何外部链接或未来代码。没有误读私有材料的记录。

`user_prompt.txt` 是静态渲染，base 是无 .git 的源码导出而非完整运行容器（`environment_brief.md:3–6`）。因此本报告没有验证实际模型消息、真实工具配置、网络能力、运行资源、依赖可用性或开发条件。核心剩余未知是旧 symlink 断言与当前操作/验收条件如何协调，以及实际 actor 环境能否执行上述最小导入、权限复现和窄测试；均需后续验证。

