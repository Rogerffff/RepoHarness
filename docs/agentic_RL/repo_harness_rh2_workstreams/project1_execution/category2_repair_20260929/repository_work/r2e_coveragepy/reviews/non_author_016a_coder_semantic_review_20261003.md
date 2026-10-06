# 016A Coder 首臂非作者候选语义窄核（2026-10-03）

结论：**现行 R6 题级目标通过；无具体新材料阻断，当前不需追加 CPU。** 保留原 reward=1、15/15 参考通过、另 1 非参考 SKIP。候选存在实际数据库孤儿行和弱自测，不能据此称全面正确、全仓无回归，亦不授训练或原 benchmark 资格。

核查者为 Codex 非作者 subagent `/root/coveragepy_016a_cpu_review`，未编写本题材料或 Coder 候选。本次不是 fresh public reader，已接触本题公开/私有 R6 材料、既有 CPU 原件、本人旧 CPU/Qwen 审查和本臂完整原件；不使用其他题私有方案。只做本地标准库读取、SHA、AST、tar 成员内存读取、SQLite 内存 `deserialize` 加 `query_only` 查询；未导入或执行候选、未跑项目测试、CPU、SSH、Docker、安装或模型服务。此次只写本报告及同名 JSON。

## 依据与复用边界

本臂原件为 `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1`。总回执 SHA 为 `d987ce644beaf5f0da8e72258c5cf69a12f244ea76da23ecbe0d48e7c1fc1d33`。固定 R6 release manifest 为 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`，适用 001 保留项、086 隐藏测试、087 公开 statement。

复用既有非作者 CPU 审查对 R6 身份、正式 14 行判别力及实际公开交付的核实，不重审已通过运输；退出、清理和原应用绑定复用 `coverage016a_coder_a1_execution_review_v1.json` 的有限结论。本人独立读取本臂原 FrozenPatch 全 7 项、baseline 源、完整轨迹工具参数/返回与模型解释、原测试日志及 15 参考诊断；原日志完整测试摘要独立解析后，逐键等于旧 CPU 已核的固定 R6 expected map。所有这类标准库检查都是本地审查观察，不称 CPU 测试或模型结果。

`solver_prompt.txt` 包含完整现行 statement。现行公开目标是不可 UTF-8 编码文件名不令 `save` 崩溃，允许跳过或内部处理，不硬绑告警与实现层；086 同时要求正常文件、可编码非 ASCII 文件的 line/branch 数据及新对象读回。本臂正式原件为 `15 passed, 1 skipped in 0.98 seconds`、`RH2_TEST_RC=0`；15 参考逐键均 PASSED，额外 SKIP 为 `test_1.py:199` 的既有耗时项，不能记作参考失败或成功。

## 候选与正常数据语义

| FrozenPatch 路径 | 操作 | 字节 | 内容 SHA256 |
| --- | --- | ---: | --- |
| .coverage | add | 53248 | `d7d502e01a0eb60ffa062121e7a9ff7ead4a2c85a22bfb884ba60a8e0c76db7c` |
| comprehensive_test.py | add | 918 | `fb791eb6d565eb4135634b3755baf8b3900ed357786071b2bfa9314492de1bfe` |
| coverage/sqldata.py | modify | 42323 | `7846e94111d3db82560dee5c47a5e4ed5940ce6849921fa108226dd7b6c06aeb` |
| final_test.py | add | 1117 | `d2b50ee14108e5974368264c727990311ecbec93545e2f072a2132d73fbacd2b` |
| reproduce_issue.py | add | 236 | `f2873e3359b459ea135bbedf62335452e2c3d551072394cbb7fa76af14790845` |
| test_normal.py | add | 223 | `ff249e937085325b22f7c8833b85d91463afb96412127ef4fdf1b29954892564` |
| tests/modules/.coverage | add | 53248 | `7ec1d77fa342d663a584359bef213b8961f827c639abea994f928f11c4572157` |

各项解码字节的 SHA 与 FP 内容声明一致；四个辅助脚本和两份数据库在 baseline tar 中均不存在。baseline `coverage/sqldata.py` SHA 为 `d3823873dac7bcc15024e490d099239ad4beef3fcdffea671291bc6401b2c4b7`。完整 diff 和 AST 方法对比表明仅修改 `CoverageData._file_id`，没有增删源方法，没有改既有公开测试、评分入口、fixture/conftest 或正式受保护路径。

最终 `_file_id`（候选 358–379 行）仅在 SQLite 插入发生 `UnicodeEncodeError` 时可选告警并 `return None`，不缓存坏名。正常文件的插入及 `_file_map` 路径保留原行为，`lines`/`arcs` 查询对 None 继续返回 None；`measured_files`（773–775）返回 map 的键，因此从源码上避免旧 Qwen 把坏名缓存为 None 后仍列入测量文件的已证问题。本臂没有新增同对象/新对象的枚举运行，不能把这个源码判断说成实际 API 复现。

正常 line/branch 与 fresh read 的成功以本臂实际正式测试为依据。`update`（595–608）读取源数据库时用 `INNER JOIN file`；合法文件的数据仍走未改路径，孤儿行不会成为合法文件数据。坏名 combine、plugin 和重复添加未在本次运行检查，不能把正常数据测试外推到全部这些边界。

## 实际质量缺陷与静态边界

**C1，已证孤儿数据行。** 根 `.coverage` 的 `file` 表只有 `/testbed/normal.py`（id=1）；`line_bits` 同时有 `(file_id=1, context_id=1, numbits=02)` 和 `(file_id=NULL, context_id=1, numbits=02)`，前者实际记录正常第 1 行，后者没有可归属文件。其 meta `sys_argv` 是 `['final_test.py']`。原因是 `add_lines`（453–463）未检查 `_file_id` 返回值，仍插入 None。因此最终实现只跳过 file 表插入，不能说完整地丢弃了该文件数据。

两份原二进制均为 53248 字节，内存只读 `quick_check` 为 ok，`foreign_key_check` 为空；SQLite 允许 NULL 外键，这两项不证明 API 逻辑完整。`tests/modules/.coverage` 为公开测试留下的 9 个文件、3 条 line_bits，无 NULL file_id；两份 arc/tracer 表均为空。本次没有实际 branch 孤儿行证据。JSON 保存原表记录、内容 SHA 和解码行号，可独立对拍。

**C2，仅静态边界风险。** `add_arcs`（484–490）也未筛 None，可能写 NULL arc 行；重复添加坏名时 SQL `file_id = NULL` 不匹配旧行，唯一约束允许 NULL，可能累积数据。`touch_file`（554–557）未检查返回值，指定 plugin 后进入 `add_file_tracers`（522–526）仍可抛“unmeasured file”；未改的 `collector.flush_data`（411–429）也在写 lines/arcs 后写 tracer。这里已指出具体控制路径，但没有本次运行复现，不当作已证 plugin 失败或新材料阻断。

## 自测是否支持模型结论

完整轨迹共 366 行，读取了 30 个完整工具调用的参数和返回及模型解释。L32/36 首次复现编码异常；L97 临时使用 md5 替代路径，模型 L106 自行放弃，L110/114 按过时 old_string 编辑失败；L145 完整方法替换才形成最终候选，L158/162 原复现不再崩溃。临时 hash 方案与失败 Edit 不用于判断最终源码。

L193/199 的 `154 passed, 1 skipped` 是 `tests/test_api.py tests/test_data.py tests/test_oddball.py` 三模块；L230/234 普通 `test_adding_lines`、L243/247 普通 `test_adding_arcs` 各 1 pass 都是这 154 项的子项，不是新增坏名 branch 覆盖，也不是全仓测试。

四份新增 helper 均没有保存后 lines/arcs/measured_files 或 fresh read 的数据断言。`reproduce_issue.py` 和 `test_normal.py` 只检查有无异常；`comprehensive_test.py` 在编码失败时返回 False，只有主脚本入口才据此退出 1，若由 pytest 调用其测试函数，False 返回本身不会自动使测试失败。`final_test.py` 三段都捕获 `Exception` 后只打印失败，最后无条件打印成功，不传播失败退出。L291/295 实际打印成功支持这次“未见崩溃”，却不能据退出 0 验证数据内容。未见旧 Qwen 那种自测断言失败后删弱断言的过程；本臂 helper 从起始就很弱。模型最终“所有现有功能完全正常”等说法超过这些证据范围。

`reproduce_issue.py`、`test_normal.py`、`final_test.py` 顶层使用默认 `Coverage().save()`，导入会写默认 `.coverage`；根数据库 meta 已证 final helper 的实际写入。根 `*_test.py`/`test_*.py` 在更宽 pytest 收集时可能产生副作用，这一点未运行检查。本次正式入口仅取 r2e 测试，实际公开命令明确取三个原模块，不收集这些根 helper；未发现正式评分控制或既有公开测试被篡改，也未把生成数据库误作参考测试证据。

## 当前用途与剩余事项

当前允许保留普通基座探针的版本化目标成功事实和首臂原分，同时携带 C1–C4 的候选质量说明。无须因孤儿行补做本题 CPU，也无本次新材料阻断；不授训练资格。父线程负责完整七维、效率和总账，本报告不替代这些工作。

如日后要核销候选质量，可定向核坏名重复 lines/arcs 的孤儿行及增长、combine 后合法数据、坏名 plugin 的 touch/collector flush。它们是可选后续质量用途，不是当前追加实验要求。本次未核的运行边界保持未知，旧 Qwen 报告及历史 CPU 原件未改。

关键原件 SHA（其余证据、完整工具参数/返回、diff 与数据库记录见同名 JSON）：

- `runs/ordinary_gpu_probe_20261002/receipts/r2e-coveragepy-016a-r086087-cpu-r6-20261003-v1_two_model_v1.json`：`d987ce644beaf5f0da8e72258c5cf69a12f244ea76da23ecbe0d48e7c1fc1d33`。
- `runs/ordinary_gpu_probe_20261002/reviews/coverage016a_coder_a1_execution_review_v1.json`：`535fd4680e6789ec4b14449d97e0c0d8466a4e9f1295411dff28730243f94274`。
- `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1/attempt/trajectory.jsonl`：`3e74309b98c2edfff170128f2af0b728a6c96f0a0300602760a775d92f1126e3`。
- `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1/attempt/frozen/frozen_patch.json`：`f33cda944ad820a4b68ccf110d337bb2727c8232f0d0637baca2b36a4575c315`。
- `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1/attempt/frozen/baseline.tar`：`4a94e2246f9eb0befd317ed25336ad89bb14360d24bdc400136359d38069bd38`。
- `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1/grading/eval_logs/evallog_gpu1003-coverage016a-cod_3141e7cf.diagnostics.json`：`0730fae68e2eb1c4cf5ee5254c32e973c1fc739e35ca4e5a4fb8df58282997fd`。
- `runs/ordinary_gpu_probe_20261002/remote/queue_v16r2/results/gpu1003-coverage016a-coder-a1/grading/eval_logs/evallog_gpu1003-coverage016a-cod_3141e7cf.eval.log`：`284ef3ae1e27b51b40543318e981c45f6ddd865d95d00ae933ca838479d0e490`。
