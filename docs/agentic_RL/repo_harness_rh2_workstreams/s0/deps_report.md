# S0-1 依赖底座报告（V1 结论）

日期：2026-07-07。执行位置：本机（macOS，Python 3.12.13 via uv）。

## 工程

`rh2/` 独立子项目（C2 定案）：`pyproject.toml`（`package = false`，src layout 骨架）+ `uv.lock` + `.python-version=3.12`。根 pyproject 与旧包未动。

## verifiers pin

```text
verifiers = { git = "https://github.com/PrimeIntellect-ai/verifiers",
              rev = "5885ab9c54152e707af2a11797aa52c3eb1752da" }   # 完整 40 位 hash（C1）
```

与 `reference/verifiers` 本地 checkout HEAD 一致（`git rev-parse HEAD` 核对）。

## 实际安装版本

```text
python          3.12.13
verifiers       0.1.15.dev419   （pin commit 构建版本号）
renderers       0.1.8.dev54
prime-sandboxes 0.2.28
prime-tunnel    0.1.10
pydantic        2.13.4
```

`import verifiers.v1` 与 `import renderers` 均成功。

## V1 判定

- **安装层：通过**——全部依赖（含 prime 生态三件）在 macOS + Python 3.12 一次安装成功，无版本冲突、无编译失败。方案 A（依赖 + 子类扩展）的安装前提成立。
- **使用层（DockerRuntime 起容器执行 run()）**：由 S0-3 docker 分支验证，结果见 `toy_trace_dump/`。
- **prime runtime 实际调用**：按计划降级为可选（import 惰性已核实），未验证，不阻塞。

## 备注

- uv 提示 `VIRTUAL_ENV` 指向根仓库旧 venv 与 rh2 项目 venv 不一致并忽略之——预期行为（两套环境隔离正是 C2 的目的），在 rh2/ 下运行一律用 `uv run`。
