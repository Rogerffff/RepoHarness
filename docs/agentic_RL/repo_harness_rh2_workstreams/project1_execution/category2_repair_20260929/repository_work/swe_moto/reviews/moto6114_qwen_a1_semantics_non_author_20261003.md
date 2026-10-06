# Moto6114 Qwen a1 实际模型补丁语义非作者窄核

日期：2026-10-03。对象：`gpu1003-moto6114-qwen36-a1` 的固定实际模型 patch。结论：**该补丁能按常规名称和 cluster ARN 查找当前 backend 的集群，但它不只是修公开 describe 问题；额外改动已引入两处可从原公开 base 直接证明的 Neptune 名称委托回归。** 原 GPU raw reward 1 与这个语义结论并存；本报告不改原分数、不把安装故障改判为模型 0，也不完成安装修复或重 grade。

## 范围、固定身份和证据方法

原件根目录为 `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-moto6114-qwen36-a1/`（下称 J）。实际读取 J 的公开 `solver_prompt.txt`、`attempt/candidate/getmoto__moto-6114.diff`、完整 `attempt/harness/trajectory.jsonl`，以及 `attempt/frozen/baseline.tar` 与 `baseline_manifest.json` 的必要源码成员。只用标准库读取、哈希、JSON/AST 解析和内存字符串比对；没有解包到工作区，没有导入/执行源码、SDK、Docker、模型、远端或 CPU 测试，没有修改任何原件、共享代码、已有报告或请求，仅新增本报告。

审查者先前已接触本题私有评分上下文，**不是盲 solver**。本次问题依据仅来自实际公开 prompt、实际模型 patch 与其公开 base 源码；没有拿私有新增断言或未规定的 AWS 行为扩展功能要求。题主交接的 GPU raw1、`make init` wheel 权限失败及其重评分由 GPU root 线程负责，本次没有独立重做该执行/评分验收。

| 原件（相对 J） | SHA256 | 字节数 |
| --- | --- | ---: |
| `attempt/candidate/getmoto__moto-6114.diff` | `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747` | 6463 |
| `solver_prompt.txt` | `8974243c9d3df94c6de1a79d5a4e7d12963c79395153a545e917f542496ab599` | 3207 |
| `attempt/frozen/baseline_manifest.json` | `04e38e97900d9e2d0f39a8b458dfe8ebf4569c8b50cb9c1f4610c7b16ee8f031` | 471903 |
| `attempt/frozen/baseline.tar` | `cfc48e225a8d351f978d69fc449906937b52f47d4d6f9e02b0fb8c189e561957` | 50032640 |
| `attempt/harness/trajectory.jsonl` | `84e8f68be83f41c2d06259fa3eae613e58113780f6ac240a26514fdf1f266e11` | 1964647 |

baseline manifest 的 task 为 `swe_gym_lite::getmoto__moto-6114`，workdir `/testbed`，`materialized_head` 与 `task_base_commit` 均为公开 prompt 所列的 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。tar 中实际读取的 `moto/rds/models.py`、`moto/neptune/models.py`、两者 responses、`moto/core/__init__.py`、`moto/core/common_models.py` 和 `tests/test_neptune/test_clusters.py` 均为普通成员，内容 digest 逐项匹配 manifest。本次没有宣称核过整份 baseline 的所有成员。

关键原源码 SHA：RDS models 为 `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`，Neptune models 为 `c5bf4a50b5676592daf8df02dbaef2978019b6d04cbbfdceb0387c6acbcfe906`。在内存逐行核五个 diff hunk 与原 RDS 文件相符，构造出的候选源码 AST 可解析；原/新 Git blob 分别为 diff 中的 `9a670c2fd4e4be8c24aa4ad385eec47ce3eb42a7` / `d7ce78554bab93a17b9d784ea8f8e03d012e6e9f`。候选源码 SHA256 为 `05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d` / 161961 字节。又将轨迹的九次实际 Edit 仅在内存按 old/new string 顺序比对，所得字节与该候选完全相同；下述“候选行号”指此内存重建文件，未将其写入仓库。

## 公开要求与 helper 的准确范围

公开 issue 要求 `describe_db_clusters(DBClusterIdentifier=...)` 能使用已有集群的 ARN，并保留名称查找；开发说明没有要求 modify/start/stop/delete/snapshot 一并支持 ARN。实际 patch 只改 `moto/rds/models.py`，除新增 helper/describe 外，还改了这五项写操作。

