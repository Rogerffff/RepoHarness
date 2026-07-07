# R2E-Gym-Subset Docker 镜像修复前状态核验报告

核验任务：DF-2，确认 HuggingFace 数据集 `R2E-Gym/R2E-Gym-Subset` 中样本对应的 Docker 镜像工作区是否仍处于修复前状态，也就是镜像内代码是否尚未应用 `parsed_commit_content` 描述的金标修复。

核验日期：2026-07-07

## 总结论

本次核验的 3 个不同仓库样本分别来自 `orange3`、`coveragepy`、`numpy`。三者结论一致：

- 镜像内仓库目录均为 `/testbed`，镜像架构均为 `amd64`。
- 数据集字段 `commit_hash` 与 `parsed_commit_content.new_commit_hash` 一致，语义是“修复提交”，不是初始提交。
- 镜像内当前 `HEAD` 均不等于 `commit_hash`，而是等于该修复提交的父提交。
- `parsed_commit_content` 中新增的关键修复代码行在镜像工作区内均不存在，旧代码行仍然存在。

因此，本次抽样未发现镜像已经包含金标修复。对训练数据治理而言，这支持将 `docker_image` 视为修复前初始环境，将 `parsed_commit_content` 视为答案侧或者评测侧信息；训练过程不得把 `parsed_commit_content` 暴露给模型可见上下文。

## 样本选择说明

按任务要求，先使用如下接口获取前 5 行，并将响应落到临时文件后用 `jq` 抽取字段：

```bash
curl -fsSL 'https://datasets-server.huggingface.co/rows?dataset=R2E-Gym/R2E-Gym-Subset&config=default&split=train&offset=0&length=5' -o /tmp/r2e_subset_rows_0_5.json
```

实际返回文件大小为 `1,784,992` 字节，前 5 行的 `repo_name` 全部是 `orange3`，无法严格从这 5 行中选出 3 个不同仓库。随后扩大前缀探测：`offset=0&length=80` 仍全部是 `orange3`。为了完成“3 个不同仓库”的核验目标，本报告额外使用单行 offset 探测选取了第 500 行和第 1000 行。该偏离原因是数据集按仓库分段排序，而不是前 5 行已经覆盖多个仓库。

最终核验样本：

| 行号 | 仓库名称 | Docker 镜像 | `commit_hash` |
| --- | --- | --- | --- |
| 0 | `orange3` | `namanjain12/orange3_final:2d9617bd0cb1f0ba61771258410ab8fae8e7e24d` | `2d9617bd0cb1f0ba61771258410ab8fae8e7e24d` |
| 500 | `coveragepy` | `namanjain12/coveragepy_final:afe6cf34d022e8dbbaa47826c487a98ca6832721` | `afe6cf34d022e8dbbaa47826c487a98ca6832721` |
| 1000 | `numpy` | `namanjain12/numpy_final:10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149` | `10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149` |

## 实例 1：orange3，第 0 行

基本信息：

- 仓库名称：`orange3`
- 镜像：`namanjain12/orange3_final:2d9617bd0cb1f0ba61771258410ab8fae8e7e24d`
- 镜像摘要：`sha256:d546d21f56bb6b9c99045bd8fea196c04e43c9fbd6d9bc36fba4a90f88a45276`
- 镜像工作目录：`/testbed`
- 数据集 `commit_hash`：`2d9617bd0cb1f0ba61771258410ab8fae8e7e24d`
- `parsed_commit_content.new_commit_hash`：`2d9617bd0cb1f0ba61771258410ab8fae8e7e24d`
- `parsed_commit_content.old_commit_hash`：`2d9617bd0cb1f0ba61771258410ab8fae8e7e24d^`
- 修复提交信息：`Settings migration: Allow rejecting a context`

提交关系核验：

- 容器内 `HEAD`：`a9f233e7805abc417f65e334f678b45960926614 Merge pull request #3271 from janezd/prevent-vizrank-edit`
- 修复提交在容器 Git 历史中存在：是。
- `HEAD == commit_hash`：否。
- `commit_hash` 的父提交：`a9f233e7805abc417f65e334f678b45960926614`
- `HEAD == commit_hash` 的父提交：是。
- `HEAD` 是修复提交的祖先：是。

关键文件核对：

- `Orange/widgets/settings.py` 的目标函数 `_migrate_contexts` 仍为旧实现：

```python
def _migrate_contexts(self, contexts):
    for context in contexts:
        self.widget_class.migrate_context(context, context.values.pop(VERSION_KEY, 0))
```

- 金标修复中新增的 `__all__` 导出行 `"IncompatibleContext"]` 不存在。
- 金标修复中新增的回归测试 `def test_migrates_settings_removes_incompatible(self):` 在 `Orange/widgets/tests/test_context_handler.py` 中不存在。
- 注意：`Orange/widgets/settings.py` 其他位置本来已有 `IncompatibleContext` 相关代码，因此不能只用全文件是否出现 `except IncompatibleContext:` 作为判断依据。本次采用目标函数 `_migrate_contexts` 的上下文作为判据。

