# 公开读者记录：datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb

- 角色与日期：R2E 公开读者（单题、干净上下文），按 `roles/public_reader_r2e.md` 执行，2026-09-29。
- 引用约定：文件路径都相对于本题公开包根目录（如 `user_prompt.txt`、`worktree/datalad/support/network.py`），行号取自公开包里的文件。
- 性质：静态阅读。没有运行项目代码，也没有开容器。§4 与 `commands.json` 里的命令都是"建议，未执行"。唯一执行过的是在本机 Python 3.12.13 上用标准库 `urllib.parse` 做的两次检查，没有导入项目代码，见 §5。
- 同目录 `commands.json` 共 5 条命令。

## 0. 摘要

- **题目要求**：`URL('weired_url:/')` 在 base 上得到 `scheme='file:implicit'`、`hostname=''`、`path='weired_url:/'`，应改为 `scheme='ssh:implicit'`、`hostname='weired_url'`、`path='/'`。
- **根因**：可从 base 源码静态读出。`URL._set_from_str` 先调用标准库 `urlparse`（`worktree/datalad/support/network.py:478`）。标准库只把由字母、数字和 `+-.` 组成的冒号前缀当作 scheme；`weired_url` 含 `_`，所以 scheme 为空，整串都进了 path。接着它落进 `network.py:491-499` 的分支（无 scheme、无 hostname、path 不含 `@`、不以 `//` 开头），被标成 `file:implicit`（`:499`）。公开测试里已经有这条被注释掉的用例，旁边的注释也指出了同一根因（`worktree/datalad/tests/test_network.py:203-206`）。
- **改动面**：预计只在 `network.py` 的 `_set_from_str`。`test_network.py` 钉住了很多应保留的旧行为（§1.2）。
- **关键未知**：
  - 题面只钉住一个输入。§1.3 的边界（纯数字路径、带 query 的下划线主机名、转义冒号等）应如何处理，公开材料判断不了。
  - 跑公开测试需要 nose、mock、GitPython（及 `git`）、patool。它们是否都装在 `.venv` 里，`environment_brief.md` 没写。
  - 公开测试 `test_get_local_file_url_linux` 预计在 base 上就会失败，原因是 Python 3.7 的 `quote` 行为变化，与本题无关（§3.4）。

## 1. 需求表

### 1.1 要改变的行为

| 编号 | 行为 | 类别 | 依据 |
|---|---|---|---|
| C1 | `URL('weired_url:/')` 的 `scheme == 'ssh:implicit'`、`hostname == 'weired_url'`、`path == '/'` | 明示 | `user_prompt.txt:10-22` |
| C2 | 同一输入的其余字段（`username`、`password`、`port`、`query`、`fragment`）保持空串，即 `URL('weired_url:/') == URL(scheme='ssh:implicit', hostname='weired_url', path='/')` | 可推知 | 被注释掉的用例走 `_check_url` 助手（`test_network.py:206`、`:112-121`），它比较完整的 `_fields`（`network.py:537-540`）；题面只打印了三个字段 |
| C3 | 字符串往返：`str(URL(scheme='ssh:implicit', hostname='weired_url', path='/')) == 'weired_url:/'`；修复后解析该输入也不应触发 `network.py:529-531` 的"往返不一致"警告 | 可推知；base 已满足 | `_check_url` 的 `test_network.py:117`；按 `__str_ssh__`（`network.py:345-355`）静态推算，base 上已得到 `'weired_url:/'`，修复不能破坏这一点 |
| C4 | 推广到同类输入：主机名含 `urlparse` 不接受为 scheme 的字符（如 `_`），写成 `host:path` 形式，比如相对路径 `weired_url:path` | 可推知 | 题面泛称 "hostname followed by a colon and a path"（`user_prompt.txt:7`），但只给了一个例子；类文档把 ssh 的隐式形式写作 `"host:path"`（`network.py:281-283`） |
| C5 | 连带效果：`is_url('weired_url:/')` 由 False 变为 True | 可推知，C1 成立后自动成立 | `is_url` 只看 scheme 是否为 `ssh:implicit`（`network.py:613-624`）。题面说的 "downstream operations" 没有点名；调用方见 `worktree/datalad/distribution/install.py:122,292,309,321` |

### 1.2 应保留的旧行为

