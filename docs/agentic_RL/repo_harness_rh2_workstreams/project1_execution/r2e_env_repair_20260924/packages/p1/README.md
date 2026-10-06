# P1 包报告：aiohttp ×5、coveragepy ×5（R2E 环境审查第一轮）

2026-09-24（远端 UTC 09-23 18:15–19:00）/ P1 sub-agent。状态词：**已实施**＝做了；**已验证**＝有运行证据；**建议**＝待主会话 / 用户决定。
本包没有改共享文件（本目录 README、decisions、known_issues、dispositions、recipes）、`s2_r2e/`、expected / gold / 隐藏测试、`rh2/src`、`rh2/scripts`、镜像，也没碰远端 `/work/replay`、`/work/r2e_derived`、`/work/code` 与中央复跑 `/work/envrepair/_rerun2/`。

## 1. 逐题结论

"unknown（只差 R13）"＝R01 / R02 / R08 / R15 pass、探针十项最小条件满足、issue 都已归因，只是同条件下 R-f 只跑过一次；中央复跑并入后若逐键一致即 `environment_qualified`（记录里有 `pending_checks: ["R13"]`）。

| 题 | 分类 | 处置 | 关键 issue | 证据（逐题记录 + 探针） |
| --- | --- | --- | --- | --- |
| aiohttp `1c1c0ea3` | solver_condition | unknown（只差 R13） | 导入需 cwd=/testbed、裸 `pytest` 收集即 ImportError；`TestShutdown.test_shutdown_handler_cancellation_suppressed` 有时序敏感嫌疑（来源宿主机新旧提交都 FAILED、期望 PASSED、我们实测 PASSED） | [record](../../tasks/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/screening_record.json)；`runs/r2e_env_repair_20260924/p1/dev_probe/aiohttp__1c1c…/` |
| aiohttp `22a12cc2` | solver_condition | unknown（只差 R13） | 同上的导入条件；**公开题面没点明缺陷在"经 HTTP 代理 CONNECT 的 HTTPS"路径**，照题面复现不出（R03 / R09 issue）；事后诊断证明沙箱可离线复现真实缺陷 | [record](../../tasks/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/screening_record.json)；`…/dev_probe_posthoc/aiohttp__22a12cc2…/` |
| aiohttp `240da100` | solver_condition | **environment_qualified** | 导入条件；venv 无 pip；Python 3.9 跑 2014 年代码 + 来源镜像 `create_task(loop=)` 改写无效 → 真实客户端 / 服务端不可用、`tests/test_client.py` 收集 SyntaxError；期望 2 个 FAILED 键＝上游在 3.9 上本就失败 | [record](../../tasks/aiohttp__240da100151933883d7dea0528d45877df025b92/screening_record.json)；`…/dev_probe_posthoc2/aiohttp__240da100…/` |
| aiohttp `4075c653` | solver_condition | unknown（只差 R13） | 导入条件；期望 3 个 FAILED 键＝C 解析器扩展未构建（镜像属性；与来源宿主机记录不同） | [record](../../tasks/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/screening_record.json) |
| aiohttp `61833518` | solver_condition | unknown（只差 R13） | 导入条件；venv 无 pip；`create_task(loop=)` 改写使 `tests/test_client_functional.py` 基本全挂（相关的 `tests/test_http_protocol.py` 47/47 通过） | [record](../../tasks/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/screening_record.json)；`…/dev_probe_posthoc2/aiohttp__61833518…/` |
| coveragepy `016af5f6` | **material** | **held_material** | 期望 `MockingProtectionTest.test_os_path_exists=FAILED` 来自来源宿主机检出（子进程缺 `mock`）；发布镜像 13/13 PASSED → gold 恒 0；已写提案 | [record](../../tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/screening_record.json)；[提案](../../material_revisions/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae.md) |
| coveragepy `5dbbe143` | env_ok | unknown（只差 R13） | — | [record](../../tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/screening_record.json) |
| coveragepy `97997d2c` | env_ok | unknown（只差 R13） | — | [record](../../tasks/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/screening_record.json) |
| coveragepy `ea6906b0` | solver_condition | unknown（只差 R13） | venv 无 pip（本包 coveragepy 里唯一） | [record](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/screening_record.json) |
| coveragepy `f5eb5f21` | env_ok | unknown（只差 R13） | — | [record](../../tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/screening_record.json) |

