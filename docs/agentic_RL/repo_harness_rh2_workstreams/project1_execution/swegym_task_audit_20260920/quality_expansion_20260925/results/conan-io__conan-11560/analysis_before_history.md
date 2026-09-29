# conan-io__conan-11560 — analysis before history

## 身份、运行条件、交付与证据边界
本稿由 fresh 私有主审 e25_main_pack06_conan 在 history release 前形成。ROOT 固定为 `/Users/roger/Desktop/claude-code-verl-stage0h`；P 为本题 `runs/swegym_quality_expansion_20260925/public/<task>`，S=P/base，V 为对应 private 目录。下述源文件行号均相对本题 S。所有 exec 显式 ROOT；只读静态文件/授权原件与 stdlib 文本/JSON/hash，未执行/导入项目、测试、安装、网络、容器、SSH、GPU、模型，也未修改原题/测试/gold/评分或派生 agent。

八方面已分别覆盖：公开目标与疑义、版本初态、全部增改断言/F2P/P2P、合理非 gold 与误拒、gold/相关 caller/回归、开发需求与资产、合法交付与可信测试恢复、关系/答案暴露/用途。运行引用是已存在的历史 RH2 原件，不是旧质量判断，不是本轮 CPU 或真实模型运行。

check3 实际用户/system 消息、工具呈现与 public_hints 交付仍 unknown；check4/6–13/33 当前 actor UID/HOME/cwd/PATH、解释器、读写权限、依赖/忽略资产、网络和资源未取证。历史 noop 工作树状态在 trusted setup 前显示 clean；gold 显示唯一修复源码相对 base 的 diff。`git show` 的基线提交 diff 不是初始未提交改动。当前 actor 初态、来源规定变更、准备后 porcelain status/RC 仍 unknown，不能从静态 Git 导出或历史 grader 状态代替。镜像 tag、expected manifest digest 与 actual image ID 分开，后者 null。

check9/16/17/18/19 的局部正证据是 candidate SHA、投影路径、基线/阶段指针、可信测试从 base checkout 后 test.patch cleanly applied，以及下列实际选择和逐测试输出；未查任意候选全部安全性质。仅有来源 parser 标识/逐测试映射，没有完整 scorer 控制面源码审计。历史日志没有相关 expected skip/xfail/missing；缺失或 skip 不能算通过。安装成功只指最后命令 RC 0，日志所查 pip 依赖为 already satisfied；不推广到所有历史依赖可从零恢复。

check5 同仓不同 base/不同目标的本包关系可见，但没有跨池重复/留出检索授权，因此 overlap unknown。check29 实际 actor 可见未来答案 unknown；usage 的审查者私有暴露已知：本题 gold、隐藏 test.patch、expected、noop/gold 原件与封存 public_read；尚未读 history/旧质量记录/reviewer。check30 外部取答与31评分控制面攻击能力未核。check34/35/36 没有真实模型能力、完整解答诚实性或训练阶段适配证据。check14/15 重复评分/并发/缓存变化未验证；check37–39 本轮没有环境/题目修订，复验及共享影响 unknown。check40 流程封存不能证明无漏检、误拒或抽样偏差，本稿已记录具体局限。

最终用途仅 `development_diagnostic`，不得据此批准训练/正式评测。`file_rules.additional_exclusions=[]`、`revision_refs=[]`；disposition=`needs_review/static_review`。没有本轮 token/费用观测，costs 相关值 null；下述历史秒数/资源只保留原字段和值，不转成本或资格。

## 初判与公开目标（23、24、25、27）
静态初判：needs_review / static_review，题意—验收存在实质分歧。公开用户要修复 Linux libcurl→OpenSSL 多静态库链接，并明确给出每个 cc_import 增加 `alwayslink = True` 的输出示例。gold 全部改动却只有静态/普通导入路径后的尾逗号及 cc_library.deps 内 `# do not sort` 注释；没有 alwayslink，也没有改变库顺序。不能把 gold 当规格，也不能仅凭注释断言通过宣称已修复实际链接。题面将独立 cc_import visibility 明确留给另一问题，本审查不新增该要求。

