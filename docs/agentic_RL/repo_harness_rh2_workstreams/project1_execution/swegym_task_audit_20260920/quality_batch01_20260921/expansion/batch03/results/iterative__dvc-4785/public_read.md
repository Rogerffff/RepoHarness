# iterative__dvc-4785 公开要求静态审查

本次只阅读角色卡及指定 `PUBLIC_DIR` 内的公开材料；未读取私有评分、gold、其它题、历史结论或镜像克隆，未联网、运行项目、安装依赖或修改 `base/`。以下路径均相对本题公开包。所有开发命令均为**建议，未执行**。该阅读范围是协作约定，不是文件权限隔离或预训练无污染证明。

## 1. 需求表

| 行为 | 公开依据 | 确定程度及应保留事项 |
| --- | --- | --- |
| HTTP(S) 存在性检查遇到 401/403，不应把错误当作文件不存在 | `user_prompt.txt:3-6`，同一 issue 在 `:7-10` 重复；`base/dvc/tree/http.py:143-144` 直接将响应转成布尔值 | **明示**。至少应使调用方看见失败，不能静默返回 `False`。重复文本未增加另一组要求。 |
| 成功响应继续表示存在；404 继续表示不存在 | `user_prompt.txt:6` 的 “unless we have success or 404”；`base/dvc/tree/http.py:130-144` | **明示目标，代码补充接口形式**。`exists(path_info, use_dvcignore=True)` 应维持布尔查询接口；不宜把所有 HTTP 错误都抛出而丢失正常 404 分支。这里的 404 指用于判断的响应，HEAD/GET 混合错误的选择另见下文。 |
| 其它失败状态（例如 500）也应被显式报告 | 标题和 `res.raise_for_status()` 建议，`user_prompt.txt:3-6` | **可合理推知**。只硬编码解决 401/403、继续把其余错误都当不存在，不符合广义问题描述。题面未列完整状态码矩阵。 |
| HTTP 与 HTTPS 一致受益 | 题面 `HTTP(S)`；`base/dvc/tree/https.py:3-7` 直接继承 `HTTPTree`；`base/dvc/dependency/http.py:7-8`、`base/dvc/dependency/https.py:5-6` | **明示并有代码支持**。可以在共享实现内处理，无需分别复制逻辑。 |
| 保留 HEAD 不可用时成功 GET 的回退 | `base/dvc/tree/http.py:130-141` 明确注明部分服务器禁止 HEAD，并在 GET 成功时返回 GET 响应 | **现有代码可合理推知的兼容行为**。例如 HEAD 405、GET 200 应继续成功；在任何 HEAD 错误上立即抛异常可能破坏此行为。 |
| 保留请求层现有认证、重定向、超时、TLS 配置及上传下载规则 | `base/dvc/tree/http.py:51-57,59-128,161-200`；`base/tests/unit/remote/test_http.py:7-127` | **现有接口和公开测试约定**。请求默认跟随重定向、超时 60 秒；301/302 无 Location 的特殊错误仍需兼容。下载错误已用 DVC 的 `HTTPError`，上传仅接受 200/201；本题没有要求扩大这些操作的成功范围。 |
| 上层应能区分“缺失”与“查询失败” | `base/dvc/tree/base.py:240-247,615-638`；`base/dvc/remote/base.py:54-100` | **由调用者可合理推知**。`False` 会让 `get_hash` 返回 `None`，或让远程 hash 筛选丢掉该对象；异常可以中止这种错误的缺失判断。无需新增返回结构或命令行选项。 |
| 异常类、精确文案、错误状态优先级 | 题面称 `raise_for_status()` 为 “simplest fix”；`base/dvc/exceptions.py:287-289` 已有 DVC `HTTPError`；`base/dvc/main.py:88-109` 区分 DVC 异常与通用异常 | **仍有多种合理解释**。Requests 原生 HTTPError 和现有 DVC HTTPError 均有公开理由；二者命令行呈现有所不同。公开材料没有规定 `.exists()` 必须抛哪个类、逐字匹配哪句文本。 |

**issue、harness、环境声明分开记录：** issue 只要求上述状态处理变化。`public_bundle.json:1` 的 `public_hints` 另要求编辑非测试源码、不改测试、窄范围验证、完成后简短总结；其中“conda testbed 已激活、工具已就绪”是待验环境声明。`environment_brief.md:20-26` 明确说明旧“所有测试修改都会恢复、永不计分”不能代表当前机制：当前不按测试文件名统一排除，仍有官方文件恢复等具体限制。原禁止改测试指令是否实际适用仍须核对，本审查不授权忽略它。

