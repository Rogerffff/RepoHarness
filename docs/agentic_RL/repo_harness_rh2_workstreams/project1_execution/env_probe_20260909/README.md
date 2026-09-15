# x86 环境探针执行报告（2026-09-09 夜间，B 线）

> **后续独立核查（Codex，2026-09-09）：** 请同时阅读 [远端核查与补充](codex_remote_check_20260909.md)。本页保留 01:10 UTC 的作者报告；其中 Prime 去色归因、R2E 七题 gold 差异解释、¥38 总费用、Git 清理覆盖范围以及“探针等价于 rh2”的推断已被后续证据更正。R2E 最终 144 次结果经固定官方函数重放仍全部一致，DeepSeek 13/24 的观察保留。原始工件已补充备份；追加重复新发现 MONAI-763 共享内存故障，详见核查稿。

> **24 题语义审查补充：** [可解性与评分信号审查](solvability_review_20260909/README.md)确认全部轨迹有 API 返回的 thinking；13/10/1 原始分数中同时存在评分假阴性、覆盖不足、题意范围分歧和三题实际访问上游答案，因此不能当独立解题准确率。Pydantic-5706 官方漏测旧行为失败，Pydantic-8500 官方用例没有覆盖题面原例。另撤回本页“MONAI-6975 mutation 证明只约束一半修复”的解释：被删除的末 hunk 仅是 docstring，mutation 保留了完整功能修复。详见新稿及逐题证据。

状态：**夜间执行报告（2026-09-09 01:10 UTC 版）**。SWE-Gym 216 题 pass 1、核心 12 题四组变体、R2E 24 题、DeepSeek 参考求解均已完成；216 题 pass 2（追加重复到 N=3）仍在实例上跑，末尾"本轮状态"一节说明。作者：Claude（B 线）。所有结论都是探针事实与建议，没有新增任何评分/训练规则或批准。用户授权：租用 vast.ai x86 实例、使用 DeepSeek key 做参考求解探针、docker hub 个人 token；实验安排由 Claude 决定。

runner 代码在 `rh2/experiments/env_probe_20260909/`（`swegym_probe.py`、`r2e_probe.py`、`cc_probe.py`、`summarize.py`），未跟踪、未提交，不改 rh2 包。账本与日志在实例 `/work/ledger/`，收尾时复制到本目录 `ledger/`。

## 1. 机器与准备

| 项 | 值 |
| --- | --- |
| 实例 | vast.ai m:18856（offer 49819482），Quebec，VM 镜像 Ubuntu 22.04.5，Docker 28.1.1 预装 |
| 资源 | 19 vCPU（Xeon E5-2673 v4）、VM 内可见 49 GB 内存、600 GB 盘（起步空闲 573 GB）、下行约 2.6 Gbps |
| 价格 | $0.176/h（含 600 GB 盘），起租时账户信用 $6.15 |
| 评分 oracle | 官方 SWE-Gym fork `SWE-Gym/SWE-Bench-Fork@242429c1` 作库安装在 `/work/venv`；`make_test_spec` 生成官方 eval 脚本、`MAP_REPO_TO_PARSER` 解析、`get_eval_tests_report` 判定 |
| 数据 | 216 题三份 bundle + 11 列原始行 + 键控镜像清单（本地 s2 产物 rsync 过去）；R2E 24 题从 HF 冻结 revision `e8b9fcb…` 拉全字段 |
| Claude Code | 2.1.205（rh2 pin），Node v22.23.2，打成 `/work/ccbundle`（449 MB）复制进容器 |
| DeepSeek | Anthropic 兼容端点，`deepseek-v4-pro`；起步余额 ¥55.32 |

## 2. 租机前在本机完成的对照（无 Docker）

对 216 题用官方 fork 生成 eval 脚本并与 rh2 评分 bundle 的 `eval_cmd` 逐题对照（[official_cmd_contract_216.json](../B_materials_20260908/official_cmd_contract_216.json)）：

| 对照项 | 题数 |
| --- | ---: |
| rh2 `eval_cmd` 是官方测试命令前缀 | 216 / 216 |
| mypy `-k "<case> or <case>"` 表达式（rh2 bundle 无） | 40 |
| conan `eval_commands`（`export PYTHONPATH=…:$(pwd)`，rh2 bundle 无） | 12 |
| 官方脚本在测试前执行 install 步（按 `specs["install"]` 精确匹配） | **216 / 216** |