`check_records.py` 对本包 10 题：0 个问题（rc 0）。

## 2. 已实施 / 已验证

- **公开复现脚本 10 个**（`repros/<iid>.py`，只据公开题面与公开工作区源码；写完后才读隐藏测试、gold 日志与来源执行记录）。探针 `r2e-p1-probe-1828` 跑 10 题：十项最小条件 10/10，`REPRO_RC` 全 0；9 题 `REPRO_OBSERVED=1`，aiohttp `22a12cc2` 为 0（题面问题，见 §3.4）。**已验证**。
- **事后诊断 3 轮**（不是公开复现；同一探针工具换 `--repro-dir`，脚本在 `runs/r2e_env_repair_20260924/p1/posthoc*/`）：
  - posthoc（unit 1837）：`22a12cc2` 同一错误指纹直连抛 `ServerFingerprintMismatch`、经本机 CONNECT 代理不抛（status 200）；旧 aiohttp 两题的公开测试。
  - posthoc2（unit 1841，修正 v1 只打印 6 行根因、把告警行当汇总行的问题）：`240da100` `tests/test_connector.py` 30 passed / 2 failed、`tests/test_client.py` SyntaxError；`61833518` `tests/test_http_protocol.py` 47/47、`test_client_functional.py` 因 `create_task() got an unexpected keyword argument 'loop'` 大面积失败。
  - posthoc3（unit 1856）：aiohttp 4 题（`1c1c0ea3` `22a12cc2` `240da100` `61833518`）上 `python -m pytest` 收集正常，**裸 `pytest` 收集即 ImportError**（3.x rc 4：加载 `tests/conftest.py` 失败；0.x rc 2），`PYTHONPATH=/testbed` 两者都正常；`/tmp` 下脚本不加 PYTHONPATH 导入失败。
- **R06 逐键归因**（期望含 FAILED 键的 3 题）：`240da100` 2 键＝上游在 Python 3.9 上本就失败；`4075c653` 3 键＝缺可选编译扩展（C 解析器）；`016af5f6` 1 键＝来源参考环境差异。均有 gold 日志原因行 + 来源执行记录对照。**已验证**（日志证据）。
- **材料修订提案 1 份**：`016af5f6`（§3.1）。**建议**。
- **逐题记录** 10 份 `screening_record.json` + `findings.md`。**已实施**，机械核对通过。

## 3. 本包提案清单（建议）

### 3.1 材料修订（T0，用户决定）

- coveragepy `016af5f6`：[提案](../../material_revisions/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae.md)。推荐方案 A——该题 `expected_v1` 把 `MockingProtectionTest.test_os_path_exists` 改为 PASSED（预计 gold 15/15、noop 只剩目标键不符）。只删期望键**不可行**：grader 要求观测键集＝期望键集（`envpack/scoring.py`），删了会变 unexpected 仍得 0；要"移出评分"就得改隐藏测试或 grader。

### 3.2 解题侧条件（E10；建议写进题包 / 系统提示，由任务面决定）

| 条件 | 适用题 | 证据 |
| --- | --- | --- |
| 包没装进 venv：cwd 必须是 /testbed；跑测试用 `python -m pytest`（裸 `pytest` 收集即 ImportError）；/testbed 外的脚本要 `sys.path.insert(0, "/testbed")` 或 `PYTHONPATH=/testbed` | aiohttp ×5（4 题实测，`4075c653` 同一 install.sh 未单测） | 探针 `IMPORT_FROM_TMP_RC=1`；posthoc3；M3 `pkgsrc.txt` |
| venv 无 pip（uv 也不在 PATH），也无网络：不能装包 | aiohttp `240da100` `61833518`；coveragepy `ea6906b0` | 探针 `PIP_VERSION` |
| Python 3.9 上的旧 aiohttp：真实 HTTP 客户端 / 服务端不可用；只跑题目相关模块、用 mock 验证；`pytest tests/` 整目录会被 `test_client.py` 的收集错误中断（`240da100`） | aiohttp `240da100`（`tests/test_connector.py`）、`61833518`（`tests/test_http_protocol.py`） | posthoc / posthoc2 |
| 无网络；`--network none` 保留回环（`22a12cc2` 事后诊断实测可在 127.0.0.1 起 TLS 服务与代理） | 全部 | 探针 `NET_CONNECT_RC`；posthoc |

### 3.3 资源

