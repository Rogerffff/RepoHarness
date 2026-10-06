# Moto5406：复用已有 East1 P2P 的材料准备

2026-09-30。**当前只完成材料与最小消费接缝设计，未实现生产、未做新 CPU 验收。** 范围限起始第2类28题中的 getmoto__moto-5406：DynamoDB表ARN随客户端地区生成。root须在MONAI4583收口及本材料复核后另行派发实施。

原正式命令只执行 `tests/test_dynamodb/test_dynamodb_table_without_range_key.py`；已有East1节点位于另一个文件 `tests/test_dynamodb/test_dynamodb_create_table.py`，**原来未被正式命令执行，也不在评分参考中**。不是已执行文件漏计参考。CPU29分别执行该旧公开节点的历史结果为base/gold通过、constant_east2因TableArn地区错误失败；同一错误候选原27参考却全部通过并得1。

最小方向：保留原test_patch完整字节与原East2 F2P/26P2P顺序，只追加已有East1节点为P2P。无需制造新测试补丁，不执行额外文件全部12个测试。

| 项目 | 原材料 | 提案（未实施） |
| --- | --- | --- |
| F2P | 1：原East2 test_create_table | 原1保持 |
| P2P | 26 | 原26 + 既有East1 test_create_table_standard = 27 |
| 总参考 | 27 | 28，原27顺序不变 |
| test_patch | SHA 8ebca50a732adf095b78e805dabf13bb64efd7037639c3280b08425705c4db8f | 完整相同；effective_test.patch只是同字节副本 |
| 安装 | 原vendor `make init` | 原安装、原镜像；无E10/派生层 |
| 判分/权限/parser | 原SWE二值判分和安全边界 | 保持；新增材料需独立身份，旧资格拒绝 |

精确原派生命令：

```text
pytest -n0 -rA tests/test_dynamodb/test_dynamodb_table_without_range_key.py
```

精确提议命令（原命令完整前缀加一个空格和唯一固定node）：

```text
pytest -n0 -rA tests/test_dynamodb/test_dynamodb_table_without_range_key.py tests/test_dynamodb/test_dynamodb_create_table.py::test_create_table_standard
```

追加节点为 `tests/test_dynamodb/test_dynamodb_create_table.py::test_create_table_standard`。原公开文件SHA a0543ad19335b4d87b717263e797055ab9876481d469808554be9ec1d6ca6292，14998字节，原base `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。该函数行12–52无参数、无参数化，仅 `@mock_dynamodb`；43–45行已有完整East1 ARN断言。共用conftest仅一个非autouse的table fixture，本节点不请求它；tests包仅注册sure辅助断言。依赖boto3/botocore、sure、pytest、moto与datetime都是原正式27项已有依赖；没有新增安装需求。

公开依据来自原题“client指定East2却ARN报East1”及base已有East1回归断言。原题例子创建名mock_Foundational_AMI_Catalog却期望test_table，不能把表名笔误当规范；已有仓库断言使用实际表名messages。gold仅是私有正对照，未用gold定义公开规范。范围不含Stream/SSE/TableClass/backup/CloudFormation或其它地区/账户/服务。

| 对照 | CPU29原27项正式reward | CPU29既有East1节点 | 新28项提议预期（尚未运行） |
| --- | --- | --- | --- |
| noop/base | 0，原East2 F2P失败 | PASSED | 0；原F2P失败，其余27通过 |
| gold | 1，原27全通过 | PASSED | 1；28全通过 |
| constant_east2 | 1，原27全通过 | FAILED，TableArn East2对East1 | 0；原27通过，新增P2P唯一目标失败 |

原actor的4条公开命令、原27评分及独立私有East1结果可支撑原镜像、激活、导入和行为依据；它们属于不同运行阶段。**原actor没有执行新28项正式spec，旧私有后检不能替代新正式reward，也不能授予训练资格。** 后续须新prepared/assignment和共用builder、真实actor原工件fresh grader、完整baseline/excluded census、逐参考/安装/源码及两层清理。

历史原OCI manifest为sha256:727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6，历史config ID为sha256:808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6。新机须实际恢复/inspect，不能把旧ID当本次验证。旧CPU真实make init包含setup.py develop与requirements-dev中的editable安装，三方安装均成功；Python3.12.4、SDK1.35.9、pytest8.3.2、导入/testbed/moto。setup约293/278/280秒，预算实际900而非旧300；不把warning、间隔采样或resource_facts=null补称全生命周期无OOM。

材料manifest：[getmoto__moto-5406 materials_manifest.json](materials_manifest.json)，SHA d5ca5786f42ef1a25463b28e89ba101a7e2062229294fc3e143fe22459f5fb83。105份冻结资产、6份生成材料逐SHA/长度核对；其中历史运行原件只作历史证据。CPU29 result列出的83条evidence全部核SHA，无缺件；这不冒充独立重做其历史91文件跨机运输审查。原四类来源来自当前不可变MONAI4583冻结树的原216数据第63行，canonical父digest/public/environment/validation见manifest。旧source_refs的raw_line SHA不含末尾LF，当前副本保留LF，两种SHA已精确对账，非材料语义差异。

本地只做静态git patch应用/AST、冻结RH2 vendor/parser重放，没有导入或运行Moto、安装、Docker、远端或重跑旧实验。真实原test_patch应用后27方法集合与参考完全相等，gold/constant源SHA与历史一致；冻结parser从原三份test段重得27精确状态，另一个旧公开节点从原日志重得1个状态。初轮嵌套git目录导致静态apply跳过，被AST检查抓到；失败目录完整保留，设置GIT_CEILING_DIRECTORIES隔离后退出0。失败仅材料准备脚本，不是项目运行。

继续入口：[原镜像与安装复用](environment_reuse.md)、[最小consumer接缝](consumer_extension_plan.md)、[公开依据与节点依赖](public_basis.md)、[完整原/新参考](../../../../../../../runs/category2_repair_20260929/swe_materials/moto5406_next/generated/references_candidate.json）、[有限验收矩阵](../../../../../../../runs/category2_repair_20260929/swe_materials/moto5406_next/generated/acceptance_matrix.json）、[原CPU29结果](../../../../../../../runs/category2_repair_20260929/swe_materials/moto5406_next/history/cpu29_result.md）、[精确静态/冻结parser记录](../../../../../../../runs/category2_repair_20260929/swe_materials/moto5406_next/generated/static_checks.json）。
