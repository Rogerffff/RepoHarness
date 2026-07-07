# S1-2 envpack 冻结记录（frozen_v1）：8 题 digest 清单 + 回归对照

执行日期：2026-07-07（本机，无 GPU/docker 需求）。
任务：环境包库抽取 + 8 题冻结固化 + public/private bundle 拆分（03-s1-execution-plan.md S1-2，A6 验收级 + A7 接口预留）。
验收结论先行：**库层 4 模块落地且 import 零 verifiers/swebench；8 题 bundle 拆分泄漏扫描 0 命中；官方 parser 对 S0-7 全部 8 份真实 eval 日志回归一致；`uv run pytest -q` 全套 274 用例全绿（S1-1 后 222 + 本任务 52）。远程整链回归因实例关机递延（见 §5）。**

## 1. 拆分后的代码形态

```text
rh2/src/repoharness2/envpack/          框架无关库层（import 不得引入 verifiers/swebench，单测钉死）
  materialize.py   /testbed 血缘校验：build_probe_script(base_commit) 生成探针 bash，
                   evaluate_probe(...) 解析输出并判定（base 对象存在 且 HEAD==base 或
                   HEAD^==base；叠加提交内容可非空，diffstat 只作证据）；
                   BASH_ENV_PATH/BASH_ENV_CONTENT（conda testbed 注入）一并下沉。
  scoring.py       官方 parser 评分：parse_official_eval / parse_eval_log(private_bundle, log)
                   -> EvalVerdict（严格模型）；三类 parser（django unittest verbose、
                   sympy bin/test、pytest -rA 含 ANSI）经官方 swebench 4.1.0 函数链
                   get_logs_eval -> get_eval_tests_report -> get_resolution_status；
                   swebench 保持惰性 import。A7 接口：grading_outcome_fields(verdict)
                   直接产出 contracts.GradingReport 的 outcome/failure_category/reward/
                   四计数字段组（infra_failure 永不由 parser 层产出，归 S1-4 manager）。
  bundles.py       A6 拆分：PublicTaskBundle / PrivateGradingBundle / BundlePair +
                   split_frozen_entry + 泄漏扫描 + load_bundle_pairs（防漂移校验入口）。
  freeze.py        frozen_v1 账本生成与校验（python -m repoharness2.envpack.freeze 再生成）。
  data/swe_smoke_tasks.json   题目数据从 taskset/data/ 迁入库层（140KB，内容未动，
                              字节流 sha256:190fcde8c35e…）。
  data/frozen_v1.json         本冻结记录的机器可读本体。

rh2/src/repoharness2/taskset/swebench_smoke.py   verifiers 薄壳（321 行 -> 约 200 行）：
  load_tasks/setup/@reward 全部改调库层；Task 上的 fail_to_pass/pass_to_pass/test_cmd
  字段删除（A6：私有评分材料不再随 Task 进 trace dump），评分按 instance_id 取
  private bundle。prompt/system_prompt 逐字沿用 S0-7 文本（回归锚点）。
```

## 2. bundle 拆分（A6）语义

- **PublicTaskBundle**（模型可见面，唯一允许进 rollout 容器/public projection/SFT export 的任务数据）：
  instance_id、repo、base_commit、image、image_manifest_digest、workdir(/testbed)、
  allowed_tools(bash,edit)、problem_statement（含自证 sha256）、public_hints（S0-7 SYSTEM_PROMPT 逐字）。
- **PrivateGradingBundle**（评分器专用，永不进 rollout 容器/模型上下文/训练导出）：
  golden_patch、test_patch、fail_to_pass、pass_to_pass、eval_script（官方 make_test_spec 冻结产物）、
  test_cmd、version（官方 parser/test_cmd 配置键，刻意不进 public）、environment_setup_commit。
- 三道防线：
  1. schema 白名单（`extra="forbid"`：往 public 塞 `test_patch` 字段构造期即拒）；
  2. 字段名静态互斥（PublicTaskBundle 字段名 ∩ 私有名单 = ∅，模块级 assert + 单测）；
  3. 内容泄漏扫描（split_frozen_entry 出厂前整树过 contracts 的 forbidden marker 扫描，
     命中即 BundleLeakError；名单含 golden_patch/test_patch/FAIL_TO_PASS/PASS_TO_PASS/
     hidden_verifier/grader_only + 旧 L4/L5 共 23 项）。
