# iterative__dvc-4785：读历史前的独立私有分析

本稿先于本题 history/refs 与旧质量记录保存；此时未读它们、reviewer 或批次聚合。已读本题 public_read.md；观点仍逐项返回原件。本轮仅静态文件/历史 Git 导出文本及 stdlib 元数据分析，没有运行项目、测试、安装、容器或模型。以下命令均是建议。用途仅 development_diagnostic，状态 needs_review / static_review。

路径简写：P=`runs/swegym_quality_batch03_20260921_v1/public/iterative__dvc-4785`，V=同层 `private/iterative__dvc-4785`，E=`runs/env_recipe_repair_20260919/dvc_install_v1c`；所有路径相对 `${REPO_ROOT}`。源码行号指 P/base 的指定 base，日志行号指 E/tasks/iterative__dvc-4785 下原件。未以当前 ROOT/rh2 代替历史运行源码。

## 暂定判断

原问题真实、固定 grader 的 gold/noop 分差可信；但需保留两项语义问题。公开题面直接建议 `res.raise_for_status()`，新增唯一 F2P 却要求 `dvc.exceptions.HTTPError`，使直接采用 Requests 异常的合理路线有被拒风险。仓库 download/upload 已用 DVC 异常，提供相反的惯例证据，不能只凭异常名不同直接判测试无效。其次，公开明确点名的 401 没被新测试覆盖，针对 403 的局部修复可能过关。二者目前是源码可定位的静态推断，不是已运行反例。本题暂不作为无争议的 actor probe 候选。

唯一优先下一步：在后续获准的固定环境，用保留原 `_head` 的直接 `raise_for_status()` 合理候选，做 200/404/403/401 的窄公开行为与冻结 RH2 评分差分；记录抛出的异常类型及 CLI 行为，再判定精确异常类是否误拒。不要先改 expected、公开题面或测试，也不要求全仓门槛。

## 1. 公开需求与材料身份

P/user_prompt.txt:3–10 重复了同一 issue：HTTP(S) exists 不应把 403/401 当作不存在，成功仍为真、404 仍为假；建议调用 `res.raise_for_status()`。重复段落不增加目标。没有要求异常文案、状态属性、内部 helper 或指定异常类。P/base/dvc/tree/http.py:130–144 的 `_head` 在 HEAD 不成功时尝试 streaming GET，只在后者成功时替换响应；`exists` 直接 `bool(response)`，把最终错误响应折成 False。`dvc/tree/https.py:1–7` 继承同一实现。公开调用者 `dvc/tree/base.py:240–278,615–638` 将 False 转为缺失/从存在对象中过滤，说明静默 False 的业务影响。

精确 base=`7da3de451f1580d0c48d7f0a82b1f96ea0e91157`，tree=`1caf710bcefaadc5a3c677b87fd0b6dab0c2ae2e`。沿用父任务身份验收：465 个跟踪 blob 已导出，无 symlink/gitlink/LFS 未实体项，不重验全树。V/grading.json 与 public base 一致；test.patch 987 bytes SHA256=`e043ab2074affb0c5ecfb9e7425fec399a3ed41525ded8d8fcb24b17413e8bdc` 与 grading 内嵌 test_patch 一致；gold.patch 544 bytes SHA256=`dd7f46172f65e9cb78279eb3d27caff51e1f8a82b817a5fb0f7f75700b7ed6e3` 与 validation 内嵌 gold 和 gold ledger 候选一致。source_refs 的来源均为本题精确第 135 行；不展开邻题。

公开包是静态导出，P/environment_brief.md:3–12,20–26 已明确 actual messages、shell 激活、工具和 actor 权限待验。bundle 的旧 public_hints 禁止改测试与“全部测试恢复”措辞不能当现行机制事实；本题合法源文件修复不需要修改测试，不因该共享输入疑点判题失效。

## 2. 需求—断言双向映射

全部新增测试只有 `tests/unit/remote/test_http.py::test_exists`，即 F2P=1，但内部有三项行为断言。读完 V/test.patch:1–35、base 同文件全部 127 行及必要 fixture。其 `HTTPError` 来自 base 测试第 3 行的 `dvc.exceptions`。

