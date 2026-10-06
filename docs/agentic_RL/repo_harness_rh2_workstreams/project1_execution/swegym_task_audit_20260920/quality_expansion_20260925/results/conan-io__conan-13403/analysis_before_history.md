# conan-io__conan-13403 — analysis before history

## 身份、运行条件、交付与证据边界
本稿由 fresh 私有主审 e25_main_pack06_conan 在 history release 前形成。ROOT 固定为 `/Users/roger/Desktop/claude-code-verl-stage0h`；P 为本题 `runs/swegym_quality_expansion_20260925/public/<task>`，S=P/base，V 为对应 private 目录。下述源文件行号均相对本题 S。所有 exec 显式 ROOT；只读静态文件/授权原件与 stdlib 文本/JSON/hash，未执行/导入项目、测试、安装、网络、容器、SSH、GPU、模型，也未修改原题/测试/gold/评分或派生 agent。

八方面已分别覆盖：公开目标与疑义、版本初态、全部增改断言/F2P/P2P、合理非 gold 与误拒、gold/相关 caller/回归、开发需求与资产、合法交付与可信测试恢复、关系/答案暴露/用途。运行引用是已存在的历史 RH2 原件，不是旧质量判断，不是本轮 CPU 或真实模型运行。

check3 实际用户/system 消息、工具呈现与 public_hints 交付仍 unknown；check4/6–13/33 当前 actor UID/HOME/cwd/PATH、解释器、读写权限、依赖/忽略资产、网络和资源未取证。历史 noop 工作树状态在 trusted setup 前显示 clean；gold 显示唯一修复源码相对 base 的 diff。`git show` 的基线提交 diff 不是初始未提交改动。当前 actor 初态、来源规定变更、准备后 porcelain status/RC 仍 unknown，不能从静态 Git 导出或历史 grader 状态代替。镜像 tag、expected manifest digest 与 actual image ID 分开，后者 null。

check9/16/17/18/19 的局部正证据是 candidate SHA、投影路径、基线/阶段指针、可信测试从 base checkout 后 test.patch cleanly applied，以及下列实际选择和逐测试输出；未查任意候选全部安全性质。仅有来源 parser 标识/逐测试映射，没有完整 scorer 控制面源码审计。历史日志没有相关 expected skip/xfail/missing；缺失或 skip 不能算通过。安装成功只指最后命令 RC 0，日志所查 pip 依赖为 already satisfied；不推广到所有历史依赖可从零恢复。

check5 同仓不同 base/不同目标的本包关系可见，但没有跨池重复/留出检索授权，因此 overlap unknown。check29 实际 actor 可见未来答案 unknown；usage 的审查者私有暴露已知：本题 gold、隐藏 test.patch、expected、noop/gold 原件与封存 public_read；尚未读 history/旧质量记录/reviewer。check30 外部取答与31评分控制面攻击能力未核。check34/35/36 没有真实模型能力、完整解答诚实性或训练阶段适配证据。check14/15 重复评分/并发/缓存变化未验证；check37–39 本轮没有环境/题目修订，复验及共享影响 unknown。check40 流程封存不能证明无漏检、误拒或抽样偏差，本稿已记录具体局限。

最终用途仅 `development_diagnostic`，不得据此批准训练/正式评测。`file_rules.additional_exclusions=[]`、`revision_refs=[]`；disposition=`needs_review/static_review`。没有本轮 token/费用观测，costs 相关值 null；下述历史秒数/资源只保留原字段和值，不转成本或资格。

## 初判与公开目标（23–27）
静态初判：needs_review / static_review；新增目录入口方向可定位，但 gold 有可直接推导的旧位置参数兼容性破坏，测试又绑定内部 chdir 调用，不能仅凭 gold 通过当完整正确。公开用户要在 build_folder 的 configure.ac 上运行 autoreconf，而无需改 recipe.source_folder。base `S/conan/tools/gnu/autotools.py:101–111` 无条件进入 source_folder，外层 chdir 会被覆盖；这是明确源码证据，不是本轮执行复现。

gold 全改动已逐行读：签名从 `autoreconf(self, args=None)` 改成 `autoreconf(self, build_script_folder=None, args=None)`；文档新增目录参数；相对目录 join source_folder，缺省仍 source_folder；chdir 使用新目录。configure 的既有 :36–59 使用相同 join 规则，所以相对源码路径有公开 API 类比；绝对 build_folder 在 Linux join 下可覆盖 source 前缀。目录参数名称可从 configure 合理推断但题面没有明确把位置顺序或内部 helper 调用作为契约。

