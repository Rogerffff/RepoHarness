# B3 公开要求静态审查：getmoto__moto-6408

本次仅使用角色卡及本题公开包；未接触私有评分、gold、旧审查结论、其它题、共享镜像或历史对象。未执行或导入项目、测试、安装、联网、Docker、SSH 或配额操作。以下路径与行号相对于 PUBLIC_DIR；所有运行命令都是**建议，未执行**。

## 1. 需求与证据

| 行为 | 性质及公开依据 | 应改变或保留的结果 |
|---|---|---|
| 已存在的标签从一个多标签镜像迁移到另一已存在镜像 | 明示。`user_prompt.txt:3-7,14-52` 先分别上传 image_001/image_002，再把 mock-tag 先后指向两者 | 第二次 put 后，用 mock-tag 读取到的镜像应变为 image_002；题面最低断言是前后读取的完整对象不相等 |
| 标签应具有唯一归属，迁移应修改存储状态 | 可合理推知。`base/moto/ecr/models.py:601-605` 明说 tags 唯一；`105-115,646-656` 都按标签归属检索；题面把该操作称为 move | 不应仅靠改变查询顺序或输出字段通过“不相等”断言。迁移后 mock-tag 不应仍属于 image_001 |
| 保留来源镜像其它标签，也保留目的镜像原有标签 | 可合理推知。`base/moto/ecr/models.py:304-313,745-755` 的多标签增删语义；`base/tests/test_ecr/test_ecr_boto3.py:465-502,1139-1175` | 本题场景自然应形成 image_001 → 第一份 manifest；image_002、mock-tag → 第二份 manifest。来源的 image_001 标签不能因迁移丢失；目的原有 image_002 标签也不能丢失 |
| 同 manifest 可有多个不同标签，仍是一条镜像记录 | 公开测试明确。`base/tests/test_ecr/test_ecr_boto3.py:465-502` | describe 返回一条镜像、两个标签；该例标签顺序已有断言 `["v1", "latest"]`，内部重构需保留可观察结果 |
| 旧的同标签、不同新 manifest 覆盖路径 | 公开测试明确。`base/tests/test_ecr/test_ecr_boto3.py:506-545` | 来源只有一个标签时，覆盖后旧镜像移除、仅保留新镜像；之后以其它标签重新上传旧 manifest 可成为另一镜像。题面主要增加“目的镜像已存在、来源有多个标签”这一组合，不能破坏旧路径 |
| 相同 manifest 和相同标签的重复上传 | 公开测试明确。`base/tests/test_ecr/test_ecr_boto3.py:549-581`；`base/moto/ecr/exceptions.py:108-125` | 保留 PutImage 的 HTTP 400、ImageAlreadyExistsException、已测试错误消息和镜像数不增长。`base/CHANGELOG.md:5-22` 也将重复镜像/标签列为 4.1.11 行为 |
| 旧标签仍可读取同一镜像；空标签不应混入列表 | 公开测试明确。`base/tests/test_ecr/test_ecr_boto3.py:1108-1135,808-864`；`base/CHANGELOG.md:128` | 多标签查询仍应返回对应 manifest；未提供 imageTag 的上传不能产生 None 标签或清掉其它标签 |
| API 输出和默认仓库行为 | 公开接口及测试。`base/moto/ecr/responses.py:55-82,101-109`；`base/moto/ecr/models.py:85,315-364`；`base/tests/test_ecr/test_ecr_boto3.py:337-350,378-396,1028-1067` | 保留 boto3 参数名及 image/imageId/imageDigest/imageTag/imageManifest、images/failures 等结构。题面未设置 mutability，仓库默认 MUTABLE；本题没有要求另行实现 IMMUTABLE 策略 |

题面没有逐项明示：多标签镜像中“不是最后追加的旧标签”被重新上传时的重复错误、按旧标签查询时响应 imageId.imageTag 应回显请求标签还是当前代表标签、迁移后的全局镜像排列顺序、JSON 内容等价但字符串不同的 manifest 是否去重。现实现用完整 manifest 字符串匹配（`base/moto/ecr/models.py:570-575`），而多标签查询公开测试只比较 manifest（`base/tests/test_ecr/test_ecr_boto3.py:1125-1135`）。这些不能直接提升为本题新增的精确验收约定；尤其不应要求与某个内部实现相同的辅助函数名或列表遍历方式。

## 2. 合理实现范围

