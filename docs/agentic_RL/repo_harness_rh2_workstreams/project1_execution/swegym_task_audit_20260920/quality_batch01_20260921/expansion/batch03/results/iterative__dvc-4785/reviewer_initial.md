# iterative__dvc-4785 独立复核初判（封存后不回写）

记录时间：2026-09-20 21:34 UTC / 2026-09-21 05:34 SGT。B3 DVC fresh 独立 reviewer；权威 ROOT=`.`，下列路径相对此根。机器处置 `state=needs_review, scope=static_review`；用途 `development_diagnostic`。

**独立结论：公开HTTP存在性错误成立，gold修好同一状态响应的200/404/403/401主分支，但当前测试不足以确认HEAD→GET回退中的合理旧行为。建议先做状态组合CPU诊断，暂不把原版gold通过等同完整质量合格。** 最重要的新静态疑点是：既有 `_head` 在HEAD和GET都不成功时返回原HEAD响应；因此gold会把HEAD405/GET404从base的False改成抛405，而HEAD404/GET403仍返回False隐藏权限错误。前者是与公开“不把404当错误”及原回退用途相关的回归候选，后者是漏修候选，均尚未运行。

## 阅读与暴露

先读public prompt/bundle/base_identity和base HTTP/HTTPS实现、8项旧测试及依赖入口，再读private全部七份原件。公开environment_brief与本包先前已读版本同SHA `428a617a33ab868848d32d8be9af7b5f53b5fd406c1446005290bf433bb79628`。已见 environment_record 自带gold/noop摘要；独立性指未见主审/历史质量结论，并非无结果盲审。已读另外两题原件/gold，不能再承担它们的公开角色。未读任何题的public_read、analysis_before_history、old_findings_delta、card、screening_record、review或analysis_68；inventory只取common、dvc_install_v1c和本题exact对象。

已读完整test.patch、gold、全部F2P/P2P；追读BaseTree.get_hash/list_hashes_exists、Remote.hashes_exist、BaseOutput.exists/workspace_status、HTTPDependency/HTTPS继承、CLI异常处理、HTTP本地fixture和服务helper。仅静态文件与stdlib文本/哈希；无项目导入、执行、测试、安装、网络或Docker。日志是历史原件复读，不称重跑。逐blob验收复用协调者已验事实。

## 1. 公开目标与合理路线

题面正文重复一遍，重复未增加第二项要求。目标是HTTP(S) remote的exists不要把401/403等错误当文件不存在；成功为True、404为False，其余HTTP错误应向上传递。题面给出 `res.raise_for_status()` 作为“simplest fix”，是显式修法提示，不是必须写出同一函数调用。

公开 `dvc/tree/http.py:98–144` 的request包裹传输异常，HEAD失败后用流式GET回退，exists当前仅对Response求bool，4xx/5xx成为False。`dvc/tree/https.py:6–7`直接继承HTTPTree，故两种scheme共用修复。合理实现可检查最终响应状态并抛库级HTTPError，或调用requests的raise_for_status后适配到DVC异常约定；不需要新依赖，也不必改测试。

## 2–3. 完整断言、参考集与相关旧行为

patch只在 `tests/unit/remote/test_http.py` 后追加28行一个 `test_exists(mocker)`。它创建**同一个**requests.Response，raw赋io.StringIO以便GET上下文close，mock `tree.request` 每次都返回此对象；依次设200、404、403，检查 `is True`、`is False`、`pytest.raises(dvc.exceptions.HTTPError)`。无HTTP真实请求，也没有Mock调用次数/顺序断言。复用同一对象意味着它不能检验HEAD与GET返回不同状态；URL虽是https，但实例仍为HTTPTree，HTTPS继承链仅靠源码推断。

| 公开要求/旧行为 | 依据 | 测试及断言 | 覆盖判断 |
| --- | --- | --- | --- |
| 成功存在 | prompt；base exists bool | 唯一F2P `test_exists`内200→True | 直接覆盖；只测200，无其它成功/redirect组合 |
| 404不存在 | prompt | 同一F2P 404→False，HEAD/GET均为同一个404 | 直接覆盖同状态，不覆盖HEAD受限而GET404 |
| 403应显式报错 | prompt | 同一F2P 403抛DVC HTTPError | 直接覆盖；noop真实失败在未抛异常 |
| 401及其它HTTP错误 | prompt明确401，标题广义statuses | 新测试没有401/5xx | 缺失；只为403抛错的实现静态可过而仍漏401，尚无本轮候选得分实验 |
| HEAD被拒而GET可用时应继续工作 | http.py:130–141 的公开旧回退和4131注释 | 无不同响应/状态组合断言 | 缺失。不能把“mock保留了_HEAD调用”视为回退正确性证明 |
| 下载失败使用库级HTTPError | base `_download:161–164` | P2P `test_download_fails_on_error_code`通过本地http服务404→DVC HTTPError | 覆盖下载入口；不是exists的401或回退验证 |
| auth/SSL/上传method保持 | base _auth_method/_session/__init__ | 其余7 P2P见下 | 有直接旧行为断言，无真实鉴权服务必需性 |
| CLI/缓存把错误与missing区别处理 | BaseOutput:187–203；BaseTree:240–278,615–638；Remote:54–100 | 不在本题执行/参考范围 | 未验端到端；代码能解释错误为何不能静默False |