## 需求—断言双向表
唯一 F2P 为 `S/conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works`；base :1–26 全读，test.patch 全部两 hunk 已读；P2P=[]，不能称回归覆盖完整。

| 需求或合理旧行为 | 依据 | 增改后断言与 fixture | 覆盖判断 |
|---|---|---|---|
| 能显式选择 autoreconf 执行目录 | 题面 build_folder；configure 类比 | `autoreconf(build_script_folder="subfolder")`；`chdir_mock.assert_called_with(autotools, "/path/to/sources/subfolder")` | 只验证源码相对子目录与内部调用；没有 build_folder/绝对目录/实际 cwd（25） |
| 无参数仍在 source_folder，保留 toolchain 参数 | base :101–111 | `autoreconf()` 后 assert_called_with 源目录；最后 command 等于 `autoreconf -bar foo` | 缺省目录“调用意图”及命令覆盖；实际 chdir 被 mock |
| configure 相对/默认路径不变 | base :36–59 | 原两条 command 字符串断言保持 | 局部回归正证据，嵌在唯一 F2P 内，不是额外 P2P |
| 旧 args 调用继续有效（位置及关键字） | base 签名/文档 :101–106；cmd_args_to_string | 无显式 args 断言；fixture 只把配置 autoreconf_args 从空改为 -bar foo | 缺失；gold 位置调用破坏单独列 26，不只列 25 |
| 真实执行目录正确、退出/异常恢复外层 cwd | 题面行为；chdir :289–303 | `@patch('conan.tools.gnu.autotools.chdir')`，运行只是 ConanFileMock 保存命令 | 未覆盖；可只调用 helper 不进入上下文仍骗过相关调用断言 |
| 不修改 source_folder；实际 configure.ac 成功处理 | 题面明确不愿改 source_folder | 没有 recipe.folder 不变、真实 autoreconf 或生成文件断言 | 缺失，测试只给不存在的 /path/to/sources |

决定性 helper：`S/conan/tools/files/files.py:289–303` 真正 os.chdir 并 finally 恢复；`S/conan/tools/build/__init__.py:29–60,63–105` 读取/写入 conanbuild.conf 和参数转义；`S/conans/test/utils/mocks.py:104–142` 的 run 不执行系统程序，只存 command/path/env；`test_files.py:32–47` 仅创建临时目录。唯一测试在临时 cwd 写 toolchain 参数，真实 source 目录不存在，由 MagicMock 避免 chdir 错误。没有 GNU 二进制参与。

## 合理解、误拒与 gold 回归
1. **明确静态旧接口回归（26 issue）。** 在有效配置/源码目录前提下，旧 `autoreconf(['--install'])` 把列表作为 args，由 cmd_args_to_string 正常形成命令；gold 将非空列表绑定 build_script_folder，再传入 os.path.join，列表不是路径，调用在 run 前报 TypeError。这不是“测试没覆盖所以假定坏了”，而是签名绑定与 join 入参类型的直接推导；本轮未执行，证据级别标记静态确定性推导。文档没有宣告取消旧 args 位置用法。现有调用者多用无参或 args=，不能据此把公开位置参数删除视为无风险。可保留 `args` 首位，将新目录放后面或只接受关键字，仍能通过新增 keyword 调用。
2. **内部 helper 约束误拒（24 issue）。** 当前断言强制调用本模块的 chdir，且首实参是 Autotools 对象。复用同一公开 helper 但传 self._conanfile（helper 文档恰称当前 recipe），或者采用等价 os.chdir try/finally，都能实现目录行为却不满足 mock 调用。由于 mock 下 /path/to/sources 不存在，真实 chdir 的等价实现还可能遇到 fixture 人工错误。未执行完整替代解，不泛化为所有替代都被拒；这个内部对象身份没有题面依据。
3. **漏测（25 issue）与局部正确性（27）分开。** gold 对相对、默认目录的逻辑及 Linux 绝对路径可静态说明；历史唯一 F2P 通过提供局部正证据。测试未真实进入目录、未覆盖本题 build_folder、未检查 args、未查异常恢复，因此无法保证完整目标；位置参数问题使 gold 完整正确性受限。不能以评分 1.0 消去 26。
4. 目录名含空格由 os.chdir 参数处理而非 shell 拼接，gold 不引入该处引用问题；正常/异常恢复仍复用原 helper。Windows/subsystem、不存在目录报错形式和空字符串语义没有新规格，不自创要求（28）。

