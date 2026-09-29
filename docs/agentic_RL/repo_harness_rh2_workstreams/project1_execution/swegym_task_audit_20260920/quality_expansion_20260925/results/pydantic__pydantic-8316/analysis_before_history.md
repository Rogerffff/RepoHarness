# pydantic__pydantic-8316 — history 解封前独立主审

审查者：`/root/e25_main_pack08_pydantic`。仅静态文件/JSON/hash 操作，未执行、导入或测试项目，未联网/容器/实验/派生 agent；未读 history、旧质量结论、reviewer、根汇总。gold 与新增参数对缩写分词的局部修复有正证据，但 gold 同时收窄了旧字母→数字规则。初步保持 `needs_review/static_review`、`development_diagnostic`，不宣称 actor 或训练资格。

## 公开目标、范围消解与初态

题面核心明确：`to_snake('HTTPResponse')` 应为 `http_response`。标题和描述针对连续大写缩写之后正常单词的边界。题面说 CamelCase 全部只转小写过宽：旧代码已有 lowercase→uppercase 分词，普通 CamelToSnake 不存在这个缺陷。

附带 `to_camel` / `populate_by_name=True` 示例期望接收 HTTPResponseCode，但这不是同一缺陷：`alias_generators.py:20–30` 将 http_response_code 生成为 httpResponseCode；`config.py:131–159` 只保证可用原字段名或生成别名，`_generate_schema.py:926–973,1054–1061` 把生成器应用于字段名而非任意输入 key。`tests/test_aliases.py:382–413` 的原名/别名开关支持这个契约。HTTPResponseCode 两者皆非，因此该 ValidationError 不足以要求扩大为忽略大小写输入；gold 不修改 to_camel 并非自动构成漏修。公开范围宜说明此点，不能把用户附注当作新别名协议。

base=`20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24`，451 个跟踪条目静态导出。报告者 core2.10.1/Python3.11.3 不等于本 base；pyproject:64–69 要求 Python>=3.8、core==2.14.5，所引 grader Python3.8/pkg2.6.0a1。actual actor 输入、初始改动、忽略资产、UID/权限/PATH/包来源 unknown。

## 所有新增参数与双向需求—断言

完整 `test.patch` 只在 `test_camel2snake` 参数列表新增 `('CAMELToSnake','camel_to_snake')`。pytest 用原 `value,result` helper，唯一函数体断言为 `assert to_snake(value) == result`（base/tests/test_utils.py:519–542 全文已读，patch 后行号整体后移）。不新增 fixture/helper、内部正则检查或格式化误差要求；test_utils 从真实 alias_generators 导入，conftest autouse 仅设置错误 URL 环境变量。

| 需求/合理旧行为 | 公开依据 | 测试及决定性断言 | 覆盖与证据层次 |
|---|---|---|---|
| 缩写+正常单词边界，HTTPResponse→http_response | prompt 精确例；to_snake 文档 | 唯一 F2P `tests/test_utils.py::test_camel2snake[CAMELToSnake-camel_to_snake]` | 同类代表覆盖；没有直接 HTTPResponse 断言；原 noop 得 camelto_snake，gold PASS |
| 普通 camel/Pascal 分词 | 旧 to_snake 正则及 docstring | P2P CamelToSnake/camelToSnake→camel_to_snake | 已读全部参数，原 gold/noop 均 PASS |
| 原下划线与末尾数字行为保留 | test_utils:519–539 | P2P 各前后单/双下划线、Camel2/camel2/Camel2Snake/camel2Snake | 已读全部17个旧 to_snake 参数；各状态已核；数字前一字符均小写，未覆盖大写→数字 |
| 大写字母后数字的旧分隔规则 | base alias_generators.py:42 的 `[a-zA-Z]` | 无 A1/API2/HTTP2 预期；新增参数也无数字 | 具体回归风险与 check25 漏测；规范是否可改需确认，见下文静态推演 |
| 生成别名仍作用于字段名，validation/serialization 别名不被意外改名 | config:319–376；_generate_schema；aliases.py:82–112 | test_utils 的直接函数参数不测试模型字段 alias；test_aliases 公开测试读过但不在所选评分文件 | 集成覆盖缺失；单函数返回变化可影响真实验证/序列化 key |
| to_camel/to_pascal 旧转换不变 | alias_generators.py:7–30 | P2P test_on_lower_camel_* 3项；test_snake2camel_start_lower 与 test_snake2camel 各9参数 | 已读所有21项断言/参数及原日志，空串/单字母/下划线数字保持；不要求接受 HTTPResponseCode 输入 |