无。10 题 gold 峰值 171–518 MB / 4 GiB；R-f setup 6–45 s、测试 1–32 s；默认 profile 足够。

### 3.4 其它（不属环境资格，交后续环节）

- aiohttp `22a12cc2` 公开题面完整性：目标测试 `TestProxy.test_https_connect_fingerprint_mismatch` 是代理路径，题面只说 HTTPS + 指纹、示例是直连（在 base 上已正确抛异常），示例里的指纹字符串在此版本直接 ValueError。建议交题意筛查（清单 §6）决定补一句题面或降权；本轮不改。
- aiohttp `1c1c0ea3` 时序敏感嫌疑键：请中央复跑（R13）专门看 `TestShutdown.test_shutdown_handler_cancellation_suppressed`。
- 来源镜像的 `asyncio.async → create_task(loop=)` 改写（aiohttp 0.x 两题）：**不建议**修——会改基线代码，`240da100` 的期望 FAILED 键语义随之改变，属材料修订；且不影响本池判分。

### 3.5 请主会话合并到共享文件的内容（建议）

- `known_issues.json`：
  - `reference_status:coveragepy_016af5f6` → `proposed`；证据补 `s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl`（该题 `execution_result_content`）与提案文件；summary 更正为"RH2 与 M3 独立 runner"（09-09 runner 没跑这题）。
  - `solver_condition:import_requires_cwd_testbed`：aiohttp 5 题由探针确认（`IMPORT_FROM_TMP_RC=1`）；补"裸 `pytest` 收集即 ImportError、`python -m pytest` / `PYTHONPATH=/testbed` 正常"（posthoc3）。
  - `solver_condition:no_pip_in_venv`：P1 枚举＝aiohttp `240da100`、`61833518`，coveragepy `ea6906b0`；其余 7 题有 pip。
  - `expected_non_passed_keys`：P1 三题已归因（见 §2）。
  - 新族 `source_image_compat_rewrite:aiohttp_0x`（`240da100`、`61833518`；solver_condition，状态 `verified`）。
  - 新族 `expected_provenance_mixed`（global，`open`）：期望与来源宿主机执行记录逐键相同的有 `016af5f6` `240da100` 等；`4075c653` 差 104 键（宿主机建了 C 扩展）、`1c1c0ea3` 差 1 键——期望来源不统一，不能假设"期望＝宿主机记录"或"期望＝镜像"。
  - 新族 `timing_sensitive_key_watch`（`1c1c0ea3`，`open`，等中央复跑）。
- `decisions.md` 待用户决定（T0）：`016af5f6` 期望修订（选项 A / B / C，推荐 A）。
- `dispositions.json`：`016af5f6` → `held_material`（等待 E05 决定）。
- `README.md` §9 / 派发说明：`016af5f6` 的"两个独立 runner（M3、09-09）"应为"M3（多个阶段）"。

## 4. 未解决项

| 项 | 原因 / 缺什么 |
| --- | --- |
| 8 题 R13 | 同条件只有 R-f 一次运行；按派发说明不等中央复跑，由主会话并入 |
| `016af5f6` 期望修订 | T0，等用户决定 |
| `22a12cc2` 题面 | 属题意筛查，本轮不改 |
| `4075c653`：解题者本地建出 C 扩展 `.so` 时评分 delta 是否带上二进制新文件 | 未验证（离线能否构建也未验证）；若带上，3 个期望 FAILED 键会翻转 |
| 来源镜像既有脏改动不会卷进候选补丁 | 只有代码阅读（`generate.py` / `replay_grade.py` 都用 `FrozenDeltaSource` 按基线 census 求 delta），未经真实 rollout 验证；归 A 线 |
| `1c1c0ea3` 时序敏感嫌疑键 | 等中央复跑数据 |

## 5. 远端产物与本地回传

远端 `/work/envrepair/p1/` 与本地 `runs/r2e_env_repair_20260924/p1/` 逐文件 sha256 一致（103 个文件，652 KB）。

| 路径 | 内容 |
| --- | --- |
| `repros/` | 10 个公开复现脚本（副本；仓库内正本在本目录 `repros/`） |
| `dev_probe/`（unit `r2e-p1-probe-1828`，日志 `logs/probe_1828.log`） | 10 题 `dev_probe.json` / `agent_probe.log` / `root_init.log` / `container.json` + `summary.json` |
| `posthoc/` + `dev_probe_posthoc/`（unit 1837） | `22a12cc2` 代理路径诊断；`240da100` / `61833518` 公开测试 v1 |
| `posthoc2/` + `dev_probe_posthoc2/`（unit 1841） | 公开测试汇总 v2（`240da100`、`61833518`） |
| `posthoc3/` + `dev_probe_posthoc3/`（unit 1856） | `python -m pytest` vs 裸 `pytest` vs PYTHONPATH（aiohttp 4 题） |

