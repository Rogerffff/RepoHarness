# 公开读者审查：scrapy__9a15fcf89a151811de8ac783419df0512c863d5e

- 角色：R2E 公开读者（静态审查，不解题）；2026-09-25。
- 材料：只读了角色卡和本题公开包。没有运行项目代码，没有安装依赖，没有修改 `worktree/`，也没有联网。
- 路径约定：路径都相对 `PUBLIC_DIR`。`worktree/` 内的文件省略这个前缀，例如 `scrapy/responsetypes.py` 指 `worktree/scrapy/responsetypes.py`。
- 性质：凡是说“base 下会怎样”，都是读代码得出的静态推断，没有在容器里执行。命令一律是“建议，未执行”。

## 0. 概括

题面要求 `responsetypes.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8')` 返回 `TextResponse`，而不是 `Response`。从 base 源码可以读出问题确实存在：映射表里没有 `application/x-json`，也没有 `application/*` 兜底。表里已经有同类条目 `application/json`，所以定位和修改都很直接。

主要风险不在题意，而在 Python 3.9 环境。这版 scrapy 仍以 Python 2.7 为主，`tests/test_responsetypes.py` 在 py3 下被列入忽略清单。经 `Headers` 走的判型路径在 py3 下拿到的是 bytes 头值，base 上就会抛 `TypeError`。

## 1. 需求表

| 编号 | 行为 | 明确程度 | 依据 |
|---|---|---|---|
| R1 | `responsetypes.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8')` 返回 `scrapy.http.TextResponse` 类本身；base 返回的是 `Response` | 明示 | `user_prompt.txt:10-14`；base 行为见 `scrapy/responsetypes.py:51-57`、`:41-49` |
| R2 | 只要 MIME 主体是 `application/x-json`，无论 content-type 参数是 `encoding=`、`charset=`，也无论有没有空格或大小写差异，都得到 `TextResponse` | 明示，并可从代码推知。明示：`user_prompt.txt:18` 写的是 “Responses with the MIME type `application/x-json` …”。推知：`scrapy/responsetypes.py:56` 用 `split(';')[0].strip().lower()` 丢弃参数，并把大小写归一 | 同左 |
| R3 | 其它入口对 `application/x-json` 也应给出相同结果：`from_mimetype('application/x-json')`、`from_headers`、`from_args(headers=...)` | 可合理推知。这些入口最终都走 `from_mimetype`（`scrapy/responsetypes.py:57`、`:72-73`、`:105`）。但题面只示例了 `from_content_type`，而且 py3 下 header 路径另有 bytes 问题（见 A2） | `scrapy/responsetypes.py:41-49, 67-76, 101-112` |
| K1 | 保留已有映射：`text/html`、`application/xhtml+xml`、`application/vnd.wap.xhtml+xml` → `HtmlResponse`；`text/xml`、`application/xml`、`application/{atom,rdf,rss}+xml` → `XmlResponse`；`application/json`、`application/javascript`、`application/x-javascript`、`text/*` → `TextResponse`；`application/octet-stream` 等未登记的 `application/*` → `Response` | 公开测试 + 现有代码 | `tests/test_responsetypes.py:30-41`，其中 `:37` 是 octet-stream → `Response`；`scrapy/responsetypes.py:18-31, 48-49` |
| K2 | 只要给了 `content_encoding`（来自 `Content-Encoding` 头，例如 gzip），就一律返回 `Response`；x-json 也不例外 | 现有代码 + 公开测试 | `scrapy/responsetypes.py:54-55`；`tests/test_responsetypes.py:58` |
| K3 | `from_filename`、`from_content_disposition`、`from_body` 以及自带 `mime.types` 的加载保持不变 | 公开测试 | `tests/test_responsetypes.py:8-28, 43-52, 79-81` |
| K4 | 返回值必须是与 `scrapy.http.TextResponse` 相同的类对象。公开测试一律用 `is` 比较 | 公开测试写法 + 题面措辞 | `tests/test_responsetypes.py:19, 28, 41, 52, 63, 77`；`scrapy/http/__init__.py:17` 再导出该类；表中的类路径经 `load_object` 解析（`scrapy/responsetypes.py:38-39`、`scrapy/utils/misc.py:31-51`） |
| A1 | 其它 JSON 变体（如 `application/ld+json`、`application/vnd.api+json`）是否也应改为 `TextResponse` | 有多种合理解释。题面只点名 `application/x-json`。`text/json`、`text/x-json` 在 base 上已经经 `text/*` 得到 `TextResponse` | `user_prompt.txt`；`scrapy/responsetypes.py:30, 48-49` |
| A2 | Python 3 下 `from_content_type`、`from_headers` 是否应接受 bytes 头值 | 题面完全没提。base 的 py3 header 路径本来就不能用（见 3.2）。公开材料无法判断隐藏测试是否覆盖它 | `scrapy/http/headers.py:13-36`；`scrapy/responsetypes.py:56, 61, 72-73`；`tests/py3-ignores.txt:40` |