源码 `S/conan/tools/google/bazeldeps.py:17–44,58–180` 给出生成并保存 BUILD 的完整路径。`cpp_info.aggregated_components()` 先聚合；`S/conans/model/new_build_info.py:161–206` 按组件依赖逆序合并列表，普通 libs 字典在 Python 3.10 保留插入顺序。未发现此生成器内的排序步骤；注释是否对外部 BUILD 格式化工具有控制作用，本轮无该工具规范/实测，因此只是可能机制，不能推断 gold 必然无效或必然有效。公开题面没有把外部排序工具及注释指定为修复契约。

## 需求—断言双向表（全部 F2P 与 P2P）
测试均在 `S/conans/test/unittests/tools/google/test_bazeldeps.py`；下列行号为 base，test.patch 是增改后的准确文本。每项均已读函数完整正文，不用状态数量代替语义阅读。

| 公开需求或合理旧行为 | 依据 | 测试与决定性断言 | 覆盖判断与证据层次 |
|---|---|---|---|
| 多静态库 cc_import 增 alwayslink；解决真实链接 | P/user_prompt.txt 的两段 BUILD 示例 | 四个 F2P 都不检查 alwayslink；fixture 每包只有一个库；未运行 Bazel/linker | 缺失（25）；gold 缺公开输出（27）；真实链接效果 unknown |
| 单库、defines、system libs、包级 deps | 既有生成行为 | F2P `test_bazeldeps_dependency_buildfiles` :29–61；保留名称/转义/linkopts，新增精确 `deps = [\n        # do not sort\n    \n    ":lib1_precompiled",` | 旧行为局部覆盖；新增注释与空白没有明确公开依据（23、24） |
| 完整 basename 的库路径可用 | `_get_lib_file_paths` :199–233 | F2P `test_bazeldeps_get_lib_file_path_by_basename` :64–96；同样精确注释/空白，库名为 liblib1.a | basename 及旧字段部分覆盖；不是多库顺序测试 |
| 包级依赖保留传递包引用 | 模板 :100–102 | F2P `test_bazeldeps_dependency_transitive` :99–152；正则强制注释后 lib1 再 @TransitiveDepName | 局部顺序覆盖；一个导入库 + 一个包依赖，不是 ssl/crypto 两个档案 |
| `.lib` + `.dll` 共享导入保持完整 | :69–75、151–165、228–230 | F2P `test_bazeldeps_shared_library_interface_buildfiles` :179–227；去所有空白后比较整份 BUILD，新增注释仍计入字符 | 共享路径/头/入口覆盖；额外合法属性也可能被拒；不是 alwayslink 需求证明 |
| 只有头文件包不生成 deps/import | :111–112 及模板条件 | P2P `test_bazeldeps_interface_buildfiles` :155–176；去空白全文相等 | 已读、历史两端通过；窄格式约束 |
| 主依赖 .bzl 正确引用包 | :235–271 | P2P `test_bazeldeps_main_buildfile` :230–264；逐字符串存在 | 已读、历史两端通过；未查实际 Bazel 加载 |
| build dependency 暴露 binaries filegroup | :46–56 | P2P `test_bazeldeps_build_dependency_buildfiles` :266–287；name、glob | 已读、历史两端通过；与目标静态链接独立 |

决定性 helper：同文件 MockConanFileDeps 全读；temp_folder :31–46 创建带空格临时目录；save 空文件只是库发现 fixture，不能供链接。生成器全部 :1–277 已读，包括丢弃无 libs/includes 包、文件发现、dll 配对、保存主 BUILD 与 editable 明确异常。关联旧集成 `S/conans/test/integration/toolchains/google/test_bazel.py:1–78` 全读，覆盖空包、相对路径、同名目录排除；不在本题 expected/实跑选择中。其 TestClient 深层实现本题未独立读取，不以另一题版本代替。