若禁止改测试适用，本题可以只改生产源码，并用现有测试和临时内联诊断验证，未发现它必然排除合理生产修复；它会限制把新回归案例写入仓库测试文件。若不适用，可补测试，但不改变目标行为或使测试改动本身成为修复。此差别登记为共享输入/运行条件问题，不能从旧恢复说明推断题目不可用。bundle 会写入解题容器公开路径；未在 `user_prompt.txt` 渲染不等于字段不可读（`environment_brief.md:25-26`）。

## 2. 合理实现范围

- 可以在 `exists()` 对选定响应分类，也可以经小型共享辅助函数处理；只要保留成功、缺失、查询失败三者的区别及现有 HEAD/GET 兼容行为，不应凭实现位置、分支顺序、局部变量名或是否字面调用 `raise_for_status()` 排除等效实现。
- 直接使用 Requests 的状态异常，或使用现成 DVC `HTTPError(code, reason)`，都能从题面/仓库获得依据。后者与上传下载及 CLI 的 DVC 异常路径一致；前者是题面明确提出的最简方向。公开证据支持“有可诊断的 HTTP 失败”，不支持唯一异常类或精确错误字符串成为硬约束。
- `exists()` 的方法签名、布尔成功/缺失语义、HTTPS 继承关系以及现有认证/TLS/请求参数有代码约定；没有要求新增名称、配置键、返回对象或新的用户输出格式。把成功范围缩为只允许 200 会收窄当前行为，题面没有给出这种理由。
- 合理修复不必重写所有 HTTP 操作。`get_file_hash()` 也使用 `_head()`（`base/dvc/tree/http.py:146-159`），因此若把检查移到该层，应评估对读取 ETag/Content-MD5 的影响；题面聚焦 `.exists()`，没有明示要求修改其直接调用时的所有失败表现。

尚未唯一决定的边界：

1. `_head()` 在 HEAD 和 GET 均失败时返回原 HEAD 响应（`base/dvc/tree/http.py:137-141`）。HEAD 404、GET 403 时，是保留 HEAD 的缺失结论还是报告 GET 的拒绝；HEAD 403、GET 404 时又是否反过来，题面没有说明。HEAD/GET 同为 401、403 或 404 的基本案例没有这个歧义。
2. “成功”没有列出全部终态 3xx。现有逻辑依赖 Requests 的响应真值/`ok`，且请求通常跟随重定向；301/302 缺 Location 已有特殊错误。不能从本题推导必须全面重定义重定向或每一个非 2xx 的意义。实际依赖版本及其行为应在 actor 环境核对。
3. HEAD 被拒但 GET 成功，应按现有回退继续认为存在。若将标题理解为“任何中间 HTTP 错误都必须报告”，会与这个已有兼容行为冲突；更有代码依据的解释是报告最终存在性判断无法处理的失败。

## 3. 初态线索与疑义

公开入口清楚：题面直接点名 `.exists()`，源码对应 `HTTPTree.exists()`。共享的 HTTPS 子类、HEAD/GET 选择、上层 hash 查询路径均可正常查代码得到，不属于题面缺失。`base_identity.json:3-15` 记录指定 commit、465 个导出条目、无 gitlinks/LFS 未物化指针、未导出 Git 元数据；这些是包内身份记录，未在真实容器另行验证。

已读公开单元测试 `base/tests/unit/remote/test_http.py:7-127` 覆盖下载错误、认证、默认 TLS 验证及自定义请求方法，未直接覆盖 `.exists()` 的 401/403。`base/tests/unit/dependency/test_http.py:1-7` 继承通用缺失依赖测试；该测试直接 mock `exists=False`（`base/tests/unit/dependency/test_local.py:16-20`），可说明缺失语义，不能证明 HTTP 错误已测到。`base/tests/func/test_import_url.py:118-141` 有本地 HTTP fixture 的导入成功场景。相关测试关键字搜索也未发现直接针对 HTTP `_head()` 或 `.exists()` 错误状态的现有断言；这不是对全仓测试的穷尽证明。

基本缺陷可用 mock 的响应离线复现，无需真实账户、认证凭据、公网远程存储、GPU、模型或数据集。HEAD 回退的外链 issue #4131 未随包附完整讨论，但源码注释已说明目的，当前未发现必须补入该链接内容才能开发。安装和贡献指南有外链（`base/README.rst:91-92,148-152`、`base/CONTRIBUTING.md:1`）；本地依赖声明和 CI 已提供调查入口，不应自动要求联网或拉取最新代码。未发现本题必须补读公开祖先历史的理由。

