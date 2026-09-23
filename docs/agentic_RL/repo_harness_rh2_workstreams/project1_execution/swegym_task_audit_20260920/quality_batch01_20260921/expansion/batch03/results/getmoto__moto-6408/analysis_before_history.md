# getmoto__moto-6408：历史读取前独立初稿

撰写时间：2026-09-20 21:37 UTC / 2026-09-21 05:37 SGT；保存后的实际封存时刻以协调者哈希登记/mtime为准，本文不回写。仅静态读取文本、已有日志和stdlib文本统计；未运行/导入项目、安装、网络、Docker/SSH、模型、配额或CPU反例。

路径：`ROOT=${REPO_ROOT}`；`P=ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6408`；`V=.../private/getmoto__moto-6408`；`E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6408`。源码行均相对P/base。先读本题封存public_read；后读本题全部test/gold/grading/validation及run_refs、environment_record和原件。**environment_record已经显示gold/noop摘要，不能称无结果暴露盲审。** 未读本题history/refs或旧调查、其它题结果、reviewer及本批聚合。复用协议和同一冻结baseline的机制知识，不把前题质量结论用作本题证据。

## 暂定处置

`needs_review / static_review`，仅`development_diagnostic`。公开目标清晰、初态与原参考分差有可解释的实证，gold修复题面“两个已存在镜像之间移动标签”的具体顺序；但验收没有验证唯一归属/剩余标签，且沿gold调用链发现新目的manifest分支仍可能删除刚创建的镜像。后者是合理邻接边界的未修旧缺陷，**尚未证成gold新增回归，也不把它冒充题面精确原复现**。先作一项窄CPU对照判断验收边界；本轮只建议未执行，正式actor仍待验。

## 1. 公开需求、材料与初态

base `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a`，tree `4d46b90dfbe69f5b7468a662b4dc237fbe9f513b`；public_bundle/base_identity/grading一致。gold SHA256 `fa6d9adadc553b4eb713ca3749a90efe7adb572348c837fd2bbf48a3dd95d7dd`与validation/ledger一致。材料及210清单验证复用协调者结果，未重复全库blob核验。

题面在默认MUTABLE仓库先上传两个不同manifest，各有image_001/image_002标签，再先后将mock-tag加在它们上，要求迁移后查询切换。公开models.py:601–605直述标签唯一，304–313提供多标签删除/新增，batch_get_image:646–656按成员关系取值；这些支持“移动”必须改变持久标签归属，且保留两侧其它标签。合理约束来自公开代码/旧测试，不是仅来自新增测试名称。题面只取首项比较完整对象；隐藏F2P加强到确切manifest，属核心目标的合理断言。

base已存在目的manifest分支608–621只update_tag，没有从原镜像移除标签，故两个镜像同时持有mock-tag；按repository.images原顺序查询首项仍旧manifest。N原日志719–727真实失败于该结果，初态不是仅由diff推断。题面省略json/boto3/decorator/helper导入，公开测试1–23与helper全文可补，不构成必需外部附件缺失。未捕获实际模型消息；通用public_hints与user_prompt的关系仍需正式actor核验。

## 2. 需求—断言双向映射