## 3. 已确认的环境事实（SWE-Gym 12 题核心批 + R2E 6–24 题）

### 3.1 SWE-Gym 镜像

| 事实 | 观测 | 含义 |
| --- | --- | --- |
| 镜像 digest | 12/12 与键控清单一致，`amd64/linux` | 拉到的就是冻结的那份 |
| HEAD == base_commit | 12/12 | 工作区初始状态正确 |
| git 版本 | 2.34.1（全部） | **官方 run_instance 的 `git apply --allow-empty` 在此版本不存在该选项 → 必然退到 `patch --batch --fuzz=5 -p1`**。gold 补丁 `git apply --check` 全部通过，所以退路只是因为选项，但这意味着"官方评分在这些镜像上一直是 fuzz=5 宽松应用"。rh2 的 frozen delta 写入不是 patch 语义，两者对错位补丁的接受范围不同，需要在对账时记录 |
| 未来 git 历史 | remotes=0，但 tags 94–320，**base 之后仍可达的提交 749–2150**（含修复提交所在历史） | 求解容器必须先做 rh2 的 git-sanitize；探针已验证脚本可用（见 §5） |
| 不可达对象 | 62–37,809 | 同上，`git fsck` 可见 |
| 默认网络 | `pypi.org` 可达（200） | 官方 install 步在线可完成；rh2 grader 是 deny_all，见 §4 |
| `agent` 用户 | 不存在 | rh2 沙箱自建；探针同样自建 54321 |
| 包导入位置 | 11/12 从 `/testbed/<pkg>/__init__.py` 导入（editable）；**conan 例外**：`import conans` 在 /tmp 下失败，依赖官方 `eval_commands` 的 `PYTHONPATH=$(pwd)` | 纯 Python 修改无需重装即可生效；**conan 12 题若不执行 `eval_commands`，测试会因 import 失败整体报错（假阴性）** |
| 根目录控制文件 | conftest/pytest.ini/setup.cfg/pyproject/tox 存在情况逐题记录 | 供 Wave3 控制面定义 |

### 3.2 R2E 镜像（aiohttp、coveragepy、datalad、scrapy、numpy×2 已核）

| 事实 | 观测 |
| --- | --- |
| HEAD 是修复提交的父提交 | 6/6 yes |
| **修复提交在 git 历史中可达**（`git cat-file -t <commit_hash>` = commit） | 6/6 |
| remotes / tags / HEAD 之后可达提交 | 1 / 119–289 / 2,280–27,031 |
| 工作区脏文件行数 | 2–7（镜像自带未提交改动/未跟踪文件，需要在 rh2 ingestion 时核对是哪些） |
| 解释器 | `/testbed/.venv/bin/python`（3.7.9 或 3.9.21） |
| 隐藏测试 | `/r2e_tests/`（根目录）；`/testbed/run_tests.sh` 运行 `r2e_tests`，评分前须复制到 `/testbed/r2e_tests` |
| 容器内无 `expected_test_output.json` | 预期映射只在数据行 `expected_output_json` |

## 4. 门结果

### 4.1 SWE-Gym 核心 12 题（default 变体：官方脚本原样、默认网络、root；empty/gold 各 N=3）

| 结果 | 题数 | 说明 |
| --- | ---: | --- |
| empty ×3 全部正确 NO | 12 / 12 | 每次 ≥1 个 F2P 失败，测试真跑，parser 解析非空 |
| gold ×3 全部 RESOLVED_FULL 且严格判定通过 | 10 / 12 | 全部参考 case 出现、无 SKIPPED/MISSING/XFAIL |
| gold ×3 全部 RESOLVED_NO | 2 / 12 | modin-6937（P2P 含依赖 S3 服务的测试）、pandas-48106（参考 ID 与日志不匹配，见下） |
| 三次重复判定不一致 | 0 | 官方判定 + 严格判定 + 逐 F2P 状态 + P2P 失败数完全一致 |

