# getmoto__moto-6114：history 解封前的独立私有初判

2026-09-21。仅静态审查与复读既有运行；未运行项目或新实验。暂定 disposition 为 **needs_review / static_review**，用途限 **development_diagnostic**。最值得先查的是“ARN 查询返回错误集群仍可得分”的具体漏测候选；当前不能据此宣称已证实 RH2 误收。

## 证据范围与身份

所有相对路径以权威根 . 为准：

- P = runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114；S = P/base。
- V = runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114。
- E = runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114。
- F = runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz 内的只读成员；没有解包或执行。
- B = docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/getmoto__moto-6114。

精确 base 为 f01709f9ba656e7cf4399bcd1a0a07fd134b0aec，tree 为 f879708cd000d0a6664095d52fae4b0295b693bd。P/public_bundle.json 与 V/grading.json 一致；P/base_identity.json 记录 blob、模式及路径集合已核验，唯一未物化 gitlink 为不涉及此测试的 Terraform provider。这里未重新逐 blob 核整个仓库。

已读并核 B/public_read.md 的 SHA256：20b97ef56a9417a75c53ce91023009da45a02abd6e824a9ba21dd20a2de5f912。私有 test.patch 全文与 grading.test_patch 一致（SHA256 32beadd88d5189dcab69b796980a93c464cb7b6f9d16bc8329d5da3e80571b61），gold.patch 全文与 validation.golden_patch 一致（bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc）。

本上下文已暴露于隐藏测试、gold、环境记录及 noop/gold 结果，因此“独立”只指未读旧调查，并非 result blind。V/environment_record.json 内附的 history 键仅列 install_wave1 运行来源，也已随授权环境原件看到；未打开本题 history 目录、历史调查引用或旧报告。未读其他题或其他角色结论（唯一允许的公开读者产物除外），未读批次 aggregate。inventory 只选择 common 和精确 getmoto__moto-6114 entry；common 的 archive 信息已用于定位，没有跟随其他批次报告。未读 V/source_refs.json。

## 公开要求、初态与调用链

公开核心是：给 describe_db_clusters 的 DBClusterIdentifier 传**已存在集群的完整 ARN**，应返回该集群；名称路径继续可用。题面“ClusterArn Filter”是对参数用途的描述，不是新增 ClusterArn 参数或要求实现通用 Filters。P/user_prompt.txt:10、17 创建/查询 test-cluster-1，但 :24 失败例写 test-cluster-0；这是可消除的示例笔误，不能用后者单独证明缺陷。用创建响应的 DBClusterArn 复现可避免笔误与硬编码账户。

静态路径为：S/moto/rds/urls.py:1–5 → RDSResponse（responses.py:19–32、584–588）→ 当前账户/区域的 RDSBackend.describe_db_clusters（models.py:1951–1958）→ Cluster.to_xml → DESCRIBE_CLUSTERS_TEMPLATE（responses.py:1093–1107）。创建以短名称入 OrderedDict（models.py:1873–1880）；ARN 是独立属性（:121–123）。base 查询只用字典键，正常完整 ARN 不能命中。

这不仅是 gold 差异推测：既有 noop 原日志 E/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log:533–569 展示两个集群创建、名称查询通过后，真正执行 ARN 查询；:654 报 DBClusterNotFoundFault，消息含完整的 cluster-id2 ARN。初态故障落在题意路径，未停在依赖或收集阶段。

F2P 为 tests/test_rds/test_rds_clusters.py::test_describe_db_cluster_after_creation（下称 T）。已完整读 S/tests/test_rds/test_rds_clusters.py 的 35 个函数（1–809）和全部 test.patch。静态 AST 名称核对显示：T + grading.json 的 34 个 P2P 恰好等于该文件全部 35 个测试函数，没有用“同文件测试数”代替阅读。

fixture/helper：T 无 pytest fixture 参数；@mock_rds 经 S/moto/__init__.py:6–15、124，moto/rds/__init__.py:1–5，core/models.py:81–115、118–131 启停 mock 并重置 backend。tests/__init__.py 导入 helpers.py；其 3 个自定义 sure assertion 全读，T 没有调用它们。T 使用 sure 的普通 length_of。默认非 server 模式是进程内 HTTP 拦截（core/models.py:285–310、408–422；settings.py:9），不需要真实 AWS/RDS。公共树只有 tests/test_dynamodb/conftest.py，不在此测试的祖先目录；没有额外 RDS conftest 被遗漏。

## 公开要求 → 断言，以及断言 → 公开依据

测试 ID 以下均省略共同前缀 tests/test_rds/test_rds_clusters.py::。

