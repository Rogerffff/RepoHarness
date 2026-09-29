# pydantic__pydantic-6043 — history 解封前独立主审

审查者：`/root/e25_main_pack08_pydantic`。仅做静态阅读/JSON/hash，未执行或导入项目、测试、网络、容器、实验，没有派生 agent；未读 history、旧质量结论、reviewer 或根汇总。所有运行证据均为 run_refs 指定历史原件。本题建议保留 `needs_review/static_review`、`development_diagnostic`，主要原因是公开旧字段保序承诺与唯一评分顺序断言冲突，且测试对递归排序覆盖很窄。

## 目标、公开歧义与版本

题面要求 best-effort 的确定排序 JSON Schema，使内部重构尽量不改变文本/示例差异；建议末端递归整理 keys/items，没有强制 helper 名或具体算法。base 为 `d476599cdd956284595034d7d9fd046569a0574c`（379 个 Git 跟踪条目静态导出）。`pyproject.toml:60–65` 要求 Python>=3.7、core==0.38.0；grader 使用 Python 3.8。actual actor 的输入、消息、工作树、权限和资产 unknown，静态 base 不替代它们。

决定性公开冲突在 `base/docs/usage/models.md:958–966`：明确把“field order is preserved in the model schema”列为字段顺序的重要承诺。`_named_required_fields_schema`（json_schema.py:901–924）顺序填入 properties 与 required，旧 `test_by_alias` 也明确要求 Snap 在 Crackle 前。题面新目标允许改变部分顺序，但没有明确废除字段保序；保留 properties 字段序、递归整理其他 schema 键是合理的保守实现。公开 reader 独立得出这一选择。不能仅以 gold 正好全排序就宣称公开要求只能如此。

## 新/改断言、helper 与双向映射

`test.patch` 全文只把 `tests/test_json_schema.py::test_by_alias` 一行预期由 `['Snap','Crackle']` 改为 `['Crackle','Snap']`。该函数所有语句（102–118）已读：ApplePie.title='Apple Pie'；a:float alias Snap 必填、b:int alias Crackle 默认10；前一大 dict 断言不感知映射顺序；by_alias=False 的 a,b 已经字母有序。没有新增 fixture/helper 或递归检查。conftest 唯一 autouse 环境项是省略错误 URL，不决定 schema 排序。

| 要求或合理旧行为 | 公开依据 | 决定性测试/断言 | 结论及证据层次 |
|---|---|---|---|
| best-effort 递归整理普通 schema 映射键 | user_prompt 全文 | 唯一 F2P `test_by_alias` 仅检查一个 properties 映射 | 部分；没有根键、嵌套字段 schema 键、列表内 schema 键、$defs 顺序断言，check25 漏测 |
| 字段映射保留声明顺序 | docs/usage/models.md:964；原 test_by_alias:117；json_schema.py:904–919 | 私有测试把别名字段强制改成 Crackle,Snap | 公开契约冲突/合理保守解的潜在误拒，check23/24；不是单纯代码风格要求 |
| 使用别名与关闭别名正确，默认/必填/类型不变 | test_by_alias:103–118 | 完整 dict 值断言、by_alias=False 键列表 | 内容有覆盖；未显式检查普通键排序；a,b 不能区分保序与排序 |
| 两类入口覆盖：单模型与批量定义、TypeAdapter | json_schema.py:215–321,1553–1602；type_adapter.py:311–375 | P2P `test_schema_from_models`、`test_dataclass`、`test_schema_no_definitions`、`test_type_adapter_json_schemas_title_description` 等 | 值/引用有覆盖，dict 相等不验键序；排序仅修单模型也可能逃过批量顺序缺口 |
| 位置列表不能重排 | tuple_positional_schema:601–621 | 全部六个 `test_tuple[...]` 参数；`test_tuple_with_extra_schema` | 已读全部参数、模型与 TypeAdapter 双断言及定制 core helper；prefixItems 类型顺序受保护 |
| enum、examples、required 列表保持内容和顺序 | tests:443–471,2222–2249,1413–1487 | `test_list_enum_schema_extras` 保 spam,egg,chips 及 examples；`test_schema_attributes` 保枚举序；schema_from_models required 保 name,ingredients | P2P 有明确列表次序覆盖；题面 items 不能被解释成无条件全列表排序 |
| validation/serialization、引用和 generator 扩展保持 | tests:3709–3766,4060–4131 | `test_serialization_validation_interaction`；`test_generate_json_schema_generate_twice`；`test_override_generate_json_schema` | 已读各完整测试及局部类/helper；验证模式内容/引用、一次性使用、super 后追加 $schema；没有文本顺序完整性断言 |
| 自定义 extras 不丢内容 | _update_class_schema:975–1011 | `test_model_with_schema_extra`、`test_model_with_schema_extra_callable` | 字典 examples 与 callable 删除 properties 改 type 有覆盖；混合类型键/循环扩展未规定且未验证 |

