# DataLad 开发环境说明

工作目录为 `/testbed`。使用仓库已有的 `.venv` 解释器；运行命令时加 `-B` 可避免写入 Python 字节码缓存。

核对解释器、公开依赖及源码导入位置：

```bash
/testbed/.venv/bin/python -B -c "import sys, six, requests, appdirs, datalad; from datalad.support.network import URL, is_url; print(sys.version.split()[0], datalad.__version__, datalad.__file__)"
```

用公开 API 观察题面示例的字段与 URL 识别结果：

```bash
/testbed/.venv/bin/python -B -c "from datalad.support.network import URL, is_url; u = URL('weired_url:/'); print(repr(u), u.fields, is_url('weired_url:/'))"
```

相关公开测试：

```bash
/testbed/.venv/bin/python -B -W ignore -m pytest -p no:cacheprovider -rA datalad/tests/test_network.py
```

这个公开测试文件中，题面示例的用例原来被注释。另有与本题解析问题无关的历史兼容差异：Python 3.7 的 `urllib.parse.quote` 保留 `~`，`test_get_local_file_url_linux` 仍期望 `%7E`；nose 式 yield 用例 `test_get_url_straight_filename` 在该 pytest 版本中不执行。修改后应结合题面要求检查公开行为。