**第二个真实反例：pandas-48106 gold ×3 全部 RESOLVED_NO，但测试全通过（1044 passed）。** 参考 P2P 里有 3 个 ID 是 `test_contains_raise_error_if_period_index_is_in_multi_index[Period\('2017',`（在第一个空格处被截断，且带一个反斜杠），本镜像里 pytest 打出来的是 `[Period\\('2019', 'A-DEC'\\), 'foo', 'bar'-key0]`（两个反斜杠），官方 parser 按空格截断后得到 `[Period\\('2019',`，与参考键的反斜杠数不同 → 3 个 P2P 永远 MISSING → 任何补丁都得不到 FULL。同时一个年份下 4 个参数化 case 截断后塌成同一个键（后者覆盖前者）。对 216 题的静态扫描：参考 ID 含反斜杠的 8 题（dask-10972、dask-6818、dvc-4185、modin-5940、modin-6780、modin-6937、pandas-48106、pandas-50319），参数被截断的 8 题（dask-10972、dask-6818、moto-6178、dvc-4166、modin-5940、modin-6937、pandas-48106、pandas-56849），合计 11 个不同任务处于"参考 ID 脆弱"风险；216 全量 gold 结果会给出实际影响数。这正是 O04 §7.5 预言的"参数化名截断 + 规范化规则"问题，在真实镜像里发生了。

探针层（批次 B）：无关文件补丁 12/12 正确不通过；删末 hunk 变异 11 题 rejected，**MONAI-6975 为 suspicious_pass**：gold 两个 hunk，只保留第一个（`lazy` 默认值 False→None）即可让 F2P 通过，第二个 hunk 对参考测试不可见。这不是评分器错误，而是"测试只约束了一半修复"的题级事实，进人工复核清单。

每仓库单次耗时（校准记录，秒）：

| 仓库 | install 步 | 测试 | 单次总耗时 | 备注 |
| --- | ---: | ---: | ---: | --- |
| python/mypy | 7.9 | 3.5 | 15.5 | `-k` 表达式选中 2 个 case |
| conan-io/conan | 2.7 | 1.3 | 8 | `eval_commands` 设 PYTHONPATH |
| pydantic/pydantic | **76–79** | 4.2 | 86–88 | `pdm add pre-commit; make install` 在线；离线行为见 §7 |
| Project-MONAI/MONAI | 9.7 | 17 | 31 | |
| dask/dask | 2.6–4.3 | 5–6 | 12–14 | |
| getmoto/moto | 11–12 | 4.4–4.9 | 20.8 | `make init` |
| iterative/dvc | 21–25 | 35–36 | 64 | 状态映射里 46 个 FAILED 不在参考集内（环境相关测试），参考 case 全部通过 |
| modin-project/modin | 4–6 | **1,084–1,144** | 1,100–1,157 | 整个 `test_io.py` 约 3,400 个 case，18 分钟一次；见下面的第一个真实反例 |

**第一个真实评分反例：modin-6937 的判定随网络状态翻转。** default 变体（默认网络）gold ×3 全部 RESOLVED_NO：F2P 已 PASSED，但参考 P2P 中的 `TestCsv::test_read_csv_s3_issue4658` FAILED；**`--network none` 的两个变体里同一测试 PASSED，gold 得 RESOLVED_FULL**。也就是说，SWE-Gym 的参考 P2P 是在无网络环境里生成的，该测试在能出网时反而失败：有网时假凭证请求打到真实 AWS 端点，抛 `botocore.errorfactory.NoSuchBucket`，与测试预期的错误路径不同；无网时走连接失败路径，测试通过。含义：(a) 评分必须在与参考集生成时一致的网络条件下进行，rh2 grader 的 deny_all 恰好是正确的一侧，而"官方脚本 + 默认网络"会把这类题误判为不可解；(b) 同文件还有 19 个 `*_s3` 测试 setup ERROR，不在参考集内，不影响判定；(c) 单次评分 18 分钟，A 线定 grader wall-clock 时不能照搬 DeepSWE 的 300 s。（本节首版曾把它写成"P2P 依赖外部服务、任何环境都不可判 FULL"，按批次 C 的结果更正。）

### 4.1b 批次 C：离线与省略 install（12 题 × empty/gold × 2 变体 = 48 次）

| 变体 | empty 正确 NO | gold FULL | 与 default 不一致的题 |
| --- | ---: | ---: | --- |
| offline（官方脚本原样，`--network none`） | 12 / 12 | 11 / 12 | modin-6937 由 NO 变 FULL（见上）；pandas-48106 仍 NO（参考 ID 问题） |
| offline_noinstall（删除 install 行，`--network none`） | 12 / 12 | 11 / 12 | 同上 |