## 2. 合理实现范围

以下实现都满足 R1-R2，并能保持 K1-K4，应当接受：

- **在 `ResponseTypes.CLASSES` 登记 `application/x-json`**（`scrapy/responsetypes.py:18-31`）。`from_mimetype`、`from_content_type`、`from_headers` 和 `from_args` 都会因此改变结果。
- **在 `from_mimetype` 里按规则识别 JSON 族**，例如子类型是 `json`、`x-json`，或以 `+json` 结尾。不能把整个 `application/*` 兜底成 `TextResponse`，否则会破坏 K1 中 `application/octet-stream` → `Response` 的公开断言（`tests/test_responsetypes.py:37`）。
- **查表前先做别名归一**，例如把 `application/x-json` 视为 `application/json`。

**只在 `from_content_type` 里特判**能满足题面示例，但 `from_mimetype('application/x-json')` 仍会返回 `Response`。这与题面“MIME 类型为 x-json 的响应都应是 TextResponse”的一般表述不完全一致。如果隐藏测试走其它入口，这种写法可能不被接受；公开材料无法确认。

以下做法与明示要求或公开测试冲突：

- **新建 `TextResponse` 的子类（如 `JsonResponse`）并返回它。** 题面写明期望 `scrapy.http.TextResponse`（`user_prompt.txt:13, 18`），公开测试又用 `is` 比较，子类通不过这种断言。
- **只改 `scrapy/mime.types`。** 这份文件只被 `from_filename` 用来按扩展名猜类型（`scrapy/responsetypes.py:35-37, 78-84`），不影响 `from_content_type`，单独修改修不好题面示例。
- **绕过 `content_encoding` 检查。** 这会违反 K2。

题目没有约定新的公开名称、参数或默认值，输出就是类对象。题面也没有要求修改文档或 `docs/news.rst`。

超出题面的改动包括 A2 的 bytes 兼容和 A1 的 JSON 族扩展。题面既没要求，也没禁止。bytes 兼容会改变 py3 下 `test_from_headers`、`test_from_args` 这类用例的结果（见 4）。如果评分逐条比对用例的期望状态，这类额外改动可能影响得分。评分规则和隐藏测试都不在公开材料中，只能列为未知。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或强烈暗示修法

- 题面没有给出实现代码。示例（`user_prompt.txt:10-15`）只包含调用和期望输出，不是修好后的实现。
- 但题面精确给出了“输入字符串 → 期望类”，而 base 映射表里已有同类条目 `'application/json': 'scrapy.http.TextResponse'`（`scrapy/responsetypes.py:26`）。这等于强烈暗示了修法：按现有表结构补上对应类型。作为训练题，这道题难度很低，定位几乎不需要推理。
- 示例字符串 `application/x-json; encoding=UTF8;charset=UTF-8` 很具体：带非标准参数 `encoding=UTF8`，`;` 后也没有空格。它可能是从测试用例原样搬来的；这是推断，没有证据。

### 3.2 题面描述的行为能否从 base 源码读出

