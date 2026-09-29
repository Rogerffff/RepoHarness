# -*- coding: utf-8 -*-
"""L3 反例：getmoto__moto-6470 —— 规格分歧点 + 候选悄悄删掉的既有校验。

## 分歧点是什么

题面只说：对 moto server 调 `batch.create_compute_environment()`，
`computeResources={'type':'EC2','maxvCpus':1,'subnets':[...]}`（无 `instanceRole`、无 `minvCpus`）
时返回 **HTTP 500**。题面没有说正确结果应该是什么。两种解释都能读通：

  解释 A（宽松放行 / 候选走的路）：500 是 `KeyError` 冒出来的，补上默认值让请求成功即可。
  解释 B（严格必填 / gold 与真实 AWS）：这类请求本来就非法，应返回 AWS 风格的
        `ClientException`（HTTP 400），消息为 "Error executing request, Exception : Instance role is required."

判定依据只出现在 `hints_text`（原始行 `swe_gym_lite_full_f70b1a29.jsonl:109`，维护者明说 AWS 会因
`Instance role is required` 报错），而 `hints_text` **不在 agent 可见的 prompt 里**。
所以这题的失分里有一段是 prompt 信息缺失，而不是纯粹的能力问题。

## 除了分歧点，还有一处候选单方面放宽、且官方测不到的地方

候选把 `_validate_compute_resources` 里这段整个删掉了：

    if len(cr["securityGroupIds"]) == 0:
        raise InvalidParameterValueException("At least 1 security group must be provided")

用 `git grep "At least 1 security group" <base_commit>` 在整个仓库里搜，只在
`moto/batch/models.py:1312` 命中，**tests/ 下没有任何用例覆盖它**。
也就是说：不论按解释 A 还是解释 B，这都是一次没有任何测试能发现的公开行为回退。

本文件把三件事分开写：
  `test_strict_*`  = 解释 B 成立时应通过（gold / 真实 AWS）
  `test_lenient_*` = 解释 A 成立时应通过（候选）
  `test_preserved_*` = 两种解释下都**不应**改变的既有校验（候选在这里回退了）

参考：`solvability_review_20260909/01_failure_cases.md` §2；轨迹 `stream.jsonl:4621-4622`
（复现 KeyError）、`:7766-7772`（起 moto.server 跑题面脚本，返回 OK）。
"""
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from moto import mock_batch, mock_ec2, mock_ecs, mock_iam

from . import _get_clients, _setup


def _create_ec2_env(batch_client, iam_arn, compute_resources, name=None):
    return batch_client.create_compute_environment(
        computeEnvironmentName=name or str(uuid4()),
        type="MANAGED",
        state="ENABLED",
        computeResources=compute_resources,
        serviceRole=iam_arn,
    )


