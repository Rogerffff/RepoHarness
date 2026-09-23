"""Moto5752 行为裁决：DescribeParameters 的标签过滤——题面 MWE 的两种顺序（公开需求）与 tag+BeginsWith（F2P 第 3 断言，题面未提）。
在 behavior_check.sh 的容器里以 base / gold / 候选分别运行；每行 RESULT= 一个 JSON。"""
import json

import boto3
from moto import mock_ssm


def names(client, filters):
    r = client.describe_parameters(ParameterFilters=filters)
    return sorted(p["Name"] for p in r["Parameters"])


def emit(case, value, basis):
    print("RESULT=" + json.dumps({"case": case, "value": value, "basis": basis}, ensure_ascii=False))


with mock_ssm():
    c = boto3.client("ssm", region_name="eu-west-1")
    c.put_parameter(Name="/spam/eggs", Value="eggs", Type="String", Tags=[{"Key": "spam", "Value": "eggs"}])
    c.put_parameter(Name="/hello/world", Value="world", Type="String", Tags=[{"Key": "hello", "Value": "world"}])
    c.put_parameter(Name="/hello2", Value="x", Type="String", Tags=[{"Key": "hello", "Value": "world2"}])
    # 题面 MWE：两个 tag 过滤器同时给出，顺序不同结果应一致（各只匹配一个参数）
    f1 = [{"Key": "tag:spam", "Values": ["eggs"]}, {"Key": "tag:hello", "Values": ["world"]}]
    f2 = list(reversed(f1))
    emit("issue_order_A_two_tag_filters", names(c, f1), "题面：两个 tag 过滤器同时匹配的参数才应返回（预期 []，因为没有参数同时带两个标签）")
    emit("issue_order_B_two_tag_filters", names(c, f2), "题面：与顺序 A 结果一致")
    emit("single_tag_equals", names(c, [{"Key": "tag:hello", "Values": ["world"]}]), "既有行为：单标签等值匹配 → ['/hello/world']")
    # F2P 第 3 断言（题面未提）：tag + BeginsWith
    try:
        v = names(c, [{"Key": "tag:hello", "Option": "BeginsWith", "Values": ["w"]}])
        emit("tag_beginswith_w", v, "F2P 第 3 断言期望 2 项（/hello/world、/hello2）；AWS API 文档允许标签过滤用 BeginsWith；题面未提")
    except Exception as exc:  # noqa: BLE001
        emit("tag_beginswith_w", f"error:{type(exc).__name__}:{str(exc)[:120]}", "同上")
    try:
        v = names(c, [{"Key": "tag:hello", "Option": "Equals", "Values": ["world"]}])
        emit("tag_equals_explicit_option", v, "显式 Option=Equals 应与缺省一致")
    except Exception as exc:  # noqa: BLE001
        emit("tag_equals_explicit_option", f"error:{type(exc).__name__}:{str(exc)[:120]}", "同上")