- **能读出。** `from_content_type`（`scrapy/responsetypes.py:51-57`）先取 `split(';')[0].strip().lower()`，得到 `application/x-json`。`from_mimetype`（`:41-49`）在 `self.classes` 中查不到这个键，兜底键 `application/*` 也不存在，于是返回 `Response`。
- **类名写法一致。** 题面的 `Actual: scrapy.http.response.Response`（`user_prompt.txt:14`）与类所在模块一致（`scrapy/http/response/__init__.py:16`）。`Expected: scrapy.http.TextResponse` 用的是公开别名，真实 repr 会是 `scrapy.http.response.text.TextResponse`（`scrapy/http/response/text.py:17`），不会误导读者。
- **下游后果写得笼统。** 题面说 “downstream processing” 或 “JSON handling” 会出问题（`user_prompt.txt:7, 21`），但没有给具体报错。从代码可以补出一个具体后果：`Response` 没有 `encoding`、`body_as_unicode()`、`selector`、`xpath`、`css`（`scrapy/http/response/text.py:51-67, 101-112`），依赖这些成员的下游代码会抛 `AttributeError`。
- **题面的动机场景在本环境的 base 上走不到映射表。**
  - 真实下载和缓存会用 `Headers` 调 `from_args(headers=...)`，例如 `scrapy/core/downloader/handlers/http11.py:264`、`scrapy/core/downloader/webclient.py:129`、`scrapy/extensions/httpcache.py:187`。
  - `Headers` 在 py3 下会把键和值规范成 bytes（`scrapy/http/headers.py:13-36`）。`from_content_type` 随后对 bytes 调 `.split(';')`（`scrapy/responsetypes.py:56`），会抛 `TypeError: a bytes-like object is required, not 'str'`。
  - `http11.py:269` 还使用 `zope.interface` 的 `implements(...)` 类建议写法，这种写法在 py3 下不可用；该文件也列在 `tests/py3-ignores.txt:82`。
  - 题面给出的直接示例是传 str 调 `from_content_type`，这条路径可以复现。

### 3.3 题面示例在 base 接口下是否说得通

- **能说通。** `from_content_type(content_type, content_encoding=None)` 接受 str，示例也没有传 `content_encoding`。参数里的 `encoding=UTF8` 不是 `content_encoding` 形参；后者对应 `Content-Encoding` 头。代码也不会解析 `encoding=UTF8`。
- **示例省略了导入，存在小歧义。** `responsetypes` 既是模块名，也是模块内单例名（`scrapy/responsetypes.py:114`）。正确写法是 `from scrapy.responsetypes import responsetypes`（`tests/test_responsetypes.py:2`）。如果写成 `from scrapy import responsetypes`，拿到的是模块，调用 `from_content_type` 会抛 `AttributeError`。读一眼公开测试就能消除这个歧义。
- **有一个措辞小问题。** 题面把整串 `application/x-json; encoding=UTF8;charset=UTF-8` 称为 “MIME type”。严格说，MIME 类型只是 `application/x-json`，其余是参数。这不影响理解。
- **提交号一致。** 题面中的 `commit 3fc4e0b319fc`（`user_prompt.txt:1`）与 `public_bundle.json:9` 的 `base_commit` 一致。

### 3.4 `public_hints` 的三类内容（`public_bundle.json:15`）

- **题目需求。**
  - “fixing a real GitHub issue” 对 R2E 并不准确，因为题面是自动生成的；但这不改变要做的事。
  - “find the root cause, and edit NON-TEST source files” 与本题一致，修改点在 `scrapy/responsetypes.py`。
- **给解题者的操作指令。** 包括 “Do NOT modify test files”、“keep runs narrow (a single test file or module)”、“reply with a short summary and stop calling tools”。
- **环境事实声明。**
  - “checked out at /testbed (your bash tool already runs there)” 与 `environment_brief.md:10` 一致。
  - “pre-activated conda env named `testbed`: `python`, `pip` … point at it” 与 `environment_brief.md:10-11` 不符。实际 `python` 是 `/testbed/.venv/bin/python`（3.9.21），没有 pip、pip3 或 uv，也不能出网。对合法解法影响很小：修复不需要新依赖；照提示执行 `conda activate` 或 `pip install` 会失败，退回直接使用 `python` 即可。
  - “grading resets the test files … test edits never count” 按角色卡说明不是本来源的实际机制。公开的 `run_tests.sh:1` 显示，评分命令跑的是不在工作树中的 `r2e_tests`。因此修改 `tests/` 本来就进不了评分运行，这条提示对解法没有实质影响。

### 3.5 初态线索