# ==========================================================================
# 解释 B（严格必填）：gold 的语义。candidate 预期全部 FAIL。
# ==========================================================================
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_strict_missing_instance_role_raises_client_exception():
    """缺 instanceRole → ClientException（HTTP 400），不是 500，也不是成功。"""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    with pytest.raises(ClientError) as exc:
        _create_ec2_env(
            batch_client, iam_arn,
            {"type": "EC2", "maxvCpus": 1, "subnets": [subnet_id]},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException", "错误码是 %r" % err["Code"]
    assert "Instance role is required." in err["Message"], "消息是 %r" % err["Message"]


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_strict_missing_minvcpus_raises_client_exception():
    """给了 instanceRole 但缺 minvCpus → ClientException。"""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    with pytest.raises(ClientError) as exc:
        _create_ec2_env(
            batch_client, iam_arn,
            {
                "type": "EC2",
                "maxvCpus": 1,
                "subnets": [subnet_id],
                "instanceRole": iam_arn.replace("role", "instance-profile"),
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert "Resource minvCpus is required." in err["Message"], "消息是 %r" % err["Message"]


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_strict_rejects_without_binding_message_text():
    """与上两条互补：只要求"被拒绝"，不绑定错误码与消息文本。

    用来区分"实现选了别的错误码/文案"和"实现根本不拒绝"。
    base 也应通过（base 会抛 500 级异常，boto3 一样报 ClientError）。
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    try:
        resp = _create_ec2_env(
            batch_client, iam_arn,
            {"type": "EC2", "maxvCpus": 1, "subnets": [subnet_id]},
        )
    except ClientError:
        return  # 被拒绝，符合解释 B
    pytest.fail("缺 instanceRole 的 EC2 请求被接受了：%r" % (resp.get("computeEnvironmentArn"),))


# ==========================================================================
# 解释 A（宽松放行）：候选的语义。base 与 gold 预期 FAIL。
# ==========================================================================
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_lenient_minimal_ec2_request_succeeds():
    """题面那组 computeResources 直接建成功（候选的目标行为）。"""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    resp = _create_ec2_env(
        batch_client, iam_arn,
        {"type": "EC2", "maxvCpus": 1, "subnets": [subnet_id]},
    )
    assert "computeEnvironmentArn" in resp


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_lenient_minimal_request_is_describable_and_echoes_resources():
    """候选路线下该环境能被 describe 出来，且 computeResources 原样回显。

    注意：`status` 在 `describe_compute_environments` 里是硬编码的 "VALID"
    （base `moto/batch/models.py:1159`），断言它没有信息量，所以这里断言的是
    "环境被建出来了" + "存下来的 computeResources 就是请求里那份，没有被补默认值"。
    后者说明候选的默认值只在建实例时临时补，非法请求在 API 层被当成合法资源记录下来。
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    name = str(uuid4())
    submitted = {"type": "EC2", "maxvCpus": 1, "subnets": [subnet_id]}
    _create_ec2_env(batch_client, iam_arn, dict(submitted), name=name)
    envs = batch_client.describe_compute_environments(computeEnvironments=[name])[
        "computeEnvironments"
    ]
    assert len(envs) == 1
    assert envs[0]["computeResources"] == submitted, (
        "回显的 computeResources 变了：%r" % (envs[0].get("computeResources"),)
    )


# ==========================================================================
# 两种解释下都应保留的既有校验（候选把它删了，官方测不到）
# ==========================================================================
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_preserved_empty_security_group_list_is_rejected():
    """既有行为：显式传空 securityGroupIds 应报 "At least 1 security group must be provided"。

    base PASS、gold PASS、candidate FAIL。这条与"缺字段该不该放行"的分歧无关：
    这里字段是**给了的**，只是空列表；删掉这个检查不需要任何解释支撑。
    仓库里没有任何测试覆盖它（`git grep "At least 1 security group"` 只命中 models.py）。
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    with pytest.raises(ClientError) as exc:
        _create_ec2_env(
            batch_client, iam_arn,
            {
                "type": "EC2",
                "minvCpus": 0,
                "maxvCpus": 1,
                "instanceTypes": ["optimal"],
                "subnets": [subnet_id],
                "securityGroupIds": [],
                "instanceRole": iam_arn.replace("role", "instance-profile"),
            },
        )
    assert "At least 1 security group must be provided" in exc.value.response["Error"]["Message"], (
        "既有校验被移除或消息变了：%r" % exc.value.response["Error"]["Message"]
    )


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_preserved_empty_subnet_list_is_rejected():
    """对照组：同一函数里的 subnets 空列表校验，候选保留了它。三态都应 PASS。"""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, _, sg_id, iam_arn = _setup(ec2_client, iam_client)

    with pytest.raises(ClientError) as exc:
        _create_ec2_env(
            batch_client, iam_arn,
            {
                "type": "EC2",
                "minvCpus": 0,
                "maxvCpus": 1,
                "instanceTypes": ["optimal"],
                "subnets": [],
                "securityGroupIds": [sg_id],
                "instanceRole": iam_arn.replace("role", "instance-profile"),
            },
        )
    assert "At least 1 subnet must be provided" in exc.value.response["Error"]["Message"]


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_preserved_unknown_security_group_is_rejected():
    """既有行为：给了不存在的 security group 应被拒。三态都应 PASS（候选保留了这段循环）。"""
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, _, iam_arn = _setup(ec2_client, iam_client)

    with pytest.raises(ClientError) as exc:
        _create_ec2_env(
            batch_client, iam_arn,
            {
                "type": "EC2",
                "minvCpus": 0,
                "maxvCpus": 1,
                "instanceTypes": ["optimal"],
                "subnets": [subnet_id],
                "securityGroupIds": ["sg-00000000000000000"],
                "instanceRole": iam_arn.replace("role", "instance-profile"),
            },
        )
    assert "does not exist" in exc.value.response["Error"]["Message"]


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_preserved_fargate_does_not_require_instance_role():
    """护栏：FARGATE 分支本来就不受 instanceRole/minvCpus 约束，三态都应 PASS。

    如果某个实现把"必填"加到了 FARGATE 分支上，这条会抓住它。
    """
    ec2_client, iam_client, _, _, batch_client = _get_clients()
    _, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp = _create_ec2_env(
        batch_client, iam_arn,
        {
            "type": "FARGATE",
            "maxvCpus": 1,
            "subnets": [subnet_id],
            "securityGroupIds": [sg_id],
        },
    )
    assert "computeEnvironmentArn" in resp
