# conan-io__conan-12397 — analysis before history

## 身份、运行条件、交付与证据边界
本稿由 fresh 私有主审 e25_main_pack06_conan 在 history release 前形成。ROOT 固定为 `/Users/roger/Desktop/claude-code-verl-stage0h`；P 为本题 `runs/swegym_quality_expansion_20260925/public/<task>`，S=P/base，V 为对应 private 目录。下述源文件行号均相对本题 S。所有 exec 显式 ROOT；只读静态文件/授权原件与 stdlib 文本/JSON/hash，未执行/导入项目、测试、安装、网络、容器、SSH、GPU、模型，也未修改原题/测试/gold/评分或派生 agent。

八方面已分别覆盖：公开目标与疑义、版本初态、全部增改断言/F2P/P2P、合理非 gold 与误拒、gold/相关 caller/回归、开发需求与资产、合法交付与可信测试恢复、关系/答案暴露/用途。运行引用是已存在的历史 RH2 原件，不是旧质量判断，不是本轮 CPU 或真实模型运行。

check3 实际用户/system 消息、工具呈现与 public_hints 交付仍 unknown；check4/6–13/33 当前 actor UID/HOME/cwd/PATH、解释器、读写权限、依赖/忽略资产、网络和资源未取证。历史 noop 工作树状态在 trusted setup 前显示 clean；gold 显示唯一修复源码相对 base 的 diff。`git show` 的基线提交 diff 不是初始未提交改动。当前 actor 初态、来源规定变更、准备后 porcelain status/RC 仍 unknown，不能从静态 Git 导出或历史 grader 状态代替。镜像 tag、expected manifest digest 与 actual image ID 分开，后者 null。

check9/16/17/18/19 的局部正证据是 candidate SHA、投影路径、基线/阶段指针、可信测试从 base checkout 后 test.patch cleanly applied，以及下列实际选择和逐测试输出；未查任意候选全部安全性质。仅有来源 parser 标识/逐测试映射，没有完整 scorer 控制面源码审计。历史日志没有相关 expected skip/xfail/missing；缺失或 skip 不能算通过。安装成功只指最后命令 RC 0，日志所查 pip 依赖为 already satisfied；不推广到所有历史依赖可从零恢复。

check5 同仓不同 base/不同目标的本包关系可见，但没有跨池重复/留出检索授权，因此 overlap unknown。check29 实际 actor 可见未来答案 unknown；usage 的审查者私有暴露已知：本题 gold、隐藏 test.patch、expected、noop/gold 原件与封存 public_read；尚未读 history/旧质量记录/reviewer。check30 外部取答与31评分控制面攻击能力未核。check34/35/36 没有真实模型能力、完整解答诚实性或训练阶段适配证据。check14/15 重复评分/并发/缓存变化未验证；check37–39 本轮没有环境/题目修订，复验及共享影响 unknown。check40 流程封存不能证明无漏检、误拒或抽样偏差，本稿已记录具体局限。

最终用途仅 `development_diagnostic`，不得据此批准训练/正式评测。`file_rules.additional_exclusions=[]`、`revision_refs=[]`；disposition=`needs_review/static_review`。没有本轮 token/费用观测，costs 相关值 null；下述历史秒数/资源只保留原字段和值，不转成本或资格。

## 初判与公开目标（23、25、27）
静态初判：needs_review / static_review，可定位且 gold 有局部正确性证据，但现有验收不足以确认题面 Linux Clang+libc++ 路径。目标是 Meson 生成的 C++ 链接参数携带与编译一致的标准库选择，包与 test_package 正确链接。gold 全部修改只在 `if self.libcxx` 内增加 `self.cpp_link_args.append(self.libcxx)`，与根因直接对应。无需硬编码 libc++、复制全部编译参数或扩展其他构建系统。

`S/conan/tools/meson/toolchain.py:1–377` 全读：初始化 :135 调 libcxx_flags，:175–180 初始化环境 flags；:303–321 在上下文追加 Apple/conf 和 libcxx；:355–356 分别序列化；:367–377 content/generate 共用 native/cross 模板。`S/conan/tools/_compilers.py:68–98` 全读决定性 helper：clang/intel-cc 按 libcxx 映射 -stdlib，apple-clang 独立映射；gcc 的第二返回值是 ABI 宏，不是链接标志；sun-cc/qcc 的非 -stdlib 值未实测。`helpers.py:79–95` 序列化字符串/列表和 cppstd。不能把这些静态映射称为各编译器已经验证。