反向审视唯一隐藏变化：Crackle/Snap 与同一 alias 对象的字母排序直接相关，有新排序动机，但相对旧保序承诺缺少明确优先级。测试没有要求 `_sort_json_schema` 函数名、对象身份或具体排序实现。本题不是“只要排序任何一层就充分”的规格。

303 个 expected P2P 均与 gold/noop 原状态行机械逐 ID 对拍为 PASSED，没有缺席/skip。语义按上述风险区段抽查，未通读全部 303 项；尤其复杂 discriminated unions、所有 default/constraint 参数、所有碰撞路径未完整审阅。不能用 303 这个数量替代排序语义证据。

## 完整 gold 与具体边界

已读 gold 全部三个 hunk：`generate_definitions` 返回 sorted definitions，`generate` 返回 sorted json_schema，末尾新增 `_sort_json_schema`。完整 helper 分为 dict/list/scalar 三支：dict 对所有键调用 sorted 并递归重建；list 保原元素位置、只递归值；scalar 原样返回。它不改引用重写、_used 检查或模型验证；单模型/TypeAdapter 单 schema 都经 generate，批量 model/TypeAdapter definitions 经 generate_definitions。调用方和相邻引用收集/去重代码已核读。

这个实现对正常有限、字符串键 JSON 树给出递归映射排序，并保住位置数组约束；这是局部正证据，不是完整无回归证明。已知具体行为变化是 properties 全字母排序：字段 z,a 会由 z,a 变成 a,z，违背旧文档字段保序。gold 没有修订文档，评分反而只要求这一处变化。可把它定为“已静态证实的旧行为改变与规格冲突”，而不是从 P2P 全绿推出旧契约不存在。

合理非 gold 实现 A：递归排序普通字典，遇到 properties 保持其键插入序但仍递归每个值，列表保序。这实现满足保守公开理解，会被唯一 F2P 拒绝；未运行，不把它称作已实测误拒。实现 B：只排序生成的 properties、不整理根/嵌套/$defs。它可能通过唯一 F2P 和值比较 P2P，仍明显不能满足题面递归整理的主要意图；这是可定位覆盖缺口，不声称已跑恶意候选。

批量外壳在 gold 之后仍按 `$defs`、title、description 构建（json_schema.py:1594–1602，type_adapter.py:367–375），不是全字母序；它本身顺序稳定，题面 best-effort 没有说必须消除此差别。因此记录为边界/完整性未明，不机械判 gold 失败。用户覆盖 generate 在 super 后追加键同样不受排序管控；不能强制拦截合法子类扩展。混合型非字符串键/循环等不是规范 JSON 树，未据此制造必修反例。递归排序 list 元素不等于改变 list 顺序，不能错误指控 tuple 回归。

## 开发需求与交付范围

| 操作/资产 | 公开依据 | 现有证据与缺口 | 最小公开命令与预期（仅建议，未执行） |
|---|---|---|---|
| 核初态并编辑非测试生成器源码 | public_hints；两个 generate 出口 | 历史 gold 只投影 json_schema.py；actor 消息/HEAD/status/可写性 unknown | `pwd`、`git rev-parse HEAD`、`git status --porcelain=v1` 并保存 RC；`git diff -- pydantic/json_schema.py` |
| 当前源码导入及 core==0.38.0、pytest | pyproject:60–65,101–108,143–151 | 历史 grader 安装/选定测试成功；actor 解释器/PATH/插件未验 | `python -c 'import sys,pydantic,pydantic_core; print(sys.executable,pydantic.__file__,pydantic_core.__version__)'` |
| 观察真实 API 文本/键序 | 题面文本稳定性、公开模型 schema API | dict 相等不能验序；目前契约优先级有争议 | `python -c 'import json; from pydantic import create_model; M=create_model("M",z=(int,...),a=(str,...)); s=M.model_json_schema(); print(list(s),list(s["properties"])); print(json.dumps(s))'`；记录顺序，禁用 sort_keys 掩盖结果 |
| 窄范围兼容路径 | 上表 tuple/enum/alias/批量/模式测试 | 历史已运行对应文件，actor 未验 | `python -m pytest -q tests/test_json_schema.py -k "tuple or list_enum_schema_extras or schema_from_models or serialization_validation_interaction"`；列表约束/引用不变 |
| 合法提交/可信恢复 | non-test 提示、recipe/diagnostics | 原件显示恢复和应用 1 个测试文件；gold 无测试改动 | 源码候选可交付；不新增排除规则，不改测试/评分 |