install 步离线行为：moto `make init` 与 pydantic `pdm add ...` 离线 rc=2（pip 连不上），其余 rc=0（editable 安装本地完成）；**无论 install 成功、失败还是被删除，12 题的判定都不变**。省略 install 省下的时间：pandas 约 700 s、pydantic 70–180 s、dvc 20–40 s、moto 9–14 s，其余个位数秒。结论（供 A/B 对账）：对这 12 题，rh2 grader "只跑测试命令、不重装、无网络"的设计在判定上与官方脚本一致或更接近参考语义；但 conan 的 `eval_commands`（PYTHONPATH）必须保留，pandas 的 Cython 修改若涉及 .pyx 仍需重建（本批 gold 是纯 Python 修改）。

### 4.1c SWE-Gym 216 题全量 pass 1（facts / empty / gold 各 1 次，default 变体，22:18–01:03 UTC）

| 项 | 结果 |
| --- | --- |
| 镜像 | 216/216 digest 与键控清单一致、amd64、HEAD == base_commit；默认网络下 216/216 可达 pypi；**216/216 含 base 之后仍可达的提交（中位数 1,775，最多 8,294）** |
| 包导入位置 | 191 题从 `/testbed` 导入（editable）；13 题 `import` 失败（conan 12 题依赖 `eval_commands` 的 PYTHONPATH，另 1 题待查）；12 题为早期 facts 记录无此字段 |
| empty 门 | **216/216** 正确 RESOLVED_NO（测试真跑、≥1 F2P 失败） |
| gold 门 | **204/216** RESOLVED_FULL 且严格判定通过；**12 题 RESOLVED_NO** |
| gold 失败原因 | 10 题 `p2p_missing`（参考 ID 与日志不匹配）、2 题 `p2p_not_ok`（modin 的 S3 测试在默认网络下失败） |
| 耗时（gold 单次，含容器启动/官方脚本/解析） | 中位 44 s，p90 201 s，最大 1,103 s；install 中位 9 s、p90 69 s、最大 708 s（pandas 重编译）；测试中位 7 s、p90 29 s、最大 1,094 s（modin `test_io.py`）；216 题一遍 gold 合计 5.3 机时 |
| 拉取 | 192 个镜像按需拉取，中位 22 s；pull-run-rmi 峰值磁盘占用 <130 GB |

**10 题 `p2p_missing` 都是同一类：参考 P2P 的 ID 含非 ASCII / 转义 / 空格，dataset 里的字符串与镜像内 pytest 打印的字符串不同或被官方 parser 在空格处截断**：

| 题 | 参考 ID 例子（截断显示） |
| --- | --- |
| moto-5417 / 5545 / 6308 | `test_multipart_upload_with_copy_key[the-unicode-💩-key]`、`test_copy_key_boto3[the-unicode-💩-key]` |
| moto-5562 / 5701 | `test_key_with_special_characters[/the-key-unîcode/test]` |
| dvc-4185 | `test_run_with_invalid_stage_name[\\]` |
| modin-6780 | `test_str_extract[([ab])(\\d)-False-separator` |
| pandas-48106 / 50319 | `…[Period\\('2017',`、`test_is_iso_format[%Y\\%m\\%d` |
| pydantic-8977 | `test_constrained_bytes_too_long[âª¶â\x93²â½·01-False]`（mojibake） |

这 10 题在当前官方 parser 语义下**任何补丁都拿不到 FULL**（占 216 的 4.6%）。§4.1 的静态扫描（反斜杠/空格/截断，11 题）只命中其中 4 题，另有 6 题静态扫描列出的题实际通过；所以"参考 ID 脆弱"必须靠真跑 gold 门识别，不能靠字符串规则。处理方式仍是 T0：要么在 ingestion 时按镜像内实际 nodeid 重新规范化参考集（改变官方指标定义，需声明），要么把这 10 题标为"当前评分链不可判 FULL"排除出训练池并保留原因。

另外 2 题（modin-5940、modin-6937）是 `*_s3` 测试在默认网络下 FAILED；modin-6937 已在 §4.1b 证明无网络时 FULL，modin-5940 很可能同类（待 pass 2 或离线复核）。

按仓库：MONAI 26/26、conan 12/12、dask 14/14、mypy 40/40、pydantic 19/20、dvc 34/35、moto 54/59、pandas 3/5、modin 2/5。

### 4.2 R2E 24 题（noop / gold ×3，`--network none`）

第二轮（parser 逐字对齐 Prime）：24 题 noop 72/72 得 0（每题至少 1 个预期 PASSED 的 case 实际 FAILED，不是空日志），gold 60/72 得 1；**4 道 pillow 题 gold 全部 0**，原因不是测试失败而是键不匹配：pillow 的 `expected_output_json` 键自带 ANSI 转义（`\x1b[1mtest_sanity\x1b[0m`）。两套上游实现在这里不一样：