- **没有镜像初态改动。** `worktree_manifest.json` 中 `initial_diff.bytes = 0`。工作树由 base 的 506 个跟踪文件和未跟踪的 `run_tests.sh` 组成，共 507 个文件，与清单一致。镜像里还有 `install.sh`，但它没有随工作树提供（`untracked_missing`），所以公开材料看不到环境是怎么安装的。
- **仓库以 Python 2.7 为主，环境却是 Python 3.9.21。**
  - `setup.py:33-34` 只声明 Python 2 和 2.7，`tox.ini:7` 也写着 `envlist = py27`。
  - py3 移植尚未完成。`conftest.py:25-29` 在 py3 下把 `tests/py3-ignores.txt` 中的文件加入 `collect_ignore`，其中包括本题相关的 `tests/test_responsetypes.py`（`:40`）。
  - import 链有版本约束：`scrapy/item.py:8` 的 `from collections import MutableMapping` 在 3.9 仍可用，但从 3.10 起不可用；`scrapy/selector/csstranslator.py:2` 依赖 cssselect 的私有名 `_unicode_safe_getattr`，需要安装提供该名称的旧版 cssselect。
  - 公开材料没有列出这些依赖的实际版本。
- **解题者能看到 `run_tests.sh`。** 从中可知官方测试目录名是 `r2e_tests`，也能看到 warning 过滤方式。但这个目录不存在，直接运行 `run_tests.sh` 得不到验证信号。
- **`.venv` 与 `.gitignore` 的说法不一致，属于小问题。** `environment_brief.md:6` 把 `.venv` 归为“被 `.gitignore` 忽略”的产物，但根 `.gitignore` 只有 `venv`（`.gitignore:9`），不匹配 `.venv`。容器里的 `git status` 会不会把 `.venv/` 列为未跟踪，还取决于镜像中的其它忽略配置，公开材料无法确认。这只会给查看 diff 增加噪声，不影响题意。

### 3.6 调查入口与缺失信息

- **调查入口清楚。** 题面点名 `from_content_type`。执行 `grep -rn from_content_type` 就会找到 `scrapy/responsetypes.py:51`。映射表、兜底逻辑和表驱动的公开测试（`tests/test_responsetypes.py:30-41`）都集中在两个文件里。只有想确认影响面时，才需要读调用者；调用者列表见第 5 节。
- **会真正影响开发的缺失信息：**
  1. 隐藏测试覆盖哪些入口和输入类型：只测 str 版 `from_content_type`，还是也走 `Headers` 的 bytes 路径，或覆盖其它 JSON 变体。
  2. `.venv` 中的依赖是否齐全，`import scrapy` 能否成功。环境没有 pip，也不能出网，缺依赖时无法补装。
- 除此之外，只需正常阅读代码。

## 4. 开发需求表

下表中的命令都在后面的代码块里给出，全部是“建议，未执行”；“预计现象”都是静态推断。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令与预计现象 |
|---|---|---|---|---|
| 解释器与工作目录 | `run_tests.sh:1` 使用 `.venv/bin/python`；`public_bundle.json:18` 指定 `workdir` | `python` → `/testbed/.venv/bin/python` 3.9.21（`:10`） | 无 | C1 → `Python 3.9.21` |
| 导入 scrapy 及其第三方依赖（Twisted、six、w3lib、lxml、cssselect 等） | `requirements.txt:1-7`、`setup.py:39-47`；import 链见 `scrapy/__init__.py:42-51`、`scrapy/responsetypes.py:12-14` | 只说明解释器，不列已装包；没有 pip，不能出网（`:11`） | 不知道依赖是否齐全、版本是否兼容（见 `scrapy/item.py:8`、`scrapy/selector/csstranslator.py:2`）；没有 `install.sh`；也不知道 `.venv` 里是否另装了一份 scrapy | C2 → 预计打印 `1.1.0dev1` 和 `/testbed/scrapy/...` 路径。若出现 `ImportError`，说明环境缺依赖，且无法自行补装 |
| 复现原 bug，并直接核对保留行为（不经过 pytest） | `user_prompt.txt:10-15`；`scrapy/responsetypes.py:41-57` | 同上 | 无额外缺口 | C3 → 详见代码块后的说明 |
| 公开测试回归 | `tests/test_responsetypes.py`、`pytest.ini`、`conftest.py` | brief 没有直接说明 pytest 已安装，但可以从 `run_tests.sh:1` 推知 | pytest 和 pytest-twisted 的版本未知。缺 pytest-twisted 时，`pytest.ini:6` 的 `twisted = 1` 可能只会触发未知配置项警告。公开文件里没有 x-json 用例，只能用来看回归，看不到失败转通过 | C4 → 收集 7 个用例。base 下 `test_from_headers`、`test_from_args` 会因为 bytes 头值在 `scrapy/responsetypes.py:56` 抛 `TypeError`，其余 5 个通过。只补映射的修复不会改变这组结果 |
| 官方评分命令 | `run_tests.sh:1`；清单注明它是评分面原文 | — | `r2e_tests` 是隐藏测试，不在工作树中 | C5 → pytest 会报找不到 `r2e_tests`。这不是验证信号 |
| 构建与安装 | 纯 Python 改动。`scrapy/VERSION` 和 `scrapy/mime.types` 由 `pkgutil.get_data` 读取（`scrapy/__init__.py:10`、`scrapy/responsetypes.py:36`），两份文件都在工作树中 | 不需要编译 | 无 | 不需要命令 |
| 网络和外部服务 | 本题不需要 | 不能出网 | 无 | — |
| 资源 | `pytest.ini:2` 的 `usefixtures = chdir` 会为每个用例在 `/tmp` 下建立 tmpdir | 2 CPU、4 GiB 内存，`/tmp` 1 GiB（`:12`） | 无 | 静态判断：跑单个测试文件足够 |

