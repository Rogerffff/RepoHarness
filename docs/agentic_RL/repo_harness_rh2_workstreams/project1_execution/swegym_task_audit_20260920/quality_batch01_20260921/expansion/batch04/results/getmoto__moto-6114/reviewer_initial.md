# getmoto__moto-6114 — 独立 reviewer 初判（封存稿）

2026-09-21；角色：B4 fresh reviewer，非主审。建议 `needs_review / static_review`，用途 `development_diagnostic`。核心问题可定位，gold 与普通成功路径一致；验收只查 ARN 查询结果数量，未查对象身份，存在有具体反例设计的漏测。尚未执行反例或真实 actor，不能据此宣称题目已准入或已经实证错误计分。

**阅读与暴露边界。** 权威根为 `${REPO_ROOT}`。未读本题 public_read、主审 analysis/card/record/delta、review/history/refs、root 聚合或其他题原件。读取公开题面与 base 后读取全部 test.patch、gold.patch、F2P/P2P 清单；也读取了获准的本题环境记录和既有 gold/noop 结果，因此是“独立于既有质量结论”的初判，**并非 result blind**。只用标准库读取/解析文本、AST、JSON 与归档成员；没有项目 import、pytest、安装、网络、Docker、SSH、GPU、模型调用，未修改题目、源码、测试或评分。

本稿内路径缩写：

- `P = runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114`；`S = P/base`。
- `V = runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114`。
- `E = runs/env_recipe_repair_20260919/install_wave1`；`L = E/tasks/getmoto__moto-6114`。
- `G = L/gold/eval_logs/evallog_replay-er19-iw1-getmoto__356bbc61.eval.log`；`N = L/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log`。
- `F = runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`，只经 `tarfile.extractfile` 读取相关入口，未解包执行。

**1. 公开需求与可解范围（3、23）。**

`P/user_prompt.txt` 要求 `describe_db_clusters(DBClusterIdentifier=...)` 同时支持集群标识符及该已存在集群的 ARN。这里“Filter”是自然语言称呼；复现实际传入 `DBClusterIdentifier`，没有要求新增 `Filters` 参数实现。正确返回应是 ARN 所指集群，不能只返回任意一条。保留不传参数时列举全部、普通标识符定位、未知普通标识符报错，均有公开旧代码/测试依据。

正文完整示例创建并查询 `test-cluster-1`；后面孤立失败行写成 `test-cluster-0`，与创建对象不一致。将其认作例子笔误有充分上下文依据；不把“未创建 test-cluster-0 也须返回数据”引入标准。公开材料足以定位普通需求，题意本身不因这处笔误判无效。题面不规定内部 helper、解析算法、错误 ARN 的精确消息或跨账号/跨区域 ARN 语义。`user_prompt.txt` 是静态渲染材料，真实 solver rendered 消息和 public_hints 是否进入 CLI system message 未核验（check 3 unknown）。

**2. 材料、初始故障与版本（1、2、27）。**

公开及私有 bundle 均指向 base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。`base_identity.json` 记录精确 tree、blob 校验和未导出 Git 元数据；本轮未重新计算整个 Git tree。通过标准库比较确认 `V/test.patch == grading.json.test_patch`、`V/gold.patch == validation.json.golden_patch`。gold ledger 的 patch SHA 为 `bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc`，与 validation 一致。

调用链为 `S/moto/rds/responses.py:584–588` 取原样 DBClusterIdentifier → `S/moto/rds/models.py:1951–1958` 直接查以短 ID 为键的 RDS/Neptune 字典。创建存储见 models.py:1873–1879；ARN 属性见 :122–123。这解释了已存在 ARN 查询失败。它不只是 gold 差异推断：`N:544–569,654` 显示实际传入创建返回的 `arn:aws:rds:eu-north-1:123456789012:cluster:cluster-id2`，在新增 ARN 调用抛出 DBClusterNotFoundFault；`N:711–716` 为 F2P 失败和退出 1。

