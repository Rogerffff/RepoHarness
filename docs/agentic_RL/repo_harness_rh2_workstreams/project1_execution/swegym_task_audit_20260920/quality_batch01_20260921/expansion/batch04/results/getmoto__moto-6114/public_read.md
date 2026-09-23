# getmoto__moto-6114 公开审读

依据仅为共享公开读者角色卡及本题公开包。本文相对引用以 `runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/` 为根；权威工作区为 `.`。未运行项目、导入项目或执行测试。

## 需求与应保留行为

| 要求 | 证据与确定程度 |
| --- | --- |
| `describe_db_clusters(DBClusterIdentifier=完整集群ARN)` 应找到已存在的 RDS 集群，与按短名称查询指向同一资源。 | **明示**：`user_prompt.txt:3-17,26-30`。参数实际叫 `DBClusterIdentifier`；题面称“ClusterArn Filter”并不是要求新增名为 `ClusterArn` 的参数。 |
| 短名称查询继续成功；未指定标识符时返回全部集群，初始空环境返回空 `DBClusters`。 | **明示及既有约定**：`user_prompt.txt:15-16,20-21`；`base/tests/test_rds/test_rds_clusters.py:10-28,242-264`。 |
| 维持 `DBClusters` 列表及原集群字段、生成的 `DBClusterArn`，不因 ARN 查询重新创建或改变资源。 | **由接口合理推知**：`base/moto/rds/responses.py:584-588,1093-1107`；`base/moto/rds/models.py:121-123`；`base/tests/test_rds/test_rds_clusters.py:141-180`。名称和 ARN 应查询同一后端对象的正常序列化结果。 |
| 不存在的短名称仍抛 `DBClusterNotFoundFault`，消息为 `DBCluster <输入> not found.`。 | **公开测试明确**：`base/tests/test_rds/test_rds_clusters.py:18-28`；异常构造见 `base/moto/rds/exceptions.py:118-122`。不存在的 ARN 沿用该错误类型是合理推知，题面没有另定错误格式。 |
| 保留 RDS 入口可返回 Neptune 集群的旧行为及当前账户、区域隔离。 | **源码约定**：`base/moto/rds/models.py:1348-1350,1951-1958`；`base/moto/rds/responses.py:15-32`。无参数查询目前先列 RDS 再列 Neptune；同短名称查询优先 RDS。不要在重构合并集合时意外丢失这些行为。 |
| 通用 `Filters=[...]`、分页、大小写归一化、跨账户/跨区域 ARN、异常 ARN 校验及其他集群操作的 ARN 支持。 | **未充分约定**：题面所有有效调用均使用 `DBClusterIdentifier`，RDS 响应函数只读取该参数（`base/moto/rds/responses.py:584-588`）。Neptune 后端明确注明尚未实现分页与 Filters（`base/moto/neptune/models.py:309-317`）。不能把这些功能都作为本题明示验收条件。 |

## 初态线索、调用者和合理实现范围

公开材料足以给出调查入口。RDS 响应层把输入原样交给后端（`base/moto/rds/responses.py:584-588`），创建时以短名称为字典键（`base/moto/rds/models.py:1873-1880`），查询只做字典键判断（同文件 `1951-1958`），而完整 ARN 是另一属性（同文件 `121-123`）。因此静态代码能解释正常完整 ARN 为什么进入 not-found 分支；这不是已执行的复现。

合理解法至少包括：在后端保留名称路径并按对象 `db_cluster_arn` 查找；将查找抽为共享辅助函数；或将受支持、经过合理识别的 ARN 转换为标识符后查询。在题面正常输入域内，它们都可能满足需求，不应限定新增函数名、特定循环或唯一补丁结构。相邻实例及快照过滤代码已经允许把名称、ARN 都作为匹配属性（`base/moto/rds/models.py:300-304,371-374,1442-1452`），可作为设计参考，但不要求把完整过滤框架引入本题。

完整属性匹配与简单截取 ARN 最后部分在错误账户、区域、资源类型时会产生不同结果。公开内容不足以证明这些边界的全部 AWS 行为；应明确记录边界，不把任意含冒号的字符串都当作已授权的集群别名。至少保持既有后端隔离，不凭题面样例硬编码账户或区域。Neptune 的 ARN 属性格式与 RDS 相同（`base/moto/neptune/models.py:109-111`）；保留其原有名称与列表行为是必要兼容点，是否扩展其所有独立入口的 ARN 能力则不是题面明示目标。

