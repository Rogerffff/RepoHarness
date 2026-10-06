# aiohttp__4075c653：旧主张对照（old_findings_delta）

- 角色：R2E 私有主审，2026-09-29。本文在 `analysis_before_history.md` 封存之后写。
- 历史来源：`runs/r2e_static_prep_20260924/v3/history/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/refs.json` 列出的 09-23/24 环境审查材料：
  - 本题的 `findings.md`、`screening_record.json`（R01–R20）、`facts.json`；
  - `known_issues.json` 里的 `solver_condition:testbed_must_be_on_sys_path`、`expected_non_passed_keys`、`expected_provenance_mixed` 三族；
  - `packages/p1/README.md` 与 `results_20260924.md` 里涉及本题的行；
  - `repros/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a.py`。
  - `decisions.md` 只按本题编号 grep，没有全文精读。
- 新证据（都在 `runs/r2e_lifecycle_20260929/` 下，新机器，镜像 `sha256:f483bab4…`，配方 `r2e_derive_v1+sysconfig_v1`）：
  - `env_verify/ledger_{noop,gold}.jsonl` 各 L4；
  - `devcheck/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/`（`devcheck.log`、`orig/captures/*.out`、`private_control.json`）；
  - `inv/aiohttp_4075/ledger_{DG1,ALT1}.jsonl` L1 及日志；
  - `inv/aiohttp_4075/pcheck_matrix_{none,gold,DG1,ALT1}.json`。
- 范围说明：旧审查只看**环境资格**（环境能否解题、能否判分），没有评估测试强度与 gold 的语义完整性。所以本卡新增的 S1 与旧主张并不矛盾，是旧审查范围之外的新结论。

## 1. 逐条对照

