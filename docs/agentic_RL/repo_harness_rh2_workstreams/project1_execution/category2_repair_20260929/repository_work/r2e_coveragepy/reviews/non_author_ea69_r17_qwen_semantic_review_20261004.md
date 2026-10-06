# EA69 R17 Qwen 首臂：非作者语义与边界核查

核查日期：2026-10-04。核查者沿用已有接触上下文，已读本题私有评分与候选，**不是 fresh public reader**。仅审 `gpu1003-coverageea69-r17-qwen36-a1`、本次 Qwen CPU 边界及新增评分方法；旧 CPU、Coder 已验部分按适用版本复用。本轮未启动任何作业或项目测试，未改题面、候选、评分或总账。

## 结论

原 R17 Qwen 的执行、运输和正式评分有效：**raw1、49/49、test RC0；install skipped，RC null**。固定 parser 对原完整测试段逐键重放，与原49键 expected 完全一致。正常用户两行内容 fixture、两次生成的真实 Git 检查通过；这不是完整公开目标通过。

候选将 `/*` 的文本子串存在当作实际 Git 忽略规则已经有效。新 CPU 原件证明四种已有内容输入在两轮生成均漏忽略，因而候选没有满足实际已交付的“保留用户内容，同时所有生成产物被忽略，再生成仍成立”目标。这是候选行为缺陷及 R17 评分覆盖盲区，不能归为材料无法运行，也不能重写原49分。

**51键草稿受影响窄验通过独立核查，可支持最小普通发布请求。** 发布后仍需核新评分身份的实际消费与补验收；当前八次单方法运行不是正式完整51键评分。保留 R17 评分完整性阻断，直至该缺口修复并实际复验。没有新增公开目标、模型重跑要求或训练资格；不由单臂推断稳定能力。

## 实现、测试控制与残留

生产实现仅在 `coverage/html.py` 增加末尾调用和 `make_local_gitignore_file()`：无文件写 `/*`；已有文件读内容，若不含该子串则以 append 写入并必要时补换行。其余生产 AST 保持基线。正常路径保留内容，且 `/*` 本身能覆盖特殊 CSS 文件名。问题是注释、嵌套规则、否定规则或被后续例外覆盖的模式都可能含相同子串。

完整 FrozenPatch 有两项，均 regular/100644：生产 html.py（18536B）和 `.coverage`（53248B），不能称“只改 html.py”。SQLite 只读核查为84条 file路径、2条 line_bits、0 arc，全来自 `/testbed`；84路径条目不等于84个实际被覆盖文件或84个测试。未见私测/控制路径；未改公开测试、conftest或runner，未据此认定作弊或误评分。DB是未清理的自测残留，其所有消费风险尚未全面验证。原正式 projection 保留两项。

完整303行轨迹及17工具结果逐项读回（11 Bash、4 Read、2 Edit），0 tool_result error。模型先读完整生产源码和公开 HTML 测试，两次 Edit 后未再修生产逻辑。HTML46项跑4次：baseline一次，修改后三次；test_coverage.py84项一次，公开不同用例并集130。公开兼容命令实际含 `RH2_PUBLIC_SPY_ENCODING_OK=1`，46通过、2 warning；它只在本进程转发 open args/kwargs，保留原 `mode.startswith('w')` 记录与断言，没有弱化测试文件。

5个附加断言场景和2次 Git 观察不能与回归数量相加。临时源码由无filename的 `exec(open(...).read())` 执行，`Coverage(source='.')` 对应cwd而非该临时样本，使自测采集针对性弱。首次 `git add -f` 主动stage文件，不能证明忽略；模型识别该错误后改为未stage的status观察，但仍无assert/子命令RC检查，并用绝对路径比对相对status文字。实际 report空status是普通路径观察，后续“全部正确”结论超出证据。两次NoDataCollected警告保留；管道tail可能掩盖退出码，实际所读测试footer仍通过。弱自测与残留不是自动作弊结论。

## 真实 Git 边界闭批

21文件、4741766B逐SHA/bytes核回；原GPU精确 `e23fbbed…` 镜像、完整原两项FP及360路径基线恢复，原候选未修。实际 UID/GID54321、Python3.7.9、Git2.34.1、2CPU/4GiB/512、网络关闭、无挂载。GPU运输的Git2.43.0与CPU版本分列，未把不同Git二进制称相同。容器/root仅负责准备，实际探针以UID54321运行。

| 臂 | 两轮全部生成产物被忽略的fixture | 结果 |
| --- | ---: | --- |
| baseline | 0/3 | 预期负对照 |
| safe_append | 10/10 | 正对照全部通过 |
| 原 Qwen | 6/10 | 四种已有规则输入失败 |

三臂23组、46次报告，386个生成路径/轮观察；Qwen失败50项：注释含`/*`、`cache/*`、`!/*`各两轮8文件未忽略；`/*`之后`!index.html`两轮仅index未忽略。正常内容、有效规则最后生效及4个CSS名字（普通、`!`、`#`、`[]`）均通过。已有内容前缀在这些Qwen输入仍保留，因此缺陷是实际忽略行为。

runner 用 `git check-ignore --no-index -q` 的退出0判ignored，退出1与实际status未忽略路径一致；`-v`只作说明，显式negation也有verbose输出，不能把非空输出当忽略。Git环境排除系统/用户规则，未stage生成文件。每fixture独立Git、实际源文件路径和明确data_file；原`.coverage`虽完整恢复，此窄验有意使用新data_file，不覆盖DB全部消费路径。job finished RC0是诊断完整完成，自有容器残留0，不是候选通过。

## 新增验收草稿