直接调用路径的关键词检索发现 RDS 响应层和公开 RDS 测试；另有独立的 Neptune 响应/后端及测试。Neptune 公开测试覆盖空列表、创建后查询、删除后为空和区域隔离（`base/tests/test_neptune/test_clusters.py:12-34,60-80`），适合作为涉及共用路径时的窄回归检查。无需因此扩大到全仓测试。

两处材料问题需要区分：

- `user_prompt.txt:10,17` 创建并查询 `test-cluster-1`，但 `:24` 的失败示例写 `test-cluster-0`；后者单独运行本来就应查不到。使用创建响应里的 `DBClusterArn` 可消除笔误及硬编码账户的干扰，不妨碍定位缺陷。
- 题面片段未包含 import 或函数调用；公开测试已提供 `boto3`、`mock_rds` 的用法（`base/tests/test_rds/test_rds_clusters.py:1-14`），属于正常补齐复现步骤，不是实质阻塞。未见必须获取的外部附件；未访问外链或历史。

## 开发需求与最小未来检查

以下所有命令均为**建议，未执行**；应由实际 actor 在 `/testbed` 核验。这里只能评估所需条件，不能证明环境已具备。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 / 缺口 | 最小建议及预期 |
| --- | --- | --- | --- |
| Python、可导入的本地 Moto、boto3/botocore、Jinja2 等传递依赖 | `base/setup.cfg:26-38` 声明 Python >=3.7 和运行依赖；RDS 还导入 EC2、Neptune（`base/moto/rds/models.py:1-14`）。 | `environment_brief.md:3-12` 仅说明拟用环境，未验证激活、包版本或 actor 权限；`public_bundle.json:1` 的 conda 说法不是运行证明。 | `python -c 'import sys, boto3, moto; import moto.rds.models; print(sys.executable); print(moto.__file__)'`。预期成功且指向工作区；失败先区分环境导入问题与业务缺陷。 |
| mock 内的最小业务复现 | `user_prompt.txt:6-17`；现有公开测试使用 `@mock_rds`。 | 静态 base 不能证明实际容器可运行。此流程按公开设计不需要真实 AWS、数据库、GPU 或 Docker。 | 下方内联脚本：旧源码预计名称查询成功、ARN 查询抛 `DBClusterNotFoundFault`；修复后两者 `DBClusters` 一致。 |
| pytest 与公开断言依赖 | `base/requirements-tests.txt:1-8` 含 pytest、surer 等；测试导入 `sure`（`base/tests/test_rds/test_rds_clusters.py:1-7`）。 | 未验证安装情况，网络说明不承诺公网下载（`environment_brief.md:10-12`）。 | `python -m pytest -q tests/test_rds/test_rds_clusters.py -k 'describe_db_cluster'`；预期既有名称/空列表/不存在名称检查保持通过。该旧测试选择本身没有覆盖题面 ARN 成功路径。 |
| 共用路径回归（仅当改动触及 Neptune） | `base/moto/rds/models.py:1951-1958` 与 `base/tests/test_neptune/test_clusters.py:60-80`。 | 同上；无需全仓通过作为本题前提。 | `python -m pytest -q tests/test_neptune/test_clusters.py -k 'describe_db_clusters or test_create_db_cluster or test_delete_db_cluster'`；预期既有列表、区域及删除行为保持。 |
| 依赖准备、构建与资产 | `base/CONTRIBUTING.md:19-22`；`base/Makefile:17-19`；`base/requirements-dev.txt:1-14`；`base/pyproject.toml:1-3`。`.gitmodules:1-3` 只声明 Terraform 测试子模块。 | 全量开发依赖较宽；不能假定允许在线安装。静态包未证明镜像预装包、构建产物或资产齐备。该 Terraform 子模块不是本题 mock 复现的必要资产。 | 无独立构建是验证此源码查询改动的前置步骤。若本地包未安装，环境准备方可用离线依赖执行 `python -m pip install --no-index --no-build-isolation -e .`；需已有 setuptools 与运行依赖，成功应建立工作区可导入链接。不要为本题直接启动会覆盖全仓服务依赖的 `make test`。 |