| 公开要求/旧行为 | 依据 | 对应测试与关键断言 | 覆盖程度 |
| --- | --- | --- | --- |
| 将mock-tag从已存在、多标签来源移到已存在目的 | user_prompt整段；models.py:601–605、646–656 | 唯一F2P test_multiple_tags__ensure_tags_exist_only_on_one_image：移动前首项manifest=001，后首项manifest=002 | 精确复现覆盖；noop失败、gold通过。 |
| 一个tag最多指向一个镜像、来源其它tag和目的其它tag仍在 | models.py:304–313、601–605、745–755；公开多标签/删除测试 | F2P两处都用`first, *_`，未断言images长度/failures，也未describe或旧标签回查 | 原目标的状态不变量未完整保护。仅改排序或把来源整图删掉的部分实现可能蒙混，未执行证明得分。 |
| 多个tag对应一个manifest对象且保留追加顺序 | test_ecr_boto3.py:465–502 | P2P test_put_image_with_multiple_tags：一图，2标签，精确[v1,latest] | 单镜像加独立标签覆盖；与迁移组合尚不同。顺序断言来自旧公开行为，不是gold唯一写法。 |
| 同tag的新manifest替换、原来源单tag可移除 | 506–545 | P2P test_put_multiple_images_with_same_tag：旧图只有一标签，替换后一图且digest等于新图；重传旧manifest另tag后两图 | 覆盖单tag来源+新目的；未覆盖多tag来源+新目的。 |
| 同manifest和同tag重复报ImageAlreadyExists | 549–581、CHANGELOG:22；models.py:577–579 | P2P test_put_same_image_with_same_tag：400/错误码/动态digest错误消息、最终一图 | 已有单tag精确错误覆盖；非代表旧tag重复未明确测试，不能强制额外错误顺序。 |
| 无imageTag不生成None标签、不清其它标签 | 808–864 | P2P两项describe_images_tags_should_not_contain_empty_tag | 无tag→多tag，以及多tag→无tag→新tag均覆盖，gold静态无明显新增破坏。 |
| 普通put/get/list/describe和媒体类型、manifest list、时间、删除多/末标签 | 337–461、585–635、1028–1211 | 相关P2P：返回结构、get一项且failures空、多标签查询manifest相同、remove last删除图等 | 已追对应源码和关键旧测试。迁移后保留旧标签仍未组合断言。 |

完整test.patch：只新增一个49行测试函数，两个最终assert比较manifest；两次put的digest索引只是字段存在性访问，并不断言digest关系。无新增fixture或内部Mock断言。唯一helper `_create_image_manifest`完整展开：标准库random生成5层，各层size与sha输入，再用标准库hashlib合成digest；无下载、Docker镜像层或真实ECR。已有helper随机性可能使测试数据不同，但单次原日志确为不同manifest；没有实测flaky或实质碰撞证据，不据随机调用判坏题。未补独立manifest不同断言是小限度，不列首要问题。

F2P用@mock_ecr与真实boto3客户端序列化进程内mock，us-east-1、create_repository，未用额外fixture。读了ECR __init__、tests/__init__/helpers、imports、requirements；本题tests/test_ecr及tests顶层无conftest。sure用于旧断言，F2P的两个比较是普通assert。

完整F2P1/P2P95参考清单已读；日志全部96摘要行做stdlib文本分账，引用集合与解析键集合相等，无缺席、额外、skip或碰撞。**不等于展开了95个函数。** 展开的P2P主要为put各分支（337–581）、list（585–635）、describe空tag两项（808–864）、batch_get三项（1028–1135）、batch_delete_by_tag/delete_last_tag（1139–1211）；describe_images与by_tag另读部分/主体。策略、扫描、复制、生命周期、仓库CRUD等其余节点只读清单/结果，不作全面语义认证。

## 3. 合理路线、可蒙混实现与gold检查

合理非gold路线：先确定目标Image及原tag所有者，只从其它对象解除该tag，必要时按公开旧策略移除失去最后tag的旧图；再创建/标记目标。可抽取内部操作或以索引维护归属，不必调用batch_delete_image、不必修改response序列。新增验收没有内部函数/调用形状约束，未发现必然误拒该路线；未执行替代解，不声称所有合法解均接受。

**I1：迁移状态漏测。** 在“已存在目的、其它镜像持同tag”时仅把目的对象移到repository.images首位，保留原镜像标签；原F2P会读到目的manifest，但真实状态仍重复。相关P2P没有这组组合的唯一性断言，预期可存活但尚未跑实际RH2。另一个错误修法直接删整个来源图也损失image_001标签，却满足新增两个manifest比较。不是说官方测试无效，而是其方法名中的“only one image”没有被结果数量/归属直接验证。