**3. 需求—断言双向映射（18–20、25、32）。**

唯一 F2P 为 `tests/test_rds/test_rds_clusters.py::test_describe_db_cluster_after_creation`。完整 test.patch 共 29 行，仅改这一旧测试：取得第二个集群的返回 ARN，再做一次长度断言（`V/test.patch:9–15,23–25`）。没有新 fixture 或 helper。旧测试使用 boto3、sure、`@mock_rds`；mock 入口 `S/moto/rds/__init__.py:5`，通用 mock 生命周期见 `S/moto/core/models.py:35–141`，包括假凭证、backend reset 与调用包裹。

| 公开要求/合理回归 | 公开依据 | 对应测试及决定性断言 | 判断/证据 |
| --- | --- | --- | --- |
| 已存在集群 ARN 可查询 | issue；models.py:122–123 的 ARN 属性 | 唯一 F2P，创建 cluster-id1/2，用第二个 ARN 查询，断言长度 1 | **部分覆盖**：确实通过公开 API 走业务调用；N 在此失败，G:579 通过。但未核对象身份和数据。 |
| 返回 ARN 所指集群 | issue 的 lookup 语义；短 ID 字典定位的旧行为 | 同一 F2P 只查长度，没有 DBClusterIdentifier/DBClusterArn 或字段等价断言 | **缺失**：查询第二个 ARN 却返回第一个对象也满足新增断言。 |
| 短 ID 查询仍能工作；不传 ID 列举全部 | 旧测试 :242–264；models.py:1951–1958 | 同一 F2P 的 ID 查询长度 1、无参长度 2；P2P initial 的空列表 | 覆盖数量/基本分支；短 ID 身份断言同样弱，不把旧薄弱处全算本次新增缺陷。 |
| 普通未知 ID 报错 | 旧测试 :18–28；exceptions.py:118–122 | P2P `test_describe_db_cluster_fails_for_non_existent_cluster` 精确断言 Code/Message | 已覆盖；精确消息源于公开旧契约，不构成已发现误拒。 |
| 删除、改名、启停、恢复后正常查询 | 旧测试 :101–126、268–300、344–357、379–396、645–712 | 相应 P2P 检查旧 ID 不在全量列表、删除为空、状态、恢复后全量/按 ID 数量 | 保护若干旧分支；没有恢复/改名后的 ARN 查询。 |
| 不存在 ARN；ARN 变化后的查询 | issue 的存在条件与已有错误处理；ARN 随 ID 计算 | 本题参考集合无相应 ARN 负例/变更例 | 覆盖限度。尤其错误 ARN 的完整消息未由公开材料规定，不自建精确消息要求。 |
| 题面 us-east-1 / aurora-mysql 原例 | issue 完整示例 | F2P 使用 eu-north-1 / aurora | 路径未按 region/engine 分支，静态上具代表性；不是原例逐字运行证据。 |
| RDS 查询中已有 Neptune fallback | models.py:1955–1958；:1349–1350 | 本题 34 P2P 均在 RDS clusters 单文件，不含 Neptune 文件 | 合理保留旧分支；未证明相关服务回归已全测。 |

34 个 P2P ID 全部读取，并与两个原始日志的逐项 PASSED/FAILED 行对照：gold 1/1 F2P + 34/34 P2P；noop 0/1 + 34/34。实际断言精读范围为 RDS clusters.py:1–434 与 :640–745，重点完整读取所有 `describe_db_clusters` 调用所在测试；AST 仅用于核对该调用清单，未运行项目。其余快照/HTTP endpoint 测试只核参考 ID 和日志结果，不冒称逐断言审查。另读 Neptune clusters.py:1–95 与 backend describe :309–318，确认相关旧行为，未将其当作实际评分 P2P。

**4. 漏测与合理替代解（24、28）。**

