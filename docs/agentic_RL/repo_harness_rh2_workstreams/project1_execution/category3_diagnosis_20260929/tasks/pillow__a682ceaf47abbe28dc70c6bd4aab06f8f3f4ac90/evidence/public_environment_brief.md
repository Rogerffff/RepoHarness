# 环境说明（pillow__a682ceaf，负责人核实于 2026-09-30）

以下只列在来源镜像里实际核对过的事实；未核对的写“未核对”。

- 工作目录 `/testbed`，仓库处于 base 提交 `7a1e28404`（“Merge pull request #7272 from radarhere/harfbuzz”）。工作树中有两个未跟踪的构建文件：`install.sh`、`run_tests.sh`。
- Python 环境：`/testbed/.venv`，`python` 为 CPython 3.9.21（uv 管理的解释器）。
- Pillow 以可编辑方式安装自 `/testbed/src`（`import PIL` 得到 `10.1.0.dev0`，`PIL.__file__` 为 `/testbed/src/PIL/__init__.py`）。仓库含 C 扩展（`src/*.c`、`src/libImaging/`），由 `install.sh` 中的 `uv pip install -e . --no-build-isolation` 构建。只改 Python 文件无需重建；改 C 源码后需要重建，重建在无网络环境下能否成功：未核对。
- `python -m pytest` 可用（pytest 8.3.4）。仓库自带公开测试在 `Tests/`。
- 无网络。`pip` 是否可用：未核对（`install.sh` 使用 `uv`）。
- 本目录的 `worktree/` 是 `/testbed` 的副本，去掉了 `.venv/` 与 `.git/`；两者在真实解题环境里都存在。