| 实现 | 去色规则 | 对 pillow 的后果 |
| --- | --- | --- |
| R2E 原始 runtime `decolor_dict_keys` | `\[\d+m`（连 ESC 一起删） | 两侧都变成 `test_sanity`，匹配 |
| Prime `_decolor` | `\[\d+m`（留下 ESC） | expected 变成 `\x1btest_sanity\x1b`；若沙箱输出无色则 parse 侧是 `test_sanity`，**必然 0 分**；只有输出同样带色才对称匹配 |

本探针第三轮按 R2E 原始语义两侧对称删完整 ANSI（`r2e_probe/0.3`）：**24 题 × noop/gold × 3 次 = 144 次全部通过**（noop=0 且有真实失败 case，gold=1），三次重复的 mismatch 集合逐题一致；账本 `r2e_ledger_v3.jsonl`（v1/v2 保留作审计）。这是接入 R2E 时必须写进 adapter 的一条：**expected 键与解析键要用同一去色规则**，并把"expected 含 ANSI"记为数据事实。

其余 20 题在两轮里全部一致：noop=0、gold=1，3 次重复的 mismatch 集合逐次相同。gold 由 `parsed_commit_content` 重建（非测试 .py 文件）与容器内 `git diff HEAD <fix_commit>` 的改动行在 17/24 题一致；7 题不一致（coveragepy ea6906、datalad 9ba5de、orange3 f237f9、pandas 19c5ee、pandas 7dd34e、scrapy cfed9b、pillow 2d01f7）但 gold 仍得 1，说明差异来自被过滤掉的非 .py / 测试路径文件，不影响判分；正式接入时按 Prime 的过滤规则逐题核对。

## 5. Claude Code 2.1.205 + DeepSeek 参考求解（api_reference_run）

方法：同一镜像独立 `docker run`（默认网络），复制 ccbundle，建 `agent/54321`，root 执行 rh2 `git-sanitize.sh`，`chown /testbed`，以 agent 在 /testbed 运行 `claude -p <rh2 render_user_prompt 原文> --permission-mode bypassPermissions --output-format stream-json --include-hook-events --verbose --disallowedTools Task WebFetch WebSearch --max-turns 60`，wall-clock 1500 s；结束后 root 导出 `git add -A; git diff --cached --binary HEAD`，交 `swegym_probe.py --gates candidate` 在 fresh 容器用官方脚本评分。结果只回答"该题在此 harness 下能否被一个强模型解出"，不进任何成功率。

冒烟（pydantic-8500，19:55–20:06 UTC）：**resolved**（官方 RESOLVED_FULL，严格判定通过）。58 轮、57 次工具调用（Bash 44 / Read 10 / Edit 3）、506 s、**¥0.56**（余额 55.20 → 54.64）。git-sanitize 生效：base 之后可达提交 749 → 0。导出补丁 11 KB，触及 `pydantic/main.py` 之外还改了 `pdm.lock`、`pyproject.toml`（模型执行了 `pdm`/`make install` 类命令的副产物）与 `tests/test_construction.py`（官方脚本会把官方测试文件重置到 base，因此不影响判分）。据此把其余 23 题（核心 + 备用）排入同一探针，预算上限按余额保留 ¥10。

count_tokens 端点：DeepSeek 返回 200，Claude Code 未报错。stream-json 一题约 4.5 MB（含 thinking_tokens 事件）。

**24 题批次（核心 12 + 备用 12，60 轮 / 1500 s 上限，3 并发）：**

| 结果 | 题数 | 备注 |
| --- | ---: | --- |
| resolved（官方 FULL 且严格通过） | 13 | 含重跑后的 modin-6298；其中 3 题在第 60 轮被截断（`error_max_turns`）但导出的补丁已经修好 |
| unresolved | 10 | 含 modin-6937 与 pandas-48106 这两道结构性不可判 FULL 的题；其余 8 题里 3 题 PARTIAL（部分 F2P 通过）、5 题 NO；6 次达到 60 轮上限 |
| 官方判定 error | 1 | MONAI-2454：候选新建了与官方 test_patch 同名的测试文件，见下方第三个反例；投影后可判，结果 unresolved |
| 首轮 infra 失败后重跑 | 2 | 备用题镜像未预拉，`docker run` 按需拉取超过 180 s 超时；预拉后重跑成功 |
| 费用 | ¥38.4 | 平均约 ¥1.6/题，最高 ¥3.49（pandas-50319）；余额 55.32 → 36.9 |
| 单题耗时 | 86–557 s | 平均约 330 s；工具调用平均约 45 次，Bash 为主 |
| 补丁触及测试文件 | 多数 | 模型常顺手改/加测试；官方脚本会把官方测试文件重置到 base，其它测试文件的改动保留（与 rh2 投影语义需对账） |