公开要求允许在 put_image 内统一管理标签所有权，也允许抽取内部辅助方法、复用现有标签增删功能，或调整内部索引；只要上述可观察语义及旧公开测试成立，都应具有可接受性。没有公开要求限定改动行数、具体函数名或必须调用 batch_delete_image。较大的重构仍须保持各个响应序列化及已有标签顺序约定。

只让 batch_get_image 把目的镜像排到前面、只改变返回对象使题面断言不等、或删掉整个多标签来源镜像，都不能满足从公开代码合理推知的标签迁移语义。已有测试支持保留单标签旧镜像的删除行为，但“移向已存在目的镜像且来源仅一个标签”这个额外组合没有在本次读到的公开测试中直接断言；可由旧覆盖/删除策略推导，不应冒充题面直接说明。

## 3. 初态线索、疑义及输入类别

**可定位的静态调查入口。** `ECRResponse.put_image` 把请求转交后端（`base/moto/ecr/responses.py:55-64`）。后端找到目的 manifest 时直接 update_tag（`base/moto/ecr/models.py:608-621`），这会只更新目的对象的 image_tag 和 image_tags（`310-313`）。移除已有同名标签的逻辑位于“目的 manifest 尚不存在”的另一个分支（`591-607`）。按题面顺序，来源和目的会同时保留 mock-tag；batch_get_image 遍历全部镜像并把匹配者都加入结果（`646-656`），因此旧镜像仍是返回的第一项，预计使题面 `initial_image != new_image` 失败。这是代码路径推演，没有运行验证。

**题面代码可补全。** 题面省略 json、boto3、mock_ecr 和 `_create_image_manifest` 的导入，也只定义测试函数而未调用。公开测试在 `base/tests/test_ecr/test_ecr_boto3.py:1-23` 给出了全部导入，helper 位于 `base/tests/test_ecr/test_ecr_helpers.py:7-44`，无需补外链或未知附件。helper 随机生成层；复现应确认两份 manifest 不相同，避免把“重复同镜像”混入本题条件。恢复这些导入和阅读调用者属于正常开发调查，不构成题面缺陷。

**仍需区分的三类输入。**

- Issue 需求：上表所列回归及复现序列，来源为 `user_prompt.txt:3-53` 和 `public_bundle.json:1` 的 problem_statement。
- Harness 操作指令：`public_bundle.json:1` 的 public_hints 要求只改 NON-TEST 源码、不改测试、窄范围验证并简短总结。针对本题，模型源码中的修复范围足以承载合理解；即使禁止改测试仍适用，也可用内存脚本复现并运行原有公开测试。若该禁令不适用，则可新增回归测试，但这不是完成行为修复的前提。
- 待核验的环境声明：`public_bundle.json:1` 声称 /testbed 及预激活 conda testbed，不是运行证明；其“全部测试改动恢复、永不计分”的解释已被 `environment_brief.md:18-26` 明确限定，不能当作当前统一机制。本题哪些官方文件恢复、原禁令是否实际适用、hints 如何进入实际消息，仍属共享输入/运行条件问题。bundle 会写入真实解题工作区可见路径，未出现在渲染题面不代表不可见。

目前没有发现会阻碍理解核心修复的缺失公开材料。无法验证运行条件不等于题目不可解；也未给本题通过/淘汰标签。公开祖先历史不是这一静态定位所必需，因此未请求或访问历史。题面之外的完整 AWS 语义如确需扩展，才需要另补对应公开资料；本审查没有联网推断。