## 需求—断言双向表
测试文件 `S/conans/test/integration/toolchains/meson/test_mesontoolchain.py:1–120` 全文已读，test.patch 全部三个 hunk 已读；无新函数，F2P 1、P2P 2。

| 需求或旧行为 | 公开依据 | 测试 ID / 断言 | 覆盖与证据层次 |
|---|---|---|---|
| Clang+libc++ 的 cpp 编译、链接保持同一 STL | 题面 Notes/Workaround；helper :77–81 | F2P `test_apple_meson_keep_user_custom_flags`：Apple cross profile，新增 cpp_args/cpp_link_args 含尾部 -stdlib=libc++ 的子串断言 | 仅 apple-clang 配置生成，Linux clang native 路径缺失；不编译链接 |
| 用户 Apple SDK、arch、最低版本 flags 保留 | 旧行为 :242–259、:304–310 | 同 F2P c_args/c_link_args 仍要求原序列，cpp 两项追加 stdlib | 已读；原顺序明确在测试输出中，无法推出所有等价 flags 顺序必须拒绝 |
| GCC ABI 宏只进编译，conf/环境链接 flags 保留 | helper :92–98；公开“不应复制全部编译选项”的合理旧行为 | P2P `test_extra_flags_via_conf`：profile 从 libstdc++11 改为 libstdc++；cpp_args 新增 -D_GLIBCXX_USE_CXX11_ABI=0；c_args/c_link_args/cpp_link_args 原期望保持 | 该 modified P2P 已完整读；base 本来支持 ABI=0，noop 也过；不是 gold 新增 ABI 功能 |
| 默认引号/cppstd/backend/buildtype | 原模板 | P2P `test_correct_quotes` 要求 c++17、ninja、release 子串 | 已读、两端通过；无 stdlib 链接断言 |
| libc++/libstdc++ 选择不应硬编码；native/cross 共用 | helper 和题面标准库选择 | expected 无 Linux clang、clang libstdc++、空 libcxx 测试 | 缺失（25），错误实现可只补 apple-clang 而通过；不是已证明 gold 错误 |
| 包与 test_package 实际链接成功 | 题面 Expected；模板 `new_v2_meson.py:28–35,53–71` | 三项仅 TestClient install+load 配置文件 | 缺失；没有真实 Meson、Clang/libc++ 构建证据 |

## helper、调用者与断言身份陷阱
TestClient 读取 :325–450、490–535、541–608：临时缓存初始化/复制，默认 remotes 清空，save/load，run_cli 在 current_folder 调 Conan Command 并恢复 cwd，错误状态不合预期会抛出；因此三测试真实经过 Conan install/generate，不只是直接 mock `_context`。该版本的 deeper ClientCache/Command 路径没有逐行穷尽。模板 `new_v2_meson.py:1–100` 同时在包 generate 和 test_package generator 使用 MesonToolchain，gold 的公共路径能影响两处。工具 conftest 的 autouse :292–327 仅处理 tool_ 标记；这三个函数只有 Py2 skipif，历史 Python3.10 均实际执行。

关键漏检：`"cpp_link_args = [...]" in content` 未锚定键名；模板同样生成 `objcpp_link_args`，其后缀也含该字符串。旧 Apple cpp_args 期望缺 stdlib 却能通过，因为 objcpp_args 在加入 libcxx 之前已复制旧列表。test.patch 改为期望 stdlib 后，当前 gold 正常匹配真正 cpp 行；但若错误实现只对 Objective-C++ link 列表加 flag，F2P 的链接断言也可能在 objcpp_link_args 行匹配，真正 cpp 链接仍错误。这是可由两字符串和模板直接推导的特定漏测（25），尚无候选运行实验。另一方面，断言要求 flags 精确布局/顺序，合法等价序列化可能被拒；应按确切配置键读列表而非子串。不能因此断言所有 flags 调序等价，因为冲突 flags 优先级会受顺序影响。