| 公开要求/合理旧行为 | 依据位置 | 测试与决定性断言 | 覆盖判断 | 执行证据/限制 |
| --- | --- | --- | --- | --- |
| 成功响应仍存在 | prompt:6；http.py:143–144 | test_exists：Response 200，`is True`（patch:27–28） | 覆盖一个状态 | gold/noop 均越过此断言 |
| 404 表示不存在 | prompt:6 | 同 F2P：404，`is False`（30–31） | 覆盖 | gold/noop 均越过此断言 |
| 403 不能静默缺失 | prompt:6 | 同 F2P：403 必须抛 DVC.HTTPError（33–35） | 行为覆盖、类型有争议 | noop 原日志:618–623 恰在未抛异常失败 |
| 401 不能静默缺失 | prompt:6 明确点名 | 没有 401 断言 | 缺失 | 只对 403 抛异常的分支路线可漏401；未运行 |
| 其它失败状态不应一律 False | prompt 的 HTTP statuses/raise_for_status 建议 | 没有500等状态 | 部分 | 不为未约定重定向细节扩张要求 |
| HEAD 不支持而 GET 成功仍可判断存在 | http.py:130–141 旧行为 | F2P 对所有 request 返回同一 Response | 未覆盖分支组合 | 同 mock 不能证明 HEAD405/GET200 等差异响应 |
| 下载错误采用现有 DVC 异常 | base test_http.py:7–11、http.py:161–177 | P2P test_download_fails_on_error_code，missing.txt 抛 DVC.HTTPError | 覆盖原下载路径 | 两次日志捕获本地 GET 404；不是公网失败假通过 |
| public/basic/digest/custom auth、TLS verify、HTTP method 保持 | base test_http.py:14–127 | 其余7个 P2P 检查 auth对象/headers、verify True/False、method PUT | 覆盖配置级旧行为 | 共8 P2P全过；没有实际TLS/远端认证交换 |
| HTTP与HTTPS沿公共实现一致 | https.py:1–7 | F2P 用 https URL但实例是 HTTPTree，request 被 mock | 静态共享，端到端未测 | 不声称已测HTTPS子类派发/TLS |

反向核验：200/404 的严格 bool 返回有旧 API 依据；异常文案不被断言。异常类是唯一额外可疑约束，没有强制 gold 的分支布局或 helper 名。DVC.HTTPError 仅继承 DvcException（dvc/exceptions.py:287–289），与 Requests.HTTPError 不是同一类。题面直接建议的原生 Requests 异常路线，即使正确区分 403/401 与缺失，按该断言预计仍被拒。另一方面，同模块 download/upload 已抛 DVC.HTTPError（http.py:170–171,198–200），dvc/main.py:88–109 对 DvcException 友好处理、一般 Exception 输出 unexpected-error；这是保留该类的合理产品动机，但公开是否必须采用它尚需独立判断。

F2P 使用一个 requests.Response，在 200→404→403 间改 status_code；为 fallback 的 streaming GET 手工置 raw=StringIO，mocker.patch.object(tree, request, return_value=res)。不访问 example.org，不检查请求方法/次数，也不能单靠它验证重试、认证或 HEAD/GET 差异。存在检测同样可在 existing `_head` 返回后统一处理；无需写死测试 URL/状态403，亦无需改调用者。

## 3. 原始运行：执行、解析与计分各自计账

精确入口是 V/run_refs.json：gold/noop ledger.jsonl 均第1行；日志分别 `gold/eval_logs/evallog_replay-er19-dv1-iterativ_bd348b66.eval.log` 与 `noop/eval_logs/evallog_replay-er19-dv1-iterativ_ad440329.eval.log`。已读两账本/diagnostics 全文与原日志初态 diff、注入、安装关键行、完整测试段/失败体/summary。不是根据 environment_record 的标签反推执行。

| 条件 | gold | noop |
| --- | --- | --- |
| 实际命令 | `pytest -rA tests/unit/remote/test_http.py`（600） | 同命令（581） |
| 实际 collected/完成 | 9/9；9 passed（605–624） | 9/9；1 failed、8 passed（586–639） |
| F2P/P2P 冻结引用 | 1/1、8/8 | 0/1、8/8 |
| parser 项数/段外 | 9/0 | 9/0 |
| 缺失/跳过引用 | 空/空 | 空/空 |
| reward/测试RC | 1/0 | 0/1 |
| installRC/失败命令 | 0/空 | 0/空 |
| 安装/测试阶段秒（ledger） | 6.957/6.81 | 6.581/7.669 |
| mem_peak MB | 293.578 | 435.199 |