## 4. 开发需求与最小验证建议

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持层次、缺口 | 最小验证与预计现象 |
|---|---|---|---|
| Python、本地 Moto 源码及写权限 | `base/setup.cfg:26-38` 要求 Python >=3.7；`public_bundle.json:1` 指定 /testbed 与 base commit | `environment_brief.md:8-12` 描述拟用 actor、可写工作区及默认资源；未验证解释器激活、实际资源或 import 路径 | C1（建议，未执行）应导入本地 /testbed 的 Moto 和 ECR 模型；导入失败或路径指向其它安装属于环境问题 |
| boto3/botocore 与 Moto 基础依赖 | `base/setup.cfg:28-38,133`；ecr extra 无额外条目；`base/moto/ecr/models.py:8-30` | 镜像标识和 digest 只是 bundle 元数据，不提供已安装版本。无需推定可下载依赖 | C1（建议，未执行）检查直接导入；C2 再覆盖 mock 启动和序列化，成功导入本身不证明能复现 |
| pytest、sure 导入支持、freezegun 等公开测试依赖 | `base/requirements-tests.txt:1-8`、`base/tests/test_ecr/test_ecr_boto3.py:1-23`；`base/tests/__init__.py:3` → `base/tests/helpers.py:4` 也导入 sure | requirements 使用 surer 包名而代码导入 sure；实际安装能否满足需核验，不能仅凭文本判为缺包。环境未提供锁定安装事实 | C3（建议，未执行）应收集并运行该模块；缺依赖导致的 collection error 不应记作业务回归 |
| 进程内 mock ECR，不需真实 AWS/ECR、Docker daemon 或外部镜像层 | 题面使用 mock_ecr；`base/moto/ecr/__init__.py:1-5`；`base/moto/core/models.py:57-85,301-341,360,424-439`；`base/moto/settings.py:9` | 默认是进程内 mock，但 actor 的 TEST_SERVER_MODE 尚未验证；该变量为 true 会改用服务模式 | C2/C3（建议，未执行）显式指定 TEST_SERVER_MODE=false。预期仅使用虚拟凭据和本地 mock；不需要持有 AWS 账号或拉容器镜像 |
| 两份 manifest 与测试 helper | `base/tests/test_ecr/test_ecr_helpers.py:7-44` | 包中已有 JSON 构造代码，无额外二进制或远程资产缺口 | C2（建议，未执行）预计基线在最后不等断言失败；修复后查询切换到第二份 manifest。可进一步检查标签唯一归属和其它标签保留 |
| 安装 / 构建 | `base/CONTRIBUTING.md:17-22`、`base/Makefile:17-19`、`base/pyproject.toml:1-3`；`base/requirements-dev.txt:1-15` | 普通 Python 源码，无本题专用构建步骤。网络限制见 `environment_brief.md:10`；缺依赖时需要预装环境或声明的离线资产，不能假定公网安装可用 | 无需为此次修复先跑全量构建。若确需包构建，C4（建议，未执行）预期生成 wheel；依赖或 build 工具缺失应记环境缺口 |
| Terraform 子模块及全仓特殊服务测试 | `base_identity.json:10-17`、`base/.gitmodules:1-3`、`base/Makefile:46-50` | terraform-provider-aws 内容未导出；本题 mock ECR 路径未见依赖 | 无须补该子模块以完成所列最小验证，也不应因缺少它要求全仓测试或判本题不可用 |

以下命令仅供将来的真实 actor 环境使用；`/testbed` 来自公开工作区约定，不指当前静态导出目录。**全部为建议，未执行。**

C1：最小导入及安装来源检查（建议，未执行）。

```bash
env TEST_SERVER_MODE=false PYTHONPATH=/testbed python -c 'import sys, boto3, botocore, moto; from moto import mock_ecr; from moto.ecr.models import ECRBackend; print(sys.executable); print(moto.__file__); print(boto3.__version__, botocore.__version__)'
```

C2：补齐公开 helper 导入并直接执行题面核心序列，不修改测试文件（建议，未执行）。最后的断言预计在初态失败；该结果尚未经实际证实。

```bash
env TEST_SERVER_MODE=false PYTHONPATH=/testbed python - <<'PY'
import json
import boto3
from moto import mock_ecr
from tests.test_ecr.test_ecr_helpers import _create_image_manifest

@mock_ecr
def reproduce():
    repo_name = "testrepo"
    tag_to_move = "mock-tag"
    manifests = {
        "image_001": json.dumps(_create_image_manifest()),
        "image_002": json.dumps(_create_image_manifest()),
    }
    assert manifests["image_001"] != manifests["image_002"]
    client = boto3.client("ecr", "us-east-1")
    client.create_repository(repositoryName=repo_name)
    for name, manifest in manifests.items():
        client.put_image(repositoryName=repo_name, imageTag=name,
                         imageManifest=manifest)
    client.put_image(repositoryName=repo_name, imageTag=tag_to_move,
                     imageManifest=manifests["image_001"])
    initial_image, *_ = client.batch_get_image(
        repositoryName=repo_name, imageIds=[{"imageTag": tag_to_move}]
    )["images"]
    client.put_image(repositoryName=repo_name, imageTag=tag_to_move,
                     imageManifest=manifests["image_002"])
    new_image, *_ = client.batch_get_image(
        repositoryName=repo_name, imageIds=[{"imageTag": tag_to_move}]
    )["images"]
    assert initial_image != new_image

reproduce()
PY
```