## gold 正确性、边界和合理替代解
局部正证据（27）：gold 使用已有非空选择值，保留 LDFLAGS/conf，ABI 分支未动；native/cross 共用 cpp_link_args 输出。这支持公开修复方向，历史 1 F2P+2 P2P 通过。合理非 gold：在渲染上下文对 cpp_link_args 组合 stdlib 而不修改实例列表，或在初始化建立所需标志，只要保留 recipe 可修改性/既有优先级。现有测试不锁定 append 所在语句；未实际执行替代解，不能泛称无误拒（24 unknown/静态风险）。

重复读取 content 会重复 extend/append，大部分为 base 原有副作用，gold 会把新链接 flag 也累加；没有证据说明正常 caller 多次读取产生实际损坏，不记作已证 gold 回归（26 unknown）。Objective-C++ 漏 stdlib 在 base 已存在，且题面明确 cpp；不把它强行纳为 gold 必修回归（28）。sun-cc/qcc 额外链接值语义、冲突手写 -stdlib、完整编译边界仍未验证。

公开复现 `conan new ... -s compiler=...` 存在参数疑义，封存 public_read 指出 -s 为 sources；本审查未独立读取 command parser，因此将此作为公开阅读记录的待核说明，不夸称自己原件复验。不会因这一文字瑕疵否定清楚的 cpp_link_args 要求。

## 开发需求与合法交付
| 操作/资产 | 公开依据 | 现有证据/适用对象与缺口 | 最小公开命令及预期（未执行） |
|---|---|---|---|
| 实际初态、源码写权限、导入来源 | public_hints；toolchain.py | 历史 gold 仅投影该源码；actor unknown | `git status --porcelain=v1`；`python -c "import conan; print(conan.__file__)"`，核对实际来源和初始差异 |
| Python/Jinja2/Conan 测试缓存 | requirements、TestClient | 历史 grader pip RC0、三测试执行；actor 临时目录/HOME/PATH unknown | `python -m pytest -q conans/test/integration/toolchains/meson/test_mesontoolchain.py`，旧公开断言通过只证明旧范围 |
| Linux Clang+libc++ 生成准确 cpp_link_args | 题面、libcxx_flags | 生成路径无需 Clang 二进制；当前 expected 未测此 profile | 临时公开 recipe/profile 后 `conan install . -pr:h clang14-libcxx -pr:b default`；按完整键检查 conan_meson_native.ini 的 cpp_link_args、保留自定义链接 flags |
| 包与 test_package 的真实链接 | new_v2_meson.py:1–100 | Clang14、libc++头/库、Meson/ninja/pkg-config/linker 和当前 actor 资产 unknown | 分开 `conan new conan_meson/1.0.0 -m meson_lib` 与完整 profile 的 `conan create . -pr:h clang14-libcxx -pr:b default`；检查实际链接命令及 test_package 成功 |

临时验证放独立目录，不修改禁止提交的可信测试。公开模板未显示必须公网、凭证、GPU；安装依赖可预置，实际 actor 的网络供应另验。历史生成测试不证明编译器/标准库资产存在。候选/可信测试路径分离有局部交付证据；未审计任意候选篡改控制面的能力。

## 唯一优先下一步
补一个按确切键读取生成文件的 Linux clang/libc++ native 最小验收，并用“只修 objcpp_link_args”的错误候选确认它被拒绝；其判别目标是现有 F2P 的后缀匹配漏检及未覆盖题面配置。可以交任务二做局部 CPU 验证，不需要全仓或模型；本轮未执行、不把该候选当合法修复。

## 阅读范围与未读
除上述完整工具链/测试和 helper 范围，P 三公开身份/提示文件及封存 public_read 全文；gold/test、grading、validation、run_refs 内容/原件对应指针；requirements、pytest.ini 全读。conftest 仅搜索和 :287–327；未读其完整工具表/插件深层。原日志只核授权任务及相关区段/匹配行，未读其他任务行或质量历史。未读取或运行外部编译器文档、完整链接工程、全仓测试、真实 actor 输入；不以同仓别题替代证据。

## 原始运行证据附录（本题限定）

静态 base_commit `883eff8961d6e0d96652f78e3d7d3884479e769e`；base_tree `c613a62d0d4650723d28d1e20aaca3b2ec2b4757`；blob inventory SHA256 `11f15968d8358c02d57f5e810892948077f52c2d43641c0e3a79d97c665775a8`。grading version `1.54`、Python 声明 `3.10`、eval_cmd `pytest -n0 -rA`；公开报告者版本与实际 base 开发版本不强行相等。validation gold SHA `sha256:a2601a41c874af2aff7fb7a867d381af14ee7f0e63844e172ad6d3dd4a52c457`。

