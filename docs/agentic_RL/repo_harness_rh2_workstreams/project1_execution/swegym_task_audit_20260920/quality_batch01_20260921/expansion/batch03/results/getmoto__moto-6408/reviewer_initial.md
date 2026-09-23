# getmoto__moto-6408 独立初判（封存后不回写）

`needs_review` / `static_review` / `development_diagnostic`。在任何本题 public_read、主审初稿/delta/card/record、旧质量结论之前保存。全部结论来自静态源码、原始日志和stdlib文本/JSON/hash核对；未执行项目代码、测试、安装、网络、Docker或模型。

ROOT=${REPO_ROOT}；I3=ROOT/runs/swegym_quality_batch03_20260921_v1；IW=ROOT/runs/env_recipe_repair_20260919/install_wave1。下文 base 路径均指 I3/public/getmoto__moto-6408/base。

初判：问题、base、新增F2P相符，gold确实处理题面“两个manifest预先存在”的移动标签序列，历史真实RH2证据也支持此点。但测试只取第一个查询结果，没有证明标签唯一或旧镜像仍可访问；gold的“新manifest”分支保留了追加后再全局删标签的顺序，存在把新镜像删掉的静态路径。建议先做一个窄的状态语义诊断，再决定是否将此题作为完整标签移动诊断。没有发现新测试强迫gold内部实现或新增隐藏接口。

## 暴露与版本

已读共用四份方法卡；本题 user_prompt/public_bundle/base_identity/environment_brief、test/gold patch、grading/validation/source_refs/run_refs/environment_record；inventory只取common、install_wave1和所分配三题exact项。environment_record 自带 verified_environment_pair、gold/noop奖励/退出码摘要与history运行指针，已暴露，不能称“无结果盲审”；未追 analysis_reference/analysis_149，未读本批聚合、旧质量结论、其它题或任何主审/公开读者稿。

base=`1dfbeed5a72a4bd57361e44441d0d06af6a2e58a`，tree=`4d46b90dfbe69f5b7468a662b4dc237fbe9f513b`，public/grading身份一致。base_identity记录内容/OID/mode/path核验；无.git，Terraform子模块未物化且不在本题调用链。精确选取原prepared本题项canonical SHA=`a5fbcc1af636312671aefd9a5d789685ad6795da43729949ba4b0baf424e651a`，原host_grading_views第94行raw SHA=`b06e24704af3b1b9252775bfb047ab4920239ff5a4e929f517c1320f352a8a88`；其中grading与本题冻结JSON相等。gold.patch与validation字符串、test.patch与grading字符串分别相等；gold SHA=`fa6d9adadc553b4eb713ca3749a90efe7adb572348c837fd2bbf48a3dd95d7dd`也被历史候选账本引用。

## 公开目标与全部新增断言

题面描述4.1.11 ECR回归：已有标签指向多标签镜像时，put_image应把标签移到指定manifest；给出两manifest先各有独立名称，再将mock-tag从image_001移到image_002的复现。公开代码里的 `_create_image_manifest` 未在题面定义，但base测试import可定位 tests/test_ecr/test_ecr_helpers.py:31–44；无需读隐藏补丁才能补齐复现。预期是服务端标签状态一致，不能只让查询顺序变化。

| 公开目标/旧行为 | 依据 | 断言/覆盖 | 判断 |
| --- | --- | --- | --- |
| 原序列移动tag后返回第二manifest | 题面复现；ECRBackend.put_image:570–621 | 全部F2P仅 `test_multiple_tags__ensure_tags_exist_only_on_one_image`：第一次batch_get第一项manifest等于image_001；移动后第一项等于image_002 | 覆盖题面核心序列；比题面initial!=new更精确，属于公开目标 |
| 标签唯一，旧镜像其它标签不丢失 | 题面多标签；base put_image:602–603“Tags are unique”注释；旧multi-tag/delete行为 | F2P两次都是 `image, *_`，不验len/failures/旧独立tag或两个digest | 明确漏测；不能用函数名“only_on_one_image”代替断言 |
| 目标manifest尚不存在也应移动标签 | 公开put_image一般行为；base已有新manifest分支与P2P test_put_multiple_images_with_same_tag | 旧P2P只覆盖源镜像单tag；F2P只覆盖目标已存在 | gold静态路径有缺陷，需窄实证；不是题面原复现失败的已跑结论 |
| 同manifest多标签保留且可按任一tag查找 | 旧tests:465–502、1108–1135 | P2P精确保留v1/latest和两tag查询manifest一致 | 覆盖通常加tag，不覆盖移动过程的旧tag保留 |
| 相同manifest相同当前tag应报ImageAlreadyExistsException | 公开旧test:549–581 | P2P保护code/message/HTTP400及镜像数1 | gold保留该分支；非当前tag重复提交未直接覆盖 |
| 删除一个tag与最后一个tag/digest删除区别 | 旧tests:1139–1211、1257–1301、1368–1452 | P2P保护多标签删一个、最后tag删镜像、digest删整镜像、组合不匹配 | 单独delete行为覆盖；不能证明put复用delete时顺序正确 |
| 无tag、manifest list、显式mediaType | 旧tests:354–424、663–778、808–864 | 相应P2P都参与评分且完整读关键路径 | 已保护常见旁路；非默认IMMUTABLE行为test只验证配置切换 |

