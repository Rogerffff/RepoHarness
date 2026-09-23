# getmoto__moto-7584 — reviewer_initial

日期：2026-09-21。独立 reviewer 第一阶段；尚未读取公开读者、主审、本题旧质量结论或 history 目录。已见授权私有原件 environment_record.json 中的批次 history 引用字段，未跟读其汇总。三题全保存后等待协调者整包封存，不提前进入第二阶段。

## 初判

建议 `needs_review / static_review`，用途 `development_diagnostic`。发现具体的公开目标—gold—测试不一致，不能凭历史 gold=1 认定题意已对齐。最重要的问题是公开原例“成功订阅→删除端点→再次订阅”仍会在 gold 中成功返回旧订阅；隐藏 F2P 删除了首次订阅这一步。另有错误字符串对合理实现的潜在误拒。尚未执行 CPU 反例或真实模型。

本报告路径缩写：`P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-7584`，`Q=…/private/getmoto__moto-7584`，`E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-7584`；`ROOT=.`。以下 base 文件均在 P/base。

## 公开目标、初态与断言映射

base 为 `cc1193076090f9daf90970db286b6b41581dd8bc`，tree 为 `63d237e03a2a4e7fbc31e324013809e31565e6bd`。公开目标是 application 协议订阅不存在的 SNS 端点时抛 InvalidParameterException，原例明确先成功订阅一次。问题不是一般 publish 失败；新增测试名虽含 publish，实际调用 subscribe。S2 精确 public/grading/validation 行均为 source_refs 指定的第 110 行，身份对应；不重新做整包 blob 核验。

| 要求或回归 | 公开依据 / 已读实现 | 新改断言或参考测试 | 判断 |
| --- | --- | --- | --- |
| 不存在端点的新 application 订阅应失败 | user_prompt；models.py:502 的 subscribe 原来直接创建 Subscription | 唯一 F2P test_publish_to_deleted_platform_endpoint：创建端点、删除、首次 subscribe；pytest.raises(ClientError) | 覆盖这一负例；noop 原始日志 619–622 行 DID NOT RAISE |
| 公开原例删除已订阅端点后再次订阅失败 | user_prompt 的两次 subscribe；models.py:515–517、538–548、714–718 | F2P 没有第一次 subscribe | 缺失且 gold 漏修：delete_endpoint 只删 platform_endpoints，不删 subscriptions；gold 检查插在旧订阅提前返回之后 |
| 错误类型/Code | exceptions.py:45–49 的 SNSInvalidParameter→InvalidParameter；responses.py:221 起直接委派 backend | F2P 断言 Error.Code == InvalidParameter | 与公开类型目标一致，不约束内部实现 |
| 错误 Message | 公开文案为 “…for endpoint {endpoint_arn}” | F2P 精确等于 “…for endpoint arn{endpoint_arn}” | ARN 自带 arn:；测试额外要求 arnarn:。gold 注释称 AWS 如此，与题面报告来源不同；本轮不验证远端真值 |
| 有效端点应可订阅，其他协议继续工作 | 公开原例第一步；公开 test_subscriptions_boto3.py 的 SMS、SQS 幂等、HTTP 正常订阅 | 19 个 P2P 全在 test_application_boto3.py；它们没有有效 application subscribe | 这一正分支未保护；一概拒绝 application 的自然但不完整实现静态预计也能过本题参考集，未执行 |
| 应保留应用/端点 CRUD、重复端点、属性、直接 publish、禁用端点、SMS 属性 | test_application_boto3.py 全文 1–492 | 所有 19 个 P2P 正文均已读 | 历史全过；不把“直接 publish 可用”写成“application subscribe 正例已测” |

新增 test.patch 只有这一个测试。全部关键新断言已核：异常发生、Code、完整 Message；finally 清理不是额外语义要求。helper `tests/test_sns/__init__.py:sns_aws_verified` 已全文读：默认在 mock_aws 中用 mock_api_key，只有显式 MOTO_TEST_ALLOW_AWS_REQUEST=true 才走真实 AWS/SSM/Firebase 分支。aws_verified 标签与 docstring 是上游声明，不是本轮远端验证。

## 合理解法、gold 和回归

合理替代路线是在调用 _find_subscription 前针对 application 调用 get_endpoint，转换为 SNSInvalidParameter；其它协议和有效端点幂等不变。这样能满足公开原例，且无需采用 gold 的检查顺序。若按公开消息输出 “…endpoint {endpoint}”，静态预计被隐藏字符串断言拒绝；改成隐藏的额外 arn 则消除该项差异。此处分别保留行为争议与文案争议，不以 gold 注释裁决公开需求。

gold 是部分实现：对“从未订阅过的已删除端点”能修复；对题面原例返回旧对象。注释称旧订阅在删除端点后会短暂存在，但 base 没有相应过期清理路径，且该云服务声明未经本轮验证。不能把上游可能观察到的行为自动替换成题面新的条件。SMS 输入检查仍在原位；普通订阅调用者与公开 SQS 幂等测试已抽读。未穷举跨账户、跨区域与同时不存在的 topic/endpoint 错误优先级，这些未覆盖边界不单独判坏题。

## 环境、资产和 actor 开发条件