反向检查：CAMELToSnake 与题面 HTTPResponse 都是缩写末尾大写接大写+小写单词的边界，新增预期有公开依据，不限定正则或特定 helper。唯一参数不足以代表所有字符串；仍无 myHTTPResponse、多缩写混合、Unicode/标点或纯缩写数字覆盖。后二者没有精确定义时不能凭审查者偏好添加强制规则。

评分 expected 有143个 P2P，所有 ID 与原 gold/noop PASSED 行逐项机械核同，没有 expected 缺席/skip。语义完整读过全部38项相关旧 alias 转换参数/测试（17 snake + 18 camel/Pascal + 3基础例），其余 utility P2P 未通读；原名/别名集成测试仅公开静态证据，不谎称历史评分执行过。

## 完整 gold、调用者和具体回归风险

gold 只改 alias_generators.py 的 to_snake，全部新增注释/四次 re.sub/lambda 与 lower 已读。首个规则用 `([A-Z]+)([A-Z][a-z])` 分开缩写与正常单词；后续分开小写→大写、数字→大写、小写→数字。小写/数字→大写由旧联合类拆成两次；最后 lower 保留。`to_pascal`、`to_camel` 未改。

关键非必要变化：旧第一条 `[a-zA-Z]([0-9])` 被最后一条 `[a-z]([0-9])` 取代，大写→数字被删除。无需运行即可按模式静态推演：

| 输入 | base 路径与输出 | gold 路径与输出 | 解释 |
|---|---|---|---|
| HTTPResponse | 无旧匹配，lower→httpresponse | HTTP/Response 首规则分开→http_response | 精确公开目标局部修好 |
| CAMELToSnake | 仅 o/S 分开→camelto_snake | CAMEL/To 首规则及 o/S→camel_to_snake | 新 F2P 的变化 |
| A1 | A/1 匹配旧第一条→a_1 | 四条均不匹配→a1 | 已静态证明旧行为改变，非已执行实验 |
| API2 | I/2 匹配旧第一条→api_2 | 无大写/数字分割→api2 | 与缩写修复无直接必要关系，现有参数漏测 |

旧对 A1/API2 的精确输出未由专门测试/文档示例固定；数字命名惯例可有多种合理约定，因此不能直接把一切差异称为已确认用户可见缺陷。但保持既有明确代码规则是合理兼容要求，题面未授权收窄它；这值得在 check26 记录具体兼容疑点，与 check25 没有测试保护分开。若字段 A1 或 API2 用 `ConfigDict(alias_generator=to_snake)`，`_apply_alias_generator_to_field_info` 会把上述输出赋给 validation_alias/serialization_alias/alias；`AliasGenerator._generate_alias/generate_aliases` 另一公开调用路径同样使用 field_name。这说明风险能传播到实际入参/导出 key，而不是无关内部 helper。

合理非 gold 解：在旧两个规则之前新增缩写边界分隔，保留原 `[a-zA-Z]→digit` 规则；或者字符边界扫描满足同样契约。新增测试不约束这些形状，未发现相应误拒条件；未运行替代解，不宣称全体正确实现都能过。只特判 CAMELToSnake 可骗过新增用例而不修 HTTPResponse，但它是测试不足的例子，绝非合法解决方案。gold 的局部目标正确不能等同“完整且无回归”。

## 开发需求、网络资产和合法交付

| 操作/资产 | 公开依据 | 现有证据适用范围与缺口 | 最小公开命令/预期（未执行） |
|---|---|---|---|
| 核实际 actor 初态、编辑非测试 Python 文件 | public_hints；to_snake 全文 | 历史 gold 仅投影 alias_generators.py；actor 消息/权限 unknown | `pwd`、`git rev-parse HEAD`、`git status --porcelain=v1` 含 RC；`git diff -- pydantic/alias_generators.py` |
| Python/core/test plugins | pyproject:64–69,97–116,152–168 | grader 能安装并导入 /testbed/pydantic；actor 未验 | `python -c 'import sys,pydantic,pydantic_core; print(sys.executable,pydantic.__file__,pydantic_core.__version__)'`，核 core2.14.5；不误用 site-packages |
| 直接用户 API复现及保留旧参数 | prompt、test_utils 公开参数 | stdlib re+Python 项目，无远程服务/数据/GPU需求 | `python -c 'from pydantic.alias_generators import to_snake; assert to_snake("HTTPResponse")=="http_response"'`；base 目标失败、修后通过；`python -m pytest -q tests/test_utils.py -k "camel or snake"` |
| 数字边界的实际 alias 影响 | 公开 to_snake 旧规则、_generate_schema/config 调用者 | 静态推导明确，当前 CPU/actual actor 结果未取 | 同一小脚本输出 A1/API2 的 to_snake 和设 alias_generator=to_snake 模型的 model_fields alias、model_dump(by_alias=True)，再核旧 key 能否填充；先作对照观察，不偷偷新增评分要求 |
| 可信测试恢复与合法候选 | non-test public_hints；recipe/diagnostics | 原件恢复/应用1个测试文件；gold无test/conftest路径 | 仅源文件补丁可交付；additional_exclusions=[]，无修订题面/测试 |