候选 `find_cluster_from_identifier:1962–1978` 对匹配原 `arn_regex` 的输入提取末尾两段，只有 resource type 为 `cluster` 才按 resource name 查字典；普通 name 则直接查字典。两种情况均先 RDS、后 Neptune，找不到时抛 `DBClusterNotFoundError`。因此对当前 account/region 中的普通 RDS 集群，ARN 对应哪个名称就取哪个对象，不是返回第一项；直接 name 的原优先次序、空参数返回两种 backend 全列表的分支均保留。原 Neptune DBCluster 的 ARN 本身也是 `arn:aws:rds:...:cluster:<name>`（原 Neptune models:109–111）。

helper 没有比较 ARN 的完整 account/region 与对象 ARN；这说明它的实际实现范围，**不在本报告中据此新增跨区域/跨账户 AWS 规范或认定一个额外必修功能要求**。本题公开常规 ARN 场景的修复与下述原行为回归应分开判断。

## 两处确定的原行为回归

### 1. RDS façade 按 Neptune name 删除会访问不存在的属性

原 RDS models:1976–1987 在 name 不属于 RDS、属于 `self.neptune.clusters` 时，直接委托 `self.neptune.delete_db_cluster(name)`。原 Neptune models:319–326 将已存在 name 从字典移除并返回对象，注释还明确 DeletionProtection 尚不执行。

候选 `delete_db_cluster:2001–2013` 先由通用 helper 得到 Neptune DBCluster，然后在 2003 行无条件读 `cluster.deletion_protection`，没有继续原 Neptune 委托。**原 Neptune DBCluster:53–107 没有创建这个属性，也没有同名 property；其父 `BaseModel` 仅定义实例登记的 `__new__`，没有属性兜底。** 对正常新建 Neptune 集群，这条路径必然先发生 `AttributeError`，尚未执行 pop，原先能完成的 name 删除因此失败。

这是原 façade 的已有行为回归，不需要假定真实 AWS 是否应该支持某项 Neptune 参数。`moto/neptune/models.py` 没被 patch 改动，独立 Neptune 客户端调用自己的 backend delete 仍是原实现；不能泛化为所有 Neptune 删除 API 都坏了。

### 2. RDS façade 按 Neptune name 启动被新增 RDS 状态条件拒绝

原 RDS models:1989–2001 对不在 RDS 字典的 name 委托 `self.neptune.start_db_cluster(name)`。原 Neptune models:346–353 只核存在，复制对象并令返回状态为 `started`，底层状态保持 `available`；原 create 在 DBCluster:82 将状态设置为 `available`。原公开 Neptune 测试 `tests/test_neptune/test_clusters.py:108–116` 也是创建后直接 start 的序列，佐证此 base 的实现行为，但该测试本身调用 Neptune 客户端，不是 RDS façade 回归已被运行验证的证据。

候选 `start_db_cluster:2015–2024` 去掉 Neptune name 委托，统一要求 `cluster.status == 'stopped'`。因此同一正常创建、仍为 `available` 的 Neptune name，原 RDS façade 可返回 started，候选则在 2017–2020 行抛 `InvalidDBClusterStateFault`。这也是源码直接证明的行为差异，不以外部 AWS 启停政策为根据。没有声称原 RDS 集群自己的 stopped 前置条件有误。

以上两项是**静态确定**的控制流与属性事实；本次没有实际运行这些反例，不把推导出的异常写成已运输的 CPU 结果。

## 其余额外改动的边界