| 开发需要 | 可见依据和历史证据 | 剩余条件 / 最小验证路径 |
| --- | --- | --- |
| 导入工作区 moto、boto3/botocore，执行本地 SNS mock | public Makefile:16–18 为 pip editable + requirements-dev；requirements-tests 含 pytest/xdist。历史 ledger observation import=/testbed/moto/__init__.py、源版本 5.0.6.dev | 正式 agent/54321 shell 的 PATH、解释器、包来源待核；可先打印 sys.executable、moto.__file__，再运行带 mock_aws、明确 region 的公开原例 |
| 离线构建依赖 | E/image.json、build.log：public digest 3b263c… 派生为 image 5d879f…，COPY setuptools72.1.0/wheel0.43.0/packaging24.1，并设 PIP_NO_INDEX/FIND_LINKS | COPY 本身不是安装；gold log:441 起 make init 与 442 的离线目录、483/594 成功安装，noop 同样完成，证明这一 grader 消费链。正式 actor 仍取 public image，未证自动使用派生层 |
| 本地测试与数据 | mocks 在内存构造应用/端点，无额外模型权重或数据资产；默认 helper 不需要 AWS 凭证/Firebase 密钥 | 不开启 live 分支。公开旧测试可窄跑 test_application_boto3.py / test_subscriptions_boto3.py；这是建议命令，未执行 |
| 写入/提交 | 修复只需 moto/sns/models.py 或等价非测试调用层 | 工作区可写是代码默认；系统环境可写不由 candidate.apply_user 证明。无需修改隐藏测试或不可提交资产 |

base setup.cfg:3 自身写 version=4.1.0.dev，而 moto/__init__.py:4 写 5.0.6.dev；因此日志安装分发名 4.1.0.dev0 与源版本差异有公开源码解释，不据此宣称错版本。

已读 E/{gold,noop}/ledger.jsonl 各第 1 行和 run_refs 指定日志的恢复、安装、测试、失败/摘要段。gold 日志 607 命令 `pytest -n0 -rA tests/test_sns/test_application_boto3.py`，645 行 20 passed/rc0；noop 650–655 行唯一 F2P failed、19 passed/rc1。ledger 是历史真实 RH2 诊断：gold F2P1/1、P2P19/19、reward1；noop F2P0/1、P2P19/19、reward0。两者 grader UID54322、2 CPU/4GiB、deny_all、可写 conda 前缀；candidate.apply_user=agent/54321 仅应用补丁。不是正式 actor 开发会话，也不是本轮重跑。

## 投影、官方恢复与控制面

已核当前 ROOT/rh2 实现（仓库 HEAD e3d120b55a62cca5985f688de8cdd481b12ea6be；源码可含未提交变化，引用以已读函数为准）：

- prepared_task_face.py:312–335 用 test.patch 精确路径，`test_globs=()`；本题官方恢复/保护仅 `tests/test_sns/test_application_boto3.py`，gold 的 `moto/sns/models.py` 被投影保留；ledger included_paths 对应。
- trusted_projection.py:classify_control_plane_path 与 manager.py:HygieneRules 仍保护官方精确文件和 .rh2*/rh2/* 保留域，不按所有测试名排除。因此 `tests/test_sns/__init__.py` 的 decorator 位于官方文件之外；若候选篡改它使其不调用 func，可能让装饰后的验收测试空跑通过。仅为静态控制面风险，违反公开“不改测试”指令，不是合理修复，也未做利用实验；不能声称该 helper 会自动恢复。
- scoring.py:parse_eval_log_v2、swegym_parsers.py:parse_log_pytest 按标记段与冻结 F2P/P2P 解析；manager.py:execution_failure_trigger/classify_execution_failure_shape 区分全局执行失败。普通完成的非参考 pytest 失败/rc1 不自动令 reward0。
- rollout_spec_from_view 使用 public image、prompt、bundle；render_user_prompt 不拼 public_hints，但 bundle 会公开物化，不能说提示字段不可见。materialize 的 /root/.rh2_bash_env 与 profile 隐藏 /root 的可读/激活实际效果仍待 actor 验证；未据静态冲突断言已坏。

## 关系、暴露与唯一下一步

同上下文还私有审查 5752、5134；这些是不同 API 问题，不能仅按同仓并簇。已在本题后续 base 看到 5134 的 UNDEFINED/exists 修法（events/models.py:40、888、917）和 5752 的标签列表匹配修法（ssm/models.py:1872 起）；这是跨版本答案包含关系，须在任务划分/跨题 solver 暴露中保留。未读任何其它题结论或未来 Git 历史。本 reviewer 已见 gold、隐藏测试、运行原件，不是公开 solver，也不能作为独立模型求解样本。

唯一优先下一步：在已冻结 grader 诊断条件下做一组离线 CPU 语义对照，同时检查 base、gold 与“先验证 endpoint、按公开消息”的合理替代实现对完整公开原例和 RH2 原参考集的结果。应区分“公开原例仍成功却得1”与“公开行为修好却因额外 arn 得0”，保留调用/异常/评分日志；不调用 live AWS，不先改正式题面/测试。本轮未执行该实验。actor 环境启用核验是另一个条件，不能由这组实验代替。