最小复现脚本（**建议，未执行**；不落地或修改测试文件）：

```bash
AWS_EC2_METADATA_DISABLED=true AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing python - <<'CHECK'
import boto3
from moto import mock_rds

@mock_rds
def check():
    c = boto3.client("rds", region_name="us-east-1")
    cluster = c.create_db_cluster(
        DBClusterIdentifier="test-cluster-1",
        Engine="aurora-mysql",
        MasterUsername="root",
        MasterUserPassword="test123456789",
    )["DBCluster"]
    by_name = c.describe_db_clusters(
        DBClusterIdentifier=cluster["DBClusterIdentifier"]
    )["DBClusters"]
    by_arn = c.describe_db_clusters(
        DBClusterIdentifier=cluster["DBClusterArn"]
    )["DBClusters"]
    assert len(by_name) == 1
    assert by_arn == by_name

check()
CHECK
```

后续最小检查建议还包括：两个不同名称集群时 ARN 只命中目标；不存在 ARN 不意外返回同名其他区域/账户对象；若重构集合查询，保留 RDS/Neptune 的原有名称优先级。错误 ARN 的精确校验策略仍需公开规范支撑，不把本建议等同于已经明示的隐藏验收要求。

## 旧提示与环境声明分层

`public_bundle.json:1` 的 issue 目标是 ARN 查询兼容。其 `public_hints` 另要求只修改非测试源码、不要改测试、运行窄测试、完成后简短回复；本题合理源码修复不依赖修改测试，因此该指令适用时仍有可行路径（可用上方内联复现）。若该指令不适用，新增回归测试也有价值，但本审读不授权取消它。关于“测试改动都会恢复、永不计分”的旧解释不能当作已核验的现行机制，环境说明已明确纠正（`environment_brief.md:18-26`）。

静态提示所称 `/testbed`、预激活 conda 与工具可用性，应与实际 actor 的运行事实分开。`user_prompt.txt` 只是静态渲染，bundle 可见字段不等于已确认进入系统消息；未验证实际模型消息、CPU/内存限制、依赖、资源或构建能力（`environment_brief.md:3-13,25-26`）。这些是共享输入/运行条件待核对项，不据此判断题目不可解。

## 实际阅读与曝光范围

- 共享角色卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md`。
- 本题公开顶层全文：`public_bundle.json`、`user_prompt.txt`、`environment_brief.md`。实际提示文件为 `.txt`，未见所指 `.md` 版本；未读 `base_identity.json` 内容。
- base 内容按需全文、片段或搜索命中：`moto/rds/{models,responses,exceptions,utils}.py`、`moto/neptune/{models,responses}.py`、`tests/test_rds/{test_rds_clusters,test_filters,__init__}.py`、`tests/test_neptune/{test_clusters,test_cluster_tags}.py`、`tests/{__init__,helpers}.py`、`README.md`、`CONTRIBUTING.md`、`Makefile`、`setup.cfg`、`pyproject.toml`、`requirements.txt`、`requirements-tests.txt`、`requirements-dev.txt`、`.gitmodules`、`docs/docs/services/rds.rst`。Neptune responses、filter/tag 测试、README/Makefile 等部分仅见定向搜索命中，未通读。
- 在本题包内枚举过文件名；在 `base/moto`、`base/tests` 全树做过 `describe_db_clusters` 定向内容检索。文件名枚举结果曾截断，不声称逐个读过全部文件。尝试读取的 `base/setup.py`、`base/tests/conftest.py` 和枚举的 `base/tests/helpers/` 不存在，没有获得其内容。
- 未读 private、history、其他题、主审/复审/质量结论、批次 manifest/inventory/aggregates；未访问 Git 历史、镜像、外网或任何未来对象。未用默认 worktree。未导入或执行项目、测试、安装依赖、Docker、SSH、GPU、付费模型；未修改原题、源码、测试或评分，未提交推送，未创建子 agent。
- 唯一写入为本报告，采用一次创建；保存后不回写。上述边界是协作阅读约定，不是权限隔离或预训练无污染证明。