39文件、4488902B逐SHA/bytes与输出tar逐内容一致。原Qwen完整两项FP、Coder原单项FP恢复；同 `e23fbbed…` 镜像/UID及限制，八次 pytest 原日志均匹配诊断分类，无infra失败。每个方法单独运行，结果如下（RC）：

| 臂 | 字面CSS名字 | 已有模式行为 |
| --- | ---: | ---: |
| baseline | 1 | 1 |
| safe_append | 0 | 0 |
| 原 Qwen | 0 | 1 |
| 原 Coder | 1 | 0 |

Qwen失败方法在首输入/首轮 `report_rules_0/coverage_html.js` 即断言失败；Coder CSS方法在`!custom.css`首轮失败。**失败后循环早停，不能称该方法所有子场景已完成。** 四种Qwen反例的完整两轮证据来自上一独立boundary闭批；safe通过的两个方法完成各全部循环。诊断脚本预期RC只是辨别正负控制，不是新增正式expected标签。

去掉两个新方法后，v3测试与旧preserve_v1 AST完整一致；CSS方法与旧v2草稿AST一致。expected51保留旧49键与状态，仅增加两个PASSED键。CSS方法测试4种字面名字两轮；已有模式方法测试5种内容两轮，都用真实Git quiet退出码检查所有生成产物。这是在现有公开目标内填覆盖缺口，未加空行/CRLF/文本顺序/字节幂等要求，也不要求某种实现方式。新稿仍需发布/冻结/部署身份及实际消费验收，不能直接拿当前51草稿重写两臂原分。

## 身份、预算、消耗和终止

实际完整solver prompt和首request单个user文本与R17 statement+原brief精确匹配，prompt SHA `19aa60c7…`；该题面已经明确preserve和再次生成，未发现gold/私测泄露。base `7fd1ea39925f…`，code_v8、CC2.1.205、agent UID54321、环境与实际actor/grader镜像一致；worktree导入、解释器、公开compat预检成立。固定source/recipe/hidden/runner与既有R17身份对齐；360基线按Git100644/100755核语义，非声称POSIX权限逐位相等。原FP、baseline、projection、排除路径往返及评分镜像一致。

模型Qwen3.6-35B-A3B revision `995ad96e…`，BF16/TP1；actual capture读回绑定配置/挂载/HTTP与本job开始前时点。未重新哈希全部权重或证明显存权重身份，gateway audit `checkpoint_identity_verified=false`保留。adapter qwen3 parser与实际thinking块成立；engine配置不单独声称严格thinking模式。

统一预算10800s/240回合、context196608、wire单请求max_tokens65536、gateway1024；CC metadata32000分列，评分whole3600/setup300/apply120/test1800s。18生成+1count，累计输入429634/输出5597、cache0、峰33495/926；未触及已知预算。累计输入含重复上下文。solve54.147s、CC50.441s/API36.670s、gateway累计36.141s、actor118.722077s、grader48.817s各有不同边界；不当作纯GPU推理。重复HTML回归与完整大段读取有合并机会，但未测并行支持或收益。

正式grader peak348.84MB；13个有限资源切片中actor8行仅7有效，观察峰1057497088B/pids22；grader3样本观察134205440B。口径不同且采样有空档，不推断连续完整峰、共享GPU用量或196K容量。CC2.288095美元为别名估价，非实际账单。

completed/end_turn/harness0；actor清理、评分清理各通过，gateway revoked/drained、active0、pre_drain residual0，标签残留为空。pkill1表示未找到进程，不是残留。新两个CPU job finished0并自有容器0。原闭批manifest的paired_request_closed=false按当时版本保留；当前两臂returned/机械ACK引用题主后续状态，不混入旧R6 Qwen，不据此授训练资格。

## 证据与核查界限

| 原件入口 | SHA256 |
| --- | --- |
| GPU closed_manifest.json（146文件/11181414B） | `81445828267029f8d16f5543549c21428233160afd28dc012dd5d2a74a886795` |
| 原FrozenPatch文件 | `ae3ae46f8abc45f85acacfc1784babf8c9aaddf333ce535d8c6699a325f2f25c` |
| 原FP canonical | `a237757b19cee92e4226ec84cdb60104f11622ef13b125823dec2e2636715381` |
| 原正式eval.log | `f97119e956e59be238263e3037b156b4d29da44e2a545f099afc58959f1eb67d` |
| Qwen boundary闭批manifest | `0697b4e76f388b1af0e13d8f699ecabdad2330566393a3efb60ab539f41f3e87` |
| criterion v3闭批manifest | `0af8a1f3b721987c10ae7f61d56c665027045118f4e3f3bba3d579c3d83f7809` |
| v3测试草稿 | `6fa2ecfd00f917a12867d75b2c855875b88446411a7f35dc5ed429829d1998fa` |
| v3 expected草稿 | `d766068e50bbeb338cd8a63e80b0c0e97ea9cfc83dde44b5f6e59fc6647e6b2a` |

完整路径、每件SHA/bytes、49状态、8次结果、七维判定在同名JSON。146件做完整性核查，不冒称全部通用代码/诊断文件逐段语义重审；实际语义阅读为全部轨迹/FP、完整生产与公开HTML测试、正式49完整段及身份/预算/评分/清理相关原件；本次两个CPU闭批runner与所有结果、草稿受影响范围完整读回。复用旧R17公开空FP CPU及旧矩阵仅未变private/source/recipe/runner范围，Coder只复用原CSS专项报告与本次原FP/新方法。未重审旧506件，未运行新作业，未测多次稳定性。

独立核心结论形成后比对题主`model_analysis_qwen36_r17_a1_20261004.md/json`，关键行为、49分、DB范围、窄验和计时口径一致；题主pair状态属于后续引用。支持固定51键私有评分最小修订并按普通流程发布/补验收，原证据与历史50稿保留。