功能只需本地 Python schema 生成，不需服务、GPU 或外部数据。原离线 wheel 底座、install-v1 配方只证明当时 grader 条件；actor 资产/网络不明。目录导出缺省不证明镜像缺件。

## 初判与唯一优先下一步

check23/24 issue：公开字段保序和唯一 F2P 强制排序冲突，可导致合理保守解误拒。check25 issue：仅 properties 键序不能验证递归排序。check26 issue 的严格范围是 gold 改变已有文档承诺的字段顺序，静态可证；是否作为被新需求授权的兼容性改变需裁决，不说已实测生产破坏。check27 局部递归映射实现有正证据，完整性/规格一致性不成立为无条件 pass。check1/2/16–21 仅材料对齐和历史 grader 局部正证据；check3/10/29/33 actual actor unknown。check5 没查评测留出重叠。check31/40 没审计所有控制面/漏检误拒偏差，封存流程不能支撑 pass。未列项 not_checked，成本 unknown/null。

唯一优先下一步：先由规格维护者裁决 properties 字段序是否应继续保留，并让公开要求与断言同向；若决定破坏旧保序，应明确声明而不是让隐藏断言暗示。这个争议已有决定性静态材料，先跑 CPU 不会回答契约优先级，因此本题不机械追加实验。裁决后才能合理设计递归/批量键序检查；本次没有改题、改 gold、改测试或评分。

## 阅读范围

全文：本题 prompt/bundle/identity/brief、封存 public_read、gold/test/validation；所有 expected ID；run_refs 指定账本/诊断/recipe/image/build 原件（同 SHA 重复仅字节核对），gold 原 candidate 字节核同；baseline/projection/stage 限授权指针。environment_record/source_refs 仅来源定位。没有读 history/reviewer/其他包/根汇总或链接外源。

正文区段：json_schema.py:215–323,601–625,880–925,975–1012,1500–1623；type_adapter.py:311–375；tests/test_json_schema.py:1–170,443–472,595–657,1413–1490,1580–1605,2195–2277,3709–3768,3796–3803（xfail 理由）,3945–3981,4060–4133,4360–4410；tests/conftest.py:1–94；docs/usage/models.md:958–1007；pyproject:55–75,95–125,135–172。另检索 tests 定义/keys/list/skip/xfail 命中，不等于阅读其余全部测试。

原日志核读 status/HEAD、相对 base 源码与 pyproject diff 全文、锁文件变动包/版本/hunk、安装命令/RC、可信恢复、全体测试 ID 状态、目标失败栈、上述相关 P2P、尾部摘要。gold/noop 的 pdm.lock/pyproject 初态差异分别逐字相同；未逐依赖/哈希审阅锁文件、未通读巨大 Git show 正文、未读取 parser/manager 归档源码。明确区分这种定向证据与完整环境/安全审计。

## 原件证据附录（本题独立条件）

路径缩写：`PUBLIC=runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-6043`，`PRIVATE=runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-6043`，均相对固定 ROOT `/Users/roger/Desktop/claude-code-verl-stage0h`。公开 reader 是本题 `results/pydantic__pydantic-6043/public_read.md`。下面每条 log/ledger 都是本题 run_refs 精确授权的单题原件，不引用旧质量标签。

来源字段行号：public=160, grading=160, validation=160；来源原账本未跨题浏览。public base/grading/base manifest 的 commit 一致，private gold 与 validation golden_patch 及历史 candidate.patch 字节核同。

