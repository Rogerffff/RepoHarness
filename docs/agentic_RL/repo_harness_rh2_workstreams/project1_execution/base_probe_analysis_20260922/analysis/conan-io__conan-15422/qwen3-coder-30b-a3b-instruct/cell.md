# 格子报告：conan-io__conan-15422 × qwen3-coder-30b-a3b-instruct（a2 / a3 / a4）

协议：`runs/base_probe_20260922/analysis/CELL_PROTOCOL.md`（含 `REVIEW_PROTOCOL.md`）。**非严格盲审**：attempt 与网关目录路径含模型名；阶段一只读运行记录 §2 / §3 / §6，未读 §7–§9、grading/、gold、测试补丁、题卡与同题报告，派发消息未带 reward。阶段一结论先写入本文件，阶段二后只压缩措辞、把细节移入 §4，结论未改。a1 已有单独报告（同目录 `a1.md`），本文只审 a2 / a3 / a4，阶段二引 a1 作对照。条件：`bash_env_v1`、CC 2.1.205、adapter `tool_parser=qwen3_coder`、无 thinking、T=0.7、`max_new_tokens=8192`、上下文 131072（E0）。E 编号见 §4。

## 1. 格子结论

1. 三条全部 reward=1（F2P `test_presets_njobs` PASSED、P2P 0 fail/40、`RESOLVED_FULL`、41 passed / 3 skipped），候选在 fresh 容器实测，install / test rc=0；67–112 s、27–34 轮，无截断、无 infra、无答案渠道探测、未读 harness 目录（E13–E15）。
2. **补丁分两类**：a2、a4 用 `build_jobs()`（未配置时写容器 CPU 数），与 gold 同义（差异只在 `jobs=0` 边角）；**a3 用 `conf.get(..., default=None)` 只在显式配置时写 `jobs`，未配置时不写——与 a1 同一种缺口**，且这次不是静态推断：a3 自己在求解容器里跑出了 `Has 'jobs' field: False`，并写了断言"未配置不写"的单测（E16–E19）。多配置路径三条都不设门，与 gold 同函数；a3 还在 VS 2019 生成器下自测到 `jobs: 8`（E18）。
3. 疑似假阳性：a3（同 a1 形状，"官方通过、默认仍缺失"两半都已在容器内实测）。a2 / a4 未见与公开需求相悖的行为（E16–E17）。
4. a3 的 12.5 KB 候选：源码只有 4 行；其余是 1 个新测试文件（92 行，3 用例，其中"未配置不写"用例与 gold 相反）+ 3 个仓库根草稿（README 70 行、`debug_test.py` 48 行、`verify_implementation.py` 106 行）；没有改既有期望（E12、E15）。
5. 接口现象稳定：`<|im_end|>` 泄漏 3/3（各 1 次，都是无工具调用的收尾轮；89 个带调用轮 0 次）；CC 改写工具参数 17/89 次（补 `replace_all:false` 3、去 `cd /testbed && ` 6、删空行尾随空格 8）；无 `finish=length`，prompt ≤ 50.2K；a3 / a4 各有 1 次 CC `count_tokens` 请求被网关以 `{"input_tokens": 0}` 顶回（E8–E11）。
6. 工具面干扰：无关工具 a2 7（+ `Skill(verify)` 连锁 4）/33、a3 2/30、a4 3/26；CC 每 6–8 轮注入一次 `role:system` Task 提醒（每条 4 次），a2、a4 各有 2/4 次提醒在同轮或下一轮引出 Task* 调用（因果为推断）；`ReportFindings` 被当"交差"工具（a2 两次空、a4 一条自相矛盾）。RL 含义：与 a1 合计 4/4 全 1，奖励分不出 a1 / a3 的默认路径缺口与 a2 / a4 ≈ gold，也分不出 a3 的 3 个草稿文件与 a2 的 11 次绕路；组内优势为零（E20–E22）。

## 2. 每条尝试

### a2（`bp22-qwen3-coder-30b--conan-15422-a2`，in_tree，87.9 s / 35 回合 / 34 次请求 / 33 次调用）