## 合理解、误拒、漏测与 gold 回归
- 合理解示例：仅对静态库导入添加 alwayslink（补必要逗号），不添加 deps 注释。这符合明确静态示例，但四个修改断言仍要求注释，至少前三项必然静态不匹配。未执行该替代解，不声称 runtime 成功；这是由断言字符串可直接确定的误拒机制（24）。
- 只添加指定注释即可满足 F2P 的新增要求，而多库真实链接和 alwayslink 均未检查。gold 已真实通过该套检查，是“该验收接受缺少公开属性的候选”的直接局部证据；不等于已证明每种链接场景失败（25、27）。
- 注释和尾逗号不改变本轮已查 Python 路径发现/组件合并。未发现有证据的 gold 新增旧行为回归（26 unknown，非 pass）；没有编译器、Bazel、不同平台或真实 OpenSSL 对照。也不能把未测多库行为冒称已证回归。
- 精确空白限制与完整共享 BUILD 相等还可能拒绝语义等价序列化；缺少规范说明这种布局是 API。相比之下保留 library 名称、路径、依赖是合理旧行为，并非本审查自创要求（28）。

## 开发操作、资产与合法交付
| 需要的操作/资产 | 公开依据 | 已有适用证据与 actor 缺口 | 最小公开命令及预期（未执行） |
|---|---|---|---|
| 读改生成器与源码导入 | public_hints 非测试文件；模板类 | 历史候选只投影 bazeldeps.py；actor 写权限/PATH/源码来源 unknown | `git status --porcelain=v1`；`python -c "import conan; print(conan.__file__)"`，应核对真实初态且导入工作树 |
| Python/Jinja2/mock/pytest 与临时目录 | requirements、上述单测 fixture | 历史 grader 安装 RC 0、7 项实际执行；actor 仍 unknown | `python -m pytest -q conans/test/unittests/tools/google/test_bazeldeps.py`；旧公开测试仅查旧行为，不证新目标 |
| 公开 Conan 生成流程与双库假包 | 题面 BUILD；旧集成 create/install | 空档案即可验输出，不要求网络 | 独立临时 recipe 声明 ssl、crypto 并写相应 .a；`conan install <consumer> -g BazelDeps`，逐 import 检查属性/路径；不修改可信测试 |
| 真实跨档案链接 | Linux libcurl/OpenSSL 问题 | Bazel/rules_cc、C++、对应源码/档案的 actor 资产、版本、网络/缓存未知 | 准备有符号依赖的最小双静态库工程后 `bazel build //:consumer`；成功才支持链接结论，版本检查或空文件不够 |

生成文本层不固有需要 GPU/模型/网络；pip 准备可能需要供应源，但历史 deny_all 下依赖已满足，不能推广 actor。源码与 trusted test 分路径，有局部合法交付正证据；评分控制面可否被任意候选改写未审计（31 unknown）。

## 唯一优先下一步
先由题目维护方裁定公开契约：是否坚持题面 alwayslink，还是改述为防止外部排序并提供对应公开依据；随后按裁定设计行为验收。当前核心是规格/评分分歧，不建议先机械重跑 CPU 或全仓。独立记录保留注释误拒及真实多库漏测，不因唯一下一步而合并删除。

## 本题阅读范围与未读
本题上述全部源文件/函数范围、gold/test patch 全文、完整 expected 列表；P 的 user_prompt、public_bundle、environment_brief、base_identity；封存 public_read 全文。requirements.txt/requirements_dev.txt、pytest.ini 全读；conftest.py 仅匹配行及 :230–270 的 autouse 工具选择。原日志按附录所列相关区段/匹配行读取，未把大段 git show 的基线提交 diff 当工作树差异。未读其他功能测试正文、其他题的 Bazel 版本、外部 Bazel 规范、历史质量结论或 reviewer。初期较大输出截断后，决定性源码和断言已分段补读；枚举不计全文阅读。

## 原始运行证据附录（本题限定）