- source image tag：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-6043:latest`
- expected source manifest digest：`sha256:93d7f9c929a93d19bf881a8066a95e825c598c6b7551864aea86ba3c4e49eb86`
- 当前 actual actor image ID：unknown/null。下表 actual image ID 是历史派生 grader image，二者不可代换。

### gold 原运行

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-6043/gold/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-6043/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_1041cb4c.eval.log`，授权行 1–3335。
- actual historical image：`sha256:faabec318960e7045bf7568760307284ff10f41134d45899d25820c40bc78e49`；scripts_digest：`sha256:acec532a5d6ea5d9db5d937e099593bfce79f9c7fea13ccfd694fa585a3ffd2c`；derived recipe=`pydantic-install-v1`。
- candidate：`{"apply_method": "git_apply", "apply_stderr_tail": null, "apply_user": "agent/54321", "kind": "gold", "origin": "/work/full216_20260919/replay/gold/pydantic__pydantic-6043.gold.patch", "patch_sha256": "sha256:1195b6492a02dbfee79d2112a56bc9997ee8cb535a92a517e63bbee1ebcfc134"}`；projection：`{"frozen_patch_digest": "sha256:124c9e2ad388ca593d6cc57881c3d9a66d315d341573e48a97baaf6b3b7f8eb5", "ignored_paths": [], "included_paths": ["pydantic/json_schema.py"], "unsupported_shape_reasons": []}`。baseline 的 task_base_commit/materialized_head 与本题 base一致，stage apply_method/head、projection physical_attempt_id 与该次原候选指针匹配。
- 安装/test：`{"install_rc_last_command": 0, "install_seconds": 4.282, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 3.438}`。原脚本末尾 echo 返回码不能替代 RH2_TEST_RC；这里直接用原标记与失败栈。
- 原 raw ID状态计数：`{"PASSED": 306, "XFAIL": 1}`。parser 报 num_parsed_tests=306，这不是原收集数量。所有 303 个 expected P2P 原行均 PASSED，所有 F2P 原行见下表；expected 无缺席/skip，与 diagnostics.reference_missing/reference_skipped=[] 相符。未核 parser 对所有非 expected 名称的标准化细节。

| F2P ID | 原状态 | 原日志行 |
|---|---|---|
| `tests/test_json_schema.py::test_by_alias` | PASSED | 3017 |

- 信任恢复：`{"RH2_SETUP_ABSENT_TEST_FILES": "0", "RH2_SETUP_APPLY_RC": "0", "RH2_SETUP_EXPECTED_TEST_FILES": "1", "RH2_SETUP_IRREGULAR_TEST_FILES": "", "RH2_SETUP_OK": "1", "RH2_SETUP_RESTORED": "1", "RH2_SETUP_TEST_FILES": "1"}`；candidate_test_like_paths=[]，runner_integrity_changed=False。这是该路径局部正证据，未证全评分控制面不能绕过。
- 来源/资源：`{"RH2_OBS_IMPORT_PATH": "/testbed/pydantic/__init__.py", "RH2_OBS_INSTALL_PROBE": "absent", "RH2_OBS_INSTALL_PROBE_PRE": "absent", "RH2_OBS_PKG_VERSION": "2.0b2", "RH2_OBS_PREFIX_OWNER_PRE": "54322", "RH2_OBS_RUNNER_DIGEST": "d3654dc4a4918a6e29494d9f77fa9a98b6bc37135b7b6bc5b323d30680c5af05", "RH2_OBS_RUNNER_DIGEST_PRE": "d3654dc4a4918a6e29494d9f77fa9a98b6bc37135b7b6bc5b323d30680c5af05"}`；policy=`{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`；budgets=`{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`；resource=`{"mem_peak_mb": 133.137, "mem_peak_unavailable_or_zero": false}`，保持原字段名/数值，不推断单位；cleanup=`{"detail": "", "removed": true, "steps": ["rm:ok"]}`。这些不证明当前 actor 用户权限或资源。
### noop 原运行

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-6043/noop/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-6043/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_c5499389.eval.log`，授权行 1–3312。
- actual historical image：`sha256:faabec318960e7045bf7568760307284ff10f41134d45899d25820c40bc78e49`；scripts_digest：`sha256:acec532a5d6ea5d9db5d937e099593bfce79f9c7fea13ccfd694fa585a3ffd2c`；derived recipe=`pydantic-install-v1`。
- candidate：`{"apply_method": "noop", "apply_stderr_tail": null, "apply_user": "agent/54321", "kind": "noop", "origin": "noop", "patch_sha256": null}`；projection：`{"frozen_patch_digest": "sha256:62499d226e08027e670763e41a8f20f3932e8c2c924a383329f3ca943899c752", "ignored_paths": [], "included_paths": [], "unsupported_shape_reasons": []}`。baseline 的 task_base_commit/materialized_head 与本题 base一致，stage apply_method/head、projection physical_attempt_id 与该次原候选指针匹配。
- 安装/test：`{"install_rc_last_command": 0, "install_seconds": 4.488, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 3.641}`。原脚本末尾 echo 返回码不能替代 RH2_TEST_RC；这里直接用原标记与失败栈。
- 原 raw ID状态计数：`{"FAILED": 1, "PASSED": 305, "XFAIL": 1}`。parser 报 num_parsed_tests=306，这不是原收集数量。所有 303 个 expected P2P 原行均 PASSED，所有 F2P 原行见下表；expected 无缺席/skip，与 diagnostics.reference_missing/reference_skipped=[] 相符。未核 parser 对所有非 expected 名称的标准化细节。

| F2P ID | 原状态 | 原日志行 |
|---|---|---|
| `tests/test_json_schema.py::test_by_alias` | FAILED | 2975 |

- 信任恢复：`{"RH2_SETUP_ABSENT_TEST_FILES": "0", "RH2_SETUP_APPLY_RC": "0", "RH2_SETUP_EXPECTED_TEST_FILES": "1", "RH2_SETUP_IRREGULAR_TEST_FILES": "", "RH2_SETUP_OK": "1", "RH2_SETUP_RESTORED": "1", "RH2_SETUP_TEST_FILES": "1"}`；candidate_test_like_paths=[]，runner_integrity_changed=False。这是该路径局部正证据，未证全评分控制面不能绕过。
- 来源/资源：`{"RH2_OBS_IMPORT_PATH": "/testbed/pydantic/__init__.py", "RH2_OBS_INSTALL_PROBE": "absent", "RH2_OBS_INSTALL_PROBE_PRE": "absent", "RH2_OBS_PKG_VERSION": "2.0b2", "RH2_OBS_PREFIX_OWNER_PRE": "54322", "RH2_OBS_RUNNER_DIGEST": "d3654dc4a4918a6e29494d9f77fa9a98b6bc37135b7b6bc5b323d30680c5af05", "RH2_OBS_RUNNER_DIGEST_PRE": "d3654dc4a4918a6e29494d9f77fa9a98b6bc37135b7b6bc5b323d30680c5af05"}`；policy=`{"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}`；budgets=`{"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}`；resource=`{"mem_peak_mb": 167.324, "mem_peak_unavailable_or_zero": false}`，保持原字段名/数值，不推断单位；cleanup=`{"detail": "", "removed": true, "steps": ["rm:ok"]}`。这些不证明当前 actor 用户权限或资源。

### 配方、初态与证据界限

原 candidate_test/eval before 脚本安装命令是 `export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit; make install;`；after 改为 `python -m pip install -e .`，再以 `python -I`/tomli 静态读取候选 pyproject 的 testing/testing-extra，写 `/tmp/rh2-envrepair-testing-reqs.txt` 并 `python -m pip install -r`。image.json/build.log 明确只叠加 wheels 层，设 `PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`；构建有 ARG默认值 warning，但实际镜像写入完成，不能将 warning 当失败。日志中完整测试命令为 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`。修订改变环境安装路线，没有改变本题 test.patch 或 expected；没有读到 before 配方执行失败的本题原栈，故不编造旧安装失败位置。