```bash
# C1（建议，未执行）
cd /testbed && python --version

# C2（建议，未执行）：确认导入的是工作树里的 scrapy
cd /testbed && python -c "import scrapy, scrapy.responsetypes as m; print(scrapy.__version__, scrapy.__file__, m.__file__)"

# C3（建议，未执行）：复现题面示例，并核对保留行为
cd /testbed && python - <<'EOF'
from scrapy.responsetypes import responsetypes as r
for ct in ['application/x-json; encoding=UTF8;charset=UTF-8',
           'Application/X-JSON',
           'application/json',
           'application/octet-stream',
           'text/html; charset=UTF-8']:
    print(repr(ct), '->', r.from_content_type(ct))
print('x-json + gzip ->', r.from_content_type('application/x-json', 'gzip'))
print('from_mimetype ->', r.from_mimetype('application/x-json'))
EOF

# C4（建议，未执行）：必须从 /testbed 启动，并显式给出文件路径
cd /testbed && python -m pytest -rA tests/test_responsetypes.py

# C5（建议，未执行）：只用来确认它不是验证信号
cd /testbed && bash run_tests.sh
```

C3 的预计现象：

- **base：**
  - 两行 x-json 都返回 `<class 'scrapy.http.response.Response'>`。
  - `application/json` 返回 `TextResponse`。
  - `application/octet-stream` 返回 `Response`。
  - `text/html` 返回 `HtmlResponse`。
  - gzip 行返回 `Response`。
  - `from_mimetype` 行返回 `Response`。
- **修复后：**
  - 两行 x-json 变为 `<class 'scrapy.http.response.text.TextResponse'>`；大写那一行也会变，因为第 56 行会先转成小写。
  - 其余几行不变。
  - `from_mimetype` 行是否也变为 `TextResponse`，取决于修改放在哪一层（见第 2 节）。

C4 的注意事项：

- 必须从 `/testbed` 启动。`conftest.py:26` 以相对路径读取 `tests/py3-ignores.txt`。
- 必须显式给出文件路径。`python -m pytest tests` 在 py3 下会因 `collect_ignore` 跳过这个文件。
- 显式路径不受 `collect_ignore` 影响；这是 pytest 的一般行为，未在本环境验证。
- 这个文件中的类继承 `unittest.TestCase`。`pytest.ini:4` 的 `python_classes=` 为空，不影响它被收集。

## 5. 阅读范围

实际打开的内容：