**第三个真实反例（评分链语义）：MONAI-2454 候选补丁新建了 `tests/test_to_tensor.py`，而官方 `test_patch` 恰好也是新建同一路径。** 官方脚本先 `git checkout <base> tests/test_to_tensor.py`（base 没有该文件，失败但脚本无 `set -e` 继续），再 `git apply` 官方 test_patch → `error: tests/test_to_tensor.py: already exists in working directory` → 没有 "Applied patch" 标记 → 官方判定为补丁未应用（error），模型是否修对无从得知。静态扫描：216 题中 **8 题**的 test_patch 会新建测试文件；DeepSeek 的 24 个候选里 **17 个**触及了官方测试路径（多为修改已有测试文件，官方脚本会重置，无害），1 个撞上新建文件。含义：(a) 官方 runner 对"候选新建了官方测试同名文件"这一常见行为会判 error，不是模型错；(b) rh2 的可信投影若做的是"官方测试路径先按 base 恢复再写官方 test_patch"，遇到 base 不存在的新文件同样会失败，**A 线需要确认 rh2 trusted setup 对新增官方测试文件的处理（先删候选版本再写官方版本）**；(c) 本探针为此增加了 `candidate_projected` 门：去掉候选中触及官方测试路径的文件段后再按官方脚本评分，结果见 §7。

解读边界：这是"一个强 API 模型在 rh2 同款提示词与 Claude Code 2.1.205 下、60 轮内的单次结果"，用于说明题目在此 harness 下可被解出的比例量级（22 道可判 FULL 的题里 12 道），不是任何模型的成功率，也不是我们基座的锚点。

## 6. 对 rh2 评分链的直接含义（供 A/B 对账，不是决定）

1. **install 步**：官方脚本 216/216 有 install。批次 C 证明对 12 题省略 install 或离线运行都不改变判定；rh2 grader "只跑测试命令、deny_all"的设计在判定上等价且省下最多 700 s/次。必须保留的是 conan 的 `eval_commands`（PYTHONPATH），否则 12 题 import 失败。
2. **网络状态是评分语义的一部分**：SWE-Gym 参考集是离线生成的；modin-6937 在默认网络下 gold 判 NO、无网络判 FULL。rh2 的 deny_all 是正确的一侧，任何"在线跑官方脚本"的对照都要注明网络条件。
3. **参考 ID 脆弱**：216 题里 10 题的 P2P 参考 ID 在当前镜像下永远 MISSING（非 ASCII / 转义 / 空格截断）。这是 SWE-Gym Lite 数据面的缺陷，不是 rh2 的；训练池要么排除并记录原因，要么改判定定义（T0）。
4. **补丁应用语义**：镜像 git 2.34.1 使官方 runner 总是退到 `patch --fuzz=5`；rh2 是 frozen delta 直写。gold 全部能 `git apply --check`，所以本批没有因 fuzz 放宽而通过的案例，但对账时要用同一候选工件比较两条路径。
5. **官方测试路径与候选新文件冲突**：8/216 题的 test_patch 新建测试文件；候选若创建同名文件，官方脚本判 error。rh2 trusted setup 需要"先删候选版本再写官方版本"的语义，A 线确认。
6. **可见性**：216/216 SWE-Gym 镜像与 24/24 R2E 镜像都含未来提交（含修复提交）；rh2 rollout 侧 git-sanitize 必需，探针已验证它在这些镜像上把 base 之后可达提交清到 0。
7. **测试只约束一半修复**（MONAI-6975 删末 hunk 仍 FULL）与 **部分测试文件不受官方脚本重置**（候选改动的非官方测试文件保留）是题级事实，不是评分器错误；进人工复核清单。
8. **评分时长**：gold 单次中位 44 s、p90 201 s、最大 1,103 s（modin）。A 线的 grader wall-clock 若取 300 s，会把 modin 5 题、pandas 5 题（重编译）和部分 MONAI/dvc 判成超时；建议按仓库设上限或先把 install 步去掉再定。
9. **R2E 接入**：reward 是"预期状态映射精确匹配"（预期里可以有 FAILED/ERROR）；expected 键可能带 ANSI（pillow），两侧必须用同一去色规则；隐藏测试在 `/r2e_tests`，评分前复制到 `/testbed/r2e_tests`。