具体错误解设计：只在字符串以 `arn:` 开头且 RDS 字典非空时返回 `list(self.clusters.values())[:1]`，其他输入完全沿用 base。现有新增用例有两个对象，请求第二个 ARN；错误解返回第一个却仍满足长度 1。34 P2P 的 describe 调用没有 ARN 输入，因而静态预计全部维持原行为。这是可区分的错误计分假说，**尚未制作补丁、执行或证实 RH2 reward=1**；现有日志只证明 noop/gold 对照。

与 gold 不同的合理路线是保留原短 ID 查询，在 ARN 输入时匹配已存对象的 `db_cluster_arn`，然后返回匹配对象并保留原有无参/Neptune 分支；也可在 response 层对已确认的正常集群 ARN 做正规化。测试只观察公共 API，没有约束 split、helper 名、内部 Mock 调用形状或执行顺序。未发现会拒绝上述正常范围替代解的断言，但没执行替代解，也没穷举所有合法解；check 24 不记全称 pass。

**5. gold 与回归（26、27）。**

gold 仅在非空输入查表前增加 `cluster_identifier.split(":")[-1]`（`V/gold.patch:10`）。对本题正常 ARN 与普通短 ID，可定位同一存储对象；无参路径不变。按源码能修复 issue 中一致的 test-cluster-1 例子，也保留普通未知 ID 的既有错误格式。没有发现依赖未交付文件或混入其他需求。

该实现会丢弃 ARN 前缀，畸形前缀、账号/region 不符但末段同名的输入也可能命中本地对象；未知 ARN 的错误消息会显示剥离后的 ID。它们是可观察到的实现行为，**本地公开材料不足以确定全部 AWS 边界契约，不能据此直接判 gold 错误或拟定隐藏要求**。已读的 Neptune 跨区域旧测试只证明不同 client 的普通列表隔离，不证明“给本区域 client 传跨区 ARN”应采用哪一种行为。实际 gold 35 passed 也不证明这些边界正确。

**6. 开发条件与环境证据（6–15）。**

读取 `batch04/environment_replay_inventory.json` 时只输出 common 和本题精确 entry。随后定位本题 image.json、两个 ledger 第 1 行及原 eval log，核得 SHA 与 `V/run_refs.json` 完全一致：G `6f3ea7a472101fa9edd0655740f14f6a877c307f2e5e74e4dd7b2acfe11a43c4`，N `c6d13397fa775c2244a4f622436f23a394c920dd06c5b44260c8f9d8ced12e7c`；gold/noop ledger 分别 `84820dc41610cbcf5e868dc56013f1efdba74ad64992fbf93b48a77dbdd7dc74`、`d14eb80ea9a7d1e958734c240d8dbaf31cfd5e7706c95e838858e2cbbeb5137c`。