本题必要逻辑没有网络、外部权重或特殊数据。依赖安装沿原件离线 wheel 配方在历史 grader 中成功，不证明 actor 同样预置/有权限。pytest-benchmark 配置要求实际插件存在；不要仅 collect-only 就声称功能可执行。

## 初判与唯一优先下一步

check23：主目标充分，附加 to_camel 范围已按公开契约收窄；不把含混附注扩成新功能。check24：没有具体实现形状误拒证据。check25 issue：新增单一无数字参数，缺少核心原例/一般缩写与大写→数字兼容保护。check26 issue/待核，严格指旧 A1/API2 转换被 gold 改写的静态兼容风险；已证行为差异，不宣称已实验确认它违反唯一规格。check27：公开目标局部正确、完整性待核。check1/2/16–21 仅材料和历史运行局部正证据，check3/10/29/33 actual actor unknown；check5留出重叠未查；check31/40没有全攻击面/偏差证明；其余未列 not_checked。

唯一优先下一步：任务二做一个窄、公开 API 的 base/gold 对照，覆盖 HTTPResponse、A1、API2 及 alias_generator=to_snake 的模型字段验证/按别名导出，记录真实 key 变化和实际 actor 入口条件。目的只在确认具体数字边界变动是否影响原有可用工作流，从而决定是否保留兼容规则；不执行全仓、不给未明 Unicode/标点凑测试。本次没有执行此脚本，也没有修改任务。

## 实际阅读与暴露范围

全文：本题 prompt/bundle/identity/brief、封存 public_read、gold/test/validation；grading 所有 expected ID；run_refs 指定账本/诊断/recipe/image/build，重复同 SHA 只核同；gold 原候选与私有 gold 字节对比；baseline/projection/stage 限指定 JSON 指针。environment_record/source_refs 只作本题定位，没有跟随旧结论。

正文：alias_generators.py:1–44 全文；tests/test_utils.py:1–40,460–550；tests/conftest.py:1–110（决定性 autouse 与 helper完整）；_generate_schema.py:926–980,1048–1061；aliases.py:80–112；config.py:131–159,319–376；tests/test_aliases.py:380–420；pyproject:55–75,95–125,135–172；skip/dependency/caller 精确检索命中。未通读 utility 其余测试、全部字段构造/校验 core 或 Unicode/正则库实现。

原日志核读初态 status/HEAD、相对 base 源码与 pyproject diff、锁文件变动 package/version/hunk、install/恢复命令和 RC、全体原测试 ID 状态、目标失败栈、全部 alias 相关 P2P 状态和尾部。已机械证 gold/noop 共同 pdm.lock/pyproject 初态差异逐字相同；锁文件未逐依赖/哈希语义审阅，Git show 正文不计作完整源码审计。未读 history、reviewer、其他包、根汇总、HISTORY正文或外链。

## 原件证据附录（本题独立条件）

路径缩写：`PUBLIC=runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-8316`，`PRIVATE=runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8316`，均相对固定 ROOT `/Users/roger/Desktop/claude-code-verl-stage0h`。公开 reader 是本题 `results/pydantic__pydantic-8316/public_read.md`。下面每条 log/ledger 都是本题 run_refs 精确授权的单题原件，不引用旧质量标签。

来源字段行号：public=165, grading=165, validation=165；来源原账本未跨题浏览。public base/grading/base manifest 的 commit 一致，private gold 与 validation golden_patch 及历史 candidate.patch 字节核同。

