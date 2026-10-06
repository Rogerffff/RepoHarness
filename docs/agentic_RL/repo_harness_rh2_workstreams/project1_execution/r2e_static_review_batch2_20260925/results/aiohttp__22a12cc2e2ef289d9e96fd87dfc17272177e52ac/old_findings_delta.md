# 旧结论与本次审查的差异：aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac

- 日期：2026-09-25。R2E 私有主审写于 `analysis_before_history.md` 封存之后。
- 历史引用来自 `runs/r2e_static_prep_20260924/v3/history/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/refs.json`。实际读了：环境审查轮（09-24）的 `screening_record.json`、`findings.md`、`facts.json`（前约 9000 字符），`known_issues.json` 里的两个相关族，`decisions.md`，`results_20260924.md`，`packages/p1/README.md` 中与本题有关的段落，`repros/…py`，`p1/posthoc/…py`，两份 `agent_probe.log`（grep 相关行），以及 `reconcile_all/reconcile.json` 里本题的两行。
- 仍然没有读：首批审查目录、Codex 复核目录、本批 README、`assignments.json`、`grader_candidates.md`。

## 1. 总判断

旧记录是**环境资格审查**：它回答"环境能否支持解题与判分"，结论是 `environment_qualified`，并把题面缺少代理路径这一点作为题面问题移交后续题意筛查。对这些环境与材料事实，我逐项找到了新的独立证据，**全部确认**。

旧记录**没有审查测试强度和替代解**。本次的主要新增是：目标键只检查 mock 交互，一个在现实中什么都没修的实现（K3：去校验连到代理的原始 TCP transport）按推断能拿 1；另外"经代理 + 正确指纹仍能连通"没有任何测试保护。这些不推翻旧的环境结论，但旧记录 R16 标的 `pass` 只成立于"症状对应题面"这一层，不能当作"目标测试足以检验修复"。

我的初判在读历史后**没有改动**：`needs_review`，理由是测试偏弱加题面误导，待 K3 实跑。

## 2. 逐条对照