| # | 旧主张（出处） | 判定 | 决定性证据 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 环境支持解题与判分；解题侧条件是"/testbed 须在 sys.path 上"（findings L3；known_issues 同族） | **确认** | 新机 devcheck 以 agent（uid 54321）身份走正式启动链：在 `/testbed` 下 `python -c`、`python -m pytest` 都正常，`aiohttp` 从 `/testbed/aiohttp/__init__.py` 导入（`orig/captures/env.out`）；新机 noop 0、gold 1 | 镜像与配方已换成新版本，结论照样成立。"从 /tmp 导入会失败"本轮没有复测 |
| 2 | R-f：noop 0，失败的只有两个目标键；gold 1（129/129），入口 rc=1 属正常（findings L6；R02、R08、R13） | **确认**（新机复验） | `env_verify/ledger_noop.jsonl` L4：127/129，mismatched 就是那两个目标键；`ledger_gold.jsonl` L4：129/129；两次 test rc 都是 1 | 旧镜像 `0d785442…` 的证据由新版本证据取代 |
| 3 | R06：3 个期望 FAILED 键是因为 C 解析器扩展没有构建（findings L7；R06） | **确认** | 新机 gold、DG1、ALT1 的日志里这 3 个键都失败，原因不变（DG1/ALT1 日志 L472-474）；devcheck 输出 `c_parser_available False`、`no aiohttp/*.so` | 补充：ALT1 这类比 gold 更严的修复实跑仍是 129/129，所以正确修复不会翻转这 3 个键；只有改动扩展检测或构建出 `.so` 的候选会翻转 |
| 4 | 期望的来源不统一：来源宿主机记录里这三键是 PASSED，共 230 个用例（findings L8；`expected_provenance_mixed`） | **未核实** | 本轮没读来源宿主机记录 | 与本卡结论无关。另外旧文档里这个差异有两个数：findings/p1 README 写"差 104 键"，known_issues 的 next 写"103 键"，属于引用笔误级的不一致 |
| 5 | 探针：公开测试 20/20 通过（R09，用的是 `tests/test_base_protocol.py`） | **过时** | 那个文件与本题无关。新 devcheck 跑的是与本题相关的公开测试：`tests/test_http_parser.py` 在设 `AIOHTTP_NO_EXTENSIONS=1` 后 124 passed / 5 skipped；另外三个相关文件 135 passed（`orig/captures/public_*.out`）。gold 下结果相同（`private_control.json`） | — |
| 6 | 公开复现：纯 Python 解析器对两段输入都不报错，`REPRO_OBSERVED=1`（findings L9；R09） | **确认** | devcheck `repro_parser_issue_cases` 打印 FAILS 2；在公开 API 层，服务端对两例都返回 `HTTP/1.1 200 OK`（`repro_server_400_py_parser.out`） | 新增的是公开 API 层的复现 |
| 7 | R03：题面对两种输入的描述准确；例 1 把 bytes 嵌进 f-string 是笔误，按意图就能复现 | **部分确认，需修正** | devcheck 的 `issue_ex1_literal` 一行显示：字面写法在 base 上**已经**抛 `InvalidHeader`。所以对字面的例 1，题面 "No exceptions are raised" 不成立 | 我记为 P4（误导，但题面 L22 的文字能消解），不再算"描述准确"的 pass。可选 R-f，证据已经齐 |
| 8 | R03 附注：公开提示里的 conda 措辞是全局问题（E09） | **过时（已修）** | 当前 `PUB/public_bundle.json` L15 的 `public_hints` 已经是 `.venv` 的说法 | — |
| 9 | R16：两个目标键对应题面的两段示例 | **确认，另有新结论** | 对应关系不变。新发现：<br>- 两个键**只**用了示例的字面值（T2c）；<br>- 退化候选 DG1 实跑 1.0、129/129（`inv/aiohttp_4075/ledger_DG1.jsonl` L1）；<br>- 私有矩阵里，DG1 会接受西里尔字母字段名、`\xe9` 字段名、用 VT/TAB 分隔的请求行 | 旧审查不评估测试强度，所以这不是推翻旧结论 |
| 10 | 处置为 `environment_qualified`（screening_record disposition） | **过时**（作为用途结论） | v1 §2 把环境资格与训练资格分开记。环境条件在新机依然成立，但测试层有 S1，本卡改为 `needs_repair` | 旧状态里的环境事实仍然有效 |
| 11 | 风险：如果以后的派生配方改成构建 C 扩展，这 3 个 FAILED 键会翻转，期望要同步修订（findings L13；R20） | **确认**（仍有效） | 当前配方没有构建扩展（devcheck） | — |
| 12 | 风险：解题者如果在工作区建出 `.so`，评分 delta 是否带上二进制新文件未验证；带上的话 3 键会翻转（findings L14；p1 README L82） | **未核实**（可能性低） | 要建扩展需要 `vendor/llhttp/build/c/llhttp.c` 等源码（`WT/setup.py` L29-42），公开工作树里 `vendor/llhttp` 是空子模块；重建还需要 npm（`WT/vendor/README.rst` L7-21），而环境不联网。镜像里 `vendor/llhttp` 的实际内容没查 | 探针分析时如果看到候选构建了扩展，按 T5 解释它的 0 分，不算模型把修复改错 |
| 13 | 解题侧条件：有 pip 23.2.1；不联网，但回环接口可用（solver_conditions） | **确认** | devcheck env 显示 pip 23.2.1；在正式 profile 下，服务端复现能在回环端口上监听并收到响应 | — |
| 14 | R04：gold 只改 `aiohttp/http_parser.py`；基线里的脏改动不会卷进候选补丁（代码阅读，未经真实 rollout） | **部分确认** | 新机 gold、DG1、ALT1 的正式评分投影 `included_paths` 都是 `["aiohttp/http_parser.py"]` | 走的仍是 replay 路径，不是真实 rollout 的导出 |
| 15 | R12：内存峰值 435 MB，测试约 5 秒 | **确认**（新机数值不同） | 新机峰值约 438 MB；测试段 12–14 秒；trusted setup 81–101 秒，新机器更慢（各账本的 `phases`） | 只是时长变化，不影响结论 |
| 16 | R17：没有未来提交，没有修复痕迹 | **确认** | devcheck 的 git_sanitize：REFS 0、REMOTES 0、REFLOG 0，HEAD 不变；r2e_preflight 输出 `GIT_HISTORY=ok` | 镜像里 `git log` 能看到 base 之前的相关修复（#7720，Py 解析器 Unicode 问题），这是公开历史，不是本题答案 |

## 2. 主审自己改判或补强的地方

- **I3（T2b）：从"预测"改为"已确认"。** DG1 正式评分 1.0（129/129）。投影里有 `aiohttp/http_parser.py`，129 个键全部解析，测试段正常结束，所以这是有效的"错误解得 1"。私有矩阵给出了它违反公开要求的具体输入：字段名 `f\xd0\xbeo`、`f\xe9o` 被接受；请求行 `GET\x0b/path HTTP/1.1`、`GET\t/path HTTP/1.1` 被当成 `GET /path` 接受。
- **I4（第 4 步）：从 conditional 改为 S1 成立。**
  - 私有矩阵实证：请求目标里夹 LF、FF、CR、TAB 时，base 都抛 `BadStatusLine`，gold 全部接受，例如 `('GET', '/pa\nth', [])`。
  - 因此 R-c #3 从"视复核而定"改为**必做**（仍要经 Codex 复核），并新增 ALT2（gold 加一个请求行控制字符检查）作为最小的 D4 正对照。
  - 依据与"不因保 gold 而放宽"的理由见 `card.md` 附录 G。
- **ALT1 比 gold 更严的地方**：字段名里的 `/`、请求目标里的 `\x01`、版本号里的 FF。我逐条判断过，与 R-c 的断言和公开回归都不冲突（`card.md` 附录 H）。这几处仍按 T3 登记，不进修订。
- **R-c #1 的写法**：参数改用 `pytest.param(..., id="nonascii-mid-name")` 给出显式 id，免得键名里出现 pytest 对非 ASCII 字符的转义。断言内容不变。
- **读历史前的结论没有被推翻。** 历史材料与新运行只确认或补强了原判断。
