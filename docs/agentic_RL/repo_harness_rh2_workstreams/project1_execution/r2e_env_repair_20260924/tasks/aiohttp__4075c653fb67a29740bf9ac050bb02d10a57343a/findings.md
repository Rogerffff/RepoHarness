# aiohttp `4075c653`（3.9.0b0）环境审查结论

**结论**：环境支持解题与判分；分类 `solver_condition`（包只在 cwd=/testbed 时可导入）。处置暂记 `unknown`，只差 R13。

**依据**
- R-f：noop 0（目标键 `test_bad_headers[py-parser-pyloop-\xffoo: bar]`、`test_http_request_bad_status_line_whitespace[py-parser-pyloop]`）、gold 1（129/129，入口 rc=1 属正常）；对账 agree。
- R06：3 个期望 FAILED 键 `test_c_parser_loaded`（AssertionError）、`test_invalid_character[pyloop]`、`test_invalid_linebreak[pyloop]`（NameError: HttpRequestParserC）都来自 **C 解析器扩展未构建**（`_http_parser.pyx/.c` 在、没有 `.so`，而 NO_EXTENSIONS=False）；noop / gold 稳定 FAILED，与解无关。
- 期望来源不统一的证据：来源宿主机记录里这三键 PASSED（宿主机建了 C 扩展、共 230 个用例），期望却和发布镜像一致（129 键）。
- 探针：十项最小条件满足；pip 23.2.1；公开测试 20/20 通过；公开复现：纯 Python 解析器对两段输入都不报错（`REPRO_OBSERVED=1`）。
- 脏树只有 `M Makefile`（pip→uv pip）与三个未跟踪脚本，无修复痕迹。

**缺口 / 风险**
- 若将来派生配方改为构建 C 扩展，这 3 个期望 FAILED 键会翻转，须同步修订期望。
- 解题者若在工作区建出 `.so`（离线能否构建未验证），评分 delta 是否带上这类二进制新文件未验证。

**建议**：声明 cwd /testbed 条件，跑测试用 `python -m pytest`（同仓其它 4 题实测裸 `pytest` 收集即 ImportError，本题同一 install.sh、未单测）；本地观测到的是纯 Python 解析器（与评分一致），不必尝试构建扩展。

先后说明（E06）：repros 写完后才读 gold 日志、隐藏测试与来源执行记录。
