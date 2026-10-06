# Pandas 50319 Coder 首轮新增原件与有限语义窄核（2026-10-03）

**结论：本轮原 1 分可信，完整候选通过当前公开“None 或正确格式”契约及 109 条来源 P2P；未发现误奖、误拒或需阻断另一模型首轮的题级问题。模型自己的扩展构建和端到端验证没有闭合。** 正式 grader 随后真实 Cython 转换、编译、链接并复制 parsing 扩展，115 个物理节点全通过。不得把正式通过改写成模型已经验证通过，也不得从通过推断具体返回分支、当前候选数组回退或稳定成功率。

仅覆盖 `gpu1003-pandas50319-coder-a1` 新首臂。配对请求另一模型尚未闭合；不因此追加采样、改候选或改测试，不授予训练资格。旧静态材料、CPU 六臂及原公开 actor 只复用既有适用版本，没有重复审查。

## 独立角色与原件核收

本包非作者 subagent 没有编写或执行本轮求解、评分及作者分析。已接触题主摘要，并读取作者分析，因此不是盲审；关键计数、候选字节、轨迹与编译结论均从原件重新计算。只做本机只读 SHA/字节、JSON/日志/轨迹解析、tar 成员只读、base64 解码及内存文本对照。没有网络、SSH、Docker、CPU/GPU、安装、项目导入、动态实验或新采样；唯一写入是排他新建本报告，未改作者材料、候选、原件、旧报告、共享代码或总账。