既有运行是 install-wave1 派生镜像 `sha256:b473823508458d059713620738c06954d661e3b7b51d43cb8e126e630f57231c`；仅 COPY 离线 wheel 并设置 PIP_NO_INDEX/PIP_FIND_LINKS，pins 为 setuptools 72.1.0、wheel 0.43.0、packaging 24.1。脚本 `E/run_install_wave1.py:54–61` 消费指定 derived-image 和原准备 summary，没有本题 recipe/materials/bindings override。`G:368` 实际 make init；:539 运行 `pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，:541 Python 3.12.4，:604–608 为 35 passed / rc=0。官方命令派生也由 F 内 spec_vendor.py:164–197 支持。

运行身份为 **rh2grader/54322**、2 CPU、4 GiB、deny_all、解释器前缀可写；candidate apply 为 agent/54321，并不等于真实 actor shell 开发验证。两个 ledger cleanup.removed=true、reference_missing_count=0、runner_integrity_changed=false。只引用历史评分事实，本轮未重跑；目标机镜像和离线构建 payload 可用性尚未确认。

| 开发需要 | 公开依据/现有证据 | 当前缺口与最小验证路径（未执行） |
| --- | --- | --- |
| 正确 Python、工作区导入、boto3/botocore 与 mock 依赖 | setup.cfg:28–40；RDS tests imports；G:375–386 的安装记录 | actor 实际 shell 打印 `sys.executable`、`moto.__file__`，确认编辑的工作区生效；不能将 grader 的可写前缀代入 actor。 |
| pytest、sure/surer、xdist 与开发安装 | requirements-tests.txt；Makefile:17–19；公开 installation.rst 的单服务测试说明 | actor 先跑公开现有单文件测试，再跑 issue 的 ARN 复现；原 base 公开测试可通过但新增复现应失败。依赖准备需固定离线资产；不要求 solver 临时联网。 |
| 本地 mock 与数据 | mock_rds/core mock 假凭证和 reset；正常非 ServerMode 单测 | 本题窄验证没有真实 AWS 服务、外部数据集、编译或 GPU 需求证据；Docker/terraform 是其他工作流说明，不作为本题必要条件。 |
| 可提交源码和观察新行为 | backend/response Python 源码；gold projection 包含 models.py | 常规修复不要求改测试、系统资产或生成文件。实际 tool/权限/环境仍须 actor 验证；本地静态包没有 .git，不能推定真实提交体验。 |

**7. 交付、评分与可见资产（4、16–17、21–22、29–31）。**

test.patch 只触碰 `tests/test_rds/test_rds_clusters.py`，没有混入普通业务源码。`G:191–199` 记录将该官方测试恢复到本题 base 后注入 test.patch；gold ledger projection.included_paths 只有 `moto/rds/models.py`，ignored_paths=[]。本题可在普通源码内完成，无已见投影阻塞。`P/public_bundle.json` 的禁止改测试提示不妨碍这一修复，但其“所有测试修改永不计分”的泛化解释不作为已验机制；此处只确认实际恢复的这一文件。

本题断言不依赖新私有 helper/config；已查范围未发现必须修改受保护文件才能修复的冲突。没有重做共享 parser/隔离安全审计。check 29 的真实 actor 镜像资产、未跟踪文件、历史/答案泄漏检查仍 unknown；“静态公开包无 .git”不能当作真实环境无泄漏的证明。

**8. 题目关系与使用建议（5、29–30、37–40）。**

这是范围很小的参数形式兼容修复；题面直接指出受影响参数，但没有给 gold 的 split 算法。未读取其他题、未来历史或旧报告，跨题同源/派生/答案关系未查，不给去重或模型记忆结论。reviewer 已见 gold、隐藏测试和历史评分结果，产物不可作为独立 solver 的公开输入。33–36 的真实模型交互、成功率和成本未查。

原 40 checks 语义保留：3=真实 rendered 消息 unknown；23=核心题意可明确，局部笔误已说明；24=合理替代解静态可行但普遍接受性未证；29=真实 actor 资产/泄漏 unknown。覆盖缺口归入 18–20/25，gold 已知正常范围修复与未定边界分开，不能用环境配对通过把题目质量标成 pass。

**唯一优先下一步。** 在另获 CPU 执行授权并具备可达评分环境后，只做上述“ARN 返回第一个集群”错误候选的定点校准：使用同一双集群输入，独立公开行为断言核对返回 `DBClusterIdentifier`/`DBClusterArn` 必须等于所请求的第二个集群，同时保留原 RH2 评分；gold 作已有正确路径对照。若错误候选公开行为失败而原评分通过，即实证当前最具体的漏测，再讨论加强对象身份断言。不要先围绕尚无本地契约的 AWS ARN 边界扩张题意。actor 消息/环境与资产未知仍单独保留，不能由该校准消除。

本稿保存后封存；只向协调者发送路径和 SHA，等待显式解封后才读主审/公开读稿/本题 history 并另写 review.md。