| 旧主张（出处） | 判定 | 新的决定性证据 | 备注 |
| --- | --- | --- | --- |
| R01：材料一致；派生镜像复核通过；HEAD=`354153e9b706` | 确认 | eval 日志 `RH2_SETUP_HIDDEN_TESTS_TREE=80d242…` 与 `run_refs.json` 一致；devcheck preflight 三项都是 ok；gold 补丁的 index `6bc3ee54` 与公开工作树 `connector.py` 的 blob 相同（我在 scratch 仓库里复算得 `6bc3ee5`） | — |
| R02/R13/R15：noop 0 只错目标键；gold 1（18/18）；两次运行一致；参考日志 5+5 份结果吻合 | 确认 | 我读了两份当前 noop/gold eval 日志的全文与汇总行（sha256 与 `run_refs.json` 一致），以及 M3 gold a1/a2 的汇总行（都是 18 passed）；`reconcile.json` 本题两行列出了参考日志 | 5+5 份参考日志没有逐份打开，只核对了 M3 的两份 |
| R03/R09（issue）：题面没提代理路径；示例 `fingerprint='incorrect_fingerprint'` 会抛 ValueError；直连在 base 上已经会抛异常；经本机 CONNECT 代理不抛，可以离线复现 | **确认，并补了更强的证据** | devcheck 在**正式 actor 启动路径**下以 agent 身份（uid 54321，隔离内网 `rh2acc-…-net`，不是 `--network none`）运行，四个场景的结果是 `direct+bad_fp -> ServerFingerprintMismatch`、`proxy+good_fp -> CONNECTED`、`proxy+bad_fp -> CONNECTED`、`proxy+bad_fp_per_request -> CONNECTED`（`captures/pr4_7_cmd.out`）；私有 gold 对照里两个错误指纹的场景都变成 `ServerFingerprintMismatch`，正确指纹仍连通（`private_control.json`）；示例本身是 `RAISED ValueError fingerprint has invalid length`（`pr2_2_cmd`） | 旧的事后诊断只覆盖连接器级错误指纹、只看 base；新证据补了请求级错误指纹、正确指纹正例和 gold 对照 |
| R04：gold 只改 `aiohttp/connector.py`；解题不需要改测试辅助 | 确认 | gold 补丁全文；隐藏测试只依赖包代码与同名的 conftest（与公开 `tests/conftest.py` 逐字相同，我做了 diff） | 补充：隐藏 conftest 通过 `pytest_plugins` 加载 `aiohttp.pytest_plugin`，这是候选可以改动的包代码，属于同仓共有通道（清单 31，未验证） |
| R05 / 族 `testbed_must_be_on_sys_path`：Python 3.9.21，pytest 8.3.3，pip 24.2；只能从 `/testbed` 导入；装了 trustme | 确认 | devcheck `env`：从 `/testbed` 运行 `python -c` 得到 `aiohttp 3.11.0.dev0 /testbed/aiohttp/__init__.py`，pip 24.2，pytest 8.3.3；`pr0_1` 显示 `trustme`、`proxy`、`pytest_cov`、`aiohappyeyeballs` 都在 | "裸 `pytest` 收集即 ImportError"这一点 devcheck 没有测，没有新证据（未核实，沿用 posthoc3） |
| R06/R11（not_applicable）：期望全部 PASSED；不依赖外部服务 | 确认 | `expected_output.json` 18 个 PASSED；目标测试完全 mock | — |
| R07：隐藏测试不可读；agent 可写 `/testbed` | 确认 | devcheck preflight `RH2_PREFLIGHT_HIDDEN_TESTS=ok`；环境简报 | — |
| R10：无出网；回环可用 | 确认（条件更新） | 旧证据来自 `--network none` 探针；新证据来自正式 actor 的隔离内网（prelaunch：`IFACES=eth0,lo`），回环 TLS 加代理仍然可用 | — |
| R12：峰值约 518 MB / 4 GiB | 确认 | 当前账本 `resource.mem_peak_mb` 在 515–528 之间 | — |
| R14：每次都用新容器，没有缓存残留 | 未核实 | 本次没有重新核对 | 不影响结论 |
| R16（pass）：目标键对应题面"指纹不符不抛异常"，但只在代理路径上成立 | **症状对应确认；"pass"作为测试充分性判断不成立（新增 issue）** | 隐藏测试 `test_1.py:381-479` 用 `mock.patch.object(connector, "_get_fingerprint", return_value=fingerprint_mock)` 替换取指纹，又把 `fingerprint_mock.check` 设成直接抛异常，唯一的断言是 `assertRaises`。所以它不检查被校验的 transport。静态推断：K3（在 `_create_proxy_connection` 里对原始代理 transport 调 `check`）在真实环境中是空操作，因为 `Fingerprint.check` 遇到非 TLS transport 直接 return（`client_reqrep.py:139-141`），但它能让目标键通过 | 旧审查的范围是环境资格，不包括测试强度，所以不算旧审查漏判，是范围之外的新发现；待 K3 实跑确认 |
| R17：无泄漏（HEAD 无子提交，没有补丁残留，派生镜像 `fix_present=no`） | 确认 | devcheck preflight `RH2_PREFLIGHT_GIT_HISTORY=ok`；公开 `CHANGES/` 没有指纹相关片段；公开 `tests/test_proxy.py` 不含新测试 | — |
| issue `solver_condition`：须把 `/testbed` 放进 sys.path，或用 `python -m pytest` | 确认 | 同 R05；v3 环境简报已经写入这一条 | 状态已从 proposed 变为"已写进公开环境说明"（`environment_brief.md:13`） |
| issue `material`（open）：题面没提代理；建议补一句 "including HTTPS requests sent through an HTTP proxy (CONNECT)" 或降权 | 确认，并扩大建议范围 | 同 R03 | 我同意补题面，另外建议修正示例（改成 `ssl=aiohttp.Fingerprint(<32 字节>)`）。单补题面不能解决 K3 类误收，**还需要修订测试**，至少补"真实 `Fingerprint`，transport 带 TLS extras"的负例和一个正例；这些是修订提案，须用户决定 |
| `facts.json` 里 `public_hints_mention_conda: true` | **过时** | v3 公开包的 `public_hints` 已经是 `.venv` 措辞（`public_bundle.json`），环境卡 §2 也这样写 | 旧值基于 v0 的 prompts |
| 旧公开测试选的是 `tests/test_base_protocol.py`（20 passed） | 过时 / 相关性低 | devcheck 跑了与本题相关的公开测试：`test_proxy.py` 17 passed、`test_client_fingerprint.py` 12 passed、`test_connector.py -k …` 10 passed、`test_client_functional.py -k fingerprint` 2 passed | 旧结论"环境支持本地验证"仍然成立，现在有了更相关的证据 |
| 族 `prompt_quality_candidates` 建议的自动检查："题面 Actual Behavior 的报错文本应出现在 noop 目标键的原因行里" | 对本题**不适用**（这个检查查不出本题的问题） | 本题 Actual Behavior 写的是 "No exception is raised"，noop 原因行是 "ServerFingerprintMismatch not raised"，两者一致；本题的问题是缺少触发条件、示例不成立，不是报错文本不符 | 如果要做这类自动检查，建议再加一条"题面示例能否在 base 上原样触发 Actual Behavior" |
| disposition `environment_qualified` | 确认（仅限环境范围） | 以上各行 | 本次静态审查的处置是 `needs_review`，范围不同，两者不矛盾 |

## 3. 我读历史后是否改判

没有改判。历史里没有出现与我初判冲突的事实，只是给同一结论（代理路径缺陷真实、可以离线复现、题面没有点明）补了第三份独立证据：09-24 的 `--network none` 探针，加上我这次引用的正式链 devcheck 和私有 gold 对照。

有两处写法据历史做了细化：
1. 在 card 里写明，环境资格（旧）与题目质量（新）是两个维度；
2. 修订建议在旧的"补一句题面"之外，加上"修测试"，否则题面补好了，reward 仍会误收 K3 类实现。
