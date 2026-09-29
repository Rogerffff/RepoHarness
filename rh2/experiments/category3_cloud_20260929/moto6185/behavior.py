"""私有行为对照（moto-6185，不交给求解者）：合法属性名 S 在各位置的 Put/Get 往返，以及真正类型错误的服务端校验。

分四组：
- L：题面同款表（HASH index，类型 N），资源层 API、正常 SDK 校验；题面两例、非示例的字符串值、深层、list 内 map、
  其它类型标签作属性名、S 在前的属性顺序，以及 batch/transact/update 入口；
- K：主键名本身是 M 或 S 的表（合法但少见的主键名）；
- N：关闭 botocore 参数校验的低层 client（与 F2P 同一入口），各种真正的类型错误；
- 每行记录 put 结果（成功 / ClientError 的 Code 与 Message / 其它 Python 异常类型），合法行再做 get 等值比较。
"""
import json
import os
from decimal import Decimal

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ["TEST_SERVER_MODE"] = "false"
import boto3  # noqa: E402
import botocore.client  # noqa: E402
import botocore.session  # noqa: E402
from boto3.dynamodb.types import TypeSerializer  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_dynamodb  # noqa: E402

PROV = {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}


def attempt(fn):
    try:
        return {"ok": True, "value": fn()}
    except ClientError as e:
        return {"ok": False, "kind": "ClientError", "code": e.response["Error"]["Code"],
                "message": e.response["Error"]["Message"]}
    except Exception as e:  # noqa: BLE001 - 记录非 ClientError 的内部异常
        return {"ok": False, "kind": type(e).__name__, "message": str(e)[:300]}


def make_table(ddb, name, hash_name, hash_type="N", range_name=None, range_type="S"):
    ks = [{"AttributeName": hash_name, "KeyType": "HASH"}]
    ad = [{"AttributeName": hash_name, "AttributeType": hash_type}]
    if range_name:
        ks.append({"AttributeName": range_name, "KeyType": "RANGE"})
        ad.append({"AttributeName": range_name, "AttributeType": range_type})
    ddb.create_table(TableName=name, KeySchema=ks, AttributeDefinitions=ad, ProvisionedThroughput=PROV)
    return ddb.Table(name)


def roundtrip(table, item, key_names):
    put = attempt(lambda: table.put_item(Item=item) and None)
    row = {"item": item, "put": put}
    if put["ok"]:
        key = {k: item[k] for k in key_names}
        got = attempt(lambda: table.get_item(Key=key).get("Item"))
        row["get_equal"] = got["ok"] and got["value"] == item
        if not row["get_equal"]:
            row["got"] = got
    return row


out = {"L": {}, "K": {}, "N": {}}
LEGAL = [
    ("control_lower_s", {"s": None}),
    ("control_A", {"A": None}),
    ("top_S_null", {"S": None}),                       # 题面例 1
    ("nested_S_null", {"A": {"S": None}}),             # 题面例 2
    ("top_S_str", {"S": "text"}),
    ("nested_S_str", {"A": {"S": "text"}}),
    ("deep_S", {"A": {"B": {"C": {"S": None}}}}),     # 题面“deeply nested”
    ("deep2_S_str", {"A": {"B": {"S": "x"}}}),
    ("nested_S_sibling", {"A": {"S": Decimal(1), "T": "x"}}),
    ("S_in_S_in_S", {"S": {"S": {"S": None}}}),
    ("nested_S_map_value", {"A": {"S": {"B": "x"}}}),
    ("list_map_S", {"A": [{"S": None}]}),
    ("other_tag_names", {"N": Decimal(5), "M": "m", "L": [Decimal(1)], "NULL": None, "SS": {"a"}}),
    ("S_first_then_other", {"S": None, "x": Decimal(1)}),
]
with mock_dynamodb():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    t = make_table(ddb, "test", "index")
    for i, (name, extra) in enumerate(LEGAL):
        out["L"][name] = roundtrip(t, {"index": i, **extra}, ["index"])
    # 共享 put 调用链的其它入口
    item = {"index": 100, "A": {"S": None}}
    def _batch():
        with t.batch_writer() as bw:
            bw.put_item(Item=item)
    b = attempt(_batch)
    got = attempt(lambda: t.get_item(Key={"index": 100}).get("Item"))
    out["L"]["batch_nested_S_null"] = {"put": b, "get_equal": got["ok"] and got["value"] == item}
    client = boto3.client("dynamodb", region_name="us-east-1")
    ser = TypeSerializer()
    item2 = {"index": 101, "A": {"S": None}}
    tr = attempt(lambda: client.transact_write_items(TransactItems=[
        {"Put": {"TableName": "test", "Item": {k: ser.serialize(v) for k, v in item2.items()}}}]) and None)
    got = attempt(lambda: t.get_item(Key={"index": 101}).get("Item"))
    out["L"]["transact_nested_S_null"] = {"put": tr, "get_equal": got["ok"] and got["value"] == item2}
    t.put_item(Item={"index": 102})
    up = attempt(lambda: t.update_item(Key={"index": 102}, UpdateExpression="SET #a = :v",
                                       ExpressionAttributeNames={"#a": "A"},
                                       ExpressionAttributeValues={":v": {"S": None}}) and None)
    got = attempt(lambda: t.get_item(Key={"index": 102}).get("Item"))
    out["L"]["update_set_nested_S_null"] = {"update": up,
                                            "get_equal": got["ok"] and got["value"] == {"index": 102, "A": {"S": None}}}