**阶段一。** 无修前复现：find → Read `presets.py` → grep jobs → Read `cpu.py` → TaskCreate → 直接 Edit（E1）。定位正确（`_build_preset_fields`；`build_jobs` 缺省 CPU 数）。两次 Edit 同一函数，第二次加 `isinstance(njobs, int) and njobs > 0` 守卫（冗余，`build_jobs` 已 `check_type=int`）（E2）。验证扎实：临时脚本首跑因 `define(..., "8")` 传 str 失败（唯一 is_error），改 int 后看到 `"jobs": 8`；无配置脚本看到 `"jobs": 2`（沙箱 2 CPU）；既有单测 2 passed、`test_cross_build` 1 passed；临时文件全部 rm（E3）。无关工具 7 次：TaskCreate / TaskUpdate×2 / TaskList、ReportFindings×2（空 findings）、`Skill(verify)`——注入 11,766 字符的 verify 提示后又花 4 次调用重做一遍验证（find、Write、运行、rm），合计 11/33 次与修 bug 无关（E20–E21）。未读 `.harness/`（in_tree 下存在，候选已排除）；无答案渠道；终止正常，说明与 diff 一致，"All existing tests pass"基于 3 个测试属过度概括。自部署：prompt 18,904 → 39,390，最长输出 1,016，全 `stop`，33 个调用 1:1 解析；`<|im_end|>` 泄漏于 A-T34；CC 改写 7 处（E8–E11）。

**阶段二。** reward 1，F2P PASSED，P2P 40/40；`projectable`，只含 `presets.py`，`ignored_paths=[]`（E13–E15）。与 gold 同义：显式值同、未配置同（最终代码下自测 `"jobs": 2`，E17）、多配置同函数无门（静态）；唯一差异 `jobs=0` / 负数时省略（gold 写），无公开依据判对错（E16）。题卡风险未显现为语义缺口。

**归因。** `model_success`；process_quality `mixed`（无复现、11/33 次绕路、冗余守卫；验证与清理干净）；置信 high。

### a3（`…-a3`，out_of_tree，112.5 s / 31 回合 / 31 次请求 / 30 次调用）

**阶段一。** 无修前复现：Read `presets.py` → grep → Read 整份 `conf.py`（约 9K token，只用到一行）→ Read `cpu.py` → 直接 Edit（E1）。定位正确，但实现走 `conf.get("tools.build:jobs", default=None, check_type=int)`，`is not None` 才写（E2）。验证过程曲折：新建 3 用例的测试文件复制既有模块级 fixture，"未配置"用例被前一用例的 `jobs=16` 污染而失败；先误判"环境/缓存问题"，单跑通过、整文件再失败、写 `debug_test.py`、改 json 断言后看到 `{'jobs': 16}` 才判为 fixture 污染，4 次 is_error 全出于此；随后 `verify_implementation.py` 三场景通过（无 conf → 无 jobs；16；VS 2019 多配置 → 8）、`test_cmaketoolchain.py` 35 passed、最终改成每用例 `create_conanfile()` 后 3 passed、`-k preset` 5 passed（E4）。**未清理**：README、`debug_test.py`、`verify_implementation.py` 留在仓库根，候选 12,528 B（E12）。无关工具只有收尾的 TaskCreate / TaskUpdate（在总结之后，纯仪式）。交付说明漏报两个草稿文件。自部署：prompt 18,901 → 50,222，最长输出 1,808（整文件重写的 Edit），全 `stop`，30 个调用 1:1；`<|im_end|>` 于 A-T31；CC 改写 7 处（E8–E11）。

**阶段二。** reward 1，F2P PASSED，P2P 40/40；`projectable`，5 个文件全部纳入投影，`ignored_paths=[]`，`candidate_test_like_paths` 两项；评分只跑 `test_cmaketoolchain.py`，新测试与草稿不被执行（E13–E15）。**与 gold 相反的路径：未配置。** 输入 `conan install . -g CMakeToolchain`（F2P 去掉 `-c`）；预期 `buildPresets[0]["jobs"]` = CPU 默认（gold fp_check 实测 2）；实际无 `jobs` 键——a3 自己的脚本输出 `Has 'jobs' field: False`、单测 `assert "jobs" not in build_presets[0]` PASSED、README 明文"If not set, omit the jobs field"（E17、E19）。这是 a1 缺口的第二次出现，形状同 fp_check `coder_a1` 行；与 a1 的差别只在 `jobs=0`（a3 写 0 = gold，a1 省略）。多配置路径：显式值下自测 `jobs: 8`（追加分支）与单测（新建分支）都写；未配置 + 多配置按同一逻辑缺（静态）（E18）。题卡"只在显式配置时写 jobs 的部分实现静态上可能满分"在本条**实跑显现**（E22）。