## 7. 本轮状态（随批次更新，UTC 时间）

- [x] 机器就位、oracle 安装、数据同步、24 + 24 题镜像拉取（含 digest 核）
- [x] SWE-Gym 校准 3 题；核心 12 题 empty/gold ×3（批次 A）：10 题全过，modin-6937 / pandas-48106 为结构性反例（§4.1）
- [x] 探针层（批次 B）：无关文件补丁 12/12 正确不通过；删末 hunk 11 rejected + MONAI-6975 suspicious_pass
- [ ] 离线 / 省略 install（批次 C，46/48 完成）：已完成的题全部与 default 判定一致；moto 的 `make init` 离线 rc=2 但不影响判定；省略 install 同样不影响判定
- [x] rh2grader 身份（批次 D）：root 做 setup/install，测试命令以 uid 54322 执行（`id -un` 记录为 rh2grader）；12 题的官方判定、逐 case 状态计数与 root 完全一致（10 FULL + 同样的 modin/pandas 两个 NO）。对这 12 题，W3b T0(a) 担心的"非 root 翻转权限类测试"没有出现；注意本批 install 仍由 root 完成，候选用户只跑测试。首次尝试因我把 root 创建的日志文件直接交给 54322 追加写而失败（权限），修复后重跑
- [x] R2E 24 题 facts；noop/gold ×3 = 144/144 通过（v3 账本）；pillow 的 ANSI 键问题与 Prime/R2E 去色差异记录在 §4.2
- [x] DeepSeek + Claude Code 2.1.205：24 题全部跑完（含 2 题因镜像未预拉超时后重跑）：13 resolved（modin-6298 重跑后 resolved）、9 unresolved（含 2 题结构性不可判）、MONAI-2454 官方判定 error（测试文件同名冲突，§5），投影后 unresolved
- [x] `candidate_projected` 门（去掉候选对官方测试路径的改动后评分）：24 题完成，13 resolved / 11 unresolved，与官方判定逐题一致、无翻转；MONAI-2454 由官方 error 变为可判（unresolved），说明投影只修复了"无法判分"，不改变结论
- [x] SWE-Gym 216 全量 pass 1（facts/empty/gold ×1）：22:18–01:03 UTC 完成，结果见 §4.1c（首次启动因按需拉镜像 120 s 超时失败了 40 个 job，改为显式 `docker pull` 后重跑；账本里这些 `infra_failed:docker_timeout` 行保留作审计，判定以后续成功行为准）
- [x] pass 2（empty/gold 追加到 ×3）：01:03–04:42 UTC 完成，816 个 job；216 题 × empty/gold 各 3 次齐全。**gold 3/3 FULL 204 题、empty 3/3 正确 215 题**；三次判定不一致的只有 MONAI-763 的 empty 第 2 次（`suspicious`，parsed_cases=0），Codex 已定位为容器默认共享内存 64 MiB 导致 DataLoader SIGBUS（见 [codex_remote_check_20260909.md](codex_remote_check_20260909.md) §2），不是判定翻转；12 题 gold 三次全 NO，与 pass 1 相同
- [x] 账本快照回传到本目录 `ledger/`（01:08 UTC；pass 2 结束后需再同步一次）、汇总表 `ledger/summary.md`、B 留言板登记

## 8. 收口与勘误（Claude，2026-09-09 04:50 UTC）

Codex 的[远端核查](codex_remote_check_20260909.md)与[24 题可解性审查](solvability_review_20260909/README.md)在我等待 pass 2 期间完成。逐条回应（按协作协议四选一）：