本题实际执行9、解析9、冻结计分9恰好相等，不能通用混同。按冻结 archive 的标准 SWE-Gym parser 规则做纯文本 token 元数据分析，正好还原各9个 nodeid及状态，全部与冻结参考对上，无参数空格截断/业务日志伪ID。历史 `src/repoharness2/envpack/scoring.py:240–309` 只在 Start/End test segment 解析并按 F2P/P2P 计算；普通完整pytest的非引用失败不自动等于reward0。本题没有额外非引用测试，但回归建议将来若另执行，必须另记，不偷偷并入分数。

noop 初态不是干净 base：日志:132–174 表明 setup.py 把 moto==1.3.14.dev464 改为1.3.14；gold:132–193 同改，另有与 gold 相同的 http.py 差分。该依赖改动不包含目标修复，两角色相同；不能以 `.mod` 推断 gold未装或污染为已修。两个测试段都在 Python3.9.19/pytest7.4.4；noop 是200/404断言后403未抛DVC异常，确实对应问题。

## 4. gold 与相关回归

V/gold.patch:7–14 只改 exists：404→False；bool成功→True；其余抛 DVC.HTTPError(status,reason)。不改依赖、认证、session、_head或测试。静态上 401 和其它最终错误响应也得到异常处理，超过唯一403样例；本题未有实测401。gold/noop 对照支持当前三断言与8项保留行为，不能证明所有 HTTP 状态组合、客户端/CLI 行为。

沿 `BaseTree.get_hash`、`list_hashes_exists` 和 `dvc/remote/base.py:54–100` 追读：False原来被当缺失，抛错可让权限/认证失败不再静默消失。`tests/unit/dependency/test_http.py:1–7` 复用 common dependency；`test_local.py:1–20` mock exists=False，只覆盖缺失；`tests/func/test_import_url.py:118–141` 涉 HTTP fixture 的既有导入/状态回归不在冻结引用，也未执行。本轮不据此写“无回归”。

_head 原有策略在 HEAD/GET 都失败时返回原HEAD响应，例如 HEAD404/GET403仍取404、HEAD403/GET404仍取403。这是 base既有行为，gold未触碰；公开没有规定冲突响应优先级，暂不判 gold 漏修，也不私自把偏好的策略加入验收。保留 HEAD失败→GET成功的既有能力是合理窄回归；优先差分可同时记录它，但不机械扩成全仓测试。

## 5. 开发条件：固定 grader 已有证据，actor 仍待验

从 batch03/environment_replay_inventory.json 只提取本题对象、common及families.dvc_install_v1c。输入配方为 E/recipes/iterative__dvc-4785.json，不是逐run的recipe审计输出。已读安装 wrapper `E/replay_with_install_recipe.py:61–86`：仅精确替换原安装串到 eval_script/candidate_test_script 各一处并保存前后及digest；本题 compat=[]，无额外trusted setup补片。

配方 `python -m pip install -e '.[all,tests]'` 后以 `python -I` 记录 metadata版本并返回原install_rc。公开 setup.py:48–186 确有 all/tests extras、requests、pytest-mock、RangeHTTPServer等需要。Dockerfile仅COPY wheels并设置PIP_NO_INDEX/PIP_FIND_LINKS，不能证明安装。本题消费证据则是 gold原日志:373–376,570–590 与 noop:354–357,551–571，实际重建editable、卸载原DVC、成功安装1.9.1+7da3de.mod且RC0；ledger 观测 import=/testbed/dvc/__init__.py。当前机未重建，历史wheel/context payload不在本地，不能保证迁移后仍可装。

此 fixed grader 为 rh2grader/54322、candidate apply记录为agent/54321，prefix owner54322，`env_qualification=absent`、install probe absent。实际image=`sha256:2d73ba1750ba6fcb44dfd08fefb39f3c65576f379dcdeb9ea591faee6b113a9b`（local_build），来源期待digest=`sha256:5709713b2fe48c8ccb75d72cedccb4853e332e928fe5223fab06959c3be7509c`。两者区别已记录，不能将前者换称原公共镜像；scripts digest=`sha256:cfc006ac8132ec2f058cfba471e74bc4326012857bc1368c7b427ac5ab0436f9`。双侧2CPU/4GiB/PID512/shm64MiB/tmp1GiB/deny_all。运行未显示OOM/超时/安装错误；只各一次，不声称重复稳定或并发保证。