| 额外改动 | 静态结论与证据强度 |
| --- | --- |
| `modify_db_cluster` 的 Neptune name | 普通 Neptune name 仍在候选 1887–1897 行进入原 Neptune modify，kwargs 保持原格式；这一 name 委托没有发现上述 start/delete 式回归。 |
| modify 的 Neptune ARN 扩展 | 候选能识别 ARN 的末尾名称，却把原 ARN kwargs 原样传给 Neptune；原 Neptune modify:329–332 直接以 `kwargs['db_cluster_identifier']` 索引按名称存放的字典，因此正常创建的 Neptune 名称对象用 ARN 进入此新分支会 KeyError。它是新增扩展自身不完整，不是原 base 已支持的 ARN modify 被破坏；公开 describe 要求不授权据此扩大 AWS 功能验收。 |
| modify / delete 在已有 RDS rename 后 | 原 modify 已有“pop new identifier 后仍用旧 dictionary key”的不一致；模型没有产生这个原缺陷。但模型新增 `actual_id=cluster.db_cluster_identifier` 并以它 del/pop，会使该原状态进一步变成 KeyError：create `old` → modify `old` 且 new=`renamed` 后，字典键仍是 `old`、对象 identifier 已是 `renamed`；原再 modify/delete `old` 能按旧键进入，候选却尝试删除 `renamed` 或从 Neptune pop。此序列差异可由源码证明，不能把原 rename 本来就完整正确或“按新名查找失败”说成模型新引入。 |
| `create_db_cluster_snapshot` 的 RDS ARN | helper 选到普通 RDS 对象后，后续逻辑与原路径相同；此窄范围未发现普通 RDS ARN 快照的确定错误。 |
| snapshot 的 Neptune 扩展 | 原 snapshot 只取 RDS 字典，Neptune name 原来抛 DBClusterNotFound；候选 helper 接受 Neptune 后，后续仍读 `cluster.copy_tags_to_snapshot`（候选 1928 行），原 Neptune DBCluster 没有该属性。新接受分支会 AttributeError。这是额外扩展未适配对象类型，不当作公开 describe 必须新增的 Neptune 快照功能。 |
| `stop_db_cluster` 的 Neptune 扩展 | 原 RDS stop 对 Neptune name 返回 NotFound，候选会得到其对象并允许 available → stopped。这是明确扩大接受范围；仅凭本地 base/公开 issue，没有证据要求或禁止它，不认定一个外部 AWS 语义错误。 |

这份补丁的两个主要回归已经足以否定“仅修公开 describe ARN 且保持原行为”的表述；不需要用上述弱范围判断凑出更多必修要求。

## 实际轨迹能证明什么

完整 harness JSONL 有 812 行。其 Edit 字节已与最终 patch 对齐，修改目标全部是 RDS models。模型轨迹记录了普通 RDS ARN/name 的自测，最后 778/782 行的自测输出包含 describe、snapshot、stop、start、delete 成功；798 行记录 `tests/test_rds/` 汇总为 212 passed。没有 `mock_neptune` 或 `tests/test_neptune` 的实际 Bash 检查，故这些 RDS 自测不能排除 Neptune façade 回归。

轨迹 736/740 行曾记录中间版 delete ARN 的 KeyError，模型在 764 行修正 actual id 后于 778/782 行重做该 RDS 自测；本报告未把已被最终 patch 修掉的中间错误作为当前问题。模型运行 pytest 的部分命令使用 head/tail 管道，轨迹内成功文本属于模型当时的自测记录，不等于本次独立重跑或正式安装/重 grade 收口。模型最后声称 212 通过也不涵盖上述跨 backend 名称路径。

## 如需运行，最小定向核查

本报告不启动 CPU。若题主需要实际运行证据，最小范围是**同 account/region 的原 RDS façade 与 Neptune backend 两条名称路径**，在原 base 与固定模型 patch 两侧分别核一次：

1. 正常创建一个 Neptune DBCluster（backend 直接创建时显式使用原 API 的 `storage_encrypted='false'`），保持原 create 的 available 状态，再调用同区 RDS backend 的 `start_db_cluster(name)`；原侧应返回 started，候选侧预期在 RDS 状态检查抛 InvalidDBClusterStateFault。
2. 另建一个 Neptune DBCluster，再调用同区 RDS backend 的 `delete_db_cluster(name)`，不传 snapshot；原侧应删除并返回对象，候选侧预期在 deletion_protection 属性访问抛 AttributeError，字典仍保留对象。

直接 backend 路径即可确认现有委托的回归，无需自主模型、全 RDS/Neptune 套件或真实 AWS；如选择 SDK 路径，则同时启用原 RDS/Neptune mock，避免把单独 Neptune 客户端的未改分支当作覆盖。上述“预期”来自本次静态推导，尚不是实际跑出的结果。这些仅是候选补丁诊断，不改冻结评分、参考列表或原 raw reward，也不把安装故障记为模型 0。GPU root 的安装修复/重 grade 闭环保持原职责。