| 编号 | 行为 | 类别 | 依据 |
|---|---|---|---|
| K1 | 已能正确解析的 ssh 形式保持不变：`host:path/sp1`、`host:path`、`host:/path`、`user@host:path/sp1`、`git@host:user/proj`、`weired:/`，以及 `repr(URL("host:path"))` 的精确文本 | 明示（公开测试） | `test_network.py:153-161,199-203` |
| K2 | 不含冒号的相对/绝对路径仍为 `file:implicit`（`f`、`f/s1`、`/f`、`/f/s1`）；`URL('smth').hostname == ''` | 明示 | `test_network.py:193-196,139-141` |
| K3 | `is_url` 的否定例保持不变：`relative`、`/absolute`、`like@sshlogin`、`''`、`' '` 都不是 URL；`weired://` 仍算 URL | 明示 | `test_network.py:262-274`。注意 `like@sshlogin` 在 base 上得到 False 的方式：构造时 `__str_ssh__` 的 `assert`（`network.py:349`）抛出 `AssertionError`，再被 `is_url` 的裸 `except` 吞掉（`network.py:618-621`）。重写 `@` 分支时容易无意中改掉这一点 |
| K4 | `weired://` 仍记录 "Parsed version of url ... differs" 警告，且 `str()` 返回原串 | 明示 | `test_network.py:215-223`，依赖 `network.py:524-531` |
| K5 | 带显式 scheme 的 URL 不受影响：`http(s)://`、`ssh://`、`git://`、`file://`（含 `file:///c:/path/sp1`）、`hg+https://`、`dl+archive:KEY...`，以及 `parse_url_opts` 的 http/s3 例子；`///` 与 `//a/` 仍为 `datalad:implicit` | 明示 | `test_network.py:85-96,146-190`。`dl+archive` 另被 `worktree/datalad/customremotes/archives.py:88,97` 使用 |
| K6 | `_split_colon` 的行为不变，包括 `a\:b` 中的转义冒号不作为分隔符 | 明示 | `test_network.py:99-104` |
| K7 | 冒号前已有 `/` 的本地路径（如 `/some/dir:x`、`rel_dir/sub:x`）仍为 `file:implicit` | 可推知；公开测试未覆盖 | 主机名不会含 `/`：hostname 会拼进 netloc（`network.py:441-460`），含 `/` 会让往返串失真。这也与 git 的 scp 式地址约定一致（外部常识，不是仓库证据） |
| K8 | 爬虫模板串（名字带 `_`，query 里有含冒号的值，如 `openfmri_s3?_url=s3://b/k`）经 `parse_url_opts` 仍解析为 `file:implicit` 的 path 加 query，不抛错 | 可推知；公开测试未覆盖 | `worktree/datalad/crawler/pipeline.py:453-470` 的文档写明模板可以带 URL 式 query，`:485-487` 把模板交给 `parse_url_opts`。`openfmri_s3` 是真实存在的管线模块（`worktree/datalad/crawler/pipelines/openfmri_s3.py`）。base 上 `urlparse` 先把 `?` 后面切成 query，path 只剩 `openfmri_s3` |

### 1.3 仍有多种合理解释的输入（题面未约定）

| 编号 | 输入 | base 上的结果（静态推断） | 歧义所在 |
|---|---|---|---|
| A1 | 纯数字路径 `host1:22` | 推断为 `file:implicit`。Python 3.7.x 的 `urlsplit` 把"冒号后全是数字"视为端口号，因而不识别 scheme；3.9 起去掉了这条判断。本机 3.12 的行为不同，这一项未在 3.7.9 上验证 | 形式上同样是 `host:path`，但题面只讲下划线的例子。修与不修都说得通 |
| A2 | 下划线主机名加 query/fragment，如 `weired_url:/p?x=1` | `file:implicit`，path 为 `weired_url:/p`，query 为 `x=1` | 若让它进入 `network.py:505-511` 分支，会抛 `ValueError`（代码注释承认这是个 TODO）；而普通主机名 `weired:/p?x=1` 在 base 上是 `ssh:implicit` 且保留 query。抛错、按 ssh 保留 query、维持 file，三种结果都有依据 |
| A3 | 含转义冒号的 `a\:b` | `file:implicit` | 仓库把 `\:` 视为非分隔符（K6）。如果修复只看"path 里有冒号"就归为 ssh，`_split_colon` 切不开，hostname 为空，构造时 `__str_ssh__` 的 `assert` 会抛 `AssertionError`。按仓库自己的约定应保持 file，但公开测试没有这个例子 |
| A4 | 大写 `Weired_URL:/` | `file:implicit` | `urlparse` 会把 scheme 转成小写（所以 base 上 `Host:/p` 得到 `hostname='host'`）；新逻辑若从原串切分，会保留大小写。题面例子全是小写，没有约定 |