**归因。** `model_success`（显式路径真实生效）+ `suspected_false_positive`（默认路径漏修，参考测试不覆盖）；process_quality `mixed`（验证最终扎实，但 4 次自伤、草稿入库、说明漏报）；置信 high（缺口由候选代码在容器内实测，公开可推性按 a1 报告与题卡为中高）。

### a4（`…-a4`，out_of_tree，67.0 s / 27 回合 / 27 次请求 / 26 次调用）

**阶段一。** 无修前复现，但读得最全（12 次 Read：`presets.py`、`conf.py`、`test_cmake_toolchain.py` 200 行、`cmake.py` 全文看到 `_cmake_cmd_line_args` 用 `build_jobs`、`build/__init__.py`、`cpu.py`）→ TaskCreate → Edit 函数体 + Edit 顶部 import，回读确认（E1–E2）。验证：在**既有单测文件** `test_cmake_presets_definitions.py` 追加 `test_cmake_presets_jobs_parameter`（显式 16），并加 `import json`（未用）与 `load_cmake_presets`；新用例 1 passed、整文件 3 passed、功能测试 `test_cmake_toolchain_custom_toolchain` 1 passed；**未验证未配置场景**（E5）。0 次 is_error。无关工具 3 次：TaskCreate、TaskUpdate、ReportFindings（一条把自己的改动写成 correctness 失败场景的"finding"）。交付说明与 diff 一致，但"only adds … when explicitly configured or has a meaningful value"有误导（`build_jobs` 总返回正整数，`jobs` 总会写），同一说明另一处写明缺省 CPU 数。自部署：prompt 18,901 → 48,334，最长输出 1,203，全 `stop`，26 个调用 1:1；`<|im_end|>` 于 A-T27；CC 改写 3 处（E8–E11）。

**阶段二。** reward 1，F2P PASSED，P2P 40/40；`projectable`，`included_paths` 两项，`ignored_paths=[]`——改的单测文件不是官方测试文件，被纳入投影但评分命令不执行它（E13–E15）。与 gold 同义（`if njobs:` 只在 `jobs=0` 边角省略），未配置 / 多配置两条路径与 gold 同函数同取值（静态，本条未自测）（E16、E18）。题卡风险未显现。测试改动类型：新增用例，未改既有期望。

**归因。** `model_success`；process_quality `good`（0 错误、最省回合、有回归验证；扣分项是 3 次仪式工具与未测默认路径）；置信 high。

## 3. 格子级核对

**(1) 成功补丁是否实质相同 / 与 gold 同义 / 假阳性。** 源码段三种：a2（局部 import + `isinstance`/`>0` 守卫）、a4（顶部 import + `if njobs`）——二者语义相同且≈gold；a3（`default=None` + `is not None`）——与 a1（无 default + `if jobs`）同一缺口。两条参考测试不覆盖的路径（对照 gold 与 `conan15422_fp_check/` 实测，E19）：

| 路径 | gold（fp_check） | a1（fp_check） | a2 | a3 | a4 |
| --- | --- | --- | --- | --- | --- |
| 无 conf（题面报告者的实际场景） | 2 | 缺 | 2（容器内自测，最终代码，E17） | **缺**（容器内自测 + 单测 + README，E17） | 2（静态：同 a2 逻辑） |
| `jobs=42` 单配置（≈唯一 F2P） | 42 | 42 | 42（评分 PASSED） | 42 | 42 |
| 显式值 + 多配置生成器 | 42 | 42 | 写（静态：同函数无门） | 8（VS 2019 自测，追加分支 + 新建分支，E18） | 写（静态） |
| 无 conf + 多配置 | 2（推断） | 缺 | 2（静态） | 缺（静态，由无 conf 推出） | 2（静态） |
| `jobs=0` | 0 | 缺 | 缺 | 0 | 缺 |

疑似假阳性：**a3**，输入 / 预期 / 实际见 a2.2；与 a1 一起，本格子 4 条官方 1 分里 2 条漏默认。a2 / a4 无。

**(2) 失败原因。** 无失败（0/3；含 a1 为 0/4）。

**(3) RL 含义。** 全 1 无区分度：奖励分不出 {a1, a3}（漏默认，题卡预言的缺口）与 {a2, a4}（≈gold），也分不出 a3 的草稿入库、a2 的 11 次绕路与 a4 的干净过程；组内优势为零。要有信号需另版本给参考测试补"未配置默认"断言（新增断言须有公开依据、不硬编码本机 CPU 数，见运行记录 §9.2.3）。