| Codex 发现 | 回应 | 说明 |
| --- | --- | --- |
| Prime `_decolor` 正则含真实 `0x1b` 字节，"Prime 留下 ESC" 是转录时丢了不可见字符 | **accepted，撤回** §4.2 的"两套上游实现不同、Prime 必然零分"归因 | 保留的只是"expected 与解析键必须同规则去色"这一实现要求；v3 runner 的对称去色与固定官方函数重放 144/144 一致 |
| R2E 七题 gold 与 git diff 的差异只是 diff 表述，最终文件内容相同 | **accepted** | §4.2 的"差异来自被过滤文件"解释撤回；疑点关闭 |
| 逐题余额差在并发窗口重叠，¥38 是重复计数；账户净减 ¥18.76 | **accepted** | §5 费用改按账户区间：DeepSeek ¥55.32 → ¥36.56 |
| git-sanitize 只在 24 个 CC 求解容器验证了 `after_future=0`，不能推广到全部 240 个镜像 | **accepted** | §6 第 6 条按此收窄 |
| `candidate_projected` 只去精确同路径，rh2 还按 `DEFAULT_SWE_TEST_GLOBS` 排除更多测试路径，6 题有差别；MONAI-2454 的同名新文件在现有 rh2 投影下本来不会进 grader | **accepted** | §5/§6 的"rh2 需要新增先删同名文件"建议撤回，改为"用这 7 个现成工件对账真实 rh2 grader" |
| MONAI-6975 删末 hunk 删掉的只是 docstring，不是弱测试证据；mutation 实际 10 rejected / 1 suspicious / 1 fixture_invalid | **accepted** | 我的变异 fixture 是"机械删末 hunk"，不保证破坏行为；§4.1 的解释撤回，后续 mutation 要针对明确行为 |
| conan 在 `/tmp` 下 import 失败不能推出 12 题必然假阴性；grader_user 变体没带 `export PYTHONPATH` 仍通过 | **accepted** | §3.1/§6 改为"命令差异待用真实 rh2 路径核验" |
| modin-6937 的网络翻转有实证，但不能反推整个参考集是离线生成的；modin-5940 离线未验 | **accepted（收窄）** | 保留"评分网络条件必须固定并记录" |
| 10 题参考 ID 是"当前镜像 / 日志 / parser 组合下无法 FULL"，不是"数据必坏、永远不可能" | **accepted（收窄）** | 处置仍是 T0：先逐类归因（Unicode / 反斜杠 / 空格各一题），再决定改规范化还是排除 |
| DeepSeek 24 题里 3 条轨迹通过 Bash 下载了上游修复（Pydantic-8500、Conan-14296、Moto-5701）；13/24 不是独立解题率 | **accepted** | 探针只禁了 `Task/WebFetch/WebSearch`，Bash 出网未禁；下一轮若测自主修复，必须封仓库工具的出网或单独报告为"可检索修复" |
| Pydantic-5706 官方评分覆盖不足（候选破坏 Sequence 行为但只跑 `test_json_schema.py`）；Pydantic-8500 官方用例未覆盖题面原例 | **accepted** | 这是"官方通过里的真实反例"，比我找到的三个反例更接近训练信号本身 |
| r2e v1/v2 原始日志被 v3 同路径覆盖，三版没有各自完整证据 | **accepted** | runner 设计缺陷：输出路径未含 run/version；下一批修 |
| 216 首遍中单次超过 300 s 的是 10 题，不是所有 modin/pandas | **accepted** | §6 第 8 条按此改 |

**没有被推翻的**：216 题 empty 216/216、gold 204/216 的门结果（pass 2 重复后仍是 204 题 3/3 FULL）；R2E 144/144；核心 12 题四组变体一致；官方脚本 216/216 含 install 且省略/离线不改 12 题判定；镜像 git 2.34.1 使官方 runner 退到 `patch --fuzz=5`；240 个镜像 facts 中 base 之后可达提交均 >0。

**新增（pass 2）**：MONAI-763 的共享内存故障说明 grader 容器的 `--shm-size` 是资源配置的一部分（默认 64 MiB 会让 torch DataLoader 测试 SIGBUS）；1,296 次 default 运行里只出现这 1 次判定噪声，其余全部三次一致。

**收口状态**：实例上的 `code/ data/ ledger/ logs/` 已在 pass 2 结束后完整同步到本地 git 忽略目录 `runs/env_probe_20260909_final_sync/`（Codex 的 02:50 快照在 `runs/env_probe_20260909_codex_backup/`）；仓库内 `ledger/` 是最终账本快照。实例仍在运行（vast 信用 $4.54），是否释放由用户决定。

实例上看进度：`tmux attach -t full216`；账本 `/work/ledger/swegym_ledger.jsonl`；`cd /work && ./venv/bin/python code/summarize.py` 随时可出汇总表。费用：vast 信用 $6.15 → $5.18（01:05 UTC），DeepSeek ¥55.32 → ¥36.56。原始日志（每次运行的 eval.sh / patch.diff / test_output.txt / status_map.json）在实例 `/work/ledger/logs*/`，总量数 GB，未回传仓库；实例释放前请打包保存或指定要保留的子集。