### 1.4 `public_hints` 的三类内容（`public_bundle.json:15`）

- **题目需求**：找到根因，修改非测试源文件来修复问题。
- **给解题者的操作指令**：不要改仓库测试文件；测试要窄跑，在 `/testbed` 用 `python -m pytest`；确认完成后简短总结，停止调用工具。
- **环境事实声明**：`/testbed/.venv` 是项目环境，`python` 和测试工具已指向它；无网络；`pip` 可能不可用；修复由另一组测试评判。

对合法解法的影响：

- 修复只需标准库（`re` 已在 `network.py:14` 导入），不需要装包，也不需要联网。
- "不改测试文件"意味着不能靠取消注释 `test_network.py:206` 来验证。但可以用 `python -c` 直接调用同一个 `_check_url` 助手（§4 的 `repro_check_url_helper`），开发不受影响。
- 仓库自己的测试运行器是 nose（`worktree/CONTRIBUTING.md:175,181`、`worktree/tox.ini:9`），提示要求用 pytest。`test_network.py:67-73` 的 yield 式测试在 pytest 下不会真正执行，与本题无关。

## 2. 合理实现范围

- **修改位置**：`URL._set_from_str`（`network.py:477-531`）是唯一给无 scheme 字符串分配 `file:implicit` 的地方（`:499`），改这里最直接。也可以在调用 `urlparse` 之前先做一次 scp 式预判。两种位置都合理，前提是 §1.2 的保留项不变。
- **判定方式**：只要 C1-C3 成立、K1-K8 不变，以下做法都应被接受：
  - 在"无 scheme、无 hostname"分支里，如果 path 中有一个未转义的冒号，且冒号前没有 `/`，就标为 `ssh:implicit`，再复用现有的 `network.py:505-521` 分支完成切分（该分支已处理 `user@` 前缀和 query/fragment 报错）；
  - 用正则匹配主机名字符集（如字母、数字加 `._-`）后跟冒号；
  - 在新分支里直接设置 hostname 和 path。

  不同实现对 A1-A4 的处理会不同，题面没有约定。
- **需要避开的做法**（依据来自仓库，属于边界条件，不是在猜标准答案）：
  - 让新规则也作用于 `urlparse` 已识别出 scheme 的字符串。例如在 `urlparse` 之前用一条宽松正则截获所有 `xxx:yyy`，会改变 `weired://`（K4）、`dl+archive:`（K5）乃至 `http://` 的结果。
  - 在 query/fragment 还没切掉的原始整串上找冒号：`openfmri_s3?_url=s3://...` 这类模板会被误判为 ssh，并在 `network.py:506-511` 抛 `ValueError`（K8）。
  - 不按 `_split_colon` 的转义约定判断冒号（A3）。
- **命名和输出约定**：
  - scheme 字符串必须精确为 `'ssh:implicit'`。`is_url`（`network.py:624`）和 `_as_str` 按 `__str_<base>__` 的分派（`network.py:386-388`）都依赖这个值。
  - 字段缺省值用空串而不是 `None`（`network.py:315-321,473-475`）。
  - 不需要新增参数、选项或默认行为，`URL` 的构造签名不变。
- **不需要改的**：`is_url`；`__str_ssh__`（base 上已能正确往返，见 C3）；测试文件；同模块里 `get_local_file_url` 对 `~` 的编码（§3.4 那个失败与本题无关）。
- **没有发现其它替代方案**：题面没有给 hostname/path 的字面值留余地（例如 path 写成 `''` 或 `'//'`），C1 的三个值是硬约定。

## 3. 题面质量与初态线索

### 3.1 是否给出或强烈暗示修法

- 没有给出修法。示例代码是调用公开 API 的复现，不是修好后的实现。
- 题面写明"应得到 `ssh:implicit`、实际得到 `file:implicit`"，这等于指向 `network.py:499` 这个赋值点。它是定位线索，不是解法。
- 示例的输入和三个期望值，与仓库里被注释掉的测试 `test_network.py:206` 完全一致；同处的注释（`:204-205`）直接写出了根因（scheme 不允许某些字符）。这很可能暗示了隐藏测试要检查什么，但题面本身没有复制实现。