| 公开要求或合理旧行为 | 公开依据 | 验收测试及决定性断言 | 覆盖判断 / 证据 |
| --- | --- | --- | --- |
| 已存在完整 ARN 定位同一个集群 | P/user_prompt.txt:4、15–17、26–30；S/models.py:121–123、1873–1880 | T 在 eu-north-1 创建 cluster-id1、cluster-id2；新增从第二次创建响应取 DBClusterArn；ARN describe 只断言 DBClusters 长度 1（V/test.patch:8–25） | **部分**。确有业务调用；不核 Identifier、ARN 或与按名称结果相同。既有 noop 在该调用失败，gold 通过。 |
| 名称查询仍可用 | 题面 :16、21；S/test_rds_clusters.py:262–264 | T 的旧断言，查询 cluster-id2 长度 1；test_restore_db_cluster_from_snapshot:678–680 查询 db-restore-1 长度 1 | **部分**：存在性有保护，目标身份仍未被这两项断言核实。 |
| 不带参数返回全部；空环境为空 | 题面 :15；S/models.py:1958 | T 长度 2；test_describe_db_cluster_initial 长度 0；delete、restore 的 0/1/2 长度变化 | **覆盖已测场景**；没有完整集合身份或混合 RDS/Neptune 断言。 |
| 不存在短名称仍报原错误 | S/test_rds_clusters.py:18–28；S/exceptions.py:118–122 | test_describe_db_cluster_fails_for_non_existent_cluster，核 DBClusterNotFoundFault 和 DBCluster cluster-id not found. | **覆盖短名称**。精确字符串是已有公开测试要求，不是隐藏新增的任意格式。 |
| 不存在 ARN 不应被任意已有集群替代 | 公开“if it exists”与按标识符查询语义；未另定 ARN 错误文案 | 没有不存在 ARN 的调用；短名称 not-found P2P 不进入 ARN 分支 | **缺失**；错误类型沿用是合理回归方向，精确 ARN 文案未经公开规定。 |
| 返回对象保留原字段与状态 | S/responses.py:1093–1098；公开创建属性测试 | test_create_db_cluster__verify_default_properties 核创建响应字段与 ARN；start/stop P2P 核无参 describe 的状态 | **部分**；创建响应正确不证明 ARN describe 返回同一对象。不能把创建时 Status=creating 与随后 describe 的 Status=available 直接相等作为新要求。 |
| RDS 入口继续可见同账户/区域 Neptune 集群；同名时先 RDS | S/models.py:1348–1350、1953–1958；responses.py:15–32 | 本 34 P2P 不含 Neptune。额外阅读 S/tests/test_neptune/test_clusters.py:12–80，保护列表/区域/删除行为 | **评分缺失，公开窄回归可用**。mock_neptune 实际也加载 .rds/mock_rds（moto/__init__.py:116），故共用入口值得保留。 |
| 创建校验、修改、删除、启停、快照、恢复、标签、HTTP endpoint 原行为 | 全读公开测试文件；相关现有模型调用 | 34 P2P 包含密码/用户名验证、默认字段、改名、删除及快照保护、启停状态/未知资源、快照复制/查询/删除/恢复、标签和 EnableHttpEndpoint | **覆盖既有断言范围**，两角色均 34P。gold 不改这些方法；未穷举全仓或所有相邻 API。 |

反向检查所有**新增验收约束**只有：从真实创建响应取得 ARN，调用同一 API，返回 1 个结果。它们均有公开需求依据；未要求 split、内部函数名、Mock 调用形状或实现顺序。eu-north-1 和 aurora 是正常公开 API 用法，不因题面示例是 us-east-1/aurora-mysql 就构成额外隐藏规格。T 没有核题面原 engine 组合；本次 gold 只归一化 identifier，未触及 engine 分支，仍需实际 actor 运行公开原例确认。

## 合理替代解、gold 与具体疑点

**合理替代路线（未执行）**：保留原无参列表、短名称查找及 RDS→Neptune 优先级；在已有对象中比较输入与 db_cluster_arn，返回匹配对象；没有匹配则沿用 DBClusterNotFoundError。也可只对受识别的 ARN 解出名称，再保留原字典查询。正常有效 ARN 域内不必采取 gold 的 split 实现。现有隐藏断言没有明显误拒这两条路线；这不是所有合法解均接受的证明，检查 24 仍不得伪 pass。

gold 仅在 S/models.py:1952 后新增 cluster_identifier.split(":")[-1]，返回与序列化路径原样保留，无新依赖或未交付文件。正常完整 ARN 会落到正确的名称键；普通短名称无冒号则不变。既有 RH2 为它给出全部 35P，支持其已测场景正确。