**(4) 派发消息的专项。**
- **a3 的 12.5 KB**：`presets.py` 4 行（D86–89）；新测试文件 92 行（D93–191）= 新增测试，3 用例，其中 `test_cmake_presets_no_jobs_parameter_when_not_set`（D153–168）把与 gold 相反的行为固化为断言（若套用 gold 该用例失败；评分不跑它）；草稿 3 个：README（D1–77，明文"If not set, omit"）、`debug_test.py`（D192–246，模块级 fixture 的调试副本）、`verify_implementation.py`（D247–359）。没有"改既有期望"。
- **无关工具与 CC 提醒的频次**（E20–E21）：无关调用 a1 4/33、a2 7(+4)/33、a3 2/30、a4 3/26。CC 中段 `role:system` 提醒"The task tools haven't been used recently…"每条 4 次（a2 seq 7/15/22/29；a3 6/12/18/25；a4 6/11/19/24）；随后 ≤1 轮内出现 Task* 调用：a2 2/4（seq 7 同轮 TaskCreate、seq 22 同轮 TaskUpdate）、a4 2/4（seq 12 TaskCreate、seq 25 TaskUpdate）、a3 0/4（Task* 在总结之后）。`ReportFindings` 无提醒也被调用（a2 2、a4 1、a3 0）。`Skill(verify)` 1 次（a2），注入 11,766 字符提示，直接导致 4 次额外调用与第二份总结。`<system-reminder>` 标签仅 `currentDate` 1 次/条；tool_result 尾注"file state is current…" 6/7/3 次，未见影响。同工具面下 DeepSeek 无此现象（a1 报告 E15）。
- **`<|im_end|>` 与 CC 改写**（E8–E11）：泄漏 3/3，各 1 次，只在无工具调用的收尾轮（A-T34 / A-T31 / A-T27），并进入 CC `result`；带调用轮 0/89。CC 改写 17/89：`replace_all:false` 补 3（每条会话首个 Edit）、Bash 去 `cd /testbed && ` 6（a2 3、a3 2、a4 1）、Write/Edit 内容里只含空格的行改成空行 8（a2 3、a3 4、a4 1）。网关回传历史与 CC 记录 0 差异——回放给模型的是改写后的版本，与采样 token 不逐字一致。
- **网关 / adapter 其它**：全部 status 200、`stream_error=null`、`stop_reason` 齐全；a3、a4 各有 1 个 `/v1/messages/count_tokens` 请求（紧随读 `conf.py` 之后）由网关直接回 `{"input_tokens": 0}`、未到 adapter（E11）——对本轮无可见影响（上下文 ≤ 50K），若 CC 用它决定自动压缩，则该桩会让阈值判断失真，属未验推断，回交 A 线。

## 4. 证据指针表

T = `ADIR/<a>/transcript.md` 行号；A-Tn = `GW/coder_adapter/<attempt_id>.turns.jsonl` 第 n 行（1 起）= `GW/coder/<attempt_id>/requests.jsonl` 的 `seq` n = `resp_n.sse`（`count_tokens` 行无 seq，不计）；D = `ADIR/<a>/candidate/conan-io__conan-15422.diff` 行号；EV = `ADIR/<a>/grading/eval_logs/*.eval.log` 行号；LG = `ADIR/<a>/grading/ledger.jsonl`。`ADIR = runs/base_probe_20260922/remote/runs/matrix/attempts/conan-io__conan-15422/qwen3-coder-30b-a3b-instruct`，`GW = runs/base_probe_20260922/remote/gateway`。