静态 base_commit `345be91a038e1bda707e07a19889953412d358dc`；base_tree `e34214d86fd1cd12e56ad04b71583a9d2c0ed6a2`；blob inventory SHA256 `3a159fe17241c8b5a1f5f4e540223d998eec356148d2c1f5b5dcf18eea821bc8`。grading version `1.51`、Python 声明 `3.10`、eval_cmd `pytest -n0 -rA`；公开报告者版本与实际 base 开发版本不强行相等。validation gold SHA `sha256:0c0a96da87e7f6b88ce14b06d27237cbae8f4b2534e1bbe27f4fc078ad1d7897`。

- V/gold.patch SHA256 `0c0a96da87e7f6b88ce14b06d27237cbae8f4b2534e1bbe27f4fc078ad1d7897`。
- V/test.patch SHA256 `e45acc07853ac4a61844a77c8434567bb34ac1e1a6f8fa6f08105c885e9afc99`。
- V/grading.json SHA256 `03ee23e4094c9efc7f7eef9855b3a31950e358f5083f84be3be8463e16206d19`。
- V/run_refs.json SHA256 `07625d1f6fb8713fbf2ca95c3ccf1facd2f9646c957686d8bd70c32ef4a90208`。

### noop

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:11`，本行 SHA256 `2ab24f6e18a779101efc5368413c8a0c7ae6125f2a7155ebb370ddae176e3fb5`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_31f12366.eval.log` 的授权 `1–635`，全文 hash `a9444e47b66a3cbd7f159809cb1eecf73ca3ac22a9427132641d9578065da0db` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-11560:latest",
  "image_digest_expected": "sha256:2ab97e51d7c77d280b6e818043472af58b388043171bfb6a725deda81583b44e",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:b7f064d894d6b9811e171c1a3e78278950ee91ed5f4cc9850aced3fb4f19f6da",
  "policy": {
    "candidate_writable_prefixes": [
      "/opt/miniconda3/envs/testbed"
    ],
    "cpus": 2.0,
    "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a",
    "memory_bytes": 4294967296,
    "network": "deny_all",
    "pids_limit": 512,
    "profile_id": "rh2.grader_sandbox_profile.v1",
    "shm_bytes": 67108864,
    "tmpfs_bytes": 1073741824,
    "uid": 54322,
    "user": "rh2grader"
  },
  "budgets": {
    "candidate_stage_seconds": 900.0,
    "cleanup_seconds": 120.0,
    "grading_deadline_seconds": 3600.0,
    "image_pull_seconds": 1800.0
  },
  "observations": {
    "RH2_OBS_IMPORT_PATH": "/testbed/conans/__init__.py",
    "RH2_OBS_PKG_VERSION": "1.51.0-dev",
    "RH2_OBS_PREFIX_OWNER_PRE": "54322",
    "RH2_OBS_RUNNER_DIGEST": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792",
    "RH2_OBS_RUNNER_DIGEST_PRE": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792"
  },
  "candidate": {
    "apply_method": "noop",
    "apply_stderr_tail": null,
    "apply_user": "agent/54321",
    "kind": "noop",
    "origin": "noop",
    "patch_sha256": null
  },
  "projection": {
    "frozen_patch_digest": "sha256:eb7d34aa87433c8f944832bafff0451275ee219cd4e88e2bfb2a9e09cedf2a00",
    "ignored_paths": [],
    "included_paths": [],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.407,
    "install_skipped": false,
    "log_partial": false,
    "markers_seen": [
      "RH2_INSTALL_RC",
      "RH2_TEST_RC",
      "RH2_TS_INSTALL_END",
      "RH2_TS_INSTALL_START",
      "RH2_TS_TEST_END",
      "RH2_TS_TEST_START"
    ],
    "test_rc": 1,
    "test_seconds": 1.028
  },
  "test": {
    "rc": 1,
    "seconds": 1.028
  },
  "report": {
    "execution_failure_evidence": [],
    "execution_failure_stage": null,
    "f2p_pass": 0,
    "f2p_total": 4,
    "failure_category": "tests_failed",
    "grader_version": "swebench-4.1.0+swegym_parsers@242429c1",
    "grading_semantics": "swe_f2p_p2p",
    "infra_failure_detail": null,
    "outcome": "unresolved",
    "p2p_fail": 0,
    "p2p_total": 3,
    "report_id": "rpt_grading_31f12366",
    "reward": 0.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 7,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_NO"
  },
  "resource": {
    "mem_peak_mb": 67.613,
    "mem_peak_unavailable_or_zero": false
  },
  "cleanup": {
    "detail": "",
    "removed": true,
    "steps": [
      "rm:ok"
    ]
  }
}
```

原件受限 JSON pointers 核读：
```json
{
  "projection": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-4bfffebb/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:eb7d34aa87433c8f944832bafff0451275ee219cd4e88e2bfb2a9e09cedf2a00",
      "/physical_attempt_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-11560-4bfffebb",
      "/rollout_execution_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-11560",
      "/included_entry_paths": []
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-4bfffebb/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-11560",
      "/task_base_commit": "345be91a038e1bda707e07a19889953412d358dc",
      "/materialized_head": "345be91a038e1bda707e07a19889953412d358dc"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-4bfffebb/stage.json",
    "selected": {
      "/apply_method": "noop",
      "/head": "345be91a038e1bda707e07a19889953412d358dc"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
165: + git -c core.fileMode=false diff 345be91a038e1bda707e07a19889953412d358dc
169: + git checkout 345be91a038e1bda707e07a19889953412d358dc -- conans/test/unittests/tools/google/test_bazeldeps.py
206: RH2_SETUP_OK=1
349: + python -m pip install -r conans/requirements.txt
370: + python -m pip install -r conans/requirements_server.txt
374: + python -m pip install -r conans/requirements_dev.txt
397: RH2_INSTALL_RC=0
407: + pytest -n0 -rA conans/test/unittests/tools/google/test_bazeldeps.py
412: collected 7 items
621: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_interface_buildfiles
622: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_main_buildfile
623: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_build_dependency_buildfiles
624: FAILED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_dependency_buildfiles
625: FAILED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_get_lib_file_path_by_basename
626: FAILED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_dependency_transitive
627: FAILED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_shared_library_interface_buildfiles
628: ==================== 4 failed, 3 passed, 1 warning in 0.27s ====================
632: RH2_TEST_RC=1
```

### gold

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:12`，本行 SHA256 `864aa785646f5518fa3d3e31285390d5390b93762afee8ce364bf8fb951d7e72`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_d3546252.eval.log` 的授权 `1–464`，全文 hash `44b3777af3f83ff8ba52f4e0041b192a969bf2a2b31f9d68cda3dddd964285d6` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-11560:latest",
  "image_digest_expected": "sha256:2ab97e51d7c77d280b6e818043472af58b388043171bfb6a725deda81583b44e",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:b7f064d894d6b9811e171c1a3e78278950ee91ed5f4cc9850aced3fb4f19f6da",
  "policy": {
    "candidate_writable_prefixes": [
      "/opt/miniconda3/envs/testbed"
    ],
    "cpus": 2.0,
    "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a",
    "memory_bytes": 4294967296,
    "network": "deny_all",
    "pids_limit": 512,
    "profile_id": "rh2.grader_sandbox_profile.v1",
    "shm_bytes": 67108864,
    "tmpfs_bytes": 1073741824,
    "uid": 54322,
    "user": "rh2grader"
  },
  "budgets": {
    "candidate_stage_seconds": 900.0,
    "cleanup_seconds": 120.0,
    "grading_deadline_seconds": 3600.0,
    "image_pull_seconds": 1800.0
  },
  "observations": {
    "RH2_OBS_IMPORT_PATH": "/testbed/conans/__init__.py",
    "RH2_OBS_PKG_VERSION": "1.51.0-dev",
    "RH2_OBS_PREFIX_OWNER_PRE": "54322",
    "RH2_OBS_RUNNER_DIGEST": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792",
    "RH2_OBS_RUNNER_DIGEST_PRE": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792"
  },
  "candidate": {
    "apply_method": "git_apply",
    "apply_stderr_tail": null,
    "apply_user": "agent/54321",
    "kind": "gold",
    "origin": "/work/full216_20260919/replay/gold/conan-io__conan-11560.gold.patch",
    "patch_sha256": "sha256:0c0a96da87e7f6b88ce14b06d27237cbae8f4b2534e1bbe27f4fc078ad1d7897"
  },
  "projection": {
    "frozen_patch_digest": "sha256:00d729f5ed1ed8bbdda7fa574dd154fc75c7c582d44fcd27bce75d1493bcd1e5",
    "ignored_paths": [],
    "included_paths": [
      "conan/tools/google/bazeldeps.py"
    ],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.316,
    "install_skipped": false,
    "log_partial": false,
    "markers_seen": [
      "RH2_INSTALL_RC",
      "RH2_TEST_RC",
      "RH2_TS_INSTALL_END",
      "RH2_TS_INSTALL_START",
      "RH2_TS_TEST_END",
      "RH2_TS_TEST_START"
    ],
    "test_rc": 0,
    "test_seconds": 0.933
  },
  "test": {
    "rc": 0,
    "seconds": 0.933
  },
  "report": {
    "execution_failure_evidence": [],
    "execution_failure_stage": null,
    "f2p_pass": 4,
    "f2p_total": 4,
    "failure_category": null,
    "grader_version": "swebench-4.1.0+swegym_parsers@242429c1",
    "grading_semantics": "swe_f2p_p2p",
    "infra_failure_detail": null,
    "outcome": "resolved",
    "p2p_fail": 0,
    "p2p_total": 3,
    "report_id": "rpt_grading_d3546252",
    "reward": 1.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 7,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_FULL"
  },
  "resource": {
    "mem_peak_mb": 71.625,
    "mem_peak_unavailable_or_zero": false
  },
  "cleanup": {
    "detail": "",
    "removed": true,
    "steps": [
      "rm:ok"
    ]
  }
}
```

原件受限 JSON pointers 核读：
```json
{
  "projection": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-07a18c66/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:00d729f5ed1ed8bbdda7fa574dd154fc75c7c582d44fcd27bce75d1493bcd1e5",
      "/physical_attempt_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-11560-07a18c66",
      "/rollout_execution_id": "replay-f216-baseline01-w01-2-swe_gym_lite--conan-io__conan-11560",
      "/included_entry_paths": [
        "conan/tools/google/bazeldeps.py"
      ]
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-07a18c66/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-11560",
      "/task_base_commit": "345be91a038e1bda707e07a19889953412d358dc",
      "/materialized_head": "345be91a038e1bda707e07a19889953412d358dc"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/artifacts/swe_gym_lite--conan-io__conan-11560/a1-07a18c66/stage.json",
    "selected": {
      "/apply_method": "git_apply",
      "/head": "345be91a038e1bda707e07a19889953412d358dc"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
170: + git -c core.fileMode=false diff 345be91a038e1bda707e07a19889953412d358dc
195: + git checkout 345be91a038e1bda707e07a19889953412d358dc -- conans/test/unittests/tools/google/test_bazeldeps.py
232: RH2_SETUP_OK=1
375: + python -m pip install -r conans/requirements.txt
396: + python -m pip install -r conans/requirements_server.txt
400: + python -m pip install -r conans/requirements_dev.txt
423: RH2_INSTALL_RC=0
433: + pytest -n0 -rA conans/test/unittests/tools/google/test_bazeldeps.py
438: collected 7 items
450: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_dependency_buildfiles
451: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_get_lib_file_path_by_basename
452: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_dependency_transitive
453: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_interface_buildfiles
454: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_shared_library_interface_buildfiles
455: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_main_buildfile
456: PASSED conans/test/unittests/tools/google/test_bazeldeps.py::test_bazeldeps_build_dependency_buildfiles
457: ========================= 7 passed, 1 warning in 0.18s =========================
461: RH2_TEST_RC=0
```

本稿封存后不改写；只有 root 明确 history release 后另写 delta/card/record。