相关旧功能调用者 `S/conans/test/functional/toolchains/gnu/autotools/test_basic.py:251–375` 已读：test_autotools_option_checking 无参；test_autotools_arguments_override 用 args=['--install']、配置 --verbose，保留不含 --force、含 --install 等断言。它们有 Linux/Darwin skipif 与 tool('autotools')，不在当前 expected/实跑选择中；gold 不改这些关键字调用含义。测试文件更早/更后其他功能未读，其他仓库调用未穷尽。尝试查本题 base/conans/client/templates 不存在仅是静态路径定位失败，不推断 actor 缺资产。

## 开发需求、资产与合法交付
| 操作/资产 | 公开依据 | 当前证据及适用范围/缺口 | 最小公开命令及预期（未执行） |
|---|---|---|---|
| actor 初态/写权限/源码导入 | public_hints；Autotools | 历史仅投影 autotools.py；当前 actor unknown | `git status --porcelain=v1`，`python -c "import conan; print(conan.__file__)"`；核对源码和允许初始差异 |
| 配置文件、临时 cwd 和参数行为 | load/save_toolchain_args、ConanFileMock | 历史单测跑过，不代表 actor 可写 generators_folder | 在独立临时目录以公开 save_toolchain_args 建最小配置；`python -m pytest -q conans/test/unittests/tools/gnu/autotools_test.py` 仅验证旧公开范围 |
| 目录选择和旧 args 最小 Python 探针 | 题面/旧签名/chdir | 不需要 GNU 工具即可观察 recipe.run 时 cwd；当前结果 unknown | 独立脚本创建 source/sub、build，替换 cf.run 记录 cwd 与命令；调用默认、关键字目录、绝对 build、`autoreconf(['--install'])`；分别预期 cwd 正确、args 不丢、外层目录恢复 |
| 真实 build_folder 的 configure.ac | 题面；旧 GNU 功能测试 | autoreconf/autoconf/automake/make/gcc 与项目输入的 actor 可用性 unknown | `command -v autoreconf autoconf automake make gcc` 后，用有效最小 configure.ac/Makefile.am 执行 recipe；应在 build_folder 产生预期生成文件 |
| 旧完整功能路径 | test_basic.py:251–375 | 未在本题历史选择执行；工具标记可能跳过 | `python -m pytest -q conans/test/functional/toolchains/gnu/autotools/test_basic.py -k 'option_checking or arguments_override' -rs`；须核真实执行，skip 不是通过 |

Python 层目录验证没有固定网络/GPU/模型需求；完整构建需要工具和公开输入。历史 grader 配置/依赖可用不代表 actor 资产到位。合法修复只需非测试源文件；不得把本私有测试/mocks/审查稿放入 solver，也不得用修改 trusted test 作为交付。

## 唯一优先下一步
由任务二在 actor 等价、独立私有环境做旧位置参数与新目录的同一最小行为探针，比较 base/gold/保留 args 首位的兼容实现，真实记录 run 时 cwd/命令和异常。首要判别是 gold 是否破坏合法旧调用；不需要系统 autoreconf、模型或全仓测试。probe 当前未执行，不能记 CPU 结果。mock 误拒和 build_folder 漏测仍各自保留，后续验收应按行为而非内部对象身份约束。

## 实际阅读范围与未读
P 的 user_prompt、public_bundle、environment_brief、base_identity；封存 public_read 全文；私有 gold/test/grading/validation/run_refs 和附录精确原件。Autotools :1–125、唯一测试 :1–26 全读；build/__init__.py :1–105；files.py :280–310；mocks :104–145；test_files :1–62；test_basic.py :235–375。requirements/pytest.ini 全读；conftest 仅相关匹配行和 :335–390。原日志未逐行语义审读 git show 的既有大提交正文，相关工作树 diff/恢复/安装/测试区段已读。没有读其他题/包结论、reviewer、history、外链；没有项目执行/导入/测试。静态输出身份不代替实际 actor。

## 原始运行证据附录（本题限定）

静态 base_commit `55163679ad1fa933f671ddf186e53b92bf39bbdb`；base_tree `8d117eff3b0d26609aef8485dc56691225d8cc5f`；blob inventory SHA256 `85642c72eab037c2fa5bea50e22b0d641aae418fa7646320ea571cdabf04658a`。grading version `2.1`、Python 声明 `3.10`、eval_cmd `pytest -n0 -rA`；公开报告者版本与实际 base 开发版本不强行相等。validation gold SHA `sha256:5b3a40f06e716c754804adf61a88e8f31a3a24c22f826218025707c39663fd10`。