test.patch仅新增这一个函数，无改删旧断言、无新fixture。完整读全部49新增行（包括装饰器、两次创建、两次移动/查询、两条manifest断言与digest字段索引）。完整读 helper `_generate_random_sha`、`_create_image_layers`、`_create_image_digest`、`_create_image_manifest` 及manifest_list helper；全部为本地随机数据，无外部镜像仓库或网络。两个manifest由5层随机size/digest生成，历史实际输出不同；未实测稳定性，不把随机生成本身判失败。

冻结P2P名单95项全核；**实际展开函数不是95个全读**。完整展开的相关旧函数：test_put_image、test_put_image_without_mediatype、test_put_image_with_imagemanifestmediatype、test_put_manifest_list、test_put_image_with_push_date、test_put_image_with_multiple_tags、test_put_multiple_images_with_same_tag、test_put_same_image_with_same_tag、test_list_images、test_describe_images、test_describe_images_by_tag、test_describe_images_tags_should_not_contain_empty_tag1/2、test_batch_get_image、test_batch_get_image_that_doesnt_exist、test_batch_get_image_with_multiple_tags、test_batch_delete_image_by_tag、test_batch_delete_image_delete_last_tag、test_batch_delete_image_by_digest、test_batch_delete_image_with_matching_digest_and_tag、test_batch_delete_image_with_mismatched_digest_and_tag、test_delete_batch_image_with_multiple_images、test_put_image_tag_mutability；另外展开create_repository默认/非默认配置。其余只核参考名及原日志状态，未穷举scan/policy调用者。

## 源码、gold与合理替代实现

完整读models.py中的Image构造/response/remove_tag/update_tag、Repository._get_image、ECRBackend.put_image/batch_get_image/batch_delete_image/list_images/describe_images/put_image_tag_mutability，responses.py:55–109的API接线。

base在已有manifest分支只 `image.update_tag`，未移除旧镜像上的相同tag；batch_get_image:646–656遍历所有匹配镜像，原序列因此返回两个，旧镜像排第一。gold将已有tag搜索改为 `image_tag in x.image_tags`，并在更新已有manifest前调用batch_delete_image。这与题面核心因果一致，未要求唯一内部helper名。

剩余具体路径（静态推断，未执行）：源镜像A tags=[unique_A,moving]，新manifest B尚未放入repository。put_image:591–607先append B(tags=[moving])，再batch_delete_image。delete:716–755遍历repository.images，A有多个tag故只移除moving、A仍在；遍历继续到B，B仅一个tag于是把B删除。put_image仍返回脱离列表的B对象，后续batch_get(moving)将无镜像。这对“moving是A当前tag”在base已存在；gold改为所有tag匹配后，也使非当前tag走该删除路径。不能一概称gold新引入所有情况，但足以质疑覆盖完整性。

另一个评分弱点：只改batch_get_image迭代顺序使新镜像排前、仍保留两个镜像上的moving，静态上可能通过新增两个断言；或者移动时删除整个旧多tag镜像，新增F2P也未检查unique_A丢失。是否实际取得reward需CPU确认，本轮没有跑候选，不将推断写成已验证漏洞。

合理替代解可以在指定目标镜像更新/创建前，只从其它镜像移除该tag，按既有最后tag规则处理旧对象，再更新目标；不必调用batch_delete_image，也不必改变查询排序。现有断言主要检查外部行为，未发现该路线遭私有helper/Mock形状误拒。对digest算法、IMMUTABLE完整服务语义等base既存限度仅记录边界，不扩大本题修复目标。

## 运行原件与评分账

精确原件：IW/tasks/getmoto__moto-6408/{gold,noop}/ledger.jsonl第1行、driver.log、image.json、status.json，逐题plan项。gold eval=`evallog_replay-er19-iw1-getmoto__8717daf0.eval.log` SHA=`1b7a13f1d42bf6113b86e94c2a2a1087c5e79c8d44f8041e37febf25d67bcb19`；noop eval=`evallog_replay-er19-iw1-getmoto__0fdceeeb.eval.log` SHA=`e2119781fba36b80a209e8c50be45c6a7043d44823a7b15935239a1fa2d1555e`；重算与run_refs相同，两个ledger文件SHA也相符。

| 层次 | gold | noop |
| --- | --- | --- |
| 原命令 | 日志689：pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py | 659同命令 |
| 实际节点 | 695收集96；820摘要96 passed | 665收集96；848摘要1 failed,95 passed |
| 初始失败语义 | 新增F2P通过（744） | 719–725第二manifest等式失败，不是导入/安装异常 |
| 解析键/冻结参考 | 96键；F2P1/1、P2P95/95 | 96键；F2P0/1、P2P95/95 |
| 退出码/奖励 | RH2_TEST_RC=0（824）；reward1 | RH2_TEST_RC=1（852）；reward0 |
| 安装证据 | make init517；两轮build deps done521/563，build+install553/559、670/676，末码0 | make init487；done491/533，build+install523/529、640/646，末码0 |