- source image tag：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8316:latest`
- expected source manifest digest：`sha256:3cbc02f34155d2855f8544b131fa9a49720a671fbc92f49137bceebf11a59e0c`
- 当前 actual actor image ID：unknown/null。下表 actual image ID 是历史派生 grader image，二者不可代换。

### gold 原运行

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8316/gold/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8316/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_16828e54.eval.log`，授权行 1–1032。
- actual historical image：`sha256:20d1a0331247a0a74642aaedc3cde40234009f9ce36f0a687405f0612650d5de`；scripts_digest：`sha256:09a8ebbc5b70cb304d589656b094030b0f9d6c793050330cbf4bbf1434870610`；derived recipe=`pydantic-install-v1`。
- candidate：`{"apply_method": "git_apply", "apply_stderr_tail": null, "apply_user": "agent/54321", "kind": "gold", "origin": "/work/full216_20260919/replay/gold/pydantic__pydantic-8316.gold.patch", "patch_sha256": "sha256:290e40116e89b175013661f98a8bbcc1c1bf428e34417d93bc5f0d90fb3835d7"}`；projection：`{"frozen_patch_digest": "sha256:93aa5e30911f5ec4547d7212a08ff31712b64b1f14e4b51668ec3ab1d4fcfb0a", "ignored_paths": [], "included_paths": ["pydantic/alias_generators.py"], "unsupported_shape_reasons": []}`。baseline 的 task_base_commit/materialized_head 与本题 base一致，stage apply_method/head、projection physical_attempt_id 与该次原候选指针匹配。
- 安装/test：`{"install_rc_last_command": 0, "install_seconds": 4.621, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 4.028}`。原脚本末尾 echo 返回码不能替代 RH2_TEST_RC；这里直接用原标记与失败栈。
- 原 raw ID状态计数：`{"PASSED": 159, "SKIPPED": 14}`。parser 报 num_parsed_tests=169，这不是原收集数量。所有 143 个 expected P2P 原行均 PASSED，所有 F2P 原行见下表；expected 无缺席/skip，与 diagnostics.reference_missing/reference_skipped=[] 相符。未核 parser 对所有非 expected 名称的标准化细节。

| F2P ID | 原状态 | 原日志行 |
|---|---|---|
| `tests/test_utils.py::test_camel2snake[CAMELToSnake-camel_to_snake]` | PASSED | 1005 |

