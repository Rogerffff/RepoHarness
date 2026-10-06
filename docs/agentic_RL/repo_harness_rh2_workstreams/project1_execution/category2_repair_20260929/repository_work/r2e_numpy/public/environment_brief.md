# 本题公开审查的环境说明（中性，R2E）

这是静态材料，不是实际容器，也不是捕获的模型请求。`user_prompt.txt` 由当前 `render_user_prompt` 渲染；
`public_bundle.json` 的 `public_hints` 是正式链写进容器的 R2E 提示（`.venv`、不联网、pip 可能没有、不要改仓库测试文件）；环境细节以本说明为准。
`worktree/` 是解题者在 `/testbed` 看到的初始工作树：base 提交的跟踪文件，加上镜像初态相对 base 的改动与未跟踪的构建文件；
不含 `.git`、被 `.gitignore` 忽略的构建产物（编译扩展、`.venv` 等）和隐藏测试。缺哪些文件见 `worktree_manifest.json`。

## 解题环境（环境阶段实测，按本题填写）

- 工作目录 `/testbed`；`python` 经镜像环境变量指向 `/testbed/.venv/bin/python`（Python 3.7.9）。
- pip：没有（pip / pip3 / uv 命令都不在 PATH）；无出网，装不了新包。
- 解题身份是 agent（uid 54321），可写 `/testbed` 与 home；资源默认 2 CPU / 4 GiB，`/tmp` 1 GiB。
- 包没有装进 venv：`/testbed` 必须在 `sys.path` 上才能导入（在 `/testbed` 下用 `python -c`，或设 `PYTHONPATH=/testbed`）；跑测试用 `python -m pytest`，裸 `pytest` 收集会失败。

请只据公开材料列出必要的开发条件与最小验证命令；不要把缺证据当作题目不可解。不要读其它题或本目录之外的调查材料。