- V/gold.patch SHA256 `5b3a40f06e716c754804adf61a88e8f31a3a24c22f826218025707c39663fd10`。
- V/test.patch SHA256 `e6811f47541fa7dd41f6434ff4009fe19af3f0a524856d7e1ae3679f7fa7d433`。
- V/grading.json SHA256 `d87f37cec04a0d121594164aeb80f98ee9ddf30c3b5605b4b0564d9848df21f5`。
- V/run_refs.json SHA256 `c27c49342be29ff4fa6370ea2ab17bddf6d964407ca0b8903e00e943ec2d8536`。

### noop

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/ledger.jsonl:13`，本行 SHA256 `9c364ba160418a07651833381538ffe62d8e1d7e36033dfb41f157dd550834fa`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/eval_logs/evallog_replay-f216-baseline01-w_956632ce.eval.log` 的授权 `1–755`，全文 hash `723f00c331489c2648fad75efe3ef60dead069d10be4277e746da43a1c028ac2` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13403:latest",
  "image_digest_expected": "sha256:6c7a9b7d705ffab262c468fcd3dca87b3cbc6ba8c772ecce155699c30a71da84",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:3552fb9bba0af3e63ef8689a1f52753a69fccfaf004b9ce0ae2c297aaa3a9cf8",
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
    "RH2_OBS_PKG_VERSION": "2.1.0-dev",
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
    "frozen_patch_digest": "sha256:5d5c06ddfd08280ed956aac204c97c1fc4e6050a37ffff1a27af23d58b3df98d",
    "ignored_paths": [],
    "included_paths": [],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.158,
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
    "test_seconds": 0.629
  },
  "test": {
    "rc": 1,
    "seconds": 0.629
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
    "p2p_total": 0,
    "report_id": "rpt_grading_956632ce",
    "reward": 0.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 1,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_NO"
  },
  "resource": {
    "mem_peak_mb": 70.383,
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
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-a753a954/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:5d5c06ddfd08280ed956aac204c97c1fc4e6050a37ffff1a27af23d58b3df98d",
      "/physical_attempt_id": "replay-f216-baseline01-w01-3-swe_gym_lite--conan-io__conan-13403-a753a954",
      "/rollout_execution_id": "replay-f216-baseline01-w01-3-swe_gym_lite--conan-io__conan-13403",
      "/included_entry_paths": []
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-a753a954/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-13403",
      "/task_base_commit": "55163679ad1fa933f671ddf186e53b92bf39bbdb",
      "/materialized_head": "55163679ad1fa933f671ddf186e53b92bf39bbdb"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-a753a954/stage.json",
    "selected": {
      "/apply_method": "noop",
      "/head": "55163679ad1fa933f671ddf186e53b92bf39bbdb"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
471: + git -c core.fileMode=false diff 55163679ad1fa933f671ddf186e53b92bf39bbdb
475: + git checkout 55163679ad1fa933f671ddf186e53b92bf39bbdb -- conans/test/unittests/tools/gnu/autotools_test.py
512: RH2_SETUP_OK=1
652: + python -m pip install -r conans/requirements.txt
667: + python -m pip install -r conans/requirements_server.txt
671: + python -m pip install -r conans/requirements_dev.txt
693: RH2_INSTALL_RC=0
703: + pytest -n0 -rA conans/test/unittests/tools/gnu/autotools_test.py
708: collected 1 item
747: FAILED conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works
748: ============================== 1 failed in 0.27s ===============================
752: RH2_TEST_RC=1
```

### gold

账本 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/ledger.jsonl:14`，本行 SHA256 `5780bf4c849b5aa0498ef1b0c0126f10934ac5cc1d3f16ddaf24071da0bb679c`，已核一致；未输出/语义阅读别题行。日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/eval_logs/evallog_replay-f216-baseline01-w_ce904c96.eval.log` 的授权 `1–760`，全文 hash `a9ac373afbd38d4be0774f63a7777bb17d3ed91ea8e55750d80c012d82a10d67` 已核；阅读范围是相关状态/diff/恢复/安装/测试区段与命令/结果匹配行，不宣称每行均语义审读。

```json
{
  "image_ref": "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13403:latest",
  "image_digest_expected": "sha256:6c7a9b7d705ffab262c468fcd3dca87b3cbc6ba8c772ecce155699c30a71da84",
  "image_id_actual": null,
  "image_local_build": false,
  "derived_image_recipe": null,
  "scripts_digest": "sha256:3552fb9bba0af3e63ef8689a1f52753a69fccfaf004b9ce0ae2c297aaa3a9cf8",
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
    "RH2_OBS_PKG_VERSION": "2.1.0-dev",
    "RH2_OBS_PREFIX_OWNER_PRE": "54322",
    "RH2_OBS_RUNNER_DIGEST": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792",
    "RH2_OBS_RUNNER_DIGEST_PRE": "9c7467b6f377ed0bd4f1924f872a3b3647d9769d51f1b60ab9e2911c4bac8792"
  },
  "candidate": {
    "apply_method": "git_apply",
    "apply_stderr_tail": null,
    "apply_user": "agent/54321",
    "kind": "gold",
    "origin": "/work/full216_20260919/replay/gold/conan-io__conan-13403.gold.patch",
    "patch_sha256": "sha256:5b3a40f06e716c754804adf61a88e8f31a3a24c22f826218025707c39663fd10"
  },
  "projection": {
    "frozen_patch_digest": "sha256:db7f3dd0c574325471f3c1491bf9d84327c866ed7023e33e2c52c4ceabc57bfd",
    "ignored_paths": [],
    "included_paths": [
      "conan/tools/gnu/autotools.py"
    ],
    "unsupported_shape_reasons": []
  },
  "install": {
    "install_rc_last_command": 0,
    "install_seconds": 2.325,
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
    "test_seconds": 0.835
  },
  "test": {
    "rc": 0,
    "seconds": 0.835
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
    "p2p_total": 0,
    "report_id": "rpt_grading_ce904c96",
    "reward": 1.0
  },
  "verdict_diagnostics": {
    "apply_ok": true,
    "num_parsed_outside_segment": 0,
    "num_parsed_tests": 1,
    "parser_source": "swegym_parsers@242429c1",
    "reference_missing": [],
    "reference_skipped": [],
    "resolution": "RESOLVED_FULL"
  },
  "resource": {
    "mem_peak_mb": 70.477,
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
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-b665b177/projection.json",
    "selected": {
      "/frozen_patch_digest": "sha256:db7f3dd0c574325471f3c1491bf9d84327c866ed7023e33e2c52c4ceabc57bfd",
      "/physical_attempt_id": "replay-f216-baseline01-w01-3-swe_gym_lite--conan-io__conan-13403-b665b177",
      "/rollout_execution_id": "replay-f216-baseline01-w01-3-swe_gym_lite--conan-io__conan-13403",
      "/included_entry_paths": [
        "conan/tools/gnu/autotools.py"
      ]
    }
  },
  "baseline": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-b665b177/baseline_manifest.json",
    "selected": {
      "/task_id": "swe_gym_lite::conan-io__conan-13403",
      "/task_base_commit": "55163679ad1fa933f671ddf186e53b92bf39bbdb",
      "/materialized_head": "55163679ad1fa933f671ddf186e53b92bf39bbdb"
    }
  },
  "stage": {
    "path": "runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/artifacts/swe_gym_lite--conan-io__conan-13403/a1-b665b177/stage.json",
    "selected": {
      "/apply_method": "git_apply",
      "/head": "55163679ad1fa933f671ddf186e53b92bf39bbdb"
    }
  }
}
```

关键原日志行（其余断言/fixture 已在正文逐项分析）：
```text
476: + git -c core.fileMode=false diff 55163679ad1fa933f671ddf186e53b92bf39bbdb
507: + git checkout 55163679ad1fa933f671ddf186e53b92bf39bbdb -- conans/test/unittests/tools/gnu/autotools_test.py
544: RH2_SETUP_OK=1
684: + python -m pip install -r conans/requirements.txt
699: + python -m pip install -r conans/requirements_server.txt
703: + python -m pip install -r conans/requirements_dev.txt
725: RH2_INSTALL_RC=0
735: + pytest -n0 -rA conans/test/unittests/tools/gnu/autotools_test.py
740: collected 1 item
752: PASSED conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works
753: ============================== 1 passed in 0.33s ===============================
757: RH2_TEST_RC=0
```

本稿封存后不改写；只有 root 明确 history release 后另写 delta/card/record。