gold在existing-manifest分支先batch_delete_image再update_tag；原题来源有两个tag，删除只移除mock-tag，保留image_001；目的尚无mock-tag，未被删，再追加并保留image_002。故公开精确序列的完整归属静态上正确；实际历史得分亦支持已测部分。补丁仅models.py两个hunk，不引入新依赖/文件。第一hunk把tag匹配从代表image_tag改成image_tags成员，方向合理。

**I2：邻接未修缺陷——新目的镜像被删除（强静态推断）。** 构造原镜像A的tags=[v1,latest]，用v1上传从未存在的manifest B。gold在新manifest分支591–607先append B(v1)，再因A含v1而调用batch_delete_image(v1)。该函数716–755先对A移除v1，A仍有latest所以列表不缩短；接着遍历新B，只有v1就把B整图remove。put返回的Image对象仍被返回，但后续batch_get(v1)无图。base用代表标签latest比对v1，反而不会进入delete，从而保留A/B的重复v1——base同样错误但表现不同。若移动的是latest（代表标签），base/gold均已有同样新图删除路径。这是旧缺陷未彻底解决，不是“原base正确、gold引入”的已证回归。

I2与公开“已有tag、多tag镜像”的描述及同tag新manifest旧测试组合有关，但题面精确复现预创建了B。因此应先区分业务修复是否包含这一邻接组合，再讨论任务修订；不据此自动reject。I1针对精确原序列，不依赖扩大范围。

唯一优先CPU实验（建议未执行）：一份受控迁移对照，只改变“目的manifest是否预先存在”，原镜像始终多tag，检查返回目标、完整images计数、describe中两侧标签集合。比较base/gold与先解除旧归属的合理实现，并记录原F2P/P2P得分。此实验可同时确认gold对题面控制组正确、I2是否真实、现有评分是否不敏感；不要求同时制作两份攻击补丁。I1的排序部分实现暂列后续候选，不声称已测奖励漏洞。

## 4. 原日志与历史执行条件

G=`E/gold/eval_logs/evallog_replay-er19-iw1-getmoto__8717daf0.eval.log`；N=`E/noop/eval_logs/evallog_replay-er19-iw1-getmoto__0fdceeeb.eval.log`。两ledger:1、diagnostics、driver.log、image.json均已读。

- gold started_at=2026-09-19T06:29:51.362821Z；noop=06:28:42.140326Z。镜像均`sha256:9ea5a5f571d9feda40bda0d0be2c1242c409a457c7ff38827deb9b937a4e85c4`，来源digest `sha256:db52bf5253616c8662863703accf3ad9e5c20e809e63f2e5829b48fb1212f8a4`；scripts_digest `sha256:fa4f2ffa96bcbb4c953d5b8470b4e0927a859647b803cc0788f80b1c76fb305a`。
- install_wave1只COPY wheels/设置PIP_NO_INDEX、PIP_FIND_LINKS，没有recipe/materials/bindings wrapper；冻结原spec getmoto/moto4.1仍make init。**COPY不是安装证据**：G:517、520–559、562–679/N:487、490–529、532–649显示两次editable构建/安装完成和rc0。Makefile:17–19、requirements-dev前两行解释两轮操作。历史导入观测/testbed/moto/__init__.py、4.1.12.dev；metadata4.1.0.dev0来自公开setup.cfg。候选可投影源码与目标分差相符，不只是版本号判断。
- G:689/N:659实际命令`pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`，Python3.12.4、pytest8.3.2。G:695/820为96收集且96pass；N:665/848为96收集、1fail95pass，失败在新增最终manifest断言719。两ledger分别reward1/0，F2P1/1与0/1，P2P均95/95。普通rc1本身不自动赋reward0；本次有具体冻结F2P失败支持。
- 执行节点96、冻结参考96、解析键96分账相同。文本统计覆盖G:724–819、N:752–847完整摘要；这是对原日志字符串的只读统计，不是重新运行项目parser或测试。ledger/diagnostics missing/skipped为空，解析标记外为0。
- policy为rh2grader/54322、2CPU、4GiB、deny_all、64MiB shm、1GiB tmpfs，conda前缀可写；apply_user=agent/54321不是正式actor运行。gold仅投影moto/ecr/models.py、noop空；env_qualification=absent。历史峰值204.816/228.629MiB不代填actor资源pass。driver close无open containers/cleanup failure，但只是一轮既有证据，未重测稳定性。