- **Q1，确定的静态覆盖缺口，误收待实验**：T 请求第二个集群却仅核 length=1。如果实现保留所有旧分支，仅在“输入以 arn: 开头且 self.clusters 非空”时返回第一个 RDS 集群，就会给该请求返回 cluster-id1，明显违反“按 ARN 找到目标”，同时静态上满足 T 新增断言；完整 34 P2P 没有 ARN describe 调用来否定它。这不是依赖测试名或常量的硬编码。需要真实 CPU 重放后才能写“已证明 RH2 接受错误解”。
- **Q2，未测兼容范围**：RDSBackend 合并 Neptune 集群的行为没有计入本题 P2P。重写过滤集合时可能丢失这条旧路径，gold 的增量改法没有删除该路径。额外 Neptune 测试虽公开存在，未参与这里的真实 35 项评分，不能写成已过。
- **Q3，gold 边界歧义**：无条件 split 会使 wrong-prefix:cluster-id2、不同 ARN 前缀或资源类型但相同末段落到本地同名对象，也把不存在 ARN 的错误消息改为只含末段。源码足以推导行为变化；目前读到的公开本地材料没有给出这些 ARN 的合法输入域、精确拒绝策略或错误消息契约。不以“跨账户/区域必须怎样”自造 AWS 标准，不据此定 gold 错误或要求改题。后续若要增边界断言，先找可公开给 solver 的规范依据。
- **Q4，题面小歧义与输入待验**：test-cluster-0 笔误可修正为使用创建响应；真实 CLI 消息尚未捕获，public_hints 是否进入 system message、环境激活声明是否成立不能从静态模板推出。

## 既有 RH2 环境原件与 actor 缺口

已核 V/run_refs.json 引用的原件：

| 角色 | 原件与行 | 直接看到的事实 |
| --- | --- | --- |
| noop | E/noop/ledger.jsonl:1；evallog_replay-er19-iw1-getmoto__793414a1.eval.log:496–526、533–656、677–719 | editable 安装成功；pytest -n0 -rA tests/test_rds/test_rds_clusters.py 收集 35 项；T 因完整 ARN not-found 失败，34 P2P 通过；测试退出 1，reward 0，参考缺席 0。 |
| gold | E/gold/ledger.jsonl:1；evallog_replay-er19-iw1-getmoto__356bbc61.eval.log:183–199、368–425、515–611 | gold diff 可见，官方测试恢复并 clean apply；make init 的两段 editable 安装完成；35P，测试退出 0，reward 1，参考缺席 0。 |
| 环境身份 | E/image.json:2–11；两份 ledger:1；E/status.json:3–22 | install-wave1 派生镜像 sha256:b473823508458d059713620738c06954d661e3b7b51d43cb8e126e630f57231c；原 digest 与公共 bundle cb35f7e… 匹配；仅添加离线 wheel 与 PIP_NO_INDEX/PIP_FIND_LINKS；脚本摘要 d98d9e14…；grader 为 rh2grader/54322，deny_all、2 CPU/4 GiB。candidate apply_user=agent/54321 仅证明注入身份，不是模型开发流程。 |
| 导入/投影/清理 | 两份 ledger:1 | 评分导入 /testbed/moto/__init__.py；gold projection 仅含 moto/rds/models.py，ignored_paths=[]；两角色 cleanup.removed=true、stage_error=null、runner_integrity_changed=false。 |

原日志 SHA256 分别为 noop c6d13397fa775c2244a4f622436f23a394c920dd06c5b44260c8f9d8ced12e7c、gold 6f3ea7a472101fa9edd0655740f14f6a877c307f2e5e74e4dd7b2acfe11a43c4；ledger SHA256 为 noop d14eb80ea9a7d1e958734c240d8dbaf31cfd5e7706c95e838858e2cbbeb5137c、gold 84820dc41610cbcf5e868dc56013f1efdba74ad64992fbf93b48a77dbdd7dc74。均与 V/run_refs.json 相符。独立按日志 PASSED/FAILED 行核 35 个参考 ID，无缺席；失败 traceback 又提供测试体执行证据，未只凭 parser 状态。

静态读 install_wave1/run_install_wave1.py:24–65、73–81：准备阶段下载 wheel，派生镜像 COPY 资产；之后按原 spec 做 noop/gold，未覆盖 recipe/materials/bindings。E/image.json pins 为 setuptools 72.1.0、wheel 0.43.0、packaging 24.1。inventory 本题 entry 明记当前权威机缺原 assets/contexts/getmoto__moto-6114；目标派生镜像是否存在也未核。这是未来重放准备缺项，不能将审计 JSON 当作实际 payload。

