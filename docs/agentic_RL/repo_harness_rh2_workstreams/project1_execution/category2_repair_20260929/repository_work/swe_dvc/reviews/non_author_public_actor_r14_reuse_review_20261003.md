# R5 公开 actor 对 R14 的复用窄核（非作者，2026-10-03）

结论：未发现阻断三题 R5 公开 actor 历史事实复用的变化。R14 三题公开 bundle 与 R5 实际 prepared 的 public 完整对象相等，公开 prompt 构建、Claude Code 启动与受限 profile 路径未改变；固定派生镜像与 wheel 字节也匹配。可延用已有公开交付／开发核查证据，不产生一次新的 R14 actor 运行。6954 新 prepared 的公开 face 已补核；4166、9395 新 prepared 尚未提供。

本审查者已阅读三题私有材料和已有结论，不是 fresh 公开读者。仅离线读取、SHA256 与 AST／JSON／文本比较，没有运行 CPU、SSH、Docker、pytest 或项目测试，没有修改输入、共享代码或旧报告。

## 固定输入与版本

请求 `public_actor_r14_reuse_review_request_20261003.json` 实读 SHA256：`ffaafa5ab3ffd8c12d66a94f2b58352201ff8545800d4def3e7c58a122c68657`。递归核对其中 46 个 path/SHA 条目（44 个唯一文件），全部匹配。作者 actor_record 只作导航；运行事实复用既有非作者报告并抽查原始 attempt、首请求及完整公开测试 capture。

- R5：`cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。
- R14：`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。
- 两份既有非作者报告的实读 SHA：`non_author_actor6954_and_metadata_delta_review_20261003.md` = `ace9f7daf594669ab4d1f22f21eb2f7c083c9b0a08d9d6322460b2843d366f42`；`non_author_actor4166_9395_runtime_review_20261003.md` = `c914c520234eaee7da6fd9d3c20d9a84c8bd67aa509236d0c00c752ceab55632`。

本次未重新读取并逐项验收 R14 全部 1220 个 release 成员；下述结论限于请求列明文件、公开 bundle／注册表及影响公开路径的差异代码。

## 代码变化及继承范围

请求列明的七对入口中，六对字节完全相同：

| 文件（release repo 内） | R5 = R14 实读 SHA256 |
| --- | --- |
| `rh2/scripts/replay_grade.py` | `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3` |
| `rh2/experiments/task2_swegym_dev_20260925/devcheck.py` | `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160` |
| `rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py` | `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1` |
| `rh2/experiments/base_probe_fixes_20260923/stub_anthropic_endpoint.py` | `dab06b7a5ed681e9938c6033f41e3bd6947cdc19c0e333e7fc5a859d805f5138` |
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | `313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee` |
| `rh2/src/repoharness2/adapters/slime/bringup.py` | `019cbd01c06c20f5109160e555e78e7e1015ffb2614b16f6c74ab7b6c266fe3f` |


唯一变化对是 `rh2/src/repoharness2/adapters/slime/prepared_task_face.py`：R5 `77c579c2d49b899568a7a88de67df92f05439b09d1ec258a1cf3f80b51b27ac9` → R14 `22bf13dd0fc6c7b7d8ab7155c0afcef547b71acf5ff0d919c7a6c57160f7d012`。逐项阅读差异后，DVC 相关变更为私有 revision 的恢复／安装前置验证、有效测试字节检查、私有分区与固定评分镜像，以及拒绝在 DVC behavior grading 路径传入 overlay。`PreparedTaskFace` 现有方法中仅 `grading_spec` 的 AST 改变；`load`、`verify_dispatch`、`rollout_spec` 等未变。`rollout_spec_from_view`（R14 863–902 行）AST 完全相同，继续从 public 构建 task/base/prompt/workdir/image；DVC 不走新增 Conan/Moto overlay 限制。此处的私有 grading overlay 拒绝不影响既有 DevRunner 显式 actor image override。

另检查变化链的公开构建：`adapters/slime/replay_grade.py` 的 `load_context` 与 `prepare_for_replay` AST 不变；新增 replay 分支属于私有评分。`swe_material_revisions.py` 的 DVC 修订操作保留 public，仅更新 grading 并重建 environment package；该 ingest 的公开题面改写仅针对指定 mypy/Moto 题，不包括这三题。`spec_vendor.py` 的新增分支用于安装／测试命令；`environment_overlay.py` 的新增 recipe 身份不改变这三题公开镜像。`envpack/bundles.py` 字节未变，SHA `f107d1a09979cc52890a1d5dbfb7697c6744179157041aa2bb6d1d0530d7c988`，其 `render_user_prompt` 未变。本次未导入或执行这些模块。

