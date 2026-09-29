"""私有行为对照：题面示例序列、从未订阅过的已删端点、不存在端点、有效端点重复订阅、其它协议。"""
import json
import os

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_aws  # noqa: E402


def attempt(fn):
    try:
        return {"raised": False, "value": fn()}
    except ClientError as e:
        return {"raised": True, "code": e.response["Error"]["Code"], "message": e.response["Error"]["Message"]}


def setup(conn):
    app = conn.create_platform_application(Name="test", Platform="GCM", Attributes={})["PlatformApplicationArn"]
    ep = conn.create_platform_endpoint(PlatformApplicationArn=app, Token="test-token")["EndpointArn"]
    topic = conn.create_topic(Name="test-topic")["TopicArn"]
    return app, ep, topic


def sub(conn, topic, ep, protocol="application"):
    return lambda: conn.subscribe(TopicArn=topic, Endpoint=ep, Protocol=protocol)["SubscriptionArn"]


out = {}
with mock_aws():
    c = boto3.client("sns", region_name="us-east-1")
    app, ep, topic = setup(c)
    first = attempt(sub(c, topic, ep))
    c.delete_endpoint(EndpointArn=ep)
    second = attempt(sub(c, topic, ep))
    out["statement_example"] = {"endpoint": ep, "first": first, "second_after_delete": second}
with mock_aws():
    c = boto3.client("sns", region_name="us-east-1")
    app, ep, topic = setup(c)
    c.delete_endpoint(EndpointArn=ep)
    out["deleted_never_subscribed"] = {"endpoint": ep, "subscribe": attempt(sub(c, topic, ep))}
with mock_aws():
    c = boto3.client("sns", region_name="us-east-1")
    app, ep, topic = setup(c)
    fake = ep.rsplit("/", 1)[0] + "/00000000-0000-0000-0000-000000000000"
    out["never_created_endpoint"] = {"endpoint": fake, "subscribe": attempt(sub(c, topic, fake))}
with mock_aws():
    c = boto3.client("sns", region_name="us-east-1")
    app, ep, topic = setup(c)
    a, b = attempt(sub(c, topic, ep)), attempt(sub(c, topic, ep))
    out["valid_twice"] = {"first": a, "second": b,
                          "same_arn": (not a["raised"] and not b["raised"] and a["value"] == b["value"]),
                          "listed": len(c.list_subscriptions_by_topic(TopicArn=topic)["Subscriptions"])}
with mock_aws():
    c = boto3.client("sns", region_name="us-east-1")
    topic = c.create_topic(Name="t2")["TopicArn"]
    sqs = boto3.client("sqs", region_name="us-east-1")
    q = sqs.create_queue(QueueName="q")["QueueUrl"]
    qarn = sqs.get_queue_attributes(QueueUrl=q, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    out["other_protocols"] = {"sqs": attempt(sub(c, topic, qarn, "sqs")),
                              "email": attempt(sub(c, topic, "a@example.com", "email"))}
print(json.dumps(out, ensure_ascii=False, indent=1))