| 开发需要 | 公开/源码依据 | 已有证据范围与缺口 | 未来最小验证（本轮未执行） |
| --- | --- | --- | --- |
| 定位问题并编辑可提交源码 | responses.py:584–588、models.py:1951–1958 | 公开入口充分；gold 同路径投影有效。实际 actor 可写性和 Git 体验未验 | actor 身份核 cwd、HEAD、UID/HOME、moto/rds/models.py 可写及差异收集。 |
| 本地 Python/Moto、boto3、sure/pytest 与传递依赖 | setup.cfg:26–38；requirements-tests.txt；models.py:10–14 导入 EC2/Neptune | grader Python 3.12.4、pytest 8.3.2，导入工作区；不能代填 actor | 实际工具 shell 打印 sys.executable、moto.__file__；导入 boto3、moto.rds.models、sure 后运行公开复现。 |
| 依赖准备及可写安装环境 | pyproject.toml:1–3；Makefile:17–19；requirements-dev.txt | grader 以可写 conda 前缀完成 make init；actor 的前缀权限、激活和离线 wheel 可达性未知 | 若已有 editable 导入不必重装；确需安装时先核离线 wheels、setuptools 与权限，再做受限 editable 安装。 |
| 业务与公开测试执行 | mock_rds 调用链及 T；同文件旧 describe 测试 | 默认 mock 不要求真实 AWS、数据库服务、GPU；本题没有必要外部业务附件；整体镜像资产未验 | 实际 actor 跑 public_read.md 的同集群按名称/ARN 对照；再跑公开 describe 子集。 |
| 服务、资源与网络 | settings.py:9 默认非 server；公开 environment_brief | 准备 wheel 可由准备方联网固定，mock 解题/测试无需公网；grader 小资源成功只是其条件 | 核实际 TEST_SERVER_MODE、进程环境及资源；不把 grader 配置当 actor 配置。 |

F/prepared_task_face.py:336–349 的正式 rollout 仍取 public.image/digest；F/replay_grade.py:304–309 则在重放时显式选 derived_image。两条路径不同，不能声称修复配方已被真实 actor 消费。共用环境卡关于激活、模型代理、权限、正式工具入口的未知项仍保留。检查 3（真实 solver rendered 消息）与 29（真实 actor 资产/答案暴露）为 unknown；没有本题真实模型成功率、token 或费用观测，costs 应为 null。

## 交付边界、关系和用途

V/test.patch 只改 tests/test_rds/test_rds_clusters.py，未混入普通业务源码。F/prepared_task_face.py:179–228、298–330 与 gold 日志 :191–199 表明此官方文件会恢复并应用原测试补丁；test_globs=()，不是把所有测试文件统一排除。合法修复可只改 moto/rds/models.py，也可改未受该恢复影响的响应层；本题没有必须修改但无法提交的文件证据。保持 additional_exclusions=[]。未对一般评分攻击面或所有控制文件做新审计。

公开包未导出 .git/未来对象，但真实 actor 镜像文件、预装包、可见祖先历史是否含答案未验；不能给泄漏检查 pass。未调查跨题关系，未据相同文件或补丁形状推断重复题。修复属于可解释的小型 API 参数兼容任务，公开材料足以定位，不以静态阅读猜能力区分度或训练价值。

## 八方面收口与唯一优先下一实验

1. 公开要求：已对照 issue、公开旧测试与源码；笔误可定位；真实消息未知。
2. 材料/初态：base、patch、参考集一致；既有真实 noop 失败位置支持原 bug。
3. 测试：完整展开唯一 F2P 与 34 P2P；明确长度断言漏掉目标身份、无不存在 ARN。
4. 合理解：对象完整 ARN 匹配路线可行，未发现特定实现约束；替代解尚未运行。
5. gold/回归：正常域增量修复有真实 35P；Neptune 评分缺口与 ARN 非标准边界保留。
6. 开发条件：已核修复配方与 grader 原件；实际 actor 环境、资产、消息仍未知。
7. 交付/评分：本题恢复路径与源码投影已定位；不新增文件排除或扩展安全结论。
8. 关系/用途：未查跨题或真实模型；审查暴露产物只供开发诊断，不能喂给 solver。

**唯一优先下一步：一次目标身份 CPU 对照。** 在准备好并核身份的本题重放环境中，分别用 gold 作正对照，以及 Q1“任何 ARN 返回首个集群、保留其他路径”的候选，跑原 35 项 RH2 评分；同时以两个不同集群的创建响应 ARN 进行独立语义复现，断言返回 DBClusterIdentifier 与 DBClusterArn 对应请求对象（可对照同一对象的 describe-by-name，避免拿 creating 的创建响应与 available 的查询响应全量比较）。如果错误候选 reward=1 但身份检查失败，即把当前静态漏测疑点升级为真实误收证据。该探针不依赖异常 ARN 的 AWS 边界规范。完整属性匹配的合理替代解可复用同一语义检查，现阶段没有结果。

此实验及任何断言修订均**尚未执行**；不把建议反例当独立 solver 成功，不改原题/评分。封存本稿后等待协调者显式解封 history，再另写 delta、card、record；不回写 public_read.md 或本稿。
