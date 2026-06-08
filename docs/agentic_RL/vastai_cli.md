**暂停(停止)实例** — 保留数据,可重启:
```bash
vastai stop instance <ID>
```

**删除实例** — 不可逆,数据会丢失:
```bash
vastai destroy instance <ID>
```

批量操作可使用 `vastai stop instances` 和 `vastai destroy instances`(支持多个 ID)。先通过 `vastai show instances-v1` 查看实例 ID。

```suggestions
(Stop Instance)[/cli/reference/stop-instance]
(Destroy Instance)[/cli/reference/destroy-instance]
(CLI Hello World)[/cli/hello-world]
```

## 本机 CLI 安装和认证记录

当前项目虚拟环境中已经安装 Vast.ai CLI：

```bash
uv pip install vastai
.venv/bin/vastai --help
```

官方文档安装命令是：

```bash
pip install vastai
```

本机为了避免污染系统 Python，使用当前 RepoHarness worktree 的 `.venv` 安装。

API key 已通过本地 CLI 配置：

```bash
.venv/bin/vastai set api-key "$VASTAI_API_KEY"
```

认证验证命令：

```bash
.venv/bin/vastai show user
```

验证结果：`vastai show user` 已能成功返回账户信息。不要把完整输出写入提交或公开报告，因为其中可能包含账户信息。

## 常用实例操作

查看当前实例：

```bash
.venv/bin/vastai show instances-v1
```

`vastai show instances` 当前仍可用，但 CLI 提示它后续会废弃，因此优先使用 `show instances-v1`。

查看单个实例详情：

```bash
.venv/bin/vastai show instance <ID>
```

获取 SSH 地址：

```bash
.venv/bin/vastai ssh-url <ID>
```

暂停实例，保留磁盘数据并停止计算计费：

```bash
.venv/bin/vastai stop instance <ID>
```

启动或恢复已经暂停的实例：

```bash
.venv/bin/vastai start instance <ID>
```

删除实例，不可逆，会丢失实例磁盘数据：

```bash
.venv/bin/vastai destroy instance <ID>
```

Stage 12.6 远端 smoke 完成或遇到无法继续的问题时，默认使用 `stop instance` 暂停实例，不要使用 `destroy instance`，除非用户明确要求删除。

## 安全注意

当前文件临时包含 API key，不能提交到 Git，不能上传到远端 evidence，也不能复制到运行报告。后续建议把 API key 移到本机 Vast.ai CLI 配置或环境变量中，并从本文档删除明文 key。


VASTAI_API_KEY:3a86df1ad3002ba52b864fc43551e68149d8ab75a01bc25ac76b359d0d7eef37