另外用 `docker run --rm --network none` 起过 18 个一次性只读容器（名 `rh2-p1-peek-*`）读公开工作区源码、install.sh、缓存目录；全部随退出删除。
收尾检查：`docker ps -a` 无 `rh2-devprobe-<P1 题>*` 与 `rh2-p1-*` 容器；远端 `df -h /` 可用 42 GB（开工时 46 GB，其余包与中央复跑同时在跑）。没有启动复跑（本包没有改变条件的题）。

## 6. 耗时

- 远端墙钟约 45 min（18:15–19:00 UTC）。探针容器合计 749 s：主探针 424 s（10 题，12–80 s / 题，其中 `chown -R /testbed` 7–60 s）；posthoc 110 s、posthoc2 33 s、posthoc3 182 s。
- aiohttp 3.x 三题的 `chown` 55–60 s，coveragepy 22–36 s——比 5 题试跑（coveragepy 11 s）慢一倍，与 4 包 + 中央复跑并发有关，不作校准（E08）。

## 7. 对流程 / 工具的改进建议

1. **探针丢字段**：`run_dev_probe.py` 的 `_KV_RE = ^[A-Z][A-Z0-9_]*=` 不认小写，`WHICH_python / WHICH_pip / WHICH_gcc / WHICH_make / WHICH_xvfb-run` 全被丢掉，`dev_probe.json` 里没有，只能回看 `agent_probe.log`。建议正则放宽到 `^[A-Z][A-Za-z0-9_-]*=`，或在 agent 脚本里把键名转大写。
2. **公开测试只取字母序第一个文件**：旧 aiohttp 两题分别取到 `tests/test_client.py`（SyntaxError）与 `tests/test_client_functional.py`（被镜像改写弄坏），和题目无关。建议允许 sub-agent 在 `repros/<iid>.tests` 里列要跑的公开模块（只列公开 `tests/` 下的文件，不泄漏隐藏测试）。
3. **`PUBLIC_*_TAIL` 只留 3 行、`REPRO_OUTPUT` 只留末 40 行**：分不清收集失败是 conftest / 插件 / 依赖还是源码语法（R09 要求区分），`61833518` 的长输出也被截断。建议记"汇总行 + 前几条 `E …Error` 根因行 + FAILED/ERROR 列表"（posthoc2 脚本的做法），`REPRO_OUTPUT` 改成头 20 + 尾 40。
4. **加一个"裸 `pytest`"检查**：cwd-only 仓库里 `python -m pytest` 正常而裸 `pytest` 失败，是解题者最常碰到的坑；探针现在只测 `python -m pytest`。
5. **复现脚本的 sys.path**：探针以 `python /rh2/repro.py` 运行，`sys.path[0]` 是 `/rh2` 而不是 cwd；cwd-only 仓库的脚本必须自己补 sys.path（P1 的脚本都做了，并把"是否需要补"打印成 `REPRO_IMPORT=`，正好当解题侧证据）。建议写进 `repros/README.md`。
6. **E06 先后与 facts.json**：派发要求先读 facts.json，而它含期望键名与 gold 触碰路径，严格说与"写脚本前不读期望映射"冲突。本包按派发顺序做，并在每题 findings 注明先后；建议给复现环节准备一个去掉期望键与 gold 路径的 facts 视图。
7. **期望来源比对进汇总器**：`collate_facts.py` 可以解析 raw `execution_result_content` 的新提交状态，与期望、与发布镜像 gold 实测三方比对，自动标出"期望＝宿主机记录≠镜像"（`016af5f6` 这类）与"期望≠宿主机记录"（`4075c653` 这类）的键——只标候选，逐键人工归因。
8. **派发说明的一处事实错误**：`016af5f6` 没有 09-09 runner 的运行（见 §3.5）。

说明：本包写复现脚本后做语法自检时，`py_compile` 顺带编译了 `repros/` 里其它包的脚本（只生成 `__pycache__`，随即删除，源文件未改、修改时间早于本包写入）。