- **实测：8 题真实题面 + 公开提示过紧凑匹配扫描 0 误报**——S1-1 notes 留下的
  "紧凑匹配在真实题面上的误报率未知"问题就此关闭，value 扫描无需降级。

## 3. 冻结记录（frozen_v1，8 题 digest 清单）

机器可读本体：`rh2/src/repoharness2/envpack/data/frozen_v1.json`（生成确定性：同一源数据
永远生成同一记录，无运行期时间戳；`load_bundle_pairs` 默认逐题重算比对，任一 digest
不符即 FrozenRecordMismatch，fail-closed）。

- 冻结状态：8 题于 2026-07-09 经用户确认冻结（C6 选题 + C2 状态同步）。
- 源数据文件 sha256：`sha256:190fcde8c35e34b44bf5888744f7f4788857b0f878ed8878751c92a07fe488d0`
- records_digest（8 条记录的规范化 digest，inspect 四步范式锚点）：
  `sha256:1c5cba91aca10b956b1a150de86445814ed209ed1320577276d8d58e6c242328`

| instance_id | 镜像 manifest digest | 题面 sha256 | public bundle digest | private bundle digest |
| --- | --- | --- | --- | --- |
| django__django-11099 | 57060beb3096… | b0526bc6d926… | 83926ba1b2e8… | b8c98e251029… |
| django__django-11133 | cf92d32f28cf… | a7f427b7eb3f… | 7adbcf30d4bc… | 3743da056190… |
| django__django-16139 | f8c120d58e3e… | b995147ec63f… | c40b2ca4fbf1… | 4a5eef7a937e… |
| sympy__sympy-14711 | 4285e771c489… | e4767d6b2a2a… | 66171d34f23d… | 1f790bc82151… |
| sympy__sympy-15349 | b10d13ced1fd… | 9e23e96a13f1… | 96640e5aded5… | 235dd9a120d6… |
| psf__requests-1142 | 9b0b13a4a762… | 0192533ff2ef… | 240bf3194f08… | d507f0c8a5bf… |
| psf__requests-2931 | f3c752f9cb9f… | c36c337f6c5d… | c316f6708410… | a38921044b47… |
| astropy__astropy-14995 | b29a3bf3daeb… | 2eb1c507dd3a… | cdd8748aa1f9… | 620a24ffa337… |

（表中为各 digest 的前 12 位十六进制；完整 64 位值见 frozen_v1.json。digest 口径：
bundle 的 `model_dump(mode="json")` 规范化 JSON（key 排序 + 紧凑分隔符）sha256，
与 contracts.canonical_json_digest 同一实现，inspector 可独立重算。）

## 4. 本机回归（(a) 层，必做）：parser 对 S0-7 真实 eval 日志

数据源：`s0/swe_smoke_dumps/eval_logs/<instance_id>.eval.log`（428KB 原始合并流日志）
对照物：`s0/swe_smoke_dumps/<instance_id>.json` 里 S0-7 当时落盘的 summary/metrics/swe_eval。
测试：`rh2/tests/envpack/test_scoring_regression.py`（逐题参数化 + 专项）。

| instance_id | parser 族 | resolution | reward | f2p_rate | p2p_rate | 与 S0-7 记录 |
| --- | --- | --- | --- | --- | --- | --- |
| django__django-11099 | django unittest | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| django__django-11133 | django unittest | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| django__django-16139 | django unittest | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| sympy__sympy-14711 | sympy bin/test | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| sympy__sympy-15349 | sympy bin/test | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| psf__requests-1142 | pytest -rA | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致 |
| psf__requests-2931 | pytest -rA | RESOLVED_NO | 0.0 | 1.00 | 0.988 | 一致（P2P 回归条目也逐项一致） |
| astropy__astropy-14995 | pytest -rA + ANSI | RESOLVED_FULL | 1.0 | 1.00 | 1.000 | 一致（日志实测含 `\x1b[` 色码） |