| 编号 | 指向 |
| --- | --- |
| E0 | `GW/coder_adapter/adapter_config.json`（`tool_parser=qwen3_coder`、`reasoning_parser=null`、T0.7、`max_new_tokens=8192`、`max_context_tokens=131072`）；各 `attempt.json` `actor_env=bash_env_v1`、`cc_version_observed`、`solver_note`；prompt 三条 sha256 相同 `a41bbc56…` |
| E1 | 无修前复现：a2 首个 Edit T L368–376（A-T8）早于首个执行类验证 T L806（A-T16）；a3 Edit T L435–449（A-T6）早于 T L669；a4 Edit T L989–1004（A-T13）早于 T L1295。三条全部调用输入中无 `conan install` / `TestClient` 修前运行 |
| E2 | 定位：a2 T L58–180（presets.py）、L240–306（cpu.py，`default=_cpu_count()` L275–278）；a3 T L58–180、L222–343（conf.py，prompt 24,101→33,317）、L353–419；a4 T L58–180、L222–343、L383–524、L534–567、L610–753（`cmake.py:17–19` 用 `build_jobs`）、L763–880、L890–956、L1014–1041、L1076–1158（`Read offset=0` 行号从 0 起 L1115） |
| E3 | a2 验证：Write T L790–803（A-T15）；失败 L806–821（A-T16，`must be a int-like object`）；修正 L831–846；`"jobs": 8` L887–893；无配置 `"jobs": 2` L971–976；第二次 Edit L1005–1013（A-T21）；既有单测 2 passed L1063–1076（A-T23）；`test_cross_build` L1096–1108；rm L1118–1131；Skill 后 verify 脚本 L1400–1413（A-T29）、输出 `"jobs": 16` L1458–1462、默认 `"jobs": 2` L1502–1506（A-T30）；rm L1525–1538 |
| E4 | a3 验证：Write 测试 T L702–715（A-T11）；1 failed L735–783（A-T12）；单跑 PASSED L803–815（A-T13）；再 failed L835–883（A-T14）；误判"environment or caching issue" L979；debug_test L893–906、输出无 jobs L955–960（A-T16）；json 断言 Edit L984–1001（A-T17，输出 1,661 token）；`{'jobs': 16}` L1048（A-T18）；判为 fixture 污染 L1061、L1326；verify 脚本 L1099–1112、输出 L1125–1147（A-T21）；35 passed L1188–1234（A-T23）；README L1244–1257（A-T24）；`-k preset` 1 failed L1277–1321（A-T25）；每用例 `create_conanfile` Edit L1331–1348（A-T26，1,808 token）；3 passed L1361–1375；5 passed L1395–1411 |
| E5 | a4 验证：Edit 既有测试文件 T L1270–1285（A-T21，追加 `test_cmake_presets_jobs_parameter`，`define("tools.build:jobs", 16)`）；1 passed L1305–1317（A-T22）；3 passed L1337–1351（A-T23）；功能测试 1 passed L1371–1383（A-T24）；整条无"未配置"场景运行（调用输入检索无 `Conf()` 不 define 的运行） |
| E6 | is_error 统计（`trajectory.jsonl` `tool_result.is_error`）：a2 1（A-T16 结果）、a3 4（A-T12 / T14 / T18 / T25 结果，均 pytest exit 1）、a4 0；无参数缺失 / 类型错 / 未先 Read / 字符串不唯一 |
| E7 | 无答案渠道 / 未读 harness：三条全部 tool_use 输入无 `pip` / `git log|show|branch|remote` / `curl|wget|http` / `site-packages` / `.harness` / `rh2_harness`；`facts/pip_freeze_before.txt` = `after.txt`；`facts/prelaunch.json` `DNS_EXTERNAL=DENIED`、`GIT_REMOTES=0`；a2 `facts/git_state_after.txt` `?? .harness/` 未进候选（`candidate.files` 仅 presets.py） |
| E8 | 上下文 / 输出：A-T 各行 `prompt_tokens` / `output_tokens` / `finish_reason`（a2 18,904→39,390，最长 1,016 @A-T29；a3 18,901→50,222，最长 1,808 @A-T26；a4 18,901→48,334，最长 1,203 @A-T21；全 `stop`）；`raw_output` 的 `<tool_call>` 计数 = `parsed.tool_calls` 数（33 / 30 / 26，0 差异） |
| E9 | `<|im_end|>`：每轮 `raw_output` 结尾都有；`parsed.content` 含它的只有 A-T34（a2）、A-T31（a3）、A-T27（a4）；对应 T L1689 / L1562 / L1527 与 `result.result`（T L1695 / L1568 / L1533）。成因见 a1 报告 E9 |
| E10 | CC 改写（adapter `parsed.tool_calls[].arguments` vs `trajectory.jsonl` 同序 `tool_use.input`；最后一条 `requests.jsonl` 回放的 `tool_use.input` 与 trajectory 0 差异）：a2 A-T8 Edit +`replace_all:false`、A-T16/T23/T28 Bash 去 `cd /testbed && `、A-T15/T19/T29 Write 空行尾随空格删除（例：`"    "`→`""`，首个差异在第 511 字符）；a3 A-T6 Edit +replace_all、A-T10/T21 Bash、A-T11/T15/T20 Write、A-T26 Edit 空白；a4 A-T13 Edit +replace_all、A-T21 Edit 空白、A-T22 Bash。模型自带 `replace_all` 的调用（如 a2 A-T21 原文 `False`）由 adapter 转 bool，不计改写 |
| E11 | 网关：`GW/coder/<id>/responses.jsonl` 全部 `status=200`、`stream_error=null`、`stop_reason∈{tool_use,end_turn}`；`usage.json` requests 34 / 31 / 27；a3、a4 各 1 条无 seq 的 `POST /v1/messages/count_tokens?beta=true`（ts 落在 seq 4 之后）响应 `{"input_tokens": 0}`、19 B、`application/json`，adapter turns 无对应行 |
| E12 | a3 候选构成：D1–77 README、D78–92 presets.py（D86–89）、D93–191 新测试（D111–128 `create_conanfile`，D153–168 "not in" 用例，D171–190 多配置用例）、D192–246 debug_test.py、D247–359 verify_implementation.py；`facts/git_state_after.txt` 4 个 `??`；`attempt.json` `candidate.bytes=12528`、`touches_tests` 两项；交付说明 T L1513–1562 未提 debug / verify 两文件 |
| E13 | LG `report`（`reward=1.0`、`outcome=resolved`、`f2p_pass=1/1`、`p2p_fail=0/40`）、`verdict_diagnostics.resolution=RESOLVED_FULL`、`install`（`install_rc_last_command=0`、`test_rc=0`）、`candidate.patch_sha256` = `attempt.json` `candidate.sha256`（a2 `310cb181…`、a3 `90c9d84e…`、a4 `8eae5382…`）；同机对照 `runs/base_probe_20260922/remote/runs/p0_controls/conan-io__conan-15422/{noop,gold}/ledger.jsonl` = 0.0 unresolved（F2P 0/1）/ 1.0 resolved |
| E14 | EV：a2 L957–990 与末段（`test_presets_njobs` PASSED、`41 passed, 3 skipped`、`RH2_TEST_RC=0`）；a3 L137–147（fresh 容器 `git status`：presets.py modified + 4 个 untracked）、L950（`pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`）；a4 L141（`modified: …test_cmake_presets_definitions.py`）、L717–742（该文件 diff 回显）；三条都有"恢复官方测试文件 + `git apply` 测试补丁"行（a2 L716–717、a3 L721–722、a4 L759–760） |
| E15 | LG `classification.verdict=projectable`（reason_codes 空）、`projection.included_paths`（a2 1 项；a3 5 项；a4 2 项）、`projection.ignored_paths=[]`（三条）、`candidate_test_like_paths`（a2 空；a3 `test_cmake_presets_jobs.py`、`debug_test.py`；a4 `test_cmake_presets_definitions.py`）、`candidate_touched_conftest_or_fixture=[]`；官方测试文件 = `s2/ingest/grading_bundles_v2_v0.jsonl` 本题行 `test_patch` 所改的 `test_cmaketoolchain.py`（`eval_cmd="pytest -n0 -rA"`，F2P 1 项，P2P 40 项） |
| E16 | gold：`runs/base_probe_20260922/remote/gold/conan-io__conan-15422.gold.patch`（顶部 import + 无条件 `ret["jobs"] = build_jobs(conanfile)`）；a2 diff（局部 import、`if njobs and isinstance(njobs, int) and njobs > 0`）；a4 diff（顶部 import、`if njobs`）；a3 diff D86–89；a1 diff（`ADIR/a1/candidate/*.diff`：无 default + `if jobs`） |
| E17 | 未配置路径实测：a2 最终代码 T L1502–1506（`"jobs": 2`）；a3 T L1130–1133（`Has 'jobs' field: False` / `Correctly does NOT have 'jobs' field`）、单测 PASSED T L1371、README D19；a4 无自测。gold / a1 对照：`runs/base_probe_20260922/remote/runs/conan15422_fp_check/{gold,coder_a1}/out.txt`（`no_conf` 2 / null；`cpu_count` 30 但容器配额 2） |
| E18 | 多配置路径：base `presets.py:54–60`（已有文件 + multiconfig 分支）与 `:66–68`（`_contents`）都经 `_build_preset_fields`（T L122–136）；a3 自测 T L1142（`'configurePreset': 'default', 'configuration': 'Release', 'jobs': 8`，同一 generators_folder 已有文件 → 追加分支）与单测 D171–190（新建分支）PASSED L1372；gold 在 Ninja Multi-Config 下 42：fp_check `gold/out.txt` |
| E19 | 已知缺口对照：`conan15422_fp_check/{coder_a1,deepseek_a1}/out.txt`、`coder_a1/src_only.diff` = a1 候选；同题报告 `…/qwen3-coder-30b-a3b-instruct/a1.md` §阶段二 2、`…/deepseek-v4-pro/a1.md`、`…/qwen3.6-35b-a3b/cell.md` §3；运行记录 `base_model_probe_run_20260922.md` §7.5 第 8 条、§7.5d、§8.2、§9.2.3 |
| E20 | 无关工具：a2 A-T7 TaskCreate（T L345–358）、A-T9 / A-T22 TaskUpdate、A-T26 / A-T33 ReportFindings（`findings: []`，T L1202–1215、L1616–1629）、A-T27 Skill（T L1218–1367，注入文本在 requests seq 28 msg#58，11,766 字符）、A-T32 TaskList；Skill 连锁 A-T28–T31（T L1377–1538）；a3 A-T29 TaskCreate、A-T30 TaskUpdate（T L1478–1508，在总结 L1416 之后）；a4 A-T12 TaskCreate、A-T25 TaskUpdate、A-T26 ReportFindings（T L1461–1482 的"finding"内容） |
| E21 | CC 提醒：最后一条 `requests.jsonl` 里 `role:"system"` 消息（a2 msg#14/31/46/61，首见 seq 7/15/22/29；a3 msg#12/25/38/53，首见 6/12/18/25；a4 msg#12/23/40/51，首见 6/11/19/24；msg#1 为 skills 清单，含 deep-research 描述）；`<system-reminder>` 仅 `currentDate` 1 个；tool_result 尾注 "file state is current in your context" a2 6 / a3 7 / a4 3 次 |
| E22 | 题卡：`…/results/conan-io__conan-15422/card.md` L8–9（默认值无断言）、L13（核心限制）、L17（唯一优先下一步）；`review.md` "默认、其它显式值、多配置…缺覆盖"行与 §最小后续实验 2（grader 负对照）；`analysis_before_history.md` 暂定处置段 |