### 3.2 描述的行为能否从 base 源码读出

- 能。在 base 源码上静态走一遍：
  1. `urlparse('weired_url:/')` 得到空 scheme，path 为 `weired_url:/`。原因是 `_` 不在标准库的 `scheme_chars` 里：我在本机 3.12 标准库上核对过这个常量，它与 3.7 中的内容相同。
  2. scheme 为空，`network.py:483` 的分支不进入。
  3. 进入 `:491-499`：path 不含 `@`，也不以 `//` 开头，于是被标为 `file:implicit`。
  4. `:505` 的分支不进入。
  5. `_as_str()` 走 `__str_file__`，得到原串，不产生警告。

  结果是 `scheme='file:implicit'`、`hostname=''`、`path='weired_url:/'`，与题面的 "Actual Behavior" 一致。
- 两处措辞不准确，但不影响解题：
  - "leaving the hostname undefined"：实际值是空串 `''`，既不是 `None`，也不会抛 `AttributeError`（`network.py:315-321,475`）。
  - 标题里的 "Causes Parsing Failures" 和正文 "This mismatch causes assertions ... to fail"：base 上这个输入不抛任何异常，只是静默地给出错误的字段。"assertions" 最可能指测试断言。
- **描述的范围比实际缺陷宽**：题面说 "SSH implicit URLs that include a hostname followed by a colon and a path" 都会被误判，但 `host:/path`、`weired:/`、`user@host:path` 在 base 上已经解析正确，公开测试覆盖了这些情况（`test_network.py:154-158,203`）。真正出错的是一个窄类：主机名含 `urlparse` 不接受的字符，且没有 `user@` 前缀。`user@weired_url:/` 因为含 `@`，在 `:492-494` 已经走 ssh 分支。解题者如果按题面字面去"修所有 `host:path`"，可能会多改；跑一下 `weired:/` 就能看出差别。
- **"下游操作失败"没有点名**：从代码里能找到一个例子。`is_url` 对这个输入返回 False，于是 `install` 把它当本地路径处理（`install.py:292-299,309,321`）；`.gitmodules` 里这种形式的子模块 URL 会被当成相对路径拼接（`install.py:122-140`）。

### 3.3 示例在 base 接口下是否说得通

- 说得通：`from datalad.support.network import URL` 在 base 中存在（`network.py:265`）；`URL(url)` 接受字符串（`:309-325`）；`.scheme`、`.hostname`、`.path` 由 `network.py:591-592` 的 `exec` 绑定为只读属性。base 上示例的三行 `print` 预计依次输出 `file:implicit`、一个空行、`weired_url:/`。
- `weired` 的拼写沿用仓库测试里的写法，不是题面错误。

### 3.4 调查入口、初态与缺失信息

- **复现入口**：题面示例可以直接用 `python -c` 运行（§4 的 `repro_issue_example`）。更贴近仓库约定的方式是调用公开测试助手 `_check_url`（`repro_check_url_helper`）。
- **需要读的代码很少**：`network.py:477-531` 和 `:595-597`；相关公开测试在 `test_network.py:112-223,262-274`。
- **初态**：
  - `worktree_manifest.json:14-16` 显示，镜像初态相对 base 的 diff 为 0 字节。
  - 未跟踪文件只有两个：`run_tests.sh`（公开包收录）和 `install.sh`（公开包未收录），见 `worktree_manifest.json:20-32`。
  - `run_tests.sh:1` 运行的 `r2e_tests` 目录不在工作树中（属于隐藏测试），解题时不应依赖它。
- **与本题无关的既有失败**：`test_get_local_file_url_linux`（`test_network.py:277-281`）预计在 base 上就失败。`get_local_file_url('/a~')`（`network.py:629-645`）经 `urlquote` 得到 `file:///a~`，而测试期望 `file:///a%7E`。原因是从 Python 3.7 起，`urllib.parse.quote` 把 `~` 当作无需转义的字符；本机 3.12 上 `quote('/a~')` 返回 `'/a~'`，与此一致。这一项不属于题目需求。解题者跑公开测试时会看到这个失败，由于它和本题在同一模块，容易被误导去改 `get_local_file_url`。
- **真正会阻碍开发的缺失信息**：没有。仍不确定的是隐藏测试对 §1.3 边界的期望。这是题面覆盖范围的问题，不妨碍写出满足 C1 的修复。

## 4. 开发需求表