## 5. 开发条件及交付边界

| 必要操作/资产 | 证据 | 缺口与建议（未执行） |
| --- | --- | --- |
| 导入本地moto、boto3/botocore、pytest/sure/freezegun并编辑Python源码 | setup.cfg:26–38/133的ECR extra无附加依赖；测试imports/requirements；历史工作区导入 | 正式actor实际UID/HOME/PATH/解释器、conda激活、import路径和写权限待验。用public_read C1及原复现核查。 |
| 两份manifest、进程内mock | 包内helper标准库生成；ECR __init__将base_decorator连到backend | 无真实AWS账号、ECR服务、Docker daemon或外部层文件需要；实际TEST_SERVER_MODE=false/mock启动待验。 |
| 窄公开验证 | 原复现、put多标签/同tag/空tag、get/delete公开测试 | 无专用编译，新源码行为测试即可；不要求全仓make test。仅在安装需要时准备构建工具。 |
| 离线候选安装 | 历史image pins setuptools72.1.0/wheel0.43.0/packaging24.1且真实make init成功 | 当前机派生镜像存在性未知、原wheel payload/context未保存；必要时准备阶段重获固定资产。不得假定运行期公网可用。 |
| 提交修复 | gold projection只含moto/ecr/models.py | 官方恢复/保护精确tests/test_ecr/test_ecr_boto3.py；test_globs=()。helper并不因文件名test而自动排除。合法源码修复不受该恢复影响，additional_exclusions=[]。 |

Terraform gitlink未物化但本题所查Python调用不依赖；不据此判环境坏。已识别helper/requirements等非官方恢复依赖可以影响执行，未执行漏洞实验、无证据新增排除。静态base无Git不能证明容器祖先/缓存无答案；实际public_hints投递/真实可見文件/网络限制未验。

历史机制仅用已读冻结`ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`成员文本（未解包、导入或执行）：prepared_task_face.py sha256 `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`，179–212逐官方文件恢复并apply、299–348设test_globs空和public prompt；spec_vendor.py `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`，121–197按test.patch派生命令；swegym_parsers.py `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`，44–56；scoring.py `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`，230–269按冻结参考判分。pinned JSON sha256 `0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`的getmoto/moto4.1项是make init/Python3.12/pytest -n0 -rA。当前ROOT/rh2不是本题历史字节证据。

## 6. 八方面收口与范围

公开需求、材料初态、测试映射、合理替代、gold/旧行为、开发条件、交付评分、关系用途均已写明。题目关系未见已核具体commit/补丁派生，暂不聚类；issue描述回归版本和复现、未给gold代码。审查者已接触隐藏测试、gold及环境摘要，不可作为本题新solver；本轮不是训练/评测批准。

除前述源码，实际读P/public_bundle、base_identity，V/test.patch/gold.patch/grading/validation/run_refs/environment_record全文，environment_replay_inventory仅common/families.install_wave1与本题exact-id对象，未追analysis_reference；读取models.py:1–125、251–367、490–776和responses:49–112、helper全文、测试所列片段、setup/Makefile/requirements/CHANGELOG所列片段。未展开其余95节点全部函数体、其它ECR测试模块、完整mock core传递依赖、在线AWS规范、所有参数组合、真实actor/容器/消息/当前资产、重复稳定性、模型成功率及成本。全部反例与修订仅建议；下一阶段需先获明确history放行。

