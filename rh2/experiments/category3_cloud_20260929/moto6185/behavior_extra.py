"""私有行为对照补充行（moto-6185）：名为 S 的属性是否关掉了其它类型校验。与 behavior.py 同一入口
（关闭 botocore 参数校验的低层 client、F2P 同款表），每行只记录 put 结果与之后是否已存入。"""
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
    ("attrS_contains_N_int", {"S": {"M": {"sth": {"N": 5}}}}),
    ("attrS_then_nested_N_int", {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}}),
    ("nested_N_int_then_attrS", {"nested": {"M": {"sth": {"N": 5}}}, "S": {"S": "asdf"}}),
    ("nested_attrS_contains_N_int", {"A": {"M": {"S": {"M": {"x": {"N": 5}}}}}}),
    ("attrS_then_nonkey_S_int", {"S": {"S": "asdf"}, "bad": {"S": 123}}),
]
out = {}
with mock_dynamodb():
    c = botocore.session.Session().create_client(
        "dynamodb", region_name="us-east-1", config=botocore.client.Config(parameter_validation=False))
    c.create_table(TableName="without_sk", KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                   AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                   ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1})
    for i, (name, attrs) in enumerate(ROWS):
        pk = f"x{i}"
        try:
            c.put_item(TableName="without_sk", Item={"pk": {"S": pk}, **attrs})
            r = "ok"
        except ClientError as e:
            r = f"ClientError:{e.response['Error']['Code']}:{e.response['Error']['Message'][:50]}"
        except Exception as e:  # noqa: BLE001
            r = f"{type(e).__name__}:{str(e)[:60]}"
        try:
            stored = c.get_item(TableName="without_sk", Key={"pk": {"S": pk}}).get("Item") is not None
        except Exception as e:  # noqa: BLE001
            stored = f"get-{type(e).__name__}"
        out[name] = f"{r} stored_after={stored}"
print("=== SUMMARY")
for k, v in out.items():
    print(f"X.{k}: {v}")
