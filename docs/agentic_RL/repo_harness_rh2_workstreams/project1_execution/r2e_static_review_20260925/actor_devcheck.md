# R2E 首批 8 题：真实 actor 条件下的开发命令核对（2026-09-25）

Claude（B 线 R2E 协调者）执行，按[共用开发验证流程](../actor_development_validation.md) §3 第 1–5 步。本页只记运行事实，不是审查结论；题目处置以各题 `card.md` 与 `review.md` 为准。命令清单取自各题公开读者与主审的开发需求，是"已跑的命令"，不代表开发需求已经列全。

## 1. 入口与共同条件

- **入口**：任务二的共用入口 [`devcheck.py`](../../../../../rh2/experiments/task2_swegym_dev_20260925/devcheck.py)，也就是 A 线 `acceptance_startup_2` 的正式装配：容器、relay、专用网络、git sanitize、可信初始化、激活文件、启动前核查与激活核查、`ClaudeCodeDriver.run`。模型换成桩端点，按命令清单发出 Bash 调用，每条命令都由真实 Claude Code 2.1.205 在 agent 身份的子 shell 里执行。
- **R2E 层**：在共用入口上加了一层 [`r2e_devcheck.py`](../../../../../rh2/experiments/r2e_actor_20260925/r2e_devcheck.py)，只改两处：
  - 任务面由正式的 `PreparedTaskFace.load` 加覆盖表构造，即派生镜像 image ID、`.venv` 激活与前缀、覆盖条目互检；
  - 命令清单最前面注入 R2E rollout 预检。

  没有另写 launcher。
- **本入口不验证**：桩端点直连，绕过了 Qwen adapter，所以 count_tokens、提醒、EOS、溢出都不在验证范围内。它也不证明模型能力。
- **机器**：A 线借给 B 线的 CPU 机，x86_64，8 vCPU / 31 GB，B 线目录是 `/work/b_r2e/`。
- **代码与摄入面**：
  - 代码是本机工作树快照，474 个文件逐个核对 sha256 一致。
  - 摄入面是今晚重新生成的一版（`public_hints` 改为 R2E 措辞，pin `781363b0…`）。
  - 派生镜像：orange3 `9b5494e2` 与 pandas `32dd55cb` 用批次三的 `derived7`；其余 6 题今晚新建（`derived8`，6/6 构建成功）。
- **资源**：正式 profile 默认值，2 CPU / 4 GiB / `/tmp` 1 GiB / home 256 MiB，已由 `docker inspect` 回读确认。
- **8 题共同结果**：
  - 预检三项全过：解释器可执行、隐藏测试不可读、HEAD 没有子提交；
  - agent 身份为 uid 54321，`python` 是 `/testbed/.venv/bin/python`；
  - 激活文件对 agent 不可写；
  - 被测包都从 `/testbed` 导入；
  - 容器实际镜像等于覆盖表里的派生镜像 ID；
  - 每次运行后没有残留容器或网络。
- **私有 gold 对照**：用任务二的 [`private_control.py`](../../../../../rh2/experiments/task2_swegym_dev_20260925/private_control.py)。在同一派生镜像起一次性容器，以 root 身份、不联网运行，只应用 gold 的源码段，再执行同一批公开命令。这个容器不交给求解者。
- **证据位置**：本机 `runs/r2e_actor_20260925/devcheck/<题>/{orig,private_gold}/`。
  - `attempt.json`：阶段记录、镜像事实、有效 profile 与逐命令 rc；
  - `captures/*.out`：逐命令输出；
  - `private_gold/private_control.json`：私有 gold 对照结果。

## 2. 逐题结果

"base" 指原条件下经 CC 执行，"gold" 指私有对照。表中 pytest 计数取自输出的汇总行。

