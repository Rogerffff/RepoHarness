# coveragepy 016af5f6：修订题面公开静态阅读

日期：2026-10-03。结论：目标清楚，公开代码静态支持示例的调用顺序与保存阶段的失败路径；未发现题面强迫某一修复位置或实现方法。实际复现、修复有效性与容器测试均未验证，本报告不构成 actor 交付或 CPU 验收。

## 题意与边界

`statement_v1.txt` 明确要求：遇到不能用 UTF-8 编码的文件名，保存 coverage 数据不应因 `UnicodeEncodeError` 中断；允许跳过该文件或内部处理编码错误。它未限定必须改 tracer、数据库层或其他具体模块，未要求特定告警或文件名保留方式，合理实现路线仍开放。

两点措辞需按示例理解：这里的 “Non-UTF8 Filenames” 指 Python 文件名字符串包含不能严格 UTF-8 编码的代理码点（示例 `\udcff`），并非所有非 ASCII 文件名；示例只给 `compile` 一个逻辑文件名，没有创建真实磁盘文件。题面没有说明异常文件是否必须保留覆盖数据，但明确允许 skipping，因此这不是阻碍实现的歧义。错误文本中的 `position 80` 依赖绝对路径，不宜作为固定验收条件。

## 公开代码依据

- `coverage/control.py:504–543`：`start()` 启动 collector，`stop()` 停止采集而未调用 `get_data()`。`start()` 文档说明同一作用域语句不被测量；示例执行的是新编译代码帧，调用顺序没有因此失效。
- `coverage/pytracer.py:131–164` 与 `coverage/ctracer/tracer.c:389–425`：新帧的 `co_filename` 被送入 `should_trace`，行数据按所得源文件名收集。
- `coverage/inorout.py:212–255, 280–299`：`__file__` 与原文件名 basename 不同时保留原文件名；示例的 `\udcff.py` 不符合空名、`memory:` 或 `<...>` 排除条件。`coverage/files.py:55–76, 162–171` 的规范化没有静态保证拒绝该名字，也没有要求源文件必须存在。
- `coverage/control.py:640–643, 682–701` → `coverage/collector.py:411–433` → `coverage/sqldata.py:423–452, 358–369`：`save()` 先 `get_data()`、刷新行数据，最终把文件名原样作为 SQLite `file.path` 参数；`SqliteDb.execute()`（1026–1047）只捕获 `sqlite3.Error`，没有 `UnicodeEncodeError` 分支。这支持“编码异常可从 `save()` 冒出”的静态推断。精确的 Python/SQLite 参数编码行为仍须实跑确认。`CoverageData.write()`（744–746）是空操作，因此保存阶段的失败更准确地说发生于刷新数据，而非最后的 `write()`。
- 公开测试 `tests/test_oddball.py:531–562` 已覆盖 `exec(compile(...))` 文件名归属，支持该调用方式是项目接受的使用场景；未运行该测试。

## 必须实跑的环境未知

公开环境说明给出 `/testbed/.venv/bin/python` 为 Python 3.7.9，有 pip、无出网，agent 可写 `/testbed` 与 home，2 CPU / 4 GiB、`/tmp` 1 GiB。它同时明确静态快照省略 `.venv`、编译产物和隐藏测试。仅据此无法确认实际导入路径、C 扩展是否可用、SQLite 版本及其代理码点绑定表现、测试依赖是否齐备，以及原示例的实际异常栈。

`collector.py:19–33, 149–155` 在 CTracer 不可用时回退到 PyTracer；两种 tracer 的实际可用性与修后结果需在目标环境核对。`Coverage()` 默认读配置（`control.py:99–101, 131–144`），运行环境也可能影响选择和过滤。公开 `setup.cfg` 没有 coverage 配置节，但 pytest 默认 `-n3`；局部验证可用 `-o addopts=` 避免这一默认并行度。`tox.ini` 包含装包、构建和切换扩展流程，离线环境不能把直接跑 tox 当成必然可用路径。

旁附 `public_reader_commands_20261003.json` 仅记录建议命令，全部未执行。最小检查依次为解释器/导入与 tracer 能力、原题示例、相关公开回归测试；修后不能只检查进程不报错，还应确认普通文件仍能保存数据。

## 实际输入与 SHA-256

阅读限于请求本身、修订题面、中性环境说明、公开 manifest 与公开工作树代码/配置/测试；没有打开来源引用、旧 bundle 题面、私有题卡、审查/评分/候选材料或 `tests/gold` 内容。曾枚举公开工作树文件名；未运行项目、安装依赖、联网、SSH、修改源码或调用其他模型。manifest 标注 base commit 为 `5bb5da50b182583036b7808bb32f2c8c191d9d26`、base tree 为 `43af3882f5a62cf0b6c2ed4f3165b57b202cb30e`；这是公开标注，本阅读未独立核验完整工作树。

四个入口的实测 SHA-256：

```text
public_review_request.md  9c44174d83fa1f1cb40c78775467ef75a0ba5e7d8940c354aae74fb0594bc703
materials/statement_v1.txt  e654fab906c8c9b5a994aed85c7e924c2389f10842dc319d0249060d3ee7d1e1
environment_brief.md  f8cc81e0637d940699d34a1e3c73bd1b8298abdce242cd0e4054207d217d4245
worktree_manifest.json  b1248e090428ae116e02912537e9cf0962d35a363a3af5a153e6dd2abfa38afb
```

实际读取或检索的工作树文件实测 SHA-256（均相对允许的 `worktree/`）：

```text
coverage/control.py  6fe345880a0c96663bf00eb14299d266f19b3c5c4f3a23512481099a50e36780
coverage/inorout.py  8b43bcbb279ee4f083a167deabcc19b2dc8caef43786f7c1f36001aee813ee8a
coverage/collector.py  68c470a8f6ccfbde45d746af052433cd157719a947980d7399facea9f9a9bd33
coverage/files.py  24089e67d9f67172d3f3afa8e5496c347f884bff99e9775579c3f60c9c083cf2
coverage/pytracer.py  be5a5345587fa2fa8c9dd47fbf4494435481d44360bcac8ea8c0d553ef3d0f1b
coverage/sqldata.py  d3823873dac7bcc15024e490d099239ad4beef3fcdffea671291bc6401b2c4b7
coverage/ctracer/tracer.c  21ab6fd0e140700414dfc977711b5cb7e3a557af847c9af2618e134e8eee15ee
coverage/config.py  b8d5580bba47dfe77ecc21f4846584e5574caf8bdc76c0a4a1d5246b33d71ce8
tox.ini  788fe41a1830b5f116eda692804aa3887df7bd026f422cf005b45d27f6e649c8
setup.cfg  f31a1d281e54ec6f76e5a702a546e6dad86b2800764cf7eda5fdb3934ccac518
requirements/pytest.pip  e353c177221330095b47f1e98a929383654012bd187069bd06619cba0d0ea924
tests/test_oddball.py  fcef33208ca267dc6719fb258c3dea043d23e19cf34af2d62528cb24286aae7f
tests/test_api.py  3beea4f71b899425b04381a1fce30e4c2bbcf5d590ec49b5092f86811f507767
tests/test_data.py  d66b56b59dbcdc9faeb272d6545a13e4c592c0e712ff1f0361a6d8d838c00c51
```