- V/gold.patch SHA256 `a2601a41c874af2aff7fb7a867d381af14ee7f0e63844e172ad6d3dd4a52c457`。
- V/test.patch SHA256 `444addc85bb304ccc3a4caecc3ce5d52a9f0dffe89ba92ea897d55c69bf02375`。
- V/grading.json SHA256 `64171910608dccc93e11719e592d01610aa5192ed404aa4c34cf9d8b49536890`。
- V/run_refs.json SHA256 `1db64b0562fccc72e787c9d48494cbe121ccc82b6d21db59687e4594fd242e13`。

### noop

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/ledger.jsonl:13`，本行 SHA256 `6fc3eadb1667be26854124e5fecb8750a385643cde53e03b4f1fc56e104acf3e`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/eval_logs/evallog_replay-f216-baseline01-w_540c82fd.eval.log` 的授权 `1–523`，全文 hash `18659f49d77677206cc04e207db78c353908c05e52434ffc7b164840f6e947f8` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-12397:latest",
  "image_digest_expected": "sha256:b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:32f297e2f2f65e1e457b94a30201b015b04c2da546944319f627f544f01b31c8",
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
    "RH2_OBS_PKG_VERSION": "1.54.0-dev",
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
    "frozen_patch_digest": "sha256:6683816b4536132fc410a453cd852ecda052efe4e5018627405675a2ae58488e",
    "ignored_paths": [],
    "included_paths": [],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.405,
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
    "test_seconds": 1.818
  },
  "test": {
    "rc": 1,
    "seconds": 1.818
  },
  "report": {
    "execution_failure_evidence": [],
    "execution_failure_stage": null,
    "f2p_pass": 0,
    "f2p_total": 1,
    "failure_category": "tests_failed",
    "grader_version": "swebench-4.1.0+swegym_parsers@242429c1",
    "grading_semantics": "swe_f2p_p2p",
    "infra_failure_detail": null,
    "outcome": "unresolved",
    "p2p_fail": 0,
    "p2p_total": 2,
    "report_id": "rpt_grading_540c82fd",
    "reward": 0.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 3,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_NO"
  },
  "resource": {
    "mem_peak_mb": 89.688,
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
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-390dfa20/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:6683816b4536132fc410a453cd852ecda052efe4e5018627405675a2ae58488e",
      "/physical_attempt_id": "replay-f216-baseline01-w01-0-swe_gym_lite--conan-io__conan-12397-390dfa20",
      "/rollout_execution_id": "replay-f216-baseline01-w01-0-swe_gym_lite--conan-io__conan-12397",
      "/included_entry_paths": []
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-390dfa20/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-12397",
      "/task_base_commit": "883eff8961d6e0d96652f78e3d7d3884479e769e",
      "/materialized_head": "883eff8961d6e0d96652f78e3d7d3884479e769e"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-390dfa20/stage.json",
    "selected": {
      "/apply_method": "noop",
      "/head": "883eff8961d6e0d96652f78e3d7d3884479e769e"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
187: + git -c core.fileMode=false diff 883eff8961d6e0d96652f78e3d7d3884479e769e
191: + git checkout 883eff8961d6e0d96652f78e3d7d3884479e769e -- conans/test/integration/toolchains/meson/test_mesontoolchain.py
228: RH2_SETUP_OK=1
371: + python -m pip install -r conans/requirements.txt
392: + python -m pip install -r conans/requirements_server.txt
396: + python -m pip install -r conans/requirements_dev.txt
419: RH2_INSTALL_RC=0
429: + pytest -n0 -rA conans/test/integration/toolchains/meson/test_mesontoolchain.py
434: collected 3 items
513: PASSED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_extra_flags_via_conf
514: PASSED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_correct_quotes
515: FAILED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_apple_meson_keep_user_custom_flags
516: =================== 1 failed, 2 passed, 3 warnings in 1.11s ====================
520: RH2_TEST_RC=1
```

### gold

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/ledger.jsonl:14`，本行 SHA256 `aab10f15da90153459797373e5cd6702d310e386abc595a7f98ac6712617c2cb`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/eval_logs/evallog_replay-f216-baseline01-w_b0585990.eval.log` 的授权 `1–481`，全文 hash `d1f48cd16040e586773da7373a940c094c21fa016ce4ad19577ec910044aa1a7` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-12397:latest",
  "image_digest_expected": "sha256:b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:32f297e2f2f65e1e457b94a30201b015b04c2da546944319f627f544f01b31c8",
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
    "RH2_OBS_PKG_VERSION": "1.54.0-dev",
    "RH2_OBS_PREFIX_OWNER_PRE": "54322",
    "RH2_OBS_RUNNER_DIGEST": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792",
    "RH2_OBS_RUNNER_DIGEST_PRE": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792"
  },
  "candidate": {
    "apply_method": "git_apply",
    "apply_stderr_tail": null,
    "apply_user": "agent/54321",
    "kind": "gold",
    "origin": "/work/full216_20260919/replay/gold/conan-io__conan-12397.gold.patch",
    "patch_sha256": "sha256:a2601a41c874af2aff7fb7a867d381af14ee7f0e63844e172ad6d3dd4a52c457"
  },
  "projection": {
    "frozen_patch_digest": "sha256:0a803532b8b0d9f8a7339bbbaceed420209e4b398821aeebc7e06fda3c9ebf3a",
    "ignored_paths": [],
    "included_paths": [
      "conan/tools/meson/toolchain.py"
    ],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.071,
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
    "test_seconds": 1.857
  },
  "test": {
    "rc": 0,
    "seconds": 1.857
  },
  "report": {
    "execution_failure_evidence": [],
    "execution_failure_stage": null,
    "f2p_pass": 1,
    "f2p_total": 1,
    "failure_category": null,
    "grader_version": "swebench-4.1.0+swegym_parsers@242429c1",
    "grading_semantics": "swe_f2p_p2p",
    "infra_failure_detail": null,
    "outcome": "resolved",
    "p2p_fail": 0,
    "p2p_total": 2,
    "report_id": "rpt_grading_b0585990",
    "reward": 1.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 3,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_FULL"
  },
  "resource": {
    "mem_peak_mb": 85.195,
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
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-d54304e4/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:0a803532b8b0d9f8a7339bbbaceed420209e4b398821aeebc7e06fda3c9ebf3a",
      "/physical_attempt_id": "replay-f216-baseline01-w01-0-swe_gym_lite--conan-io__conan-12397-d54304e4",
      "/rollout_execution_id": "replay-f216-baseline01-w01-0-swe_gym_lite--conan-io__conan-12397",
      "/included_entry_paths": [
        "conan/tools/meson/toolchain.py"
      ]
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-d54304e4/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-12397",
      "/task_base_commit": "883eff8961d6e0d96652f78e3d7d3884479e769e",
      "/materialized_head": "883eff8961d6e0d96652f78e3d7d3884479e769e"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-0/artifacts/swe_gym_lite--conan-io__conan-12397/a1-d54304e4/stage.json",
    "selected": {
      "/apply_method": "git_apply",
      "/head": "883eff8961d6e0d96652f78e3d7d3884479e769e"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
192: + git -c core.fileMode=false diff 883eff8961d6e0d96652f78e3d7d3884479e769e
208: + git checkout 883eff8961d6e0d96652f78e3d7d3884479e769e -- conans/test/integration/toolchains/meson/test_mesontoolchain.py
245: RH2_SETUP_OK=1
388: + python -m pip install -r conans/requirements.txt
409: + python -m pip install -r conans/requirements_server.txt
413: + python -m pip install -r conans/requirements_dev.txt
436: RH2_INSTALL_RC=0
446: + pytest -n0 -rA conans/test/integration/toolchains/meson/test_mesontoolchain.py
451: collected 3 items
471: PASSED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_apple_meson_keep_user_custom_flags
472: PASSED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_extra_flags_via_conf
473: PASSED conans/test/integration/toolchains/meson/test_mesontoolchain.py::test_correct_quotes
474: ======================== 3 passed, 3 warnings in 1.14s =========================
478: RH2_TEST_RC=0
```

本稿封存后不改写；只有 root 明确 history release 后另写 delta/card/record。