| 题 | 入口事实（actor） | 题面原例或公开复现：base → gold | 相关公开测试：base → gold | 开发条件 |
| --- | --- | --- | --- | --- |
| pillow `2b061b68` | Python 3.9；PIL 与已编译的 `_imaging` 在 `/testbed/src`；无 pip；pytest 8.3.4；无图像查看器 | 题面原例：`TypeError`（缺 `formats`）→ `UnidentifiedImageError`。即便用 gold，原例也失败，与题面说法冲突。`hopper.jpg` 配 `formats=['JPEG']`：`TypeError` → 打印 `JPEG`，可区分修复前后 | `Tests/test_image.py`：2 败 52 过 → 相同。失败的两条是 `pytest.warns(None)`，即题面所说的 TypeError | 可开发；公开复现需自写正例；两条死测试恒失败 |
| scrapy `9a15fcf8` | scrapy 1.1.0dev1，从 `/testbed` 导入；无 pip；pytest 8.3.4 | 题面原例：`Response` → `TextResponse` | `tests/test_responsetypes.py`（必须显式给路径）：2 败 5 过 → 相同。`test_from_args`、`test_from_headers` 都报 TypeError | 可开发；两条公开测试在 py3 下恒失败 |
| coveragepy `5dbbe143` | coverage 5.0.2a1，在 `/testbed` 与 `/tmp` 下都从 `/testbed` 导入；有 pip 19.3.1；pytest 4.6.6 | 题面原例：`TypeError`（不认 `once`）→ 通过，但只打印第一条警告。gold 按 slug 去重，题面写的是 "only once each" | `tests/test_api.py`、`tests/test_testing.py` 中带 warn 的：6 过 → 6 过。这些测试不区分修复前后 | 可开发 |
| pandas `32dd55cb` | pandas 从 `/testbed` 导入（版本号带 `.dirty`）；有 pip 24.0；工作区有来源镜像的 versioneer 改写（5 个已跟踪文件） | 题面原例：`ValueError`（sum 不支持 dtype）→ 得到 float64 均值 | `frame/test_analytics.py`：91 过 1 跳 → **1 败 90 过**，失败的恰是 `test_mean_datetimelike_numeric_only_false`；`arrays/integer/test_function.py`：25 过 → 25 过 | 可开发；gold 会让一条公开旧测试失败 |
| orange3 `9b5494e2`（`+env_v2`） | Orange 从 `/testbed` 导入；sklearn 0.22.2.post1，scipy 1.5.4（`+env_v2` 生效）；有 pip 24.0；有 xvfb-run；工作区有未跟踪的 `datasets` | 题面原例：lbfgs 不支持 l1 的 `ValueError` → 输出带新 solver 的模型 | `test_logistic_regression.py`：3 败 → 2 败，gold 下仍失败的是 `test_learner_scorer`、`test_learner_scorer_multiclass`，与期望里仍为 FAILED 的两个键同名；控件测试（Qt）：3 败 → 3 败 | 可开发；有 3 条 Qt 控件测试、2 条 scorer 测试与本题无关，但恒失败 |
| orange3 `22e98f8f` | Orange 与 Cython 扩展在 `/testbed`；numpy 1.17.5；有 pip 24.0；pytest 7.4.4；工作区有未跟踪的 `datasets` | 仓库函数：`[2,3,1]` 的 mapping 为 `[2,0,1]` → `[0,1,2]`（gold 返回 list，base 返回 ndarray）。**题面标为 "Example Buggy Code" 的代码逐字运行，输出的就是正确的 `[0,1,2]`** | 控件测试文件：23 过 3 跳 → 相同；只跑 helper 的用例：1 过 → 1 过。现有公开测试不区分修复前后 | 可开发；题面代码等于修法（执行证实） |
| numpy `18b7cd9d` | 3.7.9，numpy 1.13.0.dev0 从 `/testbed` 导入；nose 1.3.7；无 pip；pytest 7.4.4 | 题面原例：`AttributeError` → `False`。其它入口在 gold 下依次为：`p != None` 得 `True`，`None == p` 得 `False`，`p == 3` 与 `p == [1,2,3]` 都得 `False`，`p.__eq__(None)` 得 `NotImplemented` | `lib/tests/test_regression.py -k poly`：9 过 → 9 过；`test_polynomial.py`：10 过 → 10 过 | 可开发；公开测试不区分修复前后 |
| aiohttp `61833518` | 0.17.0a0 从 `/testbed` 导入；无 pip；pytest 8.3.4；工作区有来源镜像的兼容改写（4 个已跟踪文件，另有一个未跟踪脚本） | 公开读者的 C2：出现空 `transport.write` → 没有空写；C3（chunked 写出器）：正文以终止块开头 → 正常 | `test_http_protocol.py`：47 过 → 47 过；`test_web_response.py` 与 `test_wsgi.py`：3 败 68 过 → 相同（cookie 相关，与本题无关） | 可开发；题面示例的断言按字面写恒为真，需按 C2 取参数；3 条无关失败 |

## 3. 对审查与候选清单的意义

- **执行证据已与静态结论对上的**：
  - pandas：gold 让公开旧测试失败，说明 T2 冲突属实。
  - pillow：原例在 gold 下仍失败，说明题面与目标断言冲突；`pytest.warns(None)` 那两条公开测试是死测试。
  - orange3 `22e98f8f`：题面代码就是修法。
  - coveragepy：gold 按 slug 去重，与题面措辞之间确有落差。
  - scrapy：公开测试文件里那两条在 py3 下恒失败。

  这些都只是开发条件层面的事实，是否构成题目缺陷由各题复核收口。