结论：该镜像处于修复前状态。

## 实例 2：coveragepy，第 500 行

基本信息：

- 仓库名称：`coveragepy`
- 镜像：`namanjain12/coveragepy_final:afe6cf34d022e8dbbaa47826c487a98ca6832721`
- 镜像摘要：`sha256:4296a97761a450eadd22a31f6ddcaae938d2b94288fa8569e5297d4be0ea9698`
- 镜像工作目录：`/testbed`
- 数据集 `commit_hash`：`afe6cf34d022e8dbbaa47826c487a98ca6832721`
- `parsed_commit_content.new_commit_hash`：`afe6cf34d022e8dbbaa47826c487a98ca6832721`
- `parsed_commit_content.old_commit_hash`：`afe6cf34d022e8dbbaa47826c487a98ca6832721^`
- 修复提交信息：`fix: avoid measuring generated code. #1160`

提交关系核验：

- 容器内 `HEAD`：`8021196662dcadf161cbeaebb3be4b0392b51803 refactor: no need for specialized pyexpat code anymore`
- 修复提交在容器 Git 历史中存在：是。
- `HEAD == commit_hash`：否。
- `commit_hash` 的父提交：`8021196662dcadf161cbeaebb3be4b0392b51803`
- `HEAD == commit_hash` 的父提交：是。
- `HEAD` 是修复提交的祖先：是。

关键文件核对：

- `coverage/inorout.py` 中金标修复新增的生成文件名保护逻辑不存在：

```python
if original_filename.startswith('<'):
    return nope(disp, "not a real original file name")
```

- `coverage/disposition.py` 中金标修复新增的调试输出分支 `if disp.original_filename != disp.source_filename:` 不存在。
- `CHANGES.rst` 中金标修复新增的 `issue 1160` 说明不存在。
- `tests/test_oddball.py` 中金标修复新增的 `Doctests used to be traced` 回归测试说明不存在。

结论：该镜像处于修复前状态。

## 实例 3：numpy，第 1000 行

基本信息：

- 仓库名称：`numpy`
- 镜像：`namanjain12/numpy_final:10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149`
- 镜像摘要：`sha256:af370c047e7d236cb6f17cc7edf51f49a76e34691bf944a3af97edb082d7093f`
- 镜像工作目录：`/testbed`
- 数据集 `commit_hash`：`10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149`
- `parsed_commit_content.new_commit_hash`：`10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149`
- `parsed_commit_content.old_commit_hash`：`10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149^`
- 修复提交信息：`Merge pull request #10412 from eric-wieser/record.__repr__`

提交关系核验：

- 容器内 `HEAD`：`1290e7fd5d40903d69733b4797f7c30ca025e1f7 Merge pull request #10418 from eric-wieser/basestring`
- 修复提交在容器 Git 历史中存在：是。
- `HEAD == commit_hash`：否。
- `commit_hash` 的父提交：`1290e7fd5d40903d69733b4797f7c30ca025e1f7`
- `HEAD == commit_hash` 的父提交：是。
- `HEAD` 是修复提交的祖先：是。

关键文件核对：

- `numpy/core/records.py` 中旧实现仍然存在：

```python
def __repr__(self):
    return self.__str__()

def __str__(self):
    return str(self.item())
```

- 金标修复新增的 `return super(record, self).__repr__()` 不存在。
- 金标修复新增的 `return super(record, self).__str__()` 不存在。
- `numpy/core/tests/test_records.py` 中金标修复新增的 `import textwrap` 不存在。

结论：该镜像处于修复前状态。

## 可选测试执行情况

本次没有运行每个实例的项目测试。原因是本任务的硬性核验目标是镜像工作区是否已经应用金标修复，提交关系和文件内容已经给出直接证据；而这些镜像在本机 `arm64` Mac 上通过 `linux/amd64` 模拟运行，项目级测试容易引入依赖安装、编译或者模拟性能因素，反而可能产生与“修复是否已应用”无关的噪声。

## 清理记录

核验完成后已执行 `docker rmi` 清理本次拉取的 3 个镜像。清理结果：

- 已移除 `namanjain12/orange3_final:2d9617bd0cb1f0ba61771258410ab8fae8e7e24d`，本地镜像标识为 `sha256:d546d21f56bb6b9c99045bd8fea196c04e43c9fbd6d9bc36fba4a90f88a45276`。
- 已移除 `namanjain12/coveragepy_final:afe6cf34d022e8dbbaa47826c487a98ca6832721`，本地镜像标识为 `sha256:4296a97761a450eadd22a31f6ddcaae938d2b94288fa8569e5297d4be0ea9698`。
- 已移除 `namanjain12/numpy_final:10a7d4fbb219e9198e9fa2b7dc3c3dcef7b39149`，本地镜像标识为 `sha256:af370c047e7d236cb6f17cc7edf51f49a76e34691bf944a3af97edb082d7093f`。