8 P2P全部通读：`test_download_fails_on_error_code`；public_auth(None)、basic_auth(对象和值)、digest_auth(对象和值)、custom_auth(header/password)、ssl_verify默认True、ssl_verify_disable(False)、http_method(PUT与basic auth)。这些测试没有回退状态矩阵。另读公开 `tests/unit/dependency/test_http.py` 的继承与test_local.py中save_missing，该测试仅mock tree.exists=False，不能新增HTTP错误覆盖；remote_tree通用exists当前只参数化gs/s3，也不能借来充HTTP覆盖。

执行节点9、parser键9、冻结F2P1+P2P8在此题一一对应，没有带空格的参考ID冲突。

## 4. gold、替代解与回归疑点

gold仅改 `dvc/tree/http.py::HTTPTree.exists`：404先False、bool(res)为True则True、否则抛已有 `HTTPError(status_code, reason)`。同状态401/403/5xx静态会报错，200/404按需求；不改request、_head、鉴权、下载/上传，源码可提交，未见未交付依赖。

**回退组合的具体问题（静态，不写成CPU实测）：** `_head`先取HEAD；若非ok，再取GET；仅GET ok时返回GET，否则返回HEAD。gold没有改这一选择逻辑。

| 响应序列 | base exists | gold exists | 解释 |
| --- | --- | --- | --- |
| HEAD405 → GET200 | True | True | 既有fallback正常路径保持 |
| HEAD405 → GET404 | False | 抛DVC HTTPError(405) | HEAD不支持但GET确认missing。gold改变旧False；题面404豁免未明确只针对HEAD，故合理回归疑点较强 |
| HEAD404 → GET403 | False | False | 执行的GET权限错误被丢弃；若要求最终可用方法的错误可见，gold仍漏修 |
| HEAD401 → GET401 | False | 抛DVC HTTPError(401) | 题面明确例子静态得到修复，但没有测试 |

优先核这些不同状态，不能为了保住gold而把它们排除出“HTTP(S) remotes”范围。反过来，也不把任意互相矛盾服务器响应都直接定为高影响缺陷：实际HTTP语义和兼容HEAD禁用的既有意图应由定点实验/需求收口说明。

**异常类型约束保留张力，尚不单独判为确定误拒。** 题面建议直接res.raise_for_status会抛 `requests.exceptions.HTTPError`，而新测试只接受不相关的DVC HTTPError类。这一差异是静态可定位的。不过base同模块_download/_upload已用DVC HTTPError；`dvc/exceptions.py:287–289`把它归于DvcException；`dvc/command/data_sync.py:39,62,83`和`command/status.py:80`只按DvcException走预期错误处理，main.py:88–109将其他异常当unexpected。因此库级异常有公开调用者依据，并非纯隐藏答案名称；裸requests异常会改变CLI处理路径。记录为公开建议与接口约定的解释问题，不宣称所有裸raise_for_status解均合理，也不强求使用gold分支结构。精确message/reason未被test断言。

## 5. 版本与历史运行证据

base=`7da3de451f1580d0c48d7f0a82b1f96ea0e91157`，tree=`1caf710bcefaadc5a3c677b87fd0b6dab0c2ae2e`；grading一致。gold SHA `dd7f46172f65e9cb78279eb3d27caff51e1f8a82b817a5fb0f7f75700b7ed6e3` 与gold ledger:1相符。原运行目录 `runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4785/`：