对照粒度：resolution / apply_ok / reward / f2p_rate / p2p_rate / f2p_success /
f2p_failure / p2p_failure 全字段等值（不是只对 reward）。另覆盖：官方坏码日志
（`>>>>> Patch Apply Failed`）→ apply_ok=False → grading_outcome_fields 归
patch_apply_failed 且四计数为 None；三类 verdict（resolved / tests_failed /
patch_apply_failed）产出的字段组均能构造通过 contracts.GradingReport
fail-closed 校验的报告（A7 接口验收）；parser 层输出永不含 infra_failure。

## 5. 远程整链回归（(b) 层）：递延

2026-07-07 两次尝试 `ssh -p 19451 root@99.148.65.9`（间隔约 40 分钟）均 Connection
refused，ping 100% 丢包——vast 实例处于关机状态（S0-7 报告注明"用户自管实例电源"）。
按计划该层**不阻塞**：记录为 **"远程整链回归（2 题 verifiers 薄壳等价验证）递延到
S1-7a 前"**。届时动作：同步 rh2/src + experiments 到
`/workspace/claude-code-verl-stage0h/`，用 s0_swe_smoke.py 重跑 2 题
（建议 django__django-11099 + psf__requests-2931，覆盖 resolved 与 P2P 回归两态），
对照本文件 §4 表（薄壳等价判据：物化/评分链路跑通 + parser 结论与库层一致，
reward 数值受 deepseek 采样影响不作硬判据）。key 仍走 ssh stdin 注入，不落盘不回显。

薄壳等价的本机侧证据（tests/envpack/test_taskset_shell.py）：load_tasks 的
prompt/system_prompt 逐字等于库层渲染（与 S0-7 文本相同）、8 题顺序与冻结一致、
Task 对象 marker 扫描 0 命中、runner 的 subset/_rows 用法兼容未破坏。

## 6. 单测清单（52 个新用例，全绿；全套 274 全绿）

```text
tests/envpack/test_no_verifiers_import.py   2  库层纯度：干净子进程 import 全部 envpack 模块 +
                                               全量数据加载，sys.modules 零 verifiers/swebench
tests/envpack/test_materialize.py          11  血缘合法（HEAD==base / 叠加提交空 diff / 非空环境修补 /
                                               脏工作树只作证据）与非法（无血缘 HEAD / base 对象缺失 /
                                               探针失败 stdout 不可信 / 空输出）；探针脚本注入防护
tests/envpack/test_bundles.py              12  三道防线 + 8 题真实数据 0 误报 + digest 稳定互异 +
                                               配对键校验 + prompt 渲染锚点
tests/envpack/test_freeze_record.py         7  在盘账本 == 重建结果、防漂移 fail-closed（改 digest /
                                               删记录 / 错 schema_id 三种注入）
tests/envpack/test_scoring_regression.py   14  8 题真实日志逐题对照 + ANSI 专项 + P2P 回归活案例 +
                                               apply-fail 坏码 + A7 GradingReport 构造三态 +
                                               infra_failure 永不产出
tests/envpack/test_taskset_shell.py         6  薄壳任务面与 A6 纪律（见 §5）
```

## 7. 执行中发现（同步进 implementation-notes）

1. **紧凑 marker 匹配在真实题面 0 误报**（S1-1 → S1-2 的遗留问题关闭，扫描无需降级）。
2. **version 字段归私有侧**：A6 public 名单没有 version；它是官方
   MAP_REPO_TO_PARSER / MAP_REPO_VERSION_TO_SPECS 的配置键，按 fail-closed 归
   PrivateGradingBundle，模型解题不需要它。S0-7 曾把 version/F2P/P2P/test_cmd 挂在
   Task 上（会随 trace dump 序列化），本次全部移除。
3. **make_test_spec 的最小键集**：instance_id/repo/version/base_commit/test_patch/
   FAIL_TO_PASS/PASS_TO_PASS 七键即可重建 TestSpec（problem_statement 等经 .get 可缺省），
   private bundle 据此即可独立驱动官方 parser，无需保留原始 instance 全量字段。
4. **远程实例关机**（(b) 层递延，见 §5）。
