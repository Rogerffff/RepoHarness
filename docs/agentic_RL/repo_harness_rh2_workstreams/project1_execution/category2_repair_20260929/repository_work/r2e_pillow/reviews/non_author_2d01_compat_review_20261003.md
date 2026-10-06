# Pillow 2d01：公开 pytest8 兼容 helper 非作者窄核

2026-10-03。**未发现当前兼容方法的材料阻断；可进入已安排的真实 actor 开发验收。** 本次为静态、非作者、非 fresh 核查；没有执行 Pillow、pytest、兼容 helper、项目模块、SSH、容器、安装或下载，也没有新 reward。范围仅为 2d01 的公开兼容方法、命令嵌入一致性及必要公开测试加载条件，不重审私有题义或旧九方矩阵。

## 转换保留原断言和传播语义

独立读取冻结公开 `Tests/test_file_tiff.py`，确认只有 `TestFileTiff.test_closed_file`、`TestFileTiff.test_context_manager` 含目标 `pytest.warns(None)`。按照 helper 的文本转换在内存重建副本并做 AST 对照：仅新增 `import warnings`、替换两个 context manager、分别在其 body 首部插入 `warnings.simplefilter("always")`。将这三类变化逆向归一化后，整个模块 AST 与原文相等；105 个原 `assert` 的 AST 与顺序全部相等，两处 `assert not record` 保留，图像打开/加载/关闭和嵌套 Image context 顺序未变。

`warnings.catch_warnings(record=True)` 记录上下文中的警告，`simplefilter("always")` 将实际警告纳入 record，仍由原 `assert not record` 拒绝；没有 skip、删除断言或忽略真实警告。该 context manager 不抑制 body 的普通异常，helper 也没有捕获图像异常的分支。警告过滤设置随 context 退出恢复，不对后续测试永久设置 always。以上为标准库上下文及源码控制流的静态判断；作者的 Image 替身检查没有移作本次独立执行证据。

helper 的 AST 名称核对和文本次数检查可以拒绝当前目标位置/原文格式已变化的输入；并不构成对未来任意公开测试版本的自动认证。本次结论绑定下表原文摘要。

## 临时副本、conftest 与导入条件

- helper 要求实际运行时当前目录等于解析后的 testbed 根目录；临时 `.py` 写入同一 `Tests` 目录，在 NamedTemporaryFile context 关闭后才交 pytest。该目录有 `Tests/__init__.py`，原 `from .helper import ...` 保持相对包加载条件；测试中的 `Tests/images/...` 路径仍相对原工作树根目录。原模块没有按自身文件名定位图片的 `__file__` 依赖。
- 根 `conftest.py` 声明 `pytest_plugins = ["Tests.helper"]`；`Tests/conftest.py` 保留原 header/marker 设置；`setup.cfg` 的 pytest 配置仅含 `-ra --color=yes` 和 `testpaths = Tests`，没有改变导入方式或限定原 TIFF 文件名的配置。helper 没有禁用 conftest，只禁用 cacheprovider。额外两个原公开测试路径存在，未修改其内容；其中也没有遗漏的 `pytest.warns(None)`。
- `pytest.main` 显式选择兼容 TIFF 整文件、原 TIFF metadata 整文件和原 libtiff metadata 一个节点，返回其实际退出码；没有把结果改写为成功。finally 删除临时文件，并比较原 TIFF 文件前后字节；检测到原件变化会报错。原件只读，不回写。
- 公开命令用 testbed 根目录运行并设置 `PYTHONDONTWRITEBYTECODE=1`。可编辑 PIL 安装、`.venv`/C 扩展与 libtiff 的实际身份不由临时位置自动证明；单独 `env_import` 命令已列出所需观察项，真实 actor 仍须确认导入来自目标源码及扩展可加载。不能仅凭静态 package/conftest 条件宣称公开测试已经通过。

## 公开与私有隔离

[公开 helper](../public/tiff_pytest8_compat.py)只读取公开 TIFF 文件、创建公开测试的临时副本并选择公开测试路径；没有读取或写入隐藏测试、expected 映射、gold、私有候选或评分库存的路径。它是开发兼容工具，不能作为正式隐藏测试替换。

[公开命令](../public/2d01_commands.json)中的兼容 heredoc 与独立 helper **逐字相等**，没有另一个未核版本。该 public 目录可按准备入口单独交付；包含历史评分、gold 与私有结论的父目录仍不能整包进入 solver。当前正式材料保留的两个 FAILED 期望键不因开发副本通过而翻转，也不把该副本结果称为新增正式 reward。

## 审查绑定 SHA256

| 对象 | SHA256 |
| --- | --- |
| `public/tiff_pytest8_compat.py` | `048305930edc80eba33ad35a8e0217dd5edb8dd8fac08c90581f147cce6f1cc0` |
| `public/2d01_commands.json` | `01613892059efeb6dea715079191e7d616b5faa29247c761ab1f3667944198fe` |
| 冻结公开 `Tests/test_file_tiff.py` | `93f9c839a24777b6b29975be49af8e528dcd56dcef2069326ff258a856aae397` |
| 内存重建的兼容副本 | `b02fd092890b3c88f89f7d7ffb99155f23976e3aec3d9a9005e0285cd16d1b93` |
| 公开根 `conftest.py` | `6c3ca6f57f0a1bbf1ffe2aeec4d7669aec86ffdd329c8bcb6cbffc9d04ec47f7` |
| 公开 `Tests/conftest.py` | `e0c42459f78478160caf3412fc70b1641daf90c21ac9f326bdb372bb98fe8e8e` |
| 公开 `Tests/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 公开 `setup.cfg` | `029bacdcd1b3c5c10ba1353cce582005756f8828a94d499f048ee74ced7b5962` |

公开工作树来源：`runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/`。原文与副本摘要独立重算，与作者 `static_checks.json` 的兼容记录一致；helper/命令摘要为本次独立计算。

停止条件：当前方法静态窄核结束。下一步仅按 [2d01 当前准备](../2d01.md) 在真实 actor 下确认导入身份、base/正确解的公开兼容运行和原例行为；若文件身份变化、出现 conftest/导入异常或警告行为矛盾，再核对应差异。不新增评分修订、重跑全九方矩阵或据此放行探针/训练资格。

唯一新增文件为本审查记录，使用排他创建；未覆盖作者材料或并行文件。