with mock_dynamodb():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    tm = make_table(ddb, "hashM", "M", "S")
    out["K"]["hashM_nested_S_null"] = roundtrip(tm, {"M": "id1", "A": {"S": None}}, ["M"])
    out["K"]["hashM_top_S_null"] = roundtrip(tm, {"M": "id2", "S": None}, ["M"])
    out["K"]["hashM_deep_S_str"] = roundtrip(tm, {"M": "id3", "A": {"B": {"S": "x"}}}, ["M"])
    out["K"]["hashM_plain"] = roundtrip(tm, {"M": "id4", "A": "x"}, ["M"])
    tr_ = make_table(ddb, "rangeM", "pk", "S", "M", "S")
    out["K"]["rangeM_nested_S_null"] = roundtrip(tr_, {"pk": "p", "M": "r", "A": {"S": None}}, ["pk", "M"])
    ts = make_table(ddb, "hashS", "S", "S")
    out["K"]["hashS_plain"] = roundtrip(ts, {"S": "id1"}, ["S"])
    out["K"]["hashS_nested_S_null"] = roundtrip(ts, {"S": "id2", "A": {"S": None}}, ["S"])
    tA = make_table(ddb, "hashA", "A", "S")
    out["K"]["hashA_nested_S_null"] = roundtrip(tA, {"A": "id1", "B": {"S": None}}, ["A"])

NEG = [
    ("pk_S_int", {"pk": {"S": 123}}),                                          # 公开旧测试
    ("pk_S_dict", {"pk": {"S": {"S": "asdf"}}}),                              # 公开旧测试
    ("nonkey_S_dict", {"pk": {"S": "a1"}, "bad": {"S": {"S": "x"}}}),
    ("nonkey_S_int", {"pk": {"S": "a2"}, "bad": {"S": 123}}),
    ("nested_nonkey_S_dict", {"pk": {"S": "a3"}, "A": {"M": {"x": {"S": {"S": "y"}}}}}),
    ("nested_nonkey_N_int", {"pk": {"S": "a4"}, "nested": {"M": {"sth": {"N": 5}}}}),  # 公开 P2P 同形
    ("nonkey_N_int", {"pk": {"S": "a5"}, "bad": {"N": 5}}),
    ("attrS_S_dict", {"pk": {"S": "a6"}, "S": {"S": {"S": "x"}}}),
    ("attrS_S_int", {"pk": {"S": "a7"}, "S": {"S": 123}}),
    ("attrS_first_then_N_int", {"S": {"NULL": True}, "x": {"N": 5}, "pk": {"S": "a8"}}),
]
with mock_dynamodb():
    session = botocore.session.Session()
    c = session.create_client("dynamodb", region_name="us-east-1",
                              config=botocore.client.Config(parameter_validation=False))
    c.create_table(TableName="without_sk", KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                   AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}], ProvisionedThroughput=PROV)
    for name, item in NEG:
        r = attempt(lambda: c.put_item(TableName="without_sk", Item=item) and None)
        row = {"item": item, "put": r}
        pk = item.get("pk", {}).get("S")
        if isinstance(pk, str):
            g = attempt(lambda: c.get_item(TableName="without_sk", Key={"pk": {"S": pk}}).get("Item"))
            row["stored_after"] = g if not g["ok"] else (g["value"] is not None)
        out["N"][name] = row
    # 合法的低层写法（与 F2P 新增正例同一入口），作为对照
    for name, item in [("lowlevel_top_S_str", {"pk": {"S": "v1"}, "S": {"S": "asdf"}}),
                       ("lowlevel_nested_S_null", {"pk": {"S": "v2"}, "A": {"M": {"S": {"NULL": True}}}}),
                       ("lowlevel_deep_S_str", {"pk": {"S": "v3"}, "A": {"M": {"B": {"M": {"S": {"S": "x"}}}}}}),
                       ("lowlevel_list_map_S", {"pk": {"S": "v4"}, "A": {"L": [{"M": {"S": {"S": "x"}}}]}})]:
        r = attempt(lambda: c.put_item(TableName="without_sk", Item=item) and None)
        row = {"item": item, "put": r}
        if r["ok"]:
            g = attempt(lambda: c.get_item(TableName="without_sk", Key={"pk": item["pk"]})["Item"])
            row["get_equal"] = g["ok"] and g["value"] == item
        out["N"][name] = row


def summarize(row):
    p = row.get("put", row.get("update"))
    s = "ok" if p["ok"] else (f"{p['kind']}:{p.get('code', '')}:{p['message'][:60]}")
    if "get_equal" in row:
        s += f" get_equal={row['get_equal']}"
    if "stored_after" in row:
        s += f" stored_after={row['stored_after']}"
    return s


print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print("=== SUMMARY")
for g in out:
    for k, v in out[g].items():
        print(f"{g}.{k}: {summarize(v)}")