DevRunner → acceptance Runner → ClaudeCodeDriver 的既有继承结论继续适用。当前 helper 未变：v1 `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0`，v2 `f513232d19dae5c28e3a0ae8600cc9ad7cbab71aa0a7582f5abd9ceccaf7bd8d`。helper 通过配置选择 release repo／prepared／实际镜像，没有把 R5 release 名字写死到启动代码。复用历史事实不意味着可以重绑旧 prepared：新 environment/grading digest 应由新 prepared 独立记录。

## 三题公开输入、镜像与实际历史证据

R14 `public_bundles_v0.jsonl` 实读 SHA `f6f338ef3ba0f927d8957c37c5fdb781cce42cef023cd4a9d002edf52ca01e78`，`environment_packages_v0.jsonl` = `d7a965ee126a4c1728e9d8c463ecd4c07584b76fd6d11f0278e3589aa463abe1`。逐题 R14 public 与 R5 rollout_view.public 全字段相等（含原 issue 的 CRLF、题面 SHA、base、公开 image、manifest、工作目录、allowed tools）；独立 canonical JSON SHA 与 public digest 相同。

| 题目 | public digest（R5 = R14） | 原实际公开作业／测试结果 |
| --- | --- | --- |
| 6954 | `9186b41928accff7f5b576f240163c6c87c013cc9cfb219fa8a42571b3d526fb` | `dvc6954-public-actor-20261003-v1-003`；11 passed、46 warnings、4.05s |
| 4166 | `5d5da25d1dcc9203b201085f837abf65b4cc32adb0e61dff65fba48f20db1a4a` | `dvc4166-public-actor-20261003-v2-001`；29 passed、2 warnings、1.91s |
| 9395 | `1f95551f8b887dc01d5a2c2fba8aef01a449c701e1577dec4905181f14abafd9` | `dvc9395-public-actor-20261003-v1-001`；17 passed、24.69s |

三题当前 neutral brief 与旧成功作业归档字节相同。重新读取 `stub/requests/messages_000.json`，每题首个 user text 均逐字等于归档 prepared prompt + 两个换行 + neutral brief；不是只复信布尔标记。公开命令仅做身份、激活拒写、已有公开测试和依赖／CLI 检查；没有混入新增私有测试。四命令每题 rc0、harness rc0，完整 `captures/public_tests.out` 与表中摘要一致，未出现 skip／失败／收集错误。完整节点分母的旧非作者核查结论继续适用；本次没有重新采集节点。

R14 revision registry 实读 SHA `815811717d21fa259b354eaf85a1598241d66d85b5af547d9208b2835c4edace`。registry 中固定派生镜像 ID 与旧 attempt 和 image.json 一致：

| 题目 | 实际派生镜像 ID | 本机固定 wheel 数／校验 |
| --- | --- | --- |
| 6954 | `sha256:083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30` | 7／全匹配 |
| 4166 | `sha256:28ed5ef69d46c326ec183f8719e426611ca848046156fa98f9f6c7f35b46ebeb` | 5／全匹配，含 `networkx-2.3+rh2.1` |
| 9395 | `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60` | 7／全匹配 |

逐个读取 context/wheels 文件计算 SHA，结果等于 image.json.wheels 及 registry.installation.wheels；image.json.expected_wheels 是对应子集（4166 NetworkX 为额外固定 wheel）。三份 Dockerfile 实读同为 `10fd2f82a47d1eae9d8627486aeeb1e6d704f2c7bfa0441b418e68f2ed8511f1`，只离线安装固定 wheels，没有复制私有测试。基线 commit 分别为 `28dd39a1a0d710585ff21bf66199208b1b83cbde`、`520e01f11305aba1994df354adef86e6d90180de`、`c75a5583b3840ba90a8e800a0f42c1cb120916db`。这证明本地输入与旧运行身份对应，没有重新 inspect 或重建镜像。

原历史事实仍是 CC `2.1.205`、UID54321、`/testbed`、受保护激活脚本、固定 stub 的四 Bash 命令；共同 profile digest `a0d183d13a4a099cd0bd62d9e19fca7019428f7d08f5b69522a3ead4b565c68f`。已有实际 actor inspect 支持 2 CPU／4 GiB／PID512、非 privileged、swap0、无宿主 bind／额外 mounts，网络限于受控 relay。cleanup 原件均为容器 rm0、stub rc0、network／relay failures 空、按标签容器／网络与强制清理残留为空。不是新模型求解能力检验。

## 非阻断导航差异及原限制

请求中 4166 的 `input.json` 实读 `65ada6987d8818abb7632518c19bcb3b48d0224ff8288f5dd485f7ca2ad82501`，是遗留 v1 输入；成功 v2 attempt.input_sha256 对应同根的 `input_v2.json`，实读 `894bb5e2af530d979552d0244386cff5357df69d742515338cd9c81e15309be9`，helper 是 v2。前者不能代表成功作业的输入身份。它不推翻已核成功事实，但后续导航应指向实际 v2 输入。没有改写请求或记录。

