"""复核者补充探针（moto-6185，私有）：正对照与 base 可能不同的畸形输入。关闭参数校验的低层 client。

每行：row、put 结果、之后是否存入（及存入的值）。这些输入都不是合法的 AttributeValue，
只用来登记各版本与 base 的行为差异，不作判分依据。
"""
import json
import os

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ["TEST_SERVER_MODE"] = "false"
import botocore.client  # noqa: E402
import botocore.session  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_dynamodb  # noqa: E402

ROWS = [
    # v2s／v3 的“非主键 S→dict”两例：普通名字、名为 S 的属性
    ("attr_S_dict", {"attr": {"S": {"S": "asdf"}}}),
    ("attrS_S_dict", {"S": {"S": {"S": "asdf"}}}),
    # map 成员的值是“裸值”而不是 AttributeValue；成员名恰为 S 或 N 时 base 会“碰巧”报错
    ("raw_member_named_S_int", {"A": {"M": {"S": 5}}}),
    ("raw_member_named_N_int", {"A": {"M": {"N": 5}}}),
    ("raw_member_named_x_int", {"A": {"M": {"x": 5}}}),
    # S 类型给布尔值、列表（base 不校验）
    ("nonkey_S_bool", {"attr": {"S": True}}),
    ("nonkey_S_list", {"attr": {"S": ["a"]}}),
    # list 内的畸形值（base 不校验 list）
    ("list_N_int", {"A": {"L": [{"N": 5}]}}),
    ("list_map_member_N_int", {"A": {"L": [{"M": {"x": {"N": 5}}}]}}),
    # 同一个 AttributeValue 里有两个类型标签
    ("two_tags_N_int", {"attr": {"S": "a", "N": 5}}),
]

with mock_dynamodb():
    c = botocore.session.Session().create_client(
        "dynamodb", region_name="us-east-1", config=botocore.client.Config(parameter_validation=False))
    c.create_table(TableName="t", KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                   AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                   ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1})
    for i, (row, attrs) in enumerate(ROWS):
        pk = f"e{i}"
        try:
            c.put_item(TableName="t", Item={"pk": {"S": pk}, **attrs})
            put = "ok"
        except ClientError as e:
            err = e.response["Error"]
            put = err["Code"] + ":" + err["Message"][:40]
        except Exception as e:  # noqa: BLE001
            put = "EXC:" + type(e).__name__
        try:
            got = c.get_item(TableName="t", Key={"pk": {"S": pk}}).get("Item")
        except Exception as e:  # noqa: BLE001
            got = "get-" + type(e).__name__
        print(json.dumps({"row": row, "put": put, "stored": got}, default=str, sort_keys=True))