- **角色卡：** `roles/public_reader_r2e.md`。没有打开它链接的 SWE-Gym 版角色卡。
- **全文读取：** `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- **`worktree_manifest.json`：** 只用脚本读取顶层键、`export`、`initial_diff`、`untracked_*`，以及 `files` 的前 5 项。
- **未打开的外部路径：** 清单中的 `initial_diff.source`，以及 `public_bundle.json` 的 `source`。两者都指向 `PUBLIC_DIR` 以外。
- **`worktree/` 中全文读取的文件：**
  - 核心代码与测试：`scrapy/responsetypes.py`、`tests/test_responsetypes.py`、`tests/py3-ignores.txt`、`tests/requirements.txt`、`tests/__init__.py`。
  - 测试与运行配置：`conftest.py`、`pytest.ini`、`run_tests.sh`。
  - 安装与项目元数据：`requirements.txt`、`setup.py`、`setup.cfg`、`tox.ini`、`INSTALL`、`.bumpversion.cfg`、`.gitignore`、`CONTRIBUTING.md`、`NEWS`、`scrapy/VERSION`。
  - scrapy 模块：`scrapy/__init__.py`、`scrapy/_monkeypatches.py`、`scrapy/http/__init__.py`、`scrapy/http/headers.py`、`scrapy/mime.types`。
- **`worktree/` 中部分读取的文件：**
  - `scrapy/http/response/__init__.py`：约 1-80 行。
  - `scrapy/http/response/text.py`：1-112 行。
  - `scrapy/utils/datatypes.py`：开头和 `CaselessDict`。
  - `scrapy/utils/python.py`：开头和 `isbinarytext`。
  - `scrapy/utils/misc.py`：开头和 `load_object`。
  - `scrapy/downloadermiddlewares/httpcompression.py`：15-45 行。
  - `scrapy/core/downloader/handlers/http11.py`：1-25、255-270 行，以及 `:269` 所在的 grep 命中。
  - `scrapy/selector/csstranslator.py`：1-20 行。
- **import 链上的 import 行：**
  - `scrapy/spiders/`：`__init__.py`、`crawl.py`、`feed.py`、`sitemap.py`。
  - `scrapy/selector/`：`__init__.py`、`unified.py`、`lxmlsel.py`、`lxmldocument.py`。
  - `scrapy/http/request/`：`__init__.py`、`form.py`、`rpc.py`。
  - `scrapy/http/`：`common.py`、`response/html.py`、`response/xml.py`。
  - `scrapy/utils/`：`url.py`、`deprecate.py`、`iterators.py`、`sitemap.py`、`decorators.py`、`trackref.py`、`response.py`、`spider.py`。
  - 其它：`scrapy/item.py`、`scrapy/linkextractors/__init__.py`。
- **全仓 grep：**
  - 查了 `responsetypes`、`from_content_type`、`from_mimetype`、`ResponseTypes` 的所有调用点。命中位置包括 decompression 中间件、httpcompression 中间件、file/ftp/http11 下载处理器、`webclient.py` 和 `httpcache.py`。
  - 查了 `x-json`、`application/json`、`+json`。
  - 查了 `docs/topics/request-response.rst`、`docs/news.rst`、`docs/faq.rst` 中与 JSON、MIME、`TextResponse` 相关的行。

没有查的范围：

- 公开包不包含 `.venv`、`install.sh`、`.git` 和隐藏测试 `r2e_tests`。已装依赖及版本、`import scrapy` 能否成功都没有核实。
- import 链只抽查了 import 行，没有逐个读完函数体；py3.9 兼容性没有全面核对。
- 调用者中的 `webclient.py`、`httpcache.py`、`file.py`、`ftp.py`、`decompression.py` 只看了 grep 命中行。
- pytest 收集行为（`collect_ignore` 不作用于显式路径、`unittest.TestCase` 的收集、缺 pytest-twisted 时的表现）是按 pytest 的一般行为推断，未在本环境验证。

保留的限制：

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获到的模型实际消息。
- `worktree/` 不是完整的运行容器。
- 本文没有验证模型实际收到的消息、运行资源或开发条件。第 4 节的全部“预计现象”都是静态推断。

误读记录：无。本次没有读取任何 `private/` 或 `history/` 目录，也没有读取 gold 补丁、隐藏测试、期望结果或旧审查结论。

## 关键未知

1. **隐藏测试覆盖哪些入口和输入。** 它可能只测题面那种 str 版 `from_content_type`，也可能走 `Headers` 路径（py3 下为 bytes），或覆盖其它 JSON 变体。如果走 bytes 路径，只补映射在 py3 下仍会在 `scrapy/responsetypes.py:56` 抛 `TypeError`；这已经超出题面描述。
2. **评分如何处理 base 在 py3 下就失败的既有用例。** 相关用例是 `test_from_headers` 和 `test_from_args`。也不知道超出题面的 bytes 兼容修复会不会改变评分结果。
3. **`.venv` 里的依赖能否让 `import scrapy` 成功。** 环境没有 pip，也不能出网，缺依赖时无法补装；公开材料没有给出已装版本。