- 信任恢复：`{"RH2_SETUP_ABSENT_TEST_FILES": "0", "RH2_SETUP_APPLY_RC": "0", "RH2_SETUP_EXPECTED_TEST_FILES": "1", "RH2_SETUP_IRREGULAR_TEST_FILES": "", "RH2_SETUP_OK": "1", "RH2_SETUP_RESTORED": "1", "RH2_SETUP_TEST_FILES": "1"}`；candidate_test_like_paths=[]，runner_integrity_changed=False。这是该路径局部正证据，未证全评分控制面不能绕过。
- 来源/资源：`{"RH2_OBS_IMPORT_PATH": "/testbed/pydantic/__init__.py", "RH2_OBS_INSTALL_PROBE": "absent", "RH2_OBS_INSTALL_PROBE_PRE": "absent", "RH2_OBS_PKG_VERSION": "2.6.0a1", "RH2_OBS_PREFIX_OWNER_PRE": "54322", "RH2_OBS_RUNNER_DIGEST": "cdcb38ab1e198b9cd561dd143e40400f292c84e3211d65ee5e13cc16744cea34", "RH2_OBS_RUNNER_DIGEST_PRE": "cdcb38ab1e198b9cd561dd143e40400f292c84e3211d65ee5e13cc16744cea34"}`；policy=`{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`；budgets=`{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`；resource=`{"mem_peak_mb": 206.781, "mem_peak_unavailable_or_zero": false}`，保持原字段名/数值，不推断单位；cleanup=`{"detail": "", "removed": true, "steps": ["rm:ok"]}`。这些不证明当前 actor 用户权限或资源。
### noop 原运行

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8316/noop/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8316/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_02c87450.eval.log`，授权行 1–1030。
- actual historical image：`sha256:20d1a0331247a0a74642aaedc3cde40234009f9ce36f0a687405f0612650d5de`；scripts_digest：`sha256:09a8ebbc5b70cb304d589656b094030b0f9d6c793050330cbf4bbf1434870610`；derived recipe=`pydantic-install-v1`。
- candidate：`{"apply_method": "noop", "apply_stderr_tail": null, "apply_user": "agent/54321", "kind": "noop", "origin": "noop", "patch_sha256": null}`；projection：`{"frozen_patch_digest": "sha256:ff11a180b2b1a9aff3e3e7d4d68ea0f646e8e7050bbb990b190e62945321e1bf", "ignored_paths": [], "included_paths": [], "unsupported_shape_reasons": []}`。baseline 的 task_base_commit/materialized_head 与本题 base一致，stage apply_method/head、projection physical_attempt_id 与该次原候选指针匹配。
- 安装/test：`{"install_rc_last_command": 0, "install_seconds": 4.99, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 4.357}`。原脚本末尾 echo 返回码不能替代 RH2_TEST_RC；这里直接用原标记与失败栈。
- 原 raw ID状态计数：`{"PASSED": 158, "SKIPPED": 14, "FAILED": 1}`。parser 报 num_parsed_tests=169，这不是原收集数量。所有 143 个 expected P2P 原行均 PASSED，所有 F2P 原行见下表；expected 无缺席/skip，与 diagnostics.reference_missing/reference_skipped=[] 相符。未核 parser 对所有非 expected 名称的标准化细节。

| F2P ID | 原状态 | 原日志行 |
|---|---|---|
| `tests/test_utils.py::test_camel2snake[CAMELToSnake-camel_to_snake]` | FAILED | 985 |

- 信任恢复：`{"RH2_SETUP_ABSENT_TEST_FILES": "0", "RH2_SETUP_APPLY_RC": "0", "RH2_SETUP_EXPECTED_TEST_FILES": "1", "RH2_SETUP_IRREGULAR_TEST_FILES": "", "RH2_SETUP_OK": "1", "RH2_SETUP_RESTORED": "1", "RH2_SETUP_TEST_FILES": "1"}`；candidate_test_like_paths=[]，runner_integrity_changed=False。这是该路径局部正证据，未证全评分控制面不能绕过。
- 来源/资源：`{"RH2_OBS_IMPORT_PATH": "/testbed/pydantic/__init__.py", "RH2_OBS_INSTALL_PROBE": "absent", "RH2_OBS_INSTALL_PROBE_PRE": "absent", "RH2_OBS_PKG_VERSION": "2.6.0a1", "RH2_OBS_PREFIX_OWNER_PRE": "54322", "RH2_OBS_RUNNER_DIGEST": "cdcb38ab1e198b9cd561dd143e40400f292c84e3211d65ee5e13cc16744cea34", "RH2_OBS_RUNNER_DIGEST_PRE": "cdcb38ab1e198b9cd561dd143e40400f292c84e3211d65ee5e13cc16744cea34"}`；policy=`{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`；budgets=`{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`；resource=`{"mem_peak_mb": 233.141, "mem_peak_unavailable_or_zero": false}`，保持原字段名/数值，不推断单位；cleanup=`{"detail": "", "removed": true, "steps": ["rm:ok"]}`。这些不证明当前 actor 用户权限或资源。

### 配方、初态与证据界限

原 candidate_test/eval before 脚本安装命令是 `export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit; make install;`；after 改为 `python -m pip install -e .`，再以 `python -I`/tomli 静态读取候选 pyproject 的 testing/testing-extra，写 `/tmp/rh2-envrepair-testing-reqs.txt` 并 `python -m pip install -r`。image.json/build.log 明确只叠加 wheels 层，设 `PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`；构建有 ARG默认值 warning，但实际镜像写入完成，不能将 warning 当失败。日志中完整测试命令为 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_utils.py`。修订改变环境安装路线，没有改变本题 test.patch 或 expected；没有读到 before 配方执行失败的本题原栈，故不编造旧安装失败位置。

历史 eval `git status`（各 log:132起）显示 noop 已有 pdm.lock/pyproject.toml 未提交修改；gold 另有相应源码文件。后续 `git show` 是 HEAD提交，不是未提交差异。真正 `git -c core.fileMode=false diff BASE` 中，pyproject 增加 pre-commit 运行依赖（本题 >=3.5.0）；pdm.lock 增加 pre-commit/cfgv/distlib/identify/nodeenv/virtualenv 等及锁格式变化。两次的锁与 pyproject diff 已机械逐字核同，不能将其叫干净 base，也没有擅自 reset。未采实际 actor 准备前后 `status --porcelain=v1` 及 RC，这个状态仍 unknown。

目标栈 noop:1003–1010 明确 tests/test_utils.py:543 的 camelto_snake 与 camel_to_snake 字符串差异；gold:1005 PASS。相关 alias 全部状态在 noop:954–993 / gold:974–1012。raw14 skip 是13项 test_display_as_type_310（源码87行 Python<3.10 skip）及1项 test_lenient_issubclass_with_generic_aliases（118行 Python<3.9 skip），不在 expected。gold159 passed/14 skipped，noop158 passed/1 failed/14 skipped，无 xfail/xpass。

用途边界：审查者已获准见本题 gold、隐藏测试、expected、原 grader 日志与封存公开分析；尚未见旧答案/history。此材料必须留在私有审查侧，不提供独立 solver。actual actor 是否能看到未来修复仍 unknown（check29）。`file_rules.additional_exclusions=[]`，`revision_refs=[]`；本次无题目修订。未观测本审查 token/货币/CPU实验成本，填 null，不据本地静态命令耗时推造运行资格。八方面已按上述范围处理；未穷举能力/环境/误拒/漏检与抽样偏差（check40 unknown）。