所有命令都在 `/testbed` 下以解题身份运行，状态一律为"建议，未执行"。为了不在仓库里留下文件：用 `python -B` 避免写 `.pyc`；pytest 加 `-p no:cacheprovider`，避免留下 `.pytest_cache`（`worktree/.gitignore:18` 只忽略 `*.pyc`）。

| 操作 / 资产 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 命令 id |
|---|---|---|---|---|
| 导入 `datalad.support.network` | 导入链需要 `six`、`requests`（`network.py:21-34`）和 `appdirs`（`worktree/datalad/config.py:17`）。`import datalad` 会实例化 `ConfigManager` 与 `SSHManager`（`worktree/datalad/__init__.py:19-26`），后者在 HOME 下创建用户配置目录（`worktree/datalad/support/sshconnector.py:128-135`）。`worktree/datalad/version.py:21-40` 在有 `.git` 时会运行 `git describe`，失败会被吞掉 | `.venv` 为 Python 3.7.9；agent 可写 home（`environment_brief.md:10-12`） | brief 没有列出已安装的包 | `import_env` |
| 复现题面示例 | `user_prompt.txt:10-19` | 同上 | 无 | `repro_issue_example` |
| 用仓库测试助手跑被注释掉的用例 | `test_network.py:112-121,206` | 提示称测试工具已指向 `.venv`（`public_bundle.json:15`）；brief 没有列出测试依赖 | `datalad.tests.utils` 需要 `mock`、`nose`、GitPython（`import git` 需要 `git` 可执行文件）和 `patool>=1.7`（`worktree/datalad/tests/utils.py:27,37-42,121-125`、`worktree/datalad/support/archives.py:15-18`）。关于 git，brief 只间接提到"HOME 无 git 身份"（`environment_brief.md:13`） | `repro_check_url_helper` |
| 边界观察 | §1.2 的 K7-K8，§1.3 的 A1-A4 | 同导入 | 无 | `edge_case_survey` |
| 相关公开测试 | `test_network.py` 整个文件 | `run_tests.sh:1` 用 `.venv/bin/python -m pytest` | pytest 版本未知；测试依赖同上 | `public_test_network` |
| 网络、git 身份、构建 | 本题的解析逻辑纯本地，不需要网络，不需要提交，也没有编译扩展 | brief 已说明无网络、无 git 身份 | 无 | 不需要 |

资源方面，按静态估计，brief 给的 2 CPU / 4 GiB / `/tmp` 1 GiB 足够运行上述命令。`test_url_fragments_and_query` 会通过 `with_tempfile` 在临时目录写一个小文件（`worktree/datalad/tests/utils.py:912-930`）。

命令明细（与 `commands.json` 一致；"预计"都是静态推断）：

1. `import_env`（应退出 0）：`python -B -c "import sys, six, requests, appdirs, datalad; from datalad.support.network import URL, is_url; print(sys.version.split()[0], datalad.__version__, datalad.__file__)"`。预计打印 `3.7.9`、一个版本号（`0.2.dev1` 或 `git describe` 的结果）和 `/testbed/datalad/__init__.py`。最后一项用来确认导入的是工作树里的包，这样改动才会生效。修复前后输出相同。
2. `repro_issue_example`（base 上应失败）：用公开 API 断言 C1-C3。
   - 修复前：先打印 `URL(path='weired_url:/', scheme='file:implicit') is_url=False`，再以 `AssertionError: ('file:implicit', '', 'weired_url:/')` 退出。
   - 修复后：打印 `URL(hostname='weired_url', path='/', scheme='ssh:implicit') is_url=True` 和 `OK`，退出码 0。
3. `repro_check_url_helper`（base 上应失败）：`python -B -W ignore -c "from datalad.tests.test_network import _check_url; _check_url('weired_url:/', scheme='ssh:implicit', hostname='weired_url', path='/'); print('OK')"`。
   - 修复前：预计 `AssertionError: URL(path='weired_url:/', scheme='file:implicit') != URL(hostname='weired_url', path='/', scheme='ssh:implicit')`。如果报的是 `ImportError` 或 `ModuleNotFoundError`，说明测试依赖缺失，不算复现。
   - 修复后：打印 `OK`。