- noop ledger:1 时间2026-09-19 07:50:53 UTC（15:50:53 SGT）；`noop/eval_logs/...ad440329.eval.log:562–586`是成功安装dvc-1.9.1+7da3de.mod、install_rc0、Python3.9.19/pytest7.4.4/Linux与9个collected；618–621是在403检查 `DID NOT RAISE dvc.exceptions.HTTPError`；630–639为8pass/1fail，rc1，F2P0/1、P2P fail0/8、reward0。
- gold ledger:1 时间07:51:28 UTC（15:51:28 SGT）；`gold/eval_logs/...bd348b66.eval.log:581–605`同样成功安装并执行 `pytest -rA tests/unit/remote/test_http.py`；615–624全部9pass、rc0；F2P1/1、P2P fail0/8、reward1。
- 两者diagnostics reference_missing/skipped为空，parsed=9；导入观察为/testbed/dvc/__init__.py；runner digest未变；cleanup/driver_close记录关闭完成。env_qualification=absent，不能因环境摘要写verified而改成已获正式资格。
- 派生image ID `sha256:2d73ba1750ba6fcb44dfd08fefb39f3c65576f379dcdeb9ea591faee6b113a9b`；scripts digest `sha256:cfc006ac8132ec2f058cfba471e74bc4326012857bc1368c7b427ac5ab0436f9`。policy为rh2grader/54322、deny_all、2CPU/4GiB、shm64MiB、可写testbed解释器前缀；apply身份另为agent/54321。不是正式actor实际CC会话证据。
- 真实安装输入 `recipes/iterative__dvc-4785.json`，以 `pip install -e '.[all,tests]'`替换原安装，保留安装rc；run/recipe属于审计输出。setup.py:48–146,158–169支持这些extras，requests为原依赖。COPY wheels不是安装证明，已核原log成功；目标机器的派生镜像与原wheel/context可用性未验，本地context未保存。

## 6. 开发条件

| 所需操作/资产 | 公开依据 | 证据与缺口 | 最小验证建议（未执行） |
| --- | --- | --- | --- |
| 导入工作区HTTPTree、requests和pytest | setup.py与base http.py | 历史grader成功；actor PATH/激活/工作区import未验 | 实际agent shell记录解释器、UID、dvc.__file__，核候选源文件生效 |
| 纯状态诊断 | 公开函数源码与requests依赖 | 用独立Response对象及request替身即可；无需访问example.org | 在本地隔离脚本调用真实工作区HTTPTree并记录返回/异常类/状态组合，不导入私有测试给solver |
| 旧下载回归 | `tests/remotes/http.py:37–48`、`tests/utils/httpd.py:92–114` | 旧P2P启动localhost动态端口的HTTPServer；有thread，没用外网 | actor窄跑公开test_download_fails_on_error_code，确认loopback监听/连接许可 |
| 所需环境准备 | tests/conftest导入remotes；setup extras | 包导入面较广，但本题9测试不需Docker/云凭证/真实外网服务 | 准备阶段固定依赖和本地helper；不泛开放解题网络 |

写入仅非测试业务文件；不会要求提交系统包、下载私有资产或修改会被官方恢复的源码。public_hints的“conda已激活”与禁改测试解释仍须核实际消息，不拿它当成功事实。

## 7. 投影、官方恢复与计分

历史机制只读冻结dvc.tar.gz成员文本；共享调用链身份同本包前两初稿：replay adapter `031046ba444e26a91643ce988c3855e80acb1b4cf90408235d61ff35d87fb896`，face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`，spec_vendor `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`，projection `5ef126803e93e3606123a4aef4389d35bad0551a622020d1dd22f0db32224a60`，scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`，parser `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`。没有解包写盘、导入运行或用当前ROOT/rh2冒充历史。

本题official精确路径仅 `tests/unit/remote/test_http.py`；test_globs=()，不是所有测试全排除。trusted_setup原diagnostics恢复1文件、apply_rc0、保护1文件；gold投影included仅dvc/tree/http.py，ignored为空。计分按标记段解析+冻结F2P/P2P；此题完整pytest失败恰与参考失败一致，但不推广成rc1必reward0。共享conftest/pytest配置控制面未全排除问题不在本轮另造攻击，也不据此增加exclusions。

## 8. 跨题关系、用途与唯一下一步

三题业务故障不同，不能因同仓或使用相同安装家族合并为同题。实际跨版本线索：本题公开base `dvc/config.py:385–399` 已含3665 gold的 `_to_relpath`/partial/as_posix 逻辑，属明确的先前修复进入后题可见base；6954公开base又保留同接口但仅相对路径正规化。以后模型任务若共用历史上下文，需记录这一可见线索；本次reviewer本就已见三题gold，产物只作development_diagnostic。6954的HTTP实现已换到FSSpecWrapper/aiohttp（base dvc/fs/http.py），不能仅靠后来文件名推断4785 gold完整性或同问题。

唯一优先实验（建议，未执行）：给base与gold的真实HTTPTree.request输入**独立HEAD/GET Response**，运行上述四组状态组合，并加共同200/404/403控制；记录每次返回值、异常类及状态，再对应原RH29项得分。优先确认HEAD405→GET404的回归和HEAD404→GET403的漏修，决定是否需要修订gold/test；原test.patch/ref/reward保持不动。先验明目标镜像、配方与角色入口，不用重读旧日志充作新CPU结果。无新候选/修订/实验已经执行的声明。