会真正影响执行、但尚未核实的是 actor 的解释器与依赖兼容、测试收集依赖、本地 loopback 监听及临时目录权限。依赖/服务不足需要运行条件补齐，不等同于需求无法解释。没有原始失败日志或真实远程 URL，也不妨碍用受控 401/403 响应复现核心行为。

## 4. 开发需求表及最小验证入口

所有下列命令均为**建议，未执行**，工作目录假定是将来的 actor `/testbed`；不是在本次静态导出中执行。环境说明只提供计划和声明，未提供运行通过证据（`environment_brief.md:3-13`）。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小命令/预计现象 |
| --- | --- | --- | --- |
| actor 身份、源码工作目录、Python 导入 | `public_bundle.json:1`；`base/setup.py:48-85,173`；CI 使用 Python 3.6–3.9：`base/.github/workflows/tests.yaml:35-51` | 声明 `/testbed`、agent/54321、可写工作区/home；conda 激活未验 | **建议，未执行：** `id`、`pwd`、`python -c 'import sys, requests; from dvc.tree.http import HTTPTree; from dvc.tree.https import HTTPSTree; print(sys.executable, sys.version); print(HTTPTree, HTTPSTree, requests.__version__)'`。预计能导入；缺依赖或旧包不兼容是环境失败，不能算本题状态处理失败。Python 下限声明不是任意新版本已兼容的证明。 |
| 离线状态诊断，无服务和凭据 | `base/dvc/tree/http.py:130-144`；`base/dvc/tree/https.py:6-7` | CPU 资源按默认说明，实际未验；此路径不需网络、Docker 或 TLS 证书 | **建议，未执行：** 下方内联 Python。预计基线把 401/403/500 返回 `False`；修复应报告异常。200/204 为 `True`，404 为 `False`，HEAD 405/GET 200 为 `True`。两种协议都检查。 |
| 窄范围公开测试的收集与 Python 依赖 | `base/setup.py:108-146`；`base/tests/conftest.py:5-6`；`base/tests/remotes/__init__.py:5-34`；`base/tests/remotes/s3.py:7` 顶层导入 moto | 仅有“测试工具已就绪”旧声明；不保证镜像所有依赖及版本匹配 | **建议，未执行：** `python -m pytest --collect-only -q tests/unit/remote/test_http.py`，成功后 `python -m pytest -q tests/unit/remote/test_http.py`。预计现有测试可在基线和修复后通过；它们不是核心缺陷的直接失败证据。即使只选 HTTP 文件，全局 conftest 仍可能要求 moto 等其它收集依赖，不能只预装 requests 就宣布 pytest 可用。 |
| 本地 HTTP 服务、可写临时文件、线程和端口 | `base/tests/remotes/http.py:14-18,37-48`；`base/tests/utils/httpd.py:8,92-114`；`base/setup.py:135` 固定 rangehttpserver 1.2.0 | 不假定公网；loopback 服务与 actor 权限未验证 | 上述单元文件的下载错误测试会启动本地服务器；需 `RangeHTTPServer`、临时目录及 localhost 随机端口。**建议，未执行：** `python -m pytest -q tests/func/test_import_url.py -k 'test_import_url and http'`。预计只选 HTTP 参数化成功路径并通过；实际选中数需检查，零选中不能算通过。无需启动其它远程服务。 |
| pytest 资源初始化及测试 fixture | `base/tests/__init__.py:41-47` 设置文件描述符和进程资源限制；`base/tests/dir_helpers.py:92-112,289-315` 创建临时 DVC/Git fixture；`base/tests/basic_env.py:7-13` 导入 GitPython | 默认 2 CPU/4 GiB/PID512 与 tmp/home 限额，未验真实 hard limit、Git、写权限 | 收集可能先因设置 RLIMIT 或依赖失败；fixture 需临时目录写权限，涉及 Git 的扩展检查需可用 Git。**建议，未执行：** `git --version`、`python -m pytest -q tests/unit/dependency/test_http.py`。预计通用缺失依赖测试通过；不把此结果当作 401/403 验证。窄范围 pytest 不使用 `python -m tests` 默认的 4 个 worker（`base/tests/__main__.py:19-23`）。 |
| 安装/构建资产 | `base/setup.py:48-85,108-146,148-186`；CI 安装 `.[all,tests]`，`base/.github/workflows/tests.yaml:48-51` | 网络不允许假定公网下载；无已验证 wheel/cache 清单 | 本题是 Python 源码逻辑审查，导入和窄测试足够，无需先构建发行包。**建议，未执行：** `python -m pip check` 用于核对已安装依赖。若导入/收集确实缺包，需提供与该旧代码兼容的预装环境或离线依赖；不建议未经诊断照搬 CI 联网安装全部远程 extras。 |