公开开发需读写/testbed、home/temp、测试临时Git/DVC目录；必要解释器/pytest/mocker和本地 HTTP 服务端已在grader工作，但actor实际PATH/激活/安装prefix权限未验。tests/conftest.py:5–33 导入通用fixture及autouse清理；tests/dir_helpers.py:80–121,259–316 构建临时目录/仓库；tests/remotes/http.py:1–48、tests/utils/httpd.py:1–114 的本地HTTPServer绑定127.0.0.1随机端口，线程与关闭行为已读。外网无必要：F2P全mock，P2P下载为loopback404（gold:612–613；noop:627–628），auth/TLS为配置断言。正式actor是否可bind/读包/运行公开测试仍需本题身份CPU资格验证；此处未执行。

建议开发命令仅列最相关的 `python -m pytest -q tests/unit/remote/test_http.py`（actor公开base没有私有test_exists）及公开要求驱动的受控状态复现；无需运行全部远端集成/容器。预置包构建是否需要额外工具属于准备阶段；普通业务修复无新增编译、权重或公网资产需求。环境不确定性不能误记为题目无解。

## 6. 交付、官方恢复、泄漏与用途

历史运行代码来自既有 `runs/env_recipe_repair_20260919/frozen_sources/dvc.tar.gz`，只用tarfile读取成员文本，未解包/导入/运行。沿用已读 `src/repoharness2/adapters/slime/prepared_task_face.py:185–234,304–338` 的profile分段及官方恢复行为；本题只保护/恢复 `tests/unit/remote/test_http.py`（已存在），不含普通源码。日志 gold:194–202、noop:175–183 恢复后应用官方patch成功；diagnostics各expected1/protected1/missing0。gold投影只含dvc/tree/http.py，noop空；此合法路径不被恢复覆盖。不能把完整eval_script审计副本误当实际profile唯一入口。

补充实际阅读的历史成员及身份：`src/repoharness2/envpack/scoring.py` SHA256=`b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`（文档/字段、v2解析与outcome至309的相关片段）；`src/repoharness2/envpack/swegym_parsers.py` SHA256=`995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`（全部111行，44–55解析、93 DVC映射）。vendor commit=`242429c188fcfd06aad13fce9a54d450470bf0ac`，ledger grader=`swebench-4.1.0+swegym_parsers@242429c1`。只证明这些历史路径对当前两份原日志的解释，不给当前ROOT/rh2或未知actor背书。

未实测攻击、实际actor可见挂载/Git refs/缓存或网络隔离，不写安全已过。公开base不含.git并不证明真实容器没未来对象。官方单文件保护及runner integrity未变仅为已引用条件的证据；没有题目特有的新增排除依据，additional_exclusions=[]。未查跨题重复/同修复派生，不凭同仓同文件建立关系。

已见公开稿、隐藏test/grading、gold/validation、环境结果摘要、真实两角色日志/账本/diagnostics与历史harness源码；后续还将获准读本题旧记录。本上下文不能充当solver，也不能把本稿给solver。没有真实模型轨迹，不推断基座成功率、训练价值或正式准入；token/费用未知填null。历史环境摘要已如实使用，其质量/analysis指针未追读。

## 7. 八方面覆盖与边界

公开需求：题面、提示、源码调用者及旧测试已查，实际消息待验。材料与初始问题：身份沿用验收并核局部patch与原日志，原bug成立但共享setup改动存在。测试是否测到要求：全部新增断言、1F2P、8P2P与fixtures已读并对账；401缺口明确。误拒合理解：精确DVC异常与公开raise_for_status路线冲突待窄差分及独立复核。回归/gold：改动与相关调用链已读，端到端与HEAD/GET组合未运行。开发条件：固定grader安装/权限/loopback有原件，正式actor和迁移未知。交付评分边界：已核单官方路径、投影、历史parser/参考命中；控制面攻击与实际可见材料未验。题目关系用途：未做跨题关系调查，仅development_diagnostic，reviewer未开始；无题面/测试/参考修订。