- **开发条件差异**（写进逐题 actor 说明，不改共同提示）：
  - pip：pandas、coveragepy、orange3 有，pillow、scrapy、numpy、aiohttp 没有；
  - pytest 版本有 8.3.4、7.4.4、4.6.6 三种；
  - pillow、scrapy、orange3 `9b5494e2`、aiohttp 有与本题无关、但恒失败的公开测试；
  - 6 题的相关公开测试区分不了修复前后（pillow、scrapy、coveragepy、orange3 `22e98f8f`、numpy、aiohttp），要靠自写复现。
- **还没有验证的**：
  - 经 Qwen adapter 的链路；
  - 真实模型求解；
  - `generate.py` 的正式 actor 里尚未加入 R2E 预检（本入口是在命令层做的，见[接线说明](../r2e_actor_wiring_20260925.md) §4 第 3 点）；
  - 派生镜像分发到探针机的方式。

## 4. 两道探针候选的事后复核（09-25 上午，按 Codex 复核补齐）

隐藏测试对这两题覆盖不全：已证实有错误或不完整的实现也能得 1。所以探针里得 1 的补丁要再过一道检查。检查结论单独成列，原始 reward 仍以评分账本为准。入口是 [`postcheck/run_postcheck.py`](../../../../../rh2/experiments/r2e_actor_20260925/postcheck/run_postcheck.py)：在派生镜像的一次性容器里（root 身份、不联网）应用候选补丁，再运行对应的检查脚本。

- **numpy `18b7cd9d`**（[`numpy_18b7cd9d_behavior.py`](../../../../../rh2/experiments/r2e_actor_20260925/postcheck/numpy_18b7cd9d_behavior.py)）：逐项检查 12 项，每项单独捕获异常，一项报错不会让后面的项跳过。
  - 检查的范围：与 None、普通对象、标量、系数相同的列表比较；等值的另一个 poly1d；同长不同值、不同长度的 poly1d。
  - 不要求照 gold 返回 NotImplemented。
- **aiohttp `61833518`**（[`aiohttp_61833518_c3.py`](../../../../../rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_61833518_c3.py)）：语义化 C3，3 种载荷，每种检查两个场景。
  - chunked 场景：分块格式完整；终止块恰好一个且在末尾；拼起来按 raw deflate 解压等于原载荷。
  - Content-Length 场景：没有空写入；解压后等于原载荷。
  - 不要求字节等于 gold。解析器自检覆盖了合法的重新分帧、提前终止、空正文、缺终止块。

用已评分的补丁验证（证据 `runs/r2e_actor_20260925/postcheck_validate/`）：

| 题 | 补丁（评分 reward） | 检查结论 | 未通过的项 |
| --- | --- | --- | --- |
| numpy | base（0） | 不通过 | 与 None、对象、标量、列表比较的 7 项 |
| numpy | gold（1） | 通过 | — |
| numpy | A：`__eq__` 对非 poly1d 返回 False（1） | 通过 | — |
| numpy | D：只让 `__eq__` 返回 NotImplemented（0） | 不通过 | `p != None`、`p != object()` |
| numpy | N：只特判 None（1） | **不通过** | 与对象、标量、列表比较 |
| numpy | I：退回身份比较（1） | **不通过** | 等值的另一个 poly1d |
| aiohttp | base（0） | 不通过 | 6 个场景全部 |
| aiohttp | gold（1） | 通过 | — |
| aiohttp | AP1：只修 Content-Length 写出器（1） | **不通过** | 3 个 chunked 场景 |
| aiohttp | AP2：两个写出器都修（1） | 通过 | — |

加粗的是评分给 1、但检查不通过的补丁，也就是这两道题的已知漏测。

## 5. 复跑

从 `rh2/`，在有派生镜像与 CC 平台包的机器上运行。`<题>` 是各题 instance_id，`<overlays.jsonl>` 是覆盖表，`<id>` 是自取的运行标识：

```bash
# 1. 准备任务面（只准备有覆盖条目的题；R2E 任务面缺条目即拒）
.venv/bin/python scripts/replay_grade.py prepare --repo-root <代码根> --out-dir <prepared> --private-dir <private> \
    --sources r2e_gym_subset --task-ids r2e_gym_subset::<题>

# 2. 真实 CC + 桩端点，逐条执行命令清单
SLIME_AGENT_CC_PLATFORM_TARBALL=<claude-code-linux-x64-2.1.205.tgz> .venv/bin/python \
    experiments/r2e_actor_20260925/r2e_devcheck.py --prepared-summary <prepared>/replay_summary.json \
    --overlays <overlays.jsonl> --task <题> --commands experiments/r2e_actor_20260925/commands/<题>.json \
    --out-dir <out> --attempt-id <id>

# 3. 私有 gold 对照（不交给求解者）
.venv/bin/python experiments/task2_swegym_dev_20260925/private_control.py --image <派生镜像ID> --gold <gold.patch> \
    --commands experiments/r2e_actor_20260925/commands/<题>.json --ids <命令id,…> --out <json> --python-prefix /testbed/.venv
```