快照根 S 为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas50319-coder-a1/`；本 job 根 J 为 `S/queue_v31/results/gpu1003-pandas50319-coder-a1/`。逐件独立重算闭合 manifest 所列 **531 件、239,938,367 字节，全部 SHA/大小一致**，仅将当前 job 纳入结论。

- 回执：`runs/ordinary_gpu_probe_20261002/migration_20261003/pandas50319_first_coder_execution_receipt_v1.json`，2,158 字节，SHA256 `a8c170f1c43ff75ef876265563096cf92acb739f4c05a04f2ae961a09c1f4824`。
- 同目录闭合 manifest：`gpu1003-pandas50319-coder-a1_closed_manifest_v1.json`，100,441 字节，SHA256 `fcfd40b0ae30e68afcfb5088d25bc1c3a9273d35d80ccbb11e6568dcdee70589`。
- code_v8 source manifest SHA256 `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`；queue_v31 固定 inputs manifest SHA256 `ca25283e7715cbd46eb345c60fdcde59d7f24bd1cc2ce0f2cda1be0059e5378d`。这些文件在上述 531 件中，未重审全发布或其它 job。

新增 GPU execution 审查 `runs/ordinary_gpu_probe_20261002/reviews/closed_three_execution_increment_non_author_20261003_v1.md/json` 的当前臂结论与本轮一致（JSON SHA256 `1df8968be5fb6399a856cf37c48141d9550253a002255ddc9f3576679bece4ed`）。它的 Pandas 大归档 SHA 复用 sync_v3；本核另独立重算全部 manifest 文件，语义结论不由那份 execution 审查替代。

## 原分、参考与完整七成员

`J/grading/report.json` 原 reward=1、outcome=resolved，2/2 F2P、0/109 P2P 失败，execution/infra failure 均 null。原 `evallog_gpu1003-pandas50319-code_e0352640.eval.log` 为 465,072 字节，SHA256 `81961bcafcc9c45cce46788e544abd8236561ddf5c040ececfaa4a8aea82df7c`。

独立把当前 `S/prepared_dask_pandas_four_code8_v1/pandas50319/private/host_grading_views.jsonl` 的每条参考映射到原日志：2 F 精确匹配；109 P 包括 94 个精确引用、12 个唯一旧截断引用和 3 个显式绑定组。3 组包含 1/2/4 个成员，故 109 来源 P 对应 **113 个不同物理节点**。2 F 加 113 P 正好覆盖全部 115 节点，全部 PASSED，无缺席、skip、未归类或重复；来源 P 列表与原 P 列表逐字相同。日志 5023/5024 行是新 `[reported]`、`[another-dot-date]` 两节点 PASSED；5074 行 footer 为 `115 passed, 2 warnings in 0.21s`。

下表成员均带完整前缀 `pandas/tests/tslibs/test_parsing.py::`，行号指原 eval.log。绑定消费身份为 `d2d78ebe7df4115b4d2d8e748fd83ff54e68c3234b3d91c814bff65c468097cd`，与已核版本一致；没有沿用单个旧别名的末值替代完整组。

| 完整成员后缀 | 原状态 | 日志行 |
| --- | --- | --- |
| `test_is_iso_format[%Y\\%m\\%d %H:%M:%S-True]` | PASSED | 5056 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00-%Y-%m-%d %H:%M:%S]` | PASSED | 4996 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00.000000-%Y-%m-%d %H:%M:%S.%f]` | PASSED | 5020 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%d-%m %H:%M:%S-True-None]` | PASSED | 5051 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%m-%d %H:%M:%S-False-None]` | PASSED | 5050 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%d-%m %H:%M:%S-True-None]` | PASSED | 5047 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%m-%d %H:%M:%S-False-None]` | PASSED | 5046 |

当前有效测试补丁 SHA256 `0cef8c604fb79cd8d677087b28a09736751617e5aacfb312cb8fede48d3cae8f`，host view 的 test_patch 与 effective_test_patch 逐字相等。原 eval.log 1693–1704 行从精确 base 恢复 `test_parsing.py`、核 base SHA `71a22bdd…ff4d` 并正常应用补丁，1725–1737 行 attest 为 restore1/apply0/present1/absent0/setupOK1。原旧 F 已退休；新两例调用真实 `guess_datetime_format`，仅在结果非 None 时检查 str 类型及 `datetime.strptime` 的日期、时间和微秒。因此 2 F 通过证明这个有限契约；原件不记录 None/格式分支，也未在这两例运行数组转换，不能移用旧 CPU None 候选的数组结果。

## 完整候选与实际新扩展构建

FrozenPatch canonical digest 独立重算为 `sha256:6db0193491c27c2269a659ee679f7fcebeddcc08c614af8f28e8f89aa5cb01d6`；baseline manifest 为 `sha256:3da93f2518e48272209d08a9045857954b4b5110e68ffa8a17946e653b3c504d`，与 result/attempt/projection 相等，base HEAD 为 `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`。actor baseline census 和 grader rebuild census 逐字相等；只读 baseline.tar 的 pyx 为 38,455 字节、SHA256 `5c8e81b9914bc6448b21a909cf13d3c2e7799e63e92d386042dd4262b6d048aa`。

FP **28 个 entry 全部 base64 解码并核 content_digest**，同时与 attempt 成员摘要相等；projection 按路径和顺序包含全部 28 个，没有运输过滤。26 add、2 modify：19 个其它模块构建产物（9 `.so`、10 `.o`，其中 join.o 为原零字节）、7 个新增诊断脚本，及修改的 `parsing.pyx` 与生成 `parsing.c`。不称为仅运输三行源代码；原 review diff 7,908,302 字节，FP JSON 33,322,327 字节是真实候选成本。

pyx payload 为 38,585 字节、SHA256 `6e3ad15b0a4dd1ebeed5cc41387719c1859537e468fda76da9e534ed9e9af10d`。从 baseline 独立生成的小 diff，逐字等于作者 `source_delta.patch`：只在 `_fill_token` 的 `seconds, nanoseconds = token.split(".")` 后加入注释及 `if seconds == "": seconds = "0"`，原后续补齐/微秒截取/最终格式匹配逻辑保留。生成 C 为 1,741,170 字节、SHA256 `1adea9d95c69d8409ed7ae2c4c3539a753ec9094414dffa7a95c8231d3b7385c`；15342 行执行 Unicode 空字符串比较，15352–15353 行实际赋字符串0，且3078/3105行常量及34234/34312行映射一致。不是仅同步注释。

FP 中没有 parsing 的 `.so` 或 `.o`。原 eval.log 3165 行执行 `python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true`；3173–3174 行明确因 pyx 改变而 Cythonizing；3882/3884/3889 行依次构建 parsing、编译新 parsing.c、链接新扩展至独立临时 build 目录；4023 行将新 parsing.so 复制回 checkout。4919 行 installRC0，4929 行以新 pytest 进程运行唯一正式 `pandas/tests/tslibs/test_parsing.py`，5082 行 testRC0。diagnostics 原 `compile_probe=null` 保留；日志足以证明这次实际编译，不能把 null 改成通用编译探测通过，也未凭不存在的最终 `.so` SHA/mtime 记录扩展身份。

正式 patch hygiene 为 clean、clean checkout replay=true、test_files_modified=false、forbidden_path_touched=false。helper 脚本仍在候选中，正式命令没有拿这些自测替代参考测试。control_surface 为保护4目录/1文件、EXPECTED_FILES1、missing0、protectOK1；runner前后 SHA均 `1cfac6828a8ce1101528108a0a3379da1fe8e2b0ba4a9021ea32c5ffc26e13a4`，runner_integrity_changed=false。评分脚本 digest `38c1676d0dc7faacf71684b51a62dfc386cfa31cd906964ab75e58ff792939c4`、材料身份 `aec98b708135a7f293dc888a0a4cf70090584a6ea40fd1a32f0f087aac652979` 与实际加载的 `ok:gold_ledger.jsonl:rpt_grading_a29b64e6` 相等；资格账本 candidate.kind=gold、report resolved/2F/109P/missing0，并未新增训练资格。

## 轨迹：异步构建未闭合，最终承认待重建

原 `J/attempt/trajectory.jsonl`（与 harness 副本同字节）为 307,622 字节、SHA256 `2758e9ee18be640e4049c6faeee1509480c562522ba58e07433843f501a2e9f5`，共322行。26 个唯一 tool ID 都有对应结果，协议层最多1个未返回调用；独立计数为 Bash14/Write7/Read4/Edit1，3个 is_error，不把流式分块重复计请求。

| 原轨迹行 / 工具 | 实际记录与意义 |
| --- | --- |
| 45→49，工具4 `toolu_19c38907ed31ac5f` | 原真实调用报 `ValueError: invalid literal for int() with base 10: ''`；脚本捕获异常，tool is_error=false，不代表行为成功。 |
| 67→71、89→93，工具6/8 | lexer 打印含日期分隔符 `.`；私有 cdef `_fill_token` 导入失败。Python复制逻辑证实 `00.000` 本身正常，模型最初归因不成立，随后纠正。没有真实 Cython 函数逐token追踪，确切崩溃token仍未直接观测。 |
| 115→122，工具10 `toolu_b376b33b3a28e377` | `python setup.py build_ext --inplace` 返回后台job `bmdjgbiy1`，119/121 行登记 started/backgrounded，未记录成功终态。 |
| 171→175、210→214、258→262 | 源修改后的真实调用仍为原 ValueError，构建日志仍在 interval 等其它模块；复制逻辑打印通过及 import successful 均不能证明新 parsing 扩展已就绪。 |
| 280→284，工具24 `toolu_f6cf6f2551e06404` | `python test_datetime_format_fix.py` 返回1，unittest真实 ERROR/FAIL，尚未验证修复后的完整编译函数。 |
| 306→313，工具26 `toolu_aa6c49f93605ad4a` | 模型执行 `pkill -f "build_ext"`；312 行后台通知 failed/exit144，313 行工具也返回144。这是模型主动停止，不能归为 harness 预算截断。 |
| 318、322终结 | 模型仍判断源修法成立，但明确说完整 pandas rebuild 才能 end-to-end 验证；没有宣称真实编译测试已经全通过。 |

后台编译与后续读取、复制逻辑和诊断确有执行重叠，不能笼统写全程串行；重叠没有解决编译终态等待。实际暴露工具仅 Bash/Edit/NotebookEdit/Read/Write，没有 Task/agent 调用入口，跨 agent 能力不可评估；不把推理服务 max_running_requests1 推为执行层普遍不支持并行。

独立核 gateway 28 行中27次生成、1次 count_tokens；生成序号1–27和原响应一一对应，全部 HTTP200/stream_error null，26 tool_use＋1 end_turn。累计 input588,802/output5,738、单请求已报告 input峰值29,031、cache0；累计量不是单个上下文长度。solve177.117秒，CC173.266秒/API48.257秒，harness0/completed/end_turn；原预算240回合/10,800秒/196,608上下文，实际27请求 max_tokens均65536。CC modelUsage.maxOutputTokens32000 原值保留，没有预算截断证据。

原计时口径一致：总评分1013.803秒，受信准备604.545759秒；后续评估包装329.199923秒，含由时间标记计算的安装324.623秒与测试包装3.081秒；pytest footer0.21秒。原 cleanup/parser 时间null保留，不冒填0，也不把受信准备全部叫pytest耗时。

## 必要身份、收尾与作者比对

actor 原 facts 为 UID54321、testbed Python3.8.20；baseline/prompt均在启动前冻结，solver_prompt与attempt/prompt逐字一致。按本job精确容器名和run_id从原 resource JSONL 独立筛得19个actor样本（11:48:05.067731–11:52:36.372436Z）、67个grader样本（11:53:06.512983–12:09:41.086458Z），同角色内container ID稳定、actual image均 `sha256:a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a`，与作者读回逐字一致；排除同run_id relay。原记录 image_identity `e645e434…ba21e` 是 manifest，不能与actual ID混写，采样间隙仍未知。

`S/diagnostics/QUEUE_V31_gpu1003-pandas50319-coder-a1_before/` 的独立现场读回在11:47:51.548325–51.742907Z，engine/adapter 前后ID/PID/启动时间稳定、restart0、模型只读挂载和实际服务配置匹配，gateway model_sent均 Qwen3-Coder-30B-A3B-Instruct；下载绑定 revision为 `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`。25个列明文件的实际大小全相等（含16分片）。原下载 manifest files_count28 与 files数组25的元数据差异保留；不据此推断丢权重或题级阻断。现场未重算各权重SHA，也没有GPU内存权重证明。

原 `gateway_audit.checkpoint_identity_verified=false` 及 input_check `config_only=true/runtime_request_and_sglang_readback_verified=false` 均保留；上述独立读回不静默改写原标记，也不成为训练 typed actor 租约或训练资格。

actor原 cleanup为 container_rm0、container_left空、label容器/网络空、network/relay failures空、cleanup_ok=true；pre_drain residual0，gateway撤销且active0/drained=true。grader result/status cleanup_ok=true，manager创建1/移除1，containers_open/supply_open/cleanup_failures均空。只闭合本job原收尾记录，不声称新做现场最终残留查询或全机零残留。

作者报告 `tasks/pandas-dev__pandas-50319/probe_analysis_coder_20261003_v1.md` SHA256 `b1a42358e671d25506d3b907f40a5103bc0081f83fc1002ce75bfca988ff4004`；结构化作者 evidence `runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261003/pandas50319_coder_a1_v1/evidence.json` SHA256 `6b56e727b08e97bef97ec77fea86078b14bdacaed12eec5f103a0c82071f1ec3`。其关键结论、source_delta、参考/绑定、构建、计数、计时和身份边界与上述独立核查一致，未发现需改作者结论的实质错误。本轮新增核查完成；具体None/格式分支、当前候选数组回退、连续资源/权重身份和另一模型首轮继续留未知，不为这些限定范围另起实验。