4166 原镜像只允许精确初态 ` M setup.py\n` 与完整 binary diff SHA `8bd072b6e35dd358d920432c24b35048d4e51a9d0bc78972ceeb18e302b8dfbf`，属于原依赖镜像的 moto 元数据差异；不是候选改动，也没有泛化接受其它 dirty 树。旧 v1 自有 guard 在 CC／公开命令前失败的事实保留，不能算模型或题目失败。

原限制照常保留：`-q` 日志没有完整逐节点 verbose 输出；helper 的 pytest 解析为 null，成功计数必须读 raw capture，不能靠 helper 自动断言。基线 SHA guard／源码 pin 检查未另外保存完整 stdout，未归档容器中公开基线测试的完整字节快照。8 GiB writable quota 只是配置，不能当作 HostConfig 已落实的证明。仅使用固定 stub，不证明真实模型 probe、训练 actor 已接入或新 consumer 的正式 reward。

## 6954 新 prepared 的补充读回

父任务后续给出 `formal_evidence/dvc6954_r14_prepare_v1/` 六份产物，以及 `tasks/iterative__dvc-6954/public_actor_r14_applicability_v1.json`；后者实读 SHA `fc80962f1a1542556e773a4830503adcaf425a2992518f659d4815dc506ba09d`，仅作导航。独立比较新旧 rollout.public 全字段相等，public digest 相同；prompts.jsonl 的 prompt 内容逐字相同。新 environment digest 为 `c8cde31e2160b7caa94884d54e45a48f2527a744e2bb1ecb3789f502ebc6e311`，旧为 `fde8b5bf5c4609335704707df908f67cc2f180b130330e64439cebbf8c3d0147`，不能混用旧 prepared 身份。

| 新归档文件 | 实读 SHA256 |
| --- | --- |
| `prepared/rollout_task_views.jsonl` | `d9f8d6e34e7d234a2127cb98868958d879c97f7a94e723fa685c7b9e82fcee92` |
| `prepared/prompts.jsonl` | `120d534963bf25937dbefdd85c682450823463ab31691ad5e322bb847a2ed5b2` |
| `prepared/prepared_manifest.json` | `a1aa0200be589df82faafc91d008429521724d56a9f5ff8ab51926980dc51cde` |
| `prepared/replay_summary.json` | `a4862ec050024536e718c107fe69ad8613fa9e573427b8c182aa445b2fcfde11` |
| `private/host_grading_views.jsonl` | `3d5459fee235d462960d7e1042ff87e6e6f40de9cf2962e2fd315f7433bc2118` |
| `jobs/dvc6954-r14-prepare-20261003-002/completion.json` | `cdfb21b13d038b7083b15f74cb06b92c0d9da4f29e5ad1931af64e523c9831d1` |


prepared manifest 的两个公开文件 SHA/count=1、host SHA/count=1、task/public/environment 绑定均与实际文件一致；summary 的 manifest／host SHA 及 completion 的 summary SHA 引用也匹配。completion 记录 mode=prepare、process_exit_code=0、R14 release/manifest、v2 wrapper SHA `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`，命令指向该 R14 release 的官方 replay_grade.py prepare。本轮补充归档未含其输入文件、process.log 或完整 release 成员校验原件，故这里只确认公开产物和引用链，不扩写完整 prepare 来源或运行验收。

4166、9395 R14 新 prepared 仍待单独读回。R5 的三个实际公开开发核查事实可在相同公开输入与固定镜像条件下延用于 R14 诊断说明；这不证明 R14 新 actor 运行、正式私有评分矩阵、RH2 reward、模型 probe、环境／训练资格或训练消费已通过。

## 最少原件定位

历史 raw 根按固定请求的三条 `prior_actor_cases.raw_root`：每题对应 `attempts/<上述 job>/attempt.json`、`stub/requests/messages_000.json`、`captures/{identity,activation_permissions,public_tests,dependency_cli}.out`。本次抽查实读 SHA 如下：

| 题目 | attempt.json | 首请求 | public_tests.out |
| --- | --- | --- |
| 6954 | `42df02ea4ca20adad9ebc18e14a862025bcf3cf1c28e2911ae18af3fd89f47d4` | `89b9fe99079ba7b15f96a4efc10edb657076eb491e2aaa69844dc15ef8143d60` | `5aa6f55f2605bd00400f538b42ab886274ef5e2f8319d8d665701708fe674954` |
| 4166 | `8d7def502848dfe686097bceadd7c81c018a6f4f48fb5716ad6c10338215ff7d` | `a72378988ef12cd7335e1610b2f5305a498588ec01c8004c7aca09b6953fd3ef` | `6983f8a8d40fb3f74a45ae322a18daf487628fd6023fac773f0755dec5326072` |
| 9395 | `324b0ae2c3c32d213639e6290015bcfde7574d06156a9365aa11e1a330a5e453` | `46adeb7fb517230bf6b811348079c7e137eec621dbee8dcee0480daa331b7d47` | `825ec61de795e419e538f64318d80aea7113ee80f3c1d3b97e5bb75da9d65c8d` |