另以stdlib逐行核PASSED/FAILED摘要：两日志各96行、96个按split()[1]得到的键，95 P2P全为PASSED、无缺失；没有把全部函数体当已读。历史baseline.tar.gz内 swegym parser实际按空白切键（成员名为src/repoharness2/envpack/swegym_parsers.py:44–56），本题现有参数名不产生重复键；scoring.py:189–271只消费marker内状态及冻结F2P/P2P，不以全部pytest退出码作为奖励同义词。

历史harness只通过tarfile.extractfile只读成员：scripts/replay_grade.py、src/repoharness2/adapters/slime/{replay_grade,prepared_task_face}.py、envpack/{spec_vendor,swegym_parsers,scoring}.py与specs JSON的getmoto/moto4.1项。未解包、import或执行。common所列前四成员hash已核匹配；原spec install=make init，python3.12，test_cmd=pytest -n0 -rA。install_wave1无recipe/materials/binding覆盖。

## 开发条件、交付与用途

本题原image.json/pins：setuptools72.1.0、wheel0.43.0、packaging24.1；COPY wheels与PIP_NO_INDEX/PIP_FIND_LINKS只是准备方式，安装结论依上述原日志，不能靠Dockerfile代替。派生image=`sha256:9ea5a5f571d9feda40bda0d0be2c1242c409a457c7ff38827deb9b937a4e85c4`，base image=`sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689`，scripts_digest=`sha256:fa4f2ffa96bcbb4c953d5b8470b4e0927a859647b803cc0788f80b1c76fb305a`。status.json保存最后gold的原/work命令，noop有launcher生成规则和原日志，不能声称status捕获两次命令。

历史policy原字段：user=rh2grader、uid54322、cpus2.0、memory_bytes4294967296、pids_limit512、shm_bytes67108864、tmpfs_bytes1073741824、network=deny_all、candidate_writable_prefixes=[/opt/miniconda3/envs/testbed]；candidate apply_user=agent/54321。resource.mem_peak_mb gold204.816/noop228.629、resource_facts=null，保留原字段不改单位。导入观察/testbed/moto/__init__.py、版本4.1.12.dev；安装元数据4.1.0.dev0另账，不据显示差异推翻已核base。env_qualification=absent，driver关闭无残留/cleanup_failures；这些不是正式actor资格。

| 开发需求 | 公开入口/依据 | 证据与缺口 | 未来最小验证 |
| --- | --- | --- | --- |
| 定位、改源码并验证生效 | moto/ecr/models.py、responses；题面helper可从旧tests定位 | 普通Python改动，可交付；actor解释器/工作区来源未验 | actor实际shell检查UID/cwd/python/moto.__file__ |
| boto3/mock_ecr/pytest依赖 | Makefile17–19、setup.cfg26–38、requirements-dev/tests、contributing安装文档 | 历史grader make init成功；actor PATH/激活/可写安装待验 | 窄跑旧test_put_image_with_multiple_tags与公开复现 |
| manifest数据/服务 | helper全在base，本地生成manifest字符串 | 不需拉容器镜像、访问AWS或ECR；历史deny_all也可跑 | 使用固定两个不同manifest、虚假AWS凭证与明确region复现 |
| 原运行可重放输入 | inventory+status | 当前原prepared仍指/work、镜像可用性与原wheel payload均待准备 | 另建重定位副本、验证镜像身份/归档code-root；本轮不动 |

正式actor验收是后续模型开发门槛，不是本项固定grader语义CPU诊断的自动前置；不能把grader通过写成actor通过。public_hints的NON-TEST限制不阻碍本题业务源码修复；实际消息注入/已激活宣称待核。官方test.patch仅tests/test_ecr/test_ecr_boto3.py，该文件由prepared_task_face:306–331恢复/保护，test_globs=()；gold models.py在projection.included_paths，ignored_paths空。没有修改tests/gold/评分，未补额外排除路径。未做真实镜像答案资产/整个隔离验收；未查其它题以构造重复簇，不从同仓推断题目关系或模型学习价值。

八方面已逐项处理：公开需求；材料/初态；全新增断言/F2P和相关P2P；误拒/替代解；gold/调用者回归；开发条件；交付与parser；关系/暴露用途。全仓及所有合理实现仍未检查。

优先未来实验：同一个绑定历史条件的CPU诊断，固定A/B manifest，先复现题面序列并检查moving唯一、unique_A仍可查，再令B起初不存在重复移动，核put返回、batch_get与describe的一致性。先验证具体gold缺口；如要确认评分漏测，再单独设计有因果目的的部分实现，不强制双候选。保留needs_review，不将静态推断当实跑或训练/正式评测批准。