4. `edge_case_survey`（只看输出）：一段 heredoc 脚本，逐行打印 12 个输入的 `repr(URL(s))` 和 `is_url(s)`。
   - base 上预计：`weired_url:/`、`weired_url:path`、`/some/dir:x`、`rel_dir/sub:x`、`a\:b`、`weired_url:/p?x=1`、`openfmri_s3?_url=s3://b/k` 都是 `file:implicit`；`user@weired_url:/` 和 `weired:/` 已经是 `ssh:implicit`；`like@sshlogin` 抛 `AssertionError`；`weired://` 得到 `URL(hostname='weired', scheme='ssh:implicit')`，stderr 上有 WARNING；`host1:22` 推断为 `file:implicit`（未验证）。
   - 合理修复后预计：前两项变为 `ssh:implicit`；带 `/` 的两项和模板串保持 file；A1-A3 的结果随实现而异。
5. `public_test_network`（只看输出）：`python -B -W ignore -m pytest -p no:cacheprovider -rA datalad/tests/test_network.py`。
   - 预计修复前后都是 16 passed、1 failed、1 xfailed。failed 是 `test_get_local_file_url_linux`（见 §3.4）；xfailed 是 yield 测试 `test_get_url_straight_filename`，pytest 4-7 会把它标为 xfail 并给出收集警告。
   - 这个文件不能区分修复前后，因为目标用例被注释掉了（`:206`），它只能用作回归检查。如果想要一个干净的回归闸门，可以再加 `--deselect datalad/tests/test_network.py::test_get_local_file_url_linux`，预计得到 16 passed、1 xfailed，退出码 0。

## 5. 阅读范围

实际打开的文件：

- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 的全文。
- `worktree_manifest.json`：只看了顶层键、`export`、`initial_diff`、`untracked_*`、`not_included`，以及文件表中含 `network` 的条目。没有打开它指向公开包以外的路径。
- 读了全文：`worktree/datalad/support/network.py`、`worktree/datalad/tests/test_network.py`、`worktree/run_tests.sh`、`worktree/datalad/__init__.py`、`worktree/datalad/support/__init__.py`、`worktree/datalad/tests/__init__.py`、`worktree/.gitignore`、`worktree/requirements.txt`、`worktree/tox.ini`。
- 读了片段：
  - `worktree/datalad/distribution/install.py`（100-140、280-335）
  - `worktree/datalad/customremotes/archives.py`（75-115）
  - `worktree/datalad/crawler/pipeline.py`（300-345、452-500）
  - `worktree/datalad/config.py`（导入部分与 75-175）
  - `worktree/datalad/support/sshconnector.py`（导入部分与 120-150）
  - `worktree/datalad/version.py`（1-40）
  - `worktree/datalad/log.py`（导入部分与 150-260 的日志初始化）
  - `worktree/datalad/cmd.py`、`worktree/datalad/utils.py`、`worktree/datalad/support/gitrepo.py`、`worktree/datalad/support/annexrepo.py`（导入部分）
  - `worktree/datalad/tests/utils.py`（导入部分、36-43、540-600、895-930，以及几个助手的定义位置）
  - `worktree/datalad/support/vcr_.py`、`worktree/datalad/support/archives.py`（导入部分）
  - `worktree/setup.py`（41-67）、`worktree/CONTRIBUTING.md`（170-182）
  - `worktree/README.md`（安装段落的 grep 结果）
- 目录列表：`worktree/cfgs/`、`worktree/datalad/crawler/pipelines/`。另外在整个工作树里 grep 了 `URL(`、`is_url(`、`parse_url_opts`、`ssh:implicit` 等调用点。
- 在本机 Python 3.12.13 上只用标准库做了检查，没有导入项目代码：
  - `urllib.parse.scheme_chars` 不含 `_`，`urlparse('weired_url:/')` 得到空 scheme、path 为整串；
  - `quote('/a~')` 返回 `'/a~'`。
  - 3.12 与解题环境的 3.7.9 在"冒号后纯数字"上的行为不同（A1），这一项未验证。

没有查的范围：其它测试文件（只 grep 过调用点）；`docs/` 源文件（只 grep 过）；`install.sh`（公开包未收录）；隐藏测试；`.git` 历史；上游的后续提交或 PR。没有做网络搜索。

需要保留的限制：`user_prompt.txt` 只是静态渲染，不是模型实际收到的消息；`worktree/` 不含 `.venv`、`.git` 和隐藏测试，不是完整的运行容器。本文没有验证模型实际收到的消息、运行资源、已安装的包或开发条件。文中所有"预计"都是静态推断，需要协调者在真实解题环境里按 `commands.json` 照跑核对。