题面原断言比较完整对象且只取首项，比业务目标更弱。后续验证宜再检查查询恰有一个结果且 manifest 等于 image_002，并通过 describe_images 确認来源/目的的其它标签保留；这些是语义核对建议，不是本次已执行测试。

C3：先检查与改动直接相关的公开测试，必要时扩展到同一模块（两条均为建议，未执行）。旧测试没有覆盖题面的完整组合，基线通过这些测试也不能排除本回归。

```bash
env TEST_SERVER_MODE=false PYTHONPATH=/testbed python -m pytest -q /testbed/tests/test_ecr/test_ecr_boto3.py -k 'put_image or put_multiple_images_with_same_tag or put_same_image_with_same_tag or batch_get_image or batch_delete_image_by_tag or batch_delete_image_delete_last_tag or describe_images_tags_should_not_contain_empty_tag'
env TEST_SERVER_MODE=false PYTHONPATH=/testbed python -m pytest -q /testbed/tests/test_ecr/test_ecr_boto3.py
```

C4：只有需要确认包构建时使用；不是修复前置条件（建议，未执行）。禁用隔离意味着所需 build/setuptools 等必须已经可用。

```bash
python -m build --wheel --no-isolation --outdir /tmp/moto-6408-wheel /testbed
```

公开开发文档中的 make init 会安装广泛依赖，make test 会运行全仓及 lint（`base/Makefile:17-44`），不宜直接作为本题最小验证。未建议也未执行下载、Docker、SSH 或服务部署。

## 5. 实际阅读范围与限制

实际打开的材料：

- 角色卡；`user_prompt.txt` 全文、`public_bundle.json` 全文、`environment_brief.md` 全文、`base_identity.json` 全文。
- `base/moto/ecr/models.py`：1-165、251-375、490-763；`base/moto/ecr/responses.py`：1-126；`base/moto/ecr/exceptions.py`：1-137；`base/moto/ecr/__init__.py` 全文。
- `base/tests/test_ecr/test_ecr_boto3.py`：1-65、330-584、808-866、1025-1213，以及该文件中 image/tag 相关行的搜索；`base/tests/test_ecr/test_ecr_helpers.py` 全文；`base/tests/__init__.py` 与 `base/tests/helpers.py` 全文。
- `base/moto/__init__.py`：1-90；`base/moto/core/models.py`：35-100、301-365、420-445 的相关片段和 mock/凭据关键词搜索；`base/moto/settings.py`：1-20、95-115 及相关变量搜索。
- `base/README.md`：12-70 及安装/测试关键词搜索；`base/CONTRIBUTING.md` 全文；`base/setup.cfg`：24-62、128-138、215-232 及相关关键词搜索；`base/requirements.txt`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/pyproject.toml` 全文；`base/Makefile`：1-55 及测试/安装相关行搜索；`base/.gitmodules` 全文。
- `base/CHANGELOG.md`：1-34、112-131、560-577 及 ECR/版本关键词搜索，仅为此 base 内的公开文档，没有读取 Git 历史。
- 本题包内做过文件名清单/筛选；尝试打开 `base/tests/conftest.py` 后得知不存在，之后仅搜索 conftest 文件名，未打开其它服务的 conftest。部分组合工具输出截断，关键实现与测试片段随后单独补读。

未查：其它服务实现、其它 ECR 测试模块内容、完整 core 导入传递依赖、所有 ECR 参数组合、外链规范与完整在线文档、实际容器、真实消息、actor 环境、资源/网络可达性、Git 祖先、子模块内容、隐藏验收测试。未修改 base。

`user_prompt.txt` 仅是静态渲染；`base/` 是 Git 跟踪文件导出而非完整运行容器（`environment_brief.md:3-6`）。因此本报告不证明模型真正收到的消息、运行资源、依赖安装和开发条件已经验证。只读范围是本次协作约定，不是文件权限隔离或预训练无污染证明。

关键未知：实际 actor 的 Python/依赖版本与 mock 启动可用性；hints 进入消息的位置、禁止改测试指令本次是否适用以及具体恢复规则；未明确约定的多标签边界输出。核心需求和源码调查入口已有公开依据，未发现需要额外公开附件才能推进的阻塞点。