**建议，未执行：最小离线复现命令。** 只替换当前对象的 `request` 返回值，保留生产 `_head()` 和 `exists()` 路径，不写测试文件，也不会发出网络请求。代码用于观察行为，不规定唯一异常类型。

```bash
python - <<'PY'
from http import HTTPStatus
from unittest.mock import patch

from requests import Response
from dvc.tree.http import HTTPTree
from dvc.tree.https import HTTPSTree

for cls, scheme in ((HTTPTree, "http"), (HTTPSTree, "https")):
    tree = cls(None, {"url": scheme + "://example.invalid/file"})
    for head, get in ((200, 200), (204, 204), (404, 404),
                      (401, 401), (403, 403), (500, 500), (405, 200)):
        def request(method, url, **kwargs):
            code = head if method == "HEAD" else get
            response = Response()
            response.status_code = code
            response.reason = HTTPStatus(code).phrase
            response.url = url
            response._content = b""
            response._content_consumed = True
            return response

        with patch.object(tree, "request", side_effect=request):
            try:
                outcome = tree.exists(tree.path_info)
            except Exception as exc:
                outcome = (type(exc).__name__, str(exc))
        print(cls.__name__, head, get, outcome)
PY
```

上面 401/403/500 的基线预计打印 `False`，正是需要纠正的行为；修复后预计打印含 HTTP 失败信息的异常。该脚本并不证明真实认证、TLS、连接错误、重定向或完整命令行路径可用。混合错误 HEAD 404/GET 403 与 HEAD 403/GET 404 可追加作调查样例，但其期望值应先明确，不能将任意一种结果预设成唯一验收要求。

## 5. 实际阅读范围和未查项

实际完整打开：角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；`base/dvc/tree/http.py`、`base/dvc/tree/https.py`、`base/dvc/dependency/http.py`、`base/dvc/dependency/https.py`；`base/tests/unit/remote/test_http.py`、`base/tests/unit/dependency/test_http.py`、`base/tests/unit/dependency/test_local.py`、`base/tests/remotes/http.py`、`base/tests/remotes/__init__.py`、`base/tests/utils/httpd.py`、`base/tests/conftest.py`、`base/tests/func/conftest.py`、`base/tests/__init__.py`、`base/tests/__main__.py`；`base/setup.py`、`base/setup.cfg`、`base/pyproject.toml`、`base/CONTRIBUTING.md`。

实际分段打开：`base/dvc/tree/base.py:30-135,230-290,605-654`；`base/dvc/remote/base.py:1-200`（文件止于 169）；`base/dvc/exceptions.py:1-48,280-302`；`base/dvc/main.py:29-131`；`base/tests/func/test_remote.py:1-225,460-590`（输出部分截断，此文件未作为核心 HTTP 要求证据）；`base/tests/func/test_import_url.py:118-186`；`base/tests/dir_helpers.py:1-160,270-340`；`base/tests/basic_env.py:1-110`；`base/README.rst:87-155`；`base/.github/workflows/tests.yaml:35-70`。

此外在本题公开包执行文件名及关键词搜索，范围包括 HTTP 相关文件、`base/dvc/remote/`、`base/dvc/tree/`、`base/tests/`、安装/CI 文件，读取搜索命中行，例如 `base/tests/remotes/s3.py:7`、`base/dvc/tree/__init__.py` 及部分其它 remote fixture 的 import 行。对不存在的 `Makefile`、`tests/func/test_external.py`、`tests/unit/test_remote.py` 的搜索只返回路径不存在；未把不存在路径当成内容证据。未完整阅读其它远程后端或全仓测试。

未查：真实镜像与 actor shell、实际模型请求/消息、当前测试恢复明细、安装包源码和版本、锁定依赖解析、真实服务、资源/权限、项目执行结果、外链全文及公开祖先历史。`user_prompt.txt` 只是静态渲染，`base/` 不是完整运行容器；不能据本报告宣称实际开发条件或测试已经验证。关键未定项是异常类型/输出边界、混合 HEAD/GET 错误状态的优先级，以及上述真实运行条件；核心状态错误与公开调查入口已经可以从现有材料识别。