## 5. JSON

```json
{"cell": {"task": "conan-io__conan-15422", "solver": "qwen3-coder-30b-a3b-instruct", "attempts_reviewed": ["a2", "a3", "a4"], "successes_equivalent_to_gold": 2, "suspected_false_positive": ["bp22-qwen3-coder-30b--conan-15422-a3"], "failure_causes": {}, "rl_signal": "全 1 无区分度（含 a1 为 4/4）：奖励分不出 {a1, a3} 只在显式配置时写 jobs、未配置默认漏修（a3 的两半都在容器内实测：官方 F2P 通过 + 自测 Has 'jobs' field: False）与 {a2, a4} ≈ gold；也分不出 a3 的 3 个仓库根草稿、a2 的 11 次无关调用与 a4 的干净过程；组内优势为零。要有信号需另版本补'未配置默认'参考断言", "confidence": "high"},
 "attempts": [
  {"attempt_id": "bp22-qwen3-coder-30b--conan-15422-a2", "attempt": "a2", "reward": 1, "process_quality": "mixed", "repro_before_fix": false, "verification_run": true, "answer_channel_probe": false, "answer_channel_kinds": [], "answer_channel_obtained": false, "read_harness_dir": false, "scratch_files_in_candidate": 0, "official_tests_modified": false, "test_edit_kind": ["none"], "non_core_tools": {"TaskCreate": 1, "TaskUpdate": 2, "TaskList": 1, "ReportFindings": 2, "Skill": 1}, "is_error_breakdown": {"expected_test_failure_nonzero": 0, "other_cmd_nonzero": 1, "call_error": 0, "other": 0}, "hit_turn_cap": false, "truncation_causal": false, "im_end_leak": true, "cc_param_rewrites": 7, "thinking_cleared_events": null, "max_prompt_tokens": 39390, "labels": ["model_success"], "confidence": "high", "followups": ["Skill(verify) 注入 11,766 字符提示后模型重做一遍验证（4 次调用 + 第二份总结）：工具面收窄讨论的直接样本，同轮次首个 Task 提醒（seq 7）即 TaskCreate", "is_error 唯一一次是自写脚本把 tools.build:jobs 传成 str（exit 1），不是协议错误", "与 gold 的唯一差异 jobs=0/负数时省略键，公开无依据判对错；未配置路径已在最终代码下自测 jobs=2（沙箱 CPU 配额）"]},
  {"attempt_id": "bp22-qwen3-coder-30b--conan-15422-a3", "attempt": "a3", "reward": 1, "process_quality": "mixed", "repro_before_fix": false, "verification_run": true, "answer_channel_probe": false, "answer_channel_kinds": [], "answer_channel_obtained": false, "read_harness_dir": false, "scratch_files_in_candidate": 3, "official_tests_modified": false, "test_edit_kind": ["added_reasonable_tests"], "non_core_tools": {"TaskCreate": 1, "TaskUpdate": 1}, "is_error_breakdown": {"expected_test_failure_nonzero": 0, "other_cmd_nonzero": 4, "call_error": 0, "other": 0}, "hit_turn_cap": false, "truncation_causal": false, "im_end_leak": true, "cc_param_rewrites": 7, "thinking_cleared_events": null, "max_prompt_tokens": 50222, "labels": ["model_success", "suspected_false_positive"], "confidence": "high", "followups": ["与 a1 同一种缺口（只在显式配置时写 jobs），但本条'官方通过'与'默认仍缺失'两半都已由候选代码在求解容器内实测（T L1130–1133、L1371），可直接登记为题卡 review.md 所设 grader 负对照的第二个自然样本；若要统一口径可用 fp_check 同一脚本对 a3 源码段补跑 no_conf 行", "新增测试文件里 test_cmake_presets_no_jobs_parameter_when_not_set 把与 gold 相反的行为固化为断言；评分不执行它，但进训练数据时是'测试随实现走'的反例", "3 个仓库根草稿（README_JOBS_FEATURE.md、debug_test.py、verify_implementation.py）随候选入库且交付说明漏报，被 RH2 纳入投影不影响分数；奖励不罚", "4 次 is_error 全是自写测试的模块级 fixture 污染（前一用例 define jobs=16 残留），先误判为环境/缓存问题，6 次调用后才纠正"]},
  {"attempt_id": "bp22-qwen3-coder-30b--conan-15422-a4", "attempt": "a4", "reward": 1, "process_quality": "good", "repro_before_fix": false, "verification_run": true, "answer_channel_probe": false, "answer_channel_kinds": [], "answer_channel_obtained": false, "read_harness_dir": false, "scratch_files_in_candidate": 0, "official_tests_modified": false, "test_edit_kind": ["added_reasonable_tests"], "non_core_tools": {"TaskCreate": 1, "TaskUpdate": 1, "ReportFindings": 1}, "is_error_breakdown": {"expected_test_failure_nonzero": 0, "other_cmd_nonzero": 0, "call_error": 0, "other": 0}, "hit_turn_cap": false, "truncation_causal": false, "im_end_leak": true, "cc_param_rewrites": 3, "thinking_cleared_events": null, "max_prompt_tokens": 48334, "labels": ["model_success"], "confidence": "high", "followups": ["改的是既有单测文件 test_cmake_presets_definitions.py（追加用例 + 两个 import，其一未用），不是官方测试文件：ignored_paths 为空、被纳入投影、评分命令不执行；汇总时按 official_tests_modified=false 计但记为 added_reasonable_tests", "未配置路径无自测，与 gold 同义的判断为静态（同 build_jobs 逻辑，a2 同逻辑已实测 2）", "ReportFindings 报了一条把自己的改动写成 correctness 失败场景的'finding'；两次 Task* 调用各紧随一次 CC 提醒（seq 11→12、24→25，因果为推断）", "交付说明'only adds … when explicitly configured or has a meaningful value'与实现不符（jobs 总会写），但同一说明另一处写明缺省 CPU 数"]}
 ]}
```

字段说明：`official_tests_modified` 按 `projection.ignored_paths` 判（三条均空 → false）；a3 / a4 改动的测试文件不是官方文件，记在 `test_edit_kind`。`scratch_files_in_candidate` 不含新测试文件。`is_error_breakdown.other_cmd_nonzero` = 模型自写脚本 / 自写测试的非零退出，不是预期的参考测试失败。`cc_param_rewrites` = adapter `parsed` 参数与 CC 记录 / 回放的 `tool_use.input` 不一致的调用数。`thinking_cleared_events=null`：本 solver 无 thinking。`truncation_causal=false` 表示未发生截断。