历史 eval `git status`（各 log:132起）显示 noop 已有 pdm.lock/pyproject.toml 未提交修改；gold 另有相应源码文件。后续 `git show` 是 HEAD提交，不是未提交差异。真正 `git -c core.fileMode=false diff BASE` 中，pyproject 增加 pre-commit 运行依赖（本题 >=2.21.0）；pdm.lock 增加 pre-commit/cfgv/distlib/identify/nodeenv/virtualenv 等及锁格式变化。两次的锁与 pyproject diff 已机械逐字核同，不能将其叫干净 base，也没有擅自 reset。未采实际 actor 准备前后 `status --porcelain=v1` 及 RC，这个状态仍 unknown。

目标栈 noop:3284–3292 明确 tests/test_json_schema.py:117 键列表 Snap,Crackle 与 Crackle,Snap 不同；gold:3017 PASS。tuple 六参数 noop:2997–3002 / gold:3038–3043；enum extras noop:2989 / gold:3030；批量 schema noop:3090 / gold:3131；schema_attributes noop:3214 / gold:3255；TypeAdapter无定义 noop:3279 / gold:3320。raw唯一 XFAIL 是 test_get_pydantic_core_schema_calls（同文件:3796–3802 的既有重复调用原因）；不在 expected。gold306 passed/1 xfailed，noop305 passed/1 failed/1 xfailed，无 skip/xpass。

用途边界：审查者已获准见本题 gold、隐藏测试、expected、原 grader 日志与封存公开分析；尚未见旧答案/history。此材料必须留在私有审查侧，不提供独立 solver。actual actor 是否能看到未来修复仍 unknown（check29）。`file_rules.additional_exclusions=[]`，`revision_refs=[]`；本次无题目修订。未观测本审查 token/货币/CPU实验成本，填 null，不据本地静态命令耗时推造运行资格。八方面已按上述范围处理；未穷举能力/环境/误拒/漏检与抽样偏差（check40 unknown）。
